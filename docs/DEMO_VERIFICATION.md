# Live demonstration verification

**4 November current three-minute demonstration:** [2:59.07 video](../ReplayLab_Meta_Hackathon_Demo.mp4)
shows the full tutorial, fresh Meta generation, visible review/approval, real
shared-screen FAIL, correction, PASS and UNCERTAIN, evaluation and completed graph.
Meta Llama 3.2 1B runs on AMD Vulkan, with natural GuyNeural narration and no spoken
preamble. [Accepted recording and audio evidence](THREE_MINUTE_DEMO.md).
The earlier prepared-workflow measurements below remain historical. The separate
[short proof](TUTORIAL_PROOF.md) is archived; neither is the current main video.

**Accepted final artifact:**
[ReplayLab_Meta_Hackathon_Demo.mp4](assets/prepared-workflow-demo.mp4),
**176.4 seconds**, one continuous actual application take. Its
[safe recording report](validation/hackathon-recording.json) contains actual
requests, verdicts, provenance, timings, and acceptance checks. Historical
rehearsals and withheld takes are distinguished below.

Audit date: **3 November 2026 (Asia/Calcutta)**. Safe metadata only is recorded
here. Credentials, runtime databases, personal desktop content, and uploaded
private media are excluded.

## Read-only checks in this task

The checks below called the running API without changing provider selection,
approving an existing project, or generating model traffic.

| Check | Actual result |
| --- | --- |
| `GET /api/health` | HTTP 200; selected provider `local_meta`; model `meta-llama/Llama-3.2-3B-Instruct`. Immediately after startup, `live_verified` was false, correctly reflecting that no validated call had yet completed in that server instance. |
| Existing generated workflow | HTTP 200; project **Local Meta generated walkthrough**; ready, digital, unapproved, two steps, no video/frames. It was not modified. |
| Existing generated workflow graph | HTTP 200; two nodes, one dependency edge. |
| `GET /api/evaluation/digital` | HTTP 200; `provider_mode=local_ocr`; checked-in measurement dated 28 October; 20 completed/20 target, 20 expected verdicts matched. |
| `GET /api/evaluation/nvidia` | HTTP 200; separate checked-in NVIDIA report dated 2 November; 2 attempts, 0 completed/20 target, `live_api_verified=false`, accuracy/uncertainty/latency metrics null. |

The first startup probes for the UI, API health, and model health encountered
connection errors while services were starting. Later API reads succeeded.
These transient failures are retained here rather than being described as
successful initial checks. The launcher and final rehearsal perform their own
complete readiness checks.

## Fresh source and Meta extraction

Prepared a new project named **Hackathon live demonstration**, separate from the
owner's existing unapproved walkthrough. The source is a **14.92-second**
continuous browser recording of real interactions with the visibly labeled
CodeLab simulation. It shows opening Extensions Marketplace and searching for
Replay Formatter; it does not install third-party software. Its timestamped
transcript was supplied with confirmed usage rights.

- Actual source upload and media processing produced **four source frames**.
- Source MP4 SHA256:
  `697c3bcfbc4181daeaa6ceb959548fa7bd96b1534f5f45064f88f635de392110`.
- Successful extraction used actual local frame OCR and the supplied transcript;
  validated model alias: `meta-llama/Llama-3.2-3B-Instruct`.
- Actual response ID: `chatcmpl-QEzCvU71OXmu5GqBbWQyxOl9LsLORCvg`.
- Model-reported request time: **110047.619 ms**; recorded rounded duration
  **110.048 s**. No cloud inference or image-pixel input to Llama is claimed.
- Two earlier extraction attempts failed: the first exceeded its 120-second
  timeout; the second was interrupted by server reload. They are retained as
  failed attempts, not successful results or model UNCERTAIN verdicts.

The successful model returned **five proposed steps**, including duplicated or
incidental text from frame OCR. The owner-authorized coding agent reviewed the
proposal and retained the **two intended tutorial actions**. Review removed
navigation-only alternatives and replaced the always-visible Settings
contradiction with the transcript-quoted content heading **Preferences**. The
second step now requires both **Search results** and **Replay Formatter**.
No verifier outcome was hardcoded and the deterministic engine was not changed
to force a demonstration verdict.

