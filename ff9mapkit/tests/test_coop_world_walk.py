"""[ff9mapkit netsync s166] WORLD WALK, ROUND A -- the bench's repo half (studies/test-harness/scenarios/coop_world_walk.py) and the
contract / stand-in pins of its pieces. THIS STEP: PIECE A0, decision 19's CONTROL-OFF KIT-CELL CLOSE (studies/world-coop/S166-DESIGN.md).

  * THE CONTRACT: `netsync.world.kitcell` at its catch-line sentinel as netsync.world's LAST key (after `dot`), the `worldwalk` verb's
    ops / words / refusals, the log prefixes, the rung the ladder's last -- battlewire's, the driver's and the stand-in's in one place;
    once the engine's s166 patch is on the stack (or FF9_S166_CLONE names a clone carrying the tag) the same against ITS source.
  * THE TWIN: battlewire.kit_cell_close_rule's truth table, and every one-line mutant of it fails a row (a sid-0-only close fails the
    ferryman's, a close that ignores control fails the control-on one, a stock-entry close fails the stock read's).
  * THE STAND-IN'S ENGINE FACTS, each row able to fail: the kit cells (entry 0) read a bare Confirm requested whatever control says,
    the boat and the ferryman in their boxes, entry 1's stock read evaluated control-off -- under BOTH entry orders (an order-dependent
    close passes one and fails the other); the ~ menu's "Disable control" hold (the harness cannot drive it in game); a host and a
    control-on read untouched.
  * EVERY LEG SMOKED AGAINST THE STAND-IN through the real Session: green on the s166 stand-in under both orders; on the s165 one
    exactly OLD_PREDICTED red with the hazard MEASURED and no `worldwalk` op sent; under `kitcell old` exactly LEVER_PREDICTED; each
    fault lever exactly its SOLO_FAULT_REDS (ORDER_FAULT_REDS under entry 1 first); the calibration itself can fail (a lever the engine
    ignores, a leg that never measured its hazard, two destructive legs in one launch); the pure judges red on each wrong shape.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

from ._patchstack import msr

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                              # noqa: E402
from harness import battlewire as BW                                   # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
FS_LANDING = (68.0, -444.0)                         # coop_world_wait.FS_LANDING: in the 6603 cell (2, 13), OFF its trigger
KIT_AT = BW.KIT_6603_TRIGGER                        # ON the 6603 trigger (80, -444): where its cell function is requested

# ------------------------------------------------------------------------------------------------ the child
_CHILD = r'''
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
SENT = []

def root(ini):
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    (t / "Memoria.ini").write_text(ini, encoding="utf-8")
    return t

def fake_for(t, run, cw):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    if run.get("caps"):
        f.netsync_caps = FG.caps_through(run["caps"])
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(run.get("faults", ()))
    f.wf_follow_host_cfg = bool(run.get("follow_host", True))
    if run.get("kit", True):
        f.world_kit = dict(FG.FAKE_WORLD_KIT)           # the deployed kit's world-script content (today's, on s165 too)
    if run.get("order") == "e1":
        f.world_kit_order = FG.FAKE_WORLD_KIT_ORDER_E1_FIRST
    real_ns = f._netsync
    def ns(args, _real=real_ns):
        if args and str(args[0]).lower() in ("worldwalk", "worldfollow"):
            SENT.append(" ".join(str(a) for a in args))
        _real(args)
    f._netsync = ns
    return f

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:900]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def solo(run):
    for k in ("COOP_WW_LEG", "COOP_WW_LEVER", "COOP_CALIBRATE", "COOP_WW_KIT_AT", "COOP_WW_FERRY_AT"):
        os.environ.pop(k, None)
    if run.get("legs"):
        os.environ["COOP_WW_LEG"] = run["legs"]
    if run.get("kit_at"):
        os.environ["COOP_WW_KIT_AT"] = run["kit_at"]            # move the kit stand (its instrument still judges it)
    ww = load("coop_world_walk")
    cw, wf, cb = ww.cw, ww.wf, ww.cb
    # the bench's own waits, shortened for a stand-in that runs at 600 fps (every JUDGED threshold stays the bench's)
    for k, v in dict(KITOFF_S=1.0, FERRY_S=1.0, HAZARD_S=10.0, LEAVE_S=12.0, CONTROL_S=2.0).items():
        setattr(ww, k, v)
    for k, v in dict(HOME_S=10.0, LEAVE_S=12.0, START_S=4.0).items():
        setattr(wf, k, v)
    cw.read_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    ww.read_kit_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    t = root("[Netsync]\nEnabled = 0\nFollowHost = " + ("1" if run.get("follow_host", True) else "0") + "\n")
    f = fake_for(t, run, cw)
    cb.CALIBRATE = bool(run.get("cal"))
    ww.LEVER = run.get("lever", "kitcell")
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    # THE FREEZE LIFTED, by the engine's own lever (`bench worldfreeze off`: BenchWorldFreezeOff on the selftest role) -- right after
    # the leg's `control 0` (before the press) or right after its Confirm (inside the judged window)
    lift = run.get("lift")
    if lift == "before_press":
        real_control = ww._control
        def _control(g_, on, _real=real_control):
            st = _real(g_, on)
            if not on:
                g_.netsync("bench", "worldfreeze", "off")
                g_.wait_frames(6)
            return st
        ww._control = _control
    elif lift == "after_press":
        real_press = g.press
        def _press(button, *a, _real=real_press, **k):
            out = _real(button, *a, **k)
            if str(button).lower() == "confirm":
                g.netsync("bench", "worldfreeze", "off")
            return out
        g.press = _press
    with g:
        ww.run(g)
        out = rows_of(list(g.checks))
    out["sent"] = list(SENT)
    out["log"] = [ln for ln in (t / "Memoria.log").read_text(encoding="utf-8", errors="replace").splitlines()
                  if "kit-cell close" in ln or "worldwalk" in ln]
    return out

results = {name: (SENT.clear(), solo(run))[1] for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _child(payload, *, timeout: float = 600.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run(**run) -> dict:
    return _child({"runs": {"r": run}})["r"]


_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)
print(json.dumps({
    "all": list(ww.SOLO_ALL), "solo": list(ww.solo_catalog(False)), "cal": list(ww.solo_catalog(True, ("kitoff",), "kitcell")),
    "legs": {k: list(v) for k, v in ww.SOLO_LEGS_ROWS.items()}, "leg_row": ww.LEG_ROW, "old": list(ww.OLD_PREDICTED),
    "lever": {k: list(v) for k, v in ww.LEVER_PREDICTED.items()}, "faults": {k: list(v) for k, v in ww.SOLO_FAULT_REDS.items()},
    "order_faults": {k: list(v) for k, v in ww.ORDER_FAULT_REDS.items()},
    "consts": {"PROBE": ww.PROBE, "ROUTE_PROBE": ww.ROUTE_PROBE, "LEGS": list(ww.LEGS), "LEVERS": list(ww.LEVERS),
               "FARSHORE": ww.FARSHORE, "WORLD": ww.WORLD, "FS_LANDING": list(ww.FS_LANDING), "KIT_CELL": list(ww.KIT_CELL),
               "KIT_FIELD": ww.KIT_FIELD, "FERRY_AT": list(ww.FERRY_AT), "FERRY_STAND": list(ww.FERRY_STAND),
               "KIT_TRIGGER": list(ww.KIT_TRIGGER), "KIT_TRIGGER_R": ww.KIT_TRIGGER_R, "KIT_STAND": list(ww.KIT_STAND),
               "SOLO_LEGS": list(ww.SOLO_LEGS or ())},
    "doc": " ".join((ww.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


# ================================================================================================ the contract
CONTRACT_KITCELL = {"lever": None, "closed": 0, "last_sid": -1, "last_world": -1}
CONTRACT_OPS = ("kitcell", "clear")


def test_the_s166_contract_is_battlewires_to_the_key():
    """The key's catch-line sentinel (json text, order included) as netsync.world's LAST key after s165's `dot` (the prefix law); the
    verb's ops and words; the log prefixes and the proof line's regex; the census facts the stand-in and the bench share."""
    assert json.dumps(BW.WORLD_KITCELL_SENTINELS) == json.dumps(CONTRACT_KITCELL)
    assert list(BW.WORLD_SENTINELS_S166) == list(BW.WORLD_SENTINELS_S165) + ["kitcell"] and BW.WORLD_S166_KEYS == ("kitcell",)
    assert {k: v for k, v in BW.WORLD_SENTINELS_S166.items() if k != "kitcell"} == BW.WORLD_SENTINELS_S165
    assert BW.WORLDWALK_OPS == CONTRACT_OPS and BW.WORLDWALK_WORDS == {"kitcell": ("old", "act")}
    assert BW.WORLD_KITCELL_LEVER_WORDS == ("act", "old")
    assert BW.LOG_WORLD_KITCELL == "world kit-cell close: " and BW.PROOF_WORLD_WALK == "world walk selftest: "
    assert re.fullmatch(BW.WORLD_WALK_PROOF_RE, "world walk selftest: OK (84 rows, 13 mutants)")     # the engine's own tallies
    assert not re.fullmatch(BW.WORLD_WALK_PROOF_RE,
                            "world walk selftest: FAILED (row kit_cell.9011_sid0_closes failed (1 of 84))")   # the engine's word
    assert (FG.FAKE_WORLD_WALK_SELFTEST_ROWS, FG.FAKE_WORLD_WALK_MUTANTS) == (84, 13)      # the stand-in speaks the engine's tallies
    assert BW.worldwalk_ack("kitcell", "old") == "[NetSync] harness: worldwalk kitcell old"
    assert BW.LOG_WORLDWALK_RELEASED == "[NetSync] harness: worldwalk levers released (with the harness)"
    # the engine's whole ack lines (the stand-in's text) each open with the convention's prefix
    for ln, (op, word) in ((BW.LOG_WORLDWALK_KITCELL_OLD, ("kitcell", "old")), (BW.LOG_WORLDWALK_KITCELL_ACT, ("kitcell", "act")),
                           (BW.LOG_WORLDWALK_CLEAR, ("clear", None))):
        assert ln.startswith(BW.worldwalk_ack(op, word)), ln
    # the close's line, the engine's text exactly: "entry <sid> on world map <world> (<term>) -- ..."
    assert BW.log_world_kitcell(0, 9011) == ("world kit-cell close: entry 0 on world map 9011 (entry 0: the kit's entrance cells) -- a "
                                             "control-off read of a host-owned key masked (following guest): the host drives; the "
                                             "guest rejoins at their next stop")
    assert BW.log_world_kitcell(16, 9011).startswith(
        "world kit-cell close: entry 16 on world map 9011 (beyond the stock dispatcher's last entry 14: a kit object) -- ")
    # ...and a bench's reading of it: the exact prefix, then the engine's head naming THIS entry on THIS world map (anchored)
    assert BW.kitcell_line_names(BW.log_world_kitcell(0, 9011), 0, 9011)
    assert BW.kitcell_line_names("x | [NetSync] " + BW.log_world_kitcell(16, 9011), 16, 9011)
    assert not BW.kitcell_line_names(BW.log_world_kitcell(16, 9011), 1, 9011)          # 16 is not 1
    assert not BW.kitcell_line_names(BW.log_world_kitcell(16, 9011), 14, 9011)         # the stock last it names is not the entry
    assert not BW.kitcell_line_names(BW.log_world_kitcell(0, 9010), 0, 9011)
    assert not BW.kitcell_line_names("x | [NetSync] world kit-cell close: world map 9011, entry 16", 16, 9011)   # not the engine's head
    assert not BW.kitcell_line_names("world kit-cell close entry 0 9011", 0, 9011)      # the prefix is exact
    # the census: the walk worlds, the cell worlds (K1), the stock dispatchers' last entries, the cells, the objects
    assert BW.WALK_WORLDS == (9002, 9010, 9011)
    assert BW.KIT_CELL_WORLDS == (9000, 9002, 9003, 9005, 9007, 9008, 9009, 9010, 9011)
    assert set(BW.WALK_WORLDS) < set(BW.KIT_CELL_WORLDS) and FG.FAKE_WORLD_KIT["cell_worlds"] == BW.KIT_CELL_WORLDS
    # decision 19's reader scope as K1 widened it: every world map's stock dispatcher's last entry (the engine's StockLast)
    assert BW.STOCK_LAST_ENTRY == {9000: 11, 9001: 7, 9002: 14, 9003: 12, 9004: 3, 9005: 15, 9006: 6, 9007: 12, 9008: 12,
                                   9009: 13, 9010: 12, 9011: 14, 9012: 7, 9013: 14}
    assert BW.world_cell(*FS_LANDING) == (2, 13) and BW.KIT_CELLS[(2, 13)] == 6603 and len(BW.KIT_CELLS) == 6
    assert sorted(BW.KIT_CELLS.values()) == [6601, 6601, 6601, 6601, 6602, 6603]
    assert (BW.KIT_BOAT_SID, BW.KIT_BOAT_AT, BW.KIT_BOAT_RANGE) == (15, (492.0, -1130.0), 40.0)
    assert (BW.KIT_FERRY_SID, BW.KIT_FERRY_AT, BW.KIT_FERRY_RANGE) == (16, (29.0, -1168.0), 12.0)
    from ff9mapkit.world import entrance as WE                            # the kit's own cell math, one source
    assert WE.CELL_SIZE == BW.WORLD_CELL_U and WE.pack_cell_tag(2, 13, 1) == 0x8D09
    assert all(WE.unpack_cell_tag(WE.pack_cell_tag(cx, cz, 1))[:2] == (cx, cz) for cx, cz in BW.KIT_CELLS)
    # the in-box test is strict (the census's B_LT): the box edge is outside
    assert BW.in_kit_box(BW.KIT_FERRY_AT, 12.0, 29.0 + 11.99, -1168.0) and not BW.in_kit_box(BW.KIT_FERRY_AT, 12.0, 41.0, -1168.0)


def test_the_kit_triggers_are_the_deployed_event_tiles_not_the_cells():
    """THE STAND POINT (the 2026-11-02 OLD run: a press at FS_LANDING measured nothing). The engine requests a cell's function only
    while the walker stands on an EVENT-ID triangle, so each kit cell's trigger is its census patch (the deployed terrain's event tiles),
    never the 32-u cell: every cell has one, each triangle's centroid inside its cell; the 6603 patch is the ledger's `--trigger-at 80
    -444 --trigger-radius 3.0 --no-tile-area` -- exactly the triangles whose centroid lies within 3 u -- and FS_LANDING, in the cell, is
    OFF it; the trigger's centre is on it, so is the 2*sqrt(2) disc round it, while a point 2.97 u out on the SW diagonal is not (the
    stand judge needs the tiles, not the radius alone); the ferry stand is on no trigger."""
    assert set(BW.KIT_TRIGGER_TILES) == set(BW.KIT_CELLS) and FG.FAKE_WORLD_KIT["triggers"] == BW.KIT_TRIGGER_TILES
    for cell, tris in BW.KIT_TRIGGER_TILES.items():
        assert 6 <= len(tris) <= 7, cell
        for t in tris:
            cx, cz = sum(p[0] for p in t) / 3.0, sum(p[1] for p in t) / 3.0
            assert BW.world_cell(cx, cz) == cell, (cell, t)
    assert BW.KIT_6603_TRIGGER == (80.0, -444.0) and BW.KIT_6603_TRIGGER_R == 3.0
    tx, tz = BW.KIT_6603_TRIGGER
    for t in BW.KIT_TRIGGER_TILES[(2, 13)]:
        cx, cz = sum(p[0] for p in t) / 3.0, sum(p[1] for p in t) / 3.0
        assert ((cx - tx) ** 2 + (cz - tz) ** 2) ** 0.5 <= BW.KIT_6603_TRIGGER_R, t
    assert BW.kit_cell_field(9011, *FS_LANDING) == 6603 and BW.kit_trigger_field(9011, *FS_LANDING) is None
    assert BW.kit_trigger_field(9011, *BW.KIT_6603_TRIGGER) == 6603 and BW.kit_trigger_field(9010, *BW.KIT_6603_TRIGGER) == 6603
    assert BW.kit_trigger_field(9001, *BW.KIT_6603_TRIGGER) is None           # no kit cells on that world's dispatcher
    import math
    r = 2.0 * math.sqrt(2.0) - 0.01
    assert all(BW.kit_trigger_field(9011, tx + r * math.cos(a * math.pi / 8), tz + r * math.sin(a * math.pi / 8)) == 6603
               for a in range(16))
    assert BW.kit_trigger_field(9011, tx - 2.1, tz - 2.1) is None              # 2.97 u from the trigger, off its tiles
    assert BW.kit_trigger_field(9011, tx - 4.0, tz + 4.0) == 6603              # a patch corner, 5.66 u out: on them
    assert BW.kit_trigger_field(9011, tx + 4.0, tz - 4.0) is None              # ...but z -448 is cell (2, 14): another tag
    ferry = (BW.KIT_FERRY_AT[0] - 3.0, BW.KIT_FERRY_AT[1] + 8.0)
    assert BW.kit_trigger_field(9011, *ferry) is None and BW.kit_trigger_field(9011, 48.0, -1168.0) == 6601
    # the freeze keys the stand judges and the instruments read (s144's block; on the solo bench its term is "bench")
    assert BW.WORLD_FREEZE_ON_KEY == "netsync.world.freeze.on" and BW.WORLD_FREEZE_WHY_KEY == "netsync.world.freeze.why"
    assert BW.WORLD_FREEZE_WHY_SOLO == "bench" and BW.WORLD_FREEZE_WHY_SOLO in BW.WORLD_FREEZE_WHYS


def test_the_s166_rung_is_the_ladders_last():
    """`worldwalk` is the ladder's newest rung (patch s166, one sub-verb), its calibration caps_through("worldfollow"); the sub-verb is
    the driver's and the stand-in's LAST; the keys tables carry `kitcell` inside `netsync.world`."""
    rungs = list(FG.NETSYNC_BATTLE_CAPS)
    assert rungs[-1] == "worldwalk" and rungs[-2] == "worldfollow" and FG.NETSYNC_BATTLE_CAPS["worldwalk"] == ("s166", ("worldwalk",))
    assert FG.NETSYNC_S166_CAPS == frozenset(("worldwalk",)) and "worldwalk" not in FG.caps_through("worldfollow")
    assert FG.NETSYNC_SUBVERBS[-1] == Session.NETSYNC_SUBVERBS[-1] == Session.NETSYNC_AUTHORITY_SUBVERBS[-1] == "worldwalk"
    assert FG.NETSYNC_SUBVERBS[-2] == Session.NETSYNC_SUBVERBS[-2] == "worldfollow"
    assert "worldwalk" not in FG.netsync_subverbs(FG.caps_through("worldfollow"))
    assert Session.NETSYNC_WORLDWALK_SUBVERBS["worldwalk"][:3] == ("coop_world_walk", "netsync.world.kitcell", "s166")
    assert "worldwalk" not in FG.NETSYNC_TOP_CAP_KEYS                     # no top-level netsync key in A0
    assert FG.NETSYNC_TOP_NESTED_KEYS["worldwalk"] == {"world": ("kitcell",)} and FG.NETSYNC_BATTLE_CAP_KEYS["worldwalk"] == {}
    assert FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldwalk"] == tuple(BW.WORLD_SENTINELS_S166)
    assert FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldfollow"] == tuple(BW.WORLD_SENTINELS_S165)     # s165's row unmoved


# ------------------------------------------------------------------------------------------------ the stand-in, direct
def _game(root):
    (root / "x64").mkdir(parents=True, exist_ok=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (root / "FF9CustomMap").mkdir(exist_ok=True)
    (root / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    return root


def _fake(root, *, caps=None, faults=(), kit=True, order=None) -> FakeGame:
    f = FakeGame(root, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    if caps is not None:
        f.netsync_caps = FG.caps_through(caps)
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(faults)
    f.wf_follow_host_cfg = True
    if kit:
        f.world_kit = dict(FG.FAKE_WORLD_KIT)
    if order is not None:
        f.world_kit_order = order
    return f


def _session(root, fake) -> Session:
    g = Session(game_path=root, run_dir=root / "run", save_dir=root / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g


def _log(fake) -> str:
    return (fake.game_path / "Memoria.log").read_text(encoding="utf-8", errors="replace")


def _on_world(g, fake, x, z, *, bench=True, world=9011):
    """The selftest role (`bench 1`: a frozen spectator) on ``world`` (9011) at (x, z): the stand-in's own world entry, then its pose."""
    g.newgame(settle=0)
    g.warp(6603)
    g.netsync("selftest", 1)
    if bench:
        g.netsync("bench", 1)
    fake.enter_world(world, x, z)
    g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=5, what="the world map")
    g.wait_frames(10)


