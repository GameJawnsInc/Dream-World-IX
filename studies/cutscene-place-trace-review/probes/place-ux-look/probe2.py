"""_project_backdrop: does it honour layer position/size/camera?"""
import sys
from pathlib import Path
from PIL import Image
from ff9mapkit.workspace import placedoc as P

root = Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True)
Image.new("RGBA", (384, 448), (200, 40, 40, 255)).save(root / "bg_cam0.png")
Image.new("RGBA", (384, 448), (40, 40, 200, 255)).save(root / "bg_cam1.png")
Image.new("RGBA", (32, 32), (40, 200, 40, 255)).save(root / "crate.png")

class Proj:
    def __init__(self, layers): self.raw = {"layers": layers}
    def path(self, ref): return root / ref

layers = [
    {"image": "bg_cam0.png", "z": 4000, "camera": 0},
    {"image": "bg_cam1.png", "z": 3999, "camera": 1},
    {"image": "crate.png", "z": 100, "position": [200, 300], "size": [32, 32], "camera": 0},
]
out = P._project_backdrop(Proj(layers), camera=None)
im = Image.open(out)
print("written to:", out)
print("composite size:", im.size, "(the frame is 384x448)")
print("pixel(0,0):", im.getpixel((0, 0)), " pixel(16,16):", im.getpixel((16, 16)))
layers2 = layers[:2]
im2 = Image.open(P._project_backdrop(Proj(layers2), camera=None))
print("two full-frame cams, size", im2.size, "pixel(10,10):", im2.getpixel((10, 10)), "(cam0 is red, cam1 blue)")
