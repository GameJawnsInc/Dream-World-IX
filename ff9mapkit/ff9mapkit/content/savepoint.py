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

**The ACT (2026-07-18).** The moogle's save choreography is now synthesized too -- see the ACT section
below. The 4-agent census (all 65 ``Menu(4,0)`` field ids) proved the interact-time act is ONE invariant
template across all 57 moogle instances: hop clip 6503 -> the book (model 133) + feather (model 134)
props appear -> the moogle's book-open 4645 -> ``Menu(4,0)`` -> props hide -> hop 6503 back. All real
variance lives in the pre-interaction REVEAL (tag 1: barrel-pop x6, flying x1, bespoke x2), never in the
act. The one thing still verbatim-carry-only is those bespoke reveals (``import <field> --save-moogle``).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

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


# --- the other real menu rows (Tent / Mogshop / Switch party members) --------------------------------
TENT_ITEM = 253               # the Tent item id (donor: RemoveItem(253, 1))
PARTY_SLOTS = 8               # SetHP/SetMP are called per party slot 0..7
DEFAULT_TENT_ROW = "Tent"
DEFAULT_SHOP_ROW = "Mogshop"
DEFAULT_PARTY_ROW = "Switch party members"
DEFAULT_TENT_PROMPT = "Rest inside a tent, kupo?"
DEFAULT_TENT_YES, DEFAULT_TENT_NO = "Rest", "Don't rest"
DEFAULT_NO_TENT = "You don't have any tents, kupo!"
# Party(min_party_size, locked_mask): arg1 = the minimum party size, arg2 = a BITMASK of character
# slots the player may not remove (EventEngine.DoEventCode PARTYMENU, 0xB2). The donor save moogle
# calls Party(4, 1) -- a full party of four with slot 0 locked.
#
# ⚠ THE MIN-SIZE SOFTLOCK (in-game 2026-07-18, playtest report). `PartySettingUI.FF9Party_Check` is the
# ONLY exit from the party screen -- `OnKeyCancel` runs it and, when it fails, just buzzes (SFX 102) and
# stays. It reads `charCnt >= info.party_ct && healthyCnt != 0`, where charCnt counts the OCCUPIED party
# slots. So a literal `Party(4, ...)` with fewer than four characters available is UNESCAPABLE. Stock
# never hits it (the row only appears on late-game moogles with a full roster) -- and the engine itself
# clamps this exact value elsewhere: `UIKeyTrigger.cs:1002` does `party_ct = Math.Min(4, selectList.Count)`.
#
# So the kit's DEFAULT is now that clamp, computed at runtime: arg1 is an EXPRESSION counting the party
# (`getv1()` evaluates it, same as the proven `EnableDialogChoices(VAR|4, 0)` form). The count equals
# charCnt on entry, so the check passes immediately and can never lock; with a full party it is 4 --
# byte-for-byte stock behaviour. An explicit `party_min` still emits the literal, unchanged.
DEFAULT_PARTY_LOCKED = 1
DEFAULT_PARTY_MIN = 4         # the stock literal -- what `party_min` defaults to when set explicitly
PARTYCHK = 0x6B               # expression fn (op_binary 107 B_PARTYCHK): partychk(CharacterOldIndex)
                              # -> 1 when that character occupies a party slot (EventEngine.partychk
                              # walks party.member[0..3] -- the SAME array FF9Party_Check counts)
PARTY_CHAR_IDS = tuple(range(12))   # CharacterOldIndex 0..11 (content.party.CHAR_OLD_INDEX). A custom
                                    # 13th+ character is deliberately NOT counted: undercounting only
                                    # lowers the threshold (still >= charCnt-safe), overcounting would
                                    # re-create the softlock.


def _half_heal(fn_cur: int, fn_max: int, slot: int) -> bytes:
    """``CUR(slot) + (MAX(slot) + 1) / 2`` as an expression operand -- the donor's tent formula,
    token-for-token (field 300 @5029). A tent restores HALF of maximum, rounded up; ``SetHP``/``SetMP``
    clamp at the maximum, so a nearly-full character simply tops out."""
    c = bytes([_region.T_CONST]) + int(slot).to_bytes(2, "little")
    return (c + bytes([fn_cur]) + c + bytes([fn_max])
            + bytes([_region.T_CONST]) + (1).to_bytes(2, "little") + bytes([_region.T_PLUS])
            + bytes([_region.T_CONST]) + (2).to_bytes(2, "little") + bytes([_region.T_DIV])
            + bytes([_region.T_PLUS, _region.T_END]))


def tent_rest_body() -> bytes:
    """The tent's effect: per party slot 0..7, **if the member is not KO'd**, restore half of maximum
    HP and MP, then consume one Tent.

    Byte-shaped on field 300 @5016-5608. The per-slot guard is the load-bearing part: ``if (CURHP(slot)
    != 0)`` -- a tent must NOT revive a dead party member, and a slot the party doesn't hold reads 0 and
    is skipped by the same test. ``RemoveItem`` runs once, after the heals (the donor's order), so a
    build that somehow reached here without a tent still cannot go negative -- the caller gates on
    :func:`has_tent_cond`."""
    out = b""
    for k in range(PARTY_SLOTS):
        alive = (bytes([_region.EXPR_OP]) + bytes([_region.T_CONST]) + k.to_bytes(2, "little")
                 + bytes([_region.T_CURHP, _region.T_CONST]) + (0).to_bytes(2, "little")
                 + bytes([_region.T_NE, _region.T_END]))
        heal = (opcodes.encode(0xF1, k, _half_heal(_region.T_CURHP, _region.T_MAXHP, k), arg_flags=0b10)
                + opcodes.encode(0xF2, k, _half_heal(_region.T_CURMP, _region.T_MAXMP, k), arg_flags=0b10))
        out += _region.if_block(alive, heal)
    # ⚠ THE REST PRESENTATION IS NOT OPTIONAL. The heals above are byte-identical to the donor's, but a
    # tent that silently edits HP reads in-game as "it took my tent and did nothing" -- which is exactly
    # what the first shipped version did (playtest, 2026-07-19). The donor wraps the heals in a
    # fade-to-WHITE rest bracket (field 300 @4925-5608) and that bracket IS the feedback:
    #   sfx 1363 ; CalculateScreenPosition(player) ; FadeFilter(6,24, 255,255,255)   -- out to white
    #   Wait(16) ; sfx 1230 (the rest chime) ; Wait(8) ; HideAllObjects
    #   <the heals>
    #   CalculateScreenPosition(player) ; FadeFilter(7,16, 0,0,0) ; Wait(20)          -- back in
    #   RemoveItem(Tent)                                                              -- AFTER the fade
    # The donor passes the fade intensity through a Map scratch holding 255; we pass the literal, the
    # same simplification content.mognet.letter_display already makes for the letter bracket.
    return (act_sfx(TENT_SFX_REST)
            + opcodes.encode(0xA9, PLAYER_UID)                       # CalculateScreenPosition(player)
            + opcodes.encode(0xEC, 6, 24, 255, 255, 255, 255)        # fade OUT to white
            + opcodes.wait(16)
            + act_sfx(TENT_SFX_SLEEP)
            + opcodes.wait(8)
            + opcodes.encode(0xD5)                                   # HideAllObjects (field 300 @5010)
            + out
            + opcodes.encode(0xA9, PLAYER_UID)
            + opcodes.encode(0xEC, 7, 16, 255, 0, 0, 0)              # fade back IN
            + opcodes.wait(20)
            + opcodes.remove_item(TENT_ITEM, 1))


def has_tent_cond() -> bytes:
    """``if (GetItemCount(Tent) > 0)`` -- gates the tent row's offer (the donor shows a "no tents"
    line instead; see :func:`tent_dispatch`)."""
    return (bytes([_region.EXPR_OP, _region.T_CONST]) + TENT_ITEM.to_bytes(2, "little")
            + bytes([_region.T_ITEMCOUNT, _region.T_CONST]) + (0).to_bytes(2, "little")
            + bytes([_region.T_NE, _region.T_END]))


def tent_dispatch(prompt_txid: int, none_txid: int, *, window: int = CHOICE_WINDOW,
                  flags: int = CHOICE_FLAGS) -> bytes:
    """The whole Tent row: no tents -> the "you don't have any" line; otherwise the confirm (its text
    carries the live ``(Tent(s) Remaining=[NUMB=7])`` count -- the caller loads text var 7 first), and
    row 0 rests. Declining is a bodiless row."""
    rest = (opcodes.window_sync(window, flags, prompt_txid)
            + _choice.switch_on_choice([tent_rest_body(), b""]))
    # the donor loads the remaining-tent count into text var 7 for the prompt (field 300 @4853)
    count = opcodes.encode(0x66, 7, bytes([_region.T_CONST]) + TENT_ITEM.to_bytes(2, "little")
                           + bytes([_region.T_ITEMCOUNT, _region.T_END]), arg_flags=0b10)
    return _region.if_else(has_tent_cond(), count + rest,
                           opcodes.window_sync(1, 128, none_txid))


