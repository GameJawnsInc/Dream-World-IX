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


SHORT_FLAG = bytes([0x05, 0xC4, 200, 0x7D, 1, 0, 0x2C, 0x7F])  # set GLOB 200 (C4 short, 1-byte index)


def _glob_idxs(out):
    eb = EbScript.from_bytes(out)
    return [_glob_var_token(out, i.off + 1)[0] for i in eb.instrs(eb.entries[0].funcs[0])
            if i.op == 0x05 and _glob_var_token(out, i.off + 1)]


def test_flag_cross_0xff_short_to_long():
    """A remap that crosses 0xFF (200 C4/1-byte -> 8512 E4/2-byte) is length-CHANGING: rebuilt via the keystone,
    grows by 1 byte, lints clean, and now reads the long-form flag."""
    base = _eb(SHORT_FLAG + RET)
    out = LE.apply_logic_edits(base, [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 200, "new_flag": 8512}])
    assert _glob_idxs(out) == [8512] and len(out) == len(base) + 1
    assert eblint.errors(eblint.lint_eb(out)) == [] and EbScript.from_bytes(out).to_bytes() == out


def test_flag_cross_0xff_long_to_short():
    """The reverse (8512 E4/2-byte -> 100 C4/1-byte) shrinks by 1 byte and lints clean."""
    base = _eb(FLAG + RET)
    out = LE.apply_logic_edits(base, [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 8512, "new_flag": 100}])
    assert _glob_idxs(out) == [100] and len(out) == len(base) - 1
    assert eblint.errors(eblint.lint_eb(out)) == []


def test_flag_cross_0xff_relocates_jump():
    """A JMP spanning the re-widened flag token relocates so it still hits its target after the length change."""
    from ff9mapkit.eb import cmdasm
    body = cmdasm.assemble_block("JMP(d)\n" + cmdasm.disassemble_block(SHORT_FLAG, 0, len(SHORT_FLAG)) + "\nd:\nRET()")
    out = LE.apply_logic_edits(_eb(body), [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 200, "new_flag": 8512}])
    assert eblint.errors(eblint.lint_eb(out)) == []            # eblint validates every jump/switch target
    eb = EbScript.from_bytes(out)
    f = eb.entries[0].funcs[0]
    jmp = next(i for i in eb.instrs(f) if i.op == 0x01)
    ret = [i for i in eb.instrs(f) if i.op == 0x04][-1]
    assert disasm.jump_target(jmp) == ret.off                  # relocated to still land on the RET


def test_flag_same_width_stays_in_place():
    """A same-width remap (8512 -> 8520, both E4) is byte-length-identical (the in-place path, not a rebuild)."""
    base = _eb(FLAG + RET)
    out = LE.apply_logic_edits(base, [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 8512, "new_flag": 8520}])
    assert _glob_idxs(out) == [8520] and len(out) == len(base)


def test_flag_cross_0xff_two_remaps_in_one_function():
    """Two cross-0xFF remaps in ONE function compose: the second's captured offset is adjusted for the first's
    length change (processed ascending-offset), so both land on their intended instructions."""
    short50 = bytes([0x05, 0xC4, 50, 0x7D, 1, 0, 0x2C, 0x7F])   # set GLOB 50 (C4 short)
    long300 = bytes([0x05, 0xE4]) + struct.pack("<H", 300) + bytes([0x7D, 1, 0, 0x2C, 0x7F])  # set GLOB 300 (E4)
    out = LE.apply_logic_edits(_eb(short50 + long300 + RET), [
        {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 50, "new_flag": 8512},   # short->long (+1)
        {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 300, "new_flag": 100}])   # long->short (-1)
    assert _glob_idxs(out) == [8512, 100] and eblint.errors(eblint.lint_eb(out)) == []
    assert EbScript.from_bytes(out).to_bytes() == out


def test_flag_cross_0xff_conflicting_edits_refused_not_corrupted():
    """A conflicting set (an in-place edit drifts the very instruction a cross-0xFF remap targets) fails CLEANLY
    -- the offset+old guard refuses, never silently patches a different instruction (the review's MED finding)."""
    one = bytes([0x05, 0xC4, 200, 0x7D, 1, 0, 0x2C, 0x7F])      # the only GLOB 200 read/write
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(one + RET), [
            {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 200, "new_flag": 77},     # in-place: drifts the site
            {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 200, "new_flag": 8512}])  # cross: site no longer 200


