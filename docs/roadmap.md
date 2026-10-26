# ReplayLab roadmap

**Current state:** Repository preparation and planning only. No application features, model calls, screenshots, deployments, evaluation scores, or test results are complete.

The target is a working vertical slice for a controlled four-step colored-block assembly: upload a demonstration, review timestamped steps, inspect the action graph, capture an attempt, and receive an evidence-backed PASS, FAIL, or UNCERTAIN result.

## Delivery rules

- Verify the official hackathon build window before creating project-specific application code. Check the organizer's latest rules and deadline before submission.
- Keep this repository private, as requested by the user. Do not make it public automatically. If submission rules require public access, explain that requirement and obtain authorization before changing visibility.
- Commit and push major completed milestones with factual summaries and recorded validation. Do not describe a milestone as complete while its required behavior is missing.
- Distinguish implemented behavior, mock fixtures, live provider behavior, and unverified integration work in documentation and the UI.
- Use official Meta schemas and model identifiers only after checking current documentation. Do not fabricate provider methods, outputs, or successful live calls.

## Phase 0: Preparation

**Planned deliverables:** Private repository, documented product scope, architecture, roadmap, repository hygiene, and confirmed build eligibility.

**Acceptance:** Repository visibility is verified as private; the initial commit contains planning material only; no secrets or private media are included; the official build start and implementation gate are recorded accurately.

## Phase 1: Foundation

**Planned deliverables:** React/TypeScript frontend, FastAPI backend, SQLite metadata storage, navigation shell, health endpoint, provider interfaces, explicit mock status, and environment configuration.

**Acceptance:** Frontend and backend start using documented commands; the API health check succeeds; basic project persistence survives a restart; absent credentials produce visibly labeled mock mode; relevant startup/API checks run and their actual outcomes are recorded.

## Phase 2: Video and task understanding

**Planned deliverables:** Safe uploads, real video playback and metadata, FFmpeg/OpenCV reference frames with timestamps, background jobs, validated task contracts, deterministic mock extraction, and editable task review.

**Acceptance:** A permitted sample video produces real timestamped frames; corrupt or oversized media is rejected safely; processing failures are visible; extracted task output is schema-validated; users approve or correct steps before practice; data persists after reload.

## Phase 3: Action graph and guided practice

**Planned deliverables:** Domain DAG engine, React Flow graph, source evidence display, dependency-aware progression, webcam preview/capture, manual checkpoint uploads, and persisted attempts.

**Acceptance:** Missing dependencies and cycles are rejected; topological order is valid; edits retain valid dependencies; steps cannot advance ahead of prerequisites; camera denial and unavailable devices have usable recovery paths; captured/uploaded checkpoints show beside their reference images.

## Phase 4: Evidence-grounded verification

**Planned deliverables:** Deterministic normalized-geometry rules; evidence sufficiency checks; PASS/FAIL/UNCERTAIN aggregation; object/rule diagnostics; available overlays; template corrections; and focused verification tests.

**Acceptance:** Correct relationships pass, visible mismatches fail with a specific correction, and occlusion/poor visibility/camera mismatch yield uncertainty when evidence is insufficient. A low-confidence missing detection does not automatically fail. Verdicts come from observations and constraints, never filenames, buttons, or requested outcomes. Explanation output cannot override the verdict.

## Phase 5: Meta integration

**Planned deliverables:** Officially documented reasoning, segmentation, and grounded explanation adapters; real response normalization; provider provenance; inference cache; visible availability; and explicit failure handling.

**Acceptance:** Current official identifiers and request/response contracts are documented before integration; API keys stay on the backend; malformed provider outputs are rejected; authentication, billing, rate-limit, timeout, and outage paths are handled. Successful live requests are claimed only after execution and inspection. If credentials or billing block validation, document exactly which adapter behavior remains unverified and preserve the clearly labeled offline workflow.

## Phase 6: Evaluation and polish

**Planned deliverables:** At least 12 labeled scenarios covering correct, incorrect, and ambiguous cases; evaluation diagnostics; frontend/backend checks; CI; responsive and accessible UI; privacy/error handling; and reproducible local setup.

**Acceptance:** Record actual test commands and outcomes. Report expected versus predicted verdicts with case counts, sample size, and limitations. Keep fixture-based deterministic checks separate from live model measurements. Report a confusion matrix or metrics only when supported by the collected labels and results. Capture screenshots/GIFs only from working features.

## Phase 7: Deployment and submission preparation

**Planned deliverables:** Deployment guide, working demo data, actual model-usage description, factual three-minute demo script/video, license and asset attribution, verified submission links, and a readiness checklist.

**Acceptance:** Reproduce the end-to-end flow from documented setup; verify deployed health and media behavior if deployed; disclose cloud processing and retention; verify video access and current organizer requirements. Resolve any public-repository requirement with the user before changing the private repository's visibility. Submit only capabilities and live calls that have been demonstrated.

## Validation and milestone records

For each implementation milestone, record the change, validation command(s), actual result, provider mode, known limitations, and commit identifier. Push meaningful milestones to the private GitHub repository. Keep secrets and user media out of commits.

The first useful vertical slice should connect real upload/frame extraction to approved task constraints and checkpoint verification in explicit mock mode. Subsequent work replaces provider fixtures with verified live integrations while preserving deterministic verdicts and honest provenance.

No implementation phase is marked complete by this document. Phase status should change only when the corresponding acceptance checks have actually been met.
