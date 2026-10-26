You are my principal AI engineer, full-stack developer, systems architect, and technical lead.

Your task is to BUILD, TEST, and PREPARE FOR DEPLOYMENT a complete working application called REPLAYLAB for the Meta Global AI Developer Hackathon 2026.

Do not just create a plan, mockup, placeholder application, or documentation. Actually implement the software, run it, fix errors, and complete the functionality described below.

PROJECT NAME: ReplayLab
TAGLINE: Teach once. Learn by doing.
TRACK: Indie Developer
THEME: Push the Frontier

CRITICAL HACKATHON RULES:
- All submitted project-specific code must be built during the official hackathon period. Check the official start before implementation. If the event has not started, do planning only.
- Public GitHub repository required.
- Meta models must be meaningfully integrated before final submission.
- Do not represent mocked AI results as real model inference.
- Clearly distinguish work implemented during this hackathon.
- The final submission requires an accessible three-minute demo video.
- Deadline: November 4, 2026, 9 PM Eastern Time. Follow the organizers' latest published rules.

==================================================
1. PRODUCT VISION
==================================================

Build an AI-powered system that learns a physical task from a demonstration video and guides another person through the same task while checking their progress visually.

Example:

Person A records a video showing how to assemble a small structure from colored interlocking building blocks.

ReplayLab analyzes the video and extracts:
- The objects involved
- The chronological actions
- The relationship between objects
- The expected state after each step
- The prerequisites for subsequent steps
- A source timestamp and reference frame for each step

ReplayLab generates an interactive action graph and a guided tutorial.

Person B follows the instructions while using a camera.

After every step, ReplayLab analyzes a checkpoint image, compares it with the expected state, and determines whether the step was completed correctly.

It should return:
PASS: Observable requirements are satisfied.
FAIL: A specific requirement is visibly violated.
UNCERTAIN: The available image is insufficient to determine correctness.

If a step is incorrect, explain the specific mistake and offer a corrective instruction backed by visible evidence.

CORE INNOVATION:
Do not build a generic image analyzer or AI tutorial chatbot.

Build an evidence-grounded visual task verification engine connecting:
Video understanding -> Structured action graphs -> Object observations -> Constraint verification -> Adaptive instructions.

MVP DOMAIN:
A controlled four-step tabletop assembly with colored blocks, consistent camera angle, lighting, and distinguishable components.

Do not claim the product understands arbitrary assembly tasks or invisible 3D connections.

==================================================
2. TECH STACK
==================================================

Frontend:
- React
- TypeScript
- Vite
- Tailwind CSS
- React Flow / @xyflow/react
- Lucide icons
- Optional Framer Motion for meaningful animations
- Browser MediaDevices API for camera capture

Backend:
- Python 3.11+
- FastAPI
- Pydantic v2
- SQLModel / SQLAlchemy
- SQLite for MVP
- OpenCV
- FFmpeg
- NumPy
- pytest

AI:
- Meta Muse Spark series for multimodal video understanding, structured step extraction, and grounded explanations
- Meta SAM 3.1 for object segmentation and tracking
- Meta Model API for hosted model access
- An optional permitted Meta open-weights inference provider as fallback
- Deterministic verification rules separate from the LLM

Architecture:
- Monorepo
- Modular backend
- Strongly typed schemas
- REST APIs
- Clean separation of UI, inference, domain logic, and persistence
- Environment-based configuration
- Docker Compose for optional local startup
- Tests and CI

Meta API documentation:
https://dev.meta.ai/docs/quickstart
https://dev.meta.ai/docs/video-understanding
https://dev.meta.ai/docs/sam/overview
https://dev.meta.ai/docs/sam/client-libraries
https://dev.meta.ai/docs/file-handling

Verify the current official API endpoints, model identifiers, request schemas, authentication, and response formats before implementing integrations. Never invent API methods or SAM response structures.

==================================================
3. PROJECT STRUCTURE
==================================================

Create a maintainable project similar to:

replaylab/
  apps/
    web/
      src/
        components/
        pages/
        hooks/
        services/
        types/
        styles/
    api/
      app/
        api/
        core/
        database/
        models/
        schemas/
        services/
          video/
          graph/
          verification/
          inference/
        providers/
          mock/
          meta/
        utils/
      tests/
  packages/
    contracts/
  demo/
    fixtures/
    examples/
  docs/
    architecture.md
    evaluation.md
    deployment.md
  .github/
    workflows/
  .env.example
  .gitignore
  docker-compose.yml
  README.md

You may adjust the structure if there is a clearly better architecture. Avoid unnecessary complexity.

==================================================
4. USER INTERFACE AND EXPERIENCE
==================================================

Create a polished, responsive application with a premium research-tool / developer-tool aesthetic.

