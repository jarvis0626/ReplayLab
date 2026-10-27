"""Ephemeral screen OCR and best-effort redaction before optional cloud vision.

Only sanitized observations are held in a small in-memory cache. Screenshots,
recognized private text, and credentials are never written or logged here.
"""

from __future__ import annotations

import hashlib
import io
import re
import threading
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from app.digital_schemas import ScreenElement, ScreenObservation
from app.services.media import decode_image

_EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", re.ASCII)
_KEY = re.compile(
    r"\b(?:(?:sk|pk|ghp|gho|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{8,}|AKIA[A-Z0-9]{12,}|AIza[A-Za-z0-9_-]{20,})\b"
)
_ASSIGNED_SECRET = re.compile(
    r"\b(?:api[ _-]?key|access[ _-]?token|secret|password|authorization|bearer)\s*[:=]\s*[\"']?[^\s\"']{6,}",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/-]{8,}", re.IGNORECASE)
_LONG_TOKEN = re.compile(r"\b(?=[A-Za-z0-9_-]{32,}\b)(?=[A-Za-z0-9_-]*[0-9])[A-Za-z0-9_-]{32,}\b")
_lock = threading.RLock()
_engine = None
_cache: OrderedDict[str, ScreenObservation] = OrderedDict()


def clear_screen_cache():
    with _lock:
        _cache.clear()
    from app.providers.meta_screen import clear_meta_screen_cache

    clear_meta_screen_cache()


def redact_text(text: str) -> str:
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _KEY.sub("[REDACTED_KEY]", text)
    text = _ASSIGNED_SECRET.sub("[REDACTED_SECRET]", text)
    text = _BEARER.sub("[REDACTED_SECRET]", text)
    return _LONG_TOKEN.sub("[REDACTED_TOKEN]", text)


def is_coach_capture(text: str) -> bool:
    folded = re.sub(r"\s+", " ", text.casefold())
    return "replaylab" in folded and any(
        phrase in folded
        for phrase in (
            "current step",
            "upcoming step",
            "live coach",
            "screen assistant",
            "reference state",
            "share screen",
        )
    )


def _get_ocr():
    global _engine
    if _engine is None:
        import rapidocr
        from rapidocr import RapidOCR

        models = Path(rapidocr.__file__).parent / "models"
        paths = {
            "Det.model_path": models / "PP-OCRv6_det_small.onnx",
            "Cls.model_path": models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx",
            "Rec.model_path": models / "PP-OCRv6_rec_small.onnx",
        }
        if not all(path.is_file() for path in paths.values()):
            raise RuntimeError("The local OCR model files are missing.")
        _engine = RapidOCR(
            params={
                **{name: str(path) for name, path in paths.items()},
                "Global.log_level": "critical",
                "Global.max_side_len": 2000,
                "EngineConfig.onnxruntime.intra_op_num_threads": 2,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            }
        )
    return _engine


def _role(text: str) -> str:
    # Navigation labels such as Settings or Error Lens do not establish an
    # active pane or failure. Only explicit visible labels create these roles.
    if re.match(
        r"^(?:error\s*:|installation failed\b|access denied\b|permission denied\b|download failed\b|unexpected error\b)",
        text,
        re.IGNORECASE,
    ):
        return "error"
    if re.match(
        r"^(?:dialog\s*:|permission required\b|confirm installation\b|restart required\b)",
        text,
        re.IGNORECASE,
    ):
        return "dialog"
    for prefix, role in (
        ("window:", "window"),
        ("path:", "path"),
        ("selected:", "selection"),
        ("selection:", "selection"),
        ("button:", "button"),
    ):
        if text.casefold().startswith(prefix):
            return role
    if re.match(r"^(?:[A-Za-z]:[\\/]|/(?:home|Users|usr|opt|tmp)/)", text):
        return "path"
    return "text"


