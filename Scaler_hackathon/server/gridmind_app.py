"""Single-session GridMind simulation and experiment API."""
from __future__ import annotations

import copy
import csv
import os
import threading
import time
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

from .benchmarks import (
    load_config,
    make_seeded_scenario,
    run_experiments,
    run_scenario_suite,
)
from .datacenter_simulator import DatacenterSimulator
from .decision import POLICIES, execute_policy_step
from .nemotron import (
    configured_base_url,
    configured_inference_timeout_seconds,
    request_proposal,
    verify_catalogue_model,
)
from .scenarios import get_scenario_config, load_scenario_suite

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "demo.json"
operation_lock = threading.Lock()
recent_runs: list[dict[str, Any]] = []
latest_benchmark: dict[str, Any] | None = None
verified_live_model_id: str | None = None
last_verification_model_id: str | None = None
last_verification_status = "not_attempted"
LEGACY_SCENARIOS = ("standard", "workload_surge", "node_failure", "tight_deadlines")
SCENARIO_IDS = tuple(
    item["id"] for item in load_scenario_suite()["scenarios"]
)
SCENARIOS = LEGACY_SCENARIOS + SCENARIO_IDS


def create_simulator(seed: int, scenario_name: str) -> DatacenterSimulator:
    if scenario_name in SCENARIO_IDS:
        config = get_scenario_config(scenario_name, seed)
        materialized = make_seeded_scenario(config, seed)
        return DatacenterSimulator(
            seed=seed,
            power_budget_kw=materialized["power_budget_kw"],
            failure_probability=materialized["failure_probability"],
            nodes=materialized["nodes"],
            workloads=materialized["workloads"],
            recovery_steps=materialized["recovery_steps"],
            energy_price_per_kwh=materialized["energy_price_per_kwh"],
        )
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


active_scenario = "balanced"
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

    assignments: dict[StrictStr, StrictStr] = Field(default_factory=dict, max_length=100)
    preempt: list[StrictStr] = Field(default_factory=list, max_length=100)
    cancel: list[StrictStr] = Field(default_factory=list, max_length=100)


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: StrictInt | None = Field(default=None, ge=0, le=2_147_483_647)
    scenario: Literal[
        "standard",
        "workload_surge",
        "node_failure",
        "tight_deadlines",
        "balanced",
        "burst_arrivals",
        "mixed_priority_deadlines",
        "heterogeneous_gpu_types",
        "gpu_memory_pressure",
        "tight_power_budget",
        "node_failure_recovery",
        "short_long_contention",
        "infeasible_workloads",
        "combined_stress",
    ] = "standard"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: Literal["fifo", "priority", "resource_aware", "nemotron"] = "resource_aware"
    steps: StrictInt = Field(default=1, ge=1, le=100)
    use_live_model: StrictBool = False


class ModelVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_live_request: StrictBool = False


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seeds: list[StrictInt] = Field(default_factory=lambda: [1, 2, 3], min_length=1, max_length=5)
    policies: list[Literal["fifo", "priority", "resource_aware", "nemotron"]] = Field(
        default_factory=lambda: list(POLICIES), min_length=1, max_length=4
    )
    scenario: Literal[
        "balanced",
        "burst_arrivals",
        "mixed_priority_deadlines",
        "heterogeneous_gpu_types",
        "gpu_memory_pressure",
        "tight_power_budget",
        "node_failure_recovery",
        "short_long_contention",
        "infeasible_workloads",
        "combined_stress",
    ] = "balanced"
    use_live_model: StrictBool = False


class ScenarioSuiteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seeds: list[StrictInt] = Field(
        default_factory=lambda: [1], min_length=1, max_length=2
    )
    policies: list[Literal["fifo", "priority", "resource_aware", "nemotron"]] = Field(
        default_factory=lambda: list(POLICIES), min_length=1, max_length=4
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "gridmind", "mode": "simulation-only"}


