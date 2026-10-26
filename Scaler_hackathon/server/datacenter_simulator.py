"""Deterministic simulation-only GPU data-centre environment."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
import random

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
    @property
    def power_kw(self) -> float:
        return 0.0 if not self.available else min(self.power_limit_kw, self.idle_kw + self.per_gpu_kw*self.allocated_gpus)

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
    def __post_init__(self):
        if self.remaining is None: self.remaining = self.duration

class DatacenterSimulator:
    """Capacity-checked scheduler sandbox; each tick represents one minute."""
    def __init__(self, seed: int = 7, power_budget_kw: float = 20.0):
        self.seed, self.rng = seed, random.Random(seed)
        self.power_budget_kw = power_budget_kw
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
        self.step_count, self.energy_kwh = 0, 0.0
        self.history: list[dict[str, Any]] = []
        self._allocations()

    def _allocations(self):
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
        self.__init__(self.seed if seed is None else seed, self.power_budget_kw)
        return self.state()

    def apply_action(self, assignments: dict[str,str] | None = None, preempt: list[str] | None = None):
        assignments, preempt = assignments or {}, preempt or []
        by_id = {w.id:w for w in self.workloads}
        rejected = []
        for wid in preempt:
            w = by_id.get(wid)
            if w and w.status == "running":
                w.status, w.node_id, w.remaining = "pending", None, w.duration
        self._allocations()
        for wid,nid in assignments.items():
            w, n = by_id.get(wid), next((x for x in self.nodes if x.id == nid), None)
            reason = None
            if not w or w.status != "pending": reason = "unknown_or_not_pending"
            elif not n: reason = "unknown_node"
            elif not n.available or n.allocated_gpus+w.gpu_count > n.gpu_count or n.allocated_memory_gb+w.memory_gb > n.memory_gb: reason = "insufficient_or_unavailable_resources"
            elif sum(x.power_kw for x in self.nodes)+n.per_gpu_kw*w.gpu_count > self.power_budget_kw: reason = "power_budget_exceeded"
            if reason:
                rejected.append({"workload_id":wid,"reason":reason}); continue
            w.status, w.node_id, w.started_at = "running", n.id, self.step_count
            self._allocations()
        # A seeded, short-lived simulated fault; not a physical reliability model.
        if self.step_count and self.step_count % 11 == 0 and self.rng.random() < 0.15:
            active = [n for n in self.nodes if n.available]
            if active:
                failed = self.rng.choice(active); failed.available = False
                for w in self.workloads:
                    if w.node_id == failed.id and w.status == "running":
                        w.status, w.node_id, w.remaining = "pending", None, w.duration
        self._allocations()
        for w in self.workloads:
            if w.status == "running":
                w.remaining = max(0, int(w.remaining or 0)-1)
                if w.remaining == 0:
                    w.status, w.completed_at, w.node_id = "completed", self.step_count+1, None
        for n in self.nodes: n.available = True
        self.step_count += 1
        self._allocations()
        self.energy_kwh += sum(n.power_kw for n in self.nodes)/60.0
        result = self.state()
        result["rejected_actions"] = rejected
        self.history.append(result)
        return result

    def state(self):
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
