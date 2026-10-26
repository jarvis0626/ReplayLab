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

The project brief requires planning only before the official build period. This initial repository therefore records requirements, planning, and repository setup without application implementation. Recheck the organizers' published rules and start status before writing project-specific application code; this schedule check does not establish participant acceptance or replace the rules. The linked [application overview and event waiver](https://cerebralvalley.ai/e/meta-ai-developer-hackathon/waiver) did not expose substantive content through the research tool.

## Meta integration research

Official documentation is accessible and currently documents:

- [Quickstart](https://dev.meta.ai/docs/quickstart): base URL `https://api.meta.ai/v1`, Bearer authentication using `MODEL_API_KEY`, and model `muse-spark-1.3` through the Responses API.
- [Video understanding](https://dev.meta.ai/docs/video-understanding): upload with the Files API using `purpose=user_data`, then reference the uploaded `file_id` in an `input_file` content block in a Responses request.
- [SAM overview](https://dev.meta.ai/docs/sam/overview): model `sam-3.1` through `POST /v1/responses`; image/video inputs and segmentation output in a custom special-token grammar rather than ordinary chat JSON.
- [SAM client libraries](https://dev.meta.ai/docs/sam/client-libraries): official parsers `@meta-sam/parser` for TypeScript and `meta_sam_parser` for Python.
- [File handling](https://dev.meta.ai/docs/file-handling): `POST /v1/files` for uploads and `DELETE /v1/files/{file_id}` for cleanup. Uploaded files persist by default unless expiration is configured or they are deleted.

These are documentation findings only. No adapter, model request, account access, billing status, or live inference has been implemented or verified. Recheck request and response schemas when integration begins; never present fixture output as live inference.
