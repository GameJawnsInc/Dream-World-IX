"""[ff9mapkit netsync s167] WORLD WALK, ROUND B -- THE STAND-IN'S MODEL of the walk (studies/world-coop/S166-DESIGN.md decisions 13-28):
battlewire's twins of every round-B rule, each pinned to the ENGINE's source BY STAGE, fakegame's `worldwalk` rung piece "b", and coop_peer's
s167 wire (the caps word, the digest, section 11).

  * THE TWINS: every rule's truth table (the engine proof's own rows, re-stated), and a one-line mutant of each key twin fails ITS OWN row.
  * THE ENGINE PINS, by stage: the s167 patch on this branch's stack, else a clone named by FF9_S167_CLONE carrying the s167 tag; else (the
    deployed s166 stage) each pin SKIPS. Constants, tables, term order, names, line texts, the catch literal's `walk` / `fp` and the lane's
    s167 keys, the verb's usage / clear / acks, the proof's and the overlay selftest's tallies are read off the source, so a drift goes red.
  * THE STAND-IN, stepped BY HAND (pieces FAKE_WORLD_WALK_S167_PIECES; the default stays the deployed s166): the keys in the agent's order,
    W-FREE and `walk off`, every W-REFUSE term, the stall hold and the world reload's drop, the entry buzz (a location, a kit cell under both
    reader orders), the visit's re-arm, the fingerprint, WorldTPS, the caps line, decisions 23 / 27 / 28 -- and every round-B fault turns ITS
    row red.
  * COOP_PEER: caps 0x0003 when the host speaks it (`--caps 1` an s166-shaped guest), the digest echo / pin, the why byte gated as the engine
    gates it, section 11 on a host record (`where --pose` names it with the digest), replay-host passing section 11 through.
"""
import json
import os
import pathlib
import re
import sys
import tempfile

import pytest

from ._patchstack import msr, stack_file

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from harness import battlewire as BW                                   # noqa: E402
from harness import coop_peer as CP                                    # noqa: E402
from harness import fakegame as FG                                     # noqa: E402
from harness.fakegame import FakeGame                                  # noqa: E402

S167_TAG = "[ff9mapkit netsync s167]"
S167_CLONE_ENV = "FF9_S167_CLONE"
_LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


# ================================================================================================ THE TWINS (pure)
def _host(**kw):
    """A host's held trailer as the hold keeps it: a valid world block on 9011, on foot, caps b0 + b1, a digest."""
    t = BW.ww_trailer(has=True, fmt=1, caps=BW.WW_OWN_CAPS_WALK, seq=9, place=BW.WW_PLACE_WORLD, state=BW.WW_ST_CONTROL | BW.WW_ST_VISIBLE,
                      world=9011, x=70.0, z=-444.0, rot=(0.0, 0.0, 0.0, 1.0), model=BW.WW_GEO_ZIDANE, digest=0x1234ABCD)
    t.update(kw)
    return t


def _wf(**kw):
    """WalkFixture: the field-gate bench on 9011, every term free (the engine proof's base row)."""
    f = BW.ww_walk_facts(role="selftest", follow_host=True, bench_gates=True, suppress_encounters=True, own_world=9011, walker_index=1,
                         host=_host(), host_state_set=True, host_b6=True, host_sc=1000, own_sc=1000, own_caps=BW.WW_OWN_CAPS_WALK,
                         own_digest=0x1234ABCD)
    f.update(kw)
    return f


#: decision 14, one row per term in its order: (the fixture's change, the why it must read)
WALK_ROWS = [
    ({}, BW.WW_WALK_FREE),
    (dict(lever_off=True), BW.WW_WALK_LEVER),
    (dict(follow_host=False), BW.WW_WALK_ROLE),
    (dict(role="client", follow_host=True, mirroring=True, ramp_pending=True), BW.WW_WALK_RAMP),
    (dict(pair_unmirrored=True), BW.WW_WALK_PAIRING),
    (dict(role="client", mirroring=False), BW.WW_WALK_PAIRING),
    (dict(suppress_encounters=False), BW.WW_WALK_ENCOUNTERS),
    (dict(diorama=True), BW.WW_WALK_NOT_LIVE),
    (dict(own_world=9000, host=_host(world=9000)), BW.WW_WALK_SET),
    (dict(own_mode=7), BW.WW_WALK_OWN_MODE),
    (dict(walker_index=0), BW.WW_WALK_OWN_MODE),
    (dict(transition=True), BW.WW_WALK_TRANSITION),
    (dict(host=_host(caps=0)), BW.WW_WALK_PEER_CAPS),
    (dict(host=BW.ww_trailer()), BW.WW_WALK_PEER_CAPS),
    (dict(host_b6=False), BW.WW_WALK_HOST_NOT_WORLD),
    (dict(host=_host(world=9010)), BW.WW_WALK_OTHER_WORLD),
    (dict(host_sc=6000), BW.WW_WALK_BAND),
    (dict(host=_host(mode=1)), BW.WW_WALK_RIDING),
    (dict(host=_host(state=BW.WW_ST_SCENE)), BW.WW_WALK_HOST_SCENE),
    (dict(own_caps=BW.WW_OWN_CAPS), BW.WW_WALK_FP_OFF),
    (dict(host=_host(caps=BW.WW_OWN_CAPS, digest=0)), BW.WW_WALK_OLD_PARTNER),
    (dict(own_digest=0), BW.WW_WALK_CHECKING),
    (dict(own_digest=0xDEAD), BW.WW_WALK_FP_MISMATCH),
    (dict(fp_dry=True), BW.WW_WALK_FP_DRY),
    (dict(plane_bound=True), BW.WW_WALK_FREE),                         # kit 9011's boat binds the plane: lawful
    (dict(veg=1), BW.WW_WALK_FREE),                                    # no [181] term
    (dict(visitor_follow_host=False), BW.WW_WALK_FREE),                # never NetSyncVisitor.FollowHost
    (dict(host_arrival_age_ms=60000), BW.WW_WALK_FREE),                # staleness never freezes
]


@pytest.mark.parametrize("change, why", WALK_ROWS, ids=[f"{i}:{BW.ww_walk_why_name(w)}" for i, (_c, w) in enumerate(WALK_ROWS)])
def test_walk_free_rule_reads_each_term_in_its_order(change, why):
    assert BW.ww_walk_free_rule(_wf(**change)) == why


def _walk_mutant_catches(mutant, row) -> bool:
    change, why = WALK_ROWS[row]
    return mutant(_wf(**change)) != why


def test_each_walk_mutant_fails_its_own_row():
    """The design's mutants (S166-DESIGN.md "A1"): a [181] term, a plane-pointer refusal, no pairing term, freeze on staleness,
    NetSyncVisitor.FollowHost read -- each caught by the row named beside it."""
    real = BW.ww_walk_free_rule
    veg = lambda f: BW.WW_WALK_OWN_MODE if f["veg"] else real(f)                                       # noqa: E731
    plane = lambda f: BW.WW_WALK_OWN_MODE if f["plane_bound"] else real(f)                             # noqa: E731
    nopair = lambda f: real(dict(f, pair_unmirrored=False, mirroring=True))                            # noqa: E731
    stale = lambda f: BW.WW_WALK_HOST_NOT_WORLD if f["host_arrival_age_ms"] > 2000 else real(f)        # noqa: E731
    visitor = lambda f: real(dict(f, follow_host=f["visitor_follow_host"]))                            # noqa: E731
    rows = {r: i for i, r in enumerate(map(lambda x: json.dumps(x[0], default=str), WALK_ROWS))}
    assert _walk_mutant_catches(veg, rows[json.dumps(dict(veg=1))])
    assert _walk_mutant_catches(plane, rows[json.dumps(dict(plane_bound=True))])
    assert _walk_mutant_catches(nopair, rows[json.dumps(dict(pair_unmirrored=True))])
    assert _walk_mutant_catches(stale, rows[json.dumps(dict(host_arrival_age_ms=60000))])
    assert _walk_mutant_catches(visitor, rows[json.dumps(dict(visitor_follow_host=False))])


def test_the_why_byte_and_its_names():
    """WhyByteRule (the host 0; `walk off` / a non-b1 partner s166's raw code; place 4 the walk's class; elsewhere W3C-4's class),
    WhyClassesOnRule (BOTH caps words b1, the walk on) and WhyByteName."""
    assert BW.ww_why_byte_rule(False, "host", 4, BW.WW_WALK_PAIRING, 5) == 0
    assert BW.ww_why_byte_rule(True, "client", 4, BW.WW_WALK_PAIRING, 29) == 0x1F                    # s166: PackWhy(1, raw) folds 29
    assert BW.ww_why_byte_rule(False, "client", 4, BW.WW_WALK_PAIRING, 29) == 0x23
    assert BW.ww_why_byte_rule(False, "client", 4, BW.WW_WALK_FREE, 29) == 0                           # walking free: class 0
    assert BW.ww_why_byte_rule(False, "client", 1, BW.WW_WALK_FREE, 29) == 0x13                        # pairing_save -> class 3
    assert BW.ww_why_classes_on_rule(False, 3, 3) and not BW.ww_why_classes_on_rule(True, 3, 3)
    assert not BW.ww_why_classes_on_rule(False, 3, 1) and not BW.ww_why_classes_on_rule(False, 1, 3)  # one word is not both
    assert BW.ww_why_byte_name(0x23, True) == "walk:pairing" and BW.ww_why_byte_name(0x1F, False) == "world_out_code:15+"
    assert BW.ww_why_byte_name(0x13, True) == "world_out:pairing" and BW.ww_why_byte_name(0x13, False) == "world_out_code:3"
    assert BW.ww_why_byte_name(0x31, True) == "rule3:1" and BW.ww_why_byte_name(0, True) is None and BW.ww_why_byte_name(0x20, True) is None
    assert [BW.ww_walk_why_class(w) for w in range(21)] == list(BW.WW_WALK_CLASSES) and BW.ww_walk_why_class(99) == 0
    assert len(BW.WW_WORLD_OUT_CLASSES) == 30 and BW.ww_world_out_why_class(30) == 0 and max(BW.WW_WORLD_OUT_CLASSES) == 15


