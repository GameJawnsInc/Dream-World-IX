"""The `.eb` EXPRESSION sub-language vocabulary -- the `op_binary` operator table + the variable-token encoding.

Committed, hand-transcribed from the open-source Memoria ``EBin.cs`` (the ``op_binary`` / ``VariableSource`` /
``VariableType`` enums -- names/values only, provenance-clean). The disassembler's ``read_expr`` decodes an
expression's token stream but labels each operator ``opXX``; this table turns those into the real mnemonics
(``B_CURHP``, ``B_LT``, ``B_PLUS``, ``B_SYSVAR`` …) and decodes a ``0xC0+`` variable token into its
``source.type[index]`` form -- which is what makes an enemy-AI script (or any field script) READABLE.

A var token byte (>= 0xC0, the ``B_VAR`` base) encodes (``EBin.expr_varSpec`` / ``getVarOperation``):
  bit7,6 = 1 (the 0xC0 base) · bit5 = long-index (a 2-byte index follows, else 1) · bits 4-2 = VariableType ·
  bits 1-0 = VariableSource (only 0-3 -- Global/Map/Instance/Null; the higher sources Object/System/Member come
  from their own tokens B_OBJSPECA/B_SYSLIST/B_MEMBER). e.g. ``0xC4`` = Global + Bit (a story-flag read, the
  kit's GLOB_BOOL); ``0xC5`` = Map + Bit (the transient MAP_BOOL twin).
"""
from __future__ import annotations

# op_binary (EBin.cs): the expression operator token -> mnemonic. 0-127; 0x29/0x5F/0x78-0x7E are the operators
# that read inline operand bytes (handled by read_expr), the rest are pure stack operators.
EXPR_OP_NAMES = {
    0: "B_PAD0", 1: "B_PAD1", 2: "B_PAD2", 3: "B_PAD3",
    4: "B_POST_PLUS", 5: "B_POST_MINUS", 6: "B_PRE_PLUS", 7: "B_PRE_MINUS",
    8: "B_POST_PLUS_A", 9: "B_POST_MINUS_A", 10: "B_PRE_PLUS_A", 11: "B_PRE_MINUS_A",
    12: "B_SINGLE_PLUS", 13: "B_SINGLE_MINUS", 14: "B_NOT", 15: "B_NOT_E", 16: "B_COMP",
    17: "B_MULT", 18: "B_DIV", 19: "B_REM", 20: "B_PLUS", 21: "B_MINUS",
    22: "B_SHIFT_LEFT", 23: "B_SHIFT_RIGHT", 24: "B_LT", 25: "B_GT", 26: "B_LE", 27: "B_GE",
    28: "B_LT_E", 29: "B_GT_E", 30: "B_LE_E", 31: "B_GE_E", 32: "B_EQ", 33: "B_NE", 34: "B_EQ_E", 35: "B_NE_E",
    36: "B_AND", 37: "B_XOR", 38: "B_OR", 39: "B_ANDAND", 40: "B_OROR", 41: "B_MEMBER", 42: "B_COUNT",
    43: "B_PICK", 44: "B_LET", 45: "B_LET_A", 46: "B_LET_E", 47: "B_MULT_LET", 48: "B_DIV_LET", 49: "B_REM_LET",
    50: "B_PLUS_LET", 51: "B_MINUS_LET", 52: "B_SHIFT_LEFT_LET", 53: "B_SHIFT_RIGHT_LET",
    54: "B_MULT_LET_A", 55: "B_DIV_LET_A", 56: "B_REM_LET_A", 57: "B_PLUS_LET_A", 58: "B_MINUS_LET_A",
    59: "B_SHIFT_LEFT_LET_A", 60: "B_SHIFT_RIGHT_LET_A", 61: "B_AND_LET", 62: "B_XOR_LET", 63: "B_OR_LET",
    64: "B_AND_LET_A", 65: "B_XOR_LET_A", 66: "B_OR_LET_A", 67: "B_AND_LET_E", 68: "B_XOR_LET_E", 69: "B_OR_LET_E",
    70: "B_CAST8", 71: "B_CAST8U", 72: "B_CAST16", 73: "B_CAST16U", 74: "B_CAST_LIST", 75: "B_LMAX", 76: "B_LMIN",
    77: "B_SELECT", 78: "B_OBJSPEC", 79: "B_KEYON", 80: "B_SIN2", 81: "B_COS2",
    82: "B_CURHP", 83: "B_MAXHP", 84: "B_AND_E", 85: "B_NAND_E", 86: "B_XOR_E", 87: "B_OR_E",
    88: "B_KEYOFF", 89: "B_KEY", 90: "B_KEYON2", 91: "B_KEYOFF2", 92: "B_KEY2",
    93: "B_ANGLE", 94: "B_DISTANCE", 95: "B_PTR", 96: "B_ANGLEA", 97: "B_DISTANCEA", 98: "B_SIN", 99: "B_COS",
    100: "B_HAVE_ITEM", 101: "B_BAFRAME", 102: "B_ANGLE2", 103: "pad67", 104: "pad68", 105: "pad69",
    106: "B_FRAME", 107: "B_PARTYCHK", 108: "B_SPS", 109: "B_PARTYADD", 110: "B_CURMP", 111: "B_MAXMP",
    112: "B_BGIID", 113: "B_BGIFLOOR", 120: "B_OBJSPECA", 121: "B_SYSLIST", 122: "B_SYSVAR",
    123: "B_pad7b", 124: "B_PAD4", 125: "B_CONST", 126: "B_CONST4", 127: "B_EXPR_END",
}

# VariableSource / VariableType (EBin.cs). The var-token decode uses source 0-3 (the only ones the 0xC0 token
# encodes); 4-7 are reached via dedicated tokens and listed for completeness.
VAR_SOURCE = {0: "Global", 1: "Map", 2: "Instance", 3: "Null", 4: "Object", 5: "System", 6: "Member", 7: "Int26"}
VAR_TYPE = {0: "SBit", 1: "Bit", 2: "Int24", 3: "UInt24", 4: "SByte", 5: "Byte", 6: "Int16", 7: "UInt16"}


def expr_op_name(token: int) -> str:
    """Mnemonic for an expression operator token (or ``opXX`` if it isn't a defined op_binary value)."""
    return EXPR_OP_NAMES.get(token, f"op{token:02X}")


def decode_var(token: int, index: int) -> str:
    """A ``0xC0+`` variable token + its decoded index -> ``Source.Type[index]`` (e.g. ``Global.Bit[8512]``)."""
    src = VAR_SOURCE.get(token & 3, f"src{token & 3}")
    typ = VAR_TYPE.get((token >> 2) & 7, f"t{(token >> 2) & 7}")
    return f"{src}.{typ}[{index}]"
