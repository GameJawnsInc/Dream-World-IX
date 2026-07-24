"""RUNG F -- UV-FIX round 2 (2026-07-24): DISSOLVE THE QUILT.

Round 1 (uvf_fix.py -> ...FF9CustomMap-world-FIXED) killed all 2305 UV-degenerate Terrain tris and
restored the 6 blob Sea4 planes, but the per-pixel eye found the repaired hole-fill zone reads as a
strong regular diamond/chevron MOSAIC with visible per-cell tile boundaries -- while the surrounding
lawful frame-mint grass (build_landmass output, in-game-proven class) renders smoothly in the SAME
image. Cause: round 1 resolved the 923 FULLY-DROPPED cells (no surviving lawful tri) via
interior.decode_cell_pick, whose (quad,ori) choices carry visible spatial order.

THE MECHANISM (see the module docstring at bottom of the report):
  * decode_cell_pick picks ORIENTATION uniformly at random per cell (ORIS[randrange(4)]) with ZERO
    neighbour coupling -> adjacent cells almost never share a texture orientation -> every cell edge is
    an orientation discontinuity = the visible per-cell tile boundaries / chevrons.
  * grassland.assign_mains (build_landmass' OWN generator) COPIES a neighbour's rotation with p=0.32
    (real same-rotation 49%) -> large coherent same-orientation patches -> texture flows continuously
    across cell boundaries = smooth.
  * decode_cell_pick ALSO avoids BOTH W AND S neighbour quads (set-union) -> over-constrained -> a
    regular alternating (diamond) quad lattice; assign_mains avoids only ONE randomly-chosen neighbour
    quad (real same-quad 12%) -> organic quad patches.

FIX v2: IDENTICAL pipeline to uvf_fix.py (same classifier -> same 2305 tris, same apron-normal
recompute, same Sea4 restore, same centroid-cell fallback for the 58 lattice-corner tris) EXCEPT the
(quad,ori) resolution for the 923 dropped cells is done through the PROVEN assign_mains policy.
assign_mains does NOT accept a pre-assigned/constraint map (read its source: it builds cell_quad/cell_ori
fresh from an empty dict), so we MIRROR its body EXACTLY -- single Mersenne-Twister stream, W/S
single-neighbour quad-avoid, p=0.32 rotation-copy -- but PRE-SEED cell_quad/cell_ori with the 90
method-(a) neighbour-decoded cells (ground truth, never overwritten) so the dropped cells honour the
FIXED boundary via anti-repeat. Seed 0xF92 (deterministic; distinct from assign_mains' 0xF91 default
and decode_cell_pick's 0xF91 so the streams don't alias). Iterate sorted(dropped): every W=(i-1,j)/
S=(i,j-1) neighbour is lexicographically smaller -> already resolved (method-a pre-seed or earlier
dropped) -> exact assign_mains semantics.

Emits ...FF9CustomMap-world-FIXED2 (full 180-file tree). Self-checks: post-fix defective==0; diff vs
FIXED = UV-only, confined to tris whose cells re-resolved (normals/positions/tangents/indices identical
to FIXED, Sea4 identical to FIXED); diff vs the specimen = the round-1 contract (positions/topology/
indices identical everywhere, carried-core + lawful frame-mint byte-identical, only 22 files changed:
16 Terrain + 6 Sea4). Plus a spatial-autocorrelation texture-variety metric (v1-repaired vs v2-repaired
vs frame-mint reference). READ-ONLY vs the game install.
"""
from __future__ import annotations
import hashlib
import json
import math
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                       # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import grassland as G                     # noqa: E402
from ff9mapkit.world import interior as I                      # noqa: E402

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN
CELL = 4.0
UV_EPS = 1e-6
AREA_EPS = 1e-6
DECODE_ERR = 1e-4
V2_SEED = 0xF92

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED = RUNG_F / "FF9CustomMap-world-FIXED"           # round-1 output (A/B baseline; never modified)
FIXED2 = RUNG_F / "FF9CustomMap-world-FIXED2"          # this round's output
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
REPORT = RUNG_F / "uvf_fix2_report.json"


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def terr_path(root, bx, by):
    return Path(root) / M.override_relpath(1, bx, by, part="Terrain")


