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


def test_cutscene_director_gate_and_advance_in_built_eb(tmp_path):
    """The STORY-EVENT DIRECTOR (#13): a [cutscene] gated on a beat (requires_scenario) that advances the
    story at scene end (set_scenario) -- the gate + advance bytes land in the built .eb; a plain cutscene
    has neither (byte-level; the shapes are the [startup]/[[on_entry]]-proven ones)."""
    import struct as _s
    from ff9mapkit import build as B
    cam = "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    base = '[field]\nid = 30000\nname = "DIR"\narea = 11' + cam
    gate_sig = bytes([0x05, 0xDC, 0x00, 0x7D]) + _s.pack("<H", 2600)   # SC == 2600 (cond_eq shape)
    adv_sig = bytes([0x05, 0xDC, 0x00, 0x7D]) + _s.pack("<H", 2610)    # SC := 2610 (set_var shape)
    def _eb(txt, tag):
        f = tmp_path / f"{tag}.field.toml"
        f.write_text(txt, encoding="utf-8")
        p = B.FieldProject.load(f)
        assert validate(p) == []
        return B.build_script(p, "us", {}, cutscene_txids=[500])
    plain = _eb(base + '\n[cutscene]\nsteps = [ { say = "hello" } ]\n', "plain")
    gated = _eb(base + '\n[cutscene]\nrequires_scenario = 2600\nset_scenario = 2610\n'
                       'steps = [ { say = "hello" } ]\n', "gated")
    assert gate_sig in gated and adv_sig in gated
    assert gate_sig not in plain and adv_sig not in plain
    # the CAST flavor (the conductor) gates + advances too (the same early-return prologue on its entry)
    cast = _eb(base + '\n[[npc]]\nname = "vivi"\npreset = "vivi"\npos = [0, -300]\ndialogue = "..."\n'
                      '\n[cutscene]\nactors = ["vivi"]\nrequires_scenario = 2600\nset_scenario = 2610\n'
                      'steps = [ { say = "hi" } ]\n', "cast")
    assert gate_sig in cast and adv_sig in cast


def test_cutscene_dispatch_plural_blocks(tmp_path):
    """[[cutscene]] (#13 v2): several beat-gated scenes per field. A one-block [[cutscene]] builds
    byte-identical to the legacy [cutscene] singleton; a two-scene dispatch emits BOTH gates + BOTH
    advances with DISTINCT auto once-flags (the cutscene auto band + k)."""
    import struct as _s
    from ff9mapkit import build as B
    from ff9mapkit.content import region as R
    from ff9mapkit.content.cutscene import DEFAULT_CUTSCENE_FLAG
    cam = "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    base = '[field]\nid = 30000\nname = "DISP"\narea = 11' + cam
    def _eb(txt, tag, txids):
        f = tmp_path / f"{tag}.field.toml"
        f.write_text(txt, encoding="utf-8")
        p = B.FieldProject.load(f)
        assert validate(p) == []
        return B.build_script(p, "us", {}, cutscene_txids=txids)
    one_single = _eb(base + '\n[cutscene]\nsteps = [ { say = "hello" } ]\n', "sng", [500])
    one_plural = _eb(base + '\n[[cutscene]]\nsteps = [ { say = "hello" } ]\n', "pl1", [500])
    assert one_single == one_plural                        # the singleton is exactly the one-block case
    disp = _eb(base + '\n[[cutscene]]\nrequires_scenario = 2600\nset_scenario = 2610\nsteps = [ { say = "one" } ]\n'
                      '\n[[cutscene]]\nrequires_scenario = 2610\nset_scenario = 2620\nsteps = [ { say = "two" } ]\n',
               "disp", [500, 501])
    for v in (2600, 2610, 2620):                           # both gates + both advances land
        assert bytes([0x05, 0xDC, 0x00, 0x7D]) + _s.pack("<H", v) in disp
    assert R.set_var(R.GLOB_BOOL, DEFAULT_CUTSCENE_FLAG, 1) in disp      # block 0's auto once-flag
    assert R.set_var(R.GLOB_BOOL, DEFAULT_CUTSCENE_FLAG + 1, 1) in disp  # block 1's -- distinct, never shared


def test_validate_cutscene_dispatch_rules(tmp_path):
    """The dispatch rule: pairwise-distinct gates (same-gate / double-ungated pairs rejected). Several
    CAST scenes coexist -- the shared tag-state removed the old one-conductor limit."""
    cam = "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    base = '[field]\nid = 30000\nname = "DISP"\narea = 11' + cam
    npc = '\n[[npc]]\nname = "a"\npreset = "vivi"\npos = [0, -300]\ndialogue = "."\n' \
          '\n[[npc]]\nname = "b"\npreset = "steiner"\npos = [100, -300]\ndialogue = "."\n'
    def _probs(txt, tag):
        f = tmp_path / f"{tag}.field.toml"
        f.write_text(txt, encoding="utf-8")
        return validate(FieldProject.load(f))
    same = _probs(base + '\n[[cutscene]]\nrequires_scenario = 2600\nsteps = [ { say = "a" } ]\n'
                         '\n[[cutscene]]\nrequires_scenario = 2600\nsteps = [ { say = "b" } ]\n', "same")
    assert any("pairwise-distinct" in p for p in same)
    ungated = _probs(base + '\n[[cutscene]]\nsteps = [ { say = "a" } ]\n'
                            '\n[[cutscene]]\nsteps = [ { say = "b" } ]\n', "ung")
    assert any("both UNGATED" in p for p in ungated)
    two_cast = _probs(base + npc +
                      '\n[[cutscene]]\nrequires_scenario = 2600\nactors = ["a"]\nsteps = [ { say = "x" } ]\n'
                      '\n[[cutscene]]\nrequires_scenario = 2610\nactors = ["b"]\nsteps = [ { say = "y" } ]\n',
                      "cast")
    assert two_cast == []      # several CAST scenes coexist (shared tag-state; no one-conductor rule)


def test_validate_cutscene_director_keys(tmp_path):
    cam = "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    base = '[field]\nid = 30000\nname = "DIR"\narea = 11' + cam
    bad = tmp_path / "bad.field.toml"
    bad.write_text(base + '\n[cutscene]\nrequires_scenario = "NotAPlace"\nsteps = [ { say = "x" } ]\n',
                   encoding="utf-8")
    assert any("requires_scenario" in p for p in validate(FieldProject.load(bad)))
    both = tmp_path / "both.field.toml"
    both.write_text(base + '\n[cutscene]\nrequires_flag = 8600\nrequires_flag_clear = 8601\n'
                           'steps = [ { say = "x" } ]\n', encoding="utf-8")
    assert any("not both" in p for p in validate(FieldProject.load(both)))


def test_validate_rejects_requires_flag_and_clear_together(tmp_path):
    """requires_flag + requires_flag_clear on the SAME block silently drops the clear condition in
    _gate_of (it checks requires_flag first and returns) -- validate() must reject the combo on every
    block type that reads it, the same way it already rejects it on [[choice]] options and [cutscene]."""
    cam = "\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    base = '[field]\nid = 30000\nname = "GATE"\narea = 11' + cam
    both = base + (
        '\n[[npc]]\nname = "guard"\npos = [0, -300]\nrequires_flag = 8600\nrequires_flag_clear = 8601\n'
        '\n[[gateway]]\nto = 4000\nzone = [[0,0],[10,0],[10,10],[0,10]]\n'
        'requires_flag = 8600\nrequires_flag_clear = 8601\n'
        '\n[[event]]\nzone = [[0,0],[10,0],[10,10],[0,10]]\nmessage = "x"\n'
        'requires_flag = 8600\nrequires_flag_clear = 8601\n'
        '\n[[chest]]\npos = [0, -300]\ngil = 100\nflag = 8700\n'
        'requires_flag = 8600\nrequires_flag_clear = 8601\n'
        '\n[[prop]]\nprop = "chest"\npos = [0, -300]\nrequires_flag = 8600\nrequires_flag_clear = 8601\n'
        '\n[[coop]]\nset_flag = 8710\nzone = [[0,0],[10,0],[10,10],[0,10]]\n'
        'requires_flag = 8600\nrequires_flag_clear = 8601\n'
    )
    f = tmp_path / "both.field.toml"
    f.write_text(both, encoding="utf-8")
    problems = validate(FieldProject.load(f))
    for label in ("[[npc]] 'guard'", "[[gateway]]", "[[event]]", "[[chest]] #0",
                  "[[prop]] 'chest'", "[[coop]] gate '#0'"):
        assert any(p.startswith(label) and "can't have BOTH requires_flag and requires_flag_clear" in p
                   for p in problems), f"missing gate-conflict rejection for {label}: {problems}"


