"""Phase 4b keystone: the labeled disassembler (`cmdasm.disassemble_block`) + switch-relocating assembler.

`disassemble_block` decodes a function to `assemble_block` source where every JUMP and every SWITCH case/default
target is a function-relative `L<n>` label; re-assembling reproduces the bytes, and -- because targets are labels
-- a length change between a branch and its target is RELOCATED automatically. This is what a length-changing
rebuild (mid-function insert / cross-0xFF flag / switch-case) splices back via `eb.edit.replace_function_body`.
"""
from __future__ import annotations

import pytest

from ff9mapkit.eb import cmdasm, disasm
from ff9mapkit.eb.model import EbScript


def _game():
    try:
        from ff9mapkit.extract import EventBundle
        return EventBundle()
    except Exception:                                              # noqa: BLE001
        return None


# ---- synthetic round-trip (no install) ----
def test_roundtrip_jump_and_switch_synthetic():
    """A hand-authored function with a forward JMP + a contiguous SWITCH round-trips
    disassemble_block -> assemble_block byte-for-byte."""
    src = ("JMP(mid)\n"
           "mid:\n"
           "SWITCH(0, dflt, c0, c1)\n"
           "c0:\nSetTriangleFlagMask(1)\nRET()\n"
           "c1:\nSetTriangleFlagMask(2)\nRET()\n"
           "dflt:\nRET()\n")
    body = cmdasm.assemble_block(src)
    rt = cmdasm.disassemble_block(body, 0, len(body))
    assert cmdasm.assemble_block(rt) == body
    # the decoded switch's three arms all resolve to in-body instruction boundaries (forward)
    sw = next(i.switch() for i in disasm.iter_code(body, 0, len(body)) if i.is_switch)
    offs = {i.off for i in disasm.iter_code(body, 0, len(body))}
    assert all(e.target in offs for e in sw.edges)


def test_roundtrip_switchex_explicit_values():
    """The explicit value/offset form (0x06 SWITCHEX) round-trips with its case VALUES preserved."""
    src = ("SWITCHEX(dflt, 7, c7, 9, c9)\n"
           "c7:\nSetTriangleFlagMask(1)\nRET()\n"
           "c9:\nSetTriangleFlagMask(2)\nRET()\n"
           "dflt:\nRET()\n")
    body = cmdasm.assemble_block(src)
    assert cmdasm.assemble_block(cmdasm.disassemble_block(body, 0, len(body))) == body
    sw = next(i.switch() for i in disasm.iter_code(body, 0, len(body)) if i.is_switch)
    assert sorted(e.value for e in sw.edges if not e.is_default) == [7, 9]


# ---- the keystone payoff: relocation under a length change ----
def test_jump_relocates_under_prepend():
    """Prepending an instruction to the SOURCE shifts the body; the JMP, being a label, retargets so it still
    lands on the same logical instruction (the engine never sees a stale offset)."""
    src = "JMP(done)\nSetTriangleFlagMask(5)\nSetTriangleFlagMask(6)\ndone:\nRET()\n"
    base = cmdasm.assemble_block(src)
    grown = cmdasm.assemble_block("SetTriangleFlagMask(9)\n" + src)               # SetTriangleFlagMask(9) = 3 bytes prepended
    assert len(grown) == len(base) + 3
    jb = disasm.jump_target(next(i for i in disasm.iter_code(base, 0, len(base)) if i.op == 0x01))
    jg = disasm.jump_target(next(i for i in disasm.iter_code(grown, 0, len(grown)) if i.op == 0x01))
    assert jg == jb + 3                                            # the jump target moved with the body


def test_switch_relocates_under_prepend():
    """The crux Phase-4b claim: a SWITCH's case offsets (raw forward reloffsets, not relocated by the engine)
    are recomputed on re-assembly, so inserting code before a switch keeps every arm correct."""
    src = ("SWITCH(0, dflt, c0, c1)\n"
           "c0:\nSetTriangleFlagMask(1)\nRET()\n"
           "c1:\nSetTriangleFlagMask(2)\nRET()\n"
           "dflt:\nSetTriangleFlagMask(3)\nRET()\n")
    base = cmdasm.assemble_block(src)
    grown = cmdasm.assemble_block("SetTriangleFlagMask(9)\n" + src)               # +3 bytes before the switch
    assert len(grown) == len(base) + 3
    sb = next(i.switch() for i in disasm.iter_code(base, 0, len(base)) if i.is_switch)
    sg = next(i.switch() for i in disasm.iter_code(grown, 0, len(grown)) if i.is_switch)
    assert sorted(e.target for e in sg.edges) == [t + 3 for t in sorted(e.target for e in sb.edges)]


