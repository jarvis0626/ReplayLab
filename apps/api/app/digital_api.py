"""Digital workflows and transient screen sessions; no screenshots are persisted."""

import copy
import hashlib
import json
import math
import shutil
import threading
import time
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from app.api_contracts import Project
from app.digital_schemas import ScreenObservation, ScreenResult
from app.schemas import Task
from app.services.media import MediaError, decode_image, inspect_video
from app.services.thresholds import configured_thresholds
from app.services.verification_records import build_verification
from app.verification_contracts import WorkflowVerification


class TutorialInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    youtube_url: str | None = Field(default=None, max_length=2048)
    transcript: str = Field(default="", max_length=50000)
    title: str | None = Field(default=None, max_length=240)
    usage_rights_confirmed: bool = False


class AskInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=2000)


class ScreenCheck(BaseModel):
    result: ScreenResult
    observation: ScreenObservation
    completed_step_ids: list[str]
    current_step_id: str | None
    upcoming_step_id: str | None
    screen_stored: bool = False
    source_scope: str | None = None
    verification: WorkflowVerification | None = None


class ScreenSessions:
    """Bounded, ten-minute RAM evidence with stop-generation and request gates."""

    def __init__(self):
        self.lock = threading.RLock()
        self.records = {}
        self.generations = {}
        self.inflight = set()
        self.started = {}

    def clear(self, project_id):
        with self.lock:
            self.generations[project_id] = self.generations.get(project_id, 0) + 1
            self.records.pop(project_id, None)

    def last(self, project_id):
        with self.lock:
            record = self.records.get(project_id)
            if record and time.monotonic() - record["time"] < 600:
                return copy.deepcopy(record)
            self.records.pop(project_id, None)
            return None


