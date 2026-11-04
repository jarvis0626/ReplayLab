# Three-minute tutorial demonstration narration

[Watch the full narrated take](../ReplayLab_Meta_Hackathon_Demo.mp4):
**179.066667 seconds (2:59.07)**. The exact spoken plan below is pinned to the
accepted continuous source video. All twelve synthesized segments fit their
scene windows, and the complete narrated audio/video file passed decoding.
The [voiceover report](validation/three-minute-tutorial-voiceover.json) records
matching original/output video packets and timestamps.

The voice is **en-US-GuyNeural**, at its normal speaking rate. Narration starts
with the tutorial upload. Synthetic narration is disclosed in MP4 metadata and
documentation. Only the narration text goes to the speech service.

| Window (seconds) | Exact spoken text |
| --- | --- |
| 0.6-18.8 | I upload and play the tutorial. It shows opening Extensions Marketplace in CodeLab. ReplayLab will turn that demonstrated action into a checkpoint we can verify while practicing. |
| 20.6-34.2 | Generate task steps makes a fresh request to Meta Llama. It uses the timestamped transcript and text read from an actual tutorial frame. The proposed workflow appears from that source. |
| 35.8-41.8 | The graph shows our tutorial checkpoint and expected Marketplace heading. |
| 42.8-54.1 | The proposed Marketplace goal stays intact. During review, I add Preferences as a known wrong destination, then approve the task before guided practice. |
| 55.6-62.4 | I share the actual target tab. Settings is open instead of the Marketplace. |
| 63.8-82.5 | ReplayLab returns FAIL. The evidence shows Preferences, the contradictory heading we approved. The correction asks us to return to Extensions Marketplace. This decision comes from observed text and the reviewed rule. |
| 85.8-95.0 | I follow that correction by opening Extensions in the same shared tab, then request a fresh check of the changed screen. |
| 96.3-110.8 | Now the Marketplace heading is visible, so verification returns PASS. The checkpoint becomes complete because its evidence satisfies the approved rule. Simply changing screens did not mark it done. |
| 114.9-127.2 | Next I switch to Explorer and request another observation. This view does not show the expected Marketplace heading, and we should not infer success from the previous screen. |
| 128.5-138.4 | This new view is UNCERTAIN. It proves neither the target nor a known contradiction. Earlier verified progress stays complete. |
| 141.3-157.2 | This separate dashboard reports twenty controlled OCR cases, with twenty matching labels. It also shows uncertainty recall, false certainty, and measured latency. These results are limited to this dataset. |
| 159.0-178.3 | This runs on my laptop using Meta Llama 3.2, one billion parameters, accelerated by AMD Vulkan. OCR reads pixels; Llama reasons over the text. The original tutorial checkpoint is now verified in the graph. |

The actual FAIL appears at **62.994 s**, PASS at **95.523 s**, and UNCERTAIN at
**127.720 s**. Their spoken verdicts begin afterwards. The tutorial plays to its
end, the proposed source goal is retained, and the Preferences counterstate is
explicitly identified as a reviewer addition. The later uncertain observation
does not erase the earlier proven completion.

The [JSON narration plan](three-minute-narration.json) is the source of exact
spoken text and timing. Its source hash must match the accepted recording.
Speech must fit the measured windows at its natural rate; shorten text when
needed and preserve the original video's speed, frames, and timing.

See [the complete demonstration evidence](THREE_MINUTE_DEMO.md) and
[recording report](validation/three-minute-tutorial-recording.json).
The earlier [short proof](TUTORIAL_PROOF.md) and
[prepared-workflow script](PREPARED_DEMO_SCRIPT.md) retain separate evidence.
