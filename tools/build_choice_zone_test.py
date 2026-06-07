#!/usr/bin/env python3
"""Build a ZONE-TRIGGERED choice test field (4003): walk into a "lever" zone -> a choice menu.

A flat floor (calibration grid) with a cyan LEVER zone. Walk into it -> a menu pops (movement
locked):
  "Pull it."   -> reply + sets a story flag (8200)
  "Leave it."  -> nothing  (Cancel/B picks this, the last row)
once = false, so it fires once PER VISIT (re-arm with F6, which reloads the field). Verify: the menu
pops on entry, does NOT re-pop while you stand in the zone (loop-safe), and re-arms after F6.

Run:  python tools/build_choice_zone_test.py
then: python tools/deploy_field.py tools/choice_zone_out/choice_zone.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "choice_zone_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
LEVER = [(-350, -600), (350, -600), (350, -1100), (-350, -1100)]   # the walk-in zone
SPAWN = (0, -350)

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
LEVC, SPN, BG = (70, 220, 230, 255), (240, 80, 80, 255), (26, 28, 34, 255)


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
    zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in LEVER]
    for i in range(4):
        P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], LEVC, thick=7)
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    P.draw_line(buf, W, H, (sx - 30, sy), (sx + 30, sy), SPN, thick=8)
    P.draw_line(buf, W, H, (sx, sy - 30), (sx, sy + 30), SPN, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Zone-choice test (field 4003). Walk into the cyan LEVER zone -> a menu (movement locked).
[field]
id = 4003
name = "LEVERROOM"
area = 11
text_block = 1073
title = "Zone-choice test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[choice]]
zone = {quad(LEVER)}
prompt = "Pull the lever?"
once = false                  # once per visit (re-arm with F6); default true = once ever
[[choice.options]]
text = "Pull it."
reply = "*kachunk!*  Something opened."
set_flag = [8200, 1]
[[choice.options]]
text = "Leave it."            # Cancel/B picks this (the last row)

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "choice_zone.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
