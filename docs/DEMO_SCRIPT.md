# Tutorial demonstration narration

[Watch the current tutorial proof](../ReplayLab_Meta_Hackathon_Demo.mp4):
**45.633 seconds**, one continuous actual app take. Upload, live generation,
review/approval, a real shared-tab check, and completed progress are visible.

The voice is **en-US-GuyNeural** at its normal speaking rate. It starts directly
with the tutorial; there is no spoken disclaimer. Synthetic narration is
identified in the MP4 metadata and these docs. Only the narration text is sent
to the speech service. The original video packets and timestamps are unchanged.

| Window (seconds) | Exact spoken text |
| --- | --- |
| 0.5-12.1 | Upload a tutorial and watch it play. Replay Lab turns its instructions into a checkpoint you can practice. |
| 12.9-22.4 | Meta Llama generates a checkpoint from the tutorial's transcript and sampled frame. Review the result, then approve it. |
| 23.4-37.2 | Now follow the tutorial in the shared Code Lab tab. Replay Lab reads the actual screen and checks its visible heading against the approved checkpoint. |
| 38.2-45.2 | Pass. The screen matches the tutorial, and the graph marks the checkpoint complete. |

The actual workflow appears at 20.724s, the screen check returns PASS at 37.705s,
and the completed graph appears at 42.686s. Narration announces PASS afterwards.
See [recording and verification](TUTORIAL_PROOF.md) and the
[neural audio report](validation/tutorial-proof-voiceover.json).

The earlier three-minute prepared-workflow script remains in
[PREPARED_DEMO_SCRIPT.md](PREPARED_DEMO_SCRIPT.md), paired with its archived video.
