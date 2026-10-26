# GridMind demo script and storyboard

Target length: 2 minutes 30 seconds. Capture the actual application and shell;
do not fabricate screenshots or insert benchmark values not produced by the
commands. The video has not been recorded in this implementation environment.

## Prepare the recording

From `Scaler_hackathon/`:

```bash
uv sync --locked --extra dev
cd agent-grid-view
npm ci
npm run build
cd ..
uv run uvicorn server.gridmind_app:app --port 7861
```

Open <http://127.0.0.1:7861/>. In a separate terminal, generate fresh
reproducible results:

```bash
uv run python -m server.benchmarks \
  --config configs/demo.json --seeds 1,2,3 \
  --output-dir benchmarks/sample
```

Optional live segment: only if a verified model ID and authorized key are
available, run `uv run python scripts/smoke_test_nemotron.py` first. Otherwise
show Nemotron's explicit fallback state and say it is offline fallback.

## Timed storyboard

| Time | Scene and spoken point | Evidence to capture |
|---|---|---|
| 0:00–0:20 | Introduce the problem: GPU jobs compete for memory/capacity, deadlines and a shared power budget. Explain this is a simulation. | Dashboard header, simulation-only indicator, seed and node inventory. |
| 0:20–0:45 | Show the heterogeneous node pool, workload priorities/deadlines, current queue, and estimated power/energy. State power is synthetic. | Actual displayed nodes/workloads/metrics; hover/read labels if needed. |
| 0:45–1:10 | Select workload surge or tight deadlines, set seed 42, reset, and step the resource-aware scheduler. | Scenario control, visible state change, decision trace and validated allocations. |
| 1:10–1:35 | Select node failures, reset, and run several steps; point out requeue/recovery behavior. | Workload statuses and node status from actual API/UI behavior. |
| 1:35–2:05 | Run the benchmark on three seeds and compare FIFO, priority, resource-aware, and Nemotron. | Benchmark output/result panel; note Nemotron rows are fallback unless live was verified. |
| 2:05–2:25 | Explain deterministic validation and the fallback boundary. If live smoke succeeded, show its real sanitized status; otherwise explicitly say live verification is pending. | Decision trace and relevant terminal result without credentials. |
| 2:25–2:30 | Close with reproducibility, limitations, and repository link. | Setup command/readme briefly. |

## Capture checklist

- Use the local app and freshly generated output; do not stage synthetic
  screenshots or alter displayed values.
- Avoid terminal history, environment dumps, `.env`, HTTP headers, tokens, or
  other credentials in frame.
- State that simulation power/cost is estimated and that the project does not
  control real infrastructure.
- Keep the final video under three minutes and publish it only after verifying
  it is publicly viewable.
