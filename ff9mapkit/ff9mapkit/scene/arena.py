"""The big flat SCROLLING checkerboard ARENA -- a wide debug stage for staging objects in a row without
obstruction (huge monster models, the prop/held galleries, the Info Hub in-game preview). A perspective
checkerboard floor (pure-stdlib placeholder art, projected through the camera so it auto-aligns with the
walkmesh) + a flat walkmesh + a scrolling camera (window_width 384, range N screens wide).

`build_arena()` writes the art + returns the camera/walkmesh meta; `arena_scene_lines()` gives the
field.toml SCENE that a caller appends `[[npc]]`/`[[prop]]` placements to (a gallery, the preview);
`arena_toml()` is the standalone debug stage. Lifted here from `tools/build_debug_arena.py` so the package
(notably the Info Hub spine's `preview_field_toml`) can build a stage without importing a dev script.
"""
from __future__ import annotations

import math
from pathlib import Path

from . import guide, placeholder

PITCH, FOV = 40.0, 42.2                         # downward tilt; horizontal FOV
DIST = 7000.0                                  # camera pulled back -> larger world floor = zoomed OUT
BACK_Y, FRONT_Y = 150.0, 430.0                 # painted-canvas rows the floor's back/front edges sit on
BACK_SPAN = 0.43                               # back edge's canvas half-span as a fraction of range_w


def build_arena(art_dir: Path, *, screens: int = 3) -> dict:
    """Generate the arena's checkerboard art (back + floor PNGs) into ``art_dir``; return the camera +
    walkmesh the field.toml needs (range_w, quad, zb, zf, spawn_z)."""
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


def arena_scene_lines(meta: dict, *, spawn_z=None, name="ARENA", art_prefix="art") -> list:
    """The field.toml SCENE lines (field/camera/walkmesh/layers/player) for an arena -- so a caller can
    append its own `[[npc]]`/`[[prop]]` placements. ``spawn_z`` defaults to the arena centre."""
    if spawn_z is None:
        spawn_z = meta["spawn_z"]
    quad = "[" + ", ".join(f"[{x}, {z}]" for x, z in meta["quad"]) + "]"
    return ["[field]", "id = 4003", f'name = "{name}"', "area = 11", "text_block = 1073", "",
            "[camera]", f"pitch = {PITCH}", f"distance = {int(DIST)}", f"fov = {FOV}",
            f"range = [{meta['range_w']}, 448]", "window_width = 384", "[camera.scroll]", "enabled = true", "",
            "[walkmesh]", f"quad = {quad}", 'frame = "world"', "",
            "[[layers]]", f'image = "{art_prefix}/back.png"', "z = 4000",
            "[[layers]]", f'image = "{art_prefix}/floor.png"', "z = 3000", "",
            "[player]", f"spawn = [0, {spawn_z}]", ""]


def arena_toml(meta: dict, *, name="ARENA", art_prefix="art") -> str:
    """The standalone debug-arena field.toml (player at the centre)."""
    lines = ["# Big flat scrolling checkerboard ARENA -- a debug stage for staging large objects (auto-generated)."]
    lines += arena_scene_lines(meta, name=name, art_prefix=art_prefix)
    return "\n".join(lines)
