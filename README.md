# GridMind

GridMind is a simulation-first data-centre operations console for evaluating
GPU workload scheduling against accelerator capacity, memory, deadlines, node
failures, and a facility power budget. It compares FIFO, priority,
resource-aware, and optional Nemotron-proposal scheduling. The Nemotron path
is opt-in; its offline default is deterministic fallback, not live inference.

The simulator, API, dashboard, and documentation are in
[`Scaler_hackathon/`](./Scaler_hackathon/). The inherited Scaler Energy Manager
remains as historical source and is not GridMind's runtime. GridMind controls
no physical infrastructure; all workload, failure, power, energy, and price
values are simulated.

## Requirements

- Python 3.11 (Python 3.10+ is supported by the project), [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm

## Clean-checkout setup and tests

From the repository root:

```bash
cd Scaler_hackathon
uv sync --locked --extra dev --extra legacy
uv run --locked --extra dev --extra legacy python -m pytest -q
uv run --locked --extra dev --extra legacy ruff check \
  server/judge_demo.py server/benchmarks.py tests/test_judge_demo.py
uv lock --check
cd agent-grid-view
npm ci
npm test -- --run
npm run lint
npx tsc -b --pretty false
npm run build
```

The test command follows CI and installs the historical `legacy` extra needed
by the full repository test suite. The GridMind API and default demo do not
require provider credentials, internet access to an inference provider, or a
GPU. `npm ci` requires npm registry access only when dependencies are not
already cached. The separate `legacy-training` extra is not needed to run or
test GridMind.

## Run the application

After building the dashboard, from `Scaler_hackathon/`:

```bash
uv run uvicorn server.gridmind_app:app --host 127.0.0.1 --port 7861
```

Open <http://127.0.0.1:7861/> for the dashboard or
<http://127.0.0.1:7861/docs> for the API. For dashboard hot reload, leave the
API running and start `npm run dev` from `Scaler_hackathon/agent-grid-view` in
a second terminal; Vite proxies API requests to port 7861.

## Focused offline demo and checked-in evidence

From `Scaler_hackathon/`:

```bash
uv run python -m server.judge_demo
uv run python -m server.judge_demo --check
```

The first command regenerates the separately scoped `benchmarks/judge-demo/`
artifacts from the `node_failure_recovery` scenario, seed 7, and 90-step
fixed horizon. The second runs the scenario again and compares the generated
manifest, raw run records, and report to the checked-in evidence. It ignores
only `experiment.created_at` and each run's `created_at`; every other JSON
field is compared. The report includes the actual feasible
placement candidates, a scheduler deferral diagnostic, per-workload outcomes,
exact denominators, and offline Nemotron telemetry. See the
[walkthrough](./Scaler_hackathon/docs/DEMO_SCRIPT.md) and
[generated report](./Scaler_hackathon/benchmarks/judge-demo/report.md).

## Reproduce the primary scenario suite

From `Scaler_hackathon/`:

```bash
uv run python -m server.benchmarks \
  --suite configs/scenarios.json --seeds 1,2,3,4,5 \
  --policies fifo,priority,resource_aware,nemotron \
  --output-dir benchmarks/reproduced-suite
```

This runs all ten versioned synthetic scenarios using the same seeds and
failure traces across policies and writes raw JSON, CSV, and Markdown output.
The checked-in primary sample is
[`benchmarks/sample-suite/report.md`](./Scaler_hackathon/benchmarks/sample-suite/report.md).
Offline Nemotron results are deterministic fallback outcomes; they are not
model inference or evidence that AI improves scheduling.

## Optional live model verification

The normal setup, test, dashboard, and demo paths make no provider request.
For an explicitly authorized real smoke test, configure `NEBIUS_API_KEY` and
an exact, catalogue-supported NVIDIA Nemotron `GRIDMIND_MODEL` in the server
environment only, then run from `Scaler_hackathon/`:

```bash
uv run python scripts/smoke_test_nemotron.py --live
```

This is a paid/network-dependent external request. The script requires the
explicit `--live` opt-in, checks catalogue access and validates one real
proposal; a successful deterministic fallback is not a successful live test.
Never put credentials in the dashboard or a `VITE_*` variable. No live
Token Factory request or Nebius deployment is claimed for the checked-in
evidence. See the [model integration guide](./Scaler_hackathon/docs/MODEL_INTEGRATION.md).

## Scope and submission readiness

The [architecture](./Scaler_hackathon/docs/GRIDMIND_ARCHITECTURE.md),
[benchmark methodology](./Scaler_hackathon/docs/BENCHMARK_METHODOLOGY.md),
[safety limitations](./Scaler_hackathon/docs/LIMITATIONS_SAFETY.md),
[provenance audit](./Scaler_hackathon/docs/PROVENANCE_AUDIT.md), and
[hackathon checklist](./Scaler_hackathon/docs/HACKATHON_SUBMISSION.md) explain
what is implemented and what remains blocked or requires operator action.
The repository is public, but it has no repository-level open-source license.
No live model request, public deployment, published demo video, rights
clearance, or hackathon submission is claimed.
