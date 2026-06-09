#!/usr/bin/env python3
"""PROP TEST -- exercise the real [[prop]] section (the verified FF9 prop recipe: SetModel + fixed pose +
EnableHeadFocus(0), a non-character object). Confirms props render as the right object, hold the correct
pose (chest CLOSED, moogle whole -- not the 'b' bind pose), and do NOT turn to face the player.

Usage:
  py tools/build_prop_test.py                              # chest(closed), tent, save-moogle, frog
  py tools/build_prop_test.py GEO_ACC_F0_TBX:close ...     # GEO[:pose] pairs (<=8)
"""
import os
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit import catalog as C

IHTEST = Path(os.environ.get("IHTEST", r"C:\Users\skaki\AppData\Local\Temp\ihtest"))
ROW_Z, ROW_X, SPAWN = 150, (-800, 800), [0, 500]
# (GEO name, pose action or None=default). chest/moogle need a real pose; tent/frog default fine.
DEFAULT = [("GEO_ACC_F0_TBX", "close"), ("GEO_ACC_F0_TNT", None),
           ("GEO_ACC_F0_MGR", "1872"), ("GEO_ACC_F0_MGP", "1874"), ("GEO_NPC_F0_FRC", None)]


def main():
    args = sys.argv[1:]
    if args:
        items = []
        for a in args[:8]:
            geo, _, pose = a.partition(":")
            items.append((geo, pose or None))
    else:
        items = DEFAULT
    n = len(items)
    xs = [round(ROW_X[0] + (ROW_X[1] - ROW_X[0]) * i / max(1, n - 1)) for i in range(n)]

    lines = [
        "# PROP TEST -- the [[prop]] section (static set-dressing; head-tracking OFF). Confirm each renders",
        "# as the right object at the right pose, and does NOT rotate to face you.",
        "[field]", "id = 4003", 'name = "GRGR_FORK"', "area = 21",
        'borrow_bg = "GRGR_MAP420_GR_CEN_0"', "text_block = 1073", "",
        "[camera]", 'borrow = "camera.bgx"', "control_direction = 0", "",
        "[walkmesh]", 'reference = "walkmesh.bgi"', "",
        "[player]", f"spawn = [{SPAWN[0]}, {SPAWN[1]}]", "",
    ]
    report = []
    for (geo, pose), x in zip(items, xs):
        m = C.model(geo)
        if not m:
            print(f"skip {geo!r} (no such model)")
            continue
        lines += ["[[prop]]", f'name = "{m.token}"', f'model = "{geo}"', f"pos = [{x}, {ROW_Z}]"]
        if pose:
            lines.append(f'pose = "{pose}"')
        lines.append("")
        report.append((m.token, geo, pose or "(default)"))

    out = IHTEST / "gallery.field.toml"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"PROP TEST ({len(report)} props via [[prop]])\n")
    for i, (tok, geo, pose) in enumerate(report, 1):
        print(f"  {i}. {tok:4} {geo:18} pose={pose}")
    print(f"\nwrote {out}\ndeploy:  py tools/deploy_field.py \"{out}\"")


if __name__ == "__main__":
    main()
