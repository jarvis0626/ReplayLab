import copy
import hashlib
import json
import logging
import re
import shutil
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import cv2
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from app.api_contracts import Approval, Attempt, Consent, Project, ProjectCreate, ProviderChoice
from app.core.config import Settings
from app.core.store import Store
from app.providers.mock import MockProvider
from app.schemas import Task
from app.services.demo import ensure_demo, register_demo_frames
from app.services.graph import available_steps, validate_graph
from app.services.media import (
    MediaError,
    decode_image,
    extract_frames,
    inspect_video,
    measured_quality,
    prepare_meta_video,
)
from app.services.verification import verify
from app.services.thresholds import configured_thresholds
from app.services.verification_records import build_verification

logger = logging.getLogger("replaylab")
VIDEO_MIME = {
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "video/x-msvideo": ".avi",
    "video/avi": ".avi",
}
IMAGE_MIME = {"image/png", "image/jpeg", "image/webp"}
SAFE_ID = re.compile(r"^[a-f0-9]{32}$")
SAFE_FILE = re.compile(r"^(?:video|frame|attempt)-[a-f0-9]{32}\.(?:mp4|mov|webm|avi|png)$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def revision(task: dict) -> str:
    return hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    data_directory = settings.data_dir.resolve()
    media_directory = data_directory / "media"
    demo_directory = data_directory / "demo"
    media_directory.mkdir(parents=True, exist_ok=True)
    store = Store(data_directory / "replaylab.sqlite3")
    mode = {"value": settings.ai_provider if settings.ai_provider in {"mock", "meta"} else "mock"}
    job_locks: dict[str, threading.RLock] = {}

    @asynccontextmanager
    async def lifespan(application):
        for project in store.projects():
            if project["status"] == "processing":
                project.update(
                    status="error",
                    error="Processing was interrupted by a server restart. Upload or extract again.",
                )
                store.save_project(project)
            for attempt in store.attempts(project["id"]):
                if attempt["status"] == "verifying":
                    attempt.update(
                        status="error", error="Verification was interrupted. Retry this checkpoint."
                    )
                    store.save_attempt(attempt)
        yield
        store.engine.dispose()

    api = FastAPI(title="ReplayLab API", version="3.0.0", lifespan=lifespan)
    api.state.store = store
    api.state.settings = settings
    api.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @api.middleware("http")
    async def request_limits(request: Request, call_next):
        # FastAPI parses multipart before entering a route. Anchor cancellation
        # before that parse so Stop also invalidates a capture still uploading.
        screen_request = re.fullmatch(r"/api/projects/([a-f0-9]{32})/screen-check", request.url.path)
        sessions = getattr(api.state, "screen_sessions", None)
        if request.method == "POST" and screen_request and sessions is not None:
            with sessions.lock:
                request.state.screen_generation = sessions.generations.get(screen_request.group(1), 0)
        length = request.headers.get("content-length")
        limit = (
            settings.max_video_bytes + 2 * 1024 * 1024
            if "multipart/form-data" in request.headers.get("content-type", "")
            else 512 * 1024
        )
        if length and (not length.isdigit() or int(length) > limit):
            return JSONResponse({"detail": "Request exceeds the configured upload limit."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "private, no-store"
        return response

    @api.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Omit submitted inputs/context to avoid echoing content or internal values.
        return JSONResponse(
            {
                "detail": [
                    {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
            status_code=422,
        )

    def project_or_404(project_id: str) -> dict:
        if not SAFE_ID.fullmatch(project_id):
            raise HTTPException(404, "Project not found.")
        project = store.project(project_id)
        if project is None:
            raise HTTPException(404, "Project not found.")
        return project

    def attempt_or_404(attempt_id: str) -> dict:
        attempt = store.attempt(attempt_id) if SAFE_ID.fullmatch(attempt_id) else None
        if attempt is None:
            raise HTTPException(404, "Attempt not found.")
        project_or_404(attempt["project_id"])
        return attempt

    def lock_for(project_id: str):
        with store.lock:
            return job_locks.setdefault(project_id, threading.RLock())

    def require_idle(project: dict):
        if project["status"] == "processing":
            raise HTTPException(409, "This project is processing. Wait for completion before changing it.")

    def provider_status() -> dict:
        selected = mode["value"]
        configured = bool(settings.model_api_key) if selected == "meta" else True
        return {
            "mode": selected,
            "configured": configured,
            "available": selected == "mock",
            "live_verified": False,
            "message": "MOCK reasoning — physical fixtures and local OCR for digital screens; no live Meta inference."
            if selected == "mock"
            else (
                "Meta credentials configured. Live availability must be confirmed by an actual request."
                if configured
                else "Meta API key is missing. Configure MODEL_API_KEY on the server or select mock mode."
            ),
            "models": ["muse-spark-1.3", "sam-3.1"] if selected == "meta" else [],
        }

    def provider_for(selected: str):
        if selected == "mock":
            return MockProvider(demo_directory)
        if not settings.model_api_key:
            raise HTTPException(
                503,
                "Meta API credentials are missing. Configure MODEL_API_KEY or explicitly select mock mode.",
            )
        from app.providers.meta import MetaProvider

        return MetaProvider(
            settings.model_api_key, data_directory / "inference-cache", base_url=settings.meta_base_url
        )

    def require_consent(selected: str, consent: bool):
        if selected == "meta" and not consent:
            raise HTTPException(
                422, "Explicit cloud-processing consent is required before sending media to Meta."
            )

    def new_project(name: str, modality: str = "physical") -> dict:
        document = Project(
            id=uuid4().hex, name=name, created_at=now(), status="new", modality=modality
        ).model_dump(mode="json")
        (media_directory / document["id"]).mkdir(parents=True, exist_ok=True)
        return store.save_project(document)

    def set_error(project_id: str, message: str):
        store.mutate_project(
            project_id,
            lambda project: project.update(
                status="error",
                error=message,
                processing={"stage": "error", "progress": 0, "message": message},
            ),
        )

    def process_video(project_id: str, filename: str, original_name: str, known_demo: bool = False):
        with lock_for(project_id):
            path = media_directory / project_id / filename
            try:
                metadata = inspect_video(path, settings.max_video_seconds)
                frames = extract_frames(path, path.parent, metadata, project_id)
                if known_demo:
                    register_demo_frames(demo_directory, frames, path.parent)

                def update(project):
                    project.update(
                        video={
                            "url": f"/api/media/{project_id}/{filename}",
                            "original_name": original_name,
                            **metadata,
                        },
                        frames=frames,
                        task=None,
                        approved=False,
                        completed_step_ids=[],
                        status="ready",
                        error=None,
                        processing={
                            "stage": "frames_ready",
                            "progress": 100,
                            "message": "Four real reference frames extracted.",
                        },
                    )

                store.mutate_project(project_id, update)
            except MediaError as exc:
                path.unlink(missing_ok=True)
                set_error(project_id, str(exc))
            except Exception:
                logger.error("video_processing_failed project=%s", project_id)
                set_error(
                    project_id,
                    "Video processing failed. Check FFmpeg installation and retry with supported media.",
                )

    def process_extraction(project_id: str, selected: str):
        with lock_for(project_id):
            project = store.project(project_id)
            if project is None:
                return
            try:
                provider = provider_for(selected)
                path = (
                    media_directory / project_id / project["video"]["url"].rsplit("/", 1)[-1]
                    if project["video"]
                    else None
                )
                if selected == "meta" and path:
                    path = prepare_meta_video(path)
                if project.get("modality", "physical") == "digital":
                    from app.providers.digital_reasoner import extract_workflow

                    task = extract_workflow(project, provider, selected, path)
                else:
                    task = Task.model_validate(provider.extract_task(path, project["frames"]))
                validate_task_media(task, project, require_rules=task.modality == "physical")
                store.mutate_project(
                    project_id,
                    lambda document: document.update(
                        task=task.model_dump(mode="json"),
                        approved=False,
                        completed_step_ids=[],
                        status="ready",
                        error=None,
                        processing={
                            "stage": "task_ready",
                            "progress": 100,
                            "message": "Review proposed steps and approve before practice.",
                        },
                    ),
                )
            except HTTPException as exc:
                set_error(project_id, str(exc.detail))
            except MediaError as exc:
                set_error(project_id, str(exc))
            except (ValueError, ValidationError):
                set_error(project_id, "The provider returned an invalid task. No instructions were approved.")
            except Exception as exc:
                from app.providers.meta import ProviderError

                message = (
                    str(exc)
                    if isinstance(exc, ProviderError)
                    else "Task extraction failed. Retry or explicitly choose mock mode."
                )
                set_error(project_id, message)

    def validate_task_media(task: Task, project: dict, require_rules: bool = True):
        if task.modality != project.get("modality", "physical"):
            raise HTTPException(422, "Workflow modality must match its project.")
        frame_ids = {frame["id"] for frame in project["frames"]}
        for step in task.steps:
            if require_rules and not (step.screen_rules if task.modality == "digital" else step.rules):
                raise HTTPException(422, "Each step requires at least one observable checkpoint rule.")
            if step.reference_frame_id is not None and step.reference_frame_id not in frame_ids:
                raise HTTPException(422, "Each step must reference an extracted frame from this project.")
            if task.modality == "physical" and step.reference_frame_id is None:
                raise HTTPException(422, "Physical steps require an extracted reference frame.")
            if project["video"] and step.timestamp_end > project["video"]["duration"] + 0.05:
                raise HTTPException(422, "Step timestamps must be within the source video.")

    @api.get("/api/health")
    def health():
        return {
            "status": "ok",
            "provider": provider_status(),
            "version": "3.0.0",
            "privacy": "Local single-user development server; no public authentication.",
        }

    @api.post("/api/provider")
    def select_provider(choice: ProviderChoice):
        if any(project["status"] == "processing" for project in store.projects()):
            raise HTTPException(409, "Wait for processing jobs before changing the provider.")
        mode["value"] = choice.mode
        return {"provider": provider_status()}

    @api.get("/api/projects", response_model=list[Project])
    def list_projects():
        return store.projects()

    @api.post("/api/projects", response_model=Project, status_code=201)
    def create_project(body: ProjectCreate):
        return new_project(body.name, body.modality)

    @api.post("/api/projects/demo", response_model=Project, status_code=201)
    def create_demo():
        manifest = ensure_demo(demo_directory)
        project = new_project("Four-block assembly · demo")
        filename = f"video-{uuid4().hex}.mp4"
        shutil.copyfile(demo_directory / manifest["video"], media_directory / project["id"] / filename)
        process_video(project["id"], filename, "ReplayLab synthetic assembly.mp4", known_demo=True)
        ready = project_or_404(project["id"])
        if ready["status"] != "error":
            # Demo always uses explicit mock provenance even if the active provider is Meta.
            task = MockProvider(demo_directory).extract_task(
                media_directory / project["id"] / filename, ready["frames"]
            )
            ready.update(task=task.model_dump(mode="json"), status="ready")
            store.save_project(ready)
        return ready

    @api.get("/api/projects/{project_id}", response_model=Project)
    def get_project(project_id: str):
        return project_or_404(project_id)

    @api.get("/api/projects/{project_id}/processing-status")
    def processing_status(project_id: str):
        project = project_or_404(project_id)
        return {"status": project["status"], "error": project["error"], **project["processing"]}

    @api.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str):
        project = project_or_404(project_id)
        require_idle(project)
        with lock_for(project_id):
            project = project_or_404(project_id)
            require_idle(project)
            if any(attempt["status"] == "verifying" for attempt in store.attempts(project_id)):
                raise HTTPException(409, "Wait for checkpoint verification before deleting this project.")
            target = (media_directory / project_id).resolve()
            if target.parent != media_directory.resolve():
                raise HTTPException(400, "Invalid project media identifier.")
            shutil.rmtree(target, ignore_errors=True)
            # Shared inference cache can contain derived private media. Clear it
            # conservatively on deletion; other projects can safely refill it.
            cache = (data_directory / "inference-cache").resolve()
            if cache.parent == data_directory:
                shutil.rmtree(cache, ignore_errors=True)
            store.delete_project(project_id)
            if hasattr(api.state, "screen_sessions"):
                api.state.screen_sessions.clear(project_id)
            from app.services.screen_observation import clear_screen_cache

            clear_screen_cache()

    async def save_upload(upload: UploadFile, path: Path, limit: int):
        total = 0
        try:
            with path.open("wb") as output:
                while chunk := await upload.read(1024 * 1024):
                    total += len(chunk)
                    if total > limit:
                        raise HTTPException(413, "The uploaded file exceeds the configured size limit.")
                    output.write(chunk)
            if total == 0:
                raise HTTPException(422, "The uploaded file is empty.")
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    @api.post("/api/projects/{project_id}/video", response_model=Project, status_code=202)
    async def upload_video(
        project_id: str,
        background_tasks: BackgroundTasks,
        file: Annotated[UploadFile, File()],
        usage_rights_confirmed: Annotated[bool, Form()] = False,
    ):
        project = project_or_404(project_id)
        require_idle(project)
        if project.get("modality") == "digital" and not usage_rights_confirmed:
            await file.close()
            raise HTTPException(422, "Confirm that you have appropriate rights to use this tutorial video.")
        if file.content_type not in VIDEO_MIME:
            await file.close()
            raise HTTPException(415, "Supported video types are MP4, MOV, WebM, and AVI.")
        filename = f"video-{uuid4().hex}{VIDEO_MIME[file.content_type]}"
        original = re.split(r"[\\/]", file.filename or "video")[-1]
        original = "".join(character for character in original if character.isprintable())[:160]
        with store.lock:
            project = project_or_404(project_id)
            require_idle(project)
            project.update(
                status="processing",
                error=None,
                approved=False,
                completed_step_ids=[],
                task=None,
                processing={
                    "stage": "uploading",
                    "progress": 5,
                    "message": "Saving and validating uploaded media.",
                },
            )
            if project.get("modality") == "digital":
                project["tutorial"] = project.get("tutorial") or {
                    "kind": "upload",
                    "title": original,
                    "transcript_segments": [],
                }
                project["tutorial"]["usage_rights_confirmed"] = True
                project["tutorial"]["uploaded_video_rights_confirmed"] = True
            store.save_project(project)
        try:
            await save_upload(file, media_directory / project_id / filename, settings.max_video_bytes)
        except HTTPException as exc:
            set_error(project_id, str(exc.detail))
            raise
        background_tasks.add_task(process_video, project_id, filename, original)
        return copy.deepcopy(project)

    @api.post("/api/projects/{project_id}/extract", response_model=Project, status_code=202)
    def extract(project_id: str, consent: Consent, background_tasks: BackgroundTasks):
        with store.lock:
            project = project_or_404(project_id)
            require_idle(project)
            digital_source = project.get("modality") == "digital" and (project.get("tutorial") or {}).get(
                "transcript_segments"
            )
            if not digital_source and (not project["video"] or not project["frames"]):
                raise HTTPException(409, "Upload and process a video before extracting steps.")
            selected = mode["value"]
            require_consent(selected, consent.cloud_consent)
            provider_for(selected)
            project.update(
                status="processing",
                error=None,
                approved=False,
                completed_step_ids=[],
                processing={
                    "stage": "extracting",
                    "progress": 45,
                    "message": "Generating proposed task steps for review.",
                },
            )
            store.save_project(project)
        background_tasks.add_task(process_extraction, project_id, selected)
        return copy.deepcopy(project)

    @api.put("/api/projects/{project_id}/task", response_model=Project)
    def update_task(project_id: str, task: Task):
        with store.lock:
            project = project_or_404(project_id)
            require_idle(project)
            validate_task_media(task, project, require_rules=task.modality == "physical")
            task.provenance = {**task.provenance, "user_edited": True}
            project.update(task=task.model_dump(mode="json"), approved=False, completed_step_ids=[])
            store.save_project(project)
            if hasattr(api.state, "screen_sessions"):
                api.state.screen_sessions.clear(project_id)
            return project

    @api.patch("/api/projects/{project_id}/steps/{step_id}", response_model=Project)
    def update_step(project_id: str, step_id: str, changes: dict):
        project = project_or_404(project_id)
        require_idle(project)
        if not project["task"]:
            raise HTTPException(409, "Extract a task first.")
        task = copy.deepcopy(project["task"])
        position = next((index for index, step in enumerate(task["steps"]) if step["id"] == step_id), None)
        if position is None:
            raise HTTPException(404, "Step not found.")
        if "id" in changes and changes["id"] != step_id:
            raise HTTPException(422, "Step identifiers cannot be changed through this route.")
        try:
            task["steps"][position].update(changes)
            validated = Task.model_validate(task)
        except (ValueError, ValidationError):
            raise HTTPException(422, "The step update violates task schema or graph dependencies.") from None
        return update_task(project_id, validated)

    @api.post("/api/projects/{project_id}/approve", response_model=Project)
    def approve(project_id: str, body: Approval):
        with store.lock:
            project = project_or_404(project_id)
            require_idle(project)
            if not project["task"]:
                raise HTTPException(409, "Extract and review a task before approval.")
            validate_task_media(Task.model_validate(project["task"]), project)
            project["approved"] = body.approved
            store.save_project(project)
            if hasattr(api.state, "screen_sessions"):
                api.state.screen_sessions.clear(project_id)
            return project

    @api.get("/api/projects/{project_id}/graph")
    def graph(project_id: str):
        project = project_or_404(project_id)
        if not project["task"]:
            return {"nodes": [], "edges": [], "order": []}
        task = Task.model_validate(project["task"])
        available = {step.id for step in available_steps(task.steps, project["completed_step_ids"])}
        return {
            "nodes": [
                {
                    **step.model_dump(mode="json"),
                    "status": "completed"
                    if step.id in project["completed_step_ids"]
                    else "current"
                    if step.id in available
                    else "pending",
                }
                for step in task.steps
            ],
            "edges": [
                {"source": dependency, "target": step.id}
                for step in task.steps
                for dependency in step.dependencies
            ],
            "order": validate_graph(task.steps),
        }

    @api.post("/api/projects/{project_id}/attempts", response_model=Attempt, status_code=201)
    async def create_attempt(
        project_id: str, step_id: Annotated[str, Form()], file: Annotated[UploadFile, File()]
    ):
        project = project_or_404(project_id)
        require_idle(project)
        if project.get("modality") == "digital":
            await file.close()
            raise HTTPException(409, "Use the screen assistant to verify digital workflows.")
        if not project["approved"] or not project["task"]:
            raise HTTPException(409, "Review and approve the task before creating a checkpoint.")
        task = Task.model_validate(project["task"])
        step = next((item for item in task.steps if item.id == step_id), None)
        if not step:
            raise HTTPException(404, "Step not found.")
        if not set(step.dependencies).issubset(project["completed_step_ids"]):
            raise HTTPException(409, "Complete this step's prerequisites first.")
        if file.content_type not in IMAGE_MIME:
            await file.close()
            raise HTTPException(415, "Checkpoint must be a PNG, JPEG, or WebP image.")
        attempt_id = uuid4().hex
        path = media_directory / project_id / f"attempt-{attempt_id}.png"
        await save_upload(file, path, settings.max_image_bytes)
        try:
            image = decode_image(path.read_bytes())
            if not cv2.imwrite(str(path), image):
                raise MediaError("Checkpoint could not be saved.")
        except MediaError as exc:
            path.unlink(missing_ok=True)
            raise HTTPException(422, str(exc)) from None
        attempt = Attempt(
            id=attempt_id,
            project_id=project_id,
            step_id=step_id,
            image_url=f"/api/media/{project_id}/{path.name}",
            created_at=now(),
            task_revision=revision(project["task"]),
        ).model_dump(mode="json")
        store.save_attempt(attempt)
        store.mutate_project(
            project_id, lambda document: document.update(attempt_count=document["attempt_count"] + 1)
        )
        return attempt

    @api.get("/api/projects/{project_id}/attempts", response_model=list[Attempt])
    def list_attempts(project_id: str):
        project_or_404(project_id)
        return store.attempts(project_id)

    @api.get("/api/attempts/{attempt_id}", response_model=Attempt)
    def get_attempt(attempt_id: str):
        return attempt_or_404(attempt_id)

    @api.post("/api/attempts/{attempt_id}/verify", response_model=Attempt)
    def verify_attempt(attempt_id: str, consent: Consent):
        attempt = attempt_or_404(attempt_id)
        project_id = attempt["project_id"]
        with lock_for(project_id):
            project = project_or_404(project_id)
            require_idle(project)
            if not project["approved"] or revision(project["task"]) != attempt["task_revision"]:
                raise HTTPException(
                    409, "The task changed after this checkpoint. Review, approve, and capture a new attempt."
                )
            task = Task.model_validate(project["task"])
            step = next(item for item in task.steps if item.id == attempt["step_id"])
            if not set(step.dependencies).issubset(project["completed_step_ids"]):
                raise HTTPException(409, "Complete the prerequisites before verifying this step.")
            selected = mode["value"]
            require_consent(selected, consent.cloud_consent)
            provider = provider_for(selected)
            attempt.update(status="verifying", error=None, result=None, verification=None)
            store.save_attempt(attempt)
            try:
                started = time.perf_counter()
                frame = next(frame for frame in project["frames"] if frame["id"] == step.reference_frame_id)
                reference_path = media_directory / project_id / frame["url"].rsplit("/", 1)[-1]
                current_path = media_directory / project_id / attempt["image_url"].rsplit("/", 1)[-1]
                prompts = list(
                    dict.fromkeys(
                        step.object_labels
                        + [rule.subject for rule in step.rules]
                        + [rule.target for rule in step.rules if rule.target]
                    )
                )
                reference = provider.observe(reference_path, prompts)
                current = provider.observe(current_path, prompts)
                if consent.comparable is False:
                    current.comparable = False
                if selected == "meta":
                    for observed, path in [(reference, reference_path), (current, current_path)]:
                        observed.image_quality = measured_quality(path)
                        # The user supplies viewpoint/visibility evidence; SAM does not measure these.
                        observed.comparable = consent.comparable
                        if consent.visibility_confirmed:
                            observed.visibility = 1.0
                        observed.provenance.update(
                            user_viewpoint_attestation=consent.comparable,
                            user_visibility_attestation=consent.visibility_confirmed,
                            quality_source="Laplacian sharpness and exposure heuristic; not calibrated model confidence",
                        )
                with configured_thresholds(settings):
                    result = verify(step, reference, current)
                result.explanation = provider.explain(result)
                with store.lock:
                    fresh = project_or_404(project_id)
                    if (
                        not fresh["approved"]
                        or fresh["status"] == "processing"
                        or revision(fresh["task"]) != attempt["task_revision"]
                    ):
                        raise HTTPException(
                            409,
                            "The task changed during verification. Review, approve, and capture a new checkpoint.",
                        )
                    verification = build_verification(
                        fresh, task, step, result, task_revision=attempt["task_revision"],
                        latency_ms=(time.perf_counter() - started) * 1000,
                        retained=True, selected_mode=selected,
                        explanation_provider="meta_grounded" if getattr(
                            provider, "last_explanation_provenance", {}
                        ).get("provider") == "meta" else "deterministic_template",
                    )
                    attempt.update(
                        status="verified",
                        result=result.model_dump(mode="json"),
                        verification=verification.model_dump(mode="json"),
                        reference_observations=[
                            item.model_dump(mode="json") for item in reference.observations
                        ],
                        analysis={
                            "reference": reference.model_dump(mode="json", exclude={"observations"}),
                            "checkpoint": current.model_dump(mode="json", exclude={"observations"}),
                            "explanation": getattr(
                                provider,
                                "last_explanation_provenance",
                                {"provider": "deterministic mock template"},
                            ),
                        },
                    )
                    store.save_attempt(attempt)
                    store.save_verification(verification.model_dump(mode="json"))
                    if result.status == "pass":

                        def complete(document):
                            if step.id not in document["completed_step_ids"]:
                                document["completed_step_ids"].append(step.id)

                        store.mutate_project(project_id, complete)
                return attempt
            except HTTPException as exc:
                attempt.update(status="error", error=str(exc.detail), result=None)
                store.save_attempt(attempt)
                raise
            except Exception as exc:
                from app.providers.meta import ProviderError

                message = (
                    str(exc)
                    if isinstance(exc, ProviderError)
                    else "Checkpoint analysis failed. No step was completed. Retry or check provider availability."
                )
                attempt.update(status="error", error=message)
                store.save_attempt(attempt)
                raise HTTPException(502, message) from None

    @api.get("/api/projects/{project_id}/evaluation")
    def evaluation(project_id: str):
        project_or_404(project_id)
        from app.services.evaluation import run_evaluation

        return run_evaluation()

    @api.get("/api/demo/fixtures")
    def fixtures():
        return ensure_demo(demo_directory)["fixtures"]

    @api.get("/api/demo/fixtures/{fixture_id}/image")
    def fixture_image(fixture_id: str):
        manifest = ensure_demo(demo_directory)
        if fixture_id not in {item["id"] for item in manifest["fixtures"]}:
            raise HTTPException(404, "Fixture not found.")
        return FileResponse(demo_directory / f"{fixture_id}.png", media_type="image/png")

    @api.get("/api/demo/video")
    def demo_video():
        manifest = ensure_demo(demo_directory)
        return FileResponse(
            demo_directory / manifest["video"],
            media_type="video/mp4",
            filename="replaylab-synthetic-demo.mp4",
        )

    @api.get("/api/media/{project_id}/{filename}")
    def get_media(project_id: str, filename: str):
        project_or_404(project_id)
        if not SAFE_FILE.fullmatch(filename):
            raise HTTPException(404, "Media not found.")
        path = media_directory / project_id / filename
        if not path.is_file():
            raise HTTPException(404, "Media not found.")
        return FileResponse(path)

    from app.digital_api import install_digital_routes

    install_digital_routes(
        api,
        settings=settings,
        store=store,
        media_directory=media_directory,
        data_directory=data_directory,
        mode=mode,
        provider_for=provider_for,
        project_or_404=project_or_404,
        new_project=new_project,
        require_idle=require_idle,
    )
    from app.v3_api import install_verification_routes

    install_verification_routes(api, store=store, project_or_404=project_or_404)
    from app.evaluation_api import register_evaluation_routes

    register_evaluation_routes(api)
    return api


app = create_app()