def test_flag_cross_0xff_guard_and_mix():
    """The remap is old-guarded (a wrong old flag isn't found -> refused), and a cross-0xFF remap composes with
    same-pass in-place edits on the same function."""
    with pytest.raises(LE.LogicEditError):                     # no GLOB 999 in the func
        LE.apply_logic_edits(_eb(SHORT_FLAG + RET),
                             [{"kind": "flag_index", "entry": 0, "tag": 0, "flag": 999, "new_flag": 8512}])
    out = LE.apply_logic_edits(_eb(ADDGIL + SHORT_FLAG + RET), [
        {"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 5000},          # in-place
        {"kind": "flag_index", "entry": 0, "tag": 0, "flag": 200, "new_flag": 8512}])        # cross-0xFF rebuild
    assert _read(out, 0xCE, 0) == 5000 and _glob_idxs(out) == [8512]
    assert eblint.errors(eblint.lint_eb(out)) == []


def test_flag_cross_0xff_on_real_fields():
    """On REAL field bytecode: find a GLOB flag read/write and remap it ACROSS the 0xFF boundary -- the rebuilt
    function stays eblint-clean + byte-round-trips (the keystone relocates the real jumps/switch)."""
    try:
        from ff9mapkit.extract import EventBundle
        bundle = EventBundle()
    except Exception:                                                    # noqa: BLE001
        pytest.skip("no game install")
    tested = 0
    for fid in (351, 300, 302, 1054, 70, 250):
        try:
            data = bundle.eb_for_id(fid)
        except Exception:                                               # noqa: BLE001
            continue
        if not data:
            continue
        s = EbScript.from_bytes(data)
        site = None
        for e in s.entries:
            if e.empty:
                continue
            for f in e.funcs:
                for i in s.instrs(f):
                    tok = _glob_var_token(data, i.off + 1) if i.op == 0x05 else None
                    if tok is not None:
                        site = (e.index, f.tag, tok[0]); break
                if site:
                    break
            if site:
                break
        if site is None:
            continue
        ent, tag, old = site
        new = 8512 if old <= 0xFF else 100                              # force a width change either way
        out = LE.apply_logic_edits(data, [{"kind": "flag_index", "entry": ent, "tag": tag,
                                           "flag": old, "new_flag": new, "nth": 0}])
        assert eblint.errors(eblint.lint_eb(out)) == [], f"field {fid}"
        assert EbScript.from_bytes(out).to_bytes() == out and len(out) != len(data), f"field {fid}"
        tested += 1
    if not tested:
        pytest.skip("no sample field had a GLOB flag token")


def test_txid_non_window_op_refused():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(FIELD + RET), [{"kind": "txid", "entry": 0, "tag": 0, "op": 0x2B, "old": 300, "new": 1}])


def test_unknown_kind_refused():
    with pytest.raises(LE.LogicEditError):
        LE.apply_logic_edits(_eb(RET), [{"kind": "frobnicate", "entry": 0, "tag": 0}])


def test_malformed_edit_container_is_clean_error():
    """`[logic_edit]` (a single table) / a non-dict element -> a clean LogicEditError, not a raw AttributeError."""
    eb = _eb(ADDGIL + RET)
    for bad in ("foo", [1], {"kind": "gil", "entry": 0, "tag": 0, "op": 0xCE, "old": 100, "new": 1}):
        with pytest.raises(LE.LogicEditError):
            LE.apply_logic_edits(eb, bad)


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


# ============================================================================================
# Phase 2b: editable_effects -- the GUI authoring surface (discover edit-sites, synth + merge edits)
# ============================================================================================
ADDITEM236 = bytes([0x48, 0, 236, 0, 1])               # AddItem(id=236, count=1)
SETTEXTVAR236 = bytes([0x66, 0, 0, 236, 0])            # SetTextVariable(slot=0, value=236) -- display id
WIN0 = bytes([0x1F, 0, 0, 0, 0, 0])                    # WindowSync(_, _, txid=0)


def _site(sites, group, old=None):
    return next(s for s in sites if s.group == group and (old is None or s.old == old))


