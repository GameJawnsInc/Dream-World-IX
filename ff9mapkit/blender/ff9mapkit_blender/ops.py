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
SEAMS_NAME = "FF9_Seams"
RANGE_WH = (384, 448)
SCREEN_W = 384          # the visible field width; a scrolling painting is wider and the FOV is
                        # always measured at this width (a wide Range must not change the focal length)


def _range_wh(p):
    """The painted-canvas size: the full painting for a scrolling field, else one 384x448 screen."""
    return (int(p.canvas_w), int(p.canvas_h)) if p.scroll_enabled else RANGE_WH

# content markers (Phase 2): tagged Blender objects -> [[npc]]/[[gateway]]/[[event]]/[player] on export.
MARKER_KEY = "ff9_marker"            # obj[MARKER_KEY] in {"npc","gateway","event","camzone","spawn","waypoint"}
GATEWAY_HALF_W = 700.0               # default gateway quad half-extents (FF9 ~= Blender units)
GATEWAY_HALF_D = 250.0
CAM_KEY = "ff9_cam"                  # obj[CAM_KEY] = camera index (0 = default at load) for a multi-cam field


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
    """One painted background layer: a PNG + its depth Z (smaller Z = in front). ``shader`` is the
    overlay blend mode (empty = opaque; e.g. "PSX/FieldMap_Abr_1" for an imported light/glow layer)."""
    image: bpy.props.StringProperty(name="Image", subtype="FILE_PATH")
    z: bpy.props.IntProperty(name="Depth Z", default=4000, update=_layer_z_update)
    shader: bpy.props.StringProperty(name="Shader", default="")
    camera: bpy.props.IntProperty(name="Camera", default=0, min=0,
                                  description="Which camera shows this layer in a multi-camera field "
                                              "(0 = the only/default camera)")
    # A tight per-tile-depth sub-layer (editable fork) carries its own position+size; a full-canvas
    # painted layer leaves size (0,0) so build defaults to [0,0] + the camera range. Preserved so a
    # fork's per-tile occlusion survives import -> export.
    position: bpy.props.IntVectorProperty(name="Position", size=2, default=(0, 0))
    size: bpy.props.IntVectorProperty(name="Size", size=2, default=(0, 0))


class FF9MKProps(bpy.types.PropertyGroup):
    field_id: bpy.props.IntProperty(name="Field ID", default=4003, min=4000)
    field_name: bpy.props.StringProperty(name="Name", default="MY_ROOM")
    area: bpy.props.IntProperty(name="Area", default=11, min=10)
    text_block: bpy.props.IntProperty(name="Text Block", default=1073)
    # set by "Import FF9 Field": the REAL field's mapid. When non-empty the field is BG-borrow
    # (engine renders that field's art/walkmesh/camera) and Export emits a borrow field.toml.
    borrow_bg: bpy.props.StringProperty(name="Borrow BG", default="")
    # set by "Import FF9 Field" for an EDITABLE (--editable) fork: a full custom scene over a real
    # field (real camera + per-depth art + world-frame walkmesh). Export preserves the exact camera +
    # ships obj+links+frame=world (no character offset) so a reshape stays connected. False = a
    # from-scratch novel room (re-posable camera, flat walkmesh + character_offset).
    editable_fork: bpy.props.BoolProperty(name="Editable Fork", default=False)
    pitch: bpy.props.FloatProperty(name="Pitch", default=48.0, min=0.0, max=89.0)
    distance: bpy.props.FloatProperty(name="Distance", default=4500.0, min=1.0)
    fov: bpy.props.FloatProperty(name="FOV", default=42.2, min=1.0, max=170.0)
    yaw: bpy.props.FloatProperty(name="Yaw", default=0.0, min=-180.0, max=180.0,
                                 description="Rotation about vertical (0 = head-on). Vary it per camera "
                                             "in a multi-camera field")
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
    # --- battle map (3D BBG geometry) ---
    bbg_name: bpy.props.StringProperty(name="BBG", default="",
                                       description="The battle-background slot (e.g. BBG_B209)")
    bbg_dir: bpy.props.StringProperty(
        name="Battle Map Dir", subtype="DIR_PATH", default="",
        description="Folder the BBG fbx + image#.png textures live in / export to (set on import)")


GUIDE_COLLECTION = "FF9 Guide"
BATTLE_COLLECTION = "FF9 Battle Map"
BBG_GROUP_KEY = "ff9_bbg_group"          # obj[...] = "Group_0/2/4/8" (tags an imported BBG group mesh)
BBG_TEX_KEY = "ff9_bbg_tex"              # material[...] = its texture stem (image#), for re-export


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
                                yaw_deg=p.yaw, range_wh=(rw, rh),
                                viewport=tuple(cam.scroll_bounds((rw, rh))))
        # sensor = the FULL painting width so the Blender viewport shows the backdrop + walkmesh at
        # the SAME scale as in-game (to_canvas). Using the 384 window here made the camera FOV too
        # narrow (~42 vs ~75 deg), so the backdrop looked ~1.8x too big and walkmeshes got modelled
        # ~1.8x too small. proj is still the window focal, so the EXPORTED camera is unchanged.
        b = bridge.ff9_cam_to_blender(ff9, sensor_width=float(rw))
    else:
        ff9 = guide.make_camera(p.pitch, p.distance, fov_x_deg=p.fov, yaw_deg=p.yaw, range_wh=(rw, rh))
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


def _import_content(context, field_cfg, scene_cfg):
    """Re-create placed content as Blender markers on import (round-trip): NPC / waypoint / gateway /
    event from the merged field.toml (logic) + scene.toml (positions). Positions are FF9 floor coords
    mapped back to Blender. Skips a named entity already present (same kind+name) so a re-import doesn't
    duplicate. Returns a {kind: count} tally."""
    def loc(x, z):
        return bridge.ff9_verts_to_blender([(float(x), 0.0, float(z))])[0]
    existing = {(o.get(MARKER_KEY), o.get("ff9_name")) for o in context.scene.objects if o.get(MARKER_KEY)}
    made = {}

    def add_empty(kind, name, x, z, props):
        e = bpy.data.objects.new("FF9_NPC" if kind == "npc" else "FF9_Waypoint", None)
        e.empty_display_type = "ARROWS" if kind == "npc" else "SPHERE"
        e.empty_display_size = 200.0 if kind == "npc" else 120.0
        e.location = loc(x, z)
        e[MARKER_KEY] = kind
        e["ff9_name"] = name
        for k, v in props.items():
            if v is not None:
                e[k] = v
        _link_active(context, e)

    def add_zone(kind, name, zone, props, color=None):
        mesh = bpy.data.meshes.new("FF9_Gateway" if kind == "gateway" else "FF9_Event")
        mesh.from_pydata([list(loc(x, z)) for (x, z) in zone[:4]], [], [(0, 1, 2, 3)])
        mesh.update()
        obj = bpy.data.objects.new(mesh.name, mesh)
        obj.display_type = "WIRE"
        obj.show_in_front = True
        if color:
            obj.color = color
        obj[MARKER_KEY] = kind
        if name is not None:
            obj["ff9_name"] = name
        for k, v in props.items():
            if v is not None:
                obj[k] = v
        _link_active(context, obj)

    for n in bridge.merge_import_entities(field_cfg, scene_cfg, "npc"):
        nm = n.get("name") or "NPC"
        if n.get("pos") and ("npc", nm) not in existing:
            # marker = spatial only (model + position); dialogue stays in the field.toml logic file
            add_empty("npc", nm, n["pos"][0], n["pos"][1], {"ff9_preset": n.get("preset")})
            made["npc"] = made.get("npc", 0) + 1
    for m in bridge.merge_import_entities(field_cfg, scene_cfg, "marker"):
        nm = m.get("name") or "waypoint"
        if m.get("pos") and ("waypoint", nm) not in existing:
            add_empty("waypoint", nm, m["pos"][0], m["pos"][1], {})
            made["marker"] = made.get("marker", 0) + 1
    for g in bridge.merge_import_entities(field_cfg, scene_cfg, "gateway"):
        nm = g.get("name")
        if g.get("zone") and not (nm and ("gateway", nm) in existing):
            add_zone("gateway", nm, g["zone"],
                     {"ff9_to": int(g.get("to", 100)), "ff9_entrance": int(g.get("entrance", 0))})
            made["gateway"] = made.get("gateway", 0) + 1
    for ev in bridge.merge_import_entities(field_cfg, scene_cfg, "event"):
        nm = ev.get("name") or "event"
        if ev.get("zone") and ("event", nm) not in existing:
            sf = ev.get("set_flag")
            sf_idx = int(sf[0]) if isinstance(sf, (list, tuple)) else (int(sf) if sf is not None else -1)
            add_zone("event", nm, ev["zone"],
                     {"ff9_message": ev.get("message"), "ff9_set_flag": sf_idx,
                      "ff9_once": 1 if ev.get("once", True) else 0}, color=(1.0, 0.85, 0.1, 1.0))
            made["event"] = made.get("event", 0) + 1
    return made


