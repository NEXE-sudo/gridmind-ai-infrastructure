import csv
import json
from pathlib import Path

import pytest

from server.benchmarks import (
    load_config,
    make_seeded_scenario,
    run_episode,
    run_experiments,
    run_scenario_suite,
    write_results,
)
from server.datacenter_simulator import DatacenterSimulator
from server.decision import execute_policy_step
from server.scenarios import load_scenario_suite

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


def test_versioned_scenario_suite_is_paired_and_reproducible():
    suite = load_scenario_suite()
    assert suite["suite_version"] == "1.0.0"
    assert len(suite["scenarios"]) == 10

    first = run_scenario_suite(
        [7, 8], policies=["fifo", "resource_aware"]
    )
    second = run_scenario_suite(
        [7, 8], policies=["fifo", "resource_aware"]
    )
    assert first["scenario_count"] == 10
    assert len(first["runs"]) == 40
    for scenario_id, scenario in first["scenarios"].items():
        assert scenario_id in second["scenarios"]
        for seed in [7, 8]:
            paired = [
                run
                for run in first["runs"]
                if run["scenario_id"] == scenario_id and run["seed"] == seed
            ]
            assert len({run["scenario_sha256"] for run in paired}) == 1
            assert all(run["history_included"] is False for run in paired)
            assert [
                run["scenario_sha256"] for run in paired
            ] == [
                run["scenario_sha256"]
                for run in second["runs"]
                if run["scenario_id"] == scenario_id and run["seed"] == seed
            ]
        assert scenario["configuration"]["synthetic_assumptions"] is True


def test_seed_changes_materialized_workload_arrivals_for_scenario_suite():
    config = load_scenario_suite()
    scenario = next(item for item in config["scenarios"] if item["id"] == "burst_arrivals")
    from server.scenarios import materialize_scenario

    source = materialize_scenario(scenario, config)
    first = make_seeded_scenario(source, 1)
    second = make_seeded_scenario(source, 2)
    assert first["scenario_sha256"] != second["scenario_sha256"]
    assert [job["submission_time"] for job in first["workloads"]] != [
        job["submission_time"] for job in second["workloads"]
    ]


def test_failed_and_incomplete_policy_runs_remain_in_summaries(monkeypatch):
    from server import benchmarks

    config = load_config(CONFIG_PATH)
    config["max_steps"] = 1
    config["arrival_jitter_steps"] = 0
    result = run_experiments(config, [9], policies=["fifo"])
    assert result["runs"][0]["status"] == "incomplete"
    assert result["comparison"]["fifo"]["incomplete_run_count"] == 1

    monkeypatch.setattr(
        benchmarks,
        "execute_policy_step",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    failed = run_experiments(config, [9], policies=["fifo"])
    assert failed["runs"][0]["status"] == "failed"
    assert failed["runs"][0]["error_type"] == "RuntimeError"
    assert failed["comparison"]["fifo"]["failed_run_count"] == 1


def test_live_experiment_is_bounded(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-key")
    monkeypatch.setenv("GRIDMIND_MODEL", "verified-by-test")
    with pytest.raises(ValueError, match="bounded to one seed"):
        run_experiments(load_config(CONFIG_PATH), [1], live_model=True)


def test_policies_share_same_exogenous_node_failure_trace():
    config = load_config(CONFIG_PATH)
    config["failure_probability"] = 0.5
    config["max_steps"] = 10
    for workload in config["workloads"]:
        workload["duration"] = 100
        workload["deadline_after_minutes"] = 150
        workload.pop("deadline", None)
    scenario = make_seeded_scenario(config, 34)

    fifo = run_episode(config, scenario, "fifo")
    resource_aware = run_episode(config, scenario, "resource_aware")
    fifo_trace = [
        [event for event in step["events"] if event["type"] == "node_failed"]
        for step in fifo["history"]
    ]
    aware_trace = [
        [event for event in step["events"] if event["type"] == "node_failed"]
        for step in resource_aware["history"]
    ]
    assert fifo_trace == aware_trace
