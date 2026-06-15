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

A ``show_line`` (or any ``message =``) line is APPENDED to the donor ``.mes`` above its txids -- the same
append-and-resolve channel ``[[on_entry]]`` narration uses (:func:`build._verbatim_on_entry_messages`) -- so
the inserted ``WindowSync`` resolves into real text. A message ALWAYS implies a once-guard (a window in a
tread zone would re-open every frame), even on an otherwise-idempotent ``set_flag``.

The effect bytes reuse the proven :mod:`ff9mapkit.content.region` / :mod:`ff9mapkit.content.event` encoders
verbatim (zero new bytecode). The composed ``.eb`` is re-validated by :func:`ff9mapkit.eblint.lint_eb` before
the build ships it -- a bad add fails the BUILD (a clean :class:`LogicAddError`), never a silent mis-splice.
"""
from __future__ import annotations

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
            if a.get("kind") == "set_flag" and isinstance(a.get("flag"), int) and not isinstance(a.get("flag"), bool):
                self._used.add(a["flag"])

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
    except _cmdasm.CmdAsmError as ex:                           # ...is a clean failure, not a raw traceback
        raise LogicAddError(f"logic_add where='after': could not rebuild entry{_int(add, 'entry')}/"
                            f"tag{_int(add, 'tag')}: {ex}")
    return _edit.replace_function_body(eb_bytes, entry, tag, new_body)


def _apply_one(eb_bytes, add, alloc, warnings=None, *, message_txid=None) -> bytes:
    if add.get("kind") not in _ADD_KINDS:
        raise LogicAddError(f"logic_add unknown kind '{add.get('kind')}' (kinds: {_ADD_KINDS})")
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
    out = bytes(eb_bytes)
    for idx, add in enumerate(adds):
        out = _apply_one(out, add, alloc, warnings, message_txid=message_txids.get(idx))
    return out