def _press(g, fake, *, control: bool, menu: bool = False, frames: float = 0.25):
    """Control set (or the ~ menu's hold), one Confirm, the samples after it: (states, the kitcell block at the end)."""
    import time as _t
    if menu:
        fake.debug_menu_hold(True)
    else:
        g.control(control)
    g.wait_frames(4)
    g.press("confirm", 4)
    states, t0 = [], _t.time()
    while _t.time() - t0 < frames:
        states.append(g.state)
        _t.sleep(0.01)
    g.wait_frames(60)
    states.append(g.state)
    if menu:
        fake.debug_menu_hold(False)
    return states, g.state.world_kitcell_block


def _left(states) -> bool:
    return any(s.ui_state == "FieldHUD" or (s.raw.get("world") or {}).get("next_mode") == 1 for s in states)


@pytest.mark.parametrize("order", [FG.FAKE_WORLD_KIT_ORDER, FG.FAKE_WORLD_KIT_ORDER_E1_FIRST], ids=["e0_first", "e1_first"])
def test_the_kit_cell_read_is_closed_control_off_under_both_orders_and_today_it_enters(tmp_path, order):
    """The kit cell (entry 0) ON its trigger, control OFF, Confirm: s165 (caps_through worldfollow) -- the guest enters 6603 ALONE, the
    hazard; s166 -- WorldHUD kept, `closed` +2 (entry 0 and the boat's eager read, entry 15: BW.KIT_EAGER_READERS; 9011), entry
    0's line once. A close keyed on the pass's FIRST read leaks the kit cell itself exactly under entry 1 first (its stock read
    consumes the tick): THE ORDER LAW -- every kit-cell row runs both orders; under entry 0 first it still leaks the boat's read."""
    for caps, fault, want_left in ((None, (), False), ("worldfollow", (), True), (None, ("kitcell_first_read",), None)):
        root = _game(tmp_path / f"{caps}-{fault}-{order[0]}")
        fake = _fake(root, caps=caps, faults=fault, order=order)
        with _session(root, fake) as g:
            _on_world(g, fake, *KIT_AT)
            k0 = g.state.world_kitcell_block
            states, k1 = _press(g, fake, control=False)
            left = _left(states)
            if want_left is None:                               # the order-dependent fault
                want_left = order[0] == "e1"
            assert left is want_left, (caps, fault, order, [(s.ui_state, s.field_id) for s in states[-3:]])
            if caps is None and not fault and not left:
                assert k1["closed"] - k0["closed"] == 2 and k1["last_sid"] in (0, BW.KIT_BOAT_SID) and k1["last_world"] == 9011
                assert _log(fake).count(BW.LOG_WORLD_KITCELL) == 2                # entry 0's line and the boat's, once each
            if fault and not left:                              # the first-read dedupe: the boat's eager read leaked
                assert k1["closed"] - k0["closed"] == 1 and k1["last_sid"] == 0
            if caps is not None:
                assert k1 is None and BW.LOG_WORLD_KITCELL not in _log(fake)
            if left:
                g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=5, what="the kit cell's field")
                assert g.state.field_id == 6603


