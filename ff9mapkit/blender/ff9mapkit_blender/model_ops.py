"""One-click "Import/Export FF9 Model" operators -- the Blender front door to the model edit loop.

The model pipeline (reading p0data via UnityPy, writing the loose-FBX + .anim overrides) can't run inside
Blender's bundled Python, so -- unlike the field operators, which vendor bpy-free math -- these SHELL OUT to
the ``ff9mapkit`` CLI (the full env that has UnityPy + the FF9 install) and use Blender's OWN glTF I/O for the
in-Blender half:

  * Import Model : run ``ff9mapkit model-gltf <geo>`` -> import the .glb (rigged + textured + clips).
  * Export Model : export the scene to .glb (the settings the kit's importer expects) -> run
                   ``ff9mapkit model-import <glb> --deploy <mod>`` (writes the mesh AND changed clips).

The CLI command / mod folder / game path live in AddonPreferences (persisted, shown in the panel). If the CLI
can't be found or errors, the operator reports the exact manual command so the user isn't stuck.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

import bpy

from . import bridge

# The AddonPreferences bl_idname must be the ADDON's package key in context.preferences.addons. model_ops is a
# DIRECT submodule, so its __package__ IS that key -- "ff9mapkit_blender" for a legacy install and the full
# "bl_ext.<repo>.ff9mapkit_blender" for a 4.2 extension install (don't split it -- that breaks extensions).
ADDON_ID = __package__
_TIMEOUT = 600                                 # s -- a p0data read + emit is a few seconds; be generous


class FF9MK_ModelPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    ff9mapkit_cmd: bpy.props.StringProperty(
        name="ff9mapkit command", default="ff9mapkit",
        description="How to run the kit CLI (it needs UnityPy + the FF9 install -- so NOT Blender's Python). "
                    "Leave as 'ff9mapkit' for a normal install: the add-on auto-finds it on PATH or at "
                    "~/.local/bin (where the .exe installer's `uv tool install` puts it). Change it only for a "
                    "checkout ('py -m ff9mapkit') or a venv (full path to its python + ' -m ff9mapkit')")
    mod_folder: bpy.props.StringProperty(
        name="Mod folder", subtype="DIR_PATH", default="",
        description="Export target: the Memoria mod folder to write the loose-FBX + .anim override into "
                    "(e.g. <FF9>/FF9CustomMap)")
    game_path: bpy.props.StringProperty(
        name="FF9 install (optional)", subtype="DIR_PATH", default="",
        description="Path to the FF9 install; leave blank to let the CLI auto-detect (Steam/GOG)")

    def draw(self, context):
        col = self.layout.column()
        col.prop(self, "ff9mapkit_cmd")
        col.prop(self, "mod_folder")
        col.prop(self, "game_path")
        col.label(text="Import needs only the command + a working FF9 install; Export also needs the mod folder.",
                  icon="INFO")


def _prefs(context):
    ad = context.preferences.addons.get(ADDON_ID)
    return ad.preferences if ad else None


def _base_argv(context):
    """The argv prefix that runs the CLI. Honors an explicit pref; else finds an installed ``ff9mapkit`` on
    PATH; else the uv-tool launcher at ``~/.local/bin`` (where the EXECUTABLE installer puts it -- so an
    exe-installed user works even if Blender's PATH is stale). See ``bridge.resolve_kit_argv``."""
    p = _prefs(context)
    configured = p.ff9mapkit_cmd if p else ""
    cand = os.path.join(os.path.expanduser("~"), ".local", "bin",
                        "ff9mapkit.exe" if os.name == "nt" else "ff9mapkit")
    local_hit = cand if os.path.isfile(cand) else None
    return bridge.resolve_kit_argv(configured, shutil.which("ff9mapkit"), local_hit)


def _game_arg(context):
    p = _prefs(context)
    g = (p.game_path if p else "").strip()
    return bpy.path.abspath(g) if g else None


def _run(argv):
    """Run the CLI. Returns (ok, stdout, stderr, launch_error|None). A missing command -> launch_error set."""
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=_TIMEOUT)
        return r.returncode == 0, r.stdout or "", r.stderr or "", None
    except FileNotFoundError:
        return False, "", "", (f"couldn't run {argv[0]!r} -- set the correct 'ff9mapkit command' in "
                               f"Preferences > Add-ons > FF9 Map Kit")
    except subprocess.TimeoutExpired:
        return False, "", "", "the ff9mapkit CLI timed out"


def _last_line(text, default=""):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    return lines[-1] if lines else default


