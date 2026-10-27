from __future__ import annotations

import socket

import pytest

from app.services.tutorials import (
    TutorialError,
    extract_digital_task,
    instruction_warnings,
    parse_transcript,
    parse_tutorial,
    youtube_reference,
)


def test_bracket_timestamps_and_multiline_narration():
    assert parse_transcript(
        '[00:00]Open "Extensions Marketplace".\nThen inspect it.\n[00:12] Find "Replay Formatter".'
    ) == [
        {"start": 0.0, "end": 12.0, "text": 'Open "Extensions Marketplace". Then inspect it.'},
        {"start": 12.0, "end": 12.0, "text": 'Find "Replay Formatter".'},
    ]


def test_explicit_timestamp_ranges_are_preserved():
    assert parse_transcript('00:12-00:24 Open "Extensions"\n00:24 - 00:30 Search') == [
        {"start": 12.0, "end": 24.0, "text": 'Open "Extensions"'},
        {"start": 24.0, "end": 30.0, "text": "Search"},
    ]


@pytest.mark.parametrize("source", ["[00:12-00:24 Action", "00:12-00:24] Action"])
def test_unbalanced_timestamp_range_brackets_are_rejected(source):
    with pytest.raises(TutorialError, match="balanced"):
        parse_transcript(source)


def test_balanced_timestamp_range_brackets_are_supported():
    assert parse_transcript("[00:12-00:24] Action") == [{"start": 12.0, "end": 24.0, "text": "Action"}]


def test_srt_counters_fractional_timestamps_and_multiline_text():
    source = '1\n00:00:01,125 --> 00:00:04,500\nOpen "Extensions"\nand inspect the panel.\n\n2\n00:00:05,000 --> 00:00:08,000\nSearch.'
    assert parse_transcript(source) == [
        {"start": 1.125, "end": 4.5, "text": 'Open "Extensions" and inspect the panel.'},
        {"start": 5.0, "end": 8.0, "text": "Search."},
    ]


@pytest.mark.parametrize(
    "text",
    [
        "",
        "No timestamps",
        "[00:xx] Broken timestamp",
        "[00:70] Invalid seconds",
        "[01:60:00] Invalid minutes",
        "[04:00:01] Too long",
        "[00:12]",
        "00:12-00:10 Reversed",
        "00:12-00:12 Empty explicit range",
        "[00:12] First\n[00:10] Earlier",
        "[00:12] First\n[00:12] Duplicate",
        "00:00-00:20 First\n00:10-00:30 Overlap",
    ],
    ids=lambda value: f"transcript-{len(value)}",
)
def test_invalid_or_unbounded_transcripts_rejected(text):
    with pytest.raises(TutorialError):
        parse_transcript(text)


def test_maximum_segment_count_is_enforced():
    source = "\n".join(f"[00:{index:02d}] Action" for index in range(51))
    with pytest.raises(TutorialError, match="50"):
        parse_transcript(source)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&feature=shared",
        "https://m.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?t=12",
    ],
)
def test_youtube_references_are_canonical_and_never_fetched(url, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Tutorial ingestion must not open a network connection")

    monkeypatch.setattr(socket, "create_connection", no_network)
    reference = youtube_reference(url)
    assert reference == {
        "youtube_id": "dQw4w9WgXcQ",
        "embed_url": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://user:secret@youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com:443/watch?v=dQw4w9WgXcQ",
        "https://127.0.0.1/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ/extra",
        "https://youtube.com/redirect?q=https://example.com",
        "https://youtube.com/watch?v=short",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&v=abcdefghijk",
        "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ\n.evil.example",
        "https://youtube.com/watch?v=../../etc/passwd",
    ],
)
def test_invalid_youtube_urls_rejected(url):
    with pytest.raises(TutorialError) as error:
        youtube_reference(url)
    assert error.value.code == "invalid_youtube_url"


def test_metadata_records_explicit_rights_and_unverified_title():
    result = parse_tutorial(
        "https://youtu.be/dQw4w9WgXcQ",
        '[00:00] Open "Extensions"',
        "My supplied title",
        usage_rights_confirmed=True,
    )
    assert result["usage_rights_confirmed"] is True
    assert result["content_fetched"] is False
    assert result["title_source"] == "user-provided, unverified"
    assert len(result["transcript_segments"]) == 1
    assert parse_tutorial("https://youtu.be/dQw4w9WgXcQ", "")["usage_rights_confirmed"] is False


def test_youtube_without_transcript_is_reference_only():
    result = parse_tutorial("https://youtu.be/dQw4w9WgXcQ", "")
    assert result["title"] == "YouTube tutorial"
    assert result["transcript_segments"] == []
    with pytest.raises(TutorialError):
        extract_digital_task(result["transcript_segments"], [])


def test_whitespace_does_not_bypass_character_limit():
    with pytest.raises(TutorialError, match="50,000"):
        parse_tutorial("https://youtu.be/dQw4w9WgXcQ", " " * 50_001)


def test_raw_transcript_character_limit_is_enforced():
    with pytest.raises(TutorialError, match="50,000"):
        parse_transcript("[00:00] " + "x" * 50_000)


def test_transcript_proposal_has_valid_dag_and_conservative_label_rules():
    segments = parse_transcript(
        '[00:00] Open "Extensions Marketplace".\n[00:10] Search for “Replay Formatter”.\n[00:20] Finish the operation.'
    )
    task = extract_digital_task(segments, [{"id": "a", "timestamp": 0}, {"id": "b", "timestamp": 20}])
    assert task.modality == "digital" and task.provider_mode == "mock"
    assert task.provenance["inferred_from_video"] is False
    assert task.provenance["requires_approval"] is True
    assert task.steps[0].screen_rules[0].expected == "Extensions Marketplace"
    assert task.steps[1].screen_rules[0].expected == "Replay Formatter"
    assert task.steps[1].dependencies == [task.steps[0].id]
    assert task.steps[1].reference_frame_id == "b"
    assert task.steps[2].screen_rules == []
    assert task.steps[2].id in task.provenance["manual_rule_step_ids"]
    assert task.steps[2].rules == []


def test_empty_frames_are_valid_for_pasted_transcript():
    task = extract_digital_task(parse_transcript('[00:00] Open "Extensions"'), [])
    assert task.steps[0].reference_frame_id is None


@pytest.mark.parametrize(
    "segments",
    [
        [{"start": float("nan"), "end": 1, "text": "Action"}],
        [{"start": True, "end": 1, "text": "Action"}],
        [{"start": 2, "end": 1, "text": "Action"}],
    ],
)
def test_direct_segment_inputs_are_validated(segments):
    with pytest.raises(TutorialError):
        extract_digital_task(segments, [])


def test_segmenter_cannot_claim_meta_inference():
    with pytest.raises(TutorialError, match="offline mock"):
        extract_digital_task(parse_transcript('[00:00] Open "Extensions"'), [], "meta")


def test_suspicious_instructions_are_advisory_without_reputation_claims():
    warnings = instruction_warnings(
        "Disable your antivirus. Download the installer from https://vendor.example/tool.exe"
    )
    assert len(warnings) == 2
    assert "not been verified" in warnings[1]
    assert instruction_warnings("Install the extension using the marketplace.") == []
    assert instruction_warnings("Never disable antivirus. Do not turn off the firewall.") == []


def test_unverified_download_warning_does_not_depend_on_domain_reputation():
    for domain in ("known-vendor.example", "unknown.example"):
        assert instruction_warnings(f"Download the archive from https://{domain}/tool.zip")
