"""Read side of the .eb: extracting gateways / music / encounters / movement from a real field.

Two oracles:
  * a REAL field -- Alexandria/Main Street (field 100, ``alex100-us.eb.bytes``) has three real exits
    (101/107/114) plus the door we injected in Session 12 (-> 4000), field BGM song 9, head-on
    movement, and no encounters. The scanner must recover all of that.
  * ROUND-TRIP against the kit's own injectors -- inject a gateway / encounter into the blank field,
    scan it back, and the values must match (the scanner is the exact inverse of the injectors).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit import data, eventscan
from ff9mapkit.content import encounter as _enc
from ff9mapkit.content import gateway as _gw

FIX = Path(__file__).parent / "fixtures"
ALEX100 = (FIX / "alex100-us.eb.bytes").read_bytes()
CLEAN = data.blank_field_bytes("us")


# --- real field (field 100) ---------------------------------------------------------------
def test_scan_gateways_real_field():
    gws = eventscan.scan_gateways(ALEX100)
    by_to = {g["to"]: g for g in gws}
    assert {101, 107, 114, 4000} <= set(by_to)            # 3 real exits + our injected door
    assert by_to[101]["entrance"] == 200                  # the real arrival entrance
    for g in gws:
        assert len(g["zone"]) in (3, 4)                   # normalised to quad corners
        assert all(len(p) == 2 for p in g["zone"])


def test_scan_injected_door_roundtrips_through_real_field():
    # the Session-12 Alexandria door we injected into field 100 -> our custom field 4000
    door = next(g for g in eventscan.scan_gateways(ALEX100) if g["to"] == 4000)
    assert door["entrance"] == 0
    assert door["zone"] == [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400]]


def test_scan_music_real_field():
    assert eventscan.scan_music(ALEX100) == 9             # Vivi's Theme (Disc 1)


def test_scan_control_direction_real_field():
    assert eventscan.scan_control_direction(ALEX100) == 0  # head-on town camera


def test_scan_encounter_none_in_town():
    assert eventscan.scan_encounter(ALEX100) is None       # towns have no random battles


# --- GLOB flag scanners (P5) --------------------------------------------------------------
def test_glob_var_token():
    assert eventscan._glob_var_token(bytes([0xC4, 191]), 0) == (191, 2)          # short GLOB bool
    assert eventscan._glob_var_token(bytes([0xE4, 0x71, 0x20]), 0) == (8305, 3)  # long GLOB bool (LE)
    assert eventscan._glob_var_token(bytes([0xC5, 5]), 0) is None                # MAP bool = transient
    assert eventscan._glob_var_token(bytes([0xE5, 0, 1]), 0) is None             # MAP long = transient
    assert eventscan._glob_var_token(bytes([0x7D, 0, 0]), 0) is None             # not a var token


def test_flag_gate_scanners_roundtrip():
    Z = [[-700, 2200], [200, 2200], [200, 3400], [-700, 3400], [-700, 3400]]   # quad + doubled last vertex
    eb = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=True)
    assert eventscan.scan_edge_flag_gates(eb) == [(8305, True)]      # the exact region.flag_gate prologue
    assert (8305, True) in eventscan.scan_required_flags(eb)         # general read form catches it too
    # a gate READS its flag, never WRITES it (the template's own housekeeping writes 184/191 stay separate)
    assert 8305 not in {idx for idx, _op in eventscan.scan_flags_set(eb)}

    eb2 = _gw.inject_gateway(CLEAN, 4000, entrance=0, zone=Z, gate_flag=8305, gate_require_set=False)
    assert eventscan.scan_edge_flag_gates(eb2) == [(8305, False)]    # polarity flips with require_set


def test_scan_content_aggregate():
    c = eventscan.scan_content(ALEX100)
    assert c["music"] == 9 and c["control_direction"] == 0 and c["encounter"] is None
    assert len(c["gateways"]) >= 4


# --- round-trips against the kit's own injectors ------------------------------------------
def test_gateway_roundtrip():
    zone = _gw.quad_zone([(-200, 200), (200, 200), (200, 400), (-200, 400)])
    eb = _gw.inject_gateway(CLEAN, 1234, entrance=42, zone=zone)
    gws = eventscan.scan_gateways(eb)
    assert len(gws) == 1
    g = gws[0]
    assert g["to"] == 1234 and g["entrance"] == 42
    assert g["zone"] == [[-200, 200], [200, 200], [200, 400], [-200, 400]]   # doubled vertex dropped


def test_encounter_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, freq=200)
    enc = eventscan.scan_encounter(eb)
    assert enc is not None
    assert enc["scenes"] == [67, 67, 67, 67]
    assert enc["freq"] == 200


def test_encounter_distinct_scenes_roundtrip():
    eb = _enc.inject_encounter(CLEAN, scene=67, scenes=(10, 11, 12, 13), freq=128)
    enc = eventscan.scan_encounter(eb)
    assert enc["scenes"] == [10, 11, 12, 13] and enc["freq"] == 128


# --- import emission (the field.toml blocks ff9mapkit import writes) ----------------------
def test_imported_content_toml_is_valid_and_complete(tmp_path):
    import tomllib
    from ff9mapkit import extract
    # objects carry a verbatim entry sidecar, so the emit needs an out_dir (as ladders/jumps do)
    blocks, cd, summary = extract._imported_content_toml(ALEX100, out_dir=tmp_path, name="field")
    assert cd == 0
    assert summary == {"gateways": 4, "encounter": False, "music": 9, "control_direction": 0,
                       "ladders": 0, "jumps": 0, "objects": 2,   # Alexandria: the bell + the ticket prop,
                       "gateways_retargeted": 0, "gateways_seamed": 0}   # carried VERBATIM (hidden NPCs skipped)
    # the verbatim entry sidecars are written next to the field.toml
    assert (tmp_path / "field.object0.bin").is_file() and (tmp_path / "field.object1.bin").is_file()
    # embed in a complete borrow field.toml -> it must be valid TOML with the right structures
    toml = ('[field]\nid=4003\nname="T"\narea=2\nborrow_bg="X"\n\n'
            f'[camera]\nborrow="c.bgx"\ncontrol_direction={cd}\n\n[player]\nspawn=[0,0]\n\n{blocks}')
    d = tomllib.loads(toml)
    assert {g["to"] for g in d["gateway"]} == {101, 107, 114, 4000}
    assert all(len(g["zone"]) == 4 for g in d["gateway"])
    assert d["music"]["song"] == 9
    # the imported objects are emitted as [[object]] graft blocks pointing at their sidecars
    assert len(d["object"]) == 2 and {o["bin"] for o in d["object"]} == {"field.object0.bin", "field.object1.bin"}
    assert all("instances" in o and o["donor_player_entry"] == 19 for o in d["object"])


# --- scan_objects: carry a real field's persistent NPCs/props (faithful fork) -------------
def test_scan_objects_roundtrips_an_injected_prop():
    # the scanner is the inverse of the prop injector: inject a prop, scan it back exactly.
    from ff9mapkit.content import prop as _prop
    eb = _prop.inject_prop(CLEAN, 120, -340, model=133, pose=1872, face=5)
    objs = eventscan.scan_objects(eb)
    assert len(objs) == 1
    o = objs[0]
    assert o["kind"] == "prop" and o["model_id"] == 133 and o["pose"] == 1872
    assert (o["x"], o["z"]) == (120, -340) and o["face"] == 5 and o["talkable"] is False


def test_scan_objects_roundtrips_an_injected_npc_as_talkable():
    from ff9mapkit.content import npc as _npc
    eb = _npc.inject_npc(CLEAN, -80, 200, model=220, animset=50)   # a GEO_NPC moogle, talkable (keeps tag-3)
    objs = eventscan.scan_objects(eb)
    assert len(objs) == 1 and objs[0]["kind"] == "npc" and objs[0]["talkable"] is True
    assert (objs[0]["x"], objs[0]["z"]) == (-80, 200) and objs[0]["model_id"] == 220


def test_scan_objects_blank_field_has_none():
    # the bare template's only object is the PLAYER (DefinePlayerCharacter), which is excluded.
    assert eventscan.scan_objects(CLEAN) == []


def _game_ready():
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_objects_skips_script_hidden_save_machinery():
    # field 122 (the Dali storage room): the visible barrel/boxes carry; the SAVE-POINT machinery
    # (moogle/book/tent, all loaded HIDDEN via SetObjectFlags + shown by the save script) is skipped --
    # carrying it placed an always-deployed tent + a floating moogle (the in-game-reported bug).
    from ff9mapkit import extract
    models = {o["model"] for o in eventscan.scan_objects(
        extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0"))}
    assert "GEO_ACC_F0_CSK" in models                                  # the barrel (shown set-dressing)
    assert not (models & {"GEO_ACC_F0_TNT", "GEO_ACC_F0_MGR", "GEO_NPC_F0_MOG"})   # hidden save machinery


# --- scan_objects_verbatim: the FAITHFUL graft spec (verbatim entry bytes + ref classification) -----
def test_scan_objects_verbatim_blank_has_none():
    assert eventscan.scan_objects_verbatim(CLEAN) == []


def test_scan_objects_verbatim_roundtrips_injected_prop_verbatim():
    # the graft scanner carries the donor entry VERBATIM (not a decode) -- a kit prop references nothing,
    # so it's fully graft-safe, and its carried bytes are byte-identical to the entry in the script.
    from ff9mapkit.content import prop as _prop
    eb = _prop.inject_prop(CLEAN, 120, -340, model=133, pose=1872, face=5)
    specs = eventscan.scan_objects_verbatim(eb)
    assert len(specs) == 1
    s = specs[0]
    assert s["kind"] == "prop" and s["model_id"] == 133 and s["pose"] == 1872
    assert s["instances"] == [{"arg": 0, "x": 120, "z": -340}]
    assert s["graft_safety"] == "clean" and s["carry_tags"] == [0]     # bare prop: Init-only, no refs
    assert s["player_tags_needed"] == [] and s["refs"] == []
    assert s["entry_bytes"] == eventscan._entry_bytes(eb, s["donor_idx"])   # VERBATIM
    assert s["self_positions"] is True and s["needs_d9"] == {}


def test_scan_objects_verbatim_npc_is_talkable_and_clean():
    from ff9mapkit.content import npc as _npc
    eb = _npc.inject_npc(CLEAN, -80, 200, model=220, animset=50)
    specs = eventscan.scan_objects_verbatim(eb)
    assert len(specs) == 1 and specs[0]["kind"] == "npc"               # keeps a tag-3 talk func
    assert specs[0]["graft_safety"] == "clean" and specs[0]["carry_tags"] == [0, 1, 3]
    assert specs[0]["entry_bytes"] == eventscan._entry_bytes(eb, specs[0]["donor_idx"])


@pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")
def test_scan_objects_verbatim_field122_cask_is_render_faithful():
    # The bug that started this: the field-122 cask rendered upside-down via the player-clone. The graft
    # carries its REAL entry verbatim. Its interactive tag-2 RunScripts the PLAYER (by entry index 23) at
    # tag 24 -- a tag the blank fork's player (tags 0/1 only) lacks -- so it is init_only: render tags
    # carry, tag 2 drops. Validates the design's key facts (docs/OBJECT_CARRY.md).
    from ff9mapkit import extract
    from ff9mapkit.eb import EbScript
    eb = extract.extract_event_script("fbg_n08_udft_map122_uf_sto_0")
    specs = eventscan.scan_objects_verbatim(eb)
    by_slot = {s["donor_idx"]: s for s in specs}

    cask = next(s for s in specs if s["model"] == "GEO_ACC_F0_CSK")
    assert cask["graft_safety"] == "init_only"
    assert cask["instances"][0]["x"] == -250 and cask["instances"][0]["z"] == -571   # measured placement
    assert cask["pose"] == 1904 and cask["self_positions"] is True
    assert 2 not in cask["carry_tags"] and 24 in cask["player_tags_needed"]           # drop the dangling tag
    assert cask["entry_bytes"] == eventscan._entry_bytes(eb, cask["donor_idx"])       # VERBATIM
    pref = next(r for r in cask["refs"] if r["klass"] == "player")
    assert pref["op"] == 0x12 and pref["value"] == 23 and pref["tag"] == 24           # player BY ENTRY INDEX

    # the BBX is an arg-instanced row: ONE entry, three InitObject args, self-contained position.
    bbx = next(s for s in specs if s["model"] == "GEO_ACC_F0_BBX")
    assert bbx["graft_safety"] == "clean" and len(bbx["instances"]) == 3
    assert [i["arg"] for i in bbx["instances"]] == [128, 129, 130]

    # the player-entry-index guard: the controlled player (entry 23) is never carried as an object.
    assert eventscan._player_entry_index(EbScript.from_bytes(eb)) == 23
    assert 23 not in by_slot


def test_content_section_falls_back_to_commented_stub_when_empty():
    from ff9mapkit import extract
    assert extract._content_section("", 5, 7).lstrip().startswith("# [[gateway]]")
    assert extract._content_section("[[gateway]]\nto = 9", 0, 0).startswith("[[gateway]]")


def test_fieldtable_maps_known_fields_to_event_names():
    from ff9mapkit._fieldtable import FBG_TO_EVT
    assert len(FBG_TO_EVT) > 600
    assert FBG_TO_EVT["fbg_n21_grgr_map420_gr_cen_0"][1] == "EVT_GARGAN_GR_CEN_0"
    assert FBG_TO_EVT["fbg_n36_glgv_map792_gv_rm1_0"][1] == "EVT_GULUGU_GV_RM1_0"
