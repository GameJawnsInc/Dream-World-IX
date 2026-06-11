"""Faithful object carry -- the verbatim ``.eb`` entry graft (``content/object.py``).

The graft is the engine-grounded replacement for the lossy player-clone object emit: it APPENDS a real
field object's entry bytes verbatim at a free slot and arms it, so the object renders byte-identical to
the source field (no "Zidane in a barrel skin"). These pin the mechanism offline; the closing proof that
the cask renders upright in-game is the human playtest (docs/OBJECT_CARRY.md, Phase 5).
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import data, eventscan
from ff9mapkit.content import object as _obj
from ff9mapkit.content import prop as _prop
from ff9mapkit.eb import EbScript, edit, opcodes
from ff9mapkit.eb.disasm import read_code

CLEAN = data.blank_field_bytes("us")


def _prop_spec(x=10, z=20, model=133, pose=1872):
    eb = _prop.inject_prop(CLEAN, x, z, model=model, pose=pose)
    return eventscan.scan_objects_verbatim(eb)[0]


# --- carry_bytes: verbatim whole-entry carry + the init_only subset --------------------------------
def test_carry_bytes_whole_entry_is_identity():
    s = _prop_spec()
    assert _obj.carry_bytes(s["entry_bytes"], None) == s["entry_bytes"]            # None = whole entry
    assert _obj.carry_bytes(s["entry_bytes"], s["carry_tags"]) == s["entry_bytes"]  # full tag set = identity


def test_carry_bytes_subset_drops_a_func_and_stays_parseable():
    s = _prop_spec()
    # a bare prop has only tag 0; build a richer entry by carrying an NPC (tags 0,1,3) minus the talk func
    from ff9mapkit.content import npc as _npc
    ns = eventscan.scan_objects_verbatim(_npc.inject_npc(CLEAN, 0, 0, model=220, animset=50))[0]
    sub = _obj.carry_bytes(ns["entry_bytes"], [0, 1])
    assert sub[1] == 2                                       # func count dropped 3 -> 2
    # the subset is a valid entry: append it and the whole script still round-trips
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, sub)
    eb = EbScript.from_bytes(g)
    assert eb.to_bytes() == g and {f.tag for f in eb.entry(slot).funcs} == {0, 1}


# --- the byte-offset + value remap primitives ------------------------------------------------------
def test_arg_byte_offset_matches_the_decoder():
    # InitObject 0x09 (< 0x10, NO argflag): slot@1, arg@2
    init, _ = read_code(opcodes.init_object(7, 3), 0)
    assert _obj._arg_byte_offset(init, 0) == 1 and _obj._arg_byte_offset(init, 1) == 2
    # RunScriptSync 0x14 (>= 0x10, argflag byte): level@2, uid@3, tag@4
    sync, _ = read_code(opcodes.run_script_sync(2, 250, 9), 0)
    assert _obj._arg_byte_offset(sync, 1) == 3 and sync.imm(1) == 250


def test_remap_value_rules():
    d2n = {7: 30, 8: 31}
    # self by index -> new slot; player by entry index -> 250; carried sibling -> its new slot
    assert _obj._remap_value("uid", 7, 7, 30, 5, d2n) == 30
    assert _obj._remap_value("uid", 5, 7, 30, 5, d2n) == 250
    assert _obj._remap_value("uid", 8, 7, 30, 5, d2n) == 31
    # engine specials are slot-independent -- kept verbatim
    for special in (250, 255, 251, 252, 253, 254):
        assert _obj._remap_value("uid", special, 7, 30, 5, d2n) == special


def test_remap_entry_refs_rewrites_self_and_player_by_index():
    # an entry whose func RunScripts the player BY ENTRY INDEX (5) and ITSELF by index (7)
    rss = bytes([0x14, 0x00, 2, 5, 0])      # RunScriptSync(level=2, uid=5=player-entry, tag=0)
    rs = bytes([0x12, 0x00, 2, 7, 1])       # RunScript(level=2, uid=7=self-by-index, tag=1)
    body = rss + rs + opcodes.RETURN
    entry = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(CLEAN).first_free_slot()
    g = edit.append_entry(CLEAN, slot, entry)
    g = _obj.remap_entry_refs(g, slot, donor_idx=7, donor_player_entry=5, donor2new={7: slot})
    eb = EbScript.from_bytes(g)
    runs = {ins.op: ins for f in eb.entry(slot).funcs for ins in eb.instrs(f) if ins.op in (0x12, 0x14)}
    assert runs[0x14].imm(1) == 250          # player-by-index 5 -> the controlUID alias 250
    assert runs[0x12].imm(1) == slot         # self-by-index 7 -> the new slot
    assert eb.to_bytes() == g                # same-length patch -> still a valid script


# --- graft_objects end to end ----------------------------------------------------------------------
def test_graft_clean_prop_roundtrips_verbatim():
    s = _prop_spec(x=120, z=-340, model=133, pose=1872)
    g = _obj.graft_objects(CLEAN, [dict(s)])
    assert EbScript.from_bytes(g).to_bytes() == g
    back = eventscan.scan_objects_verbatim(g)
    assert len(back) == 1 and back[0]["model_id"] == 133 and back[0]["pose"] == 1872
    assert back[0]["instances"][0]["x"] == 120 and back[0]["instances"][0]["z"] == -340
    # the carried entry is byte-identical to the donor entry (modulo the slot it lives in)
    assert eventscan._entry_bytes(g, back[0]["donor_idx"]) == s["entry_bytes"]


def test_graft_refused_objects_are_skipped():
    s = dict(_prop_spec())
    s["graft_safety"] = "refuse"
    assert _obj.graft_objects(CLEAN, [s]) == CLEAN          # nothing grafted


def test_graft_grows_entry_table_past_the_template_ceiling():
    s = _prop_spec()
    specs = [{**s, "donor_idx": 100 + i} for i in range(14)]   # more than the blank field's 10 slots
    g = _obj.graft_objects(CLEAN, specs)
    eb = EbScript.from_bytes(g)
    assert eb.entry_count > 10 and eb.to_bytes() == g
    assert len(eventscan.scan_objects_verbatim(g)) == 14


def test_graft_arms_main_init_d9_positioned_object():
    # a synthetic Main_Init-D9-positioned object (the "moogle" class): its Init creates a model + reads
    # D9(0)/D9(4); the graft must set those in Main_Init right before the InitObject.
    init = (opcodes.encode(eventscan.SET_MODEL_OP, 133, 0) + opcodes.encode(0x1D)   # SetModel + CreateObject
            + opcodes.encode(eventscan.SET_STAND_ANIM_OP, 1872) + opcodes.RETURN)
    entry = bytes([0, 1]) + struct.pack("<HH", 0, 4) + init
    spec = {"donor_idx": 99, "entry_bytes": entry, "kind": "prop", "carry_tags": None,
            "graft_safety": "clean", "donor_player_entry": None, "self_positions": False,
            "needs_d9": {0: -250, 4: -571}, "instances": [{"arg": 0}]}
    g = _obj.graft_objects(CLEAN, [spec])
    assert EbScript.from_bytes(g).to_bytes() == g
    back = eventscan.scan_objects_verbatim(g)
    assert len(back) == 1 and back[0]["model_id"] == 133
    assert (back[0]["instances"][0]["x"], back[0]["instances"][0]["z"]) == (-250, -571)


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_graft_field122_cask_renders_faithfully_not_a_player_clone():
    # The headline case: the field-122 cask rendered UPSIDE-DOWN via the player-clone. The graft carries
    # its REAL entry verbatim -> upright at (-250,-571), pose 1904, with ZERO player-clone ops. (The
    # upright VISUAL is the human playtest; this pins the bytes.)
    from ff9mapkit import extract
    specs = eventscan.scan_objects_verbatim(extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0"))
    cask = next(s for s in specs if s["model"] == "GEO_ACC_F0_CSK")
    g = _obj.graft_objects(CLEAN, [dict(cask)])
    assert EbScript.from_bytes(g).to_bytes() == g
    back = next(x for x in eventscan.scan_objects_verbatim(g) if x["model"] == "GEO_ACC_F0_CSK")
    assert (back["instances"][0]["x"], back["instances"][0]["z"]) == (-250, -571)
    assert back["pose"] == 1904
    eb = EbScript.from_bytes(g)
    ops = {ins.op for f in eb.entry(back["donor_idx"]).funcs for ins in eb.instrs(f)}
    assert 0x2C not in ops                  # NO DefinePlayerCharacter (not a player clone)
    assert 2 not in [f.tag for f in eb.entry(back["donor_idx"]).funcs]   # the dangling interactive tag dropped
