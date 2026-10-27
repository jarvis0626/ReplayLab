# Tutorial sources and transcript proposals

ReplayLab digital workflows accept a rights-confirmed uploaded video, a YouTube
reference, or a user-pasted timestamped transcript. Source instructions remain
untrusted evidence. They are never executed, and proposals require review and
approval before screen verification.

## YouTube references

The server validates HTTPS URLs on exactly `youtube.com`, `www.youtube.com`,
`m.youtube.com`, or `youtu.be`. Supported paths are `/watch?v=...`, `/shorts/...`,
`/embed/...`, and a single `youtu.be` video-ID path. IDs must contain exactly 11
ASCII letters, digits, underscores, or hyphens. Credentials, explicit ports,
lookalike hosts, ambiguous video IDs, and unsupported redirect paths are rejected.

The saved source contains the ID, a canonical
`https://www.youtube-nocookie.com/embed/{id}` URL, supplied/default title, parsed
segments, usage-rights confirmation, and advisory instruction warnings. Supplied
titles are marked unverified. The server does **not** fetch metadata, download
videos or captions, scrape pages, or attempt to infer unavailable content.
A URL without a transcript is a playback reference, not a successful extraction.

The browser embeds the original player. Google documents the `/embed/VIDEO_ID`
format and the `youtube-nocookie.com` privacy-enhanced domain. Embedding still
contacts YouTube and can be unavailable for a particular video; this is not a
guarantee of playback or an offline copy.
[Player parameters](https://developers.google.com/youtube/player_parameters),
[YouTube embedding help](https://support.google.com/youtube/answer/171780?hl=en).

Usage-rights confirmation is an explicit user attestation enforced at the API
boundary, not a claim that ReplayLab checked ownership or licensed third-party
material. Only provide tutorial content you are authorized to use.

## Timestamp formats and bounds

Examples accepted by the local parser:

```text
[00:00] Open "Extensions Marketplace".
[00:12] Search for "Replay Formatter".
```

```text
00:12-00:24 Open "Extension details".
00:24-00:30 Locate "Install extension".
```

SRT counters, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, and multiline captions are also
supported. Point timestamps end at the next timestamp; the final point ends at
its own timestamp because no duration was supplied. Explicit ranges retain their
ends and must have positive duration. Segments must have strictly increasing
starts, non-overlapping ranges, and nonempty text. Malformed timestamps are
rejected rather than silently interpreted as a step.

Limits are 50,000 input characters, 50 segments, and timestamps within four hours.
The existing video upload duration/size limits apply separately. A transcript is
not proof that a label was actually visible in its source video.

## Offline extraction and screen rules

Offline extraction creates one editable step per transcript segment, in a simple
dependency chain. Quoted UI labels become candidate `text_present` rules, with at
most eight labels per segment. A segment without a quoted label has no inferred
screen rules and is explicitly marked for manual checkpoint definition. No
hidden application state, installed software, path, or successful action is
assumed. Missing observable rules remain uncertain.

Task provenance identifies deterministic transcript segmentation, states that no
video or screen inference occurred, and requires approval. The local segmenter
cannot label itself as Meta inference. The separate Muse adapter remains an
explicit provider path and is not silently substituted for local parsing.
Live Meta account validation remains pending under the owner's offline scope.

Warnings flag instructions to disable security protections and unverified
download sources. A warning does not label a domain malicious or execute/block a
general extension installation. All referenced download sources remain
unverified by ReplayLab. Instructions, transcripts, screenshots, and captions
cannot override application or model system instructions.

## Generated digital example

`ensure_digital_demo(directory)` generates four 1280 x 800 PNG references and an
actual 12-second H.264 MP4 under the supplied ignored runtime directory. It uses
portable fonts and local FFmpeg; there are no remote downloads. The manifest
contains filenames/timestamps and a fixed synthetic transcript. The associated
task is a reviewed-later mock template for **CodeLab 1.0**, not video analysis or
a real extension installation.

Its checkpoints are Extensions Marketplace; Search results and Replay Formatter;
Extension details and Install extension; then Installed and Enabled. The wrong
Preferences pane is explicit contradictory evidence. Visible error/dialog guards
come from the screen verifier, not an assumption that OCR can prove their absence.
The local screen provider must read actual captured pixels; filenames and hidden
simulator state do not select verdicts. Documentation banners avoid expected
state words such as "Installed" before that state is shown.

The ingestion tests cover bounds, formats, URL validation with networking denied,
provenance, advisory warnings, and graph generation. Demo tests verify actual PNG
dimensions and an FFprobe-inspected playable MP4. These establish software
behavior; they do not establish general tutorial understanding or model accuracy.
