"""world-forest / world-hill / world-mountain -- the interior-topography verbs (hermetic).

The full-fidelity acceptance is the zero-byte-diff identity proof against the deployed,
in-game-proven island E / Uaho bench (``studies/overworld-topography/
interior_productize_check.py`` + ``mountain_productize_check.py`` -- mint -> module carve
reproduces the playtested bytes exactly). The identity assertions themselves are ported
here as the game-data-gated tests at the bottom (skipped without the install + the
deployed FF9CustomMap-world blocks); the studies keep the forensic extras (the mountain's
fresh-mint dent-tolerance TRACK B). The rest covers the hermetic machinery:

  * chain_ring (simple-cycle chaining + degeneracy refusal)
  * chain_rings (multi-cycle chaining + degree-2 refusal) + signed_area orientation
  * split_borders8 (64u border split, channel lerp, THE WALL LAW's true-3D-area filter)
  * raised_cosine + decode_cell_pick determinism
  * the zip-annulus fallback policy (THE DIVERSITY POLICY): assign_mains_seeded's exact
    assign_mains mirror + pre-seed semantics, the autocorrelation band vs the retired
    chevron picker, and a hermetic carve_forest whose whole ring falls back
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


def _patch_donor(monkeypatch, donor, parts=None):
    """``donor``: one BlockMesh (served for any block) or ``{(x, y): BlockMesh}``;
    ``parts``: optional ``{(x, y): {part_lowercase: BlockMesh}}`` auxiliary meshes."""
    from ff9mapkit.world import extract as X

    def fake_read_block(x, y, *, disc=1, lod="0_1", part="terrain", game=None):
        if part != "terrain":
            if parts and part in parts.get((x, y), {}):
                return parts[(x, y)][part]
            raise ValueError(f"disc{disc} block[{x}][{y}] {part} mesh not found")
        if isinstance(donor, dict):
            if (x, y) not in donor:
                raise ValueError(f"disc{disc} block[{x}][{y}] {part} mesh not found")
            return donor[(x, y)]
        return donor
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
    with pytest.raises(ValueError, match="needs deployed Terrain overrides"):
        IN.carve_mountain(soup, near=(500.0, -500.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)
    # a grass-only donor has no massif
    _patch_donor(monkeypatch, _mains_grid())
    with pytest.raises(ValueError, match="no rock massif"):
        IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)


def _cone_donor_blocks(cx=64.0, cz=-32.0, radius=26.0, apex=6.0):
    """A subdivided rock cone straddling donor blocks (0,0)/(1,0), pre-split at the 64u
    border exactly like stock data ships (identity welds at the cut)."""
    import math as _m
    rings = [(radius, 0.0), (radius * 0.75, apex * 0.25),
             (radius * 0.5, apex * 0.5), (radius * 0.25, apex * 0.75)]
    NSEG = 24

    def ring_pt(r, y, k):
        a = 2 * _m.pi * k / NSEG
        return (cx + r * _m.cos(a), y, cz + r * _m.sin(a))

    def up(tri):
        a, b, c = tri
        cy = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        return tri if cy > 0 else (a, c, b)

    tris3 = []
    for (r1, y1), (r2, y2) in zip(rings, rings[1:]):
        for k in range(NSEG):
            p00, p01 = ring_pt(r1, y1, k), ring_pt(r1, y1, k + 1)
            p10, p11 = ring_pt(r2, y2, k), ring_pt(r2, y2, k + 1)
            tris3.append(up((p00, p01, p10)))
            tris3.append(up((p01, p11, p10)))
    r4, y4 = rings[-1]
    for k in range(NSEG):
        tris3.append(up((ring_pt(r4, y4, k), ring_pt(r4, y4, k + 1), (cx, apex, cz))))
    parents = [(tuple((*p, _MAIN_U, 0.5, 0.0, 1.0, 0.0) for p in t), MASSIF_DONOR, "m")
               for t in tris3]
    out = {}
    for blk, pieces in IN.split_borders8(parents).items():
        bx, by = blk
        rows = [(tuple((c[0] - 64.0 * bx, c[1], c[2] + 64.0 * by) for c in corners),
                 MASSIF_DONOR, _MAIN_U) for corners, idall, fam in pieces]
        out[blk] = _bm(rows, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)
    return out


def _grid_block(bx, by, y=3.2, n=16, cell=4.0, extra=()):
    """A full-width (64u) mains grid block in local coords, plus optional extra tris."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    tris.extend(extra)
    return _bm(tris, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)


