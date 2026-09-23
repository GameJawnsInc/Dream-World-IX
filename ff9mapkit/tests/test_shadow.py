"""The stock field BLOB SHADOW under kit-field actors (content.shadow + mapconfig + _shadowparams).

A synthesized field ships no MapConfigData, so the engine's per-model shadow service never runs and every
actor's ``FF9Shadow`` keeps its zero scale -- no shadow. The build now emits ``SetShadowSize`` +
``SetShadowAmplifier`` (the same two engine calls the MCF service makes) with the census values, on the
player and every ``[[npc]]``, and on nothing else: the invariant tests below build each field with the
shadows forced off and require the shadows-on build to differ by EXACTLY the shadow ops.
"""
from __future__ import annotations

import re
import struct

import pytest

from ff9mapkit import _shadowparams, mapconfig
from ff9mapkit.content import npc as N
from ff9mapkit.content import shadow as SH
from ff9mapkit.eb import EbScript, ebsrc, opcodes

ZIDANE, CSO, MOOGLE = 98, 217, 220


# ---- the MapConfigData decoder (authored bytes -- no SE data) ------------------------------------------

def _mcf(lights, chars, *, light_use=None, char_use=None) -> bytes:
    b = struct.pack("<HHHBBBBBB", 0, 1, 0, len(lights), len(lights) if light_use is None else light_use,
                    len(chars), len(chars) if char_use is None else char_use, 0, 0)
    for t, si, sr in lights:
        b += struct.pack("<4b", t, 0, si, sr) + bytes(8)
    for geo, si, sr in chars:
        b += struct.pack("<Hbb", geo, si, sr) + bytes(4)
    return b


def test_mapconfig_mirrors_the_engine_row_lookup():
    mc = mapconfig.parse(_mcf([(mapconfig.LIGHT_DEFAULT, 1, 2), (mapconfig.LIGHT_DEFAULT, 5, 5)],
                              [(0xFFFF, 4, 8), (CSO, 3, 10), (CSO, 7, 12)]))
    # ff9fieldMCFGetCharByID walks charUse-1 DOWN to 0: the LAST matching row wins
    assert mc.char(CSO).shadow_i == 7
    # a model with no row falls to the 0xFFFF default row; plus the default light -- the LOWEST-index
    # type-1 light, since ff9fieldMCFGetLightDefault walks in reverse and keeps overwriting
    assert mc.effective_shadow(ZIDANE) == (4 + 1, 8 + 2)
    assert mc.effective_shadow(CSO) == (7 + 1, 12 + 2)


def test_mapconfig_honours_the_use_counts():
    mc = mapconfig.parse(_mcf([], [(0xFFFF, 4, 8), (CSO, 3, 10)], char_use=1))
    assert mc.char(CSO) is None                         # row past charUse: the engine never sees it
    assert mc.effective_shadow(CSO) == (4, 8)
    assert mapconfig.parse(_mcf([], [(CSO, 3, 10)])).effective_shadow(ZIDANE) is None


# ---- the census table + the resolver ---------------------------------------------------------------------

def test_census_values_for_the_common_rigs():
    # the numbers the in-game bench exercises; a regenerated table that moves them should be looked at
    assert SH.params_for(ZIDANE) == (9, 4)
    assert SH.params_for(CSO) == (9, 3)
    assert SH.params_for(MOOGLE) == (6, 2)
    assert SH.params_for(59999) == _shadowparams.DEFAULT          # no shipping field shows it
    for m, (size, inten) in _shadowparams.SHADOW_PARAMS.items():
        assert 0 <= size <= SH.SIZE_MAX and 0 <= inten <= SH.INTENSITY_MAX, m


def test_resolve_semantics():
    assert SH.resolve(None, ZIDANE) == (9, 4)                     # absent = the census
    assert SH.resolve(True, ZIDANE) == (9, 4)
    assert SH.resolve(False, ZIDANE) is None                     # the opt-out
    assert SH.resolve({"size": 12}, ZIDANE) == (12, 4)            # partial override keeps the census intensity
    assert SH.resolve({"size": 12, "intensity": 6}, ZIDANE) == (12, 6)
    assert SH.init_ops(ZIDANE, False) == b""


@pytest.mark.parametrize("value", [3, "yes", {"radius": 4}, {"size": 256}, {"size": -1},
                                   {"intensity": 32}, {"size": True}, {"size": 4.0}])
def test_bad_values_are_refused(value):
    assert SH.problems(value, "[[npc]] 'x'")
    with pytest.raises(ValueError):
        SH.resolve(value, ZIDANE)


