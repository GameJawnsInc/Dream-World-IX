"""[ff9mapkit netsync s166] WORLD WALK, ROUND A -- THE STAND-IN'S MODEL of A1 + A3 + A4: battlewire's twins of every
round-A rule, each pinned to the ENGINE's source BY STAGE, and fakegame's `worldwalk` rung pieces "a3" / "a4" (studies/world-coop/
S166-DESIGN.md decisions 2-12 and 25, "The stand-in").

  * THE TWINS: every rule's truth table (the engine proof's own rows, re-stated), and every one-line mutant of a twin fails ITS OWN row
    (a mutant caught by another row proves nothing about its term).
  * THE ENGINE PINS, by stage: the s166 patch on this branch's stack (tests/_patchstack.stack_file), else a clone named by FF9_S166_CLONE
    carrying the s166 tag; else (the deployed A0b stage) each pin SKIPS. A source with A0 / A0b only (no A1) skips the A1 pins; one without
    A3 skips the A3 pins, one without A4 the A4 pins. Constants, term order, names, row tables and line texts are read off the source, so a
    drift goes red. (The W2 reconcile pinned A4's FINAL contract: its pure rules' twins, its verb, the ghost's names and lines, the catch.)
  * THE CODEC: battlewire's trailer vocabulary is coop_peer's (the bytes) and the engine's (the pin above).
  * THE STAND-IN, stepped BY HAND (no thread, no Session): the selftest slot's trailer, w_blockReady stale on a field, the own sync load,
    the bench host's ops and writer, the receiver cache, the lane, the host's and the world's lines, the wire peer, the ghost and the dot's
    source (A4), the proof's tallies derived from the source -- and every round-A fault turns EXACTLY its model rows red.
"""
import json
import os
import pathlib
import re
import sys
import tempfile
from types import SimpleNamespace

import pytest

from ._patchstack import msr, stack_file

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

S166_TAG = "[ff9mapkit netsync s166]"
S166_CLONE_ENV = "FF9_S166_CLONE"
_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


# ================================================================================================ THE TWINS (pure)
def _rules(**swap):
    """The twin rule set (a mutant swaps exactly one entry)."""
    r = SimpleNamespace(kind=BW.ww_lane_gap_kind, step=BW.ww_lane_gap_step, end_len=BW.ww_lane_end_len_rule, host=BW.ww_host_line_rule,
                        edge=BW.ww_host_line_edge_step, line=BW.ww_world_line_rule, ghost=BW.ww_ghost_rule, who=BW.ww_ghost_who_rule,
                        stall=BW.ww_ghost_stall_rule, ease=BW.ww_torus_ease_step, snap=BW.ww_ghost_snap_rule, place=BW.ww_ghost_place_step,
                        body=BW.ww_world_body_rule, ratio=BW.ww_world_body_ratio, path=BW.ww_bench_path_pose, scene=BW.ww_scene_bit_step,
                        cache=BW.ww_world_cache_step, deliver=BW.ww_bench_deliver_rule, flags=BW.ww_trailer_flags_rule,
                        rot=lambda dx, dz: BW.ww_walker_rotation(BW.ww_walker_yaw(dx, dz)), record=BW.ww_record_field_rule,
                        where=BW.ww_place_rule, header=BW.ww_wire_header_rule, once=BW.ww_version_line_once, feature=BW.ww_feature_on,
                        mismatch=BW.ww_wire_mismatch_rule, redial=BW.ww_redial_say_step, gate=BW.ww_ghost_scene_gate,
                        walk=BW.ww_walk_world_rule, render=BW.ww_render_of)
    for k, v in swap.items():
        assert hasattr(r, k), k
        setattr(r, k, v)
    return r


def _sample(place, state=0, follows=True, **kw):
    """A peer's sample as the cache holds it (SampleFixture): the world block filled on place 4."""
    t = BW.ww_trailer(has=True, fmt=1, caps=BW.WW_CAP_WORLD_POSE, seq=100, place=place, state=state,
                      flags=BW.WW_FLAG_FOLLOW if follows else 0)
    if place == BW.WW_PLACE_WORLD:
        t.update(world=9011, x=70.0, z=-444.0, rot=(0.0, 0.0, 0.0, 1.0), model=BW.WW_GEO_ZIDANE)
    t.update(kw)
    return t


def _facts(**kw):
    """GhostFixture: a frozen guest on 9011 seeing its live host, every term passing."""
    f = BW.ww_ghost_facts(who=True, on_world=True, block_ready=True, walker=True, own_world=9011, own_idx=11, own_sc=1000,
                          own_frozen=True, peer=_sample(BW.WW_PLACE_WORLD, BW.WW_ST_CONTROL | BW.WW_ST_VISIBLE), peer_idx=11,
                          peer_sc=1000, peer_sc_known=True, seq_age_ms=30, arrival_age_ms=30)
    f.update(kw)
    return f


def _lane_run(r, steps, lever_off=False):
    """LaneGapStep over (arrival_age, seq_age, place) steps -> the lines said and the book."""
    b, out = BW.ww_lane_book(), []
    for a, s, p in steps:
        line, n = r.step(b, a, s, p, lever_off)
        if line:
            out.append((line, n))
    return out, b


def _scene_run(r, steps):
    """SceneBitStep over (dt, live, control, visible, fullmap, fading, menu) -> the last bit."""
    c, now, bit = BW.ww_scene_clock(), 0, False
    for dt, *args in steps:
        now += dt
        bit = r.scene(c, *args, now)
    return bit


def _ghost_row(r, why, **kw):
    return r.ghost(_facts(**kw)) == why


def _slots_at(x, z):
    return BW.ww_ring_slots(x, z)


ROWS = {
    # ---- the codec helpers
    "record.world_sample_field_zero": lambda r: r.record(BW.WW_PLACE_WORLD, 6603) == 0 and r.record(BW.WW_PLACE_WORLD_LOADING, 6603) == 0
    and r.record(BW.WW_PLACE_DIORAMA, 6603) == 0,
    "record.field_keeps_field": lambda r: r.record(BW.WW_PLACE_FIELD, 6603) == 6603 and r.record(BW.WW_PLACE_TRANSITION, 6603) == 6603,
    "place.title": lambda r: r.where(True, True, True, True, True, True, True) == BW.WW_PLACE_NONE,
    "place.transition_any_scene": lambda r: r.where(False, True, True, True, True, True, True) == BW.WW_PLACE_TRANSITION,
    "place.world_loading": lambda r: r.where(False, False, False, False, True, False, False) == BW.WW_PLACE_WORLD_LOADING,
    "place.world_live": lambda r: r.where(False, False, False, False, True, True, False) == BW.WW_PLACE_WORLD,
    "place.field_after_world_visit_is_field": lambda r: r.where(False, False, False, False, False, True, True) == BW.WW_PLACE_FIELD,
    "place.battle_and_diorama": lambda r: r.where(False, False, False, True, False, False, False) == BW.WW_PLACE_BATTLE
    and r.where(False, False, True, True, True, True, True) == BW.WW_PLACE_DIORAMA,
    # ---- the wire
    "wire.mine": lambda r: r.header(BW.WW_MAGIC, 15, 15) == BW.WW_WIRE_MINE,
    "wire.other_version_counted": lambda r: r.header(BW.WW_MAGIC, 14, 15) == BW.WW_WIRE_OTHER,
    "wire.foreign_magic_not_counted": lambda r: r.header(0x47, 14, 15) == BW.WW_WIRE_FOREIGN,
    "wire.version_line_once": lambda r: (lambda s: r.once(s, 14) and not r.once(s, 14) and r.once(s, 13))(set()),
    "caps.capless_peer_feature_off": lambda r: not r.feature(BW.WW_OWN_CAPS, 0, BW.WW_CAP_WORLD_POSE)
    and r.feature(BW.WW_OWN_CAPS, BW.WW_CAP_WORLD_POSE, BW.WW_CAP_WORLD_POSE),
    "wire.mismatch_ages_out": lambda r: r.mismatch(4999, -1) and not r.mismatch(5000, -1) and not r.mismatch(-1, -1),
    "wire.mismatch_mine_clears": lambda r: not r.mismatch(300, 100) and r.mismatch(300, 900),
    "redial.same_reason_quiet": lambda r: (lambda s: r.redial(s, "a", False) and not r.redial(s, "a", False))([]),
    "redial.alternating_said_once": lambda r: (lambda s: r.redial(s, "a", False) and r.redial(s, "b", False)
                                               and not r.redial(s, "a", False) and not r.redial(s, "b", False))([]),
    "redial.carried_link_speaks": lambda r: (lambda s: r.redial(s, "a", False) and r.redial(s, "a", True))([]),
    # ---- the lane
    "lane.kind.fresh": lambda r: r.kind(30, 30, BW.WW_PLACE_WORLD) == BW.WW_LANE_OK,
    "lane.kind.jitter_300_no_line": lambda r: r.kind(300, 300, BW.WW_PLACE_WORLD) == BW.WW_LANE_OK,
    "lane.kind.stall_is_gap": lambda r: r.kind(1200, 1200, BW.WW_PLACE_WORLD) == BW.WW_LANE_GAP,
    "lane.kind.world_load_is_loading_hang": lambda r: r.kind(34, 2500, BW.WW_PLACE_WORLD_LOADING) == BW.WW_LANE_HANG_LOADING,
    "lane.kind.battle_load_is_loading_hang": lambda r: r.kind(34, 1500, BW.WW_PLACE_TRANSITION) == BW.WW_LANE_HANG_LOADING,
    "lane.kind.place4_freeze_is_hang": lambda r: r.kind(34, 1500, BW.WW_PLACE_WORLD) == BW.WW_LANE_HANG,
    "lane.kind.capless_no_hang": lambda r: r.kind(34, -1, BW.WW_PLACE_NONE) == BW.WW_LANE_OK,
    "lane.step.gap_pair": lambda r: _lane_run(r, [(30, 30, 4), (1000, 1000, 4), (1500, 1500, 4), (30, 30, 4)])[0]
    == [(BW.WW_LINE_GAP_START, 1000), (BW.WW_LINE_GAP_END, 1500)],
    "lane.step.loading_pair": lambda r: _lane_run(r, [(30, 30, 3), (30, 1000, 3), (30, 2000, 3), (30, 30, 4)])[0]
    == [(BW.WW_LINE_LOAD_START, 1000), (BW.WW_LINE_LOAD_END, 2000)],
    "lane.step.hang_then_gap": lambda r: [x[0] for x in _lane_run(r, [(30, 1000, 4), (1000, 2200, 4), (1100, 2300, 4)])[0]]
    == [BW.WW_LINE_HANG_START, BW.WW_LINE_HANG_CUT, BW.WW_LINE_GAP_START],
    "lane.count250_once_per_gap": lambda r: _lane_run(r, [(260, 260, 4), (300, 300, 4), (30, 30, 4), (400, 400, 4)])[1]["gaps250"] == 2,
    "lane.lever_off_still_counts": lambda r: (lambda o: o[0] == [] and o[1]["gaps"] == 1)(
        _lane_run(r, [(1000, 1000, 4), (30, 30, 4)], lever_off=True)),
    "lane.no_end_without_start": lambda r: _lane_run(r, [(1000, 1000, 4), (30, 30, 4)], lever_off=True)[0] == [],
    "lane.loads_keep_stall_lines": lambda r: (lambda o: o[0][-1] == (BW.WW_LINE_GAP_START, 1000))(
        _lane_run(r, [x for _ in range(25) for x in ((30, 1000, 3), (30, 30, 4))] + [(1000, 1000, 4)])),
    "lane.budget_then_counted_only": lambda r: [x[0] for x in _lane_run(r, [x for _ in range(21) for x in ((1000, 1000, 4), (30, 30, 4))])[0]][-1]
    == BW.WW_LINE_STALL_BUDGET,
    "lane.end_len.hang_from_sender_ms": lambda r: r.end_len(BW.WW_LINE_HANG_END, 2500, 1300) == 1300
    and r.end_len(BW.WW_LINE_LOAD_END, 2500, 1300) == 1300,
    "lane.end_len.gap_on_receiver": lambda r: r.end_len(BW.WW_LINE_GAP_END, 2500, 1300) == 2500
    and r.end_len(BW.WW_LINE_HANG_CUT, 2500, 1300) == 2500,
    "lane.end_len.no_span_keeps_mine": lambda r: r.end_len(BW.WW_LINE_HANG_END, 2500, -1) == 2500,
    # ---- the host's lines
    "hostline.guest_standing_none": lambda r: r.host(False, True, True, True, _sample(4, BW.WW_ST_CONTROL), 30) == BW.WW_HOST_LINE_NONE,
    "hostline.following_out": lambda r: r.host(False, True, True, True, _sample(2, BW.WW_ST_WORLDOUT), 30) == BW.WW_HOST_LINE_FOLLOWING,
    "hostline.guest_field_fade_none": lambda r: r.host(False, True, True, True, _sample(2, 0), 30) == BW.WW_HOST_LINE_NONE,
    "hostline.loading": lambda r: r.host(False, True, True, True, _sample(3), 30) == BW.WW_HOST_LINE_LOADING,
    "hostline.long_world_load_is_loading": lambda r: r.host(False, True, True, True, _sample(3), 3000) == BW.WW_HOST_LINE_LOADING,
    "hostline.scene": lambda r: r.host(False, True, True, True, _sample(4, BW.WW_ST_SCENE), 30) == BW.WW_HOST_LINE_SCENE,
    "hostline.released_guest_scene": lambda r: r.host(False, True, True, True, _sample(4, BW.WW_ST_SCENE), 30) == BW.WW_HOST_LINE_SCENE
    and not _sample(4, BW.WW_ST_SCENE)["state"] & BW.WW_ST_FROZEN,
    "hostline.lost_contact": lambda r: r.host(False, True, True, True, _sample(4), 5000) == BW.WW_HOST_LINE_LOST,
    "hostline.no_follow_no_lines": lambda r: r.host(False, True, True, True, _sample(4, BW.WW_ST_SCENE, False), 30) == BW.WW_HOST_LINE_NONE,
    "hostline.host_on_field_none": lambda r: r.host(False, True, False, True, _sample(3), 30) == BW.WW_HOST_LINE_NONE,
    "hostline.client_or_unlinked_none": lambda r: r.host(False, False, True, True, _sample(3), 30) == BW.WW_HOST_LINE_NONE
    and r.host(False, True, True, False, _sample(3), 30) == BW.WW_HOST_LINE_NONE,
    "hostline.lever_off": lambda r: r.host(True, True, True, True, _sample(3), 30) == BW.WW_HOST_LINE_NONE,
    "hostlog.unsaid_end_silent": lambda r: (lambda b: [r.edge(b, s, t)[0] for s, t in
                                                       [(1, 0), (0, 10)] * 20 + [(1, 999), (0, 1000)]][-2:] == [BW.WW_HOST_LOG_BUDGET, 0])(
        BW.ww_host_line_book()),
    "hostlog.budget_21st_is_the_over_line": lambda r: (lambda b: [r.edge(b, s, t)[0] for s, t in [(1, 0), (0, 10)] * 21][-2]
                                                       == BW.WW_HOST_LOG_BUDGET)(BW.ww_host_line_book()),
    "hostlog.edges_with_duration": lambda r: (lambda b: (r.edge(b, 1, 100), r.edge(b, 0, 600))[1][4] == 500)(BW.ww_host_line_book()),
    # ---- the world line
    "line.mismatch_first": lambda r: r.line(True, BW.WW_HOST_LINE_LOST, True, True) == BW.WW_WORLD_LINE_MISMATCH
    and r.line(True, BW.WW_HOST_LINE_SCENE, False, False) == BW.WW_WORLD_LINE_MISMATCH,
    "line.session_line_speaks_first": lambda r: r.line(False, BW.WW_HOST_LINE_LOST, True, True) == BW.WW_WORLD_LINE_NONE,
    "line.host_line_before_lost": lambda r: r.line(False, BW.WW_HOST_LINE_SCENE, True, False) == BW.WW_HOST_LINE_SCENE,
    "line.ghost_stale_is_lost": lambda r: r.line(False, BW.WW_HOST_LINE_NONE, True, False) == BW.WW_HOST_LINE_LOST,
    "line.none": lambda r: r.line(False, BW.WW_HOST_LINE_NONE, False, False) == BW.WW_WORLD_LINE_NONE,
    # ---- who, the gate, the walk set
    "who.client_following": lambda r: r.who(True, "client", True, False, True, BW.ww_trailer()),
    "who.client_free_roamer": lambda r: not r.who(True, "client", False, False, True, BW.ww_trailer()),
    "who.host_following_guest": lambda r: r.who(True, "host", False, False, True, _sample(4, 0, True)),
    "who.host_released_guest": lambda r: r.who(True, "host", False, False, True, _sample(4, 0, True))
    and not _sample(4, 0, True)["state"] & BW.WW_ST_FROZEN,
    "who.host_no_follow_flag": lambda r: not r.who(True, "host", False, False, True, _sample(4, BW.WW_ST_FROZEN, False)),
    "who.bench": lambda r: r.who(True, "selftest", False, True, False, BW.ww_trailer()),
    "who.coop_off": lambda r: not r.who(False, "client", True, True, True, _sample(4)),
    "gate.field_after_world_visit_no_mint": lambda r: not r.gate(False, True) and r.gate(True, True),
    "walk.9000_not_a_walk_world": lambda r: not r.walk(9000) and r.walk(9002) and r.walk(9010) and r.walk(9011),
    # ---- GhostRule: each refusal alone, in decision 9's order, the lever last
    "ghost.shows": lambda r: _ghost_row(r, BW.WW_GHOST_SHOW),
    "ghost.frozen_guest_sees_host": lambda r: _ghost_row(r, BW.WW_GHOST_SHOW, own_frozen=True),
    "ghost.role": lambda r: _ghost_row(r, BW.WW_GHOST_ROLE, who=False),
    "ghost.not_live": lambda r: _ghost_row(r, BW.WW_GHOST_NOT_LIVE, block_ready=False),
    "ghost.event_world": lambda r: _ghost_row(r, BW.WW_GHOST_EVENT_WORLD, event_world=True),
    "ghost.my_9000_walk_set": lambda r: _ghost_row(r, BW.WW_GHOST_WALK_SET, own_world=9000),
    "ghost.no_record": lambda r: _ghost_row(r, BW.WW_GHOST_NO_RECORD, peer=BW.ww_trailer()),
    "ghost.peer_caps": lambda r: _ghost_row(r, BW.WW_GHOST_PEER_CAPS, peer=_sample(4, caps=0)),
    "ghost.peer_battle_place5": lambda r: _ghost_row(r, BW.WW_GHOST_PEER_BLOCK, peer=dict(_sample(4), place=BW.WW_PLACE_BATTLE)),   # kept its world
    "ghost.peer_no_walker": lambda r: _ghost_row(r, BW.WW_GHOST_PEER_BLOCK, peer=_sample(4, world=0)),
    "ghost.peer_place2_hides": lambda r: _ghost_row(r, BW.WW_GHOST_PEER_BLOCK, peer=_sample(BW.WW_PLACE_TRANSITION),
                                                    peer_last_world=_sample(4)),
    "ghost.sticky_holds_place2": lambda r: _ghost_row(r, BW.WW_GHOST_SHOW, peer=_sample(BW.WW_PLACE_TRANSITION),
                                                      peer_last_world=_sample(4), sticky=True),
    "ghost.pose_range": lambda r: _ghost_row(r, BW.WW_GHOST_POSE_RANGE, peer=_sample(4, x=float("nan"))),
    "ghost.peer_9013_on_my_9011_other_world": lambda r: _ghost_row(r, BW.WW_GHOST_OTHER_WORLD, peer=_sample(4, world=9013)),
    "ghost.band": lambda r: _ghost_row(r, BW.WW_GHOST_BAND, peer_sc=6000),
    "ghost.peer_riding": lambda r: _ghost_row(r, BW.WW_GHOST_RIDING, peer=_sample(4, mode=1)),
    "ghost.peer_scene": lambda r: _ghost_row(r, BW.WW_GHOST_PEER_SCENE, peer=_sample(4, BW.WW_ST_SCENE)),
    "ghost.peer_hung_6s_stale": lambda r: _ghost_row(r, BW.WW_GHOST_STALE, seq_age_ms=6000, arrival_age_ms=30),
    "ghost.lever": lambda r: _ghost_row(r, BW.WW_GHOST_LEVER, lever_off=True),
    "ghost.lever_last": lambda r: _ghost_row(r, BW.WW_GHOST_STALE, seq_age_ms=6000, lever_off=True),
    # ---- the stall hold
    "stall.moving": lambda r: r.stall(100) == BW.WW_STALL_MOVE,
    "stall.seq_frozen_400ms_stands": lambda r: r.stall(400) == BW.WW_STALL_STAND,
    "stall.hide_at_5s": lambda r: r.stall(5000) == BW.WW_STALL_HIDE and r.stall(-1) == BW.WW_STALL_HIDE,
    # ---- the torus and the motion
    "ease.x_seam_short_way": lambda r: (lambda p: p[0] > 1500.0 or p[0] < 40.0)(r.ease(1530.0, 0.0, -400.0, 6.0, 0.0, -400.0, 0.05)),
    "ease.z_seam_short_way": lambda r: (lambda p: p[2] > -40.0 or p[2] < -1240.0)(r.ease(100.0, 0.0, -1275.0, 100.0, 0.0, -5.0, 0.05)),
    "ease.converges_and_holds": lambda r: (lambda p: abs(p[0] - 200.0) < 0.01)(r.ease(200.0, 0.0, -400.0, 200.0, 0.0, -400.0, 0.05)),
    "snap.first_show": lambda r: r.snap(False, False, 0.0),
    "snap.world_change": lambda r: r.snap(True, True, 0.0),
    "snap.jump_over_64": lambda r: r.snap(True, False, 64.5) and r.snap(True, False, float("nan")),
    "snap.ease_a_25u_resume": lambda r: not r.snap(True, False, 25.0),
    "place.render_of": lambda r: r.render(70.0, -444.0, _slots_at(70.0, -444.0))[0] and not r.render(float("nan"), -1.0, _slots_at(0, 0))[0],
    "place.standing_ghost_across_my_wrap": lambda r: all(
        (lambda m: (r.place(m, 9011, 1530.0, 0.0, -400.0, (0.0, 0.0, 0.0, 1.0), 0.0, _slots_at(1500.0, -400.0)),
                    r.place(m, 9011, 1530.0, 0.0, -400.0, (0.0, 0.0, 0.0, 1.0), 1 / 30, _slots_at(ox, -400.0)),
                    BW.ww_ring_inverse(m["rx"], m["rz"], ox, -400.0))[2])(BW.ww_ghost_motion())[0] == pytest.approx(1530.0, abs=0.01)
        for ox in (1500.0, 1530.0, 1600.0 - 1536.0, 10.0)),
    # ---- the body
    "body.9002_undressed_dagger": lambda r: r.body(BW.WW_GEO_DAGGER) == BW.WW_GEO_DAGGER,
    "body.9010_9011_undressed_zidane": lambda r: r.body(BW.WW_GEO_ZIDANE) == BW.WW_GEO_ZIDANE,
    "body.zeroed_block_no_body": lambda r: r.body(0) == -1,
    "body.mog_ratio_76": lambda r: r.ratio(BW.WW_GEO_MOG) == 76 and r.ratio(BW.WW_GEO_ZIDANE) == 67,
    # ---- the bench path
    "path.x_seam_leg_short_way": lambda r: (lambda p: p[0] and (p[1] > 1490.0 or p[1] < 20.0))(r.path([10.0, -10.0, 1500.0, -10.0], 2, 24.0,
                                                                                                   False, 1000)),
    "path.loop_wraps_to_start": lambda r: (lambda p: p[0] and abs(p[1] - 10.0) < 0.5)(r.path([10.0, -10.0, 34.0, -10.0], 2, 24.0, True,
                                                                                               2000)),
    "path.end_stands": lambda r: (lambda p: not p[0] and p[1] == 34.0)(r.path([10.0, -10.0, 34.0, -10.0], 2, 24.0, False, 5000)),
    "path.walker_heading": lambda r: r.path([10.0, -10.0, 34.0, -10.0], 2, 24.0, False, 500)[3] == pytest.approx(270.0),
    # ---- the scene bit
    "scene.control_off_600ms_set": lambda r: _scene_run(r, [(0, True, False, True, False, False, False)] + [(100, True, False, True, False,
                                                                                                              False, False)] * 6),
    "scene.control_off_300ms_clear": lambda r: not _scene_run(r, [(0, True, False, True, False, False, False)] + [(100, True, False, True,
                                                                                                                   False, False, False)] * 3),
    "scene.walker_hidden_600ms_set": lambda r: _scene_run(r, [(0, True, True, False, False, False, False)] + [(100, True, True, False,
                                                                                                               False, False, False)] * 6),
    "scene.menu_hold_1s_clear": lambda r: not _scene_run(r, [(0, True, False, True, False, False, True)] + [(100, True, False, True, False,
                                                                                                              False, True)] * 10),
    "scene.own_fullmap_1s_clear": lambda r: not _scene_run(r, [(0, True, False, True, True, False, False)] + [(100, True, False, True, True,
                                                                                                               False, False)] * 10),
    "scene.fade_1s_clear": lambda r: not _scene_run(r, [(0, True, False, True, False, True, False)] + [(100, True, False, True, False, True,
                                                                                                         False)] * 10),
    "scene.excluded_pauses": lambda r: _scene_run(r, [(0, True, False, True, False, False, False)] + [(100, True, False, True, False, False,
                                                                                                        False)] * 4
                                                  + [(100, True, False, True, False, True, False)] * 5 + [(100, True, False, True, False,
                                                                                                             False, False)] * 2),
    # ---- A3: the rotation, the flags, the cache, the bench host's writer
    "rot.walker_heading_not_travel": lambda r: all(abs(a - b) < 1e-6 for a, b in zip(r.rot(0.0, -1.0), (0.0, 0.0, 0.0, 1.0))),
    "rot.east_270": lambda r: all(abs(a - b) < 1e-4 for a, b in zip(r.rot(1.0, 0.0), (0.0, 0.70710678, 0.0, -0.70710678))),
    "flags.client_follow_b0": lambda r: r.flags("client", True) == BW.WW_FLAG_FOLLOW and r.flags("client", False) == 0,
    "flags.host_never_follows": lambda r: r.flags("host", True) == 0,
    "flags.selftest_stands_in": lambda r: r.flags("selftest", True) == BW.WW_FLAG_FOLLOW,
    "cache.resend_moves_arrival_not_seq": lambda r: (lambda c: (r.cache(c, True, 100, 94, 3, _sample(4, seq=7), 100),
                                                                r.cache(c, True, 600, 94, 3, _sample(4, seq=7), 600),
                                                                c["arrival_tick"] == 600 and c["seq_move_tick"] == 100)[2])(BW.ww_world_cache()),
    "cache.valid_cliff_holds_both_clocks": lambda r: (lambda c: (r.cache(c, True, 100, 94, 3, _sample(4, seq=7), 100),
                                                                 r.cache(c, False, 0, 0, 0, BW.ww_trailer(), 3000),
                                                                 c["has"] and c["arrival_tick"] == 100 and c["seq_set"])[2])(BW.ww_world_cache()),
    "cache.world_sample_kept_through_place3": lambda r: (lambda c: (r.cache(c, True, 100, 94, 3, _sample(4, seq=7), 100),
                                                                    r.cache(c, True, 200, 94, 3, _sample(3, seq=8), 200),
                                                                    c["world_set"] and c["world"]["seq"] == 7 and c["latest"]["seq"] == 8)[2])(
        BW.ww_world_cache()),
    "cache.capless_has_no_seq": lambda r: (lambda c: (r.cache(c, True, 100, 94, 3, _sample(4, seq=7), 100),
                                                      r.cache(c, True, 200, 39, 0, BW.ww_trailer(), 200), not c["seq_set"])[2])(BW.ww_world_cache()),
    "bench.freeze_resends": lambda r: r.deliver(True, False) == (True, False),
    "bench.gap_keeps_building": lambda r: r.deliver(False, True) == (False, True),
}