@app.get("/ready")
def ready() -> dict[str, Any]:
    model_id = os.getenv("GRIDMIND_MODEL")
    configured = bool(os.getenv("NEBIUS_API_KEY") and model_id)
    return {
        "status": "ready",
        "model_configured": configured,
        "model_verification_status": (
            "not_configured"
            if not configured
            else last_verification_status
            if model_id == last_verification_model_id
            else "not_attempted"
        ),
        "active_simulator": True,
        "state_scope": "single-process-single-session",
    }


@app.post("/model/verify")
def verify_live_model(req: ModelVerificationRequest) -> dict[str, Any]:
    global last_verification_model_id, last_verification_status
    global verified_live_model_id
    if not req.confirm_live_request:
        raise HTTPException(
            422, "Set confirm_live_request=true to authorize one real provider request"
        )
    with operation_lock:
        verified_live_model_id = None
        last_verification_model_id = None
        last_verification_status = "not_attempted"
    api_key = os.getenv("NEBIUS_API_KEY")
    model_id = os.getenv("GRIDMIND_MODEL")
    if not api_key or not model_id:
        with operation_lock:
            last_verification_status = "not_configured"
        return {
            "status": "not_configured",
            "catalogue_status": "not_attempted",
            "request_attempts": 0,
        }
    normalized_model_id = model_id.casefold()
    if (
        model_id != model_id.strip()
        or any(ord(char) < 32 for char in model_id)
        or len(model_id) > 200
        or api_key in model_id
        or not normalized_model_id.startswith("nvidia/")
        or "nemotron" not in normalized_model_id
    ):
        with operation_lock:
            if (
                len(model_id) <= 200
                and model_id == model_id.strip()
                and not any(ord(char) < 32 for char in model_id)
                and api_key not in model_id
            ):
                last_verification_model_id = model_id
            last_verification_status = "invalid_model_id"
        return {
            "status": "invalid_model_id",
            "catalogue_status": "not_attempted",
            "request_attempts": 0,
            "error_code": "expected_nvidia_nemotron_id",
        }
    try:
        timeout_seconds = configured_inference_timeout_seconds()
        configured_base_url()
    except ValueError:
        with operation_lock:
            last_verification_model_id = model_id
            last_verification_status = "invalid_configuration"
        return {
            "status": "invalid_configuration",
            "catalogue_status": "not_attempted",
            "request_attempts": 0,
            "error_code": "invalid_provider_configuration",
        }

    with operation_lock:
        last_verification_model_id = model_id
        last_verification_status = "not_attempted"
        catalogue_started = time.perf_counter()
        try:
            catalogue_match = verify_catalogue_model(
                model_id, api_key, timeout=min(timeout_seconds, 10.0)
            )
        except RuntimeError:
            last_verification_status = "live_failure_fallback"
            return {
                "status": "live_failure_fallback",
                "catalogue_status": "failed",
                "model_id": model_id,
                "catalogue_latency_ms": round(
                    (time.perf_counter() - catalogue_started) * 1000, 3
                ),
                "request_attempts": 0,
                "error_code": "catalogue_unavailable",
            }
        catalogue_latency_ms = round(
            (time.perf_counter() - catalogue_started) * 1000, 3
        )
        if not catalogue_match:
            last_verification_status = "invalid_model_id"
            return {
                "status": "invalid_model_id",
                "catalogue_status": "model_not_listed",
                "model_id": model_id,
                "catalogue_latency_ms": catalogue_latency_ms,
                "request_attempts": 0,
            }

        verification_sim = DatacenterSimulator(seed=17)
        proposal = request_proposal(verification_sim.state())
        validation_rejections = (
            verification_sim.validate_assignments(proposal.assignments)
            if proposal.used_model
            else []
        )
        if proposal.used_model and not proposal.assignments:
            validation_rejections.append(
                {"workload_id": "", "reason": "empty_assignments"}
            )
        if proposal.used_model and not validation_rejections:
            status = "live_success"
            verified_live_model_id = model_id
        elif proposal.used_model or proposal.status == "invalid_response":
            status = "invalid_model_proposal"
        else:
            status = "live_failure_fallback"
        last_verification_status = status
        return {
            "status": status,
            "catalogue_status": "verified_exact_match",
            "model_id": proposal.model_id or model_id,
            "catalogue_latency_ms": catalogue_latency_ms,
            "provider_response_received": proposal.response_received,
            "request_attempts": proposal.request_attempts,
            "retry_count": max(0, proposal.request_attempts - 1),
            "latency_ms": proposal.latency_ms,
            "prompt_tokens": proposal.prompt_tokens,
            "completion_tokens": proposal.completion_tokens,
            "error_code": proposal.error_code,
            "validation_rejections": validation_rejections,
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


@app.get("/scenarios")
def scenarios() -> dict[str, Any]:
    suite = load_scenario_suite()
    return {
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "synthetic": True,
        "scenarios": [
            {
                key: item[key]
                for key in (
                    "id",
                    "name",
                    "description",
                    "intended_stress",
                    "topology_id",
                    "power_budget_kw",
                    "failure_probability",
                    "recovery_steps",
                    "max_steps",
                    "horizon_rationale",
                )
            }
            for item in suite["scenarios"]
        ],
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
        sim.horizon_steps = None
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
    if req.use_live_model and os.getenv("GRIDMIND_MODEL") != verified_live_model_id:
        raise HTTPException(
            409,
            "Run POST /model/verify and receive live_success before requesting live inference",
        )
    if req.use_live_model and req.steps > 10:
        raise HTTPException(422, "Live inference is limited to ten simulation steps per request")
    with operation_lock:
        if req.use_live_model and os.getenv("GRIDMIND_MODEL") != verified_live_model_id:
            raise HTTPException(
                409,
                "Live model verification expired before execution; verify again",
            )
        history = []
        run_id = str(uuid4())
        sim.horizon_steps = sim.step_count + req.steps
        for _ in range(req.steps):
            result = execute_policy_step(
                sim,
                req.policy,
                use_live_model=req.use_live_model,
            )
            history.append(result)
        record = {
            "run_id": run_id,
            "kind": "simulation",
            "policy": req.policy,
            "seed": sim.seed,
            "status": "completed",
            "termination_reason": "requested_horizon_reached",
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
    if req.use_live_model and len(req.seeds) != 1:
        raise HTTPException(422, "Live benchmark inference is limited to one seed")
    if req.use_live_model and os.getenv("GRIDMIND_MODEL") != verified_live_model_id:
        raise HTTPException(
            409,
            "Run POST /model/verify and receive live_success before a live benchmark",
        )
    with operation_lock:
        if req.use_live_model and os.getenv("GRIDMIND_MODEL") != verified_live_model_id:
            raise HTTPException(
                409,
                "Live model verification expired before benchmark execution; verify again",
            )
        try:
            config = get_scenario_config(req.scenario, seed=0)
            if req.use_live_model:
                config["max_steps"] = min(config["max_steps"], 10)
            latest_benchmark = run_experiments(
                config,
                req.seeds,
                policies=req.policies,
                live_model=req.use_live_model,
                live_verified=req.use_live_model,
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


@app.post("/benchmarks/suite")
def run_benchmark_suite(req: ScenarioSuiteRequest) -> dict[str, Any]:
        global latest_benchmark
        if len(set(req.seeds)) != len(req.seeds):
            raise HTTPException(422, "seeds must be unique")
        if len(set(req.policies)) != len(req.policies):
            raise HTTPException(422, "policies must be unique")
        with operation_lock:
            try:
                latest_benchmark = run_scenario_suite(
                    req.seeds,
                    policies=req.policies,
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            for record in latest_benchmark["runs"]:
                recent_runs.append(
                    {
                        "run_id": record["run_id"],
                        "kind": "scenario_suite",
                        "policy": record["policy"],
                        "scenario_id": record["scenario_id"],
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
        with operation_lock:
            if latest_benchmark is None:
                raise HTTPException(404, "No benchmark has been run in this process")
            return latest_benchmark


@app.get("/history")
def history(limit: int = 20) -> dict[str, Any]:
    if not 1 <= limit <= 50:
        raise HTTPException(422, "limit must be between 1 and 50")
    with operation_lock:
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
        "scenario_id",
        "scenario_sha256",
        "policy",
        "seed",
        "status",
        "steps_executed",
        *metric_fields,
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
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
