"""Phase 4a: length-CHANGING in-place ADDITIONS to a verbatim fork's ``.eb`` -- PREPEND a guarded effect to
an existing routine. The structural sibling of :mod:`ff9mapkit.logic_edit` (length-PRESERVING value swaps).

Where ``[[logic_edit]]`` overwrites an operand same-width, ``[[logic_add]]`` ADDS instructions, which changes
the ``.eb``'s length. The ONLY length-changing primitive used is
:func:`ff9mapkit.eb.edit.insert_in_function` with ``rel_off=0`` -- the documented, 676/676-proven, ALWAYS-safe
PREPEND (the engine is uniformly IP-relative, so the whole function body shifts together; safe even over a
0x06/0x0B switch table). The riskier shapes (mid-function insert, switch-case relocation, whole-function
rebuild) are deferred to Phase 4b: a scoping sweep proved :func:`ff9mapkit.eb.cmdasm.assemble_instruction`
round-trips 100% of field instructions, but it does NOT relocate switch-table case offsets, so a length change
*before/inside* a switch-bearing function can only be done by a wholesale-discard ``replace_function_body`` or
this rel_off=0 prepend -- never a generic mid-function rebuild.

Kinds:
  * ``set_flag`` -- write a GLOB story flag. IDEMPOTENT, so prepended UNGATED into any routine.
  * ``give_item`` / ``give_gil`` -- CUMULATIVE (each call adds more), so wrapped in the FF9 chest once-guard
    ``if(!guard){guard=1; body}`` (the guard flag auto-allocated from the safe band) -- UNLESS it's a tag-3
    talk handler with ``repeat = true`` (a deliberately repeatable per-interaction effect).

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
_ADD_KINDS = ("set_flag", "give_item", "give_gil")
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


def _effect_body(add) -> bytes:
    """The raw effect bytes for one add (no guard) -- reuses the content encoders."""
    kind = add.get("kind")
    if kind == "set_flag":
        idx, val = _int(add, "flag"), _int(add, "value", default=1, optional=True)
        if not _flags.is_safe_custom(idx):
            raise LogicAddError(f"set_flag index {idx} is outside the safe custom band "
                                f"[{_flags.FIRST_SAFE_FLAG}, {_flags.CHOICE_SCRATCH_FLOOR}) (or reserved)")
        return _region.set_var(GLOB_BOOL, idx, val)
    if kind == "give_item":
        count = _int(add, "count", default=1, optional=True)
        if not (1 <= count <= 255):
            raise LogicAddError(f"give_item count {count} out of range (1-255; AddItem count is one byte)")
        try:
            return _event.give_item(add.get("item"), count)        # name or id, resolved by items
        except (ValueError, KeyError) as ex:
            raise LogicAddError(f"give_item: {ex}")
    if kind == "give_gil":
        amount = _int(add, "amount")
        if not (0 < amount <= _GIL_CAP):
            raise LogicAddError(f"give_gil amount {amount} out of range (1-{_GIL_CAP})")
        return _event.give_gil(amount)
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


def _core_bytes(add, alloc, warnings=None) -> bytes:
    """The bytes to prepend for one add: the effect, guarded unless it's idempotent (set_flag) or a
    deliberately-repeatable tag-3 talk effect (``repeat = true``)."""
    body = _effect_body(add)
    if add.get("kind") not in _CUMULATIVE:
        return body                                            # set_flag -- idempotent, ungated
    if add.get("repeat"):
        if _int(add, "tag") != TALK_TAG:
            raise LogicAddError(f"logic_add {add['kind']} repeat=true is only allowed on a tag-{TALK_TAG} "
                                f"talk handler (got tag {_int(add, 'tag')}); else it would fire every frame")
        if warnings is not None:                               # tag-3 is talk for an NPC but action-press for a region
            warnings.append(f"[[logic_add]] {add['kind']} repeat=true on entry {_int(add, 'entry')} tag {TALK_TAG} "
                            "re-fires on EVERY interaction (NPC talk / region action-button press), not once")
        return body                                            # an opt-in per-interaction repeat
    return _guarded(body, alloc.take(add))                     # default: once-guarded (safe in any routine)


def _apply_one(eb_bytes, add, alloc, warnings=None) -> bytes:
    if add.get("kind") not in _ADD_KINDS:
        raise LogicAddError(f"logic_add unknown kind '{add.get('kind')}' (kinds: {_ADD_KINDS})")
    where = add.get("where", "prepend")
    if where != "prepend":
        raise LogicAddError(f"logic_add where='{where}' is not supported in Phase 4a (only 'prepend'); "
                            "mid-function placement needs switch relocation (Phase 4b)")
    entry, tag = _int(add, "entry"), _int(add, "tag")
    eb = EbScript.from_bytes(eb_bytes)
    if not (0 <= entry < eb.entry_count) or eb.entry(entry).empty:
        raise LogicAddError(f"logic_add entry {entry} is empty or out of range (0..{eb.entry_count - 1})")
    if eb.entry(entry).func_by_tag(tag) is None:
        raise LogicAddError(f"logic_add entry {entry} has no function tag {tag}")
    core = _core_bytes(add, alloc, warnings)
    return _edit.insert_in_function(eb_bytes, entry, tag, 0, core)   # the always-safe rel_off=0 prepend


def apply_logic_adds(eb_bytes, adds, *, guard_base=None, guard_window=None, reserved_flags=None,
                     warnings=None) -> bytes:
    """Apply every ``[[logic_add]]`` to ``eb_bytes`` as a guarded PREPEND and return the new bytes. Empty ->
    byte-identical. Raises :class:`LogicAddError` on any unsafe add. ``guard_base``/``guard_window`` confine
    auto once-guards to a campaign member's flag block; ``reserved_flags`` is the project's OTHER authored
    safe-band flags (so a guard never aliases one). ``warnings`` (a list) collects advisories."""
    if adds is None:
        adds = []
    if not isinstance(adds, (list, tuple)):                     # a single [logic_add] table (or junk) -> clean error
        raise LogicAddError("logic_add must be an array of tables ([[logic_add]]), not "
                            f"{type(adds).__name__} (you likely wrote [logic_add] instead of [[logic_add]])")
    adds = [a for a in adds if a]
    for a in adds:
        if not isinstance(a, dict):
            raise LogicAddError(f"each logic_add must be a table, got {type(a).__name__}")
    if not adds:
        return bytes(eb_bytes)
    alloc = _GuardAlloc(guard_base, guard_window, adds, reserved_flags)
    out = bytes(eb_bytes)
    for add in adds:
        out = _apply_one(out, add, alloc, warnings)
    return out
