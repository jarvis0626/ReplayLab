# URGENT — REPLAYLAB NVIDIA API INTEGRATION & FINAL IMPLEMENTATION

You are my senior AI engineer and full-stack technical lead working on **ReplayLab**, my submission for the Meta Global AI Developer Hackathon 2026.

**Your job is to implement the remaining features, integrate NVIDIA-hosted Meta models, test the real application, and prepare it for submission. Do not stop at planning.**

The Meta Model API promotional credits have not arrived, so we are switching to NVIDIA's hosted Meta Muse Glimmer model.

## 1. API KEY SETUP

I have an NVIDIA API key.

**NVIDIA configuration:**

- Base URL: `https://integrate.api.nvidia.com/v1`
- Model: `meta/muse-glimmer-30b`
- API interface: OpenAI-compatible Chat Completions
- Environment variable: `NVIDIA_API_KEY`

Set up secure API key configuration.

1. Check whether `NVIDIA_API_KEY` already exists in the environment.
2. If not, create a local `.env` configuration and add `.env` to `.gitignore`.
3. Provide me with a secure way to enter my API key locally, without including it in the conversation, terminal history, committed code, or logs.
4. Use `python-dotenv` or equivalent to load the key.
5. Create `.env.example` with placeholder values.
6. Never print or expose the actual API key.
7. Never push secrets to GitHub.

If working in a cloud Codex environment, use its available secret configuration mechanism instead of asking me to paste the key into chat.

Do not proceed with live API requests until the key is configured.

## 2. INTEGRATE NVIDIA MUSE GLIMMER

Implement a fully functional NVIDIA inference provider in the existing ReplayLab backend.

Use the OpenAI-compatible client.

Verify NVIDIA's current official documentation for the precise model identifier, supported image input format, token limits, and request parameters.

Create the following capabilities:

**A. Screenshot Understanding**

Accept a screenshot from the user's screen and send it to Muse Glimmer.

Extract structured observations:

- Visible application
- Current window or panel
- Visible buttons
- Menu selections
- Dialogs
- Error messages
- Relevant text
- Visible UI state
- Evidence supporting each observation
- Uncertainty or missing information

Return structured JSON validated using Pydantic.

**B. Workflow Understanding**

Analyze frames extracted from a tutorial video.

Identify:

- Workflow steps
- Expected UI states
- Dependencies
- Reference screenshots
- Relevant actions
- Verification constraints

If Muse Glimmer does not support direct video input, extract frames locally using FFmpeg/OpenCV and analyze supported image inputs.

Do not invent unavailable model capabilities.

**C. Grounded Explanations**

Use Muse Glimmer to explain verification results.

The model must receive structured evidence and cannot override the verification engine's verdict.

**D. Provider Architecture**

Support:

- `AI_PROVIDER=nvidia`
- `AI_PROVIDER=meta`
- `AI_PROVIDER=mock`

Preserve existing provider integrations.

Show the active provider in the frontend.

Never silently substitute mocked inference for a failed real API call.

## 3. VERIFY THE API REALLY WORKS

Before implementing additional features:

1. Run a real text inference request.
2. Run a real image inference request.
3. Confirm responses from the actual NVIDIA endpoint.
4. Validate structured observation extraction.
5. Test error handling.
6. Measure response latency.
7. Confirm the frontend can receive live inference results.

If an API request fails, identify the cause and fix it when possible.

Do not claim integration success unless real requests execute successfully.

Cache successful inference responses to minimize API usage.

## 4. COMPLETE REPLAYLAB'S CORE FUNCTIONALITY

Inspect the current repository and preserve existing working components.

Prioritize the complete digital workflow:

**Tutorial → Step extraction → Workflow graph → Screen capture → AI observations → Verification → Corrective guidance.**

Required implementation:

- Upload tutorial videos.
- Extract reference frames and timestamps.
- Generate structured workflow steps.
- Display an interactive action graph.
- Allow user review and editing of steps.
- Capture the user's screen with explicit permission.
- Analyze actual screenshots using NVIDIA Muse Glimmer.
- Compare observed states against expected workflow states.
- Detect incorrect actions.
- Generate evidence-backed corrections.
- Recheck the user's screen after corrections.
- Advance when completion is verified.

