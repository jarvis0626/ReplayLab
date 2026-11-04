# Tutorial to verified action

[Watch the actual tutorial demonstration](../ReplayLab_Meta_Hackathon_Demo.mp4):
**45.633 seconds**, 1920 x 1080, H.264 at 30 FPS, with a timed neural voiceover.
The recording and narrated file both passed validation. It starts directly with
the tutorial upload, without a dashboard introduction or spoken voice disclaimer.

The take starts inside an empty project and shows **actual tutorial upload and
playback, live Meta workflow generation, visible review and approval, real tab
sharing, PASS, and completed graph progress**. The workflow is generated during
this take, rather than opened from a previously prepared graph.

## Actual timeline

| Elapsed time | Visible application action |
| --- | --- |
| 1.147 s | Upload a real tutorial to the empty project |
| 5.947 s | Play the actual tutorial showing the Marketplace action |
| 12.490 s | Generate task steps now - actual local Meta request |
| 20.724 s | The model-generated workflow appears from this uploaded tutorial |
| 22.313 s | Review the model's source-quoted positive heading before approval |
| 22.977 s | tutorial-followed: inspect the actual shared target |
| 37.705 s | tutorial-followed: actual PASS with observed evidence |
| 42.686 s | The uploaded tutorial checkpoint is now verified complete |

Live workflow extraction took **6.605 s** overall,
including **6347.066 ms** for the actual Meta response.
The real screen check returned PASS in **14600.90 ms**,
including capture scheduling, OCR, model reasoning, and verification. The only
step became complete; manual navigation did not establish completion.

- Workflow response: `chatcmpl-liaWTGZoxc2AtIwYBZ1ka34AGxYQuoAl`.
- Screen observation response: `chatcmpl-c8OuzeObobH3C4tbUOtYpH1lgRgbNFPH`.
- Requested and returned model: `meta-llama/Llama-3.2-1B-Instruct`.
- Uploaded tutorial: **9.12 s**, producing **four extracted source frames**.
- This one-goal tutorial used **one representative OCR frame** for inference;
  provenance records one used frame and four available frames.
- The original model proposal and reviewed task were unchanged:
  `review_saved_changes=false`. Its source-quoted **Extensions Marketplace**
  expected label, title, rule, and expected state were preserved. No replacement
  expected state or requested verdict was injected.
- One real shared-tab submission, zero JavaScript errors, and zero nonlocal
  browser hosts were recorded. The capture track was stopped at the end.

## What the pipeline uses

**Meta Llama 3.2 1B Instruct** runs locally with the AMD Vulkan profile. Local OCR
reads source frames and shared-screen pixels; Meta receives redacted text and
the supplied transcript. Deterministic rules decide whether the observed heading
satisfies the approved checkpoint. Positive initial proposals do not invent
alternative labels or counterstates; those require explicit review.

CodeLab is visibly labeled as an interactive simulation. This is one controlled
practice workflow, without a third-party extension installation or evidence of
accuracy across arbitrary software. Chromium's source-selection test flag
chooses a real tab stream after the application's share gesture. A human
operating-system permission picker is not claimed.

## Narration

The narrated file uses **en-US-GuyNeural**. It uses Microsoft Edge online speech
for the approved narration text only, without application screenshots, videos,
model media, or credentials. Synthetic speech is identified in MP4 metadata and
this documentation. There is no spoken synthetic-voice disclaimer or dashboard
introduction before the actual tutorial demonstration.

Narration is added after capture. The mux helper copies H.264 video packets and
timestamps, verifies matching source/output hashes, and checks complete decoding
and audio levels. Each spoken segment must fit its assigned real-time window.
No scene stitching, speed change, response replacement, or artificial waiting is
used. Original footage and earlier failed takes stay under ignored `.artifacts/`.

## Accepted media and evidence

| Check | Actual result |
| --- | --- |
| Video | 45.633333 s; 1920 x 1080; H.264; 30 FPS; 1,369 frames |
| Audio | en-US-GuyNeural synthetic narration; AAC mono, 48 kHz |
| Speech timing | Four measured segments fit their recorded scene windows |
| Full decode | Passed for the complete narrated file |
| Browser playback | Advanced to 1.686049 s with 34,102 audio bytes and 290,743 video bytes decoded; no error |
| Visual review | Seven actual video frames reviewed; tutorial input, live generation, proposed rule, PASS evidence, and completion confirmed |
| Video preservation | Source/output encoded-packet and timestamp hashes match |
| Audio levels | Mean -19.1 dBFS; peak -1.4 dBFS; no full-scale clipping |
| Final file | 3,233,185 bytes; SHA256 `5acbbbf822566aa51c829fb42e41d7038b43e793ba8f660e5446cc134ed13441` |

The unchanged video-packet SHA256 is
`812a5c20b249b011dc957fc2fcaaa563236cdae25dca6c5331c7edd86c7d9af1`.
The unchanged timestamp SHA256 is
`932f6497f64461ba6d3cf5ba232f8add57de4b5f8e0ad4117b1eeb1b112d2842`.
The [recording report](validation/tutorial-proof-recording.json),
[voiceover report](validation/tutorial-proof-voiceover.json), and
[exact spoken plan](tutorial-proof-narration.json) preserve the actual evidence.
Earlier failed candidates remain separate and were not stitched into this take.

## Reproduce

The separate system Python installation contains Playwright. With the local
application and exact Meta model running:

```powershell
python scripts/record_tutorial_proof.py --tutorial-video .artifacts/tutorial-proof-source/Open-Extensions-Marketplace-tutorial.mp4 --model meta-llama/Llama-3.2-1B-Instruct --name "Hackathon live demonstration - fresh tutorial proof" --checks pass
```

The helper creates a new project for this run. It rejects a wrong model-proposed
heading or unexpected verdict and retains failed candidates instead of publishing
them as successful recordings. It leaves existing owner projects alone.

After reviewing a successful candidate, use its source SHA256, duration, and
measured chapter windows in the narration plan:

```powershell
python scripts/narrate_tutorial_proof.py --source .artifacts/<successful-run>/tutorial-proof.mp4 --plan docs/tutorial-proof-narration.json
```

Install the optional pinned speech client only under ignored repository artifacts
if it is unavailable:

```powershell
python -m pip install --target .artifacts/tts-client edge-tts==7.3.1
```

The previous main MP4 is backed up before a validated narrated candidate replaces
it. The helper writes `docs/validation/tutorial-proof-voiceover.json` only after
its actual checks pass.
