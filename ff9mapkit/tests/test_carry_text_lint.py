"""#5 (FORK_FIDELITY.md): a carried TALKABLE object whose donor dialogue isn't carried renders WRONG/missing
text in the fork. lint_logic flags it -- build-side, by decoding the [[object]] verbatim entry's talk windows
and checking them against the [carry_text] plan. (The dangling-PLAYER-tag softlock half of #5 is already a
build-blocking validate() problem; this covers the un-carried-text half.)
"""
from __future__ import annotations

import struct

from ff9mapkit.build import FieldProject, lint_logic, _entry_window_txids
from ff9mapkit.eb import opcodes

BASE = """
[field]
id = 4003
name = "FORKROOM"
area = 11
text_block = 187

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


def _object_entry(talk_txid: int, *, talkable: bool = True) -> bytes:
    """A minimal verbatim object entry: tag-0 Init (return) + (optionally) tag-3 talk (WindowSync + return).
    Mirrors the on-disk layout build grafts: [type][func_count][(tag, fpos) table][bodies], fpos relative
    to entryStart+2."""
    funcs = [(0, opcodes.RETURN)]
    if talkable:
        funcs.append((3, opcodes.window_sync(1, 128, talk_txid) + opcodes.RETURN))
    fc = len(funcs)
    table, bodies, pos = b"", b"", fc * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, pos)
        pos += len(body)
        bodies += body
    return bytes([8, fc]) + table + bodies


def test_entry_window_txids_decodes_talk_windows():
    e = _object_entry(540)
    assert _entry_window_txids(e) == {540}                          # the tag-3 talk window
    assert _entry_window_txids(_object_entry(540, talkable=False)) == set()   # a prop: no talk window
    assert _entry_window_txids(e, carry_tags=[0]) == set()          # tag 3 DROPPED (init_only) -> not counted
    assert _entry_window_txids(e, carry_tags=[0, 3]) == {540}       # tag 3 kept -> counted


def _proj(tmp_path, obj_block: str, entry: bytes):
    (tmp_path / "obj.bin").write_bytes(entry)
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + obj_block, encoding="utf-8")
    return FieldProject.load(p)


def test_carried_talkable_without_text_carry_warns(tmp_path):
    proj = _proj(tmp_path, '\n[[object]]\nbin = "obj.bin"\nkind = "npc"\ndonor_idx = 0\n', _object_entry(540))
    assert any("obj.bin" in w and "540" in w and "carry-text" in w.lower() for w in lint_logic(proj))


def test_prop_object_does_not_warn(tmp_path):
    proj = _proj(tmp_path, '\n[[object]]\nbin = "obj.bin"\nkind = "prop"\ndonor_idx = 0\n',
                 _object_entry(540, talkable=False))
    assert not any("WRONG/missing" in w for w in lint_logic(proj))


def test_init_only_dropped_talk_tag_does_not_warn(tmp_path):
    # an init_only object whose tag 3 is dropped (carry_tags = [0]) -> the talk window never runs in the fork
    proj = _proj(tmp_path, '\n[[object]]\nbin = "obj.bin"\nkind = "npc"\ndonor_idx = 0\ncarry_tags = [0]\n',
                 _object_entry(540))
    assert not any("WRONG/missing" in w for w in lint_logic(proj))


def test_no_object_blocks_no_warning(tmp_path):
    # a plain authored field (no carried objects) is unaffected
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + '\n[[npc]]\nname = "Bob"\narchetype = "moogle"\npos = [0, -300]\ndialogue = "Hi."\n',
                 encoding="utf-8")
    assert not any("WRONG/missing" in w for w in lint_logic(FieldProject.load(p)))
