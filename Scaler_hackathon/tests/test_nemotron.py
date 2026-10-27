import json
from types import ModuleType, SimpleNamespace
from typing import ClassVar

import pytest

from server.datacenter_simulator import DatacenterSimulator
from server.decision import execute_policy_step
from server.metrics import aggregate_runs, calculate_metrics
from server.nemotron import Proposal, request_proposal, verify_catalogue_model


class FakeOpenAIError(Exception):
    pass


class FakeAPITimeoutError(FakeOpenAIError):
    pass


class FakeRateLimitError(FakeOpenAIError):
    pass


class FakeCataloguePage:
    def __init__(self, data, has_more=False):
        self.data = data
        self.has_more = has_more

    def __iter__(self):
        return iter(self.data)


def install_fake_openai(
    monkeypatch, response=None, error=None, model_ids=(), catalogue_has_more=False
):
    module = ModuleType("openai")

    class FakeClient:
        instances: ClassVar[list] = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.request_kwargs = []
            self.instances.append(self)
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self.create_completion)
            )
            self.models = SimpleNamespace(list=self.list_models)

        def create_completion(self, **kwargs):
            assert kwargs["response_format"] == {"type": "json_object"}
            self.request_kwargs.append(kwargs)
            if error:
                if isinstance(error, list):
                    raise error.pop(0)
                raise error
            return response

        def list_models(self):
            if error:
                raise error
            return FakeCataloguePage(
                [SimpleNamespace(id=model_id) for model_id in model_ids],
                has_more=catalogue_has_more,
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
        usage=(
            None
            if prompt_tokens is None and completion_tokens is None
            else SimpleNamespace(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
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
    assert proposal.request_attempts == 1
    assert proposal.response_received is True
    assert proposal.latency_ms is not None
    assert "secret-not-logged" not in repr(proposal)


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"assignments":{"infer-001":"gpu-a"},"assignments":{"infer-002":"gpu-a"},"explanation":"duplicate"}',
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
    assert proposal.request_attempts == 1
    assert proposal.response_received is True


def test_missing_completion_choice_is_reported_as_invalid_response(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/catalogue-model")
    response = SimpleNamespace(
        choices=[],
        usage=SimpleNamespace(prompt_tokens=4, completion_tokens=0),
    )
    install_fake_openai(monkeypatch, response=response)

    proposal = request_proposal(DatacenterSimulator().state())

    assert proposal.status == "invalid_response"
    assert proposal.error_code == "invalid_completion_schema"
    assert proposal.response_received is True
    assert proposal.prompt_tokens == 4
    assert proposal.completion_tokens == 0
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
    assert proposal.request_attempts == (
        2 if expected in {"timeout", "rate_limited"} else 1
    )


def test_catalogue_verification_requires_exact_match(monkeypatch):
    client_class = install_fake_openai(
        monkeypatch, model_ids=["nvidia/Other", "nvidia/Nemotron"]
    )
    assert verify_catalogue_model("nvidia/Nemotron", "secret") is True
    assert verify_catalogue_model("nvidia/Nemotron-Nano", "secret") is False
    assert client_class.instances[0].kwargs["api_key"] == "secret"
    assert client_class.instances[0].kwargs["max_retries"] == 0


def test_catalogue_errors_are_sanitized(monkeypatch):
    install_fake_openai(monkeypatch, error=FakeOpenAIError("secret provider body"))
    with pytest.raises(RuntimeError, match="Could not verify") as error:
        verify_catalogue_model("nvidia/Nemotron", "secret")
    assert "secret" not in str(error.value)


def test_catalogue_verification_refuses_unbounded_pagination(monkeypatch):
    install_fake_openai(
        monkeypatch,
        model_ids=["nvidia/Nemotron"],
        catalogue_has_more=True,
    )

    with pytest.raises(RuntimeError, match="bounded verification page"):
        verify_catalogue_model("nvidia/Nemotron", "secret")


def test_rate_limit_retry_is_bounded_and_counted(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    client_class = install_fake_openai(
        monkeypatch,
        response=mock_response(
            '{"assignments":{"infer-001":"gpu-a"},"explanation":"fits"}'
        ),
        error=[FakeRateLimitError()],
    )
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "model"
    assert proposal.request_attempts == 2
    assert proposal.response_received is True
    client = client_class.instances[0]
    assert client.kwargs["max_retries"] == 0
    assert len(client.request_kwargs) == 2
    assert all(0 < item["timeout"] <= 15 for item in client.request_kwargs)


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
    assert result["inference_mode"] == "invalid_model_proposal"


@pytest.mark.parametrize(
    ("assignment", "expected_reason"),
    [
        ({"infer-001": "missing-node"}, "unknown_node"),
        ({"missing-workload": "gpu-a"}, "unknown_or_not_eligible"),
    ],
)
def test_empty_or_impossible_model_plan_is_rejected_before_application(
    monkeypatch, assignment, expected_reason
):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal(
            assignment,
            "Try an unknown node.",
            "model",
            request_attempts=1,
            response_received=True,
        ),
    )
    sim = DatacenterSimulator()
    result = execute_policy_step(sim, "nemotron", use_live_model=True)

    assert result["inference_mode"] == "invalid_model_proposal"
    assert result["proposal_validation_rejections"] == [
        {"workload_id": next(iter(assignment)), "reason": expected_reason}
    ]
    assert result["executed_assignments"] != assignment
    assert sim.counters["ai_invocations"] == 1
    assert sim.counters["ai_request_attempts"] == 1
    assert sim.counters["ai_valid_responses"] == 1
    assert sim.counters["ai_invalid_proposals"] == 1
    assert sim.counters["ai_fallbacks"] == 1


def test_partial_model_plan_is_allowed_and_not_counted_as_invalid(monkeypatch):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal(
            {"infer-001": "gpu-a"},
            "Place the fitting inference job.",
            "model",
            request_attempts=1,
        ),
    )
    result = execute_policy_step(
        DatacenterSimulator(), "nemotron", use_live_model=True
    )
    assert result["inference_mode"] == "live_success"
    assert result["fallback_used"] is False
    assert result["executed_assignments"] == {"infer-001": "gpu-a"}


def test_missing_usage_is_not_reported_as_zero(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    install_fake_openai(
        monkeypatch,
        mock_response(
            '{"assignments":{"infer-001":"gpu-a"},"explanation":"fits"}',
            prompt_tokens=None,
            completion_tokens=None,
        ),
    )
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.prompt_tokens is None
    assert proposal.completion_tokens is None


def test_metrics_keep_unreturned_usage_null(monkeypatch):
    monkeypatch.setattr(
        "server.decision.request_proposal",
        lambda _: Proposal(
            {"infer-001": "gpu-a"},
            "Fits.",
            "model",
            request_attempts=1,
            response_received=True,
        ),
    )
    sim = DatacenterSimulator()
    execute_policy_step(sim, "nemotron", use_live_model=True)
    metrics = calculate_metrics(sim)
    assert metrics["ai_prompt_tokens"] is None
    assert metrics["ai_completion_tokens"] is None
    assert metrics["ai_prompt_token_reports"] == 0
    assert metrics["ai_completion_token_reports"] == 0


def test_aggregate_token_usage_uses_only_runs_that_report_usage():
    summary = aggregate_runs(
        [
            {
                "status": "completed",
                "metrics": {
                    "ai_prompt_tokens": None,
                    "ai_completion_tokens": None,
                },
            },
            {
                "status": "completed",
                "metrics": {
                    "ai_prompt_tokens": 12,
                    "ai_completion_tokens": 3,
                },
            },
        ]
    )
    assert summary["metrics"]["ai_prompt_tokens"]["mean"] == 12
    assert summary["metrics"]["ai_prompt_tokens"]["n"] == 1
    assert summary["metrics"]["ai_completion_tokens"]["mean"] == 3
    assert summary["metrics"]["ai_completion_tokens"]["n"] == 1


def test_provider_failure_after_a_success_uses_fallback(monkeypatch):
    proposals = iter(
        [
            Proposal(
                {"infer-001": "gpu-a"},
                "Fits.",
                "model",
                request_attempts=1,
                response_received=True,
            ),
            Proposal(
                {},
                "Provider failure.",
                "timeout",
                request_attempts=2,
            ),
        ]
    )
    monkeypatch.setattr(
        "server.decision.request_proposal", lambda _: next(proposals)
    )
    sim = DatacenterSimulator()
    first = execute_policy_step(sim, "nemotron", use_live_model=True)
    second = execute_policy_step(sim, "nemotron", use_live_model=True)

    assert first["inference_mode"] == "live_success"
    assert second["inference_mode"] == "live_failure_fallback"
    assert second["fallback_used"] is True
    assert second["proposal_request_attempts"] == 2
    assert sim.counters["ai_invocations"] == 1
    assert sim.counters["ai_request_attempts"] == 3
    assert sim.counters["ai_retries"] == 1
    assert sim.counters["ai_failures"] == 1
    assert sim.counters["ai_fallbacks"] == 1


@pytest.mark.parametrize(
    ("model_id", "timeout"),
    [
        (" nvidia/Nemotron-test", "15"),
        ("nvidia/Nemotron-secret", "15"),
        ("nvidia/Nemotron-test", "nan"),
        ("nvidia/Nemotron-test", "61"),
    ],
)
def test_invalid_configuration_fails_without_provider_request(
    monkeypatch, model_id, timeout
):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", model_id)
    monkeypatch.setenv("GRIDMIND_INFERENCE_TIMEOUT_SECONDS", timeout)
    monkeypatch.delitem(__import__("sys").modules, "openai", raising=False)
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "invalid_configuration"
    assert proposal.request_attempts == 0


def test_custom_non_nebius_base_url_fails_closed(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    monkeypatch.setenv("NEBIUS_BASE_URL", "http://attacker.example/v1/")
    proposal = request_proposal(DatacenterSimulator().state())
    assert proposal.status == "invalid_configuration"
    assert proposal.error_code == "invalid_base_url"
    assert proposal.request_attempts == 0
