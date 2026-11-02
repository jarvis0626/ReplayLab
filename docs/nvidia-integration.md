# NVIDIA integration and live validation

Checked on 2 November 2026. The owner authorized NVIDIA-hosted Meta inference;
the direct Meta Model API remains unverified. The repository stays private.

The owner subsequently required a working Meta model for the deadline. A
[local Meta Llama OCR/text provider](local-meta-setup.md) now supplies that route
without using this cloud endpoint. A diagnostic Nemotron request established
that the saved NVIDIA key can make successful calls; Muse Glimmer's failures
remain model-specific evidence, not proof that the key is absent or invalid.

## Implemented

The cloud adapter supports explicit `nvidia` mode alongside mock, direct Meta,
and local Meta modes. NVIDIA uses
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
Only safe connection-establishment failures and HTTP 429 have bounded submission
retries. Timeouts, ambiguous disconnects, and HTTP 500/502/503/504 never resubmit a
possibly accepted generation. Errors omit upstream private messages. Logs contain
status, latency, and token counts without inputs or keys.
HTTP 202 responses now use bounded status polling without resubmitting the
generation. Polling identifiers are validated and redirects are rejected. Normal
Chat Completions POST requests omit a forced polling header; only status GET
requests use `NVCF-POLL-SECONDS: 5`.

Validation of this request-handling update: **427 backend tests passed** on
2 November 2026, including mocked polling, duplicate-submission prevention,
redirect rejection, concurrent diagnostics, and request-ID sanitization. Backend
and diagnostic-script Ruff checks passed. These offline checks do not establish
successful live NVIDIA inference.

Tutorial frames/transcripts are not sanitized by screen redaction. Review them
before cloud consent. NVIDIA trial processing/retention terms apply; Meta's
`store:false` and Files-expiration controls are not claimed for NVIDIA requests.

## Actual result: Muse Glimmer API inference is blocked

The owner demonstrated a successful NVIDIA Playground reply. Application API
requests on this machine still fail. Public catalog GET succeeded and listed
the requested model; unauthenticated POST returned 401. Authenticated text and
image probes each reached a 90-second timeout, streaming reached 45 seconds, and
minimal requests also timed out. The exact generated example timed out through
both HTTPX and the official OpenAI Python client. Those initial timeouts returned
no HTTP response or request ID. Later requests returned HTTP 504 with NVIDIA
request IDs; no live HTTP 202 was observed. The configured product model was not
silently replaced.

The owner replaced the key locally. An earlier application-path text probe at
**2026-11-02 16:29:02 UTC** ended with **HTTP 504 after 15,540.57 ms**. The final
probe using the safer production request handling at **16:32:43 UTC** timed out
after **35,766.98 ms** with a configured 35-second timeout. It received no HTTP
response, request ID, or model output; the diagnostic did not send an image after
text failed. Authenticated function metadata returned 200 and listed Muse
Glimmer as ACTIVE; this does not establish inference access or functioning
generation. Changing the key has not resolved the observed failure.

The bounded real evaluation attempted two controlled screenshots and stopped
after two timeouts. It scored **0 completed cases**; accuracy, uncertainty recall,
false certainty, and successful-response latency remain unknown. The earlier
20/20 local OCR result is a separate offline measurement. Actual statuses and
timings are preserved in [live checks](validation/nvidia-live-checks.json) and the
[NVIDIA evaluation report](../demo/evaluation/digital/nvidia-results.json).

The application/adapter is implemented and contract-tested, but successful live
Muse Glimmer inference and a Muse submission demo are **not verified**. The
existing [three-minute recording](v3-demo.md) remains explicitly offline and must
not be relabeled as NVIDIA inference. The cause of the API timeouts and gateway
errors is not established.

## Account and request diagnostics

The completed key replacement and Playground test have not resolved API access.
The next external action is to ask NVIDIA to trace the failed requests using the
[prepared support request](nvidia-support-request.md). It contains request IDs
and outcomes, with no credential. It has not been sent externally. The current
evidence does not identify a particular account permission or global outage.

To retry safely after NVIDIA resolves access or routing:

```powershell
.venv\Scripts\python.exe scripts/diagnose-nvidia.py --timeout-seconds 60 --consent-controlled-screenshot
```

The diagnostic reads the local server key, checks text first, and sends the
repository-owned synthetic CodeLab image only after text succeeds and the flag
is supplied. Its report is saved under ignored `.artifacts/nvidia-diagnosis.json`.
Run the consent-gated evaluation only when actual text and image inference work.
A green service status or a visible model catalog cannot establish that result.

Official sources checked:

- [NVIDIA model and generated example](https://build.nvidia.com/meta/muse-glimmer-30b)
- [Model capabilities](https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b)
- [Chat Completions parameters](https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b-infer)
- [Generic Integrate HTTP 202 status endpoint](https://docs.api.nvidia.com/nim/reference/baai-bge-m3-statuspolling)
- [API-key services](https://docs.nvidia.com/rag/latest/api-key.html)
- [Organization/user permissions](https://docs.nvidia.com/ngc/latest/ngc-user-guide.html)
