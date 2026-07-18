"""The text-block guard (deploystack) -- catch a .mes collision before a playtest, on BOTH axes.

The engine merges a field's dialogue (mesID = text_block) CUMULATIVELY per txid: every FolderNames folder
that defines field/<mesID>.mes plus the BASE GAME, applied low-priority-first. So a block collides two ways:
(1) CROSS-FOLDER -- a higher-priority folder's lines win over a lower worktree's; (2) VANILLA -- because the
base game is always in the merge, a custom field on a REAL block overwrites that location's shipping
dialogue, with no stacking required. Guarding (1) by "pick another real block" is what CAUSES (2).

These tests pin the FolderNames parse, both detections, the verbatim-fork exemption, the requirement that
suggestions be FREE CUSTOM ids (never a real block -- the pre-fix guard suggested Ice Cavern and Lindblum
Castle), the per-language sweep, and graceful degradation.
"""
from __future__ import annotations

from ff9mapkit.deploystack import (parse_folder_names, check_text_block_shadow, shadow_warning,
                                   check_text_block_shadows, text_shadow_warning, blocks_at,
                                   check_csv_shadow, HIGHEST_WINS_CSVS, vanilla_fields_on,
                                   describe_vanilla, suggest_text_blocks, fork_donor_blocks_at, donor_block_for,
                                   SCRATCH_TEXT_BLOCK_BASE)

# Real shipping blocks (from the engine's own eventIDToMESID): 1073 = Black Mage Village (fields 3050-3059),
# 187 = a real Cleyra block, 8 = Ice Cavern, 22 = Lindblum Castle. 200/201 are NOT real blocks -- they stand
# in for a registered custom id in tests that want to isolate the cross-folder axis.
VANILLA_BLOCK, OTHER_VANILLA, FREE_BLOCK = 1073, 187, 200


INI = '''[Mod]
; The "Priorities" field is only a hint for the Launcher's Mod Manager; FolderNames defines order.
FolderNames = "A", "B", "C"
Enabled = 1
'''


def _mk(game, folder, lang, blocks):
    d = game / folder / "FF9_Data" / "embeddedasset" / "text" / lang / "field"
    d.mkdir(parents=True, exist_ok=True)
    for b in blocks:
        (d / f"{b}.mes").write_text(f"_[TXID=500]block {b}[ENDN]\n", encoding="utf-8")


