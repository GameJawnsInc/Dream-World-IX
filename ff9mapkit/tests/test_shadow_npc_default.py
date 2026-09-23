"""An ``[[npc]]`` and the ``[player]`` cast the census blob shadow for EVERY model -- they do NOT follow
``_shadowparams.STOCK_CASTS`` the way a ``[[prop]]`` does.

Decided from stock bytes (studies/actor-shadow/NPC-STOCK-CASTS.md). ``STOCK_CASTS`` asks whether a model's
free-standing stock objects ``DisableShadow`` on every path through their Init. For set dressing that IS the
ordinary case: the tent and the save book stand on the floor with no shadow. For a creature or character it
is not. Its "disabled" votes come from where the object is. Most are birds perched on rooftops or in flight;
Alexandria's bird turns its shadow back ON as it lands. Others are the frog-catching pond's walkmesh-unbound
frogs and tadpoles, and cutscene apparitions hidden at Init. A kit ``[[npc]]`` has only ``pos = [x, z]``:
it always stands on the walkmesh, and stock's objects standing there cast (2141 of 2191). 12 of the 24
non-accessory models ``STOCK_CASTS`` disables never stand in stock at all, and the frog, the Lindblum trick
bird, Black Waltz 3 and the ``F4_JJY`` old man cast wherever they do. The player is the same: 1022 of
stock's 1054 player objects cast, and both ``STOCK_CASTS``-disabled models stock ever makes the player
(Black Waltz 3 on the cargo-ship deck, ``F4_JJY`` at the Eidolon Wall) cast.

These tests pin that default, so a later "fix" that routes the NPC or the player through the prop rule
fails here and points at the study.
"""
from __future__ import annotations

import pytest

from ff9mapkit import _shadowparams
from ff9mapkit.content import shadow as SH
from ff9mapkit.eb import EbScript

FROG, BIRD, TADPOLE, RED_DRAGON, BLACK_WALTZ_3 = 176, 63, 178, 616, 167

# [[npc]] lines: two through the kit's own archetypes (what an author reaches for), two by GEO name
_NPCS = ('[[npc]]\nname="frog"\narchetype="frog"\npos=[300,0]\n'
         '[[npc]]\nname="bird"\narchetype="bird"\npos=[-300,0]\n'
         '[[npc]]\nname="tadpole"\nmodel="GEO_NPC_F0_TAD"\npos=[0,300]\n'
         '[[npc]]\nname="dragon"\nmodel="GEO_MON_F0_CDR"\npos=[0,-600]\n')


def _toml(tmp_path, body: str):
    p = tmp_path / "f.field.toml"
    p.write_text('[field]\nid=30990\nname="SHN"\nborrow_bg="X"\narea=21\ntext_block=8\n'
                 '[camera]\npitch=30\ndistance=900\nfov=40\n' + body, encoding="utf-8")
    return p


def _script(p) -> bytes:
    from ff9mapkit import build
    return build.build_script(build.FieldProject.load(p), "us", {})


def _actors(ebb: bytes) -> dict:
    """``{entry: (model, (size, amp) or None)}`` for every object whose Init ``SetModel``\\ s a literal."""
    eb = EbScript.from_bytes(ebb)
    out = {}
    for e in eb.entries:
        f0 = None if e.empty else e.func_by_tag(0)
        ins = [] if f0 is None else list(eb.instrs(f0))
        sm = next((i for i in ins if i.op == SH.SET_MODEL), None)
        if sm is None or sm.imm(0) is None:
            continue
        sz = [i for i in ins if i.op == SH.SET_SHADOW_SIZE]
        am = [i for i in ins if i.op == SH.SET_SHADOW_AMP]
        assert len(sz) == len(am) <= 1, e.index
        out[e.index] = (int(sm.imm(0)), (sz[0].args[0], am[0].args[0]) if sz else None)
    return out


def _census(model) -> tuple:
    size, intensity = SH.params_for(model)
    return size, intensity << 3


def test_an_npc_of_a_model_stock_disables_casts_its_census(tmp_path):
    from ff9mapkit.content.ladder import find_player_entry
    ebb = _script(_toml(tmp_path, '[player]\nspawn=[0,0]\n' + _NPCS))
    pe = find_player_entry(EbScript.from_bytes(ebb))
    npcs = {m: s for e, (m, s) in _actors(ebb).items() if e != pe}
    assert set(npcs) == {FROG, BIRD, TADPOLE, RED_DRAGON}, npcs     # each archetype resolved to its model
    for m, s in npcs.items():
        assert s == _census(m), (m, s)                              # an absent key = the census, no prop rule


def test_the_npc_opt_out_still_works_for_those_models(tmp_path):
    ebb = _script(_toml(tmp_path, '[player]\nspawn=[0,0]\n'
                        '[[npc]]\nname="frog"\narchetype="frog"\npos=[300,0]\nshadow=false\n'))
    assert [s for m, s in _actors(ebb).values() if m == FROG] == [None]


def test_the_player_reskinned_to_a_model_stock_disables_casts_its_census(tmp_path):
    from ff9mapkit.content.ladder import find_player_entry
    ebb = _script(_toml(tmp_path, '[player]\nspawn=[0,0]\nmodel="GEO_SUB_F0_BW3"\n'))
    model, s = _actors(ebb)[find_player_entry(EbScript.from_bytes(ebb))]
    assert model == BLACK_WALTZ_3
    assert s == _census(BLACK_WALTZ_3)


def test_these_are_models_the_prop_rule_would_drop():
    # the premise: every model the tests above pin is one STOCK_CASTS disables, so they test the rule's
    # absence and not a model that casts either way
    if not hasattr(_shadowparams, "STOCK_CASTS"):
        pytest.skip("_shadowparams has no STOCK_CASTS in this tree (the [[prop]] rule has not landed)")
    for m in (FROG, BIRD, TADPOLE, RED_DRAGON, BLACK_WALTZ_3):
        assert _shadowparams.STOCK_CASTS.get(m) is False, m
