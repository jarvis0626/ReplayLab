"""Durable storage, restart recovery, deletion, and bounded media inspection."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api_contracts import Attempt
from app.core.config import Settings
from app.main import create_app, revision
from app.schemas import Rule, Step, Task
from app.services.media import MediaError, inspect_video


def configuration(directory):
    return Settings(data_dir=directory, model_api_key="", ai_provider="mock")


def stored_attempt(project, identifier="a" * 32, status="ready"):
    return Attempt(
        id=identifier,
        project_id=project["id"],
        step_id="first",
        image_url=f"/api/media/{project['id']}/attempt-{identifier}.png",
        created_at="2026-10-26T12:00:00+00:00",
        status=status,
        task_revision=revision(project["task"]),
    ).model_dump(mode="json")


def test_sqlite_project_task_approval_progress_and_attempt_survive_reopen(tmp_path):
    initial = create_app(configuration(tmp_path))
    with TestClient(initial) as client:
        project = client.post("/api/projects", json={"name": "Durable assembly"}).json()
        task = Task(
            id="procedure",
            title="Approved procedure",
            steps=[
                Step(
                    id="first", title="Place red", rules=[Rule(id="present", kind="presence", subject="red")]
                ),
                Step(
                    id="second",
                    title="Continue",
                    dependencies=["first"],
                    rules=[Rule(id="present", kind="presence", subject="blue")],
                ),
            ],
        )
        project.update(
            task=task.model_dump(mode="json"),
            approved=True,
            status="ready",
            completed_step_ids=["first"],
            attempt_count=1,
        )
        initial.state.store.save_project(project)
        attempt = stored_attempt(project)
        initial.state.store.save_attempt(attempt)
        # Detached caller objects cannot modify committed JSON accidentally.
        snapshot = initial.state.store.project(project["id"])
        snapshot["completed_step_ids"].append("second")
        assert initial.state.store.project(project["id"])["completed_step_ids"] == ["first"]

    database = tmp_path / "replaylab.sqlite3"
    assert database.read_bytes()[:16] == b"SQLite format 3\x00"
    reopened = create_app(configuration(tmp_path))
    with TestClient(reopened) as client:
        response = client.get(f"/api/projects/{project['id']}")
        assert response.status_code == 200
        assert response.json() == project
        assert client.get(f"/api/attempts/{attempt['id']}").json() == attempt
        assert client.get(f"/api/projects/{project['id']}/attempts").json() == [attempt]
        graph = client.get(f"/api/projects/{project['id']}/graph").json()
        assert [node["status"] for node in graph["nodes"]] == ["completed", "current"]


def test_startup_recovers_only_interrupted_processing_and_verification(tmp_path):
    initial = create_app(configuration(tmp_path))
    with TestClient(initial) as client:
        active = client.post("/api/projects", json={"name": "Interrupted"}).json()
        idle = client.post("/api/projects", json={"name": "Unaffected"}).json()
        active.update(status="processing", processing={"stage": "extracting", "progress": 45})
        initial.state.store.save_project(active)
        interrupted = stored_attempt(active, status="verifying")
        unaffected = stored_attempt(idle, identifier="b" * 32)
        initial.state.store.save_attempt(interrupted)
        initial.state.store.save_attempt(unaffected)

    restarted = create_app(configuration(tmp_path))
    with TestClient(restarted) as client:
        recovered_project = client.get(f"/api/projects/{active['id']}").json()
        recovered_attempt = client.get(f"/api/attempts/{interrupted['id']}").json()
        assert recovered_project["status"] == "error"
        assert "interrupted" in recovered_project["error"].lower()
        assert recovered_project["approved"] is False
        assert recovered_project["completed_step_ids"] == []
        assert recovered_attempt["status"] == "error"
        assert "interrupted" in recovered_attempt["error"].lower()
        assert recovered_attempt["result"] is None
        assert client.get(f"/api/projects/{idle['id']}").json() == idle
        assert client.get(f"/api/attempts/{unaffected['id']}").json() == unaffected

    # Recovery is persisted, not merely an in-memory response transformation.
    again = create_app(configuration(tmp_path))
    with TestClient(again) as client:
        assert client.get(f"/api/projects/{active['id']}").json()["status"] == "error"
        assert client.get(f"/api/attempts/{interrupted['id']}").json()["status"] == "error"


def test_project_deletion_purges_derived_cache_and_remains_deleted_after_restart(tmp_path):
    application = create_app(configuration(tmp_path))
    with TestClient(application) as client:
        project = client.post("/api/projects", json={"name": "Delete private data"}).json()
        other = client.post("/api/projects", json={"name": "Keep this project"}).json()
        attempt = stored_attempt(project)
        application.state.store.save_attempt(attempt)
        media = tmp_path / "media" / project["id"]
        (media / "private-upload.bin").write_bytes(b"private media")
        other_media = tmp_path / "media" / other["id"] / "keep.bin"
        other_media.write_bytes(b"other project")
        cache = tmp_path / "inference-cache"
        (cache / "nested").mkdir(parents=True)
        (cache / "task.json").write_text(json.dumps({"private": "task proposal"}))
        (cache / "nested" / "observations.json").write_text(json.dumps({"private": "mask geometry"}))
        response = client.delete(f"/api/projects/{project['id']}")
        assert response.status_code == 204, response.text
        assert not media.exists()
        assert not cache.exists()
        assert other_media.read_bytes() == b"other project"
        assert application.state.store.project(project["id"]) is None
        assert application.state.store.attempt(attempt["id"]) is None

    reopened = create_app(configuration(tmp_path))
    with TestClient(reopened) as client:
        assert client.get(f"/api/projects/{project['id']}").status_code == 404
        assert client.get(f"/api/attempts/{attempt['id']}").status_code == 404
        assert client.get(f"/api/projects/{other['id']}").status_code == 200


def probe_result(monkeypatch, *, duration="8.0", width=960, height=640, streams=None):
    document = {
        "format": {"duration": duration},
        "streams": streams
        if streams is not None
        else [{"codec_type": "video", "width": width, "height": height}],
    }
    calls = []

    def fake_probe(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(stdout=json.dumps(document).encode("utf-8"))

    monkeypatch.setattr("app.services.media.subprocess.run", fake_probe)
    return calls


def test_video_metadata_uses_bounded_argument_list_and_accepts_valid_limits(monkeypatch):
    calls = probe_result(monkeypatch, duration="120", width=4096, height=2160)
    path = Path("a path with spaces") / "upload.mp4"
    assert inspect_video(path, 120) == {"duration": 120, "width": 4096, "height": 2160}
    arguments, options = calls[0]
    assert arguments[0] == "ffprobe" and arguments[-1] == str(path)
    assert options["timeout"] == 15 and options["check"] is True
    assert options.get("shell", False) is False


@pytest.mark.parametrize("duration", ["0", "-1", "120.001", "NaN", "Infinity", "-Infinity", "N/A"])
def test_invalid_video_duration_is_rejected_before_frame_extraction(monkeypatch, duration):
    probe_result(monkeypatch, duration=duration)
    with pytest.raises(MediaError):
        inspect_video(Path("uploaded.mp4"), 120)


@pytest.mark.parametrize(
    "width,height", [(31, 640), (960, 31), (4097, 640), (960, 4097), (4096, 4096), (-1, 640)]
)
def test_invalid_video_dimensions_are_rejected_before_frame_extraction(monkeypatch, width, height):
    probe_result(monkeypatch, width=width, height=height)
    with pytest.raises(MediaError, match="dimensions"):
        inspect_video(Path("uploaded.mp4"), 120)


def test_audio_only_upload_is_not_accepted_as_video(monkeypatch):
    probe_result(monkeypatch, streams=[{"codec_type": "audio"}])
    with pytest.raises(MediaError, match="readable video"):
        inspect_video(Path("uploaded.mp4"), 120)
