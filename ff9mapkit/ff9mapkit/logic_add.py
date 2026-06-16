"""Phase 4a: length-CHANGING in-place ADDITIONS to a verbatim fork's ``.eb`` -- PREPEND a guarded effect to
an existing routine. The structural sibling of :mod:`ff9mapkit.logic_edit` (length-PRESERVING value swaps).

Where ``[[logic_edit]]`` overwrites an operand same-width, ``[[logic_add]]`` ADDS instructions, which changes
the ``.eb``'s length. Two placements:
  * ``where = "prepend"`` (default, Phase 4a) -- :func:`ff9mapkit.eb.edit.insert_in_function` at ``rel_off=0``,
    the 676/676-proven ALWAYS-safe prepend (the engine is uniformly IP-relative, so the whole function body
    shifts together; safe even over a 0x06/0x0B switch table).
  * ``where = "after"`` (Phase 4b) -- insert the effect AFTER the ``after_nth``-th ``after_op`` instruction, via
    the keystone (:func:`ff9mapkit.eb.cmdasm.disassemble_items` -> splice the effect's labeled source ->
    :func:`ff9mapkit.eb.cmdasm.assemble_block` -> :func:`ff9mapkit.eb.edit.replace_function_body`), so EVERY jump
    and switch in the function relocates past the inserted bytes (the keystone round-trips all 676 fields +
    3155/3155 switch functions byte-exact, and relocates them under a length change).

Kinds:
  * ``set_flag`` -- write a GLOB story flag. IDEMPOTENT, so prepended UNGATED into any routine.
  * ``give_item`` / ``give_gil`` -- CUMULATIVE (each call adds more), so wrapped in the FF9 chest once-guard
    ``if(!guard){guard=1; body}`` (the guard flag auto-allocated from the safe band) -- UNLESS it's a tag-3
    talk handler with ``repeat = true`` (a deliberately repeatable per-interaction effect).
  * ``show_line`` -- open a dialogue window showing an authored line. Its only effect is the message, so
    it's the way to ANNOUNCE a silent ``give_item``/``give_gil`` (otherwise they hand over the reward with
    no "Received X!" box). Any other kind may also carry an optional ``message = "..."`` to announce its
    effect in the SAME once-guard (give THEN show, atomically).
  * ``add_case`` -- ADD a new arm to an existing jump table (0x06/0x0B/0x0D) -- a NEW dispatch arm (a scenario
    value, an ATE/dialogue menu row) that runs one of the effects above (named by ``effect``) then rejoins the
    switch's DEFAULT arm (``then = "merge"``). 0x0B/0x0D are contiguous (``case = "auto"`` = base+ncases, the
    only legal extension); 0x06 takes an explicit unused ``case`` value. Length-changing: the operand table
    grows + the branch body is appended at the function end, and the keystone re-anchors every reloff.
    ``add_case`` alone makes an EXISTING-but-default selector value live -- it adds a dispatch arm but no
    SELECTABLE, LABELLED menu row.
  * ``menu_row`` -- the full coordinated MENU ROW: add a NEW selectable + labelled option to an existing
    dialogue-choice menu. Orchestrates three legs over a CANONICAL menu (a base-0 contiguous GetChoose switch
    + a text-gated ``[CHOO]`` row list): (A) the dispatch arm (an ``add_case`` at the next contiguous row
    index, running ``effect``), (B) a best-effort widen of the ``EnableDialogChoices`` (0x7C) availability
    mask, and (C) a verified splice of the new ``\n[MOVE=18,0]<label>`` row into the menu's single ``.mes``
    entry (the row-label leg ships in :func:`menu_row_text_plan` / :func:`apply_menu_row_text`, applied by the
    build). v1 targets TEXT-gated menus (no pre-tag / ``[PCHC]``); a ``[PCHM]`` mask-gated menu (incl. the ATE
    avail-word menus) fails closed -- the runtime mask leg is a follow-up. One ``menu_row`` per switch.

A ``show_line`` (or any ``message =``) line is APPENDED to the donor ``.mes`` above its txids -- the same
append-and-resolve channel ``[[on_entry]]`` narration uses (:func:`build._verbatim_on_entry_messages`) -- so
the inserted ``WindowSync`` resolves into real text. A message ALWAYS implies a once-guard (a window in a
tread zone would re-open every frame), even on an otherwise-idempotent ``set_flag``.

The effect bytes reuse the proven :mod:`ff9mapkit.content.region` / :mod:`ff9mapkit.content.event` encoders
verbatim (zero new bytecode). The composed ``.eb`` is re-validated by :func:`ff9mapkit.eblint.lint_eb` before
the build ships it -- a bad add fails the BUILD (a clean :class:`LogicAddError`), never a silent mis-splice.
"""
from __future__ import annotations

import re

from . import flags as _flags
from .content import event as _event
from .content import region as _region
from .eb import edit as _edit
from .eb.model import EbScript

