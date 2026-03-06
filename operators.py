"""
Blender operators and UI for Node Runner import/export.
"""

import logging

import bpy

from .constants import EXPORT_HEADER
from .encoding import encode, decode
from .serialize import serialize_node_tree
from .deserialize import deserialize_node_tree

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Addon preferences
# ---------------------------------------------------------------------------

class NODE_RUNNER_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    import_at_cursor: bpy.props.BoolProperty(
        name="Import at Cursor",
        description="Offset imported nodes to the mouse cursor position",
        default=True,
    )  # type: ignore

    select_imported: bpy.props.BoolProperty(
        name="Select Imported Nodes",
        description="Select only the imported nodes after import",
        default=True,
    )  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "import_at_cursor")
        layout.prop(self, "select_imported")


def _get_prefs(context):
    """Return addon preferences, with safe fallback defaults."""
    prefs = context.preferences.addons.get(__package__)
    if prefs:
        return prefs.preferences
    return None


# ---------------------------------------------------------------------------
#  Export operators
# ---------------------------------------------------------------------------

class NODE_RUNNER_OT_export(bpy.types.Operator):
    """Export selected nodes as a Node Runner string"""

    bl_idname = "node_runner.export"
    bl_label = "Export Nodes"
    bl_options = {"REGISTER", "UNDO"}

    export_name: bpy.props.StringProperty(
        name="Name",
        default="MyNodes",
        description="Label prepended to the exported string",
    )  # type: ignore

    node_runner_hash: bpy.props.StringProperty(
        name="Hash",
        default="",
        description="The generated Node Runner hash (read-only)",
    )  # type: ignore

    def execute(self, context):
        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.label(text="Copied to clipboard!", icon="CHECKMARK")
        col = layout.column(align=True)
        col.prop(self, "node_runner_hash", text="", icon="COPYDOWN")

    def invoke(self, context, event):
        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            self.report({"WARNING"}, "No active node tree")
            return {"CANCELLED"}

        selected = context.selected_nodes or []
        names = [
            n.name for n in selected
            if not isinstance(
                n, (bpy.types.NodeGroupInput, bpy.types.NodeGroupOutput)
            )
        ]

        if not names:
            self.report({"WARNING"}, "No exportable nodes selected")
            return {"CANCELLED"}

        data = serialize_node_tree(edit_tree, selected_node_names=names)
        encoded = encode(data)

        export_name = self.export_name or "MyNodes"
        export_str = export_name + EXPORT_HEADER + encoded
        self.node_runner_hash = export_str
        context.window_manager.clipboard = export_str

        self.report({"INFO"}, "Node Runner: hash copied to clipboard")
        return context.window_manager.invoke_props_dialog(self, width=420)


class NODE_RUNNER_OT_export_named(bpy.types.Operator):
    """Export selected nodes with a custom name"""

    bl_idname = "node_runner.export_named"
    bl_label = "Export Nodes (Named)"
    bl_options = {"REGISTER", "UNDO"}

    export_name: bpy.props.StringProperty(
        name="Name",
        default="MyNodes",
        description="Label prepended to the exported string",
    )  # type: ignore

    def execute(self, context):
        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            self.report({"WARNING"}, "No active node tree")
            return {"CANCELLED"}

        selected = context.selected_nodes or []
        names = [
            n.name for n in selected
            if not isinstance(
                n, (bpy.types.NodeGroupInput, bpy.types.NodeGroupOutput)
            )
        ]
        if not names:
            self.report({"WARNING"}, "No exportable nodes selected")
            return {"CANCELLED"}

        data = serialize_node_tree(edit_tree, selected_node_names=names)
        encoded = encode(data)

        export_str = self.export_name + EXPORT_HEADER + encoded
        context.window_manager.clipboard = export_str

        self.report({"INFO"}, f"Exported as '{self.export_name}' — copied to clipboard")
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_name", text="Name", icon="SORTALPHA")


# ---------------------------------------------------------------------------
#  Import operators
# ---------------------------------------------------------------------------

