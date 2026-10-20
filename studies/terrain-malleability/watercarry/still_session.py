"""R0's visual calibration: two stills of STOCK water in game, to set beside `world-render --stock` of the same places.

Read-only: no deploy, no Memoria.ini edit, nothing written to any mod folder. Reaches the disc-1 world through bench
6603 (as every terrain round), turns encounters off, then per view teleports to a lawn home (off the 4u lattice,
inside its triangle; picked offline from the stock bytes), faces the feature, and takes two stills 60 frames apart.
  C  cluster C, the lowland river: home (1096.5, -940.5), bearing 103.8 to (1090, -914)
  D  the (19,11) twin falls:      home (1252.5, -777.5), bearing  81.2 to (1262, -716)
RUN:  py tools/play.py studies/terrain-malleability/watercarry/still_session.py --label water-stills
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
sys.path.insert(0, str(HERE.parent / "ingame"))
from harness import HarnessError                      # noqa: E402
import veh_lib as V                                   # noqa: E402

VIEWS = {"C": ((1096.5, -940.5), 103.8, 6.71), "D": ((1252.5, -777.5), 81.2, 3.34)}
ONLY = os.environ.get("WATER_VIEWS")          # e.g. "D" to re-take one view
SETTLE, APART = 180, 60


def run(g):
    g.note("water-stills: stock cluster C river and the (19,11) falls, for the offline renderer's calibration")
    rec: dict = {}
    V.reach_world_as(g, rec, scenario=0, pokes={}, expect_world=0, first=True)
    g.no_encounters()
    g.check(g.state.on_world, "on the world map", str(rec.get("arrival")))
    arr = rec.get("arrival") or V.here(g)
    try:
        g.world_face(0.0, home=(arr["x"], arr["z"]))             # learn the turn rate on the landing lawn
    except HarnessError as err:
        g.note(f"warm-up face: {err}")
    for name, (home, bearing, ground_y) in VIEWS.items():
        if ONLY and name not in ONLY.split(","):
            continue
        g.teleport(*home)
        face = None
        for _attempt in range(2):                                  # one retry: the learned rate is kept
            try:
                face = g.world_face(bearing, home=home)
                break
            except HarnessError as err:
                g.note(f"{name}: face attempt {_attempt + 1}: {str(err)[:200]}")
        if face is None:
            face = {"heading": float("nan"), "error": float("inf")}
        g.teleport(*home)
        g.wait_frames(SETTLE)
        g.shot(f"{name}-a")
        g.wait_frames(APART)
        g.shot(f"{name}-b")
        at = V.settle3(g)
        g.check(abs(face["error"]) <= 6.0, f"{name}: faces the feature", f"heading {face['heading']:.1f} vs {bearing}")
        g.check(at["y"] is not None and abs(at["y"] - ground_y) <= 0.2, f"{name}: stands on the predicted lawn",
                f"y={at['y']} want {ground_y}")
