"""world-forest / world-hill / world-mountain -- the interior-topography verbs (hermetic).

The full-fidelity acceptance is the zero-byte-diff identity proof against the deployed,
in-game-proven island E / Uaho bench (``studies/overworld-topography/
interior_productize_check.py`` + ``mountain_productize_check.py`` -- mint -> module carve
reproduces the playtested bytes exactly); it needs the install + the deployed blocks, so
it stays a local study script. These tests cover the hermetic machinery:

  * chain_ring (simple-cycle chaining + degeneracy refusal)
  * chain_rings (multi-cycle chaining + degree-2 refusal) + signed_area orientation
  * split_borders8 (64u border split, channel lerp, THE WALL LAW's true-3D-area filter)
  * raised_cosine + decode_cell_pick determinism
  * soup_from_blocks byte-fam classification (main/stamp/forest/rock + the coast proxy)
  * build_hill on a synthetic mains grid: gates pass, pure-Y displacement, local normals,
    the rolling-relief envelope refusing a STACKED second hill, the slope-envelope refusal
  * carve_mountain end-to-end on a synthetic donor pyramid + mains-grid bench (the donor
    read is monkeypatched -- no game bytes): rigid carry, hole+zip accounting, the
    rock-probe, and the no-rock / footprint / in-block / double-carry refusals
  * read_deployed_blocks against a temp game dir (found / not-found semantics)
"""
from __future__ import annotations

import math

import pytest

from ff9mapkit.world import grassland as G, interior as IN, mesh as M
from ff9mapkit.world.extract import BlockMesh, encode_id, CH_POS, CH_NRM, CH_UV, CH_TAN

GRASS = float(encode_id(topograph=0))
FOREST = float(encode_id(topograph=37))
ROCK = float(encode_id(topograph=58))
_MAIN_U = (G.FAM_REGION["main"][0] + G.FAM_REGION["main"][2]) / 2.0


