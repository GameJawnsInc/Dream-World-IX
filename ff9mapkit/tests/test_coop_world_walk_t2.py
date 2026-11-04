"""[ff9mapkit netsync s166] WORLD WALK, ROUND A -- THE T2 AND DUO ROWS (studies/test-harness/scenarios/coop_world_walk_t2.py), offline.

  * THE TABLES: every leg's catalog, OLD / LEVER predictions and stand-in FAULT_REDS name rows the leg carries and faults the stand-in
    has; the duo's likewise.
  * THE INSTRUMENT: roam_instrument_tape is a v15 host through coop_peer's REAL codec (wire 15, fmt-1 trailers, the load's byte-identical
    re-sends with a frozen seq, the walker HEADING as the rotation, the seam crossed), its facts hold and both windows are found -- and
    every fact can fail (a v14 restamp, a riding host, no seam, a short tile stand, no 300).
  * THE PURE JUDGES go red on each wrong shape: the oracle by seq, the live header, A-WIRE, T2-A old, roam / freeze, T2-H, the duo.
  * EVERY LEG SMOKED AGAINST THE STAND-IN through the real Session and stub peers (replay-host / serve-guest / the duo's link) that drive
    the stand-in's transport seams (FakeGame.wire_frame, follow_session, host_at, host_world_pose) -- on the stand-in's OWN clock where
    a row judges an engine age: NEW green, OLD exactly the leg's OLD_PREDICTED (the A0b build: wire 14), each lever exactly its
    LEVER_PREDICTED with its shape measured, each stand-in fault exactly its FAULT_REDS rows, a lever the engine ignores reds the CAL row
    alone.

Every scenario-touching test runs in a CHILD process: a scenario puts its own dir on sys.path and reads its COOP_* knobs at import.
"""
import importlib.util
import json
import os
import pathlib
import re
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
    spec = importlib.util.spec_from_file_location("coop_world_walk_t2_pure", str(SCENARIOS / "coop_world_walk_t2.py"))
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
def test_the_tables_name_rows_the_legs_carry_and_faults_the_stand_in_has(t2):
    faults = set(FG.WORLD_WALK_A_FAULTS) | set(FG.WORLD_WALK_FAULTS)
    cats = {leg: t2.leg_catalog(leg, True) for leg in ("wire", "roam", "freeze", "host")}
    cats["old"] = dict(t2.OLD_CHECKS)
    cats["duo"] = dict(t2.DUO_CHECKS)
    for leg, table in t2.FAULT_REDS.items():
        for fault, rows in table.items():
            assert fault in faults, (leg, fault)
            assert rows and set(rows) <= set(cats[leg]), (leg, fault, rows)
    for leg, (old, lev) in {"wire": (t2.WIRE_OLD_PREDICTED, t2.WIRE_LEVER_PREDICTED),
                            "roam": (t2.ROAM_OLD_PREDICTED, t2.ROAM_LEVER_PREDICTED),
                            "freeze": (t2.FREEZE_OLD_PREDICTED, t2.FREEZE_LEVER_PREDICTED),
                            "host": (t2.HOST_OLD_PREDICTED, t2.HOST_LEVER_PREDICTED)}.items():
        assert set(old) <= set(cats[leg]), leg
        assert set(lev) == set(t2.LEVERS[leg]), leg
        for lever, rows in lev.items():
            assert rows and set(rows) <= set(cats[leg]), (leg, lever)
            assert lever in t2.LEVER_OPS or lever == "wire15"
    assert set(t2.DUO_LEVER_PREDICTED) == set(t2.DUO_LEVERS)
    assert set(t2.DUO_OLD_PREDICTED) == set(t2.DUO_ORDER) - {"S166-D-SHARED"}
    assert all(set(r) <= set(t2.DUO_ORDER) for r in t2.DUO_LEVER_PREDICTED.values())
    assert all(f in faults for f in t2.LEVER_IGNORED.values())
    assert set(t2.LEVERS) == set(t2.LEGS)
    # the gate row is never part of a calibration (its verdict is the tape's, not the engine's)
    assert "S166-RM-GATE" not in t2.ROAM_OLD_PREDICTED and all("S166-RM-GATE" not in r for r in t2.ROAM_LEVER_PREDICTED.values())
    assert t2.lever_of("roam", None) == "ghost" and t2.lever_of("roam", "nope") is None and t2.lever_of("duo", "dot") == "dot"


# ================================================================================================ the instrument
def _instrument(t2):
    return t2.roam_instrument_tape(CP)


