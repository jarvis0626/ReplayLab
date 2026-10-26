"""Validated contracts shared by providers, persistence, and deterministic logic."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["pass", "fail", "uncertain"]
RuleKind = Literal["presence", "count", "above", "below", "left", "right", "near", "aligned", "color"]
BBox = tuple[float, float, float, float]


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class Observation(Contract):
    label: str = Field(min_length=1, max_length=120)
    bbox: BBox
    confidence: float | None = Field(default=None, ge=0, le=1)
    track_id: str | None = None
    mask_rle: dict[str, Any] | None = None
    timestamp: float | None = Field(default=None, ge=0)
    source: str = "unknown"
    provider: str = "unknown"
    color: str | None = None
    color_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("bbox")
    @classmethod
    def valid_box(cls, value: BBox) -> BBox:
        x1, y1, x2, y2 = value
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in value):
            raise ValueError("Bounding box coordinates must be finite and normalized to [0, 1].")
        if x1 >= x2 or y1 >= y2:
            raise ValueError("Bounding boxes require x1 < x2 and y1 < y2.")
        return value

    @field_validator("label")
    @classmethod
    def clean_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("An observation label cannot be blank.")
        return value


class ObservationSet(Contract):
    observations: list[Observation] = Field(default_factory=list)
    visibility: float | None = Field(default=None, ge=0, le=1)
    coverage: float | None = Field(default=None, ge=0, le=1)
    image_quality: float | None = Field(default=None, ge=0, le=1)
    comparable: bool | None = None
    provider_mode: str = "mock"
    provenance: dict[str, Any] = Field(default_factory=dict)


class Rule(Contract):
    id: str = Field(min_length=1, max_length=120)
    kind: RuleKind
    subject: str = Field(min_length=1, max_length=120)
    target: str | None = None
    value: float | str | bool | None = None
    tolerance: float = Field(default=0.04, gt=0, le=0.5)

    @model_validator(mode="after")
    def valid_rule(self) -> Rule:
        if self.kind in {"above", "below", "left", "right", "near", "aligned"}:
            if not self.target or self.target.casefold() == self.subject.casefold():
                raise ValueError("A relationship rule requires a distinct target label.")
        if self.kind == "presence" and self.value is not None and not isinstance(self.value, bool):
            raise ValueError("Presence value must be a boolean or omitted.")
        if self.kind == "count":
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise ValueError("Count rules require a nonnegative integer value.")
            if not math.isfinite(self.value) or self.value < 0 or self.value != int(self.value):
                raise ValueError("Count rules require a nonnegative integer value.")
        if self.kind == "near" and self.value is not None:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise ValueError("Near rules require a numeric maximum distance.")
            if not math.isfinite(self.value) or not 0 < self.value <= math.sqrt(2):
                raise ValueError("Near distance must be positive and within normalized image dimensions.")
        if self.kind == "aligned" and self.value not in (None, "x", "y"):
            raise ValueError("Aligned rules use value x or y to select a center axis.")
        if self.kind == "color" and (not isinstance(self.value, str) or not self.value.strip()):
            raise ValueError("Color rules require an expected color string.")
        return self


class Step(Contract):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    timestamp_start: float = Field(default=0, ge=0)
    timestamp_end: float = Field(default=0, ge=0)
    reference_frame_id: str | None = None
    object_labels: list[str] = Field(default_factory=list)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_step(self) -> Step:
        if self.timestamp_end < self.timestamp_start:
            raise ValueError("Step end timestamp cannot precede its start.")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("Step dependencies must be unique.")
        rule_ids = [rule.id for rule in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Rule identifiers must be unique within a step.")
        return self


class Task(Contract):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=240)
    description: str = ""
    objects: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1, max_length=100)
    provider_mode: str = "mock"
    provenance: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_graph(self) -> Task:
        # Local import keeps graph functions usable with these same schemas.
        from app.services.graph import validate_graph

        validate_graph(self.steps)
        return self


class RuleResult(Contract):
    rule_id: str
    kind: RuleKind
    status: Status
    evidence: list[str] = Field(default_factory=list)
    expected: str
    observed: str
    correction: str | None = None


class VerificationResult(Contract):
    step_id: str
    status: Status
    observations: list[Observation] = Field(default_factory=list)
    rule_results: list[RuleResult] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    explanation: str
    provider_mode: str
