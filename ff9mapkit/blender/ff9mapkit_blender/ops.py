"""Blender operators + scene properties for FF9 Map Kit.

Thin wrappers: each reads/writes Blender objects and delegates the math to `bridge` (which is
bpy-free + offline-validated). Targets Blender 4.2+/5.x.

Workflow: Setup FF9 Scene -> (pose/aim the camera, model the FF9_Walkmesh) -> Compute Paint
Guide -> Export Field -> run `ff9mapkit build <field.toml>`.
"""

from __future__ import annotations

import os
import shutil

import bpy
from mathutils import Matrix

from . import bridge
from .vendor import bgx, cam, guide

CAMERA_NAME = "FF9_Camera"
WALKMESH_NAME = "FF9_Walkmesh"
RANGE_WH = (384, 448)


# --------------------------------------------------------------------------- properties
class FF9MKLayer(bpy.types.PropertyGroup):
    """One painted background layer: a PNG + its depth Z (smaller Z = in front)."""
    image: bpy.props.StringProperty(name="Image", subtype="FILE_PATH")
    z: bpy.props.IntProperty(name="Depth Z", default=4000)


class FF9MKProps(bpy.types.PropertyGroup):
    field_id: bpy.props.IntProperty(name="Field ID", default=4003, min=4000)
    field_name: bpy.props.StringProperty(name="Name", default="MY_ROOM")
    area: bpy.props.IntProperty(name="Area", default=11, min=10)
    text_block: bpy.props.IntProperty(name="Text Block", default=1073)
    pitch: bpy.props.FloatProperty(name="Pitch", default=48.0, min=0.0, max=89.0)
    distance: bpy.props.FloatProperty(name="Distance", default=4500.0, min=1.0)
    fov: bpy.props.FloatProperty(name="FOV", default=42.2, min=1.0, max=170.0)
    back_y: bpy.props.FloatProperty(name="Floor back (canvas Y)", default=205.0)
    front_y: bpy.props.FloatProperty(name="Floor front (canvas Y)", default=432.0)
    walkmesh: bpy.props.PointerProperty(name="Walkmesh", type=bpy.types.Object,
                                        poll=lambda self, o: o.type == "MESH")
    export_dir: bpy.props.StringProperty(name="Export to", subtype="DIR_PATH", default="//ff9field")
    layers: bpy.props.CollectionProperty(type=FF9MKLayer)
    layers_index: bpy.props.IntProperty(default=0)


GUIDE_COLLECTION = "FF9 Guide"


# --------------------------------------------------------------------------- helpers
def _matrix_from_bridge(b):
    R, loc = b["rotation"], b["location"]
    return Matrix(((R[0][0], R[0][1], R[0][2], loc[0]),
                   (R[1][0], R[1][1], R[1][2], loc[1]),
                   (R[2][0], R[2][1], R[2][2], loc[2]),
                   (0.0, 0.0, 0.0, 1.0)))


def _pose_camera(cam_obj, pitch, distance, fov):
    ff9 = guide.make_camera(pitch, distance, fov_x_deg=fov, range_wh=RANGE_WH)
    b = bridge.ff9_cam_to_blender(ff9)
    cam_obj.matrix_world = _matrix_from_bridge(b)
    cam_obj.data.sensor_fit = "HORIZONTAL"
    cam_obj.data.sensor_width = b["sensor_width"]
    cam_obj.data.lens = b["lens"]
    # FF9 world units are large (cameras sit thousands of units from the floor); widen the
    # camera clip range so the scene isn't culled by Blender's default 1000-unit far clip.
    cam_obj.data.clip_start = 1.0
    cam_obj.data.clip_end = 100000.0


def active_camera_to_ff9(context):
    """The scene's active camera as an FF9 cam.Cam (None if there is no camera)."""
    cam_obj = context.scene.camera
    if cam_obj is None or cam_obj.type != "CAMERA":
        return None
    mw = cam_obj.matrix_world
    m3 = mw.to_3x3()
    R_bl = [[m3[i][j] for j in range(3)] for i in range(3)]   # columns = local axes in world
    loc = [mw.translation[i] for i in range(3)]
    return bridge.blender_cam_to_ff9(loc, R_bl, cam_obj.data.lens,
                                     sensor_width=cam_obj.data.sensor_width, range_wh=RANGE_WH)


