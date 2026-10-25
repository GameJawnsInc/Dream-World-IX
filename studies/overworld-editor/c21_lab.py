"""C21: the gold chocobo's camera in game -- and the airship's, boarded on foot.

    py studies/overworld-editor/c21_lab.py calibrate   # offline: the nudge discriminant on C8's stills (known truths)
    py studies/overworld-editor/c21_lab.py predict     # offline: the registered predictions, before the game opens
    py studies/overworld-editor/c21_lab.py capture     # the game: deploy the pepper room, the stills, revert, quit
    py studies/overworld-editor/c21_lab.py compare     # offline: each still against both nudge pairs

THE QUESTION. C8 decoded the gold chocobo in flight with the airship's final Y nudges, 1419 / 996, "once it has taken
off". The source says otherwise. FixTypeCam eases its nudges toward a TARGET (ff9.w_cameraUpdate, 25 a frame), and
the target is written in three places only:
  * w_movementChange (RunWorldCode 1), per type_cam: 0 and 1 -> 558 / 312, 2 -> 320 / 701, 3 -> 1419 / 996; for
    type_cam 4 (the gold chocobo flying) it sets the nudge but NOT the target, so the next frame eases it back;
  * RunScriptSync tag 19 -> 1419 / 996, and tag 21 -> 558 / 312 (EventEngine.DoEventCode REQEW, world mode only).
In WORLD07 the take-off is entry 2's request 9 ([190] = 6, RunWorldCode(1, 6), the chocobo's tag 18), never tag 19;
tag 19 is the Dead Pepper fed IN THE AIR (request 10: the rise toward the Air Garden, which comes back down when the
garden is not near). And tag 21 is the Hilda Garde III's boarding ON FOOT (request 16: [190] = 8, RunWorldCode(1, 8),
then RunScriptSync(5, 6, 21)). So the source predicts:
  P1  the gold chocobo after a take-off: 558 / 312 (C8's decode: 1419 / 996);
  P2  after a Dead Pepper in the air: 1419 / 996;
  P3  the Hilda Garde III boarded on foot: 558 / 312 (C8 measured it loaded aboard, where 1419 / 996 is right).

THE ROUTE. C8's boardings (veh_lib.reach_world_as: field 6603 at ScenarioCounter 10650 -> WORLD07, [190] / [191] and
the records poked, out of the door). The gold chocobo boards on the ground (mode 5, [191] 5, flags 809 / 810), is
teleported onto C8's forest spot (topograph 37: take-off and landing are forest-only, entry 2's switch on
topographs 36-38) and takes off with Confirm. The Dead Pepper comes from c21_pepper.field.toml, a scratch room at
31300 the new game passes through once (a new game has none, and the harness has no item verb); the chocobo's menu
(Triangle) needs Global.Byte[187] bit 0 too (poked). The airship: on foot, the Hilda Garde III parked at C8's LOW
record, the party teleported beside it, walked into it, Confirm.
The pepper room is deployed at the start of `capture` and reverted at its end; the game is closed after.

THE MEASURE. The stills are scored against the decode drawn twice, once per nudge pair, everything else equal: C8's
edge map and colour classes, the renders fogged as C18 measured (the no-mist year, as ScenarioCounter 10650 is). The
measure is first checked on C8's own stills, whose nudges are known (`calibrate`).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "terrain-malleability" / "ingame"))
import c1_lab as C1                                                    # noqa: E402  (pins the worktree package)
import c2_lab as C2                                                    # noqa: E402  (the shell steps)
import c7_compare as CMP                                               # noqa: E402

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
OUT = HERE / "out" / "c21_lab"
CAPTURE = HERE / "out" / "c21_capture.json"
COMPARE = HERE / "out" / "c21_compare.json"
CALIBRATE = HERE / "out" / "c21_calibrate.json"
PREDICT = HERE / "out" / "c21_predict.json"
EVIDENCE = HERE / "evidence" / "c21"
PEPPER_TOML = HERE / "c21_pepper.field.toml"
PEPPER_FIELD = 31300
CAMERA_SRC = Path(r"C:\gd\Dream-World-IX\studies\overworld-topography\west-seam-continent\camera_landing.bgx")
SETTLE = 120                                                           # frames for the eased eye / aim to stop

WALK = (558, 312)                                                      # the walker's nudges (type_cam 0 / 1, tag 21)
RISEN = (1419, 996)                                                    # the airship's (type_cam 3, tag 19)
BOAT = (320, 701)                                                      # the Blue Narciss's (type_cam 2)
FIXES = {"walk": WALK, "risen": RISEN, "boat": BOAT}


# ------------------------------------------------------------------------------------------------- the measure
def _setup():
    from ff9mapkit.world import fog as FG
    from ff9mapkit.world import gamecam as G
    from ff9mapkit.world import render as R
    stack = R.game_stack(GAME)
    return {"G": G, "R": R, "S": G.Settings.from_game(GAME), "table": G.transport_table(GAME), "stack": stack,
            "names": [p.name for p in stack],
            "gsites": {d: R.RenderSite(cells=(), disc=d, game=GAME, stack=stack) for d in (1, 4)},
            "fogs": {m: FG.from_game(GAME, mist=m) for m in (False, True)}, "FG": FG, "cache": {}}


def _disc_mist(row) -> tuple:
    """The still's disc and Mist year from its world: 9008 / 9009 are disc 4 (ScenarioCounter >= 11090, the Mist
    back: WorldConfiguration.UseMist, < 5990 or > 11090); 9003 / 9007 here are disc 1 at 9500 / 10650, no mist."""
    return (4, True) if int(row.get("world") or 0) in (9008, 9009) else (1, False)


def _site(env, row, w, h):
    """The render site around the still (cached), its disc's ground site and its year's fog."""
    R = env["R"]
    disc, mist = _disc_mist(row)
    bx, by = int(row["x"] // 64), int(-row["z"] // 64)
    key = (disc, bx, by, w, h)
    if key not in env["cache"]:
        cells = tuple((cx, cy) for cx in range(bx - 4, bx + 5) for cy in range(max(0, by - 4), min(20, by + 5)))
        site = R.RenderSite(cells=cells, disc=disc, game=GAME, stack=env["stack"], res=(w, h))
        env["cache"][key] = (site, R.load_batches(site, stock=True))
    return (*env["cache"][key], env["gsites"][disc], env["fogs"][mist])


def score_row(env, row, fixes=FIXES, *, save=None) -> dict:
    """The still against the decode drawn once per nudge pair in ``fixes``, everything else as world.gamecam decodes
    it: ``{name: {"edges", "classes"}}`` (C8's two measures; the renders fogged by world.fog)."""
    G, R = env["G"], env["R"]
    img = CMP._load(row["shot"])
    H, W = img.shape[:2]
    w, h = W // CMP.SCALE, H // CMP.SCALE
    gs = CMP._small(img, w, h)
    x, y, z = row["x"], row["y"], row["z"]
    site, batches, gsite, fog = _site(env, row, w, h)
    gq = C1._ground(gsite, x, z, env["names"])

    def ground(px, pz):
        return C1._ground(gsite, px % 1536.0, pz, env["names"]).get("y")
    region = CMP._region(h, w)
    ge, gc = CMP.edges(gs), CMP.classes(gs)
    out, frames = {}, [gs]
    for name, fix in fixes.items():
        v = G.pose((x, y, z), row["cam_rot"], settings=env["S"], area=int(gq.get("area", 14) or 0),
                   upper_counter=row.get("cam_upper") or 0, ground=ground, mode=int(row.get("ctl") or 0),
                   table=env["table"], topograph=gq.get("topograph"), fix=fix)
        v["reach"] = 600.0
        ri, dep = R.raster(v, batches, "c21", site=site, out_dir=None, verbose=False, want_depth=True)
        ri = env["FG"].fog_still(ri.clip(0, 255).astype(np.uint8), dep, v, fog).astype(np.float32)
        frames.append(ri)
        out[name] = {"edges": round(CMP.edge_score(ge, CMP.edges(ri), region), 4),
                     "classes": round(CMP.agree(gc, CMP.classes(ri, sky_rgb=R.SKY), region), 4),
                     "eye_y": round(v["eye"][1], 3), "aim_y": round(v["at"][1], 3)}
    if save:
        from PIL import Image
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.concatenate(frames, axis=1).clip(0, 255).astype(np.uint8)).save(OUT / f"{save}.png")
    return out


