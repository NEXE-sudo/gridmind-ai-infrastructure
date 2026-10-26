"""Shared operational metric definitions for simulation and experiments."""
from __future__ import annotations

from collections.abc import Iterable
from statistics import fmean, stdev
from typing import Any


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")
    index = (len(ordered) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower), 4)


def calculate_metrics(sim: Any) -> dict[str, Any]:
    """Calculate one consistent, machine-readable snapshot of simulator outcomes."""
    workloads = sim.workloads
    submitted = [workload for workload in workloads if workload.submitted]
    completed = [workload for workload in submitted if workload.status == "completed"]
    misses = sum(
        workload.deadline is not None
        and (
            workload.completed_at is not None
            and workload.completed_at > workload.deadline
            or workload.completed_at is None
            and workload.status not in {"failed", "cancelled"}
            and sim.step_count > workload.deadline
        )
        for workload in submitted
    )
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
    gpu_util_samples = sim.gpu_utilization_samples
    memory_util_samples = sim.memory_utilization_samples
    elapsed_hours = sim.step_count / 60
    counters = sim.counters
    available_power = sum(node.power_kw for node in sim.nodes)

    return {
        "elapsed_steps": sim.step_count,
        "submitted_workloads": len(submitted),
        "completed_workloads": len(completed),
        "failed_workloads": sum(workload.status == "failed" for workload in submitted),
        "cancelled_workloads": sum(workload.status == "cancelled" for workload in submitted),
        "unfinished_workloads": sum(
            workload.status in {"pending", "running"} for workload in submitted
        ),
        "queued_workloads": sum(
            workload.status == "pending" for workload in submitted
        ),
        "running_workloads": sum(
            workload.status == "running" for workload in submitted
        ),
        "completion_rate": round(len(completed) / len(submitted), 4) if submitted else 0.0,
        "throughput_jobs_per_hour": round(
            len(completed) / elapsed_hours, 4
        ) if elapsed_hours else 0.0,
        "deadline_misses": int(misses),
        "deadline_miss_rate": round(misses / len(submitted), 4) if submitted else 0.0,
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
        else 0.0,
        "completed_count_for_sla": len(completed),
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
        else 0.0,
        "gpu_utilization": round(current_gpus / total_gpus, 4)
        if total_gpus
        else 0.0,
        "average_gpu_utilization": round(fmean(gpu_util_samples), 4)
        if gpu_util_samples
        else 0.0,
        "current_memory_utilization": round(current_memory / total_memory, 4)
        if total_memory
        else 0.0,
        "average_memory_utilization": round(fmean(memory_util_samples), 4)
        if memory_util_samples
        else 0.0,
        "estimated_power_kw": round(available_power, 4),
        "power_budget_kw": sim.power_budget_kw,
        "power_budget_violations": counters["power_budget_violations"],
        "estimated_energy_kwh": round(sim.energy_kwh, 6),
        "estimated_energy_cost": round(sim.energy_kwh * sim.energy_price_per_kwh, 6),
        "energy_price_per_kwh": sim.energy_price_per_kwh,
        "failed_nodes": counters["node_failures"],
        "workloads_requeued": counters["workloads_requeued"],
        "rejected_actions": counters["rejected_actions"],
        "resource_rejections": counters["resource_rejections"],
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
        "workloads_with_deadlines": sum(
            workload.deadline is not None for workload in submitted
        ),
        "unfinished_deadline_misses_included": True,
        "sample_count_wait_times": len(wait_times),
        "sample_count_turnaround_times": len(turnaround_times),
    }


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize all run records, retaining unsuccessful runs in denominators."""
    if not runs:
        return {"run_count": 0, "successful_run_count": 0, "failed_run_count": 0}

    successful = [run for run in runs if run["status"] == "completed"]
    numeric_metrics = (
        "throughput_jobs_per_hour",
        "completion_rate",
        "deadline_miss_rate",
        "sla_attainment_rate",
        "average_queue_wait_minutes",
        "average_turnaround_minutes",
        "average_gpu_utilization",
        "average_memory_utilization",
        "estimated_energy_kwh",
        "estimated_energy_cost",
        "power_budget_violations",
        "rejected_actions",
        "failed_workloads",
        "unfinished_workloads",
        "ai_invocations",
        "ai_failures",
        "ai_fallbacks",
        "ai_invalid_proposals",
        "ai_latency_ms_mean",
    )
    summary: dict[str, Any] = {
        "run_count": len(runs),
        "successful_run_count": len(successful),
        "failed_run_count": sum(run["status"] == "failed" for run in runs),
        "incomplete_run_count": sum(run["status"] == "incomplete" for run in runs),
        "metrics_include_successful_runs_only": False,
        "metrics": {},
    }
    for metric in numeric_metrics:
        values = [
            float(run["metrics"][metric])
            for run in runs
            if run.get("metrics") is not None and run["metrics"].get(metric) is not None
        ]
        summary["metrics"][metric] = {
            "mean": round(fmean(values), 6) if values else None,
            "sample_stddev": round(stdev(values), 6) if len(values) > 1 else None,
            "p50": percentile(values, 0.5),
            "p95": percentile(values, 0.95),
            "n": len(values),
        }
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
            and node.power_kw
            + node.per_gpu_kw * workload.gpu_count
            <= node.power_limit_kw
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