def test_the_instrument_is_a_v15_host_through_the_real_codec_and_its_facts_hold(t2, tmp_path):
    recs = _instrument(t2)
    assert CP.tape_wire(recs) == 15
    rows = t2.trailer_rows(recs, CP)
    assert rows and all(r["len"] == CP.POS_V15_LEN and r["has"] for r in rows)       # 94 B, fmt 1, on every type-0 frame
    world = [r for r in rows if r["valid"]]
    assert world and {r["world"] for r in world} == {9011} and {r["flags"] for r in world} == {0} and {r["mode"] for r in world} == {0}
    # the host's own sync load: ONE place-3 frame re-sent byte-identical (the seq and the ms frozen)
    loads = [r for r in recs if r.dir == 0 and CP.parse_frame(r.payload)[0] == CP.TYPE_POS
             and CP.parse_pos_payload(CP.parse_frame(r.payload)[1])["trailer"]["place"] == CP.PLACE_WORLD_LOADING]
    assert len(loads) > 30 and len({r.payload for r in loads}) == 1
    # the rotation is the walker's HEADING (travel + 180), never the travel heading
    walk = [(a, b) for a, b in zip(world, world[1:]) if 0.5 < t2.torus(a["x"], a["z"], b["x"], b["z"]) < 64.0]
    a, b = walk[len(walk) // 2]
    dx, dz = t2._tdx(b["x"] - a["x"], 1536.0), t2._tdx(b["z"] - a["z"], 1280.0)
    assert t2._yaw_diff(b["yaw"], BW.ww_walker_yaw(dx, dz)) < 0.5
    assert t2._yaw_diff(b["yaw"], (BW.ww_walker_yaw(dx, dz) + 180.0) % 360.0) > 179.0
    f = t2.roam_tape_facts(recs, CP, header=t2.INSTRUMENT_HEADER)
    ok, bad = t2.facts_ok(f)
    assert ok, bad
    w = f["windows"]
    assert f["instrument"] and w["bh23"] is not None and w["bh6"] is not None
    assert w["bh6"] >= w["bh23"] + t2.BH23_S + t2.RECOVER_S + 1.0 or w["bh6"] + t2.BH6_S + t2.RECOVER_S + 1.0 <= w["bh23"]
    assert w["bh23"] >= t2.seam_crossings(rows)[0] + t2.SEAM_ROOM_S
    # written through coop_peer's own TapeWriter: the header records the wire from the frames and names the instrument
    p = t2.write_instrument(tmp_path / "i.f9tape", CP)
    header, back, torn = CP.read_tape(p)
    assert header["wire"] == 15 and header["instrument"] == "roam" and header["synthetic"] is True and not torn
    assert len(back) == len(recs)


def test_every_roam_fact_can_fail(t2):
    recs = _instrument(t2)

    def facts(r, plan=None):
        return t2.roam_tape_facts(r if plan is None else t2.roam_instrument_tape(CP, plan=plan), CP)
    v14 = [CP.Record(r.t, r.dir, CP.restamp(r.payload, 14)) for r in recs]
    assert not facts(v14)["rm3"]["ok"] and "wire 14" in facts(v14)["rm3"]["why"]
    no_seam = tuple(x for x in t2.ROAM_PLAN if not (x[0] == "walk" and x[1] == 180.0))
    assert not facts(None, no_seam)["rm5"]["ok"]
    short = tuple(("stand", 5.0) if x == ("stand", 20.0) else x for x in t2.ROAM_PLAN)
    assert not facts(None, short)["rm6"]["ok"]
    no300 = tuple(x for x in t2.ROAM_PLAN if x[0] != "enter")[:-1]
    assert not facts(None, no300)["rm7"]["ok"]
    stand_only = tuple(x for x in t2.ROAM_PLAN if x[0] != "walk")
    f = facts(None, stand_only)
    assert not f["rm4"]["ok"] and f["windows"]["bh23"] is None              # nothing moves: no BH23 window either
    riding = []
    for r in recs:
        got = CP.parse_frame(r.payload)
        if got and got[0] == CP.TYPE_POS and len(got[1]) == CP.POS_V15_LEN and got[1][CP.TRAILER_AT + 9] == CP.PLACE_WORLD:
            p = bytearray(got[1])
            p[81] = 1                                                        # [190] riding
            riding.append(CP.Record(r.t, r.dir, CP.build_frame(CP.TYPE_POS, bytes(p), wire=15)))
        else:
            riding.append(r)
    assert not facts(riding)["rm3"]["ok"]


def test_the_plan_poses_face_the_walker_heading_and_wrap_the_seam(t2):
    poses = t2.plan_poses()
    walks = [x for x in t2.ROAM_PLAN if x[0] == "walk"]
    heads = {round(BW.ww_walker_yaw(__import__("math").cos(__import__("math").radians(b)),
                                    __import__("math").sin(__import__("math").radians(b))), 3) for _w, b, _d in walks}
    assert heads <= {round(p[4], 3) for p in poses}
    xs = [p[2] for p in poses if p[1] == "world"]
    assert all(0.0 <= x < 1536.0 for x in xs) and any(x > 1400.0 for x in xs) and any(x < 100.0 for x in xs)
    assert poses[-1][1] == "field" and any(p[1] == "enter" for p in poses)


# ================================================================================================ the pure judges
class S:
    """A sample: frame, ui, world, the raw document."""

    def __init__(self, frame, *, ui="WorldHUD", world=9011, field=0, x=68.0, z=-444.0, br=True, lane=None, ghost=None, line=None,
                 dot=None, wp=None, hg=None, session=None, freeze=True, wire=15):
        self.frame, self.ui_state, self.world_id, self.field_id = frame, ui, world, field
        self.world_x, self.world_z, self.dialogue_wire = x, z, wire
        ns = {"world": {"freeze": {"on": freeze}}, "session": dict(session or {})}
        for k, v in (("lane", lane), ("ghost", ghost), ("line", line), ("dot", dot)):
            if v is not None:
                ns["world"][k] = v
        if wp is not None:
            ns["wire_peer"] = wp
        if hg is not None:
            ns["host"] = {"world": {"guest": hg}}
        self.raw = {"world": {"x": x, "z": z, "block_ready": br, "ticks": frame}, "netsync": ns}


def _smap(t2):
    return t2.seq_map(t2.trailer_rows(_instrument(t2), CP))


def _on_oracle(t2, smap, seq, *, off=0.0, yaw_flip=False, shown=True):
    r = smap[seq]
    yaw = (r["yaw"] + (180.0 if yaw_flip else 0.0)) % 360.0
    return {"want": shown, "shown": shown, "why_not": None if shown else "lever", "placed": True, "x": r["x"] + off, "z": r["z"],
            "tx": r["x"], "tz": r["z"], "yaw": yaw}


def test_the_oracle_judge_goes_red_on_each_wrong_shape(t2):
    smap = _smap(t2)
    rows = sorted((r for r in smap.values() if r["valid"]), key=lambda r: r["t"])
    seqs = [r["seq"] for r in rows if rows[0]["t"] + 10.0 <= r["t"] <= rows[0]["t"] + 25.0][::3]

    def samples(**kw):
        return [S(i, lane={"rx": {"seq": q}}, ghost=_on_oracle(t2, smap, q, **kw)) for i, q in enumerate(seqs)]
    ok, why = t2.judge_ghost_on_oracle(samples(), smap)
    assert ok, why
    assert "straight-leg facing" in why and int(why.split(" straight-leg")[0].split("; ")[-1]) > 5
    assert not t2.judge_ghost_on_oracle(samples(off=12.0), smap)[0]                     # eased off the path
    assert not t2.judge_ghost_on_oracle(samples(yaw_flip=True), smap)[0]                 # facing the travel (180 off)
    assert not t2.judge_ghost_on_oracle(samples(shown=False), smap)[0]                   # hidden
    bad_target = samples()
    bad_target[3].raw["netsync"]["world"]["ghost"]["tx"] += 1.0
    assert not t2.judge_ghost_on_oracle(bad_target, smap)[0]                             # the target is not the tape's
    lagged = samples()                                                                   # a target one seq behind the cache: the publish
    for s_, q in zip(lagged, seqs):                                                      # between Update and LateUpdate (allowed)
        prev = smap[t2.seq_back(q, 1)]
        s_.raw["netsync"]["world"]["ghost"].update(tx=prev["x"], tz=prev["z"])
    assert t2.judge_ghost_on_oracle(lagged, smap)[0]
    stale = samples()                                                                    # ...but never a target from 10 seqs back
    for s_, q in zip(stale, seqs):
        old_ = smap[t2.seq_back(q, 10)]
        s_.raw["netsync"]["world"]["ghost"].update(tx=old_["x"], tz=old_["z"])
    assert not t2.judge_ghost_on_oracle(stale, smap)[0]
    assert not t2.judge_ghost_on_oracle(samples()[:5], smap)[0]                          # too few
    foreign = [S(i, lane={"rx": {"seq": 60000 + i}}, ghost=_on_oracle(t2, smap, seqs[0])) for i in range(30)]
    assert not t2.judge_ghost_on_oracle(foreign, smap)[0]                                # seqs not on the tape
    assert t2.judge_ghost_on_oracle([S(i) for i in range(30)], smap)[1].startswith("absent")
    # [W2 critic] a window with no straight leg judged no facing: red (the facing clause must run)
    still = {q: dict(smap[seqs[0]], seq=q) for q in range(100, 140)}
    ss = [S(i, lane={"rx": {"seq": q}}, ghost=_on_oracle(t2, still, q)) for i, q in enumerate(range(115, 140))]
    ok, why = t2.judge_ghost_on_oracle(ss, still)
    assert not ok and "0 straight-leg facing(s) judged" in why, why
    # the torus: a path across the seam is near both sides
    assert t2.path_distance(1535.0, -500.0, [(1530.0, -500.0), (6.0, -500.0)]) < 0.01


def test_the_live_header_and_the_wire_judges(t2):
    ok_line = "guest header: wire 15 -- the replay sends wire 15 (restamped from the tape's 14 to the guest's own)"
    asked = "guest header: wire 15 -- the replay sends wire 14 (as recorded, --wire tape -- the guest speaks 15: it DROPS every frame and never pairs)"
    assert t2.judge_live_header(ok_line, 15)[0]
    assert not t2.judge_live_header(asked, 15)[0] and t2.judge_live_header(asked, 15, want_send=14)[0]
    assert not t2.judge_live_header(ok_line, 14)[0]                                     # the probe disagrees with the header
    assert not t2.judge_live_header(None, 15)[0]
    assert t2.judge_live_header("host header: wire 15 -- this fake guest sends wire 15 (the host's own)", 15, side="host")[0]
    # NOPAIR
    rest = dict(ui="FieldHUD", field=6603, lane={"rx": {"samples": 0}})
    win = [S(i, **rest) for i in range(10)]
    assert t2.judge_wire_nopair(win, [])[0]
    assert not t2.judge_wire_nopair(win, ["01.11.2026 10:00:00 |I| [NetSync] paired on the host's field (6603) -- reloading it once so "
                                          "the state mirror arms"])[0]
    assert not t2.judge_wire_nopair(win + [S(11, ui="FieldHUD", field=6603, lane={"rx": {"samples": 3}})], [])[0]
    assert not t2.judge_wire_nopair(win + [S(11, ui="FieldHUD", field=6603, lane={"rx": {"samples": 0}},
                                              session={"mirroring": True})], [])[0]
    assert not t2.judge_wire_nopair([S(i, ui="FieldHUD", field=6603) for i in range(5)], [])[0]           # no lane: absent
    # [W2 critic] a cache fed by a CAPLESS host reads samples 0 (they count seq moves) -- the kind / arrival clock must catch it
    assert not t2.judge_wire_nopair(win + [S(11, ui="FieldHUD", field=6603, lane={"rx": {"samples": 0, "kind": "absent"}})], [])[0]
    assert not t2.judge_wire_nopair(win + [S(11, ui="FieldHUD", field=6603, lane={"rx": {"samples": 0}, "arrival_age_ms": 40})], [])[0]
    # REJECT
    words = BW.WORDS_WIRE_MISMATCH

    def wsample(i, rej, mismatch=True, drawn=True, last=14, lines=1):
        return S(i, ui="FieldHUD", field=6603, wp={"rejected": rej, "last_version": last, "lines": lines, "mismatch": mismatch,
                                                    "words": words if mismatch else None},
                 line={"asked": "mismatch", "text": BW.WORDS_WW_WIRE_MISMATCH, "drawn": drawn})
    base = S(0, ui="FieldHUD", field=6603, wp={"rejected": 0, "last_version": -1, "lines": 0, "mismatch": False, "words": None})
    good = [wsample(i, 10 * i) for i in range(1, 8)]
    log = ["x |I| " + BW.log_peer_wire(14, 15)]
    assert t2.judge_wire_reject(base, good, log)[0]
    assert not t2.judge_wire_reject(base, good, log * 2)[0]                                # two lines
    assert not t2.judge_wire_reject(base, [wsample(i, 1) for i in range(1, 8)], log)[0]    # never rose
    assert not t2.judge_wire_reject(base, good[:-1] + [wsample(8, 80, drawn=False)], log)[0]
    assert not t2.judge_wire_reject(base, good[:3] + [wsample(9, 90, mismatch=False)] + good[3:], log)[0]
    assert not t2.judge_wire_reject(base, good[:3] + [wsample(9, 5)] + good[3:], log)[0]   # it fell
    assert t2.judge_wire_reject(base, [S(1)], log)[1].startswith("absent")
    # CLEAR
    paired = ["01.11.2026 10:00:01 |I| [NetSync] paired on the host's field (6603) -- reloading it once so the state mirror arms"]
    up = [S(i, wp={"mismatch": True}, line={"asked": "mismatch"}) for i in range(3)]
    gone = [S(10 + i, wp={"mismatch": False}, line={"asked": None}) for i in range(5)]
    assert t2.judge_wire_clear(up + gone, paired, len(up))[0]
    assert not t2.judge_wire_clear(up + up + gone, paired, len(up))[0]                     # latched past the window
    assert not t2.judge_wire_clear(up + gone, [], len(up))[0]                              # never paired
    assert not t2.judge_wire_clear([S(1)], paired, 0)[0]
    # the lever's shape
    cap = [S(i, wp={"rejected": 0}, lane={"rx": {"kind": "absent"}}) for i in range(4)]
    nr = [S(9, ghost={"why_not": "no_record"})]
    assert t2.wire_lever_measured(cap, paired, nr)[0]
    assert not t2.wire_lever_measured(cap, [], nr)[0]
    assert not t2.wire_lever_measured(cap, paired, [S(9, ghost={"why_not": "peer_caps"})])[0]


def test_the_old_judges(t2):
    assert t2.judge_old_wire("guest header: wire 15 -- the replay sends wire 15 (restamped from the tape's 14 to the guest's own)")[0]
    assert t2.judge_old_wire("guest header: wire 14 -- the replay sends wire 14 (as recorded)")[0]
    assert not t2.judge_old_wire("guest header: wire 15 -- the replay sends wire 15 (as recorded)")[0]
    assert not t2.judge_old_wire(None)[0]
    calm = [S(i, ui="FieldHUD", field=6603, wp={"rejected": 0}, lane={"rx": {"kind": "absent"}, "caps": {"peer": 0}},
              ghost={"shown": False, "why_not": "not_live"}, line={"asked": None}) for i in range(5)]
    world = [S(10 + i, wp={"rejected": 0}, lane={"rx": {"kind": "absent"}, "caps": {"peer": 0}},
               ghost={"shown": False, "why_not": "no_record"}, line={"asked": None}) for i in range(5)]
    assert t2.judge_old_dormant(calm + world, [])[0]
    gap = ["x |I| [NetSync] client " + BW.ww_lane_line_text(BW.WW_LINE_GAP_START, 1000)]
    assert not t2.judge_old_dormant(calm + world, gap)[0]
    assert not t2.judge_old_dormant(calm + world[:-1] + [S(20, ghost={"shown": True}, lane={"rx": {"kind": "fmt1"}})], [])[0]
    assert not t2.judge_old_dormant(calm + world[:-1] + [S(20, wp={"rejected": 4}, lane={"rx": {"kind": "absent"}},
                                                           ghost={"why_not": "no_record"})], [])[0]
    ok, why = t2.judge_old_dormant([S(i, ui="FieldHUD", field=6603) for i in range(3)], [])
    assert ok and "by construction" in why
    # [W2 critic] a cache NEVER fed (kind null, caps -1: the sentinels) proves nothing dormant -- the instrument reds it
    unfed = [S(i, ui="FieldHUD", field=6603, wp={"rejected": 0}, lane={"rx": {"kind": None}, "caps": {"peer": -1}},
               ghost={"shown": False, "why_not": "not_live"}, line={"asked": None}) for i in range(5)]
    ok, why = t2.judge_old_dormant(unfed, [])
    assert not ok and "NO (never read" in why


def _lane_log(role, line, n):
    return f"01.11.2026 10:00:00 |I| [NetSync] {role} " + BW.ww_lane_line_text(line, n)


def test_the_blackhole_and_freeze_judges(t2):
    smap = _smap(t2)
    rows = sorted((r for r in smap.values() if r["valid"]), key=lambda r: r["t"])
    seqs = [r["seq"] for r in rows if rows[0]["t"] + 10.0 <= r["t"] <= rows[0]["t"] + 14.0]
    q0 = seqs[0]
    base = S(0, ghost={"hides": 0, "snaps": 1})

    def g(q, **kw):
        d = _on_oracle(t2, smap, q)
        d.update({"hides": 0, "snaps": 1, "stall": "move", **kw})
        return d
    win = [S(i, lane={"rx": {"seq": q0}}, ghost=g(q0, stall="stand" if i > 3 else "move")) for i in range(1, 12)]
    rec = [S(20 + i, lane={"rx": {"seq": q}}, ghost=g(q)) for i, q in enumerate(seqs[5:20])]
    lines = [_lane_log("client", BW.WW_LINE_GAP_START, 1000), _lane_log("client", BW.WW_LINE_GAP_END, 2330)]
    assert t2.judge_bh23(base, win, rec, lines, smap)[0]
    assert not t2.judge_bh23(base, win, rec, lines[:1], smap)[0]                          # no end
    assert not t2.judge_bh23(base, win, rec, [lines[0], _lane_log("client", BW.WW_LINE_GAP_END, 3500)], smap)[0]
    assert not t2.judge_bh23(base, win, rec, lines + [_lane_log("client", BW.WW_LINE_HANG_START, 1000)], smap)[0]
    assert not t2.judge_bh23(base, [S(1, lane={"rx": {"seq": q0}}, ghost=g(q0))] * 5, rec, lines, smap)[0]   # never stood
    snapped = [S(30, lane={"rx": {"seq": seqs[25]}}, ghost=g(seqs[25], snaps=2))]
    assert not t2.judge_bh23(base, win, rec + snapped, lines, smap)[0]                    # a snap
    # BH6
    win6 = [S(i, lane={"seq_age_ms": 500 * i}, ghost={"shown": i < 10, "want": i < 10, "why_not": None if i < 10 else "stale",
                                                      "snaps": 1}) for i in range(1, 13)]
    rec6 = [S(40, ghost={"shown": True, "snaps": 2})]
    assert t2.judge_bh6(base, win6, rec6)[0]
    early = [S(1, lane={"seq_age_ms": 1000}, ghost={"shown": False, "why_not": "stale", "want": False, "snaps": 1})]
    assert not t2.judge_bh6(base, early + win6, rec6)[0]
    assert not t2.judge_bh6(base, win6, [S(40, ghost={"shown": True, "snaps": 1})])[0]   # re-shown without a snap
    # the freeze
    fz = {"tx": 100.0, "tz": -500.0, "x": 100.0, "z": -500.0, "placed": True, "stand": "ANH_X_STAND"}

    def fs(i, age, **kw):
        d = dict(fz, seq_age_ms=age, shown=True, want=True, why_not=None, stall="stand" if age >= 300 else "move",
                 anim="stand" if age >= 300 else "follow", clip="ANH_X_STAND" if age >= 300 else "ANH_X_RUN", snaps=1)
        d.update(kw)
        return S(i, lane={"seq_age_ms": age}, ghost=d, line={"asked": None})
    w23 = [fs(i, 100 * i) for i in range(1, 23)]
    l23 = [_lane_log("client", BW.WW_LINE_HANG_START, 1000), _lane_log("client", BW.WW_LINE_HANG_END, 2333)]
    assert t2.judge_t2_freeze(base, w23, [], l23, 2300, hide=False)[0]
    assert not t2.judge_t2_freeze(base, w23, [], [l23[0].replace("is not updating", "is loading")] + l23[1:], 2300, hide=False)[0]
    assert not t2.judge_t2_freeze(base, w23, [], l23 + [_lane_log("client", BW.WW_LINE_GAP_START, 1000)], 2300, hide=False)[0]
    assert not t2.judge_t2_freeze(base, [fs(i, 100 * i, stall="move", anim="follow") for i in range(1, 23)], [], l23, 2300,
                                  hide=False)[0]                                           # never stood (the hold on rs.Valid)
    assert not t2.judge_t2_freeze(base, w23[:-1] + [fs(30, 2300, x=103.0)], [], l23, 2300, hide=False)[0]   # drifted off the hold
    lost = {"asked": "lost", "text": BW.WORDS_WW_LOST_CONTACT, "drawn": True}
    w6 = [fs(i, 250 * i) for i in range(1, 20)] + [S(30 + i, lane={"seq_age_ms": 5050 + 50 * i},
                                                     ghost=dict(fz, seq_age_ms=5050 + 50 * i, shown=False, want=False,
                                                                why_not="stale", stall="hide", snaps=1), line=lost)
                                                   for i in range(5)]
    r6 = [S(60, ghost={"shown": True, "snaps": 2})]
    l6 = [_lane_log("client", BW.WW_LINE_HANG_START, 1000), "x |I| " + BW.log_ww_line_lost(5000, 30),
          _lane_log("client", BW.WW_LINE_HANG_END, 6033), "x |I| " + BW.log_ww_line_lost_over(1000, None)]
    assert t2.judge_t2_freeze(base, w6, r6, l6, 6000, hide=True)[0]
    nodraw = [S(s.frame, lane={"seq_age_ms": 5100}, ghost=_g, line=dict(lost, drawn=False))
              for s, _g in ((x, x.raw["netsync"]["world"]["ghost"]) for x in w6[-5:])]
    assert not t2.judge_t2_freeze(base, w6[:-5] + nodraw, r6, l6, 6000, hide=True)[0]   # the line not drawn
    assert not t2.judge_t2_freeze(base, w6, r6, [x for x in l6 if "world line" not in x], 6000, hide=True)[0]
    assert not t2.judge_t2_freeze(base, w6, r6, l6, 2300, hide=True)[0]                 # the end names the wrong span
    # the levers' shapes
    assert t2.lanegap_measured(S(0, lane={"gaps": 0}), S(1, lane={"gaps": 1}), [])
    assert not t2.lanegap_measured(S(0, lane={"gaps": 0}), S(1, lane={"gaps": 1}), lines)
    assert t2.ghost_off_measured([S(1, ghost={"want": True, "shown": False})])
    assert not t2.ghost_off_measured([S(1, ghost={"want": True, "shown": False}), S(2, ghost={"shown": True})])


def test_the_host_judges(t2):
    hg = lambda p, line=None, flags=1, state=0: {"place": p, "state": state, "flags": flags, "line": line, "edges": 0}   # noqa: E731
    W = {"following": BW.WORDS_WW_HOST_FOLLOWING, "loading": BW.WORDS_WW_HOST_LOADING, "scene": BW.WORDS_WW_HOST_SCENE}
    seq = [("following", 2), ("loading", 3), (None, 4), ("scene", 4), (None, 4)]
    samples = [S(i, hg=hg(p, n), line={"asked": n, "text": W.get(n), "drawn": n is not None}) for i, (n, p) in enumerate(seq)]
    logs = [f'x |I| {BW.LOG_WW_HOST_WORLD}the partner is {n} ("{W[n]}") -- the guest\'s place x' for n in W]
    assert t2.judge_th_instrument(samples)[0]
    assert t2.judge_th_lines(samples, logs)[0]
    assert not t2.judge_th_lines(samples, logs[:2])[0]
    assert not t2.judge_th_lines(list(reversed(samples)), logs)[0]                        # out of order
    assert not t2.judge_th_lines([S(1, hg=hg(2, "following"), line={"asked": "following", "text": "x", "drawn": True})], logs)[0]
    assert not t2.judge_th_instrument([s for s in samples if s.raw["netsync"]["host"]["world"]["guest"]["place"] != 3])[0]
    assert t2.judge_th_lines([S(1)], logs)[1].startswith("absent")
    # GAP
    base = S(0, ghost={"hides": 0})
    gw = [S(i, hg=hg(4), ghost={"shown": True, "hides": 0}) for i in range(1, 6)]
    gl = [_lane_log("host", BW.WW_LINE_GAP_START, 1000), _lane_log("host", BW.WW_LINE_GAP_END, 1540)]
    assert t2.judge_th_gap(base, gw, gw, gl)[0]
    assert not t2.judge_th_gap(base, gw, gw, [x.replace("] host ", "] client ") for x in gl])[0]   # not the host's lane
    assert not t2.judge_th_gap(base, gw + [S(9, hg=hg(4, "lost"), ghost={"shown": True, "hides": 0})], gw, gl)[0]
    assert not t2.judge_th_gap(base, gw + [S(9, hg=hg(4), ghost={"shown": False, "hides": 1})], gw, gl)[0]
    # RELEASED / NOFOLLOW (their taps)
    smap = _smap(t2)
    rows = sorted((r for r in smap.values() if r["valid"]), key=lambda r: r["t"])
    tap = [dict(r, state=0x86, flags=1, place=4) for r in rows[:200]]
    tmap = t2.seq_map(tap)
    rel = [S(0, hg=hg(2, "following"), line={"asked": "following", "text": W["following"], "drawn": True})] + \
          [S(1 + i, hg=hg(4), lane={"rx": {"seq": r["seq"]}}, ghost=_on_oracle(t2, tmap, r["seq"])) for i, r in enumerate(rows[20:120:4])]
    flog = [logs[0]]
    assert t2.judge_th_released(rel, flog, tap, tmap)[0]
    assert not t2.judge_th_released(rel, flog, [dict(r, state=0x85) for r in tap], tmap)[0]   # not a released guest's record
    assert not t2.judge_th_released(rel[1:], flog, tap, tmap)[0]                              # no line
    ctap = [dict(r, flags=0) for r in tap]
    quiet = [S(i, hg=hg(4, None, flags=0), line={"asked": None}, ghost={"shown": False, "why_not": "role"}) for i in range(6)]
    assert t2.judge_th_nofollow(quiet, [], ctap)[0]
    assert not t2.judge_th_nofollow(quiet, [], tap)[0]                                        # the tap follows
    assert not t2.judge_th_nofollow(quiet + [S(9, hg=hg(4, "lost", flags=0), line={"asked": "lost"},
                                               ghost={"shown": False, "why_not": "role"})], [], ctap)[0]
    assert not t2.judge_th_nofollow(quiet + [S(9, hg=hg(4, flags=0), line={"asked": None}, ghost={"shown": True})], [], ctap)[0]
    assert not t2.judge_th_nofollow(quiet, logs[:1], ctap)[0]
    assert t2.hostlines_measured([S(0, hg=hg(2)), S(1, hg=hg(3)), S(2, hg=hg(4, state=0x40))], [])
    assert not t2.hostlines_measured([S(0, hg=hg(2)), S(1, hg=hg(3)), S(2, hg=hg(4, "scene", state=0x40))], [])


def test_the_duo_judges(t2):
    import datetime as dt
    host = [S(i, lane={"tx": {"seq": 100 + 2 * i, "x": 100.0 + 4.0 * i, "z": -500.0, "mode": 0, "kind": "fmt1"},
                       "rx": {"kind": "fmt1"}, "caps": {"peer": 1}}) for i in range(12)]
    assert t2.tx_pose_at(host, 104) == (108.0, -500.0)
    assert t2.tx_pose_at(host, 105) == pytest.approx((110.0, -500.0))
    assert t2.tx_pose_at(host, 200) is None

    def gs(i, seq, off=0.0, shown=True):
        x = 100.0 + 2.0 * (seq - 100)
        return S(i, x=500.0, z=-500.0, lane={"rx": {"seq": seq, "kind": "fmt1"}, "tx": {"kind": "fmt1"}, "caps": {"peer": 1}},
                 ghost={"placed": True, "shown": shown, "tx": x + off, "tz": -500.0, "x": x + off, "z": -500.0})
    guest = [gs(i, 100 + 2 * i) for i in range(10)]
    ok, why = t2.judge_d_g1(guest, host, (500.0, -500.0), (500.0, -500.0))
    assert ok, why
    assert not t2.judge_d_g1([gs(i, 100 + 2 * i, off=9.0) for i in range(10)], host, (500.0, -500.0), (500.0, -500.0))[0]
    assert not t2.judge_d_g1(guest, host, (500.0, -500.0), (520.0, -500.0))[0]            # the frozen guest moved
    assert not t2.judge_d_g1(guest, host[:1], (500.0, -500.0), (500.0, -500.0))[0]        # unmatched / the host never moved
    assert t2.judge_d_trailer(host, guest)[0]
    assert not t2.judge_d_trailer(host, [S(1, lane={"rx": {"kind": "absent"}, "tx": {"kind": "fmt1"}, "caps": {"peer": 0}})])[0]
    hs = [S(i, ghost={"shown": True, "x": 500.5, "z": -500.0}) for i in range(10)]
    assert t2.judge_d_g2(hs, (500.0, -500.0), "1.0 s")[0]
    assert not t2.judge_d_g2(hs, (510.0, -500.0), "1.0 s")[0]
    # DOTRIDE
    ride = [S(i, lane={"tx": {"seq": 100 + 2 * i, "x": 100.0 + 4.0 * i, "z": -500.0, "mode": 1}}) for i in range(12)]
    dots = [S(i, lane={"rx": {"seq": 100 + 2 * i}}, dot={"src": "trailer", "src_x": 100.0 + 4.0 * i, "src_z": -500.0}) for i in range(10)]
    assert t2.judge_d_dotride(dots, ride)[0]
    assert not t2.judge_d_dotride([S(s.frame, lane=s.raw["netsync"]["world"]["lane"], dot=dict(s.raw["netsync"]["world"]["dot"],
                                                                                                 src="section0")) for s in dots], ride)[0]
    assert not t2.judge_d_dotride(dots, host)[0]                                           # the host never rode
    assert t2.dot_lever_measured([S(1, dot={"src": "section0"})]) and not t2.dot_lever_measured([S(1, dot={"src": "trailer"})])
    # BATTLE: the contention split
    t0 = dt.datetime(2026, 11, 3, 10, 0, 0)
    hang = f"03.11.2026 10:00:05 |I| [NetSync] guest-x client " + BW.ww_lane_line_text(BW.WW_LINE_HANG_START, 1000)
    hang = hang.replace("guest-x client", "client")
    load = f"03.11.2026 10:00:05 |I| [NetSync] client " + BW.ww_lane_line_text(BW.WW_LINE_LOAD_START, 1000)
    bh, ah = S(0, ghost={"mints": 1}), S(1, ghost={"mints": 2, "shown": True})
    bg, ag = S(0, ghost={"mints": 1}), S(1, ghost={"mints": 2, "shown": True})
    win = [(t0 + dt.timedelta(seconds=4), t0 + dt.timedelta(seconds=6))]
    assert t2.judge_d_battle(bh, ah, bg, ag, [], [hang, load], win, [])[0]                # inside the host's load: contention
    assert not t2.judge_d_battle(bh, ah, bg, ag, [], [hang], [], [])[0]                    # no window: a real hang
    assert not t2.judge_d_battle(bh, ah, bg, S(1, ghost={"mints": 1, "shown": True}), [], [], [], [])[0]   # never re-minted
    assert not t2.judge_d_battle(bh, ah, bg, S(1, ghost={"mints": 2, "shown": False}), [], [], [], [])[0]
    stamped = [(t0, S(1, ui="WorldHUD")), (t0 + dt.timedelta(seconds=0.1), S(2, ui="WorldHUD")),
               (t0 + dt.timedelta(seconds=2.0), S(3, ui="BattleHUD", world=0))]
    assert t2.load_windows(stamped) == [(stamped[1][0], stamped[2][0])]
    # REJOIN
    gl = [S(1, lane={"rx": {"place": 4}}, ghost={"shown": True}), S(2, lane={"rx": {"place": 2}}, ghost={"shown": False})]
    assert t2.judge_d_rejoin(gl, [S(3, ui="FieldHUD", ghost={"shown": False})], (True, "ok"))[0]
    sticky = gl + [S(3, lane={"rx": {"place": 2}}, ghost={"shown": True})]
    assert not t2.judge_d_rejoin(sticky, [], (True, "ok"))[0] and t2.sticky_measured(sticky)
    assert not t2.judge_d_rejoin(gl, [], (False, "never on 300"))[0]
    # [W2 critic] a ghost never drawn hides nothing: `ghost off` (want true, shown false throughout) is red by the instrument
    off = [S(1, lane={"rx": {"place": 4}}, ghost={"want": True, "shown": False}), S(2, lane={"rx": {"place": 2}}, ghost={"shown": False})]
    ok, why = t2.judge_d_rejoin(off, [], (True, "ok"))
    assert not ok and "before the host left on 0 sample(s)" in why and t2.ghost_off_measured(off)
    # LINES
    W = BW.WORDS_WW_HOST_FOLLOWING
    hl = [S(1, hg={"line": "following"}, line={"asked": "following", "text": W, "drawn": True}), S(2, hg={"line": None})]
    log = [f'x |I| {BW.LOG_WW_HOST_WORLD}the partner is following ("{W}") -- the guest\'s place transition, state 0x20']
    assert t2.judge_d_lines(hl, log, True)[0]
    assert not t2.judge_d_lines(hl, log, False)[0]
    assert not t2.judge_d_lines(hl[:1], log, True)[0]                                      # the line never ended
    assert not t2.judge_d_lines(hl, [], True)[0]


def test_the_window_picker_and_the_seam(t2):
    rows = t2.trailer_rows(_instrument(t2), CP)
    w = t2.plan_windows(rows)
    a = next(r for r in rows if r.get("valid") and r["t"] >= w["bh23"])
    b = next(r for r in rows if r.get("valid") and r["t"] >= w["bh23"] + t2.BH23_S)
    assert t2.GAP_WINDOW_U[0] <= t2.torus(a["x"], a["z"], b["x"], b["z"]) <= t2.GAP_WINDOW_U[1] + 1.0
    assert t2.pick_window(rows, 2.3, after=1e9) is None
    assert t2.pick_window([], 2.3, after=0.0) is None


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
                 D_WALK_FRAMES=90, D_WALK_S=1.0).items():
    setattr(t2, k, v)
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
    if run.get("stage") == "a0b":
        f.world_walk_pieces = FG.FAKE_WORLD_WALK_A0B_BUILD
    f.swap_qpc = None
    f.regions = {6603: [{"zone": cw.FS_DOOR, "world": cw.WORLD, "world_at": list(cw.FS_LANDING)}]}
    f.exit_frames = 900
    f.overworld = {"speed": 0.4, "turn": 2.8125, "cam": 0.0, "lag": 1}
    f.world_locations = {cw.ICE_CAVERN: (cw.ICE_TILE[0], cw.ICE_TILE[1], 2.0)}
    f.world_swirl_frames, f.world_exit_frames = 40, 40
    f.world_walk_faults = set(run.get("faults", ()))
    f.world_out_fade_frames = int(run.get("fade", 120))
    FAKES.append(f)
    return f

