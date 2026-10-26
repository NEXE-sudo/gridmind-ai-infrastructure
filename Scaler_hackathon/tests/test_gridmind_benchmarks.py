import csv
import json
from pathlib import Path

import pytest

from server.benchmarks import (
    load_config,
    make_seeded_scenario,
    run_experiments,
    write_results,
)
from server.datacenter_simulator import DatacenterSimulator
from server.decision import execute_policy_step

CONFIG_PATH = Path(__file__).parents[1] / "configs" / "demo.json"


def test_seeded_scenario_is_reproducible_and_has_staggered_arrivals():
    config = load_config(CONFIG_PATH)
    first = make_seeded_scenario(config, 42)
    second = make_seeded_scenario(config, 42)
    assert first == second
    assert first["scenario_sha256"] == second["scenario_sha256"]
    assert any(workload["submission_time"] > 0 for workload in first["workloads"])


def test_policy_experiments_use_identical_scenarios_and_export_results(tmp_path):
    config = load_config(CONFIG_PATH)
    result = run_experiments(
        config,
        [11, 12],
        policies=["fifo", "priority", "resource_aware", "nemotron"],
    )

    assert len(result["runs"]) == 8
    for seed in [11, 12]:
        records = [record for record in result["runs"] if record["seed"] == seed]
        assert len({record["scenario_sha256"] for record in records}) == 1
        assert all(record["status"] == "completed" for record in records)
    assert all(
        record["metrics"]["ai_fallbacks"] > 0
        for record in result["runs"]
        if record["policy"] == "nemotron"
    )
    paths = write_results(result, tmp_path)
    exported = json.loads(Path(paths["json"]).read_text())
    assert len(exported["runs"]) == 8
    with Path(paths["csv"]).open(newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 8
    assert b"\r\n" not in Path(paths["csv"]).read_bytes()
    assert Path(paths["markdown"]).read_text().startswith("# GridMind experiment report")
    assert result["paired_comparison_vs_resource_aware"]["fifo"][
        "paired_successful_seed_count"
    ] == 2


def test_live_experiment_requires_explicit_credentials_and_model(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("GRIDMIND_MODEL", raising=False)
    with pytest.raises(ValueError, match="--live-model requires"):
        run_experiments(load_config(CONFIG_PATH), [1], live_model=True)


def test_live_experiment_requires_nemotron_policy():
    with pytest.raises(ValueError, match="requires the nemotron policy"):
        run_experiments(
            load_config(CONFIG_PATH),
            [1],
            policies=["fifo"],
            live_model=True,
        )


def test_duplicate_seed_rejected():
    with pytest.raises(ValueError, match="unique"):
        run_experiments(load_config(CONFIG_PATH), [1, 1])


def test_offline_ai_records_fallback_without_inference_request(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("GRIDMIND_MODEL", raising=False)
    sim = DatacenterSimulator()
    result = execute_policy_step(sim, "nemotron")

    assert result["fallback_used"] is True
    assert result["proposal_status"] == "offline"
    assert sim.counters["ai_invocations"] == 0
    assert sim.counters["ai_attempts"] > 0
    assert sim.counters["ai_fallbacks"] > 0
