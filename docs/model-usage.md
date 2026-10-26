# Model integration and provenance

ReplayLab separates model suggestions, observed geometry, and deterministic
verification. The default mock provider uses explicitly labeled fixtures. Live
requests use the server-side Meta credential and require consent at the API/UI
boundary before uploaded media is sent to Meta. A failed live call is surfaced;
it never silently becomes a mock result.

## Verified contracts

The live adapter uses the official [Meta Model API](https://dev.meta.ai/docs/quickstart):

| Purpose | Model and transport | How ReplayLab uses the response |
| --- | --- | --- |
| Propose a task graph from a reference MP4 | `muse-spark-1.3`, `POST https://api.meta.ai/v1/responses` | Strict JSON Schema output; local Pydantic, graph, and object-label validation; human approval still required |
| Locate objects in a checkpoint/reference image | `sam-3.1`, the same Responses endpoint | Official SAM parser, source-pixel boxes, decoded masks, and optional reported confidence |
| Prioritize evidence for an explanation | `muse-spark-1.3`, strict JSON Schema output | The model selects existing evidence IDs; the application renders existing fact strings and retains the deterministic verdict |

Authentication is `Authorization: Bearer <MODEL_API_KEY>`. Credentials remain on
the server and are excluded from cache files and browser responses. The adapter
does not require the OpenAI SDK: `httpx` sends the documented HTTP requests.
Python dependencies include Pillow, Pydantic, and `meta-sam-parser==0.1.0`.

## Video proposals

Videos are uploaded with `POST /v1/files`, multipart `purpose=user_data`, and
referenced by `input_file.file_id` in the Responses request. The API supports
MP4 video for Muse understanding. ReplayLab uses `store:false`; this disables
stored Responses state and does not itself delete an uploaded file.
The adapter rejects non-MP4 paths before upload; conversion must happen locally
before invoking it, rather than relabeling bytes from a different container.

The uploaded file has an expiration of one hour. The adapter also attempts
`DELETE /v1/files/{file_id}` in a `finally` block, including when proposal parsing
fails. A successful task records a cleanup failure in provenance; expiration
remains the fallback. If a network failure occurs after an upload reaches Meta
but before its ID reaches ReplayLab, the expiration still bounds retention.

The model must return timestamps in seconds, unique step IDs, dependencies,
object labels, and supported rule types. ReplayLab rejects invalid graphs or
undeclared labels and maps each step to the sampled reference frame closest to
its end timestamp. Four sampled frames cannot guarantee that a short action's
exact final state is represented; users must review the proposed frame and rules.

[Video understanding](https://dev.meta.ai/docs/video-understanding/) ·
[File handling and expiration](https://dev.meta.ai/docs/file-handling) ·
[Structured output](https://dev.meta.ai/docs/structured-output)

## SAM observations

Each request supplies one short noun phrase and one image data URL. Different
object concepts use separate requests. Metadata values are strings:
`include_confidence:"true"` and `mask_encoding:"one_bit"`. The current adapter
uses the documented non-streaming response path and requires completed output.

SAM returns special-token text, **not JSON**. The official Python public API is
`image_segmentation_format().create_parser()` followed by `push()` and
`finish(CompletedOutcome())`; it is imported from `meta_sam_parser`. The package
also provides `parse_responses_stream` for async streams. It does not export
`parse_image_stream` or `parse_video_stream`.

The adapter validates masks and rejects malformed records, incomplete output,
unrecognized plain text, and source dimensions inconsistent with the actual
oriented image. Inclusive wire coordinates become half-open boxes in the
official parser. Boxes are then normalized to the actual image dimensions.
Masks use official compressed COCO RLE with a box-local raster, normalized box
bounds, and `coordinate_space:"box_local"`; their `size` is the local mask's
height and width, not the complete source image dimensions.

Missing confidence stays `None`. A completed empty response is a valid result
with zero matches. Detection alone cannot establish that every object was
visible or found. The adapter leaves visibility, coverage, quality, and view
comparability unknown, with `detection_complete:false`. Separate measurements
and explicit user attestations may enrich those fields in the API layer.
Absence and exact counts require stronger completeness evidence than SAM alone
provides. SAM does not independently measure a color attribute; named color
prompts are not converted into calibrated color observations.

[SAM prompts](https://dev.meta.ai/docs/sam/segmenting) ·
[Wire grammar](https://dev.meta.ai/docs/sam/reading-segmentation) ·
[Official Python parser](https://github.com/meta-models/meta-sam/blob/main/python/README.md)

## Errors, explanation boundaries, and local caching

Authentication, billing, access restrictions, malformed media, missing resources,
and size-limit errors return server-safe messages. Rate limiting, selected
temporary server errors, and transport timeouts use at most three attempts with
backoff. `Retry-After` is honored up to 60 seconds; larger delays are surfaced
immediately for a later retry. A provider 504 is surfaced rather than blindly
repeating the same expensive request. Raw provider diagnostics are not returned
to users.

An explanation request cannot change the computed status. Unknown evidence IDs,
changed status, unexpected fields, and failed requests retain the original
deterministic explanation. The adapter records explanation provenance separately
as `last_explanation_provenance`. No unrestricted model narration is rendered.

Successful proposals and normalized observations are cached only in the ignored
runtime data directory. SHA-256 keys include the operation, exact media bytes,
model, schema/parser identity, and prompts. Cached proposals are validated again
and mapped to the current project's frame IDs. Corrupt caches are ignored. Cache
payloads contain derived private observations and descriptions. Deleting a project
clears the shared inference cache conservatively; other projects can refill their cache entries.
Do not treat runtime cache files as shareable fixtures.

[Error handling](https://dev.meta.ai/docs/error-handling) ·
[Responses schemas](https://dev.meta.ai/docs/api-reference/responses/schemas)

## Validation status

Provider tests use `httpx.MockTransport`; they make no external requests. They
cover request shapes, structured proposal validation, upload cleanup, caching,
auth/billing/access errors, retries, refusals, incomplete output, actual official
SAM mask parsing, normalized coordinates, unknown quality, and evidence-only
explanations. The SAM payload in those tests is a public Meta parser example,
not a ReplayLab accuracy measurement.

No credentialed Meta smoke test or live media accuracy study has been completed.
Account entitlement, billing, observed latency, and model behavior on the user's
media remain unverified until live requests are run with an authorized key and
explicit media consent. Unit tests establish adapter behavior against documented
contracts, not successful operation of an external account.
