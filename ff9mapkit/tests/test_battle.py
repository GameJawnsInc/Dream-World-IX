"""Pure (no game install) tests for the battle-map pillar: ASCII-FBX emit + battle.toml validate.

These are in the PURE tier (NOT in conftest._NEEDS_GAME_DATA) -- they build synthetic geometry and a
temp battle.toml, so they run on a fresh clone without UnityPy or the FF9 install.
"""
from __future__ import annotations

import textwrap

import struct

import pytest

from ff9mapkit.battle import camera_codec, camera_data, event_data, fbx, scene_data
from ff9mapkit.battle.build import (BattleProject, _author_inb, _bbg_number, build_battle_mod,
                                    validate_battle)
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.eb.model import EbScript


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
def _raw16(patcount=1, typcount=2, monster_count=2, put_flags=1):
    """A synthetic BTL_SCENE raw16: ``patcount`` identical patterns (Camera=5, slots 0/2 -> type 0, slot 1
    -> type 1) + N monsters (MaxHP = 100+t). `put_flags` is each SB2_PUT.Flags (1 = FLG_TARGETABLE)."""
    hdr = bytes([1, patcount, typcount, 0]) + struct.pack("<H", 0) + b"\x00\x00"
    pats = b""
    for _p in range(patcount):
        pat = bytes([10, monster_count, 5, 0]) + struct.pack("<I", 100)
        for slot in range(4):
            typeno = 1 if slot == 1 else 0
            pat += bytes([typeno, put_flags, 0, 0]) + struct.pack("<hhhh", slot * 100, slot * 7, slot * -50, 0)
        pats += pat
    mons = b""
    for t in range(typcount):
        m = bytearray(116)                            # SB2_MON_PARM
        struct.pack_into("<H", m, 12, 100 + t)        # MaxHP
        mons += bytes(m)
    return hdr + pats + mons


def _battle_eb(main_inits, n_ai=2):
    """A minimal EbScript-parseable battle eb: entry 0 = Main_Init (the given InitObjects + RETURN),
    entries 1..n_ai = per-type AI stubs (a single RETURN). ``main_inits`` = [(entry, uid), ...]."""
    def entry_body(funcs):                            # funcs = [(tag, code_bytes)]
        fc = len(funcs)
        table, code, off = b"", b"", fc * 4           # fpos measured from fbase (es+2); code after the table
        for tag, c in funcs:
            table += struct.pack("<HH", tag, off)
            off += len(c)
            code += c
        return bytes([2, fc]) + table + code          # type=2, funcCount, func-table, code
    mi = b"".join(bytes([0x09, e, u]) for e, u in main_inits) + bytes([0x04])   # InitObject* + RETURN
    bodies = [entry_body([(0, mi)])] + [entry_body([(0, bytes([0x04]))]) for _ in range(n_ai)]
    table = bytearray(80)                             # 10 slots x 8 bytes (offset is relative to byte 128)
    blob, off = b"", 80
    for i, body in enumerate(bodies):
        struct.pack_into("<HH", table, i * 8, off, len(body))
        blob += body
        off += len(body)
    header = bytearray(128)
    header[0:2] = b"EV"                               # .eb magic
    header[3] = len(bodies)                           # entry count
    return bytes(header) + bytes(table) + blob


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


def test_scene_spawn_count_and_type():
    # donor_max = 2 (synthetic). A SUPPORTED edit: keep count 2, retype slot 1 (Fang) -> type 0 (2 Goblins)
    out, _ = scene_data.apply_scene_edits(_raw16(), {
        "monster_count": 2, "enemy": [{"slot": 1, "type": 0, "pos": [10, 20]}]})
    assert out[8 + 1] == 2                                  # pattern MonsterCount
    put1 = 8 + 8 + 12 * 1
    assert out[put1] == 0                                   # slot 1 TypeNo retyped to 0
    assert out[put1 + 1] & 1                                # FLG_TARGETABLE set (normal attackable enemy)
    assert struct.unpack_from("<h", out, put1 + 6)[0] == 0  # grounded to slot 0's height


def test_scene_spawn_applies_to_all_patterns():
    # spawn composition (monster_count) re-composes a DETERMINISTIC fight across EVERY pattern
    raw = _raw16(patcount=2, monster_count=1)
    out, _ = scene_data.apply_scene_edits(raw, {
        "monster_count": 3, "enemy": [{"slot": 2, "type": 0, "pos": [10, 20]}]})
    for p in range(2):
        po = 8 + 56 * p
        assert out[po + 1] == 3                             # MonsterCount set on BOTH patterns
        assert out[po + 8 + 12 * 2] == 0                    # slot 2 retyped on BOTH patterns


def test_scene_spawn_no_donor_cap_only_engine_cap():
    # the donor-count cap is gone (build re-authors Main_Init); 4 is allowed, the engine cap is 1-4
    out, _ = scene_data.apply_scene_edits(_raw16(monster_count=1), {"monster_count": 4})
    assert out[8 + 1] == 4
    assert any("1-4" in p for p in scene_data.validate_scene(_raw16(), {"monster_count": 5}))


