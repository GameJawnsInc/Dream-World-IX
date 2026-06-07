#!/usr/bin/env python3
"""Build a DIALOGUE-CHOICE test field (4003) to prove talk -> menu -> branch in-game.

A flat floor (calibration grid) with a Vivi NPC (magenta cross). Walk up to Vivi, face him, press
the action button -> a 3-option menu:
  "A Potion, please. (-100 gil)"  -> reply + a Potion (+1 item) and gil DOWN 100
  "Tell me a secret."             -> reply + sets a story flag (8001)
  "Nothing."                      -> reply only  (this is LAST, so Cancel/B picks it)

Verify: the menu appears with 3 rows + a cursor; picking #1 adds a Potion and drops gil 100 (check
the menu); picking #3 (or pressing B = cancel -> last row) just says "Come again!". Calibration grid
(not art); the room renders + is walkable.

Run:  python tools/build_choice_test.py
then: python tools/deploy_field.py tools/choice_out/choice.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "choice_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
NPC = (0, -1050)        # where Vivi stands (toward the back)
SPAWN = (0, -450)       # the player starts in front of him

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
NPCC, SPN, BG = (230, 90, 230, 255), (240, 80, 80, 255), (26, 28, 34, 255)


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
    for (px, pz), col in ((NPC, NPCC), (SPAWN, SPN)):
        cx, cy = (c * SCALE for c in C.to_canvas((px, 0.0, pz), cam))
        P.draw_line(buf, W, H, (cx - 34, cy), (cx + 34, cy), col, thick=8)
        P.draw_line(buf, W, H, (cx, cy - 34), (cx, cy + 34), col, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Dialogue-choice test (field 4003). Talk to Vivi (magenta) -> a 3-option menu -> branch.
[field]
id = 4003
name = "CHOICEROOM"
area = 11
text_block = 1073
title = "Choice test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[npc]]
name = "Vivi"
preset = "vivi"
pos = [{NPC[0]}, {NPC[1]}]

[[choice]]
npc = "Vivi"
prompt = "What'll it be?"
[[choice.options]]
text = "A Potion, please. (-100 gil)"
reply = "Here you go!"
give_item = [232, 1]
gil = -100
[[choice.options]]
text = "Tell me a secret."
reply = "...the Mist rises from below."
set_flag = [8001, 1]
[[choice.options]]
text = "Nothing."
reply = "Come again!"

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "choice.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
