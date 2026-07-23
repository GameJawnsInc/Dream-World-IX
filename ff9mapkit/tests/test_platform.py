"""Carry-platform pillar (Pandemonium-elevator style: the player is physically carried within one
field by a scripted MoveInstantXZY ride, control disabled, no Field() re-entry).

Provenance-clean: the ride is synthesised with the kit's own opcodes (the navigable-climb primitives
minus the d-pad). The ride is RELATIVE -- it captures the player's boarding height and lifts him by
`rise` from there (no absolute teleport, so it never warps him under a platform model). Tests assert the
graft + arm round-trips, the ride loop terminates, the direction follows `rise`'s sign, and the composed
.eb stays structurally sound (eblint).
"""
from __future__ import annotations

from ff9mapkit import data, eblint
from ff9mapkit.content import platform as _platform
from ff9mapkit.eb import EbScript, opcodes
from ff9mapkit.eb.disasm import iter_code, jump_target
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
    body = _platform.carry_body(rise=200, duration=32)
    ops = _ops(body)
    assert ops.count(0xA1) == 2                  # per-frame loop snap + exact final snap (NO absolute board snap)
    assert 0x22 in ops                           # Wait(1) in the loop (deterministic ride timing)
    assert 0x03 in ops                           # JMP_TRUE -- the loop back-edge (so it can repeat)
    assert ops[-1] == 0x04                        # ends in RETURN
    assert 0xA8 in ops                           # SetPathing (detach at board, re-attach at land)
    # captures the boarding selfY (MAP.I16[4]) + the destination (MAP.I16[3]) -- the relative ride
    assert bytes([_platform._region.MAP_INT16, _platform.PLATFORM_START]) in body
    assert bytes([_platform._region.MAP_INT16, _platform.PLATFORM_SCRATCH]) in body


def test_carry_direction_follows_rise_sign():
    up = _platform.carry_body(rise=200, duration=16)       # positive -> UP -> selfY decreases
    down = _platform.carry_body(rise=-200, duration=16)    # negative -> DOWN -> selfY increases
    assert up != down
    assert bytes([0x78, 0xFF, 0x01]) in up and bytes([0x78, 0xFF, 0x01]) in down   # reads selfY (78 FF 01)
    assert bytes([0x19, 0x7F]) in up             # `selfY > target` terminator (ascending, B_GT)
    assert bytes([0x18, 0x7F]) in down           # `selfY < target` terminator (descending, B_LT)


def test_zero_rise_rejected():
    import pytest
    with pytest.raises(ValueError):
        _platform.carry_body(rise=0)             # a zero ride never moves
    with pytest.raises(ValueError):
        _platform.carry_body()                   # neither land nor rise


# --- land mode: ride from the boarding spot to an absolute floor (clean landing) ----------
def test_carry_land_rides_to_absolute_point():
    body = _platform.carry_body(land=(12, 432, -474), speed=30)
    ops = _ops(body)
    assert ops.count(0xA1) == 2                  # interpolated loop snap + exact final snap (to the landing)
    assert 0x22 in ops and 0x03 in ops and ops[-1] == 0x04
    # captures boarding x / z / selfY (MAP.I16[5]/[6]/[4]) -- the ride interpolates FROM there
    for idx in (_platform.PLATFORM_START_X, _platform.PLATFORM_START_Z, _platform.PLATFORM_START):
        assert bytes([_platform._region.MAP_INT16, idx]) in body
    # the exact final snap carries the landing's x (12) and selfY (-(-474)=474) as constants
    import struct
    assert struct.pack("<h", 12) in body and struct.pack("<h", 474) in body


def test_carry_land_zero_span_skips_division():
    """A 2-element `land=(x,z)` defaults ly=0 -> lsy=0; if the boarding selfY is ALSO 0 (a ground-floor
    boarding spot -- the common case), interp()'s (lsy - csy) divisor would be 0. The ride must guard
    this at runtime (it can't know the boarding height at build time) instead of dividing blind."""
    body = _platform.carry_body(land=(12, 432), speed=30)
    instrs = list(iter_code(bytes(body), 0, len(body)))
    jmp_true = [i for i in instrs if i.op == 0x03]
    assert len(jmp_true) == 2                       # the new zero-span guard + the loop's own back-edge
    a1s = [i for i in instrs if i.op == 0xA1]
    assert len(a1s) == 2                             # interpolated loop snap + the exact final landing snap
    guard = jmp_true[0]                              # emitted right after capturing the boarding position
    assert jump_target(guard) == a1s[-1].off         # skips straight to the exact-landing MoveInstantXZY


def test_inject_land_platform_lints_clean():
    eb, _ = _platform.inject_platform(CLEAN, ZONE, land=(12, 432, -474))
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    assert parsed.entry(pe).func_by_tag(_platform.FIRST_PLATFORM_TAG) is not None
    assert _new_errors(eb) == []


