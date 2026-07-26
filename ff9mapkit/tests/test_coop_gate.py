"""Unit tests for the ``[[coop]]`` two-plate gate (netsync V2) -- content/coop.py + the build wiring.

Offline only: expression-byte goldens (hand-decoded against the region.py RPN vocabulary and
EBin's byte-addressed LE reads), rect validation, and a full synthesize-path build round-trip
asserting the gate's regions + expression bytes land in the built ``.eb``.
"""

import struct

import pytest

from ff9mapkit import flags as _flags
from ff9mapkit.content import coop as _coop
from ff9mapkit.content import region as _region


# ---------------------------------------------------------------- rects

def test_normalize_rect_sorts_and_validates():
    assert _coop.normalize_rect([10, 20, -10, -20]) == (-10, -20, 10, 20)     # corners sorted
    assert _coop.normalize_rect((1, 2, 3, 4)) == (1, 2, 3, 4)
    with pytest.raises(ValueError):
        _coop.normalize_rect([0, 0, 0, 10])          # zero width
    with pytest.raises(ValueError):
        _coop.normalize_rect([0, 0, 10])             # not 4 numbers
    with pytest.raises(ValueError):
        _coop.normalize_rect([0, 0, 40000, 10])      # beyond Int16
    with pytest.raises(ValueError):
        _coop.normalize_rect("nope")


def test_rect_zone_perimeter_order():
    assert _coop.rect_zone([-5, -6, 7, 8]) == [(-5, -6), (7, -6), (7, 8), (-5, 8)]


# ---------------------------------------------------------------- expression golden

def test_cond_peer_in_rect_bytes():
    """Hand-decode the compound condition: presence==1 && X>=x1 && X<=x2 && Z>=z1 && Z<=z2.
    The cells are byte-addressed with the long-index encoding (idx > 0xFF -> class|0x20 + u16)."""
    got = _coop.cond_peer_in_rect([-100, -50, 100, 50])

    def var(cls, idx):
        return bytes([cls | 0x20]) + struct.pack("<H", idx)

    def const(v):
        return bytes([_region.T_CONST]) + struct.pack("<h", v)

    want = bytes([_region.EXPR_OP])
    want += var(_region.GLOB_BYTE, _coop.COOP_PRESENCE_BYTE) + const(1) + bytes([_region.T_EQ])
    for idx, lo, hi in ((_coop.COOP_PEER_X, -100, 100), (_coop.COOP_PEER_Z, -50, 50)):
        want += var(_region.GLOB_INT16, idx) + const(lo) + bytes([_region.T_GE, _region.T_ANDAND])
        want += var(_region.GLOB_INT16, idx) + const(hi) + bytes([_region.T_LE, _region.T_ANDAND])
    want += bytes([_region.T_END])
    assert got == want


def test_gate_range_body_shape():
    """movement gate + if(!flag){ if(peer-in-rect){ flag=1 [; message] } } + RETURN, flag set FIRST."""
    from ff9mapkit.content import event as _event
    from ff9mapkit.eb import opcodes
    body = _coop.gate_range_body([0, 0, 10, 10], 8600)
    assert body.startswith(_region.MOVEMENT_GATE)
    assert body.endswith(opcodes.RETURN)
    set_flag = _region.set_var(_region.GLOB_BOOL, 8600, 1)
    assert set_flag in body
    cond = _coop.cond_peer_in_rect([0, 0, 10, 10])
    assert cond in body
    # the once-latch (if !flag) sits OUTSIDE the peer check: cond_not appears before the peer cond
    assert body.index(_region.cond_not(_region.GLOB_BOOL, 8600)) < body.index(cond)
    with_msg = _coop.gate_range_body([0, 0, 10, 10], 8600, message_txid=5)
    # flag first, message after (FF9's chest convention -- loop-safe however the window behaves)
    assert with_msg.index(set_flag) < with_msg.index(_event.message(5))


# ---------------------------------------------------------------- flag registry

