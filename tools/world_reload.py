#!/usr/bin/env python3
"""Make the RUNNING game re-read the world map's files, then put the party at a point (dev checkout only).

    py tools/world_reload.py X Z                # e.g. after `ff9mapkit world-promote <draft>`
    py tools/world_reload.py X Z --shot NAME    # ... and an in-engine still once he has settled

The World tab's "Show in game" runs this after a Promote (editor rung C4, ``studies/overworld-editor/PLAN.md``): the
game follows an edit with NO DLL and no relaunch. The engine reads every block override when the world LOADS, so
the round trip is the one the terrain labs used since round 16: from the world map into bench field 6603 (the
harness's world warp), out of its door, and the world loads afresh from disk. Then the engine's overworld teleport
puts the party at X, Z.

It ATTACHES to the game already running (never launches or quits it), keeps the story's ScenarioCounter as it is
(6603's exit cascade picks the world from it), and refuses, with the reason, when no game is running, when it is not
on the world map, when 6603 is not registered, or when another harness run holds this install. On foot only: a ride
(a chocobo, an airship) is dropped by the field visit. The last line of output is one JSON object: ``{"ok", "x", "z",
"world_x", "world_y", "world_z", "scenario", "seconds": {"to_field", "to_world", "teleport", "total"}, "shot",
"run_dir", "error"}``.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                                 # tools/harness

# THE ROUTE (studies/terrain-malleability/ingame/veh_lib.py, where the terrain labs keep it): bench field 6603, its
# door polygon (field units) and a point beyond it the walk aims for; walking out loads the world.
BENCH_FIELD = 6603
DOOR = [[285, -352], [875, -460], [424, -2944], [-166, -2836]]
EXIT_AT = (400.0, -1400.0)


def main(argv) -> int:
    shot = None
    if len(argv) == 4 and argv[2] == "--shot":
        shot, argv = argv[3], argv[:2]
    if len(argv) != 2:
        print(__doc__)
        return 2
    x, z = float(argv[0]), float(argv[1])
    out = {"ok": False, "x": x, "z": z, "world_x": None, "world_y": None, "world_z": None, "scenario": None,
           "seconds": {}, "shot": None, "run_dir": None, "error": None}
    t0 = time.time()
    try:
        from harness.session import Session
        with Session(label="world-reload", attach=True, verbose=False) as s:
            out["run_dir"] = str(s.run_dir)
            st = s.state
            if not st.on_world:
                raise RuntimeError("the game is not on the world map: the reload starts from it")
            out["scenario"] = st.scenario
            s.world_warp(BENCH_FIELD, scenario=st.scenario)
            out["seconds"]["to_field"] = round(time.time() - t0, 2)
            t1 = time.time()
            s.calibrate_axes(hazards=[DOOR])
            s.walk_to(*EXIT_AT, strict=False, halt_on_transition=True)
            s.wait_world(timeout=90)
            out["seconds"]["to_world"] = round(time.time() - t1, 2)
            t2 = time.time()
            s.teleport(x, z)
            st = s.world_settle()
            out["seconds"]["teleport"] = round(time.time() - t2, 2)
            out.update(ok=True, world_x=st.world_x, world_y=st.world_y, world_z=st.world_z)
            y = "?" if st.world_y is None else f"{st.world_y:.3f}"
            print(f"reloaded the world and teleported to x {st.world_x:.2f}, z {st.world_z:.2f}, standing at y {y}")
            if shot:
                out["shot"] = str(s.shot(shot))
    except Exception as e:                                    # noqa: BLE001 -- the reason IS the output
        out["error"] = f"{type(e).__name__}: {e}"
        print(f"reload refused: {out['error']}")
    out["seconds"]["total"] = round(time.time() - t0, 2)
    print(json.dumps(out))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
