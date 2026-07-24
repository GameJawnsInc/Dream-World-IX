"""Build the owner's ready-to-open Bahamut .blend (M2 deliverable, "a Bahamut they can open in Blender").

Takes the textured ``summon-export`` output (``ef227_bahamut.glb`` -- rig + rigid skin + 6 decoded texture
pages + all 8 baked motion clips, TRANSPLANT.md rung W3) and turns it into ONE self-contained ``.blend``:
friendly object/armature names, all 8 clips renamed + fake-user-protected + stashed as NLA tracks (a
browsable library), the long flight clip (clip6, 82 frames -- the frame-count table validated in
``m0/EULER.md`` section 3: ``[24,30,26,48,40,68,82,28]`` for clip0..clip7) left as the ACTIVE action so
opening the file and hitting spacebar plays something good immediately, packed textures, and a camera framed
on the whole creature with the viewport already looking through it.

Then renders the proof set (rest + flight-mid + a 4-angle turntable) so the result can be eyeballed without
opening Blender interactively.

Provenance: this SCRIPT is committable code. Its INPUT (``ef227_bahamut.glb``) and OUTPUT (``bahamut.blend``,
the renders) are stock-derived Square-Enix content and must stay under ``C:/gd/SCRATCH/summon-transplant/``
-- never committed, never copied into a mod folder. This script does not itself enforce that (unlike
``summons/export.py``'s ``assert_local_only``) because it is a one-shot authoring tool the caller invokes
with an explicit SCRATCH path, not a library API; don't point ``--out`` anywhere else.

Run (Blender 5.1 headless):
    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python make_bahamut_blend.py --
        <ef227_bahamut.glb> <out.blend> <out_renders_dir>

All three positional args are optional -- they default to the standard SCRATCH layout (see DEFAULTS below),
so a bare invocation with no args after ``--`` regenerates the shipped file.

Regen the source .glb first if you want a fresh decode:
    py -m ff9mapkit summon-export C:/gd/SCRATCH/summon-format/ef227.bytes \
        --out C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb --rest identity --anims all
"""
import math
import os
import re
import sys

import bpy
import mathutils
import numpy as np

# --------------------------------------------------------------------------- args + defaults
DEFAULTS = (
    "C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb",
    "C:/gd/SCRATCH/summon-transplant/bahamut.blend",
    "C:/gd/SCRATCH/summon-transplant/renders",
)
_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
IN_GLB = _argv[0] if len(_argv) > 0 else DEFAULTS[0]
OUT_BLEND = _argv[1] if len(_argv) > 1 else DEFAULTS[1]
OUT_RENDERS = _argv[2] if len(_argv) > 2 else DEFAULTS[2]
os.makedirs(OUT_RENDERS, exist_ok=True)
os.makedirs(os.path.dirname(OUT_BLEND) or ".", exist_ok=True)

FPS = 15.0  # the native tick (build.DEFAULT_FPS) -- not a measured PSX rate, but the preview convention
# EULER.md section 3's validated frame-count table, file order clip0..clip7 -- the ONLY pinned narrative
# roles are clip0 (first-loop) and clip6 (the dominant/longest flight clip); the rest are labelled by their
# own frame count only (no invented role beyond what the study actually pinned).
CLIP_TAG = {0: "first", 6: "flight"}

print(f"[bahamut-blend] in={IN_GLB}\n  out_blend={OUT_BLEND}\n  out_renders={OUT_RENDERS}")

