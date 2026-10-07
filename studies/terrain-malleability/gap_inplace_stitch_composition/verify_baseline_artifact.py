"""VERIFIER (adversarial) [generalised: env VB_AMOUNTS=1,3,-3 VB_ALL=1 VB_OUT=name] -- is the S7 "origin-shift" wall class (A=+1, Object seams) a BOUNDARY-LINE artifact?

verify_object_walls.py found every A=+1 topo-59 wall has its target probe on the base line of a VERTICAL Object
tri. Here, for every such wall (same plan/instrument as tear_sweep.py, A=+1, R 8/16/24), the target is nudged
+-EPS across the vertical face (along the face's horizontal normal) and the same start->target step is re-run
before and after the edit. If the after-edit verdict equals the stock verdict on BOTH nudged points, the
introduced wall lives only on the zero-width base line (no walkable area changes) -- an instrument artifact.
Writes out/verify_baseline_artifact.json.   Run: py <this file>
"""
from __future__ import annotations

import json
import os
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
import tear_sweep as T                                 # noqa: E402
from ff9mapkit.world import placement as P             # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402

EPS = (0.02, 0.1)


def main():
    M = S.load_disc(1)
    blocks = T.build_world(M)
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    tri_at = defaultdict(lambda: defaultdict(list))
    for (x, y), parts in blocks.items():
        for p, m in parts.items():
            for t in range(m.ntri):
                for k in range(3):
                    tri_at[(x, y)][m.lv[m.fi[3 * t + k]]].append((p, t))
    welds = {}
    for (x, y), parts in blocks.items():
        if "terrain" not in parts:
            continue
        w = {}
        for lp, wp in zip(parts["terrain"].lv, parts["terrain"].wv):
            if lp not in w:
                o = owners[S.wrap_key(wp)] - {(x, y, "terrain")}
                if o:
                    w[lp] = sorted(o)
        welds[(x, y)] = w
    plan = []
    PARTN = set(os.environ.get("VB_PARTNER", "object").split(","))
    for b in sorted({(x, y) for (x, y, p) in M if p in PARTN}):
        cells = defaultdict(list)
        for lp, others in welds[b].items():
            if any(o[2] in PARTN for o in others):
                cells[(math.floor((lp[0] + b[0] * 64) / 16), math.floor((lp[2] - b[1] * 64) / 16))].append(
                    (lp[0] + b[0] * 64, lp[2] - b[1] * 64))
        for c, pts in sorted(cells.items()):
            mx = sum(p[0] for p in pts) / len(pts); mz = sum(p[1] for p in pts) / len(pts)
            plan.append((b, min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - mz) ** 2)))
    base, stats, ex = {}, Counter(), []
    edits_any, edits_area = defaultdict(set), defaultdict(set)
    AS = [float(a) for a in os.environ.get("VB_AMOUNTS", "1").split(",")]
    for A in AS:
     for (b0, (cx, cz)) in plan:
        for R in (8.0, 16.0, 24.0):
            bx0, bx1 = math.floor((cx - R) / 64), math.floor((cx + R) / 64)
            by0, by1 = math.floor(-(cz + R) / 64), math.floor(-(cz - R) / 64)
            for blk in [(bx, by) for bx in range(bx0, bx1 + 1) for by in range(by0, by1 + 1)
                        if 0 <= bx < 24 and 0 <= by < 20 and (bx, by) in welds]:
                ox, oz = blk[0] * 64, -blk[1] * 64
                ter = blocks[blk]["terrain"]
                wt = {lp: _falloff(math.hypot(lp[0] + ox - cx, lp[2] + oz - cz) / R, "smooth") for lp in set(ter.lv)}
                mla = None
                for lp, others in welds[blk].items():
                    if abs(A * wt.get(lp, 0.0)) <= S.TOL or not any(o[2] in PARTN for o in others):
                        continue
                    if blk not in base:
                        ml = T.meshlist_for(blocks, blk)
                        base[blk] = (ml, P.build_meshlist_index(ml))
                    if mla is None:
                        mla = T.meshlist_for(blocks, blk, [(v[0], v[1] + A * wt.get(v, 0.0), v[2]) for v in ter.lv])
                    mlb, idx = base[blk]
                    probes = []
                    for (p, t) in tri_at[blk][lp]:
                        m = blocks[blk][p]
                        cs = [m.lv[m.fi[3 * t + k]] for k in range(3)]
                        gx, gz = sum(q[0] for q in cs) / 3 - lp[0], sum(q[2] for q in cs) / 3 - lp[2]
                        L = math.hypot(gx, gz)
                        if L > 1e-6:
                            probes.append((p, cs, (lp[0] + T.PROBE * gx / L, lp[2] + T.PROBE * gz / L)))
                    for (pa, csa, Ap) in probes:
                        for (pb, csb, Bp) in probes:
                            if pa == pb or "terrain" not in (pa, pb) or {pa, pb} - ({"terrain"} | PARTN):
                                continue
                            bef, _ = T.crossing(mlb, idx, Ap, mlb, idx, Bp)
                            aft, da = T.crossing(mla, idx, Ap, mla, idx, Bp)
                            if not (bef and aft is False and (os.environ.get("VB_ALL") or da.startswith("unwalkable topo 59"))):
                                continue
                            # horizontal normal of the target tri's plane (vertical tri -> its XZ line normal)
                            u = [csb[1][i] - csb[0][i] for i in range(3)]
                            v = [csb[2][i] - csb[0][i] for i in range(3)]
                            n = (u[1] * v[2] - u[2] * v[1], u[0] * v[1] - u[1] * v[0])   # (nx, nz)
                            L = math.hypot(*n) or 1.0
                            n = (n[0] / L, n[1] / L)
                            verdict = []
                            for e in EPS:
                                for sgn in (1, -1):
                                    Bq = (Bp[0] + sgn * e * n[0], Bp[1] + sgn * e * n[1])
                                    b2, _ = T.crossing(mlb, idx, Ap, mlb, idx, Bq)
                                    a2, _ = T.crossing(mla, idx, Ap, mla, idx, Bq)
                                    verdict.append((e, sgn, bool(b2), bool(a2)))
                            changed = [v for v in verdict if v[2] != v[3]]
                            cls = "LINE-ONLY (no nudged point changes)" if not changed else \
                                f"AREA (changes at nudge {sorted({(c[0], c[1]) for c in changed})})"
                            vt = abs((csb[1][0]-csb[0][0])*(csb[2][2]-csb[0][2])-(csb[2][0]-csb[0][0])*(csb[1][2]-csb[0][2])) < 2e-6
                            stats[(f"A{A:+g}", pa + "->" + pb, "target VERTICAL" if vt else "target has area", da.split("(")[0], cls)] += 1
                            edits_any[(A, R)].add((b0, cx, cz))
                            if cls.startswith('AREA'):
                                edits_area[(A, R)].add((b0, cx, cz))
                            if len(ex) < 8:
                                ex.append({"blk": blk, "R": R, "target": Bp, "verdicts(eps,side,stock_legal,after_legal)": verdict})
    print("A=+1 topo-59 origin-shift walls, nudged +-0.02/+-0.1u across the target face:")
    for k, v in stats.most_common():
        print(f"   {v:5d}  {k}")
    per_edit = {f"A{a:+g} R{r:g}": {"edits_with_wall": len(edits_any[(a, r)]), "edits_with_AREA_wall": len(edits_area[(a, r)])} for (a, r) in sorted(edits_any)}
    print("per (A,R) edits with >=1 wall / with >=1 AREA (non-line) wall:", per_edit)
    p = S.OUT / os.environ.get("VB_OUT", "verify_baseline_artifact.json")
    p.write_text(json.dumps({"per_edit": per_edit, "classes": [[list(k) if isinstance(k, tuple) else k, v] for k, v in stats.items()], "examples": ex}, indent=1, default=str), encoding="utf-8")
    print("->", p)


if __name__ == "__main__":
    main()
