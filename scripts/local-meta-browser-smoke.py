"""Exercise actual local Meta OCR/text inference through ReplayLab's browser UI.

No response mocking, cloud inference, requested verdicts, or synthetic model
observations are used. The task template and uploaded pixels are explicitly the
repository-owned CodeLab simulation. Default: one screen submission. The optional
wrong-panel check adds one, on a separate fresh project with the same first step.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "local-meta"
SCREENSHOTS = ROOT / "demo" / "evaluation" / "digital" / "screenshots"
MODEL = "meta-llama/Llama-3.2-3B-Instruct"


def inspect_cloud_consent(outgoing):
    """Inspect an exposed multipart field without assuming CDP includes file data."""
    payload = outgoing.post_data_buffer
    if not payload:
        return {"cloud_consent_sent": None, "cloud_consent_inspection": "Browser did not expose the multipart body."}
    content_type = outgoing.headers.get("content-type", "")
    header = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("ascii")
    message = BytesParser(policy=policy.default).parsebytes(header + payload)
    for part in message.walk():
        if part.get_param("name", header="content-disposition") != "cloud_consent":
            continue
        raw = part.get_payload(decode=True)
        if raw is None:
            continue
        value = raw.decode("ascii", errors="replace").strip()
        if value in {"true", "false"}:
            return {"cloud_consent_sent": value == "true", "cloud_consent_inspection": "Parsed the browser-exposed multipart text field."}
        return {"cloud_consent_sent": None, "cloud_consent_inspection": "Browser exposed an unrecognized cloud consent field."}
    return {"cloud_consent_sent": None, "cloud_consent_inspection": "Multipart field unavailable in the browser-exposed request body; not verified by this browser check."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-wrong-panel", action="store_true",
                        help="Submit one additional owned Settings screenshot on a fresh approved project.")
    parser.add_argument("--ui-only", action="store_true",
                        help="Inspect provider UI only; send no screenshot or model request.")
    args = parser.parse_args()
    if args.ui_only and args.include_wrong_panel:
        parser.error("--ui-only cannot be combined with --include-wrong-panel.")
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report_path = OUTPUT / ("browser-ui-validation.json" if args.ui_only else "browser-validation.json")
    report = {
        "checked_at": datetime.now(UTC).isoformat(), "success": False,
        "provider_mode": "local_meta", "expected_model": MODEL,
        "ui_only": args.ui_only, "browser": None, "phase": "initial",
        "screen_submission_budget": 0 if args.ui_only else 2 if args.include_wrong_panel else 1,
        "actual_screen_submissions": 0, "cases": [], "checks": [],
        "page_errors": [], "nonlocal_browser_hosts": [], "cleanup": [],
        "limitations": [
            "Meta Llama reasons over actual local OCR text; image pixels are not Llama model input.",
            "The approved workflow and test screenshots are the explicitly simulated CodeLab demo.",
            "This small browser check does not establish model accuracy, general application support, or hackathon eligibility.",
            "Manual screenshot upload is exercised; a human screen picker and live tab stream are not tested here.",
            "No tutorial extraction is measured by this approved-template workflow.",
        ],
    }
    owned_projects = []
    nonlocal_hosts = set()
    page = None
    browser = None
    context = None
    request = None

    def save():
        report["nonlocal_browser_hosts"] = sorted(nonlocal_hosts)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")

    def phase(name):
        report["phase"] = name
        save()
        print(json.dumps({"phase": name, "actual_screen_submissions": report["actual_screen_submissions"]}), flush=True)

    def shot(name):
        page.screenshot(path=str(OUTPUT / f"{name}.png"), full_page=True)

    def no_overflow(label):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), label
        report["checks"].append(label)

    with sync_playwright() as playwright:
        try:
            phase("connect")
            request = playwright.request.new_context(base_url="http://127.0.0.1:8010")
            health_response = request.get("/api/health")
            assert health_response.ok, "ReplayLab API is unavailable. Start it before running this check."
            assert health_response.json()["status"] == "ok"
            browser = playwright.chromium.launch(headless=True)
            report["browser"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.set_default_timeout(20000)
            page.on("pageerror", lambda error: report["page_errors"].append(type(error).__name__))

            def inspect_destination(outgoing):
                parsed = urlsplit(outgoing.url)
                if parsed.scheme in {"http", "https"} and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                    nonlocal_hosts.add(parsed.hostname)

            page.on("request", inspect_destination)
            page.goto("http://127.0.0.1:5173")
            page.get_by_role("button", name="Open provider settings", exact=True).click()
            dialog = page.get_by_role("dialog")
            with page.expect_response(lambda item: item.url.endswith("/api/provider")) as changed:
                dialog.get_by_role("button", name=re.compile(re.escape("Local Meta Llama · OCR + text"))).click()
            assert changed.value.ok and changed.value.json()["provider"]["mode"] == "local_meta"
            expect(page.get_by_text("LOCAL META MODE", exact=True)).to_be_visible()
            expect(dialog.get_by_text(re.compile("Model: " + re.escape(MODEL)))).to_be_visible()
            expect(dialog.get_by_text(re.compile("Meta Llama receives redacted text"))).to_be_visible()
            expect(dialog.get_by_text(re.compile("Built with Llama\\."))).to_be_visible()
            expect(dialog.get_by_role("checkbox", name=re.compile("I consent to sending"))).to_have_count(0)
            assert report["actual_screen_submissions"] == 0
            report["checks"].append("local Meta mode, configured model, OCR/text disclosure, and no cloud consent gate")
            no_overflow("local Meta settings fit desktop 1440px")
            shot("desktop-provider-settings")
            page.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow("local Meta settings fit tablet 1024px")
            shot("tablet-provider-settings")
            page.set_viewport_size({"width": 1440, "height": 1000})
            dialog.get_by_role("button", name="Save preferences", exact=True).click()

            cases = [] if args.ui_only else [("correct-market", "case-correct-market.png", "pass")]
            if args.include_wrong_panel:
                cases.append(("wrong-settings-market", "case-wrong-settings-market.png", "fail"))
            for case_id, screenshot, expected_verdict in cases:
                phase("prepare-" + case_id)
                active = request.get("/api/health").json()["provider"]
                assert active["mode"] == "local_meta", "Provider changed before capture; no screenshot was sent."
                if owned_projects:
                    page.get_by_role("button", name="ReplayLab dashboard", exact=True).click()
                with page.expect_response(lambda item: item.url.endswith("/api/projects/digital-demo")) as created:
                    page.get_by_role("button", name="Try digital demo", exact=True).click()
                project = created.value.json()
                assert created.value.ok and project["modality"] == "digital"
                owned_projects.append(project["id"])
                assert project["completed_step_ids"] == []
                first_step = project["task"]["steps"][0]["id"]
                expect(page.locator(".react-flow__node")).to_have_count(4)
                with page.expect_response(lambda item: item.url.endswith("/approve")) as approved:
                    page.get_by_role("button", name="Approve task", exact=True).click()
                assert approved.value.ok
                page.get_by_role("button", name="Start practice", exact=True).click()
                expect(page.get_by_role("button", name="Upload screenshot", exact=True)).to_be_enabled()
                expect(page.get_by_role("button", name="Choose screen or window", exact=True)).to_be_enabled()
                expect(page.get_by_role("checkbox", name=re.compile("I consent to sending this project"))).to_have_count(0)
                expect(page.get_by_text(re.compile("Meta Llama receives only redacted OCR text"))).to_be_visible()
                report["checks"].append(case_id + ": actual approved template is ready without cloud consent")
                shot(case_id + "-ready")
                assert report["actual_screen_submissions"] < report["screen_submission_budget"]
                phase("infer-" + case_id)
                report["actual_screen_submissions"] += 1
                save()
                started = time.perf_counter()
                with page.expect_response(lambda item: item.url.endswith("/screen-check"), timeout=300000) as observed:
                    page.get_by_label("Upload screen screenshot", exact=True).set_input_files(str(SCREENSHOTS / screenshot))
                response = observed.value
                elapsed = round((time.perf_counter() - started) * 1000, 2)
                body = response.json()
                case = {"id": case_id, "screenshot": screenshot, "expected_verdict": expected_verdict,
                        "http_status": response.status, "browser_request_latency_ms": elapsed}
                report["cases"].append(case)
                save()
                assert response.ok, "Actual local Meta screen request failed; inspect the recorded HTTP status and UI."
                result, observation = body["result"], body["observation"]
                provenance = observation["provenance"]
                case.update({
                    "actual_verdict": result["status"], "matches_expected": result["status"] == expected_verdict,
                    "result_provider": result["provider_mode"], "observation_provider": observation["provider_mode"],
                    "requested_model": provenance.get("model"), "response_model": provenance.get("response_model"),
                    "local_only": provenance.get("local_only"), "vision_inference": provenance.get("vision_inference"),
                    "api_response_validated": provenance.get("api_response_validated"),
                    "live_api_verified": provenance.get("live_api_verified"),
                    "observation_latency_ms": provenance.get("latency_ms"), "request_id": provenance.get("request_id"),
                    "token_usage": provenance.get("token_usage"), "ocr_selected_count": provenance.get("ocr_selected_count"),
                    "completed_step_ids": body["completed_step_ids"], "screen_stored": body.get("screen_stored"),
                    "explanation_provider": (body.get("verification") or {}).get("provider", {}).get("explanation"),
                    "explanation": result.get("explanation"), "reason": result.get("reason"),
                    "rule_results": result.get("rule_results", []), "evidence": result.get("evidence", []),
                    "observed_visible_text": observation.get("visible_text"),
                    "observed_elements": observation.get("elements", []),
                    "observation_confidence": observation.get("confidence"),
                    "image_quality": observation.get("image_quality"),
                    "interface_version": observation.get("interface_version"),
                    "missing_information": provenance.get("missing_information", []),
                    "visible_application": provenance.get("visible_application"),
                    "current_window": provenance.get("current_window"),
                    "warnings": result.get("warnings", []),
                })
                save()
                assert result["provider_mode"] == observation["provider_mode"] == "local_meta"
                assert provenance.get("model") == MODEL
                assert provenance.get("local_only") is True and provenance.get("vision_inference") is False
                assert provenance.get("api_response_validated") is True and provenance.get("live_api_verified") is True
                assert provenance.get("request_id"), "A validated local model response identifier is required."
                case.update(inspect_cloud_consent(response.request))
                # CDP may omit multipart content for binary uploads. Preserve an
                # unknown field rather than fail a valid inference or invent a
                # consent value. Active mode and local-only provenance above are
                # checked independently; frontend tests cover FormData contents.
                assert case["cloud_consent_sent"] is not True, "Local processing unexpectedly sent cloud consent."
                expected_progress = [first_step] if result["status"] == "pass" else []
                assert body["completed_step_ids"] == expected_progress, "Progress must follow the actual deterministic verdict."
                saved = request.get(f"/api/projects/{project['id']}").json()
                assert saved["completed_step_ids"] == expected_progress
                assert request.get("/api/health").json()["provider"]["mode"] == "local_meta"
                expect(page.get_by_role("region", name="Screen verification result")).to_be_visible()
                report["checks"].append(case_id + ": genuine local Meta provenance and verdict-owned progression")
                no_overflow(case_id + ": result fits desktop 1440px")
                shot(case_id + "-actual-result")
                page.set_viewport_size({"width": 1024, "height": 1000})
                no_overflow(case_id + ": result fits tablet 1024px")
                shot(case_id + "-tablet-result")
                page.set_viewport_size({"width": 1440, "height": 1000})
                case["ui_checked"] = True
                save()

            assert not report["page_errors"], "Browser JavaScript errors occurred."
            assert not nonlocal_hosts.intersection({"integrate.api.nvidia.com", "api.meta.ai", "api.openai.com"})
            report["checks"].append("zero browser JavaScript errors and no browser requests to cloud inference hosts")
            report["success"] = all(case.get("matches_expected", False) for case in report["cases"]) if not args.ui_only else True
            phase("complete" if report["success"] else "completed-with-verdict-disagreement")
        except Exception as error:
            report["error"] = {"type": type(error).__name__, "phase": report["phase"]}
            if page is not None and not page.is_closed():
                try:
                    shot("failure-" + report["phase"])
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
                    try:
                        cleaned = request.delete(f"/api/projects/{identifier}")
                        report["cleanup"].append({"owned_project": identifier, "http_status": cleaned.status})
                    except PlaywrightError as error:
                        report["cleanup"].append({"owned_project": identifier, "error_type": type(error).__name__})
                request.dispose()
            save()
            print(json.dumps({"success": report["success"], "checks": len(report["checks"]),
                "actual_screen_submissions": report["actual_screen_submissions"],
                "cases": [{"id": case["id"], "verdict": case.get("actual_verdict"), "http_status": case["http_status"]}
                          for case in report["cases"]], "page_errors": len(report["page_errors"]),
                "report": str(report_path.relative_to(ROOT))}), flush=True)
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
