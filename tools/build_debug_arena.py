#!/usr/bin/env python3
"""Build a big flat SCROLLING checkerboard ARENA -- a wide debug stage for staging LARGE objects (huge
monster models) in a row without obstruction. Like `ff9mapkit new`, but WIDE + scrolling: a perspective
checkerboard floor (pure-stdlib placeholder art, projected through the camera so it auto-aligns with the
walkmesh) + a flat walkmesh + a scrolling camera (window_width 384, range N screens wide).

Writes IHTEST/arena/{arena.field.toml, art/back.png, art/floor.png}. `build_arena()` is importable so the
archetype gallery can stage its creatures here. Deploy: py tools/deploy_field.py IHTEST/arena/arena.field.toml

Usage: py tools/build_debug_arena.py [--screens N]    # N screens wide (default 3 -> range 1152)
"""
import math
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import guide, placeholder

IHTEST = Path(os.environ.get("IHTEST", r"C:\Users\skaki\AppData\Local\Temp\ihtest"))
PITCH, FOV = 40.0, 42.2                         # downward tilt; horizontal FOV
DIST = 7000.0                                  # camera pulled back -> larger world floor = zoomed OUT
BACK_Y, FRONT_Y = 150.0, 430.0                 # painted-canvas rows the floor's back/front edges sit on
BACK_SPAN = 0.43                               # back edge's canvas half-span as a fraction of range_w
                                               #   (fills the scroll canvas width; front edge overflows a bit)


def build_arena(art_dir: Path, *, screens: int = 3):
    """Generate the arena's checkerboard art (back + floor PNGs) into ``art_dir``; return a dict with the
    camera + walkmesh the field.toml needs (range_w, quad, zb, zf, spawn_z)."""
    range_w = 384 * screens
    cam = guide.make_camera(PITCH, DIST, fov_x_deg=FOV, range_wh=(range_w, 448))
    frame = guide.frame_floor(cam, back_canvas_y=BACK_Y, front_canvas_y=FRONT_Y,
                              back_span_px=range_w * BACK_SPAN)
    quad = [[int(x), int(z)] for (x, z) in guide.walkmesh_corners(frame)]
    # square-ON-SCREEN checkerboard: at pitch p a world Z step foreshortens to ~sin(p) of a world X step,
    # so world cells must be ~1/sin(p) DEEPER than wide to read square. Pick ~6 rows deep, derive columns.
    sinp = math.sin(math.radians(PITCH))
    width, depth = 2 * frame.half_width, abs(frame.zf - frame.zb)
    nz = 6
    nx = max(4, round(width / (depth / nz * sinp)))
    art_dir.mkdir(parents=True, exist_ok=True)
    placeholder.write_placeholders(cam, frame, art_dir / "back.png", art_dir / "floor.png", nx=nx, nz=nz)
    return {"range_w": range_w, "quad": quad, "zb": frame.zb, "zf": frame.zf,
            "spawn_z": int(round((frame.zb + frame.zf) / 2))}


def arena_toml(meta: dict, *, name="ARENA", title="Debug arena", art_prefix="art") -> str:
    quad = "[" + ", ".join(f"[{x}, {z}]" for x, z in meta["quad"]) + "]"
    return f"""# Big flat scrolling checkerboard ARENA -- a debug stage for staging large objects (auto-generated).
[field]
id = 4003
name = "{name}"
area = 11
text_block = 1073
title = "{title}"

[camera]
pitch = {PITCH}
distance = {int(DIST)}
fov = {FOV}
range = [{meta['range_w']}, 448]
window_width = 384
[camera.scroll]
enabled = true

[walkmesh]
quad = {quad}
frame = "world"

[[layers]]
image = "{art_prefix}/back.png"
z = 4000
[[layers]]
image = "{art_prefix}/floor.png"
z = 3000

[player]
spawn = [0, {meta['spawn_z']}]
"""


def main():
    screens = 3
    if "--screens" in sys.argv:
        screens = int(sys.argv[sys.argv.index("--screens") + 1])
    arena = IHTEST / "arena"
    meta = build_arena(arena / "art", screens=screens)
    (arena / "arena.field.toml").write_text(arena_toml(meta), encoding="utf-8")
    w = meta["quad"][1][0] - meta["quad"][0][0]
    print(f"arena: {screens} screens wide (range {meta['range_w']}px); flat walkmesh {w} x "
          f"{meta['zf'] - meta['zb']} world units; floor z=-{abs(meta['zb'])}..{meta['zf']}")
    print(f"  quad   = {meta['quad']}")
    print(f"  spawn  = [0, {meta['spawn_z']}]")
    print(f"wrote {arena / 'arena.field.toml'} + art/back.png + art/floor.png")
    print(f'deploy: py tools/deploy_field.py "{arena / "arena.field.toml"}"')


if __name__ == "__main__":
    main()
