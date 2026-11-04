"""Record the actual tutorial upload -> live Meta extraction -> guided proof.

The recording begins directly inside an empty tutorial project. All source,
model output, visible review, browser sharing and verdicts are actual application
behavior. Candidates and raw reports stay ignored until separately reviewed.
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
TRANSCRIPT = ('00:00 - 00:08 Open "Extensions Marketplace" in CodeLab. '
              'Confirm the visible heading "Extensions Marketplace". '
              'This tutorial contains one checkpoint.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tutorial-video", required=True, type=Path)
    parser.add_argument("--name", default="Hackathon live demonstration - tutorial proof")
    parser.add_argument("--model", default=MODEL, choices=[MODEL, "meta-llama/Llama-3.2-1B-Instruct"])
    parser.add_argument("--max-duration", type=float, default=179)
    parser.add_argument("--checks", choices=["pass"], default="pass",
                        help="This focused take proves actual tutorial-following completion with one real screen check.")
    args = parser.parse_args()
    args.name += " " + datetime.now(UTC).strftime("%H%M%S%f")
    expected_model = args.model
    source = args.tutorial_video.resolve()
    if not source.is_relative_to(ROOT) or not source.is_file():
        parser.error("Use a real recorded tutorial inside this repository.")
    if not 30 <= args.max_duration <= 179:
        parser.error("The uncut take must remain below 180 seconds.")
    from playwright.sync_api import expect, sync_playwright

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        parser.error("The installed FFmpeg and FFprobe tools are required.")
    work = ROOT / ".artifacts" / ("tutorial-proof-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    work.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), work / "executed-recorder.py")
    report_path = work / "validation.json"
    report = {"success": False, "created_at": datetime.now(UTC).isoformat(),
              "model": expected_model, "source_file": str(source.relative_to(ROOT)),
              "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "transcript": TRANSCRIPT, "chapters": [], "cases": [],
              "screen_submissions": 0, "nonlocal_browser_hosts": [], "page_errors": [],
              "limitations": ["CodeLab is a labeled interactive simulation; no extension is installed.",
                              "Meta Llama reasons over actual OCR text and a supplied transcript, not image pixels.",
                              "The engineering agent reviews source-supported constraints through the visible UI.",
                              "Chromium selects a real tab stream with its test source selector; no human OS picker is claimed.",
                              "This is a small controlled demonstration, not a representative accuracy benchmark."]}
    began = None
    coach = context = target_context = browser = request = None
    hosts, submissions = set(), []

    def save():
        report["nonlocal_browser_hosts"] = sorted(hosts)
        report["screen_submissions"] = len(submissions)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def elapsed():
        return time.perf_counter() - began

    def chapter(name):
        assert elapsed() < args.max_duration, "Natural workflow exceeded the three-minute budget; no final is published."
        assert not re.search(r"nvapi-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{24,}", coach.locator("body").inner_text())
        report["chapters"].append({"name": name, "at_seconds": round(elapsed(), 3)})
        save()
        print(json.dumps({"chapter": name, "at_seconds": round(elapsed(), 3)}), flush=True)

    def wait_project_ready(project_id, *, expect_task=False):
        while elapsed() < args.max_duration - 5:
            value = request.get(f"/api/projects/{project_id}").json()
            if value["status"] == "error":
                raise AssertionError(value.get("error") or "Actual processing failed.")
            if value["status"] != "processing" and (not expect_task or value.get("task")):
                return value
            coach.wait_for_timeout(350)
        raise AssertionError("Actual processing did not fit the recording budget.")

    with sync_playwright() as p:
        try:
            request = p.request.new_context(base_url="http://127.0.0.1:8010", timeout=20000)
            health = request.get("/api/health")
            assert health.ok and health.json()["provider"]["mode"] == "local_meta"
            assert health.json()["provider"]["model"] == expected_model
            created = request.post("/api/projects", data={"name": args.name, "modality": "digital"})
            assert created.ok
            project_id = created.json()["id"]
            report["project_id"] = project_id
            assert created.json()["task"] is None and created.json()["video"] is None
            browser = p.chromium.launch(headless=True, channel="chromium", args=[
                "--auto-select-tab-capture-source-by-title=ReplayLab CodeLab",
                "--enable-usermedia-screen-capturing", "--allow-http-screen-capture",
                "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows"])
            target_context = browser.new_context(viewport={"width": 1440, "height": 900})
            target = target_context.new_page()
            target.goto("http://127.0.0.1:5173/?digital-demo=1")
            expect(target).to_have_title("ReplayLab CodeLab")
            target.get_by_role("button", name="Settings", exact=True).click()
            context = browser.new_context(viewport={"width": 1920, "height": 1080},
                record_video_dir=str(work / "native"), record_video_size={"width": 1920, "height": 1080})
            coach = context.new_page()
            native = coach.video
            began = time.perf_counter()
            coach.set_default_timeout(20000)
            coach.on("pageerror", lambda error: report["page_errors"].append(type(error).__name__))

            def outgoing(value):
                url = urlsplit(value.url)
                if url.scheme in {"http", "https"} and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
                    hosts.add(url.hostname)
                if url.path.endswith("/screen-check"):
                    submissions.append(round(elapsed(), 3))

            coach.on("request", outgoing)
            coach.goto("http://127.0.0.1:5173")
            coach.locator(".project-card-main").filter(has=coach.get_by_role("heading", name=args.name, exact=True)).click()
            chapter("Upload a real tutorial to the empty project")
            coach.get_by_role("checkbox", name="I have permission to upload and use this tutorial video.", exact=True).check()
            with coach.expect_response(lambda response: response.url.endswith(f"/api/projects/{project_id}/video")) as uploaded:
                coach.get_by_label("Upload demonstration video", exact=True).set_input_files(str(source))
            assert uploaded.value.ok
            project = wait_project_ready(project_id)
            report["source_frame_count"] = len(project["frames"])
            assert project["video"] and project["frames"]
            tutorial = coach.get_by_label("Demonstration video", exact=True)
            expect(tutorial).to_be_visible()
            tutorial.scroll_into_view_if_needed()
            tutorial.evaluate("async video => {video.muted=true; await video.play()}")
            chapter("Play the actual tutorial showing the Marketplace action")
            coach.wait_for_timeout(5000)
            tutorial.evaluate("video => video.pause()")
            coach.get_by_label("Tutorial title (optional)", exact=True).fill("Open Extensions Marketplace - recorded tutorial")
            coach.get_by_label("Timestamped transcript", exact=True).fill(TRANSCRIPT)
            coach.get_by_role("checkbox", name="I have permission to use this tutorial/transcript and have reviewed its usage rights.", exact=True).check()
            with coach.expect_response(lambda response: response.url.endswith("/tutorial")) as saved:
                coach.get_by_role("button", name="Save tutorial source", exact=True).click()
            assert saved.value.ok
            coach.locator(".tutorial-segments").scroll_into_view_if_needed()
            coach.wait_for_timeout(1000)
            generate = coach.get_by_role("button", name="Generate task steps", exact=True)
            generate.scroll_into_view_if_needed()
            tick = time.perf_counter()
            with coach.expect_response(lambda response: response.url.endswith("/extract")) as extraction:
                generate.click()
            assert extraction.value.ok
            chapter("Generate task steps now - actual local Meta request")
            project = wait_project_ready(project_id, expect_task=True)
            report["extraction_seconds"] = round(time.perf_counter() - tick, 3)
            proposal = project["task"]
            report["original_model_proposal"] = proposal
            assert proposal["provider_mode"] == "local_meta"
            assert proposal["provenance"]["model"] == expected_model and proposal["provenance"]["request_id"]
            assert proposal["provenance"]["source_frame_count"] > 0
            assert not project["approved"]
            coach.get_by_role("button", name="Review task & graph", exact=True).click()
            expect(coach.get_by_text("LOCAL_META PROPOSAL", exact=True)).to_be_visible()
            expect(coach.locator(".react-flow__node")).to_have_count(len(proposal["steps"]))
            chapter("The model-generated workflow appears from this uploaded tutorial")
            coach.wait_for_timeout(1200)
            # Review is visible, not a hidden replacement of the model output.
            # Keep the actual model-proposed heading, without inventing or
            # replacing its expected state. Opposing labels need separate review.
            keep = next((step for step in proposal["steps"] if any(
                rule["expected"].casefold() == "extensions marketplace"
                for rule in step["screen_rules"])), None)
            assert keep is not None, "The actual model did not propose the tutorial's quoted checkpoint. No replacement is injected."
            if len(proposal["steps"]) > 1:
                coach.get_by_role("button", name="List view", exact=True).click()
                keep_index = proposal["steps"].index(keep)
                for index in range(len(proposal["steps"]) - 1, -1, -1):
                    if index == keep_index:
                        continue
                    coach.locator(".step-list-item").nth(index).click()
                    coach.get_by_role("button", name="Remove selected step", exact=True).click()
                coach.locator(".step-list-item").first.click()
            keep_rule = next(index for index, rule in enumerate(keep["screen_rules"])
                             if rule["expected"].casefold() == "extensions marketplace")
            for index in range(len(keep["screen_rules"]) - 1, -1, -1):
                if index != keep_rule:
                    coach.get_by_role("button", name=f"Remove screen rule {index + 1}", exact=True).click()
            assert coach.get_by_label("Expected visible text/state", exact=True).input_value().casefold() == "extensions marketplace"
            assert coach.locator(".digital-rule-editor select").input_value() == "text_present"
            coach.get_by_label("Accepted alternatives (comma separated)", exact=True).fill("")
            coach.get_by_label("Visible contradictions (comma separated)", exact=True).fill("")
            save_button = coach.get_by_role("button", name="Save changes", exact=True)
            if save_button.is_enabled():
                with coach.expect_response(lambda response: response.url.endswith("/task") and response.request.method == "PUT") as reviewed:
                    save_button.click()
                assert reviewed.value.ok
                project = reviewed.value.json()
                report["review_saved_changes"] = True
            else:
                project = request.get(f"/api/projects/{project_id}").json()
                report["review_saved_changes"] = False
            report["reviewed_task"] = project["task"]
            report["review_changes"] = "Visible UI review retained the model's actual source-quoted positive heading, title and expected state; only incidental steps/rules and unreviewed alternatives/opposition were removed. No replacement expected state was injected."
            if coach.get_by_role("button", name="Graph view", exact=True).is_visible():
                coach.get_by_role("button", name="Graph view", exact=True).click()
            expect(coach.locator(".react-flow__node")).to_have_count(1)
            chapter("Review the model's source-quoted positive heading before approval")
            with coach.expect_response(lambda response: response.url.endswith("/approve")) as approved:
                coach.get_by_role("button", name="Approve task", exact=True).click()
            assert approved.value.ok
            coach.get_by_role("button", name="Start practice", exact=True).click()
            step_id = project["task"]["steps"][0]["id"]

            def check(case_id, expected, first=False):
                chapter(case_id + ": inspect the actual shared target")
                before = len(submissions)
                tick = time.perf_counter()
                timeout = max(1000, int((args.max_duration - elapsed() - 3) * 1000))
                with coach.expect_response(lambda response: response.url.endswith("/screen-check"), timeout=timeout) as response:
                    if first:
                        coach.get_by_role("button", name="Choose screen or window", exact=True).click()
                        expect(coach.get_by_text("Visible capture scope: browser tab", exact=True)).to_be_visible()
                        coach.wait_for_function("document.querySelector('video[aria-label=\"Shared screen preview\"]')?.videoWidth > 0")
                        coach.get_by_role("button", name="Recheck", exact=True).click()
                    else:
                        target.get_by_role("button", name="Extensions", exact=True).click()
                        target.bring_to_front()
                        target.wait_for_timeout(650)
                        coach.bring_to_front()
                        coach.get_by_label("Shared screen preview", exact=True).evaluate("""async video => {
                            await new Promise(resolve=>{let count=0;const next=()=>{if(++count>=2)resolve();else video.requestVideoFrameCallback(next)};
                            video.requestVideoFrameCallback(next);setTimeout(resolve,1500)})}""")
                        coach.get_by_role("button", name="Resume", exact=True).click()
                        coach.get_by_role("button", name="Recheck", exact=True).click()
                assert response.value.ok
                coach.get_by_role("button", name="Pause", exact=True).click()
                value = response.value.json()
                result, provenance = value["result"], value["observation"]["provenance"]
                report["cases"].append({"id": case_id, "actual": result["status"], "expected": expected,
                    "latency_ms": round((time.perf_counter() - tick) * 1000, 2), "response": value})
                save()
                assert len(submissions) == before + 1
                assert result["status"] == expected and result["provider_mode"] == "local_meta"
                assert value["source_scope"] == "browser tab"
                assert provenance.get("model") == expected_model and provenance.get("request_id")
                assert provenance.get("api_response_validated") and provenance.get("live_api_verified")
                assert provenance.get("local_only") and provenance.get("vision_inference") is False
                assert value["completed_step_ids"] == ([step_id] if expected == "pass" else [])
                if expected == "fail":
                    assert any(rule["status"] == "fail" and rule.get("evidence") and rule.get("correction") for rule in result["rule_results"])
                region = coach.get_by_role("region", name="Screen verification result")
                region.scroll_into_view_if_needed()
                chapter(case_id + ": actual " + expected.upper() + " with observed evidence")
                coach.wait_for_timeout(2300)
                coach.get_by_text("Inspect decision and source evidence", exact=True).click()
                coach.locator(".verification-inspector").scroll_into_view_if_needed()
                coach.wait_for_timeout(1500)
                coach.screenshot(path=str(work / (case_id + ".png")), full_page=True)
                coach.get_by_label("Shared screen preview", exact=True).scroll_into_view_if_needed()

            report["selected_checks"] = "pass"
            report["remaining_seconds_before_sharing"] = round(args.max_duration - elapsed(), 3)
            target.get_by_role("button", name="Extensions", exact=True).click()
            check("tutorial-followed", "pass", first=True)
            report["stream"] = coach.get_by_label("Shared screen preview", exact=True).evaluate(
                "video=>{window.__tutorialTrack=video.srcObject.getVideoTracks()[0];return {settings:window.__tutorialTrack.getSettings(),state:window.__tutorialTrack.readyState}}")
            assert coach.get_by_text("All digital checkpoints are verified.", exact=True).is_visible()
            coach.get_by_role("button", name="Stop sharing", exact=True).click()
            assert coach.evaluate("window.__tutorialTrack.readyState") == "ended"
            coach.get_by_role("navigation", name="Project workspace").get_by_role("button", name=re.compile("^Task & graph")).click()
            expect(coach.locator(".react-flow__node.completed")).to_have_count(1)
            chapter("The uploaded tutorial checkpoint is now verified complete")
            coach.wait_for_timeout(3000)
            report["elapsed_seconds"] = round(elapsed(), 3)
            assert report["elapsed_seconds"] < args.max_duration
            assert not hosts and not report["page_errors"] and len(submissions) == 1
            context.close()
            context = None
            candidate = work / "tutorial-proof.mp4"
            subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-i", str(native.path()),
                "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                "-movflags", "+faststart", "-an", str(candidate)], check=True, timeout=180)
            report["video"] = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-show_entries",
                "format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_frames", "-of", "json", str(candidate)]))
            assert float(report["video"]["format"]["duration"]) <= 180
            subprocess.run([ffmpeg, "-v", "error", "-i", str(candidate), "-f", "null", "-"],
                check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            report["output"] = str(candidate.relative_to(ROOT))
            report["output_sha256"] = hashlib.sha256(candidate.read_bytes()).hexdigest()
            report["success"] = True
            save()
            print(json.dumps({"success": True, "candidate": str(candidate), "report": str(report_path),
                              "duration": report["video"]["format"]["duration"]}), flush=True)
        except BaseException as error:
            report["success"] = False
            report["error_type"] = type(error).__name__
            report["error_message"] = str(error)[:500]
            if coach is not None and not coach.is_closed():
                coach.screenshot(path=str(work / "failure.png"), full_page=True)
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
