r"""[[item_text]] -- author an item's menu NAME + help/battle DESCRIPTION via a TextPatch.txt >DATABASE
find/replace patch (Memoria.TextPatcher). The channel is a per-mod-folder drop-in like DictionaryPatch/
BattlePatch, read once at DataPatchers.Initialize. These tests pin the emitter (condition format, full-replace,
$/newline escaping), the non-clobbering merge, validation, and the build aggregation -- all install-free
(the kit writes only the author's strings + the resolved item id; it reads nothing from the bundles).
"""
from __future__ import annotations

from ff9mapkit import items as _items
from ff9mapkit.content import itemtext as IT
from ff9mapkit.build import FieldProject, validate, _emit_item_text

POTION = _items.resolve("Potion")        # 236
HIPOT = _items.resolve("Hi-Potion")      # 237


# ---- render_block_lines (the >DATABASE patch text) --------------------------------------------
def test_render_name_only():
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "Mega Potion"}])
    assert lines == [
        ">DATABASE",
        f"[code=Condition] Database == 'RegularItem' && EntryId == {POTION} && IsNameEntry == true [/code]",
        "FindAndReplace",
        r"Find: \A[\s\S]*\z",
        "Replace: Mega Potion",
    ]


def test_render_desc_only_uses_help_flag():
    lines = IT.render_block_lines([{"name": "Potion", "description": "Restores 15 HP."}])
    # the description targets IsHelpEntry -- which the engine applies to BOTH menu-help AND battle desc
    assert f"IsHelpEntry == true" in lines[1]
    assert "IsNameEntry" not in "\n".join(lines)
    assert lines[-1] == "Replace: Restores 15 HP."


def test_render_both_emits_two_blocks():
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "X", "description": "Y"}])
    assert lines.count(">DATABASE") == 2                  # one name block + one help block
    assert lines.count("FindAndReplace") == 2             # one modifier each (engine applies only the first)
    assert any("IsNameEntry == true" in l for l in lines)
    assert any("IsHelpEntry == true" in l for l in lines)


def test_render_resolves_id_and_name_forms():
    by_name = IT.render_block_lines([{"name": "Hi-Potion", "display_name": "X"}])
    by_id = IT.render_block_lines([{"name": HIPOT, "display_name": "X"}])
    assert by_name == by_id
    assert f"EntryId == {HIPOT}" in by_name[1]


def test_render_escapes_dollar():
    # Replace is a .NET Regex.Replace replacement -> $ must be doubled (else $N reads as a group ref)
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "Cost $5"}])
    assert lines[-1] == "Replace: Cost $$5"


def test_render_newline_to_backslash_n():
    # the engine reads the patch line-by-line then converts \n back to a newline -> a multi-line description
    # must collapse onto ONE Replace: line as the two chars \n
    lines = IT.render_block_lines([{"name": "Potion", "description": "Line1\nLine2"}])
    assert lines[-1] == r"Replace: Line1\nLine2"
    assert sum(1 for l in lines if l.startswith("Replace:")) == 1   # still one line (no embedded newline)


def test_render_crlf_normalised():
    lines = IT.render_block_lines([{"name": "Potion", "description": "A\r\nB\rC"}])
    assert lines[-1] == r"Replace: A\nB\nC"


def test_render_empty():
    assert IT.render_block_lines([]) == []
    assert IT.render_block_lines(None) == []


# ---- error paths (raise ItemTextError -> fail the lint/build, never the game) ------------------
def test_render_missing_name_raises():
    try:
        IT.render_block_lines([{"display_name": "X"}])
        assert False, "expected ItemTextError"
    except IT.ItemTextError as ex:
        assert "needs a `name`" in str(ex)


def test_render_neither_field_raises():
    try:
        IT.render_block_lines([{"name": "Potion"}])
        assert False
    except IT.ItemTextError as ex:
        assert "neither display_name nor description" in str(ex)


