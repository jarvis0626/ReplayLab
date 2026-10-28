"""Shared workflow inspection, retained evidence, and human correction reports."""

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.schemas import Task
from app.services.graph import available_steps, validate_graph
from app.services.screen_observation import redact_text
from app.verification_contracts import (
    VerificationFeedback, VerificationFeedbackInput, WorkflowVerification,
)


def install_verification_routes(api, *, store, project_or_404):
    @api.get("/api/projects/{project_id}/verifications", response_model=list[WorkflowVerification])
    def verifications(project_id: str):
        project_or_404(project_id)
        return store.verifications(project_id)

    @api.get("/api/projects/{project_id}/workflow")
    def workflow(project_id: str):
        project = project_or_404(project_id)
        if not project["task"]:
            raise HTTPException(409, "Extract and review a workflow first.")
        task = Task.model_validate(project["task"])
        task_revision = hashlib.sha256(json.dumps(project["task"], sort_keys=True).encode()).hexdigest()
        records = store.verifications(project_id)
        eligible = {step.id for step in available_steps(task.steps, project["completed_step_ids"])}
        return {
            "id": project_id, "task": task.model_dump(mode="json"),
            "source_video": project["video"], "source_tutorial": project.get("tutorial"),
            "approved": project["approved"], "task_revision": task_revision,
            "completed_step_ids": project["completed_step_ids"],
            "order": validate_graph(task.steps),
            "steps": [{
                **step.model_dump(mode="json"),
                "progression": "completed" if step.id in project["completed_step_ids"] else
                    "current" if step.id in eligible else "pending",
                "latest_verification": next((record for record in records
                    if record["step_id"] == step.id and record["task_revision"] == task_revision), None),
            } for step in task.steps],
            "evidence_retention": {
                "digital_default": "transient; ten-minute RAM session, cleared when sharing stops",
                "retained": "explicit opt-in relevant redacted evidence; no screenshots; newest 100 per workflow",
                "deletion": "deleting this workflow removes saved evidence and correction reports",
            },
        }

    @api.post("/api/projects/{project_id}/verifications/{verification_id}/feedback",
              response_model=VerificationFeedback, status_code=201)
    def feedback(project_id: str, verification_id: str, body: VerificationFeedbackInput):
        with store.lock:
            project_or_404(project_id)
            found = next((item for item in store.verifications(project_id)
                          if item["id"] == verification_id), None)
            if found is None:
                sessions = getattr(api.state, "screen_sessions", None)
                last = sessions.last(project_id) if sessions else None
                transient = last["response"].get("verification") if last else None
                if transient and transient["id"] == verification_id:
                    found = transient
            if found is None:
                raise HTTPException(404, "Verification evidence is no longer available. Capture again or choose a retained record.")
            existing = next((item for item in store.feedback(project_id)
                             if item["verification_id"] == verification_id), None)
            report = VerificationFeedback(
                id=existing["id"] if existing else uuid4().hex,
                verification_id=verification_id, expected_verdict=body.expected_verdict,
                notes=redact_text(body.notes), created_at=datetime.now(timezone.utc).isoformat(),
            )
            # Reporting does not replace a deterministic verdict or mark a step complete.
            return store.save_feedback(project_id, report.model_dump(mode="json"))

    @api.get("/api/projects/{project_id}/verification-feedback", response_model=list[VerificationFeedback])
    def feedback_reports(project_id: str):
        project_or_404(project_id)
        return store.feedback(project_id)
