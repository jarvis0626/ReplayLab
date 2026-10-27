"""Generate a labeled CodeLab simulation reference, not a real extension install."""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from app.schemas import Step, Task

_LOCK = threading.RLock()
_VERSION = 2
_FRAME_NAMES = [f"reference-{index}.png" for index in range(1, 5)]
_VIDEO_NAME = "codelab-extension.mp4"
_TIMESTAMPS = [2.0, 5.0, 8.0, 11.0]


class DigitalDemoError(RuntimeError):
    pass


def demonstration_transcript() -> list[dict]:
    return [
        {"start": 0.0, "end": 3.0, "text": 'Open the "Extensions Marketplace" panel in CodeLab.'},
        {"start": 3.0, "end": 6.0, "text": 'Search for "Replay Formatter" and inspect "Search results".'},
        {
            "start": 6.0,
            "end": 9.0,
            "text": 'Open "Extension details" for "Replay Formatter" and locate "Install extension".',
        },
        {
            "start": 9.0,
            "end": 12.0,
            "text": 'Use the simulated install control, then confirm "Installed" and "Enabled".',
        },
    ]


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _render_reference(stage: int, path: Path):
    image = Image.new("RGB", (1280, 800), "#111723")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 96), fill="#1d2938")
    draw.text((30, 24), "CodeLab 1.0", font=_font(34, True), fill="white")
    draw.text((920, 36), "SIMULATED WORKSPACE", font=_font(18), fill="#b7c8d6")
    draw.rectangle((0, 96, 230, 752), fill="#182230")
    draw.text((26, 126), "Explorer", font=_font(25), fill="#c0ceda")
    draw.rounded_rectangle((14, 184, 214, 246), radius=8, fill="#2e5262")
    draw.text((26, 202), "Extensions", font=_font(25, True), fill="white")
    draw.text((26, 274), "Workspace", font=_font(25), fill="#c0ceda")
    draw.text(
        (268, 120),
        "Extensions Marketplace" if stage == 1 else "Search results" if stage == 2 else "Extension details",
        font=_font(35, True),
        fill="white",
    )
    if stage in (1, 2):
        draw.rounded_rectangle((266, 192, 1226, 256), radius=8, fill="#233346", outline="#718595", width=2)
        draw.text(
            (290, 209),
            "Search extensions" if stage == 1 else "Replay Formatter",
            font=_font(27),
            fill="#e3edf4",
        )
    if stage == 1:
        draw.text((274, 302), "Find extensions for your workspace", font=_font(29), fill="#d8e2eb")
        draw.text(
            (274, 358),
            "Search for the extension demonstrated in the tutorial.",
            font=_font(23),
            fill="#b7c8d6",
        )
    else:
        top = 308 if stage == 2 else 204
        draw.rounded_rectangle(
            (268, top, 1226, top + 238), radius=12, fill="#213044", outline="#52667a", width=2
        )
        draw.rounded_rectangle((296, top + 30, 360, top + 94), radius=10, fill="#51a9bd")
        draw.text((316, top + 42), "R", font=_font(34, True), fill="#10202c")
        draw.text((388, top + 35), "Replay Formatter", font=_font(34, True), fill="white")
        draw.text((388, top + 92), "Format source files in CodeLab", font=_font(25), fill="#c8d6e3")
        draw.text((388, top + 141), "Sandbox simulation - no system changes", font=_font(20), fill="#b7c8d6")
        if stage == 3:
            draw.rounded_rectangle((274, 500, 620, 574), radius=10, fill="#a5e6e6")
            draw.text((307, 522), "Install extension", font=_font(29, True), fill="#13212b")
        if stage == 4:
            draw.rounded_rectangle((274, 500, 602, 574), radius=10, fill="#234f42")
            draw.text((308, 519), "Installed", font=_font(31, True), fill="#baf2ce")
            draw.rounded_rectangle((642, 500, 970, 574), radius=10, fill="#234f42")
            draw.text((677, 519), "Enabled", font=_font(31, True), fill="#baf2ce")
    draw.rectangle((0, 752, 1280, 800), fill="#4b3e21")
    draw.text(
        (24, 765),
        "MOCK DEMO - synthetic CodeLab reference - no live model inference",
        font=_font(20),
        fill="#ffe2a6",
    )
    image.save(path, format="PNG")


