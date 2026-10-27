"""Exercise actual Chromium tab capture and local OCR against ReplayLab 2.

No getDisplayMedia replacement, network interception, fixture observations, or
requested verdict is used. Chromium's test selection flag chooses the separate
CodeLab tab after the UI's explicit share gesture. All screenshots contain only
the controlled, clearly labeled CodeLab sandbox and the local coaching app.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import tempfile
import time
import traceback
from email import policy
from email.parser import BytesParser
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "assets" / "v2"
REPORT = ROOT / "docs" / "digital-browser-qa.md"


def log(phase: str, **safe_details):
    print(json.dumps({"phase": phase, **safe_details}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    parser.add_argument("--api-url", default="http://127.0.0.1:8010")
    parser.add_argument("--record", action="store_true")
    parser.add_argument(
        "--probe-version",
        action="store_true",
        help="Save controlled CodeLab version OCR diagnostics, then delete its temporary project",
    )
    args = parser.parse_args()
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    outcomes = []
    page_errors = []
    checks = []
    inflight = set()
    peak_inflight = 0
    project_id = None
    succeeded = False
    video_metadata = None
    phase = "initial"
    started = time.monotonic()

    with (
        sync_playwright() as playwright,
        tempfile.TemporaryDirectory(prefix="replaylab-digital-qa-") as recordings,
    ):
        browser = playwright.chromium.launch(
            headless=True,
            channel="chromium",
            args=[
                "--auto-select-tab-capture-source-by-title=ReplayLab CodeLab",
                "--enable-usermedia-screen-capturing",
                "--allow-http-screen-capture",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows",
            ],
        )
        log("browser-started", channel="chromium", version=browser.version)
        request = playwright.request.new_context(base_url=args.api_url)
        assert request.get("/api/health").ok, "Local API is unavailable"
        assert request.post("/api/provider", data={"mode": "mock"}).ok
        settings = {"viewport": {"width": 1440, "height": 1000}}
        if args.record:
            settings.update(
                record_video_dir=recordings,
                record_video_size={"width": 1440, "height": 1000},
            )
        context = browser.new_context(**settings)
        context.on(
            "page",
            lambda page: page.on(
                "pageerror", lambda error: page_errors.append(str(error))
            ),
        )
        coach = context.new_page()
        simulator = context.new_page()

        def is_screen(url):
            return url.endswith("/screen-check")

        def request_started(req):
            nonlocal peak_inflight
            if is_screen(req.url):
                inflight.add(req)
                peak_inflight = max(peak_inflight, len(inflight))

        coach.on("request", request_started)
        coach.on("requestfinished", lambda req: inflight.discard(req))
        coach.on("requestfailed", lambda req: inflight.discard(req))

        def response_received(response):
            if not is_screen(response.url):
                return
            if not response.ok:
                checks.append({"http_error": response.status})
                log("screen-response", http_status=response.status)
                return
            data = response.json()
            checks.append(data)
            debug = ROOT / ".artifacts"
            debug.mkdir(exist_ok=True)
            (debug / "v2-last-screen-debug.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            if phase == "version":
                debug = ROOT / ".artifacts"
                debug.mkdir(exist_ok=True)
                (debug / "v2-version-debug.json").write_text(
                    json.dumps(data, indent=2), encoding="utf-8"
                )
                body = response.request.post_data_buffer
                content_type = response.request.header_value("content-type")
                if body and content_type:
                    message = BytesParser(policy=policy.default).parsebytes(
                        (
                            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n"
                        ).encode()
                        + body
                    )
                    for part in message.iter_parts():
                        if part.get_filename() == "screen-check.png":
                            (debug / "v2-version-source.png").write_bytes(
                                part.get_payload(decode=True)
                            )
            log(
                "screen-response",
                verdict=data["result"]["status"],
                reason=data["result"].get("reason"),
                provider=data["result"]["provider_mode"],
                completed=len(data["completed_step_ids"]),
                source_scope=data.get("source_scope"),
                version_detected=bool(data["observation"].get("interface_version")),
                version_ambiguous=data["observation"]
                .get("provenance", {})
                .get("interface_version_ambiguous", False),
                visible_version_token=any(
                    re.search(
                        r"CodeLab\s*\d+\.\d+", element.get("text", ""), re.IGNORECASE
                    )
                    for element in data["observation"].get("elements", [])
                ),
            )

        coach.on("response", response_received)

        def pace(target):
            if args.record:
                remaining = target - (time.monotonic() - started)
                while remaining > 0:
                    coach.wait_for_timeout(min(remaining, 5) * 1000)
                    remaining = target - (time.monotonic() - started)

        def screenshot(page, name):
            previous = page.evaluate("scrollY")
            page.evaluate("scrollTo(0,0)")
            page.wait_for_timeout(120)
            page.screenshot(
                path=str(ARTIFACTS / f"{name}.png"),
                full_page=True,
                animations="disabled",
            )
            page.evaluate("position => scrollTo(0,position)", previous)

        def save_shared_debug_frame():
            data_url = coach.get_by_label("Shared screen preview", exact=True).evaluate("""video => {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                return canvas.toDataURL('image/png');
            }""")
            debug = ROOT / ".artifacts"
            debug.mkdir(exist_ok=True)
            (debug / "v2-version-source.png").write_bytes(
                base64.b64decode(data_url.split(",", 1)[1])
            )

        def no_overflow(page, label):
            size = page.evaluate(
                "() => ({viewport:innerWidth,body:document.body.scrollWidth,root:document.documentElement.scrollWidth})"
            )
            assert (
                size["body"] <= size["viewport"] + 1
                and size["root"] <= size["viewport"] + 1
            ), (label, size)
            outcomes.append({"check": label, "result": "pass"})

        def tab(label):
            coach.get_by_role("navigation", name="Project workspace").get_by_role(
                "button", name=re.compile(label)
            ).click()

        def wait_check(status, after, *, reason=None, completed=None, timeout=90000):
            deadline = time.monotonic() + timeout / 1000
            while time.monotonic() < deadline:
                coach.wait_for_timeout(200)
                for data in checks[after:]:
                    if data.get("http_error"):
                        continue
                    result = data["result"]
                    if (
                        result["status"] == status
                        and (reason is None or result.get("reason") == reason)
                        and (
                            completed is None
                            or len(data["completed_step_ids"]) == completed
                        )
                    ):
                        assert result["provider_mode"] == "local_ocr", (
                            "Expected genuine local OCR provenance"
                        )
                        assert data["screen_stored"] is False
                        return data
            safe = [
                {
                    "status": c.get("result", {}).get("status"),
                    "reason": c.get("result", {}).get("reason"),
                    "completed": len(c.get("completed_step_ids", [])),
                    "http": c.get("http_error"),
                }
                for c in checks[after:]
            ]
            if phase == "version":
                save_shared_debug_frame()
            raise AssertionError(
                f"Expected {status}/{reason}/{completed}; received safe summary {safe}"
            )

        def pause():
            button = coach.get_by_role("button", name="Pause", exact=True)
            if button.is_visible():
                button.click()
            expect(coach.get_by_text("SHARING · PAUSED", exact=True)).to_be_visible()

        def resume():
            # Keep the real media element visible and allow delivered frames to
            # advance after a source change. This does not alter capture APIs,
            # observations, or the verifier.
            simulator.bring_to_front()
            simulator.wait_for_timeout(350)
            coach.bring_to_front()
            preview = coach.get_by_label("Shared screen preview", exact=True)
            preview.scroll_into_view_if_needed()
            preview.evaluate("""async video => {
                await new Promise(resolve => {
                    let frames = 0;
                    const done = () => { if (++frames >= 2) resolve(); else video.requestVideoFrameCallback(done); };
                    video.requestVideoFrameCallback(done);
                    setTimeout(resolve, 1500);
                });
            }""")
            coach.get_by_role("button", name="Resume", exact=True).click()
            expect(coach.get_by_text("SHARING", exact=True)).to_be_visible()

        try:
            coach.goto(args.base_url)
            expect(coach.get_by_text("MOCK MODE", exact=True)).to_be_visible()
            no_overflow(coach, "desktop dashboard at 1440px")
            screenshot(coach, "dashboard")
            with coach.expect_response(
                lambda response: (
                    response.url.endswith("/api/projects/digital-demo")
                    and response.request.method == "POST"
                )
            ) as created:
                coach.get_by_role("button", name="Try digital demo", exact=True).click()
            project = created.value.json()
            project_id = project["id"]
            log("digital-demo-created")
            assert (
                project["modality"] == "digital" and len(project["task"]["steps"]) == 4
            )
            expect(coach.locator(".react-flow__node")).to_have_count(4)
            no_overflow(coach, "desktop digital graph at 1440px")
            screenshot(coach, "digital-task-graph")
            tab("^Demonstration$")
            video = coach.get_by_label("Demonstration video", exact=True)
            expect(video).to_be_visible()
            coach.wait_for_function("document.querySelector('video')?.readyState >= 1")
            media = video.evaluate(
                "video => ({duration:video.duration,width:video.videoWidth,height:video.videoHeight})"
            )
            assert media["duration"] > 0 and media["width"] > 0
            video.evaluate("video => video.play()")
            coach.wait_for_timeout(1000)
            assert video.evaluate("video => video.currentTime") > 0.3
            video.evaluate("video => video.pause()")
            expect(coach.locator(".keyframe")).to_have_count(4)
            no_overflow(coach, "desktop tutorial studio at 1440px")
            screenshot(coach, "digital-tutorial-studio")
            outcomes.append(
                {
                    "check": "generated digital tutorial MP4 loads, plays, and shows four synthetic source references",
                    "result": "pass",
                }
            )
            tab("^Task & graph")
            description = coach.locator(".step-editor textarea").first
            description.fill(
                description.input_value() + " Reviewed in real browser QA."
            )
            coach.get_by_role("button", name="Save changes", exact=True).click()
            expect(
                coach.get_by_role("button", name="Approve task", exact=True)
            ).to_be_enabled()
            coach.get_by_role("button", name="Approve task", exact=True).click()
            expect(
                coach.get_by_role("button", name="Start practice", exact=True)
            ).to_be_visible()
            outcomes.append(
                {
                    "check": "digital graph, task edit, save, and explicit approval",
                    "result": "pass",
                }
            )
            coach.get_by_role("button", name="Start practice", exact=True).click()
            log("workflow-approved")
            simulator.goto(args.base_url + "?digital-demo=1")
            expect(simulator).to_have_title("ReplayLab CodeLab")
            expect(
                simulator.get_by_text(
                    "Interactive simulation · no actual software changes", exact=True
                )
            ).to_be_visible()
            simulator.get_by_role("button", name="Extensions", exact=True).click()
            if args.probe_version:
                phase = "version"
                simulator.get_by_role(
                    "button", name="Change UI version", exact=True
                ).click()
            screenshot(simulator, "codelab-simulator")
            no_overflow(simulator, "desktop CodeLab simulator at 1440px")
            coach.bring_to_front()
            pace(8)
            before = len(checks)
            coach.get_by_role(
                "button", name="Choose screen or window", exact=True
            ).click()
            log("share-requested")
            expect(
                coach.get_by_text("Visible capture scope: browser tab", exact=True)
            ).to_be_visible(timeout=30000)
            simulator.bring_to_front()
            simulator.wait_for_timeout(500)
            coach.bring_to_front()
            coach.get_by_label("Shared screen preview", exact=True).scroll_into_view_if_needed()
            try:
                coach.wait_for_function("document.querySelector('video[aria-label=\"Shared screen preview\"]')?.videoWidth > 0", timeout=20000)
            except PlaywrightTimeoutError:
                debug = ROOT / ".artifacts"
                debug.mkdir(exist_ok=True)
                metadata = coach.get_by_label("Shared screen preview", exact=True).evaluate("video => ({width:video.videoWidth,height:video.videoHeight,readyState:video.readyState,paused:video.paused,hasStream:!!video.srcObject,tracks:video.srcObject?.getTracks().map(track=>({kind:track.kind,state:track.readyState,enabled:track.enabled,muted:track.muted}))})")
                (debug / "v2-initial-stream-debug.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                coach.screenshot(path=str(debug / "v2-initial-stream.png"), full_page=True)
                log("capture-initialization-failed", **metadata)
                raise
            log("initial-frame-ready")
            if args.probe_version:
                deadline = time.monotonic() + 90
                while len(checks) == before and time.monotonic() < deadline:
                    coach.wait_for_timeout(200)
                assert len(checks) > before, "No controlled version capture response"
                save_shared_debug_frame()
                log("version-probe-complete", diagnostic_saved=True)
                return
            first = wait_check("pass", before, completed=1)
            assert first.get("source_scope") == "browser tab"
            settings = coach.get_by_label("Shared screen preview", exact=True).evaluate(
                "video => {window.__qaTrack=video.srcObject.getVideoTracks()[0]; return {surface:window.__qaTrack.getSettings().displaySurface,state:window.__qaTrack.readyState,width:video.videoWidth,height:video.videoHeight}}"
            )
            assert (
                settings["surface"] == "browser"
                and settings["state"] == "live"
                and settings["width"] > 0
            )
            outcomes.append(
                {
                    "check": "real getDisplayMedia separate-tab capture -> local OCR -> first-step PASS",
                    "result": "pass",
                }
            )
            pause()
            no_overflow(coach, "desktop live screen coach at 1440px")
            screenshot(coach, "screen-sharing-pass")
            log(
                "capture-confirmed",
                scope=settings["surface"],
                track_state=settings["state"],
                width=settings["width"],
                height=settings["height"],
            )

            # Paused capture cannot send further periodic screen requests.
            paused_count = len(checks)
            coach.wait_for_timeout(4500)
            assert len(checks) == paused_count
            outcomes.append(
                {"check": "pause prevents new periodic screen checks", "result": "pass"}
            )
            before = len(checks)
            simulator.get_by_role("button", name="Settings", exact=True).click()
            resume()
            wait_check("fail", before, completed=1)
            pause()
            screenshot(coach, "wrong-destination-fail")
            outcomes.append(
                {"check": "visible wrong destination -> FAIL", "result": "fail"}
            )
            coach.get_by_label("Ask about the current workflow", exact=True).fill(
                "How should I recover?"
            )
            with coach.expect_response(
                lambda response: response.url.endswith("/ask")
            ) as asked:
                coach.get_by_role("button", name="Send question", exact=True).click()
            assert (
                asked.value.ok
                and asked.value.json()["provider_mode"] == "grounded_template"
            )
            expect(coach.locator(".screen-answer")).to_be_visible()
            outcomes.append(
                {
                    "check": "Ask returns grounded template with explicit provenance",
                    "result": "pass",
                }
            )
            pace(26)

            before = len(checks)
            simulator.get_by_role("button", name="Extensions", exact=True).click()
            simulator.get_by_label("Search extensions", exact=True).fill(
                "Replay Formatter"
            )
            resume()
            wait_check("pass", before, completed=2)
            pause()
            outcomes.append(
                {
                    "check": "correct visible search -> second-step PASS",
                    "result": "pass",
                }
            )
            pace(38)
            before = len(checks)
            simulator.get_by_role(
                "button", name=re.compile("Replay Formatter.*View details")
            ).click()
            resume()
            wait_check("pass", before, completed=3)
            pause()
            outcomes.append(
                {
                    "check": "visible extension details -> third-step PASS",
                    "result": "pass",
                }
            )

            before = len(checks)
            simulator.get_by_role(
                "button", name="Show unexpected dialog", exact=True
            ).click()
            resume()
            dialog_result = wait_check("fail", before, completed=3)
            assert dialog_result["result"]["reason"] in {
                "unexpected_dialog",
                "mismatch",
            }
            pause()
            screenshot(coach, "unexpected-dialog-fail")
            outcomes.append(
                {"check": "visible Permission denied dialog -> FAIL", "result": "fail"}
            )
            pace(54)

            before = len(checks)
            phase = "version"
            simulator.get_by_role("button", name="Dismiss dialog", exact=True).click()
            simulator.get_by_role(
                "button", name="Change UI version", exact=True
            ).click()
            resume()
            wait_check("uncertain", before, reason="interface_mismatch", completed=3)
            save_shared_debug_frame()
            pause()
            phase = "final"
            screenshot(coach, "interface-version-uncertain")
            outcomes.append(
                {
                    "check": "visible CodeLab 2.0 -> interface-mismatch UNCERTAIN",
                    "result": "uncertain",
                }
            )
            pace(67)

            before = len(checks)
            simulator.get_by_role(
                "button", name="Change UI version", exact=True
            ).click()
            simulator.get_by_role(
                "button", name="Install extension", exact=True
            ).click()
            expect(simulator.get_by_text("Installed", exact=True)).to_be_visible()
            expect(simulator.get_by_text("Enabled", exact=True)).to_be_visible()
            screenshot(simulator, "codelab-complete")
            resume()
            final = wait_check("pass", before, completed=4)
            pause()
            assert len(final["completed_step_ids"]) == 4
            expect(
                coach.get_by_text("All digital checkpoints are verified.", exact=True)
            ).to_be_visible()
            screenshot(coach, "digital-workflow-complete")
            outcomes.append(
                {
                    "check": "visible Installed and Enabled -> final PASS and 4/4 completion",
                    "result": "pass",
                }
            )
            coach.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow(coach, "tablet live screen coach at 1024px")
            screenshot(coach, "tablet-screen-coach")
            coach.set_viewport_size({"width": 1440, "height": 1000})
            pace(80)
            coach.get_by_role("button", name="Stop sharing", exact=True).click()
            expect(coach.get_by_text("NOT SHARING", exact=True)).to_be_visible()
            assert coach.evaluate("window.__qaTrack.readyState") == "ended"
            assert coach.get_by_label("Shared screen preview", exact=True).evaluate(
                "video => video.srcObject === null"
            )
            expect(coach.locator(".screen-answer")).to_have_count(0)
            stopped_count = len(checks)
            coach.wait_for_timeout(4500)
            assert len(checks) == stopped_count
            outcomes.append(
                {
                    "check": "stop ends actual track, clears Ask and session, and prevents further capture",
                    "result": "pass",
                }
            )
            assert peak_inflight <= 1, "Overlapping screenshot requests were observed"
            assert not page_errors, "JavaScript page errors were observed"
            outcomes.append(
                {
                    "check": "no overlapping screen checks or JavaScript page errors",
                    "result": "pass",
                }
            )
            pace(90)
            video_path = coach.video.path() if args.record else None
            context.close()

            if video_path:
                ffmpeg = shutil.which("ffmpeg")
                assert ffmpeg, "Optional MP4 export needs FFmpeg"
                destination = ARTIFACTS / "digital-demo.mp4"
                subprocess.run(
                    [
                        ffmpeg,
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        video_path,
                        "-vf",
                        "scale=1280:-2",
                        "-r",
                        "25",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "27",
                        "-pix_fmt",
                        "yuv420p",
                        "-movflags",
                        "+faststart",
                        "-an",
                        "-y",
                        str(destination),
                    ],
                    check=True,
                    timeout=180,
                )
                video_metadata = json.loads(
                    subprocess.check_output(
                        [
                            "ffprobe",
                            "-v",
                            "error",
                            "-show_entries",
                            "format=duration,size",
                            "-of",
                            "json",
                            str(destination),
                        ]
                    )
                )["format"]
                log("recording-exported", **video_metadata)

            rows = "\n".join(
                f"| {item['check']} | {item['result'].upper()} |" for item in outcomes
            )
            report = f"""# ReplayLab 2 actual digital browser QA