def test_carve_mountain_multiblock_span(monkeypatch, tmp_path):
    """A cross-border donor massif carried onto a 2x2 target span: the blob merges from
    two donor blocks, new tris split at the 64u borders, all four span blocks re-emit,
    and the rigid-carry + crack gates hold across the internal borders."""
    _patch_donor(monkeypatch, _cone_donor_blocks())
    coast = [(((2.0, 3.2, -2.0), (6.0, 3.2, -2.0), (2.0, 3.2, -6.0)), ROCK, 0.9)]
    soup = IN.soup_from_blocks({
        (0, 1): _grid_block(0, 1, extra=coast), (1, 1): _grid_block(1, 1),
        (0, 2): _grid_block(0, 2), (1, 2): _grid_block(1, 2)})
    res = IN.carve_mountain(soup, near=(64.0, -128.0), donor=[(0, 0), (1, 0)],
                            alcove=None, game=tmp_path, log=lambda *a: None)
    assert set(res["changed"]) == {(0, 1), (1, 1), (0, 2), (1, 2)}
    r = res["report"]
    assert sorted(map(tuple, r["blocks"])) == [(0, 1), (0, 2), (1, 1), (1, 2)]
    assert r["peak_y"] == pytest.approx(3.2 + 6.0, abs=1e-6)
    assert r["rock_rigid"] < 1e-6
    # the split massif lands rock (dispatch-stripped) in more than one block
    blocks_with_rock = [blk for blk, bm in res["changed"].items()
                        if any(t4[0] == MASSIF for t4 in bm.chan_arrays[CH_TAN])]
    assert len(blocks_with_rock) >= 2
    # a missing span block refuses up front
    soup2 = IN.soup_from_blocks({
        (0, 1): _grid_block(0, 1, extra=coast), (1, 1): _grid_block(1, 1),
        (0, 2): _grid_block(0, 2)})
    with pytest.raises(ValueError, match="needs deployed Terrain overrides"):
        IN.carve_mountain(soup2, near=(64.0, -128.0), donor=[(0, 0), (1, 0)],
                          alcove=None, game=tmp_path, log=lambda *a: None)


def test_ground_uv_desert_translation():
    """THE DESERT TRANSLATION LAW: desert mains = grass mains + (0.65332, -0.09863),
    byte-exact at 5dp against the measured desert rects."""
    for quad in ((0, 0), (0, 1), (1, 0), (1, 1)):
        gu, gv = G.mains_uv(2.0, -6.0, (0, -2), quad, 0)
        du, dv = G.ground_uv(2.0, -6.0, (0, -2), quad, 0, "desert")
        assert du == pytest.approx(gu + 0.65332, abs=1e-12)
        assert dv == pytest.approx(gv + -0.09863, abs=1e-12)
    # the translated region lands on the measured desert rects (5dp)
    lo_u, lo_v, hi_u, hi_v = G.ground_main_region("desert")
    assert lo_u == pytest.approx(0.65723, abs=1e-5)
    assert hi_u == pytest.approx(0.78027, abs=1e-5)
    assert lo_v == pytest.approx(0.66992, abs=1e-5)
    assert hi_v == pytest.approx(0.73145, abs=1e-5)
    # grass is the bit-frozen identity
    assert G.ground_uv(2.0, -6.0, (0, -2), (1, 0), 90) == \
        G.mains_uv(2.0, -6.0, (0, -2), (1, 0), 90)


