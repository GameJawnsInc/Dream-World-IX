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
SCREEN_W = 384          # the visible field width; a scrolling painting is wider and the FOV is
                        # always measured at this width (a wide Range must not change the focal length)


def _range_wh(p):
    """The painted-canvas size: the full painting for a scrolling field, else one 384x448 screen."""
    return (int(p.canvas_w), int(p.canvas_h)) if p.scroll_enabled else RANGE_WH

# content markers (Phase 2): tagged Blender objects -> [[npc]]/[[gateway]]/[player] on export.
MARKER_KEY = "ff9_marker"            # obj[MARKER_KEY] in {"npc", "gateway", "spawn"}
GATEWAY_HALF_W = 700.0               # default gateway quad half-extents (FF9 ~= Blender units)
GATEWAY_HALF_D = 250.0


# --------------------------------------------------------------------------- properties
def _layer_z_update(self, context):
    """Foreground layers (small z) preview IN FRONT of the scene; background layers behind."""
    cam_obj = context.scene.camera
    if cam_obj is None or cam_obj.type != "CAMERA":
        return
    tgt = os.path.basename(self.image)
    for bg in cam_obj.data.background_images:
        if bg.image and os.path.basename(bg.image.filepath) == tgt:
            bg.display_depth = "FRONT" if self.z < 1000 else "BACK"


class FF9MKLayer(bpy.types.PropertyGroup):
    """One painted background layer: a PNG + its depth Z (smaller Z = in front)."""
    image: bpy.props.StringProperty(name="Image", subtype="FILE_PATH")
    z: bpy.props.IntProperty(name="Depth Z", default=4000, update=_layer_z_update)


class FF9MKProps(bpy.types.PropertyGroup):
    field_id: bpy.props.IntProperty(name="Field ID", default=4003, min=4000)
    field_name: bpy.props.StringProperty(name="Name", default="MY_ROOM")
    area: bpy.props.IntProperty(name="Area", default=11, min=10)
    text_block: bpy.props.IntProperty(name="Text Block", default=1073)
    # set by "Import FF9 Field": the REAL field's mapid. When non-empty the field is BG-borrow
    # (engine renders that field's art/walkmesh/camera) and Export emits a borrow field.toml.
    borrow_bg: bpy.props.StringProperty(name="Borrow BG", default="")
    pitch: bpy.props.FloatProperty(name="Pitch", default=48.0, min=0.0, max=89.0)
    distance: bpy.props.FloatProperty(name="Distance", default=4500.0, min=1.0)
    fov: bpy.props.FloatProperty(name="FOV", default=42.2, min=1.0, max=170.0)
    # larger-than-screen scrolling: the painting is wider/taller than the 384x448 screen and the
    # view pans to follow the player. FOV stays measured at the 384 screen width (window_width).
    scroll_enabled: bpy.props.BoolProperty(
        name="Scrolling room", default=False,
        description="Larger-than-screen painting the view pans across (FF9 streets/corridors)")
    canvas_w: bpy.props.IntProperty(name="Canvas W", default=768, min=384,
                                    description="Full painting width (>= 384; 768 = 2x screen)")
    canvas_h: bpy.props.IntProperty(name="Canvas H", default=448, min=448,
                                    description="Full painting height (>= 448)")
    back_y: bpy.props.FloatProperty(name="Floor back (canvas Y)", default=205.0)
    front_y: bpy.props.FloatProperty(name="Floor front (canvas Y)", default=432.0)
    walkmesh: bpy.props.PointerProperty(name="Walkmesh", type=bpy.types.Object,
                                        poll=lambda self, o: o.type == "MESH")
    export_dir: bpy.props.StringProperty(
        name="Export to", subtype="DIR_PATH", default="ff9field",
        description="Output folder. A plain name (or //name) resolves next to the .blend; or pick "
                    "an absolute folder. If the .blend is unsaved it falls back to ~/<name>")
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


