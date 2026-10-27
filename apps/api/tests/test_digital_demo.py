from __future__ import annotations

import json
import subprocess

import pytest
from PIL import Image

from app.services.digital_demo import (
    DigitalDemoError,
    demonstration_transcript,
    digital_demo_task,
    ensure_digital_demo,
)


def test_generated_references_and_actual_playable_video(tmp_path):
    directory = tmp_path / "digital-demo"
    manifest = ensure_digital_demo(directory)
    assert manifest["kind"] == "demo"
    assert manifest["usage_rights_confirmed"] is True
    assert manifest["provenance"]["inferred_from_video"] is False
    assert len(manifest["frames"]) == 4
    for frame in manifest["frames"]:
        path = directory / frame["filename"]
        assert path.parent == directory
        with Image.open(path) as image:
            assert image.size == (1280, 800)
            assert image.format == "PNG"
    output = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,width,height",
            "-of",
            "json",
            str(directory / manifest["video"]),
        ]
    )
    metadata = json.loads(output)
    assert metadata["streams"][0]["codec_name"] == "h264"
    assert metadata["streams"][0]["width"] == 1280
    assert metadata["streams"][0]["height"] == 800
    assert float(metadata["format"]["duration"]) == pytest.approx(12.0)
    assert manifest["frames"][-1]["timestamp"] < float(metadata["format"]["duration"])


def test_cached_complete_demo_does_not_regenerate_video(tmp_path, monkeypatch):
    first = ensure_digital_demo(tmp_path / "digital-demo")

    def no_process(*args, **kwargs):
        raise AssertionError("Complete generated assets should be reused")

    monkeypatch.setattr("app.services.digital_demo.subprocess.run", no_process)
    assert ensure_digital_demo(tmp_path / "digital-demo") == first


def test_demo_task_matches_simulator_states_and_requires_approval():
    frames = [{"id": f"frame-{index}", "timestamp": index * 3.0} for index in range(4)]
    task = digital_demo_task(frames)
    assert task.modality == "digital"
    assert task.interface_version == "CodeLab 1.0"
    assert task.provider_mode == "mock"
    assert task.provenance["requires_approval"] is True
    assert task.provenance["inferred_from_video"] is False
    assert [step.id for step in task.steps] == [f"digital-step-{index}" for index in range(1, 5)]
    assert [rule.expected for rule in task.steps[0].screen_rules] == ["Extensions Marketplace"]
    assert [rule.expected for rule in task.steps[1].screen_rules] == ["Search results", "Replay Formatter"]
    assert [rule.expected for rule in task.steps[2].screen_rules] == [
        "Extension details",
        "Replay Formatter",
        "Install extension",
    ]
    assert [rule.expected for rule in task.steps[3].screen_rules] == [
        "Replay Formatter",
        "Installed",
        "Enabled",
    ]
    for index, step in enumerate(task.steps):
        assert step.reference_frame_id == frames[index]["id"]
        assert step.dependencies == ([f"digital-step-{index}"] if index else [])
        assert step.rules == []
        assert all(rule.kind == "text_present" for rule in step.screen_rules)
        assert all("Preferences" in rule.contradictions for rule in step.screen_rules)
        assert all(rule.kind != "error_absent" for rule in step.screen_rules)


def test_missing_reference_frames_fail_clearly():
    with pytest.raises(DigitalDemoError, match="Four reference"):
        digital_demo_task([])


def test_demonstration_transcript_is_fresh_and_bounded():
    transcript = demonstration_transcript()
    transcript[0]["text"] = "changed"
    assert demonstration_transcript()[0]["text"] != "changed"
    assert len(transcript) == 4
    assert [segment["start"] for segment in transcript] == [0, 3, 6, 9]


def test_missing_ffmpeg_is_safe_and_no_success_manifest_written(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("private executable path")

    monkeypatch.setattr("app.services.digital_demo.subprocess.run", missing)
    with pytest.raises(DigitalDemoError, match="FFmpeg") as error:
        ensure_digital_demo(tmp_path / "digital-demo")
    assert "private" not in str(error.value)
    assert not (tmp_path / "digital-demo" / "manifest.json").exists()