def test_off_the_trigger_nothing_is_requested_and_the_bench_freeze_needs_no_host(tmp_path):
    """THE 2026-11-02 OLD RUN, reproduced offline. On s165 a control-off Confirm at FS_LANDING -- in the 6603 cell, 12 u off its trigger
    -- reaches nothing (every sample WorldHUD 9011: the run's own 121 samples), while the same press ON the trigger enters 6603 alone;
    on s166 the off-trigger press closes only the boat's eager read (entry 15): nothing requested entry 0's function. And the solo
    bench's freeze is `bench 1` on the
    selftest role (why 'bench', SpectatorField's third term): it holds with no bench host for longer than a client's 2 s stale span
    (the run: freeze.on true through both presses, the lift only at `reset`), and lifts by the engine's own `bench worldfreeze off`."""
    import time as _t
    for caps, at, want_left in (("worldfollow", FS_LANDING, False), ("worldfollow", KIT_AT, True), (None, FS_LANDING, False)):
        root = _game(tmp_path / f"{caps}-{at[0]:g}")
        fake = _fake(root, caps=caps)
        with _session(root, fake) as g:
            _on_world(g, fake, *at)
            k0 = g.state.world_kitcell_block
            states, k1 = _press(g, fake, control=False)
            assert _left(states) is want_left, (caps, at, [(s.ui_state, s.field_id) for s in states[-3:]])
            if not want_left:
                assert all(s.ui_state == "WorldHUD" and s.world_id == 9011 for s in states), (caps, at)
            if caps is None:
                lines = _log(fake).splitlines()
                assert k1["closed"] - k0["closed"] == 1 and k1["last_sid"] == BW.KIT_BOAT_SID, k1
                assert not any(BW.kitcell_line_names(ln, 0, 9011) for ln in lines), lines[-5:]
    root = _game(tmp_path / "freeze")
    fake = _fake(root)
    with _session(root, fake) as g:
        _on_world(g, fake, *KIT_AT)
        fz = lambda: g.state.netsync["world"]["freeze"]                       # noqa: E731
        assert (fz()["on"], fz()["why"]) == (True, BW.WORLD_FREEZE_WHY_SOLO)
        assert not (g.state.netsync["world"]["host"] or {}).get("valid")        # no bench host on at all
        _t.sleep(2.2)
        g.wait_frames(10)
        assert (fz()["on"], fz()["why"]) == (True, BW.WORLD_FREEZE_WHY_SOLO)
        g.netsync("bench", "worldfreeze", "off")
        g.wait_frames(6)
        assert fz()["on"] is False
        g.netsync("bench", "worldfreeze", "on")
        g.wait_frames(6)
        assert fz()["on"] is True


def test_the_kit_cells_close_on_a_disc_1_world_and_the_line_re_arms_per_world_load(tmp_path):
    """K1's widening, as the engine ships it: entry 0's six cells sit in EVERY free-roam dispatcher the install overrides, not only the
    walk set -- so on disc 1's 9000 (cell (2, 13)'s trigger is the 6603 entrance there too) s165 takes a control-off Confirm into
    6603 ALONE, and s166 closes it (last_world 9000). The witness and the line follow NetSyncField: a second press inside the same
    world load counts again (`closed` +2) but speaks once; a new world load (s145's warm return is one) re-arms the line -- once more
    for the same entry; the line is the engine's text exactly."""
    assert BW.kit_cell_field(9000, *FS_LANDING) == 6603 and BW.kit_cell_field(9001, *FS_LANDING) is None
    assert BW.kit_cell_field(9013, *FS_LANDING) is None                  # Path D's cells are its own (not modelled)
    root = _game(tmp_path / "s165")
    fake = _fake(root, caps="worldfollow")
    with _session(root, fake) as g:
        _on_world(g, fake, *KIT_AT, world=9000)
        states, _k = _press(g, fake, control=False)
        assert _left(states), [(s.ui_state, s.world_id) for s in states[-3:]]
        g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=5, what="the kit cell's field")
        assert g.state.field_id == 6603
    root = _game(tmp_path / "s166")
    fake = _fake(root)
    with _session(root, fake) as g:
        _on_world(g, fake, *KIT_AT, world=9000)
        k0 = g.state.world_kitcell_block
        line = "[NetSync] " + BW.log_world_kitcell(0, 9000)
        for n, reload_first, lines in ((1, False, 1), (2, False, 1), (3, True, 2)):
            if reload_first:
                fake.enter_world(9000, *KIT_AT)                          # a world load: the line's latch re-arms
                g.wait_frames(10)
            states, k1 = _press(g, fake, control=False)
            assert not _left(states) and all(s.ui_state == "WorldHUD" and s.world_id == 9000 for s in states), n
            assert k1["closed"] - k0["closed"] == n and (k1["last_sid"], k1["last_world"]) == (0, 9000), (n, k1)
            assert _log(fake).count(line) == lines and _log(fake).count(BW.LOG_WORLD_KITCELL) == lines, n


@pytest.mark.parametrize("order", [FG.FAKE_WORLD_KIT_ORDER, FG.FAKE_WORLD_KIT_ORDER_E1_FIRST], ids=["e0_first", "e1_first"])
def test_the_boat_rows_run_under_both_orders_and_a_sid0_only_close_leaks_one(tmp_path, order):
    """The boat (entry 15) at BOAT_SPAWN, control OFF, Confirm: its board needs Map[24] 169 AT its read, which the entry order decides
    (e0's reset after e1's request: no board). s165 boards under e0 first only -- so under e1 first a boat row is VACUOUS, and a
    sid-0-only close (the design's mutant) passes it there: the boat row must run both orders. s166 never boards, under either."""
    boards = {}
    for caps, fault in ((None, ()), ("worldfollow", ()), (None, ("kitcell_sid0_only",))):
        root = _game(tmp_path / f"{caps}-{fault}-{order[0]}")
        fake = _fake(root, caps=caps, faults=fault, order=order)
        with _session(root, fake) as g:
            _on_world(g, fake, *BW.KIT_BOAT_AT)
            k0 = g.state.world_kitcell_block
            _states, k1 = _press(g, fake, control=False)
            boards[(caps, fault)] = g.state.vehicle == BW.KIT_BOARD_MODE
            if caps is None and not fault:
                assert k1["closed"] - k0["closed"] == 1 and k1["last_sid"] == BW.KIT_BOAT_SID
    e0_first = order[0] == "e0"
    assert boards == {(None, ()): False, ("worldfollow", ()): e0_first, (None, ("kitcell_sid0_only",)): e0_first}, boards


