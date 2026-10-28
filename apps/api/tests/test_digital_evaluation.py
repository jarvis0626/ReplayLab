import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.digital_schemas import ScreenObservation, ScreenResult
from app.evaluation_api import register_evaluation_routes
from app.services.digital_evaluation import (
    DATASET_DIRECTORY,
    case_image,
    empty_report,
    load_report,
    manifest_fingerprint,
    run_digital_evaluation,
    summarize_cases,
)


def scored(expected, predicted, latency=1):
    return {"expected": expected, "predicted": predicted, "correct": expected == predicted, "processing_latency_ms": latency}


def test_metrics_measure_false_certainty_swaps_and_abstention_with_denominators():
    report = summarize_cases([
        scored("pass", "pass", 1), scored("pass", "fail", 2),
        scored("fail", "pass", 3), scored("fail", "uncertain", 4),
        scored("uncertain", "uncertain", 5), scored("uncertain", "pass", 6),
    ])
    assert report["accuracy"] == 2 / 6
    assert report["decisive_accuracy"] == 1 / 4
    assert report["decisive_predictions"] == 4
    assert report["false_certainty_rate"] == 1 / 2
    assert report["uncertainty_recall"] == 1 / 2
    assert report["decisive_misclassifications"] == 2
    assert report["latency_ms"]["median"] == 3.5
    assert report["latency_ms"]["p95"] == 6
    assert report["confusion_matrix"]["fail"]["uncertain"] == 1


def test_empty_metrics_are_unknown_instead_of_perfect():
    report = empty_report()
    assert report["sample_size"] == 0
    for metric in ("accuracy", "decisive_accuracy", "false_certainty_rate", "uncertainty_recall"):
        assert report[metric] is None
    assert report["latency_ms"]["median"] is None


def test_report_for_changed_manifest_is_not_shown_as_current(tmp_path, monkeypatch):
    (tmp_path / "cases.json").write_text("{}", encoding="utf-8")
    (tmp_path / "baseline-results.json").write_text(json.dumps({
        "manifest_sha256": "outdated", "sample_size": 20, "accuracy": 1.0,
    }), encoding="utf-8")
    monkeypatch.setattr("app.services.digital_evaluation.DATASET_DIRECTORY", tmp_path)
    report = load_report()
    assert report["sample_size"] == 0 and report["accuracy"] is None
    assert "current case manifest" in report["limitations"][-1]


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_manifest_reports_are_portable_across_git_newline_conversion(tmp_path, monkeypatch, newline):
    unix_payload = b'{\n  "cases": []\n}\n'
    (tmp_path / "cases.json").write_bytes(unix_payload.replace(b"\n", newline))
    (tmp_path / "baseline-results.json").write_text(json.dumps({
        "manifest_sha256": manifest_fingerprint(unix_payload), "sample_size": 20, "accuracy": 1.0,
    }), encoding="utf-8")
    monkeypatch.setattr("app.services.digital_evaluation.DATASET_DIRECTORY", tmp_path)
    report = load_report()
    assert report["sample_size"] == 20
    assert report["report_source"] == "checked_in_measurement"
    assert manifest_fingerprint(unix_payload) == manifest_fingerprint(unix_payload.replace(b"\n", b"\r\n"))


def test_frozen_dataset_has_twenty_pre_labeled_cases_and_actual_images():
    dataset = json.loads((DATASET_DIRECTORY / "cases.json").read_text(encoding="utf-8"))
    plan = json.loads((DATASET_DIRECTORY / "label-plan.json").read_text(encoding="utf-8"))
    assert len(dataset["cases"]) == len(plan) == 20
    for category in ("correct", "incorrect", "ambiguous", "interface_difference"):
        assert sum(case["category"] == category for case in dataset["cases"]) == 5
    assert "not independent human" in dataset["label_provenance"]
    for case in dataset["cases"]:
        assert case["expected"] == next(item["expected"] for item in plan if item["id"] == case["id"])
        image = case_image(case["screenshot"]).read_bytes()
        assert image.startswith(b"\x89PNG")
        assert hashlib.sha256(image).hexdigest() == case["screenshot_sha256"]
        assert "predicted" not in case


