"""Phase-2: in-place value edits on a verbatim fork's .eb / .mes (logic_edit.py).

Pure synthetic tests (hand-built minimal .eb / .mes, no install) prove each edit kind round-trips a value
LENGTH-PRESERVING, the old-guards REFUSE on drift/overflow/ambiguity, the composed .eb stays structurally
clean (eblint), and a no-op edit list is byte-identical. The .mes text rewrite is a verified in-place splice.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import eblint
from ff9mapkit import logic_edit as LE
from ff9mapkit.eb import disasm
from ff9mapkit.eb.model import EbScript
from ff9mapkit.eventscan import _glob_var_token


def _eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as Main_Init's bytecode."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)
    return bytes(head) + slot + funcbody


def _read(out: bytes, op: int, operand: int):
    """The first ``op`` instruction's operand ``operand`` in entry 0 / tag 0 of ``out``."""
    eb = EbScript.from_bytes(out)
    for ins in eb.instrs(eb.entries[0].funcs[0]):
        if ins.op == op:
            return ins.imm(operand)
    return None


ADDITEM = bytes([0x48, 0, 232, 0, 1])              # AddItem(id=232, count=1)
ADDGIL = bytes([0xCE, 0, 100, 0, 0])               # AddGil(100)
FIELD = bytes([0x2B, 0, 0x2C, 0x01])               # Field(300)
WINDOW = bytes([0x1F, 0, 0, 0, 100, 0])            # WindowSync(_, _, txid=100)
FLAG = bytes([0x05, 0xE4]) + struct.pack("<H", 8512) + bytes([0x7D, 1, 0, 0x2C, 0x7F])  # set GLOB 8512
RET = bytes([0x04])


# ---- each .eb kind round-trips a value, length-preserving ----
def test_item_id_and_count():
    out = LE.apply_logic_edits(_eb(ADDITEM + RET),
                               [{"kind": "item", "entry": 0, "tag": 0, "op": 0x48, "operand": "id", "old": 232, "new": 233}])
    assert _read(out, 0x48, 0) == 233 and len(out) == len(_eb(ADDITEM + RET))
    out2 = LE.apply_logic_edits(_eb(ADDITEM + RET),
                                [{"kind": "item", "entry": 0, "tag": 0, "op": 0x48, "operand": "count", "old": 1, "new": 5}])
    assert _read(out2, 0x48, 1) == 5


def test_gil_and_field_and_txid():
    out = LE.apply_logic_edits(_eb(ADDGIL + RET), [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 5000}])
    assert _read(out, 0xCE, 0) == 5000
    out = LE.apply_logic_edits(_eb(FIELD + RET), [{"kind": "field", "entry": 0, "tag": 0, "op": 0x2B, "old": 300, "new": 6300}])
    assert _read(out, 0x2B, 0) == 6300
    out = LE.apply_logic_edits(_eb(WINDOW + RET), [{"kind": "txid", "entry": 0, "tag": 0, "op": 0x1F, "old": 100, "new": 222}])
    assert _read(out, 0x1F, 2) == 222


def test_generic_operand_kind_patches_any_literal():
    """The generic `operand` kind patches any literal operand -- e.g. SetTextVariable (0x66)'s display item id
    (the 'Received <item>!' message var), the DISPLAY half of a chest reward, separate from the AddItem give."""
    eb = _eb(bytes([0x66, 0, 0, 0xEC, 0x00, 0x04]))          # SetTextVariable(0, 236); RET  (236=0xEC, 2-byte op1)
    out = LE.apply_logic_edits(eb, [{"kind": "operand", "entry": 0, "tag": 0, "op": 0x66,
                                     "operand": 1, "old": 236, "new": 239}])
    eb2 = EbScript.from_bytes(out)
    assert [i.imm(1) for i in eb2.instrs(eb2.entries[0].funcs[0]) if i.op == 0x66] == [239]
    assert len(out) == len(eb)


def test_flag_index_same_width_class():
    out = LE.apply_logic_edits(_eb(FLAG + RET), [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 8512, "new_flag": 8520}])
    eb = EbScript.from_bytes(out)
    flags = [_glob_var_token(out, i.off + 1)[0] for i in eb.instrs(eb.entries[0].funcs[0])
             if i.op == 0x05 and _glob_var_token(out, i.off + 1)]
    assert flags == [8520] and len(out) == len(_eb(FLAG + RET))


