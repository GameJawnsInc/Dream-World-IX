"""choice.switch_on_choice -- the op_0B dispatch that reads the dialog choice ONCE.

Why this exists: `choice.branch` emits an independent `if(GetChoose()==i)` per option and each one
RE-READS sysvar 9 when it runs. The moment one arm opens a second choice window, that window overwrites
sysvar 9 and the later arms test the INNER answer (pick row 0, answer "No" = row 1 in the nested confirm,
and the outer row-1 arm fires too). FF9 itself avoids this by pushing GetChoose() once and switching:
field 300 @4278-4282, field 2919 @3552-3556. These pin the emitter against the kit's own switch DECODER,
which is validated boundary-aligned across all 5563 switches in the 676 shipping fields.
"""
from __future__ import annotations

from ff9mapkit.content import choice as _choice
from ff9mapkit.eb import disasm, opcodes


def _decode(blob):
    ins = list(disasm.iter_code(blob, 0, len(blob)))
    sw = [i for i in ins if i.op == _choice.SWITCH_OP]
    assert len(sw) == 1, "expected exactly one op_0B dispatch"
    return ins, disasm.decode_switch(sw[0])


def test_switch_targets_each_arm_and_defaults_past_the_block():
    bodies = [opcodes.wait(11), opcodes.wait(22) + opcodes.wait(23), b"", opcodes.wait(44)]
    blob = _choice.switch_on_choice(bodies)
    ins, info = _decode(blob)
    assert info.base == 0
    assert blob[:4] == bytes([0x05, 0x7A, 0x09, 0x7F])      # the one-and-only selector read precedes the switch
    cases = [e for e in info.edges if not e.is_default]
    assert [e.value for e in cases] == [0, 1, 2, 3]
    # every arm target is a real instruction boundary inside the blob...
    offs = {i.off for i in ins}
    assert all(e.target in offs or e.target == len(blob) for e in info.edges)
    # ...and the default lands exactly past the whole block (an out-of-range pick does nothing)
    assert [e.target for e in info.edges if e.is_default] == [len(blob)]


def test_every_arm_converges_on_the_common_exit():
    """No arm may fall through into the next row's body -- each ends with an unconditional hop to the
    single exit. This is the property `branch` cannot give us."""
    bodies = [opcodes.wait(11), opcodes.wait(22), b"", opcodes.wait(44)]
    blob = _choice.switch_on_choice(bodies)
    ins, _ = _decode(blob)
    hops = [i for i in ins if i.op == 0x01]                    # JMP_UNCOND
    assert len(hops) == len(bodies)                            # exactly one per arm, including the empty one
    for h in hops:
        assert h.off + h.length + h.args[0] == len(blob)       # all land on the exit


def test_empty_body_gets_its_own_arm_not_a_fallthrough():
    blob = _choice.switch_on_choice([b"", opcodes.wait(9)])
    ins, info = _decode(blob)
    t0 = [e.target for e in info.edges if e.value == 0][0]
    t1 = [e.target for e in info.edges if e.value == 1][0]
    assert t0 != t1                                            # distinct arms
    at0 = [i for i in ins if i.off == t0][0]
    assert at0.op == 0x01                                      # row 0 = a bare hop to the exit, no body


def test_single_row_and_empty_input():
    assert _choice.switch_on_choice([]) == b""
    ins, info = _decode(_choice.switch_on_choice([opcodes.wait(5)]))
    assert len([e for e in info.edges if not e.is_default]) == 1


def test_switch_reads_the_choice_once_via_sysvar_9():
    """switch_body must push GetSysvar(9) before the switch -- the whole point is one read."""
    body = _choice.switch_body(500, [opcodes.wait(1), opcodes.wait(2)])
    ins = list(disasm.iter_code(body, 0, len(body)))
    # the selector push: op_05 {GetSysvar(9) END} -- byte-exact, as field 300 @4278 spells it
    assert b"\x05\x7a\x09\x7f" in body
    sw = [i for i in ins if i.op == _choice.SWITCH_OP]
    assert len(sw) == 1                                        # exactly one dispatch
    assert sum(1 for i in ins if i.op == 0x1F) == 1            # exactly one prompt window
    # and NO if-block re-reads the choice (that is the bug this replaces)
    assert sum(1 for i in ins if i.op in (0x02, 0x03)) == 0


def test_large_menu_offsets_stay_correct():
    """7 rows with big bodies -- the real save-moogle menu shape; catches i16 offset math errors."""
    bodies = [opcodes.wait(i) * 40 for i in range(1, 8)]
    blob = _choice.switch_on_choice(bodies)
    ins, info = _decode(blob)
    assert len([e for e in info.edges if not e.is_default]) == 7
    offs = {i.off for i in ins}
    assert all(e.target in offs or e.target == len(blob) for e in info.edges)
    for h in [i for i in ins if i.op == 0x01]:
        assert h.off + h.length + h.args[0] == len(blob)
