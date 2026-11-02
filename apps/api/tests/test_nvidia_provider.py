"""NVIDIA Chat Completions contract tests; all requests use MockTransport."""

import base64
import copy
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import pytest
from PIL import Image

from app.digital_schemas import ScreenElement, ScreenObservation
from app.providers.grounded_explanation import clear_explanation_cache, explain_verification
from app.providers.meta import ProviderError
from app.providers.nvidia import (
    NVIDIA_MODEL, NvidiaProvider, NvidiaScreenProvider, clear_nvidia_screen_cache, image_part,
)
from app.schemas import Step
from app.digital_schemas import ScreenResult, ScreenRuleResult


def completed(content, **extra):
    return {
        "id": "chatcmpl-controlled-test", "model": NVIDIA_MODEL,
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 21, "completion_tokens": 12, "total_tokens": 33},
        **extra,
    }


def adapter(tmp_path, handler):
    return NvidiaProvider(
        "test-nvidia-" + uuid4().hex, tmp_path / "cache",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def image_bytes():
    data = io.BytesIO()
    Image.new("RGB", (320, 200), "navy").save(data, format="PNG")
    return data.getvalue()


def local(*texts):
    return ScreenObservation(
        elements=[ScreenElement(text=text, confidence=.97, source="local_ocr", bbox=(.1, .2, .8, .4)) for text in texts],
        visible_text="\n".join(texts), confidence=.97, image_quality=.98, provider_mode="local_ocr",
        provenance={"redaction_applied": True, "ocr_available": True, "real_ocr": True},
    )


def screen_payload(text="Extensions", confidence=.95, **extra):
    return {
        "visible_application": "CodeLab", "current_window": "Extensions Marketplace",
        "elements": [{"text": text, "role": "window", "bbox": [.1, .2, .8, .4], "confidence": confidence}],
        "missing_information": [], **extra,
    }


@pytest.fixture(autouse=True)
def reset_caches():
    clear_nvidia_screen_cache()
    clear_explanation_cache()
    yield
    clear_nvidia_screen_cache()
    clear_explanation_cache()


def test_text_transport_matches_documented_chat_protocol_and_diagnostics(tmp_path, caplog):
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert str(request.url) == "https://integrate.api.nvidia.com/v1/chat/completions"
        assert body["model"] == NVIDIA_MODEL and body["stream"] is False
        assert body["temperature"] == .95 and body["top_p"] == 1
        assert body["reasoning_effort"] == "low" and body["max_tokens"] == 128
        assert "response_format" not in body and "store" not in body
        assert request.headers["Authorization"].startswith("Bearer test-nvidia-")
        return httpx.Response(200, json=completed("NVIDIA text response"))

    provider = adapter(tmp_path, handler)
    assert provider.live_verified is False
    with caplog.at_level("INFO", logger="replaylab.provider"):
        assert provider.complete([{"role": "user", "content": "Controlled probe"}], max_tokens=128) == "NVIDIA text response"
    assert provider.live_verified is True and provider.last_latency_ms >= 0
    assert provider.last_usage == {"prompt_tokens": 21, "completion_tokens": 12, "total_tokens": 33}
    assert provider.last_response_id == "chatcmpl-controlled-test"
    assert provider.last_model == NVIDIA_MODEL
    assert provider._api_key not in caplog.text and "Controlled probe" not in caplog.text
    assert len(calls) == 1


@pytest.mark.parametrize("status,code", [
    (400, "invalid_request"), (401, "authentication"), (402, "billing"), (403, "forbidden"),
    (404, "not_found"), (413, "payload_too_large"), (422, "invalid_request"), (429, "rate_limit"),
    (500, "upstream_error"), (202, "pending"),
])
def test_safe_errors_do_not_echo_provider_content_or_become_mock(tmp_path, status, code, monkeypatch):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "SECRET UPSTREAM CONTENT"})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError) as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == code
    assert "SECRET" not in str(caught.value) and provider.live_verified is False
    assert len(calls) == (2 if status == 429 else 1)


