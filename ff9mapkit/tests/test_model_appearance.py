"""Offline tests for the engine appearance-logic census (no install needed -- only the GEO name matters).

Encodes THE RULE the Garnet scrunchie taught us: engine per-model appearance logic is NAME-keyed, so an
OVERRIDE preserves it and a MINT bypasses it; and a story-evolved character is several GEO ids, not one.
"""
from ff9mapkit.models import appearance


def test_garnet_override_flags_hairswap_and_story_evolved():
    notes = appearance.appearance_notes("GEO_MAIN_F0_GRN", minted=False)
    joined = " ".join(notes)
    assert "HAIR-SWAP" in joined and "OVERRIDE preserves" in joined      # keeps the engine behavior
    assert "long_hair" in joined and "short_hair" in joined              # names to preserve
    assert "STORY-EVOLVED" in joined and "GEO_MAIN_F1_GRN" in joined     # several ids, not one


def test_garnet_mint_says_bypassed():
    notes = " ".join(appearance.appearance_notes("GEO_MAIN_F0_GRN", minted=True))
    assert "MINT bypasses" in notes and "BOTH long_hair AND short_hair" in notes


def test_zidane_costume_form_flags_texture_reassign():
    notes = " ".join(appearance.appearance_notes("GEO_MAIN_F3_ZDN", minted=False))
    assert "textures per-form" in notes                                  # the ZDN reassign branch
    assert "STORY-EVOLVED" in notes


def test_plain_npc_has_no_notes():
    assert appearance.appearance_notes("GEO_NPC_F1_BBA") == []


def test_id_token_resolves_to_name():
    assert appearance.appearance_notes(185) == appearance.appearance_notes("GEO_MAIN_F0_GRN")
    assert appearance.appearance_notes(999999999) == []                  # unknown id -> nothing


def test_character_forms_and_scenario_gated():
    forms = appearance.character_forms("GEO_MAIN_F0_GRN")
    assert "GEO_MAIN_F0_GRN" in forms and "GEO_MAIN_F8_GRN" in forms and len(forms) == 7
    assert appearance.character_forms("GEO_NPC_F1_BBA") == []            # not a MAIN field model
    assert appearance.is_scenario_gated("GEO_MAIN_F0_GRN")
    assert appearance.is_scenario_gated("GEO_MAIN_F3_ZDN")
    assert not appearance.is_scenario_gated("GEO_MAIN_F0_VIV")           # story-evolved but not name-gated


def test_the_hair_swap_set_matches_the_engine_table():
    # transcribed from ModelFactory.garnetShortHairTable -- the 12 name-keyed models
    assert len(appearance.GARNET_HAIR_SWAP) == 12
    assert "GEO_MAIN_F0_GRN" in appearance.GARNET_HAIR_SWAP
    assert "GEO_MON_B3_149" in appearance.GARNET_HAIR_SWAP


def test_appearance_of_structured_profile():
    grn = appearance.appearance_of("GEO_MAIN_F0_GRN")
    assert grn.scenario_gated and grn.gate_kind == "hair-swap"
    assert grn.story_evolved and grn.special and len(grn.forms) == 7 and "GEO_MAIN_F8_GRN" in grn.forms

    zdn = appearance.appearance_of("GEO_MAIN_F3_ZDN")               # a gated Zidane costume form
    assert zdn.gate_kind == "texture-reassign" and zdn.scenario_gated and zdn.story_evolved

    viv = appearance.appearance_of("GEO_MAIN_F0_VIV")              # story-evolved (F0/F7) but NOT name-gated
    assert viv.story_evolved and not viv.scenario_gated and len(viv.forms) == 2 and viv.special

    mon = appearance.appearance_of("GEO_MON_B3_149")               # a gated hair-swap model that's not a field form
    assert mon.scenario_gated and mon.gate_kind == "hair-swap" and not mon.story_evolved and mon.special

    # a plain model / an unknown id collapse to the identity-comparable singleton
    assert appearance.appearance_of("GEO_NPC_F1_BBA") is appearance.NO_APPEARANCE
    assert appearance.appearance_of(999999999) is appearance.NO_APPEARANCE
    assert not appearance.NO_APPEARANCE.special


def test_catalog_model_carries_appearance():
    from ff9mapkit import catalog as C
    grn = C.model("GEO_MAIN_F0_GRN")
    assert grn.appearance.scenario_gated and grn.appearance.story_evolved
    assert C.model(8).appearance.story_evolved                     # Vivi F0 -> {F0, F7}
    assert not C.model("GEO_NPC_F1_BBA").appearance.special        # a plain NPC carries NO_APPEARANCE
    assert C.model("GEO_NPC_F1_BBA").appearance is appearance.NO_APPEARANCE
