"""THE CELL-CLIPPED FILL in game: paired stills of the four morphed cliff tops, one launch per lab variant.

Read-only on the owner's state: the harness sandboxes the saves; the lab (lab_install.py) is the only mod change and
sits first in FolderNames for the session. Reaches the disc-1 world through bench 6603 at ScenarioCounter 0 (cell
(13,17) switches form with Lindblum from 5598, so form 1 -- the edited Terrain -- is the one on screen), turns
encounters off, faces once on the landing lawn (world_face learns the bumper rate there), then per station teleports
to its home (out/stations.json: stock lawn 12u from the window's OLD streak tri), faces the tri, and takes two stills
60 frames apart. The same stations and names for both variants, so the pairs line up: <station>-<variant>-a/b.
Checks: each face lands within 6 deg; he stands on the predicted lawn (0.2u).
RUN:  py studies/coast-shape-language/cellclip-fill/lab_install.py install old
      py tools/play.py studies/coast-shape-language/cellclip-fill/still_session.py --label cellclip-old
      py studies/coast-shape-language/cellclip-fill/lab_install.py swap new
      py tools/play.py studies/coast-shape-language/cellclip-fill/still_session.py --label cellclip-new
      py studies/coast-shape-language/cellclip-fill/lab_install.py uninstall <run dir>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "studies" / "terrain-malleability" / "ingame"))
from harness import HarnessError                      # noqa: E402
import veh_lib as V                                   # noqa: E402  (the 6603 route out to the world)

SETTLE, APART = 180, 60


def run(g):
    variant = json.loads((HERE / "out" / "install.json").read_text(encoding="utf-8"))["variant"]
    stations = json.loads((HERE / "out" / "stations.json").read_text(encoding="utf-8"))
    g.note(f"cellclip-fill stills, lab variant {variant!r}: stations {sorted(stations)}")
    rec: dict = {}
    V.reach_world_as(g, rec, scenario=0, pokes={}, expect_world=0, first=True)
    g.no_encounters()
    g.check(g.state.on_world, "on the world map", str(rec.get("arrival")))
    arr = rec.get("arrival") or V.here(g)
    try:
        g.world_face(0.0, home=(arr["x"], arr["z"]))             # learn the turn rate on the landing lawn
    except HarnessError as err:
        g.note(f"warm-up face: {err}")
    # the second variant's run faces the heading the FIRST run reached (out/face_targets.json), tighter, so a
    # pair's two cameras sit within ~1.5 deg of each other rather than both within 6 of the bearing
    tpath = HERE / "out" / "face_targets.json"
    targets = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
    for name, s in stations.items():
        home = tuple(s["home"])
        g.teleport(*home)
        face = None
        want, tol = (targets[name], 1.5) if name in targets else (s["bearing"], 6.0)
        for attempt in range(2):                                   # one retry: the learned rate is kept
            try:
                face = g.world_face(want, home=home, tolerance=tol)
                break
            except HarnessError as err:
                g.note(f"{name}: face attempt {attempt + 1}: {str(err)[:200]}")
        if face is None:
            face = {"heading": float("nan"), "error": float("inf")}
        g.teleport(*home)
        g.wait_frames(SETTLE)
        g.shot(f"{name}-{variant}-a")
        g.wait_frames(APART)
        g.shot(f"{name}-{variant}-b")
        at = V.settle3(g)
        g.check(abs(face["error"]) <= 6.0, f"{name}: faces the window's streak tri",
                f"heading {face['heading']} vs {s['bearing']}")
        g.check(at["y"] is not None and abs(at["y"] - s["ground_y"]) <= 0.2,
                f"{name}: stands on the predicted lawn", f"y={at['y']} want {s['ground_y']}")
        # THE CLOSE-UPS (the camera keeps the home's yaw across a teleport): 3u short of the OLD streak tri on the
        # same line, then on it -- the 12u view does not resolve a 1-2 u^2 tri
        for key in ("near", "on"):
            if key not in s:
                continue
            g.teleport(*s[key]["at"])
            g.wait_frames(SETTLE)
            g.shot(f"{name}-{variant}-{key}")
            at = V.settle3(g)
            g.check(at["y"] is not None and abs(at["y"] - s[key]["ground_y"]) <= 0.2,
                    f"{name}: stands {key} the streak tri's spot", f"y={at['y']} want {s[key]['ground_y']}")
