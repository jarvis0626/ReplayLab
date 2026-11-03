"""Capture a real CodeLab tutorial and extract a new, unapproved Meta workflow.

Run with the separate Python installation containing Playwright. Source media,
runtime project IDs and full responses stay in ignored .artifacts. No existing
project is changed and no model proposal is approved by this helper.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MODEL = "meta-llama/Llama-3.2-3B-Instruct"
TRANSCRIPT = (
    '00:00 In the CodeLab simulation, open "Extensions Marketplace". '
    '"Preferences" is the wrong destination; use Extensions instead of Settings.\n'
    '00:06 Search for "Replay Formatter" and confirm "Search results". '
    'This tutorial demonstrates searching, not installing real software.'
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default="Hackathon live demonstration")
    parser.add_argument("--clone-from", help="Make a fresh practice copy of an existing prepared demo's genuine proposal and media; no new extraction is claimed.")
    args = parser.parse_args()
    if args.clone_from and not re.fullmatch(r"[a-f0-9]{32}", args.clone_from):
        parser.error("Clone source must be a project identifier.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("FFmpeg must already be installed.")
    work = ROOT / ".artifacts" / ("hackathon-preparation-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    work.mkdir(parents=True, exist_ok=False)
    report = {"success": False, "created_at": datetime.now(UTC).isoformat(), "phase": "initialization",
              "source": "Actual continuous browser interactions in labeled CodeLab simulation",
              "model": MODEL, "approved": False, "transcript": TRANSCRIPT}
    report_path = work / "preparation.json"

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    @contextmanager
    def record_outcome():
        save()
        try:
            yield
        except BaseException as error:
            # Exception messages from dependencies can contain request bodies or
            # environment values. Record only the class and our fixed phase.
            report["success"] = False
            report["error_type"] = type(error).__name__
            raise
        finally:
            report["finished_at"] = datetime.now(UTC).isoformat()
            save()

    with record_outcome(), sync_playwright() as p, ExitStack() as resources:
        report["phase"] = "provider_readiness"
        save()
        request = p.request.new_context(base_url="http://127.0.0.1:8010", timeout=180000)
        resources.callback(request.dispose)
        health = request.get("/api/health").json()
        assert health["provider"]["mode"] == "local_meta", "Select local Meta before preparation."
        source = work / "CodeLab-real-interaction-tutorial.mp4"
        original = None
        report["phase"] = "tutorial_source"
        save()
        if args.clone_from:
            original = request.get(f"/api/projects/{args.clone_from}").json()
            assert original["name"].startswith("Hackathon live demonstration")
            assert original["task"]["provider_mode"] == "local_meta" and original["video"]
            assert original["task"]["provenance"]["model"] == MODEL
            assert original["task"]["provenance"]["request_id"]
            media = request.get(original["video"]["url"])
            assert media.ok
            source.write_bytes(media.body())
            report["prepared_copy_from"] = args.clone_from
            report["new_model_extraction"] = False
        else:
            browser = p.chromium.launch(headless=True, channel="chromium")
            context = browser.new_context(viewport={"width": 1280, "height": 800},
                record_video_dir=str(work / "source"), record_video_size={"width": 1280, "height": 800})
            page = context.new_page()
            video = page.video
            page.goto("http://127.0.0.1:5173?digital-demo=1")
            expect(page).to_have_title("ReplayLab CodeLab")
            page.get_by_role("button", name="Extensions", exact=True).click()
            expect(page.get_by_role("heading", name="Extensions Marketplace", exact=True)).to_be_visible()
            page.wait_for_timeout(6000)
            page.get_by_role("textbox", name="Search extensions", exact=True).press_sequentially("Replay Formatter", delay=85)
            expect(page.get_by_role("heading", name="Search results", exact=True)).to_be_visible()
            page.wait_for_timeout(6000)
            context.close()
            browser.close()
            subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(video.path()),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(source)], check=True, timeout=90)
        report["tutorial_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        report["tutorial_file"] = str(source.relative_to(ROOT))
        report["phase"] = "project_creation"
        save()
        response = request.post("/api/projects", data={"name": args.name, "modality": "digital"})
        assert response.ok
        project_id = response.json()["id"]
        report["project_id"] = project_id
        report["phase"] = "tutorial_upload"
        save()
        transcript = TRANSCRIPT if original is None else "\n".join(
            f"{int(item['start']) // 60:02}:{int(item['start']) % 60:02} {item['text']}"
            for item in original["tutorial"]["transcript_segments"])
        response = request.post(f"/api/projects/{project_id}/tutorial", data={
            "title": "Prepared tutorial: find Replay Formatter in the CodeLab simulation",
            "transcript": transcript, "usage_rights_confirmed": True})
        assert response.ok
        response = request.post(f"/api/projects/{project_id}/video", multipart={
            "file": {"name": source.name, "mimeType": "video/mp4", "buffer": source.read_bytes()},
            "usage_rights_confirmed": "true"})
        assert response.ok

        def wait_ready():
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                project = request.get(f"/api/projects/{project_id}").json()
                if project["status"] == "error":
                    raise RuntimeError(project.get("error") or "Processing failed")
                if project["status"] != "processing":
                    return project
                time.sleep(0.5)
            raise TimeoutError("Processing did not complete")

        project = wait_ready()
        report["source_frame_count"] = len(project["frames"])
        assert project["video"] and project["frames"]
        report["phase"] = "workflow_extraction" if original is None else "prepared_workflow_copy"
        save()
        if original is None:
            began = time.monotonic()
            assert request.post(f"/api/projects/{project_id}/extract", data={"cloud_consent": False}).ok
            project = wait_ready()
            report["extraction_ms"] = round((time.monotonic() - began) * 1000, 2)
            report["new_model_extraction"] = True
        else:
            task = original["task"]
            for step in task["steps"]:
                original_frame = next((frame for frame in original["frames"]
                    if frame["id"] == step["reference_frame_id"]), None)
                source_timestamp = original_frame["timestamp"] if original_frame else step["timestamp_end"]
                step["reference_frame_id"] = min(project["frames"], key=lambda item: abs(item["timestamp"] - source_timestamp))["id"]
            task["provenance"]["prepared_copy_from"] = args.clone_from
            response = request.put(f"/api/projects/{project_id}/task", data=task)
            assert response.ok
            project = response.json()
        assert project["task"]["provider_mode"] == "local_meta"
        assert project["task"]["provenance"]["model"] == MODEL
        assert project["task"]["provenance"]["request_id"]
        assert project["task"]["provenance"]["source_frame_count"] > 0
        assert not project["approved"] and not project["completed_step_ids"]
        report["proposal"] = project["task"]
        report["phase"] = "complete"
        report["success"] = True
        save()
        (ROOT / ".artifacts" / "hackathon-demo-project.json").write_text(json.dumps({
            "project_id": project_id, "preparation_report": str(report_path.relative_to(ROOT)),
            "tutorial_file": str(source.relative_to(ROOT))}, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"success": True, "project_id": project_id, "steps": len(project["task"]["steps"]),
                          "source_frames": len(project["frames"]), "report": str(report_path.relative_to(ROOT))}), flush=True)


if __name__ == "__main__":
    main()
