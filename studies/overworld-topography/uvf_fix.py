"""RUNG F -- UV-FIX round (2026-07-24).

Pure UV (+ selective apron-normal) rewrite of the staged RUNG F build, GEOMETRY BYTE-PRESERVED.
The forensics round CONFIRMED 2305/6996 staged Terrain tris are UV-DEGENERATE (all 3 vertex UVs
collapsed to a single point -> a real 7-25u2 world tri samples one texel -> the playtest's flat
solid-green sheets). This script:

  * copies the specimen tree -> ...FF9CustomMap-world-FIXED (never touches the specimen),
  * classifies every Terrain tri (defective = 3 vertex UVs identical <1e-6 OR uv-tri area <1e-6),
  * per defective vertex, rewrites uv = grassland.ground_uv(vx,vz, cell, quad, ori, "grass") with the
    cell's (quad,ori) recovered by (a) neighbour-decode from a lawful same-cell tri, else (b) the
    interior decode-pick honouring the W/S anti-repeat, else (c) assign_mains(seed=0xF91),
  * recomputes geometric up-facing normals on the 321 apron (tiling-annulus) tris ONLY,
  * restores the full Sea4 plane on the 6 blob blocks (byte-copy of the 14 uniform block-local planes),
  * records everything to out/rung_f/uvf_fix_report.json and self-checks post-fix defective == 0 +
    byte-rigidity of every untouched tri + the flat-mesh invariant on every written file.

Geometry (vcount / flat_index / positions / tangents) stays byte-identical everywhere; the carried-core
(1454) and lawful frame-mint (3237) tris are never touched. READ-ONLY vs the game install.
"""
from __future__ import annotations
import hashlib
import json
import math
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

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED = RUNG_F / "FF9CustomMap-world-FIXED"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
REPORT = RUNG_F / "uvf_fix_report.json"


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def terr_path(root, bx, by):
    return Path(root) / M.override_relpath(1, bx, by, part="Terrain")


def sea4_path(root, bx, by):
    return Path(root) / M.override_relpath(1, bx, by, part="Sea4")


def uv_degenerate(uv3):
    """True iff the 3 UVs are bit-identical within UV_EPS OR the UV-triangle area < AREA_EPS."""
    (u0, v0), (u1, v1), (u2, v2) = uv3
    same01 = abs(u0 - u1) < UV_EPS and abs(v0 - v1) < UV_EPS
    same02 = abs(u0 - u2) < UV_EPS and abs(v0 - v2) < UV_EPS
    same12 = abs(u1 - u2) < UV_EPS and abs(v1 - v2) < UV_EPS
    if same01 and same02 and same12:
        return True
    area = abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5
    return area < AREA_EPS


def decode_quad_ori(cell, verts_world, uv3):
    """Brute-force the 16 (quad, ori) combos against grassland.mains_uv for this lawful tri (all 3 verts
    with the tri's centroid CELL, matching how build_landmass generated it). Returns (quad, ori) with
    max per-vertex UV err < DECODE_ERR, else None."""
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


