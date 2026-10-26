# GridMind architecture

## Runtime flow

Client -> FastAPI -> deterministic policy or optional Nemotron proposal ->
simulator validation -> state, metrics, rejected-action reasons.

## Components

- server/datacenter_simulator.py: node/workload state, capacity checks, progress,
  estimated energy, and metrics.
- server/workload_scheduler.py: FIFO, priority, resource-aware policies and
  optional model proposal. Malformed proposals and proposals that fail
  simulator-side capacity, node-power, or facility-power validation are
  discarded before application. The API reports deterministic fallback use.
- server/gridmind_app.py: isolated API entry point.
- server/__init__.py: lazy legacy environment export, so importing the
  independent GridMind app does not initialize OpenEnv.
- tests/test_gridmind_simulator.py and tests/test_gridmind_api.py: seeded
  reproducibility, policies, capacity/power checks, job lifecycle, transient
  failures/recovery, request validation, and HTTP contract.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | /health | Service health and simulation-only mode |
| GET | /state | Current nodes, workloads, metrics |
| GET | /policies | Available policies and model configuration status |
| POST | /reset | Reset simulator, optionally with a seed |
| POST | /step | Apply placements and advance one tick |
| POST | /run | Run a policy for a bounded number of ticks |

`/step` rejects malformed request shapes with HTTP 422 and reports infeasible
placements in `rejected_actions`. `/run` uses a strict policy enum and a
1–100-step bound. Its response includes per-step decision labels and whether
the Nemotron path fell back. A node failure lasts for one simulated step,
requeues affected work without discarding remaining runtime, and is visible in
the returned state and event list. Energy is integrated from power during the
simulated step, including the tick on which a job completes.

## Limitations

No Kubernetes integration, real cluster connection, NVIDIA telemetry, MIG
management, CUDA instrumentation, or hardware actuation exists in this phase.
Power and energy are estimates. Verify the current Nebius model identifier
before claiming a successful live Nemotron integration.
