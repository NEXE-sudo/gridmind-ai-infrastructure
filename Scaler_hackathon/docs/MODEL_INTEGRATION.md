# NVIDIA Nemotron through Nebius Token Factory

## Provider contract verified from current documentation

The adapter uses Nebius Token Factory's OpenAI-compatible API:
`https://api.tokenfactory.nebius.com/v1/`, authenticated with
`NEBIUS_API_KEY`. It calls chat completions with the configured model ID,
`temperature=0`, a bounded token limit, and JSON response mode. The expected
response has exactly two keys:

```json
{
  "assignments": {"workload-id": "node-id"},
  "explanation": "Concise scheduling rationale."
}
```

The adapter calls the authenticated `/v1/models` catalogue through the SDK's
`models.list()` method with SDK retries disabled. Verification inspects only
the returned page; if the response indicates additional pages, it fails closed
rather than making an unbounded sequence of catalogue requests. The smoke
workflow requires an exact catalogue ID whose name is an NVIDIA Nemotron
identifier; no ID is hard-coded because availability depends on the live
catalogue and account. The currently configured ID is not evidence of
catalogue support.

Authoritative provider references, checked 2026-10-26:

- [Token Factory quickstart](https://docs.tokenfactory.nebius.com/quickstart.md)
  documents `https://api.tokenfactory.nebius.com/v1/`, the OpenAI-compatible
  chat-completions request, and the `NEBIUS_API_KEY` environment variable.
- [API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction.md)
  documents API-key authentication and the compatible request/response shape.
- [List models](https://docs.tokenfactory.nebius.com/api-reference/models/list-models.md)
  documents listing currently available model IDs.

These docs establish the contract, not live availability. This checkout had no
authorized `NEBIUS_API_KEY` or configured `GRIDMIND_MODEL`; no catalogue or
inference request was made, and no supported model ID or live result is
claimed.

## Offline setup and tests

Ordinary demo use, tests, and benchmarks do not require credentials, provider
access, network access, or paid inference. Nemotron in offline mode is explicitly
the deterministic resource-aware fallback.

From `Scaler_hackathon/`:

```bash
uv sync --locked --extra dev --extra legacy
uv run python -m pytest -q
uv run ruff check server/nemotron.py server/decision.py server/gridmind_app.py \
  server/benchmarks.py scripts/smoke_test_nemotron.py \
  tests/test_nemotron.py tests/test_smoke_test_nemotron.py \
  tests/test_gridmind_api.py tests/test_gridmind_benchmarks.py
```

## Optional, explicitly authorized live smoke test

Keep credentials on the server. Configure them in the shell or a git-ignored
`.env` file; never place them in a frontend `VITE_*` variable:

```bash
export NEBIUS_API_KEY='<Token Factory API key>'
export NEBIUS_BASE_URL='https://api.tokenfactory.nebius.com/v1/'
export GRIDMIND_MODEL='<exact NVIDIA/Nemotron ID from the authenticated catalogue>'
export GRIDMIND_INFERENCE_TIMEOUT_SECONDS=15
```

The one command below explicitly opts into a real catalogue lookup and a
single bounded inference request. It prints the configured model ID, UTC
timestamp, request attempts/retries, latency, and token usage only when the
provider returns usage. It never prints keys, headers, prompts, raw responses,
or provider error bodies. It exits non-zero on missing configuration,
catalogue mismatch, provider failure, malformed output, or an invalid
placement. The proposal is validated but never executed.

```bash
uv run python scripts/smoke_test_nemotron.py --live
```

For an authenticated catalogue-only request (no inference), explicitly opt in
as well:

```bash
uv run python scripts/smoke_test_nemotron.py --live --catalogue
```

The smoke script refuses non-HTTPS or non-Token-Factory hosts and requires an
NVIDIA Nemotron model identifier before sending credentials. The API console
also exposes a confirmation-gated `/model/verify` operation. The verification
checks the exact catalogue entry, makes one separate real request, validates
its proposal, and enables live `/run` or a bounded live benchmark only for the
verified model ID in that API process. A shell smoke test does not silently
mark a separately running API process as verified.

## Runtime safeguards and telemetry

- Requests use `max_retries=0` in the SDK and at most one explicit retry for a
  timeout or rate limit. Per-request timeouts share one configurable total
  deadline, capped at 60 seconds; response generation is bounded to 350
  tokens.
- Missing or malformed configuration, SDK/provider errors, invalid JSON,
  duplicate JSON keys, unexpected schema, and invalid placements fail closed.
  They select deterministic resource-aware scheduling in simulation runs.
- The complete proposed plan is validated before any model placement is
  applied. Unknown IDs, unavailable nodes, GPU/memory limits, model fit, node
  power, and facility power are checked by simulator code. Empty plans are
  rejected; partial plans are allowed and omitted queued work is diagnosed.
- `ai_attempts` counts eligible Nemotron scheduling decisions;
  `ai_request_attempts` counts calls started through the SDK; `ai_retries`
  counts additional calls; `ai_invocations` counts completion responses
  received; `ai_valid_responses` counts responses matching the JSON contract.
  A timeout cannot prove whether the provider executed work remotely, so
  attempt/response counters are not a provider billing ledger.
- Failures and invalid proposals are counted separately from simulator
  workload failures. `ai_fallbacks` counts deterministic fallback decisions.
  Latency is end-to-end provider-call latency including retries. Prompt and
  completion token totals are `null` when the API did not return usage; report
  counts show how many responses supplied each field. No usage is fabricated.
- `inference_mode` is explicit in decision history: `not_configured`,
  `not_attempted`, `live_success`, `live_failure_fallback`,
  `invalid_model_proposal`, or `offline_fallback`. Configuration alone never
  implies live success.
- Provider identity and model ID may appear in benchmark provenance; API keys,
  authorization headers, and raw request/response bodies are not persisted.
- Synthetic simulator energy/cost is not mixed with provider latency, model
  usage, or a real cloud bill. Model rationales are untrusted explanations,
  not causal proof.

## Live evaluation status

No live catalogue or inference evidence is available in this environment.
Provider-backed evaluation was not run. The API and CLI require a successful
catalogue plus one valid, simulator-checked live request before a live
benchmark can begin. The bounded live experiment is exploratory: one seed and
at most ten fixed-horizon steps. Offline experiments remain deterministic and
reproducible; live inference is nondeterministic and network-dependent.
