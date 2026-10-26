"""Deterministic schedulers and the optional constrained Nemotron policy."""
from __future__ import annotations

from typing import Any, Literal

from .datacenter_simulator import DatacenterSimulator, Node, Workload

PolicyName = Literal["fifo", "priority", "resource_aware"]


def _ordered_pending(
    sim: DatacenterSimulator, policy: PolicyName | str
) -> list[Workload]:
    pending = [
        workload
        for workload in sim.workloads
        if workload.status == "pending" and workload.submitted
    ]
    if policy == "fifo":
        pending.sort(key=lambda workload: workload.submission_time)
    elif policy == "priority":
        pending.sort(
            key=lambda workload: (
                -workload.priority,
                workload.deadline if workload.deadline is not None else 10**9,
                workload.submission_time,
                workload.id,
            )
        )
    elif policy == "resource_aware":
        pending.sort(
            key=lambda workload: (
                -workload.priority,
                workload.deadline if workload.deadline is not None else 10**9,
                -(workload.gpu_count * workload.memory_gb),
                workload.submission_time,
                workload.id,
            )
        )
    else:
        raise ValueError(f"Unknown scheduler policy: {policy}")
    return pending


def _node_reason(
    sim: DatacenterSimulator,
    workload: Workload,
    node: Node,
    reserved: list[int],
    projected_power: float,
) -> str | None:
    if workload.required_gpu_model and workload.required_gpu_model != node.gpu_model:
        return "gpu_model_mismatch"
    if workload.gpu_count > node.gpu_count:
        return "gpu_count_insufficient"
    if workload.memory_gb > node.memory_gb:
        return "memory_insufficient"
    if not node.available:
        return "node_unavailable"
    reserved_gpus, reserved_memory = reserved
    if reserved_gpus + workload.gpu_count > node.gpu_count:
        return (
            "same_decision_gpu_reservation"
            if reserved_gpus > node.allocated_gpus
            else "temporary_gpu_capacity_contention"
        )
    if reserved_memory + workload.memory_gb > node.memory_gb:
        return (
            "same_decision_memory_reservation"
            if reserved_memory > node.allocated_memory_gb
            else "temporary_memory_capacity_contention"
        )
    standalone_node_power = node.idle_kw + node.per_gpu_kw * workload.gpu_count
    if standalone_node_power > node.power_limit_kw:
        return "node_power_limit"
    projected_node_power = node.idle_kw + node.per_gpu_kw * (
        reserved_gpus + workload.gpu_count
    )
    if projected_node_power > node.power_limit_kw:
        return (
            "same_decision_node_power_reservation"
            if reserved_gpus > node.allocated_gpus
            else "node_power_contention"
        )
    if (
        projected_power + node.per_gpu_kw * workload.gpu_count
        > sim.power_budget_kw
    ):
        return "facility_power_reservation" if projected_power > sim.estimated_total_power_kw() else "facility_power_contention"
    return None


def _skip_diagnostic(
    sim: DatacenterSimulator,
    workload: Workload,
    reserved: dict[str, list[int]],
    projected_power: float,
    *,
    reason_override: str | None = None,
) -> dict[str, Any]:
    node_reasons = {
        node.id: _node_reason(
            sim, workload, node, reserved[node.id], projected_power
        )
        for node in sim.nodes
    }
    eligible_nodes = [
        node
        for node in sim.nodes
        if (
            workload.required_gpu_model is None
            or workload.required_gpu_model == node.gpu_model
        )
        and workload.gpu_count <= node.gpu_count
        and workload.memory_gb <= node.memory_gb
        and node.idle_kw + node.per_gpu_kw * workload.gpu_count
        <= node.power_limit_kw
    ]
    applicable = [node_reasons[node.id] for node in eligible_nodes]
    if reason_override:
        reason = reason_override
    elif eligible_nodes and all(reason == "node_unavailable" for reason in applicable):
        reason = "node_failure_recovery"
    elif any(
        reason
        in {
            "same_decision_gpu_reservation",
            "same_decision_memory_reservation",
            "same_decision_node_power_reservation",
            "facility_power_reservation",
        }
        for reason in applicable
    ):
        reason = "same_decision_reservation_contention"
    elif any(
        reason
        in {
            "temporary_gpu_capacity_contention",
            "temporary_memory_capacity_contention",
        }
        for reason in applicable
    ):
        reason = "temporary_capacity_contention"
    elif any(
        reason
        in {
            "node_power_contention",
            "facility_power_contention",
            "node_power_limit",
        }
        for reason in applicable
    ):
        reason = "power_constrained_waiting"
    else:
        reason = "scheduler_deferral"
    return {
        "workload_id": workload.id,
        "reason": reason,
        "node_reasons": node_reasons,
        "step": sim.step_count,
    }


def schedule_with_diagnostics(
    sim: DatacenterSimulator,
    policy: PolicyName | str = "resource_aware",
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    pending = _ordered_pending(sim, policy)
    reserved = {
        node.id: [node.allocated_gpus, node.allocated_memory_gb]
        for node in sim.nodes
    }
    projected_power = sim.estimated_total_power_kw()
    assignments: dict[str, str] = {}
    diagnostics: list[dict[str, Any]] = []
    for workload in pending:
        options = []
        for node in sim.nodes:
            if _node_reason(
                sim, workload, node, reserved[node.id], projected_power
            ) is None:
                fill = (reserved[node.id][0] + workload.gpu_count) / node.gpu_count
                power_delta = node.per_gpu_kw * workload.gpu_count
                options.append((fill, node.id, power_delta))
        if not options:
            diagnostics.append(
                _skip_diagnostic(sim, workload, reserved, projected_power)
            )
            continue
        _, node_id, power_delta = max(options, key=lambda option: (option[0], option[1]))
        node = next(node for node in sim.nodes if node.id == node_id)
        reserved[node_id][0] += workload.gpu_count
        reserved[node_id][1] += workload.memory_gb
        projected_power += power_delta
        assignments[workload.id] = node.id
    return assignments, diagnostics


def diagnose_unassigned(
    sim: DatacenterSimulator,
    assigned_workloads: set[str],
    *,
    reason: str,
) -> list[dict[str, Any]]:
    reserved = {
        node.id: [node.allocated_gpus, node.allocated_memory_gb]
        for node in sim.nodes
    }
    projected_power = sim.estimated_total_power_kw()
    return [
        _skip_diagnostic(
            sim,
            workload,
            reserved,
            projected_power,
            reason_override=reason,
        )
        for workload in sim.workloads
        if workload.status == "pending"
        and workload.submitted
        and workload.id not in assigned_workloads
    ]


def schedule(
    sim: DatacenterSimulator,
    policy: PolicyName | str = "resource_aware",
) -> dict[str, str]:
    return schedule_with_diagnostics(sim, policy)[0]


def nemotron_propose(state: dict) -> dict[str, str]:
    """Compatibility helper for callers expecting a proposal mapping."""
    from .nemotron import request_proposal

    return request_proposal(state).assignments
