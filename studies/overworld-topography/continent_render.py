"""Render THE NEW CONTINENT design onto the canvas: outline, interior programme, offshore
carries, entrance cells -- plus the measured coast-to-stock-land clearance. Read-only."""
from __future__ import annotations
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "ff9mapkit"))
sys.path.insert(0, HERE)
from ff9mapkit.world import mesh as M  # noqa: E402
import continent_site_scan as C        # noqa: E402

OUT = os.path.join(HERE, "out", "world-design")
BLOCK = 64.0
CX, CZ, R, LOBES, SEED = 176.0, -176.0, 96.0, 3, 31.0
lay = json.load(open(os.path.join(OUT, "continent_layout.json")))
pts, radii = M.multi_blob_outline(CX, CZ, lobes=LOBES, base_radius=R, seed=SEED)

# --- measured clearance from the minted coast to the nearest STOCK/live block --------------
worst = (1e9, None, None)
for (px, pz) in pts:
    for (bx, by) in C.FORBIDDEN:
        d = C.pt_block_dist(px, pz, bx, by)
        if d < worst[0]:
            worst = (d, (round(px, 1), round(pz, 1)), (bx, by))
print(f"minimum coast->stock-block clearance: {worst[0]:.1f}u  at coast {worst[1]} vs block {worst[2]}")
xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
print(f"outline x [{min(xs):.1f}, {max(xs):.1f}]   z [{min(zs):.1f}, {max(zs):.1f}]")

OFFSHORE = [
    ("harbour isle (grass beach carry)", "world-transplant --cell 5,1 --donor 7,17", [(5, 1)]),
    ("desert isle (GroundRetile)", "world-transplant --cell 9,3 --donor 10,17 --size 2x2 --ground desert --strips none",
     [(9, 3), (10, 3), (9, 4), (10, 4)]),
    ("snow isle (GroundRetile)", "world-transplant --cell 11,1 --donor 10,17 --size 2x2 --ground snow --strips none",
     [(11, 1), (12, 1), (11, 2), (12, 2)]),
]
for label, cmd, blks in OFFSHORE:
    bad = [b for b in blks if b in C.FORBIDDEN]
    print(f"offshore {label:38s} blocks={blks} {'OK (all free ocean)' if not bad else 'CONFLICT ' + str(bad)}")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
except Exception as e:
    print("no matplotlib:", e); sys.exit(0)

fig, ax = plt.subplots(figsize=(15, 13))
fig.patch.set_facecolor("#0d1b2a"); ax.set_facecolor("#123047")
for y in range(20):
    for x in range(24):
        c = (x, y)
        col = "#123047"
        if c in C.FORBIDDEN:
            col = "#7d8a97" if [x, y] in [list(b) for b in json.load(
                open(os.path.join(OUT, "_forbidden_blocks.json")))["stock_occ"]] else "#b06a3a"
        ax.add_patch(Rectangle((x * BLOCK, -(y + 1) * BLOCK), BLOCK, BLOCK,
                               facecolor=col, edgecolor="#1d3f5c", lw=.6))
ax.plot([p[0] for p in pts] + [pts[0][0]], [p[1] for p in pts] + [pts[0][1]],
        color="#7ddf7d", lw=2.4, zorder=5)
ax.fill([p[0] for p in pts], [p[1] for p in pts], color="#4a7c3f", alpha=.85, zorder=4)
for it in lay["interior"]:
    if not it.get("at"):
        continue
    x, z = it["at"]
    lbl = it["label"].split(" ")[0]
    col = {"massif-A": "#8a8a8a", "massif-B": "#8a8a8a"}.get(lbl, "#2f6b2a" if lbl.startswith("forest") else "#9ac47a")
    ax.add_patch(Circle((x, z), it["foot"], facecolor=col, edgecolor="w", lw=1.0, alpha=.95, zorder=6))
    ax.text(x, z, lbl.replace("forest-", "F").replace("hill-", "h").replace("massif-", "M"),
            color="w", ha="center", va="center", fontsize=8, zorder=7)
for label, cmd, blks in OFFSHORE:
    for (bx, by) in blks:
        ax.add_patch(Rectangle((bx * BLOCK, -(by + 1) * BLOCK), BLOCK, BLOCK,
                               facecolor="#d9a441", edgecolor="w", lw=1.2, alpha=.8, zorder=5))
    b = blks[0]
    ax.text(b[0] * BLOCK + 4, -(b[1]) * BLOCK - 14, label.split(" ")[0], color="#2b1a00", fontsize=8, zorder=8)
ax.set_xlim(0, 24 * BLOCK); ax.set_ylim(-20 * BLOCK, 0)
ax.set_aspect("equal")
ax.set_title("ANGLE B -- THE NEW CONTINENT (world-island --center 176,-176 --radius 108 "
             "--lobes 3 --seed 30 --ground grass)\nplus its minted offshore archipelago; "
             "grey = stock land, orange-brown = live custom content (immovable)",
             color="w", fontsize=11)
for (cxx, czz, nm) in [(240, -176, "PORT (cell 7,5)"), (144, -80, "NORTH (cell 4,2)")]:
    ax.plot([cxx], [czz], marker="*", ms=17, color="#ffd166", mec="k", zorder=9)
    ax.text(cxx + 8, czz, nm, color="#ffd166", fontsize=8, zorder=9)
ax.tick_params(colors="#9ac")
p = os.path.join(OUT, "continent_design.png")
fig.savefig(p, dpi=105, bbox_inches="tight", facecolor=fig.get_facecolor())
print("wrote", p)
