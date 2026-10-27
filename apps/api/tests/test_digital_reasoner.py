import json

import httpx
import pytest

from app.providers.digital_reasoner import extract_workflow
from app.providers.meta import MetaProvider, ProviderError


def project():
    return {
        "name": "Extension guide",
        "frames": [{"id": "frame-a", "timestamp": 1.0}],
        "tutorial": {
            "title": "Guide",
            "transcript_segments": [{"start": 0, "end": 2, "text": 'Open "Extensions".'}],
        },
    }


def proposal():
    return {
        "title": "Extension guide",
        "description": "A visible UI procedure",
        "interface_version": None,
        "steps": [
            {
                "id": "open",
                "title": "Open extensions",
                "description": "Show Extensions",
                "dependencies": [],
                "timestamp_start": 0,
                "timestamp_end": 2,
                "expected_state": "Extensions panel visible",
                "screen_rules": [
                    {
                        "id": "panel",
                        "kind": "text_present",
                        "expected": "Extensions",
                        "alternatives": [],
                        "contradictions": ["Preferences"],
                        "description": "Panel title",
                    }
                ],
            }
        ],
    }


def response(data):
    return {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(data)}]}],
    }


def test_muse_transcript_uses_digital_schema_and_maps_reference(tmp_path):
    calls = []

    def handle(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["model"] == "muse-spark-1.3"
        assert body["store"] is False
        assert body["text"]["format"]["name"] == "ReplayLabDigitalWorkflow"
        assert "untrusted" in body["instructions"].lower()
        assert body["input"][0]["content"][0]["type"] == "input_text"
        return httpx.Response(200, json=response(proposal()))

    provider = MetaProvider("test-key", tmp_path, client=httpx.Client(transport=httpx.MockTransport(handle)))
    task = extract_workflow(project(), provider, "meta", None)
    assert task.modality == "digital"
    assert task.steps[0].reference_frame_id == "frame-a"
    assert task.steps[0].screen_rules[0].expected == "Extensions"
    assert not task.steps[0].rules
    cached = extract_workflow(project(), provider, "meta", None)
    assert cached.provenance["cache_hit"] is True
    assert len(calls) == 1


def test_video_file_deleted_even_when_workflow_invalid(tmp_path):
    video = tmp_path / "reference.mp4"
    video.write_bytes(b"test transport bytes; not live media")
    calls = []
    invalid = proposal()
    invalid["steps"][0]["dependencies"] = ["missing"]

    def handle(request):
        calls.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(200, json={"deleted": True})
        if request.url.path.endswith("/files"):
            assert b"3600" in request.content
            return httpx.Response(200, json={"id": "file-demo"})
        return httpx.Response(200, json=response(invalid))

    provider = MetaProvider(
        "test-key", tmp_path / "cache", client=httpx.Client(transport=httpx.MockTransport(handle))
    )
    with pytest.raises(ProviderError, match="invalid digital workflow"):
        extract_workflow(project(), provider, "meta", video)
    assert calls[-1] == ("DELETE", "/v1/files/file-demo")


def test_meta_digital_errors_never_become_mock(tmp_path):
    provider = MetaProvider(
        "test-key",
        tmp_path,
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(402, json={"error": {"message": "private token"}})
            )
        ),
    )
    with pytest.raises(ProviderError, match="billing"):
        extract_workflow(project(), provider, "meta", None)


def test_mock_transcript_is_proposal_and_not_video_inference():
    task = extract_workflow(project(), None, "mock", None)
    assert task.modality == "digital"
    assert task.provider_mode == "mock"
    assert task.steps[0].screen_rules[0].expected == "Extensions"


def test_youtube_reference_without_transcript_not_sent_to_model(tmp_path):
    source = project()
    source["tutorial"]["transcript_segments"] = []
    provider = MetaProvider(
        "test-key",
        tmp_path,
        client=httpx.Client(
            transport=httpx.MockTransport(lambda request: pytest.fail("No source should be uploaded"))
        ),
    )
    with pytest.raises(ProviderError, match="not downloaded"):
        extract_workflow(source, provider, "meta", None)


@pytest.mark.parametrize("identifier", ["../../responses", "file-../../responses", True, ""])
def test_invalid_cloud_file_identifier_never_becomes_delete_path(tmp_path, identifier):
    video = tmp_path / "reference.mp4"
    video.write_bytes(b"transport fixture")
    methods = []

    def handle(request):
        methods.append(request.method)
        return httpx.Response(200, json={"id": identifier})

    provider = MetaProvider(
        "test-key", tmp_path / "cache", client=httpx.Client(transport=httpx.MockTransport(handle))
    )
    with pytest.raises(ProviderError, match="invalid upload identifier"):
        extract_workflow(project(), provider, "meta", video)
    assert methods == ["POST"]
