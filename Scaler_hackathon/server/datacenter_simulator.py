"""Seeded, discrete-time data-centre simulator; power is illustrative only."""
from __future__ import annotations

import math
import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any

from .metrics import calculate_metrics


@dataclass
class Node:
    id: str
    gpu_count: int
    memory_gb: int
    power_limit_kw: float
    idle_kw: float = 0.2
    per_gpu_kw: float = 0.65
    gpu_model: str = "NVIDIA A100"
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
        if not self.gpu_model:
            raise ValueError("GPU model must be provided")

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
    submission_time: int = 0
    status: str = "pending"
    node_id: str | None = None
    remaining: int | None = None
    started_at: int | None = None
    completed_at: int | None = None
    failure_count: int = 0
    max_retries: int = 2
    submitted: bool = True
    completed_work_units: int = 0
    required_gpu_model: str | None = None
    workload_class: str = "general"

    def __post_init__(self) -> None:
        if (
            not self.id
            or not self.name
            or self.gpu_count < 1
            or self.memory_gb < 1
            or self.duration < 1
            or self.priority < 1
            or self.submission_time < 0
            or self.max_retries < 0
        ):
            raise ValueError(
                "Workload identity, resources, duration, priority, and arrival must be valid"
            )
        if self.deadline is not None and self.deadline < 0:
            raise ValueError("Workload deadline must be non-negative")
        if self.required_gpu_model is not None and not self.required_gpu_model:
            raise ValueError("Required GPU model must be a non-empty string")
        if not self.workload_class:
            raise ValueError("Workload class must be a non-empty string")
        if self.remaining is None:
            self.remaining = self.duration
        if not 0 <= self.remaining <= self.duration:
            raise ValueError("Workload remaining duration is outside its valid range")
        if self.status not in {"pending", "running", "completed", "failed", "cancelled"}:
            raise ValueError(f"Unsupported workload status: {self.status}")
        if self.submission_time > 0 and self.submitted:
            raise ValueError("A future workload cannot be submitted before its arrival time")


DEFAULT_NODES = (
    {"id": "gpu-a", "gpu_count": 4, "memory_gb": 80, "power_limit_kw": 3.5, "gpu_model": "NVIDIA A100"},
    {"id": "gpu-b", "gpu_count": 4, "memory_gb": 48, "power_limit_kw": 3.0, "gpu_model": "NVIDIA L40S"},
    {"id": "gpu-c", "gpu_count": 2, "memory_gb": 24, "power_limit_kw": 1.8, "gpu_model": "NVIDIA T4"},
)

DEFAULT_WORKLOADS = (
    {"id": "train-001", "name": "Fine-tune model", "gpu_count": 2, "memory_gb": 40, "duration": 5, "priority": 3, "deadline": 8},
    {"id": "infer-001", "name": "Inference batch", "gpu_count": 1, "memory_gb": 12, "duration": 2, "priority": 5, "deadline": 4},
    {"id": "embed-001", "name": "Embedding generation", "gpu_count": 1, "memory_gb": 8, "duration": 3, "priority": 2, "deadline": 7},
    {"id": "train-002", "name": "Training run", "gpu_count": 4, "memory_gb": 40, "duration": 7, "priority": 2, "deadline": 12},
    {"id": "infer-002", "name": "Latency-sensitive inference", "gpu_count": 1, "memory_gb": 16, "duration": 2, "priority": 5, "deadline": 5},
    {"id": "eval-001", "name": "Model evaluation", "gpu_count": 2, "memory_gb": 24, "duration": 4, "priority": 1, "deadline": 10},
)


