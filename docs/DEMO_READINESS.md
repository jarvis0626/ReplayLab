# Live demonstration readiness

**4 November current three-minute demonstration:** [2:59.07 video](../ReplayLab_Meta_Hackathon_Demo.mp4)
shows the full tutorial, fresh Meta generation, visible review/approval, real
shared-screen FAIL, correction, PASS and UNCERTAIN, evaluation and completed graph.
Meta Llama 3.2 1B runs on AMD Vulkan, with natural GuyNeural narration and no spoken
preamble. [Accepted recording and audio evidence](THREE_MINUTE_DEMO.md).
The earlier prepared-workflow measurements below remain historical. The separate
[short proof](TUTORIAL_PROOF.md) is archived; neither is the current main video.

**Ready.** The accepted [continuous demonstration](assets/prepared-workflow-demo.mp4)
is **2:56.4**, **1920×1080**, **30 FPS**, H.264 MP4. It shows actual local Meta
inference, a real target-tab stream, **FAIL → correction → PASS → UNCERTAIN**,
the measured evaluation, and the provider disclosure. The video includes locally generated synthetic narration, disclosed in the first
spoken sentence. The [spoken script and timestamps](DEMO_SCRIPT.md) and
[audio validation](validation/hackathon-voiceover.json) document the addition.
The original video packets, frames, and timing are unchanged.

Audit date: **3 November 2026 (Asia/Calcutta)**. This document distinguishes actual
executed checks from implemented capabilities. A successful unit test is not a
successful model call or a human-operated screen-sharing test.

## Provider and truthful presentation

The selected provider is **`local_meta`**, serving
**`meta-llama/Llama-3.2-3B-Instruct`** through the loopback llama.cpp server. The
model is a pinned Q4_K_M community conversion of Meta's original Llama model.
**Built with Llama.** Actual local OCR reads screenshot pixels; Llama receives
redacted text and proposes workflow steps or grounded explanation plans.
Deterministic constraints decide PASS, FAIL, and UNCERTAIN.

The rehearsal makes three fresh **Meta observation** requests. Grounded
explanation plans are a separate path and may reuse a validated cache entry;
UNCERTAIN uses the deterministic explanation template. The recording does not
claim three fresh model-generated explanations.

This is real Meta text inference on the laptop's CPU. It is not Meta Muse Glimmer
vision, SAM segmentation, or a successful NVIDIA cloud call. The API's
`live_verified` flag is scoped to the current server instance and becomes true
only after an actual validated successful inference response. Selecting the mode
or getting model-server health does not itself prove inference success.

The earlier [local Meta browser report](assets/local-meta/browser-validation.json)
records two actual model-backed screen requests. The earlier
[workflow report](validation/local-meta-workflow.json) records one actual
two-step Meta proposal from a timestamped transcript. Those historical results
are not presented as freshly executed checks for this demonstration.

Fresh preparation in this task also succeeded: a **14.92-second** continuous
recording of actual CodeLab interactions was uploaded, four source frames were
extracted, and real Meta inference generated a five-step proposal from the
transcript plus local frame OCR in **110.048 s**. That proposal required review:
the coding agent retained the two intended tutorial actions and removed
duplicated/incidental OCR actions and ambiguous navigation labels. The edited
task records `user_edited=true` and the original proposal hash, five original
steps, two retained steps, and exact review changes. It must be presented as a
**prepared, reviewed Meta-generated workflow**, not untouched model output or
an extraction occurring during the final recording.

## Feature audit

