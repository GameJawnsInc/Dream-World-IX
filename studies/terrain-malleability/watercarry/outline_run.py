"""Rung 1 runner: cluster C's kit island outline (``river.outline``), its custom-outline mint (``river.mint``) and the
join-column gates J1-J4, with plans of the island and of each join. Offline; reads the install, writes nothing to it.
RUN:  py studies/terrain-malleability/watercarry/outline_run.py
      (writes out/outline.json, out/outline_plan.png, out/outline_join_E.png, out/outline_join_W.png)
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
from ff9mapkit.world import island as I, river as R  # noqa: E402
import fragment_run as FR  # noqa: E402


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    f = R.fragment(R.CLUSTER_C)
    ol = R.outline(f)
    built = R.mint(ol)
    joins = R.join_gates(built, ol, f.joins)
    v = I.verify_landmass(built)
    rep = {"outline": ol.report, "shore_origin": ol.shore_origin, "blocks": [list(b) for b in sorted(built["blocks"])],
           "mint_tris": sum(len(b.tris) for b in built["blocks"].values()), "joins": joins,
           "verify": {k: v[k] for k in ("cracks", "open_edges", "holes", "down_facing", "walk_filter_fails",
                                        "grass_over_8u", "missing_faces")}}
    print(json.dumps(rep, indent=1))
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "outline.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")

    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    fig, ax = plt.subplots(figsize=(13, 15))
    ax.add_collection(PolyCollection([np.asarray([gpos[k] for k in t])[:, [0, 2]] for t in gtris],
                                     facecolors=["#8a5a2b" if m[2] == "rock" else "#b8e0a8" for m in gmeta],
                                     edgecolors="#ffffff", linewidths=0.2, alpha=0.8))
    ax.add_collection(PolyCollection([t["P"][:, [0, 2]] for t in f.tris], facecolors=[FR.colour(t) for t in f.tris],
                                     edgecolors="none", alpha=0.85))
    ring = np.asarray(ol.ring + [ol.ring[0]])
    ax.plot(ring[:ol.arc_end + 1, 0], ring[:ol.arc_end + 1, 1], color="#c00000", lw=1.5, label="the kit arc")
    ax.plot(ring[ol.arc_end:, 0], ring[ol.arc_end:, 1], color="#0000c0", lw=1.0, ls="--",
            label="the seaward boundary (closes the ring; the opening drops this side)")
    for n, (_cr, b) in f.joins.items():
        ax.annotate(n, (b[0], b[2]), xytext=(6, 6), textcoords="offset points", fontsize=14, weight="bold")
    ax.set_xlim(ring[:, 0].min() - 10, ring[:, 0].max() + 10)
    ax.set_ylim(ring[:, 1].min() - 10, ring[:, 1].max() + 10)
    ax.set_aspect("equal")
    ax.legend(loc="lower left")
    ax.set_title(f"cluster C: the kit arc ({ol.report['arc_len']}u) and the custom-outline mint; J1-J4 green")
    fig.savefig(HERE / "out" / "outline_plan.png", dpi=90, bbox_inches="tight")
    for n, (_cr, b) in f.joins.items():
        ax.set_xlim(b[0] - 22, b[0] + 22)
        ax.set_ylim(b[2] - 22, b[2] + 22)
        ax.set_title(f"join {n}: the kit wall (brown, minted) meets the carried stock lip at the column")
        fig.savefig(HERE / "out" / f"outline_join_{n}.png", dpi=90, bbox_inches="tight")


if __name__ == "__main__":
    main()
