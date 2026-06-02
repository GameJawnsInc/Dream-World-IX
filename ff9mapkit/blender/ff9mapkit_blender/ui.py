"""The FF9 Map Kit N-panel (View3D sidebar)."""

from __future__ import annotations

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

        layout.operator("ff9mk.setup_scene", icon="SCENE_DATA")

        box = layout.box()
        box.label(text="Camera", icon="CAMERA_DATA")
        col = box.column(align=True)
        col.prop(p, "pitch")
        col.prop(p, "distance")
        col.prop(p, "fov")
        box.operator("ff9mk.pose_camera", icon="CON_CAMERASOLVED")
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
