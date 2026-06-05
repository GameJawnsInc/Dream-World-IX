#!/usr/bin/env python3
"""Build a STORY-LOGIC test field (4003): a flag set by an event changes the world.

GOLD switch zone -> sets story flag 200 (once) + a message. While the flag is clear, a GUARD (Vivi,
at the magenta marker) is ABSENT and the back DOOR (cyan) is LOCKED (walking into it does nothing).
Flip the switch -> the guard appears and the door unlocks (exits to Alexandria). Proves
event set_flag -> [[npc]] requires_flag + [[gateway]] requires_flag.

Run:  python tools/build_story_test.py
then: python tools/deploy_field.py tools/story_out/story.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "story_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
FLOOR = [(-1200, -100), (1200, -100), (1200, -1400), (-1200, -1400)]
SWITCH = [(300, -400), (700, -400), (700, -800), (300, -800)]      # event: set flag 200
DOOR = [(-200, -1200), (200, -1200), (200, -1350), (-200, -1350)]  # gateway requires flag 200
NPC = (-500, -600)                                                  # appears once flag 200 is set
SPAWN = (0, -300)
FLAG = 200

A, B = (95, 100, 120, 255), (55, 60, 78, 255)
GOLD, CYAN, MAG, SPN = (240, 200, 60, 255), (70, 220, 230, 255), (235, 90, 235, 255), (240, 80, 80, 255)
BG = (24, 26, 32, 255)


def cross(buf, W, H, x, y, col, r=34, t=8):
    P.draw_line(buf, W, H, (x - r, y), (x + r, y), col, thick=t)
    P.draw_line(buf, W, H, (x, y - r), (x, y + r), col, thick=t)


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
    for zone, col in ((SWITCH, GOLD), (DOOR, CYAN)):
        zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in zone]
        for i in range(4):
            P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], col, thick=7)
    nx, ny = (c * SCALE for c in C.to_canvas((NPC[0], 0.0, NPC[1]), cam))
    cross(buf, W, H, nx, ny, MAG)                                   # where the guard will appear
    sx, sy = (c * SCALE for c in C.to_canvas((SPAWN[0], 0.0, SPAWN[1]), cam))
    cross(buf, W, H, sx, sy, SPN)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# Story-logic test (field 4003). Switch (gold) sets flag {FLAG}; guard (magenta) + door (cyan) gate on it.
[field]
id = 4003
name = "STORYROOM"
area = 11
text_block = 1073
title = "Story logic test"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[event]]                              # the switch: set story flag {FLAG}
zone = {quad(SWITCH)}
set_flag = [{FLAG}, 1]
message = "*CLICK* — you hear something unlock."

[[npc]]                                # guard: appears only after the switch
preset = "vivi"
pos = [{NPC[0]}, {NPC[1]}]
dialogue = "You flipped the switch! The door's open now."
requires_flag = {FLAG}

[[gateway]]                            # door: locked until the switch is flipped
to = 100
entrance = 204
zone = {quad(DOOR)}
requires_flag = {FLAG}

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "story.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