def _apply_canvas_resolution(context, rw, rh):
    """Match the render resolution to the FF9 canvas so the camera frames the field at the right
    aspect. FF9 fields are 384x448 portrait (wider when scrolling); Blender defaults to 1920x1080
    landscape, which makes the matched camera look too wide / off-centre in the viewport."""
    r = context.scene.render
    r.resolution_x = int(rw)
    r.resolution_y = int(rh)
    r.resolution_percentage = 100


_FLOOR_PALETTE = [(0.90, 0.30, 0.30), (0.30, 0.65, 0.95), (0.40, 0.85, 0.40), (0.95, 0.80, 0.25),
                  (0.85, 0.45, 0.90), (0.45, 0.82, 0.85), (0.95, 0.55, 0.30), (0.60, 0.60, 0.95),
                  (0.80, 0.80, 0.45), (0.55, 0.85, 0.66), (0.95, 0.40, 0.60), (0.50, 0.75, 0.40)]


def _color_mesh_by_floor(mesh, floor_ids):
    """Give each FF9 walkmesh floor a distinct material colour so multi-floor fields are legible
    (a 7-floor coplanar tangle like GRGR reads as colour-separated regions, not one stack)."""
    nf = (max(floor_ids) + 1) if floor_ids else 1
    mesh.materials.clear()
    for fi in range(nf):
        r, g, b = _FLOOR_PALETTE[fi % len(_FLOOR_PALETTE)]
        mat = bpy.data.materials.new(f"FF9_Floor_{fi:02d}")
        mat.diffuse_color = (r, g, b, 1.0)        # shows in Solid view (Color = Material)
        mesh.materials.append(mat)
    for i, poly in enumerate(mesh.polygons):
        poly.material_index = floor_ids[i] if i < len(floor_ids) else 0


def _build_seam_overlay(context, bgi_bytes):
    """(Re)build a bright wireframe overlay (FF9_Seams) of the cross-floor SEAM edges -- the edges you
    must NOT move when reshaping a multi-floor fork (they re-attach the floors by world position on
    build). Removes a stale overlay; creates nothing for a single-floor field. Returns the seam count."""
    sverts, sedges = bridge.seam_edges_blender(bgi_bytes)
    obj = bpy.data.objects.get(SEAMS_NAME)
    if not sedges:                                      # single floor / no seams -> remove any stale one
        if obj is not None:
            old = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if old and old.users == 0:
                bpy.data.meshes.remove(old)
        return 0
    mesh = bpy.data.meshes.new(SEAMS_NAME)
    mesh.from_pydata([list(v) for v in sverts], [tuple(e) for e in sedges], [])
    mesh.update()
    if obj is None:
        obj = bpy.data.objects.new(SEAMS_NAME, mesh)
        context.scene.collection.objects.link(obj)
    else:
        old = obj.data
        obj.data = mesh
        if old and old.users == 0:
            bpy.data.meshes.remove(old)
    obj.display_type = "WIRE"
    obj.show_in_front = True            # always visible, floating on the walkmesh
    obj.hide_select = True              # reference only -- don't grab it while reshaping
    obj.color = (1.0, 0.85, 0.1, 1.0)   # amber
    return len(sedges)


def _show_material_colors(context):
    """Set 3D viewports to Solid + Material colour so the per-floor colours are visible."""
    for area in context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.color_type = "MATERIAL"


def _camera_obj_to_ff9(context, cam_obj):
    """Any Blender camera OBJECT as an FF9 cam.Cam (used per-camera for a multi-camera export)."""
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


def active_camera_to_ff9(context):
    """The scene's active camera as an FF9 cam.Cam (None if there is no camera)."""
    cam_obj = context.scene.camera
    if cam_obj is None or cam_obj.type != "CAMERA":
        return None
    return _camera_obj_to_ff9(context, cam_obj)


def selected_or_scene_camera_ff9(context):
    """The SELECTED camera as an FF9 cam.Cam (so the panel readout follows the camera you're editing in
    a multi-camera field), else the scene's active camera. None if there's no camera."""
    cam_obj = context.active_object
    if cam_obj is None or cam_obj.type != "CAMERA":
        cam_obj = context.scene.camera
    if cam_obj is None or cam_obj.type != "CAMERA":
        return None
    return _camera_obj_to_ff9(context, cam_obj)


def _read_camera_into_props(context, cam_obj):
    """Load a camera object's pitch/distance/FOV/yaw into the panel props (the inverse of _pose_camera),
    so you can read a camera's current values, tweak, and re-Pose it. Scroll/canvas are field-level and
    left as-is (multi-camera fields aren't scrolling)."""
    p = context.scene.ff9mapkit
    c = _camera_obj_to_ff9(context, cam_obj)
    dec = cam.decompose(c)
    p.pitch = round(cam.pitch_deg(c), 2)
    p.yaw = round(cam.yaw_deg(c), 2)
    if dec.get("fov_x_deg"):
        p.fov = round(dec["fov_x_deg"], 2)
    C = dec["C"]
    p.distance = round((C[0] ** 2 + C[1] ** 2 + C[2] ** 2) ** 0.5, 1)


def _collect_cameras(context):
    """All FF9 camera objects, sorted by their ``ff9_cam`` index (0 = default at load). The main
    FF9_Camera counts as index 0 even if untagged (single-camera fields). Returns a list of objects."""
    cams = []
    for o in context.scene.objects:
        if o.type != "CAMERA":
            continue
        if CAM_KEY in o:
            cams.append((int(o[CAM_KEY]), o))
        elif o.name == CAMERA_NAME:
            cams.append((0, o))
    cams.sort(key=lambda t: t[0])
    return [o for _, o in cams]


def _walkmesh_world_mesh(obj):
    """(world_verts, tri_faces, floor_ids) for a mesh object, triangulated.

    ``floor_ids`` is each triangle's material slot index (the per-floor colouring set on import, so a
    re-exported multi-floor field keeps its floors); a single/zero-material mesh yields all-0 = one
    floor. Flushes live Edit-Mode edits first: Blender doesn't push edit-mode changes to ``obj.data``
    until you leave Edit Mode, so exporting mid-edit would otherwise capture the STALE mesh.
    """
    if obj.mode == "EDIT":
        obj.update_from_editmode()
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    verts = [list(mw @ v.co) for v in mesh.vertices]
    faces = [tuple(lt.vertices) for lt in mesh.loop_triangles]
    floor_ids = [int(lt.material_index) for lt in mesh.loop_triangles]
    return verts, faces, floor_ids


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
        p.borrow_bg = ""               # a fresh scene is a from-scratch novel room, not a fork
        p.editable_fork = False
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
        # pose the SELECTED camera if one is selected (so you can edit camera 1, 2, ... independently);
        # else the scene's active camera. Setting scene.camera makes the viewport look through it.
        cam_obj = context.active_object
        if cam_obj is None or cam_obj.type != "CAMERA":
            cam_obj = context.scene.camera
        if cam_obj is None or cam_obj.type != "CAMERA":
            self.report({"ERROR"}, "Select a camera (or run Setup FF9 Scene first).")
            return {"CANCELLED"}
        p = context.scene.ff9mapkit
        context.scene.camera = cam_obj
        _pose_camera(cam_obj, p)
        _apply_canvas_resolution(context, *_range_wh(p))
        self.report({"INFO"}, f"posed {cam_obj.name} (pitch {p.pitch:g}, yaw {p.yaw:g})")
        return {"FINISHED"}