def _m(fn):
    return fn


#: the twins' one-line mutants -> the row that must catch each (the engine proof's own names where it has them)
MUTANTS = {
    "field_world": (dict(record=lambda p, f: 9011 if p in (3, 4, 6) else f), "record.world_sample_field_zero"),
    "place_stale_block_ready": (dict(where=lambda ti, tr, di, ba, on, br, fl: 4 if not (ti or tr or di or ba) and br
                                     else BW.ww_place_rule(ti, tr, di, ba, on, br, fl)), "place.field_after_world_visit_is_field"),
    "wire_magic_blind": (dict(header=lambda mg, v, own: 0 if v == own else 2), "wire.foreign_magic_not_counted"),
    "version_line_always": (dict(once=lambda s, v: (BW.ww_version_line_once(s, v), True)[1]), "wire.version_line_once"),
    "caps_own_only": (dict(feature=lambda own, peer, bit: BW.ww_feature_on(own, own, bit)), "caps.capless_peer_feature_off"),
    "mismatch_latched": (dict(mismatch=lambda rf, mn: rf >= 0 and (mn < 0 or mn > rf)), "wire.mismatch_ages_out"),
    "mismatch_mine_blind": (dict(mismatch=lambda rf, mn: BW.ww_wire_mismatch_rule(rf, -1)), "wire.mismatch_mine_clears"),
    "redial_never_quiet": (dict(redial=lambda s, ln, c: (BW.ww_redial_say_step(s, ln, c), True)[1]), "redial.same_reason_quiet"),
    "redial_carried_blind": (dict(redial=lambda s, ln, c: BW.ww_redial_say_step(s, ln, False)), "redial.carried_link_speaks"),
    "gap_on_stamp": (dict(kind=lambda a, s, p: BW.ww_lane_gap_kind(s, s, p)), "lane.kind.world_load_is_loading_hang"),
    "arrival_on_seq": (dict(kind=lambda a, s, p: BW.ww_lane_gap_kind(max(a, s), s, p)), "lane.kind.battle_load_is_loading_hang"),
    "hang_always_loading": (dict(kind=lambda a, s, p: (lambda k: 3 if k == 2 else k)(BW.ww_lane_gap_kind(a, s, p))),
                            "lane.kind.place4_freeze_is_hang"),
    "line_at_250": (dict(kind=lambda a, s, p: 1 if a >= 250 else BW.ww_lane_gap_kind(a, s, p)), "lane.kind.jitter_300_no_line"),
    "lever_mutes_counts": (dict(step=lambda b, a, s, p, lv: (0, 0) if lv else BW.ww_lane_gap_step(b, a, s, p, lv)),
                           "lane.lever_off_still_counts"),
    "one_budget": (dict(step=lambda b, a, s, p, lv: (lambda x: (b.__setitem__("stall_pairs", b["stall_pairs"] + 1)
                                                                if x[0] == BW.WW_LINE_LOAD_START else None, x)[1])(
        BW.ww_lane_gap_step(b, a, s, p, lv))), "lane.loads_keep_stall_lines"),
    "hang_cut_as_update": (dict(step=lambda b, a, s, p, lv: (lambda x: (BW.WW_LINE_HANG_END, x[1]) if x[0] == BW.WW_LINE_HANG_CUT else x)(
        BW.ww_lane_gap_step(b, a, s, p, lv))), "lane.step.hang_then_gap"),
    "hang_len_on_receiver": (dict(end_len=lambda ln, rcv, snd: rcv), "lane.end_len.hang_from_sender_ms"),
    "gap_len_from_sender": (dict(end_len=lambda ln, rcv, snd: snd if ln in (2, 4, 6) and snd > 0 else rcv), "lane.end_len.gap_on_receiver"),
    "hostlines_state_b0": (dict(host=lambda lv, h, own, lk, g, a: BW.ww_host_line_rule(lv, h, own, lk, g, a)
                                if g["state"] & BW.WW_ST_FROZEN else 0), "hostline.released_guest_scene"),
    "hostlines_lost_on_seq": (dict(host=lambda lv, h, own, lk, g, a: 4 if a >= 2500 else BW.ww_host_line_rule(lv, h, own, lk, g, a)),
                              "hostline.long_world_load_is_loading"),
    "hostlines_off_world": (dict(host=lambda lv, h, own, lk, g, a: BW.ww_host_line_rule(lv, h, True, lk, g, a)),
                            "hostline.host_on_field_none"),
    "hostlines_place2_any": (dict(host=lambda lv, h, own, lk, g, a: BW.ww_host_line_rule(
        lv, h, own, lk, dict(g, state=g["state"] | BW.WW_ST_WORLDOUT) if g["place"] == 2 else g, a)), "hostline.guest_field_fade_none"),
    "hostlog_end_unsaid": (dict(edge=lambda b, s, t: (lambda x: (BW.WW_HOST_LOG_EDGE,) + x[1:] if x[0] == 0 and x[1] != s and x[1] and s == 0
                                                      else x)(BW.ww_host_line_edge_step(b, s, t))), "hostlog.unsaid_end_silent"),
    "hostlog_no_budget": (dict(edge=lambda b, s, t: (lambda x: (BW.WW_HOST_LOG_EDGE,) + x[1:] if x[1] != s and s and not x[3] else x)(
        BW.ww_host_line_edge_step(b, s, t))), "hostlog.budget_21st_is_the_over_line"),
    "lost_over_session": (dict(line=lambda mm, hl, st, ss: BW.ww_world_line_rule(mm, hl, st, False)), "line.session_line_speaks_first"),
    "mismatch_after_host": (dict(line=lambda mm, hl, st, ss: hl if not ss and 0 < hl <= 4 else BW.ww_world_line_rule(mm, hl, st, ss)),
                            "line.mismatch_first"),
    "ghost_host_state_b0": (dict(who=lambda lv, role, fh, bg, lk, p: lv and lk and p["has"] and bool(p["state"] & BW.WW_ST_FROZEN)
                                 if role == "host" else BW.ww_ghost_who_rule(lv, role, fh, bg, lk, p)), "who.host_released_guest"),
    "ghost_host_any": (dict(who=lambda lv, role, fh, bg, lk, p: bool(lv and lk) if role == "host" else BW.ww_ghost_who_rule(lv, role, fh, bg,
                                                                                                                             lk, p)),
                       "who.host_no_follow_flag"),
    "mint_stale_block_ready": (dict(gate=lambda on, br: br), "gate.field_after_world_visit_no_mint"),
    "walk_set_blind": (dict(walk=lambda w: 9000 <= w <= 9013), "walk.9000_not_a_walk_world"),
    "ghost_by_idx": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, peer=dict(f["peer"], world=f["own_world"]))
                                                           if f["peer_idx"] >= 0 and f["peer_idx"] == f["own_idx"] else f)),
                     "ghost.peer_9013_on_my_9011_other_world"),
    "ghost_own_freeze_hides": (dict(ghost=lambda f: BW.WW_GHOST_NOT_LIVE if f["own_frozen"] else BW.ww_ghost_rule(f)),
                               "ghost.frozen_guest_sees_host"),
    "ghost_place_blind": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, peer=dict(f["peer"], place=4)) if f["peer"]["has"] else f)),
                          "ghost.peer_battle_place5"),
    "ghost_sticky_default": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, sticky=True))), "ghost.peer_place2_hides"),
    "ghost_riding_blind": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, peer=dict(f["peer"], mode=0)))), "ghost.peer_riding"),
    "ghost_scene_blind": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, peer=dict(f["peer"], state=f["peer"]["state"] & ~BW.WW_ST_SCENE)))),
                          "ghost.peer_scene"),
    "ghost_fresh_on_arrival": (dict(ghost=lambda f: BW.ww_ghost_rule(dict(f, seq_age_ms=f["arrival_age_ms"]))), "ghost.peer_hung_6s_stale"),
    "ghost_lever_first": (dict(ghost=lambda f: BW.WW_GHOST_LEVER if f["lever_off"] else BW.ww_ghost_rule(f)), "ghost.lever_last"),
    "hold_on_valid": (dict(stall=lambda s: BW.WW_STALL_MOVE if 0 <= s < 2000 else BW.ww_ghost_stall_rule(s)),
                      "stall.seq_frozen_400ms_stands"),
    "naive_seam_lerp": (dict(ease=lambda x, y, z, tx, ty, tz, dt: BW.ww_torus_ease_step(x, y, z, tx, ty, tz, dt, unwrap=False)),
                        "ease.x_seam_short_way"),
    "render_space_ease": (dict(place=lambda m, w, tx, ty, tz, q, dt, sl: (lambda had, prx, prz: (
        lambda snap: (m.update(rx=prx + (m["rx"] - prx) * BW.ww_ease_k(dt), rz=prz + (m["rz"] - prz) * BW.ww_ease_k(dt))
                      if had and not snap else None, snap)[1])(BW.ww_ghost_place_step(m, w, tx, ty, tz, q, dt, sl)))(
        m["placed"], m["rx"], m["rz"])), "place.standing_ghost_across_my_wrap"),
    "snap_world_blind": (dict(snap=lambda s, w, j: BW.ww_ghost_snap_rule(s, False, j)), "snap.world_change"),
    "snap_small_jump": (dict(snap=lambda s, w, j: BW.ww_ghost_snap_rule(s, w, j * 4.0)), "snap.ease_a_25u_resume"),
    "dress_default_310": (dict(body=lambda model, dress=0: BW.WW_GEO_ZIDANE), "body.9002_undressed_dagger"),
    "ratio_flat": (dict(ratio=lambda model: 67), "body.mog_ratio_76"),
    "scene_menu_hold": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l, ctl, v, fm, fd, False, now)),
                        "scene.menu_hold_1s_clear"),
    "scene_fullmap_counts": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l, ctl, v, False, fd, mh, now)),
                             "scene.own_fullmap_1s_clear"),
    "scene_fade_counts": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l, ctl, v, fm, False, mh, now)),
                          "scene.fade_1s_clear"),
    "scene_no_delay": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l, ctl, v, fm, fd, mh, now)
                            or (l and not (ctl and v) and not (fm or fd or mh))), "scene.control_off_300ms_clear"),
    "scene_control_only": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l, ctl, True, fm, fd, mh, now)),
                           "scene.walker_hidden_600ms_set"),
    "scene_fade_resets": (dict(scene=lambda c, l, ctl, v, fm, fd, mh, now: BW.ww_scene_bit_step(c, l and not (fm or fd or mh), ctl, v, fm, fd,
                                                                                                 mh, now)), "scene.excluded_pauses"),
    "path_no_unwrap": (dict(path=lambda p, n, u, lp, ms: BW.ww_bench_path_pose(p, n, u, lp, ms, unwrap=False)), "path.x_seam_leg_short_way"),
    "path_no_loop": (dict(path=lambda p, n, u, lp, ms: BW.ww_bench_path_pose(p, n, u, False, ms)), "path.loop_wraps_to_start"),
    "rot_travel_heading": (dict(rot=lambda dx, dz: BW.ww_walker_rotation(BW.ww_walker_yaw(dx, dz) - 180.0)), "rot.walker_heading_not_travel"),
    "flags_host_follows": (dict(flags=lambda role, fh: BW.WW_FLAG_FOLLOW if fh else 0), "flags.host_never_follows"),
    "arrival_on_seq_move": (dict(cache=lambda c, v, a, ln, k, t, now: (lambda had, was: (lambda mv: (c.__setitem__("arrival_tick", was)
                                                                                                    if not mv and had else None, mv)[1])(
        BW.ww_world_cache_step(c, v, a, ln, k, t, now)))(c["has"], c["arrival_tick"])), "cache.resend_moves_arrival_not_seq"),
    "valid_cliff_resets": (dict(cache=lambda c, v, a, ln, k, t, now: BW.ww_world_cache_step(c, v, a, ln, k, t, now) if v
                                else (c.update(BW.ww_world_cache()), False)[1]), "cache.valid_cliff_holds_both_clocks"),
    "world_any_place": (dict(cache=lambda c, v, a, ln, k, t, now: (lambda mv: (c.update(world_set=True, world=t, world_tick=now)
                                                                               if mv else None, mv)[1])(
        BW.ww_world_cache_step(c, v, a, ln, k, t, now))), "cache.world_sample_kept_through_place3"),
    "capless_keeps_seq": (dict(cache=lambda c, v, a, ln, k, t, now: (lambda had: (lambda mv: (c.__setitem__("seq_set", had)
                                                                                              if v and not t["has"] else None, mv)[1])(
        BW.ww_world_cache_step(c, v, a, ln, k, t, now)))(c["seq_set"])), "cache.capless_has_no_seq"),
    "bench_gap_stops_building": (dict(deliver=lambda fz, gp: (not gp, not fz and not gp)), "bench.gap_keeps_building"),
    "bench_freeze_stops_arrivals": (dict(deliver=lambda fz, gp: (not gp and not fz, not fz)), "bench.freeze_resends"),
}