def test_coop_cells_reserved_in_the_registry():
    for bit in (_flags.COOP_CELLS_FLOOR, _flags.COOP_CELLS_FLOOR + 32, _flags.CHOICE_SCRATCH_FLOOR - 1):
        assert _flags.is_reserved(bit), bit
        assert not _flags.is_safe_custom(bit), bit
    assert _flags.is_safe_custom(_flags.FIRST_SAFE_FLAG)           # the band itself still allocates
    names = {w.name: w for w in _flags.NAMED_WORDS}
    assert names["CoopPeerPresence"].byte == _coop.COOP_PRESENCE_BYTE
    assert names["CoopPeerX"].byte == _coop.COOP_PEER_X and names["CoopPeerX"].signed
    assert names["CoopPeerZ"].byte == _coop.COOP_PEER_Z and names["CoopPeerZ"].signed
    # the cells sit exactly on the engine's byte layout: presence, pad, X word, Z word
    assert (_coop.COOP_PEER_X, _coop.COOP_PEER_Z) == (_coop.COOP_PRESENCE_BYTE + 2,
                                                      _coop.COOP_PRESENCE_BYTE + 4)


# ---------------------------------------------------------------- build round-trip

@pytest.fixture
def gate_project(tmp_path):
    from ff9mapkit.build import FieldProject
    toml = tmp_path / "gate.field.toml"
    toml.write_text(
        '[field]\nname = "COOPGATE"\nid = 30090\narea = 10\n\n'
        '[[coop]]\nname = "twin-seals"\n'
        'plate_a = [-305, -60, -185, 60]\n'
        'plate_b = [-55, -60, 65, 60]\n'                # centers 250 apart -> selftest-provable
        'set_flag = 8600\n'
        'text = "The twin seals release!"\n',
        encoding="utf-8")
    return FieldProject.load(toml)


def test_coop_gate_builds_two_regions(gate_project):
    from ff9mapkit import build as _build
    (mes_body, _txids, _ev, _cs, _ch, _oe, _ate, _chst, _gw, coop_txids, _sp11, _bh12, _ni13) = _build.collect_text(gate_project)
    assert coop_txids == {0: 500}                       # first authored line -> text.DEFAULT_BASE_TXID
    assert "twin seals" in mes_body
    eb = _build.build_script(gate_project, "us", {}, coop_txids=coop_txids)
    # both plates' region bodies present: each checks the peer against the OTHER plate
    assert _coop.cond_peer_in_rect([-55, -60, 65, 60]) in eb       # plate A's body
    assert _coop.cond_peer_in_rect([-305, -60, -185, 60]) in eb    # plate B's body
    assert eb.count(_region.set_var(_region.GLOB_BOOL, 8600, 1)) == 2


def test_coop_gate_missing_pieces_refuse(tmp_path):
    from ff9mapkit import build as _build
    from ff9mapkit.build import BuildError, FieldProject
    toml = tmp_path / "bad.field.toml"
    toml.write_text('[field]\nname = "BAD"\nid = 30091\narea = 10\n\n'
                    '[[coop]]\nplate_a = [0, 0, 10, 10]\nset_flag = 8600\n', encoding="utf-8")
    with pytest.raises(BuildError, match="plate_a and plate_b"):
        _build.build_script(FieldProject.load(toml), "us", {})
    toml.write_text('[field]\nname = "BAD"\nid = 30091\narea = 10\n\n'
                    '[[coop]]\nplate_a = [0, 0, 10, 10]\nplate_b = [20, 0, 30, 10]\n', encoding="utf-8")
    with pytest.raises(BuildError, match="set_flag"):
        _build.build_script(FieldProject.load(toml), "us", {})


def test_gate_reveal_lands_between_flag_and_message():
    """A gated NPC's live reveal (InitObject) runs after the set (its Init re-reads the flag's
    new value) and BEFORE the message -- the NPC is standing there when the window closes."""
    from ff9mapkit.content import event as _event
    rv = _event.reveal_object(7)
    body = _coop.gate_range_body([0, 0, 10, 10], 8600, message_txid=5, reveal=rv)
    sf = _region.set_var(_region.GLOB_BOOL, 8600, 1)
    assert body.index(sf) < body.index(rv) < body.index(_event.message(5))


