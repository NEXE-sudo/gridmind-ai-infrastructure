# Pull request and engineering decision log

Update this file in every PR. Keep entries factual and evidence-based.

## PR register

| PR | Phase | Scope | Status / evidence |
|---|---|---|---|
| [#1](https://github.com/NEXE-sudo/gridmind-ai-infrastructure/pull/1) | P0–P1 | Plan, workflow, simulator, schedulers, guarded Nemotron proposal path, API, tests | Fixes committed and pushed; GitHub reports no required checks/reviews; merge decision pending |

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
  part of this PR. Merge outcome is recorded only after GitHub confirms it.

### Isolated migration
GridMind gets a separate simulator and API entry point before energy-specific
modules are replaced. This preserves provenance and makes the new domain testable.

### Model proposals are untrusted
Nemotron cannot bypass resource or power checks. If credentials are missing or
inference fails, the deterministic scheduler is used instead.

### Simulation assumptions are visible
Power coefficients and one-minute ticks are synthetic. They are appropriate for
controlled comparisons, not claims about actual GPU power or energy.
