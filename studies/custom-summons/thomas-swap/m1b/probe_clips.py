"""Probe: do bahamut's clips carry LOCATION channels (scale-sensitive) or rotation-only? And which end
of the spine is the head? Read-only."""
import bpy, sys, mathutils
argv = sys.argv[sys.argv.index("--") + 1:]
bahamut_glb = argv[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=bahamut_glb)
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")

def iter_fcurves(act):
    # Blender 5.x slotted Action API
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        for fc in act.fcurves:
            yield fc
        return
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    yield fc


# channel-type census across all clip actions
for act in bpy.data.actions:
    kinds = {}
    for fc in iter_fcurves(act):
        dp = fc.data_path
        if dp.endswith("location"): k = "loc"
        elif "rotation_quaternion" in dp: k = "quat"
        elif "rotation_euler" in dp: k = "euler"
        elif dp.endswith("scale"): k = "scale"
        else: k = dp
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{act.name}: {kinds}")

# where is the head? cluster mesh0/mesh1 verts by Y, and check the two spine tips (bone009 vs bone000 area)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "Icosphere"]
ys = []
for o in meshes:
    for v in o.data.vertices:
        ys.append((o.matrix_world @ v.co).y)
ys.sort()
n = len(ys)
print(f"\nmesh vert Y: min={ys[0]:.2f} max={ys[-1]:.2f} median={ys[n//2]:.2f}")
# count verts in each Y third
lo, hi = ys[0], ys[-1]
t1, t2 = lo + (hi-lo)/3, lo + 2*(hi-lo)/3
c = [0,0,0]
for y in ys:
    c[0 if y<t1 else (1 if y<t2 else 2)] += 1
print(f"vert count by Y-third [{lo:.1f}..{t1:.1f}]={c[0]} [{t1:.1f}..{t2:.1f}]={c[1]} [{t2:.1f}..{hi:.1f}]={c[2]}")

# bone names near the extremes: which bones have head near min-Y and near max-Y
b = arm.data.bones
byy = sorted(b, key=lambda x: x.head_local.y)
print("bones with most -Y head:", [(x.name, round(x.head_local.y,1)) for x in byy[:5]])
print("bones with most +Y head:", [(x.name, round(x.head_local.y,1)) for x in byy[-5:]])
