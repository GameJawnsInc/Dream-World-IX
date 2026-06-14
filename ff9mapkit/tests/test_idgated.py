"""The lost-on-a-mint catalog: engine behaviors keyed on a field's real fldMapNo that a fork loses on its
custom id (idgated) -- walkmesh hotfix / narrow-map letterbox / Chocobo HUD / intro FMV. Pure baked data
(no install), so it's unit-testable and safe on the install-free fork-report path.
"""
from __future__ import annotations

from ff9mapkit import idgated as IG


def test_narrow_map_width_baked_and_default():
    assert IG.narrow_map_width(2356) == 350          # Gulug/Room (a narrow field, from MapWidthList)
    assert IG.narrow_map_width(101) == 640           # a wide field
    assert IG.narrow_map_width(4003) == IG.FORK_DEFAULT_WIDTH   # an unlisted custom id -> the fork default
    assert IG.narrow_map_width("2356") == 350        # accepts a numeric string
    assert IG.narrow_map_width(None) == IG.FORK_DEFAULT_WIDTH


def test_loses_letterbox():
    assert IG.loses_letterbox(2356) is True          # 350 < widescreen
    assert IG.loses_letterbox(101) is False          # 640 >= widescreen
    assert IG.loses_letterbox(4003) is False         # custom id (unlisted) -> renders widescreen, nothing to lose
    assert IG.loses_letterbox(99999) is False


def test_lost_on_mint_aggregates():
    labels = lambda f: [lbl for lbl, _ in IG.lost_on_mint(f)]
    # Gulug 2356: a load-time walkmesh hotfix AND a narrow field
    assert labels(2356) == ["walkmesh hotfix", "narrow-map letterbox"]
    # Chocobo's Forest 2950: narrow + the live dig HUD
    assert "Chocobo dig HUD" in labels(2950)
    # field 70: the intro FMV (not in the width table -> not narrow)
    assert labels(70) == ["intro FMV"]
    # a plain wide field loses nothing
    assert IG.lost_on_mint(101) == []
    assert IG.lost_on_mint(99999) == []
    assert IG.lost_on_mint(None) == []


def test_walkmesh_entry_notes_auto_vs_fork_in_place():
    detail = dict(IG.lost_on_mint(2356))["walkmesh hotfix"]
    assert "auto-reproduced" in detail                # 2356 is load-time -> reproduced
    detail2 = dict(IG.lost_on_mint(2803))["walkmesh hotfix"]
    assert "fork-in-place" in detail2                 # 2803 (Daguerreo) is dynamic -> fork in place
