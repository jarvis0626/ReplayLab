import pytest

from app.schemas import Step
from app.services.graph import available_steps, validate_graph


def step(identifier, dependencies=None):
    return Step(id=identifier, title=identifier, dependencies=dependencies or [])


def test_topological_order_is_stable_and_respects_dependencies():
    steps = [step("finish", ["left", "right"]), step("root"), step("left", ["root"]), step("right", ["root"])]
    assert validate_graph(steps) == ["root", "left", "right", "finish"]


@pytest.mark.parametrize(
    "steps, error",
    [
        ([step("a"), step("a")], "unique"),
        ([step("a", ["missing"])], "missing dependency"),
        ([step("a", ["a"])], "itself"),
        ([step("a", ["b"]), step("b", ["a"])], "cycle"),
    ],
)
def test_invalid_graphs_are_rejected(steps, error):
    with pytest.raises(ValueError, match=error):
        validate_graph(steps)


def test_available_steps_enforces_prerequisites_and_completion():
    steps = [step("a"), step("b", ["a"]), step("c", ["a"]), step("d", ["b", "c"])]
    assert [item.id for item in available_steps(steps, [])] == ["a"]
    assert [item.id for item in available_steps(steps, ["a"])] == ["b", "c"]
    assert [item.id for item in available_steps(steps, ["a", "b"])] == ["c"]
    assert [item.id for item in available_steps(steps, ["a", "b", "c"])] == ["d"]
    assert available_steps(steps, ["a", "b", "c", "d"]) == []


def test_unknown_or_out_of_order_completion_is_rejected():
    steps = [step("a"), step("b", ["a"])]
    with pytest.raises(ValueError, match="outside"):
        available_steps(steps, ["unknown"])
    with pytest.raises(ValueError, match="prerequisite"):
        available_steps(steps, ["b"])