def test_the_hold_the_stall_hole_and_the_visit():
    h = BW.ww_walk_hold()
    BW.ww_walk_hold_step(h, False, True, _host(), True, True, 1000)
    assert h["trailer_set"] and h["state_set"] and h["b6"] and h["host_sc"] == 1000
    BW.ww_walk_hold_step(h, False, False, BW.ww_trailer(), False, False, -1)          # a stale Update keeps both parts
    assert h["trailer_set"] and h["host"]["digest"] == 0x1234ABCD and h["host_sc"] == 1000
    BW.ww_walk_hold_step(h, True, False, BW.ww_trailer(), False, False, -1)           # a drop: frozen until a fresh frame
    assert not h["trailer_set"] and not h["state_set"] and h["drops"] == 1 and h["host_sc"] == -1
    BW.ww_walk_hold_step(h, False, True, BW.ww_trailer(), False, False, -1)           # a capless frame is taken too: it freezes
    assert h["trailer_set"] and not h["host"]["has"]
    assert BW.ww_walk_hold_drop_rule(False, False, True, False, False) and not BW.ww_walk_hold_drop_rule(*(False,) * 5)
    assert BW.ww_world_session_held_rule(True, "client", True, False, True, False)
    assert not BW.ww_world_session_held_rule(True, "selftest", True, True, False, False)
    assert not BW.ww_world_session_held_rule(True, "client", True, True, False, True)
    assert BW.ww_world_spectator_rule(False, 3, True, False) and not BW.ww_world_spectator_rule(False, 1, True, False)
    assert not BW.ww_world_spectator_rule(False, 3, True, True) and BW.ww_world_spectator_rule(True, 1, False, True)
    v = BW.ww_visit_book()
    assert BW.ww_visit_step(v, False, True) and v["visits"] == 1                        # the process's first world load
    assert not BW.ww_visit_step(v, False, True) and v["visits"] == 1                    # a warm return: the same visit
    BW.ww_visit_step(v, True, False)
    assert BW.ww_visit_step(v, False, True) and v["visits"] == 2                        # field -> world: a new visit
    assert BW.ww_decline_rearm_rule(True, False) and not BW.ww_decline_rearm_rule(True, True)


def _er(**kw):
    return BW.ww_entry_read(keys=BW.EV_CONFIRM, read_mask=BW.EV_CONFIRM, key_tick=5, **kw)


ENTRY_ROWS = [
    (dict(sid=1, place=4), BW.WW_ENTRY_LOCATION),
    (dict(sid=1, place=52), BW.WW_ENTRY_NONE),                         # the quicksand stays silent
    (dict(sid=1, place=4, bit812=True), BW.WW_ENTRY_NONE),
    (dict(sid=1, place=4, lock=1), BW.WW_ENTRY_NONE),
    (dict(sid=0), BW.WW_ENTRY_KIT_CELL),
    (dict(sid=15, place=169), BW.WW_ENTRY_BOAT),
    (dict(sid=15, place=100), BW.WW_ENTRY_NONE),                       # the boat's eager read out of range
    (dict(sid=15, place=169, mode=7), BW.WW_ENTRY_NONE),
    (dict(sid=16, place=100), BW.WW_ENTRY_FERRY),
    (dict(sid=16, place=169), BW.WW_ENTRY_NONE),
    (dict(sid=15, place=169, world=9010), BW.WW_ENTRY_NONE),          # the kit objects are 9011's
    (dict(sid=0, world=9000), BW.WW_ENTRY_NONE),                       # not a walk world
    (dict(sid=0, last_tick=5), BW.WW_ENTRY_NONE),                      # the KeyTick dedupe
    (dict(sid=0, held=True), BW.WW_ENTRY_NONE),
    (dict(sid=0, control=False), BW.WW_ENTRY_NONE),
    (dict(sid=0, frozen=False), BW.WW_ENTRY_NONE),
    (dict(sid=0, lever_silent=True), BW.WW_ENTRY_NONE),
    (dict(sid=0, gmode=1), BW.WW_ENTRY_NONE),
    (dict(sid=7), BW.WW_ENTRY_NONE),                                   # any other reader (the buzz-on-any mutant's row)
]


@pytest.mark.parametrize("change, entry", ENTRY_ROWS, ids=[str(i) for i in range(len(ENTRY_ROWS))])
def test_the_entry_refusal_rule(change, entry):
    assert BW.ww_entry_refusal_rule(_er(**change)) == entry


def test_the_entry_mutants_fail_their_rows():
    real = BW.ww_entry_refusal_rule
    any_confirm = lambda e: BW.WW_ENTRY_LOCATION if e["keys"] & BW.EV_CONFIRM and e["frozen"] else real(e)   # noqa: E731
    no_dedupe = lambda e: real(dict(e, last_tick=-1))                                                         # noqa: E731
    place_only = lambda e: BW.WW_ENTRY_LOCATION if e["place"] not in (100, 52) and e["sid"] == 1 else BW.WW_ENTRY_NONE  # noqa: E731
    no169 = lambda e: BW.WW_ENTRY_BOAT if e["sid"] == 15 and e["mode"] == 0 and e["world"] == 9011 else real(e)  # noqa: E731
    assert any_confirm(_er(sid=7)) != BW.WW_ENTRY_NONE                 # the open-ground row
    assert no_dedupe(_er(sid=0, last_tick=5)) != BW.WW_ENTRY_NONE      # the dedupe row
    assert place_only(_er(sid=0)) != BW.WW_ENTRY_KIT_CELL              # the kit-cell row
    assert no169(_er(sid=15, place=100)) != BW.WW_ENTRY_NONE           # the boat-range row
    assert BW.ww_entry_lock_var(9002) == 33 and BW.ww_entry_lock_var(9011) == 35 and BW.ww_entry_lock_var(9000) == -1
    assert BW.ww_story_bit811(0x08) and BW.ww_story_bit812(0x10) and not BW.ww_story_bit811(0x10)
    assert BW.ww_entry_line_live_rule(True, 3999) and not BW.ww_entry_line_live_rule(True, 4000)


def test_the_fingerprint_rules():
    assert BW.ww_fp_lang_word("US") == 0x5355 and BW.ww_fp_lang_word("U") == 0 and BW.ww_fp_lang_word(None) == 0
    comps = [0x5355, 1, 2, 3, 4, 5]
    d = BW.ww_fp_combine(comps)
    import struct
    import zlib
    assert d == zlib.crc32(struct.pack("<6I", *comps)) and BW.ww_fp_combine(comps[:5]) == 0
    assert BW.ww_fp_state_rule(1, 3, d, d) == BW.WW_FP_OFF and BW.ww_fp_state_rule(3, 1, d, d) == BW.WW_FP_OLD
    assert BW.ww_fp_state_rule(3, 3, 0, d) == BW.WW_FP_CHECKING and BW.ww_fp_state_rule(3, 3, d, d) == BW.WW_FP_SAME
    assert BW.ww_fp_state_rule(3, 3, d, d ^ 1) == BW.WW_FP_DIFFERS
    body = BW.ww_write_fp_section(9011, comps)
    assert len(body) == BW.WW_FP_SECTION_LEN == 36 and body[:6] == bytes([1, 0x33, 0x23, 0x55, 0x53, 6])
    assert BW.ww_try_read_fp_section(body) == (9011, 0x5355, comps, 0x3F)
    assert BW.ww_try_read_fp_section(body[:20]) is None and BW.ww_try_read_fp_section(b"\x00" + body[1:]) is None
    unknown = bytearray(body)
    unknown[BW.WW_FP_SECTION_HEAD + 5] = 9                              # comp 1's id -> an id this build does not know: skipped
    assert BW.ww_try_read_fp_section(bytes(unknown))[3] == 0x3D
    other = list(comps)
    other[2] = 0xDEAD
    assert BW.ww_fp_first_differ_rule(9011, other, 9011, 0x5355, comps, 0x3F) == BW.WW_FP_MESHES
    assert BW.ww_fp_first_differ_rule(9011, other, 9010, 0x5355, comps, 0x3F) == BW.WW_FP_NAME_STALE
    assert BW.ww_fp_first_differ_rule(9011, comps, 9011, 0x5246, comps, 0x3F) == BW.WW_FP_LANG
    assert BW.ww_fp_first_differ_rule(9011, other, 9011, 0x5355, comps, 0x3B) == BW.WW_FP_NAME_NONE   # c2 absent: none named
    assert BW.ww_fp_checking_line_rule(10000, False) and not BW.ww_fp_checking_line_rule(10000, True)
    assert not BW.ww_fp_checking_line_rule(9999, False)
    assert BW.ww_fp_tx_digest_rule(3, 4, d) == d and BW.ww_fp_tx_digest_rule(1, 4, d) == 0 and BW.ww_fp_tx_digest_rule(3, 1, d) == 0
    assert BW.ww_fp_section_send_rule(True, 3, 3, True, d) and not BW.ww_fp_section_send_rule(True, 3, 1, True, d)
    assert not BW.ww_fp_section_send_rule(False, 3, 3, True, d) and not BW.ww_fp_section_send_rule(True, 3, 3, True, 0)
    assert BW.ww_fp_compare_rule(9011, 3, d, _host(digest=d)) == BW.WW_FP_SAME
    assert BW.ww_fp_compare_rule(9010, 3, d, _host(digest=d)) == BW.WW_FP_NO_COMPARE
    view, vd = BW.ww_fp_view_rule(comps, True, 0xDEAD)
    assert view[2] == 0xDEAD and view[:2] == comps[:2] and vd == BW.ww_fp_combine(view) and vd != d
    assert BW.ww_fp_own_digest_rule(d, 9011, 9011) == d and BW.ww_fp_own_digest_rule(d, 9011, 9010) == 0
    book = {}
    assert BW.ww_fp_visit_line_step(book, "k", 1, True) and not BW.ww_fp_visit_line_step(book, "k", 1, True)
    assert BW.ww_fp_visit_line_step(book, "k", 2, True) and not BW.ww_fp_visit_line_step(book, "j", 2, False)


