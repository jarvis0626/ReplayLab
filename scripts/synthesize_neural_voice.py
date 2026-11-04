"""Synthesize only the supplied narration text using Microsoft Edge online speech.

Optional client setup stays local to this repo:
python -m pip install --target .artifacts/tts-client edge-tts==7.3.1

This does not upload video, application screenshots, credentials, or model media.
The selected neural voice is synthetic narration, not the user's recorded voice.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".artifacts" / "tts-client"))


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True, help="JSON with segments containing id, start, end, text.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--voice", default="en-US-GuyNeural")
    parser.add_argument("--rate", default="+0%")
    args = parser.parse_args()
    plan_path, output = args.plan.resolve(), args.output_dir.resolve()
    if not plan_path.is_relative_to(ROOT) or not plan_path.is_file():
        parser.error("Use a narration plan inside this repository.")
    if not output.is_relative_to(ROOT / ".artifacts"):
        parser.error("Write generated speech only under this repository's ignored .artifacts directory.")
    if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}-[A-Za-z]+Neural", args.voice):
        parser.error("Supply a named Microsoft neural voice.")
    if not re.fullmatch(r"[+-]\d{1,2}%", args.rate):
        parser.error("Use a bounded voice rate such as +0%.")
    try:
        import edge_tts
    except ImportError:
        parser.error("Install the optional pinned edge-tts client under .artifacts/tts-client first.")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    segments = plan["segments"]
    if not 1 <= len(segments) <= 40:
        parser.error("Narration needs between one and forty short segments.")
    identifiers = set()
    for item in segments:
        if (not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", item["id"])
                or item["id"] in identifiers or not 0 <= item["start"] < item["end"]
                or not isinstance(item["text"], str) or not 1 <= len(item["text"]) <= 5000):
            parser.error("Invalid, duplicated, or excessive narration segment.")
        identifiers.add(item["id"])
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "neural-speech.json"
    report = {"success": False, "created_at": datetime.now(UTC).isoformat(),
              "synthetic_narration": True, "provider": "Microsoft Edge online speech via edge-tts",
              "client_version": importlib.metadata.version("edge-tts"), "voice": args.voice,
              "rate": args.rate, "online_content": "Only the supplied narration text; no application media or credentials.",
              "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(), "segments": []}
    semaphore = asyncio.Semaphore(3)

    async def speak(item):
        async with semaphore:
            target = output / (item["id"] + ".mp3")
            speaker = edge_tts.Communicate(item["text"], args.voice, rate=args.rate,
                                          connect_timeout=10, receive_timeout=40)
            async with asyncio.timeout(60):
                await speaker.save(str(target))
            duration_text = await asyncio.to_thread(subprocess.check_output, [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(target)], text=True)
            duration = float(duration_text.strip())
            return {**item, "file": str(target.relative_to(ROOT)), "duration_seconds": duration,
                    "speech_end_seconds": round(item["start"] + duration, 6),
                    "fits_window": duration <= item["end"] - item["start"],
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    try:
        report["segments"] = await asyncio.gather(*(speak(item) for item in segments))
        report["success"] = all(item["fits_window"] for item in report["segments"])
        report["finished_at"] = datetime.now(UTC).isoformat()
    except Exception as error:
        report["error_type"] = type(error).__name__
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"success": report["success"], "voice": args.voice,
                      "segments": len(report["segments"]),
                      "overflowing": [item["id"] for item in report["segments"] if not item["fits_window"]],
                      "report": str(report_path.relative_to(ROOT))}), flush=True)
    if not report["success"]:
        raise SystemExit("Shorten overflowing text to fit the recorded scenes; no video speed change is applied.")


if __name__ == "__main__":
    asyncio.run(main())
