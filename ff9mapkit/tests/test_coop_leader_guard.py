"""[ff9mapkit netsync s143] THE LEADER GUARD's REPO HALF -- the harness rung, the driver's lever gate, the stand-in's model of
the guard (and its fault levers), the repro bench (studies/test-harness/scenarios/coop_leader_guard.py) and its seats, the
re-keyed benches, the runners.

The owner's decision (2026-10-19, after the Plant Brain report): [Netsync] GuestSlots stays positional, but a guest bit that
lands on the host's LEADER moves to the next member (wrapping), else drops. tests/test_leader_guard.py pins the ENGINE half
(the rule's twin against the engine's own selftest rows, the call-site law, the keys); this file pins what the repo builds on
it -- every check of the bench made to fail by a stand-in fault, the calibration sets on the s141 stand-in and under the
lever, the oracle off the kit's own party resolver and a kit-built `.eb`, and THE PREMISE CENSUS: every bench that hands the
loopback guest a party position, re-checked against the guard (neutral, or re-keyed by the engine's stage).

Every scenario-touching test runs the bench in a CHILD process (the scenario puts its own dir on sys.path -- never this
process's: ~40 modules there a bare import could resolve to).
"""
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

from ._patchstack import msr, net_lines

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import HarnessError, Session                          # noqa: E402
from harness import battlewire as BW                               # noqa: E402
from harness import fakegame as FG                                 # noqa: E402
from harness.fakegame import FakeGame                              # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"
BENCH = REPO / "studies" / "battle-coop" / "bench"
RUN = BENCH / "run"
PATCH = "s143-netsync-guest-never-leader.patch"
PB, FX, CP = [10, 0, 1, 3], [2, 0, 1, 3], [0, 1, 2, 3]       # the three seats' CharacterIds (field 257, 261, COOPPARTY)
FIELDS = (30602, 30604, 30607, 30608, 30609)
BODY = {30609: 8}                                             # the leader-body seat: the kit's Vivi walks it


# ------------------------------------------------------------------------------------------------ the stand-in, in-process
def _game(tmp_path, fields=FIELDS):
    (tmp_path / "x64").mkdir(parents=True)
    (tmp_path / "x64" / "FF9.exe").write_bytes(b"MZ")
    (tmp_path / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    mod = tmp_path / "FF9CustomMap"
    mod.mkdir()
    (mod / "DictionaryPatch.txt").write_text("".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in fields),
                                             encoding="utf-8")
    return tmp_path


def _fake(game, **kw) -> FakeGame:
    fake = FakeGame(game)
    fake.fps = 240
    fake.battle_seat_party = True
    fake.party_adds = {30604: (1, 2, 3), 30607: tuple(PB), 30608: tuple(FX)}
    fake.party_removes = {30607: tuple(range(12)), 30608: tuple(range(12))}
    fake.atb_gain, fake.enemy_hit, fake.cmd_resolve_frames = 60, 1, 45
    fake.ini_ghost_as = "auto"
    fake.field_player_models = dict(BODY)
    for k, v in kw.items():
        setattr(fake, k, v)
    return fake


def _session(game, fake) -> Session:
    return Session(game_path=game, run_dir=game / "run", save_dir=game / "player-saves", pid_probe=lambda: [],
                   launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)


def _log(fake) -> str:
    return pathlib.Path(fake.memoria_log).read_text(encoding="utf-8", errors="replace")


def _seated(g, seat: int):
    g.newgame(settle=0)
    g.warp(30604)
    if seat != 30604:
        g.warp(seat)
    g.warp(30602)
    g.netsync("selftest", 1)
    g.netsync("guestslots", 2)


# ------------------------------------------------------------------------------------------------ the rung and the driver
def test_the_leaderguard_rung_is_s143s_after_dresspolish_and_calibrates_on_s141():
    names = list(FG.NETSYNC_BATTLE_CAPS)
    # [ff9mapkit netsync s144] the LAST rung through s143 (s144's `worldwait` follows it: test_world_coop.py)
    assert [n for n in names if int(FG.NETSYNC_BATTLE_CAPS[n][0][1:]) <= 143][-1] == "leaderguard"
    assert names[names.index("dresspolish") + 1] == "leaderguard"
    assert FG.NETSYNC_BATTLE_CAPS["leaderguard"] == ("s143", ()) and FG.NETSYNC_S143_CAPS == frozenset(("leaderguard",))
    assert "leaderguard" not in FG.caps_through("dresspolish") and "dresspolish" in FG.caps_through("dresspolish")
    assert FG.NETSYNC_BATTLE_CAP_KEYS["leaderguard"] == {"host": ("guard",), "peer": ("guard",)}
    assert FG.NETSYNC_DRESS_CAP_KEYS["leaderguard"] == BW.DRESS_KEYS_BY_RUNG["leaderguard"] == ("guard",)
    assert Session.NETSYNC_BENCH_OPS["leaderguard"][:3] == ("coop_leader_guard", "netsync.battle.host.guard", "s143")
    # the bench's probe is the rung's key (and _coop_battle's ladder carries it)
    src = (SCENARIOS / "_coop_battle.py").read_text(encoding="utf-8")
    assert '143: "netsync.battle.host.guard",' in src
    assert "PROBE = cb.R3_PROBES[143]" in (SCENARIOS / "coop_leader_guard.py").read_text(encoding="utf-8")


def test_the_driver_never_sends_bench_leaderguard_to_an_s141_engine(tmp_path):
    """THE s110 HAZARD AGAIN: an s141 agent reads `bench leaderguard off` as `bench 1` (the FIELD-GATE bench ON). The driver
    refuses it before the step on an engine without `host.guard`; on s143 it lands, logs its OFF line, `off` reads true."""
    game = _game(tmp_path)
    old = _fake(game, netsync_caps=FG.caps_through("dresspolish"))
    with _session(game, old) as g:
        g.newgame(settle=0)
        g.warp(30602)
        g.netsync("selftest", 1)
        with pytest.raises(HarnessError, match="netsync.battle.host.guard"):
            g.netsync("bench", "leaderguard", "off")
        assert not any(s and s[0] == "netsync" and "leaderguard" in s for s in old.executed)
        assert g.state.netsync.get("bench") is False                  # the field-gate bench never went ON
    game2 = _game(tmp_path / "s143")
    new = _fake(game2)
    with _session(game2, new) as g:
        g.newgame(settle=0)
        g.warp(30602)
        with pytest.raises(HarnessError, match="selftest role"):     # the agent's own role gate
            g.netsync("bench", "leaderguard", "off")
        g.netsync("selftest", 1)
        with pytest.raises(HarnessError, match="leaderguard on\\|off"):
            g.netsync("bench", "leaderguard", "maybe")
        st = g.netsync("bench", "leaderguard", "off")
        st = g.wait_for(lambda s: s.coop_guard_off is True, timeout=4.0, what="the lever")
        assert BW.LOG_GUARD_OFF in _log(new)


@pytest.mark.parametrize("stuck", [False, True])
def test_the_release_puts_the_lever_back_and_says_so(tmp_path, stuck):
    """`reset` (HarnessReleaseBench) releases the lever LAST with "leader guard back ON (released with the harness)", once;
    the re-read WITH the role reads off false. The `lever_stuck` fault keeps it -- off reads true there (the bench's S143-R
    can fail), and no release line is written."""
    game = _game(tmp_path)
    fake = _fake(game, guard_faults={"lever_stuck"} if stuck else set())
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(30602)
        g.netsync("selftest", 1)
        g.netsync("bench", "leaderguard", "off")
        g.wait_for(lambda s: s.coop_guard_off is True, timeout=4.0, what="the lever")
        g.send("reset")
        st = g.wait_for(lambda s: s.netsync is not None and not s.netsync["forced"], timeout=5.0, what="the release")
        assert st.coop_guard_off is False                             # the role is off: the lever cannot bite
        g.netsync("selftest", 1)
        st = g.wait_for(lambda s: s.netsync["forced"], timeout=5.0, what="the role again")
        assert st.coop_guard_off is stuck
        assert _log(fake).count(BW.LOG_GUARD_RELEASED) == (0 if stuck else 1)