def test_worldtps_the_map_the_minimap_and_the_caps():
    book = {}
    assert BW.ww_tps_line_step(book, 28, 20) and not BW.ww_tps_line_step(book, 28, 20) and BW.ww_tps_line_step(book, 28, 30)
    assert not BW.ww_tps_line_step(book, 20, 20) and not BW.ww_tps_mismatch_rule(0, 20)
    assert BW.ww_tps_apply_step(0, True, False, True, 20) == 20 and BW.ww_tps_apply_step(20, True, False, False, 20) == 0
    assert BW.ww_tps_apply_step(20, False, True, True, 20) == 0 and BW.ww_tps_apply_step(0, True, False, True, 300) == 0
    assert BW.ww_tps_effective_rule(20, 28) == 20 and BW.ww_tps_effective_rule(0, 28) == 28
    assert not BW.ww_full_map_refuse_rule(True, False, False, 9011, False)              # unfrozen: s144 refuses nothing
    assert BW.ww_full_map_refuse_rule(False, True, True, 9011, False)                   # the location pick stays refused
    assert not BW.ww_full_map_refuse_rule(True, True, True, 9011, False)                # a lawful walker on 9011
    assert BW.ww_full_map_refuse_rule(True, True, True, 9002, False) and BW.ww_full_map_refuse_rule(True, True, True, 9011, True)
    assert BW.ww_full_map_coop_close_now_rule(True, True, True, False, False)
    assert not BW.ww_full_map_coop_close_now_rule(True, True, False, False, False)      # a released guest keeps its map
    assert BW.ww_full_map_coop_close_now_rule(True, True, False, True, False)           # ...but not at the ramp
    assert BW.ww_close_map_line_rule(True, True, False, False) and not BW.ww_close_map_line_rule(True, True, True, False)
    assert BW.ww_full_map_dot_rule(True, True, False) == BW.WW_FM_DOT_SHOW and BW.ww_full_map_dot_rule(True, False, False) == BW.WW_FM_DOT_PLACE
    assert BW.ww_full_map_dot_rule(True, True, True) == BW.WW_FM_DOT_HIDE
    assert BW.ww_full_map_dot_place_rule(1, 196.0, 180.0, 0.5, 0.5) == (32.0, 64.0)
    assert BW.ww_full_map_dot_place_rule(0, 200.0, 190.0, 0.5, 0.5) == (50.0, 82.0)
    assert BW.ww_boot_map_rule(False, False) == BW.WW_BOOT_MAP_NONE and BW.ww_boot_map_rule(True, True) == BW.WW_BOOT_MAP_WAIT
    assert BW.ww_boot_map_rule(True, False) == BW.WW_BOOT_MAP_CLOSE
    assert BW.ww_minimap_select_rule(True, True, True, False, False, False) == BW.WW_SEL_COOP_CLOSE
    assert BW.ww_minimap_select_rule(True, True, True, False, True, False) == BW.WW_SEL_STOCK      # a lawful walker keeps stock's cycle
    assert BW.ww_minimap_select_rule(True, True, True, True, False, False) == BW.WW_SEL_STOCK      # an encounter starting
    assert BW.ww_minimap_select_rule(True, True, True, False, False, True) == BW.WW_SEL_STOCK      # `minimap old`
    assert BW.WW_SEL_COOP_CLOSE & BW.WW_SEL_FORBIDDEN == 0 and BW.WW_SEL_COOP_CLOSE & BW.WW_SEL_QUIET
    latch = BW.ww_hint_latch_step(False, False, False, True, False)
    assert latch and BW.ww_hint_latch_step(latch, True, False, False, False)            # a warm return (no new visit) keeps it
    assert not BW.ww_hint_latch_step(latch, True, True, False, False) and not BW.ww_hint_latch_step(True, False, False, True, True)
    assert BW.ww_minimap_hint_quiet_rule(True, True, False) and not BW.ww_minimap_hint_quiet_rule(True, True, True)
    assert BW.ww_own_caps_rule(False) == 3 and BW.ww_own_caps_rule(True) == BW.WW_OWN_CAPS == 1
    said = []
    assert BW.ww_caps_line_step(said, 3, 1) and not BW.ww_caps_line_step(said, 3, 1) and not BW.ww_caps_line_step(said, 1, 3)
    assert BW.ww_caps_line_text(3, 1) == ("the partner's co-op build lacks my world fingerprint (its caps 0x0001, mine 0x0003) -- off for "
                                          "this pair: the older behaviour")
    for k in range(20):
        BW.ww_caps_line_step(said, 0xFF00 | k, 0)
    assert len(said) == BW.WW_CAPS_BOOK_MAX


def test_the_owner_lines_the_world_line_and_the_host_walk_line():
    assert BW.ww_walk_owner_line(BW.WW_WALK_RIDING) == BW.WORDS_WORLD_OUT_RIDES
    assert BW.ww_walk_owner_line(BW.WW_WALK_FP_MISMATCH, BW.WW_FP_MESHES) == (
        "Your world map differs from your partner's (world map meshes): you'll follow them as before.")
    assert BW.ww_walk_owner_line(BW.WW_WALK_FP_MISMATCH, BW.WW_FP_NAME_NONE) == (
        "Your world map differs from your partner's: you'll follow them as before.")
    assert BW.ww_walk_owner_line(BW.WW_WALK_BAND) is None and BW.ww_walk_owner_line(BW.WW_WALK_PAIRING) == BW.WORDS_WW_WALK_PAIRING
    assert BW.ww_world_line_s167_rule(BW.WW_HOST_LINE_LOST, False, True, 11) == BW.WW_HOST_LINE_LOST
    assert BW.ww_world_line_s167_rule(0, True, True, 11) == 0 and BW.ww_world_line_s167_rule(0, False, True, 11) == 10
    assert BW.ww_world_line_s167_rule(0, False, False, 13) == 13
    assert BW.ww_world_line_name_s167(10) == "entry_refused" and BW.ww_world_line_name_s167(9) is None
    assert BW.ww_world_line_name_s167(BW.WW_HOST_LINE_LOST) == "lost"
    guest = _host(caps=BW.WW_OWN_CAPS, flags=BW.WW_FLAG_FOLLOW)
    rule = BW.ww_host_walk_line_rule
    assert rule(False, True, True, True, 9011, 3, guest, 100) == BW.WW_HOST_LINE_OLDER
    g3 = dict(guest, caps=3, state=BW.WW_ST_MISMATCH | BW.WW_ST_FROZEN)
    assert rule(False, True, True, True, 9011, 3, g3, 100) == BW.WW_HOST_LINE_FP_DIFFERS
    cant = dict(guest, caps=3, state=BW.WW_ST_FROZEN, why=0x23)
    assert rule(False, True, True, True, 9011, 3, cant, 100) == BW.WW_HOST_LINE_CANT_WALK
    assert rule(False, True, True, True, 9011, 3, dict(cant, why=0x2C), 100) == BW.WW_HOST_LINE_NONE    # riding: the host knows
    assert rule(True, True, True, True, 9011, 3, guest, 100) == BW.WW_HOST_LINE_NONE
    assert rule(False, True, True, True, 9011, 3, guest, 5000) == BW.WW_HOST_LINE_NONE                  # lost contact owns it
    assert rule(False, True, True, True, 9000, 3, dict(guest, world=9000), 100) == BW.WW_HOST_LINE_NONE


# ================================================================================================ THE ENGINE PINS (by stage)
def _s167_patch_live() -> bool:
    return any(nm.startswith("s167-") and nm not in msr.DEAD for nm in msr.stack())


def _engine_text(file_name: str) -> str:
    """The s167 post-image of ``file_name`` BY STAGE: the s167 patch on the stack (a file the stack creates reads whole; any other file its
    s167 sections' context and added lines), else a clone named by FF9_S167_CLONE carrying the s167 tag; else SKIP (the deployed s166)."""
    if _s167_patch_live():
        try:
            return "\n".join(stack_file(file_name))
        except AssertionError:
            out = []
            for nm in msr.stack():
                if nm.startswith("s167-") and nm not in msr.DEAD:
                    for path, sec in msr.sections((msr.PATCHES / nm).read_bytes()):
                        if path and path.replace("\\", "/").rsplit("/", 1)[-1] == file_name:
                            out += [ln[1:] for ln in sec.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
                                    if ln[:1] in (" ", "+") and not ln.startswith("+++")]
            return "\n".join(out)
    raw = os.environ.get(S167_CLONE_ENV, "").strip()
    root = pathlib.Path(raw) if raw else None
    if root is not None and (root / "Memoria" / "Netsync").is_dir():
        hits = [p for p in root.rglob(file_name) if p.is_file()]
        if hits:
            text = hits[0].read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
            if S167_TAG in text:
                return text
    pytest.skip("the s167 patch is not on this branch's stack (the deployed s166 stage) -- set "
                f"{S167_CLONE_ENV}=<the clone's Assembly-CSharp> to pin a clone that carries the tag")


