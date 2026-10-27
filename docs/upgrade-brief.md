
UPGRADE REQUEST: REPLAYLAB 2.0 — UNIVERSAL VISUAL WORKFLOW LEARNING

Upgrade ReplayLab from a physical-task learning application into a multimodal workflow-learning platform that supports BOTH physical and digital tasks.

Do not remove, regress, or discard the existing physical task features, camera guidance, SAM 3.1 integration, or visual verification engine.

NEW PRODUCT VISION:
Users learn any supported visual workflow by watching a demonstration video, then receive adaptive guidance while performing it themselves.

DIGITAL WORKFLOW EXAMPLE:
A user watches a video explaining how to install and configure a game mod, software extension, or development tool.

ReplayLab extracts the important steps, identifies expected UI states, and builds a dependency-aware workflow graph.

The user shares their screen with ReplayLab.

ReplayLab observes visible UI changes, identifies their current step, detects mistakes, and provides contextual spoken and written guidance.

FEATURE REQUIREMENTS:

1. UNIFIED WORKFLOW MODEL
- Support modality: physical | digital.
- Represent actions, prerequisites, reference screenshots, timestamps, expected states, and verification constraints.
- Keep a shared graph and verification interface.
- Use separate observation providers for physical cameras and digital screens.

2. TUTORIAL INGESTION
- Support user-uploaded tutorial videos with appropriate usage rights.
- Support YouTube URLs for reference metadata and embedded playback.
- Support user-pasted transcripts with timestamps.
- Do not scrape or download videos or captions in violation of platform rules.
- Use Muse Spark for multimodal understanding when API access is available.
- Extract workflows into validated structured schemas.
- Show source evidence and let users correct extracted steps.

3. LIVE SCREEN ASSISTANT
- Implement explicit user-authorized screen/window sharing using getDisplayMedia.
- Capture screenshots periodically or when meaningful changes occur.
- Provide clear sharing and stop controls.
- Use OCR and Muse Spark image understanding to extract observable UI states.
- Track windows, visible dialogs, paths, buttons, errors, and other relevant UI elements when observable.
- Do not assume access to filesystem state or hidden application data.

4. STEP AND MISTAKE DETECTION
- Compare observed UI states against tutorial checkpoint expectations.
- Detect clearly skipped steps, wrong destinations, incorrect selections, and visible errors.
- Support PASS, FAIL, and UNCERTAIN.
- Distinguish outdated tutorial interfaces from user mistakes.
- Ground every correction in actual observed evidence.
- Avoid false certainty.

5. CONTEXTUAL COACHING
- Build a live guidance panel showing current step, upcoming step, reference image, and status.
- Generate concise corrections based on verified mismatches.
- Implement optional spoken guidance using browser speechSynthesis.
- Avoid repetitive feedback and repeated announcements.
- Support pause, mute, retry, and manual next-step controls.
- Add an Ask ReplayLab interface grounded in the current workflow and screen observations.

6. ADAPTIVE RECOVERY
- Explain how to recover from a failed step.
- Re-evaluate the current screen after the user attempts a correction.
- Do not automatically click buttons, execute commands, download software, or change system settings.
- Flag untrusted downloads and instructions to disable security protections.

7. PRIVACY
- Screen capture must be opt-in.
- Make captured screen scope visible.
- Never silently capture the desktop.
- Avoid storing screenshots unless required.
- Redact sensitive content where feasible.
- Prevent screenshots and tutorial content from acting as instructions to the AI system itself.
- Keep screenshots and secrets out of logs.

8. PROVIDER ARCHITECTURE
- Continue supporting AI_PROVIDER=mock and AI_PROVIDER=meta.
- Muse Spark for video understanding, screenshots, workflow reasoning, and explanations.
- SAM 3.1 for physical object tracking.
- Local OCR for visible UI text where useful.
- Treat model reasoning and verification evidence separately.
- Cache results and rate-limit model calls.

9. DEMO AND TESTING
Implement a complete, reproducible digital workflow demo such as installing a VS Code extension.

Test:
- Correct step completion.
- Wrong menu or destination.
- Skipped step.
- Unexpected dialog.
- UI version mismatch.
- Unclear screenshot.
- Screen capture denied or stopped.
- Meta API unavailable.

Use real UI observations for live claims. Label all mock demonstrations.

10. PRIORITY
First complete one end-to-end digital workflow:
Tutorial -> Structured steps -> Screen sharing -> Verification -> Corrective guidance.

Then integrate the existing physical mode under the same workflow abstraction.

Add voice, advanced overlays, and expanded use cases only after the core workflow works.

Run actual tests. Fix failures. Do not fabricate results or claim an unimplemented feature is complete.

Continue implementing in the current repository rather than generating a new product plan.