def test_rewrite_main_init_breaks_count():
    eb = _battle_eb([(2, 0x80)], n_ai=2)                    # donor: 1 InitObject (entry 2 = type-1 AI)
    assert event_data.main_init_initobject_count(eb) == 1
    out = event_data.rewrite_main_init(eb, [0, 0, 0, 0])    # -> 4 Goblins (type 0 -> entry 1)
    assert event_data.main_init_initobject_count(out) == 4
    eb2 = EbScript.from_bytes(out)
    assert not eb2.entry(1).empty and not eb2.entry(2).empty   # AI entries survive the relayout
    # mixed types map InitObject(1+type, 0x80+slot)
    ebm = EbScript.from_bytes(event_data.rewrite_main_init(eb, [1, 0]))
    inits = [(i.imm(0), i.imm(1)) for i in ebm.instrs(ebm.entry(0).func_by_tag(0)) if i.op == 0x09]
    assert inits == [(2, 0x80), (1, 0x81)]


def test_rewrite_main_init_missing_ai_entry_raises():
    eb = _battle_eb([(1, 0x80)], n_ai=1)                    # only entry 1 is an AI; type 1 would need entry 2
    with pytest.raises(ValueError):
        event_data.rewrite_main_init(eb, [1])


# --------------------------------------------------------------------- camera_data (in-place camera tweak)
def _raw17_cam(pitch=0x40, ori=0x10, dist=0x14):
    """A minimal raw17 with one camera, one sequence, one cameraPosition code."""
    b = bytearray(34)
    struct.pack_into("<h", b, 2, 16)        # camOffset (header's 2nd int16)
    struct.pack_into("<H", b, 16, 2)        # offset table: setOffset0=2 (firstSet=2 -> cameraCount=1)
    struct.pack_into("<H", b, 18, 1)        # cam0 Flags = HAS_SEQUENCE_0
    struct.pack_into("<H", b, 20, 4)        # seq0 offset (relative to cam base 18 -> seq at 22)
    struct.pack_into("<H", b, 22, 1)        # Code: frame = 1
    struct.pack_into("<H", b, 24, 1)        # CodeFlags = HAS_CAMERA_POSITION_BIT
    b[26:32] = bytes([0, 0, pitch, ori, 0, dist])          # cameraPosition: code,flags,pitch,ori,roll,dist
    struct.pack_into("<H", b, 32, 0)        # terminator frame = 0
    return bytes(b)


def test_camera_tweak_yaw_pitch_zoom():
    raw = _raw17_cam(pitch=0x40, ori=0x10, dist=0x14)
    out = camera_data.tweak_opening(raw, [0], yaw_deg=180, pitch_deg=45, zoom=2.0)
    assert len(out) == len(raw)                            # in place, no length change (no offset repack)
    assert out[29] == (0x10 + 0x20) % 0x40                 # yaw 180deg -> orientation +0x20
    assert out[28] == (0x40 + 0x10) % 0x80                 # pitch 45deg -> pitch +0x10
    assert out[31] == 0x14 * 2                             # zoom x2 -> distance doubled


def test_camera_opening_indices():
    assert camera_data.opening_indices(0) == [0]
    assert camera_data.opening_indices(2) == [2]
    assert camera_data.opening_indices(5) == [0, 1, 2]     # random (>=3)
    assert camera_data.opening_indices(None) == [0, 1, 2]  # unpinned


def test_camera_tweak_no_keyframes_raises():
    with pytest.raises(camera_data.CameraEditError):
        camera_data.tweak_opening(_raw17_cam(), [5], yaw_deg=90)   # camera index out of range


def test_camera_codec_roundtrip():
    raw = _raw17_cam(pitch=0x40, ori=0x10, dist=0x14)
    cam_off, cams = camera_codec.parse_block(raw)
    assert camera_codec.serialize_block(cams) == raw[cam_off:]     # byte-identical (offset repack correct)


def _raw17_opening(est_campos=bytes([0x15, 0x80, 0xF1, 0x20, 0x00, 0x0B])):
    """A donor raw17 shaped like a REAL opening: an establishing code (cameraPosition + targetPosition +
    focal) followed by the handoff (SAVE_FIXED|SETTING SetCameraPhase(1)) + UNK6 marker + terminator.
    Built via the codec itself so the offset tables are correct."""
    tgt = bytes([0x15, 0x80, 0x78, 0x06, 0x80, 0x13])            # static look-at
    focal = bytes([1, 3, 200 & 0xFF, 200 >> 8])
    seq = [
        {"frame": 1, "flags": 0x0809, "block": est_campos + tgt + focal},   # establish (no move)
        {"frame": 90, "flags": 0x4080, "block": b"\x01\x00"},               # SAVE_FIXED|SETTING type=1
        {"frame": 91, "flags": 0x8000, "block": b"\x21\x00\x00\x00"},       # UNK6 marker
        {"frame": 0},
    ]
    cams = [{"flags": 0x01, "sequences": [seq], "unknown": None, "position": None}]
    return struct.pack("<hh", 4, 4) + camera_codec.serialize_block(cams)     # camOffset = 4


