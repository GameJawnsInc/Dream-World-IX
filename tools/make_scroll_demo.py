#!/usr/bin/env python3
"""Phase-3 setup: generate a paint guide + field.toml scaffold for a 2x-wide SCROLLING room.

Produces, in ff9mapkit/examples/scroll-demo/:
  * art/paint_template.png  — transparent trace-over guide (full 768x448 canvas, 4x) showing the
    walkable floor outline + perspective grid + canvas border. Paint your room on layers UNDER it.
  * art/paint_guide.png     — opaque checkerboard reference (same framing).
  * scroll_demo.field.toml  — the build recipe: [camera.scroll] + the matching walkmesh quad.

The human paints art/back.png (the whole scene: floor + walls) and optionally art/front.png
(foreground occluders, small z). Then:  ff9mapkit build .../scroll_demo.field.toml

Run:  python tools/make_scroll_demo.py
"""
import os, sys
from pathlib import Path

KIT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit")))
sys.path.insert(0, str(KIT))
from ff9mapkit.scene import cam as C, guide as G

DEMO = KIT / "examples" / "scroll-demo"
ART = DEMO / "art"
ART.mkdir(parents=True, exist_ok=True)

# ---- camera: 2x-wide painting, normal focal length, scroll bounds ----
PITCH, DIST, FOVX, YAW = 40.0, 4500.0, 42.2, 0.0
WIN_W, RANGE_W, RANGE_H = 384, 768, 448
VIEWPORT = C.scroll_bounds((RANGE_W, RANGE_H))
proj = G.proj_from_fov_x(FOVX, WIN_W)
cam = G.make_camera(PITCH, DIST, proj=proj, yaw_deg=YAW, range_wh=(RANGE_W, RANGE_H), viewport=VIEWPORT)

def cv(x, z):
    return C.to_canvas((x, 0, z), cam)

# ---- frame a WIDE floor in the lower portion (leaving the top half for back walls/scenery) ----
BACK_CY, FRONT_CY = 235.0, 432.0
ZB = round(C.solve_z_for_canvasY(cam, BACK_CY))
ZF = round(C.solve_z_for_canvasY(cam, FRONT_CY))

def solve_x_for_cx(target_cx, z, lo=-20000.0, hi=20000.0):
    fa = cv(lo, z)[0] - target_cx
    for _ in range(80):
        m = 0.5 * (lo + hi); fm = cv(m, z)[0] - target_cx
        if abs(fm) < 0.01:
            return m
        if (fm > 0) == (fa > 0):
            lo, fa = m, fm
        else:
            hi = m
    return 0.5 * (lo + hi)

# fill the canvas width at the FRONT row (widest footprint)
FX = round(max(abs(solve_x_for_cx(24.0, ZF)), abs(solve_x_for_cx(RANGE_W - 24.0, ZF))))

frame = G.frame_floor(cam, back_canvas_y=BACK_CY, front_canvas_y=FRONT_CY, half_width=FX)
G.render_paint_template(cam, frame, ART / "paint_template.png", scale=4)
G.render_paint_guide(cam, frame, ART / "paint_guide.png", scale=4, nx=12, nz=5)

# ---- field.toml ----
wm = G.walkmesh_corners(frame)                      # [BL, BR, FR, FL] (x,z)
SPAWN_X, SPAWN_Z = 0, round((ZF + ZB) / 2)
toml = f"""# Scrolling demo room: a 2x-wide (768x448) painting the view pans across.
# Paint art/back.png (the whole scene; floor inside the outline, walls above) and optionally
# art/front.png (foreground occluders). Then:  ff9mapkit build scroll_demo.field.toml
[field]
id = 4003
name = "SCROLLDEMO"
area = 11
text_block = 1073
title = "Scrolling demo"

[camera]
pitch = {PITCH}
distance = {int(DIST)}
fov = {FOVX}
range = [{RANGE_W}, {RANGE_H}]   # the painting is 2x the screen wide
window_width = {WIN_W}           # keep the focal length normal (don't widen the FOV)

[camera.scroll]
enabled = true                   # auto scroll bounds + the engine EnableCameraServices

[walkmesh]
quad = [[{wm[0][0]:.0f},{wm[0][1]:.0f}],[{wm[1][0]:.0f},{wm[1][1]:.0f}],[{wm[2][0]:.0f},{wm[2][1]:.0f}],[{wm[3][0]:.0f},{wm[3][1]:.0f}]]
# character_offset defaults to 298 (auto-framed); explicit quad here defaults to 0. Use 298 to plant.
character_offset = 298

[[layers]]
image = "art/back.png"           # the whole painting (floor + walls + scenery)
z = 4000
# [[layers]]                      # optional foreground occluders (small z draws OVER the player)
# image = "art/front.png"
# z = 8

[player]
spawn = [{SPAWN_X}, {SPAWN_Z}]
"""
(DEMO / "scroll_demo.field.toml").write_text(toml, encoding="utf-8", newline="\n")

# ---- report ----
print(f"camera: pitch {PITCH} fov {FOVX} -> proj {proj}; Range {RANGE_W}x{RANGE_H}; Viewport {VIEWPORT}")
print(f"floor world: x[{-FX}..{FX}]  z[{ZF}..{ZB}]")
print("floor canvas footprint (where the WALKABLE floor sits on the 768x448 painting):")
for nm, (x, z) in zip(("back-L", "back-R", "front-R", "front-L"),
                      [(-FX, ZB), (FX, ZB), (FX, ZF), (-FX, ZF)]):
    print(f"   {nm:8} world=({x},0,{z}) -> canvas {tuple(round(v) for v in cv(x, z))}")
print(f"\nwrote:\n  {ART/'paint_template.png'}  (transparent trace-over, 3072x1792)")
print(f"  {ART/'paint_guide.png'}     (opaque checker reference)")
print(f"  {DEMO/'scroll_demo.field.toml'}")
print("\nPAINT art/back.png at 3072x1792 (RGBA): floor inside the outline, walls/scene above it,"
      "\nfull width — the view scrolls across the whole 768 logical width as you walk.")
