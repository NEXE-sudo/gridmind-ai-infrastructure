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
from .metrics import aggregate_runs, bootstrap_mean_interval
from .nemotron import (
    configured_base_url,
    configured_inference_timeout_seconds,
    request_proposal,
    verify_catalogue_model,
)
from .scenarios import load_scenario_suite, scenario_configs

SIMULATOR_VERSION = "gridmind-simulator-v4"
POLICY_VERSION = "gridmind-policies-v3"
MAX_EXPERIMENT_SEEDS = 100
MAX_SUITE_RUNS = 2_000
MAX_SUITE_POLICY_STEPS = 500_000
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
    if not 1 <= len(config["nodes"]) <= 64:
        raise ValueError("A scenario must contain 1–64 nodes")
    if not 1 <= len(config["workloads"]) <= 1_000:
        raise ValueError("A scenario must contain 1–1000 workloads")
    workloads = []
    for source in config["workloads"]:
        workload = dict(source)
        arrival = workload.pop(
            "arrival_time", workload.get("submission_time", 0)
        )
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
            base_arrival = workload.pop("submission_time", 0)
            arrival = base_arrival + (
                rng_seed.randint(0, jitter) if jitter else 0
            )
        workload["submission_time"] = arrival
        workload["submitted"] = arrival == 0
        if "deadline_after_minutes" in workload:
            workload["deadline"] = arrival + workload.pop("deadline_after_minutes")
        workloads.append(workload)
    materialized = {
        "name": config["name"],
        "description": config.get("description"),
        "intended_stress": config.get("intended_stress"),
        "scenario_id": config.get("scenario_id", config["name"]),
        "scenario_version": config.get("scenario_version", "1"),
        "suite_id": config.get("suite_id"),
        "topology_id": config.get("topology_id"),
        "seed_behavior": config.get("seed_behavior"),
        "horizon_rationale": config.get("horizon_rationale"),
        "synthetic_assumptions": config.get("synthetic_assumptions", True),
        "workload_parameters": config.get("workload_parameters"),
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
    include_history: bool = True,
) -> dict[str, Any]:
    simulator: DatacenterSimulator | None = None
    started = datetime.now(UTC)
    record: dict[str, Any] = {
        "run_id": f"{scenario['scenario_sha256'][:12]}-{policy}",
        "scenario_id": scenario.get("scenario_id", scenario["name"]),
        "scenario_version": scenario.get("scenario_version", "1"),
        "scenario_name": scenario["name"],
        "scenario_sha256": scenario["scenario_sha256"],
        "policy": policy,
        "policy_version": POLICY_VERSION,
        "simulator_version": SIMULATOR_VERSION,
        "seed": scenario["seed"],
        "live_model_enabled": live_model,
        "model_provider": "nebius-token-factory" if live_model else None,
        "model_id": os.getenv("GRIDMIND_MODEL") if live_model else None,
        "model_execution_mode": (
            "live_inference" if live_model and policy == "nemotron"
            else "deterministic_fallback" if policy == "nemotron"
            else "baseline_scheduler"
        ),
        "policy_sha256": hashlib.sha256(
            json.dumps(
                {"policy": policy, "version": POLICY_VERSION},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "status": "failed",
        "termination_reason": None,
        "workloads_terminal_at_step": None,
        "steps_executed": 0,
        "error_type": None,
        "created_at": started.isoformat(),
        "metrics": None,
        "history": [],
        "history_included": include_history,
        "event_trace": [],
        "event_counts": {},
        "scheduling_diagnostic_trace": [],
        "exogenous_failure_trace": [],
        "exogenous_failure_trace_sha256": hashlib.sha256(b"[]").hexdigest(),
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
            horizon_steps=config["max_steps"],
        )
        for _ in range(config["max_steps"]):
            step = execute_policy_step(simulator, policy, use_live_model=live_model)
            for event in step["events"]:
                event_row = {"step": simulator.step_count - 1, **event}
                record["event_trace"].append(event_row)
                event_type = event["type"]
                record["event_counts"][event_type] = (
                    record["event_counts"].get(event_type, 0) + 1
                )
            record["scheduling_diagnostic_trace"].extend(
                step["scheduling_diagnostics"]
            )
            if (
                record["workloads_terminal_at_step"] is None
                and not any(
                    workload.status in {"pending", "running"}
                    for workload in simulator.workloads
                )
            ):
                record["workloads_terminal_at_step"] = simulator.step_count
            if include_history:
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
                            "inference_mode",
                            "proposal_request_attempts",
                            "proposal_retry_count",
                            "proposal_response_received",
                            "proposal_prompt_tokens",
                            "proposal_completion_tokens",
                            "scheduling_diagnostics",
                            "placement_diagnostics",
                            "fallback_used",
                            "rejected_actions",
                            "events",
                            "metrics",
                        )
                    }
                )
        record["status"] = "completed"
        record["termination_reason"] = "fixed_horizon_reached"
        record["steps_executed"] = simulator.step_count
        record["metrics"] = simulator.state()["metrics"]
        record["node_state"] = simulator.state()["nodes"]
        record["workload_state"] = simulator.state()["workloads"]
        record["exogenous_failure_trace"] = list(simulator.node_failure_trace)
        failure_trace = json.dumps(
            record["exogenous_failure_trace"],
            sort_keys=True,
            separators=(",", ":"),
        )
        record["exogenous_failure_trace_sha256"] = hashlib.sha256(
            failure_trace.encode()
        ).hexdigest()
    except Exception as exc:  # noqa: BLE001 - isolate and preserve each failed run.
        logger.error(
            "Benchmark episode failed for policy=%s seed=%s (%s)",
            policy,
            scenario["seed"],
            type(exc).__name__,
        )
        record["error_type"] = type(exc).__name__
        if simulator is not None:
            record["steps_executed"] = simulator.step_count
            record["metrics"] = simulator.state()["metrics"]
            record["node_state"] = simulator.state()["nodes"]
            record["workload_state"] = simulator.state()["workloads"]
            record["status"] = "failed"
            record["termination_reason"] = "simulation_error"
            record["exogenous_failure_trace"] = list(simulator.node_failure_trace)
            record["exogenous_failure_trace_sha256"] = hashlib.sha256(
                json.dumps(
                    record["exogenous_failure_trace"],
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
    return record


def run_experiments(
    config: dict[str, Any],
    seeds: list[int],
    *,
    policies: list[str] | None = None,
    live_model: bool = False,
    live_verified: bool = False,
    include_history: bool = True,
) -> dict[str, Any]:
    validate_config(config)
    policies = list(POLICIES) if policies is None else policies
    if not policies or any(policy not in POLICIES for policy in policies):
        raise ValueError(f"Policies must be selected from {', '.join(POLICIES)}")
    if live_model and "nemotron" not in policies:
        raise ValueError("Live inference requires the nemotron policy")
    if (
        not seeds
        or len(seeds) > MAX_EXPERIMENT_SEEDS
        or any(type(seed) is not int or not 0 <= seed <= 2_147_483_647 for seed in seeds)
    ):
        raise ValueError(f"Supply 1–{MAX_EXPERIMENT_SEEDS} non-negative integer seeds")
    if len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be unique")
    if live_model and not (os.getenv("NEBIUS_API_KEY") and os.getenv("GRIDMIND_MODEL")):
        raise ValueError("--live-model requires NEBIUS_API_KEY and GRIDMIND_MODEL")
    if live_model and (len(seeds) != 1 or config["max_steps"] > 10):
        raise ValueError(
            "Live inference is bounded to one seed and at most ten simulation steps per run"
        )
    if live_model and not live_verified:
        raise ValueError(
            "Live experiments require a successful catalogue and one-request preflight"
        )

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
                    include_history=include_history,
                )
            )
    comparison = {
        policy: aggregate_runs([record for record in records if record["policy"] == policy])
        for policy in policies
    }
    return {
        "schema_version": 3,
        "created_at": datetime.now(UTC).isoformat(),
        "configuration": config,
        "scenario_id": config.get("scenario_id", config["name"]),
        "scenario_version": config.get("scenario_version", "1"),
        "seeds": seeds,
        "policies": policies,
        "live_model_enabled": live_model,
        "model_provider": "nebius-token-factory" if live_model else None,
        "model_id": os.getenv("GRIDMIND_MODEL") if live_model else None,
        "comparison": comparison,
        "paired_comparison_vs_resource_aware": paired_comparison(records, policies),
        "runs": records,
        "limitations": [
            "Synthetic one-minute simulation; power and energy are not facility telemetry.",
            "Results are scenario- and seed-specific; small samples are not statistically conclusive.",
            "Every policy runs the same declared fixed horizon; unresolved workload outcomes are reported separately from execution status.",
            "Offline Nemotron policy records fallback execution, not model inference.",
            "Model-generated explanations are rationales, not causal proof.",
        ],
    }


