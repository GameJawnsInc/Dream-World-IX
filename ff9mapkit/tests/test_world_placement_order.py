"""THE ONE ENGINE-CITED REGISTRATION ORDER (audit rec 11).

The engine's part-registration order was hardcoded four times in three mutually inconsistent
orders (interior omitted the carried aux parts entirely, coastnav and transplant both had
Sea5 before Sea4). Now ``placement.REGISTRATION_ORDER`` is the single source (source-cited to
``WMWorld.cs LoadBlock``), ``build_meshlist`` is the one constructor, ``census`` refuses an
out-of-order stack -- and ``interior.census_gate`` measures the REAL carried ensemble parts,
so a carried massif Object over the probe point FAILS the gate instead of passing by
omission (the one fix here that buys a playtest).

Hermetic: every mesh is synthesized; ``island._sea_plane`` is monkeypatched.
"""
from __future__ import annotations

import pytest

from ff9mapkit.world import interior as IN, placement as P
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN


def _bm(tris, name="Block[0][0] Terrain", x=0, y=0):
    """A BlockMesh from ``[(corners[(x, y, z)]x3, idall), ...]`` in buffer order."""
    pos, nrm, uv, tan, flat, t_out = [], [], [], [], [], []
    for corners, idall in tris:
        base = len(pos)
        for c in corners:
            pos.append(list(c))
            nrm.append([0.0, 1.0, 0.0])
            uv.append([0.0, 0.0])
            tan.append([float(idall), 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        t_out.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=1, x=x, y=y, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


GRASS = encode_id(topograph=0)
SCENERY = encode_id(topograph=49)                        # the ensemble carry's blocked-topo IDALL
SEA57 = encode_id(topograph=57)
_UP = [(0.0, 3.5, 0.0), (8.0, 3.5, 0.0), (0.0, 3.5, -8.0)]


def _grid(idall, y, n=16, cell=4.0, name="Block[0][0] Terrain"):
    """A full-coverage n x n grid of 4u cells at height ``y`` in the block-local frame."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), idall))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), idall))
    return _bm(tris, name=name)


# ---- the constant + the one constructor -----------------------------------------------------------------------------

def test_build_meshlist_sorts_any_case_into_the_engine_order():
    bm = _bm([(_UP, GRASS)])
    got = P.build_meshlist({"Sea1": bm, "beach1": bm, "Terrain": bm, "riverjoint": bm})
    assert [nm for nm, _ in got] == ["Terrain", "Beach1", "RiverJoint", "Sea1"]
    # str.capitalize is NOT canonicalization -- it would have minted "Riverjoint"
    assert P.canonical_part("riverjoint") == "RiverJoint" and P.canonical_part("bogus") is None


def test_build_meshlist_refuses_a_part_the_engine_never_registers():
    with pytest.raises(ValueError, match="unknown walkmesh part"):
        P.build_meshlist({"Terrain": _bm([(_UP, GRASS)]), "Lava": _bm([(_UP, GRASS)])})


def test_census_refuses_an_out_of_order_or_duplicated_stack():
    bm = _bm([(_UP, GRASS)])
    with pytest.raises(ValueError, match="registration order"):
        P.census([("Sea1", bm), ("Beach1", bm)], span=(1.0, 7.0, -7.0, -1.0), samples=2)
    with pytest.raises(ValueError, match="registration order"):
        P.census([("Terrain", bm), ("Terrain", bm)], span=(1.0, 7.0, -7.0, -1.0), samples=2)
    # a valid subsequence passes, and engine-unknown fixture names pass through unjudged
    P.census([("Terrain", bm), ("Sea4", _bm([(_UP, SEA57)]))],
             span=(1.0, 7.0, -7.0, -1.0), samples=2)
    P.census([("SynthFixture", bm)], span=(1.0, 7.0, -7.0, -1.0), samples=2)


def test_transplant_carry_set_is_an_engine_subsequence():
    """The census meshlists transplant builds iterate PARTS -- drift here (the old
    sea5-before-sea4) would make every transplant census refuse."""
    from ff9mapkit.world.transplant import PARTS, part_name
    P.check_registration_order([(part_name(p), None) for p in PARTS])


def test_coastnav_has_no_private_order_copy():
    from ff9mapkit.world import coastnav as CN
    assert not hasattr(CN, "PARTS_ORDER")


# ---- the fix that buys a playtest: census_gate measures the REAL carried parts --------------------------------------

def test_census_gate_fails_the_probe_on_a_carried_object_shadow(monkeypatch):
    """Object registers AHEAD of Terrain, so a carried massif Object over the probe point is
    what the engine grounds on -- the gate used to census a hidden BLANK Object and pass.
    Fed ``parts=res["changed_parts"]`` (the cli world-mountain wiring), it must now raise;
    blind (no ``parts``), it still documents the old pass so the contrast is pinned here."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _grid(SEA57, 0.0,
                                                                       name="Block[0][0] Sea4"))
    terrain = _grid(GRASS, 3.2)
    shadow = [(16.0, 6.0, -16.0), (28.0, 6.0, -16.0), (16.0, 6.0, -28.0)]
    carried = _bm([(shadow, SCENERY)], name="Block[0][0] Object")
    probe = ((20.0, -20.0), 0)                           # block (0,0): world == block-local

    IN.census_gate({(0, 0): terrain}, probe=probe, baseline={(0, 0): terrain})
    IN.census_gate({(0, 0): terrain}, probe=probe, baseline={(0, 0): terrain},
                   parts={(0, 0): {}})                   # empty carry: unchanged verdict
    with pytest.raises(ValueError, match="probe grounded on Object"):
        IN.census_gate({(0, 0): terrain}, probe=probe, baseline={(0, 0): terrain},
                       parts={(0, 0): {"Object": carried}})


def test_census_gate_carried_falls_join_the_scan(monkeypatch):
    """The ensemble's Falls/River/RiverJoint were simply OMITTED before -- handed in via
    ``parts`` they must join the stack (visible in the census counts as grounded samples)."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _grid(SEA57, 0.0,
                                                                       name="Block[0][0] Sea4"))
    terrain = _grid(GRASS, 3.2)
    sheet = [(32.0, 9.0, -32.0), (44.0, 9.0, -32.0), (32.0, 9.0, -44.0)]
    falls = _bm([(sheet, SCENERY)], name="Block[0][0] Falls")
    # Falls registers AFTER Terrain, so terrain still wins under it -- the gate stays green,
    # but the part must be scanned (an unknown name would refuse in build_meshlist).
    IN.census_gate({(0, 0): terrain}, baseline={(0, 0): terrain},
                   parts={(0, 0): {"Falls": falls, "RiverJoint": _bm([], name="rj")}})
