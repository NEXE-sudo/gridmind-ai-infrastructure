"""Deterministic simulation-only GPU data-centre environment."""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Node:
    id: str
    gpu_count: int
    memory_gb: int
    power_limit_kw: float
    idle_kw: float = 0.2
    per_gpu_kw: float = 0.65
    available: bool = True
    allocated_gpus: int = 0
    allocated_memory_gb: int = 0
    workloads: list[str] = field(default_factory=list)
    recover_at_step: int | None = None

    def __post_init__(self) -> None:
        if not self.id or self.gpu_count < 1 or self.memory_gb < 1:
            raise ValueError("Node id, GPU capacity, and memory capacity must be positive")
        if any(
            not math.isfinite(value) or value < 0
            for value in (self.power_limit_kw, self.idle_kw, self.per_gpu_kw)
        ):
            raise ValueError("Node power values must be finite and non-negative")
        if self.idle_kw > self.power_limit_kw:
            raise ValueError("Node idle power cannot exceed its power limit")

    @property
    def power_kw(self) -> float:
        return (
            self.idle_kw + self.per_gpu_kw * self.allocated_gpus
            if self.available
            else 0.0
        )

@dataclass
class Workload:
    id: str
    name: str
    gpu_count: int
    memory_gb: int
    duration: int
    priority: int = 1
    deadline: int | None = None
    status: str = "pending"
    node_id: str | None = None
    remaining: int | None = None
    started_at: int | None = None
    completed_at: int | None = None

    def __post_init__(self) -> None:
        if (
            not self.id
            or not self.name
            or self.gpu_count < 1
            or self.memory_gb < 1
            or self.duration < 1
            or self.priority < 1
        ):
            raise ValueError("Workload identity, resources, duration, and priority must be positive")
        if self.deadline is not None and self.deadline < 0:
            raise ValueError("Workload deadline must be non-negative")
        if self.remaining is None: self.remaining = self.duration
        if self.remaining < 0 or self.remaining > self.duration:
            raise ValueError("Workload remaining duration is outside its valid range")
        if self.status not in {"pending", "running", "completed"}:
            raise ValueError(f"Unsupported workload status: {self.status}")

