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
    (mes_body, _txids, _ev, _cs, _ch, _oe, _ate, _chst, _gw, coop_txids) = _build.collect_text(gate_project)
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
