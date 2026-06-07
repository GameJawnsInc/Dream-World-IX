"""The ladder primitive -- FF9's real ladder mechanism (tread '!' prompt + action RunScriptSyncs the
player's climb). Grounded in Treno/Residence; verified in-game. These check the opcodes, the injector
structure on the blank field, and a full build."""
from __future__ import annotations

import tomllib

import pytest

from ff9mapkit import build, data, eventscan, extract
from ff9mapkit.content import ladder
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code

CLEAN = data.blank_field_bytes("us")

# a minimal FAITHFUL climb: the ladder-flag signature scan_ladders keys on -- AddCharacterAttribute(4)
# (0xCC, 2-byte arg) then RETURN. A real climb is this + the jump arcs; the flag alone is enough to
# identify a ladder and round-trip the inject<->scan symmetry without shipping any game bytes.
FAITHFUL_CLIMB = bytes([0xCC, 0x00, 0x04, 0x00]) + opcodes.RETURN


def _ops(eb, entry_index, tag):
    f = eb.entry(entry_index).func_by_tag(tag)
    return [i.op for i in iter_code(eb.data, f.abs_start, f.abs_end)]


def test_opcodes_runscriptsync_and_bubble():
    # RunScriptSync(2,250,17) = REQEW 0x14, argFlag 0, three 1-byte args.
    assert opcodes.run_script_sync(2, 250, 17) == bytes([0x14, 0x00, 2, 250, 17])
    assert opcodes.bubble(1) == bytes([0x68, 0x00, 1])


def test_inject_ladder_adds_player_climb_and_region():
    out, slot = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)], (80, 80, 0))
    eb = EbScript.from_bytes(out)
    pe = ladder.find_player_entry(eb)
    # the player gets a climb function at the climb tag, doing MoveInstantXZY (0xA1) + SetPathing (0xA8)
    assert eb.entry(pe).func_by_tag(ladder.FIRST_CLIMB_TAG) is not None
    climb = _ops(eb, pe, ladder.FIRST_CLIMB_TAG)
    assert 0xA1 in climb and 0xA8 in climb
    # the ladder region: tread (tag 2) shows the Bubble (0x68); action (tag 3) RunScriptSyncs (0x14)
    assert 0x68 in _ops(eb, slot, 2)
    assert 0x14 in _ops(eb, slot, 3)
    # and it's armed in Main_Init (InitRegion 0x08 referencing the region slot)
    init = eb.entry(0).func_by_tag(0)
    armed = [i for i in iter_code(eb.data, init.abs_start, init.abs_end) if i.op == 0x08 and i.args[0] == slot]
    assert armed, "ladder region not armed by InitRegion in Main_Init"


def test_two_ladders_get_distinct_climb_tags():
    out, _ = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)], (80, 80),
                                  climb_tag=17)
    out, _ = ladder.inject_ladder(out, [(60, -10), (90, -10), (90, -50), (60, -50)], (-80, -80),
                                  climb_tag=18)
    eb = EbScript.from_bytes(out)
    pe = ladder.find_player_entry(eb)
    assert eb.entry(pe).func_by_tag(17) is not None
    assert eb.entry(pe).func_by_tag(18) is not None


def test_build_field_with_ladder(tmp_path):
    p = tmp_path / "l.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "L"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[ladder]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nto = [120, 120]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "ladder" in x.lower()]
    eb = build.build_script(proj, "us", {})
    s = EbScript.from_bytes(eb)
    pe = next(e.index for e in s.entries if not e.empty
              and any(i.op == 0x2C for f in e.funcs for i in s.instrs(f)))
    assert s.entry(pe).func_by_tag(ladder.FIRST_CLIMB_TAG) is not None        # climb attached
    assert any(i.op == 0x14 for e in s.entries if not e.empty                 # a RunScriptSync exists
               for f in e.funcs for i in s.instrs(f))