| Feature requested | Verified evidence and recording suitability |
| --- | --- |
| Frontend/backend startup | The final default demo-launcher check passed: UI, API, selected local Meta provider, model health, and prepared project were healthy; actual inference had set `live_verified=true`. |
| Tutorial upload/processing | Fresh final-demo preparation uploaded a 14.92-second actual CodeLab interaction recording with a rights-cleared timestamped transcript. Processing extracted four real source frames. The target remains a visibly labeled simulation. |
| Workflow extraction | Fresh real Meta inference used the transcript and four locally OCR-read source frames; five proposed steps were reviewed down to the two intended actions. Success took 110.048 s after two failed attempts. Extraction is prepared before recording to fit the time limit. |
| Interactive graph | The fresh complete rehearsal displayed the prepared, reviewed two-step graph and expected states, then approved it before practice. The earlier unmodified owner proposal also returned two nodes and one dependency edge through the graph endpoint. |
| Screen sharing | The fresh complete rehearsal used a genuine browser `getDisplayMedia()` tab stream with 1728×1080 source dimensions. Three actual target changes were submitted through that stream, not saved PNG uploads. Chromium's test-only source selector chose the owned target tab; no mocked stream or human picker is claimed. The track was stopped at the end. |
| Screenshot observation | Three fresh stream-derived local OCR observations completed with validated local Meta response provenance in this task. Llama receives redacted OCR text, not image pixels. |
| PASS | Accepted final take: actual HTTP 200, deterministic PASS in 21777.02 ms; the first step completed only after reliable Marketplace evidence. |
| FAIL | Accepted final take: actual HTTP 200, deterministic FAIL in 26423.54 ms, observed Preferences evidence and a supported correction, no progress. |
| UNCERTAIN | Accepted final take: actual HTTP 200, deterministic UNCERTAIN in 24670.27 ms because neither Search results nor Replay Formatter was established. The second step remained incomplete. |
| Corrections | Fresh FAIL showed the approved Marketplace correction with actual Preferences evidence; following it led to a new streamed observation and PASS. FAIL/PASS used validated local Meta grounded plans; UNCERTAIN used the labeled deterministic explanation template. Explanations did not change verdicts. |
| Real Meta inference | Fresh tutorial extraction produced a validated response from the exact local Meta alias, in addition to historical screen-request evidence. Direct Meta Model API remains unverified. |
| Local inference | Pinned CPU runtime and approximately 2.02 GB model are installed under ignored `.artifacts/local-meta/`. No NVIDIA GPU is needed. Native readiness is checked separately from actual model requests. |
| Physical camera verification | Omit from the main recording. Selected local Meta provider explicitly rejects physical/SAM verification. Physical fixtures are implemented and labeled; actual camera/SAM inference is unverified. |
| Evaluation dashboard | The 20-case **local OCR** evaluation was rerun in this task: 20/20 expected verdicts matched, no skipped cases. GET confirmed the fresh local rerun is displayed. The separate NVIDIA report still has **zero completed cases**. This dashboard is suitable with its visible scope labels. It does not currently measure local Llama accuracy. |

## Demonstration target selection

The existing CodeLab target is a functional interactive browser application with
an explicitly displayed simulation notice. It supports repeatable software-like
panel, search, details, and simulated install changes. Showing it is permitted by
the brief's alternative-workflow option, provided the recording calls it a
simulation and does not claim a real VS Code extension installation.

An actual application-window or browser-tab capture is preferable to uploading a
saved reference screenshot. The target window must remain separate from the
ReplayLab coach to avoid self-capture proving the coach's own instructions.
The verifier already abstains when it detects coach self-capture.

The prepared proposal named **Local Meta generated walkthrough** is left
unapproved for the owner. It contains a transcript reference, two generated steps,
and no video or extracted frames. Showing that project cannot be described as
live video understanding. Any new demonstration project is separate and must
have its own source, generation provenance, reviewed rules, and approval record.

The separate **Hackathon live demonstration** project now has the actual
CodeLab interaction tutorial, its timestamped transcript, four extracted source
frames, and reviewed Meta-generated graph. The first approved constraint will
expect the unique **Extensions Marketplace** content heading and treat the
tutorial-quoted **Preferences** heading as the known wrong destination. The
second will require both **Search results** and **Replay Formatter**. Always
visible sidebar navigation is not used to prove that a panel is active.

## Known limitations and unsuitable claims

- CPU inference is noticeable: the earlier full screen requests took 17.84–28.18 s;
  fresh video-frame/transcript extraction took 110.048 s. Waiting must remain
  visible at normal speed, and extraction must be labeled prepared.
- OCR may miss icons, small text, hidden controls, occluded content, and active
  selection. Llama cannot fill those gaps with invented observations.
