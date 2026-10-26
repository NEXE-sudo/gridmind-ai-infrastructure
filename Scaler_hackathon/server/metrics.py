"""Shared operational metric definitions for simulation and experiments."""
from __future__ import annotations

import random
from collections.abc import Iterable
from statistics import fmean, stdev
from typing import Any

STARVATION_THRESHOLD_MINUTES = 30
BOOTSTRAP_REPLICATES = 2_000


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    index = (len(ordered) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(
        ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 4
    )


def bootstrap_mean_interval(
    values: list[float],
    *,
    seed: int = 20_261_026,
) -> dict[str, float | int | None | str]:
    """Deterministic descriptive bootstrap; fewer than five pairs is insufficient."""
    if len(values) < 5:
        return {
            "lower": None,
            "upper": None,
            "replicates": 0,
            "status": "insufficient_independent_runs",
        }
    rng = random.Random(seed)
    means = sorted(
        fmean(rng.choices(values, k=len(values)))
        for _ in range(BOOTSTRAP_REPLICATES)
    )
    lower = percentile(means, 0.025)
    upper = percentile(means, 0.975)
    return {
        "lower": lower,
        "upper": upper,
        "replicates": BOOTSTRAP_REPLICATES,
        "status": "descriptive_percentile_bootstrap",
    }


def _reason_counts(reasons: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for reason in reasons:
        counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def calculate_metrics(sim: Any) -> dict[str, Any]:
    """Calculate one auditable snapshot with explicit workload denominators."""
    workloads = sim.workloads
    submitted = [workload for workload in workloads if workload.submitted]
    completed = [workload for workload in submitted if workload.status == "completed"]
    permanently_infeasible = [
        workload
        for workload in submitted
        if workload.failure_reason
        and workload.failure_reason.startswith("permanent_infeasibility:")
    ]
    structural_reasons = {
        workload.id: reason
        for workload in workloads
        if (reason := sim.permanent_infeasibility_reason(workload)) is not None
    }
    feasible = [
        workload
        for workload in workloads
        if sim.permanent_infeasibility_reason(workload) is None
    ]
    unresolved = [
        workload
        for workload in workloads
        if workload.status in {"pending", "running"}
    ]
    deadlines = [workload for workload in submitted if workload.deadline is not None]
    deadline_attained = [
        workload
        for workload in deadlines
        if workload.status == "completed"
        and workload.completed_at is not None
        and workload.completed_at <= workload.deadline
    ]
    deadline_missed = [
        workload
        for workload in deadlines
        if (
            workload.completed_at is not None
            and workload.completed_at > workload.deadline
        )
        or (
            workload.completed_at is None
            and sim.step_count >= workload.deadline
        )
    ]
    deadlines_due = [
        workload
        for workload in deadlines
        if sim.step_count >= workload.deadline
        or (
            workload.completed_at is not None
            and workload.completed_at > workload.deadline
        )
    ]
    wait_times = [
        workload.started_at - workload.submission_time
        for workload in completed
        if workload.started_at is not None
    ]
    turnaround_times = [
        workload.completed_at - workload.submission_time
        for workload in completed
        if workload.completed_at is not None
    ]
    total_gpus = sum(node.gpu_count for node in sim.nodes)
    total_memory = sum(node.memory_gb for node in sim.nodes)
    current_gpus = sum(node.allocated_gpus for node in sim.nodes)
    current_memory = sum(node.allocated_memory_gb for node in sim.nodes)
    elapsed_hours = sim.step_count / 60
    counters = sim.counters
    workload_class_totals: dict[str, int] = {}
    workload_class_completed: dict[str, int] = {}
    for workload in submitted:
        workload_class_totals[workload.workload_class] = (
            workload_class_totals.get(workload.workload_class, 0) + 1
        )
        if workload.status == "completed":
            workload_class_completed[workload.workload_class] = (
                workload_class_completed.get(workload.workload_class, 0) + 1
            )

    starved = [
        workload
        for workload in submitted
        if workload.status == "pending"
        and sim.permanent_infeasibility_reason(workload) is None
        and workload.last_scheduling_reason == "scheduler_deferral"
        and sim.step_count - workload.submission_time >= STARVATION_THRESHOLD_MINUTES
    ]
    status_counts = {
        status: sum(workload.status == status for workload in workloads)
        for status in ("pending", "running", "completed", "failed", "cancelled")
    }
    horizon_reached = (
        sim.horizon_steps is not None and sim.step_count >= sim.horizon_steps
    )
    outcome_classifications: dict[str, str] = {}
    for workload in workloads:
        if workload.failure_reason and workload.failure_reason.startswith(
            "permanent_infeasibility:"
        ):
            classification = "expected_infeasibility"
        elif workload.status in {"completed", "failed", "cancelled"}:
            classification = workload.status
        elif not workload.submitted:
            classification = "arrival_after_horizon" if horizon_reached else "not_arrived"
        elif (
            workload.deadline is not None
            and sim.step_count >= workload.deadline
        ):
            classification = "deadline_miss"
        elif workload.status == "running":
            classification = "horizon_incomplete" if horizon_reached else "running"
        elif workload.last_scheduling_reason == "node_failure_recovery":
            classification = "node_failure_recovery"
        elif workload.last_scheduling_reason in {
            "temporary_capacity_contention",
            "same_decision_reservation_contention",
        }:
            classification = "temporary_capacity_contention"
        elif workload.last_scheduling_reason == "power_constrained_waiting":
            classification = "power_constrained_waiting"
        elif workload.last_scheduling_reason == "model_proposal_omitted":
            classification = "scheduler_policy_deferred"
        elif (
            workload.last_scheduling_reason == "scheduler_deferral"
            and sim.step_count - workload.submission_time
            >= STARVATION_THRESHOLD_MINUTES
        ):
            classification = "starvation_or_scheduler_defect"
        else:
            classification = "horizon_incomplete" if horizon_reached else "pending"
        outcome_classifications[workload.id] = classification

    horizon_ids = [workload.id for workload in unresolved] if horizon_reached else None
    horizon_reasons = (
        _reason_counts(outcome_classifications[workload_id] for workload_id in horizon_ids or [])
        if horizon_reached
        else None
    )
    horizon_blocking_reasons = (
        _reason_counts(
            "arrival_after_horizon"
            if not workload.submitted
            else "running_work_at_horizon"
            if workload.status == "running"
            else workload.last_scheduling_reason or "unexplained_horizon_wait"
            for workload in unresolved
        )
        if horizon_reached
        else None
    )
    skip_counts: dict[str, int] = {}
    for workload in workloads:
        for reason, count in workload.scheduling_skip_counts.items():
            skip_counts[reason] = skip_counts.get(reason, 0) + count
    execution_failed = [
        workload
        for workload in submitted
        if workload.status == "failed" and workload not in permanently_infeasible
    ]
    completion_rate = len(completed) / len(submitted) if submitted else None
    submitted_feasible = [
        workload for workload in feasible if workload.submitted
    ]
    feasible_completion_rate = (
        sum(workload.status == "completed" for workload in submitted_feasible)
        / len(submitted_feasible)
        if submitted_feasible
        else None
    )
    scenario_completion_rate = (
        len(completed) / len(workloads) if workloads else None
    )
    scenario_feasible_completion_rate = (
        sum(workload.status == "completed" for workload in feasible) / len(feasible)
        if feasible
        else None
    )

    return {
        "elapsed_steps": sim.step_count,
        "total_workloads": len(workloads),
        "submitted_workloads": len(submitted),
        "arrived_workloads": len(submitted),
        "not_yet_arrived_workloads": sum(not workload.submitted for workload in workloads),
        "completed_workloads": len(completed),
        "failed_workloads": sum(workload.status == "failed" for workload in submitted),
        "execution_failed_workloads": len(execution_failed),
        "cancelled_workloads": sum(workload.status == "cancelled" for workload in submitted),
        "unfinished_workloads": sum(
            workload.status in {"pending", "running"} for workload in submitted
        ),
        "unresolved_workloads": len(unresolved),
        "unresolved_submitted_workloads": sum(
            workload.submitted for workload in unresolved
        ),
        "queued_workloads": sum(
            workload.status == "pending" for workload in submitted
        ),
        "running_workloads": sum(
            workload.status == "running" for workload in submitted
        ),
        "completion_rate": round(completion_rate, 4) if completion_rate is not None else None,
        "completion_rate_full_submitted_denominator": (
            round(completion_rate, 4) if completion_rate is not None else None
        ),
        "completion_rate_submitted_denominator": (
            round(completion_rate, 4) if completion_rate is not None else None
        ),
        "completion_rate_scenario_denominator": (
            round(scenario_completion_rate, 4)
            if scenario_completion_rate is not None
            else None
        ),
        "feasible_workloads": len(feasible),
        "feasible_completed_workloads": sum(
            workload.status == "completed" for workload in feasible
        ),
        "feasible_completion_rate": (
            round(feasible_completion_rate, 4)
            if feasible_completion_rate is not None
            else None
        ),
        "completion_rate_feasible_denominator": (
            round(feasible_completion_rate, 4)
            if feasible_completion_rate is not None
            else None
        ),
        "feasible_submitted_workloads": len(submitted_feasible),
        "feasible_scenario_completion_rate": (
            round(scenario_feasible_completion_rate, 4)
            if scenario_feasible_completion_rate is not None
            else None
        ),
        "throughput_jobs_per_hour": round(len(completed) / elapsed_hours, 4)
        if elapsed_hours
        else 0.0,
        "deadline_misses": len(deadline_missed),
        "deadline_miss_denominator": len(deadlines_due),
        "deadline_miss_rate": round(len(deadline_missed) / len(deadlines_due), 4)
        if deadlines_due
        else None,
        "deadline_attained_workloads": len(deadline_attained),
        "deadline_attainment_denominator": len(deadlines),
        "deadline_attainment_rate": round(len(deadline_attained) / len(deadlines), 4)
        if deadlines
        else None,
        "deadline_not_attained_workloads": len(deadlines) - len(deadline_attained),
        "unfinished_deadline_misses_included": True,
        "sla_attainment_rate": round(
            sum(
                workload.status == "completed"
                and (
                    workload.deadline is None
                    or workload.completed_at is not None
                    and workload.completed_at <= workload.deadline
                )
                for workload in submitted
            )
            / len(submitted),
            4,
        )
        if submitted
        else None,
        "completed_count_for_sla": len(completed),
        "workload_status_counts": status_counts,
        "permanently_infeasible_workloads": len(permanently_infeasible),
        "structurally_infeasible_scenario_workloads": len(structural_reasons),
        "structurally_infeasible_workload_ids": sorted(structural_reasons),
        "structural_infeasibility_reason_counts": _reason_counts(
            structural_reasons.values()
        ),
        "permanently_infeasible_workload_ids": [
            workload.id for workload in permanently_infeasible
        ],
        "permanent_infeasibility_reason_counts": _reason_counts(
            workload.failure_reason.removeprefix("permanent_infeasibility:")
            for workload in permanently_infeasible
            if workload.failure_reason
        ),
        "horizon_reached": horizon_reached,
        "horizon_steps": sim.horizon_steps,
        "horizon_incomplete_workloads": len(unresolved) if horizon_reached else None,
        "horizon_incomplete_workload_ids": horizon_ids,
        "horizon_incomplete_reason_counts": horizon_reasons,
        "horizon_incomplete_blocking_reason_counts": horizon_blocking_reasons,
        "workload_outcome_classifications": outcome_classifications,
        "average_queue_wait_minutes": round(fmean(wait_times), 4) if wait_times else None,
        "p50_queue_wait_minutes": percentile(wait_times, 0.5),
        "p95_queue_wait_minutes": percentile(wait_times, 0.95),
        "average_turnaround_minutes": round(fmean(turnaround_times), 4)
        if turnaround_times
        else None,
        "p50_turnaround_minutes": percentile(turnaround_times, 0.5),
        "p95_turnaround_minutes": percentile(turnaround_times, 0.95),
        "current_gpu_utilization": round(current_gpus / total_gpus, 4)
        if total_gpus
        else None,
        "gpu_utilization": round(current_gpus / total_gpus, 4)
        if total_gpus
        else None,
        "average_gpu_utilization": round(fmean(sim.gpu_utilization_samples), 4)
        if sim.gpu_utilization_samples
        else None,
        "current_memory_utilization": round(current_memory / total_memory, 4)
        if total_memory
        else None,
        "average_memory_utilization": round(fmean(sim.memory_utilization_samples), 4)
        if sim.memory_utilization_samples
        else None,
        "estimated_power_kw": round(sim.estimated_total_power_kw(), 4),
        "power_budget_kw": sim.power_budget_kw,
        "power_budget_violations": counters["power_budget_violations"],
        "estimated_energy_kwh": round(sim.energy_kwh, 6),
        "estimated_energy_cost": round(
            sim.energy_kwh * sim.energy_price_per_kwh, 6
        ),
        "energy_price_per_kwh": sim.energy_price_per_kwh,
        "failed_nodes": counters["node_failures"],
        "recovered_nodes": counters["node_recoveries"],
        "workloads_requeued": counters["workloads_requeued"],
        "workloads_preempted": counters["workloads_preempted"],
        "starved_workloads": len(starved),
        "starvation_threshold_minutes": STARVATION_THRESHOLD_MINUTES,
        "infeasible_pending_workloads": 0,
        "scheduling_skip_counts": dict(sorted(skip_counts.items())),
        "completion_rate_by_workload_class": {
            workload_class: round(
                workload_class_completed.get(workload_class, 0) / count, 4
            )
            for workload_class, count in sorted(workload_class_totals.items())
        },
        "rejected_actions": counters["rejected_actions"],
        "resource_rejections": counters["resource_rejections"],
        "gpu_model_rejections": counters["gpu_model_rejections"],
        "gpu_count_rejections": counters["gpu_count_rejections"],
        "memory_rejections": counters["memory_rejections"],
        "node_availability_rejections": counters["node_availability_rejections"],
        "node_power_rejections": counters["node_power_rejections"],
        "facility_power_rejections": counters["facility_power_rejections"],
        "fragmented_gpu_fraction": round(_fragmented_gpu_fraction(sim), 4),
        "ai_invocations": counters["ai_invocations"],
        "ai_attempts": counters["ai_attempts"],
        "ai_failures": counters["ai_failures"],
        "ai_fallbacks": counters["ai_fallbacks"],
        "ai_invalid_proposals": counters["ai_invalid_proposals"],
        "ai_latency_ms_mean": round(fmean(sim.ai_latencies_ms), 3)
        if sim.ai_latencies_ms
        else None,
        "ai_prompt_tokens": counters["ai_prompt_tokens"],
        "ai_completion_tokens": counters["ai_completion_tokens"],
        "model_cost": sim.model_cost,
        "model_cost_basis": sim.model_cost_basis,
        "workloads_with_deadlines": len(deadlines),
        "deadline_miss_semantics": (
            "A late completion or work still unresolved when its deadline is reached "
            "is a miss; unfinished work remains eligible after the deadline."
        ),
        "sample_count_wait_times": len(wait_times),
        "sample_count_turnaround_times": len(turnaround_times),
    }


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate only successful executions; retain workload outcomes in totals."""
    if not runs:
        return {
            "run_count": 0,
            "successful_run_count": 0,
            "failed_run_count": 0,
            "incomplete_run_count": 0,
            "metrics_include_successful_runs_only": True,
            "metrics": {},
            "workload_totals": {},
        }

    successful = [run for run in runs if run["status"] == "completed"]
    metric_names = (
        "throughput_jobs_per_hour",
        "completion_rate",
        "completion_rate_scenario_denominator",
        "feasible_completion_rate",
        "feasible_scenario_completion_rate",
        "deadline_miss_rate",
        "deadline_attainment_rate",
        "sla_attainment_rate",
        "average_queue_wait_minutes",
        "average_turnaround_minutes",
        "average_gpu_utilization",
        "average_memory_utilization",
        "estimated_energy_kwh",
        "estimated_energy_cost",
        "power_budget_violations",
        "rejected_actions",
        "resource_rejections",
        "failed_workloads",
        "execution_failed_workloads",
        "cancelled_workloads",
        "unfinished_workloads",
        "unresolved_workloads",
        "horizon_incomplete_workloads",
        "permanently_infeasible_workloads",
        "deadline_misses",
        "ai_invocations",
        "ai_failures",
        "ai_fallbacks",
        "ai_invalid_proposals",
        "ai_latency_ms_mean",
        "failed_nodes",
        "recovered_nodes",
        "workloads_requeued",
        "workloads_preempted",
        "starved_workloads",
        "infeasible_pending_workloads",
    )
    summary: dict[str, Any] = {
        "run_count": len(runs),
        "successful_run_count": len(successful),
        "failed_run_count": sum(run["status"] == "failed" for run in runs),
        "incomplete_run_count": sum(run["status"] == "incomplete" for run in runs),
        "metrics_include_successful_runs_only": True,
        "run_status_counts": _reason_counts(run["status"] for run in runs),
        "metrics": {},
        "workload_totals": {},
    }
    for metric in metric_names:
        values = [
            float(run["metrics"][metric])
            for run in successful
            if run.get("metrics") is not None
            and run["metrics"].get(metric) is not None
        ]
        summary["metrics"][metric] = {
            "mean": round(fmean(values), 6) if values else None,
            "sample_stddev": round(stdev(values), 6) if len(values) > 1 else None,
            "p50": percentile(values, 0.5),
            "p95": percentile(values, 0.95),
            "n": len(values),
            "confidence_interval_95": bootstrap_mean_interval(values),
        }
    count_metrics = (
        "submitted_workloads",
        "total_workloads",
        "not_yet_arrived_workloads",
        "completed_workloads",
        "failed_workloads",
        "execution_failed_workloads",
        "cancelled_workloads",
        "unfinished_workloads",
        "unresolved_workloads",
        "unresolved_submitted_workloads",
        "horizon_incomplete_workloads",
        "permanently_infeasible_workloads",
        "structurally_infeasible_scenario_workloads",
        "feasible_workloads",
        "feasible_completed_workloads",
        "deadline_misses",
        "deadline_miss_denominator",
        "deadline_attained_workloads",
        "deadline_attainment_denominator",
        "failed_nodes",
        "recovered_nodes",
        "workloads_requeued",
        "workloads_preempted",
        "starved_workloads",
        "rejected_actions",
        "resource_rejections",
        "gpu_model_rejections",
        "gpu_count_rejections",
        "memory_rejections",
        "node_availability_rejections",
        "node_power_rejections",
        "facility_power_rejections",
    )
    summary["workload_totals"] = {
        metric: sum(
            int(run["metrics"].get(metric) or 0)
            for run in successful
            if run.get("metrics") is not None
        )
        for metric in count_metrics
    }
    reason_totals: dict[str, int] = {}
    for run in successful:
        reasons = run.get("metrics", {}).get("horizon_incomplete_reason_counts") or {}
        for reason, count in reasons.items():
            reason_totals[reason] = reason_totals.get(reason, 0) + count
    summary["horizon_incomplete_reason_totals"] = dict(sorted(reason_totals.items()))
    blocking_reason_totals: dict[str, int] = {}
    for run in successful:
        reasons = (
            run.get("metrics", {}).get("horizon_incomplete_blocking_reason_counts")
            or {}
        )
        for reason, count in reasons.items():
            blocking_reason_totals[reason] = (
                blocking_reason_totals.get(reason, 0) + count
            )
    summary["horizon_incomplete_blocking_reason_totals"] = dict(
        sorted(blocking_reason_totals.items())
    )
    return summary


def _fragmented_gpu_fraction(sim: Any) -> float:
    free_gpu_capacity = 0
    unusable_free_gpu_capacity = 0
    queued = [
        workload
        for workload in sim.workloads
        if workload.submitted and workload.status == "pending"
    ]
    for node in sim.nodes:
        free = max(0, node.gpu_count - node.allocated_gpus)
        free_gpu_capacity += free
        if queued and not any(
            node.available
            and workload.gpu_count <= free
            and workload.memory_gb <= node.memory_gb - node.allocated_memory_gb
            and node.power_kw + node.per_gpu_kw * workload.gpu_count <= node.power_limit_kw
            and sim.estimated_total_power_kw()
            + node.per_gpu_kw * workload.gpu_count
            <= sim.power_budget_kw
            for workload in queued
        ):
            unusable_free_gpu_capacity += free
    return (
        unusable_free_gpu_capacity / free_gpu_capacity
        if free_gpu_capacity
        else 0.0
    )
