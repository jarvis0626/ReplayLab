# Run ReplayLab with a local Meta model

Built with Llama. This mode runs **Meta Llama 3.2 3B Instruct** on the PC's CPU,
using a pinned community Q4_K_M GGUF conversion and portable llama.cpp. It works
without an NVIDIA GPU or cloud inference credits. Screenshots are read by actual
local OCR; Llama receives redacted text, not images. It is not Muse Glimmer or SAM.

## Start

From the repository root on Windows x64, after normal `npm.cmd run setup`:

```powershell
.venv\Scripts\python.exe scripts/setup-local-meta.py --activate
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. The local model API binds only to
`127.0.0.1:8083`; ReplayLab's API uses `127.0.0.1:8010`. The development launcher
starts the model when local Meta is selected. If a healthy instance already serves
the expected model, it reuses that instance. Ctrl+C stops services owned by that
development launch; a separately started model remains under its original owner.

Setup downloads approximately 2.02 GB of model weights and a 24.4 MB CPU runtime.
Both have pinned revisions and SHA256 checks. Files remain under ignored
`.artifacts/local-meta/`; no model weights, executables, or credentials are committed.
Activation explicitly selects `AI_PROVIDER=local_meta` in ignored `apps/api/.env`
and preserves existing NVIDIA and direct Meta credentials.

## What the model does

Local Meta proposes digital workflow steps from supplied timestamped transcripts
and real OCR extracted from sampled tutorial frames. Proposals must be reviewed
and approved before guided verification. Unsupported proposals are rejected.

During a screen check, local OCR supplies measured text, boxes, and recognition
confidence. Meta interprets a bounded set of OCR facts and can plan explanations
from existing evidence and approved corrections. Deterministic rules decide
PASS/FAIL/UNCERTAIN. Model output cannot invent observations, remove observed
counterevidence, change confidence, or override the verdict. A failed model call
is an error; it never silently becomes an offline or cloud result.

This mode does not understand unrecognized icons, hidden filesystem state, audio,
physical assembly geometry, or arbitrary visual appearance. CPU reasoning is
slower than local OCR alone. Screen checks and workflow proposals show measured
latency; this small development setup does not establish broad accuracy.

## Measured evidence

The [88-second local Meta recording](local-meta-demo.md) shows the real CPU path,
normal-speed waiting, and evidence-driven PASS/FAIL decisions.

The initial real local text request returned HTTP 200 in 586 ms. An initial OCR
reasoning request returned valid JSON in 9.02 seconds. Early integration checks
exposed slow verbose output and overly restrictive OCR selection; those failures
are retained separately from final browser validation.

See [browser validation](assets/local-meta/browser-validation.json) for actual
provider/model IDs, verdicts, timings, request counts, and limitations. This mode
uses a genuine Meta model but does not establish hackathon eligibility or satisfy
an unverified requirement to use a particular Meta API/model.

Final browser checks on 2 November used actual local OCR and actual Meta model
responses, without network mocking:

| Controlled screenshot | Deterministic outcome | Full request time |
| --- | --- | --- |
| Extensions Marketplace | PASS; first step completed | 28.18 s |
| Wrong Settings panel | FAIL; no progress | 17.84 s |

Both explanations used validated `local_meta_grounded_plan` responses. Twelve
browser assertions passed, with zero JavaScript errors and no nonlocal browser
requests. Desktop and tablet layouts were checked. Two authored simulation cases
are not a representative accuracy benchmark or a human screen-sharing test.

A separate [real API workflow check](validation/local-meta-workflow.json) generated
a two-step Meta proposal from an authored timestamped transcript in 44.14 seconds.
It remains unapproved in the local workspace as **Local Meta generated walkthrough**.
An attempted screen check before approval returned HTTP 409. This measures one
transcript proposal, not video understanding or extraction accuracy.

Final offline validation: **486 backend tests**, **52 frontend tests**, backend
and helper-script Ruff checks, TypeScript, and the frontend production build
passed. Model inference was measured separately from these mocked contract tests.

## Sources and licenses

- [Original Meta model](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct)
- [Pinned community quantization](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/tree/5ab33fa94d1d04e903623ae72c95d1696f09f9e8)
- [Pinned portable runtime](https://github.com/ggml-org/llama.cpp/releases/tag/b11960)
- [Model license, acceptable use policy, and attribution](third-party/llama3.2/README.md)
