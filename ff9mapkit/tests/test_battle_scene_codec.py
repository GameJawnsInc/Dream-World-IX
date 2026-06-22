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


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_battle_text_faithful_per_language():
    # the FULLY-FAITHFUL read: each language's <id>.mes resolved by its real EmbeddedAsset/Text/<lang>/Battle/<id>
    # resource path (the ResourceManager index), not a content heuristic -> every language is exact.
    from ff9mapkit.battle import extract
    from ff9mapkit.battle.extract import _has_cjk
    a = extract.read_scene_assets("EF_R007")
    mes = a["mes"]
    assert b"Goblin" in mes["us"] and b"Fang" in mes["us"]      # English
    assert b"Duende" in mes["es"]                               # Spanish (a content heuristic would miss this)
    assert b"Gobelin" in mes["fr"]                              # French
    assert b"Isegrim" in mes["gr"]                              # German
    assert _has_cjk(mes["jp"])                                  # Japanese
    assert a["mes_note"] is None                                # faithful -> no warning
    # the NAME-COLLIDED id (battle 74 also names a ~50 KB field-text block) now resolves the English BATTLE text
    z = extract.read_scene_assets("AC_E031")
    assert b"Zorn" in z["mes"]["us"] and b"Thorn" in z["mes"]["us"]
    assert z["mes_note"] is None and len(z["mes"]["us"]) < 4000   # battle text, NOT the field-text collision


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_donor_ai_facts_lists_entries_and_named_attacks():
    # the AI-phase readout helper: the scene's attack table (names resolved from the .mes) + the AI functions,
    # flagging the ai_phase-able ones (exactly one Attack). Reuses the disassembler + scene_codec.
    from ff9mapkit.battle import extract
    from ff9mapkit.workspace.battledoc import donor_ai_facts
    a = extract.read_scene_assets("EF_R007")
    facts = donor_ai_facts(a["eb"]["us"], a["raw16"], a["mes"]["us"])
    assert facts is not None
    attacks, ai_funcs = facts
    assert any("Knife" in str(nm) for _i, nm in attacks)         # attack names resolved from the .mes
    assert ai_funcs and any(n == 1 for *_h, n in ai_funcs)       # at least one enrage-able function (one Attack)


# ----------------------------------------------------------------- install-gated: camera codec on a real donor
@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
@pytest.mark.parametrize("donor", ["EF_R007"])
def test_camera_codec_golden_roundtrip_real_donor(donor):
    """The raw17 opening-camera codec (``camera_codec.parse_block`` <-> ``serialize_block`` /
    ``splice_block``), asserted against a REAL donor raw17 -- the camera-codec analog of the raw16 golden
    above. The synthetic test (``test_camera_codec_roundtrip`` in test_battle.py) only proves the offset
    repack on a hand-built block; THIS proves the parse is truly lossless (every camera's flag-keyed
    sub-blocks, the set-offset table, any abort/empty cameras) on actual Square-Enix bytes. Closes the
    'tested only on SYNTHETIC raw17' gap (docs/BATTLE_DESIGN.md)."""
    from ff9mapkit.battle import camera_codec, extract
    try:
        raw17 = extract.read_scene_assets(donor)["raw17"]
    except (ValueError, KeyError, FileNotFoundError) as ex:
        pytest.skip(f"donor {donor} not readable: {ex}")
    cam_off, cams = camera_codec.parse_block(raw17)
    # THE golden assertions: the parsed camera block re-serializes byte-identically to the donor's [camOffset:],
    # and the production splice path reproduces the WHOLE raw17 file.
    assert camera_codec.serialize_block(cams) == raw17[cam_off:]
    assert camera_codec.splice_block(raw17, cams) == raw17
    # and the parse is structurally sane (>= 1 camera; at least one carries an opening sequence)
    assert len(cams) >= 1
    assert any(cam["sequences"] for cam in cams)


# ----------------------------------------------------------------- install-gated: enemy re-skin transplant
@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_reskin_scan_finds_real_enemy_by_geo():
    """The name-form donor scan against REAL bytes: a geo that an EF_R007 enemy uses is found by
    ``_scan_for_geo`` (so ``model = \"<name>\"`` always transplants a real, shipped block)."""
    from ff9mapkit.battle import extract, reskin
    raw16 = extract.read_scene_assets("EF_R007")["raw16"]
    geo = scene_codec.parse_scene(raw16).monsters[0].geo
    found = reskin._scan_for_geo(geo)
    assert found is not None, f"no battle enemy uses geo {geo}?"
    _scene_name, t, donor_raw16 = found
    assert scene_codec.parse_scene(donor_raw16).monsters[t].geo == geo


@pytest.mark.skipif(not _can_read_donor(), reason="needs the FF9 install + UnityPy (p0data2.bin)")
def test_reskin_transplant_real_donor():
    """End-to-end on real bytes: transplant another scene's enemy model into EF_R007 type 0 -> the model+anim
    fields come from the donor, the gameplay fields stay EF_R007's, and the result is a valid scene."""
    from ff9mapkit.battle import extract, reskin, scene_data
    base = scene_codec.parse_scene(extract.read_scene_assets("EF_R007")["raw16"])
    raw16 = extract.read_scene_assets("EF_R007")["raw16"]
    donor_scene = next(n for n in extract.list_battle_scenes() if n != "EF_R007")
    donor_block, _prov = reskin.resolve_donor_block({"scene": donor_scene, "type": 0})
    donor_mon = scene_codec.parse_scene(extract.read_scene_assets(donor_scene)["raw16"]).monsters[0]
    out, _w = scene_data.apply_scene_edits(raw16, {"enemy": [{"slot": 0, "_reskin_block": donor_block}]})
    res = scene_codec.parse_scene(out)
    t0, base0 = res.monsters[0], base.monsters[0]
    # model + animation transplanted from the donor
    assert (t0.geo, t0.mot, t0.mesh, t0.radius) == (donor_mon.geo, donor_mon.mot, donor_mon.mesh, donor_mon.radius)
    # gameplay kept from EF_R007 (NOT the donor's)
    assert (t0.hp, t0.level, t0.weak_element, t0.win_card) == (base0.hp, base0.level, base0.weak_element, base0.win_card)
    assert scene_codec.serialize_scene(res) == out          # still a valid, round-tripping scene
