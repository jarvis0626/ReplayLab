# NVIDIA-hosted model evaluation

## Recorded run — 2 November 2026

The [actual report](../demo/evaluation/digital/nvidia-results.json) contains
**0 completed cases out of 20**. Two repository-owned screenshots were attempted
with a 10-second inference timeout; both timed out. Processing times including
local OCR were 13049.26 ms and 12217.54 ms. The two-failure circuit prevented the
remaining 18 submissions. No prediction, accuracy, uncertainty recall,
false-certainty score, or successful-response latency is manufactured from these
failures. All such metrics remain unknown. The earlier local OCR 20/20 result
remains separate. [Live checks](validation/nvidia-live-checks.json) also preserve
the failed text/image/streaming/client diagnostics.

The NVIDIA suite reuses the frozen 20-case controlled CodeLab challenge from
[digital evaluation](digital-evaluation.md). The local OCR measurement remains
separate. Opening this suite never sends an image or calls a model. Until an
actual NVIDIA run exists, it displays **zero completed cases** and unknown
metrics, rather than copying the local OCR results.

## Actual inference path

An explicitly authorized run reads only the repository-owned screenshots, checks
their frozen SHA-256 hashes, performs local OCR/privacy preparation, sends the
supported image input to the configured NVIDIA-hosted model, validates its
structured observation, and applies the deterministic screen rules. Neither the
observer nor verifier receives the expected classification. Model observations
cannot override the rules or manufacture a completion verdict.

Each scored case must carry a validated NVIDIA response provenance. A local-only
or mock result, unavailable inference, changed screenshot, or failed response is
recorded as skipped, with no fabricated verdict. Authentication, billing, access,
and unavailable-model errors stop further requests; remaining cases are marked
unattempted. A run contains at most 20 cases; the provider's bounded transient
retry policy can generate more than one HTTP attempt for a case.

Two consecutive connection, timeout, upstream, pending, or rate-limit failures
open a failure circuit. No more images are submitted in that run. The report
preserves the two actual failed attempts and marks the remaining cases
unattempted, with no predicted verdicts or accuracy claim. A validated successful
observation resets this consecutive-failure counter.

The report records the actual configured model and NVIDIA host, time, completed
and attempted counts, expected/predicted verdicts, visible evidence, constraints,
failure notes, confusion matrix, accuracy, decisive accuracy, false certainty,
uncertainty recall, PASS/FAIL swaps, and latency. Cache hits and fresh observations
are counted separately, with a separate uncached latency sample. Validated model
cache reuse is not new cloud inference and is labeled accordingly.

## Run locally

Configure the server-only `NVIDIA_API_KEY` using the secure local setup. Never
put it in a command, source file, screenshot, or committed environment file.
The CLI explicitly authorizes only this bounded repository-owned dataset:

```powershell
.venv\Scripts\python.exe scripts/evaluate-nvidia.py --consent-controlled-screenshots
```

For a bounded service-availability diagnosis, add `--timeout-seconds 10`.
Overrides must be 5–180 seconds. Without an override, the CLI and API use the
server's `NVIDIA_TIMEOUT_SECONDS` (default 45), `NVIDIA_MAX_TOKENS` (default 4096),
and `NVIDIA_REASONING_EFFORT` (default `low`). A provider timeout is not a model
UNCERTAIN verdict: it remains an unscored failed attempt.

It writes the report to ignored
`apps/api/data/evaluation/nvidia-latest.json`. To preserve an actual measured run
for review, inspect the evidence and then use
`--output demo/evaluation/digital/nvidia-results.json`. Do not replace the
original local OCR `baseline-results.json`.

The Evaluation page reads `GET /api/evaluation/nvidia`. Running it explicitly
requires `POST /api/evaluation/nvidia/run` with `{"cloud_consent": true}`. The
server refuses the request without consent or configured credentials. Report
loading checks the dataset fingerprint, provider mode, model, and host so a
different configuration is not silently presented as the selected model's result.

## Scope and pending results

The labels were authored by the implementing coding agent before inference and
have not been independently reviewed by human annotators. CodeLab is a controlled
software simulation; these cases do not measure a real extension installation,
unseen applications, tutorial extraction, or physical SAM performance. Combining
OCR, model interpretation, and deterministic constraints measures the complete
observation/verification path, rather than standalone model accuracy.

Latency includes preparation, OCR, NVIDIA request or validated cache lookup, and
deterministic verification. It excludes browser capture, upload to ReplayLab,
human interaction, and explanation generation. The small dataset shares the demo
application and vocabulary, so even perfect agreement would not establish broad
accuracy or calibrated confidence.

Actual live counts and measured results must come from the generated report.
Mock-transport tests validate schema/error/orchestration behavior and are never
reported as NVIDIA model accuracy.