def test_ground_families_registry():
    """THE TRANSLATION LAW IS UNIVERSAL (the ground-families census 2026-07-15):
    every registry family is a pure grass translation whose mains region + wall band
    stay inside the atlas; the measured 5dp deltas are pinned; grass stays first (the
    CLI default) and brush wears the desert wall (measured stock adjacency)."""
    assert tuple(G.GROUNDS)[0] == "grass"
    assert set(G.GROUNDS) == {"grass", "desert", "scrub", "brush", "snow",
                              "canyon", "dunes"}
    expect = {
        "scrub": (0.25977, -0.06738, 4),
        "brush": (0.45703, -0.20215, 38),
        "snow": (0.0, -0.33691, 27),
        "canyon": (0.7793, -0.31641, 45),
        "dunes": (0.38964, -0.13477, 41),
    }
    for name, (du, dv, topo) in expect.items():
        g = G.GROUNDS[name]
        assert (g["mains_du"], g["mains_dv"], g["topo"]) == (du, dv, topo), name
    for name, g in G.GROUNDS.items():
        lo_u, lo_v, hi_u, hi_v = G.ground_main_region(name)
        assert 0.0 <= lo_u < hi_u <= 1.0 and 0.0 <= lo_v < hi_v <= 1.0, name
        wu = (0.699 + g["wall_du"], 0.947 + g["wall_du"])
        wv = (0.893 + g["wall_dv"], 0.923 + g["wall_dv"])
        assert 0.0 <= wu[0] < wu[1] <= 1.0 and 0.0 <= wv[0] < wv[1] <= 1.0, name
        # translation composition: ground_uv == mains_uv + the family delta
        u, v = G.mains_uv(2.0, -6.0, (0, -2), (1, 0), 90)
        gu, gv = G.ground_uv(2.0, -6.0, (0, -2), (1, 0), 90, name)
        assert gu == pytest.approx(u + g["mains_du"], abs=1e-12), name
        assert gv == pytest.approx(v + g["mains_dv"], abs=1e-12), name
    assert G.GROUNDS["brush"]["wall_du"] == G.GROUNDS["desert"]["wall_du"]
    assert G.GROUNDS["brush"]["wall_dv"] == G.GROUNDS["desert"]["wall_dv"]
    # stock-role classes (the 2026-07-15 ground-sampler playtest): only "island"
    # families are whole-landmass fills whose coast reads native
    assert {n: g["cls"] for n, g in G.GROUNDS.items()} == {
        "grass": "island", "desert": "island", "snow": "island", "canyon": "island",
        "scrub": "transition", "brush": "slope", "dunes": "interior"}
    from ff9mapkit.cli import _ground_choices
    assert _ground_choices() == tuple(G.GROUNDS)


def test_carve_mountain_on_desert_ground(monkeypatch, tmp_path):
    """A carve onto a desert-family bench: plain classification, zip topo + UVs, and
    the outside-the-rim probe all speak topo-17 desert."""
    DESERT = float(encode_id(topograph=17))
    DES_U = _MAIN_U + 0.65332
    _patch_donor(monkeypatch, _pyramid_donor())
    tris = []
    for i in range(13):
        for j in range(13):
            x0, x1 = i * 4.0, (i + 1) * 4.0
            z0, z1 = -j * 4.0, -(j + 1) * 4.0
            tris.append((((x0, 3.2, z0), (x1, 3.2, z0), (x0, 3.2, z1)), DESERT, DES_U))
            tris.append((((x1, 3.2, z0), (x1, 3.2, z1), (x0, 3.2, z1)), DESERT, DES_U))
    tris.append((((54.0, 3.2, -54.0), (58.0, 3.2, -54.0), (54.0, 3.2, -58.0)), ROCK, 0.9))
    soup = IN.soup_from_blocks({(0, 0): _bm(tris)})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, ground="desert",
                            game=tmp_path, log=lambda *a: None)
    (blk, bm), = res["changed"].items()
    ids = {t4[0] for t4 in bm.chan_arrays[CH_TAN]}
    assert MASSIF in ids and DESERT in ids and GRASS not in ids
    # the zip annulus samples the desert mains region
    dlo, dvlo, dhi, dvhi = G.ground_main_region("desert")
    zips = [uv for uv, t4 in zip(bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN])
            if t4[0] == DESERT]
    assert all(dlo - 0.02 <= u <= dhi + 0.02 for (u, v) in zips)
    # a grass-ground carve on the same desert bench refuses (no plain ground)
    with pytest.raises(ValueError, match="not clear plain-grass|no non-plain|no lawful"):
        IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, ground="grass",
                          game=tmp_path, log=lambda *a: None)