@pytest.mark.parametrize("content", [None, "", [], 123])
def test_missing_final_content_never_uses_reasoning_as_evidence(tmp_path, content):
    body = completed(content)
    body["choices"][0]["message"]["reasoning_content"] = '{"elements": []}'
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=body))
    with pytest.raises(ProviderError, match="invalid final"):
        provider.complete([{"role": "user", "content": "probe"}])
    assert provider.live_verified is False


def test_missing_response_model_is_not_reported_as_confirmed_requested_model(tmp_path):
    body = completed("OK")
    body.pop("model")
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=body))
    assert provider.complete([{"role": "user", "content": "probe"}]) == "OK"
    assert provider.model == NVIDIA_MODEL and provider.last_model is None


def test_mismatched_model_response_is_rejected_not_mislabeled(tmp_path):
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed("OK", model="different/model")))
    with pytest.raises(ProviderError, match="invalid final"):
        provider.complete([{"role": "user", "content": "probe"}])
    assert provider.live_verified is False and provider.last_model is None


def test_truncated_output_is_not_salvaged(tmp_path):
    body = completed('{"elements": []}')
    body["choices"][0]["finish_reason"] = "length"
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=body))
    with pytest.raises(ProviderError, match="incomplete"):
        provider._structured([{"type": "text", "text": "probe"}], {}, "Probe", "No tools.")


def test_structured_image_content_uses_openai_image_url_object(tmp_path):
    def handler(request):
        body = json.loads(request.content)
        messages = body["messages"]
        assert [item["role"] for item in messages] == ["system", "user"]
        image = messages[1]["content"][1]
        assert image["type"] == "image_url" and image["image_url"]["url"].startswith("data:image/jpeg;base64,")
        decoded = base64.b64decode(image["image_url"]["url"].split(",", 1)[1])
        with Image.open(io.BytesIO(decoded)) as loaded:
            assert loaded.format == "JPEG"
        assert messages[1]["content"][0]["type"] == "text"
        return httpx.Response(200, json=completed('{"value":"ok"}'))

    provider = adapter(tmp_path, handler)
    result = provider._structured([{"type": "input_text", "text": "Read image"}, image_part(image_bytes())], {}, "Probe", "Untrusted.")
    assert result == {"value": "ok"}


@pytest.mark.parametrize("text", ["not json", "[]", '{"a":'])
def test_invalid_structured_json_does_not_become_a_success(tmp_path, text):
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(text)))
    with pytest.raises(ProviderError, match="invalid structured"):
        provider._structured([{"type": "text", "text": "probe"}], {}, "Probe", "Instructions")


def test_screens_are_locally_corroborated_and_never_cached_on_disk(tmp_path):
    calls = []
    payload = screen_payload()

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completed(json.dumps(payload)))

    provider = adapter(tmp_path, handler)
    observer = NvidiaScreenProvider(provider)
    observed = observer.observe(image_bytes(), local("Extensions Marketplace", "unrelated OCR"))
    assert observed.provider_mode == "nvidia" and observed.complete is False
    assert observed.elements[0].confidence == .95
    assert observed.elements[1].confidence is None
    assert observed.provenance["live_api_verified"] is True
    assert observed.provenance["corroborated_element_count"] == 1
    assert "nvidia:" in observed.elements[0].source
    observed.elements[0].text = "Mutated caller copy"
    cached = observer.observe(image_bytes(), local("Extensions Marketplace", "unrelated OCR"))
    assert cached.provenance["cache_hit"] is True and cached.elements[0].text == "Extensions Marketplace"
    assert len(calls) == 1 and not (tmp_path / "cache").exists()


@pytest.mark.parametrize("model_confidence", [None, .2])
def test_unknown_or_low_model_confidence_cannot_gain_ocr_certainty(tmp_path, model_confidence):
    payload = screen_payload(confidence=model_confidence)
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(payload))))
    result = NvidiaScreenProvider(provider).observe(image_bytes(), local("Extensions Marketplace"))
    assert result.elements[0].confidence == model_confidence
    assert result.confidence is None or result.confidence < .75


