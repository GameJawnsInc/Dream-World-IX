"""[party] party-membership authoring -- add/remove existing playable characters at field load.

The authoring complement to `import --swap-player` (which changes who you WALK as): [party] mutates
party.member[] (who's in the MENU + BATTLE). The add is FF9's real B_PARTYADD (op 0x6D) JOIN form, proven
in-game (inject partyadd(Steiner) -> the party menu shows the new member). These tests pin the emitted
bytecode against the proven probe, the name/alias resolution, the build injection (prepended to Main_Init),
byte-identity when absent, validation, and the SetPartyReserve wipe-warning scan.
"""
from __future__ import annotations

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate, BuildError, _field_load_inject
from ff9mapkit.config import ModLayout
from ff9mapkit.content import party
from ff9mapkit.eb import EbScript, edit
import ff9mapkit.forkreport as forkreport


def _raise(exc):
    raise exc

BASE = """
[field]
id = 4003
name = "PARTYROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]
"""


# ---- the bytecode emitters (grounded in the in-game-proven probe) -----------------------------
def test_add_member_matches_proven_probe():
    # the in-game-proven probe bytes (2026-06-11): inject partyadd(Steiner=3) into Main_Init
    assert party.add_member(3) == bytes.fromhex("05 c5 93 7d 03 00 6d 2c 7f".replace(" ", ""))
    # real field 60 JOIN form (add Vivi=1)
    assert party.add_member(1) == bytes.fromhex("05 c5 93 7d 01 00 6d 2c 7f".replace(" ", ""))


def test_remove_member_is_removeparty_op():
    assert party.remove_member(0) == bytes([0xDD, 0x00, 0x00])    # RemoveParty(Zidane), literal arg
    assert party.remove_member(7) == bytes([0xDD, 0x00, 0x07])


def test_party_body_removes_then_adds_else_empty():
    assert party.party_body() == b""                              # nothing -> byte-identical caller
    assert party.party_body(adds=[3], removes=[0]) == party.remove_member(0) + party.add_member(3)


# ---- name resolution --------------------------------------------------------------------------
def test_resolve_member_names_aliases_ints():
    assert party.resolve_member("steiner") == 3
    assert party.resolve_member("STEINER") == 3
    assert party.resolve_member("dagger") == 2                    # alias -> Garnet
    assert party.resolve_member("salamander") == 7               # alias -> Amarant
    assert party.resolve_member(5) == 5                          # bare CharacterOldIndex passes through
    with pytest.raises(ValueError):
        party.resolve_member("zorn")
    with pytest.raises(ValueError):
        party.resolve_member(99)
    with pytest.raises(ValueError):
        party.resolve_member(True)                              # bools are not members


def test_char_table_pinned_to_forkreport():
    """Single source of truth: the local table must stay in lockstep with forkreport's (the scanner side)."""
    assert party.CHAR_OLD_INDEX == forkreport.CHAR_OLD_INDEX


# ---- build integration ------------------------------------------------------------------------
def _build_eb(tmp_path, toml: str) -> EbScript:
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_PARTYROOM.eb.bytes").read_bytes())


def _main_init_bytes(eb: EbScript) -> bytes:
    f0 = eb.entry(0).func_by_tag(0)
    return eb.data[f0.abs_start:f0.abs_end]


def test_party_add_injected_at_start_of_main_init(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner"]\n'))
    assert party.add_member(3) in body
    assert body.startswith(party.add_member(3))                  # prepended -> runs at field load


def test_party_add_and_remove(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE + '\n[party]\nremove = ["zidane"]\nadd = ["vivi"]\n'))
    assert party.remove_member(0) in body and party.add_member(1) in body


def test_party_absent_is_byte_identical(tmp_path):
    body = _main_init_bytes(_build_eb(tmp_path, BASE))
    assert party.add_member(3) not in body
    # the partyadd opcode signature (expr + MAP scratch) is absent entirely when [party] is omitted
    assert bytes([0x05, party._region.MAP_BOOL, party.PARTY_SCRATCH]) not in body


