import json
from types import ModuleType, SimpleNamespace

import pytest

from server.datacenter_simulator import DatacenterSimulator
from server.decision import execute_policy_step
from server.nemotron import Proposal, request_proposal, verify_catalogue_model


class FakeOpenAIError(Exception):
    pass


class FakeAPITimeoutError(FakeOpenAIError):
    pass


class FakeRateLimitError(FakeOpenAIError):
    pass


def install_fake_openai(monkeypatch, response=None, error=None, model_ids=()):
    module = ModuleType("openai")

    class FakeClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )
            self.models = SimpleNamespace(list=self.list_models)

        def create_completion(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            if error:
                raise error
            return response

        def list_models(self):
            return SimpleNamespace(
                data=[SimpleNamespace(id=model_id) for model_id in model_ids]
            )

    module.OpenAI = FakeClient
    module.OpenAIError = FakeOpenAIError
    module.APITimeoutError = FakeAPITimeoutError
    module.RateLimitError = FakeRateLimitError
    monkeypatch.setitem(__import__("sys").modules, "openai", module)
    return FakeClient


def mock_response(content, prompt_tokens=13, completion_tokens=7):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def test_missing_credentials_falls_back_without_logging_secret(monkeypatch, caplog):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("GRIDMIND_MODEL", raising=False)
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "unavailable"
    assert proposal.assignments == {}
    assert "test-secret" not in caplog.text


def test_valid_structured_response_records_usage_and_latency(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret-not-logged")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/catalogue-model")
    install_fake_openai(
        monkeypatch,
        mock_response(
            json.dumps(
                {
                    "assignments": {"infer-001": "gpu-a"},
                    "explanation": "The small request fits this node.",
                }
            )
        ),
    )
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "model"
    assert proposal.assignments == {"infer-001": "gpu-a"}
    assert proposal.prompt_tokens == 13
    assert proposal.completion_tokens == 7
    assert proposal.latency_ms is not None
    assert "secret-not-logged" not in repr(proposal)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"assignments":{"infer-001":"gpu-a"}}',
        '{"assignments":[],"explanation":"invalid"}',
        '{"assignments":{"infer-001":4},"explanation":"invalid"}',
    ],
)
def test_malformed_response_is_flagged_for_fallback(monkeypatch, content):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/catalogue-model")
    install_fake_openai(monkeypatch, mock_response(content))
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "invalid_response"
    assert proposal.assignments == {}


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (FakeAPITimeoutError(), "timeout"),
        (FakeRateLimitError(), "rate_limited"),
        (FakeOpenAIError(), "provider_error"),
    ],
)
def test_provider_errors_are_classified_and_fail_closed(
    monkeypatch, exception, expected
):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/catalogue-model")
    install_fake_openai(monkeypatch, error=exception)
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == expected
    assert proposal.assignments == {}
    assert "secret" not in proposal.explanation


def test_catalogue_verification_requires_exact_match(monkeypatch):
    install_fake_openai(monkeypatch, model_ids=["nvidia/Other", "nvidia/Nemotron"])
    assert verify_catalogue_model("nvidia/Nemotron", "secret") is True
    assert verify_catalogue_model("nvidia/Nemotron-Nano", "secret") is False


def test_invalid_model_response_uses_deterministic_fallback(monkeypatch):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal({}, "Malformed response.", "invalid_response"),
    )
    sim = DatacenterSimulator()
    result = execute_policy_step(sim, "nemotron", use_live_model=True)

    assert result["fallback_used"] is True
    assert result["decision"] == "resource_aware_fallback"
    assert result["executed_assignments"]
    assert sim.counters["ai_invalid_proposals"] == 1
    assert sim.counters["ai_fallbacks"] == 1
