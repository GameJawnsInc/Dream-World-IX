"""Hairline seams in the rot-mountain lab: where can the sea show through the grass?

The owner, watching round 16 live: "a small seam in the grass ... some 1-pixel seams as well". A 1-pixel seam
on ground is a crack the rasterizer leaves between two surfaces that do not share an edge exactly:
  OPEN   an edge used by ONE Terrain tri (by position, kk3), away from the island's coast foot (y > 0.5)
  TJ     a vertex lying inside another tri's edge (3D, < 2e-3) without splitting it: watertight in exact
         arithmetic, a crack under float32 (meshedit.find_tjunctions's law, in 3D and over block borders)
Run over the bare island and each carve (A rot 0, B rot 45, C rot 30 x1.5), in the world frame across the four
blocks (the block borders x 1344 and z -64 included). Prints each defect with its block, its place relative to
the massif (inside the rim / zip annulus / apron / elsewhere), and whether the bare island already had it.
Rerun: py studies/terrain-malleability/rockstretch/rot_cracks.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rot_prep as P  # noqa: E402

LABS = ("island", "A", "B", "C")
EPS = 2e-3


def key(p):
    return (round(float(p[0]), 3), round(float(p[1]), 3), round(float(p[2]), 3))


def audit(T, topo):
    edges = Counter()
    for t in T:
        k = [key(p) for p in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((k[a], k[b])))] += 1
    open_ = [e for e, n in edges.items() if n == 1 and min(e[0][1], e[1][1]) > 0.5]
    verts = {key(p) for t in T for p in t}
    grid = defaultdict(list)
    for v in verts:
        grid[(math.floor(v[0]), math.floor(v[2]))].append(v)
    tj = set()
    for t in T:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = np.array(t[a]), np.array(t[b])
            d = pb - pa
            L2 = float(d @ d)
            if L2 < 1e-10:
                continue
            ka, kb = key(pa), key(pb)
            x0, x1 = sorted((pa[0], pb[0]))
            z0, z1 = sorted((pa[2], pb[2]))
            for gx in range(math.floor(x0) - 1, math.floor(x1) + 2):
                for gz in range(math.floor(z0) - 1, math.floor(z1) + 2):
                    for w in grid.get((gx, gz), ()):
                        if w == ka or w == kb:
                            continue
                        wv = np.array(w)
                        s = float((wv - pa) @ d) / L2
                        if not 1e-4 < s < 1 - 1e-4:
                            continue
                        if np.linalg.norm(pa + s * d - wv) < EPS:
                            tj.add((w, ka, kb))
    return open_, sorted(tj)


def where(p, rock_xz, rim_r, cx, cz):
    r = math.hypot(p[0] - cx, p[2] - cz)
    blk = (int(p[0] // 64), int(-p[2] // 64))
    border = abs(p[0] - 1344.0) < 0.01 or abs(p[2] + 64.0) < 0.01
    if rock_xz is None:
        return f"blk {blk}{' BORDER' if border else ''}"
    d = min(math.hypot(p[0] - x, p[2] - z) for x, z in rock_xz)
    zone = "rock" if d < 0.05 else "zip/apron" if d < 6.0 else "grass"
    return f"blk {blk}{' BORDER' if border else ''} {zone} {d:.2f}u from rock"


def main():
    base_open, base_tj = None, None
    for lab in LABS:
        T, topo = P.load(lab) if lab != "island" else _load_island()
        open_, tj = audit(T, topo)
        rock = T[topo == P.ROCK].reshape(-1, 3) if (topo == P.ROCK).any() else None
        rock_xz = None if rock is None else {(round(float(p[0]), 2), round(float(p[2]), 2)) for p in rock}
        cx = cz = rim_r = None
        if rock is not None:
            cx, cz = float(rock[:, 0].mean()), float(rock[:, 2].mean())
        if lab == "island":
            base_open, base_tj = set(open_), {w for w, _, _ in tj}
        new_open = [e for e in open_ if e not in base_open]
        new_tj = [x for x in tj if x[0] not in base_tj]
        print(f"== {lab}: open edges {len(open_)} (new vs island {len(new_open)}), T-junctions {len(tj)} "
              f"(new {len(new_tj)})")
        for e in (new_open if lab != "island" else open_)[:12]:
            print(f"   OPEN {e[0]} -- {e[1]}  {where(e[0], rock_xz, rim_r, cx, cz)}")
        for w, a, b in (new_tj if lab != "island" else tj)[:12]:
            print(f"   TJ   {w} on {a}--{b}  {where(w, rock_xz, rim_r, cx, cz)}")


def _load_island():
    from ff9mapkit.world import mesh as M, extract as X
    tris, topo = [], []
    for bx, by in P.BLOCKS:
        d = M.read_ff9mesh(P.LAB / "island" / "FF9CustomMap-lab" / M.override_relpath(1, bx, by))
        V = np.asarray(d["verts"], float) + np.array([64.0 * bx, 0.0, -64.0 * by])
        idx = np.asarray(d["indices"]).reshape(-1, 3)
        tris.append(V[idx])
        topo += [X.decode_id(int(round(d["tangents"][t[0]][0])))["topograph"] for t in idx]
    return np.concatenate(tris), np.array(topo)


if __name__ == "__main__":
    main()
