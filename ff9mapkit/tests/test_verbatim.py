"""Verbatim-.eb fork (docs/FORK_FIDELITY.md, the entry-0 carry): ship a real field's WHOLE event script
instead of re-synthesizing, remapping only the Field() destinations."""
from __future__ import annotations

import pytest

from ff9mapkit import data
from ff9mapkit.content import gateway as _gw
from ff9mapkit.content import verbatim as _vb
from ff9mapkit.eb import EbScript


def _fields(eb_bytes):
    s = EbScript.from_bytes(eb_bytes)
    return [i.imm(0) for e in s.entries if not e.empty for f in e.funcs
            for i in s.instrs(f) if i.op == 0x2B]


def test_startup_applies_to_verbatim_eb():
    # REGRESSION (review #1): [startup] presets must reach a verbatim .eb too. build_field ships the verbatim
    # bytes WITHOUT calling build_script, so it must apply _apply_startup itself -- else the documented
    # "pair with [startup] to boot a beat" is a silent no-op and the fork boots at scenario-zero.
    from ff9mapkit import build

    class _P:                                                  # _apply_startup only reads project.raw
        def __init__(self, raw):
            self.raw = raw

    blank = data.blank_field_bytes("us")
    assert build._apply_startup(_P({}), blank) == blank        # no [startup] -> byte-identical
    booted = build._apply_startup(_P({"startup": {"scenario": 2600}}), blank)
    assert booted != blank and len(booted) > len(blank)        # the ScenarioCounter preset was injected


def test_on_entry_arms_into_verbatim_bytes():
    # CONVERGENCE with story_flags' [[on_entry]]: like [startup], a field-load hook must fire in a verbatim
    # fork too -- build_field applies the shared _apply_on_entry to the verbatim bytes (the synthesize path's
    # build_script bypasses it). The helper arms a gated, once code entry into Main_Init.
    from ff9mapkit import build
    from ff9mapkit.build import _FlagAlloc
    from ff9mapkit.eb import EbScript

    class _P:
        name = "DV"

        def __init__(self, raw):
            self.raw = raw

    blank = data.blank_field_bytes("us")
    n0 = sum(1 for e in EbScript.from_bytes(blank).entries if not e.empty)
    assert build._apply_on_entry(_P({}), blank, {}, _FlagAlloc(None)) == blank   # no [[on_entry]] -> identical
    # a gated state-advance hook arms as one more code entry (the InitCode-in-Main_Init entry-beat hook)
    armed = build._apply_on_entry(_P({"on_entry": [{"set_scenario": 2600, "requires_scenario": 2000}]}),
                                  blank, {}, _FlagAlloc(None))
    assert armed != blank and len(armed) > len(blank)
    assert sum(1 for e in EbScript.from_bytes(armed).entries if not e.empty) == n0 + 1
    # verbatim drop_messages: a message hook drops the narration (warned) but STILL arms its state-advance
    warns = []
    armed_m = build._apply_on_entry(_P({"on_entry": [{"message": "Hi", "set_scenario": 2600}]}),
                                    blank, {0: 1234}, _FlagAlloc(None), drop_messages=True, warnings=warns)
    assert armed_m != blank and any("dropped" in w for w in warns)


def test_render_retarget_live_table_vs_template():
    # single-field import (no id_remap): the commented-out fill-in template, count 0 (byte-identical golden)
    txt, n = _vb.render_retarget([100, 200], None)
    assert n == 0 and txt == "# retarget = {\n#   100 = 0\n#   200 = 0\n# }\n"
    assert _vb.render_retarget([], None) == ("# retarget = {\n#   (this field has no Field() exits)\n# }\n", 0)
    # id_remap with NO in-chain dest -> still the template (nothing to wire), count 0
    assert _vb.render_retarget([100], {999: 4100})[1] == 0
    # import-chain: a LIVE table for the in-chain dest; the rest noted as live seams
    txt, n = _vb.render_retarget([100, 200], {100: 4100})
    assert n == 1
    assert txt == ("retarget = { 100 = 4100 }\n"
                   "# (the rest are live seams back into the real game -- not in this chain: 200)\n")
    # every dest in-chain -> no live-seam note
    assert _vb.render_retarget([100], {100: 4100}) == ("retarget = { 100 = 4100 }\n", 1)


def test_remap_fields_patches_destinations():
    # a gateway region warps Field(100); remap_fields retargets it (the verbatim-fork destination remap)
    eb = _gw.inject_gateway(data.blank_field_bytes("us"), 100,
                            zone=_gw.quad_zone([(0, 0), (10, 0), (10, 10), (0, 10)]))
    assert 100 in _fields(eb)
    out = _vb.remap_fields(eb, {100: 4100})
    assert 4100 in _fields(out) and 100 not in _fields(out)
    assert EbScript.from_bytes(out).to_bytes() == out          # still a valid, round-tripping eb
    # ids not in the map stay as live seams; an empty map is a byte-identical no-op
    assert _vb.remap_fields(eb, {999: 4100}) == eb
    assert _vb.remap_fields(eb, {}) == eb