GLOB_BOOL = _region.GLOB_BOOL                       # 0xC4 -- save-persistent story-flag class
_ADD_KINDS = ("set_flag", "give_item", "give_gil", "show_line")
_CUMULATIVE = ("give_item", "give_gil")             # need a once-guard (set_flag is idempotent)
TALK_TAG = 3                                        # the only tag where an UNGATED cumulative effect is sane
_GIL_CAP = 9_999_999
_SWITCH_OPS = (0x06, 0x0B, 0x0D)                    # JMP_SWITCHEX (explicit) / JMP_SWITCH (contiguous) / 2-byte
_DISPATCH_KINDS = ("add_case", "menu_row")          # kinds whose EFFECT is named by `effect` (not `kind`)
ENABLE_DIALOG_CHOICES = 0x7C                        # CHOOSEPARAM: [argflags][availMask:u16][default:u8]
CHOICE_INDENT = "[MOVE=18,0]"                       # = content.text.CHOICE_INDENT (per-row menu indent)


def _effective_effect_add(add):
    """The add whose ``kind`` names the EFFECT to encode. For a normal effect add that's ``add`` itself; for a
    DISPATCH add (``add_case``/``menu_row`` -- ``kind`` stays the dispatch kind, the payload is named by
    ``effect``) it's a synthesized ``{**add, "kind": <effect>}`` -- so the effect/message/guard machinery treats
    all of them uniformly. ``None`` for a dispatch add with no ``effect`` (a stub arm)."""
    if add.get("kind") not in _DISPATCH_KINDS:
        return add
    eff = add.get("effect")
    return {**add, "kind": eff} if eff is not None else None


class LogicAddError(ValueError):
    """A ``[[logic_add]]`` that can't be applied safely (bad routine, out-of-band flag, overflow, no guards
    left, an unsafe ungated effect) -- it fails the BUILD, never silently mis-adds."""


def _int(add, key, *, default=None, optional=False):
    if key not in add:
        if optional:
            return default
        raise LogicAddError(f"logic_add ({add.get('kind', '?')}) missing required key '{key}'")
    v = add[key]
    if isinstance(v, bool) or not isinstance(v, int):
        raise LogicAddError(f"logic_add ({add.get('kind', '?')}) key '{key}' must be an integer, "
                            f"got {type(v).__name__} ({v!r})")
    return v


def _add_message(add) -> "str | None":
    """The authored line this add SHOWS, or None. ``show_line`` requires one; any other kind may carry an
    optional ``message = "..."`` to announce its effect. Raises on a present-but-malformed message."""
    add = _effective_effect_add(add)
    if add is None:                                            # an add_case stub (no effect) -> no message
        return None
    msg = add.get("message")
    if add.get("kind") == "show_line":
        if not isinstance(msg, str) or not msg:
            raise LogicAddError("logic_add show_line needs a non-empty `message` string (the line to show)")
        return msg
    if msg is None:
        return None
    if not isinstance(msg, str) or not msg:
        raise LogicAddError(f"logic_add ({add.get('kind', '?')}) message must be a non-empty string")
    return msg


def _needs_guard(add) -> bool:
    """A once-guard is needed for a CUMULATIVE effect (give_item/give_gil pile up) OR any add that shows a
    MESSAGE (a window in a tread zone would re-open every frame). ``set_flag`` alone is idempotent -> ungated."""
    return add.get("kind") in _CUMULATIVE or _add_message(add) is not None


def _effect_body(add, *, message_txid=None) -> bytes:
    """The raw effect bytes for one add (no guard) -- reuses the content encoders. When the add carries a
    message (or IS a ``show_line``), a ``WindowSync(message_txid)`` is APPENDED after the effect (give THEN
    announce); ``message_txid`` is the build-allocated id of the appended ``.mes`` line."""
    kind = add.get("kind")
    msg = _add_message(add)
    if msg is not None and message_txid is None:                   # the build allocates message txids; a
        raise LogicAddError(f"logic_add ({kind}) has a message but no text id was allocated (internal: "
                            "apply_logic_adds needs message_txids -- the build/Check plan provides it)")
    tail = _event.message(int(message_txid)) if msg is not None else b""
    if kind == "show_line":
        return tail                                                # the message IS the whole effect
    if kind == "set_flag":
        idx, val = _int(add, "flag"), _int(add, "value", default=1, optional=True)
        if not _flags.is_safe_custom(idx):
            raise LogicAddError(f"set_flag index {idx} is outside the safe custom band "
                                f"[{_flags.FIRST_SAFE_FLAG}, {_flags.CHOICE_SCRATCH_FLOOR}) (or reserved)")
        return _region.set_var(GLOB_BOOL, idx, val) + tail
    if kind == "give_item":
        count = _int(add, "count", default=1, optional=True)
        if not (1 <= count <= 255):
            raise LogicAddError(f"give_item count {count} out of range (1-255; AddItem count is one byte)")
        try:
            return _event.give_item(add.get("item"), count) + tail  # name or id, resolved by items
        except (ValueError, KeyError) as ex:
            raise LogicAddError(f"give_item: {ex}")
    if kind == "give_gil":
        amount = _int(add, "amount")
        if not (0 < amount <= _GIL_CAP):
            raise LogicAddError(f"give_gil amount {amount} out of range (1-{_GIL_CAP})")
        return _event.give_gil(amount) + tail
    raise LogicAddError(f"logic_add unknown kind '{kind}' (kinds: {_ADD_KINDS})")


def _guarded(body: bytes, guard: int) -> bytes:
    """``if(!guard){ guard=1; body }`` -- the FF9 chest once-guard (dedup-flag FIRST so a window in ``body``
    can't double-fire), via the proven region encoders."""
    return _region.if_block(_region.cond_not(GLOB_BOOL, guard),
                            _region.set_var(GLOB_BOOL, guard, 1) + body)


