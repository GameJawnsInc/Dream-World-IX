"""Rung A1's in-game check, scenario 1 of 2: reach the disc-1 world map and leave the game open there.

Run by a1_run.py as ``py tools/play.py studies/overworld-editor/a1_reach.py --keep-open``: New Game, then the
terrain rounds' route out to the world (bench 6603, ``ingame/veh_lib.reach_world_as``), encounters off. The session
ends DISARMED with the game still on the world map, so tools/world_teleport.py (the World tab button's argv) can
attach to it, exactly as it would from the Workspace.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE.parents[0] / "terrain-malleability" / "ingame"))
import veh_lib as V                                                   # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")


def run(g):
    ini = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    folders = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    has_6603 = any(re.search(r"^FieldScene 6603 ", (GAME / f / "DictionaryPatch.txt").read_text(
        encoding="utf-8", errors="replace"), re.M) for f in folders if (GAME / f / "DictionaryPatch.txt").is_file())
    if not g.check(has_6603, "bench 6603 (the route to the world) is registered", str(folders)):
        return
    rec = {}
    V.reach_world_as(g, rec, scenario=0, pokes={}, expect_world=0, first=True)
    g.no_encounters()
    st = g.world_settle()
    g.check(st.on_world, "on the world map", json.dumps(rec.get("arrival"), default=str))
    g.shot("a1-arrival")
    (g.run_dir / "a1_reach.json").write_text(json.dumps({"arrival": rec.get("arrival"), "folders": folders,
                                                          "world": (st.world_x, st.world_y, st.world_z)},
                                                         default=str, indent=1), encoding="utf-8")
