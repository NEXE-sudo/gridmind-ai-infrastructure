from server.datacenter_simulator import DatacenterSimulator, Node, Workload
from server.workload_scheduler import schedule

def test_seeded_state_is_reproducible():
    assert DatacenterSimulator(seed=21).state()==DatacenterSimulator(seed=21).state()

def test_scheduler_uses_known_ids():
    sim=DatacenterSimulator()
    result=schedule(sim)
    assert set(result)<={w.id for w in sim.workloads}
    assert set(result.values())<={n.id for n in sim.nodes}

def test_unknown_node_is_rejected_without_starting_job():
    sim=DatacenterSimulator()
    state=sim.apply_action({"train-001":"does-not-exist"})
    assert state["rejected_actions"]==[{"workload_id":"train-001","reason":"unknown_node"}]
    assert next(w for w in sim.workloads if w.id=="train-001").status=="pending"

def test_capacity_violation_is_rejected():
    sim=DatacenterSimulator()
    sim.nodes=[Node("small",1,8,1.0)]
    sim.workloads=[Workload("large","oversized",2,16,2)]
    state=sim.apply_action({"large":"small"})
    assert state["rejected_actions"][0]["reason"]=="insufficient_or_unavailable_resources"

def test_step_metrics_are_sane():
    sim=DatacenterSimulator()
    state=sim.apply_action(schedule(sim))
    assert state["step"]==1
    assert 0<=state["metrics"]["gpu_utilization"]<=1
    assert state["metrics"]["estimated_energy_kwh"]>=0

def test_unknown_policy_fails_loudly():
    import pytest
    with pytest.raises(ValueError): schedule(DatacenterSimulator(),"unknown")