def test_model_only_hallucination_remains_uncorroborated(tmp_path):
    payload = screen_payload("Installed", confidence=1)
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(payload))))
    result = NvidiaScreenProvider(provider).observe(image_bytes(), local("Not installed"))
    assert result.elements[0].confidence is None
    assert "Not installed" in result.visible_text
    assert any(item.confidence is None for item in result.elements if item.text == "Not installed")


def test_privacy_scan_is_required_even_for_direct_adapter_use(tmp_path):
    provider = adapter(tmp_path, lambda request: pytest.fail("No request without privacy scan"))
    with pytest.raises(ProviderError, match="privacy scan"):
        NvidiaScreenProvider(provider).observe(image_bytes(), ScreenObservation())


def test_extra_fields_and_invalid_boxes_are_rejected(tmp_path):
    payload = screen_payload()
    payload["elements"][0]["bbox"] = [1, .2, .1, .4]
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(payload))))
    with pytest.raises(ProviderError, match="invalid screen observations"):
        NvidiaScreenProvider(provider).observe(image_bytes(), local("Extensions"))


def test_sensitive_model_text_is_redacted_again(tmp_path):
    payload = screen_payload("user@example.invalid")
    payload["missing_information"] = ["account user@example.invalid is hidden"]
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(payload))))
    result = NvidiaScreenProvider(provider).observe(image_bytes(), local("[REDACTED_EMAIL]"))
    assert "user@example.invalid" not in result.model_dump_json()


def workflow():
    return {
        "title": "Open Extensions", "description": "One visible checkpoint", "interface_version": None,
        "steps": [{"id": "open", "title": "Open Extensions", "description": "Inspect the visible panel.",
                   "dependencies": [], "timestamp_start": 0, "timestamp_end": 1,
                   "expected_state": "Extensions visible",
                   "screen_rules": [{"id": "r", "kind": "text_present", "expected": "Extensions", "alternatives": [], "contradictions": [], "description": ""}]}],
    }


def test_workflow_uses_timestamped_images_and_validates_proposal_for_review(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        parts = body["messages"][1]["content"]
        assert any(item["type"] == "image_url" for item in parts)
        assert any("1.000 seconds" in item.get("text", "") for item in parts)
        assert "direct video" in body["messages"][0]["content"]
        return httpx.Response(200, json=completed(json.dumps(workflow())))

    path = tmp_path / "frame.png"
    path.write_bytes(image_bytes())
    project = {"name": "Tutorial", "video": {"duration": 2}, "tutorial": {}}
    frames = [{"id": "frame-1", "timestamp": 1, "path": path}]
    provider = adapter(tmp_path, handler)
    task = provider.extract_workflow(project, frames)
    assert task.provider_mode == "nvidia" and task.modality == "digital"
    assert task.steps[0].reference_frame_id == "frame-1"
    assert task.provenance["requires_approval"] is True and task.provenance["direct_video_supported"] is False
    provider.last_response_id = "different-request"
    provider.last_latency_ms = 99999
    cached = provider.extract_workflow(project, frames)
    assert cached.provenance["cache_hit"] is True
    assert cached.provenance["request_id"] is None and cached.provenance["latency_ms"] == 0
    assert cached.provenance["token_usage"] == {} and cached.provenance["response_model"] is None
    assert len(calls) == 1


@pytest.mark.parametrize("mutation", ["cycle", "timestamp", "extra"])
def test_bad_workflow_is_rejected_before_it_can_be_cached(tmp_path, mutation):
    proposal = workflow()
    if mutation == "cycle":
        proposal["steps"][0]["dependencies"] = ["open"]
    elif mutation == "timestamp":
        proposal["steps"][0]["timestamp_end"] = 100
    else:
        proposal["verdict"] = "pass"
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(proposal))))
    project = {"name": "Transcript", "tutorial": {"transcript_segments": [{"start": 0, "end": 2, "text": "Open Extensions"}]}}
    with pytest.raises(ProviderError, match="invalid workflow"):
        provider.extract_workflow(project, [])
    assert not (tmp_path / "cache").exists()


