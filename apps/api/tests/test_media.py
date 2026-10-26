import struct
import zlib

import cv2
import numpy as np
import pytest

from app.services.media import MediaError, decode_image


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
