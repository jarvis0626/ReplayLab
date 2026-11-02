"""Exercise one real consented NVIDIA screen request and explicit offline recovery.

No browser/network responses are replaced. Only repository-owned CodeLab pixels
are submitted; credentials remain inside the API. A provider failure is recorded
as a failure, never as a fabricated UNCERTAIN verdict or a successful integration.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "nvidia"
SCREENSHOT = ROOT / "demo" / "evaluation" / "digital" / "screenshots" / "case-correct-market.png"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-live", action="store_true", help="Continue offline checks using already preserved live-failure evidence; sends no additional cloud screenshot.")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    checks, page_errors, screen_responses = [], [], []
    identifier = None
    with sync_playwright() as playwright:
        request = playwright.request.new_context(base_url="http://127.0.0.1:8010")
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(type(error).__name__))
        page.on("response", lambda response: screen_responses.append(response.status)
                if response.url.endswith("/screen-check") else None)

        def shot(name):
            page.screenshot(path=str(OUTPUT / f"{name}.png"), full_page=True)

        def no_overflow(label):
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), label
            checks.append(label)

        def choose(mode):
            page.get_by_role("button", name="Open provider settings", exact=True).click()
            name = "NVIDIA cloud vision" if mode == "nvidia" else "Offline / mock"
            page.get_by_role("dialog").get_by_role("button").filter(has=page.get_by_text(name, exact=True)).click()
            expect(page.get_by_text("NVIDIA MODE" if mode == "nvidia" else "MOCK MODE", exact=True)).to_be_visible()

        try:
            health = request.get("/api/health").json()
            assert health["status"] == "ok"
            page.goto("http://127.0.0.1:5173")
            expect(page.get_by_role("button", name="Open provider settings", exact=True)).to_be_visible()
            choose("nvidia")
            expect(page.get_by_text("NVIDIA access unverified", exact=True)).to_be_visible()
            expect(page.get_by_text(re.compile("Model: meta/muse-glimmer-30b"))).to_be_visible()
            expect(page.get_by_role("checkbox", name=re.compile("I consent to sending this session"))).not_to_be_checked()
            no_overflow("NVIDIA settings fit desktop 1440px")
            shot("provider-unverified")
            page.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow("NVIDIA settings fit tablet 1024px")
            shot("tablet-provider-settings")
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.get_by_role("button", name="Save preferences", exact=True).click()
            with page.expect_response(lambda response: response.url.endswith("/api/projects/digital-demo")) as created:
                page.get_by_role("button", name="Try digital demo", exact=True).click()
            project = created.value.json()
            identifier = project["id"]
            expect(page.locator(".react-flow__node")).to_have_count(4)
            page.get_by_role("button", name="Approve task", exact=True).click()
            page.get_by_role("button", name="Start practice", exact=True).click()
            expect(page.get_by_role("button", name="Choose screen or window", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Upload screenshot", exact=True)).to_be_disabled()
            assert screen_responses == []
            checks.append("no media request before separate project screen consent")
            shot("screen-consent-required")
            page.get_by_role("checkbox", name=re.compile("I consent to sending this project")).check()
            expect(page.get_by_role("button", name="Upload screenshot", exact=True)).to_be_enabled()
            if args.skip_live:
                live_evidence = json.loads((OUTPUT / "live-failure-validation.json").read_text(encoding="utf-8"))
                assert live_evidence["actual_nvidia_status"] == 502
            else:
                started = time.perf_counter()
                with page.expect_response(lambda response: response.url.endswith("/screen-check"), timeout=60000) as observed:
                    page.get_by_label("Upload screen screenshot", exact=True).set_input_files(str(SCREENSHOT))
                response = observed.value
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                body = response.json()
                assert response.status == 502, "The expected unavailable-provider check returned another status; inspect the actual response."
                assert "NVIDIA" in body["detail"] and re.search("timed out|Retry", body["detail"], re.IGNORECASE)
                expect(page.get_by_role("alert")).to_contain_text("NVIDIA")
                assert request.get(f"/api/projects/{identifier}").json()["completed_step_ids"] == []
                assert request.get("/api/health").json()["provider"]["mode"] == "nvidia"
                assert request.get("/api/health").json()["provider"]["live_verified"] is False
                assert len(screen_responses) == 1
                live_evidence = {
                    "actual_nvidia_screen_requests": 1, "actual_nvidia_status": response.status,
                    "actual_nvidia_latency_ms": latency_ms, "completed_step_count": 0,
                    "provider_after_failure": "nvidia", "live_verified": False,
                    "actual_nvidia_success": False, "no_mock_result_returned": True,
                }
                (OUTPUT / "live-failure-validation.json").write_text(json.dumps(live_evidence, indent=2) + "\n", encoding="utf-8", newline="\n")
                checks.append("one actual NVIDIA request fails visibly with no verdict, progress, or automatic fallback")
                shot("actual-nvidia-timeout")
            choose("mock")
            page.get_by_role("button", name="Save preferences", exact=True).click()
            expect(page.get_by_role("button", name="Upload screenshot", exact=True)).to_be_enabled()
            with page.expect_response(lambda item: item.url.endswith("/screen-check"), timeout=30000) as offline:
                page.get_by_label("Upload screen screenshot", exact=True).set_input_files(str(SCREENSHOT))
            offline_body = offline.value.json()
            assert offline.value.ok and offline_body["result"]["provider_mode"] == "local_ocr"
            assert offline_body["result"]["status"] == "pass"
            assert len(offline_body["completed_step_ids"]) == 1
            checks.append("explicit user provider switch restores real local OCR PASS and progression")
            shot("explicit-offline-recovery")
            page.get_by_role("navigation", name="Project workspace").get_by_role("button", name="Evaluation", exact=True).click()
            page.get_by_role("button", name="NVIDIA model evaluation", exact=True).click()
            expect(page.get_by_text("0 cases", exact=True)).to_be_visible()
            expect(page.get_by_text(re.compile("No completed live model cases"))).to_be_visible()
            expect(page.get_by_role("button", name="Run evaluation", exact=True)).to_be_disabled()
            report = request.get("/api/evaluation/nvidia").json()
            assert report["sample_size"] == 0 and report["target_size"] == 20
            assert report["accuracy"] is None and report["live_api_verified"] is False
            assert len(report["skipped"]) == 20 and report["attempted_cases"] == 2
            assert report["failure_circuit_open"] is True
            checks.append("NVIDIA evaluation preserves two actual failures and eighteen unattempted cases with unknown metrics")
            no_overflow("NVIDIA evaluation fits desktop 1440px")
            shot("nvidia-evaluation-unavailable")
            page.set_viewport_size({"width": 1024, "height": 1000})
            no_overflow("NVIDIA evaluation fits tablet 1024px")
            shot("tablet-nvidia-evaluation")
            assert not page_errors, "Browser JavaScript errors occurred."
            checks.append("zero browser JavaScript errors")
            metadata = {
                "browser": browser.version, "checks": checks,
                "live_failure_evidence": live_evidence,
                "actual_nvidia_requests_this_browser_phase": 0 if args.skip_live else 1,
                "continued_after_harness_selector_fix": args.skip_live,
                "offline_recovery_verdict": offline_body["result"]["status"],
                "offline_recovery_provider": offline_body["result"]["provider_mode"],
                "nvidia_evaluation_completed": 0, "nvidia_evaluation_attempted": report["attempted_cases"],
                "nvidia_evaluation_unattempted": len(report["skipped"]) - report["attempted_cases"],
                "page_errors": len(page_errors),
                "limitations": [
                    "No successful NVIDIA inference or live-model accuracy is established.",
                    "Only a repo-owned controlled CodeLab screenshot was sent after explicit in-app consent.",
                    "Manual screenshot review was exercised; this check does not validate a human screen picker or live tab stream.",
                    "The existing offline three-minute demo is preserved; no fabricated live-success video was made.",
                ],
            }
            (OUTPUT / "browser-validation.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(json.dumps({"checks": len(checks), "nvidia_status": live_evidence["actual_nvidia_status"], "offline_verdict": "pass", "page_errors": 0}), flush=True)
        finally:
            context.close()
            browser.close()
            if identifier:
                assert request.delete(f"/api/projects/{identifier}").status == 204
            assert request.post("/api/provider", data={"mode": "nvidia"}).ok
            request.dispose()


if __name__ == "__main__":
    main()