def _stack(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk(g, "A", "us", [1073])            # priority #1
    _mk(g, "B", "us", [1073, 200])       # priority #2
    _mk(g, "C", "us", [1073, 187])       # priority #3 (lowest)
    return g


def test_parse_folder_names_order_and_skips_comment():
    assert parse_folder_names(INI) == ["A", "B", "C"]
    assert parse_folder_names("[Mod]\nEnabled = 1\n") == []                 # no FolderNames key
    assert parse_folder_names("; FolderNames = \"X\"\nFolderNames = \"Y\"\n") == ["Y"]   # comment skipped


def test_shadow_detected_for_lowest_priority_default_block(tmp_path):
    g = _stack(tmp_path)
    r = check_text_block_shadow(g, "C", VANILLA_BLOCK)
    assert not r.ok and r.shadowed_by == "A"               # the FIRST higher-priority definer


def test_suggestions_are_free_custom_ids_never_a_real_block(tmp_path):
    """THE poisoned-pool regression. The pre-fix guard suggested "a real block no higher folder defines",
    which on the live stack returned [8, 22, 68, 945, ...] -- Ice Cavern, Lindblum Castle, the overworld
    dispatchers. Following it MOVED the corruption instead of removing it."""
    g = _stack(tmp_path)
    r = check_text_block_shadow(g, "C", VANILLA_BLOCK)
    assert r.suggestions, "a colliding block must come with a concrete alternative"
    assert all(not vanilla_fields_on(s) for s in r.suggestions)      # never a REAL location's block
    assert OTHER_VANILLA not in r.suggestions                        # specifically: not the old advice
    assert all(s >= SCRATCH_TEXT_BLOCK_BASE for s in r.suggestions)  # from the custom band
    assert VANILLA_BLOCK not in r.suggestions                        # never the colliding block itself
    # and never a block ANY stacked folder already ships (it would just re-collide)
    taken = blocks_at(g / "A", "us") | blocks_at(g / "B", "us") | blocks_at(g / "C", "us")
    assert not (set(r.suggestions) & taken)


def test_highest_priority_folder_still_flagged_for_vanilla_overwrite(tmp_path):
    """The headline gap: the pre-fix guard called this CLEAR while it silently overwrote Black Mage Village.
    Nothing is higher than 'A', so the cross-folder axis is genuinely clear -- but the base game is always in
    the cumulative merge, so the vanilla axis is not."""
    g = _stack(tmp_path)
    r = check_text_block_shadow(g, "A", VANILLA_BLOCK)
    assert r.shadowed_by is None                            # nothing is higher than A
    assert r.squats_vanilla and not r.ok                    # ...but it overwrites fields 3050-3059
    assert r.vanilla_fields[0] == 3050


def test_non_vanilla_block_is_clear_when_unshadowed(tmp_path):
    g = _stack(tmp_path)
    assert check_text_block_shadow(g, "B", FREE_BLOCK).ok    # 200: not real, not defined by higher 'A'


def test_fork_is_exempt_only_on_its_OWN_donor_block(tmp_path):
    """A fork re-ships its DONOR's own text on the DONOR's own block -- that overwrite is a no-op, so the
    vanilla axis must not fire. But the exemption is scoped to THAT block: an earlier version took a bare
    `verbatim=True` boolean, which waved through a fork sitting on any block at all -- including a fork left
    on the kit default 1073, which really does overwrite Black Mage Village."""
    g = _stack(tmp_path)
    # exempt on its own donor block...
    assert check_text_block_shadow(g, "C", OTHER_VANILLA, verbatim_blocks={OTHER_VANILLA}).ok
    # ...NOT exempt on a different real block it merely happens to carry (THE regression)
    off = check_text_block_shadow(g, "A", VANILLA_BLOCK, verbatim_blocks={OTHER_VANILLA})
    assert off.squats_vanilla and not off.ok
    # and the CROSS-FOLDER axis survives the exemption entirely
    r = check_text_block_shadow(g, "C", VANILLA_BLOCK, verbatim_blocks={VANILLA_BLOCK})
    assert not r.ok and r.shadowed_by == "A" and not r.squats_vanilla


def test_donor_block_for_covers_all_three_fork_forms():
    """The predicate must see native/BG-borrow forks too, not just verbatim ones -- donor 302 (Ice Cavern)
    lives on block 8, donor 600 (Lindblum) on block 22. An earlier version tested `"verbatim_eb" in raw`,
    which false-positived every --native fork on its own legitimate donor block."""
    assert donor_block_for({"verbatim_eb": {"donor": 302}}) == 8          # verbatim
    assert donor_block_for({"field": {"source_field": 600}}) == 22        # --native / --editable
    assert donor_block_for({"field": {"borrow_field": 600}}) == 22        # BG-borrow
    assert donor_block_for({"field": {"source_field": "600"}}) == 22      # string form
    assert donor_block_for({"field": {"id": 4003}}) is None              # not a fork
    assert donor_block_for({}) is None
    assert donor_block_for({"field": {"source_field": True}}) is None    # bool is not a donor id
    assert donor_block_for({"field": {"source_field": 99999}}) is None   # unknown donor -> no exemption


def test_simultaneous_findings_get_distinct_suggestions(tmp_path):
    """Two colliding blocks in ONE deploy must not both be told to move to the same id -- that would be a
    fresh collision caused by this tool's own advice."""
    g = _stack(tmp_path)
    reports = check_text_block_shadows(g, "C", {VANILLA_BLOCK, OTHER_VANILLA, 8})
    firsts = [r.suggestions[0] for r in reports if r.suggestions]
    assert len(firsts) == len(set(firsts)) and len(firsts) >= 3
    w = text_shadow_warning(reports, "C")
    for f in firsts:                                        # every row names its own id in the message
        assert f"use {f}" in w


def test_explicit_folder_names_override(tmp_path):
    g = _stack(tmp_path)
    # pass the order directly (no Memoria.ini read): C first => nothing shadows it
    assert check_text_block_shadow(g, "C", VANILLA_BLOCK, folder_names=["C", "A", "B"]).shadowed_by is None


def test_graceful_without_memoria_ini(tmp_path):
    g = tmp_path / "bare"
    g.mkdir()
    r = check_text_block_shadow(g, "C", FREE_BLOCK)         # no Memoria.ini -> empty stack
    assert r.ok and r.order == []


def test_vanilla_axis_needs_no_stack_at_all(tmp_path):
    """Unlike the shadow axis, this one does not degrade to silence when Memoria.ini is unreadable -- the base
    game is in the merge regardless of what any mod folder does."""
    g = tmp_path / "bare"
    g.mkdir()
    r = check_text_block_shadow(g, "C", VANILLA_BLOCK)
    assert r.order == [] and r.shadowed_by is None and r.squats_vanilla and not r.ok


def test_target_not_in_stack_no_false_alarm(tmp_path):
    g = _stack(tmp_path)
    # unlisted target -> nothing is "higher" (the shadow axis stays quiet)
    assert check_text_block_shadow(g, "FF9CustomMap-zz", FREE_BLOCK).ok


def test_shadow_warning_text(tmp_path):
    g = _stack(tmp_path)
    w = shadow_warning(check_text_block_shadow(g, "C", VANILLA_BLOCK))
    assert w and "TEXT SHADOWED" in w and "'A'" in w
    assert "register_text_block = true" in w                # the fix hint names the registration
    assert str(OTHER_VANILLA) not in w                      # and never steers at a real block
    assert shadow_warning(check_text_block_shadow(g, "B", FREE_BLOCK)) is None   # clear -> no warning


def test_vanilla_warning_names_the_real_fields(tmp_path):
    g = _stack(tmp_path)
    w = shadow_warning(check_text_block_shadow(g, "A", VANILLA_BLOCK))
    assert w and "OVERWRITES VANILLA" in w and "3050-3059" in w


# ---- the vanilla index + custom-block allocator ------------------------------------------------
def test_vanilla_fields_on_and_describe():
    assert vanilla_fields_on(VANILLA_BLOCK)[0] == 3050      # 1073 = MES_MAGE2, Black Mage Village
    assert len(vanilla_fields_on(8)) == 13                  # block 8 = Ice Cavern, fields 300-312
    assert vanilla_fields_on(FREE_BLOCK) == ()              # 200 is nobody's
    assert describe_vanilla(8) == "13 real fields 300-312"
    assert describe_vanilla(FREE_BLOCK) == ""
    # the real overworld dispatchers live on block 68 -- a `field_id < 4000` filter would wrongly drop them
    assert 9000 in vanilla_fields_on(68)


def test_suggest_text_blocks_skips_real_and_taken():
    s = suggest_text_blocks(taken={SCRATCH_TEXT_BLOCK_BASE, SCRATCH_TEXT_BLOCK_BASE + 1}, n=3)
    assert s == [SCRATCH_TEXT_BLOCK_BASE + 2, SCRATCH_TEXT_BLOCK_BASE + 3, SCRATCH_TEXT_BLOCK_BASE + 4]
    assert all(not vanilla_fields_on(b) for b in suggest_text_blocks(n=5))
    assert suggest_text_blocks(n=0) == []


def test_fork_donor_blocks_maps_donors_to_their_blocks(tmp_path):
    d = tmp_path / "dist"
    d.mkdir()
    assert fork_donor_blocks_at(d) == set()                 # no ForkDonorPatch -> claim no exemption
    (d / "ForkDonorPatch.txt").write_text(
        "# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n8641 600\n9002 3050\n", encoding="utf-8")
    # donor 600 lives on block 22 (Lindblum), donor 3050 on 1073 (Mage Village)
    assert fork_donor_blocks_at(d) == {22, VANILLA_BLOCK}


# ---- batch text-block shadow (the campaign/journey deploy guard) ------------------------------
def test_blocks_at_reads_a_root_mes_stems(tmp_path):
    g = _stack(tmp_path)
    assert blocks_at(g / "B", "us") == {1073, 200}
    assert blocks_at(g / "C", "us") == {1073, 187}
    assert blocks_at(g / "nope", "us") == set()             # missing root -> empty, no error


def test_check_text_block_shadows_flags_both_axes(tmp_path):
    """One row PER AXIS: a block that is both shadowed and real reports twice, so the warning can group them.
    (201 is defined by nobody and is not a real block -> clear on both axes, no row at all.)"""
    g = _stack(tmp_path)
    reports = check_text_block_shadows(g, "C", {VANILLA_BLOCK, 201})
    assert {r.text_block for r in reports} == {VANILLA_BLOCK}          # 201 never appears
    assert [(r.shadowed_by, r.squats_vanilla) for r in reports] == [("A", False), (None, True)]
    # 187 is NOT shadowed (only C defines it) but IS a real block -> reported on the vanilla axis alone
    r2 = check_text_block_shadows(g, "C", {OTHER_VANILLA})
    assert [(r.text_block, r.shadowed_by, r.squats_vanilla) for r in r2] == [(OTHER_VANILLA, None, True)]
    # 200 IS defined by higher-priority 'B' -> shadow axis only (it is not a real block)
    r3 = check_text_block_shadows(g, "C", {FREE_BLOCK})
    assert [(r.text_block, r.shadowed_by, r.squats_vanilla) for r in r3] == [(FREE_BLOCK, "B", False)]


def test_check_text_block_shadows_verbatim_blocks_exempt(tmp_path):
    g = _stack(tmp_path)
    # a campaign of verbatim forks carrying donor blocks 187 + 1073: 187 is fully clear, 1073 still shadowed
    reports = check_text_block_shadows(g, "C", {VANILLA_BLOCK, OTHER_VANILLA},
                                       verbatim_blocks={VANILLA_BLOCK, OTHER_VANILLA})
    assert [(r.text_block, r.shadowed_by, r.squats_vanilla) for r in reports] == [(VANILLA_BLOCK, "A", False)]


def test_check_text_block_shadows_clear_when_highest_or_unlisted(tmp_path):
    g = _stack(tmp_path)
    # highest / unlisted -> the SHADOW axis is quiet; use a block nobody ships so the vanilla axis is too
    assert check_text_block_shadows(g, "A", {201}) == []
    assert check_text_block_shadows(g, "FF9CustomMap-zz", {201}) == []
    # ...but 'A' on a REAL block is still reported (nothing higher, yet vanilla is overwritten)
    assert [r.text_block for r in check_text_block_shadows(g, "A", {VANILLA_BLOCK})] == [VANILLA_BLOCK]


def test_check_text_block_shadows_per_language(tmp_path):
    """lang=None sweeps every language. A novel field's text is identical across langs so the finding is
    symmetric and must dedup to ONE row; a lang-ASYMMETRIC collision must survive as its own row."""
    g = _stack(tmp_path)
    _mk(g, "A", "fr", [FREE_BLOCK])                      # 'A' shadows 200 in FRENCH only
    # 1073 is shadowed by 'A' in every language it exists in -> ONE shadow row, not seven
    shadow = [r for r in check_text_block_shadows(g, "C", {VANILLA_BLOCK}, lang=None)
              if r.shadowed_by is not None]
    assert [(r.lang, r.shadowed_by) for r in shadow] == [("us", "A")]
    # the language-independent vanilla row is emitted exactly once alongside it
    assert len([r for r in check_text_block_shadows(g, "C", {VANILLA_BLOCK}, lang=None)
                if r.squats_vanilla]) == 1
    # 200 is shadowed by a DIFFERENT folder per language ('B' ships it in us, 'A' only in fr) -- both
    # survive, because collapsing them would hide a real finding the us-only check could never see.
    fr = check_text_block_shadows(g, "C", {FREE_BLOCK}, lang=None)
    assert [(r.lang, r.shadowed_by) for r in fr] == [("us", "B"), ("fr", "A")]
    # the pre-fix single-language check sees only the 'us' half
    assert [(r.lang, r.shadowed_by) for r in
            check_text_block_shadows(g, "C", {FREE_BLOCK}, lang="us")] == [("us", "B")]


def test_text_shadow_warning_text(tmp_path):
    g = _stack(tmp_path)
    w = text_shadow_warning(check_text_block_shadows(g, "C", {VANILLA_BLOCK}), "C")
    assert w and "block 1073" in w and "'A'" in w
    assert "SHADOWED" in w and "OVERWRITES VANILLA" in w and "3050-3059" in w
    assert "register_text_block = true" in w
    assert text_shadow_warning([], "C") is None                         # clear -> no warning


# ---- the highest-wins CSV (InitialItems.csv) shadow guard -------------------------------------
INITIAL_ITEMS = HIGHEST_WINS_CSVS[0]   # "StreamingAssets/Data/Items/InitialItems.csv"


def _mk_csv(game, folder, relpath):
    # relpath is forward-slash-separated (matches check_csv_shadow's own normalization); pathlib
    # nests it correctly on every platform. A literal "\\" only nests on Windows -- on POSIX it's
    # just a character, so it wrote a single flat file instead of the expected nested path.
    p = game / folder / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("236;5;# Potion\n", encoding="utf-8")


def _csv_stack(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")   # FolderNames = A, B, C
    return g


def test_initial_items_shadowed_by_higher_folder(tmp_path):
    g = _csv_stack(tmp_path)
    _mk_csv(g, "A", INITIAL_ITEMS)                          # higher-priority folder also ships the bag
    _mk_csv(g, "C", INITIAL_ITEMS)
    w = check_csv_shadow(g, "C", INITIAL_ITEMS)
    assert w and "SHADOWED" in w and "'A'" in w and "InitialItems.csv" in w


def test_initial_items_not_shadowed_when_highest(tmp_path):
    g = _csv_stack(tmp_path)
    _mk_csv(g, "A", INITIAL_ITEMS)
    assert check_csv_shadow(g, "A", INITIAL_ITEMS) is None  # nothing higher than A


def test_initial_items_no_shadow_when_higher_lacks_it(tmp_path):
    g = _csv_stack(tmp_path)
    _mk_csv(g, "C", INITIAL_ITEMS)                          # only C ships it -> no higher copy
    assert check_csv_shadow(g, "C", INITIAL_ITEMS) is None


def test_csv_shadow_graceful_without_ini(tmp_path):
    g = tmp_path / "bare"
    g.mkdir()
    assert check_csv_shadow(g, "C", INITIAL_ITEMS) is None  # no Memoria.ini -> empty stack, no false alarm


def test_csv_shadow_target_not_in_stack(tmp_path):
    g = _csv_stack(tmp_path)
    _mk_csv(g, "A", INITIAL_ITEMS)
    assert check_csv_shadow(g, "FF9CustomMap-zz", INITIAL_ITEMS) is None   # unlisted target -> nothing higher


# ---- the cross-folder NAME-collision guard (EVT_/FBG_ shadow) ----------------------------------
from ff9mapkit.deploystack import (check_name_collisions, name_collision_warning,  # noqa: E402
                                   eb_names_at, scene_names_at)


def _mk_eb(game, folder, lang, names):
    d = (game / folder / "StreamingAssets" / "assets" / "resources" / "commonasset"
         / "eventengine" / "eventbinary" / "field" / lang)
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / f"{n}.eb.bytes").write_bytes(b"\x00")


def _mk_scene(game, folder, names):
    base = game / folder / "StreamingAssets" / "assets" / "resources" / "FieldMaps"
    for n in names:
        (base / n).mkdir(parents=True, exist_ok=True)


def test_eb_and_scene_names_at(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    _mk_eb(g, "A", "us", ["EVT_FOO", "EVT_BAR"])
    _mk_eb(g, "A", "uk", ["EVT_FOO", "EVT_BAR"])           # other langs hold the same names
    _mk_scene(g, "A", ["FBG_N11_FOO"])
    assert eb_names_at(g / "A") == {"EVT_FOO", "EVT_BAR"}   # extension stripped, deduped across langs
    assert scene_names_at(g / "A") == {"FBG_N11_FOO"}
    assert eb_names_at(g / "missing") == set() and scene_names_at(g / "missing") == set()


def test_name_collision_shadows_us_when_higher_has_it(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")   # FolderNames = A, B, C
    _mk_eb(g, "A", "us", ["EVT_DL_ENT"])                    # higher-priority A already ships the name
    cs = check_name_collisions(g, "C", {"EVT_DL_ENT", "EVT_UNIQUE"}, set())
    assert len(cs) == 1
    c = cs[0]
    assert c.name == "EVT_DL_ENT" and c.other_folder == "A" and c.kind == "eb" and c.relation == "shadows_us"


def test_name_collision_we_shadow_lower_folder(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_scene(g, "C", ["FBG_N11_DL_ENT"])                  # lower-priority C ships the scene; we (A) are higher
    cs = check_name_collisions(g, "A", set(), {"FBG_N11_DL_ENT"})
    assert len(cs) == 1 and cs[0].relation == "we_shadow" and cs[0].kind == "scene"


def test_name_collision_excludes_target_folder(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_eb(g, "B", "us", ["EVT_X"])
    assert check_name_collisions(g, "B", {"EVT_X"}, set()) == []   # our own folder is replaced in place


def test_name_collision_ambiguous_when_target_unlisted(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")   # A, B, C (target not among them)
    _mk_eb(g, "A", "us", ["EVT_X"])
    cs = check_name_collisions(g, "FF9CustomMap-zz", {"EVT_X"}, set())
    assert len(cs) == 1 and cs[0].relation == "ambiguous"


def test_name_collision_graceful_without_ini(tmp_path):
    g = tmp_path / "bare"
    g.mkdir()
    assert check_name_collisions(g, "C", {"EVT_X"}, {"FBG_N11_X"}) == []   # empty stack -> no false alarm


def test_name_collision_explicit_order_override(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    _mk_eb(g, "A", "us", ["EVT_X"])
    # pass the order directly (no Memoria.ini read): C first, A lower -> A shadows nothing of C's
    cs = check_name_collisions(g, "C", {"EVT_X"}, set(), folder_names=["C", "A", "B"])
    assert len(cs) == 1 and cs[0].relation == "we_shadow"   # C is highest -> C shadows A's copy


def test_name_collision_warning_text_and_none(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_eb(g, "A", "us", ["EVT_DL_ENT"])
    cs = check_name_collisions(g, "C", {"EVT_DL_ENT"}, set())
    w = name_collision_warning(cs, "C")
    assert w and "NAME COLLISION" in w and "--name-prefix" in w and "EVT_DL_ENT" in w and "'A'" in w
    assert name_collision_warning([], "C") is None         # clear -> no warning


# ---- the cross-folder ID-collision guard (global EventDB; the name guard MISSES it) -------------
from ff9mapkit.deploystack import (check_id_collisions, id_collision_warning,  # noqa: E402
                                   dictionary_ids_at)


def _mk_dict(game, folder, lines):
    p = game / folder / "DictionaryPatch.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_dictionary_ids_at_parses_field_and_battle(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    _mk_dict(g, "A", ["FieldScene 30007 11 TEST30007 TEST30007 741",
                      "BattleScene 30011 CAMKEYS BBG_B209", "# comment", "garbage", "FieldScene xx bad"])
    ids = dictionary_ids_at(g / "A")
    assert ids[30007] == ("FieldScene", "TEST30007")        # kind + MAPID
    assert ids[30011] == ("BattleScene", "CAMKEYS")         # kind + scene name; non-int / junk lines skipped
    assert dictionary_ids_at(g / "missing") == {}


def test_id_collision_field_vs_battle_the_30011_bug(tmp_path):
    # the real multi-hour bug: -ate FieldScene 30011 vs -bb BattleScene 30011 -- names DIFFER, so the NAME
    # guard returns clear; this id guard must catch it.
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")    # FolderNames = A, B, C
    _mk_dict(g, "B", ["BattleScene 30011 CAMKEYS BBG_B209"])
    cs = check_id_collisions(g, "A", {30011})
    assert len(cs) == 1
    c = cs[0]
    assert (c.field_id, c.other_folder, c.other_kind, c.other_name) == (30011, "B", "BattleScene", "CAMKEYS")
    # the NAME guard does NOT see it (TEST30011 != CAMKEYS) -- proves the two guards are complementary
    assert check_name_collisions(g, "A", {"EVT_TEST30011"}, {"FBG_N11_TEST30011"}) == []


def test_id_collision_field_vs_field_and_free_id(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_dict(g, "C", ["FieldScene 4100 30 DC_DL_ENT DC_DL_ENT 50"])
    cs = check_id_collisions(g, "A", {4100, 4101})           # 4100 collides, 4101 free
    assert len(cs) == 1 and cs[0].field_id == 4100 and cs[0].other_kind == "FieldScene"
    assert check_id_collisions(g, "A", {30600}) == []        # an id nobody else uses -> clear


def test_id_collision_excludes_target_folder(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_dict(g, "B", ["FieldScene 30011 11 TEST30011 TEST30011 738"])
    assert check_id_collisions(g, "B", {30011}) == []        # our own folder's id is replaced in place


def test_id_collision_graceful_without_ini_and_order_override(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    _mk_dict(g, "B", ["BattleScene 30011 CAMKEYS BBG_B209"])
    assert check_id_collisions(g, "A", {30011}) == []        # no Memoria.ini -> empty stack, no false alarm
    cs = check_id_collisions(g, "A", {30011}, folder_names=["A", "B", "C"])   # explicit order
    assert len(cs) == 1 and cs[0].other_folder == "B"


def test_id_collision_warning_text_and_none(tmp_path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "Memoria.ini").write_text(INI, encoding="utf-8")
    _mk_dict(g, "B", ["BattleScene 30011 CAMKEYS BBG_B209"])
    w = id_collision_warning(check_id_collisions(g, "A", {30011}), "A")
    assert w and "ID COLLISION" in w and "30011" in w and "'B'" in w and "CAMKEYS" in w and "EventDB" in w
    assert id_collision_warning([], "A") is None             # clear -> no warning
