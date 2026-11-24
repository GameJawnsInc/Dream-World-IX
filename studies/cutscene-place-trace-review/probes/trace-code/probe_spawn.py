"""Is the generated [player] spawn on the walkmesh for a concave (L / U) traced floor?"""
import shutil
from pathlib import Path
from PIL import Image
from ff9mapkit import imagefield as I
S = Path(r"<SCRATCH>/review/trace-code/spawn")
shutil.rmtree(S, ignore_errors=True); S.mkdir(parents=True)
img = S / "p.png"; Image.new("RGB", (800, 600), (9, 9, 9)).save(img)
def inside(p, poly):
    x, y = p; hit = False
    for i in range(len(poly)):
        ax, ay = poly[i]; bx, by = poly[(i + 1) % len(poly)]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit
shapes = {
  "L (canvas)": [(40, 430), (340, 430), (340, 380), (110, 380), (110, 200), (40, 200)],
  "U (canvas)": [(30, 430), (350, 430), (350, 200), (290, 200), (290, 380), (90, 380), (90, 200), (30, 200)],
}
for nm, fl in shapes.items():
    m = I.build_image_field(img, fl, S / nm[0], name="X", field_id=30500)
    sp = m["spawn"]
    grown = I.outset_polygon(m["world_floor"], I.COLLISION_OUTSET)
    print(nm, "spawn", tuple(round(c) for c in sp), "inside traced floor:", inside(sp, m["world_floor"]),
          "inside walkmesh:", inside(sp, grown))
