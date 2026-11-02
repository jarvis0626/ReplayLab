"""Evaluation orchestration tests use explicit observations, never live calls."""

import hashlib
import json
import sys
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.digital_schemas import ScreenElement, ScreenObservation
from app.evaluation_api import register_evaluation_routes
from app.providers.meta import ProviderError
from app.services.digital_evaluation import manifest_fingerprint
from app.services.nvidia_evaluation import (
    DEFAULT_HOST,
    DEFAULT_MODEL,
    empty_nvidia_report,
    load_nvidia_report,
    run_nvidia_evaluation,
)


def dataset(directory, *, count=1, expected="pass"):
    (directory / "screenshots").mkdir()
    image = b"explicit controlled image bytes"
    (directory / "screenshots/case-a.png").write_bytes(image)
    task = {"id": "t", "title": "Reviewed workflow", "modality": "digital", "objects": [], "steps": [
        {"id": "s", "title": "Show Ready", "screen_rules": [{"id": "r", "kind": "text_present", "expected": "Ready"}]},
    ]}
    (directory / "workflow.json").write_text(json.dumps(task), encoding="utf-8")
    manifest = {"name": "Explicit test challenge", "label_provenance": "Fixed test labels, no human study", "cases": [
        {"id": f"c{index}", "title": "Controlled case", "category": "correct", "expected": expected,
         "screenshot": "case-a.png", "screenshot_sha256": hashlib.sha256(image).hexdigest(),
         "reference_step_id": "s", "completed_step_ids": []}
        for index in range(count)
    ]}
    (directory / "cases.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def observation(*, mode="nvidia", verified=True, cached=False):
    return ScreenObservation(
        elements=[ScreenElement(text="Ready", confidence=.99, source="nvidia:test:ocr_corroborated")],
        visible_text="Ready", confidence=.99, image_quality=1, provider_mode=mode,
        provenance={"live_api_verified": verified, "api_response_validated": verified, "cache_hit": cached},
    )


def test_no_consent_prevents_any_dataset_read_or_observer_call(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", lambda *a, **k: pytest.fail("No upload allowed"))
    with pytest.raises(ValueError, match="consent"):
        run_nvidia_evaluation(object(), dataset_directory=tmp_path)


def test_empty_nvidia_report_never_relabels_the_local_ocr_baseline():
    report = empty_nvidia_report()
    assert report["provider_mode"] == "nvidia" and report["sample_size"] == 0
    assert report["live_api_verified"] is False
    assert report["accuracy"] is None and report["false_certainty_rate"] is None
    assert report["model"] == DEFAULT_MODEL


def test_ground_truth_never_reaches_observer_and_disagreements_are_retained(tmp_path, monkeypatch):
    dataset(tmp_path, expected="uncertain")
    marker = object()
    calls = []

    def observe(pixels, mode, provider, *, cloud_consent):
        assert pixels == b"explicit controlled image bytes"
        assert mode == "nvidia" and provider is marker and cloud_consent is True
        calls.append(True)
        return observation()

    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", observe)
    output = tmp_path / "report.json"
    report = run_nvidia_evaluation(marker, cloud_consent=True, dataset_directory=tmp_path, output_path=output)
    assert len(calls) == 1 and report["sample_size"] == 1
    assert report["accuracy"] == 0 and report["false_certainty_rate"] == 1
    assert report["details"][0]["predicted"] == "pass" and report["details"][0]["expected"] == "uncertain"
    assert report["details"][0]["failure_notes"] and report["live_api_verified"] is True
    assert json.loads(output.read_text())["model"] == DEFAULT_MODEL


@pytest.mark.parametrize("mode,verified", [("local_ocr", True), ("mock", True), ("nvidia", False)])
def test_unknown_or_local_only_results_are_not_scored_as_cloud_inference(tmp_path, monkeypatch, mode, verified):
    dataset(tmp_path)
    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", lambda *a, **k: observation(mode=mode, verified=verified))
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert report["sample_size"] == 0 and len(report["skipped"]) == 1
    assert report["accuracy"] is None and report["live_api_verified"] is False
    assert report["skipped"][0]["code"] == "unavailable_evidence"


def test_permanent_provider_error_stops_further_paid_requests_and_keeps_unknown_metrics(tmp_path, monkeypatch):
    dataset(tmp_path, count=3)
    calls = []

    def denied(*args, **kwargs):
        calls.append(True)
        raise ProviderError("NVIDIA credential was rejected.", "authentication", 401)

    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", denied)
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert len(calls) == report["attempted_cases"] == 1
    assert report["sample_size"] == 0 and report["accuracy"] is None
    assert len(report["skipped"]) == 3
    assert [case["attempted"] for case in report["skipped"]] == [True, False, False]


@pytest.mark.parametrize("code", ["connection", "timeout", "upstream_error", "rate_limit", "pending"])
def test_two_consecutive_unavailable_calls_open_circuit_without_fabricated_predictions(tmp_path, monkeypatch, code):
    dataset(tmp_path, count=20)
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(True)
        raise ProviderError("NVIDIA is unavailable for this controlled test.", code)

    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", unavailable)
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert len(calls) == report["attempted_cases"] == 2
    assert report["sample_size"] == 0 and report["accuracy"] is None
    assert report["live_api_verified"] is False and report["failure_circuit_open"] is True
    assert report["stop_reason"] == "unavailable_circuit_open"
    assert len(report["skipped"]) == 20
    assert sum(item["attempted"] for item in report["skipped"]) == 2
    assert all("predicted" not in item for item in report["skipped"])


def test_success_resets_consecutive_failure_circuit(tmp_path, monkeypatch):
    dataset(tmp_path, count=4)
    responses = iter(["timeout", observation(), "connection", observation()])

    def observe(*args, **kwargs):
        value = next(responses)
        if isinstance(value, str):
            raise ProviderError("Controlled unavailable response.", value)
        return value

    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", observe)
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert report["attempted_cases"] == 4 and report["sample_size"] == 2
    assert report["failure_circuit_open"] is False and len(report["skipped"]) == 2


def test_cache_hits_have_separate_counts_and_uncached_latency_sample_size(tmp_path, monkeypatch):
    dataset(tmp_path, count=2)
    observations = iter([observation(), observation(cached=True)])
    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", lambda *a, **k: next(observations))
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert report["sample_size"] == 2
    assert report["fresh_observation_count"] == report["cached_observation_count"] == 1
    assert report["latency_ms"]["sample_size"] == 2
    assert report["uncached_latency_ms"]["sample_size"] == 1


def test_changed_screenshot_is_skipped_without_sending_it(tmp_path, monkeypatch):
    dataset(tmp_path)
    (tmp_path / "screenshots/case-a.png").write_bytes(b"changed pixels")
    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", lambda *a, **k: pytest.fail("Changed dataset sent"))
    report = run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)
    assert report["sample_size"] == 0 and len(report["skipped"]) == 1


def test_bounded_challenge_refuses_more_than_twenty_cases(tmp_path, monkeypatch):
    dataset(tmp_path, count=21)
    monkeypatch.setattr("app.services.nvidia_evaluation.observe_screen", lambda *a, **k: pytest.fail("Unbounded evaluation"))
    with pytest.raises(ValueError, match="twenty"):
        run_nvidia_evaluation(object(), cloud_consent=True, dataset_directory=tmp_path)


def test_report_loader_requires_matching_model_host_manifest_and_cloud_mode(tmp_path):
    dataset(tmp_path)
    report = {**empty_nvidia_report(), "manifest_sha256": manifest_fingerprint((tmp_path / "cases.json").read_bytes())}
    target = tmp_path / "nvidia-results.json"
    target.write_text(json.dumps(report), encoding="utf-8")
    assert load_nvidia_report(dataset_directory=tmp_path)["report_source"] == "checked_in_nvidia_measurement"
    assert "report_source" not in load_nvidia_report(model="other-model", dataset_directory=tmp_path)
    assert "report_source" not in load_nvidia_report(host="https://other.invalid/v1", dataset_directory=tmp_path)
    report["provider_mode"] = "local_ocr"
    target.write_text(json.dumps(report), encoding="utf-8")
    assert "report_source" not in load_nvidia_report(dataset_directory=tmp_path)


def test_api_get_never_calls_cloud_and_post_requires_consent_and_configured_key(tmp_path, monkeypatch):
    app = FastAPI()
    app.state.settings = SimpleNamespace(data_dir=tmp_path, nvidia_api_key="")
    register_evaluation_routes(app)
    monkeypatch.setattr("app.evaluation_api.run_nvidia_evaluation", lambda *a, **k: pytest.fail("Cloud call without consent"))
    with TestClient(app) as client:
        report = client.get("/api/evaluation/nvidia")
        assert report.status_code == 200 and report.json()["provider_mode"] == "nvidia"
        assert client.post("/api/evaluation/nvidia/run", json={"cloud_consent": False}).status_code == 422
        assert client.post("/api/evaluation/nvidia/run", json={"cloud_consent": True}).status_code == 503


def test_api_run_uses_nvidia_adapter_only_after_explicit_consent(tmp_path, monkeypatch):
    app = FastAPI()
    app.state.settings = SimpleNamespace(data_dir=tmp_path, nvidia_api_key="explicit-test-placeholder")
    register_evaluation_routes(app)
    made = []

    class Provider:
        def __init__(self, key, cache_dir, *, base_url, model, timeout_seconds, max_tokens, reasoning_effort):
            assert key == "explicit-test-placeholder" and base_url == DEFAULT_HOST and model == DEFAULT_MODEL
            assert timeout_seconds == 45 and max_tokens == 4096 and reasoning_effort == "low"
            made.append(self)

    fake_module = SimpleNamespace(NvidiaProvider=Provider, NvidiaScreenProvider=lambda provider: provider)
    monkeypatch.setitem(sys.modules, "app.providers.nvidia", fake_module)
    measured = {**empty_nvidia_report(), "sample_size": 1}

    def run(provider, **kwargs):
        assert provider is made[0] and kwargs["cloud_consent"] is True
        return measured

    monkeypatch.setattr("app.evaluation_api.run_nvidia_evaluation", run)
    with TestClient(app) as client:
        response = client.post("/api/evaluation/nvidia/run", json={"cloud_consent": True})
        assert response.status_code == 200 and response.json() == measured
    assert len(made) == 1
