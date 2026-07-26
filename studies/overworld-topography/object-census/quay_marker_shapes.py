"""READ-ONLY: dump raw vertex geometry for the top marker candidates found by quay_marker_census.py,
to distinguish "thin vertical post/arch" shapes from "flat plaque"/"boxy building" shapes without a
renderer (no game bytes leave this scratch dump; verts are just numbers)."""
import sys
from pathlib import Path

ROOT = Path(r"C:\gd\Dream-World-IX\.claude\worktrees\gui-workspace-improvements-277c74")
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit.world import extract as X          # noqa: E402

CANDIDATES = [
    (16, 15, "N. Gate/Melda Arch"),
    (17, 15, "N. Gate/Melda Arch"),
    (18, 13, "Alexandria/Main Street, Pinnacle Rocks/Entry"),
    (14, 14, "Treno/Gate"),
    (13, 4, "Mdn. Sari/Entrance"),
    (6, 16, "(unnamed, coastal, 8 tri)"),
    (9, 1, "(unnamed, coastal, 2 tri)"),
]

for (bx, by, label) in CANDIDATES:
    bm = X.read_block(bx, by, disc=1, part="object")
    verts = bm.verts
    print(f"\n=== Block[{bx}][{by}] -- {label} -- {bm.vcount} verts, {len(bm.tris)} tris ===")
    for i, v in enumerate(verts):
        print(f"  v{i}: x={v[0]:7.2f} y={v[1]:7.2f} z={v[2]:7.2f}")
    print(f"  tris: {bm.tris}")