class DatacenterSimulator:
    """Capacity-checked simulator with one-minute ticks and reproducible events."""

    def __init__(
        self,
        seed: int = 7,
        power_budget_kw: float = 20.0,
        failure_probability: float = 0.0,
        *,
        nodes: Iterable[Node | dict[str, Any]] | None = None,
        workloads: Iterable[Workload | dict[str, Any]] | None = None,
        recovery_steps: int = 1,
        energy_price_per_kwh: float = 0.08,
    ):
        if not math.isfinite(power_budget_kw) or power_budget_kw <= 0:
            raise ValueError("Power budget must be finite and positive")
        if not math.isfinite(failure_probability) or not 0 <= failure_probability <= 1:
            raise ValueError("Failure probability must be between 0 and 1")
        if recovery_steps < 1:
            raise ValueError("Node recovery must take at least one step")
        if not math.isfinite(energy_price_per_kwh) or energy_price_per_kwh < 0:
            raise ValueError("Energy price must be finite and non-negative")
        self.seed = seed
        self.rng = random.Random(seed)
        self.failure_rng = random.Random(seed ^ 0x5F3759DF)
        self.failure_node_rng = random.Random(seed ^ 0x6C8E9CF5)
        self.power_budget_kw = power_budget_kw
        self.failure_probability = failure_probability
        self.recovery_steps = recovery_steps
        self.energy_price_per_kwh = energy_price_per_kwh
        self.nodes = [
            value if isinstance(value, Node) else Node(**value)
            for value in (nodes if nodes is not None else DEFAULT_NODES)
        ]
        self.workloads = [
            value if isinstance(value, Workload) else Workload(**value)
            for value in (workloads if workloads is not None else DEFAULT_WORKLOADS)
        ]
        self._node_specs = [
            {
                key: value
                for key, value in asdict(node).items()
                if key
                in {
                    "id",
                    "gpu_count",
                    "memory_gb",
                    "power_limit_kw",
                    "idle_kw",
                    "per_gpu_kw",
                    "gpu_model",
                    "available",
                }
            }
            for node in self.nodes
        ]
        self._workload_specs = [asdict(workload) for workload in self.workloads]
        if not self.nodes or not self.workloads:
            raise ValueError("At least one node and one workload are required")
        if len({node.id for node in self.nodes}) != len(self.nodes):
            raise ValueError("Node ids must be unique")
        if len({workload.id for workload in self.workloads}) != len(self.workloads):
            raise ValueError("Workload ids must be unique")
        if sum(node.idle_kw for node in self.nodes) > power_budget_kw:
            raise ValueError("Power budget is below combined node idle power")
        self.step_count = 0
        self.energy_kwh = 0.0
        self.history: list[dict[str, Any]] = []
        self.gpu_utilization_samples: list[float] = []
        self.memory_utilization_samples: list[float] = []
        self.ai_latencies_ms: list[float] = []
        self.model_cost: float | None = None
        self.model_cost_basis = "not_available"
        self.counters = {
            "rejected_actions": 0,
            "resource_rejections": 0,
            "power_budget_violations": 0,
            "node_failures": 0,
            "node_recoveries": 0,
            "workloads_requeued": 0,
            "workloads_preempted": 0,
            "ai_invocations": 0,
            "ai_attempts": 0,
            "ai_failures": 0,
            "ai_fallbacks": 0,
            "ai_invalid_proposals": 0,
            "ai_prompt_tokens": 0,
            "ai_completion_tokens": 0,
        }
        self._allocations()

    def _allocations(self) -> None:
        for node in self.nodes:
            node.allocated_gpus = 0
            node.allocated_memory_gb = 0
            node.workloads = []
        for workload in self.workloads:
            if workload.status == "running" and workload.node_id:
                node = next(
                    (
                        item
                        for item in self.nodes
                        if item.id == workload.node_id and item.available
                    ),
                    None,
                )
                if node:
                    node.allocated_gpus += workload.gpu_count
                    node.allocated_memory_gb += workload.memory_gb
                    node.workloads.append(workload.id)

    def estimated_total_power_kw(self) -> float:
        return sum(node.power_kw for node in self.nodes)

    def reset(self, seed: int | None = None) -> dict[str, Any]:
        self.__init__(
            self.seed if seed is None else seed,
            self.power_budget_kw,
            self.failure_probability,
            nodes=self._node_specs,
            workloads=self._workload_specs,
            recovery_steps=self.recovery_steps,
            energy_price_per_kwh=self.energy_price_per_kwh,
        )
        return self.state()

    def activate_arrivals(self) -> list[str]:
        arrived = []
        for workload in self.workloads:
            if not workload.submitted and workload.submission_time <= self.step_count:
                workload.submitted = True
                arrived.append(workload.id)
        return arrived

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
        projected_power = self.estimated_total_power_kw()
        rejected: list[dict[str, str]] = []
        seen: set[str] = set()

        for workload_id, node_id in assignments.items():
            workload = workloads.get(workload_id)
            node = nodes.get(node_id)
            reason = None
            if workload_id in seen:
                reason = "duplicate_workload"
            elif workload is None or workload.status != "pending" or not workload.submitted:
                reason = "unknown_or_not_eligible"
            elif node is None:
                reason = "unknown_node"
            elif (
                workload.required_gpu_model is not None
                and workload.required_gpu_model != node.gpu_model
            ):
                reason = "incompatible_gpu_model"
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
            seen.add(workload_id)
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
        cancel: list[str] | None = None,
    ) -> dict[str, Any]:
        assignments, preempt, cancel = assignments or {}, preempt or [], cancel or []
        if (
            not isinstance(assignments, dict)
            or not isinstance(preempt, list)
            or not isinstance(cancel, list)
        ):
            raise TypeError("Assignments must be a mapping; preempt and cancel must be lists")
        if (
            any(not isinstance(key, str) or not isinstance(value, str) for key, value in assignments.items())
            or any(not isinstance(item, str) for item in preempt + cancel)
        ):
            raise TypeError("Workload and node ids must be strings")

        by_id = {workload.id: workload for workload in self.workloads}
        rejected: list[dict[str, str]] = []
        events: list[dict[str, str]] = self.activate_arrivals()
        for node in self.nodes:
            if node.recover_at_step is not None and node.recover_at_step <= self.step_count:
                node.available = True
                node.recover_at_step = None
                self.counters["node_recoveries"] += 1
                events.append({"type": "node_recovered", "node_id": node.id})

        for workload_id in cancel:
            workload = by_id.get(workload_id)
            if workload and workload.status == "pending":
                workload.status = "cancelled"
                events.append({"type": "workload_cancelled", "workload_id": workload_id})
            else:
                rejected.append({"workload_id": workload_id, "reason": "unknown_or_not_pending"})

        for workload_id in preempt:
            workload = by_id.get(workload_id)
            if workload and workload.status == "running":
                workload.status, workload.node_id = "pending", None
                self.counters["workloads_preempted"] += 1
                events.append({"type": "workload_preempted", "workload_id": workload_id})
            else:
                rejected.append({"workload_id": workload_id, "reason": "unknown_or_not_running"})

        self._allocations()
        assignment_rejections = self.validate_assignments(assignments)
        rejected.extend(assignment_rejections)
        rejected_ids = {item["workload_id"] for item in assignment_rejections}
        for workload_id, node_id in assignments.items():
            if workload_id in rejected_ids:
                continue
            workload = by_id[workload_id]
            workload.status, workload.node_id = "running", node_id
            if workload.started_at is None:
                workload.started_at = self.step_count
            events.append(
                {"type": "workload_started", "workload_id": workload_id, "node_id": node_id}
            )
        self._allocations()

        if (
            self.failure_probability
            and self.failure_rng.random() < self.failure_probability
        ):
            active = [node for node in self.nodes if node.available]
            if active:
                failed_node = self.failure_node_rng.choice(active)
                failed_node.available = False
                failed_node.recover_at_step = self.step_count + self.recovery_steps
                self.counters["node_failures"] += 1
                events.append({"type": "node_failed", "node_id": failed_node.id})
                for workload in self.workloads:
                    if workload.node_id == failed_node.id and workload.status == "running":
                        workload.failure_count += 1
                        workload.node_id = None
                        if workload.failure_count > workload.max_retries:
                            workload.status = "failed"
                            events.append(
                                {"type": "workload_failed", "workload_id": workload.id}
                            )
                        else:
                            workload.status = "pending"
                            self.counters["workloads_requeued"] += 1
                            events.append(
                                {"type": "workload_requeued", "workload_id": workload.id}
                            )
        self._allocations()

        step_power_kw = self.estimated_total_power_kw()
        used_gpus = sum(node.allocated_gpus for node in self.nodes)
        used_memory = sum(node.allocated_memory_gb for node in self.nodes)
        self.gpu_utilization_samples.append(
            used_gpus / sum(node.gpu_count for node in self.nodes)
        )
        self.memory_utilization_samples.append(
            used_memory / sum(node.memory_gb for node in self.nodes)
        )
        for workload in self.workloads:
            if workload.status == "running":
                workload.remaining = max(0, int(workload.remaining or 0) - 1)
                workload.completed_work_units += 1
                if workload.remaining == 0:
                    workload.status = "completed"
                    workload.completed_at = self.step_count + 1
                    workload.node_id = None
                    events.append(
                        {"type": "workload_completed", "workload_id": workload.id}
                    )

        self.energy_kwh += step_power_kw / 60
        self.step_count += 1
        self._allocations()
        self.counters["rejected_actions"] += len(rejected)
        self.counters["resource_rejections"] += sum(
            item["reason"]
            in {
                "insufficient_or_unavailable_resources",
                "node_power_limit_exceeded",
                "power_budget_exceeded",
            }
            for item in rejected
        )
        self.counters["power_budget_violations"] += sum(
            item["reason"] == "power_budget_exceeded" for item in rejected
        )
        result = self.state()
        result.update({"rejected_actions": rejected, "events": events})
        self.history.append(result)
        return result

    def state(self) -> dict[str, Any]:
        result = {
            "step": self.step_count,
            "seed": self.seed,
            "power_budget_kw": self.power_budget_kw,
            "nodes": [
                asdict(node)
                | {
                    "utilization": round(node.allocated_gpus / node.gpu_count, 4),
                    "memory_utilization": round(
                        node.allocated_memory_gb / node.memory_gb, 4
                    ),
                    "estimated_power_kw": round(node.power_kw, 3),
                }
                for node in self.nodes
            ],
            "workloads": [asdict(workload) for workload in self.workloads],
        }
        result["metrics"] = calculate_metrics(self)
        result["queue_depth"] = result["metrics"]["queued_workloads"]
        return result
