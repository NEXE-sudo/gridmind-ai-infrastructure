# GridMind architecture

## Product boundary

GridMind is an offline-capable, discrete-time data-centre operations simulator.
It does not connect to real GPUs, Kubernetes, NVIDIA telemetry, MIG, or facility
power controls. Each tick represents one synthetic minute. Power coefficients,
energy, and cost are illustrative model inputs rather than hardware readings.
The original electricity-grid application remains in the repository as
historical code; GridMind has its own API and React dashboard.

## Closed-loop flow

1. Load the deterministic scenario and seed, or create a configured dashboard
   scenario (standard, workload surge, node failure, or tight deadlines).
2. Advance workload arrival, node recovery, scheduler selection, and resource
   placement by a single simulator tick.
3. For the optional Nemotron policy, send one compact state proposal request
   through the Nebius Token Factory OpenAI-compatible endpoint.
4. Validate the proposal's schema and every node/resource/power assignment in
   deterministic simulator code. Invalid proposals do not mutate allocations;
   resource-aware scheduling is the fallback.
5. Account for workload progress, completions, failures/requeues, estimated
   power and energy, and per-step metrics.
6. Compare policies on identical materialized scenarios and seeds; retain all
   completed, incomplete, and failed run records.

## Components

- `server/datacenter_simulator.py`: typed nodes and workloads, lifecycle
  transitions, arrivals, preemption/cancellation, failure/recovery, placement
  validation, power accounting, and simulation state.
- `server/workload_scheduler.py`: deterministic FIFO, priority, and
  resource-aware schedulers.
- `server/nemotron.py`: optional Nebius Token Factory adapter, strict response
  parsing, timeout/retry handling, catalogue verification helper, and
  secret-safe provider error reporting.
- `server/decision.py`: single policy decision/execution path, proposal
  validation, fallback selection, and inference counters.
- `server/metrics.py`: common operational definitions and multi-run summaries.
- `server/benchmarks.py`: scenario validation, seeded paired experiments,
  machine-readable exports, and Markdown report generation.
- `server/gridmind_app.py`: bounded FastAPI operations, in-memory experiment
  history, CSV export, single-session locking, and optional static dashboard
  hosting.
- `agent-grid-view/`: Vite/React operations console and UI workflow tests.
- `configs/demo.json`: synthetic heterogeneous demo scenario.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health`, `/ready` | Health, simulation boundary, model configuration status |
| GET | `/state`, `/nodes`, `/workloads` | Current state inspection |
| GET | `/policies` | Available policies and model configuration |
| POST | `/reset` | Seeded reset with named scenario controls |
| POST | `/step` | Apply placements and optional preemption/cancellation |
| POST | `/run` | Bounded run of a named policy (1–100 steps) |
| POST | `/benchmarks/run` | Paired benchmark (1–5 seeds, 1–4 policies) |
| GET | `/benchmarks/latest`, `/history` | In-process experiment retrieval |
| GET | `/exports/latest.csv` | CSV export of the latest API benchmark |

Malformed request schemas return HTTP 422. Structurally valid but infeasible
placements are reported with rejection reasons. The process is deliberately
single-session: a lock serializes mutations, but state and history are not
isolated per user and disappear when the process restarts.

## Scheduling and transition rules

Node GPU count, memory, per-node power, total facility power, availability, and
workload eligibility are checked against projected allocations before each
placement is applied. Workload progress is retained when a job is preempted or
requeued after a node failure. Completed work is never undone. A retry limit
eventually marks repeatedly failed jobs as failed. Arrivals are activated at
their configured submission tick. Power is sampled during the tick before
workload completion, so the final running tick is included in energy.

## Safety and explainability

Nemotron receives a compact state summary, not credentials or arbitrary user
content. The response must be JSON with exactly `assignments` and
`explanation`; the explanation is a model-generated rationale, not causal
proof. The model never executes a request directly: all proposals pass the
same local resource and power validation as deterministic policies. Missing
credentials, timeout, provider failure, malformed output, or rejected
assignments select the deterministic fallback and are visible in the decision
trace.

See [model integration](MODEL_INTEGRATION.md),
[benchmark methodology](BENCHMARK_METHODOLOGY.md), and
[limitations and safety](LIMITATIONS_SAFETY.md).
