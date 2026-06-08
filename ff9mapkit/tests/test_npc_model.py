"""Offline (no game install) checks for the Info-Hub-backed [[npc]] model wiring.

These exercise build.resolve_npc_model / validate / lint_logic directly -- no field is built -- so they
run without the byte-level base templates (unlike test_build, which conftest skips when the FF9-derived
assets aren't extracted). They lock in:
  * [[npc]] model accepts an exact GEO name (resolved via the catalog) as well as a raw id;
  * a bad model NAME is a fatal validate() problem (a clean message instead of a build crash);
  * a raw model/animation id outside the known tables is a non-fatal lint warning (catches typos
    offline before they silently break in-game).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject, lint_logic, resolve_npc_model, validate


def _proj(npc=None, cutscene=None):
    """A minimal otherwise-valid project (field + a pitch camera) so validate()'s only complaint is the
    content we're probing."""
    raw = {"field": {"id": 4003, "name": "T", "area": 11},
           "camera": {"pitch": 40, "distance": 3000, "fov": 42},
           "npc": npc or []}
    if cutscene:
        raw["cutscene"] = cutscene
    return FieldProject(raw, Path("."))


def test_resolve_npc_model_passthrough_and_name():
    assert resolve_npc_model(None) is None
    assert resolve_npc_model(8) == 8                       # raw id unchanged -> golden builds byte-identical
    assert resolve_npc_model("8") == 8
    assert resolve_npc_model("GEO_MAIN_F0_VIV") == 8       # exact GEO name -> id
    assert resolve_npc_model("geo_main_f0_viv") == 8       # case-insensitive
    assert resolve_npc_model(999999) == 999999             # an unknown raw id passes through (lint warns)
    with pytest.raises(ValueError):
        resolve_npc_model("GEO_NOPE")
    with pytest.raises(ValueError):
        resolve_npc_model(True)                            # a boolean is never a model


def test_validate_flags_unknown_npc_model_name():
    bad = validate(_proj(npc=[{"name": "guard", "pos": [0, 0], "model": "GEO_NOPE"}]))
    assert any("model" in p and "guard" in p for p in bad)          # a bad NAME is a fatal problem
    good = validate(_proj(npc=[{"name": "guard", "pos": [0, 0], "model": "GEO_NPC_F0_BAR"}]))
    assert good == []                                               # a real GEO name builds clean
    raw_id = validate(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 999999}]))
    assert not any("model:" in p for p in raw_id)                   # an unknown raw id is NOT fatal (lint only)


def test_lint_warns_on_unknown_model_and_animation_ids():
    w = lint_logic(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 999999,
                               "anims": {"stand": 999999999}}]))
    assert any("model id 999999" in x for x in w)
    assert any("anims" in x and "999999999" in x for x in w)
    clean = lint_logic(_proj(npc=[{"name": "g", "pos": [0, 0], "model": 8, "anims": {"stand": 148}}]))
    assert not any("model table" in x or "known animation" in x for x in clean)
    wc = lint_logic(_proj(npc=[{"name": "a", "pos": [0, 0], "preset": "vivi"}],
                          cutscene={"actor": "a", "steps": [{"animation": 999999999}]}))
    assert any("animation id 999999999" in x for x in wc)