def _pose_camera(cam_obj, p):
    rw, rh = _range_wh(p)
    if p.scroll_enabled:
        # wide painting, normal focal length (proj from the 384 screen), + scroll bounds
        ff9 = guide.make_camera(p.pitch, p.distance, proj=guide.proj_from_fov_x(p.fov, SCREEN_W),
                                range_wh=(rw, rh), viewport=tuple(cam.scroll_bounds((rw, rh))))
        # sensor = the FULL painting width so the Blender viewport shows the backdrop + walkmesh at
        # the SAME scale as in-game (to_canvas). Using the 384 window here made the camera FOV too
        # narrow (~42 vs ~75 deg), so the backdrop looked ~1.8x too big and walkmeshes got modelled
        # ~1.8x too small. proj is still the window focal, so the EXPORTED camera is unchanged.
        b = bridge.ff9_cam_to_blender(ff9, sensor_width=float(rw))
    else:
        ff9 = guide.make_camera(p.pitch, p.distance, fov_x_deg=p.fov, range_wh=(rw, rh))
        b = bridge.ff9_cam_to_blender(ff9)
    cam_obj.matrix_world = _matrix_from_bridge(b)
    cam_obj.data.sensor_fit = "HORIZONTAL"
    cam_obj.data.sensor_width = b["sensor_width"]
    cam_obj.data.lens = b["lens"]
    # FF9 world units are large (cameras sit thousands of units from the floor); widen the
    # camera clip range so the scene isn't culled by Blender's default 1000-unit far clip.
    cam_obj.data.clip_start = 1.0
    cam_obj.data.clip_end = 100000.0


def _pose_camera_from_ff9(cam_obj, c0, scrolling):
    """Pose a Blender camera to match an EXACT FF9 cam.Cam (used by Import FF9 Field)."""
    rw = float(c0.range[0])
    b = bridge.ff9_cam_to_blender(c0, sensor_width=rw) if scrolling else bridge.ff9_cam_to_blender(c0)
    cam_obj.matrix_world = _matrix_from_bridge(b)
    cam_obj.data.sensor_fit = "HORIZONTAL"
    cam_obj.data.sensor_width = b["sensor_width"]
    cam_obj.data.lens = b["lens"]
    cam_obj.data.clip_start = 1.0
    cam_obj.data.clip_end = 100000.0


