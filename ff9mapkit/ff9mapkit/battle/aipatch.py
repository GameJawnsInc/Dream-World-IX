"""Phase-6b: SAME-LENGTH enemy-AI constant patches -- the first AI *authoring* step (read = Phase-6a `battleai`).

An enemy's AI is the per-scene ``EVT_BATTLE_*.eb`` bytecode. The safest authoring edit is a *literal* one: change
a numeric CONSTANT in place without moving any bytes -- an HP threshold a phase-switch compares (``B_CONST`` in
an expression), the attack index a turn selects (a ``BTLCMD`` immediate), a ``Wait`` count. No length change means
no ``fpos``/entry-table fixup and no risk of mis-packing -- byte-accurate by construction (the eb-codec identity
holds), exactly like ``scene_data``'s surgical raw16 patch.

The author CITES a constant by its byte offset in the us donor (``battle-ai --sites``) + a required OLD-value guard,
and ``new`` must fit the SAME byte width. The offset is only a citation: it resolves once, on that reference eb, to
a STRUCTURAL anchor -- entry, function tag, instruction ordinal, constant ordinal within the instruction
(:class:`Anchor`) -- and every eb the patch lands in is located by that anchor, never by the offset.

A battle eb's bytecode is NOT language-identical. 521 of the 562 stock scenes match with the 84-byte name field
masked; the other 41 differ in LENGTH (35 jp-only, 5 all six non-us, 1 European-only), in AI entries 0-3, around
``BattleDialog``/``SET``/``Wait``/jumps. There the same absolute offset carries 9,517 of the 25,521 us-site/language
pairs -- 155 of them onto a DIFFERENT constant that happens to hold the same value -- and refuses the rest. So each
language's function is matched against the reference's (:func:`correspond`): instructions compare modulo their
literal values, matched as a common prefix + suffix, and every matched jump or switch must land alike. A constant in
the unmatched middle, or whose counterpart holds another value, is REFUSED for that language. Measured over the
install: 21,181 of the 25,521 pairs patch, every one at the instruction a stricter alignment (literals compared,
only jump offsets masked) also picks; the 155 are refused or moved to their real counterpart. 433 pairs the offset
carried are now refused as unprovable: 432 in the four ``WM_99xx`` scenes, whose other languages merge two us dialog
blocks into one, and one whose jp expression differs around the constant.

This reaches NUMERIC LITERALS only (command immediates + ``B_CONST``/``B_CONST4`` expression literals) -- the
"same-length literal patch" tier. Structural AI changes (new branches, an expression assembler, retargeting which
variable is read) are Phase-6c. Read-the-AI-first is mandatory: there is no semantic search; you cite the offset
the disassembler prints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

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


@dataclass(frozen=True)
class Anchor:
    """Where a cited constant lives STRUCTURALLY -- the address that carries across languages and length edits."""
    entry: int
    tag: int
    instr: int         # ordinal of the instruction within the function
    slot: int          # ordinal of the constant among that instruction's constants
    site: Site         # the constant in the reference eb (its offset is the citation)


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
        if o == 0xD3:                                   # flexible_varfunc: u16 id + u8 argc (NOT a literal); the
            pos += 3                                    # engine carves it out of the var space before the var test
            continue
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


def _parse(eb_bytes: bytes) -> EbScript:
    try:                                                 # a truncated/corrupt eb (e.g. a bad funcCount) can index
        return EbScript.from_bytes(eb_bytes)             # past the buffer during parse -> raise a CLEAN error, not
    except (ValueError, IndexError) as ex:               # a raw IndexError (mirrors battleai.disassemble_ai)
        raise AiPatchError(f"malformed/truncated AI .eb: {type(ex).__name__}: {ex}")


def constant_sites(eb_bytes: bytes) -> list:
    """Every patchable numeric constant in a battle ``.eb``'s AI, in byte order. The ``offset`` of each is the
    ``at`` you cite in an ``[[scene.ai_patch]]``; the disassembler (``battle-ai --sites``) prints them."""
    eb = _parse(eb_bytes)
    out = []
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            ctx = f"entry{e.index}/tag{f.tag}"
            out += _func_constants(eb.data, f.abs_start, min(f.abs_end, len(eb.data)), ctx)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Structural correspondence: which instruction of another eb's function IS a given instruction of the reference's.
# ---------------------------------------------------------------------------------------------------------------

class Row(NamedTuple):
    """One decoded instruction of a function, with its constants and its SHAPE modulo their values."""
    ins: _disasm.Instr
    sites: tuple       # the instruction's constants (Site), in byte order
    skel: tuple        # (instruction bytes with every constant zeroed, ((rel offset, width), ...))


def func_rows(eb: EbScript, entry: int, tag: int) -> list | None:
    """``[Row, ...]`` for function ``(entry, tag)`` of ``eb``, or None when the entry is absent/empty or lacks it.
    Two instructions with equal ``skel`` are the same command reading the same variables with the same operator
    stream -- they may differ only in literal values (a text id, a Wait count, a jump offset)."""
    if not 0 <= entry < len(eb.entries) or eb.entries[entry].empty:
        return None
    f = eb.entries[entry].func_by_tag(tag)
    if f is None:
        return None
    data = eb.data
    ctx = f"entry{entry}/tag{tag}"
    rows = []
    for ins in _disasm.iter_code(data, f.abs_start, min(f.abs_end, len(data))):
        sites = tuple(_func_constants(data, ins.off, ins.end, ctx))
        masked = bytearray(data[ins.off:ins.end])
        for s in sites:
            masked[s.offset - ins.off:s.offset - ins.off + s.width] = bytes(s.width)
        rows.append(Row(ins, sites, (bytes(masked), tuple((s.offset - ins.off, s.width) for s in sites))))
    return rows


def _targets(rows: list) -> list:
    """Per instruction: the row indices it can jump to (``len(rows)`` = the function's end; None = no instruction
    starts there), or None when it is not a jump / switch."""
    index = {r.ins.off: k for k, r in enumerate(rows)}
    if rows:
        index[rows[-1].ins.end] = len(rows)
    out = []
    for r in rows:
        offs = None
        if r.ins.op in _disasm.JUMP_OPS:
            t = _disasm.jump_target(r.ins)
            offs = None if t is None else [t]
        elif r.ins.op in _disasm.SWITCH_OPS:
            sw = _disasm.decode_switch(r.ins)
            offs = None if sw is None else [e.target for e in sw.edges]
        out.append(None if offs is None else [index.get(o) for o in offs])
    return out


def correspond(ref: list, tgt: list) -> list:
    """For each instruction of ``ref`` (a :func:`func_rows` list), the index of the SAME instruction in ``tgt``, or
    None where there is no provable counterpart.

    Instructions match when their shapes (``Row.skel``) are equal. The matched part is a common prefix plus a
    common suffix, the middle unmatched -- and only the positions EVERY such alignment agrees on: when the longest
    prefix and suffix overlap on either side (the length difference sits inside a repeated run), the overlap could
    belong to either and stays unmatched. Every matched jump or switch must then land on the matched target, or,
    on both sides, inside the differing middle or on the first instruction after it (an insertion at a join point
    moves one side's landing onto the new code). Any other landing means the two are not the same jump -- the
    edit starts there -- so the matched region is cut back to exclude it (and re-checked). Identical functions
    map one to one."""
    su, st = [r.skel for r in ref], [r.skel for r in tgt]
    nu, nt = len(su), len(st)
    d = nt - nu
    p = 0
    while p < min(nu, nt) and su[p] == st[p]:
        p += 1
    s = 0
    while s < min(nu, nt) and su[nu - 1 - s] == st[nt - 1 - s]:
        s += 1
    if d:                                           # a prefix of a + suffix of b needs a + b <= the shorter length;
        k = min(nu, nt, p + s)                      # the sure part is what every maximal (a, b) covers
        p, s = k - s, k - p

    def m(i):
        if i is None:
            return None
        if i == nu:
            return nt
        return i if i < p else (i + d if i >= nu - s else None)

    def lands_alike(a, b) -> bool:
        if a is None or b is None:                  # a jump into the middle of an instruction, or out of the function
            return False
        if p <= a <= nu - s and p <= b <= nt - s:   # both in the differing middle (or right after it)
            return True
        return m(a) == b

    jumps_ref, jumps_tgt = _targets(ref), _targets(tgt)
    while True:
        bad = None
        for i in range(nu):
            j = m(i)
            if j is None or jumps_ref[i] is None:
                continue
            tu, tt = jumps_ref[i], jumps_tgt[j]
            if tt is None or len(tt) != len(tu) or not all(lands_alike(a, b) for a, b in zip(tu, tt)):
                bad = i
                break
        if bad is None:
            return [m(i) for i in range(nu)]
        if bad < p:
            p = bad
        if bad >= nu - s:
            s = nu - 1 - bad


# ---------------------------------------------------------------------------------------------------------------
# The patch: cite (on the reference) -> anchor -> locate (on each eb) -> guard -> write.
# ---------------------------------------------------------------------------------------------------------------

def anchor_at(ref_bytes: bytes, at: int) -> Anchor | None:
    """The structural :class:`Anchor` of the constant whose first byte is at ``at`` in ``ref_bytes``, or None."""
    eb = _parse(ref_bytes)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            if not f.abs_start <= at < f.abs_end:
                continue
            for k, row in enumerate(func_rows(eb, e.index, f.tag) or ()):
                for q, site in enumerate(row.sites):
                    if site.offset == at:
                        return Anchor(e.index, f.tag, k, q, site)
    return None


def locate(anchor: Anchor, ref_bytes: bytes, eb_bytes: bytes) -> tuple:
    """``(site, why)``: ``anchor``'s constant in ``eb_bytes`` (its function matched against ``ref_bytes``'s by
    :func:`correspond`), or ``(None, reason)`` when that eb has no provable counterpart."""
    rows_ref = func_rows(_parse(ref_bytes), anchor.entry, anchor.tag)
    rows = func_rows(_parse(eb_bytes), anchor.entry, anchor.tag)
    if rows is None:
        return None, f"it has no entry {anchor.entry} tag {anchor.tag}"
    j = correspond(rows_ref, rows)[anchor.instr]
    if j is None:
        return None, (f"entry {anchor.entry} tag {anchor.tag} differs there around this constant ("
                      f"{len(rows)} instructions vs {len(rows_ref)}), so it has no provable counterpart")
    return rows[j].sites[anchor.slot], ""


def apply_ai_patches(eb_bytes: bytes, patches, *, ref: bytes | None = None, lang: str | None = None) -> tuple:
    """Apply ``[{at, old, new}, ...]`` same-length constant patches to ``eb_bytes``. Returns (patched, warns).

    ``at`` is a constant's offset in ``ref`` -- the eb the author cited it from (the us donor, ``battle-ai
    --sites``); None means ``eb_bytes`` itself. It resolves to an :class:`Anchor` on ``ref``, which is located in
    ``eb_bytes`` structurally (:func:`locate`), so another language's eb or one a length edit already shifted is
    patched at the SAME constant, never at the same offset. Raises AiPatchError on a bad citation, an
    old-mismatch, a width-overflow, or (``lang`` names the eb) a constant with no counterpart there -- so a wrong
    patch fails the build, never the game."""
    if not isinstance(patches, list):
        raise AiPatchError("[[scene.ai_patch]] must be a list of tables")
    ref = eb_bytes if ref is None else ref
    in_lang = f" in {lang}'s battle script" if lang else ""
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
        anchor = anchor_at(ref, at)
        if anchor is None:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: no patchable constant at offset {at} "
                               f"(cite an offset from `battle-ai --sites`)")
        if anchor.site.value != old:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: expected old = {old} at offset {at}, but the eb has "
                               f"{anchor.site.value} ({anchor.site.where}) -- wrong offset, or already patched?")
        site, why = (anchor.site, "") if ref is eb_bytes else locate(anchor, ref, eb_bytes)
        if site is None:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: the constant at offset {at} ({anchor.site.where}) cannot "
                               f"be patched{in_lang}: {why}. Patching the same offset there would hit whatever "
                               f"constant sits at it; cite a constant outside the differing stretch")
        if site.value != old:
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: the constant at offset {at} ({anchor.site.where}) holds "
                               f"{site.value}{in_lang}, not {old} -- that language's script differs here")
        if not 0 <= new <= site.vmax:                    # site.vmax handles ANY width + the B_CONST4 26-bit mask
            note = " (the engine masks this B_CONST4 literal to 26 bits)" if site.vmax == 0x3FFFFFF else ""
            raise AiPatchError(f"[[scene.ai_patch]] #{n}: new = {new} does not fit the {site.width}-byte constant "
                               f"at offset {at} (0-{site.vmax}){note} -- a same-length patch can't widen it")
        for k in range(site.width):                      # little-endian, generic width (1/2/3/4) -> no struct map
            b[site.offset + k] = (new >> (8 * k)) & 0xFF
    return bytes(b), warnings


def validate_patches(eb_bytes: bytes, patches, *, ref: bytes | None = None, lang: str | None = None) -> list:
    """Offline problems (empty => OK): re-run the patch on a copy and surface any AiPatchError as a message."""
    try:
        apply_ai_patches(eb_bytes, patches, ref=ref, lang=lang)
        return []
    except AiPatchError as ex:
        return [str(ex)]
