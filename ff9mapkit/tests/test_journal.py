"""The 100%-completion JOURNAL (:mod:`ff9mapkit.journal`) -- decode a save's completion counters offline.

Every test here synthesizes its own state: a 2048-byte ``gEventGlobal`` built byte-by-byte, and (for the
extra-backed rows) a SimpleJSON-binary tree built with :mod:`ff9mapkit.sjbinary` the same way
``tests/test_save_items.py:19-49`` does. **No game data, no extracted templates, no install** -- so this
module runs FULLY in a fresh worktree where ``provision.templates_present()`` is False.

Two tests are gated and WILL SKIP without the owner's machine; both say so in their skip reason:

  * ``test_key_items_live_names`` -- needs ``<install>/StreamingAssets/Text/*/KeyItems.strings``. It
    carries its OWN ``skipif`` rather than relying on ``conftest.py``'s FileNotFoundError->skip machinery,
    because ``keyitems._load`` DEGRADES to None instead of raising, so conftest would never fire and the
    assertion would FAIL on CI instead of skipping.
  * ``test_real_save_round_trip`` -- needs the owner's ``SavedData_ww.dat``. Read-only; the repo ships no
    save.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict

import pytest

from ff9mapkit import journal as J
from ff9mapkit import keyitems as KI
from ff9mapkit import save as S
from ff9mapkit import sjbinary as SJ


# ---- fixture builders -------------------------------------------------------------------------
def _geg(**kw) -> bytes:
    """A 2048-byte gEventGlobal with named writers. Every keyword maps to one engine location, cited at
    the write so a fixture can never drift from the module's own offsets."""
    g = bytearray(2048)
    if "scenario" in kw:                                  # UInt16 @0, EventState.cs:18
        g[0], g[1] = kw["scenario"] & 0xFF, kw["scenario"] >> 8 & 0xFF
    if "field_entrance" in kw:                            # UInt16 @2, EventState.cs:28
        g[2], g[3] = kw["field_entrance"] & 0xFF, kw["field_entrance"] >> 8 & 0xFF
    if "beak" in kw:                                      # Byte @139, EMinigame.cs:282
        g[139] = kw["beak"]
    for key, off in (("chocograph_dug", 184), ("chocograph_found", 187)):   # Int24s, ChocographUI.cs:250-251
        if key in kw:
            v = kw[key]
            g[off], g[off + 1], g[off + 2] = v & 0xFF, v >> 8 & 0xFF, v >> 16 & 0xFF
    if "dig_ability" in kw:                               # Byte @191, ChocographUI.cs:245
        g[191] = kw["dig_ability"]
    if "ragtime" in kw:                                   # Byte @198 bits 3..7, BattleAchievement.cs:41-42
        g[198] = (kw["ragtime"] & 31) << 3
    if "hunt_winner" in kw:                               # Byte @313, EMinigame.cs:302
        g[313] = kw["hunt_winner"]
    if "stellazzio" in kw:                                # UInt16 @355, EMinigame.cs:179
        g[355], g[356] = kw["stellazzio"] & 0xFF, kw["stellazzio"] >> 8 & 0xFF
    if "coin_toss" in kw:                                 # Byte @369, EMinigame.cs:335
        g[369] = kw["coin_toss"]
    for i in range(kw.get("beaches", 0)):                 # Bits 856+, EMinigame.cs:478
        g[(J.SANDY_BEACH_BIT + i) >> 3] |= 1 << ((J.SANDY_BEACH_BIT + i) & 7)
    for name, bit in (("mognet_central", J.MOGNET_CENTRAL_BIT), ("paradise", J.CHOCOBO_PARADISE_BIT),
                      ("yan", J.YAN_BLESSING_BIT)):
        if kw.get(name):
            g[bit >> 3] |= 1 << (bit & 7)
    if "delivered" in kw:                                 # Byte @1032, content/mognet.py:85
        g[1032] = kw["delivered"]
    if "stiltzkin" in kw:                                 # Byte @1033, content/mognet.py:86
        g[1033] = kw["stiltzkin"]
    for k in range(kw.get("carrying", 0)):                # slot k occupied byte, content/mognet.py:87-89
        g[1034 + 4 * k] = 1
    for i in range(kw.get("give_locks", 0)):
        g[(J.MOGNET_GIVE_LO + i) >> 3] |= 1 << ((J.MOGNET_GIVE_LO + i) & 7)
    for i in range(kw.get("read_locks", 0)):
        g[(J.MOGNET_READ_LO + i) >> 3] |= 1 << ((J.MOGNET_READ_LO + i) & 7)
    for b in kw.get("th_bytes", ()):                      # raw bytes to fill 0xFF for TH scoring
        g[b] = 0xFF
    for off, val in (kw.get("raw") or {}).items():        # escape hatch for an exact byte
        g[off] = val
    return bytes(g)


def _int(v):
    return SJ.SJData(SJ.INT, v)


def _card(cid, ctype=0, arrow=0):
    c = SJ.SJClass()
    c.add("id", _int(cid)); c.add("type", _int(ctype)); c.add("arrow", _int(arrow))
    return c


def _minigame(cards=(), win=0, lose=0, draw=0):
    """A 30000_MiniGame node (JsonParser.cs:690-737). ``cards`` = [(id, type, arrow), ...]."""
    m = SJ.SJClass()
    m.add("sWin", _int(win)); m.add("sLose", _int(lose)); m.add("sDraw", _int(draw))
    m.add("MiniGameCard", SJ.SJArray([_card(*c) for c in cards]))
    return m


def _common(gil=1234, frog_no=7, steal_no=11, escape_no=2, battle_no=300, kills=((10, 5), (11, 3)),
            categories=(1, 2, 3, 4, 5, 6, 7, 8), keyitems=((0, True, False), (4, True, False)),
            with_categories=True):
    """A 40000_Common node in the MODERN (``!oldSaveFormat``) shape -- JsonParser.cs:918-1006."""
    c = SJ.SJClass()
    c.add("players", SJ.SJArray([]))
    c.add("escape_no", _int(escape_no))
    c.add("gil", _int(gil))
    c.add("frog_no", _int(frog_no))
    c.add("steal_no", _int(steal_no))
    if with_categories:
        for name, v in zip(J.KILL_CATEGORIES, categories):
            c.add(name, _int(v))
    c.add("kills_per_model", SJ.SJArray([
        (lambda e: (e.add("id", _int(i)), e.add("count", _int(n)), e)[-1])(SJ.SJClass())
        for i, n in kills]))
    c.add("items", SJ.SJArray([]))
    rare = SJ.SJArray([])
    for iid, obtained, used in keyitems:                  # rareItemsEx is SPARSE: absent != not obtained
        e = SJ.SJClass()
        e.add("id", _int(iid))
        e.add("obtained", SJ.SJData(SJ.VALUE, str(obtained)))
        e.add("used", SJ.SJData(SJ.VALUE, str(used)))
        rare.items.append(e)
    c.add("rareItemsEx", rare)
    c.add("battle_no", _int(battle_no))
    return c


def _setting(time_s=3661.5):
    s = SJ.SJClass()
    s.add("00001_time", SJ.SJData(SJ.DOUBLE, time_s))
    return s


def _event(step=0):
    e = SJ.SJClass()
    e.add("gStepCount", _int(step))
    return e


def _state(geg=None, *, common="auto", minigame="auto", setting="auto", event="auto", main_pt=None,
           label="test", geg_source="extra"):
    return J.JournalState(label, geg if geg is not None else _geg(), geg_source,
                          _common() if common == "auto" else common,
                          _minigame() if minigame == "auto" else minigame,
                          _event() if event == "auto" else event,
                          _setting() if setting == "auto" else setting,
                          main_pt)


def _val(state, rid):
    return J.build_report(state).by_id(rid)


def _extra_file(tmp_path, name="SavedData_ww_Memoria_0_2.dat", **kw):
    """A synthetic Memoria extra file: the four sibling nodes, plus the Base64 gEventGlobal that
    ``save.read_extra_gEventGlobal`` finds by regex (save.py:86-95)."""
    import base64
    root = SJ.SJClass()
    root.add("95000_Setting", _setting())
    ev = _event()
    ev.add("gEventGlobal", SJ.SJData(SJ.VALUE, base64.b64encode(kw.pop("geg", _geg())).decode()))
    root.add("20000_Event", ev)
    root.add("40000_Common", _common(**kw))
    root.add("30000_MiniGame", _minigame())
    p = tmp_path / name
    p.write_bytes(SJ.dumps(root))
    return p


