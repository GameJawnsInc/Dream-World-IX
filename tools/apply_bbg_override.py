#!/usr/bin/env python3
"""STEP-1 PROBE (apply): recolor a battle background's textures and drop them into the live
FF9CustomMap battle-texture override path, to prove Memoria's on-disc override (no engine rebuild).

Target path (derived from ModelFactory.CreateModel checkTextureOnDisc=true +
AssetManager.SearchAssetOnDisc bundle branch, GetBelongingBundleFilename matches "BattleMap/"):
  <game>/FF9CustomMap/StreamingAssets/Assets/Resources/BattleMap/BattleModel/battleMap_all/<BBG>/<texname>.png
where <texname> == the runtime material.mainTexture.name == the bundle Texture2D m_Name.

These are NEW files added to the mod folder (they do not overwrite any base-game file), so reverting
= deleting the override folder. A revert script is emitted next to this one.

Usage:  py tools/apply_bbg_override.py BBG_B013 [pattern]
  pattern = checker (default) | magenta
Reads originals from tools/scroll_out/bbg_probe/<bbg>/  (run probe_bbg_textures.py first).
"""
import colorsys
import os
import sys
import tomllib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
KIT = str(HERE.parent / "ff9mapkit")
sys.path.insert(0, KIT)
from ff9mapkit.config import find_game_path  # noqa: E402


def _mod_folder():
    """Per-worktree mod folder (matches deploy_field.py): $FF9_MOD_FOLDER > .ff9deploy.toml > FF9CustomMap."""
    f = HERE.parent / ".ff9deploy.toml"
    if f.is_file():
        try:
            return tomllib.loads(f.read_text(encoding="utf-8")).get("mod_folder")
        except Exception:
            pass
    return None


MOD_FOLDER = os.environ.get("FF9_MOD_FOLDER") or _mod_folder() or "FF9CustomMap"

bbg = sys.argv[1] if len(sys.argv) > 1 else "BBG_B013"
pattern = sys.argv[2] if len(sys.argv) > 2 else "checker"
src = HERE / "scroll_out" / "bbg_probe" / bbg.lower()
originals = sorted(src.glob("*.png"))
if not originals:
    sys.exit(f"no originals in {src} -- run first:  py tools/probe_bbg_textures.py {bbg}")


def _font(size):
    for p in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def magenta(im: Image.Image, idx: int) -> Image.Image:
    """Vivid magenta tint: R=B=255, G carries faint luminance, alpha preserved."""
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    full = Image.new("L", im.size, 255)
    faint = lum.point(lambda v: v // 3)
    return Image.merge("RGBA", (full, faint, full, a))


def checker(im: Image.Image, idx: int) -> Image.Image:
    """UV test pattern: a bold checkerboard in a per-texture hue with the texture index drawn big.
    Reveals UV wrapping/stretching across the 3D surfaces and which image maps where. Original
    alpha preserved so cutout regions (foliage) still show the geometry silhouette + sky behind."""
    a = im.convert("RGBA").split()[3]
    w, h = im.size
    hue = idx / 8.0
    bright = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.85, 1.0))
    dark = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.90, 0.40))
    cell = max(8, w // 8)
    base = Image.new("RGB", (w, h))
    px = base.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = bright if ((x // cell) + (y // cell)) % 2 == 0 else dark
    d = ImageDraw.Draw(base)
    d.text((w * 0.30, h * 0.18), str(idx), fill=(255, 255, 255), font=_font(int(h * 0.6)))
    out = base.convert("RGBA")
    out.putalpha(a)
    return out


make = {"checker": checker, "magenta": magenta}[pattern]
game = find_game_path()
dst = (game / MOD_FOLDER / "StreamingAssets" / "Assets" / "Resources"
       / "BattleMap" / "BattleModel" / "battleMap_all" / bbg)
dst.mkdir(parents=True, exist_ok=True)
for p in originals:
    digits = "".join(ch for ch in p.stem if ch.isdigit())
    idx = int(digits) if digits else 0
    out = dst / p.name
    make(Image.open(p), idx).save(out)
    print("wrote", out)

revert = HERE / "scroll_out" / f"revert_bbg_override_{bbg}.py"
revert.write_text(
    "#!/usr/bin/env python3\n"
    "import shutil\nfrom pathlib import Path\n"
    f"d = Path(r\"{dst}\")\n"
    "shutil.rmtree(d, ignore_errors=True)\n"
    f"print('reverted: removed battle-texture override', d)\n",
    encoding="utf-8", newline="\n")
print(f"\n{len(originals)} '{pattern}' textures -> {dst}")
print(f"revert (delete override): py {revert}")
print(f"NOTE: override is GLOBAL to {bbg} within mod folder {MOD_FOLDER} -- any battle using it "
      f"(scene 67 = Evil Forest for BBG_B013) shows it.")
