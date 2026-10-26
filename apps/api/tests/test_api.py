from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    application = create_app(Settings(data_dir=tmp_path, model_api_key="", ai_provider="mock"))
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def demo(client):
    response = client.post("/api/projects/demo")
    assert response.status_code == 201, response.text
    project = response.json()
    assert project["status"] == "ready", project
    return project


def upload_checkpoint(client, project, step_id, fixture):
    image = client.get(f"/api/demo/fixtures/{fixture}/image").content
    return client.post(
        f"/api/projects/{project['id']}/attempts",
        data={"step_id": step_id},
        files={"file": ("arbitrary-name.png", image, "image/png")},
    )


def test_health_project_persistence_and_private_local_contract(client):
    health = client.get("/api/health").json()
    assert health["provider"]["mode"] == "mock"
    assert "MODEL_API_KEY" not in str(health)
    assert client.post("/api/projects", json={"name": "  "}).status_code == 422
    created = client.post("/api/projects", json={"name": "Assembly"}).json()
    assert client.get(f"/api/projects/{created['id']}").json()["name"] == "Assembly"
    assert len(client.get("/api/projects").json()) == 1


def test_real_demo_frames_video_and_graph(client, demo):
    assert len(demo["frames"]) == 4
    assert demo["video"]["duration"] == pytest.approx(8, abs=0.2)
    media = client.get(demo["video"]["url"])
    assert media.status_code == 200
    assert media.headers["content-type"] == "video/mp4"
    assert media.headers["x-content-type-options"] == "nosniff"
    assert client.get(demo["frames"][0]["url"]).headers["content-type"] == "image/png"
    graph = client.get(f"/api/projects/{demo['id']}/graph").json()
    assert graph["order"] == ["step-1", "step-2", "step-3", "step-4"]
    assert graph["nodes"][0]["status"] == "current"
    assert demo["task"]["provenance"]["inferred_from_video"] is False


def test_full_demo_verification_and_dependency_progression(client, demo):
    assert upload_checkpoint(client, demo, "step-1", "step-1").status_code == 409
    assert client.post(f"/api/projects/{demo['id']}/approve", json={"approved": True}).status_code == 200
    assert upload_checkpoint(client, demo, "step-2", "step-2").status_code == 409
    for number, fixture in enumerate(["step-1", "step-2", "step-3", "complete"], 1):
        uploaded = upload_checkpoint(client, demo, f"step-{number}", fixture)
        assert uploaded.status_code == 201, uploaded.text
        attempt = uploaded.json()
        response = client.post(f"/api/attempts/{attempt['id']}/verify", json={})
        assert response.status_code == 200, response.text
        assert response.json()["result"]["status"] == "pass", response.json()
    finished = client.get(f"/api/projects/{demo['id']}").json()
    assert finished["completed_step_ids"] == ["step-1", "step-2", "step-3", "step-4"]
    assert len(client.get(f"/api/projects/{demo['id']}/attempts").json()) == 4


def test_real_mismatch_and_obstruction_are_distinct(client, demo):
    client.post(f"/api/projects/{demo['id']}/approve", json={"approved": True})
    first = upload_checkpoint(client, demo, "step-1", "step-1").json()
    client.post(f"/api/attempts/{first['id']}/verify", json={})
    wrong = upload_checkpoint(client, demo, "step-2", "blue-right").json()
    failed = client.post(f"/api/attempts/{wrong['id']}/verify", json={}).json()
    assert failed["result"]["status"] == "fail"
    assert "align" in failed["result"]["explanation"].lower()
    partial = upload_checkpoint(client, demo, "step-2", "partial").json()
    uncertain = client.post(f"/api/attempts/{partial['id']}/verify", json={}).json()
    assert uncertain["result"]["status"] == "uncertain"
    assert client.get(f"/api/projects/{demo['id']}").json()["completed_step_ids"] == ["step-1"]


