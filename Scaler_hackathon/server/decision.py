"""Single policy execution path shared by the API and experiment runner."""
from __future__ import annotations

from typing import Any

from .datacenter_simulator import DatacenterSimulator
from .nemotron import Proposal, request_proposal
from .workload_scheduler import (
    diagnose_unassigned,
    schedule_with_diagnostics,
)

POLICIES = ("fifo", "priority", "resource_aware", "nemotron")


def execute_policy_step(
    sim: DatacenterSimulator,
    policy: str,
    *,
    use_live_model: bool = False,
) -> dict[str, Any]:
    if policy not in POLICIES:
        raise ValueError(f"Unsupported policy: {policy}")
    preparation_events = sim.prepare_step()
    arrived = [
        event["workload_id"]
        for event in preparation_events
        if event["type"] in {"workload_arrived", "workload_failed"}
    ]
    proposal: Proposal | None = None
    fallback_used = False
    validation_rejections: list[dict[str, str]] = []
    scheduling_diagnostics: list[dict[str, Any]] = []
    placement_diagnostics: list[dict[str, Any]] = []
    if policy == "nemotron":
        queued = any(
            workload.status == "pending" and workload.submitted
            for workload in sim.workloads
        )
        if queued:
            sim.counters["ai_attempts"] += 1
            if use_live_model:
                proposal = request_proposal(sim.state())
                sim.counters["ai_request_attempts"] += proposal.request_attempts
                sim.counters["ai_retries"] += max(0, proposal.request_attempts - 1)
                sim.counters["ai_invocations"] += int(proposal.response_received)
                if proposal.latency_ms is not None:
                    sim.ai_latencies_ms.append(proposal.latency_ms)
                if proposal.prompt_tokens is not None:
                    sim.counters["ai_prompt_tokens"] += proposal.prompt_tokens
                    sim.counters["ai_prompt_token_reports"] += 1
                if proposal.completion_tokens is not None:
                    sim.counters["ai_completion_tokens"] += proposal.completion_tokens
                    sim.counters["ai_completion_token_reports"] += 1
                if proposal.used_model:
                    sim.counters["ai_valid_responses"] += 1
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
                if not proposal.assignments:
                    validation_rejections.append(
                        {"workload_id": "", "reason": "empty_assignments"}
                    )
                if validation_rejections:
                    sim.counters["ai_invalid_proposals"] += 1
                    fallback_used = True
                else:
                    assignments = proposal.assignments
                    placement_diagnostics = [
                        {
                            "workload_id": workload_id,
                            "node_id": node_id,
                            "assignment_source": "validated_model_proposal",
                            "selection_rule": "model_proposed_node",
                            "simulator_constraints_validated": True,
                            "candidate_evaluation": (
                                "not_performed_by_deterministic_scheduler"
                            ),
                        }
                        for workload_id, node_id in sorted(assignments.items())
                    ]
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
            (
                assignments,
                scheduling_diagnostics,
                placement_diagnostics,
            ) = schedule_with_diagnostics(sim, "resource_aware")
        elif proposal and proposal.used_model:
            assignments = proposal.assignments
            scheduling_diagnostics = diagnose_unassigned(
                sim, set(assignments), reason="model_proposal_omitted"
            )
        else:
            assignments = {}
            placement_diagnostics = []
        decision = "resource_aware_fallback" if fallback_used else (
            "nemotron" if proposal and proposal.used_model else "nemotron_no_work"
        )
        rationale = proposal.explanation if proposal else "Deterministic fallback."
    else:
        (
            assignments,
            scheduling_diagnostics,
            placement_diagnostics,
        ) = schedule_with_diagnostics(sim, policy)
        decision = policy
        rationale = {
            "fifo": "Earliest submitted eligible workload first; placement respects fit.",
            "priority": "Highest priority, then earliest deadline, then submission order.",
            "resource_aware": (
                "Priority/deadline ordering with best-fit node packing under power limits."
            ),
        }[policy]

    sim.record_scheduling_diagnostics(scheduling_diagnostics)
    result = sim.apply_action(assignments, prepared_events=preparation_events)
    inference_mode = "not_applicable"
    if proposal:
        if proposal.status == "offline":
            inference_mode = "offline_fallback"
        elif proposal.status == "not_needed":
            inference_mode = "not_attempted"
        elif proposal.status == "invalid_response" or (
            proposal.used_model and fallback_used
        ):
            inference_mode = "invalid_model_proposal"
        elif proposal.used_model:
            inference_mode = "live_success"
        elif (
            proposal.status == "unavailable"
            and proposal.error_code == "credentials_or_model_missing"
        ):
            inference_mode = "not_configured"
        elif use_live_model:
            inference_mode = "live_failure_fallback"
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
            "proposal_request_attempts": proposal.request_attempts if proposal else 0,
            "proposal_retry_count": (
                max(0, proposal.request_attempts - 1) if proposal else 0
            ),
            "proposal_response_received": (
                proposal.response_received if proposal else False
            ),
            "proposal_prompt_tokens": proposal.prompt_tokens if proposal else None,
            "proposal_completion_tokens": (
                proposal.completion_tokens if proposal else None
            ),
            "proposal_validation_rejections": validation_rejections,
            "scheduling_diagnostics": scheduling_diagnostics,
            "placement_diagnostics": placement_diagnostics,
            "fallback_used": fallback_used,
            "inference_mode": inference_mode,
            "arrivals": arrived,
        }
    )
    return result