def _consts(text: str, names: str) -> dict:
    return {m.group(1): int(m.group(2), 0) for m in re.finditer(r"\b(" + names + r")\s*=\s*(0x[0-9A-Fa-f]+|-?\d+)\b(?![.\w])", text)}


def _array(text: str, name: str) -> list:
    m = re.search(name + r"\s*=\s*\{(.*?)\};", text, re.S)
    assert m, name
    body = re.sub(r"//[^\n]*", "", m.group(1))
    return [None if t.strip() == "null" else (int(t.strip(), 0) if re.fullmatch(r"\s*-?\d+\s*", t) else json.loads(t.strip()))
            for t in re.findall(r'"(?:[^"\\]|\\.)*"|null|-?\d+', body)]


def test_s167_the_walk_codes_names_words_and_classes_are_the_engines():
    ww = _engine_text("NetSyncWorldWalk.cs")
    c = _consts(ww, r"Walk(?:Free|Lever|Role|Ramp|Pairing|Encounters|NotLive|Set|OwnMode|Transition|PeerCaps|HostNotWorld|OtherWorld|Band|"
                    r"Riding|HostScene|FpOff|OldPartner|Checking|FpMismatch|FpDry|WhyMax)")
    assert [c[k] for k in ("WalkFree", "WalkLever", "WalkPairing", "WalkFpMismatch", "WalkFpDry", "WalkWhyMax")] == [0, 1, 4, 19, 20, 20]
    assert _array(ww, "WalkNames") == list(BW.WW_WALK_NAMES)
    assert _array(ww, "WalkWords") == list(BW.WW_WALK_WORDS)
    assert _array(ww, r"Byte\[\] WalkClasses") == list(BW.WW_WALK_CLASSES)
    assert _array(ww, r"Byte\[\] WorldOutClasses") == list(BW.WW_WORLD_OUT_CLASSES)
    assert _array(ww, "WorldOutClassNames") == list(BW.WW_WORLD_OUT_CLASS_NAMES)
    assert _array(ww, "WalkClassNames") == list(BW.WW_WALK_CLASS_NAMES)
    body = ww[ww.index("internal static Int32 WalkFreeRule(WalkFacts f)"):]
    body = body[:body.index("\n        }\n")]
    assert re.findall(r"return (Walk\w+);", body)[:len(BW.WW_WALK_RULE_ORDER)] == list(BW.WW_WALK_RULE_ORDER)
    assert "f.Veg" not in body and "PlaneBound" not in body and "VisitorFollowHost" not in body and "HostArrivalAgeMs" not in body


def test_s167_the_entry_fp_caps_and_selection_constants_are_the_engines():
    ww = _engine_text("NetSyncWorldWalk.cs")
    c = _consts(ww, r"Entry(?:None|Location|KitCell|Boat|Ferry|PlaceQuicksand|PlaceIdle|PlaceBoat|LockWorld02|LockWorld10|LineMs|PlaceVar)")
    assert c == {"EntryNone": 0, "EntryLocation": 1, "EntryKitCell": 2, "EntryBoat": 3, "EntryFerry": 4, "EntryPlaceQuicksand": 52,
                 "EntryPlaceIdle": 100, "EntryPlaceBoat": 169, "EntryLockWorld02": 33, "EntryLockWorld10": 35, "EntryLineMs": 4000,
                 "EntryPlaceVar": 24}
    assert _array(ww, "EntryNames") == list(BW.WW_ENTRY_NAMES)
    assert _array(ww, "FpCompNames") == list(BW.WW_FP_COMP_NAMES) and _array(ww, "FpCompWords") == list(BW.WW_FP_COMP_WORDS)
    assert _array(ww, "FpStateNames") == list(BW.WW_FP_STATE_NAMES)
    fp = _consts(ww, r"Fp(?:Same|Off|Old|Checking|Differs|NameNone|NameStale|CheckTimeoutMs|SectionFmt|SectionHead|NoCompare)")
    assert fp == {"FpSame": 0, "FpOff": 1, "FpOld": 2, "FpChecking": 3, "FpDiffers": 4, "FpNameNone": -1, "FpNameStale": -2,
                  "FpCheckTimeoutMs": 10000, "FpSectionFmt": 1, "FpSectionHead": 6, "FpNoCompare": -1}
    assert "internal const Int32 OwnCapsWalk = CapWorldPose | CapWorldFp;" in ww and "CapsBookMax = 16;" in ww
    assert _array(ww, "CapsNames") == list(BW.WW_CAPS_NAMES)
    sel = _consts(ww, r"Sel(?:Stock|HudNoMiniMap|MiniMapOff|NaviOff|ChocoOff|NaviByte|Quiet|CoopClose|Buzz|CountMap|SelectOff|FullMapOff|"
                      r"ControlOn)")
    assert sel == {"SelStock": 0, "SelHudNoMiniMap": 1, "SelMiniMapOff": 2, "SelNaviOff": 4, "SelChocoOff": 8, "SelNaviByte": 0x10,
                   "SelQuiet": 0x20, "SelCoopClose": 0x3F, "SelBuzz": 0x100, "SelCountMap": 0x200, "SelSelectOff": 0x400,
                   "SelFullMapOff": 0x800, "SelControlOn": 0x1000}
    assert _consts(ww, r"FmDot(?:Hide|Place|Show)|BootMap(?:None|Close|Wait)") == {
        "FmDotHide": 0, "FmDotPlace": 1, "FmDotShow": 2, "BootMapNone": 0, "BootMapClose": 1, "BootMapWait": 2}
    assert _consts(ww, r"WorldLineEntry|HostLineCantWalk|HostLineOlder|HostLineFpDiffers") == {
        "WorldLineEntry": 10, "HostLineCantWalk": 11, "HostLineOlder": 12, "HostLineFpDiffers": 13}
    assert _array(ww, "S167LineNames") == list(BW.WW_S167_LINE_NAMES)
    state = re.search(r"\bconst (?:Byte|Int32) SectionFp = (\d+);", _engine_text("NetSyncState.cs"))
    assert state and int(state.group(1)) == BW.SECTION_FP == 11


def test_s167_the_owner_words_are_the_engines():
    ww = _engine_text("NetSyncWorldWalk.cs")
    lines = dict(re.findall(r'internal const String (Line\w+) = "((?:[^"\\]|\\.)*)";', ww))
    assert {k: lines[k] for k in ("LineEntryRefused", "LineWalkPairing", "LineWalkChecking", "LineWalkOlder", "LineHostFpDiffers",
                                  "LineHostCantWalk", "LineHostOlder", "LineCloseMap")} == {
        "LineEntryRefused": BW.WORDS_WW_ENTRY_REFUSED, "LineWalkPairing": BW.WORDS_WW_WALK_PAIRING,
        "LineWalkChecking": BW.WORDS_WW_WALK_CHECKING, "LineWalkOlder": BW.WORDS_WW_WALK_OLDER,
        "LineHostFpDiffers": BW.WORDS_WW_HOST_FP_DIFFERS, "LineHostCantWalk": BW.WORDS_WW_HOST_CANT_WALK,
        "LineHostOlder": BW.WORDS_WW_HOST_OLDER, "LineCloseMap": BW.WORDS_WW_CLOSE_MAP}
    assert '"world speed differs: my [Graphics] WorldTPS is " + own + ", the partner\'s " + peer' in ww


def test_s167_the_log_lines_are_the_engines():
    field = _engine_text("NetSyncField.cs")
    client = _engine_text("NetSyncClient.cs")
    assert '": the guest walks its own copy on foot (the host on foot on this world map; entering a location stays the host\'s)"' in field
    assert ": travel input held -- the walk waits (" in field and '"[NetSync] world walk FROZEN ("' in field
    assert '" will speak once more; a warm battle return never re-arms)"' in field
    assert '"[NetSync] world map: the full map opens for the walking guest on world map "' in field
    assert '" straight to no minimap -- no buzz, control untouched, Select opens it again; s165\'s minimap hint stays quiet for this"' in field
    assert '"world entrance (" + HarnessEntryLastName + ")"' in field
    assert '"[NetSync] host world: the partner\'s walk -- "' in client
    assert ' -- the walk stays frozen until both are ready"' in client


def test_s167_the_verb_is_the_engines():
    client = _engine_text("NetSyncClient.cs")
    lits = set(_LIT.findall(client))
    usage = [s for s in lits if s.startswith("netsync worldwalk: expected kitcell")]
    assert usage and BW.WORLDWALK_USAGE_S167 in [u.replace('\\"', '"') for u in usage] or any(
        BW.WORLDWALK_USAGE_S167.startswith(u) for u in usage), usage
    flat = client.replace('"\n', "").replace("\n", " ")
    for (op, word), ack in BW.WORLDWALK_B_ACKS.items():
        head = f"[NetSync] harness: worldwalk {op} {word}"
        assert head in client, (op, word)
        if " -- " in ack:
            tail = ack.split(" -- ", 1)[1]
            assert tail.replace('"', '\\"') in client or tail[:60].replace('"', '\\"') in client, (op, word)
    assert BW.LOG_WORLDWALK_CLEAR_S167[len(BW.LOG_WORLDWALK_CLEAR_A4):].lstrip(", ") in flat or \
        "the walk is on, the bench pairs as act" in client


