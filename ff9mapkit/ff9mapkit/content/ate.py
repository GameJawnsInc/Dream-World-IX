"""``[[ate]]`` -- synthesize an Active Time Event (FF9's optional "Press SELECT" cutscene mechanism).

An ATE has three engine-visible parts (see ``docs/ATE_SYSTEM.md``); this module emits all of them onto
a custom field, byte-for-byte as the real Lindblum Main-St hub (field 552, the "Small-Town Knight" ATE):

  Main_Init wiring (prepended):
      ATE(mode)                       # 0xD7 -> EIcon.SetAIcon -> the blinking "Active Time Event" HUD prompt
      <avail flag> = 1                # the author's own GLOB availability flag
      InitCode(<menu slot>)           # activate the menu code-entry (its tag-1 func then loops each frame)

  the menu code-entry (appended):
      func0 (tag 0): RETURN           # trivial init
      func1 (tag 1): the per-frame LOOP --
          if ( usercontrol==1  AND  <avail>==1  AND  B_KEYON(SELECT) ) {     # the real gate, field 552 [11667]
              DisableMove ; EnableDialogChoices ; WindowSync(win, 64=winATE, prompt) ;  # the "Select event" menu
              <branch on GetChoose -> the picked row's body> ; EnableMove
          }
          RETURN

Engine facts grounding every byte (all verified): ``AICON=0xD7`` (the blink HUD), ``winATE=64`` ->
``CaptionType.ActiveTimeEvent``, ``GetChoose`` = sysvar 9, ``B_KEYON=0x4F`` (press-edge), ``Select=1u``,
sysvar 2 = ``usercontrol``. The menu + per-row branch reuse :mod:`ff9mapkit.content.choice` (the same
``GetChoose`` machinery) with ``flags=64`` so the window renders with the ATE caption; each row's body is the
ordinary event/choice action vocabulary (a narration line, a story-flag set, or a ``warp`` to the cutscene
field -- the real hub->destination pattern, e.g. Small-Town Knight -> ``Field(555)``).
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import choice as _choice, region as _region

# Availability-flag band: GLOB bools, clear of events (8000), cutscene (8100), choice (8200). Each [[ate]]
# on a field claims ATE_FLAG_BASE + i so multiple ATEs don't collide.
ATE_FLAG_BASE = 8300

# ATE(mode) presets -- the arg is a 3-bit FLAG WORD, not an enum (see opcodes.ate / EIcon.cs:416-454 /
# docs/ATE_SYSTEM.md): >0 enable (0=off); &3==2 Gray (else Blue); &4 force-show (draw without user control).
MODE_BLUE = 1     # Blue, no force -- the optional Press-SELECT prompt (shows only with control). The [ate] HUB default.
MODE_GRAY = 2     # Gray, no force -- NEVER used in the real game (can't show during a no-control beat; use 6 for grey).
MODE_FORCE = 5    # Blue + force -- field 206's lone real site. AVOID for authoring: re-flashes the SELECT glyph (use 6).

WIN_ATE = 64      # ETb.winATE -> Dialog.CaptionType.ActiveTimeEvent


def _build_entry(funcs, etype: int = 0) -> bytes:
    """Assemble an entry body from ``funcs = [(tag, code_bytes), ...]``: ``[type][func_count]`` + the
    func table (``tag:u16, fpos:u16`` each; ``fpos`` is relative to entryStart+2) + the concatenated code.
    Mirrors the layout :class:`ff9mapkit.eb.model.EbScript` parses (so it round-trips)."""
    fc = len(funcs)
    fpos = fc * 4                                  # code starts right after the func table
    table = bytearray()
    code = bytearray()
    for tag, c in funcs:
        table += struct.pack("<HH", tag, fpos)
        code += c
        fpos += len(c)
    return bytes([etype, fc]) + bytes(table) + bytes(code)


JMP_OP = 0x01   # the undocumented UNCONDITIONAL jump (op_01): target = instr.end + signed-i16 offset


def menu_loop_body(prompt_txid: int, option_bodies, *, avail_idx: int, window: int = 1,
                   setup: bytes = b"") -> bytes:
    """The menu entry's tag-1 LOOP body. It must POLL each frame, exactly as the real ATE menu does
    (field 552 entry-7 tag-1)::

        loop:  if ( usercontrol AND avail AND B_KEYON(SELECT) ) { winATE menu }
               Wait(1)                 # yield a frame -> one poll per frame (not a busy-spin)
               JMP loop                # op_01 unconditional jump back to the top; NO RETURN

    The poller lives as long as the field is loaded (no terminate). ``setup`` is the optional
    ``EnableDialogChoices`` pre-choose opcode (default / cancel / hidden rows), from
    :func:`ff9mapkit.content.choice.pre_choose`.

    NB the earlier ``if(gate){menu} + RETURN`` form ran ONCE right after ``InitCode`` and never polled
    again -- so SELECT did nothing. The ``Wait(1)`` + ``op_01`` jump-back is what makes it a real loop."""
    menu = _choice.region_body(prompt_txid, option_bodies, window=window, flags=WIN_ATE, setup=setup)
    gate = _region.cond_ate_select(_region.GLOB_BOOL, avail_idx)
    body = _region.if_block(gate, menu) + opcodes.wait(1)
    back = -(len(body) + 3)                          # op_01 is 3 bytes; jump back to the loop top (offset 0)
    return body + bytes([JMP_OP]) + struct.pack("<h", back)


def menu_entry(prompt_txid: int, option_bodies, *, avail_idx: int, window: int = 1,
               setup: bytes = b"") -> bytes:
    """The complete ATE menu CODE-ENTRY body (ready for :func:`ff9mapkit.eb.edit.append_entry`): a trivial
    tag-0 init (RETURN) + the tag-1 polling loop (:func:`menu_loop_body`). InitCode'd from Main_Init."""
    return _build_entry([(0, opcodes.RETURN),
                         (1, menu_loop_body(prompt_txid, option_bodies, avail_idx=avail_idx,
                                            window=window, setup=setup))])


