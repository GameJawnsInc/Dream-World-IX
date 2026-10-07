"""How often does an ARBITRARY world-terrain edit on real land tear a stock stitch? (disc 1 and disc 4, 0_1)

Sample every land block on a 4u lattice (cell centres). For a radial edit of radius R and amount A centred
there (smooth falloff, mesh._falloff), the edit tears iff some Terrain position welded to a NON-Terrain part lies
where |A * falloff(d/R)| > 0.05. Reported per (A, R): the fraction of land samples whose edit tears ANY weld,
tears a WALKABLE-partner weld (Beach1/Beach2/Object), and moves an entrance (event!=0) tri. These fractions are
the chance that a world-terrain edit dropped at a random land spot needs the kit changes ranked in NOTES.md.
Writes out/tear_exposure.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/tear_exposure.py
"""
from __future__ import annotations

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402
from ff9mapkit.world.mesh import _falloff              # noqa: E402

AMOUNTS = (1.0, 3.0, 6.0)
RADII = (8.0, 16.0, 24.0, 48.0, 96.0)       # 96 = world-deploy's --radius default (cli.py world-deploy parser)
WALKP = {"beach1", "beach2", "object"}


def tmax(A):
    """largest t=d/R with |A*falloff(t)| > 0.05 (bisection on the monotone smooth falloff)."""
    lo, hi = 0.0, 1.0
    if abs(A) * _falloff(0.0) <= S.TOL:
        return 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if abs(A) * _falloff(mid) > S.TOL:
            lo = mid
        else:
            hi = mid
    return lo


def run(disc):
    M = S.load_disc(disc)
    owners = defaultdict(set)
    for k, m in M.items():
        for p in m.wv:
            owners[S.wrap_key(p)].add(k)
    weld_any, weld_walk, ent = [], [], []
    for (x, y, p), m in M.items():
        if p != "terrain":
            continue
        seen = set()
        for wp in m.wv:
            if wp in seen:
                continue
            seen.add(wp)
            o = {q[2] for q in owners[S.wrap_key(wp)]} - {"terrain"}
            if o:
                weld_any.append((wp[0], wp[2]))
                if o & WALKP:
                    weld_walk.append((wp[0], wp[2]))
        for t in range(m.ntri):
            if S.event(m.tri_idall(t)):
                for k in range(3):
                    v = m.wv[m.fi[3 * t + k]]
                    ent.append((v[0], v[2]))

    def grid(pts, cell=16.0):
        g = defaultdict(list)
        for p in pts:
            g[(math.floor(p[0] / cell), math.floor(p[1] / cell))].append(p)
        return g
    G = {"any": grid(weld_any), "walk": grid(weld_walk), "ent": grid(ent)}

    def near(g, x, z, r):
        c = 16.0
        for gx in range(math.floor((x - r) / c), math.floor((x + r) / c) + 1):
            for gz in range(math.floor((z - r) / c), math.floor((z + r) / c) + 1):
                for (px, pz) in g.get((gx, gz), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 < r * r:
                        return True
        return False
    samples = []
    for (x, y, p) in M:
        if p != "terrain":
            continue
        for i in range(16):
            for j in range(16):
                samples.append((x * 64 + 2 + 4 * i, -(y * 64 + 2 + 4 * j)))
    out = {"land_samples": len(samples), "welded_nonterrain_positions": len(weld_any),
           "walkable_partner_positions": len(weld_walk)}
    for A in AMOUNTS:
        tm = tmax(A)
        for R in RADII:
            r = tm * R
            n_any = sum(1 for (x, z) in samples if near(G["any"], x, z, r))
            n_walk = sum(1 for (x, z) in samples if near(G["walk"], x, z, r))
            n_ent = sum(1 for (x, z) in samples if near(G["ent"], x, z, r))
            out[f"A{A:g}_R{R:g}"] = {"tear_reach": round(r, 2), "frac_tears_any": round(n_any / len(samples), 4),
                                     "frac_tears_walkable": round(n_walk / len(samples), 4),
                                     "frac_moves_entrance": round(n_ent / len(samples), 4)}
            print(f"disc {disc} A {A:g} R {R:g} (tear reach {r:.1f}u): tears any {n_any / len(samples):.1%}, "
                  f"walkable-partner {n_walk / len(samples):.1%}, entrance {n_ent / len(samples):.1%}")
    return out


res = {f"disc{d}": run(d) for d in (1, 4)}
p = S.save_json("tear_exposure.json", res)
print("->", p)
