"""The Memoria custom extended opcodes (0x112-0x11E, the 0xFF page).

The engine reads every operand of these with getv3() (3-byte immediates,
expression-flagged like any arg) and they never appear in the static
opArgCount/opArgSize tables — the regen script's CUSTOM_EXTENDED block owns
their shapes, transcribed from the DoEventCode case bodies. This battery pins
encode->decode round trips so lint/disasm treat them as first-class.
"""
from __future__ import annotations

from ff9mapkit.eb import disasm as D
from ff9mapkit.eb import exprasm, opcodes


def _decode_one(body: bytes):
    ins = list(D.iter_code(body, 0, len(body)))
    assert len(ins) == 1 and ins[0].end == len(body)
    return ins[0]


def test_add_shop_item_round_trip():
    body = opcodes.encode("AddShopItem", 40, 236, 1)
    assert body[:2] == bytes([0xFF, 0x15])
    assert _decode_one(body).op == 0x115
    assert opcodes.resolve("AddShopItem") == 0x115


def test_walk_ex_and_singletons():
    body = opcodes.encode(0x117, 3, 40, 100, -20, 300, 0)
    assert _decode_one(body).op == 0x117
    for op, args in ((0x11A, (1000,)), (0x11B, (7,)), (0x11E, (0, 18, 0))):
        assert _decode_one(opcodes.encode(op, *args)).op == op


def test_extended_expression_arg():
    """getv3 honors the arg-flag bits like any classic arg — an expression
    operand (e.g. a vector cell as the shop id) must round-trip."""
    expr = exprasm.assemble("const(1000) const(0) B_VECTOR B_EXPR_END")
    body = opcodes.encode("AddShopItem", expr, 236, 1, arg_flags=0b001)
    assert _decode_one(body).op == 0x115


def test_extended_mixed_stream_walks():
    body = (opcodes.encode(0x66, 0, 42)             # SetTextVariable
            + opcodes.encode("AddShopItem", 40, 236, 1)
            + opcodes.encode("ClearMemoriaVector", 1000)
            + bytes([0x04]))
    ops = [i.op for i in D.iter_code(body, 0, len(body))]
    assert ops == [0x66, 0x115, 0x11A, 0x04]