def _verdict(sc: dict, a: str, b: str) -> dict:
    """Which of nudge pairs ``a`` / ``b`` each measure prefers, and by how much."""
    return {m: {"pick": a if sc[a][m] > sc[b][m] else b, "margin": round(sc[a][m] - sc[b][m], 4)}
            for m in ("edges", "classes")}


# ------------------------------------------------------------------------------------------------- offline steps
def calibrate():
    """THE INSTRUMENT FIRST: on C8's stills the nudges are known from the source alone -- the airship LOADED aboard
    (w_movementChange, type_cam 3: 1419 / 996), the chocobo (type_cam 1: 558 / 312), the boat (type_cam 2: 320 /
    701). The discriminant must pick each still's own pair, or it cannot judge C21's."""
    rec = json.loads((HERE / "out" / "c8_capture.json").read_text(encoding="utf-8"))
    truth = {8: "risen", 1: "walk", 7: "boat"}
    env = _setup()
    rows, hits = [], {"edges": 0, "classes": 0}
    for row in rec["rows"]:
        if not row.get("shot") or not Path(row["shot"]).is_file():
            continue
        sc = score_row(env, row, save=f"cal-{row['spot']}-{row['turn']}")
        want = truth[int(row["ctl"])]
        picks = {m: max(sc, key=lambda k: sc[k][m]) for m in ("edges", "classes")}
        for m in hits:
            hits[m] += picks[m] == want
        rows.append({"still": f"{row['spot']}-{row['turn']}", "truth": want, "picks": picks, "scores": sc})
        print(rows[-1]["still"], "truth", want, "picks", picks,
              {k: (v["edges"], v["classes"]) for k, v in sc.items()})
    res = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": rows, "hits": hits, "n": len(rows)}
    CALIBRATE.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"hits: edges {hits['edges']}/{len(rows)}, classes {hits['classes']}/{len(rows)} -> {CALIBRATE}")


