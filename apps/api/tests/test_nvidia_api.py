"""Cloud consent and route integration; every inference uses mocked transport."""

import asyncio
import json

import cv2
import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.digital_schemas import ScreenElement, ScreenObservation, ScreenRule
from app.main import create_app
from app.providers.nvidia import NvidiaProvider
from app.schemas import Step, Task


@pytest.fixture
def environment(tmp_path, monkeypatch):
    from app.providers.nvidia import clear_nvidia_screen_cache

    clear_nvidia_screen_cache()
    calls = []
    state = {"text": "Extensions", "confidence": .99, "status": 200}

    def handler(request):
        payload = json.loads(request.content)
        assert str(request.url) == "https://integrate.api.nvidia.com/v1/chat/completions"
        assert payload["model"] == "meta/muse-glimmer-30b"
        calls.append(payload)
        if state["status"] != 200:
            return httpx.Response(state["status"], json={"error": "private upstream details"})
        if "ReplayLabGroundedExplanation" in payload["messages"][0]["content"]:
            proposed = {"status": "pass", "evidence_ids": ["E1"], "correction_id": None}
        else:
            proposed = {
                "visible_application": "CodeLab", "current_window": state["text"],
                "elements": [{"text": state["text"], "role": "text", "bbox": None, "confidence": state["confidence"]}],
                "missing_information": [],
            }
        return httpx.Response(200, json={"id": "contract-test-response", "model": payload["model"],
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposed)}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    def factory(key, cache_dir, **kwargs):
        return NvidiaProvider(key, cache_dir, client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)

    monkeypatch.setattr("app.providers.nvidia.NvidiaProvider", factory)
    app = create_app(Settings(data_dir=tmp_path, ai_provider="mock", model_api_key="",
                              nvidia_api_key="test-contract-only", screen_nvidia_interval=0))
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda image: ScreenObservation(
        elements=[ScreenElement(text=state["text"], confidence=.99, source="controlled OCR test")],
        visible_text=state["text"], confidence=.99, image_quality=1, provider_mode="local_ocr",
        provenance={"ocr_available": True, "redaction_applied": True},
    ))
    task = Task(id="task", title="Open Extensions", modality="digital", steps=[Step(
        id="open", title="Open Extensions", screen_rules=[ScreenRule(
            id="r1", kind="text_present", expected="Extensions", contradictions=["Preferences"]
        )]
    )])
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "NVIDIA contract test", "modality": "digital"}).json()
        project.update(task=task.model_dump(mode="json"), approved=True, status="ready")
        app.state.store.save_project(project)
        client.post("/api/provider", json={"mode": "nvidia"})
        yield app, client, project, state, calls
    clear_nvidia_screen_cache()


def capture(client, project, consent=True):
    _, image = cv2.imencode(".png", np.full((64, 64, 3), 125, dtype=np.uint8))
    return client.post(f"/api/projects/{project['id']}/screen-check",
        data={"step_id": "open", "cloud_consent": str(consent).lower()},
        files={"file": ("screen.png", image.tobytes(), "image/png")})


@pytest.mark.parametrize("text,confidence,verdict", [
    ("Extensions", .99, "pass"), ("Preferences", .99, "fail"), ("Extensions", None, "uncertain"),
])
def test_nvidia_wire_observations_reach_deterministic_verification(environment, text, confidence, verdict):
    app, client, project, state, calls = environment
    state.update(text=text, confidence=confidence)
    response = capture(client, project)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"]["status"] == verdict
    assert body["result"]["provider_mode"] == "nvidia"
    assert body["verification"]["provider"]["mode"] == "nvidia"
    assert body["observation"]["provenance"]["api_response_validated"] is True
    assert app.state.store.project(project["id"])["completed_step_ids"] == (["open"] if verdict == "pass" else [])
    assert calls and body["screen_stored"] is False
    assert client.get("/api/health").json()["provider"]["live_verified"] is True  # mocked wire contract only


def test_nvidia_requires_distinct_cloud_consent_and_missing_key_never_falls_back(environment):
    app, client, project, _, calls = environment
    assert capture(client, project, consent=False).status_code == 422
    assert calls == []
    app.state.settings.nvidia_api_key = ""
    assert capture(client, project).status_code == 503
    assert calls == []
    assert client.get("/api/health").json()["provider"]["configured"] is False


def test_nvidia_upstream_failure_is_visible_and_does_not_complete(environment):
    app, client, project, state, calls = environment
    state["status"] = 403
    response = capture(client, project)
    assert response.status_code == 502
    assert "private upstream details" not in response.text and len(calls) == 1
    assert app.state.store.project(project["id"])["completed_step_ids"] == []


def test_nvidia_does_not_replace_physical_segmentation(environment):
    _, client, _, _, calls = environment
    physical = client.post("/api/projects/demo").json()
    response = client.post(f"/api/projects/{physical['id']}/extract", json={"cloud_consent": True})
    assert response.status_code == 422 and calls == []


def test_switching_provider_discards_a_multipart_capture_before_any_cloud_request(environment):
    app, client, project, _, calls = environment
    client.post("/api/provider", json={"mode": "mock"})
    _, image = cv2.imencode(".png", np.full((64, 64, 3), 125, dtype=np.uint8))
    payload = image.tobytes()
    boundary = "replaylab-nvidia-consent-boundary"
    prefix = (f'--{boundary}\r\nContent-Disposition: form-data; name="step_id"\r\n\r\nopen\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="cloud_consent"\r\n\r\ntrue\r\n'
              f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="screen.png"\r\nContent-Type: image/png\r\n\r\n').encode()

    async def run():
        started, release = asyncio.Event(), asyncio.Event()

        async def stream():
            yield prefix + payload[:10]
            started.set()
            await release.wait()
            yield payload[10:] + f"\r\n--{boundary}--\r\n".encode()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as transport:
            future = asyncio.create_task(transport.post(f"/api/projects/{project['id']}/screen-check",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, content=stream()))
            await asyncio.wait_for(started.wait(), 5)
            changed = await transport.post("/api/provider", json={"mode": "nvidia"})
            assert changed.status_code == 200
            release.set()
            return await asyncio.wait_for(future, 5)

    response = asyncio.run(run())
    assert response.status_code == 409 and calls == []
    assert app.state.store.project(project["id"])["completed_step_ids"] == []


def test_nvidia_credentials_are_redacted_and_excluded_from_repr(environment):
    from app.services.screen_observation import redact_text

    app, client, _, _, _ = environment
    example = "nvapi-" + "A" * 64
    assert example not in redact_text("key " + example)
    assert "test-contract-only" not in repr(app.state.settings)
    assert "test-contract-only" not in client.get("/api/health").text
