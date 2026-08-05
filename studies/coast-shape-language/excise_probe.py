"""EXCISE FEASIBILITY -- what actually has to be dropped, and what has to be re-filled?

The design menu named the donor-rect EXCISE as the binding capability gap: 7 of 57
landmasses are carryable, and the disqualifier is nearly always a NEIGHBOURING mass
crossing the rect frame, not the target island. Excise = drop the foreign mass and
re-zip sea over its footprint.

Before designing that, two things must be MEASURED, because the whole shape of the
operator depends on them:

  1. Do the terrain tris separate into clean per-landmass components on SHARED VERTS?
     If two masses share a vertex anywhere the drop set is not well-defined.
  2. Is sea4 CUT under the land, or does it run continuously beneath it?
     If sea4 is continuous under land, excise is a pure DROP and needs no fill at all.
     If it is cut (THE SEA4-UNDER-LAND LAW says stock cuts it), excise must EMIT a
     patch and weld it -- a much bigger operator.

  py studies/coast-shape-language/excise_probe.py [--donor 6,6] [--size 2x2]

Read-only; touches no mod folder.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
from ff9mapkit.world import transplant as TR                 # noqa: E402

BLOCK = 64.0
KD = 4                                   # the key decimals DropTris uses


def key(v):
    return (round(v[0], KD), round(v[1], KD), round(v[2], KD))


def components(tris):
    """Group tris into components joined by SHARED VERTEX KEYS (union-find)."""
    parent = {}

    def find(a):
        parent.setdefault(a, a)
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for t in tris:
        ks = [key(v[0]) for v in t]
        for k in ks[1:]:
            union(ks[0], k)
    groups = defaultdict(list)
    for t in tris:
        groups[find(key(t[0][0]))].append(t)
    return sorted(groups.values(), key=len, reverse=True)


def bbox(tris):
    xs = [v[0][0] for t in tris for v in t]
    zs = [v[0][2] for t in tris for v in t]
    ys = [v[0][1] for t in tris for v in t]
    return (min(xs), max(xs), min(zs), max(zs), min(ys), max(ys))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor", default="6,6")
    ap.add_argument("--size", default="2x2")
    ap.add_argument("--disc", type=int, default=1)
    args = ap.parse_args()
    dx, dy = (int(v) for v in args.donor.split(","))
    nx, ny = (int(v) for v in args.size.lower().split("x"))

    x0, x1 = BLOCK * dx, BLOCK * (dx + nx)
    z1, z0 = -BLOCK * dy, -BLOCK * (dy + ny)          # z0 < z1, both negative
    print(f"donor rect ({dx},{dy})+{nx}x{ny}  world x[{x0},{x1}] z[{z0},{z1}]")

    terrain, sea4 = [], []
    for by in range(dy, dy + ny):
        for bx in range(dx, dx + nx):
            terrain += TR.world_tris(bx, by, "terrain", disc=args.disc)
            sea4 += TR.world_tris(bx, by, "sea4", disc=args.disc)
    print(f"terrain {len(terrain)} tris, sea4 {len(sea4)} tris")

    comps = components(terrain)
    print(f"\n{len(comps)} vertex-connected terrain component(s):")
    frame_eps = 2.0
    foreign = []
    for i, c in enumerate(comps[:10]):
        bx0, bx1, bz0, bz1, by0, by1 = bbox(c)
        touches = (bx0 <= x0 + frame_eps or bx1 >= x1 - frame_eps
                   or bz0 <= z0 + frame_eps or bz1 >= z1 - frame_eps)
        tag = "CROSSES FRAME" if touches else "contained"
        print(f"   #{i}: {len(c):>5} tris  x[{bx0:8.1f},{bx1:8.1f}] "
              f"z[{bz0:9.1f},{bz1:9.1f}] y[{by0:6.1f},{by1:6.1f}]  {tag}")
        if touches:
            foreign.append(c)

    # --- the load-bearing question: is sea4 cut under the land? -----------------
    print("\nSEA4 UNDER LAND?")
    if not sea4:
        print("   no sea4 in this rect at all")
        return 0

    def plan_cells(tris, g=4.0):
        out = set()
        for t in tris:
            cx = sum(v[0][0] for v in t) / 3.0
            cz = sum(v[0][2] for v in t) / 3.0
            out.add((int(cx // g), int(cz // g)))
        return out

    sea_cells = plan_cells(sea4)
    for i, c in enumerate(comps[:6]):
        lc = plan_cells(c)
        over = lc & sea_cells
        print(f"   component #{i}: {len(lc):>5} land cells, "
              f"{len(over):>5} also carry sea4 ({100.0 * len(over) / max(1, len(lc)):.0f}%)")
    print("\n   -> HIGH overlap means sea4 runs continuously under land: an excise is a"
          "\n      pure DROP, no fill needed. LOW overlap means stock CUT the sea there"
          "\n      and the excise must EMIT a patch and weld it into the sea4 sheet.")

    # --- the SECOND load-bearing question: is each island's sea4 hole its OWN loop? ---
    # If two nearby islands share one merged hole, excising one of them cannot just
    # fill "the hole" -- the fill would swallow the island we are keeping, and the
    # operator would need an authored cut line. Separate loops = a clean operator.
    print("\nSEA4 HOLE TOPOLOGY (the fill boundary must be an EXISTING loop):")
    edge = defaultdict(int)
    for t in sea4:
        ks = [key(v[0]) for v in t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edge[tuple(sorted((ks[a], ks[b])))] += 1
    adj = defaultdict(set)
    for (a, b), c in edge.items():
        if c == 1:
            adj[a].add(b)
            adj[b].add(a)
    seen, loops = set(), []
    for s0 in sorted(adj):
        if s0 in seen:
            continue
        stack, comp = [s0], []
        seen.add(s0)
        while stack:
            v = stack.pop()
            comp.append(v)
            for w in adj[v]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        loops.append(comp)
    loops.sort(key=len, reverse=True)
    print(f"   {len(loops)} boundary loop(s) in the sea4 sheet")
    for i, lp in enumerate(loops[:8]):
        xs = [v[0] for v in lp]
        zs = [v[2] for v in lp]
        onframe = (min(xs) <= x0 + 0.01 and max(xs) >= x1 - 0.01
                   and min(zs) <= z0 + 0.01 and max(zs) >= z1 - 0.01)
        # which terrain component(s) does this loop enclose?
        encl = []
        for ci, c in enumerate(comps[:6]):
            cb = bbox(c)
            if (cb[0] >= min(xs) - 4 and cb[1] <= max(xs) + 4
                    and cb[2] >= min(zs) - 4 and cb[3] <= max(zs) + 4):
                encl.append(ci)
        print(f"   loop {i}: {len(lp):>4} verts  x[{min(xs):7.1f},{max(xs):7.1f}] "
              f"z[{min(zs):8.1f},{max(zs):8.1f}]  "
              f"{'the RECT FRAME' if onframe else 'island hole'}  encloses={encl}")
    print("\n   -> one loop per island (plus the rect frame) = the excise fill boundary"
          "\n      is an EXISTING loop and needs no authored cut line.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