# ---- primitives -------------------------------------------------------------------------------
def test_u16_and_bit_match_the_engine_addressing():
    g = _geg(scenario=0xBEEF)
    assert J._u16(g, 0) == 0xBEEF                          # EBin.cs:1873-1875, little-endian UNSIGNED
    g2 = bytearray(2048); g2[23] = 0b0000_0001             # "bit 184" == byte 23 bit 0 (EBin.cs:1853)
    assert J._bit(bytes(g2), 184) == 1
    assert J._u8(bytes(g2), 184) == 0                      # ...and "byte 184" is a DIFFERENT location


def test_int24_sign_extends_exactly_like_the_engine():
    """THE TEST THAT WOULD HAVE CAUGHT THE DESIGN BUG. ``EBin.GetVariableValueInternal`` casts the third
    byte to SByte (EBin.cs:1858-1861), so a fully-set chocograph field reads -1, and any compare against
    16777215 fails. The masked form (EMinigame.cs:435-436) is what a bitfield read must use."""
    g = _geg(chocograph_dug=0xFFFFFF)
    assert J._i24s(g, J.CHOCOGRAPH_OPENED_OFF) == -1        # signed, exactly as the engine returns it
    assert J._u24(g, J.CHOCOGRAPH_OPENED_OFF) == 0xFFFFFF   # ...and masked back to the bitfield
    assert _val(_state(g), "chocobo.chocographs_dug").value == 24
    # bit 23 alone: the byte that trips the SByte cast, in isolation.
    g2 = _geg(chocograph_dug=0x800000)
    assert J._i24s(g2, J.CHOCOGRAPH_OPENED_OFF) == -(1 << 23)
    assert _val(_state(g2), "chocobo.chocographs_dug").value == 1


def test_treasure_hunter_x2_band_overlaps_the_chocograph_int24():
    """The TH weight-2 band is bytes 182-186 (EventState.cs:69) and chocograph-OPENED is bytes 184-186
    (ChocographUI.cs:251) -- THE SAME BYTES. Filling the Int24 must add exactly 3*8*2 = 48 TH points.
    This is asserted, not assumed: nobody may 'fix' the double-count by making the rows independent."""
    base = _val(_state(_geg()), "treasure.hunter_points").value
    rep = J.build_report(_state(_geg(chocograph_dug=0xFFFFFF)))
    assert rep.by_id("treasure.hunter_points").value == base + 48
    assert rep.by_id("chocobo.chocographs_dug").value == 24


def test_treasure_hunter_rank_ladder_every_boundary():
    """The ladder from EventState.cs:55-63 (a COMMENT in stock), at each boundary."""
    cases = [(0, "H"), (199, "H"), (200, "G"), (219, "G"), (220, "F"), (239, "F"), (240, "E"),
             (259, "E"), (260, "D"), (279, "D"), (280, "C"), (299, "C"), (300, "B"), (319, "B"),
             (320, "A"), (339, "A"), (340, "S"), (9999, "S")]
    for pts, letter in cases:
        idx, got = J.treasure_hunter_rank(pts)
        assert got == letter, f"{pts} pts -> {got}, expected {letter}"
        assert J.TH_RANKS[idx] == letter


def test_treasure_hunter_points_weights():
    # weight 1 over 896-960 and 966-975, weight 2 over 182-186 (flags.TH_POINT_RANGES / EventState.cs:64-70)
    assert _val(_state(_geg(th_bytes=[900])), "treasure.hunter_points").value == 8
    assert _val(_state(_geg(th_bytes=[970])), "treasure.hunter_points").value == 8
    assert _val(_state(_geg(th_bytes=[182])), "treasure.hunter_points").value == 16
    assert _val(_state(_geg(th_bytes=[961])), "treasure.hunter_points").value == 0   # the 961-965 hole


# ---- gEventGlobal rows ------------------------------------------------------------------------
def test_story_scenario_value_and_milestone():
    r = _val(_state(_geg(scenario=7200)), "story.scenario")
    assert (r.value, r.denominator) == (7200, None)         # never a bar: it is a chapter heading
    assert "Alexandria Castle" in r.detail
    assert r.pct is None


def test_chocographs_found_and_dug_are_separate_int24s():
    g = _geg(chocograph_found=0b111, chocograph_dug=0b1)
    rep = J.build_report(_state(g))
    assert rep.by_id("chocobo.chocographs_found").value == 3
    assert rep.by_id("chocobo.chocographs_dug").value == 1
    assert rep.by_id("chocobo.chocographs_found").denominator == 24


def test_beak_level_and_dig_ability():
    rep = J.build_report(_state(_geg(beak=16, dig_ability=2)))
    assert (rep.by_id("chocobo.beak_level").value, rep.by_id("chocobo.beak_level").denominator) == (16, 99)
    assert (rep.by_id("chocobo.dig_ability").value, rep.by_id("chocobo.dig_ability").denominator) == (2, 5)


def test_beaches_counts_21_static_bits():
    assert _val(_state(_geg(beaches=0)), "chocobo.beaches").value == 0
    assert _val(_state(_geg(beaches=13)), "chocobo.beaches").value == 13
    r = _val(_state(_geg(beaches=21)), "chocobo.beaches")
    assert (r.value, r.denominator, r.complete) == (21, 21, True)


def test_stellazzio_counts_only_the_low_13_bits():
    assert _val(_state(_geg(stellazzio=0b1_1111)), "minigame.stellazzio").value == 5
    # bits 13-15 are outside the engine's 13-iteration loop (EMinigame.cs:181) and must NOT be counted
    assert _val(_state(_geg(stellazzio=0xFFFF)), "minigame.stellazzio").value == 13


def test_ragtime_is_a_5_bit_field_at_byte_198():
    assert _val(_state(_geg(ragtime=3)), "minigame.ragtime_quiz").value == 3
    assert _val(_state(_geg(ragtime=16)), "minigame.ragtime_quiz").denominator == 16
    # the low 3 bits of byte 198 belong to something else and must not leak into the count
    assert _val(_state(_geg(raw={198: 0b0000_0111})), "minigame.ragtime_quiz").value == 0


def test_hunt_winner_is_exclusive_and_names_the_winner():
    r = _val(_state(_geg(hunt_winner=2)), "minigame.hunt_winner")
    assert (r.value, r.detail, r.denominator) == (2, "Vivi", None)
    assert r.exclusive_group == "festival_of_the_hunt"


def test_coin_toss_denominator_is_the_thief_condition():
    r = _val(_state(_geg(coin_toss=13)), "minigame.coin_toss")
    assert (r.value, r.denominator) == (13, 51)             # EMinigame.ThiefNPCCoinCondition (:755)


def test_mognet_rows():
    g = _geg(delivered=13, stiltzkin=3, carrying=2, give_locks=13, read_locks=24,
             mognet_central=True, paradise=False)
    rep = J.build_report(_state(g))
    assert rep.by_id("mognet.delivered").value == 13
    assert rep.by_id("mognet.letters_carried").value == 2
    assert rep.by_id("mognet.give_locks").value == 13
    assert rep.by_id("mognet.read_locks").value == 24
    assert rep.by_id("mognet.central_discovered").value == 1
    assert rep.by_id("mognet.paradise_discovered").value == 0


def test_stiltzkin_tally_carries_no_denominator():
    """THE TRAP. Byte 1033 is the moogle fields' own tally; AllStiltzkinItem=8 scores
    AchievementState.StiltzkinBuy (EMinigame.cs:50-52), which lives elsewhere. Hanging /8 here would ship
    a plausible, checkable, WRONG number -- so the two are separate rows and only the SIBLING carries 8."""
    tally = _val(_state(_geg(stiltzkin=3)), "mognet.stiltzkin_tally")
    assert tally.denominator is None and tally.value == 3
    buys = _val(_state(), "mognet.stiltzkin_purchases")
    assert (buys.status, buys.denominator, buys.value) == ("untracked", 8, None)
    assert "StiltzkinBuy" in buys.blocked_by


def test_yan_blessing_bit():
    assert _val(_state(_geg(yan=True)), "combat.yan_blessing").value == 1
    assert _val(_state(_geg()), "combat.yan_blessing").value == 0


