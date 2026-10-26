from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from server import gridmind_app
from server.datacenter_simulator import DatacenterSimulator
from server.decision import Proposal


@pytest.fixture(autouse=True)
def isolated_simulator(monkeypatch):
    monkeypatch.setattr(gridmind_app, "sim", DatacenterSimulator(seed=7))
    monkeypatch.setattr(gridmind_app, "active_scenario", "standard")
    monkeypatch.setattr(gridmind_app, "recent_runs", [])
    monkeypatch.setattr(gridmind_app, "latest_benchmark", None)


def test_app_startup_and_health_state_policy_routes():
    with TestClient(gridmind_app.app) as client:
        health = client.get("/health")
        state = client.get("/state")
        policies = client.get("/policies")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "gridmind",
        "mode": "simulation-only",
    }
    assert state.status_code == 200
    assert state.json()["seed"] == 7
    assert policies.status_code == 200
    assert {item["id"] for item in policies.json()["policies"]} == {
        "fifo",
        "priority",
        "resource_aware",
        "nemotron",
    }


def test_reset_step_and_run_behaviour():
    with TestClient(gridmind_app.app) as client:
        reset = client.post("/reset", json={"seed": 31})
        step = client.post("/step", json={"assignments": {"infer-001": "gpu-a100"}})
        run = client.post("/run", json={"policy": "resource_aware", "steps": 2})

    assert reset.status_code == 200
    assert reset.json()["seed"] == 31
    assert step.status_code == 200
    assert step.json()["step"] == 1
    assert step.json()["rejected_actions"] == []
    assert run.status_code == 200
    assert run.json()["steps_executed"] == 2
    assert run.json()["termination_reason"] == "requested_horizon_reached"
    assert run.json()["metrics"]["horizon_reached"] is True
    assert run.json()["history"][0]["decision"] == "resource_aware"


