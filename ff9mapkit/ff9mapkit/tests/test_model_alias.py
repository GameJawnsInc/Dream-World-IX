"""Offline tests for the model-alias chain (the battle-model export-gap fix; no install needed).

The engine loads ~71 catalog models' GEOMETRY from a DONOR prefab (``CheckUpscale`` ->
``GetRenameModelPath``, ModelFactory.cs): every character BATTLE form's body is the very prefab its
FIELD form loads (``GEO_MAIN_B0_000`` -> 98), bosses borrow character bodies, alt outfits share the
base prefab. Pre-fix, ``resolve_geo``'s requested-id lookup raised a fake
``models/2/5414/5414.fbx``-not-found for all of them. The fix: :func:`extract.resolve_prefab`
replays the engine chain from the baked ``_modelalias`` tables -- IDENTITY (``resolve_geo``, what
animations key off) stays the requested id; only the geometry lookup and the loose-override target
follow the chain. Chains pinned here were measured against the real install (prefab presence probed
in p0data4) on 2026-07-10; the numbers match the re-verified gap memo exactly.
"""
import pytest

from ff9mapkit._modeldb import MODELS
from ff9mapkit.models import export, extract
from ff9mapkit.models.appearance import appearance_notes


# ------------------------------------------------------------------ resolve_prefab: the engine chain

def test_battle_form_resolves_to_the_shared_field_prefab():
    """GEO_MAIN_B0_000 (Zidane battle) -> GEO_MAIN_UP0_ZDN -> GEO_MAIN_F0_ZDN = prefab 98: the battle
    BODY is the same prefab the field loads (the corrected diagnosis -- battle_model0/1 is a 103-vert
    overlay, NOT the body). A digit token resolves identically."""
    assert extract.resolve_prefab("GEO_MAIN_B0_000") == ("GEO_MAIN_F0_ZDN", 98, 2)
    assert extract.resolve_prefab("5414") == ("GEO_MAIN_F0_ZDN", 98, 2)
    # identity is untouched: animations key off the REQUESTED id (5414 = the 36 battle clips)
    assert extract.resolve_geo("GEO_MAIN_B0_000") == ("GEO_MAIN_B0_000", 5414, 2)


def test_vivi_battle_form_is_its_own_prefab():
    """GEO_MAIN_B0_006 -> GEO_MAIN_UP0_VIV -> back to GEO_MAIN_B0_006 (5415): Vivi's battle model is
    the genuine own-prefab case (why WarpedEdge's Vivi animation edits worked before the fix)."""
    assert extract.resolve_prefab("GEO_MAIN_B0_006") == ("GEO_MAIN_B0_006", 5415, 2)


def test_alias_crosses_groups_and_takes_the_upscaled_groups_type_dir():
    """GEO_MAIN_B0_015 (Blank battle) -> GEO_SUB_UP0_BLN -> GEO_SUB_F0_BLN: a MAIN-group request whose
    prefab ships under models/5/ -- the type dir comes from the POST-UPSCALE name's group (the
    engine's GetModelType reads the upscalePath), not the requested group."""
    assert extract.resolve_prefab("GEO_MAIN_B0_015") == ("GEO_SUB_F0_BLN", 5467, 5)


def test_mask_prefabs_are_forced_into_the_sub_dir():
    """GEO_MON_B3_183/184 resolve to their OWN ids but the prefabs ship under models/5/ (the
    GetRenameModelPath ``geoId == 429 || 430 -> ModelType.sub`` override; disc-verified: models/5/429
    exists, models/3/429 does not). A tint-only redirect -- the id alone isn't the whole target."""
    assert extract.resolve_prefab("GEO_MON_B3_183") == ("GEO_MON_B3_183", 429, 5)
    assert extract.resolve_prefab("GEO_MON_B3_184") == ("GEO_MON_B3_184", 430, 5)


def test_boss_aliases_to_a_main_field_body():
    """GEO_MON_B3_172 (the IsUseAsEnemyCharacter set) -> GEO_MAIN_F0_KUI = 273: some bosses ARE
    character bodies."""
    assert extract.resolve_prefab("GEO_MON_B3_172") == ("GEO_MAIN_F0_KUI", 273, 2)


