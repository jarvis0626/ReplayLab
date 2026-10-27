"""Digital API integration with actual OCR once and controlled evidence elsewhere."""

from __future__ import annotations

import copy
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.digital_schemas import ScreenElement, ScreenObservation
from app.main import create_app
from app.providers.meta import ProviderError
from app.services.digital_demo import ensure_digital_demo


@pytest.fixture(scope="module")
def digital_assets(tmp_path_factory):
    directory = tmp_path_factory.mktemp("digital-api-assets") / "digital-demo"
    ensure_digital_demo(directory)
    return directory


@pytest.fixture
def digital_client(tmp_path, digital_assets):
    shutil.copytree(digital_assets, tmp_path / "digital-demo")
    app = create_app(
        Settings(
            data_dir=tmp_path,
            ai_provider="mock",
            model_api_key="",
            screen_local_interval=0,
            screen_meta_interval=0,
        )
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def digital_project(digital_client):
    response = digital_client.post("/api/projects/digital-demo")
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, project):
    response = client.post(f"/api/projects/{project['id']}/approve", json={"approved": True})
    assert response.status_code == 200, response.text


def capture(client, project, *, index=0, content=None, **data):
    if content is None:
        content = client.get(project["frames"][index]["url"]).content
    return client.post(
        f"/api/projects/{project['id']}/screen-check",
        data={
            "step_id": project["task"]["steps"][index]["id"],
            "source_scope": "Synthetic CodeLab window",
            **data,
        },
        files={"file": ("screen.png", content, "image/png")},
    )


def evidence(*texts, quality=1.0, version="CodeLab 1.0", role="text"):
    return ScreenObservation(
        elements=[
            ScreenElement(text=text, confidence=0.99, role=role, source="explicit test observation")
            for text in texts
        ],
        visible_text="\n".join(texts),
        confidence=0.99,
        image_quality=quality,
        interface_version=version,
        provider_mode="local_ocr",
        provenance={"fixture": True, "screenshots_stored": False},
    )


@pytest.mark.parametrize("mutation", ["identical_task_save", "approval_toggle"])
def test_review_changes_discard_cached_screen_and_ask_evidence(
    digital_client, digital_project, monkeypatch, mutation
):
    client, project = digital_client, digital_project
    # Set user_edited before the first capture so the later identical save has
    # the same revision; revision comparison alone cannot invalidate it.
    task = client.put(f"/api/projects/{project['id']}/task", json=project["task"]).json()["task"]
    approve(client, project)
    calls = []

    def observe(*args, **kwargs):
        calls.append(1)
        return evidence("Extensions Marketplace")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", observe)
    assert capture(client, project).json()["result"]["status"] == "pass"
    assert client.app.state.screen_sessions.last(project["id"]) is not None
    if mutation == "identical_task_save":
        assert client.put(f"/api/projects/{project['id']}/task", json=task).status_code == 200
    else:
        assert (
            client.post(f"/api/projects/{project['id']}/approve", json={"approved": False}).status_code == 200
        )
    approve(client, project)
    assert client.app.state.screen_sessions.last(project["id"]) is None
    answer = client.post(f"/api/projects/{project['id']}/ask", json={"question": "What is visible?"}).json()
    assert answer["evidence"] == []
    assert "do not have a current screen" in answer["answer"]
    assert capture(client, project).json()["result"]["status"] == "pass"
    assert len(calls) == 2