def session(t, f):
    g = Session(game_path=t, run_dir=t / "run", save_dir=t / "player-saves", pid_probe=lambda: [],
                launcher=lambda exe, f=f: f.start(), boot_timeout=15.0, verbose=False)
    g._booted_once = True
    return g

def rows_of(checks):
    rows = [(r["what"].split(":")[0], bool(r["ok"]), r["detail"][:1200]) for r in checks]
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
    """replay-host's stand-in: the tape's host frames onto the guest stand-in's seams AT THE WIRE replay-host would send
    (replay_send_wire over --wire): a frame of another wire is only BOOKED (FakeGame.wire_frame: the engine drops it -- no pairing,
    no host cache); --blackhole-at / --freeze-at as coop_peer's Replayer (a blackhole sends nothing, a freeze re-sends the last pos
    and state slots byte-identical, the seq frozen). Paced on the stand-in's VIRTUAL clock (the rows judge engine ages), or the wall
    at SPEED for coop_world_follow's own walk leg (its tape-time map is the wall's)."""
    clock = "virtual"
    def _now(self, f):
        return f.rt if self.clock == "virtual" else time.time() * SPEED
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
        mode = self._arg("--wire") or "auto"
        guest = f.netsync_wire_now()
        send, how = CP.replay_send_wire(mode, guest, CP.tape_wire(recs))
        self._say(CP.GUEST_WIRE_LINE.format(guest=guest, send=send, how=how))
        t0 = frames[0][0].t
        bhs = [(float(a), float(n)) for a, n in zip(self._arg("--blackhole-at", True), self._arg("--blackhole-for", True))]
        fzs = [(float(a), float(n)) for a, n in zip(self._arg("--freeze-at", True), self._arg("--freeze-for", True))]
        self._say(f"REPLAY start: tape {t0:.2f} s -> now; {len(frames)} host frame(s) up to tape {frames[-1][0].t:.2f} s")
        now0 = self._now(f)
        state = {"field": None, "flags": -1, "story": None, "first": True, "pos": None}
        said = set()
        def deliver(w, p, fresh=True, t=None):
            if send != guest:
                f.wire_frame(send, p)                               # booked and dropped: never a pairing, never the cache
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
            if state["field"] is None:
                return
            if state["first"]:
                f.follow_session(state["field"], flags=state["flags"], fresh=True, story=state["story"], pair_kick=True)
                state["first"] = False
            else:
                f.host_at(state["field"], flags=state["flags"], story=state["story"])
            if w == CP.TYPE_STATE and fresh:
                feed_pose(f, p)
        last, said = {}, set()
        edges = sorted([(a, "BLACKHOLE", n) for a, n in bhs] + [(a, "FREEZE", n) for a, n in fzs])
        def tape_now():
            return t0 + (self._now(f) - now0)
        def frozen(tt):
            return any(a <= tt < a + n for a, n in fzs)
        for r, w, p in frames:
            due = now0 + (r.t - t0)
            nxt = 0.0
            while self._now(f) < due and not self._halt.is_set():
                if frozen(tape_now()) and last and self._now(f) >= nxt:
                    nxt = self._now(f) + CP.TICK_S                  # the writer's re-send, byte-identical, every write tick
                    for lw, lp in list(last.items()):
                        deliver(lw, lp, fresh=False)
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
                continue                                            # dropped (a blackhole sends nothing; a freeze re-sends the slot)
            last[w] = p
            deliver(w, p, t=r.t)
        self._say(f"replay done (end of tape): sent {len(frames)}, dropped in blackholes 0, unsent (no guest attached) 0, max lag "
                  "0.000 s")
    pose = True

