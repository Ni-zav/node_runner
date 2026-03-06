"""
Encoding and decoding utilities for Node Runner.

Handles compression (zlib) and encoding (base64) of serialized node data.
"""

import pickle
import zlib
import base64
import binascii
import logging

log = logging.getLogger(__name__)


def encode(data: dict) -> str:
    """Serialize, compress, and base64-encode node tree data.

    Args:
        data: Serialized node tree dictionary.

    Returns:
        Base64 encoded string.
    """
    raw = pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)
    compressed = zlib.compress(raw, 9)
    return base64.b64encode(compressed).decode("utf-8")


def decode(base64_encoded: str) -> dict:
    """Decode and decompress a base64-encoded node tree string.

    Args:
        base64_encoded: Base64 encoded and zlib compressed data.

    Returns:
        Deserialized node tree dictionary.

    Raises:
        ValueError: If decoding or decompression fails.
    """
    try:
        compressed = base64.b64decode(base64_encoded)
        raw = zlib.decompress(compressed)
        return pickle.loads(raw)
    except (zlib.error, pickle.UnpicklingError, binascii.Error) as exc:
        raise ValueError(f"Failed to decode node data: {exc}") from exc