def predict():
    """The registered predictions, written before the game opens (the source's reading, quoted in the docstring)."""
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"),
           "P1": {"what": "gold chocobo after a take-off (request 9, tag 18)", "nudges": WALK,
                  "c8_decode": RISEN},
           "P2": {"what": "gold chocobo after a Dead Pepper in the air (request 10, tag 19)", "nudges": RISEN},
           "P3": {"what": "Hilda Garde III boarded on foot (request 16, tag 21)", "nudges": WALK,
                  "c8_decode": RISEN},
           "P0": {"what": "the gold chocobo on the ground before the take-off (type_cam 1)", "nudges": WALK},
           # run 2, registered after run 1 from the per-world census of tags 19 / 21 (C21.md): Memoria's hook keys
           # on the tag NUMBER, and WORLD08 / 09 number the chocobo's functions differently from WORLD00-07
           "P4": {"what": "disc 4 (WORLD08): the gold chocobo after a take-off (request 9 runs tag 19 there)",
                  "nudges": RISEN},
           "P5": {"what": "disc 4: after a Dead Pepper in the air (tag 20 there: no hook, the take-off's stays)",
                  "nudges": RISEN},
           "P6": {"what": "WORLD03: the Blue Narciss boarded on foot (request 12: [190] = 7, then tag 21)",
                  "nudges": WALK, "c8_decode": BOAT},
           "P7": {"what": "disc 4: the Invincible boarded on foot (no tag 19 / 21 on its path: type_cam 3's own)",
                  "nudges": RISEN},
           "judged_by": "each still's edge score with the predicted pair above the other pair's"}
    PREDICT.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps(rec, indent=1))


PREP2 = HERE / "out" / "c21_prep2.json"


def _record(x, y, z, face=192, base=74) -> dict:
    """A vehicle record at ``base`` (74 boat / airship, 83 chocobo): x, z Int24 and y Int16 in 1/256 units, the face."""
    import c8_lab as C8
    return {str(int(k) - 74 + base): v for k, v in C8.record(x, y, z, face).items()}