def test_validate_rejects_dangling_gateway_carry_player_calls(tmp_path):
    """#3 (FORK_FIDELITY.md #2b): a [[gateway_carry]] player-call door's RunScript(player, T) must resolve to a
    grafted [[player_func]] -- a dangling call is a walk-up softlock, so validate() blocks it. With the matching
    [[player_func]] the check passes."""
    cam = "\n\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    (tmp_path / "door.bin").write_bytes(b"\x01\x00")
    (tmp_path / "pf.bin").write_bytes(b"\x04")
    base = '[field]\nid = 30000\nname = "DOOR"\narea = 11' + cam + \
           '\n[[gateway_carry]]\nbin = "door.bin"\ndonor_entry = 1\nplayer_calls = [13]\ndonor_player_entry = 3\n'
    bad = tmp_path / "bad.field.toml"
    bad.write_text(base, encoding="utf-8")
    assert any("dangling player call" in p for p in validate(FieldProject.load(bad)))
    ok = tmp_path / "ok.field.toml"
    ok.write_text(base + '\n[[player_func]]\nbin = "pf.bin"\ndonor_tag = 13\nsafety = "walk"\n'
                         'donor_init_packs = []\n', encoding="utf-8")
    assert not any("dangling player call" in p for p in validate(FieldProject.load(ok)))


def test_validate_rejects_out_of_range_field_id(tmp_path):
    """A field id past the engine's Int16 fldMapNo cap (32767) is rejected (it registers unreachable AND can
    break DictionaryPatch parsing -> a New-Game black screen, as a 620729 deploy did 2026-06-15). A valid
    scratch id is fine."""
    cam = "\n\n[camera]\npitch = 48.0\ndistance = 480.0\nfov = 46.0\n"
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid = 620729\nname = "BADID"\narea = 11' + cam, encoding="utf-8")
    assert any("out of range 1-32767" in p for p in validate(FieldProject.load(bad)))
    ok = tmp_path / "ok.field.toml"
    ok.write_text('[field]\nid = 30000\nname = "OKID"\narea = 11' + cam, encoding="utf-8")
    assert not any("out of range 1-32767" in p for p in validate(FieldProject.load(ok)))


def test_build_reproduces_hut_int_eb_byte_exact(built):
    # The hut script EMBEDS the blank field (game-derived), so we can't ship its bytes as a golden.
    # Instead we compare the fresh build's SHA-256 to the manifest (a hash isn't a redistribution of
    # the bytes) -- still a byte-exact regression guard. See ff9mapkit/provision.py.
    from ff9mapkit import provision
    out, _ = built
    eb = ModLayout(out).eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes()
    assert provision.sha256(eb) == provision.load_manifest()["goldens"]["EVT_HUT_INT.eb.bytes/us"]


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


def test_field_location_emits_locationname_directive(tmp_path):
    """[field] location authors the menu/title place-name via a `LocationName <id> <title>` DictionaryPatch
    directive (engine: DataPatchers.CustomLocationNames -> FF9TextTool.FieldLocationName). A multi-word title
    (spaces, '/') survives, and the directive line follows the field's own FieldScene line in the written file."""
    proj = FieldProject.load(EXAMPLE)
    proj.field["location"] = "  Prima Vista/Cargo Room  "   # surrounding/interior whitespace is collapsed
    info = build_mod([proj], tmp_path, mod_name="FF9CustomMap")
    dp = ModLayout(tmp_path).dictionary_patch.read_text(encoding="utf-8")
    lines = [l for l in dp.splitlines() if l.strip()]
    assert f"LocationName {proj.id} Prima Vista/Cargo Room" in lines
    i = next(k for k, l in enumerate(lines) if l.startswith(f"FieldScene {proj.id} "))
    assert lines[i + 1] == f"LocationName {proj.id} Prima Vista/Cargo Room"   # right after its FieldScene line
    assert dp.count("LocationName ") == 1
    # build_mod also surfaces it in info["location_lines"] -- deploy_field.py appends THESE to the stacked live
    # DictionaryPatch (it reconstructs from info, not by copying the built file, so it must see the directive).
    assert info["location_lines"] == [f"LocationName {proj.id} Prima Vista/Cargo Room"]


def test_field_location_absent_emits_no_directive(built):
    out, info = built
    assert "LocationName " not in ModLayout(out).dictionary_patch.read_text(encoding="utf-8")
    assert info["location_lines"] == []


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


SEQROOM = """
[field]
id = 4003
name = "SEQROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[object]]
bin = "f.object0.bin"
kind = "prop"
donor_idx = 7
instances = [{ arg = 0, x = 0, z = 0 }]
seqs = [{ entry = 9, bin = "f.object0.seq9.bin" }]
"""


def test_seq_helper_closure_lint(tmp_path):
    # the STARTSEQ-helper closure lint guards (docs/OBJECT_CARRY.md S2 v1.5): a benign type-1 helper
    # validates clean; an unsafe (cutscene) body, a missing sidecar, and a double-arm are all errors.
    import struct
    from ff9mapkit.eb import opcodes
    init = opcodes.encode(0x2F, 133, 0) + opcodes.encode(0x33, 1872) + opcodes.RETURN   # SetModel + pose
    loop = opcodes.encode(0x43, 9) + opcodes.RETURN                                     # STARTSEQ(9)
    obj = bytes([0, 2]) + struct.pack("<HH", 0, 8) + struct.pack("<HH", 1, 8 + len(init)) + init + loop
    (tmp_path / "f.object0.bin").write_bytes(obj)
    p = tmp_path / "f.field.toml"
    p.write_text(SEQROOM, encoding="utf-8")
    benign = bytes([1, 1]) + struct.pack("<HH", 0, 4) + opcodes.RETURN
    (tmp_path / "f.object0.seq9.bin").write_bytes(benign)
    assert validate(FieldProject.load(p)) == []                                        # benign -> clean
    (tmp_path / "f.object0.seq9.bin").write_bytes(                                      # MoveCamera -> error
        bytes([1, 1]) + struct.pack("<HH", 0, 4) + opcodes.encode(0x6F, 0, 0, 0, 0, 0, 0) + opcodes.RETURN)
    assert any("cutscene op MoveCamera" in x for x in validate(FieldProject.load(p)))
    (tmp_path / "f.object0.seq9.bin").unlink()                                          # missing -> error
    assert any("seqs helper sidecar not found" in x for x in validate(FieldProject.load(p)))


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


TRADE = """
[field]
id = 4003
name = "TRADEROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[event]]                       # a trade: take a Dagger, give a Potion
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]
remove_item = ["Dagger", 1]
give_item = ["Potion", 1]
message = "Traded!"

[[event]]                       # a pure consume: take an Ore, no give (remove_item is a valid sole action)
zone = [[-700, -400], [-300, -400], [-300, -800], [-700, -800]]
remove_item = ["Ore", 2]
once = false
"""


