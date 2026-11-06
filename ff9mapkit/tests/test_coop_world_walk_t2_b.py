"""[ff9mapkit netsync s167] WORLD WALK, ROUND B -- THE T2 AND DUO LEGS (studies/test-harness/scenarios/coop_world_walk_t2.py's round-B
section), offline.

  * THE TABLES: every round-B leg's catalog, OLD / LEVER predictions, measures and stand-in fault reds name rows the leg carries, levers
    it accepts and faults the stand-in has; the duo's likewise; the gate row is never part of a calibration.
  * THE s167 INSTRUMENT: roam_instrument_tape(caps 0x0003, the guest's own digest and components) is an s167 host through coop_peer's
    REAL codec -- the digest on every place-4 trailer, section 11 between sections 0 and 7 of its world-phase state frames -- and rm8 (the
    tape's s167 shape) holds on it and fails on round A's (caps 0x0001) and an uncalibrated one; the stall windows end before the host's
    tile teleport.
  * THE PURE JUDGES go red on each wrong shape -- D-BATTLE's above all (the stand-in has no diorama: its judge is proven here only).
  * EVERY LEG SMOKED AGAINST THE STAND-IN through the real Session and stub peers on the stand-in's OWN clock -- round A's stubs plus
    round B's transport facts: replay-host's `--from`, the session's StaleMs (a blackhole stales the position lane: IsLiveFollowedSession),
    section 11 off the host's state frames (ObserveHostDialog), serve-guest fed the host's own frames (`--caps auto` / `--digest echo`),
    and the duo link's section 11 and section 4's life (an intent ends 'left' once its host leaves the landed field): NEW green (the
    owner-gated row red on the instrument), OLD on s166 exactly B_T2_OLD_PREDICTED / DUO_B_OLD_PREDICTED with every red MEASURING
    s166's shape and NO round-B op sent, each lever exactly its prediction, each stand-in fault exactly its rows; and round A's legs on
    an s167 stand-in green through THE REGRESSION RE-KEY -- and red without it (the re-key is a check that can fail).

Every scenario-touching run is a CHILD process (a scenario reads its COOP_* knobs at import and puts its dir on sys.path).
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402

SCENARIOS = REPO / "studies" / "test-harness" / "scenarios"


def _load_t2():
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_world_walk_t2_b_pure", str(SCENARIOS / "coop_world_walk_t2.py"))
    m = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(m)
    finally:
        os.environ.update(old)
    return m


@pytest.fixture(scope="module")
def t2():
    return _load_t2()


# ================================================================================================ the tables
def test_round_bs_tables_name_rows_its_legs_carry_levers_they_accept_and_faults_the_stand_in_has(t2):
    faults = set(FG.WORLD_WALK_B_FAULTS)
    assert set(t2.B_T2_LEGS) == {"walk", "stallhole", "hostb"} and set(t2.B_T2_LEGS) <= set(t2.LEGS)
    assert set(t2.B_T2_LEVERS) == set(t2.B_T2_LEGS) and set(t2.B_T2_CHECKS) == set(t2.B_T2_LEGS)
    for leg in t2.B_T2_LEGS:
        cat = t2.b_leg_catalog(leg, True)
        assert set(t2.B_T2_OLD_PREDICTED[leg]) <= set(cat), leg
        assert f"S167-{leg.upper()}-CAL" in cat
        for lever in t2.B_T2_LEVERS[leg]:
            rows = t2.B_T2_LEVER_PREDICTED[(leg, lever)]
            assert rows and set(rows) <= set(cat) and lever in t2.B_LEVER_OPS, (leg, lever)
        for row in set(t2.B_T2_OLD_PREDICTED[leg]) | {r for (lg, _l), rs in t2.B_T2_LEVER_PREDICTED.items() if lg == leg for r in rs}:
            assert row in t2.B_T2_MEASURE, row                                # every predicted red names the shape it measures
        # the gate row is never part of a calibration (its verdict is the tape's, never the engine's)
        assert "S167-WR-GATE" not in t2.B_T2_OLD_PREDICTED[leg]
        assert ("S167-WR-GATE" in cat) is (leg != "hostb")
    assert {lg for lg, _l in t2.B_T2_LEVER_PREDICTED} <= set(t2.B_T2_LEGS)
    assert set(t2.DUO_B_LEVER_PREDICTED) == set(t2.DUO_B_LEVERS) and all(lv in t2.B_LEVER_OPS for lv in t2.DUO_B_LEVERS)
    assert set(t2.DUO_B_OLD_PREDICTED) == set(t2.DUO_B_ORDER) - {"S167-D-SHARED"}
    assert all(set(r) <= set(t2.DUO_B_ORDER) for r in t2.DUO_B_LEVER_PREDICTED.values())
    assert set(t2.DUO_B_OLD_PREDICTED) <= set(t2.DUO_B_MEASURE)
    assert "S167-D-ENTRY" not in t2.DUO_B_LEVER_PREDICTED["walk"]              # `walk off` keeps the refusal (refuse act)
    assert sorted((lg, f) for lg, table in t2.B_T2_FAULT_REDS.items() for f in table) == sorted(_FAULTS)
    for leg, table in t2.B_T2_FAULT_REDS.items():
        rows_of = t2.DUO_B_ORDER if leg == "duo" else t2.b_leg_catalog(leg, False)
        for fault, rows in table.items():
            assert fault in faults, (leg, fault)
            assert rows and set(rows) <= set(rows_of), (leg, fault, rows)
    # the levers are any-role ops of round B's own verb (THE DUO CANNOT PULL A SELFTEST-ROLE LEVER), and fullmap rides with minimap old
    for ops in t2.B_LEVER_OPS.values():
        assert all(op in BW.WORLDWALK_OPS_B and word in BW.WORLDWALK_WORDS_B[op] for op, word in ops)
    assert t2.B_LEVER_OPS["fullmap"] == (("fullmap", "old"), ("minimap", "old"))
    assert t2.b_t2_lever_of("stallhole", None) == "stallhold" and t2.b_t2_lever_of("stallhole", "walk") == "walk"
    assert t2.b_t2_lever_of("walk", "stallhold") is None and t2.b_t2_lever_of("duo", "fullmap") == "fullmap"
    # round A's tables are untouched: its legs and levers as they were
    assert set(t2.LEVERS) == set(t2.LEGS) - set(t2.B_T2_LEGS)


# ================================================================================================ the s167 instrument
_COMPS = [BW.ww_fp_lang_word("US"), 0x11111111, 0x22222222, 0x33333333, 0x44444444, 0x55555555]


def test_the_s167_instrument_carries_caps_b1_the_digest_and_section_11_and_rm8_can_fail(t2, tmp_path):
    digest = BW.ww_fp_combine(_COMPS)
    recs = t2.roam_instrument_tape(CP, caps=t2.CAPS_S167, digest=digest, fp_comps=_COMPS)
    rows = t2.trailer_rows(recs, CP)
    world = [r for r in rows if r["has"] and r["valid"]]
    assert world and {r["caps"] for r in world} == {3} and {r["digest"] for r in world} == {digest}
    assert {r["digest"] for r in rows if r["has"] and not r["valid"]} == {0}          # FpTxDigestRule: place 4 only
    secs = [(r.t, CP.fp_section_of(p)) for r, w, p in CP.host_frames(recs) if w == CP.TYPE_STATE]
    on = [s for _t, s in secs if s is not None]
    assert on and all(s == {"world": t2.WORLD, "lang": "US", "comps": _COMPS, "mask": 0x3F} for s in on)
    first_world = min(r["t"] for r in world)
    assert all(s is None for t, s in secs if t < first_world)                        # never off the host's live world
    for r, w, p in CP.host_frames(recs):                                              # 11 sits between 0 and 7 (8 stays last)
        if w == CP.TYPE_STATE and CP.fp_section_of(p) is not None:
            order, at = [], 0
            while at + 3 <= len(p):
                order.append(p[at])
                at += 3 + (p[at + 1] | (p[at + 2] << 8))
            assert order == [0, BW.SECTION_FP, 7], order
            break
    assert t2.facts_ok(t2.roam_tape_facts(recs, CP))[0]                               # round A's facts hold on it too
    assert t2.tape_s167(recs, CP)["ok"]
    a = t2.roam_instrument_tape(CP)                                                   # round A's: caps 0x0001, no digest
    assert not t2.tape_s167(a, CP)["ok"] and "older build" in t2.tape_s167(a, CP)["why"]
    bare = t2.roam_instrument_tape(CP, caps=t2.CAPS_S167)                             # s167 caps, digest 0: checking
    assert not t2.tape_s167(bare, CP)["ok"]
    p = t2.write_instrument(tmp_path / "b.f9tape", CP, caps=t2.CAPS_S167, digest=digest, fp_comps=_COMPS)
    header, back, torn = CP.read_tape(p)
    assert header["stage"] == "s167" and header["digest"] == f"0x{digest:08X}" and header["calibrated"] is True and not torn
    assert len(back) == len(recs)


def test_fp_comps_of_reads_the_guests_own_fingerprint_as_section_11_carries_it(t2):
    comps = {"language": "US", **{n: f"0x{v:08X}" for n, v in zip(BW.WW_FP_COMP_NAMES[1:], _COMPS[1:])}}
    real = BW.ww_fp_combine(_COMPS)
    st = S(1, fp={"ready": True, "components": comps, "real": f"0x{real:08X}", "world": 9011})
    got = t2.fp_comps_of(st)
    assert got == {"world": 9011, "comps": _COMPS, "real": real, "combined": real}
    assert t2.fp_comps_of(S(1, fp={"ready": False, "components": comps, "real": "0x1"})) is None
    assert t2.fp_comps_of(S(1, fp={"ready": True, "components": None})) is None
    assert t2.fp_comps_of(S(1)) is None


def test_the_stall_windows_end_before_the_hosts_tile_teleport(t2, monkeypatch):
    rows = t2.trailer_rows(t2.roam_instrument_tape(CP, caps=t2.CAPS_S167), CP)
    live = t2.world_live_t(rows)
    w = t2.stall_windows(rows)
    assert w["from"] >= live + t2.STALL_FROM_S - 0.01 and w["sand"] is None          # (rounded to 0.01 s)
    assert w["gap"] >= w["from"] + t2.STALL_ROOM_S and w["press"] >= w["gap"] + t2.STALL_GAP_S + t2.STALL_RECOVER_S
    valid = [r for r in rows if r["has"] and r["valid"] and r["t"] >= w["from"]]
    jump = next(b["t"] for a, b in zip(valid, valid[1:]) if t2.torus(a["x"], a["z"], b["x"], b["z"]) >= 64.0)
    assert w["press"] + t2.STALL_PRESS_S + t2.RECOVER_S <= jump                       # the host's entry never pulls the guest mid-row
    monkeypatch.setattr(t2, "SAND_AT", (300.0, -300.0))
    ws = t2.stall_windows(rows)
    assert ws["sand"] is not None and ws["gap"] + t2.STALL_GAP_S <= ws["sand"] and ws["sand"] + t2.STALL_PRESS_S <= ws["press"]
    monkeypatch.setattr(t2, "STALL_RECOVER_S", 30.0)                                  # no room before the tile: None, never a late window
    assert t2.stall_windows(rows)["press"] is None
    assert t2.stall_windows([]) == {"from": None, "gap": None, "sand": None, "press": None}


# ================================================================================================ the pure judges
class S:
    """A sample: frame, ui, world, the raw document (round B's blocks)."""

    def __init__(self, frame, *, ui="WorldHUD", world=9011, field=0, x=68.0, z=-444.0, br=True, freeze=True, why_f=None, walk=None,
                 fp=None, lane=None, line=None, ghost=None, dot=None, hg=None, session=None, out=None, rejoin=None, nm=3):
        self.frame, self.ui_state, self.world_id, self.field_id = frame, ui, world, field
        self.world_x, self.world_z, self.control, self.fading = x, z, True, False
        ns = {"world": {"freeze": {"on": freeze, "why": why_f, "edges": 0, "keys": 0, "battles": 0, "map": 0}},
              "session": dict(session or {})}
        for k, v in (("walk", walk), ("fp", fp), ("lane", lane), ("line", line), ("ghost", ghost), ("dot", dot), ("out", out),
                     ("rejoin", rejoin)):
            if v is not None:
                ns["world"][k] = v
        if isinstance(freeze, dict):
            ns["world"]["freeze"] = freeze
        if hg is not None:
            ns["host"] = {"world": {"guest": hg}}
        self.raw = {"world": {"x": x, "z": z, "block_ready": br, "ticks": frame, "next_mode": nm}, "netsync": ns}


def _w(**kw):
    w = {"free": True, "why": None, "stall_held": False, "line": None, "map": {"opens": 0, "coop_closes": 0, "last_close": None}}
    w.update(kw)
    return w


def test_wr_free_and_wr_pair_go_red_on_each_wrong_shape(t2):
    free = S(1, walk=_w(), fp={"state": "match"}, lane={"tx": {"state": BW.WW_ST_WALKING}})
    assert t2.judge_wr_free(free, free, 12.0, 40)[0]
    assert not t2.judge_wr_free(free, free, 1.0, 40)[0]                                # held
    assert not t2.judge_wr_free(None, free, 12.0, 40)[0]                               # never read free after the landing
    assert not t2.judge_wr_free(free, S(1, walk=_w(), fp={"state": "mismatch"}, lane={"tx": {"state": 2}}), 12.0, 40)[0]
    assert not t2.judge_wr_free(free, S(1, walk=_w(), fp={"state": "match"}, lane={"tx": {"state": 0}}), 12.0, 40)[0]   # no b1
    assert not t2.judge_wr_free(free, S(1, freeze=False, walk=_w(), fp={"state": "match"}, lane={"tx": {"state": 2}}), 12.0, 40)[0]
    ok, why = t2.judge_wr_free(None, S(1), 0.0, 40)
    assert not ok and why.startswith("absent")
    pair = [S(i, walk=_w(free=False, why="pairing", line=BW.WORDS_WW_WALK_PAIRING), out={"starts": 0}) for i in range(4)]
    base = S(0, out={"starts": 0})
    assert t2.judge_wr_pair(pair, base)[0]
    assert not t2.judge_wr_pair(pair[:-1] + [S(9, walk=_w(free=False, why="checking", line=BW.WORDS_WW_WALK_CHECKING),
                                                 out={"starts": 0})], base)[0]
    assert not t2.judge_wr_pair(pair + [S(9, walk=_w(free=False, why="pairing", line=BW.WORDS_WW_WALK_PAIRING), out={"starts": 1})],
                                base)[0]                                                 # a follow-out started: it was never world-paired
    mir = [S(i, walk=_w(free=False, why="pairing", line=BW.WORDS_WW_WALK_PAIRING), out={"starts": 0}, session={"mirroring": True})
           for i in range(3)]
    assert not t2.judge_wr_pair(mir, base)[0]                                          # mirroring: not world-paired
    assert t2.pair_old_shape([S(i, out={"starts": 0}) for i in range(3)]) and not t2.pair_old_shape(pair)


def _lane(age):
    return {"arrival_age_ms": age, "tx": {"state": 0}}


def test_the_stall_hole_judges_go_red_on_each_wrong_shape(t2):
    edge = {"on": True, "why": "session", "edges": 3, "keys": 0, "battles": 0, "map": 0}
    base = S(0, freeze=dict(edge, why="live"), walk=_w(free=False, why="pairing"), lane=_lane(30))
    held = [S(i, freeze=dict(edge), walk=_w(free=False, why="pairing", stall_held=age >= 2000), lane=_lane(age))
            for i, age in enumerate((900, 1900, 2150, 2250, 40))]
    assert t2.judge_stallhole(base, held, [])[0]
    ok, why = t2.judge_stallhole(base, [s for s in held if (s.raw["netsync"]["world"]["lane"]["arrival_age_ms"] < 2000)], [])
    assert not ok and "never staled" in why                                            # a blackhole that never staled: not reached
    lifted = held[:3] + [S(9, freeze=dict(edge, on=False), walk=_w(free=False), lane=_lane(2250))]
    assert not t2.judge_stallhole(base, lifted, [])[0] and t2.stall_lifted(lifted, [])
    edged = held[:-1] + [S(9, freeze=dict(edge, edges=4), walk=_w(free=False, why="pairing"), lane=_lane(40))]
    assert not t2.judge_stallhole(base, edged, [])[0]                                  # a re-freeze edge: the freeze fell
    unheld = [S(i, freeze=dict(edge, why="live"), walk=_w(free=False, stall_held=False), lane=_lane(2200)) for i in range(2)]
    assert not t2.judge_stallhole(base, unheld, [])[0]                                 # frozen, but never by the hole
    assert not t2.judge_stallhole(base, held, ["[NetSync] world freeze lifted on world map 9011: the session's link is down"])[0]
    assert not t2.stall_lifted(held, [])
    # the presses
    pbase = S(0, freeze=dict(edge, keys=5), walk=_w(free=False, stall_held=True), lane=_lane(2400))
    after = [S(1, freeze=dict(edge, keys=6), walk=_w(free=False))]
    assert t2.judge_stall_press({"kind": "location", "base": pbase, "after": after})[0]
    assert not t2.judge_stall_press({"kind": "location", "base": pbase, "after": after + [S(2, ui="FieldHUD", field=300)]})[0]
    assert not t2.judge_stall_press({"kind": "location", "base": pbase, "after": after + [S(2, nm=1)]})[0]   # the MAPJUMP started
    assert not t2.judge_stall_press({"kind": "location", "base": pbase, "after": [S(1, freeze=dict(edge, keys=5))]})[0]
    early = S(0, freeze=dict(edge, keys=5), walk=_w(free=False, stall_held=False), lane=_lane(1500))
    ok, why = t2.judge_stall_press({"kind": "location", "base": early, "after": after})
    assert not ok and "before the stall" in why
    sand = [S(1, freeze=dict(edge, keys=5, battles=1))]
    assert t2.judge_stall_press({"kind": "sand", "base": pbase, "after": sand})[0]
    assert t2.judge_stall_press({"kind": "sand", "base": pbase, "after": after})[0]   # the mask took it (K1 names which)
    assert not t2.judge_stall_press({"kind": "sand", "base": pbase, "after": sand + [S(2, ui="BattleHUD")]})[0]
    assert not t2.judge_stall_press({"kind": "sand", "base": pbase, "after": [S(1, freeze=dict(edge, keys=5))]})[0]
    assert t2.press_leaked([{"base": pbase, "after": after + [S(2, nm=1)]}])
    assert t2.press_leaked([{"base": S(0, freeze=dict(edge, on=False, keys=5), lane=_lane(2400)), "after": [S(1, freeze=dict(edge, keys=5))]}])
    assert not t2.press_leaked([{"base": pbase, "after": after}])
    assert not t2.judge_stall_keys([])[0]
    ok, why = t2.judge_stall_keys([{"kind": "location", "base": S(0, freeze=dict(edge, on=False), lane=_lane(2400)), "after": after}])
    assert not ok and why.startswith("absent")


def _hs(i, asked, *, words=None, drawn=True, place=4, shown=True):
    return S(i, walk=_w(), line={"asked": asked, "text": words, "drawn": drawn}, hg={"place": place}, ghost={"shown": shown})


def test_the_t2_hb_judge_goes_red_on_each_wrong_shape(t2):
    n = t2.THB_SETTLE + t2.THB_MIN
    older = [_hs(i, "older", words=BW.WORDS_WW_HOST_OLDER) for i in range(n)]
    line = "[NetSync] " + "host world: the partner's walk -- older (\"x\") -- the guest's state 0x86"
    assert t2.judge_thb("older", older, [line])[0]
    assert not t2.judge_thb("older", older, [])[0]                                     # no walk log line
    assert not t2.judge_thb("older", older[:-1] + [_hs(99, None)], [line])[0]          # the line dropped at the end
    assert not t2.judge_thb("older", older[:-1] + [_hs(99, "older", words=BW.WORDS_WW_HOST_OLDER, drawn=False)], [line])[0]
    assert not t2.judge_thb("older", older[:-1] + [_hs(99, "fp_differs", words=BW.WORDS_WW_HOST_FP_DIFFERS)], [line])[0]
    assert not t2.judge_thb("older", [_hs(i, "older", words=BW.WORDS_WW_HOST_OLDER, place=3) for i in range(n)], [line])[0]
    fp = [_hs(i, "fp_differs", words=BW.WORDS_WW_HOST_FP_DIFFERS) for i in range(n)]
    fl = BW.LOG_WW_HOST_WALK + "fp_differs (\"x\")"
    assert t2.judge_thb("fp", fp, [fl, BW.log_ww_fp_host(9011, 0x1234, 0xDEAD)])[0]
    assert not t2.judge_thb("fp", fp, [fl])[0]                                          # the host's own fingerprint line missing
    quiet = [_hs(i, None) for i in range(n)]
    assert t2.judge_thb("quiet", quiet, [])[0]
    assert not t2.judge_thb("quiet", quiet + [_hs(99, "cant_walk")], [])[0]
    assert not t2.judge_thb("quiet", quiet, [BW.LOG_WW_HOST_WALK + "older"])[0]
    assert not t2.judge_thb("quiet", [_hs(i, None, shown=False) for i in range(n)], [])[0]
    assert t2.thb_quiet_shape(quiet) and not t2.thb_quiet_shape(older)
    # [W2 critic] a phase whose guest never reached place 4 asks no line either -- that is no measurement of OLD's quiet
    assert not t2.thb_quiet_shape([]) and not t2.thb_quiet_shape([_hs(i, None, place=3) for i in range(n)])
    assert not t2.thb_quiet_shape(quiet[:t2.THB_SETTLE + t2.THB_MIN - 1])


def _tx(seq, x, z):
    return {"tx": {"seq": seq, "x": x, "z": z, "mode": 0}, "rx": {"seq": seq}}


def _ds(i, *, own=(68.0, -444.0), ghost_xz=None, seq=None, mover=None, free=True):
    """A duo sample: its own pose, its ghost of the other at ``ghost_xz`` and the rx seq it holds, its own tx (``mover``: seq, x, z)."""
    lane = {"tx": {}, "rx": {}}
    if mover is not None:
        lane["tx"] = {"seq": mover[0], "x": mover[1], "z": mover[2], "mode": 0}
    if seq is not None:
        lane["rx"] = {"seq": seq}
    g = {"placed": ghost_xz is not None, "shown": ghost_xz is not None}
    if ghost_xz is not None:
        g.update(x=ghost_xz[0], z=ghost_xz[1], tx=ghost_xz[0], tz=ghost_xz[1])
    return S(i, x=own[0], z=own[1], walk=_w(free=free, why=None if free else "lever"), lane=lane, ghost=g)


def test_the_duo_walk_judges_go_red_on_each_wrong_shape(t2):
    n = t2.D_MIN_SAMPLES + 2
    mover = [_ds(i, own=(68.0 + 3.0 * i, -444.0), mover=(100 + i, 68.0 + 3.0 * i, -444.0)) for i in range(n)]
    still = [_ds(i, ghost_xz=(68.0 + 3.0 * i, -444.0), seq=100 + i) for i in range(n)]
    h0 = h1 = (68.0, -444.0)
    assert t2.judge_dw("w1", still, mover, h0, h1, None, None)[0]                    # the guest moves, the host's ghost tracks it
    assert not t2.judge_dw("w1", still, mover, h0, (90.0, -444.0), None, None)[0]     # the host moved too
    off = still[:-1] + [_ds(99, ghost_xz=(10.0, -10.0), seq=100 + n - 1)]
    assert not t2.judge_dw("w1", off, mover, h0, h1, None, None)[0]                  # the ghost off the mover's trailer
    frozen_mover = [_ds(i, mover=(100 + i, 68.0, -444.0), free=False) for i in range(n)]
    ok, _why = t2.judge_dw("w1", [_ds(i, ghost_xz=(68.0, -444.0), seq=100 + i) for i in range(n)], frozen_mover, h0, h1, None, None)
    assert not ok                                                                     # the guest never moved (and is not free)
    host_moves = [_ds(i, mover=(200 + i, 68.0 + 3.0 * i, -444.0)) for i in range(n)]
    guest_sees = [_ds(i, ghost_xz=(68.0 + 3.0 * i, -444.0), seq=200 + i) for i in range(n)]
    assert t2.judge_dw("w2", host_moves, guest_sees, None, None, (68.0, -444.0), (68.0, -444.0))[0]
    lever = [_ds(i, ghost_xz=(68.0 + 3.0 * i, -444.0), seq=200 + i, free=False) for i in range(n)]
    assert not t2.judge_dw("w2", host_moves, lever, None, None, (68.0, -444.0), (68.0, -444.0))[0]   # `walk off`: not free
    assert t2.dw_frozen(lever) and not t2.dw_frozen(guest_sees)
    ok, why = t2.judge_dw("w2", host_moves, [S(i) for i in range(n)], None, None, (1, 1), (1, 1))
    assert not ok and why.startswith("absent")
    # [W2 critic] D-W1 / D-W3's OLD shape: the guest's own hold HELD over judged samples -- an empty Tap (0.0 u) measures nothing
    held = [_ds(i, free=False) for i in range(n)]
    assert t2.dw_held(held) and not t2.dw_held([]) and not t2.dw_held(mover)
    assert not t2.dw_held([S(i, br=False) for i in range(n)])                         # THE PRE-INIT SAMPLE: none judged
    # ...and D-BATTLE / D-REJOIN-WAIT's: frozen AND not walking (`not walk_free` alone holds on every s166 state)
    assert t2.frozen_not_walking(S(1)) and not t2.frozen_not_walking(S(1, freeze=False)) and not t2.frozen_not_walking(None)
    assert not t2.frozen_not_walking(S(1, walk=_w()))


def test_the_duo_refusal_far_map_and_wait_judges_go_red_on_each_wrong_shape(t2):
    good = S(1, walk=_w(), fp={"state": "match"}, lane={"caps": {"peer": 3}})
    assert t2.judge_dw_free(good, good)[0]
    assert not t2.judge_dw_free(S(1, walk=_w(), fp={"state": "match"}, lane={"caps": {"peer": 1}}), good)[0]   # an s166-shaped peer
    assert not t2.judge_dw_free(S(1, walk=_w(free=False, why="lever"), fp={"state": "match"}, lane={"caps": {"peer": 3}}), good)[0]
    hit = S(1, line={"asked": "fp_differs", "text": BW.WORDS_WW_HOST_FP_DIFFERS, "drawn": True})
    lines = [BW.LOG_WW_HOST_WALK + "fp_differs (\"x\")", BW.log_ww_fp_host(9011, 1, 2)]
    assert t2.judge_host_fp([hit], lines)[0] and not t2.judge_host_fp([S(1)], lines)[0] and not t2.judge_host_fp([hit], lines[:1])[0]
    rejoin_ok = (True, "landed")
    far = S(1, x=68.0, z=-444.0, walk=_w())
    assert t2.judge_d_far(far, t2.ICE_TILE, rejoin_ok)[0]
    assert not t2.judge_d_far(S(1, x=1190.0, z=-790.0, walk=_w()), t2.ICE_TILE, rejoin_ok)[0]      # standing on the host
    assert not t2.judge_d_far(S(1, walk=_w(free=False, why="lever")), t2.ICE_TILE, rejoin_ok)[0]
    assert not t2.judge_d_far(far, t2.ICE_TILE, (False, "never"))[0]
    # D-MAP: open (FullMap, opens +1, map +0), then the co-op close BEFORE the rejoin's line, then landed
    mb = S(0, walk=_w(), dot={"hud": "HUD"})
    opened = [S(1, walk=_w(map={"opens": 1, "coop_closes": 0, "last_close": None}), dot={"hud": "FullMap"})]
    rj = [S(2, walk=_w(map={"opens": 1, "coop_closes": 1, "last_close": "rejoin"}), dot={"hud": "HUDNoMiniMap"})]
    cl = BW.log_ww_map_closed("rejoin", 9011, 300)
    arm = "[NetSync] " + BW.log_world_rejoining(300, 9011, True)
    m = {"base": mb, "opened": opened, "rejoin": rj, "lines": [cl, arm], "landed": True, "boot": None}
    assert t2.judge_d_map(m)[0]
    assert not t2.judge_d_map(dict(m, lines=[arm, cl]))[0]                           # the arm first: the close came too late
    assert not t2.judge_d_map(dict(m, opened=[S(1, walk=_w(), dot={"hud": "HUD"})]))[0]
    # [W2 critic] the OLD / lever shape: never FullMap AND the Select taken a frozen way -- refused (freeze.map +1) or decision 27's close
    refused = S(1, walk=_w(), dot={"hud": "HUD"}, freeze={"on": True, "why": None, "edges": 0, "keys": 0, "battles": 0, "map": 1})
    assert t2.map_never_full(dict(m, opened=[refused])) and t2.map_never_full(dict(m, opened=[S(1, dot={"hud": "HUDNoMiniMap"})]))
    assert not t2.map_never_full(dict(m, opened=[mb]))                               # a Select never read: no measurement
    assert not t2.map_never_full(dict(m, opened=opened)) and not t2.map_never_full(dict(m, base=S(0, ui="FieldHUD"), opened=[refused]))
    assert not t2.judge_d_map(dict(m, rejoin=[S(2, walk=_w(map={"opens": 1, "coop_closes": 1, "last_close": "boot"}))]))[0]
    assert not t2.judge_d_map(dict(m, landed=False))[0]
    assert not t2.judge_d_map(dict(m, boot=(False, "no boot close")))[0]
    # D-REJOIN-WAIT
    on = {"shown": True, "want": True}
    wb = S(0, walk=_w(), out={"starts": 0}, rejoin={"lands": 0}, ghost=dict(on, snaps=0), lane={"rx": {"place": 4}})
    waits = [S(1, rejoin={"lands": 0, "why": "a world script holds control"}, ghost={"shown": False, "want": False},
               lane={"rx": {"place": 1}})]
    after = S(2, walk=_w(), out={"starts": 0}, rejoin={"lands": 0}, ghost=dict(on, snaps=1), lane={"rx": {"place": 4}})
    w = {"base": wb, "samples": waits + [after], "after": after, "entered": True, "returned": True}
    assert t2.judge_d_wait(w)[0]
    assert not t2.judge_d_wait(dict(w, after=S(2, walk=_w(), out={"starts": 1}, rejoin={"lands": 0}, ghost=dict(on, snaps=1))))[0]
    assert not t2.judge_d_wait(dict(w, after=S(2, walk=_w(), out={"starts": 0}, rejoin={"lands": 1}, ghost=dict(on, snaps=1))))[0]
    assert not t2.judge_d_wait(dict(w, samples=waits + [S(3, ui="FieldHUD", field=300)] + [after]))[0]   # it left the world
    assert not t2.judge_d_wait(dict(w, after=S(2, walk=_w(), out={"starts": 0}, rejoin={"lands": 0}, ghost=dict(on, snaps=0))))[0]
    assert not t2.judge_d_wait(dict(w, samples=[after]))[0]                          # the rejoin never read waiting
    assert not t2.judge_d_wait(dict(w, returned=False))[0]
    # [W2 critic] LIVE VERDICT vs LAST DRAWN: a 'hidden' frame whose live verdict still WANTS the ghost (the draw not caught up) is no
    # hide, and a shown ghost the verdict no longer wants is no re-show
    pre_draw = [S(1, rejoin={"lands": 0, "why": "a world script holds control"}, ghost={"shown": False, "want": True},
                  lane={"rx": {"place": 1}})]
    assert not t2.judge_d_wait(dict(w, samples=pre_draw + [after]))[0]
    stale = S(2, walk=_w(), out={"starts": 0}, rejoin={"lands": 0}, ghost={"snaps": 1, "shown": True, "want": False},
              lane={"rx": {"place": 4}})
    assert not t2.judge_d_wait(dict(w, samples=waits + [stale], after=stale))[0]


def test_d_battles_judge_goes_red_on_each_wrong_shape(t2):
    """D-BATTLE never runs on the stand-in (no diorama model): its judge is proven HERE -- apart, the boot's co-op close (the review's R1:
    an open map used to sit the fight out), booted, back at its OWN pose, free again."""
    pre = S(0, x=68.0, z=-444.0, walk=_w(map={"opens": 1, "coop_closes": 0, "last_close": None}))
    host = S(0, x=120.0, z=-444.0)
    after = S(1, x=68.5, z=-444.0, walk=_w(map={"opens": 1, "coop_closes": 1, "last_close": "boot"}))
    b = {"pre": pre, "host_pre": host, "opened": True, "after": after, "free_after": True, "booted": True,
         "lines": [BW.log_ww_map_closed("boot", 9011)], "why": ""}
    assert t2.judge_d_battle_b(b)[0]
    assert not t2.judge_d_battle_b(dict(b, host_pre=S(0, x=70.0, z=-444.0)))[0]       # not apart: "its OWN pose" proves nothing
    assert not t2.judge_d_battle_b(dict(b, after=S(1, x=120.0, z=-444.0, walk=after.raw["netsync"]["world"]["walk"])))[0]   # the host's
    assert not t2.judge_d_battle_b(dict(b, booted=False))[0]
    assert not t2.judge_d_battle_b(dict(b, free_after=False))[0]
    assert not t2.judge_d_battle_b(dict(b, lines=[]))[0]                               # no boot close line
    assert not t2.judge_d_battle_b(dict(b, opened=False))[0]
    ok, why = t2.judge_d_battle_b(dict(b, after=S(1)))
    assert not ok and why.startswith("absent")


# ================================================================================================ the stand-in smokes
_CHILD = r'''
import datetime as _dt, importlib.util, json, os, pathlib, struct, sys, tempfile, threading, time
scen, tools, kit = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, tools)
sys.path.insert(0, kit)
doc = json.loads(sys.stdin.read() or "{}")
for k in [k for k in os.environ if k.startswith("COOP_")]:
    os.environ.pop(k)
os.environ["COOP_WWT_DUO_BATTLE"] = "0"
from harness import Session
from harness import fakegame as FG
from harness import battlewire as BW
from harness import coop_peer as CP
def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(scen, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
t2 = load("coop_world_walk_t2")
ww, wf, cw, pb, cb = t2.ww, t2.wf, t2.cw, t2.pb, t2.cb
SPEED = 8.0
for k, v in dict(REFUSE_S=1.0, START_S=4.0, LEAVE_S=12.0, FIELD_S=10.0, HOME_S=10.0, DOT_S=2.0, STALE_S=0.6, PICK_S=0.3,
                 HOLD_SETTLE_S=0.3, TILE_SLACK_S=12.0, REJOIN_S=15.0, FO_S=12.0, DUO_HOME_S=12.0, REPLAY_SPEED=SPEED).items():
    setattr(wf, k, v)
for k, v in dict(FIELD_S=10.0, DIAL_S=8.0, REJOIN_S=12.0).items():
    setattr(cw, k, v)
for k, v in dict(WIRE_S=2.0, WIRE_CLEAR_S=1.0, WIRE_PAIR_S=10.0, WIRE_WORLD_S=20.0, LAND_S=30.0, EVENT_S=30.0, TH_A_S=20.0,
                 TH_B_S=8.0, TH_C_S=1.5, TH_TAIL_S=0.4, TH_DIAL_S=10.0, POLL_S=0.004, D_S=0.5, D_LAND_S=15.0, TAP_S=0.003,
                 D_WALK_FRAMES=300, D_WALK_S=1.0, D_WALK_TAIL_S=0.1, D_HOLD_SETTLE_S=0.05, D_HOLD_READ_S=2.0,
                 # [s167] round B's waits on the stand-in's 10x virtual clock (the windows are tape seconds; the waits wall seconds)
                 STALL_ROOM_S=6.0, STALL_RECOVER_S=12.0, STALL_TAIL_S=0.15, STALL_PAIR_S=5.0, PRESS_WATCH_S=0.4, THB_PHASE_S=1.0,
                 B_READY_S=4.0, B_CASE_S=2.0, FP_READY_S=8.0, D_WAIT_S=0.4, D_FOLLOW_S=3.0).items():
    setattr(t2, k, v)
BASE_T2 = {k: getattr(t2, k) for k in ('STALL_ROOM_S', 'STALL_RECOVER_S', 'STALL_TAIL_S', 'PRESS_WATCH_S')}
FAKES = []

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
    if run.get("stage", "s167") == "s167":
        f.world_walk_pieces = FG.FAKE_WORLD_WALK_S167_PIECES
    f.swap_qpc = None
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": float(run.get("ow_speed", 0.4)), "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(run.get("faults", ()))
    f.world_out_fade_frames = int(run.get("fade", 120))
    sand = run.get("sand")
    if sand is not None:                                        # the place-52 clause: a teleport onto the stand puts him on 52
        orig = f._execute
        def ex(step, _o=orig, _f=f, _s=sand):
            out = _o(step)
            if step and step[0] == "teleport" and len(step) >= 3:
                _f.world_area = 52 if abs(float(step[1]) - _s[0]) < 1.0 and abs(float(step[2]) - _s[1]) < 1.0 else 0
            return out
        f._execute = ex
    FAKES.append(f)
    return f

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1500]) for r in checks]
    return {"red": sorted(c for c, ok, _d in rows if not ok), "all": [c for c, _ok, _d in rows],
            "detail": {c: d for c, _ok, d in rows}}

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

class _Peer(pb.PeerProc):
    def _say(self, msg):
        n = _dt.datetime.now()
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[coop-peer {n:%H:%M:%S}.{n.microsecond // 1000:03d}] {msg}\n")
    def _arg(self, name, all_=False):
        vals = [self.args[i + 1] for i, a in enumerate(self.args) if a == name and i + 1 < len(self.args)]
        return vals if all_ else (vals[0] if vals else None)
    def start(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.started = _dt.datetime.now()
        self._halt = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
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

class StubReplay(_Peer):
    """replay-host's stand-in (round A's, on the VIRTUAL clock) plus round B's transport facts: `--from` (the replay starts at that tape
    second), the session's StaleMs (no host frame delivered for 2 s of the stand-in's clock -> the position lane invalid,
    IsLiveFollowedSession false; the next frame -> valid again) and section 11 (each host state frame's, or none: ObserveHostDialog)."""
    def _now(self, f):
        return f.rt
    def _run(self):
        f = FAKES[-1]
        port, code = self._arg("--port"), self._arg("--code")
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub replay-host")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not f.dial_socket:
            time.sleep(0.02)
        if self._halt.is_set() or not f.dial_socket:
            return
        self._say(f"GUEST game connected (session {code})")
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{port}/sess/{code}?role=guest")
        _h, recs, _torn = CP.read_tape(self.args[0])
        frames = list(CP.host_frames(recs))
        frm = self._arg("--from")
        if frm is not None:
            frames = [x for x in frames if x[0].t >= float(frm)]
        mode = self._arg("--wire") or "auto"
        guest = f.netsync_wire_now()
        send, how = CP.replay_send_wire(mode, guest, CP.tape_wire(recs))
        self._say(CP.GUEST_WIRE_LINE.format(guest=guest, send=send, how=how))
        t0 = frames[0][0].t
        bhs = [(float(a), float(n)) for a, n in zip(self._arg("--blackhole-at", True), self._arg("--blackhole-for", True))]
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape {frames[-1][0].t:.2f} s")
        now0 = self._now(f)
        state = {"field": None, "flags": -1, "story": None, "first": True, "fresh_t": None}
        def deliver(w, p, t=None):
            if send != guest:
                f.wire_frame(send, p)
                return
            if w == CP.TYPE_POS:
                f.wire_frame(None, p)
                d = CP.parse_pos_payload(p)
                if d and d["field"] != state["field"]:
                    if t is not None:
                        self._say(f"tape {t:.2f}: host field {state['field'] if state['field'] is not None else 'none'} -> {d['field']}")
                    state["field"] = d["field"]
            elif w == CP.TYPE_STATE:
                sec = pb.state_sections(p)
                if 0 in sec:
                    state["story"] = bytes(sec[0])
                if 7 in sec:
                    v = BW.parse_dialog_section(sec[7])
                    state["flags"] = v["flags"] if v else state["flags"]
                if f.coop_follow is not None:
                    f.fp_host_section(sec.get(BW.SECTION_FP))           # [s167] section 11, or none (the copy clears)
            if state["field"] is None:
                return
            if state["first"]:
                f.follow_session(state["field"], flags=state["flags"], fresh=True, story=state["story"], pair_kick=True)
                state["first"] = False
            else:
                f.host_at(state["field"], flags=state["flags"], story=state["story"], valid=True)
            state["fresh_t"] = self._now(f)
            if w == CP.TYPE_STATE:
                feed_pose(f, p)
        said = set()
        edges = sorted((a, "BLACKHOLE", n) for a, n in bhs)
        def stale_check():
            if f.coop_follow is not None and state["fresh_t"] is not None and f.coop_follow["valid"] \
                    and self._now(f) - state["fresh_t"] >= BW.STALE_MS / 1000.0:
                f.host_at(valid=False)                                     # GetRemote past StaleMs: the lane invalid
        for r, w, p in frames:
            due = now0 + (r.t - t0)
            while self._now(f) < due and not self._halt.is_set():
                stale_check()
                time.sleep(0.001)
            if self._halt.is_set():
                return
            for a, kind, n in edges:
                if r.t >= a and (a, kind, "b") not in said:
                    said.add((a, kind, "b"))
                    self._say(f"{kind} at tape {r.t:.2f} s: the link stays open -- the stub")
                if r.t >= a + n and (a, kind, "e") not in said and (a, kind, "b") in said:
                    said.add((a, kind, "e"))
                    self._say(f"{kind} over at tape {r.t:.2f} s: host frames resume -- the stub")
            if any(a <= r.t < a + n for a, _k, n in edges):
                stale_check()
                continue
            deliver(w, p, t=r.t)
        self._say(f"replay done (end of tape): sent {len(frames)}, dropped in blackholes 0, unsent (no guest attached) 0, max lag "
                  "0.000 s")
        while not self._halt.is_set():                                     # `--at-end hold`: the link open, silent
            stale_check()
            time.sleep(0.005)

class StubServe(_Peer):
    """serve-guest's stand-in: its REAL model on the host stand-in's VIRTUAL clock, every type-0 frame onto FakeGame.wire_frame -- and
    [s167] the HOST's own type-0 frames fed back into the model (on_host_frame: `--caps auto` adopts the host's word, `--digest echo`
    its digest), as the real serve-guest reads them off its socket."""
    def _run(self):
        f = FAKES[-1]
        port = self._arg("--port")
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub serve-guest")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not (f.netsync.get("role") == "host" and f.netsync.get("enabled")):
            time.sleep(0.02)
        if self._halt.is_set():
            return
        args = CP.build_parser().parse_args(["serve-guest"] + list(self.args))
        model = CP._model_from(args)
        wire = f.netsync_wire_now()
        code = f.session_code
        self._say(f"HOST game connected (session {code}) -- this tool is its guest now")
        f._mlog(f"[NetSync] relay connected ws://127.0.0.1:{port}/sess/{code}?role=host")
        self._say(CP.HOST_WIRE_LINE.format(host=wire, send=wire, how="the host's own"))
        self.sent_recs = []
        rt0 = f.rt
        nxt = rt0
        while not self._halt.is_set():
            if f.rt < nxt:
                time.sleep(0.002)
                continue
            nxt = f.rt + CP.TICK_S
            s = f.rt - rt0
            ht = f.world_tx_frame()
            if ht is not None:
                model.on_host_frame(CP.TYPE_POS, ht, s)
            for fr in model.outgoing(s, wire):
                got = CP.parse_frame(fr)
                if got is None:
                    continue
                self.sent_recs.append(CP.Record(s, 1, fr))
                if got[0] == CP.TYPE_POS:
                    f.wire_frame(None, got[1])
    def stop(self, timeout=10.0):
        out = super().stop(timeout)
        tp = self._arg("--tap")
        if tp:
            head = json.dumps({"tool": "stub", "started": _dt.datetime.now().isoformat()}).encode("utf-8")
            body = b"".join(struct.pack("<dBI", r.t, r.dir, len(r.payload)) + r.payload for r in getattr(self, "sent_recs", []))
            pathlib.Path(tp).write_bytes(b"F9TAPE01" + struct.pack("<I", len(head)) + head + body)
        return out

class PeerSwitch(pb.PeerProc):
    def __new__(cls, mode, args, **kw):
        k = StubReplay if mode == "replay-host" else StubServe
        return k(mode, args, **kw)

def stubs():
    pb.IniGuard = StubIni
    pb.port_free = lambda port, host="127.0.0.1": (True, "")
    pb.PeerProc = PeerSwitch

def t2_run(run):
    t = root()
    stubs()
    leg = run["leg"]
    os.environ["COOP_TAPE_DIR"] = str(t / "tapes")                 # no recorded ROAM tape: THE INSTRUMENT
    os.environ.pop("COOP_TAPE_WORLD_ROAM", None)
    if leg in ("roam", "freeze"):                                     # round A's legs (the regression re-key): its own instrument
        os.environ["COOP_TAPE_WORLD_ROAM"] = str(t2.write_instrument(t / "roam-INSTRUMENT.f9tape", CP))
    if run.get("sand") is not None:
        t2.SAND_AT = tuple(run["sand"])
    else:
        t2.SAND_AT = None
    for k, v in dict(BASE_T2, **run.get("consts", {})).items():
        setattr(t2, k, v)                                               # a run's own waits (restored to the child's for the next)
    f = fake_for(t, run)
    cb.CALIBRATE = bool(run.get("cal"))
    t2.LEG, t2.LEVER_RAW = leg, run.get("lever")
    t2.DUO_MODE = "a"
    with session(t, f) as g:
        t2.run(g)
        out = rows_of(list(g.checks))
    sent = [ln.split("|M| ", 1)[-1] for ln in (t / "Memoria.log").read_text(encoding="utf-8").splitlines()
            if "harness: worldwalk " in ln]
    out["acks"] = sent
    return out

class Link(threading.Thread):
    """The duo's stub TRANSPORT (round A's: s165's seams onto the guest, each game's type-0 slot onto the other) -- plus [s167] the HOST's
    section 11 onto the guest (FpSectionSendRule over the host stand-in: the host role, both caps b1, its live world the fingerprint's,
    its digest nonzero; else none: the guest's copy clears)."""
    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
    def run(self):
        sent, landed = None, False
        while not self.halt.is_set():
            h, g = self.h, self.g
            g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes))
            w = h.world
            if h.ui_state == "WorldHUD" and w.get("x") is not None and w.get("id"):
                g.host_world_pose(float(w["x"]), float(w["z"]), idx=int(w["id"]) - 9000, mode=int(w.get("vehicle") or 0))
            it = h.host_field_intent
            if it is not None and it != sent:
                sent, landed = it, False
                g.host_intent(it[1])
            if sent is not None and g.coop_follow is not None:
                # [s167] section 4's life (s164 IntentLifeRule): once the host landed on the intent's field and LEFT it, the intent ends
                # ('left') -- the guest's deferred intent goes with it (a frame without section 4 is no intent)
                if h.host_lane_field() == sent[1]:
                    landed = True
                elif landed and g.coop_follow.get("intent") is not None:
                    g.host_at(intent=None)
            if g._wwb_on():
                fp = h._wwb["fp"]
                live = h.ui_state == "WorldHUD" and int(w.get("id") or 0) == int(fp.get("world") or -1)
                on = (h._wwb_on() and live and fp.get("ready") and fp.get("comps") is not None and h._wwb_real_digest() != 0
                      and h._wwb_own_caps() & BW.WW_CAP_WORLD_FP and g._wwb_own_caps() & BW.WW_CAP_WORLD_FP)
                g.fp_host_section(BW.ww_write_fp_section(int(fp["world"]), fp["comps"]) if on else None)
            ht, gt = h.world_tx_frame(), g.world_tx_frame()
            if ht is not None:
                g.wire_frame(None, ht)
            if gt is not None:
                h.wire_frame(None, gt)
            time.sleep(0.002)

class StubDuo:
    def __init__(self, host, guest):
        self.host, self.guest, self.strict, self.rows, self.notes = host, guest, True, [], []
    def check(self, ok, what, detail="", *, role=None, cid=None):
        self.rows.append((cid, bool(ok), str(detail)[:1500]))
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)

def duo(run):
    if run.get("norekey"):                                          # [s167] the re-key's own control: round A on s167 WITHOUT it
        ww.s166_lever_set = lambda g, st: (True, "")
    th, tg = root(), root()
    run = dict(run, fade=600)
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    fh.world_exit_frames = fgst.world_exit_frames = 240
    cb.CALIBRATE = bool(run.get("cal"))
    t2.LEVER_RAW = run.get("lever")
    t2.DUO_MODE = run.get("mode", "b")
    gh, gg = session(th, fh), session(tg, fgst)
    with gh, gg:
        for g in (gh, gg):
            g.newgame(settle=0)
            g.warp(cw.FARSHORE)
        fh.netsync.update(enabled=True, role="host", instance=True)
        fh.story_bytes[pb.MARKER_BYTE] = pb.MARKER_VALUE
        fgst.follow_session(cw.FARSHORE, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, story=bytes(fh.story_bytes), pair_kick=True)
        fgst.wf_follow_host_cfg = True                             # the duo guest's ini: FollowHost 1 (NetSyncVisitor.SuppressEncounters)
        link = Link(fh, fgst)
        link.start()
        gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
        d = StubDuo(gh, gg)
        try:
            t2.run_duo(d)
        finally:
            link.halt.set()
        acks = [ln.split("|M| ", 1)[-1] for t in (th, tg) for ln in (t / "Memoria.log").read_text(encoding="utf-8").splitlines()
                if "harness: worldwalk " in ln]
        return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                "detail": {c: dd for c, _ok, dd in d.rows}, "notes": list(d.notes), "acks": acks}

kinds = {"t2": t2_run, "duo": duo}
results = {}
for name, run in doc.get("runs", {}).items():
    t_start = time.time()
    results[name] = kinds[run["kind"]](run)
    results[name]["wall_s"] = round(time.time() - t_start, 1)
print(json.dumps(results))
'''


def _child(payload, *, timeout: float = 1500.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-6000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run(kind: str = "t2", **run) -> dict:
    return _child({"runs": {"r": dict(run, kind=kind)}})["r"]


def _show(r):
    return {c: r["detail"].get(c, "")[:900] for c in r["red"]}


GATE = "S167-WR-GATE"
_NOT_ON_STAND_IN = {"S167-D-BATTLE"}
#: the acks a round-B op leaves (the engine's whole line starts "[NetSync] harness: worldwalk <op> "): never on s166
_B_ACK = tuple(f"harness: worldwalk {op} " for op in BW.WORLDWALK_OPS_B)


def _cal_ok(r, cal):
    return cal in r["all"] and cal not in r["red"]


def _no_b_op(r) -> bool:
    return not any(a.split("[NetSync] ", 1)[-1].startswith(_B_ACK) for a in r["acks"])


# ---- T2-B (walk)
def test_s167t2_walk_is_green_on_the_s167_stand_in_but_the_owner_gate():
    r = _run(leg="walk")
    assert r["red"] == [GATE], _show(r)
    assert "THE INSTRUMENT" in r["detail"][GATE] and "calibrated to my own fingerprint" in r["detail"]["T2-TAPE"]
    assert "(world map meshes)" in r["detail"]["S167-WR-REFUSE"] and "mask': 63" in r["detail"]["S167-WR-REFUSE"]


def test_s167t2_walk_old_on_s166_and_the_lever_calibrate_exactly(t2):
    rs = _child({"runs": {"old": dict(kind="t2", leg="walk", stage="s166", cal=True),
                          "lev": dict(kind="t2", leg="walk", cal=True, lever="walk")}})
    old, lev = rs["old"], rs["lev"]
    assert set(old["red"]) == set(t2.B_T2_OLD_PREDICTED["walk"]) | {GATE} and _cal_ok(old, "S167-WALK-CAL"), _show(old)
    assert _no_b_op(old), old["acks"]                                               # s166: no round-B op is ever sent
    assert set(lev["red"]) == set(t2.B_T2_LEVER_PREDICTED[("walk", "walk")]) | {GATE} and _cal_ok(lev, "S167-WALK-CAL"), _show(lev)


# ---- WR-PAIR + W-STALLHOLE (stallhole)
def test_s167t2_stallhole_is_green_on_the_s167_stand_in_but_the_owner_gate():
    r = _run(leg="stallhole")
    assert r["red"] == [GATE], _show(r)
    assert "freeze.why on the stall ['session']" in r["detail"]["S167-W-STALLHOLE"], _show(r)


@pytest.mark.parametrize("lever", [None, "stallhold", "walk"])
def test_s167t2_stallhole_old_and_each_lever_calibrate_exactly(t2, lever):
    if lever is None:
        r = _run(leg="stallhole", stage="s166", cal=True)
        want = t2.B_T2_OLD_PREDICTED["stallhole"]
        assert _no_b_op(r), r["acks"]
        assert "the freeze off on [" in r["detail"]["S167-W-STALLHOLE"]           # s166's hole MEASURED: the stall lifts the freeze
    else:
        r = _run(leg="stallhole", cal=True, lever=lever)
        want = t2.B_T2_LEVER_PREDICTED[("stallhole", lever)]
    assert set(r["red"]) == set(want) | {GATE} and _cal_ok(r, "S167-STALLHOLE-CAL"), _show(r)


def test_s167t2_the_place_52_clause_holds_on_s167_and_measures_the_local_battle_on_s166():
    sand = [300.0, -300.0]
    rs = _child({"runs": {"new": dict(kind="t2", leg="stallhole", sand=sand, consts={"STALL_RECOVER_S": 8.0}),
                          "old": dict(kind="t2", leg="stallhole", sand=sand, stage="s166", cal=True, consts={"STALL_RECOVER_S": 8.0})}})
    new, old = rs["new"], rs["old"]
    assert new["red"] == [GATE] and "sand: frozen at the press True" in new["detail"]["S167-W-STALLHOLE-KEYS"], _show(new)
    assert "'BattleHUD'" in old["detail"]["S167-W-STALLHOLE-KEYS"] and _cal_ok(old, "S167-STALLHOLE-CAL"), _show(old)


# ---- T2-HB (hostb)
def test_s167t2_hostb_is_green_on_the_s167_host_stand_in():
    r = _run(leg="hostb")
    assert r["red"] == [], _show(r)
    assert "naming the guest's 0x0000DEAD 1x" in r["detail"]["S167-THB-FP"]


def test_s167t2_hostb_old_on_s166_and_the_lever_calibrate_exactly(t2):
    rs = _child({"runs": {"old": dict(kind="t2", leg="hostb", stage="s166", cal=True),
                          "lev": dict(kind="t2", leg="hostb", cal=True, lever="walk")}})
    old, lev = rs["old"], rs["lev"]
    assert set(old["red"]) == set(t2.B_T2_OLD_PREDICTED["hostb"]) and _cal_ok(old, "S167-HOSTB-CAL"), _show(old)
    assert _no_b_op(old), old["acks"]
    assert set(lev["red"]) == set(t2.B_T2_LEVER_PREDICTED[("hostb", "walk")]) and _cal_ok(lev, "S167-HOSTB-CAL"), _show(lev)


def test_s167t2_a_lever_that_is_not_the_legs_is_refused_before_anything_runs():
    r = _run(leg="walk", cal=True, lever="stallhold")
    assert r["red"] == ["S167-T2-LEVER"] and r["all"] == ["S167-T2-LEVER"], _show(r)


# ---- the stand-in's faults
#: every (leg, fault) of B_T2_FAULT_REDS (the tables test pins the two equal)
_FAULTS = [("stallhole", "stall_free"), ("stallhole", "pairing_free"), ("walk", "fp_ignored"), ("duo", "fp_ignored"),
           ("duo", "refuse_silent")]


@pytest.mark.parametrize("leg,fault", _FAULTS)
def test_s167t2_each_round_b_fault_turns_exactly_its_rows_red(t2, leg, fault):
    assert fault in t2.B_T2_FAULT_REDS[leg]
    if leg == "duo":
        r = _run("duo", faults=[fault])
        assert set(r["red"]) - _NOT_ON_STAND_IN == set(t2.B_T2_FAULT_REDS["duo"][fault]), _show(r)
    else:
        r = _run(leg=leg, faults=[fault])
        assert set(r["red"]) - {GATE} == set(t2.B_T2_FAULT_REDS[leg][fault]), _show(r)


# ---- the duo (COOP_WWT_DUO=b; D-BATTLE needs a diorama model: named "not run" on the stand-in, judged by its pure test)
def test_s167t2_the_round_b_duo_is_green_on_two_s167_stand_ins_but_the_named_battle():
    r = _run("duo")
    assert set(r["red"]) == _NOT_ON_STAND_IN, _show(r)
    assert "not run" in r["detail"]["S167-D-BATTLE"]
    assert "the close line at 0, the rejoin's line at 1" in r["detail"]["S167-D-MAP"], _show(r)
    assert "'fp_differs' asked + words + drawn on" in r["detail"]["S167-D-REFUSE"]


@pytest.mark.parametrize("lever", [None, "walk", "fullmap"])
def test_s167t2_the_round_b_duo_old_and_each_lever_calibrate_exactly(t2, lever):
    if lever is None:
        r = _run("duo", stage="s166", cal=True)
        want = set(t2.DUO_B_OLD_PREDICTED)
        assert _no_b_op(r), r["acks"]
    else:
        r = _run("duo", cal=True, lever=lever)
        want = set(t2.DUO_B_LEVER_PREDICTED[lever])
    assert set(r["red"]) - {"S167-D-CAL"} == want | _NOT_ON_STAND_IN and "S167-D-CAL" not in r["red"], _show(r)


# ---- THE REGRESSION RE-KEY: round A's legs on an s167 stand-in read s166 -- and without the re-key they do not
def test_s167t2_round_a_on_the_s167_stand_in_pulls_the_s166_lever_set_and_reads_s166():
    rs = _child({"runs": {"roam": dict(kind="t2", leg="roam"), "host": dict(kind="t2", leg="host"),
                          "duo": dict(kind="duo", mode="a"), "bare": dict(kind="duo", mode="a", norekey=True)}})
    assert rs["roam"]["red"] == ["S166-RM-GATE"], _show(rs["roam"])
    assert rs["host"]["red"] == [], _show(rs["host"])
    assert rs["duo"]["red"] == ["S166-D-BATTLE"], _show(rs["duo"])
    for name in ("roam", "host", "duo"):
        acks = [a.split("[NetSync] ", 1)[-1] for a in rs[name]["acks"]]
        assert any(a.startswith("harness: worldwalk walk off") for a in acks) and any(a.startswith("harness: worldwalk fp off")
                                                                                       for a in acks), (name, acks)
    # the control: the same duo WITHOUT the re-key -- an s167 pair speaks caps 0x0003, so round A's D-TRAILER (the peer's caps 1) reds
    assert "S166-D-TRAILER" in rs["bare"]["red"], _show(rs["bare"])
