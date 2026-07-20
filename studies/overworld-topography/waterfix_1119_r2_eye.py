"""waterfix_1119_r2_eye.py -- the OFFLINE WATER-TILE EYE for the round-2 Block[11][19] fix.

Renders plan-view (top-down, local frame x[0,64] z[-64,0]) tile mosaics to judge tile COHERENCE:

  PRE     the round-1 MERGED Sea4 (512 tris) -- every tri through the ONE Sea4 caustic texture
          (what the game showed BEFORE this fix): the former-Sea5 quarter-v strips smear into the
          reported STREAKY band at the north seam.
  FINAL   the round-2 RESTORE: each pristine part through ITS OWN texture (Sea3 light / Sea4 deep /
          Sea5 gradient) -- what the divert now binds.  (== "restored-uncorrected": the audit
          mandated NO tile recalculation, so restored and final are the same bytes.)
  DONOR   the stock (8,18) donor block, each part through its own texture -- the GROUND TRUTH.
          FINAL must match DONOR (verbatim carry).

Textures = the real animated caustic tiles (frame 0), copied to the scratchpad by the forensics pass
(sea_tex/: Sea3->10_128_64_0, Sea4->10_128_128_0, Sea5->11_64_0_0).  Judges tile coherence/material
correctness only -- water "quality" (the 4-rotation caustic shuffle) is a human/in-game call.

Run: py studies/overworld-topography/waterfix_1119_r2_eye.py [OUT_DIR]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                              # noqa: E402
from ff9mapkit.world import extract as X                          # noqa: E402

BK1 = REPO / "backups" / "waterfix-1119.20260720"                 # pristine per-layer (== restored)
BK2 = REPO / "backups" / "waterfix-1119-r2.20260720"              # merged Sea4 (pre-fix)
SCRATCH = Path(r"C:/Users/skaki/AppData/Local/Temp/claude"
               r"/C--gd-Dream-World-IX--claude-worktrees-overworld-work-continue-0d139c"
               r"/240477cb-9c70-4795-9c0a-63bcbfc834cd/scratchpad")
TEXDIR = SCRATCH / "sea_tex"
TEX = {"Sea3": "10_128_64_0.png", "Sea4": "10_128_128_0.png", "Sea5": "11_64_0_0.png"}
SC = 12                                                            # px per world unit
OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent


def load_tex(name):
    im = Image.open(TEXDIR / TEX[name]).convert("RGBA")
    return np.asarray(im, dtype=np.float64), im.size


TEXA = {k: load_tex(k) for k in TEX}


def sample(name, u, v):
    arr, (Wt, Ht) = TEXA[name]
    fx = (u % 1.0) * Wt - 0.5
    fy = (1.0 - (v % 1.0)) * Ht - 0.5                              # PNG top row = v=1
    x0, y0 = int(np.floor(fx)), int(np.floor(fy))
    tx, ty = fx - x0, fy - y0
    acc = np.zeros(3)
    for dx, dy, wg in ((0, 0, (1-tx)*(1-ty)), (1, 0, tx*(1-ty)), (0, 1, (1-tx)*ty), (1, 1, tx*ty)):
        px, py = min(max(x0+dx, 0), Wt-1), min(max(y0+dy, 0), Ht-1)
        acc += arr[py, px, :3] * wg
    return acc


RW, RH = 64 * SC, 64 * SC


def raster(tri_entries):
    img = np.full((RH, RW, 3), (60, 90, 130), dtype=np.float64)
    for texname, tri in tri_entries:
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
                img[py, px] = sample(texname, u, v)
    return img


def entries_from(bm, texture):
    V = np.asarray(bm.verts); U = np.asarray(bm.uvs)
    return [(texture, [(V[k][0], V[k][2], U[k][0], U[k][1]) for k in tri]) for tri in bm.tris]


def load_ff9(path, part):
    return M.blockmesh_from_ff9mesh(str(path), disc=1, x=11, y=19, part=part)


# ---- PRE: merged Sea4 all through Sea4 texture ----
merged = load_ff9(BK2 / "Disc1__Block[11][19] Sea4.ff9mesh", "sea4")
pre = raster(entries_from(merged, "Sea4"))

# ---- FINAL: restored per-layer, own textures ----
restored = {p: load_ff9(BK1 / f"Disc1__Block[11][19] {p}.ff9mesh", p.lower()) for p in ("Sea3", "Sea4", "Sea5")}
final = raster(entries_from(restored["Sea4"], "Sea4")
               + entries_from(restored["Sea3"], "Sea3")
               + entries_from(restored["Sea5"], "Sea5"))

# ---- DONOR: stock (8,18) per-layer, own textures (ground truth) ----
donor = {p: X.read_block(8, 18, disc=1, part=p.lower()) for p in ("Sea3", "Sea4", "Sea5")}
donref = raster(entries_from(donor["Sea4"], "Sea4")
                + entries_from(donor["Sea3"], "Sea3")
                + entries_from(donor["Sea5"], "Sea5"))


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB")


imgs = [to_img(pre), to_img(final), to_img(donref)]
labels = ["PRE  round-1 merged Sea4 (all -> Sea4 tex): STREAKY north band",
          "FINAL  restored per-layer, own textures: coherent",
          "DONOR  stock (8,18) ground truth (FINAL must match)"]
gap, head = 12, 24
sheet = Image.new("RGB", (RW*3 + gap*2, RH + head), (12, 12, 12))
dr = ImageDraw.Draw(sheet)
for i, (im, lb) in enumerate(zip(imgs, labels)):
    sheet.paste(im, (i*(RW+gap), head))
    dr.text((i*(RW+gap)+4, 6), lb, fill=(235, 235, 235))
OUT = OUT_DIR / "waterfix_1119_r2_eye.png"
sheet.save(OUT)

# byte cross-check: FINAL should equal DONOR (verbatim carry)
diff = float(np.abs(np.asarray(imgs[1], float) - np.asarray(imgs[2], float)).mean())
print(f"PRE={merged.vcount//3} tris (merged) | FINAL/DONOR per-layer "
      f"Sea3/Sea4/Sea5={[len(restored[p].tris) for p in ('Sea3','Sea4','Sea5')]}")
print(f"FINAL-vs-DONOR mean pixel diff = {diff:.3f} (0 = FINAL renders identically to the stock donor)")
print(f"-> {OUT}")