def test_unknown_image_is_not_live_segmentation(client, demo):
    client.post(f"/api/projects/{demo['id']}/approve", json={"approved": True})
    _, content = cv2.imencode(".png", np.full((100, 100, 3), 120, np.uint8))
    uploaded = client.post(
        f"/api/projects/{demo['id']}/attempts",
        data={"step_id": "step-1"},
        files={"file": ("complete.png", content.tobytes(), "image/png")},
    ).json()
    result = client.post(f"/api/attempts/{uploaded['id']}/verify", json={}).json()["result"]
    assert result["status"] == "uncertain"
    assert result["observations"] == []


def test_step_edits_invalidate_approval_and_old_attempts(client, demo):
    client.post(f"/api/projects/{demo['id']}/approve", json={"approved": True})
    old = upload_checkpoint(client, demo, "step-1", "step-1").json()
    updated = client.patch(f"/api/projects/{demo['id']}/steps/step-1", json={"title": "Edited title"})
    assert updated.status_code == 200
    assert updated.json()["approved"] is False
    client.post(f"/api/projects/{demo['id']}/approve", json={"approved": True})
    assert client.post(f"/api/attempts/{old['id']}/verify", json={}).status_code == 409
    assert (
        client.patch(
            f"/api/projects/{demo['id']}/steps/step-1", json={"dependencies": ["step-4"]}
        ).status_code
        == 422
    )


def test_corrupt_video_mime_and_traversal(client):
    project = client.post("/api/projects", json={"name": "Upload validation"}).json()
    url = f"/api/projects/{project['id']}/video"
    assert client.post(url, files={"file": ("video.txt", b"not video", "text/plain")}).status_code == 415
    response = client.post(url, files={"file": ("../../escape.mp4", b"not video", "video/mp4")})
    assert response.status_code == 202
    assert client.get(f"/api/projects/{project['id']}").json()["status"] == "error"
    assert client.get(f"/api/media/{project['id']}/manifest.json").status_code == 404
    assert client.get("/api/projects/not-a-safe-id").status_code == 404
    assert client.get("/api/demo/fixtures/unknown/image").status_code == 404


def test_upload_limit_and_corrupt_image(tmp_path):
    app = create_app(Settings(data_dir=tmp_path, max_video_bytes=16, max_image_bytes=8))
    with TestClient(app) as client:
        project = client.post("/api/projects", json={"name": "Limits"}).json()
        assert (
            client.post(
                f"/api/projects/{project['id']}/video", files={"file": ("v.mp4", b"x" * 17, "video/mp4")}
            ).status_code
            == 413
        )


def test_meta_consent_and_missing_credential_do_not_silently_mock(client, demo):
    response = client.post("/api/provider", json={"mode": "meta"})
    assert response.json()["provider"]["configured"] is False
    url = f"/api/projects/{demo['id']}/extract"
    assert client.post(url, json={}).status_code == 422
    assert client.post(url, json={"cloud_consent": True}).status_code == 503
    assert client.get("/api/health").json()["provider"]["mode"] == "meta"


def test_evaluation_is_measured_and_deletion_removes_media(client, demo):
    evaluation = client.get(f"/api/projects/{demo['id']}/evaluation").json()
    assert evaluation["sample_size"] >= 12
    assert evaluation["correct"] == evaluation["sample_size"]
    assert evaluation["provider_mode"] == "mock"
    media_url = demo["frames"][0]["url"]
    assert client.delete(f"/api/projects/{demo['id']}").status_code == 204
    assert client.get(media_url).status_code == 404
    assert not (Path(client.app.state.settings.data_dir) / "media" / demo["id"]).exists()


def test_valid_upload_uses_real_frames_and_mock_extraction(client, demo):
    project = client.post("/api/projects", json={"name": "Uploaded demo"}).json()
    video = client.get(demo["video"]["url"]).content
    assert (
        client.post(
            f"/api/projects/{project['id']}/video", files={"file": ("../demo.mp4", video, "video/mp4")}
        ).status_code
        == 202
    )
    ready = client.get(f"/api/projects/{project['id']}").json()
    assert ready["status"] == "ready"
    assert ready["video"]["original_name"] == "demo.mp4"
    assert len(ready["frames"]) == 4
    assert client.post(f"/api/projects/{project['id']}/extract", json={}).status_code == 202
    extracted = client.get(f"/api/projects/{project['id']}").json()
    assert extracted["task"]["provider_mode"] == "mock"
    assert extracted["approved"] is False
