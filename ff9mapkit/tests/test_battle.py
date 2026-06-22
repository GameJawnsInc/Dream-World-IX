"""Pure (no game install) tests for the battle-map pillar: ASCII-FBX emit + battle.toml validate.

These are in the PURE tier (NOT in conftest._NEEDS_GAME_DATA) -- they build synthetic geometry and a
temp battle.toml, so they run on a fresh clone without UnityPy or the FF9 install.
"""
from __future__ import annotations

import textwrap

import struct

import pytest

from ff9mapkit.battle import camera_codec, camera_data, event_data, fbx, scene_data
from ff9mapkit.battle.build import (BattleProject, _ai_entries, _author_inb, _bbg_number, build_battle_mod,
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


def test_battle_toml_templates_render():
    # guard: `battle.extract` is only imported by the (game-data-gated) CLI path, so a SyntaxError or a
    # bad f-string in its toml TEMPLATES (e.g. a literal { in the camera_keyframes docs) would slip past
    # the rest of the suite. Importing + rendering both templates here catches that in the pure tier.
    from ff9mapkit.battle import extract
    mint = extract._mint_toml("BBG_B209", "CAMKEYS", 30011, 8, 3,
                              {"donor": "EF_R007", "donor_id": 67}, new_bbg=True)
    assert "[[scene.camera_keyframes]]" in mint and "BBG_B209" in mint
    assert "BBG_B013" in extract._battle_toml("BBG_B013", "FORK", 5000, 8, 3)


def test_parse_fbx_roundtrips_emit():
    # the Blender loop hinges on this: parse our own FBX back to `groups` and re-emit byte-identically
    text, _ = fbx.emit_fbx(_groups())
    parsed = fbx.parse_fbx(text)
    assert fbx.emit_fbx(parsed)[0] == text                         # exact round-trip
    assert [g["name"] for g in parsed] == ["Group_2", "Group_0"]   # group names + order preserved
    assert [len(g["submeshes"]) for g in parsed] == [1, 2]         # multi-submesh merged by group name
    assert [sm["texture"] for sm in parsed[1]["submeshes"]] == ["image0", "image1"]  # per-submesh texture
    assert parsed[0]["normals"] is not None and parsed[1]["normals"] is None         # normals presence kept
    assert parsed[0]["verts"] == [[-1, 0, -1], [1, 0, -1], [1, 0, 1], [-1, 0, 1]]    # verts verbatim
    assert parsed[1]["submeshes"][1]["tris"] == [[2, 1, 0]]        # winding (PolygonVertexIndex) preserved


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


def _scene_raw16(flags=0):
    """A minimal 1-pattern / 1-type raw16 with put[0] -> type 0 (targetable) and a given header Flags word."""
    from ff9mapkit.battle import scene_codec as sc
    mon = sc.MonParm.unpack(bytes(116))
    puts = [sc.Put(0, 1, 0, 0, 0, 0, 0, 0)] + [sc.Put(0, 0, 0, 0, 0, 0, 0, 0) for _ in range(3)]
    pat = sc.Pattern(rate=100, monster_count=1, camera=0, pad0=0, ap=10, puts=puts)
    head = bytes([0, 1, 1, 0]) + struct.pack("<H", flags) + b"\x00\x00"   # Ver/Pat/Typ/Atk + Flags(2) + pad(2)
    return sc.serialize_scene(sc.Scene(head=head, patterns=[pat], monsters=[mon], attacks=[], tail=b""))


def test_apply_scene_flags_sets_named_bits_and_preserves_others():
    from ff9mapkit.battle.scene_data import apply_scene_edits
    raw = _scene_raw16(flags=0x04)                            # an unknown bit 2 set -> must survive
    out, _ = apply_scene_edits(raw, {"flags": ["back_attack", "no_escape"]})
    fl = struct.unpack_from("<H", out, 4)[0]
    assert fl & 0x02 and fl & 0x20                            # back_attack + no_escape set
    assert fl & 0x04                                         # the unknown bit is preserved
    assert not (fl & 0x01) and not (fl & 0x08)               # preemptive / no_exp cleared (not named)


def test_apply_scene_flags_raw_int_and_absent():
    from ff9mapkit.battle.scene_data import apply_scene_edits
    raw = _scene_raw16(flags=0x04)
    out, _ = apply_scene_edits(raw, {"flags": 0x09})         # a raw int REPLACES the whole word
    assert struct.unpack_from("<H", out, 4)[0] == 0x09
    out2, _ = apply_scene_edits(raw, {})                     # absent -> the donor's header is kept verbatim
    assert struct.unpack_from("<H", out2, 4)[0] == 0x04


def test_apply_scene_flags_unknown_name_errors():
    from ff9mapkit.battle.scene_data import apply_scene_edits, SceneEditError
    with pytest.raises(SceneEditError):
        apply_scene_edits(_scene_raw16(), {"flags": ["nope"]})


def test_raw_int_flags_survive_the_gui_strlist_roundtrip():
    # a hand-authored raw-int `flags = 9` opened+saved in the GUI normalises to the one-int list [9] (STRLIST
    # re-parse); the encoders must read [9] as the raw word 9, NOT a flag NAMED "9" (the review-found regression).
    from ff9mapkit.editor import battle_forms as bf, forms
    from ff9mapkit.battle.scene_data import _encode_flags, _encode_scene_flags
    se = forms.build_entity(bf.SCENE_SPEC, forms.entity_to_values(bf.SCENE_SPEC, {"flags": 9}))
    assert se["flags"] == [9] and _encode_scene_flags(se["flags"], 0x04) == 9
    ee = forms.build_entity(bf.ENEMY_SPEC, forms.entity_to_values(bf.ENEMY_SPEC, {"slot": 0, "flags": 9}))
    assert ee["flags"] == [9] and _encode_flags(ee["flags"], 0) == 9
    # a multi-int list ORs to one raw word; a name list still takes the named-bit path (preserving other bits)
    assert _encode_scene_flags([1, 2], 0) == 3
    assert _encode_scene_flags(["back_attack"], 0x04) == 0x06          # 0x04 preserved + back_attack (0x02)


def test_validate_battle_flags_bad_camera_zoom(tmp_path):
    _write_scene(tmp_path)                                            # mint scene assets present -> scene is validated
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
        scene_id = 5000
        scene_name = "FIGHT"

        [scene]
        camera_zoom = 0.0
    ''')
    assert any("camera_zoom must be > 0" in p for p in validate_battle(proj))


def test_validate_battle_lints_player_csv_blocks(tmp_path):
    # the mod-global player/ability CSV deltas a battle.toml may carry are lint-checked by validate_battle
    # (install-free: value range + structure). A bad [[character]] stat and a bad [[battle_action]] are caught.
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"

        [[character]]
        character = "Vivi"
        strength = 999            # Byte stat, max 255

        [[battle_action]]
        action = "Fire"
        category = 999            # Byte column, max 255
    ''')
    probs = validate_battle(proj)
    assert any("[[character]]" in p and "out of range" in p for p in probs)
    assert any("[[battle_action]]" in p and "out of range" in p for p in probs)


