"""THE FERRY LANE -- a dialogue-CHOICE worldmap exit (stock's Blue Narciss "Where to?" idiom).

Covers the two halves that can silently rot:
  * the DESUGAR -- `[[ferry]]` -> an ordinary `[[choice]]` with worldmap option rows, decline LAST
    (the engine's CANCEL/B returns the last row, so the decline arm must be there and must be last or
    a mis-press sails you somewhere);
  * the BYTE CONTRACT of a worldmap option row -- the same body a walk-out gateway emits: both
    position blocks, POSITION_PRESET_KEY 35, and never the band-invariant key 62 that caused the
    original 9009 fall-through.

Pure logic: no game install, no templates, so these run everywhere (unlike the byte-level slice).
"""
from __future__ import annotations

import tomllib

import pytest

from ff9mapkit import build
from ff9mapkit.content import choice as C
from ff9mapkit.content import region as R
from ff9mapkit.content import worldexit as WX

FERRY_TOML = """
[field]
id = 6601
name = "LANTERN_HALL"
area = 55

[[npc]]
name = "Purser"
pos = [130, -1650]
model = 220
dialogue = "Kupo!"

[[ferry]]
npc = "Purser"
prompt = "Where shall we sail, kupo?"
decline = "Not yet, kupo."
decline_reply = "Kupo!"

[[ferry.destination]]
name = "Ashvale"
arrive = [60.0, -1168.0]
arrive_face = 192

[[ferry.destination]]
name = "Larkspur"
arrive = [688.0, -616.0]
arrive_face = 64
"""


def _load(tmp_path, text=FERRY_TOML):
    p = tmp_path / "f.toml"
    p.write_text(text, encoding="utf-8")
    return build.FieldProject.load(p)


# --- the desugar -------------------------------------------------------------------------------

def test_ferry_desugars_to_a_choice_with_decline_last(tmp_path):
    pr = _load(tmp_path)
    chs = pr.raw["choice"]
    assert len(chs) == 1 and chs[0]["npc"] == "Purser" and chs[0]["_ferry"] is True
    rows = chs[0]["options"]
    assert [r["text"] for r in rows] == ["Ashvale", "Larkspur", "Not yet, kupo."]
    # the two destinations carry worldmap arms; the decline carries NONE (it just closes)
    assert rows[0]["worldmap"] == {"arrive": [60.0, -1168.0], "face": 192}
    assert rows[1]["worldmap"] == {"arrive": [688.0, -616.0], "face": 64}
    assert "worldmap" not in rows[-1] and "warp" not in rows[-1]


def test_ferry_menu_is_instant_by_default(tmp_path):
    """A travel menu should POP, not type on character-by-character."""
    assert _load(tmp_path).raw["choice"][0]["instant"] is True


def test_no_ferry_block_leaves_raw_untouched(tmp_path):
    """A field with no [[ferry]] must not gain a `choice` key -- byte-identical builds depend on it."""
    pr = _load(tmp_path, FERRY_TOML.split("[[ferry]]")[0])
    assert "choice" not in pr.raw


# --- lint --------------------------------------------------------------------------------------

@pytest.mark.parametrize("mutate,needle", [
    (lambda s: s.split("[[ferry.destination]]")[0], "at least one [[ferry.destination]]"),
    (lambda s: s.replace('decline = "Not yet, kupo."', ""), "needs decline"),
    (lambda s: s.replace("arrive_face = 64", "arrive_face = 999"), "must be a raw facing byte"),
    (lambda s: s.replace('prompt = "Where shall we sail, kupo?"', ""), "needs a prompt"),
    (lambda s: s.replace("arrive = [688.0, -616.0]", "arrive = [688.0]"), "needs arrive = [x, z]"),
    (lambda s: s.replace('npc = "Purser"\nprompt', 'npc = "Nobody"\nprompt'), "is not a defined [[npc]]"),
])
def test_lint_rejects_malformed_ferries(tmp_path, mutate, needle):
    pr = _load(tmp_path, mutate(FERRY_TOML))
    problems = [p for p in build.validate(pr) if "[[ferry]]" in p]
    assert any(needle in p for p in problems), f"expected {needle!r}, got {problems}"


def test_lint_accepts_the_good_ferry(tmp_path):
    assert not [p for p in build.validate(_load(tmp_path)) if "[[ferry]]" in p]


# --- the byte contract of a worldmap option row -------------------------------------------------

def _key(v):
    return R.set_var(R.GLOB_INT16, R.FIELD_ENTRANCE_IDX, v)


def test_worldmap_option_emits_the_full_exit_body():
    body = C.option_body({"worldmap": {"arrive": [60.0, -1168.0], "face": 192}})
    assert WX.arrive_writes(60.0, -1168.0, face=192) in body, "the arrive block must be written verbatim"
    assert body.count(_key(WX.POSITION_PRESET_KEY)) == 1, "exactly one POSITION_PRESET_KEY write"
    assert _key(62) not in body, "key 62 is the band-invariant D8:2=0 trap -- never emit it"


def test_worldmap_option_is_last_in_the_body():
    """The exit transitions away, so anything after it is unreachable -- a reply must precede it."""
    body = C.option_body({"worldmap": {"arrive": [1.0, -2.0], "face": 0}, "gil": 50}, reply_txid=7)
    assert body.index(WX.arrive_writes(1.0, -2.0, face=0)) > 0
    assert body.endswith(C.option_body({"worldmap": {"arrive": [1.0, -2.0], "face": 0}})[-16:])


def test_each_destination_gets_its_own_coords_and_face():
    a = C.option_body({"worldmap": {"arrive": [60.0, -1168.0], "face": 192}})
    b = C.option_body({"worldmap": {"arrive": [688.0, -616.0], "face": 64}})
    assert a != b
    assert WX.arrive_writes(688.0, -616.0, face=64) in b
    assert WX.arrive_writes(688.0, -616.0, face=64) not in a


def test_decline_row_emits_no_transition():
    """The stay-ashore arm must close cleanly: no arrive write, no preset key, no warp."""
    body = C.option_body({"text": "Not yet."}, reply_txid=3)
    assert _key(WX.POSITION_PRESET_KEY) not in body and _key(62) not in body
    for xz in ((60.0, -1168.0), (688.0, -616.0)):
        assert WX.arrive_writes(*xz, face=192) not in body


def test_warp_and_worldmap_are_mutually_exclusive():
    """Both end the function by transitioning away; `warp` wins and `worldmap` must not also fire."""
    body = C.option_body({"warp": 4600, "worldmap": {"arrive": [1.0, -2.0], "face": 0}})
    assert WX.arrive_writes(1.0, -2.0, face=0) not in body
