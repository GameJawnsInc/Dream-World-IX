"""Add random-battle encounters to a field.

Appends a type-0 "code" entry whose function runs ``SetRandomBattles`` +
``SetRandomBattleFrequency``, and activates it from Main_Init via ``InitCode`` written over a
``Wait`` filler (shift-free). The battle scene id selects which encounter table is used (e.g.
67 = Evil Forest / the first, weakest battles). Frequency 0..255 (higher = more frequent).

NOTE: a field that hosts encounters also needs an after-battle reinit handler or the player
freezes on return — see :mod:`ff9mapkit.content.reinit`.
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes


def _battle_entry(pattern: int, scenes, freq: int) -> bytes:
    scenes = list(scenes)
    if len(scenes) != 4:
        raise ValueError("need exactly 4 battle scene ids")
    code = opcodes.set_random_battles(pattern, *scenes) + opcodes.set_random_battle_frequency(freq) \
        + opcodes.RETURN
    # entry: type 0, funcCount 1, funcTable[(tag 0, fpos 4)], then code
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + code


def inject_encounter(eb_bytes, *, scene: int, freq: int = 255, pattern: int = 1, scenes=None,
                     slot: int | None = None, spawn_wait_n: int = 2,
                     spawn_wait_occurrence: int = 0) -> bytes:
    """Add encounters of ``scene`` (or an explicit 4-tuple ``scenes``) at ``freq``."""
    if scenes is None:
        scenes = (scene,) * 4
    eb = EbScript.from_bytes(eb_bytes)
    if slot is None:
        slot = eb.first_free_slot()
    out = edit.append_entry(eb_bytes, slot, _battle_entry(pattern, scenes, freq))
    wait_off = edit.find_wait(EbScript.from_bytes(out), n=spawn_wait_n,
                              occurrence=spawn_wait_occurrence)
    out = edit.patch_bytes(out, wait_off, opcodes.init_code(slot, 0),
                           expect=opcodes.wait(spawn_wait_n))
    return out