class _GuardAlloc:
    """Hands out disjoint once-guard flags. Avoids collisions with: the author's other ``set_flag`` indices,
    the project's OTHER authored story flags (``reserved`` -- ``[startup]``/``[[flag]]``/``[[on_entry]]``/
    gateway ``set_flags``; else a guard could alias a load-time flag and silently pre-fire), each other, and
    (in a campaign) a SIBLING member's window. Auto-guards are drawn from ``[base, base+window)`` (a campaign
    member's flag block) or ``[FIRST_SAFE_FLAG, CHOICE_SCRATCH_FLOOR)`` for a single field; an explicit
    ``guard`` is band-checked + collision-checked but not window-confined (it may be a deliberate shared flag)."""

    def __init__(self, base, window, adds, reserved):
        self._base = base if base is not None else _flags.FIRST_SAFE_FLAG
        self._next = self._base
        self._hi = (self._base + window) if (base is not None and window) else _flags.CHOICE_SCRATCH_FLOOR
        self._hi = min(self._hi, _flags.CHOICE_SCRATCH_FLOOR)
        self._used = {f for f in (reserved or ()) if isinstance(f, int) and not isinstance(f, bool)}
        for a in adds or []:                           # other set_flag targets (handed-out guards are recorded in take)
            ea = _effective_effect_add(a)              # incl. an add_case whose effect is set_flag
            if ea and ea.get("kind") == "set_flag" and isinstance(ea.get("flag"), int) and not isinstance(ea.get("flag"), bool):
                self._used.add(ea["flag"])

    def take(self, add):
        g = add.get("guard")
        if g is not None:
            if isinstance(g, bool) or not isinstance(g, int):
                raise LogicAddError("logic_add guard must be an integer")
            if not _flags.is_safe_custom(g):
                raise LogicAddError(f"logic_add guard {g} is outside the safe custom band "
                                    f"[{_flags.FIRST_SAFE_FLAG}, {_flags.CHOICE_SCRATCH_FLOOR}) (or reserved)")
            if g in self._used:
                raise LogicAddError(f"logic_add guard {g} collides with another guard or an authored flag "
                                    f"-- pick a free index in [{self._base}, {self._hi})")
            self._used.add(g)
            return g
        while self._next < self._hi:
            g = self._next
            self._next += 1
            if g not in self._used and _flags.is_safe_custom(g):
                self._used.add(g)
                return g
        raise LogicAddError(f"logic_add ran out of safe guard flags in [{self._base}, {self._hi}) -- "
                            "raise [campaign] flags_per_field or set an explicit guard = N")


def _core_bytes(add, alloc, warnings=None, *, message_txid=None) -> bytes:
    """The bytes to prepend for one add: the effect, guarded unless it's idempotent (a message-less
    set_flag) or a deliberately-repeatable tag-3 talk effect (``repeat = true``)."""
    body = _effect_body(add, message_txid=message_txid)
    if not _needs_guard(add):
        return body                                            # set_flag w/o a message -- idempotent, ungated
    if add.get("repeat"):
        if _int(add, "tag") != TALK_TAG:
            raise LogicAddError(f"logic_add {add['kind']} repeat=true is only allowed on a tag-{TALK_TAG} "
                                f"talk handler (got tag {_int(add, 'tag')}); else it would fire every frame")
        if warnings is not None:                               # tag-3 is talk for an NPC but action-press for a region
            warnings.append(f"[[logic_add]] {add['kind']} repeat=true on entry {_int(add, 'entry')} tag {TALK_TAG} "
                            "re-fires on EVERY interaction (NPC talk / region action-button press), not once")
        return body                                            # an opt-in per-interaction repeat
    return _guarded(body, alloc.take(add))                     # default: once-guarded (safe in any routine)