- FAIL requires a specific observed mismatch. Missing expected text alone yields
  UNCERTAIN. A supported correction must lead to a fresh observation before PASS.
- Historical headless recording exposed a background-tab frame-delivery freeze.
  The fresh capture probe used a separate target browser context without video
  recording and verified actual changing frames. The complete fresh rehearsal
  then passed using real tab captures; stale frames were not replaced with files.
- The freshly rerun 20/20 dashboard score is a small developer-authored CodeLab OCR challenge,
  not an independent study or Meta-model accuracy measurement.
- NVIDIA Muse requests remained unresolved; the known local Meta route is used.
  Public hosting, direct Meta API access, SAM success, hackathon eligibility, and
  compliance with any specific model/API submission rule remain unverified.
- The final video captures one actual ReplayLab browser page continuously. The
  target appears through its genuine shared-tab preview. It does not record a
  human-operated Windows sharing picker or a third-party VS Code installation.

The latest corrected natural-speed rehearsal passed in **94.408 s**, leaving room for
readable narration/scene holds in a three-minute continuous take. It made three
actual screen submissions, observed **FAIL → correction → PASS → UNCERTAIN**,
recorded three fresh Meta observation response IDs, stopped the real stream, and
reported zero JavaScript errors and zero nonlocal browser hosts. The first step
was completed; the second intentionally remained pending. The final recording is
a separate accepted run with its own fresh requests and media validation.

An earlier rehearsal passed in 91.901 s and is retained separately; it predates
the reference-frame correction. The first continuous recording attempt passed its API/verdict checks and media
decode, but visual review found that the first reference frame showed the next
tutorial action. It was withheld as a **diagnostic take**, not published as the
final demonstration. The provider now prefers a source frame inside the step's
own interval before an action boundary; preparation copies retain the reviewed
reference timestamp. The 94.408-second corrected rehearsal passed after this
fix; its [safe report](validation/hackathon-rehearsal.json) records three fresh
Meta observation IDs and the same genuine verification loop. The final retake
was subsequently recorded and accepted separately. The diagnostic is retained
under ignored `.artifacts/`.

Post-change regression checks passed: **489 backend tests** in **54.93 s**,
then **53 frontend tests** in **9.52 s**, backend/helper Ruff, TypeScript, the Vite
production build, and Node script syntax. These checks include repeated-frame
OCR deduplication, both in-interval/fallback reference-frame selection, and a
pending-to-complete UI regression.

A second continuous take had correct reference frames, actual model responses,
and persisted progress of one out of two steps. Visual review still withheld it:
the sidebar incorrectly said **All checkpoints verified** while the final step
was pending. That 176.2-second take is retained as ignored `diagnostic-2.mp4`.
The sidebar now requires every step ID to be completed before showing that
message; a frontend test exercises pending and completed states. The verifier,
source material, and genuine capture path are unchanged. A fresh final retake
was recorded and accepted after this UI fix; the pending last-step message is
correct in the reviewed final output.

The accepted [recording report](validation/hackathon-recording.json) records
three fresh Meta observation responses, three screen submissions, a stopped
capture track, zero JavaScript errors/nonlocal browser hosts, and progress of
**one out of two steps**. FFprobe, full FFmpeg decode, actual Chromium playback,
and visual review of 14 sampled frames passed. No cuts, speed changes, response
substitution, or diagnostic footage were used in the final take.

The launcher now has a separate owner-ready prepared project, left
**unapproved with zero of two steps complete**. Its default readiness check
passed; using it does not silently approve model-proposed actions or claim a new
extraction.

See [verification evidence](DEMO_VERIFICATION.md), the
[recording script](DEMO_SCRIPT.md), and [setup instructions](DEMO_SETUP.md).
Safe raw evidence: [preparation and original proposal](validation/hackathon-preparation.json),
[latest rehearsal](validation/hackathon-rehearsal.json), and
[fresh local OCR evaluation](validation/hackathon-digital-evaluation.json).
The [accepted final recording report](validation/hackathon-recording.json)
contains its actual case evidence, timings, and media acceptance.
