import copy
import json

import pytest

from app.schemas import Observation, ObservationSet, Rule, Step
from app.services.evaluation import FIXTURES_PATH, run_evaluation
from app.services.verification import verify


def observation(label="red", box=(0.2, 0.2, 0.4, 0.4), **kwargs):
    return Observation(label=label, bbox=box, confidence=kwargs.pop("confidence", 0.99), **kwargs)


def scene(observations=None, **kwargs):
    values = dict(
        observations=observations or [],
        visibility=1,
        coverage=1,
        image_quality=1,
        comparable=True,
        provenance={"detection_complete": True},
        provider_mode="mock",
    )
    values.update(kwargs)
    return ObservationSet(**values)


def check(rule, current, reference=None):
    return verify(Step(id="step", title="approved step", rules=[rule]), reference or scene(), current)


DATASET = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", DATASET["scenarios"], ids=lambda case: case["id"])
def test_labeled_observation_scenarios(case):
    defaults = DATASET["scene_defaults"]
    current = ObservationSet.model_validate(
        {**defaults, **case.get("scene", {}), "observations": case["observations"]}
    )
    step = Step(id=case["id"], title=case["title"], rules=case["rules"])
    result = verify(step, ObservationSet.model_validate(defaults), current)
    assert result.status == case["expected"], result.explanation
    assert result.provider_mode == "mock"


@pytest.mark.parametrize(
    "kind,subject_box,target_box,expected",
    [
        ("above", (0.2, 0.7, 0.3, 0.8), (0.2, 0.1, 0.3, 0.2), "fail"),
        ("below", (0.2, 0.1, 0.3, 0.2), (0.2, 0.7, 0.3, 0.8), "fail"),
        ("left", (0.7, 0.2, 0.8, 0.3), (0.1, 0.2, 0.2, 0.3), "fail"),
        ("right", (0.1, 0.2, 0.2, 0.3), (0.7, 0.2, 0.8, 0.3), "fail"),
    ],
)
def test_directional_mismatches_return_specific_grounded_corrections(kind, subject_box, target_box, expected):
    result = check(
        Rule(id="r", kind=kind, subject="red", target="blue"),
        scene([observation(box=subject_box), observation(label="blue", box=target_box)]),
    )
    assert result.status == expected
    assert f"Move red {kind} of blue" in result.explanation
    assert any("Normalized centers" in line for line in result.evidence)


@pytest.mark.parametrize(
    "field,value",
    [("visibility", None), ("image_quality", None), ("comparable", None), ("comparable", False)],
)
def test_unknown_scene_evidence_does_not_pass_or_fail(field, value):
    current = scene([observation()], **{field: value})
    assert check(Rule(id="r", kind="presence", subject="red"), current).status == "uncertain"


def test_reference_quality_and_camera_comparability_are_required():
    current = scene([observation()])
    result = check(Rule(id="r", kind="presence", subject="red"), current, scene(image_quality=None))
    assert result.status == "uncertain"
    assert "Reference image quality is unknown" in result.explanation


def test_absence_cannot_fail_without_explicit_scene_completeness():
    result = check(Rule(id="r", kind="presence", subject="red"), scene(provenance={}))
    assert result.status == "uncertain"


def test_forbidden_object_requires_reliable_absence_or_visible_presence():
    rule = Rule(id="r", kind="presence", subject="red", value=False)
    assert check(rule, scene()).status == "pass"
    assert check(rule, scene([observation()])).status == "fail"
    assert check(rule, scene([observation(confidence=0.2)])).status == "uncertain"


def test_duplicate_detections_cannot_prove_extra_objects():
    repeated = observation()
    result = check(Rule(id="r", kind="count", subject="red", value=1), scene([repeated, repeated]))
    assert result.status == "uncertain"
    assert "Overlapping boxes" in result.explanation


def test_low_confidence_distractor_makes_unique_relationship_uncertain():
    result = check(
        Rule(id="r", kind="left", subject="red", target="blue"),
        scene(
            [
                observation(box=(0.1, 0.2, 0.2, 0.3)),
                observation(confidence=0.2),
                observation(label="blue", box=(0.7, 0.2, 0.8, 0.3)),
            ]
        ),
    )
    assert result.status == "uncertain"


def test_clear_failure_remains_failure_and_preserves_other_uncertainty():
    step = Step(
        id="s",
        title="two constraints",
        rules=[
            Rule(id="absent", kind="presence", subject="red", value=False),
            Rule(id="missing", kind="left", subject="green", target="blue"),
        ],
    )
    result = verify(step, scene(), scene([observation()]))
    assert result.status == "fail"
    assert [item.status for item in result.rule_results] == ["fail", "uncertain"]
    assert "Other constraints remain uncertain" in result.explanation


def test_no_constraints_cannot_pass_and_inputs_are_not_mutated():
    current = scene([observation()])
    before = copy.deepcopy(current)
    result = verify(Step(id="s", title="unreviewed"), scene(), current)
    assert result.status == "uncertain"
    assert current == before


def test_evaluation_reports_actual_counts_and_explicit_limits():
    report = run_evaluation()
    assert report["sample_size"] >= 12
    assert report["correct"] == report["sample_size"]
    assert report["accuracy"] == 1
    assert sum(sum(row.values()) for row in report["confusion_matrix"].values()) == report["sample_size"]
    assert "not model detection" in report["limitations"][0]
