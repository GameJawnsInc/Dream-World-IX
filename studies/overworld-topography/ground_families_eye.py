"""THE GROUND FAMILIES EYE -- crop each family's translated atlas regions to a contact
sheet, so the translations can be judged visually offline (snow must look white, canyon
red, scrub scrubby...). Reads the deltas ground_families_anatomy.py measured.

    py studies/overworld-topography/ground_families_eye.py
-> out/ground_families_eye.png  (+ per-region alpha coverage on stdout)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                        # noqa: E402

GP = Path(_cfg.find_game_path(None))
MOG = GP / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / \
    "textures" / "res(1_24)_terrain.png"
atlas = Image.open(MOG).convert("RGBA")
AW, AH = atlas.size

GRASS_MAINS = (0.00391, 0.76855, 0.12695, 0.83008)          # u0,v0,u1,v1
GRASS_WALL = (0.699, 0.893, 0.947, 0.923)

# (name, mains (du,dv), wall band (u0,v_top,u1,v_base) or None)
ROWS = [
    ("grass",    (0.0, 0.0),          (0.69922, 0.89258, 0.94727, 0.92285)),
    ("desert",   (0.65332, -0.09863), (0.42773, 0.87207, 0.67578, 0.90234)),
    ("scrub",    (0.25977, -0.06738), None),
    ("brush", (0.45703, -0.20215), (0.42773, 0.87207, 0.67578, 0.90234)),
    ("snow",     (0.0, -0.33691),     (0.25879, 0.94434, 0.50684, 0.97461)),
    ("canyon",   (0.7793, -0.31641),  (0.00391, 0.39453, 0.25195, 0.42578)),
    ("dunes41",  (0.38964, -0.13477), None),
]


def crop_uv(u0, v0, u1, v1):
    """Atlas crop for a uv rect (v0<v1; pixel y flips v)."""
    px0, px1 = int(u0 * AW), int(u1 * AW) + 1
    py0, py1 = int((1.0 - v1) * AH), int((1.0 - v0) * AH) + 1
    im = atlas.crop((px0, py0, px1, py1))
    a = im.getchannel("A")
    n_blank = sum(1 for p in a.getdata() if p < 24)
    return im, n_blank / max(1, im.width * im.height)


SC = 3
tiles = []
for name, (du, dv), wall in ROWS:
    m = (GRASS_MAINS[0] + du, GRASS_MAINS[1] + dv,
         GRASS_MAINS[2] + du, GRASS_MAINS[3] + dv)
    mi, mb = crop_uv(*m)
    wi, wb = (None, None)
    if wall:
        wi, wb = crop_uv(wall[0], wall[1], wall[2], wall[3])
    print(f"{name:9s} mains {mi.width}x{mi.height}px blank {mb:.1%}"
          + (f" | wall {wi.width}x{wi.height}px blank {wb:.1%}" if wi else " | wall n/a"))
    tiles.append((name, mi, wi))

pad, lab = 8, 18
cw = max(t[1].width * SC for t in tiles) + pad + max((t[2].width * SC if t[2] else 0) for t in tiles)
ch = sum(max(t[1].height, t[2].height if t[2] else 0) * SC + lab + pad for t in tiles)
sheet = Image.new("RGBA", (cw + 2 * pad + 120, ch + pad), (24, 24, 24, 255))
dr = ImageDraw.Draw(sheet)
y = pad
for name, mi, wi in tiles:
    dr.text((pad, y + 4), name, fill=(255, 255, 160, 255))
    x = 120
    big = mi.resize((mi.width * SC, mi.height * SC), Image.NEAREST)
    sheet.paste(big, (x, y + lab))
    x += big.width + pad
    if wi:
        bw = wi.resize((wi.width * SC, wi.height * SC), Image.NEAREST)
        sheet.paste(bw, (x, y + lab))
    y += max(mi.height, wi.height if wi else 0) * SC + lab + pad
OUT = Path(__file__).with_name("out") / "ground_families_eye.png"
sheet.save(OUT)
print(f"-> {OUT}")
