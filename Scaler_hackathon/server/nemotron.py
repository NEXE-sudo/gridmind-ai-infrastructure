"""Optional Nebius Token Factory adapter for constrained scheduling proposals."""
from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@dataclass(frozen=True)
class Proposal:
    assignments: dict[str, str]
    explanation: str
    status: str
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    model_id: str | None = None
    error_code: str | None = None
    request_attempts: int = 0
    response_received: bool = False

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
    if (
        model_id != model_id.strip()
        or any(ord(char) < 32 for char in model_id)
        or len(model_id) > 200
        or api_key in model_id
    ):
        return Proposal(
            {},
            "The configured model ID is invalid; use the exact catalogue ID.",
            "invalid_configuration",
            error_code="invalid_model_id",
        )

    try:
        timeout_seconds = configured_inference_timeout_seconds()
        base_url = configured_base_url()
    except ValueError as exc:
        return Proposal(
            {},
            str(exc),
            "invalid_configuration",
            model_id=model_id,
            error_code=(
                "invalid_timeout"
                if "timeout" in str(exc).lower()
                else "invalid_base_url"
            ),
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
                "required_gpu_model": workload.get("required_gpu_model"),
                "workload_class": workload.get("workload_class", "general"),
            }
            for workload in state["workloads"]
            if workload["status"] == "pending" and workload["submitted"]
        ],
    }
    started = time.perf_counter()
    deadline = started + timeout_seconds
    request_attempts = 0
    response_received = False
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    client = None
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )
        response = None
        for attempt in range(2):
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise TimeoutError("Request deadline exceeded")
            request_attempts += 1
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    timeout=remaining,
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
                break
            except (RateLimitError, APITimeoutError):
                if attempt == 1 or deadline - time.perf_counter() <= 0.1:
                    raise
                time.sleep(min(0.1, max(0.0, deadline - time.perf_counter())))
        if response is None:
            raise OpenAIError("No response returned")
        response_received = True
        usage = getattr(response, "usage", None)
        prompt_tokens = _usage_count(usage, "prompt_tokens")
        completion_tokens = _usage_count(usage, "completion_tokens")
        latency_ms = (time.perf_counter() - started) * 1000
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            return Proposal(
                {},
                "The provider response did not contain a completion choice.",
                "invalid_response",
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_id=model_id,
                error_code="invalid_completion_schema",
                request_attempts=request_attempts,
                response_received=True,
            )
        try:
            parsed = (
                json.loads(content, object_pairs_hook=_reject_duplicate_keys)
                if isinstance(content, str)
                else None
            )
        except (json.JSONDecodeError, ValueError):
            return Proposal(
                {},
                "The model response was not valid JSON.",
                "invalid_response",
                latency_ms=latency_ms,
                model_id=model_id,
                error_code="invalid_json",
                request_attempts=request_attempts,
                response_received=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
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
                request_attempts=request_attempts,
                response_received=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        return Proposal(
            parsed["assignments"],
            parsed["explanation"][:1000],
            "model",
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_id=model_id,
            request_attempts=request_attempts,
            response_received=True,
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
    except TimeoutError:
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
        request_attempts=request_attempts,
        response_received=response_received,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _usage_count(usage: Any, field: str) -> int | None:
    value = getattr(usage, field, None) if usage is not None else None
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def configured_inference_timeout_seconds() -> float:
    try:
        timeout_seconds = float(
            os.getenv("GRIDMIND_INFERENCE_TIMEOUT_SECONDS", "15")
        )
    except ValueError as exc:
        raise ValueError(
            "The configured inference timeout must be greater than 0 and at most 60 seconds"
        ) from exc
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 60:
        raise ValueError(
            "The configured inference timeout must be greater than 0 and at most 60 seconds"
        )
    return timeout_seconds


def configured_base_url() -> str:
    base_url = os.getenv("NEBIUS_BASE_URL", DEFAULT_BASE_URL)
    try:
        parsed_url = urlsplit(base_url)
        port = parsed_url.port
    except ValueError as exc:
        raise ValueError("NEBIUS_BASE_URL is malformed") from exc
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "api.tokenfactory.nebius.com"
        or parsed_url.username
        or parsed_url.password
        or parsed_url.query
        or parsed_url.fragment
        or port not in {None, 443}
        or parsed_url.path.rstrip("/") != "/v1"
    ):
        raise ValueError("NEBIUS_BASE_URL must use the official HTTPS Token Factory API")
    return base_url


def verify_catalogue_model(model_id: str, api_key: str, timeout: float = 10.0) -> bool:
    """Confirm an exact ID is currently returned by the authenticated catalogue."""
    if (
        not isinstance(model_id, str)
        or not isinstance(api_key, str)
        or not model_id
        or not api_key
        or model_id != model_id.strip()
        or any(ord(char) < 32 for char in model_id)
        or len(model_id) > 200
        or api_key in model_id
    ):
        raise RuntimeError("Model catalogue request configuration is invalid")
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise RuntimeError("Catalogue timeout is invalid")
    try:
        from openai import OpenAI, OpenAIError
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies before checking the catalogue") from exc
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=configured_base_url(),
            timeout=timeout,
            max_retries=0,
        )
        page = client.models.list()
        if getattr(page, "has_more", False):
            raise RuntimeError("Model catalogue exceeds the bounded verification page")
        return any(model.id == model_id for model in page.data)
    except (OpenAIError, OSError, ValueError, TypeError, AttributeError) as exc:
        logger.warning("Nebius model catalogue request failed (%s)", type(exc).__name__)
        raise RuntimeError("Could not verify the model ID against the Token Factory catalogue") from exc