def _quality(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # A screenshot may be largely white or black; camera exposure heuristics
    # are inappropriate. Require contrast and sharp visible detail instead.
    contrast = float(gray.std())
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return round(min(1.0, contrast / 12, sharpness / 25), 3)


def _local_observation(image_bytes: bytes) -> ScreenObservation:
    image = decode_image(image_bytes)
    digest = hashlib.sha256(image_bytes).hexdigest()
    with _lock:
        if digest in _cache:
            value = _cache.pop(digest)
            _cache[digest] = value
            result = value.model_copy(deep=True)
            result.provenance["cache_hit"] = True
            return result
        try:
            output = _get_ocr()(image)
        except (ImportError, RuntimeError, OSError, ValueError):
            return ScreenObservation(
                image_quality=_quality(image),
                provider_mode="local_ocr",
                provenance={
                    "engine": "rapidocr",
                    "ocr_available": False,
                    "real_ocr": False,
                    "reason": "Local OCR is unavailable. Install the pinned OCR dependencies and bundled models.",
                    "redaction_applied": False,
                    "screenshots_stored": False,
                },
            )
        height, width = image.shape[:2]
        elements = []
        redacted_count = 0
        texts = output.txts if output.txts is not None else []
        boxes = output.boxes if output.boxes is not None else []
        scores = output.scores if output.scores is not None else []
        for raw_text, box, score in list(zip(texts, boxes, scores))[:500]:
            text = str(raw_text).strip()
            if not text:
                continue
            sanitized = redact_text(text)
            private = sanitized != text
            redacted_count += int(private)
            xs, ys = np.asarray(box)[:, 0], np.asarray(box)[:, 1]
            bbox = (
                max(0.0, float(min(xs)) / width),
                max(0.0, float(min(ys)) / height),
                min(1.0, float(max(xs)) / width),
                min(1.0, float(max(ys)) / height),
            )
            if bbox[0] >= bbox[2] or bbox[1] >= bbox[3]:
                continue
            confidence = float(score) if score is not None and np.isfinite(score) else None
            elements.append(
                ScreenElement(
                    text=sanitized[:4000],
                    role=_role(sanitized),
                    bbox=bbox,
                    confidence=confidence,
                    source="local_ocr:redacted" if private else "local_ocr",
                )
            )
        visible_text = "\n".join(item.text for item in elements)
        known_scores = [item.confidence for item in elements if item.confidence is not None]
        version_text = None
        for item in elements:
            if item.confidence is None or item.confidence < 0.75:
                continue
            version = re.search(r"\binterface version\s*[:=]\s*([^\n]{1,120})", item.text, re.IGNORECASE)
            code_lab = re.fullmatch(r"CodeLab\s*(\d+(?:\.\d+){1,3})", item.text, re.IGNORECASE)
            if version:
                version_text = version.group(1).strip()
                break
            if code_lab:
                version_text = "CodeLab " + code_lab.group(1)
                break
        result = ScreenObservation(
            elements=elements,
            visible_text=visible_text,
            confidence=sum(known_scores) / len(known_scores) if known_scores else None,
            image_quality=_quality(image),
            provider_mode="local_ocr",
            interface_version=version_text,
            complete=False,
            provenance={
                "engine": "rapidocr-3.10.0/onnxruntime",
                "ocr_available": True,
                "real_ocr": True,
                "fixture": False,
                "cache_hit": False,
                "redaction_applied": True,
                "redacted_regions": redacted_count,
                "screenshots_stored": False,
                "self_capture": is_coach_capture(visible_text),
                "quality_source": "Screenshot contrast and sharpness heuristic; not calibrated model confidence",
                "redaction_limits": "Best effort for detected email addresses and key-like text; review the selected sharing scope.",
            },
        )
        _cache[digest] = result.model_copy(deep=True)
        while len(_cache) > 16:
            _cache.popitem(last=False)
        return result


def redact_screenshot(image_bytes: bytes, observation: ScreenObservation) -> bytes:
    """Black out entire detected private text lines, then strip image metadata."""
    with Image.open(io.BytesIO(image_bytes)) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for element in observation.elements:
        if "[REDACTED" not in element.text and "redacted" not in element.source:
            continue
        if element.bbox is None:
            # A secret without coordinates cannot safely be removed selectively.
            raise ValueError("Sensitive text has no region for screenshot redaction.")
        x1, y1, x2, y2 = element.bbox
        draw.rectangle(
            (
                max(0, int(x1 * width) - 4),
                max(0, int(y1 * height) - 4),
                min(width, int(x2 * width) + 4),
                min(height, int(y2 * height) + 4),
            ),
            fill="black",
        )
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def observe_screen(
    image_bytes: bytes, mode: str = "mock", meta_provider=None, *, cloud_consent: bool = False
) -> ScreenObservation:
    if mode not in {"mock", "meta"}:
        raise ValueError("Screen provider mode must be mock or meta.")
    if mode == "meta" and not cloud_consent:
        raise ValueError("Explicit cloud consent is required before sending screen content to Meta.")
    local = _local_observation(image_bytes)
    if mode == "mock":
        return local
    if meta_provider is None:
        raise ValueError("A configured Meta screenshot provider is required; no mock fallback is selected.")
    if not local.provenance.get("ocr_available"):
        raise ValueError("The privacy OCR scan is unavailable; no screenshot was sent to Meta.")
    if local.provenance.get("self_capture"):
        return local
    redacted = redact_screenshot(image_bytes, local)
    return meta_provider.observe(redacted, local)


screenobserve = observe_screen