class StubServe(_Peer):
    """serve-guest's stand-in: its REAL model (coop_peer's own parser and _model_from over these args) on the host stand-in's VIRTUAL
    clock, every type-0 frame onto FakeGame.wire_frame, and the tap (what it sent, dir 1) written at the stop."""
    def _run(self):
        f = FAKES[-1]
        port = self._arg("--port")
        self._say(f"listening on ws://127.0.0.1:{port} -- the stub serve-guest")
        end = time.time() + 30.0
        while not self._halt.is_set() and time.time() < end and not (f.netsync.get("role") == "host" and f.netsync.get("enabled")):
            time.sleep(0.02)
        if self._halt.is_set():
            return
        args = CP.build_parser().parse_args(["serve-guest"] + [a for a in self.args if True])
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
            write_tape(pathlib.Path(tp), getattr(self, "sent_recs", []))
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
    if leg == "old":
        StubReplay.clock = "wall"
        tape = t / "tape-host6603-world-walk-s164.f9tape"
        write_tape(tape, pb.synthetic_world_walk_tape(CP, tile_s=65.0))
        os.environ["COOP_TAPE"] = str(tape)
    elif leg == "wire":
        StubReplay.clock = "virtual"
        tape = t / "tape-host6603-world-walk-s164.f9tape"
        write_tape(tape, pb.synthetic_world_walk_tape(CP, tile_s=65.0))
        os.environ["COOP_TAPE"] = str(tape)
    else:
        StubReplay.clock = "virtual"
        os.environ["COOP_TAPE_WORLD_ROAM"] = str(t2.write_instrument(t / "roam-INSTRUMENT.f9tape", CP))
    f = fake_for(t, run)
    cb.CALIBRATE = bool(run.get("cal"))
    t2.LEG, t2.LEVER_RAW = leg, run.get("lever")
    with session(t, f) as g:
        t2.run(g)
        out = rows_of(list(g.checks))
    return out

