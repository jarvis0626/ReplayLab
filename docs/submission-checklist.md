# Submission readiness

As of 2 November 2026, a genuine **local Meta Llama 3.2 3B** route is running on
the owner's Windows CPU. Actual browser checks returned PASS for a correct owned
capture and FAIL for a contradictory panel, with real model-grounded explanation
plans. A real API request generated a two-step transcript proposal and blocked
verification before approval. See [local Meta setup and measured evidence](local-meta-setup.md).

NVIDIA-hosted Muse Glimmer and direct Meta Model API/SAM validation remain
unverified; the Muse cloud requests timed out or returned HTTP 504. The original
three-minute recording remains an offline OCR demonstration. Local Meta is text
reasoning over OCR, not model vision or a claim of Muse/SAM inference.

ReplayLab 3.0 is a functioning local research preview with verified Meta text
inference. It is **not certified hackathon-ready**: submission eligibility and
any requirement for a particular model/API remain unconfirmed. The repository
stays private under owner instructions.

| Brief requirement | Delivered behavior / remaining boundary |
| --- | --- |
| Launch, create, upload, sample video | Local FastAPI/Vite startup and actual FFmpeg processing tested |
| Extract and review a structured workflow | Real local Meta transcript proposal measured; local frame OCR can supply text evidence, with editable graph and explicit approval; arbitrary visual interpretation remains unverified |
| Shared physical/digital workflow and results | Same reviewed task/DAG, persistent progression, shared inspectable decision contract |
| Screen permission and observation | User-triggered browser capture, scope/preview, pause/stop, adaptive real local OCR; automated browser QA selects a real tab using a Chromium test flag |
| PASS, FAIL, UNCERTAIN, corrections | Positive evidence, visible contradictions, abstention, version-quality checks, inspectable rules and sources |
| Genuine Meta model usage | Local Meta Llama 3.2 3B verified on real text, OCR interpretation, workflow proposals, and grounded explanation plans; Muse/SAM cloud calls and broad accuracy remain unverified |
| Separate provider modes | Explicit local Meta, mock, NVIDIA, and direct Meta; no silent replacement of failed model calls |
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

Before submission, the owner must verify allowed model/API requirements,
eligibility/acceptance, repository visibility requirements, and any hosted-demo
requirement. Local Meta inference is verified; broader capability and submission
claims must stay within the recorded evidence.
