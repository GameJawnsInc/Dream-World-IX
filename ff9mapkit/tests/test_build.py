"""Phase-4 validation: the field.toml -> mod builder.

The example project (examples/vivi-hut/hut_int.field.toml) is the worked example AND the build
oracle: compiling it must reproduce the in-game-verified EVT_HUT_INT.eb script byte-for-byte,
emit the exact DictionaryPatch line, write the Session-9 dialogue .mes, and lay out a valid
background scene + walkmesh — all offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ff9mapkit.build import FieldProject, build_mod, validate
from ff9mapkit.config import LANGS, ModLayout
from ff9mapkit.scene import bgi, bgx

FIX = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).parents[1] / "examples" / "vivi-hut" / "hut_int.field.toml"


@pytest.fixture()
def built(tmp_path):
    proj = FieldProject.load(EXAMPLE)
    info = build_mod([proj], tmp_path, mod_name="FF9CustomMap", author="test")
    return tmp_path, info


def test_example_validates_clean():
    assert validate(FieldProject.load(EXAMPLE)) == []


def test_build_reproduces_hut_int_eb_byte_exact(built):
    out, _ = built
    eb = ModLayout(out).eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes()
    assert eb == (FIX / "hut_int-us.eb.bytes").read_bytes()


def test_build_writes_all_languages(built):
    out, _ = built
    L = ModLayout(out)
    for lang in LANGS:
        assert L.eb_path(lang, "EVT_HUT_INT.eb.bytes").is_file()


def test_build_dictionary_and_mes_and_description(built):
    out, info = built
    L = ModLayout(out)
    assert info["dictionary"] == ["FieldScene 4002 11 HUT_INT HUT_INT 1073"]
    assert L.dictionary_patch.read_text().strip() == "FieldScene 4002 11 HUT_INT HUT_INT 1073"
    assert L.mes_path("us", 1073).read_text(encoding="utf-8").strip() == \
        "_[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]"
    assert "<InstallationPath>FF9CustomMap</InstallationPath>" in L.mod_description.read_text()


def test_build_scene_and_walkmesh(built):
    out, _ = built
    fm = ModLayout(out).fieldmap_dir("FBG_N11_HUT_INT")
    # walkmesh round-trips and has the quad's 2 triangles
    raw = (fm / "FBG_N11_HUT_INT.bgi.bytes").read_bytes()
    wm = bgi.BgiWalkmesh.from_bytes(raw)
    assert wm.to_bytes() == raw and len(wm.tris) == 2
    # scene has both layers + a camera, and the PNGs were copied
    scene = bgx.BgxScene.from_file(fm / "FBG_N11_HUT_INT.bgx")
    assert [o.image for o in scene.overlays] == ["back.png", "floor.png"]
    assert len(scene.cameras) == 1
    assert (fm / "back.png").is_file() and (fm / "floor.png").is_file()


TWOCAM = """
[field]
id = 4003
name = "TWOCAM"
area = 11
text_block = 1073

[[camera]]
pitch = 40
yaw = 0
[[camera]]
pitch = 40
yaw = 30

[[camera_zone]]
to_camera = 1
zone = [[500, -150], [900, -150], [900, -550], [500, -550]]
[[camera_zone]]
to_camera = 0
zone = [[-900, -150], [-500, -150], [-500, -550], [-900, -550]]

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -500]
"""


@pytest.fixture()
def twocam(tmp_path):
    p = tmp_path / "twocam.field.toml"
    p.write_text(TWOCAM, encoding="utf-8")
    out = tmp_path / "mod"
    info = build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    return out, info


def test_multicam_validates_clean(tmp_path):
    p = tmp_path / "twocam.field.toml"
    p.write_text(TWOCAM, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []


def test_multicam_scene_has_two_cameras(twocam):
    out, _ = twocam
    scene = bgx.BgxScene.from_file(ModLayout(out).fieldmap_dir("FBG_N11_TWOCAM") / "FBG_N11_TWOCAM.bgx")
    assert len(scene.cameras) == 2


def test_multicam_eb_has_switch_zones(twocam):
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    out, _ = twocam
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_TWOCAM.eb.bytes").read_bytes())
    assert eb.to_bytes() == eb.data                       # valid round-trip
    # two type-1 region entries whose Range (tag 2) contains SetFieldCamera (0x7E)
    switch_regions = [e for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)
                      and any(ins.op == 0x7E for f in [e.func_by_tag(2)]
                              for ins in iter_code(eb.data, f.abs_start, f.abs_end))]
    assert len(switch_regions) == 2
    # Main_Init arms the switch (InitCode 0x07 for the load-time init entry)
    f0 = eb.entry(0).func_by_tag(0)
    assert any(ins.op == 0x07 for ins in iter_code(eb.data, f0.abs_start, f0.abs_end))


EVENTS = """
[field]
id = 4003
name = "EVENTROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[event]]                       # walk-in chest: give a Potion + a message, once
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]
give_item = [232, 1]
message = "Got a Potion!"

