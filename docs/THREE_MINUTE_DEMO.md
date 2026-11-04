# Three-minute tutorial to verified action

[Watch the full narrated demonstration](../ReplayLab_Meta_Hackathon_Demo.mp4):
**179.066667 seconds (2:59.07)**, 1920 x 1080, H.264 at 30 FPS, 5,372 frames.
The continuous recording and narrated file both passed full media decoding.
All twelve natural-voice segments fit their measured scene windows.

The take starts directly inside an empty tutorial project. It shows the full
uploaded tutorial, newly generated Meta workflow, visible review and approval,
actual shared-tab verification, measured evaluation, and the configured model.
There is no opening dashboard tour or spoken voice disclaimer.

## Actual timeline

| Elapsed time | Recorded application action |
| --- | --- |
| 1.276 s | Upload a real tutorial to the empty project |
| 8.334 s | Play the actual tutorial showing the Marketplace action |
| 20.150 s | Generate task steps now - actual local Meta request |
| 35.333 s | The model-generated workflow appears from this uploaded tutorial |
| 42.359 s | Review the model's source-quoted positive heading before approval |
| 55.045 s | wrong-settings: inspect the actual shared target |
| 62.994 s | wrong-settings: actual FAIL with observed evidence |
| 87.317 s | corrected-marketplace: inspect the actual shared target |
| 95.523 s | corrected-marketplace: actual PASS with observed evidence |
| 114.302 s | ambiguous-new-view: inspect the actual shared target |
| 127.720 s | ambiguous-new-view: actual UNCERTAIN with observed evidence |
| 140.734 s | Measured local OCR evaluation with explicit dataset and sample size |
| 158.504 s | Actual Meta model and local OCR/text boundary |
| 164.717 s | The uploaded tutorial checkpoint is now verified complete |

The **9.12-second tutorial plays to its end**, completing at **17.472 s**.
It produces four extracted source frames. This single-goal workflow uses one
representative OCR frame plus the supplied timestamped transcript; provenance
records both the used and available frame counts.

Live task extraction takes **9.478 s** overall, including **9,215.472 ms** for
the actual Meta response. Its request ID is
`chatcmpl-Lxo13DJrI9CkzKCDbc3kHcz6CNZB0hon`.
Requested and returned model are **`meta-llama/Llama-3.2-1B-Instruct`**.

The model's actual **Extensions Marketplace** positive goal is retained.
Through visible task editing, the reviewer adds **Preferences** as known
contradictory text, then saves and approves the task. This addition is not
attributed to model extraction or quoted as source tutorial content.

| Actual outcome | Capture/check elapsed time | Validated Meta observation response |
| --- | --- | --- |
| FAIL | 7813.65 ms | `chatcmpl-MMHghza74zTL9s7iWcEi3klTZFY6lWCX` |
| PASS | 7954.96 ms | `chatcmpl-BlgJRRYnpCVvcY5JJztNFRHQ9L5RCcSs` |
| UNCERTAIN | 13221.67 ms | `chatcmpl-lpQkr83tjsV0E5d4SQynuk3uMdPFH9G1` |

All three requests use actual shared-tab screenshots and return distinct,
validated, uncached local Meta responses. The browser reports no JavaScript
errors or nonlocal browser hosts. Sharing is stopped and the captured track
ends. These elapsed times include the UI/capture pipeline and are separate
from provider-only inference latency.

The source tutorial has one checkpoint. FAIL supplies visible Preferences
counterevidence and a correction. PASS supplies the expected Marketplace
heading and completes the checkpoint. Explorer then produces UNCERTAIN for
that new observation; the earlier proven completion remains in the history.
No pending second checkpoint is claimed, and navigation alone never marks
progress complete.

## Pipeline and measured scope

**Meta Llama 3.2 1B Instruct** runs locally with the pinned AMD Vulkan profile.
Local OCR reads actual tutorial frames and shared-screen pixels; Meta receives
redacted text and the supplied transcript. Deterministic rules decide PASS,
FAIL, or UNCERTAIN. This pipeline does not claim that the text model sees images.
Built with Llama.

