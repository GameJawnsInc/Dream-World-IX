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
    give item / gil, then set a story flag. Order: reply -> give_item -> gil -> set_flag (set_flag
    last so anything reading it sees the final state)."""
    parts = []
    if reply_txid is not None:
        parts.append(_event.message(reply_txid))
    if "give_item" in opt:
        gi = opt["give_item"]
        parts.append(_event.give_item(gi[0], int(gi[1]) if len(gi) > 1 else 1))   # gi[0] = id or name
    if "gil" in opt:
        parts.append(_event.give_gil(int(opt["gil"])))
    if "set_flag" in opt:
        sf = opt["set_flag"]
        parts.append(_event.set_flag(int(sf[0]), int(sf[1]) if len(sf) > 1 else 1))
    return b"".join(parts)


def pre_choose(ch: dict) -> tuple[bytes, str]:
    """Pre-choose config for a choice: which row is highlighted by DEFAULT, which row CANCEL (B) picks,
    and statically GREYED/disabled options. Returns ``(setup_bytes, text_tag)`` -- the setup is an
    ``EnableDialogChoices`` opcode emitted before the window (see :func:`region_body`), the tag is
    prepended to the choice text. Returns ``(b"", "")`` when nothing is configured, so a plain choice
    stays byte-identical.

    Mechanism (Memoria ``Dialog.SetupChoose`` + ``ETb.SetChooseParam``): the opcode sets the
    availability mask (bit i = row i on, LSB-first) + the default row; the text tag tells the dialog to
    apply them. ``[PCHM=count,cancel]`` applies the MASK (grey out + skip disabled rows);
    ``[PCHC=count,cancel]`` sets count/cancel/default WITHOUT disabling. A disabled row keeps its text
    line and the engine just skips the cursor over it, so ``GetChoose()`` still returns ABSOLUTE indices
    -- the per-option :func:`branch` is unaffected. A disabled default/cancel auto-remaps to the nearest
    active row (engine-side)."""
    options = ch.get("options", [])
    n = len(options)
    disabled = [bool(o.get("disabled")) for o in options]
    default = int(ch.get("default", 0))
    cancel = int(ch["cancel"]) if "cancel" in ch else (n - 1)   # engine default cancel = last row
    has_disable = any(disabled)
    if not (has_disable or "default" in ch or "cancel" in ch):
        return b"", ""                                          # nothing configured -> byte-identical
    # Availability mask = the EXACT bits for the (enabled) rows -- e.g. 3 rows all on -> 0b111 = 7.
    # NOT 0xFFFF: getv2 sign-extends 0xFFFF to -1, and ETb.SetChooseParam's loop is `while availMask>0`,
    # so a negative mask never runs and the default collapses to 0 (verified in-game). (1<<n)-1 stays
    # positive for any realistic row count.
    mask = sum(1 << i for i in range(n) if not disabled[i])
    tag = f"[PCHM={n},{cancel}]" if has_disable else f"[PCHC={n},{cancel}]"
    return opcodes.enable_dialog_choices(mask, default), tag


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