[[event]]                       # repeatable line
zone = [[-700, -400], [-300, -400], [-300, -800], [-700, -800]]
message = "A cool breeze blows through."
once = false
"""


def test_event_field_validates_and_builds(tmp_path):
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "ev.field.toml"
    p.write_text(EVENTS, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    L = ModLayout(out)
    eb = EbScript.from_bytes(L.eb_path("us", "EVT_EVENTROOM.eb.bytes").read_bytes())
    ops = [i.op for e in eb.entries if not e.empty for f in e.funcs
           for i in iter_code(eb.data, f.abs_start, f.abs_end)]
    assert 0x48 in ops                                          # AddItem from the chest event
    # both event messages land in the .mes (NPC-free field starts at TXID 500)
    mes = L.mes_path("us", 1073).read_text(encoding="utf-8")
    assert "Got a Potion!" in mes and "A cool breeze blows through." in mes
    # two event regions exist
    assert sum(1 for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)) == 2


STORY = """
[field]
id = 4003
name = "STORYROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1200, -100], [1200, -100], [1200, -1400], [-1200, -1400]]

[player]
spawn = [0, -300]

[[event]]                       # a switch that sets story flag 200
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]
set_flag = [200, 1]
message = "*click* something opened."

[[npc]]                         # only appears once flag 200 is set
name = "Guard"
preset = "vivi"
pos = [-500, -600]
dialogue = "You opened it!"
requires_flag = 200

[[gateway]]                     # door that unlocks once flag 200 is set
to = 100
entrance = 204
zone = [[-200, -1200], [200, -1200], [200, -1350], [-200, -1350]]
requires_flag = 200
"""


def test_story_flag_branching_builds(tmp_path):
    from ff9mapkit.content import region
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "story.field.toml"
    p.write_text(STORY, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_STORYROOM.eb.bytes").read_bytes())
    gate = region.flag_gate(region.GLOB_BOOL, 200)
    # the NPC's Init is gated by flag 200
    npc_e = next(e for e in eb.entries if not e.empty and e.func_by_tag(3) and e.index != 0)
    init = npc_e.func_by_tag(0)
    assert eb.data[init.abs_start:init.abs_start + 8] == gate
    # a gateway region (Field 0x2B in Range) is gated by flag 200
    gw = next(e for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)
              and any(i.op == 0x2B for i in iter_code(eb.data, e.func_by_tag(2).abs_start,
                                                      e.func_by_tag(2).abs_end)))
    grng = gw.func_by_tag(2)
    assert eb.data[grng.abs_start:grng.abs_start + 8] == gate
    # the event sets flag 200 (SetVar GlobBool 200 = 1 in some region's Range)
    allbytes = eb.to_bytes()
    assert region.set_var(region.GLOB_BOOL, 200, 1) in allbytes


THREECAM = """
[field]
id = 4003
name = "TRICAM"
area = 11
text_block = 1073

[[camera]]
pitch = 45
yaw = 0
[[camera]]
pitch = 45
yaw = 25
[[camera]]
pitch = 45
yaw = -25

[[camera_zone]]
to_camera = 0
zone = [[-1100, -100], [-400, -100], [-400, -900], [-1100, -900]]
[[camera_zone]]
to_camera = 1
zone = [[-300, -100], [300, -100], [300, -900], [-300, -900]]
[[camera_zone]]
to_camera = 2
zone = [[400, -100], [1100, -100], [1100, -900], [400, -900]]

[walkmesh]
quad = [[-1200, -50], [1200, -50], [1200, -1000], [-1200, -1000]]

[player]
spawn = [0, -300]

[encounter]
scene = 67
"""


def test_threecam_builds_with_restore(tmp_path):
    from ff9mapkit.content import region
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "tri.field.toml"
    p.write_text(THREECAM, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    L = ModLayout(out)
    scene = bgx.BgxScene.from_file(L.fieldmap_dir("FBG_N11_TRICAM") / "FBG_N11_TRICAM.bgx")
    assert len(scene.cameras) == 3
    eb = EbScript.from_bytes(L.eb_path("us", "EVT_TRICAM.eb.bytes").read_bytes())
    assert eb.to_bytes() == eb.data
    # three type-1 switch regions, each with SETCAM
    sw = [e for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)
          and any(i.op == 0x7E for i in iter_code(eb.data, e.func_by_tag(2).abs_start,
                                                  e.func_by_tag(2).abs_end))]
    assert len(sw) == 3
    # after-battle restore in tag-10: cond_eq(flag, K) + SetFieldCamera(K) for cams 1 and 2
    t10 = eb.entry(0).func_by_tag(10)
    body = eb.data[t10.abs_start:t10.abs_end]
    from ff9mapkit.eb import opcodes
    assert region.cond_eq(region.GLOB_UINT8, 24, 1) in body and opcodes.set_field_camera(1) in body
    assert region.cond_eq(region.GLOB_UINT8, 24, 2) in body


def test_validate_rejects_low_area(tmp_path):
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4002\nname="X"\narea=7\n[camera]\npitch=48\n', encoding="utf-8")
    problems = validate(FieldProject.load(bad))
    assert any("area must be >= 10" in p for p in problems)
