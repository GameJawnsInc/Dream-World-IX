#!/usr/bin/env python3
"""Build a FLAG-GATED choice test field (4003): an option hidden UNTIL a story flag is set.

Flat floor with two zones:
  * CYAN "CONSOLE" (left)  -> a press-action choice menu:
        "Buy a Potion."          (always shown)
        "Use the Gate Key."      (requires_flag = 8001 -> HIDDEN until you flip the switch)
        "Leave."                 (always shown)
  * GOLD "SWITCH" (right)  -> a walk-in event that sets flag 8001 ("you found the key").

VERIFY in-game:
  1. Press the CONSOLE first -> menu shows only "Buy a Potion." and "Leave." (no Gate Key row).
  2. Walk into the GOLD switch -> "You found the Gate Key!" (sets flag 8001).
  3. Press the CONSOLE again -> the "Use the Gate Key." row is now PRESENT.
  4. F10 (reset save state) -> the Gate Key row is hidden again (flag cleared) -- repeatable.

This is the flag-gated availability mask (built at runtime from the flag), FF9's moogle-mail pattern.

Run:  python tools/build_flaggate_test.py
then: python tools/deploy_field.py tools/flaggate_out/flaggate.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "flaggate_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
CONSOLE = [(-700, -600), (-100, -600), (-100, -1100), (-700, -1100)]   # left
SWITCH = [(100, -600), (700, -600), (700, -1100), (100, -1100)]        # right
SPAWN = (0, -350)

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
CON, SWI, SPN, BG = (70, 220, 230, 255), (235, 200, 70, 255), (240, 80, 80, 255), (26, 28, 34, 255)


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
    for zone, col in ((CONSOLE, CON), (SWITCH, SWI)):
        zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in zone]
        for i in range(4):
            P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], col, thick=7)
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    P.draw_line(buf, W, H, (sx - 30, sy), (sx + 30, sy), SPN, thick=8)
    P.draw_line(buf, W, H, (sx, sy - 30), (sx, sy + 30), SPN, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Flag-gated choice test (field 4003). The CONSOLE's "Use the Gate Key" row is hidden until
# the SWITCH sets flag 8001. F10 (reset save state) hides it again.
[field]
id = 4003
name = "FLAGGATE"
area = 11
text_block = 1073
title = "Flag-gated choice test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[choice]]
zone = {quad(CONSOLE)}
prompt = "Shop:"
[[choice.options]]
text = "Buy a Potion."
reply = "Here's a Potion!"
give_item = ["Potion", 1]
[[choice.options]]
text = "Use the Gate Key."
requires_flag = 8001          # HIDDEN until flag 8001 is set (by the switch)
reply = "*kachunk* -- the gate opens!"
[[choice.options]]
text = "Leave."

[[event]]
name = "keyslot"
zone = {quad(SWITCH)}
message = "You found the Gate Key!"
set_flag = [8001, 1]          # reveal the "Use the Gate Key" choice row

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "flaggate.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