def ensure_digital_demo(directory: Path) -> dict:
    """Create assets only below the supplied runtime directory; return filenames."""
    directory = Path(directory).resolve()
    with _LOCK:
        directory.mkdir(parents=True, exist_ok=True)
        manifest_path = directory / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text("utf-8"))
            if (
                manifest.get("version") == _VERSION
                and manifest.get("video") == _VIDEO_NAME
                and [frame.get("filename") for frame in manifest.get("frames", [])] == _FRAME_NAMES
                and all(
                    (directory / name).is_file() and (directory / name).stat().st_size > 0
                    for name in [*_FRAME_NAMES, _VIDEO_NAME]
                )
            ):
                return manifest
        except (OSError, ValueError, AttributeError, TypeError):
            pass
        for index, name in enumerate(_FRAME_NAMES, 1):
            _render_reference(index, directory / name)
        pending = directory / "codelab-extension.pending.mp4"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-framerate",
                    "1/3",
                    "-start_number",
                    "1",
                    "-i",
                    str(directory / "reference-%d.png"),
                    "-t",
                    "12",
                    "-r",
                    "10",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-threads",
                    "1",
                    "-movflags",
                    "+faststart",
                    "-y",
                    str(pending),
                ],
                capture_output=True,
                timeout=45,
                check=True,
            )
            if not pending.is_file() or not pending.stat().st_size:
                raise DigitalDemoError("The digital demo video could not be generated.")
            os.replace(pending, directory / _VIDEO_NAME)
        except (FileNotFoundError, subprocess.SubprocessError):
            pending.unlink(missing_ok=True)
            raise DigitalDemoError("FFmpeg is required to create the digital demonstration.") from None
        manifest = {
            "version": _VERSION,
            "kind": "demo",
            "title": "CodeLab extension workflow",
            "interface_version": "CodeLab 1.0",
            "video": _VIDEO_NAME,
            "frames": [
                {"filename": name, "timestamp": timestamp}
                for name, timestamp in zip(_FRAME_NAMES, _TIMESTAMPS)
            ],
            "transcript_segments": demonstration_transcript(),
            "usage_rights_confirmed": True,
            "provenance": {
                "synthetic": True,
                "inferred_from_video": False,
                "source": "ReplayLab-generated simulated CodeLab reference",
            },
        }
        temporary_manifest = directory / "manifest.pending.json"
        temporary_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        os.replace(temporary_manifest, manifest_path)
        return manifest


def digital_demo_task(frames: list[dict]) -> Task:
    """Build fixed reviewed-later rules against actual user-supplied screen pixels."""
    from app.digital_schemas import ScreenRule

    if len(frames) < 4 or any(not isinstance(frame.get("id"), str) for frame in frames[:4]):
        raise DigitalDemoError("Four reference frames are required for the digital demonstration.")
    states = [
        ("Open the Extensions Marketplace", ["Extensions Marketplace"]),
        ("Find Replay Formatter", ["Search results", "Replay Formatter"]),
        ("Review the extension details", ["Extension details", "Replay Formatter", "Install extension"]),
        ("Confirm installed and enabled", ["Replay Formatter", "Installed", "Enabled"]),
    ]
    steps = []
    segments = demonstration_transcript()
    for index, (title, labels) in enumerate(states):
        step_id = f"digital-step-{index + 1}"
        rules = []
        for position, label in enumerate(labels):
            contradictions = ["Preferences"]
            if index == 3 and label == "Installed":
                contradictions.append("Install extension")
            if index == 3 and label == "Enabled":
                contradictions.append("Disabled")
            rules.append(
                ScreenRule(
                    id=f"{step_id}-text-{position + 1}",
                    kind="text_present",
                    expected=label,
                    alternatives=[],
                    contradictions=contradictions,
                    description="Verify this visible CodeLab simulation label with actual screen observations.",
                )
            )
        steps.append(
            Step(
                id=step_id,
                title=title,
                description=segments[index]["text"],
                dependencies=[f"digital-step-{index}"] if index else [],
                timestamp_start=segments[index]["start"],
                timestamp_end=segments[index]["end"],
                reference_frame_id=frames[index]["id"],
                expected_state="; ".join(labels),
                screen_rules=rules,
            )
        )
    return Task(
        id=uuid4().hex,
        title="Install a simulated CodeLab extension",
        modality="digital",
        interface_version="CodeLab 1.0",
        provider_mode="mock",
        objects=[],
        steps=steps,
        description="Labeled synthetic CodeLab workflow. Steps are a fixed local template, not video analysis. No extension is actually installed.",
        provenance={
            "provider": "fixed synthetic transcript template",
            "synthetic": True,
            "inferred_from_video": False,
            "inferred_from_screen": False,
            "requires_approval": True,
            "source_is_untrusted_evidence": True,
        },
    )