# --------------------------------------------------------------------------- import
bpy.ops.wm.read_factory_settings(use_empty=True)
# Set the scene's fps to the export's own tick (15) BEFORE importing: the glTF importer bakes each sampler's
# TIME values (seconds -- fixed at export as keyframe_index/15, build.DEFAULT_FPS) onto Blender FRAME numbers
# using whatever the scene's fps is AT IMPORT TIME. Import at the default 24fps and a clip's frame_range would
# stretch to keyframe_count*24/15 frames (e.g. clip6's true 82 keys -> 131) while covering the SAME real
# duration -- so changing fps afterwards would silently change playback speed instead of just relabeling it.
# Setting it first makes 1 Blender frame == 1 native tick, so frame_range matches the true keyframe counts
# ([24,30,26,48,40,68,82,28], EULER.md section 3) and playback speed is correct with no rescale needed.
bpy.context.scene.render.fps = int(FPS)
bpy.context.scene.render.fps_base = 1.0
bpy.ops.import_scene.gltf(filepath=IN_GLB)

objs = list(bpy.data.objects)
armatures = [o for o in objs if o.type == "ARMATURE"]
if len(armatures) != 1:
    raise RuntimeError(f"expected exactly 1 armature, found {len(armatures)}: {[a.name for a in armatures]}")

# Blender's glTF importer auto-generates an "Icosphere" bone-custom-shape widget mesh alongside the real skin
# (the same stray m1b/offline_eye.py strips via clear_shapes_and_icos) -- it carries no Armature modifier and
# no skin weights, so filter the real parts by "has an Armature modifier", not just "is a MESH".
all_meshes = [o for o in objs if o.type == "MESH"]
meshes = [o for o in all_meshes if any(mod.type == "ARMATURE" for mod in o.modifiers)]
stray = [o for o in objs if o.type not in ("ARMATURE",) and o not in meshes]
if not meshes:
    raise RuntimeError("no skinned mesh objects came in with the glTF import (none carry an Armature modifier)")
for pb in armatures[0].pose.bones:
    pb.custom_shape = None  # drop widget refs before the widget objects are removed, else Blender warns
for o in stray:
    print(f"[bahamut-blend] removing stray object (no Armature modifier -- a bone-shape widget, not skin): "
          f"{o.name} ({o.type})")
    bpy.data.objects.remove(o, do_unlink=True)

rig = armatures[0]
print(f"[bahamut-blend] armature '{rig.name}': {len(rig.data.bones)} bones")
print(f"[bahamut-blend] {len(meshes)} mesh part object(s): {[m.name for m in meshes]}")

# --------------------------------------------------------------------------- join the mesh parts -> 'Bahamut'
bpy.ops.object.select_all(action="DESELECT")
for m in meshes:
    m.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
body.name = "Bahamut"
body.data.name = "Bahamut"
rig.name = "Bahamut_rig"
rig.data.name = "Bahamut_rig"
print(f"[bahamut-blend] joined -> '{body.name}' ({len(body.data.vertices)} verts, "
      f"{len(body.data.materials)} material slot(s))")

# sanity: the mesh must still carry exactly one Armature modifier pointed at the (renamed) rig
arm_mods = [mod for mod in body.modifiers if mod.type == "ARMATURE"]
if not arm_mods:
    raise RuntimeError("joined mesh lost its Armature modifier -- the skin is not bound")
for mod in arm_mods:
    mod.object = rig

# --------------------------------------------------------------------------- clips: rename in place (reuse
# the importer's own NLA structure, don't duplicate it)
# The glTF importer ALREADY, for multiple animations targeting one armature: creates all 8 Actions, pushes
# EACH to its own muted NLA track (name == the clip label, one strip == the whole clip at frame 1..N), and
# leaves the first one (clip0) as the arbitrary active action. That is already exactly the "browsable
# library + one immediate default" shape this file wants -- so rename the existing tracks/strips/actions in
# place rather than building a second, duplicate set of tracks alongside them.
if rig.animation_data is None:
    rig.animation_data_create()

