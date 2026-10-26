import json
import subprocess
import threading
from pathlib import Path

import cv2
import numpy as np

from app.services.media import pixel_hash

_lock = threading.RLock()
BOXES = {
    "red block": [0.44, 0.60, 0.58, 0.77],
    "blue block": [0.44, 0.37, 0.58, 0.54],
    "green block": [0.23, 0.60, 0.37, 0.77],
    "yellow block": [0.65, 0.60, 0.79, 0.77],
}
COLORS = {
    "red block": (75, 80, 228),
    "blue block": (220, 135, 55),
    "green block": (130, 190, 65),
    "yellow block": (60, 205, 235),
}


def render_scene(boxes: dict, caption: str) -> np.ndarray:
    image = np.full((640, 960, 3), (38, 34, 27), dtype=np.uint8)
    cv2.rectangle(image, (80, 105), (880, 590), (73, 65, 52), 2)
    for x in range(100, 880, 40):
        for y in range(125, 590, 40):
            cv2.circle(image, (x, y), 1, (82, 74, 59), -1)
    cv2.putText(
        image,
        "REPLAYLAB / SYNTHETIC FIXTURE",
        (40, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (175, 185, 190),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(image, caption, (40, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (175, 185, 190), 1, cv2.LINE_AA)
    for label, bbox in boxes.items():
        x1, y1, x2, y2 = [round(value * dim) for value, dim in zip(bbox, [960, 640, 960, 640])]
        color = COLORS[label]
        cv2.rectangle(image, (x1 + 6, y1 + 7), (x2 + 6, y2 + 7), (20, 20, 20), -1)
        cv2.rectangle(image, (x1, y1), (x2 - 1, y2 - 1), color, -1)
        for cx in [x1 + 30, x2 - 30]:
            for cy in [y1 + 30, y2 - 30]:
                cv2.circle(
                    image,
                    (cx, cy),
                    12,
                    tuple(min(255, component + 22) for component in color),
                    -1,
                    cv2.LINE_AA,
                )
                cv2.circle(
                    image, (cx, cy), 12, tuple(max(0, component - 28) for component in color), 1, cv2.LINE_AA
                )
    return image


def observations(boxes: dict, partial: bool = False) -> dict:
    return {
        "observations": [
            {
                "label": label,
                "bbox": bbox,
                "confidence": 0.99,
                "track_id": label,
                "source": "synthetic fixture geometry",
                "provider": "mock",
                "color": label.split()[0],
                "color_confidence": 1.0,
            }
            for label, bbox in boxes.items()
        ],
        "visibility": 0.35 if partial else 1.0,
        "coverage": 0.35 if partial else 1.0,
        "image_quality": 1.0,
        "comparable": not partial,
        "provider_mode": "mock",
        "provenance": {
            "fixture": True,
            "detection_complete": not partial,
            "source": "generated geometry; not model inference",
        },
    }


def ensure_demo(directory: Path) -> dict:
    with _lock:
        directory.mkdir(parents=True, exist_ok=True)
        manifest_path = directory / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text())
        fixtures, lookup = [], {}
        scenes = [
            ("step-1", "First checkpoint", dict(list(BOXES.items())[:1]), False),
            ("step-2", "Second checkpoint", dict(list(BOXES.items())[:2]), False),
            ("step-3", "Third checkpoint", dict(list(BOXES.items())[:3]), False),
            ("complete", "Four-block reference", BOXES, False),
            (
                "blue-right",
                "Blue block to the right",
                {**BOXES, "blue block": [0.65, 0.35, 0.79, 0.52]},
                False,
            ),
            ("partial", "Obstructed camera view", {"red block": BOXES["red block"]}, True),
        ]
        for fixture_id, label, boxes, partial in scenes:
            path = directory / f"{fixture_id}.png"
            image = render_scene(boxes, label)
            if partial:
                cv2.rectangle(image, (300, 130), (860, 365), (26, 26, 26), -1)
                cv2.putText(
                    image, "VIEW OBSTRUCTED", (415, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (180, 180, 180), 1
                )
            cv2.imwrite(str(path), image)
            lookup[pixel_hash(path)] = observations(boxes, partial)
            fixtures.append(
                {
                    "id": fixture_id,
                    "label": label,
                    "url": f"/api/demo/fixtures/{fixture_id}/image",
                    "description": "Synthetic labeled fixture. Geometry is known; no live inference.",
                }
            )
        video_path = directory / "assembly-source.avi"
        writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (960, 640))
        if not writer.isOpened():
            raise RuntimeError("The installed OpenCV build cannot create the demo video.")
        for stage in range(1, 5):
            image = render_scene(dict(list(BOXES.items())[:stage]), f"Checkpoint {stage} / 4")
            for _ in range(20):
                writer.write(image)
        writer.release()
        playable_path = directory / "assembly.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(video_path),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-threads",
                "1",
                "-y",
                str(playable_path),
            ],
            capture_output=True,
            timeout=45,
            check=True,
        )
        video_path.unlink(missing_ok=True)
        manifest = {"fixtures": fixtures, "lookup": lookup, "video": playable_path.name}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest


def register_demo_frames(directory: Path, frames: list[dict], media_directory: Path):
    """Register only frames extracted from the app-generated known demo video."""
    with _lock:
        manifest = ensure_demo(directory)
        for index, frame in enumerate(frames):
            path = media_directory / frame["url"].rsplit("/", 1)[-1]
            stage_boxes = dict(list(BOXES.items())[: index + 1])
            manifest["lookup"][pixel_hash(path)] = observations(stage_boxes)
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
