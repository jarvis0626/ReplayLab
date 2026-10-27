# ReplayLab 2 actual digital browser QA

This run used real headless Chromium 148.0.7778.96, the running local Vite/FastAPI application, and actual local OCR. No getDisplayMedia stub, network response interception, fixture observation lookup, or requested outcome was used. The shared source was a separate, explicitly labeled CodeLab simulator tab; its software installation is simulated. This does not establish arbitrary workflow support or live Meta inference.

The browser's explicit share button started an actual `getDisplayMedia` call. Chromium's test-only `--auto-select-tab-capture-source-by-title=ReplayLab CodeLab` flag selected that tab in place of a human picker. Track settings reported `displaySurface:browser` and `readyState:live`; stopping changed the same track to `ended`. This validates a real browser tab stream under test selection, not a manually exercised operating-system permission picker. The script uses `channel="chromium"` for the full new headless browser; the default headless shell denied capture in this environment. See the primary [Playwright browser guidance](https://playwright.dev/python/docs/browsers#chromium-new-headless-mode) and [Chromium test-selection flag source](https://chromium.googlesource.com/chromium/src/+/refs/tags/147.0.7727.118/chrome/common/chrome_switches.cc).

| Browser interaction | Actual result |
| --- | --- |
| desktop dashboard at 1440px | PASS |
| desktop digital graph at 1440px | PASS |
| desktop tutorial studio at 1440px | PASS |
| generated digital tutorial MP4 loads, plays, and shows four synthetic source references | PASS |
| digital graph, task edit, save, and explicit approval | PASS |
| desktop CodeLab simulator at 1440px | PASS |
| real getDisplayMedia separate-tab capture -> local OCR -> first-step PASS | PASS |
| desktop live screen coach at 1440px | PASS |
| pause prevents new periodic screen checks | PASS |
| visible wrong destination -> FAIL | FAIL |
| Ask returns grounded template with explicit provenance | PASS |
| correct visible search -> second-step PASS | PASS |
| visible extension details -> third-step PASS | PASS |
| visible Permission denied dialog -> FAIL | FAIL |
| visible CodeLab 2.0 -> interface-mismatch UNCERTAIN | UNCERTAIN |
| visible Installed and Enabled -> final PASS and 4/4 completion | PASS |
| tablet live screen coach at 1024px | PASS |
| stop ends actual track, clears Ask and session, and prevents further capture | PASS |
| no overlapping screen checks or JavaScript page errors | PASS |

**19 assertion groups passed.** Successful screen-check responses: **7**. Peak concurrent screenshot requests: **1**. JavaScript page errors: **0**. Screenshots were not retained by the API. Desktop and tablet page widths were checked at 1440 x 1000 and 1024 x 1000; these are tested sizes, not exhaustive device coverage.

All images below capture the actual running application and synthetic CodeLab interface. They are not stock images or fabricated inference screenshots.

| Artifact | Observed feature |
| --- | --- |
| [Dashboard](assets/v2/dashboard.png) | Physical and digital workflow entry points |
| [Digital task graph](assets/v2/digital-task-graph.png) | Four dependent steps and explicit review gate |
| [Tutorial studio](assets/v2/digital-tutorial-studio.png) | Generated demo MP4, extracted source frames, and transcript |
| [CodeLab simulator](assets/v2/codelab-simulator.png) | Clearly labeled synthetic target application |
| [Sharing and PASS](assets/v2/screen-sharing-pass.png) | Actual shared-tab video and local OCR evidence |
| [Wrong destination](assets/v2/wrong-destination-fail.png) | Visible Preferences panel produces FAIL |
| [Unexpected dialog](assets/v2/unexpected-dialog-fail.png) | Visible Permission denied error produces FAIL |
| [Version mismatch](assets/v2/interface-version-uncertain.png) | Visible CodeLab 2.0 produces UNCERTAIN |
| [CodeLab final state](assets/v2/codelab-complete.png) | User-triggered simulated Installed and Enabled state |
| [Completed workflow](assets/v2/digital-workflow-complete.png) | Final OCR-backed PASS and 4 / 4 progress |
| [Tablet coach](assets/v2/tablet-screen-coach.png) | Actual 1024-pixel layout |

The harness brings the selected source tab to the foreground to obtain its initial painted frame, then returns to the coach. After source changes it waits for delivered video frames before resuming analysis. These are browser focus and frame-delivery controls, not observation or verdict substitutions. The application also rechecks at a bounded heartbeat so thumbnail gating cannot indefinitely hide a small semantic label change.

No recording was requested for this run.

Run against the intended local test workspace using `python scripts/digital-browser-smoke.py` after starting the application. System Python needs Playwright and its Chromium browser. Optional `--record` export needs FFmpeg and FFprobe; recording was not part of this successful run. The script explicitly selects mock workflow reasoning and uses real local OCR for screen pixels. It retains one completed showcase project after success and deletes only its own failed project after failure. Runtime project data is not committed.

Optional QA prerequisites and replay commands (the application itself does not require Playwright):

```sh
python -m pip install playwright==1.60.0
python -m playwright install chromium
python scripts/digital-browser-smoke.py
```

Manual permission-picker interaction, physical screen-sharing hardware/browser variants, live Meta screenshot inference, and real third-party extension installation remain unverified. The physical-task browser regression is reported separately in [browser-qa.md](browser-qa.md).

Elapsed run time: 96.8 seconds. Showcase project ID: `ac036aafbf424323af8327cc56298fee` (local runtime data only).
