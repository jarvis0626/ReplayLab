# Official source verification

Checked on 26 October 2026 at approximately 17:35 IST (12:05 UTC).

## Hackathon schedule

- [Meta event page](https://dev.meta.ai/events/global-hackathon): the hackathon begins on 26 October with a kickoff livestream; submissions close on 4 November at 9:00 PM Eastern Time. The page says dates may change and that selected participants must accept the official rules.
- [Organizer event page](https://events.cerebralvalley.ai/e/meta-ai-developer-hackathon), linked from Meta: its visible schedule says 26 October at 12:00 PM through 4 November at 9:00 PM, labeled EST. The page's JSON-LD supplies the exact timestamps below.

| Event | Organizer timestamp (UTC) | India time (IST) |
| --- | --- | --- |
| Scheduled kickoff | `2026-10-26T17:00:00.000Z` | 26 October 2026, 10:30 PM |
| Submission deadline | `2026-11-05T02:00:00.000Z` | 5 November 2026, 7:30 AM |

The kickoff was still ahead of the verification time. The organizer explicitly labels its start time EST; the UTC timestamp above avoids ambiguity with Eastern daylight saving time on 26 October.

The initial repository commit records planning and repository setup without application implementation. At approximately 17:48 IST on 26 October, the owner explicitly authorized: "Start coding now; eligibility can remain unconfirmed." Application development begins before the scheduled kickoff under that instruction. This schedule check and owner decision do not establish submission eligibility or participant acceptance. The linked [application overview and event waiver](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver) did not expose substantive content through the research tool.

## Meta integration research

Official documentation is accessible and currently documents:

- [Quickstart](https://dev.meta.ai/docs/quickstart): base URL `https://api.meta.ai/v1`, Bearer authentication using `MODEL_API_KEY`, and model `muse-spark-1.3` through the Responses API.
- [Video understanding](https://dev.meta.ai/docs/video-understanding): upload with the Files API using `purpose=user_data`, then reference the uploaded `file_id` in an `input_file` content block in a Responses request.
- [SAM overview](https://dev.meta.ai/docs/sam/overview): model `sam-3.1` through `POST /v1/responses`; image/video inputs and segmentation output in a custom special-token grammar rather than ordinary chat JSON.
- [SAM client libraries](https://dev.meta.ai/docs/sam/client-libraries): official parsers `@meta-sam/parser` for TypeScript and `meta_sam_parser` for Python.
- [File handling](https://dev.meta.ai/docs/file-handling): `POST /v1/files` for uploads and `DELETE /v1/files/{file_id}` for cleanup. Uploaded files persist by default unless expiration is configured or they are deleted.

The adapters are now implemented and tested against mocked HTTP transport and the official SAM parser. No live model request, account access, billing status, or live inference has been verified because no API key is configured. Recheck current schemas when live validation begins; never present fixture output as live inference.
