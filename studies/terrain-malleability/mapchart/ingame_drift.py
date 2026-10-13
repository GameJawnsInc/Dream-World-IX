"""IN GAME, NEW LAND ON THE DRIFT (2026-10-12): the live FF9CustomMap-world map re-composited with new land drawn at
the registered frame plus the chart's measured drift (`navimap.WORLD_MAP_DRIFT`). One stage, no ini change: newgame
-> 6603 at scenario 9500 -> world 9003 -> open the full map (all-world chart) -> frames. The frames show the live
folder's drawn landmasses at the render's positions (the far-south ones ~20px higher than before, the east-edge ones
~11px further left); compare with the offline render.
RUN:  py tools/play.py studies/terrain-malleability/mapchart/ingame_drift.py --label mapchart-drift
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingame_session as S                                  # noqa: E402  (the 6603 route, the three Selects)


def run(g):
    g.note("mapchart: the live map with new land on the drift")
    S.stage(g, "all_live", scenario=9500, first=True)
