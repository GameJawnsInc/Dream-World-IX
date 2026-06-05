#!/usr/bin/env python3
"""Build a 2-CAMERA switch test field (4003) to prove multi-camera in-game.

A single flat floor viewed by TWO cameras (camera 0 head-on, camera 1 yawed). Each camera gets its
own calibration grid, tinted a different colour (cam 0 = COOL/cyan, cam 1 = WARM/orange) and via the
kit's EXACT `to_canvas` projection, so the floor lines land where the player walks. A bright-green
switch zone is drawn on each grid: walk into the green box to cut to the other camera. Crossing back
cuts back. The colour change + re-projected grid = an unmistakable in-game proof of the camera cut,
and the player still walking straight after the cut proves the per-camera control direction.

Run:  python tools/build_multicam_test.py
then: python tools/deploy_field.py tools/multicam_out/multicam.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "multicam_out"
OUT.mkdir(exist_ok=True)

PITCH, DIST, FOV = 45.0, 4500.0, 42.2
YAW0, YAW1 = 0.0, 35.0
SCALE = 4

# shared flat floor (world x,z); zones partition it left/right
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]   # (x, z) corners
FWD_ZONE = [(400, -350), (1100, -350), (1100, -1300), (400, -1300)]    # right -> camera 1
REV_ZONE = [(-1100, -350), (-400, -350), (-400, -1300), (-1100, -1300)]  # left -> camera 0
SPAWN = (0, -800)

COOL_A, COOL_B = (70, 150, 210, 255), (40, 90, 140, 255)      # camera 0 (blue)
WARM_A, WARM_B = (220, 150, 70, 255), (150, 95, 40, 255)      # camera 1 (orange)
GREEN = (60, 240, 90, 255)
BACKDROP = (28, 30, 36, 255)


def make_grid(camera, png_path, ca, cb, zone, nx=10, nz=10):
    """A checkerboard of the floor quad projected through `camera` (exact to_canvas), tinted (ca/cb),
    plus a green outline of the switch `zone`. Calibration art -- NOT painting."""
    W, H = int(camera.range[0] * SCALE), int(camera.range[1] * SCALE)
    buf = bytearray(bytes(BACKDROP)) * (W * H)
    x0, x1 = FLOOR[0][0], FLOOR[1][0]
    z0, z1 = FLOOR[0][1], FLOOR[2][1]
    for iz in range(nz):
        for ix in range(nx):
            ax, bx = x0 + (x1 - x0) * ix / nx, x0 + (x1 - x0) * (ix + 1) / nx
            az, bz = z0 + (z1 - z0) * iz / nz, z0 + (z1 - z0) * (iz + 1) / nz
            pts = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), camera))
                   for (x, z) in ((ax, az), (bx, az), (bx, bz), (ax, bz))]
            P._fill_quad(buf, W, H, pts, ca if (ix + iz) % 2 == 0 else cb)
    # green switch-zone outline
    zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), camera)) for (x, z) in zone]
    for i in range(4):
        P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], GREEN, thick=6)
    png_path.write_bytes(P._png_rgba(W, H, buf))


def main():
    cam0 = G.make_camera(PITCH, DIST, fov_x_deg=FOV, yaw_deg=YAW0)
    cam1 = G.make_camera(PITCH, DIST, fov_x_deg=FOV, yaw_deg=YAW1)
    make_grid(cam0, OUT / "grid_cam0.png", COOL_A, COOL_B, FWD_ZONE)   # cam0 shows where to switch -> 1
    make_grid(cam1, OUT / "grid_cam1.png", WARM_A, WARM_B, REV_ZONE)   # cam1 shows where to switch -> 0

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Multi-camera switch test (field 4003). Camera 0 (cyan, head-on) <-> camera 1 (orange, yaw {YAW1:g}).
# Walk into the GREEN box to cut to the other camera; the colour + re-projected grid prove the cut,
# and walking straight afterward proves the per-camera control direction. Calibration grids (not art).
[field]
id = 4003
name = "MULTICAM"
area = 11
text_block = 1073
title = "Multi-camera switch test"

[[camera]]
pitch = {PITCH:g}
yaw = {YAW0:g}
fov = {FOV:g}
[[camera]]
pitch = {PITCH:g}
yaw = {YAW1:g}
fov = {FOV:g}

[[layers]]
image = "grid_cam0.png"
z = 4000
camera = 0
[[layers]]
image = "grid_cam1.png"
z = 4000
camera = 1

[[camera_zone]]
to_camera = 1
zone = {quad(FWD_ZONE)}
[[camera_zone]]
to_camera = 0
zone = {quad(REV_ZONE)}

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "multicam.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("cam0 yaw", round(C.yaw_deg(cam0), 1), "cam1 yaw", round(C.yaw_deg(cam1), 1))
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
