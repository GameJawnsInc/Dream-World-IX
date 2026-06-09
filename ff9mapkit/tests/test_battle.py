"""Pure (no game install) tests for the battle-map pillar: ASCII-FBX emit + battle.toml validate.

These are in the PURE tier (NOT in conftest._NEEDS_GAME_DATA) -- they build synthetic geometry and a
temp battle.toml, so they run on a fresh clone without UnityPy or the FF9 install.
"""
from __future__ import annotations

import textwrap

import struct

from ff9mapkit.battle import fbx
from ff9mapkit.battle import scene_data
from ff9mapkit.battle.build import (BattleProject, _author_inb, _bbg_number, build_battle_mod,
                                    validate_battle)
from ff9mapkit.config import LANGS, ModLayout


def _groups():
    return [
        {"name": "Group_2", "verts": [[-1, 0, -1], [1, 0, -1], [1, 0, 1], [-1, 0, 1]],
         "normals": [[0, 1, 0]] * 4, "uvs": [[0, 0], [1, 0], [1, 1], [0, 1]],
         "submeshes": [{"texture": "image6", "tris": [[0, 1, 2], [0, 2, 3]]}]},
        {"name": "Group_0", "verts": [[0, 0, 0], [0, 10, 0], [5, 0, 0]],
         "normals": None, "uvs": [[0, 0], [0, 1], [1, 0]],
         "submeshes": [{"texture": "image0", "tris": [[0, 1, 2]]},
                       {"texture": "image1", "tris": [[2, 1, 0]]}]},
    ]


def test_emit_fbx_structure():
    text, ngeo = fbx.emit_fbx(_groups())
    assert ngeo == 3                                      # Group_2 (1) + Group_0 (2 submeshes)
    assert text.count("Geometry::Group_2") == 1
    assert text.count("Geometry::Group_0") == 2
    assert 'ShadingModel: "PSX/BattleMap_Ground"' in text   # Group_2 -> GROUND
    assert 'ShadingModel: "PSX/BattleMap_Plus"' in text     # Group_0 -> PLUS
    assert 'RelativeFilename: "image6.png"' in text
    assert 'RelativeFilename: "image1.png"' in text
    assert text.count('C: "OO"') == ngeo * 2                # geo->model + material->model
    assert text.count('C: "OP"') == ngeo                    # texture->material
    # FBX polygon-end convention: Group_2 tris [0,1,2],[0,2,3] -> 0,1,-3,0,2,-4
    assert "0,1,-3,0,2,-4" in text
    # every Model is typed "Mesh" (so FbxSkeleton doesn't treat it as a bone)
    assert text.count('Model::') == ngeo
    assert 'LimbNode' not in text and 'Root' not in text


def test_emit_fbx_no_normals_omits_normal_layer():
    g = [{"name": "Group_2", "verts": [[0, 0, 0], [1, 0, 0], [0, 0, 1]], "normals": None,
          "uvs": [[0, 0], [1, 0], [0, 1]], "submeshes": [{"texture": "image0", "tris": [[0, 1, 2]]}]}]
    text, _ = fbx.emit_fbx(g)
    assert "LayerElementNormal" not in text
    assert "LayerElementUV" in text


def test_textures_used():
    assert fbx.textures_used(_groups()) == ["image0", "image1", "image6"]


def test_validate_groups_catches_bad_index_and_uv_mismatch():
    bad = [{"name": "Group_2", "verts": [[0, 0, 0], [1, 0, 0]], "normals": None,
            "uvs": [[0, 0]],  # uv count != vert count
            "submeshes": [{"texture": "image0", "tris": [[0, 1, 5]]}]}]  # index 5 out of range
    probs = fbx.validate_groups(bad)
    assert any("uvs count" in p for p in probs)
    assert any("out of range" in p for p in probs)


def test_validate_groups_flags_unknown_group_name():
    g = [{"name": "Group_9", "verts": [[0, 0, 0]], "normals": None, "uvs": [[0, 0]],
          "submeshes": [{"texture": "image0", "tris": []}]}]
    assert any("Group_0/2/4/8" in p for p in fbx.validate_groups(g))


def _write_project(tmp_path, body):
    (tmp_path / "BBG_B013.fbx").write_text("; fbx\n", encoding="ascii")
    (tmp_path / "battle.toml").write_text(textwrap.dedent(body), encoding="utf-8")
    return BattleProject.load(tmp_path / "battle.toml")


