"""Single-session GridMind simulation and experiment API."""
from __future__ import annotations

import copy
import csv
import os
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from .benchmarks import load_config, make_seeded_scenario, run_experiments
from .datacenter_simulator import DatacenterSimulator
from .decision import POLICIES, execute_policy_step

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "demo.json"
operation_lock = threading.Lock()
recent_runs: list[dict[str, Any]] = []
latest_benchmark: dict[str, Any] | None = None
SCENARIOS = ("standard", "workload_surge", "node_failure", "tight_deadlines")


def create_simulator(seed: int, scenario_name: str) -> DatacenterSimulator:
    config = load_config(DEFAULT_CONFIG)
    if scenario_name not in SCENARIOS:
        raise ValueError(f"scenario must be one of {', '.join(SCENARIOS)}")
    if scenario_name == "workload_surge":
        surge_workloads = []
        for workload in config["workloads"]:
            surged = copy.deepcopy(workload)
            surged["id"] = f"{workload['id']}-surge"
            surged["name"] = f"{workload['name']} (surge)"
            surge_workloads.append(surged)
        config["workloads"].extend(surge_workloads)
    elif scenario_name == "tight_deadlines":
        for workload in config["workloads"]:
            workload["deadline_after_minutes"] = max(1, workload["duration"] // 2)

    materialized = make_seeded_scenario(config, seed)
    failure_probability = (
        0.35 if scenario_name == "node_failure" else config["failure_probability"]
    )
    return DatacenterSimulator(
        seed=seed,
        power_budget_kw=config["power_budget_kw"],
        failure_probability=failure_probability,
        nodes=materialized["nodes"],
        workloads=materialized["workloads"],
        recovery_steps=config.get("recovery_steps", 1),
        energy_price_per_kwh=config["energy_price_per_kwh"],
    )


active_scenario = "standard"
sim = create_simulator(42, active_scenario)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="GridMind Data-Centre Operations API",
    version="1.0.0",
    description=(
        "Simulation-only GPU scheduling and reproducible policy experiments. "
        "No real cluster is controlled; power and energy are synthetic estimates."
    ),
    lifespan=lifespan,
)


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: dict[StrictStr, StrictStr] = Field(default_factory=dict)
    preempt: list[StrictStr] = Field(default_factory=list, max_length=100)
    cancel: list[StrictStr] = Field(default_factory=list, max_length=100)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: StrictInt | None = None
    scenario: Literal["standard", "workload_surge", "node_failure", "tight_deadlines"] = "standard"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: Literal["fifo", "priority", "resource_aware", "nemotron"] = "resource_aware"
    steps: StrictInt = Field(default=1, ge=1, le=100)
    use_live_model: StrictBool = False


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seeds: list[StrictInt] = Field(default_factory=lambda: [1, 2, 3], min_length=1, max_length=5)
    policies: list[Literal["fifo", "priority", "resource_aware", "nemotron"]] = Field(
        default_factory=lambda: list(POLICIES), min_length=1, max_length=4
    )
    use_live_model: StrictBool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gridmind", "mode": "simulation-only"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    return {
        "status": "ready",
        "model_configured": bool(
            os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")
        ),
        "active_simulator": True,
        "state_scope": "single-process-single-session",
    }


@app.get("/state")
def state() -> dict[str, Any]:
    with operation_lock:
        return {
            **sim.state(),
            "scenario": active_scenario,
            "failure_probability": sim.failure_probability,
        }


@app.get("/policies")
def policies() -> dict[str, Any]:
    return {
        "policies": [
            {"id": "fifo", "description": "First submitted eligible workload first"},
            {"id": "priority", "description": "Priority, deadline, then arrival order"},
            {
                "id": "resource_aware",
                "description": "Priority/deadline with best-fit node packing",
            },
            {
                "id": "nemotron",
                "description": "Optional NVIDIA Nemotron proposal with deterministic fallback",
            },
        ],
        "model_configured": bool(
            os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")
        ),
        "model_id": os.getenv("GRIDMIND_MODEL"),
        "power_is_estimated": True,
    }


@app.get("/workloads")
def workloads() -> dict[str, Any]:
    with operation_lock:
        return {
            "step": sim.step_count,
            "workloads": sim.state()["workloads"],
            "queue_depth": sim.state()["queue_depth"],
        }


@app.get("/nodes")
def nodes() -> dict[str, Any]:
    with operation_lock:
        return {"step": sim.step_count, "nodes": sim.state()["nodes"]}