def _catch_netsync() -> dict:
    agent = _engine_text("HarnessAgent.cs")
    lines = agent.split("\n")
    catch = [ln for ln in lines if re.search(r'outer\.Append\("\\"netsync\\":\{\\"enabled', ln)]
    head = [ln for ln in lines if 'NetsyncF3Retired = "' in ln]
    tail = [ln for ln in lines if re.search(r'\+ "\\"align_win', ln)]
    if not (catch and head and tail):
        pytest.skip("this s167 HarnessAgent carries no catch literal lines")
    a, b = _LIT.findall(catch[0])
    pinned = "".join(_LIT.findall(head[0]) + _LIT.findall(tail[0]))
    return json.loads("{" + (a + pinned + b).replace('\\"', '"') + "}")["netsync"]


def test_s167_the_catch_line_carries_walk_fp_and_the_lane_keys_at_their_sentinels():
    """THE CATCH LITERAL IS PART OF EVERY KEY ADDITION: `walk` then `fp` LAST in `netsync.world`, the lane's s167 keys in place."""
    world = _catch_netsync()["world"]
    assert list(world)[-2:] == ["walk", "fp"], list(world)
    assert json.dumps(world["walk"]) == json.dumps(BW.WORLD_WALK_SENTINELS)
    assert json.dumps(world["fp"]) == json.dumps(BW.WORLD_FP_SENTINELS)
    assert json.dumps(world["lane"]) == json.dumps(BW.WORLD_SENTINELS_S167["lane"])
    assert json.dumps(world) == json.dumps(BW.WORLD_SENTINELS_S167)


def test_s167_the_agents_live_keys_are_the_catch_lines_and_read_the_live_caps():
    agent = _engine_text("HarnessAgent.cs")

    def keys(method):
        i = agent.index(f"private static void {method}(StringBuilder sb)")
        body = agent[i:agent.index("\n        }\n", i)]
        return re.findall(r'(?:Str|Num|Bool)\(sb, "(\w+)"|\\"(\w+)\\":[\[{]', body)
    walk = [a or b for a, b in keys("AppendWorldWalk")]
    assert walk == ["walk"] + [k for k in BW.WORLD_WALK_SENTINELS if k != "map"]   # its own head first; `map` is AppendWorldWalkMap's
    assert re.search(r"AppendWorldWalkMap\(sb\);[^\n]*\n\s*sb\.Append\(\"}\"\);", agent)   # ...walk's LAST key
    assert [a or b for a, b in keys("AppendWorldWalkMap")] == ["map"] + list(BW.WORLD_WALK_MAP_SENTINELS)
    fp = [a or b for a, b in keys("AppendWorldFp")]
    assert [k for k in fp if k in BW.WORLD_FP_SENTINELS and k not in ("lines",)][:6] == list(BW.WORLD_FP_SENTINELS)[:6]
    assert 'Num(sb, "own", ownCaps);' in agent and "Memoria.Netsync.NetSyncClient.WorldOwnCapsNow" in agent


def test_s167_every_sender_speaks_the_live_caps_word():
    """The own-wire line, the relay keepalive and the trailer read OwnCapsRule's LIVE word (0x0003; 0x0001 under `fp off`); the one-argument
    KeepaliveTrailer keeps s166's 0x0001 (round A's proof rows) -- the kit's twins: log_own_wire over 3, coop_peer's keepalive_trailer."""
    client = _engine_text("NetSyncClient.cs")
    assert re.search(r"NetSyncWorldWalk\.OwnWireLine\([^;]*NetSyncWire\.Version, WorldOwnCapsNow\)\);", client)
    assert "NetSyncWire.KeepaliveTrailer(NetSyncWirePeer.OwnWorldTps(), NetSyncWorldFpArmed.OwnCapsNow)" in _engine_text("NetSyncRelay.cs")
    sock = _engine_text("NetSyncSocket.cs")
    assert "return KeepaliveTrailer(worldTps, NetSyncWorldWalk.OwnCaps);" in sock
    ww = _engine_text("NetSyncWorldWalk.cs")
    assert "internal static Int32 OwnCapsNow { get { return NetSyncWorldWalk.OwnCapsRule(Off); } }" in ww
    assert re.fullmatch(BW.OWN_WIRE_RE, BW.log_own_wire("the relay", 15, BW.ww_own_caps_rule(False))).groups() == ("15", "0003", "the relay")
    assert CP.parse_world_trailer(CP.build_pos_payload(CP.FIELD_SENTINEL, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0)
                                  + CP.keepalive_trailer(20, BW.ww_own_caps_rule(False)))["caps"] == 3


def test_s167_the_proof_and_the_overlay_selftest_tallies_are_the_sources():
    """The proof's (rows, mutants) DERIVED from the s167 source equal the fallback the stand-in keeps (BW.WORLD_WALK_PROOF_S167); the
    overlay text selftest's rows (OvlRow sites) equal BW.overlay_text_selftest_rows(167)."""
    ww = _engine_text("NetSyncWorldWalk.cs")
    assert BW.world_walk_proof_counts(ww) == BW.WORLD_WALK_PROOF_S167
    client = _engine_text("NetSyncClient.cs")
    i = client.index("internal static Boolean OverlayTextSelfTest(")
    body = client[i:client.index("\n        }\n", i)]
    assert len(re.findall(r"(?<![\w.])OvlRow\(", body)) == BW.overlay_text_selftest_rows(167)        # the body's OvlRow call sites
    assert "static void OvlRow(" not in body and "static Boolean OvlRow(" not in body


