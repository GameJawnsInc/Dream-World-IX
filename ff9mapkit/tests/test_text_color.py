"""Colour + glyph markup (studies/messages/SURVEY.md §6b -- the in-text census).

Every rule pinned here came from COUNTING stock's own `.mes` text, not from reading the engine's tag
parser, and the two differ in ways that matter:

* colour is the third most-used tag in the game (20,438 pushes, all 64 blocks), not a niche;
* it is SEMANTIC -- cyan wraps a substituted name, yellow a quantity or item -- so stock colours the
  parts of a line it did not author;
* every colour push is paired with `[HSHD]` (the corpus counts match to the unit) and stock NEVER pops
  with `[-]` (zero occurrences), so a span is `[CODE][HSHD]...[C8C8C8][HSHD]` and nothing else;
* the system announce box is the exception that stopped this from being auto-applied everywhere.
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, lint_logic, validate
from ff9mapkit.content import text as _text

BASE = """
[field]
id = 30605
name = "COLTEST"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def _problems(tmp_path, toml):
    """validate() errors + lint_logic() warnings -- markup problems are advisory (a stray brace
    still builds; it just renders literally), so they surface through the lint pass."""
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    proj = FieldProject.load(p)
    return list(validate(proj)) + list(lint_logic(proj))


# --- the counted palette -----------------------------------------------------------------------

def test_the_palette_is_the_six_codes_stock_actually_ships():
    assert _text.COLOR_CODES == {
        "white": "C8C8C8", "cyan": "68C0D8", "yellow": "C8B040",
        "pink": "B880E0", "brown": "D06050", "green": "78C840",
    }


def test_grey_is_deliberately_absent():
    # 909090 is in the engine palette and is used ZERO times in stock field text
    assert "909090" not in _text.COLOR_CODES.values()
    with pytest.raises(ValueError):
        _text.resolve_color("grey")


def test_semantic_aliases_carry_the_convention():
    assert _text.resolve_color("name") == _text.COLOR_CODES["cyan"]
    assert _text.resolve_color("item") == _text.COLOR_CODES["yellow"]
    assert _text.resolve_color("amount") == _text.COLOR_CODES["yellow"]


def test_every_button_glyph_name_is_one_stock_uses():
    assert set(_text.BUTTON_GLYPHS) == {"SELECT", "START", "PAD", "SQUARE", "CROSS", "UP",
                                        "LEFT", "RIGHT", "CIRCLE", "DOWN", "TRIANGLE"}


# --- the span shape ----------------------------------------------------------------------------

def test_a_span_is_stocks_exact_shape():
    # [CODE][HSHD] ... [C8C8C8][HSHD] -- the pair Memoria's own importer encodes as "{Yellow}"
    assert _text.color_span("item", "Ore") == "[C8B040][HSHD]Ore[C8C8C8][HSHD]"


def test_the_shadow_toggle_is_not_optional():
    # the corpus counts are identical to the unit (20,438 colours == 20,438 [HSHD]); a bare colour
    # push is not a shape stock ships
    out = _text.apply_markup("{cyan}x{/}")
    assert out.count("[HSHD]") == out.count("[68C0D8]") + out.count("[C8C8C8]")


def test_the_close_re_pushes_white_and_never_emits_a_pop():
    out = _text.apply_markup("{yellow}300 Gil{/} left")
    assert out == "[C8B040][HSHD]300 Gil[C8C8C8][HSHD] left"
    assert "[-]" not in out          # stock: zero [-] pops across all 64 blocks


def test_markup_expands_through_the_speaker_form():
    assert _text.with_speaker(None, "give {item}Ore{/}") == "give [C8B040][HSHD]Ore[C8C8C8][HSHD]"
    got = _text.with_speaker("Vivi", "give {item}Ore{/}")
    assert got.startswith("Vivi\n") and "[C8B040][HSHD]Ore[C8C8C8][HSHD]" in got


# --- the no-op guarantee -----------------------------------------------------------------------

def test_a_line_without_markup_is_byte_identical():
    for s in ("plain line", "has [ZDNE] a tag", "", "no braces at all"):
        assert _text.apply_markup(s) == s