def test_reset_scenario_controls_create_reproducible_simulations():
    with TestClient(gridmind_app.app) as client:
        surge = client.post(
            "/reset", json={"seed": 31, "scenario": "workload_surge"}
        )
        failure = client.post(
            "/reset", json={"seed": 31, "scenario": "node_failure"}
        )
        deadlines = client.post(
            "/reset", json={"seed": 31, "scenario": "tight_deadlines"}
        )

    assert surge.status_code == 200
    assert len(surge.json()["workloads"]) == 16
    assert any(item["id"].endswith("-surge") for item in surge.json()["workloads"])
    assert failure.status_code == 200
    assert failure.json()["failure_probability"] == 0.35
    assert deadlines.status_code == 200
    assert all(
        item["deadline"] <= item["submission_time"] + max(1, item["duration"] // 2)
        for item in deadlines.json()["workloads"]
    )


def test_benchmark_history_latest_and_csv_export():
    with TestClient(gridmind_app.app) as client:
        result = client.post(
            "/benchmarks/run",
            json={"seeds": [3], "policies": ["fifo", "resource_aware"]},
        )
        latest = client.get("/benchmarks/latest")
        history = client.get("/history?limit=2")
        exported = client.get("/exports/latest.csv")

    assert result.status_code == 200
    assert len(result.json()["runs"]) == 2
    assert latest.json()["runs"] == result.json()["runs"]
    assert [run["kind"] for run in history.json()["runs"]] == ["benchmark", "benchmark"]
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert len(exported.text.splitlines()) == 3


def test_scenario_catalog_and_scenario_benchmark_route():
    with TestClient(gridmind_app.app) as client:
        catalog = client.get("/scenarios")
        benchmark = client.post(
            "/benchmarks/run",
            json={
                "seeds": [4],
                "policies": ["fifo", "resource_aware"],
                "scenario": "infeasible_workloads",
            },
        )

    assert catalog.status_code == 200
    assert len(catalog.json()["scenarios"]) == 10
    assert benchmark.status_code == 200
    result = benchmark.json()
    assert result["scenario_id"] == "infeasible_workloads"
    assert all(run["scenario_id"] == "infeasible_workloads" for run in result["runs"])
    run = result["runs"][0]
    assert run["status"] == "completed"
    assert run["metrics"]["permanently_infeasible_workloads"] == 3
    assert sum(run["metrics"]["workload_status_counts"].values()) == (
        run["metrics"]["total_workloads"]
    )
    assert run["termination_reason"] == "fixed_horizon_reached"


def test_api_scenario_suite_is_bounded_and_exportable():
    with TestClient(gridmind_app.app) as client:
        result = client.post(
            "/benchmarks/suite",
            json={"seeds": [5], "policies": ["fifo", "resource_aware"]},
        )
        exported = client.get("/exports/latest.csv")

    assert result.status_code == 200
    assert result.json()["scenario_count"] == 10
    assert len(result.json()["runs"]) == 20
    assert exported.status_code == 200
    assert "infeasible_workloads" in exported.text


def test_mutating_requests_are_serialized_across_threads():
    client = TestClient(gridmind_app.app)
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(
            pool.map(
                lambda _: client.post("/step", json={}),
                range(6),
            )
        )
    assert all(response.status_code == 200 for response in responses)
    assert client.get("/state").json()["step"] == 6
    client.close()


def test_invalid_actions_and_request_schemas_return_422_or_rejections():
    with TestClient(gridmind_app.app) as client:
        rejected_action = client.post(
            "/step", json={"assignments": {"train-001": "missing"}}
        )
        unknown_field = client.post("/step", json={"not_an_action": True})
        invalid_id_type = client.post("/step", json={"assignments": {"train-001": 3}})
        invalid_seed = client.post("/reset", json={"seed": "31"})
        invalid_scenario = client.post("/reset", json={"scenario": "unknown"})
        invalid_policy = client.post("/run", json={"policy": "unknown"})
        invalid_limit = client.post("/run", json={"steps": 101})
        invalid_seed_range = client.post("/reset", json={"seed": -1})
        invalid_live_horizon = client.post(
            "/run",
            json={
                "policy": "nemotron",
                "steps": 11,
                "use_live_model": True,
            },
        )
        oversized_assignment = client.post(
            "/step",
            json={"assignments": {f"job-{index}": "missing" for index in range(101)}},
        )

    assert rejected_action.status_code == 200
    assert rejected_action.json()["rejected_actions"] == [
        {"workload_id": "train-001", "reason": "unknown_node"}
    ]
    for response in (
        unknown_field,
        invalid_id_type,
        invalid_seed,
        invalid_scenario,
        invalid_policy,
        invalid_limit,
        invalid_seed_range,
        invalid_live_horizon,
        oversized_assignment,
    ):
        assert response.status_code == 422


def test_invalid_nemotron_assignment_uses_and_reports_safe_fallback(monkeypatch):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal(
            {"train-001": "unknown-node"},
            "Place the training workload.",
            "model",
        ),
    )

    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/test-model")
    with TestClient(gridmind_app.app) as client:
        response = client.post(
            "/run",
            json={"policy": "nemotron", "steps": 1, "use_live_model": True},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["fallback_used"] is True
    assert result["history"][0]["decision"] == "resource_aware_fallback"
    assert result["history"][0]["rejected_actions"] == []


def test_valid_nemotron_assignment_is_applied_without_fallback(monkeypatch):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal({"infer-001": "gpu-a"}, "Fits the available node.", "model"),
    )

    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/test-model")
    with TestClient(gridmind_app.app) as client:
        response = client.post(
            "/run",
            json={"policy": "nemotron", "steps": 1, "use_live_model": True},
        )

    assert response.status_code == 200
    result = response.json()
    assert result["fallback_used"] is False
    assert result["history"][0]["decision"] == "nemotron"
    assert result["history"][0]["rejected_actions"] == []
