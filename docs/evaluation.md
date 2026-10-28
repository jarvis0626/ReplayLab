# Evaluation: what the measured result means

ReplayLab 3.0 also provides a separate [20-case digital screenshot evaluation](digital-evaluation.md)
with actual local OCR, uncertainty/false-certainty metrics, latency, and per-case
screen evidence. The physical observation-fixture results below remain separate;
neither dataset measures live Meta model accuracy.

ReplayLab currently measures deterministic rule behavior over 25 curated
normalized-observation scenarios. An actual local run matched **25 of 25 expected
verdicts**. This is agreement on supplied observations; it does not measure Muse
video understanding, SAM detection accuracy, camera performance, or arbitrary
real-world assemblies.

The dataset is [demo/fixtures/evaluation.json](../demo/fixtures/evaluation.json).
The runner is `apps/api/app/services/evaluation.py`. The Evaluation tab calls
`GET /api/projects/{project_id}/evaluation` and shows each expected/predicted
verdict, its explanation, and this confusion matrix:

| Expected / predicted | PASS | FAIL | UNCERTAIN |
| --- | ---: | ---: | ---: |
| PASS | 10 | 0 | 0 |
| FAIL | 0 | 6 | 0 |
| UNCERTAIN | 0 | 0 | 9 |

Rows are expected labels; columns are predicted labels. The field named
`accuracy` in the endpoint is the fraction of these labels that match. It should
be presented as curated-fixture agreement rather than general model accuracy.
See [test results](test-results.md) for the validation record.

## Scenario coverage

The scenarios include reliable presence and complete-scene absence; low/unknown
detection confidence; each positional direction; a tolerance boundary; proximity
and separation; alignment and misalignment; independently reliable, wrong, and
unknown color; correct/extra/incompletely observed counts; occlusion; poor image
quality; camera mismatch; and missing/visible objects in incomplete scenes.

Observation confidence, visibility, coverage, image quality, comparability, and
complete-detection flags are explicit fixture annotations. They are not measured
Meta outputs. The runner validates them through the same domain schemas and calls
the same `verify` function used for checkpoints. The evaluation JSON is a runtime
input and must remain included in deployment artifacts, not just test folders.

## Evidence thresholds

Both reference and checkpoint require visibility and image quality at least
0.65, with camera comparability explicitly true. A reliable detection needs
confidence at least 0.75. Missing confidence stays unknown.

Absence and exact counts need checkpoint coverage at least 0.90, visibility at
least 0.85, image quality at least 0.75, and
`provenance.detection_complete=true`. Low-confidence candidate detections cannot
be counted as confirmed absence. More reliable distinct detections than the
approved count can establish a mismatch without proving scene completeness.
Overlapping boxes or repeated track identities remain ambiguous for exact count.

Directional rules compare normalized centers and reserve a tolerance band for
uncertainty. Alignment and proximity also have uncertainty margins. Color needs
its own observed color and confidence; a label containing "red" alone is not a
color measurement. These thresholds are controlled prototype policy, not a
calibrated probability of correctness.

One evidenced mismatch can establish FAIL while other rules remain uncertain.
PASS requires all approved rules to pass. Global visibility/quality/view failures
produce UNCERTAIN before geometric rules are evaluated.

## Reproduce and extend

With the API virtual environment active, from `apps/api`:

```text
python -c "import json; from app.services.evaluation import run_evaluation; print(json.dumps(run_evaluation(), indent=2))"
python -m pytest tests/test_verification.py -q
```

The UI/API evaluation does not require cloud consent or provider credentials;
it always uses the curated mock dataset. To extend it, add independently labeled
observations and expected verdicts to the JSON, preserve unknown fields honestly,
and include edge cases that could disprove the policy rather than copies of
implementation formulas.

Real-media validation remains outstanding. It needs separately labeled videos
and checkpoints, credentialed model runs with consent, false-pass/false-fail and
uncertainty analysis, object/mask measurements, sample counts, and latency/error
reporting. This small deliberately constructed set is not a held-out benchmark,
and it cannot establish physical attachment or occluded geometry.
