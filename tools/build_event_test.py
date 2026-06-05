#!/usr/bin/env python3
"""Build an EVENT test field (4003) to prove one-shot + repeatable walk-in events in-game.

A flat floor (calibration grid) with two marked zones:
  GOLD zone  (ONCE)       walk in -> "+item +1000 gil" + a message; walk in AGAIN -> nothing.
  CYAN zone  (REPEATABLE) walk in -> an ambient line, EVERY time.
Verify the once-event in the menu (new item + gil up 1000, only the first time) and that re-entering
the gold zone does nothing while the cyan line keeps firing. Calibration grid (not art).

Run:  python tools/build_event_test.py
then: python tools/deploy_field.py tools/event_out/event.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "event_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
GOLD = [(350, -350), (1050, -350), (1050, -1250), (350, -1250)]    # once: item + gil
CYAN = [(-1050, -350), (-350, -350), (-350, -1250), (-1050, -1250)]  # repeatable: message
SPAWN = (0, -800)

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
GOLDC, CYANC, SPN = (240, 200, 60, 255), (70, 220, 230, 255), (240, 80, 80, 255)
BG = (26, 28, 34, 255)


def main():
    cam = G.make_camera(PITCH, 4500.0, fov_x_deg=FOV)
    W, H = int(cam.range[0] * SCALE), int(cam.range[1] * SCALE)
    buf = bytearray(bytes(BG)) * (W * H)
    x0, x1, z0, z1 = FLOOR[0][0], FLOOR[1][0], FLOOR[0][1], FLOOR[2][1]
    for iz in range(10):
        for ix in range(10):
            ax, bx = x0 + (x1 - x0) * ix / 10, x0 + (x1 - x0) * (ix + 1) / 10
            az, bz = z0 + (z1 - z0) * iz / 10, z0 + (z1 - z0) * (iz + 1) / 10
            pts = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam))
                   for (x, z) in ((ax, az), (bx, az), (bx, bz), (ax, bz))]
            P._fill_quad(buf, W, H, pts, A if (ix + iz) % 2 == 0 else B)
    for zone, col in ((GOLD, GOLDC), (CYAN, CYANC)):
        zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in zone]
        for i in range(4):
            P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], col, thick=7)
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    P.draw_line(buf, W, H, (sx - 30, sy), (sx + 30, sy), SPN, thick=8)
    P.draw_line(buf, W, H, (sx, sy - 30), (sx, sy + 30), SPN, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Event test (field 4003). GOLD zone = ONCE (item + 1000 gil + message); CYAN zone = REPEATABLE line.
[field]
id = 4003
name = "EVENTROOM"
area = 11
text_block = 1073
title = "Event test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[event]]
zone = {quad(GOLD)}
give_item = [232, 1]
gil = 1000
message = "A treasure! (+1 item, +1000 gil)"

[[event]]
zone = {quad(CYAN)}
message = "A cool breeze blows through..."
once = false

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "event.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
