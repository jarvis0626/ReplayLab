# Development and GitHub workflow

ReplayLab runs as a local single-user FastAPI server and React/Vite application.
Use the mock provider for the reproducible sample; an API key is not required.
The repository is private, and meaningful completed milestones should be reviewed,
tested, committed, and pushed without rewriting shared history.

Implementation before kickoff was explicitly authorized by the owner on
26 October 2026. Eligibility remains unconfirmed; the original planning-only gate
no longer blocks coding. [Official sources](official-sources.md) preserve that
provenance.

## Requirements and configuration

Use Python 3.11+ and a supported Node.js release: 22.12+ on the 22.x line or 24.x.
Install FFmpeg and FFprobe on PATH. Both are used for actual video processing and
sample generation. The frontend lockfile pins the installed dependency graph;
Python dependencies are listed in `apps/api/requirements.txt`.

The repository-root [README](../README.md) is the entry point for setup/start
commands and any convenience scripts. The equivalent manual workflow follows.
The API should run from `apps/api` so its `.env` file is found.

Windows PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r apps/api/requirements.txt
Copy-Item .env.example apps/api/.env
npm --prefix apps/web ci
```

Bash, from the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements.txt
cp .env.example apps/api/.env
npm --prefix apps/web ci
```

Copy the example only on first setup; preserve an existing local configuration.
It defaults to `AI_PROVIDER=mock`. `MODEL_API_KEY` is server-only; never add it to
frontend environment variables. Runtime storage defaults to `apps/api/data` and
can be moved with `DATA_DIR`.

## Run and verify

Run the API from `apps/api` with the virtual environment's Python:

```text
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Use `.venv/Scripts/python.exe` on Windows or `.venv/bin/python` on Unix from the
repository root, adjusting the relative path after changing directories. A second
terminal runs `npm --prefix apps/web run dev` from the root. Open
`http://127.0.0.1:5173`; Vite forwards `/api` to `http://127.0.0.1:8010`.
Health and interactive API docs are `/api/health` and `/docs` on port 8010.
Run one API worker because processing locks and provider selection are local to
that process.

From `apps/api`, run with the environment's Python:

```text
python -m pytest -q
python -m ruff check app tests
```

From the repository root:

```text
npm --prefix apps/web test
npm --prefix apps/web run build
```

The build includes TypeScript checking. See [test results](test-results.md) for
the actual commands and outcomes, and [evaluation](evaluation.md) for the
observation-fixture measurement. Tests do not need a live Meta key.

## Local data and provider changes

The API stores projects/attempts in SQLite and source videos, extracted frames,
and checkpoint images below its data directory. Those files remain until project
deletion. Deletion removes the project's media and stored project/attempt records;
it also clears the shared inference cache. Shared synthetic demo assets remain available. Runtime data is
ignored by Git. Avoid committing screenshots containing private user media.

Provider settings choose mock or Meta explicitly. Switching to Meta requires a
server key and consent before extraction or verification sends media. Missing or
failed credentials produce a visible error, not a mock fallback. Live provider
tests are a separate opt-in operation; follow [model usage](model-usage.md).

## Reviewed milestone workflow

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

Replace the placeholder with actual reviewed paths and run applicable checks
before committing. Verify the remote branch reached the intended commit. Do not
force-push, change repository visibility, delete remote branches, commit secrets,
or install background commit/push automation. Keep local environment files,
dependency folders, build output, uploads, databases, and caches out of commits.
