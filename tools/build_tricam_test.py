#!/usr/bin/env python3
"""Build a 3-CAMERA test field (4003) — multi-camera v2 (N cameras + after-battle restore).

The floor is split into three X-bands, each its own camera + tinted calibration grid:
  LEFT  = camera 2 (GREEN,  yaw -25)
  MID   = camera 0 (CYAN,   yaw  0, spawn here)
  RIGHT = camera 1 (ORANGE, yaw +25)
Walk across the bands -> the view cuts between all three cameras (tint + perspective change), and
WASD stays screen-correct (per-camera control direction). It also has encounters: trigger a battle
while on a non-default camera (e.g. the orange RIGHT band), win, and the camera should be RESTORED
to where you were (not reset to cyan). Calibration grids (not art).

Run:  python tools/build_tricam_test.py
then: python tools/deploy_field.py tools/tricam_out/tricam.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "tricam_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
YAWS = [0.0, 25.0, -25.0]                       # camera 0, 1, 2
FLOOR = [(-1200, -80), (1200, -80), (1200, -1000), (-1200, -1000)]
# X-bands -> camera index (partition the floor; non-overlapping)
BANDS = [(2, -1200, -400), (0, -400, 400), (1, 400, 1200)]    # (camera, x_lo, x_hi)
ZB, ZF = -120, -960
SPAWN = (0, -300)
TINTS = {0: ((70, 150, 210, 255), (40, 90, 140, 255)),       # cyan
         1: ((220, 150, 70, 255), (150, 95, 40, 255)),       # orange
         2: ((90, 210, 110, 255), (55, 140, 70, 255))}       # green
BG = (26, 28, 34, 255)


def grid_for(cam, tint_a, tint_b, nx=12, nz=10):
    W, H = int(cam.range[0] * SCALE), int(cam.range[1] * SCALE)
    buf = bytearray(bytes(BG)) * (W * H)
    x0, x1, z0, z1 = FLOOR[0][0], FLOOR[1][0], FLOOR[0][1], FLOOR[2][1]
    for iz in range(nz):
        for ix in range(nx):
            ax, bx = x0 + (x1 - x0) * ix / nx, x0 + (x1 - x0) * (ix + 1) / nx
            az, bz = z0 + (z1 - z0) * iz / nz, z0 + (z1 - z0) * (iz + 1) / nz
            pts = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam))
                   for (x, z) in ((ax, az), (bx, az), (bx, bz), (ax, bz))]
            P._fill_quad(buf, W, H, pts, tint_a if (ix + iz) % 2 == 0 else tint_b)
    # white band-boundary lines so you can see where the cuts happen
    for _, xlo, xhi in BANDS:
        for bx in (xlo, xhi):
            p0 = tuple(c * SCALE for c in C.to_canvas((bx, 0.0, ZB), cam))
            p1 = tuple(c * SCALE for c in C.to_canvas((bx, 0.0, ZF), cam))
            P.draw_line(buf, W, H, p0, p1, (245, 245, 245, 255), thick=4)
    return W, H, buf


def main():
    cams = [G.make_camera(PITCH, 4500.0, fov_x_deg=FOV, yaw_deg=y) for y in YAWS]
    for k, c in enumerate(cams):
        W, H, buf = grid_for(c, *TINTS[k])
        (OUT / f"grid{k}.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(xlo, xhi):
        return f"[[{xlo}, {ZB}], [{xhi}, {ZB}], [{xhi}, {ZF}], [{xlo}, {ZF}]]"

    cam_blocks = "\n".join(f"[[camera]]\npitch = {PITCH:g}\nfov = {FOV:g}\nyaw = {y:g}" for y in YAWS)
    layer_blocks = "\n".join(f'[[layers]]\nimage = "grid{k}.png"\nz = 4000\ncamera = {k}'
                             for k in range(3))
    zone_blocks = "\n".join(f"[[camera_zone]]\nto_camera = {camk}\nzone = {quad(xlo, xhi)}"
                            for camk, xlo, xhi in BANDS)
    toml = f"""# 3-camera test (field 4003). LEFT=cam2 green, MID=cam0 cyan (spawn), RIGHT=cam1 orange.
[field]
id = 4003
name = "TRICAM"
area = 11
text_block = 1073
title = "3-camera test"

{cam_blocks}

{layer_blocks}

{zone_blocks}

[walkmesh]
quad = [[{FLOOR[0][0]}, {FLOOR[0][1]}], [{FLOOR[1][0]}, {FLOOR[1][1]}], [{FLOOR[2][0]}, {FLOOR[2][1]}], [{FLOOR[3][0]}, {FLOOR[3][1]}]]

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]

[encounter]                 # to test the after-battle camera restore
scene = 67
freq = 160
"""
    p = OUT / "tricam.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("yaws:", [round(C.yaw_deg(c), 1) for c in cams])
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