CLIP_RE = re.compile(r"^clip(\d+)$")
clip_actions = {}  # idx -> (action, frames)
for track in list(rig.animation_data.nla_tracks):
    mobj = CLIP_RE.match(track.name)
    if not mobj or len(track.strips) != 1:
        print(f"[bahamut-blend] ! unexpected NLA track (leaving as-is): {track.name!r} "
              f"({len(track.strips)} strip(s))")
        continue
    idx = int(mobj.group(1))
    strip = track.strips[0]
    act = strip.action
    if act is None:
        print(f"[bahamut-blend] ! track {track.name!r}'s strip carries no action")
        continue
    fr = act.frame_range
    frames = int(round(fr[1] - fr[0])) + 1
    tag = CLIP_TAG.get(idx)
    new_name = f"clip{idx}" + (f"_{tag}" if tag else "") + f"_{frames}f"
    act.name = new_name
    act.use_fake_user = True  # belt-and-suspenders: survive save/reload even if a strip is later deleted
    track.name = new_name
    strip.name = new_name
    track.mute = True  # every clip's own track stays muted -- a browsable, non-conflicting library
    clip_actions[idx] = (act, frames)

expected = set(range(8))
missing = expected - set(clip_actions)
if missing:
    print(f"[bahamut-blend] ! missing clip indices (creature exported with --anims != 'all'?): {sorted(missing)}")
print("[bahamut-blend] clips: " + ", ".join(f"{i}={clip_actions[i][0].name}" for i in sorted(clip_actions)))


def _bind_slot(anim_data_owner, action):
    """Blender 5.x layered/slotted actions: (re)assigning ``.action`` to a DIFFERENT action can leave the
    slot unresolved. Bind the first (only) slot explicitly -- the same defensive pattern
    m1b/offline_eye.py uses."""
    try:
        slots = list(action.slots)
        if slots:
            anim_data_owner.action_slot = slots[0]
    except Exception as e:  # pragma: no cover -- Blender-version dependent API
        print(f"  slot-bind warn ({action.name}): {e}")


# --------------------------------------------------------------------------- slot normalization
# Blender 4.4+ actions are SLOTTED: the curves live in a channelbag keyed by an ActionSlot, and picking an
# action in the Action Editor only animates anything if a slot gets bound to the ID. Blender auto-picks that
# slot on assignment (measured on 5.1: it resolves via adt.last_slot_identifier, then an identifier matching
# the ID's name, then a lone unused slot) -- so ONE clearly-named armature slot per action is the shape where
# plain "pick the action" always works. The glTF importer already produces exactly that here (1 slot, 375
# fcurves), but the slot is named after the object's IMPORT-TIME name ("Armature"), which goes stale the
# moment this script renames the rig -- and if a future importer ever emits stray extra slots, the auto-pick
# gets ambiguous. So: verify one-armature-slot-per-action, rename it to the rig, and refuse to guess if the
# shape is ever different (never silently drop curve data).
def _slot_fcurves(action, slot):
    n = 0
    for layer in action.layers:
        for strip in layer.strips:
            cb = strip.channelbag(slot)
            if cb:
                n += len(cb.fcurves)
    return n


def normalize_slots(action, owner):
    """Reduce ``action`` to exactly one slot targeting ``owner`` and name it after ``owner``.

    Returns the kept slot (or None). Empty stray slots are pruned; a stray that actually CARRIES curves is
    only reported -- deleting real animation data to tidy a name is never the right trade.
    """
    slots = list(action.slots)
    if not slots:
        print(f"  ! {action.name}: no slots -- the Action Editor cannot bind this action to anything")
        return None
    counts = {s.identifier: _slot_fcurves(action, s) for s in slots}
    keep = max(slots, key=lambda s: (getattr(s, "target_id_type", "") == "OBJECT", counts[s.identifier]))
    for s in slots:
        if s is keep:
            continue
        if counts[s.identifier]:
            print(f"  ! {action.name}: extra slot {s.identifier!r} carries {counts[s.identifier]} fcurve(s) "
                  f"-- KEEPING it (ambiguous slot auto-pick; inspect this clip by hand)")
            continue
        try:
            action.slots.remove(s)
            print(f"  {action.name}: pruned empty stray slot {s.identifier!r}")
        except Exception as e:  # pragma: no cover -- Blender-version dependent API
            print(f"  {action.name}: could not prune stray slot {s.identifier!r}: {e}")
    try:
        keep.name_display = owner.name  # identifier becomes 'OB' + owner.name for OBJECT-targeted slots
    except Exception as e:  # pragma: no cover
        print(f"  {action.name}: slot rename warn: {e}")
    return keep


