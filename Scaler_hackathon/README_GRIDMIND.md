# GridMind — AI infrastructure scheduling sandbox

GridMind is a simulation-first prototype for GPU workload scheduling. It models
GPU nodes, memory capacity, queued jobs, deadlines, estimated power, and progress.
It compares deterministic scheduling policies and can optionally request
placement proposals from a Nebius-hosted NVIDIA Nemotron model.

Status: initial foundation for review. This is not a production cluster
scheduler. Power values are simulated estimates; no real GPUs are controlled.

## Run locally

From the Scaler_hackathon directory:

    python -m pip install -e .
    python -m pytest tests/test_gridmind_simulator.py -q
    uvicorn server.gridmind_app:app --reload --port 7861

Open http://127.0.0.1:7861/docs for the API.

## Run a deterministic policy

    curl -X POST http://127.0.0.1:7861/run -H 'content-type: application/json' -d '{"policy":"resource_aware","steps":5}'

Policies: fifo, priority, resource_aware, and nemotron. If the model is not
configured or inference fails, the model policy falls back to resource-aware
scheduling. Confirm configuration and logs before treating a run as live model use.

## Optional Nebius configuration

Set NEBIUS_API_KEY, NEBIUS_BASE_URL, and GRIDMIND_MODEL in your shell. Use a
verified model ID from the current Nebius Token Factory catalogue. Never commit
API keys. Model output remains a proposal and is validated by the simulator.

## Project documents

- docs/GRIDMIND_ARCHITECTURE.md
- docs/PROJECT_PLAN.md
- docs/DEVELOPMENT_WORKFLOW.md
- docs/PR_LOG.md

The legacy Scaler Energy Manager README and energy-grid modules remain intact
during migration so the original project is not silently overwritten.
