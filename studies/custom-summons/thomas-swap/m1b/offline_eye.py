"""M1b THE OFFLINE EYE (step 6, MANDATORY -- the orchestrator judges these): pose the skinned Thomas with
the dragon's REAL motion and render stills, so we can see the rigid train deform on the dragon skeleton the
way the s54 hybrid will drive it in-game.

Method (engine-faithful): the skinned Thomas armature (DragonRig, identity rest, native rig scale) and
bahamut.glb's own armature are the SAME rig bit-for-bit (inspect_pose.py), so bahamut's baked clip actions
(quaternion per node + root translation, authored against that identity rest) pose DragonRig identically to
the composed world matrices the plugin feeds s54. We assign each clip to DragonRig (and to a faint ghost of
the real dragon for context) and render. A REST still (no action = the bind pose) shows Thomas whole.

Explosion guard: if a pose flings vertices (a bind mismatch), the evaluated mesh bbox blows up -- we measure
it every pose and FAIL loudly if it exceeds a sane multiple of the rest extent. (None expected: the bind IS
the armature's identity rest, so a clip poses cleanly from it.)

Run:  blender --background --python offline_eye.py -- <thomas_skinned.glb> <bahamut.glb> <out_dir>
"""
import bpy
import sys
import os
import math
import numpy as np
import mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
SKINNED_GLB, BAHAMUT_GLB, OUT_DIR = argv[0], argv[1], argv[2]
os.makedirs(OUT_DIR, exist_ok=True)

# (label, clip action name or None for rest, frame, draw ghost?)
POSES = [
    ("m1b_rest",       None,    0,   False),  # bind pose -- Thomas whole (the fitted train)
    ("m1b_clip0_f0",   "clip0", 0,   True),   # the dragon's neutral (== identity rest silhouette)
    ("m1b_clip5_f53",  "clip5", 53,  True),   # mid wing-beat (spread wings)
    ("m1b_clip6_f65",  "clip6", 65,  True),   # the long attack clip, mid
    ("m1b_clip6_f110", "clip6", 110, True),   # the long attack clip, near climax
]


def clear_shapes_and_icos(arm):
    for pb in arm.pose.bones:
        pb.custom_shape = None
    for o in [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Icosphere")]:
        bpy.data.objects.remove(o, do_unlink=True)


bpy.ops.wm.read_factory_settings(use_empty=True)

# --- skinned Thomas ---
bpy.ops.import_scene.gltf(filepath=SKINNED_GLB)
A = next(o for o in bpy.data.objects if o.type == "ARMATURE")
A.name = "DragonRig"
thomas = next(o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("Icosphere"))
clear_shapes_and_icos(A)

# --- reference dragon (ghost) + its clip actions ---
bpy.ops.import_scene.gltf(filepath=BAHAMUT_GLB)
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
B = [a for a in arms if a is not A][0]
B.name = "DragonGhost"
clear_shapes_and_icos(B)
ghost_meshes = [o for o in bpy.data.objects if o.type == "MESH" and o is not thomas and not o.name.startswith("Icosphere")]

# ghost material: faint translucent grey
gm = bpy.data.materials.new("GhostMat")
gm.use_nodes = True
bsdf = gm.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.5, 0.55, 0.6, 1.0)
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = 0.18
gm.blend_method = "BLEND" if hasattr(gm, "blend_method") else gm.blend_method
for m in ghost_meshes:
    m.data.materials.clear()
    m.data.materials.append(gm)

if A.animation_data is None:
    A.animation_data_create()
if B.animation_data is None:
    B.animation_data_create()


def rest_extent():
    return np.ptp(np.array([tuple(thomas.matrix_world @ v.co) for v in thomas.data.vertices]), axis=0)


REST = rest_extent()
print(f"[eye] Thomas rest extent xyz={REST.round(3)} (max={REST.max():.3f})")

# --- lighting + camera + render engine ---
world = bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs[0].default_value = (0.09, 0.10, 0.13, 1.0)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 3.6
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(52), 0, math.radians(28))
fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", type="SUN"))
fill.data.energy = 1.3
bpy.context.collection.objects.link(fill)
fill.rotation_euler = (math.radians(120), 0, math.radians(-55))
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
scene = bpy.context.scene
scene.render.resolution_x = 960
scene.render.resolution_y = 720
scene.render.film_transparent = False
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def evaluated_pts(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    pts = np.array([tuple(mw @ v.co) for v in me.vertices]) if len(me.vertices) else np.zeros((1, 3))
    ev.to_mesh_clear()
    return pts


def apply_pose(clip, frame):
    for arm in (A, B):
        ad = arm.animation_data
        for pb in arm.pose.bones:                       # clear to rest first
            pb.matrix_basis = mathutils.Matrix.Identity(4)
        act = bpy.data.actions.get(clip) if clip else None
        ad.action = act
        # Blender 5.x slotted actions: an action imported for another object won't drive THIS armature
        # unless we bind a slot. Pick the first (only) armature slot; channels then retarget by bone name.
        if act is not None:
            try:
                slots = list(act.slots)
                if slots:
                    ad.action_slot = slots[0]
            except Exception as e:
                print("  slot-bind warn:", e)
    if clip:
        scene.frame_set(frame)
    bpy.context.view_layer.update()


failures = []
for label, clip, frame, ghost in POSES:
    apply_pose(clip, frame)
    # diagnostic: confirm the clip actually moved a wing bone (bone039, the -Y wing tip)
    wb = A.pose.bones.get("bone039")
    wpos = tuple(round(v, 2) for v in (A.matrix_world @ wb.matrix).translation) if wb else None
    print(f"[eye] {label}: bone039 posed world pos={wpos}")
    for m in ghost_meshes:
        m.hide_render = not ghost
    tpts = evaluated_pts(thomas)
    tmin, tmax = tpts.min(0), tpts.max(0)
    ext = tmax - tmin
    ratio = ext.max() / max(REST.max(), 1e-6)
    exploded = ratio > 6.0
    tag = "  EXPLODED!" if exploded else ""
    print(f"[eye] {label}: Thomas extent={ext.round(2)} ratio_vs_rest={ratio:.2f}{tag}")
    if exploded:
        failures.append((label, ratio))
    # frame the union of Thomas + visible ghost
    allpts = tpts.copy()
    if ghost:
        for m in ghost_meshes:
            allpts = np.vstack([allpts, evaluated_pts(m)])
    cmin, cmax = allpts.min(0), allpts.max(0)
    center = mathutils.Vector((cmin + cmax) / 2)
    radius = float(np.linalg.norm(cmax - cmin)) * 0.5 or 1.0
    d = radius * 2.1
    cam.location = center + mathutils.Vector((d * 0.62, -d, radius * 0.5))
    look_at(cam, center)
    cam_data.lens = 45
    scene.render.filepath = os.path.join(OUT_DIR, label + ".png")
    bpy.ops.render.render(write_still=True)
    print(f"      -> {label}.png (cam@{tuple(round(v,1) for v in cam.location)})")

print("\n" + "=" * 50)
if failures:
    print(f"OFFLINE EYE: {len(failures)} EXPLODED pose(s): {failures}")
    sys.exit(1)
print("OFFLINE EYE DONE -- no explosions; stills written to " + OUT_DIR)