def test_unrecognised_braces_are_left_alone():
    # an author's literal braces are prose, not markup -- only known colour names are touched
    assert _text.apply_markup("a {shrug} here") == "a {shrug} here"
    assert _text.apply_markup("{Kupo} said {cyan}hi{/}") == "{Kupo} said [68C0D8][HSHD]hi[C8C8C8][HSHD]"


# --- width ------------------------------------------------------------------------------------

def test_colour_tags_are_zero_width_for_wrapping():
    # markup expands BEFORE wrapping, so the tags must not eat the line budget
    assert _text.measure(_text.apply_markup("{item}Ore{/}")) == _text.measure("Ore")


def test_a_button_glyph_is_not_zero_width():
    # it draws a sprite; the old model scored every non-name tag 0 and under-measured prompt lines
    assert _text.measure("[DBTN=CROSS]") > 0


# --- validation --------------------------------------------------------------------------------

def test_an_unclosed_span_is_reported(tmp_path):
    toml = BASE + """
[[event]]
name = "sign"
zone = [[-300,-900],[300,-900],[300,-800],[-300,-800]]
message = "Unclosed {cyan}span here"
once = false
"""
    assert any("span(s) left open" in p for p in _problems(tmp_path, toml))


def test_a_stray_close_is_reported(tmp_path):
    toml = BASE + """
[[npc]]
name = "n"
preset = "vivi"
pos = [0, -600]
dialogue = "oops {/} here"
"""
    assert any("with no colour span open" in p for p in _problems(tmp_path, toml))


def test_balanced_markup_validates_clean(tmp_path):
    toml = BASE + """
[[npc]]
name = "seller"
preset = "vivi"
pos = [0, -600]
dialogue = "An {item}Ore{/} for {amount}300 Gil{/}, {name}[ZDNE]{/}."
speaker = "Seller"
"""
    assert _problems(tmp_path, toml) == []


def test_a_choice_row_emits_the_span(tmp_path):
    # the prompt gets markup via with_speaker; without the separate row pass the two halves of ONE
    # entry would disagree -- a coloured prompt over uncoloured rows
    toml = BASE + """
[[choice]]
prompt = "Buy what?"
zone = [[-300,-900],[300,-900],[300,-800],[-300,-800]]
options = [
  { text = "{item}Potion{/}" },
  { text = "Nothing" },
]
"""
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    from ff9mapkit.build import collect_text
    got = collect_text(FieldProject.load(p))
    blob = "".join(str(v) for v in (got.values() if isinstance(got, dict) else got))
    assert "[C8B040][HSHD]Potion[C8C8C8][HSHD]" in blob


# --- THE SPACE-AFTER-GLYPH LAW ------------------------------------------------------------------

def test_a_space_after_a_glyph_is_reported():
    """NGUIText drops every space following an inline image -- :885 skips the advance and :1081 skips
    the draw, and `afterImage` is cleared only by a NON-space character, so consecutive spaces all
    vanish. Padding right of a glyph is impossible at any width; the author gets told, not no-opped."""
    assert _text.space_after_glyph_problems("Press [DBTN=CROSS] to pick.")
    assert _text.space_after_glyph_problems("Padded:  [DBTN=CROSS]  two spaces")   # 2 is no better
    assert _text.space_after_glyph_problems("[ICON=27] x")                         # any inline image


def test_stocks_colon_idiom_is_clean():
    # ':' is a non-space character, so it clears afterImage and renders -- which is exactly why the
    # shipping game uses it 128 times and uses a space zero times
    assert _text.space_after_glyph_problems("[DBTN=CROSS]: Confirm") == []
    assert _text.space_after_glyph_problems("no glyph at all") == []


def test_the_zero_width_family_is_covered_too():
    # NGUIText.IsSpace covers ' ', U+2009 thin, U+200A hair and U+200B zero-width -- all dropped
    for ch in (" ", "\u2009", "\u200a", "\u200b"):
        assert _text.space_after_glyph_problems(f"[DBTN=CROSS]{ch}x"), repr(ch)


def test_a_no_break_space_is_not_flagged():
    # U+00A0 is NOT in IsSpace, so it should survive the drop -- the one candidate padding character.
    # Bench 30603 round 4 asks whether the font actually has a glyph for it.
    assert _text.space_after_glyph_problems("[DBTN=CROSS]\u00a0\u00a0then") == []