def shop_dispatch(shop_id: int) -> bytes:
    """The Mogshop row: ``Menu(2, <shopId>)`` bracketed by the donor's brief waits (field 300 @10631).
    The inventory itself is an ordinary ``[[shop]]`` -- this row just opens it."""
    return (opcodes.wait(3) + opcodes.menu(2, int(shop_id)) + opcodes.wait(3))


def current_party_size_expr() -> bytes:
    """A bare RPN blob evaluating to the number of characters CURRENTLY in the party::

        partychk(0) + partychk(1) + ... + partychk(11)

    ``B_PARTYCHK`` reads ``party.member[0..3]``, the very array ``FF9Party_Check`` counts, so this
    equals that check's ``charCnt`` on entry -- see the softlock note above."""
    out = b""
    for k, cid in enumerate(PARTY_CHAR_IDS):
        out += bytes([_region.T_CONST]) + int(cid).to_bytes(2, "little") + bytes([PARTYCHK])
        if k:
            out += bytes([_region.T_PLUS])
    return out + bytes([_region.T_END])


def party_dispatch(*, min_size: int | None = None, locked: int = DEFAULT_PARTY_LOCKED) -> bytes:
    """The Switch-party-members row: ``Party(min, locked)`` then ``UpdatePartyUID()`` -- the donor's
    pair (field 300 @10675). ``locked`` is a bitmask of character slots the player may not remove.

    ``min_size=None`` (the default) emits the SOFTLOCK-SAFE runtime clamp -- arg1 as
    :func:`current_party_size_expr` -- so the screen is always escapable and behaves exactly like the
    donor's literal 4 once the party is full. An explicit ``min_size`` emits that literal verbatim
    (the author owns the consequence; see the note above ``DEFAULT_PARTY_LOCKED``)."""
    call = (opcodes.encode(0xB2, current_party_size_expr(), int(locked), arg_flags=0b01)
            if min_size is None else opcodes.encode(0xB2, int(min_size), int(locked)))
    return call + opcodes.encode(0xE9)


# --- THE MOOGLE'S ACT (the save choreography) --------------------------------------------------------
# Byte-decoded from field 300 (Ice Cavern/Entrance) entry 3 tag 3 and census-confirmed invariant across
# ALL 57 moogle save instances (2026-07-18, instruction-aligned scan of every field): once -- and only
# once -- the player answers YES to the save confirm, the moogle
#
#   SetTurnSpeed(32); EnableHeadFocus(0)
#   RunAnimation(6503)  "SAVE_JUMP" + sfx 1362 ; Wait(24) ; landing sfx 2631
#   [optional 15-frame hand-lerp to a landing spot -- the donor's MoveInstantXZY-per-frame walk substitute]
#   RunScriptAsync(4, 250, <pose>)      -- the player turns to watch (a grafted player tag)
#   SetPathing(1); Wait(1); EnableShadow; WaitAnimation ; TurnTowardObject(250, 32); WaitTurn
#   WindowAsync(1, 128, <line>)         -- the moogle's save line, non-blocking
#   Wait(12) ; sfx 1362                 -- the pre-open accent beat (field 300 @4559-4572; also in 810)
#   RunScriptAsync(4, <book>, 37) ; RunScriptAsync(4, <feather>, 37)   -- the props snap to it + open
#   RunAnimation(4645) "SAVE_OPEN" ; Wait(68)
#   GLOB(184)=1 ; Wait(3) ; Menu(4,0) ; Wait(3) ; GLOB(184)=0          -- save_act(), unchanged
#   RunScriptAsync(4, <book>, 38) ; RunScriptAsync(4, <feather>, 38)   -- instant hide
#   RunAnimation(6503) + sfx 1362 ; Wait(24) ; landing sfx 682 (the return thud DIFFERS by direction)
#   [optional lerp back] ; MAP.Bit[322]=1 ; RunScriptAsync(4, 250, <release>)
#   SetPathing(1); Wait(1); EnableShadow; WaitAnimation; EnableHeadFocus(3)
#   TurnTowardObject(250, 32); WaitTurn ; while (MAP.Bit[322]) Wait(1)  -- join the async release
#
# Declining at EITHER window skips the whole act (the donor jumps straight back to the row menu -- none
# of the choreography fires), and the script never branches on Menu(4,0)'s own in-menu cancel: once the
# scripted Yes lands, the physical act always completes. Both facts are donor law, reproduced here.
#
# Clip law (census): hop = 6503 ANH_NPC_F0_MOG_SAVE_JUMP and open = 4645 ANH_NPC_F0_MOG_SAVE_OPEN on
# BOTH moogle models (220 F0 / 129 F1 -- clips bind by name family, so F0 clips are legal on either);
# the book prop is model 133 GEO_ACC_F0_MGR in 57/57 fields (clip 4641), the feather 134 GEO_ACC_F0_MGP
# in 55/57 (clip 4652 -- NOT 4651; verified byte-for-byte in fields 300 AND 810). SFX ids are universal.
ACT_HOP_CLIP = 6503          # ANH_NPC_F0_MOG_SAVE_JUMP -- both directions
ACT_OPEN_CLIP = 4645         # ANH_NPC_F0_MOG_SAVE_OPEN -- the moogle's own book-open gesture
ACT_BOOK_MODEL = "GEO_ACC_F0_MGR"     # 133 -- the save book (57/57 census)
ACT_FEATHER_MODEL = "GEO_ACC_F0_MGP"  # 134 -- the feather/quill (55/57; 679 = the rare F1 variant)
ACT_BOOK_POSE = 1872         # the props' rest poses (prop_archetypes save_book / feather)
ACT_FEATHER_POSE = 1874
ACT_PROP_ANIMSET = 93        # SetModel(133, 93) / SetModel(134, 93) -- the donor's accessory animset
                             # (133/134 are off the NPC_PARAMS catalog, so it must be passed explicitly)
ACT_BOOK_OPEN_CLIP = 4641    # ANH_ACC_F0_MGR_SAVE_OPEN -- the book's own open clip
ACT_FEATHER_OPEN_CLIP = 4652  # ANH_ACC_F0_MGP_SAVE_OPEN -- 4652, not the animdb-adjacent 4651
ACT_APPEAR_TAG = 37          # the prop appear/hide tags -- donor field 300's numbers (fresh props here,
ACT_HIDE_TAG = 38            #   so any free tags work; matching the donor keeps disasm side-by-sides easy)
ACT_REQ_LEVEL = 4            # every donor RunScriptAsync in the act uses level 4 (both census fields)
ACT_TURN_SPEED = 32          # SetTurnSpeed / TurnTowardObject speed in the act
ACT_PLAYER_TURN_SPEED = 16   # the player pose funcs' TurnTowardObject speed (donor tags 32/33/34)
ACT_HOP_AIR_WAIT = 24        # frames between the hop clip start and the landing thud
ACT_PROP_WAIT = 12           # the props' post-RunAnimation settle before they show
ACT_OPEN_WAIT = 68           # after RunAnimation(4645), before the save latch -- calibrated to the clip
ACT_LERP_STEPS = 14          # the donor lerp divisor; the loop writes frames 0..14 inclusive (15 writes)
ACT_HANDSHAKE_BIT = 322      # MAP.Bit[322] -- the donor's own async-release rendezvous bit, verbatim
                             # (transient MAP scope; clear of the kit's cutscene 80+ / init 144-159 bands)
SFX_BANK = 53248             # RunSoundCode3 bank -- every act sfx uses it
SFX_HOP = 1362               # the act's accent chime: x3 in the act itself (hop out / pre-open / hop
                             # back); the donor's 4th instance accompanies its menu redisplay, not the act
SFX_LAND_OUT = 2631          # landing thud, hop OUT
SFX_LAND_BACK = 682          # landing thud, hop BACK (deliberately different)
SFX_POOF = 2979              # the book's appear "poof" (book only, not the feather)
PLAYER_UID = 250             # GetObjUID(250) = the control character (engine convention)
DEFAULT_ACT_LINE = "Here we go, kupo!"   # the WindowAsync(1,128,·) line during the act -- kit-authored
                                          # in FF9 style, never a Square-Enix quote (docs/PROVENANCE.md)


def act_sfx(sound_id: int, *, vol: int = 125) -> bytes:
    """One act sound: ``RunSoundCode3(53248, id, 0, 128, vol)`` (opcode 0xC8, widths [2,2,3,1,1]).
    Ground truth: ``c8 00 00 d0 52 05 00 00 00 80 7d`` = (53248, 1362, 0, 128, 125), field 300 @4412."""
    return opcodes.encode(0xC8, SFX_BANK, int(sound_id), 0, 128, int(vol))


def _obj_field(uid: int, field: int) -> bytes:
    """An expression operand reading another object's live var: ``78 <uid> <field> 7F`` (T_OBJVAR;
    fields 0/1/2 = position, 3 = facing). The donor's book snaps to the moogle with exactly this."""
    return bytes([_region.T_OBJVAR, uid & 0xFF, field & 0xFF, _region.T_END])