def _frustum_donor_with_falls(cx=64.0, cz=-32.0, radius=26.0, apex=6.0):
    """A rock FRUSTUM straddling donor blocks (0,0)/(1,0) whose OPEN top ring is closed
    by a fake FALLS cap -- the minimal ENSEMBLE-aperture donor (the ring is owned by an
    auxiliary part, not the Object part)."""
    import math as _m
    rings = [(radius, 0.0), (radius * 0.75, apex * 0.25),
             (radius * 0.5, apex * 0.5), (radius * 0.25, apex * 0.75)]
    NSEG = 24

    def ring_pt(r, y, k):
        a = 2 * _m.pi * k / NSEG
        return (cx + r * _m.cos(a), y, cz + r * _m.sin(a))

    def up(tri):
        a, b, c = tri
        cy = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        return tri if cy > 0 else (a, c, b)

    tris3 = []
    for (r1, y1), (r2, y2) in zip(rings, rings[1:]):
        for k in range(NSEG):
            p00, p01 = ring_pt(r1, y1, k), ring_pt(r1, y1, k + 1)
            p10, p11 = ring_pt(r2, y2, k), ring_pt(r2, y2, k + 1)
            tris3.append(up((p00, p01, p10)))
            tris3.append(up((p01, p11, p10)))
    parents = [(tuple((*p, _MAIN_U, 0.5, 0.0, 1.0, 0.0) for p in t), MASSIF_DONOR, "m")
               for t in tris3]
    terr = {}
    for blk, pieces in IN.split_borders8(parents).items():
        bx, by = blk
        rows = [(tuple((c[0] - 64.0 * bx, c[1], c[2] + 64.0 * by) for c in corners),
                 MASSIF_DONOR, _MAIN_U) for corners, idall, fam in pieces]
        terr[blk] = _bm(rows, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)
    r4, y4 = rings[-1]
    cap = [(up((ring_pt(r4, y4, k), ring_pt(r4, y4, k + 1), (cx, y4, cz))),
            MASSIF, _MAIN_U) for k in range(NSEG)]
    falls = _bm(cap, name="Block[0][0] Falls", x=0, y=0)   # (0,0)-local == world here
    return terr, {(0, 0): {"falls": falls}}