def test_every_twin_row_holds_on_the_real_rules():
    r = _rules()
    bad = [name for name, row in ROWS.items() if not row(r)]
    assert bad == [], bad


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_each_twin_mutant_fails_its_own_row(name):
    swap, row = MUTANTS[name]
    assert row in ROWS, row
    r = _rules(**swap)
    assert not ROWS[row](r), f"mutant {name} passed its own row {row}"


# ================================================================================================ A4's TWINS (the W2 reconcile: A4 FINAL)
def _a4_rules(**swap):
    """A4's twin rule set (the engine proof's A4 delegates; a mutant swaps exactly one)."""
    r = SimpleNamespace(anim=BW.ww_world_anim_rule, dt=lambda u, s: BW.ww_ease_dt_rule(u), ground=BW.ww_ground_of,
                        mismatch=BW.ww_ground_mismatch_rule, water=BW.ww_water_rule, shadow=BW.ww_shadow_rule,
                        lever=BW.ww_place_render_lever_step, place=BW.ww_ghost_place_step, dot=BW.ww_dot_source_rule,
                        yaw=BW.ww_yaw_of_rotation, dot_rot=BW.ww_dot_rotation_of_yaw)
    for k, v in swap.items():
        assert hasattr(r, k), k
        setattr(r, k, v)
    return r


def _shift_slots(sx, sz):
    """The proof's ShiftSlots: block (cx, cz) at slot ((cx + sx) % 24, (cz + sz) % 20) -- MY walker wrapped sx / sz blocks."""
    return lambda cx, cz: (True, (int(cx) + sx) % BW.WW_BLOCKS_X, (int(cz) + sz) % BW.WW_BLOCKS_Z)


def _render_lever_lags(r) -> bool:
    """place.render_lever_lags_at_my_wrap: a standing ghost, my walker wraps one block -> `place render` lags the 64 u, then settles."""
    q, s0, s1 = (0.0, 0.0, 0.0, 1.0), _shift_slots(0, 0), _shift_slots(1, 0)
    m = BW.ww_ghost_motion()
    BW.ww_ghost_place_step(m, 9011, 68.0, -10.0, -444.0, q, 1 / 60, s0)
    BW.ww_ghost_place_step(m, 9011, 68.0, -10.0, -444.0, q, 1 / 60, s0)
    had, prx, prz = m["placed"], m["rx"], m["rz"]
    snap = BW.ww_ghost_place_step(m, 9011, 68.0, -10.0, -444.0, q, 1 / 60, s1)
    r.lever(m, had, prx, prz, snap, 1 / 60)
    lagged = 68.5 < m["rx"] < 131.5 and m["rz"] == -444.0
    for _ in range(240):
        had, prx, prz = m["placed"], m["rx"], m["rz"]
        snap = BW.ww_ghost_place_step(m, 9011, 68.0, -10.0, -444.0, q, 1 / 60, s1)
        r.lever(m, had, prx, prz, snap, 1 / 60)
    return lagged and abs(m["rx"] - 132.0) < 0.01


def _rotation_eases(r) -> bool:
    """place.rotation_eases_not_snaps: one render frame turns the heading part of the way; it settles on the target."""
    s0 = _shift_slots(0, 0)
    m = BW.ww_ghost_motion()
    r.place(m, 9011, 100.0, -10.0, -500.0, (0.0, 0.0, 0.0, 1.0), 1 / 60, s0)
    r.place(m, 9011, 100.0, -10.0, -500.0, BW.ww_walker_rotation(90.0), 1 / 60, s0)
    y1 = BW.ww_yaw_of_rotation(m["rot"])
    for _ in range(240):
        r.place(m, 9011, 100.0, -10.0, -500.0, BW.ww_walker_rotation(90.0), 1 / 60, s0)
    return 1.0 < y1 < 89.0 and abs(BW.ww_yaw_of_rotation(m["rot"]) - 90.0) < 0.5


