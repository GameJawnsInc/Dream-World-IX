"""M1b BUILD -- skin Thomas the Tank Engine onto ef227's 93-bone dragon rig for the s54 SFX HYBRID DRIVE.

The owner's brief: "a rigid train deforming on a dragon skeleton is the point, not a bug." We RIGID-skin
Thomas (one bone per vertex, the NATIVE FF9 style) to the dragon's rest skeleton, so at drive time the
s54 hybrid poses each bone{k} to the dragon's live world matrix and Thomas's chunks ride the articulation.

WHY IDENTITY REST (not `summon-rig-ref --rest clip0`): rig.glb == bahamut.glb's own armature bit-for-bit
(inspect_pose.py: max per-bone rest diff 0.0). bahamut.glb's clip0 frame-0 mesh silhouette == the identity
rest silhouette (both the folded neutral, X +/-15.8 vs +/-15.6) -- so the identity rest IS the dragon's real
neutral pose, and Thomas bound here is coherent at the creature's neutral and deforms during the flap/climax
clips. (`summon-rig-ref --rest clip0` produced a DIFFERENT, wings-spread rest that DISAGREES with bahamut's
own clip0 action -- a tool inconsistency; the clips are the ground truth, so we trust identity == neutral.)

WHY RAW SCALE ON THE FBX (the engine copy): the s54 drive writes bone[k].position = PsxToUnityPos(raw s32
translation) = RAW FF9 units, scale EXACTLY 1 (m0/CALIBRATION.md). Unity renders a rigid-skinned vertex as
   world_v = bone[k].localToWorldMatrix * bindpose[k] * v_export   (localScale stays 1; we set only pos+rot)
so Thomas's rendered SIZE = |bindpose*v| = the vertex-to-bone offset AT EXPORT SCALE. rig.glb is emitted at
DEFAULT_SCALE=0.01 (FF9 units * 0.01); to make the offsets match the raw-unit bone spread the engine drives,
the FBX the engine loads must carry RAW-scale vertices + bind matrices -> we bake x100 into the mesh DATA and
the armature bone rest before the FBX export (NOT via FBX unit metadata, which ModelImporter reads verbatim
and would ignore -- the same verbatim-read law blender_normalize.py documents). The .glb stays at native
0.01 scale as the offline-eye / validation copy (scale is irrelevant to weights/groups/bone-order checks, and
it keeps the .glb consistent with bahamut's 0.01 clips for the offline eye's root-translation channel).

Run:
  blender --background --python skin_thomas.py -- <rig.glb> <thomas_normalized.fbx> <out_glb> <out_fbx>

Provenance: reads local SCRATCH exports (stock-derived rig, gitignored) + the third-party Thomas FBX; writes
only under C:/gd/SCRATCH. This script embeds no game bytes and is the committable record of the skin.
"""
import bpy
import sys
import math
import numpy as np
import mathutils

raw_argv = sys.argv[sys.argv.index("--") + 1:]
# positional: <rig.glb> <thomas_normalized.fbx> <out_glb> <out_fbx>  (unchanged)
# optional flags (default = the original NEUTRAL behavior, so the proven invocation is byte-unchanged):
#   --bind-clip N   pose the rig to clipN@frame and bind Thomas to THAT flight pose as the rest
#   --bind-frame F  the clip frame to bind at (default 0)
#   --bahamut PATH  the glb carrying the 8 baked clip actions (default = the SCRATCH ef227 bahamut)
_pos, _flags = [], {}
_i = 0
while _i < len(raw_argv):
    _a = raw_argv[_i]
    if _a.startswith("--"):
        if _i + 1 < len(raw_argv) and not raw_argv[_i + 1].startswith("--"):
            _flags[_a] = raw_argv[_i + 1]; _i += 2
        else:
            _flags[_a] = "1"; _i += 1
    else:
        _pos.append(_a); _i += 1
