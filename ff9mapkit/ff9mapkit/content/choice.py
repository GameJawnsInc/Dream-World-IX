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

from .. import flags as _flags
from ..eb import opcodes
from . import event as _event, region as _region

# zone-triggered choices auto-allocate a GLOB gate flag from here (the safe-band auto bands -- the map
# + why they moved off the legacy 8200 base live in flags.py). It must be GLOB (gEventGlobal is
# large); the per-field MAP array is only 80 bytes, so a high index there is out of bounds and
# crashes. once-per-visit is done by resetting this flag in the region's Init (re-runs each field
# load), not by a transient MAP flag.
CHOICE_FLAG_BASE = _flags.AUTO_CHOICE_BASE


def option_body(opt: dict, reply_txid: int | None = None, input_slots: dict | None = None,
                input_specs: dict | None = None, qte_slots: dict | None = None) -> bytes:
    """Compose ONE option's actions (the body run if the player picks it). Reuses the event action
    vocabulary so a choice option does exactly what an event does: an optional reply line, then
    give/take item, gil, set a story flag, optionally advance the ScenarioCounter, and (LAST) WARP to
    another field. Order: input -> reply -> give_item -> remove_item -> gil -> set_flag -> set_scenario
    -> warp. ``input`` (a ``[[numeric_input]]`` name -> its seated entry slot via ``input_slots``) runs
    FIRST -- the modal stepper blocks until Confirm/Cancel, and a submit loads gMesValue slot 0, so a
    ``reply`` can echo the number with ``[NUMB=0]``. ``warp`` is last because a Field op transitions away
    (anything after it is unreachable) -- this is the World-Hub journey-pick primitive: a menu row that
    seeds the beat then warps into the chosen field. NOTE: a choice with any ``input`` row must dispatch
    via :func:`switch_body` (the stepper opens windows -- the nested-window sysvar-9 law)."""
    parts = []
    if "input" in opt:
        from . import numinput as _numinput
        slot = (input_slots or {}).get(str(opt["input"]))
        if slot is None:
            raise ValueError(f"choice option input {opt['input']!r} has no seated "
                             f"[[numeric_input]] entry (validate should have caught this)")
        parts.append(_numinput.call_bytes(slot))
    if "qte" in opt:
        from . import qte as _qte_mod
        qslot = (qte_slots or {}).get(str(opt["qte"]))
        if qslot is None:
            raise ValueError(f"choice option qte {opt['qte']!r} has no seated "
                             f"[[qte]] entry (validate should have caught this)")
        parts.append(_qte_mod.call_bytes(qslot))
    if "recall" in opt:
        # re-load gMesValue slot 0 from that input's RESULT var so this row's reply
        # renders the SAVED number — slot 0 is transient and shared by every stepper's
        # echo (the NUMPAD Report row rendered the previous bid without this)
        from . import numinput as _numinput
        sp = (input_specs or {}).get(str(opt["recall"]))
        if sp is None:
            raise ValueError(f"choice option recall {opt['recall']!r} names no "
                             f"[[numeric_input]] (validate should have caught this)")
        parts.append(_numinput.recall_bytes(sp))
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
    if opt.get("save"):
        # A SAVE row -- open the real save menu from a dialogue choice, so one NPC can be the
        # innkeeper/purser AND the save point instead of standing next to a twin save-moogle prop.
        # `savepoint.save_act` is the same latched Menu(4,0) both real save families use
        # (GLOB(184)=1; Wait(3); Menu(4,0); Wait(3); GLOB(184)=0). It RETURNS to the menu's caller,
        # so it is NOT a transition and may sit before other actions.
        from . import savepoint as _sp
        parts.append(_sp.save_act())
    if "warp" in opt:
        # A choice that warps is ALWAYS a field transition, so it fades out first (fade=True) -- exactly
        # like a gateway/ladder. Without the fade the destination loads in the clear and you see its
        # camera-init frames (the World-Hub static-screen bug). entrance (optional) sets the arrival
        # entrance var; it is not the camera fix (the fade is) -- see event.warp.
        parts.append(_event.warp(int(opt["warp"]), entrance=opt.get("entrance"), fade=True))  # LAST: away
    elif "worldmap" in opt:
        # THE FERRY ARM -- this row sails to the OVERWORLD at a named landing, instead of warping to a
        # field. It is the same primitive a walk-out worldmap gateway uses (`worldexit.worldmap_exit_body`
        # with an explicit `arrive`), so a ferry destination and a door behave identically once taken:
        # usercontrol guard -> fade -> BOTH position blocks -> POSITION_PRESET_KEY -> computed WorldMap.
        #
        # Why a choice row and not four doors: stock FF9 books boat travel through a PERSON (the Blue
        # Narciss "Where to?"), and the alternative -- one walk-on zone per destination -- needs four
        # readable doors in the art. Borrowed art has none, so four invisible zones in one corridor are
        # unreadable and mutually triggerable. A menu is self-describing and cannot be entered by accident.
        #
        # Mutually exclusive with `warp` (both end the function by transitioning away).
        # ⚠ gate=False IS LOAD-BEARING. `worldmap_exit_body` defaults to emitting the walk-on region
        # prologue `ifnot (IsMovementEnabled) { return }`. We are inside a TALK handler, which opens with
        # DisableMove, so IsMovementEnabled is 0: the gate would take its early return, skip the entire
        # exit, and leave the player frozen with no window -- a SOFTLOCK. That is exactly how the first
        # Lantern Hall ferry shipped; the deployed bytes showed the `7a 02` gate returning before the
        # fade. A region prologue is not portable into a menu context.
        from . import worldexit as _wx
        wm = opt["worldmap"]
        on_exit = b""
        if "depart" in wm:
            # THE DEPARTURE ARM (scene-ladder rung 2b): write the pending-port code into the
            # world-flags byte before sailing -- the overworld's departure director consumes
            # (and clears) it on arrival at the stage. Assembled, not hand-packed: the byte
            # index (1872+) is beyond _set_var32's one-byte idx encoding.
            #
            # THE ORIGIN CACHE (rung 3c): Global.Int24[64] is the on-foot saved-position X --
            # the world mirror's record of where the player STOOD when they entered this hall,
            # untouched all through the field visit. The exit body's stage preset (arrive_writes,
            # emitted AFTER this on_exit block) overwrites it, so the origin would be lost by the
            # time the world's departure prologue runs. Cache the X into the kit-world band first;
            # the prologue box-tests it to stage the sail-out at the port the player boarded from.
            from ..eb.cmdasm import assemble_block as _asm
            from .. import flags as _fl
            b_idx, b_code = wm["depart"]
            on_exit = _asm(
                f"SET({{Global.Byte[{int(b_idx)}] const({int(b_code)}) B_LET B_EXPR_END}})\n"
                f"SET({{Global.Int24[{_fl.FERRY_ORIGIN_X_INT24}] Global.Int24[64] B_LET B_EXPR_END}})\n")
        parts.append(_wx.worldmap_exit_body(arrive=(float(wm["arrive"][0]), float(wm["arrive"][1])),
                                            arrive_face=int(wm.get("face", 0)), on_exit_body=on_exit,
                                            fade=True, gate=False, game=opt.get("_game")))  # LAST: away
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


