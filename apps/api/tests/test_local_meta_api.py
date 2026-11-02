"""Local Meta route contracts; OCR and model transport are controlled fixtures."""

import json

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.digital_schemas import ScreenElement, ScreenObservation, ScreenRule
from app.main import create_app
from app.providers.local_meta import LocalMetaProvider
from app.schemas import Step, Task


@pytest.fixture
def local_environment(tmp_path, monkeypatch):
    calls = []
    state = {"text": "Extensions", "confidence": .99, "status": 200}

    def handler(request):
        assert request.url.host == "127.0.0.1"
        assert "authorization" not in request.headers
        payload = json.loads(request.content)
        calls.append(payload)
        assert all(isinstance(message["content"], str) for message in payload["messages"])
        if state["status"] != 200:
            return httpx.Response(state["status"], json={"private": "UPSTREAM DETAILS"})
        properties = payload["response_format"]["json_schema"]["schema"]["properties"]
        if "status" in properties:
            data = json.loads(payload["messages"][1]["content"])
            proposed = {"status": data["status"], "evidence_ids": ["E1"], "correction_id": None}
        else:
            proposed = {"evidence_ids": ["O1"],
                        "visible_application_id": None, "current_window_id": None}
        return httpx.Response(200, json={"id": "local-contract-only", "model": payload["model"],
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposed)}}]})

    def factory(cache_dir, **kwargs):
        return LocalMetaProvider(cache_dir, client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)

    monkeypatch.setattr("app.providers.local_meta.LocalMetaProvider", factory)
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda image: ScreenObservation(
        elements=[ScreenElement(text=state["text"], confidence=state["confidence"], source="controlled OCR")],
        visible_text=state["text"], confidence=state["confidence"], image_quality=1,
        provider_mode="local_ocr", provenance={"ocr_available": True, "redaction_applied": True},
    ))
    app = create_app(Settings(data_dir=tmp_path, ai_provider="local_meta", model_api_key="",
                              nvidia_api_key="", screen_local_meta_interval=0))
    task = Task(id="local-task", title="Open Extensions", modality="digital", steps=[Step(
        id="open", title="Open Extensions", screen_rules=[ScreenRule(
            id="rule", kind="text_present", expected="Extensions", contradictions=["Preferences"],
        )],
    )])
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Local Meta route test", "modality": "digital"}).json()
        project.update(task=task.model_dump(mode="json"), approved=True, status="ready")
        app.state.store.save_project(project)
        yield app, client, project, state, calls


def screen_check(client, project):
    _, image = cv2.imencode(".png", np.full((64, 64, 3), 125, dtype=np.uint8))
    return client.post(f"/api/projects/{project['id']}/screen-check",
        data={"step_id": "open", "cloud_consent": "false"},
        files={"file": ("controlled.png", image.tobytes(), "image/png")})


@pytest.mark.parametrize("text,confidence,verdict", [
    ("Extensions", .99, "pass"), ("Preferences", .99, "fail"), ("Extensions", None, "uncertain"),
])
def test_local_meta_uses_no_cloud_key_or_consent_and_preserves_verdict(local_environment, text, confidence, verdict):
    app, client, project, state, calls = local_environment
    state.update(text=text, confidence=confidence)
    before = client.get("/api/health").json()["provider"]
    assert before["mode"] == "local_meta" and before["live_verified"] is False
    response = screen_check(client, project)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"]["status"] == verdict
    assert body["observation"]["provider_mode"] == "local_meta"
    assert body["observation"]["provenance"]["vision_inference"] is False
    assert body["observation"]["provenance"]["local_only"] is True
    assert body["verification"]["provider"]["mode"] == "local_meta"
    assert app.state.store.project(project["id"])["completed_step_ids"] == (["open"] if verdict == "pass" else [])
    assert calls and body["screen_stored"] is False
    assert client.get("/api/health").json()["provider"]["live_verified"] is True


def test_local_meta_failure_never_falls_back_to_ocr_or_advances(local_environment):
    app, client, project, state, calls = local_environment
    state["status"] = 503
    response = screen_check(client, project)
    assert response.status_code == 502
    assert "UPSTREAM DETAILS" not in response.text and len(calls) == 1
    assert app.state.store.project(project["id"])["completed_step_ids"] == []
    assert client.get("/api/health").json()["provider"]["mode"] == "local_meta"


def test_local_meta_is_selectable_but_does_not_supply_physical_segmentation(local_environment):
    _, client, _, _, calls = local_environment
    assert client.post("/api/provider", json={"mode": "mock"}).status_code == 200
    response = client.post("/api/provider", json={"mode": "local_meta"})
    assert response.status_code == 200 and response.json()["provider"]["physical_supported"] is False
    physical = client.post("/api/projects/demo").json()
    response = client.post(f"/api/projects/{physical['id']}/extract", json={"cloud_consent": False})
    assert response.status_code == 422 and calls == []
