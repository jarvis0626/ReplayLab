import hashlib
import io
import json
import os
import subprocess
import uuid
from pathlib import Path

os.environ.setdefault("OPENCV_IO_MAX_IMAGE_PIXELS", "25000000")
import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


class MediaError(ValueError):
    pass


def inspect_video(path: Path, max_seconds: float) -> dict:
    """Inspect actual content with a bounded subprocess, never a shell command."""
    try:
        process = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=15,
            check=True,
        )
        metadata = json.loads(process.stdout)
        stream = next(item for item in metadata["streams"] if item["codec_type"] == "video")
        duration = float(metadata["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
    except FileNotFoundError as exc:
        raise MediaError("FFmpeg/ffprobe is required on the API server.") from exc
    except (subprocess.SubprocessError, ValueError, KeyError, StopIteration) as exc:
        raise MediaError("The upload is not a readable video. Try a valid MP4, MOV, WebM, or AVI.") from exc
    if not np.isfinite(duration) or duration <= 0 or duration > max_seconds:
        raise MediaError(f"Video duration must be between 0 and {max_seconds:g} seconds.")
    if min(width, height) < 32 or max(width, height) > 4096 or width * height > 12_000_000:
        raise MediaError("Video dimensions must be at least 32 pixels and at most 4096 pixels per side.")
    return {"duration": round(duration, 3), "width": width, "height": height}


def extract_frames(path: Path, directory: Path, metadata: dict, project_id: str) -> list[dict]:
    frames = []
    duration = metadata["duration"]
    for fraction in [0.20, 0.45, 0.70, 0.95]:
        timestamp = min(duration - 0.01, max(0, duration * fraction))
        frame_id = uuid.uuid4().hex
        filename = f"frame-{frame_id}.png"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-nostdin",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(timestamp),
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale='min(1280,iw)':-2",
                    "-threads",
                    "1",
                    "-y",
                    str(directory / filename),
                ],
                capture_output=True,
                timeout=20,
                check=True,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            raise MediaError(
                "Frame extraction failed. The video may be corrupted or use an unsupported codec."
            ) from exc
        if not (directory / filename).exists():
            raise MediaError("No video frame was decoded at the requested timestamp.")
        frames.append(
            {"id": frame_id, "url": f"/api/media/{project_id}/{filename}", "timestamp": round(timestamp, 3)}
        )
    return frames


def decode_image(data: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(data)) as header:
            width, height = header.size
            if header.format not in {"PNG", "JPEG", "WEBP"}:
                raise MediaError("Checkpoint must contain PNG, JPEG, or WebP image data.")
            if min(width, height) < 32 or max(width, height) > 4096 or width * height > 16_000_000:
                raise MediaError(
                    "Checkpoint dimensions must be 32–4096 pixels per side, with at most 16 megapixels."
                )
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise MediaError("The checkpoint must contain an actual PNG, JPEG, or WebP image.") from exc
    try:
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise MediaError("The checkpoint could not be decoded as an image.") from exc
    if image is None:
        raise MediaError("The checkpoint must contain an actual PNG, JPEG, or WebP image.")
    height, width = image.shape[:2]
    if min(width, height) < 32 or max(width, height) > 4096 or width * height > 16_000_000:
        raise MediaError("Checkpoint dimensions must be 32–4096 pixels per side, with at most 16 megapixels.")
    return image


def pixel_hash(path: Path) -> str:
    image = decode_image(path.read_bytes())
    return hashlib.sha256(str(image.shape).encode() + image.tobytes()).hexdigest()


def measured_quality(path: Path) -> float:
    image = decode_image(path.read_bytes())
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    exposure = float(np.mean((gray > 12) & (gray < 245)))
    return min(1.0, sharpness / 70.0, exposure / 0.6)


def prepare_meta_video(path: Path) -> Path:
    # Normalize actual media regardless of the caller-supplied MIME/suffix. A
    # valid WebM can be named .mp4, so the filename cannot establish its format.
    # Include the conversion policy so old silent cache entries are not reused
    # after adding embedded audio preservation for video understanding.
    digest = hashlib.sha256(b"meta-mp4-audio-v2\0" + path.read_bytes()).hexdigest()[:32]
    destination = path.parent / f"video-{digest}.mp4"
    if destination.exists():
        return destination
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                "-threads",
                "1",
                "-y",
                str(destination),
            ],
            capture_output=True,
            timeout=90,
            check=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        destination.unlink(missing_ok=True)
        raise MediaError(
            "This video could not be converted to MP4 for Meta. Upload an H.264 MP4 and retry."
        ) from exc
    return destination