def test_render_unknown_item_raises():
    try:
        IT.render_block_lines([{"name": "Definitely Not An Item", "display_name": "X"}])
        assert False
    except IT.ItemTextError as ex:
        assert "unknown item" in str(ex)


def test_render_non_string_text_raises():
    try:
        IT.render_block_lines([{"name": "Potion", "display_name": 123}])
        assert False
    except IT.ItemTextError as ex:
        assert "must be a string" in str(ex)


def test_render_non_table_raises():
    try:
        IT.render_block_lines(["not a table"])
        assert False
    except IT.ItemTextError as ex:
        assert "must be a table" in str(ex)


def test_render_noitem_rejected():
    # 255 = RegularItem.NoItem (the empty-slot sentinel) is not a real item -> rejected (mirrors shop/synthesis)
    for nm in (255, "NoItem"):
        try:
            IT.render_block_lines([{"name": nm, "display_name": "X"}])
            assert False, f"expected ItemTextError for {nm!r}"
        except IT.ItemTextError as ex:
            assert "NoItem" in str(ex)


def test_render_literal_backslash_n_rejected():
    # a literal backslash-n cannot be represented (the engine rewrites \n -> newline) -> fail offline, not in-game
    try:
        IT.render_block_lines([{"name": "Potion", "description": r"50\n100 HP"}])
        assert False, "expected ItemTextError"
    except IT.ItemTextError as ex:
        assert "backslash-n" in str(ex)


def test_render_real_newline_still_ok():
    # a REAL newline (the intended line break) is fine -- only a LITERAL backslash-n is rejected
    lines = IT.render_block_lines([{"name": "Potion", "description": "A\nB"}])
    assert lines[-1] == r"Replace: A\nB"


# ---- validate_blocks (offline lint) -----------------------------------------------------------
def test_validate_blocks_clean():
    assert IT.validate_blocks([{"name": "Potion", "display_name": "X"}]) == []


def test_validate_blocks_surfaces_error():
    probs = IT.validate_blocks([{"name": "Potion"}])
    assert probs and "neither display_name nor description" in probs[0]


# ---- merge_text_patch (non-clobbering splice under //markers) ----------------------------------
def test_merge_into_empty():
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "X"}])
    out = IT.merge_text_patch("", lines, 4003)
    assert "// >>> ff9mapkit field 4003 TextPatch" in out
    assert "// <<< ff9mapkit field 4003" in out
    assert ">DATABASE" in out


def test_merge_preserves_other_lines_and_replaces_prior():
    lines1 = IT.render_block_lines([{"name": "Potion", "display_name": "First"}])
    live = IT.merge_text_patch("Battle: 5\nMusic: 9\n", lines1, 4003)
    assert "Battle: 5" in live and "Music: 9" in live      # a co-resident BattlePatch line survives... (own file, but proves preservation)
    lines2 = IT.render_block_lines([{"name": "Potion", "display_name": "Second"}])
    out = IT.merge_text_patch(live, lines2, 4003)
    assert "Replace: Second" in out
    assert "Replace: First" not in out                    # prior block REPLACED, not duplicated
    assert out.count("// >>> ff9mapkit field 4003") == 1   # exactly one marked block
    assert "Battle: 5" in out and "Music: 9" in out        # other lines preserved across the re-merge


def test_merge_distinct_fields_coexist():
    a = IT.merge_text_patch("", IT.render_block_lines([{"name": "Potion", "display_name": "A"}]), 4003)
    b = IT.merge_text_patch(a, IT.render_block_lines([{"name": "Hi-Potion", "display_name": "B"}]), 4100)
    assert "field 4003 TextPatch" in b and "field 4100 TextPatch" in b   # two fields' blocks coexist
    assert "Replace: A" in b and "Replace: B" in b


def test_merge_idempotent():
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "X"}])
    once = IT.merge_text_patch("", lines, 4003)
    twice = IT.merge_text_patch(once, lines, 4003)
    assert once == twice


