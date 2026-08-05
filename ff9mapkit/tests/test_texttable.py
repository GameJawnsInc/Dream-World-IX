"""The ``[[text_table]]`` lane -- a field's own ``[TBLE]`` string banks and the ``[TEXT=<name>,slot]``
tags that read them (:mod:`ff9mapkit.content.texttable`).

WHY THIS LANE EXISTS, and therefore what these tests have to pin. A ``[TEXT=bank,slot]`` bank is a
TXID in the field's own ``.mes`` (``FF9TextTool.GetTableText``, FF9TextTool.cs:650-659) and
``collect_text`` assigns txids BY POSITION, so a hand-written number bakes an id that moves the moment
a line is added above it. Every way that can go wrong is SILENT in-game:

  * a bank pointing at the wrong entry renders another table's row;
  * a bank with no entry renders ``String.Empty`` (ETb.cs:283) -- a blank line, no log;
  * a row containing a newline silently becomes two rows and shifts every row below it.

So the failing cases are the point, and each of the three above has a test that asserts the kit
REFUSES rather than emits. The end-to-end (allocate -> substitute) property is checked on a BUILT
``.mes``, never on the generator: the generator is exactly what stayed green while the completion
dashboard shipped two frozen literal rows.

Nothing here needs game data or the install.
"""
from __future__ import annotations

import re

import pytest

from ff9mapkit import build as B
from ff9mapkit.content import text as T, texttable as TT

_ROWS = ("H", "G", "F")


# ---- the entry body ----------------------------------------------------------------------------
def test_the_entry_is_stocks_own_TBLE_shape():
    """Stock's Mognet roster is ``[TBLE=41,82,88,...]`` -- 41 rows, first parameter 41, the rest
    per-row byte offsets from the PSX blob. ``ParseTextSplitTags`` ignores every parameter
    (DialogBoxSymbols.cs:35-38), so we emit the count alone; the ``=`` form is kept because every
    other TBLE consumer in the kit and in Memoria matches the literal ``"[TBLE="``."""
    assert TT.entry_text(_ROWS) == "[TBLE=3,]H\nG\nF"
    body = TT.entry_text(_ROWS)
    assert body.startswith(TT.TABLE_OPEN + "=")
    # the engine's own walk: skip to the ']' of the tag, then Split('\n')
    assert body[body.index("]") + 1:].split("\n") == list(_ROWS)


def test_no_space_after_the_tag():
    """Stock's roster has one and it lands INSIDE row 0 -- harmless there (row 0 is a real name),
    fatal here, where row 0 is a value a player reads (' ---' instead of '---')."""
    assert TT.entry_text(("---",))[len("[TBLE=1,]")] == "-"


# ---- the blocks --------------------------------------------------------------------------------
def test_blocks_normalises_and_accepts_a_single_table():
    raw = {"text_table": [{"name": "th_rank", "rows": list(_ROWS)}]}
    assert TT.blocks(raw) == [TT.TextTable("th_rank", _ROWS)]
    assert TT.blocks({"text_table": {"name": "a", "rows": ["x"]}}) == [TT.TextTable("a", ("x",))]
    assert TT.blocks({}) == []


@pytest.mark.parametrize("blk, why", [
    ({"name": "", "rows": ["a"]}, "not usable inside"),
    ({"name": "600", "rows": ["a"]}, "not usable inside"),          # a bare number IS the txid form
    ({"name": "a,b", "rows": ["a"]}, "not usable inside"),          # the tag's own separator
    ({"name": "a b", "rows": ["a"]}, "not usable inside"),
    ({"name": "ok"}, "non-empty list"),
    ({"name": "ok", "rows": []}, "non-empty list"),
    ({"name": "ok", "rows": ["a\nb"]}, "NEWLINE-SEPARATED"),
    ({"name": "ok", "rows": ["a[ENDN]"]}, "terminate the entry"),
])
def test_a_bank_that_would_ship_BROKEN_is_refused(blk, why):
    with pytest.raises(TT.TextTableError) as e:
        TT.blocks({"text_table": [blk]})
    assert why in str(e.value)


