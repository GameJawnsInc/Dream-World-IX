"""Lane d9 -- README section 7.1 rank 1(b)/(c): THE DISC9 (Path D world 9013) BATTLE WALK and its bind receipts.

NEEDS A DEPLOY THE ORCHESTRATOR MAKES FIRST (d9_PLAN.md section 3): bench field 30950 PATHDGATE in the scratch folder
FF9CustomMap-lab (first in FolderNames), with the WorldMap(9013) splice. Nothing in the live install today is a door to
9013: no live .eb carries WorldMap(9013) (byte census of all 1085 live scripts, d9_PLAN.md section 2), and the harness
has no world-reload verb (HarnessAgent.cs:652-674: warp / worldwarp / teleport only; the ~ menu's ForceWorldState,
Ff9mkDebugMenu.cs:1552-1606, is an IMGUI button). This file REFUSES TO LOAD -- before play.py launches the game --
unless the deploy is live (preflight below), because warping to an unregistered id is the null-.eb black screen.

ROUTE (per loop): newgame -> warp(30950) -> calibrate_axes(hazards=[the pad zone]) -> walk onto the pad -> the spliced
tread region runs fade + arrive_writes(425,-479) + D8:2=35 + WorldMap(9013) (inject_worldjump.py range_body) -> world
9013 -> teleport to a home on the Uaho carry, Disc9 (13,15) -> short "up" bursts, TELEPORTING HOME BEFORE EVERY ONE
(world_probe's own home idiom: the grass ring is ~9u wide, so a burst is sized to ~2u and can never leave the
measured disc), until a random battle starts -> record battle.scene -> recover to the title -> next loop.
A teleport never adds encounter distance: the count runs only while _moveKey = w_frameEncountEnable
(EventEngine.ProcessEvents.cs:72-74, :289-297), which only on-foot movement sets (ff9.cs:5535-5538).

THE LEVEL-1 PARTY CANNOT SURVIVE zone 24 (Adamantoise / Worm Hydra), so every loop ends at the title:
  rung 1  the game's own soft reset from BattleHUD -- the combo's HELD form (UIKeyTrigger.cs:55-61) is read through
          GetKey, which admits BattleHUD (:91-93), and the handler has a battle branch (:361-395, FF9BMenu_EnableMenu
          off, btl_seq 1, Replace("Title")). Memoria.log logs "[Soft Reset]" (:361).
  rung 2  let the party fall (the top-level command menu leaves the ATB running) and Confirm the Game Over screen
          (GameOverUI.cs:67-90 -> Replace("Title")).
  rung 3  restore_baseline() (close_ui + soft reset), for anything else.

REGISTERED PREDICTIONS (numbers from out/d9_prep.json, written before any run; rerun d9_prep.py first):
  R0  route: the pad lands him on world 9013 (state.world.id = wldMapNo) within 3u of (425,-479).
  H   height instrument + the BLANK-mode divert receipt: after a burst on a carry home, published world_y =
      ground (topo 0) or ground - 1.171875 (topo 37, the canopy sink V3), +-0.15. CONTROL: had the divert not armed
      (no Terrain.ff9mesh -> SeaBlockPrefab), the same x/z is sea4f at y 0, topograph 57 (not foot-walkable).
      (The carry's Terrain is the donor (0,0) Terrain verbatim, so the height can NOT tell bound from free-riding --
      part (c)'s log is the only receipt for that.)
  B1  README 1(b): every battle scene on the carry comes from zone 24's slice (records 250-253: {777,778,779,780}).
  B2  sharper: scene = the fog-0 record of the topograph he stood on when it fired -- topo 0 -> 778 (Adamantoise),
      topo 37 -> 780 (Worm Hydra). 777/779 instead would mean the s75 mist suppression did not engage (fog is part of
      the lookup key, ff9.cs:9248; WorldConfiguration.cs:235).
  RATE every battle fires within 485.6u of on-foot travel on the carry (zone 24's ENCRATE 16 makes one certain by
      check 128); median ~54u, p90 ~96u. The measured distance is the sum of burst chords, a LOWER bound of the
      engine's 3D path, so "no battle past the cap" is a sound falsifier of the encounter path.
  C   CONTROL loop (D9_CONTROL=1, default on, run LAST): the landing lawn, Disc9 (6,7) area 0 -> zone 0, topo 0, fog 0:
      every battle scene in {206,165,5,230}; no zone-24 scene there. Separates "the area under him picks the zone"
      from "Path D has one fixed table".
  REC each recovery reaches the title; rung 1 is predicted to be the one that does.
  (c) is scored OFFLINE by d9_post.py from the archived Memoria.log (one 9013 load per loop: 238 Disc9 'loaded'
      lines over 65 cells, (13,15) = [Terrain, Sea4], zero Disc1/Disc4 override lines, zero 'failed' lines).

Rerun:  py studies/terrain-malleability/ingame/d9_prep.py
        py studies/terrain-malleability/ingame/d9_session.py --preflight        (no game; checks the deploy)
        py tools/play.py studies/terrain-malleability/ingame/d9_session.py --label terrain-d9
        py studies/terrain-malleability/ingame/d9_post.py <.harness-runs/...-terrain-d9>
Env:    D9_LOOPS=topo0,topo0,topo37 (default) ; D9_CONTROL=0 drops the landing-lawn control loop.
"""
import json
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))
from harness import HarnessError                      # noqa: E402

