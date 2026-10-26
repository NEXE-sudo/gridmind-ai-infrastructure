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
- `POST /reset` with `{"seed": 31, "scenario": "node_failure"}` (scenarios:
  `standard`, `workload_surge`, `node_failure`, `tight_deadlines`)
- `POST /step` with an assignments map and optional `preempt`/`cancel` lists
- `POST /run` with a policy and 1–100 steps
- `POST /benchmarks/run` with 1–5 unique seeds and policies
- `GET /benchmarks/latest`, `GET /history?limit=20`,
  `GET /exports/latest.csv`

Invalid request shapes receive HTTP 422. Infeasible placements are rejected
with explicit reasons. The API is single-process and single-session; the
operation lock serializes simulation and benchmark mutations.

## Experiment command

```bash
uv run python -m server.benchmarks \
  --config configs/demo.json --seeds 1,2,3 \
  --output-dir benchmarks/sample
```

The model is optional; without a verified model and server-side credentials,
Nemotron uses a deterministic resource-aware fallback.