def test_ops_are_stocks_bytes():
    # field 576's Brahne Init ends 81 00 05 05 04; field 207's chest sets 81 00 20 20 then 85 00 C0 --
    # size first, amplifier second, amp = intensity << 3 (what fldmcf passes FF9ShadowSetAmpField)
    assert SH.ops(5, 4) == bytes.fromhex("81000505" "850020")
    assert SH.ops(32, 24) == bytes.fromhex("81002020" "8500c0")


# ---- the NPC Init ----------------------------------------------------------------------------------------

_ANIMS = {"stand": 1, "walk": 2, "run": 3, "left": 4, "right": 5}


def test_npc_init_without_shadow_is_unchanged():
    kw = dict(model=CSO, animset=100, anims=_ANIMS, x=10, z=20)
    assert N.build_npc_init(**kw) == N.build_npc_init(**kw, shadow=b"")


def test_npc_init_shadow_goes_last_after_the_init_tail():
    kw = dict(model=CSO, animset=100, anims=_ANIMS, x=10, z=20)
    tail = opcodes.encode(0x80)                                   # any init_tail
    body = N.build_npc_init(**kw, init_tail=tail, shadow=SH.ops(9, 3))
    assert body.endswith(tail + SH.ops(9, 3) + opcodes.RETURN)


# ---- the build (template-gated: needs `ff9mapkit extract-templates`) ------------------------------------

def _toml(tmp_path, body: str, name="SHD"):
    p = tmp_path / "f.field.toml"
    p.write_text(f'[field]\nid=30990\nname="{name}"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n' + body, encoding="utf-8")
    return p


def _init_shadow(ebb: bytes, entry: int):
    """``(size, amp)`` from the entry's Init, or None; asserts size precedes amp, both once."""
    eb = EbScript.from_bytes(ebb)
    ins = list(eb.instrs(eb.entry(entry).func_by_tag(0)))
    sz = [k for k, i in enumerate(ins) if i.op == SH.SET_SHADOW_SIZE]
    am = [k for k, i in enumerate(ins) if i.op == SH.SET_SHADOW_AMP]
    if not sz and not am:
        return None
    assert len(sz) == 1 and am == [sz[0] + 1], (sz, am)
    a, b = ins[sz[0]].args
    assert a == b
    return a, ins[am[0]].args[0]


def _script(p, **kw):
    from ff9mapkit import build
    return build.build_script(build.FieldProject.load(p), "us", {}, **kw)


def test_build_shadows_player_and_every_npc(tmp_path):
    from ff9mapkit.content.ladder import find_player_entry
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\n'
                        '[[npc]]\nname="a"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\n'
                        '[[npc]]\nname="b"\nmodel="GEO_NPC_F0_MOG"\npos=[-300,0]\nshadow=false\n'
                        '[[npc]]\nname="c"\nmodel="GEO_NPC_F0_CSO"\npos=[0,300]\nshadow={size=14,intensity=6}\n')
    ebb = _script(p)
    eb = EbScript.from_bytes(ebb)
    pe = find_player_entry(eb)
    assert _init_shadow(ebb, pe) == (9, 4 << 3)                   # Zidane, the template player
    # the player's ops sit right after its SetHeadFocusMask (field 451's Zidane)
    ops = [i.op for i in eb.instrs(eb.entry(pe).func_by_tag(0))]
    k = ops.index(SH.SET_HEAD_FOCUS_MASK)
    assert ops[k + 1:k + 3] == [SH.SET_SHADOW_SIZE, SH.SET_SHADOW_AMP]
    npcs = [e.index for e in eb.entries if not e.empty and e.index != pe
            and any(i.op == 0x2F for i in eb.instrs(e.func_by_tag(0)))]
    assert [_init_shadow(ebb, e) for e in npcs] == [(9, 3 << 3), None, (14, 6 << 3)]
    for e in npcs:                                                 # an NPC's shadow runs into its RETURN
        ins = list(eb.instrs(eb.entry(e).func_by_tag(0)))
        assert ins[-1].op == 0x04


def test_player_shadow_follows_a_reskin_and_opts_out(tmp_path):
    from ff9mapkit.content.ladder import find_player_entry
    ebb = _script(_toml(tmp_path, '[player]\nspawn=[0,0]\nmodel="GEO_NPC_F0_MOG"\n'))
    assert _init_shadow(ebb, find_player_entry(EbScript.from_bytes(ebb))) == (6, 2 << 3)
    ebb = _script(_toml(tmp_path, '[player]\nspawn=[0,0]\nshadow=false\n'))
    assert _init_shadow(ebb, find_player_entry(EbScript.from_bytes(ebb))) is None