def test_digital_demo_approval_and_four_actual_ocr_checkpoints(digital_client, digital_project):
    client, project = digital_client, digital_project
    assert project["modality"] == project["task"]["modality"] == "digital"
    assert project["task"]["provider_mode"] == "mock"
    assert project["task"]["provenance"]["inferred_from_video"] is False
    assert project["video"]["duration"] == pytest.approx(12, abs=0.1)
    assert capture(client, project).status_code == 409
    approve(client, project)
    before = {
        path.relative_to(client.app.state.settings.data_dir)
        for path in client.app.state.settings.data_dir.rglob("*")
        if path.is_file()
    }
    for index in range(4):
        response = capture(client, project, index=index)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["screen_stored"] is False
        assert payload["source_scope"] == "Synthetic CodeLab window"
        assert payload["observation"]["provenance"]["real_ocr"] is True
        assert payload["result"]["status"] == "pass", payload
        assert len(payload["completed_step_ids"]) == index + 1
    final = client.get(f"/api/projects/{project['id']}").json()
    assert final["completed_step_ids"] == [f"digital-step-{index}" for index in range(1, 5)]
    coaching = client.post(f"/api/projects/{project['id']}/ask", json={"question": "What next?"}).json()
    assert "All approved checkpoints are verified" in coaching["answer"]
    assert "no next eligible step" in coaching["answer"]
    assert client.get(f"/api/projects/{project['id']}/attempts").json() == []
    after = {
        path.relative_to(client.app.state.settings.data_dir)
        for path in client.app.state.settings.data_dir.rglob("*")
        if path.is_file()
    }
    assert before == after, "Screen capture bytes must not create files or attempt images"


@pytest.mark.parametrize(
    "body",
    [
        {"transcript": '[00:00] Open "Extensions"'},
        {"youtube_url": "https://youtu.be/dQw4w9WgXcQ", "transcript": '[00:00] Open "Extensions"'},
    ],
)
def test_tutorial_sources_require_explicit_usage_rights(digital_client, body):
    project = digital_client.post("/api/projects", json={"name": "Source test", "modality": "digital"}).json()
    response = digital_client.post(f"/api/projects/{project['id']}/tutorial", json=body)
    assert response.status_code == 422


def test_timestamped_youtube_reference_and_transcript_extract_without_network(digital_client, monkeypatch):
    def no_http(*args, **kwargs):
        raise AssertionError("Offline transcript ingestion must not contact an external provider")

    monkeypatch.setattr("app.providers.meta.MetaProvider._request", no_http)
    client = digital_client
    project = client.post("/api/projects", json={"name": "User transcript", "modality": "digital"}).json()
    saved = client.post(
        f"/api/projects/{project['id']}/tutorial",
        json={
            "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
            "title": "User-supplied title",
            "transcript": '[00:00] Open "Extensions Marketplace".\n[00:12] Search for "Replay Formatter".',
            "usage_rights_confirmed": True,
        },
    )
    assert saved.status_code == 200, saved.text
    source = saved.json()["tutorial"]
    assert source["content_fetched"] is False
    assert source["embed_url"] == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
    assert source["title_source"] == "user-provided, unverified"
    extracted = client.post(f"/api/projects/{project['id']}/extract", json={})
    assert extracted.status_code == 202, extracted.text
    ready = client.get(f"/api/projects/{project['id']}").json()
    assert ready["approved"] is False and ready["task"]["modality"] == "digital"
    assert ready["task"]["provenance"]["inferred_from_video"] is False
    assert len(ready["task"]["steps"]) == 2
    assert ready["frames"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"transcript": "Untimestamped prose", "usage_rights_confirmed": True},
        {
            "youtube_url": "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
            "usage_rights_confirmed": True,
        },
        {"transcript": "[00:20] Later\n[00:10] Earlier", "usage_rights_confirmed": True},
    ],
)
def test_invalid_tutorial_sources_are_rejected(digital_client, body):
    project = digital_client.post("/api/projects", json={"name": "Bad source", "modality": "digital"}).json()
    assert digital_client.post(f"/api/projects/{project['id']}/tutorial", json=body).status_code == 422
    assert digital_client.get(f"/api/projects/{project['id']}").json()["tutorial"] is None


def test_physical_default_and_digital_uploaded_video_rights(digital_client):
    client = digital_client
    physical = client.post("/api/projects", json={"name": "Physical stays default"}).json()
    assert physical["modality"] == "physical"
    assert client.post(f"/api/projects/{physical['id']}/screen-session/clear").status_code == 409
    digital = client.post(
        "/api/projects", json={"name": "Rights-cleared upload", "modality": "digital"}
    ).json()
    denied = client.post(
        f"/api/projects/{digital['id']}/video", files={"file": ("source.mp4", b"fixture", "video/mp4")}
    )
    assert denied.status_code == 422
    source = client.get("/api/demo/video").content
    accepted = client.post(
        f"/api/projects/{digital['id']}/video",
        data={"usage_rights_confirmed": "true"},
        files={"file": ("source.mp4", source, "video/mp4")},
    )
    assert accepted.status_code == 202, accepted.text
    assert len(client.get(f"/api/projects/{digital['id']}").json()["frames"]) == 4


