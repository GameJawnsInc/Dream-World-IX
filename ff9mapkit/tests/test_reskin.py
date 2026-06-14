"""Pure (install-free) tests for the enemy RE-SKIN lever: transplant a real donor enemy's model+animation
block into a forked enemy, keeping that enemy's gameplay. The donor RESOLUTION (name->geo->scan / a donor
scene) needs the install and is golden-tested in test_battle_scene_codec.py; here we prove the byte-copy +
the toml-shape logic with synthetic scenes + injected donor blocks.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import reskin, scene_codec, scene_data
from ff9mapkit.battle.reskin import ReskinError, reskin_spec


def _raw2(geo0=100, geo1=200, hp0=111, hp1=222):
    """A 1-pattern / 2-type / 0-attack raw16 where the two types differ in BOTH model and gameplay fields, so
    a transplant from one into the other is observable on every axis."""
    head = bytes([1, 1, 2, 0]) + struct.pack("<H", 0) + b"\x00\x00"      # ver,1 pat,2 typ,0 atk
    pat = bytes([10, 2, 5, 0]) + struct.pack("<I", 0)                    # rate,count=2,cam,pad0, AP
    for slot in range(4):
        pat += bytes([slot % 2, 1, 0, 0]) + struct.pack("<hhhh", 0, 0, 0, 0)   # type=slot%2, targetable
    mons = b""
    for t, (geo, hp) in enumerate([(geo0, hp0), (geo1, hp1)]):
        m = bytearray(116)
        struct.pack_into("<H", m, 12, hp)                                # GAMEPLAY: MaxHP
        m[64] = 10 + t                                                   # GAMEPLAY: Level
        m[63] = 0x01 + t                                                 # GAMEPLAY: WeakElement
        struct.pack_into("<H", m, 28, 40 + t)                           # MODEL: Radius
        struct.pack_into("<h", m, 30, geo)                              # MODEL: Geo
        for i in range(6):
            struct.pack_into("<H", m, 32 + 2 * i, (t + 1) * 100 + i)    # MODEL: Mot[6]
        struct.pack_into("<H", m, 44, (t + 1) * 7)                      # MODEL: Mesh[0]
        m[72] = t + 1                                                   # MODEL: Bone[0]
        struct.pack_into("<H", m, 98, (t + 1) * 9)                      # MODEL: StartSfx
        m[105] = 50 + t                                                 # GAMEPLAY: WinCard (NOT copied)
        mons += bytes(m)
    return head + pat + mons


def test_reskin_transplants_model_keeps_gameplay():
    raw = _raw2()
    donor = scene_data.mon_block(raw, 1)                                 # type 1 is the donor model
    out, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 0, "_reskin_block": donor}]})
    s = scene_codec.parse_scene(out)
    t0 = s.monsters[0]
    # model fields now match the donor (type 1)
    assert t0.geo == 200 and t0.radius == 41 and t0.mot == (200, 201, 202, 203, 204, 205)
    assert t0.mesh[0] == 14 and t0.bone[0] == 2 and t0.start_sfx == 18
    # gameplay fields unchanged (still type 0's)
    assert t0.hp == 111 and t0.level == 10 and t0.weak_element == 0x01 and t0.win_card == 50
    # valid scene; the donor source (type 1) is untouched
    assert scene_codec.serialize_scene(s) == out
    assert s.monsters[1].geo == 200 and s.monsters[1].hp == 222


def test_reskin_only_touches_model_ranges():
    raw = _raw2()
    donor = scene_data.mon_block(raw, 1)
    out, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 0, "_reskin_block": donor}]})
    mon0 = scene_data._mon_base(1)                                       # type-0 block start (patcount=1)
    changed = [i - mon0 for i in range(len(raw)) if raw[i] != out[i]]
    in_range = lambda o: any(off <= o < off + ln for off, ln in scene_data._RESKIN_RANGES)
    assert changed and all(0 <= d < 116 and in_range(d) for d in changed)   # ONLY model/display bytes moved


def test_reskin_with_stat_edit_on_same_slot():
    raw = _raw2()
    donor = scene_data.mon_block(raw, 1)
    out, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 0, "hp": 500, "_reskin_block": donor}]})
    t0 = scene_codec.parse_scene(out).monsters[0]
    assert t0.geo == 200 and t0.hp == 500                               # model from donor, hp from the edit


def test_mon_block_size_and_range():
    raw = _raw2()
    assert len(scene_data.mon_block(raw, 0)) == 116
    with pytest.raises(scene_data.SceneEditError):
        scene_data.mon_block(raw, 5)                                    # type out of range


def test_apply_reskin_block_rejects_bad_length():
    b = bytearray(_raw2())
    with pytest.raises(scene_data.SceneEditError):
        scene_data._apply_reskin_block(b, scene_data._mon_base(1), b"\x00" * 10)


# ---------------------------------------------------------------- toml-shape (reskin_spec) ---
def test_reskin_spec_forms():
    assert reskin_spec({"slot": 0}) is None
    assert reskin_spec({"slot": 0, "model": "Goblin"}) == {"name": "Goblin"}
    assert reskin_spec({"slot": 0, "model_scene": "EF_R007"}) == {"scene": "EF_R007", "type": 0}
    assert reskin_spec({"slot": 0, "model_scene": "EF_R007", "model_type": 2}) == {"scene": "EF_R007", "type": 2}


def test_reskin_spec_rejects_conflicts():
    with pytest.raises(ReskinError):
        reskin_spec({"slot": 0, "model": "X", "model_scene": "Y"})       # both forms
    with pytest.raises(ReskinError):
        reskin_spec({"slot": 0, "model": "X", "model_type": 1})          # model_type only with model_scene
    with pytest.raises(ReskinError):
        reskin_spec({"slot": 0, "model_type": 1})                        # model_type ALONE = a silent-typo trap


# ---------------------------------------------------------------- infra errors -> actionable ReskinError ---
def test_scene_donor_infra_error_is_actionable(monkeypatch):
    from ff9mapkit.battle import extract
    monkeypatch.setattr(extract, "read_scene_assets", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no install")))
    with pytest.raises(ReskinError) as ei:
        reskin.resolve_donor_block({"scene": "EF_R007", "type": 0})
    assert "--game" in str(ei.value) or "FF9_GAME_PATH" in str(ei.value)


def test_name_donor_infra_error_is_actionable(monkeypatch):
    monkeypatch.setattr(reskin, "_geo_for_name", lambda n: 7)
    monkeypatch.setattr(reskin, "_scan_for_geo", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no UnityPy")))
    with pytest.raises(ReskinError) as ei:
        reskin.resolve_donor_block({"name": "GEO_MON_B3_001"})
    assert "--game" in str(ei.value) or "UnityPy" in str(ei.value)


def test_resolve_reskins_emits_body_reskin_warning(monkeypatch):
    from ff9mapkit.battle import build as _build
    donor = scene_data.mon_block(_raw2(), 1)
    monkeypatch.setattr(reskin, "resolve_donor_block", lambda spec, game=None: (donor, "EF_R007 type 0"))
    out_cfg, warns = _build._resolve_reskins({"enemy": [{"slot": 0, "model_scene": "EF_R007"}]})
    assert out_cfg["enemy"][0]["_reskin_block"] == donor                 # block injected for apply_scene_edits
    assert warns and "stay the target enemy" in warns[0] and "idle AND attack" in warns[0]   # honest MESH-swap scope


# ---------------------------------------------------------------- name->geo (install-free catalog) ---
def test_geo_for_name_resolves_curated_creature():
    from ff9mapkit import archetypes, catalog
    name = sorted(archetypes.CREATURES)[0]                              # any curated creature -> its GEO id
    assert reskin._geo_for_name(name) == catalog.model(archetypes.CREATURES[name]["model"]).id


def test_geo_for_name_unknown_is_none():
    assert reskin._geo_for_name("totally-not-a-model-xyz") is None
