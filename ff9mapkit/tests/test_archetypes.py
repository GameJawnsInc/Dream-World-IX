"""Named NPC archetypes: a friendly name -> model + auto-resolved anims, on top of the catalog pillar.

vivi/zidane must resolve to the EXACT character preset so existing builds stay byte-identical; every
other curated archetype must resolve to a model with a full five-slot gesture set (no half-broken
curation). Pure (no game install needed) -- resolution is identifier-only.
"""
import pytest

from ff9mapkit import archetypes as AR
from ff9mapkit import catalog as C
from ff9mapkit.content.npc import PRESETS


def test_resolve_vivi_zidane_match_character_preset_exactly():
    # the byte-identity contract: archetypes.resolve -> the same (model, animset, anims) the
    # inject_npc(preset=...) path used, so routing builds through it changes no bytes.
    model, animset, anims, dlg = AR.resolve("vivi")
    assert (model, animset, anims) == PRESETS["vivi"]
    assert dlg is None
    assert AR.resolve("zidane")[:3] == PRESETS["zidane"]      # (None, None, None) -> keeps cloned player


def test_resolve_playable_archetype_uses_model_and_auto_anims():
    model, _animset, anims, _dlg = AR.resolve("garnet")
    assert model == C.resolve_model("GEO_MAIN_F0_GRN")
    assert anims == C.npc_anims(model)                        # auto-resolved from the model
    assert set(anims) == {"stand", "walk", "run", "left", "right"}
    assert AR.resolve("dagger")[0] == model                  # alias resolves to the same model


def test_resolve_npc_type_archetype():
    model, _animset, anims, _dlg = AR.resolve("black_mage")
    assert model == C.resolve_model("GEO_NPC_F0_BMG") and C.model(model).token == "BMG"
    assert anims == C.npc_anims(model)


def test_resolve_is_case_insensitive():
    assert AR.resolve("Garnet")[0] == AR.resolve("garnet")[0]


def test_resolve_unknown_raises():
    with pytest.raises(ValueError):
        AR.resolve("totally_not_a_thing")


def test_names_and_is_archetype():
    ns = AR.names()
    for expect in ("vivi", "zidane", "garnet", "steiner", "freya", "black_mage", "moogle"):
        assert expect in ns
    assert AR.is_archetype("Moogle") and not AR.is_archetype("nope")


def test_curation_guard_every_archetype_is_fully_animated():
    """Every curated archetype must place a fully-animated NPC -- a model that can't fill all five
    movement slots is bad curation and fails here offline (zidane is exempt: it keeps the cloned player)."""
    for name in AR.names():
        model, _animset, anims, _dlg = AR.resolve(name)
        if name == "zidane":
            continue
        assert model is not None, name
        assert anims and set(anims) == {"stand", "walk", "run", "left", "right"}, name
