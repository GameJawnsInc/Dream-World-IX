"""Rung 2 runner: cluster C composed onto the open ocean (``river.compose``) -- the opening, the apron, the open zip,
the area stamp, every gate and the binding plan -- with plans of the island and of its seams. Offline: reads the
install, writes nothing to it.
RUN:  py studies/terrain-malleability/watercarry/compose_run.py [--no-apron]
      (writes out/compose.json, out/compose_plan.png, out/compose_{E,W,NE,mouth}.png)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import river as R  # noqa: E402
import fragment_run as FR  # noqa: E402


def colour(t):
    if t["src"] == "kit":
        return "#8a5a2b" if t["fam"] == "rock" else "#b8e0a8"
    if t["src"] == "zip":
        return "#f0d020"
    return FR.colour(t)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    win = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(win, R.CLUSTER_C)
    ol = R.outline(f)
    offs = R.open_ocean_offsets(sorted(R.mint(ol)["blocks"]))
    dbx, dby = offs[0]
    comp = R.compose(f, offset=(64.0 * dbx, -64.0 * dby), window=win, ol=ol, apron="--no-apron" not in sys.argv)
    rep = dict(comp.report, open_ocean_offsets=offs, plan=comp.plan)
    print(json.dumps(rep, indent=1, default=float))
    (HERE / "out").mkdir(exist_ok=True)
    tag = "" if "--no-apron" not in sys.argv else "_noapron"
    (HERE / "out" / f"compose{tag}.json").write_text(json.dumps(rep, indent=1, default=float), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(14, 16))
    order = sorted(comp.tris, key=lambda t: {"kit": 0, "stock": 1, "zip": 2}[t["src"]])   # the zip on top: a fold shows
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in order], facecolors=[colour(t) for t in order],
                                     edgecolors="#404040", linewidths=0.12))
    P = np.concatenate([t["P"] for t in comp.tris])
    for x in range(int(P[:, 0].min() // 64) * 64, int(P[:, 0].max()) + 64, 64):     # the block borders
        ax.axvline(x, color="#ff00ff", lw=0.6, ls=":")
    for z in range(int(P[:, 2].min() // 64) * 64, int(P[:, 2].max()) + 64, 64):
        ax.axhline(z, color="#ff00ff", lw=0.6, ls=":")
    ax.set_aspect("equal")
    ax.set_title(f"cluster C composed at offset {comp.offset} (blocks wrap at the seam): kit lawn green, kit wall "
                 f"brown, the zip yellow, stock verbatim; green={rep['green']}")
    ax.set_xlim(P[:, 0].min() - 6, P[:, 0].max() + 6)
    ax.set_ylim(P[:, 2].min() - 6, P[:, 2].max() + 6)
    fig.savefig(HERE / "out" / f"compose_plan{tag}.png", dpi=80, bbox_inches="tight")
    dx, dz = comp.offset
    for name, (cx, cz, r) in {"E": (1136 + dx, -1020 + dz, 24), "W": (1044 + dx, -1082 + dz, 20),
                              "NE": (1133 + dx, -1004 + dz, 12), "mouth": (1046 + dx, -985 + dz, 20)}.items():
        ax.set_xlim(cx - r, cx + r)
        ax.set_ylim(cz - r, cz + r)
        ax.set_title(f"{name}: the seam between the kit (green/brown), the zip (yellow) and the carried stock")
        fig.savefig(HERE / "out" / f"compose_{name}{tag}.png", dpi=80, bbox_inches="tight")


if __name__ == "__main__":
    main()
