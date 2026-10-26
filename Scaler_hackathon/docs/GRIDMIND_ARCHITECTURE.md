# GridMind architecture

## Runtime flow

Client -> FastAPI -> deterministic policy or optional Nemotron proposal ->
simulator validation -> state, metrics, rejected-action reasons.

## Components

- server/datacenter_simulator.py: node/workload state, capacity checks, progress,
  estimated energy, and metrics.
- server/workload_scheduler.py: FIFO, priority, resource-aware policies and
  optional model proposal. The model path fails closed to deterministic fallback.
- server/gridmind_app.py: isolated API entry point.
- tests/test_gridmind_simulator.py: reproducibility, policy contract, invalid
  actions, and metric invariants.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | /health | Service health and simulation-only mode |
| GET | /state | Current nodes, workloads, metrics |
| GET | /policies | Available policies and model configuration status |
| POST | /reset | Reset simulator, optionally with a seed |
| POST | /step | Apply placements and advance one tick |
| POST | /run | Run a policy for a bounded number of ticks |

## Limitations

No Kubernetes integration, real cluster connection, NVIDIA telemetry, MIG
management, CUDA instrumentation, or hardware actuation exists in this phase.
Power and energy are estimates. Verify the current Nebius model identifier
before claiming a successful live Nemotron integration.
