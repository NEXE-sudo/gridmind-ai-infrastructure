# Limitations, safety, and threat model

## Intended use

GridMind is a local simulation and scheduling-policy evaluation sandbox. It
does not control physical GPUs, Kubernetes, cloud accounts, cluster schedulers,
facility power, or safety systems. Synthetic power/energy values must never be
presented as telemetry or a real cloud invoice.

## Trust boundaries and mitigations

| Input / boundary | Risk | Current mitigation |
|---|---|---|
| HTTP request | Invalid schema, oversized runs, accidental mutation | Strict request fields/types; run bound of 100 steps; benchmark bound of 5 seeds and 4 policies; serialized state mutation |
| Model response | Hallucinated IDs, malformed schema, infeasible placement | Exact JSON keys/type checks, bounded output, simulator-side resource and power validation, deterministic fallback |
| Provider error | Timeouts, rate limits, unavailable service | Explicit timeout, one bounded retry, non-secret error category, deterministic fallback |
| API key | Leakage in logs, frontend, or results | Server environment only, no `VITE_*` key, log sanitized error class, no prompt/header/key persistence |
| Export route | Arbitrary filesystem path traversal | API exports only the in-memory latest benchmark to a fixed CSV response; CLI output directory is an operator-selected local path |
| Concurrent requests | Conflicting mutation of shared simulator | Process-local lock; documented single-process/single-session limitation |
| Dashboard | Misleading live/model metrics or hiding unfinished work | Simulation-only badge, explicit live-inference toggle, fallback trace, scheduler-emitted placement candidates and skip reasons, estimated-energy labels, full workload denominators, unresolved/infeasible counts, and execution status separated from workload outcomes |

## Known constraints

- API state and experiment history are process-local, single-session, and not
  durable. Do not expose this API to multiple tenants or treat its lock as
  distributed coordination.
- Node-failure probabilities, recovery durations, GPU capacity, power
  coefficients, energy tariffs, and workloads are synthetic assumptions.
- The benchmark's fixed horizon is an evaluation budget, not a guarantee that
  every workload will complete. `completed` run status means only that the
  simulation reached its horizon without an exception. Infeasible, failed,
  deadline-missed, and horizon-unresolved workloads remain visible in the
  denominators and JSON/CSV evidence.
- Structural infeasibility is distinguished from temporary GPU/memory
  contention, power reservations, node recovery, missed deadlines, and
  unexplained scheduler deferral. The 30-minute starvation metric excludes
  jobs with a recorded resource or policy reason. See
  [`BENCHMARK_METHODOLOGY.md`](./BENCHMARK_METHODOLOGY.md) for precedence and
  the reproduced scenario diagnoses.
- The primary horizons are not enlarged to improve a policy's scores. A
  separate 2x-horizon diagnostic continuation showed that some resource-
  contention tails drain with more time, while combined failure stress can
  remain unresolved and repeated failures can exhaust retries. That
  diagnostic is not mixed into primary benchmark results and does not prove
  that an operational scheduler would recover similarly.
- There is no authentication, authorization, multi-tenant isolation, persistent
  storage, public deployment, or real infrastructure integration.
- CLI scenario paths are local process arguments; do not expose an
  unauthenticated arbitrary-path export endpoint.
- A live external model response can be nondeterministic and network-dependent.
  Offline runs are the reproducible comparison baseline.
- Deterministic placement evidence describes the simulator's candidate
  feasibility checks and best-fit rule, not measured cluster telemetry.
  Nemotron placement traces report simulator validation only; model-generated
  free-text rationales are not verified causal explanations. Decision history
  is process-local and bounded to the last 20 decision steps per recent run.
- The frontend dependency graph was updated and verified with both full and
  production-only `npm audit`; each reported zero known vulnerabilities.
- The optional `legacy` OpenEnv test extra uses Pillow 13 on Python 3.11+.
  Pillow 13 does not support Python 3.10, where the upstream Gradio dependency
  resolves Pillow 12.3.0; the current advisory database reports 37 findings
  for that version. This does not affect the default GridMind runtime. Avoid
  installing the legacy extra on Python 3.10 or exposing its historical UI.
- The separate `legacy-training` extra preserves historical pinned ML
  dependencies and is not used by GridMind or CI. On Python 3.11,
  `pip-audit` reported 69 findings across `datasets==2.14.4` (1),
  `torch==2.2.2` (23), and `transformers==4.36.2` (45). Do not install it
  for the GridMind runtime; update and validate the historical training stack
  before using it.
- No verified live model request or deployment is claimed for this PR.
- No root open-source license was present in the inspected base. A license
  requires repository-owner confirmation of rights and compatibility with
  inherited code/assets; this work does not create or imply a license grant.

## Before production or public deployment

Do not connect this prototype to a real scheduler. First add authenticated
multi-user sessions, authorization, durable state, tenant isolation, structured
observability, deployment-specific secret management, rate limiting, stronger
model/provider contract tests, reviewed dependency upgrades, and an explicit
human approval boundary. Independently validate simulated power and SLA
assumptions against authorized real telemetry before making operational claims.
