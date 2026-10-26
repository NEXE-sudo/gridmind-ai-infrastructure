# GridMind project plan and phase register

This is the canonical delivery record. Update it in the same PR as phase changes.
Do not mark work complete until code, tests, documentation, and evidence agree.

## Goal

GridMind is a simulation-first AI infrastructure operator. It proposes GPU
workload placements under capacity, memory, deadline, and power constraints.
The environment validates every action and reports reproducible outcomes.
The original Scaler Energy Manager is retained as provenance while the new
domain is validated.

## Phases

| Phase | Scope | Status | Exit criteria |
|---|---|---|---|
| P0 | Baseline, provenance, scope, working agreement | In progress | Existing project preserved; process documented |
| P1 | Simulator, workload model, baseline schedulers, API, tests | In review | Targeted tests and API smoke test pass |
| P2 | Deadline/SLA accounting, node failures, scenario configuration | Planned | Scenario tests and reproducible seeds |
| P3 | Nebius Token Factory and NVIDIA Nemotron integration | Planned | Verified model ID, live call, latency/error evidence, fallback tested |
| P4 | Benchmark harness across FIFO, heuristic, and model policies | Planned | Raw results, multiple seeds, variance and exact commands |
| P5 | Dashboard conversion to GPU operations | Planned | UI uses new API and comparison results |
| P6 | Reliability, security, CI, dependency review | Planned | CI green; input and failure paths covered |
| P7 | Demo and submission package | Planned | Reproducible setup, demo, architecture, limitations |

## Guardrails

- This is a simulation, not a production GPU orchestrator.
- Power and energy are estimates, never hardware telemetry.
- Model output is an untrusted proposal; simulator validation is authoritative.
- Missing credentials or inference failure must allow deterministic fallback.
- Compare policies on identical workloads and seeds.
- Do not commit secrets, private traces, or machine-specific configuration.
- Every benchmark claim records command, seed set, commit, metrics, and raw output.

## Per-PR updates

For every PR, record its link, phase, changed components, tests actually run,
observed results, remaining risks, and next step. Never claim a test passed if
the command was not run and the output inspected.