def test_zidane_alt_outfits_share_prefab_98():
    for form in ("GEO_MAIN_F3_ZDN", "GEO_MAIN_F4_ZDN", "GEO_MAIN_F5_ZDN"):
        assert extract.resolve_prefab(form) == ("GEO_MAIN_F0_ZDN", 98, 2)


def test_field_variant_aliases():
    """Not just battle forms: GEO_MAIN_F1_GRN (Garnet's gown variant) failed export pre-fix too --
    its prefab is F0's. Garnet's F4 shares F3's prefab (upscaleTable F4->UP3->F3)."""
    f0 = extract.resolve_geo("GEO_MAIN_F0_GRN")
    assert extract.resolve_prefab("GEO_MAIN_F1_GRN") == (f0[0], f0[1], 2)
    f3 = extract.resolve_geo("GEO_MAIN_F3_GRN")
    assert extract.resolve_prefab("GEO_MAIN_F4_GRN") == (f3[0], f3[1], 2)


def test_accessory_f0_points_at_its_f1_twin():
    """The 3 accessory aliases (LTT/TKT/HDB): the F0 name has no prefab; F1 carries the geometry
    (revertUpscaleTable maps F0 -> F1 directly -- the chain works on never-upscaled names too)."""
    assert extract.resolve_prefab("GEO_ACC_F0_LTT") == ("GEO_ACC_F1_LTT", 396, 1)


def test_unaliased_models_keep_their_identity():
    """The 639 un-aliased models (and self-looping chains like F0_VIV -> UP1_VIV -> F0_VIV) resolve to
    themselves -- the fix is a no-op for every model that already worked (proven byte-identical
    exports for ZDN/VIV/BBA/GRN/WEP)."""
    for tok in ("GEO_MAIN_F0_ZDN", "GEO_MAIN_F0_VIV", "GEO_NPC_F1_BBA", "GEO_WEP_B1_021",
                "GEO_MAIN_B2_001", "GEO_SUB_W0_001", "GEO_MON_F0_EFM"):
        geo, gid, tint = extract.resolve_geo(tok)
        assert extract.resolve_prefab(tok) == (geo, gid, tint), tok


def test_catalog_closure_and_alias_census():
    """Every catalog entry resolves without error to a catalog-listed prefab with a real type dir;
    exactly 71 have a differing prefab (name, id or type dir). Reconciliation with the re-verified
    gap memo: 71 = the 60 alias-RESCUED entries (no own-id prefab on disc -> export failed pre-fix)
    + 11 whose own-id prefab exists but the engine loads the donor anyway (CheckUpscale always
    applies -- pre-fix exported a prefab the game never renders)."""
    redirected = 0
    for gid, name in MODELS.items():
        geo, g, t = extract.resolve_geo(name)
        pgeo, pgid, ptint = extract.resolve_prefab(name)
        assert pgeo in extract._NAME_TO_ID, f"{name}: prefab {pgeo} not a catalog name"
        assert 1 <= ptint <= 6, f"{name}: bad prefab type {ptint}"
        if (pgeo, pgid, ptint) != (geo, g, t):
            redirected += 1
    assert redirected == 71


def test_geoid_specials_are_inert_for_catalog_names():
    """GetGEOID's two hardcoded names (GEO_MON_B3_110 -> 347, GEO_MON_B3_109 -> 5461) are NOT in the
    GEO table -- they exist only for direct engine-path calls, so no catalog chain can reach them
    (347/5461 are the EFM forms' own ids). Baked for engine-exactness; documented inert here."""
    assert "GEO_MON_B3_110" not in extract._NAME_TO_ID
    assert "GEO_MON_B3_109" not in extract._NAME_TO_ID
    assert MODELS[347] == "GEO_MON_F2_EFM" and MODELS[5461] == "GEO_MON_F0_EFM"


# ------------------------------------------------------------------ the per-form overlay hide rule

