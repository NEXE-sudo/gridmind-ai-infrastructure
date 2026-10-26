
from server.datacenter_simulator import DatacenterSimulator, Node, Workload
from server.metrics import (
    aggregate_runs,
    bootstrap_mean_interval,
    calculate_metrics,
    percentile,
)


def test_hand_calculated_queue_wait_turnaround_energy_and_cost():
    sim = DatacenterSimulator(
        power_budget_kw=2,
        energy_price_per_kwh=0.12,
        nodes=[Node("n", 1, 16, 1.2, idle_kw=0, per_gpu_kw=1)],
        workloads=[Workload("job", "test", 1, 8, 2, deadline=5)],
    )
    sim.apply_action()
    sim.apply_action({"job": "n"})
    sim.apply_action()
    sim.apply_action()

    metrics = calculate_metrics(sim)
    assert metrics["completed_workloads"] == 1
    assert metrics["average_queue_wait_minutes"] == 1
    assert metrics["average_turnaround_minutes"] == 3
    assert metrics["estimated_energy_kwh"] == round(2 / 60, 6)
    assert metrics["estimated_energy_cost"] == round((2 / 60) * 0.12, 6)
    assert metrics["sla_attainment_rate"] == 1
    assert metrics["throughput_jobs_per_hour"] == 15
    assert metrics["average_gpu_utilization"] == 0.5


def test_deadline_miss_includes_unfinished_jobs_at_horizon():
    sim = DatacenterSimulator(
        power_budget_kw=2,
        nodes=[Node("n", 1, 16, 1.2, idle_kw=0, per_gpu_kw=1)],
        workloads=[Workload("late", "deadline", 1, 8, 5, deadline=1)],
    )
    sim.apply_action()
    sim.apply_action()

    metrics = calculate_metrics(sim)
    assert metrics["deadline_misses"] == 1
    assert metrics["deadline_miss_rate"] == 1
    assert metrics["sla_attainment_rate"] == 0
    assert metrics["unfinished_deadline_misses_included"] is True
    assert metrics["completed_count_for_sla"] == 0


def test_percentile_uses_linear_interpolation_and_empty_values():
    assert percentile([], 0.95) is None
    assert percentile([1, 2, 3, 4], 0.5) == 2.5
    assert percentile([1, 2, 3, 4], 0.95) == 3.85


def test_aggregate_retains_failed_and_incomplete_run_counts():
    runs = [
        {
            "status": "completed",
            "metrics": {"throughput_jobs_per_hour": 10, "ai_latency_ms_mean": None},
        },
        {
            "status": "failed",
            "metrics": {"throughput_jobs_per_hour": 2, "ai_latency_ms_mean": None},
        },
        {
            "status": "incomplete",
            "metrics": None,
        },
    ]
    summary = aggregate_runs(runs)
    assert summary["run_count"] == 3
    assert summary["successful_run_count"] == 1
    assert summary["failed_run_count"] == 1
    assert summary["incomplete_run_count"] == 1
    assert summary["metrics"]["throughput_jobs_per_hour"]["n"] == 2
    assert summary["metrics"]["throughput_jobs_per_hour"]["mean"] == 6
    assert summary["metrics"]["ai_latency_ms_mean"]["n"] == 0


def test_starvation_infeasibility_and_class_fairness_metrics():
    sim = DatacenterSimulator(
        nodes=[Node("tiny", 1, 16, 2.0, gpu_model="NVIDIA T4")],
        workloads=[
            Workload(
                "waiting",
                "Long wait",
                1,
                8,
                80,
                submission_time=0,
                workload_class="inference",
            ),
            Workload(
                "impossible",
                "Infeasible",
                4,
                64,
                2,
                submission_time=0,
                workload_class="training",
            ),
        ],
    )
    for _ in range(31):
        sim.apply_action()

    metrics = calculate_metrics(sim)
    assert metrics["starved_workloads"] == 1
    assert metrics["infeasible_pending_workloads"] == 1
    assert metrics["completion_rate_by_workload_class"] == {
        "inference": 0.0,
        "training": 0.0,
    }


def test_bootstrap_interval_is_deterministic_and_requires_independent_samples():
    assert bootstrap_mean_interval([1, 2, 3, 4])["status"] == (
        "insufficient_independent_runs"
    )
    sample = [0.1, 0.2, 0.25, 0.4, 0.6, 0.7]
    first = bootstrap_mean_interval(sample)
    second = bootstrap_mean_interval(sample)
    assert first == second
    assert first["status"] == "descriptive_percentile_bootstrap"
    assert first["lower"] < first["upper"]
