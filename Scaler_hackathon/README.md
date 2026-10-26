# GridMind — AI data-centre operations simulator

GridMind evaluates GPU workload placements under synthetic accelerator,
memory, deadline, failure, and facility power constraints. It is a simulator
and experiment workbench, not a physical infrastructure controller.

## Local setup

From this directory:

```bash
uv sync --locked --extra dev --extra legacy
uv run --locked --extra dev --extra legacy python -m pytest -q
cd agent-grid-view
npm ci
npm test -- --run
npm run lint
npx tsc -b --pretty false
npm run build
cd ..
uv run uvicorn server.gridmind_app:app --reload --port 7861
```

Open <http://127.0.0.1:7861/>. FastAPI's interactive docs are at
<http://127.0.0.1:7861/docs>. To run the dashboard with Vite hot reload, start
`npm run dev` from `agent-grid-view/` while the API is running.

## Policies and experiments

The API supports FIFO, priority, resource-aware, and optional Nemotron
proposal-based scheduling. Nemotron proposals pass the same deterministic
validation as all other actions, and unavailable/failed inference falls back
to resource-aware scheduling.

```bash
uv run --locked python -m server.benchmarks \
  --suite configs/scenarios.json --seeds 1,2,3,4,5 \
  --output-dir benchmarks/sample-suite
```

The suite runs every selected policy against the same seeded workloads and
complete exogenous failure trace for each scenario. `completed` means the
simulation reached its fixed horizon; it does not mean that every workload
finished. Reports retain all materialized jobs in the full-set denominator,
show feasible-workload completion separately, and distinguish permanent
infeasibility from unresolved horizon outcomes and their scheduler blockers.
Five seeds permit a descriptive paired bootstrap interval, not a reliable
general performance claim. The command writes `results.json`, `runs.csv`, and
`report.md`. Nemotron is offline in this sample and uses deterministic fallback.

## Optional Token Factory inference

See [`docs/MODEL_INTEGRATION.md`](docs/MODEL_INTEGRATION.md) for catalogue
verification, exact environment variables, the explicit live smoke test, and
fallback semantics. Credentials are server-side only. No live inference is
claimed until that smoke test succeeds with a verified model ID.

## Documentation

- [Architecture](docs/GRIDMIND_ARCHITECTURE.md)
- [Benchmark methodology](docs/BENCHMARK_METHODOLOGY.md)
- [Model integration](docs/MODEL_INTEGRATION.md)
- [Limitations and safety](docs/LIMITATIONS_SAFETY.md)
- [Hackathon submission package](docs/HACKATHON_SUBMISSION.md)
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md)
- [Project phase register](docs/PROJECT_PLAN.md)
- [PR log](docs/PR_LOG.md)

The legacy electricity-grid implementation and its existing tests remain in
the repository. See the repository-root README for repository history and
current submission blockers.

The GridMind runtime itself uses the default project dependencies. The
`legacy` extra is only needed for the retained OpenEnv-backed energy-grid
modules and full historical test suite. Python 3.11+ is recommended when
installing that extra; on Python 3.10, upstream Gradio/Pillow compatibility
currently requires a Pillow release with known advisories. Do not expose the
legacy UI or install that extra in a production GridMind runtime. The
`legacy-training` extra is also historical, has known dependency advisories,
and is not needed to run GridMind.

## Container

From this directory:

```bash
docker build -t gridmind .
docker run --rm -p 7861:7860 -e PORT=7860 gridmind
```

Then open <http://127.0.0.1:7861/>. To make a verified live model available,
pass `NEBIUS_API_KEY` and `GRIDMIND_MODEL` as server-side runtime variables;
never bake them into the image. The Docker daemon was unavailable during this
change, so the image build/run commands are prepared but not verified here.
