import json

from server import decision, judge_demo


def test_judge_demo_evidence_is_reproducible(tmp_path, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("GRIDMIND_MODEL", raising=False)

    def reject_provider_call(*_args, **_kwargs):
        raise AssertionError("offline demo must not request live inference")

    monkeypatch.setattr(decision, "request_proposal", reject_provider_call)
    judge_demo.write_evidence(tmp_path)

    assert judge_demo.check_evidence(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    results = json.loads((tmp_path / "results.json").read_text())
    assert manifest["scenario_id"] == "node_failure_recovery"
    assert manifest["seed"] == 7
    assert manifest["live_model_enabled"] is False
    assert manifest["inference_mode"] == "deterministic_fallback"
    assert len({run["scenario_sha256"] for run in results["experiment"]["runs"]}) == 1
    assert (
        len(
            {
                run["exogenous_failure_trace_sha256"]
                for run in results["experiment"]["runs"]
            }
        )
        == 1
    )
    assert all(
        len(run["history"]) == manifest["horizon_steps"]
        and all("placement_diagnostics" in step for step in run["history"])
        for run in results["experiment"]["runs"]
    )
    nemotron = next(
        run for run in results["experiment"]["runs"] if run["policy"] == "nemotron"
    )
    assert nemotron["metrics"]["ai_invocations"] == 0
    assert nemotron["metrics"]["ai_fallbacks"] > 0
    report = (tmp_path / "report.md").read_text()
    assert "| node_failure_recovery-001 | completed" in report
    assert "node_failure_recovery-012 | completed at step 90; deadline missed" in report


def test_judge_demo_check_detects_changed_results(tmp_path):
    judge_demo.write_evidence(tmp_path)
    result_path = tmp_path / "results.json"
    results = json.loads(result_path.read_text())
    results["experiment"]["runs"][0]["metrics"]["completed_workloads"] += 1
    result_path.write_text(json.dumps(results))

    assert not judge_demo.check_evidence(tmp_path)


def test_judge_demo_allows_only_intentional_created_at_differences():
    stored = {
        "experiment": {
            "created_at": "old",
            "runs": [{"created_at": "old", "trace": {"created_at": "preserve"}}],
        }
    }
    current = {
        "experiment": {
            "created_at": "new",
            "runs": [{"created_at": "new", "trace": {"created_at": "preserve"}}],
        }
    }

    assert judge_demo._remove_intentional_timestamps(stored) == (
        judge_demo._remove_intentional_timestamps(current)
    )
    current["experiment"]["runs"][0]["trace"]["created_at"] = "changed"
    assert judge_demo._remove_intentional_timestamps(stored) != (
        judge_demo._remove_intentional_timestamps(current)
    )
