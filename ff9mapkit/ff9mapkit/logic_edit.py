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
· ``flag_index`` (the GLOB ``C4``/``E4`` index inside an 0x05 expression -- a same-width remap is an in-place
operand swap; a remap that CROSSES the 0xFF C4/E4 token boundary is length-changing and rebuilt via the Phase-4b
keystone) · ``switch_case`` (REDIRECT one case/default arm of a jump table 0x06/0x0B/0x0D to a different
in-function target -- re-wire which branch a dialogue-menu row / ATE / scenario value triggers; keystone rebuild,
length-neutral) · ``text`` (a ``.mes`` dialogue-string rewrite, targets the per-language ``.mes``, not the
``.eb``). Deferred: ADDING a switch case (a new menu row / dispatch arm -- length-changing, a logic_add follow-up).

The ``.eb`` bytecode is language-identical (only the 84-byte name differs), so one edit set patches all 7 langs.
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field as _dc_field

from .eb import disasm
from .eb.model import EbScript
from .content.object import _arg_byte_offset

ITEM_OP = 0x48          # AddItem(item_id:u16, count:u8)
GIL_OP = 0xCE           # AddGil(amount:u24)
FIELD_OP = 0x2B         # Field(dest:u16)
EXPR_OP = 0x05          # an expression statement (a GLOB flag read/write rides here)
SETTEXTVAR_OP = 0x66    # SetTextVariable(slot:u8, value:u16) -- feeds the "Received <item>!" DISPLAY id
WINDOW_OPS = {0x1F: 2, 0x20: 2, 0x95: 3, 0x96: 3}   # Window op -> its txid operand index (dialogue.WINDOW_OPS)
_ITEM_OPERAND = {"id": 0, "count": 1}
_EB_KINDS = ("field", "item", "gil", "txid", "flag_index", "operand", "item_display", "item_count", "switch_case")
_SWITCH_OPS = (0x06, 0x0B, 0x0D)        # JMP_SWITCHEX (explicit) / JMP_SWITCH (contiguous) / 2-byte-count variant
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


