# GridMind development workflow

## Working agreement

Prefer phase-sized pull requests that deliver a coherent capability across code,
tests, docs, and a demonstrable user outcome. Avoid one-PR-per-file increments.
Split only at a real integration boundary or where review risk demands it.

## Branch and PR rules

1. Start from the latest integration branch and inspect git status.
2. Use one descriptive branch per phase, e.g. feat/gridmind-phase-2-scheduler.
3. Preserve the original baseline branch; do not force-push shared branches.
4. Include implementation, tests, docs, and phase-register changes in the same PR.
5. Run targeted tests, then relevant full-suite and frontend checks.
6. Review the diff for old-domain leftovers, secrets, generated files, and unsupported claims.
7. Open a PR to the agreed integration branch. Describe behaviour and evidence in plain sentences.
8. Merge only after checks and review. Record the merged commit and update the phase register.

## Required PR description

- Problem and user-visible outcome
- Main design choices and trade-offs
- Components changed
- Test commands and exact results
- Manual smoke-test steps
- Security and failure-mode notes
- Known limitations and next phase

## Quality gates

- Deterministic tests for simulation and scheduling.
- Invalid actions must be rejected without corrupting state.
- Model output is validated by the same simulator rules as other proposals.
- Inference failures must not break the deterministic fallback.
- Compare policies using the same workloads and seeds.
- Separate estimated energy from real telemetry.
- Never log or commit API keys.
- Do not claim tests, live model calls, benchmarks, or deployments without evidence.

## Local commands

From the Scaler_hackathon directory:

    python -m pytest tests/test_gridmind_simulator.py -q
    uvicorn server.gridmind_app:app --reload --port 7861

In a second terminal:

    curl -fsS http://127.0.0.1:7861/health
    curl -fsS http://127.0.0.1:7861/state
    curl -fsS -X POST http://127.0.0.1:7861/run -H 'content-type: application/json' -d '{"policy":"resource_aware","steps":5}'

The GridMind API is initially separate so the existing energy-grid application
remains available while migration is in progress.
