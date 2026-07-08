"""DictionaryPatch revert/re-apply bookkeeping (``ff9mapkit.dictpatch``).

Regression cover for the 2026-07-08 deploy footgun: re-deploying a field slot wiped a foreign
``3DModelAnimation`` line (key 60001, ANH_NPC_F1_M300_IDLE) that ``model-anim-new`` had written straight
into DictionaryPatch between deploys, because the old revert dropped anim lines by SHARED GEO middle-block.
The fix matches by EXACT id/key the deploy owns; these tests pin that a foreign key survives.
"""
from ff9mapkit import dictpatch as DP


def test_mint_parsers():
    lines = ["3DModel 6300 GEO_NPC_F1_M300", "3DModel 6500 GEO_WEP_B1_M500",
             "3DModelAnimation 1000000 ANH_NPC_F1_M300_IDLE", "FieldScene 30057 11 10 TEST 1073",
             "BattleScene 900"]
    assert DP.mint_model_ids(lines) == {"6300", "6500"}
    assert DP.mint_anim_keys(lines) == {"1000000"}


def test_owns_registration_exact_id_and_key():
    # this field's own FieldScene / LocationName (id in column 2)
    assert DP.owns_registration("FieldScene 30057 11 10 TEST 1073", fid=30057, model_ids=set(), anim_keys=set())
    assert DP.owns_registration("LocationName 30057 A Place", fid=30057, model_ids=set(), anim_keys=set())
    assert not DP.owns_registration("FieldScene 30058 11 10 X 1073", fid=30057, model_ids=set(), anim_keys=set())
    # 3DModel drops by EXACT id
    assert DP.owns_registration("3DModel 6300 GEO_NPC_F1_M300", fid=30057, model_ids={"6300"}, anim_keys=set())
    assert not DP.owns_registration("3DModel 6301 GEO_NPC_F1_M301", fid=30057, model_ids={"6300"}, anim_keys=set())
    # 3DModelAnimation drops by EXACT key -- NOT by shared GEO block
    assert DP.owns_registration("3DModelAnimation 60000 ANH_NPC_F1_M300_IDLE", fid=30057, model_ids=set(),
                                anim_keys={"60000"})
    # THE BUG: a foreign anim sharing the NPC_F1_M300 block but a key this deploy doesn't own is NOT owned
    assert not DP.owns_registration("3DModelAnimation 60001 ANH_NPC_F1_M300_IDLE", fid=30057,
                                    model_ids={"6300"}, anim_keys=set())
    # blanks are never owned
    assert not DP.owns_registration("", fid=30057, model_ids=set(), anim_keys=set())
    assert not DP.owns_registration("   ", fid=30057, model_ids=set(), anim_keys=set())


def test_revert_preserves_foreign_anim_key_60001():
    """The exact reported scenario: deploy of field 30057 minted GEO 6300 (block NPC_F1_M300) but registered
    NO anim itself. `model-anim-new` later added key 60001 (same block). Re-deploy's revert must keep it."""
    fid, model_ids, anim_keys = 30057, {"6300"}, set()   # deploy owns model 6300; owns NO anim keys
    current = [
        "FieldScene 30057 11 10 TEST30057 1073",
        "3DModel 6300 GEO_NPC_F1_M300",
        "3DModelAnimation 60000 ANH_NPC_F1_M300_IDLE",   # predates the snapshot -> in backup
        "3DModelAnimation 60001 ANH_NPC_F1_M300_IDLE",   # added by model-anim-new AFTER the snapshot -> foreign, NOT in backup
        "BattleScene 900",                               # a co-deployed tool's line
    ]
    backup = [
        "FieldScene 30057 11 10 TEST30057 1073",
        "3DModelAnimation 60000 ANH_NPC_F1_M300_IDLE",
    ]
    kept, lost = DP.revert_dictionary_patch(current, backup, fid=fid, model_ids=model_ids, anim_keys=anim_keys)
    assert "3DModelAnimation 60001 ANH_NPC_F1_M300_IDLE" in kept    # the bug: this used to vanish
    assert "3DModelAnimation 60000 ANH_NPC_F1_M300_IDLE" in kept    # foreign-to-anim-keys, also survives
    assert "BattleScene 900" in kept                               # co-deployed line survives
    assert "3DModel 6300 GEO_NPC_F1_M300" not in kept              # this deploy's own mint id is dropped
    assert not lost                                                # nothing foreign was dropped


def test_revert_drops_own_fresh_lines_but_restores_prior_shared():
    """A deploy's OWN fresh mint (not in backup) is dropped on revert; a mint that PRE-EXISTED (in backup,
    e.g. a shared character another field also registered) is restored."""
    fid, model_ids, anim_keys = 5000, {"6300", "6301"}, {"1000000"}
    current = [
        "FieldScene 5000 11 10 X 1073",
        "3DModel 6300 GEO_NPC_F1_M300",                  # pre-existed (shared) -> in backup
        "3DModel 6301 GEO_NPC_F1_M301",                  # added fresh this deploy -> NOT in backup
        "3DModelAnimation 1000000 ANH_NPC_F1_M300_ATK",  # this deploy's own custom_battle_anims key
    ]
    backup = ["FieldScene 5000 11 10 X 1073", "3DModel 6300 GEO_NPC_F1_M300"]
    kept, lost = DP.revert_dictionary_patch(current, backup, fid=fid, model_ids=model_ids, anim_keys=anim_keys)
    assert "3DModel 6300 GEO_NPC_F1_M300" in kept        # shared -> restored from backup
    assert "3DModel 6301 GEO_NPC_F1_M301" not in kept    # fresh this deploy -> stays gone
    assert "3DModelAnimation 1000000 ANH_NPC_F1_M300_ATK" not in kept   # own anim key -> dropped, not in backup
    assert not lost


def test_foreign_registrations_dropped_reports_only_genuine_losses():
    before = ["3DModel 6300 GEO_A", "3DModelAnimation 60001 ANH_A", "FieldScene 5000 1 1 X 1"]
    # a wholesale replace that keeps neither model/anim line
    after = ["FieldScene 5000 1 1 X 1"]
    dropped = DP.foreign_registrations_dropped(before, after)
    assert dropped == ["3DModel 6300 GEO_A", "3DModelAnimation 60001 ANH_A"]   # de-duped, first-seen order
    # with an ownership predicate, an owned drop (the 3DModel) is excluded -> only the foreign anim warns
    owned = lambda ln: ln.startswith("3DModel ")   # noqa: E731
    assert DP.foreign_registrations_dropped(before, after, owned=owned) == ["3DModelAnimation 60001 ANH_A"]
    # nothing dropped -> empty
    assert DP.foreign_registrations_dropped(before, before) == []


def test_foreign_registrations_dropped_ignores_reordering_and_dupes():
    before = ["3DModelAnimation 60001 ANH_A", "3DModelAnimation 60001 ANH_A", "3DModel 6300 GEO_A"]
    after = ["3DModel 6300 GEO_A", "3DModelAnimation 60001 ANH_A"]   # same regs, reordered
    assert DP.foreign_registrations_dropped(before, after) == []