def test_carve_mountain_ensemble_aperture(monkeypatch, tmp_path):
    """THE ENSEMBLE CARRY: a blob ring owned by an auxiliary part (not the Object part)
    classifies as an ensemble aperture, no plug is built, the part rides the same rigid
    map into changed_parts, and deploy_mountain_parts writes content + blanks + the
    Donor.txt divert."""
    terr, parts = _frustum_donor_with_falls()
    _patch_donor(monkeypatch, terr, parts=parts)
    coast = [(((2.0, 3.2, -2.0), (6.0, 3.2, -2.0), (2.0, 3.2, -6.0)), ROCK, 0.9)]
    soup = IN.soup_from_blocks({
        (0, 1): _grid_block(0, 1, extra=coast), (1, 1): _grid_block(1, 1),
        (0, 2): _grid_block(0, 2), (1, 2): _grid_block(1, 2)})
    res = IN.carve_mountain(soup, near=(64.0, -128.0), donor=[(0, 0), (1, 0)],
                            alcove=None, game=tmp_path, log=lambda *a: None)
    r = res["report"]
    assert r["plugs"] == 0 and r["ensemble_tris"] == 24
    assert res["donor_ref"] == (0, 0)
    all_parts = {p for pp in res["changed_parts"].values() for p in pp}
    assert all_parts == {"Falls"}
    # the cap rides rigidly: its highest vert sits at bench ground + the ring height
    ys = [v[1] for pp in res["changed_parts"].values() for bmp in pp.values()
          for v in bmp.chan_arrays[CH_POS]]
    assert max(ys) == pytest.approx(3.2 + 4.5, abs=1e-6)
    # THE SCENERY SEAL: every carried aux vert stores the blocked-topo IDALL (the
    # ground query reads tangent.x as movement legality; leftover real tangents
    # garbage-decode to walkable topo 0)
    scenery = float(encode_id(topograph=49))
    tans = [t4 for pp in res["changed_parts"].values() for bmp in pp.values()
            for t4 in bmp.chan_arrays[CH_TAN]]
    assert tans and all(t4[0] == scenery for t4 in tans)
    # deployment: content + blanks for every ensemble part + the Donor.txt divert
    outs = IN.deploy_mountain_parts(res, mod_folder="modx", game=tmp_path,
                                    log=lambda *a: None)
    root = tmp_path / "modx" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
    n_falls = n_donor = 0
    for blk in map(tuple, r["blocks"]):
        bx, by = blk
        for part in IN.ENSEMBLE_PARTS:
            assert (root / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh").exists()
        d = root / f"r{by}" / f"Block[{bx}][{by}] Donor.txt"
        assert d.exists()
        n_donor += 1
    assert outs and n_donor == len(r["blocks"])


def test_carve_mountain_refuses_stacking(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, game=tmp_path,
                            log=lambda *a: None)
    soup2 = IN.soup_from_blocks(res["changed"])
    with pytest.raises(ValueError, match="not clear plain-grass"):
        IN.carve_mountain(soup2, center=(26.0, -26.0), alcove=None, game=tmp_path,
                          log=lambda *a: None)


# ---- the forest zip-annulus fallback (THE DIVERSITY POLICY) ----------------------------------

def _adjacency_stats(cells_qo):
    """Same-quad / same-ori rates over within-set E/N-adjacent cell pairs -- the UV arc's
    texture-variety metric (uvf_fix2.adjacency_stats)."""
    pairs = [(c, n) for c in cells_qo for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1))
             if n in cells_qo]
    same_q = sum(1 for a, b in pairs if cells_qo[a][0] == cells_qo[b][0])
    same_o = sum(1 for a, b in pairs if cells_qo[a][1] == cells_qo[b][1])
    return len(pairs), same_q / len(pairs), same_o / len(pairs)


def test_assign_mains_seeded_is_assign_mains_on_an_empty_preseed():
    """The mirror claim is EXACT: with no pre-seed, the constrained-boundary form draws
    the identical stream and returns bit-identical (quad, ori) fields."""
    cells = {(i, j) for i in range(8) for j in range(-8, 0)}
    for seed in (0xF91, 0xF92, 7):
        assert G.assign_mains_seeded(cells, {}, {}, seed=seed) == \
            G.assign_mains(cells, seed=seed)