def _qmul(a, b):
    """The proof's QMul (a * b: b first), (x, y, z, w)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _tilted_90():
    """Euler(10, 90, 5) by hand (Unity's Y * X * Z): a walker heading 90 with its body pitched and rolled."""
    import math
    p, rl, yw = math.radians(5.0), math.radians(2.5), math.radians(45.0)
    return _qmul(_qmul((0.0, math.sin(yw), 0.0, math.cos(yw)), (math.sin(p), 0.0, 0.0, math.cos(p))), (0.0, 0.0, math.sin(rl), math.cos(rl)))


def _dot_fixture(**kw):
    """The proof's SampleFixture(PlaceWorld, StControl | StVisible): a host's live world sample, caps b0 (``kw`` overrides a field)."""
    t = _sample(BW.WW_PLACE_WORLD, BW.WW_ST_CONTROL | BW.WW_ST_VISIBLE)
    t.update(kw)
    return t


_MV, _ST, _HD = BW.WW_STALL_MOVE, BW.WW_STALL_STAND, BW.WW_STALL_HIDE
_FOL, _FREE, _STD, _KEEP = BW.WW_ANIM_FOLLOW, BW.WW_ANIM_FREE, BW.WW_ANIM_STAND, BW.WW_ANIM_KEEP
_NAN = float("nan")

#: the engine proof's A4Rows, row for row (NetSyncWorldWalk.A4Rows: the same names, inputs and verdicts)
A4_ROWS = {
    "anim.moving_follows": lambda r: r.anim(_MV, True, 8, True) == _FOL,
    "anim.unusable_frame_free_runs": lambda r: all(r.anim(_MV, True, n, True) == _FREE for n in (0, 1, 255))
    and all(r.anim(_MV, True, n, True) == _FOL for n in (2, 254)),
    "anim.stall_400ms_stands": lambda r: r.anim(_ST, True, 8, True) == _STD and r.anim(_ST, False, 8, True) == _STD,
    "anim.stand_missing_keeps": lambda r: r.anim(_ST, True, 8, False) == _KEEP,
    "anim.missing_clip_keeps_current": lambda r: r.anim(_MV, False, 8, True) == _KEEP and r.anim(_MV, False, 0, True) == _KEEP,
    "anim.hidden_keeps": lambda r: r.anim(_HD, True, 8, True) == _KEEP,
    "anim.names_and_stand_clip": lambda r: [BW.ww_anim_name(a) for a in (_FOL, _STD, _KEEP, 9)] == ["follow", "stand", "keep", None]
    and BW.ww_stand_clip_of("GEO_SUB_W0_001") == "ANH_SUB_W0_001_STAND" and BW.ww_stand_clip_of("GEO_SUB_W0_002") == "ANH_SUB_W0_002_STAND"
    and BW.ww_stand_clip_of("GEO_SUB_W0_011") == "ANH_SUB_W0_011_STAND" and BW.ww_stand_clip_of(None) is None
    and BW.ww_stand_clip_of("GEO_") is None and BW.ww_stand_clip_of("ANH_SUB_W0_001") is None,
    "clock.unscaled_eases_a_paused_game": lambda r: abs(r.dt(1 / 60, 0.0) - 1 / 60) < 1e-7 and r.dt(0.02, 0.01) == 0.02
    and r.dt(-1.0, 0.5) == 0.0 and r.dt(_NAN, 0.5) == 0.0,
    "ground.hit_is_its_height": lambda r: r.ground(1000, 0x0123, 12.5, 13.0) == (12.5, False),
    "ground.remap_keeps_body_height": lambda r: all(r.ground(1000, g, 3.0, 13.0) == (13.0, True)
                                                    for g in (BW.WW_GROUND_ID_FEE, BW.WW_GROUND_ID_1BEE, BW.WW_GROUND_ID_2CEE)),
    "ground.miss_is_no_ground": lambda r: (lambda g: g[0] != g[0] and not g[1])(r.ground(BW.WW_GROUND_MISS_PNO, 0, 0.0, 13.0)),
    "ground.mismatch_beyond_tolerance": lambda r: r.mismatch(15.0, 13.0, False, False) and r.mismatch(11.9, 13.0, False, False)
    and not r.mismatch(13.9, 13.0, False, False) and not r.mismatch(13.0, 13.0, False, False),
    "ground.water_never_mismatches": lambda r: not r.mismatch(11.0, 13.0, True, False),
    "ground.remap_or_miss_never_mismatches": lambda r: not r.mismatch(20.0, 13.0, False, True) and not r.mismatch(20.0, _NAN, False, False),
    "ground.water_cut": lambda r: r.water(-0.02) and not r.water(-0.01) and not r.water(0.0) and not r.water(BW.WW_WATER_SLICE_U),
    "shadow.walker_on_ground": lambda r: (lambda s: abs(s[0] - 0.87890625) < 1e-6 and abs(s[1] - 0.65) < 1e-6)(r.shadow(10.0, 10.0, 4096)),
    "shadow.fog_amp_1296": lambda r: (lambda s: abs(s[0] - 0.87890625) < 1e-6 and abs(s[1] - 0.89) < 1e-6)(r.shadow(10.0, 10.0, 1296)),
    "shadow.wading_shrinks": lambda r: (lambda s: abs(s[0] - 0.8056640625) < 1e-6 and abs(s[1] - 0.66) < 1e-6)(r.shadow(10.0, 9.5, 4096)),
    "place.render_lever_lags_at_my_wrap": _render_lever_lags,
    "place.rotation_eases_not_snaps": _rotation_eases,
    "dot_src.trailer_when_caps_and_block": lambda r: r.dot(False, _dot_fixture()),
    "dot_src.lever_section0": lambda r: not r.dot(True, _dot_fixture()),
    "dot_src.capless_section0": lambda r: not r.dot(False, _dot_fixture(caps=0)) and not r.dot(False, BW.ww_trailer()),
    "dot_src.place3_or_diorama_section0": lambda r: not r.dot(False, _dot_fixture(place=BW.WW_PLACE_WORLD_LOADING))
    and not r.dot(False, _dot_fixture(place=BW.WW_PLACE_DIORAMA)) and not r.dot(False, _dot_fixture(world=0)),
    "dot_src.unusable_pose_section0": lambda r: not r.dot(False, _dot_fixture(x=_NAN)) and not r.dot(False, _dot_fixture(x=2000.0))
    and not r.dot(False, _dot_fixture(rot=(0.0, 0.0, 0.0, 0.0))),
    "dot_src.yaw_round_trip": lambda r: all(abs(r.yaw(BW.ww_walker_rotation(y)) - y) < 0.01 for y in (0.0, 45.0, 90.0, 180.0, 270.0, 359.0))
    and r.yaw((0.0, 0.0, 0.0, 0.0)) != r.yaw((0.0, 0.0, 0.0, 0.0)),
    "dot_src.yaw_ignores_body_tilt": lambda r: abs(r.yaw(_tilted_90()) - 90.0) < 0.01,
    "dot_src.rotation_is_the_pointers": lambda r: r.dot_rot(0.0) == -90.0 and r.dot_rot(90.0) == -180.0
    and abs(r.dot_rot(64 * 360.0 / 256.0) - BW.dot_rotation(64)) < 1e-4 and abs(r.dot_rot(199 * 360.0 / 256.0) - BW.dot_rotation(199)) < 1e-4,
}


def _rot_snap_place(m, w, tx, ty, tz, q, dt, sl):
    snap = BW.ww_ghost_place_step(m, w, tx, ty, tz, q, dt, sl)
    if BW.ww_rot_usable(q):
        m["rot"] = tuple(q)
    return snap


def _ground_miss_is_zero(pn, gid, ry, wy):
    g, rm = BW.ww_ground_of(pn, gid, ry, wy)
    return (ry if g != g else g), rm


def _yaw_from_w_only(q):
    import math
    return math.degrees(2.0 * math.acos(min(1.0, abs(float(q[3]))))) if BW.ww_rot_usable(q) else _NAN


#: the engine's 14 A4 mutants (NetSyncWorldWalk.Mutant: the same names), each failing ITS OWN row (MutantRows)
A4_MUTANTS = {
    "stand_frozen_follow": (dict(anim=lambda st, on, fn, so: BW.ww_world_anim_rule(_MV if st == _ST else st, on, fn, so)),
                            "anim.stall_400ms_stands"),
    "anim_miss_fallback": (dict(anim=lambda st, on, fn, so: _STD if st == _MV and not on else BW.ww_world_anim_rule(st, on, fn, so)),
                           "anim.missing_clip_keeps_current"),
    "ease_on_scaled_time": (dict(dt=lambda u, s: BW.ww_ease_dt_rule(s)), "clock.unscaled_eases_a_paused_game"),
    "rot_snap": (dict(place=_rot_snap_place), "place.rotation_eases_not_snaps"),
    "ground_no_remap": (dict(ground=lambda pn, gid, ry, wy: ((_NAN if pn == BW.WW_GROUND_MISS_PNO else float(ry)), False)),
                        "ground.remap_keeps_body_height"),
    "ground_miss_is_zero": (dict(ground=_ground_miss_is_zero), "ground.miss_is_no_ground"),
    "mismatch_in_water": (dict(mismatch=lambda wy, gy, wt, rm: BW.ww_ground_mismatch_rule(wy, gy, False, rm)), "ground.water_never_mismatches"),
    "shadow_vehicle_size": (dict(shadow=lambda gy, by, fa: (lambda s: (s[0] * 10.0 / BW.WW_SHADOW_SIZE, s[1]))(BW.ww_shadow_rule(gy, by, fa))),
                            "shadow.walker_on_ground"),
    "shadow_fog_blind": (dict(shadow=lambda gy, by, fa: BW.ww_shadow_rule(gy, by, 4096)), "shadow.fog_amp_1296"),
    "render_lever_inert": (dict(lever=lambda m, hp, px, pz, sn, dt: None), "place.render_lever_lags_at_my_wrap"),
    "dot_src_lever_blind": (dict(dot=lambda lv, h: BW.ww_dot_source_rule(False, h)), "dot_src.lever_section0"),
    "dot_src_any_place": (dict(dot=lambda lv, h: bool(not lv and h["has"] and h["caps"] & BW.WW_CAP_WORLD_POSE
                                                      and BW.ww_pose_in_torus(h["x"], h["z"]) and BW.ww_rot_usable(h["rot"]))),
                          "dot_src.place3_or_diorama_section0"),
    "yaw_from_w_only": (dict(yaw=_yaw_from_w_only), "dot_src.yaw_round_trip"),
    "dot_rot_sign": (dict(dot_rot=lambda yd: float(yd) - 90.0), "dot_src.rotation_is_the_pointers"),
}


def test_every_a4_twin_row_holds_on_the_real_rules():
    r = _a4_rules()
    bad = [name for name, row in A4_ROWS.items() if not row(r)]
    assert bad == [], bad


@pytest.mark.parametrize("name", sorted(A4_MUTANTS))
def test_each_a4_twin_mutant_fails_its_own_row(name):
    swap, row = A4_MUTANTS[name]
    assert row in A4_ROWS, row
    assert not A4_ROWS[row](_a4_rules(**swap)), f"mutant {name} passed its own row {row}"


def test_the_lane_and_line_texts_and_names_read_their_engine_words():
    """The words twins (the A1 and A3 log texts; the pin below reads them off the engine)."""
    assert BW.ww_lane_line_text(BW.WW_LINE_HANG_CUT, 2500) == ("lane hang over: the partner's frames STOPPED after 2500 ms of repeats (not an "
                                                              "update -- a gap follows)")
    assert BW.ww_lane_line_text(BW.WW_LINE_NONE, 1) is None and BW.ww_lane_line_name(BW.WW_LINE_HANG_CUT) == "hang_cut"
    assert BW.ww_host_log_text(BW.WW_HOST_LINE_LOADING, True, BW.WW_HOST_LINE_SCENE, True, 1200) == (
        "host world: the partner's loading state ended after 1200 ms; the partner is scene (\"Your partner's game is in a world-map scene.\")")
    assert BW.ww_host_log_text(0, False, BW.WW_HOST_LINE_LOST, False, 0) == "host world: the partner is lost (counted only)"
    assert BW.ww_host_log_text(0, False, 0, False, 0) is None
    assert [BW.ww_world_line_name(n) for n in range(6)] == [None, "following", "loading", "scene", "lost", "mismatch"]
    assert BW.ww_world_line_text(BW.WW_WORLD_LINE_MISMATCH) == BW.WORDS_WIRE_MISMATCH == BW.WORDS_WW_WIRE_MISMATCH
    assert [BW.ww_world_walk_line_text(BW.ww_world_line_ovl(n)) for n in (5, 4)] == [
        "FF9 co-op: " + BW.WORDS_WW_WIRE_MISMATCH, "FF9 co-op: " + BW.WORDS_WW_LOST_CONTACT]
    assert [BW.ww_overlay_name(s) for s in range(18, 23)] == list(BW.OVERLAY_NAMES_S166) and BW.ww_overlay_name(17) == BW.OVERLAY_NAMES[17]
    assert BW.log_ww_host_path(2, 24.0, False).startswith("[NetSync] harness: worldwalk host path 2 point(s) at 24 u/s -- ")
    assert "at 0 u/s" in BW.log_ww_host_path(1, 0.0, False) and "at 12.5 u/s, looping" in BW.log_ww_host_path(3, 12.5, True)
    assert BW.ww_parse_int("0x84", 0, 255) == 0x84 and BW.ww_parse_int("256", 0, 255) is None and BW.ww_parse_int("x", 0, 9) is None


def test_the_ring_model_is_a_torus_and_its_inverse_is_the_forward_maps():
    """The stand-in's WMWorld (not an engine twin): every canonical point maps into the render torus and back, for my walker anywhere."""
    for ox, oz in ((0.0, 0.0), (1530.0, -1270.0), (700.0, -640.0), (5.0, -1275.0)):
        slots = BW.ww_ring_slots(ox, oz)
        for x, z in ((0.0, 0.0), (1535.9, -1279.9), (68.0, -444.0), (1197.37, -796.7), (31.99, -32.01)):
            ok, rx, rz = BW.ww_render_of(x, z, slots)
            assert ok and 0.0 <= rx < 1536.0 and -1280.0 < rz <= 0.0, (ox, oz, x, z, rx, rz)
            ix, iz = BW.ww_ring_inverse(rx, rz, ox, oz)
            assert BW.ww_torus_distance(ix, iz, x, z) < 1e-6, (ox, oz, x, z, ix, iz)


def test_the_proof_tallies_derive_from_a_source_and_never_from_a_pin():
    """BW.world_walk_proof_counts over a synthetic source: every row( call, the K1 loop per world, every mutant name -- comments and literals
    ignored; no proof -> None."""
    src = '''
        private static Int32 Rows(Rules r, List<String> fails)
        {
            row(a, "x");   // row(ignored)
            row(b, "row(not a call)");
            Int32[] k1 = { 11, 7, 14 };
            for (Int32 i = 0; i < k1.Length; i++)
            {
                row(c, "t1");
                row(d, "t2");
            }
            return n;
        }
        private static void ARows(Rules r, Action<Boolean, String> row) { row(e, "y"); }
        private static Rules Mutant(String name) { }
        private static readonly String[] MutantNames = { "m1", "m2", // "m3"
                                                         "m4" };'''
    assert BW.world_walk_proof_counts(src) == (2 + 2 * 3 + 1, 3)
    assert BW.world_walk_proof_counts("no proof here") is None
    assert FG.world_walk_proof_tallies(FG.FAKE_WORLD_WALK_A0B_BUILD, src) == (FG.FAKE_WORLD_WALK_SELFTEST_ROWS, FG.FAKE_WORLD_WALK_MUTANTS)
    assert FG.world_walk_proof_tallies(FG.FAKE_WORLD_WALK_PIECES, src) == (9, 3)


# ================================================================================================ THE CODEC: battlewire's vocabulary is coop_peer's
def test_battlewires_trailer_vocabulary_is_coop_peers_bytes():
    assert (BW.WW_TRAILER_AT, BW.WW_TRAILER_FMT, BW.WW_TRAILER_LEN, BW.WW_POS_LEN_WORLD) == (CP.TRAILER_AT, CP.TRAILER_FMT, CP.TRAILER_LEN,
                                                                                            CP.POS_V15_LEN) == (39, 1, 55, 94)
    assert (BW.WW_CAP_WORLD_POSE, BW.WW_CAP_WORLD_FP, BW.WW_CAP_COMMS, BW.WW_CAP_GUEST_MENU, BW.WW_CAP_CMD_V2) == (
        CP.CAP_WORLD_POSE, CP.CAP_WORLD_FP, CP.CAP_COMMS, CP.CAP_GUEST_MENU, CP.CAP_CMD_V2)
    assert (BW.WW_PLACE_NONE, BW.WW_PLACE_WORLD, BW.WW_PLACE_DIORAMA) == (CP.PLACE_NONE, CP.PLACE_WORLD, CP.PLACE_DIORAMA)
    assert (BW.WW_ST_FROZEN, BW.WW_ST_SCENE, BW.WW_ST_VISIBLE, BW.WW_FLAG_FOLLOW) == (CP.ST_FROZEN, CP.ST_SCENE, CP.ST_VISIBLE, CP.FLAG_FOLLOW)
    assert BW.WW_KIND_NAMES == BW.WIRE_PEER_KINDS and BW.WW_MAGIC == CP.WIRE_MAGIC
    t = BW.ww_trailer(fmt=1, caps=1, seq=0x1234, ms=0xA1B2C3D4, place=4, state=0x85, why=0x3D, world=9011, x=68.5, y=-12.25, z=-444.75,
                      rot=(0.0, 0.5, 0.0, 0.8660254), model=310, anim=0x1ABC, anim_frame=7, frame_n=24, digest=0xDEADBEEF, world_tps=28,
                      flags=1)
    raw = CP.build_world_trailer(**BW.ww_write_fields(t, True))
    back = BW.ww_trailer_of(CP.parse_world_trailer(CP.build_pos_payload(0, anim_frame=0, frame_n=0) + raw))
    assert back["has"] and all(back[k] == pytest.approx(t[k]) if isinstance(t[k], float) else back[k] == t[k]
                               for k in t if k not in ("has", "rot")) and BW.ww_block_valid(back)
    zeroed = BW.ww_trailer_of(CP.parse_world_trailer(CP.build_pos_payload(0, anim_frame=0, frame_n=0)
                                                     + CP.build_world_trailer(**BW.ww_write_fields(dict(t, place=3), True))))
    assert zeroed["world"] == 0 and zeroed["x"] == 0.0 and zeroed["model"] == 0 and zeroed["place"] == 3 and not BW.ww_block_valid(zeroed)
    nowalker = BW.ww_trailer_of(CP.parse_world_trailer(CP.build_pos_payload(0, anim_frame=0, frame_n=0)
                                                       + CP.build_world_trailer(**BW.ww_write_fields(t, False))))
    assert nowalker["world"] == 0 and not BW.ww_block_valid(nowalker) and nowalker["seq"] == 0x1234
    assert BW.ww_write_fields(dict(t, fmt=0), True) is None                          # pose off: CP.TFMT0_TRAILER, a capless peer
    assert not BW.ww_trailer_of(CP.parse_world_trailer(CP.build_pos_payload(0, anim_frame=0, frame_n=0) + CP.TFMT0_TRAILER))["has"]
    assert BW.ww_quat_yaw(BW.ww_walker_rotation(270.0)) == pytest.approx(270.0) == CP.quat_yaw(BW.ww_walker_rotation(270.0))


# ================================================================================================ THE ENGINE PINS (by stage)
def _s166_patch_live() -> bool:
    return any(nm.startswith("s166-") and nm not in msr.DEAD for nm in msr.stack())


def _engine_text(file_name: str) -> str:
    """The s166 post-image of ``file_name`` BY STAGE: the s166 patch on the stack (a file the stack creates reads whole), else a clone named
    by FF9_S166_CLONE carrying the s166 tag; else SKIP (the deployed A0b stage)."""
    if _s166_patch_live():
        try:
            return "\n".join(stack_file(file_name))
        except AssertionError:
            out = []
            for nm in msr.stack():
                if nm.startswith("s166-") and nm not in msr.DEAD:
                    for path, sec in msr.sections((msr.PATCHES / nm).read_bytes()):
                        if path and path.replace("\\", "/").rsplit("/", 1)[-1] == file_name:
                            out += [ln[1:] for ln in sec.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
                                    if ln[:1] in (" ", "+") and not ln.startswith("+++")]
            return "\n".join(out)
    raw = os.environ.get(S166_CLONE_ENV, "").strip()
    root = pathlib.Path(raw) if raw else None
    if root is not None and (root / "Memoria" / "Netsync").is_dir():
        hits = [p for p in root.rglob(file_name) if p.is_file()]
        if hits:
            text = hits[0].read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
            if S166_TAG in text or file_name == "HarnessAgent.cs":
                return text
    pytest.skip("the s166 patch is not on this branch's stack (the deployed A0b stage) -- set "
                f"{S166_CLONE_ENV}=<the clone's Assembly-CSharp> to pin a clone that carries the tag")


def _ww_a1() -> str:
    text = _engine_text("NetSyncWorldWalk.cs")
    if "LaneGapStep" not in text:
        pytest.skip("this s166 source carries A0 / A0b alone (no A1 pure core yet)")
    return text


def _ww_a3() -> str:
    text = _ww_a1()
    if "WorldCacheStep" not in text:
        pytest.skip("this s166 source carries A1 / A2 alone (no A3 yet)")
    return text


def _client_a3() -> str:
    text = _engine_text("NetSyncClient.cs")
    if "WorldLaneStep" not in text:
        pytest.skip("this s166 NetSyncClient carries no A3 (the sender, the cache, the lines)")
    return text


def _consts(text: str, names: str) -> dict:
    return {m.group(1): int(m.group(2), 0) for m in re.finditer(r"\b(" + names + r")\s*=\s*(0x[0-9A-Fa-f]+|-?\d+)\b(?![.\w])", text)}


def _floats(text: str, names: str) -> dict:
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"\b(" + names + r")\s*=\s*(-?\d+(?:\.\d+)?)f\b", text)}


def _body(text: str, signature: str) -> str:
    """A method's body (from its signature to the closing brace at its indent)."""
    i = text.find(signature)
    assert i >= 0, signature
    j = text.find("\n        }", i)
    return text[i:j]


def _names(text: str, array: str) -> list:
    m = re.search(re.escape(array) + r"\s*=\s*\{(.*?)\};", text, re.S)
    assert m, array
    return [None if tok.strip() == "null" else tok.strip().strip('"') for tok in m.group(1).replace("\n", " ").split(",") if tok.strip()]


