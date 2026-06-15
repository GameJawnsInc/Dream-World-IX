"""Phase-2: in-place, length-preserving, GUARDED value edits on a verbatim fork's ``.eb`` (+ ``.mes`` text).

The write-side sibling of :mod:`ff9mapkit.logic_map` (read) and :mod:`ff9mapkit.eblint` (validate): a verbatim
fork ships the donor's whole compiled ``.eb``, and this lets you EDIT it IN PLACE -- change an item reward, a gil
amount, a ``Field()`` warp destination, a story-flag index, a dialogue txid, or rewrite a dialogue STRING -- WITHOUT
regenerating or splicing the script (that's Phase 4). Every ``.eb`` edit is strictly LENGTH-PRESERVING (a same-width
operand overwrite), so the entry table / fpos never move; the composed ``.eb`` is re-validated by the Phase-3 linter
(:func:`ff9mapkit.eblint.lint_eb`) before the build ships it. Each edit is **old-guarded**: it locates its site by
``entry``/``tag``/``op`` AND the current value, and REFUSES (a clean ``LogicEditError`` -> build failure, never a
silent mis-patch) if the donor bytes drifted. Authored declaratively as ``[[logic_edit]]`` in the member field.toml;
applied in build's verbatim pass (CLAUDE.md / docs/FORK_FIDELITY.md). Empty list -> byte-identical no-op.

v1 kinds: ``field`` (0x2B dest) · ``item`` (0x48 id/count) · ``gil`` (0xCE amount) · ``txid`` (a Window op's text id)
· ``flag_index`` (the GLOB ``C4``/``E4`` index inside an 0x05 expression, width-class-preserving) · ``text`` (a
``.mes`` dialogue-string rewrite, the only non-length-preserving kind -- it targets the per-language ``.mes``, not the
``.eb``). Deferred: ``switch_case`` (a switch's case value) and cross-0xFF flag remaps (a length change = Phase 4).

The ``.eb`` bytecode is language-identical (only the 84-byte name differs), so one edit set patches all 7 langs.
"""
from __future__ import annotations

import re
import struct

from .eb import disasm
from .eb.model import EbScript
from .content.object import _arg_byte_offset

ITEM_OP = 0x48          # AddItem(item_id:u16, count:u8)
GIL_OP = 0xCE           # AddGil(amount:u24)
FIELD_OP = 0x2B         # Field(dest:u16)
EXPR_OP = 0x05          # an expression statement (a GLOB flag read/write rides here)
WINDOW_OPS = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}   # Window op -> its txid operand index (dialogue.WINDOW_OPS)
_ITEM_OPERAND = {"id": 0, "count": 1}
_EB_KINDS = ("field", "item", "gil", "txid", "flag_index", "operand")
_TAIL_RE = re.compile(r"\[TAIL=([^\]]*)\]")


class LogicEditError(ValueError):
    """A logic-edit that can't be applied safely (bad address, drifted donor, overflow, unsupported) -- it
    fails the BUILD, never silently mis-patches the shipped script."""


def _req(ed, key):
    if key not in ed:
        raise LogicEditError(f"logic_edit ({ed.get('kind', '?')}) missing required key '{key}'")
    return ed[key]


