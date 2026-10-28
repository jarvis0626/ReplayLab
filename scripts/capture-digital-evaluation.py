"""Capture twenty pre-labeled controlled browser cases without running inference.

Requires optional system Playwright. This captures only the local CodeLab
simulation, never the desktop or any user application. Labels stay fixed even
when a later evaluation disagrees with them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "demo" / "evaluation" / "digital"

# Ground truth is authored here before any inference. No predictions are read.
CASES = [
    ("correct-market", "Marketplace is visibly open", "correct", "market", 1, "pass", {}),
    ("correct-search", "The requested package appears in search results", "correct", "search", 2, "pass", {}),
    ("correct-details", "Package details and install control are visible", "correct", "details", 3, "pass", {}),
    ("correct-installed", "Package is visibly installed and enabled", "correct", "installed", 4, "pass", {}),
    ("correct-tablet", "Marketplace at a tablet viewport", "correct", "market", 1, "pass", {"width": 1024}),
    ("wrong-settings-market", "Settings contradicts the marketplace checkpoint", "incorrect", "settings", 1, "fail", {}),
    ("wrong-settings-search", "Settings contradicts the package search checkpoint", "incorrect", "settings", 2, "fail", {"width": 1280}),
    ("wrong-dialog-market", "Permission error interrupts the marketplace", "incorrect", "market", 1, "fail", {"dialog": True}),
    ("wrong-not-installed", "Install control contradicts an installed checkpoint", "incorrect", "details", 4, "fail", {}),
    ("wrong-dialog-details", "Permission error interrupts extension details", "incorrect", "details", 3, "fail", {"dialog": True}),
    ("ambiguous-welcome", "Welcome screen does not establish the requested panel", "ambiguous", "welcome", 1, "uncertain", {}),
    ("ambiguous-empty-search", "Unrelated empty results cannot prove the requested package", "ambiguous", "empty-search", 2, "uncertain", {}),
    ("ambiguous-obscured", "An opaque privacy region hides the relevant content", "ambiguous", "market", 1, "uncertain", {"mask": True}),
    ("ambiguous-cropped", "Only application chrome is visible", "ambiguous", "market", 1, "uncertain", {"crop": True}),
    ("ambiguous-blurred", "Strong blur makes target labels unreadable", "ambiguous", "details", 3, "uncertain", {"blur": True}),
    ("version-market", "A visible different version makes marketplace comparison uncertain", "interface_difference", "market", 1, "uncertain", {"version": True}),
    ("version-search", "A visible different version makes search comparison uncertain", "interface_difference", "search", 2, "uncertain", {"version": True}),
    ("version-details", "A visible different version makes details comparison uncertain", "interface_difference", "details", 3, "uncertain", {"version": True}),
    ("version-installed", "A visible different version makes installed comparison uncertain", "interface_difference", "installed", 4, "uncertain", {"version": True}),
    ("version-settings", "Version difference prevents attributing a menu mismatch to the user", "interface_difference", "settings", 1, "uncertain", {"version": True, "width": 1280}),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5173")
    args = parser.parse_args()
    shots = DIRECTORY / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    frozen_plan = [
        {
            "id": identifier,
            "title": title,
            "category": category,
            "state": state,
            "reference_step_id": f"digital-step-{step}",
            "completed_step_ids": [f"digital-step-{earlier}" for earlier in range(1, step)],
            "expected": expected,
            "capture_options": options,
            "screenshot": f"case-{identifier}.png",
        }
        for identifier, title, category, state, step, expected, options in CASES
    ]
    # Materialize the labeling plan before capture, and before all inference.
    (DIRECTORY / "label-plan.json").write_text(json.dumps(frozen_plan, indent=2) + "\n", encoding="utf-8", newline="\n")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, channel="chromium")
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        for case in frozen_plan:
            options = case["capture_options"]
            page.set_viewport_size({"width": options.get("width", 1440), "height": 1000})
            page.goto(args.base_url + "/?digital-demo=1", wait_until="networkidle")
            expect(page.get_by_text("Your next skill starts here.")).to_be_visible()
            state = case["state"]
            if state == "settings":
                page.get_by_role("button", name="Settings", exact=True).click()
                expect(page.get_by_role("heading", name="Preferences")).to_be_visible()
            elif state != "welcome":
                page.get_by_role("button", name="Extensions", exact=True).click()
                if state in {"search", "details", "installed", "empty-search"}:
                    page.get_by_role("textbox", name="Search extensions").fill(
                        "unrelated package" if state == "empty-search" else "Replay Formatter"
                    )
                if state in {"details", "installed"}:
                    page.locator(".codelab-package").click()
                if state == "installed":
                    page.get_by_role("button", name="Install extension", exact=True).click()
                    expect(page.get_by_text("Installed", exact=True)).to_be_visible()
            if options.get("version"):
                page.get_by_role("button", name="Change UI version").click()
                expect(page.locator(".codelab-title strong")).to_have_text("CodeLab 2.0")
            if options.get("dialog"):
                page.get_by_role("button", name="Show unexpected dialog").click()
                expect(page.get_by_role("dialog")).to_be_visible()
            if options.get("mask"):
                page.add_style_tag(content=".codelab-editor { position: relative; } .codelab-editor::after { content: ''; position: absolute; inset: 0; background: #161d2b; z-index: 20; }")
            if options.get("blur"):
                page.add_style_tag(content=".codelab-editor { filter: blur(16px); }")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(120)
            path = shots / case["screenshot"]
            if options.get("crop"):
                page.locator(".codelab-title").screenshot(path=path)
            else:
                page.screenshot(path=path)
            case["screenshot_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            print(f"Captured {case['id']} ({case['expected']} pre-labeled)", flush=True)
        metadata = {"browser": "Chromium", "browser_version": browser.version, "device_scale_factor": 1}
        browser.close()
    dataset = {
        "name": "ReplayLab CodeLab controlled browser challenge v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "label_provenance": "Coding-agent-authored challenge labels fixed in label-plan.json before capture and before OCR inference; not independent human annotation.",
        "capture_metadata": metadata,
        "cases": frozen_plan,
    }
    (DIRECTORY / "cases.json").write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8", newline="\n")
    interpreter = ROOT / ".venv" / "Scripts" / "python.exe"
    if not interpreter.is_file():
        interpreter = ROOT / ".venv" / "bin" / "python"
    source = (
        "import json,sys;from pathlib import Path;sys.path.insert(0,str(Path.cwd()/'apps'/'api'));"
        "from app.services.digital_demo import digital_demo_task;"
        "task=digital_demo_task([{'id':f'reference-{i}'} for i in range(1,5)]);"
        "task.id='codelab-evaluation-workflow-v1';"
        "Path('demo/evaluation/digital/workflow.json').write_text(json.dumps(task.model_dump(mode='json'),indent=2)+'\\n',encoding='utf-8',newline='\\n')"
    )
    subprocess.run([str(interpreter), "-c", source], cwd=ROOT, check=True)
    print("Twenty labeled screenshots frozen. Run the separate evaluation command; no inference ran during capture.")


if __name__ == "__main__":
    main()