def test_composed_edit_passes_eblint():
    out = LE.apply_logic_edits(_eb(ADDITEM + ADDGIL + FIELD + FLAG + RET), [
        {"kind": "item", "entry": 0, "tag": 0, "op": 0x48, "operand": "id", "old": 232, "new": 233},
        {"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 5000},
        {"kind": "field", "entry": 0, "tag": 0, "op": 0x2B, "old": 300, "new": 6300},
        {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 8512, "new_flag": 8520}])
    assert eblint.errors(eblint.lint_eb(out)) == []


def test_empty_and_text_only_are_byte_identical():
    eb = _eb(ADDGIL + RET)
    assert LE.apply_logic_edits(eb, []) == eb
    assert LE.apply_logic_edits(eb, [{"kind": "text", "txid": 0, "old": "a", "new": "b"}]) == eb   # text isn't an .eb edit


# ---- guards: refuse on drift / overflow / bad address / ambiguity ----
def test_guard_old_mismatch_refuses():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(ADDGIL + RET), [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 999, "new": 1}])


def test_guard_overflow_refuses():
    with pytest.raises(LE.LogicEditError):                     # count is a 1-byte operand
        LE.apply_logic_edits(_eb(ADDITEM + RET),
                             [{"kind": "item", "entry": 0, "tag": 0, "op": 0x48, "operand": "count", "old": 1, "new": 9999}])


def test_guard_missing_entry_or_tag_refuses():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(ADDGIL + RET), [{"kind": "gil", "entry": 9, "tag": 0, "op": 0xCE, "old": 100, "new": 1}])
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(ADDGIL + RET), [{"kind": "gil", "entry": 0, "tag": 7, "op": 0xCE, "old": 100, "new": 1}])


def test_ambiguous_requires_nth_then_disambiguates():
    two = _eb(ADDGIL + ADDGIL + RET)                          # two AddGil(100) in one func
    with pytest.raises(LE.LogicEditError):                    # ambiguous without nth
        LE.apply_logic_edits(two, [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 1}])
    out = LE.apply_logic_edits(two, [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 7, "nth": 1}])
    eb = EbScript.from_bytes(out)
    gils = [i.imm(0) for i in eb.instrs(eb.entries[0].funcs[0]) if i.op == 0xCE]
    assert gils == [100, 7]                                   # only the 2nd changed


def test_flag_cross_0xff_boundary_refused():
    with pytest.raises(LE.LogicEditError):                    # 8512 (E4/2-byte) -> 200 (C4/1-byte) = length change
        LE.apply_logic_edits(_eb(FLAG + RET), [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 8512, "new_flag": 200}])


def test_txid_non_window_op_refused():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(FIELD + RET), [{"kind": "txid", "entry": 0, "tag": 0, "op": 0x2B, "old": 300, "new": 1}])


def test_unknown_kind_refused():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(RET), [{"kind": "frobnicate", "entry": 0, "tag": 0}])


def test_non_int_fields_raise_clean_logic_edit_error():
    """A TOML float/str/bool where an int is required (a hand-authoring slip) is a clean LogicEditError, not a
    raw TypeError/AttributeError traceback."""
    eb = _eb(ADDGIL + RET)
    for bad in ({"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 5000.0},   # float new
                {"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": "5000"},    # str new
                {"kind": "gil", "entry": "0", "tag": 0, "op": 0xCE, "old": 100, "new": 1}):       # str entry
        with pytest.raises(LE.LogicEditError):
            LE.apply_logic_edits(eb, [bad])
    with pytest.raises(LE.LogicEditError):                    # str nth (reached only when >1 match)
        LE.apply_logic_edits(_eb(ADDGIL + ADDGIL + RET),
                             [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 1, "nth": "z"}])


def test_text_old_new_must_be_strings():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_text_edits(_BODY, [{"kind": "text", "txid": 0, "old": 123, "new": "x"}], "us")


