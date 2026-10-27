import json
from uuid import uuid4

import httpx
import pytest

from app.digital_schemas import ScreenElement, ScreenObservation
from app.providers.meta import MetaProvider, ProviderError
from app.providers.meta_screen import MetaScreenProvider, clear_meta_screen_cache


def local():
    return ScreenObservation(
        elements=[ScreenElement(text="Extensions", confidence=0.99, source="local_ocr")],
        visible_text="Extensions",
        confidence=0.99,
        image_quality=1,
        provider_mode="local_ocr",
        provenance={"redaction_applied": True, "ocr_available": True, "screenshots_stored": False},
    )


def completed(elements):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"elements": elements})}],
            }
        ],
    }


def adapter(tmp_path, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = MetaProvider("test-screen-only-" + uuid4().hex, tmp_path / "unused-cache", client=client)
    return MetaScreenProvider(provider)


@pytest.fixture(autouse=True)
def clean_cache():
    clear_meta_screen_cache()
    yield
    clear_meta_screen_cache()


def test_screenshot_transport_uses_muse_image_block_and_no_sam_or_verdict(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert str(request.url).endswith("/responses")
        assert payload["model"] == "muse-spark-1.3" and payload["store"] is False
        image = payload["input"][0]["content"][1]
        assert image["type"] == "input_image" and image["image_url"].startswith("data:image/png;base64,")
        assert "untrusted evidence" in payload["instructions"]
        return httpx.Response(
            200,
            json=completed(
                [{"text": "Installed", "role": "text", "bbox": [0.1, 0.2, 0.5, 0.4], "confidence": 0.9}]
            ),
        )

    live = adapter(tmp_path, handler)
    result = live.observe(b"redacted-test-image", local())
    assert result.provider_mode == "meta" and result.complete is False
    assert "Installed" in result.visible_text and "Extensions" in result.visible_text
    assert len(calls) == 1
    assert not (tmp_path / "unused-cache").exists()


def test_unavailable_meta_does_not_fall_back_to_local_or_mock(tmp_path):
    live = adapter(tmp_path, lambda request: httpx.Response(403, json={"error": "not available"}))
    with pytest.raises(ProviderError, match="access"):
        live.observe(b"redacted-test-image", local())


def test_privacy_scan_is_required_for_direct_adapter_use(tmp_path):
    live = adapter(tmp_path, lambda request: pytest.fail("No request should be sent"))
    with pytest.raises(ProviderError, match="privacy scan"):
        live.observe(b"raw-image", ScreenObservation())


def test_model_returned_private_values_are_redacted_again(tmp_path):
    live = adapter(
        tmp_path,
        lambda request: httpx.Response(
            200,
            json=completed(
                [
                    {
                        "text": "account user@example.invalid",
                        "role": "text",
                        "bbox": None,
                        "confidence": None,
                    },
                ]
            ),
        ),
    )
    result = live.observe(b"redacted-test-image", local())
    assert "user@example.invalid" not in result.model_dump_json()
    assert "REDACTED_EMAIL" in result.visible_text


def test_ram_cache_avoids_repeated_network_calls_and_copies_results(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=completed([]))

    live = adapter(tmp_path, handler)
    first = live.observe(b"same-redacted-image", local())
    first.elements.clear()
    second = live.observe(b"same-redacted-image", local())
    assert second.provenance["cache_hit"] is True
    assert len(requests) == 1 and second.elements


def test_invalid_model_schema_cannot_be_used_as_screen_evidence(tmp_path):
    live = adapter(
        tmp_path,
        lambda request: httpx.Response(
            200,
            json=completed(
                [
                    {"text": "Installed", "role": "text", "bbox": [0.8, 0.1, 0.2, 0.4], "confidence": 1},
                ]
            ),
        ),
    )
    with pytest.raises(ProviderError, match="invalid screen observations"):
        live.observe(b"redacted-test-image", local())


def test_new_screenshots_are_rate_limited_per_account(tmp_path):
    live = adapter(tmp_path, lambda request: httpx.Response(200, json=completed([])))
    for index in range(10):
        live.observe(f"different-redacted-{index}".encode(), local())
    with pytest.raises(ProviderError) as failure:
        live.observe(b"eleventh-redacted-image", local())
    assert failure.value.code == "rate_limit"
