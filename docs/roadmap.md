# ReplayLab delivery status

ReplayLab 2.0 implements both the original physical workflow and an offline digital
vertical slice: tutorial source, reviewed task graph, user-authorized screen
capture, actual local OCR, deterministic verification, and corrective guidance.
The CodeLab tutorial/application is synthetic and explicitly labeled; OCR is
actual local inference rather than fixture lookup or Muse output.

## Implemented scope

| Area | Current behavior |
| --- | --- |
| Shared workflows | Physical/digital modality, timestamps, source references, editable prerequisites, approval, dependency-aware progress |
| Physical path | Original camera/image capture, four-block mock source and pixel-matched fixtures, evidence-gated geometry, retained SAM adapter |
| Digital sources | Rights-confirmed uploaded videos, strict YouTube metadata/embed references without scraping/downloads, bounded timestamp/SRT transcripts |
| Digital proposals | Fixed CodeLab mock template or quoted-label transcript candidates; manual rules where evidence is absent |
| Screen assistant | Explicit `getDisplayMedia`, visible scope/preview, pause/stop, change-aware capture, screenshot upload, browser masks |
| Observations | Bundled local RapidOCR/ONNX models, actual visible text/boxes, confidence, best-effort redaction; optional separate Muse screenshot adapter |
| Verification | Positive evidence and contradictions, dialog/error handling, interface uncertainty, skipped-prerequisite review, stale-result/cache invalidation |
| Coaching | Evidence-backed written corrections, user-enabled deduplicated speech, grounded Ask templates, navigation without fabricated completion |
| Privacy | No application persistence of raw screen images; bounded sanitized RAM results, project-session expiry/clear, explicit cloud consent |
| Validation | Parser, media, OCR, provider, graph, verifier, privacy, API/concurrency, and frontend checks; actual outcomes in test results |

The earlier physical screenshot set and three-minute silent recording remain
available as evidence of that version's working workflow. New digital browser
evidence must be recorded from the application before being claimed; source or
component tests alone do not establish browser/device behavior.

## Intentionally pending external work

| Work | Required evidence |
| --- | --- |
| Live Meta validation | Authorized consented requests inspected for actual model results, account access, errors, and latency; left pending by owner choice |
| Broader evaluation | Independently labeled real tutorials/screens and physical attempts; false passes/failures, uncertainty, and detection measurements |
| Container/public hosting | Actual engine/host startup, health, persistent disk, OCR models, capture/consent, and deletion checked |
| External publication | Authorized demo-video hosting/submission links; no public deployment or uploaded-video claim from local artifacts alone |
| Production use | Authentication, tenant isolation, durable queue, operational monitoring, and reviewed retention controls |
| Submission | Current organizer requirements and eligibility reviewed; any public-repository requirement requires an explicit owner decision |

No key is required to complete the authorized offline scope. Retain implemented
Meta paths and truthful availability errors without asking again for credentials
or silently substituting mock output.

## Provenance and publishing

The private repository and original physical implementation remain preserved.
The owner authorized pre-kickoff coding on 26 October 2026 with eligibility
unconfirmed, then chose to finish offline. [Official sources](official-sources.md)
and the [original brief](project-brief.md) preserve that history; neither confirms
submission eligibility.

Review scoped changes/secrets/artifacts, run meaningful checks, record actual
results in [test results](test-results.md), then commit and push completed major
updates to the configured private remote. Verify the remote commit. Do not
force-push, change visibility, delete remote branches, or create background push
automation. [Development](development.md) describes the working commands.
