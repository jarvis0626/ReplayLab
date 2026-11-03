"""Rehearse or record an uncut, real local Meta browser demonstration.

The target is a separate interactive CodeLab tab, visibly identified as a
simulation. Chromium's source-selection flag chooses that tab after ReplayLab's
share gesture; getDisplayMedia, pixels, OCR, model responses and verdicts are
never replaced. A successful matching rehearsal is required before recording.
This script approves and practices the explicitly supplied prepared project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODEL = "meta-llama/Llama-3.2-3B-Instruct"
WIDTH, HEIGHT = 1920, 1080


def task_fingerprint(task):
    """Match the rehearsed approved rules while excluding unrelated run IDs."""
    def semantic(value):
        if isinstance(value, dict):
            return {key: semantic(item) for key, item in value.items()
                    if key not in {"id", "provenance", "reference_frame_id"}}
        if isinstance(value, list):
            return [semantic(item) for item in value]
        return value
    return hashlib.sha256(json.dumps(semantic(task), sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", required=True,
                        help="A new, unapproved prepared Meta project owned by this demo run.")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--rehearsal-report", type=Path,
                        help="Successful report from a matching --project-id rehearsal.")
    parser.add_argument("--output", type=Path, default=ROOT / "ReplayLab_Meta_Hackathon_Demo.mp4")
    parser.add_argument("--duration", type=float, default=176,
                        help="Actual recording end target, including natural waiting (175..178 seconds).")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{32}", args.project_id):
        parser.error("Project identifier must contain 32 lowercase hexadecimal characters.")
    if not 175 <= args.duration <= 178:
        parser.error("Duration must be between 175 and 178 seconds, below the 180-second limit.")
    if args.record and not args.rehearsal_report:
        parser.error("Record only after a successful rehearsal; provide --rehearsal-report.")
    if args.rehearsal_report:
        args.rehearsal_report = args.rehearsal_report.resolve()
    if args.output.resolve().parent != ROOT:
        parser.error("The final MP4 must be written in the repository root.")
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if args.record and not (ffmpeg and ffprobe):
        raise SystemExit("FFmpeg and FFprobe are required for MP4 recording and verification.")
    run = ROOT / ".artifacts" / ("hackathon-demo-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    run.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), run / "executed-recorder.py")
    report_path = run / ("recording.json" if args.record else "rehearsal.json")
    report = {
        "started_at": datetime.now(UTC).isoformat(), "success": False,
        "recorded": False, "recording_requested": args.record,
        "project_id": args.project_id, "provider": "local_meta", "model": MODEL,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "recording_scope": "One actual ReplayLab browser page, captured continuously. Target tab appears through its real shared-stream preview.",
        "source_selection": "Chromium test-only tab title selector after the real application share gesture; no human OS picker is claimed.",
        "chapters": [], "cases": [], "page_errors": [], "nonlocal_browser_hosts": [],
        "screen_submission_count": 0, "stream": None, "video": None,
        "limitations": [
            "CodeLab is a clearly labeled interactive simulation; no real VS Code extension is installed.",
            "The workflow was genuinely extracted before the take and is presented as prepared, not live extraction.",
            "Local OCR reads actual captured pixels. Meta Llama receives redacted OCR text, not images.",
            "The evaluation dashboard is a separate controlled local OCR suite, not a Meta model accuracy benchmark.",
            "This small demonstration does not establish broad accuracy, SAM/camera performance, hosted Muse availability or hackathon eligibility.",
            "The recording is silent. Separate narration instructions are supplied; no synthetic audio is presented as live speech.",
        ],
    }
    started = None
    context = target_context = browser = request = coach = video = None
    errors, remote_hosts, submissions = [], set(), []

    def save():
        report["page_errors"] = errors
        report["nonlocal_browser_hosts"] = sorted(remote_hosts)
        report["screen_submission_count"] = len(submissions)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")

    def elapsed():
        return time.perf_counter() - started

    def chapter(name):
        assert not re.search(r"nvapi-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{24,}", coach.locator("body").inner_text()), "A credential-shaped string appeared in the controlled application; recording stopped."
        report["chapters"].append({"name": name, "at_seconds": round(elapsed(), 3)})
        save()
        print(json.dumps({"chapter": name, "elapsed_seconds": round(elapsed(), 2)}), flush=True)
        if args.record and elapsed() > 174:
            raise AssertionError("The natural workflow exceeded its available time. This take is not published.")

    def pace(at):
        if not args.record:
            return
        while elapsed() < at:
            coach.wait_for_timeout(min(500, (at - elapsed()) * 1000))

    def navigate(name):
        coach.get_by_role("navigation", name="Project workspace").get_by_role("button", name=re.compile("^" + name)).click()

    def observe_request(outgoing):
        parsed = urlsplit(outgoing.url)
        if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            remote_hosts.add(parsed.hostname)
        if parsed.path.endswith("/screen-check"):
            submissions.append({"at_seconds": round(elapsed(), 3), "method": outgoing.method})

    with sync_playwright() as playwright:
        try:
            request = playwright.request.new_context(base_url="http://127.0.0.1:8010")
            health = request.get("/api/health")
            assert health.ok and health.json()["provider"]["mode"] == "local_meta", "Start the genuine local Meta provider first."
            project_response = request.get(f"/api/projects/{args.project_id}")
            assert project_response.ok, "Prepared demonstration project does not exist."
            project = project_response.json()
            assert project["approved"] is False and project["completed_step_ids"] == [], "Use a fresh unapproved demonstration project."
            assert project["task"]["provider_mode"] == "local_meta"
            assert len(project["task"]["steps"]) == 2, "This take is rehearsed for a two-step workflow."
            assert project.get("video") and project.get("tutorial"), "An actual tutorial video and transcript must be prepared."
            report["task_fingerprint"] = task_fingerprint(project["task"])
            report["workflow_provenance"] = project["task"]["provenance"]
            if args.record:
                prior = json.loads(args.rehearsal_report.read_text(encoding="utf-8"))
                assert prior["success"] is True and prior["recorded"] is False, "A completed rehearsal is required."
                assert prior["task_fingerprint"] == report["task_fingerprint"], "The prepared task differs from the rehearsed task."
                assert prior["script_sha256"] == report["script_sha256"], "Rehearse the current recorder implementation before recording."
                assert [item["actual"] for item in prior["cases"]] == ["fail", "pass", "uncertain"]
                report["rehearsal_report"] = str(args.rehearsal_report.relative_to(ROOT))
            evaluation_response = request.get("/api/evaluation/digital")
            assert evaluation_response.ok and evaluation_response.json()["sample_size"] > 0, "Execute the actual local OCR evaluation before recording."
            report["evaluation"] = {key: evaluation_response.json().get(key) for key in
                ["sample_size", "correct", "accuracy", "false_certainty_rate", "uncertainty_recall", "latency_ms", "measured_at", "dataset"]}
            browser = playwright.chromium.launch(headless=True, channel="chromium", args=[
                "--auto-select-tab-capture-source-by-title=ReplayLab CodeLab",
                "--enable-usermedia-screen-capturing", "--allow-http-screen-capture",
                "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ])
            report["browser"] = browser.version
            # Only the coach is recorded. A separate unrecorded context keeps
            # the real captured source rendering while the coach is visible.
            target_context = browser.new_context(viewport={"width": 1440, "height": 900})
            simulator = target_context.new_page()
            simulator.goto("http://127.0.0.1:5173/?digital-demo=1")
            expect(simulator).to_have_title("ReplayLab CodeLab")
            simulator.get_by_role("button", name="Settings", exact=True).click()
            options = {"viewport": {"width": WIDTH, "height": HEIGHT}}
            if args.record:
                options.update(record_video_dir=str(run / "native"), record_video_size={"width": WIDTH, "height": HEIGHT})
            context = browser.new_context(**options)
            coach = context.new_page()
            video = coach.video
            started = time.perf_counter()
            coach.set_default_timeout(15000)
            coach.on("pageerror", lambda error: errors.append(type(error).__name__))
            coach.on("request", observe_request)
            coach.goto("http://127.0.0.1:5173")
            expect(coach.get_by_role("button", name="Open provider settings", exact=True)).to_be_visible()
            chapter("Running ReplayLab dashboard; local Meta provider selected")
            pace(11)
            target = coach.locator(".project-card-main").filter(has=coach.get_by_role("heading", name=project["name"], exact=True))
            target.click()
            navigate("Demonstration")
            tutorial = coach.get_by_label("Demonstration video", exact=True)
            expect(tutorial).to_be_visible()
            tutorial.scroll_into_view_if_needed()
            tutorial.evaluate("video => video.play()")
            chapter("Prepared tutorial: actual source video and timestamped transcript")
            coach.wait_for_timeout(5000)
            tutorial.evaluate("video => video.pause()")
            segments = coach.locator(".tutorial-segments")
            segments.scroll_into_view_if_needed()
            coach.wait_for_timeout(2500)
            pace(29)
            navigate("Task & graph")
            expect(coach.get_by_text("LOCAL_META PROPOSAL", exact=True)).to_be_visible()
            expect(coach.locator(".react-flow__node")).to_have_count(2)
            chapter("Prepared genuinely Meta-generated graph; review observable expected states")
            coach.wait_for_timeout(2500)
            with coach.expect_response(lambda response: response.url.endswith("/approve")) as approved:
                coach.get_by_role("button", name="Approve task", exact=True).click()
            assert approved.value.ok
            pace(43)
            coach.get_by_role("button", name="Start practice", exact=True).click()
            expect(coach.get_by_role("button", name="Choose screen or window", exact=True)).to_be_enabled()

            def fresh_preview():
                simulator.bring_to_front()
                simulator.wait_for_timeout(550)
                coach.bring_to_front()
                coach.get_by_label("Shared screen preview", exact=True).evaluate("""async video => {
                    await new Promise(resolve => {let count=0;const next=()=>{if(++count>=2)resolve();else video.requestVideoFrameCallback(next)};
                    video.requestVideoFrameCallback(next);setTimeout(resolve,1800)});
                }""")

            def inspect_case(case_id, expected, action, first=False):
                if action:
                    action()
                if not first:
                    fresh_preview()
                chapter(case_id + ": observe actual target tab at natural speed")
                before = len(submissions)
                tick = time.perf_counter()
                with coach.expect_response(lambda response: response.url.endswith("/screen-check"), timeout=75000) as checked:
                    if first:
                        coach.get_by_role("button", name="Choose screen or window", exact=True).click()
                        expect(coach.get_by_text("Visible capture scope: browser tab", exact=True)).to_be_visible(timeout=20000)
                    else:
                        coach.get_by_role("button", name="Resume", exact=True).click()
                        coach.get_by_role("button", name="Recheck", exact=True).click()
                response = checked.value
                coach.get_by_role("button", name="Pause", exact=True).click()
                assert response.ok, f"Actual screen inference returned HTTP {response.status}."
                value = response.json()
                provenance = value["observation"]["provenance"]
                result = value["result"]
                report["cases"].append({"id": case_id, "expected": expected, "actual": result["status"],
                    "http_status": response.status, "latency_ms": round((time.perf_counter() - tick) * 1000, 2),
                    "observation_provenance": provenance, "source_scope": value.get("source_scope"),
                    "explanation": result["explanation"], "rule_results": result["rule_results"],
                    "completed_step_ids": value["completed_step_ids"],
                    "explanation_provider": (value.get("verification") or {}).get("provider", {}).get("explanation")})
                save()
                assert len(submissions) == before + 1, "An unexpected additional screen submission occurred."
                assert result["status"] == expected, "The actual verdict differed; this take is not published."
                if expected == "fail":
                    assert any(rule.get("status") == "fail" and rule.get("correction") and rule.get("evidence")
                               for rule in result["rule_results"]), "The FAIL needs actual mismatch evidence and a correction."
                assert result["provider_mode"] == "local_meta" and value.get("source_scope") == "browser tab"
                assert provenance.get("model") == MODEL and provenance.get("request_id")
                assert provenance.get("api_response_validated") is True and provenance.get("live_api_verified") is True
                assert provenance.get("local_only") is True and provenance.get("vision_inference") is False
                progress = [project["task"]["steps"][0]["id"]] if expected in {"pass", "uncertain"} else []
                assert value["completed_step_ids"] == progress
                region = coach.get_by_role("region", name="Screen verification result")
                region.scroll_into_view_if_needed()
                expect(region.get_by_text(expected.upper(), exact=True).first).to_be_visible()
                chapter(case_id + ": actual " + expected.upper() + ", evidence and correction")
                coach.wait_for_timeout(2200)
                coach.get_by_text("Inspect decision and source evidence", exact=True).click()
                coach.locator(".verification-inspector").scroll_into_view_if_needed()
                coach.wait_for_timeout(1800)
                coach.screenshot(path=str(run / (case_id + ".png")), full_page=True)
                coach.get_by_label("Shared screen preview", exact=True).scroll_into_view_if_needed()
                return value

            inspect_case("intentional-settings-mistake", "fail", None, first=True)
            preview = coach.get_by_label("Shared screen preview", exact=True)
            report["stream"] = preview.evaluate("video => {window.__hackathonTrack=video.srcObject.getVideoTracks()[0];return {settings:window.__hackathonTrack.getSettings(),state:window.__hackathonTrack.readyState,width:video.videoWidth,height:video.videoHeight}}")
            assert report["stream"]["settings"]["displaySurface"] == "browser" and report["stream"]["state"] == "live"
            pace(79)
            inspect_case("corrected-extensions-panel", "pass", lambda: simulator.get_by_role("button", name="Extensions", exact=True).click())
            pace(111)
            inspect_case("unrelated-explorer-screen", "uncertain", lambda: simulator.get_by_role("button", name="Explorer", exact=True).click())
            pace(143)
            coach.get_by_role("button", name="Stop sharing", exact=True).click()
            assert coach.evaluate("window.__hackathonTrack.readyState") == "ended"
            report["stream_stopped"] = True
            navigate("Evaluation")
            expect(coach.get_by_text(str(report["evaluation"]["sample_size"]) + " cases", exact=True)).to_be_visible()
            coach.evaluate("scrollTo(0,0)")
            chapter("Actual executed controlled local OCR evaluation; separate from Meta inference cases")
            coach.wait_for_timeout(3500)
            coach.locator(".calibration-stats").scroll_into_view_if_needed()
            coach.wait_for_timeout(3000)
            pace(160)
            navigate("Task & graph")
            coach.get_by_role("button", name="Open provider settings", exact=True).click()
            dialog = coach.get_by_role("dialog")
            expect(dialog.get_by_text(re.compile(re.escape(MODEL)))).to_be_visible()
            expect(dialog.get_by_text(re.compile("Built with Llama\\."))).to_be_visible()
            expect(dialog.get_by_role("checkbox", name=re.compile("I consent to sending"))).to_have_count(0)
            chapter("Actual local Meta Llama model; OCR/text boundary and evidence-backed decisions")
            coach.wait_for_timeout(2500)
            dialog.get_by_role("button", name="Save preferences", exact=True).click()
            coach.locator(".react-flow").scroll_into_view_if_needed()
            report["final_project"] = {key: request.get(f"/api/projects/{args.project_id}").json().get(key)
                                       for key in ["approved", "completed_step_ids"]}
            assert report["final_project"]["completed_step_ids"] == [project["task"]["steps"][0]["id"]]
            assert not errors and not remote_hosts and len(submissions) == 3
            report["success"] = True
            chapter("Finish on the working graph, with verified progress and an honest pending checkpoint")
            pace(args.duration)
            report["elapsed_seconds"] = round(elapsed(), 3)
            context.close()
            context = None
            if args.record:
                native = Path(video.path())
                # One continuous source. No trim, concat, speed change, frame
                # replacement, synthetic padding, overlays or audio are added.
                candidate = run / "candidate.mp4"
                with (run / "ffmpeg.log").open("w", encoding="utf-8") as log:
                    subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(native),
                        "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-movflags", "+faststart", "-an", "-y", str(candidate)], stdout=log, stderr=log, check=True, timeout=180)
                metadata = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-show_entries",
                    "format=duration,size:stream=index,codec_name,codec_type,width,height,r_frame_rate,nb_frames", "-of", "json", str(candidate)]))
                report["video"] = metadata
                duration = float(metadata["format"]["duration"])
                stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
                assert 175 <= duration <= 180 and stream["codec_name"] == "h264"
                assert (stream["width"], stream["height"], stream["r_frame_rate"]) == (WIDTH, HEIGHT, "30/1")
                subprocess.run([ffmpeg, "-v", "error", "-i", str(candidate), "-f", "null", "-"], check=True, timeout=180,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                shutil.copyfile(candidate, args.output)
                report["recorded"] = True
                report["output"] = args.output.name
                report["output_sha256"] = hashlib.sha256(args.output.read_bytes()).hexdigest()
            save()
            print(json.dumps({"success": True, "recorded": report["recorded"], "report": str(report_path),
                              "duration_seconds": report.get("video", {}).get("format", {}).get("duration") if args.record else report["elapsed_seconds"]}), flush=True)
        except Exception as error:
            report["success"] = False
            report["error_type"] = type(error).__name__
            report["error_message"] = str(error)[:1000]
            if coach is not None and not coach.is_closed():
                try:
                    coach.screenshot(path=str(run / "failure.png"), full_page=True)
                except PlaywrightError as shot_error:
                    report["failure_screenshot_error"] = type(shot_error).__name__
            save()
            raise
        finally:
            if context is not None:
                context.close()
            if target_context is not None:
                target_context.close()
            if browser is not None:
                browser.close()
            if request is not None:
                request.dispose()
            save()


if __name__ == "__main__":
    main()
