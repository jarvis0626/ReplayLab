"""Real Chromium UI checks and optional silent three-minute screen recording.

Requires Playwright + its Chromium browser, installed separately from API deps.
No network route interception or fabricated UI result is used. Camera input uses
Chromium's synthetic fake-device stream, never a physical camera.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / "docs" / "assets" / "screenshots"


def log(phase: str, **details):
    print(json.dumps({"phase": phase, **details}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8010")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    failures = []
    outcomes = []
    temporary_projects = []
    showcase_id = None
    completed = False
    started = time.monotonic()

    with sync_playwright() as playwright, tempfile.TemporaryDirectory(prefix="replaylab-browser-") as recordings:
        browser = playwright.chromium.launch(
            headless=True, args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"]
        )
        request = playwright.request.new_context(base_url=args.api_url)
        assert request.get("/api/health").ok, "API is not ready"
        assert request.post("/api/provider", data={"mode": "mock"}).ok

        def context(record=False, permissions=None):
            settings = {"viewport": {"width": 1440, "height": 1000}}
            if permissions:
                settings["permissions"] = permissions
            if record:
                settings.update(record_video_dir=recordings,
                                record_video_size={"width": 1440, "height": 1000})
            result = browser.new_context(**settings)
            result.on("page", lambda page: page.on("pageerror", lambda error: failures.append(str(error))))
            return result

        def screenshot(page, name):
            scroll_y = page.evaluate("scrollY")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(100)
            page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True,
                            animations="disabled")
            page.evaluate("position => window.scrollTo(0, position)", scroll_y)

        def no_overflow(page, label):
            dimensions = page.evaluate("""() => ({
                viewport: innerWidth,
                body: document.body.scrollWidth,
                root: document.documentElement.scrollWidth
            })""")
            assert dimensions["body"] <= dimensions["viewport"] + 1, (label, dimensions)
            assert dimensions["root"] <= dimensions["viewport"] + 1, (label, dimensions)
            outcomes.append({"check": label, "result": "pass", **dimensions})

        def tab(page, name):
            page.get_by_role("navigation", name="Project workspace").get_by_role(
                "button", name=re.compile(name)
            ).click()

        def new_demo(page):
            page.goto(args.base_url)
            expect(page.get_by_text("MOCK MODE", exact=True)).to_be_visible()
            with page.expect_response(lambda response: response.url.endswith("/api/projects/demo")
                                      and response.request.method == "POST") as waiting:
                page.get_by_role("button", name="Explore the sample project", exact=True).click()
            data = waiting.value.json()
            assert data.get("task"), data
            expect(page.get_by_role("button", name="Approve task", exact=True)).to_be_visible()
            return data

        def fixture(page, label, verdict, screenshot_name=None):
            previous = page.get_by_role("button", name="Try another image", exact=True)
            if previous.is_visible():
                previous.click()
            page.get_by_role("button", name="Load fixture", exact=True).click()
            page.locator(".fixture-card").filter(has=page.locator("strong", has_text=label)).click()
            expect(page.get_by_role("button", name="Verify checkpoint", exact=True)).to_be_enabled()
            with page.expect_response(lambda response: "/api/attempts/" in response.url
                                      and response.url.endswith("/verify")) as waiting:
                page.get_by_role("button", name="Verify checkpoint", exact=True).click()
            response = waiting.value
            assert response.ok, response.text()
            actual = response.json()["result"]
            assert actual["status"] == verdict, actual
            panel = page.get_by_role("region", name="Verification result")
            expect(panel).to_be_visible()
            expect(panel.locator(".result-heading")).to_contain_text(verdict.upper())
            assert actual["provider_mode"] == "mock"
            outcomes.append({"check": label, "result": verdict,
                             "rule_statuses": [r["status"] for r in actual["rule_results"]]})
            if screenshot_name:
                panel.scroll_into_view_if_needed()
                screenshot(page, screenshot_name)
            log("checkpoint", fixture=label, verdict=verdict)
            return actual

        try:
            # Exercise genuine file upload and extraction before the paced recording.
            upload_context = context()
            page = upload_context.new_page()
            page.goto(args.base_url)
            expect(page.get_by_text("MOCK MODE", exact=True)).to_be_visible()
            screenshot(page, "dashboard")
            no_overflow(page, "desktop-dashboard")
            page.locator(".main-content").get_by_role("button", name="New project", exact=True).click()
            page.get_by_label("Project name", exact=True).fill("Browser QA upload " + str(int(time.time())))
            with page.expect_response(lambda response: response.url.endswith("/api/projects")
                                      and response.request.method == "POST") as waiting:
                page.get_by_role("dialog").get_by_role("button", name="Create project", exact=True).click()
            uploaded_project = waiting.value.json()
            temporary_projects.append(uploaded_project["id"])
            media = request.get("/api/demo/video")
            assert media.ok
            page.get_by_label("Upload demonstration video", exact=True).set_input_files({
                "name": "actual-synthetic-video.mp4", "mimeType": "video/mp4", "buffer": media.body()
            })
            expect(page.locator(".keyframe")).to_have_count(4, timeout=60000)
            expect(page.get_by_role("button", name="Generate task steps", exact=True)).to_be_enabled()
            page.get_by_role("button", name="Generate task steps", exact=True).click()
            expect(page.get_by_role("button", name="Review task & graph", exact=True)).to_be_visible(timeout=60000)
            project_state = request.get(f"/api/projects/{uploaded_project['id']}").json()
            assert project_state["task"]["provenance"]["inferred_from_video"] is False
            assert len(project_state["frames"]) == 4
            outcomes.append({"check": "UI MP4 upload and explicit mock extraction", "result": "pass"})
            upload_context.close()
            log("upload-verified", project_id=uploaded_project["id"])

            demo_context = context(record=args.record)
            page = demo_context.new_page()
            recording_start = time.monotonic()

            def pace(target):
                if args.record:
                    remaining = target - (time.monotonic() - recording_start)
                    while remaining > 0:
                        page.wait_for_timeout(min(remaining, 10) * 1000)
                        remaining = target - (time.monotonic() - recording_start)

            page.goto(args.base_url)
            expect(page.get_by_text("MOCK MODE", exact=True)).to_be_visible()
            pace(10)
            project = new_demo(page)
            showcase_id = project["id"]
            log("demo-created", project_id=showcase_id)
            expect(page.locator(".react-flow__node")).to_have_count(4)
            no_overflow(page, "desktop-task-graph")
            screenshot(page, "task-graph")
            pace(22)
            tab(page, "^Demonstration$")
            video = page.get_by_label("Demonstration video", exact=True)
            expect(video).to_be_visible()
            page.wait_for_function("document.querySelector('video')?.readyState >= 1")
            metadata = video.evaluate("video => ({duration: video.duration, width: video.videoWidth, height: video.videoHeight})")
            assert metadata["duration"] > 0 and metadata["width"] > 0
            video.evaluate("video => video.play()")
            page.wait_for_timeout(1300)
            playback_time = video.evaluate("video => video.currentTime")
            assert playback_time > 0.5, playback_time
            video.evaluate("video => video.pause()")
            expect(page.locator(".keyframe")).to_have_count(4)
            screenshot(page, "studio")
            outcomes.append({"check": "Actual MP4 metadata and playback", "result": "pass", **metadata})
            pace(40)

            tab(page, "^Task & graph")
            page.locator(".react-flow__node").filter(has_text="Position blue above red").click()
            expect(page.get_by_label("Step title", exact=True)).to_have_value("Position blue above red")
            instruction = page.locator(".step-editor textarea")
            original_instruction = instruction.input_value()
            instruction.fill(original_instruction + " Reviewed in browser QA.")
            page.get_by_role("button", name="Save changes", exact=True).click()
            expect(page.get_by_role("button", name="Approve task", exact=True)).to_be_enabled()
            page.get_by_role("button", name="Approve task", exact=True).click()
            expect(page.get_by_role("button", name="Start practice", exact=True)).to_be_visible()
            approved = request.get(f"/api/projects/{showcase_id}").json()
            assert approved["approved"] is True
            assert "Reviewed in browser QA." in approved["task"]["steps"][1]["description"]
            outcomes.append({"check": "Graph selection, edit, save, approval", "result": "pass"})
            pace(58)

            page.get_by_role("button", name="Start practice", exact=True).click()
            fixture(page, "First checkpoint", "pass", "checkpoint-pass")
            pace(78)
            page.get_by_role("button", name="Next checkpoint", exact=True).click()
            failure = fixture(page, "Blue block to the right", "fail", "checkpoint-fail")
            assert any(rule["kind"] == "aligned" and rule["status"] == "fail"
                       for rule in failure["rule_results"])
            pace(99)
            fixture(page, "Obstructed camera view", "uncertain", "checkpoint-uncertain")
            pace(118)
            fixture(page, "Second checkpoint", "pass")
            pace(132)
            page.get_by_role("button", name="Next checkpoint", exact=True).click()
            fixture(page, "Third checkpoint", "pass")
            page.get_by_role("button", name="Next checkpoint", exact=True).click()
            fixture(page, "Four-block reference", "pass", "task-complete")
            expect(page.get_by_text("4 / 4 steps complete", exact=True)).to_be_visible()
            expect(page.get_by_text("Every checkpoint is verified.", exact=True)).to_be_visible()
            outcomes.append({"check": "Four dependent steps complete", "result": "pass"})
            pace(150)

            tab(page, "^Evaluation$")
            expect(page.locator(".eval-score")).to_contain_text("25")
            expect(page.locator(".table-scroll tbody tr")).to_have_count(25)
            expect(page.locator(".confusion-table")).to_be_visible()
            screenshot(page, "evaluation")
            no_overflow(page, "desktop-evaluation")
            outcomes.append({"check": "25-case evaluation and confusion matrix", "result": "pass"})
            pace(174)
            page.get_by_role("button", name="Open provider settings", exact=True).click()
            expect(page.get_by_role("dialog")).to_contain_text("Offline / mock")
            pace(180)
            page.get_by_role("button", name="Close settings", exact=True).click()
            video_path = page.video.path() if args.record else None
            demo_context.close()

            # Tablet layout and actual synthetic camera capture, outside recording.
            camera_context = context(permissions=["camera"])
            page = camera_context.new_page()
            camera_project = new_demo(page)
            temporary_projects.append(camera_project["id"])
            page.get_by_role("button", name="Approve task", exact=True).click()
            page.get_by_role("button", name="Start practice", exact=True).click()
            page.get_by_role("button", name="Start camera", exact=True).click()
            expect(page.get_by_label("Live camera preview", exact=True)).to_be_visible()
            page.wait_for_function("document.querySelector('.webcam-preview')?.videoWidth > 0")
            page.get_by_role("button", name="Capture", exact=True).click()
            expect(page.get_by_role("button", name="Verify checkpoint", exact=True)).to_be_enabled()
            page.get_by_role("button", name="Verify checkpoint", exact=True).click()
            expect(page.get_by_role("region", name="Verification result")).to_contain_text("UNCERTAIN")
            expect(page.get_by_role("region", name="Verification result")).to_contain_text("unknown")
            screenshot(page, "synthetic-camera-uncertain")
            outcomes.append({"check": "Chromium synthetic camera capture -> unknown image -> UNCERTAIN", "result": "pass"})
            page.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow(page, "tablet-practice")
            screenshot(page, "tablet-practice")
            tab(page, "^Evaluation$")
            expect(page.locator(".table-scroll tbody tr")).to_have_count(25)
            no_overflow(page, "tablet-evaluation")
            tab(page, "^Task & graph")
            expect(page.locator(".react-flow__node")).to_have_count(4)
            no_overflow(page, "tablet-task-graph")
            page.get_by_role("button", name="ReplayLab dashboard", exact=True).click()
            no_overflow(page, "tablet-dashboard")
            camera_context.close()
            assert not failures, failures
            log("browser-checks-complete", checks=len(outcomes), page_errors=failures,
                showcase_project_id=showcase_id)

            if video_path:
                destination = ROOT / "docs" / "assets" / "demo.mp4"
                ffmpeg = shutil.which("ffmpeg")
                assert ffmpeg, "FFmpeg is required for the MP4 demonstration artifact"
                subprocess.run([
                    ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", video_path,
                    "-vf", "scale=1280:-2", "-t", "180", "-r", "25", "-frames:v", "4500",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", "-y", str(destination),
                ], check=True, timeout=180)
                metadata = json.loads(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(destination)
                ]))["format"]
                assert abs(float(metadata["duration"]) - 180) < 0.001, metadata
                log("recording-created", path=str(destination.relative_to(ROOT)), **metadata)
            report = {
                "provider": "mock", "browser": "Chromium headless", "checks": outcomes,
                "page_errors": failures, "showcase_project_id": showcase_id,
                "recorded": bool(args.record), "elapsed_seconds": round(time.monotonic() - started, 2),
            }
            completed = True
            log("result", **report)
        finally:
            if showcase_id and not completed:
                temporary_projects.append(showcase_id)
            for project_id in temporary_projects:
                response = request.delete(f"/api/projects/{project_id}")
                log("temporary-project-cleanup", project_id=project_id, status=response.status)
            request.dispose()
            browser.close()


if __name__ == "__main__":
    main()
