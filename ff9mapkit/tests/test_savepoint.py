"""Save-point synthesis (content/savepoint.py) -- a press-to-interact region that opens the SAVE menu.

The functional save is a single opcode, ``Menu(4, 0)`` (0x75) -> ``OpenSaveMenu``, verified byte-exact
against the real Dali save moogle (field 122 entry 5 tag 3). These pin the synthesis offline; the closing
proof that the save menu actually opens + writes a slot is the human playtest (docs/SAVEPOINT.md).
"""
from __future__ import annotations

from ff9mapkit import data, eventscan
from ff9mapkit.content import region as _region
from ff9mapkit.content import savepoint as _savepoint
from ff9mapkit.eb import EbScript, opcodes

CLEAN = data.blank_field_bytes("us")
ZONE = [[10, -10], [50, -10], [50, -50], [10, -50], [10, -50]]   # 5-pt (doubled last vertex) press quad


def _menu_calls(eb, entry):
    """Every Menu(menu_id, sub_id) call in an entry's funcs."""
    return [[i.imm(0), i.imm(1)] for f in eb.entry(entry).funcs for i in eb.instrs(f) if i.op == 0x75]


# --- the Menu opcode encodes byte-exact (vs the real save moogle) -----------------------------------
def test_menu_opcode_is_byte_exact():
    assert opcodes.menu(4, 0).hex() == "75000400"            # the real Dali Menu(4,0): 75 00 04 00
    assert opcodes.menu(2, 1).hex() == "75000201"            # shop menu, generic


def test_save_dispatch_brackets_the_menu_with_move_control():
    body = _savepoint.save_dispatch()
    assert body.startswith(opcodes.DISABLE_MOVE)             # lock control while the save UI is up
    assert opcodes.menu(4, 0) in body                        # the functional save
    assert body.endswith(opcodes.ENABLE_MOVE + opcodes.RETURN)   # restore control + return


# --- the region entry: init / tread(bubble) / action(save) ------------------------------------------
def test_savepoint_region_shape():
    eb = EbScript.from_bytes(data.blank_field_bytes("us"))   # a throwaway parser
    entry_bytes = _savepoint.savepoint_region(ZONE)
    # graft it into a free slot just to parse + inspect it
    from ff9mapkit.eb import edit
    slot = eb.first_free_slot()
    g = edit.append_entry(data.blank_field_bytes("us"), slot, entry_bytes)
    p = EbScript.from_bytes(g)
    tags = {f.tag for f in p.entry(slot).funcs}
    assert tags == {0, _region.RANGE_TAG, _region.INTERACT_TAG}          # init + tread + action
    # the action func (tag 3) opens the save menu; the tread func (tag 2) shows the "!" bubble
    assert [4, 0] in _menu_calls(p, slot)
    assert any(i.op == 0x68 for i in p.instrs(p.entry(slot).func_by_tag(_region.RANGE_TAG)))   # Bubble


def test_savepoint_region_no_bubble():
    from ff9mapkit.eb import edit
    base = data.blank_field_bytes("us")
    slot = EbScript.from_bytes(base).first_free_slot()
    g = edit.append_entry(base, slot, _savepoint.savepoint_region(ZONE, bubble=False))
    p = EbScript.from_bytes(g)
    assert not any(i.op == 0x68 for i in p.instrs(p.entry(slot).func_by_tag(_region.RANGE_TAG)))


# --- inject: append + arm, round-trip stable --------------------------------------------------------
def test_inject_savepoint_arms_and_round_trips():
    g, slot = _savepoint.inject_savepoint(CLEAN, ZONE)
    p = EbScript.from_bytes(g)
    assert p.to_bytes() == g                                 # the injected field round-trips byte-exact
    assert [4, 0] in _menu_calls(p, slot)                    # the save region is present
    # armed: an InitRegion(slot) (0x08) for this slot exists in the Main_Init activation
    armed = [i.imm(0) for e in p.entries if not e.empty for f in e.funcs
             for i in p.instrs(f) if i.op == 0x08]
    assert slot in armed
    # every entry disassembles cleanly (no corruption from the append)
    for e in p.entries:
        if e.empty:
            continue
        for f in e.funcs:
            list(p.instrs(f))


def test_inject_savepoints_multiple():
    g, slots = _savepoint.inject_savepoints(
        CLEAN, [{"zone": ZONE}, {"zone": ZONE, "bubble": False}])
    assert len(slots) == 2 and slots[0] != slots[1]
    p = EbScript.from_bytes(g)
    assert all([4, 0] in _menu_calls(p, s) for s in slots)


# --- end-to-end build path (field.toml [[savepoint]] -> built .eb) ----------------------------------
def test_build_field_with_savepoint(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "savepoint" in x.lower()]   # lint clean
    eb = build.build_script(proj, "us", {})
    s = EbScript.from_bytes(eb)
    assert s.to_bytes() == eb
    # the save menu made it through the build, armed
    save_regions = [e.index for e in s.entries if not e.empty and [4, 0] in _menu_calls(s, e.index)]
    assert len(save_regions) == 1


def test_validate_flags_bad_savepoint_zone(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "B"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50]]\n',   # 3 points -- too few
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[savepoint]]" in x and "4 or 5" in x for x in probs)
