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
    sp_txids = _rest[9]
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
    assert _rest[9] == {}                                # no menu text emitted
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


# ======================================================================================================
# THE CASK REVEAL ("barrel_pop") -- content/savepoint.py's newest section, docs/SAVEPOINT.md
# ======================================================================================================

def _field_toml(extra_savepoint_lines: str = "", *, spawn: bool = True) -> str:
    spawn_block = "[player]\nspawn = [0, 0]\n\n" if spawn else ""
    return (
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-400,-400],[400,-400],[400,400],[-400,400]]\n\n'
        f'{spawn_block}'
        '[[savepoint]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n'
        f'{extra_savepoint_lines}')


# --- byte-run pins: the exact emitted body, not just op presence ------------------------------------
def test_reveal_spine_body_is_byte_exact():
    """The invariant spine, independently reconstructed from the primitive opcode encoders (so this
    test does not just echo reveal_spine_body's own logic back at itself) AND pinned to a literal hex
    string -- a mutated Wait/reordered step breaks BOTH checks."""
    body = _savepoint.reveal_spine_body(jump_to=(100, -200), steps=10)
    expected = (opcodes.set_jump_animation(_savepoint.REVEAL_HOP_CLIP, 4, 16)
               + opcodes.turn_toward_position(100, -200)
               + opcodes.wait_turn()
               + opcodes.run_jump_animation()
               + opcodes.wait_animation()
               + opcodes.setup_jump(100, -200, 0, 10)
               + opcodes.jump()
               + opcodes.run_land_animation()
               + opcodes.wait_animation())
    assert body == expected
    assert body.hex() == "9400650b04109b00640038ff509c41e2006400000038ff0adc9d41"


def test_reveal_spine_body_with_sfx_and_custom_blend():
    body = _savepoint.reveal_spine_body(jump_to=(0, 0), sfx=1362, blend=(6, 23), steps=15)
    # the reveal's own sfx volume (99, field 407 @1830) -- NOT the ACT's 125 default; see act_sfx's own
    # vol kwarg and REVEAL_SFX_VOL's docstring.
    expected = (opcodes.set_jump_animation(_savepoint.REVEAL_HOP_CLIP, 6, 23)
               + _savepoint.act_sfx(1362, vol=_savepoint.REVEAL_SFX_VOL)
               + opcodes.turn_toward_position(0, 0)
               + opcodes.wait_turn()
               + opcodes.run_jump_animation()
               + opcodes.wait_animation()
               + opcodes.setup_jump(0, 0, 0, 15)
               + opcodes.jump()
               + opcodes.run_land_animation()
               + opcodes.wait_animation())
    assert body == expected
    assert body.hex() == "9400650b0617c80000d0520500000080639b0000000000509c41e2000000000000000fdc9d41"
    assert _savepoint.REVEAL_SFX_VOL == 99


def test_reveal_spine_body_requires_jump_to():
    import pytest
    with pytest.raises(ValueError, match="jump_to"):
        _savepoint.reveal_spine_body(jump_to=None)


def test_reveal_landing_dressing_byte_exact():
    body = _savepoint.reveal_landing_dressing()
    # The DOUBLE WaitTurn is the donors' own: 407 @1866/1867 and 853 both emit it twice (2/2 of the
    # donors that run this dressing). An earlier pass collapsed it to one as a "decode artifact"; the
    # disassembly says otherwise, and act/reveal timing is load-bearing in this kit.
    expected = (opcodes.turn_toward_object(_savepoint.PLAYER_UID, _savepoint.REVEAL_TURN_SPEED)
               + opcodes.wait_turn() + opcodes.wait_turn()
               + opcodes.encode(0x91, 1) + opcodes.encode(0x4B, 40, 40, 55))
    assert body == expected
    assert body.hex() == "5100fa305050" "9100014b00282837"
    assert body.count(opcodes.wait_turn()) == 2, "the donors' second WaitTurn must not be optimised away"


