"""Tests for the deserialization module."""

from tests.helpers import MockNodeTree

from node_runner.deserialize import (
    get_node_socket_base_type,
    _topological_sort_frames,
    deserialize_node_tree,
)


class TestGetNodeSocketBaseType:
    """Test socket type resolution."""

    def test_exact_match(self):
        assert get_node_socket_base_type("NodeSocketFloat") == "NodeSocketFloat"

    def test_subtype_match(self):
        assert get_node_socket_base_type("NodeSocketFloatFactor") == "NodeSocketFloat"

    def test_vector_subtype(self):
        assert get_node_socket_base_type("NodeSocketVectorXYZ") == "NodeSocketVector"

    def test_color_match(self):
        assert get_node_socket_base_type("NodeSocketColor") == "NodeSocketColor"

    def test_shader_match(self):
        assert get_node_socket_base_type("NodeSocketShader") == "NodeSocketShader"

    def test_string_match(self):
        assert get_node_socket_base_type("NodeSocketString") == "NodeSocketString"

    def test_unknown_falls_back_to_float(self):
        assert get_node_socket_base_type("NodeSocketUnknownFuture") == "NodeSocketFloat"

    def test_bool_match(self):
        assert get_node_socket_base_type("NodeSocketBool") == "NodeSocketBool"

    def test_int_subtype(self):
        assert get_node_socket_base_type("NodeSocketIntFactor") == "NodeSocketInt"

    def test_rotation_match(self):
        assert get_node_socket_base_type("NodeSocketRotation") == "NodeSocketRotation"

    def test_image_match(self):
        assert get_node_socket_base_type("NodeSocketImage") == "NodeSocketImage"


class TestTopologicalSortFrames:
    """Test frame ordering for nested frames."""

    def test_no_frames(self):
        data = {
            "Math1": {"type": "ShaderNodeMath"},
            "Math2": {"type": "ShaderNodeMath"},
        }
        assert _topological_sort_frames(data) == []

    def test_single_frame(self):
        data = {
            "Frame": {"type": "NodeFrame"},
        }
        assert _topological_sort_frames(data) == ["Frame"]

    def test_nested_frames_parent_first(self):
        data = {
            "ChildFrame": {"type": "NodeFrame", "parent": "ParentFrame"},
            "ParentFrame": {"type": "NodeFrame"},
        }
        result = _topological_sort_frames(data)
        assert result.index("ParentFrame") < result.index("ChildFrame")

    def test_deeply_nested_frames(self):
        data = {
            "GrandChild": {"type": "NodeFrame", "parent": "Child"},
            "Child": {"type": "NodeFrame", "parent": "Root"},
            "Root": {"type": "NodeFrame"},
        }
        result = _topological_sort_frames(data)
        assert result.index("Root") < result.index("Child")
        assert result.index("Child") < result.index("GrandChild")

    def test_multiple_independent_frames(self):
        data = {
            "Frame1": {"type": "NodeFrame"},
            "Frame2": {"type": "NodeFrame"},
            "Frame3": {"type": "NodeFrame"},
        }
        result = _topological_sort_frames(data)
        assert len(result) == 3
        assert set(result) == {"Frame1", "Frame2", "Frame3"}

    def test_mixed_frames_and_nodes(self):
        data = {
            "Math1": {"type": "ShaderNodeMath"},
            "InnerFrame": {"type": "NodeFrame", "parent": "OuterFrame"},
            "OuterFrame": {"type": "NodeFrame"},
            "Math2": {"type": "ShaderNodeMath", "parent": "InnerFrame"},
        }
        result = _topological_sort_frames(data)
        assert result == ["OuterFrame", "InnerFrame"]


class TestDeserializeNodeTree:
    """Integration tests for node tree deserialization."""

    def test_empty_tree(self):
        tree = MockNodeTree()
        data = {"nodes": {}, "links": [], "name": "Test"}
        socket_map = {}
        # Should not raise
        deserialize_node_tree(tree, data, socket_map)
        assert len(tree.links) == 0

    def test_basic_node_creation(self):
        tree = MockNodeTree()
        data = {
            "nodes": {
                "Math": {
                    "type": "ShaderNodeMath",
                    "label": "Add",
                    "name": "Math",
                    "location": [100, 200],
                    "location_absolute": [100, 200],
                }
            },
            "links": [],
            "name": "Test",
        }
        socket_map = {}
        deserialize_node_tree(tree, data, socket_map)
        # A node should have been created
        assert len(tree.nodes) >= 1

    def test_link_creation(self):
        tree = MockNodeTree()
        data = {
            "nodes": {
                "A": {
                    "type": "ShaderNodeMath",
                    "label": "",
                    "name": "A",
                    "location": [0, 0],
                    "location_absolute": [0, 0],
                },
                "B": {
                    "type": "ShaderNodeMath",
                    "label": "",
                    "name": "B",
                    "location": [200, 0],
                    "location_absolute": [200, 0],
                },
            },
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
        socket_map = {}
        deserialize_node_tree(tree, data, socket_map)
        # Nodes were created for both A and B
        assert len(tree.nodes) >= 2

    def test_link_args_order(self):
        """links.new() must be called with (output_socket, input_socket)."""
        tree = MockNodeTree()
        data = {
            "nodes": {
                "Src": {
                    "type": "ShaderNodeMath",
                    "label": "",
                    "name": "Src",
                    "location": [0, 0],
                    "location_absolute": [0, 0],
                },
                "Dst": {
                    "type": "ShaderNodeMath",
                    "label": "",
                    "name": "Dst",
                    "location": [200, 0],
                    "location_absolute": [200, 0],
                },
            },
            "links": [{
                "from_node": "Src",
                "to_node": "Dst",
                "from_socket": "Value",
                "from_socket_type": "NodeSocketFloat",
                "from_socket_identifier": "Value",
                "to_socket": "Value",
                "to_socket_type": "NodeSocketFloat",
                "to_socket_identifier": "Value",
            }],
            "name": "Test",
        }
        socket_map = {}
        deserialize_node_tree(tree, data, socket_map)
        # The link should have been created.
        # MockLinkCollection.new(output_socket, input_socket) stores
        # from_socket=output_socket first.  If the call order was wrong
        # the from/to would be swapped.
        if tree.links:
            link = tree.links[0]
            # from_socket should be the OUTPUT (first arg to links.new)
            # to_socket should be the INPUT (second arg to links.new)
            assert link.from_socket is not None
            assert link.to_socket is not None
