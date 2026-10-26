# ReplayLab demonstration assets

The reproducible offline example is a four-step synthetic colored-block assembly.
It is explicitly labeled MOCK MODE and has known generated geometry. No person,
private upload, external video, or live model result is bundled as demo evidence.

`fixtures/evaluation.json` is tracked source data for 25 curated normalized
observation cases. It is required by the running evaluation endpoint and must be
included when packaging the application. [Evaluation notes](../docs/evaluation.md)
explain the measured result and its limits.

## Generated media

`apps/api/app/services/demo.py` creates six PNG fixtures, a real playable MP4,
and a manifest under the ignored runtime directory `apps/api/data/demo` by
default. FFmpeg and OpenCV are required. These generated files are runtime assets,
not tracked source files. The manifest records hashes of decoded image pixels and
their supplied observations; the app also registers reference frames extracted
from its own generated sample video.

| Fixture ID | Visible sample |
| --- | --- |
| `step-1` | Red foundation |
| `step-2` | Red and blue in the demonstrated arrangement |
| `step-3` | Red, blue, and green |
| `complete` | All four blocks |
| `blue-right` | Blue moved to a different relationship |
| `partial` | Obstructed scene with reduced visibility/coverage |

A fixture's name does not choose a verdict. The active approved rules and
observations do. The same image can satisfy an early checkpoint while violating
a later one. The mock provider only recognizes registered decoded-pixel hashes;
renaming an unrelated file to a fixture name does not give it observations.
Unknown images remain uncertain in mock mode.

## Use the sample

Start the application using the repository [README](../README.md), choose
**Explore the sample project**, inspect its video/frames, then review and approve
the task in **Task & graph**. In **Guided practice**, select labeled fixtures and
verify their actual rule results. Camera/image upload is also available, but
arbitrary photos cannot be analyzed by the offline provider.

The API exposes `/api/demo/video`, `/api/demo/fixtures`, and
`/api/demo/fixtures/{fixture_id}/image`. Project media and metadata are copied into
that project's local runtime storage. Deleting a project also clears the shared
inference cache, while generated synthetic demo assets remain available. No public deployment or uploaded
demo video is implied by these local routes.

See the [three-minute walkthrough](../docs/demo-script.md),
[model usage](../docs/model-usage.md), and [actual checks](../docs/test-results.md).
