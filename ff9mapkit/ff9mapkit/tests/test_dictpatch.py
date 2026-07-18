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


def test_owns_registration_id_column_match_is_directive_scoped():
    # a 3DModel/BattleScene line whose 2nd column COINCIDES with a field id (the custom-field band 4000-9899
    # overlaps the mint-id band 6000+) must NOT be claimed by the generic FieldScene/LocationName id check --
    # only model_ids/anim_keys own those directives.
    assert not DP.owns_registration("3DModel 6300 GEO_NPC_F1_M999", fid=6300, model_ids=set(), anim_keys=set())
    assert not DP.owns_registration("BattleScene 6300 SOME_BBG", fid=6300, model_ids=set(), anim_keys=set())
    # still owned when the id IS actually a minted model this deploy registers
    assert DP.owns_registration("3DModel 6300 GEO_NPC_F1_M999", fid=6300, model_ids={"6300"}, anim_keys=set())


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


def test_revert_preserves_3dmodel_line_with_coinciding_field_id():
    """A minted GEO id can coincide with a field id (both live in 4000-9899); reverting that field must not
    drop a foreign 3DModel line just because its id column happens to equal the field id."""
    fid, model_ids, anim_keys = 6300, set(), set()   # this deploy owns NO model ids of its own
    current = [
        "FieldScene 6300 11 10 TEST 1073",
        "3DModel 6300 GEO_NPC_F1_M999",   # foreign -- coincidentally shares the numeral 6300 with the field id
    ]
    backup = ["FieldScene 6300 11 10 TEST 1073"]
    kept, lost = DP.revert_dictionary_patch(current, backup, fid=fid, model_ids=model_ids, anim_keys=anim_keys)
    assert "3DModel 6300 GEO_NPC_F1_M999" in kept    # the bug: this used to silently vanish
    assert not lost


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


def test_foreign_fieldscene_drop_is_reported():
    """The 2026-07-18 gap: a FieldScene line belonging to ANOTHER session's field vanished from the shared
    DictionaryPatch and nothing warned. An unregistered field id makes the engine load a null .eb -- a black
    screen with no error -- so the loudest signal we have must cover it."""
    before = ["FieldScene 4003 11 10 TESTROOM 1073", "FieldScene 30110 11 10 TWINALTAR 1080"]
    after = ["FieldScene 4003 11 10 TESTROOM 1073"]          # a co-resident field's registration wiped
    assert DP.foreign_registrations_dropped(before, after) == ["FieldScene 30110 11 10 TWINALTAR 1080"]
    # LocationName is id-keyed the same way (cosmetic loss -- the location loses its title, no black screen)
    assert DP.foreign_registrations_dropped(["LocationName 30110 Twin Altar"], []) == ["LocationName 30110 Twin Altar"]


def test_deploys_own_fieldscene_rewrite_is_not_reported():
    """THE ANTI-NOISE TEST -- the one that keeps the guard usable. `tools/deploy_field.py` filters out its own
    FID's line and re-appends it, so blanket FieldScene reporting would fire on EVERY deploy. Two defences,
    both pinned here: (1) FieldScene is judged on (directive, id), so re-registering 4003 under a new scene
    name/text-block id is not a loss; (2) the `owned` predicate mirroring the deploy's filter excludes the id
    outright, which is what covers a deploy that legitimately STOPS emitting its own LocationName."""
    fid = 4003
    before = ["FieldScene 4003 11 10 OLDNAME 1073", "LocationName 4003 Old Title", "BattleScene 900"]
    owned = DP.owned_predicate(fid=fid, model_ids=set(), anim_keys=set())   # exactly deploy_field's `_dp_owned`
    after = ["BattleScene 900", "FieldScene 4003 11 10 NEWNAME 1099"]   # dropped-and-re-appended, edited
    # (1) id-keyed: the rewritten FieldScene is NOT a loss -- 4003 is still registered, so no warning either way
    assert "FieldScene 4003 11 10 OLDNAME 1073" not in DP.foreign_registrations_dropped(before, after)
    # (2) but this build stopped emitting `[field] location`, so the own LocationName really is gone. WITHOUT
    #     the predicate that is a false alarm on a routine deploy -- which is why the call site must pass one.
    assert DP.foreign_registrations_dropped(before, after) == ["LocationName 4003 Old Title"]
    assert DP.foreign_registrations_dropped(before, after, owned=owned) == []
    assert DP.foreign_registrations_dropped(before, ["BattleScene 900"], owned=owned) == []
    # ...but a FOREIGN id lost in the same pass still warns
    assert DP.foreign_registrations_dropped(before + ["FieldScene 30110 1 1 X 1"], after, owned=owned) \
        == ["FieldScene 30110 1 1 X 1"]


