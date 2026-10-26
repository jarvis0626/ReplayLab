"""Dependency validation and progression for approved action graphs."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.schemas import Step


def validate_graph(steps: list[Step]) -> list[str]:
    """Return stable topological identifiers or reject invalid dependencies."""
    by_id = {step.id: step for step in steps}
    if len(by_id) != len(steps):
        raise ValueError("Step identifiers must be unique.")
    children: dict[str, list[str]] = {step.id: [] for step in steps}
    incoming: dict[str, int] = {}
    for step in steps:
        if len(step.dependencies) != len(set(step.dependencies)):
            raise ValueError(f"Step {step.id} has duplicate dependencies.")
        incoming[step.id] = len(step.dependencies)
        for dependency in step.dependencies:
            if dependency not in by_id:
                raise ValueError(f"Step {step.id} refers to missing dependency {dependency}.")
            if dependency == step.id:
                raise ValueError(f"Step {step.id} cannot depend on itself.")
            children[dependency].append(step.id)
    ready = deque(step.id for step in steps if incoming[step.id] == 0)
    order: list[str] = []
    while ready:
        step_id = ready.popleft()
        order.append(step_id)
        for child in children[step_id]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if len(order) != len(steps):
        raise ValueError("The action graph contains a dependency cycle.")
    return order


def available_steps(steps: list[Step], completed: Iterable[str]) -> list[Step]:
    """Only unfinished steps whose prerequisites are completed are available."""
    order = validate_graph(steps)
    done = set(completed)
    known = set(order)
    if done - known:
        raise ValueError("Completed steps contain identifiers outside this graph.")
    by_id = {step.id: step for step in steps}
    for step_id in done:
        if not set(by_id[step_id].dependencies) <= done:
            raise ValueError(f"Completed step {step_id} is missing a completed prerequisite.")
    return [
        by_id[step_id]
        for step_id in order
        if step_id not in done and set(by_id[step_id].dependencies) <= done
    ]