def test_the_ferryman_scene_plays_today_and_is_closed_with_a_sid0_only_close_red(tmp_path):
    """The ferryman (entry 16) within his +-12 u box, control OFF, Confirm: s165 plays his scene on the guest's copy (Map[50] 1, no
    Field()); s166 keeps Map[50] 0 and counts sid 16; a sid-0-only close plays it again (the design's mutant must fail this row)."""
    stand = (BW.KIT_FERRY_AT[0] - 3.0, BW.KIT_FERRY_AT[1] + 8.0)
    assert BW.kit_cell_field(9011, *stand) is None and BW.kit_cell_field(9011, BW.KIT_FERRY_AT[0] + 4.0, BW.KIT_FERRY_AT[1]) == 6601
    played = {}
    for caps, fault in ((None, ()), ("worldfollow", ()), (None, ("kitcell_sid0_only",))):
        root = _game(tmp_path / f"{caps}-{fault}")
        fake = _fake(root, caps=caps, faults=fault)
        with _session(root, fake) as g:
            _on_world(g, fake, *stand)
            states, k1 = _press(g, fake, control=False, frames=0.4)
            played[(caps, fault)] = any(int((s.raw.get("world") or {}).get("mapvar", "0" * 160)[100:102], 16) for s in states)
            assert all(s.ui_state == "WorldHUD" for s in states)            # no Field(): a local scene
            if caps is None and not fault:
                assert k1["last_sid"] in (BW.KIT_FERRY_SID, BW.KIT_BOAT_SID) and k1["closed"] == 2   # 16 and the boat's eager 15
    assert played == {(None, ()): False, ("worldfollow", ()): True, (None, ("kitcell_sid0_only",)): True}, played


def test_the_debug_menu_hold_is_control_off_and_a_harness_keyed_close_leaks_there(tmp_path):
    """The ~ menu open with "Disable control" (Ff9mkDebugMenu.ApplyControlHold: SetUserControl(false)) -- which no harness verb opens in
    game -- is control off: today the kit cell enters 6603 under it; s166 closes it; a close keyed on the harness's control op (the
    `kitcell_menu_leak` fault) leaks exactly there. The hold restores the prior control once at its close."""
    for caps, fault, want_left in ((None, (), False), ("worldfollow", (), True), (None, ("kitcell_menu_leak",), True)):
        root = _game(tmp_path / f"{caps}-{fault}")
        fake = _fake(root, caps=caps, faults=fault)
        with _session(root, fake) as g:
            _on_world(g, fake, *KIT_AT)
            assert g.state.control is True
            states, _k = _press(g, fake, control=False, menu=True)
            assert _left(states) is want_left, (caps, fault)
            if not want_left:
                g.wait_frames(5)
                assert g.state.control is True                         # the hold's close restored it, once
    # the hold alone, no press: control off while held, the prior value back after
    root = _game(tmp_path / "hold")
    fake = _fake(root)
    fake.control = True
    fake.debug_menu_hold(True)
    fake.debug_menu_hold(True)
    assert fake.control is False
    fake.debug_menu_hold(False)
    fake.debug_menu_hold(False)
    assert fake.control is True


def test_control_on_a_host_and_a_stock_read_are_untouched(tmp_path):
    """No lawful behaviour changes: a control-ON press on the kit cell keeps s144's mask (no entry, `closed` +0, the freeze's `keys`
    counted for each reader: entry 0, entry 1's poll and the boat's eager read); a HOST's press enters 6603 (stock: the close never
    reads a host); entry 1's stock control-off read is never closed (one press on the cell: `closed` +2 -- entry 0 and the boat's
    eager 15 -- never +3: the `kitcell_stock` fault's +3 shows it can fail)."""
    root = _game(tmp_path / "on")
    fake = _fake(root)
    with _session(root, fake) as g:
        _on_world(g, fake, *KIT_AT)
        k0, f0 = g.state.world_kitcell_block, g.state.netsync["world"]["freeze"]["keys"]
        states, k1 = _press(g, fake, control=True)
        assert not _left(states) and k1["closed"] == k0["closed"]
        assert g.state.netsync["world"]["freeze"]["keys"] - f0 == 3       # e0's read, e1's poll, e15's eager read: each masked
    root = _game(tmp_path / "host")
    fake = _fake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        fake.netsync.update(enabled=True, role="host", instance=True)
        fake.enter_world(9011, *KIT_AT)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=5, what="the world map")
        states, k1 = _press(g, fake, control=True)
        assert _left(states) and k1["closed"] == 0
    for faults, closed, last in (((), 2, (0, BW.KIT_BOAT_SID)), (("kitcell_stock",), 3, (0, 1, BW.KIT_BOAT_SID))):
        root = _game(tmp_path / f"stock-{faults}")
        fake = _fake(root, faults=faults)
        with _session(root, fake) as g:
            _on_world(g, fake, *KIT_AT)
            _states, k1 = _press(g, fake, control=False)
            assert k1["closed"] == closed and k1["last_sid"] in last, (faults, k1)


def test_the_s165_stand_in_publishes_no_kitcell_and_fails_the_verb_closed(tmp_path):
    """OLD: an s165 engine publishes no `netsync.world.kitcell` (its `world` ends at `dot`), no proof line, and answers `netsync
    worldwalk` with its unknown-sub-verb line -- the driver refuses before the step."""
    root = _game(tmp_path)
    fake = _fake(root, caps="worldfollow")
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        g.netsync("selftest", 1)
        st = g.state
        assert list(st.netsync["world"]) == list(BW.WORLD_SENTINELS_S165) and st.coop_world_walk is False
        assert st.world_kitcell_block is None and st.world_kitcell_closed is None
        assert BW.PROOF_WORLD_WALK not in _log(fake)
        with pytest.raises(HarnessError, match=r"publishes no `netsync\.world\.kitcell`"):
            g.worldwalk("kitcell", "old")
    with pytest.raises(RuntimeError, match="unknown sub-verb 'worldwalk'"):
        fake._netsync(["worldwalk", "clear"])


def test_the_stand_in_publishes_kitcell_last_and_worldwalk_refuses_in_the_contracts_order(tmp_path):
    """The default stand-in (s166): `netsync.world` = s165's eight then `kitcell` at its shape, the proof line after the world dot's;
    the verb: a malformed form refused BEFORE the step (the usage line, nothing changes); co-op off refuses every op but `clear` (from
    the step); any role -- a host pulls it too; the release puts it back, one line only when it was set."""
    root = _game(tmp_path)
    fake = _fake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        st = g.state
        assert list(st.netsync["world"]) == list(BW.WORLD_SENTINELS_S166) and st.coop_world_walk is True
        assert st.world_kitcell_block == dict(CONTRACT_KITCELL, lever="act")
        seq = g.state.seq
        for bad in (("bogus",), ("kitcell",), ("kitcell", "maybe"), ("kitcell", "old", "1"), ("clear", "1"), ()):
            with pytest.raises(HarnessError, match=re.escape(BW.WORLDWALK_USAGE)):
                g.worldwalk(*bad) if bad else g.netsync("worldwalk")
        assert g.state.seq == seq and not any(s[:2] == ["netsync", "worldwalk"] for s in fake.executed)
        with pytest.raises(HarnessError, match=re.escape(BW.WORLDWALK_OFF_REFUSAL)):
            g.worldwalk("kitcell", "old")                               # co-op off (no role yet): refused by the engine
        g.worldwalk("clear")                                            # ...but `clear` passes on any role, co-op off included
        fake.netsync.update(enabled=True, role="host", instance=True)
        g.worldwalk("kitcell", "old")                                   # any role: a host's lever
        assert g.state.world_kitcell_block["lever"] == "old"
        fake.netsync.update(enabled=False, role="selftest")
        g.netsync("selftest", 1)
        before = _log(fake).count(BW.LOG_WORLDWALK_RELEASED)
        g.netsync("selftest", 0)                                        # the harness release, every role
        g.wait_frames(4)
        assert g.state.world_kitcell_block["lever"] == "act" and _log(fake).count(BW.LOG_WORLDWALK_RELEASED) == before + 1
        g.netsync("selftest", 0)                                        # nothing set: no second line
        assert _log(fake).count(BW.LOG_WORLDWALK_RELEASED) == before + 1
        assert re.search(BW.WORLD_WALK_PROOF_RE, _log(fake))


# ------------------------------------------------------------------------------------------------ the twin and its mutants
CLOSE_ROWS = [
    # (gmode, frozen, control, world, sid, old) -> closes
    ((3, True, False, 9011, 0, False), True),          # K-CELL-OFF: a kit cell, control off, frozen
    ((3, True, False, 9011, 15, False), True),         # K-BOAT-OFF
    ((3, True, False, 9011, 16, False), True),         # K-FERRY-OFF
    ((3, True, False, 9002, 0, False), True),          # the cells on 9002 and 9010 too
    ((3, True, False, 9010, 0, False), True),
    ((3, True, False, 9010, 13, False), True),         # past WORLD10's stock last (e12)
    ((3, True, False, 9011, 1, False), False),         # K-STOCK: entry 1's stock read passes
    ((3, True, False, 9011, 14, False), False),        # WORLD11's stock last entry passes
    ((3, True, False, 9010, 12, False), False),        # WORLD10's stock last entry passes
    ((3, True, False, 9002, 13, False), False),        # WORLD02's (empty) stock slot below its last: not the kit's
    ((3, True, True, 9011, 0, False), False),          # K-CELL-ON: control on is s144's mask, never the close
    ((3, False, False, 9011, 0, False), False),        # K-UNFROZEN: a host, vanilla, a released guest
    ((1, True, False, 9011, 0, False), False),         # K-FIELD: gMode 1 (a field's entry 0)
    ((3, True, False, 9011, 0, True), False),          # K-OLD: `kitcell old` = s165
    ((3, True, False, 9011, 16, True), False),
    # K1's widening (the engine's StockLast): entry 0 on every world map; 9005's stock runs to e15; an unknown world: entry 0 alone
    ((3, True, False, 9000, 0, False), True),          # WORLD00's cells (overridden too)
    ((3, True, False, 9000, 12, False), True),         # past WORLD00's stock last (e11)
    ((3, True, False, 9005, 15, False), False),        # sid 15 is a STOCK entry on 9005 (the highest stock last)
    ((3, True, False, 9005, 16, False), True),
    ((3, True, False, 9013, 15, False), True),         # Path D's WORLD13 reads as its donor WORLD11
    ((3, True, False, 9999, 0, False), True),          # a world the census never read: entry 0 alone...
    ((3, True, False, 9999, 15, False), False),        # ...never term (b)
    ((3, True, False, 9011, -1, False), False),        # no reader (no executing object) is never a kit reader
]


