"""[ff9mapkit netsync s168] THE GUEST'S MAIN MENU, RUNG 0 -- THE SOLO (S) BENCH's REPO HALF and THE OFFLINE (O) ROWS
(studies/test-harness/scenarios/coop_guest_menu.py, COOP_GM_LEG; studies/field-coop/S168-DESIGN.md "The bench").

  * THE TABLES: legs, rows, levers, predictions, measures and fault rows agree with each other and with the docstring; every S row the
    design's table names is a row (or named as unreached); every row can be turned red offline (OLD, a lever, a fault, or its pure judge).
  * NEW: every leg through the REAL Session on the stand-in (fakegame's opt-in `guestmenu` rung): green wherever the stand-in models the
    engine -- and EXACTLY STANDIN_UNMODELLED red elsewhere, each for its named reason (the stand-in's known gaps, never a pass).
  * OLD: on the deployed-s167 stand-in each leg is exactly the setup's three and every leg row red, s121's bench reading MEASURED, and no
    `guestmenu` op ever sent (the agent would answer "unknown sub-verb" only after the step).
  * LEVER: each (leg, lever) exactly LEVER_PREDICTED red, each predicted row's shape MEASURED (S168-CAL green).
  * GM0-OFFLINE: each of fakegame.GUEST_MENU_FAULTS turns exactly its FAULT_REDS rows red on its legs.
  * THE PURE JUDGES go red on each wrong shape (the in-game-only rows' judges included: HELDKEY, MASTER, the census paths, the cfg close).
  * THE O ROWS: GM0-REGISTRY (every id once; a second claim clashes), GM0-SAVEGATES (the autosave ladder's seat term; its mutant),
    GM0-FRAME (TrailReserve recomputed; the guard rule exact at the cap; its two mutants).

Every scenario-touching run is in a CHILD process: the scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import json
import re
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import fakegame as FG                                     # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
DESIGN = REPO / "studies" / "field-coop" / "S168-DESIGN.md"
_CLEAR = ("FF9_S166_CLONE", "FF9_S167_CLONE", "FF9_S168_CLONE")

#: the rows the stand-in cannot model (fakegame's `guestmenu` rung, as the kit core built it) -> the words its red detail carries: a known
#: gap of the STAND-IN, pinned so a row there can never pass for the wrong reason (and so a stand-in that learns one shows up here)
STANDIN_UNMODELLED = {
    "GM0-WHY-SCENE": "the press: seated",                 # no host scene feeds the predicate's F3 (gm_host_scene is a knob, not `hostscene`)
    "GM0-WHY-HOSTCTL": "the press: seated",               # no F4 (the host holding input) from `swap hostctl off`
    "GM0-WHY-BUSY": "want busy",                          # no busy term from a follow in flight (gm_busy is a knob)
    "GM0-DOOR-889": "no window up at the press",          # no scribe to talk to
    "GM0-HELDKEY": "never opened a window",               # no scribe; and no held-bit write
    "GM0-MASTER": "master_skipped +0",                    # no SetMasterSkill
    "GM0-DIORAMA-BOOT": "BOOTED over the seat",           # the stand-in's boot ignores the seat (BootSeatRule)
    "GM0-SOFTRESET": "backstops.replace +0",              # no Replace backstop
    "GM0-RAMP-CFG": "closes.ending +0",                   # no ApplyConfigChange close
    "GM0-REFUSE-E2": "not reached", "GM0-REFUSE-E3": "not reached", "GM0-REFUSE-A3": "not reached",   # one confirm per screen, no labels
    "GM0-REFUSE-I2": "not reached", "GM0-LOCAL": "not reached",
}

# ------------------------------------------------------------------------------------------------ the child
_CHILD = r'''
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
from harness import Session
from harness import fakegame as FG
SENT = []

def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def root(ini):
    t = pathlib.Path(tempfile.mkdtemp(prefix="gmb_"))
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\nFieldScene 30801 31 JOURNAL "
                                                            "JOURNAL 30801\nFieldScene 30602 31 LOCKT2 LOCKT2 30602\n", encoding="utf-8")
    (t / "Memoria.ini").write_text(ini, encoding="utf-8")
    return t

def fake_for(t, run, cw):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    f.world_walk_pieces = tuple(FG.FAKE_WORLD_WALK_S167_PIECES)      # the s168 engine carries s167; the deployed s167 is this alone
    if run.get("stage", 168) >= 168:
        FG.guest_menu_stand_in(f, faults=tuple(run.get("faults", ())))
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.wf_follow_host_cfg = True
    f.world_kit = dict(FG.FAKE_WORLD_KIT)
    f.world_block_load_frames = 6
    f.swap_qpc = None
    if run.get("tag4"):
        f.gm_tag4_event = tuple(run["tag4"])
    real_ns = f._netsync
    def ns(args, _real=real_ns):
        if args and str(args[0]).lower() == "guestmenu":
            SENT.append(" ".join(str(a) for a in args))
        _real(args)
    f._netsync = ns
    return f

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1600]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

def solo(run):
    for k in [k for k in os.environ if k.startswith("COOP_")] + ["FF9_S166_CLONE", "FF9_S167_CLONE", "FF9_S168_CLONE"]:
        os.environ.pop(k, None)
    os.environ["COOP_GM_LEG"] = run.get("legs", "seat")
    if run.get("lever"):
        os.environ["COOP_GM_LEVER"] = run["lever"]
    gm = load("coop_guest_menu")
    cb = gm.cb
    # the bench's own waits, shortened for a stand-in whose virtual clock runs ahead of the wall (every JUDGED threshold stays the bench's;
    # every window ends on its own condition, so a loaded machine only waits longer -- never judges less)
    for k, v in dict(OPEN_S=4.0, CLOSE_S=5.0, SEL_S=0.6, STEP_S=0.6, HOLD_S=0.3, SAVE_S=0.5, TALK_S=1.0, EXIT_S=4.0, CFG_S=3.0).items():
        setattr(gm, k, v)
    import coop_world_walk as ww
    for k, v in dict(LEAVE_S=20.0, CONTROL_S=3.0).items():
        setattr(ww, k, v)
    for k, v in dict(HOME_S=10.0, LEAVE_S=12.0, START_S=4.0, DOT_S=2.0).items():
        setattr(ww.wf, k, v)
    t = root(run.get("ini", "[Netsync]\nEnabled = 0\nFollowHost = 1\n"))
    f = fake_for(t, run, ww.cw)
    cb.CALIBRATE = bool(run.get("cal"))
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    with g:
        gm.run(g)
        out = rows_of(list(g.checks))
    out["sent"] = list(SENT)
    return out

results = {}
for name, run in doc.get("runs", {}).items():
    SENT.clear()
    results[name] = solo(run)
print("@@" + json.dumps(results))
'''


def _child(payload, *, timeout: float = 1500.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_") and k not in _CLEAR}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    line = [ln for ln in out.stdout.splitlines() if ln.startswith("@@")][-1]
    return json.loads(line[2:])


def _runs(**runs) -> dict:
    return _child({"runs": runs})


def _load_gm():
    import importlib.util
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_guest_menu_pure", str(SCENARIOS / "coop_guest_menu.py"))
    m = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return m


@pytest.fixture(scope="module")
def gm():
    return _load_gm()


def _unmodelled(rows) -> set:
    return {r for r in rows if r in STANDIN_UNMODELLED}


def _want(gm, legs, extra=()) -> list:
    """A stand-in run's reds: ``extra`` plus the stand-in's unmodelled rows on ``legs``, and the CAL row when anything is red."""
    rows = set(gm.leg_rows(legs))
    red = set(extra) | _unmodelled(rows)
    return sorted(red | ({"S168-CAL"} if red else set()))


# ================================================================================================ the tables
def test_the_tables_are_the_docstring_the_design_and_each_others(gm):
    legs = list(gm.LEGS)
    assert legs == ["proof", "seat", "refuse", "deep", "why", "witness", "door", "close", "quit", "held", "master", "diorama", "release",
                    "softreset", "cfg", "quitexit", "world"]
    rows = [r for leg in legs for r in gm.LEG_ROWS[leg]]
    assert len(rows) == len(set(rows)) and set(rows) == set(gm.ROWS)
    assert set(gm.CHAIN_LEGS) <= set(legs) and not {"world", "quitexit", "softreset", "cfg", "deep"} & set(gm.CHAIN_LEGS)
    cat = gm.catalog(("seat",))
    assert list(cat) == list(gm.SETUP) + ["S168-P1"] + list(gm.LEG_ROWS["seat"]) + list(gm.FINAL) + ["S168-CAL"]
    assert "S168-R" not in gm.catalog(("quitexit",))                                     # the destructive leg has no reset to judge
    doc = " ".join((gm.__doc__ or "").split())
    for leg in legs:
        assert f"{leg} " in doc, leg
    # every S row of the design's table is a row here, or named as unreached in the docstring
    design = DESIGN.read_text(encoding="utf-8")
    s_rows = set()
    for ln in design.splitlines():
        if ln.startswith("| GM0-"):
            cells = [c.strip() for c in ln.split("|")]
            if "S" in re.findall(r"[A-Za-z]+", cells[2]):                               # the H column names the selftest role
                s_rows.add(cells[1])
    assert len(s_rows) >= 25 and {"GM0-SEAT", "GM0-REFUSE-x", "GM0-WHY-x", "GM0-DEPTH", "GM0-RELEASE"} <= s_rows
    own = rows + list(gm.SETUP)
    for name in sorted(s_rows):
        stem = name[:-1] if name.endswith("-x") else name + "-"
        hit = any(r == name or r.startswith(stem) for r in own) or name in doc
        assert hit, name
    for name in ("GM0-LOAD", "GM0-DEATH", "GM0-BRACKET", "THE DECLINE LATCH", "THE PRE-INIT SAMPLE", "THE ORDER SKEW", "THE CAL RULE"):
        assert name in doc, name
    # the levers: each leg's levers have ops and a read-back, each (leg, lever) a prediction inside the leg, each a measure
    for leg, levers in gm.LEG_LEVERS.items():
        for lv in levers:
            assert lv in gm.LEVER_OPS and lv in gm.LEVER_READ and lv.split(":")[0] in {k.split(":")[0] for k in gm.MEASURE}, (leg, lv)
            pred = gm.LEVER_PREDICTED.get((leg, lv))
            assert pred is not None and set(pred) <= set(gm.LEG_ROWS[leg]), (leg, lv)
    assert set(k for k, _v in gm.LEVER_PREDICTED) <= set(legs)
    for op in gm.LEVER_OPS.values():
        assert op[0] in BW.GUESTMENU_OPS
    for lv, (field, word) in gm.LEVER_READ.items():
        assert word in BW.GUEST_MENU_LEVER_WORDS[field], lv
    # the faults: exactly the stand-in's, their rows inside their legs
    assert set(gm.FAULT_REDS) == set(FG.GUEST_MENU_FAULTS)
    for fault, by in gm.FAULT_REDS.items():
        for leg, rr in by.items():
            assert leg in legs and set(rr) <= set(gm.LEG_ROWS[leg]) | {"GM0-PROOF", "S168-R"}, (fault, leg)
    # GM0-OFFLINE: every fault whose ROW is an S row reddens it (decision 36's per-fault row, where the selftest role reaches it)
    own_row = {"capture_leak": "GM0-REFUSE-I1", "restore_skip": "GM0-RESTORE", "caps_ignored": "GM0-WHY-OLDER",
               "seat_at_press": "GM0-DOOR-FAULT-OPEN", "quit_under_close": "GM0-QUIT", "own_values": "GM0-SEAT", "release_skip": "GM0-RELEASE",
               "guest_menu_proof_fail": "GM0-PROOF"}
    for fault, row in own_row.items():
        assert any(row in rr for rr in gm.FAULT_REDS[fault].values()), fault
    # every row can be turned red offline: OLD (every leg row), a lever, a fault, or the stand-in's own shape + its pure judge (below)
    assert set(gm.old_predicted(legs)) == set(gm.OLD_SETUP_RED) | set(rows)
    assert set(gm.OLD_SETUP_RED) <= set(gm.SETUP) | {"S168-P1"}
    # the why cases: one per row, each wanting whys of the closed set; the census plans cover every census site
    assert [c[0] for c in gm.WHY_CASES] == list(gm.LEG_ROWS["why"])
    assert all(w in BW.GM_ALL_WHYS for c in gm.WHY_CASES for w in c[1])
    assert set(gm.SITE_PLANS) == set(BW.GM_CENSUS_NAMES) == set(gm.REFUSE_SITES) | set(gm.DEEP_SITES)


def test_the_leg_selection_and_the_lever_choice(gm):
    assert gm._legs("s") == gm.CHAIN_LEGS and gm._legs("seat,why") == ("seat", "why") and gm._legs("nope") is None
    assert gm.lever_of("seat", None) == "old" and gm.lever_of("seat", "chip") == "chip" and gm.lever_of("seat", "capture") is None
    assert gm.lever_of("release", None) is None and gm.lever_predicted("release", None) == ()
    assert gm.lever_predicted("diorama", "old") == ("GM0-DIORAMA-BOOT",)               # GM0-SILENT's NEW is s121's own: green under `old`


def test_the_calibration_refuses_a_second_leg_a_foreign_lever_and_a_mixed_route():
    rs = _runs(two=dict(legs="seat,why", cal=True), foreign=dict(legs="seat", cal=True, lever="capture"),
               mixed=dict(legs="seat,world"), none=dict(legs="nope"))
    assert "EACH LEG NEEDS ITS OWN LAUNCH" in rs["two"]["detail"]["S168-CAL"] and rs["two"]["sent"] == []
    assert "is not leg 'seat''s" in rs["foreign"]["detail"]["S168-CAL"] and rs["foreign"]["sent"] == []
    assert "one route per launch" in rs["mixed"]["detail"]["S168-INI"] and rs["mixed"]["sent"] == []
    assert "names no leg" in rs["none"]["detail"]["S168-INI"]


# ================================================================================================ NEW on the stand-in
def test_the_chain_is_green_on_the_s168_stand_in_where_it_models_the_engine(gm):
    r = _runs(chain=dict(legs="s"))["chain"]
    want = _want(gm, gm.CHAIN_LEGS)
    assert r["red"] == want, {c: r["detail"].get(c, "")[:400] for c in set(r["red"]) ^ set(want)}
    for row in _unmodelled(gm.leg_rows(gm.CHAIN_LEGS)):
        assert STANDIN_UNMODELLED[row] in r["detail"][row], (row, r["detail"][row])
    d = r["detail"]
    assert "TWO MARKERS" in d["GM0-SEAT"] and "'players': True, 'party': True, 'gil': True" in d["GM0-SEAT"]
    assert all("census lines 1" in d[f"GM0-REFUSE-{s}"] and f"last '{s}'" in d[f"GM0-REFUSE-{s}"] for s in gm.REFUSE_SITES)
    assert "outside_settled {'set': True, 'equal': True, 'named': None}" in d["GM0-OUTSIDE"]
    assert "THE ROLLBACK" in d["GM0-SEATFAULT-BAG"] and "'component bag' lines 1" in d["GM0-WITNESS-BAG"]
    assert all("'end': 'done'" in d[f"GM0-DEPTH-{x.upper()}"] and "(watchdog 0)" in d[f"GM0-DEPTH-{x.upper()}"] for x in gm.DEPTHS)
    assert "each of ['leave', 'out', 'rejoin', 'world', 'cut', 'ending', 'title', 'scene'] closed" in d["GM0-CLOSE-IDS"]
    assert "watchdog lines 0" in d["GM0-QUIT"] and "marker 8 (want 8)" in d["GM0-RELEASE"]
    # every guestmenu op the chain sent is one the agent takes
    assert r["sent"] and all(s.split()[1] in BW.GUESTMENU_OPS for s in r["sent"])


def test_the_world_leg_and_the_settle_sees_runtime_state(gm):
    rs = _runs(clean=dict(legs="world"), tag4=dict(legs="world", tag4=[1000, 1]),
               miss=dict(legs="world", tag4=[1000, 1], faults=["settle_same_frame"]))
    assert rs["clean"]["red"] == [], rs["clean"]["detail"]
    assert "outside_settled {'set': True, 'equal': True, 'named': None}" in rs["clean"]["detail"]["GM0-WORLDTAG4"]
    # a modelled tag-4 write one frame after the HUD's Show: the settle sees it (named events) -- red, the row's finding
    assert rs["tag4"]["red"] == ["GM0-WORLDTAG4", "S168-CAL"] and "'named': 'events'" in rs["tag4"]["detail"]["GM0-WORLDTAG4"]
    # settle_same_frame (the CR-3 mutant): the stamp on the frame that FIRST reads events on misses it -- the row reads green: the miss
    assert rs["miss"]["red"] == [] and "'equal': True" in rs["miss"]["detail"]["GM0-WORLDTAG4"]


def test_the_in_game_only_legs_read_the_stand_ins_shape(gm):
    rs = _runs(deep=dict(legs="deep"), softreset=dict(legs="softreset"), cfg=dict(legs="cfg"), quitexit=dict(legs="quitexit"),
               proof=dict(legs="proof"))
    for leg in ("deep", "softreset", "cfg"):
        assert rs[leg]["red"] == _want(gm, (leg,)), (leg, rs[leg]["red"])
        for row in gm.LEG_ROWS[leg]:
            assert STANDIN_UNMODELLED[row] in rs[leg]["detail"][row], (row, rs[leg]["detail"][row])
    assert "the title True" in rs["softreset"]["detail"]["GM0-SOFTRESET"] and "New Game landed True" in rs["softreset"]["detail"]["GM0-SOFTRESET"]
    assert rs["quitexit"]["red"] == [] and "the process exited True" in rs["quitexit"]["detail"]["GM0-QUIT-EXIT"]
    assert "S168-R" not in rs["quitexit"]["all"]
    assert rs["proof"]["red"] == [] and rs["proof"]["all"][-2:] == ["S168-R", "S168-CAL"]


# ================================================================================================ OLD (the deployed s167)
@pytest.mark.parametrize("leg", ["seat", "refuse", "why", "witness", "door", "close", "quit", "release", "world"])
def test_old_on_the_s167_stand_in_is_exactly_its_rows_measured_and_no_guestmenu_op_is_sent(gm, leg):
    r = _runs(r=dict(legs=leg, cal=True, stage=167))["r"]
    want = sorted(set(gm.old_predicted((leg,))))
    assert r["red"] == want, (r["red"], r["detail"].get("S168-CAL"))
    assert "rows whose shape was NOT measured: none" in r["detail"]["S168-CAL"]
    assert r["sent"] == []
    assert "absent: no `netsync.guestmenu`" in r["detail"]["S168-P0"]
    assert all("OLD: no `netsync.guestmenu`" in r["detail"][x] and "`open` measured" in r["detail"][x] for x in gm.LEG_ROWS[leg])


# ================================================================================================ LEVER
def _lever_cases():
    import importlib.util
    spec = importlib.util.spec_from_file_location("coop_guest_menu_cases", str(SCENARIOS / "coop_guest_menu.py"))
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCENARIOS))
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return sorted(k for k in m.LEVER_PREDICTED if k[0] != "deep")             # deep's rows are unreachable on the stand-in (in game only)


@pytest.mark.parametrize("leg,lever", _lever_cases())
def test_each_lever_calibrates_exactly_and_measures_its_shape(gm, leg, lever):
    r = _runs(r=dict(legs=leg, cal=True, lever=lever))["r"]
    want = sorted(gm.LEVER_PREDICTED[(leg, lever)])
    assert r["red"] == want, (r["red"], r["detail"].get("S168-CAL"))
    assert "rows whose shape was NOT measured: none" in r["detail"]["S168-CAL"]
    assert "guestmenu " + " ".join(gm.LEVER_OPS[lever]) in r["sent"], r["sent"]


# ================================================================================================ GM0-OFFLINE: each fault, exactly its rows
def _fault_launches(gm, fault) -> list:
    """The launches a fault's rows sit on (the world leg alone: one route per launch); a fault that reddens no S row runs two legs that must
    stay as the clean stand-in reads them."""
    by = gm.FAULT_REDS[fault]
    field = [leg for leg in gm.LEGS if leg in by and leg != "world"]
    out = []
    if fault == "guest_menu_proof_fail":
        return [("proof",)]
    if field:
        out.append(tuple(field))
    if "world" in by:
        out.append(("world",))
    return out or [("seat", "close")]


@pytest.mark.parametrize("fault", sorted(FG.GUEST_MENU_FAULTS))
def test_each_stand_in_fault_turns_exactly_its_rows_red(gm, fault):
    launches = _fault_launches(gm, fault)
    rs = _child({"runs": {str(i): dict(legs=",".join(legs), faults=[fault]) for i, legs in enumerate(launches)}})
    for i, legs in enumerate(launches):
        r = rs[str(i)]
        rows = {x for leg in legs for x in gm.FAULT_REDS[fault].get(leg, ())}
        want = _want(gm, legs, rows)
        assert r["red"] == want, (legs, {c: r["detail"].get(c, "")[:300] for c in set(r["red"]) ^ set(want)})


# ================================================================================================ THE PURE JUDGES
def _gmk(**over) -> dict:
    """A `netsync.guestmenu` block at the sentinels with ``over`` merged one level deep."""
    import copy
    gmk = copy.deepcopy(BW.GUEST_MENU_SENTINELS)
    gmk["lever"] = dict(BW.GUEST_MENU_LEVER_DEFAULTS)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(gmk.get(k), dict):
            gmk[k] = dict(gmk[k], **v)
        else:
            gmk[k] = v
    return gmk


def _s(ui="FieldHUD", *, frame=1, control=True, dialog=False, mr=None, world=None, booted=False, save=None, **gm_over) -> dict:
    return {"frame": frame, "ui": ui, "field": 30801, "control": control, "dialog": dialog, "gm": _gmk(**gm_over), "mr": dict(mr or {}),
            "world": world, "label": None, "booted": booted, "fading": False, "save": save}


_FP = {"players": "0x01", "party": "0x02", "bag": "0x03", "gil": "0x04", "keyitems": "0x05"}


def _seated_snap(**over):
    comps = {k: {"before": v, "after": None} for k, v in _FP.items()}
    seat = {k: v + "ff" for k, v in _FP.items()}
    kw = dict(seated=True, open=True, opens=1, seat={"src": "bench", "frame_age_ms": 200, "marker": 7},
              fp={"before": "0xAA", "components": comps}, seat_fp={"value": "0xBB", "components": seat}, chip=BW.GM_CHIP_VIEW_ONLY,
              event_enable=False)
    kw.update(over)
    return _s("MainMenu", **kw)


def test_the_seat_chip_freeze_and_browse_judges(gm):
    base = _s()
    lines = ["[NetSync] harness: guestmenu frame 7 -- a two-marker bench host frame (900 B: sections 1, 2, 3 and 12 through the real "
             "encoders; slot 0 the impostor 4 as BENCH7 lv99, every exp a marker, gil 7000007, bag +item 0), ...",
             BW.log_gm_seated(7, 3, 4, 2, 7000007)]
    s = _seated_snap()
    assert gm.judge_seat(base, s, lines, 7)[0]
    assert not gm.judge_seat(base, s, lines, 8)[0]                                        # another marker
    assert not gm.judge_seat(base, s, lines[:1], 7)[0]                                    # no seat line
    assert not gm.judge_seat(base, s, [lines[0], BW.log_gm_seated(7, 3, 4, 2, 1234)], 7)[0]   # the seated gil is not the frame's
    skipped = _seated_snap(seat_fp={"value": "0xBB", "components": dict(_FP, gil="0x04ff")})
    assert not gm.judge_seat(base, skipped, lines, 7)[0] and gm.seat_skip_measured(skipped)  # `seat skip party`: the guest's own drawn
    assert not gm.seat_skip_measured(s)
    assert not gm.judge_seat(base, _s(seated=False, open=True), lines, 7)[0]              # the own menu
    closed = _s(seated=False, chip=None, event_enable=True)
    assert gm.judge_chip([s, s], closed)[0] and not gm.judge_chip([_seated_snap(chip=None)], closed)[0]
    assert gm.chip_off_measured([_seated_snap(chip=None)]) and not gm.chip_off_measured([s])
    assert not gm.judge_chip([s], _s(seated=False, chip=BW.GM_CHIP_VIEW_ONLY))[0]          # a chip after the close
    assert gm.judge_freeze([s, s], closed)[0]
    assert not gm.judge_freeze([s, _seated_snap(event_enable=True)], closed)[0] and gm.events_on_measured([_seated_snap(event_enable=True)])
    assert not gm.events_on_measured([s]) and not gm.events_on_measured([])                # NEW's frozen seat / nothing seated: no shape
    assert not gm.judge_freeze([s], _s(seated=False, event_enable=False))[0]               # events never back on
    assert not gm.judge_freeze([], closed)[0]                                              # never seated: nothing judged is not a pass
    visits = [{"label": lb, "found": True, "state": lb, "back": True, "seated": True} for lb in gm.SUB_SCREENS]
    greys = [{"label": "Order", "picked": True, "state": "MainMenu", "refused_delta": 0, "captures_delta": 0, "seated": True}]
    save = {"serialize": False, "seated": True}
    assert gm.judge_browse(visits, greys, ["Item", "Order"], save, s)[0]
    assert not gm.judge_browse(visits[:-1], greys, [], save, s)[0]                         # Status never opened
    assert not gm.judge_browse(visits, [dict(greys[0], state="Order")], [], save, s)[0]    # a greyed row opened
    assert not gm.judge_browse(visits, [], [], save, s)[0]                                 # no greyed row drawn
    assert not gm.judge_browse(visits, greys, ["Item", "Save"], save, s)[0]                # a Save row
    assert not gm.judge_browse(visits, greys, [], {"serialize": True, "seated": True}, s)[0]
    assert not gm.judge_browse(visits, greys, [], save, skipped)[0]                        # the guest's own party drawn


def test_the_restore_site_grey_outside_and_local_judges(gm):
    base = _s()
    good = _s(seated=False, event_enable=True, restore={"doors": 1}, fp={"before": "0xA", "after": "0xA", "equal": True, "outside_equal": True},
              outside_settled={"set": True, "equal": True, "named": None})
    skip = _s(seated=False, restore={"doors": 1}, fp={"before": "0xA", "after": "0xB", "equal": False, "named": "party", "outside_equal": True})
    assert gm.judge_restore([(base, good), (base, good)])[0]
    assert not gm.judge_restore([(base, good)])[0]                                         # the root-only cycle never ran
    assert not gm.judge_restore([(base, good), (base, skip)])[0] and gm.restore_skip_measured([(base, good), (base, skip)], "party")
    assert not gm.restore_skip_measured([(base, good)], "party")
    assert not gm.judge_restore([(base, good), (base, dict(good, gm=dict(good["gm"], seated=True)))])[0]   # judged while seated
    b, a = _s("Item", refused={"count": 0}), _s("Item", seated=True, refused={"count": 1, "last_site": "I1", "last_screen": "Item"},
                                               captures=1, impactful=0)
    rec = {"reached": True, "before": b, "after": a, "back": True}
    line = [BW.log_gm_census(BW.GM_CENSUS_I1, "Item")]
    assert gm.judge_site("I1", rec, good, line)[0]
    assert not gm.judge_site("I1", rec, good, line * 2)[0]                                # the census line twice
    assert not gm.judge_site("I1", rec, skip, line)[0]                                    # the close's fp differs
    assert not gm.judge_site("E1", rec, good, line)[0]                                    # another site
    passed = dict(rec, after=_s("Item", seated=True, refused={"count": 0}, passes=1, impactful=1), reached=False, reached_pass=True)
    assert not gm.judge_site("I1", passed, good, line)[0] and gm.capture_off_measured(passed)
    assert not gm.capture_off_measured(rec) and not gm.capture_off_measured(dict(passed, reached_pass=False))   # a refused census: no shape
    # GM0-KEYITEM: seated, the unknown-key line, and a clean restore -- each missing is red
    ks = _seated_snap()
    unk = ["[NetSync] guest menu: the host's bag carries 1 key item(s) this install does not know -- drawn as held, never installed"]
    kskip = dict(skip, gm=dict(skip["gm"], fp=dict(skip["gm"]["fp"], named="keyitems")))
    assert gm.judge_keyitem(ks, good, unk)[0]
    assert not gm.judge_keyitem(ks, good, [])[0]                                          # no unknown-key line
    assert not gm.judge_keyitem(ks, kskip, unk)[0]                                        # the close names keyitems
    assert not gm.judge_keyitem(_s(seated=False, open=True), good, unk)[0]                # never seated (the own menu)
    assert not gm.judge_keyitem(ks, None, unk)[0]                                         # no close
    assert not gm.judge_site("I1", {"reached": False, "why": "no Use row"}, good, line)[0]
    assert gm.judge_grey([{"label": "Order", "picked": True, "state": "MainMenu", "refused_delta": 0, "captures_delta": 0, "seated": True}])[0]
    assert not gm.judge_grey([{"label": "Order", "picked": True, "state": "MainMenu", "refused_delta": 1, "captures_delta": 0, "seated": True}])[0]
    assert not gm.judge_grey([])[0]
    assert not gm.judge_grey([{"label": "Order", "picked": False, "state": "MainMenu", "refused_delta": 0, "captures_delta": 0,
                               "seated": True}])[0]                                       # never confirmed: not a grey, not a pass
    assert gm.judge_outside(good)[0]
    poked = _s(seated=False, fp={"outside_equal": False, "outside_named": "events"}, outside_settled={"set": True, "equal": False,
                                                                                                     "named": "events"})
    assert not gm.judge_outside(poked)[0] and gm.poke_measured(poked) and not gm.poke_measured(good)
    steps = [{"what": "sort", "reached": True, "before": _s("Item", seated=True), "after": _s("Item", seated=True)}]
    assert gm.judge_local(steps, good)[0]
    assert not gm.judge_local([dict(steps[0], after=_s("Item", seated=True, refused={"count": 1}))], good)[0]
    assert not gm.judge_local([dict(steps[0], reached=False, why="no Arrange")], good)[0]


def test_the_why_witness_seatfault_and_door_judges(gm):
    base = _s(mr={"count": 3})
    s = _s(why="leaving", line={"text": BW.gm_refusal_line_rule("leaving"), "age": 10}, mr={"count": 4})
    assert gm.judge_why(("leaving",), base, s)[0]
    assert not gm.judge_why(("busy",), base, s)[0]                                        # another why
    assert not gm.judge_why(("leaving",), base, dict(s, mr={"count": 3}))[0]              # silent (count +0)
    assert not gm.judge_why(("leaving",), base, _s("MainMenu", why="leaving", seated=True, opens=1, mr={"count": 4},
                                                  line={"text": BW.gm_refusal_line_rule("leaving")}))[0]
    assert gm.judge_why(("no_data", "older"), base, _s(why="older", line={"text": BW.gm_refusal_line_rule("older")}, mr={"count": 4}))[0]
    w = _s(why="data_differs", line={"text": BW.gm_refusal_line_rule("data_differs", "BENCH7")})
    lines = ["[NetSync] main menu (data_differs) -- BENCH7, component pa suppressed (following guest) on field 30801"]
    assert gm.judge_witness("pa", _s(), w, lines)[0] and not gm.judge_witness("sa", _s(), w, lines)[0]
    assert not gm.judge_witness("pa", _s(), dict(w, gm=dict(w["gm"], why="fault")), lines)[0]
    fb = _s(why="fault", door_refused={"fault": 1}, event_enable=True, fp={"before": "0xA"}, lever={"seat_fault": "off"})
    flines = [BW.log_gm_seat_refused(True, None, "bag")]
    assert gm.judge_seatfault("bag", _s(), fb, flines, "0xA")[0]
    assert not gm.judge_seatfault("bag", _s(), fb, flines, "0xB")[0]                      # THE ROLLBACK: a scratch stayed installed
    assert not gm.judge_seatfault("bag", _s(), dict(fb, gm=dict(fb["gm"], lever={"seat_fault": "bag"})), flines, "0xA")[0]   # not spent
    assert not gm.judge_seatfault("gil", _s(), fb, flines, "0xA")[0]
    d = _s(why="fault", door_refused={"fault": 1}, event_enable=True, lever={"door_fault": "off"})
    assert gm.judge_door_open(_s(), d)[0] and not gm.judge_door_open(_s(), dict(d, control=False))[0]
    assert not gm.judge_door_open(_s(), _s("MainMenu", seated=True, opens=1, door_refused={"fault": 1}))[0]   # seat_at_press: seated
    held = _s(seated=True, restore={"doors": 0})
    reseat = _s("MainMenu", seated=True, opens=1, restore={"doors": 1})
    closed = _s(seated=False, opens=1, restore={"doors": 2}, fp={"before": "0xA", "after": "0xA", "equal": True, "outside_equal": True})
    assert gm.judge_door_restore(_s(), held, reseat, closed)[0]
    assert not gm.judge_door_restore(_s(), _s(seated=False, restore={"doors": 1}), reseat, closed)[0]   # the fault kept nothing
    e = _s(why="host_elsewhere", door_refused={"host_elsewhere": 1}, event_enable=True)
    assert gm.judge_door_889(_s(), e, True)[0]
    assert not gm.judge_door_889(_s(), dict(e, dialog=True), True)[0]                     # the window stayed (no OnKeyMenu)
    assert not gm.judge_door_889(_s(), e, False)[0]                                       # no window: untested, never a pass


def test_the_close_judges(gm):
    base = _s("Item", seated=True)
    words = BW.gm_close_line_rule(BW.GM_CAUSE_LEAVE)
    s = _s(seated=False, event_enable=True, closes={"leave": 1}, close_line={"text": words, "age": 50}, fp={"equal": True},
           last_close={"cause": "leave", "from": "Item", "ms": 90, "end": "done"})
    lines = [BW.log_gm_forced_close(BW.GM_CAUSE_LEAVE, "Item", BW.GM_CE_DONE, 90)]
    assert gm.judge_depth("Item", base, s, lines, 150)[0]
    assert not gm.judge_depth("Item", base, s, lines, 80)[0]                              # past the bound
    assert not gm.judge_depth("Item", base, s, lines * 2, 150)[0]                         # two lines
    assert not gm.judge_depth("Item", base, s, [BW.log_gm_forced_close(BW.GM_CAUSE_LEAVE, "Item", BW.GM_CE_WATCHDOG, 90)], 150)[0]
    assert not gm.judge_depth("Item", _s("MainMenu", seated=True), s, lines, 150)[0]     # the close's `from` is not the depth
    assert gm.depth_ms(40) == 150 and gm.depth_ms(None) == 150 and gm.depth_ms(300) > 150
    old = _s("Item", seated=True)
    assert gm.close_old_measured(base, old, [BW.log_guestmenu_fireclose(BW.GM_CAUSE_LEAVE, "old")])
    assert not gm.close_old_measured(base, s, [])
    f = _s(seated=False, event_enable=True, closes={"faults": 1}, last_close={"end": "fault"})
    assert gm.judge_depth_fault([("sub", base, f, lines)])[0]
    assert not gm.judge_depth_fault([("sub", base, dict(f, gm=dict(f["gm"], event_enable=False)), lines)])[0]
    assert not gm.judge_depth_fault([])[0]
    ids = []
    for cause in BW.GM_CLOSE_IDS:
        c = BW.gm_cause_index_rule(cause)
        ids.append((cause, _s("MainMenu", seated=True), _s(seated=False, event_enable=True, closes={cause: 1}, fp={"equal": True},
                                                            close_line={"text": BW.gm_close_line_rule(c)},
                                                            last_close={"cause": cause, "from": "MainMenu", "ms": 90, "end": "done"}),
                    [BW.log_gm_forced_close(c, "MainMenu", BW.GM_CE_DONE, 90)]))
    assert gm.judge_close_ids(ids, 150)[0]
    assert not gm.judge_close_ids(ids[:-1], 150)[0]                                       # an id never fired
    cancel = _s(seated=False, close_pending=False)
    nos = [BW.log_guestmenu_fireclose(BW.GM_CAUSE_LEAVE, "no_seat")]
    own = {"opened": True, "open": True, "seated": False}
    assert gm.judge_reopen([True, True], cancel, cancel, nos, own)[0]
    assert not gm.judge_reopen([True, False], cancel, cancel, nos, own)[0]                # a reopen refused
    assert not gm.judge_reopen([True], cancel, cancel, nos + lines, own)[0]               # the no-seat fireclose drew a close
    assert not gm.judge_reopen([True], _s(seated=True), cancel, nos, own)[0]              # the seat left held after a Cancel
    assert not gm.judge_reopen([True], cancel, cancel, nos, dict(own, seated=True))[0]
    wait = [_s("MainMenu", seated=True, close_pending=True, close_step="quit")] * 3
    after = _s(seated=False, event_enable=True, closes={"leave": 1}, last_close={"end": "done"})
    assert gm.judge_quit(_s("MainMenu"), wait, [], after, [])[0]
    assert not gm.judge_quit(_s("MainMenu"), wait + [_s("FieldHUD", seated=False)], [], after, [])[0]     # closed under the prompt
    assert not gm.judge_quit(_s("MainMenu"), wait, ["... ended by THE WATCHDOG at its deadline ..."], after, [])[0]
    assert not gm.judge_quit(_s("MainMenu"), wait, [], dict(after, gm=dict(after["gm"], event_enable=False)), [])[0]   # quit_under_close
    assert gm.judge_quit_exit(True, True, True, {"a": "1"}, {"a": "1"})[0]
    assert not gm.judge_quit_exit(True, True, True, {"a": "1"}, {"a": "2"})[0]          # a save written
    assert not gm.judge_quit_exit(True, True, False, {}, {})[0] and not gm.judge_quit_exit(True, True, True, None, None)[0]


def test_the_held_master_diorama_release_softreset_cfg_and_world_judges(gm):
    base = _s(held={"bits": 0, "keyon": 3})
    held = [_s(held={"bits": gm.CONFIRM_MASK, "keyon": 3})] * 3
    assert gm.judge_held(True, base, held, _s(seated=False), True)[0]
    assert not gm.judge_held(True, base, [_s(held={"bits": gm.CONFIRM_MASK, "keyon": 4})], _s(seated=False), True)[0]   # a false edge
    assert not gm.judge_held(True, base, [_s(held={"bits": 0, "keyon": 3})], _s(seated=False), True)[0]   # no held-bit write
    assert not gm.judge_held(True, base, held, _s(seated=False), False)[0]                # the real re-press never talked
    assert not gm.judge_held(False, base, held, _s(seated=False), True)[0]                # no stand: never a pass
    m0, m1 = _s("MainMenu", seated=True, master_skipped=1), _s("MainMenu", seated=True, master_skipped=3)
    assert gm.judge_master(m0, m1, 2)[0] and not gm.judge_master(m0, m0, 2)[0] and not gm.judge_master(m0, m1, 1)[0]
    refused = "dioboot refused: ... -- log: diorama boot REFUSED: the guest menu is seated (...)"
    assert gm.judge_dio_boot(True, refused, _s("MainMenu", seated=True))[0]
    assert not gm.judge_dio_boot(True, "BOOTED over the seat", _s("BattleHUD", booted=True, seated=True))[0]
    assert not gm.judge_dio_boot(True, "dioboot refused: a scene fade is in flight", _s("MainMenu", seated=True))[0]   # not the seat
    b = _s("BattleHUD")
    assert gm.judge_silent(True, "open", b, _s("BattleHUD"))[0]
    assert not gm.judge_silent(True, "silent", b, _s("BattleHUD"))[0] and not gm.judge_silent(True, "open", b, _s("MainMenu", open=True))[0]
    assert not gm.judge_silent(False, "open", b, b)[0]
    set_snap = _s(lever={k: BW.GUEST_MENU_LEVER_WORDS[k][1] for k in BW.GUEST_MENU_LEVER_DEFAULTS})
    after = _s()
    seat2 = _seated_snap(seat={"src": "bench", "frame_age_ms": 10, "marker": 8})
    lines2 = ["[NetSync] harness: guestmenu frame 8 -- a two-marker bench host frame (9 B: x; slot 0 the impostor 4 as BENCH8 lv99, every "
              "exp a marker, gil 7000008, bag +item 0)"]
    rel = [BW.LOG_GUESTMENU_RELEASED]
    assert gm.judge_release(set_snap, after, rel, [], seat2, lines2, 8)[0]
    assert not gm.judge_release(set_snap, _s(lever={"seat_skip": "party"}), rel, [], seat2, lines2, 8)[0]     # release_skip
    assert not gm.judge_release(set_snap, after, rel * 2, [], seat2, lines2, 8)[0]       # the line twice
    assert not gm.judge_release(set_snap, after, rel, rel, seat2, lines2, 8)[0]          # a bare reset spoke
    assert not gm.judge_release(_s(), after, rel, [], seat2, lines2, 8)[0]               # nothing was set off its default
    held_hud = _s(seated=True)
    t = _s("Title", seated=False, restore={"backstops": {"replace": 1}})
    assert gm.judge_softreset(held_hud, True, _s(), t, [BW.log_gm_restored(BW.GM_SITE_REPLACE_TITLE)], True)[0]
    assert not gm.judge_softreset(held_hud, True, _s(), t, [BW.log_gm_restored(BW.GM_SITE_REPLACE)], True)[0]   # the alarm
    assert not gm.judge_softreset(held_hud, True, _s(), t, [], False)[0]                 # the title took no input
    assert not gm.judge_softreset(_s(seated=False), True, _s(), t, [], True)[0]          # no seat held: the backstop untested
    ending = _s(seated=False, closes={"ending": 1}, close_line={"text": BW.gm_close_line_rule(BW.GM_CAUSE_ENDING)}, fp={"equal": True})
    assert gm.judge_cfg(_s(), ending, True)[0] and not gm.judge_cfg(_s(), ending, False)[0]
    assert not gm.judge_cfg(_s(), _s("MainMenu", seated=True), True)[0]
    w0 = _s("WorldHUD", world=9011, uid0_vars="0x1", sysvar192=4)
    w1 = _s("WorldHUD", world=9011, uid0_vars="0x1", sysvar192=4, fp={"equal": True}, outside_settled={"set": True, "equal": True})
    assert gm.judge_worldtag4(w0, w1, True, 9011)[0]
    assert not gm.judge_worldtag4(w0, dict(w1, gm=dict(w1["gm"], uid0_vars="0x2")), True, 9011)[0]   # a script wrote UID 0's vars
    assert not gm.judge_worldtag4(w0, dict(w1, gm=dict(w1["gm"], sysvar192=5)), True, 9011)[0]
    assert not gm.judge_worldtag4(w0, dict(w1, gm=dict(w1["gm"], outside_settled={"set": True, "equal": False, "named": "events"})),
                                  True, 9011)[0]
    assert not gm.judge_worldtag4(w0, dict(w1, world=9010), True, 9011)[0]                # a load ran (another place)
    assert not gm.judge_worldtag4(_s("WorldHUD", world=9011, uid0_vars=None, sysvar192=-1), w1, True, 9011)[0]   # nothing read before


def test_the_setup_judges(gm):
    from harness.channel import State
    ns = {"world": {"walk": {}, "fp": {"lever": "act"}}, "bench": True, "guestmenu": _gmk(caps={"own": BW.CAPS_S168})}
    st = State({"frame": 1, "netsync": ns})
    assert gm.judge_probe(st)[0]
    assert not gm.judge_probe(State({"frame": 1, "netsync": {"world": {}}}))[0]
    assert not gm.judge_probe(State({"frame": 1, "netsync": dict(ns, guestmenu=_gmk(caps={"own": BW.CAPS_S167}))}))[0]
    assert not gm.judge_probe(State({"frame": 1, "netsync": {"guestmenu": ns["guestmenu"], "world": ns["world"], "late": 1}}))[0]
    assert gm.judge_rest(st, dict(BW.GUEST_MENU_LEVER_DEFAULTS))[0] and not gm.judge_rest(st, {"menu": "old"})[0]
    ww, sb, gmp = BW.WORLD_WALK_PROOF_S168, BW.SEAT_BRACKET_PROOF_S168, BW.GUEST_MENU_PROOF_S168
    lines = ["[NetSync] " + BW.proof_ok(BW.PROOF_MENU, BW.MENU_SELFTEST_ROWS), f"[NetSync] {BW.PROOF_WORLD_WALK}OK ({ww[0]} rows, {ww[1]} mutants)",
             BW.seat_bracket_proof_line(*sb), BW.guest_menu_proof_line(*gmp)]
    assert gm.judge_proof(lines, ww, sb, gmp)[0]
    assert not gm.judge_proof([lines[0], lines[1], lines[3], lines[2]], ww, sb, gmp)[0]  # out of order
    assert not gm.judge_proof(lines, ww, sb, (408, 241))[0]                               # the pre-review tally
    assert not gm.judge_proof(lines[1:], ww, sb, gmp)[0]                                  # the menu refusal line gone
    assert not gm.judge_proof(lines + [f"[NetSync] {BW.PROOF_GUEST_MENU}FAIL (row x failed)"], ww, sb, gmp)[0]
    assert gm.judge_cal({"A"}, {"A"}, {"A": True}, ("A",))[0]
    assert not gm.judge_cal({"A", "B"}, {"A"}, {"A": True}, ("A",))[0] and not gm.judge_cal({"A"}, {"A"}, {}, ("A",))[0]


# ================================================================================================ THE O ROWS
def test_gm0_registry_every_id_once_and_a_second_claim_clashes():
    claims = [(space, ident, feature) for space, table in BW.GM_REGISTRY.items() for ident, feature in table.items()]
    assert BW.gm_registry_clashes(claims) == []
    assert BW.gm_registry_clashes(claims + [("caps", 0x02, "a second b1")])               # two claims of b1: red
    assert BW.gm_registry_clashes(claims + [("sections", 12, "another block")])           # two claims of section 12: red
    assert BW.GM_REGISTRY["caps"][BW.WW_CAP_GUEST_MENU] == "the guest menu" and BW.GM_REGISTRY["sections"][BW.SECTION_GUEST_MENU]
    assert BW.GM_REGISTRY["overlay_states"][BW.OVL_GUEST_MENU] == BW.OVERLAY_NAME_GUEST_MENU


def test_gm0_savegates_the_autosave_ladder_refuses_through_its_seat_term():
    # a seat held on the bench: not mirroring, not booted, no stock refusal, no suppress -- the seat term alone refuses
    assert BW.gm_autosave_ladder_rule(False, False, False, False, True)
    assert not BW.gm_autosave_ladder_rule(False, False, False, False, False)

    def no_seat_term(stock, sup, mir, booted, seated):                                    # the mutant: the seat term dropped
        return bool(stock or sup or mir or booted)
    assert not no_seat_term(False, False, False, False, True)                             # red: the pure table alone reddens it
    for args in ((True, False, False, False, False), (False, True, False, False, False), (False, False, True, False, False),
                 (False, False, False, True, False)):
        assert BW.gm_autosave_ladder_rule(*args)                                          # every other term still its own


def test_gm0_frame_the_trail_reserve_and_the_guard_rule():
    assert BW.gm_trail_reserve_of() == BW.GM_TRAIL_RESERVE == 430
    cap = BW.WIRE_MAX_PAYLOAD
    body = 500
    edge = cap - 3 - body - BW.GM_TRAIL_RESERVE
    assert BW.gm_sec12_fits_rule(edge, body) and not BW.gm_sec12_fits_rule(edge + 1, body)   # exact at the cap
    # mutant: TrailReserve one byte short -- the constant row red
    assert BW.GM_TRAIL_RESERVE - 1 != BW.gm_trail_reserve_of()
    # mutant: the check without TrailReserve -- a frame near the cap with a full ring passes 8192
    no_reserve = lambda frame_len, body_len: frame_len + 3 + body_len <= cap                  # noqa: E731
    near = cap - 3 - body - 10
    assert no_reserve(near, body) and near + 3 + body + BW.GM_TRAIL_RESERVE > cap and not BW.gm_sec12_fits_rule(near, body)
    # s168 appends 12 between 11 and 7 (13 reserved after 12): the section order
    order = list(BW.GM_SECTION_ORDER_S168)
    assert order.index(11) < order.index(12) < order.index(7) and order.index(12) < order.index(13)