# ------------------------------------------------------------------------------------------------ the stand-in's model
def test_the_stand_in_guards_plant_brain_and_blanks_appear_moves_nothing(tmp_path):
    """The seated Plant Brain battle on the stand-in: the field latch (Zidane, 98), the battle latch over [Blank, Zidane,
    Vivi, Steiner] (Blank hidden at boot, counted) -> 0x4 moved 1 -> 2, its line once; the host never opens Vivi, opens
    Zidane; Blank appears at the HEAD of the list with a full gauge, the guard unchanged, his window the host's."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        _seated(g, 30607)
        st = g.state
        assert st.coop_dress_party == PB and st.coop_guard_leader == 0 and st.coop_guard_leader_model == 98
        assert (st.coop_guard_raw, st.coop_guard_effective) == (2, 2)                # outside an own battle: GuestSlots
        g.start_battle(303, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce
                        and s.coop_peer_guard_line, timeout=10.0, what="the latch and both lines")
        assert (st.coop_guard_effective, st.coop_guard_moved_from, st.coop_guard_moved_to) == (4, 1, 2)
        assert st.coop_guard_chars == PB and 0 not in [u["slot"] for u in st.units(player=True)]
        assert st.coop_guard_line == "Partner: Vivi (not Zidane)" and st.coop_guard_line_shown is True
        assert (st.coop_peer_guard_mask, st.coop_peer_guard_line, st.coop_peer_guard_shown) == (4, "You: Vivi", False)
        log = _log(fake)
        assert log.count(BW.guard_latch_line(PB, 2, 0, 4, 1, 2, st.coop_guard_nonce)) == 1
        seen, after, appeared = set(), set(), False
        for _ in range(900):
            s = g.state
            if not appeared and [u for u in s.units(player=True) if u["slot"] == 0]:
                appeared = True
                assert s.units()[0]["slot"] == 0 and s.units()[0]["name"] == "Blank" and fake.battle_appears == 1
                assert (s.coop_guard_effective, s.coop_guard_moved_from, s.coop_guard_moved_to) == (4, 1, 2)
            if s.turn_slot >= 0:
                (after if appeared else seen).add(s.turn_slot)
                try:
                    g.battle_command(s.turn_slot, 1, sub=176, target=16)
                except HarnessError:
                    pass
            if 0 in after:
                break
            g.wait_frames(4)
        assert appeared and 1 in seen and 2 not in seen, (appeared, seen)
        assert 0 in after and 2 not in after, after                  # Blank's window opens on the HOST
        st = g.state
        assert (st.coop_guard_effective, st.coop_guard_moved_from, st.coop_guard_chars) == (4, 1, PB)


def test_the_stand_in_moves_nothing_on_coopparty_and_the_lever_restores_the_positions(tmp_path):
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        _seated(g, 30604)
        g.start_battle(67, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce
                        and s.coop_guard_line, timeout=10.0, what="the latch")
        assert (st.coop_guard_effective, st.coop_guard_moved_from, st.coop_guard_chars) == (2, -1, CP)
        assert st.coop_guard_line == "Partner: Vivi"
        fake.end_battle(1)
        g.wait_for(lambda s: s.ui_state == "FieldHUD", timeout=5.0, what="the field")
        g.warp(30607)
        g.warp(30602)
        g.netsync("bench", "leaderguard", "off")
        g.start_battle(303, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce
                        and s.coop_guard_line, timeout=10.0, what="the latch under the lever")
        assert (st.coop_guard_off, st.coop_guard_effective, st.coop_guard_moved_from) == (True, 2, -1)
        assert st.coop_guard_leader == 0                                   # the latch itself is untouched by the lever
        assert st.coop_guard_line == "Partner: Zidane"
        assert BW.guard_latch_line(PB, 2, -1, 2, -1, -1, st.coop_guard_nonce, guard_on=False) in _log(fake)


def test_the_stand_in_field_site_guards_auto_only(tmp_path):
    """FieldGuardMask at the selftest mirror site: `selfdress ghost 2` on the Plant Brain seat -> Vivi (8, rig 1) and
    `dress.guard` {0, 2, 4, 1, 2} with ONE field line; `rule s138` (the pre-s139 site) -> no guard, Zidane; the lever -> no
    leader, Zidane."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        _seated(g, 30607)
        g.netsync("selfdress", "ghost", 2)
        st = g.wait_for(lambda s: s.coop_dress_ghost_model == 8, timeout=4.0, what="Vivi")
        assert st.coop_dress_ghost_rig == 1
        assert st.coop_dress_guard_block == {"leader": 0, "raw": 2, "effective": 4, "moved_from": 1, "moved_to": 2}
        g.wait_frames(20)
        assert _log(fake).count(BW.guard_field_log(2, 4, 1, 2, 0)) == 1
        g.netsync("selfdress", "rule", "s138")
        st = g.wait_for(lambda s: s.coop_dress_ghost_model == 98, timeout=4.0, what="the s138 site: Zidane")
        g.netsync("selfdress", "clear")
        g.netsync("bench", "leaderguard", "off")
        g.netsync("selfdress", "ghost", 2)
        st = g.wait_for(lambda s: s.coop_dress_ghost_model == 98 and s.coop_dress_guard_leader == -1, timeout=4.0,
                        what="the lever: the positional rule")
        assert (st.coop_dress_guard_effective, st.coop_dress_guard_moved_from) == (2, -1)


# ------------------------------------------------------------------------------------------------ the bench, in children
_CHILD = r"""
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW
spec = importlib.util.spec_from_file_location("coop_leader_guard", os.path.join(scen, "coop_leader_guard.py"))
lg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lg)
doc = json.loads(sys.stdin.read() or "{}")
"""

_RUNS = _CHILD + r"""
def oracle(game):
    seats, base = {}, [0, -1, -1, -1]
    for f, (rm, add) in {30604: ((), (1, 2, 3)), 30608: (tuple(range(12)), (2, 0, 1, 3)),
                         30607: (tuple(range(12)), (10, 0, 1, 3))}.items():
        seats[f] = dict(lg.seat_want(BW.seat_after(base, rm, add), 0), where="the stand-in")
    body = dict(lg.seat_want(seats[30604]["party"], 1, me_model=8, wire=lg.BODY_WIRE), where="the stand-in", leader=1,
                model=8)
    return {"seats": seats, "leader": 0, "model": 98, "problems": {}, "body": body}
results = {}
for name, run in doc["runs"].items():
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in run.get("fields", (30602, 30604, 30607, 30608, 30609))),
        encoding="utf-8")
    if run.get("ini"):
        (t / "Memoria.ini").write_text(run["ini"], encoding="utf-8")
    lg.read_oracle = oracle
    fake = FG.FakeGame(t)
    fake.fps = 240
    if run.get("caps"):
        fake.netsync_caps = FG.caps_through(run["caps"])
    fake.battle_seat_party = True
    fake.party_adds = {30604: (1, 2, 3), 30607: tuple(run.get("pb_adds", (10, 0, 1, 3))), 30608: (2, 0, 1, 3)}
    fake.party_removes = {30607: tuple(range(12)), 30608: tuple(range(12))}
    fake.atb_gain, fake.enemy_hit, fake.cmd_resolve_frames = 60, 1, 45
    fake.ini_ghost_as = "auto"
    fake.field_player_models = {30609: 8}
    fake.guard_faults = set(run.get("faults", ()))
    lg.cb.CALIBRATE = bool(run.get("cal"))
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, fake=fake: fake.start(), boot_timeout=15.0, verbose=False)
    with g:
        g._booted_once = True
        lg.run(g)
        rows = list(g.checks)
    results[name] = {"red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
                     "all": sorted(r["what"].split(":")[0] for r in rows),
                     "detail": {r["what"].split(":")[0]: r["detail"][:400] for r in rows}}
print(json.dumps(results))
"""


