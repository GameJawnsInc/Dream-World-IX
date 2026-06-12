"""Dialogue CHOICES -- show the player a menu of options and branch on the pick.

This is the interaction / puzzle primitive: a merchant, a lever with a "Yes/No", a quest-giver. It's
the conditional-region expression machinery (:mod:`ff9mapkit.content.region`) pointed at the engine's
choice result instead of a story flag.

Grounded BYTE-FOR-BYTE in real FF9 (the Black Mage shop, field 817):

    WindowSync( 0, 128, 97 )                 // the PROMPT + the option rows are ONE text entry:
                                             //   "...Can I help you?[CHOO][MOVE=18,0]Buy/Sell\n...Nothing"
    switch ( GetDialogChoice ) from 0 {      // branch on the picked row
        case +0: ...   case +1: ... }

Engine facts (Memoria source):
  * The window is SYNCHRONOUS (``MES`` 0x1F "wait until it closes"), so the pick is finalised before
    the next opcode runs; ``Dialog`` stores it in ``ETb.sChoose``.
  * A script READS the pick via the expression sysvar token ``B_SYSVAR`` (0x7A) with code 9 ->
    ``GetSysvar(9)`` -> ``ETb.GetChoose()`` (0-based row index). See :func:`region.cond_sysvar_eq`.
  * With no ``[PCHC]``/``[PCHM]`` pre-tags the choice count comes from the rows (all enabled), and
    CANCEL (B) returns the LAST row -- so put the "decline" option last.

The prompt/option TEXT (the ``[CHOO][MOVE=18,0]`` rows) is assembled in :mod:`ff9mapkit.build`
(``collect_text``); here we build only the SCRIPT side: the window call + the per-option branch.
"""

from __future__ import annotations

from ..eb import opcodes
from . import event as _event, region as _region

# zone-triggered choices auto-allocate a GLOB gate flag from here (clear of events 8000 + cutscene
# 8100). It must be GLOB (gEventGlobal is large); the per-field MAP array is only 80 bytes, so a high
# index there is out of bounds and crashes. once-per-visit is done by resetting this flag in the
# region's Init (re-runs each field load), not by a transient MAP flag.
CHOICE_FLAG_BASE = 8200


