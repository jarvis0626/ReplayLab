# NVIDIA API support request

Prepared locally on 2 November 2026; **not sent**. Copy the message below into the
[NVIDIA Developer Forums](https://forums.developer.nvidia.com/). Do not attach
`.env`, API keys, Authorization headers, or user screenshots.

## Subject

Muse Glimmer API times out or returns HTTP 504 after key replacement; Playground succeeds

## Message

Please trace these API requests and help determine why NVIDIA-hosted
`meta/muse-glimmer-30b` inference is failing from our Windows application.

- Endpoint: `POST https://integrate.api.nvidia.com/v1/chat/completions`.
- Authentication: locally configured NVIDIA API key. The key was replaced;
  inference still fails. No credential is included here.
- Earlier application-path text check: `2026-11-02T16:29:02.732272+00:00`,
  HTTP 504 after 15,540.57 ms total. No model response was received. The diagnostic
  skipped its image check after text failed.
- Final production-path check: `2026-11-02T16:32:43.401796+00:00`, timeout after
  35,766.98 ms with a configured 35-second timeout. No HTTP response or request ID
  was received, and no image was sent. This POST omitted a forced polling header.
- Earlier text and image requests reached read timeouts. The generated example
  also timed out using HTTPX and the official OpenAI Python client. Windows curl
  and HTTP/2 probes received HTTP 504.
- Public model listing returned HTTP 200 and included the requested model.
  Authenticated function listing returned HTTP 200 and showed
  `ai-muse-glimmer-30b` as ACTIVE. These metadata results do not prove generation.
- A logged-in NVIDIA Playground `hello` request succeeded. Application API calls
  have not produced a successful model response.
- The client handles documented HTTP 202 polling, but these live checks returned
  timeouts or HTTP 504 rather than HTTP 202. Only safe connection-establishment
  failures and HTTP 429 can retry a submission; ambiguous disconnects, timeouts,
  and HTTP 500/502/503/504 do not resubmit a possibly accepted generation.

Request IDs from 2 November 2026:

| Path | HTTP status | NVCF-REQID |
| --- | --- | --- |
| Direct Cloud Functions invocation | 504 | `cb225164-568a-4266-862d-8ed54d77b527` |
| Integrate endpoint over HTTP/2 | 504 | `73681f5c-7827-4570-8647-502cec9d33e5` |
| Integrate endpoint after key replacement | 504 | `f7ef4837-6a8d-4286-a446-890a9183fb6f` |

Function ID: `fd21cc19-b4ff-4949-ba07-90dd663c416a`.
Function version: `bcb668ff-7814-4970-bebd-0fe44ba0dc69`.
The HTTP/2 check also returned
`x-request-id: a8f4615d-f235-4e9c-bc5f-dc2983d0e2e5`.

Could you check API entitlement and upstream routing/execution for these request
IDs and identify the required correction? We have not established the root cause
and are not assuming that a particular permission or a global outage is involved.

## Supporting references

- [Official Muse Glimmer Chat Completions endpoint](https://docs.api.nvidia.com/nim/reference/meta-muse-glimmer-30b-infer)
- [Generic Integrate HTTP 202 status endpoint](https://docs.api.nvidia.com/nim/reference/baai-bge-m3-statuspolling)
- [Local validation evidence](validation/nvidia-live-checks.json)
- [Integration and safe retry instructions](nvidia-integration.md)