# ---------------------------------------------------------------- rung 2

def test_assign_peer_in_rect_bytes():
    """flag = (presence && peer-in-rect): var-ref FIRST, the condition chain, B_LET, END --
    the exact assign order region.set_var uses."""
    got = _coop.assign_peer_in_rect(8602, [0, 0, 10, 10])
    want = (bytes([_region.EXPR_OP])
            + bytes([_region.GLOB_BOOL | 0x20]) + struct.pack("<H", 8602)
            + _coop._peer_in_rect_tokens([0, 0, 10, 10])
            + bytes([_region.T_ASSIGN, _region.T_END]))
    assert got == want
    # the shared token chain is exactly the once-gate's condition minus the 0x05/0x7F wrapper
    cond = _coop.cond_peer_in_rect([0, 0, 10, 10])
    assert cond == bytes([_region.EXPR_OP]) + _coop._peer_in_rect_tokens([0, 0, 10, 10]) + bytes([_region.T_END])


def test_hold_loop_body_is_level_not_latch():
    """The hold is a looping CODE entry (the TreadQuad law forbids an always-inside region):
    assign, Wait(1), unconditional JMP back to the top (signed end-relative offset)."""
    from ff9mapkit.eb import opcodes
    plate = [150, -1700, 350, -1500]
    body = _coop.hold_loop_body(plate, 8602)
    assign = _coop.assign_peer_in_rect(8602, plate)
    assert body.startswith(assign)
    assert _region.cond_not(_region.GLOB_BOOL, 8602) not in body      # NO once-latch
    assert opcodes.wait(1) in body
    # the back-jump: 0x01 + i16, target = jump END + offset = 0 (the loop top)
    assert body[-3] == 0x01
    assert struct.unpack("<h", body[-2:])[0] == -len(body)
    # requires_flag arms via a forward SKIP (never a RETURN -- that would kill the loop object)
    armed = _coop.hold_loop_body(plate, 8602, requires_flag=8600)
    skip = _region.cond_truthy(_region.GLOB_BOOL, 8600) + bytes([_region.JMP_FALSE]) + struct.pack("<H", len(assign))
    assert armed.startswith(skip)
    assert struct.unpack("<h", armed[-2:])[0] == -len(armed)          # the loop spans the arm gate too


def test_gate_range_body_requires_flag_arming():
    body = _coop.gate_range_body([0, 0, 10, 10], 8601, requires_flag=8600)
    arm = _region.flag_gate(_region.GLOB_BOOL, 8600, require_set=True)
    assert arm in body
    # the arming gate sits BEFORE the once-latch (an unarmed gate is fully inert)
    assert body.index(arm) < body.index(_region.cond_not(_region.GLOB_BOOL, 8601))


def test_rung2_blocks_build(tmp_path):
    """gather (zone=) -> ONE region; hold -> the always-inside poller; requires_flag arms."""
    from ff9mapkit import build as _build
    from ff9mapkit.build import FieldProject
    toml = tmp_path / "vault.field.toml"
    toml.write_text(
        '[field]\nname = "VAULT"\nid = 30093\narea = 10\n\n'
        '[[coop]]\nname = "gather"\nzone = [-150, -400, 400, -150]\n'
        'requires_flag = 8600\nset_flag = 8601\ntext = "Together."\n\n'
        '[[coop]]\nname = "plate"\nmode = "hold"\nplate = [150, -1700, 350, -1500]\n'
        'set_flag = 8602\n', encoding="utf-8")
    eb = _build.build_script(FieldProject.load(toml), "us", {}, coop_txids={0: 500})
    # the gather compiles ONE region: its cross-compare targets its own zone, exactly once
    assert eb.count(_coop.cond_peer_in_rect([-150, -400, 400, -150])) == 1
    assert _region.flag_gate(_region.GLOB_BOOL, 8600, require_set=True) in eb
    # the hold: a looping CODE entry (assign + Wait(1) + back-jump), NOT a region -- and no
    # always-inside quad anywhere (the TreadQuad law)
    assert _coop.hold_loop_body([150, -1700, 350, -1500], 8602) in eb
    assert struct.pack("<hh", -30000, -30000) not in eb


