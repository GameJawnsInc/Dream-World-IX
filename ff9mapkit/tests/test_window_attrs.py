"""The shared window-attribute keys (Tier-1 of studies/messages/SURVEY.md §11):
``style`` / ``window`` / ``actor`` (opcode side) + ``instant`` / ``speed`` / ``duration`` /
``window_pos`` / ``box`` (text side) on every dialogue-bearing block.

Pins: the style-name table, the dressed ``.mes`` shapes, the emitted opcode bytes (WindowSync
with authored window/flags; WindowSyncEx for ``actor``), the no-keys byte-identical default,
and the validation rulebook (bad style/window/duration/speed, the window_pos-vs-tail conflict,
actor scoping)."""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, build_mod, collect_text, validate
from ff9mapkit.config import ModLayout
from ff9mapkit.content import text as _text
from ff9mapkit.eb import opcodes

BASE = """
[field]
id = 30601
name = "WINATTRS"
area = 11

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def _project(tmp_path, toml: str) -> FieldProject:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return FieldProject.load(p)


def _build_eb_bytes(tmp_path, toml: str) -> bytes:
    pr = _project(tmp_path, toml)
    assert validate(pr) == []
    out = tmp_path / "mod"
    build_mod([pr], out, mod_name="FF9CustomMap")
    return ModLayout(out).eb_path("us", "EVT_WINATTRS.eb.bytes").read_bytes()


# --------------------------------------------------------------- the style table ---

def test_style_names_match_the_engine_flag_bytes():
    # ETb.cs:481-489 + the 9 combinations stock ships (SURVEY.md §2)
    assert _text.resolve_style(None) == 128                    # default = the classic bubble
    assert _text.resolve_style("plain") == 0
    assert _text.resolve_style("notail") == 4
    assert _text.resolve_style("mognet") == 8
    assert _text.resolve_style("transparent") == 16
    assert _text.resolve_style("ate") == 64
    assert _text.resolve_style("bubble") == 128
    assert _text.resolve_style("bubble_notail") == 132
    assert _text.resolve_style("bubble_transparent") == 144
    assert _text.resolve_style("bubble_nopan") == 160
    assert _text.resolve_style(66) == 66                       # raw byte accepted


def test_style_rejects_unknown_and_out_of_range():
    with pytest.raises(ValueError):
        _text.resolve_style("speech")
    with pytest.raises(ValueError):
        _text.resolve_style(256)
    with pytest.raises(ValueError):
        _text.resolve_style(True)


# --------------------------------------------------------------- dress_window (pure) ---

def test_dress_window_no_keys_is_identity():
    assert _text.dress_window({}, "hello") == ("hello", None, None)
    assert _text.dress_window({"tail": "LOL"}, "hi") == ("hi", None, "LOL")


def test_dress_window_full_shape():
    line, strt, tail = _text.dress_window(
        {"window_pos": [30, 26], "speed": 2, "instant": True, "duration": 90, "box": [80, 2]}, "hi")
    assert line == "[MPOS=30,26][SPED=2][IMME]hi[TIME=90]"
    assert strt == (80, 2)
    assert tail == ""            # pinned window ships tail-less (stock's pinned shape)


def test_dress_window_pin_keeps_an_explicit_tail():
    # validate rejects the combination, but the emitter must not silently drop an explicit tail
    _, _, tail = _text.dress_window({"window_pos": [10, 10], "tail": "UPL"}, "x")
    assert tail == "UPL"


def test_detached_style_ships_tail_less():
    # THE WINDOW-GEOMETRY LAW: on a detached window a [TAIL] code is a screen-CORNER anchor, so a
    # non-bubble style with no explicit tail must ship NO tag (stock's centered system windows) --
    # the deployed WINSTYLE bench first shipped its toast pinned to a corner exactly this way
    for style in ("plain", "notail", "transparent", "mognet", "ate", 0, 16):
        assert _text.dress_window({"style": style}, "x")[2] == "", style
    # bubble-family styles keep the dialogue default (the tail IS meaningful there)
    for style in (None, "bubble", "bubble_nopan", "bubble_notail", "bubble_transparent"):
        assert _text.dress_window({"style": style}, "x")[2] is None, style
    # an explicit tail always wins (a corner-anchored plain window is stock-legitimate)
    assert _text.dress_window({"style": "plain", "tail": "LOL"}, "x")[2] == "LOL"


# --------------------------------------------------------------- .mes side (collect_text) ---

def test_collect_text_dresses_npc_and_event_lines(tmp_path):
    pr = _project(tmp_path, BASE + """