def run_scenario_suite(
    seeds: list[int],
    *,
    policies: list[str] | None = None,
    live_model: bool = False,
    suite_path: str | Path | None = None,
) -> dict[str, Any]:
    suite = load_scenario_suite(suite_path) if suite_path else load_scenario_suite()
    definitions = suite["scenarios"]
    policies = list(POLICIES) if policies is None else policies
    total_runs = len(definitions) * len(seeds) * len(policies)
    estimated_steps = sum(item["max_steps"] for item in definitions) * len(seeds) * len(policies)
    if total_runs > MAX_SUITE_RUNS or estimated_steps > MAX_SUITE_POLICY_STEPS:
        raise ValueError(
            f"Scenario suite request exceeds bounds "
            f"({total_runs} runs, {estimated_steps} maximum policy-steps)"
        )
    scenario_results = {}
    all_runs = []
    for config in scenario_configs(suite_path) if suite_path else scenario_configs():
        result = run_experiments(
            config,
            seeds,
            policies=policies,
            live_model=live_model,
            include_history=False,
        )
        scenario_results[result["scenario_id"]] = {
            "configuration": result["configuration"],
            "comparison": result["comparison"],
            "paired_comparison_vs_resource_aware": result[
                "paired_comparison_vs_resource_aware"
            ],
        }
        all_runs.extend(result["runs"])
    return {
        "schema_version": 3,
        "created_at": datetime.now(UTC).isoformat(),
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "seeds": seeds,
        "policies": policies,
        "live_model_enabled": live_model,
        "model_id": os.getenv("GRIDMIND_MODEL") if live_model else None,
        "scenario_count": len(scenario_results),
        "scenarios": scenario_results,
        "runs": all_runs,
        "limitations": [
            "All workload, topology, power, failure, and price values are synthetic.",
            "Each policy is paired by seed and scenario hash and executes the entire fixed horizon; recorded exogenous node-failure traces must match.",
            "Uncertainty is summarized over scenario-seed run pairs, not jobs or simulation ticks.",
            "Offline Nemotron is deterministic resource-aware fallback, not live model inference.",
            "Scenario aggregates should not be combined into one ranking because scenarios differ.",
            "Execution status describes whether the simulation reached its horizon without an exception; it does not imply every workload completed.",
        ],
    }