def _spawn_at_ff9(context, xz):
    """Place (or move) the single FF9_Spawn marker at FF9 floor (x, z)."""
    loc = bridge.ff9_verts_to_blender([(xz[0], 0, xz[1])])[0]
    e = next((o for o in context.scene.objects if o.get(MARKER_KEY) == "spawn"), None)
    if e is None:
        e = bpy.data.objects.new("FF9_Spawn", None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = 180.0
        e[MARKER_KEY] = "spawn"
        _link_active(context, e)
    e.location = loc


def _apply_canvas_resolution(context, rw, rh):
    """Match the render resolution to the FF9 canvas so the camera frames the field at the right
    aspect. FF9 fields are 384x448 portrait (wider when scrolling); Blender defaults to 1920x1080
    landscape, which makes the matched camera look too wide / off-centre in the viewport."""
    r = context.scene.render
    r.resolution_x = int(rw)
    r.resolution_y = int(rh)
    r.resolution_percentage = 100


def active_camera_to_ff9(context):
    """The scene's active camera as an FF9 cam.Cam (None if there is no camera)."""
    cam_obj = context.scene.camera
    if cam_obj is None or cam_obj.type != "CAMERA":
        return None
    p = context.scene.ff9mapkit
    mw = cam_obj.matrix_world
    m3 = mw.to_3x3()
    R_bl = [[m3[i][j] for j in range(3)] for i in range(3)]   # columns = local axes in world
    loc = [mw.translation[i] for i in range(3)]
    rw, rh = _range_wh(p)
    if p.scroll_enabled:
        # the FF9 scroll camera's frame IS the full painting, so interpret the sensor as the canvas
        # width (proj = lens). This is robust to a STALE camera posed by an older add-on version
        # (whose sensor is 384) — otherwise the focal would come out doubled (proj 996 not 498).
        return bridge.blender_cam_to_ff9(
            loc, R_bl, cam_obj.data.lens, sensor_width=float(rw),
            range_wh=(rw, rh), viewport=tuple(cam.scroll_bounds((rw, rh))))
    return bridge.blender_cam_to_ff9(loc, R_bl, cam_obj.data.lens,
                                     sensor_width=cam_obj.data.sensor_width, range_wh=(rw, rh))


def _walkmesh_world_mesh(obj):
    """(world_verts, tri_faces) for a mesh object, triangulated.

    Flushes live Edit-Mode edits first: Blender doesn't push edit-mode changes to ``obj.data``
    until you leave Edit Mode, so exporting mid-edit would otherwise capture the STALE mesh.
    """
    if obj.mode == "EDIT":
        obj.update_from_editmode()
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    verts = [list(mw @ v.co) for v in mesh.vertices]
    faces = [tuple(lt.vertices) for lt in mesh.loop_triangles]
    return verts, faces


def _set_quad_mesh(obj, corners):
    """Reset a mesh object to a single flat quad at world `corners` (object transform -> identity)."""
    obj.matrix_world = Matrix.Identity(4)
    mesh = obj.data
    mesh.clear_geometry()
    mesh.from_pydata([list(c) for c in corners], [], [(0, 1, 2, 3)])
    mesh.update()


def _resolve_out_dir(export_dir):
    """Absolute output dir from the 'Export to' value, robust to Blender 5.x's `//` handling.

    - an absolute path is used as-is;
    - a plain name ("ff9field") or a //-relative name resolves NEXT TO the .blend if it's saved;
    - if the .blend is unsaved, falls back to ~/<name>.
    (Blender 5.x flags `//` on this property type, so we resolve relative names ourselves rather
    than relying on bpy.path.abspath of a `//` string.)
    """
    s = (export_dir or "").strip()
    if s and os.path.isabs(s):
        return s
    name = s[2:] if s.startswith("//") else s          # strip the blend-relative prefix
    name = name or "ff9field"
    blend = bpy.data.filepath
    base = os.path.dirname(blend) if blend else os.path.expanduser("~")
    return os.path.join(base, name)


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
    # vertical height guides (poles at the floor edges + a ceiling box) so walls can be modelled
    # and painted in correct perspective — not just a flat floor.
    if g.get("wall_verts") and g.get("wall_edges"):
        wmesh = bpy.data.meshes.new("FF9_Guide_Walls")
        wmesh.from_pydata([list(v) for v in g["wall_verts"]],
                          [list(e) for e in g["wall_edges"]], [])
        wmesh.update()
        walls = bpy.data.objects.new("FF9_Guide_Walls", wmesh)
        walls.display_type = "WIRE"
        walls.hide_select = True
        walls.show_in_front = True
        coll.objects.link(walls)
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
        _pose_camera(cam_obj, p)
        _apply_canvas_resolution(context, *_range_wh(p))
        context.scene.camera = cam_obj
        # walkmesh = the floor-frame quad on z=0, so it starts ON the painted floor (lined up with
        # the guide grid). The user reshapes it from there.
        c = active_camera_to_ff9(context)
        try:
            corners = bridge.floor_quad_blender(c, p.back_y, p.front_y)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        wm = bpy.data.objects.get(WALKMESH_NAME)
        if wm is None:
            wm = bpy.data.objects.new(WALKMESH_NAME, bpy.data.meshes.new(WALKMESH_NAME))
            coll.objects.link(wm)
        _set_quad_mesh(wm, corners)
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
        _pose_camera(cam_obj, p)
        _apply_canvas_resolution(context, *_range_wh(p))
        return {"FINISHED"}


class FF9MK_OT_walkmesh_from_floor(bpy.types.Operator):
    bl_idname = "ff9mk.walkmesh_from_floor"
    bl_label = "Reset Walkmesh to Floor"
    bl_description = ("Replace the walkmesh with a flat quad matching the CURRENT floor frame "
                      "(re-pose the camera, then click this to re-align). Discards its current shape")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        c = active_camera_to_ff9(context)
        if c is None:
            self.report({"ERROR"}, "No active camera (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        wm = p.walkmesh
        if wm is None or wm.type != "MESH":
            self.report({"ERROR"}, "No walkmesh set (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        try:
            corners = bridge.floor_quad_blender(c, p.back_y, p.front_y)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        _set_quad_mesh(wm, corners)
        self.report({"INFO"}, "walkmesh reset to the current floor frame")
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
        try:
            frame = guide.frame_floor(c, back_canvas_y=p.back_y, front_canvas_y=p.front_y)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
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
        # build the visible floor guide (grid + markers) in the viewport (needs no file path)
        _rebuild_floor_guide(context, c, p.back_y, p.front_y)
        # write guide.txt (best-effort; never let an unwritable path abort the guide)
        msg = f"'{GUIDE_COLLECTION}' floor grid built in the viewport"
        out = _resolve_out_dir(p.export_dir)
        try:
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, "guide.txt"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text + "\n")
            msg += f"; guide.txt -> {out}"
        except OSError as e:
            msg += f" (guide.txt not written: {e.strerror}; save the .blend or set Export to)"
        self.report({"INFO"}, msg)
        print("[FF9 Map Kit]\n" + text)
        return {"FINISHED"}


class FF9MK_OT_paint_template(bpy.types.Operator):
    bl_idname = "ff9mk.paint_template"
    bl_label = "Export Paint Template"
    bl_description = ("Write a transparent 1536x1792 trace-over paint template (floor outline + "
                      "perspective grid) for the current camera; paint your room on layers UNDER it")

    def execute(self, context):
        import array
        c = active_camera_to_ff9(context)
        if c is None:
            self.report({"ERROR"}, "No active camera (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        try:
            t = bridge.paint_template_lines(c, p.back_y, p.front_y, scale=4)
        except ValueError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        W, H = t["size"]
        buf = array.array("f", bytes(W * H * 4 * 4))          # all 0.0 -> transparent

        def line(p0, p1, rgba):
            x0, y0 = p0; x1, y1 = p1
            dx, dy = x1 - x0, y1 - y0
            n = int(max(abs(dx), abs(dy)))
            for i in range(n + 1):
                tt = i / n if n else 0.0
                x = int(round(x0 + dx * tt)); y = int(round(y0 + dy * tt))
                if 0 <= x < W and 0 <= y < H:
                    idx = ((H - 1 - y) * W + x) * 4           # bpy image rows are bottom-up
                    buf[idx], buf[idx + 1], buf[idx + 2], buf[idx + 3] = rgba

        for a, b in t["grid"]:                                # faint perspective grid
            line(a, b, (0.82, 0.84, 0.90, 0.35))
        for a, b in t.get("height", []):                      # vertical guides: poles/rings/ceiling
            line(a, b, (0.35, 0.86, 0.92, 0.80))
        for a, b in t["outline"]:                             # bright floor outline (~3px)
            for o in (-1, 0, 1):
                line((a[0], a[1] + o), (b[0], b[1] + o), (1.0, 0.67, 0.24, 0.95))
                line((a[0] + o, a[1]), (b[0] + o, b[1]), (1.0, 0.67, 0.24, 0.95))

        old = bpy.data.images.get("FF9_PaintTemplate")
        if old:
            bpy.data.images.remove(old)
        img = bpy.data.images.new("FF9_PaintTemplate", W, H, alpha=True)
        img.pixels.foreach_set(buf)
        out = _resolve_out_dir(p.export_dir)
        try:
            os.makedirs(out, exist_ok=True)
            path = os.path.join(out, "paint_template.png")
            img.filepath_raw = path
            img.file_format = "PNG"
            img.save()
        except OSError as e:
            self.report({"ERROR"}, f"can't write template: {e.strerror}. Save the .blend or set 'Export to'.")
            return {"CANCELLED"}
        self.report({"INFO"}, f"paint template ({W}x{H}) -> {path}; paint your room on layers UNDER it")
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
        rw, rh = _range_wh(p)
        context.scene.render.resolution_x = rw
        context.scene.render.resolution_y = rh
        img = bpy.data.images.load(self.filepath, check_existing=True)
        cam_data = cam_obj.data
        cam_data.show_background_images = True
        bg = cam_data.background_images.new()
        bg.image = img
        bg.frame_method = "FIT"
        bg.alpha = 1.0
        # record the layer; back-most defaults to 4000, each subsequent 1000 in front
        L = p.layers.add()
        L.image = self.filepath
        z = 4000 - 1000 * (len(p.layers) - 1)
        bg.display_depth = "FRONT" if z < 1000 else "BACK"
        L.z = z                                       # also fires _layer_z_update
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
        # clear the camera background images AND switch the preview off, on both the FF9 camera
        # (by name) and the active scene camera — covers the case where they differ.
        seen = set()
        for cam_obj in (bpy.data.objects.get(CAMERA_NAME), context.scene.camera):
            if cam_obj is None or cam_obj.type != "CAMERA" or cam_obj.name in seen:
                continue
            seen.add(cam_obj.name)
            cd = cam_obj.data
            try:
                cd.background_images.clear()
            except AttributeError:                       # older API: remove one by one
                while len(cd.background_images):
                    cd.background_images.remove(cd.background_images[0])
            cd.show_background_images = False             # hide the preview even if one lingered
        for area in context.screen.areas:                # repaint so it disappears immediately
            if area.type == "VIEW_3D":
                area.tag_redraw()
        self.report({"INFO"}, "cleared background layers + camera preview")
        return {"FINISHED"}


# --------------------------------------------------------------------------- content markers
def _cursor_floor(context):
    """3D-cursor x,y with z forced to 0 (markers live on the FF9 floor plane)."""
    cur = context.scene.cursor.location
    return (cur[0], cur[1], 0.0)


def _link_active(context, obj):
    context.collection.objects.link(obj)
    for o in context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _collect_markers(context):
    """Read tagged marker objects into (npcs, gateways, spawn), in FF9 floor coords.

    Deterministic: NPCs + gateways are sorted by object name. ``spawn`` is the last FF9_Spawn
    found (there should be one), or None."""
    npcs, gateways, spawn = [], [], None
    for obj in sorted(context.scene.objects, key=lambda o: o.name):
        mk = obj.get(MARKER_KEY)
        if not mk:
            continue
        if mk == "spawn":
            spawn = bridge.marker_floor_pos(obj.matrix_world.translation)
        elif mk == "npc":
            n = {"pos": bridge.marker_floor_pos(obj.matrix_world.translation)}
            if obj.get("ff9_name"):
                n["name"] = obj["ff9_name"]
            if obj.get("ff9_preset"):
                n["preset"] = obj["ff9_preset"]
            if obj.get("ff9_dialogue"):
                n["dialogue"] = obj["ff9_dialogue"]
            npcs.append(n)
        elif mk == "gateway" and obj.type == "MESH":
            mw = obj.matrix_world
            verts = [list(mw @ v.co) for v in obj.data.vertices[:4]]
            if len(verts) < 4:
                continue
            gateways.append({"to": int(obj.get("ff9_to", 100)),
                             "entrance": int(obj.get("ff9_entrance", 0)),
                             "zone": [bridge.marker_floor_pos(v) for v in verts]})
    return npcs, gateways, spawn


class FF9MK_OT_add_npc(bpy.types.Operator):
    bl_idname = "ff9mk.add_npc"
    bl_label = "Add NPC"
    bl_description = ("Drop an NPC marker (Empty) at the 3D cursor on the floor. Edit its model + "
                      "dialogue in Object Properties > Custom Properties (ff9_preset / ff9_dialogue)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        e = bpy.data.objects.new("FF9_NPC", None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 200.0
        e.location = _cursor_floor(context)
        e[MARKER_KEY] = "npc"
        e["ff9_name"] = "NPC"
        e["ff9_preset"] = "vivi"
        e["ff9_dialogue"] = "Hello."
        _link_active(context, e)
        self.report({"INFO"}, f"added NPC '{e.name}' — set ff9_preset / ff9_dialogue in Custom Properties")
        return {"FINISHED"}


class FF9MK_OT_add_gateway(bpy.types.Operator):
    bl_idname = "ff9mk.add_gateway"
    bl_label = "Add Gateway"
    bl_description = ("Drop an exit-zone quad at the 3D cursor on the floor. Move/scale it over the "
                      "exit; set ff9_to (target field) + ff9_entrance in Custom Properties")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cx, cy, _ = _cursor_floor(context)
        hw, hd = GATEWAY_HALF_W, GATEWAY_HALF_D
        # convex CCW rectangle; q0->q1 (the -y / front edge) is the walked-across exit edge
        corners = [(cx - hw, cy - hd, 0.0), (cx + hw, cy - hd, 0.0),
                   (cx + hw, cy + hd, 0.0), (cx - hw, cy + hd, 0.0)]
        mesh = bpy.data.meshes.new("FF9_Gateway")
        mesh.from_pydata([list(c) for c in corners], [], [(0, 1, 2, 3)])
        mesh.update()
        obj = bpy.data.objects.new("FF9_Gateway", mesh)
        obj.display_type = "WIRE"
        obj.show_in_front = True
        obj[MARKER_KEY] = "gateway"
        obj["ff9_to"] = 100
        obj["ff9_entrance"] = 0
        _link_active(context, obj)
        self.report({"INFO"}, f"added gateway '{obj.name}' — set ff9_to / ff9_entrance in Custom Properties")
        return {"FINISHED"}


class FF9MK_OT_set_spawn(bpy.types.Operator):
    bl_idname = "ff9mk.set_spawn"
    bl_label = "Set Player Spawn"
    bl_description = "Place (or move) the single player-spawn marker at the 3D cursor on the floor"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        e = None
        for obj in context.scene.objects:
            if obj.get(MARKER_KEY) == "spawn":
                e = obj
                break
        if e is None:
            e = bpy.data.objects.new("FF9_Spawn", None)
            e.empty_display_type = "SPHERE"
            e.empty_display_size = 180.0
            e[MARKER_KEY] = "spawn"
            _link_active(context, e)
        e.location = _cursor_floor(context)
        self.report({"INFO"}, f"player spawn at {bridge.marker_floor_pos(e.matrix_world.translation)}")
        return {"FINISHED"}


class FF9MK_OT_import_field(bpy.types.Operator):
    bl_idname = "ff9mk.import_field"
    bl_label = "Import FF9 Field"
    bl_description = ("Load a field forked by `ff9mapkit import <field>`: poses the real camera, "
                      "builds the real walkmesh, and sets BG-borrow so the engine renders that "
                      "field's art/walkmesh/camera. Then place NPC/gateway/spawn markers + Export.")
    bl_options = {"REGISTER", "UNDO"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    filter_glob: bpy.props.StringProperty(default="*.bgx;*.toml", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import glob as _glob
        import tomllib
        d = self.directory
        if not d or not os.path.isdir(d):
            self.report({"ERROR"}, "Pick the folder produced by `ff9mapkit import <field> --out <folder>`.")
            return {"CANCELLED"}
        bgx_path = os.path.join(d, "camera.bgx")
        bgi_path = os.path.join(d, "walkmesh.bgi")
        tomls = _glob.glob(os.path.join(d, "*.field.toml"))
        if not (os.path.isfile(bgx_path) and os.path.isfile(bgi_path) and tomls):
            self.report({"ERROR"}, "Folder needs camera.bgx + walkmesh.bgi + a *.field.toml "
                                   "(run: ff9mapkit import <field> --out <folder>).")
            return {"CANCELLED"}
        with open(tomls[0], "rb") as fh:
            cfg = tomllib.load(fh)
        field = cfg.get("field", {})
        cams = cam.parse_bgx_cameras(bgx_path)
        if not cams:
            self.report({"ERROR"}, "no CAMERA in camera.bgx")
            return {"CANCELLED"}
        c0 = cams[0]
        scrolling = c0.range[0] > 384 or c0.range[1] > 448

        p = context.scene.ff9mapkit
        p.field_id = int(field.get("id", 4003))
        p.field_name = field.get("name", "FORK")
        p.area = int(field.get("area", 11))
        p.text_block = int(field.get("text_block", 1073))
        p.borrow_bg = field.get("borrow_bg", "")
        p.scroll_enabled = scrolling
        if scrolling:
            p.canvas_w, p.canvas_h = int(c0.range[0]), int(c0.range[1])
        p.pitch = round(cam.pitch_deg(c0), 2)
        dec = cam.decompose(c0)
        if dec["fov_x_deg"]:
            p.fov = round(dec["fov_x_deg"], 2)
        C = dec["C"]
        p.distance = round((C[0] ** 2 + C[1] ** 2 + C[2] ** 2) ** 0.5, 1)

        # camera (exact, from the extracted .bgx — for the Blender view + movement/scroll on export)
        cam_obj = bpy.data.objects.get(CAMERA_NAME)
        if cam_obj is None:
            cam_obj = bpy.data.objects.new(CAMERA_NAME, bpy.data.cameras.new(CAMERA_NAME))
            context.scene.collection.objects.link(cam_obj)
        _pose_camera_from_ff9(cam_obj, c0, scrolling)
        _apply_canvas_resolution(context, c0.range[0], c0.range[1])
        context.scene.camera = cam_obj

        # real walkmesh -> editable mesh (reference for placing markers; borrow ships the real one)
        with open(bgi_path, "rb") as fh:
            verts, faces = bridge.bgi_walkmesh_to_blender(fh.read())
        wm_obj = bpy.data.objects.get(WALKMESH_NAME)
        if wm_obj is None:
            wm_obj = bpy.data.objects.new(WALKMESH_NAME, bpy.data.meshes.new(WALKMESH_NAME))
            context.scene.collection.objects.link(wm_obj)
        old = wm_obj.data
        mesh = bpy.data.meshes.new(WALKMESH_NAME)
        # Flatten to the floor plane (z=0). FF9 walkmeshes are ~flat (typically 90%+ of verts at one
        # height); the few raised verts (ramps/ladder markers) otherwise read as confusing vertical
        # strips against the flat backdrop. BG-borrow uses the REAL 3D walkmesh in-game; this flat
        # footprint is the modelling reference for placing content on the art.
        mesh.from_pydata([[v[0], v[1], 0.0] for v in verts], [], [list(f) for f in faces])
        mesh.update()
        wm_obj.data = mesh
        if old and old.users == 0:
            bpy.data.meshes.remove(old)
        p.walkmesh = wm_obj

        # Reframe (viewport-only): a real field's .bgi verts live in a corner-origin local frame, but
        # the extracted camera is in the centred world frame, so the posed camera aims off the floor.
        # Slide the camera (POSITION only) so its view axis hits the walkmesh centroid — yaw/pitch and
        # the preserved camera.bgx are untouched, so in-game movement + camera are unaffected, and the
        # walkmesh/markers stay in the frame that exports correctly.
        if verts:
            context.view_layer.update()
            mw = cam_obj.matrix_world
            fwd = -mw.to_3x3().col[2]                 # camera looks down local -Z
            if abs(fwd.z) > 1e-6:
                k = -mw.translation.z / fwd.z
                aim_x = mw.translation.x + k * fwd.x
                aim_y = mw.translation.y + k * fwd.y
                cx = sum(v[0] for v in verts) / len(verts)
                cy = sum(v[1] for v in verts) / len(verts)
                cam_obj.location.x += cx - aim_x
                cam_obj.location.y += cy - aim_y

        spawn = cfg.get("player", {}).get("spawn")
        if spawn and len(spawn) == 2:
            _spawn_at_ff9(context, spawn)
        p.export_dir = d                       # re-export here, preserving the exact camera.bgx

        # real-art backdrop, if `ff9mapkit import` composited one (needs a one-time in-game field
        # export). Loads it as the camera's BACK background so you model against the actual room.
        bg_path = os.path.join(d, "background.png")
        if os.path.isfile(bg_path):
            img = bpy.data.images.load(bg_path, check_existing=True)
            cam_obj.data.show_background_images = True
            bg = cam_obj.data.background_images.new()
            bg.image = img
            bg.frame_method = "FIT"
            bg.alpha = 1.0
            bg.display_depth = "BACK"

        self.report({"INFO"}, f"imported {p.borrow_bg or p.field_name}: real camera + walkmesh loaded. "
                              f"Add NPC/gateway/spawn markers, then Export Field.")
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
        out = _resolve_out_dir(p.export_dir)
        try:
            os.makedirs(out, exist_ok=True)
        except OSError as e:
            self.report({"ERROR"}, f"can't write to {out}: {e.strerror}. Save the .blend or set "
                                   f"'Export to' to a real folder.")
            return {"CANCELLED"}

        if p.borrow_bg:
            # BG-borrow (imported field): the engine renders the REAL field's art+walkmesh+camera,
            # so we ship only the camera (its yaw drives movement) + a borrow field.toml + markers.
            # Preserve the EXACT extracted camera.bgx if it's already here; else write the posed one.
            cbgx = os.path.join(out, "camera.bgx")
            if not os.path.isfile(cbgx):
                with open(cbgx, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(bgx.build(c, [], header_comment=f"{p.field_name} camera (borrowed)"))
            npcs, gateways, spawn = _collect_markers(context)
            with open(os.path.join(out, f"{p.field_name.lower()}.field.toml"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(_field_toml_borrow(p, npcs, gateways, spawn))
            self.report({"INFO"}, f"exported BG-borrow fork of {p.borrow_bg}: {len(npcs)} NPC(s), "
                                  f"{len(gateways)} gateway(s) -> {out}; run: ff9mapkit build "
                                  f"{p.field_name.lower()}.field.toml")
            return {"FINISHED"}

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
        # content markers -> [[npc]] / [[gateway]] / [player]
        npcs, gateways, spawn = _collect_markers(context)
        # field.toml
        toml = _field_toml(p, layers, npcs, gateways, spawn)
        with open(os.path.join(out, f"{p.field_name.lower()}.field.toml"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(toml)
        self.report({"INFO"}, f"exported {len(layers)} layer(s), {len(npcs)} NPC(s), "
                              f"{len(gateways)} gateway(s) to {out}; now run: ff9mapkit "
                              f"build {p.field_name.lower()}.field.toml")
        return {"FINISHED"}


def _field_toml(p, layers, npcs=(), gateways=(), spawn=None):
    # [[layers]] block: real if the user loaded painted art, else a commented hint
    if layers:
        layers_block = bridge.layers_to_toml(layers) + "\n"
    else:
        layers_block = ('# [[layers]]\n#   image = "back.png"\n#   z = 4000\n'
                        '# [[layers]]\n#   image = "floor.png"\n#   z = 3000\n')
    # [player] spawn: from the FF9_Spawn marker, else a default with a hint
    if spawn is not None:
        player_block = bridge.player_to_toml(spawn) + "\n"
    else:
        player_block = '[player]\nspawn = [0, -1100]   # add an FF9_Spawn marker to set this visually\n'
    # [[npc]] / [[gateway]]: from markers, else commented hints
    if npcs:
        npc_block = bridge.npcs_to_toml(npcs) + "\n"
    else:
        npc_block = ('# [[npc]]\n#   name = "Someone"\n#   preset = "vivi"\n#   pos = [0, -700]\n'
                     '#   dialogue = "Hello."\n')
    if gateways:
        gw_block = bridge.gateways_to_toml(gateways) + "\n"
    else:
        gw_block = ('# [[gateway]]\n#   to = 100\n#   entrance = 0\n'
                    '#   zone = [[-1100,-2400],[1100,-2400],[1100,-1750],[-1100,-1750]]\n')
    return (
        f"# {p.field_name} — exported from Blender by FF9 Map Kit. Compile with:\n"
        f"#   ff9mapkit build {p.field_name.lower()}.field.toml\n"
        f"# Painted PNGs + content markers (NPC/gateway/spawn) came from your Blender scene.\n\n"
        f"[field]\n"
        f"id = {p.field_id}\n"
        f'name = "{p.field_name}"\n'
        f"area = {p.area}\n"
        f"text_block = {p.text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"   # the exact camera you posed in Blender\n'
        + ("[camera.scroll]\nenabled = true   # larger-than-screen painting; the view scrolls\n"
           if p.scroll_enabled else "")
        + f"[camera.frame]\n"
        f"back = {p.back_y:g}\n"
        f"front = {p.front_y:g}\n\n"
        f"[walkmesh]\n"
        f'obj = "walkmesh.obj"\n'
        f"# slide the walkmesh toward the camera so the 3D character looks planted on the 2D floor\n"
        f"character_offset = {cam.CHARACTER_GROUND_OFFSET_Z:g}\n\n"
        f"{layers_block}\n"
        f"{player_block}\n"
        f"{npc_block}\n"
        f"{gw_block}"
    )


def _field_toml_borrow(p, npcs=(), gateways=(), spawn=None):
    """field.toml for a BG-borrow fork (imported real field): no scene/walkmesh/layers — the engine
    renders the real field's; we add a custom script + content markers."""
    player_block = (bridge.player_to_toml(spawn) + "\n") if spawn is not None else "[player]\nspawn = [0, 0]\n"
    npc_block = (bridge.npcs_to_toml(npcs) + "\n") if npcs else (
        '# [[npc]]\n#   name = "Someone"\n#   preset = "vivi"\n#   pos = [0, 0]\n#   dialogue = "Hello."\n')
    gw_block = (bridge.gateways_to_toml(gateways) + "\n") if gateways else (
        '# [[gateway]]\n#   to = 100\n#   entrance = 204\n#   zone = [[-200,200],[200,200],[200,400],[-200,400]]\n')
    scroll = "[camera.scroll]\nenabled = true\n" if p.scroll_enabled else ""
    return (
        f"# {p.field_name} — forked from real field {p.borrow_bg} (BG-borrow) via FF9 Map Kit.\n"
        f"# Renders that field's art + walkmesh + camera; your markers add the content. Compile:\n"
        f"#   ff9mapkit build {p.field_name.lower()}.field.toml\n\n"
        f"[field]\n"
        f"id = {p.field_id}\n"
        f'name = "{p.field_name}"\n'
        f"area = {p.area}\n"
        f'borrow_bg = "{p.borrow_bg}"\n'
        f"text_block = {p.text_block}\n\n"
        f"[camera]\n"
        f'borrow = "camera.bgx"\n'
        f"{scroll}\n"
        f"{player_block}\n{npc_block}\n{gw_block}"
    )


CLASSES = (FF9MKLayer, FF9MKProps, FF9MK_OT_setup_scene, FF9MK_OT_pose_camera,
           FF9MK_OT_walkmesh_from_floor, FF9MK_OT_compute_guide, FF9MK_OT_paint_template,
           FF9MK_OT_add_layer, FF9MK_OT_clear_layers,
           FF9MK_OT_add_npc, FF9MK_OT_add_gateway, FF9MK_OT_set_spawn,
           FF9MK_OT_import_field, FF9MK_OT_export_field)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ff9mapkit = bpy.props.PointerProperty(type=FF9MKProps)


def unregister():
    del bpy.types.Scene.ff9mapkit
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
