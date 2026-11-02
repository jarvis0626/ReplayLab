"""Regression checks for observed API evidence and concurrency edge cases."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.mock import MockProvider


@pytest.fixture
def prepared(tmp_path):
    application = create_app(Settings(data_dir=tmp_path, model_api_key="", ai_provider="mock"))
    with TestClient(application) as client:
        response = client.post("/api/projects/demo")
        assert response.status_code == 201, response.text
        project = response.json()
        assert project["status"] == "ready", project
        approval = client.post(f"/api/projects/{project['id']}/approve", json={"approved": True})
        assert approval.status_code == 200
        yield client, project


def checkpoint(client, project):
    image = client.get("/api/demo/fixtures/step-1/image").content
    response = client.post(
        f"/api/projects/{project['id']}/attempts",
        data={"step_id": "step-1"},
        files={"file": ("checkpoint.png", image, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_explicit_incomparable_view_cannot_pass_in_mock_mode(prepared):
    client, project = prepared
    attempt = checkpoint(client, project)
    response = client.post(f"/api/attempts/{attempt['id']}/verify", json={"comparable": False})
    assert response.status_code == 200, response.text
    assert response.json()["result"]["status"] == "uncertain"


def test_corrupt_checkpoint_does_not_leave_a_saved_attempt_or_media(prepared):
    client, project = prepared
    response = client.post(
        f"/api/projects/{project['id']}/attempts",
        data={"step_id": "step-1"},
        files={"file": ("image.png", b"not-an-image", "image/png")},
    )
    assert response.status_code == 422
    assert client.get(f"/api/projects/{project['id']}/attempts").json() == []
    media_directory = client.app.state.settings.data_dir / "media" / project["id"]
    assert not list(media_directory.glob("attempt-*.png"))
    assert client.get(f"/api/projects/{project['id']}").json()["attempt_count"] == 0


def test_concurrent_task_edit_does_not_return_a_stale_verdict(prepared, monkeypatch):
    client, project = prepared
    attempt = checkpoint(client, project)
    observation_started = threading.Event()
    release_observation = threading.Event()
    original = MockProvider.observe

    def controlled_observe(self, path, prompts):
        if not observation_started.is_set():
            observation_started.set()
            assert release_observation.wait(30), "Test did not release the provider."
        return original(self, path, prompts)

    monkeypatch.setattr(MockProvider, "observe", controlled_observe)
    with ThreadPoolExecutor(max_workers=2) as executor:
        verifying = executor.submit(client.post, f"/api/attempts/{attempt['id']}/verify", json={})
        try:
            assert observation_started.wait(10)
            editing = executor.submit(
                client.patch,
                f"/api/projects/{project['id']}/steps/step-1",
                json={"title": "Changed during verification"},
            )
            # Confirm the edit actually committed before inference can finish;
            # scheduler timing must not choose this test's expected response.
            edit_response = editing.result(timeout=15)
            assert edit_response.status_code == 200, edit_response.text
        finally:
            release_observation.set()
        verification_response = verifying.result(timeout=15)
    assert verification_response.status_code == 409, verification_response.text
    saved_attempt = client.get(f"/api/attempts/{attempt['id']}").json()
    assert saved_attempt["result"] is None and saved_attempt["verification"] is None
    assert client.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == []
    assert client.get(f"/api/projects/{project['id']}/verifications").json() == []