def test_field_entrance_is_read_unsigned_like_the_engine():
    """EventState.cs:28 is `gEventGlobal[3] << 8 | gEventGlobal[2]` -- UNSIGNED. flags.py:171 declares the
    same var signed and unpacks '<h', so an entrance >= 32768 renders NEGATIVE there. The journal follows
    the engine; flags.py is deliberately left untouched (savedoc.py renders it)."""
    from ff9mapkit import flags as F
    g = _geg(field_entrance=40000)
    assert _val(_state(g), "meta.field_entrance").value == 40000
    assert F.decode_gEventGlobal(g).field_entrance == 40000 - 65536      # the divergence, pinned


# ---- Tetra Master replication -----------------------------------------------------------------
def test_collector_points_replicates_the_engine_formula():
    """QuadMistDatabase.MiniGame_GetPlayerPoints (:185-199): kinds*10 + typePtsWorth[type] + 5*arrows."""
    cards = [(1, 0, 0xAA), (1, 3, 0xAA), (2, 2, 0xBB)]      # 2 kinds, types 0/3/2, 2 arrow patterns
    assert J.collector_points(cards) == 2 * 10 + (0 + 2 + 1) + 5 * 2 == 33
    assert J.collector_points([]) == 0


def test_collector_level_ladder_and_boundaries():
    assert J.collector_level(0) == 0
    assert J.collector_level(299) == 0
    assert J.collector_level(300) == 1                       # the first threshold
    assert J.collector_level(431) == 2                       # the owner's measured deck
    assert J.collector_level(1699) == 30
    assert J.collector_level(1700) == 31 == J.COLLECTOR_LEVEL_MAX
    assert J.collector_level(99999) == 31


def test_deck_filter_matches_the_engine_loader():
    """JsonParser.cs:650-654 DISCARDS id == NONE (255) and id >= CardPool.TOTAL_CARDS (100) before the
    deck ever reaches SavedData.MiniGameCard -- an old-format 100-entry array is mostly 255 padding, so
    counting it raw would report a 100-card deck for an empty one."""
    mg = _minigame(cards=[(1, 0, 5), (255, 255, 255), (150, 0, 0), (2, 1, 5)])
    assert J.deck_cards(mg) == [(1, 0, 5), (2, 1, 5)]
    rep = J.build_report(_state(minigame=mg))
    assert rep.by_id("minigame.cards_held").value == 2
    assert rep.by_id("minigame.card_kinds").value == 2
    assert rep.by_id("minigame.card_kinds").denominator == 100


def test_card_rows_end_to_end():
    mg = _minigame(cards=[(1, 0, 0xAA), (1, 3, 0xAA), (2, 2, 0xBB)], win=3, lose=9, draw=1)
    rep = J.build_report(_state(minigame=mg))
    assert rep.by_id("minigame.collector_points").value == 33
    assert rep.by_id("minigame.collector_level").value == 0
    assert rep.by_id("minigame.card_record").value == 3
    assert rep.by_id("minigame.card_record").detail == "W/L/D 3/9/1"


def test_empty_deck_scores_zero_not_unavailable():
    rep = J.build_report(_state(minigame=_minigame(cards=[])))
    assert rep.by_id("minigame.collector_points").value == 0
    assert rep.by_id("minigame.collector_level").value == 0
    assert rep.by_id("minigame.cards_held").status == "tracked"


# ---- extra-backed rows + status downgrades -----------------------------------------------------
def test_common_rows():
    rep = J.build_report(_state())
    assert rep.by_id("minigame.frogs").value == 7
    assert rep.by_id("party.thefts").value == 11 and rep.by_id("party.thefts").denominator == 50
    assert rep.by_id("party.escapes").value == 2
    assert rep.by_id("party.battles").value == 300
    assert rep.by_id("party.gil").value == 1234
    assert rep.by_id("party.kills_total").value == 8            # 5 + 3 from kills_per_model
    assert rep.by_id("party.kills_by_category").value == sum(range(1, 9))


def test_play_time_reads_the_setting_double():
    r = _val(_state(setting=_setting(88044.4)), "meta.play_time")
    assert r.value == 88044 and r.detail == "24h27m"


def test_no_extra_downgrades_every_extra_row_to_unavailable():
    """A VANILLA slot (no Memoria extra, no decodable main block) must report `unavailable`, never a
    fabricated 0 -- and render_report must still render."""
    st = _state(common=None, minigame=None, setting=None, event=None)
    rep = J.build_report(st)
    for spec in J.ROWS:
        if spec.store == "extra" and spec.status == "tracked":
            row = rep.by_id(spec.id)
            assert row.status == "unavailable", spec.id
            assert row.value is None, spec.id
            assert row.pct is None and row.complete is False, spec.id
    assert "FF9 completion journal" in J.render_report(rep)
    # the geg-backed rows are unaffected
    assert rep.by_id("treasure.hunter_points").status == "tracked"


# ------------------------------- a BROKEN READER is not a MISSING STORE -------------------------------
# The resolver used to swallow IndexError/KeyError/TypeError/ValueError/AttributeError from every reader
# and report `unavailable` -- so "our code crashed on this save" rendered as "this save has no such
# store", on rows that would otherwise have produced a number. Both cases below are REAL raises from
# shipping reader code, not injected stubs.

def test_a_reader_that_RAISES_reports_error_not_unavailable():
    """A truncated vanilla main block: ``read_main_keyitems`` (save_items.py:1010-1019) walks past the
    end of the 2-bit rareItems field. Before the split this row rendered as "this save has no such
    store" -- exactly what a legitimately vanilla-and-empty slot renders as."""
    st = J.JournalState("slot 1", _geg(), "main", main_pt=b"\x00" * 64)
    row = J.build_report(st).by_id("party.key_items")
    assert row.status == "error"
    assert row.error == "IndexError: index out of range"
    assert row.value is None and row.pct is None and row.complete is False


def test_a_second_reader_raise_surfaces_too():
    """``read_abilities`` (save_items.py:302-332) does a bare ``int(cnode.value)`` on every
    ``pa_extended`` entry; a non-numeric leaf raises ValueError. Same class, different store."""
    c = _common()
    p = SJ.SJClass()
    info = SJ.SJClass()
    info.add("menu_type", _int(0))
    info.add("slot_no", _int(0))
    p.add("info", info)
    p.add("name", SJ.SJData(SJ.VALUE, "Zidane"))
    e = SJ.SJClass()
    e.add("id", _int(6))
    e.add("cur", SJ.SJData(SJ.VALUE, "lots"))
    p.add("pa_extended", SJ.SJArray([e]))
    c.set("players", SJ.SJArray([p]))
    row = J.build_report(_state(common=c)).by_id("party.abilities_mastered")
    assert row.status == "error"
    assert row.error.startswith("ValueError: invalid literal for int()")


def test_the_two_outcomes_are_DISTINGUISHABLE_on_the_same_row():
    """THE POINT, in one assertion: the same row, absent store vs broken reader, must not look alike."""
    absent = J.build_report(_state(common=None, minigame=None, setting=None, event=None))
    broken = J.build_report(J.JournalState("s", _geg(), "main", main_pt=b"\x00" * 64))
    a, b = absent.by_id("party.key_items"), broken.by_id("party.key_items")
    assert (a.status, a.error) == ("unavailable", None)
    assert b.status == "error" and b.error
    assert J._fmt_value(a) != J._fmt_value(b)
    assert absent.broken == [] and len(broken.broken) == 1


def test_render_report_banners_a_broken_reader():
    """Loud, not silent: a banner above every section (independent of --category) AND the exception on
    the row itself."""
    rep = J.build_report(J.JournalState("s", _geg(), "main", main_pt=b"\x00" * 64))
    out = J.render_report(rep)
    assert "!! 1 ROW READER(S) FAILED" in out
    assert "party.key_items" in out and "IndexError: index out of range" in out
    assert "!! READER FAILED" in out
    # still visible when the user filters to a single category
    assert "!! 1 ROW READER(S) FAILED" in J.render_report(rep, category="party")


def test_a_reader_raising_something_outside_the_old_tuple_no_longer_kills_the_report(monkeypatch):
    """The old catch was a 5-type tuple, so a struct.error / UnicodeDecodeError / anything else took
    the WHOLE report down. One bad row must degrade one row."""
    spec = next(s for s in J.ROWS if s.id == "party.thefts")

    def boom(_st):
        raise RuntimeError("upstream table went away")

    rows = [_spec(spec, read=boom) if s.id == "party.thefts" else s
            for s, spec in ((s, s) for s in J.ROWS)]
    monkeypatch.setattr(J, "ROWS", rows)
    rep = J.build_report(_state())
    assert rep.by_id("party.thefts").error == "RuntimeError: upstream table went away"
    assert rep.by_id("party.escapes").status == "tracked"       # the rest of the report survives


