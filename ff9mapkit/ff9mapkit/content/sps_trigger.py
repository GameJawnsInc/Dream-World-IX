"""Emit the ``RunSPSCode`` create+place trigger for an authored ``[[sps]]`` effect (Tier 2 creator).

A new effect's ``<id>.sps.bytes`` is inert until the field's ``.eb`` fires ``RunSPSCode(slot, 130, id, 0, 0)``
to LOAD it, then positions + animates it. This injects that sequence as a standalone ``InitCode`` code-entry
in Main_Init -- the SAME proven arming as :func:`ff9mapkit.content.onentry.inject_on_entries`, so the effect
spawns at field load (post-fade) on BOTH the synthesize and verbatim-fork paths.

Op sequence per effect (confirmed against ``CommonSPSSystem.SetObjParm``):
  ``RunSPSCode(slot, 130, id, 0, 0)``   LOAD (Arg1==0 -> per-scene FieldMaps/<scene>/<id>.sps + the in-VRAM tcb)
  ``RunSPSCode(slot, 131, 3, 1, 0)``    ATTR set VISIBLE|UPDATE_ANY_FRAME
  ``RunSPSCode(slot, 135, x, y, z)``    POS -- the engine NEGATES Arg1 (Y) itself, so emit raw +Y
  ``RunSPSCode(slot, 156, abr, 0, 0)``  ABR blend (optional)        0=50%add 1=add 2=sub 3=25%add
  ``RunSPSCode(slot, 160, rate, 0, 0)`` FRAMERATE (optional)        16 = 1x
  ``RunSPSCode(slot, 145, scale, 0, 0)``SCALE (optional)            4096 = 1x

Opcode ``0xB3 RunSPSCode`` (operand widths ``[1,1,2,2,2]`` from ``eb/_optables.py``). Byte-identical when
no specs. -> [[project-ff9-sps-authoring]], docs/SPS.md.
"""
from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes

# parmType constants (Global/SPS/SPSConst.cs)
SPS_LOAD = 130
SPS_ATTR = 131
SPS_POS = 135
SPS_SCALE = 145
SPS_ABR = 156
SPS_FRAMERATE = 160
ATTR_VISIBLE_UPDATE = 3            # ATTR_VISIBLE(1) | ATTR_UPDATE_ANY_FRAME(2)
_RUN_SPS = 0xB3


def sps_trigger_ops(*, slot: int, sps_id: int, pos=(0, 0, 0),
                    abr: int | None = None, framerate: int | None = None, scale: int | None = None) -> bytes:
    """The create+place op sequence for one effect (no entry/RETURN wrapper)."""
    x, y, z = pos
    ops = opcodes.encode(_RUN_SPS, slot, SPS_LOAD, sps_id, 0, 0)
    ops += opcodes.encode(_RUN_SPS, slot, SPS_ATTR, ATTR_VISIBLE_UPDATE, 1, 0)
    ops += opcodes.encode(_RUN_SPS, slot, SPS_POS, x, y, z)          # engine negates Y -> emit raw +Y
    if scale is not None:
        ops += opcodes.encode(_RUN_SPS, slot, SPS_SCALE, scale, 0, 0)
    if abr is not None:
        ops += opcodes.encode(_RUN_SPS, slot, SPS_ABR, abr, 0, 0)
    if framerate is not None:
        ops += opcodes.encode(_RUN_SPS, slot, SPS_FRAMERATE, framerate, 0, 0)
    return ops


def inject_sps_triggers(data, specs, *, spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0):
    """Inject the create+place triggers for every authored effect as ONE standalone ``InitCode`` code-entry
    (all specs share one Main_Init arm -- one ``Wait`` filler consumed, vs one per effect). ``specs`` is a list
    of :func:`sps_trigger_ops` kwarg dicts. Returns new ``.eb`` bytes; a no-op when ``specs`` is empty."""
    specs = list(specs)
    out = data if isinstance(data, (bytes, bytearray)) else data.to_bytes()
    if not specs:
        return out
    body = b"".join(sps_trigger_ops(**s) for s in specs) + opcodes.RETURN
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    entry_slot = EbScript.from_bytes(out).first_free_slot()
    out = edit.append_entry(out, entry_slot, entry)
    out = edit.activate(out, opcodes.init_code(entry_slot, 0),
                        spawn_wait_n=spawn_wait_n, spawn_wait_occurrence=spawn_wait_occurrence)
    return out
