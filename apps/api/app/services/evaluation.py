"""Measured evaluation of curated normalized observations, never live AI accuracy."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import ObservationSet, Step
from app.services.verification import verify

FIXTURES_PATH = Path(__file__).resolve().parents[4] / "demo" / "fixtures" / "evaluation.json"


def run_evaluation() -> dict:
    dataset = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    defaults = dataset["scene_defaults"]
    reference = ObservationSet.model_validate(defaults)
    statuses = ("pass", "fail", "uncertain")
    confusion = {expected: {predicted: 0 for predicted in statuses} for expected in statuses}
    details = []
    for case in dataset["scenarios"]:
        current = ObservationSet.model_validate(
            {**defaults, **case.get("scene", {}), "observations": case["observations"]}
        )
        step = Step(id=case["id"], title=case["title"], rules=case["rules"])
        result = verify(step, reference, current)
        expected = case["expected"]
        confusion[expected][result.status] += 1
        details.append(
            {
                "id": case["id"],
                "title": case["title"],
                "expected": expected,
                "predicted": result.status,
                "correct": expected == result.status,
                "explanation": result.explanation,
            }
        )
    count = len(details)
    correct = sum(item["correct"] for item in details)
    return {
        "dataset": dataset["name"],
        "provider_mode": "mock",
        "sample_size": count,
        "correct": correct,
        "accuracy": correct / count if count else None,
        "confusion_matrix": confusion,
        "confusion_matrix_axes": {"rows": "expected", "columns": "predicted"},
        "details": details,
        "limitations": [
            "Curated normalized observations test deterministic rules, not model detection or end-to-end video accuracy.",
            "Quality, confidence, and completeness values are fixture annotations rather than measured live model outputs.",
            "Small, deliberately constructed controlled tabletop cases do not estimate general real-world performance.",
            "Only visible 2D geometry is verified; occluded joints and physical attachment are outside scope.",
        ],
    }
