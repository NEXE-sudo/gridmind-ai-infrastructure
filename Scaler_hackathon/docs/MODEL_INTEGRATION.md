# NVIDIA Nemotron through Nebius Token Factory

## Integration boundary

GridMind uses the OpenAI-compatible Nebius Token Factory API at
`https://api.tokenfactory.nebius.com/v1/`. The server calls one model once per
Nemotron scheduling step with a compact node/workload state and expects a JSON
proposal containing exactly:

```json
{
  "assignments": {"workload-id": "node-id"},
  "explanation": "Concise model-generated rationale."
}
```

The NVIDIA model identifier is configured as `GRIDMIND_MODEL`. There is no
hard-coded model ID because catalogue availability is account- and date-
dependent. Verify the exact ID against the authenticated live catalogue before
using it; do not treat configuration presence as catalogue verification.

## Configure and verify explicitly

From `Scaler_hackathon/`, configure server-side variables in the shell or a
git-ignored `.env` loaded by the deployment:

```bash
export NEBIUS_API_KEY='<Token Factory key>'
export NEBIUS_BASE_URL='https://api.tokenfactory.nebius.com/v1/'
export GRIDMIND_MODEL='<exact NVIDIA model id returned by the catalogue>'
export GRIDMIND_INFERENCE_TIMEOUT_SECONDS=15
uv run python scripts/smoke_test_nemotron.py --catalogue
```

Only set the model to an ID actually returned by that authenticated catalogue.
Then run an explicit live inference smoke test:

```bash
uv run python scripts/smoke_test_nemotron.py
```

The smoke command reports its model and result status, but never prints the
API key or request headers. A failed smoke test is a failure, not evidence of
integration. No live test was run for this checkout because no Token Factory
credentials or verified model ID were available.

## Runtime safeguards and fallback

- API key and model configuration are read from server environment variables.
  They must never be placed in `VITE_*` variables or returned to the browser.
- The provider request has a configurable timeout, one bounded SDK retry, and
  explicit rate-limit, timeout, provider-error, empty/malformed-schema, and
  invalid-placement handling.
- Only a strict JSON response is accepted. The simulator validates workload
  eligibility, node existence/availability, GPU/memory capacity, node power,
  and facility power before an assignment can run.
- If credentials are absent or the call fails, times out, or returns invalid
  JSON/schema/placements, the resource-aware scheduler is used. The decision
  and metrics expose fallback, failure, invalid proposal, latency, and token
  usage where returned.
- Only one model coordinates the current policy step. No autonomous loop or
  multi-agent model cascade is used.
- The model's explanation is a rationale, not verified causal evidence. The
  deterministic policy is the reproducible offline baseline.
- Model cost remains unavailable unless the API supplies measured usage and
  verified pricing. The simulator does not invent a cloud bill.

The project verifies the Token Factory API base URL format from the provider's
OpenAI-compatible documentation. The exact NVIDIA model ID and live request
remain unverified until a user with authorized account access runs the two
smoke-test commands above.
