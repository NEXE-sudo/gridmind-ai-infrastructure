import pytest
from fastapi.testclient import TestClient

from server import gridmind_app
from server.datacenter_simulator import DatacenterSimulator


@pytest.fixture(autouse=True)
def isolated_simulator(monkeypatch):
    monkeypatch.setattr(gridmind_app, "sim", DatacenterSimulator(seed=7))


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
        step = client.post("/step", json={"assignments": {"infer-001": "gpu-a"}})
        run = client.post("/run", json={"policy": "resource_aware", "steps": 2})

    assert reset.status_code == 200
    assert reset.json()["seed"] == 31
    assert step.status_code == 200
    assert step.json()["step"] == 1
    assert step.json()["rejected_actions"] == []
    assert run.status_code == 200
    assert run.json()["steps_executed"] == 2
    assert run.json()["history"][0]["decision"] == "resource_aware"


def test_invalid_actions_and_request_schemas_return_422_or_rejections():
    with TestClient(gridmind_app.app) as client:
        rejected_action = client.post(
            "/step", json={"assignments": {"train-001": "missing"}}
        )
        unknown_field = client.post("/step", json={"not_an_action": True})
        invalid_id_type = client.post("/step", json={"assignments": {"train-001": 3}})
        invalid_seed = client.post("/reset", json={"seed": "31"})
        invalid_policy = client.post("/run", json={"policy": "unknown"})
        invalid_limit = client.post("/run", json={"steps": 101})

    assert rejected_action.status_code == 200
    assert rejected_action.json()["rejected_actions"] == [
        {"workload_id": "train-001", "reason": "unknown_node"}
    ]
    for response in (unknown_field, invalid_id_type, invalid_seed, invalid_policy, invalid_limit):
        assert response.status_code == 422


def test_invalid_nemotron_assignment_uses_and_reports_safe_fallback(monkeypatch):
    monkeypatch.setattr(
        gridmind_app, "nemotron_propose", lambda _: {"train-001": "unknown-node"}
    )

    with TestClient(gridmind_app.app) as client:
        response = client.post("/run", json={"policy": "nemotron", "steps": 1})

    assert response.status_code == 200
    result = response.json()
    assert result["fallback_used"] is True
    assert result["history"][0]["decision"] == "resource_aware_fallback"
    assert result["history"][0]["rejected_actions"] == []


def test_valid_nemotron_assignment_is_applied_without_fallback(monkeypatch):
    monkeypatch.setattr(
        gridmind_app, "nemotron_propose", lambda _: {"infer-001": "gpu-a"}
    )

    with TestClient(gridmind_app.app) as client:
        response = client.post("/run", json={"policy": "nemotron", "steps": 1})

    assert response.status_code == 200
    result = response.json()
    assert result["fallback_used"] is False
    assert result["history"][0]["decision"] == "nemotron"
    assert result["history"][0]["rejected_actions"] == []