class FF9MK_OT_import_model(bpy.types.Operator):
    bl_idname = "ff9mk.import_model"
    bl_label = "Import FF9 Model"
    bl_description = ("Run `ff9mapkit model-gltf <geo>` and import the result -- a rigged, textured model "
                     "with its idle/walk/run clips. Edit it, then Export FF9 Model to send it back to the game")
    bl_options = {"REGISTER", "UNDO"}

    geo: bpy.props.StringProperty(
        name="Model", default="GEO_MAIN_F0_VIV",
        description="GEO name or id to import (see `ff9mapkit models`), e.g. GEO_MAIN_F0_VIV or 8")
    anims: bpy.props.EnumProperty(
        name="Clips", default="auto",
        items=[("auto", "auto (idle/walk/run/turns)", "the model's named idle/walk/run/turn clips"),
               ("all", "all (whole folder)", "every clip in the model's folder"),
               ("none", "none", "geometry + rig only, no animation")])

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        geo = self.geo.strip()
        if not geo:
            self.report({"ERROR"}, "enter a GEO name or id (e.g. GEO_MAIN_F0_VIV)")
            return {"CANCELLED"}
        out = os.path.join(tempfile.gettempdir(), "ff9mk_model_" + bridge.safe_stem(geo) + ".glb")
        argv = _base_argv(context) + bridge.model_gltf_argv(geo, anims=self.anims, out=out,
                                                            game=_game_arg(context))
        ok, so, se, launch_err = _run(argv)
        if launch_err:
            self.report({"ERROR"}, launch_err + f"  (manual: {' '.join(argv)})")
            return {"CANCELLED"}
        if not ok or not os.path.isfile(out):
            self.report({"ERROR"}, "model-gltf failed: " + (_last_line(se) or _last_line(so) or "see console"))
            return {"CANCELLED"}
        try:
            bpy.ops.import_scene.gltf(filepath=out)
        except (RuntimeError, AttributeError) as e:
            self.report({"ERROR"}, f"glTF import failed ({e}); is the glTF 2.0 importer enabled?")
            return {"CANCELLED"}
        self.report({"INFO"}, f"imported {geo}: edit the mesh/pose, then Export FF9 Model. ({_last_line(so)})")
        return {"FINISHED"}


class FF9MK_OT_export_model(bpy.types.Operator):
    bl_idname = "ff9mk.export_model"
    bl_label = "Export FF9 Model"
    bl_description = ("Export the scene to glTF and run `ff9mapkit model-import ... --deploy <mod>` -- writes "
                     "the loose-FBX mesh override AND any changed animation clips. Set the mod folder in "
                     "Preferences. F6 -> Reload field in-game to see it")
    bl_options = {"REGISTER"}

    like: bpy.props.StringProperty(
        name="Like (optional)", default="",
        description="GEO whose rig + textures to keep (auto-detected from the glTF stamp if blank -- usually "
                    "leave empty). Give it for a foreign glTF or to force a different source model")
    no_anims: bpy.props.BoolProperty(
        name="Mesh only (skip animations)", default=False,
        description="Import the mesh only; don't write back edited animation clips")
    selection_only: bpy.props.BoolProperty(
        name="Selected objects only", default=False,
        description="Export only the selected objects instead of the whole scene (use if the scene has "
                    "stray objects beyond the FF9 model + its armature)")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        p = _prefs(context)
        mod = bpy.path.abspath(p.mod_folder).strip() if p and p.mod_folder else ""
        if not mod:
            self.report({"ERROR"}, "set the Mod folder in Preferences > Add-ons > FF9 Map Kit")
            return {"CANCELLED"}
        glb = os.path.join(tempfile.gettempdir(), "ff9mk_model_export.glb")
        try:
            # The settings the kit's importer expects: GLB, Y-up, skins + animations + custom-property extras
            # (the ff9_geo / ff9_anim_key stamps that route the re-import); modifiers NOT applied so the rig
            # survives (the kit re-rigs if Blender changed the vertex count).
            bpy.ops.export_scene.gltf(
                filepath=glb, export_format="GLB", use_selection=self.selection_only,
                export_yup=True, export_skins=True, export_animations=True,
                export_extras=True, export_apply=False)
        except (RuntimeError, AttributeError) as e:
            self.report({"ERROR"}, f"glTF export failed ({e}); is the glTF 2.0 exporter enabled?")
            return {"CANCELLED"}
        argv = _base_argv(context) + bridge.model_import_argv(
            glb, mod, like=self.like.strip() or None, no_anims=self.no_anims, game=_game_arg(context))
        ok, so, se, launch_err = _run(argv)
        if launch_err:
            self.report({"ERROR"}, launch_err + f"  (manual: {' '.join(argv)})")
            return {"CANCELLED"}
        if not ok:
            self.report({"ERROR"}, "model-import failed: " + (_last_line(se) or _last_line(so) or "see console"))
            return {"CANCELLED"}
        self.report({"INFO"}, "deployed to the game -> F6 > Reload field (RELAUNCH for a NEW id). "
                              + (_last_line(so) or ""))
        return {"FINISHED"}


CLASSES = (FF9MK_ModelPreferences, FF9MK_OT_import_model, FF9MK_OT_export_model)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
