"""Bounded, network-free tutorial ingestion and editable transcript proposals.

Tutorial text is untrusted source evidence. This module never executes commands,
downloads media/captions, or treats transcript content as agent instructions.
"""

from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from app.schemas import Step, Task

MAX_TRANSCRIPT_CHARACTERS = 50_000
MAX_SEGMENTS = 50
MAX_TUTORIAL_SECONDS = 4 * 60 * 60
_TIMESTAMP = r"[0-9]{1,3}:[0-9]{2}(?::[0-9]{2})?(?:[.,][0-9]{1,3})?"
_RANGE = re.compile(
    rf"^(?P<open>\[)?(?P<start>{_TIMESTAMP})\s*(?:-->|[-–—])\s*"
    rf"(?P<end>{_TIMESTAMP})(?P<close>\])?\s*(?P<text>.*)$"
)
_POINT = re.compile(rf"^(?:\[(?P<bracket>{_TIMESTAMP})\]\s*|(?P<bare>{_TIMESTAMP})\s+)(?P<text>.*)$")
_EMPTY_POINT = re.compile(rf"^\[(?P<start>{_TIMESTAMP})\]\s*$")
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_QUOTES = re.compile(
    r""""([^"\n]{1,120})"|“([^”\n]{1,120})”|(?<!\w)'([^'\n]{1,120})'(?!\w)|`([^`\n]{1,120})`"""
)


class TutorialError(ValueError):
    def __init__(self, message: str, code: str = "invalid_tutorial"):
        super().__init__(message)
        self.code = code


def _seconds(value: str) -> float:
    fields = value.replace(",", ".").split(":")
    seconds = float(fields[-1])
    if seconds >= 60 or (len(fields) == 3 and int(fields[-2]) >= 60):
        raise TutorialError("Transcript timestamps need seconds/minutes below 60.")
    total = (
        int(fields[0]) * 3600 + int(fields[1]) * 60 + seconds
        if len(fields) == 3
        else int(fields[0]) * 60 + seconds
    )
    if not 0 <= total <= MAX_TUTORIAL_SECONDS:
        raise TutorialError("Tutorial timestamps must fit within four hours.")
    return round(total, 3)


def _validated_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(segments, list) or not 1 <= len(segments) <= MAX_SEGMENTS:
        raise TutorialError("Provide between 1 and 50 timestamped transcript segments.")
    normalized = []
    total_characters = 0
    for segment in segments:
        if not isinstance(segment, dict):
            raise TutorialError("Each transcript segment needs start, end, and text.")
        start, end, text = segment.get("start"), segment.get("end"), segment.get("text")
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, (int, float))
            or not isinstance(end, (int, float))
            or not math.isfinite(start)
            or not math.isfinite(end)
            or not 0 <= start <= end <= MAX_TUTORIAL_SECONDS
        ):
            raise TutorialError("Transcript segments need finite, ordered timestamps within four hours.")
        if not isinstance(text, str) or not text.strip():
            raise TutorialError("Each transcript segment needs nonempty text.")
        total_characters += len(text)
        if total_characters > MAX_TRANSCRIPT_CHARACTERS:
            raise TutorialError("Transcript text must contain at most 50,000 characters.")
        text = " ".join(text.split())
        if normalized and (start <= normalized[-1]["start"] or start < normalized[-1]["end"]):
            raise TutorialError("Transcript segments must be chronological and must not overlap.")
        normalized.append({"start": float(start), "end": float(end), "text": text})
    return normalized