# ================================================================================================ THE STAND-IN (stepped by hand)
def _root():
    t = pathlib.Path(tempfile.mkdtemp(prefix="ww_b_"))
    (t / "x64").mkdir()
    (t / "x64" / "FF9.exe").write_bytes(b"MZ")
    (t / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    return t


def _fake(*, pieces=FG.FAKE_WORLD_WALK_S167_PIECES, faults=(), kit=False) -> FakeGame:
    f = FakeGame(_root(), render_fps=30.0)
    f.swap_qpc = None
    f.dir.mkdir(parents=True, exist_ok=True)
    (f.dir / "arm").write_text("", encoding="utf-8")
    f.armed = True
    f.state_every = 1 << 30
    f.wf_follow_host_cfg = True
    f.world_walk_pieces = tuple(pieces)
    f.world_walk_faults = set(faults)
    f.overworld = {"speed": 2.0, "turn": 2.8125, "cam": 0.0, "lag": 1}
    if kit:
        f.world_kit = dict(FG.FAKE_WORLD_KIT)
    f.field_id, f.ui_state, f.control = 6603, "FieldHUD", True
    return f


def _step(f, n=1):
    for _ in range(int(n)):
        f._frame_once()


def _ww(f, *args):
    f._netsync(["worldwalk", *[str(a) for a in args]])


def _world(f) -> dict:
    return f._netsync_doc()["world"]


def _walk(f) -> dict:
    return _world(f)["walk"]


def _lines(f, needle) -> list:
    return [ln.split("|M| ", 1)[-1] for ln in (f.game_path / "Memoria.log").read_text(encoding="utf-8").splitlines() if needle in ln]


def _bench(f, *, world=9011, x=68.0, z=-444.0, path=("70", "-444", "24")):
    """W-FREE's setup on the selftest role: the bench, a field, the world map, BOTH bench hosts (`worldfollow host self` for section 7,
    `worldwalk host path` for the trailer)."""
    f._netsync(["selftest", "1"])
    f._netsync(["bench", "1"])
    _step(f, 4)
    f.enter_world(world, x, z)
    _step(f, 4)
    f._netsync(["worldfollow", "host", "self"])
    _ww(f, "host", "path", *path)
    _step(f, 10)


def _walk_up(f, frames=30) -> float:
    x0 = f.world["x"]
    f._schedule("up", frames)
    _step(f, frames + 2)
    return abs(f.world["x"] - x0)


def test_the_default_stand_in_is_the_deployed_s166():
    """THE DEFAULT STAYS s166 until the bench legs re-key: no `walk` / `fp`, caps own 1, the s166 usage line."""
    f = _fake(pieces=FG.FAKE_WORLD_WALK_PIECES)
    world = _world(f)
    assert "walk" not in world and "fp" not in world and world["lane"]["caps"]["own"] == BW.WW_OWN_CAPS == 1
    assert FG.FAKE_WORLD_WALK_S166_BUILD == FG.FAKE_WORLD_WALK_PIECES and "b" not in FG.FAKE_WORLD_WALK_PIECES
    with pytest.raises(RuntimeError) as err:
        _ww(f, "walk", "off")
    assert str(err.value) == BW.WORLDWALK_USAGE_A4


def test_the_s167_stand_in_publishes_round_bs_keys_in_the_agents_order_at_rest():
    f = _fake()
    world = _world(f)
    assert list(world) == list(BW.WORLD_SENTINELS_S167)
    assert {k: list(v) for k, v in world.items() if isinstance(v, dict)} == {k: list(v) for k, v in BW.WORLD_SENTINELS_S167.items()}
    assert list(world["walk"]["map"]) == list(BW.WORLD_WALK_MAP_SENTINELS) and list(world["fp"]) == list(BW.WORLD_FP_SENTINELS)
    assert world["lane"]["caps"]["own"] == BW.WW_OWN_CAPS_WALK == 3
    assert world["walk"]["lever"] == "on" and world["walk"]["why_code"] == -1 and world["fp"]["lever"] == "act"
    assert world["lane"]["world_tps"]["lever"] == "report"


def test_w_free_walks_and_walk_off_is_s166_exactly():
    """W-FREE: both bench hosts, fp ready and equal -> `walk.free`, `freeze.on` still true, x moves, one FREE line, the trailer's b1 and
    why 0; `walk off` = the s166 freeze (FROZEN (lever), x unmoved, b1 clear, s166's raw why byte)."""
    f = _fake()
    _bench(f)
    w = _walk(f)
    world = _world(f)
    assert w["free"] and w["why"] is None and world["freeze"]["on"] and world["fp"]["state"] == "match" and world["fp"]["ready"]
    assert w["held_trailer"] and w["held_state"] and w["held_b6"] and w["frees"] == 1
    assert _walk_up(f) > 20.0
    assert world["lane"]["tx"]["state"] & BW.WW_ST_WALKING and world["lane"]["tx"]["why"] == 0
    assert len(_lines(f, BW.LOG_WW_WALK_FREE)) == 1
    _ww(f, "walk", "off")
    _step(f, 2)
    assert _walk(f)["why"] == "lever" and _walk_up(f) == 0.0
    tx = _world(f)["lane"]["tx"]
    assert not tx["state"] & BW.WW_ST_WALKING and not str(tx["why_name"]).startswith("walk:")   # s166's raw world-out byte
    assert _lines(f, "world walk FROZEN (lever)")


def test_w_refuse_each_term_freezes_with_its_why():
    cases = [(("hostworld", "9010"), "other_world"), (("hostmode", "1"), "riding"), (("hoststate", "0x40"), "host_scene"),
             (("pair", "unmirrored"), "pairing"), (("fp", "fake", "0xDEAD"), "fp_mismatch")]
    for op, why in cases:
        f = _fake()
        _bench(f)
        _ww(f, *op)
        _step(f, 12)
        assert _walk(f)["why"] == why, (op, _walk(f))
        assert _walk_up(f, 10) == 0.0, op
    f = _fake()
    _bench(f)
    f._netsync(["worldfollow", "host", "nob6"])
    _step(f, 4)
    assert _walk(f)["why"] == "host_not_world"
    f = _fake()
    _bench(f)
    f.world["vehicle"] = 6
    _step(f, 2)
    assert _walk(f)["why"] == "own_mode"


def test_w_refuse_fp_names_the_meshes_on_the_line_and_the_log():
    f = _fake()
    _bench(f)
    _ww(f, "fp", "fake", "dead")
    _step(f, 6)
    w, fp = _walk(f), _world(f)["fp"]
    assert w["line"] == "Your world map differs from your partner's (world map meshes): you'll follow them as before."
    assert fp["state"] == "mismatch" and fp["named"] == "meshes" and fp["lever"] == "fake" and fp["fake"] == "0x0000DEAD"
    assert fp["own"] != fp["real"] and fp["host_section"]["set"] and fp["host_section"]["mask"] == 0x3F
    assert _world(f)["lane"]["tx"]["state"] & BW.WW_ST_MISMATCH
    assert len(_lines(f, BW.LOG_WW_FP_MISMATCH)) == 1 and fp["lines"]["mismatch"] == 1
    _step(f, 30)
    assert _world(f)["fp"]["lines"]["mismatch"] == 1                    # once per visit


def test_w_stale_hostseq_freeze_keeps_walking_and_a_world_reload_drops_the_hold():
    f = _fake()
    _bench(f)
    _ww(f, "hostseq", "freeze")
    _step(f, 75)                                                        # 2.5 s of re-sends: Valid all along, the hold refreshed
    assert _walk(f)["free"] and _walk_up(f, 10) > 0.0
    _ww(f, "hostseq", "run")
    _ww(f, "hostgap", "8000")                                           # arrivals stop: past StaleMs the receiver reads Valid = false
    _step(f, 120)                                                       # 4 s: Valid for StaleMs (2 s), then 2 s stale
    w, lane = _walk(f), _world(f)["lane"]
    # `held_age_ms` is the age of the hold's last take (every VALID Update re-takes it: the engine's "ms since THE HOLD took the host's
    # trailer"), so it counts from the StaleMs cliff, never from the last arrival
    assert lane["arrival_age_ms"] >= 3500 and 1500 <= w["held_age_ms"] <= lane["arrival_age_ms"] - 1500, (lane["arrival_age_ms"], w)
    assert w["free"] and w["held_trailer"]                              # THE STALL HOLD: staleness never freezes
    drops = w["held_drops"]
    f._world_load("WorldHUD", camera=False)
    _step(f, 2)
    w = _walk(f)
    assert w["held_drops"] == drops + 1 and not w["held_trailer"] and not w["free"] and w["why"] == "peer_caps"


def test_w_entry_buzzes_once_per_press_at_a_location_and_refuse_silent_is_s166():
    f = _fake()
    f.world_locations = {300: (1197.37, -796.7, 3.0)}
    _bench(f, x=1197.37, z=-796.7, path=("1190", "-796", "24"))
    f._execute(["press", "confirm", "30"])
    _step(f, 34)
    w = _walk(f)
    assert w["entry_refused"] == 1 and w["last_reader"] == 1 and w["last_place"] == 4 and w["last_entry"] == "location"
    assert w["last_world"] == 9011 and f.ui_state == "WorldHUD" and _world(f)["line"]["asked"] == "entry_refused"
    assert len(_lines(f, "an entrance press (location: reader entry 1, place 4)")) == 1
    _ww(f, "refuse", "silent")
    f._execute(["press", "confirm", "2"])
    _step(f, 6)
    assert _walk(f)["entry_refused"] == 1 and f.ui_state == "WorldHUD"


@pytest.mark.parametrize("order", ["e0", "e1"])
def test_w_kitcell_one_buzz_on_the_trigger_under_either_reader_order(order):
    f = _fake(kit=True)
    if order == "e1":
        f.world_kit_order = FG.FAKE_WORLD_KIT_ORDER_E1_FIRST
    _bench(f, x=BW.KIT_6603_TRIGGER[0], z=BW.KIT_6603_TRIGGER[1], path=("79", "-444", "0"))
    f._execute(["press", "confirm", "2"])
    _step(f, 6)
    w = _walk(f)
    # one press, read by entry 0 (the cell) AND entry 1 (the kit place's poll): ONE buzz whichever reads first (the KeyTick dedupe)
    want = (0, "kit_cell") if order == "e0" else (1, "location")
    assert w["entry_refused"] == 1 and (w["last_reader"], w["last_entry"]) == want and f.ui_state == "WorldHUD"
    assert not _lines(f, "world kit-cell close")                       # control ON: the buzz, never A0's control-off close


def test_the_round_b_faults_turn_their_rows_red():
    def run(fault, setup, check):
        f = _fake(faults=(fault,), kit=True)
        setup(f)
        return check(f)
    on_trigger = lambda f: _bench(f, x=BW.KIT_6603_TRIGGER[0], z=BW.KIT_6603_TRIGGER[1], path=("79", "-444", "0"))  # noqa: E731

    def press(f):
        on_trigger(f)
        f._execute(["press", "confirm", "2"])
        _step(f, 6)
    assert run("refuse_overfire", press, lambda f: _walk(f)["entry_refused"]) >= 2          # one buzz per READ
    assert run("refuse_silent", press, lambda f: _walk(f)["entry_refused"]) == 0
    assert run("refuse_leak", press, lambda f: f._wt["exit"] is not None or f.ui_state != "WorldHUD")   # the press reaches the script
    assert not run("refuse_silent", press, lambda f: f._wt["exit"] is not None or f.ui_state != "WorldHUD")  # silent: still masked

    def ride(f):
        _bench(f)
        _ww(f, "hostmode", "1")
        _step(f, 6)
    assert run("walk_unlawful", ride, lambda f: _walk(f)["free"])
    assert run("fp_ignored", lambda f: (_bench(f), _ww(f, "fp", "fake", "1"), _step(f, 6)), lambda f: _walk(f)["free"])
    assert run("pairing_free", lambda f: (_bench(f), _ww(f, "pair", "unmirrored"), _step(f, 4)), lambda f: _walk(f)["free"])

    def vehicle(f):
        _bench(f)
        f.world["vehicle"] = 6
        _step(f, 2)
    assert run("ownmode_free", vehicle, lambda f: _walk(f)["free"])


def test_the_visit_re_arms_the_decline_lines_and_a_warm_return_does_not():
    f = _fake()
    _bench(f)
    f._execute(["press", "confirm", "2"])
    _step(f, 6)
    assert _lines(f, "world script button-poll") and _walk(f)["visits"] == 1
    f._world_load("WorldHUD", reinit="stock", camera=False)            # a warm battle return: the same visit
    _step(f, 2)
    assert _walk(f)["rearms"] == 0 and _walk(f)["visits"] == 1
    f.ui_state, f.field_id = "FieldHUD", 300
    _step(f, 2)
    f.enter_world(9011, 70.0, -444.0)
    _step(f, 2)
    assert _walk(f)["visits"] == 2 and _walk(f)["rearms"] == 1 and _lines(f, BW.LOG_WW_DECLINE_REARMED)
    g = _fake(faults=("decline_stale",))
    _bench(g)
    g._execute(["press", "confirm", "2"])
    _step(g, 6)
    g.ui_state, g.field_id = "FieldHUD", 300
    _step(g, 2)
    g.enter_world(9011, 70.0, -444.0)
    _step(g, 2)
    assert _walk(g)["rearms"] == 0                                      # the fault: never re-armed


def test_w_minimap_a_frozen_guests_select_closes_it_and_the_hint_latches_for_the_visit():
    f = _fake()
    _bench(f, world=9002, x=300.0, z=-300.0, path=("302", "-300", "0"))
    f.world_hud_state, f.world_navi = "HUD", 1
    f._execute(["press", "select", "1"])
    _step(f, 3)
    w = _walk(f)
    assert f.world_hud_state == "HUDNoMiniMap" and w["minimap_closes"] == 1 and w["hint_quiet"]
    assert _world(f)["freeze"]["map"] == 0 and _lines(f, BW.LOG_WW_MINIMAP_CLOSED)
    f._world_load("WorldHUD", reinit="stock", camera=False)            # a warm return keeps the latch
    _step(f, 2)
    assert _walk(f)["hint_quiet"]
    f.ui_state, f.field_id = "FieldHUD", 300
    _step(f, 2)
    f.enter_world(9002, 300.0, -300.0)
    _step(f, 2)
    assert not _walk(f)["hint_quiet"]                                   # a NEW visit clears it
    g = _fake(faults=("minimap_strand",))
    _bench(g, world=9002, x=300.0, z=-300.0, path=("302", "-300", "0"))
    g.world_hud_state, g.world_navi = "HUD", 1
    g._execute(["press", "select", "1"])
    _step(g, 3)
    assert g.world_hud_state == "HUD" and _world(g)["freeze"]["map"] == 1   # the fault: s166's stranded cycle
    h = _fake()
    _bench(h, world=9002, x=300.0, z=-300.0, path=("302", "-300", "0"))
    _ww(h, "minimap", "old")
    h.world_hud_state, h.world_navi = "HUD", 1
    h._execute(["press", "select", "1"])
    _step(h, 3)
    assert h.world_hud_state == "HUD" and _walk(h)["minimap_closes"] == 0


def test_w_map_a_lawful_walker_opens_the_full_map_on_9011_only():
    f = _fake()
    _bench(f)
    f.world_hud_state, f.world_navi = "HUD", 1
    assert _walk(f)["map"]["lawful"]
    f._execute(["press", "select", "1"])
    _step(f, 3)
    assert f.world_hud_state == "FullMap" and _walk(f)["map"]["opens"] == 1 and _world(f)["freeze"]["map"] == 0
    g = _fake()
    _bench(g)
    _ww(g, "fullmap", "old")
    g.world_hud_state, g.world_navi = "HUD", 1
    _ww(g, "minimap", "old")
    g._execute(["press", "select", "1"])
    _step(g, 3)
    assert g.world_hud_state == "HUD" and _world(g)["freeze"]["map"] == 1   # `fullmap old` + `minimap old`: s166's refusal


def test_w_tps_one_line_per_pair_and_tps_apply_holds_the_host_value_at_a_world_load():
    f = _fake()
    f.world_tps = 28
    _bench(f)
    _ww(f, "hosttps", "20")
    _step(f, 6)
    tps = _world(f)["lane"]["world_tps"]
    assert tps["mismatch"] and tps["lines"] == 1 and tps["effective"] == 28 and len(_lines(f, "world speed differs")) == 1
    _ww(f, "tps", "apply")
    f._world_load("WorldHUD", camera=False)
    _step(f, 2)
    tps = _world(f)["lane"]["world_tps"]
    assert tps["held"] == 20 and tps["effective"] == 20 and tps["lever"] == "apply"


def test_the_proof_and_overlay_lines_by_stage(monkeypatch, tmp_path):
    d = tmp_path / "Assembly-CSharp" / "Memoria" / "Netsync"
    d.mkdir(parents=True)
    rows = "\n".join("            row(r, \"x\");" for _ in range(7))
    (d / "NetSyncWorldWalk.cs").write_text(f"// {S167_TAG} stand-in\nprivate static Int32 Rows(Rules r, List<String> fails)\n{{\n{rows}\n}}\n"
                                           "private static Rules Mutant(String name) { }\n"
                                           'private static readonly String[] MutantNames = { "m0", "m1" };\n', encoding="utf-8")
    monkeypatch.setenv(S167_CLONE_ENV, str(tmp_path / "Assembly-CSharp"))
    assert FG.world_walk_proof_tallies(FG.FAKE_WORLD_WALK_S167_PIECES) == (7, 2)
    monkeypatch.setenv(S167_CLONE_ENV, "")
    if not any(p.name.startswith("s167-") for p in (REPO / "memoria-patches").glob("*.patch")):
        assert FG.world_walk_proof_tallies(FG.FAKE_WORLD_WALK_S167_PIECES) == BW.WORLD_WALK_PROOF_S167
    assert BW.overlay_text_selftest_rows(166) == BW.OVERLAY_TEXT_SELFTEST_ROWS == 50 and BW.overlay_text_selftest_rows(167) == 58


def test_the_round_b_levers_release_with_the_harness_and_clear_says_the_s167_line():
    f = _fake()
    _bench(f)
    for op in (("walk", "off"), ("refuse", "silent"), ("stallhold", "old"), ("decline", "old"), ("fp", "off"), ("tps", "apply"),
               ("minimap", "old"), ("fullmap", "old"), ("pair", "unmirrored")):
        _ww(f, *op)
    w = _walk(f)
    assert (w["lever"], w["refuse"], w["stallhold"], w["decline"], w["minimap"], w["map"]["lever"], w["pair"]) == (
        "off", "silent", "old", "old", "old", "old", "unmirrored")
    assert _world(f)["lane"]["caps"]["own"] == 1                        # `fp off`: s166's word
    _ww(f, "clear")
    w = _walk(f)
    assert (w["lever"], w["refuse"], w["stallhold"], w["decline"], w["minimap"], w["map"]["lever"], w["pair"]) == (
        "on", "act", "act", "act", "act", "act", "act")
    assert _lines(f, "worldwalk clear")[-1] == BW.LOG_WORLDWALK_CLEAR_S167
    with pytest.raises(RuntimeError) as err:
        _ww(f, "fp", "fake", "xyz")
    assert str(err.value) == BW.WORLDWALK_USAGE_S167


# ================================================================================================ COOP_PEER (the s167 wire)
def _host_frame(caps, digest=0x1234ABCD, place=4):
    return CP.parse_frame(CP.build_pos_frame(0, wire=15, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0,
                                             trailer=CP.build_world_trailer(caps=caps, place=place, world=9011 if place == 4 else 0,
                                                                            pos=(68.0, 0.0, -444.0), rot=(0.0, 0.0, 0.0, 1.0),
                                                                            digest=digest)))[1]


def _sent(m, now=1.0):
    return CP.parse_world_trailer(CP.parse_frame(m.outgoing(now, 15)[0])[1])


def test_serve_guest_speaks_the_hosts_caps_and_echoes_its_digest():
    walk = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0))
    walk.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S167), 0.0)
    tr = _sent(walk)
    assert tr["caps"] == 3 and tr["digest"] == 0x1234ABCD and tr["state"] & CP.ST_WALKING and tr["place"] == CP.PLACE_WORLD
    old_host = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0))
    old_host.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S166, digest=0), 0.0)
    assert _sent(old_host)["caps"] == 1 and _sent(old_host)["digest"] == 0       # an s166 host: s166's word, no digest
    s166 = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0), caps=1)
    s166.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S167), 0.0)
    assert _sent(s166)["caps"] == 1 and _sent(s166)["digest"] == 0               # `--caps 1`: an s166-shaped guest
    pinned = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0), digest=0xBEEF)
    pinned.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S167), 0.0)
    assert _sent(pinned)["digest"] == 0xBEEF
    mirrored = CP.GuestModel()
    mirrored.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S167), 0.0)
    tr = CP.parse_world_trailer(CP.parse_frame(mirrored.outgoing(1.0, 15)[0])[1])
    assert tr["caps"] == 3 and tr["digest"] == 0                                 # place 0 / 1 carries no digest
    assert CP.keepalive_trailer(20, 3)[1:3] == bytes([3, 0]) and CP.keepalive_trailer(20)[1:3] == bytes([1, 0])
    args = CP.build_parser().parse_args(["serve-guest", "--caps", "1", "--digest", "0xdead", "--walk-why", "pairing"])
    assert args.caps == 1 and args.digest == 0xDEAD and args.walk_why == "pairing"


