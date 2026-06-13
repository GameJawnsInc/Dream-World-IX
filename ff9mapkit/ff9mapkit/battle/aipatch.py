"""Phase-6b: SAME-LENGTH enemy-AI constant patches -- the first AI *authoring* step (read = Phase-6a `battleai`).

An enemy's AI is the per-scene ``EVT_BATTLE_*.eb`` bytecode. The safest authoring edit is a *literal* one: change
a numeric CONSTANT in place without moving any bytes -- an HP threshold a phase-switch compares (``B_CONST`` in
an expression), the attack index a turn selects (a ``BTLCMD`` immediate), a ``Wait`` count. No length change means
no ``fpos``/entry-table fixup and no risk of mis-packing -- byte-accurate by construction (the eb-codec identity
holds), exactly like ``scene_data``'s surgical raw16 patch.

Addressing is by BYTE OFFSET (from ``battle-ai --sites``) + a required OLD-value guard: the patch only applies if
the constant at that offset currently equals ``old`` (so a stale/wrong offset fails LOUD instead of corrupting a
random byte), and ``new`` must fit the SAME byte width. Because a battle eb's bytecode is language-identical
(only the 84-byte name field differs), the same offset patches every language's eb.

This reaches NUMERIC LITERALS only (command immediates + ``B_CONST``/``B_CONST4`` expression literals) -- the
"same-length literal patch" tier. Structural AI changes (new branches, an expression assembler, retargeting which
variable is read) are Phase-6c. Read-the-AI-first is mandatory: there is no semantic search; you cite the offset
the disassembler prints.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..eb._optables import OP_ARG_COUNT
from ..eb import disasm as _disasm
from ..eb.model import EbScript

_I32 = 2 ** 31 - 1


class AiPatchError(ValueError):
    pass


@dataclass(frozen=True)
class Site:
    """One patchable numeric constant in the AI bytecode."""
    offset: int        # absolute byte offset of the constant's first byte (the patch target)
    width: int         # byte width (1/2/3/4) -- a same-length patch occupies exactly these bytes
    value: int         # the current little-endian unsigned value
    where: str         # human context, e.g. "entry2/tag1 BTLCMD arg0" or "entry2/tag1 expr-const"
    vmax: int          # the largest value the ENGINE accepts here (usually 2^(8w)-1; B_CONST4 masks to 26 bits)


def _full_max(width: int) -> int:
    return (1 << (8 * width)) - 1


def _le(raw: bytes, pos: int, sz: int) -> int:
    v = 0
    for k in range(sz):
        v |= raw[pos + k] << (8 * k)
    return v


def _expr_constants(raw: bytes, pos: int, ctx: str) -> tuple[list, int]:
    """Walk one expression token stream (mirrors :func:`disasm.pretty_expr`), collecting the ``B_CONST`` (2-byte)
    and ``B_CONST4`` (4-byte) literal sites. Returns (sites, new_pos)."""
    sites = []
    while True:
        o = raw[pos]; pos += 1
        isconst = o in (0x7D, 0x7E)
        isvar = o >= 0xC0 or o in (0x29, 0x5F, 0x78, 0x79, 0x7A)
        if not isconst and not isvar:
            if o == 0x7F:
                break
            continue
        if o == 0x7E:                                   # B_CONST4 -- a 4-byte literal, MASKED to 26 bits in-engine
            sites.append(Site(pos, 4, _le(raw, pos, 4), f"{ctx} expr-const4", 0x3FFFFFF)); pos += 4
        elif o == 0x7D:                                 # B_CONST -- a 2-byte literal (signed 16; byte-faithful)
            sites.append(Site(pos, 2, _le(raw, pos, 2), f"{ctx} expr-const", _full_max(2))); pos += 2
        elif o >= 0xE0 or o == 0x78:                    # long var / B_OBJSPECA -- 2 operand bytes (NOT a literal)
            pos += 2
        else:                                           # short var / B_SYSLIST / B_SYSVAR / B_MEMBER / B_PTR
            pos += 1
    return sites, pos


def _func_constants(raw: bytes, start: int, end: int, ctx: str) -> list:
    """Collect every patchable numeric constant in ``raw[start:end]`` (command immediates + expression literals).
    Mirrors :func:`disasm.read_code`'s operand walk exactly so the offsets always line up with the disassembly."""
    sites = []
    pos = start
    guard = 0
    while pos < end and guard < 100000:
        guard += 1
        op = raw[pos]; pos += 1
        if op == 0xFF:
            op = 0x100 | raw[pos]; pos += 1
        ac = OP_ARG_COUNT[op] if op < len(OP_ARG_COUNT) else 0
        arg_flag = 0
        if op >= 0x10 and ac != 0:
            arg_flag = raw[pos]; pos += 1
        if op == 0x05:
            arg_flag = 1
        if ac < 0:
            ac = raw[pos]; pos += 1
            if op == 0x0D:
                ac |= raw[pos] << 8; pos += 1
            if op == 0x06:
                ac = 1 + 2 * ac
            elif op in (0x0B, 0x0D):
                ac = 2 + ac
        for i in range(ac):
            if arg_flag & (1 << i):
                esites, pos = _expr_constants(raw, pos, ctx)
                sites += esites
            else:
                sz = _disasm.argsize(op, i)
                if sz:
                    sites.append(Site(pos, sz, _le(raw, pos, sz), f"{ctx} {_disasm.op_name(op)} arg{i}", _full_max(sz)))
                pos += sz
    return sites


