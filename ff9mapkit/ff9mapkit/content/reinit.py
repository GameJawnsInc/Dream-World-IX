"""Add the after-battle handler (entry-0 tag-10 "Main_Reinit") a custom field needs.

After a random battle, EventEngine restores the field then calls Request(entry0, 0, 10).
``EnterBattleEnd`` has suspended every object; only when the tag-10 handler RETURNS at level
0 does ``ExitBattleEnd`` un-suspend them. Battle fields ship a Main_Reinit; fields cloned
from a cutscene field (like our blank) have none, so the player stays frozen after battle.

Minimal handler: ``EnableMove ; return``. With ``with_fade=True`` it is prefixed with a quick
``FadeFilter`` fade-in, because the battle-return fade is a 256-frame *timed* fade that only a
field-issued FadeFilter overrides (Main_Init issues one, but after battle the field runs
tag-10, not Main_Init).

Re-layout: entry-0's function table grows by one 4-byte slot (existing funcs' fpos += 4); the
new function body is appended after entry-0's code; every later entry shifts in the file so
its entry-table offset += growth. entryCount is unchanged.
"""

from __future__ import annotations

import struct

from ..binutils import set_u16, u16
from ..eb import EbScript, opcodes

REINIT_TAG = 10


def add_reinit(eb_bytes, *, with_fade: bool = True, fade_frames: int = 16,
               tag: int = REINIT_TAG) -> bytes:
    """Add an entry-0 tag-10 handler (EnableMove; return), optionally with a fast fade-in."""
    body = b""
    if with_fade:
        body += opcodes.fade_filter(2, fade_frames, 0, 0, 0, 0)   # SUB => fade-IN over N frames
    body += opcodes.ENABLE_MOVE + opcodes.RETURN

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