[[npc]]
name = "sign"
preset = "vivi"
pos = [0, -500]
dialogue = "Read me."
instant = true
duration = 60
window_pos = [20, 16]

[[event]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
message = "A breeze."
speed = 3
""")
    body = collect_text(pr)[0]
    assert "[MPOS=20,16][IMME]Read me.[TIME=60]" in body
    assert "[SPED=3]A breeze." in body
    # the pinned NPC line carries NO [TAIL]; the un-pinned event line keeps the default
    pinned = next(ln for ln in body.splitlines() if "Read me." in ln)
    assert "[TAIL=" not in pinned
    dressed_ev = next(ln for ln in body.splitlines() if "A breeze." in ln)
    assert "[TAIL=UPR]" in dressed_ev


def test_collect_text_choice_prompt_pin_and_box(tmp_path):
    pr = _project(tmp_path, BASE + """
[[choice]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
prompt = "Which way?"
window_pos = [20, 16]
box = [90, 4]
options = [ { text = "Up" }, { text = "Down" } ]
""")
    body = collect_text(pr)[0]
    # the prompt ENTRY spans physical lines (the [CHOO] rows sit after literal newlines) --
    # assert on the [ENDN]-delimited entry, not a single line
    entry = next(e for e in body.split("[ENDN]") if "Which way?" in e)
    assert entry.count("[MPOS=20,16]") == 1
    assert "[STRT=90,4]" in entry
    assert "[TAIL=" not in entry
    # the [MPOS] pin leads the entry text (stock's [MPOS][PCHC]... order)
    assert entry.index("[MPOS=") < entry.index("[CHOO]")


def test_collect_text_no_keys_is_unchanged(tmp_path):
    pr = _project(tmp_path, BASE + """
[[npc]]
name = "plain"
preset = "vivi"
pos = [0, -500]
dialogue = "Hello."
""")
    body = collect_text(pr)[0]
    line = next(ln for ln in body.splitlines() if "Hello." in ln)
    for tag in ("[MPOS=", "[TIME=", "[SPED=", "[IMME]"):
        assert tag not in line
    assert "[STRT=10,1][TAIL=UPR]" in line       # the classic dialogue defaults


# --------------------------------------------------------------- .eb side (built bytes) ---

def test_npc_style_and_window_reach_the_talk_opcode(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[npc]]
name = "ghost"
preset = "vivi"
pos = [0, -500]
dialogue = "..."
style = "transparent"
window = 3
""")
    # WindowSync(3, 16, 500) = 1f 00 03 10 f4 01
    assert opcodes.window_sync(3, 16, 500) in eb
    assert opcodes.window_sync(1, 128, 500) not in eb


def test_event_actor_player_emits_window_sync_ex(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[event]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
message = "It speaks over your head."
actor = "player"
""")
    # WindowSyncEx(250, 1, 128, txid) -- the txid is the event's line (npc-less field: 500)
    assert opcodes.window_sync_ex(250, 1, 128, 500) in eb
    assert opcodes.window_sync(1, 128, 500) not in eb


def test_event_actor_npc_attributes_to_that_npc(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[npc]]
name = "crier"
preset = "vivi"
pos = [200, -500]
dialogue = "Hear ye."

[[event]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
message = "Hear ye, hear ye!"
actor = "crier"
""")
    # the event's window is a WindowSyncEx naming SOME uid (the crier's slot), win 1, flags 128,
    # txid 501 (the npc line took 500)
    tail = bytes([0x01, 0x80]) + (501).to_bytes(2, "little")
    idx = eb.find(b"\x95\x00")
    assert idx != -1 and eb[idx + 3:idx + 7] == tail


def test_zone_choice_style_window_reach_the_prompt(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[choice]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
prompt = "Save your game?"
style = "mognet"
window = 2
options = [ { text = "Yes" }, { text = "No" } ]
""")
    # WindowSync(2, 8, 500)
    assert opcodes.window_sync(2, 8, 500) in eb


def test_cutscene_step_style_overrides_say_flags(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[cutscene]]
steps = [
  { say = "GO!", style = "notail", window = 2, duration = 45 },
  { say = "Plain line." },
]
""")
    assert opcodes.window_sync(2, 4, 500) in eb        # the styled step
    assert opcodes.window_sync(1, 128, 501) in eb      # the default step is untouched


def test_dim_bracket_matches_the_mognet_letter_shape():
    # the letter presentation is the DONOR'S EXACT SHAPE (field 1865 / mognet.letter_display):
    # CalcScreenPos + glow fade + Wait, WindowASYNC + RaiseWindows + WaitWindow, restore fade.
    # RaiseWindows is LOAD-BEARING -- without it the text renders UNDER the fade (the round-4
    # bench: dark letter outlines behind the dim). A plain WindowSync is NOT a valid substitute.
    from ff9mapkit.content import event as _event
    b = _event.dim_bracket(1, 16, 500)
    assert b == (opcodes.encode(0xA9, 250) + opcodes.encode(0xEC, 2, 24, 255, 220, 220, 250)
                 + opcodes.wait(16)
                 + opcodes.window_async(1, 16, 500)
                 + opcodes.encode(0x8E)                 # RaiseWindows: text ABOVE the fade
                 + opcodes.encode(0x54, 1)              # WaitWindow: synchronous net semantics
                 + opcodes.encode(0xA9, 250) + opcodes.encode(0xEC, 7, 16, 255, 0, 0, 0)
                 + opcodes.wait(16))
    assert opcodes.window_sync(1, 16, 500) not in b     # no sync window hiding under the fade
    assert _event.message(500, dim=False) == opcodes.window_sync(1, 128, 500)   # default untouched
    # actor attribution inside the bracket rides the async-Ex form
    bx = _event.dim_bracket(1, 128, 500, actor_uid=250)
    assert opcodes.window_async_ex(250, 1, 128, 500) in bx


def test_npc_dim_wraps_the_talk_window(tmp_path):
    eb = _build_eb_bytes(tmp_path, BASE + """
[[npc]]
name = "whisperer"
preset = "vivi"
pos = [0, -500]
dialogue = "(a thought)"
style = "transparent"
dim = true
""")
    from ff9mapkit.content import event as _event
    assert _event.dim_bracket(1, 16, 500) in eb


def test_validate_rejects_dim_where_not_wired(tmp_path):
    problems = _problems(tmp_path, BASE + """
[[choice]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
prompt = "Pick"
dim = true
options = [ { text = "A" }, { text = "B" } ]
""")
    assert any("`dim`" in p and "not wired" in p for p in problems), problems


# --------------------------------------------------------------- validation ---

def _problems(tmp_path, toml: str) -> list:
    return validate(_project(tmp_path, toml))


def test_validate_accepts_the_new_keys(tmp_path):
    assert _problems(tmp_path, BASE + """
[[event]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
message = "ok"
style = "bubble_nopan"
window = 4
actor = "player"
instant = true
duration = 30
""") == []


@pytest.mark.parametrize("snippet,needle", [
    ('style = "speech"', "unknown window style"),
    ("window = 9", "window must be 0..7"),
    ("duration = 0", "duration must be"),
    ("speed = 300", "speed must be"),
    ("window_pos = [1, 2, 3]", "window_pos must be"),
    ("box = [10]", "box must be"),
    ('window_pos = [10, 10]\ntail = "UPL"', "drop tail or window_pos"),
    ('actor = "nobody"', "must be \"player\" or a named [[npc]]"),
    ('actor = "player"\nstyle = "plain"', "bubble-family style"),
])
def test_validate_rejects_bad_window_attrs(tmp_path, snippet, needle):
    problems = _problems(tmp_path, BASE + f"""
[[event]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
message = "x"
{snippet}
""")
    assert any(needle in p for p in problems), problems


def test_validate_rejects_actor_on_npc_block(tmp_path):
    problems = _problems(tmp_path, BASE + """
[[npc]]
name = "talker"
preset = "vivi"
pos = [0, -500]
dialogue = "hi"
actor = "player"
""")
    assert any("`actor` is not supported on this block" in p for p in problems), problems


def test_validate_rejects_actor_on_npc_attached_choice(tmp_path):
    problems = _problems(tmp_path, BASE + """
[[npc]]
name = "keeper"
preset = "vivi"
pos = [0, -500]

[[choice]]
npc = "keeper"
prompt = "Buy?"
actor = "player"
options = [ { text = "Yes" }, { text = "No" } ]
""")
    assert any("already attributes its window" in p for p in problems), problems


def test_validate_typoed_tail_now_caught_on_every_block(tmp_path):
    # the G18 fix: chest/coop/option tails used to ship typos as dead [TAIL=...] tags
    problems = _problems(tmp_path, BASE + """
[[choice]]
zone = [[-100,-700],[100,-700],[100,-600],[-100,-600]]
prompt = "Pick"
options = [ { text = "A", reply = "ok", tail = "UPPR" }, { text = "B" } ]
""")
    assert any("UPPR" in p and "TAIL" in p for p in problems), problems
