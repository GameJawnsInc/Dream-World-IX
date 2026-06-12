"""The starting-state CAPSTONE example -- ONE entry field.toml composing all FOUR new-game channels:

  [startup]         + [party]        -> the field .eb   (prepended to Main_Init at synthesis)
  [start_inventory] + [[equipment]]  -> the mod-global CSVs (Data/Items + Data/Characters, mod-write stage)

The individual channels are covered by test_startup / test_party / the start-state cases in test_build;
this guards the INTEGRATION -- that building the committed example lands all four in ONE mod folder -- plus
the two capstone DESIGN invariants (the party base + the safe flag band).
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from ff9mapkit import flags
from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import ModLayout
from ff9mapkit.content import party as _pty
from ff9mapkit.content import startup as _su

CAPSTONE = Path(__file__).parents[1] / "examples" / "capstone" / "capstone.field.toml"


def _raw() -> dict:
    with open(CAPSTONE, "rb") as fh:
        return tomllib.load(fh)


def test_capstone_validates_clean():
    assert validate(FieldProject.load(CAPSTONE)) == []


def test_capstone_source_carries_all_four_channels():
    raw = _raw()
    assert "startup" in raw and "party" in raw                 # the two .eb levers
    assert "start_inventory" in raw and raw.get("equipment")   # the two CSV levers


def test_capstone_party_adds_others_not_zidane():
    # At New Game the engine seeds Zidane into party slot 0 (ff9play.FF9Play_SetParty(0, Zidane); slots
    # 1-3 = NONE), so [party] must add the OTHERS only -- re-adding Zidane would duplicate the slot.
    adds = [_pty.resolve_member(m) for m in _raw()["party"]["add"]]
    assert adds == [3, 4]                                       # steiner, freya -> final party Zidane/Steiner/Freya
    assert _pty.resolve_member("zidane") not in adds


def test_capstone_startup_flag_in_safe_band():
    # the [startup] story bit must sit in the custom band (>= FIRST_SAFE_FLAG), clear of real FF9 usage
    for f in _raw()["startup"]["flags"]:
        assert f["flag"] >= flags.FIRST_SAFE_FLAG


def test_capstone_build_emits_all_four_channels(tmp_path):
    out = tmp_path / "mod"
    res = build_mod([FieldProject.load(CAPSTONE)], out)
    L = ModLayout(out.resolve())

    # channels 3 + 4 -- the two mod-global CSVs, in the mod root (not the field bytes)
    inv = L.initial_items_csv.read_text(encoding="utf-8")
    assert "28;1;# Excalibur" in inv and "236;20;# Potion" in inv and "240;5;# PhoenixDown" in inv
    eqp = L.default_equipment_csv.read_text(encoding="utf-8")
    assert "Steiner;3;28;146;-1;189;-1" in eqp and "Zidane" not in eqp   # partial delta, Steiner's row only

    # channels 1 + 2 -- the two .eb levers, prepended verbatim into Main_Init
    raw_eb = L.eb_path("us", "EVT_CAPSTONE.eb.bytes").read_bytes()
    assert _su.startup_body([(8512, 1)], scenario=2600) in raw_eb       # ScenarioCounter + the story bit
    assert _pty.party_body(adds=[3, 4]) in raw_eb                       # add steiner + freya
    assert raw_eb.count(bytes.fromhex("6d2c7f")) == 2                   # exactly two B_PARTYADD, no more

    # the highest-priority-wins / shadow caveat is surfaced as a build warning (the one real footgun)
    assert any("highest-priority-wins" in w.lower() or "shadow" in w.lower() for w in res["warnings"])