def prep2():
    """Run 2's spots, on the live stack (every folder, as the game draws it):
      * disc 4: the nearest forest cell (topograph 36-38) to C8's forest spot, for the take-off; a flat lawn near
        C8's LOW for the Invincible (its record, the party beside it);
      * disc 1 (WORLD03): a beach whose water starts within 4u, the Blue Narciss's record just off it and the party
        on the sand facing it."""
    from ff9mapkit.world import render as R
    stack = R.game_stack(GAME)
    names = [p.name for p in stack]
    s4 = R.RenderSite(cells=(), disc=4, game=GAME, stack=stack)
    s1 = R.RenderSite(cells=(), disc=1, game=GAME, stack=stack)
    p = json.loads((HERE.parents[0] / "terrain-malleability" / "ingame" / "out" / "veh_prep.json")
                   .read_text(encoding="utf-8"))
    out = {}
    fx, fz = p["choco"]["forest"]["world"]
    best = None
    for r in [0] + list(range(4, 200, 4)):
        for k in range(0, 360, 15 if r else 360):
            x, z = fx + r * math.cos(math.radians(k)), fz + r * math.sin(math.radians(k))
            g = C1._ground(s4, x, z, names)
            if g.get("topograph") in (36, 37, 38) and all(C1._ground(s4, x + dx, z + dz, names).get("topograph")
                                                         in (36, 37, 38) for dx, dz in ((3, 0), (-3, 0), (0, 3), (0, -3))):
                best = {"world": [round(x, 2), round(z, 2)], "ground": g.get("y"), "topo": g.get("topograph")}
                break
        if best:
            break
    out["forest4"] = best
    lx, lz = p["air"]["low"]["world"]
    g = C1._ground(s4, lx, lz, names)
    out["low4"] = {"world": [lx, lz], "ground": g.get("y"), "topo": g.get("topograph"),
                   "record": _record(lx, g.get("y") or 0.0, lz)}
    # the boat: walk C8's beach-to-water edge (veh_prep choco.edge) on disc 1 as the live stack reads it
    e = p["choco"]["edge"]
    bx, bz, bear = e["start"][0], e["start"][1], e["bearing"]
    prof = []
    for d in [i * 0.5 for i in range(0, 30)]:
        x, z = bx + d * math.cos(math.radians(bear)), bz + d * math.sin(math.radians(bear))
        g = C1._ground(s1, x, z, names)
        prof.append((d, g.get("topograph"), g.get("part"), None if g.get("y") is None else round(g["y"], 3)))
    wet = next((d for d, topo, part, y in prof if topo in (53, 54, 55, 56, 57)), None)   # the sand reads Beach1
    out["beach"] = {"start": [bx, bz], "bearing": bear, "profile": prof, "water_at": wet}
    if wet is not None:
        sx, sz = bx, bz                                                  # the party on the sand, the hull 2u off it
        ox, oz = bx + (wet + 2.0) * math.cos(math.radians(bear)), bz + (wet + 2.0) * math.sin(math.radians(bear))
        out["beach"].update({"stand": [round(sx, 2), round(sz, 2)], "boat": [round(ox, 2), round(oz, 2)],
                             "record": _record(ox, 0.0, oz)})
    PREP2.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "profile"} if isinstance(v, dict) else v
                      for k, v in out.items()}, indent=1))


