"""RUNG 8 -- THE BLENDER OFFLINE EYE: an INDEPENDENT, UNLIT, z-buffered look at NIMBRA.

    "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --python \
        studies/custom-summons/rung8-epic/creature/nimbra_eye.py

Reads only ``nimbra/nimbra_model.json`` + ``nimbra/6400.png`` (written by ``make_nimbra.py``); writes
only ``renders/blender_*.png``. No ff9mapkit import, no install read, no game write.

WHY A SECOND RENDERER AT ALL -- it is not decoration, it answers three things the kit's software
preview structurally cannot:

 1. **Unlit + texture-true.** Workbench with ``light='FLAT'`` and ``color_type='TEXTURE'`` shows the
    atlas at FULL brightness with no shading term -- which is EXACTLY how the SFX path renders an
    instantiated model (rung-7 residual b: no battle-actor lighting or tint pass). The kit preview
    multiplies a lambert buffer over the texture, so it systematically UNDER-states how bright
    NIMBRA will actually be against a blacked-out arena. This is the render that judges STORYBOARD
    1.5's "author ~15% darker than you want".
 2. **A real z-buffer.** ``preview.render_model`` is a painter's-algorithm sort, so any two
    interpenetrating parts produce a sawtooth that looks like a modelling defect but is not. Every
    "is that a hole or the renderer?" question is settled here.
 3. **An independent rig opinion.** The armature is rebuilt from the struct and re-checked
    (14 bones, contiguous bone000..bone013, parent-before-child, vertex groups within that set) by
    code that shares nothing with ``validate_nimbra.py``'s FBX parse.

POSING: the clip poses are skinned in PLAIN PYTHON here (the same linear blend ``make_nimbra.py``
uses) and pushed in as vertex positions, rather than driven through Blender's armature. That is
deliberate -- a Blender pose bone's rotation is expressed in the BONE's own roll frame (head->tail
defines its local Y), which is NOT our parent-space frame, so replaying our quaternions through
``pose_bone.rotation_quaternion`` would silently re-interpret every one of them. The armature is
built for STRUCTURE checking and viewport truth; the deformation is authored math.

ORIENTATION: the object carries a -90 degrees X rotation so FF9's Y-DOWN crown points to Blender +Z.
FF9 is left-handed and Blender is right-handed, so this reads as a left/right mirror -- irrelevant
for a bilaterally symmetric creature, and it is a VIEWING transform only (nothing is exported).
"""
import json
import math
import os
import sys

import bpy
import mathutils

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "nimbra", "nimbra_model.json")
TEX = os.path.join(HERE, "nimbra", "6400.png")
OUT = os.path.join(HERE, "renders")
SIZE = 480
failures = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


# --------------------------------------------------------------------------- skinning (plain python)

def qmat(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))