The working demonstration should use a simple VS Code workflow, such as installing an extension.

Do not delay the core demonstration to add extra tutorial categories.

## 5. VERIFICATION ENGINE — MOST IMPORTANT

Implement and test three outcomes:

**PASS:** Sufficient evidence confirms the expected conditions.

**FAIL:** Sufficient evidence demonstrates a specific contradiction.

**UNCERTAIN:** The screenshot or model observations do not provide enough evidence.

Examples:

- Correct VS Code panel opened → PASS.
- Settings opened instead of Extensions → FAIL.
- Window obscured or ambiguous → UNCERTAIN.
- Tutorial interface differs from current software → UNCERTAIN, with a possible version-mismatch explanation.

Do not allow a low-confidence model guess to become a definitive PASS or FAIL.

The verification engine must use structured constraints and preserve inspectable evidence.

A model-generated description alone is not sufficient proof of completion.

## 6. PRESERVE PHYSICAL MODE

Retain the physical-task workflow and existing SAM 3.1 integration, if implemented.

Reuse the same workflow graph and verification result schemas.

Do not attempt to substitute Muse Glimmer for SAM 3.1 segmentation without validating equivalent functionality.

If SAM 3.1 access is unavailable, keep physical mode functional to the extent possible with clearly labeled local observations or mock fixtures.

Prioritize digital mode first.

## 7. EVALUATION

Create approximately 20 labeled verification cases:

- 5 correct steps
- 5 incorrect steps
- 5 ambiguous observations
- 5 interface/version mismatch scenarios

Run the real verification pipeline on actual captured screenshots wherever possible.

Measure:

- Three-class decision accuracy
- PASS/FAIL accuracy on decisive predictions
- False-certainty rate on ground-truth UNCERTAIN cases
- Uncertainty recall
- Response latency
- Per-class confusion matrix

Do not fabricate evaluation results or present mock tests as real-model accuracy.

Document actual successes, failures, limitations, and sample sizes.

## 8. HACKATHON DEMO

Prepare a reliable three-minute demonstration showing:

1. ReplayLab understands a tutorial.
2. It generates a structured workflow.
3. The user shares their screen.
4. The user intentionally performs an incorrect action.
5. ReplayLab detects the mistake using real Meta-model inference.
6. ReplayLab explains the correction.
7. The user fixes the mistake.
8. ReplayLab verifies completion.
9. An ambiguous observation produces UNCERTAIN.
10. Actual evaluation results are displayed.
11. A physical example is shown only if sufficiently functional.

Clearly document which Meta open-weight model is used, where it is hosted, and what was built during the hackathon.

## 9. PRIORITIES AND DEADLINE

The submission deadline is November 4, 2026, at 9 PM Eastern Time.

Prioritize:

**P0:** Real NVIDIA API integration and working digital verification.

**P1:** Evidence-backed uncertainty and real evaluation results.

**P2:** Physical-mode demonstration and UI-version mismatch handling.

**P3:** UI polish, documentation, deployment, and demo preparation.

Do not prioritize voice, overlays, autonomous clicks, or unnecessary extra features.

## 10. EXECUTION INSTRUCTIONS

Start by inspecting the current repository.

Then:

1. Identify the existing API provider architecture.
2. Configure secure NVIDIA credentials.
3. Test the actual NVIDIA endpoint.
4. Implement screenshot understanding.
5. Integrate it into ReplayLab's verification pipeline.
6. Complete the digital tutorial workflow.
7. Run end-to-end tests.
8. Fix implementation errors.
9. Execute real evaluation cases.
10. Prepare the public GitHub repository and submission materials.

Perform actual coding, not just documentation.

Run the application and tests.

Do not claim that code works without executing appropriate checks.

Do not rewrite completed features unnecessarily.

When external credentials are needed, give me the exact secure local setup instructions and continue independent work.

**Your immediate goal is to make ReplayLab's digital workflow use REAL NVIDIA-hosted Meta Muse Glimmer inference and demonstrate evidence-backed PASS, FAIL, and UNCERTAIN decisions.**

Start implementing immediately and continue through the highest-priority unfinished tasks.