def test_assign_mains_seeded_consults_but_never_rewrites_the_preseed():
    pre_q = {(0, 0): (1, 0)}
    pre_o = {(0, 0): 90}
    out_q, out_o = G.assign_mains_seeded({(0, 1), (1, 0), (1, 1)}, pre_q, pre_o, seed=3)
    assert set(out_q) == set(out_o) == {(0, 1), (1, 0), (1, 1)}   # boundary not re-emitted
    assert pre_q == {(0, 0): (1, 0)} and pre_o == {(0, 0): 90}    # inputs untouched
    # (0,1) and (1,0) each have exactly ONE resolved neighbour -- the pre-seeded (0,0) --
    # so the anti-repeat guarantees neither wears its quadrant
    assert out_q[(0, 1)] != (1, 0) and out_q[(1, 0)] != (1, 0)


def test_diversity_policy_autocorrelation_beats_the_retired_picker():
    """THE DIVERSITY POLICY regression (GROUND-FAMILY-DECODE round 2 / uvf_fix2): over a
    region-scale field the seeded policy keeps assign_mains' neighbour coupling, while the
    retired uncoupled picker reads as the chevron quilt (same-ori ~uniform 0.25) with a
    RIGID quad alternation (same-quad exactly 0 under a fully-resolved neighbourhood)."""
    field = {(i, j) for i in range(30) for j in range(-30, 0)}
    q, o = G.assign_mains_seeded(field, {}, {}, seed=0xF92)
    n, sq, so = _adjacency_stats({c: (q[c], o[c]) for c in field})
    assert n == 1740
    assert 0.33 <= so <= 0.55           # measured 0.3885 (the assign_mains band)
    assert 0.06 <= sq <= 0.20           # measured 0.1132
    dec = {}
    for c in sorted(field):
        dec[c] = IN.decode_cell_pick(c, dec)
    n2, sq2, so2 = _adjacency_stats(dec)
    assert n2 == 1740
    assert so2 < 0.31 < so              # the chevron: measured 0.2701
    assert sq2 == 0.0                   # the union-avoid's rigid diamond lattice


def _canopy_donor(x0=8.0, z0=-8.0, n=5, cell=4.0):
    """A flat 5x5-cell topo-37 canopy carpet in the donor block's local frame -- the
    minimal blob: a square once-edge rim, zero relief (every step gate trivially clean)."""
    tris = []
    for i in range(n):
        for j in range(n):
            xa, xb = x0 + i * cell, x0 + (i + 1) * cell
            za, zb = z0 - j * cell, z0 - (j + 1) * cell
            tris.append((((xa, 0.0, za), (xb, 0.0, za), (xa, 0.0, zb)), FOREST, 0.5))
            tris.append((((xb, 0.0, za), (xb, 0.0, zb), (xa, 0.0, zb)), FOREST, 0.5))
    return _bm(tris, name="Block[15][15] Terrain", x=15, y=15)


def test_carve_forest_fallback_ring_wears_the_assign_mains_policy(monkeypatch, tmp_path):
    """The zip annulus on a synthetic bench (no decodable kept UVs -> every ring cell
    falls back): resolution goes through grassland.assign_mains_seeded, the ring's
    autocorrelation sits in the policy band rather than the retired picker's chevron,
    and the carve is deterministic end to end."""
    _patch_donor(monkeypatch, _canopy_donor())
    soup = IN.soup_from_blocks({(0, 0): _mains_grid()})
    res = IN.carve_forest(soup, center=(26.0, -26.0), donor=(15, 15), game=tmp_path,
                          log=lambda *a: None)
    assert res["report"]["zip_fallback_cells"] == len(res["zip_fallback"]) == 24
    assert set(res["zip_fallback"]) == set(res["zip_cells"])       # nothing decodes here
    n, sq, so = _adjacency_stats({c: res["zip_cells"][c] for c in res["zip_fallback"]})
    assert n == 24
    assert so >= 0.35                   # measured 11/24 = 0.458; the chevron sits ~0.25
    # determinism: an identical second carve resolves the identical field + bytes
    soup2 = IN.soup_from_blocks({(0, 0): _mains_grid()})
    res2 = IN.carve_forest(soup2, center=(26.0, -26.0), donor=(15, 15), game=tmp_path,
                           log=lambda *a: None)
    assert res2["zip_cells"] == res["zip_cells"]
    (blk, bm), = res["changed"].items()
    (blk2, bm2), = res2["changed"].items()
    assert blk == blk2 == (0, 0)
    assert bm.chan_arrays == bm2.chan_arrays and bm.tris == bm2.tris


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