def test_validate_battle_passes_valid_offline_player_block(tmp_path):
    # [[status_set]] is fully offline (no base CSV read) -> a valid one lints clean
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"

        [[status_set]]
        id = 39
        name = "Venom"
        statuses = ["Poison"]
    ''')
    assert validate_battle(proj) == []


def test_build_battle_emits_offline_player_csv(tmp_path):
    # the emit wiring: a [[status_set]] (offline; no install) is written into the layout, listed in
    # info["written"], and the mod-global caveat is surfaced as a warning.
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"

        [[status_set]]
        id = 39
        name = "Venom"
        statuses = ["Poison"]
    ''')
    out = tmp_path / "dist"
    info = build_battle_mod([proj], out)
    layout = ModLayout(out)
    assert layout.status_sets_csv.is_file()
    assert str(layout.status_sets_csv) in info["written"]
    assert any("mod-GLOBAL" in w for w in info["warnings"])
    body = layout.status_sets_csv.read_text(encoding="cp1252")
    assert "Venom;39;" in body


def test_build_battle_no_player_blocks_emits_no_csv(tmp_path):
    # a plain override build touches NO player CSV file and adds NO mod-global warning (the install isn't read)
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B013"
    ''')
    info = build_battle_mod([proj], tmp_path / "dist")
    layout = ModLayout(tmp_path / "dist")
    assert not layout.status_sets_csv.exists() and not layout.base_stats_csv.exists()
    assert not any("mod-GLOBAL" in w for w in info["warnings"])


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


def test_ai_entries_helper():
    # the build/validate plumbing: [[scene.enemy]] -> per-slot AI-entry override list (None = default)
    assert _ai_entries({"enemy": [{"slot": 0, "ai_entry": 2}]}, 1) == [2]
    assert _ai_entries({"enemy": [{"slot": 1, "ai_entry": 2}]}, 2) == [None, 2]
    assert _ai_entries({"enemy": [{"slot": 0, "type": 0}]}, 1) is None      # no ai_entry -> None (default binding)
    with pytest.raises((TypeError, ValueError)):                            # a TOML array ai_entry -> a clean raise
        _ai_entries({"enemy": [{"slot": 0, "ai_entry": [2]}]}, 1)           # (callers turn it into a problem, not a crash)


def test_validate_ai_entry_without_monster_count(tmp_path):
    _write_scene(tmp_path)                                                  # mint scene assets present
    proj = _write_project(tmp_path, '''
        [battlemap]
        bbg = "BBG_B200"
        fbx = "BBG_B013.fbx"
        scene_id = 5502
        scene_name = "KIT_ARENA"
        [scene]
        [[scene.enemy]]
        slot = 0
        ai_entry = 2
    ''')
    assert any("ai_entry has no effect" in p for p in validate_battle(proj))   # an orphaned override is surfaced


def test_rewrite_main_init_ai_entry_override():
    # the offset-entry-donor fix: pin the spawned enemy's AI entry explicitly instead of the generic 1+type
    eb = _battle_eb([(2, 0x80)], n_ai=2)                    # entries 1 and 2 are both AIs
    def inits(b):
        s = EbScript.from_bytes(b)
        return [(i.imm(0), i.imm(1)) for i in s.instrs(s.entry(0).func_by_tag(0)) if i.op == 0x09]
    assert inits(event_data.rewrite_main_init(eb, [0], None)) == [(1, 0x80)]   # default: type 0 -> entry 1
    assert inits(event_data.rewrite_main_init(eb, [0], [2])) == [(2, 0x80)]    # override: type 0 pinned to entry 2
    assert inits(event_data.rewrite_main_init(eb, [0, 0], [2, None])) == [(2, 0x80), (1, 0x81)]   # None = default


def test_rewrite_main_init_bad_ai_entry_raises():
    eb = _battle_eb([(2, 0x80)], n_ai=2)                    # entries 0,1,2 exist; entry 9 does not
    with pytest.raises(ValueError, match="ai_entry = 9 is not a valid"):
        event_data.rewrite_main_init(eb, [0], [9])
    with pytest.raises(ValueError, match="entry 0 is Main_Init"):   # ai_entry 0 = Main_Init itself (non-empty) -> reject
        event_data.rewrite_main_init(eb, [0], [0])


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


# --------------------------------------------------------------- scene_data combat-identity (Phase 1)
def test_scene_edits_combat_identity():
    raw = _raw16()                                              # patcount 1, typcount 2; slot 0 -> type 0
    scene = {"ap": 40, "enemy": [{
        "slot": 0, "weak": ["Fire"], "null": ["Ice"], "absorb": ["Holy"], "half": ["Thunder"],
        "phys_def": 20, "phys_evade": 5, "mag_def": 15, "mag_evade": 3, "hit_rate": 60,
        "category": 8, "blue_magic": 12, "win_card": 99,
        "resist_status": ["Death", "Petrify"], "auto_status": ["Float"]}]}
    out, warns = scene_data.apply_scene_edits(raw, scene)
    assert not warns and len(out) == len(raw)
    mon0 = 8 + 56                                               # type-0 block
    assert out[mon0 + 63] == 1 and out[mon0 + 60] == 2          # weak=Fire / null(guard)=Ice
    assert out[mon0 + 61] == 64 and out[mon0 + 62] == 4         # absorb=Holy / half=Thunder
    assert out[mon0 + 67] == 20 and out[mon0 + 68] == 5         # phys def / evade
    assert out[mon0 + 69] == 15 and out[mon0 + 70] == 3         # mag def / evade
    assert out[mon0 + 66] == 60 and out[mon0 + 65] == 8         # hit_rate / category
    assert out[mon0 + 71] == 12 and out[mon0 + 105] == 99       # blue_magic / win_card
    assert struct.unpack_from("<I", out, mon0 + 0)[0] == (1 << 8) | (1 << 0)   # resist = Death|Petrify
    assert struct.unpack_from("<I", out, mon0 + 4)[0] == (1 << 21)             # auto = Float
    assert struct.unpack_from("<I", out, 8 + 4)[0] == 40                       # pattern AP reward


def test_scene_edits_ap_reward_written_to_all_patterns():
    raw = _raw16(patcount=2)
    out, _ = scene_data.apply_scene_edits(raw, {"ap": 1234})
    for p in range(2):
        assert struct.unpack_from("<I", out, 8 + 56 * p + 4)[0] == 1234


def test_scene_edits_masks_accept_raw_int():
    out, _ = scene_data.apply_scene_edits(_raw16(), {"enemy": [
        {"slot": 0, "weak": 5, "resist_status": 1 << 19}]})
    mon0 = 8 + 56
    assert out[mon0 + 63] == 5                                  # raw element bitmask passes through
    assert struct.unpack_from("<I", out, mon0 + 0)[0] == (1 << 19)


def test_scene_edits_enemy_flags():
    raw, mon0 = _raw16(), 8 + 56                                # type-0 block; Flags @48
    out, warns = scene_data.apply_scene_edits(raw, {"enemy": [
        {"slot": 0, "flags": ["non_dying_boss", "die_dmg"]}]})  # names OR'd
    assert not warns and struct.unpack_from("<H", out, mon0 + 48)[0] == 4 | 2
    out2, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 0, "flags": "non_dying_boss"}]})
    assert struct.unpack_from("<H", out2, mon0 + 48)[0] == 4    # a single name
    out3, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 0, "flags": 0x0105}]})
    assert struct.unpack_from("<H", out3, mon0 + 48)[0] == 0x0105   # raw int passes high bits to the AI
    diff = [i for i in range(len(raw)) if raw[i] != out2[i]]
    assert diff == [mon0 + 48]                                  # only the Flags low byte changed (4 -> @48)


def test_scene_edits_bad_flags():
    assert any("flag" in p for p in
               scene_data.validate_scene(_raw16(), {"enemy": [{"slot": 0, "flags": ["nope"]}]}))
    assert any("65535" in p for p in
               scene_data.validate_scene(_raw16(), {"enemy": [{"slot": 0, "flags": 99999}]}))


def test_scene_edits_bad_element_and_status_names():
    assert any("element" in p for p in
               scene_data.validate_scene(_raw16(), {"enemy": [{"slot": 0, "weak": ["Nope"]}]}))
    assert any("status" in p for p in
               scene_data.validate_scene(_raw16(), {"enemy": [{"slot": 0, "resist_status": ["Bogus"]}]}))


def test_scene_edits_combat_identity_only_touches_edited_bytes():
    raw = _raw16()
    out, _ = scene_data.apply_scene_edits(raw, {"enemy": [{"slot": 1, "weak": ["Fire"]}]})
    diff = [i for i in range(len(raw)) if raw[i] != out[i]]
    assert diff == [8 + 56 + 116 + 63]                         # ONLY type-1's WeakElement byte


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