def test_editable_effects_item_pairs_give_and_display():
    """An item reward surfaces ONE site whose synth retargets the AddItem give AND the matched
    SetTextVariable 'Received <item>!' display together (the give-vs-display lesson)."""
    eb = _eb(ADDITEM236 + SETTEXTVAR236 + RET)
    sites = LE.editable_effects(eb, 0, 0)
    s = _site(sites, "item")
    assert s.old == 236 and len(s.templates) == 1 and len(s.display_templates) == 1
    out = LE.apply_logic_edits(eb, LE.synth_edits(s, 239))
    eb2 = EbScript.from_bytes(out)
    ins = list(eb2.instrs(eb2.entries[0].funcs[0]))
    assert [i.imm(0) for i in ins if i.op == 0x48] == [239]      # give retargeted
    assert [i.imm(1) for i in ins if i.op == 0x66] == [239]      # display retargeted too
    assert len(out) == len(eb) and eblint.errors(eblint.lint_eb(out)) == []


def test_editable_effects_item_multi_occurrence_uses_nth():
    """Two gives + two displays of the same id -> the synth emits per-nth edits that retarget all four."""
    eb = _eb(ADDITEM236 + ADDITEM236 + SETTEXTVAR236 + SETTEXTVAR236 + RET)
    s = _site(LE.editable_effects(eb, 0, 0), "item")
    assert len(s.templates) == 2 and len(s.display_templates) == 2
    assert [t.get("nth") for t in s.templates] == [0, 1]
    out = LE.apply_logic_edits(eb, LE.synth_edits(s, 239))
    eb2 = EbScript.from_bytes(out)
    ins = list(eb2.instrs(eb2.entries[0].funcs[0]))
    assert [i.imm(0) for i in ins if i.op == 0x48] == [239, 239]
    assert [i.imm(1) for i in ins if i.op == 0x66] == [239, 239]


def test_item_display_kind_pins_text_slot():
    """The item-display edit targets ONLY SetTextVariable in text slot 0 (FF9's item-get display) -- a
    same-value SetTextVariable in another slot (a preview row) must NOT be corrupted."""
    eb = _eb(bytes([0x66, 0, 0, 236, 0]) + bytes([0x66, 0, 1, 236, 0]) + RET)   # STV(slot0,236), STV(slot1,236)
    out = LE.apply_logic_edits(eb, [{"kind": "item_display", "entry": 0, "tag": 0, "op": 0x66,
                                     "operand": 1, "slot": 0, "old": 236, "new": 239}])
    eb2 = EbScript.from_bytes(out)
    assert [(i.imm(0), i.imm(1)) for i in eb2.instrs(eb2.entries[0].funcs[0]) if i.op == 0x66] == [(0, 239), (1, 236)]


def test_editable_effects_item_display_pairing_is_slot_aware():
    """Discovery pairs an AddItem only with the SAME-id SetTextVariable in slot 0; a slot-1 same-value STV is
    left out of the site (so retargeting the item never rewrites the unrelated preview)."""
    eb = _eb(ADDITEM236 + bytes([0x66, 0, 0, 236, 0]) + bytes([0x66, 0, 1, 236, 0]) + RET)
    s = _site(LE.editable_effects(eb, 0, 0), "item")
    assert len(s.display_templates) == 1 and s.display_templates[0]["kind"] == "item_display"
    out = LE.apply_logic_edits(eb, LE.synth_edits(s, 239))
    eb2 = EbScript.from_bytes(out)
    assert [(i.imm(0), i.imm(1)) for i in eb2.instrs(eb2.entries[0].funcs[0]) if i.op == 0x66] == [(0, 239), (1, 236)]


def test_item_count_kind_pins_item_id():
    """The item-quantity edit targets ONLY the AddItem of the named item id -- a same-count AddItem of a
    DIFFERENT item must keep its count."""
    eb = _eb(bytes([0x48, 0, 236, 0, 1]) + bytes([0x48, 0, 240, 0, 1]) + RET)   # AddItem(236,1), AddItem(240,1)
    out = LE.apply_logic_edits(eb, [{"kind": "item_count", "entry": 0, "tag": 0, "op": 0x48,
                                     "operand": 1, "item_id": 236, "old": 1, "new": 5}])
    eb2 = EbScript.from_bytes(out)
    assert [(i.imm(0), i.imm(1)) for i in eb2.instrs(eb2.entries[0].funcs[0]) if i.op == 0x48] == [(236, 5), (240, 1)]


