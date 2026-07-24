"""M1b: inspect the clip0-rest rig's skeleton extent (the candidate bind pose) + render the bahamut mesh
posed at clip0 frame 0, so we can decide identity-rest vs clip0-rest for the bind. Read-only."""
import bpy, sys, math, mathutils, os
argv = sys.argv[sys.argv.index("--") + 1:]
rig0_glb, bahamut_glb, out_dir = argv[0], argv[1], argv[2]
os.makedirs(out_dir, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def skel_pts(arm):
    mw = arm.matrix_world
    p = []
    for b in arm.data.bones:
        p.append(mw @ b.head_local); p.append(mw @ b.tail_local)
    return p


def bbox(p):
    return ([min(q[i] for q in p) for i in range(3)], [max(q[i] for q in p) for i in range(3)])


reset()
bpy.ops.import_scene.gltf(filepath=rig0_glb)
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
p = skel_pts(arm)
mn, mx = bbox(p)
print("CLIP0-REST rig skeleton bbox:")
print(f"  min={tuple(round(v,3) for v in mn)} max={tuple(round(v,3) for v in mx)} "
      f"dims={tuple(round(mx[i]-mn[i],3) for i in range(3))}")
# spine: root head -> farthest bone head
root = next(b for b in arm.data.bones if b.parent is None)
rh = arm.matrix_world @ root.head_local
far = max(arm.data.bones, key=lambda b: ((arm.matrix_world @ b.head_local) - rh).length)
fh = arm.matrix_world @ far.head_local
print(f"  root {root.name} head={tuple(round(v,3) for v in rh)}")
print(f"  farthest {far.name} head={tuple(round(v,3) for v in fh)} dist={ (fh-rh).length:.3f}")
print(f"  spine dir (root->farthest, normalized)={tuple(round(v,4) for v in (fh-rh).normalized())}")
# count near-degenerate collapses (bones sharing head within 1e-3)
print(f"  any-nan? {any(math.isnan(v) for q in p for v in q)}")

# ---- render bahamut posed at clip0 f0 ----
reset()
bpy.ops.import_scene.gltf(filepath=bahamut_glb)
bah = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "Icosphere"]
act = bpy.data.actions.get("clip0")
if bah.animation_data is None:
    bah.animation_data_create()
bah.animation_data.action = act
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

pts = []
for o in meshes:
    for c in o.bound_box:
        pts.append(o.matrix_world @ mathutils.Vector(c))
mmn, mmx = bbox(pts)
print(f"BAHAMUT mesh @ clip0 f0 bbox: min={tuple(round(v,3) for v in mmn)} "
      f"max={tuple(round(v,3) for v in mmx)} dims={tuple(round(mmx[i]-mmn[i],3) for i in range(3))}")

world = bpy.data.worlds.new("W"); bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs[0].default_value = (0.1, 0.1, 0.12, 1.0)
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN")); sun.data.energy = 3.5
bpy.context.collection.objects.link(sun); sun.rotation_euler = (math.radians(50), 0, math.radians(30))
cd = bpy.data.cameras.new("C"); cam = bpy.data.objects.new("C", cd)
bpy.context.collection.objects.link(cam); bpy.context.scene.camera = cam
sc = bpy.context.scene; sc.render.resolution_x = 640; sc.render.resolution_y = 480
try: sc.render.engine = "BLENDER_EEVEE_NEXT"
except Exception: sc.render.engine = "BLENDER_EEVEE"
center = mathutils.Vector([(mmn[i]+mmx[i])/2 for i in range(3)])
radius = max(mmx[i]-mmn[i] for i in range(3))
d = radius*1.9
cam.location = center + mathutils.Vector((d*0.6, -d, radius*0.4))
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.lens = 45
sc.render.filepath = os.path.join(out_dir, "bah_clip0_f0.png")
bpy.ops.render.render(write_still=True)
print("rendered bah_clip0_f0.png")
print("DONE")
