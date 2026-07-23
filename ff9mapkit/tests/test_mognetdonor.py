"""The Mognet DONOR-FORK lane: patching a REAL moogle field in place (content/mognetdonor.py) + the
jump-table-aware ``edit.insert_in_function`` that enables it.

Two tiers: OFFLINE tests hand-assemble a minimal 0x06 switch (wire format learned from field 1865:
``06 <npairs:u8> <default:u16> (<val:u16> <rel:u16>)*``, anchor = op+4) and pin the fixup math;
INSTALL-GATED tests run the real thing against field 1865 (Kupo, Alexandria Steeple) -- they skip
cleanly without a game install (the suite convention).
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import data as _data, eblint
from ff9mapkit.eb import EbScript, edit, opcodes
from ff9mapkit.eb.disasm import decode_switch, iter_code, read_code
from ff9mapkit.content import mognet as _mognet
from ff9mapkit.content import mognetdonor as md
from ff9mapkit.content.ladder import find_player_entry

CLEAN = _data.blank_field_bytes("us")


def _switch06(default_rel: int, pairs) -> bytes:
    """Hand-assemble an 0x06 switch: op, pair count, default reloffset, (value, reloffset) pairs."""
    out = bytes([0x06, len(pairs)]) + struct.pack("<H", default_rel)
    for v, r in pairs:
        out += struct.pack("<HH", v, r)
    return out


# --- the enabling primitive: mid-function insert THROUGH a jump table ----------------------
def _switch_func_body():
    """selector + switch(2 arms + default) + two 6-byte arms (Wait(k); JMP conv) + convergence.

    layout (rel):  0 selector(4B)  4 switch(12B: 2 pairs)  16 arm A  22 arm B  28 conv Wait(9) RETURN
    anchor = 4+4 = 8; arm A rel 16 -> off 8; arm B rel 22 -> off 14; default -> conv rel 28 -> off 20."""
    selector = bytes([0x05, 0xD5, md.VARIANT_BYTE, 0x7F])
    sw = _switch06(20, [(1, 8), (2, 14)])
    arm_a = opcodes.wait(1) + bytes([0x01]) + struct.pack("<h", 28 - (16 + 3 + 3))   # jmp -> conv
    arm_b = opcodes.wait(2) + bytes([0x01]) + struct.pack("<h", 28 - (22 + 3 + 3))
    conv = opcodes.wait(9) + opcodes.RETURN
    return selector + sw + arm_a + arm_b + conv


def _resolved_edges(blob, entry, tag):
    s = EbScript.from_bytes(blob)
    f = s.entry(entry).func_by_tag(tag)
    out = []
    for ins in s.instrs(f):
        if ins.op == 0x06:
            for e in decode_switch(ins).edges:
                t, _ = read_code(blob, e.target)
                out.append((e.value, t.op, tuple(t.args)))
    return out


def test_insert_through_a_jump_table_fixes_crossing_targets():
    body = _switch_func_body()
    eb = edit.add_function(CLEAN, find_player_entry(EbScript.from_bytes(CLEAN)), 40, body)
    pe = find_player_entry(EbScript.from_bytes(eb))
    before = _resolved_edges(eb, pe, 40)
    assert [(v, op) for v, op, _ in before] == [(1, 0x22), (2, 0x22), (None, 0x22)]
    assert before[2][2] == (9,)                       # default lands on the convergence Wait(9)
    # insert a guard AT the convergence (rel 28): arms + default target it exactly -> flow-through
    probe = opcodes.wait(7)
    eb2 = edit.insert_in_function(eb, pe, 40, 28, probe)
    after = _resolved_edges(eb2, pe, 40)
    # the CASE edges (targets before the insert) still land on their arms, untouched; the DEFAULT edge
    # (target == the insert point) lands on the probe and flows into the old convergence
    assert [(v, op, args) for v, op, args in after] == [
        (1, 0x22, (1,)), (2, 0x22, (2,)), (None, 0x22, (7,))]
    # the arms' own convergence jumps also cross the insert -- verify they resolve to the probe too
    s = EbScript.from_bytes(eb2)
    f = s.entry(pe).func_by_tag(40)
    jmps = [i for i in s.instrs(f) if i.op == 0x01]
    for j in jmps:
        raw = j.imm(0)
        tgt = j.end + (raw - 0x10000 if raw >= 0x8000 else raw)
        t, _ = read_code(eb2, tgt)
        assert (t.op, tuple(t.args)) == (0x22, (7,))


def test_insert_before_a_jump_table_shifts_it_wholesale():
    body = _switch_func_body()
    eb = edit.add_function(CLEAN, find_player_entry(EbScript.from_bytes(CLEAN)), 40, body)
    pe = find_player_entry(EbScript.from_bytes(eb))
    before = _resolved_edges(eb, pe, 40)
    eb2 = edit.insert_in_function(eb, pe, 40, 4, opcodes.wait(5))   # between selector and switch
    assert _resolved_edges(eb2, pe, 40) == before                   # table shifted as a block, intact


def test_straddling_plain_jump_is_fixed_not_refused():
    # a forward jump crossing the insert point gets its displacement grown by len(ins)
    body = (bytes([0x01]) + struct.pack("<h", 3)      # jmp -> rel 6 (skip the Wait(3) at rel 3)
            + opcodes.wait(3)                          # rel 3 (jumped over)
            + opcodes.wait(9) + opcodes.RETURN)        # rel 6 convergence
    eb = edit.add_function(CLEAN, find_player_entry(EbScript.from_bytes(CLEAN)), 41, body)
    pe = find_player_entry(EbScript.from_bytes(eb))
    eb2 = edit.insert_in_function(eb, pe, 41, 3, opcodes.wait(6))   # insert INSIDE the jumped-over span
    s = EbScript.from_bytes(eb2)
    f = s.entry(pe).func_by_tag(41)
    j = next(i for i in s.instrs(f) if i.op == 0x01)
    tgt = j.end + j.imm(0)
    t, _ = read_code(eb2, tgt)
    assert (t.op, tuple(t.args)) == (0x22, (9,))       # still lands on the convergence Wait(9)


# --- the guard fragment --------------------------------------------------------------------
def test_letter_content_guard_shape():
    g = md.letter_content_guard(56, 557)
    ops = [i.op for i in iter_code(g, 0, len(g))]
    assert ops == [0x05, 0x02, 0x20]                   # cond, skip, WindowAsync
    w = [i for i in iter_code(g, 0, len(g)) if i.op == 0x20][0]
    assert list(w.args) == [_mognet.LETTER_WINDOW, _mognet.LETTER_FLAGS, 557]


# --- the real donor (install-gated) --------------------------------------------------------
def _stock_1865():
    try:
        from ff9mapkit.extract import extract_event_script
        from ff9mapkit import dialogue
        eb = extract_event_script("1865", lang="us")
        mes = dialogue.extract_field_mes(1865, "us")
        return (eb, mes) if eb and mes else None
    except Exception:
        return None


_REAL = _stock_1865()


@pytest.mark.skipif(_REAL is None, reason="no FF9 install reachable for field 1865")
def test_find_letter_displays_on_the_real_donor():
    """The first playtest's decode: 1865 carries FOUR Byte[37] switches -- the read-mail display, the
    delivery announce (txids -1), the delivery display, and the delivery thanks (txids +1)."""
    sites = md.find_letter_displays(_REAL[0])
    roles = [s["role"] for s in sorted(sites, key=lambda s: s["switch_off"])]
    assert roles == ["letter", "announce", "letter", "thanks"]
    for s in sites:
        base = {19: 46, 22: 49, 33: 52, 48: 63}               # Kupo's four stock letters
        delta = {"letter": 0, "announce": -1, "thanks": 1}[s["role"]]
        assert s["arms"] == {v: t + delta for v, t in base.items()}
    assert (md.find_letter_display(_REAL[0])["entry"], md.find_letter_display(_REAL[0])["tag"]) == (5, 3)


@pytest.mark.skipif(_REAL is None, reason="no FF9 install reachable for field 1865")
def test_patch_donor_field_end_to_end():
    eb, mes = _REAL
    patched, add_mes = md.patch_donor_field(
        eb, mes, roster_name="Mogwai", content_letters={56: "Hello, kupo!"},
        inbound={"variant": 57, "from_id": 1, "prompt": "Deliver this, kupo?", "line": "Thanks!"})
    assert not eblint.errors(eblint.lint_eb(patched))
    # EVERY classified site's convergence now opens with a guard condition (the variant-56 splice)
    sites = md.find_letter_displays(patched)
    assert [s["role"] for s in sorted(sites, key=lambda s: s["switch_off"])] == \
        ["letter", "announce", "letter", "thanks"]
    for s in sites:
        conv_ins, _ = read_code(patched, s["conv"])
        assert conv_ins.op == 0x05, f"site {s['role']}@{s['switch_off']} conv lacks the guard"
    # the additive mes: entry 0 (42 rows) + the announce/letter/thanks triplet + 2 prompt entries
    from ff9mapkit import dialogue
    add = dialogue.parse_mes(add_mes)
    stock_max = max(dialogue.parse_mes(mes))
    assert add[0].text.count("\n") == _mognet.ROSTER_SIZE        # 41 breaks = 42 rows
    assert add[0].text.endswith("Mogwai")
    assert set(add) == {0} | {stock_max + k for k in range(1, 6)}
    assert add[stock_max + 1].text.startswith(md.SPEAKER_DRESS)  # the announce, speaker form
    assert "[CHOO]" in add[stock_max + 4].text                   # the offer prompt has REAL choice rows
    # the talk tag now OPENS with the inbound give gate (give_available_cond on variant 57)
    site = md.find_letter_display(patched)
    talk = EbScript.from_bytes(patched).entry(site["entry"]).func_by_tag(site["tag"])
    head = patched[talk.abs_start:talk.abs_start + len(_mognet.give_available_cond(57))]
    assert head == _mognet.give_available_cond(57)


@pytest.mark.skipif(_REAL is None, reason="no FF9 install reachable for field 1865")
def test_patch_refuses_a_stock_variant_collision():
    # the shipped-band guard fires first (19 is a real letter's variant -- its locks alias); the
    # dedicated stock-arm check behind it is defence-in-depth for allow_shipped-style futures
    with pytest.raises(ValueError, match="SHIPPED band"):
        md.patch_recipient_letters(_REAL[0], {19: {"letter": 999}})   # 19 is Kupo's own letter
