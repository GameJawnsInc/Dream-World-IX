"""RUNG F -- THE CARRIED-SPIKE SHAVE (FIXED6) CODE-DISJOINT FALSIFIER (2026-07-25).

Round-6 verifier. Does NOT import uvf_fix6.py, uvf_relief_probe.py, uvf_fix2/3/4/5.py, or their
falsifiers. Re-implements every parse/diff/weld/facing/basin/topo check here from raw bytes, using
only the kit's raw loaders (ff9mapkit.world.extract/.mesh) + the kit ground-family table
(grassland.TOPO_FAMILY) as an oracle for "which kept topos count as ground". Everything else --
position keying, the weld map, the 3D facing test, the basin distance test, the file diff -- is
independently coded here.

CLAIMS TESTED INDEPENDENTLY FROM RAW BYTES (matching uvf_fix6.py's own self-check battery, but never
calling into it):
 (1) tree diff FIXED5 -> FIXED6: exactly 180 files each side, changed set is Terrain-only, all Disc1.
 (2) UV / tangent / index bytes are BYTE-IDENTICAL on every changed file (this round writes Y + normals
     only) -- and on every file, not just the changed ones.
 (3) No X or Z coordinate differs anywhere in the 20-block Terrain union.
 (4) THE WELD MAP: build my own coincident-3D-position map on FIXED5 across all 8 parts of all 20
     touched blocks; every group that moved in FIXED6 moved as ONE (no split, no partial move); every
     moved group's dY is uniform across every entry in it.
 (5) Classify moved groups by what touched them in FIXED5 (kept-ground / kept-rock / fill-only, using
     TOPO_FAMILY as the ground oracle) and report the split.
 (6) THE BASIN: independently re-derive plan distance from the stated crater centre; zero moved groups
     fall inside the stated basin radius; report the minimum plan distance of any moved group.
 (7) FLAT-MESH invariant (vcount == len(indices) == len(verts), indices % 3 == 0) on every FIXED6
     Terrain file.
 (8) NO NEW DOWN-FACING TRIS: recompute the geometric face normal Y-sign on every Terrain triangle in
     both trees from my own cross-product, independently of uvf_fix6's tri_geo.
 (9) Re-run the build deterministically is NOT redone here (uvf_fix6.py already asserts that); this
     script only ever reads.

READ-ONLY vs the game install. Writes out/rung_f/uvf_fix6_falsify_report.json.

    py -X utf8 uvf_fix6_falsify.py
"""
from __future__ import annotations
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

RUNG = HERE / "out" / "rung_f"
FIXED5 = RUNG / "FF9CustomMap-world-FIXED5"
FIXED6 = RUNG / "FF9CustomMap-world-FIXED6"
BUILD_JSON = RUNG / "rung_f_build.json"
OUT = RUNG / "uvf_fix6_falsify_report.json"

PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
POS_DP = 3
BASIN_C = (127.14, -1161.42)
BASIN_R = 7.92
N_FILES = 180


def log(m):
    print(m, flush=True)


def pkey(p):
    return (round(p[0], POS_DP), round(p[1], POS_DP), round(p[2], POS_DP))


def rc(k):
    return math.hypot(k[0] - BASIN_C[0], k[2] - BASIN_C[1])


def face_ny(a, b, c):
    """Geometric face normal's Y component, independently coded (raw cross product)."""
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return uz * wx - ux * wz  # ny = uz*wx - ux*wz


