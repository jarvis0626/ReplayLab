"""Add timed neural narration to a verified continuous tutorial demonstration.

Only narration text goes to online speech. Source/previous output backups and
raw audio stay under ignored .artifacts. The video is stream-copied unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from add_demo_voiceover import probe, video_hash

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ReplayLab_Meta_Hackathon_Demo.mp4"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def timestamp_hash(path):
    packets = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "packet=pts_time,dts_time,duration_time", "-of", "csv=p=0", str(path)])
    return hashlib.sha256(packets).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--voice", default="en-US-GuyNeural")
    args = parser.parse_args()
    source, plan_path = args.source.resolve(), args.plan.resolve()
    if not source.is_relative_to(ROOT) or not source.is_file():
        parser.error("Source must be an existing video inside this repository.")
    if not plan_path.is_relative_to(ROOT) or not plan_path.is_file():
        parser.error("Plan must be a JSON file inside this repository.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("Installed FFmpeg and FFprobe are required.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    source_digest = digest(source)
    if source_digest != plan["source_video_sha256"]:
        parser.error("Source video does not match the narration plan's approved SHA256.")
    media = probe(source)
    duration = float(media["format"]["duration"])
    if not 0 < duration <= 180 or abs(duration - float(plan["duration_seconds"])) > 0.001:
        parser.error("Source duration must match the plan and remain within three minutes.")
    previous_end = 0.0
    for segment in plan["segments"]:
        if not previous_end <= segment["start"] < segment["end"] <= duration:
            parser.error("Narration windows overlap or exceed the actual video.")
        previous_end = segment["end"]
    work = ROOT / ".artifacts" / ("tutorial-proof-voiceover-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    work.mkdir(parents=True, exist_ok=False)
    report_path = work / "validation.json"
    report = {"success": False, "created_at": datetime.now(UTC).isoformat(),
              "source_sha256": source_digest, "source_media": media,
              "plan_sha256": digest(plan_path), "voice": args.voice,
              "synthetic_narration": True, "video_stream_copied": True,
              "narration_disclosure": "Synthetic voiceover is identified in metadata and project documentation.",
              "online_content": "Only the owner-approved narration text; no screenshots, video or credentials."}

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        original = work / "source-silent.mp4"
        shutil.copyfile(source, original)
        if OUTPUT.exists():
            report["previous_output_sha256"] = digest(OUTPUT)
            shutil.copyfile(OUTPUT, work / "previous-main-demo.mp4")
        speech_dir = work / "speech"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "synthesize_neural_voice.py"),
                        "--plan", str(plan_path), "--output-dir", str(speech_dir), "--voice", args.voice],
                       check=True, timeout=180)
        speech = json.loads((speech_dir / "neural-speech.json").read_text(encoding="utf-8"))
        if not speech["success"] or not all(item["fits_window"] for item in speech["segments"]):
            raise ValueError("Shorten speech to fit the actual scene windows.")
        report["speech"] = speech
        inputs, filters, labels = [], [], []
        for index, item in enumerate(speech["segments"]):
            inputs.extend(["-i", str(ROOT / item["file"])])
            filters.append(f"[{index}:a]aresample=48000,adelay={round(item['start'] * 1000)}:all=1[a{index}]")
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,"
                       f"aresample=48000,apad=whole_dur={duration},atrim=duration={duration}[voiceover]")
        audio = work / "voiceover.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
                        "-map", "[voiceover]", "-c:a", "pcm_s16le", str(audio)], check=True, timeout=90)
        candidate = work / "narrated.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(original), "-i", str(audio),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                        "-metadata", "comment=Synthetic neural narration added after continuous real application capture; video unchanged.",
                        "-metadata:s:a:0", f"title=Synthetic neural narration - {args.voice}",
                        "-metadata:s:a:0", "language=eng", "-movflags", "+faststart", str(candidate)], check=True, timeout=90)
        result = probe(candidate)
        old_video = next(item for item in media["streams"] if item["codec_type"] == "video")
        new_video = next(item for item in result["streams"] if item["codec_type"] == "video")
        new_audio = next(item for item in result["streams"] if item["codec_type"] == "audio")
        for field in ["codec_name", "width", "height", "r_frame_rate", "nb_frames", "duration"]:
            if old_video.get(field) != new_video.get(field):
                raise ValueError("The narrated video stream differs from its actual source.")
        if abs(float(result["format"]["duration"]) - duration) > 0.001 or float(result["format"]["duration"]) > 180:
            raise ValueError("Output duration changed or exceeded three minutes.")
        if new_audio["codec_name"] != "aac" or int(new_audio["sample_rate"]) != 48000:
            raise ValueError("Expected AAC48kHz narration is absent.")
        report["source_video_packet_sha256"], report["output_video_packet_sha256"] = video_hash(original), video_hash(candidate)
        report["source_timestamp_sha256"], report["output_timestamp_sha256"] = timestamp_hash(original), timestamp_hash(candidate)
        if report["source_video_packet_sha256"] != report["output_video_packet_sha256"] or report["source_timestamp_sha256"] != report["output_timestamp_sha256"]:
            raise ValueError("Recorded video packets or their timing changed.")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(candidate), "-f", "null", "-"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=90)
        report["full_decode_passed"] = True
        levels = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(candidate), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                                check=True, capture_output=True, text=True, timeout=60)
        report["audio_levels_dbfs"] = {name: float(value) for name, value in
            re.findall(r"(mean_volume|max_volume):\s*(-?\d+(?:\.\d+)?) dB", levels.stderr)}
        if not report["audio_levels_dbfs"] or report["audio_levels_dbfs"].get("max_volume", 0) >= 0:
            raise ValueError("Narration is missing or clips at full scale.")
        report.update(success=True, output_media=result, output_sha256=digest(candidate),
                      finished_at=datetime.now(UTC).isoformat())
        save()
        shutil.copyfile(candidate, OUTPUT)
        (ROOT / "docs" / "validation" / "tutorial-proof-voiceover.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"success": True, "output": OUTPUT.name, "voice": args.voice,
                          "duration_seconds": duration, "video_and_timestamps_unchanged": True,
                          "report": str(report_path.relative_to(ROOT))}), flush=True)
    except BaseException as error:
        report["success"] = False
        report["error_type"] = type(error).__name__
        save()
        raise


if __name__ == "__main__":
    main()