def test_editable_effects_item_count_discovery_and_synth():
    """An item site exposes the quantity (uniform AddItem count); synth_item_edits can change the id, the
    count, or both -- a count-only change emits no give/display edit."""
    eb = _eb(ADDITEM236 + bytes([0x66, 0, 0, 236, 0]) + RET)        # AddItem(236,1) + display
    s = _site(LE.editable_effects(eb, 0, 0), "item")
    assert s.count_old == 1 and len(s.count_templates) == 1 and "×1" in s.label
    out = LE.apply_logic_edits(eb, LE.synth_item_edits(s, 236, 3))  # same item, quantity 1 -> 3
    eb2 = EbScript.from_bytes(out)
    assert [(i.imm(0), i.imm(1)) for i in eb2.instrs(eb2.entries[0].funcs[0]) if i.op == 0x48] == [(236, 3)]
    both = LE.apply_logic_edits(eb, LE.synth_item_edits(s, 240, 2))  # new item AND quantity
    eb3 = EbScript.from_bytes(both)
    assert [(i.imm(0), i.imm(1)) for i in eb3.instrs(eb3.entries[0].funcs[0]) if i.op == 0x48] == [(240, 2)]
    assert [i.imm(1) for i in eb3.instrs(eb3.entries[0].funcs[0]) if i.op == 0x66] == [240]   # display tracks id


def test_synth_item_edits_skips_unchanged_components():
    s = _site(LE.editable_effects(_eb(ADDITEM236 + bytes([0x66, 0, 0, 236, 0]) + RET), 0, 0), "item")
    assert LE.synth_item_edits(s, 236, 1) == []                     # no change at all -> no edits
    assert all(e["kind"] == "item_count" for e in LE.synth_item_edits(s, 236, 4))   # count only
    assert all(e["kind"] in ("item", "item_display") for e in LE.synth_item_edits(s, 250, 1))  # id only


def test_editable_effects_item_varying_count_not_editable():
    """When the give-paths grant DIFFERENT counts, the quantity isn't surfaced as editable (noted)."""
    eb = _eb(bytes([0x48, 0, 236, 0, 1]) + bytes([0x48, 0, 236, 0, 3]) + RET)   # AddItem(236,1) and (236,3)
    s = _site(LE.editable_effects(eb, 0, 0), "item")
    assert s.count_old is None and not s.count_templates and "varies" in s.note


def test_compose_verbatim_eb_retarget_makes_field_edit_match_build(tmp_path):
    """build.compose_verbatim_eb returns the donor with [verbatim_eb] retarget applied (the SAME bytes the
    build edits), so a field-warp site discovered on it carries the POST-retarget `old` -- the GUI dry-run and
    the build can't diverge on a retargeted exit (the review's HIGH 'wrong bytes' bug)."""
    from ff9mapkit import build
    (tmp_path / "f.eb.bin").write_bytes(_eb(FIELD + RET))                 # donor Field(300)
    (tmp_path / "f.field.toml").write_text(
        '[field]\nid = 6300\nname = "F"\narea = 11\n\n[verbatim_eb]\nbin = "f.eb.bin"\n'
        'retarget = { 300 = 6300 }\n', encoding="utf-8")
    proj = build.FieldProject.load(tmp_path / "f.field.toml")
    eb, _suffix = build.compose_verbatim_eb(proj)
    e = EbScript.from_bytes(eb)
    assert [i.imm(0) for i in e.instrs(e.entries[0].funcs[0]) if i.op == 0x2B] == [6300]   # retargeted pre-edit
    site = next(s for s in LE.editable_effects(eb, 0, 0) if s.group == "field")
    assert site.old == 6300                                               # discovery sees the build's value
    out = LE.apply_logic_edits(eb, LE.synth_edits(site, 7000))            # the GUI-authored edit applies cleanly
    assert eblint.errors(eblint.lint_eb(out)) == []


def test_editable_effects_item_without_display_notes_it():
    """A give with NO matching display still authors the give, with an advisory note."""
    s = _site(LE.editable_effects(_eb(ADDITEM236 + RET), 0, 0), "item")
    assert not s.display_templates and "only the give" in s.note
    out = LE.apply_logic_edits(_eb(ADDITEM236 + RET), LE.synth_edits(s, 233))
    assert _read(out, 0x48, 0) == 233


def test_editable_effects_skips_inert_and_no_item_grants():
    """The engine no-op AddItem ids (NO_ITEM 255 / id%1000>=612) are not editable sites (parity with the
    read-only map, which hides them)."""
    eb = _eb(bytes([0x48, 0, 255, 0, 1]) + bytes([0x48, 0, 0xBC, 0x02, 1]) + RET)   # AddItem(255), AddItem(700)
    assert not [s for s in LE.editable_effects(eb, 0, 0) if s.group == "item"]


