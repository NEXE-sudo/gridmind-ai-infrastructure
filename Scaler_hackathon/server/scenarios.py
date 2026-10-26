"""Versioned synthetic scenario catalogue for GridMind experiments."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

SCENARIO_SUITE_PATH = Path(__file__).resolve().parents[1] / "configs" / "scenarios.json"
ARRIVAL_PATTERNS = {"balanced", "burst", "staggered", "late_short_jobs"}


def load_scenario_suite(path: str | Path = SCENARIO_SUITE_PATH) -> dict[str, Any]:
    try:
        suite = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read the GridMind scenario suite") from exc
    if (
        not isinstance(suite, dict)
        or suite.get("synthetic") is not True
        or not isinstance(suite.get("suite_id"), str)
        or not isinstance(suite.get("suite_version"), str)
        or not isinstance(suite.get("topologies"), dict)
        or not isinstance(suite.get("scenarios"), list)
    ):
        raise ValueError("Scenario suite metadata is invalid")
    ids = [item.get("id") for item in suite["scenarios"] if isinstance(item, dict)]
    if len(ids) != len(suite["scenarios"]) or len(ids) != len(set(ids)):
        raise ValueError("Scenario definitions must have unique IDs")
    for item in suite["scenarios"]:
        if (
            item.get("topology_id") not in suite["topologies"]
            or item.get("workloads", {}).get("arrival_pattern") not in ARRIVAL_PATTERNS
        ):
            raise ValueError(f"Invalid topology or arrival pattern for {item.get('id')}")
    return suite


def scenario_configs(
    path: str | Path = SCENARIO_SUITE_PATH,
) -> list[dict[str, Any]]:
    suite = load_scenario_suite(path)
    return [materialize_scenario(item, suite) for item in suite["scenarios"]]


def get_scenario_config(
    scenario_id: str,
    seed: int,
    path: str | Path = SCENARIO_SUITE_PATH,
) -> dict[str, Any]:
    suite = load_scenario_suite(path)
    definition = next(
        (item for item in suite["scenarios"] if item["id"] == scenario_id),
        None,
    )
    if definition is None:
        raise ValueError("Unknown scenario")
    return materialize_scenario(definition, suite, seed=seed)


def materialize_scenario(
    definition: dict[str, Any],
    suite: dict[str, Any],
    *,
    seed: int = 0,
) -> dict[str, Any]:
    """Expand a profile into explicit workloads with deterministic arrivals."""
    profile = definition["workloads"]
    count = profile["count"]
    rng = random.Random(seed)
    workloads = []
    for index in range(count):
        kind = index % len(profile["gpu_counts"])
        if profile["arrival_pattern"] == "balanced":
            arrival = (index // 2) % 7
        elif profile["arrival_pattern"] == "burst":
            burst_size = max(1, count // 3)
            arrival = (index // burst_size) * 4
        elif profile["arrival_pattern"] == "late_short_jobs":
            arrival = 0 if index < count // 2 else 4 + 2 * (index - count // 2)
            if index >= count // 2:
                kind = len(profile["gpu_counts"]) - 1
        else:
            arrival = index % 8

        required_models = profile.get("required_gpu_models", [])
        required_model = (
            required_models[index % len(required_models)] if required_models else None
        )
        priority = profile["priorities"][kind]
        duration = profile["durations"][kind]
        workloads.append(
            {
                "id": f"{definition['id']}-{index + 1:03d}",
                "name": f"{definition['name']} workload {index + 1:03d}",
                "gpu_count": profile["gpu_counts"][kind],
                "memory_gb": profile["memory_gb"][kind],
                "duration": duration,
                "priority": priority,
                "deadline_after_minutes": profile["deadline_after_minutes"][kind],
                "submission_time": arrival,
                "submitted": arrival == 0,
                "required_gpu_model": required_model,
                "workload_class": (
                    "inference"
                    if priority >= 5
                    else "training"
                    if duration >= 15
                    else "batch"
                ),
            }
        )
    # Balance arrival ties deterministically while keeping the seed's effect
    # on jitter in make_seeded_scenario, where every policy shares the result.
    if profile["arrival_pattern"] == "balanced":
        rng.shuffle(workloads)
        workloads.sort(key=lambda workload: workload["submission_time"])

    return {
        "name": definition["name"],
        "description": definition["description"],
        "intended_stress": definition["intended_stress"],
        "scenario_id": definition["id"],
        "scenario_version": suite["suite_version"],
        "suite_id": suite["suite_id"],
        "seed_behavior": (
            "Workload profile and topology are fixed by suite version; arrival jitter "
            "and failure traces are deterministic for the supplied seed."
        ),
        "synthetic_assumptions": True,
        "power_budget_kw": definition["power_budget_kw"],
        "energy_price_per_kwh": definition["energy_price_per_kwh"],
        "failure_probability": definition["failure_probability"],
        "recovery_steps": definition["recovery_steps"],
        "max_steps": definition["max_steps"],
        "arrival_jitter_steps": 2,
        "nodes": suite["topologies"][definition["topology_id"]],
        "topology_id": definition["topology_id"],
        "workload_parameters": profile,
        "workloads": workloads,
    }