@pytest.mark.parametrize("args,want", CLOSE_ROWS)
def test_the_close_twin_reads_decision_19(args, want):
    assert BW.kit_cell_close_rule(*args) is want


def _last(w, default=-1):
    return BW.STOCK_LAST_ENTRY.get(w, default)


CLOSE_MUTANTS = {
    "sid0_only": lambda gm, fr, ctl, w, sid, old=False: not old and gm == 3 and fr and not ctl and sid == 0,
    "ignores_control": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and fr
                                                                and (sid == 0 or (_last(w) >= 0 and sid > _last(w)))),
    "ignores_freeze": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and not ctl
                                                               and (sid == 0 or (_last(w) >= 0 and sid > _last(w)))),
    "stock_too": lambda gm, fr, ctl, w, sid, old=False: not old and gm == 3 and fr and not ctl and sid >= 0,
    "walk_worlds_only": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and fr and not ctl and w in BW.WALK_WORLDS
                                                                 and (sid == 0 or sid > _last(w))),
    "unknown_world_kit": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and fr and not ctl
                                                                  and (sid == 0 or sid > _last(w, 14))),
    "last_14_everywhere": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and fr and not ctl and (sid == 0 or sid > 14)),
    "no_reader_closed": lambda gm, fr, ctl, w, sid, old=False: (not old and gm == 3 and fr and not ctl
                                                                 and (sid <= 0 or (_last(w) >= 0 and sid > _last(w)))),
    "ignores_lever": lambda gm, fr, ctl, w, sid, old=False: (gm == 3 and fr and not ctl
                                                              and (sid == 0 or (_last(w) >= 0 and sid > _last(w)))),
    "any_gmode": lambda gm, fr, ctl, w, sid, old=False: (not old and fr and not ctl
                                                          and (sid == 0 or (_last(w) >= 0 and sid > _last(w)))),
}


@pytest.mark.parametrize("name", sorted(CLOSE_MUTANTS))
def test_each_close_mutant_fails_a_row(name):
    """Every one-line drift of the close fails at least one row of the table (a check that cannot fail is not a check)."""
    mut = CLOSE_MUTANTS[name]
    assert any(bool(mut(*args)) is not want for args, want in CLOSE_ROWS), name


# ================================================================================================ the bench: tables
def test_the_tables_are_the_docstring_and_each_others(tables):
    """Every row the docstring names; each prediction and fault row a real row; the faults table names exactly the stand-in's levers;
    the route is coop_world_follow's; the landing is in the 6603 cell but OFF its trigger, the kit stand ON it (the battlewire census);
    the ferry stand sits in the ferryman's box, off every kit cell."""
    doc = tables["doc"]
    for cid in tables["all"]:
        assert cid.replace("S166-", "") in doc, cid
    assert set(tables["old"]) <= set(tables["all"]) and not set(tables["old"]) & {"S166-INI", "S166-OR", "S166-S0", "S166-R"}
    assert set(tables["lever"]) == set(tables["consts"]["LEVERS"])
    assert set(tables["lever"]["kitcell"]) == set(tables["leg_row"].values()) and set(tables["lever"]["kitcell"]) < set(tables["old"])
    assert set(tables["faults"]) == set(FG.WORLD_WALK_FAULTS)
    assert all(set(v) <= set(tables["all"]) for v in tables["faults"].values())
    assert set(tables["order_faults"]) <= set(FG.WORLD_WALK_FAULTS)
    assert tables["solo"][-1] == "S166-R" and tables["cal"][-1] == "S166-CAL" and "S166-A-FERRYOFF" not in tables["cal"]
    c = tables["consts"]
    assert c["PROBE"] == "netsync.world.kitcell" and c["ROUTE_PROBE"] == "netsync.world.out" and c["LEGS"] == ["kitoff", "ferryoff"]
    assert (c["FARSHORE"], c["WORLD"], c["FS_LANDING"]) == (6603, 9011, [68.0, -444.0])
    assert c["KIT_CELL"] == [2, 13] and c["KIT_FIELD"] == 6603 and c["SOLO_LEGS"] == ["kitoff", "ferryoff"]
    assert c["KIT_TRIGGER"] == [80.0, -444.0] == c["KIT_STAND"] and c["KIT_TRIGGER_R"] == BW.KIT_6603_TRIGGER_R
    assert BW.kit_trigger_field(9011, *c["KIT_STAND"]) == 6603 and BW.kit_trigger_field(9011, *c["FS_LANDING"]) is None
    fx, fz = c["FERRY_STAND"]
    assert BW.in_kit_box(BW.KIT_FERRY_AT, BW.KIT_FERRY_RANGE, fx, fz) and BW.kit_cell_field(9011, fx, fz) is None


