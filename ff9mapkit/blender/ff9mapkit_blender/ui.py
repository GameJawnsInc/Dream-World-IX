"""The FF9 Map Kit N-panel (View3D sidebar)."""

from __future__ import annotations

import os

import bpy

from . import ops
from .vendor import cam


class FF9MK_PT_panel(bpy.types.Panel):
    bl_label = "FF9 Map Kit"
    bl_idname = "FF9MK_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "FF9 Map Kit"

    def draw(self, context):
        layout = self.layout
        p = context.scene.ff9mapkit

        row = layout.row(align=True)
        row.operator("ff9mk.setup_scene", icon="SCENE_DATA", text="New Scene")
        row.operator("ff9mk.import_field", icon="IMPORT", text="Import Field")
        if p.borrow_bg:
            layout.label(text=f"forked from {p.borrow_bg} (BG-borrow)", icon="LINKED")

        box = layout.box()
        box.label(text="Camera", icon="CAMERA_DATA")
        col = box.column(align=True)
        col.prop(p, "pitch")
        col.prop(p, "distance")
        col.prop(p, "fov")
        box.prop(p, "scroll_enabled")
        if p.scroll_enabled:
            row = box.row(align=True)
            row.prop(p, "canvas_w")
            row.prop(p, "canvas_h")
        box.operator("ff9mk.pose_camera", icon="VIEW_CAMERA")
        c = None
        try:
            c = ops.active_camera_to_ff9(context)
        except Exception:   # noqa: BLE001 - never let a readout break the panel
            c = None
        if c is not None:
            pd = cam.pitch_deg(c)
            box.label(text=f"FF9: pitch {pd:.1f} deg, FOV {cam.decompose(c)['fov_x_deg']:.1f} deg")
            if cam.pitch_warning(pd):
                wb = box.box()
                wb.alert = True
                wb.label(text="Outside validated FF9 range (<= 50 deg)", icon="ERROR")
                wb.label(text="render is exact; back-edge paint guide may drift")

        box = layout.box()
        box.label(text="Walkmesh", icon="MESH_GRID")
        box.prop(p, "walkmesh")
        row = box.row(align=True)
        row.prop(p, "back_y")
        row.prop(p, "front_y")
        box.operator("ff9mk.compute_guide", icon="IMAGE_REFERENCE")
        box.operator("ff9mk.walkmesh_from_floor", icon="MOD_LATTICE")

        box = layout.box()
        box.label(text="Background Art", icon="IMAGE_DATA")
        box.operator("ff9mk.paint_template", icon="GRID")
        row = box.row(align=True)
        row.operator("ff9mk.add_layer", icon="ADD", text="Add Layer")
        row.operator("ff9mk.clear_layers", icon="TRASH", text="")
        for L in p.layers:
            r = box.row(align=True)
            r.label(text=os.path.basename(L.image) or "(none)", icon="IMAGE_REFERENCE")
            r.prop(L, "z", text="z")
        if not p.layers:
            box.label(text="add painted PNG(s) to model against", icon="INFO")

        box = layout.box()
        box.label(text="Content", icon="OUTLINER_OB_EMPTY")
        row = box.row(align=True)
        row.operator("ff9mk.add_npc", icon="OUTLINER_OB_ARMATURE", text="NPC")
        row.operator("ff9mk.add_gateway", icon="MOD_BOOLEAN", text="Gateway")
        row.operator("ff9mk.set_spawn", icon="MESH_UVSPHERE", text="Spawn")
        # tally + per-type edit hint for the active marker
        npc_n = sum(1 for o in context.scene.objects if o.get(ops.MARKER_KEY) == "npc")
        gw_n = sum(1 for o in context.scene.objects if o.get(ops.MARKER_KEY) == "gateway")
        spawn_n = sum(1 for o in context.scene.objects if o.get(ops.MARKER_KEY) == "spawn")
        box.label(text=f"{npc_n} NPC · {gw_n} gateway · {spawn_n} spawn")
        ao = context.active_object
        mk = ao.get(ops.MARKER_KEY) if ao else None
        if mk == "npc":
            col = box.column(align=True)
            col.label(text=f"{ao.name} (move to position)")
            for key in ("ff9_name", "ff9_preset", "ff9_dialogue"):
                if key in ao:
                    col.prop(ao, f'["{key}"]', text=key[4:])
        elif mk == "gateway":
            col = box.column(align=True)
            col.label(text=f"{ao.name} (move/scale over the exit)")
            for key in ("ff9_to", "ff9_entrance"):
                if key in ao:
                    col.prop(ao, f'["{key}"]', text=key[4:])
        elif mk == "spawn":
            box.label(text=f"{ao.name} (move to set spawn)")
        else:
            box.label(text="select a marker to edit its properties", icon="INFO")

        box = layout.box()
        box.label(text="Export", icon="EXPORT")
        col = box.column(align=True)
        col.prop(p, "field_id")
        col.prop(p, "field_name")
        col.prop(p, "area")
        col.prop(p, "text_block")
        box.prop(p, "export_dir")
        box.operator("ff9mk.export_field", icon="FILE_TICK")


def register():
    bpy.utils.register_class(FF9MK_PT_panel)


def unregister():
    bpy.utils.unregister_class(FF9MK_PT_panel)
