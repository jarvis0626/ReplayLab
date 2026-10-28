"""One inspectable verification envelope for physical and digital checkpoints."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal["pass", "fail", "uncertain"]
Mismatch = Literal[
    "expected_ui_not_found", "unexpected_ui_state", "possible_version_mismatch",
    "confirmed_version_mismatch", "insufficient_visual_evidence",
]


class VerificationContract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ConstraintEvaluation(VerificationContract):
    id: str
    kind: str
    verdict: Verdict
    expected: str
    observed: str
    evidence: list[str] = Field(default_factory=list)
    correction: str | None = None


class EvidenceReference(VerificationContract):
    id: str
    kind: Literal["visible_observation", "reference_frame", "constraint"]
    text: str
    source: str
    timestamp: float | None = None


class VerificationProvider(VerificationContract):
    mode: str
    observation: str
    explanation: str


class WorkflowVerification(VerificationContract):
    id: str
    workflow_id: str
    task_id: str
    step_id: str
    modality: Literal["physical", "digital"]
    verdict: Verdict
    expected_conditions: list[str]
    observed_conditions: list[str]
    constraints: list[ConstraintEvaluation]
    evidence_references: list[EvidenceReference]
    uncertainty_reasons: list[str]
    correction: str | None
    explanation: str
    provider: VerificationProvider
    mismatch_classification: Mismatch | None = None
    latency_ms: float = Field(ge=0)
    created_at: str
    task_revision: str
    retained: bool = False


class VerificationFeedbackInput(VerificationContract):
    expected_verdict: Verdict
    notes: str = Field(default="", max_length=1000)


class VerificationFeedback(VerificationFeedbackInput):
    id: str
    verification_id: str
    created_at: str
