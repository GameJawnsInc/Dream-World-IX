#!/usr/bin/env python3
"""Re-composite a real field's background from atlas.png + .bgs (offline art decode test).
Usage: py tools/composite_test.py [tile_size]   (default 64 = Steam 4x atlas)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
from ff9mapkit.scene import bgs
from PIL import Image

D = os.path.join(os.path.dirname(__file__), "scroll_out", "p0spike")
data = open(os.path.join(D, "fbg_n21_grgr_map420_gr_cen_0.bgs.bytes"), "rb").read()
atlas = Image.open(os.path.join(D, "atlas.png")).convert("RGBA")
TILE = int(sys.argv[1]) if len(sys.argv) > 1 else 64

h, overlays = bgs.parse_overlays(data)
bgs.resolve_sprites(data, overlays, atlas.width, tile_size=TILE)
print(f"atlas {atlas.size}  overlays={len(overlays)}  sprites/overlay={[len(o.sprites) for o in overlays]}")
allspr = [s for o in overlays for s in o.sprites]
if not allspr:
    print("no sprites parsed"); sys.exit(1)
SW = TILE
gMinX = min(s.offX for s in allspr); gMaxX = max(s.offX + 16 for s in allspr)
gMinY = min(s.offY for s in allspr); gMaxY = max(s.offY + 16 for s in allspr)
W = (gMaxX - gMinX) // 16 * SW; H = (gMaxY - gMinY) // 16 * SW
print(f"sprite extent X[{gMinX},{gMaxX}] Y[{gMinY},{gMaxY}] -> composite {W}x{H}")
canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
for o in sorted(overlays, key=lambda o: -(o.curZ + o.orgZ)):          # back-to-front
    for s in o.sprites:
        tile = atlas.crop((s.atlasX, s.atlasY, s.atlasX + SW, s.atlasY + SW))
        canvas.alpha_composite(tile, ((s.offX - gMinX) // 16 * SW, (s.offY - gMinY) // 16 * SW))
out = os.path.join(D, f"COMPOSITE_grgr_tile{TILE}.png")
canvas.save(out)
print("wrote", out)
