"""Add disclosed local Windows speech to the existing continuous demo.

Video is stream-copied without trimming, re-encoding or time changes. Every
sentence must fit its assigned real-time window before a candidate is accepted.
Raw speech and the original silent video stay in ignored .artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import wave
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "demo-narration.json"
OUTPUT = ROOT / "ReplayLab_Meta_Hackathon_Demo.mp4"
SPEECH_SCRIPT = r'''
param([string]$PlanFile, [string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$plan = Get-Content -LiteralPath $PlanFile -Raw -Encoding UTF8 | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speaker.SelectVoice($plan.voice)
    $speaker.Rate = $plan.rate
    $speaker.Volume = 100
    foreach ($segment in $plan.segments) {
        $target = Join-Path $OutputDirectory ($segment.id + '.wav')
        $speaker.SetOutputToWaveFile($target)
        $speaker.Speak([string]$segment.text)
        $speaker.SetOutputToNull()
    }
} finally {
    $speaker.Dispose()
}
'''


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,nb_frames,sample_rate,channels,duration",
        "-of", "json", str(path)], text=True))


def video_hash(path):
    result = subprocess.check_output([
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-c:v", "copy", "-f", "hash", "-hash", "sha256", "-"], text=True)
    return result.strip().split("=", 1)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=OUTPUT,
                        help="Original accepted silent take. A safe copy is retained before writing output.")
    args = parser.parse_args()
    source = args.source.resolve()
    if os.name != "nt":
        parser.error("Local installed Windows speech voices are required.")
    if not source.is_relative_to(ROOT) or not source.is_file():
        parser.error("Source must be an existing recording inside this repository.")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("The installed FFmpeg and FFprobe tools are required.")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if source_digest != plan["source_video_sha256"]:
        parser.error("Source differs from the accepted original silent take. Use the preserved source-silent.mp4 for a repeat run.")
    work = ROOT / ".artifacts" / ("demo-voiceover-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    work.mkdir(parents=True, exist_ok=False)
    report_path = work / "validation.json"
    report = {"success": False, "created_at": datetime.now(UTC).isoformat(),
              "source_sha256": source_digest, "voice": plan["voice"], "rate": plan["rate"],
              "plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
              "synthetic_narration": True, "synthesis_location": "local Windows System.Speech",
              "cloud_requests": 0, "segments": [], "video_frames_changed": False,
              "disclosure": plan["disclosure"]}

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        original = work / "source-silent.mp4"
        shutil.copyfile(source, original)
        source_probe = probe(original)
        report["source_media"] = source_probe
        duration = float(source_probe["format"]["duration"])
        assert abs(duration - plan["duration_seconds"]) < 0.001
        previous_end = 0.0
        for segment in plan["segments"]:
            assert 0 <= segment["start"] < segment["end"] <= duration
            assert segment["start"] >= previous_end, "Narration windows overlap."
            assert segment["id"].replace("-", "").isalnum()
            previous_end = segment["end"]
        speech_path = work / "synthesize.ps1"
        speech_path.write_text(SPEECH_SCRIPT, encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                        "-File", str(speech_path), "-PlanFile", str(PLAN), "-OutputDirectory", str(work)],
                       check=True, timeout=120)
        inputs, filters, labels = [], [], []
        for index, segment in enumerate(plan["segments"]):
            audio_path = work / (segment["id"] + ".wav")
            with wave.open(str(audio_path), "rb") as audio:
                seconds = audio.getnframes() / audio.getframerate()
                assert audio.getnframes() > 0
            report["segments"].append({**segment, "speech_duration_seconds": round(seconds, 6),
                                       "speech_end_seconds": round(segment["start"] + seconds, 6)})
            save()
            assert seconds <= segment["end"] - segment["start"], f"Shorten narration segment {segment['id']}; speech exceeds its real-time window."
            inputs.extend(["-i", str(audio_path)])
            filters.append(f"[{index}:a]aresample=48000,adelay={round(segment['start'] * 1000)}:all=1[v{index}]")
            labels.append(f"[v{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,"
                       f"loudnorm=I=-16:TP=-1.5:LRA=11,apad=whole_dur={duration},atrim=duration={duration}[narration]")
        narration = work / "narration.wav"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
                        "-map", "[narration]", "-ar", "48000", "-c:a", "pcm_s16le", str(narration)], check=True, timeout=90)
        candidate = work / "narrated.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(original), "-i", str(narration),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-metadata", "comment=Synthetic narration added after the continuous actual application recording; video unchanged.",
                        "-metadata:s:a:0", "title=Synthetic English narration - Microsoft Zira Desktop",
                        "-metadata:s:a:0", "language=eng", "-movflags", "+faststart", str(candidate)], check=True, timeout=90)
        report["output_media"] = probe(candidate)
        streams = report["output_media"]["streams"]
        video_stream = next(item for item in streams if item["codec_type"] == "video")
        audio_stream = next(item for item in streams if item["codec_type"] == "audio")
        assert video_stream["codec_name"] == "h264" and video_stream["nb_frames"] == "5292"
        assert (video_stream["width"], video_stream["height"], video_stream["r_frame_rate"]) == (1920, 1080, "30/1")
        assert audio_stream["codec_name"] == "aac" and int(audio_stream["sample_rate"]) == 48000
        assert abs(float(report["output_media"]["format"]["duration"]) - duration) < 0.05
        assert float(report["output_media"]["format"]["duration"]) <= 180
        report["source_video_packet_sha256"] = video_hash(original)
        report["output_video_packet_sha256"] = video_hash(candidate)
        assert report["source_video_packet_sha256"] == report["output_video_packet_sha256"], "Video packets changed."
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(candidate), "-f", "null", "-"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=90)
        report["full_decode_passed"] = True
        levels = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(candidate),
                                 "-vn", "-af", "volumedetect", "-f", "null", "-"],
                                check=True, capture_output=True, text=True, timeout=60)
        report["volume_detection"] = [line.strip() for line in levels.stderr.splitlines()
                                       if "mean_volume:" in line or "max_volume:" in line]
        report["output_sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
        report["success"] = True
        report["finished_at"] = datetime.now(UTC).isoformat()
        save()
        shutil.copyfile(candidate, OUTPUT)
        (ROOT / "docs" / "validation" / "hackathon-voiceover.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"success": True, "output": OUTPUT.name, "voice": plan["voice"],
                          "video_packets_unchanged": True, "duration": report["output_media"]["format"]["duration"],
                          "segments": len(report["segments"]), "report": str(report_path.relative_to(ROOT))}), flush=True)
    except BaseException as error:
        report["success"] = False
        report["error_type"] = type(error).__name__
        save()
        raise


if __name__ == "__main__":
    main()