# --- tent_rest_body: the donor's fade-to-white REST PRESENTATION (fix 1) -------------------------------
def test_tent_rest_body_wraps_the_heals_in_the_donor_fade_bracket():
    """The heals themselves are byte-identical to the donor already (test_tent_heals_half_of_max_and_
    never_revives / test_tent_dispatch_rests_on_yes_and_not_on_no, tests/test_mognet.py, which execute
    them through the mini-VM); this pins the PRESENTATION bracket around them -- the fix for the
    2026-07-19 playtest report "tent is a no-op, it takes a tent but doesn't do anything." Reconstructed
    independently from the primitive opcode encoders (so this does not just echo tent_rest_body's own
    logic back at itself), and RemoveItem must land strictly AFTER the fade-back -- the donor's own order
    (field 300 @4925-5608), not before the heals."""
    body = _savepoint.tent_rest_body()
    lead = (_savepoint.act_sfx(_savepoint.TENT_SFX_REST)
           + opcodes.encode(0xA9, _savepoint.PLAYER_UID)             # CalculateScreenPosition(player)
           + opcodes.encode(0xEC, 6, 24, 255, 255, 255, 255)         # fade OUT to white
           + opcodes.wait(16)
           + _savepoint.act_sfx(_savepoint.TENT_SFX_SLEEP)
           + opcodes.wait(8)
           + opcodes.encode(0xD5))                                    # HideAllObjects
    tail = (opcodes.encode(0xA9, _savepoint.PLAYER_UID)
           + opcodes.encode(0xEC, 7, 16, 255, 0, 0, 0)                # fade back IN
           + opcodes.wait(20)
           + opcodes.remove_item(_savepoint.TENT_ITEM, 1))
    assert body.startswith(lead)
    assert body.endswith(tail)
    assert lead.hex() == "c80000d05305000000807da900faec000618ffffffff220010c80000d0ce04000000807d220008d5"
    assert tail.hex() == "a900faec000710ff0000002200144900fd0001"
    assert _savepoint.TENT_SFX_REST == 1363 and _savepoint.TENT_SFX_SLEEP == 1230
    # RemoveItem strictly AFTER the fade-back, not interleaved with or ahead of the heals
    fade_back = opcodes.encode(0xEC, 7, 16, 255, 0, 0, 0)
    remove = opcodes.remove_item(_savepoint.TENT_ITEM, 1)
    assert body.rindex(remove) > body.rindex(fade_back)
    assert body.count(remove) == 1                     # exactly one Tent consumed, not per-slot


# --- reveal_state_loop: THE VERTICAL HOP, no authored landing coordinate -----------------------------
def test_reveal_state_loop_pop_lands_at_container_xz_raised_by_height():
    """No authored landing coordinate exists any more -- the pop is a VERTICAL hop, so the landing is
    computed as the container's own x/z with y raised by ``height``. Anchored on field 407's own donor
    cask (kit x=-250, z=-571, y=+2, height=360): the emitted SetupJump raw args match the donor's own
    bytes exactly (the coordinate-convention note above REVEAL_STATE_IN -- y is up-positive here and
    negated on encode, so kit y=362 encodes as the donor's raw -362 = 65174).

    The stow arm now ALSO ballistic-jumps (a real ``SetupJump``/``Jump``, not the old teleport -- see
    :func:`test_reveal_state_loop_hide_returns_to_containers_own_y`), so the loop carries TWO SetupJump
    calls; the pop's is always the FIRST one emitted (the POP_REQ arm is written before the HIDE_REQ arm,
    see :func:`test_reveal_state_loop_structure_two_arms_and_loops_back`)."""
    body = _savepoint.reveal_state_loop(container_pos=(-250, -571, 2), height=360, steps=10)
    from ff9mapkit.eb import disasm
    jumps = [list(i.args) for i in disasm.iter_code(body, 0, len(body))
             if disasm.op_name(i.op) == "SetupJump"]
    assert len(jumps) == 2
    assert jumps[0] == [65286, 65174, 64965, 10]      # donor field 407's own raw SetupJump args (pop)


def test_reveal_state_loop_hide_returns_to_containers_own_y():
    """Stowing (HIDE_REQ) is now a REAL ballistic jump back down -- the donor's own case-102
    ``SetupJump(-250, -2, -571, 10) ; Jump()`` (field 407 tag 3 @8674), not the old ``MoveInstantXZY``
    teleport (a moogle that just blinked out of existence). The stow's SetupJump target is the
    CONTAINER'S OWN raw y -- unraised, unlike the pop's -- and its raw args are byte-for-byte the same
    three numbers the old teleport carried, with the jump's ``steps`` appended as a 4th arg."""
    body = _savepoint.reveal_state_loop(container_pos=(-250, -571, 2), height=360, steps=10)
    from ff9mapkit.eb import disasm
    ops = [i for i in disasm.iter_code(body, 0, len(body))]
    names = [disasm.op_name(i.op) for i in ops]
    assert "MoveInstantXZY" not in names                                   # the old teleport is GONE
    jumps = [list(i.args) for i in ops if disasm.op_name(i.op) == "SetupJump"]
    assert jumps[-1] == [65286, 65534, 64965, 10]     # donor field 407's own raw SetupJump args (stow)
    # the stow's own SetupJump is immediately followed by Jump() -- a real ballistic hop, not just a
    # SetupJump call sitting there unused
    last_setup = max(k for k, n in enumerate(names) if n == "SetupJump")
    assert names[last_setup + 1] == "Jump"