# ================================================================================================ the bench: the stand-in runs
@pytest.mark.parametrize("order", ["e0", "e1"])
def test_the_solo_leg_is_green_on_the_s166_stand_in_under_both_orders(tables, order):
    r = _run(order=order)
    assert r["all"] == tables["solo"], r["all"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    # the levers went out (the R row's pull and its release), the route's bench host too
    assert any(s.startswith("worldfollow host ") for s in r["sent"]) and "worldwalk kitcell old" in r["sent"]
    assert sum(1 for ln in r["log"] if BW.LOG_WORLD_KITCELL in ln) == 3          # entry 0, the boat's eager 15, entry 16: once each


@pytest.mark.parametrize("leg", ["kitoff", "ferryoff"])
def test_the_solo_leg_calibrates_on_s165_measures_the_hazard_and_sends_nothing_new(tables, leg):
    """OLD: the s165 stand-in publishes no `netsync.world.kitcell` -- exactly OLD_PREDICTED red (the selected leg's row among them),
    S166-CAL green because the leg MEASURED today's hazard (6603 entered alone / the ferryman's scene), and the bench SENT no
    `worldwalk` op (s165 fails the sub-verb closed)."""
    r = _run(caps="worldfollow", cal=True, legs=leg)
    row = tables["leg_row"][leg]
    want = sorted(c for c in tables["old"] if c in r["all"])
    assert row in want and sorted(set(r["red"]) - {"S166-CAL"}) == want, r["red"]
    assert "S166-CAL" not in r["red"], r["detail"]["S166-CAL"]
    assert not any(s.startswith("worldwalk") for s in r["sent"]), r["sent"]
    assert ("FieldHUD 6603" if leg == "kitoff" else "Map[50] read [1") in r["detail"][row], r["detail"][row]


@pytest.mark.parametrize("leg", ["kitoff", "ferryoff"])
def test_the_lever_calibrates_exactly_and_measures_the_hazard(tables, leg):
    """LEVER: s166 under `worldwalk kitcell old` (pulled at P1, held) -- exactly LEVER_PREDICTED red, the hazard measured (s165's
    behaviour back), S166-CAL green; a lever the engine ignores (`kitcell_lever_ignored`) reds the calibration itself."""
    runs = _child({"runs": {"lever": {"cal": True, "legs": leg}, "ignored": {"cal": True, "legs": leg,
                                                                              "faults": ["kitcell_lever_ignored"]}}})
    r = runs["lever"]
    row = tables["leg_row"][leg]
    assert set(r["red"]) - {"S166-CAL"} == {row}, {c: r["detail"][c] for c in r["red"]}
    assert "S166-CAL" not in r["red"], r["detail"]["S166-CAL"]
    assert "worldwalk kitcell old" in r["sent"]
    bad = runs["ignored"]
    assert "S166-CAL" in bad["red"] and row in bad["detail"]["S166-CAL"], bad["detail"].get("S166-CAL")


def test_a_calibration_without_a_measured_hazard_is_red():
    """OLD with no kit content on the install (nothing reads the press): the leg row is red as predicted, but its hazard was never
    measured -- the calibration reds instead of reading the prediction as met."""
    r = _run(caps="worldfollow", cal=True, legs="kitoff", kit=False)
    assert "S166-A-KITOFF" in r["red"] and "S166-CAL" in r["red"], r["red"]
    assert "NOT measured" in r["detail"]["S166-CAL"] and "S166-A-KITOFF" in r["detail"]["S166-CAL"].split("NOT measured")[1]


def test_a_calibration_names_one_leg_and_launches_nothing():
    """EACH DESTRUCTIVE LEG NEEDS ITS OWN LAUNCH: COOP_CALIBRATE=1 with both legs selected refuses at once -- S166-CAL red with the
    reason, no setup, nothing sent."""
    r = _run(cal=True)
    assert "S166-CAL" in r["red"] and "OWN LAUNCH" in r["detail"]["S166-CAL"] and r["sent"] == []
    assert all(r["detail"][c].startswith("not reached") for c in r["red"] if c != "S166-CAL")


def test_the_ini_refuses_a_bench_without_followhost():
    """S166-INI is a precondition that CAN fail: FollowHost 0 (the fabricated host's gate) stops the leg before anything is sent."""
    r = _run(follow_host=False)
    assert "S166-INI" in r["red"] and "FollowHost" in r["detail"]["S166-INI"] and r["sent"] == []


def test_an_s165_engine_without_the_calibration_runs_no_leg():
    """Nothing new to judge on s165 without COOP_CALIBRATE: the legs are not run (never a destructive leg by accident), no
    `worldwalk` op is sent."""
    r = _run(caps="worldfollow")
    assert {"S166-P0", "S166-P1", "S166-A-KITOFF", "S166-A-FERRYOFF"} <= set(r["red"])
    assert r["detail"]["S166-A-KITOFF"].startswith("not reached") and not any(s.startswith("worldwalk") for s in r["sent"])
    assert not any(s.startswith("worldfollow host") for s in r["sent"])


@pytest.mark.parametrize("fault", FG.WORLD_WALK_FAULTS)
@pytest.mark.parametrize("order", ["e0", "e1"])
def test_each_world_walk_fault_turns_exactly_its_solo_rows_red(tables, fault, order):
    """Each fault lever turns EXACTLY its rows red: SOLO_FAULT_REDS under entry 0 first, ORDER_FAULT_REDS (else the same) under entry
    1 first. `kitcell_first_read` reds both legs under both orders (the boat's eager read is never a pass's first read); the
    order-dependent HAZARD it causes is the kit-cell read test's."""
    want = set(tables["order_faults"].get(fault, tables["faults"][fault]) if order == "e1" else tables["faults"][fault])
    r = _run(faults=[fault], order=order)
    assert set(r["red"]) == want, {c: r["detail"][c] for c in set(r["red"]) ^ want}


def test_the_first_read_fault_is_red_in_both_legs_under_both_orders(tables):
    """The 2026-11-02 in-game finding: the boat's @00174 KEYON reads every Confirm on 9011, after entry 0 and before entry 16 in a
    pass, so a close keyed on the pass's first read leaks it on the kit cell and leaks the ferryman whatever the order."""
    both = ["S166-A-KITOFF", "S166-A-FERRYOFF"]
    assert tables["faults"]["kitcell_first_read"] == both and tables["order_faults"]["kitcell_first_read"] == both


def test_each_new_instrument_can_fail():
    """The stand and the freeze, each driven red through the real Session and the bench (a check that cannot fail is not a check):
      * the kit stand moved to FS_LANDING (COOP_WW_KIT_AT: in the 6603 cell, OFF its trigger -- the 2026-11-02 OLD run's stand): "not
        reached (the instrument)", nothing pressed, no close line; under the OLD calibration the hazard is NOT measured (CAL red); so
        is a stand INSIDE the 3-u radius but off the event tiles (the tiles decide);
      * THE FREEZE LIFTED by the engine's own lever (`bench worldfreeze off`) before the press or inside the judged window, in either
        leg: "not reached (the instrument): the freeze lifted ..." -- never the close's verdict; on s165 a hazard seen with the freeze
        lifted is NOT measured (CAL red), because the hazard decision 19 closes is a frozen guest's."""
    runs = _child({"runs": {
        "off_trigger": {"legs": "kitoff", "kit_at": "68,-444"},
        "off_tiles": {"legs": "kitoff", "kit_at": "77.9,-446.1"},
        "off_trigger_old": {"caps": "worldfollow", "cal": True, "legs": "kitoff", "kit_at": "68,-444"},
        "kit_before": {"legs": "kitoff", "lift": "before_press"},
        "kit_after": {"legs": "kitoff", "lift": "after_press"},
        "ferry_before": {"legs": "ferryoff", "lift": "before_press"},
        "ferry_after": {"legs": "ferryoff", "lift": "after_press"},
        "kit_old_lifted": {"caps": "worldfollow", "cal": True, "legs": "kitoff", "lift": "before_press"},
    }})
    r = runs["off_trigger"]
    assert r["red"] == ["S166-A-KITOFF"], {c: r["detail"][c] for c in r["red"]}
    d = r["detail"]["S166-A-KITOFF"]
    assert d.startswith("not reached (the instrument): at (68.0, -444.0): 12.0u from the 6603 trigger") and "event tiles: NO" in d, d
    assert not any(BW.LOG_WORLD_KITCELL in ln for ln in r["log"]), r["log"]
    # inside KIT_TRIGGER_R but off the event tiles (2.97 u out on the SW diagonal): the TILES decide, never the radius alone
    r = runs["off_tiles"]
    assert r["red"] == ["S166-A-KITOFF"], {c: r["detail"][c] for c in r["red"]}
    d = r["detail"]["S166-A-KITOFF"]
    assert d.startswith("not reached (the instrument): at (77.9, -446.1): 3.0u from the 6603 trigger") and "event tiles: NO" in d, d
    assert not any(BW.LOG_WORLD_KITCELL in ln for ln in r["log"]), r["log"]
    r = runs["off_trigger_old"]
    assert "S166-CAL" in r["red"] and "S166-A-KITOFF" in r["detail"]["S166-CAL"].split("NOT measured")[1], r["detail"]["S166-CAL"]
    assert r["detail"]["S166-A-KITOFF"].startswith("not reached (the instrument)")
    for name, row, word in (("kit_before", "S166-A-KITOFF", "the freeze lifted before the press"),
                            ("kit_after", "S166-A-KITOFF", "the freeze lifted at frame"),
                            ("ferry_before", "S166-A-FERRYOFF", "the freeze lifted before the press"),
                            ("ferry_after", "S166-A-FERRYOFF", "the freeze lifted at frame")):
        r = runs[name]
        assert r["red"] == [row], (name, {c: r["detail"][c] for c in r["red"]})
        assert r["detail"][row].startswith("not reached (the instrument): " + word), (name, r["detail"][row])
    r = runs["kit_old_lifted"]
    assert r["detail"]["S166-A-KITOFF"].startswith("not reached (the instrument): the freeze lifted before the press")
    assert "FieldHUD 6603" in r["detail"]["S166-A-KITOFF"]                    # the hazard happened -- unfrozen, so not measured
    assert "S166-CAL" in r["red"] and "S166-A-KITOFF" in r["detail"]["S166-CAL"].split("NOT measured")[1], r["detail"]["S166-CAL"]


# ================================================================================================ the pure judges
_JUDGES = r'''
import importlib.util, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)
from harness.channel import State
BW = ww.BW

def mapvar(**b):
    v = bytearray(80)
    for k, x in b.items():
        v[int(k[1:])] = x
    return v.hex()

def st(ui="WorldHUD", world=9011, field=6603, x=68.0, z=-444.0, kit=None, nm=3, mv=None, fading=False, vehicle=0, frame=1,
       block=True, ticks=10, bench=True, worldkeys=None, ctl=False, frz=True):
    w = {k: (dict(v) if isinstance(v, dict) else v) for k, v in BW.WORLD_SENTINELS_S166.items()}
    w["freeze"].update(on=frz, why="bench" if frz else None)
    if kit is not None:
        w["kitcell"] = {**BW.WORLD_KITCELL_SENTINELS, "lever": "act", **kit}
    if worldkeys is not None:
        w = {k: w.get(k, {}) for k in worldkeys}
    doc = {"frame": frame, "ui_state": ui, "fading": fading, "field": {"id": field if ui == "FieldHUD" else 0},
           "world": {"id": world, "x": x, "z": z, "vehicle": vehicle, "next_mode": nm, "mapvar": mv or mapvar(),
                     "block_ready": block, "ticks": ticks},
           "player": {"control": ctl}, "netsync": {"world": w, "bench": bench}}
    return State(doc)

def red(row, why=None):
    ok, d = row
    assert not ok, d
    if why:
        assert why in d, d
def green(row):
    ok, d = row
    assert ok, d

line0 = "02.11.2026 |M| [NetSync] " + BW.log_world_kitcell(0, 9011)
line16 = "02.11.2026 |M| [NetSync] " + BW.log_world_kitcell(16, 9011)
base = st(kit={"closed": 3})
good = [st(kit={"closed": 5, "last_sid": 0, "last_world": 9011}, frame=f) for f in (2, 3)]
# A-KITOFF: green; a FieldHUD sample, the shutdown armed, another world, the count, the sid, the world, the lever, the line
green(ww.judge_kitoff(base, good, [line0]))
red(ww.judge_kitoff(base, good + [st(ui="FieldHUD", field=6603, kit={"closed": 5, "last_sid": 0, "last_world": 9011})], [line0]),
    "LEFT WorldHUD")
red(ww.judge_kitoff(base, [st(nm=1, kit={"closed": 5, "last_sid": 0, "last_world": 9011})], [line0]), "next_mode 1")
red(ww.judge_kitoff(base, [st(world=9010, kit={"closed": 5, "last_sid": 0, "last_world": 9011})], [line0]), "LEFT")
red(ww.judge_kitoff(base, [st(kit={"closed": 3, "last_sid": 0, "last_world": 9011})], [line0]), "closed +0")
red(ww.judge_kitoff(base, [st(kit={"closed": 6, "last_sid": 0, "last_world": 9011})], [line0]), "closed +3")
red(ww.judge_kitoff(base, [st(kit={"closed": 4, "last_sid": 0, "last_world": 9011})], [line0]), "closed +1")
# the boat's eager read (BW.KIT_EAGER_READERS) reads the same press: entry 15 last is lawful (the frame's order is the engine's)
green(ww.judge_kitoff(base, [st(kit={"closed": 5, "last_sid": 15, "last_world": 9011})], [line0]))
red(ww.judge_kitoff(base, [st(kit={"closed": 5, "last_sid": 1, "last_world": 9011})], [line0]), "last_sid 1")
red(ww.judge_kitoff(base, [st(kit={"closed": 5, "last_sid": 0, "last_world": -1})], [line0]), "last_world -1")
red(ww.judge_kitoff(base, [st(kit={"closed": 5, "last_sid": 0, "last_world": 9011, "lever": "old"})], [line0]), "lever 'old'")
red(ww.judge_kitoff(base, good, []), "0x")
red(ww.judge_kitoff(base, good, [line0, line0]), "2x")
red(ww.judge_kitoff(base, good, [line16]), "0x")
red(ww.judge_kitoff(base, [], [line0]), "not reached")
# THE FREEZE INSTRUMENT: off at the press, lifted on a judged sample -> "not reached" (never the close's verdict); after today's
# hazard first shows (next_mode 1, a field) the world's exit owns the samples
red(ww.judge_kitoff(st(kit={"closed": 3}, frz=False), good, [line0]), "not reached (the instrument): the freeze lifted before")
red(ww.judge_kitoff(base, good + [st(frame=9, frz=False, kit={"closed": 5, "last_sid": 0, "last_world": 9011})], [line0]),
    "not reached (the instrument): the freeze lifted at frame 9")
ok, d = ww.judge_kitoff(base, [st(nm=1, frame=2), st(nm=1, frame=3, frz=False), st(ui="FieldHUD", frz=False, frame=4)], [])
assert not ok and "not reached" not in d and "FieldHUD 6603 reached" in d, d       # OLD's hazard, frozen: a red the CLOSE owns
green(ww.freeze_held(base, [st(nm=1, frame=2), st(nm=1, frz=False, frame=3), st(ui="FieldHUD", frz=False, frame=4)]))
red(ww.freeze_held(base, [st(frame=2), st(frz=False, frame=3), st(nm=1, frame=4)]), "lifted at frame 3")
red(ww.freeze_held(None, good), "before the press")
# the instrument: the press made control-ON, or control given back on a WorldHUD sample after it, judges nothing
red(ww.judge_kitoff(st(kit={"closed": 3}, ctl=True), good, [line0]), "control ON at the press")
red(ww.judge_kitoff(base, good + [st(ctl=True, kit={"closed": 5, "last_sid": 0, "last_world": 9011})], [line0]),
    "on 1 WorldHUD sample")
green(ww.control_held_off(base, good + [st(ui="FieldHUD", ctl=True)]))      # a field's control is not the world's read
S165 = list(BW.WORLD_SENTINELS_S165)
red(ww.judge_kitoff(st(worldkeys=S165), [st(worldkeys=S165)], [line0]), "absent")     # an s165 engine: no key
# the hazard reading: FieldHUD 6603 reached, the shutdown alone, none
assert ww.kit_hazard([st(ui="FieldHUD", field=6603)])[:2] == (True, True)
assert ww.kit_hazard([st(nm=1)])[:2] == (True, False)
assert ww.kit_hazard(good)[:2] == (False, False)
# A-FERRYOFF: green; Map[50] on any sample, a fade, an unread digest, another world, the witness for 16
fbase = st(kit={"closed": 7})
fgood = [st(kit={"closed": 9, "last_sid": 16, "last_world": 9011}, frame=f) for f in (2, 3)]
green(ww.judge_ferryoff(fbase, fgood, [line16]))
red(ww.judge_ferryoff(fbase, fgood + [st(mv=mapvar(m50=1), kit={"closed": 9, "last_sid": 16, "last_world": 9011})], [line16]),
    "Map[50] read [1]")
red(ww.judge_ferryoff(fbase, [st(fading=True, kit={"closed": 9, "last_sid": 16, "last_world": 9011})], [line16]), "fading on 1")
bad_mv = st(kit={"closed": 9, "last_sid": 16, "last_world": 9011})
bad_mv.raw["world"]["mapvar"] = None
red(ww.judge_ferryoff(fbase, [bad_mv], [line16]), "no MAP digest")
red(ww.judge_ferryoff(fbase, [st(ui="FieldHUD", kit={"closed": 9, "last_sid": 16, "last_world": 9011})], [line16]), "LEFT")
red(ww.judge_ferryoff(fbase, [st(kit={"closed": 9, "last_sid": 0, "last_world": 9011})], [line16]), "last_sid 0")
green(ww.judge_ferryoff(fbase, [st(kit={"closed": 9, "last_sid": 15, "last_world": 9011})], [line16]))
red(ww.judge_ferryoff(fbase, [st(kit={"closed": 8, "last_sid": 16, "last_world": 9011})], [line16]), "closed +1")
red(ww.judge_ferryoff(fbase, fgood, [line0]), "0x")
red(ww.judge_ferryoff(st(kit={"closed": 7}, ctl=True), fgood, [line16]), "control ON at the press")
red(ww.judge_ferryoff(st(kit={"closed": 7}, frz=False), fgood, [line16]), "not reached (the instrument): the freeze lifted before")
red(ww.judge_ferryoff(fbase, fgood + [st(frame=8, frz=False, kit={"closed": 9, "last_sid": 16, "last_world": 9011})], [line16]),
    "not reached (the instrument): the freeze lifted at frame 8")
assert ww.ferry_hazard([st(mv=mapvar(m50=2))])[0] and not ww.ferry_hazard(fgood)[0]
assert ww.map_byte(st(mv=mapvar(m50=7, m24=100)), 50) == 7 and ww.map_byte(st(mv=mapvar(m24=100)), 24) == 100
# the instruments: the landing (judged, the pose, on foot), the kit stand (ON the 6603 trigger's tiles, within 3 u, on foot, FROZEN),
# the ferry stand (the box, never a kit cell, Map[50] / [51], FROZEN)
green(ww.judge_landing(st()))
red(ww.judge_landing(None), "not judged")
red(ww.judge_landing(st(x=100.0, z=-444.0)), "32.0u from")
red(ww.judge_landing(st(x=50.0, z=-444.0)), "18.0u from")
red(ww.judge_landing(st(vehicle=6)), "[190] 6")
red(ww.judge_landing(st(world=9010)), "not on world 9011")
green(ww.judge_kit_stand(st(x=80.0, z=-444.0)))
green(ww.judge_kit_stand(st(x=81.5, z=-445.5)))
red(ww.judge_kit_stand(st()), "12.0u from the 6603 trigger")                 # FS_LANDING: in the cell, off the trigger
red(ww.judge_kit_stand(st()), "event tiles: NO")
red(ww.judge_kit_stand(st(x=77.9, z=-446.1)), "event tiles: NO")             # within 3 u, off the tiles: the tiles decide
red(ww.judge_kit_stand(st(x=76.0, z=-440.0)), "(want <= 3)")                 # on a tile corner, 5.7 u out
red(ww.judge_kit_stand(st(x=80.0, z=-444.0, frz=False)), "NOT FROZEN")
red(ww.judge_kit_stand(st(x=80.0, z=-444.0, vehicle=6)), "[190] 6")
red(ww.judge_kit_stand(st(x=80.0, z=-444.0, world=9010)), "not on world 9011")
red(ww.judge_kit_stand(None), "no state")
green(ww.judge_ferry_stand(st(x=26.0, z=-1160.0)))
red(ww.judge_ferry_stand(st(x=26.0, z=-1160.0, frz=False)), "NOT FROZEN")
red(ww.judge_ferry_stand(st(x=26.0, z=-1180.5)), "OUTSIDE")
red(ww.judge_ferry_stand(st(x=36.0, z=-1160.0)), "kit cell 6601")
red(ww.judge_ferry_stand(st(x=26.0, z=-1160.0, mv=mapvar(m51=1))), "Map[51] 1")
red(ww.judge_ferry_stand(st(x=26.0, z=-1160.0, mv=mapvar(m50=1))), "Map[50] 1")
# P0: the prefix law (kitcell right after dot), its shape, the proof line, a FAIL; P1: the lever's rest word, the bench
P = ["[NetSync] world walk selftest: OK (84 rows, 13 mutants)"]
green(ww.judge_probe(st(kit={}), P))
green(ww.judge_probe(st(kit={}, worldkeys=list(BW.WORLD_SENTINELS_S166) + ["later"]), P))     # a later piece's key after it
red(ww.judge_probe(st(kit={}), []), "NONE")
red(ww.judge_probe(st(kit={}), P + ["[NetSync] world walk selftest: FAILED (row kit_cell.9011_sid0_closes failed (1 of 84))"]),
    "FAIL lines 1")
red(ww.judge_probe(st(kit={}, worldkeys=["freeze", "rejoin", "waitline", "dio", "r3", "out", "host", "kitcell", "dot"]), P))
moved = st(kit={})
moved.raw["netsync"]["world"]["kitcell"] = {"closed": 0, "lever": "act", "last_sid": -1, "last_world": -1}
red(ww.judge_probe(moved, P))
red(ww.judge_probe(st(worldkeys=S165), P), "absent")
green(ww.judge_rest(st(kit={})))
red(ww.judge_rest(st(kit={"lever": "old"})), "lever 'old'")
green(ww.judge_rest(st(kit={"lever": "old"}), lever_old=True))
red(ww.judge_rest(st(kit={}, bench=False)), "bench False")
# R: the release
green(ww.judge_release(True, 1, st(kit={}), False))
red(ww.judge_release(False, 1, st(kit={}), False), "pulled before the reset: False")
red(ww.judge_release(True, 0, st(kit={}), False), "0x")
red(ww.judge_release(True, 1, st(kit={"lever": "old"}), False), "'old'")
red(ww.judge_release(True, 1, st(kit={}), True), "forced=True")
red(ww.judge_release(True, 1, None, False))
# CAL: the prediction AND the hazard measured on every selected leg
green(ww.judge_cal({"S166-P0", "S166-P1", "S166-A-KITOFF"}, ["S166-P0", "S166-P1", "S166-A-KITOFF"], {"S166-A-KITOFF": True},
                   ["S166-A-KITOFF"]))
red(ww.judge_cal({"S166-P0", "S166-P1", "S166-A-KITOFF"}, ["S166-P0", "S166-P1", "S166-A-KITOFF"], {}, ["S166-A-KITOFF"]),
    "NOT measured: ['S166-A-KITOFF']")
red(ww.judge_cal({"S166-P0"}, ["S166-P0", "S166-A-KITOFF"], {"S166-A-KITOFF": True}, ["S166-A-KITOFF"]), "stayed GREEN")
red(ww.judge_cal({"S166-P0", "S166-OR"}, ["S166-P0"], {}, []), "unpredicted reds: ['S166-OR']")
print("ok")
'''


def test_the_pure_judges_go_red_on_each_wrong_shape():
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _JUDGES, str(SCENARIOS), str(REPO / "tools")],
                         env={k: v for k, v in os.environ.items() if not k.startswith("COOP_")}, capture_output=True, text=True,
                         timeout=120)
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), (out.stdout[-2000:], out.stderr[-4000:])


