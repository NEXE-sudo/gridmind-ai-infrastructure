import pytest

from server.datacenter_simulator import DatacenterSimulator, Node, Workload
from server.workload_scheduler import schedule


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


def test_unknown_node_is_rejected_without_starting_job():
    sim = DatacenterSimulator()
    state = sim.apply_action({"train-001": "does-not-exist"})
    assert state["rejected_actions"] == [
        {"workload_id": "train-001", "reason": "unknown_node"}
    ]
    assert next(w for w in sim.workloads if w.id == "train-001").status == "pending"


def test_capacity_violation_is_rejected():
    sim = DatacenterSimulator()
    sim.nodes = [Node("small", 1, 8, 1.0)]
    sim.workloads = [Workload("large", "oversized", 2, 16, 2)]
    sim._allocations()

    state = sim.apply_action({"large": "small"})
    assert state["rejected_actions"][0]["reason"] == "insufficient_or_unavailable_resources"
    assert sim.workloads[0].status == "pending"


def test_node_and_power_limits_are_enforced():
    sim = DatacenterSimulator(power_budget_kw=0.7)
    result = sim.apply_action({"infer-001": "gpu-a"})
    assert result["rejected_actions"] == [
        {"workload_id": "infer-001", "reason": "power_budget_exceeded"}
    ]

    sim = DatacenterSimulator()
    sim.nodes = [Node("small-power", 2, 80, 0.5, idle_kw=0.2, per_gpu_kw=0.4)]
    sim.workloads = [Workload("job", "Power constrained", 1, 8, 1)]
    sim._allocations()
    result = sim.apply_action({"job": "small-power"})
    assert result["rejected_actions"] == [
        {"workload_id": "job", "reason": "node_power_limit_exceeded"}
    ]


def test_completed_workload_consumes_energy_for_its_final_tick():
    sim = DatacenterSimulator()
    first = sim.apply_action({"infer-001": "gpu-a"})
    assert first["metrics"]["estimated_energy_kwh"] == round(1.25 / 60, 5)
    assert next(w for w in sim.workloads if w.id == "infer-001").remaining == 1

    second = sim.apply_action()
    workload = next(w for w in sim.workloads if w.id == "infer-001")
    assert workload.status == "completed"
    assert workload.completed_at == 2
    assert second["metrics"]["completed_workloads"] == 1
    assert second["metrics"]["estimated_energy_kwh"] == round(2.5 / 60, 5)


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