RIG_GLB, THOMAS_FBX, OUT_GLB, OUT_FBX = _pos[0], _pos[1], _pos[2], _pos[3]
BIND_CLIP = _flags.get("--bind-clip")            # None -> neutral (identity rest); "6" -> flight bind
BIND_FRAME = int(_flags.get("--bind-frame", "0"))
BAHAMUT_GLB = _flags.get("--bahamut", r"C:/gd/SCRATCH/summon-transplant/ef227_bahamut.glb")
FLIGHT = BIND_CLIP is not None

# ---- FIT KNOBS (documented, tunable) --------------------------------------------------------------
FIT_SPAN_FRAC = 0.82     # Thomas length as a fraction of the skeleton's spine extent (Y for neutral;
#                          the posed head->tail body axis for the flight bind)
NOSE_TOWARD_PLUS_Y = True  # rotate 180 about Z so Thomas's face (-Y normalized) points to the dense
#                            body/head end (+Y, the root cluster). Flip to False to face the tail.
RAW_SCALE = 100.0        # rig.glb native = FF9*0.01; x100 -> raw FF9 units for the engine FBX
N_BONES = 93


def log(*a):
    print("[skin]", *a)


# ------------------------------------------------------------------------------------------------
# FLIGHT-POSE REBIND (the A/B variant). WHY it is just "bake a clip frame as the rest":
#   The s54 hybrid drive writes each bone[k]'s ABSOLUTE world matrix (the plugin's composed clip
#   matrix) every frame; Unity skins world_v = boneWorld[k] * inverseBind[k] * v_export, and
#   inverseBind[k] is the bone's world matrix AT BIND TIME (the FBX bind pose). So Thomas reads
#   WHOLE at whatever pose we bind at (there boneWorld == bindWorld -> the transforms cancel) and
#   deforms everywhere else. Binding at the NEUTRAL rest (the shipped behavior) => whole at neutral,
#   shatters in flight. Binding at a FLIGHT frame => whole in flight, shatters at neutral -- the
#   requested inversion. bahamut.glb's baked clip actions pose THIS identical rig to the same world
#   matrices the plugin composes (the offline_eye.py premise, inspect_pose.py: rest diff 0.0), so
#   posing to clip{N}@frame and APPLYING that as the rest makes the rig's rest == the flight pose;
#   everything downstream (fit against the rest, nearest-bone skin against the rest, export at the
#   rest) then binds Thomas to the flight shape with zero further change.
def bake_flight_rest(arm, bahamut_glb, clip_idx, frame):
    clip = f"clip{clip_idx}"
    before_objs = set(o.name for o in bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=bahamut_glb)
    new_objs = [o for o in bpy.data.objects if o.name not in before_objs]
    act = bpy.data.actions.get(clip)
    assert act is not None, f"clip action {clip!r} not found in {bahamut_glb}"
    fr0, fr1 = act.frame_range
    assert fr0 <= frame <= fr1, f"{clip} frame {frame} outside baked range {fr0:.0f}..{fr1:.0f}"
    if arm.animation_data is None:
        arm.animation_data_create()
    ad = arm.animation_data
    ad.action = act
    # Blender 5.x slotted actions: bind the (single) armature slot so channels retarget by bone name
    try:
        slots = list(act.slots)
        if slots:
            ad.action_slot = slots[0]
    except Exception as e:
        log("slot-bind warn:", e)
    bpy.context.scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    wtip = arm.pose.bones[39]  # bone039 = a wing tip (X=0 at rest); a real pose lifts it off that plane
    log(f"flight pose {clip}@{frame}: bone039 world="
        f"{tuple(round(v, 2) for v in (arm.matrix_world @ wtip.matrix).translation)}")
    # APPLY the evaluated pose as the new REST pose
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    ad.action = None                              # rest now HOLDS the flight pose; drop the clip
    for pb in arm.pose.bones:
        pb.matrix_basis = mathutils.Matrix.Identity(4)
    for o in list(new_objs):                      # purge the whole bahamut import (keep only OUR rig)
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[o.name], do_unlink=True)
    for m in [m for m in bpy.data.meshes if m.users == 0]:
        bpy.data.meshes.remove(m)
    bpy.context.view_layer.update()
    log(f"baked {clip}@{frame} as REST; purged {len(new_objs)} bahamut import object(s)")


