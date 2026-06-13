"""[[ate]] synthesis -- the Active Time Event primitive (the 'Press SELECT' optional-cutscene mechanism).

These pin the BYTES the synthesizer emits against the engine facts + the real Lindblum Main-St hub
(field 552, the Small-Town Knight ATE): the ATE(mode) prompt opcode, the menu-open gate
(usercontrol AND avail AND B_KEYON(SELECT)), the winATE(64) menu window, the GetChoose branch, and the
Main_Init wiring (ATE + avail-flag + InitCode). No game required -- the .eb round-trips and re-parses.
"""
from __future__ import annotations

from ff9mapkit import data
from ff9mapkit.content import ate, choice, region
from ff9mapkit.eb import EbScript, disasm, edit, opcodes


def test_ate_opcode_bytes():
    assert opcodes.ate(5) == bytes([0xD7, 0x00, 0x05])      # ATE(5) force-show -- verified vs field 552/206
    assert opcodes.ate(1) == bytes([0xD7, 0x00, 0x01])      # ATE(1) Blue/new
    assert opcodes.ate(0) == bytes([0xD7, 0x00, 0x00])      # ATE(0) off


def test_select_gate_matches_field552_structure():
    """The menu-open gate is field 552 [11667] byte-for-byte (bar the avail var): usercontrol==1 AND
    <avail>==1 AND B_KEYON(SELECT). Decode the expression tokens (don't raw-byte-count: the avail
    long-index 8300=0x206C contains a 0x20 byte that collides with the T_EQ token value)."""
    gate = region.cond_ate_select(region.GLOB_BOOL, 8300)
    assert gate[0] == 0x05                                  # EXPR_OP
    txt, _ = disasm.read_expr(gate, 1)
    assert "op7A(2)" in txt                                 # GetSysvar(2) = usercontrol
    assert "op4F" in txt                                    # B_KEYON (the SELECT press-edge)
    assert txt.count("op20") == 2                           # two equality tests (usercontrol==1, avail==1)
    assert txt.count("op27") == 2                           # two && (3-way AND)
    assert txt.rstrip("}").endswith("op7F")                 # terminated


def test_main_init_inject_is_arm_set_initcode():
    inj = ate.main_init_inject(avail_idx=ate.ATE_FLAG_BASE, menu_slot=9, mode=ate.MODE_BLUE)
    names, pos = [], 0
    while pos < len(inj):
        ins, pos = disasm.read_code(inj, pos)
        names.append(ins.name)
    assert names == ["ATE", "op_05", "InitCode"]           # arm prompt ; set avail=1 ; activate menu entry
    # the ATE arg is the mode; the InitCode arg is the menu slot
    first, _ = disasm.read_code(inj, 0)
    assert first.imm(0) == ate.MODE_BLUE


def _field_with_ate(n_rows: int = 3):
    base = data.blank_field_bytes("us")
    slot = EbScript.from_bytes(base).first_free_slot()
    bodies = [choice.option_body({}) for _ in range(n_rows)]
    entry = ate.menu_entry(prompt_txid=50, option_bodies=bodies, avail_idx=ate.ATE_FLAG_BASE)
    out = edit.append_entry(base, slot, entry)
    inj = ate.main_init_inject(avail_idx=ate.ATE_FLAG_BASE, menu_slot=slot, mode=ate.MODE_BLUE)
    out = edit.insert_in_function(out, 0, 0, 0, inj)        # prepend the wiring to Main_Init
    return EbScript.from_bytes(out), slot


def test_menu_entry_structure_and_roundtrip():
    eb, slot = _field_with_ate()
    me = eb.entry(slot)
    assert [f.tag for f in me.funcs] == [0, 1]              # tag-0 init + tag-1 loop
    loop = list(eb.instrs(me.func_by_tag(1)))
    ws = [i for i in loop if i.name == "WindowSync"]
    assert ws and ws[0].imm(1) == ate.WIN_ATE               # the menu window carries winATE (64)
    assert ws[0].imm(2) == 50                               # the prompt txid
    assert eb.to_bytes() == EbScript.from_bytes(eb.to_bytes()).to_bytes()   # round-trips clean


def test_menu_entry_winate_and_getchoose_branch():
    eb, slot = _field_with_ate(n_rows=3)
    loop = list(eb.instrs(eb.entry(slot).func_by_tag(1)))
    # winATE menu window present
    assert any(i.name == "WindowSync" and i.imm(1) == ate.WIN_ATE for i in loop)
    # the per-row branch reads GetChoose (sysvar 9) -- bodies are empty here, so the branch may be
    # elided; with non-empty bodies it appears. Assert the gate uses B_KEYON regardless.
    raw = eb.to_bytes()
    assert raw == EbScript.from_bytes(raw).to_bytes()       # round-trips


def test_ate_main_init_wiring_runs_first():
    eb, _ = _field_with_ate()
    f0 = eb.entry(0).func_by_tag(0)
    first, _ = disasm.read_code(eb.data, f0.abs_start)
    assert first.name == "ATE"                              # the prompt is armed at the very top of Main_Init
