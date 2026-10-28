# Submission readiness

ReplayLab 3.0 is a functioning offline research preview. It is **not certified
hackathon-ready**: successful live Meta inference and submission eligibility
remain unverified, and the owner requires this repository to stay private.

| Brief requirement | Delivered behavior / remaining boundary |
| --- | --- |
| Launch, create, upload, sample video | Local FastAPI/Vite startup and actual FFmpeg processing tested |
| Extract and review a structured workflow | Offline timestamped transcript/label proposal, editable graph, explicit approval; arbitrary video interpretation requires the optional Muse adapter |
| Shared physical/digital workflow and results | Same reviewed task/DAG, persistent progression, shared inspectable decision contract |
| Screen permission and observation | User-triggered browser capture, scope/preview, pause/stop, adaptive real local OCR; automated browser QA selects a real tab using a Chromium test flag |
| PASS, FAIL, UNCERTAIN, corrections | Positive evidence, visible contradictions, abstention, version-quality checks, inspectable rules and sources |
| Genuine Meta model usage | Muse video/screen/explanation and SAM adapters implemented and contract-tested; credentialed live calls, billing/access, accuracy, and real SAM tracking remain unverified |
| Separate provider modes | Explicit MOCK/META; no silent replacement of failed live observations |
| Automated tests and measured evaluation | Actual pytest/Vitest/build checks; frozen 20-case controlled browser evaluation with case evidence and latency |
| Independent evaluation | Agent-authored labels fixed before inference; independent human annotation and unseen application studies are not delivered |
| Reproducible digital demonstration | Verified 180-second CodeLab walkthrough with actual tutorial upload/transcript review, four live and three manual OCR checks, decisions, physical shared inspector, and evaluation; no real VS Code extension installation |
| Physical transfer | Controlled colored-block fixtures use the same graph/result inspector; labeled fixture observations are not live SAM |
| Public repository | Intentionally private under owner instructions; no visibility change or submission publication performed |
| Hosted application | Deployment configuration prepared; Docker runtime and public hosting remain unverified |
| Eligibility/provenance | Implementation began before the published kickoff under explicit owner authorization; participant acceptance and eligibility are unconfirmed |

Current evidence and exact checks are recorded in
[implementation status](IMPLEMENTATION_STATUS.md), [test results](test-results.md),
and [digital evaluation](digital-evaluation.md). Original physical demonstration
evidence remains available in [demo-script.md](demo-script.md).
The current recording and its reproduction/limitations are in [v3-demo.md](v3-demo.md).

Before an eventual submission, the owner must resolve live model validation,
eligibility/acceptance, repository visibility requirements, and any hosted-demo
requirement. These external decisions do not prevent the authorized offline
application work or private milestone pushes.
