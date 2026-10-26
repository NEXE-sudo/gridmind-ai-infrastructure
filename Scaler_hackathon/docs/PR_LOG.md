# Pull request and engineering decision log

Update this file in every PR. Keep entries factual and evidence-based.

## PR register

| PR | Phase | Scope | Status / evidence |
|---|---|---|---|
| [#1](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/1) | P0–P1 | Plan, workflow, simulator, schedulers, guarded Nemotron proposal path, API, tests | Squash-merged 2026-10-26 as `5ebc47ca8395c67aacd754bbb66a824c42081727`; post-merge verification passed |
| [#2](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/2) | P2–P7 | Complete GridMind simulation, metrics, paired-seed benchmark, dashboard, API, docs, and CI | Squash-merged 2026-10-26 as `966cfc6ae22cff284264f988e78b72ad2ac555f1`; post-merge CI and local verification passed |
| [#3](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/3) | P2–P5 | Ten-scenario paired benchmark suite, simulator/API safeguards, dashboard scenario controls, audits, and submission docs | Squash-merged 2026-10-26 as `f96feea5203cfff41e04a92eecb64200d60186c8`. |
| [#4](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/4) | P2–P5 | Fixed-horizon workload accounting, scheduling diagnostics, paired evaluation, reproducible evidence | Squash-merged 2026-10-26 as `661ee8dc0080c20cbe4f586c773724478258d727`; base-branch CI passed in run `40373531371`. |
| [#5](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/5) | P3 | Decision traces | Open and unmerged; its implementation is not included in the PR #6 base or changes. |
| [#6](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/6) | P3, P5 | Opt-in Nemotron verification, bounded inference telemetry, safe fallback status, and fair live-evaluation safeguards | Open for review from `feat/gridmind-live-nemotron-evaluation` to `feat/gridmind-repurpose`; no live provider request was made. |

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
  2026-10-26 as `f96feea5203cfff41e04a92eecb64200d60186c8`.

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
  from `feat/gridmind-benchmark-validity` to `feat/gridmind-repurpose`;
  squash-merged 2026-10-26 as
  `661ee8dc0080c20cbe4f586c773724478258d727`. PR #3 had merged before PR #4.
- GitHub Actions: Python and dashboard jobs passed on PR head
  `7ce108d95892e8bcd599ec90788cde06d96df6b7` in run
  [40371767347](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40371767347).

### PR #6 — Verify optional Nemotron inference and make evaluation auditable
- Phase(s): P3 and P5.
- Starting point: fetched `origin/feat/gridmind-repurpose` at
  `661ee8dc0080c20cbe4f586c773724478258d727`; PR #5 remained open at
  `e01d4ccdbae7f19caa2bd69bb808dc741e36d044` and was not included.
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
- Offline validation: Python 3.11 `uv run --locked --python 3.11 --extra dev
  --extra legacy python -m pytest -q` — 186 passed; CI Ruff file set — passed;
  `uv lock --check` — passed; deterministic scenario smoke — 40/40 runs across
  ten scenarios and four policies; ten Nemotron rows used deterministic
  fallback. A repeated run generated byte-identical CSV and Markdown.
  Dashboard — 4 tests passed; `npx tsc -b --pretty false` and production build
  passed; ESLint — 0 errors and 7 Fast Refresh warnings. `pip-audit` on locked
  runtime plus legacy test dependencies — no known vulnerabilities;
  `npm audit --audit-level=low` — 0 vulnerabilities; `git diff --check` —
  passed.
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
- PR status: open and unmerged at
  [#6](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/6),
  targeting `feat/gridmind-repurpose`. PR #5 remains open and unmodified.
- GitHub Actions: Python and dashboard checks passed on PR head
  `0b7afeecf3d37d70b95e50089f5d288d2a051dc4` in run
  [40380842304](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/actions/runs/40380842304).

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
