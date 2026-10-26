# Recorded validation

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
