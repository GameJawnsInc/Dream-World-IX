"""Add the after-battle handler (entry-0 tag-10 "Main_Reinit") a custom field needs.

After a random battle, EventEngine restores the field then calls Request(entry0, 0, 10).
``EnterBattleEnd`` has suspended every object; only when the tag-10 handler RETURNS at level
0 does ``ExitBattleEnd`` un-suspend them. Battle fields ship a Main_Reinit; fields cloned
from a cutscene field (like our blank) have none, so the player stays frozen after battle.

The handler is RESTORE-NOT-GRANT (movement survey Tier-2 item 7, stock's own Reinit semantics):
``if (IsMovementEnabled && !MAP156) EnableMove``. The engine restores the PRE-BATTLE
``usercontrol`` via context-copy BEFORE requesting tag-10 (EventEngine.cs:668-669), so sysvar 2
here reads the pre-battle lock state -- the engine's restored context IS the latch, no script
flag bookkeeping needed (stock maintains GlobBool 158 for the same job). A battle that fired
inside a lock (a scripted / behavior-tree ``Battle`` -- random encounters cannot accumulate
while locked) returns still locked, and the interrupted bracket's own EnableMove restores
control when its scene finishes; the old unconditional grant freed the player mid-scene.
MAP-bool 156 (:data:`region.STAY_LOCKED_IDX`) is the one-way stay-locked latch. A free-roam
battle reads sysvar2==1 and 156==0, so the grant runs exactly as before. With ``with_fade=True``
the body is prefixed with a quick ``FadeFilter`` fade-in, because the battle-return fade is a
256-frame *timed* fade that only a field-issued FadeFilter overrides (Main_Init issues one, but
after battle the field runs tag-10, not Main_Init).

Re-layout: entry-0's function table grows by one 4-byte slot (existing funcs' fpos += 4); the
new function body is appended after entry-0's code; every later entry shifts in the file so
its entry-table offset += growth. entryCount is unchanged.
"""

from __future__ import annotations

import struct

from ..binutils import set_u16, u16
from ..eb import EbScript, opcodes
from . import region as _region

REINIT_TAG = 10

# `if (IsMovementEnabled && !MAP156)` -- the restore-not-grant gate (module docstring): sysvar 2
# carries the engine-restored pre-battle lock state; MAP 156 is the one-way stay-locked latch.
GRANT_GATE = bytes([_region.EXPR_OP, _region.T_SYSVAR, _region.SYSVAR_USERCONTROL,
                    _region.MAP_BOOL, _region.STAY_LOCKED_IDX,
                    _region.T_NOT, _region.T_ANDAND, _region.T_END])


def add_reinit(eb_bytes, *, with_fade: bool = True, fade_frames: int = 16,
               tag: int = REINIT_TAG, prologue: bytes = b"") -> bytes:
    """Add an entry-0 tag-10 handler (``if (control was on && !stay-locked) EnableMove; return``),
    optionally with a fast fade-in. See the module docstring for the restore-not-grant gate.

    ``prologue`` (default empty) is raw bytecode run FIRST -- before the fade-in/EnableMove -- e.g. the
    ``[deathrules] on_defeat`` wipe-warp check (:func:`ff9mapkit.battle.deathrules.field_prologue`), which
    may ``Field()``-transition away so nothing after it runs on that path."""
    body = bytes(prologue)
    if with_fade:
        body += opcodes.fade_filter(2, fade_frames, 0, 0, 0, 0)   # SUB => fade-IN over N frames
    body += _region.if_block(GRANT_GATE, opcodes.ENABLE_MOVE) + opcodes.RETURN

    b = bytearray(eb_bytes)
    entry_count = b[3]
    off0, sz0 = u16(b, 128), u16(b, 130)
    es = 128 + off0
    etype, fc = b[es], b[es + 1]
    fbase = es + 2
    funcs = [[u16(b, fbase + i * 4), u16(b, fbase + i * 4 + 2)] for i in range(fc)]
    if any(t == tag for t, _ in funcs):
        raise ValueError(f"entry 0 already has a function with tag {tag}")
    code = bytes(b[fbase + fc * 4: es + sz0])
    new_funcs = [[t, fp + 4] for t, fp in funcs] + [[tag, (fc + 1) * 4 + len(code)]]
    new_entry = bytearray([etype, fc + 1])
    for t, fp in new_funcs:
        new_entry += struct.pack("<HH", t, fp)
    new_entry += code + body
    growth = len(new_entry) - sz0

    out = bytearray(bytes(b[:es]) + bytes(new_entry) + bytes(b[es + sz0:]))
    set_u16(out, 130, len(new_entry))                          # entry-0 size
    for i in range(1, entry_count):                             # relocate later entries
        slot = 128 + i * 8
        if u16(out, slot + 2) > 0 and u16(out, slot) > off0:
            set_u16(out, slot, u16(out, slot) + growth)
    return bytes(out)