def _bm(tris, name="Block[0][0] Terrain", x=0, y=0):
    """A BlockMesh from ``[(corners[(x, y, z)]x3, idall, u), ...]``."""
    pos, nrm, uv, tan, flat, t_out = [], [], [], [], [], []
    for corners, idall, u in tris:
        base = len(pos)
        for c in corners:
            pos.append(list(c))
            nrm.append([0.0, 1.0, 0.0])
            uv.append([u, 0.5])
            tan.append([idall, 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        t_out.append([base, base + 1, base + 2])
    return BlockMesh(name=name, disc=1, x=x, y=y, lod="0_1", vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def _mains_grid(y=3.2, n=13, cell=4.0):
    """A watertight n x n quad grid of mains grass tris in one block (local frame)."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    return _bm(tris)


# ---- helpers ---------------------------------------------------------------------------------

def test_chain_ring_chains_a_polygon_and_refuses_degeneracy():
    ring = [(math.cos(a) * 10, 0.0, math.sin(a) * 10) for a in
            (k * math.pi / 6 for k in range(12))]
    ring = [IN.kk3(p) for p in ring]
    edges = [tuple(sorted((ring[k], ring[(k + 1) % 12]))) for k in range(12)]
    out = IN.chain_ring(edges, "test")
    assert len(out) == 12 and set(out) == set(ring)
    with pytest.raises(ValueError, match="not a simple cycle"):
        IN.chain_ring(edges[:-1], "test")


def test_split_borders8_splits_at_the_border_and_keeps_vertical_curtains():
    # a tri straddling world x=64 splits into both blocks, channels lerped
    c = ((60.0, 1.0, -10.0, 0.0, 0.0, 0.0, 1.0, 0.0),
         (70.0, 1.0, -10.0, 1.0, 0.0, 0.0, 1.0, 0.0),
         (60.0, 1.0, -20.0, 0.0, 1.0, 0.0, 1.0, 0.0))
    out = IN.split_borders8([(c, GRASS, "zip")])
    assert set(out) == {(0, 0), (1, 0)}
    for blk, tris in out.items():
        for tri, idall, fam in tris:
            assert idall == GRASS and fam == "zip"
            for corner in tri:
                assert len(corner) == 8
                if abs(corner[0] - 64.0) < 1e-9:            # a cut vert: u lerped 0..1
                    assert 0.0 < corner[3] < 1.0
    # THE WALL LAW: a vertical curtain (zero plan area, real 3D area) survives
    wall = ((10.0, 0.0, -10.0, 0.0, 0.0, 1.0, 0.0, 0.0),
            (14.0, 0.0, -10.0, 1.0, 0.0, 1.0, 0.0, 0.0),
            (10.0, 3.0, -10.0, 0.0, 1.0, 1.0, 0.0, 0.0))
    out = IN.split_borders8([(wall, FOREST, "forest")])
    assert sum(len(v) for v in out.values()) == 1


def test_raised_cosine_profile():
    assert IN.raised_cosine(0.0, 4.2, 18.0) == pytest.approx(4.2)
    assert IN.raised_cosine(18.0, 4.2, 18.0) == 0.0
    assert IN.raised_cosine(9.0, 4.2, 18.0) == pytest.approx(2.1)
    ys = [IN.raised_cosine(d, 4.2, 18.0) for d in (0, 3, 6, 9, 12, 15, 18)]
    assert all(a >= b for a, b in zip(ys, ys[1:]))


def test_decode_cell_pick_is_deterministic_and_avoids_neighbours():
    decoded = {(4, -3): ((0, 0), 90), (5, -4): ((1, 1), 0)}
    a = IN.decode_cell_pick((5, -3), dict(decoded))
    b = IN.decode_cell_pick((5, -3), dict(decoded))
    assert a == b
    assert a[0] not in {(0, 0), (1, 1)}                     # the W + S neighbour quads


# ---- the soup --------------------------------------------------------------------------------

def test_soup_from_blocks_classifies_fams_from_bytes():
    flat = 3.0
    tris = [
        (((0, flat, 0), (4, flat, 0), (0, flat, -4)), GRASS, _MAIN_U),          # main
        (((8, flat, 0), (12, flat, 0), (8, flat, -4)), GRASS, 0.4),             # stamp (u off-region)
        (((16, flat, 0), (20, flat, 0), (16, flat, -4)), FOREST, 0.5),          # forest
        (((24, flat, 0), (28, flat, 0), (24, flat, -4)), ROCK, 0.9),            # rock -> coast
    ]
    soup = IN.soup_from_blocks({(2, 5): _bm(tris, name="Block[2][5] Terrain", x=2, y=5)})
    fams = [m[2] for m in soup["meta"]]
    assert fams == ["main", "stamp", "forest", "rock"]
    assert len(soup["coast"]) == 3                          # the rock tri's verts
    # world frame: +64*bx on x, -64*by on z
    assert soup["pos"][0][0] == pytest.approx(2 * 64.0)
    assert soup["pos"][0][2] == pytest.approx(-5 * 64.0)


# ---- the hill --------------------------------------------------------------------------------

def test_build_hill_displaces_pure_y_and_gates_pass():
    soup = IN.soup_from_blocks({(0, 0): _mains_grid()})
    res = IN.build_hill(soup, center=(24.0, -24.0), height=3.5, radius=14.0,
                        log=lambda *a: None)
    assert res["report"]["displaced_tris"] > 40
    assert res["report"]["worst_flank"] <= IN.MAX_FLANK
    assert res["report"]["peak_y"] == pytest.approx(3.2 + 3.5, abs=0.2)
    (blk, bm), = res["changed"].items()
    peak = max(v[1] for v in bm.chan_arrays[CH_POS])
    assert peak == pytest.approx(3.2 + 3.5, abs=0.2)
    xs = {round(v[0], 3) for v in bm.chan_arrays[CH_POS]}   # pure-Y: x set unchanged
    assert xs == {round(i * 4.0, 3) for i in range(14)}
    # displaced verts got locally re-smoothed normals (no longer hard-up)
    tilted = [n for n in bm.chan_arrays[CH_NRM] if abs(n[1] - 1.0) > 1e-6]
    assert tilted


def test_build_hill_refuses_stacking_and_steep_flanks():
    soup = IN.soup_from_blocks({(0, 0): _mains_grid()})
    res = IN.build_hill(soup, center=(24.0, -24.0), height=3.5, radius=14.0,
                        log=lambda *a: None)
    # the rolling-relief envelope: the same footprint now spans 3.5u -> refused
    soup2 = IN.soup_from_blocks(res["changed"])
    with pytest.raises(ValueError, match="not lawful"):
        IN.build_hill(soup2, center=(24.0, -24.0), height=3.5, radius=14.0,
                      log=lambda *a: None)
    # the measured slope envelope: too prominent for the radius -> refused
    soup3 = IN.soup_from_blocks({(0, 0): _mains_grid()})
    with pytest.raises(ValueError, match="flank slope"):
        IN.build_hill(soup3, center=(24.0, -24.0), height=5.5, radius=14.0,
                      log=lambda *a: None)


# ---- the mountain ----------------------------------------------------------------------------

MASSIF = float(encode_id(topograph=49))
# the donor wears DISPATCH CONTEXT (Uaho's real massif is baked event=1/area=63 -- the
# alcove camera-zoom quirk + a latent place-entrance trigger); the carve must strip it
MASSIF_DONOR = float(encode_id(event=1, area=63, topograph=49))


def _pyramid_donor(cx=24.0, cz=-24.0, half=4.0, apex=4.0):
    """A 4-tri rock pyramid (topo 49, donor-context event/area bits) in donor block
    (0,0)'s local frame -- the minimal massif: base ring of 4 once-edges, rigid up-wound
    faces, no apertures."""
    c00 = (cx - half, 0.0, cz - half)
    c10 = (cx + half, 0.0, cz - half)
    c11 = (cx + half, 0.0, cz + half)
    c01 = (cx - half, 0.0, cz + half)
    top = (cx, apex, cz)
    tris = []
    for a, b in ((c10, c00), (c11, c10), (c01, c11), (c00, c01)):
        tris.append(((a, b, top), MASSIF_DONOR, _MAIN_U))
    return _bm(tris, name="Block[0][0] Terrain", x=0, y=0)


def _mountain_bench(y=3.2, n=13, cell=4.0):
    """The mains grid plus one topo-58 coast tri in the far corner (the mountain scan
    needs SOME non-plain tri to measure clearance against)."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    tris.append((((54.0, y, -54.0), (58.0, y, -54.0), (54.0, y, -58.0)), ROCK, 0.9))
    return _bm(tris)


def test_chain_rings_chains_multiple_cycles_and_refuses_degeneracy():
    sq1 = [IN.kk3(p) for p in ((0, 0, 0), (4, 0, 0), (4, 0, -4), (0, 0, -4))]
    sq2 = [IN.kk3(p) for p in ((10, 0, 0), (14, 0, 0), (14, 0, -4), (10, 0, -4))]
    edges = [tuple(sorted((sq1[k], sq1[(k + 1) % 4]))) for k in range(4)] + \
            [tuple(sorted((sq2[k], sq2[(k + 1) % 4]))) for k in range(4)]
    rings = IN.chain_rings(edges, "test")
    assert sorted(len(r) for r in rings) == [4, 4]
    assert {frozenset(r) for r in rings} == {frozenset(sq1), frozenset(sq2)}
    with pytest.raises(ValueError, match="not degree-2"):
        IN.chain_rings(edges[:-1], "test")


def test_signed_area_orientation():
    ccw = [(0, 0, 0), (4, 0, 0), (4, 0, 4), (0, 0, 4)]
    assert IN.signed_area(ccw) == pytest.approx(16.0)
    assert IN.signed_area(list(reversed(ccw))) == pytest.approx(-16.0)


def _patch_donor(monkeypatch, donor_bm):
    from ff9mapkit.world import extract as X

    def fake_read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if part != "terrain":
            raise FileNotFoundError("no object part in the synthetic donor")
        return donor_bm
    monkeypatch.setattr(X, "read_block", fake_read_block)


def test_carve_mountain_carries_the_pyramid_rigidly(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                            log=lambda *a: None)
    r = res["report"]
    assert r["blob_tris"] == 4 and r["plugs"] == 0 and res["rot"] in (0, 1, 2, 3)
    # rigid carry: the apex sits at bench ground + the donor's prominence
    assert r["peak_y"] == pytest.approx(3.2 + 4.0, abs=1e-6)
    assert r["rock_rigid"] == pytest.approx(0.0, abs=1e-9)
    (blk, bm), = res["changed"].items()
    assert blk == (0, 0)
    # tri accounting: kept = bench - dropped; new = 4 massif + zip
    bench_tris = len(_mountain_bench().tris)
    assert len(bm.tris) == bench_tris - r["dropped"] + 4 + r["zip_tris"]
    # the massif tris kept topograph 49 but the donor's event/area dispatch bits are
    # STRIPPED (the alcove camera-zoom / latent-entrance carry-fidelity fix)
    rock_ids = [t4[0] for t4 in bm.chan_arrays[CH_TAN] if t4[0] == MASSIF]
    assert len(rock_ids) == 4 * 3
    assert not any(t4[0] == MASSIF_DONOR for t4 in bm.chan_arrays[CH_TAN])


def test_carve_mountain_refusals(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    with pytest.raises(ValueError, match="leaves block"):
        IN.carve_mountain(soup, center=(60.0, -26.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)
    with pytest.raises(ValueError, match="not clear plain-grass"):
        IN.carve_mountain(soup, center=(46.0, -46.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)
    with pytest.raises(ValueError, match="no deployed override"):
        IN.carve_mountain(soup, near=(500.0, -500.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)
    # a grass-only donor has no massif
    _patch_donor(monkeypatch, _mains_grid())
    with pytest.raises(ValueError, match="no rock massif"):
        IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)


def test_carve_mountain_refuses_stacking(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, game=tmp_path,
                            log=lambda *a: None)
    soup2 = IN.soup_from_blocks(res["changed"])
    with pytest.raises(ValueError, match="not clear plain-grass"):
        IN.carve_mountain(soup2, center=(26.0, -26.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)


# ---- the deployed-block loader ---------------------------------------------------------------

def test_read_deployed_blocks_semantics(tmp_path):
    with pytest.raises(ValueError, match="no deployed Terrain overrides"):
        IN.read_deployed_blocks("modx", near=(96.0, -96.0), reach=40.0, game=tmp_path)
    p = tmp_path / "modx" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1"
    p.mkdir(parents=True)
    M.write_ff9mesh(_mains_grid(), p / "Block[1][1] Terrain.ff9mesh")
    out = IN.read_deployed_blocks("modx", near=(96.0, -96.0), reach=40.0, game=tmp_path)
    assert set(out) == {(1, 1)}
    assert out[(1, 1)].vcount == _mains_grid().vcount
