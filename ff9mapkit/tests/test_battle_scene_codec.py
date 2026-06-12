"""Tests for the full BTL_SCENE raw16 codec (battle.scene_codec).

PURE tier: a synthetic raw16 (patterns + monsters + attacks + a non-zero tail) round-trips byte-exact and
the named fields decode. INSTALL-GATED: the golden round-trip on a REAL donor scene read live from the
install via UnityPy -- ``serialize(parse(real)) == real`` PROVES the offset map (incl. the engine-ignored
tail) against actual Square-Enix bytes.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import scene_codec


def _synthetic(patcount=2, typcount=2, atkcount=2, tail=b"\x00\x00\x00\x07\x2a"):
    """A hand-built raw16: header (flags=2 back-attack, non-zero pad) + patterns + monsters + attacks + tail."""
    head = bytes([1, patcount, typcount, atkcount]) + struct.pack("<H", 2) + b"\xab\xcd"
    pats = b""
    for p in range(patcount):
        pat = bytes([10, 2, 5, 0]) + struct.pack("<I", 50 + p)            # rate,count,camera,pad0, AP
        for slot in range(4):
            pat += bytes([slot % typcount, 1, 0, 0]) + struct.pack("<hhhh", slot * 100, slot * 7, slot * -50, slot * 3)
        pats += pat
    mons = b""
    for t in range(typcount):
        m = bytearray(116)
        struct.pack_into("<I", m, 0, (1 << 8) | (1 << 0))                 # ResistStatus = Death|Petrify
        struct.pack_into("<H", m, 12, 100 + t)                           # MaxHP
        struct.pack_into("<H", m, 16, 88)                                # WinGil
        m[60] = 0x02                                                     # GuardElement = Ice
        m[63] = 0x01                                                     # WeakElement = Fire
        m[64] = 5 + t                                                    # Level
        m[67] = 10                                                       # PhysicalDefence
        m[105] = 7                                                       # WinCard
        mons += bytes(m)
    atks = b""
    for a in range(atkcount):
        # info, scriptId, power, elements, rate, category, addStatus, mp, type, vfx2, name
        atks += struct.pack("<I8B2H", 0x12345678, 19, 30 + a, 1, 100, 8, 5, 6, 7, 0xabcd, 0x0010)
    return head + pats + mons + atks + tail


def test_codec_roundtrips_synthetic():
    raw = _synthetic()
    scene = scene_codec.parse_scene(raw)
    assert scene_codec.serialize_scene(scene) == raw            # byte-exact, INCLUDING the tail
    assert (scene.pat_count, scene.typ_count, scene.atk_count) == (2, 2, 2)
    assert scene.tail == b"\x00\x00\x00\x07\x2a"
    assert scene.back_attack is True and scene.can_escape is True and scene.no_exp is False


def test_codec_reads_named_fields():
    scene = scene_codec.parse_scene(_synthetic())
    m0 = scene.monsters[0]
    assert m0.hp == 100 and m0.gil == 88 and m0.level == 5 and m0.phys_def == 10 and m0.win_card == 7
    assert m0.weak_element == 0x01 and m0.guard_element == 0x02       # @63 Fire / @60 Ice
    assert m0.resist_status == (1 << 8) | (1 << 0)                    # @0 Death|Petrify
    assert scene.monsters[1].hp == 101 and scene.monsters[1].level == 6
    # pattern + put
    assert scene.patterns[0].ap == 50 and scene.patterns[1].ap == 51
    assert scene.patterns[0].puts[1].type_no == 1 and scene.patterns[0].puts[1].targetable
    # attack table
    a0 = scene.attacks[0]
    assert a0.script_id == 19 and a0.power == 30 and a0.elements == 1 and a0.rate == 100
    assert a0.category == 8 and a0.add_status == 5 and a0.mp == 6 and a0.type == 7


def test_codec_roundtrips_no_attacks_no_tail():
    raw = _synthetic(patcount=1, typcount=1, atkcount=0, tail=b"")
    assert scene_codec.serialize_scene(scene_codec.parse_scene(raw)) == raw
    assert scene_codec.parse_scene(raw).attacks == []


def test_codec_rejects_truncated():
    with pytest.raises(scene_codec.SceneCodecError):
        scene_codec.parse_scene(b"\x01\x02\x02\x00\x00\x00\x00\x00")    # claims 2 patterns, no body


def test_codec_edit_then_serialize_is_surgical():
    # the codec can also drive a structured edit: bump an enemy's weakness, re-emit -> only that byte changes
    raw = _synthetic()
    scene = scene_codec.parse_scene(raw)
    scene.monsters[0].weak_element = 0x05                              # Fire|Thunder
    out = scene_codec.serialize_scene(scene)
    diff = [i for i in range(len(raw)) if raw[i] != out[i]]
    mon0 = 8 + 56 * 2 + 0                                             # type-0 block start (patcount=2)
    assert diff == [mon0 + 63]                                        # ONLY the WeakElement byte changed


# ----------------------------------------------------------------- install-gated golden round-trip
def _can_read_donor() -> bool:
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path() / "StreamingAssets" / "p0data2.bin").is_file()
    except Exception:
        return False


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
@pytest.mark.parametrize("donor", ["EF_R007"])
def test_golden_roundtrip_real_donor(donor):
    from ff9mapkit.battle import extract
    try:
        raw16 = extract.read_scene_assets(donor)["raw16"]
    except (ValueError, KeyError, FileNotFoundError) as ex:
        pytest.skip(f"donor {donor} not readable: {ex}")
    scene = scene_codec.parse_scene(raw16)
    # THE golden assertion: a full parse -> re-serialize is byte-identical to the real donor (tail included)
    assert scene_codec.serialize_scene(scene) == raw16
    # and the real enemies parse to sane values (every type has HP, a level, a model)
    assert scene.typ_count >= 1
    assert all(m.hp > 0 and m.level > 0 and m.geo != 0 for m in scene.monsters)
    assert len(scene.attacks) == scene.atk_count