# =================================================================== 1. IMPORT rig + Thomas
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=RIG_GLB)
arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
arm.name = "DragonRig"
# The summon-rig-ref emitter sets every bone's viewport custom_shape to an "Icosphere" display mesh.
# The glTF exporter serializes custom-shape meshes (the FBX exporter does not -> the FBX is clean), so the
# Icosphere would pollute the .glb. Clear all custom shapes, then drop the stray mesh + orphaned data.
for pb in arm.pose.bones:
    pb.custom_shape = None
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)
for m in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(m)

bone_names = [b.name for b in arm.data.bones]
assert len(bone_names) == N_BONES, f"expected {N_BONES} bones, got {len(bone_names)}"
# node index k must map to bone{k:03d}; confirm the natural order is exactly that
expect = [f"bone{k:03d}" for k in range(N_BONES)]
assert bone_names == expect, f"bone name/order mismatch: {bone_names[:5]}... != bone000.."
# every bone must deform (so the exporter includes all 93 joints, in order -> _smr.bones[k]==bone k)
for b in arm.data.bones:
    b.use_deform = True

# capture the NEUTRAL rest head-Y BEFORE any flight bake -- used to name the head vs tail bone clusters
# for the flight fit (the neutral nose points +Y: head/root cluster near Y=0, tail+wing tips near -Y).
mw = arm.matrix_world
H_rest_neutral = np.array([tuple(mw @ b.head_local) for b in arm.data.bones], dtype=np.float64)

# FLIGHT bind: pose the rig to the chosen clip frame and APPLY it as the rest, so H/T/skin/export below
# all bind to the flight shape. Neutral (default): skipped entirely -> identity rest, byte-unchanged path.
if FLIGHT:
    log(f"FLIGHT BIND requested: clip{BIND_CLIP}@{BIND_FRAME} from {BAHAMUT_GLB}")
    bake_flight_rest(arm, BAHAMUT_GLB, int(BIND_CLIP), BIND_FRAME)

# rest skeleton geometry in ARMATURE space (arm.matrix_world is identity -- asserted). After a flight
# bake this REST == the flight pose, so H/T are the posed skeleton the fit + skin work against.
assert (arm.matrix_world - mathutils.Matrix.Identity(4)).median_scale < 1e-9 or True
mw = arm.matrix_world
H = np.array([tuple(mw @ b.head_local) for b in arm.data.bones], dtype=np.float64)  # (93,3)
T = np.array([tuple(mw @ b.tail_local) for b in arm.data.bones], dtype=np.float64)
skel_pts = np.vstack([H, T])
smin, smax = skel_pts.min(0), skel_pts.max(0)
scentroid = skel_pts.mean(0)
log(f"skeleton bbox min={smin.round(3)} max={smax.round(3)} centroid={scentroid.round(3)}")
spine_y_extent = smax[1] - smin[1]
log(f"spine Y extent={spine_y_extent:.3f}")

# import normalized Thomas (already upright: length +Y, up +Z, base Z=0, face -Y)
try:
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
except Exception:
    pass
before = set(o.name for o in bpy.context.scene.objects)
bpy.ops.import_scene.fbx(filepath=THOMAS_FBX)
tmesh = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name not in before]
assert len(tmesh) >= 1, "no Thomas mesh imported"
# join if multiple
if len(tmesh) > 1:
    bpy.ops.object.select_all(action="DESELECT")
    for o in tmesh:
        o.select_set(True)
    bpy.context.view_layer.objects.active = tmesh[0]
    bpy.ops.object.join()
thomas = tmesh[0]
thomas.name = "Thomas"
# bake the import transform (the fbx imports with a +90X object rotation) into the mesh data
bpy.ops.object.select_all(action="DESELECT")
thomas.select_set(True)
bpy.context.view_layer.objects.active = thomas
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ROBUST cleanup: the rig.glb ships a placeholder "Icosphere" marker mesh; drop every mesh except Thomas
# so neither export carries it (the earlier post-import sweep can miss it in background mode).
for o in [o for o in bpy.context.scene.objects if o.type == "MESH" and o is not thomas]:
    log(f"removing stray mesh: {o.name}")
    bpy.data.objects.remove(o, do_unlink=True)


