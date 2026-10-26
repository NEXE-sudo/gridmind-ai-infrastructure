"""Single policy execution path shared by the API and experiment runner."""
from __future__ import annotations

from typing import Any

from .datacenter_simulator import DatacenterSimulator
from .nemotron import Proposal, request_proposal
from .workload_scheduler import schedule

POLICIES = ("fifo", "priority", "resource_aware", "nemotron")


def execute_policy_step(
    sim: DatacenterSimulator,
    policy: str,
    *,
    use_live_model: bool = False,
) -> dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"Unsupported policy: {policy}")
    arrived = sim.activate_arrivals()
    proposal: Proposal | None = None
    fallback_used = False
    validation_rejections: list[dict[str, str]] = []
    if policy == "nemotron":
        queued = any(
            workload.status == "pending" and workload.submitted
            for workload in sim.workloads
        )
        if queued:
            sim.counters["ai_attempts"] += 1
            if use_live_model:
                sim.counters["ai_invocations"] += 1
                proposal = request_proposal(sim.state())
                if proposal.latency_ms is not None:
                    sim.ai_latencies_ms.append(proposal.latency_ms)
                sim.counters["ai_prompt_tokens"] += proposal.prompt_tokens
                sim.counters["ai_completion_tokens"] += proposal.completion_tokens
                if not proposal.used_model:
                    sim.counters["ai_failures"] += 1
            else:
                proposal = Proposal(
                    {},
                    "Offline evaluation selected deterministic fallback; no model request was made.",
                    "offline",
                    error_code="live_model_not_enabled",
                )
                sim.counters["ai_fallbacks"] += 1

            if proposal.used_model:
                validation_rejections = sim.validate_assignments(proposal.assignments)
                if validation_rejections or not proposal.assignments:
                    sim.counters["ai_invalid_proposals"] += 1
                    fallback_used = True
                else:
                    assignments = proposal.assignments
            else:
                if proposal.status == "invalid_response":
                    sim.counters["ai_invalid_proposals"] += 1
                fallback_used = True
        else:
            proposal = Proposal(
                {},
                "No eligible queued workloads; no model request was needed.",
                "not_needed",
            )
            assignments = {}

        if fallback_used:
            sim.counters["ai_fallbacks"] += 1 if proposal and proposal.status != "offline" else 0
            assignments = schedule(sim, "resource_aware")
        elif proposal and proposal.used_model:
            assignments = proposal.assignments
        decision = "resource_aware_fallback" if fallback_used else (
            "nemotron" if proposal and proposal.used_model else "nemotron_no_work"
        )
        rationale = proposal.explanation if proposal else "Deterministic fallback."
    else:
        assignments = schedule(sim, policy)
        decision = policy
        rationale = {
            "fifo": "Earliest submitted eligible workload first; placement respects fit.",
            "priority": "Highest priority, then earliest deadline, then submission order.",
            "resource_aware": (
                "Priority/deadline ordering with best-fit node packing under power limits."
            ),
        }[policy]

    result = sim.apply_action(assignments)
    result.update(
        {
            "decision": decision,
            "policy": policy,
            "proposed_assignments": (
                proposal.assignments if proposal and proposal.used_model else assignments
            ),
            "executed_assignments": assignments,
            "explanation": rationale,
            "proposal_status": proposal.status if proposal else "not_applicable",
            "proposal_latency_ms": proposal.latency_ms if proposal else None,
            "proposal_error_code": proposal.error_code if proposal else None,
            "proposal_validation_rejections": validation_rejections,
            "fallback_used": fallback_used,
            "arrivals": arrived,
        }
    )
    return result