def _game_ready():
    try:
        import UnityPy  # noqa: F401,PLC0415
        from ff9mapkit import config  # noqa: PLC0415
        return config.find_game_path(None) is not None
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_verbatim_ships_the_whole_donor_eb(tmp_path):
    # import --verbatim emits a [verbatim_eb] block + sidecar; the build ships the donor's WHOLE .eb
    # (Field-remapped) instead of synthesizing -- so the field runs its real logic (in-game proven on Dali Inn).
    from ff9mapkit import build, extract
    meta, toml = extract.write_native_project("fbg_n06_vgdl_map101_dl_inn_0", tmp_path, name="DV", verbatim=True)
    assert meta["imported_content"]["verbatim_eb"]
    assert "[verbatim_eb]" in toml.read_text()
    project = build.FieldProject.load(toml)
    donor = extract.extract_event_script("fbg_n06_vgdl_map101_dl_inn_0")
    assert _vb.verbatim_eb(project) == donor                    # no retarget -> the whole donor .eb, verbatim
    # P2 text: the donor's WHOLE .mes ships too, and the verbatim .eb's index-txids resolve into it (no remap)
    from ff9mapkit import dialogue
    assert meta["imported_content"]["text"]
    us = _vb.verbatim_mes(project, "us")
    assert us == dialogue.extract_field_mes("fbg_n06_vgdl_map101_dl_inn_0", "us")
    shown = {c.txid for c in dialogue.scan_dialogue(EbScript.from_bytes(donor)) if c.txid is not None}
    assert shown and shown <= set(dialogue.parse_mes(us))       # every line the .eb shows resolves in the text
    # with a retarget, that destination is patched in the shipped .eb (the rest stay live seams)
    exits = meta["imported_content"]["field_exits"]
    assert exits                                                # Dali Inn has Field() exits
    project.raw["verbatim_eb"]["retarget"] = {exits[0]: 4100}
    shipped = _vb.verbatim_eb(project)
    assert 4100 in _fields(shipped) and exits[0] not in _fields(shipped)


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_import_chain_verbatim_wires_a_connected_slice(tmp_path):
    # import-chain --verbatim forks a CONNECTED slice: every member ships its donor's WHOLE .eb (run as-is),
    # with the IN-CHAIN Field() exits retargeted to sibling forks + each member's donor .mes at the donor's
    # OWN registered textid (EVENT_ID_TO_MES -- a valid MesDB key). A 2-field slice: the Dali Inn (FieldScene
    # id 351) -> the Dali Wheel (350, one of its real exits). The inn's Field(350) must point at the wheel's
    # NEW id; the inn's out-of-chain exits stay live seams; both get the donor's registered textid.
    from collections import OrderedDict

    from ff9mapkit import build, campaign
    from ff9mapkit.chain import WALK_IN, GraphResult
    from ff9mapkit._fieldtext import EVENT_ID_TO_MES

    INN, WHEEL = 351, 350                                      # FieldScene ids (ID_TO_FBG keys), not event ids
    nodes = OrderedDict()
    nodes[INN] = {"zone": "vgdl", "found": True, "hop": 0, "overworld_exits": [], "encounter": None,
                  "music": None, "edges": [{"to": WHEEL, "kind": WALK_IN, "entrance": 0,
                                            "zone": [(0, 0), (1, 0), (1, 1), (0, 1)], "story_conditional": False}]}
    nodes[WHEEL] = {"zone": "vgdl", "found": True, "hop": 1, "overworld_exits": [], "encounter": None,
                    "music": None, "edges": []}
    result = GraphResult(nodes=nodes, portals=[], seams=[], unforkable=[], seeds=[INN],
                         allowed_zones={"vgdl"}, truncated=False, remaining=0,
                         bounds={"max_hops": 20, "max_fields": 25, "zones": ["vgdl"],
                                 "follow_scripted": False, "stop_at_zone_boundary": True})

    plan = campaign.write_campaign(result, tmp_path, id_base=6000, name="DALI", mod_folder="FF9CustomMap-ow",
                                   verbatim=True)
    by_real = {m.real_id: m for m in plan.members}
    inn, wheel = by_real[INN], by_real[WHEEL]
    assert inn.new_id == 6000 and wheel.new_id == 6001 and inn.mode == "native"

    # each member is a verbatim fork at its donor's OWN registered textid (a valid MesDB key, so the
    # FieldScene line registers). Same-zone members share it -- and ship IDENTICAL zone text, so no clobber.
    inn_proj = build.FieldProject.load(tmp_path / inn.toml_rel)
    wheel_proj = build.FieldProject.load(tmp_path / wheel.toml_rel)
    assert "verbatim_eb" in inn_proj.raw and "verbatim_eb" in wheel_proj.raw
    assert inn_proj.text_block == EVENT_ID_TO_MES[INN]         # the donor's own registered textid, not 1073
    assert wheel_proj.text_block == EVENT_ID_TO_MES[WHEEL]
    if inn_proj.text_block == wheel_proj.text_block:           # same zone -> the shipped .mes must be identical
        assert (_vb.verbatim_mes(inn_proj, "us") == _vb.verbatim_mes(wheel_proj, "us"))

    # the LIVE retarget: the inn's in-chain exits (Field(350)->wheel, Field(351)->itself) point at the forks;
    # its OUT-of-chain exits stay live seams back into the real game.
    inn_eb = _vb.verbatim_eb(inn_proj)
    rt = inn_proj.raw["verbatim_eb"]["retarget"]              # TOML inline-table keys are strings
    assert {int(k): int(v) for k, v in rt.items()} == {WHEEL: 6001, INN: 6000}
    assert 6001 in _fields(inn_eb) and 6000 in _fields(inn_eb)
    assert WHEEL not in _fields(inn_eb) and INN not in _fields(inn_eb)
    for seam in (352, 450):                                    # out-of-chain exits untouched (warp to live game)
        assert seam in _fields(inn_eb)