def test_s166a_the_twins_constants_are_the_engines():
    text = _ww_a1()
    assert _consts(text, r"LaneGapMs|LaneCountMs|LaneLinePairs") == {"LaneGapMs": BW.WW_LANE_GAP_MS, "LaneCountMs": BW.WW_LANE_COUNT_MS,
                                                                       "LaneLinePairs": BW.WW_LANE_LINE_PAIRS}
    assert _consts(text, r"LaneOk|LaneGap|LaneHang|LaneHangLoading") == {"LaneOk": 0, "LaneGap": 1, "LaneHang": 2, "LaneHangLoading": 3}
    assert _consts(text, r"Budget(?:Say|Over|Silent)") == {"BudgetSay": BW.WW_BUDGET_SAY, "BudgetOver": BW.WW_BUDGET_OVER,
                                                           "BudgetSilent": BW.WW_BUDGET_SILENT}
    lines = _consts(text, r"Line(?:None|GapStart|GapEnd|HangStart|HangEnd|LoadStart|LoadEnd|StallBudget|LoadBudget|HangCut)")
    assert lines == {"LineNone": BW.WW_LINE_NONE, "LineGapStart": BW.WW_LINE_GAP_START, "LineGapEnd": BW.WW_LINE_GAP_END,
                     "LineHangStart": BW.WW_LINE_HANG_START, "LineHangEnd": BW.WW_LINE_HANG_END, "LineLoadStart": BW.WW_LINE_LOAD_START,
                     "LineLoadEnd": BW.WW_LINE_LOAD_END, "LineStallBudget": BW.WW_LINE_STALL_BUDGET,
                     "LineLoadBudget": BW.WW_LINE_LOAD_BUDGET, "LineHangCut": BW.WW_LINE_HANG_CUT}
    assert BW.WW_LINE_HANG_CUT == 9                                # the review's F1 line, after the eight A1 lines
    assert _consts(text, r"HostLine(?:None|Following|Loading|Scene|Lost)|HostLostMs") == {
        "HostLineNone": 0, "HostLineFollowing": 1, "HostLineLoading": 2, "HostLineScene": 3, "HostLineLost": 4,
        "HostLostMs": BW.WW_HOST_LOST_MS}
    assert _consts(text, r"WorldWalk(?:Lo|Mid|Hi)|GhostStandMs|GhostGraceMs|GhostWhyMax") == {
        "WorldWalkLo": 9002, "WorldWalkMid": 9010, "WorldWalkHi": 9011, "GhostStandMs": BW.WW_GHOST_STAND_MS,
        "GhostGraceMs": BW.WW_GHOST_GRACE_MS, "GhostWhyMax": len(BW.WW_GHOST_NAMES) - 1}
    assert tuple(BW.WALK_WORLDS) == (9002, 9010, 9011)
    ghost = _consts(text, r"Ghost(?:Show|Role|NotLive|EventWorld|WalkSet|NoRecord|PeerCaps|PeerBlock|PoseRange|OtherWorld|Band|Riding|"
                          r"PeerScene|Stale|Lever)")
    assert ghost == {"Ghost" + n: i for i, n in enumerate(("Show", "Role", "NotLive", "EventWorld", "WalkSet", "NoRecord", "PeerCaps",
                                                          "PeerBlock", "PoseRange", "OtherWorld", "Band", "Riding", "PeerScene", "Stale",
                                                          "Lever"))}
    assert _consts(text, r"Stall(?:Move|Stand|Hide)") == {"StallMove": 0, "StallStand": 1, "StallHide": 2}
    assert _consts(text, r"BlocksX|BlocksZ") == {"BlocksX": BW.WW_BLOCKS_X, "BlocksZ": BW.WW_BLOCKS_Z}
    assert _floats(text, r"BlockSize|LerpRate|SnapJumpU") == {"BlockSize": BW.WW_BLOCK_SIZE, "LerpRate": BW.WW_LERP_RATE,
                                                              "SnapJumpU": BW.WW_SNAP_JUMP_U}
    assert _consts(text, r"Geo(?:Mog|Dagger|Zidane)|Dress(?:None|Moogle|Garnet)|WalkerRatio|MogRatio|SceneHoldMs") == {
        "GeoMog": BW.WW_GEO_MOG, "GeoDagger": BW.WW_GEO_DAGGER, "GeoZidane": BW.WW_GEO_ZIDANE, "DressNone": BW.WW_DRESS_NONE,
        "DressMoogle": BW.WW_DRESS_MOOGLE, "DressGarnet": BW.WW_DRESS_GARNET, "WalkerRatio": BW.WW_WALKER_RATIO,
        "MogRatio": BW.WW_MOG_RATIO, "SceneHoldMs": BW.WW_SCENE_HOLD_MS}
    assert _consts(text, r"Wire(?:Mine|Foreign|Other)|WireMismatchHoldMs|RedialBookMax|WhyRule(?:WorldOut|Walk|Ghost)") == {
        "WireMine": BW.WW_WIRE_MINE, "WireForeign": BW.WW_WIRE_FOREIGN, "WireOther": BW.WW_WIRE_OTHER,
        "WireMismatchHoldMs": BW.WW_WIRE_MISMATCH_HOLD_MS, "RedialBookMax": BW.WW_REDIAL_BOOK_MAX,
        "WhyRuleWorldOut": BW.WW_WHY_RULE_WORLD_OUT, "WhyRuleWalk": BW.WW_WHY_RULE_WALK, "WhyRuleGhost": BW.WW_WHY_RULE_GHOST}
    assert _consts(text, r"Kind(?:Absent|Tfmt0|Short|Fmt1)") == {"KindAbsent": 0, "KindTfmt0": 1, "KindShort": 2, "KindFmt1": 3}
    assert _names(text, "LaneKindNames") == list(BW.WW_LANE_KIND_NAMES)
    assert _names(text, "HostLineNames") == list(BW.WW_HOST_LINE_NAMES)
    assert _names(text, "GhostNames") == list(BW.WW_GHOST_NAMES)
    assert _names(text, "StallNames") == list(BW.WW_STALL_NAMES)
    assert _names(text, "PlaceNames") == list(BW.WW_PLACE_NAMES) and _names(text, "KindNames") == list(BW.WW_KIND_NAMES)
    for name, words in (("LineWireMismatch", BW.WORDS_WW_WIRE_MISMATCH), ("LineLostContact", BW.WORDS_WW_LOST_CONTACT),
                        ("LineHostFollowing", BW.WORDS_WW_HOST_FOLLOWING), ("LineHostLoading", BW.WORDS_WW_HOST_LOADING),
                        ("LineHostScene", BW.WORDS_WW_HOST_SCENE)):
        assert re.search(rf'{name} = "{re.escape(words)}";', text), name


def test_s166a_the_twins_term_orders_are_the_engines():
    """Each rule's returns in the engine's order (an order drift turns a refusal into another's)."""
    text = _ww_a1()
    assert re.findall(r"return Ghost(\w+);", _body(text, "internal static Int32 GhostRule(GhostFacts f)")) == list(BW.WW_GHOST_RULE_ORDER)
    place = _body(text, "internal static Int32 PlaceRule(")
    assert re.findall(r"if \((\w+)\)\s*return", place) == ["title", "transition", "diorama", "battle", "onWorldNow"]
    assert "return blockReady ? PlaceWorld : PlaceWorldLoading;" in place and "return fieldLive ? PlaceField : PlaceNone;" in place
    host = _body(text, "internal static Int32 HostLineRule(")
    assert [m.lower() for m in re.findall(r"return HostLine(Lost|Following|Loading|Scene);", host)] == list(BW.WW_HOST_LINE_RULE_ORDER)
    assert "if (leverOff || !hostRole || !ownLiveWorld || !linked || !guest.Follows || arrivalAgeMs < 0)" in host
    kind = _body(text, "internal static Int32 LaneGapKind(")
    assert re.findall(r"return (LaneOk|LaneGap)\b", kind) == ["LaneOk", "LaneGap", "LaneOk"]
    assert "lastPlace == PlaceTransition || lastPlace == PlaceWorldLoading ? LaneHangLoading : LaneHang" in kind
    who = _body(text, "internal static Boolean GhostWhoRule(")
    assert re.findall(r'role == "(\w+)"', who) == ["client", "host", "selftest"] and "return linked && peer.Follows;" in who
    stall = _body(text, "internal static Int32 GhostStallRule(")
    assert "if (seqAgeMs < 0 || seqAgeMs >= GhostGraceMs)" in stall and "return seqAgeMs >= GhostStandMs ? StallStand : StallMove;" in stall
    scene = _body(text, "internal static Boolean SceneBitStep(")
    assert "c.Counting = !(ownFullMap || fading || menuHold);" in scene and "return c.AccMs > SceneHoldMs;" in scene
    step = _body(text, "internal static Int32 LaneGapStep(")
    assert "if (was != LaneGap && kind == LaneGap)" in step and "return LineHangCut;" in step
    assert "LineBudgetStep(ref b.LoadPairs, ref b.LoadOver, LaneLinePairs)" in step and "LineBudgetStep(ref b.StallPairs, ref b.StallOver" in step
    assert re.search(r"return snap", _body(text, "internal static Boolean GhostPlaceStep(")) and "RenderOf(m.X, m.Z, slots" in \
        _body(text, "internal static Boolean GhostPlaceStep(")
    assert "return !shown || worldChanged || !(jumpU <= SnapJumpU);" in _body(text, "internal static Boolean GhostSnapRule(")
    assert "Math.Atan2(dx, dz) * 180.0 / Math.PI + 180.0" in _body(text, "internal static Single WalkerYaw(")
    assert "if (f.PeerScKnown && !NetSyncWorldFollow.SameBandRule(f.PeerSc, f.OwnSc))" in _body(text, "internal static Int32 GhostRule(")


def test_s166a_the_lane_texts_are_the_engines():
    text = _ww_a1()
    body = _body(text, "internal static String LaneLineText(")
    cases = dict(re.findall(r"case (Line\w+): return (.+?);", body))
    names = {"LineGapStart": BW.WW_LINE_GAP_START, "LineGapEnd": BW.WW_LINE_GAP_END, "LineHangStart": BW.WW_LINE_HANG_START,
             "LineHangEnd": BW.WW_LINE_HANG_END, "LineLoadStart": BW.WW_LINE_LOAD_START, "LineLoadEnd": BW.WW_LINE_LOAD_END,
             "LineStallBudget": BW.WW_LINE_STALL_BUDGET, "LineLoadBudget": BW.WW_LINE_LOAD_BUDGET, "LineHangCut": BW.WW_LINE_HANG_CUT}
    assert set(cases) == set(names)
    for name, expr in cases.items():
        rendered = "".join(_LIT.findall(expr.replace(" + lenMs + ", '"\u0001"').replace(" + LaneLinePairs + ", '"20"')))
        assert rendered.replace("\u0001", "777") == BW.ww_lane_line_text(names[name], 777), name
    assert BW.ww_wire_break_reason(14, 15) == "".join(_LIT.findall(
        _body(text, "internal static String WireBreakReason(").replace(" + peer + ", '"14"').replace(" + own + ", '"15"')))


def test_s166a_the_a3_rules_and_their_words_are_the_engines():
    text = _ww_a3()
    assert _consts(text, r"HostLinePairs|HostLog(?:None|Edge|Budget)|WorldLineMismatch|BenchStaleMs") == {
        "HostLinePairs": BW.WW_HOST_LINE_PAIRS, "HostLogNone": BW.WW_HOST_LOG_NONE, "HostLogEdge": BW.WW_HOST_LOG_EDGE,
        "HostLogBudget": BW.WW_HOST_LOG_BUDGET, "WorldLineMismatch": BW.WW_WORLD_LINE_MISMATCH, "BenchStaleMs": BW.WW_BENCH_STALE_MS}
    assert _names(text, "LaneLineNames") == list(BW.WW_LANE_LINE_NAMES)
    line = _body(text, "internal static Int32 WorldLineRule(")
    assert re.findall(r"if \((\w+)\)", line) == ["mismatch", "sessionSpeaks"] and "return ghostStale ? HostLineLost : WorldLineNone;" in line
    cache = _body(text, "internal static Boolean WorldCacheStep(")
    order = [s for s in ("if (!valid)", "c.ArrivalTick = arrivalTick;", "if (!t.Has)", "if (c.SeqSet && t.Seq == c.Seq)",
                         "c.SpanMs = c.SeqSet ? MsSpan(t.Ms, c.Ms) : -1;", "if (t.BlockValid)") if s in cache]
    assert len(order) == 6 and [cache.index(s) for s in order] == sorted(cache.index(s) for s in order)
    assert "return followHost && (role == \"client\" || role == \"selftest\") ? FlagFollow : 0;" in _body(
        text, "internal static Int32 TrailerFlagsRule(")
    assert "if ((line == LineHangEnd || line == LineLoadEnd) && senderSpanMs > 0)" in _body(text, "internal static Int32 LaneEndLenRule(")
    assert "rebuild = !frozen;" in _body(text, "internal static Boolean BenchDeliverRule(") and "return !gapOpen;" in _body(
        text, "internal static Boolean BenchDeliverRule(")
    assert "return delivered && ageMs >= 0 && ageMs <= BenchStaleMs;" in _body(text, "internal static Boolean BenchViewValid(")
    rot = _body(text, "internal static Quaternion WalkerRotation(")
    assert "yawDeg * Math.PI / 360.0" in rot and "new Quaternion(0f, (Single)Math.Sin(h), 0f, (Single)Math.Cos(h))" in rot
    hl = _body(text, "internal static String HostLogText(")
    for piece in ('"the partner\'s "', '" state ended after "', '" ms"', '"the partner is "', '" (\\""', '"\\")"', '" (counted only)"',
                  '"host world: "', '"; "'):
        assert piece in hl, piece
    assert '"host world lines: " + HostLinePairs + " on this link -- counted only from here"' in text


def test_s166a_the_clients_a3_lines_ops_and_overlay_are_the_stand_ins():
    """NetSyncClient's A3 words, as the stand-in prints them: the lane line, the reset / lost / fault lines, the verb's usage, clear and
    acks, the bench host's refusals and acks, the overlay states and their words."""
    client = _client_a3()
    lits = "\n".join(ln for ln in client.split("\n") if '"' in ln)
    a4 = "NetSyncWorldGhost." in client                 # [ff9mapkit netsync s166] W2 reconcile: A4 grows the usage and the clear line
    assert f'"{BW.WORLDWALK_USAGE_A4 if a4 else BW.WORLDWALK_USAGE_A3}"' in lits
    for whole in (BW.LOG_WORLDWALK_CLEAR_A4 if a4 else BW.LOG_WORLDWALK_CLEAR_A3, BW.LOG_WORLDWALK_POSE_OFF, BW.LOG_WORLDWALK_POSE_ON, BW.LOG_WORLDWALK_LANEGAP_OFF,
                  BW.LOG_WORLDWALK_LANEGAP_ON, BW.LOG_WORLDWALK_HOSTLINES_OFF, BW.LOG_WORLDWALK_HOSTLINES_ON, BW.WORLDWALK_HOST_REFUSAL,
                  BW.WORLDWALK_HOST_FOLLOW_REFUSAL):
        assert f'"{whole}"' in lits, whole
    for piece in ('"[NetSync] " + _role + " " + NetSyncWorldWalk.LaneLineText(line, len)', '"[NetSync] world lane: the receiver cache resets ("',
                  '") -- its clocks, the lane\'s book and the host\'s lines start over"', '"[NetSync] world lane fault in "',
                  '") -- said once; the lane carries on"', '"[NetSync] world line: lost contact -- the partner\'s game has not updated for "',
                  '" ms (its last frame "', '"[NetSync] world line: lost contact over after "', '" -- the guest\'s place "',
                  '"[NetSync] world line: lost-contact lines: "', '" -- hostgap takes 1-60000 ms"', '" -- host path takes 1 to "',
                  '" points (x z each: x in [0, 1536), z in (-1280, 0]) then <ups> (0-400)"',
                  f'"{BW.ww_bench_needs_host("hostseq")}"', f'"{BW.ww_bench_needs_host("hostgap")}"',
                  '"[NetSync] harness: worldwalk host path "',
                  '" -- the bench host\'s place byte ("', '" -- the bench host\'s state byte"', '"[NetSync] harness: worldwalk hoststate 0x"'):
        assert piece in client, piece
    for why in BW.WW_RESET_WHYS:
        assert f'WorldLaneReset("{why}")' in client, why
    ovl = _consts(client, r"Ovl(?:WireMismatch|WorldLost|HostFollowing|HostLoading|HostScene)")
    assert ovl == {"OvlWireMismatch": BW.OVL_WIRE_MISMATCH, "OvlWorldLost": BW.OVL_WORLD_LOST,
                                                    "OvlHostFollowing": BW.OVL_HOST_FOLLOWING, "OvlHostLoading": BW.OVL_HOST_LOADING,
                                                    "OvlHostScene": BW.OVL_HOST_SCENE}
    names = dict(re.findall(r'case (Ovl(?:WireMismatch|WorldLost|HostFollowing|HostLoading|HostScene)): return "(\w+)";', client))
    assert [names[k] for k in ("OvlWireMismatch", "OvlWorldLost", "OvlHostFollowing", "OvlHostLoading", "OvlHostScene")] == list(
        BW.OVERLAY_NAMES_S166)
    assert 'return w == null ? null : "FF9 co-op: " + w;' in client
    assert "t.State = _wwBenchState >= 0 ? _wwBenchState : (NetSyncWorldWalk.StControl | NetSyncWorldWalk.StVisible);" in client
    assert "t.Rot = NetSyncWorldWalk.WalkerRotation(yaw);" in client and "t.Flags = 0;" in client