def test_deploy_changed_cleans_up_its_scratch_dir(tmp_path):
    """The byte-compare scratch dir (one .ff9mesh per changed block, written purely to
    diff against the deployed file) must not survive the call."""
    import tempfile
    from pathlib import Path
    before = set(Path(tempfile.gettempdir()).glob("ff9_interior_*"))
    out = IN.deploy_changed({(2, 1): _mains_grid()}, mod_folder="modx",
                            game=tmp_path, log=lambda *a: None)
    assert out
    after = set(Path(tempfile.gettempdir()).glob("ff9_interior_*"))
    assert after == before


def test_wall_context_law_mint_guard():
    """THE WALL-CONTEXT LAW at the mint chokepoint: a minted island's rim is a SEA cliff
    by construction, and a family whose wall band is measured interior-only (canyon)
    refuses in build_landmass before any geometry work. Measured-coastal flags pinned."""
    from ff9mapkit.world import island as I
    with pytest.raises(ValueError, match="WALL-CONTEXT"):
        I.build_landmass(center=(288.0, -1243.0), ground="canyon")
    assert {n for n, g in G.GROUNDS.items() if g.get("wall_coastal") is True} == \
        {"grass", "desert", "snow"}
    assert G.GROUNDS["canyon"]["wall_coastal"] is False


# ---- game-data-gated: the zero-byte-diff identity net ----------------------------------------
#
# The ★ ZERO-BYTE-DIFF IDENTITY claims (world-forest/world-hill productized 2026-07-13,
# world-mountain productized 2026-07-15), ported from the study acceptance scripts so they
# are a standing regression net, not a proven-once-by-hand result. Each needs the FF9
# install (the mint/carve reads stock blocks via UnityPy) AND the deployed, in-game-proven
# FF9CustomMap-world overrides this machine playtested -- both gates checked explicitly so
# a fresh install (game present, nothing deployed) skips instead of failing.

ISLAND_E_BLOCKS = [(4, 17), (5, 17), (4, 18), (5, 18), (6, 18)]
UAHO_SEED_PT = (160.0, -1246.0)                             # the study's own scan seed


def _modw():
    from ff9mapkit import config
    return (config.find_game_path(None) / "FF9CustomMap-world" / "FF9_Data" / "WorldMap"
            / "Disc1" / "0_1")


def _game_ready() -> bool:
    try:
        import UnityPy  # noqa: F401
        from ff9mapkit import config
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _uaho_ready() -> bool:
    try:
        if not _game_ready():
            return False
        dep = _modw() / "r19" / "Block[2][19] Terrain.ff9mesh"
        return dep.is_file() and dep.with_name(dep.name + ".pristine-r31s42").is_file()
    except Exception:
        return False


