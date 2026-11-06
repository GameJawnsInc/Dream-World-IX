"""[ff9mapkit netsync s167] WORLD WALK, ROUND B -- THE SOLO LEGS' REPO HALF (studies/test-harness/scenarios/coop_world_walk.py, COOP_WW_LEG
free | refuse | stale | entry | decline | tps | minimap | map, `b` = all eight): S166-DESIGN.md's Round B rows on the forced selftest role,
driven through the REAL Session on the stand-in (fakegame's `worldwalk` rung with round B's piece "b").

  * THE TABLES: legs, rows, levers, predictions, measures and fault rows agree with each other and with the docstring; every round-B solo
    row the design names is a row (W-STALLHOLE named as T2's); every row can be turned red offline (OLD, a lever, a fault or its pure
    judge).
  * NEW: every leg green on the s167 stand-in in one launch, under both kit reader orders.
  * OLD: on the deployed-s166 stand-in exactly b_old_predicted red per leg, each row MEASURING s166's shape, and no round-B op ever sent.
  * LEVER: each leg's lever (the leg's first) exactly B_LEVER_PREDICTED red, each measuring its shape; the tps leg's none: nothing red.
  * FAULTS: each of fakegame.WORLD_WALK_B_FAULTS (+ walk_proof_fail) turns exactly its B_FAULT_REDS rows red on its legs.
  * THE REGRESSION RE-KEY: round A's legs (and A0's) on the s167 stand-in pull round B's s166 lever set first and read s166: all green.
  * THE PURE JUDGES go red on each wrong shape; the calibration refuses a second leg, a foreign lever and a mixed family.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import json
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
_CLEAR = ("FF9_S166_CLONE", "FF9_S167_CLONE")

# ------------------------------------------------------------------------------------------------ the child
_B_CHILD = r'''
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
from harness import Session
from harness import fakegame as FG

def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
SENT = []

def clone_dir(rows, mutants):
    """A stand-in s167 clone: NetSyncWorldWalk.cs carrying the s167 tag and a proof table of ``rows`` rows and ``mutants`` mutants -- the one
    source both the stand-in's proof line and the bench's S167-W-PROOF want read (FF9_S167_CLONE)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="s167clone_")) / "Assembly-CSharp" / "Memoria" / "Netsync"
    d.mkdir(parents=True)
    body = "\n".join("            row(r, \"x\");" for _ in range(rows))
    names = ", ".join(f"\"m{i}\"" for i in range(mutants))
    (d / "NetSyncWorldWalk.cs").write_text("// [ff9mapkit netsync s167] stand-in\nprivate static Int32 Rows(Rules r, List<String> fails)\n{\n"
                                          + body + "\n}\nprivate static Rules Mutant(String name) { }\n"
                                          "private static readonly String[] MutantNames = { " + names + " };\n", encoding="utf-8")
    return str(d.parents[1])

def root(ini):
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    (t / "Memoria.ini").write_text(ini, encoding="utf-8")
    return t