def test_error_rows_are_excluded_from_the_index_and_from_a_diff():
    broken = J.build_report(J.JournalState("s", _geg(), "main", main_pt=b"\x00" * 64))
    assert all(r.status == "tracked" for r in J._index_rows(broken.rows))
    assert "party.key_items" not in {r.id for r in J._index_rows(broken.rows)}
    # a row that ERRORED on one side is not a value that "moved" -- same reasoning as unavailable
    d = J.diff_reports(broken, J.build_report(_state()))
    assert "party.key_items" not in {ra.id for ra, _rb in d.changed}


def test_rows_json_carries_the_error_text():
    rep = J.build_report(J.JournalState("s", _geg(), "main", main_pt=b"\x00" * 64))
    d = next(r for r in J.rows_json(rep) if r["id"] == "party.key_items")
    assert d["status"] == "error" and d["error"] == "IndexError: index out of range"


def test_migrated_save_kills_total_is_unavailable_not_zero():
    """A save migrated from the old format has an EMPTY kills_per_model while the category counters are
    non-zero (the old arm carried only dragon_no, JsonParser.cs:932). Reporting 0 defeated enemies for a
    30-hour save is the exact failure mode this downgrade exists to prevent."""
    common = _common(kills=(), categories=(0, 0, 0, 8, 0, 0, 0, 0))
    rep = J.build_report(_state(common=common))
    assert rep.by_id("party.kills_total").status == "unavailable"
    assert rep.by_id("party.kills_total").value is None
    assert rep.by_id("party.kills_by_category").value == 8       # the categories still read
    # ...but a genuinely fresh save (no kills anywhere) reports a real 0, not unavailable
    fresh = J.build_report(_state(common=_common(kills=(), categories=(0,) * 8)))
    assert fresh.by_id("party.kills_total").value == 0


def test_key_items_denominator_is_never_baked(monkeypatch):
    """The denominator + names come from the LIVE install table; with the install unreachable the value
    is still valid and the denominator is None. rareItemsEx is SPARSE, so its length is never a
    denominator: two entries where one is not obtained must report 1, not 2 and not 'of 2'."""
    monkeypatch.setattr(KI, "all_keyitems", lambda game=None: [])      # install unreachable ->
    monkeypatch.setattr(KI, "name_of", lambda iid, game=None: None)    # keyitems.py:51-54 returns None
    common = _common(keyitems=((0, True, False), (4, False, False)))
    r = _val(_state(common=common), "party.key_items")
    assert r.value == 1 and r.denominator is None and r.names == []
    monkeypatch.setattr(KI, "all_keyitems", lambda game=None: [(i, f"Item{i}") for i in range(80)])
    monkeypatch.setattr(KI, "name_of", lambda iid, game=None: f"Item{iid}")
    r2 = _val(_state(common=common), "party.key_items")
    assert r2.value == 1 and r2.denominator == 80 and r2.names == ["Item0"]


def test_abilities_mastered_is_party_state_not_the_achievement():
    """`party.abilities_mastered` has NO denominator: AllAbility=183 scores AchievementState.abilities
    (the ever-learned HashSet), which is a DIFFERENT quantity and ships as its own untracked row."""
    mastered = J._ROWS_BY_ID["party.abilities_mastered"]
    ever = J._ROWS_BY_ID["party.abilities_ever"]
    assert mastered.denom is None
    assert (ever.denom, ever.status) == (183, "untracked")
    assert "AchievementState.abilities" in ever.blocked_by


# ---- untracked / dead / the index --------------------------------------------------------------
def test_there_is_no_chests_row():
    """A regression guard against someone helpfully adding `chests N/446` later. FF9 keeps no per-chest
    registry; the engine's only treasure metric is the blind weighted popcount."""
    rep = J.build_report(_state(_geg(th_bytes=[900, 901])))
    chest = rep.by_id("treasure.chest_atlas")
    assert (chest.status, chest.value, chest.denominator) == ("untracked", None, None)
    assert not any(r.id.startswith("treasure.chest") and r.status == "tracked" for r in rep.rows)
    assert not any(r.denominator in (446, 477, 386, 327) for r in rep.rows)


def test_untracked_rows_are_emitted_never_dropped():
    rep = J.build_report(_state())
    untracked = [r for r in rep.rows if r.status == "untracked"]
    assert len(untracked) >= 8
    for r in untracked:
        assert r.value is None and r.blocked_by and r.pct is None
    assert {r.id for r in untracked} >= {"treasure.chest_atlas", "meta.ates_seen", "meta.bestiary",
                                         "party.abilities_ever", "mognet.stiltzkin_purchases"}


def test_step_count_is_dead_and_excluded_from_the_index():
    r = _val(_state(), "meta.step_count")
    assert (r.status, r.value, r.pct) == ("dead", None, None)
    assert r not in J._index_rows(J.build_report(_state()).rows)


def test_index_excludes_exclusive_and_run_mode_rows():
    """A bar that can never fill reads as a bug, so an exclusive_group / run_mode row must not move the
    index. Winning the Festival of the Hunt (exclusive) and maxing the card collection (run_mode) both
    leave the index exactly where it was."""
    base = _val(_state(_geg()), "meta.index").value
    assert _val(_state(_geg(hunt_winner=2)), "meta.index").value == base
    # Two decks with the SAME card_kinds (a scored row) but different collector points -- so the only
    # rows that move are the run_mode-gated ones. The index must not budge.
    thin = _minigame(cards=[(1, 0, 0)])                    # 1 kind, 1 arrow  -> 15 pts
    rich = _minigame(cards=[(1, 3, 0), (1, 3, 1)])         # 1 kind, 2 arrows -> 24 pts
    a, b = J.build_report(_state(_geg(), minigame=thin)), J.build_report(_state(_geg(), minigame=rich))
    assert a.by_id("minigame.card_kinds").value == b.by_id("minigame.card_kinds").value == 1
    assert a.by_id("minigame.collector_points").value != b.by_id("minigame.collector_points").value
    assert a.by_id("meta.index").value == b.by_id("meta.index").value
    scored = {r.id for r in J._index_rows(J.build_report(_state()).rows)}
    for rid in ("minigame.hunt_winner", "minigame.collector_points", "minigame.collector_level",
                "meta.index", "meta.step_count", "party.gil"):
        assert rid not in scored, rid
    assert "chocobo.beaches" in scored                      # ...and the exclusion is not vacuous


def test_index_moves_when_a_scored_row_moves():
    """...and the exclusion is not a check that cannot fail: a plain scored row DOES move it."""
    base = _val(_state(_geg()), "meta.index").value
    moved = _val(_state(_geg(beaches=21, chocograph_found=0xFFFFFF)), "meta.index").value
    assert moved > base


# ---- the schema gate --------------------------------------------------------------------------
def test_lint_rows_is_green_over_the_shipped_table():
    assert J.lint_rows() == []


@pytest.mark.parametrize("mutate,expect", [
    (lambda r: [r[0], r[0]], "duplicate row id"),
    (lambda r: [_spec(r[0], category="nope")], "not in CATEGORIES"),
    (lambda r: [_spec(r[0], provenance="vibes")], "not in PROVENANCE"),
    (lambda r: [_spec(r[0], status="maybe")], "not in DECLARABLE_STATUSES"),
    # `unavailable` / `error` are RESOLVE-time outcomes -- a RowSpec claiming either would be
    # asserting a fact about a save it has not read.
    (lambda r: [_spec(r[0], status="unavailable")], "not in DECLARABLE_STATUSES"),
    (lambda r: [_spec(r[0], status="error")], "not in DECLARABLE_STATUSES"),
    (lambda r: [_spec(r[0], store="somewhere")], "not in STORES"),
    (lambda r: [_spec(r[0], source="EventState.cs")], "file.ext:line citation"),
    (lambda r: [_spec(_by("chocobo.beak_level"), denom_source="")], "must be set together"),
    (lambda r: [_spec(_by("meta.bestiary"), blocked_by=None)], "blocked_by is required"),
    (lambda r: [_spec(_by("meta.bestiary"), read=lambda st: J.Read(1))], "must have no reader"),
    (lambda r: [_spec(_by("chocobo.beak_level"), read=None)], "needs a reader"),
    (lambda r: [_spec(_by("chocobo.beak_level"), denom=42)], "!= the transcribed target"),
    (lambda r: [_spec(_by("party.key_items"), name_source=None)], "declares no name_source"),
])
def test_lint_rows_can_actually_fail(mutate, expect):
    """BREAK IT TO PROVE IT (feedback-a-check-that-cannot-fail): every lint rule is exercised against a
    deliberately broken table, so a green `journal lint` means something."""
    bad = J.lint_rows(mutate(list(J.ROWS)))
    assert any(expect in m for m in bad), f"expected a {expect!r} violation, got {bad}"