@pytest.mark.parametrize("filename", ["../cases.json", "case-secret.jpg", "baseline-results.json", "case-X.png"])
def test_only_controlled_png_filenames_can_be_served(filename):
    with pytest.raises(ValueError):
        case_image(filename)


def small_dataset(tmp_path):
    (tmp_path / "screenshots").mkdir()
    payload = b"controlled image bytes"
    (tmp_path / "screenshots/case-a.png").write_bytes(payload)
    (tmp_path / "workflow.json").write_text(json.dumps({
        "id": "test-workflow", "title": "Test", "modality": "digital", "objects": [],
        "steps": [{"id": "s", "title": "Step", "screen_rules": [{"id": "r", "kind": "text_present", "expected": "Ready"}]}],
    }), encoding="utf-8")
    dataset = {"name": "Test", "label_provenance": "pre-labeled", "cases": [{
        "id": "a", "title": "A", "category": "correct", "expected": "fail",
        "reference_step_id": "s", "completed_step_ids": [], "screenshot": "case-a.png",
        "screenshot_sha256": hashlib.sha256(payload).hexdigest(),
    }]}
    (tmp_path / "cases.json").write_text(json.dumps(dataset), encoding="utf-8")
    return dataset


def test_predictions_do_not_receive_ground_truth_and_disagreements_are_retained(tmp_path, monkeypatch):
    small_dataset(tmp_path)
    seen = []

    def observe(payload, mode):
        assert payload == b"controlled image bytes" and mode == "mock"
        return ScreenObservation(provider_mode="local_ocr", provenance={"real_ocr": True})

    def verify(step, observation, task, completed):
        seen.append((step.id, completed))
        return ScreenResult(step_id=step.id, status="pass", explanation="Observed ready", provider_mode="local_ocr")

    monkeypatch.setattr("app.services.digital_evaluation.observe_screen", observe)
    monkeypatch.setattr("app.services.digital_evaluation.verify_screen", verify)
    report = run_digital_evaluation(dataset_directory=tmp_path)
    assert seen == [("s", [])]
    assert report["details"][0]["predicted"] == "pass"
    assert report["details"][0]["expected"] == "fail"
    assert report["details"][0]["failure_notes"]
    assert report["accuracy"] == 0
    assert report["manifest_sha256"] == manifest_fingerprint((tmp_path / "cases.json").read_bytes())


def test_unavailable_ocr_is_skipped_instead_of_claiming_an_uncertain_prediction(tmp_path, monkeypatch):
    small_dataset(tmp_path)
    monkeypatch.setattr("app.services.digital_evaluation.observe_screen", lambda *a, **k: ScreenObservation())
    report = run_digital_evaluation(dataset_directory=tmp_path)
    assert report["sample_size"] == 0 and len(report["skipped"]) == 1
    assert report["accuracy"] is None


def test_evaluation_routes_return_measurements_and_constrain_assets(tmp_path, monkeypatch):
    app = FastAPI()
    app.state.settings = SimpleNamespace(data_dir=tmp_path)
    register_evaluation_routes(app)
    measured = {**empty_report(), "measured_at": "2026-10-28T00:00:00Z"}
    monkeypatch.setattr("app.evaluation_api.run_digital_evaluation", lambda **kwargs: measured)
    with TestClient(app) as client:
        assert client.get("/api/evaluation/digital").status_code == 200
        assert client.post("/api/evaluation/digital/run").json() == measured
        assert client.get("/api/evaluation/digital/assets/case-correct-market.png").status_code == 200
        assert client.get("/api/evaluation/digital/assets/baseline-results.json").status_code == 404
