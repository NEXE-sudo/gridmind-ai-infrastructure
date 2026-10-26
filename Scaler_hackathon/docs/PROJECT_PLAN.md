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
| P1 | Simulator, lifecycle, constraints, baseline schedulers, API | Complete in this PR | Seeded heterogeneous scenarios, power/memory limits, arrivals, failure/recovery, preemption/requeue, API tests; full Python suite. |
| P2 | Shared metrics, paired multi-seed experiments, export/report | Complete offline in this PR | CLI sample JSON/CSV/Markdown generated from actual code; definitions and pairing documented; failed/incomplete runs retained. |
| P3 | Nebius Token Factory and NVIDIA Nemotron | Implemented; external verification pending | Adapter, schema validation, bounded retry/timeout, fallback, mocked tests and smoke commands. Exact model ID and real inference require authorized credentials and a live smoke test. |
| P4 | GridMind API and operations dashboard | Implemented for local single session | Scenario controls, node/workload state, policies, run/step/reset, benchmark/history/export; frontend tests and build. |
| P5 | Reliability, security, CI, packaging | Local checks prepared; release validation pending | Unit/API/UI tests, CI workflow, lockfile, lint/build steps. CI has not run remotely yet; deployment and license remain blockers. |
| P6 | Hackathon/demo submission package | Prepared, not submission complete | Setup, architecture, methodology, model boundary, threat/limitations, actual sample report, video script and checklist. Public video, license, live model evidence, and any public URL remain outstanding. |

## PR #1 foundation already delivered

PR #1 introduced the isolated GridMind simulator/scheduler/API, initial
resource and power checks, guarded optional model proposals, lazy legacy
imports, and baseline tests. It was squash-merged as
`5ebc47ca8395c67aacd754bbb66a824c42081727`; the factual merge and post-merge
checks are recorded in `docs/PR_LOG.md`.

## Comprehensive PR scope

This PR strengthens workload transitions and scenario seeding; adds shared
metrics, deterministic policy execution, repeatable multi-seed experiments,
JSON/CSV/Markdown reporting, API experiment retrieval, scenario controls, and
the GridMind console; and adds integration tests, CI, sample outputs, setup
and submission documentation. It does not claim an actual Token Factory
request, public deployment, open-source license grant, or published video.

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