Design:
- Dark mode by default
- Clean typography
- Restrained cyan/blue accents
- Smooth transitions
- Elegant cards and panels
- High-quality spacing and visual hierarchy
- Responsive desktop and tablet layouts
- Accessible controls and contrast
- Useful animations during processing and state changes

Avoid generic AI landing pages, excessive gradients, glassmorphism, emojis everywhere, or decorative features with no purpose.

Main application areas:

A. Dashboard
- Create new ReplayLab project
- Recent projects
- Project progress/status
- Clear start demonstration action
- Sample project for first-time users
- Model provider availability indicator

B. Demonstration Studio
- Drag-and-drop video upload
- Video format/size validation
- Video preview and playback
- Timeline with extracted keyframes
- Frame selection and timestamp display
- Processing progress and meaningful error messages

C. Task Understanding Workspace
- Extracted task steps
- Objects and their roles
- Timestamped source evidence
- Reference frame for each step
- Editable step names and descriptions
- Add/remove/reorder steps with dependency validation
- Approval step before using model-proposed instructions

D. Interactive Task Graph
- React Flow visualization
- Directed nodes representing actions
- Dependency edges
- Step ordering
- Click nodes for reference frame and details
- Pan, zoom, fit view
- Distinct completed/current/pending states
- Highlight evidence associated with each step

E. Guided Practice
- Step-by-step instruction interface
- Reference frame
- User webcam preview
- Capture checkpoint image
- Alternative manual image upload
- Camera permission handling
- Current step indicator and progress bar
- Retake photo action

F. Verification Results
- PASS / FAIL / UNCERTAIN verdict
- Reference image vs captured image
- Bounding boxes/masks when available
- Object-level observations
- Individual rule results
- Reason for decision
- Confidence/uncertainty indicators that reflect actual evidence
- Actionable corrective instructions
- Retry or proceed controls

G. Evaluation
- Labeled verification test cases
- Predicted vs expected results
- Per-case diagnostics
- Confusion matrix when meaningful
- Pass/fail/uncertain counts
- Measured metrics, never fabricated results
- Clear sample-size and evaluation limitations

==================================================
5. VIDEO INGESTION AND TASK EXTRACTION
==================================================

Implement real video upload and processing.

Requirements:
- Validate MIME type, content, duration, and size
- Store uploads under generated safe identifiers
- Prevent path traversal and unsafe filenames
- Use FFmpeg/OpenCV to inspect and extract keyframes
- Save video metadata and frame timestamps
- Cache processed assets
- Support processing failures gracefully

Build an AI reasoning interface:

Reasoner.extract_task(video, frames) -> StructuredTask

StructuredTask should include:
- Task ID
- Title
- Description
- Objects
- Steps
- Source video timestamp intervals
- Reference frames
- Dependencies
- Observable checkpoint rules
- Model/provider provenance

For live inference:
Use Meta's officially documented video input mechanism and Muse Spark multimodal capabilities.

Extract structured JSON, validate it using Pydantic, reject malformed outputs, and allow users to correct uncertain steps.

Never claim an action is verified simply because the LLM described it.

When API access is unavailable, use deterministic mock extraction with a prominent MOCK MODE indicator.

==================================================
6. ACTION GRAPH ENGINE
==================================================

Create a true directed acyclic graph of task steps.

Each node contains:
- Unique identifier
- Description
- Prerequisite IDs
- Source timestamps
- Reference image
- Involved objects
- Expected visible state
- Completion status
- Checkpoint constraints

Implement:
- Cycle detection
- Missing dependency validation
- Topological sorting
- Step completion updates
- Dependency-aware progression
- Graph serialization and persistence

Keep graph logic independent of the React Flow renderer.

==================================================
7. OBJECT SEGMENTATION AND TRACKING
==================================================

Create a provider abstraction:

Segmenter.observe(image_or_video, object_prompts) -> NormalizedObservations

Normalized observations should include:
- Object label
- Object/track identifier when available
- Bounding box in normalized coordinates
- Mask where available
- Confidence or applicable quality information
- Frame timestamp
- Evidence source
- Provider provenance

LIVE MODE:
Integrate Meta SAM 3.1 using its actual documented image/video interface and official parser.

Do not assume SAM produces ordinary chat JSON.

Support prompts such as:
- red block
- blue block
- green block
- yellow block

Render segmentation results on reference and user checkpoint images.

Use a normalized representation so reference and attempt frames can be compared.

Fallback:
MockSegmenter returns known observations for explicitly labeled demo/test fixtures, never falsely represented as live segmentation.

==================================================
8. VISUAL VERIFICATION ENGINE
==================================================

THIS IS THE MOST IMPORTANT COMPONENT.

Implement a deterministic visual-state evaluator.

Inputs:
- Approved expected checkpoint constraints
- Reference observations
- Current image observations
- Camera/visibility confidence
- Prior completed steps where relevant