def _insert_after(eb_bytes, eb, f, entry, tag, add, core, warnings) -> bytes:
    """Phase-4b: splice ``core`` AFTER the ``after_nth``-th occurrence of ``after_op`` in the routine. Uses the
    keystone -- disassemble the function to labeled source, insert the effect's (re-labeled) source right after
    the anchor instruction's line, reassemble (so EVERY jump/switch in the function relocates past the inserted
    bytes), and swap the rebuilt body in via :func:`eb.edit.replace_function_body`. The effect's own once-guard
    skip lands on the function's continuation, exactly as a prepend's does."""
    from .eb import cmdasm as _cmdasm
    from .eb import disasm as _disasm
    from .eb import exprasm as _exprasm
    after_op = _int(add, "after_op")
    after_nth = _int(add, "after_nth", default=0, optional=True)
    hits = [i for i in eb.instrs(f) if i.op == after_op]
    if not (0 <= after_nth < len(hits)):
        raise LogicAddError(f"logic_add where='after': no {_disasm.op_name(after_op)} #{after_nth} in "
                            f"entry{_int(add, 'entry')}/tag{_int(add, 'tag')} (found {len(hits)})")
    anchor = hits[after_nth]
    if warnings is not None and (anchor.op in _disasm.TERMINATOR_OPS or anchor.op == 0x01):
        kind = "terminator" if anchor.op in _disasm.TERMINATOR_OPS else "unconditional JMP"
        warnings.append(f"logic_add where='after' anchors on a {kind} ({_disasm.op_name(anchor.op)}) in "
                        f"entry{_int(add, 'entry')}/tag{_int(add, 'tag')} -- the inserted effect is unreachable "
                        "(control never falls through to it). Anchor on an earlier instruction.")
    anchor_rel = anchor.off - f.abs_start
    try:                                                        # the rebuild can raise CmdAsmError (a sibling of
        items = _cmdasm.disassemble_items(eb.data, f.abs_start, f.abs_end)   # LogicAddError) -- normalize it so the
        line_idx = next((k for k, (off, _t) in enumerate(items) if off == anchor_rel), None)   # build/Check report
        if line_idx is None:                                    # the anchor is a decoded instr -> always found
            raise LogicAddError("logic_add where='after': could not locate the anchor instruction (internal)")
        effect_src = _cmdasm.relabel(_cmdasm.disassemble_block(core, 0, len(core)), "_e")
        texts = [t for _o, t in items]
        spliced = "\n".join(texts[:line_idx + 1] + effect_src.split("\n") + texts[line_idx + 1:])
        new_body = _cmdasm.assemble_block(spliced)
    except (_cmdasm.CmdAsmError, _exprasm.AssembleError) as ex:   # ...is a clean failure, not a raw traceback
        raise LogicAddError(f"logic_add where='after': could not rebuild entry{_int(add, 'entry')}/"
                            f"tag{_int(add, 'tag')}: {ex}")
    return _edit.replace_function_body(eb_bytes, entry, tag, new_body)


# --- add_case: ADD a new arm to a jump table (length-changing: grow the operand table + a new branch body) ---
def _locate_switch(eb, entry, tag, nth):
    """Find the ``nth`` switch (0x06/0x0B/0x0D) in entry/tag; return ``(f, ins, SwitchInfo)``. ``nth`` may be
    None when the function has exactly one switch. Raises a clean :class:`LogicAddError` on any miss."""
    from .eb import disasm as _disasm
    if not (0 <= entry < eb.entry_count) or eb.entry(entry).empty:
        raise LogicAddError(f"add_case entry {entry} is empty or out of range (0..{eb.entry_count - 1})")
    f = eb.entry(entry).func_by_tag(tag)
    if f is None:
        raise LogicAddError(f"add_case entry {entry} has no function tag {tag}")
    switches = [i for i in eb.instrs(f) if i.op in _SWITCH_OPS]
    if not switches:
        raise LogicAddError(f"add_case: no switch (0x06/0x0B/0x0D) in entry{entry}/tag{tag}")
    if nth is None:
        if len(switches) > 1:
            raise LogicAddError(f"add_case: {len(switches)} switches in entry{entry}/tag{tag} -- "
                                f"add `nth` (0..{len(switches) - 1})")
        nth = 0
    if not (0 <= nth < len(switches)):
        raise LogicAddError(f"add_case nth {nth} out of range (0..{len(switches) - 1})")
    ins = switches[nth]
    si = _disasm.decode_switch(ins)
    if si is None:
        raise LogicAddError(f"add_case: the switch in entry{entry}/tag{tag} has computed operands (can't add)")
    return f, ins, si


def _resolve_add_case(add, si, ncases):
    """Validate + return the new selector value. 0x0B/0x0D (contiguous): only extends at ``base + ncases``;
    ``case = "auto"`` resolves to it, an explicit int must equal it. 0x06 (explicit): any unused value 0-65535."""
    case = add.get("case", "auto")
    if si.op in (0x0B, 0x0D):
        nxt = si.base + ncases
        if case == "auto":
            return nxt
        v = _int(add, "case")
        if v != nxt:
            raise LogicAddError(f"add_case: a contiguous SWITCH only extends at the NEXT selector {nxt} "
                                f"(base {si.base} + {ncases} cases) -- got {v}; use case=\"auto\"")
        return nxt
    if case == "auto":                                         # 0x06 SWITCHEX -- needs an explicit value
        raise LogicAddError("add_case: a 0x06 SWITCHEX needs an explicit `case` value (no contiguous 'auto')")
    v = _int(add, "case")
    if v in {e.value for e in si.edges if not e.is_default}:
        raise LogicAddError(f"add_case: case value {v} already exists in this SWITCHEX (a duplicate arm is dead)")
    if not (0 <= v <= 0xFFFF):
        raise LogicAddError(f"add_case: case value {v} out of range (0-65535)")
    return v


