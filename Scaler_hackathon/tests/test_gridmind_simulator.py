import pytest

from server.datacenter_simulator import DatacenterSimulator, Node, Workload
from server.decision import execute_policy_step
from server.workload_scheduler import schedule, schedule_with_diagnostics


def test_seeded_state_is_reproducible():
    assert DatacenterSimulator(seed=21).state() == DatacenterSimulator(seed=21).state()


def test_scheduler_uses_known_ids():
    sim = DatacenterSimulator()
    result = schedule(sim)
    assert set(result) <= {workload.id for workload in sim.workloads}
    assert set(result.values()) <= {node.id for node in sim.nodes}


def test_fifo_preserves_queue_order_and_priority_orders_by_priority():
    sim = DatacenterSimulator()
    sim.nodes = [Node("small", 1, 80, 1.0, idle_kw=0.1, per_gpu_kw=0.5)]
    sim.workloads = [
        Workload("low", "Low priority", 1, 8, 1, priority=1),
        Workload("high", "High priority", 1, 8, 1, priority=5),
    ]
    sim._allocations()

    assert list(schedule(sim, "fifo")) == ["low"]
    assert list(schedule(sim, "priority")) == ["high"]


def test_scheduler_trace_records_feasible_candidates_and_selected_best_fit():
    sim = DatacenterSimulator(
        power_budget_kw=5,
        nodes=[
            Node("wide", 4, 64, 4.0, idle_kw=0.2, per_gpu_kw=0.5),
            Node("compact", 2, 32, 2.0, idle_kw=0.1, per_gpu_kw=0.4),
        ],
        workloads=[Workload("job", "Trace target", 1, 8, 2, priority=3)],
    )

    assignments, diagnostics, placements = schedule_with_diagnostics(
        sim, "resource_aware"
    )

    assert assignments == {"job": "compact"}
    assert diagnostics == []
    placement = placements[0]
    assert placement["assignment_source"] == "deterministic_scheduler"
    assert placement["selection_rule"] == (
        "max_post_placement_gpu_fill_then_lexicographically_largest_node_id"
    )
    assert placement["queue_rank"] == 1
    assert placement["priority"] == 3
    assert placement["candidate_nodes"] == [
        {
            "node_id": "wide",
            "projected_gpu_fill": 0.25,
            "free_gpus_before": 4,
            "free_memory_gb_before": 64,
            "power_delta_kw": 0.5,
            "projected_node_power_kw": 0.7,
            "projected_facility_power_kw": 0.8,
            "selected": False,
        },
        {
            "node_id": "compact",
            "projected_gpu_fill": 0.5,
            "free_gpus_before": 2,
            "free_memory_gb_before": 32,
            "power_delta_kw": 0.4,
            "projected_node_power_kw": 0.5,
            "projected_facility_power_kw": 0.7,
            "selected": True,
        },
    ]


def test_unknown_node_is_rejected_without_starting_job():
    sim = DatacenterSimulator()
    state = sim.apply_action({"train-001": "does-not-exist"})
    assert state["rejected_actions"] == [
        {"workload_id": "train-001", "reason": "unknown_node"}
    ]
    assert next(w for w in sim.workloads if w.id == "train-001").status == "pending"


def test_required_gpu_model_is_enforced_by_scheduler_and_simulator():
    sim = DatacenterSimulator(
        nodes=[Node("t4", 2, 24, 2.0, gpu_model="NVIDIA T4")],
        workloads=[
            Workload(
                "a100-job",
                "A100-only job",
                1,
                8,
                1,
                required_gpu_model="NVIDIA A100",
            )
        ],
    )
    assert schedule(sim, "resource_aware") == {}
    result = sim.apply_action({"a100-job": "t4"})
    assert result["rejected_actions"] == [
        {"workload_id": "a100-job", "reason": "unknown_or_not_eligible"}
    ]
    assert sim.workloads[0].status == "failed"
    assert sim.workloads[0].failure_reason == (
        "permanent_infeasibility:gpu_model_unavailable"
    )


def test_capacity_violation_is_rejected():
    sim = DatacenterSimulator()
    sim.nodes = [Node("small", 1, 8, 1.0)]
    sim.workloads = [Workload("large", "oversized", 2, 16, 2)]
    sim._allocations()

    state = sim.apply_action({"large": "small"})
    assert state["rejected_actions"][0]["reason"] == "gpu_count_exceeds_node_capacity"
    assert sim.workloads[0].status == "pending"


