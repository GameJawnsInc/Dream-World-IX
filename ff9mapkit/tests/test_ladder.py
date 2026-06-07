"""The ladder primitive -- FF9's real ladder mechanism (tread '!' prompt + action RunScriptSyncs the
player's climb). Grounded in Treno/Residence; verified in-game. These check the opcodes, the injector
structure on the blank field, and a full build."""
from __future__ import annotations

from ff9mapkit import build, data
from ff9mapkit.content import ladder
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code

CLEAN = data.blank_field_bytes("us")


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