def test_event_remove_item_validates_and_builds(tmp_path):
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "trade.field.toml"
    p.write_text(TRADE, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []               # remove_item is a valid action (even alone)
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_TRADEROOM.eb.bytes").read_bytes())
    ops = [i.op for e in eb.entries if not e.empty for f in e.funcs
           for i in iter_code(eb.data, f.abs_start, f.abs_end)]
    assert 0x49 in ops and 0x48 in ops                        # RemoveItem (the trade) + AddItem


def test_event_remove_item_unknown_name_is_caught(tmp_path):
    p = tmp_path / "bad.field.toml"
    p.write_text(TRADE.replace('["Dagger", 1]', '["Notathing", 1]'), encoding="utf-8")
    assert any("remove_item" in x for x in validate(FieldProject.load(p)))


STARTSTATE = """
[field]
id = 4003
name = "ENTRYROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[start_inventory]
items = [["Potion", 20], ["Phoenix Down", 5], ["Potion", 5], ["Tent", 3]]

[[equipment]]
character = "steiner"
weapon = "Excalibur"
armor = "Genji Armor"

[[equipment]]
character = "vivi"
weapon = "Mace of Zeus"
"""


def test_build_emits_start_state_csvs(tmp_path):
    # [start_inventory]/[[equipment]] on the entry field -> mod-global CSVs in the mod root (not field bytes).
    p = tmp_path / "entry.field.toml"
    p.write_text(STARTSTATE, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    res = build_mod([FieldProject.load(p)], out)
    L = ModLayout(out.resolve())
    inv = L.initial_items_csv.read_text(encoding="utf-8")
    assert "236;25;# Potion" in inv and "240;5;# PhoenixDown" in inv and "253;3;# Tent" in inv  # dup Potion summed
    eqp = L.default_equipment_csv.read_text(encoding="utf-8")
    assert "Steiner;3;28;" in eqp and "Vivi;1;78;" in eqp and "Zidane" not in eqp               # partial delta
    # the highest-wins / shadow caveat is surfaced as a build warning
    assert any("highest-priority-wins" in w.lower() or "shadow" in w.lower() for w in res["warnings"])


def test_build_warns_global_block_on_multiple_fields(tmp_path):
    a = STARTSTATE.replace('name = "ENTRYROOM"', 'name = "A"')
    b = STARTSTATE.replace('name = "ENTRYROOM"', 'name = "B"').replace("id = 4003", "id = 4004")
    pa, pb = tmp_path / "a.toml", tmp_path / "b.toml"
    pa.write_text(a, encoding="utf-8")
    pb.write_text(b, encoding="utf-8")
    res = build_mod([FieldProject.load(pa), FieldProject.load(pb)], tmp_path / "mod2")
    assert any("mod-GLOBAL" in w and "ENTRY" in w for w in res["warnings"])   # only the entry field should carry it


def test_validate_catches_bad_start_state(tmp_path):
    bad = (STARTSTATE.replace('["Phoenix Down", 5]', '["Notathing", 1]')
           .replace('character = "vivi"', 'character = "nobody"'))
    p = tmp_path / "bad.toml"
    p.write_text(bad, encoding="utf-8")
    probs = validate(FieldProject.load(p))
    assert any("start_inventory" in x for x in probs) and any("equipment" in x for x in probs)


def test_build_no_blocks_writes_no_start_state_csv(tmp_path):
    # a field WITHOUT the blocks emits NO CSV (the mod stays byte-identical for existing fields)
    plain = STARTSTATE[:STARTSTATE.index("[start_inventory]")]
    p = tmp_path / "plain.toml"
    p.write_text(plain, encoding="utf-8")
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out)
    L = ModLayout(out.resolve())
    assert not L.initial_items_csv.exists() and not L.default_equipment_csv.exists()


def test_build_entry_project_flags_non_entry_block(tmp_path):
    # the PRECISE (campaign) lint: a block on a NON-entry member is warned + ignored, nothing emitted
    entry_txt = STARTSTATE[:STARTSTATE.index("[start_inventory]")].replace('name = "ENTRYROOM"', 'name = "ENTRY"')
    other_txt = STARTSTATE.replace('name = "ENTRYROOM"', 'name = "OTHER"').replace("id = 4003", "id = 4004")
    pe, po = tmp_path / "e.toml", tmp_path / "o.toml"
    pe.write_text(entry_txt, encoding="utf-8")
    po.write_text(other_txt, encoding="utf-8")
    entry, other = FieldProject.load(pe), FieldProject.load(po)
    res = build_mod([entry, other], tmp_path / "mod", entry_project=entry)
    assert any("NON-entry" in w and "OTHER" in w for w in res["warnings"])
    assert not ModLayout((tmp_path / "mod").resolve()).initial_items_csv.exists()   # non-entry block ignored


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
    # the NPC is gated by flag 200 AT THE CALL SITE (the OBJECT-INIT GATE LAW): its Init stays
    # unconditional; Main_Init guards the InitObject
    from ff9mapkit.eb import opcodes as _opc
    npc_e = next(e for e in eb.entries if not e.empty and e.func_by_tag(3) and e.index != 0)
    guard = region.guarded_call([(region.cond_truthy(region.GLOB_BOOL, 200), True)],
                                _opc.init_object(npc_e.index, 0))
    assert guard in eb.data
    init = npc_e.func_by_tag(0)
    assert eb.data[init.abs_start:init.abs_start + 2] == b"\x05\xd9"    # first op = the position write
    # a gateway region (Field 0x2B in Range) is gated by flag 200
    gw = next(e for e in eb.entries if not e.empty and e.type == 1 and e.func_by_tag(2)
              and any(i.op == 0x2B for i in iter_code(eb.data, e.func_by_tag(2).abs_start,
                                                      e.func_by_tag(2).abs_end)))
    grng = gw.func_by_tag(2)
    assert eb.data[grng.abs_start:grng.abs_start + 8] == gate
    # the event sets flag 200 (SetVar GlobBool 200 = 1 in some region's Range)
    allbytes = eb.to_bytes()
    assert region.set_var(region.GLOB_BOOL, 200, 1) in allbytes


SAVEPOINT = """
[field]
id = 4003
name = "SAVEROOM"
area = 11
text_block = 1073

[camera]
pitch = 45

[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]

[player]
spawn = [0, -300]

[[prop]]                        # the composite: moogle + book co-located at one (x, z)
prop = "save_point"
pos = [-100, -600]
"""


def test_save_point_composite_places_both_parts(tmp_path):
    """`prop = "save_point"` expands to BOTH co-located parts (moogle 2904 + book 1872), not one object."""
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    from ff9mapkit import prop_archetypes as PA
    p = tmp_path / "save.field.toml"
    p.write_text(SAVEPOINT, encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out, mod_name="FF9CustomMap")
    eb = EbScript.from_bytes(ModLayout(out).eb_path("us", "EVT_SAVEROOM.eb.bytes").read_bytes())
    SET_STAND = 0x33
    stand_poses = set()
    for e in eb.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if not f0:
            continue
        for ins in iter_code(eb.data, f0.abs_start, f0.abs_end):
            if ins.op == SET_STAND:
                stand_poses.add(int.from_bytes(eb.data[ins.off + 2:ins.off + 4], "little"))
    expected = {pose for _, pose, _, _ in PA.resolve_composite("save_point")}   # {2904 moogle, 1872 book}
    assert expected <= stand_poses, (expected, stand_poses)


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


_COMBINED = """
[field]
id = 4003
name = "SPLITROOM"
area = 11
text_block = 1073
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[[layers]]
image = "floor.png"
z = 4000
[[npc]]
name = "guard"
preset = "vivi"
pos = [-400, -600]
dialogue = "Halt!"
requires_flag = 200
[[gateway]]
name = "north"
to = 100
entrance = 204
zone = [[-200, -1200], [200, -1200], [200, -1350], [-200, -1350]]
[[event]]
name = "lever"
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]
set_flag = [200, 1]
message = "click"
[player]
spawn = [0, -300]
"""
_LOGIC = """
[field]
id = 4003
name = "SPLITROOM"
area = 11
text_block = 1073
[[npc]]
name = "guard"
preset = "vivi"
dialogue = "Halt!"
requires_flag = 200
[[gateway]]
name = "north"
to = 100
entrance = 204
[[event]]
name = "lever"
set_flag = [200, 1]
message = "click"
"""
_SCENE = """
[camera]
pitch = 45
[walkmesh]
quad = [[-1000, -100], [1000, -100], [1000, -1000], [-1000, -1000]]
[[layers]]
image = "floor.png"
z = 4000
[[npc]]
name = "guard"
pos = [-400, -600]
[[gateway]]
name = "north"
zone = [[-200, -1200], [200, -1200], [200, -1350], [-200, -1350]]
[[event]]
name = "lever"
zone = [[300, -400], [700, -400], [700, -800], [300, -800]]
[player]
spawn = [0, -300]
"""


def _png(path, w=384, h=448):
    from PIL import Image
    Image.new("RGBA", (w, h), (10, 20, 30, 255)).save(path)


def test_two_file_split_equals_single_file(tmp_path):
    """The Blender split (scene.toml spatial + field.toml logic, merged by name) must build the SAME
    bytes as the equivalent single-file project -- the whole correctness guarantee of the overlay."""
    c = tmp_path / "combined"; c.mkdir(); _png(c / "floor.png")
    (c / "x.field.toml").write_text(_COMBINED, encoding="utf-8")
    build_mod([FieldProject.load(c / "x.field.toml")], c / "mod")

    s = tmp_path / "split"; s.mkdir(); _png(s / "floor.png")
    (s / "x.field.toml").write_text(_LOGIC, encoding="utf-8")
    (s / "x.scene.toml").write_text(_SCENE, encoding="utf-8")     # auto-discovered sibling
    build_mod([FieldProject.load(s / "x.field.toml")], s / "mod")

    L1, L2 = ModLayout(c / "mod"), ModLayout(s / "mod")
    for lang in LANGS:
        assert L1.eb_path(lang, "EVT_SPLITROOM.eb.bytes").read_bytes() == \
            L2.eb_path(lang, "EVT_SPLITROOM.eb.bytes").read_bytes()
    fm1, fm2 = L1.fieldmap_dir("FBG_N11_SPLITROOM"), L2.fieldmap_dir("FBG_N11_SPLITROOM")
    assert (fm1 / "FBG_N11_SPLITROOM.bgx").read_text() == (fm2 / "FBG_N11_SPLITROOM.bgx").read_text()
    assert (fm1 / "FBG_N11_SPLITROOM.bgi.bytes").read_bytes() == (fm2 / "FBG_N11_SPLITROOM.bgi.bytes").read_bytes()
    assert L1.mes_path("us", 1073).read_text() == L2.mes_path("us", 1073).read_text()


def test_scene_merge_unit():
    from ff9mapkit.build import _merge_scene
    base = {"field": {"id": 4003}, "npc": [{"name": "g", "dialogue": "hi"}],
            "gateway": [{"name": "d", "to": 100}]}
    scene = {"camera": {"pitch": 45}, "player": {"spawn": [0, 0]},
             "npc": [{"name": "g", "pos": [1, 2]}, {"name": "extra", "pos": [3, 4]}],
             "gateway": [{"name": "d", "zone": [[0, 0]]}]}
    m = _merge_scene(base, scene)
    assert m["camera"] == {"pitch": 45} and m["player"] == {"spawn": [0, 0]}
    g = next(n for n in m["npc"] if n["name"] == "g")
    assert g["dialogue"] == "hi" and g["pos"] == [1, 2]          # logic + spatial joined by name
    assert any(n["name"] == "extra" for n in m["npc"])           # scene-only entity appended
    assert m["gateway"][0]["to"] == 100 and m["gateway"][0]["zone"] == [[0, 0]]


def test_explicit_scene_file_reference(tmp_path):
    s = tmp_path; _png(s / "floor.png")
    (s / "logic.field.toml").write_text(_LOGIC + '\n[scene]\nfile = "myscene.toml"\n', encoding="utf-8")
    (s / "myscene.toml").write_text(_SCENE, encoding="utf-8")
    proj = FieldProject.load(s / "logic.field.toml")
    assert validate(proj) == []                                  # merged project is complete
    assert any(n.get("pos") == [-400, -600] for n in proj.raw["npc"])


_LINT_BASE = """
[field]
id = 4003
name = "X"
area = 11
[camera]
pitch = 45
[walkmesh]
quad = [[-500, -100], [500, -100], [500, -600], [-500, -600]]
[player]
spawn = [0, -300]
"""


def _lint(tmp_path, body):
    from ff9mapkit.build import FieldProject, lint_logic
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE + body, encoding="utf-8")
    return lint_logic(FieldProject.load(p))