def test_a_duplicate_name_is_refused():
    with pytest.raises(TT.TextTableError, match="duplicate name"):
        TT.blocks({"text_table": [{"name": "a", "rows": ["x"]},
                                  {"name": "a", "rows": ["y"]}]})


# ---- resolution --------------------------------------------------------------------------------
def test_a_named_bank_is_substituted_and_a_NUMERIC_one_is_left_alone():
    """``[TEXT=0,0]`` is the Mognet roster idiom (content.mognet.VAR_SPEAKER) and must survive this
    pass byte-identical -- the lane ADDS a naming layer, it does not replace the raw form."""
    assert TT.resolve("Rank [TEXT=th_rank,2]", {"th_rank": 612}) == "Rank [TEXT=612,2]"
    assert TT.resolve("[TEXT=0,0]\n“hi”", {"th_rank": 612}) == "[TEXT=0,0]\n“hi”"
    assert TT.resolve("nothing here", {}) == "nothing here"
    assert TT.refs("[TEXT=0,0] and [TEXT=th_rank,2]") == [("th_rank", 2)]


def test_an_UNKNOWN_bank_RAISES_rather_than_shipping():
    """THE CALL-SITE LAW. An unknown bank renders String.Empty -- a blank line with no error
    anywhere -- so it must be impossible to emit, not merely reported somewhere else."""
    with pytest.raises(TT.TextTableError) as e:
        TT.resolve("Rank [TEXT=th_rank,2]", {"hunt": 700})
    assert "no [[text_table]] named 'th_rank'" in str(e.value)
    assert "known banks here: ['hunt']" in str(e.value)


def test_a_slot_outside_the_engines_0_7_window_RAISES():
    """``ETb.GetStringFromTable`` guards ``index < 8u`` against gMesValue's Int32[8] and returns
    String.Empty otherwise (ETb.cs:270-283) -- another silent blank line."""
    with pytest.raises(TT.TextTableError, match="outside 0..7"):
        TT.resolve("[TEXT=a,8]", {"a": 600})
    assert TT.MAX_SLOT == 7


# ---- validate ----------------------------------------------------------------------------------
def test_validate_reports_an_unknown_bank_with_the_authored_key():
    raw = {"text_table": [{"name": "hunt", "rows": ["a"]}],
           "npc": [{"name": "n", "dialogue": "Rank [TEXT=th_rank,2]"}]}
    problems = TT.validate(raw)
    assert len(problems) == 1
    assert "npc[0].dialogue" in problems[0] and "[TEXT=th_rank,2]" in problems[0]
    assert TT.validate({"text_table": [{"name": "th_rank", "rows": ["a"]}],
                        "npc": [{"name": "n", "dialogue": "Rank [TEXT=th_rank,2]"}]}) == []


def test_validate_walks_NESTED_bodies_not_just_top_level_ones():
    raw = {"choice": [{"options": [{"text": "y", "reply": "Rank [TEXT=nope,0]"}]}]}
    problems = TT.validate(raw)
    assert len(problems) == 1 and "choice[0].options[0].reply" in problems[0]


# ---- the txid assignment rule ------------------------------------------------------------------
def test_txid_map_is_the_ONE_owner_of_the_assignment_rule():
    """The back-substitution needs an entry's txid one step BEFORE `build_mes` returns it. Re-deriving
    `start_txid + i` at that call site would be a second copy of the rule, and a drifted copy renders
    the wrong table or a blank line."""
    lines = ["a", "b", "c"]
    _body, mapping = T.build_mes(lines)
    assert mapping == T.txid_map(len(lines)) == {0: 500, 1: 501, 2: 502}
    assert T.txid_map(2, start_txid=7) == {0: 7, 1: 8}


