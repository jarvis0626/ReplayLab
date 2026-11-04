# Run the tutorial demonstration

[Current narrated proof](../ReplayLab_Meta_Hackathon_Demo.mp4): **45.633 s,
1920 x 1080, H.264,30 FPS, AAC 48 kHz**. It starts at tutorial upload and shows
new model generation during the same take, followed by real shared-screen PASS.
See [actual measured evidence](TUTORIAL_PROOF.md).

Start or reuse the installed laptop setup from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_demo.ps1
```

The current profile is **Meta Llama 3.2 1B Instruct**, Q4_K_M, running locally
with the pinned Vulkan runtime on AMD device Vulkan1. The larger3B CPU profile
remains an explicit fallback. The launcher checks the actual configured model
and never relabels 1B as 3B. This laptop is already configured. To reproduce setup:

```powershell
.venv\Scripts\python.exe scripts/setup-local-meta.py --model-size 1b --backend vulkan --device Vulkan1 --context-size 2048 --activate
```

Existing cloud credentials are preserved in ignored server configuration; this
profile uses no cloud inference. Original Meta notices remain under
`docs/third-party/llama3.2/`. Built with Llama.

A fresh one-checkpoint project named **Hackathon live demonstration - ready
tutorial practice** is available, unapproved at 0/1. The recorded completed task
is retained separately. Model proposals require review before approval.

To record a new real tutorial proof with the owned source file on this laptop:

```powershell
python scripts/record_tutorial_proof.py --tutorial-video .artifacts/tutorial-proof-source/Open-Extensions-Marketplace-tutorial.mp4 --model meta-llama/Llama-3.2-1B-Instruct --checks pass
```

The helper creates a new empty project, uploads/plays the real tutorial, saves
its timestamped transcript, requests new Meta generation, shows the generated
graph, reviews/approves it through the UI, and checks a real CodeLab tab stream.
It rejects incorrect model goals and unexpected verification results. It never
injects the desired expected state or outcome. CodeLab is a labeled simulation.

Four frames are extracted from the source video. For a single quoted goal in
one transcript segment, one representative frame is used for OCR and this
sampling is recorded in provenance. Broader tutorials keep a four-frame budget.
Initial model proposals use source text goals with no inferred counterstates;
reviewers can add alternatives or contradictory states explicitly.

The optional neural speech client stays under ignored repository artifacts:

```powershell
python -m pip install --target .artifacts/tts-client edge-tts==7.3.1
python scripts/narrate_tutorial_proof.py --source .artifacts/tutorial-proof-20261104T152636Z/tutorial-proof.mp4 --plan docs/tutorial-proof-narration.json
```

The exact plan is pinned to the accepted source hash and timing. A fresh take
requires updating its narration windows/hash after review. The mux helper
backs up the previous main video, validates each sentence window, copies H.264
video unchanged, adds AAC narration, verifies exact video-packet and timestamp
hashes, and fully decodes both streams. Only narration text goes online. No
application screenshots, video, transcripts, credentials or model media go to
the speech service. Synthetic voice is disclosed in metadata/docs.

The older three-minute prepared-workflow example is archived as
[prepared-workflow-demo.mp4](assets/prepared-workflow-demo.mp4), with its
[original setup](PREPARED_DEMO_SETUP.md). It is not labeled as live extraction.