def test_identical_screen_capture_reuses_session_then_clear_forgets_it(
    digital_client, digital_project, monkeypatch
):
    client, project = digital_client, digital_project
    approve(client, project)
    calls = []

    def observe(*args, **kwargs):
        calls.append(True)
        return evidence("Extensions Marketplace")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", observe)
    first = capture(client, project)
    second = capture(client, project)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(calls) == 1
    assert client.post(f"/api/projects/{project['id']}/screen-session/clear").status_code == 204
    assert capture(client, project).status_code == 200
    assert len(calls) == 2


@pytest.mark.parametrize(
    "observation,status,reason",
    [
        (evidence("Preferences"), "fail", "mismatch"),
        (evidence("Replay Formatter", "Installed", "Enabled"), "uncertain", "skipped_step"),
        (evidence("Permission denied", role="dialog"), "fail", "unexpected_dialog"),
        (evidence("Extensions Marketplace", version="CodeLab 2.0"), "uncertain", "interface_mismatch"),
        (evidence("Extensions Marketplace", quality=0.1), "uncertain", "insufficient_evidence"),
    ],
)
def test_observed_mismatch_and_uncertainty_do_not_advance(
    digital_client, digital_project, monkeypatch, observation, status, reason
):
    client, project = digital_client, digital_project
    approve(client, project)
    monkeypatch.setattr("app.services.screen_observation.observe_screen", lambda *args, **kwargs: observation)
    response = capture(client, project)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"]["status"] == status, payload
    assert payload["result"]["reason"] == reason, payload
    assert payload["completed_step_ids"] == []


def test_meta_requires_consent_and_key_and_never_falls_back(digital_client, digital_project, monkeypatch):
    client, project = digital_client, digital_project
    approve(client, project)
    client.post("/api/provider", json={"mode": "meta"})
    assert capture(client, project).status_code == 422
    assert capture(client, project, cloud_consent="true").status_code == 503
    client.app.state.settings.model_api_key = "test-key-not-a-real-credential"
    selected_modes = []

    def unavailable(content, mode, provider, **kwargs):
        selected_modes.append(mode)
        raise ProviderError("Meta screen analysis is unavailable.", "upstream_error", 503)

    monkeypatch.setattr("app.services.screen_observation.observe_screen", unavailable)
    response = capture(client, project, cloud_consent="true")
    assert response.status_code == 502
    assert selected_modes == ["meta"]
    assert client.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == []


def test_meta_screen_route_uses_screenshot_adapter_not_physical_sam(
    digital_client, digital_project, monkeypatch
):
    client, project = digital_client, digital_project
    approve(client, project)
    client.app.state.settings.model_api_key = "test-key-not-a-real-credential"
    client.post("/api/provider", json={"mode": "meta"})
    local = evidence("Extensions Marketplace")
    local.provenance.update(ocr_available=True, redaction_applied=True)
    calls = []

    def physical_sam_must_not_run(*args, **kwargs):
        raise AssertionError("Digital screen observations must not use the physical SAM adapter")

    def no_network(*args, **kwargs):
        raise AssertionError("This regression test must not contact Meta")

    def screenshot_adapter(self, redacted_bytes, local_observation):
        calls.append((redacted_bytes, local_observation))
        assert self.provider._api_key == "test-key-not-a-real-credential"
        return local_observation.model_copy(update={"provider_mode": "meta"})

    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda _: local)
    monkeypatch.setattr("app.providers.meta.MetaProvider.observe", physical_sam_must_not_run)
    monkeypatch.setattr("app.providers.meta.MetaProvider._request", no_network)
    monkeypatch.setattr("app.providers.meta_screen.MetaScreenProvider.observe", screenshot_adapter)
    response = capture(client, project, cloud_consent="true")
    assert response.status_code == 200, response.text
    assert response.json()["result"]["status"] == "pass"
    assert response.json()["result"]["provider_mode"] == "meta"
    assert len(calls) == 1
    assert calls[0][0].startswith(b"\x89PNG")


