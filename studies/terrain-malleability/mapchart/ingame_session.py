"""IN GAME, THE MAP ERASE (2026-10-12): does the game show the composited charts -- sunk islands gone from the map?

The lab FF9CustomMap-wmlab (first in FolderNames for this run; owner's go) holds six islands sunk with `world-sink`
(Disc1 only) and `world-minimap`'s two chart overrides: world_map_full_all.png (5 islands erased, the corner island
skipped) and world_map_full_mistcontinent.png (the small east island at (1446, -862) erased). The engine picks the
chart at every world entry (WorldHUD.InitialHUD: scenario >= 5990 -> all-world, else Mist) and loads the highest
folder's loose PNG (AssetManager walks the folders high to low on every load).

ROUTE (bench 6603, its world exit; encounters off after every world load; byte 100 = 1 so the minimap is up and the
first Select opens the full map):
  mist_lab   newgame -> 6603 at scenario 0 -> world 9011 (disc 1): the Mist chart, the lab's PNG
  all_lab    -> 6603 at scenario 9500 -> its world: the all-world chart, the lab's PNG
  (the lab's two PNGs parked in the run dir: the next folder down serves the chart)
  all_base   -> 6603 at 9500: the all-world chart from FF9CustomMap-world (its composite: the islands drawn)
  mist_base  -> 6603 at 0: the Mist chart from MoguriMain (stock)
At each stage Select is pressed three times, a frame after each (the full map is open in the first or second; the
third leaves it shut, control back). PREDICTIONS: in the lab frames the five sunk islands (the 4,813 u2 island north
of the Mist continent's west tail, the lagoon island, Daguerreo, the NE island, the small east island) are absent,
the sea round them continuing; the base frames draw them; on the Mist chart only the small east island differs.
The frames are the evidence (the agent publishes no WorldHUD state); every check here is about reaching the stage.
RUN:  py tools/play.py studies/terrain-malleability/mapchart/ingame_session.py --label mapchart-erase
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools"))
sys.path.insert(0, str(HERE.parent / "ingame"))
import veh_lib as V                                   # noqa: E402  (the 6603 route out to the world)

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
LAB = GAME / "FF9CustomMap-wmlab"
SPRITES = LAB / "FF9_Data" / "EmbeddedAsset" / "ui" / "sprites"
CHARTS = ("world_map_full_all.png", "world_map_full_mistcontinent.png")
_RECORD: dict = {"stages": []}


def _save(g):
    try:
        (g.run_dir / "mapchart_erase.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except Exception as err:                                            # noqa: BLE001
        print(f"[mapchart] could not write the record: {err}")


def park(g, out: bool) -> list:
    """Move the lab's chart PNGs into the run dir (out=True) or back (out=False). Returns what is in the lab."""
    store = g.run_dir / "parked"
    store.mkdir(exist_ok=True)
    for name in CHARTS:
        src, dst = (SPRITES / name, store / name) if out else (store / name, SPRITES / name)
        if src.is_file():
            shutil.move(str(src), str(dst))
    return sorted(p.name for p in SPRITES.glob("*.png"))


def look(g, stage: str) -> list:
    """Three Selects, a frame after each: the full map is open in one of the first two, the third leaves it shut."""
    g.wait_frames(180)                       # the continent title card masks Select while it fades
    shots = []
    for k in range(3):
        g.press("select")
        g.wait_frames(45)
        shots.append(str(g.shot(f"{stage}-select{k + 1}")))
    return shots


def stage(g, name: str, *, scenario: int, first: bool):
    rec = {"stage": name, "scenario": scenario, "lab_pngs": sorted(p.name for p in SPRITES.glob("*.png"))}
    _RECORD["stages"].append(rec)
    V.reach_world_as(g, rec, scenario=scenario, pokes={100: 1}, expect_world=0, first=first)
    g.no_encounters()
    rec["at"] = V.here(g)
    g.check(g.state.on_world and g.state.world_id is not None, f"{name}: on the world map (scenario {scenario})",
            json.dumps(rec["at"]))
    rec["shots"] = look(g, name)
    rec["after"] = V.here(g)
    g.check(rec["after"]["control"] is not False, f"{name}: the map shut again, control back",
            json.dumps(rec["after"]))
    _save(g)


def run(g):
    g.note("mapchart: the map erase in game -- the lab's composited charts vs the folders below")
    mark = g.log_mark()
    try:
        g.check(all((SPRITES / n).is_file() for n in CHARTS), "the lab holds both chart PNGs",
                json.dumps(sorted(p.name for p in SPRITES.glob("*.png"))))
        stage(g, "mist_lab", scenario=0, first=True)
        stage(g, "all_lab", scenario=9500, first=False)
        _RECORD["parked"] = park(g, out=True)
        g.check(not _RECORD["parked"], "the lab's chart PNGs parked (the next folder down serves the charts)",
                json.dumps(_RECORD["parked"]))
        stage(g, "all_base", scenario=9500, first=False)
        stage(g, "mist_base", scenario=0, first=False)
    finally:
        _RECORD["restored"] = park(g, out=False)
        try:
            _RECORD["exceptions"] = [str(e) for e in g.exceptions_since(mark)][:20]
        except Exception as err:                                        # noqa: BLE001
            _RECORD["exceptions_error"] = repr(err)
        _save(g)
