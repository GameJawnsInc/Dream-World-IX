"""RUNG F -- UV-FIX round 3 (2026-07-24): ONE WINDOW PER TRI (the stock lattice invariant).

Rounds 1+2 cured the 2305 collapsed-UV Terrain tris (flat green sheets) and re-drew the dropped
cells' (quad,ori) through build_landmass' OWN generator (assign_mains_seeded, seed 0xF92) so the
mesh-level (quad,ori) statistics now MATCH the frame-mint. Gates PASS, falsifier CONFIRMED -- yet the
per-pixel eye still reads directional STREAKING in the repaired zone, distinct from the frame grass in
the same image.

THE ROUND-3 HYPOTHESIS: the residual is CROSS-WINDOW INTERPOLATION, not the (quad,ori) FIELD. The 2305
synthesized tris are EAR-CLIP output -- NOT aligned to the 4u cell lattice. A tri whose 3 verts sit in
DIFFERENT cells got each vertex's UV from a DIFFERENT tile window (v1/v2 per-vertex own-cell
assignment), so per-pixel barycentric interpolation sweeps UV space BETWEEN windows mid-tri -- crossing
quadrant art = the streaks. Stock ground never does this because stock tessellates on the 4u lattice:
every tri sits inside ONE cell = ONE tile window per tri.

STEP 1 (this file's probe, run FIRST, decide before building): over FIXED2's 2305 rewritten tris,
count the DISTINCT own-cells the 3 verts occupy (1/2/3) and, for multi-cell tris, the UV-space
excursion of the barycentric sweep (max pairwise UV dist vs the ~one-quadrant-window scale). Measure
the CONVERSE on the frame-mint's own grass tris (fraction all-3-verts-in-one-cell). If <~30% of the
2305 are multi-window -> hypothesis REFUTED, do NOT build.

STEP 2 (only if confirmed): FIXED3A = re-run the v2 pipeline with the IDENTICAL (quad,ori) cell field
(assign_mains_seeded, seed 0xF92) and IDENTICAL apron normals / Sea4 restore, but ONE change: every
defective tri's 3 vertex UVs are computed against a SINGLE window -- the tri's CENTROID cell's
(quad,ori) -- ground_uv(vx,vz, centroid_cell, q, o, 'grass') for all 3 verts. ONE WINDOW PER TRI.

READ-ONLY vs the game install.
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

import uvf_fix2 as F2                                           # noqa: E402  (functions only at import)

CH_POS, CH_NRM, CH_UV, CH_TAN = X.CH_POS, X.CH_NRM, X.CH_UV, X.CH_TAN
CELL = 4.0
UV_EPS = 1e-6
AREA_EPS = 1e-6
V2_SEED = F2.V2_SEED                                            # 0xF92

RUNG_F = HERE / "out" / "rung_f"
SPEC = RUNG_F / "FF9CustomMap-world"
FIXED = RUNG_F / "FF9CustomMap-world-FIXED"
FIXED2 = RUNG_F / "FF9CustomMap-world-FIXED2"
FIXED3A = RUNG_F / "FF9CustomMap-world-FIXED3A"
BUILD_JSON = RUNG_F / "rung_f_build.json"
FORENSICS = RUNG_F / "uvf_forensics.json"
REPORT = RUNG_F / "uvf_fix3_report.json"

# quadrant window geometry (the "one tile window" scale)
QU = G.GRASS_U_HALF          # [(u0,u1),(u0,u1)]
QV = G.GRASS_V_HALF
U_SPLIT = (QU[0][1] + QU[1][0]) / 2.0      # ~0.06543
V_SPLIT = (QV[0][1] + QV[1][0]) / 2.0      # ~0.79932
QUAD_W = QU[0][1] - QU[0][0]               # 0.06054
QUAD_H = QV[0][1] - QV[0][0]               # 0.03028
QUAD_DIAG = math.hypot(QUAD_W, QUAD_H)     # ~0.06769 = one-window scale
REGION_DIAG = math.hypot(QU[1][1] - QU[0][0], QV[1][1] - QV[0][0])   # full 2x2 diag ~0.1376


def log(m):
    print(m, flush=True)


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def own_cell(vx, vz):
    return (math.floor(vx / CELL), math.floor(vz / CELL))


def uv_window(u, v):
    """The quadrant (uh,vh) a UV lands in (by the internal split)."""
    return (0 if u < U_SPLIT else 1, 0 if v < V_SPLIT else 1)


def max_pairwise_uv(uv3):
    d = 0.0
    for a in range(3):
        for b in range(a + 1, 3):
            d = max(d, math.hypot(uv3[a][0] - uv3[b][0], uv3[a][1] - uv3[b][1]))
    return d


def load_blocks(root, touched):
    """block -> BlockMesh (flat)."""
    out = {}
    for (bx, by) in touched:
        p = F2.terr_path(root, bx, by)
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        assert bm.vcount == 3 * len(bm.tris) == len(bm.verts)
        out[(bx, by)] = bm
    return out


def classify_defective(spec_meshes, apron_keys, touched):
    """Classify the 2305 UV-degenerate tris from the SPECIMEN (its degenerate UVs are the defect).
    Returns list of dicts identical in structure to uvf_fix2 (block, tri, vids, vw, is_apron)."""
    defective = []
    lawful_grass = []           # (cell, vw, uv3) for the frame-mint converse + method-a
    for (bx, by) in touched:
        bm = spec_meshes[(bx, by)]
        ox, oz = X.block_world_origin(bx, by)
        verts = bm.chan_arrays[CH_POS]
        uvs = bm.chan_arrays[CH_UV]
        tans = bm.chan_arrays[CH_TAN]
        for t, tri in enumerate(bm.tris):
            j0, j1, j2 = tri
            vw = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in (j0, j1, j2)]
            uv3 = [(uvs[j][0], uvs[j][1]) for j in (j0, j1, j2)]
            topo = X.decode_id(int(round(tans[j0][0])))["topograph"]
            if F2.uv_degenerate(uv3):
                cx = sum(v[0] for v in vw) / 3.0
                cz = sum(v[2] for v in vw) / 3.0
                key = ((bx, by), round(cx, 3), round(cz, 3))
                defective.append(dict(block=(bx, by), tri=t, vids=(j0, j1, j2), vw=vw,
                                      is_apron=(key in apron_keys)))
            elif topo == 0:
                cell = own_cell(sum(v[0] for v in vw) / 3.0, sum(v[2] for v in vw) / 3.0)
                lawful_grass.append((cell, vw, uv3))
    return defective, lawful_grass


# ============================================================================================
#   STEP 1 -- MECHANISM PROBE
# ============================================================================================
def probe(report, touched, apron_keys, spec_meshes, fixed2_meshes):
    defective, lawful_grass = classify_defective(spec_meshes, apron_keys, touched)
    n_def = len(defective)
    log(f"[probe] classified defective (from SPEC) = {n_def} (expect 2305)")
    assert n_def == 2305, f"defective {n_def} != 2305"

    # -- geometry side: distinct own-cells of the 3 verts (per defective tri) --
    cells_hist = Counter()
    per_block_multicell = Counter()
    # -- texture side (FIXED2's ACTUAL assigned UVs): distinct quadrant-windows + UV excursion --
    win_hist = Counter()
    per_block_multiwin = Counter()
    excursions_multiwin = []
    excursions_singlewin = []
    excursions_by_ncells = defaultdict(list)
    cross = Counter()            # (n_cells, n_windows)
    tri_recs = []
    for d in defective:
        (bx, by) = d["block"]
        ncells = len(set(own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]))
        cells_hist[ncells] += 1
        if ncells >= 2:
            per_block_multicell[(bx, by)] += 1
        bm = fixed2_meshes[(bx, by)]
        uvs = bm.chan_arrays[CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        wins = set(uv_window(u, v) for (u, v) in uv3)
        nwin = len(wins)
        win_hist[nwin] += 1
        mpe = max_pairwise_uv(uv3)
        cross[(ncells, nwin)] += 1
        excursions_by_ncells[ncells].append(mpe)
        if nwin >= 2:
            per_block_multiwin[(bx, by)] += 1
            excursions_multiwin.append(mpe)
        else:
            excursions_singlewin.append(mpe)
        tri_recs.append((bx, by, ncells, nwin, mpe))

    # -- CONVERSE on the frame-mint's OWN lawful grass tris (the lattice invariant) --
    lawful_cells_hist = Counter()
    lawful_excursions = []
    lawful_multicell_examples = []
    for (cell, vw, uv3) in lawful_grass:
        ncells = len(set(own_cell(vx, vz) for (vx, _vy, vz) in vw))
        lawful_cells_hist[ncells] += 1
        lawful_excursions.append(max_pairwise_uv([(u, v) for (u, v) in uv3]))
        if ncells >= 2 and len(lawful_multicell_examples) < 20:
            lawful_multicell_examples.append(dict(cell=list(cell), ncells=ncells,
                                                  vw=[[round(c, 3) for c in p] for p in vw]))
    n_lawful = sum(lawful_cells_hist.values())

    def stats(xs):
        if not xs:
            return None
        xs = sorted(xs)
        n = len(xs)
        return dict(n=n, min=round(xs[0], 5), p50=round(xs[n // 2], 5),
                    p90=round(xs[int(0.9 * (n - 1))], 5), max=round(xs[-1], 5),
                    mean=round(sum(xs) / n, 5))

    n_multiwin = sum(v for k, v in win_hist.items() if k >= 2)
    n_multicell = sum(v for k, v in cells_hist.items() if k >= 2)
    frac_multiwin = round(n_multiwin / n_def, 4)
    frac_multicell = round(n_multicell / n_def, 4)
    lawful_frac_single = round(lawful_cells_hist[1] / n_lawful, 5) if n_lawful else None

    probe_out = dict(
        n_defective=n_def,
        one_window_scale_quad_diag=round(QUAD_DIAG, 5),
        full_region_diag=round(REGION_DIAG, 5),
        u_split=round(U_SPLIT, 5), v_split=round(V_SPLIT, 5),
        # geometry: how many distinct 4u cells the 3 verts of a defective tri span
        distinct_owncells_hist={str(k): cells_hist[k] for k in sorted(cells_hist)},
        frac_multicell=frac_multicell,
        # texture (FIXED2 actual UVs): how many distinct quadrant WINDOWS the 3 UVs occupy
        distinct_uvwindows_hist_fixed2={str(k): win_hist[k] for k in sorted(win_hist)},
        frac_multiwindow=frac_multiwin,
        # cross-tab n_cells x n_windows
        crosstab_ncells_x_nwindows={f"cells{c}_win{w}": cross[(c, w)]
                                    for (c, w) in sorted(cross)},
        # UV excursion: multi-window tris sweep FARTHER than a single window / than lawful tris
        excursion_multiwindow=stats(excursions_multiwin),
        excursion_singlewindow=stats(excursions_singlewin),
        excursion_by_ncells={str(k): stats(excursions_by_ncells[k]) for k in sorted(excursions_by_ncells)},
        excursion_lawful_frame_grass=stats(lawful_excursions),
        multiwin_exceeding_one_window=sum(1 for e in excursions_multiwin if e > QUAD_DIAG),
        # CONVERSE: the frame-mint's own lattice invariant
        frame_mint_lawful_grass=dict(
            n=n_lawful,
            distinct_owncells_hist={str(k): lawful_cells_hist[k] for k in sorted(lawful_cells_hist)},
            frac_single_cell=lawful_frac_single,
            multicell_examples=lawful_multicell_examples,
        ),
        # spatial correlation: multi-window tris cluster in the high-defect (streaked) blocks
        per_block_multiwindow={f"{b[0]},{b[1]}": per_block_multiwin[b] for b in touched
                               if per_block_multiwin[b]},
        per_block_multicell={f"{b[0]},{b[1]}": per_block_multicell[b] for b in touched
                             if per_block_multicell[b]},
    )
    report["probe"] = probe_out

    log(f"[probe] distinct own-cells hist (defective): "
        f"{probe_out['distinct_owncells_hist']}  frac_multicell={frac_multicell}")
    log(f"[probe] distinct UV-windows hist (FIXED2 actual): "
        f"{probe_out['distinct_uvwindows_hist_fixed2']}  frac_multiwindow={frac_multiwin}")
    log(f"[probe] crosstab cells x windows: {probe_out['crosstab_ncells_x_nwindows']}")
    log(f"[probe] excursion multiwin={probe_out['excursion_multiwindow']}")
    log(f"[probe] excursion single ={probe_out['excursion_singlewindow']}")
    log(f"[probe] excursion lawful ={probe_out['excursion_lawful_frame_grass']}")
    log(f"[probe] CONVERSE frame-mint lawful grass: n={n_lawful} "
        f"single-cell frac={lawful_frac_single} hist={probe_out['frame_mint_lawful_grass']['distinct_owncells_hist']}")

    # DECISION: confirmed iff a substantial fraction of the 2305 sweep >1 window.
    confirmed = frac_multiwin >= 0.30
    report["probe"]["mechanism_confirmed"] = confirmed
    report["probe"]["decision_rule"] = "confirmed iff frac_multiwindow >= 0.30"
    log(f"[probe] MECHANISM CONFIRMED = {confirmed} (frac_multiwindow={frac_multiwin} vs 0.30)")
    return confirmed, defective


# ============================================================================================
#   STEP 2 -- BUILD FIXED3A (only if confirmed): ONE WINDOW PER TRI (centroid cell)
# ============================================================================================
def build_fixed3a(report, touched, apron_keys):
    # copy SPEC -> FIXED3A (full tree)
    if FIXED3A.exists():
        shutil.rmtree(FIXED3A)
    shutil.copytree(SPEC, FIXED3A)
    n_copied = sum(1 for _ in FIXED3A.rglob("*") if _.is_file())
    assert n_copied == 180, f"copy mismatch {n_copied}"
    log(f"[build] copied {n_copied} files -> {FIXED3A}")

    a3_meshes = load_blocks(FIXED3A, touched)
    defective, lawful_grass = classify_defective(a3_meshes, apron_keys, touched)
    assert len(defective) == 2305
    assert sum(1 for d in defective if d["is_apron"]) == 321

    # ---- rebuild the EXACT v2 (quad,ori) cell field (method-a truth + assign_mains_seeded dropped) ----
    # target/centroid cells (identical union to v2)
    target_cells = set()
    for d in defective:
        for (vx, _vy, vz) in d["vw"]:
            target_cells.add(own_cell(vx, vz))
    centroid_cells = set()
    for d in defective:
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        centroid_cells.add(own_cell(cx, cz))
    resolve_cells = target_cells | centroid_cells

    # method (a): neighbour-decode ground truth (identical to v2)
    decoded_a = {}
    by_cell = defaultdict(list)
    for (cell, vw, uv3) in lawful_grass:
        by_cell[cell].append((vw, uv3))
    for cell in sorted(by_cell):
        got = None
        for (vw, uv3) in by_cell[cell]:
            qo = F2.decode_quad_ori(cell, vw, uv3)
            if qo is not None:
                got = qo
                break
        if got is not None:
            decoded_a[cell] = got
    dropped = sorted(c for c in resolve_cells if c not in decoded_a)

    pre_quad = dict(decoded_a)
    pre_ori = {c: o for c, (q, o) in decoded_a.items()}
    v2_quad, v2_ori = F2.assign_mains_seeded(dropped, pre_quad, pre_ori, seed=V2_SEED)

    decoded = {c: (q, o, "a") for c, (q, o) in decoded_a.items()}
    for c in dropped:
        decoded[c] = (v2_quad[c], v2_ori[c], "v2")
    log(f"[build] cell field: method-a={len(decoded_a)} dropped={len(dropped)} "
        f"resolve={len(resolve_cells)}")

    # ---- APPLY: ONE WINDOW PER TRI ----
    # Primary window = the tri's CENTROID cell's (quad,ori), all 3 verts (the exact build_landmass /
    # lawful-grass path). A pathological ear-clip tri that spans >1 cell can COLLAPSE under the centroid
    # window's directional bleed CLAMP (distant verts clamp to the same boundary UV -> zero UV area);
    # for those the FALLBACK tries each vertex's own-cell (quad,ori) as the single window and takes the
    # first NON-degenerate -- still exactly ONE (quad,ori) per tri (the invariant), just not the
    # centroid's. Every candidate cell is in `decoded` (resolve set = centroid U vertex own-cells).
    uv_changed_vids = defaultdict(set)
    nrm_changed_vids = defaultdict(set)
    apron_normal_tris = 0
    spread_over_window = 0
    max_spread = 0.0
    window_source = Counter()        # centroid | owncell-fallback | centroid-degenerate(last resort)
    centroid_cellmethod = Counter()
    for d in defective:
        (bx, by) = d["block"]
        bm = a3_meshes[(bx, by)]
        uvs = bm.chan_arrays[CH_UV]
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        ccell = own_cell(cx, cz)
        # ordered single-window candidates: centroid cell first, then the 3 vertex own-cells
        cand = [ccell] + [own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        seen = set()
        chosen = None
        for k, cell in enumerate(cand):
            if cell in seen:
                continue
            seen.add(cell)
            quad, ori, meth = decoded[cell]
            uv = [list(G.ground_uv(vx, vz, cell, quad, ori, "grass"))
                  for (vx, _vy, vz) in d["vw"]]
            if not F2.uv_tri_degen(uv):
                chosen = (uv, cell, meth, "centroid" if k == 0 else "owncell-fallback")
                break
        if chosen is None:
            # LAST RESORT (a world-sliver tri no single window can spread): the v1/v2 per-VERTEX
            # own-cell path -- the ONLY non-one-window tri, non-degenerate (v2 proved post_def=0 with
            # it). A documented exception; invisible (near-zero world area).
            uv = []
            for (vx, _vy, vz) in d["vw"]:
                c = own_cell(vx, vz)
                q, o, _m = decoded[c]
                uv.append(list(G.ground_uv(vx, vz, c, q, o, "grass")))
            chosen = (uv, ccell, decoded[ccell][2], "pervertex-lastresort")
        new_uv, used_cell, used_meth, src = chosen
        window_source[src] += 1
        centroid_cellmethod[used_meth] += 1
        sp = max_pairwise_uv(new_uv)
        max_spread = max(max_spread, sp)
        if sp > QUAD_DIAG + 1e-9:
            spread_over_window += 1
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
    log(f"[build] apron normals={apron_normal_tris} window_source={dict(window_source)} "
        f"spread>window={spread_over_window} max_spread={round(max_spread,5)}")
    report["apply"] = dict(apron_normal_tris=apron_normal_tris,
                           uv_changed_verts=sum(len(s) for s in uv_changed_vids.values()),
                           nrm_changed_verts=sum(len(s) for s in nrm_changed_vids.values()),
                           window_source=dict(window_source),
                           window_cell_field_method=dict(centroid_cellmethod),
                           tris_spread_over_one_window=spread_over_window,
                           max_uv_spread=round(max_spread, 6),
                           one_window_scale=round(QUAD_DIAG, 6),
                           note=("every rewritten tri uses exactly ONE (quad,ori) window "
                                 "(centroid cell, or a vertex own-cell fallback only where the "
                                 "centroid window's bleed clamp collapses the tri)."))

    # ---- WRITE the 20 Terrain files ----
    written = {}
    for (bx, by) in touched:
        p = F2.terr_path(FIXED3A, bx, by)
        M.write_ff9mesh(a3_meshes[(bx, by)], p)
        written[str(p.relative_to(FIXED3A))] = sha256_file(p)

    # ---- SEA4: restore full plane on the 6 blob blocks (identical to v1/v2) ----
    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    blob_blocks = [tuple(b) for b in forensics["meta"]["cell_sets"]["blob_blocks"]]
    full_plane_shas = {b: sha256_file(F2.sea4_path(FIXED3A, *b)) for b in touched
                       if b not in blob_blocks}
    assert len(set(full_plane_shas.values())) == 1, "non-blob Sea4 not uniform"
    donor_blk = next(iter(full_plane_shas))
    donor_bytes = F2.sea4_path(FIXED3A, *donor_blk).read_bytes()
    dp = M.read_ff9mesh(F2.sea4_path(FIXED3A, *donor_blk))
    assert all(abs(v[1]) <= 1e-4 for v in dp["verts"]), "donor plane Y!=0"
    for (bx, by) in blob_blocks:
        p = F2.sea4_path(FIXED3A, bx, by)
        p.write_bytes(donor_bytes)
        written[str(p.relative_to(FIXED3A))] = sha256_file(p)
    report["sea4"] = dict(blob_blocks=[list(b) for b in blob_blocks], donor_block=list(donor_blk),
                          donor_vcount=dp["vcount"])
    log(f"[build] Sea4 restored on {len(blob_blocks)} blob blocks")

    return dict(a3_meshes=a3_meshes, uv_changed_vids=uv_changed_vids,
                nrm_changed_vids=nrm_changed_vids, written=written,
                blob_blocks=blob_blocks, decoded=decoded, dropped=set(dropped),
                target_cells=target_cells, defective=defective, decoded_map=decoded)


# ============================================================================================
#   STEP 2 -- SELF-CHECK
# ============================================================================================
def verify_fixed3a(report, touched, state):
    uv_changed_vids = state["uv_changed_vids"]
    nrm_changed_vids = state["nrm_changed_vids"]
    written = state["written"]
    verify = {}

    # (1) post-fix degenerate == 0
    post_def = 0
    for (bx, by) in touched:
        bm = M.blockmesh_from_ff9mesh(F2.terr_path(FIXED3A, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for tri in bm.tris:
            uv3 = [(uvs[j][0], uvs[j][1]) for j in tri]
            if F2.uv_degenerate(uv3):
                post_def += 1
    verify["post_fix_defective_count"] = post_def

    # (2) rewritten UVs in grass mains region
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    tol = 1e-6
    out_of_region = 0
    for (bx, by), vids in uv_changed_vids.items():
        bm = M.blockmesh_from_ff9mesh(F2.terr_path(FIXED3A, bx, by), disc=1, x=bx, y=by, part="terrain")
        uvs = bm.chan_arrays[CH_UV]
        for j in vids:
            u, v = uvs[j]
            if not (lo_u - tol <= u <= hi_u + tol and lo_v - tol <= v <= hi_v + tol):
                out_of_region += 1
    verify["rewritten_uv_out_of_grass_region"] = out_of_region

    # (3) rigidity vs SPECIMEN: pos/tan/idx identical; uv only at changed; nrm only at changed
    rig = dict(pos_bad=0, tan_bad=0, idx_bad=0, uv_unexpected=0, uv_expected=0,
               nrm_unexpected=0, nrm_expected=0)
    for (bx, by) in touched:
        s = M.read_ff9mesh(F2.terr_path(SPEC, bx, by))
        f = M.read_ff9mesh(F2.terr_path(FIXED3A, bx, by))
        if s["indices"] != f["indices"]:
            rig["idx_bad"] += 1
        if s["verts"] != f["verts"]:
            rig["pos_bad"] += 1
        if s["tangents"] != f["tangents"]:
            rig["tan_bad"] += 1
        chg_uv = uv_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["uvs"][j] != f["uvs"][j]:
                rig["uv_expected" if j in chg_uv else "uv_unexpected"] += 1
        chg_n = nrm_changed_vids.get((bx, by), set())
        for j in range(s["vcount"]):
            if s["normals"][j] != f["normals"][j]:
                rig["nrm_expected" if j in chg_n else "nrm_unexpected"] += 1
    verify["byte_rigidity_vs_specimen"] = rig

    # (3b) file-count contract vs specimen: 22 files (16 Terrain + 6 Sea4)
    changed_files, changed_terr, changed_sea4 = [], 0, 0
    for rel in [str(pp.relative_to(SPEC)) for pp in SPEC.rglob("*.ff9mesh")]:
        if sha256_file(SPEC / rel) != sha256_file(FIXED3A / rel):
            changed_files.append(rel)
            if "Terrain" in rel:
                changed_terr += 1
            elif "Sea4" in rel:
                changed_sea4 += 1
    verify["specimen_diff"] = dict(n_changed=len(changed_files), n_terrain=changed_terr,
                                   n_sea4=changed_sea4)

    # (4) DIFF vs FIXED2: UV-ONLY, confined to the 2305. pos/tan/idx/nrm identical, Sea4 identical.
    dv = dict(terr_pos_bad=0, terr_tan_bad=0, terr_idx_bad=0, terr_nrm_bad=0,
              uv_diff_verts=0, uv_diff_in_2305=0, uv_diff_outside_2305=0, sea4_diff_files=0)
    # vids belonging to the 2305 defective tris -- from the SPEC-based (pre-write) classification
    defective_vids = defaultdict(set)
    for d in state["defective"]:
        for j in d["vids"]:
            defective_vids[d["block"]].add(j)
    for (bx, by) in touched:
        f2 = M.read_ff9mesh(F2.terr_path(FIXED2, bx, by))
        f3 = M.read_ff9mesh(F2.terr_path(FIXED3A, bx, by))
        if f2["verts"] != f3["verts"]:
            dv["terr_pos_bad"] += 1
        if f2["tangents"] != f3["tangents"]:
            dv["terr_tan_bad"] += 1
        if f2["indices"] != f3["indices"]:
            dv["terr_idx_bad"] += 1
        if f2["normals"] != f3["normals"]:
            dv["terr_nrm_bad"] += 1
        dvids = defective_vids.get((bx, by), set())
        for j in range(f2["vcount"]):
            if f2["uvs"][j] != f3["uvs"][j]:
                dv["uv_diff_verts"] += 1
                dv["uv_diff_in_2305" if j in dvids else "uv_diff_outside_2305"] += 1
    for (bx, by) in touched:
        if sha256_file(F2.sea4_path(FIXED2, bx, by)) != sha256_file(F2.sea4_path(FIXED3A, bx, by)):
            dv["sea4_diff_files"] += 1
    verify["diff_vs_fixed2"] = dv

    # (5) flat-mesh invariant + Sea4 uniform
    flat_bad = []
    for rel in written:
        d = M.read_ff9mesh(FIXED3A / rel)
        if not (d["vcount"] == len(d["indices"]) == len(d["verts"]) and len(d["indices"]) % 3 == 0):
            flat_bad.append(rel)
    verify["flat_mesh_bad"] = flat_bad
    sea4_shas = {sha256_file(F2.sea4_path(FIXED3A, *b))[:16] for b in touched}
    verify["all_sea4_uniform"] = (len(sea4_shas) == 1)

    # (6) per-tri WINDOW COHERENCE on the rewritten 2305 (the round-3 headline). The invariant is ONE
    #     (quad,ori) per tri -- guaranteed by construction (the apply used a single window_source cell
    #     for all 3 verts). We RE-DERIVE it independently from disk: for each rewritten tri, is there a
    #     SINGLE (cell,quad,ori) in the decoded field that reproduces all 3 on-disk UVs exactly? Also
    #     report the split-classifier "incoherent" count (a stock inward-bleed ARTIFACT: 16.5% of lawful
    #     build_landmass grass tris cross the same split) and the excursion vs the lawful reference.
    decoded_map = state["decoded_map"]
    single_qo = multi_qo = 0
    split_incoherent = 0
    over_window = 0
    exc = []
    a3_terr = {b: M.blockmesh_from_ff9mesh(F2.terr_path(FIXED3A, *b), disc=1, x=b[0], y=b[1],
                                           part="terrain") for b in touched}
    for d in state["defective"]:
        (bx, by) = d["block"]
        uvs = a3_terr[(bx, by)].chan_arrays[CH_UV]
        uv3 = [(uvs[j][0], uvs[j][1]) for j in d["vids"]]
        # which single (cell) reproduces all 3 on-disk UVs? try centroid + vertex own-cells
        cx = sum(p[0] for p in d["vw"]) / 3.0
        cz = sum(p[2] for p in d["vw"]) / 3.0
        cand = [own_cell(cx, cz)] + [own_cell(vx, vz) for (vx, _vy, vz) in d["vw"]]
        ok = False
        for cell in cand:
            if cell not in decoded_map:
                continue
            q, o, _m = decoded_map[cell]
            pred = [tuple(G.ground_uv(vx, vz, cell, q, o, "grass")) for (vx, _vy, vz) in d["vw"]]
            # on-disk UVs are float32-roundtripped; compare against float64 ground_uv at float32 tol
            if all(abs(pred[k][0] - uv3[k][0]) < 5e-6 and abs(pred[k][1] - uv3[k][1]) < 5e-6
                   for k in range(3)):
                ok = True
                break
        single_qo += ok
        multi_qo += (not ok)
        if len(set(uv_window(u, v) for (u, v) in uv3)) != 1:
            split_incoherent += 1
        e = max_pairwise_uv(uv3)
        exc.append(e)
        if e > QUAD_DIAG + 1e-9:
            over_window += 1
    exc.sort()
    n = len(exc)
    verify["window_coherence"] = dict(
        n_rewritten=n,
        single_qo_reconstructed=single_qo, multi_qo_reconstructed=multi_qo,
        pct_single_qo=round(100.0 * single_qo / n, 3),
        split_classifier_incoherent=split_incoherent,
        split_incoherent_note="stock inward-bleed artifact; 16.5% of lawful build_landmass grass also crosses",
        excursion_p50=round(exc[n // 2], 5), excursion_p90=round(exc[int(0.9 * (n - 1))], 5),
        excursion_max=round(exc[-1], 5), one_window_scale=round(QUAD_DIAG, 5),
        lawful_reference_excursion_p50_p90_max=[0.06769, 0.06814, 0.08887],
        tris_spread_over_one_window=over_window)
    incoherent = multi_qo
    n_lastresort = report.get("apply", {}).get("window_source", {}).get("pervertex-lastresort", 0)
    verify["window_coherence"]["documented_pervertex_lastresort"] = n_lastresort

    report["verify"] = verify
    ok = (post_def == 0 and out_of_region == 0 and not flat_bad
          and rig["pos_bad"] == 0 and rig["tan_bad"] == 0 and rig["idx_bad"] == 0
          and rig["uv_unexpected"] == 0 and rig["nrm_unexpected"] == 0
          and verify["all_sea4_uniform"]
          and verify["specimen_diff"]["n_changed"] == 22
          and verify["specimen_diff"]["n_terrain"] == 16
          and verify["specimen_diff"]["n_sea4"] == 6
          and dv["terr_pos_bad"] == 0 and dv["terr_tan_bad"] == 0 and dv["terr_idx_bad"] == 0
          and dv["terr_nrm_bad"] == 0 and dv["sea4_diff_files"] == 0
          and dv["uv_diff_outside_2305"] == 0
          and incoherent == n_lastresort)      # only the documented per-vertex sliver(s) are non-one-window
    report["ok"] = ok
    log(f"[verify] post_def={post_def} out_of_region={out_of_region} flat_bad={flat_bad}")
    log(f"[verify] rigidity vs SPEC: {rig}")
    log(f"[verify] specimen_diff: {verify['specimen_diff']}")
    log(f"[verify] diff vs FIXED2: {dv}")
    log(f"[verify] window coherence: single_qo={single_qo}/{n} multi_qo={multi_qo} "
        f"split_incoherent(artifact)={split_incoherent} exc_p50={verify['window_coherence']['excursion_p50']} "
        f"exc_max={verify['window_coherence']['excursion_max']} over_window={over_window}")
    log(f"[verify] all_sea4_uniform={verify['all_sea4_uniform']}  OK={ok}")
    return ok


def main():
    build_flag = "--build" in sys.argv
    report = {"meta": {"script": "uvf_fix3.py", "read_only_vs_game": True, "v2_seed": V2_SEED,
                       "spec_tree": str(SPEC), "fixed2_tree": str(FIXED2),
                       "fixed3a_tree": str(FIXED3A), "build_requested": build_flag}}

    build = json.loads(BUILD_JSON.read_text(encoding="utf-8"))
    touched = [tuple(b) for b in build["compose_diag"]["touched_blocks"]]
    assert len(touched) == 20

    forensics = json.loads(FORENSICS.read_text(encoding="utf-8"))
    apron_keys = set()
    for rec in forensics["records"]:
        if rec.get("uv_verdict") == "degenerate-zero-area" and rec["provenance"] == "apron":
            cx, _cy, cz = rec["centroid"]
            apron_keys.add((tuple(rec["block"]), round(cx, 3), round(cz, 3)))

    spec_meshes = load_blocks(SPEC, touched)
    fixed2_meshes = load_blocks(FIXED2, touched)

    confirmed, defective = probe(report, touched, apron_keys, spec_meshes, fixed2_meshes)

    if confirmed and build_flag:
        state = build_fixed3a(report, touched, apron_keys)
        verify_fixed3a(report, touched, state)
    else:
        report["ok"] = None
        if not confirmed:
            log("[main] MECHANISM REFUTED -- NOT building FIXED3A.")
        elif not build_flag:
            log("[main] probe-only (pass --build to emit FIXED3A).")

    REPORT.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log(f"\n{'='*80}\nwrote {REPORT}  confirmed={confirmed} ok={report.get('ok')}")
    return report


if __name__ == "__main__":
    main()
