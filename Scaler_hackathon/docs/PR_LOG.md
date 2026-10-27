# Pull request and engineering decision log

Update this file in every PR. Keep entries factual and evidence-based.

## PR register

| PR | Phase | Scope | Status / evidence |
|---|---|---|---|
| [#1](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/1) | P0–P1 | Plan, workflow, simulator, schedulers, guarded Nemotron proposal path, API, tests | Squash-merged 2026-10-26 as `5ebc47ca8395c67aacd754bbb66a824c42081727`; post-merge verification passed |
| [#2](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/2) | P2–P7 | Complete GridMind simulation, metrics, paired-seed benchmark, dashboard, API, docs, and CI | Squash-merged 2026-10-26 as `966cfc6ae22cff284264f988e78b72ad2ac555f1`; post-merge CI and local verification passed |
| [#3](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/3) | P2–P5 | Ten-scenario paired benchmark suite, simulator/API safeguards, dashboard scenario controls, audits, and submission docs | Squash-merged 2026-10-26 as `f96feea5203cfff41e04a92eecb64200d60186c8`; checks passed before merge. |
| [#4](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/4) | P2–P5 | Fixed-horizon workload accounting, scheduling diagnostics, paired evaluation, reproducible evidence | Squash-merged 2026-10-26 as `661ee8dc0080c20cbe4f586c773724478258d727`; target-branch CI passed after merge. |
| [#5](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/5) | P7 | Scheduler-grounded placement evidence, bounded API decision history, and dashboard trace walkthrough | Squash-merged 2026-10-27 as `b1f9e35d5caeb6c212775ef263919dd95ce161f2`; PR Python/dashboard checks passed. |
| [#6](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/6) | P3, P5 | Opt-in Nemotron verification, bounded inference telemetry, safe fallback status, and fair live-evaluation safeguards | Squash-merged 2026-10-27 as `54ee42207e2fb26a9273038a188c3834c0338c83`; post-merge CI passed. No live provider request was made. |

## Entry template

### PR # — Title
- Phase(s):
- Problem solved:
- Behaviour delivered:
- Key files/components:
- Tests run and exact result:
- Manual verification:
- Risks/limitations:
- Follow-up phase:
- Merged commit:

### PR #2 — Complete simulation and evaluation platform
- Phase(s): P2–P8.
- Problem solved: finish the GridMind conversion as a reproducible data-centre
  operations simulation and demonstrable policy-evaluation product while
  preserving the legacy energy-grid project.
- Behaviour delivered: heterogeneous GPU nodes and workload lifecycle;
  deterministic FIFO, priority, resource-aware, and guarded optional Nemotron
  scheduling; shared operational metrics; paired seeded experiments and
  machine-readable exports; FastAPI operations endpoints; React console;
  CI, setup and submission documentation.
- Key files/components: `server/datacenter_simulator.py`,
  `server/workload_scheduler.py`, `server/metrics.py`, `server/decision.py`,
  `server/nemotron.py`, `server/benchmarks.py`, `server/gridmind_app.py`,
  `agent-grid-view/src/pages/GridMindConsole.tsx`, `.github/workflows/ci.yml`,
  and `docs/`.
- Tests run and exact result: pre-change baseline — 110 Python tests passed;
  final Python suite — 133 passed; benchmark regression tests after CSV
  newline fix — 6 passed; Ruff on changed benchmark/test files — passed.
  Frontend tests — 3 passed; TypeScript diagnostics — passed; production build
  — passed; ESLint — 0 errors and 7 Fast Refresh warnings. Three-seed sample
  benchmark — 12/12 policy runs completed; sample Nemotron rows used offline
  deterministic fallback. `git diff --cached --check` — passed.
- Manual verification: browser workflow verified the local console, scenario
  reset and step; API health/readiness/reset/run smoke checks succeeded.
- Risks/limitations: live Token Factory inference was not verified because
  `NEBIUS_API_KEY` and a verified account-accessible NVIDIA model ID were
  unavailable. Docker daemon was unavailable. No public demo/video was
  published. No root licence was added because rights/compatibility were not
  confirmed. No public deployment is claimed. npm audit reported 12
  full-graph advisories (2 critical, 1 high, 9 moderate) and 5 moderate
  production-only advisories after safe non-major updates. GridMind remains a
  synthetic, single-session simulation; it does not control real systems.
- Follow-up phase: configure and smoke-test a verified Nebius model; confirm
  licensing rights; build and run the container; publish the demo video and,
  if credentials/infrastructure permit, deploy the public demo. Then resolve
  or explicitly accept remaining dependency advisories.
- Merged commit: PR #2 squash-merged 2026-10-26 into `feat/gridmind-repurpose`
  as `966cfc6ae22cff284264f988e78b72ad2ac555f1`. GitHub Actions on the merged
  commit passed the complete Python test/lint and dashboard test/lint/type
  check/build jobs. Local CI-equivalent Python tests — 133 passed; targeted
  GridMind tests — 41 passed; dashboard tests — 3 passed; TypeScript checks
  and production build — passed; ESLint — 0 errors and 7 Fast Refresh warnings.

### PR #3 — Add multi-scenario GridMind benchmarks
- Phase(s): P2–P5.
- Problem solved: broaden the single-scenario evaluation into reproducible,
  statistically paired multi-scenario experiments with explicit accounting
  for incomplete runs, while improving simulator and API safeguards.
- Behaviour delivered: ten versioned synthetic scenarios; workload and
  exogenous failure pairing by seed; GPU-model compatibility; expanded
  recovery, preemption, starvation, and infeasibility metrics; paired
  bootstrap summaries; bounded suite API and CLI operations; scenario-aware
  dashboard controls; dependency upgrades and audit gates.
- Key files/components: `configs/scenarios.json`, `server/scenarios.py`,
  `server/benchmarks.py`, `server/datacenter_simulator.py`,
  `server/metrics.py`, `server/gridmind_app.py`, dashboard scenario controls,
  and `.github/workflows/ci.yml`.
- Tests run and exact result: Python suite — 144 passed; changed-file Ruff —
  passed; dashboard tests — 3 passed; TypeScript check and production build —
  passed; ESLint — 0 errors and 7 Fast Refresh warnings; `uv lock --check` —
  passed. Full and production `npm audit` — 0 findings. Python 3.11 runtime
  plus legacy test-extra `pip-audit` — 0 findings. The separate optional
  `legacy-training` extra has 69 findings across `datasets`, `torch`, and
  `transformers` and is excluded from the GridMind runtime/CI. GitHub Actions
  Python and dashboard jobs passed on PR head `8796514`; this documentation
  update will trigger a final PR check run.
- Benchmark evidence: checked-in five-seed suite — 200 runs across 10
  scenarios and 4 policies; 64 completed, 136 horizon-incomplete, 0 failed.
  Repeated CSV and Markdown outputs were byte-identical. Results are
  synthetic; offline Nemotron uses fallback and is not evidence of live
  model inference or an AI performance gain.
- Manual verification: no live Token Factory call, public deployment,
  license grant, or demo video is claimed. Python 3.10's optional legacy
  extra resolves a Pillow release with known advisories because the patched
  release requires Python 3.11+.
- Follow-up phase: obtain authorized credentials and a verified model ID for
  live inference; confirm rights for a public license; publish the
  under-three-minute demo; decide whether to upgrade or retire the historical
  training extra.
- PR status: opened as #3 from `feat/gridmind-scenario-lab-benchmarks` to
  `feat/gridmind-repurpose`, initially at commit `7848f77`; squash-merged
  2026-10-26 as `f96feea5203cfff41e04a92eecb64200d60186c8`. Python and
  dashboard checks passed before merge.

### PR #4 — Harden benchmark validity and stress diagnostics
- Phase(s): P2–P5.
- Problem solved: the prior benchmark labeled normal fixed-horizon executions
  with unresolved jobs as run-level `incomplete`, left structurally
  impossible requests pending, and counted explained contention as
  starvation. This also discarded valid paired stress-scenario observations.
- Behaviour delivered: `completed` now means a successful full-horizon
  execution, independent of workload outcomes. Permanently infeasible jobs
  become terminal with a reason; scheduling records actionable placement
  blockers; recovery and arrivals precede decisions; deadline-missed jobs
  remain eligible; requeues preserve remaining work; starvation excludes
  explained waits. Workload denominators and mutually exclusive unresolved
  outcome classifications are explicit. Every policy runs the same fixed
  horizon and is paired only on matching workload and exogenous failure
  trace hashes.
- Benchmark evidence: the baseline five-seed suite regenerated its committed
  CSV and Markdown byte-for-byte; substantive JSON records matched after
  excluding intentional timestamps. Baseline run statuses were 64 completed,
  136 incomplete, and 0 failed. The new 200-run primary suite has 200
  completed fixed-horizon executions and 0 failed executions. Across its
  2,720 workload instances: 2,262 completed, 38 operationally failed, 0
  cancelled, 220 permanently infeasible, and 200 unresolved at the horizon.
  Every scenario-policy comparison has five matched seed samples. The
  separate uniformly doubled-horizon diagnostic is not mixed into the
  primary results; some contention tails drain, while combined stress
  remains partly unresolved and failure scenarios incur retry-exhaustion
  outcomes. Nemotron uses deterministic offline fallback; no live inference
  or AI superiority is claimed.
- Tests run and exact result (commands run from `Scaler_hackathon/`, unless
  noted; every command exited 0):
  `UV_PROJECT_ENVIRONMENT=/tmp/gridmind-pr4-py311 uv run --locked --python
  3.11 --extra dev --extra legacy python -m pytest -q` — 154 passed;
  `UV_PROJECT_ENVIRONMENT=/tmp/gridmind-pr4-py311 uv run --locked --python
  3.11 --extra dev --extra legacy ruff check server/datacenter_simulator.py
  server/workload_scheduler.py server/metrics.py server/nemotron.py
  server/decision.py server/benchmarks.py server/gridmind_app.py
  server/scenarios.py tests/test_gridmind_simulator.py tests/test_gridmind_api.py
  tests/test_gridmind_metrics.py tests/test_gridmind_benchmarks.py
  tests/test_nemotron.py scripts/smoke_test_nemotron.py` — passed;
  `uv lock --check` — passed;
  `uv export --locked --format requirements-txt --no-dev --no-emit-project
  --extra legacy -o /tmp/gridmind-pr4-requirements.txt && uvx --python 3.11
  --from pip-audit pip-audit -r /tmp/gridmind-pr4-requirements.txt` — no
  known vulnerabilities;
  `UV_PROJECT_ENVIRONMENT=/tmp/gridmind-pr4-py311 uv run --locked --python
  3.11 --extra dev --extra legacy python -m server.benchmarks --suite
  configs/scenarios.json --seeds 1 --output-dir /tmp/gridmind-pr4-ci-smoke`
  — 40/40 policy runs completed. From
  `Scaler_hackathon/agent-grid-view/`: `npm test -- --run` — 3 passed;
  `npx tsc -b --pretty false` — passed; `npm run build` — passed;
  `npm run lint` — 0 errors and 7 Fast Refresh warnings;
  `npm audit --audit-level=low` — 0 vulnerabilities. Full five-seed suite
  CSV and Markdown were byte-identical across two generations; substantive
  JSON matched after excluding `created_at`.
- Risks/limitations: synthetic workloads, topology, power, failures, and
  pricing; offline Nemotron fallback only; no live Token Factory call,
  production cluster integration, public deployment, confirmed root license,
  or published demo video. The 2x continuation is diagnostic evidence, not a
  production drain guarantee. Seven existing ESLint Fast Refresh warnings
  remain. `legacy-training` was not installed or audited.
- PR status: opened as [#4](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/4)
  from `feat/gridmind-benchmark-validity` to `feat/gridmind-repurpose`.
- GitHub Actions: Python and dashboard jobs passed on the final PR branch
  head after syncing PR #3 and resolving the duplicate helper in
  `metrics.py`; the target-branch CI run
  [40373531371](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40373531371)
  passed on merge commit `661ee8dc0080c20cbe4f586c773724478258d727`.
- Merge verification: GitHub confirms PR #4 was squash-merged on 2026-10-26
  as `661ee8dc0080c20cbe4f586c773724478258d727`.

### PR #5 — Explain scheduler placement decisions
- Phase(s): P7.
- Problem solved: successful deterministic placements exposed only a generic
  policy rationale and workload-to-node mapping. The scheduler's feasible
  alternatives and the measured selection that led to a node were absent
  from the API and dashboard trace.
- Behaviour delivered: deterministic assignment records are emitted directly
  by the scheduler's candidate evaluation and include queue rank, priority,
  deadline, feasible node candidates, projected GPU fill, resource availability,
  incremental power, projected node/facility power, selected node, and the
  exact max-fill/tie-break rule. Nemotron assignments are labeled as model
  proposals accepted by simulator validation; no deterministic ranking is
  claimed for them. API run history retains a bounded 20-step trace and the
  dashboard restores and renders the latest decisions and candidate evidence.
- Benchmark evidence: policy actions and fixed benchmark horizons are
  unchanged. The primary suite is compared with the checked-in 200-run
  artifact to verify unchanged substantive results; results remain synthetic
  and offline Nemotron remains deterministic fallback.
- Tests run and exact result: full Python 3.11 suite — 157 passed; changed
  Python Ruff — passed; `uv lock --check` — passed; one-seed suite smoke —
  40/40 runs completed; dashboard tests — 4 passed; TypeScript diagnostics
  and production build — passed; ESLint — 0 errors and 7 Fast Refresh
  warnings; npm audit — 0 vulnerabilities; Python 3.11 runtime `pip-audit`
  — no known vulnerabilities. The five-seed, 200-run suite was regenerated:
  CSV and Markdown were byte-identical to committed artifacts
  (CSV SHA-256 `a0402eacb2d35403bedde9c17bb81397ce16b7f2c919aa368bfe86962a50b0347`;
  Markdown SHA-256 `39b0d64aae8fc607b7f12ad3a43c0baa5357d35c66b286a20c14ac21ceeb7adb`);
  substantive JSON matched after excluding only `created_at`.
- Risks/limitations: resource, power, and performance inputs are synthetic.
  Candidate projections describe simulator bookkeeping and do not predict
  real infrastructure. Decision history is bounded and process-local.
- PR status: opened on `feat/gridmind-decision-traces` targeting
  `feat/gridmind-repurpose`; squash-merged 2026-10-27 as
  `b1f9e35d5caeb6c212775ef263919dd95ce161f2`. GitHub Actions Python and
  dashboard checks passed on PR head `e01d4ccdbae7f19caa2bd69bb808dc741e36d044`
  in run `40375464158`.
- GitHub Actions: Python and dashboard jobs passed on PR head
  `7bb9fcb64a3b1ade356bc43c0a29f09351f258ee` in run
  [40375261470](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40375261470).

### PR #6 — Verify optional Nemotron inference and make evaluation auditable
- Phase(s): P3 and P5.
- Starting point: fetched `origin/feat/gridmind-repurpose` at
  `661ee8dc0080c20cbe4f586c773724478258d727`. PR #5 was independently open
  during initial implementation and later merged into the base; its changes
  were then integrated into this branch and validated together.
- Existing integration discovered: the base used the OpenAI-compatible
  Token Factory endpoint, `NEBIUS_API_KEY`, and `GRIDMIND_MODEL`, with a JSON
  chat-completion proposal and deterministic simulator validation/fallback.
  The live API path did not require successful catalogue verification and a
  validated one-request preflight; SDK retries were enabled and provider
  attempt/response/fallback telemetry was not fully distinguished. Existing
  provider tests used mocks. No genuine catalogue or inference request had
  been made.
- Behaviour delivered: explicit `--live` smoke-test consent; bounded,
  sanitized catalogue and inference verification; exact-model and simulator
  proposal preflight before live run/benchmark; disabled SDK retries with at
  most one explicit timeout/rate-limit retry under one deadline; strict
  duplicate-key/schema handling; explicit persisted verification states;
  separate attempts, retries, responses, invalid outputs, fallbacks, latency,
  and returned usage; fail-closed deterministic fallback; dashboard status and
  live-control gating; offline experiment provenance and methodology updates.
- Offline validation after integrating PR #5: Python 3.11 full suite — 189
  passed; focused API and placement-trace tests — 44 passed; CI Ruff file set
  and `uv lock --check` — passed; deterministic scenario smoke — 40/40 runs
  across ten scenarios and four policies, with ten Nemotron rows using
  deterministic fallback. Dashboard — 5 tests passed; TypeScript diagnostics
  and production build passed; ESLint — 0 errors and 7 Fast Refresh warnings;
  `npm audit --audit-level=low` — 0 vulnerabilities; `git diff --check` —
  passed. The separate Python runtime-plus-legacy-extra audit reported no
  known vulnerabilities before PR #5 integration. The PR #6 authored baseline
  produced byte-identical CSV and Markdown on repeated generation.
- Live verification: **blocked / unverified**. `NEBIUS_API_KEY`,
  `GRIDMIND_MODEL`, and `NEBIUS_BASE_URL` were unset. The explicitly opted-in
  smoke command refused before making a request. No exact model ID, live
  catalogue response, real inference, or live benchmark is claimed. Official
  Token Factory docs were checked on 2026-10-26, but this is not live
  availability evidence.
- Interpretation and limitations: the offline suite is a reproducibility
  check, not a live model comparison or performance claim. Workloads, power,
  energy, and costs are synthetic. Live sample counts are zero; no model
  superiority conclusion is available. `legacy-training` was not installed
  or audited.
- PR status: submitted as
  [#6](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/6),
  targeting `feat/gridmind-repurpose`.
- GitHub Actions: Python and dashboard checks passed on original PR head
  `01943c95c24440e905eba1366ce873b04d1884a6` in run
  `40381027722`, and on the combined PR #5/#6 head
  `c05e500fee2fc78d44873edc2733fed1dd032439` in run `40445105052`.
- Merge and post-merge verification: GitHub confirms PR #6 was squash-merged
  into `feat/gridmind-repurpose` on 2026-10-27 as
  `54ee42207e2fb26a9273038a188c3834c0338c83`. Target-branch CI run
  [40445320854](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40445320854)
  completed successfully. No real catalogue or inference request was made.

### PR #7 — Prepare judge-ready offline demo and submission audit
- Phase(s): P6 and P8.
- Starting point: `feat/gridmind-repurpose` at
  `54ee42207e2fb26a9273038a188c3834c0338c83`; no base changes were present
  when the feature branch was created.
- Problem solved: the repository had no single, focused walkthrough whose
  raw evidence, decision explanations, and reproducibility could be inspected
  independently of the ten-scenario benchmark suite. First-run instructions,
  asset provenance, and the final-entry requirements also needed a
  source-backed review.
- Behaviour delivered: `server.judge_demo` runs the fixed-horizon
  `node_failure_recovery` scenario at seed 7 through FIFO, resource-aware,
  and offline Nemotron fallback. It generates a versioned manifest, raw JSON
  with retained placement/defer traces, and a report with workload outcomes
  and explicit metric denominators. `--check` reruns the experiment and
  excludes only documented creation timestamps. README setup and demo
  commands, a timed walkthrough, source/asset/dependency provenance audit,
  and an official-rules checklist are added. No license, public deployment,
  video, submission, or live inference is claimed.
- Benchmark evidence: all three policies reach the 90-step horizon on the
  same workload and failure-trace hashes. For this single seed, FIFO and
  resource-aware each complete 9/12 workloads; offline Nemotron fallback
  matches resource-aware. It made 0 provider invocations and used 78
  deterministic fallbacks. These synthetic `n=1` outcomes are descriptive,
  not a performance or statistical superiority claim. A fresh five-seed,
  ten-scenario suite run executed 200 policy runs. Its Markdown report is
  byte-identical to the checked-in report; run states, workload/event/failure
  traces, and non-AI metrics also match. The existing CSV/JSON were generated
  before PR #6 and therefore lack five inference telemetry columns; this
  schema-only difference is recorded rather than presented as exact raw-file
  reproducibility.
- Tests and audits: CI-style full Python suite — 192 passed; focused API/demo
  tests — 24 passed; changed-file Ruff and `uv lock --check` — passed; focused
  demo generation and `--check` — passed; repeated 40-run suite smoke
  artifacts — deterministic apart from documented creation timestamps;
  dashboard — 5 tests passed; TypeScript diagnostics and production build —
  passed; ESLint — 0 errors and 7 Fast Refresh warnings; Python runtime plus
  legacy-extra `pip-audit` — no known vulnerabilities; `npm audit
  --audit-level=low` — 0 vulnerabilities; Markdown relative-link check — 12
  files checked, 0 broken links; `git diff --check` — passed. The optional
  `legacy-training` extra was not audited.
- Clean-checkout verification: locked `uv sync`, focused demo `--check`,
  `npm ci` (using an isolated temporary npm cache after a shared-cache
  permission collision), five dashboard tests, TypeScript diagnostics, and
  production build all passed. GitHub Actions Python and dashboard jobs passed
  on PR head `08440adff65f27f14bf7dcfa49bf7fb4189cdd08` in run
  [40464564169](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40464564169).
- Provenance and submission: GitHub reported no repository license; inherited
  contributor, adapter/checkpoint, plot, and unused public asset rights remain
  unclear and require owner/legal review. The official Devpost rules were
  checked 2026-10-27; the deadline is 2026-10-30 10:00 a.m. Pacific
  (17:00 UTC / 22:30 IST). Live Token Factory inference, Nebius execution,
  judge-accessible hosting, a public under-three-minute video, rights and
  eligibility confirmation, and account-specific submission remain blocked
  or operator actions.
- PR status: opened as
  [#7](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/7),
  targeting `feat/gridmind-repurpose`; it remains open and unmerged.
  GitHub Python and dashboard CI passed; review is pending.

## Decisions

### PR #1 reliability pass — 2026-10-26

- Root cause: importing `server.gridmind_app` first executed
  `server/__init__.py`, which eagerly imported the existing OpenEnv-backed
  energy-grid environment. GridMind itself was not the missing module; the
  import failed before Python could load it in an environment where OpenEnv
  was not installed. The original repository checkout also did not contain the
  PR's GridMind files.
- Changed: made legacy package exports lazy; enforced simulator node and
  facility power limits; validate every proposed placement against projected
  resources before application; retain running-job progress across preemption
  and transient failures; report failure/requeue events; account energy for the
  full simulated tick, including completion ticks; strictly validate API
  request fields and types; report and apply deterministic fallback for
  unavailable, malformed, or invalid Nemotron proposals.
- Tests on clean Python 3.11 virtual environment: targeted
  `tests/test_gridmind_simulator.py` — 13 passed; full `pytest -q` — 110 passed;
  FastAPI API tests are included in the full run. Import command succeeded and
  TestClient smoke returned 200 for `/health`, `/state`, `/policies`; malformed
  `/run` policy returned 422. FastAPI lifespan startup/shutdown check passed.
- Ruff: all changed implementation and test files pass. Whole-project Ruff
  reports 587 findings versus 591 on the base branch (four fewer); remaining
  findings are inherited in untouched legacy files.
- Remaining limitations: no real Nebius request was made; no credentials or
  model catalogue verification were available. No public deployment/video is
  part of this PR.
- Merge and post-merge verification: GitHub confirmed PR #1 merged at
  `2026-10-26T14:03:41Z` by squash as
  `5ebc47ca8395c67aacd754bbb66a824c42081727`. On the synchronized
  `feat/gridmind-repurpose` base, targeted simulator tests — 13 passed; full
  pytest suite — 110 passed; changed-file Ruff — passed; documented import —
  passed; TestClient `/health`, `/state`, `/policies`, `/reset`, `/step`, and
  `/run` — HTTP 200; invalid policy — HTTP 422; `uv lock --check` — passed.
  Base worktree was clean and matched `origin/feat/gridmind-repurpose`.
  Feature branch was deleted locally after its tree matched the merged base;
  GitHub had deleted the remote branch as part of the merge.

### Isolated migration
GridMind gets a separate simulator and API entry point before energy-specific
modules are replaced. This preserves provenance and makes the new domain testable.

### Model proposals are untrusted
Nemotron cannot bypass resource or power checks. If credentials are missing or
inference fails, the deterministic scheduler is used instead.

### Simulation assumptions are visible
Power coefficients and one-minute ticks are synthetic. They are appropriate for
controlled comparisons, not claims about actual GPU power or energy.
