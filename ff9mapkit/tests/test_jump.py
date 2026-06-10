"""Navigable JUMP pillar (Ice Cavern style ledge/gap hops).

Provenance-clean: all arcs are synthesised with the kit's own opcodes and round-tripped through the
injector + scanner (no Square-Enix bytes). The scanner is the exact inverse of the injector, and the
jump scanner is DISJOINT from the ladder scanner (ladder = has the ladder flag, jump = doesn't).
"""
from __future__ import annotations

from ff9mapkit import data, eventscan
from ff9mapkit.content import jump as _jump
from ff9mapkit.content import ladder as _ladder
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.content.ladder import find_player_entry

CLEAN = data.blank_field_bytes("us")
ZONE = [[-100, 100], [100, 100], [100, -100], [-100, -100]]


def _arc(dx=120, dz=240, steps=8):
    """A synthetic one-hop jump arc: jump anim -> SetupJump(dest) -> Jump -> re-enable pathing."""
    return (opcodes.run_jump_animation() + opcodes.setup_jump(dx, dz, 0, steps)
            + opcodes.jump() + opcodes.run_land_animation() + opcodes.set_pathing(1) + opcodes.RETURN)


def _ladder_arc():
    """A synthetic ladder climb (HAS the ladder flag) -- must read as a ladder, never a jump."""
    return (opcodes.add_character_attribute(_ladder.LADDER_FLAG)
            + opcodes.setup_jump(0, 0, 300, 6) + opcodes.jump() + opcodes.set_pathing(0) + opcodes.RETURN)


# --- round-trip: inject -> scan back, byte-identical -------------------------------------
def test_jump_roundtrip_action():
    arc = _arc()
    eb = _jump.ensure_jump_animation(CLEAN)
    eb, _ = _jump.inject_jump(eb, ZONE, arc, jump_tag=_jump.FIRST_JUMP_TAG, trigger="action", bubble=True)
    out = eventscan.scan_jumps(eb)
    assert len(out) == 1
    assert bytes(out[0]["jump"]) == arc                  # verbatim arc survived the graft
    assert out[0]["trigger"] == "action" and out[0]["bubble"] is True
    assert len(out[0]["zone"]) == 4


def test_jump_roundtrip_tread_no_bubble():
    arc = _arc(dx=-80, dz=300)
    eb = _jump.ensure_jump_animation(CLEAN)
    eb, _ = _jump.inject_jump(eb, ZONE, arc, jump_tag=_jump.FIRST_JUMP_TAG, trigger="tread", bubble=False)
    out = eventscan.scan_jumps(eb)
    assert len(out) == 1
    assert out[0]["trigger"] == "tread" and out[0]["bubble"] is False
    assert bytes(out[0]["jump"]) == arc


def test_multiple_jumps_distinct_tags():
    eb = _jump.ensure_jump_animation(CLEAN)
    arcs = [_arc(dx=d) for d in (50, 150, 250)]
    tag = _jump.FIRST_JUMP_TAG
    for a in arcs:
        eb, _ = _jump.inject_jump(eb, ZONE, a, jump_tag=tag, trigger="action")
        tag += 1
    out = eventscan.scan_jumps(eb)
    assert len(out) == 3
    assert {bytes(o["jump"]) for o in out} == {bytes(a) for a in arcs}


# --- the jump animation splice ------------------------------------------------------------
def test_ensure_jump_animation_idempotent():
    eb1 = _jump.ensure_jump_animation(CLEAN)
    eb2 = _jump.ensure_jump_animation(eb1)               # second call must be a no-op
    assert eb2 == eb1
    pe = find_player_entry(EbScript.from_bytes(eb1))
    init = EbScript.from_bytes(eb1).entry(pe).func_by_tag(0)
    sja = [tuple(i.args) for i in EbScript.from_bytes(eb1).instrs(init)
           if i.op == _jump.SET_JUMP_ANIM_OP]
    assert sja == [_jump.JUMP_ANIM_DEFAULT]


# --- disjoint from ladders ----------------------------------------------------------------
def test_jump_and_ladder_are_disjoint():
    # a field carrying BOTH a ladder (flagged climb) and a jump (unflagged arc): each scanner sees
    # only its own kind -- the ladder flag is the discriminator.
    eb = _jump.ensure_jump_animation(CLEAN)
    eb, _ = _ladder.inject_ladder(eb, ZONE, climb_bytes=_ladder_arc(), climb_tag=_ladder.FIRST_CLIMB_TAG)
    eb, _ = _jump.inject_jump(eb, ZONE, _arc(), jump_tag=_jump.FIRST_JUMP_TAG, trigger="action")
    jumps = eventscan.scan_jumps(eb)
    ladders = eventscan.scan_ladders(eb)
    assert len(jumps) == 1 and len(ladders) == 1
    assert bytes(jumps[0]["jump"]) != bytes(ladders[0]["climb"])   # different bodies


def test_clean_field_has_no_jumps():
    assert eventscan.scan_jumps(CLEAN) == []
    assert eventscan.scan_jumps(_jump.ensure_jump_animation(CLEAN)) == []   # the splice alone adds none


# --- the built script parses + carries the player jump function ---------------------------
def test_built_field_parses_and_has_player_jump_func():
    eb = _jump.ensure_jump_animation(CLEAN)
    eb, _ = _jump.inject_jump(eb, ZONE, _arc(), jump_tag=_jump.FIRST_JUMP_TAG)
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    assert parsed.entry(pe).func_by_tag(_jump.FIRST_JUMP_TAG) is not None   # arc grafted onto the player
    # every entry disassembles without error (round-trip stability)
    for e in parsed.entries:
        if e.empty:
            continue
        for f in e.funcs:
            list(parsed.instrs(f))


# --- end-to-end build path (field.toml [[jump]] + arc sidecar -> built .eb) ----------------
def test_build_field_with_jump(tmp_path):
    from ff9mapkit import build
    (tmp_path / "j0.bin").write_bytes(_arc())
    p = tmp_path / "j.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "J"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
        '[player]\nspawn = [0, 0]\n\n'
        '[[jump]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\njump = "j0.bin"\ntrigger = "action"\n',
        encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "jump" in x.lower()]   # lint clean
    eb = build.build_script(proj, "us", {})
    scanned = eventscan.scan_jumps(eb)
    assert len(scanned) == 1 and bytes(scanned[0]["jump"]) == _arc()       # arc made it through build
    s = EbScript.from_bytes(eb)
    pe = find_player_entry(s)
    assert s.entry(pe).func_by_tag(_jump.FIRST_JUMP_TAG) is not None
    assert any(i.op == _jump.SET_JUMP_ANIM_OP for i in s.instrs(s.entry(pe).func_by_tag(0)))


def test_validate_flags_bad_jump(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad.field.toml"
    p.write_text(
        '[field]\nid = 4003\nname = "B"\narea = 11\ntext_block = 1073\n\n'
        '[camera]\npitch = 45\nfov = 42.2\n\n'
        '[walkmesh]\nquad = [[-100,-100],[100,-100],[100,100],[-100,100]]\n\n'
        '[[jump]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\ntrigger = "fly"\n',   # no file, bad trigger
        encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[jump]]" in x and "jump =" in x for x in probs)          # missing arc file
    assert any("[[jump]]" in x and "trigger" in x for x in probs)         # bad trigger
