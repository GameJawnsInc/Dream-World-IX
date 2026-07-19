"""THE INSTRUMENT CALIBRATION -- is the super-tight unshaded render a valid oracle?

Round 3 (`dunes_strip_emitter.py`) judged a synthesized desert|dunes seam FALSIFIED on the
strength of ONE render: a 24x24u, UNSHADED, scale-32 "super-tight zoom". The reported
difference was that STOCK's boundary reads as a smooth organic coastline while the synthesized
one staircases into boxy notches.

The user looked at that render and observed that the STOCK panel ALSO shows hard edges and
bad connections. If that is right, the render cannot separate "the synthesis is bad" from
"this view makes everything look bad", and the FALSIFIED verdict is unsupported by it.

NOBODY CALIBRATED THE INSTRUMENT. This script does the missing control: render REAL STOCK
terrain that has NO ecotone strip in it at all -- pure single-family mains ground, plus a
stock desert|dunes seam, plus a stock grass|desert seam -- at the IDENTICAL settings the
verdict rested on (24x24u, unshaded, sc=32). Known-good, shipped, in-game-correct FF9 ground.

THE TEST: if pure stock mains ground also renders as a hard-edged patchwork of squares, then
the "staircase vs curve" distinction is an artifact of the view, not a property of the data,
and no visual verdict can be drawn at this zoom.

It also measures the thing the eye was being asked to judge: what FRACTION of a rendered
window's colour discontinuity sits exactly on the 4u cell lattice? Stock ground is literally a
mosaic of 4u textured quads, so at 32x with no shading the lattice is exposed everywhere --
that is the medium, not a defect.

Run from the repo root:  py studies/overworld-topography/render_calibration.py
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import extract as X                    # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
# reuse the EXACT renderer the verdict used -- importing it runs that script, so instead we
# lift its two rendering primitives by exec'ing only the function defs we need.
import importlib.util                                       # noqa: E402

OUTD = Path(__file__).with_name("out")
OUTD.mkdir(exist_ok=True)
SRC = Path(__file__).with_name("dunes_strip_emitter.py").read_text(encoding="utf-8")

# pull the renderer + sheet helpers verbatim out of the round-3 script without executing its
# analysis body (everything before the first top-level statement after the defs we want).
NS = {"__file__": str(Path(__file__).with_name("dunes_strip_emitter.py"))}
exec(compile(
    "\n".join(SRC.split("\n")[:SRC.split("\n").index("def world_tris_override(bm, bx, by, row_override):")]),
    "<prelude>", "exec"), NS)
_start = SRC.split("\n").index("def world_tris_override(bm, bx, by, row_override):")
_lines = SRC.split("\n")
_end = next(i for i in range(_start + 1, len(_lines))
            if _lines[i].startswith("# ====") or _lines[i].startswith("print(\n"))
exec(compile("\n".join(_lines[_start:_end]), "<render>", "exec"), NS)
render_plan, sheet = NS["render_plan"], NS["sheet"]

FAM_OF = {}
for t in (0, 1, 2, 3, 10, 11, 12, 13, 42):
    FAM_OF[t] = "grass"
for t in (4, 5, 6):
    FAM_OF[t] = "scrub"
for t in (17, 16, 19, 20):
    FAM_OF[t] = "desert"
FAM_OF[38] = "brush"
FAM_OF[41] = "dunes"


def block_of(bx, by):
    try:
        return X.read_block(bx, by, disc=1, part="terrain")
    except ValueError:
        return None


def nbrs(bx, by):
    out = {}
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            bm = block_of(bx + dx, by + dy)
            if bm is not None:
                out[(bx + dx, by + dy)] = bm
    return out


def fam_census(bx, by):
    bm = block_of(bx, by)
    if bm is None:
        return Counter()
    c = Counter()
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        c[FAM_OF.get(topo, f"topo{topo}")] += 1
    return c


# ---- A. pick specimens -----------------------------------------------------------------------
print("A. specimen selection (all pure-STOCK, row_override=None everywhere)\n")

# a PURE single-family interior block: desert only, no dunes, no strip pair
pure_candidates = []
for bx in range(24):
    for by in range(20):
        c = fam_census(bx, by)
        if not c:
            continue
        fams = {k for k in c if not k.startswith("topo")}
        if fams == {"desert"} and c["desert"] > 300:
            pure_candidates.append((bx, by, c["desert"]))
pure_candidates.sort(key=lambda t: -t[2])
print(f"   pure-DESERT-only blocks (no other walkable family present): {len(pure_candidates)}")
for t in pure_candidates[:6]:
    print(f"     block {t[0], t[1]}  desert tris={t[2]}")

# a pure GRASS-only block as a second, different-family control
pure_grass = []
for bx in range(24):
    for by in range(20):
        c = fam_census(bx, by)
        if not c:
            continue
        fams = {k for k in c if not k.startswith("topo")}
        if fams == {"grass"} and c["grass"] > 300:
            pure_grass.append((bx, by, c["grass"]))
pure_grass.sort(key=lambda t: -t[2])
print(f"   pure-GRASS-only blocks: {len(pure_grass)}")
for t in pure_grass[:4]:
    print(f"     block {t[0], t[1]}  grass tris={t[2]}")

SPECIMENS = []
if pure_candidates:
    bx, by, _ = pure_candidates[0]
    SPECIMENS.append((f"STOCK pure DESERT interior {bx, by} (NO strip)", bx, by))
if pure_grass:
    bx, by, _ = pure_grass[0]
    SPECIMENS.append((f"STOCK pure GRASS interior {bx, by} (NO strip)", bx, by))
SPECIMENS.append(("STOCK desert|dunes seam (18,3) -- the round-3 specimen", 18, 3))
SPECIMENS.append(("STOCK grass|desert seam (15,11)", 15, 11))

# ---- B. render each at the EXACT round-3 verdict settings --------------------------------------
print("\nB. rendering each specimen at the round-3 settings: 24x24u window, UNSHADED, sc=32")
panels = []
for label, bx, by in SPECIMENS:
    blocks = nbrs(bx, by)
    cx, cz = (bx * 64.0 + 32.0), -(by * 64.0 + 32.0)
    tex, com, nread = render_plan(blocks, cx, cz, 24, 24, sc=32, row_override=None)
    print(f"   {label}: centre ({cx:.0f},{cz:.0f}), {nread}/9 neighbours read")
    panels.append((label, tex))

sheet(panels, cols=2, cell_w=768, cell_h=768,
      path=OUTD / "render_calibration_pure_stock.png",
      title="INSTRUMENT CALIBRATION -- ALL FOUR PANELS ARE 100% STOCK, UNMODIFIED "
            "(24x24u, UNSHADED, sc=32 -- the exact settings the round-3 FALSIFIED verdict rested on)")
print(f"\n   wrote {OUTD / 'render_calibration_pure_stock.png'}")

# ---- C. quantify the lattice exposure ----------------------------------------------------------
# How much of the rendered colour discontinuity lies ON the 4u cell lattice? If stock ground is
# a 4u mosaic, a 24u window at sc=32 shows a 6x6 grid of cells, each 128px, and the strongest
# gradients should pile up on those seams -- in STOCK, with no synthesis anywhere.
print("\nC. lattice-exposure measure -- what fraction of strong colour edges sit ON the 4u grid?")
print("   (100% stock inputs; a high number means the view EXPOSES the tile mosaic by construction)")
for label, bx, by in SPECIMENS:
    blocks = nbrs(bx, by)
    cx, cz = (bx * 64.0 + 32.0), -(by * 64.0 + 32.0)
    tex, com, _ = render_plan(blocks, cx, cz, 24, 24, sc=32, row_override=None)
    a = np.asarray(tex.convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(a, axis=1))
    h, w = gx.shape
    px_per_cell = w / 6.0                     # 24u window / 4u cells = 6 cells across
    cols = np.arange(w)
    # distance from each column to the nearest cell boundary
    d = np.minimum(cols % px_per_cell, px_per_cell - (cols % px_per_cell))
    on_lat = d <= 2.0
    strong = gx > np.percentile(gx, 99.0)     # the top 1% strongest horizontal edges
    frac_on = strong[:, on_lat].sum() / max(1, strong.sum())
    frac_area = on_lat.sum() / w
    lift = frac_on / max(1e-9, frac_area)
    print(f"   {label[:52]:54s} strong-edge mass on lattice={frac_on:5.1%} "
          f"(lattice is {frac_area:4.1%} of area -> {lift:4.1f}x enrichment)")

print("\nDONE. Open out/render_calibration_pure_stock.png -- every panel is unmodified stock.")
print("If those panels show the same hard edges / boxy connections the round-3 SYNTH panel was")
print("faulted for, then the super-tight unshaded view cannot support a look verdict, and the")
print("round-3 FALSIFIED call is UNSUPPORTED BY ITS OWN EVIDENCE (it may still be true --")
print("but this render does not show it).")


# ============================================================================================
# D. THE MISSING CONTROL: STOCK vs STOCK.
# Round 3 judged "synth staircases where stock curves" by eyeballing ONE stock window against
# ONE synth window. Nobody ever asked how much STOCK VARIES AGAINST ITSELF. If two different
# stock desert|dunes windows differ from each other as much as stock differed from synth, the
# test has no resolving power and the verdict is unsupported regardless of which way it went.
# ============================================================================================
print("\n\nD. THE MISSING CONTROL -- stock vs stock (all panels unmodified stock, different windows)")
sc_cells = [c for c in []] if False else None

# find the real desert|dunes strip cells again, cheaply, to pick several genuine seam windows
seam_pts = []
for (bx, by) in [(13, 11), (13, 12), (14, 11), (14, 12), (18, 3), (18, 4), (19, 3), (19, 4), (20, 3)]:
    bm = block_of(bx, by)
    if bm is None:
        continue
    ps = bm.chan_arrays[X.CH_POS]
    fams = {}
    for tri in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        topo = X.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
        f = FAM_OF.get(topo)
        if f not in ("desert", "dunes"):
            continue
        cx_ = sum(ps[i][0] for i in tri) / 3 + 64.0 * bx
        cz_ = sum(ps[i][2] for i in tri) / 3 - 64.0 * by
        key = (int(cx_ // 4), int(cz_ // 4))
        fams.setdefault(key, set()).add(f)
    for key, s in fams.items():
        if len(s) == 2:                       # a cell carrying BOTH families = a real seam cell
            seam_pts.append((key[0] * 4 + 2.0, key[1] * 4 + 2.0, (bx, by)))
seam_pts.sort()
print(f"   genuine mixed desert|dunes cells found: {len(seam_pts)}")

# spread the picks out so the windows do not overlap
picks, used = [], []
for (px, pz, blk) in seam_pts:
    if all((px - qx) ** 2 + (pz - qz) ** 2 > 40.0 ** 2 for qx, qz, _ in used):
        used.append((px, pz, blk))
        picks.append((px, pz, blk))
    if len(picks) == 4:
        break
print(f"   non-overlapping stock seam windows selected: {len(picks)}")

panels_svs = []
for n, (px, pz, blk) in enumerate(picks, 1):
    blocks = nbrs(*blk)
    tex, com, nread = render_plan(blocks, px, pz, 24, 24, sc=32, row_override=None)
    print(f"   STOCK seam window #{n}: block {blk} centre ({px:.0f},{pz:.0f}), {nread}/9 read")
    panels_svs.append((f"STOCK #{n} -- block {blk} @ ({px:.0f},{pz:.0f}) -- UNMODIFIED", tex))

if panels_svs:
    sheet(panels_svs, cols=2, cell_w=768, cell_h=768,
          path=OUTD / "render_calibration_stock_vs_stock.png",
          title="STOCK vs STOCK -- EVERY PANEL IS UNMODIFIED REAL TERRAIN, 4 different "
                "desert|dunes seam windows (24x24u, UNSHADED, sc=32). How much does stock vary "
                "against ITSELF at the zoom the round-3 verdict used?")
    print(f"\n   wrote {OUTD / 'render_calibration_stock_vs_stock.png'}")
    print("   If these 4 all-stock panels differ from EACH OTHER about as much as the round-3")
    print("   STOCK panel differed from its SYNTH panel, the round-3 look test had no resolving")
    print("   power and its FALSIFIED verdict is not supported by that render.")