def _self_angle_flip() -> bytes:
    """``self.angle + 128`` -- the donor's landing 180° spin (uid 255 = self, field 3 = facing)."""
    return (bytes([_region.T_OBJVAR, 0xFF, 3, _region.T_CONST]) + (128).to_bytes(2, "little")
            + bytes([_region.T_PLUS, _region.T_END]))


def _trunc_div(a: int, b: int) -> int:
    """C-style division (truncate toward zero) -- the engine's expression `/` on the lerp deltas."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _lerp_frames(start, end) -> bytes:
    """The donor's 14-frame hand-lerp, UNROLLED: 15 ``MoveInstantXZY`` writes (k = 0..14) with a
    ``Wait(1)`` each, positions ``start + trunc(k*delta/14)`` -- frame-identical to the donor's
    ``Instance.Byte[8]`` counter loop (field 300 @4453-4525), without its instance-var scratch.
    ``start``/``end`` are ``(x, z, y)`` world coords."""
    (x0, z0, y0), (x1, z1, y1) = start, end
    out = b""
    for k in range(ACT_LERP_STEPS + 1):
        out += opcodes.move_instant_xzy(x0 + _trunc_div(k * (x1 - x0), ACT_LERP_STEPS),
                                        z0 + _trunc_div(k * (z1 - z0), ACT_LERP_STEPS),
                                        y0 + _trunc_div(k * (y1 - y0), ACT_LERP_STEPS))
        out += opcodes.wait(1)
    return out


def _while_truthy(var_class, idx: int, body: bytes) -> bytes:
    """``while (VAR) { body }`` -- check-first: cond, JMP_IFNOT past, body, JMP back. The act's
    handshake poll (``while (MAP.Bit[322]) Wait(1)``, field 300 @4756) is the only loop in the act."""
    cond = _region.cond_truthy(var_class, idx)
    block = cond + bytes([_region.JMP_FALSE]) + struct.pack("<H", len(body) + 3) + bytes(body)
    return block + bytes([0x01]) + struct.pack("<h", -(len(block) + 3))


def act_prop_appear_body(moogle_uid: int, open_clip: int, *, poof: bool = False) -> bytes:
    """The book/feather APPEAR function (the donor's tag 37, field 300 @10864): snap to the moogle's
    LIVE position + facing (expression args -- the moogle may have hopped), play the prop's own open
    clip, then show (flags 7 = visible + walk-through) with the 4-step ``SetObjectSize`` grow-in.
    ``poof`` adds the book's appear sfx (the donor gives it to the book only)."""
    out = act_sfx(SFX_POOF) if poof else b""
    out += opcodes.encode(0xA1, _obj_field(moogle_uid, 0), _obj_field(moogle_uid, 1),
                          _obj_field(moogle_uid, 2), arg_flags=0b111)      # MoveInstantXZY -> the moogle
    out += opcodes.encode(0x36, _obj_field(moogle_uid, 3), arg_flags=1)    # TurnInstant -> match facing
    out += opcodes.run_animation(int(open_clip))
    out += opcodes.wait(ACT_PROP_WAIT)
    out += opcodes.encode(0x93, 7)                                          # show + both collision exemptions
    for k, s in enumerate((16, 32, 48, 64)):
        if k:
            out += opcodes.wait(1)
        out += opcodes.encode(0x9F, 255, s, s, s)                           # SetObjectSize grow-in
    return out + opcodes.RETURN


def act_prop_hide_body() -> bytes:
    """The prop HIDE function (donor tag 38): an instant vanish -- ``SetObjectFlags(14)`` and out."""
    return opcodes.encode(0x93, 14) + opcodes.RETURN


def player_pose_body(moogle_uid: int) -> bytes:
    """The player's watch pose (donor obj-250 tag 33, byte-complete): turn toward the moogle, wait."""
    return (opcodes.turn_toward_object(int(moogle_uid), ACT_PLAYER_TURN_SPEED)
            + opcodes.wait_turn() + opcodes.RETURN)


def player_release_body(moogle_uid: int) -> bytes:
    """The player's release (donor tag 34): the same turn, then CLEAR the handshake bit -- the join the
    moogle's close-out polls on (RunScriptAsync doesn't block; the shared MAP bit is the rendezvous)."""
    return (opcodes.turn_toward_object(int(moogle_uid), ACT_PLAYER_TURN_SPEED) + opcodes.wait_turn()
            + _region.set_var(_region.MAP_BOOL, ACT_HANDSHAKE_BIT, 0) + opcodes.RETURN)


def moogle_act_init_tail() -> bytes:
    """``SetJumpAnimation(6503, 26, 30)`` for the moogle's Init -- the LOAD-BEARING preload. Present
    byte-identically in every donor moogle's Init, always paired with the later ``RunAnimation(6503)``
    calls; a moogle that skips it risks the hop clip not blending. Treat the triple as atomic."""
    return opcodes.set_jump_animation(ACT_HOP_CLIP, 26, 30)


def act_save_body(*, book_uid: int, feather_uid: int, pose_tag: int, release_tag: int,
                  act_txid: int | None = None, rest=None, hop_to=None, latch: bool = True) -> bytes:
    """The FULL act around the save -- the donor's confirmed-Yes choreography (see the section comment
    for the sequence), with :func:`save_act` embedded where the donor's ``Menu(4,0)`` sits.

    ``rest`` is the moogle's authored (x, z[, y]) spot; ``hop_to`` an optional landing spot -- given,
    the moogle traverses there and back with the donor's 15-frame lerp (both ends compile-time literals,
    exactly the donor's own CLOSE-OUT shape -- its intro's runtime self-read start exists only because a
    director may have moved it; ours never moves). Without ``hop_to`` the moogle hops in place: the same
    clip/sfx/wait skeleton, no traversal frames, and no landing 180° spin (that flourish corrects the
    donor's fly-away facing; in place it would just pirouette)."""
    rest3 = None if rest is None else (tuple(int(v) for v in rest) + (0,))[:3]
    hop3 = None if hop_to is None else (tuple(int(v) for v in hop_to) + (0,))[:3]
    traverse = hop3 is not None and rest3 is not None
    # ⚠ PATHING IS PER-SPOT: attach (1) on the floor, DETACH (0) off it. The donor act calls
    # SetPathing(1) at BOTH lerp ends (field 407 tag 3 @538 ground, @761 the cask-top perch) and gets
    # away with the perch call only by GEOMETRY: its cask spot (-250,-571) has NO walkmesh triangle
    # under it (verified against 407's .bgi -- the whole cask corner is off-mesh), so the attach has
    # nothing to snap to. A kit field's cask usually sits ON walkable ground, and re-attaching there
    # snapped the perched moogle down INTO the barrel (the 2026-07-19 live bug, two failed fixes that
    # synthesized around the donor instead of decoding it). The kit states the donor's INTENT
    # explicitly: an off-floor spot (y != 0) detaches; a floor spot attaches. Ground savepoints
    # (y == 0 everywhere) emit byte-identical SetPathing(1) as before.
    _out_spot_y = (hop3 if traverse else rest3 or (0, 0, 0))[2]      # where the OUT hop lands
    _rest_spot_y = (rest3 or (0, 0, 0))[2]                            # where the RETURN hop lands
    out = opcodes.encode(0x99, ACT_TURN_SPEED)                       # SetTurnSpeed(32)
    out += opcodes.encode(0x47, 0)                                    # EnableHeadFocus(0)
    out += opcodes.run_animation(ACT_HOP_CLIP)
    out += act_sfx(SFX_HOP) + opcodes.wait(ACT_HOP_AIR_WAIT) + act_sfx(SFX_LAND_OUT)
    out += opcodes.encode(0x80)                                       # DisableShadow (airborne)
    if traverse:
        out += _lerp_frames(rest3, hop3)
    out += opcodes.run_script_async(ACT_REQ_LEVEL, PLAYER_UID, int(pose_tag))
    out += (opcodes.set_pathing(0 if _out_spot_y else 1)
            + opcodes.wait(1) + opcodes.encode(0x7F) + opcodes.wait_animation())
    if traverse:
        out += opcodes.encode(0x36, _self_angle_flip(), arg_flags=1)  # the landing 180° spin
    out += opcodes.turn_toward_object(PLAYER_UID, ACT_TURN_SPEED) + opcodes.wait_turn()
    if act_txid is not None:
        out += opcodes.window_async(1, 128, int(act_txid))            # the save line, non-blocking
    # the pre-open accent beat -- Wait(12) + the chime, byte-present in every donor between the save
    # line and the prop dispatch (field 300 @4559-4572, field 810 @561-575); the adversarial review
    # caught it dropped. Unconditional: the beat belongs to the props' entrance, not the window.
    out += opcodes.wait(ACT_PROP_WAIT) + act_sfx(SFX_HOP)
    out += opcodes.run_script_async(ACT_REQ_LEVEL, int(book_uid), ACT_APPEAR_TAG)
    out += opcodes.run_script_async(ACT_REQ_LEVEL, int(feather_uid), ACT_APPEAR_TAG)
    out += opcodes.run_animation(ACT_OPEN_CLIP)
    out += opcodes.wait(ACT_OPEN_WAIT)
    out += save_act(latch=latch)                                      # the unchanged functional core
    out += opcodes.run_script_async(ACT_REQ_LEVEL, int(book_uid), ACT_HIDE_TAG)
    out += opcodes.run_script_async(ACT_REQ_LEVEL, int(feather_uid), ACT_HIDE_TAG)
    out += opcodes.run_animation(ACT_HOP_CLIP)
    out += act_sfx(SFX_HOP) + opcodes.wait(ACT_HOP_AIR_WAIT) + act_sfx(SFX_LAND_BACK)
    out += opcodes.encode(0x80)
    if traverse:
        out += _lerp_frames(hop3, rest3)
    out += _region.set_var(_region.MAP_BOOL, ACT_HANDSHAKE_BIT, 1)
    out += opcodes.run_script_async(ACT_REQ_LEVEL, PLAYER_UID, int(release_tag))
    out += (opcodes.set_pathing(0 if _rest_spot_y else 1)
            + opcodes.wait(1) + opcodes.encode(0x7F) + opcodes.wait_animation())
    out += opcodes.encode(0x47, 3)                                    # EnableHeadFocus(3) -- donor close
    if traverse:
        out += opcodes.encode(0x36, _self_angle_flip(), arg_flags=1)
    out += opcodes.turn_toward_object(PLAYER_UID, ACT_TURN_SPEED) + opcodes.wait_turn()
    out += _while_truthy(_region.MAP_BOOL, ACT_HANDSHAKE_BIT, opcodes.wait(1))
    return out


@dataclass
class ActCluster:
    """The act's supporting cast, injected by :func:`inject_act_cluster`. ``moogle_slot`` is the entry
    slot the moogle MUST then be injected at (the cluster's grafts reference it by uid) -- the build
    passes it as ``inject_npc(slot=...)``, which forces the seat (no prediction drift possible)."""
    book: int
    feather: int
    moogle_slot: int
    pose_tag: int
    release_tag: int


def inject_act_cluster(data, x: int, z: int):
    """Inject the act's supporting objects for one save moogle, BEFORE the moogle itself:

    * the book + feather as bare hidden props at the moogle's spot (donor rest state: head-focus off,
      ``SetObjectFlags(14)``, no shadow, logical size (1,1,1)), each grafted the appear (37) / hide (38)
      functions the act dispatches;
    * two fresh player functions (via :class:`content.player.PlayerTagAllocator`, the object band) --
      the watch pose and the handshake release.

    Returns ``(new_bytes, ActCluster)``. The moogle's slot is resolved here (the next free after both
    props; ``add_function`` grows no entries, so it holds) because the grafts hard-code its uid."""
    from .. import catalog as _catalog
    from . import npc as _npc
    from .ladder import find_player_entry
    from .player import PlayerTagAllocator
    prop_tail = (opcodes.encode(0x47, 0)          # EnableHeadFocus(0) -- the prop recipe
                 + opcodes.encode(0x93, 14)       # spawn HIDDEN (bits 2+4+8, show clear -- donor rest)
                 + opcodes.encode(0x80))          # DisableShadow
    book_slot = EbScript.from_bytes(data).first_free_slot()
    data = _npc.inject_npc(data, x, z, model=_catalog.resolve_model(ACT_BOOK_MODEL),
                           animset=ACT_PROP_ANIMSET, anims={k: ACT_BOOK_POSE for k in _npc.ANIM_ORDER},
                           bare=True, init_tail=prop_tail, slot=book_slot, logical_size=(1, 1, 1))
    feather_slot = EbScript.from_bytes(data).first_free_slot()
    data = _npc.inject_npc(data, x, z, model=_catalog.resolve_model(ACT_FEATHER_MODEL),
                           animset=ACT_PROP_ANIMSET, anims={k: ACT_FEATHER_POSE for k in _npc.ANIM_ORDER},
                           bare=True, init_tail=prop_tail, slot=feather_slot, logical_size=(1, 1, 1))
    moogle_slot = EbScript.from_bytes(data).first_free_slot()
    data = edit.add_function(data, book_slot, ACT_APPEAR_TAG,
                             act_prop_appear_body(moogle_slot, ACT_BOOK_OPEN_CLIP, poof=True))
    data = edit.add_function(data, book_slot, ACT_HIDE_TAG, act_prop_hide_body())
    data = edit.add_function(data, feather_slot, ACT_APPEAR_TAG,
                             act_prop_appear_body(moogle_slot, ACT_FEATHER_OPEN_CLIP))
    data = edit.add_function(data, feather_slot, ACT_HIDE_TAG, act_prop_hide_body())
    eb = EbScript.from_bytes(data)
    pe = find_player_entry(eb)
    pose_tag, release_tag = PlayerTagAllocator(eb).take("object", 2)
    data = edit.add_function(data, pe, pose_tag, player_pose_body(moogle_slot))
    data = edit.add_function(data, pe, release_tag, player_release_body(moogle_slot))
    return data, ActCluster(book_slot, feather_slot, moogle_slot, pose_tag, release_tag)


# The real save moogle's row ORDER (text entry 3 of a moogle field): Save / Tent / Mognet / Mogshop /
# Switch party members / Debug / Cancel. A field shows a SUBSET -- stock does it with a runtime
# availability mask over all seven rows; we emit only the configured rows, which is equivalent for a
# static configuration and keeps the [CHOO] list and the dispatch trivially in step. `Debug` is stock's
# own dev row and is never emitted. Cancel is always last.
MENU_ROW_ORDER = ("save", "tent", "mognet", "shop", "party")


def menu_rows(cfg) -> list:
    """The row KEYS this save point shows, in the donor's order, always ending in ``"cancel"``.
    ``cfg`` is the ``[[savepoint]]`` table; a row appears when its feature is configured."""
    on = {"save": True,
          "tent": bool(cfg.get("tent")),
          "mognet": bool(cfg.get("mognet") and str(cfg.get("mognet", {}).get("name", ""))),
          "shop": cfg.get("shop") is not None,
          "party": bool(cfg.get("party"))}
    return [k for k in MENU_ROW_ORDER if on[k]] + ["cancel"]


def save_dispatch_menu(prompt_txid: int, rows, bodies, *, prologue: bytes = b"") -> bytes:
    """The moogle's talk body for ANY configured row set: lock control, open the prompt, dispatch with
    :func:`choice.switch_on_choice` (op_0B -- one sysvar-9 read, so nested confirms are safe), restore.

    ``rows`` are the keys from :func:`menu_rows`; ``bodies`` maps each key to its body (``cancel`` and
    any missing key emit nothing). The row ORDER here must match the ``[CHOO]`` list the build writes --
    both derive from :func:`menu_rows`, so they cannot drift. ``prologue`` runs after the control lock
    and before the first window -- the build passes ``SetTextVariable(0, <moogle id>)`` there so a
    network moogle's windows can speak as their roster identity (``mognet.VAR_SPEAKER``)."""
    return (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU + bytes(prologue)
            + opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, prompt_txid)
            + _choice.switch_on_choice([bytes(bodies.get(r, b"") or b"") for r in rows])
            + opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN)


