"""Shared evidence contracts, opt-in retention, correction reports, and gates."""

import asyncio
import copy
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.core.config import Settings
from app.digital_schemas import ScreenElement, ScreenObservation, ScreenRule
from app.main import create_app
from app.schemas import Observation, ObservationSet, Rule, Step, Task
from app.services.digital_verification import verify_screen
from app.services.thresholds import configured_thresholds
from app.services.verification import verify
from app.services.verification_records import build_verification
from app.verification_contracts import WorkflowVerification


def observed(*texts, version="CodeLab 1.0", confidence=0.95, quality=1.0):
    return ScreenObservation(
        elements=[ScreenElement(text=text, confidence=confidence, source="controlled test evidence")
                  for text in texts],
        visible_text="\n".join(texts), confidence=confidence, image_quality=quality,
        interface_version=version, provider_mode="local_ocr",
    )


@pytest.fixture
def environment(tmp_path, monkeypatch):
    app = create_app(Settings(data_dir=tmp_path, model_api_key="", ai_provider="mock",
                              screen_local_interval=0))
    step = Step(id="open", title="Open extensions", expected_state="Extensions panel is visible",
                screen_rules=[ScreenRule(id="panel", kind="text_present", expected="Extensions",
                                         contradictions=["Preferences"])])
    task = Task(id="tutorial", title="Controlled UI workflow", modality="digital",
                interface_version="CodeLab 1.0", steps=[step])
    monkeypatch.setattr("app.services.screen_observation.observe_screen",
                        lambda *args, **kwargs: observed("Extensions", "private@example.com"))
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Digital", "modality": "digital"}).json()
        project.update(task=task.model_dump(mode="json"), approved=True, status="ready")
        app.state.store.save_project(project)
        yield app, client, project, task


def capture(client, project, **fields):
    _, image = cv2.imencode(".png", np.full((64, 64, 3), 120, dtype=np.uint8))
    return client.post(f"/api/projects/{project['id']}/screen-check",
                       data={"step_id": "open", **fields},
                       files={"file": ("visible.png", image.tobytes(), "image/png")})


def test_digital_verification_defaults_to_transient_and_feedback_never_changes_verdict(environment):
    app, client, project, _ = environment
    response = capture(client, project)
    assert response.status_code == 200, response.text
    record = WorkflowVerification.model_validate(response.json()["verification"])
    assert record.verdict == "pass" and record.modality == "digital"
    assert record.expected_conditions == ["Extensions"]
    assert record.provider.observation == "local_ocr" and record.provider.mode == "mock"
    assert record.latency_ms >= 0 and record.retained is False
    assert record.evidence_references and record.constraints[0].verdict == "pass"
    assert "private@example.com" not in record.model_dump_json()
    assert client.get(f"/api/projects/{project['id']}/verifications").json() == []
    report = client.post(f"/api/projects/{project['id']}/verifications/{record.id}/feedback",
                         json={"expected_verdict": "uncertain", "notes": "Contact private@example.com"})
    assert report.status_code == 201, report.text
    assert "private@example.com" not in report.text
    assert app.state.store.project(project["id"])["completed_step_ids"] == ["open"]
    # Re-reporting updates this report rather than multiplying rows.
    updated = client.post(f"/api/projects/{project['id']}/verifications/{record.id}/feedback",
                          json={"expected_verdict": "fail", "notes": "Correction"})
    assert updated.json()["id"] == report.json()["id"]
    assert len(app.state.store.feedback(project["id"])) == 1
    client.post(f"/api/projects/{project['id']}/screen-session/clear")
    assert client.post(f"/api/projects/{project['id']}/verifications/{record.id}/feedback",
                       json={"expected_verdict": "fail"}).status_code == 404


def test_retention_is_explicit_cache_distinct_and_survives_stop_and_restart(environment, tmp_path):
    app, client, project, _ = environment
    transient = capture(client, project).json()["verification"]
    retained = capture(client, project, retain_evidence=True).json()["verification"]
    assert retained["id"] != transient["id"] and retained["retained"] is True
    assert capture(client, project, retain_evidence=True).json()["verification"]["id"] == retained["id"]
    again_transient = capture(client, project, retain_evidence=False).json()["verification"]
    assert again_transient["id"] != retained["id"] and again_transient["retained"] is False
    client.post(f"/api/projects/{project['id']}/screen-session/clear")
    assert client.get(f"/api/projects/{project['id']}/verifications").json() == [retained]
    reopened = create_app(Settings(data_dir=tmp_path, ai_provider="mock", model_api_key=""))
    with TestClient(reopened) as second:
        assert second.get(f"/api/projects/{project['id']}/verifications").json() == [retained]
    assert not any("screen" in path.name or "capture" in path.name
                   for path in (tmp_path / "media" / project["id"]).iterdir())