def _child(script: str, payload=None, *, timeout: float = 600.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-c", script, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload or {}), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _tables() -> dict:
    return _child(_CHILD + r"""
print(json.dumps({"catalog": sorted(lg._catalog(False)), "catalog_cal": sorted(lg._catalog(True)),
                  "old": list(lg.OLD_PREDICTED), "lever": list(lg.LEVER_PREDICTED), "l_rows": list(lg.L_ROWS),
                  "faults": {k: list(v) for k, v in lg.GUARD_FAULT_REDS.items()},
                  "faults_cal": {k: list(v) for k, v in lg.GUARD_FAULT_REDS_CAL.items()},
                  "consts": [lg.BATTLE_FIELD, lg.PARTY_FIELD, lg.PB_FIELD, lg.FX_FIELD, lg.GUEST_SLOTS, lg.PLANT_BRAIN,
                             lg.GOBLIN, lg.PB_HIDDEN_CHAR, lg.PROBE, lg.PEER_PROBE, lg.DRESS_PROBE, lg.BODY_FIELD,
                             lg.BODY_WIRE, lg.BCMD_TRIES],
                  "doc": " ".join((lg.__doc__ or "").split())}))
""")


def test_the_benchs_tables_are_its_docstring():
    t = _tables()
    cat = set(t["catalog"])
    assert set(t["l_rows"]) == {f"S143-L{i}" for i in range(11)} <= cat
    assert set(t["catalog_cal"]) == cat | {"S143-CAL"} and "S143-CAL" not in cat
    assert set(t["old"]) <= cat and set(t["lever"]) <= cat
    # the lever's reds are behavioural ones the old engine shows too; L0 / L4 / L7 stay green under it, L0 on s141 too
    assert set(t["lever"]) < set(t["old"]) and not {"S143-L0", "S143-L4", "S143-L7"} & set(t["lever"])
    assert "S143-L0" not in t["old"] and "S143-R" not in t["old"] and "S143-S0" not in t["old"]
    assert set(t["faults"]) | set(t["faults_cal"]) == set(FG.GUARD_FAULTS)
    assert t["consts"] == [30602, 30604, 30607, 30608, 2, 303, 67, 10, "netsync.battle.host.guard",
                           "netsync.battle.peer.guard", "netsync.dress.guard", 30609, 98, 3]
    doc = t["doc"]
    for frag in ("OLD_PREDICTED", "LEVER_PREDICTED", "GUARD_FAULT_REDS", "COOPPBRAIN 30607", "COOPFOREST 30608",
                 "COOPVIVI 30609", "`battle 303 0`", "THE UNATTENDED LAW", "0293cb46ffa176f6", "seat_after",
                 "a STALE seat fails closed", "bench leaderguard off", "B_MEMBER(66)", "left running", "`battle.message`",
                 "ring gap", "WHAT NO SOLO BENCH REACHES", "BCMD_TRIES", "does not parse is red"):
        assert frag in doc, frag


def test_the_bench_runs_green_on_the_s143_stand_in():
    r = _child(_RUNS, {"runs": {"plain": {}}})["plain"]
    assert r["red"] == [], {c: r["detail"][c] for c in r["red"]}
    assert r["all"] == sorted(_tables()["catalog"])                   # every catalog row recorded, each once


def test_the_bench_calibrates_on_the_s141_stand_in_and_under_the_lever():
    t = _tables()
    r = _child(_RUNS, {"runs": {"s141": {"caps": "dresspolish", "cal": True}, "lever": {"cal": True}}})
    assert r["s141"]["red"] == sorted(t["old"]), r["s141"]["red"]
    assert r["lever"]["red"] == sorted(t["lever"]), r["lever"]["red"]
    for run in ("s141", "lever"):
        assert "S143-CAL" in r[run]["all"] and "S143-CAL" not in r[run]["red"]
    # each red is the one the docstring names: s141's L2 / L3 / L6 BEHAVIOURAL, the rest on their absent keys
    d = r["s141"]["detail"]
    assert "never 2" in d["S143-L2"] and "on 2 at +frames [" in d["S143-L2"] and "(98, 0)" in d["S143-L6"]
    assert "absent" in d["S143-L1"] and "absent" in d["S143-P0"] and "absent" in d["S143-L10"]
    assert "(1,)" in d["S143-L9"]                                          # s141's roster carries Zidane's slot
    d = r["lever"]["detail"]
    assert "'Partner: Zidane'" in d["S143-L5"] and "'off': True" in d["S143-L1"] and "(98, 0)" in d["S143-L6"]
    assert "(8, 1)" in d["S143-L10"] and "leader 1 leader_model 8" in d["S143-L10"]   # the latch reads Vivi, the site not
    assert "(1,)" in d["S143-L9"]


@pytest.mark.parametrize("fault", [f for f in FG.GUARD_FAULTS if f != "lever_stuck"])
def test_each_guard_fault_turns_exactly_its_rows_red(fault):
    """A CHECK THAT CANNOT FAIL IS NO CHECK: each stand-in fault (a value the engine would not publish, never an absent
    key) turns exactly its GUARD_FAULT_REDS row red -- together they cover every L row and P2."""
    want = sorted(_tables()["faults"][fault])
    r = _child(_RUNS, {"runs": {fault: {"faults": [fault]}}})[fault]
    assert r["red"] == want, (r["red"], {c: r["detail"][c] for c in r["red"]})


def test_the_faults_cover_every_row_and_the_release_fault_reds_r():
    """Every guard row has a fault that turns it red (L0 -- the seat -- is the oracle's: a wrong seat, below); and the
    release that keeps the lever turns S143-R red on top of the lever's own reds."""
    t = _tables()
    covered = {c for rows in t["faults"].values() for c in rows}
    assert (set(t["l_rows"]) - {"S143-L0"}) | {"S143-P2"} <= covered
    r = _child(_RUNS, {"runs": {"stuck": {"faults": ["lever_stuck"], "cal": True}}})["stuck"]
    assert r["red"] == sorted(set(t["lever"]) | set(t["faults_cal"]["lever_stuck"])), r["red"]


def test_a_missing_or_wrong_seat_reads_red_never_green():
    """No seat registered: PRE and every L row red, "not reached". A seat whose Main_Init seats ANOTHER party (Zidane first:
    [Zidane, Blank, Vivi, Steiner]): L0 red on the oracle's [10, 0, 1, 3] and the Plant Brain rows after it "not reached"
    (L7 / L8 are other seats: green)."""
    t = _tables()
    r = _child(_RUNS, {"runs": {"nopb": {"fields": [30602, 30604]},
                                "wrong": {"pb_adds": [0, 10, 1, 3]}}})
    nopb, wrong = r["nopb"], r["wrong"]
    assert "S143-PRE" in nopb["red"] and set(t["l_rows"]) <= set(nopb["red"])
    assert all("not reached" in nopb["detail"][c] for c in t["l_rows"])
    pb_rows = {"S143-L0", "S143-L6", "S143-L1", "S143-L5", "S143-L2", "S143-L9", "S143-L3", "S143-L4"}
    assert set(wrong["red"]) == pb_rows, wrong["red"]
    assert "[0, 10, 1, 3]" in wrong["detail"]["S143-L0"]
    assert all("not reached" in wrong["detail"][c] for c in pb_rows - {"S143-L0"})


# ------------------------------------------------------------------------------------------------ the seat tape's setup
_TAPE = r"""
import importlib.util, json, os, pathlib, sys, tempfile
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
from harness import Session
from harness import fakegame as FG
spec = importlib.util.spec_from_file_location("coop_tape_record", os.path.join(scen, "coop_tape_record.py"))
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)
doc = json.loads(sys.stdin.read() or "{}")
edits = []
class NoIni:                                    # the smoke never touches an ini: constructing one is recorded
    def __init__(self, *a, **k):
        edits.append("IniGuard")
    def apply(self):
        raise RuntimeError("the smoke edits no ini")
    def restore(self):
        return True, "n/a"
tr.pb.IniGuard = NoIni
tr.pb.port_free = lambda port: (True, "the smoke's port")
results = {}
for name, run in doc["runs"].items():
    del edits[:]
    t = pathlib.Path(tempfile.mkdtemp())
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "x64" / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (t / "FF9CustomMap").mkdir()
    (t / "FF9CustomMap" / "DictionaryPatch.txt").write_text(
        "".join(f"FieldScene {f} 11 T{f} T{f} {f}\n" for f in run["fields"]), encoding="utf-8")
    fake = FG.FakeGame(t)
    fake.fps = 240
    fake.party_adds = {30604: (1, 2, 3), 30607: tuple(run.get("pb_adds", (10, 0, 1, 3))), 30608: (2, 0, 1, 3)}
    fake.party_removes = {30607: tuple(range(12)), 30608: tuple(range(12))}
    tr.SEAT = int(run.get("seat", 0))
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, fake=fake: fake.start(), boot_timeout=15.0, verbose=False)
    with g:
        g._booted_once = True
        go = None
        if run.get("whole"):
            tr.run(g)
        else:
            led = tr.cb.Ledger(g, tr._catalog(tr.SEAT), finals=("REC-INI",))
            go = tr._host_setup(g, led, tr._Ctx(tr.FIELD))
        rows = list(g.checks)
        results[name] = {"go": go, "field": g.state.field_id, "edits": list(edits),
                         "red": sorted(r["what"].split(":")[0] for r in rows if not r["ok"]),
                         "all": sorted(r["what"].split(":")[0] for r in rows),
                         "detail": {r["what"].split(":")[0]: r["detail"][:400] for r in rows},
                         "catalog": sorted(tr._catalog(tr.SEAT))}
print(json.dumps(results))
"""


def test_the_tape_recorders_setup_lands_on_250_and_a_bad_seat_fails_closed():
    """(review s143 rfield-1 / rharness-1) coop_tape_record's host setup on the stand-in. COOPPARTY UNREGISTERED: seed_party
    returns without a warp, so the host would record on New Game's field 70 -- the setup still lands on field 250. A seat
    that SEATS its party: REC-SEAT green, then 250. A seat whose Main_Init seats ANOTHER party (a stale deploy): REC-SEAT red
    and the WHOLE run stops before any Memoria.ini edit (no IniGuard built, REC-INI 'never edited', the rest 'not reached').
    An UNREGISTERED seat: the warp refused, REC-SEAT red. The default run has no REC-SEAT row."""
    runs = {"nocoop": {"fields": [30607, 30608]},
            "seat": {"fields": [30604, 30607, 30608], "seat": 30607},
            "stale": {"fields": [30604, 30607, 30608], "seat": 30607, "pb_adds": [0, 10, 1, 3], "whole": True},
            "noseat": {"fields": [30604, 30608], "seat": 30607}}
    r = _child(_TAPE, {"runs": runs})
    nocoop, seat, stale, noseat = r["nocoop"], r["seat"], r["stale"], r["noseat"]
    # COOPPARTY unregistered: no seed warp (field 70 after New Game), yet the host stands on 250
    assert nocoop["go"] is True and nocoop["field"] == 250 and nocoop["red"] == [], nocoop
    assert "REC-SEAT" not in nocoop["catalog"] and nocoop["all"] == []
    # a seat that seats [Blank, Zidane, Vivi, Steiner]
    assert seat["go"] is True and seat["field"] == 250 and seat["all"] == ["REC-SEAT"] and seat["red"] == [], seat
    assert "[10, 0, 1, 3]" in seat["detail"]["REC-SEAT"] and "lands on the leader" in seat["detail"]["REC-SEAT"]
    # a stale seat ([Zidane, Blank, Vivi, Steiner]): red, and nothing edited -- the whole run stops there
    assert stale["edits"] == [] and "REC-SEAT" in stale["red"], stale
    d = stale["detail"]
    assert "[0, 10, 1, 3]" in d["REC-SEAT"] and "STALE or wrong seat" in d["REC-SEAT"]
    assert "REC-INI" not in stale["red"] and "never edited" in d["REC-INI"]
    assert set(stale["all"]) == set(stale["catalog"]) and set(stale["red"]) == set(stale["catalog"]) - {"REC-INI"}
    assert all("not reached" in d[c] for c in stale["red"] if c != "REC-SEAT")
    # an unregistered seat: the warp refused -- REC-SEAT red, every other row closed "not reached" (REC-INI is the run's final)
    assert noseat["go"] is False and "refused" in noseat["detail"]["REC-SEAT"], noseat
    assert set(noseat["red"]) == set(noseat["all"]) == set(noseat["catalog"]) - {"REC-INI"}


def test_the_tape_recorders_setup_is_one_function_with_the_fallback_outside_the_seat():
    """The fallback warp is unconditional (outside `if SEAT:`), the seat judged before the ini is touched, the default run's
    ledger is the plain catalog."""
    src = (SCENARIOS / "coop_tape_record.py").read_text(encoding="utf-8")
    body = src[src.index("def _host_setup("):src.index("def seat_party(")]
    lines = [ln for ln in body.splitlines() if ln.strip()]
    fb = next(i for i, ln in enumerate(lines) if ln.strip() == "if g.state.field_id != ctx.field:")
    assert lines[fb].startswith("    if ") and lines[fb + 1].strip() == "g.warp(ctx.field)"     # function level, not in SEAT
    assert body.index("if SEAT:") < body.index('led.check("REC-SEAT", ok, why)') < body.index("return False")
    run_src = src[src.index("def _run("):src.index("def _note_host_ghost(")]
    assert run_src.index("if not _host_setup(g, led, ctx):") < run_src.index("ctx.guard = pb.IniGuard(")
    assert "led = cb.Ledger(g, _catalog(SEAT)," in src


# ------------------------------------------------------------------------------------------------ the pure judges
_JUDGES = _CHILD + r"""
import copy
cb = lg.cb
def host(**kw):
    g = dict(BW.GUARD_HOST_SENTINELS, **kw)
    return g
def doc(guard=None, peer=None, dress=None, units=None, turn=-1, enabled=True, ghost=None, party=None, frame=1):
    d = {"frame": frame, "battle": {"active": True, "turn": {"enabled": enabled, "slot": turn},
                                    "units": units or []},
         "netsync": {"battle": {"host": {"guest_slots": 2}, "peer": {"nonce": 7, "live": True}},
                     "session": {"ghost": True}, "dress": {"party": party or [10, 0, 1, 3]}}}
    if guard is not None:
        d["netsync"]["battle"]["host"]["guard"] = guard
    if peer is not None:
        d["netsync"]["battle"]["peer"]["guard"] = peer
    if dress is not None:
        d["netsync"]["dress"]["guard"] = dress
    if ghost is not None:
        d["netsync"]["dress"]["ghost"] = {"model": ghost[0], "rig": ghost[1], "bench_mask": ghost[2]}
    return d
out = {}
lines = ["x |M| [NetSync] " + BW.PROOF_LEADER_GUARD + f"OK ({BW.LEADER_GUARD_SELFTEST_ROWS} rows)"]
full = doc(guard=host(), peer=dict(BW.GUARD_PEER_SENTINELS), dress=dict(BW.DRESS_GUARD_SENTINELS))
out["probe"] = [lg.judge_probe(full, lines)[0], lg.judge_probe(doc(), lines)[0], lg.judge_probe(full, [])[0],
                lg.judge_probe(doc(guard={"leader": -1}, peer=dict(BW.GUARD_PEER_SENTINELS),
                                   dress=dict(BW.DRESS_GUARD_SENTINELS)), lines)[0]]
rest = doc(guard=host(leader=0, leader_model=98, raw=2, effective=2))
out["rest"] = [lg.judge_rest(rest, leader=0, model=98, lever=False)[0],
               lg.judge_rest(doc(guard=host(leader=0, leader_model=98, raw=2, effective=4)), leader=0, model=98,
                             lever=False)[0],
               lg.judge_rest(rest, leader=0, model=98, lever=True)[0], lg.judge_rest(doc(), leader=0, model=98,
                                                                                    lever=False)[0]]
out["party"] = [lg.judge_party(doc(party=[10, 0, 1, 3]), [10, 0, 1, 3])[0],
                lg.judge_party(doc(party=[0, 1, 2, 3]), [10, 0, 1, 3])[0]]
want = lg.seat_want([10, 0, 1, 3], 0)
held = [doc(ghost=(8, 1, 2), dress=dict(want["field"])) for _ in range(4)]
line = BW.guard_field_log(2, 4, 1, 2, 0)
out["field"] = [lg.judge_field(held, want_ghost=(8, 1), want_guard=want["field"], log_lines=[line], want_line=line)[0],
                lg.judge_field(held[:2], want_ghost=(8, 1), want_guard=want["field"])[1][:12],
                lg.judge_field([doc(ghost=(98, 0, 2), dress=dict(want["field"]))] * 4, want_ghost=(8, 1),
                               want_guard=want["field"])[0],
                lg.judge_field([doc(ghost=(8, 1, 2))] * 4, want_ghost=(8, 1), want_guard=want["field"])[0],
                lg.judge_field(held, want_ghost=(8, 1), want_guard=want["field"], log_lines=[line, line],
                               want_line=line)[0],
                lg.judge_field([doc(ghost=(8, 1, -1), dress=dict(want["field"]))] * 4, want_ghost=(8, 1),
                               want_guard=want["field"])[0]]
keys = {"raw": 2, "effective": 4, "moved_from": 1, "moved_to": 2, "chars": [10, 0, 1, 3]}
g4 = host(raw=2, effective=4, moved_from=1, moved_to=2, chars=[10, 0, 1, 3], nonce=7)
out["keys"] = [lg.judge_keys(doc(guard=g4), keys, nonce=7)[0], lg.judge_keys(doc(guard=g4), keys, nonce=8)[0],
               lg.judge_keys(doc(guard=dict(g4, effective=2)), keys, nonce=7)[0], lg.judge_keys(doc(), keys)[0]]
names = [None, "Zidane", "Vivi", "Steiner"]
hl, gl = "Partner: Vivi (not Zidane)", "You: Vivi"
lns = [BW.guard_host_line_log(hl, 2, 4, shown=True, partner=True),
       BW.guard_guest_line_log(gl, 7, 4, shown=False, hud=False)]
good = doc(guard=dict(g4, line=hl, line_shown=True), peer={"nonce": 7, "mask": 4, "line": gl, "shown": False})
out["lines"] = [lg.judge_lines(good, lns, eff=4, moved_from=1, nonce=7, names=names)[0],
                lg.judge_lines(good, lns[:1], eff=4, moved_from=1, nonce=7, names=names)[0],
                lg.judge_lines(good, lns + lns[:1], eff=4, moved_from=1, nonce=7, names=names)[0],
                lg.judge_lines(doc(guard=dict(g4, line=hl, line_shown=False), peer=good["netsync"]["battle"]["peer"]["guard"]),
                               lns, eff=4, moved_from=1, nonce=7, names=names)[0],
                lg.judge_lines(doc(guard=dict(g4, line=hl, line_shown=True),
                                   peer={"nonce": 7, "mask": 2, "line": "You: Zidane", "shown": False}), lns, eff=4,
                               moved_from=1, nonce=7, names=names)[0],
                lg.judge_lines(doc(), lns, eff=4, moved_from=1, nonce=7, names=names)[0]]
w = [(100 + i, s, True) for i, s in enumerate([-1, 3, -1, 1, -1, 3, 1])]
out["windows"] = [lg.judge_windows([(f, s, l) for f, s, l in w], leader_idx=1, guest_idx=2, f0=40)[0],
                  lg.judge_windows(w + [(200, 2, True)], leader_idx=1, guest_idx=2, f0=40)[0],
                  lg.judge_windows([(50, 2, True)] + w, leader_idx=1, guest_idx=2, f0=40)[0],
                  lg.judge_windows([(f, 3, l) for f, s, l in w], leader_idx=1, guest_idx=2, f0=40)[0],
                  lg.judge_windows(w + [(210, 2, False)], leader_idx=1, guest_idx=2, f0=40)[0],
                  lg.judge_windows([], leader_idx=1, guest_idx=2, f0=None)[0],
                  lg.judge_windows(w, leader_idx=1, guest_idx=2, f0=40, ring_first=60)[0],
                  lg.judge_windows(w, leader_idx=1, guest_idx=2, f0=40, ring_first=150)[1][:12]]
out["lanes"] = [lg.judge_lanes([(100, [2], -1), (101, [2], -1)], leader_idx=1, guest_idx=2)[0],
                lg.judge_lanes([(100, [1], -1)], leader_idx=1, guest_idx=2)[0],
                lg.judge_lanes([(100, [2], -1), (101, [1, 2], -1)], leader_idx=1, guest_idx=2)[0],
                lg.judge_lanes([(100, [2], -1), (101, [2], 1)], leader_idx=1, guest_idx=2)[0],
                lg.judge_lanes([(100, [], -1)], leader_idx=1, guest_idx=2)[0],
                lg.judge_lanes([], leader_idx=1, guest_idx=2)[1][:12]]
out["messages"] = [lg.judge_lines(good, lns, eff=4, moved_from=1, nonce=7, names=names, messages=[None, hl])[0],
                   lg.judge_lines(good, lns, eff=4, moved_from=1, nonce=7, names=names, messages=[None, "Attack"])[0],
                   lg.judge_lines(good, lns, eff=4, moved_from=1, nonce=7, names=names, messages=[])[0]]
pb_units = [{"slot": 1, "player": True}, {"slot": 2, "player": True}, {"slot": 3, "player": True}, {"slot": 4, "player": False}]
ap_units = [{"slot": 0, "player": True}] + pb_units
pre = doc(guard=g4, units=pb_units)
post = [doc(guard=g4, units=ap_units, turn=s) for s in (-1, 0, -1)]
out["appear"] = [lg.judge_appear(pre, post, hidden_idx=0)[0],
                 lg.judge_appear(pre, [doc(guard=dict(g4, effective=2), units=ap_units, turn=0)], hidden_idx=0)[0],
                 lg.judge_appear(pre, [doc(guard=g4, units=ap_units, turn=-1)], hidden_idx=0)[0],
                 lg.judge_appear(pre, [doc(guard=g4, units=pb_units + [{"slot": 0, "player": True}], turn=0)],
                                 hidden_idx=0)[0],
                 lg.judge_appear(doc(guard=dict(g4, effective=5), units=pb_units),
                                 [doc(guard=dict(g4, effective=5), units=ap_units, turn=0)], hidden_idx=0)[0],
                 lg.judge_appear(None, post, hidden_idx=0)[1][:12], lg.judge_appear(doc(units=pb_units), post,
                                                                                  hidden_idx=0)[0]]
out["want"] = {str(f): lg.seat_want(p, 0) for f, p in ((30607, [10, 0, 1, 3]), (30608, [2, 0, 1, 3]),
                                                       (30604, [0, 1, 2, 3]))}
out["want_vivi_leader"] = lg.seat_want([10, 0, 1, 3], 1)
out["want_body"] = lg.seat_want([0, 1, 2, 3], 1, me_model=8, wire=lg.BODY_WIRE)
out["want_body_nowire"] = lg.seat_want([0, 1, 2, 3], 1, me_model=8)
out["stage"] = [lg.stage_of(full), lg.stage_of({"netsync": {"dress": {"ghost": {}, "codec": "ok", "self": {"steps": []}}}}),
                lg.stage_of({"netsync": {"dress": {"ghost": {}}}}), lg.stage_of({})]
print(json.dumps(out))
"""


def test_the_judges_go_red_on_each_wrong_shape():
    o = _child(_JUDGES)
    assert o["probe"] == [True, False, False, False]                   # whole / absent / no proof line / torn keys
    assert o["rest"] == [True, False, False, False]                    # at rest / guarded off-battle / lever mis-read / absent
    assert o["party"] == [True, False]
    assert o["field"] == [True, "not reached:", False, False, False, False]   # held, too short, Zidane, no record, 2 lines,
    assert o["keys"] == [True, False, False, False]                    # lever not published (the op never landed)
    assert o["lines"] == [True, False, False, False, False, False]     # one line missing / doubled / not shown / raw header
    assert o["windows"] == [True, False, True, False, True, False,     # Vivi opened / in the grace / Zidane never / not live
                            True, "not reached:"]                      # ...a ring that lost the command phase: not reached
    assert o["lanes"] == [True, False, False, False, False, "not reached:"]   # roster [1] / [1, 2] / held 1 / no [2] / none
    assert o["messages"] == [True, False, False]                       # on screen / another message / none read
    assert o["appear"] == [True, False, False, False, False, "not reached:", False]
    assert o["stage"] == [143, 141, 138, None]


def test_seat_want_is_the_twins_story():
    o = _child(_JUDGES)
    pb, fx, cp = o["want"]["30607"], o["want"]["30608"], o["want"]["30604"]
    assert (pb["chars"], pb["effective"], pb["moved_from"], pb["moved_to"], pb["ghost"]) == (PB, 4, 1, 2, [8, 1])
    assert pb["field"] == {"leader": 0, "raw": 2, "effective": 4, "moved_from": 1, "moved_to": 2}
    assert (fx["chars"], fx["effective"], fx["moved_from"], fx["moved_to"], fx["ghost"]) == (FX, 4, 1, 2, [8, 1])
    assert (cp["chars"], cp["effective"], cp["moved_from"], cp["moved_to"], cp["ghost"]) == (CP, 2, -1, -1, [8, 1])
    assert cp["field"]["moved_from"] == -1 and cp["field"]["effective"] == 2
    # a Vivi leader on the Plant Brain party: bit 1 (Zidane) is not hers -- nothing moves
    assert o["want_vivi_leader"]["effective"] == 2 and o["want_vivi_leader"]["moved_from"] == -1
    # THE LEADER BODY (L10): the kit's Vivi walks COOPPARTY's party -- bit 1 is HER, the field guard moves it to Garnet; on
    # the `wire 98` body GhostGuard dresses (her own body 8 would show as it is)
    b = o["want_body"]
    assert b["ghost"] == [185, 2] and b["field"] == {"leader": 1, "raw": 2, "effective": 4, "moved_from": 1, "moved_to": 2}
    assert o["want_body_nowire"]["ghost"] == [8, -1]


# ------------------------------------------------------------------------------------------------ the seats and the oracle
def _build(tmp_path, *tomls) -> pathlib.Path:
    # the build runs in a CHILD, so a missing blank is a red returncode the conftest's FileNotFoundError -> skip never sees:
    # gate it here (the seats are novel fields -- the templates are all they read, never the install)
    from ff9mapkit import provision
    if not provision.templates_present():
        pytest.skip("base templates not extracted (run `ff9mapkit extract-templates`)")
    out = tmp_path / "FF9CustomMap-msgs"
    r = subprocess.run([sys.executable, "-X", "utf8", "-m", "ff9mapkit", "build", *[str(t) for t in tomls], "--out",
                        str(out)], cwd=str(REPO / "ff9mapkit"), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:] + r.stdout[-2000:]
    return out


_ORACLE = _CHILD + r"""
game = pathlib.Path(doc["game"])
o = lg.read_oracle(game)
b = o["body"]
print(json.dumps({"seats": {str(k): {kk: v[kk] for kk in ("party", "chars", "effective", "moved_from", "moved_to", "ghost")}
                            for k, v in o["seats"].items()}, "leader": o["leader"], "model": o["model"],
                  "body": None if b is None else {k: b[k] for k in ("party", "leader", "model", "ghost", "field")},
                  "problems": o["problems"],
                  "ops": {str(f): lg.eb_party_ops(lg.deployed_eb(game, f)[0]) for f in (30604, 30607, 30608)
                          if lg.deployed_eb(game, f)[0] is not None},
                  "toml": {str(f): [list(x) for x in lg.toml_party(lg.TOMLS[f])[0]] for f in (30604, 30607, 30608)}}))
"""


def test_the_seats_are_field_257_and_261_built_by_the_kit_and_the_oracle_reads_them(tmp_path):
    """The seat tomls through the kit's own resolver are field 257's and 261's parties; the kit's BUILD prepends exactly
    their RemoveParty / B_PARTYADD sequence to Main_Init (removes first, then the adds in order -- disassembled off the
    built `.eb`); read_oracle on that build (a stacked mod folder, Memoria.ini's FolderNames) seats [10, 0, 1, 3] /
    [2, 0, 1, 3] / [0, 1, 2, 3] with the kit Zidane (98) the leader; a seat whose Main_Init differs reads STALE, a seat
    not deployed is named -- never a silent green."""
    game = tmp_path / "game"
    game.mkdir()
    mod = _build(game, BENCH / "coopparty.field.toml", BENCH / "plantbrain.field.toml", BENCH / "forestexit.field.toml",
                 BENCH / "vivibody.field.toml")
    (game / "Memoria.ini").write_text('[Mod]\nFolderNames = "FF9CustomMap", "FF9CustomMap-msgs"\n', encoding="utf-8")
    o = _child(_ORACLE, {"game": str(game)})
    assert o["problems"] == {} and o["leader"] == 0 and o["model"] == 98
    assert o["seats"]["30607"]["party"] == PB and o["seats"]["30608"]["party"] == FX and o["seats"]["30604"]["party"] == CP
    # the leader-body seat: no party op (COOPPARTY's party), the kit's Vivi (8) its player -> leader 1, the mirror Garnet
    assert o["body"] == {"party": CP, "leader": 1, "model": 8, "ghost": [185, 2],
                         "field": {"leader": 1, "raw": 2, "effective": 4, "moved_from": 1, "moved_to": 2}}
    every = [BW.OLD_INDEX_TO_ID[i] for i in range(12)]                # the twelve, as CharacterIds (Beatrix 11, Cinna 8 ...)
    assert sorted(every) == list(range(12))
    assert o["toml"]["30607"] == [every, PB] and o["toml"]["30608"] == [every, FX]
    assert o["toml"]["30604"] == [[], [1, 2, 3]]
    assert o["ops"]["30607"] == [["remove", i] for i in range(12)] + [["add", i] for i in (11, 0, 1, 3)]
    assert o["ops"]["30608"] == [["remove", i] for i in range(12)] + [["add", i] for i in (2, 0, 1, 3)]
    # STALE: 30607's .eb swapped for 30608's -- its Main_Init is not the toml's
    evt = mod / "StreamingAssets" / "assets" / "resources" / "commonasset" / "eventengine" / "eventbinary" / "field" / "us"
    (evt / "EVT_COOPPBRAIN.eb.bytes").write_bytes((evt / "EVT_COOPFOREST.eb.bytes").read_bytes())
    o = _child(_ORACLE, {"game": str(game)})
    assert "30607" not in o["seats"] and o["problems"]["eb 30607"].startswith("STALE:")
    (evt / "EVT_COOPFOREST.eb.bytes").unlink()
    o = _child(_ORACLE, {"game": str(game)})
    assert "no stacked mod folder registers it" in o["problems"]["eb 30608"]


def test_the_seat_tomls_name_their_story_fields_and_free_ids():
    for name, fid, story in (("plantbrain.field.toml", 30607, "field 257"), ("forestexit.field.toml", 30608, "field 261")):
        text = (BENCH / name).read_text(encoding="utf-8")
        assert f"id = {fid}" in text and story in text and f"--id {fid} --mod-folder FF9CustomMap-msgs" in text
        assert 'remove = ["zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant", "beatrix", "cinna", ' \
               '"marcus", "blank"]' in text
    assert 'add = ["blank", "zidane", "vivi", "steiner"]' in (BENCH / "plantbrain.field.toml").read_text(encoding="utf-8")
    assert 'add = ["garnet", "zidane", "vivi", "steiner"]' in (BENCH / "forestexit.field.toml").read_text(encoding="utf-8")
    body = (BENCH / "vivibody.field.toml").read_text(encoding="utf-8")
    assert "id = 30609" in body and "\nmodel = 8\n" in body and "[party]" not in body
    assert "--id 30609 --mod-folder FF9CustomMap-msgs" in body


# ------------------------------------------------------------------------------------------------ the twins vs the patch
def _patch_text() -> str:
    return (msr.PATCHES / PATCH).read_bytes().decode("utf-8", "replace")


def test_the_log_line_twins_are_the_engines_text():
    """Every line the bench counts is the twin's text, and the twin's text is the s143 patch's (fragment by fragment)."""
    p = _patch_text()
    for frag in ('"[NetSync] leader guard (field dress): " + what', '"GuestSlots 0x" + (mask & 0x0F).ToString("X") + " -> 0x"',
                 '" is the leader " + NetSyncBattle.GuardCharName(leader) + (to >= 0 ? "; the ghost dresses as party slot "',
                 '"\'s member" : "; no other member is free: the guest spectates") + ")";',
                 '"[NetSync] leader guard line (host): \\"" + line + "\\" -- " + (_guardLineShown',
                 '"in the battle message window" : partner ? "no battle HUD: the log only" : "no guest lane: the log only")',
                 '" (GuestSlots 0x" + (GuestSlots & 0x0F).ToString("X") + " -> 0x" + eff.ToString("X") + "; once per own battle)"',
                 '"[NetSync] leader guard line (guest): \\"" + _youLine + "\\" -- the host\'s battle (nonce " + view.Nonce',
                 '"in the diorama\'s battle message window"', '"a spectator: the log only"',
                 '"no booted diorama: the log only"', '"the selftest loopback: the log only") + " (once per host battle)"',
                 '"[NetSync] harness: leader guard back ON (released with the harness)"',
                 '"OFF -- CALIBRATION: the pre-s143 positional rule (a guest bit may name the host\'s leader, in battle and at the "',
                 '"field dress sites)"', '"leader guard: the host-side leader is now "',
                 '" -- a guest bit landing on it moves to the next member (owner, 2026-10-19)"',
                 '", my controlled body\'s model " + model + ")"', '"NONE (my controlled body\'s model " + model + ")")',
                 '"leader guard: my controlled body\'s model " + model + " names no character -- the leader stays "',
                 '"none known (the positional rule)"', '", the world map: Zidane\'s party walks it)"',
                 '", the world map: Dagger walks it)"', '"[NetSync] " + LeaderLogText(_leaderChar, model, _leaderChar != was)',
                 '"leader guard: the leader is forgotten at the title (a load starts afresh: the next "',
                 '" (own battle nonce " + _battleNonce + ")"',
                 '" over the battle\'s units ["', '" -- index ").Append(from).Append(" is the leader: the guest commands "',
                 '" is the leader and no other member is free: the bit drops (the guest spectates it)"', '" -- unmoved"',
                 '"OFF (the `bench leaderguard off` lever: the positional rule)"', '"none known"',
                 '"[NetSync] leader guard selftest: "'):
        assert frag in p, frag
    assert BW.guard_field_log(2, 4, 1, 2, 0) == ("leader guard (field dress): GuestSlots 0x2 -> 0x4 (party slot 1 is the "
                                                  "leader Zidane; the ghost dresses as party slot 2's member)")
    assert BW.guard_latch_line(PB, 2, 0, 4, 1, 2, 5) == (
        "leader guard: GuestSlots 0x2 over the battle's units [Blank, Zidane, Vivi, Steiner], leader Zidane -> 0x4 -- "
        "index 1 is the leader: the guest commands Vivi (index 2) instead (own battle nonce 5)")
    assert BW.guard_latch_line([0, -1, -1, -1], 1, 0, 0, 0, -1, 2).endswith(
        "-- index 0 is the leader and no other member is free: the bit drops (the guest spectates it) (own battle nonce 2)")
    assert "leader OFF (the `bench leaderguard off`" in BW.guard_latch_line(PB, 2, -1, 2, -1, -1, 1, guard_on=False)
    assert BW.LOG_LEADER_FORGOTTEN == ("leader guard: the leader is forgotten at the title (a load starts afresh: the next "
                                       "field body or the world map latches it)")
    assert BW.guard_leader_log(0, 615, changed=False) == ("leader guard: my controlled body's model 615 names no character "
                                                          "-- the leader stays Zidane (CharacterId 0)")
    assert BW.guard_leader_log(-1, 615, changed=False).endswith("the leader stays none known (the positional rule)")
    assert BW.LOG_GUARD_OFF.startswith("harness: leader guard OFF -- CALIBRATION")
    assert [BW.guard_char_name(c) for c in (-1, -2, 0, 10, 11, 12)] == ["-", "?", "Zidane", "Blank", "Beatrix", "#12"]


_FIELD_ROW = re.compile(r'GuardRow\((\w+) == (\d+) && rig == (-?\d+)(?: && from == (-?\d+) && to == (-?\d+))?,')


def test_the_engines_field_and_lever_rows_hold_on_the_twins_and_each_mutant_fails_its_row():
    """LeaderGuardSelfTest's field-composition rows (the guard over the RAW slots, then ResolveAuto; the client's s138 rule
    untouched) and its lever row, EVALUATED on battlewire's twins -- and a twin without the guard, one that guards the s138
    rule too, and a lever that unguards a host each fail their own row."""
    body = " ".join(net_lines("NetSyncBattle.cs", r"."))
    rows = _FIELD_ROW.findall(body)
    assert [r[0] for r in rows] == ["vivi", "mog", "s138"], rows
    assert "Int32[] f257 = { 10, 0, 1, 3 };" in body and "Int32[] solo = { 0, -1, -1, -1 };" in body
    assert 'NetSyncVisitor.ResolveDressS138("auto", 0x2, f257, out rig);' in body

    def field(rule_guard=True, s138_guarded=False):
        f257, solo = [10, 0, 1, 3], [0, -1, -1, -1]
        g = (lambda c, m: BW.leader_guard(c, m, 0)) if rule_guard else (lambda c, m: (m, -1, -1))
        e1, f1, t1 = g(f257, 2)
        e2, f2, t2 = g(solo, 1)
        s = BW.resolve_dress_s138("auto", g(f257, 2)[0] if s138_guarded else 2, f257)
        return {"vivi": (*BW.resolve_auto(e1, True, f257), f1, t1), "mog": (*BW.resolve_auto(e2, True, solo), f2, t2),
                "s138": s}

    want = {name: tuple(int(x) for x in vals if x != "") for name, *vals in rows}
    got = field()
    assert {k: tuple(v) for k, v in got.items()} == want
    assert tuple(field(rule_guard=False)["vivi"]) != want["vivi"]           # no guard: Zidane at Plant Brain
    assert tuple(field(s138_guarded=True)["s138"]) != want["s138"]          # the client's rule must stay raw
    m = re.search(r"GuardRow\(LeaderGuardOnRule\(false, false\) && LeaderGuardOnRule\(false, true\) && "
                  r"LeaderGuardOnRule\(true, false\)\s+&& !LeaderGuardOnRule\(true, true\),", body)
    assert m, "the lever row moved"
    table = [(False, False), (False, True), (True, False), (True, True)]
    assert [BW.leader_guard_on_rule(*r) for r in table] == [True, True, True, False]
    assert [(not b) for b, _r in table] != [BW.leader_guard_on_rule(*r) for r in table]   # "off whenever pulled" fails


def test_the_battle_mask_twin_gates_like_the_getter():
    """EffectiveGuestSlots: GuestSlots outside an own battle and before LOAD_INITCHR; the guard inside; 0 stays 0; the
    lever's LeaderForGuard (none on the selftest role only) gives the positions back."""
    assert BW.effective_guest_slots(2, own_battle=False, organized=True, slot_char=PB, leader=0) == (2, -1, -1)
    assert BW.effective_guest_slots(2, own_battle=True, organized=False, slot_char=PB, leader=0) == (2, -1, -1)
    assert BW.effective_guest_slots(2, own_battle=True, organized=True, slot_char=PB, leader=0) == (4, 1, 2)
    assert BW.effective_guest_slots(0x12, own_battle=True, organized=True, slot_char=PB, leader=0) == (4, 1, 2)
    assert BW.effective_guest_slots(0, own_battle=True, organized=True, slot_char=PB, leader=0) == (0, -1, -1)
    assert BW.leader_for_guard(0, True, True) == BW.LEADER_NONE and BW.leader_for_guard(0, True, False) == 0
    body = " ".join(net_lines("NetSyncBattle.cs", r"."))
    for frag in ("if (raw == 0 || !_guardOwnBattle)", "get { return LeaderGuardOn ? _leaderChar : LeaderNone; }"):
        assert frag in body, frag


def test_section_8_and_the_mirror_site_take_the_leader():
    """battlewire's HostDressSection and selftest-site twins guard `auto` with the leader (the default -1: every pre-s143
    caller reads as before); `coop_peer.py dress --leader` hands it in, and refuses it for an s139 tape."""
    assert BW.host_dress_section("auto", 2, "host", False, PB, leader=0) == bytes((8, 0, 1))      # Vivi
    assert BW.host_dress_section("auto", 2, "host", False, PB) == bytes((98, 0, 0))               # the positional Zidane
    assert BW.host_dress_section("auto", 2, "host", False, CP, leader=0) == bytes((8, 0, 1))      # COOPPARTY: no move
    assert BW.host_dress_section("vivi", 1, "host", False, PB, leader=0) == bytes((8, 0, 1))      # a name reads no mask
    assert BW.host_dress_section("auto", 1, "host", False, [0, -1, -1, -1], leader=0) == bytes((220, 0, 0xFF))  # drop: D2
    me = dict(me_model=98, me_anim=200, guest_slots=0, bench_mask=2)
    assert BW.selftest_dress(ghost_as="auto", party=PB, leader=0, **me)["model"] == 8
    assert BW.selftest_dress(ghost_as="auto", party=PB, **me)["model"] == 98
    assert BW.selftest_dress(ghost_as="auto", party=PB, leader=0, rule="s138", **me)["model"] == 98   # the s138 site
    from harness import coop_peer as CPR
    args = CPR.build_parser().parse_args(["dress", "x.f9tape", "--ghost-as", "auto", "--guest-slots", "2", "--party",
                                          "10,0,1,3", "--leader", "0"])
    assert CPR._dress_expect(args) == bytes((8, 0, 1))
    args = CPR.build_parser().parse_args(["dress", "x.f9tape", "--ghost-as", "auto", "--guest-slots", "2", "--party",
                                          "10,0,1,3"])
    assert CPR._dress_expect(args) == bytes((98, 0, 0))
    args = CPR.build_parser().parse_args(["dress", "x.f9tape", "--ghost-as", "auto", "--guest-slots", "2", "--leader", "0",
                                          "--stage", "s139"])
    with pytest.raises(ValueError, match="s139"):
        CPR._dress_expect(args)


# ------------------------------------------------------------------------------------------------ THE PREMISE CENSUS
#: every bench that hands the loopback guest a party position: (scenario, the masks it sends, the party it seats them over,
#: whether the GUARD moves a bit there with the kit Zidane the leader). A moving premise must be RE-KEYED (the bench pulls
#: `bench leaderguard off` on an engine with `host.guard`); a neutral one is the guard's own no-op.
PREMISES = {
    "coop_battle_host_gates.py": ({2}, CP), "coop_battle_handback.py": ({0, 2}, CP), "coop_handback_live.py": ({2}, CP),
    "coop_battle_end_host.py": ({0, 2, 15}, CP), "coop_battle_containment.py": ({1}, None),   # field + diorama only
    "coop_battle_start_hold.py": ({0}, CP), "coop_battle_wait_parity.py": ({0, 15}, CP),
    "coop_battle_flee_defeat.py": ({0}, CP),
    "coop_session_edges.py": ({2}, CP),   # [s153] host_gates' premise: slot 1 over COOPPARTY, Zidane leading -- guard-neutral
}
REKEYED = {"coop_battle_wait_parity.py", "coop_battle_end_host.py"}
#: every route a scenario can send `netsync guestslots <mask>` by (review s143: `cb.ns_verb` and `g.netsync` too)
_GS_SENDS = (r'(?:try_ns|ns_verb)\(g, "guestslots", (\w+)\)', r'\.netsync\("guestslots", (\w+)\)',
             r'"netsync guestslots (\w+)"')


def _guestslots_sent(texts: dict) -> dict:
    sent = {}
    for name, text in sorted(texts.items()):
        masks = {int(m, 0) if not m.isidentifier() else m for rx in _GS_SENDS for m in re.findall(rx, text)}
        if masks:
            sent[name] = masks
    return sent


def _scenario_texts() -> dict:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(SCENARIOS.glob("*.py"))}