# ================================================================================================ the offline oracle's trigger half
_TRIGGER = r'''
import importlib.util, json, os, pathlib, struct, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
from ff9mapkit.world import mesh as WM
from ff9mapkit.world import extract as WX

def load():
    spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

ww = load()
BW = ww.BW
REL = WM.override_relpath(1, 1, 6)                       # the kit's own override path for KIT_STAND's block
OX, OZ = WX.block_world_origin(1, 6)
EV1, EV0 = WX.encode_id(event=1, area=14), WX.encode_id(event=0, area=14)

def mesh(tris) -> bytes:
    """[(world (x, z) triangle, IDALL)] -> an UNINDEXED .ff9mesh (3 fresh verts a triangle, the tangent channel's x the IDALL)."""
    verts, tans = [], []
    for pts, idall in tris:
        for x, z in pts:
            verts.append((float(x - OX), 0.0, float(z - OZ)))
            tans.append((float(idall), 0.0, 0.0, 1.0))
    n = len(verts)
    out = bytearray(WM.MAGIC) + struct.pack("<iiii", WM.VERSION, n, n, 4)
    for v in verts:
        out += struct.pack("<3f", *v)
    for t in tans:
        out += struct.pack("<4f", *t)
    return bytes(out + struct.pack("<%di" % n, *range(n)))

def game(files) -> pathlib.Path:
    """A stand-in install: [Mod] FolderNames, highest first, and each folder's Block[1][6] Terrain override (bytes or tris)."""
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap", "FF9CustomMap-world"\n', encoding="utf-8")
    for folder, body in files.items():
        p = t / folder / REL
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(body if isinstance(body, bytes) else mesh(body))
    return t

CENSUS = [(t, EV1) for t in BW.KIT_TRIGGER_TILES[(2, 13)]]
LANDING = [(tuple((x - 12, z) for x, z in t), EV0) for t, _id in CENSUS]          # FS_LANDING's hexagon: plain land
OTHER = [(((100, -400), (104, -400), (104, -404)), EV1)]                          # an event tile in cell (3, 12): another cell's
GOOD = CENSUS + LANDING + OTHER
out = {
    "rel": REL,
    "ok": ww.read_trigger_oracle(game({"FF9CustomMap-world": GOOD})),
    "gone": ww.read_trigger_oracle(game({"FF9CustomMap-world": [(CENSUS[0][0], EV0)] + CENSUS[1:] + LANDING})),
    "new": ww.read_trigger_oracle(game({"FF9CustomMap-world": CENSUS + [(LANDING[0][0], EV1)] + LANDING[1:]})),
    "none": ww.read_trigger_oracle(game({})),
    "higher_wins": ww.read_trigger_oracle(game({"FF9CustomMap": LANDING, "FF9CustomMap-world": GOOD})),
    "higher_good": ww.read_trigger_oracle(game({"FF9CustomMap": GOOD, "FF9CustomMap-world": LANDING})),
    "corrupt": ww.read_trigger_oracle(game({"FF9CustomMap-world": b"not a mesh"})),
}
os.environ["COOP_WW_KIT_AT"] = "68,-444"                                          # the stand moved OFF the trigger
out["stand_off"] = load().read_trigger_oracle(game({"FF9CustomMap-world": GOOD}))
print(json.dumps(out))
'''


