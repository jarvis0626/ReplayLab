# NVIDIA integration and live validation

Checked on 2 November 2026. The owner authorized NVIDIA-hosted Meta inference;
the direct Meta Model API remains unverified. The repository stays private.

## Implemented

The server supports explicit `mock`, `meta`, and `nvidia` modes. NVIDIA uses
`meta/muse-glimmer-30b` at `https://integrate.api.nvidia.com/v1/chat/completions`,
with the documented OpenAI-compatible text/image messages. Screenshots pass local
OCR/privacy preparation first. NVIDIA returns Pydantic-validated observations;
deterministic rules retain authority over PASS/FAIL/UNCERTAIN. Model facts require
independent OCR corroboration to qualify for decisive text rules, and the model's
uncalibrated score can only reduce that evidence confidence. Unknown facts stay
unknown. Explanations select approved evidence/correction IDs, without changing
the verdict or rendering arbitrary model claims.

Tutorial understanding uses up to four actual FFmpeg-sampled frames and an
optional supplied transcript. This model is not presented as a direct video,
audio-transcription, or SAM segmentation endpoint. Human review and approval are
required. NVIDIA is explicitly rejected for physical segmentation; the existing
Meta SAM and labeled physical fixtures remain available through explicit provider
selection. No failed cloud inference silently becomes a mock result.

Provider/model/host and verified status are visible in the UI. Consent is bound
to the project and provider. A provider switch invalidates pending captures even
during multipart upload. Stop/revision guards still prevent late completion.
Concurrent requests retain their own response IDs, latency, and usage metadata.
Successful screen/plan results use bounded redacted RAM caches, not screenshot
files. Workflow proposal caches remain in ignored local storage.

## Secure configuration

From the repository root:

```powershell
.venv\Scripts\python.exe scripts/configure-nvidia.py
# To enter a replacement with hidden input:
.venv\Scripts\python.exe scripts/configure-nvidia.py --replace
```

The helper accepts a process environment key or uses a hidden prompt. It writes
only ignored `apps/api/.env`, never prints the credential, and keeps it out of
shell arguments/history. Restart the API after changing it. A key pasted into a
chat/screenshot should be replaced locally; do not paste the replacement back.
`.env.example` contains placeholders only. Normal Pydantic settings load process
environment variables ahead of the local dotenv file.

`NVIDIA_TIMEOUT_SECONDS` is bounded from 5 to 180 seconds (default 45),
`NVIDIA_MAX_TOKENS` defaults to 4096, and `NVIDIA_REASONING_EFFORT` defaults to low.
Timeouts are not automatically retried as new paid generations; transient
connection/HTTP failures have bounded retries. Errors omit upstream private
messages. Logs contain status, latency, and token counts without inputs or keys.

Tutorial frames/transcripts are not sanitized by screen redaction. Review them
before cloud consent. NVIDIA trial processing/retention terms apply; Meta's
`store:false` and Files-expiration controls are not claimed for NVIDIA requests.

## Actual result: API inference is blocked

The owner demonstrated a successful NVIDIA Playground reply. Application API
requests on this machine still timed out. Public catalog GET succeeded and listed
the requested model; unauthenticated POST returned 401. Authenticated text and
image probes each reached a 90-second timeout, streaming reached 45 seconds, and
minimal requests also timed out. The exact generated example timed out through
both HTTPX and the official OpenAI Python client. These failures returned no HTTP
response/request ID, so HTTP 202 polling was unavailable. The configured product model
was not silently replaced.

The bounded real evaluation attempted two controlled screenshots and stopped
after two timeouts. It scored **0 completed cases**; accuracy, uncertainty recall,
false certainty, and successful-response latency remain unknown. The earlier
20/20 local OCR result is a separate offline measurement. Actual statuses and
timings are preserved in [live checks](validation/nvidia-live-checks.json) and the
[NVIDIA evaluation report](../demo/evaluation/digital/nvidia-results.json).

The application/adapter is implemented and contract-tested, but successful live
NVIDIA inference and a real-model submission demo are **not verified**. The
existing [three-minute recording](v3-demo.md) remains explicitly offline and must
not be relabeled as NVIDIA inference. The API-timeout cause is not established.

## Account and request diagnostics

First try `Hello` in the model's NVIDIA Playground. A successful reply establishes
that interface's behavior, not the application's key-based API access. For key
permissions, NVIDIA documents **NGC Catalog** plus **Public API Endpoints** under
Services Included. Organization services and user roles can restrict availability.
Use an appropriate expiration and keep replacements local.

Rerun `scripts/probe-nvidia.py` after resolving API access. Run the consent-gated
evaluation only when actual text and image inference work. A green service status
or a visible model catalog is not a substitute for successful responses.

Official sources checked:

- [NVIDIA model and generated example](https://build.nvidia.com/meta/muse-glimmer-30b)
- [Model capabilities](https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b)
- [Chat Completions parameters](https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b-infer)
- [API-key services](https://docs.nvidia.com/rag/latest/api-key.html)
- [Organization/user permissions](https://docs.nvidia.com/ngc/latest/ngc-user-guide.html)
