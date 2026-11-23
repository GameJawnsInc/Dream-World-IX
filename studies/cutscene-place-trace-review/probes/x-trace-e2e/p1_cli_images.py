"""Probe 1: the real image-field CLI over awkward images + odd paths."""
import os, subprocess, sys, shutil
from pathlib import Path
from PIL import Image, ImageDraw

S = Path(__file__).parent / "p1"
shutil.rmtree(S, ignore_errors=True)
S.mkdir()
KIT = Path(r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")

def room(size, mode="RGB"):
    w, h = size
    img = Image.new("RGB", size, (38, 42, 58))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, int(h * .31)], fill=(52, 56, 76))
    d.polygon([(w*.34, h*.31), (w*.66, h*.31), (w*.95, h*.98), (w*.05, h*.98)], fill=(158, 132, 96))
    return img

imgs = {}
imgs["pano.png"] = room((4000, 1000))
imgs["tall.png"] = room((1080, 2400))
imgs["tiny.png"] = room((64, 64))
imgs["huge.png"] = room((6000, 4000))
rgba = room((800, 600)).convert("RGBA"); px = rgba.load()
for x in range(0, 400):
    for y in range(0, 600):
        px[x, y] = (0, 0, 0, 0)
imgs["rgba.png"] = rgba
imgs["pal.png"] = room((800, 600)).convert("P", palette=Image.ADAPTIVE, colors=16)
imgs["photo.jpg"] = room((800, 600))
imgs["grey.png"] = room((800, 600)).convert("L")
imgs["cmyk.jpg"] = room((800, 600)).convert("CMYK")
imgs["16bit.png"] = room((800, 600)).convert("I;16")
odd = S / "my photos é ü 写真"
odd.mkdir()
for n, im in imgs.items():
    im.save(S / n)
room((800, 600)).save(odd / "room photo é.png")
FLOOR = "60,440 324,440 260,200 124,200"
env = dict(os.environ, PYTHONIOENCODING="utf-8")
def run(img, out, *extra):
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "image-field", str(img), "--floor", FLOOR,
                        "--out", str(out), *extra], cwd=KIT, capture_output=True, text=True,
                       encoding="utf-8", env=env)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()

for n in list(imgs) + ["my photos é ü 写真/room photo é.png"]:
    code, lines = run(S / n, S / ("out-" + Path(n).stem.replace(" ", "_")), "--name", "T", "--id", "30058")
    base = S / ("out-" + Path(n).stem.replace(" ", "_")) / "art" / "base.png"
    info = ""
    if base.is_file():
        b = Image.open(base); info = f"base={b.size} {b.mode}"
    print(f"{n:40s} exit={code} {info} :: {lines[-3:] if code else lines[0]}")
