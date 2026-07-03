"""Offline tests for new-GEO-id minting (no install / UnityPy needed).

Minting adds a NEW additive GEO model id (a fresh SetModel target) rather than overriding a real one --
DLL-free, via the engine's `3DModel <id> <name>` DictionaryPatch directive. The manifest logic
(`mint.resolve_mint` / `mint_manifest`) is pure (name<->id + catalog anims, no p0data), so the id-band
rule, name derivation/validation, the emitted directive, and the animset-borrowing are all testable here;
the actual FBX write (`export_mint`) needs the install and is covered by the in-game mint proof.
"""
import pytest

from ff9mapkit.models import mint


def test_manifest_from_real_model_derives_name_type_directive_and_anims():
    man = mint.resolve_mint({"id": 6000, "from": "GEO_NPC_F1_BBA"})
    assert man["id"] == 6000
    assert man["name"] == "GEO_NPC_F1_M000"         # novel token M<id-band>, source group+form kept
    assert man["type_int"] == 4                     # NPC -> 4 (sets the Models/4/ path)
    assert man["directive"] == "3DModel 6000 GEO_NPC_F1_M000"
    assert man["source"] == "GEO_NPC_F1_BBA"
    # animset borrowed from the source: its anim IDS resolve by NAME to the source's folder in-engine
    assert man["anims_from"] == "GEO_NPC_F1_BBA"
    assert isinstance(man["anims"], dict) and man["anims"].get("stand")


def test_type_int_tracks_the_name_group():
    assert mint.type_int_of_name("GEO_MON_F0_M00") == 3
    assert mint.type_int_of_name("GEO_ACC_F0_M01") == 1
    assert mint.type_int_of_name("GEO_SUB_F0_M02") == 5
    with pytest.raises(ValueError):
        mint.type_int_of_name("GEO_XXX_F0_M00")     # unknown group


def test_derive_name_is_novel_unique_per_id():
    n1 = mint.derive_mint_name("GEO_NPC_F1_BBA", 6000)
    n2 = mint.derive_mint_name("GEO_MON_F0_ZZZ", 6042)
    assert n1 == "GEO_NPC_F1_M000" and n2 == "GEO_MON_F0_M042"
    assert n1 not in mint.extract._NAME_TO_ID     # not a real FF9 name
    # bijective: same-suffix ids (6000 vs 6100) must NOT collide (a shared name corrupts the reverse map)
    assert mint.derive_mint_name("GEO_NPC_F1_BBA", 6000) != mint.derive_mint_name("GEO_NPC_F1_BBA", 6100)


def test_band_floor_is_enforced():
    with pytest.raises(ValueError, match="mint band"):
        mint.resolve_mint({"id": 5511, "from": "GEO_NPC_F1_BBA"})   # a real id -> would overwrite it
    with pytest.raises(ValueError, match="mint band"):
        mint.resolve_mint({"id": 5999, "from": "GEO_NPC_F1_BBA"})


def test_real_name_is_rejected_to_protect_the_reverse_lookup():
    # reusing a real name would hijack GetGEOID(name) -> the real model's path breaks
    with pytest.raises(ValueError, match="REAL FF9 model name"):
        mint.resolve_mint({"id": 6000, "from": "GEO_NPC_F1_BBA", "name": "GEO_NPC_F1_BBA"})


def test_from_xor_fbx_and_at_least_one():
    with pytest.raises(ValueError, match="both `from` and `fbx`"):
        mint.resolve_mint({"id": 6000, "from": "GEO_NPC_F1_BBA", "fbx": "x.fbx"})
    with pytest.raises(ValueError, match="from|fbx"):
        mint.resolve_mint({"id": 6000})
    with pytest.raises(ValueError):
        mint.resolve_mint({"from": "GEO_NPC_F1_BBA"})   # no id


def test_fbx_form_needs_a_name_and_carries_it():
    with pytest.raises(ValueError, match="with .fbx. needs"):
        mint.resolve_mint({"id": 6000, "fbx": "mymodel/6000.fbx"})
    man = mint.resolve_mint({"id": 6000, "fbx": "mymodel/6000.fbx", "name": "GEO_MON_F0_M00",
                             "anims_from": "GEO_MON_F0_BAN"})
    assert man["type_int"] == 3 and man["directive"] == "3DModel 6000 GEO_MON_F0_M00"
    assert man["source"] is None and man["fbx"] == "mymodel/6000.fbx"
    assert man["anims"] and man["anims"].get("stand")   # borrowed from anims_from


def test_dictionary_lines_emits_mint_directives_before_fields_and_dedups():
    from ff9mapkit.build import FieldResult, _dictionary_lines
    r1 = FieldResult(dict_line="FieldScene 4003 11 TESTROOM TESTROOM 1073",
                     mint_lines=["3DModel 6000 GEO_NPC_F1_M00"])
    r2 = FieldResult(dict_line="FieldScene 4004 11 OTHER OTHER 1073",
                     mint_lines=["3DModel 6000 GEO_NPC_F1_M00", "3DModel 6001 GEO_MON_F0_M01"])
    lines = _dictionary_lines([r1, r2])
    assert lines.count("3DModel 6000 GEO_NPC_F1_M00") == 1     # deduped across members
    assert "3DModel 6001 GEO_MON_F0_M01" in lines
    # every 3DModel line precedes every FieldScene line (registration order: ids before their users)
    last_mint = max(i for i, ln in enumerate(lines) if ln.startswith("3DModel"))
    first_field = min(i for i, ln in enumerate(lines) if ln.startswith("FieldScene"))
    assert last_mint < first_field
