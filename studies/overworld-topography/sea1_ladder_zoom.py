"""sea1_ladder_zoom.py -- a REAL-ATLAS zoom of the SE sand-spit corner of (12,18), rendered through each
sea/beach part's OWN caustic atlas (THE PER-NAME MATERIAL LAW), for the {sea1,sea5} ladder PRE/POST eye.

Renders a tight window over world cells (i>=10, j>=10) of block (12,18) + the deep E neighbour (13,18) +
the S neighbour (12,19), so the corner ladder (sea2 -> sea1 -> sea5 -> deep) is visible at play-ish scale.
Reads the LIVE mod tree, so a PRE render (before deploy) shows the hard sea1|deep edge and a POST render
(after deploy) shows the graded ladder.  No writes.

Run:  py studies/overworld-topography/sea1_ladder_zoom.py [OUT_NAME=sea1_ladder_zoom_pre.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                               # noqa: E402
from ff9mapkit.world import extract as X                            # noqa: E402

GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
TEXDIR = GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / "worldmap" / "textures"
PARTMAP = {"beach1": "11_0_128_0", "sea1": "10_64_0_0", "sea2": "10_128_0_0",
           "sea3": "10_128_64_0", "sea4": "10_128_128_0", "sea5": "11_64_0_0"}
DRAW_ORDER = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea4", "sea5")
LANDC = (196, 178, 132)
DEEP_BG = (34, 58, 96)
CELL = 4.0
G = 16
SC = 18                                                            # px per world unit (tight zoom)
ISLAND = {(11, 18), (12, 18), (11, 19), (12, 19)}
OUT_NAME = sys.argv[1] if len(sys.argv) > 1 else "sea1_ladder_zoom_pre.png"

# world window: SE of (12,18).  block (12,18) origin world = (768, -1152).  cells i10..15 -> x 808..832;
# j10..15 -> z -1192..-1216.  include (13,18) i0..2 (x 832..844) and (12,19) j0..1 (z -1216..-1224).
WX0, WX1 = 806.0, 846.0                                            # world x span (east)
WZ0, WZ1 = -1224.0, -1188.0                                        # world z span (south..north)
RW = int((WX1 - WX0) * SC)
RH = int((WZ1 - WZ0) * SC)

TEXA = {k: (lambda im: (np.asarray(im, np.float64), im.size))(Image.open(TEXDIR / f"{v}.png").convert("RGBA"))
        for k, v in PARTMAP.items()}


def sample(part, u, v):
    if part == "terrain":
        return np.array(LANDC, np.float64)
    arr, (Wt, Ht) = TEXA[part]
    fx = (u % 1.0) * Wt - 0.5
    fy = (1.0 - (v % 1.0)) * Ht - 0.5
    x0, y0 = int(np.floor(fx)), int(np.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = np.zeros(3)
    for dx, dy, wg in ((0, 0, (1-tx)*(1-ty)), (1, 0, tx*(1-ty)), (0, 1, (1-tx)*ty), (1, 1, tx*ty)):
        px, py = min(max(x0+dx, 0), Wt-1), min(max(y0+dy, 0), Ht-1)
        acc += arr[py, px, :3] * wg
    return acc


def raster(img, part, tri_world):
    """tri_world: [(wx, wz, u, v) x3] in WORLD coords."""
    sx = [(t[0] - WX0) * SC for t in tri_world]
    sy = [(WZ1 - t[1]) * SC for t in tri_world]                   # world z up -> screen y down
    x0, x1 = int(min(sx)), int(max(sx)) + 1
    y0, y1 = int(min(sy)), int(max(sy)) + 1
    d = (sy[1]-sy[2])*(sx[0]-sx[2]) + (sx[2]-sx[1])*(sy[0]-sy[2])
    if abs(d) < 1e-9:
        return
    for px in range(max(0, x0), min(RW, x1)):
        for py in range(max(0, y0), min(RH, y1)):
            w0 = ((sy[1]-sy[2])*(px-sx[2]) + (sx[2]-sx[1])*(py-sy[2]))/d
            w1 = ((sy[2]-sy[0])*(px-sx[2]) + (sx[0]-sx[2])*(py-sy[2]))/d
            w2 = 1-w0-w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            u = w0*tri_world[0][2] + w1*tri_world[1][2] + w2*tri_world[2][2]
            v = w0*tri_world[0][3] + w1*tri_world[1][3] + w2*tri_world[2][3]
            img[py, px] = sample(part, u, v)


def cell_world(bm, part, bx, by):
    ox, oz = bx * 64.0, -by * 64.0
    V = np.asarray(bm.verts)
    U = np.asarray(bm.uvs) if bm.uvs else np.zeros((len(bm.verts), 2))
    for tri in bm.tris:
        yield (part, [(V[k][0] + ox, V[k][2] + oz, U[k][0], U[k][1]) for k in tri])


def deep_world(bx, by):
    ox, oz = bx * 64.0, -by * 64.0
    q = [(0.0, 0.0), (64.0, 0.0), (64.0, -64.0), (0.0, -64.0)]
    uv = [(0.0, 0.0), (16.0, 0.0), (16.0, 16.0), (0.0, 16.0)]
    for t in ((0, 1, 2), (0, 2, 3)):
        yield ("sea4", [(q[k][0]+ox, q[k][1]+oz, uv[k][0], uv[k][1]) for k in t])


def get_mod(bx, by):
    rdir = WORLD / "Disc1" / "0_1" / f"r{by}"
    parts = {}
    for p in DRAW_ORDER:
        f = rdir / f"Block[{bx}][{by}] {p.capitalize()}.ff9mesh"
        if f.exists():
            bm = M.blockmesh_from_ff9mesh(str(f), disc=1, x=bx, y=by, part=p)
            if bm.verts and bm.tris and len(bm.tris) > 1:
                parts[p] = bm
    return parts


def get_stock(bx, by):
    parts = {}
    for p in DRAW_ORDER:
        try:
            bm = X.read_block(bx, by, disc=1, part=p)
        except (ValueError, FileNotFoundError):
            bm = None
        if bm is not None and bm.verts and bm.tris:
            parts[p] = bm
    return parts


def main():
    img = np.full((RH, RW, 3), DEEP_BG, np.float64)
    for bx, by in [(12, 18), (13, 18), (12, 19), (11, 18), (13, 19), (11, 19), (12, 17), (13, 17)]:
        parts = get_mod(bx, by) if (bx, by) in ISLAND else get_stock(bx, by)
        if not parts:
            for part, tri in deep_world(bx, by):
                raster(img, part, tri)
            continue
        for p in DRAW_ORDER:
            if p in parts:
                for part, tri in cell_world(parts[p], p, bx, by):
                    raster(img, part, tri)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")
    dr = ImageDraw.Draw(im)
    # mark the block seam (12,18)|(13,18) at world x=832 and the 2 fixed sub-cells' E edge
    xseam = int((832.0 - WX0) * SC)
    dr.line([(xseam, 0), (xseam, RH)], fill=(255, 235, 120), width=1)
    for (i, j) in ((15, 14), (15, 15)):                           # the 2 hard->fixed sub-cells
        wz0 = -(18 * 64 + j * CELL); wz1 = wz0 - CELL
        y0 = int((WZ1 - wz0) * SC); y1 = int((WZ1 - wz1) * SC)
        dr.rectangle([xseam - 2, y0, xseam + 2, y1], outline=(255, 80, 80), width=1)
    tag = "POST" if "post" in OUT_NAME.lower() else "PRE"
    dr.text((4, 4), f"{tag}: SE corner of (12,18) through REAL atlases. yellow=(12,18)|(13,18) block seam; "
                    f"red=the 2 fixed sub-cells (15,14)/(15,15).E", fill=(255, 255, 255))
    dr.text((4, 16), "goal POST: sea2(bright)->sea1->sea5(gradient)->sea4(deep), no hard shallow|deep cut",
            fill=(220, 220, 220))
    out = STUDY / OUT_NAME
    im.save(out)
    print("wrote", out, im.size)


if __name__ == "__main__":
    main()