def test_physical_segmentation_is_not_silently_substituted(tmp_path):
    provider = adapter(tmp_path, lambda request: pytest.fail("No SAM substitute request"))
    with pytest.raises(ProviderError, match="physical SAM"):
        provider.observe(tmp_path / "image.png", [])


def test_existing_grounded_plan_facade_cannot_change_verdict(tmp_path):
    provider = adapter(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps({
        "status": "pass", "evidence_ids": ["E1"], "correction_id": None,
    }))))
    decision = ScreenResult(step_id="s", status="fail", evidence=["Preferences visible"],
                            explanation="The wrong panel is visible.", provider_mode="nvidia",
                            rule_results=[ScreenRuleResult(rule_id="r", status="fail", expected="Extensions", observed="Preferences")])
    before = copy.deepcopy(decision.model_dump())
    explained = explain_verification(provider, Step(id="s", title="Extensions"), decision)
    assert explained.provider_mode == "deterministic_template" and explained.warning
    assert decision.model_dump() == before


def test_timeout_is_bounded_and_safe(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("SECRET RAW NETWORK INFO", request=request)

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError, match="timed out") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert len(calls) == 1 and "SECRET" not in str(caught.value)


def test_shared_provider_keeps_concurrent_observation_metadata_with_its_request(tmp_path):
    finished_b = threading.Event()

    def handler(request):
        label = threading.current_thread().name
        tokens = 11 if label == "controlled-A" else 22
        return httpx.Response(200, json=completed(
            json.dumps(screen_payload()), id="response-" + label,
            usage={"prompt_tokens": tokens, "completion_tokens": 1, "total_tokens": tokens + 1},
        ), headers={"NVCF-REQID": ("11111111-1111-4111-8111-111111111111" if label == "controlled-A"
                                  else "22222222-2222-4222-8222-222222222222")})

    provider = adapter(tmp_path, handler)
    structured = provider._structured

    def force_other_request_to_finish_first(*args):
        proposal = structured(*args)
        if threading.current_thread().name == "controlled-A":
            assert finished_b.wait(5)
        else:
            finished_b.set()
        return proposal

    provider._structured = force_other_request_to_finish_first

    def observe(label, color):
        threading.current_thread().name = label
        data = io.BytesIO()
        Image.new("RGB", (64, 64), color).save(data, format="PNG")
        result = NvidiaScreenProvider(provider).observe(data.getvalue(), local("Extensions"))
        return result.provenance, provider.last_request_id, provider.last_http_status

    with ThreadPoolExecutor(max_workers=2) as workers:
        a = workers.submit(observe, "controlled-A", "navy")
        b = workers.submit(observe, "controlled-B", "green")
        first_result, second_result = a.result(timeout=10), b.result(timeout=10)
    first, second = first_result[0], second_result[0]
    assert first_result[1:] == ("11111111-1111-4111-8111-111111111111", 200)
    assert second_result[1:] == ("22222222-2222-4222-8222-222222222222", 200)
    assert first["request_id"] == "response-controlled-A"
    assert first["token_usage"]["prompt_tokens"] == 11
    assert second["request_id"] == "response-controlled-B"
    assert second["token_usage"]["prompt_tokens"] == 22
    assert first["response_model"] == second["response_model"] == NVIDIA_MODEL
    assert provider.last_response_id is None  # this calling thread made no request
    assert provider.last_request_id is None and provider.last_http_status is None
    assert provider.live_verified is True  # successful inference is app-visible


def test_accepted_generation_polls_same_origin_without_resubmitting(tmp_path, monkeypatch):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    identifier = "0d5919a3-e790-46bb-80c6-5c8f43830316"
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            assert "NVCF-POLL-SECONDS" not in request.headers
            return httpx.Response(202, headers={"NVCF-REQID": identifier})
        assert request.headers["NVCF-POLL-SECONDS"] == "5"
        assert request.url == f"https://integrate.api.nvidia.com/v1/status/{identifier}"
        assert request.content == b""
        if len(calls) == 2:
            return httpx.Response(202)
        return httpx.Response(200, json=completed("Polled response"))

    provider = adapter(tmp_path, handler)
    assert provider.complete([{"role": "user", "content": "probe"}]) == "Polled response"
    assert [request.method for request in calls] == ["POST", "GET", "GET"]
    assert all(request.headers["Authorization"] == "Bearer " + provider._api_key for request in calls)
    assert provider.live_verified is True and provider.last_response_id == "chatcmpl-controlled-test"