def main_init_inject(*, avail_idx: int, menu_slot: int, mode: int = MODE_BLUE) -> bytes:
    """The Main_Init wiring, prepended to entry-0 tag-0: arm the blinking prompt, set the availability
    flag, and activate the menu entry. ``ATE(mode) ; <avail>=1 ; InitCode(menu_slot)``."""
    return (opcodes.ate(mode)
            + _region.set_var(_region.GLOB_BOOL, avail_idx, 1)
            + opcodes.init_code(menu_slot))


def inject_ate(data, prompt_txid: int, option_bodies, *, avail_idx: int = ATE_FLAG_BASE,
               mode: int = MODE_BLUE, setup: bytes = b"") -> bytes:
    """Synthesize a complete ATE onto ``data`` (a field ``.eb``): append the SELECT-polling menu entry
    (:func:`menu_entry`) into a free slot, then PREPEND the Main_Init wiring (:func:`main_init_inject` --
    ``ATE(mode)`` + set the avail flag + ``InitCode`` the menu slot) to entry-0 tag-0. Returns new ``.eb``
    bytes. The prepend goes through :func:`ff9mapkit.eb.edit.insert_in_function`, which is boundary-safe even
    on a Main_Init with a ``0x06`` scenario jump-table. No-op-safe: pass real ``option_bodies`` (one per row).
    Default ``mode`` is Blue (mode 1, shows while the player has control -- the HUB convention). For a forced
    auto-play use mode 6 (Gray+force) via ``[cutscene] ate``, not ``MODE_FORCE`` (5, Blue+force) -- a force-shown
    Blue icon re-flashes the SELECT glyph during auto-play (mode arg = a 3-bit flag word; see EIcon.cs:416-454)."""
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    entry = menu_entry(prompt_txid, option_bodies, avail_idx=avail_idx, setup=setup)
    slot = EbScript.from_bytes(out).first_free_slot()
    out = edit.append_entry(out, slot, entry)
    return edit.insert_in_function(out, 0, 0, 0, main_init_inject(avail_idx=avail_idx, menu_slot=slot, mode=mode))
