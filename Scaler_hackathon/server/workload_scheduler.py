"""Deterministic schedulers and the optional constrained Nemotron policy."""
from __future__ import annotations

from typing import Literal

from .datacenter_simulator import DatacenterSimulator

PolicyName = Literal["fifo", "priority", "resource_aware"]


def schedule(
    sim: DatacenterSimulator,
    policy: PolicyName | str = "resource_aware",
) -> dict[str, str]:
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

    reserved = {
        node.id: [node.allocated_gpus, node.allocated_memory_gb]
        for node in sim.nodes
    }
    projected_power = sim.estimated_total_power_kw()
    assignments: dict[str, str] = {}
    for workload in pending:
        options = []
        for node in sim.nodes:
            gpu_count, memory_gb = reserved[node.id]
            projected_node_power = (
                node.idle_kw + node.per_gpu_kw * (gpu_count + workload.gpu_count)
            )
            power_delta = node.per_gpu_kw * workload.gpu_count
            if (
                node.available
                and (
                    workload.required_gpu_model is None
                    or workload.required_gpu_model == node.gpu_model
                )
                and gpu_count + workload.gpu_count <= node.gpu_count
                and memory_gb + workload.memory_gb <= node.memory_gb
                and projected_node_power <= node.power_limit_kw
                and projected_power + power_delta <= sim.power_budget_kw
            ):
                fill = (gpu_count + workload.gpu_count) / node.gpu_count
                options.append((fill, node.id, power_delta))
        if options:
            _, node_id, power_delta = max(options, key=lambda option: (option[0], option[1]))
            node = next(node for node in sim.nodes if node.id == node_id)
            reserved[node_id][0] += workload.gpu_count
            reserved[node_id][1] += workload.memory_gb
            projected_power += power_delta
            assignments[workload.id] = node.id
    return assignments


def nemotron_propose(state: dict) -> dict[str, str]:
    """Compatibility helper for callers expecting a proposal mapping."""
    from .nemotron import request_proposal

    return request_proposal(state).assignments