def install_digital_routes(
    api,
    *,
    settings,
    store,
    media_directory: Path,
    data_directory: Path,
    mode,
    provider_for,
    project_or_404,
    new_project,
    require_idle,
):
    sessions = ScreenSessions()
    api.state.screen_sessions = sessions

    def digital_project(project_id):
        project = project_or_404(project_id)
        require_idle(project)
        if project.get("modality", "physical") != "digital":
            raise HTTPException(
                409, "This endpoint is for digital workflows. Physical practice remains available separately."
            )
        return project

    @api.post("/api/projects/digital-demo", response_model=Project, status_code=201)
    def digital_demo():
        from app.services.digital_demo import ensure_digital_demo, digital_demo_task

        manifest = ensure_digital_demo(data_directory / "digital-demo")
        project = new_project("CodeLab extension workflow · demo", "digital")
        directory = media_directory / project["id"]
        video_name = f"video-{uuid4().hex}.mp4"
        source = data_directory / "digital-demo"
        shutil.copyfile(source / manifest["video"], directory / video_name)
        frames = []
        for frame in manifest["frames"]:
            frame_id = uuid4().hex
            name = f"frame-{frame_id}.png"
            shutil.copyfile(source / frame["filename"], directory / name)
            frames.append(
                {"id": frame_id, "url": f"/api/media/{project['id']}/{name}", "timestamp": frame["timestamp"]}
            )
        project.update(
            status="ready",
            frames=frames,
            video={
                "url": f"/api/media/{project['id']}/{video_name}",
                "original_name": "CodeLab synthetic tutorial.mp4",
                **inspect_video(directory / video_name, settings.max_video_seconds),
            },
            task=digital_demo_task(frames).model_dump(mode="json"),
            tutorial={key: value for key, value in manifest.items() if key not in {"video", "frames"}},
            processing={
                "stage": "task_ready",
                "progress": 100,
                "message": "Review the simulated workflow, then share the separate CodeLab tab.",
            },
        )
        return store.save_project(project)

    @api.post("/api/projects/{project_id}/tutorial", response_model=Project)
    def tutorial(project_id: str, body: TutorialInput):
        from app.services.tutorials import parse_tutorial

        if not body.usage_rights_confirmed:
            raise HTTPException(422, "Confirm appropriate usage rights before adding tutorial content.")
        with store.lock:
            project = digital_project(project_id)
            try:
                source = parse_tutorial(
                    body.youtube_url,
                    body.transcript,
                    body.title,
                    usage_rights_confirmed=body.usage_rights_confirmed,
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            project.update(
                tutorial=source,
                task=None,
                approved=False,
                completed_step_ids=[],
                error=None,
                status="ready",
                processing={
                    "stage": "source_ready",
                    "progress": 100,
                    "message": "Source metadata saved. YouTube playback is embedded; no video or captions were downloaded.",
                },
            )
            sessions.clear(project_id)
            return store.save_project(project)

    @api.post("/api/projects/{project_id}/screen-session/clear", status_code=204)
    def clear_screen(project_id: str):
        digital_project(project_id)
        sessions.clear(project_id)

    @api.post("/api/projects/{project_id}/screen-check", response_model=ScreenCheck)
    async def screen_check(
        project_id: str,
        request: Request,
        file: Annotated[UploadFile, File()],
        step_id: Annotated[str, Form()],
        cloud_consent: Annotated[bool, Form()] = False,
        source_scope: Annotated[str | None, Form(max_length=160)] = None,
        interface_version: Annotated[str | None, Form(max_length=120)] = None,
        retain_evidence: Annotated[bool, Form()] = False,
    ):
        # Anchor cancellation to receipt of this request. Sampling after an
        # asynchronous upload read would let a stopped upload adopt the next
        # session generation and later complete or retain a checkpoint.
        with sessions.lock:
            generation = getattr(request.state, "screen_generation", None)
            if generation is None:
                generation = sessions.generations.get(project_id, 0)
        project = digital_project(project_id)
        if not project["approved"] or not project["task"]:
            await file.close()
            raise HTTPException(409, "Review and approve the workflow before screen verification.")
        task = Task.model_validate(project["task"])
        step = next((item for item in task.steps if item.id == step_id), None)
        if step is None:
            await file.close()
            raise HTTPException(404, "Workflow step not found.")
        selected = mode["value"]
        if selected in {"meta", "nvidia"} and not cloud_consent:
            await file.close()
            raise HTTPException(422, "Explicit screen cloud-processing consent is required for the selected provider.")
        if selected == "meta":
            from app.providers.meta_screen import MetaScreenProvider

            provider = MetaScreenProvider(provider_for(selected))
        elif selected == "nvidia":
            from app.providers.nvidia import NvidiaScreenProvider

            provider = NvidiaScreenProvider(provider_for(selected))
        else:
            provider = None
        if file.content_type not in {"image/png", "image/jpeg", "image/webp"}:
            await file.close()
            raise HTTPException(415, "Screen captures must be PNG, JPEG, or WebP images.")
        try:
            content = await file.read(settings.max_image_bytes + 1)
        finally:
            await file.close()
        if len(content) > settings.max_image_bytes:
            raise HTTPException(413, "Screen capture exceeds the image size limit.")
        if await request.is_disconnected():
            raise HTTPException(409, "Screen request was stopped.")
        try:
            decode_image(content)
        except MediaError as exc:
            raise HTTPException(422, str(exc)) from None
        task_revision = hashlib.sha256(json.dumps(project["task"], sort_keys=True).encode()).hexdigest()
        key_prefix = (hashlib.sha256(content).hexdigest(), task_revision, step_id, selected, retain_evidence)
        key = (*key_prefix, tuple(project["completed_step_ids"]))
        with sessions.lock:
            if sessions.generations.get(project_id, 0) != generation:
                raise HTTPException(409, "Screen sharing was stopped; the pending capture was discarded.")
            previous = sessions.last(project_id)
            if previous and previous.get("key") == key:
                return previous["response"]
            if project_id in sessions.inflight:
                raise HTTPException(
                    429,
                    "A screen check is already running. Wait before retrying.",
                    headers={"Retry-After": "2"},
                )
            interval = settings.screen_nvidia_interval if selected == "nvidia" else settings.screen_meta_interval if selected == "meta" else settings.screen_local_interval
            if time.monotonic() - sessions.started.get(project_id, -1e9) < interval:
                raise HTTPException(
                    429,
                    "Screen checks are rate limited. Wait a moment and retry.",
                    headers={"Retry-After": str(math.ceil(interval))},
                )
            sessions.inflight.add(project_id)
            sessions.started[project_id] = time.monotonic()

        def analyze():
            from app.services.screen_observation import observe_screen
            from app.services.digital_verification import verify_screen
            from app.services.tutorials import instruction_warnings
            from app.services.screen_observation import redact_text

            started = time.perf_counter()
            observation = observe_screen(content, selected, provider, cloud_consent=cloud_consent)
            # Optional language generation must never hold the project/session
            # locks: Stop and workflow edits remain responsive during a call.
            # The authoritative decision below is recomputed against fresh progress.
            guidance = None
            proposed_result = None
            if selected in {"meta", "nvidia"}:
                from app.providers.grounded_explanation import explain_verification

                with sessions.lock:
                    if sessions.generations.get(project_id, 0) != generation:
                        raise HTTPException(409, "Screen sharing was stopped; the pending capture was discarded.")
                with configured_thresholds(settings):
                    proposed_result = verify_screen(step, observation, task, project["completed_step_ids"])
                guidance = explain_verification(provider.provider, step, proposed_result)
            with store.lock, sessions.lock:
                fresh = project_or_404(project_id)
                fresh_revision = hashlib.sha256(
                    json.dumps(fresh["task"], sort_keys=True).encode()
                ).hexdigest()
                if sessions.generations.get(project_id, 0) != generation:
                    raise HTTPException(409, "Screen sharing was stopped; the pending capture was discarded.")
                if (
                    not fresh["approved"]
                    or fresh["status"] == "processing"
                    or fresh_revision != task_revision
                ):
                    raise HTTPException(
                        409, "The workflow changed during analysis. Review it and capture again."
                    )
                with configured_thresholds(settings):
                    result = verify_screen(step, observation, task, fresh["completed_step_ids"])
                explanation_provider = "deterministic_template"
                # A changed progression invalidates a previously planned narrative.
                if guidance is not None and result == proposed_result:
                    result.explanation = guidance.text
                    explanation_provider = guidance.provider_mode
                    if guidance.warning:
                        result.warnings.append(guidance.warning)
                result.warnings = list(
                    dict.fromkeys(
                        result.warnings + instruction_warnings(step.description + " " + step.expected_state)
                    )
                )
                if result.status == "pass" and set(step.dependencies).issubset(fresh["completed_step_ids"]):
                    if step.id not in fresh["completed_step_ids"]:
                        fresh["completed_step_ids"].append(step.id)
                        store.save_project(fresh)
                elif result.status == "pass":
                    result.status = "uncertain"
                    result.reason = "skipped_step"
                    result.explanation = "This visible checkpoint matches, but its prerequisite steps have not been verified. Return to the earliest unverified checkpoint."
                from app.services.graph import available_steps

                eligible = available_steps(task.steps, fresh["completed_step_ids"])
                current = eligible[0].id if eligible else None
                remaining = [item for item in task.steps if item.id not in fresh["completed_step_ids"]]
                upcoming = next((item.id for item in remaining if item.id != current), None)
                verification = build_verification(
                    fresh, task, step, result, task_revision=task_revision,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    retained=retain_evidence, observation=observation, selected_mode=selected,
                    explanation_provider=explanation_provider,
                )
                if retain_evidence:
                    store.save_verification(verification.model_dump(mode="json"))
                response = ScreenCheck(
                    result=result,
                    observation=observation,
                    completed_step_ids=fresh["completed_step_ids"],
                    current_step_id=current,
                    upcoming_step_id=upcoming,
                    source_scope=redact_text(source_scope) if source_scope else None,
                    verification=verification,
                )
                if len(sessions.records) >= 64 and project_id not in sessions.records:
                    oldest = min(sessions.records, key=lambda item: sessions.records[item]["time"])
                    sessions.records.pop(oldest)
                sessions.records[project_id] = {
                    "key": (*key_prefix, tuple(fresh["completed_step_ids"])),
                    "revision": task_revision,
                    "time": time.monotonic(),
                    "response": response.model_dump(mode="json"),
                }
                return response

        try:
            return await run_in_threadpool(analyze)
        except HTTPException:
            raise
        except Exception as exc:
            from app.providers.meta import ProviderError

            if isinstance(exc, ProviderError):
                raise HTTPException(502, str(exc)) from None
            raise HTTPException(
                503,
                "Screen observation is unavailable. Pause sharing and retry; no checkpoint was completed.",
            ) from None
        finally:
            with sessions.lock:
                sessions.inflight.discard(project_id)

    @api.post("/api/projects/{project_id}/ask")
    def ask(project_id: str, body: AskInput):
        from app.services.screen_observation import redact_text
        from app.services.tutorials import instruction_warnings
        from app.services.graph import available_steps

        project = digital_project(project_id)
        if not project["task"]:
            raise HTTPException(409, "Extract and review a workflow first.")
        task = Task.model_validate(project["task"])
        record = sessions.last(project_id)
        revision = hashlib.sha256(json.dumps(project["task"], sort_keys=True).encode()).hexdigest()
        if record and record["revision"] != revision:
            record = None
        eligible = available_steps(task.steps, project["completed_step_ids"])
        step = eligible[0] if eligible else task.steps[-1]
        question = body.question.casefold()
        evidence = []
        warnings = instruction_warnings(body.question + " " + step.description)
        finished = all(item.id in project["completed_step_ids"] for item in task.steps)
        if finished:
            answer = "All approved checkpoints are verified. There is no next eligible step. Completion records describe the previously observed states; they do not establish hidden application or filesystem state."
            if record:
                evidence = record["response"]["result"]["evidence"][:8]
            else:
                warnings.append(
                    "No current screen evidence. This answer uses only recorded workflow progress."
                )
        elif record:
            last = record["response"]["result"]
            evidence = last["evidence"][:8]
            answer = last["explanation"]
            if any(word in question for word in ["next", "current", "what", "how"]):
                answer += (
                    f" Current eligible checkpoint: {step.title}. {step.expected_state or step.description}"
                )
        else:
            answer = f"The workflow's next eligible checkpoint is {step.title}. {step.expected_state or step.description} I do not have a current screen observation, so I cannot confirm your application's state."
            warnings.append("No current screen evidence. This answer uses only the reviewed workflow.")
        if any(word in question for word in ["filesystem", "hidden", "on disk"]):
            answer += " I can only inspect shared visible pixels; I cannot confirm hidden application data or filesystem contents."
        return {
            "answer": redact_text(answer),
            "evidence": [redact_text(item) for item in evidence],
            "warnings": list(dict.fromkeys(warnings)),
            "provider_mode": "grounded_template",
        }
