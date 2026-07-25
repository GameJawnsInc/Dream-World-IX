"""Renders out/world-design/canvas.json (+ its _forbidden_blocks / _free_sweep_rows sidecars) into
a 24x20 block-grid PNG for designers + the owner: stock land (grey), each live cluster (its own
color + label), study-reserved-but-empty benches (hatched), free ocean (pale blue), with the best
free-radius circle per size class overlaid in world units.

    py -X utf8 canvas_render.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "world-design"
BLOCK = 64.0
NX, NZ = 24, 20

CLUSTER_COLORS = ["#c0392b", "#2980b9", "#27ae60", "#8e44ad", "#d35400", "#16a085", "#c2185b"]
CLASS_COLORS = {"r132": "#e74c3c", "r96": "#f39c12", "r72": "#27ae60", "r48": "#2980b9"}


def main():
    canvas = json.loads((OUT / "canvas.json").read_text())
    fb = json.loads((OUT / "_forbidden_blocks.json").read_text())
    stock_occ = {tuple(b) for b in fb["stock_occ"]}
    live = {tuple(b) for b in fb["live"]}
    named = {tuple(b) for b in fb["named"]}
    clusters = fb["clusters"]

    fig, ax = plt.subplots(figsize=(13, 11), dpi=140)
    ax.set_facecolor("#0b2a4a")

    # base layers: free ocean / stock-occupied / named-reserved-empty
    for bx in range(NX):
        for by in range(NZ):
            b = (bx, by)
            x0, z0 = bx * BLOCK, -(by + 1) * BLOCK
            if b in live:
                continue  # drawn per-cluster below
            if b in stock_occ:
                color = "#5d6d7e"
            elif b in named:
                color = "#7d6608"
            else:
                color = "#1b4f72"
            ax.add_patch(Rectangle((x0, z0), BLOCK, BLOCK, facecolor=color, edgecolor="#0b2a4a", linewidth=0.3))

    legend_handles = [
        Rectangle((0, 0), 1, 1, facecolor="#5d6d7e", label="stock land / prefab-occupied (275 blocks)"),
        Rectangle((0, 0), 1, 1, facecolor="#7d6608", label="study-reserved (donor window / calib ref, empty)"),
        Rectangle((0, 0), 1, 1, facecolor="#1b4f72", label="free open ocean (mintable, 158 blocks)"),
    ]

    for i, c in enumerate(clusters):
        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]
        for (bx, by) in c["blocks"]:
            x0, z0 = bx * BLOCK, -(by + 1) * BLOCK
            ax.add_patch(Rectangle((x0, z0), BLOCK, BLOCK, facecolor=color, edgecolor="white", linewidth=0.6))
        bxs = [b[0] for b in c["blocks"]]
        bys = [b[1] for b in c["blocks"]]
        cx = (min(bxs) + max(bxs) + 1) / 2 * BLOCK
        cz = -(min(bys) + max(bys) + 1) / 2 * BLOCK
        short = c["label"].split(" (")[0].split(" /")[0]
        ax.annotate(f"{i+1}", (cx, cz), color="white", ha="center", va="center",
                   fontsize=11, fontweight="bold",
                   bbox=dict(boxstyle="circle", facecolor=color, edgecolor="white", linewidth=0.8))
        legend_handles.append(Rectangle((0, 0), 1, 1, facecolor=color, label=f"{i+1}. {short} ({len(c['blocks'])} blk)"))

    # free-radius-class circles (best site each class, if it exists)
    for cls, col in CLASS_COLORS.items():
        top = canvas["free_space"]["by_radius_class"][cls]["top"]
        if not top:
            continue
        s = top[0]
        circ = Circle((s["cx"], s["cz"]), s["r_max"], fill=False, edgecolor=col, linewidth=2.2,
                      linestyle="--", zorder=5)
        ax.add_patch(circ)
        ax.plot(s["cx"], s["cz"], marker="+", color=col, markersize=10, zorder=6)
        legend_handles.append(Line2D([0], [0], color=col, linestyle="--", linewidth=2.2,
                                     label=f"best {cls}+ free site (R={s['r_max']:.0f}u)"))

    # grid lines every block + coarse labels
    for bx in range(0, NX + 1, 2):
        ax.axvline(bx * BLOCK, color="#0b2a4a", linewidth=0.3, zorder=0)
    for by in range(0, NZ + 1, 2):
        ax.axhline(-by * BLOCK, color="#0b2a4a", linewidth=0.3, zorder=0)
    ax.set_xticks([bx * BLOCK for bx in range(0, NX + 1, 4)])
    ax.set_xticklabels([str(bx) for bx in range(0, NX + 1, 4)])
    ax.set_yticks([-by * BLOCK for by in range(0, NZ + 1, 4)])
    ax.set_yticklabels([str(by) for by in range(0, NZ + 1, 4)])
    ax.set_xlabel("block X (0-23, wraps)")
    ax.set_ylabel("block Y (0-19)")
    ax.set_xlim(0, NX * BLOCK)
    ax.set_ylim(-NZ * BLOCK, 0)
    ax.set_aspect("equal")
    ax.set_title("Dream World IX overworld -- THE CANVAS CENSUS (2026-07-25)\n"
                "live custom content vs free ocean, FF9CustomMap-world", color="white", fontsize=13)
    fig.patch.set_facecolor("#08192b")
    ax.title.set_color("white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("white")

    ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.01, 1.0),
             fontsize=8, facecolor="#0b2a4a", edgecolor="white", labelcolor="white")
    fig.tight_layout()
    png = OUT / "canvas.png"
    fig.savefig(png, facecolor=fig.get_facecolor())
    print("wrote", png)


if __name__ == "__main__":
    raise SystemExit(main())
