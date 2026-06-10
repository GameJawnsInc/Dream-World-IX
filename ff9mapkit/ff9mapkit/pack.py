"""Field-ID allocation + mod packaging + project scaffolding.

Custom field IDs and FBG names form a shared namespace across all installed mods, so two
independently-authored mods must not collide. There is no central registry, so the convention
is: custom fields use ids >= :data:`CUSTOM_ID_MIN`, and a mod claims a contiguous *block*.
:func:`suggest_base` derives a deterministic per-mod block from the mod name (reducing the odds
of an accidental clash); for a public release, coordinate the block with the community.

:func:`pack_mod` zips a built mod for distribution; :func:`new_project` scaffolds a fresh
``field.toml`` project directory.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

CUSTOM_ID_MIN = 4000          # shipped-content custom field ids start here (below this is base-game territory)
CUSTOM_ID_MAX = 9899          #   ...content blocks live in [CUSTOM_ID_MIN..CUSTOM_ID_MAX]
BLOCK_SIZE = 100              # ids per mod block
# HARD engine cap: the live current-field id (engine `FF9StateSystem.Common.FF9.fldMapNo`) is Int16, so a
# field id above FIELD_ID_MAX overflows and is unreachable -- the DictionaryPatch *key* is Int32, but the
# runtime current-field variable is 16-bit (FF9Snd.cs:2651), so you can register a higher id yet never
# navigate to it. Ephemeral dev/test "scratch" slots (per-worktree, gitignored .ff9deploy.toml) sit in
# [SCRATCH_ID_MIN..SCRATCH_ID_MAX] -- the top of the valid range, clearly ABOVE shipped content.
FIELD_ID_MAX = 32767
SCRATCH_ID_MIN = 30000
SCRATCH_ID_MAX = FIELD_ID_MAX


def suggest_base(mod_name: str) -> int:
    """A deterministic custom-field-id block base for a mod name (e.g. 4300).

    Hashes the name into one of the 100-id blocks in [CUSTOM_ID_MIN, CUSTOM_ID_MAX]. Two
    different names usually land in different blocks; collisions should be resolved by hand for
    a public release.
    """
    n_blocks = (CUSTOM_ID_MAX - CUSTOM_ID_MIN) // BLOCK_SIZE
    h = int.from_bytes(hashlib.sha1(mod_name.encode("utf-8")).digest()[:4], "big")
    return CUSTOM_ID_MIN + (h % n_blocks) * BLOCK_SIZE


def suggest_ids(base: int, count: int) -> list[int]:
    """``count`` consecutive ids from ``base`` (validated to stay in the custom range)."""
    if base < CUSTOM_ID_MIN or base + count - 1 > CUSTOM_ID_MAX:
        raise ValueError(f"id block [{base}..{base + count - 1}] outside custom range "
                         f"[{CUSTOM_ID_MIN}..{CUSTOM_ID_MAX}]")
    return [base + i for i in range(count)]


def pack_mod(mod_root, out_path) -> Path:
    """Zip a built mod folder for distribution. Returns the zip path.

    The archive contains the mod folder itself (so unzipping next to FF9_Launcher.exe installs
    it). Skips ``*.bak`` and editor leftovers.
    """
    mod_root = Path(mod_root).resolve()
    if not mod_root.is_dir():
        raise FileNotFoundError(mod_root)
    out_path = Path(out_path)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(mod_root.rglob("*")):
            if p.is_dir() or p.suffix in (".bak",) or p.name.endswith(".prefix.bak"):
                continue
            zf.write(p, arcname=str(Path(mod_root.name) / p.relative_to(mod_root)))
    return out_path


_FIELD_TOML_TEMPLATE = '''\
# {title} — a custom FF9 field. Compile with:  ff9mapkit build {fname}
#
# Human-supplied (Hard Constraint): paint the background layer PNGs and (optionally) model the
# walkmesh in Blender. `ff9mapkit guide --pitch {pitch} ...` prints where the floor lands on
# the painted canvas so you can paint to match.

[field]
id = {field_id}          # custom field id (>= 4000; claim a block for your mod, see docs)
name = "{name}"          # -> FBG_N{area}_{name} (background) + EVT_{name}.eb (script)
area = {area}            # must be >= 10
text_block = 1073
title = "{title}"

[camera]
pitch = {pitch}          # downward tilt (degrees); real FF9 fields are <= ~48
distance = 4500
fov = 42.2
[camera.frame]
back = 205               # painted-canvas rows the floor's back/front edges sit on
front = 432

[walkmesh]
# The walkmesh is in TRUE world coords = where the painted floor is (frame = "world"): the player
# renders exactly on it, no fudge (measured in-game, Session 18). `quad` = the floor's 4 corners,
# matching the placeholder floor below. Swap for an exported Blender mesh with `obj = "walkmesh.obj"`.
quad = {quad}
frame = "world"

[[layers]]               # background layers, back-to-front (z = depth; smaller = nearer)
image = "art/back.png"   # PLACEHOLDER (solid) -- repaint to match your camera
z = 4000
[[layers]]
image = "art/floor.png"  # PLACEHOLDER (checkerboard floor) -- repaint to match your camera
z = 3000

[player]
spawn = [0, {spawn_z}]

# [[npc]]
# name = "Someone"
# preset = "vivi"
# pos = [0, -700]
# dialogue = "Hello there."

# [[gateway]]
# to = 100               # warp to this field id
# entrance = 0
# zone = [[-1100, -2400], [1100, -2400], [1100, -1750], [-1100, -1750]]
'''


_DISTANCE, _FOV, _BACK, _FRONT = 4500.0, 42.2, 205, 432   # template camera defaults (match the toml)


def new_project(name: str, dest, *, field_id: int | None = None, area: int = 11,
                pitch: float = 48.0, title: str | None = None, placeholder_art: bool = True) -> Path:
    """Scaffold a new field project under ``dest/<name>/``. Returns the project dir.

    With ``placeholder_art`` (default), derives the walkmesh quad from the template camera frame and
    writes PLACEHOLDER ``art/back.png`` + ``art/floor.png`` (pure stdlib, no PIL) so the project
    BUILDS and is walkable straight away -- the human then replaces the art with painted layers. If
    the camera frame can't be solved (an extreme ``pitch``), falls back to a no-art scaffold.
    """
    title = title or name
    if field_id is None:
        field_id = suggest_base(name)
    proj_dir = Path(dest) / name
    (proj_dir / "art").mkdir(parents=True, exist_ok=True)
    fname = f"{name.lower()}.field.toml"

    quad = [[-1400, -2400], [1400, -2400], [1400, -800], [-1400, -800]]   # fallback
    spawn_z = -1350
    wrote_art = False
    if placeholder_art:
        try:
            from .scene import guide, placeholder
            camera = guide.make_camera(pitch, _DISTANCE, fov_x_deg=_FOV)
            frame = guide.frame_floor(camera, back_canvas_y=_BACK, front_canvas_y=_FRONT)
            quad = [[int(x), int(z)] for (x, z) in guide.walkmesh_corners(frame)]
            spawn_z = int(round((frame.zb + frame.zf) / 2))
            placeholder.write_placeholders(camera, frame, proj_dir / "art" / "back.png",
                                           proj_dir / "art" / "floor.png")
            wrote_art = True
        except (ValueError, ZeroDivisionError):
            pass   # extreme camera -> keep the fallback quad + no placeholder art

    quad_toml = "[" + ", ".join(f"[{x}, {z}]" for x, z in quad) + "]"
    (proj_dir / fname).write_text(
        _FIELD_TOML_TEMPLATE.format(name=name, area=area, field_id=field_id, pitch=pitch,
                                    title=title, fname=fname, quad=quad_toml, spawn_z=spawn_z),
        encoding="utf-8", newline="\n")
    if wrote_art:
        readme = (
            "PLACEHOLDER background art (back.png = solid slate, floor.png = perspective checkerboard)\n"
            "was generated by `ff9mapkit new` so the project builds + is walkable right away.\n"
            "REPLACE back.png and floor.png with your painted layers (same size/aspect).\n\n"
            "Run  ff9mapkit guide --pitch <p> --png guide.png  for a paint guide showing exactly\n"
            "where the floor + its edges land on the canvas for your camera.\n")
    else:
        readme = (
            "Place your painted background layer PNGs here (back.png, floor.png, ...).\n"
            "Run  ff9mapkit guide --pitch <p> --png guide.png  to get a paint guide that shows\n"
            "exactly where the floor and its edges land on the canvas for your camera.\n")
    (proj_dir / "art" / "README.txt").write_text(readme, encoding="utf-8", newline="\n")
    return proj_dir
