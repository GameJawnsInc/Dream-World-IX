"""logic-map -- the read-only legible VIEW of a verbatim fork's whole .eb (logic_map.py).

The pure layer (resolve_uid, the per-routine flag attribution, _func_kind) is tested with synthetic bytes,
so it runs with no install. The whole-field build + the cross-checks against the proven field-wide scanners
use the shipped ALEX100 fixture (skipped cleanly until `ff9mapkit extract-templates` regenerates it).
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from ff9mapkit import eventscan
from ff9mapkit import logic_map as LM

FIX = Path(__file__).parent / "fixtures"
_alex = FIX / "alex100-us.eb.bytes"
ALEX100 = _alex.read_bytes() if _alex.exists() else None
needs_alex = pytest.mark.skipif(ALEX100 is None, reason="alex100 fixture not extracted (run extract-templates)")


# ---- resolve_uid: the single GetObjUID convention (pure) ----
def test_resolve_uid_all_branches():
    # current_entry=7, two player entries [3, 5], entry_count=20
    assert eventscan.resolve_uid(255, 7, [3, 5], 20) == ("self", [7])
    assert eventscan.resolve_uid(250, 7, [3, 5], 20) == ("player", [3, 5])
    assert eventscan.resolve_uid(5, 7, [3, 5], 20) == ("player", [3, 5])    # a PC by entry index
    assert eventscan.resolve_uid(252, 7, [3, 5], 20) == ("party", [])
    assert eventscan.resolve_uid(0, 7, [3, 5], 20) == ("main", [0])          # Main_Init shared logic
    assert eventscan.resolve_uid(11, 7, [3, 5], 20) == ("object", [11])
    assert eventscan.resolve_uid(99, 7, [3, 5], 20) == ("unknown", [])       # out of range


def test_resolve_uid_player_precedes_object_and_main():
    # an object whose entry index doubles as a PC classifies as player, not object (matches _explain_call order)
    assert eventscan.resolve_uid(4, 0, [4], 20)[0] == "player"


def test_explain_call_uses_resolve_uid():
    """forkreport._explain_call is now the English layer over resolve_uid -- labels stay identical."""
    from ff9mapkit import forkreport as FR
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(ALEX100) if ALEX100 is not None else None
    n = eb.entry_count if eb is not None else 20
    assert FR._explain_call(_FakeEb(n), 7, 0, 12, set())[0] == "runs shared field logic (Main_Init routine #12)"
    assert FR._explain_call(_FakeEb(n), 7, 255, 3, set())[0] == "runs its own routine #3"
    assert FR._explain_call(_FakeEb(n), 7, 250, 4, {3})[0] == "directs the player (sequence #4)"


class _FakeEb:
    def __init__(self, entry_count):
        self.entry_count = entry_count


# ---- per-routine flag attribution (pure, synthetic bytes) ----
def test_flag_write_and_read_detection():
    # a GLOB set: 05 C4 <idx> 7D <i16> 2C 7F   (the byte after 05 is the var token)
    wset = b"\x05\xC4\x10\x7D" + struct.pack("<H", 1) + b"\x2C\x7F"
    assert LM._flag_write_at(wset, 0) == (0x10, "set")
    # a GLOB or-assign uses 3F
    wor = b"\x05\xC4\x11\x7D" + struct.pack("<H", 1) + b"\x3F\x7F"
    assert LM._flag_write_at(wor, 0) == (0x11, "or")
    # a GLOB read driving a JMP_TRUE (03): 05 C4 <idx> 7F 03 ...
    rd = b"\x05\xC4\x20\x7F\x03\x01\x00\x04"
    assert LM._flag_read_at(rd, 0) == (0x20, True)
    # a negated read (0E) before END flips require_set
    rdn = b"\x05\xC4\x21\x0E\x7F\x03\x01\x00\x04"
    assert LM._flag_read_at(rdn, 0) == (0x21, False)
    # a MAP/transient var (0xC5) is not a GLOB flag -> None on both
    assert LM._flag_write_at(b"\x05\xC5\x10\x7D\x01\x00\x2C\x7F", 0) is None
    assert LM._flag_read_at(b"\x05\xC5\x20\x7F\x03\x01\x00\x04", 0) is None


def test_func_kind_role_mapping():
    assert LM._func_kind("main", 0) == "main_init"
    assert LM._func_kind("main", 10) == "main_reinit"
    assert LM._func_kind("main", 12) == "shared_routine"
    assert LM._func_kind("npc", 3) == "npc_talk"
    assert LM._func_kind("player", 1) == "player_loop"
    assert LM._func_kind("gateway", 2) == "gateway_tread"


def test_build_logic_map_empty_bytes():
    lm = LM.build_logic_map(b"")
    assert lm.entries == [] and lm.nodes == [] and lm.sha256 == ""


def _eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as Main_Init's bytecode (mirrors test_aiauthor)."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1                                          # entryCount
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body   # type=0, fc=1, (tag=0, fpos=4), then code
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)      # off=8 (body @0x88)
    return bytes(head) + slot + funcbody


def test_flag_read_attribution_integrated():
    """A GLOB read driving a jump is attributed per-NODE and aggregates to scan_required_flags. Guards the
    build_logic_map read path that ALEX100 cannot cover (it has no read-gated jumps) -- the review's vacuous-test gap."""
    eb = _eb(bytes([0x05, 0xC4, 0x10, 0x7F, 0x03, 0x01, 0x00, 0x04]))   # 05 C4 idx=16 7F 03(JMP_TRUE) 0001 04
    lm = LM.build_logic_map(eb)
    reads = {(f["index"], f["require_set"]) for n in lm.nodes for f in n.flags_read}
    assert reads == {(0x10, True)} == set(eventscan.scan_required_flags(eb))