def test_every_guestslots_premise_is_guard_neutral_or_rekeyed():
    """THE PREMISE CENSUS (a later patch can turn an earlier bench's invariant into a stage fact): every `guestslots <mask>`
    a scenario sends -- by any route (`try_ns`, `ns_verb`, `g.netsync`, a raw send) -- is in PREMISES (a new one turns this
    red until it is judged); each mask over its seated party is the guard's no-op -- or the bench is in REKEYED and pulls
    `bench leaderguard off` on an engine that publishes `netsync.battle.host.guard` (wait_parity's and end_host leg G's
    `guestslots 15`: Zidane's position 0 is a guest bit). The containment bench's mask never meets an own battle (the field
    and a diorama: the getter's GuestSlots)."""
    texts = _scenario_texts()
    sent = _guestslots_sent(texts)
    sent.pop("coop_leader_guard.py")                                  # the s143 bench itself
    consts = {"ALL_SLOTS": 15, "GUEST_SLOTS": 2}
    sent = {k: {consts.get(m, m) for m in v} for k, v in sent.items()}
    assert set(sent) == set(PREMISES), set(sent) ^ set(PREMISES)
    for name, (masks, party) in PREMISES.items():
        assert sent[name] == masks, (name, sent[name])
        moves = party is not None and any(BW.leader_guard(BW.battle_slot_chars(party), m, 0)[1] >= 0 for m in masks)
        text = (SCENARIOS / name).read_text(encoding="utf-8")
        if moves:
            assert name in REKEYED, f"{name}: a mask moves under the guard and the bench is not re-keyed"
            assert 'cb.try_ns(g, "bench", "leaderguard", "off")' in text and "netsync.battle.host.guard" in text, name
            assert "[ff9mapkit netsync s143 re-key]" in text, name
        else:
            assert name not in REKEYED, name


