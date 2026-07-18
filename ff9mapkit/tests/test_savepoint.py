"""Save-point synthesis (content/savepoint.py) -- a faithful FF9 save point, authored not grafted.

The functional save is a single opcode, ``Menu(4, 0)`` (0x75) -> ``OpenSaveMenu``, verified byte-exact
against the real Dali save moogle (field 407 entry 5 tag 3). Around it, a byte census of all 55 real save
points found a spine both families share: option menu -> Yes/No confirm -> GLOB(184)-latched save. These
pin that offline; the closing proof that the menu opens + writes a slot is the human playtest
(docs/SAVEPOINT.md).
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
    # the save menu made it through the build TWICE by default: the press-zone AND the visible save
    # MOOGLE at the zone centre whose TALK opens the same menu (FF9's actual idiom; default moogle=true,
    # added in-game 2026-07-12 -- an invisible zone read as "no save point here")
    save_regions = [e.index for e in s.entries if not e.empty and [4, 0] in _menu_calls(s, e.index)]
    assert len(save_regions) == 2
    # moogle = false opts back down to the invisible zone only
    p2 = tmp_path / "s2.field.toml"
    p2.write_text(p.read_text(encoding="utf-8").replace(
        "[[savepoint]]\n", "[[savepoint]]\nmoogle = false\n"), encoding="utf-8")
    eb2 = build.build_script(build.FieldProject.load(p2), "us", {})
    s2 = EbScript.from_bytes(eb2)
    assert len([e.index for e in s2.entries if not e.empty and [4, 0] in _menu_calls(s2, e.index)]) == 1


def test_validate_flags_savemoogle_without_cluster(tmp_path):
    # the [[save_moogle]] carry marker (from `import --save-moogle`) needs its cluster: the hidden Moogle +
    # book/feather/tent are [[object]] blocks, the pose surgery [[player_func]] blocks. A bare marker is flagged.
    from ff9mapkit import build
    p = tmp_path / "sm.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[save_moogle]]\ncarried = true\n',           # marker, but no carried cluster
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[save_moogle]]" in x and "object" in x for x in probs)
    assert any("[[save_moogle]]" in x and "player_func" in x for x in probs)


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


def test_validate_scalar_zone_no_crash(tmp_path):
    # a non-list zone must be a clean lint PROBLEM, never a TypeError from len()
    from ff9mapkit import build
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "B"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[savepoint]]\nzone = 5\n',
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[savepoint]] zone must have 4 or 5 points" in x for x in probs)


# --- rung 1: the save-Moogle model set + the director's refusal REASON -------------------------------
# Census 2026-07-18 over FF9's 55 fields owning a true instruction-aligned Menu(4,0): 41 are built on
# model 220 (GEO_NPC_F0_MOG), 7 on model 129 (GEO_NPC_F1_MOG), 7 (Memoria/Crystal World) have NO model.
# Seeding the cluster on 220 alone silently lost the save point on every model-129 field.
def test_save_moogle_model_set_covers_both_real_variants():
    assert eventscan.SAVE_MOOGLE_MODELS == frozenset({220, 129})
    assert eventscan.SAVE_MOOGLE_MODEL == 220          # the historical scalar name still resolves


def test_save_moogle_model_set_excludes_non_save_moogle_variants():
    # 196/212/198/199 are real GEO_NPC_F*_MOG models but NEVER own a save entry -- seeding on the name
    # pattern would false-positive on decorative moogles standing in a save field.
    assert not ({196, 212, 198, 199} & eventscan.SAVE_MOOGLE_MODELS)


def test_director_report_gives_a_reason_instead_of_a_bare_none():
    # A field with no save Moogle at all: the report must explain, not just return None.
    body, why = eventscan.savepoint_director_report(CLEAN)
    assert body is None
    assert why and isinstance(why, str)


def test_extract_savepoint_director_keeps_its_bytes_or_none_contract():
    # back-compat: the original entry point still returns bytes-or-None, never the (body, reason) tuple.
    out = eventscan.extract_savepoint_director(CLEAN)
    assert out is None or isinstance(out, (bytes, bytearray))


# --- rung 2: the FAITHFUL save flow (option menu -> Yes/No confirm -> latched Menu(4,0)) -------------
# Every real save point asks before it saves -- both families. Moogle family (field 300 entry 3 tag 3):
# EnableDialogChoices + WindowAsync(2,8,3) then WindowAsync(2,8,4) then the save. Moogle-less Memoria
# family (field 2919 entry 7 tag 1): WindowAsync(7,0,454) then 457 then the save. Both bracket the
# Menu(4,0) with GLOB(184)=1 / Wait(3) ... Wait(3) / GLOB(184)=0.
def _ops(body):
    from ff9mapkit.eb import disasm
    return [disasm.op_name(i.op) for i in disasm.iter_code(body, 0, len(body))]


def test_save_act_is_the_real_latched_handshake():
    ops = _ops(_savepoint.save_act())
    assert ops == ["op_05", "op_22", "Menu", "op_22", "op_05"]      # set ; Wait ; Menu ; Wait ; clear
    assert _savepoint.SAVE_LATCH_FLAG == 184 and _savepoint.SAVE_LATCH_WAIT == 3


def test_save_act_latch_can_be_dropped():
    assert _ops(_savepoint.save_act(latch=False)) == ["Menu"]


def test_prompted_dispatch_opens_two_menus_then_saves():
    body = _savepoint.save_dispatch_prompted(500, 501)
    ops = _ops(body)
    assert ops[:2] == ["DisableMove", "DisableMenu"]
    assert ops[-3:] == ["EnableMenu", "EnableMove", "op_04"]
    assert ops.count("WindowSync") == 2 and ops.count("Menu") == 1
    # the real save point's small MENU window (slot 2, flags 8), NOT the dialogue window (1, 128)
    from ff9mapkit.eb import disasm
    wins = [list(i.args) for i in disasm.iter_code(body, 0, len(body)) if disasm.op_name(i.op) == "WindowSync"]
    assert wins == [[2, 8, 500], [2, 8, 501]]


def test_prompted_dispatch_emits_exactly_one_if_block_per_window():
    """The nesting hazard (see savepoint._row0_only): choice.branch re-reads sysvar 9 per option, so a
    second bodied row at either level would test the INNER answer after the nested window overwrote it.
    Only row 0 carries a body, so exactly two jumps exist -- one per window."""
    from ff9mapkit.eb import disasm
    body = _savepoint.save_dispatch_prompted(500, 501)
    assert sum(1 for i in disasm.iter_code(body, 0, len(body))
               if disasm.op_name(i.op) == "op_02") == 2


def test_build_savepoint_ships_the_menu_text_and_the_prompted_flow(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
        '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[-1]
    # prompt + confirm + the ACT's save line (the act ships by default since the choreography landed)
    assert sp_txids == {0: {"prompt": 500, "confirm": 501, "act": 502}}
    assert mes.count("[CHOO]") == 2                       # the option menu + the Yes/No confirm
    assert "[PCHC=2,1]" in mes                            # 2 rows, cancel = row 1
    for row in ("Save", "Cancel", "Yes", "No"):
        assert row in mes
    # ...and BOTH interact points (the press-zone and the visible Moogle's talk) run the prompted flow:
    # WindowSync(2, 8, 500) = `1f 00 02 08 f4 01`, once per entry.
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    assert eb.count(bytes.fromhex("1f000208f401")) == 2
    assert eb.count(bytes.fromhex("1f000208f501")) == 2   # ...and the Yes/No confirm window (txid 501)
    # without the txids (build_script called bare) it MUST fall back to the plain save, never emit a
    # window pointing at text the .mes does not carry.
    assert build.build_script(proj, "us", {}).count(bytes.fromhex("1f000208f401")) == 0


def test_savepoint_dialogue_false_falls_back_to_the_bare_save(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
        '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\ndialogue = false\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, *_rest = build.collect_text(proj)
    assert _rest[-1] == {}                                # no menu text emitted
    assert "[CHOO]" not in mes


def test_savepoint_rejects_unknown_and_mistyped_keys(tmp_path):
    """A mistyped key used to build silently -- `moggle = false` left the Moogle in place with no
    diagnostic. Unknown keys and wrong types are lint problems now."""
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
        '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n'
        'moggle = false\ndialogue = "yes"\nprompt = 7\n',
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("unknown key 'moggle'" in x for x in probs)
    assert any("dialogue must be true or false" in x for x in probs)
    assert any("prompt must be a string" in x for x in probs)


def test_savepoint_accepts_every_documented_key(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
        '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\n'
        'pos = [0, 0]\nmoogle = true\nbubble = true\ndialogue = true\nlatch = true\n'
        'prompt = "P"\nconfirm = "C"\nsave_row = "S"\ncancel_row = "X"\n'
        'yes_row = "Y"\nno_row = "N"\nspeaker = "Mog"\n',
        encoding="utf-8")
    assert not [x for x in build.validate(build.FieldProject.load(p)) if "savepoint" in x.lower()]