class Link(threading.Thread):
    """The duo's stub TRANSPORT: s165's seams (the host's place, section 7's flags, its story, its own world pose, its MAPJUMP intent)
    onto the guest, and round A's both ways -- each game's type-0 slot (world_tx_frame) onto the other's wire_frame, every tick."""
    def __init__(self, host, guest):
        super().__init__(daemon=True)
        self.h, self.g, self.halt = host, guest, threading.Event()
    def run(self):
        sent = None
        while not self.halt.is_set():
            h, g = self.h, self.g
            g.host_at(h.host_lane_field(), flags=h.host_dialog_flags(), story=bytes(h.story_bytes))
            w = h.world
            if h.ui_state == "WorldHUD" and w.get("x") is not None and w.get("id"):
                g.host_world_pose(float(w["x"]), float(w["z"]), idx=int(w["id"]) - 9000, mode=int(w.get("vehicle") or 0))
            it = h.host_field_intent
            if it is not None and it != sent:
                sent = it
                g.host_intent(it[1])
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
        self.rows.append((cid, bool(ok), str(detail)[:1200]))
        return bool(ok)
    def note(self, msg):
        self.notes.append(msg)

def duo(run):
    th, tg = root(), root()
    run = dict(run, fade=600)                                   # the guest's follow-out fade (1 s of wall): room for D-LINES' read
    fh, fgst = fake_for(th, run), fake_for(tg, run)
    fh.world_exit_frames = fgst.world_exit_frames = 240
    cb.CALIBRATE = bool(run.get("cal"))
    t2.LEVER_RAW = run.get("lever")
    gh, gg = session(th, fh), session(tg, fgst)
    with gh, gg:
        for g in (gh, gg):
            g.newgame(settle=0)
            g.warp(cw.FARSHORE)
        fh.netsync.update(enabled=True, role="host", instance=True)
        fh.story_bytes[pb.MARKER_BYTE] = pb.MARKER_VALUE
        fgst.follow_session(cw.FARSHORE, flags=BW.HF_ON_FIELD | BW.HF_CONTROL, fresh=True, story=bytes(fh.story_bytes), pair_kick=True)
        link = Link(fh, fgst)
        link.start()
        gg.wait_for(lambda s: (s.netsync or {}).get("session", {}).get("mirroring") is True, timeout=5, what="paired")
        d = StubDuo(gh, gg)
        try:
            t2.run_duo(d)
        finally:
            link.halt.set()
        return {"red": sorted(c for c, ok, _d in d.rows if not ok), "all": [c for c, _ok, _d in d.rows],
                "detail": {c: dd for c, _ok, dd in d.rows}}

