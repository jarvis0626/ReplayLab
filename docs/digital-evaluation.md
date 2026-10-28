# Digital screenshot evaluation

The ReplayLab 3 challenge set contains **20 actual Chromium screenshots** of the local CodeLab extension simulation: five correct checkpoints, five visibly wrong states, five ambiguous views, and five explicit interface-version differences. The predictions use real local RapidOCR/ONNX inference and deterministic screen constraints. They do not measure Meta model accuracy, tutorial extraction quality, or real extension installation.

The coding agent authored the expected labels in [label-plan.json](../demo/evaluation/digital/label-plan.json) before screenshot capture and before inference. The capture script never calls the observer or verifier. Labels are not fed to either component, and disagreements remain in the report. These are **not independently human-labeled cases**. Independent human review and unseen applications remain future work.

## Measured result

The [checked-in measurement](../demo/evaluation/digital/baseline-results.json) was produced on 28 October 2026 with Chromium 148, Python 3.12.3, Windows, and the pinned local OCR dependencies. The suite contains 20 completed cases and no skipped cases.

| Metric | Measured result | Denominator |
| --- | --- | --- |
| Three-class agreement | 20/20 (100%) | All completed cases |
| Accuracy on decisive predictions | 10/10 (100%) | All PASS/FAIL predictions, including any made on uncertain ground truth |
| False-certainty rate | 0/10 (0%) | Ground-truth UNCERTAIN cases |
| Uncertainty recall | 10/10 (100%) | Ground-truth UNCERTAIN cases |
| PASS/FAIL swaps | 0 | PASS predicted FAIL plus FAIL predicted PASS |
| Median processing latency | 2170.34 ms | 20 local screenshot submissions |
| 95th-percentile processing latency | 2928.84 ms | 20 submissions; nearest-rank percentile |

Rows are ground truth; columns are predictions:

| Ground truth | PASS | FAIL | UNCERTAIN |
| --- | ---: | ---: | ---: |
| PASS | 5 | 0 | 0 |
| FAIL | 0 | 5 | 0 |
| UNCERTAIN | 0 | 0 | 10 |

Each case records the expected workflow conditions, screenshot SHA-256, expected and predicted verdicts, OCR text, constraint evaluations, explanation, evidence, processing latency, and any failure notes. Screenshot hashes cover exact binary bytes. The JSON manifest hash normalizes CRLF to LF so Git newline conversion does not invalidate a measurement on another operating system. A screenshot's pixels may be reused for a different checkpoint: an uninstalled detail screen is correct for reviewing details and wrong for claiming installation. The case count does not mean 20 independent application environments.

The five explicit version cases show CodeLab 2.0 against a CodeLab 1.0 reference. They yield UNCERTAIN even when other labels match or a menu differs, because the interface comparison needs review. The five ambiguous cases show an unrelated welcome view, an unrelated search result, an opaque privacy region, a crop containing application chrome only, and a strongly blurred content region. All are visibly controlled transformations applied in the browser before capture, rather than fabricated observations.

## Reproduce

After `npm run setup`, run the existing dataset without starting a browser or providing API credentials:

```powershell
.venv\Scripts\python.exe scripts/evaluate-digital.py
```

The report is written to ignored `apps/api/data/evaluation/digital-latest.json`. The Evaluation page reads it with `GET /api/evaluation/digital`; **Run digital evaluation** calls `POST /api/evaluation/digital/run`. A fresh installation displays the checked-in measurement until a local rerun exists. Actual failed cases are retained; missing or changed images and unavailable OCR produce a `skipped` entry, not a fabricated prediction or a filled-in sample count. Empty denominators are `null`, not an invented zero or perfect score.

To capture a new dataset from the actual target UI, start `npm run dev` and install the optional browser tooling in system Python:

```powershell
python -m pip install playwright==1.60.0
python -m playwright install chromium
python scripts/capture-digital-evaluation.py
.venv\Scripts\python.exe scripts/evaluate-digital.py
```

Capture writes only CodeLab screenshots under `demo/evaluation/digital/screenshots`, freezes the workflow and pre-labeled case manifest, and records browser version. It does not capture a desktop, use a user's windows, or download tutorial media. To intentionally replace the checked-in measured baseline after reviewing a new capture, pass `--output demo/evaluation/digital/baseline-results.json` to the evaluation script. Normal reruns leave the baseline untouched.

## Measurement scope and limits

The dataset is separate from `demo/fixtures/evaluation.json`, the original 25-case physical rule suite. That original suite starts from curated normalized observations and does not test screenshot detection. The digital suite starts from rendered browser pixels; its workflow remains the reviewed CodeLab mock template. Neither suite is live Meta evaluation.

The evaluator clears the sanitized in-memory observation cache before each case so duplicate pixels do not become artificial sub-millisecond OCR samples. A run includes image decode, OCR, deterministic verification, and result construction. The first sample may include model initialization. Timing excludes browser capture, upload transport, user think time, and remote-model latency; hardware and concurrent CPU activity affect results.

No errors were observed in this particular small run. That result establishes regression behavior for this authored controlled challenge set. It does not establish broad real-world accuracy, human independence of annotation, calibrated OCR scores, or generalization to unseen software. The dataset shares the CodeLab application and expected vocabulary with the demonstration, and was produced by the same agent implementing the system. A future external evaluation should use independent reviewers, frozen labels, unseen tutorials, varied software versions, repeated trials, and different capture conditions.