def _catch_netsync() -> dict:
    agent = _engine_text("HarnessAgent.cs")
    lines = agent.split("\n")
    catch = [ln for ln in lines if re.search(r'outer\.Append\("\\"netsync\\":\{\\"enabled', ln)]
    head = [ln for ln in lines if 'NetsyncF3Retired = "' in ln]
    tail = [ln for ln in lines if re.search(r'\+ "\\"align_win', ln)]
    if not (catch and head and tail):
        pytest.skip("this s166 HarnessAgent carries no catch literal lines")
    a, b = _LIT.findall(catch[0])
    pinned = "".join(_LIT.findall(head[0]) + _LIT.findall(tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]


def test_s166a_the_catch_line_carries_lane_line_and_guest_at_their_sentinels():
    ns = _catch_netsync()
    world = ns["world"]
    if "lane" not in world:
        pytest.skip("this s166 catch literal carries no A3 keys yet")
    keys = list(world)
    assert keys[keys.index("pairpull"):keys.index("pairpull") + 3] == ["pairpull", "lane", "line"], keys
    assert json.dumps(world["lane"]) == json.dumps(BW.WORLD_LANE_SENTINELS)
    assert json.dumps(world["line"]) == json.dumps(BW.WORLD_LINE_SENTINELS)
    assert json.dumps(ns["host"]) == json.dumps(BW.HOST_SENTINELS_S166)
    assert list(ns)[-1] == "wire_peer"


# ================================================================================================ A4's ENGINE PINS (by stage; the W2 reconcile)
def _ww_a4() -> str:
    text = _ww_a3()
    if "WorldAnimRule" not in text:
        pytest.skip("this s166 source carries no A4 (the world ghost's call-site rules) yet")
    return text


def _ghost_cs() -> str:
    """NetSyncWorldGhost.cs, the file A4 CREATES (the stack builds it whole; a clone reads it whole)."""
    _ww_a4()
    return _engine_text("NetSyncWorldGhost.cs")


def _qnames(text: str, array: str) -> list:
    """An array's string literals in order, its // comments dropped (MutantNames / MutantRows carry a comment per piece)."""
    m = re.search(re.escape(array) + r"\s*=\s*\{(.*?)\};", text, re.S)
    assert m, array
    return re.findall(r'"([^"]*)"', re.sub(r"//[^\n]*", "", m.group(1)))


def test_s166a_the_a4_rules_their_rows_and_mutants_are_the_twins():
    """A4's pure section, read off the source: its constants and names are battlewire's, each rule's body carries the terms the twin
    reads, and the proof's A4 rows and mutants are EXACTLY the twin tables' (a row the engine adds or renames goes red here)."""
    text = _ww_a4()
    assert _consts(text, r"Anim(?:Follow|Free|Stand|Keep)") == {"AnimFollow": BW.WW_ANIM_FOLLOW, "AnimFree": BW.WW_ANIM_FREE,
                                                              "AnimStand": BW.WW_ANIM_STAND, "AnimKeep": BW.WW_ANIM_KEEP}
    assert _names(text, "AnimNames") == list(BW.WW_ANIM_NAMES)
    assert _consts(text, r"GroundId(?:Fee|1Bee|2Cee)|GroundMissPno|ShadowSize|ShadowAmp") == {
        "GroundIdFee": BW.WW_GROUND_ID_FEE, "GroundId1Bee": BW.WW_GROUND_ID_1BEE, "GroundId2Cee": BW.WW_GROUND_ID_2CEE,
        "GroundMissPno": BW.WW_GROUND_MISS_PNO, "ShadowSize": BW.WW_SHADOW_SIZE, "ShadowAmp": BW.WW_SHADOW_AMP}
    assert _floats(text, r"GroundTolU|WaterSliceU|ShadowLiftU") == {"GroundTolU": BW.WW_GROUND_TOL_U, "WaterSliceU": BW.WW_WATER_SLICE_U,
                                                                   "ShadowLiftU": BW.WW_SHADOW_LIFT_U}
    anim = _body(text, "internal static Int32 WorldAnimRule(")
    for piece in ("if (stall == StallStand)", "return standOn ? AnimStand : AnimKeep;", "if (stall != StallMove || !clipOn)",
                  "return NetSyncVisitor.FrameUsable(frameN) ? AnimFollow : AnimFree;"):
        assert piece in anim, piece
    assert "return unscaledDt > 0f ? unscaledDt : 0f;" in _body(text, "internal static Single EaseDtRule(")
    ground = _body(text, "internal static Single GroundOf(")
    assert "id == GroundIdFee || id == GroundId1Bee || id == GroundId2Cee" in ground and "return wireY;" in ground
    assert "return pno == GroundMissPno ? Single.NaN : rayY;" in ground
    assert "return slice < WaterSliceU;" in _body(text, "internal static Boolean WaterRule(")
    mm = _body(text, "internal static Boolean GroundMismatchRule(")
    assert "if (remapped || water || !PoseFinite(wireY, groundY, 0f))" in mm and "return Math.Abs(wireY - groundY) > GroundTolU;" in mm
    sh = _body(text, "internal static void ShadowRule(")
    for piece in ("Int32 num2 = (Int32)(groundY * 256f - bodyY * 256f);", "Int32 num3 = 4096 - num2 / 2;", "Int32 num4 = 4096 - num2 / 4;",
                  "num4 = ShadowSize * num4 >> 11;", "num3 = ShadowAmp * num3 >> 12;", "Int32 num5 = 32768 >> 3;", "num5 *= fogAmp;",
                  "num5 >>= 12;", "if (num5 > 4095)", "num3 *= num5;", "if (num3 > 255)", "scale = num4 * 0.000244140625f * 300f;",
                  "amp = 1f - num3 / 100f;"):
        assert piece in sh, piece
    lever = _body(text, "internal static void PlaceRenderLeverStep(")
    assert "if (!hadPlaced || snap || !m.Placed)" in lever and "m.RX = prevRx + (m.RX - prevRx) * k;" in lever
    assert ("return !leverSection0 && host.BlockValid && NetSyncWorldFollow.PoseInTorus(host.X, host.Z) && RotUsable(host.Rot);"
            in _body(text, "internal static Boolean DotSourceRule("))
    yaw = _body(text, "internal static Single YawOfRotation(")
    assert "Double fx = 2.0 * ((Double)q.x * q.z + (Double)q.w * q.y);" in yaw
    assert "Double fz = 1.0 - 2.0 * ((Double)q.x * q.x + (Double)q.y * q.y);" in yaw
    assert "return -yawDeg - 90f;" in _body(text, "internal static Single DotRotationOfYaw(")
    # the proof's A4 table, row for row, and its mutants beside their rows: EXACTLY the twins'
    a4 = _body(text, "private static void A4Rows(")
    rows = re.findall(r'"((?:anim|clock|ground|shadow|place|dot_src)\.[a-z0-9_.]+)"\);', a4)
    assert rows == list(A4_ROWS), rows
    names, row_of = _qnames(text, "MutantNames"), _qnames(text, "MutantRows")
    assert len(names) == len(row_of), (len(names), len(row_of))
    pairs = dict(zip(names, row_of))
    assert {n: pairs.get(n) for n in A4_MUTANTS} == {n: row for n, (_swap, row) in A4_MUTANTS.items()}
    assert names[-len(A4_MUTANTS):] == list(A4_MUTANTS), names[-len(A4_MUTANTS):]


def test_s166a_the_a4_verb_and_the_ghosts_words_are_the_stand_ins():
    """NetSyncClient's A4 verb (the grown usage and clear lines, the three levers' whole acks) and NetSyncWorldGhost's names and log lines,
    as the stand-in says them."""
    client = _engine_text("NetSyncClient.cs")
    if "NetSyncWorldGhost." not in client:
        pytest.skip("this s166 NetSyncClient carries no A4 (it never calls the world ghost)")
    lits = "\n".join(ln for ln in client.split("\n") if '"' in ln)
    for whole in (BW.WORLDWALK_USAGE_A4, BW.LOG_WORLDWALK_CLEAR_A4) + tuple(BW.WORLDWALK_A4_ACKS.values()):
        assert f'"{whole}"' in lits, whole
    assert BW.WORLDWALK_USAGE_A3 not in lits and BW.LOG_WORLDWALK_CLEAR_A3 + '"' not in lits    # A4 GREW both lines: A3's are gone
    for op, words in BW.A4_CONTRACT["words"].items():
        assert f'case "{op}":' in client and all(f'"{w}"' in client for w in words), op
    assert "|".join(BW.A4_CONTRACT["words"]["ghost"]) in BW.WORLDWALK_USAGE_A4      # the usage names the words in the engine's order
    ghost = _ghost_cs()
    for name, value in (("RootName", BW.WW_GHOST_ROOT_NAME), ("BodyName", BW.WW_GHOST_BODY_NAME),
                        ("ShadowName", BW.WW_GHOST_SHADOW_NAME), ("ShadowPrefab", BW.WW_GHOST_SHADOW_PREFAB)):
        assert re.search(rf'{name}\s*=\s*"{re.escape(value)}"', ghost), name
    for piece in ('"[NetSync] world ghost: minted \'" + RootName + "\' under WorldMapRoot on map "', '" (the "', '"shadow"',
                  '"NO shadow: its prefab is missing"', '"; hidden until wanted)"', f'"{BW.LOG_WW_GHOST_BODY}"', '" (model "',
                  '", ratio "', '", scale "', '"0.######"', '") -- renderers "', '", clips "', '", stand "', '"none"', '", HonoBehaviours "',
                  '", minted in "', '" ms (hidden until wanted)"', f'"{BW.LOG_WW_GHOST_BODY_FAILED}"', f'"{BW.LOG_WW_GHOST_MISMATCH}"',
                  f'"{BW.LOG_WW_GHOST_CLIP_MISS}"', f'"{BW.LOG_WW_GHOST_FAULT_TAIL}"'):
        assert piece in ghost, piece
    stand = BW.ww_stand_clip_of("GEO_SUB_W0_001")
    assert BW.log_ww_ghost_root(9011, True) == (f"[NetSync] world ghost: minted '{BW.WW_GHOST_ROOT_NAME}' under WorldMapRoot on map 9011 "
                                                "(the shadow; hidden until wanted)")
    assert BW.log_ww_ghost_body("GEO_SUB_W0_001", 310, 3, 24, stand, 0, 12) == (
        "[NetSync] world ghost: body GEO_SUB_W0_001 (model 310, ratio 67, scale 0.004089) -- renderers 3, clips 24, stand "
        "ANH_SUB_W0_001_STAND, HonoBehaviours 0, minted in 12 ms (hidden until wanted)")


def test_s166a_the_catch_line_carries_ghost_last_and_the_dots_source_at_their_sentinels():
    ns = _catch_netsync()
    world = ns["world"]
    if BW.A4_CONTRACT["ghost_key"] not in world:
        pytest.skip("this s166 catch literal carries no A4 keys yet")
    assert list(world)[-3:] == ["lane", "line", BW.A4_CONTRACT["ghost_key"]], list(world)
    assert json.dumps(world["ghost"]) == json.dumps(BW.A4_CONTRACT["ghost_sentinels"])
    assert json.dumps(world["dot"]) == json.dumps(BW.WORLD_DOT_SENTINELS_S166)
    assert list(world["dot"])[-5:] == list(BW.A4_CONTRACT["dot_src_keys"])
    assert json.dumps(world) == json.dumps(BW.WORLD_SENTINELS_S166D)            # the whole round-A world block, nested order included


# ================================================================================================ THE STAND-IN (stepped by hand)
def _root():
    t = pathlib.Path(tempfile.mkdtemp(prefix="ww_a_"))
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    return t


def _fake(*, pieces=None, faults=(), follow=True, fps=30.0) -> FakeGame:
    f = FakeGame(_root(), render_fps=fps)
    f.swap_qpc = None                                        # the stopwatch: the stand-in's virtual clock (stamps deterministic)
    f.dir.mkdir(parents=True, exist_ok=True)
    (f.dir / "arm").write_text("", encoding="utf-8")
    f.armed = True
    f.state_every = 1 << 30
    f.wf_follow_host_cfg = bool(follow)
    if pieces is not None:
        f.world_walk_pieces = tuple(pieces)
    f.world_walk_faults = set(faults)
    f.field_id, f.ui_state, f.control = 6603, "FieldHUD", True
    return f


def _step(f, n=1):
    for _ in range(int(n)):
        f._frame_once()


def _secs(f, s):
    _step(f, round(s * f._render_fps))


def _ww(f, *args):
    f._netsync(["worldwalk", *[str(a) for a in args]])


def _bench_on_world(f, x=68.0, z=-444.0, world=9011, bench=True):
    """The forced selftest role (THE FORCED-ROLE PIN: FollowHost from the ini), the field-gate bench, a field, then the world map at (x, z)."""
    f._netsync(["selftest", "1"])
    if bench:
        f._netsync(["bench", "1"])
    _step(f, 4)
    f.enter_world(world, x, z)
    _step(f, 4)


def _doc(f) -> dict:
    return f._netsync_doc()


def _lane(f) -> dict:
    return _doc(f)["world"]["lane"]


def _lines(f, needle) -> list:
    return [ln.split("|M| ", 1)[-1] for ln in (f.game_path / "Memoria.log").read_text(encoding="utf-8").splitlines() if needle in ln]


def test_the_stand_in_publishes_round_as_keys_in_the_agents_order_at_rest():
    f = _fake()
    doc = _doc(f)
    assert list(doc["world"]) == list(FG.NETSYNC_WORLD_KEYS_BY_RUNG["worldwalk"]) == list(BW.WORLD_SENTINELS_S166D)
    assert {k: list(v) for k, v in doc["world"].items() if isinstance(v, dict)} == {
        k: list(v) for k, v in BW.WORLD_SENTINELS_S166D.items()}           # every block's keys, `dot.src` .. `src_face` included (A4)
    assert list(doc["world"])[-3:] == ["lane", "line", BW.A4_CONTRACT["ghost_key"]]
    lane = doc["world"]["lane"]
    assert list(lane) == list(BW.WORLD_LANE_SENTINELS) and list(lane["tx"]) == list(BW.WORLD_LANE_TX_SENTINELS)
    assert list(lane["rx"]) == list(BW.WORLD_LANE_RX_SENTINELS) and list(lane["bench"]) == list(BW.WORLD_LANE_BENCH_SENTINELS)
    # at rest: the sentinels but for the engine's LIVE reads with no instance (the levers' words, the own caps, `open`, the own WorldTPS)
    live = {"lever": "act", "pose": "on", "hostlines": "act", "open": "ok"}
    assert {k: v for k, v in lane.items() if k not in live and k not in ("caps", "world_tps")} == \
        {k: v for k, v in BW.WORLD_LANE_SENTINELS.items() if k not in live and k not in ("caps", "world_tps")}
    assert {k: lane[k] for k in live} == live and lane["caps"] == {"own": 1, "peer": -1, "off": -1}
    assert lane["world_tps"] == {"own": FG.FAKE_WORLD_TPS, "peer": -1}
    assert doc["world"]["line"] == BW.WORLD_LINE_SENTINELS
    assert doc["host"] == BW.HOST_SENTINELS_S166 and list(doc["host"]["world"])[-1] == "guest"
    assert list(doc["world"]["dot"])[-5:] == list(BW.A4_CONTRACT["dot_src_keys"]) and list(doc)[-1] == "wire_peer"   # [s166] W2: A4 final
    assert json.dumps(doc["wire_peer"]) == json.dumps(BW.WIRE_PEER_SENTINELS)
    ghost = doc["world"][BW.A4_CONTRACT["ghost_key"]]
    assert list(ghost) == list(BW.A4_CONTRACT["ghost_sentinels"]) and ghost["shown"] is False and ghost["mints"] == 0


@pytest.mark.parametrize("build, has_lane, has_ghost", [(FG.FAKE_WORLD_WALK_A0B_BUILD, False, False),
                                                        (FG.FAKE_WORLD_WALK_A2_BUILD, False, False),
                                                        (FG.FAKE_WORLD_WALK_A3_BUILD, True, False),
                                                        (FG.FAKE_WORLD_WALK_PIECES, True, True)], ids=["a0b", "a2", "a3", "a4"])
def test_each_build_publishes_exactly_its_pieces_keys(build, has_lane, has_ghost):
    """The calibration builds: A0b (deployed) and A2 (W1) have no lane / line / guest; A3 has them and no ghost and no dot `src` (A4's
    OLD); the newest has both. A build without A3 answers the A0b verb (a `pose` op is its usage line)."""
    f = _fake(pieces=build)
    doc = _doc(f)
    world = doc["world"]
    assert ("lane" in world and "line" in world and "guest" in doc["host"]["world"]) == has_lane
    assert (BW.A4_CONTRACT["ghost_key"] in world and BW.A4_CONTRACT["dot_src_key"] in world["dot"]) == has_ghost
    f._netsync(["selftest", "1"])
    if not has_lane:
        with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_USAGE)):
            _ww(f, "pose", "off")
    else:
        _ww(f, "pose", "off")
        assert _lane(f)["pose"] == "off"


