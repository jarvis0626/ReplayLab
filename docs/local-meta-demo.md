# Local Meta demonstration

[Watch the 87.88-second recording](assets/local-meta/demo.mp4).

This is a real, silent browser recording of ReplayLab using **Meta Llama 3.2 3B
Instruct on the local CPU**, with actual local OCR. Waiting is recorded at normal
speed; no inference responses, verdicts, or progress indicators were substituted.
Built with Llama.

| Time | What is shown |
| --- | --- |
| 0:01 | Local model, OCR/text disclosure, and attribution |
| 0:04 | Existing Meta-generated workflow reviewed read-only; approval stays pending |
| 0:12 | Owned Marketplace screenshot submitted on a separate approved CodeLab template |
| 0:41 | Actual PASS and first-step progress |
| 0:53 | Owned wrong-panel screenshot submitted on another approved CodeLab template |
| 1:19 | Actual FAIL with no progress and an evidence-grounded correction |

The actual screen requests took 28.45 and 26.45 seconds. Two fresh observation
response IDs are recorded. Each submission can also request a Meta explanation
plan; the bounded explanation cache can reuse a validated plan, so the exact
number of fresh underlying explanation calls is not claimed. The
[recording report](assets/local-meta/demo-recording.json) contains model IDs,
observations, rule results, timing, cleanup, and limitations. No JavaScript errors
or nonlocal browser requests occurred.

The generated proposal was created before recording and remains unapproved and
unchanged. The screen tests use separate, approved, developer-authored simulation
templates. CodeLab simulates software changes; this is not a real extension
installation, Meta vision/SAM inference, an accuracy benchmark, or proof of
hackathon eligibility. The original [three-minute offline walkthrough](v3-demo.md)
remains available with its original disclosures.

To reproduce after [local setup](local-meta-setup.md), use a local Python with
Playwright plus installed Chromium, FFmpeg, and FFprobe:

```powershell
python scripts/record-local-meta-demo.py --review-project <unapproved-local-meta-project-id>
```

The script requires an existing unapproved Meta-generated project, leaves it
untouched, creates and deletes only its own test projects, and limits itself to
two screenshot submissions. Intermediate recordings and conversion logs remain
under ignored `.artifacts/`; only the final MP4 and safe report are published.
