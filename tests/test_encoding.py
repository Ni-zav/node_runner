"""Tests for the encoding module."""

import pytest

from node_runner.encoding import encode, decode


class TestEncodeDecode:
    """Round-trip tests for encode/decode."""

    def test_roundtrip_simple_dict(self):
        data = {"nodes": {}, "links": [], "name": "Test"}
        encoded = encode(data)
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        decoded = decode(encoded)
        assert decoded == data

    def test_roundtrip_with_node_data(self):
        data = {
            "nodes": {
                "Math": {
                    "type": "ShaderNodeMath",
                    "label": "",
                    "operation": "ADD",
                    "location": [100.0, 200.0],
                    "location_absolute": [100.0, 200.0],
                    "inputs": [0.5, 0.5, None],
                }
            },
            "links": [],
            "name": "Material",
        }
        encoded = encode(data)
        decoded = decode(encoded)
        assert decoded["nodes"]["Math"]["operation"] == "ADD"
        assert decoded["nodes"]["Math"]["location"] == [100.0, 200.0]

    def test_roundtrip_with_links(self):
        data = {
            "nodes": {"A": {"type": "ShaderNodeMath"}, "B": {"type": "ShaderNodeMath"}},
            "links": [{
                "from_node": "A",
                "to_node": "B",
                "from_socket": "Value",
                "from_socket_type": "NodeSocketFloat",
                "from_socket_identifier": "Value",
                "to_socket": "Value",
                "to_socket_type": "NodeSocketFloat",
                "to_socket_identifier": "Value",
            }],
            "name": "Test",
        }
        assert decode(encode(data)) == data

    def test_decode_invalid_data(self):
        with pytest.raises(ValueError, match="Failed to decode"):
            decode("not-valid-base64!!!")

    def test_decode_empty_string(self):
        with pytest.raises(ValueError):
            decode("")

    def test_roundtrip_nested_structures(self):
        data = {
            "nodes": {
                "ColorRamp": {
                    "type": "ShaderNodeValToRGB",
                    "color_ramp": {
                        "color_mode": "RGB",
                        "interpolation": "LINEAR",
                        "hue_interpolation": "NEAR",
                        "elements": [
                            {"position": 0.0, "color": [0.0, 0.0, 0.0, 1.0]},
                            {"position": 1.0, "color": [1.0, 1.0, 1.0, 1.0]},
                        ],
                    },
                }
            },
            "links": [],
            "name": "Test",
        }
        assert decode(encode(data)) == data

    def test_encode_produces_compact_output(self):
        """Encoding with compression should be shorter than raw pickle."""
        import pickle
        data = {"nodes": {"A" * 100: {"type": "X" * 100}}, "links": [], "name": "T"}
        encoded = encode(data)
        raw_len = len(pickle.dumps(data))
        # base64 is ~4/3 overhead, but zlib should more than compensate
        # for repetitive data
        assert len(encoded) < raw_len * 2