def _insert_case(eb_bytes, eb, f, entry, tag, ins, si, case_value, core):
    """Append a new case arm to the switch: grow its operand list (``L<new>`` for 0x0B/0x0D, ``value, L<new>``
    for 0x06) and append the new branch (``NEWCASE:`` + the effect's re-labeled source + a ``JMP`` to the
    switch's DEFAULT arm) at the function end, then reassemble (cmdasm re-anchors every reloff) + swap the body
    in. The new arm's reloff is FORWARD (the branch is after the switch); the merge JMP is a plain backward
    0x01 to the default. The count byte is recomputed by cmdasm from the operand-list length (no manual bump)."""
    from .eb import cmdasm as _cmdasm
    from .eb import exprasm as _exprasm
    sw_rel = ins.off - f.abs_start
    default_rel = next(e.target for e in si.edges if e.is_default) - f.abs_start
    if not (0 <= default_rel < (f.abs_end - f.abs_start)):     # a default arm AT the function end (a malformed
        raise LogicAddError(f"add_case: the switch's default arm in entry{entry}/tag{tag} is not an in-function "
                            "instruction boundary -- no safe merge target (the donor is itself broken)")
    try:
        items = _cmdasm.disassemble_items(eb.data, f.abs_start, f.abs_end)
        line_idx = next((k for k, (off, _t) in enumerate(items) if off == sw_rel), None)
        if line_idx is None:                                   # the located switch is decoded -> always present
            raise LogicAddError("add_case: could not locate the switch (internal)")
        texts = [t for _o, t in items]
        line = texts[line_idx]
        mnem = line[:line.index("(")]
        ops = line[line.index("(") + 1:line.rindex(")")].split(", ")
        ops += ([str(case_value), "NEWCASE"] if si.op == 0x06 else ["NEWCASE"])   # 0x0B/0x0D: positional (base+n)
        texts[line_idx] = mnem + "(" + ", ".join(ops) + ")"
        branch = ["NEWCASE:"]
        if core:                                               # the effect body (re-labeled so its L<n> can't collide)
            branch += _cmdasm.relabel(_cmdasm.disassemble_block(core, 0, len(core)), "_c").split("\n")
        branch.append(f"JMP(L{default_rel})")                  # then="merge": rejoin the switch's default arm
        new_body = _cmdasm.assemble_block("\n".join(texts + branch))
    except (_cmdasm.CmdAsmError, _exprasm.AssembleError) as ex:
        raise LogicAddError(f"add_case: could not rebuild entry{entry}/tag{tag}: {ex}")
    return _edit.replace_function_body(eb_bytes, entry, tag, new_body)


def _apply_add_case(eb_bytes, add, alloc, warnings=None, *, message_txid=None) -> bytes:
    """Add ONE new case arm to an existing switch, running a reused effect (set_flag/give_item/give_gil/
    show_line) then rejoining the switch's default arm. The keystone rebuild relocates everything."""
    if add.get("repeat"):
        raise LogicAddError("add_case does not support `repeat` (a dispatch arm is not a tag-3 talk poll)")
    then = add.get("then", "merge")
    if then != "merge":
        raise LogicAddError(f"add_case then='{then}' is not supported (v1 ships then=\"merge\" = rejoin the "
                            "switch's own default arm)")
    eff = add.get("effect")
    if eff is None:
        raise LogicAddError("add_case needs an `effect` (set_flag/give_item/give_gil/show_line) -- a stub arm "
                            "that only rejoins the default is a no-op")
    if eff not in _ADD_KINDS:
        raise LogicAddError(f"add_case effect '{eff}' must be one of {_ADD_KINDS}")
    entry, tag = _int(add, "entry"), _int(add, "tag")
    nth = _int(add, "nth", default=None, optional=True)
    eb = EbScript.from_bytes(eb_bytes)
    f, ins, si = _locate_switch(eb, entry, tag, nth)
    ncases = len([e for e in si.edges if not e.is_default])
    cc = _int(add, "case_count", default=None, optional=True)  # optional shape guard (donor drift -> fail)
    if cc is not None and cc != ncases:
        raise LogicAddError(f"add_case case_count guard: the switch has {ncases} cases, not {cc} (donor drift)")
    cap = 65535 if si.op == 0x0D else 255                      # the count byte width (0x06/0x0B = 1 byte)
    if ncases >= cap:
        raise LogicAddError(f"add_case: this switch is full ({ncases}/{cap} cases)")
    case_value = _resolve_add_case(add, si, ncases)
    core = _core_bytes(_effective_effect_add(add), alloc, warnings, message_txid=message_txid)
    return _insert_case(eb_bytes, eb, f, entry, tag, ins, si, case_value, core)


# --- menu_row: the full coordinated ADD of a selectable+labelled choice-menu row -----------------------
def _menu_row_switch(eb, add):
    """Locate + VALIDATE a ``menu_row``'s dispatch switch: it must be a base-0 CONTIGUOUS GetChoose switch
    (0x0B/0x0D, base 0) so the row index IS the case value (1:1). Returns ``(f, ins, si, new_row)`` where
    ``new_row`` = the existing case count = the next contiguous row index. Raises a clean LogicAddError on a
    non-canonical menu (explicit 0x06 / non-zero base) -- author those with a manual add_case + logic_edit text."""
    from .eb import disasm as _disasm
    entry, tag = _int(add, "entry"), _int(add, "tag")
    nth = _int(add, "nth", default=None, optional=True)
    f, ins, si = _locate_switch(eb, entry, tag, nth)
    if si.op not in (0x0B, 0x0D):
        raise LogicAddError(f"menu_row needs a CONTIGUOUS GetChoose switch (0x0B/0x0D); entry{entry}/tag{tag}'s "
                            f"switch is {_disasm.op_name(si.op)} (explicit 0x06) -- author this with a manual "
                            "add_case (explicit case) + a [[logic_edit]] text row instead")
    if si.base != 0:
        raise LogicAddError(f"menu_row needs a base-0 GetChoose switch (the picked row index IS the case value); "
                            f"entry{entry}/tag{tag}'s switch has base {si.base} -- not a 1:1 menu")
    new_row = len([e for e in si.edges if not e.is_default])
    return f, ins, si, new_row


