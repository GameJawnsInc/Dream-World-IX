"""RUNG F AFTERMATH -- UVF FORENSICS: THE PER-TRI PROVENANCE x UV-VERDICT CROSS-TABLE (2026-07-24).

The round's centerpiece. Sweeps ALL 20 Rung F staged blocks (0-4,16-19), every part, and for EVERY
triangle produces:
  PROVENANCE  -- carried-core / hole-fill / stitch / apron / frame-mint / sea / other
  UV VERDICT  -- lawful-mains / lawful-other-catalogued / degenerate-zero-area / out-of-catalog /
                 suspicious-flat

PROVENANCE METHOD (Lane A's Recipe A, refined with a CHEAP exact re-derivation of the carry's cell
sets -- NOT a full mesh rebuild): rung_f_layout.load_donor_window() reads the real donor window
(blocks 12-16,10-13, disc 1, READ-ONLY) and returns, with ZERO mesh synthesis, the exact
by_cell/dropped_by_cell maps carry() itself uses. From these + the module's own SHIFT_CELLS/DROP_SET/
LAND_HEIGHT constants (imported, never reimplemented) this script rederives, in cell-space only
(cheap): placed_R0 (the window footprint), kept_cells0/dropped_only_cells0/partial_cells0 (donor
cell classes), enclosed (HF.enclosed_missing_cells), placed_R = placed_R0|enclosed, and grass_remove
= HF.dilate(placed_R,1) -- IDENTICAL cell sets to what rung_f_layout.carry()/rung_f_stitch.stitch_tile
compute internally (same functions, same constants, no reimplementation). A staged tri's CELL then
locates it inside one of these zones. Combined with the UV-CONSTANT-STAMP signature (every synthesized
fill/stitch/apron tri carries the SAME single (grass_id,grass_uv) point threaded through carry() ->
HF.fill_loop/HF.contour_tile/HF.excise_and_refill -- Lane A's docstring citations), zone membership +
UV-constant membership together give an exact, defensible provenance label. CARRIED-CORE is additionally
BYTE-VERIFIED against the real donor tris (position undo-transform + exact match, matching rung_f_build.
stage2_rigidity's own method, reimplemented read-only here).

UV VERDICT METHOD -- Lane B's catalog (seam_null_recon.FAM_OF/classify_tri, reused via uvf_stock_census.
classify_tri_plus which adds the wall/rock sub-classifier) + Lane C's calibrated threshold (ZERO_UV_THRESH
=1e-6, empirically the exact stock-vs-specimen discriminator: 0/14,288 stock tris below it, 2305/6996
Rung F terrain tris below it).

SEA/LAND OVERLAP -- per 4u cell, a 16x16 sub-grid point-sample (point-in-triangle XZ) against the
binned land tris and the binned REAL (non-placeholder) sea tris gives a measured overlap AREA per cell
(not a full analytic polygon clip, but a direct area measurement, not just a boolean cell flag).

READ-ONLY vs the game install (only for the real donor window bytes, the toolkit's standing convention
throughout this arc) and READ-ONLY vs the staged tree (out/rung_f/FF9CustomMap-world) -- zero writes to
either. Writes only out/rung_f/uvf_forensics.json + this script.

Run: cd studies/overworld-topography && py -X utf8 uvf_forensics.py
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit import config as _cfg                # noqa: E402
from ff9mapkit.world import extract as X            # noqa: E402
from ff9mapkit.world import mesh as M               # noqa: E402

import seam_null_recon as SNR                       # noqa: E402
import uvf_stock_census as USC                       # noqa: E402
import rung_f_layout as RFL                          # noqa: E402
import rung_f_holefill as HF                         # noqa: E402

CELL = RFL.CELL
BLOCK = RFL.BLOCK
STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
OUT = HERE / "out" / "rung_f" / "uvf_forensics.json"
BUILD_JSON = HERE / "out" / "rung_f" / "rung_f_build.json"

TERRAIN = "Terrain"
PARTS_STAGED = ("Terrain", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Object", "Beach1")  # per stage6_write
FOOTPRINT = sorted((bx, by) for bx in range(0, 5) for by in range(16, 20))       # the 20 Rung F blocks

ZERO_UV_THRESH = USC.ZERO_UV_THRESH            # 1e-6, Lane C's calibrated floor (0/14288 stock exceptions)
NEAR_DEGEN_THRESH = 1e-3                       # secondary "suspicious-flat" band above the strict floor
UV_EQ_TOL = 1e-4                               # UV-bit-identity tolerance for the constant-stamp signature


def log(m):
    print(m, flush=True)


# ============================================================================================
# STAGE A -- cheap, exact re-derivation of the carry's CELL SETS (no mesh synthesis)
# ============================================================================================
def compute_carry_geometry(game_root):
    log("=" * 100)
    log("STAGE A -- cheap cell-space re-derivation of the carry footprint (rung_f_layout.load_donor_window "
        "+ the module's own SHIFT_CELLS/DROP_SET/LAND_HEIGHT + rung_f_holefill.enclosed_missing_cells/"
        "dilate -- NO mesh synthesis, NO build_landmass call, NO carry()/stitch_tile() call)")
    donor = RFL.load_donor_window(game_root)          # REAL donor read, blocks 12-16,10-13, disc 1
    by_cell = donor["by_cell"]                          # kept ecotone donor cells (pre-shift)
    dropped_by_cell = donor["dropped_by_cell"]          # dropped-feature donor cells (pre-shift)
    R = set(by_cell) | set(dropped_by_cell)
    Tx, Tz = RFL.SHIFT_CELLS
    shift = lambda c: (c[0] + Tx, c[1] + Tz)             # noqa: E731

    placed_R0 = {shift(c) for c in R}
    kept_cells0 = {shift(c) for c in by_cell}
    dropped_only_cells0 = {shift(c) for c in dropped_by_cell if c not in by_cell}
    partial_cells0 = {shift(c) for c in by_cell if c in dropped_by_cell}
    enclosed = HF.enclosed_missing_cells(placed_R0)
    placed_R = placed_R0 | enclosed
    grass_remove = HF.dilate(placed_R, 1)

    # DY -- identical formula to rung_f_layout.carry() (median ecotone-family Y among kept tris)
    des_ys, all_ys = [], []
    for tris in by_cell.values():
        for tri in tris:
            y = sum(v[0][1] for v in tri) / 3.0
            all_ys.append(y)
            topo = X.decode_id(int(round(tri[0][3][0])))["topograph"]
            if topo in (16, 17, 19, 20, 41):
                des_ys.append(y)
    ens_seat = statistics.median(des_ys) if des_ys else statistics.median(all_ys)
    DY = RFL.LAND_HEIGHT - ens_seat
    Twx, Twz = RFL.SHIFT_WORLD

    # donor byte-compare index: DONOR-SPACE (untransformed) position-sorted-key -> donor tri, KEPT ONLY.
    # Matches rung_f_build.stage2_rigidity's own convention exactly: the STAGED tri is undo-transformed
    # (subtract Twx/DY/Twz) before lookup, so the index itself stays in raw donor coordinates.
    donor_tri_lookup = {}
    donor_vert_positions = set()          # DONOR-SPACE, 4dp -- for clipped-piece sub-classification
    for c, tris in by_cell.items():
        for tri in tris:
            key = tuple(sorted((round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)) for v in tri))
            donor_tri_lookup[key] = tri
            for v in tri:
                donor_vert_positions.add((round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)))

    blob_blocks = {RFL.cell_block(c) for c in placed_R}          # exact same set rung_f_build.py computes

    log(f"  DY = {DY:.4f} (rung_f_build.json compose_diag.DY = 0.1224 -- cross-check below)")
    log(f"  placed_R0={len(placed_R0)} kept_cells0={len(kept_cells0)} dropped_only_cells0={len(dropped_only_cells0)} "
        f"partial_cells0={len(partial_cells0)} enclosed={len(enclosed)} placed_R={len(placed_R)} "
        f"grass_remove={len(grass_remove)} blob_blocks={sorted(blob_blocks)}")
    return dict(donor=donor, placed_R0=placed_R0, kept_cells0=kept_cells0,
                dropped_only_cells0=dropped_only_cells0, partial_cells0=partial_cells0, enclosed=enclosed,
                placed_R=placed_R, grass_remove=grass_remove, DY=DY, Twx=Twx, Twz=Twz,
                donor_tri_lookup=donor_tri_lookup, donor_vert_positions=donor_vert_positions,
                blob_blocks=blob_blocks)


def cell_class(cell, cg):
    if cell in cg["kept_cells0"] and cell in cg["dropped_only_cells0"]:
        return "kept+dropped(partial)"          # dropped_only_cells0 excludes kept overlaps by construction
    if cell in cg["kept_cells0"]:
        return "kept-only"
    if cell in cg["dropped_only_cells0"]:
        return "dropped-only"
    if cell in cg["enclosed"]:
        return "enclosed"
    if cell in cg["placed_R"]:
        return "placed_R-other"                  # shouldn't normally hit (kept|dropped|enclosed cover placed_R)
    if cell in cg["grass_remove"]:
        return "annulus(grass_remove-ring)"
    return "outside"


# ============================================================================================
# STAGE B -- determine the build's ACTUAL grass_uv constant-stamp point empirically from the
# staged bytes (does not require re-running mint_grass_frame/_grass_stamp -- just finds the most
# common all-3-vertex-identical UV point among Terrain tris, exactly Lane C's method).
# ============================================================================================
def find_grass_stamp_point(all_terrain_tris):
    tally = Counter()
    for t in all_terrain_tris:
        uv3 = t["uv"]
        pts = [(round(u, 4), round(v, 4)) for (u, v) in uv3]
        if pts[0] == pts[1] == pts[2]:
            tally[pts[0]] += 1
    if not tally:
        return None, 0
    pt, n = tally.most_common(1)[0]
    log(f"STAGE B -- empirical grass-stamp constant-UV point: {pt} ({n} tris carry it bit-identically); "
        f"{len(tally)} distinct all-3-identical UV points total: {tally.most_common(5)}")
    return pt, n


def is_uv_constant(uv3, point, tol=UV_EQ_TOL):
    if point is None:
        return False
    (u0, v0) = point
    return all(abs(u - u0) < tol and abs(v - v0) < tol for (u, v) in uv3)


def all3_identical(uv3, tol=1e-6):
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs(u0 - u1) < tol and abs(v0 - v1) < tol and abs(u0 - u2) < tol and abs(v0 - v2) < tol


# ============================================================================================
# STAGE C -- per-tri provenance
# ============================================================================================
def classify_provenance(cell, uv3, stamp_point, cg):
    cc = cell_class(cell, cg)
    flat = is_uv_constant(uv3, stamp_point)
    if flat:
        if cc == "dropped-only":
            return "hole-fill", "drop-hole(fully-dropped-cell)", cc
        if cc == "kept+dropped(partial)":
            return "hole-fill", "drop-hole(partial-cell)", cc
        if cc == "enclosed":
            return "stitch", "interior-blob-hole", cc
        if cc == "annulus(grass_remove-ring)":
            return "apron", "tiling-annulus", cc
        if cc == "kept-only":
            # a flat-stamped tri inside a pure-kept ecotone cell -- not expected from the drop/hole
            # machinery (those never touch kept-only cells); most likely an excise+refill local patch
            # that happened to land in a kept cell's donor "missing tri" gap.
            return "stitch", "excise-refill(in-kept-cell)", cc
        if cc == "placed_R-other":
            return "stitch", "excise-refill(placed_R-other)", cc
        # flat-stamp UV but cell is OUTSIDE every known carry/stitch zone -- genuinely unexpected
        return "other", "flat-stamp-outside-known-zones", cc
    else:
        if cc in ("kept-only", "kept+dropped(partial)"):
            return "carried-core", "per-vertex-uv(donor-like)", cc
        if cc in ("dropped-only", "enclosed", "annulus(grass_remove-ring)", "placed_R-other"):
            # per-vertex-varying UV inside a zone that should be 100% flat-stamped fill -- unexpected
            return "other", "varying-uv-inside-fill-zone", cc
        return "frame-mint", "build_landmass-grass", cc


def byte_verify_carried(tri, cg):
    """Whole-tri donor byte match (position undo-transform, exact key lookup) + per-vertex donor
    position membership (clipped/apron-piece sub-signal). Read-only, matches rung_f_build.stage2's
    own method. Returns (verified, subtype, detail)."""
    Twx, Twz, DY = cg["Twx"], cg["Twz"], cg["DY"]
    key = tuple(sorted((round(v[0][0] - Twx, 4), round(v[0][1] - DY, 4), round(v[0][2] - Twz, 4))
                       for v in tri["wnut"]))
    dtri = cg["donor_tri_lookup"].get(key)
    if dtri is not None:
        dverts = {(round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4)): v for v in dtri}
        uv_bad = nrm_bad = tan_bad = topo_bad = 0
        for (p, n, u, t) in tri["wnut"]:
            dk = (round(p[0] - Twx, 4), round(p[1] - DY, 4), round(p[2] - Twz, 4))
            dv = dverts.get(dk)
            if dv is None:
                continue
            if (u[0], u[1]) != (dv[2][0], dv[2][1]):
                uv_bad += 1
            if tuple(n) != tuple(dv[1]):
                nrm_bad += 1
            if tuple(t[1:]) != tuple(dv[3][1:]):
                tan_bad += 1
            dd = X.decode_id(int(round(dv[3][0])))
            cd = X.decode_id(int(round(t[0])))
            if not (cd["topograph"] == dd["topograph"] and cd["flags"] == dd["flags"]):
                topo_bad += 1
        exact = (uv_bad == nrm_bad == tan_bad == topo_bad == 0)
        return True, ("whole-verbatim" if exact else "whole-match-but-attr-mismatch"), \
            dict(uv_bad=uv_bad, nrm_bad=nrm_bad, tan_bad=tan_bad, topo_bad=topo_bad)
    # no whole match -- check per-vertex donor position membership (a border-clip / apron-fixh piece)
    n_vert_match = sum(1 for v in tri["wnut"]
                       if (round(v[0][0] - Twx, 4), round(v[0][1] - DY, 4), round(v[0][2] - Twz, 4))
                       in cg["donor_vert_positions"])
    if n_vert_match > 0:
        return False, f"clipped-piece({n_vert_match}/3-verts-donor-matched)", {}
    return False, "unverified(no-donor-vertex-match)", {}


# ============================================================================================
# STAGE D -- UV verdict (Lane B catalog + Lane C threshold)
# ============================================================================================
def uv_verdict(topo, uv3):
    area = USC.uv_area(uv3)
    fam = SNR.FAM_OF.get(topo)
    label, det = USC.classify_tri_plus(fam, uv3)
    if area < ZERO_UV_THRESH:
        return "degenerate-zero-area", label, det, area
    if area < NEAR_DEGEN_THRESH and all3_identical(uv3, tol=1e-3):
        return "suspicious-flat", label, det, area
    if label == "mains_own":
        return "lawful-mains", label, det, area
    if label in ("wall_rock", "strip_grass_desert", "strip_desert_dunes"):
        return "lawful-other-catalogued", label, det, area
    if label == "mains_foreign":
        return "out-of-catalog", label, det, area           # mistagged-family is its own red flag
    return "out-of-catalog", label, det, area


# ============================================================================================
# loaders (reuse USC's, staged tree only)
# ============================================================================================
def load_terrain_tris(bx, by):
    bm, src = USC.load_part(bx, by, TERRAIN, staged=True)
    if bm is None or not bm.tris:
        return []
    ox, oz = X.block_world_origin(bx, by)
    out = []
    verts, uvs, nrms, tans = bm.verts, bm.uvs, bm.normals, bm.tangents
    for tri in bm.tris:
        w = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
        uv = [(float(uvs[j][0]), float(uvs[j][1])) for j in tri]
        nrm = [tuple(nrms[j]) for j in tri]
        tan = [tuple(tans[j]) for j in tri]
        wnut = [(w[i], nrm[i], uv[i], tan[i]) for i in range(3)]
        idall = int(round(tans[tri[0]][0]))
        dec = X.decode_id(idall)
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        out.append(dict(block=(bx, by), w=w, uv=uv, wnut=wnut, topo=dec["topograph"], flags=dec["flags"],
                        event=dec["event"], area_bit=dec["area"], cell=cell,
                        area3d=USC.area3d(w), plan_area=USC.plan_area(w)))
    return out


def load_other_part_tris(bx, by, part):
    bm, src = USC.load_part(bx, by, part, staged=True)
    if bm is None or not bm.tris:
        return []
    ox, oz = X.block_world_origin(bx, by)
    out = []
    verts = bm.verts
    for tri in bm.tris:
        w = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        cell = (math.floor(cx / CELL), math.floor(cz / CELL))
        out.append(dict(block=(bx, by), w=w, cell=cell, area3d=USC.area3d(w), plan_area=USC.plan_area(w)))
    return out


# ============================================================================================
# STAGE E -- sea/land plan-overlap, grid-sampled area per cell
# ============================================================================================
def sample_cell_overlap(land_tris, sea_tris, cell, sub=16):
    cx0, cz0 = CELL * cell[0], CELL * cell[1]
    step = CELL / sub
    subarea = step * step
    n_land = n_sea = n_both = 0
    for i in range(sub):
        for j in range(sub):
            px = cx0 + (i + 0.5) * step
            pz = cz0 + (j + 0.5) * step
            in_land = any(HF._pt_in_tri_xz((px, 0.0, pz), t["w"][0], t["w"][1], t["w"][2]) for t in land_tris)
            in_sea = any(HF._pt_in_tri_xz((px, 0.0, pz), t["w"][0], t["w"][1], t["w"][2]) for t in sea_tris)
            n_land += in_land
            n_sea += in_sea
            n_both += (in_land and in_sea)
    return dict(land_area=round(n_land * subarea, 4), sea_area=round(n_sea * subarea, 4),
               overlap_area=round(n_both * subarea, 4), cell_area=CELL * CELL)


# ============================================================================================
# MAIN SWEEP
# ============================================================================================
def main():
    game_root = Path(_cfg.find_game_path(None))
    log(f"game root: {game_root}")
    log(f"staged tree: {STAGED}")
    assert STAGED.exists(), f"staged tree missing: {STAGED}"

    cg = compute_carry_geometry(game_root)

    # ---- cross-check DY against rung_f_build.json's recorded value ------------------------------
    build_dy = None
    if BUILD_JSON.exists():
        try:
            build_dy = json.loads(BUILD_JSON.read_text(encoding="utf-8"))["compose_diag"]["DY"]
        except Exception:
            pass
    dy_match = (build_dy is not None and abs(build_dy - cg["DY"]) < 1e-3)
    log(f"DY cross-check: recomputed={cg['DY']:.4f} vs rung_f_build.json={build_dy} match={dy_match}")

    # ---- load every Terrain tri across the 20 blocks --------------------------------------------
    log("=" * 100); log("SWEEP -- loading Terrain, all 20 blocks")
    all_terrain = []
    for (bx, by) in FOOTPRINT:
        all_terrain.extend(load_terrain_tris(bx, by))
    log(f"  {len(all_terrain)} Terrain tris loaded")

    stamp_point, stamp_n = find_grass_stamp_point(all_terrain)

    # ---- classify every Terrain tri ---------------------------------------------------------------
    log("=" * 100); log("CLASSIFY -- provenance x UV verdict, every Terrain tri")
    cross = Counter()
    cross_area = Counter()
    per_block_prov = defaultdict(Counter)
    per_block_defect_frac = {}
    topo_by_prov = defaultdict(Counter)
    carried_core_verify = Counter()
    records = []           # compact per-tri record (Terrain only)
    for t in all_terrain:
        prov, subtype, cc = classify_provenance(t["cell"], t["uv"], stamp_point, cg)
        verdict, label, det, area = uv_verdict(t["topo"], t["uv"])
        key = (prov, verdict)
        cross[key] += 1
        cross_area[key] += t["area3d"]
        per_block_prov[t["block"]][prov] += 1
        topo_by_prov[prov][t["topo"]] += 1
        bverify = None
        if prov == "carried-core":
            verified, bsubtype, bdet = byte_verify_carried(t, cg)
            carried_core_verify[bsubtype] += 1
            bverify = dict(verified=verified, subtype=bsubtype, detail=bdet)
        defective = verdict in ("degenerate-zero-area", "suspicious-flat", "out-of-catalog")
        records.append(dict(block=list(t["block"]), cell=list(t["cell"]), provenance=prov, subtype=subtype,
                            cell_class=cc, uv_verdict=verdict, uv_label=label, uv_detail=det,
                            uv_area=round(area, 8), area3d=round(t["area3d"], 4),
                            plan_area=round(t["plan_area"], 4), topo=t["topo"], flags=t["flags"],
                            event=t["event"], area_bit=t["area_bit"],
                            centroid=[round(sum(p[0] for p in t["w"]) / 3, 3),
                                     round(sum(p[1] for p in t["w"]) / 3, 3),
                                     round(sum(p[2] for p in t["w"]) / 3, 3)],
                            byte_verify=bverify, defective=defective))

    for blk, ctr in per_block_prov.items():
        n = sum(ctr.values())
        n_def = sum(1 for r in records if tuple(r["block"]) == blk and r["defective"])
        per_block_defect_frac[f"{blk[0]},{blk[1]}"] = dict(n_tris=n, n_defective=n_def,
                                                            defective_frac=round(n_def / n, 4) if n else None,
                                                            by_provenance=dict(ctr))

    log(f"  cross-table (provenance x uv_verdict): {len(cross)} distinct cells")
    for (prov, verdict), n in cross.most_common():
        log(f"    {prov:14s} x {verdict:24s} : n={n:5d} area3d={cross_area[(prov, verdict)]:.2f}")
    log(f"  carried-core byte-verify subtypes: {dict(carried_core_verify)}")

    # ---- populations: localize every DEFECTIVE population by (provenance,subtype) -----------------
    log("=" * 100); log("LOCALIZE -- plan-space extents of every flat/unlawful population")
    pop_key = defaultdict(list)
    for r in records:
        if r["defective"]:
            pop_key[(r["provenance"], r["subtype"], r["uv_verdict"])].append(r)
    populations = []
    for (prov, subtype, verdict), rs in sorted(pop_key.items(), key=lambda kv: -len(kv[1])):
        blocks = sorted({tuple(r["block"]) for r in rs})
        cells = [tuple(r["cell"]) for r in rs]
        cx = [c[0] for c in cells]; cz = [c[1] for c in cells]
        centroids = [r["centroid"] for r in rs]
        wx = [c[0] for c in centroids]; wy = [c[1] for c in centroids]; wz = [c[2] for c in centroids]
        area_sum = sum(r["area3d"] for r in rs)
        topo_hist = Counter(r["topo"] for r in rs)
        populations.append(dict(provenance=prov, subtype=subtype, uv_verdict=verdict, n_tris=len(rs),
                                area3d_sum=round(area_sum, 2), n_blocks=len(blocks),
                                blocks=[list(b) for b in blocks],
                                cell_range=dict(x=[min(cx), max(cx)], z=[min(cz), max(cz)]),
                                world_bbox=dict(x=[round(min(wx), 2), round(max(wx), 2)],
                                               y=[round(min(wy), 2), round(max(wy), 2)],
                                               z=[round(min(wz), 2), round(max(wz), 2)]),
                                topo_hist=dict(topo_hist.most_common(10)),
                                sample_centroids=centroids[:8]))
    for p in populations[:12]:
        log(f"  POP {p['provenance']:12s}/{p['subtype']:32s} verdict={p['uv_verdict']:20s} n={p['n_tris']:5d} "
            f"blocks={p['n_blocks']} cellsX={p['cell_range']['x']} cellsZ={p['cell_range']['z']} "
            f"area3d={p['area3d_sum']}")

    # ---- hole-fill footprint vs DROP_SET dropped-only-cells0 Jaccard (evidence item b) ------------
    hf_cells = {tuple(r["cell"]) for r in records if r["provenance"] == "hole-fill"}
    drop_cells = cg["dropped_only_cells0"] | {c for c in cg["partial_cells0"]}
    jacc_inter = len(hf_cells & drop_cells)
    jacc_union = len(hf_cells | drop_cells)
    hole_fill_vs_dropset = dict(hole_fill_cells=len(hf_cells), donor_drop_cells=len(drop_cells),
                                intersection=jacc_inter, union=jacc_union,
                                jaccard=round(jacc_inter / jacc_union, 4) if jacc_union else None)
    log(f"  hole-fill footprint vs donor DROP_SET cells: jaccard={hole_fill_vs_dropset['jaccard']} "
        f"(hf={len(hf_cells)} drop={len(drop_cells)} inter={jacc_inter})")

    # ---- apron ring geometry (evidence item c: dunes rim) ------------------------------------------
    apron_cells = {tuple(r["cell"]) for r in records if r["provenance"] == "apron"}
    apron_ys = [r["centroid"][1] for r in records if r["provenance"] == "apron"]
    apron_ring = dict(n_cells=len(apron_cells), n_tris=sum(1 for r in records if r["provenance"] == "apron"),
                      y_range=[round(min(apron_ys), 3), round(max(apron_ys), 3)] if apron_ys else None,
                      y_spread=round(max(apron_ys) - min(apron_ys), 3) if apron_ys else None,
                      cell_range=dict(x=[min(c[0] for c in apron_cells), max(c[0] for c in apron_cells)],
                                     z=[min(c[1] for c in apron_cells), max(c[1] for c in apron_cells)])
                      if apron_cells else None)
    log(f"  apron ring: {apron_ring}")

    # ---- SEA parts: load, classify placeholder vs real, sea/land overlap per cell -----------------
    log("=" * 100); log("SEA -- per-block part census + sea/land plan-overlap (grid-sampled area per cell)")
    PLACEHOLDER_AREA = 1e-6
    sea_summary = {}
    overlap_cells = []
    sea4_class = {}
    for (bx, by) in FOOTPRINT:
        blk = (bx, by)
        land = load_terrain_tris(bx, by)          # reload (cheap) so this section is self-contained
        parts_info = {}
        real_sea_by_part = {}
        for part in PARTS_STAGED[1:]:
            tris = load_other_part_tris(bx, by, part)
            n = len(tris)
            real = [t for t in tris if t["plan_area"] > PLACEHOLDER_AREA]
            parts_info[part] = dict(n_tris=n, n_real=len(real),
                                    plan_area_sum=round(sum(t["plan_area"] for t in tris), 4),
                                    y_all_zero=all(abs(v[1]) < 1e-6 for t in tris for v in t["w"]) if tris else None)
            real_sea_by_part[part] = real
        is_blob = blk in cg["blob_blocks"]
        sea4_info = parts_info.get("Sea4", {})
        sea4_class[f"{bx},{by}"] = dict(is_blob_block=is_blob,
                                        sea4_n_tris=sea4_info.get("n_tris"),
                                        sea4_plan_area=sea4_info.get("plan_area_sum"),
                                        classification=("degenerate-y0-stub" if is_blob else "full-plane"))
        sea_summary[f"{bx},{by}"] = parts_info

        all_real_sea = [t for part in PARTS_STAGED[1:] for t in real_sea_by_part[part]]
        land_by_cell = defaultdict(list)
        for t in land:
            land_by_cell[t["cell"]].append(t)
        sea_by_cell_local = defaultdict(list)
        for t in all_real_sea:
            sea_by_cell_local[t["cell"]].append(t)
        candidate_cells = set(land_by_cell) & set(sea_by_cell_local)
        for cell in sorted(candidate_cells):
            ov = sample_cell_overlap(land_by_cell[cell], sea_by_cell_local[cell], cell)
            if ov["overlap_area"] > 1e-4:
                which_parts = [p for p in PARTS_STAGED[1:] if any(t["cell"] == cell for t in real_sea_by_part[p])]
                overlap_cells.append(dict(block=[bx, by], cell=list(cell), is_blob_block=is_blob,
                                          which_sea_parts=which_parts, **ov))
    n_blob_overlap = sum(1 for c in overlap_cells if c["is_blob_block"])
    n_nonblob_overlap = len(overlap_cells) - n_blob_overlap
    log(f"  sea/land overlap cells (grid-sampled, area>1e-4): {len(overlap_cells)} total "
        f"({n_blob_overlap} in blob_blocks, {n_nonblob_overlap} in non-blob full-Sea4 blocks)")

    # ---- Sea4 discontinuity at the blob/non-blob border (translucent-sheet candidate) --------------
    log("SEA -- blob/non-blob Sea4 border discontinuity scan")
    border_pairs = []
    for (bx, by) in FOOTPRINT:
        for (dx, dy) in ((1, 0), (0, 1)):
            nb = (bx + dx, by + dy)
            if nb not in set(FOOTPRINT):
                continue
            a_blob = (bx, by) in cg["blob_blocks"]
            b_blob = nb in cg["blob_blocks"]
            if a_blob != b_blob:
                a_area = sea_summary[f"{bx},{by}"]["Sea4"]["plan_area_sum"]
                b_area = sea_summary[f"{nb[0]},{nb[1]}"]["Sea4"]["plan_area_sum"]
                border_pairs.append(dict(block_a=[bx, by], block_b=list(nb), a_is_blob=a_blob,
                                         b_is_blob=b_blob, sea4_area_a=a_area, sea4_area_b=b_area,
                                         area_ratio=round((max(a_area, b_area) + 1e-9)
                                                          / (min(a_area, b_area) + 1e-9), 1)))
    log(f"  {len(border_pairs)} blob<->non-blob block-adjacency pairs (Sea4 area discontinuity)")
    for bp in border_pairs:
        log(f"    {bp['block_a']}(blob={bp['a_is_blob']},area={bp['sea4_area_a']}) <-> "
            f"{bp['block_b']}(blob={bp['b_is_blob']},area={bp['sea4_area_b']}) ratio={bp['area_ratio']}x")

    # ---- corner blocks / SE-coast-arc check (evidence item e) --------------------------------------
    corners = [(0, 16), (4, 16), (0, 19), (4, 19)]
    corner_report = {}
    for c in corners:
        key = f"{c[0]},{c[1]}"
        pb = per_block_defect_frac.get(key, {})
        corner_report[key] = pb
    log(f"  corner-block defect fractions: {json.dumps(corner_report, default=str)[:800]}")

    # ---- block-seam concentration (evidence item a: "hug block seams") -----------------------------
    log("BLOCK-SEAM -- fraction of defective terrain tris whose cell touches a block border (local x/z"
        " in {0,15} of the 16-cell block edge)")
    _origin_cache = {}

    def touches_block_border(block, cell):
        bx, by = block
        if block not in _origin_cache:
            _origin_cache[block] = X.block_world_origin(bx, by)
        ox, oz = _origin_cache[block]
        lcx = round((CELL * cell[0] - ox) / CELL)
        lcz = round((CELL * cell[1] - oz) / CELL)
        return lcx in (0, 15) or lcz in (0, 15)
    n_defect = sum(1 for r in records if r["defective"])
    n_defect_border = sum(1 for r in records if r["defective"]
                          and touches_block_border(tuple(r["block"]), tuple(r["cell"])))
    block_seam_stat = dict(n_defective=n_defect, n_defective_on_block_border_cell=n_defect_border,
                           frac=round(n_defect_border / n_defect, 4) if n_defect else None)
    log(f"  {block_seam_stat}")

    # ---- headline cross-table (compact, for the JSON top) -------------------------------------------
    cross_table = {}
    for (prov, verdict), n in cross.items():
        cross_table.setdefault(prov, {})[verdict] = dict(n=n, area3d=round(cross_area[(prov, verdict)], 2))

    result = dict(
        meta=dict(script="uvf_forensics.py", footprint=[list(b) for b in FOOTPRINT], read_only=True,
                  staged_tree=str(STAGED), n_terrain_tris=len(all_terrain),
                  grass_stamp_point=stamp_point, grass_stamp_n_tris=stamp_n,
                  DY_recomputed=round(cg["DY"], 4), DY_build_json=build_dy, DY_match=dy_match,
                  zero_uv_thresh=ZERO_UV_THRESH, near_degen_thresh=NEAR_DEGEN_THRESH,
                  cell_sets=dict(placed_R0=len(cg["placed_R0"]), kept_cells0=len(cg["kept_cells0"]),
                                dropped_only_cells0=len(cg["dropped_only_cells0"]),
                                partial_cells0=len(cg["partial_cells0"]), enclosed=len(cg["enclosed"]),
                                placed_R=len(cg["placed_R"]), grass_remove=len(cg["grass_remove"]),
                                blob_blocks=sorted([list(b) for b in cg["blob_blocks"]]))),
        cross_table=cross_table,
        cross_table_flat=[dict(provenance=p, uv_verdict=v, n=n, area3d=round(cross_area[(p, v)], 2))
                          for (p, v), n in cross.most_common()],
        carried_core_byte_verify=dict(carried_core_verify),
        topo_by_provenance={p: dict(c.most_common(15)) for p, c in topo_by_prov.items()},
        per_block=per_block_defect_frac,
        populations=populations,
        hole_fill_vs_donor_dropset=hole_fill_vs_dropset,
        apron_ring=apron_ring,
        block_seam_stat=block_seam_stat,
        sea=dict(per_block_parts=sea_summary, sea4_classification=sea4_class,
                 overlap_cells=overlap_cells, n_overlap_cells=len(overlap_cells),
                 n_overlap_cells_blob=n_blob_overlap, n_overlap_cells_nonblob=n_nonblob_overlap,
                 blob_nonblob_border_pairs=border_pairs),
        corner_blocks=corner_report,
        records=records,           # full per-tri Terrain table (exhaustive, as requested)
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    log("=" * 100)
    log(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
    return result


if __name__ == "__main__":
    main()
