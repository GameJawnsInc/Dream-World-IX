import sys, tempfile, os
from pathlib import Path
from PIL import Image
SCR = Path(r"<SCRATCH>/review/v-place-bugs")
from ff9mapkit.workspace import placedoc as P
from ff9mapkit import build

d = Path(tempfile.mkdtemp(dir=SCR))
Image.new("RGBA", (384, 448), (200, 40, 40, 255)).save(d / "back.png")      # cam0 full bg, far
Image.new("RGBA", (384, 448), (40, 40, 200, 255)).save(d / "cam1.png")      # cam1 full bg
Image.new("RGBA", (32, 48), (40, 200, 40, 255)).save(d / "crop.png")        # near crop
(d / "R.field.toml").write_text(
    '[field]\nid = 30998\nname = "R"\narea = 11\n'
    '[camera]\npitch = 30\ndistance = 3000\n'
    '[[layers]]\nimage = "back.png"\nz = 4000\n'
    '[[layers]]\nimage = "cam1.png"\nz = 3000\ncamera = 1\n'
    '[[layers]]\nimage = "crop.png"\nz = 100\nposition = [200, 300]\nsize = [32, 48]\n', encoding="utf-8")
proj = build.FieldProject.load(str(d / "R.field.toml"))
out = P._project_backdrop(proj, None)
im = Image.open(out)
print("dest:", out)
print("size:", im.size, "pixel(0,0):", im.getpixel((0, 0)))
print("files in project dir:", sorted(os.listdir(d)))
# only the two full-frame layers
(d / "R.field.toml").write_text(
    '[field]\nid = 30998\nname = "R"\narea = 11\n'
    '[[layers]]\nimage = "back.png"\nz = 4000\n'
    '[[layers]]\nimage = "cam1.png"\nz = 3000\ncamera = 1\n', encoding="utf-8")
proj = build.FieldProject.load(str(d / "R.field.toml"))
out = P._project_backdrop(proj, None)
print("two cams, cam0 requested -> pixel(10,10):", Image.open(out).getpixel((10, 10)), "(cam0 red=200,40,40)")
