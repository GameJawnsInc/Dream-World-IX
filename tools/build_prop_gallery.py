#!/usr/bin/env python3
"""In-game PROP-ID gallery: place a batch of ACC prop models in a row, each at its CANONICAL pose (so it
renders the way it does in the game), for the human to identify by appearance + warp. Turns the cryptic
ACC tokens into named prop archetypes -- the same loop the NPC gallery used for characters.

Props are non-interactive (no talk), so identify by left->right position + the per-token field locations
printed below (warp there via F6 to see the prop in its real scene).

Usage:
  py tools/build_prop_gallery.py --batch 0          # the unnamed, in-game-placed ACC tokens, 8/batch
  py tools/build_prop_gallery.py TBX CSK SWD ...     # explicit tokens (<= 8)
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C
from ff9mapkit import prop_archetypes as PA
from ff9mapkit.scene import bgi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_prop_poses as EP          # canonical pose per model (cached)
import model_field_usage as MFU          # model -> field locations
import build_debug_arena as _arena       # the big flat scrolling checkerboard stage (--arena; big props)

IHTEST = Path(os.environ.get("IHTEST", os.path.expandvars(r"%LOCALAPPDATA%\Temp\ihtest")))
PER_BATCH = 6                              # props vary wildly in size; fewer + wider so big ones don't block
ROW_Z, ROW_X, SPAWN = 150, (-1000, 1000), [0, 500]


def unnamed_tokens():
    """In-game-placed ACC prop tokens not yet a prop archetype, MOST-USED FIRST (common props first)."""
    named = {C.model(PA.PROP_ARCHETYPES[n]["model"]).token for n in PA.names()}
    use = {}
    for m in sorted(C.models(group="ACC", field_only=True), key=lambda m: (m.token, m.form)):
        if m.token in named or m.token in use:
            continue
        total = MFU.usage(m.id, limit=1)[1]
        if total == 0:                              # skip props no field actually places
            continue
        use[m.token] = total
    return [t for t, _ in sorted(use.items(), key=lambda kv: (-kv[1], kv[0]))]


def main():
    args = sys.argv[1:]
    arena = "--arena" in args
    args = [a for a in args if a != "--arena"]
    allt = unnamed_tokens()
    if args and args[0] == "--batch":
        b = int(args[1])
        toks = allt[b * PER_BATCH:(b + 1) * PER_BATCH]
        label = f"batch {b} (props {b * PER_BATCH}-{b * PER_BATCH + len(toks) - 1} of {len(allt)} unnamed)"
    elif args:
        toks = [t.upper() for t in args][:PER_BATCH]
        label = "custom"
    else:
        print("usage: --batch N  |  TOK1 TOK2 ...")
        return 1
    if not toks:
        print(f"no tokens (only {len(allt)} unnamed ACC props remain; batch out of range?)")
        return 1

    n = len(toks)
    if arena:                                          # big flat scrolling checkerboard -- room for HUGE props
        meta = _arena.build_arena(IHTEST / "art", screens=max(3, n))
        half, margin = meta["quad"][1][0], 800
        xs = [round(-(half - margin) + 2 * (half - margin) * i / max(1, n - 1)) for i in range(n)]
        zs = [z for _, z in meta["quad"]]
        z_lo, z_hi = min(zs), max(zs)
        row_z, spawn_z = (z_lo + z_hi) // 2, z_hi - 150
        lines = [
            "# PROP-ID gallery on the big flat scrolling checkerboard -- tell me what each set piece is.",
            "[field]", "id = 4003", 'name = "ARENA"', "area = 11", "text_block = 1073", "",
            "[camera]", f"pitch = {_arena.PITCH}", f"distance = {int(_arena.DIST)}", f"fov = {_arena.FOV}",
            f"range = [{meta['range_w']}, 448]", "window_width = 384", "[camera.scroll]", "enabled = true", "",
            "[walkmesh]", f"quad = {meta['quad']}", 'frame = "world"', "",
            "[[layers]]", 'image = "art/back.png"', "z = 4000",
            "[[layers]]", 'image = "art/floor.png"', "z = 3000", "",
            "[player]", f"spawn = [0, {spawn_z}]", "",
        ]
    else:                                              # GRGR borrowed BG (floor 0)
        xs = [round(ROW_X[0] + (ROW_X[1] - ROW_X[0]) * i / max(1, n - 1)) for i in range(n)]
        row_z = ROW_Z
        lines = [
            "# PROP-ID gallery -- each set piece is at its canonical pose. Tell me what each is (left->right)",
            "# and I'll name + bake the good ones as prop archetypes. Non-interactive; warp to ID the cryptic.",
            "[field]", "id = 4003", 'name = "GRGR_FORK"', "area = 21",
            'borrow_bg = "GRGR_MAP420_GR_CEN_0"', "text_block = 1073", "",
            "[camera]", 'borrow = "camera.bgx"', "control_direction = 0", "",
            "[walkmesh]", 'reference = "walkmesh.bgi"', "",
            "[player]", f"spawn = [{SPAWN[0]}, {SPAWN[1]}]", "",
        ]
    rows = []
    for tok, x in zip(toks, xs):
        m = C.model(f"GEO_ACC_F0_{tok}")
        pose = EP.pose_of(m.id) if m else None
        lines += ["[[prop]]", f'name = "{tok}"', f'model = "GEO_ACC_F0_{tok}"', f"pos = [{x}, {row_z}]"]
        if pose:
            lines.append(f"pose = {pose}")
        lines.append("")
        locs, total = MFU.usage(m.id, limit=5) if m else ([], 0)
        where = "; ".join(f"{fid}={nm.encode('ascii', 'ignore').decode().strip()}" for fid, nm in locs)
        rows.append((tok, pose, total, where))         # field IDs included so the human can F6 -> Warp

    out = IHTEST / "gallery.field.toml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"PROP GALLERY {label}\n")
    for i, (tok, pose, total, where) in enumerate(rows, 1):
        print(f"  {i}. {tok:4} pose={pose}  in {total} field(s): {where or '(?)'}")
    print(f"\nwrote {out}\ndeploy:  py tools/deploy_field.py \"{out}\"")


if __name__ == "__main__":
    sys.exit(main() or 0)