def test_party_eb_parses_clean_after_inject(tmp_path):
    eb = _build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner", "vivi"]\n')
    f0 = eb.entry(0).func_by_tag(0)
    assert list(eb.instrs(f0))                                    # Main_Init still disassembles (no fpos corruption)
    reinit = eb.entry(0).func_by_tag(10)
    if reinit is not None:
        assert list(eb.instrs(reinit))                           # the after-battle handler survived intact


# ---- validation -------------------------------------------------------------------------------
def _problems(tmp_path, toml: str):
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    return validate(FieldProject.load(p))


def test_party_validate_catches_bad_shapes(tmp_path):
    assert any("unknown party member" in m for m in _problems(tmp_path, BASE + '\n[party]\nadd = ["zorn"]\n'))
    assert any("must be a list" in m for m in _problems(tmp_path, BASE + '\n[party]\nadd = "steiner"\n'))
    assert any("unknown key" in m for m in _problems(tmp_path, BASE + '\n[party]\nfoo = ["vivi"]\n'))
    assert any("no add or remove" in m for m in _problems(tmp_path, BASE + "\n[party]\n"))


# ---- the SetPartyReserve wipe-scan ------------------------------------------------------------
def test_field_resets_party_scan(tmp_path):
    eb = _build_eb(tmp_path, BASE + '\n[party]\nadd = ["steiner"]\n')
    assert party.field_resets_party(eb) is False                 # a synthesized field never rebuilds the roster
    reserve = bytes([party.SET_PARTY_RESERVE, 0x00, 0x00, 0x00])
    # 0xB4 in Main_Init (entry 0 tag 0) -> flagged
    assert party.field_resets_party(EbScript.from_bytes(
        edit.insert_in_function(eb.data, 0, 0, 0, reserve))) is True
    # ★ the broadened scan: 0xB4 in an OBJECT Init (entry 1 tag 0), NOT Main_Init, is also flagged -- this is
    # the real-field case (Cargo Ship has SetPartyReserve in an object Init; the old entry-0/tag-0-only scan
    # missed 109 of 111 reset fields).
    assert party.field_resets_party(EbScript.from_bytes(
        edit.insert_in_function(eb.data, 1, 0, 0, reserve))) is True


# ---- the jump-table fail-closed guard (adversarial-review finding) ----------------------------
def test_field_load_inject_converts_jump_table_valueerror():
    """Defensive net: if a field-load injector ever raises a 0x06 jump-table ValueError (a MID-function insert),
    _field_load_inject must convert it to a clear BuildError, not leak an opaque ValueError. The levers all
    PREPEND (rel_off=0), which is always safe past a jump table since the rel_off==0 fix, so this no longer
    fires for them -- but the conversion stays as insurance for a future mid-insert lever."""
    jt = ValueError("func 0 has a jump table (0x06); insert unsupported")
    with pytest.raises(BuildError, match="jump table"):
        _field_load_inject("[party]", "FIELD100", lambda: _raise(jt))
    # an UNRELATED ValueError is re-raised as-is (not swallowed/masked)
    with pytest.raises(ValueError, match="something else"):
        _field_load_inject("[party]", "X", lambda: _raise(ValueError("something else")))
    # a clean injection passes its result straight through
    assert _field_load_inject("[party]", "X", lambda: b"ok") == b"ok"


# ---- [[playable]] -- recruiting a genuine NEW (13th+) CharacterId ------------------------------
def test_resolve_member_custom_band_and_registry():
    assert party.resolve_member(12) == 12                            # a custom 13th id passes through
    assert party.resolve_member(15) == 15
    with pytest.raises(ValueError):
        party.resolve_member(16)                                     # above the custom band
    reg = {"zephyr": 12, "ark": 13}
    assert party.resolve_member("Zephyr", reg) == 12                 # a custom char by name (via the registry)
    assert party.resolve_member("steiner", reg) == 3                 # base names still resolve with a registry present
    with pytest.raises(ValueError):
        party.resolve_member("Zephyr")                             # no registry -> the custom name is unknown


