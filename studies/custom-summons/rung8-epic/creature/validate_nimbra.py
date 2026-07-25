"""RUNG 8 -- VALIDATE the staged NIMBRA set against the engine's own contract. Read-only, exit 1 on
any CRITICAL failure.

    py studies/custom-summons/rung8-epic/creature/validate_nimbra.py

This is the m1b ``validate.py`` + ``fbx_vertscale.py`` pair, ported to the FBX-ASCII the kit emits.
m1b had to reimport through Blender because its FBX came OUT of Blender; ours is written by
``fbx_skin.emit_skinned_fbx``, so we parse it with ``models/fbx_validate`` -- a faithful port of
Memoria's OWN ``FbxAsciiReader``. That is a strictly stronger oracle than a Blender round-trip: it
fails exactly where the engine fails, and Blender cannot open an ASCII FBX at all.

WHAT IS CHECKED, and which engine fact each check protects
----------------------------------------------------------
 1. The file parses under the engine's grammar.                    FbxAsciiReader.cs
 2. Exactly 14 bone Models named + ORDERED bone000..bone013, the
    root typed "Root", every other "LimbNode". The engine builds
    ``_smr.bones`` from the SKELETON, not from the skin clusters,
    and reads the bone NUMBER from the name's last 3 digits.        ModelImporter/FbxSkeleton (m1b law)
 3. Every bone's parent is declared BEFORE it, and the root's
    parent is the Armature Null (a true null Parent NREs the
    importer -> null model -> invisible + softlock).               fbx_skin.py:181-187
 4. RAW FF9 UNITS: the Vertices array is what ModelImporter
    consumes VERBATIM -- no unit metadata, no axis conversion.
    The crown must sit at ~-1400 and the model must span ~1400u.   m1b FBX_SCALE_ALL law
 5. Weights: every vertex has >=1 influence, all influences sum to
    1.0, <=4 bones per vertex, and every cluster names a bone that
    exists. SMOOTH weights are FINE here -- unlike the m1b rigid
    transplant, this is our own creature and the engine blends.
 6. Every cluster's ``Indexes`` is in range and matches ``Weights``.
 7. The material's texture is ``6400.png`` and that file is staged
    beside the FBX (the engine loads it by that filename).
 8. The three ``.anim`` clips exist under ``clips/``, parse as
    JSON, carry a channel for ALL 14 bones (the rest-fill law), and
    open/close on the shared rest pose (THE PLAYLIST-SEAM RULE).    SFXDataMesh.cs:845-869
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
try:
    import ff9mapkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(ROOT / "ff9mapkit"))

import nimbra_clips as NC                                        # noqa: E402
import nimbra_spec as NS                                         # noqa: E402
from ff9mapkit.models import fbx_validate                        # noqa: E402

STAGE = HERE.parent / "stage" / "creature"
N_BONES = 14
EXPECT = [f"bone{k:03d}" for k in range(N_BONES)]
failures: list = []


def check(cond, msg, critical=True):
    print(("  OK   " if cond else ("  FAIL " if critical else "  warn ")) + msg)
    if not cond and critical:
        failures.append(msg)


def nums(node):
    """An FBX array node's values. The reader hands back a single list prop for ``*N { a: ... }``."""
    out = []
    for p in node.props:
        out.extend(p if isinstance(p, list) else [p])
    return [float(v) for v in out]


def walk(nodes, name):
    for n in nodes:
        if n.name == name:
            yield n
        yield from walk(n.children, name)