def test_validate_reports_a_bad_shadow(tmp_path):
    from ff9mapkit import build
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\nshadow={size=999}\n'
                        '[[npc]]\nname="a"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\nshadow="on"\n')
    probs = build.validate(build.FieldProject.load(p))
    assert any(s.startswith("[player] shadow.size") for s in probs), probs
    assert any(s.startswith("[[npc]] 'a' shadow must be") for s in probs), probs


def test_a_field_with_mapconfig_is_left_to_its_mcf():
    from ff9mapkit import build

    class P:
        field = {"mapconfig": "mapconfig.bytes"}
        raw = {"player": {"shadow": False}, "npc": [{"name": "a"}, {"name": "b", "shadow": {"size": 3}}]}
    w = []
    assert build._casts_stock_shadows(P, w) is False
    assert build._casts_stock_shadows(P, w) is False               # per-language rebuild: warned ONCE
    assert len(w) == 1 and "[player]" in w[0] and "'b'" in w[0] and "'a'" not in w[0]
    P.field = {}
    assert build._casts_stock_shadows(P, []) is True


# ---- THE INVARIANT: shadows-on == shadows-off + exactly the shadow ops ---------------------------------

_LBL = re.compile(r"\bL(\d+)\b")
_SHADOW_LINE = re.compile(r"^(SetShadowSize|SetShadowAmplifier)\(")


def _canon(data: bytes) -> list:
    """Decompiled source with labels renumbered per function by first appearance -- an insert shifts every
    later label's OFFSET, never the control flow a label names."""
    out, names = [], {}
    for line in ebsrc.write_source(data, enrich=False).splitlines()[1:]:
        if line.startswith((".entry", ".func")):
            names = {}
        out.append(_LBL.sub(lambda m: "L#%d" % names.setdefault(m.group(1), len(names)), line))
    return out


def _built(project, *, shadows: bool, monkeypatch) -> bytes:
    from ff9mapkit import build
    with monkeypatch.context() as m:
        if not shadows:
            m.setattr(build, "_casts_stock_shadows", lambda p, w=None: False)
        return build.build_script(project, "us", {})


def _assert_only_shadow_ops_added(off: bytes, on: bytes, actors: int):
    import difflib
    added, other = [], []
    for d in difflib.ndiff(_canon(off), _canon(on)):
        if d.startswith("+ ") and _SHADOW_LINE.match(d[2:]):
            added.append(d)
        elif d[:2] in ("+ ", "- "):
            other.append(d)
    assert other == [], other[:6]
    assert len(added) == 2 * actors
    assert len(on) - len(off) == 7 * actors                       # 81 00 RR RR + 85 00 AA per actor


def test_only_the_shadow_ops_are_added(tmp_path, monkeypatch):
    from ff9mapkit import build
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\nface=64\n'
                        '[[player.arrival]]\nentrance=1\npos=[100,100]\n'
                        '[[npc]]\nname="a"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\ndialogue="hi"\n'
                        '[[npc]]\nname="b"\nmodel="GEO_NPC_F0_MOG"\npos=[-300,0]\nshadow=false\n')
    proj = build.FieldProject.load(p)
    _assert_only_shadow_ops_added(_built(proj, shadows=False, monkeypatch=monkeypatch),
                                  _built(proj, shadows=True, monkeypatch=monkeypatch), actors=2)


_EXAMPLES = ["vivi-hut/hut_int.field.toml", "siege/siege.field.toml", "SHOWCASE/showcase.field.toml",
             "capstone/capstone.field.toml"]


@pytest.mark.parametrize("rel", _EXAMPLES)
def test_bundled_examples_change_by_exactly_their_shadow_ops(rel, tmp_path, monkeypatch):
    from pathlib import Path
    from ff9mapkit import build
    toml = Path(__file__).resolve().parent.parent / "examples" / rel

    def eb(shadows):
        out = tmp_path / ("on" if shadows else "off")
        with monkeypatch.context() as m:
            if not shadows:
                m.setattr(build, "_casts_stock_shadows", lambda p, w=None: False)
            proj = build.FieldProject.load(toml)
            build.build_mod([proj], out, mod_name="ShadowCheck")
        return build.ModLayout(out).eb_path("us", f"EVT_{proj.name}.eb.bytes").read_bytes(), proj

    (off, proj), (on, _) = eb(False), eb(True)
    npcs = sum(1 for n in proj.raw.get("npc", []) if n.get("shadow", True) is not False)
    _assert_only_shadow_ops_added(off, on, actors=1 + npcs)
