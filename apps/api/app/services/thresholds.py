"""Request-scoped evidence gates; thresholds are policy, not accuracy estimates."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceThresholds:
    confidence: float = 0.75
    digital_quality: float = 0.4
    physical_quality: float = 0.65


_thresholds = ContextVar("verification_evidence_thresholds", default=EvidenceThresholds())


def evidence_thresholds() -> EvidenceThresholds:
    return _thresholds.get()


@contextmanager
def configured_thresholds(settings):
    token = _thresholds.set(EvidenceThresholds(
        confidence=settings.verification_min_confidence,
        digital_quality=settings.verification_digital_quality,
        physical_quality=settings.verification_physical_quality,
    ))
    try:
        yield
    finally:
        _thresholds.reset(token)