def test_rung2_refusals(tmp_path):
    from ff9mapkit import build as _build
    from ff9mapkit.build import BuildError, FieldProject
    base = '[field]\nname = "BAD"\nid = 30094\narea = 10\n\n'
    toml = tmp_path / "bad2.field.toml"
    toml.write_text(base + '[[coop]]\nmode = "hold"\nset_flag = 8602\n', encoding="utf-8")
    with pytest.raises(BuildError, match="needs plate"):
        _build.build_script(FieldProject.load(toml), "us", {})
    toml.write_text(base + '[[coop]]\nmode = "hold"\nplate = [0, 0, 10, 10]\nset_flag = 8602\n'
                           'text = "spam"\n', encoding="utf-8")
    with pytest.raises(BuildError, match="can't take text"):
        _build.build_script(FieldProject.load(toml), "us", {})
    toml.write_text(base + '[[coop]]\nmode = "levers"\nplate_a = [0, 0, 10, 10]\n'
                           'plate_b = [20, 0, 30, 10]\nset_flag = 8602\n', encoding="utf-8")
    with pytest.raises(BuildError, match="unknown mode"):
        _build.build_script(FieldProject.load(toml), "us", {})


def test_lint_region_overlaps_treadquad_law(tmp_path):
    """Overlapping tread regions starve each other (TreadQuad fires ONE per frame) -> warn;
    abutting zones (shared edge) stay clean."""
    from ff9mapkit import build as _build
    from ff9mapkit.build import FieldProject
    toml = tmp_path / "olap.field.toml"
    toml.write_text('[field]\nname = "OLAP"\nid = 30095\narea = 10\n\n'
                    '[[coop]]\nplate_a = [0, 0, 100, 100]\nplate_b = [300, 0, 400, 100]\n'
                    'set_flag = 8600\n\n'
                    '[[gateway]]\nto = 30003\nentrance = 0\n'
                    'zone = [[50, 50], [150, 50], [150, 150], [50, 150]]\n', encoding="utf-8")
    warns = _build.lint_region_overlaps(FieldProject.load(toml))
    assert len(warns) == 1 and "OVERLAP" in warns[0] and "plate_a" in warns[0], warns
    # abutting (shared edge at x=100) is a normal layout -> clean
    toml.write_text('[field]\nname = "OLAP"\nid = 30095\narea = 10\n\n'
                    '[[coop]]\nplate_a = [0, 0, 100, 100]\nplate_b = [100, 0, 200, 100]\n'
                    'set_flag = 8600\n', encoding="utf-8")
    assert _build.lint_region_overlaps(FieldProject.load(toml)) == []
    # holds are code entries, not regions -> never in the overlap set
    toml.write_text('[field]\nname = "OLAP"\nid = 30095\narea = 10\n\n'
                    '[[coop]]\nmode = "hold"\nplate = [0, 0, 100, 100]\nset_flag = 8602\n\n'
                    '[[gateway]]\nto = 30003\nentrance = 0\n'
                    'zone = [[50, 50], [150, 50], [150, 150], [50, 150]]\n', encoding="utf-8")
    assert _build.lint_region_overlaps(FieldProject.load(toml)) == []


def test_lint_flags_coop_set_flag_band(tmp_path):
    """A [[coop]] set_flag inside a reserved region (incl. the coop cells themselves) gets warned."""
    from ff9mapkit import build as _build
    from ff9mapkit.build import FieldProject
    toml = tmp_path / "lint.field.toml"
    toml.write_text('[field]\nname = "LINT"\nid = 30092\narea = 10\n\n'
                    '[[coop]]\nplate_a = [0, 0, 10, 10]\nplate_b = [20, 0, 30, 10]\n'
                    f'set_flag = {_flags.COOP_CELLS_FLOOR + 1}\ntext = "x"\n', encoding="utf-8")
    warns = _build.lint_flag_bands(FieldProject.load(toml))
    assert any("netsync_coop_cells" in w for w in warns), warns