def _widen_dialog_mask(eb_bytes, eb, f, sw_ins, new_row, warnings=None) -> bytes:
    """BEST-EFFORT leg B: OR the new row's bit into the ``EnableDialogChoices`` (0x7C) availability mask that
    sets up this menu (the last 0x7C before the switch), an in-place LENGTH-PRESERVING operand edit. A no-op
    (with a warning) when the mask is absent (text-gated menu) or computed at runtime (an expression operand
    -- ATE avail-word copy / dynamic flag-gated). For a TEXT-gated menu (no pre-tag / ``[PCHC]``) the mask is
    not consulted, so leaving it unwidened is harmless; this keeps a literal all-on mask looking consistent."""
    masks = [i for i in eb.instrs(f) if i.op == ENABLE_DIALOG_CHOICES and i.off < sw_ins.off]
    if not masks:
        if warnings is not None:
            warnings.append("menu_row: no EnableDialogChoices (0x7C) precedes the switch -- the menu enables its "
                            "rows from the text ([CHOO] rows / a [PCHC] count), so the new row relies on the .mes "
                            "row (+ count); no mask to widen.")
        return eb_bytes
    m = masks[-1]
    if m.arg_is_expr[0]:                                       # a RUNTIME-computed mask -- no literal to patch
        if warnings is not None:
            warnings.append("menu_row: the EnableDialogChoices mask is computed at runtime (expression operand), "
                            "not widened. v1 targets text-gated menus ([PCHC]/no pre-tag); if this menu hides "
                            "rows via a [PCHM] mask, the new row may not be selectable.")
        return eb_bytes
    if new_row >= 16:                                          # the availMask is a u16 -- bit 16+ is unrepresentable
        if warnings is not None:
            warnings.append(f"menu_row: row index {new_row} exceeds the 16-bit EnableDialogChoices mask -- the "
                            "availability bit can't be set. (A [PCHM] mask-gated menu with >16 rows is unsupported; "
                            "a text-gated menu doesn't consult the mask, so this is harmless there.)")
        return eb_bytes
    old = m.imm(0)
    new = (old | (1 << new_row)) & 0xFFFF
    if new == old:
        return eb_bytes                                        # bit already set
    ba = bytearray(eb_bytes)
    ba[m.off + 2:m.off + 4] = new.to_bytes(2, "little")        # op(1) + argflags(1) -> mask u16 LE at off+2
    return bytes(ba)


def _apply_menu_row(eb_bytes, add, alloc, warnings=None, *, message_txid=None) -> bytes:
    """The ``.eb`` side of a ``menu_row``: widen the availability mask (leg B), then ADD the dispatch arm at
    the next contiguous row index (leg A = ``add_case`` with ``case="auto"``, running ``effect``). The ``.mes``
    row-label leg (C) is applied by the build via :func:`menu_row_text_plan` / :func:`apply_menu_row_text`."""
    label = add.get("label")
    if not isinstance(label, str) or not label:
        raise LogicAddError("menu_row needs a non-empty `label` (the new row's menu text)")
    _int(add, "menu_txid")                                     # required: the .mes entry holding the choice rows
    if add.get("case", "auto") != "auto":
        raise LogicAddError('menu_row uses case="auto" (the new row is always the next contiguous choice index)')
    eb = EbScript.from_bytes(eb_bytes)
    f, ins, si, new_row = _menu_row_switch(eb, add)            # validates base-0 contiguous + computes new_row
    eb_bytes = _widen_dialog_mask(eb_bytes, eb, f, ins, new_row, warnings)
    return _apply_add_case(eb_bytes, add, alloc, warnings, message_txid=message_txid)   # leg A (the dispatch arm)


def _apply_one(eb_bytes, add, alloc, warnings=None, *, message_txid=None) -> bytes:
    kind = add.get("kind")
    if kind == "add_case":                                     # ADD a switch arm (length-changing table grow)
        return _apply_add_case(eb_bytes, add, alloc, warnings, message_txid=message_txid)
    if kind == "menu_row":                                     # ADD a selectable+labelled choice-menu row
        return _apply_menu_row(eb_bytes, add, alloc, warnings, message_txid=message_txid)
    if kind not in _ADD_KINDS:
        raise LogicAddError(f"logic_add unknown kind '{kind}' (kinds: {_ADD_KINDS} + 'add_case'/'menu_row')")
    where = add.get("where", "prepend")
    if where not in ("prepend", "after"):
        raise LogicAddError(f"logic_add where='{where}' is not supported (use 'prepend' or 'after'; "
                            "'after' takes an after_op anchor)")
    entry, tag = _int(add, "entry"), _int(add, "tag")
    eb = EbScript.from_bytes(eb_bytes)
    if not (0 <= entry < eb.entry_count) or eb.entry(entry).empty:
        raise LogicAddError(f"logic_add entry {entry} is empty or out of range (0..{eb.entry_count - 1})")
    f = eb.entry(entry).func_by_tag(tag)
    if f is None:
        raise LogicAddError(f"logic_add entry {entry} has no function tag {tag}")
    core = _core_bytes(add, alloc, warnings, message_txid=message_txid)
    if where == "prepend":
        return _edit.insert_in_function(eb_bytes, entry, tag, 0, core)   # the always-safe rel_off=0 prepend
    return _insert_after(eb_bytes, eb, f, entry, tag, add, core, warnings)   # mid-function (keystone rebuild)