def test_is_battle_form():
    assert extract.is_battle_form("GEO_MAIN_B0_000")
    assert extract.is_battle_form("GEO_MON_B3_172")
    assert not extract.is_battle_form("GEO_MAIN_F0_ZDN")
    assert not extract.is_battle_form("GEO_SUB_W0_001")
    assert not extract.is_battle_form("GEO_MAIN_UP0_ZDN")     # upscale-space names are not battle forms


def test_overlay_hide_prefixes_by_form():
    """Field/world forms hide battle_model* (unchanged old behavior); battle forms hide field_model*
    and KEEP the battle overlay; ZIDANE_SWORD (B0_001) hides BOTH (HideZidaneOrichalcum -> body only,
    the adversarial clincher: if battle_model were the body, the sword form would be invisible)."""
    assert extract.overlay_hide_prefixes("GEO_MAIN_F0_ZDN") == ("battle_model",)
    assert extract.overlay_hide_prefixes("GEO_SUB_W0_001") == ("battle_model",)
    assert extract.overlay_hide_prefixes("GEO_MAIN_B0_000") == ("field_model",)
    assert set(extract.overlay_hide_prefixes("GEO_MAIN_B0_001")) == {"battle_model", "field_model"}


# ------------------------------------------------------------------ strip_overlay_meshes (deploy gate)

def _mesh(name, nverts, mat_idx):
    verts = [[float(i), 0.0, 0.0] for i in range(nverts)]
    tris = [[i, i + 1, i + 2] for i in range(0, nverts - 2, 3)]
    return {"name": name, "verts": verts, "normals": [[0.0, 1.0, 0.0]] * nverts,
            "uvs": [[0.0, 0.0]] * nverts, "submeshes": [{"material_idx": mat_idx, "tris": tris}],
            "weights": [[(0, 1.0)]] * nverts, "parent": None}


def test_strip_overlay_drops_the_overlay_and_compacts_materials():
    """A B0_000-shaped struct: the battle_model* meshes are dropped for a loose-override deploy (the
    engine's name-hide can't fire on a flattened FBX -- field Zidane would grow the daggers), their
    now-unreferenced materials are compacted away with indices REMAPPED (the FBX emitter writes every
    materials[] row; a dangling one shifts the engine importer's material indexing), and
    orphaned textures pruned."""
    model = {
        "geo": "GEO_MAIN_B0_000",
        "meshes": [_mesh("mesh0", 9, 0), _mesh("battle_model0", 6, 1),
                   _mesh("battle_model1", 6, 2), _mesh("mesh1", 9, 3)],
        "materials": [{"name": "m0", "texture": "98_1"}, {"name": "b0", "texture": "orich_only"},
                      {"name": "b1", "texture": "98_1"}, {"name": "m1", "texture": "98_0"}],
        "textures": {"98_0": object(), "98_1": object(), "orich_only": object()},
    }
    warned = []
    dropped = extract.strip_overlay_meshes(model, warn=warned.append)
    assert dropped == ["battle_model0", "battle_model1"]
    assert [m["name"] for m in model["meshes"]] == ["mesh0", "mesh1"]
    assert [m["name"] for m in model["materials"]] == ["m0", "m1"]          # compacted
    assert model["meshes"][0]["submeshes"][0]["material_idx"] == 0
    assert model["meshes"][1]["submeshes"][0]["material_idx"] == 1          # remapped 3 -> 1
    assert sorted(model["textures"]) == ["98_0", "98_1"]                    # orphaned stem pruned
    assert warned and "battle_model0" in warned[0] and "BOTH" in warned[0]


def test_strip_overlay_is_a_noop_without_overlays():
    model = {"geo": "GEO_MAIN_F0_ZDN",
             "meshes": [_mesh("mesh0", 9, 0)],
             "materials": [{"name": "m0", "texture": "98_0"}], "textures": {"98_0": object()}}
    assert extract.strip_overlay_meshes(model) == []
    assert [m["name"] for m in model["meshes"]] == ["mesh0"]
    assert len(model["materials"]) == 1


