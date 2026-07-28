"""The Info Hub's Behavior ARCHETYPE cards -- derived from the Behavior tab's own stamp
tables (``behaviorscan.BEHAVIOR_ARCHETYPES`` + ``stamp_siege``), so these fences are the
derivation proof: a new archetype must land as a card with zero Hub edits, and every
card's snippet is the REAL stamp op's output -- parsed, seated, and validate-clean."""

from __future__ import annotations

import tomllib

from ff9mapkit import infohub
from ff9mapkit.content import behaviortoml as BT
from ff9mapkit.workspace import behaviorscan as BS


def test_cards_derive_from_the_stamp_tables():
    names = [e.name for e in infohub.behavior_entries()]
    assert names == [a["key"] for a in BS.BEHAVIOR_ARCHETYPES] + ["siege"]
    for e in infohub.behavior_entries():
        assert e.kind == "behavior" and e.summary       # the teach text IS the search body


def test_cards_are_picker_only_like_encounters():
    assert len(infohub.browse("", kinds=["behavior"], limit=None)) == \
        len(infohub.behavior_entries())
    assert not [e for e in infohub.browse("", limit=None) if e.kind == "behavior"]


def test_every_archetype_snippet_is_the_stamps_own_output_and_validates():
    for e in infohub.behavior_entries():
        if e.name == "siege":
            continue
        d = tomllib.loads(infohub.snippet(e))
        assert "behavior" in d, e.name
        # seat the placeholder npcs the snippet's header names, then the compiler judges
        raw = {"player": {"spawn": [0, 0]},
               "npc": [{"name": "npc_a", "pos": [0, 0]}, {"name": "npc_b", "pos": [400, 0]}],
               **d}
        assert BT.validate(raw) == [], (e.name, BT.validate(raw))


def test_the_siege_card_is_stamp_parity():
    e = next(x for x in infohub.behavior_entries() if x.name == "siege")
    d = tomllib.loads(infohub.snippet(e))
    scratch = {"player": {"spawn": [0, 0]}}
    BS.stamp_siege(scratch)
    assert d["siege"] == scratch["siege"]               # the card IS the stamp, byte-honest


def test_detail_teaches_the_doorway():
    for e in infohub.behavior_entries():
        det = infohub.detail(e)
        assert det.snippet and any(lbl == "in the app" for lbl, _v in det.facts), e.name
    guard = infohub.detail(next(x for x in infohub.behavior_entries() if x.name == "guard"))
    assert any("TARGET" in v for _l, v in guard.facts)
