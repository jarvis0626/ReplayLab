# Actual browser QA and recorded demonstration

On 26 October 2026, the local application passed **19 browser assertion groups**
using real headless Chromium against the running Vite and FastAPI servers. No
Playwright network interception or fabricated browser responses were used. There
were **zero JavaScript page errors**. These checks used explicit **MOCK MODE**;
they do not establish live Meta account access or model accuracy.

The repeatable script is [scripts/browser-smoke.py](../scripts/browser-smoke.py).
The final successful command was `python scripts/browser-smoke.py --record`.

## Verified interactions

| Workflow | Actual result |
| --- | --- |
| Dashboard and new-project dialog | Project created through the UI |
| Video upload | Real generated MP4 bytes sent through the file input; four source frames extracted |
| Mock extraction | Returned proposal explicitly recorded `inferred_from_video:false` |
| MP4 playback | Browser loaded 960 x 640 video metadata, duration 8 seconds, and advanced playback time |
| Task graph | Four graph nodes rendered; second node selected; instruction edited, saved, and approved through the UI |
| First checkpoint | PASS |
| Blue block to the right, on checkpoint two | FAIL on the alignment rule; other supported rules remained visible |
| Obstructed camera view | UNCERTAIN on all four current rules |
| Corrected second checkpoint | PASS |
| Third and final checkpoints | PASS; progress visibly reached 4 / 4 |
| Evaluation page | Rendered 25 scenario rows and the expected/predicted confusion matrix |
| Synthetic camera | Chromium's actual `fake_device` stream previewed and was captured/uploaded through canvas and multipart handling; unknown pixels returned UNCERTAIN |

The synthetic camera is a browser-generated test stream, not a physical webcam or
model observation. It tests the capture-to-upload integration. The known fixture
verdicts test the approved rules against supplied observations; their filenames
do not choose the verdict. [Evaluation scope](evaluation.md) explains the
separate 25-case curated observation measurement.

Desktop checks used a **1440 x 1000** viewport; tablet checks used **1024 x 1000**.
The document/body width equaled the viewport on desktop dashboard, graph, and
evaluation, plus tablet dashboard, graph, practice, and evaluation. No horizontal
page overflow was observed on those screens. These are two tested viewport sizes,
not exhaustive browser/device coverage.

Two temporary upload/camera projects created by the final run were deleted
successfully through the API. A completed showcase sample was retained in the
local test workspace; runtime project data is not part of the repository.

## Actual artifacts

The [silent browser recording](assets/demo.mp4) shows the working mock walkthrough
at normal speed. It is an actual screen capture, not stock footage or a rendered
prototype. Its first 180 seconds were retained without padding to meet a strict
three-minute limit. Narration is supplied separately in the
[demo script](demo-script.md); the MP4 has no audio track. No public hosting or
external video upload is claimed.

FFprobe verified:

| Property | Value |
| --- | --- |
| Duration | Exactly 180.000 seconds, 3 minutes |
| Codec | H.264 |
| Resolution | 1280 x 888 |
| Frame rate | 25 fps |
| Frame count | 4,500 |
| File size | 3,189,581 bytes |
| SHA-256 | `d85ba2c17f13aa29fd0a1d2a68753b83a0e2d70437e132c2dc39b4f63ab7d6af` |

All screenshots were captured from actual UI states. Full-page capture scrolls
to the top first so the sticky sidebar is placed correctly in the artifact.

| Screenshot | Observed feature |
| --- | --- |
| [Dashboard](assets/screenshots/dashboard.png) | Project overview and explicit mock provider status |
| [Studio](assets/screenshots/studio.png) | Playable source video and four extracted frames |
| [Task graph](assets/screenshots/task-graph.png) | Four dependent steps, source evidence, review gate |
| [PASS](assets/screenshots/checkpoint-pass.png) | Known first-checkpoint observations and satisfied rule |
| [FAIL](assets/screenshots/checkpoint-fail.png) | Visible alignment mismatch and correction |
| [UNCERTAIN](assets/screenshots/checkpoint-uncertain.png) | Obstructed view and evidence insufficiency |
| [Completed task](assets/screenshots/task-complete.png) | Final verified checkpoint and 4 / 4 progress |
| [Evaluation](assets/screenshots/evaluation.png) | Labeled scenarios and confusion matrix |
| [Synthetic camera](assets/screenshots/synthetic-camera-uncertain.png) | Browser test stream correctly remains unknown in mock mode |
| [Tablet practice](assets/screenshots/tablet-practice.png) | Actual 1024-pixel layout |

## Reproduce

Start the application using the repository [README](../README.md). Install the
optional browser tooling into the Python environment used to run the script:

```text
python -m pip install playwright
python -m playwright install chromium
python scripts/browser-smoke.py
```

Use `--record` to overwrite the demonstration MP4 with a fresh paced capture;
FFmpeg/FFprobe must be on PATH. `--base-url` and `--api-url` can override the
default localhost ports 5173 and 8010. The script explicitly selects mock mode,
creates its own test projects, deletes temporary ones, and leaves a completed
showcase project after success. It must run against an intended local test
workspace. It makes no live Meta requests and does not upload the recording.

Unit/API/provider checks are recorded separately in [test results](test-results.md).
Physical camera hardware, mobile browser permissions, real Meta inference, public
deployment, and externally hosted video access remain unverified by this run.
