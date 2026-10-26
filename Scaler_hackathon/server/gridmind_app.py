"""Separate GridMind API; the legacy energy-grid app is left untouched."""
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

from .datacenter_simulator import DatacenterSimulator
from .workload_scheduler import nemotron_propose, schedule


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="GridMind Data-Centre Operations API",
    version="0.1.0",
    description="Simulation-only GPU scheduling. Power values are estimates, not telemetry.",
    lifespan=lifespan,
)
sim = DatacenterSimulator()


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: dict[StrictStr, StrictStr] = Field(default_factory=dict)
    preempt: list[StrictStr] = Field(default_factory=list)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: StrictInt | None = None


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: Literal["fifo", "priority", "resource_aware", "nemotron"] = "resource_aware"
    steps: StrictInt = Field(default=1, ge=1, le=100)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gridmind", "mode": "simulation-only"}


@app.get("/state")
def state() -> dict[str, Any]:
    return sim.state()


@app.get("/policies")
def policies() -> dict[str, Any]:
    return {
        "policies": [
            {"id": "fifo", "description": "FIFO baseline"},
            {"id": "priority", "description": "Priority and deadline ordering"},
            {
                "id": "resource_aware",
                "description": "Priority/deadline and resource-fit packing",
            },
            {
                "id": "nemotron",
                "description": "Nebius Nemotron proposal with deterministic fallback",
            },
        ],
        "model_configured": bool(
            os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")
        ),
        "power_is_estimated": True,
    }


@app.post("/reset")
def reset(req: ResetRequest) -> dict[str, Any]:
    return sim.reset(req.seed)


@app.post("/step")
def step(req: StepRequest) -> dict[str, Any]:
    return sim.apply_action(req.assignments, req.preempt)


@app.post("/run")
def run(req: RunRequest) -> dict[str, Any]:
    history = []
    for _ in range(req.steps):
        used_fallback = False
        if req.policy == "nemotron":
            proposed = nemotron_propose(sim.state())
            if (
                (any(w.status == "pending" for w in sim.workloads) and not proposed)
                or sim.validate_assignments(proposed)
            ):
                proposed = schedule(sim, "resource_aware")
                used_fallback = True
        else:
            proposed = schedule(sim, req.policy)

        result = sim.apply_action(proposed)
        result["decision"] = (
            "resource_aware_fallback" if used_fallback else req.policy
        )
        history.append(result)
        if not any(w.status in {"pending", "running"} for w in sim.workloads):
            break

    return {
        "policy": req.policy,
        "steps_executed": len(history),
        "fallback_used": any(
            item["decision"] == "resource_aware_fallback" for item in history
        ),
        "final_state": sim.state(),
        "history": history,
    }
