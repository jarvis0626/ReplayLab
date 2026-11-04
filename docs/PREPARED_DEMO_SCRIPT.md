# ReplayLab: timed synthetic narration

Accepted recording: [ReplayLab_Meta_Hackathon_Demo.mp4](assets/prepared-workflow-demo.mp4),
**176.4 seconds**, with its original continuous video and a synchronized synthetic
voiceover added afterward at the owner's request. Microsoft Zira Desktop generates
the narration locally at normal rate **0**. The opening sentence discloses the
synthetic narration. The H.264 video packets are copied unchanged; every scene,
frame, and inference wait remains at its original speed.

Actual verdict appearances are FAIL at **1:09.6**, corrected PASS at **1:43.3**,
and UNCERTAIN at **2:18.2**. Evaluation starts at **2:23.6**, provider disclosure
at **2:40.3**, then the graph remains visible through the finish. Speech announcing
each outcome begins after its actual appearance.

The table reproduces the exact [machine-readable narration plan](demo-narration.json).
Windows leave room for natural speech and silence; they do not imply video cuts.
All eleven synthesized segments fit their assigned windows. See the
[voiceover validation report](validation/hackathon-voiceover.json) for actual speech
durations, audio metadata, full decoding, and unchanged video-packet hashes.

| Speech window | Recorded scene | Exact spoken narration |
| --- | --- | --- |
| 0:00.6 - 0:10.9 | Running dashboard and local Meta badge | This synthetic narration was added afterward. The video is one continuous take of Replay Lab, which learns workflows and checks your progress. |
| 0:12.0 - 0:28.5 | Prepared source video and timestamped transcript | This tutorial records our clearly labeled Code Lab simulation. Before this take, Meta Llama generated a proposal from the transcript and locally extracted screen text. The proposal was reviewed and simplified. |
| 0:29.6 - 0:42.5 | Review and approval of the prepared two-step graph | Here are the two prepared checkpoints and their dependency. The reviewed workflow requires explicit approval before guided verification. Model proposals alone cannot establish completion. |
| 0:43.8 - 1:08.5 | Real tab sharing; Settings is shown while inference finishes | The tutorial expects Extensions Marketplace, but Settings is deliberately opened instead. Replay Lab captures the real shared tab. Local O C R reads its pixels, and Meta Llama reasons over that text. Waiting is shown at its actual speed. |
| 1:10.3 - 1:20.5 | Actual FAIL, Preferences evidence and correction | FAIL. The visible Preferences heading contradicts the approved state. Replay Lab recommends returning to Extensions Marketplace. |
| 1:22.0 - 1:42.5 | Extensions is opened; the same constraint is rechecked | The suggested correction is followed on the same shared tab. Extensions Marketplace is now visible. Replay Lab captures the updated screen and checks the same approved constraint again. |
| 1:44.0 - 1:52.7 | Actual PASS and the next pending checkpoint | PASS. This checkpoint is verified. The search step unlocks and stays pending. |
| 1:54.0 - 2:17.8 | Explorer is shown for the unresolved search checkpoint | The next step requires search results for Replay Formatter. Instead, Explorer is shown. This screen does not establish the required state, and missing text alone cannot prove a specific mistake. |
| 2:18.7 - 2:23.2 | Actual UNCERTAIN; the checkpoint remains pending | Replay Lab returns UNCERTAIN and keeps the checkpoint pending. |
| 2:24.0 - 2:39.8 | Separately labeled, executed local OCR evaluation | This separate evaluation executed twenty controlled local O C R cases. All expected verdicts matched, including ten uncertainty cases. These development measurements are not a benchmark of Meta model accuracy. |
| 2:40.8 - 2:55.8 | Exact local Meta provider, then the working graph | Meta Llama three point two runs locally. O C R reads pixels; Llama receives redacted text. Deterministic rules decide completion. One checkpoint is verified; the other remains pending. |

The workflow was genuinely extracted before recording, reviewed by the
owner-authorized engineering agent, and simplified to two transcript-supported
actions. CodeLab is a visibly labeled interactive simulation. Local OCR reads
screenshot pixels; Meta Llama receives redacted text. Deterministic rules decide
verdicts. Three fresh Meta observation requests are recorded; grounded explanation
plans may be cached, and UNCERTAIN uses the deterministic explanation template.

This small demonstration does not establish broad model accuracy, hosted Muse
availability, physical/SAM performance, or hackathon eligibility. Earlier
recordings under `docs/assets/` retain their separate provenance.