def test_reveal_state_loop_structure_two_arms_and_loops_back():
    """The moogle's WHOLE tag-1 (installed via ``replace_function_body``, not a one-shot ``intro``
    splice): two state-gated arms (POP_REQ -> pop, HIDE_REQ -> hide), the hide arm's own ballistic jump
    back down (a real ``SetupJump``/``Jump`` pair, not the old ``MoveInstantXZY`` teleport) landing before
    its final hide, then a backward jump -- the donor's own permanent-loop shape, so the moogle can pop
    out AND go back in, unlike the old one-shot intro."""
    body = _savepoint.reveal_state_loop(container_pos=(0, 0, 0))
    from ff9mapkit.eb import disasm
    ops = [disasm.op_name(i.op) for i in disasm.iter_code(body, 0, len(body))]
    assert ops[-1] == "op_01"                                 # jump back to the top, forever
    assert ops.count("op_02") == 2                             # exactly two gated arms
    assert ops.count("SetObjectFlags") == 2                    # SHOW (pop) + HIDE (hide)
    assert "MoveInstantXZY" not in ops                         # the old teleport is GONE (a real jump now)
    # both arms now carry the airborne spine (SetJumpAnimation ... Jump), one each -- pop's first, then
    # the stow's own, both landing before the container-hide flags write
    assert ops.count("SetJumpAnimation") == 2 and ops.count("Jump") == 2
    show_idx, hide_idx = [k for k, o in enumerate(ops) if o == "SetObjectFlags"]
    jump_idxs = [k for k, o in enumerate(ops) if o == "Jump"]
    assert show_idx < ops.index("SetJumpAnimation") < jump_idxs[0] < hide_idx   # the pop's own hop
    assert jump_idxs[1] < hide_idx              # the stow's own ballistic jump lands BEFORE the hide


def _pathing_args(body: bytes) -> list:
    from ff9mapkit.eb import disasm
    return [i.args[0] for i in disasm.iter_code(body, 0, len(body))
            if disasm.op_name(i.op) == "SetPathing"]


def test_act_pathing_detaches_off_floor_attaches_on_floor():
    """THE 2026-07-19 LIVE BUG'S FIX (root-caused 2026-07-22 by the full 407 decode + walkmesh probe):
    the donor act calls SetPathing(1) at BOTH lerp ends and survives the perch-side call only because
    its cask corner has NO walkmesh triangle (verified against 407's .bgi). A kit cask usually sits ON
    walkable ground, so re-attaching at the perch snapped the moogle down INTO the barrel after a save.
    The kit now derives the pathing arg from each spot's own height: floor spot (y == 0) -> attach (1),
    off-floor spot -> DETACH (0). Ground savepoints stay byte-identical."""
    kw = dict(book_uid=20, feather_uid=21, pose_tag=30, release_tag=31)
    # barrel_pop shape: rest = the perch (y=362), hop_to = the ground save spot (y=2 = container base)
    body = _savepoint.act_save_body(rest=(-250, -571, 362), hop_to=(-150, -571, 0), **kw)
    assert _pathing_args(body) == [1, 0]        # ground landing attaches; the perch return DETACHES
    # plain ground savepoint: both spots on the floor -> both attach, exactly the pre-fix bytes
    flat = _savepoint.act_save_body(rest=(-250, -571), hop_to=(-150, -571), **kw)
    assert _pathing_args(flat) == [1, 1]
    # hop-in-place at a perch (no hop_to): the single spot is off-floor at both sites
    perch = _savepoint.act_save_body(rest=(-250, -571, 362), hop_to=None, **kw)
    assert _pathing_args(perch) == [0, 0]


def test_reveal_state_loop_pathing_detach_on_perch_reattach_on_stow():
    """The pop arm lands OFF-floor (the container top) -> it must detach (SetPathing(0)) so nothing can
    snap the perched moogle down into the container; the stow arm lands back ON the floor -> it
    re-attaches (SetPathing(1)). Order within the loop: pop's detach first, stow's attach second."""
    body = _savepoint.reveal_state_loop(container_pos=(-250, -571, 2), height=360, steps=10)
    assert _pathing_args(body) == [0, 1]


def test_save_menu_mognet_reopen_cycle():
    """Mognet is a SUBMENU of the save menu (the donor cycle): its row's completion sets the reopen
    bit and the dispatch loops back to the MENU WINDOW -- not out of the talk. Without reopen_rows
    the emitted bytes are the original shape (byte-identity for every non-mognet save point)."""
    import pytest
    from ff9mapkit.eb.disasm import iter_code
    rows = ["save", "mognet", "cancel"]
    bodies = {"save": _savepoint.save_confirm_body(11), "mognet": opcodes.wait(3)}
    plain = _savepoint.save_dispatch_menu(10, rows, bodies)
    looped = _savepoint.save_dispatch_menu(10, rows, bodies, reopen_rows=("mognet",), reopen_index=0)
    assert plain != looped
    # the plain form has NO reopen-bit tokens at all
    import struct as _s
    bit_tok = bytes([0xE5]) + _s.pack("<H", _savepoint.menu_reopen_bit(0))
    assert bit_tok not in plain
    # the looped form: bit cleared at the loop top, set at the mognet arm's end, and a backward
    # jump whose target is the loop top (the clear)
    assert looped.count(bit_tok) == 3                       # clear + arm set + the loop condition
    back = [i for i in iter_code(looped, 0, len(looped)) if i.op == 0x01 and i.imm(0) >= 0x8000]
    assert len(back) == 1                                    # exactly one backward jump (the reopen)
    with pytest.raises(ValueError):
        _savepoint.menu_reopen_bit(_savepoint.MENU_REOPEN_MAX)