def _normalize_adds(adds):
    """The canonical filtered add list -- shared by :func:`apply_logic_adds` and :func:`plan_messages` so a
    message txid keyed by index lines up with the add the build actually applies. Raises on a non-list or a
    non-table element (the same clean errors the build/Check surface)."""
    if adds is None:
        return []
    if not isinstance(adds, (list, tuple)):                     # a single [logic_add] table (or junk) -> clean error
        raise LogicAddError("logic_add must be an array of tables ([[logic_add]]), not "
                            f"{type(adds).__name__} (you likely wrote [logic_add] instead of [[logic_add]])")
    adds = [a for a in adds if a]
    for a in adds:
        if not isinstance(a, dict):
            raise LogicAddError(f"each logic_add must be a table, got {type(a).__name__}")
    return adds


def plan_messages(adds):
    """The appended ``.mes`` lines a ``[[logic_add]]`` list needs, in apply order: ``[(idx, message,
    speaker, tail)]`` for every add that SHOWS a line (a ``show_line`` or any kind with ``message =``).
    ``idx`` is the index into the normalized (filtered) add list -- the SAME index :func:`apply_logic_adds`
    enumerates -- so the build can allocate one txid per entry and hand them back as ``message_txids``."""
    out = []
    for idx, add in enumerate(_normalize_adds(adds)):
        msg = _add_message(add)
        if msg is not None:
            out.append((idx, msg, add.get("speaker"), add.get("tail")))
    return out


def apply_logic_adds(eb_bytes, adds, *, guard_base=None, guard_window=None, reserved_flags=None,
                     message_txids=None, warnings=None) -> bytes:
    """Apply every ``[[logic_add]]`` to ``eb_bytes`` (a guarded PREPEND, or a mid-function insert for
    ``where="after"``) and return the new bytes. Empty -> byte-identical. Raises :class:`LogicAddError` on
    any unsafe add. ``guard_base``/``guard_window`` confine auto once-guards to a campaign member's flag
    block; ``reserved_flags`` is the project's OTHER authored safe-band flags (so a guard never aliases one).
    ``message_txids`` maps a normalized-add index (see :func:`plan_messages`) to the txid of its appended
    ``.mes`` line -- required for any add that shows a message. ``warnings`` (a list) collects advisories."""
    adds = _normalize_adds(adds)
    if not adds:
        return bytes(eb_bytes)
    message_txids = message_txids or {}
    alloc = _GuardAlloc(guard_base, guard_window, adds, reserved_flags)
    if any(a.get("kind") == "menu_row" for a in adds):         # leg-A/leg-C alignment guard (see below)
        _assert_menu_row_switches(EbScript.from_bytes(eb_bytes), adds)
    out = bytes(eb_bytes)
    for idx, add in enumerate(adds):
        out = _apply_one(out, add, alloc, warnings, message_txid=message_txids.get(idx))
    return out


# --- menu_row leg C: the .mes row-label splice (applied by the build, NOT part of the .eb byte stream) ---
_PCHC_RE = re.compile(r"\[PCHC=(\d+),(\d+)((?:,\d+)*)\]")      # pre-choose config: count, cancel-row, +extra fields
_TRAILING_TAGS_RE = re.compile(r"(?:\[[A-Z][A-Z0-9]*(?:=[^\]]*)?\])+$")   # a run of [TAG]/[TAG=..] at the very end


def _switch_off(eb, add):
    """The absolute byte offset of the switch an ``add_case``/``menu_row`` targets on ``eb``'s bytes, or None for
    a non-dispatch add. Used to detect two dispatch adds hitting the SAME switch regardless of how ``nth`` is
    spelled (``None`` vs an explicit ``0`` on a single-switch function resolve to the same instruction)."""
    if add.get("kind") not in _DISPATCH_KINDS:
        return None
    _f, ins, _si = _locate_switch(eb, _int(add, "entry"), _int(add, "tag"),
                                  _int(add, "nth", default=None, optional=True))
    return ins.off


def _assert_menu_row_switches(eb, adds):
    """Reject a ``menu_row`` that shares its switch with ANY other dispatch add (``add_case``/``menu_row``).
    The ``menu_row`` row index (leg C) is planned from the PRE-add switch, while the dispatch case (leg A) is
    computed from the LIVE bytes as adds apply sequentially -- so a second dispatch add growing the same switch
    first would land leg A on a different case than the planned row, mis-aligning the menu (no error otherwise).
    Keys by switch OFFSET, so it also catches ``nth=None`` vs ``nth=0`` duplicates + two menu_rows on one switch.
    ``eb`` = the pre-add bytes; a non-locatable other add is skipped (its own miss surfaces at apply)."""
    dispatch = [(i, a) for i, a in enumerate(adds) if a.get("kind") in _DISPATCH_KINDS]
    offs = {}
    for i, a in dispatch:
        try:
            offs[i] = _switch_off(eb, a)
        except LogicAddError:
            offs[i] = None                                     # the other add's own error surfaces at apply
    for i, a in dispatch:
        if a.get("kind") != "menu_row" or offs[i] is None:
            continue
        for j, _b in dispatch:
            if j != i and offs[j] == offs[i]:
                raise LogicAddError(f"menu_row at index {i} shares its switch (entry{_int(a, 'entry')}/"
                                    f"tag{_int(a, 'tag')}) with another dispatch add (add_case/menu_row) at index "
                                    f"{j} -- they would mis-align the row index. Use ONE menu_row per switch, or "
                                    "split across fields.")