def _operand_edit(eb, buf, ed, op, operand_index, *, extra=None, what=None):
    """Locate an instr (op, current operand == old, + an optional ``extra(ins)`` guard) in entry/tag and
    overwrite that operand same-width. ``extra`` lets a kind pin a SECOND operand (e.g. the item-display
    text slot) so the value-filtered nth matches discovery -- without it, an unrelated same-value instr
    could be mis-targeted."""
    f = _func(eb, ed)
    old, new = _int(ed, "old"), _int(ed, "new")
    hits = [i for i in eb.instrs(f) if i.op == op and i.imm(operand_index) == old and (extra is None or extra(i))]
    ins = _pick(hits, ed, what or (f"{disasm.op_name(op)} with operand[{operand_index}]=={old} in "
                                   f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}"))
    bo = _arg_byte_offset(ins, operand_index)
    if bo is None:
        raise LogicEditError(f"logic_edit cannot address {disasm.op_name(op)} operand {operand_index} "
                             "(a preceding operand is an expression)")
    _guarded_write(buf, ins.off + bo, disasm.argsize(op, operand_index), old, new)


def _flag_width(idx: int) -> int:
    """The GLOB var token's index width in BYTES: 1 for ``idx <= 0xFF`` (the C4 short token), 2 for the E4 long
    token. The engine reads the token byte to know the width, so a remap crossing 0xFF changes BOTH the token
    byte and its length -- a length-changing edit (the keystone rebuild), not an in-place same-width swap."""
    return 1 if idx <= 0xFF else 2


def _flag_locate(eb, ed):
    """Find the 0x05 expression instruction that reads/writes GLOB flag ``ed['flag']`` (disambiguated by
    ``nth``); return ``(ins, idx, tok_len, old, new)``. Shared by the in-place and re-width flag paths so they
    locate IDENTICALLY. Raises on an out-of-range target or a flag that isn't found (donor drift / bad addr)."""
    from .eventscan import _glob_var_token
    f = _func(eb, ed)
    old, new = _int(ed, "flag"), _int(ed, "new_flag")
    if not (0 <= new <= 0xFFFF):
        raise LogicEditError(f"logic_edit flag remap target {new} out of range (0-65535)")
    hits = []
    for i in eb.instrs(f):
        if i.op != EXPR_OP:
            continue
        tok = _glob_var_token(eb.data, i.off + 1)             # the var token sits right after the 0x05
        if tok is not None and tok[0] == old:
            hits.append((i, tok))
    ins, (idx, tok_len) = _pick(hits, ed, f"GLOB flag {old} read/write in "
                                f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    return ins, idx, tok_len, old, new


def _flag_edit(eb, buf, ed):
    """In-place (length-preserving) GLOB story-flag index remap inside an 0x05 expression -- ONLY when the new
    index stays in the SAME C4/E4 width class. A cross-0xFF remap is length-changing and routed to
    :func:`_flag_rewidth` by :func:`apply_logic_edits`; this raises if one somehow reaches the in-place path."""
    ins, idx, tok_len, old, new = _flag_locate(eb, ed)
    if _flag_width(new) != (tok_len - 1):                     # C4 -> 1-byte index, E4 -> 2-byte index
        raise LogicEditError(f"internal: cross-0xFF flag remap {old}->{new} must use the re-width pass")
    _guarded_write(buf, ins.off + 2, tok_len - 1, old, new)   # 0x05 at off, token byte at off+1, index at off+2


def _flag_rewidth(eb_bytes, ed, anchor_rel, old, new) -> bytes:
    """A cross-0xFF GLOB flag remap (length-CHANGING: the C4 short token <-> the E4 long token), applied at the
    EXACT instruction located during the split (``anchor_rel`` is its function-relative offset, captured before
    the in-place pass and adjusted for any prior same-function rebuild). Rewrite that 0x05 expression's
    ``Global.Bit[old]`` token to ``Global.Bit[new]`` in the disassembled function SOURCE and reassemble via the
    keystone (``exprasm`` picks the new index's natural width; ``cmdasm`` relocates every jump/switch past the
    length change), then swap the rebuilt body in. Old-guarded: it asserts the byte at ``anchor_rel`` is still a
    0x05 reading ``old`` (so conflicting edits that drifted the site fail cleanly, never silently mis-patch)."""
    from .eb import cmdasm as _cmdasm
    from .eb import edit as _edit
    from .eb import exprasm as _exprasm
    from .eb._exprtable import decode_var
    from .eventscan import _glob_var_token, GLOB_BOOL_SHORT, GLOB_BOOL_LONG
    eb = EbScript.from_bytes(eb_bytes)
    f = _func(eb, ed)
    abs_off = f.abs_start + anchor_rel
    tok = _glob_var_token(eb.data, abs_off + 1) if (0 <= abs_off < len(eb.data) and eb.data[abs_off] == EXPR_OP) else None
    if tok is None or tok[0] != old:                          # the captured site no longer holds the old flag
        raise LogicEditError(f"logic_edit flag remap {old}->{new}: the target 0x05 expression in "
                             f"entry{_int(ed, 'entry')}/tag{_int(ed, 'tag')} drifted (conflicting edits?)")
    old_tok = decode_var(GLOB_BOOL_SHORT if old <= 0xFF else GLOB_BOOL_LONG, old)   # "Global.Bit[old]"
    new_tok = decode_var(GLOB_BOOL_SHORT if new <= 0xFF else GLOB_BOOL_LONG, new)   # "Global.Bit[new]"
    try:
        items = _cmdasm.disassemble_items(eb.data, f.abs_start, f.abs_end)
        line_idx = next((k for k, (off, _t) in enumerate(items) if off == anchor_rel), None)
        if line_idx is None:                                  # the guarded instr is decoded -> always present
            raise LogicEditError("logic_edit flag remap: could not locate the expression instruction (internal)")
        _off, text = items[line_idx]
        if old_tok not in text:                               # second guard: the decoded expr must show the old flag
            raise LogicEditError(f"logic_edit flag remap: {old_tok} not in the decoded expression ({text})")
        texts = [t for _o, t in items]
        texts[line_idx] = text.replace(old_tok, new_tok)
        new_body = _cmdasm.assemble_block("\n".join(texts))
    except (_cmdasm.CmdAsmError, _exprasm.AssembleError) as ex:   # normalize the rebuild failure (clean build error)
        raise LogicEditError(f"logic_edit flag remap {old}->{new}: could not rebuild "
                             f"entry{_int(ed, 'entry')}/tag{_int(ed, 'tag')}: {ex}")
    return _edit.replace_function_body(eb_bytes, _int(ed, "entry"), _int(ed, "tag"), new_body)


# --- switch_case: REDIRECT a jump-table arm (0x06/0x0B/0x0D) to a different in-function target -------------
def _switch_case_key(ed):
    """The selector an edit targets: an int case VALUE, or the string ``"default"``."""
    case = ed.get("case")
    if case == "default":
        return "default"
    if isinstance(case, bool) or not isinstance(case, int):
        raise LogicEditError('logic_edit switch_case needs `case` = an integer selector value or "default"')
    return case


def _switch_locate(eb, ed):
    """Find the switch instruction + the edge for ``case`` in entry/tag; return ``(ins, anchor_rel, case,
    old_target)``. Disambiguate among multiple switches with ``nth``. Guard: the selected edge currently
    resolves to ``ed['old_target']`` (a function-relative offset) -- a wrong old_target / drifted donor fails."""
    f = _func(eb, ed)
    case = _switch_case_key(ed)
    old_target = _int(ed, "old_target")
    switches = [i for i in eb.instrs(f) if i.op in _SWITCH_OPS]
    if not switches:
        raise LogicEditError(f"logic_edit switch_case: no switch (0x06/0x0B/0x0D) in "
                             f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    ins = _pick(switches, ed, f"switch instruction in entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    si = disasm.decode_switch(ins)
    if si is None:                                             # a switch whose operands aren't plain immediates
        raise LogicEditError(f"logic_edit switch_case: could not decode the switch in "
                             f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')} (computed operands?)")
    if case == "default":
        edge = next((e for e in si.edges if e.is_default), None)
    else:
        edge = next((e for e in si.edges if not e.is_default and e.value == case), None)
    if edge is None:
        raise LogicEditError(f"logic_edit switch_case: no case {case} in the switch "
                             f"(values: {[e.value for e in si.edges if not e.is_default]})")
    cur = edge.target - f.abs_start
    if cur != old_target:
        raise LogicEditError(f"logic_edit switch_case guard: case {case} currently targets {cur}, not "
                             f"old_target {old_target} (donor drift or wrong old_target)")
    return ins, ins.off - f.abs_start, case, old_target


def _switch_operand_index(op, ops, case):
    """The index in the cmdasm SWITCH/SWITCHEX operand list of the LABEL operand for ``case``.
    0x0B/0x0D: ``[base, default, case0, case1, ...]`` (case i is selector base+i). 0x06: ``[default, val0,
    lbl0, val1, lbl1, ...]`` (explicit values)."""
    if op in (0x0B, 0x0D):                                      # SWITCH(base, default, case0, case1, ...)
        if case == "default":
            return 1
        try:
            base = disasm._sx_hi(int(ops[0]) & 0xFFFF)         # cmdasm re-emits the base as RAW u16: a negative
        except (ValueError, IndexError):                       # base (-1) shows as "65535" -> sign-decode it
            raise LogicEditError("logic_edit switch_case: malformed SWITCH operands (internal)")
        i = case - base
        if not (0 <= i < len(ops) - 2):
            raise LogicEditError(f"logic_edit switch_case: selector {case} is outside the contiguous range "
                                 f"{base}..{base + len(ops) - 3} of this SWITCH (only those cases or "
                                 '"default" are redirectable; an arbitrary value needs a 0x06 SWITCHEX)')
        return 2 + i
    if case == "default":                                      # 0x06 SWITCHEX(default, val0, lbl0, ...)
        return 0
    for k in range(1, len(ops) - 1, 2):
        try:
            if int(ops[k]) == case:
                return k + 1
        except ValueError:
            continue
    raise LogicEditError(f"logic_edit switch_case: no explicit case value {case} in this SWITCHEX")


def _switch_redirect(eb_bytes, ed, anchor_rel, case, old_target, new_target) -> bytes:
    """Redirect a switch ``case``/default arm to a different in-function instruction boundary, applied at the
    EXACT switch located during the split. Swap that one arm's ``L<old_target>`` label for ``L<new_target>`` in
    the disassembled source (injecting ``L<new_target>:`` if the boundary isn't already a branch target -- a
    label is zero bytes, so this stays length-NEUTRAL) and reassemble via the keystone (``cmdasm`` re-anchors
    every reloff; it RAISES on a backward / >u16 reloff -> normalized here). Old-guarded: the byte at
    ``anchor_rel`` is still a switch of the same op AND the arm's operand is still ``L<old_target>``."""
    from .eb import cmdasm as _cmdasm
    from .eb import edit as _edit
    from .eb import exprasm as _exprasm
    eb = EbScript.from_bytes(eb_bytes)
    f = _func(eb, ed)
    abs_off = f.abs_start + anchor_rel
    op = eb.data[abs_off] if (0 <= abs_off < len(eb.data)) else None
    if op not in _SWITCH_OPS:                                   # the captured site no longer holds a switch
        raise LogicEditError(f"logic_edit switch_case: the switch in entry{_int(ed, 'entry')}/"
                             f"tag{_int(ed, 'tag')} drifted (conflicting edits?)")
    old_label, new_label = f"L{old_target}", f"L{new_target}"
    try:
        items = _cmdasm.disassemble_items(eb.data, f.abs_start, f.abs_end)
        line_idx = next((k for k, (off, _t) in enumerate(items) if off == anchor_rel), None)
        if line_idx is None:                                   # the guarded switch is decoded -> always present
            raise LogicEditError("logic_edit switch_case: could not locate the switch (internal)")
        texts = [t for _o, t in items]
        line = texts[line_idx]
        mnem = line[:line.index("(")]
        ops = line[line.index("(") + 1:line.rindex(")")].split(", ")
        op_idx = _switch_operand_index(op, ops, case)
        if ops[op_idx] != old_label:                           # second guard: the arm still points at old_target
            raise LogicEditError(f"logic_edit switch_case guard: the case {case} arm is {ops[op_idx]}, not "
                                 f"{old_label} (donor drift)")
        if not any(o is None and t.strip() == new_label + ":" for o, t in items):
            tgt_idx = next((k for k, (off, _t) in enumerate(items) if off == new_target), None)
            if tgt_idx is None:                                # new_target must be a real instruction boundary
                raise LogicEditError(f"logic_edit switch_case: new_target {new_target} is not an instruction "
                                     f"boundary in entry{_int(ed, 'entry')}/tag{_int(ed, 'tag')}")
            texts.insert(tgt_idx, new_label + ":")             # label a bare boundary (zero bytes, length-neutral)
            if tgt_idx <= line_idx:
                line_idx += 1
        ops[op_idx] = new_label
        texts[line_idx] = mnem + "(" + ", ".join(ops) + ")"
        new_body = _cmdasm.assemble_block("\n".join(texts))
    except (_cmdasm.CmdAsmError, _exprasm.AssembleError) as ex:
        raise LogicEditError(f"logic_edit switch_case {old_target}->{new_target}: could not rebuild "
                             f"entry{_int(ed, 'entry')}/tag{_int(ed, 'tag')}: {ex}")
    return _edit.replace_function_body(eb_bytes, _int(ed, "entry"), _int(ed, "tag"), new_body)


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
        _operand_edit(eb, buf, ed, _int(ed, "op"), _int(ed, "operand"))   # `operand` of any op (caller owns
        #   the choice of op/operand/nth -- e.g. a hand-authored display patch; no slot guard)
    elif kind == "item_display":                             # the "Received <item>!" DISPLAY half of a reward:
        slot = _int(ed, "slot", optional=True)               #   SetTextVariable(slot, item_id). FF9's item-get
        slot = 0 if slot is None else slot                   #   display is slot 0; pin it so a same-value
        old = _int(ed, "old")                                #   SetTextVariable in another slot isn't corrupted.
        _operand_edit(eb, buf, ed, SETTEXTVAR_OP, 1, extra=lambda i: i.imm(0) == slot,
                      what=f"SetTextVariable(slot={slot}, id={old}) display in "
                           f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    elif kind == "item_count":                               # the QUANTITY operand of a specific AddItem(id):
        iid = _int(ed, "item_id")                            #   pin the item id so a same-count AddItem of a
        old = _int(ed, "old")                                #   DIFFERENT item isn't retargeted.
        _operand_edit(eb, buf, ed, ITEM_OP, _ITEM_OPERAND["count"], extra=lambda i: i.imm(0) == iid,
                      what=f"AddItem(id={iid}) count=={old} in "
                           f"entry{_req(ed, 'entry')}/tag{_req(ed, 'tag')}")
    else:
        raise LogicEditError(f"logic_edit unknown .eb kind '{kind}' (kinds: {_EB_KINDS} + 'text')")


def _edit_list(edits):
    """Validate the ``[[logic_edit]]`` container is an array of tables (so ``[logic_edit]`` -- a single TOML
    table -- or junk is a clean :class:`LogicEditError`, not a raw ``AttributeError`` from ``.get`` on a key)
    and return its non-empty entries."""
    if edits is None:
        return []
    if not isinstance(edits, (list, tuple)):
        raise LogicEditError("logic_edit must be an array of tables ([[logic_edit]]), not "
                             f"{type(edits).__name__} (you likely wrote [logic_edit] instead of [[logic_edit]])")
    out = [e for e in edits if e]
    for e in out:
        if not isinstance(e, dict):
            raise LogicEditError(f"each logic_edit must be a table, got {type(e).__name__}")
    return out


def apply_logic_edits(eb_bytes, edits) -> bytes:
    """Apply every NON-text ``[[logic_edit]]`` to ``eb_bytes`` and return the patched bytes. Empty / text-only ->
    byte-identical. Most edits are length-preserving in-place operand swaps (old-guarded); two kinds need the
    keystone REBUILD instead -- a ``flag_index`` remap that CROSSES the 0xFF C4/E4 boundary (length-changing) and
    a ``switch_case`` redirect (length-neutral but the reloff is computed, not a literal). The rebuilds run in a
    SECOND pass AFTER the in-place edits (so the in-place edits' donor-based offsets aren't shifted first), each
    located by the EXACT function-relative offset captured here, delta-adjusted for prior same-function rebuilds.
    Raises :class:`LogicEditError` on any unsafe edit."""
    eb_edits = [e for e in _edit_list(edits) if e.get("kind") != "text"]
    if not eb_edits:
        return bytes(eb_bytes)
    eb = EbScript.from_bytes(eb_bytes)
    inplace, rebuilds = [], []                                 # in-place operand swaps vs keystone rebuilds
    for ed in eb_edits:
        kind = ed.get("kind")
        if kind == "flag_index":
            ins, _idx, tok_len, old, new = _flag_locate(eb, ed)
            if _flag_width(new) != (tok_len - 1):              # crosses 0xFF -> keystone rebuild (length-changing)
                rebuilds.append(("flag", ed, (_int(ed, "entry"), _int(ed, "tag")),
                                 ins.off - _func(eb, ed).abs_start, _flag_width(new) - _flag_width(old),
                                 (old, new)))
                continue
        elif kind == "switch_case":                            # redirect a switch arm (keystone, length-neutral)
            ins, anchor_rel, case, old_target = _switch_locate(eb, ed)
            rebuilds.append(("switch", ed, (_int(ed, "entry"), _int(ed, "tag")), anchor_rel, 0,
                             (case, old_target, _int(ed, "new_target"))))
            continue
        inplace.append(ed)
    buf = bytearray(eb_bytes)
    for ed in inplace:                                         # length-preserving: instruction offsets stay put
        _apply_eb_edit(eb, buf, ed)
    out = bytes(buf)
    # keystone rebuilds: locate each by its captured function-relative offset (stable through the in-place pass),
    # adjusted for the byte delta of prior same-function rebuilds (ascending offset) so multiple rebuilds compose.
    # Ties each rebuild to the EXACT instruction the split saw -- it can't drift onto a different same-flag instr.
    deltas: dict = {}
    for rkind, ed, key, anchor_rel, byte_delta, payload in sorted(rebuilds, key=lambda r: (r[2], r[3])):
        dk = deltas.get(key, 0)                                # cumulative byte shift from prior same-function rebuilds
        eff = anchor_rel + dk
        if rkind == "flag":
            out = _flag_rewidth(out, ed, eff, *payload)
        else:                                                  # a switch's case targets are all FORWARD of it, so
            case, old_t, new_t = payload                       # they shifted by dk too -- relocate them, not just
            out = _switch_redirect(out, ed, eff, case, old_t + dk, new_t + dk)   # the anchor (the composition fix)
        deltas[key] = dk + byte_delta
    return out


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


def verified_mes_splice(body: str, txid: int, new_text: str, *, lang: str, err=None) -> str:
    """Replace ONLY ``txid``'s text payload with ``new_text`` in an index-implicit ``.mes`` body, then re-parse
    and assert every OTHER entry is byte-identical -- a botched splice fails the build, not the player. Shared by
    the dialogue-string rewrite (``kind="text"``) and the ``logic_add`` ``menu_row`` row-label splice. ``err`` is
    the exception class to raise (defaults to :class:`LogicEditError`, so a ``menu_row`` caller can pass its own
    ``LogicAddError``). v1 supports the verbatim donor body (no ``[TXID=]`` re-index markers)."""
    from .dialogue import parse_mes
    err = err or LogicEditError
    if "[TXID=" in body:
        raise err("a .mes splice on a [TXID=]-reindexed body is not supported (Phase 2b)")
    before = parse_mes(body)
    if txid not in before:
        raise err(f"txid {txid} not found in the {lang} .mes")
    parts = body.split("[STRT=")
    if not (0 <= txid + 1 < len(parts)):                      # index-implicit: txid == position == part index-1
        raise err(f"txid {txid} out of range in the {lang} .mes")
    try:
        parts[txid + 1] = _splice_block(parts[txid + 1], new_text)
    except LogicEditError as ex:                              # _splice_block speaks LogicEditError -> normalize to err
        raise err(str(ex))
    spliced = "[STRT=".join(parts)
    after = parse_mes(spliced)                                # VERIFY: only the target entry changed
    if len(after) != len(before):
        raise err(f"the .mes splice changed the entry count ({lang})")
    for t, e in before.items():
        got = after.get(t)
        if got is None:
            raise err(f"the .mes splice dropped txid {t} ({lang})")
        if t == txid:
            if got.text != new_text:
                raise err(f"the .mes splice didn't take for txid {txid} ({lang})")
        elif (got.text, got.strt, got.tail) != (e.text, e.strt, e.tail):
            raise err(f"the .mes splice corrupted txid {t} ({lang})")
    return spliced


def apply_logic_text_edits(body: str, edits, lang: str) -> str:
    """Apply every ``kind="text"`` edit whose ``lang`` is unset or == ``lang`` to a ``.mes`` body, returning the
    rewritten body. A VERIFIED in-place splice (:func:`verified_mes_splice`): it replaces one entry's text
    payload, then re-parses and asserts every OTHER entry is byte-identical (so a botched splice fails the build,
    not the player). v1 supports the index-implicit verbatim donor body (no ``[TXID=]`` re-index markers)."""
    text_edits = [e for e in _edit_list(edits) if e.get("kind") == "text" and e.get("lang") in (None, lang)]
    if not text_edits or not body:
        return body
    from .dialogue import parse_mes, strip_tags
    if "[TXID=" in body:
        raise LogicEditError("logic_edit text rewrite on a [TXID=]-reindexed .mes is not supported (Phase 2b)")
    for ed in text_edits:
        txid, old, new = _int(ed, "txid"), _req(ed, "old"), _req(ed, "new")
        if not isinstance(old, str) or not isinstance(new, str):
            raise LogicEditError(f"logic_edit text txid {txid}: 'old' and 'new' must be strings")
        ent = parse_mes(body).get(txid)
        if ent is None:
            raise LogicEditError(f"logic_edit text: txid {txid} not found in the {lang} .mes")
        if old not in (ent.text, strip_tags(ent.text)):
            raise LogicEditError(f"logic_edit text txid {txid} ({lang}): current line != `old` (donor drifted)")
        body = verified_mes_splice(body, txid, new, lang=lang)
    return body


# --- discovery: the editable value-sites of one routine (the GUI authoring surface) -----------------
# The GUI (Workspace "Script (verbatim .eb)" subtree) can't ask the user to hand-write entry/tag/op/nth/old
# coordinates. So this walks ONE (entry, tag) routine the way the appliers' `_pick` filters do, and returns a
# legible EditSite per editable value, each carrying ready-to-fill [[logic_edit]] templates. Edit -> click ->
# pick a new value; :func:`synth_edits` splices it in; :func:`upsert_edits` merges into the field.toml list.
@dataclass
class EditSite:
    """One editable value in a routine -- a row + 'Edit…' affordance in the GUI. ``templates`` are the
    [[logic_edit]] dicts MINUS the new-value key (filled by :func:`synth_edits`). For an item reward the
    AddItem give and the matched ``SetTextVariable`` 'Received <item>!' display are paired in
    ``display_templates`` so ONE edit retargets both -- the give-vs-display decoupling: if only the give
    changes, the message lies (the chest-says-Potion-gives-Elixir bug)."""
    group: str                  # item | gil | field | flag | text  (what's being edited)
    value_kind: str             # item | int | flag | string  -> how the dialog renders/validates NEW
    label: str                  # the row label shown in the panel
    old: object                 # the donor's current value (int, or the us string for text)
    new_key: str = "new"        # the template key the NEW value goes under ("new", or "new_flag" for flag)
    templates: list = _dc_field(default_factory=list)          # the primary edits (the give / the value)
    display_templates: list = _dc_field(default_factory=list)  # item: the paired display edits
    count_templates: list = _dc_field(default_factory=list)    # item: the quantity (AddItem count) edits
    count_old: object = None    # item: the current quantity (None if it varies across give-paths -> not editable)
    note: str = ""              # an advisory (e.g. no display site found / count not shown)
    key: str = ""               # a stable id for this site within the routine (GUI row <-> its edits)


def _op_tmpl(kind, entry, tag, old, nth, total, *, op=None, operand=None):
    """One length-preserving operand template (the new value spliced in later). ``nth`` is included only
    when the value is ambiguous (``total`` > 1) -- mirroring what the appliers' ``_pick`` requires."""
    t = {"kind": kind, "entry": int(entry), "tag": int(tag), "old": old}
    if op is not None:
        t["op"] = op
    if operand is not None:
        t["operand"] = operand
    if total > 1:
        t["nth"] = nth
    return t


def _value_groups(instrs, op, operand_index):
    """``{value: [nth, ...]}`` for every immediate ``operand_index`` of ``op`` -- the value-filtered nth
    each occurrence gets (the exact index :func:`_pick` resolves), so an edit can target all or one."""
    groups: dict = {}
    for ins in instrs:
        if ins.op != op:
            continue
        v = ins.imm(operand_index)
        if v is None:
            continue
        groups.setdefault(v, []).append(len(groups.get(v, [])))
    return groups


def _line_old(entries, txid):
    """The donor's current line (tag-stripped) for ``txid``, or None (no ``.mes`` / not found)."""
    if not entries:
        return None
    from .dialogue import strip_tags
    ent = entries.get(int(txid))
    return strip_tags(ent.text) if ent is not None else None


def _short(s, width=44):
    s = " ".join(str(s).split())
    return (s[:width] + "…") if len(s) > width else s


def _text_templates(txid, lang_bodies, fallback_old):
    """A per-language ``text`` template (each guarded by THAT language's own current string) so a single
    new string is written to every localized copy consistently. Skips a ``[TXID=]``-reindexed body (Phase
    4) and a language missing the txid. Falls back to one lang-agnostic template when no bodies are given."""
    if not lang_bodies:
        return [{"kind": "text", "txid": int(txid), "old": fallback_old}] if fallback_old is not None else []
    from .dialogue import parse_mes, strip_tags
    out = []
    for lang, body in lang_bodies.items():
        if not body or "[TXID=" in body:
            continue
        ent = parse_mes(body).get(int(txid))
        if ent is None:
            continue
        out.append({"kind": "text", "lang": lang, "txid": int(txid), "old": strip_tags(ent.text)})
    return out


def editable_effects(eb_bytes, entry, tag, *, entries=None, lang_bodies=None):
    """Discover the editable value-sites of one ``(entry, tag)`` routine of a verbatim fork's ``.eb`` --
    item rewards (give + paired display), gil grants, ``Field()`` warps, GLOB story-flag indices, and
    dialogue lines -- each as an :class:`EditSite` the GUI authors a ``[[logic_edit]]`` from. Pure; never
    mutates. ``entries`` = parsed us ``.mes`` (``{txid: MesEntry}``) for line text; ``lang_bodies`` =
    ``{lang: raw .mes body}`` for per-language text-edit guards."""
    eb = EbScript.from_bytes(eb_bytes)
    if not (0 <= entry < eb.entry_count):
        return []
    e = eb.entry(entry)
    if e.empty:
        return []
    f = e.func_by_tag(tag)
    if f is None:
        return []
    from . import forkreport as FR
    instrs = list(eb.instrs(f))
    sites: list = []

    # items: group AddItem by id (skipping the engine no-op grants the read map also hides); pair each with
    # the same-id SetTextVariable in TEXT SLOT 0 (FF9's item-get display, build.set_text_variable(0, id)) so
    # the reward + its "Received <item>!" message change together. A same-value SetTextVariable in another
    # slot (e.g. a preview row) is NOT the item display and is left alone.
    disp_groups: dict = {}
    for ins in instrs:
        if ins.op == SETTEXTVAR_OP and ins.imm(0) == 0:
            v = ins.imm(1)
            if v is not None:
                disp_groups.setdefault(v, []).append(len(disp_groups.get(v, [])))
    item_groups: dict = {}
    for ins in instrs:
        if ins.op != ITEM_OP:
            continue
        iid = ins.imm(0)
        if iid is None or iid == FR.NO_ITEM or FR.item_inert(iid):
            continue
        item_groups.setdefault(iid, []).append(len(item_groups.get(iid, [])))
    for iid, nths in item_groups.items():
        give = [_op_tmpl("item", entry, tag, iid, n, len(nths), op=ITEM_OP, operand="id") for n in nths]
        dn = disp_groups.get(iid, [])
        disp = [{**_op_tmpl("item_display", entry, tag, iid, n, len(dn), op=SETTEXTVAR_OP, operand=1), "slot": 0}
                for n in dn]
        # quantity: editable only when every give-path of this item grants the SAME count (the usual case);
        # if the counts vary, expose no count edit (the user can hand-author per-path) and note it.
        counts = [ins.imm(1) for ins in instrs if ins.op == ITEM_OP and ins.imm(0) == iid]
        uniform = bool(counts) and counts[0] is not None and len(set(counts)) == 1
        count_old = counts[0] if uniform else None
        cnt = ([{**_op_tmpl("item_count", entry, tag, count_old, n, len(nths), op=ITEM_OP, operand=1),
                 "item_id": int(iid)} for n in nths] if uniform else [])
        qty = f" ×{count_old}" if count_old is not None else ""
        paths = f"  ({len(nths)} give-paths)" if len(nths) > 1 else ""
        label = f"gives {FR.item_label(iid)}{qty}{paths}"
        note = "" if disp else "no 'Received <item>!' display message paired — only the give changes"
        if not uniform and len(counts) > 1:
            note = (note + "  " if note else "") + "quantity varies across give-paths — not editable here"
        sites.append(EditSite("item", "item", label, int(iid), "new", give, disp, cnt, count_old,
                              note, f"item:{iid}"))

    # gil grants (skip the > party-cap sentinel amounts -- a scripted/computed AddGil, not a treasure reward)
    for amt, nths in _value_groups(instrs, GIL_OP, 0).items():
        if amt > FR.GIL_CAP:
            continue
        tmpls = [_op_tmpl("gil", entry, tag, amt, n, len(nths), op=GIL_OP) for n in nths]
        sites.append(EditSite("gil", "int", f"gives {amt} gil", int(amt), "new", tmpls, key=f"gil:{amt}"))

    # Field() warps (an alternative to the [verbatim_eb] retarget table -- per-site, not by global dest)
    for dest, nths in _value_groups(instrs, FIELD_OP, 0).items():
        tmpls = [_op_tmpl("field", entry, tag, dest, n, len(nths), op=FIELD_OP) for n in nths]
        sites.append(EditSite("field", "field", f"warps to field {dest}", int(dest), "new", tmpls,
                              key=f"field:{dest}"))

    # GLOB story-flag indices (read + write of one index remap together so they stay in sync)
    from .eventscan import _glob_var_token
    flag_groups: dict = {}
    for ins in instrs:
        if ins.op != EXPR_OP:
            continue
        tok = _glob_var_token(eb.data, ins.off + 1)
        if tok is not None:
            flag_groups.setdefault(tok[0], []).append(len(flag_groups.get(tok[0], [])))
    for idx, nths in flag_groups.items():
        tmpls = [{"kind": "flag_index", "entry": int(entry), "tag": int(tag), "flag": int(idx),
                  **({"nth": n} if len(nths) > 1 else {})} for n in nths]
        n = len(nths)
        sites.append(EditSite("flag", "flag", f"story flag {idx}" + (f"  (×{n})" if n > 1 else ""),
                              int(idx), "new_flag", tmpls, key=f"flag:{idx}"))

    # dialogue lines (one site per distinct Window-op txid that resolves to a line)
    seen_txid: set = set()
    for ins in instrs:
        if ins.op not in WINDOW_OPS:
            continue
        txid = ins.imm(WINDOW_OPS[ins.op])
        if txid is None or txid in seen_txid:
            continue
        seen_txid.add(txid)
        us_old = _line_old(entries, txid)
        tmpls = _text_templates(txid, lang_bodies, us_old)
        if not tmpls:
            continue                                          # no editable .mes for this line
        label = (f'line {txid}: "{_short(us_old)}"' if us_old else f"line {txid}")
        langs = [t["lang"] for t in tmpls if t.get("lang")]
        note = ("rewrites " + ", ".join(langs)) if langs else ""
        sites.append(EditSite("text", "string", label, us_old if us_old is not None else "",
                              "new", tmpls, note=note, key=f"text:{txid}"))
    return sites


# --- edit synthesis + merge (the GUI writes these into the field.toml's logic_edit list) -------------
_COORD_KEYS = ("kind", "entry", "tag", "op", "operand", "slot", "item_id", "nth", "lang", "txid", "flag", "old")


def synth_edits(site: EditSite, new) -> list:
    """The ``[[logic_edit]]`` dicts that realize editing ``site`` to ``new`` -- the value edits PLUS, for an
    item, the paired display edits (so the 'Received <item>!' message always tracks the give). For an item the
    quantity is unchanged (use :func:`synth_item_edits` to also set the count)."""
    out = [{**t, site.new_key: new} for t in site.templates]
    out += [{**t, "new": new} for t in site.display_templates]
    return out


def synth_item_edits(site: EditSite, new_id, new_count=None) -> list:
    """The edits to retarget an item reward to ``new_id`` (give + paired display) AND, when ``new_count`` is
    given and differs, its quantity. A component whose value is unchanged emits NO edit (so a count-only change
    doesn't author a redundant give edit, and vice-versa)."""
    out = []
    if new_id != site.old:
        out += [{**t, "new": new_id} for t in site.templates]
        out += [{**t, "new": new_id} for t in site.display_templates]
    if new_count is not None and site.count_old is not None and new_count != site.count_old:
        out += [{**t, "new": new_count} for t in site.count_templates]
    return out


def edit_coord(ed: dict) -> tuple:
    """The identifying coordinates of a logic_edit (everything but the NEW value) -- for dedup/replace."""
    return tuple((k, ed.get(k)) for k in _COORD_KEYS)


def site_footprint(site: EditSite) -> set:
    """The coords of EVERY edit ``site`` can author (value + display + quantity) -- so re-editing or clearing a
    site removes all of its prior edits before adding new ones (handles a changed display/count set cleanly)."""
    return {edit_coord(t) for t in (site.templates + site.display_templates + site.count_templates)}


def upsert_edits(existing, new_edits, *, drop=None) -> list:
    """Return ``existing`` with edits whose coords are in ``drop`` (default = the new edits' own coords)
    removed, then ``new_edits`` appended. Pure -- re-editing a site replaces its edits, never stacks them."""
    drop = set(drop) if drop is not None else {edit_coord(e) for e in new_edits}
    kept = [e for e in (existing or []) if edit_coord(e) not in drop]
    return kept + list(new_edits)