def test_strip_overlay_drops_field_model_too():
    """The both-subtrees split (a prefab carrying field_model*) strips symmetrically."""
    model = {"geo": "X", "meshes": [_mesh("field_model0", 6, 0), _mesh("mesh0", 9, 1)],
             "materials": [{"name": "f", "texture": "a"}, {"name": "m", "texture": "b"}],
             "textures": {"a": object(), "b": object()}}
    assert extract.strip_overlay_meshes(model) == ["field_model0"]
    assert sorted(model["textures"]) == ["b"]


# ------------------------------------------------------------------ deploy target = the PREFAB folder

def test_deploy_target_uses_the_prefab_identity():
    """SearchAssetOnDisc probes GetRenameModelPath's output (post-alias): an aliased battle form's
    override must land at the donor prefab's folder -- its own-id path is NEVER probed."""
    model = {"geo": "GEO_MAIN_B0_000", "geo_id": 5414, "type_int": 2,
             "prefab_geo": "GEO_MAIN_F0_ZDN", "prefab_id": 98, "prefab_tint": 2}
    assert export.deploy_target(model) == (2, 98)
    assert export.engine_rel_path(*export.deploy_target(model)).endswith("Models/2/98/98.fbx")


def test_deploy_target_falls_back_to_the_requested_identity():
    """Structs without prefab keys (foreign glTF re-rigs, mints, old fakes) keep the literal target."""
    assert export.deploy_target({"geo": "X", "geo_id": 10, "type_int": 4}) == (4, 10)


def test_shared_prefab_warnings_name_the_donor_and_the_alt_costume_hazard():
    model = {"geo": "GEO_MAIN_B0_000", "geo_id": 5414, "type_int": 2,
             "prefab_geo": "GEO_MAIN_F0_ZDN", "prefab_id": 98, "prefab_tint": 2}
    w = export._shared_prefab_warnings(model)
    assert len(w) == 1 and "GEO_MAIN_F0_ZDN" in w[0]
    alt = {"geo": "GEO_MAIN_F3_ZDN", "geo_id": 668, "type_int": 2,
           "prefab_geo": "GEO_MAIN_F0_ZDN", "prefab_id": 98, "prefab_tint": 2}
    w = export._shared_prefab_warnings(alt)
    assert len(w) == 2 and any("alt-costume" in x for x in w)
    assert export._shared_prefab_warnings({"geo": "GEO_MAIN_F0_ZDN"}) == []


# ------------------------------------------------------------------ surfaced notes (offline)

def test_appearance_notes_surface_the_shared_prefab():
    notes = appearance_notes("GEO_MAIN_B0_000")
    assert any("SHARED PREFAB" in n and "GEO_MAIN_F0_ZDN" in n for n in notes)
    # a minted copy notes the donor differently (name-keyed logic won't fire on a new name)
    assert any("donor prefab" in n for n in appearance_notes("GEO_MAIN_B0_000", minted=True))
    # an un-aliased model gains no such note
    assert not any("SHARED PREFAB" in n for n in appearance_notes("GEO_NPC_F1_BBA"))


# ------------------------------------------------------------------ the unshipped-id refusal

def test_unshipped_ids_have_no_alias_donor():
    """The 43 truly-absent ids (the GEO_MAIN_B2_* band etc.) resolve to THEMSELVES -- so the prefab
    lookup misses on disc and _open_prefab raises the actionable 'UNSHIPPED model' refusal instead of
    the old fake path. (Disc absence itself is install-side; the refusal text is exercised in the
    manual verification -- offline we pin that no donor exists to silently mask the absence.)"""
    for tok in ("GEO_MAIN_B2_001", "GEO_MAIN_B2_005", "GEO_MAIN_B4_003", "GEO_NPC_F6_CSM",
                "GEO_SUB_W0_007", "GEO_MON_B3_201"):
        geo, gid, tint = extract.resolve_geo(tok)
        assert extract.resolve_prefab(tok) == (geo, gid, tint), tok