def test_pending_generation_has_bounded_polls_and_exactly_one_submission(tmp_path, monkeypatch):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    monkeypatch.setattr("app.providers.nvidia.MAX_STATUS_POLLS", 2)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(202, headers={"NVCF-REQID": "0d5919a3-e790-46bb-80c6-5c8f43830316"})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError, match="bounded status polling") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == "pending" and provider.live_verified is False
    assert [request.method for request in calls] == ["POST", "GET", "GET"]


@pytest.mark.parametrize("identifier", [
    "https://untrusted.invalid/steal", "../../outside", "not-a-uuid", "0d5919a3e79046bb80c65c8f43830316",
])
def test_invalid_pending_identifier_never_becomes_a_request_url(tmp_path, identifier):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(202, headers={"NVCF-REQID": identifier})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError, match="invalid polling identifier"):
        provider.complete([{"role": "user", "content": "probe"}])
    assert len(calls) == 1 and calls[0].method == "POST"


def test_pending_without_request_id_is_explicit_and_not_resubmitted(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(202, json={"message": "queued"})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError, match="pending without a polling identifier") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == "pending" and len(calls) == 1


@pytest.mark.parametrize("phase", ["submit", "poll"])
def test_provider_redirect_never_forwards_a_key_even_with_redirect_enabled_client(tmp_path, phase, monkeypatch):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.host == "integrate.api.nvidia.com"
        if phase == "poll" and request.method == "POST":
            return httpx.Response(202, headers={"NVCF-REQID": "0d5919a3-e790-46bb-80c6-5c8f43830316"})
        return httpx.Response(302, headers={"Location": "https://untrusted.invalid/collect"})

    provider = NvidiaProvider("test-redirect-only", tmp_path / "unused", client=httpx.Client(
        transport=httpx.MockTransport(handler), follow_redirects=True,
    ))
    with pytest.raises(ProviderError, match="No credentials were forwarded") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == "unsafe_redirect"
    assert len(calls) == (1 if phase == "submit" else 2)


def test_submission_and_polls_use_remaining_budget_and_reject_late_responses(tmp_path, monkeypatch):
    now = [0.0]
    calls = []
    monkeypatch.setattr("app.providers.nvidia.time.perf_counter", lambda: now[0])
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda delay: now.__setitem__(0, now[0] + delay))

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            now[0] += 2
            return httpx.Response(202, headers={"NVCF-REQID": "0d5919a3-e790-46bb-80c6-5c8f43830316"})
        now[0] += 3
        return httpx.Response(200, json=completed("Too late"))

    provider = NvidiaProvider("test-deadline-only", tmp_path / "unused", timeout_seconds=5,
                              client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(ProviderError, match="timed out") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == "timeout" and provider.live_verified is False
    assert [request.method for request in calls] == ["POST", "GET"]
    assert calls[0].extensions["timeout"]["read"] == 5
    assert calls[1].extensions["timeout"]["read"] == 2.75


def test_status_poll_timeout_does_not_start_another_generation(tmp_path, monkeypatch):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(202, headers={"NVCF-REQID": "0d5919a3-e790-46bb-80c6-5c8f43830316"})
        raise httpx.ReadTimeout("private transport information", request=request)

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError, match="timed out") as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == "timeout" and "private" not in str(caught.value)
    assert [request.method for request in calls] == ["POST", "GET"]