# --- entry mode: self-contained ABSOLUTE drop+rise in the post-fade ride func (no Init drop, no division)
def test_entry_rise_body_absolute_no_division():
    body = _platform.entry_rise_body(land=(12, 432, -474), rise=1200, duration=48)
    ops = _ops(body)
    # 3 MoveInstantXZY: drop-to-bottom, per-frame rise, exact floor snap -- all absolute
    assert ops.count(0xA1) == 3
    assert 0x22 in ops and 0x03 in ops and 0xA8 in ops and ops[-1] == 0x04
    assert 0x16 not in ops                               # NO divide op (T_DIV) -> can't fling sideways
    import struct
    assert struct.pack("<h", -(-474) + 1200) in body     # the absolute hole-bottom selfY (1674)
    assert struct.pack("<h", -(-474)) in body            # the absolute floor selfY (474)


def test_inject_entry_rise_no_init_drop_arms_post_fade():
    eb = _platform.inject_entry_rise(CLEAN, land=(12, 432, -474), rise=1200)
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    assert parsed.entry(pe).func_by_tag(_platform.FIRST_PLATFORM_TAG) is not None     # ride grafted on the player
    # the player Init is NOT modified (no drop spliced -- it didn't stick): the only ride is the func
    # Main_Init arms an InitCode trigger that spins on usercontrol (JMP_TRUE) then RunScriptSyncs the rise
    assert any(i.op == 0x09 for i in parsed.instrs(parsed.entry(0).func_by_tag(0)))
    trig = next((parsed.entry(ei).func_by_tag(0) for ei in range(parsed.entry_count)
                 if parsed.entry(ei) is not None and parsed.entry(ei).func_by_tag(0) is not None
                 and any(i.op == 0x14 and 56 in (i.args or []) for i in parsed.instrs(parsed.entry(ei).func_by_tag(0)))), None)
    assert trig is not None and 0x03 in [i.op for i in parsed.instrs(trig)]
    assert _new_errors(eb) == []


def test_warp_tail_emits_field_transition():
    plain = _platform.carry_body(rise=200)
    elevator = _platform.carry_body(rise=200, warp_to=2714, warp_entrance=1)
    assert 0x2B not in _ops(plain)               # in-screen ride: no Field()
    assert 0x2B in _ops(elevator)                # elevator: ends in Field(dst)
    assert 0xEC in _ops(elevator)                # ...behind a fade-to-black


# --- inject: graft onto the player + arm the region, stay structurally sound --------------
def test_inject_platform_grafts_and_lints_clean():
    eb, slot = _platform.inject_platform(CLEAN, ZONE, rise=200, ride_tag=_platform.FIRST_PLATFORM_TAG)
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
    for r in (150, 250, 350):
        eb, _ = _platform.inject_platform(eb, ZONE, rise=r, ride_tag=tag)
        tag += 1
    parsed = EbScript.from_bytes(eb)
    pe = find_player_entry(parsed)
    for t in range(_platform.FIRST_PLATFORM_TAG, _platform.FIRST_PLATFORM_TAG + 3):
        assert parsed.entry(pe).func_by_tag(t) is not None
    assert _new_errors(eb) == []


def test_tread_trigger_shape():
    eb, _ = _platform.inject_platform(CLEAN, ZONE, rise=200, trigger="tread", bubble=False)
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
                 'rise = 1000\nduration = 48\ntrigger = "action"\n',
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
                 'rise = 0\nduration = 0\ntrigger = "fly"\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]]" in x and "rise" in x for x in probs)             # zero rise
    assert any("[[platform]]" in x and "duration" in x for x in probs)         # non-positive duration
    assert any("[[platform]]" in x and "trigger" in x for x in probs)          # bad trigger


def test_validate_missing_rise(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad2.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nduration = 48\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]]" in x and "rise" in x for x in probs)             # missing rise