def paired_comparison(records: list[dict[str, Any]], policies: list[str]) -> dict[str, Any]:
    baseline = {
        (record["seed"], record["scenario_sha256"]): record
        for record in records
        if record["policy"] == "resource_aware" and record["status"] == "completed"
    }
    metrics = (
        "throughput_jobs_per_hour",
        "completion_rate_scenario_denominator",
        "feasible_scenario_completion_rate",
        "deadline_miss_rate",
        "deadline_attainment_rate",
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
            (record["seed"], record["scenario_sha256"]): record
            for record in records
            if record["policy"] == policy and record["status"] == "completed"
        }
        paired_keys = sorted(set(baseline) & set(candidates))
        mismatched_trace_pairs = [
            key
            for key in paired_keys
            if baseline[key].get("exogenous_failure_trace_sha256")
            != candidates[key].get("exogenous_failure_trace_sha256")
        ]
        paired_keys = [
            key for key in paired_keys if key not in set(mismatched_trace_pairs)
        ]
        output[policy] = {
            "paired_successful_seed_count": len(paired_keys),
            "paired_successful_run_count": len(paired_keys),
            "excluded_mismatched_failure_trace_pairs": len(mismatched_trace_pairs),
            "paired_scenario_hash_count": len(
                {scenario_hash for _, scenario_hash in paired_keys}
            ),
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
                    [
                        candidates[key]["metrics"].get(metric)
                        for key in paired_keys
                    ],
                    [
                        baseline[key]["metrics"].get(metric)
                        for key in paired_keys
                    ],
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
    deltas = [value - base for value, base in pairs]
    interval = bootstrap_mean_interval(deltas, seed=20_261_027)
    return {
        "mean_delta": round(statistics.fmean(deltas), 6) if deltas else None,
        "sample_stddev": round(statistics.stdev(deltas), 6)
        if len(deltas) > 1
        else None,
        "confidence_interval_95": interval,
        "n": len(deltas),
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
        "scenario_id",
        "scenario_version",
        "scenario_sha256",
        "policy",
        "policy_version",
        "simulator_version",
        "seed",
        "live_model_enabled",
        "model_id",
        "model_execution_mode",
        "status",
        "steps_executed",
        "termination_reason",
        "workloads_terminal_at_step",
        "error_type",
        "policy_sha256",
        "exogenous_failure_trace_sha256",
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
    if "scenarios" in result:
        return render_suite_report(result)
    lines = [
        "# GridMind experiment report",
        "",
        f"- Created: `{result['created_at']}`",
        f"- Seeds: `{', '.join(map(str, result['seeds']))}`",
        f"- Scenario: `{result['configuration']['name']}`",
        f"- Live model enabled: `{result['live_model_enabled']}`",
        f"- Model ID: `{result['model_id'] or 'not used'}`",
        "",
        "## Policy summaries",
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
                "A completed run reached the fixed horizon without a simulation exception; "
                "it does not mean all workloads completed. Aggregated metrics use successful "
                "executions only; failed runs remain in the run and error counts. Power, energy, "
                "and cost are synthetic estimates, not facility telemetry or a cloud bill."
            ),
            "",
            "## Paired comparison against resource-aware",
            "",
            (
                "Only matched scenario-hash/seed pairs where both simulations reached the "
                "horizon are used. Unresolved jobs remain part of each run's workload metrics."
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


def _format_delta(deltas: dict[str, Any], name: str) -> str:
    metric = deltas[name]
    interval = metric["confidence_interval_95"]
    if interval["lower"] is None:
        return f"{metric['mean_delta']} (CI unavailable: {interval['status']})"
    return f"{metric['mean_delta']} ({interval['lower']}, {interval['upper']})"


def render_suite_report(result: dict[str, Any]) -> str:
    lines = [
        f"# GridMind scenario suite {result['suite_version']}",
        "",
        f"- Suite: `{result['suite_id']}`",
        f"- Seeds: `{', '.join(map(str, result['seeds']))}`",
        f"- Scenario count: `{result['scenario_count']}`",
        f"- Run count: `{len(result['runs'])}`",
        f"- Live inference enabled: `{result['live_model_enabled']}`",
        "",
        "All workload, topology, power, energy, and price data are synthetic. A completed run means the simulator reached its fixed horizon without an exception; it does not mean the workload queue drained.",
        "Primary horizons are fixed per scenario version and are not extended for a favored policy. Descriptive bootstrap intervals use matched independent scenario-seed runs; they are omitted below five valid pairs.",
        "",
    ]
    for scenario_id, scenario in result["scenarios"].items():
        def ratio(numerator: int, denominator: int) -> str:
            if denominator == 0:
                return "n/a"
            return f"{numerator}/{denominator} ({numerator / denominator:.1%})"

        lines.extend(
            [
                f"## {scenario['configuration']['name']} (`{scenario_id}`)",
                "",
                scenario["configuration"]["intended_stress"],
                "",
                f"Horizon: {scenario['configuration']['max_steps']} steps. {scenario['configuration']['horizon_rationale']}",
                "",
                "| Policy | Run status (complete/failed/incomplete) | Completed / all workloads | Operational failures | Cancelled | Permanently infeasible | Unresolved at horizon | Full-set completion | Feasible completion | Deadline misses / due | Deadline attained | Starved | Node failures / recoveries / requeues / preemptions | Resource / power rejections | Throughput jobs/hour | Queue wait min | Turnaround min | Energy kWh / estimated cost | Paired n vs resource-aware |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for policy, summary in scenario["comparison"].items():
            totals = summary["workload_totals"]
            metrics = summary["metrics"]
            paired = scenario["paired_comparison_vs_resource_aware"].get(policy)
            status_counts = summary["run_status_counts"]
            def mean(
                metric: str, metric_values: dict[str, Any] = metrics
            ) -> str:
                value = metric_values[metric]["mean"]
                return "n/a" if value is None else str(value)

            pair_n = (
                paired["mean_policy_minus_resource_aware"][
                    "throughput_jobs_per_hour"
                ]["n"]
                if paired
                else "—"
            )
            lines.append(
                f"| {policy} | {status_counts.get('completed', 0)}/{status_counts.get('failed', 0)}/{status_counts.get('incomplete', 0)} "
                f"| {totals['completed_workloads']}/{totals['total_workloads']} "
                f"| {totals['execution_failed_workloads']} "
                f"| {totals['cancelled_workloads']} "
                f"| {totals['permanently_infeasible_workloads']} "
                f"| {totals['horizon_incomplete_workloads']} "
                f"| {ratio(totals['completed_workloads'], totals['total_workloads'])} "
                f"| {ratio(totals['feasible_completed_workloads'], totals['feasible_workloads'])} "
                f"| {ratio(totals['deadline_misses'], totals['deadline_miss_denominator'])} "
                f"| {ratio(totals['deadline_attained_workloads'], totals['deadline_attainment_denominator'])} "
                f"| {totals['starved_workloads']} "
                f"| {totals['failed_nodes']}/{totals['recovered_nodes']}/{totals['workloads_requeued']}/{totals['workloads_preempted']} "
                f"| {totals['resource_rejections']}/{totals['node_power_rejections'] + totals['facility_power_rejections']} "
                f"| {mean('throughput_jobs_per_hour')} "
                f"| {mean('average_queue_wait_minutes')} "
                f"| {mean('average_turnaround_minutes')} "
                f"| {mean('estimated_energy_kwh')} / {mean('estimated_energy_cost')} "
                f"| {pair_n} |"
            )
        lines.extend(
            [
                "",
                (
                    "Workload totals in this table pool successful fixed-horizon runs; "
                    "failed simulation records and their partial state remain available in JSON/CSV. "
                    "Run-status counts are separate from workload statuses. The full-set "
                    "completion denominator includes every materialized workload, including "
                    "infeasible and not-yet-arrived jobs. Feasible completion uses all "
                    "structurally placeable scenario workloads. Deadline-miss denominator "
                    "counts deadlines that elapsed or completed late; deadline attainment "
                    "uses all submitted workloads with deadlines. Post-deadline work remains "
                    "eligible. Cost is an estimate from the configured synthetic energy rate."
                ),
                "",
                "| Policy | Primary unresolved outcome classification (count) |",
                "|---|---|",
            ]
        )
        for policy, summary in scenario["comparison"].items():
            reasons = summary["horizon_incomplete_reason_totals"] or {}
            rendered_reasons = ", ".join(
                f"{reason}: {count}" for reason, count in reasons.items()
            ) or "none"
            lines.append(f"| {policy} | {rendered_reasons} |")
        lines.extend(
            [
                "",
                "| Policy | Last actionable blocker for unresolved workloads (count) |",
                "|---|---|",
            ]
        )
        for policy, summary in scenario["comparison"].items():
            reasons = summary["horizon_incomplete_blocking_reason_totals"] or {}
            rendered_reasons = ", ".join(
                f"{reason}: {count}" for reason, count in reasons.items()
            ) or "none"
            lines.append(f"| {policy} | {rendered_reasons} |")
        lines.extend(
            [
                "",
                "| Policy vs resource-aware | Valid paired n | Throughput delta (95% descriptive CI) | Deadline-attainment delta (95% descriptive CI) | Energy delta kWh (95% descriptive CI) |",
                "|---|---:|---|---|---|",
            ]
        )
        for policy, comparison in scenario[
            "paired_comparison_vs_resource_aware"
        ].items():
            deltas = comparison["mean_policy_minus_resource_aware"]

            lines.append(
                f"| {policy} | {comparison['paired_successful_run_count']} "
                f"| {_format_delta(deltas, 'throughput_jobs_per_hour')} "
                f"| {_format_delta(deltas, 'deadline_attainment_rate')} "
                f"| {_format_delta(deltas, 'estimated_energy_kwh')} |"
            )
        lines.append("")
    lines.extend(["## Limitations", ""])
    lines.extend(f"- {item}" for item in result["limitations"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/demo.json")
    parser.add_argument("--suite", help="Run the versioned scenario suite JSON instead of one config.")
    parser.add_argument("--seeds", help="Comma-separated seeds (default: 1–20).")
    parser.add_argument("--policies", default=",".join(POLICIES))
    parser.add_argument("--output-dir", default="benchmarks/latest")
    parser.add_argument(
        "--live-model",
        action="store_true",
        help="Make actual Nebius requests for Nemotron runs; requires explicit credentials and model ID.",
    )
    args = parser.parse_args(argv)
    try:
        seeds = (
            [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
            if args.seeds
            else list(range(1, 21))
        )
        policies = [value.strip() for value in args.policies.split(",") if value.strip()]
        if args.suite and args.live_model:
            raise ValueError(
                "Live model requests must target one bounded scenario config, not the full suite"
            )
        live_preflight = _run_live_preflight() if args.live_model else None
        if args.suite:
            result = run_scenario_suite(
                seeds,
                policies=policies,
                suite_path=args.suite,
            )
        else:
            config = load_config(args.config)
            result = run_experiments(
                config,
                seeds,
                policies=policies,
                live_model=args.live_model,
                live_verified=bool(live_preflight),
            )
        if live_preflight is not None:
            result["live_preflight"] = live_preflight
        paths = write_results(result, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "run_count": len(result["runs"]),
                "scenario_count": result.get("scenario_count", 1),
                "outputs": paths,
            },
            indent=2,
        )
    )
    return 0


def _run_live_preflight() -> dict[str, Any]:
    api_key = os.getenv("NEBIUS_API_KEY")
    model_id = os.getenv("GRIDMIND_MODEL")
    if not api_key or not model_id:
        raise ValueError("--live-model requires NEBIUS_API_KEY and GRIDMIND_MODEL")
    normalized_model_id = model_id.casefold()
    if (
        model_id != model_id.strip()
        or any(ord(char) < 32 for char in model_id)
        or len(model_id) > 200
        or api_key in model_id
        or not normalized_model_id.startswith("nvidia/")
        or "nemotron" not in normalized_model_id
    ):
        raise ValueError("--live-model requires an NVIDIA Nemotron model ID")
    try:
        timeout_seconds = configured_inference_timeout_seconds()
        configured_base_url()
    except ValueError as exc:
        raise ValueError("Live model provider configuration is invalid") from exc
    try:
        model_available = verify_catalogue_model(
            model_id, api_key, timeout=min(timeout_seconds, 10.0)
        )
    except RuntimeError as exc:
        raise ValueError("Live model catalogue verification failed (details sanitized)") from exc
    if not model_available:
        raise ValueError("Configured model ID is not listed in the live catalogue")
    simulator = DatacenterSimulator(seed=17)
    proposal = request_proposal(simulator.state())
    rejections = (
        simulator.validate_assignments(proposal.assignments)
        if proposal.used_model
        else []
    )
    if proposal.used_model and not proposal.assignments:
        rejections.append({"workload_id": "", "reason": "empty_assignments"})
    if not proposal.used_model or rejections:
        raise ValueError(
            "Live model preflight failed: "
            + (proposal.error_code or "invalid_model_proposal")
        )
    return {
        "status": "live_success",
        "provider": "nebius-token-factory",
        "model_id": model_id,
        "test_time_utc": datetime.now(UTC).isoformat(),
        "request_attempts": proposal.request_attempts,
        "retry_count": max(0, proposal.request_attempts - 1),
        "latency_ms": proposal.latency_ms,
        "prompt_tokens": proposal.prompt_tokens,
        "completion_tokens": proposal.completion_tokens,
        "proposal_validated": True,
    }


if __name__ == "__main__":
    sys.exit(main())