def test_lint_dangling_requires_flag(tmp_path):
    lints = _lint(tmp_path, '[[npc]]\nname="g"\npreset="vivi"\npos=[0,-200]\n'
                            'dialogue="hi"\nrequires_flag=300\n')
    assert any("requires flag 300" in m and "no event sets it" in m for m in lints)


def test_lint_satisfied_flag_is_clean(tmp_path):
    lints = _lint(tmp_path,
                  '[[npc]]\nname="g"\npreset="vivi"\npos=[0,-200]\ndialogue="hi"\nrequires_flag=200\n'
                  '[[event]]\nname="e"\nzone=[[100,-100],[200,-100],[200,-200],[100,-200]]\n'
                  'set_flag=[200,1]\nonce=false\n')
    assert lints == []                                          # 200 is set by the event -> no warning


def test_lint_auto_once_skips_an_authored_flag_in_the_auto_band(tmp_path):
    # An authored flag sitting AT the event auto base is SKIPPED by the allocator (no aliasing, no
    # clash lint) -- the defaulted once-event takes the next free index, so the NPC's gate is simply
    # dangling (nothing sets it) and the dangling lint says so.
    from ff9mapkit.content.event import EVENT_FLAG_BASE
    lints = _lint(tmp_path,
                  f'[[npc]]\nname="g"\npreset="vivi"\npos=[0,-200]\ndialogue="hi"\n'
                  f'requires_flag={EVENT_FLAG_BASE}\n'
                  '[[event]]\nname="e"\nzone=[[100,-100],[200,-100],[200,-200],[100,-200]]\nmessage="x"\n')
    assert not any("clash" in m for m in lints)
    assert any("no event sets it" in m and str(EVENT_FLAG_BASE) in m for m in lints)


def test_flag_alloc_single_field_bands_sit_in_the_safe_band():
    # base=None allocates each category from its own safe-band auto band (flags.AUTO_*_BASE): every
    # index provably clear of ALL real-FF9 usage (the pre-b18 8000/8100/8200/8300 bands were below
    # FIRST_SAFE_FLAG -- 8300+ sat INSIDE the stock Mognet mailbox slot bytes).
    from ff9mapkit import flags as F
    from ff9mapkit.build import _FlagAlloc
    from ff9mapkit.content.event import EVENT_FLAG_BASE
    from ff9mapkit.content.cutscene import DEFAULT_CUTSCENE_FLAG
    from ff9mapkit.content.choice import CHOICE_FLAG_BASE
    from ff9mapkit.content.onentry import ONENTRY_FLAG_BASE
    from ff9mapkit.content.ate import ATE_FLAG_BASE
    a = _FlagAlloc(None)
    assert (a.event(0), a.event(3)) == (EVENT_FLAG_BASE, EVENT_FLAG_BASE + 3)
    assert a.cutscene() == DEFAULT_CUTSCENE_FLAG
    assert (a.choice(0), a.choice(5)) == (CHOICE_FLAG_BASE, CHOICE_FLAG_BASE + 5)
    assert (a.on_entry(0), a.ate()) == (ONENTRY_FLAG_BASE, ATE_FLAG_BASE)
    # regression (the 2026-07-26 audit): every band's every index is safe -- in [FIRST_SAFE_FLAG,
    # CHOICE_SCRATCH_FLOOR), not reserved, and in particular NOT in the stock Mognet mailbox
    # (8192-8367), lock band (8376-8511), or read-mail payload (8512-8711).
    bands = (EVENT_FLAG_BASE, DEFAULT_CUTSCENE_FLAG, CHOICE_FLAG_BASE, ONENTRY_FLAG_BASE, ATE_FLAG_BASE)
    for base in bands:
        for idx in range(base, base + F.AUTO_BAND_WIDTH):
            assert F.is_safe_custom(idx), f"auto index {idx} is not provably safe"
    # the five bands are pairwise disjoint (the pre-b18 [ate]/on_entry bands BOTH sat at 8300)
    spans = [set(range(b, b + F.AUTO_BAND_WIDTH)) for b in bands]
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            assert spans[i].isdisjoint(spans[j])
    # clear of the behavior compiler's default GLOB flag band (a field can host both systems)
    from ff9mapkit.content.behavior import Blackboard
    bb = Blackboard()
    behavior_band = set(range(bb.flag_band[0], bb.flag_band[1] + 1))
    for s in spans:
        assert s.isdisjoint(behavior_band)


def test_flag_alloc_skips_the_projects_authored_flags():
    # collision avoidance: an authored safe-band flag inside an auto band is never handed out. The
    # allocation is a pure function of (i, reserved) -> lint_logic mirrors build_script exactly.
    import pytest
    from ff9mapkit.build import BuildError, _FlagAlloc
    from ff9mapkit.content.event import EVENT_FLAG_BASE
    a = _FlagAlloc(None, reserved={EVENT_FLAG_BASE, EVENT_FLAG_BASE + 2})
    assert (a.event(0), a.event(1), a.event(2)) == (
        EVENT_FLAG_BASE + 1, EVENT_FLAG_BASE + 3, EVENT_FLAG_BASE + 4)
    # band exhaustion raises (never silently spills into the next lane's band / unsafe space)
    from ff9mapkit import flags as F
    full = _FlagAlloc(None, reserved=set(range(EVENT_FLAG_BASE, EVENT_FLAG_BASE + F.AUTO_BAND_WIDTH)))
    with pytest.raises(BuildError):
        full.event(0)


def test_flag_alloc_for_project_reserves_logic_add_indices():
    # [[logic_add]]'s explicit `guard`/`flag` sit outside collect_safe_flag_indices' section walk;
    # for_project must reserve them so a defaulted block on a verbatim fork can't alias them.
    from ff9mapkit.build import _FlagAlloc
    from ff9mapkit.content.event import EVENT_FLAG_BASE

    class _P:                                  # duck-typed project (raw + flag_base is all for_project reads)
        flag_base = None
        raw = {"logic_add": [{"kind": "set_flag", "flag": EVENT_FLAG_BASE,
                              "guard": EVENT_FLAG_BASE + 1}]}
    a = _FlagAlloc.for_project(_P())
    assert a.event(0) == EVENT_FLAG_BASE + 2
    # [[qte]]: the explicit finale flag AND the result Int16's 16-bit span are reserved (result is a
    # BYTE offset -- a safe-band result word overlaps 16 bit-flags)
    res_byte = EVENT_FLAG_BASE // 8 + 1                    # a word landing inside the event auto band
    span = set(range(res_byte * 8, res_byte * 8 + 16))

    class _Q:
        flag_base = None
        raw = {"qte": [{"name": "duel", "result": res_byte, "flag": EVENT_FLAG_BASE}]}
    q = _FlagAlloc.for_project(_Q())
    assert EVENT_FLAG_BASE in q.reserved and span <= q.reserved
    # sweep most of the band (width 40 since the safe-band partition; 18 indices are reserved
    # above, so 20 autos + 18 reserved fit with 2 spare -- the width-100-era sweep was 30)
    for i in range(20):                                    # no auto event flag lands on either reservation
        got = q.event(i)
        assert got != EVENT_FLAG_BASE and got not in span