def test_reply_op_marked_unresolved_not_an_edge():
    """A REPLY*/RunScriptObject (0x16/0x18/0x1A) dispatches to the runtime caller -> a MARKED hole, never a
    drawn edge. The module's headline high-fidelity-WITH-HOLES guarantee (guards a silent-swallow regression)."""
    for op in (0x16, 0x18, 0x1A):
        eb = _eb(bytes([op, 0x00, 0x01, 0x02, 0x04]))    # op arg_flag=0 level=1 tag=2 RET
        lm = LM.build_logic_map(eb)
        un = [u for n in lm.nodes for u in n.unresolved]
        assert len(un) == 1 and "dynamic caller" in un[0]["reason"], (hex(op), un)
        assert all(not n.calls for n in lm.nodes), "a dynamic-caller dispatch is NOT a resolved edge"


def test_computed_operands_marked_unresolved():
    """Runtime-computed (expression) operands are MARKED unresolved -- never silently dropped or mis-routed."""
    lm = LM.build_logic_map(_eb(bytes([0x2B, 0x01, 0x7F, 0x04])))         # Field(<expr>) -> computed warp
    assert any(u["reason"] == "warp target computed" for n in lm.nodes for u in n.unresolved)
    assert not any(n.warps for n in lm.nodes), "a computed Field draws no warp edge"
    lm2 = LM.build_logic_map(_eb(bytes([0x12, 0x02, 0x01, 0x7F, 0x03, 0x04])))   # RunScript(1, <expr uid>, 3)
    assert any(u["reason"] == "call target computed" for n in lm2.nodes for u in n.unresolved)
    assert not any(n.calls for n in lm2.nodes), "a computed-uid call draws no edge"


# ---- whole-field build + cross-checks against the proven scanners (ALEX100) ----
@needs_alex
def test_build_logic_map_structure():
    lm = LM.build_logic_map(ALEX100, field_id=100)
    assert lm.sha256 and len(lm.sha256) == 64
    assert lm.entries and lm.nodes
    main = [e for e in lm.entries if e.role == "main"]
    assert len(main) == 1 and main[0].index == 0           # exactly one Main entry, at index 0
    # every node's byte bounds sit inside the eb
    assert all(0 <= n.abs_start <= n.abs_end <= len(ALEX100) for n in lm.nodes)
    # at least one Main routine exists
    assert any(n.kind in ("main_init", "main_reinit", "shared_routine") for n in lm.nodes)


@needs_alex
def test_flag_attribution_matches_field_wide_scanner():
    """Per-NODE flag attribution, aggregated, must equal the proven field-wide scanners exactly."""
    lm = LM.build_logic_map(ALEX100)
    node_sets = {(f["index"], f["mode"]) for n in lm.nodes for f in n.flags_set}
    assert node_sets == set(eventscan.scan_flags_set(ALEX100))
    node_reads = {(f["index"], f["require_set"]) for n in lm.nodes for f in n.flags_read}
    assert node_reads == set(eventscan.scan_required_flags(ALEX100))


@needs_alex
def test_item_attribution_matches_scan_item_ops():
    """Per-node item grants, aggregated, must match forkreport.scan_item_ops' distinct item ids."""
    from ff9mapkit import forkreport as FR
    lm = LM.build_logic_map(ALEX100)
    node_items = {g["id"] for n in lm.nodes for g in n.gives if g["kind"] == "item"}
    scan_items = {iid for iid, _cnt in FR.scan_item_ops(ALEX100)["gives"]}
    assert node_items == scan_items
    assert all(g.get("id") is not None for n in lm.nodes for g in n.gives if g["kind"] == "item"), \
        "a computed item id is NEVER routed into gives -- it is marked unresolved"
    assert any(u["op"] == "AddItem" and "runtime" in u["reason"]
               for n in lm.nodes for u in n.unresolved), "ALEX100's computed AddItem(s) are marked unresolved"


@needs_alex
def test_warp_targets_cover_walk_in_gateways():
    """Every walk-in gateway destination must appear as a Field() warp in some node."""
    lm = LM.build_logic_map(ALEX100)
    map_field_tos = {w["to"] for n in lm.nodes for w in n.warps if w["op"] == "Field"}
    walkin = {g["to"] for g in eventscan.scan_all_warps(ALEX100)["walk_in"]}
    assert walkin <= map_field_tos


@needs_alex
def test_to_dict_is_json_serializable():
    lm = LM.build_logic_map(ALEX100, field_id=100)
    blob = json.dumps(LM.to_dict(lm))           # raises if any value isn't serializable
    d = json.loads(blob)
    assert d["field_id"] == 100 and d["generated_from_sha256"] == lm.sha256
    assert d["entries"] and d["nodes"]


@needs_alex
def test_format_logic_map_renders():
    out = LM.format_logic_map(LM.build_logic_map(ALEX100, field_id=100, fbg_name="fbg_test"))
    assert out.startswith("logic-map: fbg_test")
    assert "entries" in out and "routines" in out