# --------------------------------------------------------------- the SWITCH dispatch (op_0B) ---
SWITCH_OP = 0x0B          # JMP_SWITCH (contiguous). Layout, from eb.disasm.decode_switch (validated
                          # 100% boundary-aligned across all 5563 switches in the 676 shipping fields):
                          #   0B <n:u8> <base<<8 :u16> <default_reloff:u16> <case_reloff:u16> * n
                          # anchor = the instruction's offset + 1; target = anchor + reloff.


def switch_on_choice(option_bodies) -> bytes:
    """Dispatch on the player's dialog choice with ONE read, via ``op_05{GetSysvar(9)}`` + ``op_0B``.

    **Why this exists, and when you MUST use it instead of :func:`branch`.** ``branch`` emits an
    independent ``if(GetChoose()==i)`` block per option, and every block RE-READS sysvar 9 at the moment
    it runs. That is correct for a flat menu whose arms don't open dialogs -- but the moment one arm
    opens a SECOND choice window, that window overwrites sysvar 9, and every later ``if`` then tests the
    INNER answer. Concretely: pick row 0, then answer "No" (row 1) in the nested confirm, and the outer
    row-1 arm fires too.

    ``op_0B`` reads the selector ONCE (the preceding ``op_05`` pushes ``GetChoose()`` onto the calc
    stack) and jumps to exactly one arm, so nested windows are harmless. This is what FF9 itself does --
    field 300 @4278-4282 and field 2919 both push ``{op7A(9) op7F}`` and switch. Use it for any menu
    where more than one row has a body, or any row opens another window.

    ``option_bodies`` is one body per row, in row order; an empty/None body means "do nothing" (it gets
    an arm that jumps straight to the end, NOT a fall-through into the next row's body). Execution
    resumes after the whole block for every arm, including the default (an out-of-range pick)."""
    n = len(option_bodies)
    if n == 0:
        return b""
    bodies = [bytes(b or b"") for b in option_bodies]
    # Push the selector ONCE, immediately before the switch: op_05 {GetSysvar(9) END}. Byte-exact against
    # field 300 @4278 (`05 7a 09 7f`) followed by the 0x0B at @4282. Without this the switch dispatches on
    # whatever is already on the calc stack. The switch's case offsets are self-relative (anchor = its own
    # offset + 1), so prepending this does not disturb them.
    push = bytes([_region.EXPR_OP, _region.T_SYSVAR, _region.SYSVAR_CHOICE, _region.T_END])
    # Each arm ends with an unconditional hop to the common exit, so arms never fall into each other.
    # Lay the arms out first to learn their sizes, then back-fill the jumps.
    hop = 3                                             # JMP_UNCOND + i16
    sizes = [len(b) + hop for b in bodies]
    head = 2 + 2 * (2 + n)                              # op + count + base + default + n case offsets
    starts, p = [], head
    for s in sizes:
        starts.append(p)
        p += s
    end = p                                             # the common exit, just past the last arm
    anchor = 1                                          # decode_switch: anchor = instr.off + 1
    out = bytearray([SWITCH_OP, n])
    out += (0).to_bytes(2, "little")                    # base = 0 (rows are 0..n-1)
    out += (end - anchor).to_bytes(2, "little")         # default (out-of-range pick) -> the exit
    for st in starts:
        out += (st - anchor).to_bytes(2, "little")
    for i, b in enumerate(bodies):
        out += b
        skip = end - (starts[i] + len(b) + hop)         # bytes to skip to reach the exit
        out += bytes([_region.JMP_UNCOND]) + skip.to_bytes(2, "little")
    return push + bytes(out)


def switch_body(prompt_txid: int, option_bodies, *, window: int = 1, flags: int = 128,
                setup: bytes = b"") -> bytes:
    """:func:`region_body`'s switch-dispatched twin: lock control, (optional pre-choose ``setup``), open
    the prompt window, then :func:`switch_on_choice`, then restore control. **No RETURN** -- the caller
    adds it. Use this instead of :func:`region_body` for a multi-body or nested menu."""
    return (opcodes.DISABLE_MOVE + setup + opcodes.window_sync(window, flags, prompt_txid)
            + switch_on_choice(option_bodies) + opcodes.ENABLE_MOVE)
