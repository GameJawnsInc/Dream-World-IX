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


def test_set_is_complete_every_field_npc_model_is_named():
    """The gallery-ID loop is COMPLETE: every GEO_NPC field model whose gestures auto-resolve BY NAME to a
    full five-slot set has a named archetype. If the catalog ever gains such a model that nobody named,
    this fails -- so the "complete" claim can't silently rot. (Mirrors tools/build_archetype_gallery's
    unnamed_tokens; lives here so it's guarded by the offline suite.) Uses ``use_catalog=False`` so the bar
    is by-NAME resolvability (the gallery's job) -- NOT "has real clips in the per-model catalog", which
    placeably covers far more models (incl. obscure near-duplicates) than belong in a curated gallery."""
    slots = {"stand", "walk", "run", "left", "right"}
    named = {C.model(AR.resolve(n)[0]).token for n in AR.names() if AR.resolve(n)[0] is not None}
    unnamed = sorted(
        m.token
        for m in C.models(group="NPC", field_only=True)
        if C.npc_anims(m.id, use_catalog=False) and set(C.npc_anims(m.id, use_catalog=False)) == slots
        and m.token not in named
    )
    assert unnamed == [], f"unnamed field-NPC tokens (name them in archetypes.py): {unnamed}"


def test_every_archetype_resolves_stand_to_a_real_idle():
    """A statically-placed NPC plays its ``stand`` slot while standing; npc_anims falls back
    idle->walk->run, so a model with no real 'idle' would visibly animate (moonwalk) in place. The
    in-game verification pass confirmed none do -- guard it so a future archetype whose model lacks
    a real idle gets flagged for review (zidane exempt: it keeps the cloned player)."""
    for name in AR.names():
        if name == "zidane":
            continue
        model = AR.resolve(name)[0]
        assert "idle" in C.animations_for_model(model), \
            f"{name} ({C.model(model).name}) has no real idle -> would animate while standing"
