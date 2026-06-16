"""ff9mapkit Blender add-on — visual camera + walkmesh authoring for FF9 custom fields.

A front-end to the `ff9mapkit` CLI: pose the camera and model the walkmesh in Blender's 3D
viewport, then export camera.bgx + walkmesh.obj + a field.toml for `ff9mapkit build`.

bpy is imported lazily/guarded so the bpy-free `bridge` module can be unit-tested without
Blender. register()/unregister() are no-ops outside Blender.
"""

bl_info = {
    "name": "FF9 Map Kit",
    "author": "FF9 Map Kit contributors",
    "version": (0, 9, 16),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > FF9 Map Kit",
    "description": "Visually author FF9 custom-field cameras + walkmeshes; export for ff9mapkit build.",
    "category": "Import-Export",
}

try:
    import bpy  # noqa: F401
    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False


def register():
    if not _HAS_BPY:
        return
    from . import ops, ui
    ops.register()
    ui.register()


def unregister():
    if not _HAS_BPY:
        return
    from . import ops, ui
    ui.unregister()
    ops.unregister()
