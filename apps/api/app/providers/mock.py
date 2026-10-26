from pathlib import Path
from uuid import uuid4

from app.schemas import ObservationSet, Rule, Step, Task
from app.services.demo import ensure_demo
from app.services.media import pixel_hash


class MockProvider:
    def __init__(self, fixture_directory: Path):
        self.fixture_directory = fixture_directory

    def extract_task(self, video_path: Path, frames: list[dict]) -> Task:
        labels = ["red block", "blue block", "green block", "yellow block"]
        titles = [
            "Place the red foundation",
            "Position blue above red",
            "Align green to the left",
            "Complete with yellow on the right",
        ]
        relationships = [
            None,
            ("above", "blue block", "red block"),
            ("left", "green block", "red block"),
            ("right", "yellow block", "red block"),
        ]
        steps = []
        for index, title in enumerate(titles):
            rules = [
                Rule(id=f"present-{n}", kind="presence", subject=label)
                for n, label in enumerate(labels[: index + 1])
            ]
            for position in range(1, index + 1):
                kind, subject, target = relationships[position]
                rules.append(Rule(id=f"relation-{position}", kind=kind, subject=subject, target=target))
                rules.append(
                    Rule(
                        id=f"alignment-{position}",
                        kind="aligned",
                        subject=subject,
                        target=target,
                        value="x" if position == 1 else "y",
                        tolerance=0.05,
                    )
                )
            frame = frames[min(index, len(frames) - 1)]
            steps.append(
                Step(
                    id=f"step-{index + 1}",
                    title=title,
                    description="Offline four-block template. Review the expected objects and relationships before approval.",
                    dependencies=[f"step-{index}"] if index else [],
                    timestamp_start=round(max(0, frame["timestamp"] - 1), 3),
                    timestamp_end=frame["timestamp"],
                    reference_frame_id=frame["id"],
                    object_labels=labels[: index + 1],
                    rules=rules,
                )
            )
        return Task(
            id=uuid4().hex,
            title="Four-block tabletop assembly",
            description="MOCK template, not an interpretation of the uploaded video. Only the generated demonstration has known matching observations.",
            objects=labels,
            steps=steps,
            provider_mode="mock",
            provenance={"provider": "deterministic mock template", "inferred_from_video": False},
        )

    def observe(self, image_path: Path, object_prompts: list[str]) -> ObservationSet:
        manifest = ensure_demo(self.fixture_directory)
        known = manifest["lookup"].get(pixel_hash(image_path))
        if known:
            result = ObservationSet.model_validate(known)
            result.observations = [item for item in result.observations if item.label in object_prompts]
            return result
        return ObservationSet(
            provider_mode="mock",
            provenance={
                "fixture": False,
                "detection_complete": False,
                "reason": "This image is not a registered demo fixture. Offline mock mode cannot observe arbitrary uploaded images.",
            },
        )

    def explain(self, result) -> str:
        return result.explanation