def test_feedback_cannot_cross_projects_and_deletion_removes_retained_evidence(environment):
    app, client, project, _ = environment
    record = capture(client, project, retain_evidence=True).json()["verification"]
    other = client.post("/api/projects", json={"name": "Other"}).json()
    route = f"/api/projects/{other['id']}/verifications/{record['id']}/feedback"
    assert client.post(route, json={"expected_verdict": "fail"}).status_code == 404
    route = f"/api/projects/{project['id']}/verifications/{record['id']}/feedback"
    assert client.post(route, json={"expected_verdict": "fail"}).status_code == 201
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    assert app.state.store.verifications(project["id"]) == []
    assert app.state.store.feedback(project["id"]) == []


def test_stop_discards_an_inflight_capture_before_any_retained_history_or_completion(environment, monkeypatch):
    _, client, project, _ = environment
    entered, release = threading.Event(), threading.Event()

    def delayed_observation(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return observed("Extensions")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", delayed_observation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(capture, client, project, retain_evidence=True)
        assert entered.wait(5)
        try:
            assert client.post(f"/api/projects/{project['id']}/screen-session/clear").status_code == 204
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 409
    assert client.get(f"/api/projects/{project['id']}/verifications").json() == []
    assert client.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == []


@pytest.mark.parametrize("mode", ["mock", "meta"])
def test_stop_during_upload_read_never_observes_or_completes_the_stopped_capture(environment, monkeypatch, mode):
    app, client, project, _ = environment
    entered, release = threading.Event(), threading.Event()
    original_read = UploadFile.read

    async def delayed_read(file, *args, **kwargs):
        entered.set()
        while not release.is_set():
            await asyncio.sleep(0.01)
        return await original_read(file, *args, **kwargs)

    def forbidden_observation(*args, **kwargs):
        raise AssertionError("A stopped upload must not start local or cloud observation.")

    def forbidden_explanation(*args, **kwargs):
        raise AssertionError("A stopped upload must not start cloud explanation.")

    app.state.settings.model_api_key = "test-stop-race-not-a-real-credential"
    client.post("/api/provider", json={"mode": mode})
    monkeypatch.setattr(UploadFile, "read", delayed_read)
    monkeypatch.setattr("app.services.screen_observation.observe_screen", forbidden_observation)
    monkeypatch.setattr("app.providers.grounded_explanation.explain_verification", forbidden_explanation)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(capture, client, project, retain_evidence=True, cloud_consent=True)
        assert entered.wait(5)
        try:
            assert client.post(f"/api/projects/{project['id']}/screen-session/clear").status_code == 204
        finally:
            release.set()
        response = pending.result(timeout=5)
    assert response.status_code == 409, response.text
    assert client.get(f"/api/projects/{project['id']}/verifications").json() == []
    assert client.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == []
    assert app.state.screen_sessions.last(project["id"]) is None


def test_stop_during_real_streamed_multipart_receipt_discards_capture_before_route_entry(environment, monkeypatch):
    app, _, project, _ = environment

    def forbidden_observation(*args, **kwargs):
        raise AssertionError("A stopped multipart upload must never start observation.")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", forbidden_observation)
    _, image = cv2.imencode(".png", np.full((64, 64, 3), 120, dtype=np.uint8))
    boundary = "ReplayLabStreamedRegression"
    prefix = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="step_id"\r\n\r\nopen\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="retain_evidence"\r\n\r\ntrue\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="screen.png"\r\n'
        'Content-Type: image/png\r\n\r\n'
    ).encode()

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def body():
            yield prefix + image.tobytes()[:10]
            entered.set()
            await release.wait()
            yield image.tobytes()[10:] + f"\r\n--{boundary}--\r\n".encode()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            pending = asyncio.create_task(client.post(
                f"/api/projects/{project['id']}/screen-check", content=body(),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            ))
            await asyncio.wait_for(entered.wait(), timeout=5)
            try:
                stopped = await client.post(f"/api/projects/{project['id']}/screen-session/clear")
                assert stopped.status_code == 204
            finally:
                release.set()
            response = await asyncio.wait_for(pending, timeout=5)
            assert response.status_code == 409, response.text

    asyncio.run(scenario())
    assert app.state.store.verifications(project["id"]) == []
    assert app.state.store.project(project["id"])["completed_step_ids"] == []
    assert app.state.screen_sessions.last(project["id"]) is None


