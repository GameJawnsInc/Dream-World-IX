"""Item name <-> id resolution (pure; baked from Memoria's RegularItem enum, no game data). Lets an
author write give_item = ["Potion", 1] instead of memorizing 236 (and catches the 232=Sapphire trap)."""

from __future__ import annotations

import pytest

from ff9mapkit import items
from ff9mapkit.content import event
from ff9mapkit.eb import opcodes


def test_resolve_names_case_space_hyphen_insensitive():
    assert items.resolve("Potion") == 236
    assert items.resolve("potion") == 236
    assert items.resolve("Hi-Potion") == 237
    assert items.resolve("hi potion") == 237
    assert items.resolve("phoenix down") == 240
    assert items.resolve("Sapphire") == 232          # the gem we mistook for a Potion


def test_resolve_numeric_passthrough_and_range():
    assert items.resolve(236) == 236
    assert items.resolve("236") == 236
    with pytest.raises(ValueError):
        items.resolve(999)


def test_resolve_unknown_name_raises_with_hint():
    with pytest.raises(ValueError):
        items.resolve("Megalixir")                   # not an FF9 item


def test_name_of():
    assert items.name_of(236) == "Potion"
    assert items.name_of(232) == "Sapphire"


def test_give_item_accepts_a_name():
    # the whole point: give_item("Potion") and give_item(236) produce the same AddItem bytes
    assert event.give_item("Potion", 1) == opcodes.add_item(236, 1)
    assert event.give_item(236, 1) == opcodes.add_item(236, 1)
