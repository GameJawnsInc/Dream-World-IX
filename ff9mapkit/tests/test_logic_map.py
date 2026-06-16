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
from ff9mapkit.eb.model import EbScript
from ff9mapkit.eb.disasm import Instr, decode_switch, SWITCH_OPS

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


# ---- Phase 1: the switch-table (0x06/0x0B/0x0D) case->target decoder (disasm.decode_switch) ----
def _instr(off, op, args):
    return Instr(off=off, op=op, args=list(args), arg_is_expr=[False] * len(args), length=0)


def test_decode_switch_0b_contiguous():
    """JMP_SWITCH (0x0B): base + n contiguous case reloffsets + a default; anchor = off+1. Real field-50 example."""
    sw = decode_switch(_instr(3933, 0x0B, [10, 1502, 11, 94, 1440]))
    assert sw.base == 10
    assert [(e.value, e.target, e.is_default) for e in sw.edges] == \
        [(10, 3945, False), (11, 4028, False), (12, 5374, False), (None, 5436, True)]


def test_decode_switch_06_explicit():
    """JMP_SWITCHEX (0x06): explicit (value, reloffset) pairs + a leading default; anchor = off+4. Real field-51."""
    sw = decode_switch(_instr(581, 0x06, [88, 104, 8, 3, 68]))
    assert sw.base is None
    assert [(e.value, e.target, e.is_default) for e in sw.edges] == [(104, 593, False), (3, 653, False), (None, 673, True)]


def test_decode_switch_base_sign_extends_high_byte():
    """The contiguous-form base sign-extends its HIGH byte only (engine (SByte) cast): 0xFFFE -> selector -2."""
    sw = decode_switch(_instr(0, 0x0B, [0xFFFE, 0, 0]))
    assert sw.base == -2 and sw.edges[0].value == -2


def test_decode_switch_0d_anchor_off_plus_2():
    """0x0D is JMP_SWITCH with a 2-byte count -> same body, anchor off+2 (none ship; by-construction)."""
    sw = decode_switch(_instr(0, 0x0D, [0, 4, 8]))
    assert sw.base == 0 and sw.edges[0].target == 10 and sw.edges[-1].target == 6   # off+2 + {8 (case), 4 (default)}


def test_decode_switch_default_only_no_cases():
    """A degenerate switch with n==0 (only the default arm) decodes to a single default edge, no cases, no crash."""
    s06 = decode_switch(_instr(0, 0x06, [5]))                 # ac = 1 + 2*0
    assert s06.base is None and [(e.value, e.target, e.is_default) for e in s06.edges] == [(None, 9, True)]
    s0b = decode_switch(_instr(0, 0x0B, [3, 7]))              # ac = 2 + 0  (base=3, default reloff=7)
    assert s0b.base == 3 and [(e.value, e.target, e.is_default) for e in s0b.edges] == [(None, 8, True)]


def test_decode_switch_rejects_non_switch_and_malformed():
    assert decode_switch(_instr(0, 0x2B, [100])) is None                                  # not a switch op
    assert decode_switch(Instr(0, 0x0B, ["{expr}", 0, 0], [True, False, False], 0)) is None   # expr operand
    assert decode_switch(_instr(0, 0x0B, [5])) is None                                    # too short for base+default


def test_build_logic_map_decodes_switch_into_branches():
    """build_logic_map surfaces a switch as a node.branches entry -- not silently skipped, not unresolved."""
    eb = _eb(bytes([0x0B, 0x01, 0x00, 0x00, 0x04, 0x00, 0x08, 0x00, 0x04]))   # JMP_SWITCH base=0 default=4 case0=8
    lm = LM.build_logic_map(eb)
    br = [b for n in lm.nodes for b in n.branches]
    assert len(br) == 1 and br[0]["base"] == 0
    edges = br[0]["edges"]
    assert sum(1 for e in edges if not e["is_default"]) == 1 and any(e["is_default"] for e in edges)
    assert not any(u["reason"].startswith("switch") for n in lm.nodes for u in n.unresolved)   # decoded, not bailed