def _by(rid):
    return J._ROWS_BY_ID[rid]


def _spec(base, **kw):
    from dataclasses import replace
    return replace(base, **kw)


def test_engine_targets_transcription_guard():
    """:data:`ENGINE_TARGETS` is a TRANSCRIPTION of AchievementManager.cs DataWorld (``Data = GetData()``
    throws without SharedDataBytesStorage, so it cannot be queried). This pins it against an accidental
    edit -- it is honestly a comparison of two Python literals, not a query of the engine."""
    expected = {
        "Defeat10000": (10000, "AchievementManager.cs:1490"),
        "AllStiltzkinItem": (8, "AchievementManager.cs:1502"),
        "AllPasssiveAbility": (63, "AchievementManager.cs:1514"),
        "AllAbility": (183, "AchievementManager.cs:1526"),
        "ChocoboLv99": (99, "AchievementManager.cs:1560"),
        "AllSandyBeach": (21, "AchievementManager.cs:1572"),
        "AllTreasure": (24, "AchievementManager.cs:1584"),
        "Frog99": (99, "AchievementManager.cs:1618"),
        "QueenReward10": (10, "AchievementManager.cs:1708"),
        "CardWinAll": (235, "AchievementManager.cs:1910"),
        "Steal50": (50, "AchievementManager.cs:1945"),
        "ATE80": (79, "AchievementManager.cs:2169"),
        "Moonstone4": (4, "AchievementManager.cs:2181"),
    }
    assert J.ENGINE_TARGETS == expected
    # and the constants derived from them have not drifted apart
    assert J.CHOCOGRAPH_MAX == J.ENGINE_TARGETS["AllTreasure"][0] == 24
    assert J.ATE_SEEN_MAX == J.ENGINE_TARGETS["ATE80"][0] == 79
    # QueenReward10 is the Stellazzio REWARD threshold and must never become the coin denominator
    assert J.STELLAZZIO_MAX == 13 != J.ENGINE_TARGETS["QueenReward10"][0]
    # CardWinAll is the OPPONENT list, not the card-kind count
    assert J.CARD_KINDS_MAX == 100 != J.ENGINE_TARGETS["CardWinAll"][0]


# ---- export contract --------------------------------------------------------------------------
def test_rows_are_json_round_trippable():
    """The contract the later catalog generator and the later in-game screen both depend on: no callables
    leak out of a resolved row."""
    rep = J.build_report(_state())
    for r in rep.rows:
        d = asdict(r)
        assert json.loads(json.dumps(d)) == d, r.id
    specs = J.rows_json()
    assert json.loads(json.dumps(specs))
    assert all("read" not in s for s in specs)
    assert len(specs) == len(J.ROWS)
    assert len({s["id"] for s in specs}) == len(J.ROWS)


def test_row_ids_are_stable_contract():
    """`id` is a PERMANENT contract (a catalog + an in-game screen key off it). A rename here should
    force a deliberate decision, not slip through."""
    assert {r.id for r in J.ROWS} >= {
        "story.scenario", "treasure.hunter_points", "treasure.hunter_rank", "treasure.chest_atlas",
        "chocobo.chocographs_found", "chocobo.chocographs_dug", "chocobo.beak_level",
        "chocobo.dig_ability", "chocobo.beaches", "minigame.stellazzio", "minigame.ragtime_quiz",
        "minigame.hunt_winner", "minigame.coin_toss", "minigame.frogs", "minigame.cards_held",
        "minigame.card_kinds", "minigame.collector_points", "minigame.collector_level",
        "minigame.card_record", "minigame.quadmist_opponents", "mognet.delivered",
        "mognet.stiltzkin_tally", "mognet.stiltzkin_purchases", "mognet.letters_carried",
        "mognet.give_locks", "mognet.read_locks", "mognet.central_discovered",
        "mognet.paradise_discovered", "party.gil", "party.key_items", "party.abilities_mastered",
        "party.abilities_ever", "party.passive_abilities_ever", "party.thefts", "party.escapes",
        "party.battles", "party.kills_total", "party.kills_by_category", "combat.yan_blessing",
        "meta.play_time", "meta.step_count", "meta.field_entrance", "meta.ates_seen", "meta.bestiary",
        "meta.synthesis_recipes", "meta.friendly_monsters", "meta.achievement_keys", "meta.index"}


def test_every_row_cites_an_engine_or_kit_source():
    for spec in J.ROWS:
        if spec.provenance == "kit-derived":
            continue
        assert J._SOURCE_RE.match(spec.source), f"{spec.id}: {spec.source!r}"


# ---- diff -------------------------------------------------------------------------------------
def test_diff_identical_states_is_empty():
    a = J.build_report(_state(_geg(beaches=3), label="A"))
    b = J.build_report(_state(_geg(beaches=3), label="B"))
    d = J.diff_reports(a, b)
    assert d.empty and d.changed == []
    assert "no completion-state difference" in J.render_diff(d)


def test_diff_reports_only_the_row_that_moved_with_the_right_sign():
    a = J.build_report(_state(_geg(beaches=3), label="A"))
    b = J.build_report(_state(_geg(beaches=7), label="B"))
    d = J.diff_reports(a, b)
    moved = {ra.id: (ra.value, rb.value) for ra, rb in d.changed}
    assert moved["chocobo.beaches"] == (3, 7)
    # 4 of 21 beaches is well under one point of the pooled index (the pool is ~10600 -- see the
    # meta.index note), so the index legitimately does NOT move here; nothing else may.
    assert set(moved) <= {"chocobo.beaches", "meta.index"}
    assert "+4" in J.render_diff(d)


def test_diff_does_not_report_a_vanished_store_as_a_decrease():
    """tracked -> unavailable means the STORE vanished (B has no Memoria extra), not that progress went
    backwards. Reporting `50 -> 0` there would be a fabricated regression."""
    a = J.build_report(_state(label="A"))
    b = J.build_report(_state(common=None, minigame=None, setting=None, label="B"))
    assert a.by_id("party.thefts").value == 11 and b.by_id("party.thefts").status == "unavailable"
    assert all(ra.id != "party.thefts" for ra, _ in J.diff_reports(a, b).changed)


# ---- rendering --------------------------------------------------------------------------------
def test_render_hides_untracked_rows_unless_asked():
    rep = J.build_report(_state(_geg(scenario=7200)))
    plain = J.render_report(rep)
    assert "not tracked by the game -- `--all`" in plain
    assert "Bestiary species seen" not in plain
    full = J.render_report(rep, show_all=True)
    assert "Bestiary species seen" in full
    assert "Steps taken" in full                           # the dead row shows under --all too


def test_render_category_filter():
    out = J.render_report(J.build_report(_state()), category="chocobo")
    assert "Choco's beak level" in out and "Stellazzio coins" not in out


def test_pct_is_none_without_a_denominator():
    rep = J.build_report(_state(_geg(scenario=100)))
    assert rep.by_id("story.scenario").pct is None         # never draw a bar for a chapter heading
    assert rep.by_id("treasure.hunter_points").pct is None  # no engine max exists
    assert rep.by_id("chocobo.beaches").pct == 0.0


# ---- loader -----------------------------------------------------------------------------------
def test_load_state_from_a_synthetic_extra_file(tmp_path):
    p = _extra_file(tmp_path, geg=_geg(scenario=4321, beaches=5), gil=999)
    states = J.load_state(str(p))
    assert len(states) == 1
    st = states[0]
    assert len(st.geg) == 2048 and st.geg_source == "extra"
    assert st.common is not None and st.minigame is not None and st.setting is not None
    rep = J.build_report(st)
    assert rep.by_id("story.scenario").value == 4321
    assert rep.by_id("chocobo.beaches").value == 5
    assert rep.by_id("party.gil").value == 999