def _int(ed, key, *, optional=False):
    """Require ``key`` be a plain int (TOML floats/strings/bools are author mistakes -> a clean LogicEditError,
    not a raw TypeError). ``optional`` returns None when the key is absent."""
    if optional and key not in ed:
        return None
    v = _req(ed, key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise LogicEditError(f"logic_edit ({ed.get('kind', '?')}) key '{key}' must be an integer, "
                             f"got {type(v).__name__} ({v!r})")
    return v


def _func(eb, ed):
    entry, tag = _int(ed, "entry"), _int(ed, "tag")
    if not (0 <= entry < eb.entry_count):
        raise LogicEditError(f"logic_edit entry {entry} out of range (0..{eb.entry_count - 1})")
    e = eb.entry(entry)
    if e.empty:
        raise LogicEditError(f"logic_edit entry {entry} is an empty slot")
    f = e.func_by_tag(tag)
    if f is None:
        raise LogicEditError(f"logic_edit entry {entry} has no function tag {tag}")
    return f


def _pick(hits, ed, what):
    """Choose among instrs already filtered to match the old value: exactly one, or ``nth`` to disambiguate."""
    if not hits:
        raise LogicEditError(f"logic_edit found no {what} (the donor drifted or the address is wrong)")
    if len(hits) == 1:
        return hits[0]
    nth = _int(ed, "nth", optional=True)
    if nth is None:
        raise LogicEditError(f"logic_edit is ambiguous: {len(hits)} {what} -- add `nth` (0..{len(hits) - 1})")
    if not (0 <= nth < len(hits)):
        raise LogicEditError(f"logic_edit nth={nth} out of range (0..{len(hits) - 1}) for {what}")
    return hits[nth]


def _guarded_write(buf, abs_off, w, old, new):
    """Overwrite ``w`` bytes at ``abs_off`` IN PLACE, asserting the current bytes encode ``old`` first (a real
    guard that also catches an offset miscalculation). ``new`` must fit ``w`` bytes."""
    if not (0 <= new < (1 << (8 * w))):
        raise LogicEditError(f"logic_edit new value {new} doesn't fit a {w}-byte operand")
    expect = old.to_bytes(w, "little")
    cur = bytes(buf[abs_off:abs_off + w])
    if cur != expect:
        raise LogicEditError(f"logic_edit guard @{abs_off}: expected {expect.hex()} got {cur.hex()} "
                             "(donor drift or a bad address)")
    buf[abs_off:abs_off + w] = new.to_bytes(w, "little")


def _operand_edit(eb, buf, ed, op, operand_index):
    """Locate an instr (op, current operand == old) in entry/tag and overwrite that operand same-width."""
    f = _func(eb, ed)
    old, new = _int(ed, "old"), _int(ed, "new")
    hits = [i for i in eb.instrs(f) if i.op == op and i.imm(operand_index) == old]
    ins = _pick(hits, ed, f"{disasm.op_name(op)} with operand[{operand_index}]=={old} in "
                          f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    bo = _arg_byte_offset(ins, operand_index)
    if bo is None:
        raise LogicEditError(f"logic_edit cannot address {disasm.op_name(op)} operand {operand_index} "
                             "(a preceding operand is an expression)")
    _guarded_write(buf, ins.off + bo, disasm.argsize(op, operand_index), old, new)


def _flag_edit(eb, buf, ed):
    """Remap a GLOB story-flag index inside an 0x05 expression (the C4/E4 var token) -- width-class-preserving."""
    from .eventscan import _glob_var_token
    f = _func(eb, ed)
    old, new = _int(ed, "flag"), _int(ed, "new_flag")
    hits = []
    for i in eb.instrs(f):
        if i.op != EXPR_OP:
            continue
        tok = _glob_var_token(eb.data, i.off + 1)             # the var token sits right after the 0x05
        if tok is not None and tok[0] == old:
            hits.append((i, tok))
    pair = _pick(hits, ed, f"GLOB flag {old} read/write in entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    ins, (idx, tok_len) = pair
    idx_w = tok_len - 1                                        # C4 -> 1-byte index, E4 -> 2-byte index
    new_w = 1 if new <= 0xFF else 2
    if new_w != idx_w:
        raise LogicEditError(f"logic_edit flag remap {old}->{new} crosses the 0xFF C4/E4 token boundary "
                             "(a length change) -- not supported in the in-place tier (Phase 4)")
    _guarded_write(buf, ins.off + 2, idx_w, old, new)         # 0x05 at off, token byte at off+1, index at off+2


def _apply_eb_edit(eb, buf, ed):
    kind = _req(ed, "kind")
    if kind == "field":
        _operand_edit(eb, buf, ed, FIELD_OP, 0)
    elif kind == "item":
        _operand_edit(eb, buf, ed, ITEM_OP, _ITEM_OPERAND.get(ed.get("operand", "id"), 0))
    elif kind == "gil":
        _operand_edit(eb, buf, ed, GIL_OP, 0)
    elif kind == "txid":
        op = _int(ed, "op")
        if op not in WINDOW_OPS:
            raise LogicEditError(f"logic_edit txid op {op:#x} is not a Window op {sorted(WINDOW_OPS)}")
        _operand_edit(eb, buf, ed, op, WINDOW_OPS[op])
    elif kind == "flag_index":
        _flag_edit(eb, buf, ed)
    elif kind == "operand":                                  # generic escape hatch: patch literal operand
        _operand_edit(eb, buf, ed, _int(ed, "op"), _int(ed, "operand"))   # `operand` of any op (e.g. the
        #   item id a SetTextVariable(0x66) feeds the "Received <item>!" message -- the DISPLAY half of a
        #   reward, separate from the AddItem that GIVES it; both must change to fully retarget a chest)
    else:
        raise LogicEditError(f"logic_edit unknown .eb kind '{kind}' (kinds: {_EB_KINDS} + 'text')")


def apply_logic_edits(eb_bytes, edits) -> bytes:
    """Apply every NON-text ``[[logic_edit]]`` to ``eb_bytes`` in place (length-preserving, old-guarded) and
    return the patched bytes. Empty / text-only -> byte-identical. Raises :class:`LogicEditError` on any unsafe
    edit (bad address, drift, overflow, unsupported)."""
    eb_edits = [e for e in (edits or []) if e.get("kind") != "text"]
    if not eb_edits:
        return bytes(eb_bytes)
    eb = EbScript.from_bytes(eb_bytes)
    buf = bytearray(eb_bytes)
    for ed in eb_edits:
        _apply_eb_edit(eb, buf, ed)
    return bytes(buf)


# --- .mes dialogue-string rewrite (kind="text") -- a verified in-place splice, per language ----------
def _splice_block(part: str, new_text: str) -> str:
    """Replace the text payload of one ``[STRT=...]...[ENDN]`` block (a ``[STRT=``-split segment), preserving
    its STRT geometry, optional [TAIL], the [ENDN], and any trailing bytes before the next entry."""
    b = part.find("]")
    if b < 0:
        raise LogicEditError("malformed .mes entry (no STRT close)")
    rest = part[b + 1:]
    mt = _TAIL_RE.match(rest)
    tail_str = mt.group(0) if mt else ""
    endn = part.find("[ENDN]", b + 1 + len(tail_str))
    if endn < 0:
        raise LogicEditError("malformed .mes entry (no [ENDN])")
    return part[:b + 1] + tail_str + new_text + part[endn:]


def apply_logic_text_edits(body: str, edits, lang: str) -> str:
    """Apply every ``kind="text"`` edit whose ``lang`` is unset or == ``lang`` to a ``.mes`` body, returning the
    rewritten body. A VERIFIED in-place splice: it replaces one entry's text payload, then re-parses and asserts
    every OTHER entry is byte-identical (so a botched splice fails the build, not the player). v1 supports the
    index-implicit verbatim donor body (no ``[TXID=]`` re-index markers)."""
    text_edits = [e for e in (edits or []) if e.get("kind") == "text" and e.get("lang") in (None, lang)]
    if not text_edits or not body:
        return body
    from .dialogue import parse_mes, strip_tags
    if "[TXID=" in body:
        raise LogicEditError("logic_edit text rewrite on a [TXID=]-reindexed .mes is not supported (Phase 2b)")
    for ed in text_edits:
        txid, old, new = _int(ed, "txid"), _req(ed, "old"), _req(ed, "new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise LogicEditError(f"logic_edit text txid {txid}: 'old' and 'new' must be strings")
        before = parse_mes(body)
        ent = before.get(txid)
        if ent is None:
            raise LogicEditError(f"logic_edit text: txid {txid} not found in the {lang} .mes")
        if old not in (ent.text, strip_tags(ent.text)):
            raise LogicEditError(f"logic_edit text txid {txid} ({lang}): current line != `old` (donor drifted)")
        parts = body.split("[STRT=")
        if not (0 <= txid + 1 < len(parts)):                  # index-implicit: txid == position == part index-1
            raise LogicEditError(f"logic_edit text: txid {txid} out of range in the {lang} .mes")
        parts[txid + 1] = _splice_block(parts[txid + 1], new)
        spliced = "[STRT=".join(parts)
        after = parse_mes(spliced)                            # VERIFY: only the target entry changed
        if len(after) != len(before):
            raise LogicEditError(f"logic_edit text splice changed the .mes entry count ({lang})")
        for t, e in before.items():
            got = after.get(t)
            if got is None:
                raise LogicEditError(f"logic_edit text splice dropped txid {t} ({lang})")
            if t == txid:
                if got.text != new:
                    raise LogicEditError(f"logic_edit text splice didn't take for txid {txid} ({lang})")
            elif (got.text, got.strt, got.tail) != (e.text, e.strt, e.tail):
                raise LogicEditError(f"logic_edit text splice corrupted txid {t} ({lang})")
        body = spliced
    return body