The task records `user_edited=true` and `provenance.demo_review`, including
original proposal SHA256
`1225956930bc4dbe943410bb2f9b7ad888f634a91bf1586e32b36b3a5545e9f6`,
five original steps, two retained steps, and review changes. It was left
unapproved after preparation; the guided rehearsal/recording performs approval
as a visible action. This is **reviewed Meta-generated output**, not an untouched
two-step model response. Preparation occurs before recording and must be labeled
accordingly in the video.

The [safe preparation report](validation/hackathon-preparation.json) retains the
original five-step model output as well as the full review chain and final
prepared task. It is not limited to the edited two-step result.

## Fresh genuine capture probe

The recorder's separate native 1920×1080 coach-window probe obtained an actual
`getDisplayMedia()` browser-tab stream reporting **1728×1080** source dimensions.
Changing the actual target between Settings and Extensions produced different
captured frame content. A separate target browser context without its own
recording avoided the prior stale-frame behavior in this probe. Chromium's
test-only source-selection flag selected the owned CodeLab tab after the explicit
share action; the browser media API was not stubbed. This does not test a
human-operated OS permission picker.

The probe did not perform application API inference and is not evidence of a
successful full verification loop. Actual stream-driven FAIL, correction, PASS,
and UNCERTAIN must be recorded in the separate complete rehearsal.

## Historical actual inference evidence

These completed measurements establish the existing implementation baseline.
They are kept separate from fresh final-demo results.

| Executed check | Actual sample and outcome | Evidence |
| --- | --- | --- |
| Local Meta browser checks, 2 November | 2 controlled screenshot submissions, 12 assertions; actual PASS then FAIL on separate approved CodeLab templates; zero JavaScript errors/nonlocal browser hosts. | [Raw browser report](assets/local-meta/browser-validation.json) |
| Actual Meta workflow proposal, 2 November | 1 authored timestamped transcript; 2-step proposal in 44.14 s, no invented interface version, remained unapproved; preapproval verification returned HTTP 409. | [Workflow report](validation/local-meta-workflow.json) |
| Earlier local Meta recording | 87.88 s uncut silent browser video; real CPU inference, normal-speed waiting, PASS/FAIL screenshots. It does not show a full stream-driven mistake/correction/uncertainty loop. | [Recording report](assets/local-meta/demo-recording.json), [video](assets/local-meta/demo.mp4) |
| OCR-only live-tab walkthrough, 28 October | 7 actual OCR decisions: PASS, FAIL, PASS, UNCERTAIN, UNCERTAIN, PASS, PASS. First four came from real tab capture; later three used explicitly disclosed manual screenshot review after a headless background-frame issue. No live Meta claim. | [V3 report](assets/v3/demo-validation.json), [scope](v3-demo.md) |

The older 87.88-second and 180-second recordings are preserved. Neither is renamed
as the requested new final recording.

## Fresh evaluation and dashboard verification

Executed `.venv\Scripts\python.exe scripts/evaluate-digital.py` in this task;
exit code **0**. The new report was measured at **3 November 2026, 19:19:35 IST**
(`2026-11-03T13:49:35.294926+00:00`). All 20 frozen screenshot hashes matched;
all cases completed, with no skipped cases. A subsequent API read confirmed
`report_source=local_rerun` and the new timestamp. The checked-in historical
baseline was not overwritten. The runtime report is
`apps/api/data/evaluation/digital-latest.json` (ignored runtime data).
A [safe report snapshot](validation/hackathon-digital-evaluation.json) preserves
the actual per-case results and timing for review.

The dashboard's selected **Digital screen captures** suite reads these actual
executed measurements from the controlled local OCR dataset. Its visible badge
says **LOCAL OCR · CAPTURED BROWSER PIXELS**. The live-demo provider may be local
Meta, but that does not change the suite's identity.

| Metric | Actual value | Denominator |
| --- | --- | --- |
| Three-class agreement | 20/20 (100%) | 20 completed controlled captures |
| Decisive accuracy | 10/10 (100%) | PASS/FAIL predictions |
| False certainty | 0/10 (0%) | Ground-truth UNCERTAIN cases |
| Uncertainty recall | 10/10 (100%) | Ground-truth UNCERTAIN cases |
| Median/p95 processing time | 3575.15 / 5204.44 ms | 20 local OCR submissions |