def test_a_tx_the_selftest_slot_carries_my_own_block_on_9011_and_place_3_in_the_load():
    """A-TX: on the forced selftest role, the slot's trailer every Update (before the off-field return): place 4, world 9011, x / z my
    walker's, seq advancing, flags b0 (FollowHost from the ini), Field 0, 94 B fmt1; place 3 through a world load's block window; place 1
    back on a field with w_blockReady STALE-true (never place 4); `pose off`: tfmt 0, still 94 B."""
    f = _fake()
    f.world_block_load_frames = 6
    _bench_on_world(f)
    _step(f, 1)
    assert _lane(f)["tx"]["place"] == BW.WW_PLACE_WORLD_LOADING and _doc(f)["world"]["lane"]["tx"]["x"] is None
    _step(f, 8)
    tx1 = _lane(f)["tx"]
    _step(f, 3)
    tx2 = _lane(f)["tx"]
    assert tx2["place"] == BW.WW_PLACE_WORLD and tx2["world"] == 9011 and tx2["x"] == pytest.approx(68.0) and tx2["z"] == pytest.approx(-444.0)
    assert tx2["seq"] == tx1["seq"] + 3 and tx2["flags"] == BW.WW_FLAG_FOLLOW and tx2["field"] == 0
    assert (tx2["len"], tx2["kind"], tx2["fmt"], tx2["model"]) == (94, "fmt1", 1, BW.WW_GEO_ZIDANE)
    assert tx2["state"] & BW.WW_ST_FROZEN and tx2["state"] & BW.WW_ST_VISIBLE      # THE BENCH TERM HOLDS THE FREEZE on the forced role
    _ww(f, "pose", "off")
    _step(f, 2)
    tx3 = _lane(f)["tx"]
    assert (tx3["fmt"], tx3["kind"], tx3["len"]) == (0, "tfmt0", 94)
    f.ui_state, f.field_id = "FieldHUD", 6603                # a field after the world visit (the stand-in's world -> field)
    _step(f, 2)
    assert f._wwa_block_ready() is True and _lane(f)["tx"]["place"] == BW.WW_PLACE_FIELD and _lane(f)["tx"]["field"] == 6603


def test_a_tx_unfollowed_selftest_sends_no_follow_flag_and_a_capless_build_reads_capless():
    f = _fake(follow=False)
    _bench_on_world(f)
    _step(f, 3)
    assert _lane(f)["tx"]["flags"] == 0


def test_my_own_sync_load_freezes_my_seq_and_the_writer_resends_my_last_slot():
    """A GAME PUBLISHES NOTHING DURING ITS OWN SYNC LOAD: with ``world_sync_load_ms`` a world load stalls the whole Update -- the seq and the
    slot stand (what a stub link re-sends) -- then the builds resume."""
    f = _fake()
    f.world_sync_load_ms = {"world": 1000}
    f._netsync(["selftest", "1"])
    _step(f, 5)
    before = f.world_tx_frame()
    seq0 = _lane(f)["tx"]["seq"]
    f.enter_world(9011, 68.0, -444.0)
    _secs(f, 0.9)
    assert _lane(f)["tx"]["seq"] == seq0 and f.world_tx_frame() == before
    _secs(f, 0.3)
    assert _lane(f)["tx"]["seq"] > seq0 and _lane(f)["tx"]["place"] == BW.WW_PLACE_WORLD


def test_the_bench_host_refuses_off_role_without_followhost_and_on_a_bad_shape():
    f = _fake()
    f._netsync(["selftest", "1"])
    with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_HOST_REFUSAL)):
        _ww(f, "host", "path", "10", "-10", "24")
    f._netsync(["bench", "1"])
    f.wf_follow_host_cfg = False
    with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_HOST_FOLLOW_REFUSAL)):
        _ww(f, "host", "path", "10", "-10", "24")
    f.wf_follow_host_cfg = True
    for bad in (["host", "path", "10", "24"], ["host", "path", "1600", "-10", "24"], ["host", "path", "10", "5", "24"],
                ["host", "path", "10", "-10", "500"], ["host", "path", "10", "-10", "x"]):
        with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_HOST_PATH_SHAPE)):
            _ww(f, *bad)
    with pytest.raises(RuntimeError, match="no bench host is on"):
        _ww(f, "hostseq", "freeze")
    with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_HOSTGAP_SHAPE)):
        _ww(f, "hostgap", "0")
    _ww(f, "hoststate", "0xC4")
    _ww(f, "host", "path", "10", "-10", "34", "-10", "24", "loop")
    assert _lines(f, "worldwalk host path 2 point(s) at 24 u/s, looping") and _lines(f, "worldwalk hoststate 0xC4")
    f._netsync(["selftest", "0"])
    with pytest.raises(RuntimeError, match=re.escape(BW.WORLDWALK_OFF_REFUSAL)):
        _ww(f, "pose", "off")


def _bench(f, *, path=("1500", "-444", "40", "-444"), ups="24", world=9011, x=68.0, z=-444.0):
    _bench_on_world(f, x, z, world)
    _ww(f, "host", "path", *path, ups)
    _secs(f, 0.5)


def test_a_stall_freeze_holds_a_hang_and_hostgap_says_one_gap_pair():
    """A-STALL / A-HANG: `hostseq freeze` keeps frames ARRIVING with the seq standing -- a HANG (never a gap), its end on the SENDER's clock;
    `hostgap 1500` stops arrivals while it keeps building -- one gap pair, its end on mine; lost contact at 5 s on `netsync.world.line`
    (exempt from the selftest role's OvlOff, never drawn there)."""
    f = _fake()
    _bench(f)
    _ww(f, "hostseq", "freeze")
    _secs(f, 2.0)
    lane = _lane(f)
    assert lane["open"] == "hang" and lane["arrival_age_ms"] < 100 and lane["seq_age_ms"] >= 1900 and lane["hangs"] == 1
    _secs(f, 3.5)
    line = _doc(f)["world"]["line"]
    assert line["asked"] == "lost" and line["text"] == BW.WORDS_WW_LOST_CONTACT and line["drawn"] is False
    assert _doc(f)["session"]["overlay"] == "off"
    _ww(f, "hostseq", "run")
    _secs(f, 0.3)
    lane = _lane(f)
    assert lane["last_line"] == "hang_end" and lane["last_len_ms"] >= 5000 and _doc(f)["world"]["line"]["asked"] is None
    _ww(f, "hostgap", "1500")
    _secs(f, 2.0)
    lane = _lane(f)
    gap = _lines(f, "selftest lane gap")
    assert lane["gaps"] == 1 and lane["last_line"] == "gap_end" and len(gap) == 2 and "over" in gap[1]
    assert re.search(r"gap over: the partner's frames are back after 1[45]\d\d ms", gap[1])


@pytest.mark.parametrize("place, word", [(3, "loading"), (4, "not updating")])
def test_a_hang_after_place_3_is_worded_loading_and_after_place_4_a_hang(place, word):
    f = _fake()
    _bench(f)
    _ww(f, "hostplace", str(place))
    _secs(f, 0.2)
    _ww(f, "hostseq", "freeze")
    _secs(f, 1.5)
    assert word in _lines(f, "selftest lane hang:")[-1]
    _ww(f, "hostgap", "2000")                                  # A-HANG's lever: a gap in the same state cuts the hang (never "loaded")
    _secs(f, 1.5)
    assert _lane(f)["last_line"] == "gap_start" and _lines(f, "frames STOPPED after") and not _lines(f, "loaded after")


def test_the_bench_host_off_resets_the_cache_and_the_release_puts_every_lever_back():
    f = _fake()
    _bench(f)
    _ww(f, "lanegap", "off")
    _ww(f, "hostplace", "3")
    f._wwk_release()
    lane = _lane(f)
    assert lane["lever"] == "act" and lane["bench"]["on"] is False and lane["bench"]["place"] == -1 and lane["resets"] == 1
    assert lane["reset_why"] == "the bench host left" and _lines(f, BW.LOG_WORLDWALK_RELEASED)
    assert _lines(f, BW.LOG_WW_RESET + "the bench host left")


def test_a_wire_another_wire_is_booked_once_per_version_and_cleared_by_mine():
    """A-WIRE: a frame of another wire -- `rejected` +1 per frame, ONE line per process and version, the mismatch words (the world line
    "mismatch", drawn on a client) for 5 s, cleared at once by a frame of my own wire; TCP's break line once per reason, the rest quiet."""
    f = _fake()
    f.netsync.update(enabled=True, role="client", instance=True)
    _step(f, 2)
    for _ in range(3):
        f.wire_frame(14, transport="tcp")
        _step(f, 1)
    wp = _doc(f)["wire_peer"]
    assert (wp["rejected"], wp["last_version"], wp["lines"], wp["mismatch"], wp["words"], wp["quiet_redials"]) == (
        3, 14, 1, True, BW.WORDS_WIRE_MISMATCH, 2)
    assert len(_lines(f, BW.log_peer_wire(14, 15))) == 1 and len(_lines(f, "wire-version mismatch")) == 1
    line = _doc(f)["world"]["line"]
    assert line["asked"] == "mismatch" and line["drawn"] is True
    f.wire_frame(None)
    _step(f, 1)
    assert _doc(f)["wire_peer"]["mismatch"] is False and _doc(f)["world"]["line"]["asked"] is None
    f.wire_frame(13)
    _secs(f, 5.1)
    wp = _doc(f)["wire_peer"]
    assert wp["lines"] == 2 and wp["mismatch"] is False and wp["rejected_age_ms"] >= 5000


def test_a_client_caches_its_hosts_trailer_from_the_transport_and_wire_peer_rx_reads_it():
    f = _fake()
    f.netsync.update(enabled=True, role="client", instance=True)
    host = FakeGame(_root())
    host.swap_qpc = None
    host.netsync.update(enabled=True, role="host", instance=True)
    host.ui_state, host.world = "WorldHUD", {"id": 9011, "x": 300.0, "z": -500.0, "vehicle": 0}
    host.dir.mkdir(parents=True, exist_ok=True)
    (host.dir / "arm").write_text("", encoding="utf-8")
    host.armed, host.state_every = True, 1 << 30
    host._world_load()
    for _ in range(5):
        host._frame_once()
        f.wire_frame(None, host.world_tx_frame())
        _step(f, 1)
    lane, rx = _lane(f), _doc(f)["wire_peer"]["rx"]
    assert lane["rx"]["world"] == 9011 and lane["rx"]["x"] == pytest.approx(300.0) and lane["rx"]["flags"] == 0
    assert (rx["len"], rx["kind"], rx["caps"], rx["place"]) == (94, "fmt1", 1, BW.WW_PLACE_WORLD)
    assert _lane(host)["tx"]["why"] == 0 and _lane(host)["tx"]["flags"] == 0     # a host never claims to follow; its why byte is 0


def _guest_frame(place, state, follows=True, seq=1):
    t = BW.ww_trailer(fmt=1, caps=1, seq=seq, ms=seq * 33, place=place, state=state, flags=BW.WW_FLAG_FOLLOW if follows else 0)
    return CP.build_pos_payload(0, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0) + CP.build_world_trailer(**BW.ww_write_fields(t, False))


def _host_on_world(faults=()):
    f = _fake(faults=faults)
    f.netsync.update(enabled=True, role="host", instance=True)
    f.enter_world(9011, 300.0, -500.0)
    _step(f, 3)
    return f


def _feed(f, place, state, secs, follows=True):
    for _ in range(round(secs * f._render_fps)):
        f._wwa["guest_seq"] = f._wwa.get("guest_seq", 0) + 1
        f.wire_frame(None, _guest_frame(place, state, follows, f._wwa["guest_seq"]))
        _step(f, 1)


def test_t2_h_the_hosts_lines_follow_its_guest_and_log_one_line_per_edge():
    """T2-H on the stand-in: a following guest's place 2 + b5 -> "following", place 3 -> "loading", place 4 + b6 -> "scene", silence 5 s ->
    "lost"; one log line per edge with the ended state's duration; `netsync.host.world.guest` reads the raw place / state / flags."""
    f = _host_on_world()
    _feed(f, 2, BW.WW_ST_WORLDOUT, 0.5)
    assert _doc(f)["host"]["world"]["guest"]["line"] == "following" and _doc(f)["world"]["line"]["drawn"] is True
    _feed(f, 3, 0, 0.5)
    _feed(f, 4, BW.WW_ST_SCENE | BW.WW_ST_VISIBLE, 0.5)
    guest = _doc(f)["host"]["world"]["guest"]
    assert (guest["place"], guest["state"], guest["flags"], guest["line"]) == (4, BW.WW_ST_SCENE | BW.WW_ST_VISIBLE, 1, "scene")
    _feed(f, 4, BW.WW_ST_VISIBLE, 0.2)
    _secs(f, 5.2)
    assert _doc(f)["host"]["world"]["guest"]["line"] == "lost" and _doc(f)["world"]["line"]["asked"] == "lost"
    logs = _lines(f, BW.LOG_WW_HOST_WORLD)
    assert [re.search(r'the partner is (\w+) \("', ln).group(1) for ln in logs if '("' in ln] == ["following", "loading", "scene", "lost"]
    assert re.search(r"the partner's following state ended after \d+ ms", logs[1]) and _doc(f)["host"]["world"]["guest"]["edges"] == 5


def test_t2_h_no_follow_flag_gets_no_lines_and_the_lever_silences_them():
    f = _host_on_world()
    _feed(f, 3, 0, 0.5, follows=False)
    assert _doc(f)["host"]["world"]["guest"]["line"] is None and not _lines(f, BW.LOG_WW_HOST_WORLD)
    _ww(f, "hostlines", "off")
    _feed(f, 3, 0, 0.5)
    assert _doc(f)["host"]["world"]["guest"]["line"] is None and _lane(f)["hostlines"] == "off"


def _guest_world_frame(seq):
    """[ff9mapkit netsync s166] W2 reconcile: a following guest's LIVE world frame (place 4, its block written: GhostRule can reach Stale)."""
    t = BW.ww_trailer(fmt=1, caps=1, seq=seq, ms=seq * 33, place=BW.WW_PLACE_WORLD, state=BW.WW_ST_CONTROL | BW.WW_ST_VISIBLE,
                      flags=BW.WW_FLAG_FOLLOW, world=9011, x=310.0, z=-500.0, rot=(0.0, 0.0, 0.0, 1.0), model=BW.WW_GEO_ZIDANE)
    return CP.build_pos_payload(0, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0) + CP.build_world_trailer(**BW.ww_write_fields(t, True))


def _hung_guest(f):
    """The guest walks 0.5 s, then HANGS 5.6 s: its writer re-sends the last frame byte for byte (arrivals continue, the seq stands)."""
    for seq in range(1, 16):
        f.wire_frame(None, _guest_world_frame(seq))
        _step(f, 1)
    for _ in range(round(5.6 * f._render_fps)):
        f.wire_frame(None, _guest_world_frame(15))
        _step(f, 1)


@pytest.mark.parametrize("lever", [False, True])
def test_t2_h_hostlines_off_silences_the_hosts_stall_lost_line_too(lever):
    """The review's W2R-1 on the stand-in: a host whose guest HANGS (re-sends, the seq frozen 5 s) reads lost contact from the stall hold
    (GhostRule Stale) -- the control row; under `worldwalk hostlines off` the host shows no line for its guest, that one included."""
    f = _host_on_world()
    if lever:
        _ww(f, "hostlines", "off")
    _hung_guest(f)
    doc = _doc(f)
    assert doc["world"]["lane"]["seq_age_ms"] >= BW.WW_GHOST_GRACE_MS and doc["world"]["lane"]["arrival_age_ms"] < 200   # a hang, not a gap
    assert doc["world"]["line"]["asked"] == (None if lever else "lost"), doc["world"]["line"]
    assert bool(_lines(f, BW.LOG_WW_LINE_LOST)) is (not lever)


def test_t2_h_hostlines_off_logs_no_guest_edge_even_its_own_flip():
    """The review's W2R-2: pulling `hostlines off` while the guest's "following" line stands ends that state with NO log line (the book
    still steps: `edges` counts it); the control -- the same end without the lever -- IS logged."""
    for lever in (False, True):
        f = _host_on_world()
        _feed(f, 2, BW.WW_ST_WORLDOUT, 0.5)
        assert _doc(f)["host"]["world"]["guest"]["line"] == "following"
        said, edges = len(_lines(f, BW.LOG_WW_HOST_WORLD)), _doc(f)["host"]["world"]["guest"]["edges"]
        if lever:
            _ww(f, "hostlines", "off")
            _step(f, 2)
        else:
            _feed(f, 4, BW.WW_ST_VISIBLE, 0.2)                 # the control: the guest lands -- "following" ends with its line
        assert _doc(f)["host"]["world"]["guest"]["edges"] == edges + 1
        assert (len(_lines(f, BW.LOG_WW_HOST_WORLD)) == said) is lever


