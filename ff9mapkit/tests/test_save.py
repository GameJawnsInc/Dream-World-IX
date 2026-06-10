"""Tests for the FF9 save codec (ff9mapkit.save) -- the RECREATE verb. Synthetic saves only (no real
game data): we build a save block exactly as the engine does and assert the read/edit/round-trip."""
import base64

import pytest

pytest.importorskip("Crypto")        # the save codec needs pycryptodome; skip cleanly if absent

from ff9mapkit import save as S       # noqa: E402


def _geg(sc, bits=()):
    g = bytearray(2048)
    g[0], g[1] = sc & 0xFF, sc >> 8 & 0xFF
    for b in bits:
        g[b >> 3] |= 1 << (b & 7)
    return bytes(g)


def _make_save(geg_by_block):
    """A synthetic SavedData_ww.dat: header region + one 18432-byte AES block per entry, each a
    'SAVE' magic + the gEventGlobal Base64 at offset 23 (the real layout)."""
    from Crypto.Cipher import AES
    key, iv = S._key_iv()
    nblocks = max(geg_by_block) + 1
    data = bytearray(S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE * nblocks)
    for n, geg in geg_by_block.items():
        pt = bytearray(S.SAVE_BLOCK_SIZE)               # 18432, a multiple of 16 -> raw CBC, no padding
        pt[0:4] = b"SAVE"
        b64 = base64.b64encode(geg)
        pt[23:23 + len(b64)] = b64
        ct = AES.new(key, AES.MODE_CBC, iv).encrypt(bytes(pt))
        lo = S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE * n
        data[lo:lo + S.SAVE_BLOCK_SIZE] = ct
    return bytes(data)


def test_block_index_mapping():
    assert S.block_index(0, 0) == 1 and S.block_index(0, 1) == 2 and S.block_index(1, 0) == 16


def test_read_and_enumerate():
    sv = S.FF9Save(_make_save({1: _geg(7200, (8520,)), 2: _geg(2500)}))
    assert sv.gEventGlobal(1)[:2] == bytes([7200 & 0xFF, 7200 >> 8])
    assert (sv.gEventGlobal(1)[1065] >> 0) & 1 == 1                     # flag 8520 set
    pops = {p.block: (p.scenario, p.slot, p.save) for p in sv.populated()}
    assert pops == {1: (7200, 0, 0), 2: (2500, 0, 1)}                   # block 0 (zeros) is not a save


def test_unedited_block_round_trips_byte_identical():
    sv = S.FF9Save(_make_save({1: _geg(5000)}))
    before = bytes(sv.data)
    sv.set_gEventGlobal(1, sv.gEventGlobal(1))                          # re-write the same bytes
    assert bytes(sv.data) == before                                    # AES-CBC bijection -> no change


def test_edit_isolates_to_target_block():
    sv = S.FF9Save(_make_save({1: _geg(7200), 2: _geg(2500)}))
    orig = bytes(sv.data)
    geg = bytearray(sv.gEventGlobal(1))
    notes = S.edit_story_state(geg, scenario=2530, set_flags=(8530,))
    sv.set_gEventGlobal(1, bytes(geg))
    assert sv.gEventGlobal(1)[:2] == bytes([2530 & 0xFF, 2530 >> 8])
    assert (sv.gEventGlobal(1)[8530 >> 3] >> (8530 & 7)) & 1 == 1
    assert any("2530" in n for n in notes)
    lo = S.BASE_SAVE_BLOCK_OFFSET + S.SAVE_BLOCK_SIZE                   # block 1 span
    hi = lo + S.SAVE_BLOCK_SIZE
    assert sv.data[:lo] == orig[:lo] and sv.data[hi:] == orig[hi:]     # everything else untouched (incl. block 2)


def test_edit_story_state_guards():
    g = bytearray(2048)
    with pytest.raises(ValueError, match="reserved"):
        S.edit_story_state(g, set_flags=(8400,))                       # chest band -> refused
    with pytest.raises(ValueError, match="out of range"):
        S.edit_story_state(g, scenario=70000)
    with pytest.raises(ValueError, match="out of range"):
        S.edit_story_state(g, set_flags=(99999,))


def test_extra_file_path():
    main = "/x/y/SavedData_ww.dat"
    assert S.extra_file_path(main, 0).endswith("SavedData_ww_Memoria_Autosave.dat")   # autosave
    assert S.extra_file_path(main, 3).endswith("SavedData_ww_Memoria_0_2.dat")          # slot 0 save 2
    assert S.extra_file_path(main, 16).endswith("SavedData_ww_Memoria_1_0.dat")         # slot 1 save 0
    assert S.extra_file_path("not-a-dat.txt", 1) is None


def test_extra_file_read_and_patch(tmp_path):
    # a synthetic (unencrypted) Memoria extra file: binary bytes around the gEventGlobal Base64 (null
    # separators, like the real file -- abutting ASCII would merge into the base64 run)
    p = tmp_path / "s_Memoria_0_2.dat"
    p.write_bytes(b"\x02\x00\x00\x00key\x00" + base64.b64encode(_geg(0)) + b"\x00\x00tail")
    assert S.read_extra_gEventGlobal(str(p))[:2] == b"\x00\x00"                          # SC 0
    assert S.patch_extra_gEventGlobal(str(p), _geg(2500, (8520,))) is True
    got = S.read_extra_gEventGlobal(str(p))
    assert got[0] | got[1] << 8 == 2500 and (got[1065] >> 0) & 1 == 1                    # SC + flag took
    assert S.read_extra_gEventGlobal(str(tmp_path / "missing.dat")) is None              # absent file
    q = tmp_path / "no_geg.dat"
    q.write_bytes(b"no base64 of the right size here")
    assert S.patch_extra_gEventGlobal(str(q), _geg(1)) is False                          # nothing to patch


def test_write_roundtrips(tmp_path):
    sv = S.FF9Save(_make_save({1: _geg(6000)}))
    geg = bytearray(sv.gEventGlobal(1))
    S.edit_story_state(geg, scenario=2500)
    sv.set_gEventGlobal(1, bytes(geg))
    p = tmp_path / "out.dat"
    sv.write(p)
    assert S.FF9Save.load(p).gEventGlobal(1)[:2] == bytes([2500 & 0xFF, 2500 >> 8])
