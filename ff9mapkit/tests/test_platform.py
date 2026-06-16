"""Carry-platform pillar (Pandemonium-elevator style: the player is physically carried within one
field by a scripted MoveInstantXZY ride, control disabled, no Field() re-entry).

Provenance-clean: the ride is synthesised with the kit's own opcodes (the navigable-climb primitives
minus the d-pad). Tests assert the graft + arm round-trips, the ride loop terminates, the direction is
derived from board/arrive height, and the composed .eb stays structurally sound (eblint).
"""
from __future__ import annotations

from ff9mapkit import data, eblint
from ff9mapkit.content import platform as _platform
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code
from ff9mapkit.content.ladder import find_player_entry

CLEAN = data.blank_field_bytes("us")
ZONE = [[-100, 100], [100, 100], [100, -100], [-100, -100]]


def _ops(body: bytes) -> list:
    return [ins.op for ins in iter_code(bytes(body), 0, len(body))]


def _new_errors(eb: bytes) -> list:
    """eblint errors introduced by the platform graft -- ignores the blank field's own pre-existing
    empty Main_Loop placeholder (entry0/tag1), which the kit's blank template ships with and no graft
    here touches. So this still catches ANY new fault (bad jump offset, dangling target, ...)."""
    return [e for e in eblint.errors(eblint.lint_eb(eb))
            if not (e.where == "entry0/tag1" and "empty function body" in e.message)]


# --- the ride body: structure + termination ----------------------------------------------
def test_carry_body_has_terminating_loop():
    body = _platform.carry_body((0, 0, 0), (0, 0, 200), duration=32)
    ops = _ops(body)
    assert ops.count(0xA1) == 3                  # board snap + per-frame loop snap + exact final snap
    assert 0x22 in ops                           # Wait(1) in the loop
    assert 0x03 in ops                           # JMP_TRUE -- the loop back-edge (so it can repeat)
    assert ops[-1] == 0x04                        # ends in RETURN
    assert 0xA8 in ops                           # SetPathing (detach at board, re-attach at land)


def test_carry_direction_derived_from_height():
    up = _platform.carry_body((0, 0, 0), (0, 0, 200), duration=16)      # arrive higher -> selfY decreases
    down = _platform.carry_body((0, 0, 200), (0, 0, 0), duration=16)    # arrive lower  -> selfY increases
    assert up != down
    # the terminating test compares selfY (78 FF 01) against the arrive height with B_GT(0x19) up / B_LT(0x18) down
    assert bytes([0x78, 0xFF, 0x01]) in up and bytes([0x78, 0xFF, 0x01]) in down
    assert bytes([0x19, 0x7F]) in up             # `selfY > sy_arrive` terminator (ascending)
    assert bytes([0x18, 0x7F]) in down           # `selfY < sy_arrive` terminator (descending)


def test_zero_height_ride_rejected():
    import pytest
    with pytest.raises(ValueError):
        _platform.carry_body((0, 0, 100), (50, 50, 100))      # same height -> never moves


def test_warp_tail_emits_field_transition():
    plain = _platform.carry_body((0, 0, 0), (0, 0, 200))
    elevator = _platform.carry_body((0, 0, 0), (0, 0, 200), warp_to=2714, warp_entrance=1)
    assert 0x2B not in _ops(plain)               # in-screen ride: no Field()
    assert 0x2B in _ops(elevator)                # elevator: ends in Field(dst)
    assert 0xEC in _ops(elevator)                # ...behind a fade-to-black


# --- inject: graft onto the player + arm the region, stay structurally sound --------------
def test_inject_platform_grafts_and_lints_clean():
    eb, slot = _platform.inject_platform(CLEAN, ZONE, (0, 0, 0), (0, 0, 200),
                                         ride_tag=_platform.FIRST_PLATFORM_TAG)
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    assert parsed.entry(pe).func_by_tag(_platform.FIRST_PLATFORM_TAG) is not None   # ride grafted on the player
    # the boarding region RunScriptSyncs the player ride (2, 250, ride_tag)
    sync = [tuple(i.args) for e in parsed.entries if not e.empty for f in e.funcs
            for i in parsed.instrs(f) if i.op == 0x14]
    assert (_platform.RUNSCRIPT_LEVEL, _platform.PLAYER_UID, _platform.FIRST_PLATFORM_TAG) in sync
    assert _new_errors(eb) == []                                  # composed .eb is sound
    for e in parsed.entries:                                                        # round-trip stability
        if e.empty:
            continue
        for f in e.funcs:
            list(parsed.instrs(f))


def test_multiple_platforms_distinct_tags():
    eb = CLEAN
    tag = _platform.FIRST_PLATFORM_TAG
    for arrive in ((0, 0, 150), (0, 0, 250), (0, 0, 350)):
        eb, _ = _platform.inject_platform(eb, ZONE, (0, 0, 0), arrive, ride_tag=tag)
        tag += 1
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    for t in range(_platform.FIRST_PLATFORM_TAG, _platform.FIRST_PLATFORM_TAG + 3):
        assert parsed.entry(pe).func_by_tag(t) is not None
    assert _new_errors(eb) == []


def test_tread_trigger_shape():
    eb, _ = _platform.inject_platform(CLEAN, ZONE, (0, 0, 0), (0, 0, 200), trigger="tread", bubble=False)
    assert _new_errors(eb) == []


# --- end-to-end build path (field.toml [[platform]] -> built .eb) -------------------------
_FIELD = (
    '[field]\nid = 4003\nname = "P"\narea = 11\ntext_block = 1073\n\n'
    '[camera]\npitch = 45\nfov = 42.2\n\n'
    '[walkmesh]\nquad = [[-200,-200],[200,-200],[200,200],[-200,200]]\n\n'
    '[player]\nspawn = [0, 0]\n\n'
)


def test_build_field_with_platform(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "p.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n'
                 'board = [0, 0, 0]\narrive = [0, 0, 200]\nduration = 32\ntrigger = "action"\n',
                 encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "platform" in x.lower()]    # lint clean
    eb = build.build_script(proj, "us", {})
    s = EbScript.from_bytes(eb)
    pe = find_player_entry(s)
    assert s.entry(pe).func_by_tag(_platform.FIRST_PLATFORM_TAG) is not None    # ride made it through build
    assert _new_errors(eb) == []                             # built .eb is sound


def test_validate_flags_bad_platform(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\n'
                 'board = [0, 0, 100]\narrive = [0, 0, 100]\nduration = 0\ntrigger = "fly"\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]]" in x and "height" in x for x in probs)           # zero-height ride
    assert any("[[platform]]" in x and "duration" in x for x in probs)         # non-positive duration
    assert any("[[platform]]" in x and "trigger" in x for x in probs)          # bad trigger


def test_validate_missing_endpoints(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad2.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nboard = [0, 0, 0]\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]]" in x and "arrive" in x for x in probs)           # missing arrive endpoint


def test_validate_scalar_zone_no_crash(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad3.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = 5\nboard = [0, 0, 0]\narrive = [0, 0, 200]\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]] zone must have 3-5 points" in x for x in probs)