def test_the_guestslots_census_sees_every_route():
    """The instrument can fail: a mask sent through `ns_verb`, `g.netsync` or a raw send is counted (an `ns_verb` the old
    scan missed: coop_battle_handback's `cb.ns_verb(g, "guestslots", 2)`), and a NEW one turns the census red."""
    texts = _scenario_texts()
    assert 'cb.ns_verb(g, "guestslots", 2)' in texts["coop_battle_handback.py"]
    probe = {"a.py": 'x = cb.ns_verb(g, "guestslots", 1)', "b.py": 'g.netsync("guestslots", 8)',
             "c.py": 'g.send("netsync guestslots 4")', "d.py": 'cb.try_ns(g, "guestslots", ALL)'}
    assert _guestslots_sent(probe) == {"a.py": {1}, "b.py": {8}, "c.py": {4}, "d.py": {"ALL"}}
    texts["coop_battle_host_gates.py"] += '\ncb.ns_verb(g, "guestslots", 1)\n'
    assert _guestslots_sent(texts)["coop_battle_host_gates.py"] != PREMISES["coop_battle_host_gates.py"][0]


#: THE FIELD-LEVER CENSUS (review s143 field-3): every mask a scenario hands a field dress site -- the selftest mirror's
#: `selfdress ghost` (leg G's `("ghost", <expr>)` ops, leg S8's `_s_send(g, ctx, "ghost", <expr>)`, the s143 bench's own
#: `"selfdress", "ghost", <expr>`), the `selfdress self auto <mask>` bench (`_s_load(..., f"auto {<expr>}")`: UNGUARDED in
#: the engine -- the pre-s143 host rule) and duo G9's GuestSlots phases -- as SOURCE expressions, per file and kind. A new one
#: turns this red until it is judged below.
FIELD_LEVERS = {
    "coop_self_dress.py": {"ghost": {"0", "1 << s1", "1 << slot", "2", "6", "bit"}, "self_auto": {"S_AUTO_MASK", "bit"}},
    "coop_dress_wire.py": {"g9": {"0", "2", "4"}},
    "coop_leader_guard.py": {"sd_ghost": {"GUEST_SLOTS"}},
}
_FIELD_RX = {"ghost": (r'\("ghost", (?!")([^)\]]+)\)', r'_s_send\(g, ctx, "ghost", (\w+)\)'),
             "self_auto": (r'_s_load\(g, ctx, field, f"auto \{(\w+)\}"',),
             "g9": (r'\("S139-G9[a-z]", (\d+)',),
             "sd_ghost": (r'"selfdress", "ghost", (\w+)',)}