def test_the_trigger_oracle_reads_the_deployed_tiles_and_can_fail():
    """S166-OR's trigger half (read_trigger_oracle) against stand-in installs it reads through the kit's own .ff9mesh reader -- a check
    that cannot fail is not a check: green on the census (FS_LANDING's plain tiles and another cell's event tile not counted); red on
    one census tile gone, one new event tile in the cell, no override, a corrupt override, the HIGHER-priority folder's override
    (FolderNames order) missing the trigger, and KIT_STAND moved off the tiles (COOP_WW_KIT_AT)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _TRIGGER, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-4000:]
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["rel"] == "FF9_Data/WorldMap/Disc1/0_1/r6/Block[1][6] Terrain.ff9mesh"
    assert r["ok"]["problem"] is None and "6 event tile(s) in cell (2, 13)" in r["ok"]["fact"], r["ok"]
    assert r["higher_good"]["problem"] is None and r["higher_good"]["fact"].startswith("FF9CustomMap/"), r["higher_good"]
    for name, word in (("gone", "1 gone"), ("new", "1 new"), ("higher_wins", "6 gone"), ("none", "no stacked folder overrides"),
                       ("corrupt", "ValueError"), ("stand_off", "is not on the 6603 trigger's tiles")):
        assert r[name]["problem"] and word in r[name]["problem"], (name, r[name])
    assert "re-census" in r["gone"]["problem"] and "re-census" in r["new"]["problem"]


# ================================================================================================ the engine's source (skipped until it lands)
S166_TAG = "[ff9mapkit netsync s166]"
S166_CLONE_ENV = "FF9_S166_CLONE"
_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


def _s166_patch():
    names = [nm for nm in msr.stack() if nm.startswith("s166-") and nm not in msr.DEAD]
    return (msr.PATCHES / names[0]).read_bytes() if names else None


def _s166_text(file_name: str) -> str:
    """The s166 post-image of ``file_name``: the patch's hunks (context and added lines) on the stack, the whole file in a clone named
    by FF9_S166_CLONE that carries the s166 tag; else the pin SKIPS (the engine lane is mid-build)."""
    blob = _s166_patch()
    if blob is not None:
        out = []
        for path, sec in msr.sections(blob):
            if path and path.replace("\\", "/").rsplit("/", 1)[-1] == file_name:
                out += [ln[1:] for ln in sec.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
                        if ln[:1] in (" ", "+") and not ln.startswith("+++")]
        return "\n".join(out)
    raw = os.environ.get(S166_CLONE_ENV, "").strip()
    root = pathlib.Path(raw) if raw else None
    if root is not None and (root / "Memoria" / "Netsync").is_dir() and any(
            S166_TAG in p.read_text(encoding="utf-8-sig", errors="replace") for p in (root / "Memoria" / "Netsync").glob("*.cs")):
        hits = [p for p in root.rglob(file_name) if p.is_file()]
        return hits[0].read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n") if hits else ""
    pytest.skip("the s166 patch is not on this branch's stack yet (the engine lane is mid-build; the integration step emits it) -- set "
                f"{S166_CLONE_ENV}=<the clone's Assembly-CSharp> to pin a clone that carries the tag")


def _s166_catch_world() -> dict:
    """The netsync-off catch literal's `netsync.world` object as the s166 HarnessAgent writes it."""
    lines = _s166_text("HarnessAgent.cs").split("\n")
    catch = [ln for ln in lines if re.search(r'outer\.Append\("\\"netsync\\":\{\\"enabled', ln)]
    head = [ln for ln in lines if 'NetsyncF3Retired = "' in ln]
    tail = [ln for ln in lines if re.search(r'\+ "\\"align_win', ln)]
    if not (catch and head and tail):
        pytest.skip("the s166 patch does not carry the catch literal's lines (it never touched HarnessAgent.cs?)")
    a, b = _LIT.findall(catch[0])
    pinned = "".join(_LIT.findall(head[0]) + _LIT.findall(tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]["world"]


def test_s166_the_catch_line_carries_kitcell_at_its_sentinel_after_dot():
    world = _s166_catch_world()
    assert list(world)[-2:] == ["dot", "kitcell"], list(world)
    assert json.dumps(world["kitcell"]) == json.dumps(CONTRACT_KITCELL)
    agent = _s166_text("HarnessAgent.cs")
    assert any(S166_TAG in ln and "sentinel" in ln and ln.strip().startswith("//") for ln in agent.split("\n")), \
        "no history comment line beside the catch literal"


def test_s166_the_engines_stock_last_table_is_battlewires():
    """The close's reader term (b) reads the engine's StockLast table (indexed world - 9000): battlewire's STOCK_LAST_ENTRY is the same
    table, world for world -- a drift would let the stand-in pass a close the engine never makes (or miss one it does)."""
    text = _s166_text("NetSyncWorldWalk.cs")
    m = re.search(r"StockLast\s*=\s*\{(.*?)\};", text, re.S)
    if not m:
        pytest.skip("the s166 source carries no StockLast table (the engine lane put the rule elsewhere)")
    vals = [int(v) for v in re.findall(r"^\s*(-?\d+),", m.group(1), re.M)]
    assert {9000 + i: v for i, v in enumerate(vals)} == BW.STOCK_LAST_ENTRY, vals


def test_s166_the_agent_speaks_the_contracts_verb_key_and_lines():
    agent = _s166_text("HarnessAgent.cs")
    m = re.search(r"netsync: unknown sub-verb[^\n]*\(([a-z0-9|-]+)\)", agent)
    assert m and m.group(1).split("|")[-2:] == ["worldfollow", "worldwalk"], m and m.group(1)
    assert '\\"kitcell\\"' in agent or '"kitcell"' in agent
    text = "\n".join(ln for name in ("HarnessAgent.cs", "NetSyncClient.cs", "NetSyncField.cs", "NetSyncWorldWalk.cs", "NetSyncBattle.cs")
                     for ln in _s166_text(name).split("\n") if '"' in ln)
    for frag in (BW.LOG_WORLD_KITCELL, BW.PROOF_WORLD_WALK, "harness: worldwalk ", "kitcell old|act", "worldwalk levers released"):
        assert frag in text, frag
    # the stand-in's whole lines are the engine's: the verb's texts, and the close line's literal pieces in the order it joins them
    for ln in (BW.WORLDWALK_USAGE, BW.WORLDWALK_OFF_REFUSAL, BW.LOG_WORLDWALK_RELEASED, BW.LOG_WORLDWALK_KITCELL_OLD,
               BW.LOG_WORLDWALK_KITCELL_ACT, BW.LOG_WORLDWALK_CLEAR):
        assert f'"{ln}"' in text, ln
    pieces = ('"[NetSync] world kit-cell close: entry "', '" on world map "', '"entry 0: the kit\'s entrance cells"',
              '"beyond the stock dispatcher\'s last entry "', '": a kit object"',
              '") -- a control-off read of a host-owned key masked (following guest): the host drives; the guest rejoins at their next stop"')
    at, i = [], 0
    for p in pieces:                                                    # each piece AFTER the one before it (a shared piece such as
        i = text.find(p, i)                                             # " on world map " also sits in older lines)
        at.append(i)
        if i < 0:
            break
    assert all(i >= 0 for i in at) and at[-1] - at[0] < 1500, dict(zip(pieces, at))   # one statement, in its own order
    assert "[NetSync] " + BW.log_world_kitcell(0, 9011) == "".join(
        [pieces[0][1:-1], "0", pieces[1][1:-1], "9011 (", pieces[2][1:-1], pieces[5][1:-1]])