def parse_transcript(transcript: str) -> list[dict[str, Any]]:
    """Parse timestamped lines/ranges or SRT; never invent a final duration.

    Point-only segments end at the following timestamp. The last point ends at
    its own timestamp because no duration was supplied. SRT ranges retain ends.
    """
    if not isinstance(transcript, str) or not transcript.strip():
        raise TutorialError("Paste a transcript with timestamps before extracting steps.")
    if len(transcript) > MAX_TRANSCRIPT_CHARACTERS:
        raise TutorialError("Transcript text must contain at most 50,000 characters.")
    lines = transcript.lstrip("\ufeff").splitlines()
    pending: list[dict[str, Any]] = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        # Ignore an SRT counter only when followed by an actual range line.
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if line.isascii() and line.isdigit() and _RANGE.fullmatch(following):
            continue
        match = _RANGE.fullmatch(line)
        if match:
            if bool(match["open"]) != bool(match["close"]):
                raise TutorialError("Transcript timestamp range brackets must be balanced.")
            start, end = _seconds(match["start"]), _seconds(match["end"])
            if end <= start:
                raise TutorialError("An explicit transcript range must end after it starts.")
            pending.append({"start": start, "end": end, "text": match["text"]})
        elif match := _POINT.fullmatch(line):
            pending.append(
                {"start": _seconds(match["bracket"] or match["bare"]), "end": None, "text": match["text"]}
            )
        elif match := _EMPTY_POINT.fullmatch(line):
            pending.append({"start": _seconds(match["start"]), "end": None, "text": ""})
        else:
            if re.match(r"^\[?[0-9]{1,3}:", line) or "-->" in line:
                raise TutorialError("A transcript timestamp is malformed.")
            if not pending:
                raise TutorialError("Every transcript section must start with a timestamp.")
            pending[-1]["text"] += " " + line
        if len(pending) > MAX_SEGMENTS:
            raise TutorialError("A tutorial supports at most 50 transcript segments.")
    for index, segment in enumerate(pending):
        if segment["end"] is None:
            segment["end"] = pending[index + 1]["start"] if index + 1 < len(pending) else segment["start"]
    return _validated_segments(pending)


def youtube_reference(url: str) -> dict[str, str]:
    """Return a canonical embed reference after strict host/path validation."""
    if not isinstance(url, str) or len(url) > 2048 or any(ord(char) < 32 for char in url):
        raise TutorialError("Provide a valid HTTPS YouTube URL.", "invalid_youtube_url")
    try:
        parsed = urlsplit(url.strip())
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
            or parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
        ):
            raise ValueError("Unsupported URL")
        parts = parsed.path.strip("/").split("/")
        if parsed.hostname == "youtu.be" and len(parts) == 1:
            video_id = parts[0]
        elif parsed.hostname != "youtu.be" and parsed.path.rstrip("/") == "/watch":
            values = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
            if len(values) != 1:
                raise ValueError("Ambiguous video id")
            video_id = values[0]
        elif parsed.hostname != "youtu.be" and len(parts) == 2 and parts[0] in {"shorts", "embed"}:
            video_id = parts[1]
        else:
            raise ValueError("Unsupported path")
        if not _VIDEO_ID.fullmatch(video_id):
            raise ValueError("Invalid video id")
    except (ValueError, AttributeError):
        raise TutorialError(
            "Use an HTTPS YouTube watch, shorts, embed, or youtu.be URL with an 11-character video ID.",
            "invalid_youtube_url",
        ) from None
    return {"youtube_id": video_id, "embed_url": f"https://www.youtube-nocookie.com/embed/{video_id}"}


def instruction_warnings(text: str) -> list[str]:
    """Flag source instructions for review, without judging website reputation."""
    warnings = []
    security = re.compile(
        r"\b(?:disable|turn\s+off|deactivate|bypass)\s+(?:(?:the|your)\s+)?"
        r"(?:anti[- ]?virus|firewall|windows\s+defender|defender|security\s+protections?|"
        r"real[- ]time\s+protection|smartscreen|gatekeeper|browser\s+security)",
        re.I,
    )
    for match in security.finditer(text):
        prefix = text[max(0, match.start() - 18) : match.start()].lower()
        if not re.search(r"(?:do\s+not|don't|never)\s*$", prefix):
            warnings.append("This source asks to disable security protections. Review it before continuing.")
            break
    if (
        re.search(r"\bdownload(?:s|ed|ing)?\b", text, re.I)
        or re.search(r"\binstall(?:ation|er)?\b[^.\n]{0,100}\bfrom\b", text, re.I)
        or re.search(r"https?://\S+\.(?:exe|msi|zip|vsix|dmg|pkg)(?:[?#\s]|$)", text, re.I)
    ):
        warnings.append(
            "Download sources in this tutorial have not been verified by ReplayLab. Confirm the publisher and source yourself."
        )
    return warnings