def test_mognet_mailbox_region_is_reserved():
    # the 2026-07-26 audit's root finding: bytes 1024-1045 (bits 8192-8367) are the stock Mognet
    # MAILBOX (wipe-guard / counters / the 12 live letter-slot bytes) -- flags.py must know.
    from ff9mapkit import flags as F
    for bit in (F.MOGNET_MAILBOX_LO, 8300, F.MOGNET_MAILBOX_HI):    # 8300 = the pre-b18 on_entry/ate base
        r = F.bit_region(bit)
        assert r is not None and r.reserved and r.name == "mognet_mailbox"
    assert F.bit_region(8191) is None or F.bit_region(8191).name != "mognet_mailbox"


def test_flag_alloc_campaign_member_blocks_are_disjoint():
    # a per-member base packs cutscene/events/choices into the member's own K=64 block -> no sibling aliasing
    from ff9mapkit.build import _FlagAlloc, EVENTS_PER_FIELD
    base = 8512
    a, b = _FlagAlloc(base), _FlagAlloc(base + 64)
    assert a.cutscene() == base                                  # cutscene at base+0
    assert (a.event(0), a.event(2)) == (base + 1, base + 3)      # events base+1..
    assert a.choice(0) == base + 1 + EVENTS_PER_FIELD            # choices after the event reserve
    used_a = {a.cutscene(), a.event(0), a.event(EVENTS_PER_FIELD - 1), a.choice(0), a.choice(31)}
    used_b = {b.cutscene(), b.event(0), b.choice(0)}
    assert max(used_a) < base + 64 and used_a.isdisjoint(used_b)


def test_auto_event_flags_stay_inside_the_member_block_at_every_width():
    """★ THE TEST ABOVE ONLY EVER USED K=64, WHICH IS WHY THIS SURVIVED. Events pack at base+1.., so the
    cap is K-1, not the bare EVENTS_PER_FIELD (which is the K=64 answer). Both overflow guards tested the
    constant while the sibling walk-choice guard read flags_per_field -- so at the live opening campaign's
    K=16, auto events 16..31 wrote into the NEXT member's block, and at stolen-ember's K=8, events 8..31.
    Silently: build, both lints and the build stamp were all green, because the stamp records where a
    window IS, not what gets written into it. The bits are save-persistent."""
    from ff9mapkit.build import EVENTS_PER_FIELD, _FlagAlloc, max_auto_events

    class _P:
        def __init__(self, k):
            self.flags_per_field = k

    base = 8712
    for k in (2, 8, 16, 33, 64, 128):
        cap = max_auto_events(_P(k))
        alloc = _FlagAlloc(base)
        flags = [alloc.event(i) for i in range(cap)]
        assert all(base <= f < base + k for f in flags), \
            f"K={k}: auto event flags {[f for f in flags if not (base <= f < base + k)]} escape {base}..{base+k-1}"
        assert all(f < alloc.choice(0) for f in flags), f"K={k}: an event flag reached the choice sub-band"
    assert max_auto_events(_P(8)) == 7 and max_auto_events(_P(16)) == 15      # K-1 governs below 32
    assert max_auto_events(_P(64)) == EVENTS_PER_FIELD                        # the constant governs above
    assert max_auto_events(object()) == EVENTS_PER_FIELD                      # single-field: unchanged


def test_lint_duplicate_names(tmp_path):
    lints = _lint(tmp_path, '[[npc]]\nname="g"\npreset="vivi"\npos=[0,-150]\ndialogue="a"\n'
                            '[[npc]]\nname="g"\npreset="vivi"\npos=[100,-150]\ndialogue="b"\n')
    assert any("duplicate" in m and "'g'" in m for m in lints)


def test_lint_choice_default_past_disabled_row_warns(tmp_path):
    # default=2 with option 1 disabled: the engine converts abs->avail then reads as abs -> can't honor
    lints = _lint(tmp_path,
                  '[[choice]]\nzone=[[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt="P"\ndefault=2\n'
                  '[[choice.options]]\ntext="A"\n'
                  '[[choice.options]]\ntext="B"\ndisabled=true\n'
                  '[[choice.options]]\ntext="C"\n')
    assert any("can't be honored" in m for m in lints)


def test_lint_choice_default_without_disable_is_clean(tmp_path):
    # default works fine when no rows before it are greyed
    lints = _lint(tmp_path,
                  '[[choice]]\nzone=[[10,-10],[50,-10],[50,-50],[10,-50]]\nprompt="P"\ndefault=2\ncancel=0\n'
                  '[[choice.options]]\ntext="A"\n[[choice.options]]\ntext="B"\n[[choice.options]]\ntext="C"\n')
    assert not any("can't be honored" in m for m in lints)


def test_validate_npc_needs_position(tmp_path):
    from ff9mapkit.build import FieldProject, validate
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE + '[[npc]]\nname="g"\npreset="vivi"\ndialogue="hi"\n', encoding="utf-8")
    probs = validate(FieldProject.load(p))
    assert any("has no position" in m for m in probs)


def test_cutscene_field_builds(tmp_path):
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE + '[cutscene]\nsteps = [ {say="hi"}, {wait=20}, {set_flag=[210,1]} ]\n',
                 encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out)
    L = ModLayout(out)
    eb = EbScript.from_bytes(L.eb_path("us", "EVT_X.eb.bytes").read_bytes())
    # the scene entry is the one with a WINDOW (0x1F) -- a bare 0x2D probe would find the shared
    # control WATCHDOG, which a narration field now ships too (the grant-spin adoption)
    cs = next(e for e in eb.entries if not e.empty and e.type == 0 and e.index != 0
              and any(i.op == 0x1F for i in iter_code(eb.data, e.func_by_tag(0).abs_start,
                                                      e.func_by_tag(0).abs_end)))
    ops = [i.op for i in iter_code(eb.data, cs.func_by_tag(0).abs_start, cs.func_by_tag(0).abs_end)]
    assert 0x2D in ops and 0x1F in ops and 0x2E in ops    # DisableMove, WindowSync, EnableMove
    assert "hi" in L.mes_path("us", 4003).read_text(encoding="utf-8")   # _LINT_BASE id -> derived block


def test_cast_scene_of_one_runs_through_conductor(tmp_path):
    """#13 v3 (the ONE actor mechanism): a cast of one (`actors = ["vivi"]`, untagged steps default to it)
    builds as a CONDUCTOR -- a standalone director entry drives the NPC by uid; walk/teleport/face_player
    run as tags on the NPC's own entry (RunScriptSync'd, so they animate in its context)."""
    from ff9mapkit.eb import EbScript
    from ff9mapkit.eb.disasm import iter_code
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE +
                 '[[npc]]\nname = "vivi"\npreset = "vivi"\npos = [0, -300]\ndialogue = "x"\n'
                 '[cutscene]\nactors = ["vivi"]\n'
                 'steps = [ {walk=[200,-300]}, {animation=921}, {face_player=true}, '
                 '{say="welcome"}, {walk=[0,-300]} ]\n', encoding="utf-8")
    assert validate(FieldProject.load(p)) == []
    out = tmp_path / "mod"
    build_mod([FieldProject.load(p)], out)
    L = ModLayout(out)
    eb = EbScript.from_bytes(L.eb_path("us", "EVT_X.eb.bytes").read_bytes())
    npc_entries = [e for e in eb.entries if not e.empty and e.func_by_tag(3) and e.index != 0]
    assert len(npc_entries) == 1
    npc_e = npc_entries[0]
    # the tag-kind steps landed as tags on the NPC's entry: walk(20), face_player(21), walk(22)
    assert all(npc_e.func_by_tag(t) is not None for t in (20, 21, 22))
    # a standalone CONDUCTOR entry drives the NPC: RunScriptSync(2, uid, tag) calls in step order + the
    # by-uid animation, and it owns the control lock (the NPC loop does NOT lock)
    drv = next(e for e in eb.entries if not e.empty and e.index != 0 and e.func_by_tag(0)
               and any(i.op == 0x14 for i in iter_code(eb.data, e.func_by_tag(0).abs_start,
                                                       e.func_by_tag(0).abs_end)))
    body = eb.data[drv.func_by_tag(0).abs_start:drv.func_by_tag(0).abs_end]
    calls = [(i.imm(1), i.imm(2)) for i in iter_code(body, 0, len(body)) if i.op == 0x14]
    assert calls == [(npc_e.index, 20), (npc_e.index, 21), (npc_e.index, 22)]
    ops = [i.op for i in iter_code(body, 0, len(body))]
    assert 0xBD in ops and 0x2D in ops                     # RunAnimationEx (by uid) + the control lock
    assert 0x1F in ops                                     # the UNTAGGED say stays a narration window
    assert "welcome" in L.mes_path("us", 4003).read_text(encoding="utf-8")   # _LINT_BASE id -> derived block
    for lang in LANGS:                                      # every language built
        assert L.eb_path(lang, "EVT_X.eb.bytes").is_file()