def fake_for(t, run, cw, wf):
    f = FG.FakeGame(t, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
    # the stage: the deployed s166 (b24e0123: every round-A piece) or s167 (+ round B's piece "b") -- the default of these tests
    f.world_walk_pieces = tuple(FG.FAKE_WORLD_WALK_S166_BUILD if run.get("stage") == 166 else FG.FAKE_WORLD_WALK_S167_PIECES)
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.atb_gain, f.enemy_hit, f.cmd_resolve_frames = 60, 1, 45          # the warm return's fight: one Goblin, won quickly
    f.world_walk_faults = set(run.get("faults", ()))
    f.wf_follow_host_cfg = True
    f.world_kit = dict(FG.FAKE_WORLD_KIT)
    f.world_locations = {wf.ICE_CAVERN: (wf.ICE_TILE[0], wf.ICE_TILE[1], 3.0)}
    if run.get("order") == "e1":
        f.world_kit_order = FG.FAKE_WORLD_KIT_ORDER_E1_FIRST
    f.world_block_load_frames = 6
    f.swap_qpc = None
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
    for k in ("COOP_WW_LEG", "COOP_WW_LEVER", "COOP_CALIBRATE", "FF9_S166_CLONE", "FF9_S167_CLONE"):
        os.environ.pop(k, None)
    os.environ["COOP_WW_LEG"] = run.get("legs", "free")
    if run.get("lever"):
        os.environ["COOP_WW_LEVER"] = run["lever"]
    if run.get("clone"):
        os.environ["FF9_S167_CLONE"] = clone_dir(*run["clone"])
    ww = load("coop_world_walk")
    cw, wf, cb = ww.cw, ww.wf, ww.cb
    # the bench's own waits, shortened for a stand-in whose virtual clock runs ~10x the wall (every JUDGED threshold stays the bench's;
    # every window ends on its own condition, so a loaded machine only waits longer -- never judges less)
    for k, v in dict(LEAVE_S=20.0, CONTROL_S=3.0, CASE_S=4.0, WALK_READY_S=8.0, STALE_FREEZE_S=3.0, STALE_GAP_S=8.0, PRESS_S=1.0,
                     DECLINE_S=0.5, TPS_S=4.0, TPS_WATCH_S=0.5, SEL_S=2.0, TX_S=0.6, GHOST_WALK_S=10.0, RULE_S=5.0, WRAP_S=0.5,
                     DOTRIDE_S=8.0, DOT_BACK_S=4.0, BODY_S=8.0, STALL_S=12.0, RESHOW_S=6.0, GAP_S=6.0, HANG_S=4.0,
                     HANG_TAIL_S=0.1).items():
        setattr(ww, k, v)
    for k, v in dict(HOME_S=10.0, LEAVE_S=12.0, START_S=4.0, DOT_S=2.0).items():
        setattr(wf, k, v)
    for k, v in dict(BATTLE_S=10.0, FIGHT_S=60.0, RETURN_S=15.0).items():
        setattr(cw, k, v)
    cw.read_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    ww.read_kit_oracle = lambda game: {"problems": {}, "facts": {"stand-in": True}}
    t = root("[Netsync]\nEnabled = 0\nFollowHost = 1\n")
    f = fake_for(t, run, cw, wf)
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


def _b_child(payload, *, timeout: float = 1200.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_") and k not in _CLEAR}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _B_CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-4000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _b_run(**run) -> dict:
    return _b_child({"runs": {"r": run}})["r"]


_B_TABLES = r'''
import importlib.util, json, os, sys
scen, tools = sys.argv[1], sys.argv[2]
sys.path.insert(0, tools)
spec = importlib.util.spec_from_file_location("coop_world_walk", os.path.join(scen, "coop_world_walk.py"))
ww = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ww)
print(json.dumps({
    "legs": list(ww.B_LEGS), "rows": {k: list(v) for k, v in ww.B_LEG_ROWS.items()}, "b_rows": list(ww.B_ROWS),
    "levers": {k: list(v) for k, v in ww.B_LEVERS.items()}, "ops": {k: [list(o) for o in v] for k, v in ww.B_LEVER_OPS.items()},
    "predicted": [[leg, lever, list(rows)] for (leg, lever), rows in ww.B_LEVER_PREDICTED.items()], "measure": dict(ww.B_MEASURE),
    "old_red": {k: list(v) for k, v in ww.B_OLD_RED.items()}, "old_setup": list(ww.B_OLD_SETUP_RED),
    "faults": {f: {leg: list(rows) for leg, rows in by.items()} for f, by in ww.B_FAULT_REDS.items()},
    "all_rows": list(ww.B_ALL_ROWS), "catalog": list(ww.b_catalog(False)), "cal": list(ww.b_catalog(True, ("free",), "walk")),
    "setup": list(ww.B_SETUP), "final": list(ww.B_FINAL), "cases": [[r, w, list(o), list(u)] for r, w, o, u in ww.B_REFUSE_CASES],
    "s166_set": [list(o) for o in ww.S166_LEVER_SET], "rest": dict(ww.B_REST), "own_ops": list(ww.B_OWN_OPS),
    "a_legs": list(ww.A_LEGS), "a0_legs": list(ww.LEGS), "doc": " ".join((ww.__doc__ or "").split())}))
'''


@pytest.fixture(scope="module")
def b_tables() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _B_TABLES, str(SCENARIOS), str(REPO / "tools")], env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _union(b_tables, fault) -> list:
    return sorted({r for rows in b_tables["faults"].get(fault, {}).values() for r in rows})


#: each fault's launch: the legs its rows sit on (a fault that reddens no solo row runs two legs that must stay green)
def _fault_legs(b_tables, fault) -> str:
    legs = [leg for leg in b_tables["legs"] if leg in b_tables["faults"].get(fault, {})]
    if fault == "walk_proof_fail":
        legs = ["free"]
    return ",".join(legs or ["free", "stale"])


# ================================================================================================ the tables
def test_the_round_b_tables_are_the_docstring_the_design_and_each_others(b_tables):
    t = b_tables
    assert t["legs"] == ["free", "refuse", "stale", "entry", "decline", "tps", "minimap", "map"]
    assert not set(t["legs"]) & (set(t["a_legs"]) | set(t["a0_legs"]) | {"pair", "a", "all"})   # one family per launch, no name shared
    rows = [r for leg in t["legs"] for r in t["rows"][leg]]
    assert len(rows) == len(set(rows)) and set(rows) == set(t["b_rows"])
    assert t["catalog"] == t["setup"] + ["S167-P1"] + rows + t["final"] and t["cal"][-1] == "S167-CAL"
    assert t["all_rows"] == t["catalog"]
    # the design's Round B rows on the solo route, each named in the docstring and a row here (W-STALLHOLE: T2's, named)
    for name in ("W-FREE", "W-CAM", "W-REFUSE-x", "NOB6", "OTHER", "RIDE", "SCENE", "OWNMODE", "PAIR", "FP", "W-STALE", "W-ENTRY",
                 "W-KITCELL", "W-KITBOAT", "W-FERRY", "W-OPEN", "W-DECLINE", "W-TPS", "W-TPS-APPLY", "W-MAP", "W-MINIMAP",
                 "S167-W-PROOF", "W-STALLHOLE", "THE TRIGGER IS NOT THE CELL", "S166_LEVER_SET"):
        assert name in t["doc"], name
    for leg in t["legs"]:
        assert f"{leg} " in t["doc"] or f"{leg}|" in t["doc"], leg
    # the levers: each leg's levers have ops, each (leg, lever) a prediction inside the leg's rows, each predicted row a measure
    assert set(t["ops"]) == {lv for lvs in t["levers"].values() for lv in lvs} and t["levers"]["tps"] == []
    assert {(leg, lv) for leg, lv, _p in t["predicted"]} == {(leg, lv) for leg, lvs in t["levers"].items() for lv in lvs}
    for leg, lever, pred in t["predicted"]:
        assert set(pred) <= set(t["rows"][leg]) and all(r in t["measure"] for r in pred), (leg, lever)
        assert "S167-W-OPEN" not in pred                                    # W-OPEN's OLD is its NEW: green under every lever
    assert ["fullmap", "old"] in t["ops"]["fullmap"] and ["minimap", "old"] in t["ops"]["fullmap"]   # s166 exactly only together
    # OLD: every leg's rows but W-OPEN, each measured; the setup's three
    assert set(t["old_red"]) == set(t["legs"]) and t["old_setup"] == ["S167-P0", "S167-W-PROOF", "S167-P1"]
    for leg in t["legs"]:
        want = [r for r in t["rows"][leg] if r != "S167-W-OPEN"]
        assert t["old_red"][leg] == want and all(r in t["measure"] for r in want), leg
    # the faults: exactly the stand-in's round-B faults (+ A0's proof fault), their rows inside their legs
    assert set(t["faults"]) == set(FG.WORLD_WALK_B_FAULTS) | {"walk_proof_fail"}
    for fault, by in t["faults"].items():
        for leg, rr in by.items():
            assert leg in t["legs"] and set(rr) <= set(t["rows"][leg]) | {"S167-W-PROOF"}, (fault, leg)
    assert t["faults"]["stall_free"] == {}                                  # W-STALLHOLE is T2's: no solo row
    # every round-B row can be turned red offline: OLD, a lever or a fault (W-OPEN by its pure judge: the test below)
    reddened = {r for rr in t["old_red"].values() for r in rr} | {r for _l, _v, p in t["predicted"] for r in p} | \
               {r for by in t["faults"].values() for rr in by.values() for r in rr}
    assert set(rows) - reddened == {"S167-W-OPEN"}
    # the refusal cases: one per W-REFUSE row, each with its why and an undo; round B's own ops never sent to s166
    assert [c[0] for c in t["cases"]] == t["rows"]["refuse"]
    assert [c[1] for c in t["cases"]] == ["host_not_world", "other_world", "riding", "host_scene", "own_mode", "pairing", "fp_mismatch",
                                          "fp_old"]
    # [W2 critic] decision 21's three fingerprint levers each exercised: `fp fake` (FP), `fp old` (FPDRY), `fp off` (THE REGRESSION SET)
    assert ["worldwalk", "fp", "old"] in [c[2] for c in t["cases"]] and ["fp", "off"] in t["s166_set"]
    assert all(c[1] in BW.WW_WALK_NAMES for c in t["cases"])
    assert set(t["own_ops"]) == set(BW.WORLDWALK_OPS_B)
    # THE REGRESSION SET: W1's whole s166 lever set, each an op round B takes with its s166 word; the rest the engine's
    assert t["s166_set"] == [["walk", "off"], ["refuse", "silent"], ["stallhold", "old"], ["decline", "old"], ["fp", "off"],
                             ["minimap", "old"], ["fullmap", "old"]]
    assert all(w in BW.WORLDWALK_WORDS_B[op] for op, w in t["s166_set"])
    # at rest: each lever's shipping word (its published words' first: walk.lever .. walk.minimap, fp.lever, world_tps.lever, walk.map.lever)
    key = {"walk": "lever", "pair": "pair", "refuse": "refuse", "stallhold": "stallhold", "decline": "decline", "minimap": "minimap"}
    assert {op: t["rest"][op] for op in key} == {op: BW.WORLD_WALK_LEVER_WORDS[k][0] for op, k in key.items()}
    assert (t["rest"]["fp"], t["rest"]["tps"], t["rest"]["fullmap"]) == (BW.WORLD_FP_LEVER_WORDS[0], BW.WORLD_TPS_LEVER_WORDS[0],
                                                                          BW.WORLD_MAP_LEVER_WORDS[0])
    assert set(t["rest"]) == set(key) | {"fp", "tps", "fullmap"}


# ================================================================================================ the stand-in runs
@pytest.mark.parametrize("order", ["e0", "e1"])
def test_every_round_b_leg_is_green_on_the_s167_stand_in_in_one_launch(order):
    r = _b_run(legs="b", order=order)
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    for row in ("S167-P0", "S167-W-PROOF", "S167-P1", "S167-W-FREE", "S167-W-CAM", "S167-W-REFUSE-FP", "S167-W-STALE", "S167-W-OPEN",
                "S167-W-ENTRY", "S167-W-KITCELL", "S167-W-KITBOAT", "S167-W-FERRY", "S167-W-DECLINE", "S167-W-TPS", "S167-W-TPS-APPLY",
                "S167-W-MINIMAP", "S167-W-MAP", "S167-R"):
        assert row in r["all"], row
    d = r["detail"]
    assert "FREE lines 1" in d["S167-W-FREE"] and "b1 set" in d["S167-W-FREE"]
    assert "(world map meshes)" in d["S167-W-REFUSE-FP"] and "mismatch lines 1" in d["S167-W-REFUSE-FP"]
    assert "location lines 1" in d["S167-W-ENTRY"] and "kitcell.closed +0" in d["S167-W-KITCELL"]
    assert ("last reader 0" if order == "e0" else "last reader 1") in d["S167-W-KITCELL"]   # one buzz whichever entry reads first
    assert "9010: ok" in d["S167-W-MAP"] and "9011: ok" in d["S167-W-MAP"]
    # THE WALK'S BENCH: both bench hosts re-issued per leg; round B's own ops reached the engine
    assert "worldfollow host self" in r["sent"] and any(s.startswith("worldwalk host path") for s in r["sent"])
    assert {"worldwalk pair unmirrored", "worldwalk fp fake dead", "worldwalk tps apply", "worldwalk walk off"} <= set(r["sent"])


@pytest.mark.parametrize("leg", ["free", "refuse", "stale", "entry", "decline", "tps", "minimap", "map"])
def test_old_on_the_s166_stand_in_is_exactly_its_rows_each_measured_and_no_round_b_op_is_sent(b_tables, leg):
    """OLD (the deployed s166: no `netsync.world.walk` / `fp` / `walk.map`): exactly the setup's three and the leg's B_OLD_RED red, each
    leg row MEASURING s166's shape (S167-CAL green: frozen, still, silent, once per process, stranded, refused, absent), W-OPEN green,
    and no round-B worldwalk op ever sent."""
    r = _b_run(legs=leg, cal=True, stage=166)
    want = sorted(b_tables["old_setup"] + b_tables["old_red"][leg])
    assert r["red"] == want, (r["red"], r["detail"].get("S167-CAL"))
    assert "rows whose lever shape was NOT measured: none" in r["detail"]["S167-CAL"], r["detail"]["S167-CAL"]
    own = set(b_tables["own_ops"])
    assert not [s for s in r["sent"] if s.startswith("worldwalk") and s.split()[1] in own], r["sent"]
    assert all("absent" in r["detail"][x] or "cam_rot" in r["detail"][x] for x in b_tables["old_red"][leg]), r["detail"]


@pytest.mark.parametrize("leg", ["free", "refuse", "stale", "entry", "decline", "tps", "minimap", "map"])
def test_each_lever_calibrates_exactly_and_measures_its_shape(b_tables, leg):
    """LEVER_PREDICTED on the s167 stand-in, the leg's first lever pulled at P1 and held: exactly B_LEVER_PREDICTED red (the tps leg has
    none: nothing red), each row's shape MEASURED (the lever restores OLD), the calibration green."""
    r = _b_run(legs=leg, cal=True)
    lv = (b_tables["levers"][leg] or [None])[0]
    want = sorted(next((p for lg, v, p in b_tables["predicted"] if lg == leg and v == lv), []))
    assert r["red"] == want, (r["red"], r["detail"].get("S167-CAL"))
    assert "rows whose lever shape was NOT measured: none" in r["detail"]["S167-CAL"]
    for op in b_tables["ops"].get(lv, []) if lv else []:
        assert "worldwalk " + " ".join(op) in r["sent"], (op, r["sent"])


@pytest.mark.parametrize("fault", sorted(set(FG.WORLD_WALK_B_FAULTS) | {"walk_proof_fail"}))
def test_each_round_b_fault_turns_exactly_its_rows_red(b_tables, fault):
    r = _b_run(legs=_fault_legs(b_tables, fault), faults=[fault])
    want = _union(b_tables, fault)
    assert r["red"] == want, {c: r["detail"].get(c, "")[:500] for c in set(r["red"]) ^ set(want)}


def test_the_calibration_names_one_leg_its_own_lever_and_one_family():
    rs = _b_child({"runs": {"two": dict(legs="free,refuse", cal=True), "foreign": dict(legs="entry", cal=True, lever="walk"),
                            "mixed": dict(legs="free,tx"), "mixed0": dict(legs="kitoff,map")}})
    assert "EACH LEG NEEDS ITS OWN LAUNCH" in rs["two"]["detail"]["S167-CAL"] and rs["two"]["sent"] == []
    assert "is not leg 'entry''s" in rs["foreign"]["detail"]["S167-CAL"] and rs["foreign"]["sent"] == []
    assert "one family per launch" in rs["mixed"]["detail"]["S167-INI"] and rs["mixed"]["sent"] == []
    assert "one family per launch" in rs["mixed0"]["detail"]["S167-INI"] and rs["mixed0"]["sent"] == []


def test_s167_w_proof_reads_the_s167_sources_tallies():
    """S167-W-PROOF's want is the s167 source's (here a stand-in clone's 7 rows / 2 mutants: the stand-in prints the same); with no source
    reachable it wants more than s166's 323 / 110, which the W1 fallback (532 / 196) is."""
    rs = _b_child({"runs": {"clone": dict(legs="free", clone=[7, 2]), "none": dict(legs="free")}})
    assert rs["clone"]["red"] == [] and "want (7, 2)" in rs["clone"]["detail"]["S167-W-PROOF"], rs["clone"]["detail"]["S167-W-PROOF"]
    if not any(p.name.startswith("s167-") for p in (REPO / "memoria-patches").glob("*.patch")):
        assert rs["none"]["red"] == [] and "want above s166's (323, 110)" in rs["none"]["detail"]["S167-W-PROOF"]


# ================================================================================================ THE REGRESSION RE-KEY
def test_round_a_and_a0_on_the_s167_stand_in_pull_the_s166_lever_set_and_read_s166():
    """An s167 build under round A's legs: P1 pulls W1's whole s166 lever set (walk off, refuse silent, stallhold old, decline old, fp off,
    minimap old, fullmap old) and reads it back; A-PROOF wants the s167 source's tallies; every round-A and A0 row green -- a re-key BY
    STAGE, never a weakened row. On the s166 stand-in nothing of it is sent (the round-A tests' own runs)."""
    rs = _b_child({"runs": {"a": dict(legs="a"), "a0": dict(legs="kitoff,ferryoff")}})
    for name in ("a", "a0"):
        r = rs[name]
        assert r["red"] == [], (name, {c: r["detail"][c] for c in r["red"]})
        head = r["sent"][:7]
        assert head == ["worldwalk walk off", "worldwalk refuse silent", "worldwalk stallhold old", "worldwalk decline old",
                        "worldwalk fp off", "worldwalk minimap old", "worldwalk fullmap old"], (name, r["sent"][:9])
    assert "the s167 source's tallies" in rs["a"]["detail"]["S166-A-PROOF"] or "above A0b's" in rs["a"]["detail"]["S166-A-PROOF"]
    assert "round B's s166 lever set read back" in rs["a"]["detail"]["S166-A-P1"]
    assert "round B's s166 lever set read back" in rs["a0"]["detail"]["S166-P1"]


# ================================================================================================ the pure judges
def _load_ww():
    import importlib.util
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_world_walk_pure_b", str(SCENARIOS / "coop_world_walk.py"))
    m = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return m


def _st(frame=1, *, ui="WorldHUD", world=9011, x=68.0, z=-444.0, control=True, vehicle=0, walk=None, mapb=None, fp=None, lane=None,
        freeze=None, line=None, dot=None, kit=None, cam=0.0, nm=3, fading=False, mapvar=None, flags=None, field=-1):
    from harness.channel import State
    w = None
    if walk is not None:
        w = dict(BW.WORLD_WALK_SENTINELS, **walk)
        w["map"] = dict(BW.WORLD_WALK_MAP_SENTINELS, **(mapb or {}))
    blocks = {"freeze": dict({"on": True, "why": "bench", "keys": 0, "map": 0}, **(freeze or {})),
              "kitcell": dict({"closed": 0}, **(kit or {}))}
    for k, v in (("walk", w), ("fp", fp), ("lane", lane), ("line", line), ("dot", dot)):
        if v is not None:
            blocks[k] = v
    raw = {"frame": frame, "ui_state": ui, "fading": fading, "field": {"id": field}, "player": {"control": control},
           "world": {"id": world, "x": x, "z": z, "vehicle": vehicle, "ctl": vehicle, "block_ready": True, "ticks": frame,
                     "cam_rot": cam, "next_mode": nm, "mapvar": mapvar},
           "netsync": {"world": blocks, "bench": True}, "flags": {str(k): v for k, v in (flags or {}).items()}}
    return State(raw)


def test_the_pure_round_b_judges_go_red_on_each_wrong_shape():
    ww = _load_ww()
    # W-FREE: a walk of 60 u, free throughout, one edge, b1 -- green; each term off -- red
    free = {"free": True, "why": None}
    lane = {"tx": {"state": BW.WW_ST_WALKING | 0x85, "why": 0}}
    b, s = _st(1, walk=free, lane=lane), _st(2, walk=free, lane=lane)
    lines = [BW.log_ww_walk_free(9011)]
    assert ww.judge_free(b, s, 60.0, 40, lines)[0]
    assert not ww.judge_free(b, s, 3.0, 40, lines)[0]                                   # under WALK_U
    assert not ww.judge_free(b, s, 60.0, 40, lines * 2)[0]                              # two edges
    assert not ww.judge_free(b, _st(2, walk=free, lane={"tx": {"state": 0x85, "why": 0}}), 60.0, 40, lines)[0]   # no b1
    assert not ww.judge_free(b, _st(2, walk=free, lane=lane, freeze={"on": False}), 60.0, 40, lines)[0]          # the freeze dropped
    assert "absent" in ww.judge_free(b, _st(2), 0.0, 40, [])[1]
    # W-CAM: each way, opposite; a still camera is OLD's shape
    assert ww.judge_cam(_st(cam=0.0), _st(cam=30.0), _st(cam=0.0))[0]
    assert not ww.judge_cam(_st(cam=0.0), _st(cam=30.0), _st(cam=60.0))[0]              # the same way twice
    assert not ww.judge_cam(_st(cam=0.0), _st(cam=1.0), _st(cam=0.0))[0]
    assert ww.cam_still(_st(cam=10.0), _st(cam=10.1), _st(cam=10.0)) and not ww.cam_still(_st(cam=0.0), _st(cam=30.0), _st(cam=0.0))
    assert ww.judge_cam(_st(cam=355.0), _st(cam=20.0), _st(cam=350.0))[0]             # across 0 degrees
    # W-REFUSE: its own why, held, its words, free before and after
    ok_case = {"op": "x", "sent": "sent", "sent_ok": True, "pre": _st(walk=free), "moved": 0.0, "adv": 40,
               "ref": _st(walk={"why": "riding", "why_code": BW.WW_WALK_RIDING}),
               "post": _st(walk={"why": "riding", "why_code": BW.WW_WALK_RIDING, "free": False, "line": BW.WORDS_WORLD_OUT_RIDES}),
               "back": _st(walk=free), "lines": []}
    assert ww.judge_refuse("S167-W-REFUSE-RIDE", "riding", ok_case)[0]
    assert not ww.judge_refuse("S167-W-REFUSE-RIDE", "host_scene", ok_case)[0]          # another why
    assert not ww.judge_refuse("S167-W-REFUSE-RIDE", "riding", dict(ok_case, moved=40.0))[0]    # it walked
    assert not ww.judge_refuse("S167-W-REFUSE-RIDE", "riding", dict(ok_case, back=_st(walk={"free": False})))[0]   # never undone
    assert not ww.judge_refuse("S167-W-REFUSE-RIDE", "riding", dict(ok_case, pre=_st(walk={"free": False})))[0]    # no control
    assert not ww.judge_refuse("S167-W-REFUSE-FP", "riding", ok_case)[0]                # FP's extras missing
    # [W2 critic] FPDRY: fp_old only past a MATCHING fingerprint (the walk would be free), b1 and b4 clear
    dry_w = {"why": "fp_old", "why_code": BW.WW_WALK_NAMES.index("fp_old"), "free": False}
    dry = dict(ok_case, ref=_st(walk=dry_w), post=_st(walk=dict(dry_w, line=ww.walk_line_want(_st(walk=dry_w))),
                                                     fp={"state": "match"}, lane={"tx": {"state": 0x85}}))
    assert ww.judge_refuse("S167-W-REFUSE-FPDRY", "fp_old", dry)[0]
    assert not ww.judge_refuse("S167-W-REFUSE-FPDRY", "fp_old", dict(dry, post=_st(walk=dry["post"].raw["netsync"]["world"]["walk"],
                                                                                 fp={"state": "mismatch"}, lane={"tx": {"state": 0x85}})))[0]
    assert not ww.judge_refuse("S167-W-REFUSE-FPDRY", "fp_old", dict(dry, post=_st(walk=dry["post"].raw["netsync"]["world"]["walk"],
                                                                                 fp={"state": "match"},
                                                                                 lane={"tx": {"state": 0x85 | BW.WW_ST_WALKING}})))[0]
    # W-OPEN: a buzz on open ground is red; an unread press (keys +0) is red
    b0 = _st(1, walk={"entry_refused": 0}, freeze={"keys": 0})
    assert ww.judge_open(b0, [_st(2, walk={"entry_refused": 0}, freeze={"keys": 1})], [])[0]
    assert not ww.judge_open(b0, [_st(2, walk={"entry_refused": 1}, freeze={"keys": 1})], [])[0]
    assert not ww.judge_open(b0, [_st(2, walk={"entry_refused": 0}, freeze={"keys": 0})], [])[0]
    assert not ww.judge_open(_st(1, freeze={"keys": 0}), [_st(2, walk={"entry_refused": 1}, freeze={"keys": 1})], [])[0]   # unread
    assert not ww.judge_open(b0, [_st(2, walk={"entry_refused": 0}, freeze={"keys": 1})],
                             [BW.log_ww_entry_press(BW.WW_ENTRY_LOCATION, 1, 4, 9011)])[0]
    # W-ENTRY: one buzz by entry 1 at place 4; the request byte or the discovery bit moved, two buzzes, reader 0 -- red
    hit = {"entry_refused": 1, "last_reader": 1, "last_place": 4, "last_entry": "location", "last_world": 9011,
           "last_cell": list(BW.world_cell(68.0, -444.0))}                         # the walker's cell at the press (_st's pose)
    mv = "00" * 80
    loc_line = [ww.BW.ww_entry_press_what(BW.WW_ENTRY_LOCATION, 1, 4)]
    eb = _st(1, walk={"entry_refused": 0}, mapvar=mv, flags={ww.DISCOVERY_BIT: False})
    good = _st(2, walk=hit, line={"asked": "entry_refused"}, mapvar=mv, flags={ww.DISCOVERY_BIT: False})
    assert ww.judge_entry(eb, [good], loc_line)[0]
    req = mv[:58] + "04" + mv[60:]
    assert not ww.judge_entry(eb, [_st(2, walk=hit, line={"asked": "entry_refused"}, mapvar=req, flags={ww.DISCOVERY_BIT: False})],
                              loc_line)[0]
    assert not ww.judge_entry(eb, [_st(2, walk=hit, line={"asked": "entry_refused"}, mapvar=mv, flags={ww.DISCOVERY_BIT: True})],
                              loc_line)[0]
    assert not ww.judge_entry(eb, [_st(2, walk=dict(hit, entry_refused=2), line={"asked": "entry_refused"}, mapvar=mv,
                                       flags={ww.DISCOVERY_BIT: False})], loc_line)[0]
    assert not ww.judge_entry(eb, [_st(2, ui="FieldHUD", world=-1, walk=hit, mapvar=mv, flags={ww.DISCOVERY_BIT: False})], loc_line)[0]
    # [W2 critic] decision 18's last_cell: the buzz stamps the walker's own cell -- another cell, or none stamped, is red
    for cell in ([3, 13], [-1, -1], None):
        assert not ww.judge_entry(eb, [_st(2, walk=dict(hit, last_cell=cell), line={"asked": "entry_refused"}, mapvar=mv,
                                           flags={ww.DISCOVERY_BIT: False})], loc_line)[0], cell
    # W-KITCELL: either reader, one buzz; two buzzes, a close, a field -- red
    kb = _st(1, walk={"entry_refused": 0})
    k0 = {"entry_refused": 1, "last_reader": 0, "last_place": 100, "last_entry": "kit_cell", "last_world": 9011, "last_cell": [2, 13]}
    k1 = {"entry_refused": 1, "last_reader": 1, "last_place": 62, "last_entry": "location", "last_world": 9011, "last_cell": [2, 13]}
    assert ww.judge_kitcell(kb, [_st(2, walk=k0)], [])[0] and ww.judge_kitcell(kb, [_st(2, walk=k1)], [])[0]
    assert not ww.judge_kitcell(kb, [_st(2, walk=dict(k0, last_cell=[-1, -1]))], [])[0]     # no cell stamped at the buzz
    assert not ww.judge_kitcell(kb, [_st(2, walk=dict(k1, last_place=100))], [])[0]    # a sid-1 read off a place
    assert not ww.judge_kitcell(kb, [_st(2, walk=dict(k0, entry_refused=2))], [])[0]
    assert not ww.judge_kitcell(kb, [_st(2, walk=k0, kit={"closed": 1})], [])[0]
    # W-KITBOAT: sid 15 at 169 or sid 1 at 69; boarded -- red
    bb = {"entry_refused": 1, "last_reader": 15, "last_place": 169, "last_entry": "boat", "last_world": 9011}
    assert ww.judge_kitboat(kb, [_st(2, walk=bb)], [])[0]
    assert not ww.judge_kitboat(kb, [_st(2, walk=bb, vehicle=7)], [])[0]
    assert not ww.judge_kitboat(kb, [_st(2, walk=dict(bb, last_place=100))], [])[0]
    assert not ww.judge_kitboat(kb, [_st(2, walk=bb, nm=1)], [])[0]                    # [W2 critic] a field request (next_mode 1)
    assert not ww.judge_kitboat(kb, [_st(2, walk=dict(bb, last_world=9010))], [])[0]
    # W-FERRY: sid 16 at 100; Map[50] set -- red
    fb = {"entry_refused": 1, "last_reader": 16, "last_place": 100, "last_entry": "ferryman", "last_world": 9011}
    f_line = [BW.ww_entry_press_what(BW.WW_ENTRY_FERRY, 16, 100)]
    assert ww.judge_ferry(kb, [_st(2, walk=fb, mapvar=mv)], f_line)[0]
    scene = mv[:100] + "01" + mv[102:]
    assert not ww.judge_ferry(kb, [_st(2, walk=fb, mapvar=scene)], f_line)[0]
    assert not ww.judge_ferry(kb, [_st(2, walk=fb, mapvar=mv, nm=1)], f_line)[0]     # [W2 critic] a field request (next_mode 1)
    # entry_silent: OLD's shape -- masked, no buzz, no line; a buzz or the hazard is not it
    sb = _st(1, freeze={"keys": 0})
    assert ww.entry_silent(sb, [_st(2, freeze={"keys": 1})], [], lambda ss: False)
    assert not ww.entry_silent(sb, [_st(2, freeze={"keys": 1}, walk={"entry_refused": 1})], [], lambda ss: False)
    assert not ww.entry_silent(sb, [_st(2, freeze={"keys": 1})], [], lambda ss: True)
    # W-DECLINE: once, nothing after the warm return, once more after the round trip
    w0, w1 = _st(walk={"visits": 1, "rearms": 0}), _st(walk={"visits": 1, "rearms": 0})
    t1 = _st(walk={"visits": 2, "rearms": 1})
    d = {"n1": 1, "n2": 0, "warm": (True, "ok", w0, w1), "n3": 0, "trip": (True, "ok", w1, t1, [BW.log_ww_decline_rearmed(1)]),
         "n4": 1}
    assert ww.judge_decline(d)[0]
    assert not ww.judge_decline(dict(d, n4=0))[0] and not ww.judge_decline(dict(d, n3=1))[0] and not ww.judge_decline(dict(d, n2=1))[0]
    assert not ww.judge_decline(dict(d, warm=(True, "ok", w0, _st(walk={"visits": 2, "rearms": 1}))))[0]   # a warm return re-armed
    # [W2 critic] OLD's shape needs its positive half: the line spoke once first (a needle that matches nothing reads n4 0 too)
    old = dict(d, n4=0)
    assert ww.decline_once_per_process(old) and not ww.decline_once_per_process(d)
    assert not ww.decline_once_per_process(dict(old, n1=0)) and not ww.decline_once_per_process(dict(old, trip=(False, "no", w1, t1, [])))
    # [W2 critic] W-FREE-9002: walked on WorldHUD 9002, free, the freeze kept, a FREE line naming 9002, b1
    l92 = [BW.log_ww_walk_free(9002)]
    s92 = _st(2, world=9002, walk=free, lane=lane)
    assert ww.judge_free_world(s92, 60.0, 40, l92, 9002)[0]
    assert not ww.judge_free_world(s92, 1.0, 40, l92, 9002)[0]                        # held
    assert not ww.judge_free_world(_st(2, walk=free, lane=lane), 60.0, 40, l92, 9002)[0]   # never left 9011
    assert not ww.judge_free_world(s92, 60.0, 40, [BW.log_ww_walk_free(9011)], 9002)[0]   # the FREE edge named another world
    assert not ww.judge_free_world(_st(2, world=9002, walk={"free": False, "why": "lever"}, lane=lane), 60.0, 40, l92, 9002)[0]
    assert "absent" in ww.judge_free_world(_st(2, world=9002), 0.0, 40, [], 9002)[1]
    # W-TPS / W-TPS-APPLY
    tb = _st(lane={"world_tps": {"own": 28, "peer": 28, "lever": "report", "held": 0, "effective": 28, "mismatch": False, "lines": 0}})
    ts = _st(lane={"world_tps": {"own": 28, "peer": 20, "lever": "report", "held": 0, "effective": 28, "mismatch": True, "lines": 1}})
    tl = [BW.log_ww_tps("selftest", 28, 20)]
    assert ww.judge_tps(tb, ts, tl, 28, 20)[0]
    assert not ww.judge_tps(tb, ts, tl * 2, 28, 20)[0] and not ww.judge_tps(tb, ts, [], 28, 20)[0]
    assert "absent" in ww.judge_tps(tb, _st(lane={"world_tps": {"own": 28, "peer": 20}}), [], 28, 20)[1]
    assert ww.tps_absent(_st(lane={"world_tps": {"own": 28, "peer": 20}}), [], 20) and not ww.tps_absent(ts, tl, 20)
    ta = _st(lane={"world_tps": {"own": 28, "peer": 20, "lever": "apply", "held": 20, "effective": 20, "mismatch": True, "lines": 1}})
    assert ww.judge_tps_apply(ta, [BW.log_ww_tps_held(20, 28)], 28, 20, (True, ""), (True, "ok"))[0]
    assert not ww.judge_tps_apply(ta, [], 28, 20, (True, ""), (True, "ok"))[0]
    assert not ww.judge_tps_apply(ts, [BW.log_ww_tps_held(20, 28)], 28, 20, (True, ""), (True, "ok"))[0]
    # W-MINIMAP: the close, the reopen, the new visit; stranded (OLD) and a forgotten latch are red
    mb = _st(walk={"minimap_closes": 0, "hint_quiet": False, "visits": 1}, dot={"hud": "HUD", "minimap": True, "navi_mode": 1})
    mc = _st(walk={"minimap_closes": 1, "hint_quiet": True, "visits": 1}, dot={"hud": "HUDNoMiniMap", "minimap": False, "navi_mode": 0})
    mr = _st(walk={"minimap_closes": 1, "hint_quiet": True, "visits": 1}, dot={"hud": "HUD", "minimap": True, "navi_mode": 1})
    mt = _st(walk={"minimap_closes": 1, "hint_quiet": False, "visits": 2}, dot={"hud": "HUDNoMiniMap"})
    m = {"base": mb, "close": mc, "lines": [BW.log_ww_minimap_closed(9011)], "reopen": mr, "trip": (True, "ok", mr, mt)}
    assert ww.judge_minimap(m)[0] and not ww.minimap_stranded(m)
    strand = _st(walk={"minimap_closes": 0, "hint_quiet": False}, freeze={"map": 1}, dot={"hud": "HUD", "minimap": True, "navi_mode": 1})
    assert not ww.judge_minimap(dict(m, close=strand))[0] and ww.minimap_stranded(dict(m, close=strand))
    assert not ww.judge_minimap(dict(m, close=_st(walk={"minimap_closes": 1, "hint_quiet": False}, dot=dict(mc.raw["netsync"]["world"]
                                                                                                             ["dot"]))))[0]
    assert not ww.judge_minimap(dict(m, trip=(True, "ok", mr, mr)))[0]                  # no new visit: still quiet
    # W-MAP: FullMap with the dot shown AND placed, opens +1, map +0, one line, the close latching
    pb = _st(walk=free, mapb={"lawful": True, "opens": 0}, dot={"hud": "HUD"})
    po = _st(walk=free, mapb={"lawful": True, "opens": 1, "dot_shown": True, "dot_placed": True}, dot={"hud": "FullMap", "navi_mode": 2})
    pc = _st(walk=dict(free, hint_quiet=True), mapb={"dot_shown": False}, dot={"hud": "HUDNoMiniMap"})
    good_map = [(9011, {"base": pb, "open": [po], "lines": [BW.log_ww_map_opens(9011)], "close": pc}, "ok")]
    assert ww.judge_map(good_map)[0]
    unplaced = _st(walk=free, mapb={"lawful": True, "opens": 1, "dot_shown": True, "dot_placed": False}, dot={"hud": "FullMap",
                                                                                                             "navi_mode": 2})
    assert not ww.judge_map([(9011, dict(good_map[0][1], open=[unplaced]), "ok")])[0]  # LIVE VERDICT vs LAST DRAWN
    refused = _st(walk=free, mapb={"lawful": True, "opens": 0}, freeze={"map": 1}, dot={"hud": "HUD"})
    assert not ww.judge_map([(9011, dict(good_map[0][1], open=[refused]), "ok")])[0]
    assert ww.map_refused({"base": pb, "open": [refused]}) and not ww.map_refused({"base": pb, "open": [po]})
    assert not ww.judge_map([(9011, None, "never landed")])[0]
    # W-STALE: the gap's instrument (it ended before the reload was judged) is "not reached", never a pass
    fr = [_st(i, walk=free) for i in range(3)]
    rb, rs = _st(walk={"held_drops": 1}), _st(walk={"held_drops": 2, "held_trailer": False, "free": False, "why": "peer_caps"},
                                              lane={"bench": {"gap_left_ms": 30000}})
    p = {"freeze": (fr, 50.0, 40, fr[-1]), "nob6": (_st(walk={"why": "host_not_world"}), _st(walk=free)),
         "gap": (_st(walk=dict(free, held_trailer=True), lane={"arrival_age_ms": 4000}), 50.0, 40, None),
         "reload": (rb, rs, True, "ok"), "resume": _st(walk=free)}
    assert ww.judge_stale(p)[0]
    ended = _st(walk={"held_drops": 2, "held_trailer": True, "free": True}, lane={"bench": {"gap_left_ms": 0}})
    ok, why = ww.judge_stale(dict(p, reload=(rb, ended, True, "ok")))
    assert not ok and "the gap ended before the reload" in why
    assert not ww.judge_stale(dict(p, freeze=(fr, 0.0, 40, fr[-1])))[0]               # frozen under the freeze: OLD's shape
    assert "the rest not run" in ww.judge_stale({"freeze": (fr, 0.0, 40, fr[-1])})[1]
    # S167-P0 / S167-W-PROOF
    world = {k: (dict(v) if isinstance(v, dict) else v) for k, v in BW.WORLD_SENTINELS_S167.items()}
    world["lane"]["caps"] = {"own": 3, "peer": -1, "off": -1}
    from harness.channel import State
    assert ww.judge_b_probe(State({"netsync": {"world": world}}))[0]
    swapped = dict(world)
    swapped = {**{k: v for k, v in world.items() if k not in ("walk", "fp")}, "fp": world["fp"], "walk": world["walk"]}
    assert not ww.judge_b_probe(State({"netsync": {"world": swapped}}))[0]           # fp before walk
    world1 = dict(world, lane=dict(world["lane"], caps={"own": 1}))
    assert not ww.judge_b_probe(State({"netsync": {"world": world1}}))[0]             # `fp off` left on: caps 1
    ok_lines = [f"[NetSync] {BW.PROOF_WORLD_WALK}OK (532 rows, 196 mutants)", "[NetSync] " + BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 58)]
    assert ww.judge_b_proof(ok_lines, (532, 196))[0] and ww.judge_b_proof(ok_lines, None, "none")[0]
    s166_lines = [f"[NetSync] {BW.PROOF_WORLD_WALK}OK (323 rows, 110 mutants)", "[NetSync] " + BW.proof_ok(BW.PROOF_OVERLAY_TEXT, 50)]
    assert not ww.judge_b_proof(s166_lines, None, "none")[0] and not ww.judge_b_proof(ok_lines[:1], (532, 196))[0]
    assert not ww.judge_b_proof(ok_lines + [f"[NetSync] {BW.PROOF_WORLD_WALK}FAIL x"], (532, 196))[0]
