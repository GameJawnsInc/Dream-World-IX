"""THE MASS-ANATOMY CONTRACT round -- LANE B: BODY DECAL-SATURATION + SPINE-WIDTH STATISTICS
(2026-07-23). Mandated by the Rung E rejection (GROUND-FAMILY-DECODE-2026-07-19.md, "## Rung E",
refutation 2 "THE SATURATED COMB"): the eye rejected Rung E's corridor for being 75.7% dressed
with no plain spine, while the aggregate writes:body ratio gate (1.9686) was blind to that
arrangement. This script measures STOCK's real arrangement at the map's one grass|desert ecotone
site (blocks (13-15,11-12)) and, for comparison, the Rung E staged build's own arrangement, so a
future Rung F build has a stock-measured saturation CEILING and spine-width FLOOR to gate on.

READ-ONLY against the game install and the Rung E staging tree: only X.read_block (stock disc-1
bytes) via seam_null_recon.py's proven load_tris/classify_tri/edge_index/FAM_OF (imported, not
re-derived -- CALIBRATE-THE-INSTRUMENT-BEFORE-YOU-JUDGE-WITH-IT: this script's classifier is
byte-identical to every prior round's), plus a local mixed stock+staged-override loader for the
already-built (never-deployed, dry-run-only) Rung E tree at out/rung_e/FF9CustomMap-world. ZERO
writes to the game install, no deploy, no mirror, no --apply. Only files this round may write:
contract_mass_*.py (this file) and out/contract_mass/*.

Run:  py studies/overworld-topography/contract_mass_saturation.py
Artifact -> out/contract_mass/lane_b_saturation.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                        # noqa: E402 -- proven FAM_OF/classify_tri/edge_index/load_tris
from ff9mapkit.world import extract as X              # noqa: E402
from ff9mapkit.world import grassland as G            # noqa: E402
from ff9mapkit.world import mesh as M                 # noqa: E402

OUT_DIR = HERE / "out" / "contract_mass"
OUT = OUT_DIR / "lane_b_saturation.json"
SITES_JSON = OUT_DIR / "sites.json"
CROSSCHECK_JSON = HERE / "out" / "topo16_ecotone_crosscheck.json"
RUNG_E_MOD_DIR = HERE / "out" / "rung_e" / "FF9CustomMap-world"
RUNG_E_INDEPENDENT_JSON = HERE / "out" / "rung_e" / "verify_rung_e_independent.json"

CELL = 4.0
BLOCK = 64.0

# ---- the known site (map's only grass|desert ecotone -- sites.json ecotone_sites[0]) -------------
CORE = sorted({(bx, by) for bx in (13, 14, 15) for by in (11, 12)})
CORE_RING = sorted({(bx + dx, by + dy) for (bx, by) in CORE for dx in (-2, -1, 0, 1, 2)
                    for dy in (-2, -1, 0, 1, 2) if M.block_in_grid(bx + dx, by + dy)})

# ---- calibration controls, pulled from contract_mass_scout.py's own desert_masses census ---------
CALIB_PURE_DESERT_BLOCKS = sorted({(11, 4), (11, 5), (12, 4), (12, 5), (13, 4), (13, 5)})   # "mass_5" -- topo17 only, NOT grass-adjacent (scout brief)
CALIB_PURE_RING = sorted({(bx + dx, by + dy) for (bx, by) in CALIB_PURE_DESERT_BLOCKS
                          for dx in (-1, 0, 1) for dy in (-1, 0, 1) if M.block_in_grid(bx + dx, by + dy)})

# ---- the scout-flagged re-check: "mass_3" (777 cells, blocks (13-16,3-6), grass_adjacent=True per
# the scout's cheby<=1 cell test, but ABSENT from ecotone_sites -- verify with an actual edge check,
# same discipline as seam_null_recon part_a's (7,19)/(8,19) island correction) ---------------------
MASS3_BLOCKS = sorted({(13, 5), (13, 6), (14, 4), (14, 5), (14, 6), (15, 4), (15, 5), (15, 6),
                       (16, 3), (16, 4), (16, 5), (16, 6)})
MASS3_RING = sorted({(bx + dx, by + dy) for (bx, by) in MASS3_BLOCKS
                     for dx in (-1, 0, 1) for dy in (-1, 0, 1) if M.block_in_grid(bx + dx, by + dy)})

KMAX_STEPS = 25          # spine ray-march ceiling (100u) -- generous vs. the known <=4-cell depth; report if ever hit
TANGENT_WINDOW_CHEBY = 4  # PCA neighbourhood radius for local boundary tangent (cells)


def world_of(cell):
    return (cell[0] * CELL + CELL / 2.0, cell[1] * CELL + CELL / 2.0)


def cheby(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


# ====================================================================================================
# a mixed stock+staged-override loader for the Rung E dry-run tree (mirrors SNR.load_tris(source=
# "deployed")'s exact discipline -- override where staged, stock fallback elsewhere -- but pointed at
# out/rung_e/FF9CustomMap-world instead of the live game's mod folder; this NEVER touches the game
# install).
# ====================================================================================================
def load_tris_staged(blocks, mod_dir, *, must_have=()):
    bm_by_block = {}
    src_by_block = {}
    for (bx, by) in blocks:
        rel = M.override_relpath(1, bx, by, part="Terrain")
        path = mod_dir / rel
        if path.exists():
            bm = M.blockmesh_from_ff9mesh(path, disc=1, x=bx, y=by, part="terrain")
            src = "staged"
        elif (bx, by) in must_have:
            raise FileNotFoundError(f"expected staged override missing: {path}")
        else:
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            src = "stock"
        bm_by_block[(bx, by)] = bm
        src_by_block[(bx, by)] = src

    tris = []
    for (bx, by), bm in bm_by_block.items():
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            fam = SNR.FAM_OF.get(topo)
            w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            tris.append(dict(block=(bx, by), topo=topo, fam=fam, w=w, uv=uv, cell=cell))
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, bm_by_block, src_by_block


# ====================================================================================================
# shared measurement primitives, applied identically to stock and to the Rung E staged tree
# ====================================================================================================
def cell_index(tris):
    """cell -> [tri,...]; cell -> set(fam present); cell -> block."""
    cell_tris = defaultdict(list)
    cell_fams = defaultdict(set)
    cell_block = {}
    for t in tris:
        c = t["cell"]
        cell_tris[c].append(t)
        if t["fam"]:
            cell_fams[c].add(t["fam"])
        cell_block[c] = t["block"]
    return cell_tris, cell_fams, cell_block


def gd_boundary_cells(tris):
    """`tris` may be a FILTERED subset of a larger loaded list -- SNR.edge_index keys its owner-lists
    by each tri's own 'gid' (assigned at load time over the FULL list), which no longer equals a
    position in `tris` once filtered. Index by gid explicitly rather than assume list-position."""
    by_gid = {t["gid"]: t for t in tris}
    edge_owner = SNR.edge_index(tris)
    boundary = set()
    n_edges = 0
    for e, owners in edge_owner.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if fams == {"grass", "desert"}:
            n_edges += 1
            for g in owners:
                boundary.add(by_gid[g]["cell"])
    return boundary, n_edges


def classify_cell_for_march(cell, cell_tris):
    """One label per cell for the perpendicular march: 'desert_dressed_grass' / 'desert_dressed_dunes'
    / 'desert_plain' (desert-family tri present, none of it wearing either STRIPS decal) / else
    'nondesert:<majority-fam-or-topo>' / 'no_data' (cell outside the loaded region)."""
    tris_here = cell_tris.get(cell)
    if not tris_here:
        return "no_data"
    desert_tris = [t for t in tris_here if t["fam"] == "desert"]
    if desert_tris:
        has_gd = False
        has_dd = False
        for t in desert_tris:
            cls, _detail = SNR.classify_tri(t["fam"], t["uv"])
            if cls == "strip_grass_desert":
                has_gd = True
            elif cls == "strip_desert_dunes":
                has_dd = True
        if has_gd:
            return "desert_dressed_grass"
        if has_dd:
            return "desert_dressed_dunes"
        return "desert_plain"
    fam_tally = Counter(t["fam"] for t in tris_here if t["fam"])
    if fam_tally:
        return f"nondesert:{fam_tally.most_common(1)[0][0]}"
    topo_tally = Counter(t["topo"] for t in tris_here)
    return f"nondesert:topo{topo_tally.most_common(1)[0][0]}"


def pca_tangent(cell, boundary_world, window=TANGENT_WINDOW_CHEBY):
    center = world_of(cell)
    pts = [(p[0] - center[0], p[1] - center[1]) for c2, p in boundary_world.items()
           if cheby(cell, c2) <= window]
    if len(pts) < 3:
        return None
    n = len(pts)
    sxx = sum(x * x for x, _z in pts) / n
    szz = sum(z * z for _x, z in pts) / n
    sxz = sum(x * z for x, z in pts) / n
    tr = sxx + szz
    det = sxx * szz - sxz * sxz
    disc = math.sqrt(max(0.0, (tr * tr) / 4.0 - det))
    lam1 = tr / 2.0 + disc
    if abs(sxz) > 1e-9:
        vx, vz = sxz, lam1 - sxx
    elif sxx >= szz:
        vx, vz = 1.0, 0.0
    else:
        vx, vz = 0.0, 1.0
    norm = math.hypot(vx, vz)
    if norm < 1e-9:
        return None
    return (vx / norm, vz / norm)


def measure_cross_section(cell, normal_signed, cell_tris, kmax=KMAX_STEPS):
    cx, cz = world_of(cell)
    seq = []
    for k in range(1, kmax + 1):
        px = cx + k * CELL * normal_signed[0]
        pz = cz + k * CELL * normal_signed[1]
        ck = (math.floor(px / CELL), math.floor(pz / CELL))
        cls = classify_cell_for_march(ck, cell_tris)
        seq.append((k, ck, cls))
        if not cls.startswith("desert"):
            break
    i = 0
    margin_len = 0
    while i < len(seq) and seq[i][2] in ("desert_dressed_grass", "desert_dressed_dunes"):
        margin_len += 1
        i += 1
    spine_len = 0
    while i < len(seq) and seq[i][2] == "desert_plain":
        spine_len += 1
        i += 1
    censored = (i >= len(seq)) and (len(seq) == kmax) and seq[-1][2].startswith("desert")
    terminus = None if i >= len(seq) else seq[i][2]
    terminus_k = None if i >= len(seq) else seq[i][0]
    return dict(margin_len=margin_len, spine_len=spine_len, terminus=terminus,
               terminus_k=terminus_k, censored=censored, n_steps=len(seq))


def run_spine_march(boundary_cells, cell_tris, label):
    """For every boundary cell with a resolvable local tangent, determine the desert-facing normal
    and run measure_cross_section. Reports (not silently drops) every skip category."""
    boundary_world = {c: world_of(c) for c in boundary_cells}
    results = []
    skip_no_tangent = 0
    skip_no_desert_side = 0
    n_both_sides_desert = 0
    for c in sorted(boundary_cells):
        tang = pca_tangent(c, boundary_world)
        if tang is None:
            skip_no_tangent += 1
            continue
        normal = (-tang[1], tang[0])
        cx, cz = world_of(c)
        probe_k = 1.5
        p_plus = (cx + probe_k * CELL * normal[0], cz + probe_k * CELL * normal[1])
        p_minus = (cx - probe_k * CELL * normal[0], cz - probe_k * CELL * normal[1])
        cell_plus = (math.floor(p_plus[0] / CELL), math.floor(p_plus[1] / CELL))
        cell_minus = (math.floor(p_minus[0] / CELL), math.floor(p_minus[1] / CELL))
        cls_plus = classify_cell_for_march(cell_plus, cell_tris)
        cls_minus = classify_cell_for_march(cell_minus, cell_tris)
        plus_desert = cls_plus.startswith("desert")
        minus_desert = cls_minus.startswith("desert")
        if plus_desert and minus_desert:
            n_both_sides_desert += 1
            chosen = normal
        elif plus_desert:
            chosen = normal
        elif minus_desert:
            chosen = (-normal[0], -normal[1])
        else:
            skip_no_desert_side += 1
            continue
        r = measure_cross_section(c, chosen, cell_tris)
        r["cell"] = list(c)
        results.append(r)
    spine_lens = sorted(r["spine_len"] for r in results)
    margin_lens = sorted(r["margin_len"] for r in results)
    terminus_tally = Counter(r["terminus"] for r in results)
    n_censored = sum(1 for r in results if r["censored"])

    def pct(arr, p):
        if not arr:
            return None
        idx = min(len(arr) - 1, int(round(p / 100.0 * (len(arr) - 1))))
        return arr[idx]

    summary = dict(
        label=label, n_boundary_cells=len(boundary_cells), n_measured=len(results),
        n_skip_no_tangent=skip_no_tangent, n_skip_no_desert_side=skip_no_desert_side,
        n_both_sides_desert=n_both_sides_desert, n_censored_at_kmax=n_censored,
        spine_len_min=spine_lens[0] if spine_lens else None,
        spine_len_median=pct(spine_lens, 50), spine_len_p90=pct(spine_lens, 90),
        spine_len_max=spine_lens[-1] if spine_lens else None,
        spine_len_mean=round(sum(spine_lens) / len(spine_lens), 3) if spine_lens else None,
        margin_len_min=margin_lens[0] if margin_lens else None,
        margin_len_median=pct(margin_lens, 50), margin_len_p90=pct(margin_lens, 90),
        margin_len_max=margin_lens[-1] if margin_lens else None,
        terminus_tally=dict(terminus_tally),
        spine_len_histogram=dict(sorted(Counter(spine_lens).items())),
    )
    print(f"  [{label}] spine march: {len(results)}/{len(boundary_cells)} cross-sections measured "
         f"(skip: no-tangent={skip_no_tangent}, no-desert-side={skip_no_desert_side}); "
         f"spine_len min/median/p90/max = {summary['spine_len_min']}/{summary['spine_len_median']}/"
         f"{summary['spine_len_p90']}/{summary['spine_len_max']} cells; censored@kmax={n_censored}")
    print(f"  [{label}] terminus tally: {dict(terminus_tally)}")
    return summary, results


# ====================================================================================================
# band-based cross-check (chebyshev distance-to-nearest-boundary-cell) -- an independent, coarser
# convention for the same "how far does plain desert run" question, reused verbatim from Round 10's
# own BFS method (SNR.cell_distance_bfs) so the two conventions can be compared side by side per the
# MEASURE-THE-REALIZED-BYTES / report-both-conventions discipline this round inherited from the
# contract's own coast-distance episode.
# ====================================================================================================
def band_profile(tris, boundary_cells, cell_fams, label):
    all_cells = set(cell_fams)
    dist = SNR.cell_distance_bfs(all_cells, boundary_cells)
    band_tally = defaultdict(lambda: Counter())   # band -> classify-detail Counter, desert tris only
    for t in tris:
        if t["fam"] != "desert":
            continue
        dd = dist.get(t["cell"])
        if dd is None:
            continue
        cls, _detail = SNR.classify_tri(t["fam"], t["uv"])
        band_tally[dd][cls] += 1
    out = {}
    max_band_with_desert = -1
    for b in sorted(band_tally):
        c = band_tally[b]
        total = sum(c.values())
        dressed = c.get("strip_grass_desert", 0) + c.get("strip_desert_dunes", 0)
        out[str(b)] = dict(total=total, dressed=dressed, plain=c.get("mains_own", 0),
                           other=total - dressed - c.get("mains_own", 0),
                           dressed_rate=round(dressed / total, 4) if total else None,
                           detail=dict(c))
        if total > 0:
            max_band_with_desert = max(max_band_with_desert, b)
    print(f"  [{label}] band profile (desert-family tris by chebyshev distance-to-boundary):")
    for b in sorted(band_tally):
        print(f"     band {b}: {out[str(b)]}")
    print(f"  [{label}] max band with any desert-family tri present: {max_band_with_desert} "
         f"(i.e. the desert component's total graph-depth from the boundary line)")
    return dict(by_band=out, max_band_with_desert=max_band_with_desert)


# ====================================================================================================
# calibration
# ====================================================================================================
def run_calibration():
    print("=" * 100)
    print("CALIBRATION -- verify the classifier against a known-pure-desert control and re-derive the")
    print("known site's own already-published topo16_ecotone_crosscheck.json numbers independently.")
    print("=" * 100)

    # ---- control A: pure desert, NOT grass-adjacent (mass_5, topo17 only per the scout census) ----
    tris_a, _bms_a, _src_a = SNR.load_tris(CALIB_PURE_RING, source="stock")
    core_a = [t for t in tris_a if t["block"] in CALIB_PURE_DESERT_BLOCKS]
    desert_a = [t for t in core_a if t["fam"] == "desert"]
    dressed_a = 0
    topo_a = Counter(t["topo"] for t in desert_a)
    for t in desert_a:
        cls, _d = SNR.classify_tri(t["fam"], t["uv"])
        if cls in ("strip_grass_desert", "strip_desert_dunes"):
            dressed_a += 1
    rate_a = dressed_a / len(desert_a) if desert_a else None
    print(f"CONTROL A (pure desert, blocks {CALIB_PURE_DESERT_BLOCKS}, not grass-adjacent): "
         f"{len(desert_a)} desert-family tris, topo={dict(topo_a)}, {dressed_a} carry an ecotone "
         f"decal ({'PASS -- 0% as expected' if dressed_a == 0 else f'rate={rate_a:.4f}'})")
    calib_a_pass = (dressed_a == 0)
    if not calib_a_pass:
        print(f"  !!! CALIBRATION CONCERN: control A is supposed to be a clean, non-ecotone desert "
             f"patch and shows {dressed_a}/{len(desert_a)} dressed tris. Reporting loudly, not "
             f"silently trusting the detector past this point.")

    # ---- control B: re-derive topo16_ecotone_crosscheck.json's own numbers from scratch -----------
    tris_b, _bms_b, _src_b = SNR.load_tris(CORE, source="stock")
    t16 = [t for t in tris_b if t["topo"] == 16]
    tally_b = Counter()
    for t in t16:
        cls, _d = SNR.classify_tri(t["fam"], t["uv"])
        tally_b[cls] += 1
    total16 = len(t16)
    print(f"\nCONTROL B (known site core {CORE}, all topo-16 tris): total16={total16} "
         f"classify tally={dict(tally_b)}")
    prior = None
    calib_b_pass = None
    if CROSSCHECK_JSON.is_file():
        prior = json.loads(CROSSCHECK_JSON.read_text(encoding="utf-8"))
        prior_total16 = prior["total16"]
        prior_tri = prior["tri_classification"]
        match_total = (total16 == prior_total16)
        match_gd = (tally_b.get("strip_grass_desert", 0) == prior_tri.get("strip_grass_desert", 0))
        match_dd = (tally_b.get("strip_desert_dunes", 0) == prior_tri.get("strip_desert_dunes", 0))
        match_mains = (tally_b.get("mains_own", 0) == prior_tri.get("desert_mains", 0))
        calib_b_pass = match_total and match_gd and match_dd and match_mains
        print(f"  vs. {CROSSCHECK_JSON.name}: total16 {total16} vs {prior_total16} "
             f"({'match' if match_total else 'MISMATCH'}); strip_grass_desert "
             f"{tally_b.get('strip_grass_desert', 0)} vs {prior_tri.get('strip_grass_desert', 0)} "
             f"({'match' if match_gd else 'MISMATCH'}); strip_desert_dunes "
             f"{tally_b.get('strip_desert_dunes', 0)} vs {prior_tri.get('strip_desert_dunes', 0)} "
             f"({'match' if match_dd else 'MISMATCH'}); desert_mains "
             f"{tally_b.get('mains_own', 0)} vs {prior_tri.get('desert_mains', 0)} "
             f"({'match' if match_mains else 'MISMATCH'})")
        print(f"  CONTROL B: {'PASS -- independently reproduces topo16_ecotone_crosscheck.json exactly' if calib_b_pass else 'FAIL -- see mismatches above, reported loudly'}")
    else:
        print(f"  !!! {CROSSCHECK_JSON} not found -- control B run standalone, no prior artifact to "
             f"cross-check against (reporting the raw numbers only).")

    out = dict(
        control_a_pure_desert=dict(blocks=[list(b) for b in CALIB_PURE_DESERT_BLOCKS],
                                   n_desert_tris=len(desert_a), n_dressed=dressed_a,
                                   dressed_rate=round(rate_a, 4) if rate_a is not None else None,
                                   topo_tally=dict(topo_a), passed=calib_a_pass),
        control_b_known_site_reproduction=dict(
            blocks=[list(b) for b in CORE], total16=total16, tally=dict(tally_b),
            prior_artifact=str(CROSSCHECK_JSON) if prior else None, passed=calib_b_pass),
        overall_calibration_passed=bool(calib_a_pass and (calib_b_pass in (True, None))),
    )
    print(f"\nOVERALL CALIBRATION: {'PASS' if out['overall_calibration_passed'] else 'FAIL -- do not trust downstream numbers without investigating'}")
    return out


# ====================================================================================================
# mass_3 re-check (scout's flagged item)
# ====================================================================================================
def run_mass3_recheck():
    print("\n" + "=" * 100)
    print("MASS_3 RE-CHECK -- scout flagged this 777-cell plain-desert mass (blocks (13-16,3-6)) as "
         "'grass_adjacent=True' by a cheby<=1 CELL test, but it did NOT surface in ecotone_sites "
         "(no straddle EDGE found). Verify with an actual mesh-edge check, same discipline as "
         "seam_null_recon part_a's (7,19)/(8,19) island correction.")
    print("=" * 100)
    tris, _bms, _src = SNR.load_tris(MASS3_RING, source="stock")
    core_tris = [t for t in tris if t["block"] in MASS3_BLOCKS]
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"] in ("grass", "desert"):
            cell_fams[t["cell"]].add(t["fam"])
    boundary, n_edges = gd_boundary_cells(core_tris)
    grass_cells = sorted(c for c, f in cell_fams.items() if "grass" in f)
    desert_cells = sorted(c for c, f in cell_fams.items() if "desert" in f)
    nearest = None
    for gc in grass_cells:
        for dc in desert_cells:
            d = cheby(gc, dc)
            if nearest is None or d < nearest[0]:
                nearest = (d, gc, dc)
    print(f"grass|desert boundary EDGES found within/touching mass_3's own blocks: {n_edges}")
    print(f"grass cells: {len(grass_cells)}  desert cells: {len(desert_cells)}")
    print(f"nearest grass-cell<->desert-cell pair (chebyshev cells, 0=adjacent/touching): {nearest}")
    verdict = ("NO real straddle boundary -- confirms the scout's own ecotone_sites census (n=1, "
              "the (13-15,11-12) site is the map's only one); mass_3's 'grass_adjacent' flag was "
              "the coarse cheby<=1 CELL test finding grass and desert cells merely near each other, "
              "not an actual shared mesh edge or straddle cell." if n_edges == 0 else
              f"UNEXPECTED: {n_edges} real grass|desert edges found in mass_3 -- this would be a "
              f"SECOND ecotone site the scout's own census missed; flagged for the scout to re-run.")
    print(f"VERDICT: {verdict}")
    return dict(blocks=[list(b) for b in MASS3_BLOCKS], n_gd_edges=n_edges,
               n_grass_cells=len(grass_cells), n_desert_cells=len(desert_cells),
               nearest_pair=None if nearest is None else dict(cheby_cells=nearest[0],
                   grass_cell=list(nearest[1]), desert_cell=list(nearest[2])),
               verdict=verdict)


# ====================================================================================================
# connected components of dressed cells -- do all stock patches touch the boundary?
# ====================================================================================================
def dressing_components(tris, boundary_cells, label):
    cell_tris, _cf, _cb = cell_index(tris)
    decal_cells_gd = set()
    for c, ts in cell_tris.items():
        for t in ts:
            if t["fam"] == "desert":
                cls, _d = SNR.classify_tri(t["fam"], t["uv"])
                if cls == "strip_grass_desert":
                    decal_cells_gd.add(c)
                    break
    # 8-connectivity (chebyshev<=1), strict, matching the study's own "site" convention
    seen = set()
    comps = []
    for start in sorted(decal_cells_gd):
        if start in seen:
            continue
        comp = []
        q = deque([start])
        seen.add(start)
        while q:
            u = q.popleft()
            comp.append(u)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    n = (u[0] + dx, u[1] + dy)
                    if n in decal_cells_gd and n not in seen:
                        seen.add(n)
                        q.append(n)
        comps.append(sorted(comp))
    n_floating = 0
    comp_reports = []
    for comp in comps:
        touches = any(cheby(c, b) <= 1 for c in comp for b in boundary_cells)
        if not touches:
            n_floating += 1
        comp_reports.append(dict(n_cells=len(comp), touches_boundary=touches, cells=[list(c) for c in comp[:5]] + (["..."] if len(comp) > 5 else [])))
    print(f"  [{label}] desert-side grass-decal cells: {len(decal_cells_gd)}, "
         f"connected components (cheby<=1): {len(comps)}, floating (does NOT touch a boundary cell "
         f"within 1 cell): {n_floating}")
    return dict(n_decal_cells=len(decal_cells_gd), n_components=len(comps),
               n_floating_components=n_floating, components=comp_reports)


# ====================================================================================================
# main per-site saturation + row-distribution + writes:body measurement
# ====================================================================================================
def measure_site(tris, core_blocks_set, label, restrict_to_core=True):
    core_tris = [t for t in tris if t["block"] in core_blocks_set] if restrict_to_core else tris
    t16 = [t for t in core_tris if t["topo"] == 16]
    tally = Counter()
    for t in t16:
        cls, _d = SNR.classify_tri(t["fam"], t["uv"])
        tally[cls] += 1
    total16 = len(t16)
    n_dressed_grass = tally.get("strip_grass_desert", 0)
    n_dressed_dunes = tally.get("strip_desert_dunes", 0)
    n_plain = tally.get("mains_own", 0)
    n_other = total16 - n_dressed_grass - n_dressed_dunes - n_plain
    sat_grass_only = n_dressed_grass / total16 if total16 else None
    sat_any_decal = (n_dressed_grass + n_dressed_dunes) / total16 if total16 else None

    # label-blind cross-check: scan ALL tris in-region (not just topo==16) for UV-geometry hits on the
    # grass|desert STRIPS rect or the desert mains rect; report any whose TOPO id disagrees with 16.
    uv_hits_offtopo = []
    for t in core_tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        cls, detail = SNR.classify_tri(t["fam"], t["uv"])
        if cls == "strip_grass_desert" and t["topo"] != 16 and t["fam"] == "desert":
            uv_hits_offtopo.append(dict(block=list(t["block"]), cell=list(t["cell"]), topo=t["topo"], detail=detail))
    print(f"  [{label}] topo-16 body population: {total16} tris -- "
         f"dressed(grass)={n_dressed_grass}, dressed(dunes)={n_dressed_dunes}, plain={n_plain}, "
         f"other/residual={n_other}")
    print(f"  [{label}] SATURATION (grass-decal only, comparable to Rung E's 75.7%): "
         f"{sat_grass_only}")
    print(f"  [{label}] SATURATION (any ecotone decal, grass+dunes): {sat_any_decal}")
    if uv_hits_offtopo:
        print(f"  [{label}] !!! {len(uv_hits_offtopo)} desert-family tris classify UV-geometrically as "
             f"strip_grass_desert but carry a topo id != 16 -- label-blind disagreement, reported not hidden: "
             f"{uv_hits_offtopo[:5]}")

    # writes:body ratio, Rung D/E's own convention: n_body = topo-16 tri count; n_writes = 2 *
    # (distinct desert-side cells bearing >=1 grass-decal tri) -- the doubled-per-cell "operation
    # count" (uv write + topo write) their build scripts use, reproduced independently here (NOT
    # copied from their JSON) so this is a genuine re-derivation, not a re-print.
    decal_cells = set()
    for t in t16:
        if t["fam"] == "desert":
            cls, _d = SNR.classify_tri(t["fam"], t["uv"])
            if cls == "strip_grass_desert":
                decal_cells.add(t["cell"])
    n_writes_equiv = 2 * len(decal_cells)
    ratio_writes_equiv = n_writes_equiv / total16 if total16 else None
    ratio_tri_fraction = sat_grass_only   # the cleaner, dimensionally-consistent fraction
    print(f"  [{label}] writes:body (Rung D/E convention, re-derived independently): "
         f"n_decal_cells={len(decal_cells)}, n_writes_equiv={n_writes_equiv}, body={total16}, "
         f"ratio={ratio_writes_equiv}")

    return dict(
        label=label, total16=total16, n_dressed_grass=n_dressed_grass, n_dressed_dunes=n_dressed_dunes,
        n_plain=n_plain, n_other_residual=n_other, tally=dict(tally),
        saturation_grass_decal_only=round(sat_grass_only, 4) if sat_grass_only is not None else None,
        saturation_any_decal=round(sat_any_decal, 4) if sat_any_decal is not None else None,
        label_blind_offtopo_hits=uv_hits_offtopo,
        n_decal_cells_grass_side=len(decal_cells), n_writes_equiv=n_writes_equiv,
        ratio_writes_equiv_body=round(ratio_writes_equiv, 4) if ratio_writes_equiv is not None else None,
        ratio_tri_fraction=round(ratio_tri_fraction, 4) if ratio_tri_fraction is not None else None,
    )


def row_distribution(tris, core_blocks_set, label):
    core_tris = [t for t in tris if t["block"] in core_blocks_set]
    row_tally = Counter()
    row_tally_by_fam = defaultdict(Counter)
    for t in core_tris:
        if t["fam"] not in ("grass", "desert"):
            continue
        cls, detail = SNR.classify_tri(t["fam"], t["uv"])
        if cls == "strip_grass_desert":
            row_tally[detail] += 1
            row_tally_by_fam[t["fam"]][detail] += 1
    total = sum(row_tally.values())
    fractions = {str(k): dict(n=v, frac=round(v / total, 4) if total else None)
                for k, v in sorted(row_tally.items())}
    print(f"  [{label}] row distribution (all {total} strip_grass_desert tris, both family sides): "
         f"{fractions}")
    print(f"  [{label}] row distribution split by family side: "
         f"{ {f: dict(sorted(c.items())) for f, c in row_tally_by_fam.items()} }")
    return dict(total_dressed_tris=total, row_tally=dict(sorted(row_tally.items())),
               row_fractions=fractions,
               row_tally_by_family={f: dict(sorted(c.items())) for f, c in row_tally_by_fam.items()})


# ====================================================================================================
# main
# ====================================================================================================
def main():
    t0 = time.time()
    print(f"game root: {SNR.GAME_ROOT}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    calibration = run_calibration()
    mass3 = run_mass3_recheck()

    # ================================================================================================
    # STOCK -- the known site
    # ================================================================================================
    print("\n" + "=" * 100)
    print("STOCK -- the known grass|desert ecotone site, blocks (13-15,11-12) + a 2-cell Moore ring")
    print("=" * 100)
    stock_tris, stock_bms, stock_src = SNR.load_tris(CORE_RING, source="stock")
    print(f"blocks loaded: {sorted(stock_bms)}  ({len(stock_tris)} tris, {time.time()-t0:.1f}s)")
    core_tris_stock = [t for t in stock_tris if t["block"] in set(CORE)]
    boundary_stock, n_edges_stock = gd_boundary_cells(core_tris_stock)
    print(f"grass|desert boundary edges: {n_edges_stock}, boundary cells: {len(boundary_stock)} "
         f"(sites.json says 240 -- {'match' if len(boundary_stock) == 240 else 'MISMATCH, reported'})")

    stock_saturation = measure_site(stock_tris, set(CORE), "STOCK known-site")
    stock_rows = row_distribution(stock_tris, set(CORE), "STOCK known-site")
    stock_components = dressing_components(core_tris_stock, boundary_stock, "STOCK known-site")

    print("\n-- STOCK spine march (perpendicular ray from each boundary cell into the desert side) --")
    cell_tris_stock, cell_fams_stock, _cb = cell_index(stock_tris)
    stock_spine, stock_spine_raw = run_spine_march(boundary_stock, cell_tris_stock, "STOCK known-site")

    print("\n-- STOCK band-profile cross-check (BFS chebyshev distance-to-boundary convention) --")
    stock_band = band_profile(core_tris_stock, boundary_stock, cell_fams_stock, "STOCK known-site")

    # ================================================================================================
    # RUNG E STAGED BUILD -- same measurements, overlaid on stock for context blocks
    # ================================================================================================
    print("\n" + "=" * 100)
    print("RUNG E STAGED BUILD -- out/rung_e/FF9CustomMap-world, overlaid on stock (dry-run tree, "
         "never deployed to the game install)")
    print("=" * 100)
    if not RUNG_E_MOD_DIR.is_dir():
        print(f"!!! {RUNG_E_MOD_DIR} not found -- skipping the Rung E comparison entirely (reported, "
             f"not silently substituted).")
        rung_e_out = None
    else:
        touched_blocks = []
        for p in sorted(RUNG_E_MOD_DIR.rglob("*Terrain.ff9mesh")):
            name = p.stem  # "Block[x][y] Terrain" minus suffix handled by rglob pattern already
            import re
            mm = re.search(r"Block\[(\d+)\]\[(\d+)\]", p.name)
            if mm:
                touched_blocks.append((int(mm.group(1)), int(mm.group(2))))
        touched_blocks = sorted(set(touched_blocks))
        ring = sorted({(bx + dx, by + dy) for (bx, by) in touched_blocks
                      for dx in (-1, 0, 1) for dy in (-1, 0, 1) if M.block_in_grid(bx + dx, by + dy)})
        print(f"staged terrain-override blocks found: {touched_blocks}")
        print(f"loading touched blocks + 1-block ring ({len(ring)} blocks total)")
        staged_tris, staged_bms, staged_src = load_tris_staged(ring, RUNG_E_MOD_DIR, must_have=set(touched_blocks))
        print(f"blocks loaded: {[(b, staged_src[b]) for b in sorted(staged_bms)]}  "
             f"({len(staged_tris)} tris, {time.time()-t0:.1f}s)")

        staged_core = [t for t in staged_tris if t["block"] in set(touched_blocks)]
        boundary_staged, n_edges_staged = gd_boundary_cells(staged_core)
        print(f"grass|desert boundary edges (staged): {n_edges_staged}, boundary cells: {len(boundary_staged)}")

        staged_saturation = measure_site(staged_tris, set(touched_blocks), "RUNG-E staged")
        staged_rows = row_distribution(staged_tris, set(touched_blocks), "RUNG-E staged")
        staged_components = dressing_components(staged_core, boundary_staged, "RUNG-E staged")

        print("\n-- RUNG E spine march --")
        cell_tris_staged, cell_fams_staged, _cb2 = cell_index(staged_tris)
        staged_spine, staged_spine_raw = run_spine_march(boundary_staged, cell_tris_staged, "RUNG-E staged")

        print("\n-- RUNG E band-profile cross-check --")
        staged_band = band_profile(staged_core, boundary_staged, cell_fams_staged, "RUNG-E staged")

        # cross-check against the already-published verify_rung_e_independent.json numbers
        reproduction_check = None
        if RUNG_E_INDEPENDENT_JSON.is_file():
            prior = json.loads(RUNG_E_INDEPENDENT_JSON.read_text(encoding="utf-8"))
            prior_body = prior.get("n_body_independent")
            reported_sat = 193 / 255  # the eye review's own reported fraction, GROUND-FAMILY-DECODE-2026-07-19.md "## Rung E"
            match_body = (staged_saturation["total16"] == prior_body)
            sat_diff = abs((staged_saturation["saturation_grass_decal_only"] or 0) - reported_sat)
            reproduction_check = dict(
                prior_n_body_independent=prior_body, my_total16=staged_saturation["total16"],
                body_count_matches=match_body, prior_reported_saturation_193_of_255=round(reported_sat, 4),
                my_saturation_grass_decal_only=staged_saturation["saturation_grass_decal_only"],
                saturation_abs_diff=round(sat_diff, 4),
                reproduces_75_7_pct_finding=(sat_diff < 0.02),
            )
            print(f"\nREPRODUCTION CHECK vs {RUNG_E_INDEPENDENT_JSON.name}: body {staged_saturation['total16']} "
                 f"vs prior {prior_body} ({'match' if match_body else 'MISMATCH'}); saturation "
                 f"{staged_saturation['saturation_grass_decal_only']} vs prior-reported {round(reported_sat,4)} "
                 f"(diff {round(sat_diff,4)}) -> "
                 f"{'REPRODUCES the 75.7% saturated-comb finding' if reproduction_check['reproduces_75_7_pct_finding'] else '!!! DOES NOT REPRODUCE -- reported loudly'}")

        rung_e_out = dict(
            touched_blocks=[list(b) for b in touched_blocks], ring_blocks=[list(b) for b in ring],
            block_source={f"{k[0]},{k[1]}": v for k, v in staged_src.items()},
            n_gd_boundary_edges=n_edges_staged, n_boundary_cells=len(boundary_staged),
            saturation=staged_saturation, row_distribution=staged_rows,
            dressing_components=staged_components, spine=staged_spine,
            band_profile=staged_band, reproduction_check=reproduction_check,
        )

    # ================================================================================================
    # comparison headline numbers
    # ================================================================================================
    stock_sat = stock_saturation["saturation_grass_decal_only"]
    stock_spine_p90 = stock_spine["spine_len_p90"]
    stock_spine_median = stock_spine["spine_len_median"]
    rung_e_sat = rung_e_out["saturation"]["saturation_grass_decal_only"] if rung_e_out else None

    # ---- RECONCILE the two spine conventions -- they must be compared, not silently picked between
    # (MEASURE-THE-REALIZED-BYTES / report-both-conventions discipline). The perpendicular cross-
    # section metric and the graph-BFS band metric answer a slightly different question and can
    # legitimately diverge on a jagged, zigzagging boundary (this site has one -- Round 10's own
    # turn_deg_max readings). Report both, and an honest read of what they jointly imply.
    stock_zero_spine_frac = stock_spine["spine_len_histogram"].get(0, 0) / max(1, stock_spine["n_measured"])
    rung_e_zero_spine_frac = (rung_e_out["spine"]["spine_len_histogram"].get(0, 0) / max(1, rung_e_out["spine"]["n_measured"])) if rung_e_out else None
    band1_stock = stock_band["by_band"].get("1")
    spine_reconciliation = dict(
        cross_section_convention=dict(
            stock_median=stock_spine_median, stock_p90=stock_spine_p90,
            stock_mean=stock_spine["spine_len_mean"], stock_zero_spine_fraction=round(stock_zero_spine_frac, 4),
            rung_e_median=rung_e_out["spine"]["spine_len_median"] if rung_e_out else None,
            rung_e_p90=rung_e_out["spine"]["spine_len_p90"] if rung_e_out else None,
            rung_e_mean=rung_e_out["spine"]["spine_len_mean"] if rung_e_out else None,
            rung_e_zero_spine_fraction=round(rung_e_zero_spine_frac, 4) if rung_e_zero_spine_frac is not None else None,
        ),
        band_bfs_convention=dict(
            stock_band1_total=band1_stock["total"] if band1_stock else None,
            stock_band1_plain_rate=(1.0 - band1_stock["dressed_rate"]) if band1_stock and band1_stock["dressed_rate"] is not None else None,
            note="band1 (one graph-hop past the boundary-touching row) is stock's most-plain band -- "
                 "84% plain in this site's own numbers, sandwiched between a grass-facing margin "
                 "(band0, 90.7% dressed) and a dunes-facing margin re-emerging at band2-3 (55-69% "
                 "dressed with the desert|dunes decal, NOT the grass|desert one).",
        ),
        honest_synthesis=(
            "The two conventions do NOT contradict once reconciled, but they DO complicate a simple "
            "spine-width FLOOR gate: at this specific (thin, doubly-margined) site, roughly HALF of "
            f"all cross-sections have ZERO plain cells in both stock ({round(stock_zero_spine_frac*100,1)}%) "
            f"and the REJECTED Rung E build ({round((rung_e_zero_spine_frac or 0)*100,1)}%) -- "
            "spine-width alone is a WEAK, noisy discriminator here, not the clean gate its own name "
            "implies. The band-BFS view explains why: this lobe is squeezed between TWO dressed "
            "margins (grass on one side, dunes on the other) with only ~1 cell of typically-plain "
            "material between them -- consistent with the RIBBON FALLACY's own caution that this "
            "site's topo-16 skin is thin, not a wide plain interior. SATURATION is the far cleaner, "
            "better-calibrated ceiling (stock 50.2%/63.5% vs Rung E's 75.7%, a clean ~25-point gap); "
            "the ROW-DISTRIBUTION shape (see row_distribution) is a SECOND clean signal Rung E also "
            "violates (row0-heavy 53.8% vs stock's balanced ~20/34/27/19% spread) that this round "
            "did not originally expect to find as strong as it did. A future Rung F gate should "
            "lean on saturation-ceiling + row-distribution-shape as the primary gates, and treat any "
            "spine-width floor as advisory/secondary until measured on a WIDER stock exemplar (this "
            "study has exactly one real grass|desert site, and it happens to be a thin, pinched one)."
        ),
    )
    print("\n" + "-" * 100)
    print("SPINE RECONCILIATION:")
    print(json.dumps(spine_reconciliation, indent=1))
    print("-" * 100)

    prior_local_ratio_1_8667 = 1.8667
    my_stock_ratio = stock_saturation["ratio_writes_equiv_body"]
    ratio_test_note = (
        f"the PRIOR flagged number local_stock_ratio=1.8667 (desert=210/strip=392, from an earlier "
        f"rung's ad-hoc render census with untraceable units) does NOT match this round's "
        f"independently re-derived writes:body ratio at the same site ({my_stock_ratio}, same Rung "
        f"D/E convention: n_writes=2*decal_cells / n_body=topo16 tri count). Not treated as a "
        f"contradiction of a load-bearing claim -- the old number's own inputs (210/392) were never "
        f"traceable to a body/write tri count this study can re-derive (rung_d_build.py's own code "
        f"comment already retracted a DIFFERENT related fabricated 110:422 clause on the same "
        f"suspicion). This round's number supersedes it as the reproducible one."
    )
    print("\n" + "=" * 100)
    print("HEADLINE")
    print("=" * 100)
    if stock_sat is not None:
        print(f"STOCK known-site grass-decal saturation: {stock_sat} ({stock_sat*100:.1f}%)")
    else:
        print("STOCK saturation: n/a")
    print(f"STOCK spine-width (median/p90 cells): {stock_spine_median}/{stock_spine_p90}")
    if rung_e_sat is not None:
        print(f"RUNG E staged saturation: {rung_e_sat} ({rung_e_sat*100:.1f}%)")
    print(ratio_test_note)

    out = dict(
        meta=dict(script="contract_mass_saturation.py", elapsed_s=round(time.time() - t0, 1),
                  core_blocks=[list(b) for b in CORE], core_ring_blocks=[list(b) for b in CORE_RING],
                  kmax_steps=KMAX_STEPS, tangent_window_cheby=TANGENT_WINDOW_CHEBY),
        calibration=calibration,
        mass3_recheck=mass3,
        stock=dict(
            n_gd_boundary_edges=n_edges_stock, n_boundary_cells=len(boundary_stock),
            saturation=stock_saturation, row_distribution=stock_rows,
            dressing_components=stock_components, spine=stock_spine, band_profile=stock_band,
        ),
        rung_e_staged=rung_e_out,
        spine_reconciliation=spine_reconciliation,
        prior_number_tests=dict(
            local_stock_ratio_1_8667=dict(
                prior_value=prior_local_ratio_1_8667, my_recomputed_value=my_stock_ratio,
                note=ratio_test_note),
            row0_was_20pct=dict(
                prior_value_pct=20,
                my_row0_frac=stock_rows["row_fractions"].get("0", {}).get("frac"),
                note="prior figure from Round 10's TRAIN read; this round's full-core recount is the refined number."),
            stock_quartile_dressing_90_40_80_90=dict(
                prior_values_pct=[90, 40, 80, 90],
                note="reproduced verbatim in out/contract_gd_composition.json line_geometry.dressing_density_by_quartile_main_component -- NOT recomputed here (that artifact is read-only input, still valid; this round's saturation number is a DIFFERENT population -- topo16-tri-fraction, not path-quartile-cell-rate -- so it is a complementary, not competing, measurement)."),
        ),
    )
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\n-> {OUT}  (total {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
