"""M1b INSPECTION pass 2 (read-only): render the bahamut.glb REST silhouette + two clip poses so the
FIT has a visual, dump the FULL skeleton extent (heads+tails), the bone026 branch, and confirm the
rig.glb armature is bit-identical to bahamut.glb's own armature (so skinning onto rig.glb is valid and
bahamut's clips retarget by bone name).

Run:
  blender --background --python inspect_pose.py -- <rig.glb> <bahamut.glb> <out_dir>
"""
import bpy
import sys
import math
import mathutils
import os

argv = sys.argv[sys.argv.index("--") + 1:]
rig_glb, bahamut_glb, out_dir = argv[0], argv[1], argv[2]
os.makedirs(out_dir, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def skel_points(arm):
    pts = []
    mw = arm.matrix_world
    for b in arm.data.bones:
        pts.append(mw @ b.head_local)
        pts.append(mw @ b.tail_local)
    return pts


def bbox(pts):
    mins = [min(p[i] for p in pts) for i in range(3)]
    maxs = [max(p[i] for p in pts) for i in range(3)]
    return mins, maxs


# ---- rig.glb armature rest (reference for skinning) ----
reset()
bpy.ops.import_scene.gltf(filepath=rig_glb)
rig_arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
rig_rest = {b.name: (b.head_local.copy(), b.tail_local.copy()) for b in rig_arm.data.bones}
rp = skel_points(rig_arm)
rmin, rmax = bbox(rp)
print("RIG.glb full skeleton (heads+tails) world bbox:")
print(f"  min={tuple(round(v,3) for v in rmin)} max={tuple(round(v,3) for v in rmax)} "
      f"dims={tuple(round(rmax[i]-rmin[i],3) for i in range(3))}")

# bone026 branch chain
print("\nbone026 branch (the 2nd root child):")
byname = {b.name: b for b in rig_arm.data.bones}
cur = byname.get("bone026")
chain = []
seen = set()
while cur and cur.name not in seen:
    seen.add(cur.name)
    chain.append((cur.name, tuple(round(v, 2) for v in cur.head_local)))
    kids = [b for b in rig_arm.data.bones if b.parent and b.parent.name == cur.name]
    cur = kids[0] if kids else None
for nm, h in chain[:14]:
    print(f"  {nm} head={h}")

# ---- bahamut.glb: armature + mesh + clips ----
reset()
bpy.ops.import_scene.gltf(filepath=bahamut_glb)
bah_arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "Icosphere"]

# confirm identical skeleton
maxdiff = 0.0
for b in bah_arm.data.bones:
    if b.name in rig_rest:
        h0, t0 = rig_rest[b.name]
        maxdiff = max(maxdiff, (b.head_local - h0).length, (b.tail_local - t0).length)
print(f"\nrig.glb vs bahamut.glb armature: max per-bone head/tail rest diff = {maxdiff:.6f} "
      f"({'IDENTICAL' if maxdiff < 1e-4 else 'DIFFERENT!'})")

bp = skel_points(bah_arm)
bmin, bmax = bbox(bp)
print(f"BAHAMUT skeleton world bbox: min={tuple(round(v,3) for v in bmin)} "
      f"max={tuple(round(v,3) for v in bmax)}")


def mesh_bbox_world(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ mathutils.Vector(c))
    return bbox(pts)


mmin, mmax = mesh_bbox_world(meshes)
print(f"BAHAMUT mesh world bbox (rest): min={tuple(round(v,3) for v in mmin)} "
      f"max={tuple(round(v,3) for v in mmax)} dims={tuple(round(mmax[i]-mmin[i],3) for i in range(3))}")

# ---- render helper ----
world = bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs[0].default_value = (0.1, 0.1, 0.12, 1.0)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
sun.data.energy = 3.5
bpy.context.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30))
cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam
scene = bpy.context.scene
scene.render.resolution_x = 640
scene.render.resolution_y = 480
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except Exception:
    scene.render.engine = "BLENDER_EEVEE"

center = mathutils.Vector([(mmin[i] + mmax[i]) / 2 for i in range(3)])
radius = max(mmax[i] - mmin[i] for i in range(3))


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def shoot(name):
    d = radius * 1.9
    cam.location = center + mathutils.Vector((d * 0.6, -d, radius * 0.4))
    look_at(cam, center)
    cam_data.lens = 45
    scene.render.filepath = os.path.join(out_dir, name)
    bpy.ops.render.render(write_still=True)
    print(f"  rendered {name}")


def apply_clip(clip_name, frame):
    act = bpy.data.actions.get(clip_name)
    if not act:
        print(f"  (no action {clip_name})")
        return
    if not bah_arm.animation_data:
        bah_arm.animation_data_create()
    bah_arm.animation_data.action = act
    scene.frame_set(frame)
    bpy.context.view_layer.update()


print("\nrendering rest + poses:")
shoot("bah_rest.png")
apply_clip("clip5", 53)   # mid of the 107-frame clip
shoot("bah_clip5_f53.png")
apply_clip("clip6", 65)   # mid of the 130-frame clip
shoot("bah_clip6_f65.png")
print("INSPECT POSE DONE")