def mm(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def mv(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def bone_world(bones, pose):
    idx = {b["name"]: i for i, b in enumerate(bones)}
    out = {}
    for i, b in enumerate(bones):
        p = pose.get(i, {})
        lr = qmat(p.get("rot") or (0.0, 0.0, 0.0, 1.0))
        lp = tuple(p.get("pos") or b["pos"])
        if b["parent"] is None:
            out[i] = (lr, lp)
        else:
            PR, PP = out[idx[b["parent"]]]
            d = mv(PR, lp)
            out[i] = (mm(PR, lr), tuple(PP[k] + d[k] for k in range(3)))
    return out


def skin(model, pose):
    bones = model["bones"]
    bw = bone_world(bones, pose)
    rest = {i: p for i, (_r, p) in bone_world(bones, {}).items()}
    V = []
    for v, infl in zip(model["verts"], model["weights"]):
        acc = [0.0, 0.0, 0.0]
        for bn, w in infl:
            R, P = bw[bn]
            r = rest[bn]
            d = mv(R, (v[0] - r[0], v[1] - r[1], v[2] - r[2]))
            for k in range(3):
                acc[k] += w * (d[k] + P[k])
        V.append(tuple(acc))
    return V


def pose_at(curves, frame):
    out = {}
    for bn, ch in curves.items():
        e = {}
        for chan, keys in ch.items():
            e[chan] = tuple(keys[min(frame, len(keys) - 1)][1])
        out[int(bn)] = e
    return out


# --------------------------------------------------------------------------- scene construction

def build_scene(model):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    verts = [tuple(v) for v in model["verts"]]
    faces = [tuple(t) for t in model["tris"]]

    me = bpy.data.meshes.new("nimbra")
    me.from_pydata(verts, [], faces)
    me.validate()
    uvl = me.uv_layers.new(name="UVMap")
    uvs = model["uvs"]
    for poly in me.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            uvl.data[li].uv = tuple(uvs[me.loops[li].vertex_index])
    ob = bpy.data.objects.new("nimbra", me)
    bpy.context.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(-90.0), 0.0, 0.0)     # FF9 Y-down crown -> Blender +Z

    # material: EMISSION, so the render carries zero lighting -- the SFX path's real condition
    mat = bpy.data.materials.new("nimbra")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(TEX)
    tex.interpolation = "Closest"                            # FF9's crisp low-res texel look
    emi = nt.nodes.new("ShaderNodeEmission")
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], emi.inputs["Color"])
    nt.links.new(emi.outputs["Emission"], outn.inputs["Surface"])
    me.materials.append(mat)

    # the armature -- built for STRUCTURE checking + viewport truth, not for posing (see module doc)
    bones = model["bones"]
    bw = bone_world(bones, {})
    kids = {}
    for i, b in enumerate(bones):
        if b["parent"] is not None:
            kids.setdefault(b["parent"], []).append(i)
    arm = bpy.data.armatures.new("NimbraRig")
    aob = bpy.data.objects.new("NimbraRig", arm)
    bpy.context.collection.objects.link(aob)
    aob.rotation_euler = ob.rotation_euler
    bpy.context.view_layer.objects.active = aob
    bpy.ops.object.mode_set(mode="EDIT")
    for i, b in enumerate(bones):
        eb = arm.edit_bones.new(b["name"])
        head = mathutils.Vector(bw[i][1])
        ch = kids.get(b["name"])
        tail = (mathutils.Vector(bw[ch[0]][1]) if ch
                else head + mathutils.Vector((0.0, 60.0, 0.0)))
        if (tail - head).length < 1e-3:
            tail = head + mathutils.Vector((0.0, 40.0, 0.0))
        eb.head, eb.tail = head, tail
    for b in bones:                                          # parent AFTER all bones exist
        if b["parent"]:
            arm.edit_bones[b["name"]].parent = arm.edit_bones[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    for b in bones:
        ob.vertex_groups.new(name=b["name"])
    for vi, infl in enumerate(model["weights"]):
        for bn, w in infl:
            ob.vertex_groups[bones[bn]["name"]].add([vi], float(w), "REPLACE")
    return ob, aob


def setup_render():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"                    # NO lighting term -- the SFX path has no lighting pass
    sh.color_type = "TEXTURE"
    sh.show_object_outline = False
    sh.show_specular_highlight = False
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("void")
    sc.world.use_nodes = False
    sc.world.color = (0.02, 0.022, 0.025)      # the blacked-out arena NIMBRA is composed against
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.file_format = "PNG"
    cam_d = bpy.data.cameras.new("cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 1650.0
    # Blender's default clip range is 0.1..100 BLENDER UNITS. NIMBRA is authored in FF9 units, so the
    # creature is 1400 tall and the camera stands 4000 away -- everything falls beyond the far plane
    # and the first run rendered four empty frames. Scene scale is the trap, not the camera pose.
    cam_d.clip_start, cam_d.clip_end = 1.0, 20000.0
    cam = bpy.data.objects.new("cam", cam_d)
    bpy.context.collection.objects.link(cam)
    sc.camera = cam
    return cam


def place(cam, yaw_deg, dist=4000.0, target_z=700.0, pitch_deg=8.0):
    """Orbit at ``yaw_deg``, AIMING at (0, 0, target_z) -- the model's mid-height.

    The camera height is derived, not set: a pitched camera's aim point drops by dist*tan(pitch), so
    parking it AT target_z pointed it 562u below the creature and the first framing pass cropped
    everything above the waist."""
    a, p = math.radians(yaw_deg), math.radians(pitch_deg)
    cam.location = (math.sin(a) * dist, -math.cos(a) * dist, target_z + dist * math.tan(p))
    cam.rotation_euler = (math.radians(90.0) - p, 0.0, a)


def shot(cam, yaw, path):
    place(cam, yaw)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    model = json.load(open(SRC, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    ob, aob = build_scene(model)
    cam = setup_render()

    # ---- the independent rig opinion --------------------------------------------------------
    print("BLENDER RIG CHECK")
    names = [b.name for b in aob.data.bones]
    expect = [f"bone{k:03d}" for k in range(len(model["bones"]))]
    check(sorted(names) == sorted(expect),
          f"armature carries exactly bone000..bone{len(expect)-1:03d} ({len(names)} bones)")
    order_ok = True
    pos = {n: i for i, n in enumerate(expect)}
    for b in aob.data.bones:
        if b.parent and pos[b.parent.name] >= pos[b.name]:
            order_ok = False
    check(order_ok, "every bone's parent has a LOWER index (contiguous, parent-before-child)")
    vg = {g.name for g in ob.vertex_groups}
    check(vg.issubset(set(expect)), f"all {len(vg)} vertex groups are within the bone set")
    counts = [0] * len(ob.data.vertices)
    sums = [0.0] * len(ob.data.vertices)
    for v in ob.data.vertices:
        for g in v.groups:
            if g.weight > 1e-4:
                counts[v.index] += 1
                sums[v.index] += g.weight
    check(min(counts) >= 1, f"every vertex is influenced (unweighted {counts.count(0)})")
    check(max(counts) <= 4, f"<= 4 influences/vertex (max {max(counts)})")
    check(max(abs(s - 1.0) for s in sums) < 1e-4,
          f"weights normalized (worst |sum-1| {max(abs(s - 1.0) for s in sums):.2e})")
    ext = [(max(c[i] for c in model["verts"]) - min(c[i] for c in model["verts"])) for i in range(3)]
    check(1300.0 <= ext[1] <= 1500.0, f"raw-unit height {ext[1]:.0f}u")

    # ---- the renders --------------------------------------------------------------------------
    print("BLENDER RENDERS (unlit, textured, z-buffered)")
    # YAW 180 = the party's view. The object's -90 X rotation sends FF9 +Z (the face) to Blender +Y,
    # and a yaw-0 camera stands at -Y looking toward +Y -- i.e. straight at NIMBRA's BACK. The first
    # framing pass labelled that "front" and rendered four portraits of a black mask shell.
    for tag, yaw in (("front", 180), ("three_q", 220), ("side", 270), ("back", 0)):
        shot(cam, yaw, os.path.join(OUT, f"blender_bind_{tag}.png"))
        print(f"  blender_bind_{tag}.png")
    for name, spec in model["clips"].items():
        frames = spec["frames"]
        f = {"emerge": 0, "drift": frames // 2, "strike": 33}[name]
        V = skin(model, pose_at(spec["curves"], f))
        for i, v in enumerate(V):
            ob.data.vertices[i].co = v
        ob.data.update()
        yaw = {"emerge": 192, "drift": 214, "strike": 226}[name]
        shot(cam, yaw, os.path.join(OUT, f"blender_clip_{name}_f{f}.png"))
        print(f"  blender_clip_{name}_f{f}.png")
    for i, v in enumerate(model["verts"]):                    # restore the bind pose
        ob.data.vertices[i].co = tuple(v)
    ob.data.update()

    print("=" * 60)
    if failures:
        print(f"BLENDER EYE: {len(failures)} CRITICAL failure(s)")
        for f in failures:
            print("  - " + f)
        sys.exit(1)
    print("BLENDER EYE: rig checks green, renders written -- LOOK AT THEM")


main()
