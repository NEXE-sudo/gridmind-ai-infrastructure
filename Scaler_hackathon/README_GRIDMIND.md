# GridMind — AI infrastructure scheduling sandbox

GridMind is a simulation-first prototype for GPU workload scheduling. It models
GPU nodes, memory capacity, queued jobs, deadlines, estimated power, and progress.
It compares deterministic scheduling policies and can optionally request
placement proposals from a Nebius-hosted NVIDIA Nemotron model.

GridMind is an isolated API and simulator alongside the existing energy-grid
application. It is not a production cluster scheduler. Power values are
simulated estimates; no real GPUs are controlled.

## Run locally

Use the `NEXE-sudo/gridmind-ai-infrastructure` repository, not a separate
checkout of the original `Scaler_Energy-Manager` repository. From the repository
root:

    cd Scaler_hackathon
    uv sync --extra dev
    uv run python -c "from server.gridmind_app import app; print(app.title)"
    uv run python -m pytest tests/test_gridmind_simulator.py -q
    uv run uvicorn server.gridmind_app:app --reload --port 7861

Open http://127.0.0.1:7861/docs for the API.

The import must run with `Scaler_hackathon/` as the current working directory.
Running the command from the original repository (or its own
`Scaler_hackathon/` directory) cannot import this PR's `server.gridmind_app`.
The GridMind server package also loads legacy OpenEnv components lazily so the
GridMind import does not require initializing the legacy application.

## Run a deterministic policy

    curl -X POST http://127.0.0.1:7861/run -H 'content-type: application/json' -d '{"policy":"resource_aware","steps":5}'

Policies: fifo, priority, resource_aware, and nemotron. If the model is not
configured or inference fails, the model policy falls back to resource-aware
scheduling. The `/run` response records `fallback_used` and the per-step
`decision`; malformed or simulator-invalid model proposals are rejected before
they can affect state. Confirm configuration and the per-step decision before
treating a run as live model use.

`POST /step` accepts `assignments` (workload ID to node ID) and optional
`preempt` (running workload IDs). Invalid requests return HTTP 422. Syntactically
valid but infeasible placements return a `rejected_actions` entry without
starting the workload. `POST /run` accepts one of the listed policies and 1–100
steps. `POST /reset` accepts an optional integer seed.

## Optional Nebius configuration

Set NEBIUS_API_KEY, NEBIUS_BASE_URL, and GRIDMIND_MODEL in your shell. Use a
verified model ID from the current Nebius Token Factory catalogue. Never commit
API keys. Model output remains a proposal and is validated by the simulator.

## Project documents

- [docs/GRIDMIND_ARCHITECTURE.md](docs/GRIDMIND_ARCHITECTURE.md)
- [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)
- [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md)
- [docs/PR_LOG.md](docs/PR_LOG.md)

The legacy Scaler Energy Manager README and energy-grid modules remain intact
during migration so the original project is not silently overwritten.
