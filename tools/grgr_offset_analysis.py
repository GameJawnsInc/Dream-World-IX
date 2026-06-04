#!/usr/bin/env python3
"""Why does the GRGR walkmesh footprint need ~0.52*orgPos to sit on the art?

Pull the real .bgi + .bgs, print the frame fields, and test which clean quantity
reproduces the user's empirical ~f52 offset. Offline; decisive.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
from ff9mapkit import extract
from ff9mapkit.scene import bgs, bgi, cam

FIELD = "grgr_map420_gr_cen"

path, folder, roles, env = extract.find_field(FIELD)
bgs_bytes = extract._raw_bytes(env.container[roles["bgs"]].read())
bgi_bytes = extract._raw_bytes(env.container[roles["bgi"]].read())

wm = bgi.BgiWalkmesh.from_bytes(bgi_bytes)
hdr, overlays = bgs.parse_overlays(bgs_bytes)
bgs.resolve_sprites(bgs_bytes, overlays, 2048, 40)
c0 = bgs.parse_cameras(bgs_bytes)[0]

print(f"=== {folder} ===")
print("BGI frame:")
for nm in ("orgPos", "curPos", "minPos", "maxPos", "charPos"):
    v = getattr(wm, nm)
    print(f"  {nm:8s} = ({v.x:6d}, {v.y:6d}, {v.z:6d})")
vx = [v.x for v in wm.verts]; vy = [v.y for v in wm.verts]; vz = [v.z for v in wm.verts]
print(f"  vert x[{min(vx)},{max(vx)}]  y[{min(vy)},{max(vy)}]  z[{min(vz)},{max(vz)}]  (n={len(wm.verts)})")

b = hdr.bounds  # (orgZ,curZ, orgX,orgY, curX,curY, minX,maxX, minY,maxY, scrX,scrY)
print("\nBGS scene header bounds:")
print(f"  orgZ={b[0]} curZ={b[1]} orgX={b[2]} orgY={b[3]} curX={b[4]} curY={b[5]}")
print(f"  minX={b[6]} maxX={b[7]} minY={b[8]} maxY={b[9]} scrX={b[10]} scrY={b[11]}")

print("\nCamera[0]:")
print(f"  proj={c0.proj} range={c0.range} centerOffset={c0.centerOffset} t={c0.t} depthOffset={c0.depthOffset}")
print(f"  pitch={cam.pitch_deg(c0):.2f} yaw={cam.yaw_deg(c0):.2f}")

# where does the OPAQUE art floor sit on the canvas? use the lowest opaque overlay's painted extent
W, H = c0.range[0], c0.range[1]
print(f"\ncanvas (logical) = {W} x {H}")

# footprint canvas extent at several offsets (fraction of orgPos)
org = (wm.orgPos.x, wm.orgPos.z)
def foot_extent(frac):
    dx, dz = org[0] * frac, org[1] * frac
    xs, ys = [], []
    for v in wm.verts:
        cx, cy = cam.to_canvas((v.x + dx, v.y, v.z + dz), c0)
        xs.append(cx); ys.append(cy)
    return (min(xs), max(xs), min(ys), max(ys))

print("\nfootprint canvas extent vs offset fraction of orgPos:")
for frac in (0.0, 0.40, 0.50, 0.52, 0.60, 0.80, 1.0):
    x0, x1, y0, y1 = foot_extent(frac)
    print(f"  f{int(frac*100):3d}  x[{x0:7.1f},{x1:7.1f}] cx={ (x0+x1)/2:7.1f}   y[{y0:7.1f},{y1:7.1f}] cy={(y0+y1)/2:7.1f}")

# clean-quantity hunt: what world dx,dz centers the footprint on the canvas center (W/2,H/2)?
# solve numerically: footprint centroid vs offset is linear in (dx,dz) per to_canvas.
import statistics
def centroid(dx, dz):
    xs, ys = [], []
    for v in wm.verts:
        cx, cy = cam.to_canvas((v.x + dx, v.y, v.z + dz), c0)
        xs.append(cx); ys.append(cy)
    return statistics.fmean(xs), statistics.fmean(ys)

# the user picked f52 by eye; print the world offset that is
fx = 0.52
# where does the in-game spawn (charPos) land on the canvas via the validated engine projection?
spx, spy = cam.to_canvas((wm.charPos.x, wm.charPos.y, wm.charPos.z), c0)
print(f"\nto_canvas(charPos)  = ({spx:.1f}, {spy:.1f})   (in-game spawn screen pos; canvas {W}x{H} logical)")
spx2, spy2 = cam.to_canvas((0, 0, 0), c0)
print(f"to_canvas(world 0)  = ({spx2:.1f}, {spy2:.1f})")

# where does the OPAQUE art actually sit on the (logical) canvas?
print("\nopaque overlay canvas extents (logical px):")
allx, ally = [], []
for i, o in enumerate(overlays):
    if not o.sprites or o.sprites[0].trans != 0:
        continue
    mnX = min(s.offX for s in o.sprites); mxX = max(s.offX for s in o.sprites) + 16
    mnY = min(s.offY for s in o.sprites); mxY = max(s.offY for s in o.sprites) + 16
    px0 = (b[2] + o.orgX + mnX); px1 = (b[2] + o.orgX + mxX)
    py0 = (b[3] + o.orgY + mnY); py1 = (b[3] + o.orgY + mxY)
    allx += [px0, px1]; ally += [py0, py1]
    print(f"  Overlay{i:2d}  x[{px0:5d},{px1:5d}] y[{py0:5d},{py1:5d}]  z={o.curZ+o.orgZ}")
if allx:
    print(f"  ALL opaque   x[{min(allx)},{max(allx)}] y[{min(ally)},{max(ally)}]")

print(f"\nuser f52 world offset = ({org[0]*fx:.0f}, {org[1]*fx:.0f})")
print(f"  0.5*orgPos          = ({org[0]*0.5:.0f}, {org[1]*0.5:.0f})")
print(f"  orgPos - charPos    = ({wm.orgPos.x - wm.charPos.x}, {wm.orgPos.z - wm.charPos.z})")
print(f"  (orgPos+maxPos)/2   = ({(wm.orgPos.x+wm.maxPos.x)/2:.0f}, {(wm.orgPos.z+wm.maxPos.z)/2:.0f})")
print(f"  -(scene orgX,orgY*?)= scene org ({b[2]},{b[3]})")
