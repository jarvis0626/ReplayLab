# Model integration, evidence, and data flow

ReplayLab separates task proposals, visible observations, deterministic verdicts,
and guidance. The owner chose **finish offline; leave live validation pending**.
Both offline examples and local OCR are implemented; no successful live Meta
request is claimed. Failed Meta requests remain visible and never become mock
results.

## Provider responsibilities

| Function | Implemented provider | Evidence boundary |
| --- | --- | --- |
| Physical offline proposal | Fixed four-block mock template | Not an interpretation of an arbitrary video |
| Digital offline proposal | Fixed CodeLab template or timestamped transcript segmentation | Quoted labels are candidate rules requiring review; absent labels need manual rules |
| Physical offline observations | Registered decoded-pixel fixture lookup | Explicit synthetic geometry; unknown images remain uncertain |
| Digital local observations | RapidOCR 3.10.0 with ONNX Runtime 1.31.1 | Actual screenshot pixels, OCR confidence/boxes, best-effort redaction; no hidden application state |
| Optional tutorial understanding | Muse Spark `muse-spark-1.3` | Validated proposals through Responses, requiring human approval |
| Optional digital screenshot understanding | Separate Muse screenshot adapter | Redacted inline image; returns observations, not verdicts; never uses SAM |
| Optional physical segmentation | `sam-3.1` | Official SAM parser normalizes boxes/masks/confidence |
| Guidance | Deterministic corrections/Ask templates, optional fixed-evidence selection and browser speech | Cannot override verdicts or invent observations |

In 3.0, digital Meta guidance uses a constrained Muse sentence plan: select up to
three existing evidence IDs and one approved correction ID, preserving the exact
deterministic status. Only those approved facts are rendered as natural language.
Free-form model narration is not accepted. Unsupported IDs, changed statuses, or
provider failure retain explicitly identified deterministic guidance; actual Meta
screen observations do not become mock data. The optional call runs outside global
project/session locks, and a stopped or changed workflow cannot commit its result.
Plans use a bounded 16-entry, ten-minute redacted RAM cache, cleared on deletion.

Local OCR uses the three models installed with the RapidOCR wheel through explicit
paths. Missing OCR dependencies/models produce unavailable/uncertain behavior;
capture-time code does not fetch replacements. OCR scores measure recognition,
not the probability that a workflow or physical action is complete.

## Meta contracts

