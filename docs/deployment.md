# Local operation and deployment

ReplayLab is a single-user research preview supporting physical and digital tasks.
The repository remains private. Prepared Docker files are not a claim of verified
container startup, public hosting, or successful live Meta requests.

## Source operation

Install Node.js 22.12+, Python 3.11+ (tested with 3.12), and FFmpeg/FFprobe on PATH.
From the root, run `npm run setup` followed by `npm run dev`; use `npm.cmd` in
PowerShell if its execution policy blocks `npm.ps1`.

Setup creates `.venv`, installs `apps/api/requirements.lock` when present, and runs
frontend `npm ci`. It includes RapidOCR 3.10.0, ONNX Runtime 1.31.1, and the OCR
models supplied with the installed RapidOCR wheel. Inference uses local model
paths, so missing model files are an installation issue rather than a reason to
download models silently during capture.

The UI is at http://127.0.0.1:5173 and API health at
http://127.0.0.1:8010/api/health. Vite proxies `/api`. Ctrl+C stops the development
services. Default source storage is `apps/api/data`; `DATA_DIR` can choose another
directory. Run one API worker because the screen sessions, provider mode, and
processing locks are process-local.

The source API reads `apps/api/.env`; `.env.example` supplies safe placeholders.
Mock proposals, local screen OCR, and physical fixtures require no Meta key.
Optional credentials remain server-only, with explicit consent before cloud
extraction or screenshot analysis. The owner's current scope leaves live Meta
validation pending. `npm run check` validates source behavior; `npm run contracts`
exports the shared OpenAPI snapshot. See [test results](test-results.md).

## Docker configuration

With an operating Docker engine:

```sh
docker compose up --build
```

The configuration serves http://localhost:8080 on a loopback-only host binding.
Nginx serves the built SPA and proxies `/api` to port 8010 in the API container.
The API runs as an unprivileged user, with FFmpeg installed, one worker, and a
writable `/data` volume. Dependency installation includes the local OCR package
and its model files. Health checks gate frontend startup. The proxy allows
multipart upload overhead while the API separately enforces its media limits.

Compose defaults to mock mode. It reads optional environment values from the shell
or a root `.env`; source mode instead reads `apps/api/.env`. Both are ignored by
Git/build context. Never bake secrets into images. Browser consent is still
required if a Meta provider is selected. Container build/startup and OCR inference
inside that container must be verified on an actual Docker engine before claiming
a working container deployment.

## Storage and capture

The `replaylab-data` volume preserves tutorial videos/transcripts, reference frames,
physical attempts, workflow state, generated demos, and disk inference caches.
Stopping/recreating containers does not delete the volume. Application project
deletion removes project media/records and clears shared inference/screen caches;
generated demo assets remain available. Backups contain private project data.

The screen path does not persist raw screenshot files or database blobs. It uses
transient request bytes and sanitized bounded RAM caches; the current project
session has a ten-minute TTL and clears on Stop. Framework multipart buffering
can use temporary files. Configure host/proxy logging and temporary storage to
match your retention needs rather than treating application non-persistence as
zero forensic traces. See [model usage](model-usage.md) for masks, redaction limits,
and the distinct inline-screen versus uploaded-video cloud paths.

## External hosting

Use an authentication gateway and HTTPS before exposing this service beyond
localhost. It has no multi-user authorization or tenant isolation. Preserve
same-origin `/api`, writable persistent storage, bundled OCR models, one API
worker, and server-only secrets. Independent public users need authenticated
isolated storage and a durable job queue before shared use.

Camera and screen sharing require a supported browser on localhost or HTTPS,
explicit user selection, and browser/OS permission. The provider cannot inspect
hidden applications or filesystem state. Test consent, capture denial/stop,
redaction, synthetic CodeLab OCR, physical fixtures, video playback, deletion,
and health on the actual host. Verify external embedded-video playback separately;
a valid reference URL does not guarantee that a particular video permits playback.