def menu_row_text_plan(eb_bytes, adds):
    """For each ``menu_row`` add (in normalized order): ``(idx, menu_txid, label, new_row)`` -- the data the
    build needs to splice the row LABEL into the donor ``.mes``. ``new_row`` is read from the ORIGINAL switch
    (``eb_bytes`` = the pre-``logic_add`` bytes), so it matches the dispatch arm :func:`apply_logic_adds` adds.
    Empty -> no ``.mes`` work. :func:`_assert_menu_row_switches` enforces ONE dispatch add per switch (a second
    would mis-align the row index). Raises a clean :class:`LogicAddError` on a non-canonical menu."""
    adds = _normalize_adds(adds)
    if not any(a.get("kind") == "menu_row" for a in adds):
        return []
    eb = EbScript.from_bytes(eb_bytes)
    _assert_menu_row_switches(eb, adds)
    out = []
    for idx, add in enumerate(adds):
        if add.get("kind") != "menu_row":
            continue
        label = add.get("label")
        if not isinstance(label, str) or not label:
            raise LogicAddError("menu_row needs a non-empty `label` (the new row's menu text)")
        if "\n" in label:
            raise LogicAddError(f"menu_row label may not contain a newline (it would inject a phantom row): {label!r}")
        _f, _ins, _si, new_row = _menu_row_switch(eb, add)
        out.append((idx, _int(add, "menu_txid"), label, new_row))
    return out


def apply_menu_row_text(body, plan, lang, warnings=None):
    r"""Leg C: splice each planned ``menu_row``'s ``\n[MOVE=18,0]<label>`` row into the menu's single ``.mes``
    entry (the verbatim donor body), bumping a ``[PCHC]`` row count. A VERIFIED splice (every other entry stays
    byte-identical, via :func:`logic_edit.verified_mes_splice`). Fails CLOSED on a ``[PCHM]`` mask-gated menu, a
    missing/non-choice entry, an unsupported trailing window tag (only a final ``[IMME]`` is handled), or a row
    count that doesn't match the dispatch (so the row index and case stay 1:1). ``plan`` =
    :func:`menu_row_text_plan`; empty plan/body -> unchanged."""
    if not plan or not body:
        return body
    from . import logic_edit as _le
    from .dialogue import parse_mes
    for (_idx, menu_txid, label, new_row) in plan:
        ent = parse_mes(body).get(menu_txid)
        if ent is None:
            raise LogicAddError(f"menu_row: menu_txid {menu_txid} not found in the {lang} .mes")
        text = ent.text
        choo = text.find("[CHOO]")
        if choo < 0:
            raise LogicAddError(f"menu_row: menu_txid {menu_txid} is not a choice menu (no [CHOO] tag) in the "
                                f"{lang} .mes")
        if "[PCHM=" in text:                                   # mask-gated (any arity) -- v1 fails closed
            raise LogicAddError(f"menu_row: menu_txid {menu_txid} is a [PCHM] mask-gated menu -- v1 targets "
                                "text-gated menus ([PCHC] / no pre-tag); a mask-gated row is a follow-up")
        after = text[choo + len("[CHOO]"):]                    # the row list (then maybe a trailing tag run)
        tail = _TRAILING_TAGS_RE.search(after)
        tail_str = tail.group(0) if tail else ""
        if tail_str and tail_str != "[IMME]":                  # an unknown trailing window tag -> don't corrupt it
            raise LogicAddError(f"menu_row: menu_txid {menu_txid} ends with an unsupported trailing tag "
                                f"{tail_str!r} ({lang} .mes) -- v1 handles plain rows (+ a final [IMME])")
        rows = after[:len(after) - len(tail_str)].split("\n")  # the row segments (excluding the trailing tag run)
        if len(rows) != new_row:
            raise LogicAddError(f"menu_row: menu_txid {menu_txid} has {len(rows)} row(s) but the dispatch expects "
                                f"the new row at index {new_row} ({lang} .mes) -- the menu's rows and its "
                                "GetChoose switch aren't 1:1 (donor drift / not a single-line canonical menu)")
        seg = "\n" + CHOICE_INDENT + label
        new_text = (text[:len(text) - len(tail_str)] + seg + tail_str) if tail_str else (text + seg)
        cm = _PCHC_RE.search(text)
        if cm and cm.start() < choo:                           # a [PCHC] BEFORE the rows: bump count, keep the rest
            new_text = (new_text[:cm.start()] + f"[PCHC={int(cm.group(1)) + 1},{cm.group(2)}{cm.group(3)}]"
                        + new_text[cm.end():])
        elif warnings is not None:                             # no pre-tag: CANCEL (B) = the (new) last row
            warnings.append(f"menu_row: menu_txid {menu_txid} has no pre-tag, so CANCEL (B) returns the LAST row "
                            "-- the new row is now last, so B will trigger it. Add a [PCHC] cancel row if that's "
                            "unwanted.")
        body = _le.verified_mes_splice(body, menu_txid, new_text, lang=lang, err=LogicAddError)
    return body
