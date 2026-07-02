"""discmr.img codec (world/worldpack.py) -- parse sector-TOC -> pointer-pack -> EncountData(355) + special(9),
in-place edits, round-trip identity, and the mod-override deploy path.

Hermetic core builds a synthetic discmr (a valid TOC + pack + tables) so the parse / edit / serialize / deploy
logic is pinned without the install. Game-gated: the real discmr.img (both discs) round-trips and carries 355
non-zero records + 9 special rows.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import config
from ff9mapkit.world import worldpack as WP


def _synth_discmr(records=None, specials=None, *, container="assets/resources/worldmap/wmap/disc1/discmr.img.bytes"):
    """A minimal valid discmr.img: sector-0 TOC (record[1] -> the pack at byte 2048), then a pointer-table pack
    with sub-tables 3 (355 EncountData) and 4 (9 special). `records` = list of (scene[4], pattern, pad)."""
    if records is None:
        records = [([i, (i + 1000) & 0xFFFF, (i + 2000) & 0xFFFF, (i + 3000) & 0xFFFF], (i % 40) << 2, i % 2)
                   for i in range(WP.ENCOUNT_COUNT)]
    if specials is None:
        specials = [[(i * 12 + j + 1) if j < 3 else WP.SPECIAL_EMPTY for j in range(12)]
                    for i in range(WP.SPECIAL_COUNT)]
    enc = b"".join(struct.pack("<4HBB", *(s & 0xFFFF for s in sc), pat & 0xFF, pad & 0xFF) for sc, pat, pad in records)
    spc = b"".join(struct.pack("<12H", *(a & 0xFFFF for a in area)) for area in specials)
    count = 5                                                   # offs[0..5]; sub-tables 3=enc, 4=special
    header_len = 4 + (count + 1) * 4
    off_enc = header_len
    off_spc = off_enc + len(enc)
    off_end = off_spc + len(spc)
    offs = [header_len, header_len, header_len, off_enc, off_spc, off_end]
    pack = struct.pack("<I", count) + b"".join(struct.pack("<I", o) for o in offs) + enc + spc
    length_sectors = (len(pack) + WP.SECTOR - 1) // WP.SECTOR
    toc = bytearray(WP.SECTOR)
    struct.pack_into("<ii", toc, WP.PACK_SECTION * 8, 1, length_sectors)   # record[1]: start sector 1, N sectors
    body = bytes(toc) + pack + bytes(length_sectors * WP.SECTOR - len(pack))
    return body, container


# --------------------------------------------------------------------------- parse + round-trip (hermetic)

def test_parse_reads_the_tables():
    data, _ = _synth_discmr()
    d = WP.Discmr.from_bytes(data)
    assert len(d.encounters) == WP.ENCOUNT_COUNT and len(d.specials) == WP.SPECIAL_COUNT
    assert d.pack_off == WP.SECTOR                             # pack at sector 1
    r5 = d.encounters[5]
    assert r5.scene == [5, 1005, 2005, 3005] and r5.topograph == 5 and r5.fog == 1
    assert d.specials[0][:3] == [1, 2, 3] and d.specials[0][3] == WP.SPECIAL_EMPTY


def test_round_trip_identity():
    data, _ = _synth_discmr()
    assert WP.Discmr.from_bytes(data).to_bytes() == data       # unedited -> byte-identical


def test_set_encounter_touches_only_the_target_record():
    data, _ = _synth_discmr()
    d = WP.Discmr.from_bytes(data)
    before = d.to_bytes()
    d.set_encounter(4, scene=[111, 222, 333, 444], pattern=37 << 2, pad=0)
    after = d.to_bytes()
    base = d.enc_abs + 4 * WP.ENCOUNT_SIZE
    diff = [k for k in range(len(before)) if before[k] != after[k]]
    assert diff and all(base <= k < base + WP.ENCOUNT_SIZE for k in diff)   # only record 4's 10 bytes
    d2 = WP.Discmr.from_bytes(after)
    assert d2.encounters[4].scene == [111, 222, 333, 444] and d2.encounters[4].topograph == 37
    # scene as a {slot: id} dict sets just that slot
    d.set_encounter(4, scene={0: 777})
    assert d.encounters[4].scene == [777, 222, 333, 444]


def test_remap_and_match():
    data, _ = _synth_discmr()
    d = WP.Discmr.from_bytes(data)
    assert d.match(index=5) == [5]
    assert d.match(topograph=5) == [5, 45, 85, 125, 165, 205, 245, 285, 325]     # every 40th record
    assert d.match(topograph=5, fog=1) == [5, 45, 85, 125, 165, 205, 245, 285, 325]  # those are all fog=odd
    assert d.match(topograph=5, fog=0) == []
    n = d.remap_scene({5: 9999})                              # record 5 slot0 == 5
    assert n == 1 and d.encounters[5].scene[0] == 9999


def test_apply_config_set_and_remap():
    data, _ = _synth_discmr()
    d = WP.Discmr.from_bytes(data)
    summary = WP.apply_config(d, {"set": [{"topograph": 5, "scene": [1, 2, 3, 4]}], "remap": {"1000": 12345}})
    assert summary["sets"][0]["count"] == 9
    assert all(d.encounters[i].scene == [1, 2, 3, 4] for i in d.match(topograph=5))
    # remap ran AFTER the set; 1000 == record 0's scene[1] (topograph 0, untouched by the set) -> survives
    assert summary["remapped"] == 1 and d.encounters[0].scene[1] == 12345
    # `all = true` matches every record (the uniform-overworld / override-path test)
    d2 = WP.Discmr.from_bytes(data)
    s2 = WP.apply_config(d2, {"set": [{"all": True, "scene": [359, 359, 359, 359]}]})
    assert s2["sets"][0]["count"] == WP.ENCOUNT_COUNT
    assert all(r.scene == [359, 359, 359, 359] for r in d2.encounters)
    # a matcher-less or no-match set raises
    with pytest.raises(ValueError):
        WP.apply_config(d, {"set": [{"scene": [0, 0, 0, 0]}]})
    with pytest.raises(ValueError):
        WP.apply_config(d, {"set": [{"topograph": 99, "scene": [0, 0, 0, 0]}]})


def test_bad_image_is_rejected():
    with pytest.raises(ValueError):
        WP.Discmr.from_bytes(b"\x00" * 16)                    # too small


# --------------------------------------------------------------------------- deploy (hermetic)

def test_deploy_lands_at_the_mod_override_path(tmp_path, monkeypatch):
    data, container = _synth_discmr()
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    d = WP.Discmr.from_bytes(data, container=container, disc=1)
    d.set_encounter(0, scene=[9, 9, 9, 9])
    dest = WP.deploy_discmr(d, mod_folder="FF9CustomMap")
    assert dest == (tmp_path / "FF9CustomMap" / "StreamingAssets" / container).resolve()
    assert dest.is_file()
    # the override re-reads with the edit and is otherwise byte-identical to the edited image
    assert dest.read_bytes() == d.to_bytes()
    assert WP.Discmr.from_bytes(dest.read_bytes()).encounters[0].scene == [9, 9, 9, 9]


# --------------------------------------------------------------------------- real discmr.img (game-gated)

def _game_ready() -> bool:
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
@pytest.mark.parametrize("disc", [1, 4])
def test_real_discmr_round_trips_and_is_populated(disc):
    d = WP.load_discmr(disc)
    raw = d.to_bytes()
    assert WP.Discmr.from_bytes(raw).to_bytes() == raw        # round-trip identity on the real asset
    assert len(d.encounters) == 355 and len(d.specials) == 9
    assert sum(1 for r in d.encounters if any(r.scene)) == 355   # every record has a battle scene
    assert d.container == f"assets/resources/worldmap/wmap/disc{disc}/discmr.img.bytes"
    # the fog twins: record 0 (clear) and 1 (mist) share a topograph
    assert d.encounters[0].topograph == d.encounters[1].topograph
    assert d.encounters[0].fog == 0 and d.encounters[1].fog == 1