def test_merge_empty_strips_prior_block():
    lines = IT.render_block_lines([{"name": "Potion", "display_name": "X"}])
    live = IT.merge_text_patch("keep\n", lines, 4003)
    stripped = IT.merge_text_patch(live, [], 4003)
    assert "field 4003 TextPatch" not in stripped
    assert "keep" in stripped


def test_merge_markers_are_comments():
    # the markers MUST start with // so the engine skips them (TextPatcher: line.StartsWith("//") -> continue)
    out = IT.merge_text_patch("", IT.render_block_lines([{"name": "Potion", "display_name": "X"}]), 4003)
    for ln in out.splitlines():
        if "ff9mapkit field" in ln:
            assert ln.startswith("//"), f"marker not a comment: {ln!r}"


# ---- validate() integration + build aggregation -----------------------------------------------
BASE = """
[field]
id = 4003
name = "TEXTTEST"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[player]
spawn = [0, -300]
"""


def _proj(toml, tmp_path):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def test_validate_clean(tmp_path):
    toml = BASE + '\n[[item_text]]\nname = "Potion"\ndisplay_name = "Mega Potion"\ndescription = "Heals lots."\n'
    probs = validate(_proj(toml, tmp_path))
    assert not any("item_text" in p for p in probs)


def test_validate_flags_empty_block(tmp_path):
    toml = BASE + '\n[[item_text]]\nname = "Potion"\n'
    probs = validate(_proj(toml, tmp_path))
    assert any("neither display_name nor description" in p for p in probs)


def test_validate_flags_unknown_item(tmp_path):
    toml = BASE + '\n[[item_text]]\nname = "Not An Item"\ndisplay_name = "X"\n'
    probs = validate(_proj(toml, tmp_path))
    assert any("unknown item" in p for p in probs)


class _StubProj:
    def __init__(self, name, item_text, tmp_path):
        self.raw = {"field": {"name": name}, "item_text": item_text}
        self.path = tmp_path / "f.toml"


def test_emit_item_text_aggregates_and_dedup_warns(tmp_path):
    p1 = _StubProj("FieldA", [{"name": "Potion", "display_name": "A"}], tmp_path)
    p2 = _StubProj("FieldB", [{"name": "Potion", "display_name": "B"}, {"name": "Hi-Potion", "description": "C"}],
                   tmp_path)
    lines, warns = _emit_item_text([p1, p2])
    assert lines.count(">DATABASE") == 3                  # Potion name x2 (later wins at runtime) + Hi-Potion desc
    assert any("display_name is set in two fields (FieldA and FieldB)" in w for w in warns)


def test_emit_item_text_dedup_keys_on_resolved_id_across_aliases(tmp_path):
    # review fix: the same item via different spellings/id must still warn (dedup keys on the resolved id)
    p1 = _StubProj("FieldA", [{"name": "Hi-Potion", "display_name": "A"}], tmp_path)
    p2 = _StubProj("FieldB", [{"name": HIPOT, "display_name": "B"}], tmp_path)   # numeric id, same item
    _lines, warns = _emit_item_text([p1, p2])
    assert any("is set in two fields (FieldA and FieldB)" in w for w in warns)


def test_emit_item_text_same_field_twice_message(tmp_path):
    # review fix: two blocks for one item in ONE field reads "twice on <field>", not "in two fields (X and X)"
    p = _StubProj("OnlyField", [{"name": "Potion", "display_name": "A"}, {"name": "Potion", "display_name": "B"}],
                  tmp_path)
    _lines, warns = _emit_item_text([p])
    assert any("set twice on OnlyField" in w for w in warns)
    assert not any("OnlyField and OnlyField" in w for w in warns)


def test_emit_item_text_none():
    class P:
        raw = {}
        path = "x"
    assert _emit_item_text([P()]) == ([], [])
