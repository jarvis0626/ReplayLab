# Development and GitHub workflow

ReplayLab 3.0 adds shared decision/feedback contracts and a captured digital
evaluation. See [implementation status](IMPLEMENTATION_STATUS.md) and
[digital evaluation](digital-evaluation.md). The latter can be replayed without
a browser using `.venv\Scripts\python.exe scripts/evaluate-digital.py`.

The optional policy variables in `.env.example` set minimum observation
confidence and image-quality gates. They are heuristic policy values, not
calibrated probabilities. Defaults remain compatible with existing workflows.
Per-capture digital evidence retention is off until explicitly selected in the
screen assistant; no digital screenshot images are saved by that feature.

ReplayLab runs locally with FastAPI, SQLite, and React/Vite. Both physical and
digital examples work without a Meta key. Digital local OCR is separate from
labeled mock task proposals and physical fixture lookup.

## Requirements and setup

Install Node.js 22.12+, Python 3.11+ (tested with 3.12), and FFmpeg/FFprobe on PATH.
From the repository root:

```powershell
# Windows PowerShell
npm.cmd run setup
npm.cmd run dev
```

```sh
# Linux/macOS
npm run setup
npm run dev
```

Setup creates `.venv`, installs `apps/api/requirements.lock` when available, and
runs frontend `npm ci`. It checks Python/Node and FFmpeg availability. It does not
activate the environment or copy credentials. OCR adds larger binary/model
dependencies: RapidOCR 3.10.0 and ONNX Runtime 1.31.1. The RapidOCR wheel supplies
the three local ONNX models; capture-time inference uses installed paths and
requires no runtime model download.

`npm run dev` starts the API at 127.0.0.1:8010 and Vite at 127.0.0.1:5173, with
`/api` proxied to FastAPI. Ctrl+C stops both services. Health and interactive API
docs are `/api/health` and `/docs` on port 8010. Run one API worker: screen sessions,
provider selection, and locks are process-local.

The default is `AI_PROVIDER=mock`. For local configuration, copy `.env.example`
to `apps/api/.env` only if it does not already exist. Keep `MODEL_API_KEY` on the
server and out of frontend variables. Source-mode data defaults to `apps/api/data`;
`DATA_DIR` can move it. Screen check intervals are separately configurable through
`SCREEN_LOCAL_INTERVAL` and `SCREEN_META_INTERVAL`.

For a manual API terminal, run the environment's Python from `apps/api`:

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Use `../../.venv/Scripts/python.exe` on Windows or `../../.venv/bin/python` on Unix
when already inside `apps/api`. A separate root terminal can run
`npm --prefix apps/web run dev`.

## Checks and contracts

```text
npm run check
npm run contracts
npm run build
```

Checks include backend pytest/Ruff, frontend tests, TypeScript checking, and the
production build. Contract export regenerates `packages/contracts/openapi.json`
using temporary storage. API-only checks from `apps/api` are `python -m pytest -q`
and `python -m ruff check app tests` with the virtual environment's Python.

Tests use actual local OCR on generated pixel images and controlled observations
for edge/concurrency cases. Meta transport tests make no live requests. Review
[test results](test-results.md) for measured outcomes and
[evaluation](evaluation.md) for the separate curated physical observation set.

## Workflows and private data

Use [digital workflows](digital-workflows.md) for the CodeLab sandbox and screen
assistant. Choose its separate tab/window in the browser picker, keeping the
coach outside the capture. Camera/screen sharing requires localhost or HTTPS.
Sharing, optional voice, pause, and stop are controlled by the user. Uploaded
tutorials require usage-rights confirmation; YouTube references never trigger
server downloads or caption scraping.

Source videos/transcripts, task state, reference frames, progress, and physical
attempts persist until project deletion. Raw screen images are not application
media/database records. Sanitized screen results stay in bounded RAM caches;
current project screen evidence expires after ten minutes and clears on Stop.
The HTTP framework can transiently buffer multipart uploads, so this is not a
guarantee of zero disk traces. Project deletion clears inference/screen caches;
shared generated demo assets remain available.

Preview masks and OCR redaction are best effort. Uploaded screenshot files do
not inherit live-preview masks. Source tutorial videos/transcripts are not
automatically sanitized by that pipeline. Do not commit private media, keys,
screen captures, runtime databases, caches, dependencies, or build products.

The owner chose to finish offline and leave live Meta validation pending. Retain
the implemented adapters and visible error paths without claiming live success or
requesting a key as a completion prerequisite. [Model usage](model-usage.md)
documents optional provider behavior and consent boundaries.

## Reviewed milestone publishing

```text
git status --short
git diff
git add <reviewed-paths>
git diff --cached --check
git diff --cached
git commit -m "Describe the completed milestone"
git push
git status --short --branch
```

Replace the placeholder with scoped reviewed paths and run applicable checks
before committing. Verify the remote commit. The owner's standing instruction
authorizes meaningful completed milestone pushes; do not force-push, rewrite
shared history, remove remote branches, change visibility, or install background
commit automation.

The repository remains private. Coding before kickoff was explicitly authorized
on 26 October 2026; eligibility remains unconfirmed. Preserve the original brief
and [official-source provenance](official-sources.md).