# ------------------------------------------------------------------------------------------------- the game
def _row(g, rows, spot, turn, **extra):
    g.wait_frames(SETTLE)
    st = g.state
    row = {"spot": spot, "turn": turn, "x": st.world_x, "y": st.world_y, "z": st.world_z,
           "cam_rot": st.world_cam_rot, "cam_upper": st.world_cam_upper, "ctl": st.world_ctl, "world": st.world_id,
           "vehicle": st.vehicle, **extra}
    rows.append(row)
    row["shot"] = str(g.shot(f"c21-{spot}-{turn}"))
    (g.run_dir / "c21_capture.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    return row


def _y_track(g, frames: int, every: int = 3) -> list:
    out = []
    for _ in range(max(1, frames // every)):
        g.wait_frames(every)
        out.append(round(g.state.world_y, 3))
    return out


def _gold(g, rows, rec, V, *, tag, forest, world):
    """The gold chocobo, boarded on the ground: a still there, the take-off (Confirm on forest), three stills in
    flight (one turned, one back), the Dead Pepper from its menu, two stills after it."""
    g.check(g.state.world_ctl == 5, f"{tag}: on the gold chocobo, on the ground", json.dumps(V.here(g), default=str))
    V.tp(g, *forest)
    _row(g, rows, f"{tag}-ground", 0)
    g.press("confirm", 4)                                               # the take-off (forest only)
    rec["takeoff_y"] = _y_track(g, 90)
    V.settle3(g)
    g.check(g.state.world_ctl == 6 and g.state.vehicle == 6, f"{tag}: the gold chocobo took off",
            json.dumps(V.here(g), default=str))
    _row(g, rows, f"{tag}-fly", 0)
    g.send("hold leftbumper 24", "wait 26")
    V.settle3(g)
    _row(g, rows, f"{tag}-fly", 1)
    g.send("hold rightbumper 24", "wait 26")                           # back to the first heading for the pair
    V.settle3(g)
    _row(g, rows, f"{tag}-fly", 2)
    g.press("menu", 4)                                                  # the chocobo's menu: the Dead Pepper
    g.wait_dialogue(timeout=10.0)
    rec["menu"] = {"text": g.state.text, "choice": g.state.choice}
    rec["pick"] = g.choose_landed(1)
    rec["rise_y"] = _y_track(g, 240)
    V.settle3(g)
    g.check(g.state.world_ctl == 6 and g.state.world_id == world, f"{tag}: still flying after the Dead Pepper",
            json.dumps(V.here(g), default=str))
    _row(g, rows, f"{tag}-risen", 0)
    g.send("hold leftbumper 24", "wait 26")
    V.settle3(g)
    _row(g, rows, f"{tag}-risen", 1)


def _on_foot(g, rows, rec, V, *, tag, at, mode, bearings, stand=9.0, face_tol=6.0):
    """A vehicle parked at ``at``, boarded ON FOOT: stand off it along each bearing in turn, walk into it, Confirm,
    until the travel mode is ``mode``; two stills aboard."""
    g.check(g.state.world_ctl == 0, f"{tag}: on foot beside the parked vehicle", json.dumps(V.here(g), default=str))
    tries = []
    for bearing in bearings:
        sx = at[0] - stand * math.cos(math.radians(bearing))          # (bearings are atan2(dz, dx): world_face)
        sz = at[1] - stand * math.sin(math.radians(bearing))
        V.tp(g, sx, sz)
        g.world_face(bearing, home=(sx, sz), tolerance=face_tol)
        walk = g.world_approach(bearing, stand)
        g.press("confirm", 4)
        g.wait_frames(240)
        V.settle3(g)
        tries.append({"bearing": bearing, "walk": walk.get("outcome"), "ctl": g.state.world_ctl, "here": V.here(g)})
        if g.state.world_ctl == mode:
            break
    rec["tries"] = tries
    g.check(g.state.world_ctl == mode, f"{tag}: boarded on foot", json.dumps(tries, default=str))
    _row(g, rows, f"{tag}-boarded", 0)
    g.send("hold leftbumper 24", "wait 26")
    V.settle3(g)
    _row(g, rows, f"{tag}-boarded", 1)


def capture_scenario(g):
    """Run by tools/play.py. Run 1 (WORLD07, disc 1): the gold chocobo, then the Hilda Garde III boarded on foot.
    Run 2 (``C21_RUN=2``): the gold chocobo on disc 4 (WORLD08), the Invincible boarded on foot there, the Blue
    Narciss boarded on foot in WORLD03. A failed group records why and the next still runs."""
    import os
    import traceback
    import veh_lib as V
    p = json.loads((HERE / "out" / "c8_prep.json").read_text(encoding="utf-8"))
    rows, rec = [], {}
    first = [True]
    real_newgame = g.newgame

    def newgame(*a, **k):                                              # the new game passes the pepper room once
        r = real_newgame(*a, **k)
        g.warp(PEPPER_FIELD)
        g.wait_frames(120)
        rec.setdefault("pepper", {})["field"] = g.state.field_id if hasattr(g.state, "field_id") else None
        return r
    g.newgame = newgame

    def board(name, sc, pokes, flags=(), world=None):
        V.reach_world_as(g, rec.setdefault(name, {}), scenario=sc, pokes=pokes, flags=flags,
                         expect_world=world, first=first[0])
        first[0] = False

    def group(name, fn):
        try:
            fn()
        except Exception:                                               # noqa: BLE001 -- the next group still runs
            rows.append({"spot": name, "error": traceback.format_exc()})
    if os.environ.get("C21_RUN") == "3":                               # the boat again: run 2's ended in a battle
        q = json.loads(PREP2.read_text(encoding="utf-8"))

        def boat3():
            b = q["beach"]
            pokes = {190: 0, 191: 0, **{int(k): v for k, v in b["record"].items()}}
            board("boat", 9500, pokes, world=9003)
            g.no_encounters(True)                                       # world_face's probes walk ~30u at level 1
            _on_foot(g, rows, rec["boat"], V, tag="boat", at=b["boat"], mode=7, bearings=(float(b["bearing"]),),
                     stand=math.dist(b["stand"], b["boat"]), face_tol=20.0)   # the sand is slow: the hull is wide
        group("boat", boat3)
    elif os.environ.get("C21_RUN") == "2":
        q = json.loads(PREP2.read_text(encoding="utf-8"))
        group("gold4", lambda: (board("gold4", 11101, {190: 5, 191: 5, 187: 1}, flags=(809, 810), world=9008),
                                _gold(g, rows, rec["gold4"], V, tag="gold4", forest=q["forest4"]["world"],
                                      world=9008)))

        def inv():
            pokes = {190: 0, 191: 0, **{int(k): v for k, v in q["low4"]["record"].items()}}
            board("inv", 11101, pokes, world=9008)
            _on_foot(g, rows, rec["inv"], V, tag="inv", at=q["low4"]["world"], mode=9, bearings=(0.0, 180.0, 90.0, 270.0))
        group("inv", inv)

        def boat():
            b = q["beach"]
            pokes = {190: 0, 191: 0, **{int(k): v for k, v in b["record"].items()}}
            board("boat", 9500, pokes, world=9003)
            _on_foot(g, rows, rec["boat"], V, tag="boat", at=b["boat"], mode=7, bearings=(float(b["bearing"]),),
                     stand=math.dist(b["stand"], b["boat"]))
        group("boat", boat)
    else:
        group("gold", lambda: (board("gold", 10650, {190: 5, 191: 5, 187: 1}, flags=(809, 810), world=9007),
                               _gold(g, rows, rec["gold"], V, tag="gold", forest=p["choco"]["forest"]["world"],
                                     world=9007)))

        def air():
            pokes = {190: 0, 191: 0, **{int(k): v for k, v in p["air"]["spawn"]["record"].items()}}
            board("air", 10650, pokes, world=9007)
            _on_foot(g, rows, rec["air"], V, tag="air", at=p["air"]["low"]["world"], mode=8,
                     bearings=(0.0, 180.0, 90.0, 270.0))
        group("air", air)
    (g.run_dir / "c21_capture.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    (g.run_dir / "c21_route.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")


def run(g):                                                            # tools/play.py's entry
    capture_scenario(g)


def _archived(name, label):
    runs = sorted((REPO / ".harness-runs").glob(f"*-{label}"))
    if not runs or not (runs[-1] / name).is_file():
        return None
    data = json.loads((runs[-1] / name).read_text(encoding="utf-8"))
    for row in data if isinstance(data, list) else ():
        if row.get("shot") and not Path(row["shot"]).is_file():
            cand = list(runs[-1].rglob(Path(row["shot"]).name))
            if cand:
                row["shot"] = str(cand[-1])
    return data


def _capture_path(run: int) -> Path:
    return CAPTURE if run == 1 else HERE / "out" / f"c21_capture{run}.json"


def capture(run: int = 1):
    import os
    py = sys.executable
    label = "c21-capture" if run == 1 else f"c21-capture{run}"
    os.environ["C21_RUN"] = str(run)                                    # read by capture_scenario in play.py
    OUT.mkdir(parents=True, exist_ok=True)
    cam = OUT / "camera_1659.bgx"                                       # the pepper room's borrowed camera (game bytes)
    if not cam.is_file():
        cam.write_bytes(CAMERA_SRC.read_bytes())
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "run": run}
    dep = C2._sh([py, "tools/deploy_field.py", PEPPER_TOML, "--id", str(PEPPER_FIELD), "--mod-folder", "FF9CustomMap"],
                 900)
    rec["deploy_rc"] = dep.returncode
    (OUT / f"deploy_stdout{run}.txt").write_text(dep.stdout + "\n--- stderr ---\n" + dep.stderr, encoding="utf-8")
    assert dep.returncode == 0, dep.stdout[-1500:] + dep.stderr[-1500:]
    try:
        r = C2._sh([py, "tools/play.py", Path(__file__), "--keep-open", "--label", label], 2400)
        rec["capture_rc"] = r.returncode
        (OUT / f"capture_stdout{run}.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", f"{label}-quit"], 300)  # close it
        rv = [ln.split("revert:", 1)[1].split("(")[0].strip() for ln in dep.stdout.splitlines()
              if ln.startswith("revert:")]                              # deploy_field's own per-id revert script
        rec["revert"] = rv
        if rv:
            rr = subprocess.run([py, rv[-1]], cwd=REPO, capture_output=True, text=True, timeout=600)
            rec["revert_rc"] = rr.returncode
            rec["revert_out"] = (rr.stdout + rr.stderr)[-1500:]
    rec["rows"] = _archived("c21_capture.json", label) or []
    rec["route"] = _archived("c21_route.json", label) or {}
    _capture_path(run).write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for row in rec["rows"]:
        print({k: (v if k != "error" else v[-900:]) for k, v in row.items() if k != "shot"})


def _vshift(a, b, region, span=40) -> int:
    """The vertical shift (rows, at the compare scale) that best lays frame ``b``'s edge map on ``a``'s: positive when
    ``b``'s picture sits LOWER (the camera rose or tipped up)."""
    ea, eb = CMP.edges(a), CMP.edges(b)
    best = (-2.0, 0)
    for s in range(-span, span + 1):
        sh = np.roll(eb, -s, axis=0)
        reg = region.copy()
        if s > 0:
            reg[-s:] = False
        elif s < 0:
            reg[:-s] = False
        sc = CMP.edge_score(ea, sh, reg)
        if sc > best[0]:
            best = (sc, s)
    return best[1]


def _pair(env, ra, rb) -> dict:
    """Still ``ra`` -> still ``rb``: how much the game's frame changed and moved, against the same change drawn by the
    decode with the walker's nudges on ``ra`` and the risen ones on ``rb`` (the source's reading of the pepper)."""
    G, R = env["G"], env["R"]
    a, b = CMP._load(ra["shot"]), CMP._load(rb["shot"])
    h, w = a.shape[0] // CMP.SCALE, a.shape[1] // CMP.SCALE
    sa, sb = CMP._small(a, w, h), CMP._small(b, w, h)
    reg = CMP._region(h, w)
    renders = {}
    for name, fix in (("walk", WALK), ("risen", RISEN)):
        x, y, z = ra["x"], ra["y"], ra["z"]
        site, batches, gsite, fog = _site(env, ra, w, h)
        gq = C1._ground(gsite, x, z, env["names"])
        v = G.pose((x, y, z), ra["cam_rot"], settings=env["S"], area=int(gq.get("area", 14) or 0),
                   upper_counter=0, mode=int(ra["ctl"]), table=env["table"], topograph=gq.get("topograph"),
                   ground=lambda px, pz: C1._ground(gsite, px % 1536.0, pz, env["names"]).get("y"), fix=fix)
        v["reach"] = 600.0
        ri, dep = R.raster(v, batches, "c21", site=site, out_dir=None, verbose=False, want_depth=True)
        renders[name] = env["FG"].fog_still(ri.clip(0, 255).astype(np.uint8), dep, v, fog).astype(np.float32)
    return {"a": f"{ra['spot']}-{ra['turn']}", "b": f"{rb['spot']}-{rb['turn']}",
            "dy": round(rb["y"] - ra["y"], 3), "drot": round(rb["cam_rot"] - ra["cam_rot"], 3),
            "frame_mae": round(float(np.abs(sa - sb)[reg].mean()), 3),
            "edges_between": round(CMP.edge_score(CMP.edges(sa), CMP.edges(sb), reg), 4),
            "game_vshift": _vshift(sa, sb, reg),
            "decode_vshift_walk_to_risen": _vshift(renders["walk"], renders["risen"], reg),
            "decode_mae_walk_to_risen": round(float(np.abs(renders["walk"] - renders["risen"])[reg].mean()), 3)}


#: per still: (the pair the source predicts, the pair it is told apart from) -- the registered P0-P7
PREDICTED = {"gold-ground": ("walk", "risen"), "gold-fly": ("walk", "risen"), "gold-risen": ("risen", "walk"),
             "air-boarded": ("walk", "risen"),
             "gold4-ground": ("walk", "risen"), "gold4-fly": ("risen", "walk"), "gold4-risen": ("risen", "walk"),
             "inv-boarded": ("risen", "walk"), "boat-boarded": ("walk", "boat")}


def _yellow_feet(img):
    """The gold chocobo's lowest saturated-yellow row in the middle fifth of the frame (its feet), or None."""
    H, W = img.shape[:2]
    r, g_, b = img[..., 0], img[..., 1], img[..., 2]
    m = (r > 170) & (g_ > 140) & (b < 110) & (r - b > 90)
    m[:, :int(W * 0.4)] = False
    m[:, int(W * 0.6):] = False
    ys = np.nonzero(m)[0]
    return int(ys.max()) if len(ys) > 30 else None


def _party_row(v, p, H):
    """The screen row the camera ``v`` draws world point ``p`` at, in a frame ``H`` rows tall."""
    eye = np.asarray(v["eye"], dtype=float)
    fwd = np.asarray(v["at"], dtype=float) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross([0.0, 1.0, 0.0], fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    d = np.asarray(p, dtype=float) - eye
    return H / 2.0 - (H / 2.0) / math.tan(math.radians(v["fov"]) / 2.0) * float(d @ up) / float(d @ fwd)


def _sprite(env, row) -> dict | None:
    """THE PARTY'S OWN ROW: where the decode draws the party under each nudge pair, beside where the game drew the
    gold chocobo's feet. The aim nudge moves the party in the frame with no terrain in between, so this witness needs
    no render; the feet sit a constant few rows off the projected point (the model's own offset), which the ground
    still -- C8's confirmed chocobo camera -- measures."""
    G = env["G"]
    img = CMP._load(row["shot"])
    feet = _yellow_feet(img)
    if feet is None:
        return None
    _s, _b, gsite, _f = _site(env, row, img.shape[1] // CMP.SCALE, img.shape[0] // CMP.SCALE)
    gq = C1._ground(gsite, row["x"], row["z"], env["names"])
    out = {"feet_row": feet}
    for name, fix in (("walk", WALK), ("risen", RISEN)):
        v = G.pose((row["x"], row["y"], row["z"]), row["cam_rot"], settings=env["S"],
                   area=int(gq.get("area", 14) or 0), mode=int(row["ctl"]), table=env["table"],
                   topograph=gq.get("topograph"), fix=fix,
                   ground=lambda px, pz: C1._ground(gsite, px % 1536.0, pz, env["names"]).get("y"))
        out[name] = round(_party_row(v, (row["x"], row["y"], row["z"]), img.shape[0]), 1)
    return out


def compare():
    pred = json.loads(PREDICT.read_text(encoding="utf-8"))
    env = _setup()
    rows, sprites, by = [], {}, {}
    caps = [json.loads(_capture_path(n).read_text(encoding="utf-8")) for n in (1, 2, 3) if _capture_path(n).is_file()]
    for rec in caps:
        for row in rec["rows"]:
            if "error" in row or not row.get("shot") or row["spot"] not in PREDICTED:
                continue
            name = f"{row['spot']}-{row['turn']}"
            by[name] = row
            exp, alt = PREDICTED[row["spot"]]
            sc = score_row(env, row, {exp: FIXES[exp], alt: FIXES[alt]}, save=f"cmp-{name}")
            v = _verdict(sc, exp, alt)
            rows.append({"still": name, "world": row["world"], "ctl": row["ctl"], "y": round(row["y"], 3),
                         "cam_rot": row["cam_rot"], "predicted": exp, "against": alt, "verdict": v, "scores": sc,
                         "holds": {m: v[m]["pick"] == exp for m in v}})
            if row["spot"].startswith("gold"):
                s = _sprite(env, row)
                if s:
                    sprites[name] = s
            print(name, "predicted", exp, "vs", alt, {m: (v[m]["pick"], v[m]["margin"]) for m in v})
    # the sprite verdict: the ground still's feet-to-party offset (the walker's camera, C8-confirmed) is the model's
    # own; each flying still is judged by which pair's party row leaves that same offset
    for tag in ("gold", "gold4"):
        base = sprites.get(f"{tag}-ground-0")
        if not base:
            continue
        off = base["feet_row"] - base["walk"]
        for k, s in sprites.items():
            if k.rsplit("-", 2)[0] != tag:
                continue
            res = {n: round(s["feet_row"] - s[n] - off, 1) for n in ("walk", "risen")}
            s.update({"offset_ref": round(off, 1), "residual": res, "pick": min(res, key=lambda n: abs(res[n])),
                      "predicted": PREDICTED[k.rsplit("-", 1)[0]][0]})
            s["holds"] = s["pick"] == s["predicted"]
            print("sprite", k, s)
    # THE PAIRED WITNESS: fly-2 and risen-0 stand at the same place, height and yaw; only the Dead Pepper lies
    # between them (fly-2 / fly-0, the same nudges 1 degree of yaw apart, is the control)
    pairs = {}
    for tag in ("gold", "gold4"):
        if all(f"{tag}-{k}" in by for k in ("fly-0", "fly-2", "risen-0")):
            pairs[tag] = {"pepper": _pair(env, by[f"{tag}-fly-2"], by[f"{tag}-risen-0"]),
                          "control": _pair(env, by[f"{tag}-fly-2"], by[f"{tag}-fly-0"])}
    res = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "predictions": pred, "rows": rows, "sprites": sprites,
           "pairs": pairs, "routes": [rec.get("route") for rec in caps]}
    COMPARE.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for src in (PREDICT, CALIBRATE, COMPARE, PREP2):
        if src.is_file():
            data = json.loads(src.read_text(encoding="utf-8"))
            (EVIDENCE / src.name).write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
    print("pairs:", json.dumps(pairs), "->", COMPARE)


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    fn = {"calibrate": calibrate, "predict": predict, "prep2": prep2, "capture": capture,
          "capture2": lambda: capture(2), "capture3": lambda: capture(3), "compare": compare}.get(cmd[0] if cmd else "")
    if fn is None:
        raise SystemExit(__doc__)
    fn()