def test_node_and_power_limits_are_enforced():
    sim = DatacenterSimulator(power_budget_kw=0.7)
    result = sim.apply_action({"infer-001": "gpu-a"})
    assert result["rejected_actions"] == [
        {"workload_id": "infer-001", "reason": "unknown_or_not_eligible"}
    ]
    assert next(w for w in sim.workloads if w.id == "infer-001").failure_reason == (
        "permanent_infeasibility:facility_power_limit_exceeded_at_idle"
    )

    sim = DatacenterSimulator()
    sim.nodes = [Node("small-power", 2, 80, 0.5, idle_kw=0.2, per_gpu_kw=0.4)]
    sim.workloads = [Workload("job", "Power constrained", 1, 8, 1)]
    sim._allocations()
    result = sim.apply_action({"job": "small-power"})
    assert result["rejected_actions"] == [
        {"workload_id": "job", "reason": "node_power_limit_exceeded"}
    ]
    assert sim.workloads[0].status == "pending"


def test_completed_workload_consumes_energy_for_its_final_tick():
    sim = DatacenterSimulator()
    first = sim.apply_action({"infer-001": "gpu-a"})
    assert first["metrics"]["estimated_energy_kwh"] == round(1.25 / 60, 6)
    assert next(w for w in sim.workloads if w.id == "infer-001").remaining == 1

    second = sim.apply_action()
    workload = next(w for w in sim.workloads if w.id == "infer-001")
    assert workload.status == "completed"
    assert workload.completed_at == 2
    assert second["metrics"]["completed_workloads"] == 1
    assert second["metrics"]["estimated_energy_kwh"] == round(2.5 / 60, 6)


def test_preemption_preserves_remaining_duration():
    sim = DatacenterSimulator()
    sim.apply_action({"infer-001": "gpu-a"})
    result = sim.apply_action(preempt=["infer-001"])
    workload = next(w for w in sim.workloads if w.id == "infer-001")

    assert workload.status == "pending"
    assert workload.remaining == 1
    assert workload.started_at == 0
    assert result["rejected_actions"] == []


def test_simulated_node_failure_requeues_and_recovers_workload():
    sim = DatacenterSimulator(seed=21, failure_probability=1.0)
    sim.nodes = [Node("only-node", 2, 80, 2.0)]
    sim.workloads = [Workload("job", "Failure test", 1, 8, 4)]
    sim.workloads[0].status = "running"
    sim.workloads[0].node_id = "only-node"
    sim.workloads[0].remaining = 3
    sim.workloads[0].started_at = 0
    sim.step_count = 11
    sim._allocations()

    failed = sim.apply_action()
    workload = sim.workloads[0]
    assert {"type": "node_failed", "node_id": "only-node"} in failed["events"]
    assert workload.status == "pending"
    assert workload.remaining == 3
    assert failed["nodes"][0]["available"] is False
    assert failed["metrics"]["estimated_energy_kwh"] == 0

    sim.failure_probability = 0
    recovered = sim.apply_action({"job": "only-node"})
    assert recovered["nodes"][0]["available"] is True
    assert workload.status == "running"
    assert workload.remaining == 2


def test_step_metrics_are_sane():
    sim = DatacenterSimulator()
    state = sim.apply_action(schedule(sim))
    assert state["step"] == 1
    assert 0 <= state["metrics"]["gpu_utilization"] <= 1
    assert state["metrics"]["estimated_energy_kwh"] >= 0
    assert state["metrics"]["estimated_power_kw"] <= state["power_budget_kw"]


def test_model_assignments_are_validated_before_application():
    sim = DatacenterSimulator()
    proposal = {"train-001": "missing-node"}
    assert sim.validate_assignments(proposal) == [
        {"workload_id": "train-001", "reason": "unknown_node"}
    ]
    result = sim.apply_action(proposal)
    assert result["rejected_actions"] == sim.validate_assignments(proposal)
    assert next(w for w in sim.workloads if w.id == "train-001").status == "pending"


def test_invalid_action_types_are_rejected_without_advancing_state():
    sim = DatacenterSimulator()
    with pytest.raises(TypeError):
        sim.apply_action({1: "gpu-a"})
    assert sim.step_count == 0


def test_unknown_policy_fails_loudly():
    with pytest.raises(ValueError):
        schedule(DatacenterSimulator(), "unknown")


