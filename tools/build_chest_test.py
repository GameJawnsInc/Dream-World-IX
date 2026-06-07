#!/usr/bin/env python3
"""Build a TREASURE CHEST test field (4003) exercising the chest niceties.

Flat floor with one GOLD chest zone -> a faithful FF9 chest:
  give_item Potion + received (item-get window) + require_space (bag-full guard) + once.
Compiles to FF9's exact chest shape:
  if (GetItemCount(Potion) < 99) { if (!opened) { opened=1; AddItem(Potion); SetTextVariable; "Received Potion!" } }

VERIFY in-game:
  1. Walk into the GOLD chest -> the canonical "Received Potion!" item-get window (window type 7).
  2. Open the menu (V) -> you have +1 Potion.
  3. Walk over the chest again -> nothing (once -- the dedup flag is set).
  4. F10 (reset save state) -> the chest gives again (flag cleared) -- repeatable.
  (Bag-full guard is hard to test without 99 Potions; it's grounded byte-for-byte vs a real chest.)

Run:  python tools/build_chest_test.py
then: python tools/deploy_field.py tools/chest_out/chest.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "chest_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -150), (1200, -150), (1200, -1500), (-1200, -1500)]
CHEST = [(-300, -600), (300, -600), (300, -1100), (-300, -1100)]
SPAWN = (0, -350)

A, B = (90, 110, 130, 255), (55, 70, 90, 255)
CH, SPN, BG = (235, 200, 70, 255), (240, 80, 80, 255), (26, 28, 34, 255)


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
    zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in CHEST]
    for i in range(4):
        P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], CH, thick=8)
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    P.draw_line(buf, W, H, (sx - 30, sy), (sx + 30, sy), SPN, thick=8)
    P.draw_line(buf, W, H, (sx, sy - 30), (sx, sy + 30), SPN, thick=8)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Treasure-chest test (field 4003). Walk into the GOLD chest -> "Received Potion!" item-get window.
[field]
id = 4003
name = "CHEST"
area = 11
text_block = 1073
title = "Treasure chest test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[event]]
name = "chest"
zone = {quad(CHEST)}
give_item = ["Potion", 1]
received = true          # canonical "Received Potion!" item-get window (window type 7)
require_space = true     # chest behavior: skip (retryable) if the bag is full
once = true              # fires once (the dedup flag); F10 re-arms it

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "chest.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