class NODE_RUNNER_OT_import(bpy.types.Operator):
    """Import nodes from a Node Runner string"""

    bl_idname = "node_runner.import_nodes"
    bl_label = "Import Nodes"
    bl_options = {"REGISTER", "UNDO"}

    node_runner_import_field: bpy.props.StringProperty(
        name="Hash",
        default="",
        description="Paste the Node Runner hash here",
    )  # type: ignore

    import_at_cursor: bpy.props.BoolProperty(
        name="Import at Cursor",
        description="Offset imported nodes to the mouse cursor position",
        default=True,
    )  # type: ignore

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "node_runner_import_field", text="", icon="PASTEDOWN")
        layout.prop(self, "import_at_cursor", icon="PIVOT_CURSOR")

    def execute(self, context):
        raw = self.node_runner_import_field
        if not raw:
            self.report({"INFO"}, "No hash string provided")
            return {"CANCELLED"}

        return self._do_import(context, raw)

    def invoke(self, context, event):
        self._mouse_x = event.mouse_region_x
        self._mouse_y = event.mouse_region_y

        prefs = _get_prefs(context)
        if prefs:
            self.import_at_cursor = prefs.import_at_cursor

        return context.window_manager.invoke_props_dialog(self, width=420)

    def _do_import(self, context, raw):
        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            self.report({"WARNING"}, "No active node tree to import into")
            return {"CANCELLED"}

        # Strip header
        if EXPORT_HEADER in raw:
            raw = raw.split(EXPORT_HEADER, 1)[1]

        try:
            data = decode(raw)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        # Deselect all existing nodes
        for node in edit_tree.nodes:
            node.select = False

        # Track which nodes already exist
        existing_names = set(n.name for n in edit_tree.nodes)

        socket_id_map = {}
        deserialize_node_tree(edit_tree, data, socket_id_map)

        # Find freshly created nodes
        new_nodes = [n for n in edit_tree.nodes if n.name not in existing_names]

        # Select imported nodes
        prefs = _get_prefs(context)
        select_imported = prefs.select_imported if prefs else True
        if select_imported:
            for node in new_nodes:
                node.select = True
            if new_nodes:
                edit_tree.nodes.active = new_nodes[0]

        # Offset to cursor position
        if self.import_at_cursor and new_nodes and hasattr(self, "_mouse_x"):
            try:
                region = context.region
                from mathutils import Vector
                mouse_view = region.view2d.region_to_view(
                    self._mouse_x, self._mouse_y
                )
                # Find bounding box center of imported nodes
                min_x = min(n.location.x for n in new_nodes)
                max_x = max(n.location.x + n.dimensions.x for n in new_nodes)
                min_y = min(n.location.y - n.dimensions.y for n in new_nodes)
                max_y = max(n.location.y for n in new_nodes)
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2

                offset_x = mouse_view[0] - center_x
                offset_y = mouse_view[1] - center_y

                for node in new_nodes:
                    if node.parent is None:
                        node.location.x += offset_x
                        node.location.y += offset_y
            except Exception:
                # Silently skip offset if anything goes wrong
                pass

        node_count = len(new_nodes)
        self.report({"INFO"}, f"Imported {node_count} node{'s' if node_count != 1 else ''}")
        return {"FINISHED"}


class NODE_RUNNER_OT_paste(bpy.types.Operator):
    """Quick-paste nodes from clipboard"""

    bl_idname = "node_runner.paste"
    bl_label = "Paste Nodes from Clipboard"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        raw = context.window_manager.clipboard
        if not raw or EXPORT_HEADER not in raw:
            self.report({"WARNING"}, "Clipboard does not contain a Node Runner hash")
            return {"CANCELLED"}

        edit_tree = context.space_data.edit_tree
        if edit_tree is None:
            self.report({"WARNING"}, "No active node tree")
            return {"CANCELLED"}

        # Strip header
        raw = raw.split(EXPORT_HEADER, 1)[1]

        try:
            data = decode(raw)
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        # Deselect all
        for node in edit_tree.nodes:
            node.select = False

        existing_names = set(n.name for n in edit_tree.nodes)

        socket_id_map = {}
        deserialize_node_tree(edit_tree, data, socket_id_map)

        new_nodes = [n for n in edit_tree.nodes if n.name not in existing_names]

        prefs = _get_prefs(context)
        select_imported = prefs.select_imported if prefs else True
        if select_imported:
            for node in new_nodes:
                node.select = True
            if new_nodes:
                edit_tree.nodes.active = new_nodes[0]

        node_count = len(new_nodes)
        self.report({"INFO"}, f"Pasted {node_count} node{'s' if node_count != 1 else ''}")
        return {"FINISHED"}

    def invoke(self, context, event):
        return self.execute(context)


# ---------------------------------------------------------------------------
#  Context menu (submenu)
# ---------------------------------------------------------------------------

class NODE_RUNNER_MT_menu(bpy.types.Menu):
    """Node Runner submenu"""

    bl_idname = "NODE_RUNNER_MT_menu"
    bl_label = "Node Runner"

    def draw(self, context):
        layout = self.layout

        layout.operator(
            NODE_RUNNER_OT_export.bl_idname,
            text="Export Selected",
            icon="EXPORT",
        )
        layout.operator(
            NODE_RUNNER_OT_export_named.bl_idname,
            text="Export Selected (Named)",
            icon="SORTALPHA",
        )
        layout.separator()
        layout.operator(
            NODE_RUNNER_OT_import.bl_idname,
            text="Import from Hash",
            icon="IMPORT",
        )
        layout.operator(
            NODE_RUNNER_OT_paste.bl_idname,
            text="Paste from Clipboard",
            icon="PASTEDOWN",
        )


def menu_draw(self, context):
    self.layout.separator()
    self.layout.menu(NODE_RUNNER_MT_menu.bl_idname, icon="NODE")


# ---------------------------------------------------------------------------
#  Registration
# ---------------------------------------------------------------------------

_classes = (
    NODE_RUNNER_preferences,
    NODE_RUNNER_OT_export,
    NODE_RUNNER_OT_export_named,
    NODE_RUNNER_OT_import,
    NODE_RUNNER_OT_paste,
    NODE_RUNNER_MT_menu,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.NODE_MT_context_menu.append(menu_draw)


def unregister():
    bpy.types.NODE_MT_context_menu.remove(menu_draw)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