import numpy as np                                     # noqa: E402

GAME_DEFAULT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
PREP = json.loads((HERE / "out" / "d9_prep.json").read_text(encoding="utf-8"))
with np.load(HERE / "out" / "d9_grid.npz") as _z:      # decompress once, not per lookup
    GRID = {k: _z[k] for k in _z.files}

BENCH, BENCH_NAME, LAB, WORLD = 30950, "PATHDGATE", "FF9CustomMap-lab", 9013
WORLDMAP_9013 = bytes.fromhex("b6003523")               # opcodes.world_map(9013): WMAPJUMP 0xB6, arg 0x2335
LANGS = ("us", "uk", "jp", "fr", "gr", "it", "es")
EB_REL = "StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/{lang}/EVT_PATHDGATE.eb.bytes"
ZONE = [[-600, -1900], [600, -1900], [600, -1500], [-600, -1500]]   # inject_worldjump.ZONE_CORNERS
PAD = (0.0, -1700.0)
LANDING = tuple(PREP["constants"]["landing"])
HOMES = {k: tuple(v["world"]) for k, v in PREP["homes"].items()}
HOME_CELL = {k: ("landing" if k == "landing" else "carry") for k in HOMES}
SINK = PREP["constants"]["sink"]
CANOPY = (36, 37, 38)
BURST_TARGET = PREP["constants"]["burst_target"]
BURST_MAX = PREP["constants"]["burst_max"]
TOL_Y = 0.15
PRED = PREP["predicted_scenes"]
CAP = {"carry": PREP["rate_model"]["certain_by_u"], "landing": PREP["rate_model_landing"]["certain_by_u"]}
WALK_SLACK = 20.0                                       # walk this far past the certain-by distance before giving up
LOOP_WALL_S = 600.0
_RECORD: dict = {"lane": "d9", "pred": PRED, "homes": PREP["homes"], "loops": []}