Rules should support:
- Required object is present
- Object count
- Relative position (above, below, left, right)
- Basic proximity / alignment
- Known color discrimination where reliable
- Visibility confidence
- Camera-angle comparability

Use normalized geometry, not absolute screen pixels.

Outputs:
VerificationResult {
  step_id,
  status: "pass" | "fail" | "uncertain",
  observations,
  rule_results,
  evidence,
  explanation,
  provider_mode
}

Important decision rules:
- PASS only if required constraints are adequately observed and satisfied.
- FAIL only when there is sufficient evidence of a specific mismatch.
- UNCERTAIN when an object is obscured, image quality is inadequate, segmentation is unreliable, or the camera views cannot be compared.
- Never turn a low-confidence missing detection automatically into a FAIL.
- Do not allow an explanation model to override the deterministic verdict.

Examples:
Correct structure -> PASS.
Clearly misplaced blue block -> FAIL.
Required component visibly absent with sufficient coverage -> FAIL.
Occluded component -> UNCERTAIN.
Different camera angle preventing reliable comparison -> UNCERTAIN.

Implement actual comparison logic. Do not hardcode the verification result based on the image filename, demo button, or requested outcome.

==================================================
9. AI EXPLANATION ENGINE
==================================================

Create:

Explainer.explain(verdict, observations, rule_results, evidence)

The explanation should:
- Describe the observed mismatch
- Identify the relevant objects
- Explain the expected relationship
- Provide a specific corrective action
- Explain uncertainty when evidence is insufficient
- Never invent observations

Example:
"I can see the blue block to the right of the red block, but the reference step requires it above the red block. Move it above the red block and capture another image."

Muse Spark may generate natural-language explanations from structured evidence.

If no API key is available, use deterministic template explanations.

==================================================
10. DATABASE AND API
==================================================

Persist projects, videos, frames, tasks, steps, checkpoints, attempts, and verification results.

Implement approximately these REST routes:

GET /api/health
POST /api/projects
GET /api/projects
GET /api/projects/{id}
DELETE /api/projects/{id}

POST /api/projects/{id}/video
POST /api/projects/{id}/extract
GET /api/projects/{id}/processing-status

PATCH /api/projects/{id}/steps/{step_id}
GET /api/projects/{id}/graph

POST /api/projects/{id}/attempts
POST /api/attempts/{id}/verify

GET /api/projects/{id}/evaluation

Use proper response schemas, validation, error responses, media access policies, and CORS configuration.

Long-running video processing should not freeze HTTP requests or the UI. Use a reasonable development job mechanism with status polling and clear failure handling.

==================================================
11. META MODEL API INTEGRATION
==================================================

IMPORTANT: My Meta account may temporarily be billing-restricted while hackathon credits are processed.

Therefore support:

AI_PROVIDER=mock
AI_PROVIDER=meta

Default to mock mode when no valid API credentials are available.

Use:
MODEL_API_KEY from environment variables.
Never expose API keys to the frontend.
Never commit secrets to Git.

Build separate model adapters.

Real mode should integrate:
- Muse Spark multimodal video reasoning
- SAM 3.1 object segmentation
- Muse Spark evidence-grounded explanations

Consult official API documentation before making requests.

Handle:
- Missing key
- Authentication failure
- Billing restrictions
- Rate limits
- Timeout
- Invalid model output
- Unsupported input
- Provider outage

Make provider status visible to the user.

Cache inference results to save hackathon credits.

Add basic usage logging without leaking credentials or private content.

Do not show mocked or fixture-based results as real inference.

If Meta access remains blocked, implement and test adapters as far as possible, report precisely what is unverified, and preserve the full offline application.

==================================================
12. TESTING
==================================================

Implement tests throughout development.

Backend:
- Graph creation and cycle detection
- Step dependencies
- Pydantic schema validation
- Video upload limits and invalid media
- Task extraction result validation
- Normalized geometry
- Correct relative position verification
- Missing objects
- Swapped positions
- Low-confidence detection
- Occlusion
- Camera mismatch
- PASS, FAIL, UNCERTAIN behavior
- Provider failures
- API error handling

Frontend:
- Application navigation
- Project creation
- Video upload UX
- Task graph rendering
- Checkpoint capture/upload
- Verification result display
- Mock-mode labeling

Create a small labeled evaluation suite with at least 12 scenarios, including correct, incorrect, and ambiguous outcomes.

Fixtures must be transparently labeled. Avoid claiming these tests demonstrate real-world model accuracy if they only test curated mock observations.

Run tests for real. Fix failures rather than claiming they passed.

==================================================
13. SECURITY, PRIVACY, AND RELIABILITY
==================================================