# ---- END TO END, ON THE BUILT .mes ---------------------------------------------------------------
def _project(tmp_path, extra):
    toml = f"""
[field]
id = 30899
name = "TTBENCH"
area = 11

[camera]
pitch = 48.0
distance = 4500
fov = 42.2
[camera.frame]
back = 205
front = 432

[walkmesh]
quad = [[-1220, 257], [1220, 257], [1220, -1931], [-1220, -1931]]
frame = "world"

[player]
spawn = [0, -837]

[[npc]]
name = "keeper"
model = "GEO_NPC_F0_CSO"
pos = [400, -837]
{extra}
"""
    p = tmp_path / "tt.field.toml"
    p.write_text(toml, encoding="utf-8")
    return B.FieldProject.load(p)


_LANE = """
[[text_table]]
name = "th_rank"
rows = ["H", "G", "F"]

[[text_table]]
name = "hunt"
rows = ["---", "Zidane"]

[[choice]]
npc = "keeper"
prompt = "Which?"
  [[choice.options]]
  text = "Rank"
  reply = \"\"\"Rank  [TEXT=th_rank,0]
Won   [TEXT=hunt,1]\"\"\"
  window = 2
  values = ["expr:const(1)", "expr:const(1)"]

  [[choice.options]]
  text = "Nothing"
"""


def _mes(tmp_path, project):
    out = tmp_path / "mod"
    B.build_mod([project], out, mod_name="FF9CustomMap")
    raw = (out / "FF9_Data/embeddedasset/text/us/field/30899.mes").read_text(encoding="utf-8")
    pat = re.compile(r"_\[TXID=(\d+)\](?:\[STRT=[^\]]*\])?(?:\[TAIL=[^\]]*\])?(.*?)\[ENDN\]", re.S)
    return {int(m.group(1)): m.group(2) for m in pat.finditer(raw)}


def test_the_BUILT_mes_allocates_a_bank_and_substitutes_its_REAL_txid(tmp_path):
    """The whole lane, on the artifact: two banks land as their own .mes entries, and each tag in the
    page entry carries the txid of ITS OWN bank -- an off-by-one renders the other table."""
    bodies = _mes(tmp_path, _project(tmp_path, _LANE))
    rank = next(t for t, b in bodies.items() if b == TT.entry_text(("H", "G", "F")))
    hunt = next(t for t, b in bodies.items() if b == TT.entry_text(("---", "Zidane")))
    assert rank != hunt
    page = next(b for b in bodies.values() if "Rank  [TEXT=" in b)
    assert f"[TEXT={rank},0]" in page and f"[TEXT={hunt},1]" in page
    # the banks are added LAST, after every window entry -- so adding one shifts no existing txid
    assert rank > max(t for t, b in bodies.items() if TT.TABLE_OPEN not in b)


def test_a_field_with_NO_text_table_is_BYTE_IDENTICAL_to_before_the_lane(tmp_path):
    """The lane must be a no-op for every field that does not use it: the substitution pass returns a
    line with no named reference unchanged, and no entry is allocated."""
    plain = '\n[[npc]]\nname = "n2"\nmodel = "GEO_NPC_F0_CSO"\npos = [-400, -837]\ndialogue = "Hi."\n'
    bodies = _mes(tmp_path, _project(tmp_path, plain))
    assert not any(TT.TABLE_OPEN in b for b in bodies.values())
    assert "Hi." in "".join(bodies.values())


def test_a_reference_to_an_UNDECLARED_bank_fails_VALIDATE_not_the_playtest(tmp_path):
    bad = '\n[[npc]]\nname = "n2"\nmodel = "GEO_NPC_F0_CSO"\npos = [-400, -837]\n' \
          'dialogue = "Rank [TEXT=th_rank,0]"\n'
    problems = B.validate(_project(tmp_path, bad))
    assert any("names no [[text_table]]" in str(p) for p in problems), problems