def test_apply_party_recruits_playable_recruit_flag(tmp_path):
    from types import SimpleNamespace
    from ff9mapkit import build
    eb = _build_eb(tmp_path, BASE).data                             # a clean synth field eb (no install needed)
    proj = SimpleNamespace(raw={"playable": [{"name": "Marcus", "borrow": "vivi", "id": 12, "recruit": True}]})
    out = build._apply_party(proj, eb)                              # recruit = true -> B_PARTYADD(12) prepended
    body = _main_init_bytes(EbScript.from_bytes(out))
    assert party.add_member(12) in body


def test_apply_party_recruits_custom_by_name(tmp_path):
    from types import SimpleNamespace
    from ff9mapkit import build
    eb = _build_eb(tmp_path, BASE).data
    proj = SimpleNamespace(raw={"playable": [{"name": "Zephyr", "borrow": "vivi", "id": 12}],
                                "party": {"add": ["Zephyr"]}})       # [party] add by the [[playable]] name
    body = _main_init_bytes(EbScript.from_bytes(build._apply_party(proj, eb)))
    assert party.add_member(12) in body


def test_dictionary_lines_includes_charname_extras():
    from types import SimpleNamespace
    from ff9mapkit.build import _dictionary_lines
    r = SimpleNamespace(text_block=1073, register_text_block=False, location_line=None, mint_lines=[],
                        dict_line="FieldScene 4003 11 100 PARTYROOM 1073")
    out = _dictionary_lines([r], ["CharacterDefaultName 12 US Marcus"])
    assert "CharacterDefaultName 12 US Marcus" in out
    assert out.index("CharacterDefaultName 12 US Marcus") < out.index(r.dict_line)   # directive before FieldScene


def test_playable_validate_and_party_by_name(tmp_path):
    # a bare custom id validates clean (the [[playable]] may be defined elsewhere / mod-global)
    assert _problems(tmp_path, BASE + "\n[party]\nadd = [12]\n") == []
    # [party] add by a custom NAME resolves only when a [[playable]] with that name is on the field
    ok = BASE + '\n[[playable]]\nname = "Zephyr"\nborrow = "vivi"\n[party]\nadd = ["Zephyr"]\n'
    assert _problems(tmp_path, ok) == []
    bad = BASE + '\n[party]\nadd = ["Zephyr"]\n'                    # no [[playable]] -> the name is unknown
    assert any("unknown party member" in m for m in _problems(tmp_path, bad))
    # a malformed [[playable]] is reported
    assert any("[[playable]]" in m for m in _problems(tmp_path, BASE + '\n[[playable]]\nborrow = "vivi"\n'))


def test_build_raises_on_bare_custom_recruit_without_playable(tmp_path):
    # a bare `[party] add = [12]` with NO [[playable]] defining id 12 would emit B_PARTYADD(12) but allocate no
    # PLAYER -> a null-deref crash at field load. The build must reject it (no install needed -- the guard fires
    # before any character CSV is read).
    p = tmp_path / "f.field.toml"
    p.write_text(BASE + "\n[party]\nadd = [12]\n", encoding="utf-8")
    with pytest.raises(BuildError, match=r"no \[\[playable\]\]|crashes"):
        build_mod([FieldProject.load(p)], tmp_path / "mod")


def test_full_build_playable_end_to_end(tmp_path):
    """The whole [[playable]] path in one build (install-gated: reads the base character CSVs). Skips cleanly
    on a public clone without the FF9 install."""
    toml = BASE + '\n[[playable]]\nname = "Marcus"\nborrow = "vivi"\nrecruit = true\nstats = { strength = 40 }\n'
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    try:
        build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    except BuildError as ex:
        if "install" in str(ex).lower():
            pytest.skip("no FF9 install for the base character CSVs")
        raise
    layout = ModLayout(out)
    # the allocator (CharacterParameters) + stats (BaseStats) both carry id-12
    assert any(l.split(";")[1:2] == ["12"] for l in layout.base_stats_csv.read_text(encoding="cp1252").splitlines()
               if l and not l.startswith("#"))
    assert any(l.split(";")[0:1] == ["12"] for l in
               layout.character_parameters_csv.read_text(encoding="cp1252").splitlines()
               if l and not l.startswith("#"))
    # the name directive rides the DictionaryPatch
    assert "CharacterDefaultName 12 US Marcus" in layout.dictionary_patch.read_text(encoding="utf-8")
    # Main_Init recruits the 13th character
    eb = EbScript.from_bytes(layout.eb_path("us", "EVT_PARTYROOM.eb.bytes").read_bytes())
    assert party.add_member(12) in _main_init_bytes(eb)