def test_camera_author_grammar_matches_real_opening():
    donor = _raw17_opening()
    out = camera_codec.author_opening(donor, [0], [
        {"yaw": -76, "pitch": 5, "zoom": 2.5},                              # establish (instant, far/offset)
        {"yaw": -20, "zoom": 1.6, "move": 45, "ease": "in"},               # swoop
        {"move": 30, "ease": "out"}])                                       # settle == proven framing
    assert camera_codec.serialize_block(camera_codec.parse_block(out)[1]) == out[4:]   # round-trips
    codes = camera_codec.parse_block(out)[1][0]["sequences"][0]
    # frames: establish@1, move1@1, move2@(1+45)=46, handoff@(76+5)=81, marker@82, END
    assert [c["frame"] for c in codes] == [1, 1, 46, 81, 82, 0]
    assert codes[0]["flags"] & 0x02 == 0                          # establishing has NO movement (instant)
    assert codes[1]["flags"] & 0x02 and codes[2]["flags"] & 0x02  # both swoop segments DO move
    assert codes[3]["flags"] == 0x4080                            # SAVE_FIXED|SETTING handoff preserved
    assert codes[3]["block"] == b"\x01\x00"                       # == SetCameraPhase(1)
    assert codes[4]["flags"] == 0x8000                            # UNK6 marker preserved


def test_camera_author_anchors_on_proven_settle_pose():
    # the last keyframe with no offsets/zoom must reproduce the donor's SETTLE pose byte-for-byte (the shot
    # the battle actually uses) -- so an authored sweep always ends on the game's normal framing.
    base = bytes([0x15, 0x80, 0xF1, 0x20, 0x00, 0x0B])
    donor = _raw17_opening(est_campos=base)
    out = camera_codec.author_opening(donor, [0], [{"yaw": -40, "zoom": 2.0}, {"move": 30}])
    codes = camera_codec.parse_block(out)[1][0]["sequences"][0]
    settle = camera_codec._split_code(codes[1]["flags"], codes[1]["block"])
    assert settle["campos"][:6] == base                          # last segment == proven settle pose verbatim
    start = camera_codec._split_code(codes[0]["flags"], codes[0]["block"])
    assert start["campos"][3] == (0x20 - round(40 / 360 * 0x40)) % 0x40    # yaw offset -40deg
    assert start["campos"][5] == round(0x0B * 2.0)               # zoom x2 on distance


def test_camera_author_static_target_keeps_fight_framed():
    donor = _raw17_opening()
    out = camera_codec.author_opening(donor, [0], [
        {"yaw": -40}, {"yaw": -20, "move": 30}, {"move": 30}])
    codes = camera_codec.parse_block(out)[1][0]["sequences"][0]
    # every authored code looks at the donor's proven ON-FIGHT target (its last targetPosition), NOT a zeroed
    # or far one -- that's what keeps the framing where the battle actually settles.
    on_fight = bytes([0x15, 0x80, 0x78, 0x06, 0x80, 0x13])
    for c in codes[:3]:
        assert camera_codec._split_code(c["flags"], c["block"])["tgtpos"] == on_fight


def test_camera_author_needs_two_keyframes():
    with pytest.raises(camera_codec.CameraCodecError):
        camera_codec.author_opening(_raw17_opening(), [0], [{"yaw": 200}])     # one pose = static, not a sweep


def test_camera_author_no_opening_sequence_raises():
    with pytest.raises(camera_codec.CameraCodecError):
        camera_codec.author_opening(_raw17_opening(), [7], [{"yaw": 1}, {"yaw": 2, "move": 10}])  # no such cam


def test_scene_spawn_type_grounds_to_slot0_height():
    # slot 2's donor Ypos is 14 (slot*7); activating it via `type` should ground it to slot 0's Ypos (0)
    out, _ = scene_data.apply_scene_edits(_raw16(), {"enemy": [{"slot": 2, "type": 0, "pos": [50, 60]}]})
    put2 = 8 + 8 + 12 * 2
    assert struct.unpack_from("<h", out, put2 + 6)[0] == 0          # grounded to slot 0's height
    # an explicit y still wins
    out2, _ = scene_data.apply_scene_edits(_raw16(), {"enemy": [{"slot": 2, "type": 0, "y": 99}]})
    assert struct.unpack_from("<h", out2, put2 + 6)[0] == 99


def test_scene_spawn_validation():
    raw = _raw16()
    assert any("monster_count" in p for p in scene_data.validate_scene(raw, {"monster_count": 9}))
    assert any("type" in p for p in scene_data.validate_scene(raw, {"enemy": [{"slot": 0, "type": 5}]}))
    # an active slot with no FLG_TARGETABLE is rejected (couldn't hit it -> the fight can't end)
    assert any("targetable" in p for p in scene_data.validate_scene(_raw16(put_flags=0), {}))


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