def test_actor_step_without_cast_is_rejected(tmp_path):
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE + '[cutscene]\nsteps = [ {walk=[0,-300]} ]\n', encoding="utf-8")
    assert any("needs a cast" in s for s in validate(FieldProject.load(p)))


def test_cutscene_unknown_actor_is_rejected(tmp_path):
    p = tmp_path / "x.field.toml"
    p.write_text(_LINT_BASE + '[cutscene]\nactors = ["ghost"]\nsteps = [ {wait=5} ]\n', encoding="utf-8")
    assert any("not a defined [[npc]] name" in s for s in validate(FieldProject.load(p)))


def test_cutscene_migration_errors(tmp_path):
    """#13 v3 breaking changes: the old block key `actor` (string OR list), the step key `anim`, and
    `exit_warp` all fail validation with a migration hint (never silently misbuild)."""
    def probs(body):
        p = tmp_path / "m.field.toml"
        p.write_text(_LINT_BASE + body, encoding="utf-8")
        return validate(FieldProject.load(p))
    assert any("`actor` was replaced by `actors`" in s and 'actors = ["g"]' in s
               for s in probs('[cutscene]\nactor = "g"\nsteps = [ {wait=5} ]\n'))
    assert any("`actor` was replaced by `actors`" in s
               for s in probs('[cutscene]\nactor = ["a", "b"]\nsteps = [ {wait=5} ]\n'))
    assert any("`anim` was renamed `animation`" in s
               for s in probs('[cutscene]\nactors = ["x"]\nsteps = [ {actor = "x", anim = 5} ]\n'))
    assert any("`exit_warp` was renamed `then_warp`" in s
               for s in probs('[cutscene]\nexit_warp = 100\nsteps = [ {say = "x"} ]\n'))


def test_validate_rejects_low_area(tmp_path):
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4002\nname="X"\narea=7\n[camera]\npitch=48\n', encoding="utf-8")
    problems = validate(FieldProject.load(bad))
    assert any("area must be >= 10" in p for p in problems)


def test_battle_bgm_emits_scene_keyed_music(tmp_path):
    # [[battle_bgm]] -> a SCENE-keyed Battle:/Music: BattlePatch line (a verbatim fork's carried boss battle;
    # a mint loses the engine's (field, scene) song lookup, so the kit reproduces it scene-keyed). Inject the
    # block into the loaded oracle project (so its art/walkmesh assets still resolve from EXAMPLE's dir).
    proj = FieldProject.load(EXAMPLE)
    proj.raw["battle_bgm"] = [{"scene": 330, "song": 35}]
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    bp = ModLayout(out).battle_patch.read_text(encoding="utf-8")
    assert "Battle: 330" in bp and "Music: 35" in bp


def test_battle_bgm_dedups_scene_globally(tmp_path):
    # the same scene twice -> ONE Battle:/Music: pair (it's scene-keyed + mod-global; a dup just restates it)
    proj = FieldProject.load(EXAMPLE)
    proj.raw["battle_bgm"] = [{"scene": 330, "song": 35}, {"scene": 330, "song": 35}]
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    bp = ModLayout(out).battle_patch.read_text(encoding="utf-8")
    assert bp.count("Battle: 330") == 1


def test_rebuild_without_battle_blocks_removes_a_stale_battle_patch(tmp_path):
    # build_mod writes a WHOLE mod, so it must OWN BattlePatch.txt in its out_root the way it owns
    # DictionaryPatch. It never cleans out_root (the only rmtree is scripts_dir), and the write is a bare
    # `if bp_lines:` -- so dropping the last [[battle_bgm]] used to leave the PREVIOUS build's file behind,
    # still patching a scene the mod no longer mentions. Worse downstream: a campaign that emits no battle
    # lines leaves the stale file for build_battle_mod's append to duplicate into.
    proj = FieldProject.load(EXAMPLE)
    proj.raw["battle_bgm"] = [{"scene": 330, "song": 35}]
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    assert ModLayout(out).battle_patch.is_file(), "setup: the first build must emit a BattlePatch"

    proj.raw.pop("battle_bgm")                             # the author removed the block
    build_mod([proj], out, mod_name="FF9CustomMap")
    assert not ModLayout(out).battle_patch.exists(), \
        "a rebuild that emits no battle lines must not leave the prior build's BattlePatch.txt behind"


def test_preserve_existing_keeps_a_foreign_battle_patch_block(tmp_path):
    # ...but ONLY in its own dist. `preserve_existing` means "installing INTO a shipping folder" (the Build
    # tab deploys in place with it), where another deploy's sentinel-marked block legitimately lives. The
    # ownership delete must not reach into that folder and unpatch someone else's battle.
    from ff9mapkit.battle import battlepatch as _bp
    out = tmp_path / "mod"
    out.mkdir()
    foreign = _bp.merge_battle_patch("", ["Battle: 999", "Music: 7"], 4003)
    ModLayout(out).battle_patch.write_text(foreign, encoding="utf-8", newline="\n")

    proj = FieldProject.load(EXAMPLE)                      # emits NO battle lines of its own
    build_mod([proj], out, mod_name="FF9CustomMap", preserve_existing=True)
    live = ModLayout(out).battle_patch.read_text(encoding="utf-8")
    assert "Battle: 999" in live and "ff9mapkit field 4003" in live, \
        f"preserve_existing must keep another deploy's BattlePatch block, got:\n{live}"


def test_validate_rejects_bad_battle_bgm(tmp_path):
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4003\nname="X"\narea=11\n[camera]\npitch=48\n'
                   "[[battle_bgm]]\nscene = -1\nsong = 35\n", encoding="utf-8")
    assert any("battle_bgm" in p for p in validate(FieldProject.load(bad)))


def test_battle_bgm_scene_takes_a_name_like_encounter_does(tmp_path):
    # `scene` names the SAME thing in [[battle_bgm]] as in [encounter], so it must accept the same values --
    # one file used to build `scene = "BSC_CA_E013"` under [encounter] and fail lint on it here.
    proj = FieldProject.load(EXAMPLE)
    proj.raw["battle_bgm"] = [{"scene": "BSC_CA_E013", "song": 35}]     # BSC_CA_E013 == 296
    assert validate(proj) == [], "a KNOWN BSC_ name must lint clean"
    out = tmp_path / "mod"
    build_mod([proj], out, mod_name="FF9CustomMap")
    bp = ModLayout(out).battle_patch.read_text(encoding="utf-8")
    assert "Battle: 296" in bp and "Music: 35" in bp, bp        # the NAME reached the scene-keyed line as an id


def test_validate_names_the_row_of_an_unknown_battle_bgm_scene(tmp_path):
    # the fence: it builds, or it fails LINT with the row index and a suggestion -- never an int() death
    # mid-build. song stays integers-only (an akao song-play id has no name catalog) and says so.
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4003\nname="X"\narea=11\n[camera]\npitch=48\n'
                   '[[battle_bgm]]\nscene = 330\nsong = 35\n'
                   '[[battle_bgm]]\nscene = "BSC_NOPE"\nsong = 35\n', encoding="utf-8")
    probs = validate(FieldProject.load(bad))
    assert any("#1" in p and "BSC_NOPE" in p for p in probs), probs
    assert not any("#0" in p for p in probs), "the good row must not be blamed"
    worse = tmp_path / "worse.field.toml"
    worse.write_text('[field]\nid=4003\nname="X"\narea=11\n[camera]\npitch=48\n'
                     '[[battle_bgm]]\nscene = 330\nsong = "Rufus\'s Welcoming Ceremony"\n', encoding="utf-8")
    assert any("song must be an integer" in p for p in validate(FieldProject.load(worse)))


# ---- [encounter] scene/scenes take a NAME as well as an id -------------------------------------
# The trap this closes: `lint_logic` resolved a catalog name to report on it (so a name linted CLEAN),
# but both build consumers did a bare `int()` -- the same value then died as `invalid literal for int()
# with base 10: 'BSC_CA_E013'` with no field, no key and no suggestion. Every shipped example writes a
# numeric id, so nothing exercised the name path through a build. Now: it builds, or it fails lint named.

