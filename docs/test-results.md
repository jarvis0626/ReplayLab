# Recorded validation

## NVIDIA integration — 2 November 2026

The final `npm.cmd run check` passed **396 backend tests**, **42 frontend tests**,
backend Ruff, TypeScript, and the Vite production build. New coverage includes
37 NVIDIA transport/schema/grounding/cache/concurrency tests, eight cloud-consent
and routing cases, and 19 evaluation orchestration cases. All inference in those
unit/integration tests uses mocked transport; these counts are not model accuracy.
The OpenAPI snapshot, Docker Compose configuration, helper-script Ruff checks,
and local document links also validate.

The application source passed [GitHub Actions on Ubuntu](https://github.com/jarvis0626/ReplayLab/actions/runs/41454722961),
commit `810149c`. Reviewing older workflow results also uncovered a test race:
the stale-task regression assumed that an edit would finish within300ms. The
application correctly returned409 after an edit, while that timing branch
occasionally expected200. The test now waits for the actual edit response before
releasing inference, then requires409 and no stale result/evidence/progress.
All three affected API edge-case tests and Ruff passed after this test-only fix.

Actual authenticated text/image probes, streaming, minimal requests, and the
exact NVIDIA example via HTTPX and the official client all timed out. The owner
demonstrated a successful Playground response, which does not establish this
application's API access. [Raw safe check metadata](validation/nvidia-live-checks.json)
preserves the actual failures without keys or invented model responses.

The real [NVIDIA evaluation](nvidia-evaluation.md) attempted two controlled images
with a ten-second timeout and opened its failure circuit. **0/20 cases completed**,
18 were not attempted, and all accuracy/calibration/successful-response latency
metrics remain unknown. The original local OCR 20/20 result stays separate.

The [actual browser test](nvidia-browser-qa.md) sent one controlled screenshot with
explicit in-app consent and observed HTTP 502, a visible timeout, zero progression,
and NVIDIA still selected. Explicitly selecting mock afterward produced real
local OCR PASS. Eight continuation assertion groups passed with zero JavaScript
errors and desktop/tablet layout checks. The failed first harness phase and its
unknown timing are disclosed; no second live image request was manufactured for
the continuation. No successful live NVIDIA or new submission-video claim is made.

## ReplayLab 3.0 upgrade — 28 October 2026

`npm.cmd run check` completed with **332 backend tests passed**, **38 frontend
tests passed**, backend Ruff clean, and a successful TypeScript/Vite production
build. This includes all earlier physical/digital tests and new shared evidence,
retention, feedback, threshold, version-quality, model-grounding, audio media,
streamed-upload cancellation, and evaluation metric regressions. A Starlette
HTTPX TestClient deprecation warning remains; it does not fail the suite.

The captured digital suite measured **20/20 agreement**, **10/10 decisive
accuracy**, **0/10 false certainty**, **10/10 uncertainty recall**, zero PASS/FAIL
swaps, median **2170.34 ms**, and nearest-rank p95 **2928.84 ms** (n=20). The
screenshots were captured from actual Chromium-rendered CodeLab attempts and
controlled obscured/version views. Labels were fixed by the implementing agent
before inference; no independent human review or live Meta inference is claimed.
See [evaluation methodology and case evidence](digital-evaluation.md).

OpenAPI export, document-link checks, and `docker compose config --quiet` pass.
Docker runtime/public hosting and credentialed Meta calls remain unverified.
The final application source passed [GitHub Actions on Ubuntu](https://github.com/jarvis0626/ReplayLab/actions/runs/40706517421),
commit `d525b97`. The earlier backend milestone also passed
[Actions](https://github.com/jarvis0626/ReplayLab/actions/runs/40705588273),
commit `603e00a`.

The [actual 3.0 recording](v3-demo.md) passed **13 browser assertion groups** with
**seven real OCR decisions** (four live tab captures, three explicitly manual
actual browser screenshots): four PASS, one FAIL, two UNCERTAIN. It verified all
four digital checkpoints, a separate physical fixture PASS using the common
inspector, saved evidence, stopped tracks, desktop/tablet layouts, and measured
evaluation. Zero JavaScript errors were observed. The final silent subtitled
H.264 video is **180.000 s**, **1280×960**, **4,500 frames**, **3,759,818 bytes**;
FFprobe and full FFmpeg decode passed. The manual transition addresses a recorded
headless Chromium background-frame freeze; it is disclosed in the video and report.

## ReplayLab 2.0 upgrade — 27 October 2026

The integrated `npm.cmd run check` completed with **286 backend tests passed**, **32 frontend tests passed**, Ruff clean, and a successful TypeScript/Vite production build. This run includes the original physical workflow tests and the digital ingestion, OCR, verification, privacy, cache, and concurrency suites.

After adding the small-change heartbeat and semantic voice deduplication, the frontend suite passed **33 tests** and rebuilt successfully. The affected digital API suite also passed **23 tests**, including completed-workflow coaching. The final application source passed [GitHub Actions on Ubuntu](https://github.com/jarvis0626/ReplayLab/actions/runs/40544143866), commit `59b0410`.

The [actual digital browser walkthrough](digital-browser-qa.md) passed **19 assertion groups** using a real Chromium tab stream and local OCR: seven successful screen checks produced four PASS results, two evidence-backed FAIL results, and one interface-mismatch UNCERTAIN. It verified four-step completion, pause, ended capture tracks, no requests after stop, cleared Ask context, peak request concurrency of one, zero JavaScript errors, and desktop/tablet layout. Chromium's test-only source-selection flag chose the controlled CodeLab tab; no screen API stub or canned verdict was used.

Actual local OCR was exercised on generated reference pixels and rendered CodeLab screenshots. Contract tests for Muse tutorial/screenshot adapters use mocked HTTP transport; they are not live Meta calls. Tests cover rights confirmation, strict YouTube references, timestamped/SRT transcripts, all four digital checkpoints, wrong destinations, unverified prerequisites, visible dialogs/errors, unclear frames, version mismatch/ambiguity, coach self-capture, redaction, denied/stopped sharing, stale results, and cached-progress invalidation.

GitHub Actions passed on Ubuntu for the upgrade implementation and version-parser hardening: [verified 2.0 workflow](https://github.com/jarvis0626/ReplayLab/actions/runs/40541938683), commit `e808f7f`. The earlier integrated upgrade run also [passed](https://github.com/jarvis0626/ReplayLab/actions/runs/40541100391), commit `a4a778c`. Later changes are checked separately; these links do not claim a future run has completed.

OpenAPI export and Docker Compose configuration validation passed. Docker image startup, public hosting, live Meta availability, and submission eligibility remain unverified. The owner explicitly retained offline operation and private repository visibility.

## Original physical baseline — 26 October 2026

Local validation was performed on 26 October 2026 using Windows, Python 3.12.3, Node.js 22.17.1, npm 10.9.2, and FFmpeg 8.0.1. These are executed checks, not planned checks.

| Check | Observed result |
| --- | --- |
| `npm.cmd run check`: backend pytest | **140 passed** |
| Backend Ruff | Passed |
| Frontend Vitest | **19 passed** |
| TypeScript and Vite production build | Passed |
| Frontend dependency audit | 0 known npm vulnerabilities at validation time |
| OpenAPI contract export | Passed |
| `npm.cmd run setup` | Passed; locked Python dependencies and clean npm installation completed |
| `docker compose config --quiet` | Passed |
| Curated normalized-observation evaluation | **25/25** expected verdicts matched: 10 PASS, 6 FAIL, 9 UNCERTAIN |

The backend suite covers schema and normalized-geometry validation, DAG dependencies/cycles, all supported verification rules, missing/low-confidence/occluded observations, viewpoint mismatch, exact counts and duplicate detections, actual video processing, upload content/size/duration/dimension limits, approval and progression, stale-checkpoint rejection, provider transport/parser failures, SQLite reopen persistence, interrupted-job recovery, and project/cache deletion.

After adding safe provider usage logging and persisted analysis provenance, the affected provider/media/API-edge subset was rerun: **39 passed**, with Ruff clean. The exported OpenAPI contract is regenerated after response schema changes.

One upstream Starlette warning reports that its HTTPX TestClient integration is deprecated in favor of HTTPX2. It did not fail the checks. The pinned, tested HTTPX client remains used for the actual provider adapter; no live Meta request was executed.

## Browser and external checks

The actual Chromium walkthrough passed **19 check groups** with zero page errors, including real upload/playback, graph review/approval, all three verdicts, four-step progression, evaluation, synthetic camera capture, and desktop/tablet layout. See [browser QA](browser-qa.md) for its artifact and check record. Screenshots and recording use the real application with labeled synthetic fixtures. Synthetic browser camera testing does not establish physical-camera behavior on every device.

Docker image build/startup remains **unverified** because Docker Desktop's engine is unavailable in this environment. Compose configuration validation does not establish container startup.

Live Meta credentials, account entitlement, billing, inference accuracy, and latency remain **unverified**. The owner explicitly chose to finish offline. Provider contract tests use mocked HTTP transport and the actual official SAM parser, not live model responses.

GitHub Actions **passed on Ubuntu** for implementation commit `a31c863`: [verified workflow run](https://github.com/jarvis0626/ReplayLab/actions/runs/40326054241). That run executes backend tests/lint and frontend tests/build. Later documentation-only pushes can trigger separate runs; their state is not implied by this record.

Public hosting, a publicly accessible demo-video link, and hackathon eligibility are not established by these checks. The silent, actual application recording is stored locally and in the private repository at [docs/assets/demo.mp4](assets/demo.mp4); it is exactly 180 seconds with 4,500 H.264 video frames.
