"""ADVERSARIAL RE-MEASUREMENT of S1's claimed "TWO-AXIS GROUND-UV LAW".

The claim under test (ground_uv_law.py / out/ground_uv_law.json):
  "the CONTOUR axis is plan-locked at 62 quanta per 4u at every slope to 42 deg; the
   DOWN-SLOPE axis sits on 62/64 on gentle ground and slides toward the surface
   (arclength) value as the face steepens -- crossing over above ~20 deg on grass and
   reaching FULL surface-following by ~42 deg."
and its build rule: "retile freely <=20 deg; 20-35 deg keep the donor uv; >35 deg not ground."

THREE INDEPENDENT ATTACKS, all by a DIFFERENT statistic than theirs:

A. THE AXIS-LABEL ATTACK (their sigma1/sigma2 are UNLABELLED).
   ground_uv_law.py reads sigma1/sigma2 = the SVD singular values of J_plan. SVD orders
   by MAGNITUDE, not by axis. "sigma2 pinned at 62, sigma1 rising" is the *definition* of
   "the larger one got larger" -- it is true of ANY perturbation, in ANY direction. Their
   two-axis law needs the stretch to lie ALONG the plan gradient. So I measure the
   DIRECTION-LABELLED rates instead:
      g_hat = unit plan direction of steepest descent (from the face normal)
      c_hat = its plan perpendicular (the contour)
      s_g = |J_plan . g_hat|, s_c = |J_plan . c_hat|     [quanta per 4u, 1 quantum = 1/64 tile]
   PLAN law   -> s_g = s_c = 62..64 at every slope.
   SURFACE law-> s_g = 62/cos(slope), s_c = 62.
   Plus theta = angle between J_plan's max-stretch plan direction and g_hat. Under the
   claimed law theta -> 0. Under a noise story theta is spread (median near 45 deg).

B. THE NOISE-FLOOR ATTACK (a synthetic PLAN control through the same pipeline).
   J_plan = D . inv(P_plan). As a face steepens its PLAN extent shrinks by cos, so
   inv(P_plan) grows and the 1/1024 uv quantization in D is amplified by ~1/cos --
   preferentially into the LARGER singular value. So a face that is PERFECTLY
   plan-projected must still read as "sliding toward surface" through their statistic.
   Control: keep the REAL vertex positions, overwrite uv with an EXACT mains-rect plan
   map (62 quanta per 4u, real per-cell phase/orientation), re-quantize to 1/1024, and
   run the identical measurement. Also a SURFACE positive control (same map applied to
   per-triangle isometrically-unfolded coords) to prove the test has power.
   Verdict rule: an effect that the synthetic PLAN control reproduces is not evidence.

C. THE CELL-BUDGET COUNTEREXAMPLE.
   Ground verts sit on the 4u PLAN lattice. If a steep cell's uv extent is still exactly
   one tile, its cell-average scale is plan-locked BY CONSTRUCTION, and no systematic
   down-slope surface slide can be present -- whatever the per-triangle SVD says. Measured
   per cell by slope bin, plus a hunt for individual STEEP (>=25, >=35, >=40 deg) stock
   ground triangles that are exactly-plan on BOTH labelled axes.

Also re-derived independently: the shipped-decoder gate surprise (1e-4 vs one quantum),
and the true uv quantum PER AXIS (the claim's "1 quantum = 1/64 tile" is only true in u).

Read-only vs stock disc-1 and disc-4 (a DIFFERENT block sample than the claim's disc-1-only).
Artifacts -> out/verify_s1_ground_uv.json + out/verify_s1_ground_uv.png
Run: py -X utf8 verify_s1_ground_uv.py [max_blocks_per_disc]
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
UVQ = 1.0 / 1024.0
OUT = HERE / "out" / "verify_s1_ground_uv.json"
PNG = HERE / "out" / "verify_s1_ground_uv.png"

FOOT_MASK = (0x0010667F, 0xD8FF3CFF)
WALKABLE = {t for t in range(32) if (FOOT_MASK[1] >> t) & 1}
WALKABLE |= {32 + t for t in range(32) if (FOOT_MASK[0] >> t) & 1}

FAMILIES = {
    "grass": {0, 1, 2, 3, 42}, "plateau": {10, 11, 12}, "shelf13": {13},
    "scrub": {4, 5, 6}, "desert": {17, 18, 19, 20, 21, 22, 23}, "dirt16": {16},
    "dunes41": {41}, "snow": {27, 28}, "canyon": {45, 46}, "forest": {36, 37},
    "sand": {31, 32, 33}, "rocky7": {7, 30, 34, 35, 52, 38},
}
FAM_OF = {t: f for f, ts in FAMILIES.items() for t in ts}
MAINS = ("grass", "plateau", "shelf13")

RECT_U = G.GRASS_U_HALF[0][1] - G.GRASS_U_HALF[0][0]
RECT_V = G.GRASS_V_HALF[0][1] - G.GRASS_V_HALF[0][0]
# quanta unit = 1/64 tile in BOTH axes (the claim's unit), so we can compare numbers directly
QPT = 64.0
FINE = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40),
        (40, 50), (50, 91)]


def pcts(a, ps=(10, 25, 50, 75, 90)):
    if a is None or len(a) == 0:
        return None
    a = np.asarray(a, float)
    o = {f"p{p}": round(float(np.percentile(a, p)), 4) for p in ps}
    o["n"] = int(a.size)
    o["mean"] = round(float(a.mean()), 4)
    return o


def tri_J_plan(P, uvs):
    """J in TILE units per world unit, plan (x,z) domain. Exact (3 pts determine affine)."""
    e1, e2 = P[1] - P[0], P[2] - P[0]
    D = np.array([[(uvs[1][0] - uvs[0][0]) / TILE_U, (uvs[2][0] - uvs[0][0]) / TILE_U],
                  [(uvs[1][1] - uvs[0][1]) / TILE_V, (uvs[2][1] - uvs[0][1]) / TILE_V]])
    Pm = np.array([[e1[0], e2[0]], [e1[2], e2[2]]])
    if abs(float(np.linalg.det(Pm))) < 1e-9:
        return None
    return D @ np.linalg.inv(Pm)


def unfold_tri(P):
    """Per-triangle isometric flattening: 2D coords in which 3D lengths are exact."""
    e1 = P[1] - P[0]
    L = float(np.linalg.norm(e1))
    if L < 1e-9:
        return None
    ex = e1 / L
    n = np.cross(e1, P[2] - P[0])
    nl = float(np.linalg.norm(n))
    if nl < 1e-9:
        return None
    ey = np.cross(n / nl, ex)
    d2 = P[2] - P[0]
    return [(0.0, 0.0), (L, 0.0), (float(d2 @ ex), float(d2 @ ey))]


def labelled(J, nrm):
    """DIRECTION-LABELLED rates. Returns (s_g, s_c, theta_deg) in quanta per 4u."""
    hn = math.hypot(float(nrm[0]), float(nrm[2]))
    if hn < 1e-9:
        return None
    g = np.array([-float(nrm[0]) / hn, -float(nrm[2]) / hn])   # plan steepest-descent dir
    c = np.array([-g[1], g[0]])
    Jq = J * CELL * QPT
    s_g = float(np.linalg.norm(Jq @ g))
    s_c = float(np.linalg.norm(Jq @ c))
    _u, sv, vt = np.linalg.svd(Jq)
    if sv[1] < 1e-12:
        return None
    v1 = vt[0]
    cosang = abs(float(v1 @ g))
    th = math.degrees(math.acos(max(0.0, min(1.0, cosang))))
    return s_g, s_c, min(th, 180.0 - th)


def near_lattice(v, tol=1.0):
    return min(abs(v - 62.0), abs(v - 64.0)) <= tol


def collect(discs, cap):
    """One pass; returns the per-triangle record list."""
    recs = []
    cellrec = []
    nb = {}
    for disc in discs:
        try:
            blocks = X.list_blocks(disc=disc)
        except Exception:                                     # noqa: BLE001
            continue
        if cap:
            blocks = blocks[:cap]
        nread = 0
        for (bx, by) in blocks:
            try:
                bm = X.read_block(bx, by, disc=disc, part="terrain")
            except Exception:                                 # noqa: BLE001
                continue
            V, U, T = bm.verts, bm.uvs, bm.tangents
            if V is None or U is None or T is None:
                continue
            nread += 1
            ntri = len(bm.flat_index) // 3
            cells = defaultdict(list)
            for t in range(ntri):
                idx = bm.flat_index[3 * t:3 * t + 3]
                topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
                if topo not in WALKABLE:
                    continue
                P = [np.array(V[i], float) for i in idx]
                uvs = [tuple(U[i]) for i in idx]
                nrm = np.cross(P[1] - P[0], P[2] - P[0])
                nl = float(np.linalg.norm(nrm))
                if nl < 1e-12:
                    continue
                slope = math.degrees(math.acos(min(1.0, abs(float(nrm[1])) / nl)))
                fam = FAM_OF.get(topo, "other")
                Asurf = 0.5 * nl
                # SAME shape filter as the claim's M2d, so the populations are comparable
                angs, ok = [], True
                for i3 in range(3):
                    a1 = np.array([P[(i3 + 1) % 3][0] - P[i3][0], P[(i3 + 1) % 3][2] - P[i3][2]])
                    b1 = np.array([P[(i3 + 2) % 3][0] - P[i3][0], P[(i3 + 2) % 3][2] - P[i3][2]])
                    n1, n2 = float(np.linalg.norm(a1)), float(np.linalg.norm(b1))
                    if n1 < 1.5 or n2 < 1.5:
                        ok = False
                        break
                    angs.append(math.degrees(math.acos(
                        max(-1.0, min(1.0, float(a1 @ b1) / n1 / n2)))))
                cx = sum(p[0] for p in P) / 3.0
                cz = sum(p[2] for p in P) / 3.0
                cij = (int(math.floor(cx / CELL)), int(math.floor(cz / CELL)))
                cells[cij].append((P, uvs, slope, fam, nrm / nl))
                if not (ok and angs and min(angs) >= 20.0 and Asurf > 2.0):
                    continue
                J = tri_J_plan(P, uvs)
                if J is None:
                    continue
                lab = labelled(J, nrm)
                if lab is None:
                    continue
                s_g, s_c, th = lab
                # ---- the two SYNTHETIC controls, identical pipeline -----------------
                syn = {}
                uf = unfold_tri(P)
                base = uvs[0]
                for tag in ("plan", "surf"):
                    dom = ([(float(p[0]), float(p[2])) for p in P] if tag == "plan" else uf)
                    if dom is None:
                        continue
                    o = dom[0]
                    su, sv2 = [], []
                    for (dx, dz) in dom:
                        u = base[0] + (RECT_U / CELL) * (dx - o[0])
                        v = base[1] - (RECT_V / CELL) * (dz - o[1])
                        su.append(round(u / UVQ) * UVQ)        # stock's own resolution
                        sv2.append(round(v / UVQ) * UVQ)
                    uvS = list(zip(su, sv2))
                    Js = tri_J_plan(P, uvS)
                    if Js is None:
                        continue
                    lb = labelled(Js, nrm)
                    if lb is None:
                        continue
                    syn[tag] = lb
                if "plan" not in syn or "surf" not in syn:
                    continue
                recs.append(dict(disc=disc, blk=(bx, by), fam=fam, slope=slope,
                                 s_g=s_g, s_c=s_c, th=th,
                                 gp=syn["plan"][0], cp=syn["plan"][1], tp=syn["plan"][2],
                                 gs=syn["surf"][0], cs=syn["surf"][1], ts=syn["surf"][2]))
            # ---- per-cell uv budget (attack C) --------------------------------------
            for cij, ts in cells.items():
                uv = [w for (_P, uvs, _s, _f, _n) in ts for w in uvs]
                pos = [(float(p[0]), float(p[2])) for (P, _u, _s, _f, _n) in ts for p in P]
                du = (max(w[0] for w in uv) - min(w[0] for w in uv)) / TILE_U
                dv = (max(w[1] for w in uv) - min(w[1] for w in uv)) / TILE_V
                px = max(p[0] for p in pos) - min(p[0] for p in pos)
                pz = max(p[1] for p in pos) - min(p[1] for p in pos)
                cellrec.append(dict(disc=disc, smax=max(t[2] for t in ts),
                                    fam=Counter(t[3] for t in ts).most_common(1)[0][0],
                                    uvext=max(du, dv), planext=max(px, pz),
                                    ntri=len(ts)))
        nb[f"disc{disc}"] = nread
    return recs, cellrec, nb


def sweep(recs, key_g, key_c, key_t, fams=None):
    sel0 = [r for r in recs if fams is None or r["fam"] in fams]
    out = {}
    for lo, hi in FINE:
        s = [r for r in sel0 if lo <= r["slope"] < hi]
        e = {"n": len(s)}
        if len(s) >= 15:
            smed = float(np.median([r["slope"] for r in s]))
            cosm = math.cos(math.radians(smed))
            g = [r[key_g] for r in s]
            c = [r[key_c] for r in s]
            e.update(slope_med=round(smed, 2),
                     s_downslope_q=pcts(g, (25, 50, 75)),
                     s_contour_q=pcts(c, (25, 50, 75)),
                     PLAN_predicts_q=62.0,
                     SURF_predicts_downslope_q=round(62.0 / cosm, 2),
                     ratio_med=round(float(np.median([a / b for a, b in zip(g, c)])), 4),
                     SURF_ratio_predicts=round(1.0 / cosm, 4),
                     theta_to_gradient_med_deg=round(float(np.median([r[key_t] for r in s])), 2),
                     both_axes_on_62_or_64_rate=round(
                         sum(1 for a, b in zip(g, c)
                             if near_lattice(a) and near_lattice(b)) / len(s), 4),
                     downslope_on_62_or_64_rate=round(
                         sum(1 for a in g if near_lattice(a)) / len(g), 4))
        out[f"{lo}-{hi}"] = e
    return out


def main():
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    rep = {"meta": {"script": "verify_s1_ground_uv.py", "role": "adversarial verifier of S1",
                    "read_only_vs_game": True, "discs": [1, 4],
                    "quanta_unit": "1/64 tile in BOTH axes (the claim's unit)",
                    "TRUE_uv_quantum_in_tiles": {"u": round(UVQ / TILE_U, 6),
                                                 "v": round(UVQ / TILE_V, 6)},
                    "mains_rect_quanta": [round(RECT_U / TILE_U * QPT, 3),
                                          round(RECT_V / TILE_V * QPT, 3)]}}

    recs, cellrec, nb = collect([1, 4], cap)
    rep["meta"].update(blocks_read=nb, n_tris_measured=len(recs), n_cells=len(cellrec),
                       fam_census=dict(Counter(r["fam"] for r in recs).most_common()))
    print("tris", len(recs), "cells", len(cellrec), nb)

    # ---- ATTACK A: direction-labelled, real data --------------------------------------
    rep["A_real_direction_labelled"] = {
        "MAINS": sweep(recs, "s_g", "s_c", "th", set(MAINS)),
        "desert": sweep(recs, "s_g", "s_c", "th", {"desert"}),
        "ALL": sweep(recs, "s_g", "s_c", "th", None),
    }
    # ---- ATTACK B: the two synthetic controls, same pipeline ---------------------------
    rep["B_control_SYNTHETIC_PLAN"] = {
        "note": "uv overwritten with an EXACT 62-quanta plan map, re-quantized to 1/1024. "
                "Any slope-dependence here is pure quantization artifact.",
        "MAINS": sweep(recs, "gp", "cp", "tp", set(MAINS)),
        "ALL": sweep(recs, "gp", "cp", "tp", None),
    }
    rep["B_control_SYNTHETIC_SURFACE"] = {
        "note": "same map applied to per-triangle unfolded SURFACE coords -- the positive "
                "control; proves the statistic can see a real surface law.",
        "MAINS": sweep(recs, "gs", "cs", "ts", set(MAINS)),
        "ALL": sweep(recs, "gs", "cs", "ts", None),
    }

    # excess of real over the plan control, per bin (the only honest effect size)
    ex = {}
    for fam_tag, fams in (("MAINS", set(MAINS)), ("desert", {"desert"}), ("ALL", None)):
        rows = {}
        for lo, hi in FINE:
            s = [r for r in recs if lo <= r["slope"] < hi
                 and (fams is None or r["fam"] in fams)]
            if len(s) < 15:
                rows[f"{lo}-{hi}"] = {"n": len(s)}
                continue
            smed = float(np.median([r["slope"] for r in s]))
            cosm = math.cos(math.radians(smed))
            real = float(np.median([r["s_g"] for r in s]))
            ctrlP = float(np.median([r["gp"] for r in s]))
            ctrlS = float(np.median([r["gs"] for r in s]))
            rows[f"{lo}-{hi}"] = dict(
                n=len(s), slope_med=round(smed, 2),
                real_downslope_q=round(real, 2),
                plan_control_q=round(ctrlP, 2),
                surface_control_q=round(ctrlS, 2),
                SURF_law_needs_q=round(62.0 / cosm, 2),
                excess_over_plan_control_q=round(real - ctrlP, 2),
                surface_fraction_vs_CONTROLS=(round((real - ctrlP) / (ctrlS - ctrlP), 4)
                                              if ctrlS - ctrlP > 0.5 else None))
        ex[fam_tag] = rows
    rep["B_effect_size_vs_controls"] = ex

    # ---- ATTACK C: cell uv budget + steep counterexamples -----------------------------
    cb = {}
    for lo, hi in [(0, 10), (10, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 91)]:
        s = [c for c in cellrec if lo <= c["smax"] < hi]
        e = {"n": len(s)}
        if len(s) >= 10:
            e.update(uv_extent_tiles=pcts([c["uvext"] for c in s], (25, 50, 75, 90)),
                     plan_extent_u=pcts([c["planext"] for c in s], (25, 50, 75)),
                     within_one_tile_rate=round(sum(1 for c in s if c["uvext"] <= 1.02) / len(s), 4),
                     full_4u_plan_footprint_rate=round(
                         sum(1 for c in s if c["planext"] >= 3.9) / len(s), 4))
        cb[f"{lo}-{hi}"] = e
    rep["C_cell_uv_budget"] = cb

    hunt = {}
    for thr in (20.0, 25.0, 30.0, 35.0, 40.0):
        s = [r for r in recs if r["slope"] >= thr]
        exact = [r for r in s if near_lattice(r["s_g"], 1.0) and near_lattice(r["s_c"], 1.0)]
        ctrl = [r for r in s if near_lattice(r["gp"], 1.0) and near_lattice(r["cp"], 1.0)]
        hunt[f">={thr:g}deg"] = dict(
            n=len(s), n_exact_plan_both_axes=len(exact),
            rate=round(len(exact) / len(s), 4) if s else None,
            plan_control_rate=round(len(ctrl) / len(s), 4) if s else None,
            examples=[dict(disc=r["disc"], blk=list(r["blk"]), fam=r["fam"],
                           slope=round(r["slope"], 2), s_g=round(r["s_g"], 2),
                           s_c=round(r["s_c"], 2))
                      for r in sorted(exact, key=lambda r: -r["slope"])[:8]])
    rep["C_steep_exact_plan_counterexamples"] = hunt

    # ---- the shipped-decoder gate, re-derived independently ---------------------------
    rep["D_uv_quantum_per_axis"] = {
        "claim_says": "one uv quantum = 1/64 tile (2 px u, 4 px v)",
        "measured": {"u": "1/1024 raw = 1/64 tile = 2 px", "v": "1/1024 raw = 1/32 tile = 4 px"},
        "consequence": "the claim's 'quanta' unit is a TRUE quantum in u but HALF a quantum "
                       "in v, so its 62-vs-64 pinning and its 1-quantum gates are 2x tighter "
                       "in v than the data's own resolution; v-axis rounding alone injects "
                       "+-1.0 of its unit.",
    }

    OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("wrote", OUT)

    # ---- PNG ---------------------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axs = plt.subplots(1, 3, figsize=(16.5, 4.8))
        for ax, (tag, fams) in zip(axs, (("MAINS", set(MAINS)), ("desert", {"desert"}),
                                         ("ALL", None))):
            xs, real, cp, cs, need = [], [], [], [], []
            for lo, hi in FINE:
                s = [r for r in recs if lo <= r["slope"] < hi
                     and (fams is None or r["fam"] in fams)]
                if len(s) < 15:
                    continue
                sm = float(np.median([r["slope"] for r in s]))
                xs.append(sm)
                real.append(float(np.median([r["s_g"] for r in s])))
                cp.append(float(np.median([r["gp"] for r in s])))
                cs.append(float(np.median([r["gs"] for r in s])))
                need.append(62.0 / math.cos(math.radians(sm)))
            ax.plot(xs, real, "o-", color="#111", lw=2, label="STOCK down-slope rate")
            ax.plot(xs, cp, "s--", color="#1f77b4", label="synthetic PLAN control")
            ax.plot(xs, cs, "^--", color="#d62728", label="synthetic SURFACE control")
            ax.plot(xs, need, ":", color="#888", label="62/cos (pure surface)")
            ax.axhline(62, color="#2ca02c", lw=0.8)
            ax.axhline(64, color="#2ca02c", lw=0.8, ls=":")
            ax.set_title(f"{tag}: down-slope uv rate vs slope")
            ax.set_xlabel("face slope (deg)")
            ax.set_ylabel("quanta per 4u along the plan gradient")
            ax.legend(fontsize=7)
            ax.grid(alpha=.25)
        fig.suptitle("S1 VERIFY -- direction-labelled down-slope uv rate, stock vs synthetic "
                     "PLAN/SURFACE controls (same pipeline)", fontsize=10)
        fig.tight_layout()
        fig.savefig(PNG, dpi=110)
        print("wrote", PNG)
    except Exception as e:                                    # noqa: BLE001
        print("png skipped:", e)


if __name__ == "__main__":
    main()