def test_serve_guests_walk_why_is_gated_as_the_engine_gates_it():
    b1 = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0, state=0x85), walk_why=BW.WW_WALK_PAIRING)
    b1.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S167), 0.0)
    assert _sent(b1)["why"] == 0x23                                       # both words b1: the walk's class
    s166 = CP.GuestModel(walk=CP.WorldWalkPlan(out_s=0.0, load_s=0.0, state=0x85), walk_why=BW.WW_WALK_PAIRING)
    s166.on_host_frame(CP.TYPE_POS, _host_frame(CP.CAPS_S166, digest=0), 0.0)
    assert _sent(s166)["why"] == 0                                        # an s166 host: s166's raw world-out byte
    host_line = BW.ww_host_walk_line_rule(False, True, True, True, 9011, 3, BW.ww_trailer_of(_sent(b1)), 100)
    assert host_line == BW.WW_HOST_LINE_CANT_WALK


def test_section_11_on_a_host_record_where_pose_names_it_and_the_digest(tmp_path, capsys):
    comps = [0x5355, 11, 22, 33, 44, 55]
    tap = CP.TapeWriter(tmp_path / "s167.f9tape", mode="test", clock=lambda: 0.0)
    story = CP.story_with_pose(68.0, -444.0, idx=11)
    state = BW.append_section(b"", BW.SECTION_STORY, story) + CP.fp_section_bytes(9011, comps)
    state = BW.append_section(state, BW.SECTION_DIALOG, BW.dialog_section(0x0165, 3, BW.HF_WORLD | BW.HF_CONTROL))
    tap.write(CP.DIR_HOST, CP.build_pos_frame(0, wire=15, rot=(0.0, 0.0, 0.0, 1.0), anim_frame=0, frame_n=0,
                                              trailer=CP.build_world_trailer(caps=3, place=4, world=9011, pos=(68.0, 0.0, -444.0),
                                                                             rot=(0.0, 0.0, 0.0, 1.0), digest=0xABCD1234)), t=0.0)
    frame = CP.build_frame(CP.TYPE_STATE, state, wire=15)
    tap.write(CP.DIR_HOST, frame, t=0.01)
    tap.close()
    rows = CP.tape_poses(CP.read_tape(tmp_path / "s167.f9tape")[1])
    assert rows[0]["fp"] == {"world": 9011, "lang": "US", "comps": comps, "mask": 0x3F} and rows[0]["pose"]["x"] == 68.0
    assert CP.main(["where", str(tmp_path / "s167.f9tape"), "--pose", "--every", "0"]) == 0
    out = capsys.readouterr().out
    assert "caps 0x0003" in out and "digest 0xABCD1234" in out and "s11 world 9011 lang US mask 0x3F" in out
    assert "1 with section 11" in out
    rep = CP.Replayer([], start=0.0, send=lambda *a: None, log=lambda *a: None, wire=15)
    assert rep.stamped(frame) == frame                                  # an s167 tape's section 11 passes byte for byte
    v14 = CP.restamp(frame, 14)
    assert CP.restamp(v14, 15) == frame and CP.fp_section_of(CP.parse_frame(v14, versions=(14,))[1]) == rows[0]["fp"]


