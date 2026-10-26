"""[ff9mapkit netsync s154] THE DIORAMA SEAT's BENCH, its REPO HALF -- studies/test-harness/scenarios/coop_world_party_duo.py.

The two-game bench is the proof (calibrated first on the s153 DLL: exactly WP1a, WP1b, WP1c, WP2a, WP2b red; WP-I, WP1-pre,
WP2-pre, WP1d green). This file pins every judge it builds on as a PURE function over hand-built samples -- each red on the s153
shape (the guest's own Zidane seated in the host's battle, the digit panel instead of the stock menu, the 6603 field load's levels
on a mirroring guest) and green on the s154 one -- the calibration ledger (behavioural rows only, never a missing log line; each
battle's boot its own row, driven through the shipped run_duo ledger), and the mirror leg's fight cap recomputed from the EXP
arithmetic that makes its gate reachable -- with its pre-pair farm, and the cal153 run (20261026-121811-duo-s154-wpm-cal153)
replayed on its own samples and log lines: a return that never lands stops the leg AT that battle, 'not reached', and a battle
starts only on a guest live on the world map.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import pathlib
import subprocess
import sys
import textwrap

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"

_PRELUDE = r'''
import importlib.util, os, sys
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
for k in ("COOP_CALIBRATE", "COOP_WP_LEG", "COOP_WP_FIGHTS"):
    os.environ.pop(k, None)
from harness.channel import State
from harness import battlewire as BW
spec = importlib.util.spec_from_file_location("coop_world_party_duo", os.path.join(scen, "coop_world_party_duo.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

HOST_UNITS = [("Zidane", 1), ("Vivi", 1), ("Garnet", 1), ("Steiner", 1)]

def units(pairs, *, enemies=1):
    out = [{"slot": i, "player": True, "name": n, "level": lv} for i, (n, lv) in enumerate(pairs)]
    return out + [{"slot": 4 + j, "player": False, "name": "Goblin", "level": 1} for j in range(enemies)]

def battle_st(n, pairs, *, party=None, debug=True, mirror_party=None, mirroring=False, menu=None):
    ns = {"dress": {"party": party if party is not None else [0, -1, -1, -1], "mirror_party": mirror_party},
          "session": {"mirroring": mirroring, "peer_alive": True}}
    if menu is not None:
        ns["battle"] = {"host": {"wait": {"menu": menu}}}
    return State({"frame": n, "ui_state": "BattleHUD", "scene": "BattleMapDebug" if debug else "BattleMap",
                  "battle": {"active": True, "debug": debug, "units": units(pairs)}, "netsync": ns})

def world_st(n, *, party=None, returns=1, frozen=True, mirroring=False, mirror_party=None, peer=True, world=9011, ui="WorldHUD"):
    return State({"frame": n, "ui_state": ui, "world": {"id": world, "x": 1197.0, "z": -796.0},
                  "netsync": {"instance": True, "dress": {"party": party if party is not None else [0, -1, -1, -1],
                                                          "mirror_party": mirror_party},
                              "session": {"mirroring": mirroring, "peer_alive": peer},
                              "world": {"freeze": {"on": frozen}, "dio": {"returns": returns}}}})

# THE cal153 RUN's DEAD WORLD (.harness-runs/20261026-121811-duo-s154-wpm-cal153, guest states-FAILED-1.jsonl at 12:24:49, the
# keys the judges read, verbatim): after its 4th return the world map never constructed -- ui BattleResult on scene WorldMap,
# world ticks 0, no diorama up, the return COUNTED (4), the freeze flag still on
def dead_world_st(n, *, returns=4):
    return State({"frame": n, "ui_state": "BattleResult", "scene": "WorldMap", "fading": False,
                  "world": {"id": 9011, "x": 1197.367, "z": -796.699, "vehicle": 0, "ctl": 0, "ticks": 0},
                  "battle": {"active": False, "epoch": 0, "debug": False, "result": 1, "scene": 0},
                  "netsync": {"instance": True, "dress": {"party": [0, -1, -1, -1], "mirror_party": [0, 1, 2, 3]},
                              "session": {"mirroring": True, "peer_alive": True},
                              "diorama": {"booted": False, "boot": "warm", "returns": returns, "last_return": "warm"},
                              "world": {"freeze": {"on": True, "why": "live"},
                                        "dio": {"booted_world": False, "boot_world": 9011, "returns": returns,
                                                "last_return": "warm", "resuming": False}}}})

# ...and its engine log across that return (guest Memoria.log 2329-2341, verbatim but for the elided stack)
DEAD_RETURN_LINES = [
    "26.10.2026 12:22:13 |M| [NetSync] diorama LEAVE requested -> WorldMap (world 9011, mode 3)",
    "26.10.2026 12:22:13 |M| [NetSync] diorama torn down -- state restored, isDebug cleared; r9_refused=0",
    "26.10.2026 12:22:14 |M| [NetSync] diorama RETURN (warm) -> world 9011 resumed through Main_Reinit: the guest stands where it "
    "stood at boot (player at (306526, -203955))",
    "26.10.2026 12:22:14 |E| When importing FBX 'FF9CustomMap-world/StreamingAssets/Assets/Resources/Models/5/6321/6321.fbx':",
    "26.10.2026 12:22:14 |E| System.IO.IOException: Sharing violation on path C:\\gd\\ff9-inst\\guest\\FF9CustomMap-world\\"
    "StreamingAssets\\Assets\\Resources\\Models\\5\\6321\\6321.fbx",
    "26.10.2026 12:22:14 |E|   at Memoria.Assets.FbxIO.ReadFlexible (System.String path) [0x00000] in <filename unknown>:0 ",
    "26.10.2026 12:22:14 |M| [NetSync] diorama leave noted (nonce 4) -- the watcher won't re-boot this battle",
]

class MirrorGuest:
    """A mirroring guest frozen on 9011; ``dead`` turns it into the run's dead world (world_settle and state alike)."""
    def __init__(self, s154=False):
        self.s154, self.dead = s154, False
    def _st(self):
        st = dead_world_st(1) if self.dead else world_st(1, mirroring=True, mirror_party=[0, 1, 2, 3])
        if self.s154:
            st.raw["netsync"].setdefault("diorama", {})["boot_song"] = -1     # the s154 probe WP55-CAL reads the stage by
        return st
    def world_settle(self):
        return self._st()
    @property
    def state(self):
        return self._st()
    def wait_for(self, predicate, timeout=20.0, what=""):
        return self._st()
    def wait_frames(self, n):
        pass