def test_reveal_init_tail_byte_exact():
    assert _savepoint.reveal_init_tail().hex() == "93000e"          # SetObjectFlags(14)
    assert _savepoint.reveal_init_tail() == opcodes.encode(0x93, _savepoint.REVEAL_HIDE_FLAGS)


def test_cask_init_byte_shape():
    body = _savepoint.build_cask_init(5, -5)
    from ff9mapkit.eb import disasm
    ops = [(disasm.op_name(i.op), list(i.args) if i.args else i.args)
           for i in disasm.iter_code(body, 0, len(body))]
    # the 4 opcodes the task brief cites, in that order, with those exact args
    named = [o for o in ops if o[0] in ("SetModel", "SetStandAnimation", "SetObjectLogicalSize", "SetObjectFlags")]
    assert named == [("SetModel", [241, 93]), ("SetStandAnimation", [1904]),
                     ("SetObjectLogicalSize", [1, 50, 50]), ("SetObjectFlags", [37])]
    assert ops[-1] == ("op_04", [])                                 # RETURN


def test_cask_trigger_body_byte_exact_and_one_shot_guard():
    """No handshake bit any more -- the guard, the POP_REQ write, and the poll all key off the SAME
    state byte (:func:`reveal_vars`), independently reconstructed from the primitive encoders below and
    pinned to a literal hex string."""
    body = _savepoint.cask_trigger_body()
    from ff9mapkit.content import region as _region2
    from ff9mapkit.eb import opcodes as _op2
    state_idx, _hs = _savepoint.reveal_vars(0)
    expected = (_region2.if_block(_savepoint._cond_neq(_region2.GLOB_UINT8, state_idx,
                                                        _savepoint.REVEAL_STATE_IN), _op2.RETURN)
               + _op2.DISABLE_MOVE
               + _region2.set_var(_region2.GLOB_UINT8, state_idx, _savepoint.REVEAL_STATE_POP_REQ)
               + _savepoint._while_not_eq(_region2.GLOB_UINT8, state_idx, _savepoint.REVEAL_STATE_OUT,
                                         _op2.wait(1))
               + _op2.ENABLE_MOVE + _op2.RETURN)
    assert body == expected
    assert body.hex() == "05d5207d0000217f020100042d05d5207d01002c7f05d5207d0200217f02060022000101efff2e04"
    from ff9mapkit.eb import disasm
    ops = [disasm.op_name(i.op) for i in disasm.iter_code(body, 0, len(body))]
    # the one-shot guard is the FIRST thing: if (state != IN) return -- structurally, an op_05 cond,
    # an op_02 (jump-if-false, skipping the return), then op_04 (return) right there
    assert ops[0] == "op_05" and ops[1] == "op_02" and ops[2] == "op_04"
    assert ops[3] == "DisableMove" and ops[-2:] == ["EnableMove", "op_04"]


# --- the moogle model resolves through the kit's own prop-archetype catalog -------------------------
def test_cask_model_resolves_via_prop_archetype_catalog():
    from ff9mapkit import prop_archetypes as _pa
    assert _pa.resolve("cask") == (241, 1904)
    assert _pa.resolve("barrel") == _pa.resolve("cask")             # alias
    assert _pa.resolve("crate") == _pa.resolve("cask")               # alias


# --- inject_barrel_pop_reveal + full field build ------------------------------------------------------
def test_inject_barrel_pop_reveal_round_trips_and_orders_cask_before_prediction():
    """``inject_barrel_pop_reveal`` now returns a 2-tuple -- ``(new_data, moogle_init_tail)`` -- the
    intro splice is gone; the moogle's loop is installed separately via ``reveal_state_loop`` +
    ``replace_function_body`` (see build.py). The tail STOWS the moogle: hidden AND collision-shrunk."""
    g, tail = _savepoint.inject_barrel_pop_reveal(CLEAN, container_pos=(0, 0))
    p = EbScript.from_bytes(g)
    assert p.to_bytes() == g
    assert tail == (_savepoint.reveal_init_tail()
                    + opcodes.encode(0x4B, *_savepoint.REVEAL_IN_LOGICAL_SIZE))
    assert tail.hex() == "93000e4b00080801"
    # a cask entry (a type-2 object, tags {0, 3}, no tag 1) now exists
    cask_entries = [e.index for e in p.entries if not e.empty and {f.tag for f in e.funcs} == {0, 3}]
    assert cask_entries


def test_inject_barrel_pop_reveal_container_false_skips_the_cask():
    g, _tail = _savepoint.inject_barrel_pop_reveal(CLEAN, container_pos=(0, 0), container=False)
    base_entries = sum(1 for e in EbScript.from_bytes(CLEAN).entries if not e.empty)
    new_entries = sum(1 for e in EbScript.from_bytes(g).entries if not e.empty)
    assert new_entries == base_entries                              # nothing was appended


