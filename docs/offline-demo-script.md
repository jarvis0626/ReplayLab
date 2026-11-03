# Three-minute demonstration script

An [actual silent browser recording](assets/demo.mp4) is now available: 180.000
seconds of the working local application in **MOCK MODE**. It has no narration
track; the suggested narration below is separate. The recording has not been
uploaded to a public video service. [Browser QA](browser-qa.md) records its verified
metadata and checks. The synthetic template and supplied fixture observations are
not live Meta inference.

Before recording, start the API/frontend, confirm `/api/health`, open the dashboard,
and keep a fresh sample project available. The first sample generation may take
longer while FFmpeg creates the video. Keep browser zoom readable and avoid
showing credentials or private media. Use [test results](test-results.md) and
[evaluation](evaluation.md) for current verified claims.

| Time | Screen action | Suggested narration |
| --- | --- | --- |
| 0:00-0:20 | Dashboard; point to the MOCK MODE badge | "ReplayLab turns a reviewed task into visual practice checkpoints. This recording uses an offline synthetic assembly with known observations. Live Meta account access has not been verified." |
| 0:20-0:40 | Choose **Explore the sample project**; play part of the video and select a timestamped frame | "This is an actual generated video, and these are real extracted frames. The offline task steps are a fixed four-block template; they are not inferred from an uploaded video." |
| 0:40-1:00 | Open **Task & graph**; select the second step; show its prerequisite, reference, and rules; approve the reviewed task | "The user reviews the objects, timestamps, dependencies, and observable rules. Practice requires approval. Editing the task resets approval and progress." |
| 1:00-1:25 | **Guided practice**: use fixture **First checkpoint**, then **Verify checkpoint**; show PASS and move to step two | "These supplied fixture observations establish that the approved visible requirements hold. PASS unlocks the dependent checkpoint. The verifier uses rules and evidence, not a requested outcome." |
| 1:25-1:50 | On step two, use **Blue block to the right**, verify, and show the failed rule/correction | "Here the blue block is visibly in the wrong relation to red. The deterministic engine reports the mismatch and the correction. This does not complete the step." |
| 1:50-2:10 | Use **Obstructed camera view**, verify, then show UNCERTAIN | "Insufficient visibility and an unsuitable view are not enough to judge completion. ReplayLab asks for clearer evidence instead of treating a missing detection as a confirmed failure." |
| 2:10-2:30 | Use **Second checkpoint**, verify; show PASS, observation overlay, and attempt history | "The corrected known fixture satisfies the reviewed relationships. Attempts and progress persist. An arbitrary webcam or uploaded image in mock mode has no known observations and remains uncertain." |
| 2:30-2:50 | Open **Evaluation**; show cases and confusion matrix | "The deterministic engine matched 25 of 25 curated observation scenarios: ten pass, six fail, nine uncertain. This is fixture agreement, not model detection accuracy or a real-world benchmark." |
| 2:50-3:00 | Show provider settings briefly without enabling cloud consent | "The documented Muse Spark and SAM adapter is implemented with explicit consent and visible failures. Credentialed live validation and hosted-demo verification remain separate work." |

If an action takes longer, shorten narration rather than hiding an error or
claiming a result before it appears. Keep the fixture disclosure visible in the
recording. Do not use the name of a fixture as proof of its verdict: inspect the
returned rule diagnostics. A filename-only rename cannot create known fixture
observations; the mock provider compares decoded pixels.

For an extended walkthrough, complete steps three and four with **Third
checkpoint** and **Four-block reference**, reload to show persistence, then
demonstrate task edits requiring renewed approval. The short recording need not
claim all four steps were completed if only two were shown.
