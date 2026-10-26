import json

import pytest

from scripts import smoke_test_nemotron
from server.nemotron import Proposal


def test_smoke_refuses_to_request_without_explicit_opt_in(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    monkeypatch.setattr(
        smoke_test_nemotron,
        "verify_catalogue_model",
        lambda *_: pytest.fail("must not query catalogue"),
    )

    assert smoke_test_nemotron.main([]) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_smoke_reports_verified_live_request_without_secrets(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret-never-print")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    monkeypatch.setattr(
        smoke_test_nemotron,
        "verify_catalogue_model",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        smoke_test_nemotron,
        "request_proposal",
        lambda _: Proposal(
            {"infer-001": "gpu-a"},
            "Fits.",
            "model",
            latency_ms=12.5,
            prompt_tokens=10,
            completion_tokens=4,
            model_id="nvidia/Nemotron-test",
            request_attempts=1,
            response_received=True,
        ),
    )

    assert smoke_test_nemotron.main(["--live"]) == 0
    output = capsys.readouterr().out
    assert "catalogue_status=verified_exact_match" in output
    assert '"inference_status": "live_success"' in output
    assert '"request_attempts": 1' in output
    assert "secret-never-print" not in output
    assert json.loads(output[output.index("{") :])["provider_request_status"] == "success"


def test_smoke_distinguishes_provider_failure_from_fallback(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    monkeypatch.setattr(
        smoke_test_nemotron,
        "verify_catalogue_model",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        smoke_test_nemotron,
        "request_proposal",
        lambda _: Proposal({}, "Fallback only.", "timeout", error_code="timeout"),
    )

    assert smoke_test_nemotron.main(["--live"]) == 1
    output = capsys.readouterr().out
    assert '"inference_status": "live_failure"' in output
    assert '"provider_request_status": "failed"' in output


def test_smoke_never_prints_a_secret_misconfigured_as_model_id(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-secret")
    monkeypatch.setattr(
        smoke_test_nemotron,
        "verify_catalogue_model",
        lambda *_: pytest.fail("must refuse before catalogue request"),
    )

    assert smoke_test_nemotron.main(["--live"]) == 2
    output = capsys.readouterr().out
    assert "secret" not in output


def test_smoke_rejects_invalid_timeout_before_catalogue_request(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "secret")
    monkeypatch.setenv("GRIDMIND_MODEL", "nvidia/Nemotron-test")
    monkeypatch.setenv("GRIDMIND_INFERENCE_TIMEOUT_SECONDS", "nan")
    monkeypatch.setattr(
        smoke_test_nemotron,
        "verify_catalogue_model",
        lambda *_args, **_kwargs: pytest.fail("must not query catalogue"),
    )

    assert smoke_test_nemotron.main(["--live"]) == 2
    assert "no request was made" in capsys.readouterr().out