def test_validate_flags_bad_ladder(tmp_path):
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "B"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[ladder]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n',   # no 'to'
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert any("ladder" in x.lower() and "to" in x.lower() for x in build.validate(proj))


# --- FAITHFUL mode: grafting / importing a real ladder's verbatim climb -----------------------
def test_inject_ladder_grafts_faithful_climb_verbatim():
    out, _ = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)],
                                  climb_bytes=FAITHFUL_CLIMB)
    eb = EbScript.from_bytes(out)
    f = eb.entry(ladder.find_player_entry(eb)).func_by_tag(ladder.FIRST_CLIMB_TAG)
    assert eb.data[f.abs_start:f.abs_end] == FAITHFUL_CLIMB     # grafted exactly -- no shift/relocate


def test_inject_ladder_requires_climb_or_dest():
    with pytest.raises(ValueError):
        ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)])


def test_scan_ladders_roundtrips_through_injector():
    # scan_ladders is the inverse of the faithful inject: inject -> scan -> same zone/tag/climb.
    out, _ = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)],
                                  climb_bytes=FAITHFUL_CLIMB)
    lads = eventscan.scan_ladders(out)
    assert len(lads) == 1
    L = lads[0]
    assert L["climb_tag"] == ladder.FIRST_CLIMB_TAG
    assert L["zone"] == [[10, -10], [50, -10], [50, -50], [10, -50]]
    assert L["bubble"] is True                                  # ladder_region's tread Bubble
    assert L["climb"] == FAITHFUL_CLIMB                         # extracted verbatim


def test_scan_ladders_ignores_non_ladder_runscriptsync():
    # a region that RunScriptSyncs a player func WITHOUT the ladder signature is NOT a ladder
    # (e.g. Treno's facing / stand-anim tweaks). A climb that's just RETURN must not be detected.
    out, _ = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)],
                                  climb_bytes=opcodes.RETURN)
    assert eventscan.scan_ladders(out) == []


def test_build_faithful_ladder_from_sidecar(tmp_path):
    (tmp_path / "climb.bin").write_bytes(FAITHFUL_CLIMB)
    p = tmp_path / "l.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "L"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[ladder]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nclimb = "climb.bin"\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "ladder" in x.lower()]
    eb = build.build_script(proj, "us", {})
    lads = eventscan.scan_ladders(eb)
    assert len(lads) == 1 and lads[0]["climb"] == FAITHFUL_CLIMB    # grafted verbatim through the build


def test_build_faithful_ladder_missing_sidecar_flagged(tmp_path):
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "B"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[ladder]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nclimb = "nope.bin"\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert any("ladder" in x.lower() and "not found" in x.lower() for x in build.validate(proj))


def test_import_emits_ladder_block_and_sidecar(tmp_path):
    # the import emitter on a field that HAS a ladder -> a [[ladder]] block + a verbatim climb sidecar.
    # Build a synthetic "real field" by injecting a faithful ladder into the blank (no game bytes).
    eb, _ = ladder.inject_ladder(CLEAN, [(10, -10), (50, -10), (50, -50), (10, -50)],
                                 climb_bytes=FAITHFUL_CLIMB)
    blocks, _cd, summary = extract._imported_content_toml(eb, out_dir=tmp_path, name="T")
    assert summary["ladders"] == 1
    assert (tmp_path / "T.ladder0.climb.bin").read_bytes() == FAITHFUL_CLIMB
    toml = ('[field]\nid=4003\nname="T"\narea=11\ntext_block=1073\n'
            '[camera]\npitch=45\nfov=42.2\n[walkmesh]\nquad=[[-9,-9],[9,-9],[9,9],[-9,9]]\n'
            '[player]\nspawn=[0,0]\n\n' + blocks)
    d = tomllib.loads(toml)
    assert d["ladder"][0]["climb"] == "T.ladder0.climb.bin"
    assert len(d["ladder"][0]["zone"]) == 4