def test_validate_flags_logic_edit_on_synthesized_field():
    """[[logic_edit]] on a non-verbatim field is surfaced as a problem (offline, via validate) -- not silently
    dropped at build."""
    from ff9mapkit import build

    class _P:                                                 # a synthesized project (no [verbatim_eb])
        raw = {"logic_edit": [{"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 1, "new": 2}]}

        def logic_edits(self):
            return self.raw.get("logic_edit", [])

    problems = []
    build._validate_logic_edits(_P(), problems)
    assert any("only applies to a VERBATIM" in p for p in problems)
    no_edits = type("Q", (), {"raw": {}, "logic_edits": lambda self: []})()
    p2 = []
    build._validate_logic_edits(no_edits, p2)
    assert p2 == []


# ---- .mes dialogue-string rewrite (verified in-place splice) ----
_BODY = "[STRT=10,1]Hello world[ENDN][STRT=8,2][TAIL=DWN]Second line[ENDN]"


def test_text_rewrite_preserves_other_entries_and_geometry():
    out = LE.apply_logic_text_edits(_BODY, [{"kind": "text", "txid": 0, "old": "Hello world", "new": "Hi there"}], "us")
    assert out == "[STRT=10,1]Hi there[ENDN][STRT=8,2][TAIL=DWN]Second line[ENDN]"
    # editing the 2nd entry preserves its [TAIL] geometry
    out2 = LE.apply_logic_text_edits(_BODY, [{"kind": "text", "txid": 1, "old": "Second line", "new": "New 2nd"}], "us")
    assert out2 == "[STRT=10,1]Hello world[ENDN][STRT=8,2][TAIL=DWN]New 2nd[ENDN]"


def test_text_old_mismatch_and_missing_txid_refuse():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_text_edits(_BODY, [{"kind": "text", "txid": 0, "old": "WRONG", "new": "x"}], "us")
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_text_edits(_BODY, [{"kind": "text", "txid": 9, "old": "x", "new": "y"}], "us")


def test_text_reindexed_body_refused():
    with pytest.raises(LE.LogicEditError):                    # [TXID=] re-indexed bodies are Phase 2b
        LE.apply_logic_text_edits("[TXID=5][STRT=10,1]Hi[ENDN]", [{"kind": "text", "txid": 5, "old": "Hi", "new": "Yo"}], "us")


def test_text_lang_filter():
    edits = [{"kind": "text", "txid": 0, "old": "Hello world", "new": "X", "lang": "fr"}]
    assert LE.apply_logic_text_edits(_BODY, edits, "us") == _BODY            # lang mismatch -> no-op
    assert "X" in LE.apply_logic_text_edits(_BODY, edits, "fr")             # lang match -> applied


# ---- real game bytecode: the applier on an actual field .eb (install-gated) ----
def test_apply_on_real_field_eb():
    """A field-retarget edit on a real field's .eb is length-preserving, lands on the right Field(), and the
    result stays structurally clean (eblint) -- proves the applier on actual game bytecode, not just synthetic."""
    try:
        from ff9mapkit.extract import EventBundle
        data = EventBundle().eb_for_id(2803)                  # Daguerreo 2F (has Field()/AddItem/flags)
    except Exception:                                         # noqa: BLE001
        pytest.skip("no game install")
    if not data:
        pytest.skip("field 2803 not in this install")
    eb = EbScript.from_bytes(data)
    site = next(((e.index, f.tag, ins.imm(0))
                 for e in eb.entries if not e.empty for f in e.funcs
                 for ins in eb.instrs(f) if ins.op == 0x2B and ins.imm(0) is not None), None)
    assert site, "expected a literal Field() in field 2803"
    ent, tag, dest = site
    out = LE.apply_logic_edits(data, [{"kind": "field", "entry": ent, "tag": tag, "op": 0x2B,
                                       "old": dest, "new": 6300, "nth": 0}])
    assert len(out) == len(data) and eblint.errors(eblint.lint_eb(out)) == []
    eb2 = EbScript.from_bytes(out)
    dests = [i.imm(0) for i in eb2.instrs(eb2.entry(ent).func_by_tag(tag)) if i.op == 0x2B]
    assert 6300 in dests
