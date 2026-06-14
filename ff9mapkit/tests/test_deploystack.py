"""The text-block SHADOW guard (deploystack) -- catch a cross-worktree .mes collision before a playtest.

The engine reads a field's dialogue (mesID = text_block) from the FIRST folder in Memoria.ini FolderNames
that defines field/<mesID>.mes. If a HIGHER-priority folder also defines the block, a lower-priority
worktree's text is shadowed (it renders the other folder's text). These tests pin the FolderNames parse,
the shadow detection by stack order, the valid-alternative suggestions, and graceful degradation.
"""
from __future__ import annotations

from ff9mapkit.deploystack import (parse_folder_names, check_text_block_shadow, shadow_warning,
                                   check_csv_shadow, HIGHEST_WINS_CSVS)


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
    r = check_text_block_shadow(g, "C", 1073)
    assert not r.ok and r.shadowed_by == "A"               # the FIRST higher-priority definer
    assert 187 in r.suggestions and 200 not in r.suggestions   # 187 free; 200 is defined by higher 'B'
    assert 1073 not in r.suggestions                       # never suggest the colliding block itself


def test_highest_priority_folder_is_never_shadowed(tmp_path):
    g = _stack(tmp_path)
    assert check_text_block_shadow(g, "A", 1073).ok         # nothing is higher than A


def test_unique_block_is_not_shadowed(tmp_path):
    g = _stack(tmp_path)
    assert check_text_block_shadow(g, "C", 187).ok          # 187 only defined by C itself (+ no higher)
    assert check_text_block_shadow(g, "B", 200).ok          # 200 not defined by higher 'A'


def test_explicit_folder_names_override(tmp_path):
    g = _stack(tmp_path)
    # pass the order directly (no Memoria.ini read): C first => nothing shadows it
    assert check_text_block_shadow(g, "C", 1073, folder_names=["C", "A", "B"]).ok


def test_graceful_without_memoria_ini(tmp_path):
    g = tmp_path / "bare"
    g.mkdir()
    r = check_text_block_shadow(g, "C", 1073)               # no Memoria.ini -> empty stack
    assert r.ok and r.suggestions == [] and r.order == []


def test_target_not_in_stack_no_false_alarm(tmp_path):
    g = _stack(tmp_path)
    assert check_text_block_shadow(g, "FF9CustomMap-zz", 1073).ok   # unlisted target -> nothing is "higher"


def test_shadow_warning_text(tmp_path):
    g = _stack(tmp_path)
    r = check_text_block_shadow(g, "C", 1073)
    w = shadow_warning(r)
    assert w and "TEXT SHADOWED" in w and "'A'" in w and "187" in w
    assert shadow_warning(check_text_block_shadow(g, "A", 1073)) is None   # clear -> no warning


# ---- the highest-wins CSV (InitialItems.csv) shadow guard -------------------------------------
INITIAL_ITEMS = HIGHEST_WINS_CSVS[0]   # "StreamingAssets/Data/Items/InitialItems.csv"


def _mk_csv(game, folder, relpath):
    p = game / folder / relpath.replace("/", "\\")
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
