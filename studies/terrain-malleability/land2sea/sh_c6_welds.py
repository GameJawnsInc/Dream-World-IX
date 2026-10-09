"""ISLAND CLUSTERS, question 6 (2026-10-09): is a sink's result watertight? An independent check of the finished mesh.

The footprint sink builds new geometry: part-cells ear-clipped against the old coastline, kept water split where a 4u
line crosses it. Its own gates count coverage samples; they do not look at edges. Here every plan (`sink_auto_plan`) is
applied to stock (drops out, emits in) over the 3x3 blocks round it, and the water at the waterline is checked:
  open edges   a new tri's edge that no other tri (new or kept, any part) shares -- a crack, unless it is the outer
               rim of the checked area or faces an open-ocean block (no mesh: open in stock too)
  T-junctions  a vertex lying part-way along a new tri's edge (zero-area slivers excluded)
  near misses  two distinct vertices of new tris and their neighbours within 0.05u (the weld audit's threshold)
Whole-tile plans (rounds 10-11, in-game proven) are the control.
Writes out/sh_c6_welds.json.
Run (from C:\\gd\\Dream-World-IX):  py studies/terrain-malleability/land2sea/sh_c6_welds.py X Z [X Z ...]
"""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2] / "ff9mapkit"
sys.path.insert(0, str(KIT))
PARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4", "object")


def k3(v):
    return (round(v[0][0], 4), round(v[0][1], 4), round(v[0][2], 4))


def area(t):
    (a, b, c) = [(v[0][0], v[0][2]) for v in t]
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0


def check(at, res):
    from ff9mapkit.world import discmirror as DM, transplant as TR
    real = DM._real_parts(1, "0_1")
    plan, rep = TR.sink_auto_plan(at)
    blocks = sorted(plan)
    near = sorted({(b[0] + dx, b[1] + dy) for b in blocks for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(real))
    soup = {(b, p): TR.world_tris(*b, p) if p in real[b] else [] for b in near for p in PARTS}
    new = []
    for b, tws in plan.items():
        for tw in tws:
            if isinstance(tw, TR.DropTris):
                soup[(b, tw.part)] = [t for t in soup[(b, tw.part)] if tw._key_set(t) not in tw.keys]
            elif isinstance(tw, TR.EmitTris):
                em = tw.emit()
                soup[(b, tw.part)] += em
                new += em
    allt = [t for ts in soup.values() for t in ts]
    ec = Counter()
    for t in allt:
        ks = [k3(v) for v in t]
        for i in range(3):
            if ks[i] != ks[(i + 1) % 3]:
                ec[tuple(sorted((ks[i], ks[(i + 1) % 3])))] += 1
    xs = [v[0][0] for t in new for v in t]
    zs = [v[0][2] for t in new for v in t]
    lo_x, hi_x = 64.0 * min(b[0] for b in near), 64.0 * (max(b[0] for b in near) + 1)
    lo_z, hi_z = -64.0 * (max(b[1] for b in near) + 1), -64.0 * min(b[1] for b in near)
    open_edges = []
    for t in new:
        if area(t) < 1e-9:
            continue
        ks = [k3(v) for v in t]
        for i in range(3):
            e = tuple(sorted((ks[i], ks[(i + 1) % 3])))
            if ec[e] == 1:
                rim = all(abs(p[0] - lo_x) < 1e-3 or abs(p[0] - hi_x) < 1e-3 or abs(p[2] - lo_z) < 1e-3
                          or abs(p[2] - hi_z) < 1e-3 for p in e)
                # an edge on a block border facing an open-ocean block (no mesh of its own: the shared SeaBlockPrefab)
                # is open in stock too
                mx, mz = (e[0][0] + e[1][0]) / 2.0, (e[0][2] + e[1][2]) / 2.0
                cx, cz = TR._plan_centroid(t)
                ox, oz = mx + (mx - cx) * 1e-3, mz + (mz - cz) * 1e-3
                prefab = (int(math.floor(ox / 64.0)), int(math.floor(-oz / 64.0))) not in real
                if not rim and not prefab:
                    open_edges.append(e)
    # T-junctions: any vertex of any tri strictly inside a new tri's edge
    vcell = defaultdict(set)
    for t in allt:
        for v in t:
            vcell[(math.floor(v[0][0] / 4.0), math.floor(v[0][2] / 4.0))].add(k3(v))
    tj = []
    for t in new:
        if area(t) < 1e-9:
            continue
        for i in range(3):
            a, b = t[i][0], t[(i + 1) % 3][0]
            cells = {(math.floor(a[0] / 4.0) + dx, math.floor(a[2] / 4.0) + dz) for dx in (-1, 0, 1) for dz in (-1, 0, 1)}
            for c in cells:
                for q in vcell.get(c, ()):
                    if q in (k3(t[i]), k3(t[(i + 1) % 3])) or abs(q[1] - 0.0) > 1e-6:
                        continue
                    if TR._seg_dist((q[0], q[2]), (a[0], a[2]), (b[0], b[2])) < 1e-5:
                        tj.append(q)
    # near misses among new tris' vertices and everything round them
    newv = {k3(v) for t in new for v in t}
    near_miss = 0
    for qv in newv:
        c = (math.floor(qv[0] / 4.0), math.floor(qv[2] / 4.0))
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for w in vcell.get((c[0] + dx, c[1] + dz), ()):
                    if w != qv and abs(w[1] - qv[1]) < 1e-6 and 0 < math.hypot(w[0] - qv[0], w[2] - qv[2]) < 0.05:
                        near_miss += 1
    out = {"at": at, "fill": rep.get("fill"), "new_tris": len(new), "open_edges": len(open_edges),
           "open_first": open_edges[:2], "t_junctions": len(set(tj)), "t_first": sorted(set(tj))[:2],
           "near_miss_pairs": near_miss // 2}
    res[f"{at[0]},{at[1]}"] = out
    print(json.dumps(out), flush=True)


def main():
    import ff9mapkit
    assert "Dream-World-IX" in ff9mapkit.__file__, ff9mapkit.__file__
    a = [float(v) for v in sys.argv[1:]]
    res = {}
    for k in range(0, len(a), 2):
        check((a[k], a[k + 1]), res)
    (HERE / "out" / "sh_c6_welds.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