kinds = {"t2": t2_run, "duo": duo}
results = {name: kinds[run["kind"]](run) for name, run in doc.get("runs", {}).items()}
print(json.dumps(results))
'''


def _child(payload, *, timeout: float = 900.0) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("COOP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    out = subprocess.run([sys.executable, "-X", "utf8", "-c", _CHILD, str(SCENARIOS), str(REPO / "tools"), str(REPO / "ff9mapkit")],
                         env=env, input=json.dumps(payload), capture_output=True, text=True, timeout=timeout)
    assert out.returncode == 0, out.stderr[-6000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _run(kind: str = "t2", **run) -> dict:
    return _child({"runs": {"r": dict(run, kind=kind)}})["r"]


def _show(r):
    return {c: r["detail"].get(c, "")[:700] for c in r["red"]}


_FINALS = {"T2-SAVE", "T2-INI", "T2H-INI"}


def _cal_ok(r, cal):
    return cal in r["all"] and cal not in r["red"]


# ---- A-WIRE
def test_s166t2_a_wire_new_is_green_on_the_s166_stand_in(t2):
    r = _run(leg="wire")
    assert r["red"] == [], _show(r)
    assert set(t2.WIRE_ROWS) <= set(r["all"])


def test_s166t2_a_wire_old_on_a0b_and_the_lever_calibrate_exactly():
    old = _run(leg="wire", stage="a0b", cal=True)
    assert set(old["red"]) == {"S166-WIRE-NOPAIR", "S166-WIRE-REJECT", "S166-WIRE-CLEAR"} and _cal_ok(old, "S166-WIRE-CAL"), _show(old)
    lev = _run(leg="wire", cal=True, lever="wire15")
    assert set(lev["red"]) == {"S166-WIRE-NOPAIR", "S166-WIRE-REJECT"} and _cal_ok(lev, "S166-WIRE-CAL"), _show(lev)


@pytest.mark.parametrize("fault", sorted({"wire_peer_dark", "wire_words_latched"}))
def test_s166t2_each_wire_fault_turns_exactly_its_rows_red(t2, fault):
    r = _run(leg="wire", faults=[fault])
    assert set(r["red"]) == set(t2.FAULT_REDS["wire"][fault]), _show(r)


# ---- T2-A old
def test_s166t2_t2_a_old_is_every_s165_row_and_round_a_dormant_and_a_fault_reds_dormant_alone(t2):
    r = _run(leg="old")
    assert r["red"] == [] and {"S166-OLD-WIRE", "S166-OLD-DORMANT"} <= set(r["all"]), _show(r)
    assert any(c.startswith("S165-WK-") for c in r["all"])
    f = _run(leg="old", faults=["arrival_on_seq"])
    assert set(f["red"]) == set(t2.FAULT_REDS["old"]["arrival_on_seq"]), _show(f)
    v14 = _run(leg="old", stage="a0b")
    assert v14["red"] == [], _show(v14)                                                     # green on v14 (the design's OLD)
    assert "as recorded" in v14["detail"].get("S166-OLD-WIRE", "") or "S166-OLD-WIRE" not in v14["red"]


# ---- roam
def test_s166t2_roam_on_the_instrument_is_green_but_the_owner_gate(t2):
    r = _run(leg="roam")
    assert r["red"] == ["S166-RM-GATE"], _show(r)
    assert "THE INSTRUMENT" in r["detail"]["S166-RM-GATE"]


@pytest.mark.parametrize("lever", ["ghost", "lanegap"])
def test_s166t2_roam_each_lever_calibrates_exactly(t2, lever):
    r = _run(leg="roam", cal=True, lever=lever)
    assert set(r["red"]) - {"S166-RM-GATE"} == set(t2.ROAM_LEVER_PREDICTED[lever]) and _cal_ok(r, "S166-ROAM-CAL"), _show(r)


def test_s166t2_roam_old_on_a0b_and_the_seam_fault(t2):
    old = _run(leg="roam", stage="a0b", cal=True)
    assert set(old["red"]) - {"S166-RM-GATE"} == set(t2.ROAM_OLD_PREDICTED) and _cal_ok(old, "S166-ROAM-CAL"), _show(old)
    f = _run(leg="roam", faults=["ghost_unwrapped"])
    assert set(f["red"]) - {"S166-RM-GATE"} == set(t2.FAULT_REDS["roam"]["ghost_unwrapped"]), _show(f)


def test_s166t2_a_roam_lever_the_engine_ignores_reds_the_calibration_alone():
    r = _run(leg="roam", cal=True, lever="ghost", faults=["ghost_lever_ignored"])
    assert set(r["red"]) - {"S166-RM-GATE"} == {"S166-ROAM-CAL"}, _show(r)


# ---- freeze
def test_s166t2_freeze_is_green_on_the_s166_stand_in(t2):
    r = _run(leg="freeze")
    assert r["red"] == [], _show(r)


@pytest.mark.parametrize("lever", ["lanegap", "ghost"])
def test_s166t2_freeze_each_lever_calibrates_exactly(t2, lever):
    r = _run(leg="freeze", cal=True, lever=lever)
    assert set(r["red"]) == set(t2.FREEZE_LEVER_PREDICTED[lever]) and _cal_ok(r, "S166-FREEZE-CAL"), _show(r)


@pytest.mark.parametrize("fault", ["hold_on_valid", "gap_on_stamp", "arrival_on_seq", "line_dark"])
def test_s166t2_each_freeze_fault_turns_exactly_its_rows_red(t2, fault):
    r = _run(leg="freeze", faults=[fault])
    assert set(r["red"]) == set(t2.FAULT_REDS["freeze"][fault]), _show(r)


# ---- T2-H
def test_s166t2_t2_h_is_green_on_the_s166_host_stand_in(t2):
    r = _run(leg="host")
    assert r["red"] == [], _show(r)
    assert set(t2.HOST_ROWS) <= set(r["all"])


@pytest.mark.parametrize("lever", ["hostlines", "ghost"])
def test_s166t2_t2_h_each_lever_calibrates_exactly(t2, lever):
    r = _run(leg="host", cal=True, lever=lever)
    assert set(r["red"]) == set(t2.HOST_LEVER_PREDICTED[lever]) and _cal_ok(r, "S166-TH-CAL"), _show(r)


def test_s166t2_t2_h_old_on_a0b_and_the_state_b0_fault(t2):
    old = _run(leg="host", stage="a0b", cal=True)
    assert set(old["red"]) == set(t2.HOST_OLD_PREDICTED) and _cal_ok(old, "S166-TH-CAL"), _show(old)
    f = _run(leg="host", faults=["host_lines_state_b0"])
    assert set(f["red"]) == set(t2.FAULT_REDS["host"]["host_lines_state_b0"]), _show(f)


# ---- the duo (D-BATTLE needs a diorama model: named "not run" on the stand-in, judged by its pure test)
_NOT_ON_STAND_IN = {"S166-D-BATTLE"}


def test_s166t2_the_duo_is_green_on_two_s166_stand_ins_but_the_named_battle():
    r = _run("duo")
    assert set(r["red"]) == _NOT_ON_STAND_IN, _show(r)
    assert "not run" in r["detail"]["S166-D-BATTLE"]


#: `ghost sticky` (D-REJOIN's lever) is NOT drivable on the stand-in: its rejoin starts the guest's own exit at the host's intent, so no
#: live guest sample ever sees the host on place 2 -- its calibration is the pure judge (judge_d_rejoin red + sticky_measured) and the game
@pytest.mark.parametrize("lever", ["ghost", "dot"])
def test_s166t2_each_duo_lever_calibrates_exactly(t2, lever):
    r = _run("duo", cal=True, lever=lever)
    want = set(t2.DUO_LEVER_PREDICTED[lever]) | _NOT_ON_STAND_IN
    assert set(r["red"]) - {"S166-D-CAL"} == want and "S166-D-CAL" not in r["red"], _show(r)


@pytest.mark.parametrize("fault", ["dot_src_section0"])
def test_s166t2_each_duo_fault_turns_exactly_its_rows_red(t2, fault):
    r = _run("duo", faults=[fault])
    assert set(r["red"]) - _NOT_ON_STAND_IN == set(t2.FAULT_REDS["duo"][fault]), _show(r)


def test_s166t2_the_duo_on_two_a0b_stand_ins_draws_nothing(t2):
    r = _run("duo", stage="a0b", cal=True)
    assert set(r["red"]) - {"S166-D-CAL"} == set(t2.DUO_OLD_PREDICTED), _show(r)
    assert "S166-D-CAL" not in r["red"], _show(r)



@pytest.mark.parametrize("leg,lever", [("freeze", "lanegap"), ("host", "hostlines")])
def test_s166t2_a_lever_the_engine_ignores_reds_the_calibration_alone(t2, leg, lever):
    r = _run(leg=leg, cal=True, lever=lever, faults=[t2.LEVER_IGNORED[lever]])
    cal = "S166-TH-CAL" if leg == "host" else f"S166-{leg.upper()}-CAL"
    assert set(r["red"]) == {cal}, _show(r)


# ================================================================================================ the engine pin (by stage)
def test_s166t2_the_engine_publishes_every_key_word_and_line_the_t2_and_duo_rows_judge():
    """The s166 source (the patch on the stack, else $FF9_S166_CLONE; the A0b stage SKIPS): every harness key the T2 / duo rows read, the
    owner-visible words and the log texts their judges match, as the engine writes them."""
    from .test_coop_world_walk import _body_of, _s166_text
    agent = _s166_text("HarnessAgent.cs")
    keyed = re.compile(r'(?:Str|Num|Bool)\(sb, "([a-z_0-9]+)"')
    heads = re.compile(r'\\"([a-z_0-9]+)\\":')
    wp = _body_of(agent, "private static void AppendWirePeer(")
    if not wp:
        pytest.skip("this s166 source carries no A2 (AppendWirePeer) yet")
    assert {"rejected", "last_version", "lines", "mismatch", "words"} <= set(keyed.findall(wp)) | set(heads.findall(wp))
    lane = _body_of(agent, "private static void AppendWorldLane(")
    if not lane:
        pytest.skip("this s166 source carries no A3 (AppendWorldLane) yet")
    lk = set(keyed.findall(lane)) | set(heads.findall(lane))
    for k in ("rx", "tx", "seq", "kind", "samples", "place", "mode", "x", "z", "arrival_age_ms", "seq_age_ms", "caps", "peer", "gaps",
              "hangs"):
        assert k in lk, k
    line = _body_of(agent, "private static void AppendWorldLine(")
    assert {"asked", "text", "drawn"} <= set(keyed.findall(line))
    host = _body_of(agent, "private static void AppendNetsyncHost(") + _body_of(agent, "private static void AppendWorldGuest(")
    assert "guest" in host or "AppendWorldGuest" in agent
    ghost = _body_of(agent, "private static void AppendWorldGhost(")
    if not ghost:
        pytest.skip("this s166 source carries no A4 (AppendWorldGhost) yet")
    gk = set(keyed.findall(ghost))
    for k in ("want", "why_not", "shown", "placed", "tx", "tz", "x", "z", "yaw", "stall", "anim", "clip", "stand", "seq_age_ms", "snaps",
              "hides", "mints"):
        assert k in gk, k
    dot = _body_of(agent, "private static void AppendWorldDot(")
    assert {"src", "src_x", "src_z"} <= set(keyed.findall(dot))
    walk = _s166_text("NetSyncWorldWalk.cs")
    for words in (BW.WORDS_WW_WIRE_MISMATCH, BW.WORDS_WW_LOST_CONTACT, BW.WORDS_WW_HOST_FOLLOWING, BW.WORDS_WW_HOST_LOADING,
                  BW.WORDS_WW_HOST_SCENE):
        assert words.replace('"', '\\"') in walk, words
    assert '"host world: "' in walk and '"the partner is "' in walk          # HostLogText (judge_th_lines matches both forms)
    assert "the partner's engine speaks wire " in walk and " -- update both machines" in walk   # the peer-wire line (A2)
    for name in ("no_record", "role", "stale", "not_live", "peer_block"):
        assert f'"{name}"' in walk, name


# ================================================================================================ the runners
_RUNNERS = REPO / "studies" / "world-coop" / "s166-handoff"


def test_the_runners_launch_only_legs_and_levers_the_scenarios_accept(t2):
    """round_a_*.sh: LF, bash-parseable, sourcing the guard library; every COOP_WWT_LEG / COOP_WWT_LEVER / COOP_WW_LEG / COOP_WW_LEVER they
    name is one the scenarios accept (a runner naming a refused lever burns a launch), solo legs under solo_ini.py, and solo_ini resolves
    ITS OWN worktree (it named another one)."""
    ww = None
    for name in ("round_a_lib.sh", "round_a_old.sh", "round_a_new.sh", "round_a_lever.sh", "round_a_regress.sh"):
        b = (_RUNNERS / name).read_bytes()
        assert b"\r" not in b, name
        text = b.decode("ascii")
        if name != "round_a_lib.sh":
            assert '. "$(dirname "$0")/round_a_lib.sh"' in text and "preflight " in text, name
        for leg in re.findall(r"COOP_WWT_LEG=([a-z]+)", text):
            assert leg in t2.LEGS and leg != "record", (name, leg)     # the recorder is OWNER-GATED: never in a runner
        for lever in re.findall(r"COOP_WWT_LEVER=([a-z0-9]+)", text):
            assert lever in sum(t2.LEVERS.values(), ()) + t2.DUO_LEVERS, (name, lever)
        for leg in re.findall(r"COOP_WW_LEG=([a-z]+)", text):
            assert leg in ("tx", "ghost", "wrap", "dot", "body", "stall", "pair"), (name, leg)
    lever_sh = (_RUNNERS / "round_a_lever.sh").read_text(encoding="ascii")
    pairs = re.findall(r"^solo ([a-z]+) ([a-z-]+)$", lever_sh, re.M)
    sys.path.insert(0, str(SCENARIOS))
    spec = importlib.util.spec_from_file_location("coop_world_walk_pin", str(SCENARIOS / "coop_world_walk.py"))
    ww = importlib.util.module_from_spec(spec)
    old = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("COOP_")}
    try:
        spec.loader.exec_module(ww)
    finally:
        os.environ.update(old)
    assert pairs and all((v == "-" and not ww.A_LEVERS[leg]) or v in ww.A_LEVERS[leg] for leg, v in pairs), pairs
    assert {leg for leg, _v in pairs} == set(ww.A_LEGS)
    for leg, levers in t2.LEVERS.items():
        for v in levers:
            assert f"t2 {leg} {v}" in lever_sh, (leg, v)
    new_sh = (_RUNNERS / "round_a_new.sh").read_text(encoding="ascii")
    order = [new_sh.find(k) for k in ("COOP_WW_LEG=tx", "COOP_WWT_LEG=wire", "COOP_WWT_LEG=old", "COOP_WW_LEG=$l", "COOP_WW_LEG=stall",
                                      "COOP_WWT_LEG=roam", "COOP_WWT_LEG=freeze", "COOP_WWT_LEG=host", "duo.py $SC/coop_world_walk_t2.py")]
    assert -1 not in order and order == sorted(order), order        # the design's Order: proof, wire + restamp, tx, ghosts, stall, T2, duo
    solo = (_RUNNERS / "solo_ini.py").read_text(encoding="utf-8")
    assert "dreamy-allen" not in solo.split("WT = ")[1].split("\n")[0] and "Path(__file__).resolve().parents[3]" in solo
    lib = (_RUNNERS / "round_a_lib.sh").read_text(encoding="ascii")
    assert "bench_blockers" in lib and "49201" in lib and "FF9.exe" in lib and "9e4365349fab02b1" in lib



def test_s166t2_the_roam_recorder_refuses_without_the_owners_go():
    """COOP_TAPE_WORLD_ROAM's recorder is OWNER-GATED: with no COOP_WWT_RECORD_OWNER it records nothing and edits nothing (REC-OWNER red,
    every other row unreached, REC-INI green: never edited)."""
    r = _run(leg="record")
    assert "REC-OWNER" in r["red"] and "UNSET" in r["detail"]["REC-OWNER"], _show(r)
    assert "REC-INI" not in r["red"] and "never edited" in r["detail"]["REC-INI"]
    assert all("THE OWNER GATE" in r["detail"][c] for c in r["red"] if c != "REC-OWNER"), _show(r)
