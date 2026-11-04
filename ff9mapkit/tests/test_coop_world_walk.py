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

from ._patchstack import msr, stack_file

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
CONTRACT_OPS = ("kitcell", "pairpull", "clear")          # [ff9mapkit netsync s166] A0b grew the verb (the A0 build's: WORLDWALK_OPS_A0)


def test_the_s166_contract_is_battlewires_to_the_key():
    """The key's catch-line sentinel (json text, order included) as netsync.world's LAST key after s165's `dot` (the prefix law); the
    verb's ops and words; the log prefixes and the proof line's regex; the census facts the stand-in and the bench share."""
    assert json.dumps(BW.WORLD_KITCELL_SENTINELS) == json.dumps(CONTRACT_KITCELL)
    assert list(BW.WORLD_SENTINELS_S166) == list(BW.WORLD_SENTINELS_S165) + ["kitcell"] and BW.WORLD_S166_KEYS == ("kitcell",)
    assert {k: v for k, v in BW.WORLD_SENTINELS_S166.items() if k != "kitcell"} == BW.WORLD_SENTINELS_S165
    assert BW.WORLDWALK_OPS == CONTRACT_OPS and BW.WORLDWALK_WORDS["kitcell"] == ("old", "act")
    assert BW.WORLDWALK_OPS_A0 == ("kitcell", "clear") and BW.WORLDWALK_WORDS_A0 == {"kitcell": ("old", "act")}   # the A0 build
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
    # no top-level netsync key in A0 or A0b; [ff9mapkit netsync s166] A2 (the same rung) appends `wire_peer`, netsync's LAST key
    assert FG.NETSYNC_TOP_CAP_KEYS["worldwalk"] == BW.NETSYNC_TOP_KEYS_S166 == ("wire_peer",)
    # [ff9mapkit netsync s166] A0b grows the SAME rung (one patch): `pairpull` after `kitcell`; W2: A3's `lane` / `line` after it and A4's
    # `ghost` after `line`, and inside older blocks A3's `host.world.guest` and A4's `world.dot.src` .. `src_face`
    assert FG.NETSYNC_TOP_NESTED_KEYS["worldwalk"] == {"world": ("kitcell", "pairpull", "lane", "line", "ghost"),
                                                       "world.dot": ("src", "src_lever", "src_x", "src_z", "src_face"),   # A4 final
                                                       "host.world": ("guest",)} and FG.NETSYNC_BATTLE_CAP_KEYS["worldwalk"] == {}
    assert FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldwalk"] == tuple(BW.WORLD_SENTINELS_S166D)
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
        assert list(st.netsync["world"]) == list(FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldwalk"]) and st.coop_world_walk is True   # [s166] + A0b, A3, A4
        assert st.world_kitcell_block == dict(CONTRACT_KITCELL, lever="act")
        seq = g.state.seq
        for bad in (("bogus",), ("kitcell",), ("kitcell", "maybe"), ("kitcell", "old", "1"), ("clear", "1"), ()):
            # [ff9mapkit netsync s166] W2 reconcile: the usage line THIS engine answers -- the newest stand-in's is A4's grown line
            with pytest.raises(HarnessError, match=re.escape(BW.WORLDWALK_USAGE_A4)):
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
    by FF9_S166_CLONE that carries the s166 tag; else the pin SKIPS (the engine lane is mid-build). [ff9mapkit netsync s166] On the stack a
    file the stack CREATES (every Memoria/Netsync/*.cs) reads WHOLE, as the stack builds it (tests/_patchstack.stack_file) -- a pin that
    reads an earlier round's line no s166 hunk touches (s154's pairing verdicts) must find it there exactly as in the clone."""
    blob = _s166_patch()
    if blob is not None:
        try:
            return "\n".join(stack_file(file_name))
        except AssertionError:
            pass                                    # a file the stack does not create (HarnessAgent.cs's base is stock): the hunks
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


def _s166_verb_words() -> tuple:
    """[ff9mapkit netsync s166] W2 reconcile: (the usage line, the clear line) the s166 source's `worldwalk` speaks, BY ITS STAGE read off
    its structure (never off the words themselves): A4 once NetSyncClient calls into NetSyncWorldGhost, A3 once it carries WorldLaneStep,
    else A0b's -- each piece GROWS both lines, so an earlier piece's whole line is no longer in a later source."""
    client = _s166_text("NetSyncClient.cs")
    if "NetSyncWorldGhost." in client:
        return BW.WORLDWALK_USAGE_A4, BW.LOG_WORLDWALK_CLEAR_A4
    if "private void WorldLaneStep(" in client:
        return BW.WORLDWALK_USAGE_A3, BW.LOG_WORLDWALK_CLEAR_A3
    return BW.WORLDWALK_USAGE, BW.LOG_WORLDWALK_CLEAR


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
    # [ff9mapkit netsync s166] the prefix law: `kitcell` right after s165's `dot`; A0b's `pairpull` (when the source carries it) after it
    keys = list(world)
    tail = keys[keys.index("dot"):] if "dot" in keys else keys
    # [ff9mapkit netsync s166] W2: round A's keys in their order -- A0's alone, + A0b's, + A3's two, + A4's, by the source's stage
    assert len(tail) in (2, 3, 5, 6) and tail == ["dot"] + list(BW.WORLD_S166_ROUND_A_KEYS[:len(tail) - 1]), keys
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
    usage, clear = _s166_verb_words()                   # [ff9mapkit netsync s166] W2 reconcile: the usage and clear line BY THE SOURCE'S STAGE
    for ln in (usage, BW.WORLDWALK_OFF_REFUSAL, BW.LOG_WORLDWALK_RELEASED, BW.LOG_WORLDWALK_KITCELL_OLD, BW.LOG_WORLDWALK_KITCELL_ACT, clear):
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


# ================================================================================================ [ff9mapkit netsync s166] PIECE A0b
# Decision 26, THE PAIRING PULL: the contract, the twins (the pairing window's verdicts and the pull's term) and their mutants, the
# stand-in's pairing window and landing arm, the T2-A pair leg on a stub replay-host that honours --from, D-PAIR on a stub duo whose
# link starts at the guest's apply_role, and the pure judges red on each wrong shape.
CONTRACT_PAIRPULL = {"lever": None, "pending": False, "arms": 0, "last_world": -1}


def test_s166b_the_contract_is_battlewires_to_the_key():
    """The key's catch-line sentinel (json, order included) as netsync.world's LAST key after A0's `kitcell` (the prefix law); the verb
    grown by `pairpull old|act` with the A0 build's own beside it; the why APPENDED after s165's 28 (`pairing_save`, its words); the
    log lines the engine writes (the ARMED line's world form keeps the field form's prefix; the no-autosave line names the landing)."""
    assert json.dumps(BW.WORLD_PAIRPULL_SENTINELS) == json.dumps(CONTRACT_PAIRPULL)
    assert list(BW.WORLD_SENTINELS_S166B) == list(BW.WORLD_SENTINELS_S166) + ["pairpull"] and BW.WORLD_S166B_KEYS == ("pairpull",)
    assert {k: v for k, v in BW.WORLD_SENTINELS_S166B.items() if k != "pairpull"} == BW.WORLD_SENTINELS_S166
    assert BW.WORLD_S166_ALL_KEYS == ("kitcell", "pairpull") and BW.WORLD_PAIRPULL_LEVER_WORDS == ("act", "old")
    assert BW.WORLDWALK_OPS == ("kitcell", "pairpull", "clear") and BW.WORLDWALK_WORDS == {"kitcell": ("old", "act"),
                                                                                           "pairpull": ("old", "act")}
    assert BW.WORLDWALK_OPS_A0 == ("kitcell", "clear") and BW.WORLDWALK_WORDS_A0 == {"kitcell": ("old", "act")}
    assert BW.WORLDWALK_USAGE == "netsync worldwalk: expected kitcell old|act, pairpull old|act or clear (any role)"
    assert BW.WORLDWALK_USAGE_A0 == "netsync worldwalk: expected kitcell old|act or clear (any role)"
    for ln, (op, word) in ((BW.LOG_WORLDWALK_PAIRPULL_OLD, ("pairpull", "old")), (BW.LOG_WORLDWALK_PAIRPULL_ACT, ("pairpull", "act")),
                           (BW.LOG_WORLDWALK_CLEAR, ("clear", None)), (BW.LOG_WORLDWALK_CLEAR_A0, ("clear", None))):
        assert ln.startswith(BW.worldwalk_ack(op, word)), ln
    # the why: appended, nothing renumbered (the benches key on the names); `not_mirroring` stays index 4 (WhyNotMirroring)
    assert BW.WORLD_OUT_WHYS_S166 == BW.WORLD_OUT_WHYS + ("pairing_save",) and len(BW.WORLD_OUT_WHYS) == 28
    assert BW.WORLD_OUT_WHYS_S166.index("pairing_save") + 1 == 29 and BW.WORLD_OUT_WHYS.index("not_mirroring") + 1 == 4
    assert BW.WORDS_WORLD_OUT_PAIRING == "your pairing autosave is still pending"
    # the ARMED lines: the field form byte-identical (s144), the world form "at world map W's landing", the prefix both share
    assert BW.LOG_MIRROR_ARMED_FIELD == "[NetSync] state-mirror ARMED -- this guest's fields now stage the HOST's story"
    assert BW.log_mirror_armed_world(9011) == ("[NetSync] state-mirror ARMED at world map 9011's landing -- this guest's fields now "
                                               "stage the HOST's story")
    for ln in (BW.LOG_MIRROR_ARMED_FIELD, BW.log_mirror_armed_world(9011)):
        assert ln.startswith(BW.LOG_MIRROR_ARMED_PREFIX) and ln.startswith("[NetSync] state-mirror ARMED")
    assert re.match(BW.MIRROR_ARMED_FIELD_RE, BW.LOG_MIRROR_ARMED_FIELD) and not re.match(BW.MIRROR_ARMED_FIELD_RE,
                                                                                         BW.log_mirror_armed_world(9011))
    m = re.match(BW.MIRROR_ARMED_WORLD_RE, BW.log_mirror_armed_world(9011))
    assert m and m.group(1) == "9011" and not re.match(BW.MIRROR_ARMED_WORLD_RE, BW.LOG_MIRROR_ARMED_FIELD)
    # the window's lines (s154's text): the write, the no-autosave line in both forms
    w = re.match(BW.PAIRING_WRITTEN_RE, BW.log_pairing_written("field 6603"))
    assert w and w.groups() == ("field", "6603", "pairing window")
    assert BW.log_pairing_written("field 6603") == ("[NetSync] pairing autosave written on field 6603 (the pairing window): leaving "
                                                    "co-op returns you here")
    n = re.match(BW.NO_PAIRING_RE, BW.log_no_pairing(BW.world_landing(9011)))
    assert n and n.group(2) == "9011" and n.group(3) == BW.NO_PAIRING_NOTE
    n = re.match(BW.NO_PAIRING_RE, BW.log_no_pairing("field 6603's load", "declined at x"))
    assert n and n.group(1) == "6603" and n.group(3) == "declined at x"
    assert BW.log_no_pairing(BW.world_landing(9011)).startswith(BW.LOG_NO_PAIRING + "world map 9011's landing first (")


# (window_open, written, verdict) -> pending: NetSyncWorldFollow.PairingSavePending's rows as the engine's proof has them
PENDING_ROWS = [
    ((True, False, BW.PAIR_BUSY), True),            # busy: not free-standing yet -- it waits
    ((True, True, BW.PAIR_WRITE), False),           # written in this Update -- the start may follow
    ((True, False, BW.PAIR_NOT_OWN_PLACE), False),  # durable declines: the window will never write here
    ((True, False, BW.PAIR_AUTOSAVE_OFF), False),
    ((True, False, BW.PAIR_STOCK_REFUSED), False),
    ((True, False, -1), True),                      # nothing judged yet at this entry (fail-closed)
    ((True, False, BW.PAIR_WRITE), True),           # a candidate not yet written
    ((True, False, BW.PAIR_ALREADY), True),         # a write tried here that FAILED (nothing written): s165's wait
    ((True, False, BW.PAIR_NO_WINDOW), True),
    ((False, False, BW.PAIR_BUSY), False),          # a shut window (a commit, the arm, the fall) is never pending
    ((False, False, -1), False),
    ((True, True, BW.PAIR_ALREADY), False),         # written: never pending, whatever the verdict
]
# (mirroring, bench, pairpull_old, pending) -> term 3's token
TERM_ROWS = [
    ((False, False, False, True), "pairing_save"),
    ((False, False, False, False), None),           # written / durable: the start goes on
    ((True, False, False, True), None),             # a mirroring guest passes as today
    ((False, True, False, True), None),             # the bench stays exempt
    ((False, False, True, False), "not_mirroring"),  # `pairpull old`: s165's term exactly
    ((False, False, True, True), "not_mirroring"),
    ((True, False, True, False), None),
]


@pytest.mark.parametrize("args,want", PENDING_ROWS)
def test_s166b_the_pending_twin_reads_decision_26(args, want):
    assert BW.pairing_save_pending(*args) is want


@pytest.mark.parametrize("args,want", TERM_ROWS)
def test_s166b_the_term_twin_reads_decision_26(args, want):
    assert BW.pairing_term(*args) == want


_PENDING_MUTANTS = {
    # the engine's own mutants (NetSyncWorldFollow's OwnRowMutants: each must fail ITS row)
    "pending_durable_waits": (lambda o, wr, v: o and not wr, (True, False, BW.PAIR_NOT_OWN_PLACE)),
    "pending_written_blind": (lambda o, wr, v: o and v <= BW.PAIR_BUSY, (True, True, BW.PAIR_WRITE)),
    "pending_window_blind": (lambda o, wr, v: not wr and v <= BW.PAIR_BUSY, (False, False, BW.PAIR_BUSY)),
    "pending_failed_free": (lambda o, wr, v: o and not wr and v == BW.PAIR_BUSY, (True, False, BW.PAIR_ALREADY)),
}
_TERM_MUTANTS = {
    "start_mirror_only": (lambda m, b, old, p: None if (m or b) else "not_mirroring", (False, False, False, False)),
    "start_pending_blind": (lambda m, b, old, p: None if (m or b) else ("not_mirroring" if old else None), (False, False, False, True)),
    "start_pairpull_blind": (lambda m, b, old, p: None if (m or b) else ("pairing_save" if p else None), (False, False, True, False)),
    "start_pairing_bench": (lambda m, b, old, p: None if m else ("not_mirroring" if old else ("pairing_save" if p else None)),
                            (False, True, False, True)),
}


@pytest.mark.parametrize("name", sorted(_PENDING_MUTANTS))
def test_s166b_each_pending_mutant_fails_its_own_row(name):
    fn, row = _PENDING_MUTANTS[name]
    want = dict(PENDING_ROWS)[row]
    assert fn(*row) != want, name
    assert any(bool(fn(*a)) != w for a, w in PENDING_ROWS)


@pytest.mark.parametrize("name", sorted(_TERM_MUTANTS))
def test_s166b_each_term_mutant_fails_its_own_row(name):
    fn, row = _TERM_MUTANTS[name]
    assert fn(*row) != dict(TERM_ROWS)[row], name


def test_s166b_the_window_twins_read_s154():
    """PairWindowAfter's edges; PairingDurableVerdict's order (no window -> already -> busy -> not own place -> autosave off -> the
    ladder -> a candidate); PairingLiveVerdict (a durable decline passes through, a candidate busy until free-standing); the reasons."""
    assert BW.pair_window_after(False, BW.PAIR_EDGE_RISE, True) and not BW.pair_window_after(False, BW.PAIR_EDGE_RISE, False)
    assert not any(BW.pair_window_after(True, e, True) for e in (BW.PAIR_EDGE_FALL, BW.PAIR_EDGE_COMMIT, BW.PAIR_EDGE_ARM))
    assert BW.pair_window_after(True, 5, False) and not BW.pair_window_after(False, 5, True)     # the bounce: no edge
    v = BW.pairing_durable_verdict
    assert v(False, True, True, True, False, True, True, False, False) == BW.PAIR_NO_WINDOW
    assert v(True, True, True, False, False, True, True, False, False) == BW.PAIR_NO_WINDOW      # mirroring: not my own story
    assert v(True, True, True, True, True, False, False, True, True) == BW.PAIR_ALREADY
    assert v(True, True, True, True, False, False, False, True, True) == BW.PAIR_BUSY
    assert v(True, True, True, True, False, True, False, True, True) == BW.PAIR_NOT_OWN_PLACE
    assert v(True, True, True, True, False, True, True, True, True) == BW.PAIR_AUTOSAVE_OFF
    assert v(True, True, True, True, False, True, True, False, True) == BW.PAIR_STOCK_REFUSED
    assert v(True, True, True, True, False, True, True, False, False) == BW.PAIR_WRITE
    lv = BW.pairing_live_verdict
    assert lv(BW.PAIR_WRITE, False, False) == BW.PAIR_BUSY and lv(BW.PAIR_WRITE, True, True) == BW.PAIR_STOCK_REFUSED
    assert lv(BW.PAIR_WRITE, True, False) == BW.PAIR_WRITE and lv(BW.PAIR_AUTOSAVE_OFF, False, False) == BW.PAIR_AUTOSAVE_OFF
    assert BW.PAIR_DURABLE == (4, 5, 6) and all(v > BW.PAIR_BUSY for v in BW.PAIR_DURABLE)
    assert BW.pairing_save_reason(BW.PAIR_AUTOSAVE_OFF) == "[SaveFile] DisableAutoSave=1" and BW.pairing_save_reason(BW.PAIR_WRITE) is None


# ------------------------------------------------------------------------------------------------ the stand-in, direct
def _pfake(root, *, pieces=None, faults=(), window=True, caps=None) -> FakeGame:
    f = _fake(root, caps=caps, faults=faults, kit=False)
    if pieces is not None:
        f.world_walk_pieces = tuple(pieces)
    f.pairing_window = dict(FG.FAKE_PAIRING_WINDOW, **(window if isinstance(window, dict) else {})) if window else None
    return f


def _pair_on_6603(g, fake, *, flags=BW.HF_WORLD | BW.HF_CONTROL | BW.HF_MENU, pose=(1197.37, -796.7), busy=False):
    """A New-Game guest on its own 6603 (no session), then the followed session rises with the host ALREADY on 9011 at ``pose``."""
    g.newgame(settle=0)
    g.warp(6603)
    g.wait_frames(6)
    if busy:
        fake.menu_control_enable = False                    # not free-standing: the window's write waits (busy)
    fake.follow_session(0, flags=flags, fresh=True)
    fake.host_world_pose(*pose, idx=11)


def _pw_lines(fake) -> list:
    return [ln.split("|M| ", 1)[-1] for ln in _log(fake).splitlines()
            if "pairing autosave" in ln or "state-mirror ARMED" in ln or "world follow-out: " in ln or "no pairing autosave" in ln]


def test_s166b_a_free_standing_guest_writes_at_the_rise_and_is_pulled_out_and_armed(tmp_path):
    """THE PULL on the stand-in, every engine fact in order: the window rises with the session, the free-standing guest's write comes
    FIRST (the window's tick before the gate's), then the start, the commit (the window shut), the landing at the host's pose and the
    arm -- the ARMED line naming the landing, `arms` +1, mirroring, no no-autosave line; `pending` false throughout after the write."""
    root = _game(tmp_path)
    fake = _pfake(root)
    with _session(root, fake) as g:
        _pair_on_6603(g, fake)
        st = g.wait_for(lambda s: s.ui_state == "WorldHUD" and s.world_id == 9011, timeout=10, what="the pull")
        g.wait_frames(6)
        st = g.state
        lines = _pw_lines(fake)
        assert st.session_mirroring is True and st.world_pairpull_block == {"lever": "act", "pending": False, "arms": 1,
                                                                            "last_world": 9011}, st.world_pairpull_block
        idx = {k: next(i for i, ln in enumerate(lines) if k in ln) for k in ("pairing autosave written on field 6603",
                                                                             "follow-out: start", "follow-out: commit",
                                                                             "ARMED at world map 9011", "follow-out: landed")}
        assert idx["pairing autosave written on field 6603"] < idx["follow-out: start"] < idx["follow-out: commit"] \
            < idx["ARMED at world map 9011"] < idx["follow-out: landed"], lines
        assert sum("state-mirror ARMED" in ln for ln in lines) == 1 and not any("no pairing autosave" in ln for ln in lines)
        assert not fake._pw["open"]                                    # the commit shut it


def test_s166b_a_busy_guest_waits_as_pairing_save_then_writes_and_starts(tmp_path):
    """BUSY (menu control off: not free-standing) -- `pending` true, out.why 'pairing_save', no start, s144's own field line kept (the
    state 'waiting'); free again -> the write, then the start. The `pairpull_early` fault starts at once (the start before the write):
    the commit shuts the window with nothing written and the landing's arm says so ('no pairing autosave this session: the mirror
    armed at world map 9011's landing first')."""
    for fault in ((), ("pairpull_early",)):
        root = _game(tmp_path / ("early" if fault else "ok"))
        fake = _pfake(root, faults=fault)
        with _session(root, fake) as g:
            _pair_on_6603(g, fake, busy=True)
            g.wait_frames(int(1.6 * 600))                              # past THE LIVE DEBOUNCE (1.2 s of host-alive time)
            st = g.state
            if not fault:
                assert st.ui_state == "FieldHUD" and st.field_id == 6603 and st.world_pairpull_pending is True
                assert (st.netsync["world"]["out"]["why"], st.netsync["world"]["out"]["starts"]) == ("pairing_save", 0)
                fake.menu_control_enable = True
            st = g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the pull")
            fake.menu_control_enable = True
            g.wait_frames(6)
            lines = _pw_lines(fake)
            written = [i for i, ln in enumerate(lines) if "pairing autosave written on field 6603" in ln]
            start = next(i for i, ln in enumerate(lines) if "follow-out: start" in ln)
            none = [ln for ln in lines if "no pairing autosave this session" in ln]
            if fault:
                assert not written and none and "world map 9011's landing first" in none[0], lines
            else:
                assert written and written[0] < start and not none, lines
            assert g.state.session_mirroring is True and g.state.world_pairpull_block["arms"] == 1


@pytest.mark.parametrize("knob,verdict", [({"autosave_off": True}, BW.PAIR_AUTOSAVE_OFF),
                                          ({"entry_refused": True}, BW.PAIR_STOCK_REFUSED)])
def test_s166b_a_durable_decline_lets_the_pull_start_and_the_arm_names_it(tmp_path, knob, verdict):
    """A DURABLE decline (the window will never write here) -- its line once, `pending` false, the pull starts; the landing's arm says
    there was no pairing autosave, naming the landing and the decline."""
    root = _game(tmp_path)
    fake = _pfake(root, window=knob)
    with _session(root, fake) as g:
        _pair_on_6603(g, fake)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the pull")
        g.wait_frames(6)
        lines = _pw_lines(fake)
        decl = [ln for ln in lines if "pairing autosave declined at the pairing window on field 6603" in ln]
        none = [ln for ln in lines if "no pairing autosave this session" in ln]
        assert len(decl) == 1 and BW.pairing_save_reason(verdict) in decl[0], lines
        assert none and "world map 9011's landing first (declined at the pairing window on field 6603" in none[0], none
        assert not any("pairing autosave written" in ln for ln in lines) and g.state.session_mirroring is True


def test_s166b_a_bent_place_is_a_durable_decline_and_a_failed_write_waits(tmp_path):
    """NOT MY OWN PLACE: a committed netsync move's landing (BendColdEntry: the record bent) declines durably -- the pull starts. A
    FAILED write (one write per place, whatever the outcome) is NOT resolved: `pending` stays true (fail-closed, s165's wait) and the
    guest never starts."""
    root = _game(tmp_path / "bent")
    fake = _pfake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        fake._pw_commit()                                              # a move committed from here...
        g.warp(6603)                                                   # ...and its load landed: a bent entry
        fake.follow_session(0, flags=BW.HF_WORLD | BW.HF_CONTROL | BW.HF_MENU, fresh=True)
        fake.host_world_pose(1197.37, -796.7, idx=11)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the pull")
        assert any(BW.pairing_save_reason(BW.PAIR_NOT_OWN_PLACE) in ln for ln in _pw_lines(fake))
    root = _game(tmp_path / "failed")
    fake = _pfake(root, window={"write_fails": True})
    with _session(root, fake) as g:
        _pair_on_6603(g, fake)
        g.wait_frames(int(2.0 * 600))
        st = g.state
        assert st.ui_state == "FieldHUD" and st.world_pairpull_pending is True
        assert st.netsync["world"]["out"]["why"] == "pairing_save" and st.netsync["world"]["out"]["starts"] == 0
        assert any(BW.LOG_PAIRING_FAILED + "field 6603" in "[NetSync] " + ln for ln in _pw_lines(fake))


def test_s166b_the_a0_build_and_the_lever_keep_s165s_wait_and_arm_nothing(tmp_path):
    """OLD (the A0 build) and LEVER (`pairpull old`): the guest waits on 6603 with out.why 'not_mirroring' -- its pairing autosave
    written all the same (s154's window is every engine's) -- and nothing arms. The A0 build publishes no `pairpull` and the driver
    refuses the op before the step; the stand-in's own verb answers the A0 build's usage line."""
    for case in ("a0", "lever"):
        root = _game(tmp_path / case)
        fake = _pfake(root, pieces=FG.FAKE_WORLD_WALK_A0_BUILD if case == "a0" else None)
        with _session(root, fake) as g:
            g.newgame(settle=0)
            g.warp(6603)
            st = g.state
            if case == "a0":
                assert list(st.netsync["world"]) == list(BW.WORLD_SENTINELS_S166) and st.coop_world_pairpull is False
                with pytest.raises(HarnessError, match=r"publishes no `netsync\.world\.pairpull`"):
                    g.worldwalk("pairpull", "old")
                with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_USAGE_A0)):
                    fake._netsync(["worldwalk", "pairpull", "old"])
            else:
                fake.netsync.update(enabled=True, role="client", instance=True)
                g.worldwalk("pairpull", "old")
                assert g.state.world_pairpull_block["lever"] == "old" and BW.LOG_WORLDWALK_PAIRPULL_OLD in _log(fake)
            fake.follow_session(0, flags=BW.HF_WORLD | BW.HF_CONTROL | BW.HF_MENU, fresh=True)
            fake.host_world_pose(1197.37, -796.7, idx=11)
            g.wait_frames(int(2.0 * 600))
            st = g.state
            assert st.ui_state == "FieldHUD" and st.field_id == 6603 and st.session_mirroring is False
            assert st.netsync["world"]["out"]["why"] == "not_mirroring" and st.netsync["world"]["out"]["starts"] == 0
            lines = _pw_lines(fake)
            assert any("pairing autosave written on field 6603" in ln for ln in lines) and not any("ARMED" in ln for ln in lines)


def test_s166b_byte_identical_for_a_mirroring_guest_the_bench_a_host_and_an_unmodelled_window(tmp_path):
    """A MIRRORING guest: the s165 follow-out, no second ARMED line, `arms` +0. THE BENCH (the selftest role's fabricated host): exempt
    from term 3, never armed (`arms` 0, never mirroring). A HOST: the key at rest, nothing arms. The window UNMODELLED: read as
    resolved -- the pull starts with no write line."""
    root = _game(tmp_path / "mirror")
    fake = _pfake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        fake.follow_session(6603, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, story={1121: 0xA5}, pair_kick=True)
        g.wait_for(lambda s: s.session_mirroring is True, timeout=5, what="the kick's arm")
        fake.host_at(0, flags=BW.HF_WORLD | BW.HF_CONTROL | BW.HF_MENU)
        fake.host_world_pose(1197.37, -796.7, idx=11)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the s165 follow-out")
        g.wait_frames(6)
        lines = _pw_lines(fake)
        assert sum("state-mirror ARMED" in ln for ln in lines) == 1 and "ARMED --" in [ln for ln in lines if "ARMED" in ln][0]
        assert g.state.world_pairpull_block["arms"] == 0
    root = _game(tmp_path / "bench")
    fake = _pfake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        g.netsync("selftest", 1)
        g.netsync("bench", 1)
        g.worldfollow("host", 1197.37, -796.7)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the bench follow-out")
        g.wait_frames(6)
        st = g.state
        assert st.world_pairpull_block["arms"] == 0 and st.session_mirroring is False and "ARMED" not in _log(fake)
    root = _game(tmp_path / "host")
    fake = _pfake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        fake.netsync.update(enabled=True, role="host", instance=True)
        g.wait_frames(10)
        assert g.state.world_pairpull_block == dict(CONTRACT_PAIRPULL, lever="act")
    root = _game(tmp_path / "unmodelled")
    fake = _pfake(root, window=False)
    with _session(root, fake) as g:
        _pair_on_6603(g, fake)
        g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the pull")
        g.wait_frames(6)
        lines = _pw_lines(fake)
        assert not any("pairing autosave" in ln for ln in lines) and g.state.world_pairpull_block["arms"] == 1


def test_s166b_the_unarmed_fault_leaves_the_mirror_off_and_s164s_gate_open(tmp_path):
    """`pairpull_unarmed`: the landing arms nothing -- mirroring false, no ARMED line, `arms` +0 -- and under R4's DRY lever the pick is
    a would-save (s164's own gate, the mirror, would have let it through); on the shipping stand-in the ARMED guest's chord is refused
    ahead of the menu (BW.save_chord_refused: menu_refusal.now 'audible'), so R4 counts nothing at all."""
    for fault in ((), ("pairpull_unarmed",)):
        root = _game(tmp_path / ("unarmed" if fault else "armed"))
        fake = _pfake(root, faults=fault)
        with _session(root, fake) as g:
            _pair_on_6603(g, fake)
            g.wait_for(lambda s: s.ui_state == "WorldHUD", timeout=10, what="the pull")
            g.wait_frames(6)
            st = g.state
            assert st.session_mirroring is (not fault) and st.world_pairpull_block["arms"] == (0 if fault else 1)
            g.worldfollow("saveguard", "old")
            sg0 = dict(g.state.saveguard_block)
            assert (g.state.raw.get("netsync") or {}).get("menu_refusal", {}).get("now") == ("open" if fault else "audible")
            g.savemenu()
            g.wait_frames(6)
            sg1 = dict(g.state.saveguard_block)
            dr, dw = sg1["refused"] - sg0["refused"], sg1["would_save"] - sg0["would_save"]
            assert (dr, dw) == ((0, 1) if fault else (0, 0)), (fault, sg0, sg1)


def test_s166b_the_armed_guests_chord_is_refused_ahead_of_r4_on_the_stack():
    """[ff9mapkit netsync s166] S166-PR-SAVEMENU's derivation, pinned to the patch stack: `savemenu` (s165's HarnessSaveMenu) runs
    UIKeyTrigger.OnSaveLoadSceneCommandDetected, whose s38 gate buzzes on `!IsMenuControlEnable || IsMirroringStory` before any save
    menu opens -- so an ARMED guest's pick never reaches R4's counted Save sites. BW.save_chord_refused is that gate; if either line
    leaves the stack, the row's +0 / +0 must be re-derived."""
    added, removed = [], []
    for nm in msr.stack():
        if nm in msr.DEAD:
            continue
        for path, sec in msr.sections((msr.PATCHES / nm).read_bytes()):
            if path and path.replace("\\", "/").endswith("/UIKeyTrigger.cs"):
                body = sec.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
                added += [ln[1:] for ln in body if ln.startswith("+") and not ln.startswith("+++")]
                removed += [ln[1:] for ln in body if ln.startswith("-") and not ln.startswith("---")]
    gate = "if (!uiManager.IsMenuControlEnable || Memoria.Netsync.NetSyncClient.IsMirroringStory)"
    # s38 adds the gate TWICE -- the party chord and the save chord (OnSaveLoadSceneCommandDetected) -- and no later patch takes it out
    assert sum(ln.strip() == gate for ln in added) >= 2, "s38's chord gate is gone from the stack (one copy is the party menu's)"
    assert not any(ln.strip() == gate for ln in removed), "a later patch removes s38's chord gate"
    assert any(ln.strip() == "OnSaveLoadSceneCommandDetected(uiManager.GetSceneFromState(uiManager.State), SaveLoadUI.SerializeType.Save);"
               for ln in added), "s165's `savemenu` no longer runs the chord's own path"
    assert [BW.save_chord_refused(c, m) for c in (True, False) for m in (False, True)] == [False, True, True, True]


def test_s166b_the_coop_off_hand_over_rule_reads_the_reviews_fix():
    """[ff9mapkit netsync s166] A0b review R1's rule (LandWorldOut): the arm hands over the exit ramp only from inside its own arm, with co-op
    off and no ramp pending yet -- each input flipped alone turns it off."""
    rule = BW.coop_off_ramp_hands_over
    assert rule(True, False, False) is True
    assert not rule(False, False, False) and not rule(True, True, False) and not rule(True, False, True)
    assert BW.log_world_out_coop_off(9011) == ("[NetSync] world follow-out: co-op was turned off during it -- the exit ramp reloads your own "
                                               "autosave once you are free-standing on world map 9011")


def test_s166b_coop_off_inside_a_pulled_follow_out_hands_the_ramp_over_at_the_landing(tmp_path):
    """THE REVIEW'S R1 on the stand-in: co-op turned OFF inside a pulled guest's fade (an enabled=0 config, the role kept: ApplyConfigChange
    found no mirror to ramp out of). The fade finishes; the landing arms (its ARMED line, `arms` +1) and then hands over the exit ramp --
    its line after the ARMED line and before the landing's, `netsync.session.ramp_pending` true with cause 'config'. Co-op left on: the
    same pull hands nothing over (no line, no ramp)."""
    for off in (False, True):
        root = _game(tmp_path / ("off" if off else "on"))
        fake = _pfake(root)
        fake.world_out_fade_frames = 1200                      # a 2 s fade at 600 fps: room to turn co-op off inside it
        with _session(root, fake) as g:
            _pair_on_6603(g, fake)
            g.wait_for(lambda s: s.netsync["world"]["out"]["state"] == "fading", timeout=10, what="the pull's fade")
            if off:
                fake.apply_ini({"Enabled": "0", "Role": "client", "FollowHost": "1"})
            st = g.wait_for(lambda s: s.ui_state == "WorldHUD" and s.world_id == 9011, timeout=10, what="the landing")
            g.wait_frames(6)
            st = g.state
            lines = _pw_lines(fake)
            hand = [i for i, ln in enumerate(lines) if "co-op was turned off during it" in ln]
            armed = next(i for i, ln in enumerate(lines) if "ARMED at world map 9011's landing" in ln)
            landed = next(i for i, ln in enumerate(lines) if "follow-out: landed" in ln)
            assert st.session_mirroring is True and fake._wwk["pp_arms"] == 1
            if off:
                assert len(hand) == 1 and armed < hand[0] < landed, lines
                assert lines[hand[0]] == BW.log_world_out_coop_off(9011), lines[hand[0]]
                assert (st.session_ramp_pending, st.session_ramp_cause) == (True, "config")
            else:
                assert not hand and st.session_ramp_pending is False and st.session_ramp_cause in (None, ""), lines


def test_s166b_the_stand_in_publishes_pairpull_last_and_the_lever_releases(tmp_path):
    """The default stand-in: `netsync.world` = A0's nine then `pairpull` at its shape; `worldwalk pairpull old|act` on any role, the
    clear line A0b's, the release line once when it was set; a malformed `pairpull` refused before the step in the usage line."""
    root = _game(tmp_path)
    fake = _pfake(root)
    with _session(root, fake) as g:
        g.newgame(settle=0)
        g.warp(6603)
        st = g.state
        assert list(st.netsync["world"]) == list(FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldwalk"]) and st.coop_world_pairpull is True   # [s166] W2
        assert st.world_pairpull_block == dict(CONTRACT_PAIRPULL, lever="act")
        seq = g.state.seq
        for bad in (("pairpull",), ("pairpull", "maybe"), ("pairpull", "old", "1")):
            with pytest.raises(HarnessError, match=re.escape(BW.WORLDWALK_USAGE_A4)):   # [s166] W2 reconcile: the newest stand-in's line
                g.worldwalk(*bad)
        assert g.state.seq == seq
        fake.netsync.update(enabled=True, role="host", instance=True)
        g.worldwalk("pairpull", "old")
        assert g.state.world_pairpull_block["lever"] == "old" and BW.LOG_WORLDWALK_PAIRPULL_OLD in _log(fake)
        g.worldwalk("clear")
        assert g.state.world_pairpull_block["lever"] == "act" and BW.LOG_WORLDWALK_CLEAR in _log(fake)
        g.worldwalk("pairpull", "old")
        fake.netsync.update(enabled=False, role="selftest")
        g.netsync("selftest", 1)
        before = _log(fake).count(BW.LOG_WORLDWALK_RELEASED)
        g.netsync("selftest", 0)
        g.wait_frames(4)
        assert g.state.world_pairpull_block["lever"] == "act" and _log(fake).count(BW.LOG_WORLDWALK_RELEASED) == before + 1


# ------------------------------------------------------------------------------------------------ T2-A pair and D-PAIR on stubs
_PAIR_CHILD = r'''
import datetime as _dt, importlib.util, json, os, pathlib, struct, sys, tempfile, threading, time
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
for k in ("COOP_WW_LEG", "COOP_CALIBRATE", "COOP_TAPE", "COOP_WW_PAIR_FROM"):
    os.environ.pop(k, None)
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW
from harness import coop_peer as CP
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
ww = load("coop_world_walk")
wf, cw, pb, cb = ww.wf, ww.cw, ww.pb, ww.cb
SPEED = 8.0
FROM = 36.0                                                     # the synthetic tape: the tile stand from 33.4 s, live since 30.4 s
for k, v in dict(REFUSE_S=1.0, START_S=4.0, LEAVE_S=12.0, FIELD_S=10.0, HOME_S=10.0, DOT_S=2.0, STALE_S=0.6, PICK_S=0.3,
                 HOLD_SETTLE_S=0.3, TILE_SLACK_S=12.0, REJOIN_S=15.0, FO_S=12.0, DUO_HOME_S=12.0, REPLAY_SPEED=SPEED).items():
    setattr(wf, k, v)
for k, v in dict(FIELD_S=10.0, DIAL_S=8.0, REJOIN_S=12.0).items():
    setattr(cw, k, v)
for k, v in dict(PAIR_S=8.0, PAIR_OUT_S=12.0, PAIR_FROM_S=FROM).items():
    setattr(ww, k, v)
FAKES, SENT = [], []

def root():
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    sav = t / "x64" / "ff9harness" / "save"
    sav.mkdir(parents=True)
    (sav / "SavedData_ww.dat").write_bytes(bytes(64))
    return t

def fake_for(t, run):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    if run.get("caps"):
        f.netsync_caps = FG.caps_through(run["caps"])
    if run.get("a0"):
        f.world_walk_pieces = FG.FAKE_WORLD_WALK_A0_BUILD
    f.pairing_window = dict(FG.FAKE_PAIRING_WINDOW)
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(run.get("faults", ()))
    f.world_out_fade_frames = 600
    real_ns = f._netsync
    def ns(args, _real=real_ns):
        if args and str(args[0]).lower() in ("worldwalk", "worldfollow"):
            SENT.append(" ".join(str(a) for a in args))
        _real(args)
    f._netsync = ns
    FAKES.append(f)
    return f

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(rows):
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def write_tape(path, recs):
    head = json.dumps({"tool": "stub", "started": _dt.datetime.now().isoformat()}).encode("utf-8")
    body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + r.payload for r in recs)
    path.write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)

class StubIni:
    def __init__(self, ini, values, *, label, run_dir=None, backup_root=None):
        self.values = dict(values)
    def apply(self):
        FAKES[-1].apply_ini(self.values)
        return "the stub ini"
    def update(self, values):
        self.values.update(values)
        FAKES[-1].apply_ini(self.values)
        return "the stub ini updated"
    def restore(self):
        return True, "restored (stub)"

def feed_pose(f, payload):
    fp = CP.frame_pose(payload)
    p = fp.get("pose")
    if fp.get("b6") and p is not None and p.get("torus"):
        f.host_world_pose(p["x"], p["z"], idx=p["idx"], mode=p["mode"], entrance=p["entrance"], veg=p["choco"], yaw=p["yaw"],
                          story=p["story"])

class StubReplay(pb.PeerProc):
    """coop_peer replay-host's stand-in, honouring --from: it connects once the stand-in's transport exists, then replays the tape's
    host frames from that second (SPEED x) onto the followed client's seams. ``busy``: the guest's menu control off for that many wall
    seconds from the first frame (not free-standing: the window's write waits)."""
    busy = 0.0
    def _say(self, msg):
        n = _dt.datetime.now()
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[coop-peer {n:%H:%M:%S}.{n.microsecond // 1000:03d}] {msg}\n")
    def _arg(self, name):
        return self.args[self.args.index(name) + 1] if name in self.args else None
    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
    def _run(self):
        f = FAKES[-1]
        port, code = self._arg("--port"), self._arg("--code")
        frm = float(self._arg("--from")) if self._arg("--from") else None
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub replay-host")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not f.dial_socket:
            time.sleep(0.05)
        if self._halt.is_set() or not f.dial_socket:
            return
        self._say(f"GUEST game connected (session {code})")
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{port}/sess/{code}?role=guest")
        _h, recs, _torn = CP.read_tape(self.args[0])
        frames = [x for x in CP.host_frames(recs) if frm is None or x[0].t >= frm]
        t0 = frames[0][0].t if frm is None else frm
        _w = f.netsync_wire_now()   # [ff9mapkit netsync s166] what replay-host logs before REPLAY start (the stand-in's own wire)
        _send, _how = CP.replay_send_wire("auto", _w, CP.tape_wire(recs))
        self._say(CP.GUEST_WIRE_LINE.format(guest=_w, send=_send, how=_how))
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape {frames[-1][0].t:.2f} s")
        wall0, field, flags, story, first = time.time(), None, -1, None, True
        for r, w, p in frames:
            due = wall0 + (r.t - t0) / SPEED
            while time.time() < due and not self._halt.is_set():
                time.sleep(0.01)
            if self._halt.is_set():
                return
            fresh_pose = None
            if w == CP.TYPE_POS:
                d = CP.parse_pos_payload(p)
                if d and d["field"] != field:
                    self._say(f"tape {r.t:.2f}: host field {field if field is not None else 'none'} -> {d['field']}")
                    field = d["field"]
            elif w == CP.TYPE_STATE:
                sec = pb.state_sections(p)
                if 0 in sec:
                    story = bytes(sec[0])
                if 7 in sec:
                    v = BW.parse_dialog_section(sec[7])
                    flags = v["flags"] if v else flags
                fresh_pose = p
            if field is None:
                continue
            if first:
                if self.busy:
                    f.menu_control_enable = False
                    threading.Timer(self.busy, lambda: setattr(f, "menu_control_enable", True)).start()
                f.follow_session(field, flags=flags, fresh=True, story=story, pair_kick=True)
                first = False
            else:
                f.host_at(field, flags=flags, story=story)
            if fresh_pose is not None:
                feed_pose(f, fresh_pose)
    def alive(self):
        return getattr(self, "_t", None) is not None and self._t.is_alive()
    def stop(self, timeout=10.0):
        if getattr(self, "_t", None) is None:
            self.how_ended = "never started"
            return self.how_ended
        self._halt.set()
        self._t.join(5.0)
        self.how_ended = "stopped cleanly (code 0)"
        self.lines()
        return self.how_ended

def pair(run):
    t = root()
    pb.IniGuard = StubIni
    pb.port_free = lambda port, host="127.0.0.1": (True, "")
    StubReplay.busy = float(run.get("busy", 0.0))
    pb.PeerProc = StubReplay
    tape = t / "tape-host6603-world-walk-s164.f9tape"
    write_tape(tape, pb.synthetic_world_walk_tape(CP, tile_s=float(run.get("tile_s", 120.0))))
    os.environ["COOP_TAPE"] = str(tape)
    if run.get("from") is not None:
        ww.PAIR_FROM_S = float(run["from"])
    f = fake_for(t, run)
    cb.CALIBRATE = bool(run.get("cal"))
    ww._RAW_LEG = "pair"
    with session(t, f) as g:
        ww.run(g)
        out = rows_of([(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:900]) for r in g.checks])
    ww.PAIR_FROM_S = FROM
    out["sent"] = list(SENT)
    return out

class Link(threading.Thread):
    """The duo's stub TRANSPORT, born at the GUEST's apply_role: the host stand-in's place, section 7's flags, its story and its own
    world pose onto the guest's followed-client seams; its MAPJUMP intent."""
    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
    def run(self):
        h, g, sent, first = self.h, self.g, None, True
        while not self.halt.is_set():
            if first:
                g.follow_session(h.host_lane_field(), flags=h.host_dialog_flags(), fresh=True, story=bytes(h.story_bytes),
                                 pair_kick=True)
                first = False
            else:
                g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes))
            w = h.world
            if h.ui_state == "WorldHUD" and w.get("x") is not None and w.get("id"):
                g.host_world_pose(float(w["x"]), float(w["z"]), idx=int(w["id"]) - 9000, mode=int(w.get("vehicle") or 0))
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                g.host_intent(it[1])
            time.sleep(0.02)

class StubDuo:
    def __init__(self, host, guest, fh, fg_, paired=False):
        self.host, self.guest, self.strict, self.rows, self.notes, self.paired = host, guest, True, [], [], paired
        self.fh, self.fg, self.link = fh, fg_, None
    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:900]))
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)
    def apply_role(self, role, *, cid=None):
        if role == "host":
            self.fh.netsync.update(enabled=True, role="host", instance=True)
        else:
            self.fg.wf_follow_host_cfg = True
            self.link = Link(self.fh, self.fg)
            self.link.start()
        self.check(True, f"the {role} took its role", cid=cid)
        return ["stub"]

def duo(run):
    th, tg = root(), root()
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    fh.world_exit_frames = fgst.world_exit_frames = 240
    cb.CALIBRATE = bool(run.get("cal"))
    gh, gg = session(th, fh), session(tg, fgst)
    with gh, gg:
        d = StubDuo(gh, gg, fh, fgst, paired=bool(run.get("paired")))
        try:
            ww.run_duo(d)
        finally:
            if d.link is not None:
                d.link.halt.set()
        rows = [(c, ok, dd) for c, ok, dd in d.rows if c and not str(c).startswith("S166-D-PAIR-C2")]
        return dict(rows_of(rows), sent=list(SENT))

kinds = {"pair": pair, "duo": duo}
def one(run):
    SENT.clear()
    return kinds[run["kind"]](run)
results = {name: one(run) for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _pair_child(payload, *, timeout: float = 900.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _PAIR_CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _pair_run(kind: str = "pair", **run) -> dict:
    return _pair_child({"runs": {"r": dict(run, kind=kind)}})["r"]


_PAIR_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)
print(json.dumps({"t2": list(ww.t2_pair_catalog(False)), "t2_cal": list(ww.t2_pair_catalog(True)), "rows": list(ww.T2_PAIR_ROWS),
                  "old": list(ww.T2_PAIR_OLD_PREDICTED), "lever": {k: list(v) for k, v in ww.T2_PAIR_LEVER_PREDICTED.items()},
                  "faults": {k: list(v) for k, v in ww.T2_PAIR_FAULT_REDS.items()}, "duo": list(ww.DUO_PAIR_CHECKS),
                  "duo_old": list(ww.DUO_PAIR_OLD_PREDICTED), "solo_faults": {k: list(v) for k, v in ww.SOLO_FAULT_REDS.items()},
                  "consts": {"PAIR_LEG": ww.PAIR_LEG, "PAIR_PROBE": ww.PAIR_PROBE, "PAIR_FROM_S": ww.PAIR_FROM_S,
                             "PAIR_LEVER": ww.PAIR_LEVER, "PAIR_LIVE_S": ww.PAIR_LIVE_S, "PAIR_ROOM_S": ww.PAIR_ROOM_S},
                  "doc": " ".join((ww.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def pair_tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _PAIR_TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_s166b_the_pair_tables_are_the_docstring_and_each_others(pair_tables):
    """Every T2-A pair and D-PAIR row the docstring names; the predictions and fault rows real rows; the faults the stand-in's; the
    solo bench meets neither A0b fault; the constants (the --from second pinned at 45.0 with its evidence)."""
    t, doc = pair_tables, pair_tables["doc"]
    for cid in t["rows"] + t["duo"]:
        assert cid.replace("S166-", "") in doc, cid
    assert t["t2"][:2] == ["T2-TAPE", "T2-PEER"] and t["t2"][-2:] == ["T2-SAVE", "T2-INI"] and "S166-PR-CAL" in t["t2_cal"]
    assert set(t["old"]) < set(t["rows"]) and t["lever"] == {"pairpull": t["old"]}
    assert not set(t["old"]) & {"S166-PR-I", "S166-PR-SAVE"}                     # the s154 window writes on every engine
    assert set(t["faults"]) <= set(FG.WORLD_WALK_FAULTS) and all(set(v) <= set(t["rows"]) for v in t["faults"].values())
    assert set(t["duo_old"]) < set(t["duo"]) and t["solo_faults"]["pairpull_early"] == [] == t["solo_faults"]["pairpull_unarmed"]
    c = t["consts"]
    assert (c["PAIR_LEG"], c["PAIR_PROBE"], c["PAIR_FROM_S"], c["PAIR_LEVER"]) == ("pair", "netsync.world.pairpull", 45.0, "pairpull")
    assert c["PAIR_LIVE_S"] == BW.WORLD_OUT_DEBOUNCE_MS / 1000.0
    for word in ("45.0", "40.99", "36.95", "118.25", "118.71", "where --pose", "x64/ff9harness/save", "49201", "--no-pair"):
        assert word in doc, word


def test_s166b_the_pair_leg_is_green_on_a0b_and_reds_old_and_the_lever_exactly():
    """T2-A pair on the stub replay-host (the synthetic world-walk tape from its tile stand): green on the A0b stand-in -- the pairing
    autosave, the pull, the landing at the TAPE's pose, the arm, the DRY save refused by the mirror, the rejoin into 300 staging the
    host's story; on the A0 build (COOP_CALIBRATE) exactly T2_PAIR_OLD_PREDICTED red, the OLD wait MEASURED and NO `pairpull` sent;
    under `pairpull old` exactly the same."""
    runs = _pair_child({"runs": {"new": {"kind": "pair"}, "old": {"kind": "pair", "a0": True, "cal": True},
                                 "lever": {"kind": "pair", "cal": True}}})
    r = runs["new"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert not any("pairpull" in s for s in r["sent"]) and any("saveguard old" in s for s in r["sent"])
    want = {"S166-PR-OUT", "S166-PR-POSE", "S166-PR-ARM", "S166-PR-SAVEMENU", "S166-PR-REJOIN"}
    old = runs["old"]
    assert set(old["red"]) == want, {c: old["detail"][c] for c in set(old["red"]) ^ want}
    assert "MEASURED" in old["detail"]["S166-PR-CAL"] and not any("pairpull" in s for s in old["sent"])
    lev = runs["lever"]
    assert set(lev["red"]) == want, {c: lev["detail"][c] for c in set(lev["red"]) ^ want}
    assert "worldwalk pairpull old" in lev["sent"] and "worldwalk clear" in lev["sent"]


@pytest.mark.parametrize("fault", ["pairpull_early", "pairpull_unarmed", "chord_gate_open"])
def test_s166b_each_pairpull_fault_turns_exactly_its_pair_rows_red(pair_tables, fault):
    """A BUSY guest at the pairing (menu control off for 3 wall seconds: the window's write waits): green without a fault (the start
    waits for the write: `pairing_save`), and each fault red in exactly its T2_PAIR_FAULT_REDS rows."""
    want = set(pair_tables["faults"][fault])
    runs = _pair_child({"runs": {"control": {"kind": "pair", "busy": 3.0}, "fault": {"kind": "pair", "busy": 3.0, "faults": [fault]}}})
    assert runs["control"]["red"] == [], {c: runs["control"]["detail"][c] for c in runs["control"]["red"]}
    r = runs["fault"]
    assert set(r["red"]) == want, {c: r["detail"][c] for c in set(r["red"]) ^ want}


def test_s166b_the_calibration_and_the_tape_instrument_can_fail():
    """A check that cannot fail is not a check: the calibration on A0b under a lever the stand-in IGNORES (`pairpull_lever_ignored`: the
    guest is pulled out all the same) is red -- its predicted reds stayed green; a --from second inside the host's own load (it stands
    at the landing, its heartbeat frozen) is T2-TAPE red and runs nothing; the duo paired before its host stood on the world map (no
    --no-pair) reds every D-PAIR row."""
    runs = _pair_child({"runs": {"cal": {"kind": "pair", "cal": True, "faults": ["pairpull_lever_ignored"]},
                                 "early": {"kind": "pair", "from": 28.0},
                                 "paired": {"kind": "duo", "paired": True}}})
    cal = runs["cal"]
    assert "S166-PR-CAL" in cal["red"] and "stayed GREEN" in cal["detail"]["S166-PR-CAL"], cal["detail"].get("S166-PR-CAL")
    assert "T2-TAPE" in runs["early"]["red"] and all(c in runs["early"]["red"] for c in ("S166-PR-I", "S166-PR-OUT"))
    assert set(runs["paired"]["red"]) == set(_PAIR_DUO_ROWS) and "--no-pair" in runs["paired"]["detail"]["S166-D-PAIR-I"]


_PAIR_DUO_ROWS = ("S166-D-PAIR-I", "S166-D-PAIR-SAVE", "S166-D-PAIR-OUT", "S166-D-PAIR-ARM", "S166-D-PAIR-SAVEMENU", "S166-D-PAIR-REJOIN")


def test_s166b_d_pair_is_green_on_a0b_and_calibrates_on_the_a0_build():
    """D-PAIR on two stand-ins joined by a stub link born at the GUEST's apply_role (duo.py's own op): green on A0b; on the A0 build
    (COOP_CALIBRATE) exactly DUO_PAIR_OLD_PREDICTED red, D-PAIR-CAL green."""
    runs = _pair_child({"runs": {"new": {"kind": "duo"}, "old": {"kind": "duo", "a0": True, "cal": True}}})
    r = runs["new"]
    assert set(r["all"]) >= set(_PAIR_DUO_ROWS) and r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    old = runs["old"]
    want = {"S166-D-PAIR-OUT", "S166-D-PAIR-ARM", "S166-D-PAIR-SAVEMENU", "S166-D-PAIR-REJOIN"}
    assert set(old["red"]) == want, {c: old["detail"].get(c) for c in set(old["red"]) ^ want}
    assert "S166-D-PAIR-CAL" in old["all"]


# ------------------------------------------------------------------------------------------------ the pure judges, red on each shape
def _load_ww():
    import importlib.util
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_world_walk_pure", str(SCENARIOS / "coop_world_walk.py"))
    m = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return m


def test_s166b_the_pure_pair_judges_go_red_on_each_wrong_shape():
    from harness.channel import State
    ww = _load_ww()

    def st(ui="FieldHUD", field=6603, world=0, **ns):
        net = {"session": {"mirroring": ns.get("mirroring", False)},
               "world": {"host": {"b6": ns.get("b6", False)}, "out": {"why": ns.get("why"), "starts": 0, "commits": 0, "lands": 0},
                         "pairpull": dict(CONTRACT_PAIRPULL, lever=ns.get("lever", "act"), arms=ns.get("arms", 0),
                                          last_world=ns.get("last_world", -1))},
               "saveguard": {"refused": 0, "would_save": 0, "lever": "act", "last_why": None}}
        return State({"ui_state": ui, "field": {"id": field}, "world": {"id": world, "block_ready": ns.get("block", ui == "WorldHUD"),
                                                                   "ticks": ns.get("ticks", 0)},
                      "frame": ns.get("frame", 1), "netsync": net})

    def lg(msg):
        return f"02.11.2026 12:00:00 |M| {msg}"
    W, S = lg(BW.log_pairing_written("field 6603")), lg("[NetSync] world follow-out: start -- field 6603 follows ...")
    # SAVE: the write before the start; red when after it, absent, on another field, or beside a no-autosave line
    assert ww.judge_pair_autosave([W, S])[0]
    assert not ww.judge_pair_autosave([S, W])[0] and not ww.judge_pair_autosave([S])[0]
    assert not ww.judge_pair_autosave([lg(BW.log_pairing_written("field 250")), S])[0]
    assert not ww.judge_pair_autosave([W, S, lg(BW.log_no_pairing(BW.world_landing(9011)))])[0]
    # I: never mirrored, never kicked, never armed, b6 read; the lever word
    ok = [st(), st(b6=True)]
    assert ww.judge_pair_instrument(ok, [], lever_word="act", lever_read="act")[0]
    assert not ww.judge_pair_instrument([st(mirroring=True), st(b6=True)], [])[0]
    assert not ww.judge_pair_instrument([st(), st()], [])[0]                                      # b6 never read
    assert not ww.judge_pair_instrument(ok, [lg("[NetSync] paired on the host's field (6603) -- reloading it once so ...")])[0]
    assert not ww.judge_pair_instrument(ok, [lg(BW.LOG_MIRROR_ARMED_FIELD)])[0]
    assert not ww.judge_pair_instrument(ok, [], lever_word="old", lever_read="act")[0]
    assert not ww.judge_pair_instrument([st(ui="WorldHUD", field=0, world=9011, b6=True)], [])[0]
    # ARM: mirroring on every judged world sample, arms +1 on 9011, the world ARMED line once, no field form
    base = st(arms=0)
    wsamp = [st(ui="WorldHUD", field=6603, world=9011, mirroring=True, arms=1, last_world=9011, ticks=k, frame=k) for k in (5, 6, 7)]
    A = lg(BW.log_mirror_armed_world(9011))
    assert ww.judge_pair_arm(base, wsamp, [A])[0]
    assert not ww.judge_pair_arm(base, wsamp, [A, A])[0] and not ww.judge_pair_arm(base, wsamp, [])[0]
    assert not ww.judge_pair_arm(base, wsamp, [A, lg(BW.LOG_MIRROR_ARMED_FIELD)])[0]
    assert not ww.judge_pair_arm(base, wsamp, [lg(BW.log_mirror_armed_world(9010))])[0]
    unmir = [st(ui="WorldHUD", world=9011, mirroring=k != 6, arms=1, last_world=9011, ticks=k, frame=k) for k in (5, 6, 7)]
    assert not ww.judge_pair_arm(base, unmir, [A])[0]
    assert not ww.judge_pair_arm(base, [st(ui="WorldHUD", world=9011, mirroring=True, arms=0, ticks=k, frame=k) for k in (5, 6)],
                                 [A])[0]
    assert ww.judge_pair_arm(base, wsamp, [A, lg(BW.log_no_pairing(BW.world_landing(9011)))])[0]   # the no-autosave line: SAVE's
    assert not ww.judge_pair_arm(base, [st(ui="WorldHUD", world=9011, block=False, ticks=k) for k in (1, 2)], [A])[0]
    # SAVEMENU: the chord refused by the mirror -- no menu, +0 / +0, 'audible' and mirroring at the press; red on any count (an unarmed
    # guest's would-save, an R4 refusal: the pick reached SaveLoadUI), an opened menu, stock's own 'off', no mirror, a changed sandbox,
    # the HUD lost
    sg0, files = {"refused": 0, "would_save": 0, "last_why": None, "lever": "old"}, {"SavedData_ww.dat": (1, 64)}
    press = {"ui": "WorldHUD", "world": 9011, "now": "audible", "mirroring": True, "lever": "old"}

    def sm(sg1=sg0, f1=files, back=True, opened=False, froms=("WorldHUD",), **at):
        return ww.judge_pair_savemenu(sg0, sg1, files, f1, back, press={**press, **at}, opened=opened, froms=list(froms))[0]
    assert sm()
    assert not sm({"refused": 0, "would_save": 1, "last_why": "a live co-op session"}, opened=True)
    assert not sm({"refused": 1, "would_save": 0, "last_why": "mirroring the host's story"})      # chord_gate_open: R4 reached
    assert not sm(opened=True)
    assert not sm(now="off") and not sm(now="open") and not sm(now=None) and not sm(now="dialog")
    assert not sm(mirroring=False) and not sm(mirroring=None)
    assert not sm(ui="FieldHUD") and not sm(world=9010) and not sm(lever="act")
    assert not sm(froms=()) and not sm(froms=("FieldHUD",)) and not sm(froms=("WorldHUD", "WorldHUD"))   # the verb ran once, there
    assert not sm(f1={"SavedData_ww.dat": (2, 64)}) and not sm(back=False)
    assert not ww.judge_pair_savemenu(sg0, sg0, None, None, True, press=press, opened=False, froms=["WorldHUD"])[0]
    assert not ww.judge_pair_savemenu(sg0, {}, files, files, True, press=press, opened=False, froms=["WorldHUD"])[0]
    # the OLD wait: on 6603, why not_mirroring, no start line
    wait = [st(why="not_mirroring"), st(why="not_mirroring")]
    assert ww.pair_old_wait(wait, [W])[0]
    assert not ww.pair_old_wait(wait + [st(ui="WorldHUD", world=9011)], [W])[0] and not ww.pair_old_wait(wait, [W, S])[0]
    assert not ww.pair_old_wait([st(why="debounce")], [W])[0] and not ww.pair_old_wait([], [])[0]
    # REJOIN: red when the guest never stood on the world map, or a re-arm
    assert not ww.judge_pair_rejoin([st(field=300)], st(), [])[0]
    assert "not reached" in ww.judge_pair_rejoin([st(field=300)], st(), [])[1]
    # OUT: judge_leave's, and a 'not_mirroring' read after the autosave reds it
    assert not ww.judge_pair_out(base, [st()], [], after_autosave=[st(why="not_mirroring")])[0]


def test_s166b_the_from_facts_read_the_tape_and_can_fail():
    """pair_from_facts over the synthetic world-walk tape (the shapes the bench's own tape has): green at the tile stand past the
    debounce; red on the landing stand (the wrong pose), inside the host's load (a frozen heartbeat), on a riding host, with too little
    room left, past the tape's end, and on a tape with no field after the stand."""
    ww = _load_ww()
    from harness import coop_peer as CP
    pbm = ww.pb
    rows = CP.tape_poses(pbm.synthetic_world_walk_tape(CP))
    f = ww.pair_from_facts(rows, 36.0)
    assert f["ok"], f
    assert f["live_s"] >= ww.PAIR_LIVE_S and f["room_s"] >= ww.PAIR_ROOM_S and f["enter_t"] is not None
    assert "stands" in ww.pair_from_facts(rows, 31.5)["why"]                                       # the landing stand
    assert "lasts" in ww.pair_from_facts(rows, 90.0)["why"]                                        # too little room
    assert "no host state frame" in ww.pair_from_facts(rows, 999.0)["why"]
    ride = CP.tape_poses(pbm.synthetic_world_walk_tape(CP, mode=1))
    assert "[190] 1" in ww.pair_from_facts(ride, 36.0)["why"]
    # the heartbeat FROZEN through --from (the host's own load), then moving only 0.4 s before it (live too short)
    frozen = [dict(r, hb=7) if r.get("b6") and 33.3 <= r["t"] <= 36.2 else r for r in rows]
    assert "frozen" in ww.pair_from_facts(frozen, 36.0)["why"]
    short = [dict(r, hb=7) if r.get("b6") and r["t"] <= 35.55 else r for r in rows]
    s = ww.pair_from_facts(short, 36.0)
    assert not s["ok"] and "live on the world map" in s["why"] and s["live_s"] < ww.PAIR_LIVE_S, s
    noenter = [r for r in rows if not (r.get("field") and 0 < r["field"] < 65535 and r["t"] > 40.0)]
    assert "no real field" in ww.pair_from_facts(noenter, 36.0)["why"]


# ------------------------------------------------------------------------------------------------ the engine's source (skipped until it lands)
def test_s166b_the_catch_line_carries_pairpull_at_its_sentinel_after_kitcell():
    world = _s166_catch_world()
    if "pairpull" not in world:
        pytest.skip("this s166 source carries A0 alone (A0b not emitted yet)")
    keys = list(world)                                                  # [ff9mapkit netsync s166] W2: A3 / A4 may follow (by stage)
    assert keys[keys.index("dot"):keys.index("dot") + 3] == ["dot", "kitcell", "pairpull"], keys
    assert keys[keys.index("dot") + 1:] == list(BW.WORLD_S166_ROUND_A_KEYS[:len(keys) - keys.index("dot") - 1]), keys
    assert json.dumps(world["pairpull"]) == json.dumps(CONTRACT_PAIRPULL)


def test_s166b_the_engine_speaks_the_contracts_op_why_and_lines():
    follow = _s166_text("NetSyncWorldFollow.cs")
    if "pairing_save" not in follow:
        pytest.skip("this s166 source carries A0 alone (A0b not emitted yet)")
    m = re.search(r"WhyNames\s*=\s*\{(.*?)\};", follow, re.S)
    names = re.findall(r'"([a-z_]+)"', m.group(1)) if m else []
    assert names == list(BW.WORLD_OUT_WHYS_S166), names
    assert f'"{BW.WORDS_WORLD_OUT_PAIRING}"' in follow
    text = "\n".join(ln for name in ("HarnessAgent.cs", "NetSyncClient.cs") for ln in _s166_text(name).split("\n") if '"' in ln)
    usage, clear = _s166_verb_words()                   # [ff9mapkit netsync s166] W2 reconcile: by the source's stage
    for ln in (usage, BW.LOG_WORLDWALK_PAIRPULL_OLD, BW.LOG_WORLDWALK_PAIRPULL_ACT, clear):
        assert f'"{ln}"' in text, ln
    for piece in ('"[NetSync] state-mirror ARMED at "', '" -- this guest\'s fields now stage the HOST\'s story"', '"\'s landing"',
                  '"[NetSync] state-mirror ARMED -- this guest\'s fields now stage the HOST\'s story"', '\\"pairpull\\"'):
        assert piece in text or piece in _s166_text("HarnessAgent.cs"), piece
    # [ff9mapkit netsync s166] the review's R1 hand-over line, its two literals in the order the engine joins them (the world map last)
    client = _s166_text("NetSyncClient.cs")
    a, b = client.find(f'"{BW.LOG_WORLD_OUT_COOP_OFF}"'), client.find('"are free-standing on world map "')
    assert 0 <= a < b < a + 300, (a, b)
    assert BW.log_world_out_coop_off(9011) == BW.LOG_WORLD_OUT_COOP_OFF + "are free-standing on world map " + "9011"


def test_s166b_the_engines_pending_rule_and_verdicts_are_the_twins():
    """[ff9mapkit netsync s166] The twin IS the engine's: PairingSavePending's one expression (window open, nothing written, the verdict at or
    below busy), the s154 verdict and edge numbers, term 3's two branches in their order, and the call site's three facts."""
    follow = _s166_text("NetSyncWorldFollow.cs")
    if "PairingSavePending" not in follow:
        pytest.skip("this s166 source carries A0 alone (A0b not emitted yet)")
    m = re.search(r"Boolean PairingSavePending\(Boolean windowOpen, Boolean written, Int32 verdict\)\s*\{\s*return ([^;]*);", follow)
    assert m and re.sub(r"\s+", " ", m.group(1)) == "windowOpen && !written && verdict <= NetSyncClient.PairBusy", m and m.group(1)
    t3 = re.search(r"if \(!f\.PairPull\)\s*return WhyNotMirroring;\s*if \(f\.PairPending\)\s*return WhyPairingSave;", follow)
    assert t3, "term 3's two branches (old -> not_mirroring, then pending -> pairing_save)"
    client = _s166_text("NetSyncClient.cs")
    m = re.search(r"PairWrite = (\d+), PairNoWindow = (\d+), PairAlready = (\d+), PairBusy = (\d+), PairNotOwnPlace = (\d+), "
                  r"PairAutosaveOff = (\d+),\s*PairStockRefused = (\d+)", client)
    assert m and tuple(int(x) for x in m.groups()) == (BW.PAIR_WRITE, BW.PAIR_NO_WINDOW, BW.PAIR_ALREADY, BW.PAIR_BUSY,
                                                      BW.PAIR_NOT_OWN_PLACE, BW.PAIR_AUTOSAVE_OFF, BW.PAIR_STOCK_REFUSED)
    assert "f.PairPending = NetSyncWorldFollow.PairingSavePending(_pairWindowOpen, _pairWrittenWhere != null, _pairVerdict);" in client
    assert "f.PairPull = !_ppOld;" in client
    assert re.search(r'else if \(!_ppOld && _role == "client" && !_storyMirroring\)\s*\{', client), "the landing arm's guard"


# ================================================================================================ [ff9mapkit netsync s166] ROUND A, SOLO
# The round-A solo legs (coop_world_walk.py: tx, ghost, wrap, dot, body, stall) driven through the REAL Session on the stand-in (fakegame's
# `worldwalk` rung, pieces A3 + A4): green on the newest build; OLD on the deployed A0b build, the A3 build and s165 (exactly
# a_old_predicted red, no op of a missing piece ever sent); every lever exactly A_LEVER_PREDICTED red with its shape MEASURED; every
# `*_lever_ignored` fault reds the calibration; every round-A fault exactly its A_FAULT_REDS rows over all six legs in one launch.
_A_CHILD = r'''
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
from harness import Session
from harness import fakegame as FG
SRC_ROWS, SRC_MUTANTS = 308, 98

def clone_dir():
    """A stand-in s166 clone: NetSyncWorldWalk.cs carrying the tag and a proof table of SRC_ROWS rows and SRC_MUTANTS mutants -- the one
    source both the stand-in's proof line and the bench's A-PROOF want read (FF9_S166_CLONE)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="s166clone_")) / "Assembly-CSharp" / "Memoria" / "Netsync"
    d.mkdir(parents=True)
    rows = "\n".join("            row(r, \"x\");" for _ in range(SRC_ROWS))
    names = ", ".join(f"\"m{i}\"" for i in range(SRC_MUTANTS))
    (d / "NetSyncWorldWalk.cs").write_text("// [ff9mapkit netsync s166] stand-in\nprivate static Int32 Rows(Rules r, List<String> fails)\n{\n"
                                          + rows + "\n}\nprivate static Rules Mutant(String name) { }\n"
                                          "private static readonly String[] MutantNames = { " + names + " };\n", encoding="utf-8")
    return str(d.parents[1])

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
    if run.get("pieces"):
        f.world_walk_pieces = tuple(run["pieces"])
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(run.get("faults", ()))
    f.wf_follow_host_cfg = True
    f.world_kit = dict(FG.FAKE_WORLD_KIT)
    f.world_block_load_frames = int(run.get("block_frames", 6))   # a world load's Updates before w_blockReady: place 3 (A-TX)
    f.swap_qpc = None                                             # the swap clock on the virtual clock (the engine: one clock)
    real_ns = f._netsync
    def ns(args, _real=real_ns):
        if args and str(args[0]).lower() in ("worldwalk", "worldfollow"):
            SENT.append(" ".join(str(a) for a in args))
        _real(args)
    f._netsync = ns
    return f

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1400]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def solo(run):
    for k in ("COOP_WW_LEG", "COOP_WW_LEVER", "COOP_CALIBRATE", "FF9_S166_CLONE"):
        os.environ.pop(k, None)
    os.environ["COOP_WW_LEG"] = run.get("legs", "tx")
    if run.get("lever"):
        os.environ["COOP_WW_LEVER"] = run["lever"]
    if run.get("source", True):
        os.environ["FF9_S166_CLONE"] = clone_dir()
    ww = load("coop_world_walk")
    cw, wf, cb = ww.cw, ww.wf, ww.cb
    # the bench's own waits, shortened for a stand-in whose virtual clock runs ~10x the wall (every JUDGED threshold stays the bench's)
    # (the caps are generous: every round-A window ends on its own condition, so a loaded machine only waits longer -- never judges less)
    for k, v in dict(LEAVE_S=20.0, CONTROL_S=3.0, TX_S=0.6, GHOST_WALK_S=10.0, RULE_S=5.0, WRAP_S=0.5, DOTRIDE_S=8.0, DOT_BACK_S=4.0,
                     BODY_S=8.0, STALL_S=12.0, RESHOW_S=6.0, GAP_S=6.0, HANG_S=4.0, HANG_TAIL_S=0.1).items():
        setattr(ww, k, v)
    for k, v in dict(HOME_S=10.0, LEAVE_S=12.0, START_S=4.0, DOT_S=2.0).items():
        setattr(wf, k, v)
    cw.read_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    t = root("[Netsync]\nEnabled = 0\nFollowHost = 1\n")
    f = fake_for(t, run, cw)
    cb.CALIBRATE = bool(run.get("cal"))
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    with g:
        ww.run(g)
        out = rows_of(list(g.checks))
    out["sent"] = list(SENT)
    return out

results = {name: (SENT.clear(), solo(run))[1] for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _a_child(payload, *, timeout: float = 900.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_") and k != S166_CLONE_ENV}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _A_CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _a_run(**run) -> dict:
    return _a_child({"runs": {"r": run}})["r"]


_A_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)
print(json.dumps({
    "legs": list(ww.A_LEGS), "rows": {k: list(v) for k, v in ww.A_LEG_ROWS.items()}, "needs": {k: list(v) for k, v in ww.A_ROW_NEEDS.items()},
    "levers": {k: list(v) for k, v in ww.A_LEVERS.items()}, "ops": {k: list(v) for k, v in ww.A_LEVER_OPS.items()},
    "predicted": [[leg, lever, list(rows)] for (leg, lever), rows in ww.A_LEVER_PREDICTED.items()], "measure": dict(ww.A_MEASURE),
    "faults": {f: {leg: list(rows) for leg, rows in by.items()} for f, by in ww.A_FAULT_REDS.items()},
    "quiet": list(ww.A_QUIET_LEGS), "all_rows": list(ww.A_ALL_ROWS), "catalog": list(ww.a_catalog(False)),
    "cal": list(ww.a_catalog(True, ("stall",), "lanegap")), "setup": list(ww.A_SETUP), "final": list(ww.A_FINAL),
    "a0_legs": list(ww.LEGS), "doc": " ".join((ww.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def a_tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _A_TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _a_union(a_tables, fault) -> list:
    return sorted({r for rows in a_tables["faults"].get(fault, {}).values() for r in rows})


def test_s166a_the_round_a_tables_are_the_docstring_and_each_others(a_tables):
    """The legs, rows, levers, predictions, measures and fault rows agree with each other, the design's Round A rows (every solo row:
    A-PROOF .. A-FROZEN, A-MENU named stand-in-only) and the docstring; A0's legs are untouched."""
    t = a_tables
    assert t["a0_legs"] == ["kitoff", "ferryoff"] and t["legs"] == ["tx", "ghost", "wrap", "dot", "body", "stall"]
    rows = [r for leg in t["legs"] for r in t["rows"][leg]]
    assert len(rows) == len(set(rows)) and set(rows) | {"S166-A-PROOF"} == set(t["needs"])
    assert t["catalog"] == t["setup"] + ["S166-A-P1"] + rows + t["final"] and t["cal"][-1] == "S166-A-CAL"
    for name in ("A-PROOF", "A-TX", "A-GHOST", "A-WRAP", "A-STALL", "A-HANG", "A-DOTRIDE", "A-RULE", "A-BODY", "A-MENU", "A-FROZEN"):
        assert name in t["doc"], name                                  # the design's solo rows, each named (A-MENU: stand-in only)
    assert "NOT DRIVABLE in game" in t["doc"] and "not reachable solo" in t["doc"]
    assert t["quiet"] == ["ghost", "wrap", "dot", "body"] and "lanegap off` + `hostlines off`" in t["doc"]
    for leg, lever, pred in t["predicted"]:
        assert lever in t["levers"][leg] and set(pred) <= set(t["rows"][leg]) and all(r in t["measure"] for r in pred), (leg, lever)
    assert {(leg, lever) for leg, lever, _p in t["predicted"]} == {(leg, lv) for leg, lvs in t["levers"].items() for lv in lvs}
    assert t["levers"]["body"] == [] and set(t["ops"]) == {lv for lvs in t["levers"].values() for lv in lvs} - {"worldfreeze"}
    known = set(FG.WORLD_WALK_A_FAULTS) | set(FG.WORLD_WALK_FAULTS)
    for fault, by in t["faults"].items():
        assert fault in known, fault
        for leg, rr in by.items():
            assert leg in t["legs"] and set(rr) <= set(t["rows"][leg]) | {"S166-P0", "S166-A-PROOF"}, (fault, leg)
    # every round-A row can be turned red offline by some fault or lever (A-FROZEN by its lever; A-RULE by `ghost off`)
    reddened = {r for by in t["faults"].values() for rr in by.values() for r in rr} | {r for _l, _v, p in t["predicted"] for r in p}
    assert set(rows) <= reddened, set(rows) - reddened


def test_s166a_every_round_a_leg_is_green_on_the_newest_stand_in_in_one_launch():
    r = _a_run(legs="a")
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    for row in ("S166-A-TX", "S166-A-FROZEN", "S166-A-GHOST", "S166-A-RULE", "S166-A-WRAP", "S166-A-DOTRIDE", "S166-A-BODY", "S166-A-STALL",
                "S166-A-HANG", "S166-A-HANG-CTL", "S166-A-PROOF", "S166-A-P1", "S166-A-R"):
        assert row in r["all"], row
    assert "(308, 98)" in r["detail"]["S166-A-PROOF"] and "the x seam crossed while shown: yes" in r["detail"]["S166-A-GHOST"]
    assert any(s.startswith("worldwalk host path 1480") for s in r["sent"]) and "worldwalk lanegap off" in r["sent"]


@pytest.mark.parametrize("leg", ["tx", "ghost", "wrap", "dot", "body", "stall"])
def test_s166a_old_on_the_deployed_a0b_build_is_exactly_its_absent_rows_and_sends_nothing_new(a_tables, leg):
    """OLD (the deployed A0b 9e4365349fab02b1: no `netsync.world.lane` / `ghost`): the leg's rows (A-FROZEN excepted), A-PROOF and A-P1
    red, the calibration green, and no worldwalk op of A3 / A4 ever sent."""
    r = _a_run(legs=leg, cal=True, pieces=list(FG.FAKE_WORLD_WALK_A0B_BUILD))
    want = sorted([x for x in a_tables["rows"][leg] if x != "S166-A-FROZEN"] + ["S166-A-PROOF", "S166-A-P1"])
    assert r["red"] == want, (r["red"], r["detail"].get("S166-A-CAL"))
    assert not [s for s in r["sent"] if s.startswith("worldwalk") and s.split()[1] not in ("kitcell", "pairpull", "clear")], r["sent"]
    assert all("absent" in r["detail"][x] or "not reached" in r["detail"][x] for x in want if x != "S166-A-P1"), r["detail"]


def test_s166a_old_on_s165_reds_p0_too_and_on_the_a3_build_only_a4s_rows():
    rs = _a_child({"runs": {"s165": dict(legs="tx", cal=True, caps="worldfollow"),
                            "a3_stall": dict(legs="stall", cal=True, pieces=list(FG.FAKE_WORLD_WALK_A3_BUILD)),
                            "a3_body": dict(legs="body", cal=True, pieces=list(FG.FAKE_WORLD_WALK_A3_BUILD))}})
    assert rs["s165"]["red"] == ["S166-A-P1", "S166-A-PROOF", "S166-A-TX", "S166-P0"], rs["s165"]["detail"].get("S166-A-CAL")
    # the A3 build: A-STALL needs the ghost (OLD), A-HANG / its controls run (no lever pulled on a partial stage: A0's law)
    assert rs["a3_stall"]["red"] == ["S166-A-PROOF", "S166-A-STALL"], rs["a3_stall"]["detail"].get("S166-A-CAL")
    assert rs["a3_body"]["red"] == ["S166-A-BODY", "S166-A-P1", "S166-A-PROOF"], rs["a3_body"]["detail"].get("S166-A-CAL")
    assert not any(s.split()[1] in ("ghost", "place", "dot") for s in rs["a3_body"]["sent"] + rs["a3_stall"]["sent"]
                   if s.startswith("worldwalk"))


@pytest.mark.parametrize("leg, lever", [("tx", "pose"), ("tx", "worldfreeze"), ("ghost", None), ("wrap", None), ("dot", None),
                                        ("stall", None), ("body", None)])
def test_s166a_each_lever_calibrates_exactly_and_measures_its_shape(a_tables, leg, lever):
    """LEVER_PREDICTED on the newest stand-in: exactly A_LEVER_PREDICTED[(leg, lever)] red (unset = the leg's first; A-BODY has none:
    nothing red), each row's lever shape MEASURED, the calibration green."""
    r = _a_run(legs=leg, cal=True, **({"lever": lever} if lever else {}))
    lv = lever or (a_tables["levers"][leg] or [None])[0]
    want = sorted(next((p for lg, v, p in a_tables["predicted"] if lg == leg and v == lv), []))
    assert r["red"] == want, (r["red"], r["detail"].get("S166-A-CAL"))
    assert "rows whose lever shape was NOT measured: none" in r["detail"]["S166-A-CAL"]


@pytest.mark.parametrize("leg, fault", [("tx", "pose_lever_ignored"), ("ghost", "ghost_lever_ignored"), ("wrap", "place_lever_ignored"),
                                        ("dot", "dot_src_lever_ignored"), ("stall", "lanegap_lever_ignored")])
def test_s166a_a_lever_the_engine_ignores_reds_the_calibration_alone(leg, fault):
    r = _a_run(legs=leg, cal=True, faults=[fault])
    assert r["red"] == ["S166-A-CAL"], r["red"]
    assert "predicted reds that stayed GREEN: ['S166-A-" in r["detail"]["S166-A-CAL"]


def test_s166a_a_calibration_names_one_leg_and_its_own_lever_and_never_mixes_families():
    rs = _a_child({"runs": {"two": dict(legs="tx,ghost", cal=True), "foreign": dict(legs="tx", cal=True, lever="ghost"),
                            "mixed": dict(legs="kitoff,tx")}})
    assert "EACH LEG NEEDS ITS OWN LAUNCH" in rs["two"]["detail"]["S166-A-CAL"] and rs["two"]["sent"] == []
    assert "is not leg 'tx''s" in rs["foreign"]["detail"]["S166-A-CAL"] and rs["foreign"]["sent"] == []
    assert "one family per launch" in rs["mixed"]["detail"]["S166-INI"] and rs["mixed"]["sent"] == []


@pytest.mark.parametrize("fault", sorted(set(FG.WORLD_WALK_A_FAULTS) | {"walk_proof_fail"}))
def test_s166a_each_round_a_fault_turns_exactly_its_rows_red_over_all_six_legs(a_tables, fault):
    r = _a_run(legs="a", faults=[fault])
    assert r["red"] == _a_union(a_tables, fault), {c: r["detail"].get(c, "")[:400] for c in set(r["red"]) ^ set(_a_union(a_tables, fault))}


def test_s166a_without_an_s166_source_a_proof_wants_more_than_a0bs_and_the_a0b_tallies_are_red():
    """A-PROOF's instrument can fail: no s166 source reachable -> the stand-in prints A0b's 84 / 13 (no tables of round A) -> red; P0
    (any OK line) stays green."""
    r = _a_run(legs="tx", source=False)
    assert r["red"] == ["S166-A-PROOF"] and "above A0b's (84, 13)" in r["detail"]["S166-A-PROOF"], r["detail"]["S166-A-PROOF"]


def test_s166a_a_tx_is_red_without_place_3_in_the_load():
    """A-TX's load clause can fail: a world load with no Update before w_blockReady (no block window) publishes no place 3."""
    r = _a_run(legs="tx", block_frames=0)
    assert r["red"] == ["S166-A-TX"] and "want 3 among them: NO" in r["detail"]["S166-A-TX"]


def _a_ww():
    return _load_ww()


def test_s166a_a_menu_the_hold_keeps_b6_clear_and_control_off_sets_it_on_the_stand_in(tmp_path):
    """A-MENU (stand-in only: no harness verb opens the ~ menu in game): through a 1 s "Disable control" hold the trailer's b6 stays clear
    while control is off; a 1 s `control 0` sets it. The `scene_menu_hold` fault (the hold counted) is red; a window without the hold
    (control on) fails the instrument."""
    ww = _a_ww()

    def run(faults=(), hold=True):
        root = _game(tmp_path / ("m" + "_".join(faults) + str(hold)))
        fake = _fake(root, faults=faults)
        with _session(root, fake) as g:
            _on_world(g, fake, *FS_LANDING)
            g.wait_frames(20)
            if hold:
                fake.debug_menu_hold(True)
            hs = []
            for _ in range(24):
                g.wait_frames(3)
                hs.append(g.state)
            fake.debug_menu_hold(False)
            g.wait_frames(10)
            g.control(False)
            cs = []
            for _ in range(24):
                g.wait_frames(3)
                cs.append(g.state)
            g.control(True)
            return ww.judge_menu(hs, cs)
    ok, why = run()
    assert ok, why
    ok, why = run(faults=("scene_menu_hold",))
    assert not ok and "b6 set on [" in why, why
    ok, why = run(hold=False)
    assert not ok and "control on [" in why, why


_S = type("S", (), {})


def _smp(frame, *, ui="WorldHUD", world=9011, x=68.0, z=-444.0, lane=None, ghost=None, line=None, dot=None, control=True, br=True,
         ticks=None):
    s = _S()
    s.frame, s.ui_state, s.world_id, s.control, s.vehicle = frame, ui, world, control, 0
    blocks = {"kitcell": {}}
    blocks.update({k: v for k, v in (("lane", lane), ("ghost", ghost), ("line", line), ("dot", dot)) if v is not None})
    s.raw = {"world": {"x": x, "z": z, "block_ready": br, "ticks": frame if ticks is None else ticks}, "netsync": {"world": blocks}}
    return s


def test_s166a_the_pure_round_a_judges_go_red_on_each_wrong_shape():
    ww = _a_ww()
    # A-PROOF
    lines = [f"[NetSync] {BW.PROOF_WORLD_WALK}OK (308 rows, 98 mutants)"]
    st = _smp(1, lane={"tx": {}}, ghost={"want": False})
    assert ww.judge_a_proof(st, lines, (308, 98))[0] and not ww.judge_a_proof(st, lines, (309, 98))[0]
    assert not ww.judge_a_proof(st, [f"[NetSync] {BW.PROOF_WORLD_WALK}OK (84 rows, 13 mutants)"], None)[0]
    assert not ww.judge_a_proof(st, lines + [f"[NetSync] {BW.PROOF_WORLD_WALK}FAIL x"], (308, 98))[0]
    assert not ww.judge_a_proof(_smp(1), lines, (308, 98))[0]                       # no lane / ghost: absent
    # A-TX
    tx = {"place": 4, "world": 9011, "x": 68.2, "z": -444.1, "field": 0, "kind": "fmt1", "len": 94}
    land = [_smp(0, lane={"tx": dict(tx, place=p)}) for p in (1, 2, 3)]
    good = [_smp(i, lane={"tx": dict(tx, seq=100 + i)}) for i in range(1, 12)]
    assert ww.judge_tx(land, good)[0]
    assert not ww.judge_tx(land[:2], good)[0]                                         # no place 3 in the load
    assert not ww.judge_tx(land, [_smp(i, lane={"tx": dict(tx, seq=100 + i, field=9011)}) for i in range(1, 12)])[0]
    assert not ww.judge_tx(land, [_smp(i, lane={"tx": dict(tx, seq=100)}) for i in range(1, 12)])[0]      # the seq stands
    assert not ww.judge_tx(land, [_smp(i, lane={"tx": dict(tx, seq=100 + i, x=70.5)}) for i in range(1, 12)])[0]
    assert not ww.judge_tx(land, good[:3])[0]                                         # too few judged samples
    # the lane's own words, read back off the engine's texts
    for line in range(1, 10):
        text = BW.ww_lane_line_text(line, 1234)
        got = ww.lane_lines([f"03.11.2026 12:00:00 |M| [NetSync] selftest {text} [stamp 9 ms]"])
        if line in (BW.WW_LINE_STALL_BUDGET, BW.WW_LINE_LOAD_BUDGET):
            assert got == [], (line, got)
            continue
        assert got and got[0][1] == BW.WW_LANE_LINE_NAMES[line] and got[0][2] == 1234, (line, got)
    # A-HANG / its controls
    say = lambda line, n=1100: f"[NetSync] selftest {BW.ww_lane_line_text(line, n)}"                       # noqa: E731
    open_s = [_smp(1, lane={"open": "hang_loading"})]
    assert ww.judge_hang([say(BW.WW_LINE_LOAD_START)], open_s)[0]
    ok, why = ww.judge_hang([say(BW.WW_LINE_HANG_START)], [_smp(1, lane={"open": "hang"})])
    assert not ok and "worded not updating" in why
    ok, why = ww.judge_hang([say(BW.WW_LINE_LOAD_START), say(BW.WW_LINE_GAP_START)], open_s)
    assert not ok and "a gap line" in why
    assert ww.judge_hang_ctl([say(BW.WW_LINE_HANG_CUT), say(BW.WW_LINE_GAP_START)], [say(BW.WW_LINE_HANG_START)],
                             [_smp(1, lane={"open": "hang"})])[0]
    assert not ww.judge_hang_ctl([say(BW.WW_LINE_HANG_END), say(BW.WW_LINE_GAP_START)], [say(BW.WW_LINE_HANG_START)],
                                 [_smp(1, lane={"open": "hang"})])[0]                   # the hang_cut_as_update shape
    # A-WRAP
    g0 = {"placed": True, "x": 40.0, "z": -20.0, "inv_x": 40.0, "inv_z": -20.0, "rx": 808.0, "rz": -660.0, "oracle_x": 808.0,
          "oracle_z": -660.0}
    seg = lambda gh, f0=0: ((100.0, -100.0), f0, [_smp(f0 + i, x=100.0, z=-100.0, ghost=gh) for i in range(1, 9)])   # noqa: E731
    assert ww.judge_wrap([seg(g0)])[0]
    ok, _why, bad = ww.judge_wrap([seg(dict(g0, inv_x=104.0))])
    assert not ok and ww.wrap_lever_measured(bad)                                     # off-inverse, all inside the wrap window
    assert not ww.wrap_lever_measured([(500, 400, 64.0)])                             # an off frame far from any wrap: not the lever's
    assert not ww.judge_wrap([seg(dict(g0, oracle_x=744.0))])[0]                      # the oracle off the render placement
    assert ww.judge_wrap([seg(dict(g0, inv_x=1576.0 - 1536.0 + 1536.0))])[0]          # the same point the other side of the seam
    assert not ww.judge_wrap([((100.0, -100.0), 0, [_smp(1, ghost=g0)])])[0]          # a thin stand
    # A-RULE: a refusal that never undoes, a refusal that never reached the wire
    ref = _smp(1, ghost={"why_not": "riding", "want": False, "shown": False}, lane={"rx": {"mode": 1}})
    back = _smp(2, ghost={"shown": True, "why_not": None})
    assert ww.judge_rule([("riding", ref, ("mode", 1), back)])[0]
    assert not ww.judge_rule([("riding", ref, ("mode", 1), None)])[0]
    assert not ww.judge_rule([("riding", ref, ("mode", 0), back)])[0]
    # A-DOTRIDE: the dot parked on section 0 while the trailer moves (decision 12's OLD)
    park = ww.DOT_PARK
    ride_ok, ride_old = [], []
    for i in range(12):
        bx = 1150.0 + 8.0 * i
        mp = 0
        sx, sy = BW.navi_get_pos(bx, -760.0, mp)
        face = BW.ww_walker_yaw(100.0, 0.0)
        ride_ok.append(_smp(i, lane={"bench": {"x": bx, "z": -760.0, "walking": True}},
                            dot={"want": True, "src": "trailer", "src_x": bx, "src_z": -760.0, "src_face": face, "sx": sx, "sy": sy,
                                 "rot": BW.ww_dot_rotation_of_yaw(face), "mapno": mp, "host_x": park[0], "host_z": park[1]}))
        px, py = BW.navi_get_pos(*park, mp)
        ride_old.append(_smp(i, lane={"bench": {"x": bx, "z": -760.0, "walking": True}},
                             dot={"want": True, "src": "section0", "src_x": park[0], "src_z": park[1], "src_face": 0.0, "sx": px,
                                  "sy": py, "rot": -90.0, "mapno": mp, "host_x": park[0], "host_z": park[1]}))
    back = [_smp(20, dot={"src": "section0", "src_x": park[0], "src_z": park[1]})]
    assert ww.judge_dotride(ride_ok, back)[0]
    assert not ww.judge_dotride(ride_old, back)[0] and ww.dot_lever_measured(ride_old) and not ww.dot_lever_measured(ride_ok)
    assert not ww.judge_dotride(ride_ok, [_smp(20, dot={"src": "trailer", "src_x": 1200.0, "src_z": -760.0})])[0]   # never back
    # A-BODY: a Zidane on 9002, a mint on the field between
    def body(world, model, mints, geo):
        return _smp(1, world=world, ghost={"shown": True, "model": model, "geo": geo, "renderers": 3, "clips": 24,
                                           "stand": BW.ww_stand_clip_of(geo), "mint_ms": 12, "mints": mints})
    fld = lambda m: _smp(0, ui="FieldHUD", ghost={"mints": m})                                  # noqa: E731
    v_ok = [(9002, fld(0), body(9002, 309, 1, "GEO_SUB_W0_002"), body(9002, 309, 3, "GEO_SUB_W0_002")),
            (9010, fld(3), body(9010, 310, 4, "GEO_SUB_W0_001"), body(9010, 310, 4, "GEO_SUB_W0_001"))]
    off = {"base": body(9002, 309, 1, "GEO_SUB_W0_002"), "at": body(9002, 310, 2, "GEO_SUB_W0_001"),
           "back": body(9002, 309, 3, "GEO_SUB_W0_002")}
    assert ww.judge_body(v_ok, off)[0]
    assert not ww.judge_body([(9002, fld(0), body(9002, 310, 1, "GEO_SUB_W0_001"), None)], off)[0]
    assert not ww.judge_body([v_ok[0], (9010, fld(4), body(9010, 310, 5, "GEO_SUB_W0_001"), None)], off)[0]   # a mint on the field
    assert not ww.judge_body(v_ok, None)[0]                                           # the off-diagonal never ran
    # A-STALL's gap half: two gap pairs, a hide in the gap
    gl = [say(BW.WW_LINE_GAP_START, 1000), say(BW.WW_LINE_GAP_END, 1510)]
    gb = _smp(0, lane={"gaps": 3, "gaps_250": 5}, ghost={"hides": 1})
    gs = [_smp(i, lane={"gaps": 4, "gaps_250": 6}, ghost={"shown": True, "hides": 1, "stall": "stand" if i > 3 else "move"})
          for i in range(1, 9)]
    assert ww.judge_gap(gb, gs, gl)[0]
    assert not ww.judge_gap(gb, gs, gl + gl)[0]
    assert not ww.judge_gap(gb, gs[:-1] + [_smp(9, lane={"gaps": 4, "gaps_250": 6}, ghost={"shown": False, "hides": 2})], gl)[0]
    assert not ww.judge_gap(gb, gs, [say(BW.WW_LINE_GAP_START, 1000), say(BW.WW_LINE_GAP_END, 2400)])[0]   # the wrong length
    # the calibration: a lever whose shape was never measured is red even with the predicted reds
    assert not ww.judge_a_cal({"S166-A-TX"}, {"S166-A-TX"}, {}, ("S166-A-TX",))[0]
    assert ww.judge_a_cal({"S166-A-TX"}, {"S166-A-TX"}, {"S166-A-TX": True}, ("S166-A-TX",))[0]


def test_s166a_the_session_refuses_round_as_ops_before_the_step_on_an_engine_without_their_keys(tmp_path):
    """The driver's gate (THE CATCH IS THE KEY): `pose` / `lanegap` / `hostlines` / the bench host's ops need `netsync.world.lane` (A3),
    `ghost` / `place` / `dot` need `netsync.world.ghost` (A4) -- refused before the step on an older build; a malformed A3 / A4 op is A3's
    usage line; on the newest stand-in each reaches the engine. [ff9mapkit netsync s166] W2 reconcile: a malformed op is refused in the
    usage line THAT build answers (A0b's, A3's, A4's grown one)."""
    for pieces, refused, passed, usage in ((FG.FAKE_WORLD_WALK_A0B_BUILD, ("pose", "host", "ghost"), (), BW.WORLDWALK_USAGE),
                                           (FG.FAKE_WORLD_WALK_A3_BUILD, ("ghost", "place", "dot"), ("pose",), BW.WORLDWALK_USAGE_A3),
                                           (FG.FAKE_WORLD_WALK_PIECES, (), ("pose", "ghost", "place", "dot"), BW.WORLDWALK_USAGE_A4)):
        root = _game(tmp_path / "-".join(pieces))
        fake = _fake(root)
        fake.world_walk_pieces = tuple(pieces)
        with _session(root, fake) as g:
            g.newgame(settle=0)
            g.warp(6603)
            g.netsync("selftest", 1)
            args = {"pose": ("pose", "off"), "host": ("host", "path", "10", "-10", "24"), "ghost": ("ghost", "off"),
                    "place": ("place", "render"), "dot": ("dot", "section0")}
            for op in refused:
                n = len(fake.executed)
                with pytest.raises(HarnessError, match="this engine publishes no `netsync.world." + ("ghost" if op in (
                        "ghost", "place", "dot") else "lane")):
                    g.worldwalk(*args[op])
                assert len(fake.executed) == n, op                                     # never sent
            for op in passed:
                g.worldwalk(*args[op])
            with pytest.raises(HarnessError, match=re.escape(usage)):
                g.worldwalk("pose", "maybe")
            with pytest.raises(HarnessError, match=re.escape(usage)):
                g.worldwalk("ghost", "maybe")


# ---- the engine's keys the solo rows judge, read off the s166 source by stage (skips on the deployed A0b: no patch on the stack)
A_GHOST_KEYS = ("want", "why_not", "shown", "placed", "model", "geo", "renderers", "clips", "stand", "mints", "mint_ms", "clip", "anim",
                "stall", "seq_age_ms", "x", "z", "rx", "rz", "inv_x", "inv_z", "oracle_x", "oracle_z", "snaps", "holds", "hides", "lever",
                "place")
A_LANE_KEYS = ("lever", "pose", "hostlines", "tx", "rx", "seq_age_ms", "open", "gaps", "hangs", "gaps_250", "last_line", "bench")
A_LANE_SUB_KEYS = {"tx": ("seq", "place", "world", "x", "z", "field", "len", "kind"), "rx": ("place", "state", "world", "mode"),
                   "bench": ("on", "walking", "x", "z", "gap_left_ms")}
A_DOT_KEYS = ("src", "src_lever", "src_x", "src_z", "src_face", "sx", "sy", "rot", "mapno", "host_x", "host_z", "want", "hud")
A_LINE_KEYS = ("asked", "text", "drawn")


def _body_of(text: str, head: str) -> str:
    """The source text of the method whose signature contains ``head`` (to the next 'private static void Append')."""
    a = text.find(head)
    if a < 0:
        return ""
    b = text.find("private static void Append", a + len(head))
    return text[a:b if b > 0 else a + 20000]


def test_s166a_the_engine_publishes_every_key_and_line_the_solo_rows_judge():
    agent = _s166_text("HarnessAgent.cs")
    ghost = _body_of(agent, "private static void AppendWorldGhost(")
    if not ghost:
        pytest.skip("this s166 source carries no A4 (AppendWorldGhost) yet")
    keyed = re.compile(r'(?:Str|Num|Bool)\(sb, "([a-z_0-9]+)"')
    got = set(keyed.findall(ghost))
    assert set(A_GHOST_KEYS) <= got, set(A_GHOST_KEYS) - got
    assert list(BW.A4_CONTRACT["ghost_sentinels"]) == keyed.findall(ghost), "the stand-in's ghost keys are the engine's, in order"
    lane = _body_of(agent, "private static void AppendWorldLane(")
    lane_keys = set(keyed.findall(lane)) | set(re.findall(r'\\"([a-z_0-9]+)\\":', lane))   # Num/Str/Bool, and the nested blocks' heads
    for k in A_LANE_KEYS + tuple(x for v in A_LANE_SUB_KEYS.values() for x in v):
        assert k in lane_keys, k
    dot = _body_of(agent, "private static void AppendWorldDot(")
    dot_keys = keyed.findall(dot)
    assert set(A_DOT_KEYS) <= set(dot_keys) and dot_keys[-5:] == list(BW.A4_CONTRACT["dot_src_keys"]), dot_keys[-6:]
    line = _body_of(agent, "private static void AppendWorldLine(")
    assert set(A_LINE_KEYS) <= set(keyed.findall(line))
    walk = _s166_text("NetSyncWorldWalk.cs")
    for n in (1, 2, 3, 4, 5, 6, 9):                            # LaneLineText's words, as the bench's lane_lines reads them
        head = BW.ww_lane_line_text(n, 0).split("0 ms")[0]
        assert f'"{head}"' in walk, (n, head)
    assert '"ANH_" + geoName.Substring(4) + "_STAND"' in walk and "return -yawDeg - 90f;" in walk
    for name in ("other_world", "riding", "peer_scene", "peer_block", "stale", "lever"):
        assert f'"{name}"' in walk, name
