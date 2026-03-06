"""
Node Runner — Import & export shader nodes as shareable strings.

Serializes Blender shader node trees to compressed, base64‑encoded
strings that can be shared via text, comments, or documentation.
"""

# Operators require bpy which is only available inside Blender.
# When running tests outside Blender the import is deferred so the
# test mock infrastructure can patch sys.modules first.
try:
    from . import operators

    _HAS_BPY = True
except ModuleNotFoundError:
    _HAS_BPY = False

bl_info = {
    "name": "Node Runner",
    "author": "Noah Thiering, Julius Ewert",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "Node Editor > Context Menu",
    "description": "Import and export shader & geometry nodes as a string",
    "doc_url": "docs/",
    "category": "Node",
}


def register():
    """Register all operators and menu entries."""
    if _HAS_BPY:
        operators.register()


def unregister():
    """Unregister all operators and menu entries."""
    if _HAS_BPY:
        operators.unregister()


if __name__ == "__main__":
    register()
