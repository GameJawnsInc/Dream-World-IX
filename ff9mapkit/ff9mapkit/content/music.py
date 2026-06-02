"""Add field background music (BGM).

Field music plays via ``RunSoundCode(0, songId)`` (``ff9fldsnd_song_play``); e.g. song 9 =
"Vivi's Theme (Disc 1)". Two play points:
  * :func:`add_field_music` appends a tiny init entry ``{RunSoundCode(0, song); return}`` and
    activates it from Main_Init (plays on room entry) — same shift-free mechanism as encounters.
  * :func:`add_music_to_reinit` inserts the same call into the entry-0 tag-10 handler so the
    track resumes after a battle (otherwise the field is silent on battle-return).
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes

REINIT_TAG = 10


def _music_entry(song: int) -> bytes:
    code = opcodes.run_sound_code(0, song) + opcodes.RETURN
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + code


def add_field_music(eb_bytes, song: int, *, slot: int | None = None, spawn_wait_n: int = 2,
                    spawn_wait_occurrence: int = 0) -> bytes:
    """Play ``song`` on room entry (appended init entry + InitCode over a Wait filler)."""
    eb = EbScript.from_bytes(eb_bytes)
    if slot is None:
        slot = eb.first_free_slot()
    out = edit.append_entry(eb_bytes, slot, _music_entry(song))
    wait_off = edit.find_wait(EbScript.from_bytes(out), n=spawn_wait_n,
                              occurrence=spawn_wait_occurrence)
    out = edit.patch_bytes(out, wait_off, opcodes.init_code(slot, 0),
                           expect=opcodes.wait(spawn_wait_n))
    return out


def add_music_to_reinit(eb_bytes, song: int) -> bytes:
    """Insert RunSoundCode(0, song) at the start of the entry-0 tag-10 handler (after-battle resume)."""
    eb = EbScript.from_bytes(eb_bytes)
    f = eb.entry(0).func_by_tag(REINIT_TAG)
    if f is None:
        raise ValueError("entry 0 has no tag-10 handler (run content.reinit.add_reinit first)")
    return edit.insert_bytes(eb_bytes, f.abs_start, opcodes.run_sound_code(0, song))
