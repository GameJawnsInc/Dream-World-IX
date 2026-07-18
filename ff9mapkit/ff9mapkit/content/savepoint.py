"""Save-point synthesis -- a faithful FF9 save point, authored rather than grafted.

The FUNCTIONAL save is a single opcode: ``Menu(4, 0)`` (0x75) -> ``EventService.StartMenu`` ->
``OpenSaveMenu`` (``SaveLoadUI.SerializeType.Save``), byte-exact ``75 00 04 00``.

**What the byte census (2026-07-18) actually found.** Across FF9's 55 fields owning a true,
instruction-aligned ``Menu(4, 0)`` there are exactly TWO families, and neither jumps straight to the menu:

* **The save Moogle (48 fields).** One stamped template -- always a type-2 entry, 3 funcs, tag 3, spawned
  hidden (``SetObjectFlags(14)``), ~7.1-8.4 KB. Opcode-sequence similarity between the most distant
  instances is 90-94%: they are the same script. Field 407 (Dali/Storage Area, the barrel moogle) is a
  TYPICAL member, not an advanced one -- its tag 3 is the shared template; only its tag-1 loop is
  enlarged (374 B vs the template's 295) to hop out of the cask. The staging varies; the save act does not.
* **The moogle-less save point (7 Memoria / Crystal World fields).** A **686-byte** type-0 entry whose
  Init is a single ``return`` -- no model at all. A proximity poll, a "!" ``Bubble``, an option window, a
  confirm, the save. Ten times smaller than the moogle and, notably, a MORE complete save experience.

Both families run the same spine, which is what this module authors:

    lock control -> option menu -> Yes/No confirm -> GLOB(184)=1 ; Wait(3) ; Menu(4,0) ; Wait(3) ;
    GLOB(184)=0 -> restore control

So the kit SYNTHESIZES the save rather than grafting the moogle's un-graftable cluster. The region is the
navigable cousin of :mod:`content.jump`'s ``action`` region (same Init ``SetRegion`` / tread ``Bubble``
("!") / action shape), and no player-function graft is required -- the save is a self-contained engine
call. ``build.py`` also places a visible save Moogle at the zone by default, whose TALK runs the same
dispatch.

Still NOT synthesized (the deliberate gap): the moogle's reveal/hop and book+feather animation, and the
Tent / Select-party rows of the real option menu. The tent's HP restore is not visible in the field script
at all (the Memoria branch is only ``RunScriptSync`` + ``RemoveItem(253, 1)``), so shipping a Tent row
would mean guessing at the heal -- deferred rather than half-built. The verbatim carry
(``import <field> --save-moogle``) remains the way to get the full moogle act.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import choice as _choice
from . import event as _event
from . import region as _region

SAVE_MENU_ID = 4          # EventService.FF9Menu_Command case 4u -> OpenSaveMenu
SAVE_SUB_ID = 0           # OpenSaveMenu requires sub_id == 0

# The save LATCH: gEventGlobal[184] (`General_LoadedGame` in the HW symbol names). EVERY real save point --
# both families -- sets it to 1 immediately before Menu(4,0) and back to 0 immediately after, bracketed by
# Wait(3) on each side. Verified in the moogle family (field 300 entry 3 tag 3, `opC4(184)` at 4590/4608
# around the Menu at 4601) and in the moogle-less Memoria family (field 2919 entry 7 tag 1, 3632/3655
# around the Menu at 3648). Carried here because it is universal, not because its engine effect is
# understood -- treat it as part of the save handshake.
SAVE_LATCH_FLAG = 184
SAVE_LATCH_WAIT = 3       # the Wait(3) either side of the Menu call, in both families

# The real save point's MENU window: slot 2, flags 8 -- the small selection window, NOT the ordinary
# dialogue window (1, 128). Field 300 opens its option list with `WindowAsync(2, 8, 3)` and its Yes/No
# confirm with `WindowAsync(2, 8, 4)`.
CHOICE_WINDOW = 2
CHOICE_FLAGS = 8

# Default menu wording. Deliberately plain/neutral rather than a quote of FF9's own save-point strings --
# the kit ships no Square-Enix text (docs/PROVENANCE.md). Override per save point with `prompt` /
# `confirm` / `save_row` / `cancel_row` / `yes_row` / `no_row`.
DEFAULT_PROMPT = "What would you like to do?"
DEFAULT_CONFIRM = "Save your progress?"
DEFAULT_SAVE_ROW = "Save"
DEFAULT_CANCEL_ROW = "Cancel"
DEFAULT_YES_ROW = "Yes"
DEFAULT_NO_ROW = "No"


def save_act(*, latch: bool = True) -> bytes:
    """The save handshake itself, exactly as both real families spell it::

        GLOB(184) = 1 ; Wait(3) ; Menu(4, 0) ; Wait(3) ; GLOB(184) = 0

    ``latch=False`` drops the gEventGlobal[184] bracket (the bare pre-rung-2 behaviour)."""
    if not latch:
        return opcodes.menu(SAVE_MENU_ID, SAVE_SUB_ID)
    return (_event.set_flag(SAVE_LATCH_FLAG, 1, flag_class=_region.GLOB_BOOL)
            + opcodes.wait(SAVE_LATCH_WAIT)
            + opcodes.menu(SAVE_MENU_ID, SAVE_SUB_ID)
            + opcodes.wait(SAVE_LATCH_WAIT)
            + _event.set_flag(SAVE_LATCH_FLAG, 0, flag_class=_region.GLOB_BOOL))


def _row0_only(txid: int, body: bytes) -> bytes:
    """Open a choice window and run ``body`` ONLY when the player picks row 0.

    **Why row 0 only, and why this helper exists.** ``choice.branch`` emits one INDEPENDENT if-block per
    option -- ``if(GetChoose()==0){b0} if(GetChoose()==1){b1}`` -- and every block re-reads sysvar 9. That
    is correct for a flat menu, but it breaks the moment a branch opens a SECOND choice window: the nested
    window overwrites sysvar 9, so the outer ``if(GetChoose()==1)`` then tests the INNER answer and can
    fire the wrong arm (pick "Save" then "No" -> GetChoose()==1 -> the outer Cancel arm runs too).

    The save flow is exactly that shape (option menu -> Yes/No confirm), so it is built with only row 0
    carrying a body at each level. ``branch`` skips empty bodies, so exactly one if-block is emitted per
    window and no stale sysvar read is possible. Any future row with a body (Tent, Party) must switch this
    to the real fields' pattern -- copy GetChoose into a scratch var and switch on THAT (``op_05{op7A(9)}``
    + ``op_0B``, as field 2919 does) -- NOT add a second body here."""
    return opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, txid) + _choice.branch([body])


def save_dispatch() -> bytes:
    """The bare functional save: ``DisableMove; Menu(4, 0); EnableMove; RETURN``.

    Kept as the no-text fallback (and the shape ``content.shop`` mirrors). The DEFAULT save point is
    :func:`save_dispatch_prompted` -- every real save point in FF9 asks before it saves."""
    return (opcodes.DISABLE_MOVE
            + opcodes.menu(SAVE_MENU_ID, SAVE_SUB_ID)
            + opcodes.ENABLE_MOVE + opcodes.RETURN)


def save_dispatch_mognet(prompt_txid: int, confirm_txid: int, mognet_body: bytes,
                         *, latch: bool = True) -> bytes:
    """The network-joined moogle's talk body -- a THREE-row menu: Save / Mognet / Cancel::

        DisableMove ; DisableMenu
        Window(2, 8, prompt)                     "Can I help you, kupo?"-shaped, [PCHC=3,2] in text
          row 0 Save   -> Window(2, 8, confirm) -> row 0 -> the latched save_act
          row 1 Mognet -> ``mognet_body``        (mognet.mognet_interaction_body -- guard + a/b/c)
          row 2 Cancel -> nothing
        EnableMenu ; EnableMove ; RETURN

    Dispatch is :func:`choice.switch_on_choice` (op_0B, ONE sysvar-9 read) -- the multi-body menu that
    :func:`_row0_only` structurally cannot host. The Save arm re-reads the choice AFTER opening the
    confirm window, which is safe: the hazard was ever only an outer chained-if re-reading a stale
    sysvar; a fresh read inside an already-dispatched arm is exactly how field 2919 does it.

    The 2-row :func:`save_dispatch_prompted` stays byte-frozen for [[savepoint]]s without a network
    moogle -- this function is a new path, taken only when the build wires a ``mognet_body``."""
    save_arm = (opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, confirm_txid)
                + _choice.switch_on_choice([save_act(latch=latch), b""]))
    return (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU
            + opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, prompt_txid)
            + _choice.switch_on_choice([save_arm, bytes(mognet_body), b""])
            + opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN)


def save_dispatch_prompted(prompt_txid: int, confirm_txid: int, *, latch: bool = True) -> bytes:
    """The FAITHFUL save interaction, rebuilt from the real script::

        DisableMove ; DisableMenu
        Window(2, 8, prompt)   -> row 0 "Save" ...
          Window(2, 8, confirm) -> row 0 "Yes" ...
            GLOB(184)=1 ; Wait(3) ; Menu(4,0) ; Wait(3) ; GLOB(184)=0
        EnableMenu ; EnableMove ; RETURN

    Both real families run an option menu and then a Yes/No confirm before the save (field 300:
    ``WindowAsync(2,8,3)`` then ``WindowAsync(2,8,4)``; field 2919: txid 454 then 457). The shipped
    pre-rung-2 save point jumped straight to ``Menu(4,0)`` on touch, which no save point in the game does.

    Cancel (row 1) and No (row 1) are deliberately BODILESS -- see :func:`_row0_only` for why that is a
    correctness requirement, not a shortcut."""
    return (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU
            + _row0_only(prompt_txid, _row0_only(confirm_txid, save_act(latch=latch)))
            + opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN)


def _assemble_entry(funcs) -> bytes:
    """Assemble a type-1 (region) entry from ``[(tag, body), ...]`` -- the func table (4 bytes/func:
    ``<tag:u16><fpos:u16>``) then the concatenated bodies. Same layout as :func:`content.jump`."""
    table = b""
    pos = len(funcs) * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
    return bytes([_region.REGION_ENTRY_TYPE, len(funcs)]) + table + b"".join(b for _, b in funcs)


def savepoint_region(zone, *, bubble: bool = True, dispatch: bytes | None = None) -> bytes:
    """A type-1 region entry for a save point: Init ``SetRegion(zone)`` / tread (tag 2) ``Bubble(1)`` (the
    floating "!" prompt, if ``bubble``) / action (tag 3) the save dispatch. Both trigger funcs are
    gated by :data:`content.region.MOVEMENT_GATE` (fire only while ``usercontrol == 1``), exactly like
    every real exit/switch/jump region.

    ``dispatch`` overrides the action body -- the build passes :func:`save_dispatch_prompted` (the faithful
    menu + confirm flow); ``None`` falls back to the bare :func:`save_dispatch`."""
    init = _region.set_region([tuple(p) for p in zone]) + opcodes.RETURN
    tread = _region.MOVEMENT_GATE + (opcodes.bubble(1) if bubble else b"") + opcodes.RETURN
    action = _region.MOVEMENT_GATE + (dispatch if dispatch is not None else save_dispatch())
    funcs = [(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)]
    return _assemble_entry(funcs)


def inject_savepoint(data, zone, *, bubble: bool = True, activate: bool = True,
                     dispatch: bytes | None = None):
    """Inject one save point: append a save-point region at the next free slot and arm it (``InitRegion``
    in Main_Init). Returns ``(new_bytes, region_slot)``. ``zone`` is a 4- or 5-point quad (the press
    area); ``bubble=False`` hides the "!" prompt (e.g. when a visible model already signals the save);
    ``dispatch`` supplies the action body (see :func:`savepoint_region`)."""
    eb = EbScript.from_bytes(data)
    slot = eb.first_free_slot()
    data = edit.append_entry(data, slot, savepoint_region(zone, bubble=bubble, dispatch=dispatch))
    if activate:
        data = edit.activate(data, opcodes.init_region(slot, 0))
    return data, slot


def inject_savepoints(data, savepoints, *, activate: bool = True, dispatches=None):
    """Inject every ``[[savepoint]]`` (each a dict with ``zone`` + optional ``bubble``). ``dispatches``, if
    given, is one action body per save point (same order). Returns ``(new_bytes, [slot, ...])``."""
    slots = []
    for i, sp in enumerate(savepoints):
        data, slot = inject_savepoint(data, sp["zone"], bubble=sp.get("bubble", True), activate=activate,
                                      dispatch=(dispatches[i] if dispatches else None))
        slots.append(slot)
    return data, slots


def graft_director(data, director_body):
    """Graft the save-sequence DIRECTOR (the donor field's entry-0 tag-1, from
    :func:`eventscan.extract_savepoint_director`) into the fork's EMPTY entry-0 tag-1, so it puppeteers the
    carried save Moogle. The director references no entries -- it drives the Moogle through shared transient
    MAP vars only -- so it grafts VERBATIM (replace the empty system-loop body with it). The carried Moogle +
    carried cask + this director then reconstitute the source field's exact state machine over those shared
    vars: the Moogle lowers into the barrel, pops out on a cask push, and runs the save flourish. The fork's
    entry-0 tag-1 is empty in a blank field, so this is a clean swap (docs/SAVEPOINT.md)."""
    return edit.replace_function_body(data, 0, 1, bytes(director_body))
