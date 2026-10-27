# Digital workflows

ReplayLab supports physical camera tasks and digital screen tasks in the same reviewed dependency graph. Physical object observations and SAM adapters remain separate from screen OCR and Muse screenshot understanding. This preview demonstrates a controlled CodeLab extension workflow; it does not claim to understand every application or prove hidden filesystem changes.

## Run the digital demo

Use Node.js 22.12+, Python 3.12, and FFmpeg. From the repository root, run `npm run setup` and `npm run dev` (`npm.cmd` in Windows PowerShell). Setup installs the pinned `rapidocr==3.10.0` and `onnxruntime==1.31.1` dependencies. The RapidOCR wheel includes the three ONNX models used locally; inference uses their explicit installed paths without downloading models at capture time.

1. Open the application and select **Try digital demo**. It generates a labeled synthetic CodeLab tutorial video, reference screenshots, and four editable checkpoint steps.
2. Review **Task & graph**, including expected states, rules, dependencies, and source evidence. Approve the workflow before verification.
3. Open the screen assistant and choose **Open CodeLab sandbox**. Keep this separate tab or window visible.
4. Select **Share screen** and choose the CodeLab surface in the browser's picker. The assistant displays the reported sharing scope and a preview. Keep the coaching page outside the capture.
5. In CodeLab, open **Extensions**, search for **Replay Formatter**, open its details, and use its simulated install control. ReplayLab checks the visible Marketplace, search, details, and Installed/Enabled states in sequence.
6. Try **Settings**, **Show unexpected dialog**, or **Change UI version** to inspect corrections or uncertainty. Reset the sandbox to repeat the demonstration.

CodeLab changes only its browser simulation. It does not install a real extension. Its screenshots are actual pixels processed by OCR; its tutorial and application states are deliberately synthetic. Manual screenshot upload is available when screen sharing is denied or unsupported.

## Tutorial sources and provider modes

Digital projects accept rights-cleared uploaded videos, user-pasted timestamped transcripts, and HTTPS YouTube references. Confirm usage rights before saving tutorial content or uploading a digital tutorial. Uploaded videos are decoded locally and sampled for reference frames; the default upload duration limit is 120 seconds.

YouTube support stores a validated video ID, canonical embedded-playback URL, and optional user-provided title. It does not fetch platform metadata, scrape captions, or download videos. Add a transcript yourself when you need steps from that reference. Transcript ingestion supports chronological timestamped lines/ranges and SRT, up to 50 segments, 50,000 characters, and four hours of source timestamps.

With `AI_PROVIDER=mock`, workflow extraction uses a labeled template or deterministic transcript segmentation. Quoted UI labels become candidate checkpoint rules for review. Segments without usable labels require manual rules before approval. This is separate from **local OCR**, which reads actual screenshot pixels and reports `provider_mode=local_ocr`; OCR is not fixture lookup or Muse inference.

The optional Meta adapters use Muse Spark for digital tutorial proposals and redacted screenshot observations. Digital screens do not use SAM. Existing SAM integration remains available for physical tasks. Live Meta access, account permissions, latency, and behavior remain **unverified**, following the owner's decision to finish offline. Failed Meta calls surface errors and never silently select a mock result.

## Evidence and guidance

PASS requires all approved visible constraints to be supported. FAIL requires positive contradictory evidence, a qualified wrong active path/selection/window, or an unexpected visible error or dialog. A missing OCR label alone is UNCERTAIN. Unknown or poor confidence, unreadable screenshots, and ambiguous states remain uncertain. Explicitly observed interface-version differences are treated as possible tutorial mismatch, rather than user fault. Visible later checkpoints with unverified prerequisites do not prove the user omitted an action; they prompt review without inventing history.

OCR scores describe recognized characters, not a probability of task completion. Short labels, clear target windows, and reviewed constraints work best. Visual evidence cannot establish invisible settings, on-disk files, or actual software installation.

The assistant provides written corrections, optional browser speech, pause/mute/recheck controls, and manual navigation between eligible checkpoints. Manual navigation does not mark completion. **Ask ReplayLab** renders grounded templates from the reviewed workflow and recent screen evidence; it is not an unrestricted chatbot. The application never clicks target controls, executes commands, downloads software, or changes security settings. Source instructions involving downloads or disabled security protections are flagged for independent review.

## Capture and privacy

Screen capture starts only after an explicit browser `getDisplayMedia` choice. The reported scope is browser-supplied metadata, not proof of a hidden application or filesystem state. Capture uses periodic checks and a pixel-change heuristic to skip unchanged frames. Pause stops new analysis; Stop ends the media tracks and clears the project screen session. Browser cancellation, denied permissions, and stopped tracks have recovery messages. Screen capture requires localhost or HTTPS.

Live-preview rectangular masks are applied in the browser before frames leave it. They use fixed coordinates: update them when the layout changes. Manually selected screenshot files are sent as selected and do not inherit those preview masks. The server runs local OCR, replaces detected email/key-like text in returned observations, and blacks out corresponding regions before optional Meta transmission. This is **best effort**: unreadable text, unrecognized secrets, faces, and other sensitive content may remain. Choose the narrowest sharing surface and inspect it first.

Screenshots are processed transiently and are not written to runtime storage or logs by the screen-observation path. Recent sanitized results use bounded process-memory caches; the latest project screen session expires after ten minutes and is cleared on Stop. Shared OCR/model caches have bounded entry counts and are cleared on project deletion or process restart. Tutorial videos, transcripts, reviewed workflows, and completed-step progress are persistent local project data. Screen redaction does not sanitize uploaded tutorial videos or pasted source content automatically; review those before any consented cloud extraction.

Meta screen analysis requires separate explicit in-app cloud consent. It sends an inline redacted image with `store:false` requested; that flag is not a guarantee of zero provider retention. Provider processing and retention terms still apply. No credentialed live call or public deployment is claimed.

Run `npm run check` for the current backend tests, frontend tests, lint, and production build. Local OCR tests use generated pixel images; transport tests simulate Meta responses and do not measure live model accuracy. See [deployment](deployment.md) for local storage and hosting details, and [model usage](model-usage.md) for the existing physical adapters' contracts and limitations.