def test_validate_scalar_zone_no_crash(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "bad3.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = 5\nrise = 200\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("[[platform]] zone must have 3-5 points" in x for x in probs)


# --- the VISIBLE platform model (v2: a placed model driven in lockstep) --------------------
def _bit_token(bit: int) -> bytes:
    """The long-index MAP_BOOL var token for a >0xFF bit index: 0xC5|0x20 + u16 LE (the engine's own
    getVarOperation encoding -- see region._push_var)."""
    import struct
    return bytes([0xE5]) + struct.pack("<H", bit)


def test_ride_bit_absent_leaves_v1_bytes_untouched():
    """`ride_bit=None` (no visible model) must emit ZERO ride-bit machinery -- the v1 byte shape.
    The bit band's var token must not appear anywhere in any mode."""
    for body in (_platform.carry_body(rise=200, duration=32),
                 _platform.carry_body(land=(100, 200, 300)),
                 _platform.entry_rise_body(land=(0, 0, 300), rise=600)):
        for k in range(_platform.PLATFORM_MAX_PER_FIELD):
            assert _bit_token(_platform.platform_ride_bit(k)) not in body


def test_ride_bit_set_after_detach_cleared_after_landing():
    """With a bound ride bit: raised right after the detach (so the model tracks the whole ride),
    cleared after the exact landing snap + one settle frame (so it rests at the destination)."""
    bit = _platform.platform_ride_bit(0)
    for body in (_platform.carry_body(rise=200, duration=32, ride_bit=bit),
                 _platform.carry_body(land=(100, 200, 300), ride_bit=bit),
                 _platform.entry_rise_body(land=(0, 0, 300), rise=600, ride_bit=bit)):
        tok = _bit_token(bit)
        first, last = body.find(tok), body.rfind(tok)
        assert first != -1 and last != first                     # a set AND a clear
        detach = body.find(opcodes.set_pathing(0))
        assert detach != -1 and detach < first                   # raised after the detach
        # the clear sits after the LAST MoveInstantXZY (the exact landing snap)
        last_snap = max(ins.off for ins in iter_code(bytes(body), 0, len(body)) if ins.op == 0xA1)
        assert last > last_snap


def test_platform_ride_bit_band_range_checked():
    import pytest
    assert _platform.platform_ride_bit(0) == _platform.PLATFORM_RIDE_BIT
    with pytest.raises(ValueError):
        _platform.platform_ride_bit(_platform.PLATFORM_MAX_PER_FIELD)


def test_platform_prop_entry_structure():
    """The visible platform's entry: tag-0 Init (SetModel + walk-through flags 7 + detach + absolute
    rest placement) and a tag-1 permanent loop gated on the ride bit that pins the model to the
    player's live position (0x78 obj-var reads of uid 250's x/y/z)."""
    bit = _platform.platform_ride_bit(0)
    entry = _platform.platform_prop_entry(model=241, animset=93, pose=1904, x=10, z=-20, y=30,
                                          ride_bit=bit, model_offset=40)
    assert entry[0] != 0 and entry[1] == 2                        # a typed entry with two funcs
    import struct
    t0_tag, t0_off = struct.unpack_from("<HH", entry, 2)
    t1_tag, t1_off = struct.unpack_from("<HH", entry, 6)
    assert (t0_tag, t1_tag) == (0, 1)
    init = entry[2 + t0_off:2 + t1_off]
    loop = entry[2 + t1_off:]
    ops_init = _ops(init)
    assert 0x2F in ops_init                                       # SetModel
    assert opcodes.encode(0x93, _platform.PLATFORM_MODEL_FLAGS) in init   # walk-through flags 7
    assert opcodes.set_pathing(0) in init                         # detached (rests at any height)
    assert ops_init[-1] == 0x04
    # the tracker: gated on the ride bit, reads player x/y/z live, offset applied to y
    assert _bit_token(bit) in loop
    assert bytes([0x78, 0xFA, 0x00]) in loop                      # player.x   (uid 250 = 0xFA)
    assert bytes([0x78, 0xFA, 0x01]) in loop                      # player.y
    assert bytes([0x78, 0xFA, 0x02]) in loop                      # player.z
    # permanent loop: ends in a backward 0x01 jump targeting the loop top (offset 0)
    last = [ins for ins in iter_code(bytes(loop), 0, len(loop))][-1]
    assert last.op == 0x01 and jump_target(last) == 0


def test_build_field_with_platform_model(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "pm.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nrise = 200\n'
                 'prop = "cask"\nmodel_offset = 40\n',
                 encoding="utf-8")
    proj = build.FieldProject.load(p)
    assert not [x for x in build.validate(proj) if "platform" in x.lower()]
    eb = build.build_script(proj, "us", {})
    assert not _new_errors(eb)
    # the cask model (241) is placed by a new entry whose loop reads the player's live position
    s = EbScript.from_bytes(eb)
    found = False
    for e in s.entries:
        if e.empty:
            continue
        for f in e.funcs:
            seg = s.data[f.abs_start:f.abs_end]
            if bytes([0x78, 0xFA, 0x01]) in seg and _bit_token(_platform.platform_ride_bit(0)) in seg:
                found = True
    assert found


def test_validate_platform_model_keys(tmp_path):
    from ff9mapkit import build
    p = tmp_path / "pmv.field.toml"
    p.write_text(_FIELD +
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nrise = 200\n'
                 'prop = "cask"\nmodel = "GEO_ACC_F0_CSK"\nmodel_offset = -3\n\n'
                 '[[platform]]\nzone = [[10,-10],[50,-10],[50,-50],[10,-50]]\nrise = 100\n'
                 'model_pos = [1, 2]\n',
                 encoding="utf-8")
    probs = build.validate(build.FieldProject.load(p))
    assert any("not both" in x for x in probs)                    # prop + model together
    assert any("model_offset" in x for x in probs)                # negative offset
    assert any("model_pos/model_offset need" in x for x in probs)  # model_pos with no model