# --- the default is UNCHANGED: byte-identical with no reveal_style vs an explicit "instant" ----------
def test_default_reveal_style_is_byte_identical_to_no_reveal_style_at_all(tmp_path):
    from ff9mapkit import build
    p1 = tmp_path / "a.field.toml"
    p1.write_text(_field_toml(), encoding="utf-8")
    p2 = tmp_path / "b.field.toml"
    p2.write_text(_field_toml('reveal_style = "instant"\n'), encoding="utf-8")
    eb1 = build.build_script(build.FieldProject.load(p1), "us", {})
    eb2 = build.build_script(build.FieldProject.load(p2), "us", {})
    assert eb1 == eb2
    # and neither ships a cask entry (a type-2 object with a SetModel(241, ...) in its Init)
    s = EbScript.from_bytes(eb1)
    cask_entries = [e.index for e in s.entries if not e.empty and {f.tag for f in e.funcs} == {0, 3}
                    and any(i.op == 0x2F and list(i.args)[:1] == [241]
                            for f in e.funcs for i in s.instrs(f))]
    assert not cask_entries


# --- validation: every reveal_* rule --------------------------------------------------------------
def test_validate_reveal_style_unknown_value(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "flying"\n'), encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("reveal_style must be one of" in x and "'flying'" in x for x in probs)


def test_validate_barrel_pop_needs_no_landing_coordinate(tmp_path):
    """The redesign made the landing purely DERIVED (the container's own x/z, raised by reveal_height) --
    unlike the old hand-placed reveal_jump_to, a bare reveal_style = "barrel_pop" with no other reveal_*
    key at all must validate clean. (The old requirement -- 'reveal_jump_to ... hand-placed' -- is gone;
    there is no longer any authored landing coordinate for the POP to require.)

    ``act = false`` here isolates that claim from the SEPARATE, unrelated requirement fix 4 added --
    ``act_hop_to`` is not a ``reveal_*`` key; it is the ACT's own floor-visit spot, required only when
    the act is on (see ``test_validate_barrel_pop_with_act_needs_act_hop_to``)."""
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nact = false\n'), encoding="utf-8")
    probs = [x for x in build.validate(build.FieldProject.load(p)) if "savepoint" in x.lower()]
    assert not probs


def test_validate_barrel_pop_with_act_needs_act_hop_to(tmp_path):
    """``reveal_style = "barrel_pop"`` with the act ON (the default) DOES need a hand-placed coordinate --
    just not the pop's own. The donor performs the save on the FLOOR: it leaps off the cask to a ground
    spot, opens the book there, and leaps back up. Without ``act_hop_to`` the act would play on top of
    the container, and the act's own ``SetPathing(1)`` would drop the moogle off its perch mid-flourish
    (playtest-driven fix). Neither an explicit ``act = false`` nor ``dialogue = false`` needs it -- the
    act never fires without dialogue, and doesn't exist without itself."""
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\n'), encoding="utf-8")   # act defaults True
    probs = [x for x in build.validate(build.FieldProject.load(p)) if "savepoint" in x.lower()]
    assert any("needs act_hop_to" in x for x in probs)
    # giving it clears the problem
    p2 = tmp_path / "s2.field.toml"
    p2.write_text(_field_toml('reveal_style = "barrel_pop"\nact_hop_to = [5, 5]\n'), encoding="utf-8")
    probs2 = [x for x in build.validate(build.FieldProject.load(p2)) if "savepoint" in x.lower()]
    assert not probs2
    # act = false sidesteps the requirement entirely -- no act, no floor visit, nothing to place
    p3 = tmp_path / "s3.field.toml"
    p3.write_text(_field_toml('reveal_style = "barrel_pop"\nact = false\n'), encoding="utf-8")
    probs3 = [x for x in build.validate(build.FieldProject.load(p3)) if "savepoint" in x.lower()]
    assert not probs3


def test_validate_reveal_keys_are_noops_error_outside_barrel_pop(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_from = [1, 2]\n'), encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("reveal_from" in x and "no-ops" in x for x in probs)


def test_validate_barrel_pop_requires_moogle(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nmoogle = false\n'), encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("needs the moogle" in x for x in probs)


def test_validate_reveal_from_must_be_2_or_3_ints(tmp_path):
    """``reveal_from`` (the container's own spot) is the ONLY surviving reveal_* coordinate key --
    ``reveal_jump_to``/``reveal_face`` are gone entirely, TOML keys and function parameters alike."""
    cases = {
        "too few": 'reveal_style = "barrel_pop"\nreveal_from = [1]\n',
        "too many": 'reveal_style = "barrel_pop"\nreveal_from = [1, 2, 3, 4]\n',
    }
    from ff9mapkit import build
    for label, lines in cases.items():
        p = tmp_path / "s.field.toml"
        p.write_text(_field_toml(lines), encoding="utf-8")
        probs = build.validate(build.FieldProject.load(p))
        assert any("reveal_from" in x and "[x, z]" in x for x in probs), (label, probs)


def test_validate_reveal_steps_sfx_container_types(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\n'
                             'reveal_steps = "ten"\nreveal_sfx = "boom"\nreveal_container = "yes"\n'),
                encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("reveal_steps must be an integer" in x for x in probs)
    assert any("reveal_sfx must be an integer sound id or false" in x for x in probs)
    assert any("reveal_container must be true or false" in x for x in probs)


def test_validate_reveal_sfx_false_is_valid(tmp_path):
    # act = false sidesteps the unrelated act_hop_to requirement (fix 4) so this stays focused on
    # reveal_sfx = false specifically -- see test_validate_barrel_pop_with_act_needs_act_hop_to.
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nreveal_sfx = false\nact = false\n'),
                encoding="utf-8")
    probs = [x for x in build.validate(build.FieldProject.load(p)) if "savepoint" in x.lower()]
    assert not probs


# --- act + barrel_pop composed: BOTH Init tails present, in the donor's order -------------------------
def test_act_and_barrel_pop_compose_init_tails_in_donor_order(tmp_path):
    """The moogle spawns STOWED: hidden AND collision-shrunk (see
    ``test_inject_barrel_pop_reveal_round_trips_and_orders_cask_before_prediction``), so composed with the
    ACT the Init tail is now a 3-step chain -- SetObjectFlags(14) -> SetObjectLogicalSize(8,8,1) ->
    SetJumpAnimation(6503,26,30) -- not the old direct SetObjectFlags(14)->SetJumpAnimation adjacency."""
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nact = true\n'), encoding="utf-8")
    proj = build.FieldProject.load(p)
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[9]
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    s = EbScript.from_bytes(eb)
    assert s.to_bytes() == eb
    found = False
    for e in s.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        ops = list(s.instrs(f0))
        for k, i in enumerate(ops):
            if i.op == 0x93 and list(i.args) == [_savepoint.REVEAL_HIDE_FLAGS]:
                nxt1 = ops[k + 1] if k + 1 < len(ops) else None
                nxt2 = ops[k + 2] if k + 2 < len(ops) else None
                if (nxt1 is not None and nxt1.op == 0x4B
                        and list(nxt1.args) == list(_savepoint.REVEAL_IN_LOGICAL_SIZE)
                        and nxt2 is not None and nxt2.op == 0x94 and list(nxt2.args) == [6503, 26, 30]):
                    found = True
    assert found, ("expected SetObjectFlags(14) -> SetObjectLogicalSize(8,8,1) -> "
                   "SetJumpAnimation(6503,26,30) -- stow-collision write between the reveal's hide and "
                   "the act's hop-clip preload")


def test_act_and_barrel_pop_compose_without_act_no_second_tail(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nact = false\n'), encoding="utf-8")
    proj = build.FieldProject.load(p)
    # a bare `build_script(proj, "us", {})` (no savepoint_txids) makes the moogle's talk fall back to the
    # plain save_dispatch(), which reveal_menu_cycle's new tail check (fix 2) then rejects -- go through
    # collect_text for real dialogue txids, matching how the production build pipeline always calls this
    # (see test_act_and_barrel_pop_compose_init_tails_in_donor_order, this test's sibling, right above).
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[9]
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    s = EbScript.from_bytes(eb)
    assert s.to_bytes() == eb
    # the hidden flag write exists (the reveal), but nowhere is it immediately followed by the act preload
    for e in s.entries:
        if e.empty:
            continue
        f0 = e.func_by_tag(0)
        if f0 is None:
            continue
        ops = list(s.instrs(f0))
        for k, i in enumerate(ops):
            if i.op == 0x93 and list(i.args) == [_savepoint.REVEAL_HIDE_FLAGS]:
                nxt = ops[k + 1] if k + 1 < len(ops) else None
                assert not (nxt is not None and nxt.op == 0x94 and list(nxt.args) == [6503, 26, 30])


# --- reveal_menu_cycle: refuses to wrap a body without the expected tail (fix 2) ----------------------
def test_reveal_menu_cycle_wraps_a_well_formed_body():
    """The normal case: a body ending in the standard dispatch tail wraps cleanly into the loop-then-stow
    cycle, with that exact tail re-emitted once at the real end (not duplicated, not dropped)."""
    tail = opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE + opcodes.RETURN
    body = opcodes.DISABLE_MOVE + opcodes.DISABLE_MENU + tail
    out = _savepoint.reveal_menu_cycle(body, index=0)
    assert out.endswith(tail)
    assert out.count(tail) == 1                       # not appended past itself, not dropped


def test_reveal_menu_cycle_raises_on_body_without_expected_tail():
    """The dead-code bug this fix closed: the first version appended the reopen-loop AFTER the body's own
    ``ENABLE_MENU + ENABLE_MOVE + RETURN``, which is unreachable code -- cancel never stowed the moogle
    and the menu never reopened (playtest, 2026-07-19). Rather than silently repeat that mistake on any
    body that doesn't end in the expected tail, the function now refuses outright."""
    import pytest
    # missing the tail entirely
    with pytest.raises(ValueError, match="does not end in the expected"):
        _savepoint.reveal_menu_cycle(b"\x00\x00\x00", index=0)
    # the bare no-text fallback (savepoint.save_dispatch()) is exactly this shape: it ends in
    # EnableMove + RETURN, but never opens/closes the MENU (DisableMenu/EnableMenu) -- one opcode short
    # of the tail reveal_menu_cycle requires.
    with pytest.raises(ValueError, match="does not end in the expected"):
        _savepoint.reveal_menu_cycle(_savepoint.save_dispatch(), index=0)
    # a truncated tail (RETURN dropped) must also refuse, not silently wrap
    short_tail = opcodes.ENABLE_MENU + opcodes.ENABLE_MOVE
    with pytest.raises(ValueError, match="does not end in the expected"):
        _savepoint.reveal_menu_cycle(opcodes.DISABLE_MOVE + short_tail, index=0)


# --- one-shot: the cask cannot re-fire (structural: the guard body IS the first 3 instructions) -------
def test_cask_one_shot_guard_present_in_built_field(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\n'), encoding="utf-8")
    proj = build.FieldProject.load(p)
    # go through collect_text for real savepoint_txids -- a bare `build_script(proj, "us", {})` falls
    # back to the plain save_dispatch() (no text collected), which reveal_menu_cycle's new tail check
    # (fix 2) then rejects; the production pipeline always resolves txids first.
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[9]
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    s = EbScript.from_bytes(eb)
    cask_entries = [e.index for e in s.entries if not e.empty and {f.tag for f in e.funcs} == {0, 3}]
    assert cask_entries
    for idx in cask_entries:
        f3 = s.entry(idx).func_by_tag(3)
        ops = list(s.instrs(f3))
        assert ops[0].op == 0x05 and ops[1].op == 0x02 and ops[2].op == 0x04   # cond ; jmp-false ; RETURN
        # the guard's condition tests REVEAL_STATE_IDX (MAP.Byte[32]) for inequality against IN (0) --
        # only while stowed; once OUT the moogle itself is the interact target
        cond_bytes = eb[ops[0].off:ops[0].end]
        assert cond_bytes == _savepoint._cond_neq(_region.GLOB_UINT8, _savepoint.REVEAL_STATE_IDX,
                                                  _savepoint.REVEAL_STATE_IN)


# --- the review fixes: per-save-point rendezvous vars, and the gated press-zone ----------------------
# Both were CONFIRMED defects in the first build of this feature (adversarial review, 2026-07-19),
# reproduced end to end. These pin the fixes.

def test_reveal_vars_are_per_savepoint_not_per_field():
    """A field may hold several barrel_pop save points. Sharing one MAP state byte + handshake bit made
    every cask drive every moogle (press one -> all pop, the rest go inert)."""
    assert _savepoint.reveal_vars(0) == (_savepoint.REVEAL_STATE_IDX, _savepoint.REVEAL_HANDSHAKE_BIT)
    seen = {_savepoint.reveal_vars(k) for k in range(_savepoint.REVEAL_MAX_PER_FIELD)}
    assert len(seen) == _savepoint.REVEAL_MAX_PER_FIELD          # every pair distinct
    # the state BYTES and the handshake BITS index different address spaces, but the reserved bit range
    # must still land clear of the reserved state bytes when read as bytes (bit b lives in byte b // 8).
    assert {s for s, _ in seen}.isdisjoint({b // 8 for _, b in seen})
    # the emitted bodies must actually differ, not just the constants
    assert _savepoint.cask_trigger_body(0) != _savepoint.cask_trigger_body(1)
    assert (_savepoint.reveal_state_loop(container_pos=(1, 2), index=0)
            != _savepoint.reveal_state_loop(container_pos=(1, 2), index=1))
    # past the reserved band it must RAISE, never wrap into a neighbouring reserved var
    import pytest
    with pytest.raises(ValueError):
        _savepoint.reveal_vars(_savepoint.REVEAL_MAX_PER_FIELD)


def test_two_barrel_pop_savepoints_do_not_share_vars(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-600,-600],[600,-600],[600,600],[-600,600]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[savepoint]]\nzone = [[-100,-100],[100,-100],[100,100],[-100,100]]\npos = [0, 0]\n'
        'reveal_style = "barrel_pop"\nreveal_from = [5, -5, 10]\nact_hop_to = [50, -50]\n\n'
        '[[savepoint]]\nzone = [[300,-100],[500,-100],[500,100],[300,100]]\npos = [400, 0]\n'
        'reveal_style = "barrel_pop"\nact_hop_to = [450, -50]\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "savepoint" in x.lower()]
    # go through collect_text for real savepoint_txids -- a bare `build_script(proj, "us", {})` falls
    # back to the plain save_dispatch() (no text collected), which reveal_menu_cycle's new tail check
    # (fix 2) then rejects; the production pipeline always resolves txids first.
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[9]
    eb = build.build_script(proj, "us", {}, savepoint_txids=sp_txids)   # 3-element reveal_from must NOT crash
    assert _savepoint.cask_trigger_body(0) in eb            # each cask carries its OWN rendezvous pair
    assert _savepoint.cask_trigger_body(1) in eb


def test_more_barrel_pops_than_reserved_vars_is_a_build_error(tmp_path):
    from ff9mapkit import build
    n = _savepoint.REVEAL_MAX_PER_FIELD + 1
    blocks = "".join(
        f'[[savepoint]]\nzone = [[{i*300-50},-50],[{i*300+50},-50],[{i*300+50},50],[{i*300-50},50]]\n'
        f'pos = [{i*300}, 0]\nreveal_style = "barrel_pop"\n\n'
        for i in range(n))
    p = tmp_path / "s.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "S"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-900,-900],[1900,-900],[1900,900],[-900,900]]\n\n'
        '[player]\nspawn = [0, 0]\n\n' + blocks, encoding="utf-8")
    probs = [x for x in build.validate(build.FieldProject.load(p)) if "barrel_pop" in x]
    assert probs and "cross-talk" in probs[0]


def test_barrel_pop_gates_the_press_zone_but_instant_does_not(tmp_path):
    """Without the gate the player saves from the zone with the moogle still in the cask -- the reveal
    would gate nothing and the cask would be decoration."""
    from ff9mapkit import build
    gate = _savepoint.gate_until_revealed(b"", 0)
    p = tmp_path / "bp.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nact_hop_to = [5, 5]\n'), encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "savepoint" in x.lower()]
    # go through collect_text for real savepoint_txids -- a bare `build_script(proj, "us", {})` falls
    # back to the plain save_dispatch() (no text collected), which reveal_menu_cycle's new tail check
    # (fix 2) then rejects; the production pipeline always resolves txids first.
    mes, *_rest = build.collect_text(proj)
    sp_txids = _rest[9]
    assert gate in build.build_script(proj, "us", {}, savepoint_txids=sp_txids)
    # the "instant" (non-barrel_pop) sibling never touches reveal_menu_cycle at all, so it still builds
    # fine bare (no text collected) -- unchanged from before the fixes.
    q = tmp_path / "inst.field.toml"
    q.write_text(_field_toml(""), encoding="utf-8")
    eb_i = build.build_script(build.FieldProject.load(q), "us", {})
    assert gate not in eb_i
    assert _savepoint.reveal_init_tail() not in eb_i        # the default carries NO reveal bytes at all


def test_reveal_menu_cycle_reopen_jump_lands_on_the_loop_top(tmp_path):
    """The reopen jump must land on an INSTRUCTION BOUNDARY at the loop top.

    Regression: the displacement omitted the if-condition's length, so it landed 5 bytes past the top --
    mid-instruction. In game that executed garbage after a save (the moogle stowed itself instead of
    staying on the cask, and the following Cancel softlocked). Playtest 2026-07-19.
    """
    from ff9mapkit import build
    from ff9mapkit.eb import disasm
    p = tmp_path / "bp.field.toml"
    p.write_text(_field_toml('reveal_style = "barrel_pop"\nact_hop_to = [-300, -900]\n'), encoding="utf-8")
    proj = build.FieldProject.load(p)
    _mes, *rest = build.collect_text(proj)
    eb = build.build_script(proj, "us", {}, savepoint_txids=rest[9])
    s = EbScript.from_bytes(eb)
    # the save moogle is the entry carrying the reveal state loop (tags 0/1/3)
    moogle = [e for e in s.entries
              if not e.empty and {f.tag for f in e.funcs} == {0, 1, 3}][-1]
    ops = list(s.instrs(moogle.func_by_tag(3)))
    starts = {i.off for i in ops}
    backward = []
    for i in ops:
        if i.name == "op_01" and i.imm(0) is not None:
            d = i.imm(0) - 65536 if i.imm(0) > 32767 else i.imm(0)
            if d < 0:
                backward.append((i, i.off + i.length + d))
    assert backward, "the barrel_pop talk handler must contain the reopen loop's backward jump"
    for ins, tgt in backward:
        assert tgt in starts, (f"backward jump at {ins.off} targets {tgt}, which is NOT an instruction "
                               f"boundary -- it would execute garbage")
    # and the reopen jump specifically lands on the `reopen = 0` clear that opens the loop
    reopen_clear = _region.set_var(_region.MAP_BOOL, _savepoint.reveal_vars(0)[1], 0)
    assert any(eb[tgt:tgt + len(reopen_clear)] == reopen_clear for _i, tgt in backward), \
        "no backward jump lands on the loop's `reopen = 0` top"