The adapters use `https://api.meta.ai/v1`, Bearer authentication with the
server-only `MODEL_API_KEY`, and `POST /responses`. Muse structured responses use
`text.format` with `type:json_schema`, a schema/name, and strict validation. Local
Pydantic/domain checks still reject invalid proposals and observations.
[Quickstart](https://dev.meta.ai/docs/quickstart),
[Responses schemas](https://dev.meta.ai/docs/api-reference/responses/schemas).

Tutorials, screenshots, captions, and visible text are untrusted input data.
Provider instructions prohibit treating them as agent/system instructions,
executing commands, revealing credentials, reconstructing redacted text, or
certifying completion. The verifier uses approved rules and observed evidence.

### Uploaded videos and pasted transcripts

Rights-confirmed videos are inspected and sampled locally. Non-MP4 inputs are
prepared as MP4 before Meta video understanding. File upload uses multipart
`purpose=user_data`; Muse receives an `input_file.file_id`. Uploaded files request
one-hour expiration, and cleanup attempts `DELETE /files/{id}` in `finally`.

MP4 preparation now preserves the first embedded audio track as AAC when present,
alongside H.264 video; silent sources remain supported. This is tested with actual
FFmpeg-encoded media. Source transcripts can also be supplied directly. No local
speech-to-text system or successful Muse audio transcription is claimed; Meta's
current video guide notes limitations in audio support.
Cleanup failures are surfaced in proposal provenance. A timeout before an upload
ID arrives cannot be cleaned up by ID; requested expiration remains the fallback.
[Video understanding](https://dev.meta.ai/docs/video-understanding/),
[file handling](https://dev.meta.ai/docs/file-handling).

Digital Muse extraction accepts supplied transcript text and/or an authorized
uploaded tutorial. YouTube references are not downloaded and do not supply hidden
caption content. Offline parsing is deterministic and is not labeled Muse.
Timestamps, graph structure, expected states, and rule schemas are validated.
Four sampled frames may miss a brief final state; users must inspect the evidence.

**Screen redaction does not sanitize source videos or pasted transcripts.**
Review that content before explicit cloud-extraction consent. Source metadata,
transcripts, and reviewed tasks are persistent local project data.

### Digital screenshot path

Screen sharing starts only through a user-triggered `getDisplayMedia` picker;
the app shows the browser-reported scope and preview. Browser rectangles mask
selected live-preview regions before upload. They are coordinate-based and need
review after layout changes. Manually chosen screenshot files do not inherit
those masks.

Local OCR replaces detected emails/key-like text in observations. Before optional
Meta transmission it blacks out the corresponding detected image regions and
strips image metadata. If the privacy OCR scan is unavailable, the Meta screen
request is refused. Redaction is best effort: unrecognized text, undetected
secrets, faces, and other private content can remain. Share a narrow target window
and keep the coach outside it; self-captures cannot establish their own success.

With separate explicit screen cloud consent, the Muse screenshot adapter sends an
`input_image.image_url` data URL and requests **`store:false`**. It does not use
Files upload and has **no one-hour file-expiration mechanism**. That flag requests
no stored Responses state, not zero provider retention; provider processing and
retention terms still apply. Missing credentials, auth/billing errors, refusals,
or outages do not select local/mock results silently.

Digital rules require qualified positive UI evidence. Missing expected text alone
is uncertain. Visible known contradictions, unexpected dialogs/errors, or a
qualified wrong active destination can establish failure. Explicit version
differences remain possible tutorial mismatch. No visible-label predicate proves
filesystem contents, physical installation, or hidden settings.

### Physical SAM path

Each SAM call supplies one noun phrase and an image. Metadata strings request
`include_confidence:"true"` and `mask_encoding:"one_bit"`. The adapter uses the
documented non-streaming output and requires completed responses.

SAM emits special-token text, not JSON. `meta-sam-parser==0.1.0` decodes it through
`image_segmentation_format().create_parser()`, `push`, and
`finish(CompletedOutcome())`. Inclusive wire corners become half-open boxes,
normalized to actual oriented image dimensions. Masks use official compressed
COCO RLE, with box-local size/bounds rather than whole-frame raster coordinates.
Malformed records and mismatched dimensions are rejected.

Missing confidence stays unknown. Empty completed output is a valid zero-match
result, not proof of absence. SAM does not establish visibility/completeness,
camera comparability, or an independent calibrated color measurement. The API
records user view/visibility attestations and a separate image-quality heuristic;
insufficient evidence remains uncertain.
[SAM prompts](https://dev.meta.ai/docs/sam/segmenting),
[output grammar](https://dev.meta.ai/docs/sam/reading-segmentation),
[official Python parser](https://github.com/meta-models/meta-sam/blob/main/python/README.md).

## Caching, retention, and controls

The screen endpoint does not create screenshot media, attempt images, database
screen blobs, or screen-content logs. Request bytes/canvas frames remain transient;
HTTP frameworks can buffer multipart input in temporary files. This is not a
guarantee of zero disk traces from an operating system, proxy, or HTTP stack.

Sanitized OCR and Meta screen observations use bounded process-memory caches.
The latest project screen session expires after ten minutes and clears on Stop;
stopped generations cannot commit late results. Shared OCR/model caches have
bounded entries and clear on project deletion or process restart. Screen response
cache identity includes task revision and relevant completed-step history, so
earlier skipped-step evidence is reevaluated after prerequisite progress.

Physical observations and tutorial proposals have a separate ignored disk cache
keyed by media/model/schema/configuration. These derived descriptions can still
be private. Project deletion clears shared inference caches conservatively; shared
synthetic demo assets remain available. Source videos, transcripts, reference
frames, physical attempts, and workflow progress persist until project deletion.

Rate limits and bounded retries apply separately to provider requests and screen
analysis. Error messages omit raw upstream diagnostics. Deterministic guidance
retains its verdict if optional explanation selection fails; Ask uses only the
reviewed workflow and current session evidence. Optional speech is user-enabled
and deduplicated; it does not perform target actions.

## Validation status

Transport tests simulate Meta responses and cover structured contracts, errors,
redaction boundaries, parsing, adapter separation, and cleanup. Local OCR tests
read actual generated image pixels; API tests exercise actual reference OCR and
controlled concurrency/privacy cases. These do not measure live Muse/SAM accuracy
or establish account entitlement, billing, latency, or provider retention.

Actual check results are in [test results](test-results.md). Live Meta validation
remains pending by owner choice; public hosting and container runtime verification
are separate from implemented configuration.
