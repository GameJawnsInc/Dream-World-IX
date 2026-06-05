"""Cutscenes -- ordered, control-locked scripted sequences.

This is the one thing the declarative content (NPCs / events / flags) can't express: a SEQUENCE that
runs in order. A cutscene is a code entry whose function steps through its actions with the player's
control disabled for the duration, optionally once (flag-gated), triggered on field entry.

v1 step types are the *controller-level* actions that need no per-actor targeting:
  * ``say``      -- a dialogue/narration window (WindowSync; blocks until dismissed),
  * ``wait``     -- pause N frames (Wait),
  * ``set_flag`` -- set a GlobBool story flag.
Actor movement / animation / camera pans are v2 (they act on a specific object's context -- Walk/
RunAnimation target the executing object, so they need the sequence to run in that actor's entry).

Grounded in the standard FF9 pattern -- ``DisableMove`` (0x2D) ... [WindowSync / Wait / set var] ...
``EnableMove`` (0x2E) -- gated by a flag so a one-time scene doesn't replay on re-entry.
"""

from __future__ import annotations

import struct

from ..eb import EbScript, edit, opcodes
from . import region as _region

# Default flag for a "play once" cutscene: the SAVE-PERSISTENT Global bool (survives reloads), high in
# gEventGlobal and clear of the event auto-once band (8000+).
CUTSCENE_FLAG_CLASS = _region.GLOB_BOOL
DEFAULT_CUTSCENE_FLAG = 8100


def say(text_id: int, *, window: int = 1, flags: int = 128) -> bytes:
    """Step: open a dialogue/narration window showing ``text_id`` (blocks until the player dismisses)."""
    return opcodes.window_sync(window, flags, text_id)


def wait(frames: int) -> bytes:
    """Step: pause for ``frames`` frames."""
    return opcodes.wait(frames)


def set_flag(idx: int, value: int = 1, *, flag_class=CUTSCENE_FLAG_CLASS) -> bytes:
    """Step: set a GlobBool story flag (advance/record state from within the scene)."""
    return _region.set_var(flag_class, idx, value)


def build_body(steps, once_flag: int | None, flag_class=CUTSCENE_FLAG_CLASS) -> bytes:
    """The cutscene function body: ``DisableMove`` + the ordered ``steps`` + ``EnableMove``, all gated
    ``if (!once_flag) { ...; once_flag = 1 }`` when ``once_flag`` is set (so it plays once)."""
    inner = opcodes.DISABLE_MOVE + b"".join(steps) + opcodes.ENABLE_MOVE
    if once_flag is not None:
        inner += _region.set_var(flag_class, once_flag, 1)
        return _region.if_block(_region.cond_not(flag_class, once_flag), inner) + opcodes.RETURN
    return inner + opcodes.RETURN


def inject_cutscene(data, steps, *, once_flag: int | None = None, flag_class=CUTSCENE_FLAG_CLASS,
                    spawn_wait_n: int = 2, spawn_wait_occurrence: int = 0) -> bytes:
    """Append a cutscene code entry (the sequence in :func:`build_body`) and run it on field load via
    an ``InitCode`` (over a Wait filler, or inserted into Main_Init). Returns new .eb bytes."""
    body = build_body(steps, once_flag, flag_class)
    entry = bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + body
    slot = EbScript.from_bytes(data).first_free_slot()
    out = edit.append_entry(data, slot, entry)
    return edit.activate(out, opcodes.init_code(slot, 0), spawn_wait_n=spawn_wait_n,
                         spawn_wait_occurrence=spawn_wait_occurrence)
