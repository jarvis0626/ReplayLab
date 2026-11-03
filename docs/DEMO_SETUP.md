# Preparing and recording the real demonstration

The accepted [MP4](../ReplayLab_Meta_Hackathon_Demo.mp4) exists and has been
validated: **176.4 s, 1920 × 1080, H.264, 30 FPS**. It is a silent, continuous
capture of the real application, with the target visible through genuine tab
sharing. [Verification](DEMO_VERIFICATION.md) records the actual outcomes.

This laptop also has a fresh prepared project named **Hackathon live
demonstration — ready for your run**, with two unapproved steps and no completion.
The default launcher discovers it. The recorded project and its results remain
separate. To create another fresh copy of the tested reviewed workflow:

```powershell
python scripts/prepare_hackathon_demo.py --clone-from 74cba3aa8c4b4f998587b5d08c6f283a --name "Hackathon live demonstration - fresh run"
```

Run the launcher from the repository root in PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_demo.ps1
```

The launcher validates installed dependencies and server configuration without
printing credentials, reuses healthy local services, waits for readiness and
opens the application. The selected provider for this demonstration is
`local_meta`, serving `meta-llama/Llama-3.2-3B-Instruct` on this PC. Setup does not
establish NVIDIA Muse cloud availability.

Use `-NoBrowser` to keep the launcher from opening a tab, `-CheckOnly` to validate
without starting anything, and `-ProjectId <32-hex-id>` to select a specific
prepared demonstration. Without an ID it locates the latest ready genuine Meta
project named “Hackathon live demonstration…”. It does not approve that project.

Use the prepared, genuinely extracted digital tutorial described in
[readiness](DEMO_READINESS.md). Review the source video, transcript, graph and
visible-label rules before approval. The older owner project “Local Meta
generated walkthrough” is not the recording script's project and must remain
unchanged unless separately approved by its owner.

The separate system Python installation contains Playwright; the API `.venv`
does not. With the local application running, this preparation command records
real CodeLab interactions, uploads the resulting tutorial, saves its transcript
and requests actual local Meta extraction:

```powershell
python scripts/prepare_hackathon_demo.py --name "Hackathon live demonstration - prepared review"
```

Raw model output may contain more than two steps or incidental visible labels.
Review it before approval. The tested scenario uses two transcript-supported
actions, with the first expecting “Extensions Marketplace” and the explicit
contradiction “Preferences”; the next expects “Search results” and
“Replay Formatter”. A navigation label visible on every screen does not prove an
active panel. The final preparation was reviewed by the owner-authorized agent,
not an independent human reviewer. Review changes remain in task provenance.

For a manual take, open ReplayLab and its CodeLab target in separate browser tabs.
Keep the visible simulation disclosure. Choose the **CodeLab tab** in the real
screen-sharing picker, rather than the recording display or ReplayLab tab. This
avoids mirror capture. Start on Settings, correct to Extensions, then open
Explorer for the next unresolved checkpoint. Use Pause between observations so
the presenter can explain evidence without sending repeated model requests.

Keep keys, `.env`, private media and the owner’s `test.py` out of view. The
automated recorder captures only a fresh ReplayLab browser page and its selected
CodeLab stream; it does not record the owner's desktop, existing browser profile,
notifications, terminal windows or VS Code window. It leaves unrelated applications
running. Browser viewport is 1920 × 1080; text is rendered by the real application.

The installed FFmpeg build includes Windows `gdigrab`; OBS was not found in its
standard installation paths or running processes. The automated path therefore
uses the actual Chromium page video stream and converts that one continuous
source to H.264 MP4. FFmpeg validates duration, dimensions, 30 FPS and complete
decoding. There is no concatenation, trimming, speed change, artificial padding,
replacement frame, generated screenshot, verdict override or app DOM overlay.
The final artifact is silent; [narration](DEMO_SCRIPT.md) is supplied separately.

Rehearse with a **new, unapproved** project prepared specifically for this run:

```powershell
python scripts/record_hackathon_demo.py --project-id <rehearsal-project-id>
```

The script explicitly approves and practices the supplied project. It preserves
that project's results for inspection. It never edits or deletes other projects.
Successful and failed run reports are retained under `.artifacts/hackathon-demo-*`.
An unsuccessful run does not become the final MP4.

Then use a second, fresh unapproved project containing the same genuinely
extracted prepared task, source and rules:

```powershell
python scripts/prepare_hackathon_demo.py --clone-from <rehearsal-project-id> --name "Hackathon live demonstration - prepared recording"
```

This copies the genuine prepared media and reviewed task into a new project,
retains the original model request provenance and marks `prepared_copy_from`.
It does not claim a new extraction. The returned project starts unapproved with
no completed steps. Then record it:

```powershell
python scripts/record_hackathon_demo.py --project-id <fresh-recording-project-id> --record --rehearsal-report .artifacts/<successful-run>/rehearsal.json
```

Recording requires a successful matching rehearsal and current recorder version.
Chromium's test-only tab-title flag selects the real CodeLab stream after the
application's share gesture. This exercises `getDisplayMedia`; a human operating
system permission picker is not claimed. Target rendering runs in a separate
unrecorded context to keep captured frames updating while ReplayLab is recorded.

The expected output is `ReplayLab_Meta_Hackathon_Demo.mp4` in the repository root,
175–180 seconds long. The recorder checks the actual file before reporting it as
created. See [verification](DEMO_VERIFICATION.md) for the actual latest outcome,
latencies, sample sizes and remaining limitations.

For a human-narrated recording, follow [the timed script](DEMO_SCRIPT.md) with OBS
or another already trusted recorder. Record a fresh single take with the audio
live. Do not present a prepared workflow as newly extracted during that take.
Do not hide an error or substitute the older offline recording.

The window capture option is documented in the official
[FFmpeg device documentation](https://ffmpeg.org/ffmpeg-devices.html#gdigrab).
The automated stream uses Playwright's full
[new Chromium headless mode](https://playwright.dev/python/docs/browsers#chromium-new-headless-mode).