print("[bahamut-blend] normalizing action slots (one armature slot per clip, named for the rig):")
for _i in sorted(clip_actions):
    _act = clip_actions[_i][0]
    _slot = normalize_slots(_act, rig)
    print(f"  {_act.name:22s} slot={_slot.identifier if _slot else None!r} "
          f"({_slot_fcurves(_act, _slot) if _slot else 0} fcurves)")

# the long flight clip (clip6) as the ACTIVE action -- open the file, hit spacebar, the dragon flies
flight_act, flight_frames = clip_actions[6]
rig.animation_data.action = flight_act
_bind_slot(rig.animation_data, flight_act)
print(f"[bahamut-blend] active action = {flight_act.name} ({flight_frames} frames)")

# --------------------------------------------------------------------------- scene: fps + frame range
scene = bpy.context.scene
scene.render.fps = int(FPS)
scene.render.fps_base = 1.0
scene.frame_start = 1
scene.frame_end = flight_frames
scene.frame_current = 1

# --------------------------------------------------------------------------- lighting + camera + render engine
world = bpy.data.worlds.new("BahamutWorld")
bpy.context.scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs[0].default_value = (0.09, 0.10, 0.13, 1.0)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 3.6
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(52), 0, math.radians(28))
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", type="SUN"))
fill.data.energy = 1.3
bpy.context.collection.objects.link(fill)
fill.rotation_euler = (math.radians(120), 0, math.radians(-55))

cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x = 960
scene.render.resolution_y = 720
scene.render.film_transparent = False
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def evaluated_extent(obj):
    """World-space bbox (min, max) of the DEFORMED mesh (armature modifier applied) at the current pose."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    pts = np.array([tuple(mw @ v.co) for v in me.vertices]) if len(me.vertices) else np.zeros((1, 3))
    ev.to_mesh_clear()
    return pts.min(0), pts.max(0)


def frame_camera(center, radius, azimuth_deg=200.0, elevation_ratio=0.5):
    d = radius * 2.15
    az = math.radians(azimuth_deg)
    cam.location = mathutils.Vector(center) + mathutils.Vector(
        (d * math.cos(az), d * math.sin(az), radius * elevation_ratio))
    look_at(cam, mathutils.Vector(center))
    cam_data.lens = 40


def render_pose(label, azimuth_deg=200.0):
    cmin, cmax = evaluated_extent(body)
    center = (cmin + cmax) / 2
    radius = float(np.linalg.norm(cmax - cmin)) * 0.5 or 1.0
    frame_camera(center, radius, azimuth_deg=azimuth_deg)
    scene.render.filepath = os.path.join(OUT_RENDERS, label + ".png")
    bpy.ops.render.render(write_still=True)
    print(f"[bahamut-blend] rendered {label}.png (extent={(cmax - cmin).round(2)}, cam-az={azimuth_deg:.0f})")
    return cmax - cmin


# --------------------------------------------------------------------------- proof renders
# 1) rest pose (no action driving the armature -- the pure bind pose) + a 4-angle turntable
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis = mathutils.Matrix.Identity(4)
bpy.context.view_layer.update()
rest_extent = render_pose("bahamut_blend_rest", azimuth_deg=200.0)
for i, az in enumerate((0.0, 90.0, 180.0, 270.0)):
    render_pose(f"bahamut_blend_turntable_{int(az)}", azimuth_deg=az)

# 2) flight clip, mid-frame
rig.animation_data.action = flight_act
_bind_slot(rig.animation_data, flight_act)
mid_frame = flight_frames // 2
scene.frame_set(mid_frame)
bpy.context.view_layer.update()
flight_extent = render_pose("bahamut_blend_flight_mid", azimuth_deg=200.0)

ratio = float(np.max(flight_extent) / max(np.max(rest_extent), 1e-6))
print(f"[bahamut-blend] rest extent={rest_extent.round(2)} flight-mid extent={flight_extent.round(2)} "
      f"ratio={ratio:.2f}" + ("  EXPLODED?!" if ratio > 6.0 else ""))

# --------------------------------------------------------------------------- final saved state
# leave the file parked at frame 1 of the active (flight) action -- spacebar plays clip6 start-to-end on open
rig.animation_data.action = flight_act
_bind_slot(rig.animation_data, flight_act)
scene.frame_current = 1
for pb in rig.pose.bones:
    pb.matrix_basis = mathutils.Matrix.Identity(4)  # let the action itself drive frame 1's pose, not a stale basis

# viewport: material preview shading, looking through the framed camera (frame_camera() above already
# pointed it at the rest-pose silhouette from the last render_pose() call -- reframe once more for the parked
# frame-1 pose so what's saved matches what's on screen when the file opens)
cmin, cmax = evaluated_extent(body)
center, radius = (cmin + cmax) / 2, float(np.linalg.norm(cmax - cmin)) * 0.5 or 1.0
frame_camera(center, radius, azimuth_deg=200.0)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type != "VIEW_3D":
                continue
            space.shading.type = "MATERIAL"
            space.shading.use_scene_lights = True
            space.shading.use_scene_world = False
            try:
                space.region_3d.view_perspective = "CAMERA"
            except Exception as e:  # pragma: no cover -- headless screen quirks
                print(f"  viewport view_perspective warn: {e}")

# pack every texture into the .blend -- one self-contained file
try:
    bpy.ops.file.pack_all()
except Exception as e:
    print(f"[bahamut-blend] pack_all() warn ({e}), packing images individually")
    for img in bpy.data.images:
        if img.packed_file is None and img.source == "FILE":
            try:
                img.pack()
            except Exception as e2:
                print(f"  pack warn {img.name}: {e2}")
n_packed = sum(1 for img in bpy.data.images if img.packed_file is not None)
print(f"[bahamut-blend] {n_packed}/{len(bpy.data.images)} image(s) packed")

# --------------------------------------------------------------------------- leave the RIG active (THE
# Action-Editor fix). The Action Editor always edits the ACTIVE OBJECT's animation data. bpy.ops.object.join()
# above leaves the MESH ('Bahamut') active and sole-selected, so a file saved in that state opens with the
# Action Editor pointed at the mesh: every clip the owner picks there gets assigned to the MESH -- whose
# object-level animation data cannot resolve pose.bones[...] fcurves -- while the armature keeps evaluating
# whatever action it already held (clip6). Reproduced headless: assigning all 8 clips to the mesh moves the
# rig by exactly 0.0000, i.e. "every action shows the same motion". The slots were never the problem.
# So: select + activate the armature, and leave the file in POSE mode -- pose mode also makes the fix DURABLE,
# because clicking the dragon's body in the viewport then can't silently re-point the editor at the mesh.
# All bones are left selected so the Action Editor's default "Only Show Selected" filter shows real channels
# instead of an empty list.
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
try:
    bpy.ops.object.mode_set(mode="POSE")
    for pb in rig.pose.bones:
        pb.select = True  # Blender 5.x: selection lives on PoseBone (Bone.select is gone)
except Exception as e:  # pragma: no cover -- headless context quirks
    print(f"[bahamut-blend] ! could not enter pose mode ({e}); rig is active in object mode")
print(f"[bahamut-blend] active object = {bpy.context.view_layer.objects.active.name!r} "
      f"(mode={rig.mode}, {sum(1 for pb in rig.pose.bones if pb.select)}/{len(rig.pose.bones)} bones selected)")

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print(f"[bahamut-blend] saved -> {OUT_BLEND}")
print("DONE")
