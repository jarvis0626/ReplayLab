# ReplayLab roadmap and delivery status

The local application and explicit mock vertical slice are implemented. Meta
adapters are implemented and tested against mocked transport; live service
availability is unverified. The repository remains private.

The owner explicitly authorized implementation before the scheduled kickoff on
26 October 2026. This decision superseded the original planning-only build gate;
it does not establish hackathon eligibility. Preserve the history in
[official sources](official-sources.md) when preparing a submission.

## Implemented milestones

| Milestone | Current behavior and evidence |
| --- | --- |
| Foundation | React/TypeScript/Vite frontend, FastAPI, SQLite project/attempt persistence, health/provider status, explicit mock mode |
| Media and task review | Bounded real video inspection, four timestamped frames, processing/error status, structured task editing and approval |
| Graph and practice | Validated DAG, missing-dependency/cycle rejection, React Flow view, prerequisite gates, webcam capture, image uploads, attempt history |
| Verification | Evidence-gated presence/count/position/proximity/alignment/color rules, per-rule diagnostics, corrections, PASS/FAIL/UNCERTAIN, task-revision checks |
| Offline demonstration | Generated assembly video/images, fixed mock proposal, pixel-matched known fixture observations; arbitrary images remain uncertain |
| Meta integration code | Official documented models/endpoints, structured output validation, native SAM parser, normalized boxes/COCO masks, cache, retry/error handling, consent, file cleanup |
| Reproducible evaluation | 25 curated normalized-observation scenarios, expected/predicted details and confusion matrix, packaged fixture JSON |
| Documentation | Architecture, development, model usage, evaluation scope, demo walkthrough, and deployment preparation |

These claims describe source behavior and the validation recorded in
[test results](test-results.md). A fixture or mocked-transport test is not a
credentialed model call, measured live accuracy, public deployment, or organizer
acceptance. Camera behavior additionally depends on the user's device/browser.

## Remaining delivery work

| Work | Completion criterion |
| --- | --- |
| Credentialed Meta validation | Authorized server key/account/billing, explicit media consent, inspected successful Muse and SAM calls, documented real latency and failure behavior |
| Real-media evaluation | Independently labeled reference/checkpoint set; report detection quality and end-to-end verdicts separately from deterministic fixture agreement |
| Hosted demo | Deployment credentials and chosen access policy; verify deployed health, media/fixture access, persistent disk, consent, and deletion |
| Demo recording | Record the working three-minute walkthrough, review factual claims and provider labels, upload only when sharing is authorized |
| Submission readiness | Verify current organizer requirements, eligibility, accepted links, and participant status; resolve any public-access requirement explicitly while keeping this repository private |
| Production hardening | Authentication, tenant boundaries, durable job queue, multiworker concurrency, retention controls, and operational monitoring before public multiuser use |

The first three external items require account access, hosting, or additional
media rather than a fabricated successful result. Do not substitute the offline
sample for live Meta validation or describe a prepared script as a recorded demo.

## Milestone publishing

Review the diff and staged paths for scope, secrets, and runtime artifacts. Run
the applicable checks and record actual results. Commit completed meaningful
updates, push to the configured private remote without force, and verify the
remote commit. The owner's existing instruction authorizes these milestone
pushes; it does not authorize changing repository visibility or rewriting shared
history. See [development](development.md).
