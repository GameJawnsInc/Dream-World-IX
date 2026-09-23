"""An authored ``shadow.intensity`` stops at 15 -- from 16 the engine's blob colour WRAPS.

The kit emits ``SetShadowAmplifier(intensity << 3)``. The op's argument is one byte, so 0-31 all encode, and
``INTENSITY_MAX`` used to be 31. But ``EventEngine.SetRenderer`` draws the blob in colour ``(Byte)(amp * 2)``
(EventEngine.ProcessEvents.cs:612), so intensity ``i >= 16`` draws exactly as ``i - 16``: 16 draws no shadow
at all, and 31 draws the same as 15. In-game on bench 30922 (studies/actor-shadow/intensity_wrap.py), the same
slot at 15 and at 31 is pixel-identical, and so is 16 against 0, while 15 darkens the floor under the actor
by 8-11% luminance against a no-shadow control.

The census is NOT capped. Models 200 and 488 carry stock's own MapConfigData intensity 16, which wraps the
same way in stock, so an absent key must keep emitting it.
"""
from __future__ import annotations

import pytest

from ff9mapkit import _shadowparams
from ff9mapkit.content import shadow as SH

CSO = 217                                   # GEO_NPC_F0_CSO, census (9, 3) -- the in-game bench's NPC
V10, V11 = 200, 488                         # GEO_ACC_F0_V10 / _V11, the census's two stock 16s


def _toml(tmp_path, body: str):
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=30990\nname="SHW"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n' + body, encoding="utf-8")
    return p


def test_the_cap_is_where_the_engine_colour_stops_rising():
    # the authored range is exactly the prefix where a higher intensity draws a darker blob
    colours = [SH.blob_colour(i) for i in range(SH.INTENSITY_ENCODABLE_MAX + 1)]
    assert all(a < b for a, b in zip(colours, colours[1:SH.INTENSITY_MAX + 1]))
    assert colours[SH.INTENSITY_MAX + 1] < colours[SH.INTENSITY_MAX]            # 16 is the first wrap
    assert SH.blob_colour(16) == SH.blob_colour(0) == 0                         # no shadow at all
    assert SH.blob_colour(31) == SH.blob_colour(15) == 240
    assert SH.INTENSITY_MAX == 15
    assert SH.INTENSITY_ENCODABLE_MAX << 3 <= 0xFF < (SH.INTENSITY_ENCODABLE_MAX + 1) << 3


@pytest.mark.parametrize("v", [16, 20, 31])
def test_an_authored_intensity_past_15_is_refused_with_the_wrap_explained(v):
    msgs = SH.problems({"intensity": v}, "[[npc]] 'x'", CSO)
    assert len(msgs) == 1 and msgs[0].startswith("[[npc]] 'x' shadow.intensity must be an integer 0-15"), msgs
    assert "16-31 wrap" in msgs[0] and f"{v} would draw exactly as {v - 16}" in msgs[0], msgs
    assert "census value (3)" in msgs[0], msgs                                  # CSO's census, suggested
    assert ("no shadow at all" in msgs[0]) == (v == 16), msgs
    with pytest.raises(ValueError, match="16-31 wrap"):                          # the build path refuses too
        SH.resolve({"size": 9, "intensity": v}, CSO)


def test_15_and_below_still_pass():
    for v in range(SH.INTENSITY_MAX + 1):
        assert SH.problems({"intensity": v}, "x", CSO) == []
    assert SH.resolve({"size": 9, "intensity": 15}, CSO) == (9, 15)
    assert SH.ops(9, 15) == bytes.fromhex("81000909" "850078")


def test_without_a_model_the_message_still_points_at_the_census():
    msg = SH.problems({"intensity": 16}, "[player]")[0]
    assert "16-31 wrap" in msg and "census value for the actor's model" in msg, msg


def test_the_census_keeps_stocks_own_16s():
    # faithful, not capped: stock's MapConfigData gives these two models 16, and it wraps in stock too
    assert _shadowparams.SHADOW_PARAMS[V10][1] == 16 and _shadowparams.SHADOW_PARAMS[V11][1] == 16
    assert SH.resolve(None, V10) == (2, 16)                                     # absent = the census, unrefused
    assert SH.resolve({"size": 9}, V11) == (9, 16)                              # a size-only table keeps it
    assert SH.init_ops(V10) == SH.ops(2, 16) == bytes.fromhex("81000202" "850080")
    msg = SH.problems({"intensity": 16}, "x", V10)[0]                            # ...but authoring it is refused
    assert "census value (16): stock's own value" in msg and "matches stock exactly" in msg, msg


def test_validate_refuses_an_authored_wrap_on_every_surface(tmp_path):
    from ff9mapkit import build
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\nshadow={intensity=16}\n[[flag]]\nname="c1"\nindex=8712\n'
                        '[[npc]]\nname="a"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\nshadow={size=9,intensity=31}\n'
                        '[[npc]]\nname="ok"\nmodel="GEO_NPC_F0_CSO"\npos=[-300,0]\nshadow={size=9,intensity=15}\n'
                        f'[[npc]]\nname="v10"\nmodel={V10}\npos=[0,300]\n'
                        '[[prop]]\nprop="cask"\npos=[0,0]\nshadow={intensity=20}\n'
                        '[[chest]]\npos=[0,400]\nitem="Potion"\nflag="c1"\nshadow={intensity=17}\n'
                        '[[savepoint]]\nzone=[[-100,-100],[100,-100],[100,-300],[-100,-300]]\n'
                        'shadow={intensity=24}\n')
    probs = [s for s in build.validate(build.FieldProject.load(p)) if "shadow.intensity" in s]
    heads = sorted(s.split(" shadow.intensity")[0] for s in probs)
    assert heads == ["[[chest]] #0", "[[npc]] 'a'", "[[prop]] 'cask'", "[[savepoint]]", "[player]"], probs
    assert all("16-31 wrap" in s for s in probs), probs
    npc_a = next(s for s in probs if s.startswith("[[npc]] 'a'"))
    assert "31 would draw exactly as 15" in npc_a and "census value (3)" in npc_a, npc_a


def test_the_build_refuses_an_authored_wrap(tmp_path):
    from ff9mapkit import build
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\n'
                        '[[npc]]\nname="a"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\nshadow={intensity=16}\n')
    with pytest.raises(ValueError, match="16-31 wrap"):
        build.build_script(build.FieldProject.load(p), "us", {})
