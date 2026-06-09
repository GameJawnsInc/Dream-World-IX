#!/usr/bin/env python3
"""Build an in-game ANIMATION CHECK: place a row of ARCHETYPES that each play a chosen clip (walk / run /
turn) IN PLACE, by forcing the NPC's idle slot to that clip via the `anims` override. The human scans the
row -- any model that T-poses, freezes, or plays the wrong motion is a bad auto-resolution. Offline we
already proved every slot resolves to a REAL clip (tools: the catalog audit); this confirms they RENDER.

A static [[npc]] only ever plays its `stand` (idle) clip, so we set stand = the clip under test. walk/run
/turn then animate while the NPC stands still -- letting you verify many models per screen, no cutscene
choreography (which is one-actor-per-load).

Usage:
  py tools/build_anim_check.py                       # default family-spanning sample, walk clip
  py tools/build_anim_check.py --anim run            # same sample, run clip
  py tools/build_anim_check.py guard black_mage cat  # explicit archetype names (<= 8)
  py tools/build_anim_check.py --anim turn dwarf oglop chocobo
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import archetypes as AR
from ff9mapkit import catalog as C
from ff9mapkit.scene import bgi

IHTEST = Path(os.environ.get("IHTEST", r"C:\Users\skaki\AppData\Local\Temp\ihtest"))
PER_ROW = 8
ROW_Z = 150
ROW_X = (-800, 800)
SPAWN = [0, 500]
ANIM_SLOT = {"walk": "walk", "run": "run", "turn": "left"}   # which npc_anims slot to showcase

# a family-spanning default sample: human f, armored, robed mage, beast-folk, dwarf, small animal,
# large bird, and the walk-as-run fallback bug -- if these all render, the families are sound.
DEFAULT = ["townswoman", "guard", "black_mage", "burmecian_soldier", "dwarf", "cat", "chocobo", "oglop"]


def main():
    args = sys.argv[1:]
    anim = "walk"
    if args and args[0] == "--anim":
        anim = args[1]
        args = args[2:]
    if anim not in ANIM_SLOT:
        print(f"--anim must be one of {sorted(ANIM_SLOT)}")
        return 1
    names = [a.lower() for a in args][:PER_ROW] if args else DEFAULT
    slot = ANIM_SLOT[anim]

    wm = bgi.BgiWalkmesh.from_bytes((IHTEST / "walkmesh.bgi").read_bytes())
    n = len(names)
    xs = [round(ROW_X[0] + (ROW_X[1] - ROW_X[0]) * i / max(1, n - 1)) for i in range(n)]
    off = [x for x in xs if wm.point_on_walkmesh(x, ROW_Z) is None]
    if off:
        print(f"WARNING: x={off} at z={ROW_Z} off floor 0.")

    lines = [
        f"# ANIM CHECK ({anim}) -- each NPC plays its {anim} clip in place. Scan for any that T-pose,",
        "# freeze, slide oddly, or play the wrong motion; tell me which. (Stationary creatures like",
        "# fat_chocobo have no walk -> they'll just idle, which is correct.)",
        "[field]", "id = 4003", 'name = "GRGR_FORK"', "area = 21",
        'borrow_bg = "GRGR_MAP420_GR_CEN_0"', "text_block = 1073", "",
        "[camera]", 'borrow = "camera.bgx"', "control_direction = 0", "",
        "[walkmesh]", 'reference = "walkmesh.bgi"', "",
        "[player]", f"spawn = [{SPAWN[0]}, {SPAWN[1]}]", "",
    ]
    report = []
    for name, x in zip(names, xs):
        mid = AR.resolve(name)[0]
        if mid is None:
            print(f"skip {name!r} (no model / cloned player)")
            continue
        base = C.npc_anims(mid)
        if not base:
            print(f"skip {name!r} (no anims)")
            continue
        clip = base[slot]
        real = clip != base["stand"] or anim == "walk"   # note when the clip is a fallback of idle
        a = dict(base); a["stand"] = clip                 # showcase the clip while standing
        anims_toml = ", ".join(f"{k} = {v}" for k, v in a.items())
        m = C.model(mid)
        lines += ["[[npc]]", f'name = "{name}"', f'model = "{m.name}"',
                  f"pos = [{x}, {ROW_Z}]", f"anims = {{ {anims_toml} }}",
                  f'dialogue = "{name}: {anim} clip {clip} ({m.token})"', ""]
        report.append((name, m.token, clip, base.get(slot) is not None))

    out = IHTEST / "gallery.field.toml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"ANIM CHECK '{anim}'  ({len(report)} NPCs play their {anim} clip in place)\n")
    for i, (name, tok, clip, real) in enumerate(report, 1):
        note = "" if real else "  (FALLBACK -> shows idle/substitute, expected)"
        print(f"  {i}. {name:18} {tok:4} clip {clip}{note}")
    print(f"\nwrote {out}")
    print(f'deploy:  py tools/deploy_field.py "{out}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
