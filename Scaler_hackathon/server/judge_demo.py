"""Generate and verify the focused, offline judge demonstration evidence."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .benchmarks import (
    POLICY_VERSION,
    SIMULATOR_VERSION,
    make_seeded_scenario,
    run_experiments,
)
from .scenarios import get_scenario_config, load_scenario_suite

SCENARIO_ID = "node_failure_recovery"
SEED = 7
POLICIES = ["fifo", "resource_aware", "nemotron"]
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "benchmarks" / "judge-demo"
PROJECT_DIR = Path(__file__).resolve().parents[1]
SCENARIO_SUITE_PATH = PROJECT_DIR / "configs" / "scenarios.json"
SOURCE_FILES = {
    "benchmark_runner": PROJECT_DIR / "server" / "benchmarks.py",
    "simulator": PROJECT_DIR / "server" / "datacenter_simulator.py",
    "decision_logic": PROJECT_DIR / "server" / "decision.py",
    "scheduler": PROJECT_DIR / "server" / "workload_scheduler.py",
    "scenario_loader": PROJECT_DIR / "server" / "scenarios.py",
    "metrics": PROJECT_DIR / "server" / "metrics.py",
    "demo_generator": Path(__file__).resolve(),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def generate_evidence() -> tuple[dict[str, Any], dict[str, Any], str]:
    suite = load_scenario_suite()
    config = get_scenario_config(SCENARIO_ID, SEED)
    materialized = make_seeded_scenario(config, SEED)
    experiment = run_experiments(
        config,
        [SEED],
        policies=POLICIES,
        live_model=False,
        include_history=True,
    )
    experiment["configuration"] = materialized
    runs = experiment["runs"]
    if len(runs) != len(POLICIES) or any(run["status"] != "completed" for run in runs):
        raise RuntimeError(
            "The focused demo requires all offline runs to reach the horizon"
        )
    if any(run["live_model_enabled"] for run in runs):
        raise RuntimeError("The focused demo must not enable live inference")
    scenario_hashes = {run["scenario_sha256"] for run in runs}
    failure_hashes = {run["exogenous_failure_trace_sha256"] for run in runs}
    if len(scenario_hashes) != 1 or len(failure_hashes) != 1:
        raise RuntimeError("Demo policies must share workload and failure-trace inputs")

    reference = runs[0]
    manifest = {
        "schema_version": 1,
        "demo_id": SCENARIO_ID,
        "scenario_id": SCENARIO_ID,
        "scenario_name": reference["scenario_name"],
        "scenario_suite_id": suite["suite_id"],
        "scenario_suite_version": suite["suite_version"],
        "seed": SEED,
        "horizon_steps": config["max_steps"],
        "policies": [
            {
                "id": run["policy"],
                "version": run["policy_version"],
                "sha256": run["policy_sha256"],
                "mode": run["model_execution_mode"],
            }
            for run in runs
        ],
        "simulator_version": SIMULATOR_VERSION,
        "policy_version": POLICY_VERSION,
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in SOURCE_FILES.items()
        },
        "scenario_suite_sha256": hashlib.sha256(
            SCENARIO_SUITE_PATH.read_bytes()
        ).hexdigest(),
        "scenario_configuration_sha256": _sha256(config),
        "scenario_sha256": reference["scenario_sha256"],
        "workload_set_sha256": _sha256(materialized["workloads"]),
        "topology_sha256": _sha256(config["nodes"]),
        "power_budget_kw": config["power_budget_kw"],
        "failure_probability": config["failure_probability"],
        "recovery_steps": config["recovery_steps"],
        "exogenous_failure_trace_sha256": next(iter(failure_hashes)),
        "live_model_enabled": False,
        "inference_mode": "deterministic_fallback",
        "live_provider_evidence": None,
    }
    manifest_digest = _sha256(manifest)
    result_artifact = {
        "schema_version": 1,
        "manifest_sha256": manifest_digest,
        "experiment": experiment,
    }
    return manifest, result_artifact, render_report(manifest, result_artifact)


def _ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}" + (
        f" ({numerator / denominator:.1%})" if denominator else " (n/a)"
    )


def _format_workload_outcome(workload: dict[str, Any], horizon_steps: int) -> str:
    status = workload["status"]
    if status == "completed":
        outcome = f"completed at step {workload['completed_at']}"
    elif status == "failed":
        outcome = (
            f"failed at step {workload['failed_at']} ({workload['failure_reason']})"
        )
    elif status == "running":
        outcome = (
            f"running on {workload['node_id']} at horizon "
            f"({workload['remaining']} steps remain)"
        )
    else:
        outcome = status
    if workload["failure_count"]:
        unit = "node failure" if workload["failure_count"] == 1 else "node failures"
        outcome += f"; {workload['failure_count']} {unit}"
    deadline = workload["deadline"]
    if deadline is not None and (
        (workload["completed_at"] is not None and workload["completed_at"] > deadline)
        or (workload["completed_at"] is None and horizon_steps >= deadline)
    ):
        outcome += "; deadline missed"
    return outcome


def _diagnostic_examples(
    run: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    placement = next(
        (
            decision
            for step in run["history"]
            for decision in step["placement_diagnostics"]
            if decision.get("assignment_source") == "deterministic_scheduler"
            and decision.get("candidate_nodes")
        ),
        None,
    )
    deferred = next(
        (
            diagnostic
            for step in run["history"]
            for diagnostic in step["scheduling_diagnostics"]
        ),
        None,
    )
    return placement, deferred


def render_report(manifest: dict[str, Any], artifact: dict[str, Any]) -> str:
    experiment = artifact["experiment"]
    runs = {run["policy"]: run for run in experiment["runs"]}
    resource_run = runs["resource_aware"]
    placement, deferred = _diagnostic_examples(resource_run)
    lines = [
        "# GridMind focused demo: node failure and recovery",
        "",
        "Generated from a fresh offline simulator execution by `python -m server.judge_demo`.",
        "All power, energy, workloads, and failures are synthetic. This one-seed demonstration is descriptive, not a statistically supported policy ranking.",
        "",
        "## Reproduction and provenance",
        "",
        f"- Scenario: `{manifest['scenario_id']}` (`{manifest['scenario_name']}`)",
        f"- Seed: `{manifest['seed']}`; fixed horizon: `{manifest['horizon_steps']}` one-minute steps",
        f"- Scenario suite: `{manifest['scenario_suite_id']}@{manifest['scenario_suite_version']}`",
        f"- Materialized workload hash: `{manifest['scenario_sha256']}`",
        f"- Shared failure-trace hash: `{manifest['exogenous_failure_trace_sha256']}`",
        f"- Manifest hash: `{artifact['manifest_sha256']}`",
        "- Live inference: **not attempted**. The Nemotron row uses deterministic resource-aware fallback.",
        "",
        "## Initial state",
        "",
        "| Node | GPU model | GPUs | Memory (GB) | Node power limit (kW) |",
        "|---|---|---:|---:|---:|",
    ]
    for node in experiment["configuration"]["nodes"]:
        lines.append(
            f"| {node['id']} | {node['gpu_model']} | {node['gpu_count']} "
            f"| {node['memory_gb']} | {node['power_limit_kw']} |"
        )
    lines.extend(
        [
            "",
            (
                f"Facility power budget: **{manifest['power_budget_kw']} kW**; "
                f"per-step node-failure probability: **{manifest['failure_probability']:.0%}**; "
                f"node recovery delay: **{manifest['recovery_steps']} steps**."
            ),
            "",
            "| Workload | Arrival step | Priority | GPUs | Memory (GB) | Duration (steps) | Deadline step |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for workload in experiment["configuration"]["workloads"]:
        lines.append(
            f"| {workload['id']} | {workload['submission_time']} | {workload['priority']} "
            f"| {workload['gpu_count']} | {workload['memory_gb']} | {workload['duration']} "
            f"| {workload.get('deadline', 'none')} |"
        )
    lines.extend(
        [
            "",
            "## Scheduler decision trace",
            "",
        ]
    )
    if placement:
        lines.extend(
            [
                (
                    f"The resource-aware policy placed **{placement['workload_id']}** on "
                    f"**{placement['node_id']}** at queue rank {placement['queue_rank']}. "
                    f"It selected the candidate with the greatest post-placement GPU fill; "
                    "ties use the lexicographically largest node ID."
                ),
                "",
                "| Feasible candidate | Projected GPU fill | GPUs free before | Memory free before (GB) | Power delta (kW) | Selected |",
                "|---|---:|---:|---:|---:|:---:|",
            ]
        )
        for candidate in placement["candidate_nodes"]:
            lines.append(
                f"| {candidate['node_id']} | {candidate['projected_gpu_fill']:.3f} "
                f"| {candidate['free_gpus_before']} | {candidate['free_memory_gb_before']} "
                f"| {candidate['power_delta_kw']:.3f} "
                f"| {'yes' if candidate['selected'] else 'no'} |"
            )
    else:
        lines.append("No successful placement candidate was recorded.")
    if deferred:
        lines.extend(
            [
                "",
                (
                    f"An actual deferred-work diagnostic for **{deferred['workload_id']}** at "
                    f"step {deferred['step']} reported `{deferred['reason']}`. "
                    f"Per-node checks: `{_canonical_json(deferred['node_reasons'])}`. "
                    "This is a point-in-time reason, not a claim that the workload was infeasible forever."
                ),
            ]
        )
    else:
        lines.extend(
            ["", "No deferral diagnostic was recorded in the resource-aware run."]
        )

    lines.extend(
        [
            "",
            "## Fixed-horizon operational outcomes",
            "",
            f"Each policy receives the same materialized workload set and exogenous failure trace and runs all {manifest['horizon_steps']} steps. Each status cell counts all {len(experiment['configuration']['workloads'])} scenario workloads. `Completed run` means the simulation reached its horizon; it does not mean every workload completed.",
            "",
            "| Policy | Execution | Workload status counts | Completed / all | Deadline misses / due | Deadline attained / all deadlines | Mean queue wait (minutes / samples) | Throughput (jobs/hour) |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for policy in POLICIES:
        run = runs[policy]
        metrics = run["metrics"]
        counts = metrics["workload_status_counts"]
        status_text = ", ".join(
            f"{status} {counts.get(status, 0)}"
            for status in ("completed", "failed", "cancelled", "pending", "running")
        )
        queue_wait = metrics["average_queue_wait_minutes"]
        wait_text = (
            f"{queue_wait} ({metrics['sample_count_wait_times']} samples)"
            if queue_wait is not None
            else "n/a (0 samples)"
        )
        lines.append(
            f"| {policy} (`{run['model_execution_mode']}`) | "
            f"{run['status']} {run['steps_executed']}/{manifest['horizon_steps']} steps "
            f"| {status_text} ({metrics['total_workloads']} total) "
            f"| {_ratio(metrics['completed_workloads'], metrics['total_workloads'])} "
            f"| {_ratio(metrics['deadline_misses'], metrics['deadline_miss_denominator'])} "
            f"| {_ratio(metrics['deadline_attained_workloads'], metrics['deadline_attainment_denominator'])} "
            f"| {wait_text} | {metrics['throughput_jobs_per_hour']} |"
        )
    lines.extend(
        [
            "",
            "## Synthetic infrastructure outcomes",
            "",
            "| Policy | Estimated energy (kWh) | Estimated energy cost (currency unit unspecified) | Power-budget violations | Node failures / recoveries |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for policy in POLICIES:
        run = runs[policy]
        metrics = run["metrics"]
        lines.append(
            f"| {policy} | {metrics['estimated_energy_kwh']} "
            f"| {metrics['estimated_energy_cost']} at configured synthetic tariff "
            f"{metrics['energy_price_per_kwh']}/kWh "
            f"| {metrics['power_budget_violations']} "
            f"| {run['event_counts'].get('node_failed', 0)} / {run['event_counts'].get('node_recovered', 0)} |"
        )
    nemotron_metrics = runs["nemotron"]["metrics"]
    lines.extend(
        [
            "",
            f"Offline Nemotron telemetry: **{nemotron_metrics['ai_attempts']}** scheduler decision attempts, **{nemotron_metrics['ai_invocations']}** provider invocations, **{nemotron_metrics['ai_fallbacks']}** deterministic fallback decisions, **{nemotron_metrics['ai_failures']}** provider failures, no provider latency, and no returned token usage. The policy attempted no live inference.",
            "",
            "The deadline-miss denominator is workloads whose deadlines were due by the end of the run; deadline attainment uses all workloads with a declared deadline. Queue-wait mean uses completed-workload samples only, with the sample count shown. Energy and its cost estimate use synthetic simulator output and a configured price input whose currency is unspecified; they are neither facility telemetry nor a cloud bill.",
            "",
            "### Per-workload outcomes",
            "",
            "| Workload | FIFO | Resource-aware | Nemotron (offline fallback) |",
            "|---|---|---|---|",
        ]
    )
    state_by_policy = {
        policy: {
            workload["id"]: workload for workload in runs[policy]["workload_state"]
        }
        for policy in POLICIES
    }
    for workload in experiment["configuration"]["workloads"]:
        workload_id = workload["id"]
        lines.append(
            f"| {workload_id} | "
            + " | ".join(
                _format_workload_outcome(
                    state_by_policy[policy][workload_id],
                    manifest["horizon_steps"],
                )
                for policy in POLICIES
            )
            + " |"
        )
    lines.extend(["", "### Failure and horizon diagnosis", ""])
    for policy in POLICIES:
        run = runs[policy]
        metrics = run["metrics"]
        failed = [
            workload
            for workload in run["workload_state"]
            if workload["status"] == "failed"
        ]
        unresolved = [
            workload
            for workload in run["workload_state"]
            if workload["status"] in {"pending", "running"}
        ]
        failure_summary = (
            ", ".join(
                f"{workload['id']} (`{workload['failure_reason']}`, "
                f"{workload['failure_count']} node failures)"
                for workload in failed
            )
            or "none"
        )
        unresolved_summary = (
            ", ".join(
                f"{workload['id']} ({workload['status']}, {workload['remaining']} steps remain, "
                f"{metrics['workload_outcome_classifications'].get(workload['id'], 'unclassified')})"
                for workload in unresolved
            )
            or "none"
        )
        lines.append(
            f"- **{policy}:** {metrics['permanently_infeasible_workloads']} permanently "
            f"infeasible, {metrics['rejected_actions']} rejected actions, "
            f"{metrics['power_budget_violations']} power-budget violations; "
            f"operational failures: {failure_summary}; unresolved at step "
            f"{manifest['horizon_steps']}: {unresolved_summary}. "
            f"Horizon diagnoses: `{_canonical_json(metrics['horizon_incomplete_reason_counts'])}`."
        )
    lines.extend(
        [
            "",
            "## What this establishes—and does not",
            "",
            "- Establishes that the offline simulator executes the seeded failure/recovery scenario, retains decision diagnostics, and produces reproducible paired policy records.",
            "- The table is one paired seed (`n=1` run per policy). It does not establish a general policy winner, model benefit, real infrastructure behavior, or real-world energy savings.",
            "- The `nemotron` record is **deterministic fallback**, with no live provider call, model identity claim, or provider telemetry.",
            "- Workloads still pending/running at the fixed horizon remain in the results; the horizon is not extended to drain the queue.",
            "",
        ]
    )
    return "\n".join(lines)


def _remove_intentional_timestamps(result: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(result)
    experiment = normalized.get("experiment")
    if isinstance(experiment, dict):
        experiment.pop("created_at", None)
        runs = experiment.get("runs")
        if isinstance(runs, list):
            for run in runs:
                if isinstance(run, dict):
                    run.pop("created_at", None)
    return normalized


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def check_evidence(output_dir: Path = OUTPUT_DIR) -> bool:
    manifest, result, report = generate_evidence()
    try:
        stored_manifest = json.loads(
            (output_dir / "manifest.json").read_text(encoding="utf-8")
        )
        stored_result = json.loads(
            (output_dir / "results.json").read_text(encoding="utf-8")
        )
        stored_report = (output_dir / "report.md").read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"Demo evidence is unavailable or invalid: {exc.__class__.__name__}",
            file=sys.stderr,
        )
        return False
    comparisons = {
        "manifest.json": stored_manifest == manifest,
        "results.json": _remove_intentional_timestamps(stored_result)
        == _remove_intentional_timestamps(result),
        "report.md": stored_report == report,
    }
    for name, matches in comparisons.items():
        print(f"{'MATCH' if matches else 'DIFF'} {name}")
    if all(comparisons.values()):
        print(
            "Offline demo evidence is reproducible; only created_at timestamps are excluded."
        )
        return True
    return False


def write_evidence(output_dir: Path = OUTPUT_DIR) -> None:
    manifest, result, report = generate_evidence()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_bytes(_json_bytes(manifest))
    (output_dir / "results.json").write_bytes(_json_bytes(result))
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    print(f"Wrote deterministic offline demo evidence to {output_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare a fresh run to checked-in evidence",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    if args.check:
        return 0 if check_evidence(args.output_dir) else 1
    write_evidence(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
