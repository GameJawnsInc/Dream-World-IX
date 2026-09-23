"""The stock field BLOB SHADOW under kit-field actors (content.shadow + mapconfig + _shadowparams).

A synthesized field ships no MapConfigData, so the engine's per-model shadow service never runs and every
actor's ``FF9Shadow`` keeps its zero scale -- no shadow. The build now emits ``SetShadowSize`` +
``SetShadowAmplifier`` (the same two engine calls the MCF service makes) with the census values, on the
player, every ``[[npc]]``, and the SET PIECES stock lets cast -- a ``[[prop]]`` whose model stock does not
``DisableShadow`` (``STOCK_CASTS``), every ``[[chest]]``, a save point's moogle + barrel_pop cask -- and on
nothing else (never a held prop): the invariant tests below build each field with the shadows forced off and
require the shadows-on build to differ by EXACTLY the shadow ops.
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
CHEST, CASK, TENT, SAVE_BOOK, FEATHER, LETTER = 75, 241, 225, 133, 134, 258


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


def test_stock_casts_is_stocks_script_verdict():
    # the census of stock's own Inits (DisableShadow on every path, or not) -- the rows the bench exercises
    for m in (75, 91, 701, 702, CASK, MOOGLE):                    # every chest variant, the cask, the moogle
        assert SH.stock_casts(m), m
    for m in (TENT, SAVE_BOOK, FEATHER, LETTER):                  # stock switches these off in their Init
        assert not SH.stock_casts(m), m
    assert SH.stock_casts(59999) is _shadowparams.PROP_DEFAULT_CASTS is False    # never shown standing free
    assert not SH.stock_casts("not a model")
    # most set dressing stays dark: the table's own accessory verdicts
    from ff9mapkit._modeldb import MODELS
    acc = [v for m, v in _shadowparams.STOCK_CASTS.items() if MODELS.get(m, "").startswith("GEO_ACC_")]
    assert sum(acc) < len(acc) / 2


def test_set_piece_value_semantics():
    assert SH.set_piece_value(None, CASK) is True                 # absent = stock's verdict for the model
    assert SH.set_piece_value(None, TENT) is False
    assert SH.set_piece_value(True, TENT) is True                 # an explicit value is the author's
    assert SH.set_piece_value(False, CASK) is False
    assert SH.set_piece_value({"size": 4}, TENT) == {"size": 4}
    assert SH.init_ops(TENT, SH.set_piece_value(None, TENT)) == b""
    assert SH.init_ops(CASK, SH.set_piece_value(None, CASK)) == SH.ops(*SH.params_for(CASK))


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


def test_chest_init_shadow_goes_last_after_enable_head_focus():
    from ff9mapkit.content import chest as C
    kw = dict(x=10, z=20, flag_idx=8712)
    assert C.build_chest_init(**kw) == C.build_chest_init(**kw, shadow=b"")
    body = C.build_chest_init(**kw, shadow=SH.ops(10, 4))
    assert body.endswith(opcodes.encode(C.ENABLE_HEAD_FOCUS, 0) + SH.ops(10, 4) + opcodes.RETURN)
    assert len(body) == len(C.build_chest_init(**kw)) + 7


def test_cask_init_shadow_goes_last():
    from ff9mapkit.content import savepoint as SP
    assert SP.cask_model() == CASK
    assert SP.build_cask_init(10, 20) == SP.build_cask_init(10, 20, shadow=b"")
    body = SP.build_cask_init(10, 20, shadow=SH.ops(11, 5))
    assert body.endswith(opcodes.encode(0x93, SP.CASK_FLAGS) + SH.ops(11, 5) + opcodes.RETURN)


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
        raw = {"player": {"shadow": False}, "npc": [{"name": "a"}, {"name": "b", "shadow": {"size": 3}}],
               "prop": [{"prop": "tent"}, {"prop": "cask", "shadow": False}],
               "chest": [{}, {"shadow": True}], "savepoint": [{"shadow": False}]}
    w = []
    assert build._casts_stock_shadows(P, w) is False
    assert build._casts_stock_shadows(P, w) is False               # per-language rebuild: warned ONCE
    assert len(w) == 1 and "[player]" in w[0] and "'b'" in w[0] and "'a'" not in w[0]
    assert "[[prop]] 'cask'" in w[0] and "'tent'" not in w[0]
    assert "[[chest]] #1" in w[0] and "[[chest]] #0" not in w[0] and "[[savepoint]] #0" in w[0]
    P.field = {}
    assert build._casts_stock_shadows(P, []) is True


# ---- the SET PIECES: [[prop]] (stock's per-model verdict, never held), [[chest]], the save point --------

_SET_PIECES = '''[player]
spawn=[0,0]
[[flag]]
name="c1"
index=8712
[[flag]]
name="c2"
index=8713
[[npc]]
name="holder"
model="GEO_NPC_F0_CSO"
pos=[300,0]
holds="cup"
[[prop]]
prop="cask"
pos=[100,100]
[[prop]]
prop="tent"
pos=[200,100]
[[prop]]
prop="tent"
pos=[300,100]
shadow=true
[[prop]]
prop="cask"
pos=[400,100]
shadow=false
[[prop]]
prop="save_point"
pos=[500,100]
[[prop]]
prop="cask"
pos=[600,100]
attach_to="holder"
[[chest]]
pos=[0,400]
item="Potion"
flag="c1"
[[chest]]
pos=[100,400]
gil=10
flag="c2"
model="F1"
shadow=false
[[savepoint]]
zone=[[-100,-100],[100,-100],[100,-300],[-100,-300]]
pos=[0,-200]
[[savepoint]]
zone=[[-500,-100],[-300,-100],[-300,-300],[-500,-300]]
pos=[-400,-200]
reveal_style="barrel_pop"
reveal_from=[-400,-250]
act_hop_to=[-400,-150]
'''
# every object that casts, (model, x, z) -> (size, amp): 9 actors. Everything else must carry NO size/amp op.
_SET_PIECE_CASTS = {
    (ZIDANE, None, None): (9, 4 << 3),          # the player (template spawn, position not read)
    (CSO, 300, 0): (9, 3 << 3),                 # the holder NPC
    (CASK, 100, 100): (11, 5 << 3),             # a stock-casting prop, key absent
    (TENT, 300, 100): (11, 4 << 3),             # a stock-dark prop, shadow = true
    (MOOGLE, 500, 100): (6, 2 << 3),            # the save_point composite's moogle part (its book stays dark)
    (CHEST, 0, 400): (10, 4 << 3),              # the chest
    (MOOGLE, 0, -200): (6, 2 << 3),             # the instant save moogle
    (CASK, -400, -250): (11, 5 << 3),           # the barrel_pop cask
    (MOOGLE, -400, -200): (6, 2 << 3),          # the barrel_pop moogle (hidden until the cask is pressed)
}


def _built_mod(project, out, *, shadows: bool, monkeypatch) -> bytes:
    from ff9mapkit import build
    with monkeypatch.context() as m:
        if not shadows:
            m.setattr(build, "_casts_stock_shadows", lambda p, w=None: False)
        build.build_mod([project], out, mod_name="ShadowCheck")
    return build.ModLayout(out).eb_path("us", f"EVT_{project.name}.eb.bytes").read_bytes()


def _object_inits(ebb: bytes):
    """``{(model, x, z): (entry, [Init instrs])}`` for every object Init with a literal SetModel -- the
    D9(0)/D9(4) consts every from-scratch kit object places itself with (the player reads (model, None, None))."""
    from ff9mapkit.content.ladder import find_player_entry
    eb = EbScript.from_bytes(ebb)
    pe = find_player_entry(eb)
    out = {}
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        if f0 is None:
            continue
        ins = list(eb.instrs(f0))
        sm = next((i for i in ins if i.op == 0x2F), None)
        if sm is None:
            continue
        body = ebb[f0.abs_start:f0.abs_end]
        xz = [None, None]
        if e.index != pe:
            for k, var in enumerate((0, 4)):
                at = body.find(bytes([0x05, 0xD9, var, 0x7D]))
                xz[k] = struct.unpack_from("<h", body, at + 4)[0] if at >= 0 else None
        key = (sm.args[0], *xz)
        assert key not in out, key                  # the benches place no two same-model objects together
        out[key] = (e.index, ins)
    return out, eb


def test_build_shadows_the_set_pieces_stock_shadows(tmp_path, monkeypatch):
    from ff9mapkit import build
    p = _toml(tmp_path, _SET_PIECES)
    proj = build.FieldProject.load(p)
    assert build.validate(proj) == []
    ebb = _built_mod(proj, tmp_path / "on", shadows=True, monkeypatch=monkeypatch)
    objs, eb = _object_inits(ebb)
    for key, want in _SET_PIECE_CASTS.items():
        assert key in objs, (key, sorted(objs))
        assert _init_shadow(ebb, objs[key][0]) == want, key
    casting = set(_SET_PIECE_CASTS)
    silent = [k for k in objs if k not in casting]
    assert silent, "the negative cases went missing"
    for e in eb.entries:                          # ...and NO other object anywhere carries a size/amp op
        if e.empty or e.index in {objs[k][0] for k in casting}:
            continue
        for f in e.funcs:
            assert not any(i.op in (SH.SET_SHADOW_SIZE, SH.SET_SHADOW_AMP) for i in eb.instrs(f)), e.index
    # every negative case, by name: the stock-dark tent, the opted-out cask + F1 chest, the composite's book,
    # both HELD props -- the `holds` cup, and a CASK attach_to'd to the holder, a model stock DOES cast, so
    # only the held rule keeps it dark -- and the act's book + feather, which keep their donor DisableShadow
    for key in [(TENT, 200, 100), (CASK, 400, 100), (91, 100, 400), (SAVE_BOOK, 500, 100)]:
        assert _init_shadow(ebb, objs[key][0]) is None, key
    held = [objs[(234, 300, 0)], objs[(CASK, 600, 100)]]
    assert all(any(i.op == 0x4C for i in ins) for _e, ins in held)          # both really are attached
    assert all(_init_shadow(ebb, e) is None for e, _ in held)
    acts = [objs[k] for k in objs if k[0] in (SAVE_BOOK, FEATHER) and k != (SAVE_BOOK, 500, 100)]
    assert acts and all(any(i.op == 0x80 for i in ins) for _e, ins in acts)
    # the stock SHAPE: every set piece's ops run straight into its Init RETURN
    for key in casting - {(ZIDANE, None, None)}:
        ins = objs[key][1]
        assert [i.op for i in ins[-3:]] == [SH.SET_SHADOW_SIZE, SH.SET_SHADOW_AMP, 0x04], key


def test_set_pieces_change_by_exactly_their_shadow_ops(tmp_path, monkeypatch):
    from ff9mapkit import build
    proj = build.FieldProject.load(_toml(tmp_path, _SET_PIECES))
    off = _built_mod(proj, tmp_path / "off", shadows=False, monkeypatch=monkeypatch)
    on = _built_mod(proj, tmp_path / "on", shadows=True, monkeypatch=monkeypatch)
    _assert_only_shadow_ops_added(off, on, actors=len(_SET_PIECE_CASTS))


def test_savepoint_shadow_false_darkens_the_moogle_and_its_cask(tmp_path, monkeypatch):
    from ff9mapkit import build
    body = ('[player]\nspawn=[0,0]\n[[savepoint]]\nzone=[[-500,-100],[-300,-100],[-300,-300],[-500,-300]]\n'
            'pos=[-400,-200]\nreveal_style="barrel_pop"\nreveal_from=[-400,-250]\nact_hop_to=[-400,-150]\n')
    proj = build.FieldProject.load(_toml(tmp_path, body + "shadow=false\n"))
    ebb = _built_mod(proj, tmp_path / "a", shadows=True, monkeypatch=monkeypatch)
    objs, _ = _object_inits(ebb)
    assert _init_shadow(ebb, objs[(MOOGLE, -400, -200)][0]) is None
    assert _init_shadow(ebb, objs[(CASK, -400, -250)][0]) is None
    # a table sizes the MOOGLE only; the cask keeps its census
    proj = build.FieldProject.load(_toml(tmp_path, body + "shadow={size=12,intensity=7}\n"))
    ebb = _built_mod(proj, tmp_path / "b", shadows=True, monkeypatch=monkeypatch)
    objs, _ = _object_inits(ebb)
    assert _init_shadow(ebb, objs[(MOOGLE, -400, -200)][0]) == (12, 7 << 3)
    assert _init_shadow(ebb, objs[(CASK, -400, -250)][0]) == (11, 5 << 3)


def test_validate_refuses_a_shadow_on_a_held_prop_and_bad_set_piece_values(tmp_path):
    from ff9mapkit import build
    p = _toml(tmp_path, '[player]\nspawn=[0,0]\n[[flag]]\nname="c1"\nindex=8712\n'
                        '[[npc]]\nname="h"\nmodel="GEO_NPC_F0_CSO"\npos=[300,0]\n'
                        '[[prop]]\nprop="cup"\npos=[0,0]\nattach_to="h"\nshadow=true\n'
                        '[[prop]]\nprop="cup"\npos=[0,0]\nattach_to="h"\nshadow=false\n'
                        '[[prop]]\nprop="cask"\npos=[0,0]\nshadow={radius=3}\n'
                        '[[chest]]\npos=[0,400]\nitem="Potion"\nflag="c1"\nshadow="yes"\n'
                        '[[savepoint]]\nzone=[[-100,-100],[100,-100],[100,-300],[-100,-300]]\n'
                        'shadow={intensity=40}\n')
    probs = build.validate(build.FieldProject.load(p))
    held = [s for s in probs if "held prop" in s]
    assert len(held) == 1 and held[0].startswith("[[prop]] 'cup' shadow"), probs   # false is fine
    assert any(s.startswith("[[prop]] 'cask' shadow: unknown key") for s in probs), probs
    assert any(s.startswith("[[chest]] #0 shadow must be") for s in probs), probs
    assert any(s.startswith("[[savepoint]] shadow.intensity") for s in probs), probs
    assert not any("unknown key 'shadow'" in s for s in probs), probs


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