def _field_levers(texts: dict) -> dict:
    out = {}
    for name, text in sorted(texts.items()):
        kinds = {k: {m.strip() for rx in rxs for m in re.findall(rx, text)} for k, rxs in _FIELD_RX.items()}
        kinds = {k: v for k, v in kinds.items() if v}
        if kinds:
            out[name] = kinds
    return out


def test_every_field_lever_mask_is_judged_through_the_leader():
    """THE FIELD HALF of the census (review s143 field-3): the masks are exactly FIELD_LEVERS (a new one is red), and each
    kind is judged with the guard: leg G / S8's expectation (coop_self_dress.want_ghost) and G9's (phase_bodies,
    want_host_ghost, judge_tape) thread the leader the engine takes NOW (cb.guard_leader: none before s143 or under the
    lever), so a mask that seats the leader is predicted as the guard moves it; the UNGUARDED `self auto` bench may only send
    masks that are the guard's no-op over the party it seats (S3: `auto 2` + `empty 2` -- slot 1 emptied; S7: Blank's bit
    on COOPSUB's [Zidane, Vivi, Garnet, Blank])."""
    texts = _scenario_texts()
    assert _field_levers(texts) == FIELD_LEVERS
    sd, dw, cbt = texts["coop_self_dress.py"], texts["coop_dress_wire.py"], texts["_coop_battle.py"]
    assert "lead = cb.guard_leader(x) if rules is None or rules is BW else -1" in sd and "**kw)" in sd
    assert "def guard_leader(x) -> int:" in cbt and 'g.get("off") is True' in cbt
    for frag in ("def phase_bodies(host_party, slots, leader: int = -1) -> list:",
                 "wants = phase_bodies(host_party, slots, leader)",
                 "mask = BW.field_guard_mask(HOST_GHOST_AS, int(guest_slots), chars, int(leader))[0]",
                 "lead = cb.guard_leader(host.state)", "judge_tape(records, host_party, stepped, lead)",
                 "guest_slots=slots, leader=lead,"):
        assert frag in dw, frag
    # the `self auto` bench (unguarded): each mask neutral over its seat
    assert "S_AUTO_MASK = 2 " in sd and '("empty", S_AUTO_MASK)' in sd
    assert BW.field_guard_mask("auto", 2, BW.live_slot_chars(CP, 2), 0)[1] == (-1, -1)        # S3: slot 1 emptied
    sub_party = [0, 1, 2, 10]                                                                  # COOPSUB: Blank at 3
    assert BW.field_guard_mask("auto", 1 << sub_party.index(10), sub_party, 0)[1] == (-1, -1)  # S7: Blank's bit
    # G9 at COOPPARTY: guard-neutral (the duo's premise) -- the threading is what keeps a moving phase honest
    assert all(BW.host_dress_section("auto", m, "host", False, CP, leader=0) == BW.host_dress_section(
        "auto", m, "host", False, CP) for m in (0, 2, 4))


