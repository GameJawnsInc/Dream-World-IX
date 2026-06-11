"""The text-block SHADOW guard (deploystack) -- catch a cross-worktree .mes collision before a playtest.

The engine reads a field's dialogue (mesID = text_block) from the FIRST folder in Memoria.ini FolderNames
that defines field/<mesID>.mes. If a HIGHER-priority folder also defines the block, a lower-priority
worktree's text is shadowed (it renders the other folder's text). These tests pin the FolderNames parse,
the shadow detection by stack order, the valid-alternative suggestions, and graceful degradation.
"""
from __future__ import annotations

from ff9mapkit.deploystack import (parse_folder_names, check_text_block_shadow, shadow_warning)


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