def test_editable_effects_skips_gil_sentinel():
    """A > party-cap AddGil (a scripted/computed sentinel, e.g. the generic treasure handler's gil branch) is
    not surfaced as an editable reward."""
    sentinel = bytes([0xCE, 0]) + (16000000).to_bytes(3, "little")   # AddGil(16000000) -- > 9,999,999 cap
    assert not [s for s in LE.editable_effects(_eb(sentinel + RET), 0, 0) if s.group == "gil"]


def test_editable_effects_gil_field_flag_round_trip():
    sg = _site(LE.editable_effects(_eb(ADDGIL + RET), 0, 0), "gil")
    assert _read(LE.apply_logic_edits(_eb(ADDGIL + RET), LE.synth_edits(sg, 5000)), 0xCE, 0) == 5000
    sf = _site(LE.editable_effects(_eb(FIELD + RET), 0, 0), "field")
    assert _read(LE.apply_logic_edits(_eb(FIELD + RET), LE.synth_edits(sf, 6300)), 0x2B, 0) == 6300
    sx = _site(LE.editable_effects(_eb(FLAG + RET), 0, 0), "flag")
    assert sx.new_key == "new_flag"
    out = LE.apply_logic_edits(_eb(FLAG + RET), LE.synth_edits(sx, 8520))
    eb = EbScript.from_bytes(out)
    assert [_glob_var_token(out, i.off + 1)[0] for i in eb.instrs(eb.entries[0].funcs[0])
            if i.op == 0x05 and _glob_var_token(out, i.off + 1)] == [8520]


def test_editable_effects_text_per_language_guards():
    """A dialogue line surfaces a per-language text site -- each template guarded by THAT language's own
    current string, so one new string writes consistently across langs that differ."""
    from ff9mapkit.dialogue import parse_mes
    us = "[STRT=10,1]Hello world[ENDN][STRT=8,2][TAIL=DWN]Second line[ENDN]"
    fr = "[STRT=10,1]Bonjour[ENDN][STRT=8,2][TAIL=DWN]Second line[ENDN]"
    sites = LE.editable_effects(_eb(WIN0 + RET), 0, 0, entries=parse_mes(us),
                                lang_bodies={"us": us, "fr": fr})
    s = _site(sites, "text")
    assert s.old == "Hello world"
    olds = {t["lang"]: t["old"] for t in s.templates}
    assert olds == {"us": "Hello world", "fr": "Bonjour"}        # each lang guarded by its own line
    edits = LE.synth_edits(s, "Hi there")
    assert "Hi there" in LE.apply_logic_text_edits(us, edits, "us")
    assert "Hi there" in LE.apply_logic_text_edits(fr, edits, "fr")


def test_editable_effects_text_reindexed_body_skipped():
    """A [TXID=]-reindexed .mes (Phase 4) is not offered as an editable text site (no template -> no row)."""
    from ff9mapkit.dialogue import parse_mes
    us = "[STRT=10,1]Hello world[ENDN]"
    sites = LE.editable_effects(_eb(WIN0 + RET), 0, 0, entries=parse_mes(us),
                                lang_bodies={"us": "[TXID=0][STRT=10,1]Hello world[ENDN]"})
    assert not [s for s in sites if s.group == "text"]


def test_synth_then_upsert_replaces_not_stacks():
    """Re-editing the same site replaces its edits (matched by coords), so the list never accumulates
    stale layers; site_footprint drops the give AND display together."""
    s = _site(LE.editable_effects(_eb(ADDITEM236 + SETTEXTVAR236 + RET), 0, 0), "item")
    lst = LE.upsert_edits([], LE.synth_edits(s, 239), drop=LE.site_footprint(s))
    assert len(lst) == 2
    lst2 = LE.upsert_edits(lst, LE.synth_edits(s, 241), drop=LE.site_footprint(s))
    assert len(lst2) == 2 and {e["new"] for e in lst2} == {241}    # replaced, not stacked
    cleared = LE.upsert_edits(lst2, [], drop=LE.site_footprint(s))
    assert cleared == []                                           # clearing a site removes all its edits


def test_editable_effects_out_of_range_and_empty():
    assert LE.editable_effects(_eb(RET), 9, 0) == []               # no such entry
    assert LE.editable_effects(_eb(RET), 0, 7) == []               # no such tag
    assert LE.editable_effects(_eb(RET), 0, 0) == []               # a routine with no editable values