# ================================================================================================ the remaining faults, the co-op close, the proof block
def test_the_stall_hole_holds_a_world_paired_guests_freeze_and_stall_free_lifts_it():
    """Decision 17: a following client's lane stalls on the world map (SpectatorField falls: the lane invalid, its socket up, seen live) --
    the held session keeps the freeze (`freeze.why` "session", `walk.stall_held`); `stallhold old` is s166's lift; the `stall_free` fault
    turns the row red."""
    def run(faults=(), lever=None):
        f = _fake(faults=faults)
        f.follow_session(0, flags=BW.HF_WORLD)
        f.enter_world(9011, 70.0, -444.0)
        _step(f, 4)
        assert _world(f)["freeze"]["on"] and _world(f)["freeze"]["why"] != BW.WORLD_FREEZE_WHY_SESSION
        if lever:
            _ww(f, "stallhold", lever)
        f.coop_follow["valid"] = False                                  # the stall: the lane stale, the socket up
        _step(f, 4)
        return _walk(f), _world(f)["freeze"]
    w, fr = run()
    assert w["session_held"] and w["stall_held"] and fr["on"] and fr["why"] == BW.WORLD_FREEZE_WHY_SESSION
    w, fr = run(lever="old")
    assert w["session_held"] and not w["stall_held"] and not fr["on"]   # s166: a stall lifts the freeze
    w, fr = run(faults=("stall_free",))
    assert not w["stall_held"] and not fr["on"]                         # the fault: the hole stays open


def test_hint_nag_forgets_decision_28s_latch_and_the_co_op_close_never_sets_it():
    """Decision 28: a frozen guest's Select close latches the hint quiet for the visit (the `hint_nag` fault forgets it). The engine's
    co-op close (CoopCloseFullMap: CloseFullMapBySelect + the [100] write, never NoteMinimapSelectClose) closes the map with NO latch --
    here at the session's exit ramp on the live world map (anyone's map), counted with its line."""
    for faults, quiet in (((), True), (("hint_nag",), False)):
        f = _fake(faults=faults)
        _bench(f, world=9002, x=300.0, z=-300.0, path=("302", "-300", "0"))
        f.world_hud_state, f.world_navi = "HUD", 1
        f._execute(["press", "select", "1"])
        _step(f, 3)
        assert f.world_hud_state == "HUDNoMiniMap" and _walk(f)["minimap_closes"] == 1 and _walk(f)["hint_quiet"] is quiet, faults
    f = _fake()
    _bench(f)
    f.world_hud_state, f.world_navi = "HUD", 1
    f._execute(["press", "select", "1"])                               # a lawful walker on 9011: the full map opens
    _step(f, 3)
    assert f.world_hud_state == "FullMap" and _walk(f)["map"]["opens"] == 1
    f.unfollow()                                                        # the session ends: the exit ramp's world load
    m = _walk(f)
    assert f.world_hud_state == "HUDNoMiniMap" and m["map"]["coop_closes"] == 1 and m["map"]["last_close"] == "ramp"
    assert not m["hint_quiet"] and m["minimap_closes"] == 0              # the co-op close never latches the hint
    assert _lines(f, BW.LOG_WW_MAP_CLOSED)[-1] == BW.log_ww_map_closed("ramp", 9011)
    g = _fake()
    _bench(g)
    _ww(g, "fullmap", "old")
    g.world_full_map = True
    g.unfollow()
    assert _walk(g)["map"]["coop_closes"] == 0                          # `fullmap old`: s166, no close


def test_the_s167_stand_ins_proof_block_carries_round_bs_tallies_by_stage():
    """The proof block BY STAGE: the s167 stand-in's overlay text line reads 58 rows and its world walk line round B's tallies (the s167
    source's, else the W1 clone's 532 / 196); the deployed s166 stand-in's 50 and round A's."""
    for pieces, stage in ((FG.FAKE_WORLD_WALK_S167_PIECES, 167), (FG.FAKE_WORLD_WALK_PIECES, 166)):
        f = _fake(pieces=pieces)
        f._netsync(["selftest", "1"])
        _step(f, 4)
        text = (f.game_path / "Memoria.log").read_text(encoding="utf-8")
        rows, mutants = FG.world_walk_proof_tallies(pieces)
        assert "[NetSync] " + BW.proof_ok(BW.PROOF_OVERLAY_TEXT, BW.overlay_text_selftest_rows(stage)) in text, stage
        assert f"[NetSync] {BW.PROOF_WORLD_WALK}OK ({rows} rows, {mutants} mutants)" in text, stage
        if stage == 167 and not os.environ.get(S167_CLONE_ENV, "").strip() and not _s167_patch_live():
            assert (rows, mutants) == BW.WORLD_WALK_PROOF_S167          # no s167 source reachable: the W1 clone's fallback


# ================================================================================================ THE DRIVER (session.py's gates)
def _game_root(root: pathlib.Path) -> pathlib.Path:
    (root / "x64").mkdir(parents=True, exist_ok=True)
    (root / "x64" / "FF9.exe").write_bytes(b"MZ")
    (root / "Memoria.log").write_text("fake log\n", encoding="utf-8")
    (root / "FF9CustomMap").mkdir(exist_ok=True)
    (root / "FF9CustomMap" / "DictionaryPatch.txt").write_text("FieldScene 6603 31 FARSHORE FARSHORE 6603\n", encoding="utf-8")
    return root


def test_the_session_refuses_round_bs_levers_before_the_step_on_an_engine_without_their_keys(tmp_path):
    """THE CATCH IS THE KEY: round B's levers need `netsync.world.walk` (walk / pair / refuse / stallhold / decline), `netsync.world.fp`
    (fp / tps), `netsync.world.walk.map` (minimap / fullmap) -- refused before the step on the deployed s166 (it would answer its usage line
    only after the step); a malformed one is the usage line THAT build answers (s166's A4 line, s167's grown one); on the s167 stand-in each
    reaches the engine and reads back through State's s167 blocks."""
    from harness import HarnessError, Session
    levers = ((("walk", "off"), "walk"), (("pair", "unmirrored"), "walk"), (("refuse", "silent"), "walk"), (("stallhold", "old"), "walk"),
              (("decline", "old"), "walk"), (("fp", "fake", "0xdead"), "fp"), (("tps", "apply"), "fp"), (("minimap", "old"), "walk.map"),
              (("fullmap", "old"), "walk.map"))
    for pieces, s167, usage in ((FG.FAKE_WORLD_WALK_PIECES, False, BW.WORLDWALK_USAGE_A4),
                                (FG.FAKE_WORLD_WALK_S167_PIECES, True, BW.WORLDWALK_USAGE_S167)):
        root = _game_root(tmp_path / ("s167" if s167 else "s166"))
        fake = FakeGame(root, fps=600, walkmesh=(-2000.0, -3000.0, 2000.0, 2000.0))
        fake.wf_follow_host_cfg = True
        fake.world_walk_pieces = tuple(pieces)
        g = Session(game_path=root, run_dir=root / "run", save_dir=root / "player-saves", pid_probe=lambda: [],
                    launcher=lambda exe: fake.start(), boot_timeout=15.0, verbose=False)
        g._booted_once = True
        with g:
            g.newgame(settle=0)
            g.warp(6603)
            g.netsync("selftest", 1)
            st = g.state
            assert st.coop_world_walk_b is s167 and (st.world_walk_block is not None) is s167
            assert (st.world_fp_block is not None) is s167 and (st.world_walk_map_block is not None) is s167
            for bad in (("walk", "maybe"), ("walk",), ("fp", "fake", "xyz"), ("fp", "fake"), ("minimap", "old", "1")):
                n = len(fake.executed)
                with pytest.raises(HarnessError, match=re.escape(usage)):
                    g.worldwalk(*bad)
                assert len(fake.executed) == n, bad                       # never sent
            for args, key in levers:
                n = len(fake.executed)
                if not s167:
                    with pytest.raises(HarnessError, match=re.escape(f"publishes no `netsync.world.{key}`")):
                        g.worldwalk(*args)
                    assert len(fake.executed) == n, args
                    continue
                st = g.worldwalk(*args)
                assert len(fake.executed) > n, args
            if s167:
                w, fp = st.world_walk_block, st.world_fp_block
                assert (w["lever"], w["pair"], w["refuse"], w["stallhold"], w["decline"], w["minimap"]) == (
                    "off", "unmirrored", "silent", "old", "old", "old")
                assert st.world_walk_map_block["lever"] == "old" and fp["lever"] == "fake" and fp["fake"] == "0x0000DEAD"
                assert st.netsync["world"]["lane"]["world_tps"]["lever"] == "apply"
