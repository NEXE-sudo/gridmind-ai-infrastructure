# GridMind runbook

This is the compact operator reference for the application in this directory.
For system setup, policy details, experiment commands, or submission caveats,
see [`README.md`](README.md) and the project documents.

## Start

```bash
uv sync --locked --extra dev
uv run uvicorn server.gridmind_app:app --reload --port 7861
```

Open <http://127.0.0.1:7861/> or <http://127.0.0.1:7861/docs>.

## Operations

- `GET /health`, `GET /ready`, `GET /state`, `GET /nodes`, `GET /workloads`
- `GET /policies`
- `POST /reset` with `{"seed": 31, "scenario": "node_failure_recovery"}`.
  The scenario catalogue is available from `GET /scenarios`.
- `POST /step` with an assignments map and optional `preempt`/`cancel` lists
- `POST /run` with a policy and 1–100 steps
- `POST /benchmarks/run` with 1–5 unique seeds and policies
- `POST /benchmarks/suite` with 1–2 seeds and selected policies
- `GET /benchmarks/latest`, `GET /history?limit=20`,
  `GET /exports/latest.csv`

Invalid request shapes receive HTTP 422. Infeasible placements are rejected
with explicit reasons. The API is single-process and single-session; the
operation lock serializes simulation and benchmark mutations.

## Experiment command

```bash
uv run --locked python -m server.benchmarks \
  --suite configs/scenarios.json --seeds 1,2,3,4,5 \
  --output-dir benchmarks/sample-suite
```

Each policy uses the same materialized jobs and failure trace for a seed.
`completed` means the fixed simulation horizon was reached, not that every job
completed. Infeasible and unresolved jobs remain in reported denominators.
The model is optional; without a verified model and server-side credentials,
Nemotron uses a deterministic resource-aware fallback.
