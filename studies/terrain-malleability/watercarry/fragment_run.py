"""Rung 0 runner: cluster C's world-river FRAGMENT from the kit (``ff9mapkit/world/river.py``), its F1/F2 gates and a
plan of what it carries. Offline; reads the install, writes nothing to it.
RUN:  py studies/terrain-malleability/watercarry/fragment_run.py   (writes out/fragment.json + out/fragment_plan.png)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import river as R  # noqa: E402

COLOUR = {"sea1": "#9fd8f0", "sea2": "#7cc4e8", "sea3": "#4f9fd6", "sea5": "#3a7fc0", "sea4": "#25579a",
          "beach1": "#f2dd8c", "stream": "#00c8d8", "riverjoint": "#00a0c0", "river": "#00a0c0", "falls": "#00a0c0",
          "object": "#d04040", "lip": "#8a5a2b", "sand": "#d8b878", "channel": "#2f7f3f", "ground": "#7fbf6f",
          "forest": "#2f5f2f", "rock": "#707070", "building": "#a040a0"}


def colour(t):
    c = R.tri_class(t)
    return COLOUR[t["part"]] if c in ("water", "beach", "river", "object") else COLOUR[c]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    tris = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(tris, R.CLUSTER_C)
    rep = dict(f.report)
    rep["joins"] = {n: {"crest": [round(c, 3) for c in cr], "base": [round(c, 3) for c in b]}
                    for n, (cr, b) in f.joins.items()}
    print(json.dumps(rep, indent=1))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "fragment.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")

    inside = {id(t) for t in f.tris}
    P = np.array([t["P"][:, [0, 2]] for t in f.tris])
    x0, z0 = P.reshape(-1, 2).min(axis=0) - 24
    x1, z1 = P.reshape(-1, 2).max(axis=0) + 24
    ctx = [t for t in tris if id(t) not in inside and t["P"][:, 0].max() >= x0 and t["P"][:, 0].min() <= x1
           and t["P"][:, 2].max() >= z0 and t["P"][:, 2].min() <= z1]
    fig, ax = plt.subplots(figsize=(12, 12 * (z1 - z0) / (x1 - x0)))
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in ctx], facecolors=[colour(t) for t in ctx],
                                     edgecolors="none", alpha=0.22))
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in f.tris], facecolors=[colour(t) for t in f.tris],
                                     edgecolors="none"))
    for cls, col, lw in (("lawn", "#000000", 0.8), ("source", "#ff00ff", 2.5), ("join", "#ffff00", 3.5)):
        for a, b in f.boundary.get(cls, ()):
            ax.plot([a[0], b[0]], [a[2], b[2]], color=col, lw=lw)
    S = np.array(f.seaward)
    ax.plot(S[:, 0], S[:, 2], color="#ff3030", lw=2.2, label="seaward boundary")
    (_, wb), (_, eb) = f.joins["W"], f.joins["E"]
    ax.plot([wb[0], eb[0]], [wb[2], eb[2]], color="#ff3030", lw=1, ls="--", label="the straight W-E chord")
    for n, (cr, b) in f.joins.items():
        ax.annotate(n, (b[0], b[2]), xytext=(6, 6), textcoords="offset points", fontsize=14, weight="bold")
    ax.set_xlim(x0, x1)
    ax.set_ylim(z0, z1)
    ax.set_aspect("equal")
    ax.legend(loc="lower left")
    ax.set_title(f"cluster C fragment: {rep['tris']} tris (unit {rep['unit']}, cove {rep['cove']}, coast "
                 f"{rep['coast']}, islands {sum(i['tris'] for i in rep['islands'])}); F1 + F2 green")
    fig.savefig(HERE / "out" / "fragment_plan.png", dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
