# Pull request and engineering decision log

Update this file in every PR. Keep entries factual and evidence-based.

## PR register

| PR | Phase | Scope | Status / evidence |
|---|---|---|---|
| [#1](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/1) | P0–P1 | Plan, workflow, simulator, schedulers, guarded Nemotron proposal path, API, tests | Squash-merged 2026-10-26 as `5ebc47ca8395c67aacd754bbb66a824c42081727`; post-merge verification passed |
| [#2](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/2) | P2–P7 | Complete GridMind simulation, metrics, paired-seed benchmark, dashboard, API, docs, and CI | Squash-merged 2026-10-26 as `966cfc6ae22cff284264f988e78b72ad2ac555f1`; post-merge CI and local verification passed |

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
