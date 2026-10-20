"""Before composing the bay carry: does any fragment boundary round cluster C cut ONLY lattice ground?

The bay carry seats a stock fragment (the river ensemble + the cove: its water, both beach arcs, the island in it)
into a minted island. The fragment's LANDWARD boundary is a cut through stock land. Grass mains are a 4u lattice and
cut lawfully (the zip machinery). A forest canopy, a rock massif or an Object is a component that carries WHOLE or not
at all (THE CANOPY CARRY LAW, ROCK RIGID, THE OBJECT POSE LAW). So the first question is whether any boundary
crosses none of them.
Candidates: the convex hull of (the river ensemble's ring + the cove), grown outward by D. The cove = the water and
beach tris whose centroid lies on the bay side of the W-E join chord within the bay's box, plus the island in it.
Each boundary is sampled every 0.5u and classed by the surface the ground query sees there (the topmost hit across
Terrain / Object / Beach1 / water parts).
RUN:  py studies/terrain-malleability/watercarry/closure.py   (writes out/closure.json)
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X  # noqa: E402
import seat_dryrun as S  # noqa: E402

W_BASE, E_BASE = (1040.0, -1083.34), (1141.11, -1028.0)
BAY_BOX = (1012.0, 1146.0, -1090.0, -984.0)              # x0, x1, z0, z1
WATER = ("sea1", "sea2", "sea3", "sea4", "sea5")


def side(p):
    """> 0 on the bay side of the W->E chord (the side the mouth is on)."""
    ax, az = W_BASE
    bx, bz = E_BASE
    return (bx - ax) * (p[1] - az) - (bz - az) * (p[0] - ax)


def classify(topo, part):
    if part in WATER:
        return "water"
    if part == "beach1":
        return "beach"
    if part == "object":
        return "object"
    if part in ("stream", "riverjoint", "river", "falls"):
        return "river"
    return {36: "forest", 37: "forest", 49: "rock", 7: "rock", 58: "lip", 62: "bank", 31: "sand", 59: "building"}.get(
        topo, "grass" if topo in (0, 1, 2, 3, 42, 13, 10, 11, 12) else f"topo{topo}")


def main():
    bp = X.block_parts(disc=1)
    tris = []
    for bx in range(14, 19):
        for by in range(13, 18):
            for part in ("terrain", "object", "beach1", "stream", "riverjoint") + WATER:
                if part in bp.get((bx, by), ()):
                    tris += S.tris_uv(bx, by, part)
    water, banks, _ = S.unit()
    ring_pts = [(p[0], p[2]) for t in water + banks for p in t["P"]]
    mouth_side = side((1043.1, -990.7))
    x0, x1, z0, z1 = BAY_BOX
    cove = [t for t in tris if t["part"] in WATER + ("beach1",)
            and x0 <= t["P"][:, 0].mean() <= x1 and z0 <= t["P"][:, 2].mean() <= z1
            and side((t["P"][:, 0].mean(), t["P"][:, 2].mean())) * mouth_side > 0]
    cove_pts = [(p[0], p[2]) for t in cove for p in t["P"]]
    # the island in the cove: land tris inside the bay box, on the bay side, not part of the mainland's coast strip
    pts = np.array(ring_pts + cove_pts + [W_BASE, E_BASE])
    hull = pts[ConvexHull(pts).vertices]
    cx, cz = hull.mean(axis=0)
    A = np.array([t["P"][:, [0, 2]] for t in tris])
    mins, maxs = A.min(axis=1), A.max(axis=1)

    def top_hit(x, z):
        cand = np.where((mins[:, 0] <= x) & (maxs[:, 0] >= x) & (mins[:, 1] <= z) & (maxs[:, 1] >= z))[0]
        best = None
        for i in cand:
            t = tris[i]
            a, b, c = t["P"]
            d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(d) < 1e-12:
                continue
            l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
            l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
            if l1 >= -1e-9 and l2 >= -1e-9 and 1 - l1 - l2 >= -1e-9:
                y = l1 * a[1] + l2 * b[1] + (1 - l1 - l2) * c[1]
                if best is None or y > best[0]:
                    best = (y, classify(t["topo"], t["part"]))
        return best[1] if best else "none"
    out = {}
    for D in (6.0, 12.0):
        poly = []
        for hx, hz in hull:                                  # grow each hull vertex away from the centroid by D
            L = math.hypot(hx - cx, hz - cz) or 1.0
            poly.append((hx + (hx - cx) / L * D, hz + (hz - cz) / L * D))
        cls, L_tot = Counter(), 0.0
        for i in range(len(poly)):
            (ax, az), (bx_, bz_) = poly[i], poly[(i + 1) % len(poly)]
            n = max(1, int(math.hypot(bx_ - ax, bz_ - az) / 0.5))
            for k in range(n):
                f = (k + 0.5) / n
                cls[top_hit(ax + f * (bx_ - ax), az + f * (bz_ - az))] += 0.5
            L_tot += math.hypot(bx_ - ax, bz_ - az)
        out[f"hull+{D:g}"] = {"perimeter": round(L_tot, 1), "crossing": {k: round(v, 1) for k, v in cls.most_common()},
                              "vertices": [[round(x, 1), round(z, 1)] for x, z in poly]}
        print(f"hull + {D:g}u: perimeter {L_tot:.0f}u, crosses: {dict((k, round(v)) for k, v in cls.most_common())}")
    (HERE / "out" / "closure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__" and not {"--closure", "--minimal"} & set(sys.argv):
    main()


def closure():
    """THE COMPONENT CLOSURE: from the river ensemble + the cove, add every WHOLE forest blob (topo 36/37), Object
    component and building footprint (59) that shares a vertex with the set, until nothing new touches it. Then
    class the closed set's outer boundary by what lies across it. A lawful fragment's boundary meets only lattice
    ground (grass, sand) and water; rock (49/7) is a massif that cannot be carried by a cut."""
    from collections import defaultdict
    from ff9mapkit.world.interior import kk3
    bp = X.block_parts(disc=1)
    tris = []
    for bx in range(13, 20):
        for by in range(12, 18):
            for part in ("terrain", "object", "beach1", "stream", "riverjoint") + WATER:
                if part in bp.get((bx, by), ()):
                    tris += S.tris_uv(bx, by, part)
    for i, t in enumerate(tris):
        t["i"] = i
        t["cls"] = classify(t["topo"], t["part"])
    water, banks, _ = S.unit()
    ukeys = {kk3(p) for t in water + banks for p in t["P"]}
    mouth_side = side((1043.1, -990.7))
    x0, x1, z0, z1 = BAY_BOX
    inset = set()
    for t in tris:
        c = t["P"].mean(axis=0)
        if any(kk3(p) in ukeys for p in t["P"]) and t["cls"] in ("river", "bank"):
            inset.add(t["i"])
        elif t["part"] in WATER + ("beach1",) and x0 <= c[0] <= x1 and z0 <= c[2] <= z1 and side((c[0], c[2])) * mouth_side > 0:
            inset.add(t["i"])
    # components of the whole-carry classes
    by_key = defaultdict(list)
    for t in tris:
        for p in t["P"]:
            by_key[kk3(p)].append(t["i"])

    def comp_of(i, classes):
        seen, stack = {i}, [i]
        while stack:
            j = stack.pop()
            for p in tris[j]["P"]:
                for k in by_key[kk3(p)]:
                    if k not in seen and tris[k]["cls"] in classes:
                        seen.add(k)
                        stack.append(k)
        return seen
    added = Counter()
    changed = True
    while changed:
        changed = False
        touch = {k for i in inset for p in tris[i]["P"] for k in by_key[kk3(p)]} - inset
        for k in sorted(touch):
            c = tris[k]["cls"]
            if k in inset or c not in ("forest", "object", "building"):
                continue
            comp = comp_of(k, {"forest"} if c == "forest" else {"object", "building"})
            inset |= comp
            added[c] += 1
            changed = True
    # the closed set's boundary: what lies across each once-edge
    ec = Counter(tuple(sorted((kk3(t["P"][a]), kk3(t["P"][b])))) for i in inset for t in [tris[i]]
                 for a, b in ((0, 1), (1, 2), (2, 0)))
    once = {e for e, n in ec.items() if n == 1}
    across = Counter()
    for t in tris:
        if t["i"] in inset:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((kk3(t["P"][a]), kk3(t["P"][b]))))
            if e in once:
                across[t["cls"]] += math.dist(e[0], e[1])
    rock_tris = [tris[i] for i in inset if tris[i]["cls"] == "rock"]
    rep = {"set_tris": len(inset), "components_added": dict(added),
           "boundary_across": {k: round(v, 1) for k, v in across.most_common()},
           "rock_inside": len(rock_tris)}
    print("THE COMPONENT CLOSURE:", json.dumps(rep))
    return rep


if __name__ == "__main__" and "--closure" in sys.argv:
    out = json.loads((HERE / "out" / "closure.json").read_text(encoding="utf-8"))
    out["component_closure"] = closure()
    (HERE / "out" / "closure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def minimal_fragment():
    """THE MINIMAL FRAGMENT: the river ensemble (parts, banks, the source marker, the bridge) + the cove ASSEMBLY --
    the water and beach on the bay side of the W-E chord in the bay box, the backing sand (topo 31) and the coastal
    lip walls (58) welded to them, and the island standing in the cove (its land, flood-filled from a seed). Forests
    and the tower stay home: a component BESIDE the fragment is not cut, only left. Classes the outer boundary."""
    from collections import defaultdict
    from ff9mapkit.world.interior import kk3
    bp = X.block_parts(disc=1)
    tris = []
    for bx in range(13, 20):
        for by in range(12, 18):
            for part in ("terrain", "object", "beach1", "stream", "riverjoint") + WATER:
                if part in bp.get((bx, by), ()):
                    tris += S.tris_uv(bx, by, part)
    for i, t in enumerate(tris):
        t["i"] = i
        t["cls"] = classify(t["topo"], t["part"])
    by_key = defaultdict(list)
    for t in tris:
        for p in t["P"]:
            by_key[kk3(p)].append(t["i"])
    water, banks, _ = S.unit()
    unit_keys = {(t["part"], tuple(np.round(t["P"].ravel(), 4))) for t in water + banks}
    inset = {t["i"] for t in tris if (t["part"], tuple(np.round(t["P"].ravel(), 4))) in unit_keys}
    mouth_side = side((1043.1, -990.7))
    x0, x1, z0, z1 = BAY_BOX

    def bayside(t):
        c = t["P"].mean(axis=0)
        return x0 <= c[0] <= x1 and z0 <= c[2] <= z1 and side((c[0], c[2])) * mouth_side > 0
    cove = {t["i"] for t in tris if t["part"] in WATER + ("beach1",) and bayside(t)}
    inset |= cove
    ckeys = {kk3(p) for i in cove for p in tris[i]["P"]}
    walls_sand = {t["i"] for t in tris if t["cls"] in ("lip", "sand") and bayside(t)
                  and any(kk3(p) in ckeys for p in t["P"])}
    # THE COASTAL CLOSURE: the bay's coast is an assembly -- grow it through every lip / sand / beach tri welded to it
    # on the bay side, so the only coastal cuts left are where the chord meets the coast (the join columns)
    grow = True
    while grow:
        grow = False
        keys = {kk3(p) for i in inset | walls_sand for p in tris[i]["P"]}
        for t in tris:
            if t["i"] in inset or t["i"] in walls_sand or t["cls"] not in ("lip", "sand", "beach") or not bayside(t):
                continue
            if any(kk3(p) in keys for p in t["P"]):
                walls_sand.add(t["i"])
                grow = True
    inset |= walls_sand
    # the island: flood the land from a seed tri at its middle, through land classes only
    seed = min((t for t in tris if t["part"] == "terrain"),
               key=lambda t: math.hypot(t["P"][:, 0].mean() - 1088.0, t["P"][:, 2].mean() + 1053.0))
    island, stack = {seed["i"]}, [seed["i"]]
    while stack:
        j = stack.pop()
        for p in tris[j]["P"]:
            for k in by_key[kk3(p)]:
                if k not in island and tris[k]["part"] in ("terrain", "beach1") and bayside(tris[k]):
                    island.add(k)
                    stack.append(k)
    inset |= island
    ec = Counter(tuple(sorted((kk3(tris[i]["P"][a]), kk3(tris[i]["P"][b])))) for i in inset
                 for a, b in ((0, 1), (1, 2), (2, 0)))
    once = {e for e, n in ec.items() if n == 1}
    across = Counter()
    where_cls = defaultdict(list)
    for t in tris:
        if t["i"] in inset:
            continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted((kk3(t["P"][a]), kk3(t["P"][b]))))
            if e in once:
                across[t["cls"]] += math.dist(e[0], e[1])
                if t["cls"] in ("lip", "sand", "beach", "rock"):
                    mx, mz = (e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2
                    where_cls[t["cls"]].append((round(math.hypot(mx - W_BASE[0], mz - W_BASE[1]), 1),
                                                round(math.hypot(mx - E_BASE[0], mz - E_BASE[1]), 1)))
    where = {k: {"near_W(<8u)": sum(1 for a, b in v if a < 8), "near_E(<8u)": sum(1 for a, b in v if b < 8),
                 "elsewhere": sorted((a, b) for a, b in v if a >= 8 and b >= 8)[:6]} for k, v in where_cls.items()}
    rep = {"where": where, "set_tris": len(inset), "cove_tris": len(cove), "walls_sand_tris": len(walls_sand),
           "island_tris": len(island), "boundary_across": {k: round(v, 1) for k, v in across.most_common()}}
    print("THE MINIMAL FRAGMENT:", json.dumps(rep))
    return rep


if __name__ == "__main__" and "--minimal" in sys.argv:
    out = json.loads((HERE / "out" / "closure.json").read_text(encoding="utf-8"))
    out["minimal_fragment"] = minimal_fragment()
    (HERE / "out" / "closure.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