def test_the_field_lever_census_can_fail():
    texts = _scenario_texts()
    texts["coop_self_dress.py"] += '\nled.check("S139-G9z", *_g_try(g, ctx, field, [("ghost", 1)]))\n'
    assert _field_levers(texts) != FIELD_LEVERS
    texts = _scenario_texts()
    texts["coop_dress_wire.py"] += '\n    ("S139-G9g", 1, False),\n'
    assert _field_levers(texts) != FIELD_LEVERS
    texts = _scenario_texts()
    texts["coop_self_dress.py"] += '\n    ld = _s_load(g, ctx, field, f"auto {other}")\n'
    assert _field_levers(texts) != FIELD_LEVERS


_THREAD = _CHILD + r"""
sys.path.insert(0, scen)
import _coop_battle as cb
import coop_self_dress as sd
import coop_dress_wire as dw
def doc(guard, party):
    d = {"player": {"model": 98, "anim": 0}, "netsync": {"dress": {"party": party}}}
    if guard is not None:
        d["netsync"]["battle"] = {"host": {"guard": guard}}
    return d
lv = dict(sd.LEVERS_OFF, mask=2)
pb = [10, 0, 1, 3]
out = {"leader": [cb.guard_leader(doc({"leader": 0, "off": False}, pb)), cb.guard_leader(doc({"leader": 0, "off": True}, pb)),
                  cb.guard_leader(doc(None, pb)), cb.guard_leader(doc({"leader": -1, "off": False}, pb))],
       "ghost": [sd.want_ghost(doc({"leader": 0, "off": False}, pb), lv, "auto")["model"],
                 sd.want_ghost(doc({"leader": 0, "off": True}, pb), lv, "auto")["model"],
                 sd.want_ghost(doc(None, pb), lv, "auto")["model"]],
       "bodies": [list(b) for b in dw.phase_bodies(pb, [2], 0) + dw.phase_bodies(pb, [2])],
       "host_ghost": [dw.want_host_ghost(pb, 98, 0, 2, 0)["model"], dw.want_host_ghost(pb, 98, 0, 2)["model"]]}
print(json.dumps(out))
"""


def test_the_dress_benches_thread_the_leader_into_their_twins():
    """(review s143 field-3 a) On the Plant Brain party with GuestSlots 2: the selftest site's expectation (want_ghost) and
    G9's (phase_bodies, want_host_ghost) follow the leader the engine publishes -- Vivi (8) with `host.guard` {leader 0},
    the positional Zidane (98) under the lever or before s143."""
    o = _child(_THREAD)
    assert o["leader"] == [0, -1, -1, -1]
    assert o["ghost"] == [8, 98, 98]
    assert o["bodies"] == [[8, 0, 1], [98, 0, 0]]
    assert o["host_ghost"] == [8, 98]


def test_the_rekeyed_benches_release_and_read_the_lever_back():
    wp = (SCENARIOS / "coop_battle_wait_parity.py").read_text(encoding="utf-8")
    assert 'GUARD_REL = "leader guard back ON (released with the harness)"' in wp and GUARD_REL_IN(wp)
    assert '(not ctx.p143 or (cb.host(rr).get("guard") or {}).get("off") is False)' in wp
    assert "ctx.p143 = cb.has(g.state, P143)" in wp and 'P143 = "netsync.battle.host.guard"' in wp
    eh = (SCENARIOS / "coop_battle_end_host.py").read_text(encoding="utf-8")
    k = eh.index('cb.try_ns(g, "guestslots", 15)')
    assert eh.index('cb.has(g.state, "netsync.battle.host.guard")', k) < eh.index("g.start_battle(cb.SCENE)", k)


def GUARD_REL_IN(text: str) -> bool:
    return "((GUARD_REL,) if ctx.p143 else ())" in text


# ------------------------------------------------------------------------------------------------ the runners
def test_the_s143_runners_name_every_step():
    """cal143 deploys the two NEW seats only under DEPLOY=yes (the owner's yes) and then STOPs for the relaunch (a new id
    registers at launch); it STOPs on any DLL but s141's and on a seat preflight that is not CLEAN, then calibrates the
    bench on s141. full143 proves s143 (S143_DLL): the bench, the lever, block A (wait_parity re-keyed), the s139-s141 dress
    bench + its blank-GhostAs pass, the duo G9, a fresh tape's section 8 checked with `--leader 0`, the tape and T2 legs.
    Both export SELFTEST_WT so the selftest blocks run THIS checkout's scenarios; every output outside the repo."""
    cal = (RUN / "cal143.example.sh").read_text(encoding="utf-8")
    full = (RUN / "full143.example.sh").read_text(encoding="utf-8")
    for text in (cal, full):
        # WT defaults to the checkout the runner lives in (run -> bench -> battle-coop -> studies -> the repo), WT= overrides:
        # a worktree path baked in STOPs every run once that worktree is gone (review s143)
        assert 'D="$(dirname "$0")"; WT="${WT:-$(cd "$D/../../../.." && pwd)}"' in text
        assert "/.claude/worktrees/" not in text
        assert "scratchpad" not in text and 'export SELFTEST_WT="$WT"' in text
        assert 'cd "$WT" || { echo "STOP: WT=$WT is missing' in text
        assert "OUT=/c/gd/Dream-World-IX/.harness-runs/s143" in text and "lg.read_oracle(" in text
        assert "controllers OFF (THE UNATTENDED LAW" in text
    k = cal.index("py -X utf8 tools/deploy_field.py studies/battle-coop/bench/plantbrain.field.toml --id 30607")
    assert cal.rfind('if [ "${DEPLOY:-}" = yes ]; then', 0, k) > cal.rfind("\nfi", 0, k), "an ungated deploy"
    assert (RUN / ".." / ".." / ".." / "..").resolve() == REPO
    assert "forestexit.field.toml --id 30608 --mod-folder FF9CustomMap-msgs" in cal
    assert "vivibody.field.toml --id 30609 --mod-folder FF9CustomMap-msgs" in cal and "for f in 30607 30608 30609; do" in cal
    # cal143 STEP 2: an s141 seat tape -- the s143 checks RED there, their positional twins green
    for frag in ("env COOP_TAPE_SEAT=30607", 'offer "$T" --want 4', 'offer "$T" --want 2',
                 '--ghost-as auto --guest-slots 2 --leader 0', "(want 1: s141 offers the raw mask)",
                 "(want 1: s141 ships Zidane 62 00 00)"):
        assert frag in cal, frag
    assert cal.index('bash "$SB"') < cal.index("env COOP_TAPE_SEAT=30607")
    assert "RELAUNCH the game" in cal and "DEPLOY=yes bash $0" in cal and "DEPLOY unset: NOTHING deployed" in cal
    assert 'if [ "$DLL" != 0293cb46ffa176f6 ]; then' in cal
    assert cal.index("lg.read_oracle(") < cal.index('bash "$SB"')
    assert '"leaderguard_cal141:30602:coop_leader_guard:COOP_CALIBRATE=1"' in cal
    assert 'if [ -z "${S143_DLL:-}" ]; then' in full and '[ "$DLL" != "$S143_DLL" ]' in full and "0293cb46ffa176f6" in full
    for frag in ('"leaderguard:30602:coop_leader_guard"', '"leaderguard_lever:30602:coop_leader_guard:COOP_CALIBRATE=1"',
                 '"wait_parity:30602:coop_battle_wait_parity"', '"host_gates:30602:coop_battle_host_gates"',
                 '"selfdress:250:coop_self_dress"', '"selfdress_noghost:250:coop_self_dress:COOP_DRESS_LEGS=I+G+S+F"',
                 "coop_dress_wire.py", "coop_tape_record.py", "--guest-slots 2 --leader 0", "replaytape holdtape",
                 "COOP_CUT_LEG=$l", "for f in 30602 30604 30605 30606 30607 30608 30609; do",
                 "env COOP_TAPE_SEAT=30607", "(want 0: the guarded offer)", "(want 0: 08 00 01, Vivi)",
                 "dress (positional) exit $? (want 1)"):
        assert frag in full, frag
    assert "deploy_field.py" not in full                              # full143 deploys nothing
    for name in ("selftest_block.sh", "selftest_block_noghost.sh"):
        text = (RUN / name).read_text(encoding="utf-8")
        assert 'WT="${SELFTEST_WT:-$WT}"' in text
        assert text.index('WT="${SELFTEST_WT:-$WT}"') < text.index('cd "$WT" ||')


