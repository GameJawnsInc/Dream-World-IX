#!/usr/bin/env python3
"""Build a v2 ACTOR-CUTSCENE test field (4003) showcasing the polish: a teleport WALK-IN + an emote.

On entry: control LOCKS, Vivi appears at the cyan cross on the LEFT (teleported off-screen-ish),
walks IN to his spot (magenta), turns to face the player, plays a talk-gesture animation, and says a
line -- then control returns. Walk to the back DOOR (cyan box) to leave; re-enter to confirm it plays
ONCE (Vivi just stands at his spot).

Exercises: teleport (MoveInstantXZY + SetPathing, leading -> runs before the warm-up), walk-in (the
high-turn-speed walk), face_player, animation (RunAnimation 7302 = Vivi Talk_3_1, a confirmed
model-8/animset-61 one-shot), say. Run:
    python tools/build_cutscene_actor_test.py
then: python tools/deploy_field.py tools/cutscene_actor_out/cs2.field.toml
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C
from ff9mapkit.scene import guide as G
from ff9mapkit.scene import placeholder as P

OUT = Path(os.path.dirname(__file__)) / "cutscene_actor_out"
OUT.mkdir(exist_ok=True)

PITCH, FOV, SCALE = 45.0, 42.2, 4
# z convention: MORE-negative = FRONT (toward camera / bottom of screen); less-negative = back (top).
# Vivi HOME = the left (cyan): he starts there (no spawn-flash), walks to center to greet, then
# TELEPORTS back home (tests teleport+Z at a safe time -- all commands run AFTER the warm-up, so the
# teleport never hits the entry transition where the smooth-updater fights it).
FLOOR = [(-1200, -100), (1200, -100), (1200, -1400), (-1200, -1400)]
SPAWN = (0, -1100)        # player: front (toward camera)
REST = (-1150, -800)      # Vivi's HOME (his [[npc]] pos; start + teleport-back target + replay spot)
GREET = (0, -800)         # he walks here to greet the player
ANIM = 7302               # Vivi Talk_3_1 (confirmed model-8/animset-61 one-shot, from real field 790)
DOOR = [(-250, -150), (250, -150), (250, -320), (-250, -320)]   # back edge: leave to re-test "once"

A, B = (95, 100, 120, 255), (55, 60, 78, 255)
CYAN, MAG, SPN, BG = (70, 220, 230, 255), (235, 90, 235, 255), (240, 80, 80, 255), (24, 26, 32, 255)


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
    zc = [tuple(c * SCALE for c in C.to_canvas((x, 0.0, z), cam)) for (x, z) in DOOR]
    for i in range(4):
        P.draw_line(buf, W, H, zc[i], zc[(i + 1) % 4], CYAN, thick=7)
    for (px, pz), col in ((REST, CYAN), (GREET, MAG), (SPAWN, SPN)):
        cx, cy = (c * SCALE for c in C.to_canvas((px, 0.0, pz), cam))
        cross(buf, W, H, cx, cy, col)
    (OUT / "floor.png").write_bytes(P._png_rgba(W, H, buf))

    def quad(z):
        return "[" + ", ".join(f"[{x}, {zz}]" for (x, zz) in z) + "]"

    toml = f"""# v2 actor-cutscene POLISH test (field 4003): emote + teleport.
# Vivi starts at his cyan HOME (left), walks to the magenta cross to greet you, faces you, does a
# talk-gesture emote, says a line, then TELEPORTS back home. Walk to the cyan DOOR to leave +
# re-enter (plays once).
[field]
id = 4003
name = "CUTSCENE2"
area = 11
text_block = 1073
title = "Actor cutscene polish"

[camera]
pitch = {PITCH:g}
fov = {FOV:g}

[[layers]]
image = "floor.png"
z = 4000

[[npc]]
name = "vivi"
preset = "vivi"
pos = [{REST[0]}, {REST[1]}]
dialogue = "Oh! You're finally here. I came all this way to meet you."

[cutscene]
actor = "vivi"
once = true
steps = [
  {{ walk = [{GREET[0]}, {GREET[1]}] }},   # walk in to greet the player
  {{ face_player = true }},                 # turn to look at you
  {{ animation = {ANIM} }},                 # a talk-gesture emote (Vivi Talk_3_1)
  {{ say = "...hi." }},                     # a line
  {{ teleport = [{REST[0]}, {REST[1]}] }},  # warp back home (instant) -- tests teleport + Z
]

[[gateway]]                                    # leave to re-enter and confirm the scene plays ONCE
to = 4002
entrance = 0
zone = {quad(DOOR)}

[walkmesh]
quad = {quad(FLOOR)}

[player]
spawn = [{SPAWN[0]}, {SPAWN[1]}]
"""
    p = OUT / "cs2.field.toml"
    p.write_text(toml, encoding="utf-8")
    print("wrote", p)
    print("next:  python tools/deploy_field.py", p)


if __name__ == "__main__":
    main()
