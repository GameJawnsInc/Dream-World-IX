"""comp9 re-examined: why the snow massif refuses, read from its own rim. Reads stock bytes only; writes
out/comp9_diagnose.json and out/comp9_home.png.

NOTES.md's Open list read comp9's refusal as "a coarse rim" (zip chords to 15.5u against the 9u edge gate) and
proposed splitting its rim. This measures the rim before any split is built:
  A. THE RIM GRAIN of every catalogued donor and every candidate: rim points, longest rim edge (L0), p90, edges over
     6/8/9u, and the steepest rise along one rim edge. A coarse rim would show edges near or over 9u.
  B. comp9's RIM STEPS: rim edges rising more than 2.0u, with what welds across them at home.
  C. comp9's INLETS: pairs of rim points under 12u apart in plan, over 40u apart along the rim, whose midpoint lies
     OUTSIDE the rim polygon (an inlet of home ground, not the width of an arm).
The sweep's refusals themselves come from `sweep.py` (comp9: 0/6, Uaho 6/6 on today's kit).
RUN:  py studies/terrain-malleability/mountaindonors/comp9_diagnose.py
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import extract as X, interior as IN, river as R  # noqa: E402

DONORS = {                                   # catalogued (world/data/donors.toml) then candidates (sweep.py)
    "uaho": [(0, 0)], "crag": [(10, 5), (10, 6)], "horseshoe": [(5, 15), (6, 15), (5, 16), (6, 16)],
    "comp20": [(12, 16), (12, 17)], "desert-peak": [(19, 3)],
    "comp9": [(8, 0), (8, 1), (9, 0), (9, 1), (10, 0)], "comp19": [(6, 2), (7, 2), (7, 3)],
    "comp10": [(14, 14), (15, 14)], "comp26": [(14, 3), (15, 3)],
}
ROCK = frozenset(IN.MOUNTAIN_ROCK_TOPOS)
k3 = lambda p: IN.kk3(tuple(float(v) for v in p))     # noqa: E731


def blob(name):
    return IN._mountain_blob(DONORS[name], rock_topos=ROCK, alcove_box=IN.UAHO_ALCOVE if name == "uaho" else None,
                             log=lambda *a: None)


def grain(B):
    rim = np.array(B["rim"], dtype=float)
    n = len(rim)
    nxt = np.roll(rim, -1, axis=0)
    el = np.hypot(nxt[:, 0] - rim[:, 0], nxt[:, 2] - rim[:, 2])
    dy = np.abs(nxt[:, 1] - rim[:, 1])
    return {"rim_pts": n, "L0": round(float(el.max()), 2), "p90": round(float(np.percentile(el, 90)), 2),
            "over_6u": int((el > 6).sum()), "over_8u": int((el > 8).sum()), "over_9u": int((el > 9).sum()),
            "max_edge_rise": round(float(dy.max()), 2), "rim_y": [round(float(rim[:, 1].min()), 2),
                                                                   round(float(rim[:, 1].max()), 2)]}


def inside(poly, x, z):
    c = False
    for i in range(len(poly)):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % len(poly)]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            c = not c
    return c


def comp9_detail(B):
    rim = [np.array(p, dtype=float) for p in B["rim"]]
    n = len(rim)
    bp = X.block_parts(disc=1)
    blks = {(bx + dx, by + dy) for bx, by in DONORS["comp9"] for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    T = []
    for b in sorted(blks):
        if b in bp and "terrain" in bp[b]:
            T += R.block_tris(X.read_block(*b, disc=1, part="terrain"), *b, "terrain")
    blob_keys = {tuple(sorted(k3(B["dV"][i]) for i in B["dtri"][t])) for t in B["blob"]}
    by_edge, by_vert = {}, {}
    for t in T:
        ks = [k3(p) for p in t["P"]]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            by_edge.setdefault(tuple(sorted((ks[a], ks[b]))), []).append(t)
        for k in ks:
            by_vert.setdefault(k, []).append(t)
    steps = []
    for k in range(n):
        a, b = rim[k], rim[(k + 1) % n]
        if abs(a[1] - b[1]) > 2.0:
            e = tuple(sorted((k3(a), k3(b))))
            across = [t for t in by_edge.get(e, []) if tuple(sorted(k3(p) for p in t["P"])) not in blob_keys]
            touch = [t for t in by_vert.get(k3(a), []) + by_vert.get(k3(b), [])
                     if tuple(sorted(k3(p) for p in t["P"])) not in blob_keys]
            steps.append({"edge": k, "from": [round(float(v), 2) for v in a], "to": [round(float(v), 2) for v in b],
                          "plan_u": round(math.hypot(a[0] - b[0], a[2] - b[2]), 2),
                          "rise_u": round(abs(float(a[1] - b[1])), 2),
                          "on_block_border": bool(abs(a[0] % 64) < 1e-3 and abs(b[0] % 64) < 1e-3),
                          "welded_across": [(t["topo"], t["blk"]) for t in across],
                          "touching_home_tris": {f"topo {tp} in {blk}": c for (tp, blk), c in
                                                 Counter((t["topo"], t["blk"]) for t in touch).items()}})
    poly = [(p[0], p[2]) for p in rim]
    cum = np.concatenate([[0], np.cumsum([math.hypot(*(rim[(k + 1) % n] - rim[k])[[0, 2]]) for k in range(n)])])
    per = cum[-1]
    cands = []
    for i in range(n):
        for j in range(i + 2, n):
            d = math.hypot(*(rim[i] - rim[j])[[0, 2]])
            along = min(cum[j] - cum[i], per - (cum[j] - cum[i]))
            mid = (rim[i] + rim[j]) / 2
            if d < 12.0 and along > 40.0 and not inside(poly, mid[0], mid[2]):
                cands.append((d, along, i, j, mid))
    cands.sort(key=lambda c: c[0])
    inlets, seen = [], []
    for d, along, i, j, mid in cands:
        if any(abs(i - a) < 5 and abs(j - b) < 5 for a, b in seen):
            continue
        seen.append((i, j))
        inlets.append({"mouth_u": round(d, 2), "rim_inside_u": round(along, 1), "points": [i, j],
                       "at": [round(float(mid[0]), 1), round(float(mid[2]), 1)]})
    feet = Counter(t["topo"] for k in range(n) for t in by_edge.get(tuple(sorted((k3(rim[k]), k3(rim[(k + 1) % n])))), [])
                   if tuple(sorted(k3(p) for p in t["P"])) not in blob_keys)
    return {"steps": steps, "inlets": inlets, "feet": dict(feet)}, T


def plan(B, T, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    col = {27: "#f2f4f8", 28: "#dfe6ee", 49: "#7d6650", 58: "#a89277", 7: "#5a4a3a", 62: "#6a5a48"}
    rim = np.array(B["rim"], dtype=float)
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in T], facecolors=[col.get(t["topo"], "#c8d8a0")
                                                                                  for t in T],
                                     edgecolors="#00000018", lw=0.3))
    ax.plot(np.r_[rim[:, 0], rim[0, 0]], np.r_[rim[:, 2], rim[0, 2]], "-", color="#ff00aa", lw=1.6)
    for x in (512, 576, 640, 704):
        ax.axvline(x, color="#888", lw=0.5, ls=":")
    ax.set_xlim(rim[:, 0].min() - 20, rim[:, 0].max() + 20)
    ax.set_ylim(rim[:, 2].min() - 20, rim[:, 2].max() + 20)
    ax.set_aspect("equal")
    ax.set_title("comp9 at home: rock brown, snow white, coastal 58 tan; the carried rim magenta; block borders dotted",
                 fontsize=9)
    fig.savefig(path, dpi=100, bbox_inches="tight")


def main():
    rep = {"grain": {}}
    blobs = {}
    for name in DONORS:
        try:
            blobs[name] = blob(name)
            rep["grain"][name] = grain(blobs[name])
        except Exception as e:                                                  # noqa: BLE001
            rep["grain"][name] = {"refused": f"{type(e).__name__}: {e}"[:200]}
    rep["comp9"], T = comp9_detail(blobs["comp9"])
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "comp9_diagnose.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    plan(blobs["comp9"], T, HERE / "out" / "comp9_home.png")
    for name, g in rep["grain"].items():
        print(f"{name:12s} {g}")
    print(json.dumps(rep["comp9"], indent=1, default=str))


if __name__ == "__main__":
    main()