@pytest.mark.parametrize(
    ("nodes", "workload", "power_budget", "reason"),
    [
        (
            [Node("n", 2, 32, 2.0, gpu_model="NVIDIA T4")],
            Workload("j", "model", 1, 8, 1, required_gpu_model="NVIDIA A100"),
            3.0,
            "gpu_model_unavailable",
        ),
        (
            [Node("n", 2, 32, 2.0)],
            Workload("j", "memory", 1, 64, 1),
            3.0,
            "memory_exceeds_node_capacity",
        ),
        (
            [Node("n", 2, 32, 0.5, idle_kw=0.1, per_gpu_kw=0.5)],
            Workload("j", "node power", 1, 8, 1),
            3.0,
            "node_power_limit_exceeded",
        ),
        (
            [Node("n", 2, 32, 2.0, idle_kw=0.1, per_gpu_kw=0.8)],
            Workload("j", "facility power", 2, 8, 1),
            1.5,
            "facility_power_limit_exceeded_at_idle",
        ),
    ],
)
def test_permanent_infeasibility_is_terminal_and_reasoned(
    nodes, workload, power_budget, reason
):
    sim = DatacenterSimulator(
        power_budget_kw=power_budget,
        nodes=nodes,
        workloads=[workload],
    )
    assert workload.status == "failed"
    assert workload.failure_reason == f"permanent_infeasibility:{reason}"
    assert sim.permanent_infeasibility_reason(workload) == reason
    first = sim.prepare_step()
    second = sim.prepare_step()
    failures = [event for event in first + second if event["type"] == "workload_failed"]
    assert len(failures) == 1


def test_temporary_facility_power_contention_resolves_after_running_work_finishes():
    sim = DatacenterSimulator(
        power_budget_kw=1.0,
        nodes=[Node("n", 2, 32, 2.0, idle_kw=0.1, per_gpu_kw=0.5)],
        workloads=[
            Workload("first", "first", 1, 8, 1),
            Workload("second", "second", 1, 8, 1),
        ],
    )
    first = execute_policy_step(sim, "fifo")
    assert first["executed_assignments"] == {"first": "n"}
    assert sim.workloads[1].last_scheduling_reason == (
        "same_decision_reservation_contention"
    )
    second = execute_policy_step(sim, "fifo")
    assert second["executed_assignments"] == {"second": "n"}
    assert [workload.status for workload in sim.workloads] == [
        "completed",
        "completed",
    ]
    assert sim.workloads[1].failure_reason is None


def test_scheduler_observes_node_recovery_before_choosing_assignments():
    node = Node("n", 1, 16, 1.0, idle_kw=0.1, per_gpu_kw=0.5, available=False)
    node.recover_at_step = 0
    sim = DatacenterSimulator(
        nodes=[node],
        workloads=[Workload("job", "recovery", 1, 8, 1)],
    )
    result = execute_policy_step(sim, "fifo")

    assert result["executed_assignments"] == {"job": "n"}
    assert {"type": "node_recovered", "node_id": "n"} in result["events"]
    assert sim.counters["node_recoveries"] == 1
    assert sim.workloads[0].status == "completed"


def test_completion_at_horizon_and_incomplete_work_are_distinguished():
    sim = DatacenterSimulator(
        power_budget_kw=2,
        nodes=[Node("n", 2, 32, 2.0, idle_kw=0, per_gpu_kw=0.5)],
        workloads=[
            Workload("at-cutoff", "at cutoff", 1, 8, 2),
            Workload("past-cutoff", "past cutoff", 1, 8, 3),
        ],
        horizon_steps=2,
    )
    execute_policy_step(sim, "fifo")
    execute_policy_step(sim, "fifo")
    metrics = sim.state()["metrics"]

    assert sim.workloads[0].status == "completed"
    assert sim.workloads[0].completed_at == 2
    assert sim.workloads[1].status == "running"
    assert metrics["horizon_incomplete_workloads"] == 1
    assert metrics["horizon_incomplete_workload_ids"] == ["past-cutoff"]


def test_post_deadline_work_remains_eligible_for_completion():
    sim = DatacenterSimulator(
        power_budget_kw=1,
        nodes=[Node("n", 1, 16, 1, idle_kw=0, per_gpu_kw=0.5)],
        workloads=[Workload("late", "late", 1, 8, 2, deadline=0)],
    )
    first = execute_policy_step(sim, "fifo")
    assert first["executed_assignments"] == {"late": "n"}
    execute_policy_step(sim, "fifo")
    assert sim.workloads[0].status == "completed"
    assert sim.workloads[0].completed_at == 2
    assert sim.state()["metrics"]["deadline_misses"] == 1