def sea4_path(root, bx, by):
    return Path(root) / M.override_relpath(1, bx, by, part="Sea4")


def uv_degenerate(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    same01 = abs(u0 - u1) < UV_EPS and abs(v0 - v1) < UV_EPS
    same02 = abs(u0 - u2) < UV_EPS and abs(v0 - v2) < UV_EPS
    same12 = abs(u1 - u2) < UV_EPS and abs(v1 - v2) < UV_EPS
    if same01 and same02 and same12:
        return True
    area = abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5
    return area < AREA_EPS


def uv_tri_degen(uv3):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5 < AREA_EPS


def decode_quad_ori(cell, verts_world, uv3):
    """Brute-force the 16 (quad,ori) combos against grassland.mains_uv (identical to uvf_fix.py)."""
    best = None
    for uh in (0, 1):
        for vh in (0, 1):
            quad = (uh, vh)
            for ori in G.ORIS:
                maxerr = 0.0
                for (vx, _vy, vz), (su, sv) in zip(verts_world, uv3):
                    mu, mv = G.mains_uv(vx, vz, cell, quad, ori)
                    e = math.hypot(mu - su, mv - sv)
                    if e > maxerr:
                        maxerr = e
                    if maxerr >= DECODE_ERR:
                        break
                if best is None or maxerr < best[0]:
                    best = (maxerr, quad, ori)
    if best is not None and best[0] < DECODE_ERR:
        return best[1], best[2]
    return None


def assign_mains_seeded(dropped_cells, pre_quad, pre_ori, seed=V2_SEED):
    """A VERBATIM mirror of grassland.assign_mains' loop body (single random.Random stream, W/S
    single-neighbour quad-avoid, p=0.32 rotation-copy) applied ONLY to the dropped cells, with
    cell_quad/cell_ori PRE-SEEDED by the method-(a) ground-truth cells (never overwritten -- they are
    not in dropped_cells). Because every W=(i-1,j)/S=(i,j-1) is lexicographically smaller than (i,j),
    each neighbour is already resolved (pre-seed or earlier dropped) when a cell is drawn -> exact
    assign_mains semantics extended to a constrained boundary. Returns quad/ori dicts for the dropped."""
    rng = random.Random(seed)
    cell_quad = dict(pre_quad)     # method-(a) boundary; consulted for anti-repeat, never rewritten
    cell_ori = dict(pre_ori)
    out_quad, out_ori = {}, {}
    for (i, j) in sorted(dropped_cells):
        nb_q = [cell_quad[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_quad]
        choices = [(u, v) for u in (0, 1) for v in (0, 1)]
        if nb_q:
            avoid = nb_q[rng.randrange(len(nb_q))]
            choices = [q for q in choices if q != avoid]
        q = choices[rng.randrange(len(choices))]
        cell_quad[(i, j)] = q
        out_quad[(i, j)] = q
        nb_o = [cell_ori[n] for n in ((i - 1, j), (i, j - 1)) if n in cell_ori]
        if nb_o and rng.random() < 0.32:
            o = nb_o[rng.randrange(len(nb_o))]
        else:
            o = G.ORIS[rng.randrange(4)]
        cell_ori[(i, j)] = o
        out_ori[(i, j)] = o
    return out_quad, out_ori


def adjacency_stats(cells_qo):
    """Spatial-autocorrelation texture-variety metric over a cell->(quad,ori) map. Reports, over all
    within-set E-adjacent (i,j)-(i+1,j) and N-adjacent (i,j)-(i,j+1) cell pairs: the fraction that
    share the same QUADRANT and the same ORIENTATION. A chevron/quilt (uniform-random per-cell ori,
    over-avoided quads) shows low same-ori (~0.25) + a rigid/low same-quad; the smooth frame-mint
    (assign_mains, real map) shows high same-ori (~0.49) + moderate same-quad (~0.12)."""
    same_q = same_o = n_pairs = 0
    for (i, j), (q, o) in cells_qo.items():
        for n in ((i + 1, j), (i, j + 1)):
            if n in cells_qo:
                q2, o2 = cells_qo[n]
                n_pairs += 1
                if q == q2:
                    same_q += 1
                if o == o2:
                    same_o += 1
    return dict(n_pairs=n_pairs,
                same_quad_rate=round(same_q / n_pairs, 4) if n_pairs else None,
                same_ori_rate=round(same_o / n_pairs, 4) if n_pairs else None,
                n_cells=len(cells_qo))


def main():
    report = {"meta": {"script": "uvf_fix2.py", "read_only_vs_game": True, "v2_seed": V2_SEED,
                       "spec_tree": str(SPEC), "fixed_tree": str(FIXED), "fixed2_tree": str(FIXED2)}}

    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    report["meta"]["n_touched_blocks"] = len(touched)
    assert len(touched) == 20, f"expected 20 touched blocks, got {len(touched)}"

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = set()
    fx_degen_per_block = Counter()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area":
            fx_degen_per_block[tuple(rec["block"])] += 1
            if rec["provenance"] == "apron":
                cx, _cy, cz = rec["centroid"]
                apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))
    log(f"forensics degenerate total={sum(fx_degen_per_block.values())} apron keys={len(apron_keys)}")

    # ---- copy the SPECIMEN tree (full) -> FIXED2 -----------------------------------------------
    if FIXED2.exists():
        shutil.rmtree(FIXED2)
    shutil.copytree(SPEC, FIXED2)
    n_copied = sum(1 for _ in FIXED2.rglob("*") if _.is_file())
    n_spec = sum(1 for _ in SPEC.rglob("*") if _.is_file())
    report["meta"]["files_copied"] = n_copied
    assert n_copied == n_spec == 180, f"copy mismatch {n_copied} != {n_spec}"
    log(f"copied {n_copied} files -> {FIXED2}")

    # ---- load all 20 blocks; classify defective tris (identical to uvf_fix.py) -----------------
    block_meshes = {}
    defective = []
    lawful_grass = []
    per_block_defect = Counter()
    topo_nonzero_defect = 0
    for (bx, by) in touched:
        p = terr_path(FIXED2, bx, by)
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        block_meshes[(bx, by)] = bm
        assert bm.vcount == 3 * len(bm.tris) == len(bm.verts), f"{bx},{by} not flat"
        assert bm.flat_index == list(range(bm.vcount)), f"{bx},{by} flat_index not range"
        ox, oz = X.block_world_origin(bx, by)
        verts = bm.chan_arrays[CH_POS]
        uvs = bm.chan_arrays[CH_UV]
        tans = bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            j0, j1, j2 = tri
            vw = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in (j0, j1, j2)]
            uv3 = [(uvs[j][0], uvs[j][1]) for j in (j0, j1, j2)]
            topo = X.decode_id(int(round(tans[j0][0])))["topograph"]
            if uv_degenerate(uv3):
                if topo != 0:
                    topo_nonzero_defect += 1
                cx = sum(v[0] for v in vw) / 3.0
                cz = sum(v[2] for v in vw) / 3.0
                key = ((bx, by), round(cx, 3), round(cz, 3))
                defective.append(dict(block=(bx, by), tri=t, vids=(j0, j1, j2), vw=vw,
                                      is_apron=(key in apron_keys)))
                per_block_defect[(bx, by)] += 1
            elif topo == 0:
                cx = sum(v[0] for v in vw) / 3.0
                cz = sum(v[2] for v in vw) / 3.0
                cell = (math.floor(cx / CELL), math.floor(cz / CELL))
                lawful_grass.append((cell, vw, uv3))

    n_def = len(defective)
    log(f"classified defective={n_def} (expected 2305); topo!=0 among defective={topo_nonzero_defect}")
    assert n_def == 2305, f"defective count {n_def} != 2305"
    assert topo_nonzero_defect == 0
    n_apron = sum(1 for d in defective if d["is_apron"])
    assert n_apron == 321, f"apron match {n_apron} != 321"
    report["classification"] = dict(n_defective=n_def, apron=n_apron,
                                    per_block={f"{b[0]},{b[1]}": per_block_defect[b] for b in touched})

    # ---- target cell set (per defective VERTEX) + centroid cells (for the lattice-corner fallback)
    target_cells = set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add((math.floor(vx / CELL), math.floor(vz / CELL)))
    centroid_cells = set()
    for d in defective:
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        centroid_cells.add((math.floor(cx / CELL), math.floor(cz / CELL)))
    resolve_cells = target_cells | centroid_cells
    log(f"target cells={len(target_cells)} centroid cells={len(centroid_cells)} "
        f"union(resolve)={len(resolve_cells)}")

    # ---- method (a): neighbour-decode from a lawful same-cell tri (IDENTICAL to uvf_fix.py) -----
    decoded_a = {}       # cell -> (quad, ori)  (ground truth, 90 target + more)
    a_conflicts = 0
    by_cell = defaultdict(list)
    for (cell, vw, uv3) in lawful_grass:
        by_cell[cell].append((vw, uv3))
    for cell in sorted(by_cell):
        got = None
        for (vw, uv3) in by_cell[cell]:
            qo = decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                if got is None:
                    got = qo
                elif got != qo:
                    a_conflicts += 1
                break
        if got is not None:
            decoded_a[cell] = got
    n_a = len(decoded_a)
    log(f"method (a) decoded cells = {n_a} (a_conflicts={a_conflicts})")
    assert a_conflicts == 0

    # ---- dropped cells = resolve set with NO surviving lawful tri ------------------------------
    dropped = sorted(c for c in resolve_cells if c not in decoded_a)
    log(f"dropped cells (no lawful tri, resolved via assign_mains policy) = {len(dropped)}")

    # ============================================================================================
    #   THE DIAGNOSIS DIFF: reconstruct round-1's decode_cell_pick resolution for the same dropped
    #   set (method-(a) seed identical), so we can count cells_reresolved + compare autocorrelation.
    # ============================================================================================
    # Reproduce uvf_fix.py's EXACT resolution ORDER: sorted(target_cells) first (the method-b loop),
    # then the centroid-only cells on-demand (the cell_qo fallback). decode_cell_pick's avoid-set
    # depends on which W/S neighbours are already in the running dict, so ORDER matters -> this mirrors
    # what FIXED actually baked, giving an honest cells_reresolved count on the 1013 target cells.
    decoded_r1 = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for cell in sorted(target_cells):
        if cell in decoded_r1:
            continue
        (q, o) = I.decode_cell_pick(cell, decoded_r1)
        decoded_r1[cell] = (q, o, "b")
    for cell in sorted(set(dropped) - set(target_cells)):   # centroid-only cells (added on-demand)
        if cell in decoded_r1:
            continue
        (q, o) = I.decode_cell_pick(cell, decoded_r1)
        decoded_r1[cell] = (q, o, "b")
    r1_dropped_qo = {c: (decoded_r1[c][0], decoded_r1[c][1]) for c in dropped}

    # ---- v2 resolution: assign_mains policy, pre-seeded with method-(a) boundary ----------------
    pre_quad = dict(decoded_a)
    pre_ori = {c: o for c, (q, o) in decoded_a.items()}
    v2_quad, v2_ori = assign_mains_seeded(dropped, pre_quad, pre_ori)
    v2_dropped_qo = {c: (v2_quad[c], v2_ori[c]) for c in dropped}

    # merged decode map for the APPLY: method-(a) truth + v2 for dropped
    decoded = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        decoded[c] = (v2_quad[c], v2_ori[c], "v2")

    # cells_reresolved = target cells whose (quad,ori) changed vs round 1 (method-a MUST be unchanged)
    n_changed = 0
    method_a_unchanged = True
    for c in sorted(target_cells):
        r1 = (decoded_r1[c][0], decoded_r1[c][1])
        v2 = (decoded[c][0], decoded[c][1])
        if c in decoded_a:                 # method-(a) cell
            if r1 != v2 or decoded[c][2] != "a":
                method_a_unchanged = False
        else:                              # dropped cell
            if r1 != v2:
                n_changed += 1
    log(f"target cells={len(target_cells)}  method-a among target={sum(1 for c in target_cells if c in decoded_a)}"
        f"  dropped among target={sum(1 for c in target_cells if c not in decoded_a)}  re-resolved={n_changed}")
    report["decode"] = dict(n_cells_method_a_total=n_a, a_conflicts=a_conflicts,
                            n_target_cells=len(target_cells),
                            n_target_method_a=sum(1 for c in target_cells if c in decoded_a),
                            n_target_dropped=sum(1 for c in target_cells if c not in decoded_a),
                            n_dropped_total=len(dropped),
                            cells_reresolved_vs_r1=n_changed,
                            method_a_unchanged=method_a_unchanged)
    assert method_a_unchanged, "method-(a) ground-truth cells changed -- must be preserved"

    def cell_qo(cell):
        if cell not in decoded:            # every resolve-set cell is present; guard is defensive
            q, o = v2_quad.get(cell, (None, None)), v2_ori.get(cell)
            assert q is not None, f"cell {cell} not resolved"
            decoded[cell] = (q, o, "v2")
        return decoded[cell][0], decoded[cell][1]

    # ---- APPLY: rewrite UVs (per defective vertex) + apron normals (IDENTICAL to uvf_fix.py) ----
    uv_changed_vids = defaultdict(set)
    nrm_changed_vids = defaultdict(set)
    apron_normal_tris = 0
    n_centroid_fallback = 0
    # CONTAINMENT set = every dropped cell (all re-resolved by the new assign_mains policy vs
    # decode_cell_pick). A defective tri touching only method-(a) cells decodes identical ground truth
    # in v1 and v2 -> byte-identical UV; only tris touching a dropped cell may differ from FIXED. This
    # is the provable invariant (independent of the decode_cell_pick reconstruction fidelity). The
    # STRICT changed-subset is reported separately as n_changed_qo for information.
    reresolved_cell_set = set(dropped)
    n_changed_qo = sum(1 for c in dropped if r1_dropped_qo[c] != v2_dropped_qo[c])
    for d in defective:
        (bx, by) = d["block"]
        bm = block_meshes[(bx, by)]
        uvs = bm.chan_arrays[CH_UV]
        new_uv = []
        for (vx, _vy, vz) in d["vw"]:
            cell = (math.floor(vx / CELL), math.floor(vz / CELL))
            quad, ori, _m = decoded[cell]
            new_uv.append(list(G.ground_uv(vx, vz, cell, quad, ori, "grass")))
        if uv_tri_degen(new_uv):
            cx = sum(p[0] for p in d["vw"]) / 3.0
            cz = sum(p[2] for p in d["vw"]) / 3.0
            ccell = (math.floor(cx / CELL), math.floor(cz / CELL))
            quad, ori = cell_qo(ccell)
            new_uv = [list(G.ground_uv(vx, vz, ccell, quad, ori, "grass"))
                      for (vx, _vy, vz) in d["vw"]]
            d["centroid_fallback"] = True
            n_centroid_fallback += 1
        else:
            d["centroid_fallback"] = False
        for j, uv in zip(d["vids"], new_uv):
            uvs[j] = uv
            uv_changed_vids[(bx, by)].add(j)
        if d["is_apron"]:
            nrm = bm.chan_arrays[CH_NRM]
            a, b, c = d["vw"]
            e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
            e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]]
            n = [e1[1] * e2[2] - e1[2] * e2[1],
                 e1[2] * e2[0] - e1[0] * e2[2],
                 e1[0] * e2[1] - e1[1] * e2[0]]
            if n[1] < 0.0:
                n = [-n[0], -n[1], -n[2]]
            ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
            nv = [n[0] / ln, n[1] / ln, n[2] / ln]
            for j in d["vids"]:
                nrm[j] = list(nv)
                nrm_changed_vids[(bx, by)].add(j)
            apron_normal_tris += 1
    log(f"apron normals recomputed on {apron_normal_tris} tris; centroid-cell fallback tris={n_centroid_fallback}")
    report["apply"] = dict(apron_normal_tris=apron_normal_tris,
                           uv_changed_verts=sum(len(s) for s in uv_changed_vids.values()),
                           nrm_changed_verts=sum(len(s) for s in nrm_changed_vids.values()),
                           n_centroid_cell_fallback_tris=n_centroid_fallback,
                           n_dropped_cells_reresolved=len(reresolved_cell_set),
                           n_dropped_qo_changed_vs_r1=n_changed_qo)

    # ---- WRITE the 20 Terrain files ------------------------------------------------------------
    written = {}
    for (bx, by) in touched:
        bm = block_meshes[(bx, by)]
        p = terr_path(FIXED2, bx, by)
        M.write_ff9mesh(bm, p)
        written[str(p.relative_to(FIXED2))] = sha256_file(p)

    # ---- SEA4: restore the full plane on the 6 blob blocks (IDENTICAL to uvf_fix.py) ------------
    blob_blocks = [tuple(b) for b in forensics["meta"]["cell_sets"]["blob_blocks"]]
    full_plane_shas = {}
    for (bx, by) in touched:
        if (bx, by) in blob_blocks:
            continue
        full_plane_shas[(bx, by)] = sha256_file(sea4_path(FIXED2, bx, by))
    assert len(set(full_plane_shas.values())) == 1, "non-blob Sea4 files not byte-identical"
    donor_blk = next(iter(full_plane_shas))
    donor_bytes = sea4_path(FIXED2, *donor_blk).read_bytes()
    dp = M.read_ff9mesh(sea4_path(FIXED2, *donor_blk))
    assert all(abs(v[1]) <= 1e-4 for v in dp["verts"]), "donor plane Y!=0"
    sea4_written = []
    for (bx, by) in blob_blocks:
        p = sea4_path(FIXED2, bx, by)
        p.write_bytes(donor_bytes)
        sea4_written.append([bx, by])
        written[str(p.relative_to(FIXED2))] = sha256_file(p)
    report["sea4"] = dict(blob_blocks=[list(b) for b in blob_blocks], donor_block=list(donor_blk),
                          donor_sha=sha256_file(sea4_path(FIXED2, *donor_blk))[:16],
                          donor_vcount=dp["vcount"], written=sea4_written)
    log(f"Sea4 restored on {len(sea4_written)} blob blocks (donor {donor_blk})")
    report["written_files_sha256"] = written

    # ============================================================================================
    #                                 SELF-CHECK / VERIFICATION
    # ============================================================================================
    verify = {}

    # (1) re-scan FIXED2 -> defective MUST be 0
    post_def = 0
    for (bx, by) in touched:
        bm = M.blockmesh_from_ff9mesh(terr_path(FIXED2, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for tri in bm.tris:
            uv3 = [(uvs[j][0], uvs[j][1]) for j in tri]
            if uv_degenerate(uv3):
                post_def += 1
    verify["post_fix_defective_count"] = post_def
    log(f"[verify] post-fix defective count = {post_def} (MUST be 0)")

    # (2) rewritten UVs inside grass mains region
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    tol = 1e-6
    out_of_region = 0
    for (bx, by), vids in uv_changed_vids.items():
        bm = M.blockmesh_from_ff9mesh(terr_path(FIXED2, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for j in vids:
            u, v = uvs[j]
            if not (lo_u - tol <= u <= hi_u + tol and lo_v - tol <= v <= hi_v + tol):
                out_of_region += 1
    verify["rewritten_uv_out_of_grass_region"] = out_of_region

    # (3) BYTE-RIGIDITY vs the SPECIMEN (round-1 contract): pos/tan/idx identical everywhere; uv only
    #     at uv_changed_vids; nrm only at nrm_changed_vids.
    rig = dict(pos_bad=0, tan_bad=0, idx_bad=0, uv_unexpected=0, uv_expected_changed=0,
               nrm_unexpected=0, nrm_expected_changed=0, files=len(touched))
    for (bx, by) in touched:
        s = M.read_ff9mesh(terr_path(SPEC, bx, by))
        f = M.read_ff9mesh(terr_path(FIXED2, bx, by))
        if s["indices"] != f["indices"]:
            rig["idx_bad"] += 1
        if s["verts"] != f["verts"]:
            rig["pos_bad"] += 1
        if s["tangents"] != f["tangents"]:
            rig["tan_bad"] += 1
        chg_uv = uv_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["uvs"][j] != f["uvs"][j]:
                rig["uv_expected_changed" if j in chg_uv else "uv_unexpected"] += 1
        chg_n = nrm_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["normals"][j] != f["normals"][j]:
                rig["nrm_expected_changed" if j in chg_n else "nrm_unexpected"] += 1
    verify["byte_rigidity_vs_specimen"] = rig
    log(f"[verify] rigidity vs specimen: pos_bad={rig['pos_bad']} tan_bad={rig['tan_bad']} "
        f"idx_bad={rig['idx_bad']} uv_unexpected={rig['uv_unexpected']} nrm_unexpected={rig['nrm_unexpected']}")

    # (3b) file-count contract vs specimen: exactly 22 files differ (16 Terrain + 6 Sea4) -----------
    changed_files, changed_terr, changed_sea4 = [], 0, 0
    for rel in [str(pp.relative_to(SPEC)) for pp in SPEC.rglob("*.ff9mesh")]:
        a = sha256_file(SPEC / rel)
        b = sha256_file(FIXED2 / rel)
        if a != b:
            changed_files.append(rel)
            if "Terrain" in rel:
                changed_terr += 1
            elif "Sea4" in rel:
                changed_sea4 += 1
    verify["specimen_diff"] = dict(n_changed=len(changed_files), n_terrain=changed_terr,
                                   n_sea4=changed_sea4, files=sorted(changed_files))
    log(f"[verify] specimen diff: {len(changed_files)} files ({changed_terr} Terrain + {changed_sea4} Sea4)")

    # (4) DIFF vs FIXED (round 1): UV-ONLY, confined to tris whose cell re-resolved. pos/tan/idx/nrm
    #     byte-identical to FIXED; Sea4 identical to FIXED; every differing UV vertex belongs to a
    #     defective tri that touches a re-resolved cell.
    dv = dict(terr_pos_bad=0, terr_tan_bad=0, terr_idx_bad=0, terr_nrm_bad=0,
              uv_diff_verts=0, uv_diff_in_reresolved=0, uv_diff_outside_reresolved=0,
              sea4_diff_files=0)

    def tri_cells(bm, t):
        """the cells a tri's UV can depend on: its 3 vertex cells + its centroid cell."""
        tri = bm.tris[t]
        verts = bm.chan_arrays[CH_POS]
        ox, oz = X.block_world_origin(bx, by)
        cs = set()
        cx = cz = 0.0
        for j in tri:
            wx, wz = verts[j][0] + ox, verts[j][2] + oz
            cs.add((math.floor(wx / CELL), math.floor(wz / CELL)))
            cx += wx
            cz += wz
        cs.add((math.floor((cx / 3.0) / CELL), math.floor((cz / 3.0) / CELL)))
        return cs

    for (bx, by) in touched:
        f1 = M.read_ff9mesh(terr_path(FIXED, bx, by))
        f2 = M.read_ff9mesh(terr_path(FIXED2, bx, by))
        if f1["verts"] != f2["verts"]:
            dv["terr_pos_bad"] += 1
        if f1["tangents"] != f2["tangents"]:
            dv["terr_tan_bad"] += 1
        if f1["indices"] != f2["indices"]:
            dv["terr_idx_bad"] += 1
        if f1["normals"] != f2["normals"]:
            dv["terr_nrm_bad"] += 1
        bm = block_meshes[(bx, by)]
        for j in range(f1["vcount"]):
            if f1["uvs"][j] != f2["uvs"][j]:
                dv["uv_diff_verts"] += 1
                t = j // 3
                cs = tri_cells(bm, t)
                if cs & reresolved_cell_set:
                    dv["uv_diff_in_reresolved"] += 1
                else:
                    dv["uv_diff_outside_reresolved"] += 1
    for (bx, by) in touched:
        if sha256_file(sea4_path(FIXED, bx, by)) != sha256_file(sea4_path(FIXED2, bx, by)):
            dv["sea4_diff_files"] += 1
    verify["diff_vs_fixed"] = dv
    log(f"[verify] vs FIXED: pos_bad={dv['terr_pos_bad']} tan_bad={dv['terr_tan_bad']} "
        f"idx_bad={dv['terr_idx_bad']} nrm_bad={dv['terr_nrm_bad']} sea4_diff={dv['sea4_diff_files']} "
        f"uv_diff={dv['uv_diff_verts']} (in_reresolved={dv['uv_diff_in_reresolved']} "
        f"outside={dv['uv_diff_outside_reresolved']})")

    # (5) flat-mesh invariant + Sea4 uniform
    flat_bad = []
    for rel in written:
        d = M.read_ff9mesh(FIXED2 / rel)
        if not (d["vcount"] == len(d["indices"]) == len(d["verts"]) and len(d["indices"]) % 3 == 0):
            flat_bad.append(rel)
    verify["flat_mesh_bad_written_files"] = flat_bad
    sea4_shas_post = {sha256_file(sea4_path(FIXED2, *b))[:16] for b in touched}
    verify["all_sea4_uniform_post"] = (len(sea4_shas_post) == 1)

    # ============================================================================================
    #   TEXTURE-VARIETY METRIC: spatial autocorrelation, v1-repaired vs v2-repaired vs frame-mint
    # ============================================================================================
    v1_stats = adjacency_stats(r1_dropped_qo)                       # the quilt
    v2_stats = adjacency_stats(v2_dropped_qo)                       # the fix
    frame_cells = {c: (q, o) for c, (q, o) in decoded_a.items() if c not in target_cells}
    frame_stats = adjacency_stats(frame_cells)                     # smooth reference (build_landmass/carry)
    verify["texture_variety"] = dict(
        v1_repaired_decode_cell_pick=v1_stats,
        v2_repaired_assign_mains=v2_stats,
        frame_mint_reference=frame_stats,
        note=("same_ori_rate is the discriminator: decode_cell_pick draws orientation uniformly per "
              "cell with NO neighbour coupling (~0.25 = the chevron), assign_mains copies a neighbour's "
              "rotation p=0.32 -> ~0.49 clustering matching the frame-mint reference; v2 should track the "
              "frame, v1 does not."))
    log(f"[metric] same_ori v1={v1_stats['same_ori_rate']} v2={v2_stats['same_ori_rate']} "
        f"frame={frame_stats['same_ori_rate']} | same_quad v1={v1_stats['same_quad_rate']} "
        f"v2={v2_stats['same_quad_rate']} frame={frame_stats['same_quad_rate']}")

    report["verify"] = verify
    report["ok"] = (post_def == 0 and out_of_region == 0 and not flat_bad
                    and rig["pos_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0
                    and rig["uv_unexpected"] == 0 and rig["nrm_unexpected"] == 0
                    and verify["all_sea4_uniform_post"]
                    and len(changed_files) == 22 and changed_terr == 16 and changed_sea4 == 6
                    and dv["terr_pos_bad"] == 0 and dv["terr_tan_bad"] == 0 and dv["terr_idx_bad"] == 0
                    and dv["terr_nrm_bad"] == 0 and dv["sea4_diff_files"] == 0
                    and dv["uv_diff_outside_reresolved"] == 0
                    and method_a_unchanged)

    report["diagnosis"] = dict(
        decode_cell_pick=("interior.py:332 -- per-cell fresh random.Random seeded on a spatial hash; "
                          "ORIENTATION = ORIS[randrange(4)] UNIFORM with ZERO neighbour coupling "
                          "(adjacent cells rarely share orientation -> every cell edge is a texture-"
                          "orientation discontinuity = visible per-cell tile boundaries / chevrons); "
                          "QUAD avoids the SET-UNION of BOTH W and S neighbour quads -> over-"
                          "constrained -> a regular alternating (diamond) quad lattice."),
        assign_mains=("grassland.py:273 (build_landmass' OWN generator) -- ONE random.Random stream in "
                      "raster order; ORIENTATION copies a neighbour's rotation with p=0.32 (real same-"
                      "rotation 49%) -> large coherent same-orientation patches -> texture flows across "
                      "cell boundaries = smooth; QUAD avoids only ONE randomly-chosen neighbour quad "
                      "(real same-quad 12%) -> organic patches. Does NOT accept a pre-assigned map; v2 "
                      "MIRRORS the loop verbatim, pre-seeding cell_quad/cell_ori with the method-(a) "
                      "boundary, seed 0xF92."))

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"OK={report['ok']}  post_def={post_def}  reresolved={n_changed}  -> {REPORT}")
    return report


if __name__ == "__main__":
    main()
