import sys, tempfile
from pathlib import Path
from PIL import Image
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/inspiring-wing-600ac9/ff9mapkit")
from ff9mapkit.workspace import placedoc
d = Path(tempfile.mkdtemp(dir=r"<SCRATCH>/review/place-code"))
# editable-fork-shaped layers: tight crops with position/size, 4x upscale
Image.new("RGBA",(384*4,448*4),(200,0,0,255)).save(d/"layer_04000_None.png")
Image.new("RGBA",(32*4,48*4),(0,0,255,255)).save(d/"layer_00100_None.png")
Image.new("RGBA",(384*4,448*4),(0,200,0,255)).save(d/"cam1.png")
class P:
    raw={"layers":[{"image":"layer_04000_None.png","z":4000,"position":[0,0],"size":[384,448]},
                   {"image":"layer_00100_None.png","z":100,"position":[200,300],"size":[32,48]},
                   {"image":"cam1.png","z":3000,"camera":1}]}
    def path(self, r): return d/r
for cam in (0,1):
    out = placedoc._project_backdrop(P(), cam)
    im = Image.open(out); print("cam", cam, "->", out, im.size, "pixel(0,0)=", im.getpixel((0,0)))
print("written into project dir:", sorted(p.name for p in d.iterdir()))