def _enc_build(tmp_path, tag, enc_body):
    """Build the oracle project with an [encounter] body swapped in -> (its .eb bytes, BattlePatch text)."""
    import tomllib
    proj = FieldProject.load(EXAMPLE)
    proj.raw["encounter"] = tomllib.loads(f"[encounter]\n{enc_body}\n")["encounter"]
    out = tmp_path / tag
    build_mod([proj], out, mod_name="FF9CustomMap")
    L = ModLayout(out)
    return (L.eb_path("us", "EVT_HUT_INT.eb.bytes").read_bytes(),
            L.battle_patch.read_text(encoding="utf-8"))


def test_encounter_scene_name_builds_byte_identical_to_its_id(tmp_path):
    # BSC_CA_E013 == 296. The NAME must reach the .eb's SetRandomBattles immediates AND the scene-keyed
    # BattlePatch Battle:/Music: line as that id -- byte-for-byte what the numeric form emits.
    from ff9mapkit import catalog
    sid = catalog.resolve_scene("BSC_CA_E013")
    by_id, bp_id = _enc_build(tmp_path, "byid", f"scene = {sid}\nfreq = 48")
    by_name, bp_name = _enc_build(tmp_path, "byname", 'scene = "BSC_CA_E013"\nfreq = 48')
    assert by_name == by_id, "a named [encounter] scene must compile to the same bytes as its id"
    assert bp_name == bp_id and f"Battle: {sid}" in bp_id


def test_encounter_scenes_pool_resolves_names(tmp_path):
    # the PLURAL 4-slot pool takes names too (it feeds the same SetRandomBattles op, one id per slot)
    from ff9mapkit import catalog
    sid = catalog.resolve_scene("BSC_CA_E013")
    by_id, _ = _enc_build(tmp_path, "poolid", f"scene = 67\nscenes = [{sid}, 67, {sid}, 67]")
    by_name, _ = _enc_build(tmp_path, "poolnm",
                            'scene = 67\nscenes = ["BSC_CA_E013", 67, "BSC_CA_E013", 67]')
    assert by_name == by_id


@pytest.mark.parametrize("body, key", [
    ('scene = "BSC_NOPE"', "[encounter] scene"),
    ('scene = 67\nscenes = [67, "BSC_NOPE", 67, 67]', "[encounter] scenes[1]"),
])
def test_validate_rejects_an_unresolvable_encounter_scene_name(tmp_path, body, key):
    # the fence: an unknown name never reaches the compile -- it fails lint naming the FIELD and the KEY
    # (the field, because build_field's own BuildError says only "invalid field project"), with did-you-means.
    bad = tmp_path / "bad.field.toml"
    bad.write_text(f'[field]\nid=4003\nname="ENCX"\narea=11\n[camera]\npitch=48\n[encounter]\n{body}\n',
                   encoding="utf-8")
    hits = [p for p in validate(FieldProject.load(bad)) if key in p]
    assert hits, f"no problem naming {key}"
    assert "'ENCX'" in hits[0] and "unknown battle scene" in hits[0] and "Did you mean" in hits[0]


def test_validate_rejects_a_short_encounter_scenes_pool(tmp_path):
    # SetRandomBattles takes exactly 4 slots; a short pool used to raise ValueError mid-build
    bad = tmp_path / "bad.field.toml"
    bad.write_text('[field]\nid=4003\nname="ENCX"\narea=11\n[camera]\npitch=48\n'
                   "[encounter]\nscene = 67\nscenes = [67, 67]\n", encoding="utf-8")
    assert any("[encounter] scenes needs exactly 4" in p and "'ENCX'" in p
               for p in validate(FieldProject.load(bad)))


def test_lint_logic_warns_a_scenes_pool_with_no_scene_is_inert(tmp_path):
    # `scene` is what ARMS the block (build_script's has_encounter tests it alone), so a pool-only
    # [encounter] injects NOTHING -- and used to say so only if freq/battle_music was also present.
    from ff9mapkit.build import lint_logic
    p = tmp_path / "poolonly.field.toml"
    p.write_text('[field]\nid=4003\nname="PO"\narea=11\n[camera]\npitch=48\n'
                 "[encounter]\nscenes = [67, 67, 67, 67]\n", encoding="utf-8")
    warns = [w for w in lint_logic(FieldProject.load(p)) if "[encounter]" in w]
    assert warns and "scenes" in warns[0] and "no scene" in warns[0]


def test_lint_logic_flags_a_model_bucket_scene_by_name_and_in_the_pool(tmp_path):
    # the pre-existing model-bucket warning (BSC_B3_* crashes in-game) must survive name resolution AND
    # now cover the plural pool -- one bad slot is the same InitBattleScene null-ref.
    from ff9mapkit.build import lint_logic
    def warns(body):
        p = tmp_path / f"mb{abs(hash(body))}.field.toml"
        p.write_text(f'[field]\nid=4003\nname="MB"\narea=11\n[camera]\npitch=48\n[encounter]\n{body}\n',
                     encoding="utf-8")
        proj = FieldProject.load(p)
        assert validate(proj) == [], "a REAL bucket name resolves -- it's a warning, not a schema error"
        return [w for w in lint_logic(proj) if "MODEL-BUCKET" in w]
    assert warns("scene = 472")                                  # by id (the pre-existing check)
    assert warns('scene = "BSC_B3_160"')                         # 472 by name
    assert warns('scene = 67\nscenes = [67, 67, "BSC_B3_160", 67]')   # NEW: a bad slot in the pool


def test_battle_bgm_warns_on_conflicting_song(tmp_path):
    # same scene, DIFFERENT songs -> first-wins emission + a build warning (the override is scene-keyed/global)
    proj = FieldProject.load(EXAMPLE)
    proj.raw["battle_bgm"] = [{"scene": 330, "song": 35}, {"scene": 330, "song": 9}]
    out = tmp_path / "mod"
    res = build_mod([proj], out, mod_name="FF9CustomMap")
    bp = ModLayout(out).battle_patch.read_text(encoding="utf-8")
    assert "Music: 35" in bp and "Music: 9" not in bp                 # first-wins
    assert any("conflicting songs" in w for w in res["warnings"])


def test_npc_model_kwargs_explicit_anims_override_archetype():
    """[[npc]] archetype= + anims=: the user's explicit clip set WINS. The archetype path used to drop
    the override silently -- the stolen-ember innkeeper's corrected anims never reached the game, which
    contaminated an in-game A/B (the deployed .eb still carried the auto-resolved set)."""
    from ff9mapkit import archetypes as AR
    from ff9mapkit.build import _npc_model_kwargs

    ov = {"stand": 654, "walk": 655, "run": 657, "left": 17, "right": 16}
    k = _npc_model_kwargs({"archetype": "innkeeper", "anims": ov})
    assert k["model"] == AR.resolve("innkeeper")[0]                   # archetype still names the model
    assert k["anims"] == ov                                           # ...but the explicit clips ship
    assert _npc_model_kwargs({"archetype": "innkeeper", "animset": 87})["animset"] == 87
    # no override -> the archetype's auto-resolve, unchanged
    k2 = _npc_model_kwargs({"archetype": "innkeeper"})
    assert (k2["model"], k2["animset"], k2["anims"]) == AR.resolve("innkeeper")[:3]
    # the bare-model path keeps its Info Hub join + explicit-anims precedence
    assert _npc_model_kwargs({"model": "GEO_NPC_F0_TMM"})["anims"]["stand"] == 654
    assert _npc_model_kwargs({"model": "GEO_NPC_F0_TMM", "anims": ov})["anims"] == ov


# --- the model/anims precedence is ONE function, shared with the GUI ------------------------------
# `build._npc_model_kwargs` now delegates to `blockmodel.resolve_block_model`, so an animation picker
# scopes itself to the SAME rig the build ships. The fence is byte-shaped: the lifted helper must
# answer identically to the code it replaced, block for block -- `_npc_model_kwargs` is the build's
# only spender of the rule, so agreeing here IS "the build output is unchanged".

def _legacy_npc_model_kwargs(n):
    """build._npc_model_kwargs exactly as it read before the lift (the oracle)."""
    from ff9mapkit import archetypes as _archetypes
    from ff9mapkit import catalog as _catalog
    from ff9mapkit.build import resolve_npc_model
    arch = n.get("archetype") or n.get("preset")
    if arch is not None:
        model, animset, anims, _dlg = _archetypes.resolve(arch)
        return {"model": model,
                "animset": n.get("animset") if n.get("animset") is not None else animset,
                "anims": n.get("anims") or anims}
    mid = resolve_npc_model(n.get("model"))
    anims = n.get("anims")
    if mid is not None and not anims:
        anims = _catalog.npc_anims(mid) or None
    return {"model": mid, "animset": n.get("animset"), "anims": anims}