class DatacenterSimulator:
    """Capacity-checked scheduler sandbox; each tick represents one minute."""
    def __init__(
        self,
        seed: int = 7,
        power_budget_kw: float = 20.0,
        failure_probability: float = 0.15,
    ):
        if not math.isfinite(power_budget_kw) or power_budget_kw < 0:
            raise ValueError("Power budget must be finite and non-negative")
        if not math.isfinite(failure_probability) or not 0 <= failure_probability <= 1:
            raise ValueError("Failure probability must be between 0 and 1")
        self.seed, self.rng = seed, random.Random(seed)
        self.power_budget_kw = power_budget_kw
        self.failure_probability = failure_probability
        self.nodes = [Node("gpu-a",4,80,3.5), Node("gpu-b",4,48,3.0), Node("gpu-c",2,24,1.8)]
        specs = [
            ("train-001","Fine-tune model",2,40,5,3,8),
            ("infer-001","Inference batch",1,12,2,5,4),
            ("embed-001","Embedding generation",1,8,3,2,7),
            ("train-002","Training run",4,40,7,2,12),
            ("infer-002","Latency-sensitive inference",1,16,2,5,5),
            ("eval-001","Model evaluation",2,24,4,1,10),
        ]
        self.workloads = [Workload(i,n,g,m,d,p,deadline) for i,n,g,m,d,p,deadline in specs]
        if len({node.id for node in self.nodes}) != len(self.nodes):
            raise ValueError("Node ids must be unique")
        if len({workload.id for workload in self.workloads}) != len(self.workloads):
            raise ValueError("Workload ids must be unique")
        self.step_count, self.energy_kwh = 0, 0.0
        self.history: list[dict[str, Any]] = []
        self._allocations()

    def _allocations(self) -> None:
        for n in self.nodes:
            n.allocated_gpus, n.allocated_memory_gb, n.workloads = 0, 0, []
        for w in self.workloads:
            if w.status == "running" and w.node_id:
                n = next((x for x in self.nodes if x.id == w.node_id and x.available), None)
                if n:
                    n.allocated_gpus += w.gpu_count
                    n.allocated_memory_gb += w.memory_gb
                    n.workloads.append(w.id)

    def reset(self, seed: int | None = None):
        self.__init__(
            self.seed if seed is None else seed,
            self.power_budget_kw,
            self.failure_probability,
        )
        return self.state()

    def validate_assignments(self, assignments: dict[str, str]) -> list[dict[str, str]]:
        if not isinstance(assignments, dict) or any(
            not isinstance(workload_id, str) or not isinstance(node_id, str)
            for workload_id, node_id in assignments.items()
        ):
            raise TypeError("Assignments must map workload ids to node ids")

        workloads = {workload.id: workload for workload in self.workloads}
        nodes = {node.id: node for node in self.nodes}
        reserved = {
            node.id: [node.allocated_gpus, node.allocated_memory_gb]
            for node in self.nodes
        }
        projected_power = sum(node.power_kw for node in self.nodes)
        rejected: list[dict[str, str]] = []

        for workload_id, node_id in assignments.items():
            workload = workloads.get(workload_id)
            node = nodes.get(node_id)
            reason = None
            if workload is None or workload.status != "pending":
                reason = "unknown_or_not_pending"
            elif node is None:
                reason = "unknown_node"
            else:
                gpu_count, memory_gb = reserved[node.id]
                if (
                    not node.available
                    or gpu_count + workload.gpu_count > node.gpu_count
                    or memory_gb + workload.memory_gb > node.memory_gb
                ):
                    reason = "insufficient_or_unavailable_resources"
                elif (
                    node.idle_kw
                    + node.per_gpu_kw * (gpu_count + workload.gpu_count)
                    > node.power_limit_kw
                ):
                    reason = "node_power_limit_exceeded"
                elif (
                    projected_power + node.per_gpu_kw * workload.gpu_count
                    > self.power_budget_kw
                ):
                    reason = "power_budget_exceeded"
            if reason:
                rejected.append({"workload_id": workload_id, "reason": reason})
                continue

            reserved[node.id][0] += workload.gpu_count
            reserved[node.id][1] += workload.memory_gb
            projected_power += node.per_gpu_kw * workload.gpu_count
        return rejected

    def apply_action(
        self,
        assignments: dict[str, str] | None = None,
        preempt: list[str] | None = None,
    ) -> dict[str, Any]:
        assignments, preempt = assignments or {}, preempt or []
        if not isinstance(assignments, dict) or not isinstance(preempt, list):
            raise TypeError("Assignments must be a mapping and preempt must be a list")
        if any(
            not isinstance(workload_id, str) or not isinstance(node_id, str)
            for workload_id, node_id in assignments.items()
        ) or any(not isinstance(workload_id, str) for workload_id in preempt):
            raise TypeError("Workload and node ids must be strings")
        by_id = {w.id:w for w in self.workloads}
        rejected: list[dict[str, str]] = []
        events: list[dict[str, str]] = []

        for node in self.nodes:
            if node.recover_at_step is not None and node.recover_at_step <= self.step_count:
                node.available = True
                node.recover_at_step = None

        for wid in preempt:
            w = by_id.get(wid)
            if w and w.status == "running":
                w.status, w.node_id = "pending", None
            else:
                rejected.append({"workload_id": wid, "reason": "unknown_or_not_running"})
        self._allocations()
        assignment_rejections = self.validate_assignments(assignments)
        rejected.extend(assignment_rejections)
        rejected_ids = {item["workload_id"] for item in assignment_rejections}
        for wid, nid in assignments.items():
            if wid in rejected_ids:
                continue
            w = by_id[wid]
            w.status, w.node_id = "running", nid
            if w.started_at is None:
                w.started_at = self.step_count
            self._allocations()
        # A seeded, one-step simulated fault; it is not a physical reliability model.
        if (
            self.step_count
            and self.step_count % 11 == 0
            and self.rng.random() < self.failure_probability
        ):
            active = [n for n in self.nodes if n.available]
            if active:
                failed = self.rng.choice(active)
                failed.available = False
                failed.recover_at_step = self.step_count + 1
                events.append({"type": "node_failed", "node_id": failed.id})
                for w in self.workloads:
                    if w.node_id == failed.id and w.status == "running":
                        w.status, w.node_id = "pending", None
                        events.append({"type": "workload_requeued", "workload_id": w.id})
        self._allocations()
        step_power_kw = sum(n.power_kw for n in self.nodes)
        for w in self.workloads:
            if w.status == "running":
                w.remaining = max(0, int(w.remaining or 0)-1)
                if w.remaining == 0:
                    w.status, w.completed_at, w.node_id = "completed", self.step_count+1, None
        self.step_count += 1
        self._allocations()
        self.energy_kwh += step_power_kw / 60.0
        result = self.state()
        result["rejected_actions"] = rejected
        result["events"] = events
        self.history.append(result)
        return result

    def state(self) -> dict[str, Any]:
        total_gpus = sum(n.gpu_count for n in self.nodes)
        allocated = sum(n.allocated_gpus for n in self.nodes)
        power = sum(n.power_kw for n in self.nodes)
        completed = [w for w in self.workloads if w.status == "completed"]
        return {
            "step": self.step_count, "seed": self.seed, "power_budget_kw": self.power_budget_kw,
            "nodes": [asdict(n)|{"utilization":round(n.allocated_gpus/n.gpu_count,4),"estimated_power_kw":round(n.power_kw,3)} for n in self.nodes],
            "workloads": [asdict(w) for w in self.workloads],
            "metrics": {"completed_workloads":len(completed),"deadline_misses":sum(w.deadline is not None and w.completed_at is not None and w.completed_at>w.deadline for w in completed),
                        "gpu_utilization":round(allocated/total_gpus,4) if total_gpus else 0.0,
                        "estimated_energy_kwh":round(self.energy_kwh,5),"estimated_power_kw":round(power,3),
                        "power_limit_kw":self.power_budget_kw,"queue_depth":sum(w.status=="pending" for w in self.workloads)}
        }