def test_load_state_from_a_bare_base64_blob():
    import base64
    blob = base64.b64encode(_geg(scenario=2500)).decode()
    st = J.load_state(blob)[0]
    assert st.geg_source == "loose" and st.common is None
    rep = J.build_report(st)
    assert rep.by_id("story.scenario").value == 2500
    assert rep.by_id("party.gil").status == "unavailable"


def test_load_state_pads_a_short_blob():
    assert len(J._pad(b"\x01\x02")) == 2048
    assert len(J._pad(b"\xff" * 4096)) == 2048


# ---- CLI smoke (no save, no install) -----------------------------------------------------------
def test_cli_journal_rows_and_lint(capsys):
    from ff9mapkit import cli
    assert cli.main(["journal", "rows"]) == 0
    assert "journal row(s)" in capsys.readouterr().out
    assert cli.main(["journal", "rows", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)
    # `--offline` drops the ONE check that reads the game install. This test must not depend on it:
    # without the flag, a machine that cannot read the install is SUPPOSED to exit 2 (see below).
    assert cli.main(["journal", "lint", "--offline"]) == 0
    assert "0 violation(s)" in capsys.readouterr().out


def test_cli_journal_lint_returns_2_when_the_INSTALL_cannot_be_read(monkeypatch, capsys):
    """The key-item denominator is baked into a static .mes at build time, so `journal lint` on the
    deploy machine is the only thing that can catch a table swap. An unreadable install must FAIL
    rather than skip the check silently -- and `--offline` is the deliberate, visible opt-out."""
    from ff9mapkit import cli, journalfield as JF
    monkeypatch.setattr(JF, "live_key_item_count", lambda: None)
    assert cli.main(["journal", "lint"]) == 2
    assert "UNVERIFIED here" in capsys.readouterr().out
    assert cli.main(["journal", "lint", "--offline"]) == 0
    assert "0 violation(s)" in capsys.readouterr().out


def test_cli_journal_lint_returns_2_on_a_bad_row(monkeypatch, capsys):
    from dataclasses import replace
    from ff9mapkit import cli
    broken = list(J.ROWS) + [replace(J._ROWS_BY_ID["chocobo.beak_level"], provenance="vibes")]
    monkeypatch.setattr(J, "ROWS", broken)
    assert cli.main(["journal", "lint"]) == 2
    assert "not in PROVENANCE" in capsys.readouterr().out


def test_cli_journal_report_needs_a_save(capsys):
    from ff9mapkit import cli
    assert cli.main(["journal", "report"]) == 2
    assert "needs a save path" in capsys.readouterr().out


# ---- install-gated (SKIPS without the FF9 install) ----------------------------------------------
@pytest.mark.skipif(KI._load() is None,
                    reason="needs the FF9 install for live key-item names "
                           "(keyitems._load degrades to None instead of raising, so conftest.py's "
                           "FileNotFoundError->skip machinery can never fire here)")
def test_key_items_live_names():
    table = KI.all_keyitems()
    assert table
    r = _val(_state(common=_common(keyitems=((0, True, False), (4, True, False)))), "party.key_items")
    assert r.denominator == len(table)
    assert len(r.names) == 2 and all(isinstance(n, str) and n for n in r.names)


# ---- real-save gated (SKIPS without the owner's container; the repo ships no save) --------------
def _real_save():
    d = S.default_save_dir()
    p = os.path.join(d, "SavedData_ww.dat") if d else ""
    return p if p and os.path.isfile(p) else None


@pytest.mark.skipif(_real_save() is None, reason="needs the owner's SavedData_ww.dat (never shipped)")
def test_real_save_round_trip():
    """The resolver round-trip, READ-ONLY: every populated block loads, every RowSpec resolves, and no
    tracked row exceeds its own denominator."""
    states = J.load_state(_real_save())
    assert states
    for st in states:
        assert len(st.geg) == 2048
        assert st.geg_source in ("extra", "main")
        rep = J.build_report(st)
        assert len(rep.rows) == len(J.ROWS)
        assert {r.id for r in rep.rows} == {s.id for s in J.ROWS}
        for r in rep.rows:
            if r.status == "tracked" and r.denominator is not None:
                assert r.value <= r.denominator, f"{st.label} {r.id}: {r.value} > {r.denominator}"
            if r.status != "tracked":
                assert r.value is None, f"{st.label} {r.id}"
        assert J.render_report(rep, show_all=True)


# =================================================================================================
# T1b -- the IN-GAME half of the same catalog: RowSpec.eb / eb_source / eb_absent.
#
# Two families, doing different jobs:
#   * the SCHEMA family proves the exhaustiveness gate cannot be defaulted past -- a row with neither
#     an expression nor a reason FAILS, which is the whole point of the field pair;
#   * the CROSS-VALIDATION family evaluates each expression over a synthetic gEventGlobal and
#     compares it to THIS module's own offline reader on the same heap. Two implementations of one
#     row, checked against each other offline -- the same bracket the rung-0 playtest applied
#     in-game, minus the game.
# =================================================================================================
from dataclasses import replace as _replace                      # noqa: E402
from ff9mapkit.eb import exprasm as _EA, exprsem as _ES          # noqa: E402
from ff9mapkit.eb.opcodes import EXPR_VALUE_MAX, EXPR_VALUE_MIN  # noqa: E402


def _rspec(rid):
    s = J.row_spec(rid)
    assert s is not None, rid
    return s


def _fail(tok):
    raise AssertionError("unexpected leaf %r" % (tok,))


def test_every_row_declares_EITHER_an_expression_OR_a_reason():
    """The exhaustiveness gate, stated as a property of the shipped table."""
    for s in J.ROWS:
        assert (s.eb is None) != (s.eb_absent is None), (
            "%s: exactly one of eb / eb_absent -- got eb=%r eb_absent=%r" % (s.id, s.eb, s.eb_absent))
    assert sum(1 for s in J.ROWS if s.eb) == len(J.EB_EXPRESSIONS)
    assert sum(1 for s in J.ROWS if s.eb_absent) == len(J.EB_ABSENT)
    assert len(J.ROWS) == len(J.EB_EXPRESSIONS) + len(J.EB_ABSENT)


def test_a_row_with_NEITHER_fails_lint():
    """THE GATE ITSELF. A future row that forgets both fields must FAIL, never default to invisible.
    Built by stripping the fields off a REAL row so the rest of the schema still passes -- otherwise
    a green result could come from some unrelated rule and the failure would not be attributable."""
    orphan = _replace(_rspec("chocobo.beak_level"), id="chocobo.newly_added", eb=None, eb_source="",
                      eb_absent=None)
    bad = J.lint_rows(rows=[orphan])
    assert any("exactly one" in m and "chocobo.newly_added" in m for m in bad), bad
    assert not [m for m in J.lint_rows(rows=[_replace(orphan, eb_absent="no engine read")])
                if "chocobo.newly_added" in m]


def test_a_row_declaring_BOTH_fails_lint():
    both = _replace(_rspec("chocobo.beak_level"), id="x.y", eb_absent="also a reason")
    assert any("exactly one" in m for m in J.lint_rows(rows=[both]))


def test_an_untracked_row_cannot_declare_an_expression():
    s = _replace(_rspec("meta.bestiary"), eb="Global.Byte[1]", eb_source="EBin.cs:1866", eb_absent=None)
    assert any("untracked row cannot declare an eb" in m for m in J.lint_rows(rows=[s]))


def test_an_expression_that_does_not_balance_fails_lint():
    s = _replace(_rspec("chocobo.beak_level"), eb="Global.Byte[139] B_PLUS")
    assert any("does not evaluate" in m for m in J.lint_rows(rows=[s]))


def test_an_expression_that_WRITES_fails_lint():
    """A page body is not a per-frame hud, but a journal row still READS. Same classifier as the hud
    lane (eb/exprsem.py), one owner."""
    s = _replace(_rspec("chocobo.beak_level"), eb="Global.Byte[139] const(1) B_LET")
    assert any("a journal row READS" in m for m in J.lint_rows(rows=[s]))


def test_every_expression_assembles_balances_and_is_effect_free():
    """Over the WHOLE catalog, not a sample. `exprasm.assemble` is a byte encoder that validates
    nothing (eb/exprsem.py:5-6); `analyze` is the validator."""
    for s in J.ROWS:
        if s.eb is None:
            continue
        assert "B_EXPR_END" not in s.eb.split(), s.id
        blob = _EA.assemble(s.eb + " B_EXPR_END")
        assert blob and blob[-1] == 0x7F, s.id
        a = _ES.analyze(s.eb + " B_EXPR_END")
        assert a.unsafe_to_repeat == (), "%s: %s" % (s.id, a.unsafe_to_repeat)
        assert J._SOURCE_RE.match(s.eb_source), "%s: %r" % (s.id, s.eb_source)


def test_every_expression_is_bounded_inside_the_26_bit_envelope():
    """The envelope is not advisory: `expr_Push_v0_Int24` ORs the Int26 class tag into bits 26-28
    with NO mask (EBin.cs:1270-1274), so an overflow is re-read as a DIFFERENT variable class."""
    for s in J.ROWS:
        if s.eb is None:
            continue
        lo, hi = J.eb_bounds(s.eb)
        assert EXPR_VALUE_MIN <= lo and hi <= EXPR_VALUE_MAX, "%s: %d..%d" % (s.id, lo, hi)


def test_play_time_is_divided_INSIDE_the_expression():
    """Seconds cap at 8,388,607 (EventEngine.GetSysvar.cs:70-73), so the divide is for READABILITY,
    not safety -- but the row must still publish hours, not a 7-digit second count."""
    assert J.eb_bounds(_rspec("meta.play_time").eb) == (0, 8388607 // 3600)


def test_eb_bounds_REFUSES_an_operator_or_leaf_it_has_no_rule_for():
    """The bounds gate may not widen silently when a new operator appears."""
    with pytest.raises(J.EbBoundsError):
        J.eb_bounds("Global.Byte[1] B_SINGLE_MINUS")
    with pytest.raises(J.EbBoundsError):
        J.eb_bounds("B_SYSVAR[17]")                       # TimerUI.Time -- no declared bound


def test_no_expression_publishes_a_RAW_Int24():
    """BOTH Int24 and UInt24 sign-extend (ONE case label, EBin.cs:1858-1861), and the defect bites
    only at a FULL field -- unsurfaceable by playtest. The catalog avoids the read entirely; this
    also proves the guard FIRES on whoever reintroduces it as an 'optimisation'."""
    assert not [s for s in J.ROWS if s.eb and "Int24[" in s.eb]
    raw = _replace(_rspec("chocobo.chocographs_found"), eb="Global.Int24[187]",
                   eb_source="ChocographUI.cs:250")
    assert any("const4(16777215) B_AND" in m for m in J.lint_rows(rows=[raw]))
    masked = _replace(raw, eb="Global.Int24[187] const4(16777215) B_AND")
    assert not [m for m in J.lint_rows(rows=[masked]) if "16777215" in m]


# ---- CROSS-VALIDATION: the .eb expression vs this module own offline reader ---------------------
_GEG_CROSS_ROWS = (
    "story.scenario", "chocobo.chocographs_found", "chocobo.chocographs_dug", "chocobo.beak_level",
    "chocobo.dig_ability", "chocobo.beaches", "minigame.stellazzio", "minigame.ragtime_quiz",
    "minigame.coin_toss", "mognet.delivered", "mognet.stiltzkin_tally", "mognet.letters_carried",
    "mognet.give_locks", "mognet.read_locks", "mognet.central_discovered",
    "mognet.paradise_discovered", "combat.yan_blessing", "meta.field_entrance",
)


def _cross_geg():
    return _geg(scenario=4321, field_entrance=211, beak=57, dig_ability=3,
                chocograph_found=0x0FFFFF, chocograph_dug=0x0000FF, ragtime=11, coin_toss=44,
                stellazzio=0b1010101010101, beaches=13, delivered=9, stiltzkin=4, carrying=2,
                give_locks=37, read_locks=21, mognet_central=True, paradise=True, yan=True)


@pytest.mark.parametrize("rid", _GEG_CROSS_ROWS)
def test_expression_agrees_with_the_offline_reader(rid):
    g = _cross_geg()
    offline = _val(_state(g), rid)
    assert offline.status == "tracked", rid
    assert J.eb_eval(_rspec(rid).eb, J.eb_geg_reader(g)) == offline.value, rid


def test_expression_agrees_on_a_ZERO_heap_too():
    """A stuck 0 and a correct 0 are identical on one sample -- both polarities, offline edition."""
    g = _geg()
    for rid in _GEG_CROSS_ROWS:
        assert J.eb_eval(_rspec(rid).eb, J.eb_geg_reader(g)) == _val(_state(g), rid).value == 0, rid


def test_all_24_chocographs_reads_24_not_minus_one():
    """The Int24 trap at the exact input that triggers it. The offline reader masks (`_u24`); the
    expression never touches the sign-extending path at all."""
    g = _geg(chocograph_found=0xFFFFFF, chocograph_dug=0xFFFFFF)
    assert J._i24s(g, J.CHOCOGRAPH_FOUND_OFF) == -1               # what the ENGINE Int24 read returns
    for rid in ("chocobo.chocographs_found", "chocobo.chocographs_dug"):
        assert J.eb_eval(_rspec(rid).eb, J.eb_geg_reader(g)) == 24 == _val(_state(g), rid).value


def test_treasure_hunter_rank_expression_reproduces_the_offline_ladder_at_every_point():
    """The rank ladder is 8 `>=` tests summed; `Null.SBit[5]` is not in the heap, so the points come
    from the offline computation -- which is exactly the bracket: same input, two ladders."""
    eb = _rspec("treasure.hunter_rank").eb
    for pts in range(0, 700):
        got = J.eb_eval(eb, lambda t, p=pts: p if t == "Null.SBit[5]" else _fail(t))
        assert got == J.treasure_hunter_rank(pts)[0], pts


def test_hunt_winner_clamp_folds_every_out_of_range_byte_to_row_zero():
    """`eb_bounds` reports 0..255 here because interval arithmetic is CORRELATION-BLIND -- it cannot
    see that the multiplicand and the predicate are the same byte. Only evaluation shows the clamp
    works, and this is the row where a BLANK line (GetStringFromTable returns String.Empty above the
    row count, ETb.cs:278) would read as a bug."""
    eb = _rspec("minigame.hunt_winner").eb
    assert J.eb_bounds(eb) == (0, 255)
    for b in range(256):
        g = _geg(hunt_winner=b)
        got = J.eb_eval(eb, J.eb_geg_reader(g))
        assert got == (b if b <= 3 else 0), b
        if b <= 3:                                        # inside the table the two renderers agree
            assert got == _val(_state(g), "minigame.hunt_winner").value


# ---- THE UNIT LAW: the two renderers publish ONE number, or DECLARE the conversion ---------------
def test_the_cross_validated_rows_are_the_ONLY_geg_backed_rows():
    """The cross set may not quietly shrink. Every row whose expression reads gEventGlobal and whose
    offline reader reads the same heap is IN it -- a new row cannot be added to the catalog and left
    out of the bracket the way meta.play_time was left out of it (which is how a seconds-vs-hours
    divergence survived: it was excluded from the family that would have caught it)."""
    def geg_readable(eb):
        """Membership is DERIVED, not listed: can `eb_geg_reader` drive this whole expression? That
        is exactly the condition under which the bracket can be built, so the set cannot be pruned by
        editing a literal."""
        try:
            J.eb_eval(eb, J.eb_geg_reader(_geg()))
            return True
        except J.EbBoundsError:                 # B_SYSVAR / B_HAVE_ITEM / Null.SBit -- not the heap
            return False

    geg_backed = {s.id for s in J.ROWS
                  if s.eb and s.status == "tracked" and s.read is not None and geg_readable(s.eb)}
    # hunt_winner is the ONE exemption: its upward clamp is correlation-dependent, so it gets an
    # exhaustive all-256-bytes test of its own instead of one sample here.
    assert geg_backed - set(_GEG_CROSS_ROWS) == {"minigame.hunt_winner"}
    assert set(_GEG_CROSS_ROWS) <= geg_backed


def test_every_expression_declares_its_unit_relation_to_the_offline_reader():
    """`eb_scale` has no silent default to fall into: scale 1 means "the same integer" (the bet), and
    anything else is a DECLARED conversion with a unit that the in-game page renders. lint_rows
    refuses a scale without a unit, a unit without a scale, and either on an eb-less row."""
    for s in J.ROWS:
        assert isinstance(s.eb_scale, int) and s.eb_scale >= 1, s.id
        assert (s.eb_scale != 1) == bool(s.eb_unit), s.id
        assert s.eb is not None or (s.eb_scale == 1 and not s.eb_unit), s.id
    assert {rid for rid, (sc, _u) in J.EB_SCALE.items() if sc != 1} == {"meta.play_time"}
    for rid in _GEG_CROSS_ROWS:                 # the raw-comparison family is scale-1 BY DEFINITION
        assert _rspec(rid).eb_scale == 1, rid


def test_play_time_the_two_renderers_AGREE_UNDER_THE_DECLARED_SCALE():
    """THE ROW THAT BROKE THE BET, now bracketed. `journal report` publishes 27733 (the 95000_Setting
    seconds Double) and the field page publishes 7 (hours) for ONE row id. That is legal only because
    journal.EB_SCALE declares the conversion -- and this is the test that makes the declaration mean
    something: offline // eb_scale == eb_eval, exactly, at several magnitudes."""
    spec = _rspec("meta.play_time")
    assert (spec.eb_scale, spec.eb_unit) == (3600, "h")
    for secs in (0, 59, 3599, 3600, 27733, 88044, 2160001):
        offline = _val(_state(setting=_setting(secs + 0.4)), "meta.play_time")
        assert offline.value == secs                              # the ROW value is SECONDS
        assert J.eb_eval(spec.eb, lambda t, v=secs: v) == secs // spec.eb_scale
    assert J.eb_eval(spec.eb, lambda t: 27733) == 7               # the number the PAGE renders


def test_an_UNDECLARED_unit_change_FAILS_lint():
    """The negative twin: divide inside an expression without saying so and the gate fires."""
    s = _replace(_rspec("party.gil"), eb="B_SYSVAR[6] const(1000) B_DIV", eb_scale=1000)
    assert any("eb_scale / eb_unit must be set together" in m for m in J.lint_rows(rows=[s]))
    s = _replace(_rspec("party.gil"), eb_unit="k")
    assert any("eb_scale / eb_unit must be set together" in m for m in J.lint_rows(rows=[s]))
    s = _replace(_rspec("meta.bestiary"), eb_scale=3600, eb_unit="h")
    assert any("meaningless without an eb" in m for m in J.lint_rows(rows=[s]))
    s = _replace(_rspec("party.gil"), eb_scale=0)
    assert any("eb_scale must be an int >= 1" in m for m in J.lint_rows(rows=[s]))


def test_an_expression_that_DIVIDES_without_declaring_a_scale_FAILS_lint():
    """The rule sits at the exact site the defect appeared. Delete meta.play_time's EB_SCALE entry
    and `journal lint` goes RED instead of quietly re-publishing hours as if they were seconds --
    which is what happened before, because a consistent (scale 1, unit "") schema is indistinguishable
    from a row whose renderers agree."""
    s = _replace(_rspec("meta.play_time"), eb_scale=1, eb_unit="")
    assert any("eb divides but declares eb_scale 1" in m for m in J.lint_rows(rows=[s]))
    assert not [m for m in J.lint_rows(rows=[_rspec("meta.play_time")]) if "divides" in m]
    # ...and the narrowness is deliberate: a SHIFT is bitfield extraction, not a unit change.
    assert "B_SHIFT_RIGHT" in _rspec("minigame.ragtime_quiz").eb
    assert _rspec("minigame.ragtime_quiz").eb_scale == 1
    assert not [m for m in J.lint_rows(rows=[_rspec("minigame.ragtime_quiz")]) if "divides" in m]


def test_a_SCALE_whose_expression_was_deleted_FAILS_lint():
    """A scale orphaned by a row rename would silently fall back to 1 -- i.e. back to "they agree"
    with nothing having checked that they do."""
    saved = dict(J.EB_SCALE)
    J.EB_SCALE["party.gil"] = (60, "m")                   # a row with an eb but no EB_SCALE entry...
    try:
        assert not [m for m in J.lint_rows() if "EB_SCALE" in m]      # ...that one is legal on its own
        J.EB_SCALE["chocobo.beak_level_typo"] = (60, "m")
        msgs = J.lint_rows()
        assert any("not in ROWS" in m for m in msgs)
        assert any("no EB_EXPRESSIONS entry" in m for m in msgs)
    finally:
        J.EB_SCALE.clear()
        J.EB_SCALE.update(saved)


def test_rows_json_carries_the_unit_relation():
    """`journal rows --json` is what a later catalog and the in-game screen both eat, so the scale
    has to travel WITH the expression -- a consumer must never have to guess the unit."""
    d = {r["id"]: r for r in J.rows_json()}
    assert d["meta.play_time"]["eb_scale"] == 3600 and d["meta.play_time"]["eb_unit"] == "h"
    assert d["party.gil"]["eb_scale"] == 1 and d["party.gil"]["eb_unit"] == ""


def test_key_items_expression_counts_the_SAME_set_as_the_offline_row():
    """SOURCE-OVER-DESIGN. `B_HAVE_ITEM` on an important id -> FF9Item_GetCount_Generic ->
    FF9Item_IsExistImportant (ff9item.2.cs:229, :343-345) == `rare_item_obtained.Contains(id)`, and
    the offline row counts entries whose `obtained` flag is true (JsonParser.cs:1004). A key item
    that is USED is still obtained -- FF9Item_UseImportant only ADDS to `rare_item_used`
    (ff9item.2.cs:333-336). So the two readers describe ONE quantity and the catalog keeps ONE row."""
    held = {0, 4, 7}
    rows = tuple((i, True, i == 4) for i in sorted(held))         # id 4 obtained AND used
    offline = _val(_state(common=_common(keyitems=rows)), "party.key_items")
    got = J.eb_eval(_rspec("party.key_items").eb,
                    lambda t: int(int(t[len("B_HAVE_ITEM("):-1]) - J.ITEM_IMPORTANT_BASE in held))
    assert got == offline.value == len(held)


def test_key_item_expression_spans_exactly_the_baked_window():
    ids = [int(t[len("const("):-1]) for t in _rspec("party.key_items").eb.split()
           if t.startswith("const(")]
    assert ids == list(range(J.ITEM_IMPORTANT_BASE, J.ITEM_IMPORTANT_BASE + J.KEY_ITEM_EB_COUNT))


def test_card_expressions_use_the_card_band_and_the_right_shape():
    held = _rspec("minigame.cards_held").eb
    kinds = _rspec("minigame.card_kinds").eb
    for eb in (held, kinds):
        ids = [int(t[len("const("):-1]) for t in eb.split()
               if t.startswith("const(") and int(t[len("const("):-1]) >= J.ITEM_CARD_BASE]
        assert ids == list(range(J.ITEM_CARD_BASE, J.ITEM_CARD_BASE + J.CARD_KINDS_MAX))
    # kinds counts DISTINCT ids (`> 0`), held counts copies. Two engine functions, two shapes.
    assert " B_GT" in kinds and " B_GT" not in held
    deck = {512: 3, 517: 1, 600: 2}                               # 3 kinds, 6 copies
    read = lambda t: deck.get(int(t[len("B_HAVE_ITEM("):-1]), 0)  # noqa: E731
    assert J.eb_eval(held, read) == 6
    assert J.eb_eval(kinds, read) == 3


def test_rows_json_carries_the_in_game_half():
    """`journal rows --json` is the permanent contract a catalog and the in-game screen both eat."""
    d = {r["id"]: r for r in J.rows_json()}
    assert d["party.gil"]["eb"] == "B_SYSVAR[6]"
    assert d["party.gil"]["eb_source"] == "EventEngine.GetSysvar.cs:31-32"
    assert d["party.gil"]["eb_absent"] is None
    assert d["meta.bestiary"]["eb"] is None and d["meta.bestiary"]["eb_absent"]
    json.dumps(J.rows_json())                             # still pure JSON: no callables leaked


def test_the_eb_tables_cannot_orphan_a_decision():
    """A row RENAME must fail loudly rather than silently dropping its expression."""
    saved = dict(J.EB_EXPRESSIONS)
    J.EB_EXPRESSIONS["party.gil_typo"] = ("B_SYSVAR[6]", "EventEngine.GetSysvar.cs:31-32")
    try:
        assert any("not in ROWS" in m for m in J.lint_rows())
    finally:
        J.EB_EXPRESSIONS.clear()
        J.EB_EXPRESSIONS.update(saved)
    assert not J.lint_rows()
