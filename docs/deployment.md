# Local operation and deployment

The application is a single-user research preview. No public deployment or live Meta request is claimed by these instructions. The GitHub repository remains private.

## Run from source

Install Node.js 22.12+, Python 3.11+ (3.12 is used in CI), and FFmpeg with both `ffmpeg` and `ffprobe` on PATH. From the repository root:

```sh
npm run setup
npm run dev
```

Setup creates `.venv`, installs `apps/api/requirements.lock` when available (otherwise `requirements.txt`), and runs `npm ci` in `apps/web`. It checks FFmpeg before installation. It does not activate the virtual environment or copy credentials. Windows uses `python`; Linux/macOS use `python3` to create the environment.

If Windows PowerShell blocks `npm.ps1` under its execution policy, use `npm.cmd run setup`, `npm.cmd run dev`, and `npm.cmd run check`; no policy change is needed.

The frontend is at <http://127.0.0.1:5173>; the API health check is <http://127.0.0.1:8010/api/health>. Vite proxies `/api` to the backend. Ctrl+C stops both development services and their child processes. A failed service also stops its companion. Default source-mode data is under `apps/api/data`; use `DATA_DIR` to choose another local directory.

For Meta mode, copy `.env.example` to `apps/api/.env`, configure `MODEL_API_KEY` on the server, and choose the provider in the application. Cloud processing still requires explicit in-app consent. Keys are never part of the frontend build. Mock mode uses known labeled fixtures and returns UNCERTAIN for unrecognized images.

Validate the working tree and export API contracts:

```sh
npm run check
npm run contracts
```

Checks run backend pytest and Ruff, frontend tests, and the production build. The contract export creates `packages/contracts/openapi.json` using temporary storage. CI runs these backend/frontend checks on Ubuntu with Python 3.12, Node 22, and FFmpeg; CI execution is separate from local validation.

## Docker Compose

Docker must be running. From the repository root:

```sh
docker compose up --build
```

Open <http://localhost:8080>. Only the frontend binds a host port, restricted to `127.0.0.1`. Nginx serves the production SPA and proxies `/api` to the API container on port 8010. The API runs as an unprivileged user with one worker, FFmpeg installed, and persistent data in `/data`. Health checks gate frontend startup. Requests allow 102 MB including multipart overhead; API media limits remain enforced separately. The reverse proxy waits up to 180 seconds for upstream activity.

Compose defaults to mock mode. To configure Meta, set `MODEL_API_KEY` in your shell or a root `.env` file and optionally set `AI_PROVIDER=meta`. Compose reads that root file; the source-mode API instead reads `apps/api/.env`. Both files are excluded from Docker build context and Git. Do not bake keys into either image. In-app consent remains required in Meta mode.

The named `replaylab-data` volume retains uploads, SQLite data, generated fixtures, and inference caches when containers stop or are recreated. `docker compose down` stops and removes containers while preserving the volume. Deleting a project through the application removes its local project media and records; consult the application's privacy notice for cache and cloud retention behavior. Back up the volume only when you intend to retain its private contents. Deleting a Docker volume permanently deletes its stored data.

## External hosting

Keep this single-user service behind an authentication gateway and HTTPS before exposing it beyond localhost. The API has no multi-user authorization model. Preserve same-origin `/api` proxying and persistent writable storage, run one API worker, and supply credentials through your host's secret configuration. Camera capture requires localhost or HTTPS. A production service with independent users requires authentication, authorization, isolated storage, and a durable job queue before shared use.

Validate the hosted health endpoint, video playback and reference frames, a complete mock workflow, project deletion, and consent handling on the actual host. Live Meta availability, permissions, credentials, billing, and model results need separate execution checks. Creating these container files does not establish a deployed service or successful live integration.
