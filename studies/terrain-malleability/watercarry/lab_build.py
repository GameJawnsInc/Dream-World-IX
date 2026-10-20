"""`world-river` IN GAME (PLAN.md rung 4), the build: cluster C composed onto open ocean and written as the lab folder.

The placement is the first OPEN-OCEAN whole-block offset whose 12 cells no LIVE folder overrides (the live overworld
folder holds 54 files on the first seam candidate; rung 4 found it): block offset (8, -2), cells (23,12-14),
(0,11-15), (1,11-14) -- across the world's 23|0 seam, rows 11-15. The lab is `river.write_composition` verbatim (every
gate run on the way), plus world-environment's `mist = false` (round 16's lesson: the mist hides texture).
REFUSES unless every gate is green but the two understood ones: W1's single introduced edge (THE CLIFF-CORNER BAND
STEP at the W join) and the sea-plan gate's B warning (the island's interior blocks carry little Sea4).
RUN:  py studies/terrain-malleability/watercarry/lab_build.py   (then lab_prep.py)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
import ff9mapkit  # noqa: E402
assert Path(ff9mapkit.__file__).resolve().is_relative_to(ROOT), ff9mapkit.__file__
from ff9mapkit.world import mesh as M, river as R  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB_NAME = "FF9CustomMap-lab"
LAB = HERE / "out" / "lab" / LAB_NAME
OFFSET = (8, -2)                                   # whole blocks: +8 columns, 2 rows north


def live_folders() -> list:
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    return [f for f in re.findall(r'"([^"]*)"', m.group(1)) if f != LAB_NAME] if m else []


def main():
    win = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(win, R.CLUSTER_C)
    ol = R.outline(f)
    comp = R.compose(f, offset=(64.0 * OFFSET[0], -64.0 * OFFSET[1]), window=win, ol=ol)
    blocks = sorted({(M.wrap_block_col(b[0]), b[1]) for b in (tuple(map(int, k.split(","))) for k in comp.plan["cells"])})
    occupied = {fo: M.existing_overrides(blocks, fo, disc=d) for fo in live_folders() for d in (1, 4)}
    occupied = {k: v for k, v in occupied.items() if v}
    if occupied:
        raise SystemExit(f"live folders already override the lab's cells: { {k: len(v) for k, v in occupied.items()} }")
    red = sorted(k for k, g in comp.report["gates"].items() if isinstance(g, dict) and g.get("ok") is False)
    if red:
        raise SystemExit(f"the composition is not green: {red}")
    own = Counter(t["blk"] for t in f.tris if t["part"] == "sea5")
    (bx0, bx1), (by0, by1) = R.CLUSTER_C.window
    donors = [b for b, _ in own.most_common()] + [(x, y) for x in range(bx0, bx1 + 1) for y in range(by0, by1 + 1)]
    if LAB.parent.exists():
        shutil.rmtree(LAB.parent)
    rep = R.write_composition(comp, LAB, window=win, donors=donors)
    rep.pop("meshes")
    w1 = rep["W1"]
    understood = (w1["after"]["seam"]["under"] == 0 and not w1["after"]["contacts"] and not w1["unpaintable"]
                  and w1["wang"]["incoherent"] == 0 and w1["edges_introduced"] <= 1)
    if not (rep["B1"]["ok"] and understood and rep["sea_plan"]["A_ok"] and rep["sea_plan"]["C_ok"]):
        raise SystemExit(f"rung 3's gates did not hold at this placement: B1 {rep['B1']['fails']}; W1 {w1}")
    env = LAB.parent / "mist_off.toml"
    env.write_text("[world_environment]\nmist = false\n", encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "world-environment", "--mod-folder", str(LAB), str(env)],
                       cwd=ROOT / "ff9mapkit", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"world-environment failed: {r.stdout[-400:]} {r.stderr[-400:]}")
    out = {"offset_blocks": OFFSET, "offset_world": list(comp.offset), "cells": blocks, "files": rep["files"],
           "W1": {k: w1[k] for k in ("after", "home", "edges_introduced", "edges_introduced_where", "wang")},
           "B1": {k: rep["B1"][k] for k in ("ok", "cells")}, "sea_plan": rep["sea_plan"],
           "compose": {k: comp.report[k] for k in ("opening", "apron", "zip", "green")}}
    (LAB.parent / "build.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
