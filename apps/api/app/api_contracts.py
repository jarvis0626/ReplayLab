from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas import Task, VerificationResult


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    modality: Literal["physical", "digital"] = "physical"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Project name cannot be blank.")
        return value.strip()


class Consent(RequestModel):
    cloud_consent: bool = False
    comparable: bool | None = None
    visibility_confirmed: bool = False


class Approval(RequestModel):
    approved: bool


class ProviderChoice(RequestModel):
    mode: Literal["mock", "meta"]


class VideoInfo(BaseModel):
    url: str
    duration: float
    width: int
    height: int
    original_name: str


class FrameInfo(BaseModel):
    id: str
    url: str
    timestamp: float


class Project(BaseModel):
    id: str
    name: str
    created_at: str
    status: Literal["new", "processing", "ready", "error"]
    error: str | None = None
    video: VideoInfo | None = None
    frames: list[FrameInfo] = Field(default_factory=list)
    task: Task | None = None
    approved: bool = False
    completed_step_ids: list[str] = Field(default_factory=list)
    attempt_count: int = 0
    processing: dict = Field(default_factory=dict)
    modality: Literal["physical", "digital"] = "physical"
    tutorial: dict | None = None


class Attempt(BaseModel):
    id: str
    project_id: str
    step_id: str
    image_url: str
    created_at: str
    status: Literal["ready", "verifying", "verified", "error"] = "ready"
    result: VerificationResult | None = None
    error: str | None = None
    reference_observations: list[dict] = Field(default_factory=list)
    analysis: dict = Field(default_factory=dict)
    task_revision: str
