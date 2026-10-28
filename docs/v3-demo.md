# ReplayLab 3.0 demonstration

The [three-minute walkthrough](assets/v3/demo.mp4) records the running local React/FastAPI application. It uses offline transcript extraction, real local OCR, and deterministic verification. No Meta call is presented as live. The extension target is the clearly labeled CodeLab simulation; no third-party software is installed.

The first checkpoints use a real browser `getDisplayMedia()` tab stream. After demonstrating PASS, a wrong-panel FAIL, correction, and insufficient-evidence UNCERTAIN, the recording explicitly stops sharing. Version and final checkpoints then use the application's manual screenshot-review option with fresh captures of the actual target browser. The subtitles disclose this transition. This avoids a background-tab frame-delivery freeze observed while recording in headless Chromium; a stale view was correctly treated as insufficient evidence, and that failed recording was rejected.

## Reproduce

Start the application with `npm.cmd run dev`. The optional browser tooling runs under system Python, separately from the API environment:

```powershell
python -m pip install playwright==1.60.0
python -m playwright install chromium
python scripts/record-v3-demo.py
python scripts/record-v3-demo.py --record
```

The first command runs the same browser assertions without recording or timed holds. `--record` records at normal speed, adds explanatory subtitles with FFmpeg, and exports an exactly 180-second H.264 MP4. FFmpeg and FFprobe must be available on PATH. The script creates and deletes only its own controlled demonstration projects. It selects mock workflow reasoning explicitly; digital observations still come from real OCR on submitted pixels.

Chromium's test-only `--auto-select-tab-capture-source-by-title=ReplayLab CodeLab` flag chooses the separate CodeLab tab after the user-facing share-button gesture. The script uses the full browser with `channel="chromium"`; it does not replace `getDisplayMedia`, intercept API responses, select requested verdicts, or inject fixture observations into digital verification. This does not test a human-operated OS permission picker.

## Script and shot list

The script holds scenes against a three-minute clock while preserving actual interaction and processing time. The [subtitle file](assets/v3/demo-captions.srt) records the observed scene transitions; processing can shift them slightly from this shot list.

| Approximate time | Actual application interaction | Disclosure |
| --- | --- | --- |
| 0:00–0:20 | Workspace and verification problem | Local research preview; offline workflow extraction |
| 0:20–0:37 | Create digital project, upload rights-cleared tutorial, paste timestamped transcript | Source video is synthetic CodeLab footage; source frames are actually extracted |
| 0:37–0:49 | Generate graph, review rules, set visible reference version, approve | Proposal requires review; quoted labels are offline candidates |
| 0:49–1:08 | Start real tab sharing and verify Extensions | Real local OCR produces PASS |
| 1:08–1:36 | Show wrong Settings/Preferences, inspect FAIL, correct search | Contradictory visible evidence is required for FAIL |
| 1:36–1:48 | Show a view without required extension details | Missing evidence produces UNCERTAIN |
| 1:48–1:59 | Stop sharing and manually review an actual CodeLab 2.0 screenshot | Visible version mismatch produces UNCERTAIN |
| 1:59–2:14 | Review matching-version details and final Installed/Enabled screenshots | Manual review uses real browser pixels; target install is simulated |
| 2:14–2:22 | Inspect explicitly saved redacted decision history | Capture track is ended; digital screenshots are not saved |
| 2:22–2:33 | Physical fixture checkpoint and shared decision inspector | Physical observations are labeled fixtures; no live SAM claim |
| 2:33–2:46 | Display measured 20-case digital evaluation and limitations | Controlled team-authored cases; no independent human study or broad accuracy claim |
| 2:46–3:00 | Provider status and technical distinction | Muse/SAM adapters implemented; live Meta validation and eligibility pending |

## Evidence and limits

The 28 October 2026 recorded run passed **13 assertion groups**, made **seven actual digital OCR checks** (four through the live tab stream, three through manual screenshot review), and reported **zero browser JavaScript errors**. The digital sequence was PASS, FAIL, PASS, UNCERTAIN, UNCERTAIN, PASS, PASS; a physical fixture PASS was checked separately. The exported MP4 is **180.000 seconds**, **1280 × 960**, **4,500 frames**, and **3,759,818 bytes**. Its subtitles were checked in a decoded output frame for readability.

The [validation report](assets/v3/demo-validation.json) contains the browser version, actual screen-check verdict sequence, assertion groups, page-error count, elapsed run time, and FFprobe metadata. Captures in [assets/v3](assets/v3) show the actual dashboard, uploaded tutorial, graph review, PASS, FAIL, missing evidence, version mismatch, completion, saved history, physical shared inspector, measured evaluation, and provider status. Desktop and tablet widths are checked at 1440 and 1024 pixels; these are tested sizes, not exhaustive device coverage.

The MP4 is a silent browser recording with editorial subtitles in a separate lower band. Those subtitles describe the actions and limitations; every verdict remains the application's actual API result. No scene substitutes fabricated inference or stock screenshots for implemented functionality. The original [physical recording](assets/demo.mp4) is preserved separately.

The live digital path was also exercised without recording during development. The recording shows a reliable combination of live capture and manual review and must not be described as seven successful live-stream checks. Arbitrary software workflows, a real VS Code extension install, a human-operated permission picker, physical camera hardware, and live Meta model inference remain outside this video's validation.
