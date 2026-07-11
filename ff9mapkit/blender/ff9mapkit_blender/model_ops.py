"""Import/Export FF9 Model operators -- the Blender end of the character/field model edit loop.

Same philosophy as the field operators: the add-on only does the BLENDER-side artifact I/O (import a .glb the
CLI produced; export the scene to a .glb the CLI consumes) -- it does NOT run the toolkit. The p0data-touching
work (reading a real model, writing the loose-FBX + .anim overrides) stays in the ``ff9mapkit`` CLI, which the
user runs, exactly like Export Field -> ``ff9mapkit build`` and Import Field <- ``ff9mapkit import``. So there is
no subprocess, no CLI-version/location coupling, and it works with whatever ``ff9mapkit`` the user has.

  * Import Model : produce a .glb with ``ff9mapkit model-gltf <geo> --out model.glb``, then pick it here.
  * Export Model : export the scene to .glb (the settings the kit's importer expects) + hand you the exact
                   ``ff9mapkit model-import ... --deploy <mod>`` command (copied to the clipboard) to run.
"""

from __future__ import annotations

import bpy
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import bridge


class FF9MK_OT_import_model(bpy.types.Operator, ImportHelper):
    bl_idname = "ff9mk.import_model"
    bl_label = "Import FF9 Model"
    bl_description = ("Import a .glb produced by `ff9mapkit model-gltf <geo>` -- a rigged, textured model with "
                     "its idle/walk/run clips. Edit it, then Export FF9 Model")
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb;*.gltf", options={"HIDDEN"})

    def execute(self, context):
        try:
            bpy.ops.import_scene.gltf(filepath=self.filepath)
        except (RuntimeError, AttributeError) as e:
            self.report({"ERROR"}, f"glTF import failed ({e}); is the glTF 2.0 importer enabled?")
            return {"CANCELLED"}
        self.report({"INFO"}, f"imported {bpy.path.basename(self.filepath)}: edit the mesh/pose/clips, "
                              f"then Export FF9 Model. (Keep the boneNNN bone names -- the kit's "
                              f"bone012_R_hand label suffixes are fine, but don't rename/add your own.)")
        return {"FINISHED"}


class FF9MK_OT_export_model(bpy.types.Operator, ExportHelper):
    bl_idname = "ff9mk.export_model"
    bl_label = "Export FF9 Model"
    bl_description = ("Export the scene to a .glb the kit's importer expects, then hand you the "
                     "`ff9mapkit model-import ... --deploy <mod>` command to run (copied to the clipboard)")
    bl_options = {"REGISTER"}

    filename_ext = ".glb"
    filter_glob: bpy.props.StringProperty(default="*.glb", options={"HIDDEN"})

    mod_folder: bpy.props.StringProperty(
        name="Mod folder", subtype="DIR_PATH", default="",
        description="Optional: the Memoria mod folder to bake into the model-import command "
                    "(e.g. <FF9>/FF9CustomMap). Leave blank for a placeholder you fill in yourself")
    like: bpy.props.StringProperty(
        name="Like (optional)", default="",
        description="GEO whose rig + textures to keep -- auto-detected from the glTF stamp if blank (usually "
                    "leave empty; give it for a foreign glTF or to force a different source)")
    no_anims: bpy.props.BoolProperty(
        name="Mesh only (skip animations)", default=False,
        description="Add --no-anims: import the mesh only, don't write back edited animation clips")
    all_actions: bpy.props.BoolProperty(
        name="Export ALL actions", default=False,
        description="OFF (default) exports only the ACTIVE action -- the one clip you're editing. This avoids "
                    "the footgun where a scene with the model imported more than once has stacked duplicate "
                    "actions (run.001, run.002..) that all route to the same clip and clobber each other. Turn "
                    "ON only in a clean scene where you deliberately edited several clips")
    selection_only: bpy.props.BoolProperty(
        name="Selected objects only", default=False,
        description="Export only the selected objects instead of the whole scene (if the scene has stray "
                    "objects beyond the FF9 model + its armature)")

    def execute(self, context):
        try:
            # The settings the kit's importer expects: GLB, Y-up, skins + animations + custom-property extras
            # (the ff9_geo / ff9_anim_key stamps that route the re-import); modifiers NOT applied so the rig
            # survives (the kit re-rigs if Blender changed the vertex count). Default to the ACTIVE action only
            # -- a scene with the model imported more than once stacks duplicate actions (run.001, run.002..)
            # that all route to the same clip and clobber each other last-wins; exporting the one active action
            # sidesteps that. "Export ALL actions" opts back to every action for a clean multi-clip edit.
            bpy.ops.export_scene.gltf(
                filepath=self.filepath, export_format="GLB", use_selection=self.selection_only,
                export_yup=True, export_skins=True, export_animations=True,
                export_animation_mode="ACTIONS" if self.all_actions else "ACTIVE_ACTIONS",
                export_extras=True, export_apply=False)
        except (RuntimeError, AttributeError) as e:
            self.report({"ERROR"}, f"glTF export failed ({e}); is the glTF 2.0 exporter enabled?")
            return {"CANCELLED"}
        mod = bpy.path.abspath(self.mod_folder).strip() if self.mod_folder else "<your FF9CustomMap folder>"
        argv = bridge.model_import_argv(self.filepath, mod, like=self.like.strip() or None,
                                        no_anims=self.no_anims)
        cmd = "ff9mapkit " + bridge.quote_cmd(argv)
        context.window_manager.clipboard = cmd            # ready to paste in a terminal
        print("[FF9 Map Kit] run:  " + cmd)                # also to the console (copyable there too)
        self.report({"INFO"}, f"wrote {bpy.path.basename(self.filepath)}. Command copied to clipboard -- run "
                              f"it in a terminal:  {cmd}")
        return {"FINISHED"}


CLASSES = (FF9MK_OT_import_model, FF9MK_OT_export_model)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