def test_full_build_custom_battle_model(tmp_path):
    """custom_battle_model = true -> a minted independent battle GEO + a BattleParameters serial-19 row + Iviv's
    serial pointed at 19 (install-gated: reads the base CharacterParameters/BattleParameters)."""
    toml = BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\ncustom_battle_model = true\n'
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    try:
        build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    except BuildError as ex:
        if "install" in str(ex).lower():
            pytest.skip("no FF9 install for the base character CSVs")
        raise
    layout = ModLayout(out)
    # the minted, INDEPENDENT battle model (Models/2/6100 -- NOT Vivi's 5415)
    assert (layout.model_dir(2, 6100) / "6100.fbx").is_file()
    assert "3DModel 6100 GEO_MAIN_B0_M100" in layout.dictionary_patch.read_text(encoding="utf-8")
    # a new BattleParameters serial-19 row using the minted GEO
    bp = [l for l in layout.battle_parameters_csv.read_text(encoding="cp1252").splitlines()
          if l.startswith("19;")]
    assert bp and "GEO_MAIN_B0_M100" in bp[0]
    # Iviv's CharacterParameters serial (col 6) points at the new serial 19
    cp = [l for l in layout.character_parameters_csv.read_text(encoding="cp1252").splitlines()
          if l.startswith("12;") and not l.startswith("#")]
    assert cp and cp[0].split(";")[6] == "19"


