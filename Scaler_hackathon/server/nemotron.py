"""Optional Nebius Token Factory adapter for constrained scheduling proposals."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@dataclass(frozen=True)
class Proposal:
    assignments: dict[str, str]
    explanation: str
    status: str
    latency_ms: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_id: str | None = None
    error_code: str | None = None

    @property
    def used_model(self) -> bool:
        return self.status == "model"


def request_proposal(state: dict[str, Any]) -> Proposal:
    api_key = os.getenv("NEBIUS_API_KEY")
    model_id = os.getenv("GRIDMIND_MODEL")
    if not api_key or not model_id:
        return Proposal(
            {},
            "Live Nemotron is not configured; use deterministic resource-aware scheduling.",
            "unavailable",
            error_code="credentials_or_model_missing",
        )

    try:
        from openai import APITimeoutError, OpenAI, OpenAIError, RateLimitError
    except ImportError:
        return Proposal(
            {},
            "The OpenAI-compatible SDK is unavailable; use the deterministic fallback.",
            "unavailable",
            error_code="sdk_missing",
        )

    payload = {
        "step": state["step"],
        "power_budget_kw": state["power_budget_kw"],
        "nodes": [
            {
                "id": node["id"],
                "gpu_model": node["gpu_model"],
                "free_gpus": node["gpu_count"] - node["allocated_gpus"],
                "free_memory_gb": node["memory_gb"] - node["allocated_memory_gb"],
                "available": node["available"],
            }
            for node in state["nodes"]
        ],
        "pending": [
            {
                "id": workload["id"],
                "gpu_count": workload["gpu_count"],
                "memory_gb": workload["memory_gb"],
                "priority": workload["priority"],
                "deadline": workload["deadline"],
                "remaining": workload["remaining"],
            }
            for workload in state["workloads"]
            if workload["status"] == "pending" and workload["submitted"]
        ],
    }
    started = time.perf_counter()
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
            timeout=float(os.getenv("GRIDMIND_INFERENCE_TIMEOUT_SECONDS", "15")),
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=model_id,
            temperature=0,
            max_tokens=350,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Choose safe workload placements using only the supplied state. "
                        "Return JSON with exactly these keys: assignments (object mapping "
                        "workload IDs to node IDs) and explanation (one concise string). "
                        "Never invent IDs. All placements are proposals and will be "
                        "validated deterministically."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
            ],
        )
        latency_ms = (time.perf_counter() - started) * 1000
        message = response.choices[0].message
        content = message.content
        try:
            parsed = json.loads(content) if isinstance(content, str) else None
        except json.JSONDecodeError:
            return Proposal(
                {},
                "The model response was not valid JSON.",
                "invalid_response",
                latency_ms=latency_ms,
                model_id=model_id,
                error_code="invalid_json",
            )
        if (
            not isinstance(parsed, dict)
            or set(parsed) != {"assignments", "explanation"}
            or not isinstance(parsed["assignments"], dict)
            or not isinstance(parsed["explanation"], str)
            or any(
                not isinstance(workload_id, str) or not isinstance(node_id, str)
                for workload_id, node_id in parsed["assignments"].items()
            )
        ):
            return Proposal(
                {},
                "The model response did not match the required JSON schema.",
                "invalid_response",
                latency_ms=latency_ms,
                model_id=model_id,
                error_code="invalid_schema",
            )

        usage = response.usage
        return Proposal(
            parsed["assignments"],
            parsed["explanation"][:1000],
            "model",
            latency_ms=latency_ms,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            model_id=model_id,
        )
    except RateLimitError:
        status, error_code, explanation = (
            "rate_limited",
            "rate_limited",
            "Nebius rate-limited the request; use deterministic scheduling.",
        )
    except APITimeoutError:
        status, error_code, explanation = (
            "timeout",
            "timeout",
            "Nemotron inference timed out; use deterministic scheduling.",
        )
    except (OpenAIError, OSError, ValueError, TypeError, AttributeError, IndexError) as exc:
        status, error_code, explanation = (
            "provider_error",
            type(exc).__name__,
            "Nemotron inference failed; use deterministic scheduling.",
        )
    logger.warning("Nemotron request unavailable (%s)", error_code)
    return Proposal(
        {},
        explanation,
        status,
        latency_ms=(time.perf_counter() - started) * 1000,
        model_id=model_id,
        error_code=error_code,
    )


def verify_catalogue_model(model_id: str, api_key: str, timeout: float = 10.0) -> bool:
    """Confirm an exact ID is currently returned by the authenticated catalogue."""
    try:
        from openai import OpenAI, OpenAIError
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies before checking the catalogue") from exc
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
            timeout=timeout,
            max_retries=0,
        )
        return any(model.id == model_id for model in client.models.list().data)
    except OpenAIError as exc:
        logger.warning("Nebius model catalogue request failed (%s)", type(exc).__name__)
        raise RuntimeError("Could not verify the model ID against the Token Factory catalogue") from exc