def test_battle_project_load_and_validate(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
        fbx = "BBG_B013.fbx"
    ''')
    assert proj.bbg == "BBG_B013"
    assert validate_battle(proj) == []


def test_validate_battle_flags_bad_bbg_and_missing_fbx(tmp_path):
    (tmp_path / "battle.toml").write_text(textwrap.dedent('''
        [battlemap]
        bbg = "nope"
        fbx = "missing.fbx"
    '''), encoding="utf-8")
    probs = validate_battle(BattleProject.load(tmp_path / "battle.toml"))
    assert any("BBG_" in p for p in probs)
    assert any("fbx not found" in p for p in probs)


def test_validate_battle_rejects_both_mint_and_repoint(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
        scene_id = 5000
        scene_name = "X"
        repoint_scene = 67
    ''')
    assert any("only ONE" in p for p in validate_battle(proj))


def test_build_override_copies_fbx_no_patch_lines(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
    ''')
    (tmp_path / "image6.png").write_bytes(b"\x89PNG\r\n")  # a stand-in texture next to the toml
    out = tmp_path / "dist"
    info = build_battle_mod([proj], out)
    layout = ModLayout(out)
    assert (layout.battlemap_dir("BBG_B013") / "BBG_B013.fbx").is_file()
    assert (layout.battlemap_dir("BBG_B013") / "image6.png").is_file()
    assert info["dictionary"] == [] and info["battle_patch"] == []   # pure override -> no registration


def test_build_repoint_writes_battlepatch(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
        repoint_scene = 67
    ''')
    info = build_battle_mod([proj], tmp_path / "dist")
    assert "Battle: 67" in info["battle_patch"]
    assert "BattleBackground BBG_B013" in info["battle_patch"]


def _write_scene(tmp_path):
    """Synthetic forked-scene dir (what `battle-import --fork-scene` produces): raw16/raw17 + eb/mes x7."""
    sd = tmp_path / "scene"
    (sd / "eb").mkdir(parents=True, exist_ok=True)
    (sd / "mes").mkdir(parents=True, exist_ok=True)
    (sd / "dbfile0000.raw16.bytes").write_bytes(b"RAW16")
    (sd / "btlseq.raw17.bytes").write_bytes(b"RAW17")
    for lang in LANGS:
        (sd / "eb" / f"{lang}.eb.bytes").write_bytes(b"EB_" + lang.encode())
        (sd / "mes" / f"{lang}.mes").write_bytes(b"MES_" + lang.encode())


def test_author_inb_static_and_bbg_number():
    assert _bbg_number("BBG_B200") == 200 and _bbg_number("BBG_B013") == 13
    inb = _author_inb("BBG_B200", (10, 20, 30), 32)
    f = struct.unpack("<6h4B", inb)
    assert f[0] == 200                       # bbgnumber
    assert f[1:6] == (0, 0, 0, 0, 0)         # texanim/skyrot/fog/objanim/uvcount -> static
    assert f[6:] == (10, 20, 30, 32)         # char tint + shadow


def test_validate_battle_mint_requires_scene_assets(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B200"
        fbx = "BBG_B013.fbx"
        scene_id = 5502
        scene_name = "KIT_ARENA"
    ''')
    assert any("forked scene assets" in p for p in validate_battle(proj))


def test_build_mint_new_bbg_emits_full_scene_and_inb(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B200"
        fbx = "BBG_B013.fbx"
        scene_id = 5502
        scene_name = "KIT_ARENA"
    ''')
    _write_scene(tmp_path)
    out = tmp_path / "dist"
    info = build_battle_mod([proj], out)
    layout = ModLayout(out)
    assert "BattleScene 5502 KIT_ARENA BBG_B200" in info["dictionary"]
    assert not info["warnings"]                              # mint is real now, no "experimental" warning
    sd = layout.battle_scene_dir("KIT_ARENA")
    assert (sd / "dbfile0000.raw16.bytes").read_bytes() == b"RAW16"
    assert (sd / "5502.raw17.bytes").read_bytes() == b"RAW17"   # raw17 renamed to the scene id
    assert layout.battle_eb_path("us", "KIT_ARENA").read_bytes() == b"EB_us"
    assert (layout.battle_text_dir("us") / "5502.mes").read_bytes() == b"MES_us"
    inb = (layout.battle_info_dir / "INB_B200.inb.bytes").read_bytes()      # new number -> static INB authored
    assert struct.unpack_from("<h", inb, 0)[0] == 200