class LedgerDuo:
    paired, strict = False, True
    def __init__(self, guest, host=None):
        self.guest, self.host, self.rows, self.fought, self.notes = guest, host, {}, 0, []
    def check(self, ok, label, detail="", cid=None):
        self.rows[cid] = (bool(ok), str(detail))
    def note(self, text):
        self.notes.append(str(text))

def mirror_battle(*, dead_at=None, lie_at=None, stale=True, pre_wins=None):
    """host_world_battle's stand-in over the EXP arithmetic (paired battle k's host roster carries pre_wins + k - 1 wins of
    23 // 4): every battle boots; battle ``dead_at``'s return never lands (the run's shape: returned None, its lines, the guest
    dead from then on); battle ``lie_at`` CLAIMS a landed return while the guest is dead (the ready gate's case)."""
    share = m.WIN_EXP // len(m.HOST_PARTY)
    def battle(d, where):
        k = int(where.split()[-1])
        d.fought = k
        pw = m.PRE_WINS if pre_wins is None else pre_wins
        lv = 1 if (pw + k - 1) * share < m.LV2_EXP else 2
        host = [(n, lv) for n, _l in HOST_UNITS]
        seat = [(n, 1) for n, _l in HOST_UNITS] if stale else host          # s153: the 6603 field load's level-1 Slots
        gs = [battle_st(i, seat, party=[0, 1, 2, 3], mirroring=True, mirror_party=[0, 1, 2, 3]) for i in range(3)]
        out = {"booted": gs[0], "returned": world_st(9, mirroring=True, mirror_party=[0, 1, 2, 3]), "gsamples": gs,
               "hsamples": [battle_st(9, host, debug=False)], "glines": [], "why": None, "host_err": None}
        if k == dead_at:
            d.guest.dead = True
            out.update(returned=None, glines=list(DEAD_RETURN_LINES), gsamples=gs + [dead_world_st(20 + i) for i in range(3)])
        if k == lie_at:
            d.guest.dead = True
        return out
    return battle
