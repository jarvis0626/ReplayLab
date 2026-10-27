"""Screen evidence contracts independent of the physical observation schemas."""

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ScreenStatus = Literal["pass", "fail", "uncertain"]
ScreenKind = Literal["text_present", "text_absent", "window", "path", "selection", "error_absent"]
ScreenRole = Literal["text", "window", "dialog", "button", "path", "error", "selection"]
ScreenReason = Literal[
    "completed",
    "mismatch",
    "insufficient_evidence",
    "interface_mismatch",
    "unexpected_dialog",
    "skipped_step",
    "unsafe_instruction",
]


class DigitalContract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class ScreenRule(DigitalContract):
    id: str = Field(min_length=1, max_length=120)
    kind: ScreenKind
    expected: str = Field(min_length=1, max_length=500)
    alternatives: list[str] = Field(default_factory=list, max_length=30)
    contradictions: list[str] = Field(default_factory=list, max_length=30)
    description: str = Field(default="", max_length=1500)

    @field_validator("alternatives", "contradictions")
    @classmethod
    def valid_phrases(cls, values):
        if any(not phrase.strip() or len(phrase) > 500 for phrase in values):
            raise ValueError("Screen phrases must be nonempty and at most 500 characters.")
        return [phrase.strip() for phrase in values]


class ScreenElement(DigitalContract):
    text: str = Field(min_length=1, max_length=4000)
    role: ScreenRole = "text"
    bbox: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str = "unknown"

    @field_validator("bbox")
    @classmethod
    def normalized_box(cls, value):
        if value is None:
            return value
        x1, y1, x2, y2 = value
        if not all(math.isfinite(number) and 0 <= number <= 1 for number in value) or x1 >= x2 or y1 >= y2:
            raise ValueError("Screen boxes require normalized finite x1 < x2 and y1 < y2.")
        return value


class ScreenObservation(DigitalContract):
    elements: list[ScreenElement] = Field(default_factory=list, max_length=500)
    visible_text: str = Field(default="", max_length=100000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    image_quality: float | None = Field(default=None, ge=0, le=1)
    provider_mode: str = "mock"
    interface_version: str | None = Field(default=None, max_length=120)
    complete: bool = False
    provenance: dict[str, Any] = Field(default_factory=dict)


class ScreenRuleResult(DigitalContract):
    rule_id: str
    status: ScreenStatus
    expected: str
    observed: str
    evidence: list[str] = Field(default_factory=list)
    correction: str | None = None


class ScreenResult(DigitalContract):
    step_id: str
    status: ScreenStatus
    rule_results: list[ScreenRuleResult] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    explanation: str
    provider_mode: str
    reason: ScreenReason | None = None
    observed_step_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