def parse_tutorial(
    youtube_url: str | None,
    transcript: str,
    title: str | None = None,
    *,
    usage_rights_confirmed: bool = False,
) -> dict[str, Any]:
    if not isinstance(usage_rights_confirmed, bool):
        raise TutorialError("Usage-rights confirmation must be explicit.")
    if title is not None and (not isinstance(title, str) or len(title) > 240):
        raise TutorialError("A tutorial title must contain at most 240 characters.")
    if not isinstance(transcript, str):
        raise TutorialError("Transcript must be plain text.")
    if len(transcript) > MAX_TRANSCRIPT_CHARACTERS:
        raise TutorialError("Transcript text must contain at most 50,000 characters.")
    if youtube_url is not None and not isinstance(youtube_url, str):
        raise TutorialError("YouTube reference must be a URL string.", "invalid_youtube_url")
    reference = youtube_reference(youtube_url) if youtube_url else {"youtube_id": None, "embed_url": None}
    segments = parse_transcript(transcript) if transcript.strip() else []
    if not youtube_url and not segments:
        raise TutorialError("Provide a YouTube reference or a timestamped transcript.")
    supplied_title = title.strip() if title else ""
    return {
        "kind": "youtube" if youtube_url else "transcript",
        **reference,
        "title": supplied_title or ("YouTube tutorial" if youtube_url else "Pasted tutorial transcript"),
        "title_source": "user-provided, unverified" if supplied_title else "local default, unverified",
        "transcript_segments": segments,
        "usage_rights_confirmed": usage_rights_confirmed,
        "instruction_warnings": instruction_warnings(transcript),
        "content_fetched": False,
    }


def extract_digital_task(
    transcript_segments: list[dict[str, Any]],
    frames: list[dict],
    provider_mode: str = "mock",
    *,
    title: str = "Digital tutorial",
    interface_version: str | None = None,
) -> Task:
    """Propose one editable step per segment, using quoted labels conservatively."""
    from app.digital_schemas import ScreenRule

    if provider_mode != "mock":
        raise TutorialError("This transcript segmenter is an offline mock provider, not Muse Spark.")
    segments = _validated_segments(transcript_segments)
    steps = []
    manual_steps = []
    usable_frames = [
        frame
        for frame in frames
        if isinstance(frame.get("id"), str)
        and isinstance(frame.get("timestamp"), (int, float))
        and math.isfinite(frame["timestamp"])
    ]
    for index, segment in enumerate(segments):
        labels = list(
            dict.fromkeys(
                " ".join(next(value for value in match if value).split())
                for match in _QUOTES.findall(segment["text"])
            )
        )
        labels = [label for label in labels if len(label) >= 2]
        if len(labels) > 8:
            raise TutorialError(
                "A segment supports at most eight candidate quoted UI labels; split this segment."
            )
        step_id = f"digital-step-{index + 1}"
        rules = [
            ScreenRule(
                id=f"{step_id}-label-{position + 1}",
                kind="text_present",
                expected=label,
                description="Candidate quoted transcript label; review whether it is a visible checkpoint.",
            )
            for position, label in enumerate(labels)
        ]
        if not rules:
            manual_steps.append(step_id)
        closest = (
            min(usable_frames, key=lambda frame: abs(frame["timestamp"] - segment["end"]))
            if usable_frames
            else None
        )
        steps.append(
            Step(
                id=step_id,
                title=segment["text"][:240],
                description=segment["text"],
                dependencies=[steps[-1].id] if steps else [],
                timestamp_start=segment["start"],
                timestamp_end=segment["end"],
                reference_frame_id=closest["id"] if closest else None,
                expected_state=("Visible UI text: " + "; ".join(labels))
                if labels
                else "Manual review required: define a visible checkpoint before verification.",
                screen_rules=rules,
            )
        )
    combined = " ".join(segment["text"] for segment in segments)
    return Task(
        id=uuid4().hex,
        title=title,
        modality="digital",
        interface_version=interface_version,
        description="Offline transcript segmentation. Candidate labels require review; no video or screen inference was performed.",
        steps=steps,
        provider_mode="mock",
        provenance={
            "provider": "deterministic timestamped transcript segmentation",
            "inferred_from_video": False,
            "inferred_from_screen": False,
            "requires_approval": True,
            "manual_rule_step_ids": manual_steps,
            "instruction_warnings": instruction_warnings(combined),
            "source_is_untrusted_evidence": True,
        },
    )