def test_prerequisite_progress_invalidates_earlier_skipped_capture_cache(
    digital_client, digital_project, monkeypatch
):
    client, project = digital_client, digital_project
    approve(client, project)
    first_image = client.get(project["frames"][0]["url"]).content
    second_image = client.get(project["frames"][1]["url"]).content
    calls = []

    def observe(content, *args, **kwargs):
        calls.append(content)
        if content == first_image:
            return evidence("Extensions Marketplace")
        assert content == second_image
        return evidence("Search results", "Replay Formatter")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", observe)
    skipped = capture(client, project, index=1, content=second_image)
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["result"]["status"] == "uncertain"
    assert skipped.json()["result"]["reason"] == "skipped_step"
    assert skipped.json()["completed_step_ids"] == []
    first = capture(client, project, content=first_image)
    assert first.json()["result"]["status"] == "pass"
    second = capture(client, project, index=1, content=second_image)
    assert second.status_code == 200, second.text
    assert second.json()["result"]["status"] == "pass"
    assert second.json()["completed_step_ids"] == ["digital-step-1", "digital-step-2"]
    assert len(calls) == 3
    repeated = capture(client, project, index=1, content=second_image)
    assert repeated.json() == second.json()
    assert len(calls) == 3


def test_failed_screen_calls_are_rate_limited(digital_client, digital_project, monkeypatch):
    client, project = digital_client, digital_project
    approve(client, project)
    client.app.state.settings.screen_local_interval = 60
    calls = []

    def unavailable(*args, **kwargs):
        calls.append(True)
        raise ProviderError("Observation temporarily unavailable.", "upstream_error")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", unavailable)
    assert capture(client, project).status_code == 502
    limited = capture(client, project)
    assert limited.status_code == 429
    assert limited.headers["Retry-After"] == "60"
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["stop", "edit"])
def test_stopped_or_stale_inflight_capture_cannot_complete_step(
    digital_client, digital_project, monkeypatch, mutation
):
    client, project = digital_client, digital_project
    approve(client, project)
    entered, release = threading.Event(), threading.Event()

    def blocking_observation(*args, **kwargs):
        entered.set()
        assert release.wait(10), "Test did not release the controlled observation"
        return evidence("Extensions Marketplace")

    monkeypatch.setattr("app.services.screen_observation.observe_screen", blocking_observation)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(capture, client, project)
        try:
            assert entered.wait(10), "Screen processing never started"
            if mutation == "stop":
                assert capture(client, project).status_code == 429
                assert client.post(f"/api/projects/{project['id']}/screen-session/clear").status_code == 204
            else:
                task = copy.deepcopy(project["task"])
                task["steps"][0]["description"] += " Edited while analysis is running."
                saved = client.put(f"/api/projects/{project['id']}/task", json=task)
                assert saved.status_code == 200, saved.text
            release.set()
            response = future.result(timeout=10)
        finally:
            release.set()
    assert response.status_code == 409, response.text
    assert client.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == []
    assert client.app.state.screen_sessions.last(project["id"]) is None


def test_ask_uses_workflow_without_screen_and_forgets_after_stop(
    digital_client, digital_project, monkeypatch
):
    client, project = digital_client, digital_project
    approve(client, project)
    endpoint = f"/api/projects/{project['id']}/ask"
    absent = client.post(endpoint, json={"question": "What do I do next?"}).json()
    assert absent["evidence"] == []
    assert "no current screen" in " ".join(absent["warnings"]).lower()
    monkeypatch.setattr(
        "app.services.screen_observation.observe_screen",
        lambda *args, **kwargs: evidence("Extensions Marketplace"),
    )
    assert capture(client, project).status_code == 200
    grounded = client.post(endpoint, json={"question": "What is current?"}).json()
    assert grounded["evidence"]
    client.post(f"/api/projects/{project['id']}/screen-session/clear")
    cleared = client.post(
        endpoint, json={"question": "Confirm files on disk and hidden application state"}
    ).json()
    assert cleared["evidence"] == []
    assert "cannot confirm hidden" in cleared["answer"].lower()
    assert "no current screen" in " ".join(cleared["warnings"]).lower()
