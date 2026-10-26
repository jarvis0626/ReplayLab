# ReplayLab

**Teach once. Learn by doing.**

ReplayLab is a planned application for learning a tabletop assembly task from a demonstration video, guiding another attempt, and checking visible progress against evidence-based constraints.

The initial domain is a controlled four-step assembly with colored blocks, consistent lighting, and a comparable camera angle. Verification will return **PASS**, **FAIL**, or **UNCERTAIN**, with observations and specific corrective instructions.

## Current status

This repository currently contains project planning and repository configuration. Application implementation, dependency installation, automated tests, live model calls, screenshots, and deployment have **not** been completed.

The repository is **private**, following the owner's current instruction. The original brief's public submission requirement is recorded for later review; visibility must only change on the owner's explicit request.

The organizer's published kickoff is **October 26, 2026, 17:00 UTC / 22:30 IST**. This repository was prepared before kickoff, so its initial commit contains planning documents only. Recheck the organizer's rules before implementing project-specific code. See [official sources and timing](docs/official-sources.md).

## Planned experience

1. Create a project and upload a demonstration video.
2. Extract reference frames and review proposed task steps.
3. Approve checkpoint constraints and inspect the dependency graph.
4. Follow guided practice and capture or upload checkpoint images.
5. Inspect deterministic verification results, evidence, and corrections.
6. Evaluate the verifier using clearly labeled test scenarios.

## Planned stack

- React, TypeScript, Vite, Tailwind CSS, React Flow, and Lucide.
- Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy/SQLModel, and SQLite.
- OpenCV and FFmpeg for actual media inspection and frame extraction.
- Separate mock and Meta providers, with server-side credentials.
- A deterministic geometry-based verifier that explanation models cannot override.

Provider integrations will be implemented only against verified official documentation. Fixture observations will be visibly labeled as mock data. No live Meta integration is claimed by this repository setup.

## Project documents

- [Original project brief](docs/project-brief.md)
- [Planned architecture](docs/architecture.md)
- [Development milestones and acceptance checks](docs/roadmap.md)
- [Development and GitHub workflow](docs/development.md)
- [Official event and model documentation](docs/official-sources.md)

Local installation and launch commands will be added with the first tested application milestone.

## GitHub workflow

Commit and push each major completed update after reviewing changes and running the checks relevant to that milestone. Keep secrets, uploaded media, runtime databases, and generated dependencies out of Git. See [AGENTS.md](AGENTS.md) for persistent project instructions.