@app.post("/reset")
def reset(req: ResetRequest) -> dict[str, Any]:
    global active_scenario, sim
    with operation_lock:
        next_seed = sim.seed if req.seed is None else req.seed
        sim = create_simulator(next_seed, req.scenario)
        active_scenario = req.scenario
        return {
            **sim.state(),
            "scenario": active_scenario,
            "failure_probability": sim.failure_probability,
        }


@app.post("/step")
def step(req: StepRequest) -> dict[str, Any]:
    with operation_lock:
        result = sim.apply_action(req.assignments, req.preempt, req.cancel)
        recent_runs.append(
            {
                "run_id": str(uuid4()),
                "kind": "manual_step",
                "policy": "manual",
                "seed": sim.seed,
                "status": "completed",
                "step": sim.step_count,
                "metrics": result["metrics"],
                "decision": "manual_action",
                "rejected_actions": result["rejected_actions"],
            }
        )
        del recent_runs[:-50]
        return result


@app.post("/run")
def run(req: RunRequest) -> dict[str, Any]:
    if req.use_live_model and req.policy != "nemotron":
        raise HTTPException(422, "use_live_model is only valid for policy=nemotron")
    with operation_lock:
        history = []
        run_id = str(uuid4())
        for _ in range(req.steps):
            result = execute_policy_step(
                sim,
                req.policy,
                use_live_model=req.use_live_model,
            )
            history.append(result)
            if not any(
                workload.status in {"pending", "running"}
                for workload in sim.workloads
            ):
                break
        record = {
            "run_id": run_id,
            "kind": "simulation",
            "policy": req.policy,
            "seed": sim.seed,
            "status": "completed",
            "steps_executed": len(history),
            "metrics": sim.state()["metrics"],
            "fallback_used": any(item["fallback_used"] for item in history),
            "created_at": datetime.now(UTC).isoformat(),
        }
        recent_runs.append(record)
        del recent_runs[:-50]
        return {
            **record,
            "history": history,
            "final_state": sim.state(),
        }


@app.post("/benchmarks/run")
def run_benchmark(req: BenchmarkRequest) -> dict[str, Any]:
    global latest_benchmark
    if len(set(req.seeds)) != len(req.seeds):
        raise HTTPException(422, "seeds must be unique")
    if len(set(req.policies)) != len(req.policies):
        raise HTTPException(422, "policies must be unique")
    if req.use_live_model and "nemotron" not in req.policies:
        raise HTTPException(422, "live model requested but nemotron policy is absent")
    if req.use_live_model and not (
        os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")
    ):
        raise HTTPException(
            422,
            "Live inference requires NEBIUS_API_KEY and a catalogue-verified GRIDMIND_MODEL",
        )
    with operation_lock:
        try:
            config = load_config(DEFAULT_CONFIG)
            latest_benchmark = run_experiments(
                config,
                req.seeds,
                policies=req.policies,
                live_model=req.use_live_model,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        for record in latest_benchmark["runs"]:
            recent_runs.append(
                {
                    "run_id": record["run_id"],
                    "kind": "benchmark",
                    "policy": record["policy"],
                    "seed": record["seed"],
                    "status": record["status"],
                    "metrics": record["metrics"],
                    "scenario_sha256": record["scenario_sha256"],
                    "created_at": latest_benchmark["created_at"],
                }
            )
        del recent_runs[:-50]
        return latest_benchmark


@app.get("/benchmarks/latest")
def benchmark_latest() -> dict[str, Any]:
    if latest_benchmark is None:
        raise HTTPException(404, "No benchmark has been run in this process")
    return latest_benchmark


@app.get("/history")
def history(limit: int = 20) -> dict[str, Any]:
    if not 1 <= limit <= 50:
        raise HTTPException(422, "limit must be between 1 and 50")
    return {"runs": list(reversed(recent_runs[-limit:]))}


@app.get("/exports/latest.csv")
def export_latest_csv() -> Response:
    if latest_benchmark is None:
        raise HTTPException(404, "No benchmark has been run in this process")
    rows = latest_benchmark["runs"]
    output = StringIO()
    metric_fields = sorted(
        {
            key
            for row in rows
            if row["metrics"]
            for key in row["metrics"]
        }
    )
    fields = [
        "run_id",
        "scenario_name",
        "scenario_sha256",
        "policy",
        "seed",
        "status",
        "steps_executed",
        *metric_fields,
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **{key: row.get(key) for key in fields if key in row},
                **(row["metrics"] or {}),
            }
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="gridmind-benchmark.csv"'},
    )


FRONTEND_DIST = ROOT / "agent-grid-view" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="dashboard")


def main() -> None:
    import uvicorn

    uvicorn.run(
        "server.gridmind_app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "7861")),
    )
