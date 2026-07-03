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
