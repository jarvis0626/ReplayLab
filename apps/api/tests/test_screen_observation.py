import io
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from PIL import Image

from app.digital_schemas import ScreenElement, ScreenObservation
from app.services.screen_observation import clear_screen_cache, observe_screen, redact_screenshot, redact_text


def image_bytes():
    image = np.full((600, 1000, 3), 245, np.uint8)
    for y, text in [
        (70, "Visual Studio Code"),
        (160, "Extensions"),
        (250, "Search extensions"),
        (340, "Prettier - Code formatter"),
        (440, "Installed"),
    ]:
        cv2.putText(image, text, (35, y), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (15, 15, 15), 2, cv2.LINE_AA)
    return cv2.imencode(".png", image)[1].tobytes()


@pytest.fixture(autouse=True)
def clean_cache():
    clear_screen_cache()
    yield
    clear_screen_cache()


def test_real_local_ocr_reads_generated_pixel_screenshot_without_cloud(monkeypatch):
    import httpx

    def no_cloud(*args, **kwargs):
        raise AssertionError("Local screenshot OCR must not call a cloud provider.")

    monkeypatch.setattr(httpx.Client, "request", no_cloud)
    observation = observe_screen(image_bytes(), "mock")
    assert "Extensions" in observation.visible_text
    assert "Installed" in observation.visible_text
    assert observation.provider_mode == "local_ocr"
    assert observation.provenance["real_ocr"] is True
    assert observation.provenance["screenshots_stored"] is False
    assert all(element.bbox is not None for element in observation.elements)
    assert observation.complete is False


def test_local_ocr_cache_returns_detached_sanitized_results():
    content = image_bytes()
    first = observe_screen(content)
    first.elements[0].text = "Caller mutation"
    second = observe_screen(content)
    assert second.provenance["cache_hit"] is True
    assert "Caller mutation" not in second.visible_text
    assert second.elements[0].text != "Caller mutation"


def test_redaction_scrubs_email_and_key_like_text():
    private = "mail user@example.invalid api_key=not-a-real-secret123 sk-fake-test-key12345"
    result = redact_text(private)
    assert "user@example.invalid" not in result
    assert "not-a-real-secret123" not in result
    assert "sk-fake-test-key12345" not in result


def test_meta_receives_masked_pixels_and_only_sanitized_ocr(monkeypatch):
    output = SimpleNamespace(
        txts=["user@example.invalid", "Extensions"],
        boxes=np.array(
            [[[20, 20], [300, 20], [300, 80], [20, 80]], [[20, 120], [300, 120], [300, 180], [20, 180]]]
        ),
        scores=[0.99, 0.99],
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)

    class FakeMeta:
        def observe(self, redacted, local):
            assert "user@example.invalid" not in local.model_dump_json()
            with Image.open(io.BytesIO(redacted)) as image:
                assert image.getpixel((100, 50)) == (0, 0, 0)
                assert image.getpixel((900, 500)) == (245, 245, 245)
            return local.model_copy(update={"provider_mode": "meta"})

    result = observe_screen(image_bytes(), "meta", FakeMeta(), cloud_consent=True)
    assert result.provider_mode == "meta"
    assert result.provenance["redacted_regions"] == 1


def test_meta_requires_explicit_consent_before_any_ocr_or_network(monkeypatch):
    monkeypatch.setattr(
        "app.services.screen_observation._get_ocr", lambda: pytest.fail("OCR should not start before consent")
    )
    with pytest.raises(ValueError, match="consent"):
        observe_screen(image_bytes(), "meta", object())


def test_missing_privacy_scan_blocks_cloud_without_silent_mock(monkeypatch):
    def unavailable():
        raise ImportError("Missing local OCR")

    monkeypatch.setattr("app.services.screen_observation._get_ocr", unavailable)
    with pytest.raises(ValueError, match="privacy OCR scan"):
        observe_screen(image_bytes(), "meta", object(), cloud_consent=True)


def test_secret_without_bbox_blocks_cloud_redaction():
    observation = ScreenObservation(
        elements=[ScreenElement(text="[REDACTED_EMAIL]", source="local_ocr:redacted")]
    )
    with pytest.raises(ValueError, match="no region"):
        redact_screenshot(image_bytes(), observation)


def test_explicit_demo_interface_header_yields_observed_version(monkeypatch):
    output = SimpleNamespace(
        txts=["CodeLab 1.0"], boxes=np.array([[[20, 20], [300, 20], [300, 80], [20, 80]]]), scores=[0.99]
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)
    assert observe_screen(image_bytes()).interface_version == "CodeLab 1.0"


@pytest.mark.parametrize(
    "text",
    [
        "CodeLab 2.0 practice-workspace",
        "practice-workspace CodeLab 2.0 SIMULATED WORKSPACE",
        "CodeLab2.0 | Sandbox simulation - no system changes",
        "Interface version: CodeLab 2.0 practice-workspace",
    ],
)
def test_merged_header_extracts_bounded_visible_version(monkeypatch, text):
    output = SimpleNamespace(
        txts=[text], boxes=np.array([[[20, 20], [900, 20], [900, 80], [20, 80]]]), scores=[0.99]
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)
    observation = observe_screen(image_bytes())
    assert observation.interface_version == "CodeLab 2.0"
    assert observation.provenance["interface_version_ambiguous"] is False


def test_low_confidence_merged_version_is_not_promoted_to_interface_evidence(monkeypatch):
    output = SimpleNamespace(
        txts=["CodeLab 2.0 practice-workspace"],
        boxes=np.array([[[20, 20], [900, 20], [900, 80], [20, 80]]]),
        scores=[0.5],
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)
    assert observe_screen(image_bytes()).interface_version is None


@pytest.mark.parametrize("same_line", [True, False])
def test_conflicting_reliable_versions_remain_unknown(monkeypatch, same_line):
    texts = ["CodeLab 1.0 practice-workspace CodeLab 2.0"] if same_line else ["CodeLab 1.0", "CodeLab 2.0 practice-workspace"]
    output = SimpleNamespace(
        txts=texts,
        boxes=np.array([[[20, 20], [900, 20], [900, 80], [20, 80]]] * len(texts)),
        scores=[0.99] * len(texts),
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)
    observation = observe_screen(image_bytes())
    assert observation.interface_version is None
    assert observation.provenance["interface_version_ambiguous"] is True


def test_version_token_boundaries_do_not_match_a_different_name_or_suffix(monkeypatch):
    output = SimpleNamespace(
        txts=["MyCodeLab 2.0 CodeLab 2.0preview"],
        boxes=np.array([[[20, 20], [900, 20], [900, 80], [20, 80]]]),
        scores=[0.99],
    )
    monkeypatch.setattr("app.services.screen_observation._get_ocr", lambda: lambda image: output)
    assert observe_screen(image_bytes()).interface_version is None


def test_redaction_uses_oriented_ocr_coordinates_and_strips_metadata():
    image = Image.new("RGB", (120, 240), "white")
    exif = image.getexif()
    exif[274] = 6
    encoded = io.BytesIO()
    image.save(encoded, format="JPEG", exif=exif)
    observation = ScreenObservation(
        elements=[
            ScreenElement(text="[REDACTED_EMAIL]", bbox=(0.1, 0.1, 0.9, 0.3), source="local_ocr:redacted")
        ]
    )
    redacted = redact_screenshot(encoded.getvalue(), observation)
    with Image.open(io.BytesIO(redacted)) as result:
        assert result.size == (240, 120)
        assert result.getpixel((120, 24)) == (0, 0, 0)
        assert 274 not in result.getexif()