CodeLab is visibly labeled as an interactive simulation. The demonstration does
not install a third-party extension. Chromium's test source selector chooses a
real tab stream after the application share gesture; it is not evidence of a
human-operated permission picker.

The dashboard shows the separately measured **20-case local OCR dataset**:
20/20 matching labels, 0% false certainty, and 100% uncertainty recall; measured
median latency is 3,575.15 ms and p95 is 5,204.44 ms. Those controlled CodeLab
results are separate from the three fresh Meta-backed checks in this take.
They do not establish broad software understanding or general model accuracy.

## Narration and media evidence

Natural **en-US-GuyNeural** narration was added after capture, at normal rate.
Only narration text went to online speech. Synthetic voice is identified in
metadata and docs. The mux preserved the original encoded video packets, their
timestamps, frame count, and duration. There are no internal cuts, frame
replacements, speed changes, or added padding.

| Final media check | Actual result |
| --- | --- |
| Duration | 179.066667 s, within the 175-180-second acceptance window |
| Video | H.264, 1920 x 1080, 30 FPS, 5,372 frames |
| Audio | AAC mono, 48 kHz; en-US-GuyNeural synthetic narration |
| Speech | All 12 measured segments fit their scene windows at normal rate |
| Full decode | Passed for the complete narrated audio/video file |
| Browser playback | Advanced to 1.526982 s with 28,559 audio bytes and 226,667 video bytes decoded; no error; seek to 177 s then played to the 179.066667 s end |
| Video preservation | Source/output encoded-packet and timestamp SHA256 values match |
| Audio levels | Mean -18.4 dBFS; peak -1.4 dBFS |
| Final file | 9,375,600 bytes; SHA256 `02581dce6ffff35b0fd878d790acf2f667f90c03e052ecba59add96e4a27efed` |

The unchanged video-packet SHA256 is
`53b502b49a96cf7f7b3898c1ae5085cd14c9f170da3e45333a4fab1252d90907`.
The unchanged timestamp SHA256 is
`8c1988529f842cea606252954aeab8473fa926d476eff781126a8dbf2aa8fcf5`.

The accepted silent source is **6,467,980 bytes**, SHA256
`ed1af783c2078b851e73fccfb9750042862afd49340191df31e595d5a430cf21`.
Its native browser take is 179.08 seconds; the constant-frame-rate H.264 output
is 179.066667 seconds without trimming or padding.

- [Actual recording report](validation/three-minute-tutorial-recording.json)
- [Successful voiceover report](validation/three-minute-tutorial-voiceover.json)
- [Exact timed narration plan](three-minute-narration.json)
- [Spoken script](DEMO_SCRIPT.md)

The earlier [short tutorial proof](TUTORIAL_PROOF.md) and
[prepared-workflow demonstration](PREPARED_DEMO_SCRIPT.md) retain their separate
scope and evidence. They are not substituted for this full-length take.

## Reproduce

With the current local application and exact model running:

```powershell
python scripts/record_three_minute_tutorial.py --tutorial-video .artifacts/tutorial-proof-source/Open-Extensions-Marketplace-tutorial.mp4 --model meta-llama/Llama-3.2-1B-Instruct
```

The recorder creates a separate empty project and leaves owner projects alone.
Failed candidates stay under ignored `.artifacts/` without replacing the main
video. A successful take must fit 175-180 seconds, contain the expected real
outcomes and three distinct validated Meta response IDs, play the tutorial to
its end, share a genuine tab, stop sharing, and retain qualified progress.

For a newly reviewed candidate, update the narration plan's source hash,
duration, and scene windows before running:

```powershell
python scripts/narrate_tutorial_proof.py --source .artifacts/<successful-run>/three-minute-tutorial.mp4 --plan docs/three-minute-narration.json --report docs/validation/three-minute-tutorial-voiceover.json
```

The speech client is the optional pinned `edge-tts==7.3.1` under ignored
`.artifacts/tts-client`. Full audio/video decoding, matching source/output
video-packet and timestamp hashes, measured audio levels, and browser playback
must pass before accepting a newly recorded narrated replacement.