def face_area2(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    wx, wy, wz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * wz - uz * wy
    ny = uz * wx - ux * wz
    nz = ux * wy - uy * wx
    return nx * nx + ny * ny + nz * nz


def sha_pair(p5, p6):
    import hashlib
    return hashlib.sha256(p5.read_bytes()).hexdigest(), hashlib.sha256(p6.read_bytes()).hexdigest()


def main():
    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20, len(touched)

    out = {"meta": dict(script="uvf_fix6_falsify.py", read_only=True,
                        base=str(FIXED5), out=str(FIXED6), touched_blocks=len(touched))}

    # -------------------------------------------------------------------------------------------
    # (1) whole-tree file diff, independently walked
    # -------------------------------------------------------------------------------------------
    files5 = sorted(p for p in FIXED5.rglob("*") if p.is_file())
    files6 = sorted(p for p in FIXED6.rglob("*") if p.is_file())
    rel5 = [str(p.relative_to(FIXED5)) for p in files5]
    rel6 = [str(p.relative_to(FIXED6)) for p in files6]
    same_set = (rel5 == rel6)
    changed = []
    for r in rel5:
        h5, h6 = sha_pair(FIXED5 / r, FIXED6 / r)
        if h5 != h6:
            changed.append(r)
    out["tree_diff"] = dict(
        n_files_fixed5=len(rel5), n_files_fixed6=len(rel6), file_set_identical=same_set,
        n_changed=len(changed), changed=changed,
        all_changed_are_terrain=all("Terrain" in r for r in changed),
        all_changed_are_disc1=all("Disc1" in r for r in changed),
        n_files_expected=N_FILES,
        counts_match_180=(len(rel5) == N_FILES and len(rel6) == N_FILES))
    log(f"[1] files fixed5={len(rel5)} fixed6={len(rel6)} identical_set={same_set} "
        f"changed={len(changed)} {changed}")

    # -------------------------------------------------------------------------------------------
    # (2)+(3)+(7)+(8) per-block Terrain byte checks
    # -------------------------------------------------------------------------------------------
    uv_bad = tan_bad = idx_bad = vcount_bad = 0
    xz_moved_entries = 0
    y_moved_entries = 0
    flat_bad = []
    down_before = down_after = down_changed = newly_down = 0
    degen_before = degen_after = 0
    d5_all, d6_all = {}, {}
    for b in touched:
        p5 = FIXED5 / M.override_relpath(1, b[0], b[1], part="Terrain")
        p6 = FIXED6 / M.override_relpath(1, b[0], b[1], part="Terrain")
        d5 = M.read_ff9mesh(p5)
        d6 = M.read_ff9mesh(p6)
        d5_all[b], d6_all[b] = d5, d6
        uv_bad += (d5["uvs"] != d6["uvs"])
        tan_bad += (d5["tangents"] != d6["tangents"])
        idx_bad += (d5["indices"] != d6["indices"])
        vcount_bad += (d5["vcount"] != d6["vcount"])
        if not (d6["vcount"] == len(d6["indices"]) == len(d6["verts"]) and len(d6["indices"]) % 3 == 0):
            flat_bad.append(f"{b}")
        ox, oz = X.block_world_origin(*b)
        for j in range(min(d5["vcount"], d6["vcount"])):
            v5, v6 = d5["verts"][j], d6["verts"][j]
            if v5[0] != v6[0] or v5[2] != v6[2]:
                xz_moved_entries += 1
            if v5[1] != v6[1]:
                y_moved_entries += 1
        for t in range(len(d6["indices"]) // 3):
            tri = d6["indices"][3 * t:3 * t + 3]
            A3 = [(d5["verts"][j][0] + ox, d5["verts"][j][1], d5["verts"][j][2] + oz) for j in tri]
            B3 = [(d6["verts"][j][0] + ox, d6["verts"][j][1], d6["verts"][j][2] + oz) for j in tri]
            na, nb = face_ny(*A3), face_ny(*B3)
            sa = 0 if abs(na) < 1e-12 else (1 if na > 0 else -1)
            sb = 0 if abs(nb) < 1e-12 else (1 if nb > 0 else -1)
            down_before += (sa < 0)
            down_after += (sb < 0)
            down_changed += (sa != sb)
            newly_down += (sa >= 0 and sb < 0)
            degen_before += (face_area2(*A3) < 1e-18)
            degen_after += (face_area2(*B3) < 1e-18)

    out["byte_checks"] = dict(
        uv_files_differing=uv_bad, tan_files_differing=tan_bad, idx_files_differing=idx_bad,
        vcount_files_differing=vcount_bad,
        xz_moved_vertex_entries=xz_moved_entries, y_moved_vertex_entries=y_moved_entries,
        flat_mesh_bad_blocks=flat_bad, flat_mesh_ok=(not flat_bad),
        down_facing_before=down_before, down_facing_after=down_after,
        tris_facing_changed=down_changed, newly_down_facing=newly_down,
        degenerate_area_before=degen_before, degenerate_area_after=degen_after,
        new_degenerate=max(0, degen_after - degen_before))
    log(f"[2] uv_bad={uv_bad} tan_bad={tan_bad} idx_bad={idx_bad} vcount_bad={vcount_bad} "
        f"xz_moved={xz_moved_entries} y_moved={y_moved_entries}")
    log(f"[3] flat_mesh_bad={len(flat_bad)} facing_changed={down_changed} newly_down={newly_down} "
        f"new_degenerate={max(0, degen_after - degen_before)}")

    # -------------------------------------------------------------------------------------------
    # (4)+(5)+(6) the weld map: coincident 3D positions over ALL 8 parts of all 20 blocks, built on
    #     FIXED5, classified by what kind of geometry touches them there, then checked against FIXED6.
    # -------------------------------------------------------------------------------------------
    pre_groups = defaultdict(list)     # poskey -> [(block, part, vidx)]
    post_pos = {}                      # (block, part, vidx) -> poskey in FIXED6
    kept_ground_pos = set()
    kept_rock_pos = set()
    fill_candidate_pos = set()         # touched ONLY by tris whose vertex[0] tangent decodes -- filled in below
    # classify using the SPEC (pre-fix) tree's UV-degenerate test is uvf_fix6's own bookkeeping, which
    # this falsifier deliberately avoids; instead classify purely by TOPOGRAPH FAMILY on FIXED5's own
    # Terrain tris: "ground" if grassland.TOPO_FAMILY has an entry, "rock" otherwise. This is a coarser
    # but code-disjoint oracle -- it does not know which tris are synthesized, only what topo family
    # material sits under each surviving vertex.
    topo_of_pos = defaultdict(set)
    for b in touched:
        d5 = d5_all[b]
        ox, oz = X.block_world_origin(*b)
        tans = d5["tangents"]
        for t in range(len(d5["indices"]) // 3):
            tri = d5["indices"][3 * t:3 * t + 3]
            topo = X.decode_id(int(round(tans[tri[0]][0])))["topograph"]
            for j in tri:
                v = d5["verts"][j]
                k = pkey((v[0] + ox, v[1], v[2] + oz))
                topo_of_pos[k].add(topo)
        for part in PARTS:
            p5 = FIXED5 / M.override_relpath(1, b[0], b[1], part=part)
            p6 = FIXED6 / M.override_relpath(1, b[0], b[1], part=part)
            if not p5.exists():
                continue
            dd5 = M.read_ff9mesh(p5)
            dd6 = M.read_ff9mesh(p6)
            assert dd5["vcount"] == dd6["vcount"], f"vcount drift {b} {part}"
            for j in range(dd5["vcount"]):
                a, c = dd5["verts"][j], dd6["verts"][j]
                k = pkey((a[0] + ox, a[1], a[2] + oz))
                pre_groups[k].append((b, part, j))
                post_pos[(b, part, j)] = pkey((c[0] + ox, c[1], c[2] + oz))

    for k, topos in topo_of_pos.items():
        fam = {G.TOPO_FAMILY.get(t) for t in topos}
        if any(f is not None for f in fam):
            kept_ground_pos.add(k)
        elif topos:
            kept_rock_pos.add(k)

    split, nonuniform, moved_groups = [], [], []
    for k, ents in pre_groups.items():
        outs = {post_pos[e] for e in ents}
        if len(outs) != 1:
            split.append(dict(pre=list(k), n_entries=len(ents), post=[list(o) for o in sorted(outs)]))
            continue
        out_k = next(iter(outs))
        deltas = {round(post_pos[e][1] - k[1], 6) for e in ents}
        if len(deltas) != 1:
            nonuniform.append(dict(pre=list(k), n_entries=len(ents), deltas=sorted(deltas)))
        if out_k != k:
            kind = ("carried-ground" if k in kept_ground_pos else
                    "carried-rock" if k in kept_rock_pos else "fill-or-other")
            moved_groups.append(dict(pre=list(k), post=list(out_k), dY=round(out_k[1] - k[1], 4),
                                     n_entries=len(ents), kind=kind, r_crater=round(rc(k), 3),
                                     parts=sorted({e[1] for e in ents})))

    kind_hist = Counter(g["kind"] for g in moved_groups)
    basin_moved = [g for g in moved_groups if g["r_crater"] <= BASIN_R]
    min_r = min((g["r_crater"] for g in moved_groups), default=None)

    out["weld_map"] = dict(
        n_distinct_positions_all_parts=len(pre_groups),
        n_kept_ground_positions=len(kept_ground_pos), n_kept_rock_positions=len(kept_rock_pos),
        groups_that_split=len(split), split_examples=split[:10],
        groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:10],
        n_moved_groups=len(moved_groups),
        moved_kind_hist=dict(sorted(kind_hist.items())),
        moved_groups=sorted(moved_groups, key=lambda g: -abs(g["dY"])),
        min_r_crater_of_a_moved_group=round(min_r, 3) if min_r is not None else None,
        basin_radius_u=BASIN_R, basin_disc_moved_groups=len(basin_moved),
        weld_ok=(not split and not nonuniform))
    log(f"[4] positions={len(pre_groups)} split={len(split)} nonuniform={len(nonuniform)} "
        f"moved_groups={len(moved_groups)} kind_hist={dict(kind_hist)} "
        f"min_r_crater={min_r} basin_moved={len(basin_moved)}")

    ok = bool(
        out["tree_diff"]["counts_match_180"]
        and out["tree_diff"]["all_changed_are_terrain"]
        and out["tree_diff"]["all_changed_are_disc1"]
        and out["byte_checks"]["uv_files_differing"] == 0
        and out["byte_checks"]["tan_files_differing"] == 0
        and out["byte_checks"]["idx_files_differing"] == 0
        and out["byte_checks"]["vcount_files_differing"] == 0
        and out["byte_checks"]["xz_moved_vertex_entries"] == 0
        and out["byte_checks"]["flat_mesh_ok"]
        and out["byte_checks"]["newly_down_facing"] == 0
        and out["byte_checks"]["new_degenerate"] == 0
        and out["weld_map"]["weld_ok"]
        and out["weld_map"]["basin_disc_moved_groups"] == 0
        and len(moved_groups) > 0)
    out["CONFIRMED"] = ok
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    log(f"\n{'=' * 80}\nCONFIRMED={ok}  wrote {OUT}")
    return out


if __name__ == "__main__":
    main()
