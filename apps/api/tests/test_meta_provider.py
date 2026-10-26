"""Live adapter contract tests; all network traffic uses httpx MockTransport."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.providers.meta import MetaProvider, ProviderError
from app.schemas import VerificationResult

# Captured public example from Meta's SAM parser README. This is valid encoded
# lossless mask data, not a fake SAM JSON object or a fabricated parser result.
_MASK = "!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x("
_SAM = (
    f"<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334;c=0.95|><|mask;x=0;y=0;c=0.95;data=27,60,~{_MASK}|>"
)
_PROPOSAL = {
    "title": "Place a block",
    "description": "An observed demonstration.",
    "objects": ["red block"],
    "steps": [
        {
            "id": "step1",
            "title": "Place the block",
            "description": "Put the block on the table.",
            "dependencies": [],
            "timestamp_start": 0,
            "timestamp_end": 2,
            "object_labels": ["red block"],
            "rules": [
                {
                    "id": "r1",
                    "kind": "presence",
                    "subject": "red block",
                    "target": None,
                    "value": True,
                    "tolerance": 0.04,
                }
            ],
        }
    ],
}


def response_text(text: str, status: str = "completed") -> dict:
    return {
        "id": "resp_test",
        "status": status,
        "output": [
            {"type": "reasoning", "summary": []},
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]},
        ],
    }


@pytest.fixture
def image(tmp_path: Path) -> Path:
    path = tmp_path / "current.png"
    Image.new("RGB", (320, 334), "white").save(path)
    return path


def provider(tmp_path: Path, handler) -> MetaProvider:
    return MetaProvider(
        "test-private-key", tmp_path / "cache", client=httpx.Client(transport=httpx.MockTransport(handler))
    )


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "invalid_request"),
        (401, "authentication"),
        (402, "billing"),
        (403, "forbidden"),
        (404, "not_found"),
        (413, "payload_too_large"),
        (504, "timeout"),
    ],
)
def test_permanent_errors_are_safe_and_not_retried(tmp_path, image, status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "LEAKED provider diagnostic SECRET"}})

    api = provider(tmp_path, handler)
    with pytest.raises(ProviderError) as error:
        api.observe(image, ["block"])
    assert error.value.code == code
    assert error.value.status_code == status
    assert "SECRET" not in str(error.value)
    assert "test-private-key" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_errors_retry_and_respect_retry_after(tmp_path, image, monkeypatch, status):
    sleeps, calls = [], []
    monkeypatch.setattr("app.providers.meta.time.sleep", sleeps.append)
    monkeypatch.setattr("app.providers.meta.random.random", lambda: 0)

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, headers={"Retry-After": "2"}, json={"error": {}})
        return httpx.Response(200, json=response_text(""))

    result = provider(tmp_path, handler).observe(image, ["block"])
    assert result.observations == []
    assert len(calls) == 2
    assert sleeps == [2]


def test_rate_limit_exhaustion_is_bounded(tmp_path, image, monkeypatch):
    calls = []
    monkeypatch.setattr("app.providers.meta.time.sleep", lambda _: None)

    def handler(request):
        calls.append(request)
        return httpx.Response(429, json={"error": {}})

    with pytest.raises(ProviderError, match="rate limiting") as error:
        provider(tmp_path, handler).observe(image, ["block"])
    assert error.value.code == "rate_limit"
    assert len(calls) == 3


def test_network_timeout_is_retried_then_surfaced(tmp_path, image, monkeypatch):
    calls = []
    monkeypatch.setattr("app.providers.meta.time.sleep", lambda _: None)

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret upstream detail", request=request)

    with pytest.raises(ProviderError) as error:
        provider(tmp_path, handler).observe(image, ["block"])
    assert error.value.code == "connection"
    assert "secret" not in str(error.value)
    assert len(calls) == 3


def test_sam_real_parser_normalizes_boxes_and_preserves_unknown_quality(tmp_path, image):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=response_text(_SAM))

    api = provider(tmp_path, handler)
    result = api.observe(image, ["block", "block"])
    assert result.provider_mode == "meta"
    assert len(result.observations) == 1
    observed = result.observations[0]
    assert observed.bbox == pytest.approx((211 / 320, 228 / 334, 271 / 320, 255 / 334))
    assert observed.confidence == 0.95
    assert observed.mask_rle["size"] == [27, 60]
    assert isinstance(observed.mask_rle["counts"], str)
    assert observed.mask_rle["coordinate_space"] == "box_local"
    assert result.visibility is None and result.coverage is None
    assert result.image_quality is None and result.comparable is None
    assert result.provenance["detection_complete"] is False
    payload = json.loads(requests[0].content)
    assert payload["model"] == "sam-3.1"
    assert payload["metadata"] == {"include_confidence": "true", "mask_encoding": "one_bit"}
    assert payload["store"] is False and payload["stream"] is False
    assert requests[0].headers["authorization"] == "Bearer test-private-key"
    assert payload["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
    cached = api.observe(image, ["block"])
    assert cached.provenance["cache_hit"] is True
    assert len(requests) == 1
    for path in api.cache_dir.glob("*.json"):
        assert "test-private-key" not in path.read_text()


def test_missing_sam_confidence_remains_unknown(tmp_path, image):
    result = provider(
        tmp_path, lambda _: httpx.Response(200, json=response_text(_SAM.replace(";c=0.95", "")))
    ).observe(image, ["block"])
    assert result.observations[0].confidence is None


@pytest.mark.parametrize(
    "text",
    [
        "not SAM output",
        "<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=320;h=334|>",
        _SAM.replace(_MASK, "broken"),
        _SAM.replace("w=320", "w=640"),
    ],
)
def test_malformed_or_wrong_dimension_sam_is_rejected(tmp_path, image, text):
    with pytest.raises(ProviderError) as error:
        provider(tmp_path, lambda _: httpx.Response(200, json=response_text(text))).observe(image, ["block"])
    assert error.value.code == "invalid_output"


def test_refusal_is_not_a_mock_result(tmp_path, image):
    body = {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "private diagnostic"}]}],
    }
    with pytest.raises(ProviderError) as error:
        provider(tmp_path, lambda _: httpx.Response(200, json=body)).observe(image, ["block"])
    assert error.value.code == "refusal"


def test_incomplete_response_is_not_accepted(tmp_path, image):
    with pytest.raises(ProviderError) as error:
        provider(tmp_path, lambda _: httpx.Response(200, json=response_text(_SAM, "incomplete"))).observe(
            image, ["block"]
        )
    assert error.value.code == "incomplete"


def test_invalid_provider_json_is_safe(tmp_path, image):
    with pytest.raises(ProviderError) as error:
        provider(tmp_path, lambda _: httpx.Response(200, content=b"invalid")).observe(image, ["block"])
    assert error.value.code == "invalid_response"


def test_task_upload_structured_request_cleanup_and_frame_mapping(tmp_path):
    video = tmp_path / "tutorial.mp4"
    video.write_bytes(b"local fixture; MockTransport does not decode video")
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "file-123", "object": "file", "deleted": True})
        if request.url.path.endswith("/files"):
            assert b'name="purpose"' in request.content
            assert b"user_data" in request.content
            assert b"expires_after[seconds]" in request.content
            return httpx.Response(200, json={"id": "file-123"})
        return httpx.Response(200, json=response_text(json.dumps(_PROPOSAL)))

    api = provider(tmp_path, handler)
    task = api.extract_task(video, [{"id": "f0", "timestamp": 0}, {"id": "f2", "timestamp": 2}])
    assert task.steps[0].reference_frame_id == "f2"
    assert task.provider_mode == "meta" and task.provenance["requires_approval"] is True
    assert task.provenance["cloud_file_cleanup_pending"] is False
    assert [request.method for request in requests] == ["POST", "POST", "DELETE"]
    payload = json.loads(requests[1].content)
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert "response_format" not in payload
    assert payload["input"][0]["content"][1] == {"type": "input_file", "file_id": "file-123"}
    second = api.extract_task(video, [{"id": "new-frame-id", "timestamp": 2}])
    assert second.provenance["cache_hit"] is True
    assert second.id != task.id
    assert second.steps[0].reference_frame_id == "new-frame-id"
    assert len(requests) == 3


def test_non_mp4_video_is_rejected_before_cloud_upload(tmp_path):
    video = tmp_path / "tutorial.webm"
    video.write_bytes(b"fixture")
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    with pytest.raises(ProviderError, match="requires an MP4") as error:
        provider(tmp_path, handler).extract_task(video, [])
    assert error.value.code == "unsupported_media"
    assert requests == []


@pytest.mark.parametrize("mode", ["malformed", "bad_graph", "undeclared_object"])
def test_invalid_task_is_rejected_and_file_is_deleted(tmp_path, mode):
    video = tmp_path / "tutorial.mp4"
    video.write_bytes(b"fixture")
    requests = []
    proposal = copy.deepcopy(_PROPOSAL)
    if mode == "bad_graph":
        proposal["steps"][0]["dependencies"] = ["missing-step"]
    if mode == "undeclared_object":
        proposal["steps"][0]["rules"][0]["subject"] = "invisible object"

    def handler(request):
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"deleted": True})
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-123"})
        return httpx.Response(
            200, json=response_text("bad json" if mode == "malformed" else json.dumps(proposal))
        )

    with pytest.raises(ProviderError) as error:
        provider(tmp_path, handler).extract_task(video, [])
    assert error.value.code == "invalid_output"
    assert requests[-1].method == "DELETE"


def test_cleanup_failure_keeps_valid_task_and_records_expiry(tmp_path):
    video = tmp_path / "tutorial.mp4"
    video.write_bytes(b"fixture")

    def handler(request):
        if request.method == "DELETE":
            return httpx.Response(403, json={"error": {}})
        if request.url.path.endswith("/files"):
            return httpx.Response(200, json={"id": "file-123"})
        return httpx.Response(200, json=response_text(json.dumps(_PROPOSAL)))

    task = provider(tmp_path, handler).extract_task(video, [])
    assert task.provenance["cloud_file_cleanup_pending"] is True
    assert task.provenance["cloud_file_expiration_seconds"] == 3600


def verification() -> VerificationResult:
    return VerificationResult(
        step_id="s1",
        status="uncertain",
        evidence=["The block confidence is unknown."],
        explanation="Uncertain: the observation is not reliable enough.",
        provider_mode="meta",
    )


@pytest.mark.parametrize(
    "selection",
    [
        {"status": "pass", "evidence_ids": ["E1"]},
        {"status": "uncertain", "evidence_ids": ["E99"]},
        {"status": "uncertain", "evidence_ids": ["E1"], "narration": "invented fact"},
    ],
)
def test_explanation_cannot_change_status_or_invent_facts(tmp_path, selection):
    api = provider(tmp_path, lambda _: httpx.Response(200, json=response_text(json.dumps(selection))))
    result = verification()
    assert api.explain(result) == result.explanation
    assert api.last_explanation_provenance["fallback"] is True


def test_valid_explanation_renders_only_existing_facts(tmp_path):
    selection = {"status": "uncertain", "evidence_ids": ["E1"]}
    api = provider(tmp_path, lambda _: httpx.Response(200, json=response_text(json.dumps(selection))))
    result = verification()
    assert api.explain(result) == result.explanation + " Evidence: " + result.evidence[0]
    assert api.last_explanation_provenance["rendering"] == "deterministic_evidence"


def test_explanation_provider_failure_retains_deterministic_explanation(tmp_path):
    api = provider(tmp_path, lambda _: httpx.Response(402, json={"error": {}}))
    result = verification()
    assert api.explain(result) == result.explanation
    assert api.last_explanation_provenance["fallback"] is True


def test_missing_key_fails_before_any_request(tmp_path):
    with pytest.raises(ProviderError) as error:
        MetaProvider(" ", tmp_path)
    assert error.value.code == "not_configured"