def test_mint_line_rewrite_is_still_whole_line_matched():
    """The mint directives deliberately did NOT move to key identity: a 3DModelAnimation key re-pointed at a
    different ANH name is a real loss of the old clip (the vanished key 60001), not a harmless rewrite."""
    before = ["3DModelAnimation 60001 ANH_NPC_F1_M300_IDLE"]
    after = ["3DModelAnimation 60001 ANH_NPC_F1_M300_WALK"]
    assert DP.foreign_registrations_dropped(before, after) == ["3DModelAnimation 60001 ANH_NPC_F1_M300_IDLE"]


def test_legacy_two_positional_call_still_works():
    """~30 revert scripts already on disk `sys.path.insert` into this kit and call the LIBRARY at run time
    with their OLD signature (`revert_dictionary_patch(cur, bak, fid="4003", ...)`, fid as a STRING). No new
    required parameter, no changed return shape."""
    cur = ["FieldScene 4003 11 10 TESTROOM 1073", "3DModelAnimation 60001 ANH_A", "BattleScene 900"]
    bak = ["3DModelAnimation 60001 ANH_A"]
    kept, lost = DP.revert_dictionary_patch(cur, bak, fid="4003", model_ids=set(), anim_keys=set())
    assert kept == ["3DModelAnimation 60001 ANH_A", "BattleScene 900"]   # own id gone, foreign lines intact
    assert lost == []                                                    # own FieldScene drop is not foreign
    # the 2-arg positional form legacy callers could also reach: still a plain list of verbatim lines. (It has
    # no ownership context, so it does flag the revert's own id -- exactly why revert_dictionary_patch passes
    # its `_owned` in, and why `lost` above is empty.)
    assert DP.foreign_registrations_dropped(cur, kept) == ["FieldScene 4003 11 10 TESTROOM 1073"]


def test_owned_predicate_does_not_claim_a_foreign_model_sharing_the_field_id():
    """The predicate a deploy FILTERS by is also the foreign-drop guard's ``owned=``, so its precision IS the
    guard's precision. ``tools/deploy_field.py`` hand-rolled it as "column 2 == FID", directive-agnostic --
    and mint GEO ids start at 6000 while the custom field band is 4000-9899, so they overlap. Deploying field
    6000 into a shared mod folder therefore claimed another session's ``3DModel 6000``: stripped it from the
    rewrite AND suppressed the warning about the loss. Directive scoping is what keeps both."""
    before = ["3DModel 6000 GEO_FOREIGN_NPC", "BattleScene 6000 CAMKEYS BBG_B001",
              "FieldScene 6000 11 10 OLDNAME 1073", "LocationName 6000 Old Title"]
    after = ["FieldScene 6000 11 10 NEWNAME 1073", "LocationName 6000 New Title"]
    too_broad = lambda ln: ln.split()[1:2] == ["6000"]   # noqa: E731  -- the defect this test pins
    assert DP.foreign_registrations_dropped(before, after, owned=too_broad) == []      # silent loss
    owned = DP.owned_predicate(fid=6000, model_ids=set(), anim_keys=set())
    # the deploy's own rewritten field lines stay silent; the model it never wrote is REPORTED
    assert DP.foreign_registrations_dropped(before, after, owned=owned) == ["3DModel 6000 GEO_FOREIGN_NPC"]
    # ...and the filter built from the same predicate leaves that foreign line in the file to begin with,
    # which is the real fix -- the warning is only the backstop.
    assert [ln for ln in before if not owned(ln)] == ["3DModel 6000 GEO_FOREIGN_NPC",
                                                     "BattleScene 6000 CAMKEYS BBG_B001"]


def test_owned_predicate_covers_the_playable_icon_and_name_registrations():
    """The two ``[[playable]]`` registrations a redeploy re-sets live in the predicate too (they used to be
    separate closures in the deploy script). A stale icon/name for a key THIS deploy re-emits is owned; one
    for any other status id or language is foreign and must survive."""
    owned = DP.owned_predicate(fid=4003, model_ids=set(), anim_keys=set(),
                               status_icon_ids={"200"}, charname_keys={("12", "US")})
    assert owned("BuffIcon 200 icon_a") and owned("DebuffIcon 200 icon_b")
    assert owned("CharacterDefaultName 12 US Tantalus")
    assert not owned("BuffIcon 201 icon_c")                     # another custom status
    assert not owned("CharacterDefaultName 12 JP Tantalus")     # another language row
    assert not owned("CharacterDefaultName 13 US Other")        # another character