@pytest.mark.parametrize("block", [
    {"archetype": "innkeeper"},                                    # an archetype NPC (the majority)
    {"archetype": "innkeeper", "anims": {"stand": 654}},           # ...with the explicit override
    {"archetype": "innkeeper", "animset": 87},
    {"preset": "vivi"},                                            # a playable preset
    {"preset": "vivi", "anims": {"stand": 148}},
    {"preset": "zidane"},                                          # model=None: keeps the cloned player
    {"model": "GEO_NPC_F0_TMM"},                                   # a bare model= (name)
    {"model": 8},                                                  # ...and a raw id
    {"model": 999999},                                             # an off-table raw id still passes through
    {"model": "GEO_NPC_F0_TMM", "anims": {"stand": 654}, "animset": 3},
    {"name": "no model at all"},
    {"model": None, "anims": {}},                                  # the falsy-anims corner
])
def test_lifted_model_precedence_answers_exactly_as_the_code_it_replaced(block):
    from ff9mapkit.build import _npc_model_kwargs
    assert _npc_model_kwargs(block) == _legacy_npc_model_kwargs(block)


def test_resolve_block_model_answers_for_zidane_and_the_player_block():
    from ff9mapkit import blockmodel as BM
    from ff9mapkit import catalog as C

    z = BM.resolve_block_model({"preset": "zidane"})
    assert z.model is None and z.source == "preset" and "cloned player" in z.reason

    viv = BM.resolve_block_model({"preset": "vivi"})
    assert viv.model == 8 and viv.anims_source == "archetype" and viv.reason is None

    bare = BM.resolve_block_model({"model": "GEO_NPC_F0_TMM"})
    assert (bare.source, bare.anims_source) == ("model", "catalog")

    # [player]: the model key re-skins the avatar; ABSENT means the stock cloned player, who is Zidane
    p = BM.resolve_block_model({}, kind="player")
    assert p.model == C.resolve_model(BM.PLAYER_DEFAULT_GEO) == 98 and p.source == "player-default"
    named = BM.resolve_block_model({"model": "GEO_MAIN_F0_VIV"}, kind="player")
    assert named.model == 8 and named.source == "player"
    assert named.anims == C.npc_anims(8)          # what build's [player] model= injection ships

    # strict=False never raises at a picker -- it reports instead
    with pytest.raises(ValueError):
        BM.resolve_block_model({"model": "GEO_NOPE"})
    soft = BM.resolve_block_model({"model": "GEO_NOPE"}, strict=False)
    assert soft.model is None and "GEO_NOPE" in soft.reason


# --- build must not silently unregister a shared mod folder's other fields ---------------------------
def test_build_refuses_to_unregister_a_shared_folders_other_fields(tmp_path):
    """`build` writes a WHOLE mod, so its DictionaryPatch rewrite owns the output folder. Pointed at a
    live folder other deploys share, it would unregister every field it does not emit -- their .eb/.mes
    stay on disk, so nothing looks wrong until the engine black-screens. Observed in-game 2026-07-18."""
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[field]\nid = 4005\nname = "MINE"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    out = tmp_path / "mod"
    build.build_mod([proj], out)                                  # fresh folder: fine
    assert "FieldScene 4005" in out.joinpath("DictionaryPatch.txt").read_text(encoding="utf-8")
    build.build_mod([proj], out)                                  # same set again: still fine
    # now the folder also carries a FOREIGN field (another session's deploy)
    dp = out / "DictionaryPatch.txt"
    dp.write_text("MessageFile 30110 MES_DWIX_30110\nFieldScene 30110 11 THEIRS THEIRS 30110\n"
                  + dp.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(build.BuildError) as e:
        build.build_mod([proj], out)
    assert "30110 (THEIRS)" in str(e.value) and "deploy_field.py" in str(e.value)
    assert "FieldScene 30110" in dp.read_text(encoding="utf-8")   # and the file is UNTOUCHED


def test_build_preserve_existing_installs_alongside_other_fields(tmp_path):
    """The GUI's "Install to game": one field into a SHIPPING folder that holds others. The other
    fields must stay registered (their MessageFile too), and re-installing must not duplicate."""
    from ff9mapkit import build
    p = tmp_path / "f.field.toml"
    p.write_text(
        '[field]\nid = 4008\nname = "MINE"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    out = tmp_path / "mod"
    build.build_mod([proj], out)
    dp = out / "DictionaryPatch.txt"
    dp.write_text("MessageFile 30110 MES_DWIX_30110\nFieldScene 30110 11 THEIRS THEIRS 30110\n"
                  + dp.read_text(encoding="utf-8"), encoding="utf-8")
    build.build_mod([proj], out, preserve_existing=True)
    lines = [l for l in dp.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert "FieldScene 30110 11 THEIRS THEIRS 30110" in lines      # the foreign field survives
    assert "MessageFile 30110 MES_DWIX_30110" in lines             # ...and its block registration
    assert sum(1 for l in lines if l.startswith("FieldScene 4008 ")) == 1   # ours, exactly once
    # a MessageFile still precedes the FieldScene that uses its block
    assert lines.index("MessageFile 30110 MES_DWIX_30110") < lines.index("FieldScene 30110 11 THEIRS THEIRS 30110")
    build.build_mod([proj], out, preserve_existing=True)            # idempotent -- no duplicates
    l2 = [l for l in dp.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert l2 == lines


# --- ForkDonorPatch: a fork installed by `build --out` must carry its donor map ------------------------
def _fork_toml(path, fid, *, donor=None, text_block=22):
    """A minimal buildable field; `donor` records it as a fork ([field] source_field, the native/editable
    import's record). text_block 22 is the donor's own block -- the pairing lint_text_block calls clean."""
    src = f"source_field = {donor}\n" if donor is not None else ""
    path.write_text(
        f'[field]\nid = {fid}\nname = "F{fid}"\narea = 11\ntext_block = {text_block}\n{src}\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n',
        encoding="utf-8")
    return path


def test_build_mod_emits_fork_donor_patch(tmp_path):
    """`build --out` ships a COMPLETE standalone mod, so it must emit ForkDonorPatch.txt -- the
    `<forkId> <donorRealId>` map the s24-s33 fork gates resolve through. It used to be written ONLY by
    tools/deploy_field.py, so a fork INSTALLED rather than deployed from the repo booted with every
    fork-donor behavior (off-mesh exemptions, name-keyed overlay occlusion, scroll binds) silently off."""
    from ff9mapkit import build
    out = tmp_path / "mod"
    build.build_mod([build.FieldProject.load(_fork_toml(tmp_path / "a.field.toml", 4009, donor=600))], out)
    body = (out / "ForkDonorPatch.txt").read_text(encoding="utf-8")
    assert [l for l in body.splitlines() if l.strip() and not l.startswith("#")] == ["4009 600"]
    assert body.startswith("# ff9mapkit fork-fidelity: <forkId> <donorRealId>\n")   # deploy_field's header


def test_build_mod_emits_no_fork_donor_patch_for_a_novel_field(tmp_path):
    """A NOVEL field has no donor -> no file at all (the same non-empty guard the battle/text patches use),
    so a from-scratch build stays byte-identical to what it produced before the emit existed."""
    from ff9mapkit import build
    out = tmp_path / "mod"
    build.build_mod([build.FieldProject.load(_fork_toml(tmp_path / "n.field.toml", 4009, text_block=1073))], out)
    assert not (out / "ForkDonorPatch.txt").exists()


def test_build_mod_fork_donor_patch_skips_a_self_mapping(tmp_path):
    """A fork sitting on its OWN donor id (an in-place edit, not a remap) needs no mapping -- emitting
    `600 600` would ask the engine to resolve a field to itself."""
    from ff9mapkit import build
    out = tmp_path / "mod"
    build.build_mod([build.FieldProject.load(_fork_toml(tmp_path / "s.field.toml", 600, donor=600))], out)
    assert not (out / "ForkDonorPatch.txt").exists()


def test_build_mod_preserve_existing_keeps_other_forks_donor_lines(tmp_path):
    """The DictionaryPatch lesson, one file over: installing INTO a shipping folder rewrites
    ForkDonorPatch wholesale, so without a merge it would drop the OTHER forks' mappings -- switching
    their fork-gated behaviors off with no error. Ours appears exactly once; re-installing is idempotent."""
    from ff9mapkit import build
    out = tmp_path / "mod"
    proj = build.FieldProject.load(_fork_toml(tmp_path / "a.field.toml", 4009, donor=600))
    build.build_mod([proj], out)
    fdp = out / "ForkDonorPatch.txt"
    fdp.write_text(fdp.read_text(encoding="utf-8") + "30110 1860\n", encoding="utf-8")   # another session's fork
    build.build_mod([proj], out, preserve_existing=True)
    rows = [l for l in fdp.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert sorted(rows) == ["30110 1860", "4009 600"]
    build.build_mod([proj], out, preserve_existing=True)                                 # idempotent
    assert [l for l in fdp.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")] == rows