def option_body(opt: dict, reply_txid: int | None = None) -> bytes:
    """Compose ONE option's actions (the body run if the player picks it). Reuses the event action
    vocabulary so a choice option does exactly what an event does: an optional reply line, then
    give/take item, gil, set a story flag, optionally advance the ScenarioCounter, and (LAST) WARP to
    another field. Order: reply -> give_item -> remove_item -> gil -> set_flag -> set_scenario -> warp.
    ``warp`` is last because a Field op transitions away (anything after it is unreachable) -- this is the
    World-Hub journey-pick primitive: a menu row that seeds the beat then warps into the chosen field."""
    parts = []
    if reply_txid is not None:
        parts.append(_event.message(reply_txid))
    if "give_item" in opt:
        gi = opt["give_item"]
        parts.append(_event.give_item(gi[0], int(gi[1]) if len(gi) > 1 else 1))   # gi[0] = id or name
    if "remove_item" in opt:
        ri = opt["remove_item"]
        parts.append(_event.take_item(ri[0], int(ri[1]) if len(ri) > 1 else 1))   # symmetric: a trade option
    if "gil" in opt:
        parts.append(_event.give_gil(int(opt["gil"])))
    if "set_flag" in opt:
        sf = opt["set_flag"]
        parts.append(_event.set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
    if "set_scenario" in opt:
        parts.append(_event.set_scenario(int(opt["set_scenario"])))
    if "warp" in opt:
        parts.append(_event.warp(int(opt["warp"])))                               # LAST: transitions away
    return b"".join(parts)


def _gated(o: dict) -> bool:
    """An option whose visibility depends on a story flag at runtime (flag-gated hide)."""
    return "requires_flag" in o or "requires_flag_clear" in o


def dynamic_mask_setup(options, default: int) -> bytes:
    """Build the availability mask AT RUNTIME from per-option story flags, then point
    ``EnableDialogChoices`` at it -- the real-field pattern (Dali/Storage's moogle-mail menu:
    ``set_var`` the base, ``if(flag) or_var`` each conditional bit, then ``EnableDialogChoices(VAR | .., 0)``).

    Always-visible rows form the base word; each flag-gated row ORs its bit in only when its condition
    holds (``requires_flag`` -> visible when SET, ``requires_flag_clear`` -> visible when CLEAR). The
    mask lives in a high scratch word (``region.MASK_SCRATCH_IDX``) and is read back as an UNSIGNED
    UInt16 expression-arg (no sign trap). Statically ``disabled`` rows are simply never ORed in."""
    base = sum(1 << i for i, o in enumerate(options) if not o.get("disabled") and not _gated(o))
    parts = [_region.set_var(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX, base)]
    for i, o in enumerate(options):
        if o.get("disabled") or not _gated(o):
            continue
        if "requires_flag" in o:
            cond = _region.cond_truthy(_region.GLOB_BOOL, int(o["requires_flag"]))
        else:
            cond = _region.cond_not(_region.GLOB_BOOL, int(o["requires_flag_clear"]))
        parts.append(_region.if_block(cond, _region.or_var(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX, 1 << i)))
    mask_expr = _region.var_expr(_region.GLOB_UINT16, _region.MASK_SCRATCH_IDX)
    parts.append(opcodes.enable_dialog_choices_var(mask_expr, default))
    return b"".join(parts)


def pre_choose(ch: dict) -> tuple[bytes, str]:
    """Pre-choose config for a choice: which row is highlighted by DEFAULT, which row CANCEL (B) picks,
    and which options are HIDDEN (statically via ``disabled``, or flag-gated via ``requires_flag`` /
    ``requires_flag_clear``). Returns ``(setup_bytes, text_tag)`` -- ``setup`` runs before the window
    (see :func:`region_body`), ``tag`` is prepended to the choice text. ``(b"", "")`` when nothing is
    configured, so a plain choice stays byte-identical.

    Mechanism (Memoria ``Dialog.SetupChoose`` + ``ETb.SetChooseParam``): an ``EnableDialogChoices``
    opcode sets the availability mask (bit i = row i shown, LSB-first) + the default row; the
    ``[PCHM=count,cancel]`` text tag tells the dialog to APPLY the mask (hidden rows get no widget),
    ``[PCHC=count,cancel]`` sets count/cancel/default WITHOUT hiding. ``GetChoose()`` returns the
    ABSOLUTE row index regardless of hides, so the per-option :func:`branch` is unaffected.

    Three modes: flag-gated (any ``requires_flag``) -> a runtime mask (:func:`dynamic_mask_setup`);
    static-hide (any ``disabled``) -> a literal partial mask; default/cancel only -> a literal all-on
    mask ``(1<<n)-1`` (NOT 0xFFFF, which sign-extends to -1 and breaks ``SetChooseParam``'s
    ``while availMask>0`` loop -> default collapses to 0)."""
    options = ch.get("options", [])
    n = len(options)
    default = int(ch.get("default", 0))
    cancel = int(ch["cancel"]) if "cancel" in ch else (n - 1)   # engine default cancel = last row
    has_static = any(o.get("disabled") for o in options)
    has_dynamic = any(_gated(o) for o in options)
    if not (has_static or has_dynamic or "default" in ch or "cancel" in ch):
        return b"", ""                                          # nothing configured -> byte-identical
    if has_dynamic:
        return dynamic_mask_setup(options, default), f"[PCHM={n},{cancel}]"
    if has_static:
        mask = sum(1 << i for i in range(n) if not options[i].get("disabled"))
        return opcodes.enable_dialog_choices(mask, default), f"[PCHM={n},{cancel}]"
    return opcodes.enable_dialog_choices((1 << n) - 1, default), f"[PCHC={n},{cancel}]"


def branch(option_bodies) -> bytes:
    """``if (GetChoose()==0){b0} if (GetChoose()==1){b1} ...`` -- one independent if-block per option
    (exactly how FF9 lays out choice handlers). Options with an empty body emit nothing."""
    out = b""
    for i, body in enumerate(option_bodies):
        if body:
            out += _region.if_block(_region.cond_sysvar_eq(_region.SYSVAR_CHOICE, i), body)
    return out


def region_body(prompt_txid: int, option_bodies, *, window: int = 1, flags: int = 128,
                setup: bytes = b"") -> bytes:
    """The choice block usable in ANY trigger context (an NPC talk OR a walk-in region): lock the
    player, (optional pre-choose ``setup``), open the prompt+options window, branch on the pick, restore
    control. **No RETURN** -- the caller adds it (NPC) or wraps it in a flag-gated region body (zone).

    ``setup`` is the optional ``EnableDialogChoices`` opcode from :func:`pre_choose` (default/cancel/
    disabled config); it MUST run before the window opens. Why DisableMove/EnableMove: the engine does
    NOT block field movement while a dialog is open, so without this the d-pad would move BOTH the menu
    cursor AND the character. Real FF9 wraps a choice in DisableMove...EnableMove (e.g. the Black Mage
    shop), and the menu still navigates because choice input comes from the dialog system, not field
    control."""
    return (opcodes.DISABLE_MOVE + setup + opcodes.window_sync(window, flags, prompt_txid)
            + branch(option_bodies) + opcodes.ENABLE_MOVE)


def speak_body(prompt_txid: int, option_bodies, *, window: int = 1, flags: int = 128,
               setup: bytes = b"") -> bytes:
    """A complete ``_SpeakBTN`` (NPC talk) body for a choice: the choice block + RETURN. ``flags`` 128
    is the standard field dialogue flag (same as plain NPC dialogue). ``setup`` = optional pre-choose
    opcode (see :func:`pre_choose`)."""
    return region_body(prompt_txid, option_bodies, window=window, flags=flags, setup=setup) + opcodes.RETURN
