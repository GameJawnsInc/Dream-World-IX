#!/usr/bin/env python3
"""Build a PRE-CHOOSE config test field (4003): a "console" you press to open a configured menu.

A flat floor (calibration grid) with a cyan CONSOLE zone. Stand on it and PRESS ACTION -> a menu:
  0: "First."        <- CANCEL (B) picks THIS (cancel = 0)
  1: "-- LOCKED --"  <- DISABLED: greyed / skipped by the cursor
  2: "Third."        <- DEFAULT highlighted row (default = 2)
Each enabled option shows a distinct reply, so you can confirm which row was picked.

VERIFY in-game:
  * the menu opens with the THIRD row highlighted (default=2),
  * the middle row is greyed and the cursor SKIPS over it (can't select "LOCKED"),
  * pressing B/Cancel picks the FIRST row -> "You chose FIRST." (cancel=0),
  * picking row 0 or 2 gives the matching reply; the LOCKED row is never selectable.

Run:  python tools/build_prechoose_test.py
then: python tools/deploy_field.py tools/prechoose_out/prechoose.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "prechoose_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
ZONE = [(-350, -600), (350, -600), (350, -1100), (-350, -1100)]
SPAWN = (0, -350)

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
ZC, SPN, BG = (70, 220, 230, 255), (240, 80, 80, 255), (26, 28, 34, 255)


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
    zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in ZONE]
    for i in range(4):
        P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], ZC, thick=7)
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    P.draw_line(buf, W, H, (sx - 30, sy), (sx + 30, sy), SPN, thick=8)
    P.draw_line(buf, W, H, (sx, sy - 30), (sx, sy + 30), SPN, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Pre-choose test (field 4003). Press the cyan CONSOLE zone -> a configured menu:
#   default=2 (THIRD highlighted), cancel=0 (B picks FIRST), middle row DISABLED (greyed/skipped).
[field]
id = 4003
name = "PRECHOOSE"
area = 11
text_block = 1073
title = "Pre-choose test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[choice]]
zone = {quad(ZONE)}
prompt = "Console:"
default = 2          # THIRD row highlighted when the menu opens
cancel = 0           # B / Cancel picks the FIRST row
[[choice.options]]
text = "First."
reply = "You chose FIRST. (Cancel picks this.)"
[[choice.options]]
text = "-- LOCKED --"
disabled = true      # greyed out, cursor skips it -- never selectable
reply = "you should never see this"
[[choice.options]]
text = "Third."
reply = "You chose THIRD. (Default highlight.)"

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "prechoose.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