def main():
    report = {"meta": {"script": "uvf_fix.py", "read_only_vs_game": True,
                       "spec_tree": str(SPEC), "fixed_tree": str(FIXED)}}

    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    DY = build["compose_diag"]["DY"]
    report["meta"]["n_touched_blocks"] = len(touched)
    report["meta"]["DY"] = DY
    log(f"touched blocks={len(touched)} DY={DY}")
    assert len(touched) == 20, f"expected 20 touched blocks, got {len(touched)}"

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    # apron authority: forensics degenerate 'apron' records, keyed by (block, round(cx,3), round(cz,3))
    apron_keys = set()
    fx_degen_per_block = Counter()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area":
            fx_degen_per_block[tuple(rec["block"])] += 1
            if rec["provenance"] == "apron":
                cx, _cy, cz = rec["centroid"]
                apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))
    report["meta"]["forensics_degenerate_total"] = sum(fx_degen_per_block.values())
    report["meta"]["forensics_apron_keys"] = len(apron_keys)
    log(f"forensics degenerate total={sum(fx_degen_per_block.values())} apron keys={len(apron_keys)}")

    # ---- copy the specimen tree (full) ---------------------------------------------------------
    if FIXED.exists():
        shutil.rmtree(FIXED)
    shutil.copytree(SPEC, FIXED)
    n_copied = sum(1 for _ in FIXED.rglob("*") if _.is_file())
    n_spec = sum(1 for _ in SPEC.rglob("*") if _.is_file())
    report["meta"]["files_copied"] = n_copied
    report["meta"]["files_in_specimen"] = n_spec
    assert n_copied == n_spec, f"copy mismatch {n_copied} != {n_spec}"
    log(f"copied {n_copied} files -> {FIXED}")

    # ---- load all 20 blocks; classify defective tris -------------------------------------------
    block_meshes = {}
    defective = []      # list of dicts: block, tri_idx, vids(j0,j1,j2), verts_world, centroid, is_apron
    lawful_grass = []   # (cell, verts_world, uv3) candidates for decode method (a)
    per_block_defect = Counter()
    topo_nonzero_defect = 0
    for (bx, by) in touched:
        p = terr_path(FIXED, bx, by)
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        block_meshes[(bx, by)] = bm
        # flat-mesh invariant + unindexed structure
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
                # lawful grass tri: candidate to decode its centroid cell (method a)
                cx = sum(v[0] for v in vw) / 3.0
                cz = sum(v[2] for v in vw) / 3.0
                cell = (math.floor(cx / CELL), math.floor(cz / CELL))
                lawful_grass.append((cell, vw, uv3))

    n_def = len(defective)
    log(f"classified defective={n_def} (expected 2305); topo!=0 among defective={topo_nonzero_defect}")
    report["classification"] = dict(n_defective=n_def, expected=2305,
                                    topo_nonzero_defective=topo_nonzero_defect,
                                    per_block={f"{b[0]},{b[1]}": per_block_defect[b] for b in touched})
    # cross-check per-block vs forensics
    mism = {f"{b[0]},{b[1]}": [per_block_defect[b], fx_degen_per_block[b]]
            for b in touched if per_block_defect[b] != fx_degen_per_block[b]}
    report["classification"]["per_block_mismatch_vs_forensics"] = mism
    assert n_def == 2305, f"defective count {n_def} != 2305"
    assert not mism, f"per-block mismatch vs forensics: {mism}"
    assert topo_nonzero_defect == 0, "some defective tri is not topo-0 grass"
    n_apron = sum(1 for d in defective if d["is_apron"])
    log(f"apron (tiling-annulus) defective matched via forensics centroid key = {n_apron} (expected 321)")
    assert n_apron == 321, f"apron match {n_apron} != 321"

    # ---- build the target cell set (per defective VERTEX) --------------------------------------
    target_cells = set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add((math.floor(vx / CELL), math.floor(vz / CELL)))
    log(f"target cells (from defective verts) = {len(target_cells)}")

    # ---- method (a): neighbour-decode from a lawful same-cell tri (centroid cell) --------------
    decoded = {}   # cell -> (quad, ori, method)
    a_conflicts = 0
    # group lawful candidates by centroid cell; decode each; require consistency
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
                break  # one successful decode per cell is enough
        if got is not None:
            decoded[cell] = (got[0], got[1], "a")
    n_a = len(decoded)
    log(f"method (a) decoded cells = {n_a}  (a_conflicts={a_conflicts})")

    # ---- method (b): interior decode-pick for target cells with no lawful tri ------------------
    n_b = n_c = 0
    for cell in sorted(target_cells):
        if cell in decoded:
            continue
        try:
            (quad, ori) = I.decode_cell_pick(cell, decoded)
            decoded[cell] = (quad, ori, "b")
            n_b += 1
        except Exception as e:                            # last-resort (c)
            cq, co = G.assign_mains({cell}, seed=0xF91)
            decoded[cell] = (cq[cell], co[cell], "c")
            n_c += 1
            log(f"  (c) fallback on {cell}: {e}")
    # tally how each TARGET cell was resolved
    method_of_target = Counter(decoded[c][2] for c in target_cells)
    log(f"target-cell resolution: (a)={method_of_target.get('a',0)} (b)={method_of_target.get('b',0)} "
        f"(c)={method_of_target.get('c',0)}")
    report["decode"] = dict(n_cells_method_a_total=n_a, a_conflicts=a_conflicts,
                            n_target_cells=len(target_cells),
                            target_by_method=dict(method_of_target))

    def uv_tri_degen(uv3):
        (u0, v0), (u1, v1), (u2, v2) = uv3
        return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) * 0.5 < AREA_EPS

    def cell_qo(cell):
        """(quad,ori) for a cell, decoding on demand via method (b) if not already known."""
        if cell not in decoded:
            decoded[cell] = (*I.decode_cell_pick(cell, decoded), "b")
        return decoded[cell][0], decoded[cell][1]

    # ---- APPLY: rewrite UVs (per defective vertex) + apron normals -----------------------------
    uv_changed_vids = defaultdict(set)
    nrm_changed_vids = defaultdict(set)
    apron_normal_tris = 0
    n_centroid_fallback = 0
    for d in defective:
        (bx, by) = d["block"]
        bm = block_meshes[(bx, by)]
        uvs = bm.chan_arrays[CH_UV]
        # PRIMARY: per-vertex own-cell ground_uv (spec item 4/6)
        new_uv = []
        for (vx, _vy, vz) in d["vw"]:
            cell = (math.floor(vx / CELL), math.floor(vz / CELL))
            quad, ori, _m = decoded[cell]
            new_uv.append(list(G.ground_uv(vx, vz, cell, quad, ori, "grass")))
        # FALLBACK: lattice-corner tris collapse under per-vertex own-cell (every vertex maps to its
        # cell ORIGIN). Re-assign via the tri's CENTROID cell -- the exact proven-island build_landmass
        # call (island.py:526-531) -- which spreads the 3 verts across distinct fractional corners.
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
            if n[1] < 0.0:                                # up-facing
                n = [-n[0], -n[1], -n[2]]
            ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
            nv = [n[0] / ln, n[1] / ln, n[2] / ln]
            for j in d["vids"]:
                nrm[j] = list(nv)
                nrm_changed_vids[(bx, by)].add(j)
            apron_normal_tris += 1
    log(f"apron normals recomputed on {apron_normal_tris} tris; "
        f"centroid-cell fallback tris={n_centroid_fallback}")
    report["apply"] = dict(apron_normal_tris=apron_normal_tris,
                           uv_changed_verts=sum(len(s) for s in uv_changed_vids.values()),
                           nrm_changed_verts=sum(len(s) for s in nrm_changed_vids.values()),
                           n_centroid_cell_fallback_tris=n_centroid_fallback,
                           centroid_fallback_note=(
                               "per-vertex own-cell ground_uv (spec item 4/6) is degenerate for "
                               "lattice-corner tris (all 3 verts land on their own cell ORIGIN, so the "
                               "UVs collapse independent of position); those tris fall back to the tri's "
                               "CENTROID cell -- the exact proven-island build_landmass call "
                               "(island.py grass fill, 526-531) -- guaranteeing non-degenerate spread. "
                               "Both are in-band grass mains (COL-FREEDOM LAW)."))

    # ---- WRITE the 20 Terrain files -----------------------------------------------------------
    written = {}
    for (bx, by) in touched:
        bm = block_meshes[(bx, by)]
        p = terr_path(FIXED, bx, by)
        M.write_ff9mesh(bm, p)
        written[str(p.relative_to(FIXED))] = sha256_file(p)

    # ---- SEA4: restore the full plane on the 6 blob blocks ------------------------------------
    blob_blocks = [tuple(b) for b in forensics["meta"]["cell_sets"]["blob_blocks"]]
    # find the uniform full-plane donor among the 14 non-blob Sea4 files; verify block-locality
    full_plane_shas = {}
    for (bx, by) in touched:
        if (bx, by) in blob_blocks:
            continue
        full_plane_shas[(bx, by)] = sha256_file(sea4_path(FIXED, bx, by))
    uniq = set(full_plane_shas.values())
    assert len(uniq) == 1, f"non-blob Sea4 files are NOT byte-identical: {uniq}"
    donor_blk = next(iter(full_plane_shas))
    donor_bytes = sea4_path(FIXED, *donor_blk).read_bytes()
    # sanity: parse the donor plane -> Y==0 + flat-mesh invariant
    dp = M.read_ff9mesh(sea4_path(FIXED, *donor_blk))
    donor_y_ok = all(abs(v[1]) <= 1e-4 for v in dp["verts"])
    donor_flat_ok = (dp["vcount"] == len(dp["indices"]) == 3 * (len(dp["indices"]) // 3)) and \
                    (dp["vcount"] == len(dp["verts"]))
    assert donor_y_ok and donor_flat_ok, f"donor plane invalid: y_ok={donor_y_ok} flat_ok={donor_flat_ok}"
    sea4_written = []
    for (bx, by) in blob_blocks:
        p = sea4_path(FIXED, bx, by)
        pre_sha = sha256_file(p)
        p.write_bytes(donor_bytes)                        # byte-copy the uniform block-local plane
        sea4_written.append(dict(block=[bx, by], relpath=str(p.relative_to(FIXED)),
                                 pre_sha=pre_sha[:16], post_sha=sha256_file(p)[:16]))
        written[str(p.relative_to(FIXED))] = sha256_file(p)
    report["sea4"] = dict(
        action="restored the full block-local Sea4 plane on the 6 blob blocks by byte-copying the "
               "uniform (14-block-identical) full plane; verified block-locality (single sha), Y==0, "
               "flat-mesh invariant on the donor",
        blob_blocks=[list(b) for b in blob_blocks],
        donor_block=list(donor_blk), donor_sha=sha256_file(sea4_path(FIXED, *donor_blk))[:16],
        donor_vcount=dp["vcount"], donor_n_tris=len(dp["indices"]) // 3,
        donor_y0=donor_y_ok, donor_flat=donor_flat_ok, written=sea4_written)
    log(f"Sea4 restored on {len(sea4_written)} blob blocks (donor {donor_blk}, "
        f"{dp['vcount']} verts / {len(dp['indices'])//3} tris)")

    report["written_files"] = written
    report["written_files_sha256"] = {k: v for k, v in written.items()}

    # ===========================================================================================
    #                           SELF-CHECK / VERIFICATION
    # ===========================================================================================
    verify = {}

    # (1) re-scan FIXED with the same classifier -> defective MUST be 0
    post_def = 0
    post_per_block = Counter()
    for (bx, by) in touched:
        bm = M.blockmesh_from_ff9mesh(terr_path(FIXED, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for tri in bm.tris:
            uv3 = [(uvs[j][0], uvs[j][1]) for j in tri]
            if uv_degenerate(uv3):
                post_def += 1
                post_per_block[(bx, by)] += 1
    verify["post_fix_defective_count"] = post_def
    verify["post_fix_defective_per_block"] = {f"{b[0]},{b[1]}": post_per_block[b]
                                              for b in touched if post_per_block[b]}
    log(f"[verify] post-fix defective count = {post_def}  (MUST be 0)")

    # (2) UV region sanity: every rewritten UV sits inside the grass mains region (no white gutter)
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    tol = 1e-6
    out_of_region = 0
    for (bx, by), vids in uv_changed_vids.items():
        bm = M.blockmesh_from_ff9mesh(terr_path(FIXED, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for j in vids:
            u, v = uvs[j]
            if not (lo_u - tol <= u <= hi_u + tol and lo_v - tol <= v <= hi_v + tol):
                out_of_region += 1
    verify["rewritten_uv_out_of_grass_region"] = out_of_region
    log(f"[verify] rewritten UVs outside grass mains region = {out_of_region}")

    # (3) BYTE-RIGIDITY: specimen vs fixed, per Terrain file. verts+tangents+indices bit-identical
    #     everywhere; uv differs ONLY at uv_changed_vids; normals ONLY at nrm_changed_vids.
    rig = dict(pos_bad=0, tan_bad=0, idx_bad=0, uv_unexpected=0, uv_expected_changed=0,
               nrm_unexpected=0, nrm_expected_changed=0, files=len(touched))
    for (bx, by) in touched:
        s = M.read_ff9mesh(terr_path(SPEC, bx, by))
        f = M.read_ff9mesh(terr_path(FIXED, bx, by))
        if s["indices"] != f["indices"]:
            rig["idx_bad"] += 1
        if s["verts"] != f["verts"]:
            rig["pos_bad"] += 1
        if s["tangents"] != f["tangents"]:
            rig["tan_bad"] += 1
        chg_uv = uv_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["uvs"][j] != f["uvs"][j]:
                if j in chg_uv:
                    rig["uv_expected_changed"] += 1
                else:
                    rig["uv_unexpected"] += 1
        chg_n = nrm_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["normals"][j] != f["normals"][j]:
                if j in chg_n:
                    rig["nrm_expected_changed"] += 1
                else:
                    rig["nrm_unexpected"] += 1
    verify["byte_rigidity"] = rig
    log(f"[verify] byte-rigidity: pos_bad={rig['pos_bad']} tan_bad={rig['tan_bad']} "
        f"idx_bad={rig['idx_bad']} uv_unexpected={rig['uv_unexpected']} "
        f"nrm_unexpected={rig['nrm_unexpected']} uv_changed={rig['uv_expected_changed']} "
        f"nrm_changed={rig['nrm_expected_changed']}")

    # (4) FLAT-MESH INVARIANT on every WRITTEN file (Terrain x20 + Sea4 x6) + all 20 Sea4 uniform
    flat_bad = []
    for relpath in written:
        p = FIXED / relpath
        d = M.read_ff9mesh(p)
        if not (d["vcount"] == len(d["indices"]) == len(d["verts"]) and len(d["indices"]) % 3 == 0):
            flat_bad.append(relpath)
    verify["flat_mesh_bad_written_files"] = flat_bad
    sea4_shas_post = {f"{b[0]},{b[1]}": sha256_file(sea4_path(FIXED, *b))[:16] for b in touched}
    verify["all_sea4_uniform_post"] = (len(set(sea4_shas_post.values())) == 1)
    verify["sea4_shas_post_unique"] = sorted(set(sea4_shas_post.values()))
    log(f"[verify] flat-mesh bad files={flat_bad}  all Sea4 uniform post={verify['all_sea4_uniform_post']}")

    # (5) untouched-tri byte-identity sample vs specimen (carried-core / lawful frame proof):
    #     any vertex NOT in a changed set has identical uv & nrm. (covered by rig uv/nrm_unexpected==0)
    verify["untouched_tris_byte_identical"] = (rig["uv_unexpected"] == 0 and rig["nrm_unexpected"] == 0
                                               and rig["pos_bad"] == 0 and rig["tan_bad"] == 0
                                               and rig["idx_bad"] == 0)

    report["verify"] = verify
    report["ok"] = (post_def == 0 and out_of_region == 0 and not flat_bad
                    and rig["pos_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0
                    and rig["uv_unexpected"] == 0 and rig["nrm_unexpected"] == 0
                    and verify["all_sea4_uniform_post"])

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"OK={report['ok']}  post_def={post_def}  -> {REPORT}")
    return report


if __name__ == "__main__":
    main()
