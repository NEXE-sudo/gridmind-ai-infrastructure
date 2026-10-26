"""Separate GridMind API; the legacy energy-grid app is left untouched."""
from typing import Any
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .datacenter_simulator import DatacenterSimulator
from .workload_scheduler import schedule, nemotron_propose

app=FastAPI(title="GridMind Data-Centre Operations API",version="0.1.0",
 description="Simulation-only GPU scheduling. Power values are estimates, not telemetry.")
sim=DatacenterSimulator()

class StepRequest(BaseModel):
    assignments: dict[str,str]=Field(default_factory=dict)
    preempt: list[str]=Field(default_factory=list)
class ResetRequest(BaseModel):
    seed: int|None=None
class RunRequest(BaseModel):
    policy: str="resource_aware"
    steps: int=Field(default=1,ge=1,le=100)

@app.get("/health")
def health(): return {"status":"ok","service":"gridmind","mode":"simulation-only"}
@app.get("/state")
def state()->dict[str,Any]: return sim.state()
@app.get("/policies")
def policies():
    return {"policies":[{"id":"fifo","description":"FIFO baseline"},{"id":"priority","description":"Priority and deadline ordering"},
      {"id":"resource_aware","description":"Priority/deadline and resource-fit packing"},{"id":"nemotron","description":"Nebius Nemotron proposal with deterministic fallback"}],
      "model_configured":bool(os.getenv("NEBIUS_API_KEY")),"power_is_estimated":True}
@app.post("/reset")
def reset(req:ResetRequest): return sim.reset(req.seed)
@app.post("/step")
def step(req:StepRequest): return sim.apply_action(req.assignments,req.preempt)
@app.post("/run")
def run(req:RunRequest):
    if req.policy not in {"fifo","priority","resource_aware","nemotron"}: raise HTTPException(400,"Unsupported policy")
    history=[]
    for _ in range(req.steps):
        proposed=nemotron_propose(sim.state()) if req.policy=="nemotron" else schedule(sim,req.policy)
        if req.policy=="nemotron" and not proposed: proposed=schedule(sim,"resource_aware")
        history.append(sim.apply_action(proposed))
        if not any(w.status in {"pending","running"} for w in sim.workloads): break
    return {"policy":req.policy,"steps_executed":len(history),"final_state":sim.state(),"history":history}