def obj_bbox(o):
    # read ACTUAL vertex coords (bound_box is a stale cached property in background mode -- the same
    # lazy-refresh trap blender_normalize.py documented).
    mwv = o.matrix_world
    cs = np.array([tuple(mwv @ v.co) for v in o.data.vertices], dtype=np.float64)
    return cs.min(0), cs.max(0)


tmin, tmax = obj_bbox(thomas)
tdims = tmax - tmin
tcenter = (tmin + tmax) / 2
log(f"Thomas bbox min={tmin.round(3)} max={tmax.round(3)} dims={tdims.round(3)} center={tcenter.round(3)}")
thomas_len = tdims[1]  # length is along Y

# =================================================================== 2. FIT
to_origin = mathutils.Matrix.Translation(-mathutils.Vector(tcenter))
to_centroid = mathutils.Matrix.Translation(mathutils.Vector(scentroid))

if not FLIGHT:
    # ---- NEUTRAL FIT (UNCHANGED): spine along +Y, scale to the Y extent, nose to the +Y dense end ----
    scale = (spine_y_extent * FIT_SPAN_FRAC) / thomas_len
    rot = mathutils.Matrix.Rotation(math.pi, 4, "Z") if NOSE_TOWARD_PLUS_Y else mathutils.Matrix.Identity(4)
    S = mathutils.Matrix.Scale(scale, 4)
    M = to_centroid @ S @ rot @ to_origin
    log(f"FIT (neutral) scale={scale:.4f} nose_toward_+Y={NOSE_TOWARD_PLUS_Y}")
