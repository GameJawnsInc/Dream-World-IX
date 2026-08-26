"""The entry catalog (journalcatalog.py) -- the shipped catalog is law-clean, and EVERY law is
provable-breakable (a lint that cannot fail is not a lint -- feedback-a-check-that-cannot-fail):
each law gets a constructed violation and the test asserts the lint names it.

The atlas join (LAW 2's research half) is tested against a FABRICATED mini-atlas so the laws are
exercised install-free; the real treasure_join.json cross-check additionally runs when the
research artifact is present.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ff9mapkit import journalcatalog as JC

_ATLAS = (Path(__file__).resolve().parents[2]
          / "studies" / "completion-journal" / "research" / "treasure_join.json")


def _entry(**kw):
    base = dict(id="treasure.b9999", section="d1.prima-vista", category="treasure", latch=9999)
    base.update(kw)
    return JC.Entry(**base)


@pytest.fixture(scope="module")
def catalog():
    return JC.load_catalog()


# ============================ the shipped catalog ============================
def test_shipped_catalog_loads_and_is_law_clean(catalog):
    sections, entries, deferred = catalog
    assert len(sections) >= 55          # the whole walkthrough spine ships from day one
    assert len(entries) >= 30           # d1.prima-vista, the first authored section
    assert JC.lint_catalog(sections, entries, deferred) == []


def test_prima_vista_is_fully_authored(catalog):
    _s, entries, _d = catalog
    pv = JC.entries_for("d1.prima-vista", catalog=catalog)
    assert len(pv) == 30
    # every row: prose detail present, a real predicate, census provenance, honest verify
    for e in pv:
        assert e.predicate() == "latch"
        assert e.detail, f"{e.id}: the prose pass may not ship an empty detail"
        assert e.provenance == "census"
    # verify flips ONLY on an owner report. The New Game playtest (2026-08-26) exercised exactly
    # two latches live -- the cargo-hold pair flipped OK on pickup; every other row stays honest.
    verified = {e.latch for e in pv if e.verify == "playtested"}
    assert verified == {7174, 7175}
    assert all(e.verify == "unverified" for e in pv if e.latch not in verified)
    # the four ship rows come first -- the walkthrough starts on the Prima Vista
    assert [e.latch for e in pv[:4]] == [7174, 7175, 7171, 7172]


def test_sections_cover_all_four_discs_plus_side(catalog):
    sections, _e, _d = catalog
    assert {s.disc for s in sections} == {0, 1, 2, 3, 4}
    assert any(s.side for s in sections)
    pv = next(s for s in sections if s.id == "d1.prima-vista")
    assert pv.sc_enter == 1000 and pv.sc_leave == 2020   # anchors, not hand-invented


# ============================ every law breaks ============================
def test_law1_two_predicates_refused():
    e = _entry(latch=9999, inventory=236)
    assert any("LAW 1" in p for p in JC.lint_catalog((), (e,)))


def test_law1_no_predicate_refused():
    e = _entry(latch=None)
    assert any("LAW 1" in p for p in JC.lint_catalog((), (e,)))


def test_law2_duplicate_bit_refused():
    e1 = _entry(id="treasure.b9999")
    e2 = _entry(id="treasure.b9999x")
    assert any("LAW 2" in p and "already claimed" in p for p in JC.lint_catalog((), (e1, e2)))


def test_law2_bit_out_of_range_refused():
    e = _entry(latch=JC.GLOB_BIT_MAX + 1)
    assert any("outside gEventGlobal" in p for p in JC.lint_catalog((), (e,)))


def test_law3_catchup_bit_refused_as_predicate():
    bit = next(iter(JC.CATCHUP_BITS))
    e = _entry(id=f"treasure.b{bit}", latch=bit)
    assert any("LAW 3" in p for p in JC.lint_catalog((), (e,)))


def test_law4_bad_confidence_refused():
    e = _entry(missable={"close_sc": 4080, "confidence": "certain"})
    assert any("LAW 4" in p for p in JC.lint_catalog((), (e,)))


def test_law4_missing_close_sc_refused():
    e = _entry(missable={"confidence": "derived"})
    assert any("close_sc" in p for p in JC.lint_catalog((), (e,)))


def test_law5_baked_stock_name_refused():
    e = _entry(item=236, title="Potion")     # 236 IS the Potion -- the title bakes the stock name
    assert any("LAW 5" in p for p in JC.lint_catalog((), (e,)))


def test_law5_item_id_out_of_space_refused():
    e = _entry(item=JC.ITEM_ID_MAX + 1)
    assert any("unified item space" in p for p in JC.lint_catalog((), (e,)))


def test_law6_overlong_detail_refused():
    e = _entry(detail="An enormous ramble of a locator sentence that cannot fit one window line")
    assert any("LAW 6" in p for p in JC.lint_catalog((), (e,)))


def test_law7_exclusive_group_of_one_refused():
    e = _entry(exclusive_group="hunt-reward")
    assert any("LAW 7" in p for p in JC.lint_catalog((), (e,)))


def test_law8_crosscheck_with_prose_refused():
    e = _entry(provenance="crosscheck", detail="text that must not ship")
    assert any("LAW 8" in p for p in JC.lint_catalog((), (e,)))


def test_deferral_without_reason_refused():
    d = JC.Deferred(bit=7206, why="")
    assert any("must say why" in p for p in JC.lint_catalog((), (), (d,)))


# ============================ the atlas join breaks (fabricated atlas) ============================
_MINI_ATLAS = {"events": [
    {"bit": 100, "fields": [1], "names": ["RoomA"], "rewards": []},
    {"bit": 101, "fields": [1], "names": ["RoomA"], "rewards": []},
]}


def test_atlas_direction1_unknown_bit_refused():
    e = _entry(id="treasure.b999", latch=999)
    assert any("not in the reward-event atlas" in p
               for p in JC.lint_against_atlas((e,), _MINI_ATLAS))


def test_atlas_direction2_covered_room_gap_refused():
    e = _entry(id="treasure.b100", latch=100)    # covers RoomA; bit 101 lives there too, unlisted
    probs = JC.lint_against_atlas((e,), _MINI_ATLAS)
    assert any("atlas bit 101" in p and "no row" in p for p in probs)


def test_atlas_direction2_deferral_satisfies_the_gap():
    e = _entry(id="treasure.b100", latch=100)
    d = JC.Deferred(bit=101, why="a later visit of RoomA")
    assert JC.lint_against_atlas((e,), _MINI_ATLAS, (d,)) == []


def test_atlas_stale_deferral_refused():
    e1 = _entry(id="treasure.b100", latch=100)
    e2 = _entry(id="treasure.b101", latch=101)
    d = JC.Deferred(bit=101, why="stale -- the row exists now")
    assert any("STALE" in p for p in JC.lint_against_atlas((e1, e2), _MINI_ATLAS, (d,)))


def test_atlas_deferral_for_nonexistent_event_refused():
    e = _entry(id="treasure.b100", latch=100)
    d = JC.Deferred(bit=55555, why="no such event")
    assert any("does not exist is a typo" in p
               for p in JC.lint_against_atlas((e,), _MINI_ATLAS, (d,)))


# ============================ the real atlas, when present ============================
@pytest.mark.skipif(not _ATLAS.exists(),
                    reason="treasure_join.json not regenerated here (research artifact, "
                           "gitignored; run studies/completion-journal/research/treasure_join.py)")
def test_shipped_catalog_joins_the_real_atlas(catalog):
    sections, entries, deferred = catalog
    atlas = json.loads(_ATLAS.read_text(encoding="utf-8"))
    assert JC.lint_against_atlas(entries, atlas, deferred) == []