The confusion matrix contains 5 correct PASS, 5 correct FAIL, and 10 correct
UNCERTAIN predictions, with zero off-diagonal entries and zero PASS/FAIL swaps.
The evaluation ran while separate tutorial extraction was using the CPU;
latency reflects that actual concurrent workload. These times exclude capture,
upload transport, and user actions, and are not local Llama inference latency.

These labels were authored by the implementing coding agent before inference.
They are not independently reviewed annotations. The result does not establish
broad software support, Meta-model accuracy, calibrated OCR probabilities, or
performance on unseen tutorials. The separate NVIDIA suite correctly has unknown
metrics because it has no completed inference cases.

## Offline regression baseline

The last published local Meta milestone passed **486 backend tests**, **52
frontend tests**, Ruff, TypeScript, the Vite production build, and GitHub Actions
for commit `0c39b197eaba36a51e43fe5fe32df74347085d61`. Many provider contract tests
use mocked HTTP transports; these totals are implementation checks, not hundreds
of actual model inferences. New checks for this demonstration are reported
separately after execution.

A targeted provider run after the repeated-frame-OCR input deduplication change
passed **55 local provider tests**. A subsequent full post-change run passed
**489 backend tests in 54.93 s** and **52 frontend tests in 11.75 s**, plus Ruff,
TypeScript, the Vite production build, helper-script Ruff, and Node script syntax.
The three added provider regressions cover repeated OCR evidence deduplication,
selecting a reference inside its step interval rather than the next action, and
the nearest-frame fallback when no frame falls inside the interval. Model
transports in these contract tests are mocked; the counts are not actual live
model-call counts.

After visual review identified the final-step completion-copy issue described
below, an additional frontend regression was added. The updated suite passed
**53 tests in 9.52 s**, and TypeScript plus the Vite production build passed.
The backend implementation and its 489-test result were unchanged by this UI
fix. This is the latest frontend count; the 52-test count above records the
earlier complete check rather than an additional current suite.

## Corrected pre-recording rehearsal

The latest corrected complete rehearsal **passed** in **94.408 s**. It ran the actual app
using the newly prepared, reviewed Meta-generated workflow. The run approved
that separate demonstration project, started a genuine target-tab stream,
submitted three actual screen checks, displayed the evaluation and provider,
and finished on the working graph. It did not record an MP4 (`recorded=false`).

| Actual target state | HTTP / verdict | Full screen-request time | Progress |
| --- | --- | --- | --- |
| Intentional Settings mistake, Preferences heading visible | 200 / FAIL | 24033.83 ms | No completed steps |
| Follow correction to Extensions Marketplace | 200 / PASS | 17825.37 ms | First step completed |
| Unrelated Explorer view during search checkpoint | 200 / UNCERTAIN | 13570.11 ms | First step only; second remained pending |

The FAIL evidence included **Preferences** at OCR confidence 0.97 and the
supported correction to return to Extensions Marketplace. The corrected capture
reliably observed **Extensions Marketplace** at confidence 1.00. The unrelated
view supplied neither **Search results** nor **Replay Formatter**, producing
UNCERTAIN instead of inventing a mismatch or completion.

All three observations recorded actual local OCR (`real_ocr=true`,
`fixture=false`, `cache_hit=false`), exact requested and returned Meta model
aliases, validated successful response provenance, `local_only=true`, and
`vision_inference=false`. Three fresh observation response IDs were recorded:

- FAIL: `chatcmpl-52htQ5zfCWXI8r1ECAmoBs6ji38edYN4`.
- PASS: `chatcmpl-AEdfbBAfx6by35Jb8zzGRKMUkaTj8qoH`.
- UNCERTAIN: `chatcmpl-XHJh6JN1StMm4Y9feQjLvTbTaRaN2ph4`.

FAIL and PASS explanations used `local_meta_grounded_plan`; UNCERTAIN used
`deterministic_template`. These labels are preserved rather than describing all
three explanations as model-generated. Three fresh observation calls do not
establish an exact total of underlying explanation calls, because explanation
cache use is a separate mechanism.

The recorded source scope was **browser tab**, with a live 1728×1080 stream at
5 FPS from the real media API. At finish, `stream_stopped=true`; there were
**zero JavaScript errors**, **zero nonlocal browser hosts**, and exactly
**three screen submissions**. The evaluation shown matched the fresh 20-case
local OCR report, with its distinct scope. The second task step remained
unverified, honestly showing incomplete progress.