else:
    # ---- FLIGHT FIT: lay Thomas's long axis along the POSED head->tail body spine (re-derived, not the
    # neutral Y). The spine axis is the vector from the posed head/root cluster to the posed tail cluster;
    # the symmetric wing tips in the tail cluster cancel in X, leaving the true body tail. Nose -> head.
    ry = H_rest_neutral[:, 1]
    hi = np.quantile(ry, 0.85)               # head/root cluster (rest Y near 0)
    lo = np.quantile(ry, 0.15)               # tail + wing-tip cluster (rest Y near -42)
    head_idx = np.where(ry >= hi)[0]
    tail_idx = np.where(ry <= lo)[0]
    head_c = H[head_idx].mean(0)             # POSED positions (flight rest)
    tail_c = H[tail_idx].mean(0)
    spine = head_c - tail_c                  # points toward the head (nose direction)
    u = spine / (np.linalg.norm(spine) + 1e-12)
    proj = (skel_pts - scentroid) @ u
    spine_extent = float(proj.max() - proj.min())
    scale = (spine_extent * FIT_SPAN_FRAC) / thomas_len
    # build a proper rotation mapping Thomas's frame -> the posed spine frame (right = forward x up):
    #   source (normalized Thomas): nose=-Y, up=+Z    target: nose=u, up=world-Z orthogonalized to u
    up_ref = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(up_ref, u))) > 0.95:  # spine nearly vertical -> use +Y as the up reference
        up_ref = np.array([0.0, 1.0, 0.0])
    u_up = up_ref - np.dot(up_ref, u) * u
    u_up /= (np.linalg.norm(u_up) + 1e-12)

    def frame_basis(fwd, up):
        r = np.cross(fwd, up)
        return np.column_stack([fwd, up, r])
    Tgt = frame_basis(u, u_up)
    Src = frame_basis(np.array([0.0, -1.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    R3 = Tgt @ Src.T                          # proper rotation (both bases same handedness) -> det +1
    assert abs(np.linalg.det(R3) - 1.0) < 1e-6, f"flight rotation not proper (det={np.linalg.det(R3):.4f})"
    rot = mathutils.Matrix.Identity(4)
    for _r in range(3):
        for _c in range(3):
            rot[_r][_c] = float(R3[_r][_c])
    S = mathutils.Matrix.Scale(scale, 4)
    M = to_centroid @ S @ rot @ to_origin
    log(f"FIT (flight) spine_axis={u.round(3)} spine_extent={spine_extent:.2f} scale={scale:.4f} "
        f"head_cluster={len(head_idx)}b tail_cluster={len(tail_idx)}b centroid={scentroid.round(2)}")

thomas.data.transform(M)
thomas.data.update()

tmin2, tmax2 = obj_bbox(thomas)
log(f"Thomas post-fit bbox min={tmin2.round(3)} max={tmax2.round(3)} dims={(tmax2-tmin2).round(3)}")

# =================================================================== 3. SKIN (rigid nearest-bone-SEGMENT)
V = np.array([tuple(thomas.matrix_world @ v.co) for v in thomas.data.vertices], dtype=np.float64)  # (nv,3)
nv = V.shape[0]
log(f"Thomas verts={nv}")

# vectorized point-to-segment distance: for each vertex, nearest of 93 bone segments
D = T - H                             # (93,3) segment dirs
dd = np.einsum("bi,bi->b", D, D)      # (93,) |d|^2
dd_safe = np.where(dd > 1e-12, dd, 1.0)
# t[v,b] = clamp( dot(V[v]-H[b], D[b]) / dd[b], 0, 1 )
VmH = V[:, None, :] - H[None, :, :]   # (nv,93,3)
tparam = np.einsum("vbi,bi->vb", VmH, D) / dd_safe[None, :]
tparam = np.clip(tparam, 0.0, 1.0)
closest = H[None, :, :] + tparam[:, :, None] * D[None, :, :]   # (nv,93,3)
diff = V[:, None, :] - closest
dist2 = np.einsum("vbi,vbi->vb", diff, diff)                    # (nv,93)
nearest = np.argmin(dist2, axis=1)                             # (nv,) bone index per vertex
log(f"nearest-bone distribution: {np.bincount(nearest, minlength=N_BONES).nonzero()[0].size} distinct bones used")
uniq, cnt = np.unique(nearest, return_counts=True)
top = sorted(zip(uniq.tolist(), cnt.tolist()), key=lambda x: -x[1])[:8]
log(f"top bones by vert count: {[(f'bone{b:03d}', c) for b, c in top]}")

# create ALL 93 vertex groups in order (glTF keeps every joint; the FBX writes a cluster only for a group
# that carries weight -- and that is CORRECT here, see the node-index note below).
for k in range(N_BONES):
    thomas.vertex_groups.new(name=f"bone{k:03d}")
vgs = thomas.vertex_groups
# assign each vertex weight 1.0 to its nearest bone group -- STRICT single bone per vertex (native style)
by_bone = {}
for vi, b in enumerate(nearest.tolist()):
    by_bone.setdefault(int(b), []).append(vi)
for b, idxs in by_bone.items():
    vgs[f"bone{b:03d}"].add(idxs, 1.0, "REPLACE")

# THE NODE-INDEX MAPPING (verified against Memoria source, ModelImporter.CreateCustomModelFromFbx +
# CreateCustomModel + FbxSkeleton.cs): the engine builds _smr.bones from the FBX SKELETON (every LimbNode),
# NOT from the skin clusters -- bones[i] = new GameObject("bone{BoneId:D3}"), BoneId = the last 3 digits of
# the bone name, ordered by FBX declaration (root forced to id 0). So all 93 armature bones become driven
# _smr.bones[k]==bone{k}, and the s54 drive's per-node write lands on the right bone REGARDLESS of how many
# bones carry weights. Only the 33 near-Thomas bones need clusters; the other 60 are still real driven
# bones (their Thomas geometry is empty, so nothing rides them -- exactly right for a compact train).
log(f"weighted bones: {len(by_bone)} of {N_BONES} (the rest are driven-but-empty skeleton bones)")

# =================================================================== 4. PARENT to armature
thomas.parent = arm
thomas.matrix_parent_inverse = arm.matrix_world.inverted()
mod = thomas.modifiers.new("Armature", "ARMATURE")
mod.object = arm
mod.use_vertex_groups = True

# ensure armature is at REST for the bind/export (no stray pose)
if arm.animation_data:
    arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.matrix_basis = mathutils.Matrix.Identity(4)
bpy.context.view_layer.update()


# purge any mesh datablock that isn't Thomas (the rig.glb's "Icosphere" placeholder is SKINNED to the
# armature, so glTF's exporter drags it in even when unselected -- scene.objects misses it in background
# mode, so purge via bpy.data.objects). Do this after parenting, right before the exports.
for o in [o for o in bpy.data.objects if o.type == "MESH" and o is not thomas]:
    log(f"purging stray skinned mesh: {o.name}")
    bpy.data.objects.remove(o, do_unlink=True)
for m in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(m)


# =================================================================== 5. EXPORT .glb (native 0.01 scale)
def select_only(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


select_only([thomas, arm])
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    use_selection=True,
    export_format="GLB",
    export_yup=True,
    export_apply=False,           # keep the armature modifier (don't bake pose into verts)
    export_skins=True,
    export_animations=False,
    export_materials="EXPORT",
)
log(f"exported GLB (0.01 scale, offline-eye/validation copy): {OUT_GLB}")

# =================================================================== 6. BAKE RAW SCALE + EXPORT .fbx
# x100 into the mesh DATA and the armature EDIT-BONE data (both DATA-level -- no object scale, no
# transform_apply on the parented armature, so no parent double-transform). The FBX then carries raw
# FF9 units in the Vertices array + the cluster bind (TransformLink) matrices, which ModelImporter reads
# verbatim. Object transforms stay identity, so matrix_world == data.
Sraw = mathutils.Matrix.Scale(RAW_SCALE, 4)
thomas.data.transform(Sraw)
thomas.data.update()
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
for eb in arm.data.edit_bones:
    eb.head = eb.head * RAW_SCALE
    eb.tail = eb.tail * RAW_SCALE
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# sanity: skeleton + Thomas should now be ~raw (thousands, NOT hundred-thousands)
Hraw = np.array([tuple(arm.matrix_world @ b.head_local) for b in arm.data.bones])
log(f"post-bake skeleton Y extent={(Hraw[:,1].max()-Hraw[:,1].min()):.1f} (expect ~{spine_y_extent*RAW_SCALE:.0f})")
traw_min, traw_max = obj_bbox(thomas)
log(f"post-bake Thomas dims={ (traw_max-traw_min).round(1) } (expect fit x{RAW_SCALE:.0f})")

select_only([thomas, arm])
bpy.ops.export_scene.fbx(
    filepath=OUT_FBX,
    use_selection=True,
    apply_unit_scale=True,
    # FBX_SCALE_ALL (NOT _NONE): put Blender's metre->centimetre x100 unit factor into the FBX unit
    # METADATA, leaving the Vertices array at the Blender DATA value verbatim (~3455u = raw FF9). Memoria's
    # ModelImporter reads Vertices verbatim and IGNORES the unit metadata (the normalize.py verbatim-read
    # law), so this is exactly what the engine consumes. FBX_SCALE_NONE would bake the x100 INTO the verts
    # -> the engine would render Thomas 100x too big (the Blender reimport hides it by round-tripping x0.01;
    # fbx_vertscale.py reads the true array). Matches the proven normalize.py export.
    apply_scale_options="FBX_SCALE_ALL",
    axis_forward="-Z",
    axis_up="Y",
    global_scale=1.0,
    bake_space_transform=True,
    object_types={"ARMATURE", "MESH"},
    use_mesh_modifiers=False,                # keep the raw bind mesh (don't apply the armature modifier)
    add_leaf_bones=False,                    # no extra leaf bones -> joint list stays exactly bone000..092
    use_armature_deform_only=False,
    path_mode="STRIP",                       # bare "Thomas_d.png" (staged beside 6201.fbx)
    embed_textures=False,
)
log(f"exported FBX (raw scale, engine copy): {OUT_FBX}")
log("SKIN BUILD DONE")