@needs_alex
def test_switch_soundness_sweep_real_fields():
    """Every case+default target of every switch in a sample of switch-heavy real fields lands on a decoded-
    instruction boundary inside its function -- the ailint-style soundness proof (the full 5563-switch / 676-
    field sweep runs out-of-band; this samples a few fields so it stays fast + non-vacuous)."""
    try:
        from ff9mapkit.extract import EventBundle
        bundle = EventBundle()
    except Exception:                                   # noqa: BLE001 -- no install/UnityPy -> skip the sweep
        pytest.skip("no game install for the switch sweep")
    total = 0
    for fid in (50, 51, 100, 300, 2803):
        data = bundle.eb_for_id(fid)
        if not data:
            continue
        eb = EbScript.from_bytes(data)
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                valid = {i.off for i in eb.instrs(f)} | {f.abs_end}
                for ins in eb.instrs(f):
                    if ins.op in SWITCH_OPS:
                        sw = decode_switch(ins)
                        total += 1
                        assert sw is not None
                        for ed in sw.edges:
                            assert f.abs_start <= ed.target <= f.abs_end and ed.target in valid, \
                                (fid, ins.off, ed.target)
    assert total > 0, "the sample must actually contain switches (else the sweep is vacuous)"


def test_node_summary_and_hint():
    """node_summary = a terse one-liner from the per-routine attribution; node_hint = a single-category,
    high-confidence tree suffix (EMPTY for a mixed routine, so the tree label can't mislead)."""
    N, Call = LM.Node, LM.Call
    # a MIXED routine (calls + 2 flag writes + a flag read): the summary lists all; the hint is empty
    mixed = N(0, 20, "shared_routine", 0, 0,
              calls=[Call("RunScript", 9, 29, "main", [0], 100)],
              flags_set=[{"index": 3461, "mode": "set"}, {"index": 3458, "mode": "set"}],
              flags_read=[{"index": 8512, "require_set": True}])
    s = LM.node_summary(mixed)
    assert "runs tag 29" in s and "sets 2 flags" in s and "reads flag 8512" in s
    assert LM.node_hint(mixed) == ""                       # 2+ categories -> no (misleading) hint
    # SINGLE-category routines -> a terse, honest hint
    assert LM.node_hint(N(0, 1, "shared_routine", 0, 0,
                          calls=[Call("RunScript", 9, 29, "main", [0], 0)])) == " → tag 29"
    assert LM.node_hint(N(0, 2, "shared_routine", 0, 0, warps=[{"op": "Field", "to": 300}])) == " → warp"
    says1 = N(0, 3, "shared_routine", 0, 0, says=[{"txid": 5, "text": "Hi"}])
    assert LM.node_hint(says1) == " · dialogue" and LM.node_summary(says1) == "says 1 line"
    rew = N(0, 5, "shared_routine", 0, 0, gives=[{"kind": "item", "id": 1, "count": 1, "label": "Potion"}])
    assert LM.node_summary(rew) == "gives 1 reward" and LM.node_hint(rew) == " · reward"
    # an EMPTY routine -> empty summary + no hint
    empty = N(0, 4, "shared_routine", 0, 0)
    assert LM.node_summary(empty) == "" and LM.node_hint(empty) == ""


def test_node_report():
    """node_report renders a FRIENDLY transcript: dialogue text, flag reads as run-conditions, warps named,
    switch arms by CASE VALUE (not raw offsets), and capitalized call labels."""
    N, Call = LM.Node, LM.Call
    n = N(0, 0, "main_init", 0, 0,
          says=[{"txid": 5, "text": "Welcome!"}],
          gives=[{"kind": "item", "id": 1, "count": 2, "label": "Potion"}, {"kind": "save_menu"}],
          flags_read=[{"index": 8512, "require_set": True}],
          flags_set=[{"index": 3461, "mode": "set"}, {"index": 3458, "mode": "or"}],
          warps=[{"op": "Field", "to": 300}],
          calls=[Call("RunScript", 9, 29, "main", [0], 100,
                      label="runs shared field logic (Main_Init routine #29)")],
          branches=[{"op": 0x0B, "base": 0, "edges": [{"value": 1900, "target": 10, "is_default": False},
                                                       {"value": 2005, "target": 20, "is_default": False},
                                                       {"value": None, "target": 30, "is_default": True}]}])
    r = LM.node_report(n)
    assert 'Says: "Welcome!"' in r
    assert "Gives the player Potion ×2" in r and "Opens the save-point menu" in r
    assert "Runs only if story flag 8512 is SET" in r
    assert "Sets story flag 3461" in r and "Sets (OR into) story flag 3458" in r
    assert "Warps to field 300" in r
    assert any(line.startswith("Runs shared field logic") and "entry 0" in line for line in r)
    assert "Branches on a value → cases 1900, 2005 (else a default path)" in r
    assert LM.node_report(N(0, 1, "shared_routine", 0, 0)) == []      # empty routine -> empty report