@pytest.mark.parametrize("ini,why", [("[Hacks]\nAllCharactersAvailable = 2\n", "AllCharactersAvailable '2'"),
                                     ("[Hacks]\nAllCharactersAvailable = x\n", "does not parse"),
                                     ("[Netsync]\nEnabled = 1\n", "Enabled '1'")])
def test_the_ini_gate_reads_red_and_stops_the_bench(ini, why):
    """S143-INI can fail (review s143): AllCharactersAvailable >= 2 (every RemoveParty a no-op), a value that does not parse
    (the engine's reading unknown -- it read 0, green, before) and [Netsync] Enabled 1 each turn it red, and nothing after
    it is judged green (the seats cannot be trusted)."""
    r = _child(_RUNS, {"runs": {"ini": {"ini": ini}}})["ini"]
    assert "S143-INI" in r["red"] and why in r["detail"]["S143-INI"], r["detail"].get("S143-INI")
    green = set(r["all"]) - set(r["red"])
    assert green <= {"S143-R"}, green
    assert all("not reached" in r["detail"][c] or "refuses" in r["detail"][c]
               for c in set(r["red"]) - {"S143-INI"}), {c: r["detail"][c] for c in r["red"]}


@pytest.mark.parametrize("status,want", [(1, (4, 1, 2)), (2, (2, -1, -1))])
def test_the_stand_in_world_map_battle_after_a_load_guards_the_walker(tmp_path, status, want):
    """(review s143 own-1) A world-map battle after a load, no field seen: the TITLE forgets the latch, the WORLD MAP latches
    its walker (status 1 Zidane's party -> Zidane; 2 Dagger -> Garnet), and the battle over the forest-exit party [Garnet,
    Zidane, Vivi, Steiner] with GuestSlots 2 moves the bit off Zidane (0x4) -- or, with Dagger walking, leaves it (Zidane is
    not the leader then)."""
    game = _game(tmp_path)
    fake = _fake(game)
    with _session(game, fake) as g:
        _seated(g, 30608)
        g.wait_for(lambda s: s.coop_guard_leader == 0, timeout=4.0, what="the field latch")
        fake.ui_state = "Title"                                       # a load passes the title
        g.wait_for(lambda s: s.coop_guard_leader == -1 and s.coop_guard_leader_model == -1, timeout=4.0,
                   what="the title forgets the latch")
        fake.world_status = status
        fake.ui_state = "WorldHUD"                                    # ...and lands on the world map
        model = BW.world_walker_model(status)
        g.wait_for(lambda s: s.coop_guard_leader_model == model, timeout=4.0, what="the world map's walker")
        assert g.state.coop_guard_leader == BW.next_leader(-1, model) == (0 if status == 1 else 2)
        log = _log(fake)
        assert log.count(BW.LOG_LEADER_FORGOTTEN) == 1 and BW.guard_leader_log(BW.next_leader(-1, model), model) in log
        fake.start_battle(67, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce, timeout=10.0,
                        what="the own battle's latch")
        assert st.coop_guard_chars == FX
        assert (st.coop_guard_effective, st.coop_guard_moved_from, st.coop_guard_moved_to) == want


def test_the_stand_in_keeps_the_leader_on_a_body_naming_no_character(tmp_path):
    """(review s143 field-1) Chocobo's Air Garden's shape: the host walks a body naming no character (Chocobo Gold, 615)
    -- the latch KEEPS Zidane (one 'names no character' line), so the next battle over the forest-exit party still moves the
    bit off him; the `leader_none`-style overwrite (the pre-review latch, battlewire.mutant_next_leader_overwrite) would not."""
    game = _game(tmp_path)
    fake = _fake(game)
    fake.field_player_models = {**BODY, 30602: 615}
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(30604)
        g.wait_for(lambda s: s.coop_guard_leader == -1 or s.coop_guard_leader == 0, timeout=2.0, what="a read")
        g.warp(30608)
        g.netsync("selftest", 1)
        g.wait_for(lambda s: s.coop_guard_leader == 0 and s.coop_guard_leader_model == 98, timeout=4.0, what="Zidane")
        g.warp(30602)
        st = g.wait_for(lambda s: s.coop_guard_leader_model == 615, timeout=4.0, what="the chocobo body")
        assert st.coop_guard_leader == 0
        assert _log(fake).count(BW.guard_leader_log(0, 615, changed=False)) == 1
        g.netsync("guestslots", 2)
        fake.start_battle(67, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce, timeout=10.0,
                        what="the own battle's latch")
        assert (st.coop_guard_effective, st.coop_guard_moved_from, st.coop_guard_moved_to) == (4, 1, 2)
    assert BW.mutant_next_leader_overwrite(0, 615) == -1 != BW.next_leader(0, 615)


def _battle_rec(t, seq, nonce, slots, ready, cp_mod):
    import struct
    head = struct.pack("<HHBBBBBHB", seq & 0xFFFF, 67, slots, 0, 0, 0x03, nonce, 7, 2)
    units = b""
    for idx, player, name in ((0, True, b"Zidane"), (4, False, b"Goblin")):
        info = (1 if player else 0) | 2 | (4 if (ready and player) else 0)
        units += bytes([idx, info]) + struct.pack("<IIIIHH", 100, 100, 10, 10, 0, 100) + bytes([len(name)]) + name + b"\x00"
    return cp_mod.Record(t, cp_mod.DIR_HOST, cp_mod.build_frame(cp_mod.TYPE_BATTLE, head + units))


def test_coop_peer_offer_reads_the_headers_from_the_first_ready_frame():
    """(review s143 wire-4) `coop_peer.py offer`: the type-1 header's guest mask on every battle frame from the first one with
    a player Ready bit -- the frames before it (the intro, LOAD_INITCHR not yet set: the raw mask) are not judged; one frame
    off the want turns it red; no Ready frame is red."""
    from harness import coop_peer as CPR
    recs = [_battle_rec(1.0 + i * 0.1, i, 3, 2, False, CPR) for i in range(5)]
    recs += [_battle_rec(1.5 + i * 0.1, 5 + i, 3, 4, True, CPR) for i in range(10)]
    rows = CPR.tape_offers(recs)
    assert len(rows) == 1 and rows[0]["offers"] == [4] * 10 and rows[0]["ready_t"] == pytest.approx(1.5)
    bad = recs + [_battle_rec(2.6, 40, 3, 2, True, CPR)]
    assert CPR.tape_offers(bad)[0]["offers"][-1] == 2
    none = [_battle_rec(1.0 + i * 0.1, i, 3, 4, False, CPR) for i in range(5)]
    assert CPR.tape_offers(none)[0]["ready_t"] is None
    args = CPR.build_parser().parse_args(["offer", "x.f9tape", "--want", "4"])
    assert args.func is CPR.cmd_offer and args.want == 4


@pytest.mark.parametrize("lever", [False, True])
def test_guestslots_15_hands_the_leader_back_unless_the_lever_keeps_the_positions(tmp_path, lever):
    """WHY wait_parity and end_host leg G are re-keyed, on the stand-in: `guestslots 15` in a selftest own battle with the
    leader (the kit Zidane, 98) at position 0 -- the guard drops Zidane's bit (0xF -> 0xE: no other member is free) and the
    host's window OPENS on him, which breaks "every slot is the guest's"; under `bench leaderguard off` the mask stays 0xF
    and the host's HUD opens nothing -- the premise those benches were written for."""
    game = _game(tmp_path)
    fake = _fake(game, battle_seat_party=False)
    with _session(game, fake) as g:
        g.newgame(settle=0)
        g.warp(30602)
        g.netsync("selftest", 1)
        g.netsync("guestslots", 15)
        if lever:
            g.netsync("bench", "leaderguard", "off")
        fake.atb_gain = 120
        g.start_battle(67, group=0)
        st = g.wait_for(lambda s: s.commands_enabled and s.coop_guard_nonce == s.coop_peer_nonce, timeout=10.0,
                        what="the own battle's latch")
        assert st.coop_guard_effective == (0xF if lever else 0xE)
        assert (st.coop_guard_moved_from, st.coop_guard_moved_to) == ((-1, -1) if lever else (0, -1))
        opened = set()
        for _ in range(120):
            s = g.state
            if s.turn_slot >= 0:
                opened.add(s.turn_slot)
            g.wait_frames(4)
        assert opened == (set() if lever else {0}), opened
