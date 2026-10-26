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
| P5 | Reliability, security, CI, packaging | PR #4 local verification and GitHub CI passed | Python 3.11 tests (154 passed), changed-file Ruff, frontend tests/type diagnostics/build/lint, locked dependency audits, lockfile check, deterministic scenario-suite smoke, and PR #4 Python/dashboard CI jobs passed. ESLint reports 7 Fast Refresh warnings. The unused legacy-training extra was not installed or audited; deployment and license remain blockers. |
| P6 | Hackathon/demo submission package | Prepared, not submission complete | Setup, architecture, methodology, model boundary, threat/limitations, actual sample report, video script and checklist. Public video, license, live model evidence, and any public URL remain outstanding. |
| P7 | Decision-trace explainability and demo workflow | Implemented in PR #5; GitHub CI passed | Deterministic candidate evidence is emitted during scheduling, model-proposed nodes are separated from deterministic ranking, the API retains the latest 20 steps per run, and the console restores/displays traces. Full local test/build/audit checks and PR #5 Python/dashboard jobs passed; five-seed benchmark CSV/Markdown and substantive JSON match the merged artifact exactly. |

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

PR #4 started from the verified `feat/gridmind-repurpose` base and carried
the PR #3 work plus the review fixes. PR #3 was squash-merged as
`f96feea5203cfff41e04a92eecb64200d60186c8`; PR #4 was squash-merged as
`661ee8dc0080c20cbe4f586c773724478258d727`.
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

## PR #5 decision-trace milestone (selected before implementation)

The post-merge code and sample report show that the simulator, workload
lifecycle, scenario pairing, fixed-horizon metrics, and skip diagnostics
already have regression coverage. The highest-value remaining demo gap is
that successful deterministic placements expose only a generic policy
rationale and workload-to-node mapping: the scheduler does not emit its
feasible candidate set or the best-fit comparison that selected a node.
Although the dashboard has a “Decision Trace” panel, it cannot currently
explain an accepted placement, and its decisions disappear on page reload.
Offline Nemotron matches the deterministic resource-aware policy in the
sample; without live-model evidence, an AI-performance claim is not an
appropriate next milestone.

Selected scope: make the existing scheduler decisions inspectable from
decision calculation through API response/history and the dashboard. For
each deterministic assignment, record the actually evaluated feasible node
candidates, post-placement GPU fill, incremental estimated power, the
selection rule, and the selected node. Existing skip diagnostics remain the
source of blocker reasons. For Nemotron proposals, record only that the
proposed assignment passed deterministic simulator validation; do not
fabricate a scheduler ranking or causal model explanation. Retain only a
bounded recent decision trace in process-local run history and restore it on
console load.

Acceptance criteria:

1. Candidate details come from the exact reservation and power checks used
   to choose the node; node-model, GPU, memory, node/facility power, and
   reservation constraints remain unchanged.
2. Every executed scheduler placement maps to one trace record; selected
   candidates are feasible and deterministic tie-breaking is explicit.
3. Valid model proposals are labeled as model-proposed and simulator-
   validated, with no claimed deterministic ranking. Rejected proposals and
   fallback decisions remain distinguishable.
4. API responses and bounded run history carry the trace; the dashboard
   displays candidate comparison, selection, and skips, and reload restores
   the most recent simulation trace.
5. Focused unit/API/UI tests pass; full Python and frontend checks pass;
   fixed benchmark outcomes and substantive artifacts remain unchanged.

Implementation outcome: focused scheduler/API/dashboard regression tests,
the full Python suite, frontend tests, type-check, production build, Ruff,
dependency audits, and lockfile consistency passed locally. The generated
five-seed suite retained byte-identical CSV and Markdown, and its substantive
JSON matched the committed artifact after excluding `created_at`. GitHub CI
and the final PR/merge state are recorded in the PR log when available.

Key risk: explanations can overstate what a scheduler considered. The trace
must be emitted during the same candidate evaluation that makes the placement,
not reconstructed afterward. All hardware, power, cost, and workload values
remain synthetic; this milestone does not change the offline Nemotron model
boundary or claim operational deployment.

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