def constant_sites(eb_bytes: bytes) -> list:
    """Every patchable numeric constant in a battle ``.eb``'s AI, in byte order. The ``offset`` of each is the
    ``at`` you cite in an ``[[scene.ai_patch]]``; the disassembler (``battle-ai --sites``) prints them."""
    try:                                                 # a truncated/corrupt eb (e.g. a bad funcCount) can index
        eb = EbScript.from_bytes(eb_bytes)               # past the buffer during parse -> raise a CLEAN error, not
    except (ValueError, IndexError) as ex:               # a raw IndexError (mirrors battleai.disassemble_ai)
        raise AiPatchError(f"malformed/truncated AI .eb: {type(ex).__name__}: {ex}")
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            ctx = f"entry{e.index}/tag{f.tag}"
            out += _func_constants(eb.data, f.abs_start, min(f.abs_end, len(eb.data)), ctx)
    return out


def apply_ai_patches(eb_bytes: bytes, patches) -> tuple[bytes, list]:
    """Apply ``[{at, old, new}, ...]`` same-length constant patches to ``eb_bytes``. Each ``at`` must be a real
    constant site whose current value == ``old`` (the guard) and whose width fits ``new``. Returns (patched, warns).
    Raises AiPatchError on a bad offset / old-mismatch / width-overflow -- so a wrong patch fails the build, never
    the game."""
    if not isinstance(patches, list):
        raise AiPatchError("[[scene.ai_patch]] must be a list of tables")
    sites = {s.offset: s for s in constant_sites(eb_bytes)}
    b = bytearray(eb_bytes)
    warnings: list = []
    seen: dict = {}
    for n, p in enumerate(patches):
        if not isinstance(p, dict):
            raise AiPatchError(f"[[scene.ai_patch]] #{n} must be a table (got {type(p).__name__})")
        at, old, new = p.get("at"), p.get("old"), p.get("new")
        for k, v in (("at", at), ("old", old), ("new", new)):
            if not isinstance(v, int) or isinstance(v, bool):
                raise AiPatchError(f"[[scene.ai_patch]] #{n} needs integer {k} (at = offset, old/new = values)")
        if at in seen:
            warnings.append(f"[[scene.ai_patch]] #{n} and #{seen[at]} both patch offset {at} -- the later wins")
        seen[at] = n
        site = sites.get(at)
        if site is None:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: no patchable constant at offset {at} "
                               f"(cite an offset from `battle-ai --sites`)")
        if site.value != old:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: expected old = {old} at offset {at}, but the eb has "
                               f"{site.value} ({site.where}) -- wrong offset, or already patched?")
        if not 0 <= new <= site.vmax:                    # site.vmax handles ANY width + the B_CONST4 26-bit mask
            note = " (the engine masks this B_CONST4 literal to 26 bits)" if site.vmax == 0x3FFFFFF else ""
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: new = {new} does not fit the {site.width}-byte constant "
                               f"at offset {at} (0-{site.vmax}){note} -- a same-length patch can't widen it")
        for k in range(site.width):                      # little-endian, generic width (1/2/3/4) -> no struct map
            b[at + k] = (new >> (8 * k)) & 0xFF
    return bytes(b), warnings


def validate_patches(eb_bytes: bytes, patches) -> list:
    """Offline problems (empty => OK): re-run the patch on a copy and surface any AiPatchError as a message."""
    try:
        apply_ai_patches(eb_bytes, patches)
        return []
    except AiPatchError as ex:
        return [str(ex)]
