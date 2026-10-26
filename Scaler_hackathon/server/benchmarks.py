"""Reproducible paired policy experiments with JSON, CSV, and Markdown output."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import random
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .datacenter_simulator import DatacenterSimulator
from .decision import POLICIES, execute_policy_step
from .metrics import aggregate_runs

SIMULATOR_VERSION = "gridmind-simulator-v2"
POLICY_VERSION = "gridmind-policies-v1"
logger = logging.getLogger(__name__)


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read scenario configuration: {config_path}") from exc
    validate_config(config)
    return config


def validate_config(config: Any) -> None:
    if not isinstance(config, dict):
        raise TypeError("Scenario configuration must be a JSON object")
    required = {"name", "power_budget_kw", "energy_price_per_kwh", "failure_probability", "max_steps", "nodes", "workloads"}
    if not required <= config.keys():
        raise ValueError(f"Scenario configuration missing keys: {sorted(required - config.keys())}")
    if not isinstance(config["name"], str) or not config["name"]:
        raise ValueError("Scenario name must be a non-empty string")
    if not isinstance(config["max_steps"], int) or not 1 <= config["max_steps"] <= 500:
        raise ValueError("max_steps must be an integer from 1 to 500")
    if not isinstance(config["nodes"], list) or not isinstance(config["workloads"], list):
        raise TypeError("nodes and workloads must be arrays")
    workloads = []
    for source in config["workloads"]:
        workload = dict(source)
        arrival = workload.pop("arrival_time", workload.get("submission_time", 0))
        if "deadline_after_minutes" in workload:
            workload["deadline"] = arrival + workload.pop("deadline_after_minutes")
        workload["submission_time"] = arrival
        workload["submitted"] = arrival == 0
        workloads.append(workload)
    DatacenterSimulator(
        power_budget_kw=config["power_budget_kw"],
        failure_probability=config["failure_probability"],
        energy_price_per_kwh=config["energy_price_per_kwh"],
        nodes=config["nodes"],
        workloads=workloads,
        recovery_steps=config.get("recovery_steps", 1),
    )


def make_seeded_scenario(config: dict[str, Any], seed: int) -> dict[str, Any]:
    rng_seed = random.Random(seed)
    jitter = config.get("arrival_jitter_steps", 0)
    if not isinstance(jitter, int) or jitter < 0 or jitter > config["max_steps"]:
        raise ValueError("arrival_jitter_steps must fit within the scenario horizon")
    workloads = []
    for source in config["workloads"]:
        workload = dict(source)
        arrival = workload.pop("arrival_time", None)
        if arrival is None:
            arrival = rng_seed.randint(0, jitter) if jitter else 0
        workload["submission_time"] = arrival
        workload["submitted"] = arrival == 0
        if "deadline_after_minutes" in workload:
            workload["deadline"] = arrival + workload.pop("deadline_after_minutes")
        workloads.append(workload)
    materialized = {
        "name": config["name"],
        "power_budget_kw": config["power_budget_kw"],
        "energy_price_per_kwh": config["energy_price_per_kwh"],
        "failure_probability": config["failure_probability"],
        "recovery_steps": config.get("recovery_steps", 1),
        "max_steps": config["max_steps"],
        "nodes": config["nodes"],
        "workloads": workloads,
        "seed": seed,
    }
    canonical = json.dumps(materialized, sort_keys=True, separators=(",", ":"))
    materialized["scenario_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return materialized


def run_episode(
    config: dict[str, Any],
    scenario: dict[str, Any],
    policy: str,
    *,
    live_model: bool = False,
) -> dict[str, Any]:
    simulator: DatacenterSimulator | None = None
    started = datetime.now(UTC)
    record: dict[str, Any] = {
        "run_id": f"{scenario['scenario_sha256'][:12]}-{policy}",
        "scenario_name": scenario["name"],
        "scenario_sha256": scenario["scenario_sha256"],
        "policy": policy,
        "policy_version": POLICY_VERSION,
        "simulator_version": SIMULATOR_VERSION,
        "seed": scenario["seed"],
        "live_model_enabled": live_model,
        "model_id": os.getenv("GRIDMIND_MODEL") if live_model else None,
        "status": "failed",
        "steps_executed": 0,
        "error_type": None,
        "created_at": started.isoformat(),
        "metrics": None,
        "history": [],
    }
    try:
        simulator = DatacenterSimulator(
            seed=scenario["seed"],
            power_budget_kw=scenario["power_budget_kw"],
            failure_probability=scenario["failure_probability"],
            nodes=scenario["nodes"],
            workloads=scenario["workloads"],
            recovery_steps=scenario["recovery_steps"],
            energy_price_per_kwh=scenario["energy_price_per_kwh"],
        )
        for _ in range(config["max_steps"]):
            step = execute_policy_step(simulator, policy, use_live_model=live_model)
            record["history"].append(
                {
                    key: step[key]
                    for key in (
                        "step",
                        "decision",
                        "proposed_assignments",
                        "executed_assignments",
                        "explanation",
                        "proposal_status",
                        "proposal_latency_ms",
                        "fallback_used",
                        "rejected_actions",
                        "events",
                        "metrics",
                    )
                }
            )
            if not any(
                workload.status in {"pending", "running"}
                for workload in simulator.workloads
            ):
                record["status"] = "completed"
                break
        else:
            record["status"] = "incomplete"
        record["steps_executed"] = simulator.step_count
        record["metrics"] = simulator.state()["metrics"]
        record["node_state"] = simulator.state()["nodes"]
        record["workload_state"] = simulator.state()["workloads"]
    except Exception as exc:
        logger.exception("Benchmark episode failed for policy=%s seed=%s", policy, scenario["seed"])
        record["error_type"] = type(exc).__name__
        if simulator is not None:
            record["steps_executed"] = simulator.step_count
            record["metrics"] = simulator.state()["metrics"]
            record["node_state"] = simulator.state()["nodes"]
            record["workload_state"] = simulator.state()["workloads"]
            record["status"] = (
                "incomplete" if simulator.step_count > 0 else "failed"
            )
    return record


def run_experiments(
    config: dict[str, Any],
    seeds: list[int],
    *,
    policies: list[str] | None = None,
    live_model: bool = False,
) -> dict[str, Any]:
    validate_config(config)
    policies = list(POLICIES) if policies is None else policies
    if not policies or any(policy not in POLICIES for policy in policies):
        raise ValueError(f"Policies must be selected from {', '.join(POLICIES)}")
    if live_model and "nemotron" not in policies:
        raise ValueError("Live inference requires the nemotron policy")
    if not seeds or len(seeds) > 20 or any(type(seed) is not int for seed in seeds):
        raise ValueError("Supply 1–20 integer seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be unique")
    if live_model and not (os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")):
        raise ValueError("--live-model requires NEBIUS_API_KEY and GRIDMIND_MODEL")

    records = []
    scenarios = {seed: make_seeded_scenario(config, seed) for seed in seeds}
    for seed in seeds:
        for policy in policies:
            records.append(
                run_episode(
                    config,
                    scenarios[seed],
                    policy,
                    live_model=live_model and policy == "nemotron",
                )
            )
    comparison = {
        policy: aggregate_runs([record for record in records if record["policy"] == policy])
        for policy in policies
    }
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "configuration": config,
        "seeds": seeds,
        "policies": policies,
        "live_model_enabled": live_model,
        "model_id": os.getenv("GRIDMIND_MODEL") if live_model else None,
        "comparison": comparison,
        "paired_comparison_vs_resource_aware": paired_comparison(records, policies),
        "runs": records,
        "limitations": [
            "Synthetic one-minute simulation; power and energy are not facility telemetry.",
            "Results are scenario- and seed-specific; small samples are not statistically conclusive.",
            "Offline Nemotron policy records fallback execution, not model inference.",
            "Model-generated explanations are rationales, not causal proof.",
        ],
    }


def paired_comparison(records: list[dict[str, Any]], policies: list[str]) -> dict[str, Any]:
    baseline = {
        record["seed"]: record
        for record in records
        if record["policy"] == "resource_aware" and record["status"] == "completed"
    }
    metrics = (
        "throughput_jobs_per_hour",
        "deadline_miss_rate",
        "sla_attainment_rate",
        "estimated_energy_kwh",
        "estimated_energy_cost",
        "average_queue_wait_minutes",
    )
    output = {}
    for policy in policies:
        if policy == "resource_aware":
            continue
        candidates = {
            record["seed"]: record
            for record in records
            if record["policy"] == policy and record["status"] == "completed"
        }
        seeds = sorted(set(baseline) & set(candidates))
        output[policy] = {
            "paired_successful_seed_count": len(seeds),
            "excluded_failed_or_incomplete_policy_runs": sum(
                record["policy"] == policy and record["status"] != "completed"
                for record in records
            ),
            "excluded_failed_or_incomplete_baseline_runs": sum(
                record["policy"] == "resource_aware"
                and record["status"] != "completed"
                for record in records
            ),
            "mean_policy_minus_resource_aware": {
                metric: _paired_delta(
                    [candidates[seed]["metrics"].get(metric) for seed in seeds],
                    [baseline[seed]["metrics"].get(metric) for seed in seeds],
                )
                for metric in metrics
            },
        }
    return output


def _paired_delta(values: list[Any], baseline: list[Any]) -> dict[str, Any]:
    pairs = [
        (float(value), float(base))
        for value, base in zip(values, baseline, strict=True)
        if value is not None and base is not None
    ]
    return {
        "mean_delta": round(
            statistics.fmean(value - base for value, base in pairs), 6
        )
        if pairs
        else None,
        "n": len(pairs),
    }


def write_results(result: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "results.json"
    csv_path = directory / "runs.csv"
    report_path = directory / "report.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fields = [
        "run_id",
        "scenario_name",
        "scenario_sha256",
        "policy",
        "policy_version",
        "simulator_version",
        "seed",
        "live_model_enabled",
        "model_id",
        "status",
        "steps_executed",
        "error_type",
    ]
    metric_fields = sorted(
        {
            key
            for run in result["runs"]
            if run["metrics"]
            for key in run["metrics"]
        }
    )
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output, fieldnames=fields + metric_fields, lineterminator="\n"
        )
        writer.writeheader()
        for run in result["runs"]:
            writer.writerow(
                {
                    **{key: run[key] for key in fields},
                    **(run["metrics"] or {}),
                }
            )

    report_path.write_text(render_report(result), encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path), "markdown": str(report_path)}


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# GridMind experiment report",
        "",
        f"- Created: `{result['created_at']}`",
        f"- Seeds: `{', '.join(map(str, result['seeds']))}`",
        f"- Scenario: `{result['configuration']['name']}`",
        f"- Live model enabled: `{result['live_model_enabled']}`",
        f"- Model ID: `{result['model_id'] or 'not used'}`",
        "",
        "## All-run policy summaries",
        "",
        "| Policy | Runs | Completed | Failed | Incomplete | Throughput jobs/hour | SLA attainment | Deadline miss rate | Energy kWh | Cost estimate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, summary in result["comparison"].items():
        metrics = summary["metrics"]

        def mean(key: str, metric_values: dict[str, Any] = metrics) -> str:
            value = metric_values[key]["mean"]
            return "n/a" if value is None else str(value)

        lines.append(
            f"| {policy} | {summary['run_count']} | {summary['successful_run_count']} "
            f"| {summary['failed_run_count']} | {summary['incomplete_run_count']} "
            f"| {mean('throughput_jobs_per_hour')} "
            f"| {mean('sla_attainment_rate')} | {mean('deadline_miss_rate')} "
            f"| {mean('estimated_energy_kwh')} | {mean('estimated_energy_cost')} |"
        )
    lines.extend(
        [
            "",
            (
                "Power, energy, and cost are synthetic estimates. Cost uses the scenario's "
                "configured energy rate, not a cloud bill. The aggregation includes partial "
                "metrics from failed/incomplete records; status counts are reported separately."
            ),
            "",
            "## Paired comparison against resource-aware",
            "",
            (
                "Only seed pairs where both policy runs completed are used in this paired table. "
                "Excluded runs remain visible in the all-run summaries above."
            ),
            "",
            "| Policy | Paired seeds | Throughput delta | SLA delta | Deadline miss-rate delta | Energy delta kWh |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for policy, comparison in result["paired_comparison_vs_resource_aware"].items():
        deltas = comparison["mean_policy_minus_resource_aware"]
        lines.append(
            f"| {policy} | {comparison['paired_successful_seed_count']} "
            f"| {deltas['throughput_jobs_per_hour']['mean_delta']} "
            f"| {deltas['sla_attainment_rate']['mean_delta']} "
            f"| {deltas['deadline_miss_rate']['mean_delta']} "
            f"| {deltas['estimated_energy_kwh']['mean_delta']} |"
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in result["limitations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/demo.json")
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--policies", default=",".join(POLICIES))
    parser.add_argument("--output-dir", default="benchmarks/latest")
    parser.add_argument(
        "--live-model",
        action="store_true",
        help="Make actual Nebius requests for Nemotron runs; requires explicit credentials and model ID.",
    )
    args = parser.parse_args(argv)
    try:
        seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
        policies = [value.strip() for value in args.policies.split(",") if value.strip()]
        config = load_config(args.config)
        result = run_experiments(
            config,
            seeds,
            policies=policies,
            live_model=args.live_model,
        )
        paths = write_results(result, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps({"run_count": len(result["runs"]), "outputs": paths}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