def _walkmesh_world_mesh(obj):
    """(world_verts, tri_faces) for a mesh object, triangulated."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    verts = [list(mw @ v.co) for v in mesh.vertices]
    faces = [tuple(lt.vertices) for lt in mesh.loop_triangles]
    return verts, faces


def _guide_collection(context):
    """Get (or create) the 'FF9 Guide' collection, emptied of its previous guide objects."""
    coll = bpy.data.collections.get(GUIDE_COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(GUIDE_COLLECTION)
        context.scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return coll


def _rebuild_floor_guide(context, c, back_y, front_y):
    """Build a reference floor grid + labeled markers (where the painted floor lands) as a
    non-selectable wireframe overlay in the 'FF9 Guide' collection. Idempotent."""
    g = bridge.floor_guide_geometry(c, back_y, front_y)
    coll = _guide_collection(context)
    # floor grid (wireframe reference)
    mesh = bpy.data.meshes.new("FF9_Guide_Floor")
    mesh.from_pydata([list(v) for v in g["grid_verts"]], [], [list(f) for f in g["grid_faces"]])
    mesh.update()
    grid = bpy.data.objects.new("FF9_Guide_Floor", mesh)
    grid.display_type = "WIRE"
    grid.hide_select = True
    grid.show_in_front = True
    coll.objects.link(grid)
    # key-point markers
    for label, pos in g["markers"]:
        e = bpy.data.objects.new(f"FF9_Guide_{label}", None)
        e.empty_display_type = "PLAIN_AXES"
        e.empty_display_size = 120.0
        e.location = pos
        e.hide_select = True
        coll.objects.link(e)
    return g


# --------------------------------------------------------------------------- operators
class FF9MK_OT_setup_scene(bpy.types.Operator):
    bl_idname = "ff9mk.setup_scene"
    bl_label = "Setup FF9 Scene"
    bl_description = "Create an FF9-posed camera + a flat walkmesh plane (FF9 floor = Blender z=0)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.ff9mapkit
        coll = context.collection
        # camera
        cam_obj = bpy.data.objects.get(CAMERA_NAME)
        if cam_obj is None or cam_obj.type != "CAMERA":
            cam_data = bpy.data.cameras.new(CAMERA_NAME)
            cam_obj = bpy.data.objects.new(CAMERA_NAME, cam_data)
            coll.objects.link(cam_obj)
        _pose_camera(cam_obj, p.pitch, p.distance, p.fov)
        context.scene.camera = cam_obj
        # walkmesh plane on z=0 (FF9 floor y=0). A simple 2000-unit square the user reshapes.
        wm = bpy.data.objects.get(WALKMESH_NAME)
        if wm is None:
            mesh = bpy.data.meshes.new(WALKMESH_NAME)
            s = 1000.0
            mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [],
                             [(0, 1, 2, 3)])
            mesh.update()
            wm = bpy.data.objects.new(WALKMESH_NAME, mesh)
            coll.objects.link(wm)
        p.walkmesh = wm
        # widen the 3D viewport clipping too, so the large FF9-scale scene is visible when you orbit
        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.clip_start = 1.0
                area.spaces.active.clip_end = 100000.0
        self.report({"INFO"}, "FF9 scene ready: pose the camera, shape FF9_Walkmesh on z=0. "
                              "Press Home to frame everything.")
        return {"FINISHED"}


class FF9MK_OT_pose_camera(bpy.types.Operator):
    bl_idname = "ff9mk.pose_camera"
    bl_label = "Pose Camera from Pitch/FOV"
    bl_description = "Snap the active camera to the Pitch / Distance / FOV above"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cam_obj = context.scene.camera
        if cam_obj is None or cam_obj.type != "CAMERA":
            self.report({"ERROR"}, "No active camera (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        _pose_camera(cam_obj, p.pitch, p.distance, p.fov)
        return {"FINISHED"}


class FF9MK_OT_compute_guide(bpy.types.Operator):
    bl_idname = "ff9mk.compute_guide"
    bl_label = "Compute Paint Guide"
    bl_description = "Report where the floor/walkmesh lands on the 384x448 painted canvas; writes guide.txt"

    def execute(self, context):
        c = active_camera_to_ff9(context)
        if c is None:
            self.report({"ERROR"}, "No active camera.")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        frame = guide.frame_floor(c, back_canvas_y=p.back_y, front_canvas_y=p.front_y)
        lines = ["FF9 Map Kit paint guide (canvas is 384 x 448, top-left origin, Y down)", ""]
        lines.append(f"camera pitch ~{cam.pitch_deg(c):.1f} deg, FOV_x {cam.decompose(c)['fov_x_deg']:.1f} deg")
        w = cam.pitch_warning(cam.pitch_deg(c))
        if w:
            lines.append("WARNING: " + w)
        lines.append("")
        lines.append("framed floor (world z -> canvas corner px):")
        for nm, (wx, wy, wz), cv in zip(("back-L", "back-R", "front-R", "front-L"),
                                        frame.corners_world, frame.corners_canvas):
            lines.append(f"  {nm:7} world=({wx},{wy},{wz}) -> canvas {cv}")
        lines.append(f"  walkmesh corners (x,z): {guide.walkmesh_corners(frame)}")
        # the designated walkmesh's own world bounds projected to canvas
        if p.walkmesh and p.walkmesh.type == "MESH":
            verts, _ = _walkmesh_world_mesh(p.walkmesh)
            ff9v = bridge.blender_verts_to_ff9(verts)
            canv = [cam.to_canvas(v, c) for v in ff9v]
            xs = [cx for cx, cy in canv]
            ys = [cy for cx, cy in canv]
            lines.append("")
            lines.append(f"walkmesh '{p.walkmesh.name}' canvas bounds: "
                         f"x[{min(xs):.0f}..{max(xs):.0f}] y[{min(ys):.0f}..{max(ys):.0f}]")
        text = "\n".join(lines)
        # write guide.txt next to the export dir
        out = bpy.path.abspath(p.export_dir)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "guide.txt"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
        # build the visible floor guide (grid + markers) in the viewport
        _rebuild_floor_guide(context, c, p.back_y, p.front_y)
        self.report({"INFO"}, f"paint guide written to {os.path.join(out, 'guide.txt')} + "
                              f"'{GUIDE_COLLECTION}' floor grid in the viewport")
        print("[FF9 Map Kit]\n" + text)
        return {"FINISHED"}


class FF9MK_OT_add_layer(bpy.types.Operator):
    bl_idname = "ff9mk.add_layer"
    bl_label = "Add Background Layer"
    bl_description = ("Load a painted PNG as a camera background image (model the walkmesh against "
                      "it) and add it to the field's [[layers]]")
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.png;*.tga", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        p = context.scene.ff9mapkit
        cam_obj = context.scene.camera
        if cam_obj is None or cam_obj.type != "CAMERA":
            self.report({"ERROR"}, "No active camera (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        if not self.filepath:
            self.report({"ERROR"}, "No image selected.")
            return {"CANCELLED"}
        # match the painted canvas aspect so a FIT background lines up with the FF9 frame
        context.scene.render.resolution_x = RANGE_WH[0]
        context.scene.render.resolution_y = RANGE_WH[1]
        img = bpy.data.images.load(self.filepath, check_existing=True)
        cam_data = cam_obj.data
        cam_data.show_background_images = True
        bg = cam_data.background_images.new()
        bg.image = img
        bg.display_depth = "BACK"
        bg.frame_method = "FIT"
        bg.alpha = 1.0
        # record the layer; back-most defaults to 4000, each subsequent 1000 in front
        L = p.layers.add()
        L.image = self.filepath
        L.z = 4000 - 1000 * (len(p.layers) - 1)
        p.layers_index = len(p.layers) - 1
        self.report({"INFO"}, f"added layer {os.path.basename(self.filepath)} (z={L.z}); "
                              f"view through the FF9 camera (Numpad 0) to model against it")
        return {"FINISHED"}


class FF9MK_OT_clear_layers(bpy.types.Operator):
    bl_idname = "ff9mk.clear_layers"
    bl_label = "Clear Background Layers"
    bl_description = "Remove all background layers + camera background images"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.ff9mapkit
        p.layers.clear()
        cam_obj = context.scene.camera
        if cam_obj is not None and cam_obj.type == "CAMERA":
            bgs = cam_obj.data.background_images
            while len(bgs):
                bgs.remove(bgs[0])
        self.report({"INFO"}, "cleared background layers")
        return {"FINISHED"}


class FF9MK_OT_export_field(bpy.types.Operator):
    bl_idname = "ff9mk.export_field"
    bl_label = "Export Field"
    bl_description = "Write camera.bgx + walkmesh.obj + field.toml for `ff9mapkit build`"

    def execute(self, context):
        c = active_camera_to_ff9(context)
        if c is None:
            self.report({"ERROR"}, "No active camera.")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        if not p.walkmesh or p.walkmesh.type != "MESH":
            self.report({"ERROR"}, "Set a Walkmesh mesh object.")
            return {"CANCELLED"}
        out = bpy.path.abspath(p.export_dir)
        os.makedirs(out, exist_ok=True)

        # camera.bgx (camera-only; field.toml borrows it)
        with open(os.path.join(out, "camera.bgx"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(bgx.build(c, [], header_comment=f"{p.field_name} camera (ff9mapkit blender)"))
        # walkmesh.obj (FF9 coords)
        verts, faces = _walkmesh_world_mesh(p.walkmesh)
        with open(os.path.join(out, "walkmesh.obj"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(bridge.mesh_to_ff9_obj(verts, faces))
        # painted layers: copy each PNG next to the toml + collect (basename, z)
        layers = []
        for L in p.layers:
            src = bpy.path.abspath(L.image)
            if not src or not os.path.isfile(src):
                self.report({"WARNING"}, f"layer image missing, skipped: {L.image}")
                continue
            dst = os.path.join(out, os.path.basename(src))
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
            layers.append({"image": os.path.basename(src), "z": int(L.z)})
        # field.toml
        toml = _field_toml(p, layers)
        with open(os.path.join(out, f"{p.field_name.lower()}.field.toml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(toml)
        self.report({"INFO"}, f"exported {len(layers)} layer(s) to {out}; now run: ff9mapkit "
                              f"build {p.field_name.lower()}.field.toml")
        return {"FINISHED"}


def _field_toml(p, layers):
    # [[layers]] block: real if the user loaded painted art, else a commented hint
    if layers:
        layers_block = bridge.layers_to_toml(layers) + "\n"
    else:
        layers_block = ('# [[layers]]\n#   image = "back.png"\n#   z = 4000\n'
                        '# [[layers]]\n#   image = "floor.png"\n#   z = 3000\n')
    return (
        f"# {p.field_name} — exported from Blender by FF9 Map Kit. Compile with:\n"
        f"#   ff9mapkit build {p.field_name.lower()}.field.toml\n"
        f"# The painted PNGs were copied next to this file; fill in [[npc]] / [[gateway]] as needed.\n\n"
        f"[field]\n"
        f"id = {p.field_id}\n"
        f'name = "{p.field_name}"\n'
        f"area = {p.area}\n"
        f"text_block = {p.text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"   # the exact camera you posed in Blender\n'
        f"[camera.frame]\n"
        f"back = {p.back_y:g}\n"
        f"front = {p.front_y:g}\n\n"
        f"[walkmesh]\n"
        f'obj = "walkmesh.obj"\n'
        f"# slide the walkmesh toward the camera so the 3D character looks planted on the 2D floor\n"
        f"character_offset = {cam.CHARACTER_GROUND_OFFSET_Z:g}\n\n"
        f"{layers_block}\n"
        f"[player]\nspawn = [0, -1100]\n\n"
        f"# [[npc]]\n#   name = \"Someone\"\n#   preset = \"vivi\"\n#   pos = [0, -700]\n"
        f"#   dialogue = \"Hello.\"\n\n"
        f"# [[gateway]]\n#   to = 100\n#   entrance = 0\n"
        f"#   zone = [[-1100,-2400],[1100,-2400],[1100,-1750],[-1100,-1750]]\n"
    )


CLASSES = (FF9MKLayer, FF9MKProps, FF9MK_OT_setup_scene, FF9MK_OT_pose_camera,
           FF9MK_OT_compute_guide, FF9MK_OT_add_layer, FF9MK_OT_clear_layers,
           FF9MK_OT_export_field)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ff9mapkit = bpy.props.PointerProperty(type=FF9MKProps)


def unregister():
    del bpy.types.Scene.ff9mapkit
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
