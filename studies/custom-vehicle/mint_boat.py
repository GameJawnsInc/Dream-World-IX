"""Rung 2: mint the custom hull -- GEO_SUB_W0_DWX (id 6321) from the Blue Narciss (321).

Same rig + same anim keys (5143/5145 resolve through their ANH name tokens to folder 321
regardless of our model's id -- the animation-redirect law), so ONLY the look changes:
every texture is hue-rotated toward crimson (obviously not the stock boat).

Deploys into FF9CustomMap-world: Models/5/6321/ + the 3DModel DictionaryPatch line.
RELAUNCH required once (3DModel registers at launch).

Run: py studies/custom-vehicle/mint_boat.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                          # noqa: E402
from ff9mapkit.models.mint import deploy_mint                         # noqa: E402

MINT_ID = 6321
MINT_NAME = "GEO_SUB_W0_DWX"
SOURCE = "GEO_SUB_W0_008"            # Blue Narciss

game = config.find_game_path(None)
mod = game / "FF9CustomMap-world"

man = deploy_mint(SOURCE, MINT_ID, mod, MINT_NAME)
print("minted:", man["directive"], "->", man["dictionary_patch"])

# crimson-shift every texture in the mint folder (hue rotate; keep alpha)
from PIL import Image
import colorsys

dest = None
for p in (mod / "StreamingAssets").rglob(f"{MINT_ID}.fbx"):
    dest = p.parent
    break
if dest is None:
    sys.exit("mint folder not found after deploy")

def crimson(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            hh = (hh + 0.42) % 1.0                       # rotate hue toward the red/crimson band
            ss = min(1.0, ss * 1.25 + 0.08)              # push saturation so greys pick up the tint
            r2, g2, b2 = colorsys.hls_to_rgb(hh, ll, ss)
            px[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), a)
    return rgba

pngs = sorted(dest.glob("*.png"))
if not pngs:
    sys.exit(f"no textures found in {dest} -- expected the donor's PNGs")
for p in pngs:
    img = Image.open(p)
    crimson(img).save(p)
    print(f"recolored {p.name} ({img.size[0]}x{img.size[1]})")
print(f"done: {len(pngs)} textures crimson-shifted in {dest}")
