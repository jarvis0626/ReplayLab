# ReplayLab project instructions

## Owner preferences

- Work in this repository only; do not modify unrelated repositories.
- Keep the GitHub repository **private**. This current instruction takes precedence over public-repository language in the original project brief. Ask for a visibility change only when the owner requests one or submission work actually needs a decision.
- Commit and push meaningful, completed major updates to the configured GitHub remote. This preference authorizes milestone pushes during requested project work without repeated confirmation.
- Do not force-push, rewrite shared history, or delete remote branches without explicit authorization.
- Do not create background commit/push automation. Review and validate each milestone before pushing.

## Build timing and scope

- The original brief is preserved in `docs/project-brief.md`; the owner's latest messages take precedence.
- The initial repository setup predates the published kickoff. Keep pre-kickoff work to planning and repository administration.
- Before implementing project-specific code, recheck the official event schedule and rules linked in `docs/official-sources.md`. Do not code before the official build window begins.
- Planned architecture and roadmap documents describe intended work, not completed features.

## Implementation standards

- Build a functional vertical slice before broadening scope; follow the milestone acceptance checks in `docs/roadmap.md`.
- Keep graph logic, normalized observations, deterministic verification, provider adapters, persistence, and UI separate.
- Verify official Meta endpoints, model identifiers, schemas, authentication, and SAM parsing before implementing live calls. Never invent provider APIs.
- Mark mock mode and fixture observations clearly. A failed live request must not silently become a mock result.
- PASS requires adequately observed satisfied constraints. FAIL requires evidence of a specific mismatch. Insufficient visibility, unreliable detections, and incomparable camera views produce UNCERTAIN.
- Explanations cannot override deterministic verdicts or invent observations.
- Require user approval of model-proposed steps before guided verification.
- Do not send uploaded media to cloud providers without explicit in-app consent.
- Keep credentials on the server. Never commit secrets, user uploads, runtime databases, dependency folders, or build outputs.
- Run meaningful checks appropriate to each change and fix failures. Report actual results, sample sizes, limitations, and unverified integrations honestly.

## Milestone publishing

1. Review the diff and staged file list for scope, secrets, and generated files.
2. Run applicable tests, linting, builds, or document/configuration checks.
3. Commit with a message describing the completed milestone.
4. Push the current branch to its configured upstream without force.
5. Verify the remote commit and report the outcome. If authentication or network access blocks a push, keep the local commit and explain the blocker.
