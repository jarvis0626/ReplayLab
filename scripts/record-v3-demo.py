"""Record actual ReplayLab UI interactions, real tab capture, OCR and evaluation.

Optional Playwright tooling runs separately from API dependencies. The sandbox
imitates an extension install; it never installs software. Chromium's test flag
selects a real getDisplayMedia source after the explicit share-button gesture.
No network responses, observations or verdicts are replaced. With --record,
the three-minute browser recording gets honest subtitles describing the source
and limitations; subtitles never replace the application's actual verdicts.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import tempfile
import time
import traceback
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "v3"


def log(event, **details):
    print(json.dumps({"event": event, **details}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8010")
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks = []
    assertions = []
    errors = []
    owned_projects = []
    succeeded = False
    with sync_playwright() as playwright, tempfile.TemporaryDirectory(prefix="replaylab-v3-") as temp:
        tempdir = Path(temp)
        request = playwright.request.new_context(base_url=args.api_url)
        assert request.get("/api/health").ok
        assert request.post("/api/provider", data={"mode": "mock"}).ok
        # Prepare a rights-cleared, synthetic source video before recording.
        source_response = request.post("/api/projects/digital-demo", data={})
        assert source_response.ok
        source = source_response.json()
        owned_projects.append(source["id"])
        media = request.get(source["video"]["url"])
        assert media.ok
        tutorial = tempdir / "codelab-tutorial.mp4"
        tutorial.write_bytes(media.body())
        browser = playwright.chromium.launch(headless=True, channel="chromium", args=[
            "--auto-select-tab-capture-source-by-title=ReplayLab CodeLab",
            "--enable-usermedia-screen-capturing", "--allow-http-screen-capture",
            "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
        ])
        options = {"viewport": {"width": 1440, "height": 1000}}
        if args.record:
            options.update(record_video_dir=str(tempdir / "recordings"), record_video_size={"width": 1440, "height": 1000})
        context = browser.new_context(**options)
        context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
        coach = context.new_page()
        began = time.monotonic()
        captions = []
        simulator = context.new_page()
        project_id = None

        def caption(text):
            captions.append({"at": time.monotonic() - began, "text": text})
            log("shot", number=len(captions), elapsed_seconds=round(time.monotonic() - began, 1))

        def pace(at):
            if not args.record:
                return
            while time.monotonic() - began < at:
                coach.wait_for_timeout(min(1000, (at - (time.monotonic() - began)) * 1000))

        def screenshot(name):
            coach.screenshot(path=str(OUTPUT / f"{name}.png"), full_page=True, animations="disabled")

        def no_overflow(label):
            dimensions = coach.evaluate("() => ({width:innerWidth,body:document.body.scrollWidth,root:document.documentElement.scrollWidth})")
            assert dimensions["body"] <= dimensions["width"] + 1 and dimensions["root"] <= dimensions["width"] + 1, label
            assertions.append(label)

        def tab(name):
            coach.get_by_role("navigation", name="Project workspace").get_by_role("button", name=re.compile(name)).click()

        def response_received(response):
            if response.url.endswith("/screen-check"):
                assert response.ok, f"screen check returned HTTP {response.status}"
                value = response.json()
                checks.append(value)
                log("screen-check", verdict=value["result"]["status"], reason=value["result"].get("reason"), completed=len(value["completed_step_ids"]))

        coach.on("response", response_received)

        def wait_check(verdict, after, completed=None, mismatch=None):
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                coach.wait_for_timeout(150)
                for value in checks[after:]:
                    if value["result"]["status"] != verdict:
                        continue
                    if completed is not None and len(value["completed_step_ids"]) != completed:
                        continue
                    if mismatch and value["verification"]["mismatch_classification"] != mismatch:
                        continue
                    assert value["result"]["provider_mode"] == "local_ocr"
                    assert value["screen_stored"] is False
                    assert value["verification"]["verdict"] == verdict
                    assert value["verification"]["workflow_id"] == project_id
                    return value
            raise AssertionError(f"No expected {verdict} screen-check arrived")

        def pause():
            coach.get_by_role("button", name="Pause", exact=True).click()
            expect(coach.get_by_text("SHARING · PAUSED", exact=True)).to_be_visible()

        def resume():
            simulator.bring_to_front()
            simulator.wait_for_timeout(400)
            coach.bring_to_front()
            preview = coach.get_by_label("Shared screen preview", exact=True)
            preview.scroll_into_view_if_needed()
            preview.evaluate("""async video => { await new Promise(resolve => {
                let count=0; const next=()=>{ if(++count >= 2) resolve(); else video.requestVideoFrameCallback(next); };
                video.requestVideoFrameCallback(next); setTimeout(resolve, 1600);
            }); }""")
            coach.get_by_role("button", name="Resume", exact=True).click()

        def inspect():
            coach.get_by_text("Inspect decision and source evidence", exact=True).click()
            coach.locator(".verification-inspector").first.scroll_into_view_if_needed()

        def review_target_screenshot(name, verdict, completed, mismatch=None):
            # Explicitly exercise the app's separate manual-image review path.
            # This avoids recording-mode background-tab delivery freezes; the
            # image is a fresh real browser capture, never synthesized evidence.
            simulator.bring_to_front()
            simulator.wait_for_timeout(300)
            image_path = tempdir / f"{name}.png"
            simulator.screenshot(path=str(image_path), animations="disabled")
            coach.bring_to_front()
            before = len(checks)
            coach.get_by_label("Upload screen screenshot", exact=True).set_input_files(str(image_path))
            value = wait_check(verdict, before, completed=completed, mismatch=mismatch)
            assert value["source_scope"] == "manually selected screenshot"
            return value

        try:
            coach.goto(args.base_url)
            expect(coach.get_by_text("MOCK MODE", exact=True)).to_be_visible(timeout=15000)
            caption("ReplayLab 3.0 · Watch. Learn. Do.\nTutorials explain actions. ReplayLab checks visible results.")
            screenshot("dashboard")
            pace(8)
            caption("This is an actual local app recording.\nWorkflow extraction is offline; screen OCR processes real captured pixels.")
            pace(17)
            coach.get_by_role("navigation", name="Main navigation").get_by_role("button", name="New project", exact=True).click()
            coach.get_by_label("Project name", exact=True).fill("ReplayLab 3 — verifiable extension workflow")
            coach.get_by_label("Workflow type", exact=True).select_option("digital")
            with coach.expect_response(lambda response: response.url.endswith("/api/projects") and response.request.method == "POST") as created:
                coach.get_by_role("dialog").get_by_role("button", name="Create project", exact=True).click()
            project_id = created.value.json()["id"]
            owned_projects.append(project_id)
            coach.get_by_role("checkbox", name="I have permission to upload and use this tutorial video.").check()
            coach.get_by_label("Upload demonstration video", exact=True).set_input_files(str(tutorial))
            expect(coach.get_by_label("Demonstration video", exact=True)).to_be_visible(timeout=30000)
            coach.get_by_label("Tutorial title (optional)", exact=True).fill("CodeLab extension: visible checkpoints")
            coach.get_by_label("Timestamped transcript", exact=True).fill(
                '00:00-00:03 Open "Extensions Marketplace".\n'
                '00:03-00:06 Find "Replay Formatter" in "Search results".\n'
                '00:06-00:09 Review "Extension details" for "Replay Formatter" and "Install extension".\n'
                '00:09-00:12 Confirm "Replay Formatter" is "Installed" and "Enabled".'
            )
            coach.get_by_role("checkbox", name=re.compile("I have permission to use this tutorial")).check()
            coach.get_by_role("button", name="Save tutorial source", exact=True).click()
            expect(coach.get_by_text("TRANSCRIPT SOURCE", exact=True)).to_be_visible()
            caption("Upload a rights-cleared tutorial and its timestamped transcript.\nFFmpeg extracts real source frames. Offline extraction proposes quoted UI labels.")
            screenshot("tutorial-source")
            pace(34)
            coach.get_by_role("button", name="Generate task steps", exact=True).click()
            expect(coach.get_by_role("button", name="Review task & graph", exact=True)).to_be_visible(timeout=30000)
            coach.get_by_role("button", name="Review task & graph", exact=True).click()
            expect(coach.locator(".react-flow__node")).to_have_count(4)
            coach.get_by_label("Reference application and version", exact=True).fill("CodeLab 1.0")
            # Review expected contradictions in the normal editor before approval.
            coach.locator(".react-flow__node").filter(has_text="Search results").click()
            coach.get_by_label("Visible contradictions (comma separated)", exact=True).first.fill("Preferences")
            coach.get_by_label(re.compile("^Grounded correction")).first.fill("Return to Extensions and search for Replay Formatter.")
            coach.get_by_role("button", name="Save changes", exact=True).click()
            expect(coach.get_by_role("button", name="Approve task", exact=True)).to_be_enabled()
            caption("One shared workflow graph: timestamps, visible conditions and prerequisites.\nReview and approve the proposal before verification can begin.")
            screenshot("workflow-review")
            pace(48)
            coach.get_by_role("button", name="Approve task", exact=True).click()
            coach.get_by_role("button", name="Start practice", exact=True).click()
            simulator.goto(args.base_url + "?digital-demo=1")
            expect(simulator).to_have_title("ReplayLab CodeLab")
            simulator.get_by_role("button", name="Extensions", exact=True).click()
            coach.bring_to_front()
            coach.get_by_role("checkbox", name=re.compile("Save relevant redacted decision evidence")).check()
            before = len(checks)
            coach.get_by_role("button", name="Choose screen or window", exact=True).click()
            expect(coach.get_by_text("Visible capture scope: browser tab", exact=True)).to_be_visible(timeout=20000)
            simulator.bring_to_front()
            simulator.wait_for_timeout(450)
            coach.bring_to_front()
            coach.get_by_label("Shared screen preview", exact=True).scroll_into_view_if_needed()
            first = wait_check("pass", before, completed=1)
            pause()
            assert first["verification"]["retained"] is True
            coach.get_by_label("Shared screen preview", exact=True).evaluate("video => { window.__v3DemoTrack=video.srcObject.getVideoTracks()[0]; }")
            caption("Real browser tab sharing → local OCR → evidence-backed PASS.\nCodeLab is a controlled software simulation, not a real extension installation.")
            screenshot("screen-pass")
            assertions.append("real tab capture and first-step PASS")
            pace(68)
            before = len(checks)
            simulator.get_by_role("button", name="Settings", exact=True).click()
            resume()
            wrong = wait_check("fail", before, completed=1, mismatch="unexpected_ui_state")
            pause()
            inspect()
            assert any("Preferences" in evidence for evidence in wrong["result"]["evidence"])
            caption("A visible wrong destination produces FAIL, with actual counterevidence.\nThe correction points back to the approved Extensions workflow.")
            screenshot("evidence-backed-fail")
            no_overflow("shared inspector fits desktop1440px")
            assertions.append("wrong panel FAIL with shared inspectable evidence")
            pace(83)
            before = len(checks)
            simulator.get_by_role("button", name="Extensions", exact=True).click()
            simulator.get_by_label("Search extensions", exact=True).fill("Replay Formatter")
            resume()
            wait_check("pass", before, completed=2)
            pause()
            coach.locator(".screen-result").scroll_into_view_if_needed()
            caption("Correct the visible state and the next checkpoint passes.\nProgress is persisted; dependencies unlock the following step.")
            assertions.append("corrected search PASS and dependency progression")
            pace(96)
            before = len(checks)
            simulator.get_by_role("button", name="Explorer", exact=True).click()
            resume()
            wait_check("uncertain", before, completed=2)
            pause()
            coach.locator(".screen-result").scroll_into_view_if_needed()
            caption("Missing evidence is UNCERTAIN, not automatic failure.\nShowing a different view cannot establish whether the required details are open.")
            screenshot("insufficient-evidence")
            assertions.append("unobserved checkpoint UNCERTAIN")
            pace(107)
            coach.get_by_role("button", name="Stop sharing", exact=True).click()
            expect(coach.get_by_text("NOT SHARING", exact=True)).to_be_visible()
            assert coach.evaluate("window.__v3DemoTrack.readyState") == "ended"
            coach.get_by_role("checkbox", name=re.compile("Save relevant redacted decision evidence")).check()
            simulator.bring_to_front()
            simulator.get_by_role("button", name="Extensions", exact=True).click()
            simulator.get_by_label("Search extensions", exact=True).fill("Replay Formatter")
            simulator.get_by_role("button", name=re.compile("Replay Formatter.*View details")).click()
            simulator.get_by_role("button", name="Change UI version", exact=True).click()
            expect(simulator.get_by_text("CodeLab 2.0", exact=True).first).to_be_visible()
            review_target_screenshot("version-2", "uncertain", 2, "confirmed_version_mismatch")
            coach.locator(".screen-result").scroll_into_view_if_needed()
            caption("Sharing is stopped. The app now reviews fresh, actual target screenshots.\nVisible CodeLab 2.0 differs from the approved source: evidence-backed UNCERTAIN.")
            screenshot("version-mismatch")
            assertions.append("visible version mismatch UNCERTAIN")
            pace(119)
            simulator.get_by_role("button", name="Change UI version", exact=True).click()
            review_target_screenshot("version-1-details", "pass", 3)
            simulator.get_by_role("button", name="Install extension", exact=True).click()
            review_target_screenshot("installed-enabled", "pass", 4)
            expect(coach.get_by_text("All digital checkpoints are verified.", exact=True)).to_be_visible()
            caption("Manual screenshot review confirms Installed and Enabled: four of four.\nReplayLab observes visible evidence; the sandbox installation is simulated.")
            screenshot("workflow-complete")
            assertions.append("four of four visible checkpoints verified")
            pace(134)
            expect(coach.get_by_text("NOT SHARING", exact=True)).to_be_visible()
            assert coach.evaluate("window.__v3DemoTrack.readyState") == "ended"
            coach.get_by_role("button", name="Load saved evidence", exact=True).click()
            expect(coach.locator(".trace-history-list > button")).to_have_count(len(checks))
            coach.locator(".trace-history-list > button").first.click()
            coach.locator(".verification-history").scroll_into_view_if_needed()
            screenshot("saved-decision-history")
            coach.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow("shared saved inspector fits tablet1024px")
            screenshot("tablet-evidence-inspector")
            coach.set_viewport_size({"width": 1440, "height": 1000})
            assertions.append("stop ends real track and explicitly saved evidence remains inspectable")
            caption("Stop ends the real capture track. Screenshots are never retained.\nOnly opted-in, relevant redacted decision evidence is saved for inspection.")
            pace(142)
            coach.get_by_role("button", name="ReplayLab dashboard", exact=True).click()
            with coach.expect_response(lambda response: response.url.endswith("/api/projects/demo") and response.request.method == "POST") as physical_response:
                coach.get_by_role("button", name="Explore the sample project", exact=True).click()
            physical = physical_response.value.json()
            owned_projects.append(physical["id"])
            coach.get_by_role("button", name="Approve task", exact=True).click()
            coach.get_by_role("button", name="Start practice", exact=True).click()
            coach.get_by_role("button", name="Load fixture", exact=True).click()
            coach.locator(".fixture-card").filter(has=coach.locator("strong", has_text="First checkpoint")).click()
            coach.get_by_role("button", name="Verify checkpoint", exact=True).click()
            expect(coach.locator(".verification-result .result-heading").get_by_text("PASS", exact=True)).to_be_visible(timeout=15000)
            coach.locator(".verification-result").scroll_into_view_if_needed()
            expect(coach.locator(".verification-inspector")).to_have_count(1)
            caption("Physical mode uses the same workflow and decision-inspection contract.\nThis controlled block checkpoint uses labeled fixture observations, not live SAM.")
            screenshot("physical-shared-inspector")
            assertions.append("physical fixture PASS uses shared evidence inspector")
            pace(153)
            tab("^Evaluation$")
            coach.get_by_role("button", name="Digital screen captures", exact=True).click()
            expect(coach.get_by_text("20 cases", exact=True)).to_be_visible(timeout=15000)
            coach.evaluate("scrollTo(0,0)")
            evaluation_response = request.get("/api/evaluation/digital")
            assert evaluation_response.ok
            evaluation = evaluation_response.json()
            assert evaluation["sample_size"] == 20
            caption(f"Measured evaluation: {evaluation['correct']}/{evaluation['sample_size']} agreement on controlled browser captures.\nSmall, development-team-labeled local OCR set; not broad real-world or Meta accuracy.")
            screenshot("measured-evaluation")
            no_overflow("measured evaluation fits desktop1440px")
            coach.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow("measured evaluation fits tablet1024px")
            screenshot("tablet-evaluation")
            coach.set_viewport_size({"width": 1440, "height": 1000})
            assertions.append("measured 20-case digital evaluation, calibration and latency visible")
            pace(166)
            coach.get_by_role("button", name="Open provider settings", exact=True).click()
            caption("Meta Muse Spark and SAM adapters are implemented and contract-tested.\nLive Meta inference and hackathon eligibility remain unverified; this demo is offline.")
            screenshot("honest-provider-status")
            pace(175)
            coach.get_by_role("button", name="Save preferences", exact=True).click()
            caption("ReplayLab: demonstration → expected states → evidence → verification.\nIts advantage is knowing when to pass, when to correct, and when it cannot decide.")
            pace(180.2)
            assert not errors, "Browser JavaScript error occurred"
            elapsed = time.monotonic() - began
            video = coach.video.path() if args.record else None
            context.close()
            if video:
                assert elapsed < 191, "Recording overran its planned three-minute sequence"
                def stamp(value):
                    milliseconds = int(max(0, value) * 1000)
                    return f"{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02},{milliseconds % 1000:03}"
                lines = []
                for index, item in enumerate(captions):
                    end = min(180, captions[index + 1]["at"] if index + 1 < len(captions) else 180)
                    if end > item["at"]:
                        lines.append(f"{index + 1}\n{stamp(item['at'])} --> {stamp(end)}\n{item['text']}\n")
                (tempdir / "captions.srt").write_text("\n".join(lines), encoding="utf-8")
                shutil.copyfile(tempdir / "captions.srt", OUTPUT / "demo-captions.srt")
                subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", video,
                    "-vf", "scale=1280:888,pad=1280:960:0:0:color=0x0b0e13,subtitles=captions.srt:force_style='FontName=Segoe UI,FontSize=7.2,BorderStyle=3,Outline=1,MarginV=4'",
                    "-t", "180", "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", "-y", str(OUTPUT / "demo.mp4")], check=True, cwd=tempdir, timeout=120)
                metadata = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=width,height,nb_frames", "-of", "json", str(OUTPUT / "demo.mp4")]))
                assert float(metadata["format"]["duration"]) == 180
            else:
                metadata = None
            report = {"browser": browser.version, "recorded": args.record, "elapsed_seconds": round(elapsed, 2), "assertions": assertions, "screen_check_count": len(checks), "verdicts": [value["result"]["status"] for value in checks], "page_errors": len(errors), "video": metadata, "limitations": ["Controlled CodeLab simulation, not a real VS Code extension installation.", "Actual getDisplayMedia tab stream for initial states; Chromium test flag selects the source instead of a human picker.", "After stopping sharing, version and final checkpoints use the app's manual review path with actual fresh browser screenshots. Recording-mode background-tab delivery can become stale; the verifier abstains on stale insufficient views.", "Offline transcript extraction; real local OCR. No live Meta calls.", "Controlled team-authored evaluation cases, not independent human annotation."]}
            (OUTPUT / "demo-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            succeeded = True
            log("completed", assertions=len(assertions), screen_checks=len(checks), recorded=args.record, elapsed_seconds=round(elapsed, 2))
        except Exception as failure:
            debug = ROOT / ".artifacts"
            debug.mkdir(exist_ok=True)
            coach.screenshot(path=str(debug / "v3-demo-failure.png"), full_page=True)
            (debug / "v3-demo-page-errors.json").write_text(json.dumps(errors), encoding="utf-8")
            (debug / "v3-demo-error.txt").write_text(str(failure), encoding="utf-8")
            raise
        finally:
            context.close()
            browser.close()
            # Only this script's controlled projects are removed.
            for identifier in owned_projects:
                response = request.delete(f"/api/projects/{identifier}")
                log("owned-project-cleanup", success=response.status == 204)
            request.dispose()
            if not succeeded:
                log("demo-incomplete", recorded=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - avoid leaking captured content in browser diagnostics
        frames = traceback.extract_tb(error.__traceback__)
        location = next((frame for frame in reversed(frames) if Path(frame.filename).resolve() == Path(__file__).resolve()), frames[-1])
        log("failed", error_type=type(error).__name__, source_line=location.lineno)
        raise SystemExit(1) from None