@pytest.mark.parametrize("status,code", [(429, "rate_limit"), (503, "upstream_error")])
def test_terminal_status_poll_errors_do_not_resubmit_queued_work(tmp_path, monkeypatch, status, code):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(202, headers={"NVCF-REQID": "0d5919a3-e790-46bb-80c6-5c8f43830316"})
        return httpx.Response(status, json={"error": "upstream private details"})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError) as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert caught.value.code == code
    assert [request.method for request in calls] == ["POST", "GET"]


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout])
def test_only_connection_establishment_failures_can_retry_submission(tmp_path, monkeypatch, error_type):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise error_type("private network diagnostics", request=request)
        return httpx.Response(200, json=completed("Recovered before submission"))

    provider = adapter(tmp_path, handler)
    assert provider.complete([{"role": "user", "content": "probe"}]) == "Recovered before submission"
    assert len(calls) == 2 and all(request.method == "POST" for request in calls)


@pytest.mark.parametrize("error_type", [
    httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.WriteTimeout,
])
def test_ambiguous_transport_failure_never_submits_a_second_generation(tmp_path, monkeypatch, error_type):
    monkeypatch.setattr("app.providers.nvidia.time.sleep", lambda _: None)
    calls = []

    def handler(request):
        calls.append(request)
        raise error_type("private transport diagnostics after possible submission", request=request)

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError) as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert len(calls) == 1
    assert caught.value.code == ("timeout" if issubclass(error_type, httpx.TimeoutException) else "connection")
    assert "private" not in str(caught.value) and provider.live_verified is False


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_server_error_never_automatically_duplicates_a_possible_generation(tmp_path, status):
    calls = []
    identifier = "0d5919a3-e790-46bb-80c6-5c8f43830316"

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"NVCF-REQID": identifier}, json={"error": "private upstream body"})

    provider = adapter(tmp_path, handler)
    with pytest.raises(ProviderError) as caught:
        provider.complete([{"role": "user", "content": "probe"}])
    assert len(calls) == 1 and caught.value.status_code == status
    assert provider.last_http_status == status and provider.last_request_id == identifier
    assert "private" not in str(caught.value)
    if status == 504:
        assert "HTTP 504" in str(caught.value) and "gateway timeout" in str(caught.value)


@pytest.mark.parametrize("header", [
    "https://untrusted.invalid/private-value", "private\r\nINJECTED", "x" * 500,
    "0d5919a3e79046bb80c65c8f43830316", "not-a-uuid",
])
def test_only_canonical_request_uuid_can_enter_safe_diagnostics(tmp_path, caplog, header):
    def handler(request):
        return httpx.Response(200, headers={"NVCF-REQID": header, "x-request-id": "private-other-header"},
                              json=completed("Safe final response"))

    provider = adapter(tmp_path, handler)
    with caplog.at_level("INFO", logger="replaylab.provider"):
        assert provider.complete([{"role": "user", "content": "probe"}]) == "Safe final response"
    assert provider.last_request_id is None and provider.last_http_status == 200
    assert header not in caplog.text and "private-other-header" not in caplog.text
    assert provider._api_key not in caplog.text


def test_safe_request_diagnostics_reset_before_each_completion(tmp_path, caplog):
    identifier = "0D5919A3-E790-46BB-80C6-5C8F43830316"
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, headers={"NVCF-REQID": identifier}, json=completed("First"))
        if len(calls) == 2:
            return httpx.Response(200, json=completed("No transport identifier"))
        raise httpx.ReadTimeout("private network data", request=request)

    provider = adapter(tmp_path, handler)
    with caplog.at_level("INFO", logger="replaylab.provider"):
        assert provider.complete([{"role": "user", "content": "probe"}]) == "First"
    assert provider.last_request_id == identifier.lower() and provider.last_http_status == 200
    assert identifier.lower() in caplog.text
    assert provider.complete([{"role": "user", "content": "probe"}]) == "No transport identifier"
    assert provider.last_request_id is None and provider.last_http_status == 200
    with pytest.raises(ProviderError, match="timed out"):
        provider.complete([{"role": "user", "content": "probe"}])
    assert provider.last_request_id is None and provider.last_http_status is None
    assert provider.last_response_id is None and provider.last_usage == {}