- Never commit API keys
- Validate and sanitize uploads
- Use safe generated filenames
- Restrict upload size, media types, and duration
- Configure CORS
- Do not expose internal filesystem paths
- Request camera permission explicitly
- Capture only when requested
- Provide media deletion
- Handle corrupted video safely
- Handle backend/network failure gracefully
- Never log sensitive tokens
- Document third-party media licenses
- Do not silently send user videos to third-party providers

For any public deployment, clearly disclose cloud processing and media retention behavior.

==================================================
14. DOCUMENTATION AND GITHUB
==================================================

Initialize a NEW repository named ReplayLab.

Do not alter unrelated existing repositories.

Add:
- Professional README
- Screenshots/GIFs recorded from actual working features
- Architecture diagram
- Installation instructions for Windows PowerShell and Linux
- Development commands
- Example environment configuration
- How mock and live modes work
- Model usage description
- Demo workflow
- Test results
- Evaluation limitations
- Deployment guide
- License and third-party attribution
- GitHub Actions CI for tests and linting

Do not invent screenshots, results, or working links.

If GitHub authentication is available, push the project to a new public repository under my authenticated account. Never force-push or delete an unrelated repository. Otherwise initialize Git locally and provide exact commands to publish.

==================================================
15. DEVELOPMENT MILESTONES
==================================================

PHASE 1: Foundation
- Create monorepo
- Set up frontend/backend
- Configure database
- Build app navigation and UI shell
- Add health endpoint
- Add mock AI provider interfaces
- Run initial tests

PHASE 2: Video and task understanding
- Implement real video uploads
- Extract real frames and timestamps
- Build task schemas
- Implement mock task extraction
- Create editable task timeline
- Persist everything

PHASE 3: Graph and guided practice
- Implement action dependency graph
- Build camera snapshot functionality
- Implement reference/attempt comparisons
- Add progress states
- Build the guided practice experience

PHASE 4: Verification
- Implement real deterministic rule evaluator
- Build PASS/FAIL/UNCERTAIN logic
- Evidence references and overlays
- Correction generator
- Verification tests

PHASE 5: Meta AI
- Connect Muse Spark video understanding
- Connect SAM 3.1 segmentation
- Add grounded AI explanations
- Handle provider errors and billing issues
- Test live model responses when credentials work

PHASE 6: Evaluation and polish
- Build evaluation suite
- Add quality/error handling
- Run frontend and backend tests
- Make UI responsive
- Add CI
- Improve usability

PHASE 7: Submission
- Deploy if possible
- Public GitHub repository
- Prepare a reproducible demo setup
- Write a factual 3-minute demo script
- Document the real Meta model calls
- Record the actual app demonstration if recording tools are available
- Verify all submission links and readiness

==================================================
16. IMPLEMENTATION INSTRUCTIONS FOR CODEX
==================================================

Do not respond with only a high-level plan.

Create the actual application in the workspace.

Work milestone by milestone, but continue implementing subsequent milestones within the available session rather than asking me to approve every small step.

For every milestone:
1. Implement the actual source files.
2. Install dependencies where possible.
3. Run the application or verify startup.
4. Run relevant tests.
5. Fix failures.
6. Explain any environment limitations.
7. Commit meaningful completed changes if Git is configured.

Prioritize a fully functional vertical slice over a long list of incomplete features.

Do not silently substitute a mock for a failed live model integration.
Do not fabricate test results.
Do not invent external APIs.
Do not mark incomplete features as completed.
Do not use stock UI screenshots as proof the application works.

If API credentials are unavailable:
Build everything possible in mock mode and make the real provider adapters ready, then clearly list the exact integration steps that require credentials.

Only request my intervention for genuine external blockers such as authentication, billing approval, a required secret, or external deployment permissions.

==================================================
17. SUCCESS CRITERIA
==================================================

At minimum, I should be able to:

1. Launch ReplayLab locally.
2. Create a project.
3. Upload and watch a demonstration video.
4. See extracted reference frames.
5. Generate or review structured task steps.
6. View the interactive action graph.
7. Open guided practice.
8. Capture or upload a checkpoint image.
9. Receive a reasoned PASS/FAIL/UNCERTAIN result.
10. See visual evidence for that result.
11. Get a specific correction when verification fails.
12. Run automated tests.
13. Switch between mock and Meta providers.
14. See clearly which parts are real and which are mocked.
15. Follow documentation to reproduce the demo.

FINAL EXPECTATION:

Build ReplayLab into a cohesive, visually polished, technically credible AI application suitable for the Meta Global AI Developer Hackathon.

The primary focus is the new technical capability:
Learning a visual task from demonstration and verifying another attempt using evidence-grounded reasoning.

Start by inspecting the workspace, verifying that the official build window has begun, setting up the repository, and implementing Phase 1. Continue through the milestones as far as tools and credentials permit.

Do the actual coding now rather than just telling me what to build.