class FF9MK_OT_read_camera(bpy.types.Operator):
    bl_idname = "ff9mk.read_camera"
    bl_label = "Read Camera"
    bl_description = ("Load the SELECTED camera's Pitch / Distance / FOV / Yaw into the panel above "
                      "(so switching between cameras shows that camera's values; then tweak + Pose)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cam_obj = context.active_object
        if cam_obj is None or cam_obj.type != "CAMERA":
            cam_obj = context.scene.camera
        if cam_obj is None or cam_obj.type != "CAMERA":
            self.report({"ERROR"}, "Select a camera first.")
            return {"CANCELLED"}
        _read_camera_into_props(context, cam_obj)
        context.scene.camera = cam_obj                          # view through it
        p = context.scene.ff9mapkit
        self.report({"INFO"}, f"read {cam_obj.name}: pitch {p.pitch:g}, yaw {p.yaw:g}, fov {p.fov:g}")
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
            verts, _, _ = _walkmesh_world_mesh(p.walkmesh)
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


def _rasterize_paint_template(t, scale=4):
    """Rasterize a bridge.paint_template_lines() dict into a transparent float-RGBA buffer in bpy
    image order (rows bottom-up). Mirrors the CLI render_paint_template exactly: faint perspective
    grid, bright floor outline (back edge thicker), the canvas safe-frame border, then the COLORED
    vertical height guides (poles/rings/ceiling box) on top. Returns (buf, W, H)."""
    import array
    W, H = t["size"]
    S = scale
    buf = array.array("f", bytes(W * H * 4 * 4))              # all 0.0 -> transparent

    def line(p0, p1, rgba, thick=1):                          # square-brush, overwrite (matches placeholder.draw_line)
        x0, y0 = p0; x1, y1 = p1
        dx, dy = x1 - x0, y1 - y0
        n = int(max(abs(dx), abs(dy)))
        half = max(0, thick - 1)
        for i in range(n + 1):
            tt = i / n if n else 0.0
            cx = int(round(x0 + dx * tt)); cy = int(round(y0 + dy * tt))
            for oy in range(-half, half + 1):
                yy = cy + oy
                if not (0 <= yy < H):
                    continue
                row = (H - 1 - yy) * W                         # bpy image rows are bottom-up
                for ox in range(-half, half + 1):
                    xx = cx + ox
                    if 0 <= xx < W:
                        o = (row + xx) * 4
                        buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = rgba

    for a, b in t["grid"]:                                    # faint perspective grid
        line(a, b, (0.82, 0.84, 0.90, 0.35))
    outline = t["outline"]
    for a, b in outline:                                      # bright floor outline
        line(a, b, (1.0, 0.667, 0.235, 1.0), 2 * S)
    if outline:                                               # back edge highlighted (thicker)
        line(outline[0][0], outline[0][1], (1.0, 0.667, 0.235, 1.0), 3 * S)
    for a, b in t.get("border", []):                          # canvas safe-frame
        line(a, b, (0.471, 0.784, 1.0, 0.784), 2)
    for seg in t.get("height", []):                           # COLORED poles / rings / ceiling box
        a, b, rgba = seg
        line(a, b, tuple(ch / 255.0 for ch in rgba), max(1, S // 2))
    return buf, W, H


class FF9MK_OT_paint_template(bpy.types.Operator):
    bl_idname = "ff9mk.paint_template"
    bl_label = "Export Paint Template"
    bl_description = ("Write a transparent trace-over paint template (floor outline + perspective grid "
                      "+ vertical height guides, 4x scale, full canvas) for each camera; paint your room "
                      "on layers UNDER it")

    def execute(self, context):
        p = context.scene.ff9mapkit
        cam_objs = _collect_cameras(context)
        if not cam_objs and context.scene.camera and context.scene.camera.type == "CAMERA":
            cam_objs = [context.scene.camera]                 # untagged single camera
        if not cam_objs:
            self.report({"ERROR"}, "No camera (run Setup FF9 Scene first).")
            return {"CANCELLED"}
        multi = len(cam_objs) > 1                              # multi-cam: one template per camera
        out = _resolve_out_dir(p.export_dir)
        try:
            os.makedirs(out, exist_ok=True)
        except OSError as e:
            self.report({"ERROR"}, f"can't write template: {e.strerror}. Save the .blend or set 'Export to'.")
            return {"CANCELLED"}
        written, errors = [], []
        for cam_obj in cam_objs:
            idx = int(cam_obj[CAM_KEY]) if CAM_KEY in cam_obj else 0
            c = _camera_obj_to_ff9(context, cam_obj)
            try:
                t = bridge.paint_template_lines(c, p.back_y, p.front_y, scale=4)
            except ValueError as e:
                errors.append(f"cam{idx}: {e}")
                continue
            buf, W, H = _rasterize_paint_template(t, scale=4)
            name = f"FF9_PaintTemplate_cam{idx:02d}" if multi else "FF9_PaintTemplate"
            fn = f"paint_template_cam{idx:02d}.png" if multi else "paint_template.png"
            old = bpy.data.images.get(name)
            if old:
                bpy.data.images.remove(old)
            img = bpy.data.images.new(name, W, H, alpha=True)
            img.pixels.foreach_set(buf)
            path = os.path.join(out, fn)
            try:
                img.filepath_raw = path
                img.file_format = "PNG"
                img.save()
            except OSError as e:
                errors.append(f"cam{idx}: {e.strerror}")
                continue
            written.append((idx, W, H, path))
        if not written:
            self.report({"ERROR"}, "no template written: " + "; ".join(errors))
            return {"CANCELLED"}
        if multi:
            msg = (f"{len(written)} paint templates (one per camera) -> {out}; "
                   "paint each camera's room on layers UNDER its template")
        else:
            _idx, W, H, path = written[0]
            msg = f"paint template ({W}x{H}) -> {path}; paint your room on layers UNDER it"
        if errors:
            msg += f" (skipped {len(errors)}: {'; '.join(errors)})"
        self.report({"INFO"}, msg)
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
    if obj.name not in context.collection.objects:       # idempotent: don't double-link an already-linked obj
        context.collection.objects.link(obj)
    for o in context.selected_objects:
        o.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj


def _zone_corners(obj):
    """The first 4 vertices of a zone mesh (gateway/event quad) as FF9 (x, z) floor coords, or None."""
    mw = obj.matrix_world
    verts = [list(mw @ v.co) for v in obj.data.vertices[:4]]
    if len(verts) < 4:
        return None
    return [bridge.marker_floor_pos(v) for v in verts]


def _collect_markers(context):
    """Read tagged marker objects into (npcs, gateways, spawn, events), in FF9 floor coords.

    Deterministic: NPCs/gateways/events are sorted by object name. ``spawn`` is the last FF9_Spawn
    found (there should be one), or None. Marker world coords map straight to the FF9 raw frame
    (the engine's frame), so they export as-is -- no offset."""
    npcs, gateways, events, spawn = [], [], [], None
    for obj in sorted(context.scene.objects, key=lambda o: o.name):
        mk = obj.get(MARKER_KEY)
        if not mk:
            continue
        if mk == "spawn":
            spawn = bridge.marker_floor_pos(obj.matrix_world.translation)
        elif mk == "npc":
            # spatial only: name + model + position. Dialogue/logic is authored in the field.toml
            # (the logic side), joined to this marker by name -- the Blender add-on never carries it.
            n = {"pos": bridge.marker_floor_pos(obj.matrix_world.translation)}
            if obj.get("ff9_name"):
                n["name"] = obj["ff9_name"]
            if obj.get("ff9_preset"):
                n["preset"] = obj["ff9_preset"]
            npcs.append(n)
        elif mk == "gateway" and obj.type == "MESH":
            zone = _zone_corners(obj)
            if zone is None:
                continue
            gateways.append({"to": int(obj.get("ff9_to", 100)),
                             "entrance": int(obj.get("ff9_entrance", 0)), "zone": zone})
        elif mk == "event" and obj.type == "MESH":
            zone = _zone_corners(obj)
            if zone is None:
                continue
            ev = {"zone": zone, "once": bool(int(obj.get("ff9_once", 1)))}
            if obj.get("ff9_name"):
                ev["name"] = obj["ff9_name"]
            if obj.get("ff9_message"):
                ev["message"] = obj["ff9_message"]
            sf = int(obj.get("ff9_set_flag", -1))
            if sf >= 0:
                ev["set_flag"] = [sf, 1]
            events.append(ev)
    return npcs, gateways, spawn, events


def _collect_camzones(context):
    """Camera-switch zone markers -> [{to_camera, zone}], sorted by name. The floor area where each
    camera is active; crossing in cuts the view to ``to_camera``."""
    zones = []
    for obj in sorted(context.scene.objects, key=lambda o: o.name):
        if obj.get(MARKER_KEY) == "camzone" and obj.type == "MESH":
            zone = _zone_corners(obj)
            if zone is not None:
                zones.append({"to_camera": int(obj.get("ff9_to_camera", 1)), "zone": zone})
    return zones


def _collect_waypoints(context):
    """Named movement markers -> [{name, pos}], sorted by name. A cutscene's walk/path references these
    by name (placed visually instead of typing coords): walk = "<ff9_name>"."""
    out = []
    for obj in sorted(context.scene.objects, key=lambda o: o.name):
        if obj.get(MARKER_KEY) == "waypoint":
            m = {"pos": bridge.marker_floor_pos(obj.matrix_world.translation)}
            if obj.get("ff9_name"):
                m["name"] = obj["ff9_name"]
            out.append(m)
    return out


class FF9MK_OT_add_npc(bpy.types.Operator):
    bl_idname = "ff9mk.add_npc"
    bl_label = "Add NPC"
    bl_description = ("Drop an NPC marker (Empty) at the 3D cursor on the floor. Pick its model with "
                      "ff9_preset in Object Properties > Custom Properties; its dialogue/logic is "
                      "authored in the field.toml (the logic side), joined to this marker by name")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        e = bpy.data.objects.new("FF9_NPC", None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 200.0
        e.location = _cursor_floor(context)
        e[MARKER_KEY] = "npc"
        e["ff9_name"] = "NPC"
        e["ff9_preset"] = "vivi"
        _link_active(context, e)
        self.report({"INFO"}, f"added NPC '{e.name}' — set its model (ff9_preset) in Custom Properties; "
                              "author its dialogue/logic in the field.toml (joined by name)")
        return {"FINISHED"}


class FF9MK_OT_add_waypoint(bpy.types.Operator):
    bl_idname = "ff9mk.add_waypoint"
    bl_label = "Add Waypoint"
    bl_description = ("Drop a named movement marker (Empty) at the 3D cursor on the floor. A cutscene "
                      "references it by name: walk = \"<ff9_name>\". Set ff9_name in Custom Properties")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        e = bpy.data.objects.new("FF9_Waypoint", None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = 120.0
        e.location = _cursor_floor(context)
        e[MARKER_KEY] = "waypoint"
        e["ff9_name"] = "waypoint"
        _link_active(context, e)
        self.report({"INFO"}, f"added waypoint '{e.name}' — set ff9_name, then walk = \"<name>\" in a cutscene")
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


class FF9MK_OT_add_event(bpy.types.Operator):
    bl_idname = "ff9mk.add_event"
    bl_label = "Add Event"
    bl_description = ("Drop a walk-in trigger zone at the 3D cursor on the floor. Move/scale it over "
                      "the trigger spot; set its message / set_flag (story flag) / once in Custom "
                      "Properties or the form editor. Use for chests, levers, story triggers")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cx, cy, _ = _cursor_floor(context)
        hw, hd = GATEWAY_HALF_W, GATEWAY_HALF_D
        corners = [(cx - hw, cy - hd, 0.0), (cx + hw, cy - hd, 0.0),
                   (cx + hw, cy + hd, 0.0), (cx - hw, cy + hd, 0.0)]
        mesh = bpy.data.meshes.new("FF9_Event")
        mesh.from_pydata([list(c) for c in corners], [], [(0, 1, 2, 3)])
        mesh.update()
        obj = bpy.data.objects.new("FF9_Event", mesh)
        obj.display_type = "WIRE"
        obj.show_in_front = True
        obj.color = (1.0, 0.85, 0.1, 1.0)            # amber, to read apart from gateways
        obj[MARKER_KEY] = "event"
        obj["ff9_name"] = "event"
        obj["ff9_message"] = "..."                   # a line shown on trigger (a real action => builds)
        obj["ff9_set_flag"] = -1                     # -1 = set no story flag; >=0 = set that flag
        obj["ff9_once"] = 1                           # 1 = fire once ever; 0 = every entry
        _link_active(context, obj)
        self.report({"INFO"}, f"added event '{obj.name}' — set ff9_message / ff9_set_flag / ff9_once "
                              f"in Custom Properties (or the form editor)")
        return {"FINISHED"}


class FF9MK_OT_add_camera(bpy.types.Operator):
    bl_idname = "ff9mk.add_camera"
    bl_label = "Add Camera"
    bl_description = ("Add another FF9 camera (a multi-camera field cuts between cameras as you walk "
                      "across Cam Zones). Poses it from the Pitch/Distance/FOV/Yaw above + makes it "
                      "active; adjust + Pose, give it its own background layer + a Cam Zone")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        p = context.scene.ff9mapkit
        main = bpy.data.objects.get(CAMERA_NAME)
        if main is not None and CAM_KEY not in main:
            main[CAM_KEY] = 0                                   # tag the original as camera 0
        idx = len(_collect_cameras(context))                   # next index
        cam_data = bpy.data.cameras.new(f"FF9_Camera_{idx}")
        obj = bpy.data.objects.new(f"FF9_Camera_{idx}", cam_data)
        obj[CAM_KEY] = idx
        _link_active(context, obj)                              # links + selects + makes active
        context.scene.camera = obj                              # view + pose this camera
        _pose_camera(obj, p)
        _apply_canvas_resolution(context, *_range_wh(p))
        self.report({"INFO"}, f"added camera {idx} (now active) — set Yaw/Pitch + Pose, add its "
                              f"background layer (camera={idx}) + a Cam Zone")
        return {"FINISHED"}


class FF9MK_OT_add_camzone(bpy.types.Operator):
    bl_idname = "ff9mk.add_camzone"
    bl_label = "Add Cam Zone"
    bl_description = ("Drop a camera-switch zone on the floor: walking into it cuts the view to its "
                      "target camera. Set ff9_to_camera. Zones must NOT overlap. (Needs 2+ cameras.)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cx, cy, _ = _cursor_floor(context)
        hw, hd = GATEWAY_HALF_W, GATEWAY_HALF_D
        corners = [(cx - hw, cy - hd, 0.0), (cx + hw, cy - hd, 0.0),
                   (cx + hw, cy + hd, 0.0), (cx - hw, cy + hd, 0.0)]
        mesh = bpy.data.meshes.new("FF9_CamZone")
        mesh.from_pydata([list(c) for c in corners], [], [(0, 1, 2, 3)])
        mesh.update()
        obj = bpy.data.objects.new("FF9_CamZone", mesh)
        obj.display_type = "WIRE"
        obj.show_in_front = True
        obj.color = (0.5, 0.6, 1.0, 1.0)             # blue, to read apart from gateways/events
        obj[MARKER_KEY] = "camzone"
        obj["ff9_to_camera"] = 1
        _link_active(context, obj)
        self.report({"INFO"}, f"added cam zone '{obj.name}' — set ff9_to_camera (which camera to "
                              f"switch to); place it over that camera's area, no overlaps")
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
        # a sibling <name>.scene.toml (a Blender-authored project) holds the entity POSITIONS; merge it
        # so a re-imported project round-trips. A CLI `ff9mapkit import` has none (positions are inline).
        scene_cfg = {}
        scene_path = (tomls[0][:-len(".field.toml")] + ".scene.toml" if tomls[0].endswith(".field.toml")
                      else os.path.splitext(tomls[0])[0] + ".scene.toml")
        if os.path.isfile(scene_path):
            with open(scene_path, "rb") as fh:
                scene_cfg = tomllib.load(fh)
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
        cam_obj["ff9_rw"], cam_obj["ff9_rh"] = int(c0.range[0]), int(c0.range[1])
        _apply_canvas_resolution(context, c0.range[0], c0.range[1])
        context.scene.camera = cam_obj

        # Multi-camera fields: a real field can split its walkable area across SEVERAL cameras (the
        # engine switches between them via SETCAM). The import historically posed only camera 0, so a
        # field whose floor lives on camera 1+ rendered with the walkmesh off-frame (e.g. CYSW: cam0
        # frames 0% of the main floor, cam1 frames 100%). Drop EVERY camera as its own Blender camera
        # object so you can switch the active view camera (select it -> View > Cameras > Set Active
        # Object as Camera, or Ctrl+Numpad0) and see the walkmesh framed by each real camera. cam0
        # stays the scene's active camera. The extras are tagged with their ff9_cam index so the panel
        # readout follows the selected one; an imported fork preserves the EXACT extracted camera.bgx on
        # export (borrow / editable branches), so these view-only objects never alter the shipped field.
        extra_cams = []                          # (obj, Cam) for cams[1:]; view-offset applied below
        for stale in [o for o in context.scene.objects
                      if o.type == "CAMERA" and o.name.startswith(CAMERA_NAME + "_")]:
            sd = stale.data                      # clear extras from a previous higher-camera-count import
            bpy.data.objects.remove(stale, do_unlink=True)
            if sd and sd.users == 0:
                bpy.data.cameras.remove(sd)
        for i, ci in enumerate(cams[1:], start=1):
            nm = f"{CAMERA_NAME}_{i:02d}"
            co = bpy.data.objects.new(nm, bpy.data.cameras.new(nm))
            context.scene.collection.objects.link(co)
            co[CAM_KEY] = i
            co["ff9_rw"], co["ff9_rh"] = int(ci.range[0]), int(ci.range[1])
            _pose_camera_from_ff9(co, ci, ci.range[0] > 384 or ci.range[1] > 448)
            extra_cams.append((co, ci))

        # EDITABLE (--editable) fork = a custom scene with no borrow_bg. Load its per-depth art
        # ([[layers]]) as the camera backdrop + the field's layer list (with shaders) so you model
        # against the real room AND re-export keeps the occlusion + light/shadow blends intact.
        p.editable_fork = not bool(p.borrow_bg)
        p.layers.clear()
        try:
            cam_obj.data.background_images.clear()
        except AttributeError:
            while len(cam_obj.data.background_images):
                cam_obj.data.background_images.remove(cam_obj.data.background_images[0])
        cfg_layers = cfg.get("layers", [])
        # Tight per-tile-depth sub-layers (an editable fork's occlusion split) each cover only a few
        # tiles, so FIT-stretching them as full-screen backdrops would garble the preview. For a tight
        # fork we model against the single composited background.png (loaded below) and keep the
        # sub-layers in p.layers purely so Export round-trips the per-tile occlusion (position+size).
        tight = any(Lc.get("size") for Lc in cfg_layers)
        for Lc in sorted(cfg_layers, key=lambda L: -int(L.get("z", 0))):   # back (hi z) first
            img_path = os.path.join(d, Lc.get("image", ""))
            if not os.path.isfile(img_path):
                continue
            if not tight:                                 # a full-canvas layer is usable as a FIT backdrop
                img = bpy.data.images.load(img_path, check_existing=True)
                cam_obj.data.show_background_images = True
                bg = cam_obj.data.background_images.new()
                bg.image = img
                bg.frame_method = "FIT"
                bg.alpha = 1.0
                bg.display_depth = "FRONT" if int(Lc.get("z", 4000)) < 1000 else "BACK"
            La = p.layers.add()
            La.image = img_path
            La.z = int(Lc.get("z", 4000))
            La.shader = Lc.get("shader", "") or ""
            pos, size = Lc.get("position"), Lc.get("size")
            if size:                                      # tight sub-layer -> preserve its placement
                La.position = (int((pos or (0, 0))[0]), int((pos or (0, 0))[1]))
                La.size = (int(size[0]), int(size[1]))

        # real walkmesh -> editable mesh (reference for placing markers; borrow ships the real one).
        # Real .bgi verts are corner-origin PER FLOOR; the world transform (vert+orgPos+floor.org) lands
        # the whole multi-floor mesh on the painted art as a coherent whole. That world frame IS the
        # engine's frame, so content placed on the mesh exports correctly with no undo. The mesh may
        # still extend past the screen edges (tunnels) -- correct, not a misalignment.
        with open(bgi_path, "rb") as fh:
            bgi_bytes = fh.read()
        has_art = bool(p.layers) or os.path.isfile(os.path.join(d, "background.png"))
        verts, faces = bridge.bgi_walkmesh_to_blender(bgi_bytes, world=True)
        wm_obj = bpy.data.objects.get(WALKMESH_NAME)
        if wm_obj is None:
            wm_obj = bpy.data.objects.new(WALKMESH_NAME, bpy.data.meshes.new(WALKMESH_NAME))
            context.scene.collection.objects.link(wm_obj)
        old = wm_obj.data
        mesh = bpy.data.meshes.new(WALKMESH_NAME)
        # Keep the REAL world height (don't flatten): the floor sits at its actual world Y (e.g. GRGR
        # at -2135), which the matched camera + the view-offset fit both assume. A few tall features
        # (ladders) read as vertical strips -- that's the real 3D walkmesh, and it's correct.
        mesh.from_pydata([[v[0], v[1], v[2]] for v in verts], [], [list(f) for f in faces])
        mesh.update()
        _color_mesh_by_floor(mesh, bridge.walkmesh_floor_ids(bgi_bytes))   # legible multi-floor fields
        wm_obj.data = mesh
        if old and old.users == 0:
            bpy.data.meshes.remove(old)
        _show_material_colors(context)
        p.walkmesh = wm_obj

        # highlight the cross-floor SEAM edges (FF9_Seams) so you don't move them when reshaping a
        # multi-floor fork -- they re-attach the floors by world position on build.
        n_seams = _build_seam_overlay(context, bgi_bytes) if p.editable_fork else 0

        # Per-camera VIEW nudge: Blender's pinhole != FF9's exact 2D-BG projection (cam.to_canvas),
        # so the imported walkmesh lands a few px off the painted art -- worst for head-on cameras
        # (GLGV needs ~+42 height). Offset the CAMERA by -D (moving the object by +D == moving the
        # camera by -D), which aligns the view while leaving the walkmesh + content in the raw engine
        # frame, so content still exports correctly (the tilted-camera D has a depth term that would
        # corrupt content if applied to the mesh). Only when there's art to align to.
        if has_art:
            D = bridge.walkmesh_view_offset(bgi_bytes, c0)
            cam_obj.location.x -= D[0]
            cam_obj.location.y -= D[1]
            cam_obj.location.z -= D[2]
            for co, ci in extra_cams:            # each camera gets its OWN nudge (different pose/pitch)
                Di = bridge.walkmesh_view_offset(bgi_bytes, ci)
                co.location.x -= Di[0]
                co.location.y -= Di[1]
                co.location.z -= Di[2]

        # Reframe (viewport-only) ONLY the bare no-art case: centre the camera on the walkmesh so the
        # footprint is readable. With an art backdrop, the view-offset above aligns it; keep the
        # extracted camera otherwise.
        if verts and not has_art:
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

        spawn = (scene_cfg.get("player") or cfg.get("player") or {}).get("spawn")
        if spawn and len(spawn) == 2:
            _spawn_at_ff9(context, spawn)
        # round-trip the placed content: NPCs / waypoints / gateways / events as markers (positions from
        # the scene.toml if present, else the field.toml's inline pos/zone -- e.g. a forked field's exits).
        content = _import_content(context, cfg, scene_cfg)
        p.export_dir = d                       # re-export here, preserving the exact camera.bgx

        # real-art backdrop: the single composited background.png `ff9mapkit import` writes. Loads it as
        # the camera's BACK background so you model against the actual room. Used for a tight editable
        # fork (whose per-tile sub-layers don't FIT-stretch) and for the older single-flattened path;
        # skipped only when full-canvas [[layers]] were already added as FIT backdrops above.
        bg_path = os.path.join(d, "background.png")
        if (tight or not p.layers) and os.path.isfile(bg_path):
            img = bpy.data.images.load(bg_path, check_existing=True)
            cam_obj.data.show_background_images = True
            bg = cam_obj.data.background_images.new()
            bg.image = img
            bg.frame_method = "FIT"
            bg.alpha = 1.0
            bg.display_depth = "BACK"

        # MULTI-camera fields ship a clean per-camera backdrop (background_cam01.png ..). Attach each to
        # its camera object, so switching the active camera shows THAT camera's painted art behind its
        # own walkmesh region (cam0 keeps background.png above). Skipped silently for single-camera /
        # not-re-exported projects (no per-camera file). For the backdrop + walkmesh to align you must
        # view through the camera at ITS resolution -- use "View Camera" (ff9mk.view_ff9_camera).
        for co, _ci in extra_cams:
            cbg = os.path.join(d, f"background_cam{int(co[CAM_KEY]):02d}.png")
            if not os.path.isfile(cbg):
                continue
            cim = bpy.data.images.load(cbg, check_existing=True)
            co.data.show_background_images = True
            cbgi = co.data.background_images.new()
            cbgi.image = cim
            cbgi.frame_method = "FIT"
            cbgi.alpha = 1.0
            cbgi.display_depth = "BACK"

        seam_note = (f" {n_seams} cross-floor seam(s) highlighted (FF9_Seams) -- don't move those edges."
                     if n_seams else "")
        loaded = ("  " + ", ".join(f"{v} {k}" for k, v in content.items()) + " loaded.") if content else ""
        cam_note = (f" {len(cams)} cameras dropped (FF9_Camera + _01..); select one + View > Cameras > "
                    f"Set Active Object as Camera to frame the floor by it." if len(cams) > 1 else "")
        self.report({"INFO"}, f"imported {p.borrow_bg or p.field_name}: camera + walkmesh loaded."
                              f"{cam_note}{seam_note}{loaded} Add/edit markers, then Export Field.")
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
            npcs, gateways, spawn, events = _collect_markers(context)
            scene_body = '[camera]\nborrow = "camera.bgx"\n'
            if p.scroll_enabled:
                scene_body += "[camera.scroll]\nenabled = true\n"
            stub = _write_split_files(out, p, scene_body, npcs, gateways, spawn,
                                      borrow_bg=p.borrow_bg, events=events,
                                      markers=_collect_waypoints(context))
            self.report({"INFO"}, f"BG-borrow fork of {p.borrow_bg}: scene.toml written"
                                  f"{', field.toml stub created' if stub else ' (your field.toml kept)'}"
                                  f"; run: ff9mapkit build {p.field_name.lower()}.field.toml")
            return {"FINISHED"}

        if p.editable_fork:
            # EDITABLE fork (imported real field as a custom scene): preserve the EXACT extracted
            # camera (don't re-pose — the view-offset nudge applied on import would corrupt it) +
            # the per-depth art; ship a WORLD-frame walkmesh (obj + seam sidecar if multi-floor) so
            # a reshape stays connected, with NO character offset (real-field frame).
            cbgx = os.path.join(out, "camera.bgx")
            if not os.path.isfile(cbgx):
                with open(cbgx, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(bgx.build(c, [], header_comment=f"{p.field_name} camera (forked)"))
            verts, faces, floor_ids = _walkmesh_world_mesh(p.walkmesh)
            with open(os.path.join(out, "walkmesh.obj"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(bridge.mesh_to_ff9_obj(verts, faces, floor_ids))
            has_links = os.path.isfile(os.path.join(out, "walkmesh.links.toml"))
            layers = []
            for L in p.layers:
                src = bpy.path.abspath(L.image)
                if not src or not os.path.isfile(src):
                    self.report({"WARNING"}, f"layer image missing, skipped: {L.image}")
                    continue
                dst = os.path.join(out, os.path.basename(src))
                if os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copyfile(src, dst)
                Ld = {"image": os.path.basename(src), "z": int(L.z), "shader": L.shader or None}
                if tuple(L.size) != (0, 0):              # tight per-tile-depth sub-layer: keep placement
                    Ld["position"] = [int(L.position[0]), int(L.position[1])]
                    Ld["size"] = [int(L.size[0]), int(L.size[1])]
                layers.append(Ld)
            npcs, gateways, spawn, events = _collect_markers(context)
            scene_body = '[camera]\nborrow = "camera.bgx"\n'
            if p.scroll_enabled:
                scene_body += "[camera.scroll]\nenabled = true\n"
            scene_body += '\n[walkmesh]\nobj = "walkmesh.obj"\n'
            if has_links:
                scene_body += 'links = "walkmesh.links.toml"\n'
            scene_body += 'frame = "world"\n'
            if layers:
                scene_body += "\n" + bridge.layers_to_toml(layers) + "\n"
            stub = _write_split_files(out, p, scene_body, npcs, gateways, spawn, events=events,
                                  markers=_collect_waypoints(context))
            self.report({"INFO"}, f"editable fork {p.field_name}: scene.toml ({len(layers)} layer(s), "
                                  f"{'multi-floor' if has_links else 'single-floor'})"
                                  f"{', field.toml stub created' if stub else ' (your field.toml kept)'}"
                                  f"; run: ff9mapkit build {p.field_name.lower()}.field.toml")
            return {"FINISHED"}

        # cameras: SINGLE -> [camera] borrow camera.bgx; MULTI -> [[camera]] borrow cameraK.bgx each
        # (each camera is written exact; the build resolves the array to N cameras, index 0 = default).
        cam_objs = _collect_cameras(context)
        multicam = len(cam_objs) > 1
        if multicam:
            cam_files = []
            for k, cobj in enumerate(cam_objs):
                ck = _camera_obj_to_ff9(context, cobj)
                fn = f"camera{k}.bgx"
                with open(os.path.join(out, fn), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(bgx.build(ck, [], header_comment=f"{p.field_name} camera {k}"))
                cam_files.append(fn)
            cam_body = bridge.cameras_borrow_toml(cam_files) + "\n"
        else:
            with open(os.path.join(out, "camera.bgx"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(bgx.build(c, [], header_comment=f"{p.field_name} camera (ff9mapkit blender)"))
            cam_body = ('[camera]\nborrow = "camera.bgx"\n'
                        + ("[camera.scroll]\nenabled = true\n" if p.scroll_enabled else "")
                        + f"[camera.frame]\nback = {p.back_y:g}\nfront = {p.front_y:g}\n")
        # walkmesh.obj (FF9 coords; one `o floor_N` group per material slot => multi-floor)
        verts, faces, floor_ids = _walkmesh_world_mesh(p.walkmesh)
        with open(os.path.join(out, "walkmesh.obj"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(bridge.mesh_to_ff9_obj(verts, faces, floor_ids))
        # painted layers: copy each PNG next to the toml + collect (basename, z [, camera])
        layers = []
        for L in p.layers:
            src = bpy.path.abspath(L.image)
            if not src or not os.path.isfile(src):
                self.report({"WARNING"}, f"layer image missing, skipped: {L.image}")
                continue
            dst = os.path.join(out, os.path.basename(src))
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copyfile(src, dst)
            ld = {"image": os.path.basename(src), "z": int(L.z)}
            if multicam:
                ld["camera"] = int(L.camera)           # which camera's background this layer is
            layers.append(ld)
        # content markers -> scene (positions) + field.toml logic stub
        npcs, gateways, spawn, events = _collect_markers(context)
        camzones = _collect_camzones(context) if multicam else []
        scene_body = cam_body + '\n[walkmesh]\nobj = "walkmesh.obj"\nframe = "world"\n'
        if layers:
            scene_body += "\n" + bridge.layers_to_toml(layers) + "\n"
        if camzones:
            scene_body += "\n" + bridge.camera_zones_to_toml(camzones) + "\n"
        stub = _write_split_files(out, p, scene_body, npcs, gateways, spawn, events=events,
                                  markers=_collect_waypoints(context))
        cz = f", {len(camzones)} cam-zone(s)" if multicam else ""
        self.report({"INFO"}, f"exported {p.field_name}: {len(cam_objs)} camera(s), {len(layers)} layer(s), "
                              f"{len(npcs)} NPC(s), {len(gateways)} gateway(s), {len(events)} event(s){cz}"
                              f"{', field.toml stub created' if stub else ' (your field.toml kept)'}"
                              f"; run: ff9mapkit build {p.field_name.lower()}.field.toml")
        return {"FINISHED"}


def _write_split_files(out, p, scene_body, npcs, gateways, spawn, *, borrow_bg=None, events=(), markers=()):
    """Two-file export: write ``<name>.scene.toml`` (spatial; ALWAYS overwritten) + ``<name>.field.toml``
    (logic stub; created ONLY if it doesn't already exist, so the user's script is never clobbered).
    ``scene_body`` is the path-specific ``[camera]``/``[walkmesh]``/``[[layers]]`` text. Event zones go
    in the scene; their actions go in the field stub (joined by name). Named movement ``markers`` are
    spatial-only -> scene.toml. Returns True if a fresh field.toml stub was written (False = kept)."""
    base = p.field_name.lower()
    with open(os.path.join(out, f"{base}.scene.toml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(bridge.scene_toml(p.field_name, scene_body, npcs, gateways, spawn, events=events,
                                   markers=markers))
    field_path = os.path.join(out, f"{base}.field.toml")
    if os.path.isfile(field_path):
        return False
    meta = {"field_id": p.field_id, "field_name": p.field_name, "area": p.area,
            "text_block": p.text_block, "borrow_bg": borrow_bg}
    with open(field_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(bridge.field_logic_stub(meta, npcs, gateways, events))
    return True


# --------------------------------------------------------------------------- battle map (3D BBG)
def _battle_collection(context):
    """Get (or create) the 'FF9 Battle Map' collection that holds the imported Group_* meshes."""
    coll = bpy.data.collections.get(BATTLE_COLLECTION)
    if coll is None:
        coll = bpy.data.collections.new(BATTLE_COLLECTION)
        context.scene.collection.children.link(coll)
    return coll


def _load_bbg_image(d, stem):
    """Load <stem>.png/.tga next to the fbx, for the material preview (None if absent)."""
    if not stem:
        return None
    for ext in (".png", ".tga", ".jpg"):
        p = os.path.join(d, stem + ext)
        if os.path.isfile(p):
            return bpy.data.images.load(p, check_existing=True)
    return None


def _bbg_material(name, tex, img):
    """A node material previewing the texture; tags the texture stem for faithful re-export."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat[BBG_TEX_KEY] = tex or ""
    if img is not None:
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        bsdf = nt.nodes.get("Principled BSDF")
        if bsdf:
            nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def _bbg_object_to_group(obj):
    """A tagged Blender BBG mesh object -> a battle/fbx `group` (Unity space). Reads world verts +
    per-vertex UVs (from the active UV layer) + per-vertex world normals; submeshes = material slots,
    each slot's texture from its BBG_TEX_KEY tag (set on import)."""
    if obj.mode == "EDIT":
        obj.update_from_editmode()
    mesh = obj.data
    mesh.calc_loop_triangles()
    mw = obj.matrix_world
    nm = mw.to_3x3()
    bverts = [list(mw @ v.co) for v in mesh.vertices]
    normals = [list((nm @ v.normal).normalized()) for v in mesh.vertices]
    uvs = [[0.0, 0.0] for _ in mesh.vertices]
    uvl = mesh.uv_layers.active
    # guard: in Edit Mode the object-mode UV data can read as empty (size 0) while loops exist -> only
    # read when the layer's data actually matches the loops (Export forces Object Mode first to flush).
    if uvl and len(uvl.data) == len(mesh.loops):
        d = uvl.data
        for loop in mesh.loops:                       # per-vertex (consistent unless UVs were split)
            uvs[loop.vertex_index] = [float(d[loop.index].uv[0]), float(d[loop.index].uv[1])]
    faces = [tuple(lt.vertices) for lt in mesh.loop_triangles]
    face_material = [int(lt.material_index) for lt in mesh.loop_triangles]
    mats = [(m.get(BBG_TEX_KEY) or (m.name if m else None)) if m else None for m in mesh.materials]
    name = obj.get(BBG_GROUP_KEY) or "Group_0"
    return bridge.blender_meshdata_to_group(name, bverts, faces, face_material, mats or [None], uvs,
                                            normals=normals)


def _battle_toml_stub(bbg):
    return (f"# {bbg} battle map (FF9 Map Kit Blender export).\n"
            f"#   ff9mapkit battle-build battle.toml   then   py tools/deploy_battle.py battle.toml\n\n"
            f"[battlemap]\n"
            f'bbg = "{bbg}"\n'
            f'fbx = "{bbg}.fbx"\n'
            f"# bbg = an EXISTING real slot OVERRIDES that map (no relaunch). For a NEW scene, set\n"
            f"# scene_id + scene_name and fork its gameplay with `battle-import --fork-scene <DONOR>`.\n")


class FF9MK_OT_import_battle(bpy.types.Operator):
    bl_idname = "ff9mk.import_battle"
    bl_label = "Import Battle Map"
    bl_description = ("Load a battle map's geometry (a BBG_B###.fbx from `ff9mapkit battle-import`, or "
                      "its battle.toml) as editable Group_0/2/4/8 meshes with their textures. Reshape "
                      "them, then Export Battle Map.")
    bl_options = {"REGISTER", "UNDO"}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    filter_glob: bpy.props.StringProperty(default="*.fbx;*.toml", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import tomllib
        from .vendor import battle_fbx
        path = self.filepath
        if not path or not os.path.isfile(path):
            self.report({"ERROR"}, "Pick a BBG_B###.fbx (or its battle.toml).")
            return {"CANCELLED"}
        d = os.path.dirname(path)
        if path.lower().endswith(".toml"):
            with open(path, "rb") as fh:
                bm = (tomllib.load(fh).get("battlemap") or {})
            bbg = bm.get("bbg")
            fbx_path = os.path.join(d, bm.get("fbx") or (str(bbg) + ".fbx"))
        else:
            fbx_path = path
            bbg = os.path.splitext(os.path.basename(path))[0]
        if not os.path.isfile(fbx_path):
            self.report({"ERROR"}, f"FBX not found: {fbx_path}")
            return {"CANCELLED"}
        with open(fbx_path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        try:
            groups = battle_fbx.parse_fbx(text)
        except Exception as e:          # noqa: BLE001 - report, don't crash Blender
            self.report({"ERROR"}, f"couldn't parse the FBX (is it a kit-built BBG?): {e}")
            return {"CANCELLED"}
        if not groups:
            self.report({"ERROR"}, "no Group_* geometry in the FBX.")
            return {"CANCELLED"}

        coll = _battle_collection(context)
        for o in list(coll.objects):                 # clear a prior import
            if o.get(BBG_GROUP_KEY) is not None:
                bpy.data.objects.remove(o, do_unlink=True)
        ntri = 0
        for g in groups:
            md = bridge.group_to_blender_meshdata(g)
            mesh = bpy.data.meshes.new(md["name"])
            mesh.from_pydata([list(v) for v in md["verts"]], [], [list(f) for f in md["faces"]])
            mesh.update()
            if md["uvs"] and mesh.loops:
                uvl = mesh.uv_layers.new(name="UVMap")
                for loop in mesh.loops:
                    vi = loop.vertex_index
                    if vi < len(md["uvs"]):
                        uvl.data[loop.index].uv = (md["uvs"][vi][0], md["uvs"][vi][1])
            for tex in md["materials"]:
                mesh.materials.append(_bbg_material(f'{md["name"]}_{tex or "mat"}', tex,
                                                    _load_bbg_image(d, tex)))
            for fi, fm in enumerate(md["face_material"]):
                if fi < len(mesh.polygons):
                    mesh.polygons[fi].material_index = fm
            mesh.update()
            obj = bpy.data.objects.new(f'BBG_{md["name"]}', mesh)
            obj[BBG_GROUP_KEY] = md["name"]
            coll.objects.link(obj)
            ntri += len(md["faces"])

        p = context.scene.ff9mapkit
        p.bbg_name = str(bbg or "")
        p.bbg_dir = d
        self.report({"INFO"}, f"imported {bbg}: {len(groups)} group(s), {ntri} tri(s) + textures. "
                              f"Reshape (keep Group_0/2/4/8 separate), then Export Battle Map.")
        return {"FINISHED"}


class FF9MK_OT_export_battle(bpy.types.Operator):
    bl_idname = "ff9mk.export_battle"
    bl_label = "Export Battle Map"
    bl_description = ("Write an engine-faithful BBG_B###.fbx (Group_0/2/4/8 + PSX shaders) from the "
                      "imported/reshaped meshes, for `ff9mapkit battle-build`.")

    def execute(self, context):
        from .vendor import battle_fbx
        p = context.scene.ff9mapkit
        objs = [o for o in context.scene.objects if o.type == "MESH" and o.get(BBG_GROUP_KEY) is not None]
        if not objs:
            self.report({"ERROR"}, "No battle-map groups (run Import Battle Map first).")
            return {"CANCELLED"}
        if context.mode != "OBJECT":                  # flush any live Edit-Mode edits (verts AND uv data)
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except RuntimeError:
                pass
        out = _resolve_out_dir(p.bbg_dir or p.export_dir)
        try:
            os.makedirs(out, exist_ok=True)
        except OSError as e:
            self.report({"ERROR"}, f"can't write to {out}: {e.strerror}.")
            return {"CANCELLED"}
        groups = [_bbg_object_to_group(o) for o in objs]
        problems = battle_fbx.validate_groups(groups)
        if problems:
            self.report({"ERROR"}, "geometry problems: " + "; ".join(problems[:3]))
            return {"CANCELLED"}
        text, ngeo = battle_fbx.emit_fbx(groups)
        bbg = p.bbg_name or "BBG_B200"
        with open(os.path.join(out, f"{bbg}.fbx"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        # ensure the referenced textures sit next to the fbx (copy from the import dir if exporting elsewhere)
        textures = battle_fbx.textures_used(groups)
        copied = 0
        for tex in textures:
            dst = os.path.join(out, tex + ".png")
            if not os.path.isfile(dst) and p.bbg_dir:
                cand = os.path.join(p.bbg_dir, tex + ".png")
                if os.path.isfile(cand) and os.path.abspath(cand) != os.path.abspath(dst):
                    shutil.copyfile(cand, dst)
                    copied += 1
        wrote = False
        toml_path = os.path.join(out, "battle.toml")
        if not os.path.isfile(toml_path):
            with open(toml_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(_battle_toml_stub(bbg))
            wrote = True
        missing = [t for t in textures if not os.path.isfile(os.path.join(out, t + ".png"))]
        warn = f" ({len(missing)} texture(s) missing — copy them next to the fbx)" if missing else ""
        self.report({"INFO"}, f"exported {bbg}: {ngeo} geometry, {len(textures)} texture(s)"
                              f"{', battle.toml stub' if wrote else ' (battle.toml kept)'}{warn}"
                              f"; run: ff9mapkit battle-build battle.toml")
        return {"FINISHED"}


class FF9MK_OT_view_ff9_camera(bpy.types.Operator):
    bl_idname = "ff9mk.view_ff9_camera"
    bl_label = "View Camera"
    bl_description = ("Make the SELECTED FF9 camera active, match the render resolution to its FF9 range "
                      "so its walkmesh + per-camera backdrop align, and look through it. Use this to "
                      "inspect each camera of a MULTI-camera field -- one global resolution can't frame "
                      "cameras of different aspect at once, so switch with this between FF9_Camera/_01/_02")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        cam_obj = context.active_object
        if cam_obj is None or cam_obj.type != "CAMERA":
            cam_obj = next((o for o in context.selected_objects if o.type == "CAMERA"), None)
        if cam_obj is None or cam_obj.type != "CAMERA" or "ff9_rw" not in cam_obj:
            self.report({"ERROR"}, "Select an FF9 camera (FF9_Camera or FF9_Camera_01..) first.")
            return {"CANCELLED"}
        context.scene.camera = cam_obj
        context.scene.render.resolution_x = int(cam_obj["ff9_rw"])
        context.scene.render.resolution_y = int(cam_obj["ff9_rh"])
        for area in context.screen.areas:                      # look through it in every 3D viewport
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.region_3d.view_perspective = "CAMERA"
        self.report({"INFO"}, f"viewing {cam_obj.name} @ {int(cam_obj['ff9_rw'])}x{int(cam_obj['ff9_rh'])}")
        return {"FINISHED"}


CLASSES = (FF9MKLayer, FF9MKProps, FF9MK_OT_setup_scene, FF9MK_OT_pose_camera, FF9MK_OT_read_camera,
           FF9MK_OT_walkmesh_from_floor, FF9MK_OT_compute_guide, FF9MK_OT_paint_template,
           FF9MK_OT_add_layer, FF9MK_OT_clear_layers,
           FF9MK_OT_add_npc, FF9MK_OT_add_waypoint, FF9MK_OT_add_gateway, FF9MK_OT_add_event,
           FF9MK_OT_add_camera, FF9MK_OT_add_camzone, FF9MK_OT_set_spawn, FF9MK_OT_view_ff9_camera,
           FF9MK_OT_import_field, FF9MK_OT_export_field,
           FF9MK_OT_import_battle, FF9MK_OT_export_battle)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ff9mapkit = bpy.props.PointerProperty(type=FF9MKProps)


def unregister():
    del bpy.types.Scene.ff9mapkit
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