This run used real headless Chromium {browser.version}, the running local Vite/FastAPI application, and actual local OCR. No getDisplayMedia stub, network response interception, fixture observation lookup, or requested outcome was used. The shared source was a separate, explicitly labeled CodeLab simulator tab; its software installation is simulated. This does not establish arbitrary workflow support or live Meta inference.

The browser's explicit share button started an actual `getDisplayMedia` call. Chromium's test-only `--auto-select-tab-capture-source-by-title=ReplayLab CodeLab` flag selected that tab in place of a human picker. Track settings reported `displaySurface:browser` and `readyState:live`; stopping changed the same track to `ended`. This validates a real browser tab stream under test selection, not a manually exercised operating-system permission picker. The script uses `channel="chromium"` for the full new headless browser; the default headless shell denied capture in this environment. See the primary [Playwright browser guidance](https://playwright.dev/python/docs/browsers#chromium-new-headless-mode) and [Chromium test-selection flag source](https://chromium.googlesource.com/chromium/src/+/refs/tags/147.0.7727.118/chrome/common/chrome_switches.cc).

| Browser interaction | Actual result |
| --- | --- |
{rows}

**{len(outcomes)} assertion groups passed.** Successful screen-check responses: **{sum("result" in item for item in checks)}**. Peak concurrent screenshot requests: **{peak_inflight}**. JavaScript page errors: **{len(page_errors)}**. Screenshots were not retained by the API. Desktop and tablet page widths were checked at 1440 x 1000 and 1024 x 1000; these are tested sizes, not exhaustive device coverage.

All images in [assets/v2](assets/v2) are captures of the actual running application and synthetic CodeLab interface. They are not stock images or fabricated inference screenshots. Files include dashboard, digital-task-graph, codelab-simulator, screen-sharing-pass, wrong-destination-fail, unexpected-dialog-fail, interface-version-uncertain, digital-workflow-complete, and tablet-screen-coach.

{"The optional [silent browser recording](assets/v2/digital-demo.mp4) contains the complete actual browser interaction at normal speed; it has no narration, no public hosting, and no live Meta calls. FFprobe metadata: " + json.dumps(video_metadata) + "." if video_metadata else "No recording was requested for this run."}

Run against the intended local test workspace using `python scripts/digital-browser-smoke.py` after starting the application. System Python needs Playwright and its Chromium browser; optional recording export needs FFmpeg and FFprobe. The script explicitly selects mock workflow reasoning and uses real local OCR for screen pixels. It retains one completed showcase project after success and deletes only its own failed project after failure. Runtime project data is not committed.

Manual permission-picker interaction, physical screen-sharing hardware/browser variants, live Meta screenshot inference, and real third-party extension installation remain unverified. The physical-task browser regression is reported separately in [browser-qa.md](browser-qa.md).

Elapsed run time: {time.monotonic() - started:.1f} seconds. Showcase project ID: `{project_id}` (local runtime data only).
"""
            REPORT.write_text(report, encoding="utf-8")
            succeeded = True
            log(
                "result",
                checks=len(outcomes),
                screen_checks=len(checks),
                peak_inflight=peak_inflight,
                page_errors=len(page_errors),
                showcase_project_id=project_id,
            )
        finally:
            if project_id and not succeeded:
                response = request.delete(f"/api/projects/{project_id}")
                log("failed-project-cleanup", status=response.status)
            context.close()
            request.dispose()
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 - sanitize browser diagnostics that can contain screen content
        # Playwright assertion messages can contain a full accessibility tree.
        # Log a code location and error type, never screen content.
        frames = traceback.extract_tb(error.__traceback__)
        location = next(
            (
                frame
                for frame in reversed(frames)
                if Path(frame.filename).resolve() == Path(__file__).resolve()
            ),
            frames[-1],
        )
        log("qa-failed", error_type=type(error).__name__, source_line=location.lineno)
        raise SystemExit(1) from None