def test_full_build_portrait(tmp_path):
    """portrait = a custom menu portrait: a loose Face Atlas override + a BattleParameters serial row whose
    AvatarSprite is the new sprite, WITHOUT minting a model (install-gated: reads the donor's serial)."""
    from PIL import Image
    Image.new("RGBA", (132, 190), (255, 0, 255, 255)).save(tmp_path / "port.png")
    toml = BASE + '\n[[playable]]\nname = "Iviv"\nborrow = "vivi"\nrecruit = true\nportrait = "port.png"\n'
    p = tmp_path / "f.field.toml"
    p.write_text(toml, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    try:
        build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    except BuildError as ex:
        if "install" in str(ex).lower():
            pytest.skip("no FF9 install for the base character CSVs")
        raise
    layout = ModLayout(out)
    # the loose Face Atlas override (append)
    assert (layout.face_atlas_dir / "Face Atlas.png").is_file()
    tp = (layout.face_atlas_dir / "Face Atlas.png.tpsheet").read_text(encoding="utf-8")
    assert ":append=true" in tp and "face_cu12;" in tp
    # a BattleParameters serial-19 row whose AvatarSprite (col 1) is the custom sprite
    bp = [l for l in layout.battle_parameters_csv.read_text(encoding="cp1252").splitlines() if l.startswith("19;")]
    assert bp and bp[0].split(";")[1] == "face_cu12"
    # portrait-only -> NO minted model (no 3DModel line for a battle-model mint)
    assert "GEO_MAIN_B0_M" not in layout.dictionary_patch.read_text(encoding="utf-8")


def test_resolve_playable_battle_canonicalizes_and_explicit_serial():
    # review fixes: (1) a lowercase battle_model_from is CANONICALIZED so the BattleParameters ModelId matches the
    # registered 3DModel name; (2) an explicit battle_borrow_serial lets a scenario-formula donor work (no
    # resolve_donor_battle call -> no install needed here).
    from ff9mapkit.build import _resolve_playable_battle
    spec = {"playable_id": 12, "name": "Iviv", "borrow_id": 2, "model_id": 6100, "serial": 19, "custom_model": True,
            "model_from": "geo_main_b0_006", "borrow_serial": 2, "avatar": None}    # lowercase source + explicit serial
    mb, bp, plan = _resolve_playable_battle(spec)                         # 3-tuple: plan is None without custom_anims
    assert mb["from"] == "GEO_MAIN_B0_006"                                # canonical (uppercase) == the 3DModel name
    assert bp["model"] == "GEO_MAIN_B0_M100"                              # ModelId cell == the registered GEO name
    assert bp["borrow"] == 2 and bp["id"] == 19                          # the explicit anim-source serial was used
    assert plan is None and "anim_names_remap" not in bp                  # no custom_battle_anims -> shared donor clips


def _thirteenth_example():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[1] / "examples" / "thirteenth-character" / "iviv.field.toml"


def test_resolve_playable_animset_maps_the_edit_loop():
    # the Blender edit-loop resolver: the field's custom_battle_anims playable -> (source donor, mint dest, clips).
    from ff9mapkit.config import find_game_path
    from ff9mapkit.build import resolve_playable_animset, FieldProject as FP
    try:
        find_game_path()
    except Exception:                                                    # noqa: BLE001 -- needs the install for the plan
        pytest.skip("needs the FF9 install (reads the base BattleParameters.csv + p0data)")
    info = resolve_playable_animset(str(_thirteenth_example()))
    assert info["name"] == "Iviv" and info["source_geo"] == "GEO_MAIN_B0_006"
    assert info["dest_geo_id"] == 6100 and info["src_geo_id"] == 5415 and info["key_count"] == 34
    assert all(len(c) == 3 and c[0] == 5415 for c in info["clips"])       # (src_geo_id, src_key, dst_key), one source
    assert {c[2] for c in info["clips"]} == {1010000 + i for i in range(34)}   # the mint's fresh key band
    # a field whose playable lacks custom_battle_anims -> a clear error (no animset to edit)
    proj = FP.load(str(_thirteenth_example()))
    proj.raw["playable"][0].pop("custom_battle_anims", None)
    with pytest.raises(BuildError):
        resolve_playable_animset(proj)


def test_anim_edits_build_ships_the_edited_animset(tmp_path):
    # [[playable]] anim_edits = a Blender-edited .glb the BUILD ships onto the animset (survives re-deploy).
    from ff9mapkit.config import find_game_path
    import ff9mapkit.build as B
    from ff9mapkit.build import build_mod, FieldProject as FP
    from ff9mapkit.models import gltf as mgltf
    from ff9mapkit.battle import characterdelta as cd
    import shutil
    try:
        find_game_path()
    except Exception:                                                    # noqa: BLE001 -- needs the install
        pytest.skip("needs the FF9 install (export + build read p0data)")
    proj_dir = tmp_path / "proj"
    shutil.copytree(_thirteenth_example().parent, proj_dir)
    toml_path = proj_dir / "iviv.field.toml"
    info = B.resolve_playable_animset(str(toml_path))                    # export the animset glb INTO the project dir
    mgltf.export_gltf(info["source_geo"], str(proj_dir / "iviv_anims.glb"),
                      anims=" ".join(str(sk) for _sg, sk, _dk in info["clips"]),
                      label_overrides=cd.battle_motion_labels(info["serial"]))
    proj = FP.load(str(toml_path))                                       # base_dir = proj_dir (next to the glb)
    proj.raw["playable"][0]["anim_edits"] = "iviv_anims.glb"
    B.build_mod([proj], tmp_path / "mod", mod_name="FF9CustomMap")
    shipped = list((tmp_path / "mod/StreamingAssets/Assets/Resources/Animations/6100").glob("*.anim"))
    assert len(shipped) == 34                                            # the EDITED-animset path ran + shipped all 34
    # a missing anim_edits file fails the build loud (not a silent freeze)
    proj2 = FP.load(str(toml_path))
    proj2.raw["playable"][0]["anim_edits"] = "nope.glb"
    with pytest.raises(BuildError):
        build_mod([proj2], tmp_path / "mod2", mod_name="FF9CustomMap")
