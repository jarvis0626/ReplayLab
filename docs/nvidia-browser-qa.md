# NVIDIA browser validation — 2 November 2026

The running React/FastAPI application was exercised in Chromium 148.0.7778.96
at 1440×1000 and 1024×1000. No API responses, observations, or verdicts were
replaced. Only the repository-owned CodeLab
[Extensions screenshot](../demo/evaluation/digital/screenshots/case-correct-market.png)
was sent, after explicit in-app NVIDIA screen consent. Credentials were neither
read by the browser test nor supplied through the UI.

**No successful NVIDIA inference was obtained.** The real screen-check returned
HTTP 502 with the safe message that NVIDIA timed out. The UI displayed the error,
returned no fabricated verdict, left completion at zero, and kept NVIDIA selected
and unverified. It did not silently use local OCR as a replacement model result.

| Check | Actual result |
| --- | --- |
| Provider status and model/host | NVIDIA configured, live access unverified; server-reported `meta/muse-glimmer-30b` and NVIDIA host |
| Screen consent | Share/upload disabled until separate per-project consent; no screenshot request before consent |
| One actual NVIDIA screen request | HTTP 502 timeout, zero progression, no successful integration claim |
| Explicit offline provider selection | Selecting Offline / mock through settings allowed actual local OCR to return PASS and complete the first checkpoint |
| NVIDIA evaluation report | 0 completed / 20 target, 2 failed attempts, 18 unattempted after the availability circuit opened; metrics remain N/A |
| Evaluation consent | Opening the report made no cloud inference request; Run evaluation remained disabled without its separate consent |
| Layout | Provider settings and NVIDIA evaluation fit both tested widths without horizontal overflow |
| Browser errors | Zero JavaScript page errors in the completed continuation phase |

The [browser report](assets/nvidia/browser-validation.json) records eight completed
continuation assertion groups and includes the separately preserved
[actual failed-request evidence](assets/nvidia/live-failure-validation.json).
The initial browser run completed the live timeout and no-progression assertions,
then stopped on a harness selector issue while choosing Offline / mock. After
fixing that selector, the remaining checks ran without repeating the paid cloud
request. A transient full-browser closure during the continuation was resolved
using Chromium's headless shell, which supports the manual review path used here.
The first request's exact UI timing was not preserved before the harness failure;
its latency is explicitly `null`, not an invented measurement.

The NVIDIA evaluation shown here is a read-only view of the actual failed
evaluation run. This browser check did not start another 20-case run. Provider
timeouts are recorded as unavailable cases, never filled in with UNCERTAIN
predictions or copied from the local OCR baseline.

## Captured application evidence

- [Configured but unverified provider](assets/nvidia/provider-unverified.png)
- [Separate screen consent](assets/nvidia/screen-consent-required.png)
- [Actual NVIDIA timeout](assets/nvidia/actual-nvidia-timeout.png)
- [Explicit local OCR recovery](assets/nvidia/explicit-offline-recovery.png)
- [Unavailable NVIDIA evaluation](assets/nvidia/nvidia-evaluation-unavailable.png)
- [Tablet provider settings](assets/nvidia/tablet-provider-settings.png)
- [Tablet evaluation](assets/nvidia/tablet-nvidia-evaluation.png)

## Reproduction and limits

Start the API and Vite preview, configure the server-only NVIDIA credential, and
install the optional Playwright browser tooling as described in the existing
[digital QA guide](digital-browser-qa.md). Run:

```powershell
python scripts/nvidia-browser-smoke.py
```

This failure-focused script makes one real consented screen request and expects
the currently observed unavailable-provider behavior; a different upstream result
must be inspected, not called a passed timeout test. For a local-only continuation
using already preserved failure evidence, use `--skip-live`; it sends no new
NVIDIA screenshot and records that limitation explicitly. The script deletes only
its own controlled project and restores NVIDIA mode. Preview processes belong to
the root task and were left running for its final checks.

Manual screenshot upload was exercised. A human-operated display picker, live tab
streaming with NVIDIA, successful model responses, real-model accuracy, and
third-party software installation were not validated. The existing
[three-minute offline walkthrough](v3-demo.md) remains intact. No replacement video
pretends that NVIDIA inference succeeded.