# ---- overflow guards: a length-changing edit must FAIL LOUD, never silently wrap a target ----
def test_jump_overflow_raises_not_wraps():
    """JMP/JMP_IF read a SIGNED int16; JMP_IFNOT an UNSIGNED u16. A relocation that pushes a target out of range
    must raise CmdAsmError (else `& 0xFFFF` would silently emit a garbage/backward target)."""
    AI, E = cmdasm.assemble_instruction, cmdasm.CmdAsmError
    with pytest.raises(E):                                          # forward JMP past +32767
        AI("JMP", ["far"], label_offsets={"far": 40000}, instr_end=0)
    with pytest.raises(E):                                          # backward JMP past -32768
        AI("JMP", ["back"], label_offsets={"back": 0}, instr_end=40000)
    with pytest.raises(E):                                          # JMP_IF (signed) same bound
        AI("JMP_IF", ["far"], label_offsets={"far": 40000}, instr_end=0)
    with pytest.raises(E):                                          # JMP_IFNOT forward past +65535
        AI("JMP_IFNOT", ["far"], label_offsets={"far": 70000}, instr_end=0)
    assert len(AI("JMP", ["ok"], label_offsets={"ok": 100}, instr_end=10)) == 3   # in range still assembles


def test_switch_overflow_raises_not_wraps():
    """A switch reloffset is an unsigned u16; a case/default more than 65535 bytes past the anchor must raise."""
    with pytest.raises(cmdasm.CmdAsmError):
        cmdasm.assemble_instruction("SWITCH", ["0", "dflt", "far"],
                                    label_offsets={"dflt": 10, "far": 70000}, instr_off=0)
    # in range (a forward case just under the ceiling) still assembles
    assert cmdasm.assemble_instruction("SWITCH", ["0", "dflt", "near"],
                                       label_offsets={"dflt": 10, "near": 500}, instr_off=0)


def test_disassemble_block_truncated_is_clean_error():
    """A corrupt/forked .eb whose entry size claims bytes past the buffer must not raw-crash: clamp + a typed
    CmdAsmError, mirroring battleai.disassemble_ai."""
    assert cmdasm.disassemble_block(b"\x04", 0, 50) == "RET()"      # end past buffer -> clamps, decodes in-bounds
    with pytest.raises(cmdasm.CmdAsmError):                         # a malformed expr stream running off the buffer
        cmdasm.disassemble_block(b"\x05\x00", 0, 2)


# ---- real game bytecode (install-gated) ----
def test_roundtrip_real_fields_incl_switches():
    """disassemble_block -> assemble_block is byte-exact on real field functions, INCLUDING switch-bearing ones
    and the negative-base 0x0B SWITCH (fields 353/552/1057 have base < 0). A representative sample; the full
    676-field sweep (29382/29382, 3155/3155 switch fns) was run during development."""
    b = _game()
    if b is None:
        pytest.skip("no game install")
    ids = [351, 300, 302, 70, 353, 552, 814, 1010, 1057, 1251, 2803, 206]   # incl. all the negative-base cases
    n = nsw = 0
    for fid in ids:
        try:
            data = b.eb_for_id(fid)
        except Exception:                                          # noqa: BLE001
            continue
        if not data:
            continue
        eb = EbScript.from_bytes(data)
        for e in eb.entries:
            if e.empty:
                continue
            for f in e.funcs:
                orig = bytes(eb.data[f.abs_start:f.abs_end])
                src = cmdasm.disassemble_block(eb.data, f.abs_start, f.abs_end)
                assert cmdasm.assemble_block(src) == orig, f"field {fid} entry {e.index} tag {f.tag}"
                n += 1
                nsw += any(i.is_switch and i.switch() for i in eb.instrs(f))
    if not n:
        pytest.skip("none of the sample fields were present")
    assert nsw > 0, "the sample must exercise switch functions"