def main():
    fbx = STAGE / f"{NS.GEO_ID}.fbx"
    png = STAGE / f"{NS.GEO_ID}.png"
    print(f"VALIDATE {fbx}\n{'=' * 78}")
    check(fbx.is_file(), f"staged FBX exists ({fbx.name})")
    check(png.is_file(), f"staged texture exists ({png.name})")
    if failures:
        return 1
    text = fbx.read_text(encoding="ascii")

    # 1. the engine's own grammar -------------------------------------------------------------
    try:
        tree = fbx_validate.validate(text)
        check(True, "parses under Memoria's FbxAsciiReader grammar (structural checks green)")
    except Exception as exc:
        check(False, f"FbxAsciiReader parse/validate: {exc}")
        return 1

    objects = next(n for n in tree if n.name == "Objects")
    conns = next(n for n in tree if n.name == "Connections")
    models = [n for n in objects.children if n.name == "Model"]
    by_id = {}
    bones = []
    for m in models:
        mid, label, typ = int(m.props[0]), str(m.props[1]), str(m.props[2])
        short = label.split("::", 1)[-1]
        by_id[mid] = (short, typ)
        if typ in ("Root", "LimbNode"):
            bones.append((mid, short, typ))

    # 2. skeleton identity + ORDER ---------------------------------------------------------------
    names = [b[1] for b in bones]
    check(len(names) == N_BONES, f"skeleton has {N_BONES} bones (got {len(names)})")
    check(names == EXPECT, f"bones named+ordered bone000..bone{N_BONES-1:03d} -> _smr.bones[k]==bone{{k}} "
                           f"(got {names[:4]}...{names[-1:] if names else ''})")
    check([t for _i, _n, t in bones].count("Root") == 1 and bones[0][2] == "Root",
          "exactly one Root, and it is bone000")

    # 3. parent declared before child, root parents to the Armature Null -------------------------
    oo = [(int(c.props[1]), int(c.props[2])) for c in conns.children
          if c.name == "C" and str(c.props[0]) == "OO"]
    pos = {n: i for i, (_id, n, _t) in enumerate(bones)}
    bone_ids = {i for i, _n, _t in bones}
    ok_order, root_parent = True, None
    for child, parent in oo:
        if child in bone_ids:
            cn = by_id[child][0]
            if parent in bone_ids:
                if pos[by_id[parent][0]] >= pos[cn]:
                    ok_order = False
            elif cn == "bone000" and parent in by_id:
                # NOTE: emit_skinned_fbx ALSO writes `C: "OO", boneId, clusterId` (the reversed
                # cluster convention FbxDocument.GetFirstConnectedIndex requires), so a bone appears
                # as the "child" of its clusters too. Only a real Model node can be the rig parent.
                root_parent = by_id[parent]
    check(ok_order, "every bone's parent is declared BEFORE it")
    check(root_parent is not None and root_parent[1] == "Null",
          f"bone000 parents to a non-bone Null (importer derefs Parent for boneParentId<0) "
          f"-- got {root_parent}")

    # 4. RAW FF9 UNITS -- the numbers ModelImporter consumes verbatim -----------------------------
    geo = next(walk(objects.children, "Geometry"))
    flat = nums(next(c for c in geo.children if c.name == "Vertices"))
    n = len(flat) // 3
    X, Y, Z = flat[0::3], flat[1::3], flat[2::3]
    span = (max(X) - min(X), max(Y) - min(Y), max(Z) - min(Z))
    print(f"  info: {n} verts  X [{min(X):.0f},{max(X):.0f}]  Y [{min(Y):.0f},{max(Y):.0f}]  "
          f"Z [{min(Z):.0f},{max(Z):.0f}]  span {tuple(round(s) for s in span)}")
    check(-1450.0 <= min(Y) <= -1350.0, f"crown at Y ~= -1400 (got {min(Y):.1f}) -- Y-DOWN, raw units")
    check(1300.0 <= span[1] <= 1500.0, f"height ~= 1400u (got {span[1]:.0f}) -- RAW, not a 0.01 export "
                                       f"and not an x100 double-bake")
    check(max(span) < 5000.0, f"no exploded verts (max span {max(span):.0f})")

    # 5/6. clusters: indices, weights, and the bones they name ------------------------------------
    clusters = [d for d in walk(objects.children, "Deformer") if str(d.props[2]) == "Cluster"]
    check(len(clusters) >= 1, f"skin clusters present ({len(clusters)})")
    acc = [0.0] * n
    cnt = [0] * n
    bad_idx = 0
    for cl in clusters:
        idxs = [int(v) for v in nums(next(c for c in cl.children if c.name == "Indexes"))]
        wts = nums(next(c for c in cl.children if c.name == "Weights"))
        if len(idxs) != len(wts):
            bad_idx += 1
        for i, w in zip(idxs, wts):
            if not (0 <= i < n):
                bad_idx += 1
                continue
            acc[i] += w
            cnt[i] += 1
    check(bad_idx == 0, f"every cluster index is in range and pairs with a weight ({bad_idx} bad)")
    check(min(cnt) >= 1, f"every vertex is influenced (unweighted: {sum(1 for c in cnt if c == 0)})")
    check(max(cnt) <= 4, f"<= 4 influences/vertex (max {max(cnt)})")
    worst = max(abs(a - 1.0) for a in acc)
    check(worst < 1e-6, f"influences sum to 1.0 (worst |sum-1| = {worst:.2e}) -- smooth weights are "
                        f"fine for our OWN creature; the engine blends them")
    cl_bones = set()
    for c in conns.children:
        if c.name == "C" and str(c.props[0]) == "OO" and int(c.props[1]) in bone_ids:
            cl_bones.add(by_id[int(c.props[1])][0])
    check(cl_bones.issubset(set(EXPECT)),
          f"every OO-connected bone id is a real bone (all {len(cl_bones)} of {N_BONES})")
    check(len(clusters) == N_BONES - 1,
          f"{len(clusters)} skin clusters for {N_BONES} bones -- bone003/neck deliberately carries "
          f"NO weight (the mask FLOATS; there is no neck geometry), and a weightless bone is still a "
          f"real driven _smr.bones entry (the m1b node-index law)")

    # 7. material -> texture ----------------------------------------------------------------------
    tex = {str(t.props[0]).strip('"') for t in walk(objects.children, "RelativeFilename")}
    tex |= {str(c.props[0]) for t in walk(objects.children, "Texture")
            for c in t.children if c.name == "RelativeFilename"}
    check(any(f"{NS.GEO_ID}.png" in t for t in tex),
          f"material references {NS.GEO_ID}.png (found {sorted(tex) or 'NONE'})")

    # 8. the clips ---------------------------------------------------------------------------------
    print(f"{'-' * 78}\nCLIPS")
    bonelist = NS.build_bones()
    rest_pos = {i: tuple(b["pos"]) for i, b in enumerate(bonelist)}
    for name, spec in NC.all_clips().items():
        p = STAGE / "clips" / f"{name}.anim"
        if not p.is_file():
            check(False, f"{name}: {p} missing -- run make_nimbra_anims.py")
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        check(doc.get("name") == name and abs(doc.get("frameRate", 0) - NC.RATE) < 1e-6,
              f"{name}: name+frameRate ({doc.get('name')}, {doc.get('frameRate')})")
        check(len(doc["transform"]) == N_BONES,
              f"{name}: all {N_BONES} bones carry a channel (got {len(doc['transform'])}) "
              f"-- new_clip's rest-fill, which is what stops the head-focus offset accumulating")
        # THE PLAYLIST-SEAM RULE, verified on the WRITTEN JSON rather than on the builder's memory
        worst_seam, worst_where = 0.0, ""
        for e in doc["transform"]:
            bn = int(e["bone"].rsplit("bone", 1)[-1])
            for chan, rest in (("localRotation", (0.0, 0.0, 0.0, 1.0)),
                               ("localPosition", rest_pos[bn]),
                               ("localScale", (1.0, 1.0, 1.0))):
                keys = e.get(chan)
                if not keys:
                    continue
                axes = ("x", "y", "z", "w")[:len(rest)]
                ends = [keys[-1]] if name == "emerge" else [keys[0], keys[-1]]
                for kf in ends:
                    d = max(abs(kf[a] - r) for a, r in zip(axes, rest))
                    if d > worst_seam:
                        worst_seam, worst_where = d, f"{e['bone']}.{chan}@t={kf['time']}"
        check(worst_seam < 1e-5,
              f"{name}: {'ends' if name == 'emerge' else 'opens AND closes'} on the shared rest pose "
              f"(worst {worst_seam:.2e} at {worst_where or '-'}) -- THE PLAYLIST-SEAM RULE")
        if name == "drift":
            first = {e["bone"]: e for e in doc["transform"]}
            worst_loop = 0.0
            for e in first.values():
                for chan in ("localRotation", "localPosition", "localScale"):
                    ks = e.get(chan)
                    if ks:
                        axes = [a for a in ("x", "y", "z", "w") if a in ks[0]]
                        worst_loop = max(worst_loop, max(abs(ks[0][a] - ks[-1][a]) for a in axes))
            check(worst_loop < 1e-5, f"drift: frame 0 == frame 74 exactly (worst {worst_loop:.2e}) "
                                     f"-- loopable")

    print("=" * 78)
    if failures:
        print(f"VALIDATION FAILED ({len(failures)} CRITICAL):")
        for f in failures:
            print("  - " + f)
        return 1
    print("VALIDATION PASSED -- all critical checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