def _island_e_ready() -> bool:
    try:
        if not _game_ready():
            return False
        return all((_modw() / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh").is_file()
                   for bx, by in ISLAND_E_BLOCKS)
    except Exception:
        return False


@pytest.mark.skipif(not _uaho_ready(),
                    reason="needs the FF9 install + UnityPy + the deployed Uaho bench "
                           "(Block[2][19] and its .pristine-r31s42 sibling)")
def test_carve_mountain_reproduces_deployed_uaho_bench(tmp_path):
    """THE IDENTITY NET (mountain): the pristine r31-seed-42 bench mint the study actually
    transformed -> carve_mountain at the study's own scan seed -> byte-identical to the
    deployed, in-game-approved Block[2][19] ("the cliff is great -- walkable, seams
    against the grass great", 2026-07-13). The pristine input still carries the pre-fix
    mint's one-tri hole, so the module's mint-hole patch is exercised too. Ported from
    mountain_productize_check.py TRACK A."""
    dep_p = _modw() / "r19" / "Block[2][19] Terrain.ff9mesh"
    pris = dep_p.with_name(dep_p.name + ".pristine-r31s42")
    bm = M.blockmesh_from_ff9mesh(pris, disc=1, x=2, y=19, part="terrain")
    soup = IN.soup_from_blocks({(2, 19): bm})
    res = IN.carve_mountain(soup, near=UAHO_SEED_PT, log=lambda *a: None)
    got = M.write_ff9mesh(res["changed"][(2, 19)], tmp_path / "a.ff9mesh").read_bytes()
    assert got == dep_p.read_bytes(), "carve output differs from the deployed Uaho bench"


@pytest.mark.skipif(not _island_e_ready(),
                    reason="needs the FF9 install + UnityPy + the deployed island E "
                           "blocks in FF9CustomMap-world")
def test_interior_pipeline_reproduces_deployed_island_e(tmp_path):
    """THE IDENTITY NET (forest + hill): clean seed-55 mint -> carve_forest at the center
    recovered from the deployed canopy -> f32 write/read-back (the deployed
    representation) -> build_hill -> all 5 deployed island E blocks byte-identical
    (in-game proven 2026-07-13). Ported from interior_productize_check.py.
    NOTE: the zip fallback moved to the assign_mains policy (THE DIVERSITY POLICY,
    2026-07-25) -- identity holds against a deploy CARVED BY THIS MODULE; the pre-policy
    island E bytes (36 fallback cells' zip UVs, the old chevron ring) no longer match, so
    restore-from-old-backup would fail here by design. Re-carve + redeploy instead."""
    from ff9mapkit.world.extract import decode_id
    from ff9mapkit.world.island import build_landmass

    modw = _modw()
    # recover the forest center from the deployed canopy bytes (topo 37)
    xs, zs = [], []
    for bx, by in ISLAND_E_BLOCKS:
        p = modw / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        ts = bm.chan_arrays[CH_TAN]
        ps = bm.chan_arrays[CH_POS]
        for tri in bm.tris:
            if decode_id(int(round(ts[tri[0]][0])))["topograph"] == 37:
                for i in tri:
                    xs.append(ps[i][0] + 64.0 * bx)
                    zs.append(ps[i][2] - 64.0 * by)
    assert xs, "no deployed canopy found on island E"
    center = (round((min(xs) + max(xs)) / 2), round((min(zs) + max(zs)) / 2))

    built = build_landmass(center=(344, -1152), base_radius=46, seed=55, lobes=3,
                           stamps="auto")
    res_f = IN.carve_forest(IN.soup_from_blocks(built["blocks"]), center=center,
                            donor=(15, 15))
    IN.census_gate(res_f["changed"], probe=(center, 37))
    paths = {blk: M.write_ff9mesh(bm, tmp_path / f"f_{blk[0]}_{blk[1]}.ff9mesh")
             for blk, bm in res_f["changed"].items()}
    blocks2 = {blk: M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1],
                                             part="terrain")
               for blk, p in paths.items()}
    res_h = IN.build_hill(IN.soup_from_blocks(blocks2), center=(348, -1184))
    IN.census_gate(res_h["changed"])
    assert sorted(res_h["changed"]) == [(5, 18)]
    for blk in ISLAND_E_BLOCKS:
        if blk in res_h["changed"]:
            got = M.write_ff9mesh(res_h["changed"][blk],
                                  tmp_path / f"h_{blk[0]}_{blk[1]}.ff9mesh").read_bytes()
        else:
            got = paths[blk].read_bytes()
        dep = (modw / f"r{blk[1]}" / f"Block[{blk[0]}][{blk[1]}] Terrain.ff9mesh")
        assert got == dep.read_bytes(), f"block {blk} differs from the deployed island E"
