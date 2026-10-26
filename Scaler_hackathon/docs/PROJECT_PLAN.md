# GridMind project plan and phase register

This is the delivery record. A phase is complete only when implementation,
tests, documentation, and supporting evidence agree. “Prepared” is not the
same as externally verified.

## Goal

GridMind evaluates data-centre workload scheduling across heterogeneous GPU
capacity, memory, deadlines, failures, synthetic power, and operating cost.
The original Scaler Energy Manager remains preserved as historical project
code and is not the GridMind runtime.

## Phase register

| Phase | Scope | Status | Evidence / exit criteria |
|---|---|---|---|
| P0 | Baseline, provenance, scope, working agreement | Complete in PR #1 | Separate GridMind entry point and legacy source preserved; baseline test result is in `docs/PR_LOG.md`. |
| P1 | Simulator, lifecycle, constraints, baseline schedulers, API | Implemented; lifecycle hardening in PR #4 | Explicit terminal structural infeasibility, recovery-before-scheduling, skip reasons, deadline semantics, and fixed-horizon execution status are regression-tested. |
| P2 | Shared metrics, paired multi-seed experiments, export/report | Implemented offline; benchmark validity hardened in PR #4 | Ten scenarios × five seeds × four policies; workload/run status separated, full and feasible denominators, matched failure traces, explicit unresolved reasons, deterministic CSV/Markdown, and descriptive intervals. |
| P3 | Nebius Token Factory and NVIDIA Nemotron | Implemented; external verification pending | Adapter, schema validation, bounded retry/timeout, fallback, mocked tests and smoke commands. Exact model ID and real inference require authorized credentials and a live smoke test. |
| P4 | GridMind API and operations dashboard | Implemented for local single session | Scenario controls, node/workload state, policies, run/step/reset, benchmark/history/export; frontend tests and build. |
| P5 | Reliability, security, CI, packaging | PR #4 local verification complete; GitHub checks pending | Python 3.11 tests (154 passed), changed-file Ruff, frontend tests/type diagnostics/build/lint, locked dependency audits, lockfile check, and deterministic scenario-suite smoke passed. ESLint reports 7 Fast Refresh warnings. The unused legacy-training extra was not installed or audited; deployment and license remain blockers. |
| P6 | Hackathon/demo submission package | Prepared, not submission complete | Setup, architecture, methodology, model boundary, threat/limitations, actual sample report, video script and checklist. Public video, license, live model evidence, and any public URL remain outstanding. |

## PR #1 foundation already delivered

PR #1 introduced the isolated GridMind simulator/scheduler/API, initial
resource and power checks, guarded optional model proposals, lazy legacy
imports, and baseline tests. It was squash-merged as
`5ebc47ca8395c67aacd754bbb66a824c42081727`; the factual merge and post-merge
checks are recorded in `docs/PR_LOG.md`.

## Comprehensive PR scope

This PR strengthens workload transitions and scenario seeding; adds shared
metrics, deterministic policy execution, a versioned ten-scenario catalogue,
paired multi-seed experiments, bounded bootstrap uncertainty, JSON/CSV/Markdown
reporting, API scenario and suite operations, dependency updates, and dashboard
scenario controls. It also adds regression coverage, CI smoke execution,
sample outputs, setup and submission documentation. It does not claim an
actual Token Factory request, public deployment, open-source license grant,
or published video.

## PR #4 benchmark-validity hardening

PR #4 starts from the verified `feat/gridmind-repurpose` base and carries the
unmerged PR #3 work plus the review fixes; PR #3 remains open and untouched.
The original fixed horizons and stress constraints are retained. A run marked
`completed` now means the simulator executed its complete declared horizon,
not that its workload queue drained. Structurally impossible work is
terminally reasoned; pending workloads retain actionable scheduling
diagnostics; completion, feasibility, deadline, failure, recovery, and
horizon-incomplete denominators are explicit. All paired policies run the
same complete horizon and are compared only when workload hashes and
exogenous failure-trace hashes match.

The before/after run-status counts and scenario-level workload outcomes are
in [`BENCHMARK_METHODOLOGY.md`](./BENCHMARK_METHODOLOGY.md) and
[`benchmarks/sample-suite/report.md`](../benchmarks/sample-suite/report.md).
All reported values are synthetic. Offline Nemotron remains deterministic
fallback, not evidence of live inference or AI superiority.

## Exit criteria for remaining work

1. **Live model verification:** authorized Token Factory key; exact NVIDIA ID
   returned by catalogue; catalogue check and real inference smoke both
   succeed; capture sanitized status, latency/usage if returned, and date.
2. **Public licensing:** repository owner confirms rights for project and
   inherited assets; add the selected compatible license and verify all
   third-party notices. Do not submit as openly licensed before this.
3. **Public demo:** record the actual app in <3 minutes, publish it, and test
   the public video URL.
4. **Deployment (optional if local demo is accepted):** deploy to an authorized
   service, verify health/readiness and live URL, then document service limits
   and secret handling. Do not invent a URL.
5. **Final release:** run CI on the final commit, confirm PR review/checks and
   merge status, reconcile phase register/PR log with the actual PR and commit,
   and re-check current Devpost rules and deadline.

## Guardrails

- The simulator is not a real cluster operator; estimates are synthetic.
- Model output is untrusted and cannot bypass deterministic validation.
- Missing credentials/provider failure must allow deterministic fallback.
- Compare policies on identical workload sets and seeds; retain failed runs.
- Do not claim a model call, cloud cost, result, license, merge, deployment, or
  video unless backed by actual evidence.