# ------------------------------------------------------------------------------------------------ preflight
def _folder_names(game: Path):
    ini = (game / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^\s*FolderNames\s*=\s*(.+)$', ini, re.M)
    return re.findall(r'"([^"]*)"', m.group(1)) if m else []


def preflight(game: Path) -> dict:
    """The deploy this scenario needs, checked against the live stack (EventDB/SceneData are ONE global namespace)."""
    folders = _folder_names(game)
    problems, regs = [], {}
    for f in folders:
        p = game / f / "DictionaryPatch.txt"
        if not p.is_file():
            continue
        for m in re.finditer(r"^[ \t]*(FieldScene|WorldScene|BattleScene|MessageFile)[ \t]+(\d+)[ \t]+(\S+)(?:[ \t]+(\S+))?",
                             p.read_text(encoding="utf-8", errors="replace"), re.M):
            regs.setdefault((m.group(1), int(m.group(2))), []).append((f, m.group(3), m.group(4)))
    if LAB not in folders:
        problems.append(f"{LAB} is not in Memoria.ini FolderNames {folders} -- a registration there is never read")
    fs = regs.get(("FieldScene", BENCH), [])
    if [f for f, *_ in fs] != [LAB]:
        problems.append(f"FieldScene {BENCH} must be served by {LAB} alone; found {fs or 'nowhere'}")
    elif not any(BENCH_NAME in (n or "") or BENCH_NAME in (n2 or "") for _, n, n2 in fs):
        problems.append(f"FieldScene {BENCH} in {LAB} is not {BENCH_NAME}: {fs}")
    ms = regs.get(("MessageFile", BENCH), [])
    if [f for f, *_ in ms] not in ([LAB], []):
        problems.append(f"MessageFile {BENCH} registered outside {LAB}: {ms}")
    for kind in ("WorldScene", "BattleScene"):
        if regs.get((kind, BENCH)):
            problems.append(f"{kind} {BENCH} also registered: {regs[(kind, BENCH)]} -- the null-.eb collision")
    ws = regs.get(("WorldScene", WORLD), [])
    if not ws:
        problems.append(f"WorldScene {WORLD} is not registered in any FolderNames folder -- 9013 would black-screen")
    spliced = {}
    for lang in LANGS:
        p = game / LAB / EB_REL.format(lang=lang)
        spliced[lang] = p.is_file() and WORLDMAP_9013 in p.read_bytes()
    if not all(spliced.values()):
        problems.append(f"the WorldMap(9013) splice is missing in {[k for k, v in spliced.items() if not v]} -- run "
                        f"inject_worldjump.py --mod-folder <{LAB}> after every deploy_field.py")
    return {"folders": folders, "bench": fs, "message": ms, "world": ws, "spliced": spliced, "problems": problems}


if __name__ != "__main__" and os.environ.get("D9_DRYRUN") != "1":
    _pf = preflight(GAME_DEFAULT)
    if _pf["problems"]:
        raise SystemExit("d9_session preflight REFUSES to run (nothing launched):\n  - " + "\n  - ".join(_pf["problems"]))


# ------------------------------------------------------------------------------------------------ ground lookup
def classify(x, z, cell):
    """Nearest 0.25u raster sample of the cell's LIVE walk list (d9_prep): area, topograph, event, ground."""
    if x is None or z is None:
        return {}
    ox, oz = (float(v) for v in GRID[f"{cell}_origin"])
    p = float(GRID["pitch"])
    i = int(round((x - ox) / p - 0.37))
    j = int(round(-(z - oz) / p - 0.61))
    n = GRID[f"{cell}_X"].shape[0]
    if not (0 <= i < n and 0 <= j < n):
        return {"outside_cell": True}
    topo = int(GRID[f"{cell}_topo"][i, j])
    Y = GRID[f"{cell}_Y"]
    ground = float(Y[i, j])
    # the nearest sample is up to pitch/sqrt(2) away: bound that error by the steepest step to a neighbour sample
    # (the exact sky query is d9_post.py's; this slack keeps the in-run H check from failing on the instrument)
    nb = Y[max(0, i - 1):i + 2, max(0, j - 1):j + 2]
    slack = float(np.max(np.abs(nb - ground))) * 0.7071
    return {"area": int(GRID[f"{cell}_area"][i, j]), "topo": topo, "event": int(GRID[f"{cell}_event"][i, j]),
            "ground": round(ground, 4), "expect_y": round(ground - SINK if topo in CANOPY else ground, 4),
            "slack": round(slack, 4)}


def expected_scenes(cell, topo):
    if cell == "landing":
        return PRED["landing"]
    return PRED.get(f"topo{topo}")


# ------------------------------------------------------------------------------------------------ the route
def enter_9013(g, lrec):
    st = g.state
    if st.ui_state != "Title":
        ok, why = g.restore_baseline()
        if not ok:
            raise HarnessError(f"cannot reach the title before the loop: {why}")
    g.newgame()
    g.warp(BENCH)
    st = g.state
    lrec["bench"] = {"field": st.field_id, "name": st.field_name, "pos": [st.player_x, st.player_z]}
    g.wait_frames(45)
    # A frame hitch can make a 1-frame calibration probe "move" 90-270u and reject a free axis (the 2026-10-07 run
    # lost all three carry loops to it at 27-34 fps). Re-calibrate (warp back to the spawn first) before giving up.
    for attempt in range(3):
        try:
            g.calibrate_axes(hazards=[ZONE], recalibrate=attempt > 0)
            break
        except HarnessError as err:
            lrec.setdefault("calibration_retries", []).append(str(err)[:200])
            if attempt == 2:
                raise
            g.warp(BENCH)
            g.wait_frames(90)
    g.walk_to(*PAD, strict=False, halt_on_transition=True)
    g.wait_world(timeout=90)
    st = g.world_settle()
    lrec["arrival"] = {"world": st.world_id, "x": st.world_x, "z": st.world_z, "y": st.world_y,
                       "scenario": st.scenario, "t": time.time()}


def _left_world(st, epoch0) -> bool:
    return (not st.on_world) or st.in_battle or st.battle_epoch > epoch0


def _settled_or_left(g, epoch0):
    """After a burst: wait for the world position to settle, then look once more a few frames later -- a battle's
    world-side transition can freeze him on the map for a moment before ui_state leaves WorldHUD."""
    st = g.world_settle()
    if _left_world(st, epoch0):
        return st, True
    g.wait_frames(6)
    st2 = g.state
    if _left_world(st2, epoch0):
        return st2, True
    if st2.fading:                               # SceneDirector.IsFading: a transition is under way
        try:
            st3 = g.wait_for(lambda s: _left_world(s, epoch0) or not s.fading, timeout=4.0,
                             what="a world transition to resolve")
            return st3, _left_world(st3, epoch0)
        except HarnessError:
            pass
    if not st2.control:                          # GetUserControl() false on the map: noted, never waited on
        _RECORD["no_control_samples"] = _RECORD.get("no_control_samples", 0) + 1
    return st, False


def walk_until_battle(g, home_key, lrec):
    home = HOMES[home_key]
    cell = HOME_CELL[home_key]
    cap = CAP[cell] + WALK_SLACK
    epoch0 = g.state.battle_epoch
    lrec["epoch0"] = epoch0
    frames, walked, still = 6, 0.0, 0
    bursts = lrec.setdefault("bursts", [])
    t0 = time.time()
    while walked < cap and time.time() - t0 < LOOP_WALL_S:
        g.teleport(*home)
        before, left = _settled_or_left(g, epoch0)
        if left:
            return capture(g, epoch0, before.frame, walked, lrec, cell)
        f0 = before.frame
        g.send(f"hold up {frames}", f"wait {frames + 2}")
        after, left = _settled_or_left(g, epoch0)
        if left:
            return capture(g, epoch0, f0, walked, lrec, cell)
        dx, dz = g.world_delta(before.world_pos, after.world_pos)
        d = math.hypot(dx, dz)
        walked += d
        row = {"i": len(bursts), "frames": frames, "x": after.world_x, "z": after.world_z, "y": after.world_y,
               "d": round(d, 3), "walked": round(walked, 2), **classify(after.world_x, after.world_z, cell)}
        bursts.append(row)
        if d >= 0.2:
            still = 0
            frames = max(2, min(30, int(round(BURST_TARGET / (d / frames)))))
            if d > BURST_MAX:
                frames = max(2, int(frames * 0.6))
        else:
            still += 1
            if still >= 3:                       # "up" faces a wall from home: turn the camera a quarter (L1,
                g.send("hold leftbumper 16", "wait 18")   # ff9.cs:6139-6148) and go on
                row["turned_camera"] = True
                still = 0
    lrec["no_battle"] = {"walked": round(walked, 2), "wall_s": round(time.time() - t0, 1), "cap": cap}
    return None


def capture(g, epoch0, f0, walked, lrec, cell):
    """The battle is up (or coming): its scene, the last on-map sample before it, and the class of ground there."""
    ring = g.states_since(f0)
    last = None
    for s in ring:
        w = s.get("world") or {}
        if s.get("ui_state") == "WorldHUD" and w.get("x") is not None:
            last = s
    st = g.wait_battle(after_epoch=epoch0, timeout=60)
    b = {"scene": st.battle.get("scene"), "epoch": st.battle_epoch, "epoch0": epoch0,
         "enemies": [u.get("name") for u in st.units(player=False)],
         "party": [u.get("name") for u in st.units(player=True)],
         "scene_info": st.battle.get("scene_info"), "walked_u": round(walked, 2),
         "bursts": len(lrec.get("bursts", [])), "t": time.time(), "cell": cell}
    lb = (lrec.get("bursts") or [{}])[-1]
    fire = ([float(last["world"]["x"]), float(last["world"]["z"])] if last is not None
            else [lb.get("x"), lb.get("z")])
    b["fire_pos"] = fire
    b["fire_class"] = classify(fire[0], fire[1], cell)
    b["last_burst_class"] = {k: lb.get(k) for k in ("x", "z", "area", "topo", "event")}
    try:
        g.wait_frames(90)
        b["shot"] = str(g.shot(f"{lrec['label']}-battle"))
    except HarnessError as err:
        b["shot_error"] = str(err)
    return b


def recover(g) -> dict:
    """Back to the title from wherever the loop ended. Returns which rung did it."""
    out = {"from": g.state.ui_state}
    st = g.state
    if st.ui_state == "Title":
        out["how"] = "already"
        return out
    if st.in_battle or st.ui_state in ("BattleHUD", "Tutorial"):
        try:
            g.wait_for(lambda s: s.ui_state in ("BattleHUD", "Title", "GameOver"), timeout=30,
                       what="the battle HUD to come up")
            g.reset_agent()
            g.soft_reset(timeout=30)
            out["how"] = "soft_reset_from_battle"
            return out
        except HarnessError as err:
            out["soft_reset_error"] = str(err)
        deadline = time.time() + 300
        while time.time() < deadline:
            st = g.state
            if st.ui_state == "Title":
                out["how"] = "gameover_confirm"
                return out
            if st.ui_state in ("GameOver", "BattleResult"):
                g.press("confirm", 4)
            g.wait_frames(30)
        out["gameover_timeout"] = True
    ok, why = g.restore_baseline()
    out["how"] = "restore_baseline" if ok else "FAILED"
    out["why"] = why
    return out


# ------------------------------------------------------------------------------------------------ judging
def judge_loop(g, lrec):
    lab = lrec["label"]
    cell = HOME_CELL[lrec["home"]]
    v = lrec.setdefault("verdicts", {})
    arr = lrec.get("arrival")
    if arr:
        d = math.hypot((arr["x"] or 0) - LANDING[0], (arr["z"] or 0) - LANDING[1]) if arr.get("x") is not None else 99
        v["R0"] = g.check(arr["world"] == WORLD and d < 3.0, f"{lab} R0: the pad lands him on world {WORLD} near "
                          f"{LANDING}", json.dumps(arr))
    bursts = [r for r in lrec.get("bursts", []) if r.get("y") is not None and r.get("expect_y") is not None]
    if bursts:
        dev = [round(r["y"] - r["expect_y"], 4) for r in bursts]
        good = sum(abs(r["y"] - r["expect_y"]) <= TOL_Y + r.get("slack", 0.0) for r in bursts)
        sea = sum(abs(r["y"]) < 0.2 for r in bursts)
        lrec["height"] = {"n": len(dev), "within": good, "at_sea_level": sea, "dev_minmax": [min(dev), max(dev)]}
        v["H"] = g.check(good >= max(1, int(0.8 * len(dev))),
                         f"{lab} H: published world_y = the live mesh's ground (canopy -{SINK}) after {len(dev)} bursts "
                         f"-- land on a BLANK Path D cell (control: no divert = sea4f y 0)", json.dumps(lrec["height"]))
    else:
        v["H"] = "proved-nothing"
    b = lrec.get("battle")
    if b is None:
        nb = lrec.get("no_battle") or {}
        if nb.get("walked", 0) >= CAP[cell]:
            v["RATE"] = g.check(False, f"{lab} RATE: a battle fires within {CAP[cell]}u of on-foot travel "
                                f"(ENCRATE certain-by)", json.dumps(nb))
        else:
            v["RATE"] = "proved-nothing"
            g.note(f"d9 {lab}: no battle and the walk did not reach the certain-by distance -- proved nothing")
        return
    scene = b.get("scene")
    topo = (b.get("fire_class") or {}).get("topo")
    if cell == "carry":
        v["B1"] = g.check(scene in PRED["zone24_slice"], f"{lab} B1: battle scene {scene} comes from zone 24's slice "
                          f"{PRED['zone24_slice']}", json.dumps(b, default=str))
        want = expected_scenes(cell, topo)
        if want:
            v["B2"] = g.check(scene in want, f"{lab} B2: scene {scene} = the fog-0 record for topo {topo} {want} "
                              f"(fog-1 twin would be {PRED['fog1_alternative'].get(f'topo{topo}')})",
                              json.dumps(b.get("fire_class")))
        else:
            v["B2"] = "proved-nothing"
            g.note(f"d9 {lab}: fire point class {b.get('fire_class')} has no zone-24 fog-0 row -- B2 proved nothing")
    else:
        v["C"] = g.check(scene in PRED["landing"] and scene not in PRED["zone24_slice"],
                         f"{lab} C: on the area-0 landing lawn the scene {scene} is zone 0's {PRED['landing']}",
                         json.dumps(b, default=str))
    v["RATE"] = g.check(b["walked_u"] <= CAP[cell] + 1.0, f"{lab} RATE: the battle fired within {CAP[cell]}u of "
                        f"travel ({b['walked_u']}u)", "")


def _write(g):
    try:
        (Path(g.run_dir) / "d9_session.json").write_text(json.dumps(_RECORD, indent=1, default=str), encoding="utf-8")
    except OSError:
        pass


def loops_from_env():
    loops = [s.strip() for s in os.environ.get("D9_LOOPS", "topo0,topo0,topo37").split(",") if s.strip()]
    if os.environ.get("D9_CONTROL", "1") != "0":
        loops.append("landing")
    bad = [k for k in loops if k not in HOMES]
    if bad:
        raise HarnessError(f"D9_LOOPS names unknown homes {bad}; known {sorted(HOMES)}")
    return loops


def run(g):
    pf = preflight(Path(g.game_path))
    _RECORD["preflight"] = pf
    if pf["problems"]:
        g.check(False, "d9 preflight: bench 30950 + the WorldMap(9013) splice are live in " + LAB,
                "; ".join(pf["problems"]))
        _write(g)
        return
    mark = g.log_mark()
    loops = loops_from_env()
    _RECORD["plan"] = loops
    g.note(f"d9: Disc9 battle walk, loops {loops}")
    for k, home_key in enumerate(loops):
        lrec = {"label": f"L{k + 1}-{home_key}", "home": home_key, "home_xz": HOMES[home_key], "t0": time.time()}
        _RECORD["loops"].append(lrec)
        try:
            enter_9013(g, lrec)
            st = g.state
            if st.on_world:                       # one world load per loop: d9_post's (c) repetition count
                _RECORD.setdefault("world_loads", []).append({"loop": lrec["label"], "t": time.time(),
                                                              "world": st.world_id})
            lrec["battle"] = walk_until_battle(g, home_key, lrec)
        except HarnessError as err:
            lrec["error"] = str(err)
            g.note(f"d9 {lrec['label']}: {err}")
        finally:
            try:
                lrec["recovery"] = recover(g)
            except HarnessError as err:
                lrec["recovery"] = {"how": "FAILED", "why": str(err)}
        judge_loop(g, lrec)
        _write(g)
        if lrec["recovery"].get("how") == "FAILED":
            g.note("d9: recovery failed -- stopping the loops")
            break
    battles = [l["battle"] for l in _RECORD["loops"] if l.get("battle") and HOME_CELL[l["home"]] == "carry"]
    _RECORD["summary"] = {"carry_battles": [(b["scene"], (b.get("fire_class") or {}).get("topo"), b["walked_u"])
                                            for b in battles],
                          "recoveries": [l.get("recovery", {}).get("how") for l in _RECORD["loops"]]}
    g.check(len(battles) >= 3, f"d9: three random battles recorded on the carry ({len(battles)})",
            json.dumps(_RECORD["summary"]))
    try:
        exc = g.exceptions_since(mark)
        _RECORD["exceptions"] = [str(e) for e in exc][:20]
    except Exception as err:                          # noqa: BLE001 -- an instrument, never fatal
        _RECORD["exceptions_error"] = repr(err)
    _write(g)


if __name__ == "__main__":
    if "--preflight" in sys.argv:
        r = preflight(GAME_DEFAULT)
        print(json.dumps(r, indent=1, default=str))
        sys.exit(1 if r["problems"] else 0)
    print(__doc__)