def test_a4_the_stand_in_says_its_mints_animates_only_when_drawn_and_shadows_by_the_rule():
    """A4 final on the stand-in: MintRoot's and MintBody's lines once each (the REAL world GEO, 310 on 9011), WorldAnimRule's mode while
    drawn (the stand-in's frame count 0 free-runs: no frame-follow), null under `ghost off` (want true, placed, not drawn), ShadowRule's
    walker row at the stand-in's fogAMP."""
    f = _fake()
    _bench(f)
    roots, bodies = _lines(f, BW.LOG_WW_GHOST_ROOT), _lines(f, BW.LOG_WW_GHOST_BODY)
    assert len(roots) == 1 and "on map 9011 (the shadow; hidden until wanted)" in roots[0], roots
    assert len(bodies) == 1 and bodies[0].startswith(BW.log_ww_ghost_body("GEO_SUB_W0_001", 310, FG.FAKE_WORLD_BODY["renderers"],
                                                                           FG.FAKE_WORLD_BODY["clips"], "ANH_SUB_W0_001_STAND", 0, 12)), bodies
    g = _ghost(f)
    assert g["shown"] and g["geo"] == "GEO_SUB_W0_001" and g["stand"] == "ANH_SUB_W0_001_STAND"
    assert g["anim"] == "free" and g["follow"] is False and g["stall"] == "move"
    assert (g["shadow_scale"], g["shadow_amp"]) == BW.ww_shadow_rule(g["ground_y"], g["wire_y"], FG.FAKE_WORLD_BODY["fog_amp"]) == (0.87890625, 0.65)
    _ww(f, "ghost", "off")
    _step(f, 2)
    g = _ghost(f)
    assert g["want"] and not g["shown"] and g["placed"] and g["anim"] is None and g["follow"] is False and g["lever"] == "off"
    assert _lines(f, "worldwalk ghost off")[-1] == BW.LOG_WORLDWALK_GHOST_OFF
    _ww(f, "ghost", "on")
    _step(f, 2)
    assert _ghost(f)["shown"] and _ghost(f)["anim"] == "free" and _lines(f, "worldwalk ghost on")[-1] == BW.LOG_WORLDWALK_GHOST_ON
    _ww(f, "clear")
    assert _lines(f, "worldwalk clear")[-1] == BW.LOG_WORLDWALK_CLEAR_A4


def _ghost(f) -> dict:
    return _doc(f)["world"][BW.A4_CONTRACT["ghost_key"]]


def _dot_frame(f):
    """[ff9mapkit netsync s166] W2: s165's fabricated section 0 (`worldfollow host self`) -- the dot is placed (DotWanted) only with a host
    frame, and A4's `dot.src` is null while it is not placed (AppendWorldDot, final)."""
    f._netsync(["worldfollow", "host", "self"])
    _step(f, 2)


def test_a_ghost_walks_across_the_x_seam_on_its_canonical_pose_and_the_dot_reads_the_trailer():
    """A-GHOST / A-DOTRIDE (A4): a bench host walking 1500 -> 40 across the x seam: the ghost within GHOST_TOL of the canonical
    pose every frame (an ease the short way round), the dot's source "trailer"; `pose off` puts the dot back on section 0."""
    f = _fake()
    _bench(f)
    _dot_frame(f)
    for _ in range(40):
        _step(f, 1)
        g, b = _ghost(f), _lane(f)["bench"]
        assert g["shown"] and BW.ww_torus_distance(g["x"], g["z"], b["x"], b["z"]) < 3.0, (g, b)
    assert _doc(f)["world"]["dot"]["src"] == "trailer"
    _ww(f, "pose", "off")
    _step(f, 3)
    assert _doc(f)["world"]["dot"]["src"] == "section0" and _ghost(f)["why_not"] == "no_record"    # tfmt 0 reads capless: no record


def test_a_wrap_the_inverse_is_the_point_as_my_walker_wraps_both_seams_and_place_render_is_red_exactly_there():
    f = _fake()
    _bench(f, path=("40", "-20"), ups="0", x=1500.0, z=-1270.0)
    seen = []
    for x, z in ((1530.0, -1275.0), (5.0, -1275.0), (5.0, -5.0), (40.0, -10.0), (1530.0, -5.0), (100.0, -100.0)):
        f.world["x"], f.world["z"] = x, z
        _step(f, 1)
        g = _ghost(f)
        seen.append(BW.ww_torus_distance(g["inv_x"], g["inv_z"], 40.0, -20.0))
    assert max(seen) < 0.01, seen
    _ww(f, "place", "render")
    red = []
    for x, z in ((1530.0, -1275.0), (5.0, -1275.0), (5.0, -5.0)):
        f.world["x"], f.world["z"] = x, z
        _step(f, 1)
        g = _ghost(f)
        red.append(BW.ww_torus_distance(g["inv_x"], g["inv_z"], 40.0, -20.0))
    assert all(d > 10.0 for d in red), red


def test_a_stall_the_ghost_stands_by_300_ms_hides_at_5_s_and_snaps_on_the_re_show():
    f = _fake()
    _bench(f, path=("40", "-444", "200", "-444"), ups="24")
    _ww(f, "hostseq", "freeze")
    _secs(f, 0.4)
    g = _ghost(f)
    assert g["shown"] and g["anim"] == "stand" and g["clip"] == g["stand"] and g["holds"] == 1   # [s166] W2: A4 final (`anim` the mode)
    _secs(f, 4.8)
    g = _ghost(f)
    assert not g["shown"] and g["why_not"] == "stale" and g["want"] is False and g["hides"] == 1
    snaps = g["snaps"]
    _ww(f, "hostseq", "run")
    _secs(f, 0.2)
    assert _ghost(f)["shown"] and _ghost(f)["snaps"] == snaps + 1


@pytest.mark.parametrize("ops, why", [((("hostworld", "9010"),), "other_world"), ((("hostmode", "1"),), "riding"),
                                      ((("hoststate", "0xC4"),), "peer_scene"), ((("hostplace", "5"),), "peer_block"),
                                      ((("ghost", "off"),), "lever")], ids=["other_world", "riding", "scene", "place5", "lever"])
def test_a_rule_each_refusal_alone_and_the_lever_keeps_want(ops, why):
    f = _fake()
    _bench(f)
    for op in ops:
        _ww(f, *op)
    _secs(f, 0.3)
    g = _ghost(f)
    assert g["why_not"] == why and g["shown"] is False and g["want"] == (why == "lever")


def test_a_rule_an_event_world_and_a_9002_body():
    f = _fake()
    _bench(f, world=9012)
    assert _ghost(f)["why_not"] == "event_world"
    f2 = _fake()
    _bench(f2, world=9002)
    g = _ghost(f2)
    assert g["shown"] and g["model"] == BW.WW_GEO_DAGGER and _lane(f2)["rx"]["model"] == BW.WW_GEO_DAGGER


def test_a_menu_the_debug_menus_hold_never_sets_b6_and_control_off_does():
    """A-MENU: the ~ menu open 1 s with "Disable control" -- b6 stays clear (a PAUSE); `control 0` for 1 s -- b6 set."""
    f = _fake()
    _bench_on_world(f)
    f.debug_menu_hold(True)
    _secs(f, 1.0)
    assert not _lane(f)["tx"]["state"] & BW.WW_ST_SCENE
    f.debug_menu_hold(False)
    _step(f, 2)
    f.control = False
    _secs(f, 1.0)
    assert _lane(f)["tx"]["state"] & BW.WW_ST_SCENE


def test_the_proof_line_carries_the_tallies_derived_from_the_engine_source():
    f = _fake()
    f.world_walk_source = ("private static Int32 Rows(Rules r, List<String> fails) { row(a, \"x\"); row(b, \"y\"); }\n"
                           "private static Rules Mutant(String name) { }\nprivate static readonly String[] MutantNames = { \"m\" };")
    f._netsync(["selftest", "1"])
    _step(f, 4)
    assert _lines(f, BW.PROOF_WORLD_WALK) == ["[NetSync] " + BW.PROOF_WORLD_WALK + "OK (2 rows, 1 mutants)"]


# ---- every round-A fault turns EXACTLY its model rows red (the stand-in's calibration; the bench rows map onto these)
def _scenario_stall(faults):
    f = _fake(faults=faults)
    _bench(f)
    _ww(f, "hostseq", "freeze")
    _secs(f, 0.5)
    g = _ghost(f)
    stand = g["anim"] == "stand"                              # [ff9mapkit netsync s166] W2: A4 final (`anim` the mode, `clip` the name)
    _secs(f, 1.5)
    lane = _lane(f)
    out = {"hang_not_gap": lane["open"] == "hang", "arrivals_fresh": lane["arrival_age_ms"] < 250, "stands_by_300ms": stand,
           "hang_line_said": bool(_lines(f, "selftest lane hang:"))}
    _ww(f, "hostseq", "run")
    _ww(f, "hostplace", "3")
    _secs(f, 0.3)
    _ww(f, "hostseq", "freeze")
    _secs(f, 1.2)
    _ww(f, "hostgap", "2000")
    _secs(f, 1.4)
    out["cut_never_loaded"] = bool(_lines(f, "frames STOPPED after")) and not _lines(f, "loaded after")
    return out


def _scenario_tx(faults):
    f = _fake(faults=faults)
    _bench_on_world(f)
    s0 = _lane(f)["tx"]["seq"]
    _step(f, 3)
    tx = _lane(f)["tx"]
    out = {"tx_field_zero": tx["field"] == 0, "tx_seq_advances": tx["seq"] == s0 + 3}
    _ww(f, "pose", "off")
    _step(f, 2)
    out["pose_off_tfmt0"] = _lane(f)["tx"]["kind"] == "tfmt0"
    f.debug_menu_hold(True)
    _secs(f, 1.0)
    out["menu_hold_no_b6"] = not _lane(f)["tx"]["state"] & BW.WW_ST_SCENE
    f.debug_menu_hold(False)
    _ww(f, "lanegap", "off")
    return out


def _scenario_ghost(faults):
    f = _fake(faults=faults)
    _bench(f)
    _dot_frame(f)
    near = True
    for _ in range(30):
        _step(f, 1)
        g, b = _ghost(f), _lane(f)["bench"]
        near = near and g["shown"] and BW.ww_torus_distance(g["x"], g["z"], b["x"], b["z"]) < 3.0
    out = {"ghost_on_pose": near, "dot_from_trailer": _doc(f)["world"]["dot"]["src"] == "trailer"}
    _ww(f, "dot", "section0")
    _step(f, 1)
    out["dot_lever_section0"] = _doc(f)["world"]["dot"]["src"] == "section0"
    _ww(f, "ghost", "off")
    _step(f, 1)
    out["ghost_lever_hides"] = _ghost(f)["why_not"] == "lever" and not _ghost(f)["shown"]
    _ww(f, "ghost", "on")
    f.world["x"], f.world["z"] = 1530.0, -444.0
    _ww(f, "place", "render")
    _step(f, 1)
    f.world["x"] = 5.0
    _step(f, 1)
    g = _ghost(f)
    out["place_render_breaks_wrap"] = BW.ww_torus_distance(g["inv_x"], g["inv_z"], g["x"], g["z"]) > 10.0
    mints = _ghost(f)["mints"]
    f.ui_state, f.field_id = "FieldHUD", 6603
    _step(f, 3)
    out["no_mint_on_a_field"] = _ghost(f)["mints"] == mints
    f2 = _fake(faults=faults)
    _bench(f2, world=9002)
    out["body_9002_dagger"] = _ghost(f2)["model"] == BW.WW_GEO_DAGGER
    return out


def _scenario_wire(faults):
    f = _fake(faults=faults)
    f.netsync.update(enabled=True, role="client", instance=True)
    _step(f, 2)
    f.wire_frame(14)
    _step(f, 1)
    out = {"wire_rejected_booked": _doc(f)["wire_peer"]["rejected"] == 1 and _doc(f)["world"]["line"]["asked"] == "mismatch"}
    f.wire_frame(None)
    _step(f, 1)
    out["wire_mine_clears"] = _doc(f)["wire_peer"]["mismatch"] is False
    return out


def _scenario_lines(faults):
    f = _fake(faults=faults)
    _bench(f)
    _ww(f, "hostseq", "freeze")
    _secs(f, 5.3)
    out = {"line_lost_at_5s": _doc(f)["world"]["line"]["asked"] == "lost"}
    _ww(f, "lanegap", "off")
    _ww(f, "hostseq", "run")
    _secs(f, 0.2)                                              # the hang's END is said (its start was): only STARTS go silent
    n = _lane(f)["lines"]
    _ww(f, "hostgap", "1200")
    _secs(f, 1.5)
    out["lanegap_off_silent"] = _lane(f)["lines"] == n and _lane(f)["gaps"] >= 1
    h = _host_on_world(faults)
    _feed(h, 4, BW.WW_ST_SCENE | BW.WW_ST_VISIBLE, 0.4)
    out["host_sees_released_guest_scene"] = _doc(h)["host"]["world"]["guest"]["line"] == "scene"
    _ww(h, "hostlines", "off")
    _step(h, 2)
    out["hostlines_off_silent"] = _doc(h)["host"]["world"]["guest"]["line"] is None
    return out


SCENARIOS = {"stall": _scenario_stall, "tx": _scenario_tx, "ghost": _scenario_ghost, "wire": _scenario_wire, "lines": _scenario_lines}
#: each round-A fault -> the scenario and EXACTLY the model rows it turns red there
FAULT_ROWS = {
    "ghost_unwrapped": ("ghost", ("ghost_on_pose",)),
    "gap_on_stamp": ("stall", ("hang_not_gap", "hang_line_said", "cut_never_loaded")),            # a hang read as a gap: arrivals fresh
    "arrival_on_seq": ("stall", ("hang_not_gap", "arrivals_fresh", "hang_line_said", "cut_never_loaded")),   # ...and the clock stale
    "hold_on_valid": ("stall", ("stands_by_300ms",)),
    "ghost_stale_mint": ("ghost", ("no_mint_on_a_field",)),
    "wire_field_world": ("tx", ("tx_field_zero",)),
    "scene_menu_hold": ("tx", ("menu_hold_no_b6",)),
    "pose_lever_ignored": ("tx", ("pose_off_tfmt0",)),
    "lanegap_lever_ignored": ("lines", ("lanegap_off_silent",)),
    "hostlines_lever_ignored": ("lines", ("hostlines_off_silent",)),
    "ghost_lever_ignored": ("ghost", ("ghost_lever_hides",)),
    "place_lever_ignored": ("ghost", ("place_render_breaks_wrap",)),
    "dot_src_lever_ignored": ("ghost", ("dot_lever_section0",)),
    "wire_peer_dark": ("wire", ("wire_rejected_booked",)),
    "wire_words_latched": ("wire", ("wire_mine_clears",)),
    "tx_seq_frozen": ("tx", ("tx_seq_advances",)),
    "line_dark": ("lines", ("line_lost_at_5s",)),
    "dot_src_section0": ("ghost", ("dot_from_trailer",)),
    "ghost_dress_310": ("ghost", ("body_9002_dagger",)),
    "host_lines_state_b0": ("lines", ("host_sees_released_guest_scene",)),
    "hang_cut_as_update": ("stall", ("cut_never_loaded",)),
}


def test_the_fault_table_names_every_round_a_fault_once():
    assert set(FAULT_ROWS) == set(FG.WORLD_WALK_A_FAULTS) and len(FG.WORLD_WALK_A_FAULTS) == len(set(FG.WORLD_WALK_A_FAULTS))
    assert not set(FG.WORLD_WALK_A_FAULTS) & set(FG.WORLD_WALK_FAULTS)      # apart from A0 / A0b's (their legs' own tables)
    for name in ("ghost_unwrapped", "gap_on_stamp", "arrival_on_seq", "hold_on_valid", "ghost_stale_mint", "wire_field_world",
                 "scene_menu_hold"):
        assert name in FG.WORLD_WALK_A_FAULTS, name                 # the design's named round-A faults


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_each_model_scenario_is_green_on_the_healthy_stand_in(scenario):
    out = SCENARIOS[scenario](())
    assert all(out.values()), out


@pytest.mark.parametrize("fault", sorted(FAULT_ROWS))
def test_each_round_a_fault_turns_exactly_its_model_rows_red(fault):
    scenario, rows = FAULT_ROWS[fault]
    out = SCENARIOS[scenario]((fault,))
    red = tuple(sorted(k for k, ok in out.items() if not ok))
    assert red == tuple(sorted(rows)), (fault, out)
