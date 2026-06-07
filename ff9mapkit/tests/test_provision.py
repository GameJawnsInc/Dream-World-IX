"""Provenance machinery: the copy/insert patch codec + its airtight invariant.

These run with NO game install (pure algorithm tests): they prove make_patch/apply_patch round-trip,
that apply rejects a wrong source, and -- the airtight guarantee -- that a patch never ships a run of
bytes that exists in the source (a game-byte run). The actual shipped patches are verified against the
real fields by the maintainer tool (ff9mapkit.data._regen_provenance) + the byte-level suite.
"""
from __future__ import annotations

import pytest

from ff9mapkit import provision


def test_patch_roundtrip_same_length():
    src = bytes(range(64)) * 4
    dst = bytearray(src)
    dst[10:13] = b"\xAA\xBB\xCC"          # a small in-place edit (our kind of change)
    dst = bytes(dst)
    patch = provision.make_patch(src, dst)
    assert provision.apply_patch(src, patch) == dst


def test_patch_roundtrip_slice():
    src = b"the quick brown fox jumps over the lazy dog" * 8
    dst = src[20:200] + b"\x99\x99"        # a slice + a novel tail (region-template shape)
    patch = provision.make_patch(src, dst)
    assert provision.apply_patch(src, patch) == dst


def test_patch_never_ships_game_runs():
    # dst is built mostly FROM src (a game-byte run) plus a novel edit; the patch must COPY the
    # src-derived run (reference it) and only INSERT the novel bytes -- never ship the src run.
    src = bytes(range(200))
    game_run = src[50:130]                 # an 80-byte run that exists in src
    dst = game_run + b"\x01\x02\x03 NOVEL EDIT \x04\x05"
    patch = provision.make_patch(src, dst)
    assert provision.apply_patch(src, patch) == dst
    assert provision.patch_game_runs(src, patch) == []          # no shipped run occurs in src
    shipped = b"".join(bytes.fromhex(op[1]) for op in patch["ops"] if op[0] == "i")
    assert game_run not in shipped                              # the game run was copied, not shipped


def test_apply_rejects_wrong_source():
    src = b"A" * 100
    patch = provision.make_patch(src, b"A" * 50 + b"Z" * 50)
    with pytest.raises(ValueError):
        provision.apply_patch(b"B" * 100, patch)               # different source -> hash mismatch


def test_missing_message_mentions_extract_templates():
    assert "extract-templates" in provision.MISSING_MSG