def save_confirm_body(confirm_txid: int, *, latch: bool = True, save_body: bytes | None = None) -> bytes:
    """The Save row's body: the Yes/No confirm, then the latched save. Row 1 (No) is bodiless.

    ``save_body`` replaces the bare :func:`save_act` -- the build passes :func:`act_save_body` for the
    moogle's TALK dispatch (the choreographed save), and nothing for the region's press dispatch (a
    region entry has no model; the donor's moogle-less family saves with zero clips, and so does ours).
    Either way the body runs only on the confirmed Yes -- exactly the donor's decline law."""
    return (opcodes.window_sync(CHOICE_WINDOW, CHOICE_FLAGS, confirm_txid)
            + _choice.switch_on_choice([save_body if save_body is not None else save_act(latch=latch),
                                        b""]))


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


def save_dispatch_prompted(prompt_txid: int, confirm_txid: int, *, latch: bool = True,
                           save_body: bytes | None = None, prologue: bytes = b"") -> bytes:
    """The FAITHFUL save interaction, rebuilt from the real script::

        DisableMove ; DisableMenu
        Window(2, 8, prompt)   -> row 0 "Save" ...
          Window(2, 8, confirm) -> row 0 "Yes" ...
            GLOB(184)=1 ; Wait(3) ; Menu(4,0) ; Wait(3) ; GLOB(184)=0
        EnableMenu ; EnableMove ; RETURN

    Both real families run an option menu and then a Yes/No confirm before the save (field 300:
    ``WindowAsync(2,8,3)`` then ``WindowAsync(2,8,4)``; field 2919: txid 454 then 457). The shipped
    pre-rung-2 save point jumped straight to ``Menu(4,0)`` on touch, which no save point in the game does.

    ``save_body`` swaps the confirmed-Yes body (the act -- see :func:`save_confirm_body`); it carries no
    choice reads, so the :func:`_row0_only` nesting stays sound. Cancel (row 1) and No (row 1) are
    deliberately BODILESS -- see :func:`_row0_only` for why that is a correctness requirement, not a
    shortcut."""
    inner = save_body if save_body is not None else save_act(latch=latch)
    return (opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU + bytes(prologue)
            + _row0_only(prompt_txid, _row0_only(confirm_txid, inner))
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


# --- THE CASK REVEAL ("barrel_pop") -------------------------------------------------------------------
# The moogle does not have to be visible from Init. The real barrel-pop moogle (the canonical donor set:
# fields 253, 351, 407, 853 -- the only 4/58 whose SAVE_JUMP-family reveal uses the distinct AIRBORNE clip
# 2917, decoded end to end via field 407's cask) spends its Init hidden (``SetObjectFlags(14)``) inside a
# cask/barrel prop, and pops out the first time the player presses the cask. `reveal_style = "barrel_pop"`
# synthesizes that: a cask prop (model 241 `GEO_ACC_F0_CSK`, the kit's own "cask"/"barrel"/"crate" prop
# archetype) whose press handler and the moogle's own tag-1 loop rendezvous over TWO shared transient MAP
# vars -- the same shared-var choreography the ACT above uses for its own release handshake, just a
# fresh pair (adjacent to it, not reused):
#
#   MAP.Byte[32]  (GLOB_UINT8 0xD5, Map+Byte -- the donor's OWN reveal-state slot, reused verbatim here)
#       0 = idle (never explicitly written; the engine zeroes MAP on every field load)
#       1 = POP requested (the cask just pressed)
#       2 = DONE (the moogle has already popped -- the cask's own one-shot guard)
#   MAP.Bit[323]  (MAP_BOOL 0xC5, Map+Bit -- adjacent to :data:`ACT_HANDSHAKE_BIT` 322, clear of every
#       other reserved band in this module) -- the cask-holds/moogle-releases rendezvous bit, the exact
#       shape :func:`_while_truthy` already implements for the ACT's own release.
#
# Protocol (cask press -> reveal, mirroring field 407's real one): the cask's press handler is a ONE-SHOT
# guard (state != idle -> return, so a second press after the pop is inert), then DisableMove, set the
# handshake bit + state=POP, and poll the SAME bit while it's held (so the player watches, the donor's own
# shape) before restoring control. The moogle's own tag-1 loop (spliced via ``inject_npc(intro=...)``,
# which the *loop-safe, never-RETURN* contract on that parameter matches exactly: this block runs ONCE,
# top to bottom, then falls through into the ordinary standby loop forever) waits for state==POP, shows
# itself (``SetObjectFlags(5)``), runs the invariant airborne spine, the post-land dressing, then marks
# DONE and clears the handshake -- unblocking the cask's poll.
#
# ⚠ TALKABILITY WHILE HIDDEN -- deliberately NOT re-gated. ``SetObjectFlags(14)`` (2 exempt-vs-player +
# 4 exempt-vs-NPC + 8 DISABLE-TALK) already carries the disable-talk bit (see ``content.prop``/
# ``content.chest``'s own decode of this bitfield, and the chest's own "OPEN = CLOSED + disable-talk(8):
# solid but NO '!' / inert once looted" precedent) -- so IsActuallyTalkable's per-frame poll is ALREADY
# suppressed the instant the moogle spawns hidden, with no extra gating needed. ``SetObjectFlags(5)`` (1
# show + 4 exempt-vs-NPC) on pop OMITS bit 8, so talk becomes live again the moment the moogle is shown.
# This is the shipping shape, not a kit invention: field 407's own case 2/1 pair (hide=14/show=5, verified
# against the case-switch @1770/1779) is exactly this -- and 5, not 7 (the SCENERY_FLAGS value used
# elsewhere for a walk-through prop), is the real moogle's own shown-state value.
#
# ⚠ THE SHOW-FOLD SIMPLIFICATION (documented, deliberate). Field 407's own case-101 pop arm does NOT set
# SetObjectFlags(5) itself -- a SEPARATE case-1 write does that, driven by whatever external director set
# MAP.Byte[32]=1 before =101. This kit has no such director for a synthesized field (no verbatim carry),
# so the reveal folds the show into the pop arm itself: SetObjectFlags(5) is the first thing the pop body
# does. Functionally identical for a fresh field (nothing else can observe the moogle between "cask
# pressed" and "moogle shown"); NOT a byte-for-byte replay of field 407's own two-state dance.
REVEAL_STYLES = ("instant", "barrel_pop")     # "instant" = today's behaviour (moogle visible from Init)
REVEAL_STATE_IDX = 32          # MAP.Byte[32] -- the donor's own reveal-state slot (GLOB_UINT8 = Map+Byte,
                               # transient per-field; reset to 0 on every load, so "idle" needs no write)
# THE CYCLE (field 407, decoded end to end -- the moogle is a PUPPET on two shared MAP vars; every
# writer raises MAP.Bit[327] + the state, and the moogle's own tag-1 loop consumes the state and clears
# BOTH each pass. ⚠ 2026-07-22 FULL-DIRECTOR DECODE (entry-0 tag-1, all 44 instrs): the DIRECTOR is a
# ONE-SHOT LOAD SEQUENCE, not a post-save actor -- it walks 1 (show) -> 4 (disarm, selfvar0=0) -> 102
# (stow: MoveInstantXZY into the cask + shrink) back-to-back at field load, then dies at its RETURN
# (tag-1 funcs run ONCE; the moogle's loop persists only via its own explicit back-jump). An earlier
# note put the 1->4->102 walk "after the save" -- wrong: post-save behavior is all in the ACT itself):
#   load          director stows the shown moogle INSIDE the cask (shown-but-concealed, size 8/8/1)
#   press cask    cask tag 30 locks control, writes state=101 -> the moogle's case 101 jumps STRAIGHT UP
#                 onto the cask + turns to the player (NO dialogue opens); then state=3 ARMS the act
#                 (selfvar0=1 -- the act's head gates on it) and the cask SHRINKS its own press zone
#                 (1,50,50) -> (14,14,22) so the moogle takes over as the interact target
#   press again   the moogle (on top) answers, opening its menu
#   Save          the act -- leap off (lerp to ground), book, save screen, lerp back up; the act's OWN
#                 menu loop redisplays (tag 3 @6590 jumps back to the menu) -- no director involved
#   Cancel        the act's CLOSE-OUT TAIL (tag 3 @6593): turn + an ANIMATED dive back INTO the cask
#                 (RunJumpAnimation + SetupJump to ground + land), size restored (14,14,22), then
#                 RunScriptSync(cask tag 29) = RE-ARM: the cask's press zone back to (1,50,50) + the
#                 Int16[43] "moogle is out" latch cleared -- the whole cycle is re-pressable
# ⚠ THE HOP IS VERTICAL. Field 407's cask sits at (-250, -2, -571) and case 101 jumps to
# (-250, -362, -571) -- the SAME x/z, only the height differs. So there is NO hand-placed landing
# coordinate here at all (an earlier pass wrongly made one REQUIRED): the landing is the container's own
# spot raised by the container's height. `reveal_height` (default 360 = the donor's own delta) is the
# only tunable, and it is a HEIGHT, not a perspective-tuned position.
REVEAL_STATE_IN = 0        # hidden inside the container (MAP wipes to 0 on load -- the natural start)
REVEAL_STATE_POP_REQ = 1   # the container was pressed: pop, please
REVEAL_STATE_OUT = 2       # standing on top of the container, talkable, menu live
REVEAL_STATE_HIDE_REQ = 3  # the menu was cancelled: go back in
REVEAL_CONTAINER_HEIGHT = 360   # field 407: cask y = -2, moogle-on-top y = -362 -> a 360-unit lift
REVEAL_IN_LOGICAL_SIZE = (8, 8, 1)     # case 102's own shrink -- no collision while stowed
REVEAL_OUT_LOGICAL_SIZE = (40, 40, 55)  # case 101's restore
REVEAL_HANDSHAKE_BIT = 323     # MAP.Bit[323] -- the reveal's own cask<->moogle rendezvous bit, ADJACENT to
                               # ACT_HANDSHAKE_BIT (322); transient MAP scope, clear of every other band
                               # this module/kit reserves (cutscene 80+, field-init 144-159, the ACT's 322)
# ⚠ THE RENDEZVOUS IS PER-SAVE-POINT, NOT PER-FIELD. Both vars above are the k=0 BASE of a small band:
# save point k uses MAP.Byte[32+k] and MAP.Bit[323+k]. A field may legitimately hold more than one
# barrel_pop save point, and a single shared pair made them CROSS-TALK -- pressing any one cask popped
# EVERY barrel_pop moogle on the field at once and left the other casks permanently inert (their one-shot
# guard reads the same byte). Caught by the adversarial review, reproduced end to end. The bands are sized
# by :data:`REVEAL_MAX_PER_FIELD` and range-checked at build time, so a field that outgrows them fails
# loudly instead of silently colliding with the next reserved var.
#   bytes 32..35 (Map+Byte)  -- clear of the camera's own Map byte 24
#   bits  323..326 (Map+Bit) -- all inside bit-byte 40, so they never overlap the state BYTES above
REVEAL_MAX_PER_FIELD = 4
REVEAL_HOP_CLIP = 2917         # the airborne "pop" clip -- present in all 4/4 census donors (253/351/407/853);
                               # distinct from the ACT's own hop clip 6503 (a different mechanic: a real
                               # Jump arc via SetupJump/Jump, not a RunAnimation + hand-lerp)
REVEAL_BLEND = (4, 16)         # SetJumpAnimation blend args -- shared by 3/4 donors (351/407/853); 253 uses
                               # (6, 23), documented per-scene variance, never defaulted to
REVEAL_STEPS_DEFAULT = 10      # SetupJump duration (frames) -- the MODAL donor value (407 AND 853 both use
                               # 10); 253 uses 15, 351 uses 6 -- per-scene tuning, not a universal law
REVEAL_TURN_SPEED = 48         # TurnTowardObject speed in the post-land dressing (407: TurnTowardObject(23,48))
# THE PER-DONOR VARIANCE TABLE. Everything below is per-scene, NOT law -- recorded so a future round can
# see what the census actually found rather than re-deriving it (and so the kit never quietly promotes one
# donor's flourish into a universal default, which an earlier synthesis pass did with all three rows).
#   field | sfx           | emerge gesture | SetupJump steps | SetJumpAnimation blend | post-land dressing
#   253   | 1363          | 2928           | 15              | (6, 23)                | no
#   351   | -- none --    | --             |  6              | (4, 16)                | no
#   407   | 1362 (vol 99) | --             | 10              | (4, 16)                | yes
#   853   | -- none --    | --             | 10              | (4, 16)                | yes
TENT_SFX_REST = 1363           # the tent's opening chime -- field 300 @4925
TENT_SFX_SLEEP = 1230          # the rest chime under the white fade -- field 300 @4988
REVEAL_SFX_VOL = 99            # the reveal chime's own volume -- field 407 @1830 (the ACT uses 125)
REVEAL_SFX_253 = 1363          # documented, never defaulted: HALF the donor set emits no reveal sfx at all
REVEAL_SFX_407 = 1362          # (the ACT's own SFX_HOP shares this id; the reveal is a separate mechanic)
REVEAL_EMERGE_CLIP_253 = 2928  # the pre-jump "shake" gesture -- ONE donor of four. No default, no TOML key.
REVEAL_HIDE_FLAGS = 14         # SetObjectFlags(14) -- hidden; see the module docstring's own census note
                               # ("spawned hidden (SetObjectFlags(14))", true of every real save moogle)
REVEAL_SHOW_FLAGS = 5          # SetObjectFlags(5) -- show(1) + exempt-vs-NPC(4); field407's case-1 shown
                               # state (@1779), NOT 7 (that's SCENERY_FLAGS, a walk-through PROP's value)

CASK_LOGICAL_SIZE = (1, 50, 50)   # the cask's collision box (task brief; unverified against field 407's
                                  # own bytes beyond the brief's citation -- treated as ground truth here)
CASK_FLAGS = 37                   # SetObjectFlags(37) = show(1) + exempt-vs-NPC(4) + dont-hide(32): the
                                  # cask collides with the PLAYER (bit 2 clear -- you can't walk through
                                  # it) but not other NPCs, and is never auto-hidden


def reveal_init_tail() -> bytes:
    """The moogle's OWN Init tail for ``reveal_style = "barrel_pop"``: ``SetObjectFlags(14)`` (hidden).
    The DEFAULT (``reveal_style = "instant"``, i.e. unset) adds no init_tail at all -- the moogle stays
    visible from spawn exactly as before ("the default must not change any existing build's bytes").
    Composes with the ACT's own :func:`moogle_act_init_tail` -- the donor evidence puts the flag write
    FIRST (field115 @3850/3856, field253 @4114/4120): ``reveal_init_tail() + moogle_act_init_tail()``,
    never the reverse."""
    return opcodes.encode(0x93, REVEAL_HIDE_FLAGS)


def reveal_vars(index: int = 0) -> tuple:
    """``(state_byte_idx, handshake_bit_idx)`` for save point ``index`` -- the per-save-point rendezvous
    pair (see the band note above :data:`REVEAL_MAX_PER_FIELD`). Raises past the reserved band rather than
    silently wrapping into whatever var sits beyond it."""
    k = int(index)
    if not 0 <= k < REVEAL_MAX_PER_FIELD:
        raise ValueError(
            f"barrel_pop save point index {k} is outside the reserved rendezvous band "
            f"(0..{REVEAL_MAX_PER_FIELD - 1}). Each barrel_pop save point needs its own transient MAP "
            f"state byte + handshake bit; the kit reserves {REVEAL_MAX_PER_FIELD} per field.")
    return REVEAL_STATE_IDX + k, REVEAL_HANDSHAKE_BIT + k


def _cond_neq(var_class, idx: int, value: int) -> bytes:
    """``if (VAR != value)`` condition expr -> ``05 <var> 7D <value:i16> 21 7F`` (T_NE 0x21) -- the one
    comparison :func:`content.region.cond_cmp` doesn't expose (its ``CMP_TOKENS`` has no ``'!='`` entry).
    Built inline against ``_region``'s own private encoders, the way ``content.mognet``/``content.party``/
    ``content.coop`` already do."""
    return (bytes([_region.EXPR_OP]) + _region._push_var(var_class, idx) + bytes([_region.T_CONST])
            + _region._const16(var_class, value) + bytes([_region.T_NE, _region.T_END]))


def _while_not_eq(var_class, idx: int, value: int, body: bytes) -> bytes:
    """``while (VAR != value) { body }`` -- check-first, mirroring :func:`_while_truthy`'s shape but on
    inequality: the reveal's own poll idiom ("wait while MAP.Byte[32] != POP", the donor's polling idiom)."""
    cond = _cond_neq(var_class, idx, value)
    block = cond + bytes([_region.JMP_FALSE]) + struct.pack("<H", len(body) + 3) + bytes(body)
    return block + bytes([0x01]) + struct.pack("<h", -(len(block) + 3))


def reveal_spine_body(*, jump_to, face_to=None, steps: int = REVEAL_STEPS_DEFAULT,
                      sfx: int | None = None, blend=REVEAL_BLEND) -> bytes:
    """The invariant airborne-pop spine, byte-shaped in the census's own execution order (4/4 donors):

        SetJumpAnimation(2917, blendA, blendB)
        [RunSoundCode3(...) -- only when ``sfx``; 2/4 donors (351, 853) emit none, so the default is None]
        TurnTowardPosition(face_x, face_z) ; WaitTurn()
        RunJumpAnimation() ; WaitAnimation()
        SetupJump(jx, jz, jy, steps) ; Jump()
        RunLandAnimation() ; WaitAnimation()

    ``jump_to`` = ``(x, z[, y])`` is a REQUIRED, hand-placed, perspective-tuned destination -- no formula
    derives it (the same law :mod:`content.jump` states for its own arcs). ``face_to`` defaults to
    ``jump_to`` (253/407/853 turn before jumping; 351 doesn't -- the kit always turns, since it always
    has a destination to turn toward; a bare hop-in-place with no turn isn't exposed as a TOML option).
    ``steps`` defaults to the donor MODAL value 10 (see :data:`REVEAL_STEPS_DEFAULT`)."""
    if jump_to is None:
        raise ValueError("reveal_spine_body: jump_to is required -- a perspective-tuned, hand-placed "
                         "destination (no formula derives it; the content.jump law, restated here)")
    jx, jz, jy = (tuple(int(v) for v in jump_to) + (0, 0))[:3]
    ft = tuple(int(v) for v in (face_to if face_to is not None else jump_to))
    fx, fz = (ft + (0,))[:2]
    out = opcodes.set_jump_animation(REVEAL_HOP_CLIP, int(blend[0]), int(blend[1]))
    if sfx:
        out += act_sfx(int(sfx), vol=REVEAL_SFX_VOL)     # 99, not the act's 125 -- field 407 @1830
    out += opcodes.turn_toward_position(fx, fz) + opcodes.wait_turn()
    out += opcodes.run_jump_animation() + opcodes.wait_animation()
    out += opcodes.setup_jump(jx, jz, jy, int(steps)) + opcodes.jump()
    out += opcodes.run_land_animation() + opcodes.wait_animation()
    return out


def reveal_landing_dressing(player_uid: int = PLAYER_UID) -> bytes:
    """The post-land dressing 2/4 donors (407, 853) run after the spine: turn to face the player (speed
    :data:`REVEAL_TURN_SPEED`, field407's own ``TurnTowardObject(23, 48)``), ``FollowFocus(1)``, and
    restore the moogle's normal collision box ``SetObjectLogicalSize(40, 40, 55)``. Emitted
    unconditionally here (253/351 omit it, but a fresh real Jump landing warrants correct camera-follow +
    collision regardless of which donor happens to skip it in situ).

    ⚠ The DOUBLE ``WaitTurn()`` is deliberate and load-bearing-by-default: BOTH donors that run this
    dressing emit it twice back to back (407 @1866/1867, 853 -- 2/2, verified by disassembly). An earlier
    pass collapsed it to one on the theory that it was a decode artifact; it is not -- it is in the bytes
    of every donor that has this block. This project's own law is that act/reveal timing is load-bearing,
    so the donor's repeat is reproduced rather than reasoned away."""
    return (opcodes.turn_toward_object(int(player_uid), REVEAL_TURN_SPEED)
            + opcodes.wait_turn() + opcodes.wait_turn()     # 2/2 donors: 407 @1866/1867, 853
            + opcodes.encode(0x91, 1)                       # FollowFocus(1)
            + opcodes.encode(0x4B, 40, 40, 55))              # SetObjectLogicalSize(40, 40, 55) -- restore


def _if_state(state_idx: int, value: int, body: bytes) -> bytes:
    """``if (state == value) { body }`` -- one arm of the state loop. Note ``if_block`` runs its body when
    the condition is TRUE, so this takes ``cond_cmp(..., "==")``; the one-shot guards elsewhere in this
    module use ``_cond_neq`` precisely because they want the inverse (guard-and-return)."""
    return _region.if_block(_region.cond_cmp(_region.GLOB_UINT8, state_idx, value, "=="), body)


def reveal_state_loop(*, container_pos, height: int = REVEAL_CONTAINER_HEIGHT,
                      steps: int = REVEAL_STEPS_DEFAULT, sfx=None, blend=REVEAL_BLEND,
                      player_uid: int = PLAYER_UID, index: int = 0) -> bytes:
    """The moogle's WHOLE tag-1: a permanent state loop, the donor's own shape (its tag 1 is exactly this
    -- a read of the shared state byte, an op_06 switch, and a jump back to the top; there is no standby
    tail). Replaces tag 1 outright via :func:`eb.edit.replace_function_body` -- the earlier
    ``inject_npc(intro=)`` splice could only run ONCE, so the moogle could pop out but never go back in.

    Two live transitions, matching the decoded cycle::

        POP_REQ  -> show, vertical hop onto the container, turn to the player, restore collision, OUT
        HIDE_REQ -> hop down, snap into the container, shrink collision away, hide, IN

    ``container_pos`` is ``(x, z[, y])`` -- the container's own spot; the landing is that x/z at
    ``y - height``. No perspective-tuned coordinate is involved (see the cycle note above)."""
    state_idx, _hs = reveal_vars(index)
    cx, cz, cy = (tuple(int(v) for v in container_pos) + (0, 0))[:3]
    # ⚠ COORDINATE CONVENTION. The kit's opcode emitters take y as world HEIGHT with UP = POSITIVE and
    # negate it on encode (see opcodes.move_instant_xzy / setup_jump). The donor's RAW bytes therefore
    # read -362 for a moogle standing 362 above a cask whose own raw y is -2. In THIS function's terms
    # the cask is at y=+2 and its top is y=+362, so the lift ADDS. Getting this backwards puts the
    # moogle underground with no build-time signal.
    top_y = cy + int(height)
    pop = (opcodes.encode(0x93, REVEAL_SHOW_FLAGS)
           + reveal_spine_body(jump_to=(cx, cz, top_y), face_to=(cx, cz),
                               steps=steps, sfx=sfx, blend=blend)
           # DETACH while perched: the landing is off-floor, and a walkmesh attach here snaps the
           # moogle down INTO the container on any field whose cask sits on walkable ground (the donor
           # never re-attaches at height either -- see act_save_body's pathing note: its perch-side
           # SetPathing(1) is inert only because its cask corner is off-mesh).
           + opcodes.set_pathing(0)
           + reveal_landing_dressing(player_uid)
           + _region.set_var(_region.GLOB_UINT8, state_idx, REVEAL_STATE_OUT))
    # The stow is a REAL ballistic jump back down, not a teleport: the donor does
    # `SetupJump(-250, -2, -571, 10) ; Jump()` (field 407 tag 3 @8674) -- the moogle visibly hops back
    # into the cask. A MoveInstantXZY here made it blink out of existence instead.
    hide = (opcodes.set_jump_animation(REVEAL_HOP_CLIP, int(blend[0]), int(blend[1]))
            + (act_sfx(int(sfx), vol=REVEAL_SFX_VOL) if sfx else b"")
            + opcodes.run_jump_animation() + opcodes.wait_animation()
            + opcodes.setup_jump(cx, cz, cy, int(steps)) + opcodes.jump()
            + opcodes.run_land_animation() + opcodes.wait_animation()
            + opcodes.set_pathing(1)                         # back on the floor: re-attach (undoes the
                                                             # pop's perch detach; safe at ground level)
            + opcodes.encode(0x4B, *REVEAL_IN_LOGICAL_SIZE)  # collision shrunk away (case 102's own)
            + opcodes.encode(0x93, REVEAL_HIDE_FLAGS)
            + _region.set_var(_region.GLOB_UINT8, state_idx, REVEAL_STATE_IN))
    body = (_if_state(state_idx, REVEAL_STATE_POP_REQ, pop)
            + _if_state(state_idx, REVEAL_STATE_HIDE_REQ, hide)
            + opcodes.wait(1))
    return body + bytes([0x01]) + struct.pack("<h", -(len(body) + 3))     # jump back to the top, forever


def gate_until_revealed(body: bytes, index: int = 0) -> bytes:
    """Wrap a save-point dispatch so it is INERT until this save point's moogle has actually popped:
    ``if (state != DONE) return;`` ahead of ``body``.

    Why it exists: the ``[[savepoint]]`` press-ZONE opens the save menu on its own, independently of the
    moogle. With ``reveal_style = "barrel_pop"`` that let the player stand on the zone and save while the
    moogle was still hidden in the cask -- so the reveal gated nothing and the cask was pure decoration
    (adversarial review finding, reproduced end to end). The moogle's own TALK path needs no gate: it is
    unreachable while hidden, because ``SetObjectFlags(14)`` carries the disable-talk bit.

    NOTE the transient scope: MAP vars are wiped on every field load, so re-entering the field re-hides
    the moogle AND re-closes this gate -- the player must pop the cask again each visit. That matches the
    donor (its state lives in the same wiped MAP byte) and is the intended per-visit theatre."""
    return _region.if_block(_cond_neq(_region.GLOB_UINT8, reveal_vars(index)[0], REVEAL_STATE_OUT),
                            opcodes.RETURN) + bytes(body)


def build_cask_init(x: int, z: int, *, face: int = 0) -> bytes:
    """The cask/barrel's Init (tag 0): ``SetModel(241, 93) -> SetStandAnimation(1904) ->
    SetObjectLogicalSize(1, 50, 50) -> SetObjectFlags(37)`` (the task brief's opcode order), with the same
    D9-const + CreateObject + TurnInstant placement boilerplate every from-scratch object Init in this kit
    uses (:func:`content.npc.build_npc_init`, :func:`content.chest.build_chest_init`). The model + animset
    + pose resolve through the kit's own prop-archetype catalog (``"cask"`` / its ``"barrel"``/``"crate"``
    aliases -> ``GEO_ACC_F0_CSK``, model id **241**, pose **1904** -- verified to match the task brief's
    cited bytes exactly), and the accessory animset **93** is the SAME value the ACT's own book/feather
    props use (:data:`ACT_PROP_ANIMSET`) -- both are ACC props off the ``NPC_PARAMS`` catalog."""
    from . import npc as _npc
    from .. import prop_archetypes as _prop_archetypes
    model, pose = _prop_archetypes.resolve("cask")            # (241, 1904) -- GEO_ACC_F0_CSK
    parts = [_npc._d9_const(0, x), _npc._d9_const(4, z), _npc._d9_const(6, face), _npc._d9_const(2, 0),
            opcodes.set_model(model, ACT_PROP_ANIMSET), _npc._CREATE_OBJECT, _npc._TURN_INSTANT,
            opcodes.set_stand_animation(pose),
            opcodes.encode(0x4B, *CASK_LOGICAL_SIZE),
            opcodes.encode(0x93, CASK_FLAGS),
            opcodes.RETURN]
    return b"".join(parts)


def cask_trigger_body(index: int = 0) -> bytes:
    """The cask's press-handler body -- the reveal side of the handshake: a ONE-SHOT guard (``if (state
    != IDLE) return`` -- already popped, or popping, either way a re-press is inert), lock control, raise
    the handshake + request POP, poll the SAME bit the moogle's own loop clears (:func:`_while_truthy`,
    the exact shape the ACT's own release already uses), then hand control back.

    Exported standalone (not only reachable via :func:`build_cask_init`/:func:`inject_cask`) so a
    ``reveal_container = false`` field can splice this into its own hand-authored trigger scenery instead
    of the shipped cask -- see ``docs/SAVEPOINT.md``. ``index`` selects this save point's own rendezvous
    pair (:func:`reveal_vars`) and MUST match the ``index`` its moogle's :func:`reveal_state_loop` was
    emitted with, or the two halves of the handshake talk past each other."""
    state_idx, _hs = reveal_vars(index)
    # ONLY while the moogle is stowed. Once it is OUT it stands on top of this container and IT is the
    # interact target -- the donor has no second "press the barrel" option, and a press that did nothing
    # (the earlier build's silent guard-return) reads as a dead prop.
    return (_region.if_block(_cond_neq(_region.GLOB_UINT8, state_idx, REVEAL_STATE_IN), opcodes.RETURN)
            + opcodes.DISABLE_MOVE
            + _region.set_var(_region.GLOB_UINT8, state_idx, REVEAL_STATE_POP_REQ)
            + _while_not_eq(_region.GLOB_UINT8, state_idx, REVEAL_STATE_OUT, opcodes.wait(1))
            + opcodes.ENABLE_MOVE + opcodes.RETURN)


def reveal_reopen_mark(index: int = 0) -> bytes:
    """``reopen = 1`` -- appended by the build to every non-Cancel menu row. See
    :func:`reveal_menu_cycle`; the bit is this save point's (formerly handshake) rendezvous bit, now free
    because the cask polls the state byte directly."""
    return _region.set_var(_region.MAP_BOOL, reveal_vars(index)[1], 1)


def reveal_menu_cycle(menu_body: bytes, *, index: int = 0) -> bytes:
    """Wrap the moogle's talk menu in the donor's own CYCLE (steps 6-7 of the real room)::

        loop: reopen = 0
              <menu>                  -- Save / Tent / Mognet / ... / Cancel; each ACTION arm sets reopen
              if (reopen) goto loop   -- so the menu comes back by itself after a save
        state = HIDE_REQ              -- Cancel is BODILESS, so falling through IS the cancel signal:
                                         the moogle hops back down into its container

    In field 407 this whole cycle lives in the ACT itself (tag 3): its own menu loop jumps back to the
    redisplay (@6590), and the Cancel fall-through runs the close-out tail (@6593 -- the animated dive
    into the cask + the cask re-arm via its tag 29). The entry-0 tag-1 DIRECTOR plays no part (the
    2026-07-22 full decode: it is a one-shot LOAD sequence -- show/disarm/stow -- dead after its
    RETURN; an earlier note wrongly credited it with the post-save walk). So the kit's talk handler
    owning the cycle IS the donor's shape, not a simplification. Cancel staying bodiless is a
    correctness requirement, not a shortcut (:func:`_row0_only`)."""
    state_idx, reopen_bit = reveal_vars(index)
    # ⚠ THE MENU BODY ENDS IN A RETURN. Every dispatch in this module closes with
    # `ENABLE_MENU + ENABLE_MOVE + RETURN`, so anything appended AFTER it is unreachable -- the first
    # version of this wrapper put the whole cycle there and it was dead code: cancel never stowed the
    # moogle and the menu never reopened (playtest, 2026-07-19). Strip that tail, wrap what remains, and
    # re-emit the tail at the real end.
    tail = opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN
    body = bytes(menu_body)
    if not body.endswith(tail):
        raise ValueError("reveal_menu_cycle: the menu body does not end in the expected "
                         "ENABLE_MENU/ENABLE_MOVE/RETURN tail -- refusing to wrap it, because appending "
                         "past a RETURN silently produces dead code")
    body = body[:-len(tail)]
    clear = _region.set_var(_region.MAP_BOOL, reopen_bit, 0)
    loop = clear + body
    # ⚠ THE DISPLACEMENT COUNTS THE CONDITION TOO. A backward `01 <i16>` is measured from the END of the
    # jump instruction back to its target, so every byte in between counts: the loop body, the if's
    # CONDITION, the 3-byte JMP_FALSE, and the 3-byte jump itself. The first cut omitted len(cond) and so
    # landed 5 bytes past the loop top -- mid-instruction -- which executed garbage after a save (the
    # moogle stowed itself instead of staying on the cask, and the next Cancel softlocked). Playtest,
    # 2026-07-19. Same convention as :func:`_while_truthy`, which measures from the start of its block.
    cond = _region.cond_truthy(_region.MAP_BOOL, reopen_bit)
    back = bytes([0x01]) + struct.pack("<h", -(len(loop) + len(cond) + 3 + 3))
    cycle = loop + _region.if_block(cond, back)
    # structural self-check: decode the jump we just emitted and confirm it targets the loop TOP exactly.
    # Cheap, and it turns a silent mid-instruction landing into a build-time failure.
    _jmp_at = len(loop) + len(cond) + 3
    _target = _jmp_at + 3 + struct.unpack("<h", cycle[_jmp_at + 1:_jmp_at + 3])[0]
    if _target != 0:
        raise AssertionError(f"reveal_menu_cycle: the reopen jump targets byte {_target}, not the loop "
                             f"top (0) -- a mid-instruction landing would execute garbage")
    return cycle + _region.set_var(_region.GLOB_UINT8, state_idx, REVEAL_STATE_HIDE_REQ) + tail


def inject_cask(data, x: int, z: int, *, face: int = 0, slot: int | None = None, index: int = 0,
                reserve_party_band: bool = False, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0):
    """Inject the barrel_pop container: a type-2 object, Init (tag 0, :func:`build_cask_init`) + a tag-3
    press handler (:func:`cask_trigger_body`) -- the kit's own "approach + press, one-shot" idiom standing
    in for the donor's tag-2-range + manual-B_KEYON shape (see :func:`content.chest`'s own fidelity note
    for why: the auto-dispatched talk tag is functionally identical and needs no hand-rolled key poll).
    Returns ``(new_bytes, slot)``."""
    from . import npc as _npc
    from . import object as _object
    init = build_cask_init(int(x), int(z), face=int(face))
    press = cask_trigger_body(index)
    if len(press) < 9:                       # IsActuallyTalkable polls tag3[ip+7/8]; keep it >= 9 bytes
        press += b"\x00" * (9 - len(press))
    table_len = 2 * 4
    table = struct.pack("<HH", 0, table_len) + struct.pack("<HH", 3, table_len + len(init))
    entry = bytes([_npc.NPC_ENTRY_TYPE, 2]) + table + init + press
    out, slot = _object.seat_entry(data, entry, reserve_party_band=reserve_party_band, slot=slot)
    out = edit.activate(out, opcodes.init_object(slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out, slot


def inject_barrel_pop_reveal(data, *, container_pos, height: int = REVEAL_CONTAINER_HEIGHT,
                             steps=None, sfx=None, container: bool = True,
                             player_uid: int = PLAYER_UID, index: int = 0):
    """Wire the barrel_pop reveal for ONE save point. When ``container`` (default True), injects the cask
    at ``container_pos`` FIRST -- so it consumes its entry slot before any later ``first_free_slot()``
    prediction (e.g. the ACT's :func:`inject_act_cluster`) runs on this same ``data``, avoiding a slot
    collision; ``build.py`` relies on this ordering.

    Returns ``(new_data, moogle_init_tail)``. The tail spawns the moogle STOWED (hidden + collision shrunk
    away) and goes to ``content.npc.inject_npc(init_tail=...)``. The moogle's tag-1 state machine is NOT
    returned here -- the build installs :func:`reveal_state_loop` over tag 1 with
    ``eb.edit.replace_function_body`` after injection, because the loop must run forever (an
    ``inject_npc(intro=)`` splice runs once, which could pop the moogle out but never stow it again).

    ``container=False`` skips the cask; the field author then wires their own trigger to
    :func:`cask_trigger_body` (docs/SAVEPOINT.md)."""
    out = data
    cx, cz = (tuple(int(v) for v in container_pos) + (0, 0))[:2]
    if container:
        out, _ = inject_cask(out, cx, cz, index=index)
    # The moogle spawns STOWED: hidden, at the container's own spot, collision shrunk away -- so it is
    # neither visible nor walkable-into before the pop. (The earlier build spawned it hidden but at full
    # size, leaving an invisible obstacle in front of the cask.)
    tail = (reveal_init_tail()
            + opcodes.encode(0x4B, *REVEAL_IN_LOGICAL_SIZE))
    return out, tail


def graft_director(data, director_body):
    """Graft the save-sequence DIRECTOR (the donor field's entry-0 tag-1, from
    :func:`eventscan.extract_savepoint_director`) into the fork's EMPTY entry-0 tag-1, so it puppeteers the
    carried save Moogle. The director references no entries -- it drives the Moogle through shared transient
    MAP vars only -- so it grafts VERBATIM (replace the empty system-loop body with it). The carried Moogle +
    carried cask + this director then reconstitute the source field's exact state machine over those shared
    vars: the Moogle lowers into the barrel, pops out on a cask push, and runs the save flourish. The fork's
    entry-0 tag-1 is empty in a blank field, so this is a clean swap (docs/SAVEPOINT.md)."""
    return edit.replace_function_body(data, 0, 1, bytes(director_body))