def test_unified_workflow_view_preserves_graph_progress_and_marks_revision(environment):
    app, client, project, _ = environment
    record = capture(client, project, retain_evidence=True).json()["verification"]
    view = client.get(f"/api/projects/{project['id']}/workflow").json()
    assert view["task"]["modality"] == "digital" and view["order"] == ["open"]
    assert view["steps"][0]["progression"] == "completed"
    assert view["steps"][0]["latest_verification"] == record
    edited = copy.deepcopy(project["task"])
    edited["steps"][0]["expected_state"] = "Reviewed revised expectation"
    saved = client.put(f"/api/projects/{project['id']}/task", json=edited)
    assert saved.status_code == 200, saved.text
    revised = client.get(f"/api/projects/{project['id']}/workflow").json()
    assert revised["steps"][0]["latest_verification"] is None
    assert revised["steps"][0]["progression"] == "current"
    assert len(app.state.store.verifications(project["id"])) == 1


@pytest.mark.parametrize("observation,expected", [
    (observed("Extensions", version="CodeLab 2.0"), "confirmed_version_mismatch"),
    (observed("Unrelated application"), "expected_ui_not_found"),
    (observed("Preferences"), "unexpected_ui_state"),
    (observed("Extensions", quality=0.1), "insufficient_visual_evidence"),
])
def test_mismatch_classification_comes_from_visible_evidence(environment, observation, expected):
    _, _, project, task = environment
    result = verify_screen(task.steps[0], observation, task)
    record = build_verification(project, task, task.steps[0], result,
                                task_revision="r", latency_ms=2, observation=observation)
    assert record.mismatch_classification == expected
    if "version" in expected:
        assert record.verdict == "uncertain"


def test_conflicting_visible_versions_are_possible_not_confirmed(environment):
    _, _, project, task = environment
    observation = observed("CodeLab 1.0", "CodeLab 2.0", version=None)
    observation.provenance["interface_version_ambiguous"] = True
    result = verify_screen(task.steps[0], observation, task)
    record = build_verification(project, task, task.steps[0], result,
                                task_revision="r", latency_ms=2, observation=observation)
    assert record.mismatch_classification == "possible_version_mismatch"
    assert record.verdict == "uncertain"


def test_unreliable_version_text_is_insufficient_evidence_not_a_confirmed_mismatch(environment):
    _, _, project, task = environment
    observation = observed("Extensions", version="CodeLab 2.0", confidence=0.2)
    result = verify_screen(task.steps[0], observation, task)
    record = build_verification(project, task, task.steps[0], result,
                                task_revision="r", latency_ms=2, observation=observation)
    assert record.mismatch_classification == "insufficient_visual_evidence"
    assert result.reason == "insufficient_evidence"
    assert record.constraints[0].verdict == "uncertain"
    assert record.verdict == "uncertain"


def test_api_uses_configured_confidence_gate_and_never_completes_strict_uncertainty(environment):
    app, client, project, _ = environment
    app.state.settings.verification_min_confidence = 0.99
    response = capture(client, project)
    assert response.status_code == 200, response.text
    assert response.json()["verification"]["verdict"] == "uncertain"
    assert response.json()["completed_step_ids"] == []


def test_threshold_overrides_are_request_scoped_and_apply_to_both_modalities():
    digital = Step(id="d", title="Panel", screen_rules=[ScreenRule(id="s", kind="text_present", expected="Extensions")])
    physical = Step(id="p", title="Block", rules=[Rule(id="p", kind="presence", subject="red")])
    scene = ObservationSet(observations=[Observation(label="red", bbox=(0, 0, 1, 1), confidence=0.8)],
                           visibility=1, coverage=1, comparable=True, image_quality=1)

    def run(threshold):
        settings = Settings(verification_min_confidence=threshold)
        with configured_thresholds(settings):
            return (verify_screen(digital, observed("Extensions", confidence=0.8)).status,
                    verify(physical, scene, scene).status)

    with ThreadPoolExecutor(max_workers=2) as pool:
        strict, ordinary = list(pool.map(run, [0.9, 0.75]))
    assert strict == ("uncertain", "uncertain") and ordinary == ("pass", "pass")
    assert verify_screen(digital, observed("Extensions", confidence=0.8)).status == "pass"


def test_history_limit_retains_newest_hundred_records(environment):
    app, _, project, task = environment
    result = verify_screen(task.steps[0], observed("Extensions"), task)
    template = build_verification(project, task, task.steps[0], result,
                                  task_revision="r", latency_ms=1, retained=True).model_dump(mode="json")
    for index in range(103):
        document = {**template, "id": f"record-{index}",
                    "created_at": datetime.fromtimestamp(1000 + index, timezone.utc).isoformat()}
        app.state.store.save_verification(document)
    records = app.state.store.verifications(project["id"])
    assert len(records) == 100 and records[0]["id"] == "record-102"
    assert records[-1]["id"] == "record-3"
