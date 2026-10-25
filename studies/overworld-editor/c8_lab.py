"""C8: the game's own camera ON A VEHICLE, measured -- the airship, a chocobo and the boat.

    py studies/overworld-editor/c8_lab.py prep      # offline: the boat's open-sea spawn record (the old lane is land now)
    py studies/overworld-editor/c8_lab.py capture   # the game: board each vehicle, stills with the live camera state
    py studies/overworld-editor/c8_lab.py compare   # offline: world.gamecam's vehicle pose, rendered, against each still

THE BOARDINGS are the vehicle study's DLL-free routes (studies/terrain-malleability/ingame/veh_lib.py, veh_PLAN.md
section 2): warp to field 6603 at the ScenarioCounter whose exit cascade loads the wanted dispatcher, poke
gEventGlobal[190] (+[191]) and the vehicle's record, walk out of the door -- the load-time binding a save loaded aboard
uses, so the vehicle is the real one, with the real altitude:
  * the Hilda Garde III (mode 8, type 1 flight, type_cam 3): SC 10650 -> WORLD07, the record at LOW (veh_prep);
    stills on its spawn ground, climbed, over HIGH (the floor raise lifts it to 28.9) and at the 42.19 ceiling over
    the summit, one of them turned;
  * a yellow chocobo (mode 1, type 0, type_cam 1): SC 10650 + [191] 1 + flags 809/810 -> WORLD07; stills on lawn and
    over forest (topograph 37: the chocobo's forest field of view);
  * the Blue Narciss (mode 7, type 2 boat, type_cam 2): SC 9500 -> WORLD03, at a FRESH open-sea record (`prep`: the
    vehicle study's lane at (21,1) is the comma the editor carried there in C5).
Nothing is deployed. The game is closed at the end.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "terrain-malleability" / "ingame"))
import c1_lab as C1                                                    # noqa: E402  (the paths, the ground probe)
import c2_lab as C2                                                    # noqa: E402  (the shell steps)

GAME, KIT, REPO = C1.GAME, C1.KIT, C1.REPO
OUT = HERE / "out" / "c8_lab"
PREP = HERE / "out" / "c8_prep.json"
CAPTURE = HERE / "out" / "c8_capture.json"
COMPARE = HERE / "out" / "c8_compare.json"
SETTLE = 120                                                           # frames for the eased eye / aim to stop


def record(x: float, y: float, z: float, face: int = 192) -> dict:
    """A boat / airship record, gEventGlobal Int24[74] Int16[77] Int24[79] Byte[82]: x, y, z in 1/256 units."""
    def le(v, n):
        v = int(round(v * 256.0)) & ((1 << (8 * n)) - 1)
        return [(v >> (8 * k)) & 0xFF for k in range(n)]
    b = le(x, 3) + le(y, 2) + le(z, 3) + [int(face) & 0xFF]
    return {str(74 + i): v for i, v in enumerate(b)}


def prep():
    """The boat's spawn: the nearest point to the Landing Site that the LIVE stack (every folder, as the game draws
    it) reads as deep sea (Sea4, topograph 57), off stock land, with land 24-60u away (a coast in frame). Measured
    2026-10-23: (257.76, -381.15), 24u off the island C5 minted at block (4,5)."""
    from ff9mapkit.world import render as R
    from ff9mapkit.world.islandedit import stock_land
    names = [p.name for p in R.game_stack(GAME)]
    site = R.RenderSite(cells=(), disc=1, game=GAME, stack=tuple(GAME / n for n in names))
    land = stock_land(game=GAME)
    vp = json.loads((HERE.parents[0] / "terrain-malleability" / "ingame" / "out" / "veh_prep.json")
                    .read_text(encoding="utf-8"))
    assert vp["air"]["spawn"]["record"] == record(*vp["air"]["spawn"]["world"][:1], vp["air"]["spawn"]["y"],
                                                  vp["air"]["spawn"]["world"][1]), "the record encoding is not veh_prep's"
    kx, kz = C1.CONTROL[1:]
    best = None
    for r in range(40, 400, 8):
        for k in range(0, 360, 10):
            x, z = kx + r * math.cos(math.radians(k)), kz + r * math.sin(math.radians(k))
            blk = (int(x // 64) % 24, int(-z // 64))
            if blk in land:
                continue
            g = C1._ground(site, x, z, names)
            if g.get("part") != "Sea4" or g.get("topograph") != 57:
                continue
            near = [d for d in range(8, 64, 8)
                    for a in range(0, 360, 30)
                    if C1._ground(site, x + d * math.cos(math.radians(a)), z + d * math.sin(math.radians(a)),
                                  names).get("part") == "Terrain"]
            if near and 24 <= min(near) <= 60:
                best = (round(x, 2), round(z, 2), blk, min(near))
                break
        if best:
            break
    assert best, "no deep-sea spawn with a coast in frame near the Landing Site"
    out = {"boat": {"world": [best[0], best[1]], "block": list(best[2]), "coast_u": best[3], "y": 0.0,
                    "record": record(best[0], 0.0, best[1])},
           "air": vp["air"], "choco": vp["choco"]}
    PREP.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out["boat"]), "->", PREP)


def _row(g, rows, spot, turn):
    g.wait_frames(SETTLE)
    st = g.state
    row = {"spot": spot, "turn": turn, "x": st.world_x, "y": st.world_y, "z": st.world_z,
           "cam_rot": st.world_cam_rot, "cam_upper": st.world_cam_upper, "ctl": st.world_ctl, "world": st.world_id}
    rows.append(row)
    row["shot"] = str(g.shot(f"c8-{spot}-{turn}"))
    (g.run_dir / "c8_capture.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    return row


def capture_scenario(g):
    """Run by tools/play.py: every vehicle's stills, the state beside each; a failed vehicle records why and the next
    one still runs (from the world, through the 6603 round trip)."""
    import traceback
    import veh_lib as V
    p = json.loads(PREP.read_text(encoding="utf-8"))
    rows, rec = [], {}
    first = True

    def board(name, sc, pokes, flags=(), world=None):
        nonlocal first
        V.reach_world_as(g, rec.setdefault(name, {}), scenario=sc, pokes=pokes, flags=flags,
                         expect_world=world, first=first)
        first = False
    try:                                                                # the airship
        pokes = {190: 8, 191: 0}
        pokes.update({int(k): v for k, v in p["air"]["spawn"]["record"].items()})
        board("air", 10650, pokes, world=9007)
        g.check(g.state.world_ctl == 8, "aboard the Hilda Garde III", json.dumps(V.here(g), default=str))
        _row(g, rows, "air-spawn", 0)
        climb = V.calibrate_climb(g, rec["air"]) or "down"
        g.hold(climb, 50)
        _row(g, rows, "air-climbed", 0)
        g.send("hold leftbumper 24", "wait 26")
        _row(g, rows, "air-climbed", 1)
        V.tp(g, *p["air"]["high"]["world"])
        _row(g, rows, "air-high", 0)
        V.tp(g, *p["air"]["summit"]["world"])
        _row(g, rows, "air-ceiling", 0)
    except Exception:                                                   # noqa: BLE001 -- the next vehicle still runs
        rows.append({"spot": "air", "error": traceback.format_exc()})
    try:                                                                # a yellow chocobo
        board("choco", 10650, {190: 1, 191: 1}, flags=(809, 810), world=9007)
        g.check(g.state.world_ctl == 1, "on the yellow chocobo", json.dumps(V.here(g), default=str))
        V.tp(g, *p["choco"]["lawn"]["world"])
        _row(g, rows, "choco-lawn", 0)
        g.send("hold leftbumper 24", "wait 26")
        _row(g, rows, "choco-lawn", 1)
        V.tp(g, *p["choco"]["forest"]["world"])
        _row(g, rows, "choco-forest", 0)
    except Exception:                                                   # noqa: BLE001
        rows.append({"spot": "choco", "error": traceback.format_exc()})
    try:                                                                # the Blue Narciss
        pokes = {190: 7, 191: 0}
        pokes.update({int(k): v for k, v in p["boat"]["record"].items()})
        board("boat", 9500, pokes, world=9003)
        g.check(g.state.world_ctl == 7, "aboard the Blue Narciss", json.dumps(V.here(g), default=str))
        _row(g, rows, "boat", 0)
        g.send("hold leftbumper 24", "wait 26")
        _row(g, rows, "boat", 1)
    except Exception:                                                   # noqa: BLE001
        rows.append({"spot": "boat", "error": traceback.format_exc()})
    (g.run_dir / "c8_capture.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")


def run(g):                                                            # tools/play.py's entry
    capture_scenario(g)


def _archived_rows():
    """The last capture's rows, each still's path pointed at the run's own archive (the harness moves the stills out
    of the game folder when the run ends; they never enter the repo)."""
    runs = sorted((REPO / ".harness-runs").glob("*-c8-capture"))
    if not runs or not (runs[-1] / "c8_capture.json").is_file():
        return []
    rows = json.loads((runs[-1] / "c8_capture.json").read_text(encoding="utf-8"))
    for row in rows:
        if row.get("shot") and not Path(row["shot"]).is_file():
            cand = list(runs[-1].rglob(Path(row["shot"]).name)) or \
                [p for r in (REPO / ".harness-runs").glob("*") for p in r.glob("shots/" + Path(row["shot"]).name)]
            if cand:
                row["shot"] = str(cand[-1])
    return rows


def capture():
    py = sys.executable
    OUT.mkdir(parents=True, exist_ok=True)
    rec = {"t": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        r = C2._sh([py, "tools/play.py", Path(__file__), "--keep-open", "--label", "c8-capture"], 1800)
        rec["capture_rc"] = r.returncode
        (OUT / "capture_stdout.txt").write_text(r.stdout + "\n--- stderr ---\n" + r.stderr, encoding="utf-8")
    finally:
        C2._sh([py, "tools/play.py", HERE / "a1_quit.py", "--attach", "--label", "c8-quit"], 300)   # close the game
    rec["rows"] = _archived_rows()
    CAPTURE.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    for row in rec.get("rows", []):
        print({k: (v if k != "error" else v[-600:]) for k, v in row.items() if k != "shot"})


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["prep"]:
        prep()
    elif cmd == ["capture"]:
        capture()
    elif cmd == ["compare"]:
        import c7_compare
        c7_compare.main(capture=CAPTURE, compare=COMPARE, prefix="c8")
    else:
        raise SystemExit(__doc__)