The latest rehearsal report was written under ignored
`.artifacts/hackathon-demo-20261103T140513Z/rehearsal.json`; its
[safe checked-in snapshot](validation/hackathon-rehearsal.json) contains the
actual provenance and measured results. No human OS permission-picker test or
actual VS Code installation is claimed.

The earlier rehearsal at
`.artifacts/hackathon-demo-20261103T135650Z/rehearsal.json` passed in **91.901 s**,
before the reference-frame correction. Its screen timings were 21959.20 ms FAIL,
16689.03 ms PASS, and 14089.87 ms UNCERTAIN. It remains separate historical
evidence; the table and request IDs above belong to the later corrected run.

## Withheld diagnostic take and reference-frame fix

The first actual continuous recording attempt completed its real three-case
verification loop and automated media checks. FFprobe reported **176.666667 s**,
**1920×1080**, **30 FPS**, **H.264**, **5300 frames**, and **5736381 bytes**;
full FFmpeg decode passed. Those facts establish a playable diagnostic recording,
not acceptance as the final video.

Manual visual review found that the first step's reference frame showed a later
search action instead of the expected Marketplace view. The recording was
withheld and moved to ignored
`.artifacts/hackathon-demo-20261103T135934Z/diagnostic.mp4`; its original
`recording.json` is retained beside it. Its automated `success=true` describes
API/verdict assertions and must not be mistaken for final editorial acceptance.
It is not spliced into a later video, and its output-name metadata is historical.

The general provider bug was that selecting the frame nearest a step's end
could choose pixels from the next action. Selection now first considers frames
inside `[timestamp_start, timestamp_end)` and chooses one near the step midpoint;
only an empty interval falls back to the nearest end frame. Two regression tests
cover these cases. Copying the prepared task into a recording project now
preserves the reviewed source-frame timestamp. The first expected Marketplace
reference is **2.984 s**, before the next action. This fixes source attribution
without changing deterministic verification rules or forcing verdicts.

The 94.408-second corrected rehearsal above passed after this correction with
the intended source reference preserved.

## Second withheld take and completion-copy fix

A second uncut take completed the actual three-case loop with correct source
references, three distinct fresh Meta observation responses, and persisted
progress of only the first step. Its media validation passed: **176.2 s**,
**1920×1080**, **H.264**, **30 FPS**, **5286 frames**, **5703700 bytes**, no audio,
and full FFmpeg decode. It was still withheld during visual review because the
sidebar said **All checkpoints verified** while the last step was pending.
That UI copy was false even though the API verdicts and persisted progress were
correct. The take is retained as ignored
`.artifacts/hackathon-demo-20261103T140801Z/diagnostic-2.mp4`, with its actual
`recording.json`; it is not the accepted final video.

The frontend now derives completion from **every task step ID being present in
completed progress**, instead of the absence of another upcoming step. A new
regression checks that a last pending step does not display completed-workflow
copy and that the copy appears only after completion. The updated 53-test
frontend suite, TypeScript, and Vite build passed. This change does not alter
the verifier, model behavior, source material, or stream capture. The earlier
94.408-second full rehearsal still documents those unchanged paths. The final
retake below independently showed the corrected UI and was accepted.

## Accepted final continuous take

The final take is **176.4 s (2:56.4)**, within the three-minute limit. It captures
one actual ReplayLab browser page continuously; the separate functional CodeLab
target appears through the genuine shared-tab stream. It preserves actual
waiting and interactions at natural speed. There are no stitched scenes,
speedups, response replacements, fake visual observations, or footage from the
two withheld diagnostics.

The final run approved its own prepared reviewed workflow, then executed:

| Actual target state | Actual HTTP / verdict | Full request time | Result visible in take |
| --- | --- | --- | --- |
| Intentional Settings/Preferences mistake | 200 / FAIL | 26423.54 ms | 1:09.597; no progress, observed mismatch and correction |
| Corrected Extensions Marketplace | 200 / PASS | 21777.02 ms | 1:43.292; first step completed |
| Unrelated Explorer during search step | 200 / UNCERTAIN | 24670.27 ms | 2:18.160; second step remained incomplete |

All three observations have `cache_hit=false`, `fixture=false`, actual local
OCR, the exact local Meta requested/returned model alias, validated response
provenance, `local_only=true`, and `vision_inference=false`. Actual fresh
observation response IDs:

- FAIL: `chatcmpl-mmAXFtlxnrrBBUsRTlaKmp8eE55ebOWH`.
- PASS: `chatcmpl-YubLa4nPbgzJ8RxU9UNRFlGQCAknaNPq`.
- UNCERTAIN: `chatcmpl-CaZ9742E7KzhlvHnnTJSjBdWNUSPiSXA`.

These are **three fresh Meta observation requests**. FAIL/PASS explanations use
`local_meta_grounded_plan`, which may reuse a validated explanation cache entry;
UNCERTAIN uses `deterministic_template`. The exact number of fresh underlying
explanation-model requests is unknown and is not presented as three.

The actual browser stream was 1728×1080 at 5 FPS and was ended at finish. The
recording encodes the page at 30 FPS without changing inference timing. The
report records exactly three screen submissions, zero JavaScript errors, zero
nonlocal browser hosts, and persisted progress of **one out of two steps**.
The final pending-step UI says **Verify this checkpoint to finish** rather than
claiming that all checkpoints are verified.

| Media acceptance check | Actual result |
| --- | --- |
| File | `ReplayLab_Meta_Hackathon_Demo.mp4` exists in the repository root |
| FFprobe | 176.400000 s; 1920×1080; H.264; 30/1 FPS; 5292 frames; 8714072 bytes |
| Audio | AAC, 48 kHz, mono; owner-authorized synthetic Windows narration added afterwards, disclosed at the start. See [spoken script](DEMO_SCRIPT.md). |
| Full FFmpeg decode | Passed over the complete video |
| Actual Chromium playback | Narrated MP4: duration 176.4 s; advanced to 1.737554 s; audio 34779 bytes and video 236087 bytes decoded; `error=null` |
| Visual review | Fourteen actual final MP4 frames inspected at 1, 18, 36, 70, 75, 90, 104, 109, 134, 139, 141, 150, 161, and 174 s; expected references, evidence, pending-step copy, readability, and provider disclosure checked |
| Privacy review | No visible credentials or personal desktop content in the reviewed samples; recording scope is the owned browser page/target stream |
| SHA256 | `b7fddbaa85c3c4657b9ca8db323d08e407cf1c4d4cbb2ddb591fbb9ff2605a4a` |

The safe [final recording report](validation/hackathon-recording.json) marks
`acceptance.accepted=true` and `single_take=true`. Raw recordings, failed
attempts, intermediate conversion files, and review frames remain under ignored
`.artifacts/`. The original model proposal, full review chain, corrected
rehearsal, and actual OCR evaluation are preserved in the other three linked
safe reports. No hackathon eligibility, Meta hosted vision/SAM success, human
OS-picker test, or real VS Code extension installation is inferred from this
video.

After recording, a separate owner-ready copy of the prepared workflow was left
unapproved with zero of two steps complete. The default launcher verified the
UI, API, local model, prepared project, and `live_verified=true`. This prepared
copy reuses the genuinely generated and reviewed task; it does not represent a
new model extraction or silently approve the owner's practice session.

## Synthetic narration update

At the owner's request, eleven timed narration segments were added after the
accepted recording using the installed **Microsoft Zira Desktop** Windows voice
at its normal rate. The opening sentence explicitly identifies synthetic
narration added afterward. This is a voiceover, not recorded live microphone
audio or generated model speech. The exact text/windows are in
[demo-narration.json](demo-narration.json).

Every synthesized sentence fits its assigned real-time window. FAIL narration
starts at 70.3 s, PASS at 104.0 s, and UNCERTAIN at 138.7 s, all after their actual
recorded results. No speech is sped up, and no inference waiting is removed.

FFmpeg copied the H.264 video stream without re-encoding, trimming or changing
timestamps. Source and output video-packet SHA256 are identical:
`9fa18912d5fdfd5ed89954030c31315d95fa31bcda7dbbd5eb458ad719d28dde`.
The original silent capture remains backed up under ignored `.artifacts/` and
its original metadata is retained in the accepted recording report.

The narrated output remains 176.4 s with 5,292 video frames and adds AAC mono
48 kHz audio. Full audio/video decode and real Chromium playback passed.
Measured audio mean is -17.8 dBFS and peak is -1.4 dBFS, with no clipping.
All speech was synthesized locally with zero cloud requests. See the
[actual voiceover validation report](validation/hackathon-voiceover.json).
