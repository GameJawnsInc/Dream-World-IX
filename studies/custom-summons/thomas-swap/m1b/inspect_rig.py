"""M1b INSPECTION (read-only): dump the ef227 dragon rig + bahamut mesh geometry so the FIT step has
real numbers, and dump the normalized Thomas mesh bounds. Prints ONLY -- writes nothing.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python inspect_rig.py -- \
      C:/gd/SCRATCH/summon-transplant/ef227_rig.glb \
      C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb \
      "C:/gd/SCRATCH/thomas/blender_out/thomas_normalized.fbx"

Provenance: reads only local SCRATCH exports (stock-derived, gitignored) + the third-party FBX. Embeds
no game bytes; this script is the committable record of the inspection.
"""
import bpy
import sys
import math
import mathutils

argv = sys.argv[sys.argv.index("--") + 1:]
rig_glb, bahamut_glb, thomas_fbx = argv[0], argv[1], argv[2]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)


def world_bbox(objs):
    mins = [math.inf] * 3
    maxs = [-math.inf] * 3
    for o in objs:
        if o.type != "MESH":
            continue
        for corner in o.bound_box:
            wc = o.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                mins[i] = min(mins[i], wc[i])
                maxs[i] = max(maxs[i], wc[i])
    return mins, maxs


# ============================================================ 1. THE RIG (skeleton only)
print("\n" + "=" * 70)
print("RIG:", rig_glb)
print("=" * 70)
reset()
import_glb(rig_glb)
arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
print(f"armatures: {[a.name for a in arms]}")
arm = arms[0]
print(f"armature matrix_world:\n{arm.matrix_world}")
arm_ws = arm.matrix_world
bones = arm.data.bones
print(f"BONE COUNT: {len(bones)}")

# head/tail in armature-local + world; parent chain
rows = []
for b in bones:
    hl = b.head_local          # armature space (rest)
    tl = b.tail_local
    hw = arm_ws @ hl
    tw = arm_ws @ tl
    length = (tl - hl).length
    parent = b.parent.name if b.parent else "-"
    rows.append((b.name, parent, hl, tl, hw, tw, length))

# summary stats
all_heads_w = [r[4] for r in rows]
mins = [min(h[i] for h in all_heads_w) for i in range(3)]
maxs = [max(h[i] for h in all_heads_w) for i in range(3)]
print(f"HEAD-world bbox min={tuple(round(v,4) for v in mins)} max={tuple(round(v,4) for v in maxs)}")
print(f"HEAD-world span xyz={tuple(round(maxs[i]-mins[i],4) for i in range(3))}")
lengths = [r[6] for r in rows]
print(f"bone length: min={min(lengths):.5f} max={max(lengths):.5f} mean={sum(lengths)/len(lengths):.5f}")
nz = [l for l in lengths if l > 1e-6]
print(f"non-degenerate bones (len>1e-6): {len(nz)} / {len(rows)}")

print("\n--- first 12 bones (name parent | head_local xyz | tail_local xyz | len) ---")
for name, parent, hl, tl, hw, tw, length in rows[:12]:
    print(f"  {name:9s} <-{parent:9s} H=({hl.x:8.4f},{hl.y:8.4f},{hl.z:8.4f}) "
          f"T=({tl.x:8.4f},{tl.y:8.4f},{tl.z:8.4f}) len={length:.4f}")

# Which axis has the largest head-position spread? -> the rig's dominant/spine axis
print(f"\nRIG dominant axis (largest head span): "
      f"{'XYZ'[max(range(3), key=lambda i: maxs[i]-mins[i])]}")

# root chain: walk from root following the single longest-spread child path won't be reliable;
# just print root + its immediate children so we can see the spine start
root = next(b for b in bones if b.parent is None)
print(f"ROOT bone: {root.name}  head_local=({root.head_local.x:.4f},{root.head_local.y:.4f},{root.head_local.z:.4f})")
kids = [b.name for b in bones if b.parent and b.parent.name == root.name]
print(f"ROOT children: {kids}")

# distance of every head from root head (world) -> find the farthest bone (tip of spine/neck/head or tail/wing)
rh = arm_ws @ root.head_local
far = sorted(rows, key=lambda r: (r[4] - rh).length, reverse=True)[:6]
print("farthest-from-root heads (world dist):")
for name, parent, hl, tl, hw, tw, length in far:
    print(f"  {name:9s} dist={ (hw-rh).length:8.4f} head_w=({hw.x:.3f},{hw.y:.3f},{hw.z:.3f})")


# ============================================================ 2. THE BAHAMUT MESH (envelope)
print("\n" + "=" * 70)
print("BAHAMUT MESH:", bahamut_glb)
print("=" * 70)
reset()
import_glb(bahamut_glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print(f"mesh objects: {[o.name for o in meshes]}  total verts={sum(len(o.data.vertices) for o in meshes)}")
bmins, bmaxs = world_bbox(meshes)
bdims = [bmaxs[i] - bmins[i] for i in range(3)]
print(f"REST mesh world bbox min={tuple(round(v,4) for v in bmins)} max={tuple(round(v,4) for v in bmaxs)}")
print(f"REST mesh world dims xyz={tuple(round(v,4) for v in bdims)}")
print(f"REST mesh dominant axis: {'XYZ'[max(range(3), key=lambda i: bdims[i])]}  (longest dim={max(bdims):.4f})")

# how many baked clips (animations) came with the mesh?
print(f"ACTIONS (baked clips): {len(bpy.data.actions)} -> {[a.name for a in bpy.data.actions][:12]}")
for a in bpy.data.actions[:12]:
    fr = a.frame_range
    print(f"  clip '{a.name}': frames {fr[0]:.0f}..{fr[1]:.0f}")


# ============================================================ 3. THOMAS (normalized) bounds
print("\n" + "=" * 70)
print("THOMAS normalized:", thomas_fbx)
print("=" * 70)
reset()
try:
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
except Exception:
    pass
bpy.ops.import_scene.fbx(filepath=thomas_fbx)
tmesh = [o for o in bpy.context.scene.objects if o.type == "MESH"]
print(f"thomas meshes: {[o.name for o in tmesh]}  verts={sum(len(o.data.vertices) for o in tmesh)}")
for o in tmesh:
    print(f"  {o.name}: loc={tuple(round(v,4) for v in o.location)} "
          f"rot={tuple(round(math.degrees(v),2) for v in o.rotation_euler)} scale={tuple(round(v,4) for v in o.scale)}")
    print(f"    materials: {[s.material.name if s.material else None for s in o.material_slots]}")
tmins, tmaxs = world_bbox(tmesh)
tdims = [tmaxs[i] - tmins[i] for i in range(3)]
print(f"THOMAS world bbox min={tuple(round(v,4) for v in tmins)} max={tuple(round(v,4) for v in tmaxs)}")
print(f"THOMAS world dims xyz={tuple(round(v,4) for v in tdims)}")
print(f"THOMAS dominant (length) axis: {'XYZ'[max(range(3), key=lambda i: tdims[i])]}  (len={max(tdims):.4f})")
for img in bpy.data.images:
    print(f"IMAGE: {img.name} size={tuple(img.size)} filepath={img.filepath!r}")
print("\nINSPECTION DONE")
