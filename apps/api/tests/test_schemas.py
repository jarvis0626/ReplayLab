import pytest
from pydantic import ValidationError

from app.schemas import Observation, ObservationSet, Rule, Step, Task


@pytest.mark.parametrize(
    "box",
    [
        (-0.1, 0, 0.5, 0.5),
        (0, 0, 1.1, 0.5),
        (0.5, 0, 0.1, 0.5),
        (0, 0.2, 0.5, 0.2),
        (0, 0, float("nan"), 0.5),
    ],
)
def test_invalid_normalized_boxes_rejected(box):
    with pytest.raises(ValidationError):
        Observation(label="red", bbox=box)


def test_missing_quality_is_preserved_and_extra_fields_rejected():
    observation = Observation(label=" red ", bbox=(0, 0, 1, 1))
    assert observation.label == "red"
    assert observation.confidence is None
    scene = ObservationSet(observations=[observation])
    assert scene.visibility is None and scene.comparable is None
    with pytest.raises(ValidationError):
        Observation(label="red", bbox=(0, 0, 1, 1), fabricated_confidence=1)


@pytest.mark.parametrize(
    "values",
    [
        {"kind": "above"},
        {"kind": "left", "target": "red"},
        {"kind": "count", "value": -1},
        {"kind": "count", "value": 1.5},
        {"kind": "count", "value": True},
        {"kind": "count", "value": "2"},
        {"kind": "presence", "value": "yes"},
        {"kind": "near", "target": "blue", "value": -0.1},
        {"kind": "aligned", "target": "blue", "value": "z"},
        {"kind": "color"},
    ],
)
def test_semantically_invalid_rules_rejected(values):
    with pytest.raises(ValidationError):
        Rule(id="r", subject="red", **values)


def test_step_rejects_bad_timestamps_and_duplicate_rule_ids():
    with pytest.raises(ValidationError, match="timestamp"):
        Step(id="s", title="step", timestamp_start=3, timestamp_end=2)
    rule = Rule(id="r", kind="presence", subject="red")
    with pytest.raises(ValidationError, match="Rule identifiers"):
        Step(id="s", title="step", rules=[rule, rule])
    with pytest.raises(ValidationError, match="dependencies"):
        Step(id="s", title="step", dependencies=["a", "a"])


def test_task_validates_graph_and_json_roundtrips():
    task = Task(
        id="t",
        title="test",
        steps=[Step(id="a", title="first"), Step(id="b", title="second", dependencies=["a"])],
    )
    assert Task.model_validate_json(task.model_dump_json()) == task
    with pytest.raises(ValidationError, match="missing dependency"):
        Task(id="t", title="test", steps=[Step(id="b", title="second", dependencies=["missing"])])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "NaN", "Infinity"])
def test_nonfinite_observation_and_step_timestamps_are_rejected(value):
    with pytest.raises(ValidationError):
        Observation(label="red", bbox=(0, 0, 1, 1), timestamp=value)
    with pytest.raises(ValidationError):
        Step(id="s", title="step", timestamp_start=value, timestamp_end=value)


def test_relationship_target_is_distinct_under_observation_label_matching():
    with pytest.raises(ValidationError, match="distinct target"):
        Rule(id="r", kind="above", subject="Red", target="red")
