"""Tests for the serialization module."""

from tests.helpers import MockNode, MockNodeTree
from mathutils import Vector as MockVector

from node_runner.serialize import (
    serialize_color,
    serialize_vector,
    serialize_euler,
    serialize_attr,
    serialize_node,
    serialize_node_tree,
)


class TestPrimitiveSerializers:
    """Test basic type serializers."""

    def test_serialize_color(self):
        from mathutils import Color
        c = Color((0.5, 0.2, 0.8))
        result = serialize_color(c)
        assert result == [0.5, 0.2, 0.8]

    def test_serialize_vector(self):
        from mathutils import Vector
        v = Vector((1.0, 2.0, 3.0))
        result = serialize_vector(v)
        assert result == [1.0, 2.0, 3.0]

    def test_serialize_euler(self):
        from mathutils import Euler
        e = Euler((0.1, 0.2, 0.3))
        result = serialize_euler(e)
        assert result == [0.1, 0.2, 0.3]


class TestSerializeAttr:
    """Test the generic attribute dispatcher."""

    def test_serialize_plain_int(self):
        node = MockNode()
        assert serialize_attr(node, 42) == 42

    def test_serialize_plain_float(self):
        node = MockNode()
        assert serialize_attr(node, 3.14) == 3.14

    def test_serialize_plain_string(self):
        node = MockNode()
        assert serialize_attr(node, "hello") == "hello"

    def test_serialize_plain_bool(self):
        node = MockNode()
        assert serialize_attr(node, True) is True

    def test_serialize_none(self):
        """None should pass through (pickle-safe)."""
        node = MockNode()
        assert serialize_attr(node, None) is None

    def test_serialize_vector(self):
        from mathutils import Vector
        node = MockNode()
        v = Vector((1.0, 2.0))
        result = serialize_attr(node, v)
        assert result == [1.0, 2.0]

    def test_serialize_list(self):
        node = MockNode()
        result = serialize_attr(node, [1, 2, 3])
        assert result == [1, 2, 3]


class TestSerializeNode:
    """Test node serialization."""

    def test_basic_node(self):
        node = MockNode(
            name="Math",
            bl_idname="ShaderNodeMath",
            label="My Math",
            location=(100, -50),
            operation="ADD",
        )
        result = serialize_node(node)
        assert result["type"] == "ShaderNodeMath"
        assert result["label"] == "My Math"
        assert result["location_absolute"] == [100, -50]
        assert result["operation"] == "ADD"

    def test_node_with_parent(self):
        parent_node = MockNode(name="Frame1", bl_idname="NodeFrame")
        child_node = MockNode(
            name="Child",
            bl_idname="ShaderNodeMath",
            location=(10, 20),
            parent=parent_node,
        )
        # Need to add parent to bl_rna properties
        result = serialize_node(child_node)
        assert result.get("parent") == "Frame1"

    def test_type_always_present(self):
        node = MockNode(bl_idname="ShaderNodeRGB")
        result = serialize_node(node)
        assert "type" in result
        assert result["type"] == "ShaderNodeRGB"


class TestSerializeNodeTree:
    """Test node tree serialization."""

    def test_empty_tree(self):
        tree = MockNodeTree(name="TestTree")
        result = serialize_node_tree(tree)
        assert result["name"] == "TestTree"
        assert result["nodes"] == {}
        assert result["links"] == []

    def test_tree_with_nodes(self):
        tree = MockNodeTree(name="MyMaterial")
        n1 = MockNode(name="Math1", bl_idname="ShaderNodeMath", operation="ADD")
        n2 = MockNode(name="Math2", bl_idname="ShaderNodeMath", operation="MULTIPLY")
        tree.nodes.add(n1)
        tree.nodes.add(n2)

        result = serialize_node_tree(tree)
        assert "Math1" in result["nodes"]
        assert "Math2" in result["nodes"]

    def test_selected_nodes_filter(self):
        tree = MockNodeTree(name="Mat")
        n1 = MockNode(name="Keep", bl_idname="ShaderNodeMath")
        n2 = MockNode(name="Skip", bl_idname="ShaderNodeMath")
        tree.nodes.add(n1)
        tree.nodes.add(n2)

        result = serialize_node_tree(tree, selected_node_names=["Keep"])
        assert "Keep" in result["nodes"]
        assert "Skip" not in result["nodes"]

    def test_tree_type_is_stored(self):
        tree = MockNodeTree(name="Geo", bl_idname="GeometryNodeTree")
        result = serialize_node_tree(tree)
        assert result["tree_type"] == "GeometryNodeTree"

    def test_tree_type_shader(self):
        tree = MockNodeTree(name="Mat", bl_idname="ShaderNodeTree")
        result = serialize_node_tree(tree)
        assert result["tree_type"] == "ShaderNodeTree"
