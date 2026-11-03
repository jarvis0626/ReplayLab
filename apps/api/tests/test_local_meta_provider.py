"""Local Meta isolation and OCR-grounding contracts; no real model requests."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

from app.digital_schemas import ScreenElement, ScreenObservation
from app.providers.local_meta import LOCAL_META_MODEL, LocalMetaProvider, LocalMetaScreenProvider
from app.providers.meta import ProviderError


def completed(content="OK", **extra):
    return {"id": "local-test-response", "model": LOCAL_META_MODEL,
        "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}, **extra}


def provider(tmp_path, handler, **kwargs):
    return LocalMetaProvider(tmp_path / "cache", client=httpx.Client(transport=httpx.MockTransport(handler)), **kwargs)


def ocr(*texts):
    return ScreenObservation(elements=[ScreenElement(text=text, role="window" if "Marketplace" in text else "text",
        bbox=(.1, .2, .8, .4), confidence=.93, source="local_ocr") for text in texts],
        visible_text="\n".join(texts), confidence=.93, image_quality=.95, provider_mode="local_ocr",
        provenance={"ocr_available": True, "real_ocr": True, "redaction_applied": True})


def selection(evidence_ids=None, **extra):
    return {"evidence_ids": evidence_ids if evidence_ids is not None else ["O1"],
            "visible_application_id": None, "current_window_id": "O1", **extra}


def workflow(**step_extra):
    return {"title": "Open Extensions", "description": "Review the supplied OCR checkpoint.", "interface_version": None,
        "steps": [{"id": "open", "title": "Open Extensions", "description": "Review the Extensions Marketplace panel.",
            "dependencies": [], "timestamp_start": 0, "timestamp_end": 3, "expected_state": "Extensions Marketplace",
            "screen_rules": [{"id": "panel", "kind": "window", "expected": "Extensions Marketplace",
                "alternatives": [], "contradictions": [], "description": "Check the visible panel title."}], **step_extra}]}


@pytest.mark.parametrize("base_url", [
    "https://127.0.0.1:8083/v1", "http://example.com/v1", "http://127.0.0.1.example.com/v1",
    "http://127.0.0.1@evil.invalid/v1", "http://secret@127.0.0.1:8083/v1",
    "http://localhost:8083/v1?api_key=secret", "http://localhost:8083/v1#fragment",
    "http://127.0.0.1:8083/v1/other", "http://127.0.0.1:99999/v1", "file:///v1",
])
def test_nonloopback_or_credentialed_model_urls_are_rejected_before_any_request(tmp_path, base_url):
    calls = []
    with pytest.raises(ValueError, match="HTTP loopback"):
        provider(tmp_path, lambda request: calls.append(request), base_url=base_url)
    assert calls == []


@pytest.mark.parametrize("base_url", ["http://127.0.0.1:8083/v1", "http://localhost:8083/v1/", "http://[::1]:8083/v1"])
def test_text_request_is_local_and_uses_no_cloud_credential_or_cookie(tmp_path, base_url, caplog):
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host in {"127.0.0.1", "localhost", "::1"}
        assert request.url.path == "/v1/chat/completions"
        assert "Authorization" not in request.headers and "Cookie" not in request.headers
        body = json.loads(request.content)
        assert body["model"] == LOCAL_META_MODEL and body["max_tokens"] == 512 and body["stream"] is False
        assert isinstance(body["messages"][0]["content"], str)
        return httpx.Response(200, json=completed())

    client = httpx.Client(transport=httpx.MockTransport(handler), auth=("private-user", "private-pass"),
        headers={"Authorization": "Bearer private-cloud-key"}, cookies={"session": "private-cookie"})
    adapter = LocalMetaProvider(tmp_path / "cache", client=client, base_url=base_url)
    with caplog.at_level("INFO", logger="replaylab.provider"):
        assert adapter.complete([{"role": "user", "content": "private text evidence"}]) == "OK"
    assert adapter.live_verified and adapter.last_model == LOCAL_META_MODEL
    assert adapter.last_usage == {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}
    assert len(requests) == 1 and adapter._api_key == ""
    assert "private" not in caplog.text


def test_owned_http_client_disables_environment_proxies(tmp_path, monkeypatch):
    actual_client = httpx.Client
    options = []

    def factory(**kwargs):
        options.append(kwargs)
        return actual_client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=completed())), **kwargs)

    monkeypatch.setattr("app.providers.local_meta.httpx.Client", factory)
    adapter = LocalMetaProvider(tmp_path / "cache")
    assert adapter.complete([{"role": "user", "content": "probe"}]) == "OK"
    assert options == [{"trust_env": False, "follow_redirects": False}]


def test_local_server_redirect_never_sends_evidence_to_another_host(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "https://untrusted.invalid/collect"})

    adapter = provider(tmp_path, handler)
    with pytest.raises(ProviderError, match="redirect"):
        adapter.complete([{"role": "user", "content": "private OCR evidence"}])
    assert len(requests) == 1 and requests[0].url.host == "127.0.0.1"


@pytest.mark.parametrize("failure", [429, 500, 503, httpx.ReadTimeout, httpx.RemoteProtocolError])
def test_failures_are_safe_terminal_and_never_resubmitted(tmp_path, failure):
    requests = []

    def handler(request):
        requests.append(request)
        if isinstance(failure, int):
            return httpx.Response(failure, json={"error": "private upstream text"})
        raise failure("private network error", request=request)

    adapter = provider(tmp_path, handler)
    with pytest.raises(ProviderError) as caught:
        adapter.complete([{"role": "user", "content": "probe"}])
    assert len(requests) == 1 and "private" not in str(caught.value)
    assert adapter.live_verified is False


@pytest.mark.parametrize("response_model", [None, "meta/muse-glimmer-30b", "Llama-3.2-3B-Instruct"])
def test_response_must_identify_the_exact_configured_local_model_alias(tmp_path, response_model):
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(model=response_model)))
    with pytest.raises(ProviderError, match="invalid final"):
        adapter.complete([{"role": "user", "content": "probe"}])
    assert adapter.last_model is None and adapter.live_verified is False


@pytest.mark.parametrize("content", [
    [{"type": "image_url", "image_url": {"url": "https://untrusted.invalid/image"}}],
    [{"type": "input_image", "image_url": "data:image/png;base64,SECRET"}],
    [{"type": "input_file", "file_id": "file-secret"}],
])
def test_text_only_adapter_never_transmits_images_or_files(tmp_path, content):
    requests = []
    adapter = provider(tmp_path, lambda request: requests.append(request))
    with pytest.raises(ProviderError, match="text"):
        adapter._structured(content, {}, "NoMedia", "Observe")
    with pytest.raises(ProviderError, match="text only"):
        adapter.complete([{"role": "user", "content": content}])
    assert requests == []


@pytest.mark.parametrize("content", ["not-json", "[]", '{"incomplete":', '```json\n{"value":1}\n```'])
def test_invalid_or_wrapped_json_never_becomes_model_evidence(tmp_path, content):
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(content)))
    with pytest.raises(ProviderError, match="invalid structured JSON"):
        adapter._structured([{"type": "text", "text": "probe"}], {}, "Contract", "Observe")


def test_screen_ids_ground_every_label_box_and_confidence_in_actual_ocr(tmp_path):
    source = ocr("Extensions Marketplace", "Install")
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert "image_url" not in request.content.decode() and "base64" not in request.content.decode()
        schema = body["response_format"]["json_schema"]["schema"]
        assert schema["properties"]["evidence_ids"]["items"]["enum"] == ["O1", "O2"]
        assert schema["properties"]["evidence_ids"]["maxItems"] == 8
        return httpx.Response(200, json=completed(json.dumps(selection(["O1", "O2"]))))

    adapter = provider(tmp_path, handler)
    observation = LocalMetaScreenProvider(adapter).observe(b"raw image bytes must stay here", source)
    assert len(requests) == 1 and b"raw image bytes" not in requests[0].content
    assert [item.text for item in observation.elements] == [item.text for item in source.elements]
    assert [item.bbox for item in observation.elements] == [item.bbox for item in source.elements]
    assert [item.confidence for item in observation.elements] == [.93, .93]
    assert [item.role for item in observation.elements] == [item.role for item in source.elements]
    assert observation.complete is False and observation.provider_mode == "local_meta"
    assert observation.provenance["local_only"] is True and observation.provenance["vision_inference"] is False
    assert observation.provenance["response_model"] == LOCAL_META_MODEL


@pytest.mark.parametrize("plan", [
    selection(["O99"]),
    selection(["O1", "O1"]),
    selection([{"id": "O1", "role": "selection"}]),
    selection(confidence=1),
    selection(current_window_id="O99"),
    selection(status="pass"),
])
def test_unknown_ids_invented_confidence_and_completion_claims_are_rejected(tmp_path, plan):
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(plan))))
    with pytest.raises(ProviderError, match="invalid OCR evidence"):
        LocalMetaScreenProvider(adapter).observe(b"image", ocr("Extensions Marketplace"))


def test_model_cannot_raise_unknown_ocr_confidence_or_change_a_role(tmp_path):
    source = ocr("Install")
    source.elements[0].confidence = None
    source.confidence = None
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(selection(["O1"])))))
    observed = LocalMetaScreenProvider(adapter).observe(b"image", source)
    assert observed.elements[0].confidence is None and observed.confidence is None
    assert observed.elements[0].role == source.elements[0].role


def test_ninth_selected_fact_is_rejected_even_when_every_id_exists(tmp_path):
    source = ocr(*[f"Fact {index}" for index in range(9)])
    plan = selection([f"O{index}" for index in range(1, 10)])
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(plan))))
    with pytest.raises(ProviderError, match="invalid OCR evidence"):
        LocalMetaScreenProvider(adapter).observe(b"image", source)


def test_meta_focus_cannot_discard_qualified_ocr_required_by_a_rule(tmp_path):
    from app.digital_schemas import ScreenRule
    from app.schemas import Step
    from app.services.digital_verification import verify_screen

    source = ocr("Help", "Extensions Marketplace")
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(selection(["O1"], current_window_id=None)))))
    observed = LocalMetaScreenProvider(adapter).observe(b"image", source)
    step = Step(id="open", title="Open Extensions", screen_rules=[ScreenRule(id="panel", kind="window", expected="Extensions Marketplace")])
    result = verify_screen(step, observed)
    assert result.status == "pass"
    assert observed.elements == source.elements
    assert observed.provenance["ocr_selected_count"] == 1
    assert observed.provenance["ocr_fact_count"] == 2
    assert observed.provenance["meta_focus_labels"] == ["Help"]


def test_meta_focus_cannot_hide_qualified_ocr_counterevidence(tmp_path):
    from app.digital_schemas import ScreenRule
    from app.schemas import Step
    from app.services.digital_verification import verify_screen

    source = ocr("Extensions", "Error: Connection failed")
    source.elements[1].role = "error"
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(selection(["O1"], current_window_id=None)))))
    observed = LocalMetaScreenProvider(adapter).observe(b"image", source)
    step = Step(id="open", title="Open Extensions", screen_rules=[
        ScreenRule(id="panel", kind="text_present", expected="Extensions"),
        ScreenRule(id="safe", kind="error_absent", expected="No errors"),
    ])
    result = verify_screen(step, observed)
    assert result.status == "fail"
    assert observed.elements == source.elements
    assert observed.provenance["meta_focus_labels"] == ["Extensions"]


def test_workflow_uses_locally_ocrd_frame_text_without_sending_media(tmp_path, monkeypatch):
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"private raw tutorial frame bytes")
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda data: ocr("Extensions Marketplace"))
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert body["max_tokens"] == 2048
        assert "Extensions Marketplace" in body["messages"][1]["content"]
        assert b"private raw tutorial frame" not in request.content
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["schema"]["properties"]["interface_version"] == {"type": "null"}
        return httpx.Response(200, json=completed(json.dumps(workflow())))

    adapter = provider(tmp_path, handler)
    task = adapter.extract_workflow({"video": {"duration": 5}}, [{"id": "frame", "path": str(frame), "timestamp": 3}])
    assert len(requests) == 1 and task.modality == "digital" and task.provider_mode == "local_meta"
    assert task.steps[0].reference_frame_id == "frame" and task.provenance["requires_approval"] is True
    assert task.provenance["source_frame_count"] == 1 and task.provenance["vision_inference"] is False


def test_workflow_model_cannot_turn_a_panel_title_into_an_interface_version(tmp_path):
    proposal = {**workflow(), "interface_version": "Extensions Marketplace"}
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(proposal))))
    project = {"tutorial": {"transcript_segments": [{"start": 0, "end": 4, "text": "Open Extensions Marketplace."}]}}
    with pytest.raises(ProviderError, match="invalid workflow"):
        adapter.extract_workflow(project, [])


@pytest.mark.parametrize("field", ["expected", "alternatives", "contradictions"])
def test_workflow_rejects_rule_labels_not_quoted_in_actual_source(tmp_path, field):
    proposal = workflow()
    proposal["steps"][0]["screen_rules"][0][field] = "Invented Panel" if field == "expected" else ["Invented Panel"]
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(proposal))))
    project = {"tutorial": {"transcript_segments": [{"start": 0, "end": 4, "text": "Open Extensions Marketplace."}]}}
    with pytest.raises(ProviderError, match="invalid workflow"):
        adapter.extract_workflow(project, [])


@pytest.mark.parametrize("versions,ambiguous,expected", [
    (["CodeLab 1.3"], False, "CodeLab 1.3"),
    (["CodeLab 1.3", "CodeLab 1.4"], False, None),
    (["CodeLab 1.3"], True, None),
])
def test_workflow_version_comes_only_from_unique_nonambiguous_actual_frame_ocr(tmp_path, monkeypatch, versions, ambiguous, expected):
    frames = []
    observations = {}
    for index, version in enumerate(versions):
        frame = tmp_path / f"frame-{index}.png"
        frame.write_bytes(str(index).encode())
        observations[frame.read_bytes()] = ocr("Extensions Marketplace")
        observations[frame.read_bytes()].interface_version = version
        observations[frame.read_bytes()].provenance["interface_version_ambiguous"] = ambiguous
        frames.append({"id": f"frame-{index}", "path": str(frame), "timestamp": index + 3})
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda data: observations[data])
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(workflow()))))
    task = adapter.extract_workflow({"video": {"duration": 6}}, frames)
    assert task.interface_version == expected
    assert task.provenance["interface_version_source"] == ("local_frame_ocr" if expected else None)


@pytest.mark.parametrize("step_extra", [{"dependencies": ["unknown"]}, {"timestamp_end": 50}, {"screen_rules": []}])
def test_invalid_workflow_dependencies_timestamps_or_empty_rules_are_rejected(tmp_path, step_extra):
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(workflow(**step_extra)))))
    project = {"tutorial": {"transcript_segments": [{"start": 0, "end": 4, "text": "Open Extensions Marketplace."}]}}
    with pytest.raises(ProviderError, match="invalid workflow"):
        adapter.extract_workflow(project, [])


def test_missing_source_never_causes_a_model_request(tmp_path):
    requests = []
    adapter = provider(tmp_path, lambda request: requests.append(request))
    with pytest.raises(ProviderError) as caught:
        adapter.extract_workflow({}, [])
    assert caught.value.code == "missing_source" and requests == []


def test_workflow_repeated_frame_text_keeps_first_timestamp_and_new_evidence(tmp_path, monkeypatch):
    frames, observations, requests = [], {}, []
    for index, labels in enumerate([
        ["Extensions Marketplace", "Preferences"],
        ["Extensions Marketplace", "Preferences", "Search results"],
    ]):
        path = tmp_path / f"source-{index}.png"
        path.write_bytes(str(index).encode())
        observations[path.read_bytes()] = ocr(*labels)
        frames.append({"id": str(index), "path": str(path), "timestamp": index + 1})
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda value: observations[value])

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=completed(json.dumps(workflow())))

    task = provider(tmp_path, handle).extract_workflow({"video": {"duration": 6}}, frames)
    source = requests[0]["messages"][1]["content"]
    assert source.count('"Extensions Marketplace"') == 1
    assert 'Frame OCR at 1.000: ["Extensions Marketplace", "Preferences"]' in source
    assert 'Frame OCR at 2.000: ["Search results"]' in source
    assert task.provenance["source_frame_count"] == 2


def test_workflow_reference_prefers_its_interval_over_next_action(tmp_path, monkeypatch):
    frames = []
    for index, timestamp in enumerate([3.0, 6.1]):
        path = tmp_path / f"source-{index}.png"
        path.write_bytes(str(index).encode())
        frames.append({"id": f"frame-{index}", "path": str(path), "timestamp": timestamp})
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda value: ocr("Extensions Marketplace"))
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(
        workflow(timestamp_start=0, timestamp_end=6)))))
    task = adapter.extract_workflow({"video": {"duration": 8}}, frames)
    assert task.steps[0].reference_frame_id == "frame-0"


def test_workflow_reference_without_a_frame_in_interval_uses_nearest_end(tmp_path, monkeypatch):
    path = tmp_path / "source.png"
    path.write_bytes(b"frame")
    monkeypatch.setattr("app.services.screen_observation._local_observation", lambda value: ocr("Extensions Marketplace"))
    adapter = provider(tmp_path, lambda request: httpx.Response(200, json=completed(json.dumps(
        workflow(timestamp_start=0, timestamp_end=1)))))
    task = adapter.extract_workflow({"video": {"duration": 8}},
        [{"id": "available", "path": str(path), "timestamp": 5}])
    assert task.steps[0].reference_frame_id == "available"


def test_diagnostics_belong_to_each_concurrent_calling_worker(tmp_path):
    barrier = threading.Barrier(2)

    def handler(request):
        text = json.loads(request.content)["messages"][0]["content"]
        barrier.wait(timeout=5)
        return httpx.Response(200, json=completed(text, id="id-" + text,
            usage={"prompt_tokens": 10 if text == "first" else 20}))

    adapter = provider(tmp_path, handler)

    def run(text):
        result = adapter.complete([{"role": "user", "content": text}])
        return result, adapter.last_response_id, adapter.last_usage, adapter.last_model

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(run, ["first", "second"]))
    assert first == ("first", "id-first", {"prompt_tokens": 10}, LOCAL_META_MODEL)
    assert second == ("second", "id-second", {"prompt_tokens": 20}, LOCAL_META_MODEL)
    assert adapter.last_response_id is None and adapter.live_verified is True
