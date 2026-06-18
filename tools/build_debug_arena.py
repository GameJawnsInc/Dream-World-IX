#!/usr/bin/env python3
"""Build a big flat SCROLLING checkerboard ARENA -- a wide debug stage for staging LARGE objects in a row
without obstruction. CLI wrapper: the builder now lives in the package (`ff9mapkit.scene.arena`) so the
Info Hub preview + the galleries can reuse it. Writes IHTEST/arena/{arena.field.toml, art/back.png, art/floor.png}.

Usage: py tools/build_debug_arena.py [--screens N]    # N screens wide (default 3 -> range 1152)
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
# re-export the arena API so existing importers keep working unchanged now that the builder moved into the
# package (the galleries do `import build_debug_arena as A; A.build_arena(...)`, `A.PITCH`, `A.IHTEST`, ...).
from ff9mapkit.scene.arena import (build_arena, arena_toml, arena_scene_lines,   # noqa: F401
                                   PITCH, FOV, DIST, BACK_Y, FRONT_Y, BACK_SPAN)

IHTEST = Path(os.environ.get("IHTEST", os.path.expandvars(r"%LOCALAPPDATA%\Temp\ihtest")))


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
