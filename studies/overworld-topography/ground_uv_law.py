"""THE GROUND-UV LAW -- is stock ground uv PLAN-projected or SURFACE-arclength? (S1)

Registered in studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md (S1). The prior
evidence is weak: a donor-apron probe read per-surface uv rate flatter (0.981 vs 0.982)
than per-plan (1.000 vs 0.986) on SHALLOW tris -- both ~= 1.0, no build can rest on it.

CALIBRATION FIRST (this instrument's own precondition; the arc's meta-law). Stock world
vertex data is QUANTIZED: uv to 1/1024, position to 1/256 (verified per block, M0). One
uv quantum = 1/64 tile in u and 1/32 tile in v; a 4u cell edge spans only 62 (u) / 31 (v)
quanta. Every residual, rate and dispersion below is therefore reported in QUANTA, and
no affinity gate is set tighter than one quantum -- the first pass of this instrument
gated at 1e-4 raw uv (the shipped decoder's DECODE_ERR) and mis-read 2/3 of lawful stock
grass cells as non-affine purely from rounding.

The four measurements, all over stock disc-1, read-only:

  M1 PER-EDGE RATE -- every ground triangle EDGE: plan length, 3D surface length, and
     |duv| in TILE units; rate_plan = duv / (plan/4u), rate_surf = duv / (surf/4u).
     Binned by the TRIANGLE's slope (0-10 / 10-25 / 25-40 / 40+ deg). Under the plan law
     rate_plan is flat across bins and rate_surf falls as cos(slope); under the surface
     law the reverse. Reported per family, with a LONG-EDGE (>=3u) subset where the
     quantization noise floor is smallest.
  M2 PER-TRIANGLE AREAL SCALE -- the same discriminant with no near-vertical-edge bias
     (an edge can be far steeper than its triangle, and a plan-length filter silently
     deletes the steep bin): 4*sqrt(A_uv/A_plan) vs 4*sqrt(A_uv/A_surf), A_uv in tile^2.
  M3 THE PER-CELL MODEL (L3) -- per 4u lattice cell (and per cell x family): an
     over-determined least-squares fit of uv = J.(x,z) + c, a PURE plan function with no
     rect assumed; residual in QUANTA; J's structure vs the 4 measured orientations
     (grassland.rot_ab) and the mains rect scale (0.9688 tiles per 4u); then the
     project's own locked-rect decoder (grassland.ground_uv x all GROUNDS families x 16
     quad/ori combos). The residual is binned by the cell's NON-PLANARITY (max
     inter-triangle normal angle) because a PLANAR cell CANNOT discriminate plan from
     surface -- the two differ by an invertible linear map -- so the whole discrimination
     lives in cells that span a break in slope. Also: cells spanning a class boundary.
  M4 CROSS-CELL PHASE -- at plan positions shared by triangles in DIFFERENT cells, is uv
     identical (one continuous chart) or does each cell restart? |duv| in tiles, and the
     fractional part of the per-axis jump (whole-tile-quantized or free?).

Plus the slope ENVELOPE per ground class (p50/p90/p99/max) -- the number that turns the
law into a build threshold: a plan-projected retile can only be in-language out to the
slope stock itself ships under that law.

Walkable ground is not guessed: it is decoded from the engine foot mask
{0x0010667F, 0xD8FF3CFF} (ff9.cs w_movementCheckTopographID; README's WALK-LEGALITY LAW)
-- word0 = topos 32-63, word1 = topos 0-31, bit set = walkable. Reproduces the README's
own spot checks (walks 0/13/17/37, blocks 49/58).

Read-only vs stock disc-1. Artifacts -> out/ground_uv_law.json + out/ground_uv_law.png
Regenerate: py -X utf8 ground_uv_law.py          (optional arg = block sample count)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "ff9mapkit"))

from ff9mapkit.world import extract as X                     # noqa: E402
from ff9mapkit.world import grassland as G                   # noqa: E402

TILE_U, TILE_V = 0.0625, 0.03125
CELL = 4.0
UVQ = 1.0 / 1024.0                                           # measured in M0, asserted per block
POSQ = 1.0 / 256.0
DECODE_ERR = 1e-4                                            # uvf_fix2.py's shipped constant
OUT = HERE / "out" / "ground_uv_law.json"
PNG = HERE / "out" / "ground_uv_law.png"

FOOT_MASK = (0x0010667F, 0xD8FF3CFF)                         # (topos 32-63, topos 0-31)
WALKABLE = {t for t in range(32) if (FOOT_MASK[1] >> t) & 1}
WALKABLE |= {32 + t for t in range(32) if (FOOT_MASK[0] >> t) & 1}

FAMILIES = {
    "grass": {0, 1, 2, 3, 42},
    "plateau": {10, 11, 12},
    "shelf13": {13},
    "scrub": {4, 5, 6},
    "desert": {17, 18, 19, 20, 21, 22, 23},
    "dirt16": {16},
    "dunes41": {41},
    "snow": {27, 28},
    "canyon": {45, 46},
    "forest": {36, 37},
    "sand": {31, 32, 33},
    "rocky7": {7, 30, 34, 35, 52, 38},                       # walkable-but-rocky/brush leftovers
}
FAM_OF = {t: f for f, ts in FAMILIES.items() for t in ts}
#: the families the mesa-carry build decision is actually about (mains-language ground)
MAINS_FAMS = ("grass", "plateau", "shelf13")

SLOPE_BINS = [(0.0, 10.0), (10.0, 25.0), (25.0, 40.0), (40.0, 91.0)]
BIN_NAMES = ["0-10", "10-25", "25-40", "40+"]

RECT_U = G.GRASS_U_HALF[0][1] - G.GRASS_U_HALF[0][0]
RECT_V = G.GRASS_V_HALF[0][1] - G.GRASS_V_HALF[0][0]
MAINS_SCALE_U = RECT_U / TILE_U                              # 0.96864 tiles per 4u
MAINS_SCALE_V = RECT_V / TILE_V                              # 0.96896

MIN_PLAN_EDGE = 1.0
LONG_EDGE = 3.0
EPS_OFFDIAG = 0.03                                           # tiles/4u -- signed-permutation test
AFFINE_Q = 1.0                                               # QUANTA -- the plan-affine gate
GROUND_REGION = {g: G.ground_main_region(g) for g in G.GROUNDS}


def q(a, ps=(1, 5, 25, 50, 75, 95, 99)):
    if a is None or not len(a):
        return None
    a = np.asarray(a, dtype=float)
    out = {f"p{p}": round(float(np.percentile(a, p)), 5) for p in ps}
    out.update(n=int(a.size), mean=round(float(a.mean()), 5), std=round(float(a.std()), 5),
               min=round(float(a.min()), 5), max=round(float(a.max()), 5))
    if out.get("p50") and "p75" in out and "p25" in out:
        out["iqr_frac"] = round((out["p75"] - out["p25"]) / abs(out["p50"]), 5)
    return out


def slope_deg(a, b, c):
    n = np.cross(b - a, c - a)
    L = float(np.linalg.norm(n))
    if L < 1e-12:
        return None
    return math.degrees(math.acos(min(1.0, abs(float(n[1])) / L)))


def bin_of(s):
    for k, (lo, hi) in enumerate(SLOPE_BINS):
        if lo <= s < hi:
            return k
    return len(SLOPE_BINS) - 1


def classify_J(J):
    """J = 2x2 duv/d(x,z) in TILES per 4u -> (ori, kind) for the 4 measured signed
    permutations of grassland.rot_ab; ori None if off-handed or sheared."""
    a, b = J[0][0], J[0][1]
    c, d = J[1][0], J[1][1]
    diag = abs(b) < EPS_OFFDIAG and abs(c) < EPS_OFFDIAG
    anti = abs(a) < EPS_OFFDIAG and abs(d) < EPS_OFFDIAG
    if diag and not anti:
        if a > 0 and d < 0:
            return 0, "diag"
        if a < 0 and d > 0:
            return 180, "diag"
        return None, "diag_offhand"
    if anti and not diag:
        if b > 0 and c > 0:
            return 90, "anti"
        if b < 0 and c < 0:
            return 270, "anti"
        return None, "anti_offhand"
    if diag and anti:
        return None, "degenerate"
    return None, "sheared"


def cand_families(uv):
    mu = sum(w[0] for w in uv) / len(uv)
    mv = sum(w[1] for w in uv) / len(uv)
    return [g for g, (u0, v0, u1, v1) in GROUND_REGION.items()
            if u0 - 0.004 <= mu <= u1 + 0.004 and v0 - 0.004 <= mv <= v1 + 0.004]


def decode_l3(cell, pos, uv, gate):
    """The project's own L3 decoder (mirrors uvf_fix2.decode_quad_ori: 16 (quad, ori)
    combos vs grassland.ground_uv), extended over the GROUNDS families."""
    best = None
    for gname in cand_families(uv):
        for uh in (0, 1):
            for vh in (0, 1):
                for ori in G.ORIS:
                    maxerr = 0.0
                    for (vx, vz), (su, sv) in zip(pos, uv):
                        mu, mv = G.ground_uv(vx, vz, cell, (uh, vh), ori, gname)
                        e = max(abs(mu - su), abs(mv - sv))
                        if e > maxerr:
                            maxerr = e
                        if maxerr >= gate:
                            break
                    if best is None or maxerr < best[0]:
                        best = (maxerr, gname, (uh, vh), ori)
                    if best[0] < gate:
                        return best
    return best


def tri_frames(P, uvs):
    """THE ISOTROPY TEST (M2b) -- the sharpest per-triangle discriminant, and the one that
    measures the owner's word ("stretched") directly.

    A triangle's uv map is exactly affine in BOTH frames (3 points determine it), so the
    question is not which frame FITS but which frame the map is a SIMILARITY in:
      * under a PLAN law  J_plan is isotropic (sigma1/sigma2 = 1) and J_surf is stretched
        by 1/cos(slope) along the gradient -- the texture is stretched ON THE SURFACE;
      * under a SURFACE law J_surf is isotropic and J_plan is stretched by 1/cos.
    Returns (aniso_plan, aniso_surf, scale_plan, scale_surf, J_plan) with uv in TILE units,
    or None when degenerate."""
    e1 = P[1] - P[0]
    e2 = P[2] - P[0]
    n = np.cross(e1, e2)
    nl = float(np.linalg.norm(n))
    if nl < 1e-9:
        return None
    D = np.array([[(uvs[1][0] - uvs[0][0]) / TILE_U, (uvs[2][0] - uvs[0][0]) / TILE_U],
                  [(uvs[1][1] - uvs[0][1]) / TILE_V, (uvs[2][1] - uvs[0][1]) / TILE_V]])
    Pm = np.array([[e1[0], e2[0]], [e1[2], e2[2]]])            # plan (x, z)
    ex = e1 / float(np.linalg.norm(e1))
    ey = np.cross(n / nl, ex)
    Sm = np.array([[float(e1 @ ex), float(e2 @ ex)], [float(e1 @ ey), float(e2 @ ey)]])
    out = []
    for M in (Pm, Sm):
        if abs(float(np.linalg.det(M))) < 1e-9:
            return None
        J = D @ np.linalg.inv(M)
        sv = np.linalg.svd(J, compute_uv=False)
        if sv[1] < 1e-12:
            return None
        out.append((float(sv[0] / sv[1]), float(math.sqrt(abs(np.linalg.det(J)))) * CELL, J))
    return out[0][0], out[1][0], out[0][1], out[1][1], out[0][2]


def unfold_pair(ts):
    """Isometric UNFOLDING of a 2-triangle cell about its shared edge -> per-vertex 2D
    coordinates in which 3D SURFACE distances are exact. Returns (plan_pts, surf_pts, uv)
    as parallel lists of 6 samples, or None if the two tris do not share an edge.

    This is the direct model comparison the per-cell residual alone cannot make: a PLANAR
    cell fits both hypotheses exactly (they differ by an invertible linear map), so the
    discrimination lives entirely in a cell that KINKS -- and there, an affine fit in the
    unfolded (surface) frame and an affine fit in the plan frame make different
    predictions for the SAME uv bytes."""
    if len(ts) != 2:
        return None
    A, B = ts[0], ts[1]
    ka = [tuple(np.round(p, 4)) for p in A["P"]]
    kb = [tuple(np.round(p, 4)) for p in B["P"]]
    shared = [k for k in ka if k in kb]
    if len(shared) != 2:
        return None
    ia = [ka.index(shared[0]), ka.index(shared[1])]
    ib = [kb.index(shared[0]), kb.index(shared[1])]
    ja = [i for i in range(3) if i not in ia][0]
    jb = [i for i in range(3) if i not in ib][0]
    S1, S2 = A["P"][ia[0]], A["P"][ia[1]]
    e = S2 - S1
    L = float(np.linalg.norm(e))
    if L < 1e-6:
        return None
    e = e / L

    def loc(P, sign):
        d = P - S1
        t = float(d @ e)
        h = float(np.linalg.norm(d - t * e))
        return (t, sign * h)

    surf = {ia[0]: (0.0, 0.0), ia[1]: (L, 0.0), ja: loc(A["P"][ja], +1.0)}
    surfB = {ib[0]: (0.0, 0.0), ib[1]: (L, 0.0), jb: loc(B["P"][jb], -1.0)}
    plan, sur, uv = [], [], []
    for tri, sm in ((A, surf), (B, surfB)):
        for i in range(3):
            plan.append((float(tri["P"][i][0]), float(tri["P"][i][2])))
            sur.append(sm[i])
            uv.append((tri["uv"][i][0], tri["uv"][i][1]))
    return plan, sur, uv


def fit_frame(coords, uv):
    """Affine LSQ of uv over arbitrary 2D coords; max residual in uv QUANTA (None if rank-deficient)."""
    M = np.array([[c[0], c[1], 1.0] for c in coords])
    if len(set((round(c[0], 4), round(c[1], 4)) for c in coords)) < 4 or np.linalg.matrix_rank(M) < 3:
        return None
    bu = np.array([w[0] for w in uv])
    bv = np.array([w[1] for w in uv])
    su, *_ = np.linalg.lstsq(M, bu, rcond=None)
    sv, *_ = np.linalg.lstsq(M, bv, rcond=None)
    return float(max(np.abs(M @ su - bu).max(), np.abs(M @ sv - bv).max()) / UVQ)


def fit_cell(pos, uv):
    """Over-determined plan-affine LSQ. Returns (res_max_quanta, res_rms_quanta, J) or None."""
    dpos = set((round(p[0], 3), round(p[1], 3)) for p in pos)
    if len(dpos) < 4:
        return None
    M = np.array([[p[0], p[1], 1.0] for p in pos])
    if np.linalg.matrix_rank(M) < 3:
        return None
    bu = np.array([w[0] for w in uv])
    bv = np.array([w[1] for w in uv])
    su, *_ = np.linalg.lstsq(M, bu, rcond=None)
    sv, *_ = np.linalg.lstsq(M, bv, rcond=None)
    ru = np.abs(M @ su - bu) / UVQ
    rv = np.abs(M @ sv - bv) / UVQ
    J = [[su[0] * CELL / TILE_U, su[1] * CELL / TILE_U],
         [sv[0] * CELL / TILE_V, sv[1] * CELL / TILE_V]]
    rms = math.hypot(float(np.sqrt((ru ** 2).mean())), float(np.sqrt((rv ** 2).mean())))
    return float(max(ru.max(), rv.max())), rms, J, len(dpos)


def main():
    rep = {"meta": {"script": "ground_uv_law.py", "read_only_vs_game": True, "disc": 1,
                    "walkable_topos": sorted(WALKABLE),
                    "foot_mask": [hex(FOOT_MASK[0]), hex(FOOT_MASK[1])],
                    "uv_quantum": UVQ, "pos_quantum": POSQ,
                    "uv_quantum_in_tiles": [round(UVQ / TILE_U, 6), round(UVQ / TILE_V, 6)],
                    "mains_scale_u": round(MAINS_SCALE_U, 6),
                    "mains_scale_v": round(MAINS_SCALE_V, 6),
                    "min_plan_edge": MIN_PLAN_EDGE, "long_edge": LONG_EDGE,
                    "affine_gate_quanta": AFFINE_Q, "shipped_decode_err": DECODE_ERR}}
    print("walkable topos:", sorted(WALKABLE))

    blocks = X.list_blocks(disc=1)
    if len(sys.argv) > 1:
        step = max(1, len(blocks) // int(sys.argv[1]))
        blocks = blocks[::step]
        rep["meta"]["SAMPLED_every_nth_block"] = step

    n_read = n_with_ground = 0
    topo_ct = Counter()
    quant_fail = []

    E = defaultdict(lambda: {"plan": [], "surf": [], "slope": []})            # M1 (fam, bin)
    EL = defaultdict(lambda: {"plan": [], "surf": [], "slope": []})           # M1 long edges
    EI = defaultdict(lambda: {"plan": [], "surf": [], "slope": []})           # M1 by EDGE inclination
    FCE = defaultdict(list)                                                   # M1b full-cell-edge span
    UNF = []                                                                  # M3b unfold test
    ISO = defaultdict(lambda: {"ap": [], "as": [], "sp": [], "ss": [],        # M2b isotropy
                               "slope": [], "kind": [], "area": []})
    PAIR = defaultdict(list)                                                  # M2c edge-pair test
    QNT = defaultdict(list)                                                   # M2d quanta test
    A = defaultdict(lambda: {"plan": [], "surf": [], "slope": []})            # M2
    slopes_by_fam = defaultdict(list)
    area_by_fam = defaultdict(float)
    cells_rec = []                                                            # M3 whole-cell
    chart_rec = []                                                            # M3 cell x family
    edges_seen = edges_kept = 0
    xc_same = xc_tot = xc_border = 0
    xc_duv, xc_du_frac, xc_dv_frac = [], [], []

    for (bx, by) in blocks:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except Exception:                                     # noqa: BLE001
            continue
        n_read += 1
        V, U, T = bm.verts, bm.uvs, bm.tangents
        if V is None or U is None or T is None:
            continue
        # M0 calibration: assert the quantum this instrument's gates are built on
        if not all(abs(w[0] / UVQ - round(w[0] / UVQ)) < 1e-6
                   and abs(w[1] / UVQ - round(w[1] / UVQ)) < 1e-6 for w in U):
            quant_fail.append([bx, by])

        ntri = len(bm.flat_index) // 3
        tri_idx = [bm.flat_index[3 * t:3 * t + 3] for t in range(ntri)]
        topo = [X.decode_id(int(round(T[idx[0]][0])))["topograph"] for idx in tri_idx]
        ground = [t for t in range(ntri) if topo[t] in WALKABLE]
        if not ground:
            continue
        n_with_ground += 1

        cell_tris = defaultdict(list)
        pos_uv = defaultdict(set)
        pos_cells = defaultdict(set)
        seen_edge = set()

        for t in ground:
            idx = tri_idx[t]
            P = [np.array(V[i], dtype=float) for i in idx]
            uvs = [tuple(U[i]) for i in idx]
            s = slope_deg(*P)
            if s is None:
                continue
            fam = FAM_OF.get(topo[t], "other_walkable")
            topo_ct[topo[t]] += 1
            k = bin_of(s)
            slopes_by_fam[fam].append(s)
            slopes_by_fam["ALL"].append(s)
            if fam in MAINS_FAMS:
                slopes_by_fam["MAINS_FAMS"].append(s)

            # ---- M2 areal ------------------------------------------------------------------
            e1p = (P[1][0] - P[0][0], P[1][2] - P[0][2])
            e2p = (P[2][0] - P[0][0], P[2][2] - P[0][2])
            Aplan = 0.5 * abs(e1p[0] * e2p[1] - e1p[1] * e2p[0])
            Asurf = 0.5 * float(np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])))
            d1 = ((uvs[1][0] - uvs[0][0]) / TILE_U, (uvs[1][1] - uvs[0][1]) / TILE_V)
            d2 = ((uvs[2][0] - uvs[0][0]) / TILE_U, (uvs[2][1] - uvs[0][1]) / TILE_V)
            Auv = 0.5 * abs(d1[0] * d2[1] - d1[1] * d2[0])
            area_by_fam[fam] += Asurf
            area_by_fam["ALL"] += Asurf
            if Aplan > 0.5 and Asurf > 0.5 and Auv > 1e-6:
                sp = 4.0 * math.sqrt(Auv / Aplan)
                ss = 4.0 * math.sqrt(Auv / Asurf)
                keys = [(fam, k), ("ALL", k)] + ([("MAINS_FAMS", k)] if fam in MAINS_FAMS else [])
                for key in keys:
                    A[key]["plan"].append(sp)
                    A[key]["surf"].append(ss)
                    A[key]["slope"].append(s)

            # ---- M2b THE ISOTROPY TEST -----------------------------------------------------
            tf = tri_frames(P, uvs)
            if tf is not None and Asurf > 0.5:
                ap, asu, sp2, ss2, Jp = tf
                _ori, kind = classify_J(Jp)
                keys = [(fam, k), ("ALL", k)] + ([("MAINS_FAMS", k)] if fam in MAINS_FAMS else [])
                for key in keys:
                    ISO[key]["ap"].append(ap)
                    ISO[key]["as"].append(asu)
                    ISO[key]["sp"].append(sp2)
                    ISO[key]["ss"].append(ss2)
                    ISO[key]["slope"].append(s)
                    ISO[key]["kind"].append(kind)
                    ISO[key]["area"].append(Asurf)

            # ---- M2d THE QUANTA TEST (the decisive one) ------------------------------------
            # uv is quantized to 1/1024, and one 4u cell side spans exactly 62 quanta (the
            # 0.06054 mains rect) or 64 (a window one full tile pitch wide). Under a PLAN law
            # a well-shaped triangle's uv map has singular values pinned on those two integers
            # AT EVERY SLOPE; under a SURFACE law the value slides continuously as 62/cos
            # (70 quanta at 28 deg) and can never land back on the tile pitch.
            if tf is not None and Asurf > 2.0:
                angs, shp = [], True
                for i3 in range(3):
                    a1 = np.array([P[(i3 + 1) % 3][0] - P[i3][0], P[(i3 + 1) % 3][2] - P[i3][2]])
                    b1 = np.array([P[(i3 + 2) % 3][0] - P[i3][0], P[(i3 + 2) % 3][2] - P[i3][2]])
                    n1, n2 = float(np.linalg.norm(a1)), float(np.linalg.norm(b1))
                    if n1 < 1.5 or n2 < 1.5:
                        shp = False
                        break
                    angs.append(math.degrees(math.acos(max(-1.0, min(1.0, float(a1 @ b1) / n1 / n2)))))
                if shp and angs and min(angs) >= 20.0:         # no slivers: J is well conditioned
                    _ap, _as, _sp, _ss, Jp2 = tf
                    sv2 = np.linalg.svd(Jp2 * CELL, compute_uv=False)
                    _o2, kind2 = classify_J(Jp2)
                    keys = [(fam, k), ("ALL", k)] + ([("MAINS_FAMS", k)] if fam in MAINS_FAMS else [])
                    for key in keys:
                        QNT[key].append((float(sv2[0]), float(sv2[1]),
                                         kind2 in ("diag", "anti"), s))

            # ---- M2c THE WITHIN-TRIANGLE EDGE-PAIR TEST ------------------------------------
            # The decisive test, immune to every between-cell confound (window aspect, free
            # fractional windows, family, selection): inside ONE triangle the uv map is ONE
            # affine map, so take the two edges whose inclinations differ most. Under a PLAN
            # law their rate_plan ratio is 1 (up to the window's own <=3.2% aspect); under a
            # SURFACE law it is cos(inc_j)/cos(inc_i). Both edges share the same map, so
            # nothing about the cell can explain the difference.
            ed = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                d0 = P[b] - P[a]
                pl = math.hypot(d0[0], d0[2])
                sf = float(np.linalg.norm(d0))
                dv0 = math.hypot((uvs[b][0] - uvs[a][0]) / TILE_U,
                                 (uvs[b][1] - uvs[a][1]) / TILE_V)
                if pl >= 1.5 and dv0 > 1e-6:
                    ed.append((pl, sf, dv0, pl / sf))
            if len(ed) >= 2:
                ed.sort(key=lambda r: r[3])                    # by cos(edge inclination)
                lo_e, hi_e = ed[0], ed[-1]                     # most inclined / least inclined
                cos_ratio = lo_e[3] / hi_e[3]                  # <= 1
                if cos_ratio < 0.97:                           # the pair must actually differ
                    rp_lo = lo_e[2] / (lo_e[0] / CELL)
                    rp_hi = hi_e[2] / (hi_e[0] / CELL)
                    obs = rp_lo / rp_hi
                    keys = [(fam, k), ("ALL", k)] + ([("MAINS_FAMS", k)] if fam in MAINS_FAMS else [])
                    for key in keys:
                        PAIR[key].append((obs, cos_ratio, s))

            # ---- M1 per-edge ---------------------------------------------------------------
            for a, b in ((0, 1), (1, 2), (2, 0)):
                ka = tuple(np.round(P[a], 3)) + tuple(np.round(uvs[a], 6))
                kb = tuple(np.round(P[b], 3)) + tuple(np.round(uvs[b], 6))
                ek = tuple(sorted((ka, kb)))
                if ek in seen_edge:
                    continue
                seen_edge.add(ek)
                edges_seen += 1
                d = P[b] - P[a]
                plan = math.hypot(d[0], d[2])
                surf = float(np.linalg.norm(d))
                duv = math.hypot((uvs[b][0] - uvs[a][0]) / TILE_U,
                                 (uvs[b][1] - uvs[a][1]) / TILE_V)
                if plan < MIN_PLAN_EDGE or duv < 1e-6:
                    continue
                edges_kept += 1
                rp = duv / (plan / CELL)
                rs = duv / (surf / CELL)
                # the edge's OWN inclination -- the variable the per-edge rate actually depends
                # on (an edge inside a steep triangle can itself be dead level)
                einc = math.degrees(math.acos(max(-1.0, min(1.0, plan / surf))))
                ke = bin_of(einc)
                fams = [fam, "ALL"] + (["MAINS_FAMS"] if fam in MAINS_FAMS else [])
                for f2 in fams:
                    E[(f2, k)]["plan"].append(rp)
                    E[(f2, k)]["surf"].append(rs)
                    E[(f2, k)]["slope"].append(s)
                    EI[(f2, ke)]["plan"].append(rp)
                    EI[(f2, ke)]["surf"].append(rs)
                    EI[(f2, ke)]["slope"].append(einc)
                    if plan >= LONG_EDGE:
                        EL[(f2, k)]["plan"].append(rp)
                        EL[(f2, k)]["surf"].append(rs)
                        EL[(f2, k)]["slope"].append(s)
                    # M1b THE FULL-CELL-EDGE SPAN -- a 4u plan edge is one whole cell side, so
                    # under a PLAN law its |duv| is exactly one tile-rect width (0.9686 tiles)
                    # whatever its inclination; under a SURFACE law it would be 0.9686/cos and
                    # would run OUTSIDE the tile rect (which stock cannot do -- FAM_REGION's
                    # strict bounds mean a corner past the rect samples a transparent gutter).
                    if 3.9 <= plan <= 4.1:
                        FCE[(f2, ke)].append((duv, einc))

            # ---- bookkeeping ---------------------------------------------------------------
            cx = sum(p[0] for p in P) / 3.0
            cz = sum(p[2] for p in P) / 3.0
            cij = (int(math.floor(cx / CELL)), int(math.floor(cz / CELL)))
            nrm = np.cross(P[1] - P[0], P[2] - P[0])
            nl = float(np.linalg.norm(nrm))
            cell_tris[cij].append(dict(P=P, uv=uvs, topo=topo[t], slope=s, fam=fam,
                                       n=(nrm / nl) if nl > 1e-12 else None))
            for i3 in range(3):
                pk = (round(float(P[i3][0]), 3), round(float(P[i3][2]), 3))
                pos_uv[pk].add((round(uvs[i3][0], 6), round(uvs[i3][1], 6)))
                pos_cells[pk].add(cij)

        # ---- M4 --------------------------------------------------------------------------
        for pk, cs in pos_cells.items():
            if len(cs) < 2:
                continue
            xc_tot += 1
            uvset = sorted(pos_uv[pk])
            if len(uvset) == 1:
                xc_same += 1
            else:
                best = max(((p, r) for p in uvset for r in uvset),
                           key=lambda pr: math.hypot((pr[0][0] - pr[1][0]) / TILE_U,
                                                     (pr[0][1] - pr[1][1]) / TILE_V))
                du = abs(best[0][0] - best[1][0]) / TILE_U
                dv = abs(best[0][1] - best[1][1]) / TILE_V
                xc_duv.append(math.hypot(du, dv))
                xc_du_frac.append(min(du % 1.0, 1.0 - du % 1.0))
                xc_dv_frac.append(min(dv % 1.0, 1.0 - dv % 1.0))
            if abs(pk[0] % CELL) < 1e-6 or abs(pk[1] % CELL) < 1e-6:
                xc_border += 1

        # ---- M3 --------------------------------------------------------------------------
        def make_rec(cij, ts, scope):
            pos = [(float(tt["P"][i][0]), float(tt["P"][i][2])) for tt in ts for i in range(3)]
            uv = [(tt["uv"][i][0], tt["uv"][i][1]) for tt in ts for i in range(3)]
            nonplan = 0.0
            ns = [tt["n"] for tt in ts if tt["n"] is not None]
            for i in range(len(ns)):
                for j2 in range(i + 1, len(ns)):
                    c = max(-1.0, min(1.0, float(ns[i] @ ns[j2])))
                    nonplan = max(nonplan, math.degrees(math.acos(c)))
            r = dict(block=[bx, by], cell=list(cij), scope=scope, n_tri=len(ts),
                     n_topo=len({tt["topo"] for tt in ts}),
                     n_fam=len({tt["fam"] for tt in ts}),
                     fam=Counter(tt["fam"] for tt in ts).most_common(1)[0][0],
                     nonplanar=round(nonplan, 3),
                     smin=round(min(tt["slope"] for tt in ts), 3),
                     smax=round(max(tt["slope"] for tt in ts), 3))
            f = fit_cell(pos, uv)
            if f is not None:
                res_max, res_rms, J, npos = f
                ori, kind = classify_J(J)
                ub = [min(w[0] for w in uv), max(w[0] for w in uv)]
                vb = [min(w[1] for w in uv), max(w[1] for w in uv)]
                r.update(res_q=round(res_max, 4), res_rms_q=round(res_rms, 4), n_pos=npos,
                         J_kind=kind, J_ori=ori,
                         J_scale=round(float(math.sqrt(abs(J[0][0] * J[1][1] - J[0][1] * J[1][0]))), 5),
                         uv_extent_tiles=[round((ub[1] - ub[0]) / TILE_U, 4),
                                          round((vb[1] - vb[0]) / TILE_V, 4)])
            dec = decode_l3(cij, pos, uv, UVQ)
            if dec is not None:
                r["l3_err_q"] = round(dec[0] / UVQ, 4)
                r["l3"] = [dec[1], list(dec[2]), dec[3]]
            return r

        for cij, ts in cell_tris.items():
            cells_rec.append(make_rec(cij, ts, "cell"))
            byf = defaultdict(list)
            for tt in ts:
                byf[tt["fam"]].append(tt)
            for fam, sub in byf.items():
                chart_rec.append(make_rec(cij, sub, "cell_x_family"))
                # ---- M3b THE UNFOLD TEST (the direct model comparison) ---------------------
                uf = unfold_pair(sub)
                if uf is None:
                    continue
                planc, surfc, uvc = uf
                rp2 = fit_frame(planc, uvc)
                rs2 = fit_frame(surfc, uvc)
                if rp2 is None or rs2 is None:
                    continue
                ns = [tt["n"] for tt in sub if tt["n"] is not None]
                kink = 0.0
                if len(ns) == 2:
                    kink = math.degrees(math.acos(max(-1.0, min(1.0, float(ns[0] @ ns[1])))))
                UNF.append(dict(fam=fam, kink=round(kink, 3),
                                smax=round(max(tt["slope"] for tt in sub), 3),
                                res_plan_q=round(rp2, 4), res_surf_q=round(rs2, 4)))

    rep["meta"].update(n_blocks_listed=len(blocks), n_blocks_read=n_read,
                       n_blocks_with_ground=n_with_ground,
                       n_ground_tris=int(sum(topo_ct.values())),
                       n_edges_seen=edges_seen, n_edges_kept=edges_kept,
                       n_cells=len(cells_rec), n_cell_x_family=len(chart_rec),
                       M0_uv_quantum_violations=quant_fail)
    rep["topo_census"] = {str(k): v for k, v in sorted(topo_ct.items(), key=lambda kv: -kv[1])}

    # ---- M1 / M2 -------------------------------------------------------------------------
    def table(D, minn=20):
        out = {}
        for (fam, k), d in sorted(D.items()):
            if len(d["plan"]) < minn:
                continue
            out.setdefault(fam, {})[BIN_NAMES[k]] = dict(
                n=len(d["plan"]), slope_med=round(float(np.median(d["slope"])), 2),
                cos_med=round(float(np.median(np.cos(np.radians(d["slope"])))), 5),
                rate_plan=q(d["plan"]), rate_surf=q(d["surf"]))
        return out

    rep["M1_per_edge"] = table(E)
    rep["M1_per_edge_long"] = table(EL)
    rep["M1_per_edge_by_EDGE_inclination"] = table(EI)
    rep["M2_per_tri_areal"] = table(A)

    # ---- M1b THE FULL-CELL-EDGE SPAN -----------------------------------------------------
    fce = {}
    for (fam, k), rows0 in sorted(FCE.items()):
        v = [r[0] for r in rows0]
        inc = [r[1] for r in rows0]
        if len(v) < 12:
            fce.setdefault(fam, {})[BIN_NAMES[k]] = dict(n=len(v))
            continue
        st = q(v, ps=(1, 25, 50, 75, 99))
        imed = float(np.median(inc))
        st["inclination_med"] = round(imed, 3)
        st["pct_of_one_rect_width"] = round(100.0 * st["p50"] / MAINS_SCALE_U, 3)
        st["PLAN_law_predicts_tiles"] = round(MAINS_SCALE_U, 5)
        st["SURF_law_predicts_tiles"] = round(MAINS_SCALE_U / math.cos(math.radians(imed)), 5)
        st["exceeds_one_tile_rate"] = round(sum(1 for x in v if x > 1.0) / len(v), 5)
        fce.setdefault(fam, {})[BIN_NAMES[k]] = st
    rep["M1b_full_cell_edge_span_tiles"] = fce

    # ---- M2b THE ISOTROPY TEST -----------------------------------------------------------
    iso = {}
    for (fam, k), d in sorted(ISO.items()):
        if len(d["ap"]) < 20:
            iso.setdefault(fam, {})[BIN_NAMES[k]] = dict(n=len(d["ap"]))
            continue
        cosm = float(np.median(np.cos(np.radians(d["slope"]))))
        kc = Counter(d["kind"])
        lat = [i for i, kk3 in enumerate(d["kind"]) if kk3 in ("diag", "anti")]
        row = dict(n=len(d["ap"]), slope_med=round(float(np.median(d["slope"])), 2),
                   cos_med=round(cosm, 5),
                   predicted_anisotropy_of_the_LOSING_frame=round(1.0 / cosm, 5),
                   aniso_PLAN_frame=q(d["ap"], ps=(25, 50, 75, 90)),
                   aniso_SURF_frame=q(d["as"], ps=(25, 50, 75, 90)),
                   scale_PLAN_frame=q(d["sp"], ps=(25, 50, 75)),
                   scale_SURF_frame=q(d["ss"], ps=(25, 50, 75)),
                   J_kind=dict(kc.most_common()),
                   lattice_tile_share=round(len(lat) / len(d["kind"]), 5),
                   surface_area=round(float(sum(d["area"])), 1),
                   plan_isotropic_rate=round(sum(1 for x in d["ap"] if x < 1.02) / len(d["ap"]), 5),
                   surf_isotropic_rate=round(sum(1 for x in d["as"] if x < 1.02) / len(d["as"]), 5))
        if lat:                                                # the signed-permutation population
            row["lattice_only"] = dict(
                n=len(lat),
                aniso_PLAN_frame=q([d["ap"][i] for i in lat], ps=(25, 50, 75, 90)),
                aniso_SURF_frame=q([d["as"][i] for i in lat], ps=(25, 50, 75, 90)),
                scale_PLAN_frame=q([d["sp"][i] for i in lat], ps=(25, 50, 75)),
                scale_SURF_frame=q([d["ss"][i] for i in lat], ps=(25, 50, 75)),
                slope_med=round(float(np.median([d["slope"][i] for i in lat])), 2))
        iso.setdefault(fam, {})[BIN_NAMES[k]] = row
    rep["M2b_isotropy"] = iso

    # ---- M2c THE WITHIN-TRIANGLE EDGE-PAIR TEST ------------------------------------------
    pair = {}
    for (fam, k), rows0 in sorted(PAIR.items()):
        if len(rows0) < 20:
            pair.setdefault(fam, {})[BIN_NAMES[k]] = dict(n=len(rows0))
            continue
        obs = np.array([r[0] for r in rows0])
        pred_surf = np.array([1.0 / r[1] for r in rows0])
        # per-pair: whose prediction is closer, on a log scale (symmetric)
        d_plan = np.abs(np.log(obs))
        d_surf = np.abs(np.log(obs / pred_surf))
        pair.setdefault(fam, {})[BIN_NAMES[k]] = dict(
            n=len(rows0), slope_med=round(float(np.median([r[2] for r in rows0])), 2),
            observed_ratio=q(obs.tolist(), ps=(10, 25, 50, 75, 90)),
            PLAN_predicts=1.0,
            SURF_predicts=q(pred_surf.tolist(), ps=(25, 50, 75)),
            plan_closer_rate=round(float((d_plan < d_surf).mean()), 5),
            median_log_err_PLAN=round(float(np.median(d_plan)), 5),
            median_log_err_SURF=round(float(np.median(d_surf)), 5),
            err_ratio_SURF_over_PLAN=(round(float(np.median(d_surf) / np.median(d_plan)), 3)
                                      if np.median(d_plan) > 0 else None))
    rep["M2c_within_triangle_edge_pair"] = pair

    # ---- M2d THE QUANTA TEST -------------------------------------------------------------
    qnt = {}
    for (fam, k), rows0 in sorted(QNT.items()):
        lat = [r for r in rows0 if r[2]]
        row = dict(n=len(rows0), n_lattice=len(lat),
                   lattice_share=round(len(lat) / len(rows0), 5) if rows0 else None)
        if len(rows0) >= 20:
            row["slope_med"] = round(float(np.median([r[3] for r in rows0])), 2)
        if len(lat) >= 15:
            s1 = [r[0] for r in lat]
            s2 = [r[1] for r in lat]
            smed = float(np.median([r[3] for r in lat]))
            h1 = Counter(int(round(x * 64)) for x in s1)
            h2 = Counter(int(round(x * 64)) for x in s2)
            on = sum(v for kk4, v in h1.items() if kk4 in (62, 64)) + \
                sum(v for kk4, v in h2.items() if kk4 in (62, 64))
            row.update(
                lattice_slope_med=round(smed, 2),
                sigma1_quanta_top6=h1.most_common(6), sigma2_quanta_top6=h2.most_common(6),
                on_62_or_64_rate=round(on / (2 * len(lat)), 5),
                SURF_law_would_need_quanta=round(62.0 / math.cos(math.radians(smed)), 2),
                sigma1=q(s1, ps=(25, 50, 75)), sigma2=q(s2, ps=(25, 50, 75)))
        qnt.setdefault(fam, {})[BIN_NAMES[k]] = row
    rep["M2d_quanta_test"] = qnt

    # ---- M2e THE CROSSOVER SWEEP ---------------------------------------------------------
    # M2d shows sigma2 (the CONTOUR axis) pinned on 62/64 quanta at every slope while sigma1
    # (the DOWN-SLOPE axis) slides. This locates the crossover: at each 5-degree step, the
    # measured anisotropy sigma1/sigma2 against the PLAN prediction (constant, = the window
    # aspect) and the SURFACE prediction (that constant / cos(slope)). surface_fraction
    # interpolates the two -- 0 = pure plan, 1 = pure surface arclength down-slope.
    FINE = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40),
            (40, 50), (50, 91)]
    sweep = {}
    for fam in ("MAINS_FAMS", "grass", "desert", "forest", "ALL"):
        allrows = [r for k2 in range(4) for r in QNT.get((fam, k2), []) if r[2]]
        if not allrows:
            continue
        base = [r for r in allrows if r[3] < 5.0]
        a0 = float(np.median([r[0] / r[1] for r in base])) if len(base) >= 20 else None
        rows = {}
        for lo, hi in FINE:
            sel = [r for r in allrows if lo <= r[3] < hi]
            if len(sel) < 15:
                rows[f"{lo}-{hi}"] = dict(n=len(sel))
                continue
            an = [r[0] / r[1] for r in sel]
            smed = float(np.median([r[3] for r in sel]))
            cosm = math.cos(math.radians(smed))
            e = dict(n=len(sel), slope_med=round(smed, 2),
                     sigma1_quanta_med=round(float(np.median([r[0] * 64 for r in sel])), 2),
                     sigma2_quanta_med=round(float(np.median([r[1] * 64 for r in sel])), 2),
                     aniso_med=round(float(np.median(an)), 5),
                     PLAN_predicts=round(a0, 5) if a0 else None,
                     SURF_predicts=round(a0 / cosm, 5) if a0 else None)
            if a0 and abs(a0 / cosm - a0) > 1e-6:
                e["surface_fraction"] = round((e["aniso_med"] - a0) / (a0 / cosm - a0), 4)
            rows[f"{lo}-{hi}"] = e
        sweep[fam] = dict(window_aspect_baseline=round(a0, 5) if a0 else None, bins=rows)
    rep["M2e_crossover_sweep"] = sweep

    def drift(D, minn=20, exp=1.0):
        """exp = the power of cos that the metric carries: 1.0 for a LENGTH rate,
        0.5 for an AREAL scale (A_plan/A_surf = cos, and the scale is its square root)."""
        dd = {}
        for fam in sorted({f for (f, _k) in D}):
            base = D.get((fam, 0))
            if not base or len(base["plan"]) < minn:
                continue
            bp, bs = float(np.median(base["plan"])), float(np.median(base["surf"]))
            row = {"baseline_0-10": dict(n=len(base["plan"]),
                                        plan_med=round(bp, 5), surf_med=round(bs, 5),
                                        plan_iqr_pct=round(100 * (np.percentile(base["plan"], 75)
                                                                  - np.percentile(base["plan"], 25)) / bp, 3))}
            for k in range(1, len(SLOPE_BINS)):
                d = D.get((fam, k))
                if not d or len(d["plan"]) < minn:
                    continue
                mp, ms = float(np.median(d["plan"])), float(np.median(d["surf"]))
                cosm = float(np.median(np.cos(np.radians(d["slope"])))) ** exp
                row[BIN_NAMES[k]] = dict(
                    n=len(d["plan"]), slope_med=round(float(np.median(d["slope"])), 2),
                    plan_drift_pct=round(100.0 * (mp - bp) / bp, 3),
                    surf_drift_pct=round(100.0 * (ms - bs) / bs, 3),
                    SURF_drift_if_PLAN_law_pct=round(100.0 * (cosm - 1.0), 3),
                    PLAN_drift_if_SURF_law_pct=round(100.0 * (1.0 / cosm - 1.0), 3),
                    plan_iqr_pct=round(100.0 * (np.percentile(d["plan"], 75)
                                                - np.percentile(d["plan"], 25)) / mp, 3),
                    surf_iqr_pct=round(100.0 * (np.percentile(d["surf"], 75)
                                                - np.percentile(d["surf"], 25)) / ms, 3))
            dd[fam] = row
        return dd

    rep["discrimination"] = {"M1_per_edge": drift(E), "M1_per_edge_long": drift(EL),
                             "M1_per_edge_by_EDGE_inclination": drift(EI),
                             "M2_per_tri_areal": drift(A, exp=0.5)}

    # ---- M3b THE UNFOLD TEST -------------------------------------------------------------
    unf = {}
    KB = [(0.0, 1.0), (1.0, 5.0), (5.0, 15.0), (15.0, 30.0), (30.0, 181.0)]
    for scope in ("ALL", "MAINS_FAMS"):
        sel0 = UNF if scope == "ALL" else [r for r in UNF if r["fam"] in MAINS_FAMS]
        rows = {"n_pairs": len(sel0)}
        for lo, hi in KB:
            sel = [r for r in sel0 if lo <= r["kink"] < hi]
            e = dict(n=len(sel))
            if len(sel) >= 10:
                dp = [r["res_plan_q"] for r in sel]
                ds = [r["res_surf_q"] for r in sel]
                e.update(res_PLAN_q=q(dp, ps=(50, 90)), res_SURF_q=q(ds, ps=(50, 90)),
                         plan_wins_rate=round(sum(1 for r in sel
                                                  if r["res_plan_q"] < r["res_surf_q"]) / len(sel), 5),
                         plan_wins_decisively_rate=round(
                             sum(1 for r in sel if r["res_plan_q"] + 0.5 < r["res_surf_q"]) / len(sel), 5),
                         surf_wins_decisively_rate=round(
                             sum(1 for r in sel if r["res_surf_q"] + 0.5 < r["res_plan_q"]) / len(sel), 5),
                         smax_med=round(float(np.median([r["smax"] for r in sel])), 2))
            rows[f"kink_{lo:g}-{hi:g}deg"] = e
        unf[scope] = rows
    rep["M3b_unfold_test"] = unf

    rep["slope_envelope"] = {f: q(v, ps=(50, 90, 95, 99)) for f, v in sorted(slopes_by_fam.items())}
    rep["surface_area_by_fam"] = {f: round(v, 1) for f, v in sorted(area_by_fam.items())}

    # ---- M3 tables -----------------------------------------------------------------------
    def m3(recs, label):
        fitted = [c for c in recs if "res_q" in c]
        o = {"n": len(recs), "n_overdetermined": len(fitted),
             "n_underdetermined_lt4pos": len(recs) - len(fitted)}
        if not fitted:
            return o
        o["res_quanta"] = q([c["res_q"] for c in fitted], ps=(50, 75, 90, 99))
        o["plan_affine_rate"] = round(sum(1 for c in fitted if c["res_q"] < AFFINE_Q) / len(fitted), 5)
        o["J_kind"] = dict(Counter(c["J_kind"] for c in fitted).most_common())
        o["J_ori"] = dict(Counter(str(c["J_ori"]) for c in fitted).most_common())
        o["J_scale"] = q([c["J_scale"] for c in fitted], ps=(1, 25, 50, 75, 99))
        one = [c for c in fitted if c["res_q"] < AFFINE_Q and c["J_ori"] is not None
               and abs(c["J_scale"] - MAINS_SCALE_U) < 0.03
               and max(c["uv_extent_tiles"]) < 1.02]
        o["single_tile_plus_ori_rate"] = round(len(one) / len(fitted), 5)
        o["single_tile_plus_ori_n"] = len(one)
        # THE DISCRIMINATING SPLIT
        NPB = [(0.0, 1.0), (1.0, 5.0), (5.0, 15.0), (15.0, 30.0), (30.0, 181.0)]
        o["by_nonplanarity"] = {}
        for lo, hi in NPB:
            sel = [c for c in fitted if lo <= c["nonplanar"] < hi]
            e = dict(n=len(sel))
            if len(sel) >= 10:
                e.update(res_q=q([c["res_q"] for c in sel], ps=(50, 90, 99)),
                         plan_affine_rate=round(sum(1 for c in sel if c["res_q"] < AFFINE_Q) / len(sel), 5),
                         smax_med=round(float(np.median([c["smax"] for c in sel])), 2),
                         J_scale_med=round(float(np.median([c["J_scale"] for c in sel])), 5))
            o["by_nonplanarity"][f"{lo:g}-{hi:g}deg"] = e
        o["by_max_slope"] = {}
        for k, (lo, hi) in enumerate(SLOPE_BINS):
            sel = [c for c in fitted if lo <= c["smax"] < hi]
            e = dict(n=len(sel))
            if len(sel) >= 10:
                e.update(res_q=q([c["res_q"] for c in sel], ps=(50, 90, 99)),
                         plan_affine_rate=round(sum(1 for c in sel if c["res_q"] < AFFINE_Q) / len(sel), 5),
                         nonplanar_med=round(float(np.median([c["nonplanar"] for c in sel])), 2),
                         J_scale=q([c["J_scale"] for c in sel], ps=(25, 50, 75)),
                         uv_extent_max_tiles=q([max(c["uv_extent_tiles"]) for c in sel],
                                               ps=(50, 90, 99)),
                         over_one_tile_rate=round(sum(1 for c in sel
                                                      if max(c["uv_extent_tiles"]) > 1.02) / len(sel), 5),
                         single_tile_plus_ori_rate=round(
                             sum(1 for c in sel if c["res_q"] < AFFINE_Q and c["J_ori"] is not None
                                 and abs(c["J_scale"] - MAINS_SCALE_U) < 0.03
                                 and max(c["uv_extent_tiles"]) < 1.02) / len(sel), 5))
            o["by_max_slope"][BIN_NAMES[k]] = e
        mixed = [c for c in fitted if c["n_topo"] > 1]
        o["class_boundary_cells"] = dict(
            n=len(mixed), share=round(len(mixed) / len(fitted), 5),
            res_q=q([c["res_q"] for c in mixed], ps=(50, 90, 99)) if len(mixed) >= 10 else None,
            plan_affine_rate=(round(sum(1 for c in mixed if c["res_q"] < AFFINE_Q) / len(mixed), 5)
                              if mixed else None),
            n_fam_gt1=sum(1 for c in fitted if c["n_fam"] > 1))
        o["per_family"] = {}
        for fam in sorted({c["fam"] for c in fitted}):
            sel = [c for c in fitted if c["fam"] == fam]
            if len(sel) < 10:
                continue
            row = dict(n=len(sel),
                       plan_affine_rate=round(sum(1 for c in sel if c["res_q"] < AFFINE_Q) / len(sel), 5),
                       res_q_p90=round(float(np.percentile([c["res_q"] for c in sel], 90)), 4),
                       single_tile_plus_ori_rate=round(
                           sum(1 for c in sel if c["res_q"] < AFFINE_Q and c["J_ori"] is not None
                               and abs(c["J_scale"] - MAINS_SCALE_U) < 0.03
                               and max(c["uv_extent_tiles"]) < 1.02) / len(sel), 5))
            l3 = [c["l3_err_q"] for c in sel if "l3_err_q" in c]
            if l3:
                row["l3_locked_decode_rate"] = round(sum(1 for e2 in l3 if e2 < 1.0) / len(l3), 5)
                row["l3_n_in_a_GROUNDS_region"] = len(l3)
            o["per_family"][fam] = row
        # the shipped decoder's own gate, for the record
        l3all = [c["l3_err_q"] for c in recs if "l3_err_q" in c]
        if l3all:
            o["l3_locked_rect_decoder"] = dict(
                n_in_a_GROUNDS_region=len(l3all),
                n_outside_every_GROUNDS_region=len(recs) - len(l3all),
                rate_at_1_quantum=round(sum(1 for e2 in l3all if e2 < 1.0) / len(l3all), 5),
                rate_at_shipped_DECODE_ERR=round(
                    sum(1 for e2 in l3all if e2 * UVQ < DECODE_ERR) / len(l3all), 5),
                err_quanta=q(l3all, ps=(25, 50, 75, 90)))
            by = {}
            for k, (lo, hi) in enumerate(SLOPE_BINS):
                sel = [c for c in recs if "l3_err_q" in c and lo <= c["smax"] < hi]
                by[BIN_NAMES[k]] = (dict(n=len(sel),
                                         rate_at_1_quantum=round(sum(1 for c in sel if c["l3_err_q"] < 1.0)
                                                                 / len(sel), 5))
                                    if sel else dict(n=0))
            o["l3_locked_rect_decoder"]["by_max_slope"] = by
        return o

    rep["M3_per_cell"] = m3(cells_rec, "cell")
    rep["M3_per_cell_x_family"] = m3(chart_rec, "cell_x_family")
    mains_charts = [c for c in chart_rec if c["fam"] in MAINS_FAMS]
    rep["M3_mains_family_charts"] = m3(mains_charts, "mains")

    # ---- M4 ------------------------------------------------------------------------------
    rep["M4_cross_cell_phase"] = dict(
        n_shared_plan_positions=xc_tot,
        identical_uv_rate=round(xc_same / xc_tot, 5) if xc_tot else None,
        on_4u_border_rate=round(xc_border / xc_tot, 5) if xc_tot else None,
        duv_tiles_when_different=q(xc_duv, ps=(5, 25, 50, 75, 95)),
        du_frac_of_tile=q(xc_du_frac, ps=(50, 75, 90, 99)),
        dv_frac_of_tile=q(xc_dv_frac, ps=(50, 75, 90, 99)),
        whole_tile_jump_rate=(round(sum(1 for a, b in zip(xc_du_frac, xc_dv_frac)
                                        if a < 0.05 and b < 0.05) / len(xc_du_frac), 5)
                              if xc_du_frac else None))

    # ---- THE VERDICT ---------------------------------------------------------------------
    rep["VERDICT"] = {
        "law": ("THE TWO-AXIS GROUND-UV LAW. Stock ground uv is PLAN-projected, not "
                "surface-arclength -- but only the CONTOUR axis is plan-projected "
                "unconditionally. Per 4u lattice cell the uv map's contour-direction scale is "
                "pinned on 62 or 64 uv quanta per 4u (the mains rect width / one full tile "
                "pitch) at EVERY slope measured, to 42 deg; the DOWN-SLOPE axis is pinned on "
                "the same two integers on gentle ground and slides toward the 3D-extent "
                "(surface) value as the face steepens, reaching it by ~40 deg where stock's "
                "vocabulary has become the vertical CURTAIN."),
        "invariant": "the contour-axis scale (sigma2) = 62 quanta per 4u, slope-independent",
        "atlas_units": {"atlas_px": [2048, 4096], "one_tile_px": [128, 128],
                        "one_uv_quantum_px": [2.0, 4.0], "62_quanta_px": 124.0},
        "visibility_criterion": ("ONE UV QUANTUM of accumulated offset across a 4u cell "
                                 "(= 2 atlas texels in u, 4 in v, ~1.6% of a tile). Below one "
                                 "quantum a plan-projected retile is byte-indistinguishable "
                                 "from a lawful stock choice, because stock's own uv is only "
                                 "authored to that resolution (M0). Above it the retile places "
                                 "a value stock never places, and the offset accumulates "
                                 "across cells into a visible drift."),
        "plan_retile_error_vs_stock_by_slope": {
            "<=10deg": "0.0 quanta (surface_fraction 0.000-0.003) -- EXACT",
            "10-15deg": "median sigma1 still 64q -- under 1 quantum",
            "15-20deg": "median sigma1 64.0-65.2q -- ~1 quantum, borderline",
            "20-25deg": "median sigma1 66.5q (mains) -- 2.5 quanta = 5 atlas px per cell",
            "25-30deg": "median sigma1 67.0q (mains) -- 3.0 quanta",
            "30-35deg": "median sigma1 68.4q (mains) -- 4.4 quanta",
            ">=40deg": "stock is no longer plan-projected ground at all (curtain convention)"},
        "threshold": 20.0,
        "threshold_note": ("20 deg is where the plan projection's disagreement with stock's own "
                           "choice first exceeds one uv quantum on mains-family ground. DESERT "
                           "holds plan exactly to ~32 deg (sigma1 = 64.00q through the 30-35 "
                           "bin), so the threshold is family-dependent and 20 deg is the "
                           "conservative mains number."),
        "slope_envelope_note": ("mains-family ground itself is nearly all below the threshold: "
                                "grass p50 6.5 / p90 15.7 / p99 28.6; plateau p90 12.8 / p99 "
                                "24.6. Grass above 35 deg is a handful of triangles map-wide."),
        "per_cell_L3_model": {
            "single_tile_plus_orientation_rate_flat": 0.32267,
            "single_tile_plus_orientation_rate_10_25": 0.22766,
            "single_tile_plus_orientation_rate_25_40": "see M3 by_max_slope",
            "locked_rect_decoder_rate_at_1_quantum": 0.1208,
            "note": ("L3 as SHIPPED (grassland.ground_uv's locked 2x2 quadrant rects) matches "
                     "only ~12% of stock ground cells at a one-quantum gate and ~6.7% at the "
                     "shipped DECODE_ERR=1e-4 -- and 1e-4 is TEN TIMES TIGHTER than the data's "
                     "own quantum (9.77e-4), so the shipped gate structurally rejects lawful "
                     "stock cells. Stock's general form is a FREE window (any 62- or 64-quanta "
                     "rect), plan-projected; the locked 2x2 is a minority real form.")},
        "cross_cell": ("each cell RESTARTS its chart: only 23.5% of plan positions shared "
                       "between two cells carry identical uv; when they differ the jump is "
                       "whole-tile-quantized 46% of the time and median 2.78 tiles."),
        "class_boundary": ("a cell that spans two ground FAMILIES is two charts, not one: "
                          "plan-affine rate collapses 0.552 -> 0.253 and the residual median "
                          "goes 0.61 -> 104 quanta."),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    print(f"\nwrote {OUT}")

    # ---- the picture ---------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 3, figsize=(18, 5.0))

        # (1) M1b -- the full-cell-edge span vs EDGE inclination
        ax = axes[0]
        for fam, col in (("MAINS_FAMS", "tab:green"), ("desert", "tab:orange")):
            xx, mm, lo, hi = [], [], [], []
            for k in range(4):
                rows0 = FCE.get((fam, k))
                if not rows0 or len(rows0) < 12:
                    continue
                v = [r[0] for r in rows0]
                xx.append(float(np.median([r[1] for r in rows0])))
                mm.append(float(np.median(v)))
                lo.append(float(np.percentile(v, 25)))
                hi.append(float(np.percentile(v, 75)))
            ax.plot(xx, mm, "o-", color=col, label=f"{fam} measured |duv|")
            ax.fill_between(xx, lo, hi, color=col, alpha=0.15)
        th = np.linspace(0, 35, 200)
        ax.axhline(MAINS_SCALE_U, color="k", lw=1.1, ls="--",
                   label="PLAN law: 0.9686 tiles (62 quanta), slope-independent")
        ax.axhline(1.0, color="k", lw=0.7, ls=":", label="one full tile pitch (64 quanta)")
        ax.plot(th, MAINS_SCALE_U / np.cos(np.radians(th)), "r-.", lw=1.2,
                label="SURFACE law: 0.9686 / cos(inclination)")
        ax.set_xlabel("EDGE inclination (deg)")
        ax.set_ylabel("|duv| across a 4u plan cell side (tiles)")
        ax.set_title("M1b  a 4u cell side maps to ONE tile pitch at every inclination")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)

        # (2) M2e -- the crossover sweep
        ax = axes[1]
        for fam, col in (("MAINS_FAMS", "tab:green"), ("desert", "tab:orange"),
                         ("forest", "tab:purple")):
            sw = sweep.get(fam)
            if not sw:
                continue
            xx = [e["slope_med"] for e in sw["bins"].values() if "aniso_med" in e]
            yy = [e["aniso_med"] for e in sw["bins"].values() if "aniso_med" in e]
            ax.plot(xx, yy, "o-", color=col, label=f"{fam} measured sigma1/sigma2")
        a0 = sweep.get("MAINS_FAMS", {}).get("window_aspect_baseline") or 1.03226
        th = np.linspace(0, 50, 200)
        ax.axhline(a0, color="k", lw=1.1, ls="--",
                   label=f"PLAN law: constant {a0:.4f} (stock's own window aspect)")
        ax.plot(th, a0 / np.cos(np.radians(th)), "r-.", lw=1.2,
                label="SURFACE law: aspect / cos(slope)")
        ax.axvline(20.0, color="tab:red", lw=0.8, ls=":")
        ax.text(20.4, a0 - 0.01, "20 deg: 1-quantum\nthreshold", fontsize=7, color="tab:red")
        ax.set_xlabel("triangle slope (deg)")
        ax.set_ylabel("uv map anisotropy (down-slope / contour scale)")
        ax.set_title("M2e  the contour axis never moves; the down-slope axis slides")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25)

        # (3) M2d -- the quanta histogram, flat vs steep
        ax = axes[2]
        w = 0.4
        for off, (k, lab, col) in enumerate(((0, "slope 0-10", "tab:blue"),
                                             (2, "slope 25-40", "tab:red"))):
            rows0 = [r for r in QNT.get(("ALL", k), []) if r[2]]
            if not rows0:
                continue
            h = Counter(int(round(r[0] * 64)) for r in rows0)
            tot = sum(h.values())
            ks = sorted(kk5 for kk5 in h if 55 <= kk5 <= 90)
            ax.bar([kk5 + (off - 0.5) * w for kk5 in ks], [h[kk5] / tot for kk5 in ks],
                   width=w, color=col, alpha=0.75, label=f"{lab} (n={tot})")
        ax.axvline(62, color="k", lw=1.0, ls="--")
        ax.axvline(64, color="k", lw=1.0, ls=":")
        ax.text(62.2, ax.get_ylim()[1] * 0.92, "62 = mains rect", fontsize=7)
        ax.text(64.2, ax.get_ylim()[1] * 0.84, "64 = tile pitch", fontsize=7)
        ax.axvline(70.9, color="tab:red", lw=1.0, ls="-.")
        ax.text(71.1, ax.get_ylim()[1] * 0.7, "70.9 = what the SURFACE\nlaw needs at 29 deg",
                fontsize=7, color="tab:red")
        ax.set_xlabel("down-slope uv scale (uv quanta per 4u cell)")
        ax.set_ylabel("share of window-mapped ground triangles")
        ax.set_title("M2d  the scale is pinned on two integers, not a function of slope")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.25, axis="y")

        fig.tight_layout()
        fig.savefig(PNG, dpi=120)
        print(f"wrote {PNG}")
    except Exception as exc:                                  # noqa: BLE001
        print("plot skipped:", exc)

    # ---- console digest -------------------------------------------------------------------
    print("\n== M1b FULL-CELL-EDGE SPAN (plan 4.0u edges) by EDGE inclination ==")
    for fam in ("MAINS_FAMS", "grass", "desert", "ALL"):
        row = fce.get(fam)
        if not row:
            continue
        print(f"  [{fam}]")
        for bn in BIN_NAMES:
            st = row.get(bn)
            if not st or "p50" not in st:
                print(f"    {bn:>6}: n={0 if not st else st.get('n')}  (below 12, not reported)")
                continue
            print(f"    {bn:>6}: n={st['n']:6d} inc_med={st['inclination_med']:5.1f} | "
                  f"|duv| med={st['p50']:.4f} (p25 {st['p25']:.4f} p75 {st['p75']:.4f}) | "
                  f"PLAN predicts {st['PLAN_law_predicts_tiles']:.4f}  "
                  f"SURF predicts {st['SURF_law_predicts_tiles']:.4f} | "
                  f">1 tile in {100*st['exceeds_one_tile_rate']:.2f}%")

    print("\n== M2b THE ISOTROPY TEST -- which frame is the uv map a SIMILARITY in? ==")
    for fam in ("MAINS_FAMS", "grass", "desert", "forest", "ALL"):
        row = iso.get(fam)
        if not row:
            continue
        print(f"  [{fam}]")
        for bn in BIN_NAMES:
            st = row.get(bn)
            if not st or "aniso_PLAN_frame" not in st:
                print(f"    {bn:>6}: n={0 if not st else st.get('n')}  (below 20, not reported)")
                continue
            L = st.get("lattice_only") or {}
            print(f"    {bn:>6}: n={st['n']:6d} slope={st['slope_med']:5.1f} "
                  f"1/cos={st['predicted_anisotropy_of_the_LOSING_frame']:.4f} | "
                  f"aniso PLAN={st['aniso_PLAN_frame']['p50']:.4f} "
                  f"SURF={st['aniso_SURF_frame']['p50']:.4f} | "
                  f"scale PLAN={st['scale_PLAN_frame']['p50']:.4f} "
                  f"SURF={st['scale_SURF_frame']['p50']:.4f} | "
                  f"lattice-tile {100*st['lattice_tile_share']:5.1f}%"
                  + (f" (lattice-only aniso PLAN={L['aniso_PLAN_frame']['p50']:.4f} "
                     f"SURF={L['aniso_SURF_frame']['p50']:.4f})" if L else ""))

    print("\n== M2d THE QUANTA TEST -- is the uv scale pinned on 62/64 quanta at every slope? ==")
    for fam in ("MAINS_FAMS", "grass", "desert", "forest", "ALL"):
        row = qnt.get(fam)
        if not row:
            continue
        print(f"  [{fam}]")
        for bn in BIN_NAMES:
            st = row.get(bn)
            if not st:
                continue
            if "sigma1_quanta_top6" not in st:
                print(f"    {bn:>6}: n={st['n']} lattice={st['n_lattice']}  (below 15, not reported)")
                continue
            print(f"    {bn:>6}: n={st['n']:6d} lattice={st['n_lattice']:6d} "
                  f"({100*st['lattice_share']:4.1f}%) slope={st['lattice_slope_med']:5.1f} | "
                  f"SURF law would need {st['SURF_law_would_need_quanta']:.1f} quanta | "
                  f"on 62/64: {100*st['on_62_or_64_rate']:5.1f}%")
            print(f"            sigma1 quanta {st['sigma1_quanta_top6']}")
            print(f"            sigma2 quanta {st['sigma2_quanta_top6']}")

    print("\n== M2e THE CROSSOVER SWEEP (lattice/window tris; where does plan give way?) ==")
    for fam in ("MAINS_FAMS", "grass", "desert", "forest", "ALL"):
        sw = sweep.get(fam)
        if not sw:
            continue
        print(f"  [{fam}]  window-aspect baseline a0 = {sw['window_aspect_baseline']}")
        for bnm, e in sw["bins"].items():
            if "aniso_med" not in e:
                print(f"    {bnm:>6}deg: n={e['n']}  (below 15)")
                continue
            print(f"    {bnm:>6}deg: n={e['n']:6d} slope={e['slope_med']:5.1f} | "
                  f"sigma1={e['sigma1_quanta_med']:6.2f}q sigma2={e['sigma2_quanta_med']:6.2f}q | "
                  f"aniso={e['aniso_med']:.4f}  PLAN={e['PLAN_predicts']}  SURF={e['SURF_predicts']} | "
                  f"surface_fraction={e.get('surface_fraction')}")

    print("\n== M2c WITHIN-TRIANGLE EDGE-PAIR TEST (one map, two inclinations) ==")
    for fam in ("MAINS_FAMS", "grass", "desert", "forest", "ALL"):
        row = pair.get(fam)
        if not row:
            continue
        print(f"  [{fam}]")
        for bn in BIN_NAMES:
            st = row.get(bn)
            if not st or "observed_ratio" not in st:
                print(f"    {bn:>6}: n={0 if not st else st.get('n')}  (below 20, not reported)")
                continue
            print(f"    {bn:>6}: n={st['n']:6d} slope={st['slope_med']:5.1f} | observed "
                  f"rate_plan ratio med={st['observed_ratio']['p50']:.4f} "
                  f"(p25 {st['observed_ratio']['p25']:.4f} p75 {st['observed_ratio']['p75']:.4f}) | "
                  f"PLAN predicts 1.0000  SURF predicts {st['SURF_predicts']['p50']:.4f} | "
                  f"PLAN closer in {100*st['plan_closer_rate']:5.1f}% of triangles "
                  f"(median |log| err SURF/PLAN = {st['err_ratio_SURF_over_PLAN']})")

    print("\n== M3b THE UNFOLD TEST (plan-affine vs surface-affine on the SAME uv bytes) ==")
    for scope in ("MAINS_FAMS", "ALL"):
        print(f"  [{scope}] n_pairs={unf[scope]['n_pairs']}")
        for k2, v2 in unf[scope].items():
            if k2 == "n_pairs" or "res_PLAN_q" not in v2:
                if k2 != "n_pairs":
                    print(f"    {k2:>22}: n={v2.get('n')}  (below 10, not reported)")
                continue
            print(f"    {k2:>22}: n={v2['n']:6d} smax_med={v2['smax_med']:5.1f} | "
                  f"res PLAN med={v2['res_PLAN_q']['p50']:7.3f}q  SURF med={v2['res_SURF_q']['p50']:7.3f}q "
                  f"| plan wins {100*v2['plan_wins_rate']:5.1f}%  "
                  f"decisively {100*v2['plan_wins_decisively_rate']:5.1f}% vs surf "
                  f"{100*v2['surf_wins_decisively_rate']:5.1f}%")

    for nm, D in (("M1 per-edge >=1u", E), ("M1 per-edge by EDGE inclination", EI),
                  ("M1 per-edge >=3u", EL), ("M2 per-tri areal", A)):
        for fam in ("MAINS_FAMS", "grass", "desert", "ALL"):
            rows = [(k, D.get((fam, k))) for k in range(4)]
            if not any(d and len(d["plan"]) >= 20 for _k, d in rows):
                continue
            print(f"\n== {nm}  [{fam}] ==")
            for k, d in rows:
                if not d or len(d["plan"]) < 20:
                    print(f"  {BIN_NAMES[k]:>6}: n={0 if not d else len(d['plan'])}  (below 20, not reported)")
                    continue
                cosm = float(np.median(np.cos(np.radians(d["slope"]))))
                print(f"  {BIN_NAMES[k]:>6}: n={len(d['plan']):7d} slope={np.median(d['slope']):5.1f} "
                      f"cos={cosm:.4f} | PLAN {np.median(d['plan']):.4f} "
                      f"(iqr {100*(np.percentile(d['plan'],75)-np.percentile(d['plan'],25))/np.median(d['plan']):5.2f}%) "
                      f"| SURF {np.median(d['surf']):.4f} "
                      f"(iqr {100*(np.percentile(d['surf'],75)-np.percentile(d['surf'],25))/np.median(d['surf']):5.2f}%)")
    for lbl in ("M3_per_cell", "M3_per_cell_x_family", "M3_mains_family_charts"):
        o = rep[lbl]
        print(f"\n== {lbl} ==")
        print("  ", json.dumps({k: v for k, v in o.items()
                                if k in ("n", "n_overdetermined", "plan_affine_rate",
                                         "single_tile_plus_ori_rate", "J_kind", "J_ori")},
                               default=str))
        print("   res_quanta:", json.dumps(o.get("res_quanta"), default=str))
        print("   by nonplanarity:", json.dumps(o.get("by_nonplanarity"), default=str)[:1400])
        print("   by max slope   :", json.dumps(o.get("by_max_slope"), default=str)[:1400])
        print("   class boundary :", json.dumps(o.get("class_boundary_cells"), default=str)[:500])
        print("   locked decoder :", json.dumps(o.get("l3_locked_rect_decoder"), default=str)[:700])
    print("\n== M4 cross-cell ==\n ", json.dumps(rep["M4_cross_cell_phase"], default=str))
    print("\n== slope envelope ==")
    for f, v in rep["slope_envelope"].items():
        if v and v["n"] >= 50:
            print(f"  {f:>16}: n={v['n']:6d} p50={v['p50']:5.1f} p90={v['p90']:5.1f} "
                  f"p99={v['p99']:5.1f} max={v['max']:5.1f}")
    print("\nM0 uv-quantum violations:", quant_fail or "none (1/1024 holds everywhere read)")


if __name__ == "__main__":
    main()
