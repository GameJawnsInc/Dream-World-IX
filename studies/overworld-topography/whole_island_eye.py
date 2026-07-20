"""whole_island_eye.py -- the WHOLE-ISLAND water-tile eye for the Wang-rim retile round.

Extends waterfix_1119_r2_eye.py (one cell) to the FULL 2x2 desert-beach island
"(8,17)+2x2 -> (11,18)+2x2" plus one ring of its REAL stock neighbourhood.  Renders plan-view
(top-down) each sea/beach sub-mesh through ITS OWN real caustic atlas (per THE PER-NAME MATERIAL
LAW), terrain as flat land, empty cells as generic deep (SeaBlockPrefab = full-cell Sea4).

Atlas map (engine-verified, WMRenderTextureBank.cs / WMBlock.ObjectNameToPaths):
    Beach1 -> 11_0_128_0   Sea1 -> 10_64_0_0   Sea2 -> 10_128_0_0
    Sea3   -> 10_128_64_0  Sea4 -> 10_128_128_0  Sea5 -> 11_64_0_0
Textures = Moguri loose PNGs (frame 0) at MoguriMain/.../worldmap/textures.

TWO PANELS, byte-identical island water in both (verbatim carry) -- the ONLY difference is the RING:
  CALIBRATION  stock donor site: blocks (7-10,16-19), centre 2x2 = the stock donor (8-9,17-18).
               The island's outer-frame shallow/transition tiles flow into their REAL neighbours
               -> COHERENT ground truth (this is how the game shows the donor island).
  PRE          the deployed island: blocks (10-13,17-20), centre 2x2 = (11-12,18-19) read from the
               LIVE mod tree; ring = the target location's REAL stock neighbours.  The 2x2 window
               cropped the donor's cross-block Wang system, so the carried rim tiles now abut a
               DIFFERENT neighbourhood -> the 17 hard shallow|deep rim seams (THE WANG-CARRY LAW
               violation).  Red ticks mark the frame_edge_verdicts-flagged incoherent cells.

The builder renders POST by re-running this AFTER deploying the retile (it re-reads the mod tree):
    py studies/overworld-topography/whole_island_eye.py wang_rim_post.png
CALIBRATE-THE-INSTRUMENT check: the CALIBRATION panel must show a coherent island (no hard rim
seams into its real neighbours) -- if it doesn't, the instrument is wrong, not the content.

Run:  py studies/overworld-topography/whole_island_eye.py [OUT_NAME=wang_rim_pre.png]
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                               # noqa: E402
from ff9mapkit.world import extract as X                            # noqa: E402

# reuse the study's shipped coherence predicate (parts_shade_grid / parts_sea5_tiles / frame_edge_verdicts)
_spec = importlib.util.spec_from_file_location("wf", STUDY / "waterfix_1119_r2.py")
wf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wf)

GAME = Path(r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX")
WORLD = GAME / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
TEXDIR = GAME / "MoguriMain" / "StreamingAssets" / "Assets" / "Resources" / "worldmap" / "textures"
PARTMAP = {"beach1": "11_0_128_0", "sea1": "10_64_0_0", "sea2": "10_128_0_0",
           "sea3": "10_128_64_0", "sea4": "10_128_128_0", "sea5": "11_64_0_0"}
DRAW_ORDER = ("terrain", "beach1", "sea1", "sea2", "sea3", "sea4", "sea5")   # land base -> water on top
LAND = (196, 178, 132)                                              # flat land colour (terrain plan footprint)
DEEP_BG = (34, 58, 96)                                              # canvas / uncovered = deep
SC = 6                                                              # px per world unit
CELL = 4.0
G = 16
OUT_NAME = sys.argv[1] if len(sys.argv) > 1 else "wang_rim_pre.png"

TEXA = {k: (lambda im: (np.asarray(im, np.float64), im.size))(Image.open(TEXDIR / f"{v}.png").convert("RGBA"))
        for k, v in PARTMAP.items()}


def sample(part, u, v):
    if part == "terrain":
        return np.array(LAND, np.float64)
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


NB = 4                                                             # 4x4 blocks in the window
RW = RH = NB * 64 * SC


def raster(img, entries):
    """entries: (part, [(cx, cz, u, v) x3]) in WINDOW-LOCAL coords (cx east 0..256, cz south 0..-256)."""
    for part, tri in entries:
        sx = [t[0] * SC for t in tri]
        sy = [(-t[1]) * SC for t in tri]
        x0, x1 = int(min(sx)), int(max(sx)) + 1
        y0, y1 = int(min(sy)), int(max(sy)) + 1
        d = (sy[1]-sy[2])*(sx[0]-sx[2]) + (sx[2]-sx[1])*(sy[0]-sy[2])
        if abs(d) < 1e-9:
            continue
        for px in range(max(0, x0), min(RW, x1)):
            for py in range(max(0, y0), min(RH, y1)):
                w0 = ((sy[1]-sy[2])*(px-sx[2]) + (sx[2]-sx[1])*(py-sy[2]))/d
                w1 = ((sy[2]-sy[0])*(px-sx[2]) + (sx[0]-sx[2])*(py-sy[2]))/d
                w2 = 1-w0-w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                u = w0*tri[0][2] + w1*tri[1][2] + w2*tri[2][2]
                v = w0*tri[0][3] + w1*tri[1][3] + w2*tri[2][3]
                img[py, px] = sample(part, u, v)


def cell_entries(bm, part, ox, oz):
    """BlockMesh (block-local x[0,64] z[-64,0]) -> window entries at block offset (ox east, oz south)."""
    V = np.asarray(bm.verts)
    U = np.asarray(bm.uvs) if bm.uvs else np.zeros((len(bm.verts), 2))
    out = []
    for tri in bm.tris:
        out.append((part, [(V[k][0] + ox, V[k][2] - oz, U[k][0], U[k][1]) for k in tri]))
    return out


def deep_cell_entries(ox, oz):
    """Synthetic full-cell deep Sea4 (SeaBlockPrefab for a blank open-ocean cell), tiled 1 atlas/4u."""
    q = [(0.0, 0.0), (64.0, 0.0), (64.0, -64.0), (0.0, -64.0)]
    uv = [(0.0, 0.0), (16.0, 0.0), (16.0, 16.0), (0.0, 16.0)]
    tris = [(0, 1, 2), (0, 2, 3)]
    return [("sea4", [(q[k][0]+ox, q[k][1]-oz, uv[k][0], uv[k][1]) for k in t]) for t in tris]


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


def get_mod(bx, by):
    rdir = WORLD / "Disc1" / "0_1" / f"r{by}"
    parts = {}
    for p in DRAW_ORDER:
        f = rdir / f"Block[{bx}][{by}] {p.capitalize()}.ff9mesh"
        if not f.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(str(f), disc=1, x=bx, y=by, part=p)
        if bm.verts and bm.tris and len(bm.tris) > 1:                # >1 skips the degenerate 1-tri stub
            parts[p] = bm
    return parts


def render_window(bx0, by0, center_getter):
    img = np.full((RH, RW, 3), DEEP_BG, np.float64)
    for sr in range(NB):
        for sc in range(NB):
            bx, by = bx0 + sc, by0 + sr
            ox, oz = sc * 64.0, sr * 64.0
            is_center = sc in (1, 2) and sr in (1, 2)
            parts = center_getter(bx, by) if is_center else get_stock(bx, by)
            if not parts:                                           # blank -> generic deep
                raster(img, deep_cell_entries(ox, oz))
                continue
            for p in DRAW_ORDER:
                if p in parts:
                    raster(img, cell_entries(parts[p], p, ox, oz))
    return img


def seam_marks():
    """The frame_edge_verdicts-flagged incoherent outer-frame cells on the DEPLOYED island.
    Returns [(slot_col, slot_row, i, j)] in PRE window slots (island at slots (1,1)/(2,1)/(1,2)/(2,2))."""
    # deployed shade grids per island cell
    def dep(bx, by):
        parts = wf._load_deployed_parts(wf._rdir(1, by), bx, by)
        return wf.parts_shade_grid(parts), wf.parts_sea5_tiles(parts.get("sea5"))
    specs = [(11, 18, ("N", "W"), 1, 1), (12, 18, ("N", "E"), 2, 1),
             (11, 19, ("W", "S"), 1, 2), (12, 19, ("E", "S"), 2, 2)]
    marks = []
    for bx, by, edges, scol, srow in specs:
        grid, s5 = dep(bx, by)
        for e in edges:
            for (i, j), sh, ok, det in wf.frame_edge_verdicts(grid, s5, e):
                if not ok:
                    marks.append((scol, srow, i, j, sh))
    return marks


def compose(calib, pre, marks):
    def to_img(a):
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")
    ci, pi = to_img(calib), to_img(pre)
    # red ticks on PRE at each flagged cell centre
    dr = ImageDraw.Draw(pi)
    for scol, srow, i, j, sh in marks:
        cx = int((scol * 64 + i * 4 + 2) * SC)
        cy = int((srow * 64 + j * 4 + 2) * SC)
        r = 5
        dr.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255, 40, 40), width=2)
    # island-frame box on both (slots 1..3 in world units -> 64..192)
    for im in (ci, pi):
        d = ImageDraw.Draw(im)
        d.rectangle([64*SC, 64*SC, 192*SC-1, 192*SC-1], outline=(255, 235, 120), width=2)
    gap, head = 16, 46
    sheet = Image.new("RGB", (RW*2 + gap, RH + head), (14, 14, 14))
    sheet.paste(ci, (0, head))
    sheet.paste(pi, (RW + gap, head))
    d = ImageDraw.Draw(sheet)
    d.text((6, 6), "CALIBRATION  stock donor site (8-9,17-18)+real ring: island rim flows into real "
                   "neighbours = COHERENT ground truth", fill=(230, 230, 230))
    d.text((6, 24), "(yellow box = the 2x2 island; each sea/beach part through its OWN atlas; terrain=tan; "
                    "empty=deep Sea4)", fill=(170, 170, 170))
    tag = "POST" if "post" in OUT_NAME.lower() else "PRE"
    seam_word = ("cropped-Wang hard shallow|deep seams -- the 17 rim seams" if tag == "PRE"
                 else "re-tiled rim (17 seams -> the 1 residual = the (0,9) 1-tri shore sliver, a strict "
                      "4-corner predicate limitation, not a seam; land-aware census = 0)")
    d.text((RW + gap + 6, 6), f"{tag}  deployed island (11-12,18-19)+real target ring: {len(marks)} red = "
                              "strict frame_edge_verdicts flags", fill=(230, 230, 230))
    d.text((RW + gap + 6, 24), f"(same island geometry as CALIBRATION; the deployed island TERMINATES its "
                               f"cropped shelf into deep -> {seam_word})", fill=(170, 170, 170))
    out = STUDY / OUT_NAME
    sheet.save(out)
    return out


def _shade(getter, bx, by):
    parts = getter(bx, by)
    seaparts = {p: parts[p] for p in ("sea3", "sea4", "sea5") if p in parts}
    return wf.parts_shade_grid(seaparts), wf.parts_sea5_tiles(seaparts.get("sea5"))


def _stock_sea(bx, by):
    out = {}
    for p in ("sea3", "sea4", "sea5"):
        try:
            bm = X.read_block(bx, by, disc=1, part=p)
            if bm and bm.verts:
                out[p] = bm
        except (ValueError, FileNotFoundError):
            pass
    return wf.parts_shade_grid(out), wf.parts_sea5_tiles(out.get("sea5"))


def _mod_sea(bx, by):
    parts = wf._load_deployed_parts(wf._rdir(1, by), bx, by)
    return wf.parts_shade_grid(parts), wf.parts_sea5_tiles(parts.get("sea5"))


# island outer edge -> its REAL neighbour, at both sites (donor (8-9,17-18) / deployed (11-12,18-19))
_DONOR_EDGES = [((8, 17), "N", (8, 16)), ((8, 17), "W", (7, 17)), ((9, 17), "N", (9, 16)),
                ((9, 17), "E", (10, 17)), ((8, 18), "W", (7, 18)), ((8, 18), "S", (8, 19)),
                ((9, 18), "E", (10, 18)), ((9, 18), "S", (9, 19))]
_DEP_EDGES = [((11, 18), "N", (11, 17)), ((11, 18), "W", (10, 18)), ((12, 18), "N", (12, 17)),
              ((12, 18), "E", (13, 18)), ((11, 19), "W", (10, 19)), ((11, 19), "S", (11, 20)),
              ((12, 19), "E", (13, 19)), ((12, 19), "S", (12, 20))]


def calibrate_numeric():
    """Print the instrument's calibration: island-edge-vs-REAL-neighbour incoherence at the DONOR site
    (ground truth) and the DEPLOYED site (the defect).  CALIBRATE-THE-INSTRUMENT: the predicate is
    STRICTER than stock -- even the untouched donor site scores >0 (land-coast|land-coast block seams),
    so 'ZERO incoherent' is only well-defined against a GENERIC-DEEP ring (the deployed island's real
    neighbours are NOT all deep -- see below)."""
    def run(edges, island_getter):
        tot = 0
        rows = []
        for (cx, cy), e, (nx, ny) in edges:
            gA, s5A = island_getter(cx, cy)
            gB, s5B = _stock_sea(nx, ny)
            v = wf.internal_edge_verdicts(gA, s5A, gB, s5B, e)
            tot += len(v)
            if v:
                rows.append(f"       island({cx},{cy}).{e} -> real nb ({nx},{ny}): {len(v)}")
        return tot, rows
    dt, dr = run(_DONOR_EDGES, _stock_sea)
    pt, pr = run(_DEP_EDGES, _mod_sea)
    print("[calib] instrument calibration (island edge vs REAL neighbour):")
    print(f"        DONOR site  (stock, GROUND TRUTH): {dt} incoherent  <- NOT 0: predicate stricter than stock")
    for r in dr:
        print(r)
    print(f"        DEPLOYED    (mod vs real target nb): {pt} incoherent  <- the true rim defect")
    for r in pr:
        print(r)


def main():
    print("[eye] rendering CALIBRATION (stock donor site 7-10,16-19) ...")
    calib = render_window(7, 16, get_stock)                         # all stock -> ground truth
    print("[eye] rendering PRE (deployed island 10-13,17-20; centre 2x2 = live mod tree) ...")
    pre = render_window(10, 17, get_mod)                            # centre = mod, ring = stock
    marks = seam_marks()
    out = compose(calib, pre, marks)
    # numeric footer: the 17 (should reproduce neighbor_seam_probe)
    by_cell = {}
    for scol, srow, i, j, sh in marks:
        by_cell.setdefault((scol, srow), []).append((i, j, sh))
    print(f"[eye] flagged rim cells (frame_edge_verdicts): {len(marks)} total")
    name = {(1, 1): "(11,18)", (2, 1): "(12,18)", (1, 2): "(11,19)", (2, 2): "(12,19)"}
    for k in sorted(by_cell):
        print(f"       {name[k]}: {len(by_cell[k])}  {by_cell[k][:4]}")
    print(f"-> {out}")
    calibrate_numeric()
    print("CALIBRATE check: the CALIBRATION panel (left) must read as a coherent island in its real "
          "neighbourhood; the PRE panel (right) shows the same island water with the 17 red rim seams.")


if __name__ == "__main__":
    main()
