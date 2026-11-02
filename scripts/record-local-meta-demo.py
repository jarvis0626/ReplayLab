"""Record real local Meta OCR/text screen verification without editing a pending proposal.

Uses two repository-owned CodeLab screen submissions, with up to four underlying
local model calls. Existing explanation plans may be cached; no model call count
is invented when the API does not expose cache metadata. No network mocking,
accelerated waiting, padding, cloud inference, or automatic proposal approval.
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
OUTPUT = ROOT / "docs" / "assets" / "local-meta"
PIXELS = ROOT / "demo" / "evaluation" / "digital" / "screenshots"
MODEL = "meta-llama/Llama-3.2-3B-Instruct"


def snapshot(project):
    value = {key: project[key] for key in ["task", "approved", "completed_step_ids"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-project", required=True,
                        help="Identifier of an existing unapproved local Meta proposal to review without changing it.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{32}", args.review_project):
        parser.error("Review project must be an existing ReplayLab project identifier.")
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("FFmpeg and FFprobe are required before recording.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    intermediate = ROOT / ".artifacts" / ("local-meta-recording-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    intermediate.mkdir(parents=True, exist_ok=False)
    report = {
        "recorded_at": datetime.now(UTC).isoformat(), "success": False,
        "model": MODEL, "provider_mode": "local_meta", "browser": None,
        "screen_submission_budget": 2, "actual_screen_submissions": 0,
        "underlying_local_model_request_budget": 4, "fresh_observation_response_ids": [],
        "actual_underlying_local_model_request_count": None,
        "model_request_count_limit": "Two fresh observation requests plus up to two explanation requests; existing explanation cache hits are not exposed by the API.",
        "chapters": [], "cases": [], "page_errors": [], "nonlocal_browser_hosts": [],
        "review_project": args.review_project, "review_project_unchanged": False,
        "cleanup": [], "video": None,
        "limitations": [
            "Meta Llama receives redacted OCR text, not image pixels. Deterministic rules own PASS/FAIL/UNCERTAIN.",
            "The existing Meta-generated proposal was generated before recording and remains unapproved and unchanged.",
            "The two screen checks use separate approved CodeLab fixture workflows, not the pending model-generated proposal.",
            "CodeLab simulates software changes. These two controlled screenshots are not a real-world accuracy benchmark.",
            "Manual screenshot upload is exercised, not a human screen picker or live tab stream.",
            "No hosted Meta/NVIDIA success, SAM segmentation, or hackathon eligibility is established by this recording.",
            "Waiting is recorded at actual speed. No padding, time compression, or response substitution is used.",
        ],
    }
    report_path = OUTPUT / "demo-recording.json"
    owned_projects, remote_hosts, review_writes = [], set(), []
    started = None
    context = browser = request = page = video = None

    def save():
        report["nonlocal_browser_hosts"] = sorted(remote_hosts)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")

    def chapter(name):
        elapsed = round(time.perf_counter() - started, 2)
        assert elapsed < 178, "Recording exceeded the planned uncut duration."
        report["chapters"].append({"name": name, "at_seconds": elapsed})
        save()
        print(json.dumps({"chapter": name, "elapsed_seconds": elapsed}), flush=True)

    def navigate(name):
        page.get_by_role("navigation", name="Project workspace").get_by_role("button", name=re.compile("^" + name)).click()

    with sync_playwright() as playwright:
        try:
            request = playwright.request.new_context(base_url="http://127.0.0.1:8010")
            health = request.get("/api/health")
            assert health.ok, "Start the ReplayLab API before recording."
            review = request.get(f"/api/projects/{args.review_project}").json()
            assert review["approved"] is False, "The requested review project must remain unapproved."
            assert review["task"]["provider_mode"] == "local_meta"
            before = snapshot(review)
            report["review_proposal_provenance"] = review["task"]["provenance"]
            report["review_proposal_step_count"] = len(review["task"]["steps"])
            browser = playwright.chromium.launch(headless=True)
            report["browser"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1000},
                record_video_dir=str(intermediate), record_video_size={"width": 1440, "height": 1000})
            page = context.new_page()
            video = page.video
            started = time.perf_counter()
            page.set_default_timeout(20000)
            page.on("pageerror", lambda error: report["page_errors"].append(type(error).__name__))

            def observe_request(outgoing):
                parsed = urlsplit(outgoing.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                    remote_hosts.add(parsed.hostname)
                if args.review_project in parsed.path and outgoing.method not in {"GET", "HEAD"}:
                    review_writes.append({"method": outgoing.method, "path": parsed.path})

            page.on("request", observe_request)
            page.goto("http://127.0.0.1:5173")
            page.get_by_role("button", name="Open provider settings", exact=True).click()
            dialog = page.get_by_role("dialog")
            with page.expect_response(lambda response: response.url.endswith("/api/provider")) as selected:
                dialog.get_by_role("button", name=re.compile(re.escape("Local Meta Llama · OCR + text"))).click()
            assert selected.value.json()["provider"]["mode"] == "local_meta"
            expect(dialog.get_by_text(re.compile(re.escape(MODEL)))).to_be_visible()
            expect(dialog.get_by_text(re.compile("Built with Llama\\."))).to_be_visible()
            expect(dialog.get_by_role("checkbox", name=re.compile("I consent to sending"))).to_have_count(0)
            chapter("Local Meta model, OCR/text disclosure, and Built with Llama attribution")
            page.wait_for_timeout(3000)
            dialog.get_by_role("button", name="Save preferences", exact=True).click()

            target = page.locator(".project-card-main").filter(has=page.get_by_role("heading", name=review["name"], exact=True))
            with page.expect_response(lambda response: response.url.endswith("/api/projects/" + args.review_project)):
                target.click()
            navigate("Task & graph")
            expect(page.get_by_text("LOCAL_META PROPOSAL", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Approve task", exact=True)).to_be_visible()
            expect(page.locator(".react-flow__node")).to_have_count(len(review["task"]["steps"]))
            chapter("Read-only review of the existing Meta-generated graph; approval remains pending")
            page.wait_for_timeout(5000)
            assert snapshot(request.get(f"/api/projects/{args.review_project}").json()) == before

            for case_id, expected in [("correct-market", "pass"), ("wrong-settings-market", "fail")]:
                page.get_by_role("button", name="ReplayLab dashboard", exact=True).click()
                with page.expect_response(lambda response: response.url.endswith("/api/projects/digital-demo")) as created:
                    page.get_by_role("button", name="Try digital demo", exact=True).click()
                project = created.value.json()
                assert created.value.ok and project["id"] != args.review_project
                owned_projects.append(project["id"])
                assert project["task"]["provider_mode"] == "mock", "The demo workflow must stay honestly identified as a fixture."
                expect(page.get_by_text("MOCK PROPOSAL", exact=True)).to_be_visible()
                chapter(case_id + ": approve a separate known CodeLab fixture workflow")
                page.wait_for_timeout(1500)
                with page.expect_response(lambda response: response.url.endswith("/approve")) as approved:
                    page.get_by_role("button", name="Approve task", exact=True).click()
                assert approved.value.ok
                page.get_by_role("button", name="Start practice", exact=True).click()
                expect(page.get_by_role("button", name="Upload screenshot", exact=True)).to_be_enabled()
                assert request.get("/api/health").json()["provider"]["mode"] == "local_meta"
                assert report["actual_screen_submissions"] < 2
                chapter(case_id + ": submit the owned screenshot for real local OCR and Meta text reasoning")
                report["actual_screen_submissions"] += 1
                save()
                request_started = time.perf_counter()
                remaining_ms = max(1000, int((170 - (request_started - started)) * 1000))
                with page.expect_response(lambda response: response.url.endswith("/screen-check"), timeout=remaining_ms) as observed:
                    page.get_by_label("Upload screen screenshot", exact=True).set_input_files(str(PIXELS / f"case-{case_id}.png"))
                response = observed.value
                assert response.ok, "The real local screen request failed."
                body = response.json()
                provenance = body["observation"]["provenance"]
                result = body["result"]
                record = {"id": case_id, "expected": expected, "actual": result["status"],
                    "http_status": response.status, "latency_ms": round((time.perf_counter() - request_started) * 1000, 2),
                    "provider_mode": result["provider_mode"], "observation_provenance": provenance,
                    "explanation_provider": (body.get("verification") or {}).get("provider", {}).get("explanation"),
                    "explanation": result["explanation"], "rule_results": result["rule_results"],
                    "completed_step_ids": body["completed_step_ids"]}
                report["cases"].append(record)
                save()
                assert result["provider_mode"] == "local_meta"
                assert provenance.get("local_only") is True and provenance.get("vision_inference") is False
                assert provenance.get("api_response_validated") is True and provenance.get("live_api_verified") is True
                assert provenance.get("model") == MODEL and provenance.get("request_id")
                report["fresh_observation_response_ids"].append(provenance["request_id"])
                progress = [project["task"]["steps"][0]["id"]] if result["status"] == "pass" else []
                assert body["completed_step_ids"] == progress
                assert request.get(f"/api/projects/{project['id']}").json()["completed_step_ids"] == progress
                region = page.get_by_role("region", name="Screen verification result")
                expect(region).to_be_visible()
                region.scroll_into_view_if_needed()
                chapter(case_id + ": actual " + result["status"].upper() + " and evidence-driven progress")
                page.wait_for_timeout(4000)
                page.get_by_text("Inspect decision and source evidence", exact=True).click()
                page.locator(".verification-inspector").scroll_into_view_if_needed()
                page.wait_for_timeout(3000)
                page.evaluate("scrollTo(0,0)")
                expect(page.get_by_text("Local Meta Llama provider", exact=True)).to_be_visible()
                page.wait_for_timeout(1500)

            after = request.get(f"/api/projects/{args.review_project}").json()
            report["review_project_unchanged"] = snapshot(after) == before and after["approved"] is False and not review_writes
            report["review_project_write_requests"] = review_writes
            assert report["review_project_unchanged"], "The pending proposal changed during review."
            assert not report["page_errors"] and not remote_hosts
            report["success"] = all(case["actual"] == case["expected"] for case in report["cases"])
            chapter("Finished: actual local Meta screen decisions; generated proposal remains unapproved")
            report["uncut_browser_elapsed_seconds"] = round(time.perf_counter() - started, 3)
            context.close()
            context = None
            browser.close()
            browser = None
            source = str(video.path())
            command = [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", source,
                "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
                "-movflags", "+faststart", "-an", "-y", str(OUTPUT / "demo.mp4")]
            with (intermediate / "ffmpeg.log").open("w", encoding="utf-8") as log:
                subprocess.run(command, stdout=log, stderr=log, check=True, timeout=120)
            report["video"] = json.loads(subprocess.check_output([ffprobe, "-v", "error", "-show_entries",
                "format=duration,size:stream=width,height,nb_frames", "-of", "json", str(OUTPUT / "demo.mp4")]))
            assert float(report["video"]["format"]["duration"]) <= 180, "Uncut video exceeds 180 seconds."
            report["fresh_observation_request_count"] = len(report["fresh_observation_response_ids"])
            print(json.dumps({"recorded": True, "success": report["success"],
                "duration_seconds": report["video"]["format"]["duration"], "screen_submissions": report["actual_screen_submissions"],
                "verdicts": [case["actual"] for case in report["cases"]]}), flush=True)
        except Exception as error:
            report["error_type"] = type(error).__name__
            if page is not None and not page.is_closed():
                try:
                    page.screenshot(path=str(intermediate / "failure.png"), full_page=True)
                except PlaywrightError as shot_error:
                    report["failure_screenshot_error"] = type(shot_error).__name__
            raise
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
            if request is not None:
                for identifier in owned_projects:
                    assert identifier != args.review_project
                    response = request.delete(f"/api/projects/{identifier}")
                    report["cleanup"].append({"owned_project": identifier, "http_status": response.status})
                request.dispose()
            save()
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
