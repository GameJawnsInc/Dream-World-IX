"""S1 VERIFY, pass 2 -- the calibrated per-triangle verdict, the representativeness check,
and an independent re-derivation of the claim's decoder-gate surprise.

Pass 1 (verify_s1_ground_uv.py) replaced the claim's UNLABELLED SVD singular values with
direction-labelled rates and added two synthetic controls. Pass 2 removes the last
mixture-median confound and tests the claim's thin high-slope evidence:

  E. PER-TRIANGLE 3-WAY CLASSIFICATION, calibrated by the same two controls.
     Statistic: r = s_downslope / s_contour. It is window-INDEPENDENT (both axes carry the
     same window), so it cannot be moved by the 62-vs-64 window mixture that a median over
     s_downslope alone is moved by. PLAN predicts r = the window aspect (1, 64/62 or 62/64);
     SURFACE predicts r = aspect / cos(slope). Per triangle, classify PLAN / SURFACE /
     UNDECIDED with a 2% log margin. The synthetic controls give the confusion matrix, so
     the real rates are read against a measured floor and ceiling, not against 0/1.

  F. REPRESENTATIVENESS. The claim's mains verdict above 25 deg rests on n=20-81 triangles.
     Count the DISTINCT blocks and topographs behind every steep bin, and the share coming
     from the single largest contributing block. A law carried by one block is a block, not
     a law.

  G. THE DECODER-GATE SURPRISE, re-derived on a different sample (every 3rd disc-1 block +
     every 3rd disc-4 block): locked-rect decode rate at DECODE_ERR=1e-4 vs at one true uv
     quantum. Partial credit is real; this one is checkable cheaply.

Read-only vs stock. Artifact -> out/verify_s1_ground_uv_axis.json
Run: py -X utf8 verify_s1_ground_uv_axis.py
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
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X                     # noqa: E402
from ff9mapkit.world import grassland as G                   # noqa: E402
from verify_s1_ground_uv import (CELL, FAM_OF, MAINS, TILE_U, TILE_V, UVQ,  # noqa: E402
                                WALKABLE, collect)

OUT = HERE / "out" / "verify_s1_ground_uv_axis.json"
MARGIN = math.log(1.02)                                      # 2% -- generous to both models
BINS = [(10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 55)]
ASPECTS = (1.0, 64.0 / 62.0, 62.0 / 64.0)


def classify(r, slope):
    """PLAN / SURFACE / UNDECIDED for one triangle, window-independent."""
    c = math.cos(math.radians(slope))
    dp = min(abs(math.log(r / a)) for a in ASPECTS)
    ds = min(abs(math.log(r * c / a)) for a in ASPECTS)
    if dp + MARGIN < ds:
        return "PLAN"
    if ds + MARGIN < dp:
        return "SURFACE"
    return "UNDECIDED"


def table(recs, gk, ck, fams):
    out = {}
    for lo, hi in BINS:
        s = [r for r in recs if lo <= r["slope"] < hi and (fams is None or r["fam"] in fams)]
        e = {"n": len(s)}
        if len(s) >= 15:
            cts = Counter(classify(r[gk] / r[ck], r["slope"]) for r in s if r[ck] > 1e-9)
            tot = sum(cts.values())
            e.update(slope_med=round(float(np.median([r["slope"] for r in s])), 2),
                     PLAN=round(cts["PLAN"] / tot, 4), SURFACE=round(cts["SURFACE"] / tot, 4),
                     UNDECIDED=round(cts["UNDECIDED"] / tot, 4), n_classified=tot)
        out[f"{lo}-{hi}"] = e
    return out


def main():
    rep = {"meta": {"script": "verify_s1_ground_uv_axis.py", "pass": 2,
                    "statistic": "r = s_downslope / s_contour (window-independent)",
                    "margin_pct": 2.0, "read_only_vs_game": True}}
    recs, _cells, nb = collect([1, 4], 0)
    rep["meta"]["blocks_read"] = nb
    rep["meta"]["n_tris"] = len(recs)
    print("tris", len(recs))

    # ---- E: calibrated per-triangle classification ------------------------------------
    E = {}
    for tag, fams in (("MAINS", set(MAINS)), ("grass", {"grass"}), ("plateau", {"plateau"}),
                      ("desert", {"desert"}), ("ALL", None)):
        E[tag] = {
            "STOCK": table(recs, "s_g", "s_c", fams),
            "control_SYNTHETIC_PLAN": table(recs, "gp", "cp", fams),
            "control_SYNTHETIC_SURFACE": table(recs, "gs", "cs", fams),
        }
    rep["E_per_triangle_classification"] = E

    # ---- F: representativeness of every steep bin -------------------------------------
    F = {}
    for tag, fams in (("MAINS", set(MAINS)), ("desert", {"desert"}), ("ALL", None)):
        rows = {}
        for lo, hi in BINS:
            s = [r for r in recs if lo <= r["slope"] < hi
                 and (fams is None or r["fam"] in fams)]
            if not s:
                rows[f"{lo}-{hi}"] = {"n": 0}
                continue
            bc = Counter((r["disc"], r["blk"]) for r in s)
            top = bc.most_common(3)
            rows[f"{lo}-{hi}"] = dict(
                n=len(s), n_distinct_blocks=len(bc),
                top_block_share=round(top[0][1] / len(s), 4),
                top3=[[f"d{k[0]}:{k[1][0]},{k[1][1]}", v] for k, v in top],
                fams=dict(Counter(r["fam"] for r in s).most_common(4)))
        F[tag] = rows
    rep["F_representativeness"] = F

    # ---- G: the decoder-gate surprise, different sample --------------------------------
    GROUND_REGION = {g: G.ground_main_region(g) for g in G.GROUNDS}
    n_cell = hit_q = hit_e = 0
    outside = 0
    for disc in (1, 4):
        try:
            blocks = X.list_blocks(disc=disc)[::3]
        except Exception:                                     # noqa: BLE001
            continue
        for (bx, by) in blocks:
            try:
                bm = X.read_block(bx, by, disc=disc, part="terrain")
            except Exception:                                 # noqa: BLE001
                continue
            V, U, T = bm.verts, bm.uvs, bm.tangents
            if V is None:
                continue
            cells = defaultdict(list)
            for t in range(len(bm.flat_index) // 3):
                idx = bm.flat_index[3 * t:3 * t + 3]
                topo = X.decode_id(int(round(T[idx[0]][0])))["topograph"]
                if topo not in WALKABLE:
                    continue
                P = [np.array(V[i], float) for i in idx]
                cx = sum(p[0] for p in P) / 3.0
                cz = sum(p[2] for p in P) / 3.0
                cells[(int(math.floor(cx / CELL)), int(math.floor(cz / CELL)))].append(
                    [(float(p[0]), float(p[2])) for p in P] + [tuple(U[i]) for i in idx])
            for cij, ts in cells.items():
                pos = [x for row in ts for x in row[:3]]
                uv = [x for row in ts for x in row[3:]]
                mu = sum(w[0] for w in uv) / len(uv)
                mv = sum(w[1] for w in uv) / len(uv)
                cand = [g for g, (u0, v0, u1, v1) in GROUND_REGION.items()
                        if u0 - 0.004 <= mu <= u1 + 0.004 and v0 - 0.004 <= mv <= v1 + 0.004]
                if not cand:
                    outside += 1
                    continue
                n_cell += 1
                best = 9e9
                for gname in cand:
                    for uh in (0, 1):
                        for vh in (0, 1):
                            for ori in G.ORIS:
                                m = 0.0
                                for (vx, vz), (su, sv) in zip(pos, uv):
                                    a, b = G.ground_uv(vx, vz, cij, (uh, vh), ori, gname)
                                    m = max(m, abs(a - su), abs(b - sv))
                                    if m >= best:
                                        break
                                best = min(best, m)
                if best < 1e-4:
                    hit_e += 1
                if best < UVQ:
                    hit_q += 1
    rep["G_decoder_gate"] = dict(
        sample="every 3rd disc-1 + every 3rd disc-4 block",
        n_cells_inside_a_GROUNDS_region=n_cell, n_cells_outside_every_region=outside,
        rate_at_shipped_DECODE_ERR_1e_4=round(hit_e / n_cell, 4) if n_cell else None,
        rate_at_one_true_uv_quantum=round(hit_q / n_cell, 4) if n_cell else None,
        claim_says={"at_1e_4": 0.0669, "at_one_quantum": 0.1208})

    OUT.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("wrote", OUT)
    for tag in ("MAINS", "desert"):
        print("\n==", tag)
        for b in E[tag]["STOCK"]:
            s = E[tag]["STOCK"][b]
            cp = E[tag]["control_SYNTHETIC_PLAN"][b]
            cs = E[tag]["control_SYNTHETIC_SURFACE"][b]
            if "PLAN" not in s:
                print(f"  {b:7s} n={s['n']}")
                continue
            print(f"  {b:7s} n={s['n']:5d} sl={s['slope_med']:5.1f} | STOCK P/S/U "
                  f"{s['PLAN']:.3f}/{s['SURFACE']:.3f}/{s['UNDECIDED']:.3f} | ctrlPLAN "
                  f"{cp['PLAN']:.3f}/{cp['SURFACE']:.3f} | ctrlSURF "
                  f"{cs['PLAN']:.3f}/{cs['SURFACE']:.3f}")
    print(json.dumps(rep["G_decoder_gate"], indent=1))


if __name__ == "__main__":
    main()