# --------------------------------------------------------------------- scene_data (tune the fight)
def _raw16(patcount=1, typcount=2):
    """A synthetic BTL_SCENE raw16: 1 pattern (Camera=5, slots 0/2 -> type 0, slot 1 -> type 1) + N
    monsters (MaxHP = 100+t). Matches the layout scene_data patches."""
    hdr = bytes([1, patcount, typcount, 0]) + struct.pack("<H", 0) + b"\x00\x00"
    pat = bytes([10, 2, 5, 0]) + struct.pack("<I", 100)
    for slot in range(4):
        typeno = 1 if slot == 1 else 0
        pat += bytes([typeno, 0, 0, 0]) + struct.pack("<hhhh", slot * 100, 0, slot * -50, 0)
    mons = b""
    for t in range(typcount):
        m = bytearray(116)                            # SB2_MON_PARM
        struct.pack_into("<H", m, 12, 100 + t)        # MaxHP
        mons += bytes(m)
    return hdr + pat + mons


def test_scene_edits_camera_position_stats_drops():
    raw = _raw16()
    scene = {"camera": 2, "enemy": [
        {"slot": 0, "pos": [500, -300], "rot": 64, "hp": 999, "level": 12,
         "drop": ["Potion", "none", "none", "none"]},
    ]}
    out, warns = scene_data.apply_scene_edits(raw, scene)
    assert not warns
    assert len(out) == len(raw)
    assert out[8 + 2] == 2                                      # pattern Camera byte
    put0 = 8 + 8 + 0                                            # slot 0 SB2_PUT
    assert struct.unpack_from("<h", out, put0 + 4)[0] == 500    # Xpos
    assert struct.unpack_from("<h", out, put0 + 8)[0] == -300   # Zpos
    assert struct.unpack_from("<h", out, put0 + 6)[0] == 0      # Ypos untouched (pos was [x,z])
    assert struct.unpack_from("<h", out, put0 + 10)[0] == 64    # Rot
    mon0 = 8 + 56 * 1                                           # type 0 monster block
    assert struct.unpack_from("<H", out, mon0 + 12)[0] == 999   # MaxHP
    assert out[mon0 + 64] == 12                                 # Level
    assert out[mon0 + 20] == 236                                # WinItems[0] = Potion
    assert out[mon0 + 21] == 255                                # "none" -> 255


def test_scene_edits_shared_type_warns():
    # slots 0 and 2 both map to type 0 -> editing both stats is the SAME monster data
    out, warns = scene_data.apply_scene_edits(_raw16(), {"enemy": [
        {"slot": 0, "hp": 200}, {"slot": 2, "hp": 300}]})
    assert any("share enemy type" in w for w in warns)
    assert struct.unpack_from("<H", out, 8 + 56 + 12)[0] == 300   # last write wins


def test_scene_edits_only_touch_edited_bytes():
    raw = _raw16()
    out, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 1, "hp": 4321}]})
    diff = [i for i in range(len(raw)) if raw[i] != out[i]]
    mon1 = 8 + 56 + 116                                         # type 1 block, MaxHP @ +12
    assert diff == [mon1 + 12, mon1 + 13]                       # ONLY the 2 HP bytes changed


def test_scene_validate_catches_bad_slot_pattern_item():
    raw = _raw16()
    assert any("slot" in p for p in scene_data.validate_scene(raw, {"enemy": [{"slot": 9, "hp": 1}]}))
    assert any("pattern" in p for p in scene_data.validate_scene(raw, {"pattern": 5, "enemy": []}))
    assert scene_data.validate_scene(raw, {"enemy": [{"slot": 0, "drop": ["Nope", "none", "none", "none"]}]})


def test_build_mint_existing_slot_reuses_bundle_inb(tmp_path):
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
        scene_id = 5503
        scene_name = "ON_B013"
    ''')
    _write_scene(tmp_path)
    out = tmp_path / "dist"
    info = build_battle_mod([proj], out)
    layout = ModLayout(out)
    assert "BattleScene 5503 ON_B013 BBG_B013" in info["dictionary"]
    # an existing real slot (<=177) keeps its bundled INB -> the kit does NOT shadow it with a static one
    assert not (layout.battle_info_dir / "INB_B013.inb.bytes").exists()
