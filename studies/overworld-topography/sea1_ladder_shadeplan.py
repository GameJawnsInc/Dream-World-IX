"""sea1_ladder_shadeplan.py -- the FLAT SHADE-PLAN corner zoom (adapts s12_zoom_render_opus.py), PRE|POST
side by side.  Flat per-shade colours (no caustic high-frequency), so the ONLY visible change is the 4
repartitioned cells' colour -- a clean "corner changed, rest pixel-identical" proof of the {sea1,sea5}
ladder.  PRE = the immutable backup (12,18) Sea1/Sea2/Sea5; POST = the deployed tree.  No writes to the mod.

Run:  py studies/overworld-topography/sea1_ladder_shadeplan.py   -> studies/.../sea1_ladder_shadeplan.png
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M            # noqa: E402
from ff9mapkit.world import extract as X         # noqa: E402
from ff9mapkit.world.terrain import GRID_X, GRID_Y  # noqa: E402

GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
BK = REPO / "backups" / "sea1-ladder.20260720"
G, CELL = 16, 4.0
ALLPARTS = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea5", "sea4")
ISLAND = {(11, 18), (12, 18), (11, 19), (12, 19)}
CHANGED = {(12, 18): {(14, 14), (14, 15), (15, 14), (15, 15)}}
RANK = ("terrain", "beach1", "sea2", "sea1", "sea3", "sea5", "sea4")
LAB = {"terrain": "land", "beach1": "beach1", "sea2": "sea2", "sea1": "sea1",
       "sea3": "sea3", "sea5": "sea5", "sea4": "sea4"}
COL = {"land": (206, 188, 140), "beach1": (240, 240, 235), "sea2": (150, 226, 224),
       "sea1": (95, 190, 205), "sea3": (70, 150, 180), "sea5": (52, 110, 150),
       "sea4": (30, 52, 92), None: (30, 52, 92)}
BX0, BX1, BY0, BY1 = 10, 13, 18, 19
PX = 16


def _bin(bm):
    g = defaultdict(int)
    for tri in bm.tris:
        i = int((sum(bm.verts[q][0] for q in tri) / 3) // CELL)
        j = int((-sum(bm.verts[q][2] for q in tri) / 3) // CELL)
        if 0 <= i < G and 0 <= j < G:
            g[(i, j)] += 1
    return g


def cell_parts(bx, by, pre):
    """Shade occupancy for a cell.  For (12,18) PRE, the 3 touched parts read from the backup."""
    out = {}
    if (bx, by) in ISLAND:
        rdir = WORLD / "Disc1" / "0_1" / f"r{by}"
        for part in ALLPARTS:
            cap = part.capitalize()
            live = rdir / f"Block[{bx}][{by}] {cap}.ff9mesh"
            bkp = BK / f"Disc1__Block[{bx}][{by}] {cap}.ff9mesh"
            p = bkp if (pre and (bx, by) == (12, 18) and cap in ("Sea1", "Sea2", "Sea5") and bkp.exists()) else live
            if p.exists():
                bm = M.blockmesh_from_ff9mesh(str(p), disc=1, x=bx, y=by, part=part)
                if part == "terrain" and len(bm.tris) <= 1:
                    continue
                g = _bin(bm)
                if g:
                    out[part] = g
        return out
    if 0 <= bx < GRID_X and 0 <= by < GRID_Y:
        for part in ALLPARTS:
            try:
                bm = X.read_block(bx, by, disc=1, part=part)
            except (ValueError, FileNotFoundError):
                continue
            if bm.verts:
                g = _bin(bm)
                if g:
                    out[part] = g
    return out


def shade(parts, i, j):
    if not parts:
        return "sea4"
    for p in RANK:
        if p in parts and (i, j) in parts[p]:
            return LAB[p]
    return None


def panel(pre):
    grids = {(bx, by): cell_parts(bx, by, pre) for by in range(BY0, BY1 + 1) for bx in range(BX0, BX1 + 1)}
    W = (BX1 - BX0 + 1) * G * PX
    H = (BY1 - BY0 + 1) * G * PX
    arr = np.zeros((H, W, 3), np.uint8)
    for by in range(BY0, BY1 + 1):
        for bx in range(BX0, BX1 + 1):
            parts = grids[(bx, by)]
            for i in range(G):
                for j in range(G):
                    sh = shade(parts, i, j)
                    px = ((bx - BX0) * G + i) * PX
                    py = ((by - BY0) * G + j) * PX
                    arr[py:py + PX, px:px + PX] = COL.get(sh, COL[None])
    img = Image.fromarray(arr)
    dr = ImageDraw.Draw(img)
    for bx in range(BX0, BX1 + 2):
        dr.line([((bx - BX0) * G * PX, 0), ((bx - BX0) * G * PX, H)], fill=(255, 235, 120), width=1)
    for by in range(BY0, BY1 + 2):
        dr.line([(0, (by - BY0) * G * PX), (W, (by - BY0) * G * PX)], fill=(255, 235, 120), width=1)
    for (bx, by), cells in CHANGED.items():
        for (i, j) in cells:
            x0 = ((bx - BX0) * G + i) * PX
            y0 = ((by - BY0) * G + j) * PX
            dr.rectangle([x0, y0, x0 + PX - 1, y0 + PX - 1], outline=(255, 40, 40), width=2)
    return img


def main():
    pre = panel(True)
    post = panel(False)
    gap, head = 18, 40
    W, H = pre.size
    sheet = Image.new("RGB", (W * 2 + gap, H + head), (16, 16, 16))
    sheet.paste(pre, (0, head))
    sheet.paste(post, (W + gap, head))
    dr = ImageDraw.Draw(sheet)
    dr.text((6, 6), "SHADE PLAN (flat): land / beach1 / sea2(bright) / sea1 / sea3 / sea5 / sea4(deep). "
                    "red box = the 4 repartitioned cells. island=(11-12,18-19).", fill=(235, 235, 235))
    dr.text((6, 22), "PRE (backup): (15,14)/(15,15)=sea1 face deep=HARD; (14,14)/(14,15)=sea2", fill=(200, 200, 200))
    dr.text((W + gap + 6, 22), "POST (deployed): (15,14)/(15,15)->sea5 E-tip; (14,14)/(14,15)->sea1  "
                               "=> sea2->sea1->sea5->deep", fill=(200, 200, 200))
    out = STUDY / "sea1_ladder_shadeplan.png"
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
