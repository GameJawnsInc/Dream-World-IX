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

from ..eb import EbScript, disasm, edit, opcodes

REINIT_TAG = 10

# RunSoundCode (0xC5) sound-codes that select the AUDIBLE field BGM (FF9Snd.cs FF9AllSoundDispatch).
# A field rescore MUST rewrite BOTH: PLAY starts the song, but LOAD is what makes the song's data
# resident -- patch PLAY alone and the OLD song stays loaded and keeps playing even when PLAY asks for
# the new one (the Ice Cavern fork bug: Main_Init does PLAY(60) AND LOAD(60), only PLAY was swapped).
SONG_PLAY = 0       # FF9SOUND_SONG_PLAY
SONG_LOAD = 1792    # FF9SOUND_SONG_LOAD (0x0700)
_BGM_CODES = (SONG_PLAY, SONG_LOAD)


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
    out = edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                        spawn_wait_occurrence=spawn_wait_occurrence)
    return out


def add_music_to_reinit(eb_bytes, song: int) -> bytes:
    """Insert RunSoundCode(0, song) at the start of the entry-0 tag-10 handler (after-battle resume)."""
    eb = EbScript.from_bytes(eb_bytes)
    f = eb.entry(0).func_by_tag(REINIT_TAG)
    if f is None:
        raise ValueError("entry 0 has no tag-10 handler (run content.reinit.add_reinit first)")
    return edit.insert_bytes(eb_bytes, f.abs_start, opcodes.run_sound_code(0, song))


def replace_field_music(eb_bytes, new_song: int, *, old_song: int | None = None):
    """REPLACE the field's BGM in place: overwrite the song operand of every immediate field-BGM ``RunSoundCode``
    -- both the PLAY (``code 0``) AND the LOAD (``code 1792``) of the donor's BGM song id -- with ``new_song``
    (a length-preserving 2-byte swap). For a VERBATIM fork this rewrites the donor's OWN field-BGM calls (the
    Main_Init load+play plus any after-battle/tag-10 resume), so the new track REPLACES rather than stacks
    (unlike :func:`add_field_music`, which appends a play). Rescoring the LOAD is essential: PLAY alone leaves the
    OLD song resident, so the engine keeps playing it. ``old_song`` defaults to :func:`ff9mapkit.eventscan.scan_music`
    (the donor's field BGM, found via its PLAY). A call referencing a DIFFERENT song id (a cutscene track / an
    SFX) is untouched -- only the field BGM song is rescored.

    Returns ``(out_bytes, n_patched, old_song)``. ``n_patched == 0`` with ``old_song is None`` means the donor
    has no immediate field BGM to replace (silent, or its BGM is set by a computed value); ``old_song == new_song``
    is a no-op (``n_patched == 0``, ``old_song`` echoed). The caller owns the empty case (error / append a track)."""
    from .. import eventscan as _es
    from .object import _arg_byte_offset                  # decoder-derived operand byte offset (handles argflag)
    if old_song is None:
        old_song = _es.scan_music(eb_bytes)
    if old_song is None:                                  # silent donor / expression-computed -> nothing to swap
        return bytes(eb_bytes), 0, None
    old_song, new_song = int(old_song), int(new_song)
    if old_song == new_song:                              # already the desired track -> idempotent no-op
        return bytes(eb_bytes), 0, old_song
    OP, SONG = _es.RUN_SOUND_CODE, 1                      # operand 1 = song id (operand 0 = sound-code: PLAY 0 / LOAD 1792)
    width = disasm.argsize(OP, SONG)                      # 2 bytes (song id)
    eb = EbScript.from_bytes(eb_bytes)
    buf = bytearray(eb_bytes)
    seen: set = set()                                    # entry 0's tag-0/tag-10 can enumerate one shared func
    n = 0                                                # region twice -> dedupe by offset (two real plays differ)
    for e in eb.entries:
        if e.empty:
            continue
        for f in e.funcs:
            for ins in eb.instrs(f):
                if ins.op != OP or ins.imm(0) not in _BGM_CODES or ins.imm(1) != old_song:
                    continue                              # not a PLAY/LOAD of the donor's field-BGM song id
                if ins.off in seen:
                    continue
                bo = _arg_byte_offset(ins, SONG)          # None iff a preceding operand is an expression
                if bo is None:
                    continue
                seen.add(ins.off)
                buf[ins.off + bo:ins.off + bo + width] = new_song.to_bytes(width, "little")
                n += 1
    return bytes(buf), n, old_song
