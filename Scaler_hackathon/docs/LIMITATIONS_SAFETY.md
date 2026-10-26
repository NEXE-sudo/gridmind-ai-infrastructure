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
| Dashboard | Misleading live/model metrics | Simulation-only badge, explicit live-inference toggle, fallback trace, synthetic-energy labels, and separate benchmark statuses |

## Known constraints

- API state and experiment history are process-local, single-session, and not
  durable. Do not expose this API to multiple tenants or treat its lock as
  distributed coordination.
- Node-failure probabilities, recovery durations, GPU capacity, power
  coefficients, energy tariffs, and workloads are synthetic assumptions.
- There is no authentication, authorization, multi-tenant isolation, persistent
  storage, public deployment, or real infrastructure integration.
- CLI scenario paths are local process arguments; do not expose an
  unauthenticated arbitrary-path export endpoint.
- A live external model response can be nondeterministic and network-dependent.
  Offline runs are the reproducible comparison baseline.
- On 2026-10-26, the frontend dependency audit was reviewed and safe,
  non-major updates were applied; the remaining npm audit reported 12 issues
  across the full dependency graph (2 critical, 1 high, 9 moderate) and 5
  moderate findings with `npm audit --omit=dev`. They are inherited frontend
  toolchain/runtime dependencies; no forced major upgrade was applied. Re-run
  `npm audit` before release and review compatibility before upgrading Vite,
  Vitest, Tailwind, or React Router across major versions.
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