'''


def _child(body: str) -> str:
    code = _PRELUDE + "\n" + textwrap.dedent(body)
    out = subprocess.run([sys.executable, "-c", code, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, (out.stdout[-3000:], out.stderr[-3000:])
    return out.stdout


def test_the_calibration_ledger_is_the_wrong_outcomes_only():
    _child('''
        assert m.PREDICTED_S153 == ("WP1a", "WP1b", "WP1c", "WP2a", "WP2b")
        assert set(m.PREDICTED_S153) <= set(m.CHECKS_UNARMED)
        for green in ("WP-I", "WP1-pre", "WP2-pre", "WP1d", "WP-SWIRL"):    # must be green on s153 or WP-CAL fails
            assert green in m.CHECKS_UNARMED and green not in m.PREDICTED_S153
        assert m.PRE_IDS == {1: "WP1-pre", 2: "WP2-pre"}
        order = list(m.CHECKS_UNARMED)
        assert order.index("WP1d") < order.index("WP2-pre") < order.index("WP2a")
        assert m.PREDICTED_S153_MIRROR == ("WP55-2",) and "WP55-GATE" not in m.PREDICTED_S153_MIRROR
        assert m.calibration(False, "unarmed") == m.PREDICTED_S153 and m.calibration(True, "unarmed") == ()
        assert m.calibration(False, "mirror") == m.PREDICTED_S153_MIRROR and m.calibration(True, "mirror") == ()
        assert m.LEG == "unarmed" and m._leg("55") == "mirror" and m._leg("bogus") is None
        assert m.PROBE == "netsync.diorama.boot_song" and m.HOST_PARTY == [0, 1, 2, 3] and m.GUEST_PARTY == [0, -1, -1, -1]
    ''')


def test_the_mirror_legs_default_fight_cap_can_reach_its_gate():
    """M9: the gate's arithmetic recomputed from first principles -- one Goblin (WinExp 23) split over the four-member COOPPARTY
    (integer, BattleResultUI), level 2 at 16 EXP (Leveling.csv), battle k's roster carrying k - 1 wins -- names battle 5 as the
    first whose host levels differ from battle 1's; the default cap is that, and COOP_WP_FIGHTS cannot take it below."""
    _child('''
        assert (m.WIN_EXP, m.LV2_EXP) == (23, 16)
        def first_levelling_battle(members):
            share, k = m.WIN_EXP // members, 1
            while (k - 1) * share < m.LV2_EXP:                   # battle k fights at the EXP of k - 1 wins
                k += 1
            return k
        assert first_levelling_battle(len(m.HOST_PARTY)) == 5 == m.MIN_FIGHTS
        assert m.MIRROR_FIGHTS == m.MIN_FIGHTS                   # the default reaches the gate with the whole party standing
        assert first_levelling_battle(3) <= m.MIN_FIGHTS and first_levelling_battle(2) <= m.MIN_FIGHTS   # a KO only helps
        # THE PRE-PAIR FARM: the most wins that still read level 1 (the guest's 6603 field load parses level 1), one more win
        # levels the party -- so paired battle 1 is the 4th win and paired battle 2 the gate, the total still MIN_FIGHTS
        share = m.WIN_EXP // len(m.HOST_PARTY)
        assert m.PRE_WINS == 3 and m.PRE_WINS * share < m.LV2_EXP <= (m.PRE_WINS + 1) * share
        assert m.PRE_WINS + 2 == m.MIN_FIGHTS == first_levelling_battle(len(m.HOST_PARTY))
        assert m.MIRROR_FIGHTS - m.PRE_WINS == 2                 # the paired battles: the control and the gate
        assert set(m.WIN_RESULTS) == {k for k, v in State.BATTLE_RESULTS.items() if v in ("victory", "victory-no-pose")}
        # the knob raises the cap, never lowers it below the arithmetic (a cap that cannot reach the gate is no run at all)
        def loaded(value):
            os.environ["COOP_WP_FIGHTS"] = value
            try:
                sp = importlib.util.spec_from_file_location("wp_knob", os.path.join(scen, "coop_world_party_duo.py"))
                mod = importlib.util.module_from_spec(sp)
                sp.loader.exec_module(mod)
                return mod.MIRROR_FIGHTS
            finally:
                os.environ.pop("COOP_WP_FIGHTS", None)
        assert loaded("2") == 5 and loaded("4") == 5 and loaded("7") == 7 and loaded("x") == 5 and loaded("") == 5
    ''')


def test_the_mirror_leg_reaches_its_gate_at_paired_battle_two_through_the_shipped_loop():
    """M9 through the SHIPPED run_duo ledger and _mirror_battles loop (the pairing / walk-out / WP55-I setup shimmed; the host's
    world battle stubbed over the EXP arithmetic: paired battle k's host roster is level 2 once PRE_WINS + k - 1 wins of 23 // 4
    reach 16): the gate is reached at paired battle 2 (fight 5) under the default cap, every return landing; WP55-2 is s153's
    red (the 6603 field load's levels seated) and s154's green (the frame's), so WP55-CAL calibrates on both -- and a cap of 4
    (one paired battle after the farm) can never reach it."""
    _child('''
        m.cb.CALIBRATE = True
        m.LEG = "mirror"
        def shim(d, check, rest):
            check("WP55-I", True, "the stand-in instrument")
            m._mirror_battles(d, check, rest)
        m._mirror = shim
        for stale, wp552 in ((True, False), (False, True)):
            d = LedgerDuo(MirrorGuest(s154=not stale))
            m.host_world_battle = mirror_battle(stale=stale)
            m.run_duo(d)
            assert d.fought == 2 and d.rows["WP55-GATE"][0] and "battle 2" in d.rows["WP55-GATE"][1], d.rows
            assert d.rows["WP55-1"][0] and d.rows["WP55-2"][0] is wp552, d.rows
            assert d.rows["WP55-CAL"][0], d.rows["WP55-CAL"]       # s153: exactly WP55-2 red; s154: nothing red
        m.MIRROR_FIGHTS = 4                                                     # one paired battle: never reached
        d = LedgerDuo(MirrorGuest())
        m.host_world_battle = mirror_battle()
        m.run_duo(d)
        assert d.fought == 1 and not d.rows["WP55-GATE"][0] and "not reached" in d.rows["WP55-2"][1]
        assert not d.rows["WP55-CAL"][0]
    ''')


def test_the_runs_dead_return_stops_the_mirror_leg_at_that_battle_never_the_next():
    """THE cal153 RUN (20261026-121811-duo-s154-wpm-cal153), replayed through the SHIPPED run_duo ledger and _mirror_battles:
    battles 1-3 returned, battle 4's return NEVER LANDED (the FBX sharing violation, the world constructor thrown -- the run's
    own lines and dead-world samples), and the old loop fought battle 5 against it and wrote 'battle 5: the guest never booted
    its world diorama'. Now: on the run's own schedule (no farm) the leg stops AT battle 4 -- battle 5 is never fought -- its
    rows 'not reached' naming battle 4, the dead world and the guest's error lines; on the shipped schedule (the farm) the one
    shared return before the gate is battle 1's, and a dead one stops there. WP55-CAL is red either way, on either stage: an
    unreached leg is never a calibration."""
    _child('''
        m.cb.CALIBRATE = True
        m.LEG = "mirror"
        def shim(d, check, rest):
            check("WP55-I", True, "the stand-in instrument")
            m._mirror_battles(d, check, rest)
        m._mirror = shim
        for pre_wins, dead_at in ((0, 4), (m.PRE_WINS, 1)):
            for s154 in (False, True):
                m.PRE_WINS = pre_wins
                d = LedgerDuo(MirrorGuest(s154=s154))
                m.host_world_battle = mirror_battle(dead_at=dead_at, stale=not s154, pre_wins=pre_wins)
                t0 = m.time.time()
                m.run_duo(d)
                assert d.fought == dead_at, (pre_wins, d.fought, d.rows)            # the battle after it is never fought
                for cid in ("WP55-GATE", "WP55-2"):
                    ok, why = d.rows[cid]
                    assert not ok and why.startswith("not reached: battle %d:" % dead_at), (cid, why)
                    assert "return never landed" in why and "BattleResult" in why and "ticks 0" in why, why
                    assert "Sharing violation" in why and "6321.fbx" in why, why
                    assert "never booted" not in why, why
                assert d.rows["WP55-1"][0], d.rows["WP55-1"]
                ok, why = d.rows["WP55-CAL"]
                assert not ok and "WP55-GATE" in why, why                      # an unpredicted red: never green
                assert m.time.time() - t0 < 5.0                                # the dead return is judged, not re-waited
        m.PRE_WINS = 3
    ''')


def test_a_battle_starts_only_on_a_guest_live_on_the_world_map():
    """THE READY GATE through the shipped loop: a battle whose return CLAIMS to have landed while the guest's world is the run's
    dead one (world_settle returned it at once in the old loop -- it is not WorldHUD) never starts the next battle: 'battle 2 not
    started' with the guest's ui / scene / ticks, the next battle never fought; the unarmed leg's loop shares the gate."""
    _child('''
        m.cb.CALIBRATE = True
        m.READY_S = 0.3
        m.LEG = "mirror"
        def shim(d, check, rest):
            check("WP55-I", True, "the stand-in instrument")
            m._mirror_battles(d, check, rest)
        m._mirror = shim
        d = LedgerDuo(MirrorGuest())
        m.host_world_battle = mirror_battle(lie_at=1)
        m.run_duo(d)
        assert d.fought == 1, d.rows
        ok, why = d.rows["WP55-GATE"]
        assert not ok and why.startswith("not reached: battle 2 not started: the guest is not live on the world map"), why
        assert "'BattleResult'" in why and "'WorldMap'" in why and "ticks 0" in why, why
        assert not d.rows["WP55-CAL"][0]
        # the unarmed leg: battle 1's dead return stops it before battle 2 (WP2-pre 'not reached', an unpredicted red)
        m.LEG = "unarmed"
        own = [battle_st(i, [("Zidane", 1)]) for i in range(2, 10)]
        hsam = [battle_st(1, HOST_UNITS, debug=False, menu=BW.CTL_LEGACY)]
        class Guest(MirrorGuest):
            def _st(self):
                return dead_world_st(1, returns=1) if self.dead else world_st(1, returns=0)
        fought = []
        def battle(d, where):
            fought.append(where)
            d.guest.dead = True
            return {"booted": own[0], "returned": None, "gsamples": list(own) + [dead_world_st(30)], "hsamples": list(hsam),
                    "glines": list(DEAD_RETURN_LINES), "why": None, "host_err": None}
        m.host_world_battle = battle
        def ushim(d, check, rest):
            check("WP-I", True, "the stand-in instrument")
            m._seat_battles(d, check, rest)
        m._unarmed = ushim
        d = LedgerDuo(Guest())
        m.run_duo(d)
        assert fought == ["battle 1"], fought
        ok, why = d.rows["WP2-pre"]
        assert not ok and why.startswith("not reached: battle 1: the guest's return never landed") and "Sharing violation" in why
        assert not d.rows["WP1d"][0]                                           # (its own containment red: never back on 9011)
        ok, why = d.rows["WP-CAL"]
        assert not ok and "WP2-pre" in why and "WP1d" in why, why
    ''')


def test_the_ready_and_return_judges_on_the_runs_own_samples():
    _child('''
        ok, why = m.judge_ready(dead_world_st(1))
        assert not ok and "'BattleResult'" in why and "'WorldMap'" in why and "ticks 0" in why and "returns 4" in why, why
        assert m.judge_ready(world_st(1, mirroring=True, mirror_party=[0, 1, 2, 3]))[0]
        assert m.judge_ready(world_st(1, frozen=False))[0]                     # the freeze is WP55-I's: detail only here
        assert not m.judge_ready(world_st(1, world=9002))[0] and not m.judge_ready(world_st(1, ui="FieldHUD"))[0]
        assert not m.judge_ready(None)[0]
        booted = battle_st(1, HOST_UNITS, party=[0, 1, 2, 3])
        booted.raw["netsync"]["diorama"] = {"booted": True}
        assert not m.judge_ready(booted)[0]                                    # a diorama still up is not a live world
        errs = m.engine_errors(DEAD_RETURN_LINES)
        assert errs[0].startswith("When importing FBX") and "Sharing violation" in errs[1] and len(errs) == 3, errs
        assert m.engine_errors(["26.10.2026 12:20:08 |M| [NetSync] diorama RETURN (warm)"]) == [] and m.engine_errors(None) == []
        ok, why = m.judge_return({"returned": None, "gsamples": [booted, dead_world_st(2)], "glines": DEAD_RETURN_LINES,
                                  "host_err": None})
        assert not ok and "return never landed" in why and "Sharing violation" in why and "'BattleResult'" in why, why
        assert not m.judge_return({"gsamples": [], "glines": []})[0]          # no `returned` key at all: never a landing
        ok, why = m.judge_return({"returned": None, "gsamples": [], "glines": [], "host_err": "FightTimeout: turns"})
        assert not ok and "no error line" in why and "FightTimeout" in why, why
        assert m.judge_return({"returned": world_st(7), "gsamples": [], "glines": DEAD_RETURN_LINES})[0]
        # _guest_ready: a dead guest red within its bound; a guest that comes live while it polls, green
        class Slow:
            def __init__(self, live_after):
                self.n, self.live_after = 0, live_after
            def world_settle(self):
                return dead_world_st(1)
            @property
            def state(self):
                self.n += 1
                return world_st(2) if self.n >= self.live_after else dead_world_st(2)
        t0 = m.time.time()
        ok, why, st = m._guest_ready(Slow(10 ** 9), timeout=0.6)
        assert not ok and st.ui_state == "BattleResult" and m.time.time() - t0 < 3.0, why
        ok, why, st = m._guest_ready(Slow(2), timeout=5.0)
        assert ok and st.ui_state == "WorldHUD", why
    ''')


def test_the_pre_pair_farm_banks_its_wins_alone_and_wp55_i_judges_it():
    """THE PRE-PAIR FARM through the shipped _farm and _mirror (duo.pair, the walk outs and the battles stood in): the host banks
    PRE_WINS stock world wins (fight()'s own policy) back on the world map each time, then enters 6603 from the world map; a lost
    or raised farm fight is recorded and WP55-I goes red with everything below 'not reached'. duo.pair runs the host's setup
    before the guest's New Game (ROLES order): the farm's world loads have no second game to race."""
    _child('''
        from harness import duo
        import inspect
        assert duo.ROLES == ("host", "guest")
        src = inspect.getsource(duo.Duo.pair)
        assert src.index("for r in ROLES:") < src.index("g.newgame()") < src.index("note = setup(g)") < src.index("self.apply_role")
        calls = []
        class Host:
            def __init__(self, results):
                self.results, self.ui = list(results), "FieldHUD"
            def no_encounters(self, on=True):
                calls.append("noenc")
            def world_settle(self):
                return world_st(1, party=[0, 1, 2, 3])
            def world_battle(self, scene, group=-1, rand=False, timeout=60.0):
                calls.append(("battle", scene, group, rand))
                self.ui = "BattleHUD"
            def fight(self, **kw):
                assert "policy" not in kw                                    # the stock Attack policy: no guest to wait for
                r = self.results.pop(0)
                if isinstance(r, Exception):
                    raise r
                calls.append(("fight", r))
                self.ui = "BattleResult"
                return r
            def wait_world(self, timeout=90.0):
                self.ui = "WorldHUD"
            def world_warp(self, field, **kw):
                calls.append(("world_warp", field))
                self.ui = "FieldHUD"
            def wait_frames(self, n):
                pass
            def note(self, text):
                pass
            @property
            def state(self):
                return world_st(2, party=[0, 1, 2, 3], ui=self.ui)
        def walk_out(g, **kw):
            calls.append("walk_out")
            g.ui = "WorldHUD"
            return True, "world 9011 at the landing", world_st(1)
        m.cw.walk_out = walk_out
        m.cw.teleport_settle = lambda g, xz: None
        m.cb.seed_party = lambda g, back_to: "party seeder: stood in"
        note = m._seed_host(Host([1, 1, 2]))
        assert m.FARM["wins"] == 3 and m.judge_farm(m.FARM)[0], (m.FARM, note)
        assert calls == ["noenc", "walk_out", ("battle", m.wb.SCENE, m.wb.GROUP, True), ("fight", 1),
                         ("battle", m.wb.SCENE, m.wb.GROUP, True), ("fight", 1), ("battle", m.wb.SCENE, m.wb.GROUP, True),
                         ("fight", 2), ("world_warp", m.FARSHORE)], calls
        assert "3 of 3 win(s)" in note
        for results, want in (([1, 3], "farm fight 2 ended with result 3"), ([m.HarnessError("swirl")], "farm fight 1 raised")):
            calls.clear()
            m._farm(Host(results))
            ok, why = m.judge_farm(m.FARM)
            assert not ok and want in why, why
        # _mirror itself: the farm folded into WP55-I, then the gate at paired battle 2; a bad farm reds WP55-I and stops
        m.cb.CALIBRATE = True
        m.LEG = "mirror"
        class FarmDuo(LedgerDuo):
            def __init__(self, guest, host):
                super().__init__(guest, host)
            def pair(self, field, host_setup=None, **kw):
                assert field == m.FARSHORE
                self.host.note(host_setup(self.host))
                self.paired = True
        for results, farm_ok in (([1, 1, 1], True), ([1, 3], False)):
            d = FarmDuo(MirrorGuest(), Host(results))
            m.host_world_battle = mirror_battle()
            m.run_duo(d)
            ok, why = d.rows["WP55-I"]
            assert ok is farm_ok and "pre-pair farm:" in why, why
            if farm_ok:
                assert d.fought == 2 and d.rows["WP55-GATE"][0] and not d.rows["WP55-2"][0] and d.rows["WP55-CAL"][0], d.rows
            else:
                assert d.fought == 0 and "not reached: the instrument (WP55-I) is red" in d.rows["WP55-GATE"][1], d.rows
                assert not d.rows["WP55-CAL"][0]
    ''')


def test_a_second_battle_that_never_boots_reds_the_calibration_through_wp2_pre():
    """L10 through the SHIPPED run_duo ledger and the shipped _seat_battles loop (only the W0 walk-out / WP-I setup shimmed and the
    host's world battle stubbed): s153's truth calibrates green; a battle 2 that never boots is an UNPREDICTED red (WP2-pre), so
    WP2a / WP2b's 'not reached' can no longer stand in for their predicted reds."""
    _child('''
        m.cb.CALIBRATE = True
        own = [battle_st(i, [("Zidane", 1)]) for i in range(2, 10)]          # s153: the guest's own Zidane seated
        hsam = [battle_st(1, HOST_UNITS, debug=False, menu=BW.CTL_LEGACY)]   # s153: the host decodes the digit panel
        class Guest:
            def __init__(self):
                self.returns = 0
            def world_settle(self):
                return world_st(1, returns=self.returns)
            @property
            def state(self):
                return world_st(2, returns=self.returns)
        class Duo:
            paired, strict = False, True
            def __init__(self, battle2_boots):
                self.guest, self.host, self.rows, self.b2 = Guest(), None, {}, battle2_boots
            def check(self, ok, label, detail="", cid=None):
                self.rows[cid] = (bool(ok), str(detail))
            def note(self, text):
                pass
        def battle(d, where):
            if where == "battle 2" and not d.b2:
                return {"booted": None, "returned": None, "gsamples": [], "hsamples": [], "glines": [], "why": None}
            d.guest.returns += 1
            return {"booted": own[0], "returned": world_st(3, returns=d.guest.returns), "gsamples": list(own),
                    "hsamples": list(hsam), "glines": [], "why": None}
        m.host_world_battle = battle
        def shim(d, check, rest):                                            # W0 + WP-I stand in; the loop is the real one
            check("WP-I", True, "the stand-in instrument")
            m._seat_battles(d, check, rest)
        m._unarmed = shim
        d = Duo(True)
        m.run_duo(d)
        red = {c for c, (ok, _w) in d.rows.items() if not ok}
        assert red == {"WP1a", "WP1b", "WP1c", "WP2a", "WP2b"} and d.rows["WP2-pre"][0] and d.rows["WP1d"][0], d.rows
        assert d.rows["WP-CAL"][0], d.rows["WP-CAL"]
        d = Duo(False)
        m.run_duo(d)
        assert not d.rows["WP2-pre"][0] and "not reached" in d.rows["WP2a"][1] and "not reached" in d.rows["WP2b"][1]
        ok, why = d.rows["WP-CAL"]
        assert not ok and "WP2-pre" in why, why
    ''')


def test_the_seat_judges_red_s153s_own_party_and_pass_the_hosts():
    _child('''
        host_roster = dict(HOST_UNITS)
        s154 = [world_st(1), *[battle_st(i, HOST_UNITS, party=[0, 1, 2, 3]) for i in range(2, 12)], world_st(12)]
        s153 = [world_st(1), *[battle_st(i, [("Zidane", 1)]) for i in range(2, 12)], world_st(12)]
        assert m.judge_seat_party(s154, m.HOST_PARTY)[0]
        ok, why = m.judge_seat_party(s153, m.HOST_PARTY)
        assert not ok and "[0, -1, -1, -1]" in why, why
        assert not m.judge_seat_party([world_st(1)], m.HOST_PARTY)[0]                 # no seated sample: red, never vacuous
        assert m.judge_seat_units(s154, host_roster)[0]
        ok, why = m.judge_seat_units(s153, host_roster)
        assert not ok and "1 unit(s)" in why, why
        # a seat with the host's names but a STALE level (a no-op carry) is red: level is the seat's own value
        stale = [battle_st(i, [("Zidane", 1), ("Vivi", 1), ("Garnet", 1), ("Steiner", 2)], party=[0, 1, 2, 3]) for i in range(5)]
        ok, why = m.judge_seat_units(stale, dict(HOST_UNITS, Steiner=3))
        assert not ok and "Steiner" in why, why
        # the settled roster: InitPlayerData lands after the boot -- an early partial roster is not judged
        partial = [battle_st(1, [("Zidane", 1)], party=[0, 1, 2, 3]), *[battle_st(i, HOST_UNITS, party=[0, 1, 2, 3])
                                                                       for i in range(2, 6)]]
        assert m.judge_seat_units(partial, host_roster)[0]
        assert not m.judge_seat_units(s154, {})[0]                                    # the host's roster unread: red
    ''')


def test_the_host_roster_is_read_off_the_hosts_own_battle_never_a_diorama():
    _child('''
        hs = [battle_st(1, [("Zidane", 1)], debug=False), battle_st(2, HOST_UNITS, debug=False, menu=2),
              battle_st(3, [("Zidane", 9)] * 1, debug=True)]
        assert m.host_players(hs) == dict(HOST_UNITS)
        assert m.host_players([battle_st(1, HOST_UNITS, debug=True)]) == {}
        assert m.levels_changed(dict(HOST_UNITS), dict(HOST_UNITS, Vivi=2))
        assert not m.levels_changed(dict(HOST_UNITS), dict(HOST_UNITS))
        assert not m.levels_changed({}, dict(HOST_UNITS)) and not m.levels_changed(dict(HOST_UNITS), {})
    ''')


def test_the_mirror_legs_level_judge_reds_the_field_loads_levels():
    _child('''
        battle2 = dict(HOST_UNITS, Vivi=2, Garnet=2)
        s154 = [battle_st(i, list(battle2.items()), party=[0, 1, 2, 3], mirroring=True, mirror_party=[0, 1, 2, 3]) for i in range(5)]
        s153 = [battle_st(i, HOST_UNITS, party=[0, 1, 2, 3], mirroring=True, mirror_party=[0, 1, 2, 3]) for i in range(5)]
        assert m.judge_levels(s154, battle2)[0]
        ok, why = m.judge_levels(s153, battle2)
        assert not ok and "Vivi" in why and "Garnet" in why, why
        assert m.judge_levels(s153, dict(HOST_UNITS))[0]                    # battle 1: the field load is still current (green)
        assert not m.judge_levels([world_st(1)], battle2)[0]
    ''')


def test_the_menu_judge_is_behavioural_on_both_machines():
    _child('''
        lines = ["26.10.2026 10:00:00 |I| [NetSync] stock menu: the ready mirror is SERVING slot 1"]
        hs_root = [battle_st(1, HOST_UNITS, debug=False, menu=BW.CTL_ROOT)]
        hs_digit = [battle_st(1, HOST_UNITS, debug=False, menu=BW.CTL_LEGACY)]
        assert m.judge_menu(lines, hs_root)[0]
        assert not m.judge_menu([], hs_root)[0]                     # s153: the guest never served (the digit panel)
        assert not m.judge_menu(lines, hs_digit)[0]                 # ...and the host never decoded a root / deep menu
        assert m.judge_menu(lines, [battle_st(1, HOST_UNITS, debug=False, menu=BW.CTL_DEEP)])[0]
    ''')


def test_the_containment_judge_reds_an_armed_story_mirror_and_a_missed_return():
    _child('''
        ok_run = [world_st(1, returns=0), *[battle_st(i, HOST_UNITS, party=[0, 1, 2, 3]) for i in range(2, 9)], world_st(9)]
        assert m.judge_containment(ok_run, world_st(10, returns=1), 0)[0]
        armed = [*ok_run[:3], battle_st(4, HOST_UNITS, party=[0, 1, 2, 3], mirror_party=[0, 1, 2, 3]), *ok_run[3:]]
        ok, why = m.judge_containment(armed, world_st(10, returns=1), 0)
        assert not ok and "mirror_party set on 1" in why, why
        mirroring = [*ok_run, battle_st(11, HOST_UNITS, party=[0, 1, 2, 3], mirroring=True)]
        assert not m.judge_containment(mirroring, world_st(12, returns=1), 0)[0]
        assert not m.judge_containment(ok_run, world_st(10, returns=0), 0)[0]                 # the return never counted
        assert not m.judge_containment(ok_run, world_st(10, returns=1, party=[0, 1, 2, 3]), 0)[0]   # the seat never restored
        assert not m.judge_containment(ok_run, world_st(10, returns=1, frozen=False), 0)[0]
        assert not m.judge_containment(ok_run, world_st(10, returns=1, ui="FieldHUD"), 0)[0]
        assert not m.judge_containment([], world_st(10, returns=1), 0)[0]
    ''')


def test_the_instrument_reds_an_armed_or_unborn_guest_before_anything_is_judged():
    _child('''
        host = world_st(1, party=[0, 1, 2, 3])
        assert m.judge_instrument(world_st(1), host, 0)[0]
        for bad in (world_st(1, peer=False), world_st(1, frozen=False), world_st(1, mirroring=True),
                    world_st(1, mirror_party=[0, 1, 2, 3]), world_st(1, party=[0, 1, 2, 3]), world_st(1, world=9002),
                    world_st(1, ui="FieldHUD")):
            assert not m.judge_instrument(bad, host, 0)[0]
        assert not m.judge_instrument(world_st(1), host, 1)[0]                 # an ARMED line since the walk out
        assert not m.judge_instrument(world_st(1), world_st(1), 0)[0]          # the host not seeded: the parties do not differ
        # the mirror leg's instrument wants the guest MIRRORING (s145's shape)
        assert m.judge_instrument(world_st(1, mirroring=True, mirror_party=[0, 1, 2, 3]), host, 3, mirroring_expected=True)[0]
        assert not m.judge_instrument(world_st(1), host, 0, mirroring_expected=True)[0]
    ''')
