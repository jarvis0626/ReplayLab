import struct
import json
import subprocess
import zlib

import cv2
import numpy as np
import pytest

from app.services.media import MediaError, decode_image, prepare_meta_video


def test_oversized_image_header_is_rejected_before_pixel_decode():
    _, encoded = cv2.imencode(".png", np.zeros((64, 64, 3), np.uint8))
    payload = bytearray(encoded.tobytes())
    payload[16:20] = struct.pack(">I", 5000)
    payload[29:33] = struct.pack(">I", zlib.crc32(payload[12:29]))
    with pytest.raises(MediaError, match="dimensions"):
        decode_image(bytes(payload))


def test_spoofed_image_format_is_not_decoded_as_supported_type():
    _, encoded = cv2.imencode(".bmp", np.zeros((64, 64, 3), np.uint8))
    with pytest.raises(MediaError, match="PNG, JPEG, or WebP"):
        decode_image(encoded.tobytes())


def test_meta_video_normalizes_real_container_instead_of_trusting_suffix(tmp_path):
    actual = tmp_path / "source.webm"
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=96x64:r=4:d=1",
            "-c:v",
            "libvpx-vp9",
            "-threads",
            "1",
            "-y",
            str(actual),
        ],
        check=True,
        capture_output=True,
        timeout=20,
    )
    disguised = tmp_path / "mislabeled.mp4"
    actual.rename(disguised)
    normalized = prepare_meta_video(disguised)
    assert normalized != disguised
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=format_name:stream=codec_name",
            "-of",
            "json",
            str(normalized),
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )
    metadata = json.loads(result.stdout)
    assert "mp4" in metadata["format"]["format_name"]
    assert metadata["streams"][0]["codec_name"] == "h264"
    assert prepare_meta_video(disguised) == normalized
