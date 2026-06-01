#!/usr/bin/env python3
# Flatten a field's REAR-most overlay PNG to fully OPAQUE over a chosen fill color.
#
# WHY: pure-.bgx scenes composite their overlays with premultiplied alpha
# (PSX/FieldMap_Abr_None) over the engine's black clear. The rearmost painted
# layer is mostly transparent (e.g. ground.png = 94% transparent), so during the
# global FadeFilter you SEE THROUGH the transparent areas to black -> "looks bad
# as it slowly fades in". Making the rear layer fully opaque (transparent pixels
# -> a solid fill color the human chose) removes the see-through entirely. Pure
# pixel change, full-canvas overlay geometry is untouched (BGSCENE_DEF
# CreateMemoriaOverlay builds the quad from memoriaSize only) -> zero misplacement.
#
# Geometry-neutral: same dimensions, same .bgx Position/Size. Only colors change
# (former transparent area -> fill color; painted content composited on top).
import os, struct, sys
from datetime import datetime
from PIL import Image

GAME = (r"C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap"
        r"/StreamingAssets/assets/resources/FieldMaps")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = HERE + "/hut_out"
BKP  = HERE + "/../backups"

def hex_rgba(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)

def flatten(fbg, png, fill_hex):
    fill = hex_rgba(fill_hex)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for root in (SRC, GAME):
        p = f"{root}/{fbg}/{png}"
        if not os.path.exists(p):
            print(f"  SKIP (missing): {p}"); continue
        # back up original
        tag = "src" if root == SRC else "game"
        bkp = f"{BKP}/{fbg}-{png}.{tag}.{stamp}"
        with open(p, 'rb') as f: open(bkp, 'wb').write(f.read())
        # composite original over opaque fill
        orig = Image.open(p).convert('RGBA')
        canvas = Image.new('RGBA', orig.size, fill)
        canvas.alpha_composite(orig)
        # report alpha BEFORE (so we can confirm it was transparent)
        a0 = orig.getchannel('A'); h0 = a0.histogram(); tot = orig.width*orig.height
        canvas.save(p)
        print(f"  {tag}: {p}")
        print(f"      backup -> {os.path.basename(bkp)}")
        print(f"      was {100*h0[0]/tot:.1f}% transparent -> now fully opaque over {fill_hex}")

if __name__ == "__main__":
    # exterior 'Vivi's Return': rear layer = ground.png (Z=4000), the see-through room
    flatten("FBG_N11_HUT_EXT", "ground.png", "#2d4739")
    print("done. .bgx Position/Size unchanged (geometry-neutral).")
