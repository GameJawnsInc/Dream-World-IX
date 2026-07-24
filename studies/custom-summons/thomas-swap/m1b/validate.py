"""M1b VALIDATE (step 5): reimport the skinned exports and assert the s54 hybrid-drive contract, which is
grounded in the Memoria FBX importer (ModelImporter.CreateCustomModelFromFbx + CreateCustomModel +
FbxSkeleton.cs, read in the clone):

  * the engine builds _smr.bones from the FBX SKELETON -- every LimbNode -> bone{BoneId:D3}, BoneId = the
    bone name's last 3 digits, ordered by FBX declaration (root forced to id 0). So the CRITICAL check is:
    the ARMATURE has 93 bones named bone000..bone092 IN ORDER (that is what the drive indexes by node k).
  * every vertex has exactly ONE influencing group at weight 1.0 (rigid single-bone, native FF9 style);
  * every vertex-group (skin-cluster) name is within bone000..bone092. A SUBSET is expected + correct --
    only the ~33 near-Thomas bones carry weight; the other 60 are real driven-but-empty skeleton bones.
  * the .fbx material references Thomas_d.png (the engine loads the texture by that filename).

Format-aware: the .fbx is the ENGINE copy (strict). The .glb is the offline-eye copy -- glTF legitimately
splits verts at UV seams into multiple primitives and embeds textures, so its mesh-count / texture-name are
INFO, not failures. Exit non-zero on any CRITICAL failure. Read-only.

Run:  blender --background --python validate.py -- <fbx> <glb>
"""
import bpy
import sys
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
FBX, GLB = argv[0], argv[1]
N = 93
EXPECT = [f"bone{k:03d}" for k in range(N)]
failures = []


def check(cond, msg, critical=True):
    tag = "  OK  " if cond else ("  FAIL" if critical else "  warn")
    print(tag + " " + msg)
    if not cond and critical:
        failures.append(msg)


def load(path, kind):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if kind == "fbx":
        try:
            bpy.ops.preferences.addon_enable(module="io_scene_fbx")
        except Exception:
            pass
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)


def validate(path, kind):
    strict = (kind == "fbx")
    print("\n" + "=" * 62 + f"\nVALIDATE {kind} ({'ENGINE, strict' if strict else 'offline-eye'}): {path}\n" + "=" * 62)
    load(path, kind)
    # Blender's glTF IMPORTER fabricates an "Icosphere" bone-display shape mesh on import (it is NOT in the
    # file -- the exported glb's JSON has a single 'Thomas' mesh, verified separately). Filter it out so the
    # reimport artifact doesn't masquerade as skin geometry.
    all_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    meshes = [o for o in all_meshes if not o.name.startswith("Icosphere")]
    dropped = [o.name for o in all_meshes if o.name.startswith("Icosphere")]
    if dropped:
        print(f"  (ignored importer-fabricated bone-shape mesh(es): {dropped})")
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    check(len(meshes) >= 1, f"at least one mesh (got {len(meshes)})")
    check(len(arms) == 1, f"exactly one armature (got {len(arms)})")
    if kind == "fbx":
        check(len(meshes) == 1, f"single mesh (got {len(meshes)})")
    else:
        check(len(meshes) == 1, f"[info] glb mesh objects={len(meshes)} (glTF may split at UV seams)", critical=False)
    arm = arms[0]

    # CRITICAL: armature (FBX skeleton) has 93 bones named + ordered bone000..092 -> this is _smr.bones
    bnames = [b.name for b in arm.data.bones]
    check(len(bnames) == N, f"armature/skeleton bone count == {N} (got {len(bnames)})")
    check(bnames == EXPECT, f"skeleton bones named+ordered bone000..bone{N-1:03d} "
                            f"(first5={bnames[:5]} last={bnames[-1] if bnames else '-'}) "
                            f"-> _smr.bones[k]==bone{{k}}")

    # cluster (vertex-group) names subset of bone000..092
    used_names = set()
    bad_v = 0
    bad_w = 0
    example = None
    total_v = 0
    for mesh in meshes:
        vg = [g.name for g in mesh.vertex_groups]
        check(all(n in EXPECT for n in vg),
              f"[{mesh.name}] all {len(vg)} vertex-group names within bone000..bone{N-1:03d}")
        for v in mesh.data.vertices:
            total_v += 1
            infl = [(mesh.vertex_groups[g.group].name, g.weight) for g in v.groups if g.weight > 1e-4]
            if len(infl) != 1:
                bad_v += 1
                if example is None:
                    example = (mesh.name, v.index, infl)
            else:
                used_names.add(infl[0][0])
                if abs(infl[0][1] - 1.0) > 1e-4:
                    bad_w += 1
    check(bad_v == 0, f"every vertex has exactly ONE influencing group (violations={bad_v}"
                      f"{'' if example is None else f', e.g. {example}'})")
    check(bad_w == 0, f"every influencing weight == 1.0 (violations={bad_w})")
    check(used_names.issubset(set(EXPECT)) and len(used_names) >= 1,
          f"weighted bones ({len(used_names)}) are a subset of bone000..092 "
          f"(expected ~33 near-Thomas bones; the rest are driven-but-empty)")

    # material -> Thomas_d.png (critical for fbx; info for glb which embeds)
    tex = set()
    for mesh in meshes:
        for ms in mesh.material_slots:
            m = ms.material
            if not m or not getattr(m, "node_tree", None):
                continue
            for node in m.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    fp = node.image.filepath or node.image.name
                    tex.add(fp.replace("\\", "/").split("/")[-1])
    has_thomas = any("thomas_d.png" in t.lower() for t in tex)
    check(has_thomas, f"material references Thomas_d.png (found: {sorted(tex) or 'NONE'})", critical=strict)

    # scale sanity
    co = np.vstack([np.array([tuple(m.matrix_world @ v.co) for v in m.data.vertices]) for m in meshes])
    span = (co.max(0) - co.min(0))
    print(f"  info: {total_v} verts, world span xyz={span.round(1)} "
          f"({'RAW (thousands)' if span.max() > 500 else 'native 0.01 (tens)'})")


validate(FBX, "fbx")
validate(GLB, "glb")

print("\n" + "=" * 62)
if failures:
    print(f"VALIDATION FAILED ({len(failures)} CRITICAL issue(s)):")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("VALIDATION PASSED -- all critical checks green")
