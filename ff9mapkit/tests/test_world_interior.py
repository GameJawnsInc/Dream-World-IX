"""world-forest / world-hill / world-mountain -- the interior-topography verbs (hermetic).

The full-fidelity acceptance is the zero-byte-diff identity proof against the in-game-proven
island E / Uaho bench (``studies/overworld-topography/interior_productize_check.py`` +
``mountain_productize_check.py`` -- mint -> module carve reproduces the playtested bytes
exactly). The identity assertions themselves are ported here as the game-data-gated tests at
the bottom: inputs rebuilt in-test, outputs pinned as SHA-256 digests, so they need only the
install + UnityPy (the stock donor read) and never the shared FF9CustomMap-world folder. The
rest covers the hermetic machinery:

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
  * THE T-JUNCTION LERP LAW: a saddle-rim donor over a T-vert lattice bench -- the ground
    apron pins each T-vert's lift to its host edge's lerp (the R4 hairline-slit class)
  * read_deployed_blocks against a temp game dir (found / not-found semantics)
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

import numpy as np

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
    with pytest.raises(IN.CarveRefused) as e:
        IN.chain_ring(edges[:-1], "test")
    assert e.value.gate == "ring" and len(e.value.where) == 2


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


def _mountain_bench(y=3.2, n=13, cell=4.0, coast=True):
    """The mains grid plus one topo-58 coast tri in the far corner. ``coast=False`` drops it:
    the all-lawn span of a small donor's single-block seat in a continent's interior."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    if coast:
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
    with pytest.raises(IN.CarveRefused) as e:                # it says where (rung C16): the two odd points
        IN.chain_rings(edges[:-1], "test")
    assert e.value.gate == "ring" and len(e.value.where) == 2
    assert set(e.value.where) <= {(float(p[0]), float(p[2])) for p in sq1 + sq2}


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


def test_carve_mountain_seats_on_an_all_lawn_interior_span(monkeypatch, tmp_path):
    """THE INTERIOR SEAT (R5-UAHO-BENCH.md): a span with NO non-plain tri is a continent's interior lawn,
    not a malformed bench -- the carve places (it used to refuse: "no coast to place against"). With no
    coast to rank clearance by, the scan takes the candidate nearest the requested seat, rot 0 preferred,
    and every downstream gate still runs."""
    _patch_donor(monkeypatch, _pyramid_donor())
    logs = []
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench(coast=False)})
    res = IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                            log=lambda *a: logs.append(" ".join(str(x) for x in a)))
    assert res["center"] == (26, -26) and res["rot"] == 0
    assert any("INTERIOR seat" in line for line in logs)
    assert any("clearance unbounded" in line for line in logs)
    r = res["report"]
    assert r["blob_tris"] == 4 and r["peak_y"] == pytest.approx(3.2 + 4.0, abs=1e-6)
    # an exact --center on the same all-lawn span places too
    res2 = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _mountain_bench(coast=False)}),
                             center=(30.0, -30.0), alcove=None, game=tmp_path, log=lambda *a: None)
    assert res2["center"] == (30.0, -30.0)


def test_a_weld_split_the_zip_never_touches_does_not_refuse_the_mountain(monkeypatch, tmp_path):
    """THE EXACT-WELD LAW checks only the hole ring's keys (rung C16): the zip welds to nothing else. Checked over the
    whole read window, a sub-millimetre split anywhere in it -- float noise between two old writers; the live folder
    held four -- refused every mountain whose window reached it, and said nowhere (the refusal sweep: 16 of 30 lawful
    mountain spots on the live island)."""
    _patch_donor(monkeypatch, _pyramid_donor())
    tris, y = [], 3.2
    for i in range(13):
        for j in range(13):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    # a vertex the hole never reaches, shared by several tris: one copy 3e-4u off, the same 1e-3 key, two floats
    k = next(n for n, (c, _i, _u) in enumerate(tris) if (48.0, y, -48.0) in c)
    tris[k] = (tuple((48.0003, y, -48.0) if p == (48.0, y, -48.0) else p for p in tris[k][0]),) + tris[k][1:]
    soup = IN.soup_from_blocks({(0, 0): _bm(tris)})
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, game=tmp_path, log=lambda *a: None)
    assert res["center"] == (26.0, -26.0) and res["report"]["blob_tris"] == 4


def test_the_apron_slope_judges_the_grass_the_apron_lifted(monkeypatch, tmp_path):
    """THE APRON SLOPE, on the apron (rung C17): judged over every plain tri of the span, steep grass the lift never
    moved -- a hill's flank, a vertical curtain, ground as the island already had it, up to 107u off -- refused every
    mountain whose span reached it (all 42 apron refusals of 150 measured checks; 39 of them pass now)."""
    _patch_donor(monkeypatch, _pyramid_donor())
    tris = []
    for i in range(13):
        for j in range(13):
            x0, x1, z0, z1 = i * 4.0, (i + 1) * 4.0, -j * 4.0, -(j + 1) * 4.0
            tris.append((((x0, 3.2, z0), (x1, 3.2, z0), (x0, 3.2, z1)), GRASS, _MAIN_U))
            tris.append((((x1, 3.2, z0), (x1, 3.2, z1), (x0, 3.2, z1)), GRASS, _MAIN_U))
    tris.append((((48.0, 3.2, -50.0), (52.0, 3.2, -50.0), (48.0, 7.2, -50.0)), GRASS, _MAIN_U))   # a vertical curtain
    res = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _bm(tris)}), center=(26.0, -26.0), alcove=None,
                            game=tmp_path, log=lambda *a: None)
    assert res["report"]["apron_slope"] < IN.MTN_APRON_SLOPE      # the curtain is far past the apron's reach


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


def _saddle_pyramid_donor(cx=24.0, cz=-24.0, half=4.0, apex=5.0):
    """The rigid-carry pyramid with a PURE-SADDLE base ring (heights 0.0/0.6/0.0/0.5:
    no planar component, so de-tilt keeps the +-0.28u residual): the apron lift field
    around the carried rim is genuinely nonuniform."""
    hs = (0.0, 0.6, 0.0, 0.5)
    c00 = (cx - half, hs[0], cz - half)
    c10 = (cx + half, hs[1], cz - half)
    c11 = (cx + half, hs[2], cz + half)
    c01 = (cx - half, hs[3], cz + half)
    top = (cx, apex, cz)
    tris = []
    for a, b in ((c10, c00), (c11, c10), (c01, c11), (c00, c01)):
        tris.append(((a, b, top), MASSIF_DONOR, _MAIN_U))
    return _bm(tris, name="Block[0][0] Terrain", x=0, y=0)


def test_carve_mountain_small_donor_beside_deployed_neighbours_takes_the_multiblock_span(monkeypatch, tmp_path):
    """THE CONTINENT ROUTE (R5-UAHO-BENCH.md): a small donor fits one block, but on a continent that block's
    borders weld to DEPLOYED neighbours the single-block span never loads, so the apron lift reaching a border
    split the weld there (Uaho at the west-seam R4 slot: 8 new once-edges on x=1472). With a deployed
    neighbour inside the apron reach, the carve takes the multi-block span: the neighbour loads and the lift
    applies per POSITION on both sides of the border."""
    _patch_donor(monkeypatch, _saddle_pyramid_donor())
    logs = []
    soup = IN.soup_from_blocks({(0, 0): _grid_block(0, 0), (1, 0): _grid_block(1, 0)})
    res = IN.carve_mountain(soup, center=(50.0, -24.0), alcove=None, game=tmp_path,
                            log=lambda *a: logs.append(" ".join(str(x) for x in a)))
    assert any("deployed neighbour" in line for line in logs)
    assert sorted(map(tuple, res["report"]["blocks"])) == [(0, 0), (1, 0)]
    # the shared border x = 64: every position on it carries ONE height, whichever block holds it
    out = {blk: bm for blk, bm in soup["blocks"].items()}
    out.update(res["changed"])

    def border(blk, local_x):
        bx, _by = blk
        return {round(float(p[2]), 4): round(float(p[1]), 6) for p in out[blk].chan_arrays[CH_POS]
                if abs(float(p[0]) - local_x) < 1e-6}
    left, right = border((0, 0), 64.0), border((1, 0), 0.0)
    shared = set(left) & set(right)
    assert len(shared) >= 10
    assert all(left[z] == right[z] for z in shared), "the x=64 weld split"
    # and the lift really reached the border (the case is not vacuous)
    assert any(abs(left[z] - 3.2) > 1e-4 for z in shared)


def _with_mains_uv(bm, tris):
    """Rewrite each GRASS tri's corner UVs to its centroid cell's exact mains map
    (quad (0,0), ori 0) so the mint-hole patch can decode every cell."""
    uv = bm.chan_arrays[CH_UV]
    for t_i, (corners, idall, _u) in enumerate(tris):
        if idall != GRASS:
            continue
        cx = sum(c[0] for c in corners) / 3.0
        cz = sum(c[2] for c in corners) / 3.0
        cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
        for k, c in enumerate(corners):
            uv[bm.tris[t_i][k]] = list(G.mains_uv(c[0], c[2], cell, (0, 0), 0))
    return bm


def _tjunction_bench(y=3.2, n=13, cell=4.0):
    """``_mountain_bench`` but with cells (9,5)+(9,6) merged into ONE coarse 4x8 quad:
    the fine neighbour columns' verts at z=-24 become lattice T-verts lying inside the
    quad's 8u west/east edges (1mm off the host line, as real lattices ship -- the
    mint-hole patch seals each colinear 3-cycle with a near-degenerate sliver, exactly
    the R4 continent class). Mains UVs are the real per-cell map so those cells decode."""
    tv = {(36.0, -24.0): 36.001, (40.0, -24.0): 40.001}
    tris = []
    for i in range(n):
        for j in range(n):
            if (i, j) in ((9, 5), (9, 6)):
                continue
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            for c in (((x0, y, z0), (x1, y, z0), (x0, y, z1)),
                      ((x1, y, z0), (x1, y, z1), (x0, y, z1))):
                c = tuple((tv.get((p[0], p[2]), p[0]), p[1], p[2]) for p in c)
                tris.append((c, GRASS, _MAIN_U))
    tris.append((((36.0, y, -20.0), (40.0, y, -20.0), (36.0, y, -28.0)), GRASS, _MAIN_U))
    tris.append((((40.0, y, -20.0), (40.0, y, -28.0), (36.0, y, -28.0)), GRASS, _MAIN_U))
    tris.append((((54.0, y, -54.0), (58.0, y, -54.0), (54.0, y, -58.0)), ROCK, 0.9))
    return _with_mains_uv(_bm(tris), tris)


def test_carve_mountain_pins_tjunction_verts_to_the_host_edge(monkeypatch, tmp_path):
    """THE T-JUNCTION LERP LAW (the R4 west-seam hairlines): a lattice T-vert -- a
    position lying colinear inside a neighboring tri's edge -- must land ON the deformed
    host edge, not at its own IDW lift; the nonlinearity difference is the hairline-slit
    class. Before the law, this exact carve REFUSED at the apron-slope gate (the
    mint-hole sliver tipped 86deg toward vertical -- the in-game 1px seam)."""
    _patch_donor(monkeypatch, _saddle_pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _tjunction_bench()})
    logs = []
    res = IN.carve_mountain(soup, center=(26.0, -26.0), alcove=None, gblend=18.0,
                            game=tmp_path,
                            log=lambda *a: logs.append(" ".join(map(str, a))))
    assert any(s.startswith("apron T-junction lerp: 2 ") for s in logs)
    bm = res["changed"][(0, 0)]
    yat = {(round(v[0], 3), round(v[2], 3)): v[1] for v in bm.chan_arrays[CH_POS]}
    for x in (36.0, 40.0):
        ya, yt, yb = yat[(x, -20.0)], yat[(x + 0.001, -24.0)], yat[(x, -28.0)]
        # the field really lifted and really is nonuniform here (no vacuous pass)
        assert abs(ya - 3.2) > 5e-3 and abs(yb - 3.2) > 5e-3 and abs(ya - yb) > 1e-3
        # THE LAW: the T-vert sits exactly on the deformed host edge (t = 1/2)
        assert abs(yt - (ya + yb) / 2.0) < 1e-9


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


def _carve_pyramid(tmp_path, **kw):
    return IN.carve_mountain(IN.soup_from_blocks({(0, 0): _mountain_bench()}), center=(26.0, -26.0),
                             alcove=None, game=tmp_path, log=lambda *a: None, **kw)


def test_carve_mountain_rock_height_stretches_the_rock_about_its_rim(monkeypatch, tmp_path):
    """--rock-height (terrain study X1, in-game passed to x2.0): the pyramid's apex rises x1.5 above its base
    ring; the ring (the rim) and everything round it stay where the rigid carry puts them, UVs carried; the
    rigidity gate measures the carry against the DECLARED shape (drift 0, not the raw donor's 50%)."""
    _patch_donor(monkeypatch, _pyramid_donor())
    rigid = _carve_pyramid(tmp_path)
    res = _carve_pyramid(tmp_path, rock_height=1.5)
    r = res["report"]
    assert r["peak_y"] == pytest.approx(3.2 + 6.0, abs=1e-5)
    assert r["rock_rigid"] < 1e-6
    assert (r["rock_height"]["pinned"], r["rock_height"]["free"]) == (4, 1)
    a, b = rigid["changed"][(0, 0)], res["changed"][(0, 0)]
    pa, pb = a.chan_arrays[CH_POS], b.chan_arrays[CH_POS]
    assert len(pa) == len(pb) and a.flat_index == b.flat_index
    moved = [k for k in range(len(pa)) if pa[k] != pb[k]]
    assert len(moved) == 4                                      # the apex, once per rock face
    assert all(pa[k][1] == pytest.approx(3.2 + 4.0, abs=1e-5) and pb[k][1] == pytest.approx(3.2 + 6.0, abs=1e-5)
               and (pa[k][0], pa[k][2]) == (pb[k][0], pb[k][2]) for k in moved)
    assert a.chan_arrays[CH_UV] == b.chan_arrays[CH_UV]


def test_carve_mountain_rock_height_one_is_the_rigid_carry(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    rigid = M.write_ff9mesh(_carve_pyramid(tmp_path)["changed"][(0, 0)], tmp_path / "a.ff9mesh").read_bytes()
    same = M.write_ff9mesh(_carve_pyramid(tmp_path, rock_height=1.0)["changed"][(0, 0)],
                           tmp_path / "b.ff9mesh").read_bytes()
    assert rigid == same


def test_carve_mountain_rock_height_refusals(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    for s in (0.8, 2.5):                                        # outside what was seen in game
        with pytest.raises(ValueError, match=r"outside 1\.0\.\.2"):
            _carve_pyramid(tmp_path, rock_height=s)
    _patch_donor(monkeypatch, _pyramid_donor(apex=20.0))      # x2: 3.2 + 40 = 43.2, above stock's tallest
    with pytest.raises(ValueError, match="tallest terrain"):
        _carve_pyramid(tmp_path, rock_height=2.0)
    _carve_pyramid(tmp_path, rock_height=1.5)                   # 3.2 + 30 = 33.2: lawful
    terr, parts = _frustum_donor_with_falls()                   # a falls riding the face would not follow
    _patch_donor(monkeypatch, terr, parts=parts)
    coast = [(((2.0, 3.2, -2.0), (6.0, 3.2, -2.0), (2.0, 3.2, -6.0)), ROCK, 0.9)]
    soup = IN.soup_from_blocks({
        (0, 1): _grid_block(0, 1, extra=coast), (1, 1): _grid_block(1, 1),
        (0, 2): _grid_block(0, 2), (1, 2): _grid_block(1, 2)})
    with pytest.raises(ValueError, match="not welded to the rock"):
        IN.carve_mountain(soup, near=(64.0, -128.0), donor=[(0, 0), (1, 0)], alcove=None, game=tmp_path,
                          rock_height=1.5, log=lambda *a: None)


def test_carve_mountain_rock_height_gate_still_catches_an_undeclared_stretch(monkeypatch, tmp_path):
    """Break-it: if the map stretched the rock but declared the RAW donor as its shape, the rock-rigid gate must
    refuse -- the gate is what keeps every deformation but the declared one out."""
    _patch_donor(monkeypatch, _pyramid_donor())
    real = IN._rock_height_map

    def undeclared(B, s, **kw):
        V, N, _ref, rep = real(B, s, **kw)
        return V, N, B["dV"], rep
    monkeypatch.setattr(IN, "_rock_height_map", undeclared)
    with pytest.raises(ValueError, match="deformed beyond"):
        _carve_pyramid(tmp_path, rock_height=1.5)


def test_carve_mountain_zip_welds_bit_for_bit_to_the_kept_grass(monkeypatch, tmp_path):
    """THE EXACT-WELD LAW (round 16: the owner saw 1-pixel seams round the foot). The zip's grass side was built
    from the hole ring's kk3 KEYS (rounded to 1e-3), so on ground whose heights are not round it sat up to 5e-4u
    off the kept grass -- one weld, two floats, a pinhole on screen, invisible to every key-based gate. On a bench
    at y 3.21371 every position the carve emits must be ONE float triple, however many entries share it."""
    _patch_donor(monkeypatch, _pyramid_donor())
    res = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _mountain_bench(y=3.21371)}), center=(26.0, -26.0),
                            alcove=None, game=tmp_path, log=lambda *a: None)
    floats = defaultdict(set)
    for p in res["changed"][(0, 0)].chan_arrays[CH_POS]:
        floats[IN.kk3(p)].add(tuple(p))
    split = {k: v for k, v in floats.items() if len(v) > 1}
    assert not split, f"{len(split)} welds hold two floats, e.g. {next(iter(split.items()))}"
    assert res["report"]["zip_tris"] > 0


def test_carve_mountain_rot_deg_turns_the_massif_to_any_angle(monkeypatch, tmp_path):
    """--rot: the pyramid turned 45 deg about its centre -- its base corners now on the axes, the apex (on the axis)
    unmoved, rigid (drift 0), UVs carried; 0 deg is byte-identical to the default exact carry, and a quarter angle
    takes the exact quarter-turn swap the scan uses."""
    _patch_donor(monkeypatch, _pyramid_donor())
    rigid = _carve_pyramid(tmp_path)
    zero = _carve_pyramid(tmp_path, rot_deg=0)
    assert (M.write_ff9mesh(rigid["changed"][(0, 0)], tmp_path / "a.ff9mesh").read_bytes()
            == M.write_ff9mesh(zero["changed"][(0, 0)], tmp_path / "b.ff9mesh").read_bytes())
    res = _carve_pyramid(tmp_path, rot_deg=45)
    r = res["report"]
    assert r["rot_deg"] == pytest.approx(45.0) and r["rock_rigid"] < 1e-6
    assert r["peak_y"] == pytest.approx(3.2 + 4.0, abs=1e-6)
    bm = res["changed"][(0, 0)]
    pos, tan = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
    base = {(round(p[0], 3), round(p[2], 3)) for p, t4 in zip(pos, tan) if t4[0] == MASSIF and p[1] < 3.2 + 1e-6}
    h = 4.0 * math.sqrt(2.0)                                  # a corner at half-diagonal, now on an axis
    assert base == {(round(26.0 + dx, 3), round(-26.0 + dz, 3)) for dx, dz in ((h, 0), (-h, 0), (0, h), (0, -h))}
    uv_rock = sorted(tuple(u) for u, t4 in zip(bm.chan_arrays[CH_UV], tan) if t4[0] == MASSIF)
    uv_rigid = sorted(tuple(u) for u, t4 in zip(rigid["changed"][(0, 0)].chan_arrays[CH_UV],
                                                 rigid["changed"][(0, 0)].chan_arrays[CH_TAN]) if t4[0] == MASSIF)
    assert uv_rock == uv_rigid
    q = _carve_pyramid(tmp_path, rot_deg=450)                 # 450 = 90: the int swap, not cos/sin
    assert q["rot"] == 1 and isinstance(q["rot"], int) and q["report"]["rot_deg"] == 90
    with pytest.raises(ValueError, match="finite angle"):
        _carve_pyramid(tmp_path, rot_deg=float("nan"))


def _faceted_pyramid_donor(**kw):
    """The pyramid with each face's stored normal its geometric normal (``_bm`` stores +y)."""
    bm = _pyramid_donor(**kw)
    pos, nrm = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_NRM]
    for tri in bm.tris:
        a, b, c = (np.asarray(pos[i], dtype=float) for i in tri)
        n = np.cross(b - a, c - a)
        for i in tri:
            nrm[i] = (n / np.linalg.norm(n)).tolist()
    return bm


def _rock_tris(res):
    """The carried rock tris as (corner positions, corner normals), in emitted order."""
    bm = res["changed"][(0, 0)]
    pos, nrm, tan = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_NRM], bm.chan_arrays[CH_TAN]
    return [([pos[i] for i in t], [nrm[i] for i in t]) for t in bm.tris if tan[t[0]][0] == MASSIF]


def test_carve_mountain_spread_widens_the_massif_in_plan_and_keeps_its_heights(monkeypatch, tmp_path):
    """--spread (the massif twin of world-forest --spread): the pyramid's base corners land at centre +
    1.5 x their rigid offset, the apex stays put, UVs carried; every rock normal is still its carried face's
    normal (the inverse transpose of a plan scale is exact on a plane); the rigidity gate measures the carry
    against the widened shape (drift 0, not the raw donor's 50%)."""
    _patch_donor(monkeypatch, _faceted_pyramid_donor())
    rigid = _carve_pyramid(tmp_path)
    res = _carve_pyramid(tmp_path, spread=1.5)
    r = res["report"]
    assert r["spread"] == 1.5 and r["rock_rigid"] < 1e-6
    assert r["peak_y"] == pytest.approx(3.2 + 4.0, abs=1e-6)
    # THE RIM GRAIN: each 12u widened base edge (the donor's are 8u) splits in two at its midpoint
    assert r["rim_splits"] == 4 and len(_rock_tris(res)) == 8
    base = {(round(p[0] - 26.0, 3), round(p[2] + 26.0, 3)) for ps, _ in _rock_tris(res) for p in ps
            if p[1] < 3.2 + 1e-6}
    assert base == {(dx, dz) for dx in (-6.0, 0.0, 6.0) for dz in (-6.0, 0.0, 6.0)} - {(0.0, 0.0)}
    for ps, ns in _rock_tris(res):
        a, b, c = (np.asarray(p, dtype=float) for p in ps)
        face = np.cross(b - a, c - a)
        face /= np.linalg.norm(face)
        for n in ns:
            assert np.linalg.norm(n) == pytest.approx(1.0, abs=1e-9)
            assert np.allclose(n, face, atol=1e-9)
    uv = lambda rr: sorted(tuple(u) for u, t4 in zip(rr["changed"][(0, 0)].chan_arrays[CH_UV],  # noqa: E731
                                                     rr["changed"][(0, 0)].chan_arrays[CH_TAN]) if t4[0] == MASSIF)
    assert set(uv(res)) == set(uv(rigid))                                 # carried (and lerped on a split edge)
    assert res["report"]["dropped"] > rigid["report"]["dropped"]          # a wider hole for a wider foot


def test_carve_mountain_spread_with_matching_height_is_a_uniform_scale(monkeypatch, tmp_path):
    """--spread s with --rock-height s: the massif scaled whole about its foot -- every carried rock vertex, shrunk
    back by s about (centre, bench height), lies on the rigid pyramid's surface, and the apex is s times as tall."""
    _patch_donor(monkeypatch, _pyramid_donor())
    res = _carve_pyramid(tmp_path, spread=1.5, rock_height=1.5)
    assert res["report"]["peak_y"] == pytest.approx(3.2 + 6.0, abs=1e-5) and res["report"]["rock_rigid"] < 1e-6
    for ps, _ in _rock_tris(res):
        for p in ps:
            dx, h, dz = (p[0] - 26.0) / 1.5, (p[1] - 3.2) / 1.5, (p[2] + 26.0) / 1.5
            assert max(abs(dx), abs(dz)) <= 4.0 + 1e-9
            assert h == pytest.approx(4.0 * (1.0 - max(abs(dx), abs(dz)) / 4.0), abs=1e-6)


def test_carve_mountain_spread_one_is_the_rigid_carry_and_refusals(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _pyramid_donor())
    rigid = M.write_ff9mesh(_carve_pyramid(tmp_path)["changed"][(0, 0)], tmp_path / "a.ff9mesh").read_bytes()
    same = M.write_ff9mesh(_carve_pyramid(tmp_path, spread=1.0)["changed"][(0, 0)],
                           tmp_path / "b.ff9mesh").read_bytes()
    assert rigid == same
    for s in (0.9, IN.MTN_SPREAD_MAX + 0.01, float("nan")):           # past what was seen in game
        with pytest.raises(ValueError, match=r"outside 1\.0\.\.1\.5"):
            _carve_pyramid(tmp_path, spread=s)


def test_carve_mountain_spread_gate_still_catches_an_undeclared_widening(monkeypatch, tmp_path):
    """Break-it: if the carry widened the rock but declared the RAW donor as its shape, the rock-rigid gate must
    refuse -- the declared shape is what licenses the stretch, nothing else."""
    _patch_donor(monkeypatch, _pyramid_donor())
    monkeypatch.setattr(IN, "_plan_spread", lambda V, c, s: np.array(V, dtype=float))
    with pytest.raises(ValueError, match="deformed beyond"):
        _carve_pyramid(tmp_path, spread=1.5)


BANK_SKIP = 4088.0                                       # topo 62 (stream bank) at area 15: the engine skips it


def test_the_dispatch_strip_keeps_an_idall_the_ground_query_skips():
    """THE BANK SKIP LAW (watercarry/RECON.md): the strip drops event + area bits -- except on an IDALL the engine's
    ground query skips outright, where the area IS the physics (stripped, a skipped bank becomes ground)."""
    from ff9mapkit.world import placement as P
    assert P.ground_query_skips(4088.0) and P.ground_query_skips(2040) and P.ground_query_skips(4078.0)
    assert not P.ground_query_skips(encode_id(topograph=62))
    for raw in (4088.0, 2040.0, 4078.0):
        assert IN._strip_dispatch(raw) == raw
    assert IN._strip_dispatch(MASSIF_DONOR) == MASSIF                     # entrance + camera bits still go
    gate = P.skip_parity_gate([(4088.0, 4088.0), (4088.0, float(encode_id(topograph=62))), (MASSIF_DONOR, MASSIF)],
                              label="t")
    assert gate["checked"] == 3 and gate["flipped"] == 1 and not gate["ok"]


def _bank_pyramid_donor():
    """The rock pyramid with ONE face a skipped stream-bank IDALL (carried with rock_topos=(49, 62)); the first
    face stays rock, so the carry's peak probe grounds (a skipped tri is no ground: a MISS there is the engine's)."""
    c00, c10, c11, c01, top = ((20.0, 0.0, -28.0), (28.0, 0.0, -28.0), (28.0, 0.0, -20.0), (20.0, 0.0, -20.0),
                               (24.0, 4.0, -24.0))
    ids = (MASSIF_DONOR, MASSIF_DONOR, MASSIF_DONOR, BANK_SKIP)
    tris = [((a, b, top), i, _MAIN_U) for (a, b), i in zip(((c10, c00), (c11, c10), (c01, c11), (c00, c01)), ids)]
    return _bm(tris, name="Block[0][0] Terrain", x=0, y=0)


def _pyramid_with_floor(floor_topo, cx=24.0, cz=-24.0, half=4.0):
    """The rock pyramid plus one notch-floor tri of ``floor_topo`` hung off its north base edge."""
    pyr = _pyramid_donor(cx=cx, cz=cz, half=half)
    c00, c10 = (cx - half, 0.0, cz - half), (cx + half, 0.0, cz - half)
    floor = ((c00, c10, (cx, 0.5, cz - half - 3.0)), float(encode_id(topograph=floor_topo)), _MAIN_U)
    base = [((tuple(pyr.verts[3 * t]), tuple(pyr.verts[3 * t + 1]), tuple(pyr.verts[3 * t + 2])), MASSIF_DONOR, _MAIN_U)
            for t in range(len(pyr.verts) // 3)]
    return _bm(base + [floor], name="Block[0][0] Terrain", x=0, y=0)


def test_mountain_blob_alcove_floor_takes_its_declared_topographs(monkeypatch):
    """THE INLET FLOOR (mountaindonors/INLET.md): an alcove spec's optional 4th element names the floor topographs.
    The default stays grass (Uaho's), so a snow floor rides only when the spec declares snow."""
    box = ((20.0, 28.0), (-31.0, -26.0), -0.5)                    # round the floor tri, block (0,0)'s local frame
    rock = frozenset({49})
    _patch_donor(monkeypatch, _pyramid_with_floor(27))
    snow = IN._mountain_blob([(0, 0)], rock_topos=rock, alcove_box=box + ((27,),), log=lambda *a: None)
    assert len(snow["blob"]) == 5 and sorted(snow["dtopo"][t] for t in snow["blob"]) == [27, 49, 49, 49, 49]
    # break it: the 3-element (grass) spec must leave a snow floor behind
    bare = IN._mountain_blob([(0, 0)], rock_topos=rock, alcove_box=box, log=lambda *a: None)
    assert len(bare["blob"]) == 4
    # and the default still carries a grass floor exactly as before
    _patch_donor(monkeypatch, _pyramid_with_floor(0))
    grass = IN._mountain_blob([(0, 0)], rock_topos=rock, alcove_box=box, log=lambda *a: None)
    assert len(grass["blob"]) == 5


def test_plug_chart_gate_accepts_the_painted_band_or_the_donors_own_rock():
    """A plug passes inside the July grass band or inside its donor's own rock band (snow rock is painted at
    cols -1..3 rows 1..5), and is refused outside both -- the gate must still be able to fail."""
    snow_rock = [(c, r) for c in range(-1, 4) for r in range(1, 6)]
    assert IN._plug_chart_ok([6, 7], [9, 10, 11])                         # Uaho's plugs, no donor band needed
    assert IN._plug_chart_ok([6, 7], [9, 10, 11], snow_rock)
    assert IN._plug_chart_ok([2, 3], [4, 5], snow_rock)                   # comp9's plug in its own snow rock
    assert not IN._plug_chart_ok([2, 3], [4, 5])                          # ... which the grass band alone refuses
    assert not IN._plug_chart_ok([2, 3], [8, 9], snow_rock)               # outside both: refused
    assert not IN._plug_chart_ok([11, 12], [9, 10], snow_rock)


def test_atlas_gate_refuses_a_white_gutter_texel(monkeypatch, tmp_path):
    """THE GUTTER RULE (snowmassif/NOTES.md, round 21): the Moguri atlas splits its painted regions with 1-texel
    pure-white lines; a new tri sampling one renders a white sliver. The gate refused only transparent-and-dark
    texels, so comp9's plug passed it. A 64x64 fake atlas, grey with one white band: a tri across the band is
    refused by name, the same tri moved off it passes (the rule must not fire on painted texels)."""
    from PIL import Image
    from ff9mapkit import config
    tex = tmp_path / "MoguriMain" / "StreamingAssets" / "assets" / "resources" / "worldmap" / "textures"
    tex.mkdir(parents=True)
    im = Image.new("RGBA", (64, 64), (150, 166, 179, 255))
    for x in range(64):
        for y in range(30, 35):                                         # v ~0.46-0.53, a band as thick for its
            im.putpixel((x, y), (255, 255, 255, 255))                   # sampler as Moguri's ~11-texel line
    im.save(tex / "res(1_24)_terrain.png")
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)

    def tri(v0):
        return (((0.0, 0.0, 0.0, 0.30, v0, 0, 1, 0), (1.0, 0.0, 0.0, 0.40, v0, 0, 1, 0),
                 (0.0, 0.0, 1.0, 0.35, v0 + 0.06, 0, 1, 0)), MASSIF, "plug")
    with pytest.raises(ValueError, match="white gutter"):
        IN._atlas_gate_mountain([tri(0.46)], log=lambda *a: None)       # spans v 0.46-0.52 across the row
    IN._atlas_gate_mountain([tri(0.20)], log=lambda *a: None)           # painted texels only: passes
    # break it: the pre-round-21 gate (transparent AND dark only) lets the gutter tri through
    with monkeypatch.context() as mp:
        mp.setattr(IN, "ATLAS_GUTTER_WHITE", 256)
        IN._atlas_gate_mountain([tri(0.46)], log=lambda *a: None)



def _lean(ny_target, x0=0.0):
    """A tri whose unit normal's y is ny_target (a wall leaning past vertical when negative), wound as the gate reads."""
    import math as _m
    s_ = _m.sqrt(max(0.0, 1.0 - ny_target * ny_target))
    # edges (1, 0, 0) and (0, s_, -ny) span it; their cross product is (0, ny, s_), a unit normal with y = ny
    a = (x0, 0.0, 0.0)
    b = (x0 + 1.0, 0.0, 0.0)
    c = (x0, s_, -ny_target)
    return a, b, c


def test_down_gate_keeps_only_stock_near_vertical_down_faces():
    """STEP.md round 2 (D2): the mountain gate keeps a verbatim donor tri that faced down at home by a hair and still
    does as carried; everything else that faces down still counts -- a carve-made flip, a steep stock overhang, a
    tri the carry flipped (up at home), and a near-vertical stock tri the carry steepened past the line."""
    assert abs(IN._tri_ny(*_lean(-0.007)) + 0.007) < 1e-9 and abs(IN._tri_ny(*_lean(0.5)) - 0.5) < 1e-9
    home = {0: _lean(-0.007, 0), 1: _lean(-0.30, 10), 2: _lean(0.004, 20), 3: _lean(-0.010, 30)}
    dV = np.array([p for t in range(4) for p in home[t]])
    dtri = [[3 * t, 3 * t + 1, 3 * t + 2] for t in range(4)]
    carried = {0: home[0], 1: home[1], 2: _lean(-0.004, 20), 3: _lean(-0.050, 30)}
    keys = IN._stock_down_keys([0, 1, 2, 3], dV, dtri, carried)
    # the near-vertical stock faces (0 and 3) are keyed; the steep overhang (1) and the up-at-home tri (2) are not
    assert sorted(keys.values()) == [pytest.approx(-0.010), pytest.approx(-0.007)]

    def par(ps, fam="mountain"):
        return (tuple((*p, 0.0, 0.0, 0.0, 1.0, 0.0) for p in ps), MASSIF, fam)
    lines = []
    down, kept = IN._count_down([par(carried[0])], keys, log=lines.append)
    assert (down, kept) == (0, 1) and "home ny -0.0070" in lines[0]            # stock wall: kept, by name
    assert IN._count_down([par(carried[1])], keys) == (1, 0)                   # a steep stock overhang still counts
    assert IN._count_down([par(carried[2])], keys) == (1, 0)                   # up at home, flipped by the carry
    assert IN._count_down([par(carried[3])], keys) == (1, 0)                   # near-vertical home, steepened
    assert IN._count_down([par(carried[0], "zip")], keys) == (1, 0)            # a zip tri is never stock
    assert IN._count_down([par(_lean(0.9))], keys) == (0, 0)                   # up-facing: nothing to count
    # break it: with no stock keys the old gate's count comes back
    assert IN._count_down([par(carried[0])], {}) == (1, 0)


# comp9 (a snow massif) with its inlet floor -- mountaindonors/INLET.md; the round-21 lab's spec
COMP9_BLOCKS = [(8, 0), (8, 1), (9, 0), (9, 1), (10, 0)]
COMP9_INLET = ((65.0, 77.5), (-100.0, -79.5), 3.0, (27,))


def test_carve_mountain_keeps_skipped_bank_idalls_and_the_gate_refuses_a_strip(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _bank_pyramid_donor())
    res = _carve_pyramid(tmp_path, rock_topos=(49, 62))
    bm = res["changed"][(0, 0)]
    carried = [t4[0] for t4 in bm.chan_arrays[CH_TAN] if t4[0] == BANK_SKIP]
    assert len(carried) == 3 and res["report"]["skip_parity"] == {"checked": 4, "flipped": 0}
    assert sum(1 for t4 in bm.chan_arrays[CH_TAN] if t4[0] == MASSIF) == 3 * 3        # the rock still stripped
    # break it: the old strip (area -> 0 on every tri) must be refused by the gate, by name
    from ff9mapkit.world.extract import decode_id
    monkeypatch.setattr(IN, "_strip_dispatch", lambda f: float(encode_id(topograph=decode_id(int(f))["topograph"])))
    with pytest.raises(ValueError, match="ground-query visibility of 1 donor tri"):
        _carve_pyramid(tmp_path, rock_topos=(49, 62))


def test_cli_world_mountain_passes_rock_height_and_rot(monkeypatch, capsys):
    from ff9mapkit import cli
    seen = {}

    def fake_carve(soup, **kw):
        seen.update(kw)
        return {"center": (0.0, 0.0), "changed": {}, "changed_parts": {}, "donor_ref": (0, 0),
                "report": {"blocks": [[3, 3]], "rot_deg": 0, "blob_tris": 4, "plugs": 0, "dropped": 0,
                           "zip_tris": 0, "peak_y": 9.2, "rock_rigid": 0.0, "apron_slope": 0.0, "teleport": (0, 0),
                           "rock_height": {"scale": 1.5, "pinned": 4, "free": 1, "rise_max": 2.0}}}
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: object())
    monkeypatch.setattr(IN, "carve_mountain", fake_carve)
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    args = cli.build_parser().parse_args(["world-mountain", "--mod-folder", "m", "--center", "0,0",
                                          "--rock-height", "1.5", "--rot", "30", "--spread", "1.25", "--dry-run"])
    assert cli._cmd_world_mountain(args) == 0
    assert seen["rock_height"] == 1.5 and seen["rot_deg"] == 30.0 and seen["spread"] == 1.25
    assert "rock height x1.5: 1 rock positions stretched about 4 pinned" in capsys.readouterr().out
    dflt = cli.build_parser().parse_args(["world-mountain", "--mod-folder", "m", "--center", "0,0"])
    assert dflt.rock_height == 1.0 and dflt.rot is None and dflt.spread == 1.0


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


def test_carve_forest_zip_welds_bit_for_bit_to_the_kept_grass(monkeypatch, tmp_path):
    """THE EXACT-WELD LAW in the forest carve (the same zip pattern as the mountain's): on ground whose heights
    are not round, every emitted position must be one float triple."""
    _patch_donor(monkeypatch, _canopy_donor())
    res = IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid(y=3.21371)}), center=(26.0, -26.0),
                          donor=(15, 15), game=tmp_path, log=lambda *a: None)
    floats = defaultdict(set)
    for p in res["changed"][(0, 0)].chan_arrays[CH_POS]:
        floats[IN.kk3(p)].add(tuple(p))
    split = {k: v for k, v in floats.items() if len(v) > 1}
    assert not split, f"{len(split)} welds hold two floats, e.g. {next(iter(split.items()))}"


def _canopy_dome(x0=8.0, z0=-8.0, n=5, cell=4.0, top=1.0):
    """:func:`_canopy_donor` with relief: every inner vertex raised ``top`` (a low plateau,
    rim at 0), so a plan map that touched heights would show."""
    def y(i, j):
        return top if 0 < i < n and 0 < j < n else 0.0
    tris = []
    for i in range(n):
        for j in range(n):
            xa, xb = x0 + i * cell, x0 + (i + 1) * cell
            za, zb = z0 - j * cell, z0 - (j + 1) * cell
            a, b, c, d = (xa, y(i, j), za), (xb, y(i + 1, j), za), (xa, y(i, j + 1), zb), (xb, y(i + 1, j + 1), zb)
            tris.append(((a, b, c), FOREST, 0.5))
            tris.append(((b, d, c), FOREST, 0.5))
    return _bm(tris, name="Block[15][15] Terrain", x=15, y=15)


def _canopy_pts(res):
    """The carried canopy's corners (world frame, the one-block bench), in emitted order."""
    bm = res["changed"][(0, 0)]
    pos, tan = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
    return [tuple(pos[i]) for t in bm.tris for i in t if tan[t[0]][0] == FOREST]


def test_carve_forest_spread_scales_the_canopy_in_plan_and_keeps_its_heights(monkeypatch, tmp_path):
    """--spread (terrain study X3): every canopy corner lands at centre + s x (donor - donor centre) in plan, at
    the height the verbatim carry gives it; THE RIM GRAIN splits each 5u rim edge in two (the donor's are 4u), its
    midpoints on the rim at the rim's height; the zip still welds and every gate runs."""
    _patch_donor(monkeypatch, _canopy_dome())
    cut, rep = {}, {}
    for s in (1.0, 1.25):
        res = IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                              donor=(15, 15), game=tmp_path, spread=s, log=lambda *a: None)
        assert res["report"]["spread"] == s
        cut[s], rep[s] = _canopy_pts(res), res["report"]
    one, wide = cut[1.0], cut[1.25]
    assert len(one) == 150 and rep[1.0]["rim_splits"] == 0
    assert rep[1.25]["rim_splits"] == 20 and len(wide) == 150 + 20 * 3          # one more tri per split edge
    # the donor carpet spans x 8..28, z -8..-28 of block (15,15): its centre (18, -18) lands on (26, -26)
    height_at = {(round(p[0] - 26.0, 6), round(p[2] + 26.0, 6)): p[1] for p in one}
    mids = set()
    for q in wide:
        k = (round((q[0] - 26.0) / 1.25, 6), round((q[2] + 26.0) / 1.25, 6))
        if k in height_at:
            assert q[1] == height_at[k]                              # heights: the verbatim carry's
        else:                                                        # a rim midpoint: on the rim, at its height
            assert max(abs(k[0]), abs(k[1])) == pytest.approx(10.0) and q[1] == pytest.approx(3.2)
            mids.add(k)
    assert len(mids) == 20
    xs = [p[0] for p in wide]
    assert min(xs) == pytest.approx(13.5) and max(xs) == pytest.approx(38.5)   # 20u -> 25u wide
    assert max(p[1] for p in wide) == pytest.approx(3.2 + 1.0)                   # the plateau still 1u up


def test_carve_forest_walk_in_gate_samples_through_the_grid_index(monkeypatch, tmp_path):
    """The walk-in gate places ~49 samples per 0.5u rim station; each goes through placement's
    grid index (studies/overworld-editor/PLAN.md habit 5; measured x54-x61 on the live Ring
    island), and the index is a pure accelerator: the carve is byte-identical to the scan."""
    from ff9mapkit.world import placement as P
    _patch_donor(monkeypatch, _canopy_dome())
    real_gate, real_place = IN._perimeter_walk_in_gate, P.place
    in_gate, indexed = [False], []

    def gate(*a, **k):
        in_gate[0] = True
        try:
            return real_gate(*a, **k)
        finally:
            in_gate[0] = False

    def place(ml, x, z, *a, **k):
        if in_gate[0]:
            indexed.append(k.get("index") is not None)
        return real_place(ml, x, z, *a, **k)
    monkeypatch.setattr(IN, "_perimeter_walk_in_gate", gate)
    monkeypatch.setattr(P, "place", place)

    def carve():
        res = IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                              donor=(15, 15), game=tmp_path, spread=1.25, log=lambda *a: None)
        return {b: M.ff9mesh_bytes(bm) for b, bm in res["changed"].items()}
    fast = carve()
    assert len(indexed) > 1000 and all(indexed)
    indexed.clear()
    monkeypatch.setattr(P, "build_meshlist_index", lambda ml: None)   # the old linear scan
    assert carve() == fast and indexed and not any(indexed)


def test_carve_forest_rot_turns_the_canopy_and_identity_is_byte_exact(monkeypatch, tmp_path):
    """--rot: 90 is the exact coordinate swap (dx, dz) -> (dz, -dx), any other angle the same turn by cos/sin;
    spread 1 + rot 0 (or 360) is the verbatim carry byte for byte."""
    _patch_donor(monkeypatch, _canopy_dome(z0=-10.0, n=5))      # off-square about the pivot, so a turn shows

    def carve(**kw):
        return IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                               donor=(15, 15), game=tmp_path, log=lambda *a: None, **kw)
    base = carve()
    for kw in ({"spread": 1.0, "rot_deg": 0}, {"rot_deg": 360}, {"rot_deg": -720.0}):
        same = carve(**kw)
        bm, bm0 = same["changed"][(0, 0)], base["changed"][(0, 0)]
        assert bm.chan_arrays == bm0.chan_arrays and bm.tris == bm0.tris, kw
    q90 = carve(rot_deg=90)
    assert q90["report"]["rot_deg"] == 90
    plan0 = sorted({(p[0] - 26.0, p[2] + 26.0) for p in _canopy_pts(base)})
    plan90 = {(p[0] - 26.0, p[2] + 26.0) for p in _canopy_pts(q90)}
    assert plan90 == {(dz, -dx) for dx, dz in plan0}                 # exact floats: the swap, not cos/sin
    q30 = carve(rot_deg=30)
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    want = sorted((round(c * dx + s * dz, 6), round(-s * dx + c * dz, 6)) for dx, dz in plan0)
    got = sorted({(round(p[0] - 26.0, 6), round(p[2] + 26.0, 6)) for p in _canopy_pts(q30)})
    assert got == sorted(set(want))
    assert sorted(p[1] for p in _canopy_pts(q30)) == sorted(p[1] for p in _canopy_pts(base))


def _canopy_plateau(n=5, cell=4.0, top=2.0, nudge=-0.02):
    """A canopy blob with stock's anatomy: a flat top ``top`` up on vertical curtain walls (the rim is the walls'
    base), one top corner (NE, over (28, -8)) set ``nudge`` off its base in x -- stock (15,15)'s HAIRLINE CURTAIN."""
    x0, z0 = 8.0, -8.0
    corner = (x0 + n * cell, z0)

    def tp(x, z):
        return (x + (nudge if (x, z) == corner else 0.0), top, z)
    tris = []
    for i in range(n):
        for j in range(n):
            xa, xb = x0 + i * cell, x0 + (i + 1) * cell
            za, zb = z0 - j * cell, z0 - (j + 1) * cell
            tris.append(((tp(xa, za), tp(xb, za), tp(xa, zb)), FOREST, 0.5))
            tris.append(((tp(xb, za), tp(xb, zb), tp(xa, zb)), FOREST, 0.5))
    ring = [(x0 + k * cell, z0) for k in range(n)] + [(x0 + n * cell, z0 - k * cell) for k in range(n)] + \
           [(x0 + n * cell - k * cell, z0 - n * cell) for k in range(n)] + [(x0, z0 - n * cell + k * cell) for k in range(n)]
    cx, cz = x0 + n * cell / 2, z0 - n * cell / 2
    for k in range(len(ring)):
        (px, pz), (qx, qz) = ring[k], ring[(k + 1) % len(ring)]
        a, b, c, d = (px, 0.0, pz), (qx, 0.0, qz), tp(qx, qz), tp(px, pz)
        out = ((px + qx) / 2 - cx, (pz + qz) / 2 - cz)
        for t in ((a, b, c), (a, c, d)):
            u = [t[1][m] - t[0][m] for m in range(3)]
            v = [t[2][m] - t[0][m] for m in range(3)]
            nx, nz = u[1] * v[2] - u[2] * v[1], u[0] * v[1] - u[1] * v[0]
            tris.append(((t if nx * out[0] + nz * out[1] > 0 else (t[0], t[2], t[1])), FOREST, 0.5))
    return _bm(tris, name="Block[15][15] Terrain", x=15, y=15)


def test_carve_forest_closes_the_hairline_curtain_only_when_mapped(monkeypatch, tmp_path):
    """THE HAIRLINE CURTAIN: a curtain's top corner 0.02u off its base stays as the donor has it in the verbatim
    carry (byte for byte), and is set on its base in plan once the canopy is turned or spread."""
    _patch_donor(monkeypatch, _canopy_plateau())

    def carve(**kw):
        return IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                               donor=(15, 15), game=tmp_path, log=lambda *a: None, **kw)

    def ne(res, base):
        """The NE corner's top and base plan points (the base is the rim corner at ``base``)."""
        tops = {(p[0], p[2]) for p in _canopy_pts(res) if p[1] > 4.0}
        bx, bz = base
        top = min(tops, key=lambda q: (q[0] - bx) ** 2 + (q[1] - bz) ** 2)
        return top, (bx, bz)
    v = carve()
    assert v["report"]["hairlines"] == 0
    top, base = ne(v, (36.0, -16.0))                                  # (28, -8) of the donor lands on (36, -16)
    assert top[0] - base[0] == pytest.approx(-0.02) and top[1] == base[1]     # the donor's hairline, kept
    q = carve(rot_deg=90)
    assert q["report"]["hairlines"] == 1
    top, base = ne(q, (36.0, -36.0))                                  # (dx, dz) = (10, 10) turns to (10, -10)
    assert top == base                                                 # closed: over its base exactly
    w = carve(spread=1.25)
    assert w["report"]["hairlines"] == 1
    top, base = ne(w, (38.5, -13.5))
    assert top == base


def test_zip_dp_ny_floor_routes_round_a_sliver():
    """The DP strip with a floor: a rim node on the line of a hole edge (x 15.98 against the hole's x 16) makes the
    shortest strip take a sliver (ny 0.05); with the forest's floor it routes round it. No floor = the mountain's
    strip, unchanged."""
    import numpy as np
    n, step = 4, 4.0
    hole = [(k * step, 0.0, 0.0) for k in range(n)] + [(16.0, 0.0, k * step) for k in range(n)] + \
           [(16.0 - k * step, 0.0, 16.0) for k in range(n)] + [(0.0, 0.0, 16.0 - k * step) for k in range(n)]
    rim = [(4.0, 0.4, 4.0), (12.0, 0.4, 4.0), (15.98, 0.4, 6.0), (12.0, 0.4, 12.0), (4.0, 0.4, 12.0)]
    hk, rk = [IN.kk3(p) for p in hole], [IN.kk3(p) for p in rim]
    hf, rf = dict(zip(hk, hole)), dict(zip(rk, rim))

    def min_ny(tris):
        out = 1.0
        for t in tris:
            a, b, c = (np.asarray(p) for p in t)
            nn = np.cross(b - a, c - a)
            out = min(out, abs(nn[1]) / np.linalg.norm(nn))
        return out
    _, _, plain = IN._zip_dp(hk, rk, lambda k: rf[k], hf)
    _, _, floored = IN._zip_dp(hk, rk, lambda k: rf[k], hf, ny_floor=IN.FOREST_ZIP_NY_FLOOR)
    assert len(plain) == len(floored) == len(hole) + len(rim)
    assert min_ny(plain) < 0.1 and min_ny(floored) > 0.9


def _carpet(x0, z0, nx, nz, cell=4.0, topo=FOREST):
    """``nx`` x ``nz`` flat quad cells of ``topo`` tris from local (x0, z0), +x and -z (the (x, y, z) corner list)."""
    tris = []
    for i in range(nx):
        for j in range(nz):
            xa, xb = x0 + i * cell, x0 + (i + 1) * cell
            za, zb = z0 - j * cell, z0 - (j + 1) * cell
            tris.append((((xa, 0.0, za), (xb, 0.0, za), (xa, 0.0, zb)), topo, 0.5))
            tris.append((((xb, 0.0, za), (xb, 0.0, zb), (xa, 0.0, zb)), topo, 0.5))
    return tris


def test_forest_donor_gathers_a_blob_across_a_block_border(monkeypatch, tmp_path):
    """A stock canopy may cross a block border ((3,12)-(3,13), (19,8)-(19,9), ...): the donor reader gathers it whole
    from the neighbouring block, its border corners welded by position, and the carve carries every tri."""
    left = _bm(_carpet(52.0, -8.0, 3, 5), name="Block[15][15] Terrain", x=15, y=15)     # x 52..64 in (15,15)
    right = _bm(_carpet(0.0, -8.0, 2, 5), name="Block[16][15] Terrain", x=16, y=15)     # x 64..72 in (16,15)
    _patch_donor(monkeypatch, {(15, 15): left, (16, 15): right})
    V, _uv, _n, _t, tris, blob, blocks = IN._forest_donor((15, 15), game=tmp_path)
    assert blocks == [(15, 15), (16, 15)] and len(blob) == 50
    xs = [V[i][0] for t in blob for i in tris[t]]
    assert min(xs) == 960.0 + 52.0 and max(xs) == 1024.0 + 8.0
    logs = []
    res = IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0), donor=(15, 15),
                          game=tmp_path, log=logs.append)
    assert res["report"]["blob_tris"] == 50
    assert any("spans blocks [(15, 15), (16, 15)]" in m for m in logs)


def test_forest_donor_takes_the_grass_bounded_blob_and_refuses_one_that_meets_rock(monkeypatch, tmp_path):
    """A block holding a bigger blob that meets rock and a smaller one bounded by grass gives the grass-bounded one
    ((18,15)'s case in the census); a block whose only blob meets rock refuses -- carried alone, the rock contact
    would be an open, unwalled edge."""
    small = _carpet(8.0, -8.0, 2, 2) + _carpet(4.0, -4.0, 1, 1, topo=GRASS)              # 8 canopy tris
    big = _carpet(30.0, -30.0, 4, 4)                                                       # 32 canopy tris
    rock = [(((46.0, 0.0, -30.0), (50.0, 0.0, -30.0), (46.0, 0.0, -34.0)), ROCK, 0.5)]   # across big's east rim
    _patch_donor(monkeypatch, {(15, 15): _bm(small + big + rock, name="Block[15][15] Terrain", x=15, y=15)})
    _V, _uv, _n, _t, _tris, blob, blocks = IN._forest_donor((15, 15), game=tmp_path)
    assert len(blob) == 8 and blocks == [(15, 15)]
    _patch_donor(monkeypatch, {(15, 15): _bm(big + rock, name="Block[15][15] Terrain", x=15, y=15)})
    with pytest.raises(ValueError, match="cannot be carried alone"):
        IN._forest_donor((15, 15), game=tmp_path)


def test_forest_plan_normals_take_the_inverse_transpose():
    """A plane y = 0.75 x stretched x2 in plan is y = 0.375 x: its normal leans half as far, at unit length."""
    import numpy as np
    n0 = [-0.6, 0.8, 0.0]                                         # unit normal of y = 0.75 x
    pts, nrm = IN._forest_plan(np.array([[1.0, 0.75, 0.0], [3.0, 2.25, 2.0]]), [n0, n0], (0.0, 0.0),
                               spread=2.0, rot_deg=None)
    assert pts.tolist() == [[2.0, 0.75, 0.0], [6.0, 2.25, 4.0]]
    want = np.array([-0.375, 1.0, 0.0]) / math.hypot(0.375, 1.0)
    assert np.allclose(nrm[0], want) and math.isclose(float(np.linalg.norm(nrm[0])), 1.0)
    _, nrm90 = IN._forest_plan(np.zeros((1, 3)), [n0], (0.0, 0.0), spread=1.0, rot_deg=90)
    assert nrm90 == [[0.0, 0.8, 0.6]]                             # (nx, nz) -> (nz, -nx), exact


def test_carve_forest_refuses_a_spread_outside_its_range(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _canopy_dome())
    for bad in (0.99, IN.FOREST_SPREAD_MAX + 0.01, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="spread"):
            IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                            donor=(15, 15), game=tmp_path, spread=bad, log=lambda *a: None)
    with pytest.raises(ValueError, match="finite angle"):
        IN.carve_forest(IN.soup_from_blocks({(0, 0): _mains_grid()}), center=(26.0, -26.0),
                        donor=(15, 15), game=tmp_path, rot_deg=float("nan"), log=lambda *a: None)


def test_cli_world_forest_passes_spread_and_rot(monkeypatch, capsys):
    from ff9mapkit import cli
    seen = {}

    def fake_carve(soup, **kw):
        seen.update(kw)
        return {"center": (0.0, 0.0), "changed": {},
                "report": {"blob_tris": 132, "dropped": 9, "zip_tris": 60, "wall_rise": 1.8, "zip_rise": 0.8,
                           "spread": kw["spread"], "rot_deg": kw["rot_deg"] or 0}}
    monkeypatch.setattr(IN, "read_deployed_blocks", lambda *a, **k: {})
    monkeypatch.setattr(IN, "soup_from_blocks", lambda blocks: object())
    monkeypatch.setattr(IN, "carve_forest", fake_carve)
    monkeypatch.setattr(IN, "census_gate", lambda *a, **k: None)
    args = cli.build_parser().parse_args(["world-forest", "--mod-folder", "m", "--center", "0,0",
                                          "--spread", "1.25", "--rot", "30", "--dry-run"])
    assert cli._cmd_world_forest(args) == 0
    assert seen["spread"] == 1.25 and seen["rot_deg"] == 30.0
    assert "the canopy carry (spread x1.25, rot 30deg) at world" in capsys.readouterr().out
    dflt = cli.build_parser().parse_args(["world-forest", "--mod-folder", "m", "--center", "0,0", "--dry-run"])
    assert dflt.spread == 1.0 and dflt.rot is None
    assert cli._cmd_world_forest(dflt) == 0
    assert "the canopy carry at world" in capsys.readouterr().out


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
# are a standing regression net, not a proven-once-by-hand result.
#
# HERMETIC TO THE MOD FOLDERS (2026-10-12). Both nets used to byte-compare against the
# deployed FF9CustomMap-world bench files; other sessions redeployed those blocks in July,
# both nets SKIPPED for ~3 months, and carve_mountain took two unguarded default-path UV
# passes in that window (R5b 009884a4, R5c 6b1b1ad3). Now every INPUT is rebuilt in-test
# (the mints are kit code; the carves read only the stock donor through UnityPy) and every
# expected output is a SHA-256 pin -- a one-way digest, zero Square-Enix bytes
# (docs/PROVENANCE.md: "build goldens are hashes too"). The pins were re-derived by running
# the historical package snapshots (``git archive`` of e8ca8e0^ / 10b92a1d / fac2a744 /
# b286a87c) on the reconstructed inputs; that reconstruction reproduces the recorded July
# measurements exactly (the strip's 447 tangent.x entries, the swap's UV-only diff).
# The only skip left is a machine with no install or no UnityPy, and the reason names which.

UAHO_SEED_PT = (160.0, -1246.0)                             # the study's own scan seed
UAHO_MINT = dict(center=UAHO_SEED_PT, base_radius=31.0, seed=42.0, lobes=1, n_patches=0)
UAHO_DENTS = ((141.9, -1219.5), (143.6, -1263.8))           # e8ca8e0's two re-triangulated dents
#: the bench the July carry transformed: the r31 seed-42 mint BEFORE e8ca8e0's ring-edge
#: recovery (its one-tri hole intact, so the carve's mint-hole patch runs) -- Block[2][19]
UAHO_PRISTINE_SHA = "e74eb4ecc6ffa82309eb30b8699d77928751cf63e19e20ea7ccfc92bd9c501a2"
#: the in-game-approved July bench: the DONOR-DISPATCH STRIP re-carve ("zoom is gone",
#: 2026-07-15) = today's carve with R5b/R5c switched off
UAHO_JULY_SHA = "ad2da91874dd4c3665c187d22bb81d6c1152139dbdf3f31135ce386da85f877c"
#: today's default carve = July + R5b THE LAWN-LINE SNAP (3 uv.v) + R5c THE FRINGE-SEAM
#: UNIFY (8 uv.v), studies/overworld-topography/west-seam-continent/UAHO-*-BENCH.md
#: + THE EXACT-WELD LAW (terrain round 16): the zip's grass corners on the kept grass's own
#: floats, not the hole ring's rounded keys (87 pos.y <= 5e-4u, their re-smoothed normals)
UAHO_CARVE_SHA = "f9f16a2d4e803ecfb7773769d5ae0e3850ca8d095001e77bc839b4bf903ed41b"

ISLAND_E_BLOCKS = [(4, 17), (5, 17), (4, 18), (5, 18), (6, 18)]
ISLAND_E_FOREST = (312, -1140)          # recovered from the July deploy's canopy (topo 37)
ISLAND_E_HILL = (348, -1184)
#: today's island E, per block: the July carve after THE DIVERSITY POLICY swap (b286a87c)
ISLAND_E_SHA = {
    (4, 17): "9d7e5dd77ba793057ef3ed9910368156b6d6461aef5a3d3b2b57abd493b074a6",
    (5, 17): "af359a0964f84cad7cf529901d6ddae6f539d48cc829951802f2e8a1ad93a434",
    (4, 18): "96a3efd8ac0e405b58b90071cf2a76758b49d6b78c87cd4ad197b9731c7d2362",
    (5, 18): "9f72ed31f78ccc39c1167eccd7ce1c0327ecb5f6420655801850e81ce2cd2df3",
    (6, 18): "ec91596f9f1adadf44022ff01c7b7e85fcf0a9d24a2ebbb1728d5c27c7077339",
}
#: the in-game-proven July island E (fac2a744) WITHOUT its UVs (see _geom_sha): the swap
#: moved only fallback-ring zip UVs, so this half of the July bytes must still hold verbatim
ISLAND_E_JULY_GEOM_SHA = {
    (4, 17): "3ed5502dfb96e657437d2d0e85f347fb44e119a5bc4405d0bbf726d8702c22f7",
    (5, 17): "8e05c70db01d849132ca5b308e845294fcc3c9c7f9325d704c6bbe3e4d4ab3e1",
    (4, 18): "c0c43c203a50032ad046a6dca5083358f8278e6a571aaf915ebc5230ee295123",
    (5, 18): "465c57a50d870ee2b9f3f6a00a8ec2bf6173944798b47539b02eefe80dd6255e",
    (6, 18): "d4479ba5bf16b015dafae388d648ddb0fd4031f6732ab1ca10f8dc92bb8c09d8",
}


def _game_skip_reason():
    """None when the identity nets can run, else WHICH prerequisite is missing."""
    try:
        import UnityPy  # noqa: F401
    except ImportError:
        return "UnityPy is not installed (the carves read the stock donor block through it)"
    try:
        from ff9mapkit import config
        gp = config.find_game_path(None)
    except Exception as e:  # noqa: BLE001 -- ConfigError, or a broken user config
        return f"no FF9 install resolves ({type(e).__name__}: {e})"
    if not (gp / "StreamingAssets").is_dir():
        return f"the FF9 install at {gp} has no StreamingAssets"
    return None


_GAME_SKIP = _game_skip_reason()
needs_game = pytest.mark.skipif(_GAME_SKIP is not None, reason=f"identity net: {_GAME_SKIP}")


def _sha(path) -> str:
    import hashlib
    from pathlib import Path
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _geom_sha(bm) -> str:
    """SHA-256 over everything but the UVs: the tri index list + POS/NRM/TAN as f32."""
    import hashlib
    h = hashlib.sha256(np.asarray(bm.tris, dtype="<i4").tobytes())
    for ch in (CH_POS, CH_NRM, CH_TAN):
        h.update(np.asarray(bm.chan_arrays[ch], dtype="<f4").tobytes())
    return h.hexdigest()


def _uaho_mint(tmp_path, monkeypatch, *, pristine, cell_lip=False):
    """The r31 seed-42 bench mint written to disk (the carve is fed DISK-READ f32 bytes --
    part of the proven identity). ``pristine`` switches e8ca8e0's ring-edge recovery off. The July
    nets run on the PRE-FIX lip (``cell_lip=False``, the mint those benches were proven on);
    ``cell_lip=True`` is today's default mint, the cell-clipped lip."""
    from ff9mapkit.world import island as I
    with monkeypatch.context() as mp:
        if pristine:
            mp.setattr(I, "_recover_ring_edges", lambda xz, tri_idx, nring: (tri_idx, 0))
        built = I.build_landmass(**UAHO_MINT, cell_lip=cell_lip)
    tag = ("pristine" if pristine else "fresh") + ("-lip" if cell_lip else "")
    return {blk: M.write_ff9mesh(bm, tmp_path / f"{tag}_{blk[0]}_{blk[1]}.ff9mesh")
            for blk, bm in built["blocks"].items()}


def _read19(path):
    return M.blockmesh_from_ff9mesh(path, disc=1, x=2, y=19, part="terrain")


def _uaho_carve(path, out):
    res = IN.carve_mountain(IN.soup_from_blocks({(2, 19): _read19(path)}), near=UAHO_SEED_PT,
                            log=lambda *a: None)
    assert sorted(res["changed"]) == [(2, 19)]
    return res, M.write_ff9mesh(res["changed"][(2, 19)], out)


def _july_welds(mp):
    """Emit the zip's grass corners as the hole ring's rounded keys, as the July carve did (THE EXACT-WELD LAW's
    seam): only this reproduces the in-game-approved July bytes."""
    mp.setattr(IN, "_weld_point", lambda key, exact: key)


def _uaho_r5_off(mp):
    """Switch R5b + R5c off: carve_mountain then runs its July path."""
    mp.setattr(IN, "_lawn_line_snap", lambda np_, *, rock_topos, log=print: (np_, {"entries": 0}))
    mp.setattr(IN, "_fringe_seam_unify",
               lambda np_, *, rock_topos, log=print: (np_, {"entries": 0}))


@needs_game
def test_carve_mountain_reproduces_the_july_uaho_bench(tmp_path, monkeypatch):
    """THE IDENTITY NET (mountain), anchored to July: the pristine bench mint the study
    transformed -> carve_mountain at the study's scan seed with R5b/R5c off -> byte-identical
    to the in-game-approved July Block[2][19] ("the cliff is great -- walkable, seams against
    the grass great", 2026-07-13; re-carved with the donor-dispatch strip, "zoom is gone",
    2026-07-15). The pristine input carries the pre-fix mint's one-tri hole, so the
    mint-hole patch runs. Ported from mountain_productize_check.py TRACK A."""
    pris = _uaho_mint(tmp_path, monkeypatch, pristine=True)[(2, 19)]
    assert _sha(pris) == UAHO_PRISTINE_SHA, (
        "the pre-e8ca8e0 r31 seed-42 mint drifted (island.build_landmass with no ring flips) -- "
        "the carve's input is no longer the July bench, so the carve cannot be judged")
    with monkeypatch.context() as mp:
        _uaho_r5_off(mp)
        _july_welds(mp)
        res, got = _uaho_carve(pris, tmp_path / "july.ff9mesh")
    assert (res["center"], res["rot"]) == ((162, -1246), 0)
    assert res["report"]["patched_holes"] == 1
    assert _sha(got) == UAHO_JULY_SHA, "carve_mountain no longer reproduces the July Uaho bench"


@needs_game
def test_carve_mountain_exact_weld_is_the_only_change_since_july(tmp_path, monkeypatch):
    """THE EXACT-WELD LAW (terrain round 16: the owner saw 1-pixel seams round a carried foot) against the July
    anchor: the July bytes emitted the zip's grass corners as the hole ring's rounded KEYS, so some welds held two
    floats; today's carve holds one float per weld, and differs from July ONLY there -- the same tris, UVs and
    tangents, positions moved in y alone by < 5e-4u, normals re-smoothed by < 1e-4."""
    pris = _uaho_mint(tmp_path, monkeypatch, pristine=True)[(2, 19)]
    with monkeypatch.context() as mp:
        _uaho_r5_off(mp)
        _july_welds(mp)
        _, july = _uaho_carve(pris, tmp_path / "july.ff9mesh")
    with monkeypatch.context() as mp:
        _uaho_r5_off(mp)
        _, now = _uaho_carve(pris, tmp_path / "now.ff9mesh")
    a, b = _read19(july), _read19(now)
    assert a.tris == b.tris
    for ch in (CH_UV, CH_TAN):
        assert np.array_equal(np.asarray(a.chan_arrays[ch], np.float32), np.asarray(b.chan_arrays[ch], np.float32))
    pa, pb = (np.asarray(m.chan_arrays[CH_POS], np.float32) for m in (a, b))
    assert np.array_equal(pa[:, [0, 2]], pb[:, [0, 2]]) and 0 < np.abs(pa[:, 1] - pb[:, 1]).max() < 5e-4
    na, nb = (np.asarray(m.chan_arrays[CH_NRM], np.float32) for m in (a, b))
    assert np.abs(na - nb).max() < 1e-4

    def split_welds(m):
        floats = defaultdict(set)
        for q in m.chan_arrays[CH_POS]:
            floats[IN.kk3(q)].add(tuple(q))
        return sum(1 for v in floats.values() if len(v) > 1)
    assert split_welds(a) > 0 and split_welds(b) == 0


@needs_game
def test_carve_mountain_default_is_july_plus_the_declared_r5_uv_passes(tmp_path, monkeypatch):
    """THE IDENTITY NET (mountain), today's default path: the same carve with R5b/R5c ON is
    pinned, and it differs from the July bytes ONLY by those passes' declared edits -- 3 + 8
    uv.v entries, nothing in POS/NRM/TAN or the tri list (both benches, UAHO-*-BENCH.md)."""
    pris = _uaho_mint(tmp_path, monkeypatch, pristine=True)[(2, 19)]
    res, got = _uaho_carve(pris, tmp_path / "now.ff9mesh")
    assert (res["report"]["lawn_snapped"], res["report"]["seam_unified"]) == (3, 8)
    with monkeypatch.context() as mp:
        _uaho_r5_off(mp)
        _, july = _uaho_carve(pris, tmp_path / "july.ff9mesh")
    a, b = _read19(july), _read19(got)
    assert _geom_sha(a) == _geom_sha(b), "the R5 passes moved more than UVs"
    ua, ub = a.chan_arrays[CH_UV], b.chan_arrays[CH_UV]
    assert len(ua) == len(ub)
    assert all(ua[i][0] == ub[i][0] for i in range(len(ua))), "an R5 pass moved a uv.u"
    assert sum(ua[i][1] != ub[i][1] for i in range(len(ua))) == 3 + 8
    assert _sha(got) == UAHO_CARVE_SHA, "carve_mountain's default Uaho bytes changed"


@needs_game
def test_carve_mountain_fresh_mint_differs_only_at_the_dents(tmp_path, monkeypatch):
    """The go-forward path (TRACK B): a FRESH world-island mint (ring-edge recovery on, so
    hole-free) carves to the same placement, patches no hole, and differs from the pristine
    carve only around the two concave-dent re-triangulations e8ca8e0 made in the MINT itself
    (both far outside the carve band); the neighbour block the mint spills into is
    untouched by the fix."""
    pris = _uaho_mint(tmp_path, monkeypatch, pristine=True)
    fresh = _uaho_mint(tmp_path, monkeypatch, pristine=False)
    assert _sha(fresh[(2, 18)]) == _sha(pris[(2, 18)])
    res_a, got_a = _uaho_carve(pris[(2, 19)], tmp_path / "a.ff9mesh")
    res_b, got_b = _uaho_carve(fresh[(2, 19)], tmp_path / "b.ff9mesh")
    assert (res_b["center"], res_b["rot"]) == (res_a["center"], res_a["rot"])
    assert res_b["report"]["patched_holes"] == 0

    def tri_set(path):
        bm = _read19(path)
        ps, us = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV]
        ns, ts = bm.chan_arrays[CH_NRM], bm.chan_arrays[CH_TAN]
        return {tuple(tuple((*ps[i], *us[i], *ns[i], ts[i][0])) for i in tri) for tri in bm.tris}

    diff = tri_set(got_a) ^ tri_set(got_b)
    assert diff, "the fresh mint should re-triangulate the dents"
    # the flips re-triangulate ~6 tris and re-smooth their corner normals, which the
    # neighbouring tris' coincident entries share -- measured 24 tris total (2026-07-15)
    assert len(diff) <= 32, f"dent diff too large ({len(diff)} tris)"
    for t in diff:
        cx = sum(p[0] for p in t) / 3 + 64.0 * 2
        cz = sum(p[2] for p in t) / 3 - 64.0 * 19
        assert any((cx - dx) ** 2 + (cz - dz) ** 2 < 6.0 ** 2 for dx, dz in UAHO_DENTS), \
            f"a fresh-mint carve differs away from the mint dents, at ({cx:.1f},{cz:.1f})"


@needs_game
def test_interior_pipeline_reproduces_island_e(tmp_path):
    """THE IDENTITY NET (forest + hill): clean seed-55 mint -> carve_forest at the July
    deploy's own canopy center -> f32 write/read-back (the deployed representation) ->
    build_hill -> all 5 island E blocks pinned. Anchored to the in-game-proven July bytes
    (2026-07-13) through ISLAND_E_JULY_GEOM_SHA: THE DIVERSITY POLICY swap (2026-07-25)
    re-picked only the fallback ring's zip UVs, so the tri lists, POS, NRM and TAN still
    match July verbatim, and block (6,18) matches it whole. Ported from
    interior_productize_check.py."""
    from ff9mapkit.world.island import build_landmass

    built = build_landmass(center=(344, -1152), base_radius=46, seed=55, lobes=3,
                           stamps="auto", cell_lip=False)              # the July input: the pre-fix lip
    res_f = IN.carve_forest(IN.soup_from_blocks(built["blocks"]), center=ISLAND_E_FOREST,
                            donor=(15, 15))
    IN.census_gate(res_f["changed"], probe=(ISLAND_E_FOREST, 37))
    assert sorted(res_f["changed"]) == sorted(ISLAND_E_BLOCKS)
    paths = {blk: M.write_ff9mesh(bm, tmp_path / f"f_{blk[0]}_{blk[1]}.ff9mesh")
             for blk, bm in res_f["changed"].items()}
    blocks2 = {blk: M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1],
                                             part="terrain")
               for blk, p in paths.items()}
    res_h = IN.build_hill(IN.soup_from_blocks(blocks2), center=ISLAND_E_HILL)
    IN.census_gate(res_h["changed"])
    assert sorted(res_h["changed"]) == [(5, 18)]
    geom_off, bytes_off = [], []
    for blk in ISLAND_E_BLOCKS:
        p = (M.write_ff9mesh(res_h["changed"][blk], tmp_path / f"h_{blk[0]}_{blk[1]}.ff9mesh")
             if blk in res_h["changed"] else paths[blk])
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=blk[0], y=blk[1], part="terrain")
        if _geom_sha(bm) != ISLAND_E_JULY_GEOM_SHA[blk]:
            geom_off.append(blk)
        if _sha(p) != ISLAND_E_SHA[blk]:
            bytes_off.append(blk)
    assert not geom_off, f"island E left the in-game-proven July geometry on {geom_off}"
    assert not bytes_off, f"island E's bytes changed on {bytes_off}"


def _world_tri_set(bm, blk):
    from ff9mapkit.world.extract import block_world_origin
    ox, oz = block_world_origin(*blk)
    P, U = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV]
    return {tuple(sorted((P[i][0] + ox, P[i][1], P[i][2] + oz, U[i][0], U[i][1]) for i in t)) for t in bm.tris}


def _off_the_lip(diff, rim, reach=6.0):
    """The tris of ``diff`` lying wholly more than ``reach`` from the island's rim."""
    rim = np.asarray(rim)
    return [t for t in diff if min(float(np.hypot(rim[:, 0] - p[0], rim[:, 1] - p[2]).min()) for p in t) > reach]


@needs_game
def test_the_carves_run_on_a_cell_lip_mint(tmp_path, monkeypatch):
    """THE CELL-CLIPPED LIP (the lip-streak fix) under the three interior verbs: today's default mint keeps the
    pre-fix interior, so world-forest carves island E's July canopy and world-mountain the Uaho massif at the same
    placement as on the pre-fix mint, census-clean, and their bytes differ from those carves ONLY at the lip (no tri
    more than 6u from the rim), and world-hill raises island E's July hill at its own centre the same way (its rock
    clearance 6.023 against RIM_CLEAR 6.0, as on the pre-fix mint)."""
    from ff9mapkit.world import island as I
    kw = dict(center=(344, -1152), base_radius=46, seed=55, lobes=3, stamps="auto")
    old, new = I.build_landmass(**kw, cell_lip=False), I.build_landmass(**kw)
    quiet = dict(log=lambda *a: None)
    f_old = IN.carve_forest(IN.soup_from_blocks(old["blocks"]), center=ISLAND_E_FOREST, donor=(15, 15), **quiet)
    f_new = IN.carve_forest(IN.soup_from_blocks(new["blocks"]), center=ISLAND_E_FOREST, donor=(15, 15), **quiet)
    IN.census_gate(f_new["changed"], probe=(ISLAND_E_FOREST, 37), **quiet)
    assert sorted(f_new["changed"]) == sorted(f_old["changed"]) == sorted(ISLAND_E_BLOCKS)
    diff = set()
    for blk in ISLAND_E_BLOCKS:
        diff |= _world_tri_set(f_old["changed"][blk], blk) ^ _world_tri_set(f_new["changed"][blk], blk)
    assert diff and _off_the_lip(diff, old["rim"]) == []
    h_old = IN.build_hill(IN.soup_from_blocks(f_old["changed"]), center=ISLAND_E_HILL, **quiet)
    h_new = IN.build_hill(IN.soup_from_blocks(f_new["changed"]), center=ISLAND_E_HILL, **quiet)
    IN.census_gate(h_new["changed"], **quiet)
    assert sorted(h_new["changed"]) == sorted(h_old["changed"]) == [(5, 18)]
    diff = _world_tri_set(h_old["changed"][(5, 18)], (5, 18)) ^ _world_tri_set(h_new["changed"][(5, 18)], (5, 18))
    assert diff and _off_the_lip(diff, old["rim"]) == []

    fresh = _uaho_mint(tmp_path, monkeypatch, pristine=False)
    lip = _uaho_mint(tmp_path, monkeypatch, pristine=False, cell_lip=True)
    res_a, got_a = _uaho_carve(fresh[(2, 19)], tmp_path / "a.ff9mesh")
    res_b, got_b = _uaho_carve(lip[(2, 19)], tmp_path / "b.ff9mesh")
    assert (res_b["center"], res_b["rot"]) == (res_a["center"], res_a["rot"])
    assert res_b["report"]["patched_holes"] == 0
    diff = _world_tri_set(_read19(got_a), (2, 19)) ^ _world_tri_set(_read19(got_b), (2, 19))
    rim = I.build_landmass(**UAHO_MINT, cell_lip=False)["rim"]
    assert diff and _off_the_lip(diff, rim) == []


# ---- the census gate's CUT sea plane (audit rec 4: the dead-gate revival) -------------------------------------------

SEA57 = float(encode_id(topograph=57))


def _sea_grid_plane(n=16, cell=4.0):
    """A synthetic full-cell Sea4 plane at y=0 (the shape ``island._sea_plane`` returns), local frame."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, 0.0, z0), (x1, 0.0, z0), (x0, 0.0, z1)), SEA57, 0.5))
            tris.append((((x1, 0.0, z0), (x1, 0.0, z1), (x0, 0.0, z1)), SEA57, 0.5))
    return _bm(tris, name="Block[0][0] Sea4")


def _grid_block_with_hole(bx, by, hole_cells, y=3.2, n=16, cell=4.0):
    """``_grid_block`` minus the 4u cells in ``hole_cells`` -- the punched-terrain fixture."""
    tris = []
    for i in range(n):
        for j in range(n):
            if (i, j) in hole_cells:
                continue
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), GRASS, _MAIN_U))
            tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), GRASS, _MAIN_U))
    return _bm(tris, name=f"Block[{bx}][{by}] Terrain", x=bx, y=by)


def test_census_gate_raises_on_a_punched_terrain_hole(monkeypatch):
    """THE DEAD-GATE REVIVAL. The gate used to census an UNCUT full-cell Sea4 the island lane
    never deploys, so a terrain hole grounded on phantom sea at y=0 and the ``MISS == 0``
    predicate was UNREACHABLE for the one class it exists to catch. Cut against the BASELINE
    terrain (the footprint the disk's Sea4 was actually cut against), a punched cell has
    nothing beneath it -> MISS -> raise. Revert the ``_cut_plane`` swap in ``census_gate``
    and this test goes red -- that is its entire point."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _sea_grid_plane())
    intact = _grid_block(0, 0)
    IN.census_gate({(0, 0): intact}, baseline={(0, 0): intact})       # control: gates clean
    for hole in ({(6, 6)}, {(6, 6), (7, 6), (6, 7), (7, 7)}):
        punched = _grid_block_with_hole(0, 0, hole)
        with pytest.raises(ValueError, match="placement MISS"):
            IN.census_gate({(0, 0): punched}, baseline={(0, 0): intact})


def test_census_gate_detects_holes_even_without_baseline(monkeypatch):
    """Fallback semantics (no baseline -> cut vs the edited bm) still detect punched holes:
    the cut drops a sea TRI only when all three corners are under land, and every
    hole-BOUNDARY sea tri's corners lie ON the remaining terrain's edges (edge-inclusive),
    so the boundary strip drops and MISSes regardless of hole size -- the complementarity
    trap ("cut-vs-current backfills what you punched") does not occur at tri granularity.
    ``baseline=`` (wired at every CLI call site) remains the DISK-truth cut: on disk the
    whole hole is void, not just its rim."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _sea_grid_plane())
    IN.census_gate({(0, 0): _grid_block(0, 0)})
    for hole in ({(6, 6)}, {(6, 6), (7, 6), (6, 7), (7, 7)}):
        with pytest.raises(ValueError, match="placement MISS"):
            IN.census_gate({(0, 0): _grid_block_with_hole(0, 0, hole)})


def test_census_gate_raises_on_stacked_walkable_sheets(monkeypatch):
    """THE LAWN-UNDER-HILL GATE (audit rec 3): a carve that leaves walkable lawn under a
    walkable carried surface must REFUSE -- first-in-buffer wins, so the player grounds
    beneath the new ground (the bench walk instrument pinned this class on a real playtest
    defect at 0.00u). Delete the stacked raise in census_gate and this goes red."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _sea_grid_plane())
    lawn = _grid_block(0, 0)                              # y=3.2 everywhere
    hill = ((16.0, 9.0, -16.0), (24.0, 9.0, -16.0), (16.0, 9.0, -24.0))
    stacked = _grid_block(0, 0, extra=[(hill, GRASS, _MAIN_U)])
    IN.census_gate({(0, 0): lawn}, baseline={(0, 0): lawn})
    with pytest.raises(ValueError, match="stacked walkable sheets"):
        IN.census_gate({(0, 0): stacked}, baseline={(0, 0): lawn})


# ---- the gates measure the CARVE, not the island (RUNG5.md "The forest after the seam rung") --------
#
# On the world-river island both relief refusals were the island's own state: the census found
# the river channel MISSing (it censused hidden blanks + a cut sea, while in game the river's
# parts cover it, and stock-inherited misses remain even under the whole deployed stack), and
# the forest's annulus gate counted an edge already open on the untouched island.

def _cell_sheet(cells, *, y, idall, name, cell=4.0):
    """Flat up-facing tris over the given 4u cells -- a deployed aux part (e.g. a River over
    a channel the Terrain leaves open)."""
    tris = []
    for i, j in sorted(cells):
        x0, x1 = i * cell, (i + 1) * cell
        z0, z1 = -j * cell, -(j + 1) * cell
        tris.append((((x0, y, z0), (x1, y, z0), (x0, y, z1)), idall, 0.5))
        tris.append((((x1, y, z0), (x1, y, z1), (x0, y, z1)), idall, 0.5))
    return _bm(tris, name=name)


# the river island in miniature: the Terrain is open over a channel cell (6,6) its River covers
# and over a cell (10,10) nothing covers (a stock-inherited miss the pristine stack already has)
_CHANNEL, _INHERITED = (6, 6), (10, 10)


def _river_island():
    terrain = _grid_block_with_hole(0, 0, {_CHANNEL, _INHERITED})
    river = _cell_sheet({_CHANNEL}, y=1.0, idall=SEA57, name="Block[0][0] River")
    return terrain, {(0, 0): {"River": river}}


def test_census_gate_stack_passes_the_islands_own_misses_and_refuses_the_carves(monkeypatch):
    """``stack=``: the census reads the deployed parts and subtracts what the pristine stack
    already misses (``world-river``'s home-miss shape). The island as it stands passes, and so
    does a carve that strands nothing new; a carve that opens a new hole still refuses. The old
    construction (hidden blanks + a re-cut sea, no stack) refuses the untouched island itself --
    the RUNG5 measurement this fixes."""
    from ff9mapkit.world import island as I
    monkeypatch.setattr(I, "_sea_plane", lambda disc, game=None: _sea_grid_plane())
    terrain, stack = _river_island()
    base = {(0, 0): terrain}
    with pytest.raises(ValueError, match="placement MISS"):        # the old gate: the island's own state
        IN.census_gate({(0, 0): terrain}, baseline=base)
    lines = []
    IN.census_gate({(0, 0): terrain}, baseline=base, stack=stack, log=lines.append)
    assert "the island's own" in lines[-1]
    bump = _grid_block_with_hole(0, 0, {_CHANNEL, _INHERITED})      # a carve elsewhere: a raised cell
    bump.chan_arrays[CH_POS][0][1] += 0.5
    IN.census_gate({(0, 0): bump}, baseline=base, stack=stack, log=lambda *a: None)
    # BREAK-IT: a hole the carve opens where the island grounded is NEW -> refuses
    punched = _grid_block_with_hole(0, 0, {_CHANNEL, _INHERITED, (3, 3)})
    with pytest.raises(ValueError, match="placement MISS"):
        IN.census_gate({(0, 0): punched}, baseline=base, stack=stack, log=lambda *a: None)
    # the stack really is read: the River grounds the channel's samples, so fewer are the island's own
    def own(stack_):
        got = []
        IN.census_gate({(0, 0): terrain}, baseline=base, stack=stack_, log=got.append)
        return int(re.search(r"\((\d+) MISS", got[-1])[1])
    assert 0 < own(stack) < own({(0, 0): {}})
    with pytest.raises(ValueError, match="pass baseline="):
        IN.census_gate({(0, 0): terrain}, stack=stack)


def test_census_gate_stack_keeps_the_ensemble_parts_semantics():
    """``parts=`` under ``stack=``: a block it names ships exactly those ENSEMBLE_PARTS (carried,
    else ``deploy_mountain_parts``' blank), so a deployed River the mountain deploy replaces leaves
    the edited stack -- the channel it covered is a NEW miss. A block ``parts`` does not name keeps
    its deployed parts, and a carried Object still shadows the probe."""
    terrain, stack = _river_island()
    base = {(0, 0): terrain}
    q = dict(baseline=base, stack=stack, log=lambda *a: None)
    IN.census_gate({(0, 0): terrain}, parts={}, **q)                  # no ensemble: the River stays
    with pytest.raises(ValueError, match="placement MISS"):
        IN.census_gate({(0, 0): terrain}, parts={(0, 0): {}}, **q)    # blanked by the ensemble deploy
    IN.census_gate({(0, 0): terrain}, parts={(0, 0): {"River": stack[(0, 0)]["River"]}}, **q)
    shadow = [(16.0, 6.0, -16.0), (28.0, 6.0, -16.0), (16.0, 6.0, -28.0)]
    obj = _bm([(shadow, SEA57, 0.5)], name="Block[0][0] Object")
    IN.census_gate({(0, 0): terrain}, probe=((20.0, -20.0), 0), parts={(0, 0): {"River": stack[(0, 0)]["River"]}},
                   **q)
    with pytest.raises(ValueError, match="probe grounded on Object"):
        IN.census_gate({(0, 0): terrain}, probe=((20.0, -20.0), 0),
                       parts={(0, 0): {"Object": obj, "River": stack[(0, 0)]["River"]}}, **q)


def test_census_gate_stack_subtracts_only_the_stacked_sheets_the_island_has():
    lawn = _grid_block(0, 0)
    hill = ((16.0, 9.0, -16.0), (24.0, 9.0, -16.0), (16.0, 9.0, -24.0))
    stacked = _grid_block(0, 0, extra=[(hill, GRASS, _MAIN_U)])
    q = dict(stack={(0, 0): {}}, log=lambda *a: None)
    with pytest.raises(ValueError, match="stacked walkable sheets"):   # BREAK-IT: the carve's own stack
        IN.census_gate({(0, 0): stacked}, baseline={(0, 0): lawn}, **q)
    IN.census_gate({(0, 0): stacked}, baseline={(0, 0): stacked}, **q)   # the island already had it


def test_census_parts_names_every_span_block_the_ensemble_deploy_writes():
    obj = _bm([], name="Block[1][1] Object")
    assert IN.census_parts({"changed_parts": {}, "donor_ref": None, "report": {"blocks": [[1, 1]]}}) == {}
    got = IN.census_parts({"changed_parts": {(1, 1): {"Object": obj}}, "donor_ref": (0, 0),
                           "report": {"blocks": [[1, 1], [2, 1]]}})
    assert got == {(1, 1): {"Object": obj}, (2, 1): {}}


def test_read_deployed_stack_reads_every_registered_part_but_terrain(tmp_path):
    """The aux overrides beside each block's Terrain, by WRAPPED label under the unwrapped key
    (a seam column -1 reads Block[23]); Donor.txt, parked backups and unregistered names are not
    walkmesh parts."""
    r1 = tmp_path / "modx" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1"
    r1.mkdir(parents=True)
    M.write_ff9mesh(_mains_grid(), r1 / "Block[23][1] Terrain.ff9mesh")
    M.write_ff9mesh(_cell_sheet({(1, 1)}, y=1.0, idall=SEA57, name="r"), r1 / "Block[23][1] River.ff9mesh")
    M.write_ff9mesh(_cell_sheet({(2, 2)}, y=0.0, idall=SEA57, name="s"), r1 / "Block[23][1] Sea4.ff9mesh")
    M.write_ff9mesh(_cell_sheet({(2, 2)}, y=0.0, idall=SEA57, name="j"), r1 / "Block[23][1] RiverJoint.ff9mesh")
    M.write_ff9mesh(_cell_sheet({(3, 3)}, y=0.0, idall=SEA57, name="x"), r1 / "Block[23][1] Lava.ff9mesh")
    (r1 / "Block[23][1] Sea4.ff9mesh.bak-20261020").write_bytes(b"old")
    (r1 / "Block[23][1] Donor.txt").write_text("0,0", encoding="utf-8")
    M.write_ff9mesh(_mains_grid(), r1 / "Block[0][1] Terrain.ff9mesh")
    out = IN.read_deployed_stack("modx", {(-1, 1): None, (0, 1): None}, game=tmp_path)
    assert set(out) == {(-1, 1), (0, 1)}
    assert sorted(out[(-1, 1)]) == ["River", "RiverJoint", "Sea4"] and out[(0, 1)] == {}
    assert {(bm.x, bm.y) for bm in out[(-1, 1)].values()} == {(-1, 1)}
    assert len(out[(-1, 1)]["River"].tris) == 2
    assert IN.read_deployed_stack("modx", {}, game=None) == {}


def test_relief_call_sites_census_the_deployed_stack(monkeypatch, tmp_path):
    """A law in a docstring is a wish: every relief verb's census -- the three CLI verbs and the
    three ``world-fuse`` rows -- is handed the block's deployed stack and the pristine baseline,
    and the mountain the parts its deploy writes."""
    from ff9mapkit import cli, config
    from ff9mapkit.world import fuse as FU
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    r1 = tmp_path / "modx" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r1"
    r1.mkdir(parents=True)
    M.write_ff9mesh(_mains_grid(), r1 / "Block[1][1] Terrain.ff9mesh")
    M.write_ff9mesh(_cell_sheet({(1, 1)}, y=1.0, idall=SEA57, name="r"), r1 / "Block[1][1] River.ff9mesh")
    seen = []

    def carve(soup, **k):
        return {"changed": dict(soup["blocks"]), "center": (96.0, -96.0), "changed_parts": {},
                "donor_ref": (0, 0), "report": {"blocks": [[1, 1]]}}

    def gate(changed, **k):
        seen.append(k)
        raise ValueError("stop after the census")
    for verb in ("carve_forest", "build_hill", "carve_mountain"):
        monkeypatch.setattr(IN, verb, carve)
    monkeypatch.setattr(IN, "census_gate", gate)
    for verb in ("world-forest", "world-hill", "world-mountain"):
        args = cli.build_parser().parse_args([verb, "--mod-folder", "modx", "--near", "96,-96", "--dry-run"])
        assert args.func(args) == 2
    for table in ("forest", "hill", "mountain"):
        out = FU.compose_layout("modx", {table: [{"near": [96.0, -96.0]}]}, dry_run=True)
        assert [g.get("error") for g in out["gates"] if not g["ok"]] == ["stop after the census"]
    assert len(seen) == 6
    for k in seen:
        assert set(k["baseline"]) == {(1, 1)}
        assert set(k["stack"]) == {(1, 1)} and sorted(k["stack"][(1, 1)]) == ["River"]
    assert [k.get("parts") for k in seen] == [None, None, {(1, 1): {}}] * 2


def _annulus_bench():
    """A 52u mains grid whose own WEST BORDER is open (a once-edge the island holds) 10u off the
    canopy outline at (20,-26): inside the annulus gate's 11u band, outside the 9u hole ring."""
    return IN.soup_from_blocks({(0, 0): _mains_grid()})


def test_carve_forest_annulus_gate_subtracts_the_islands_own_open_edges(monkeypatch, tmp_path):
    """The annulus-crack gate is baseline-subtracted, as carve_mountain's is: the untouched
    island's open border within 11u of the canopy (the river island's crest-over-bank edge at
    (10.84,-829.54), RUNG5.md) is the island's, not the carve's -- the canopy seats."""
    _patch_donor(monkeypatch, _canopy_donor())
    soup = _annulus_bench()
    outline = [(10.0, -16.0), (30.0, -16.0), (30.0, -36.0), (10.0, -36.0)]
    own = [e for e, n in IN._world_edge_use(soup["blocks"]).items() if n == 1
           and IN.near_poly((e[0][0] + e[1][0]) / 2, (e[0][2] + e[1][2]) / 2, outline, IN.RING_BAND + 2.0)]
    assert len(own) == 7                    # the fixture really holds open edges in the band
    lines = []
    res = IN.carve_forest(soup, center=(20.0, -26.0), donor=(15, 15), game=tmp_path, log=lines.append)
    assert res["center"] == (20.0, -26.0)
    assert any("annulusOnce=0 " in s for s in lines)


def test_carve_forest_annulus_gate_still_refuses_a_crack_the_carve_opens(monkeypatch, tmp_path):
    """BREAK-IT: on the same bench, a kept grass tri knocked out of the re-emitted annulus (a crack
    the carve introduced: its edges were shared on the pristine island) must still refuse."""
    import dataclasses
    _patch_donor(monkeypatch, _canopy_donor())
    real = IN._assemble

    def cracked(soup, drop, new_by_block):
        out = real(soup, drop, new_by_block)
        bm = out[(0, 0)]
        P = bm.chan_arrays[CH_POS]
        victim = next(t for t in bm.tris
                      if 36.0 < sum(P[i][0] for i in t) / 3 < 40.0 and -28.0 < sum(P[i][2] for i in t) / 3 < -24.0)
        out[(0, 0)] = dataclasses.replace(bm, tris=[t for t in bm.tris if t is not victim])
        return out
    monkeypatch.setattr(IN, "_assemble", cracked)
    lines = []
    with pytest.raises(ValueError, match="forest geometry gate failed"):
        IN.carve_forest(_annulus_bench(), center=(20.0, -26.0), donor=(15, 15), game=tmp_path,
                        log=lines.append)
    assert any("annulusOnce=3 " in s for s in lines)


def _hill_window_once(soup, center, radius):
    """The island's own once-edges inside a hill's crack window (radius + 4), before any lift."""
    eu = Counter()
    for t in soup["tris"]:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((IN.kk3(soup["pos"][t[a]]), IN.kk3(soup["pos"][t[b]]))))] += 1
    return [e for e, n in eu.items() if n == 1 and math.hypot((e[0][0] + e[1][0]) / 2 - center[0],
                                                              (e[0][2] + e[1][2]) / 2 - center[1]) < radius + 4]


def test_build_hill_crack_gate_passes_the_islands_own_open_edges():
    """The hill's crack gate is baseline-subtracted, as the forest's and the mountain's are: the
    52u grid's own WEST BORDER lies 16u from a r14 hill -- inside the gate's r + 4 window, outside
    the lift -- like the river island's crest-over-bank edges beside (31,-826) (RUNG5.md "The
    hill's crack gate"). The island's, not the hill's: the hill seats and the edges are logged."""
    soup = IN.soup_from_blocks({(0, 0): _mains_grid()})
    own = _hill_window_once(soup, (16.0, -24.0), 14.0)
    assert len(own) == 4 and {e[0][0] for e in own} == {0.0}      # the fixture really holds them
    lines = []
    res = IN.build_hill(soup, center=(16.0, -24.0), height=3.5, radius=14.0, log=lines.append)
    assert res["report"]["inherited_once"] == 4
    assert any(s.startswith("crack gate: 4 once-edge(s)") and "the island's own" in s for s in lines)
    assert res["report"]["displaced_tris"] > 40


def _seamed_grid(y, seam_x=32.0, jitter=0.0004, n=13, cell=4.0):
    """``_mains_grid`` whose column line ``x = seam_x`` is a NEAR-weld: the tris west of it put
    that vert at ``seam_x - jitter``, the tris east of it at ``seam_x + jitter``. Both round to the
    gate's weld key (:data:`IN.kk3`), so the pristine grid is closed; a lift that differs across
    the 0.0008u gap can round them apart -- a crack the hill itself opens."""
    tris = []
    for i in range(n):
        for j in range(n):
            x0, x1 = i * cell, (i + 1) * cell
            z0, z1 = -j * cell, -(j + 1) * cell
            sx = lambda x: x + (jitter if x == x0 else -jitter) if x == seam_x else x  # noqa: E731
            tris.append((((sx(x0), y, z0), (sx(x1), y, z0), (sx(x0), y, z1)), GRASS, _MAIN_U))
            tris.append((((sx(x1), y, z0), (sx(x1), y, z1), (sx(x0), y, z1)), GRASS, _MAIN_U))
    return _bm(tris)


def test_build_hill_crack_gate_still_refuses_a_crack_the_hill_opens():
    """BREAK-IT: a weld the lift splits is a NEW open edge -- the pristine island had it closed --
    so it still refuses. The near-weld sits 7u east of the centre, on the flank's steepest ring;
    the grid's height puts one twin pair's lifted y astride a kk3 rounding boundary. The grid's
    borders lie 24u+ off, outside the window, so the control seats on the pre-fix gate too."""
    cx, cz, h, r, jit = 25.0, -24.0, 3.5, 14.0, 0.0004
    lw = IN.raised_cosine(7.0 - jit, h, r)
    le = IN.raised_cosine(7.0 + jit, h, r)
    mid = (lw + le) / 2
    y = math.floor((3.2 + mid) * 1000) / 1000 + 0.0005 - mid       # the pair's mean lifted y on the boundary
    soup = IN.soup_from_blocks({(0, 0): _seamed_grid(y, jitter=jit)})
    assert _hill_window_once(soup, (cx, cz), r) == []               # the island holds no open edge there
    assert IN.kk3((32.0 - jit, y + lw, -24.0)) != IN.kk3((32.0 + jit, y + le, -24.0))
    with pytest.raises(ValueError, match="once-edges inside the hill region"):
        IN.build_hill(soup, center=(cx, cz), height=h, radius=r, log=lambda *a: None)
    # the control: the same grid with a TRUE weld (no jitter) seats
    IN.build_hill(IN.soup_from_blocks({(0, 0): _seamed_grid(y, jitter=0.0)}), center=(cx, cz),
                  height=h, radius=r, log=lambda *a: None)


def test_build_hill_crack_gate_judges_an_open_edge_the_lift_moves():
    """An open edge the LIFT MOVES is the hill's, not the island's: the gate matches the pristine
    edges by position, so the grid's west border inside a r14 hill centred 12u off it (displaced,
    an edge open only where the read stops tears from the block it never saw) still refuses."""
    soup = IN.soup_from_blocks({(0, 0): _mains_grid()})
    assert _hill_window_once(soup, (12.0, -24.0), 14.0)
    with pytest.raises(ValueError, match="once-edges inside the hill region"):
        IN.build_hill(soup, center=(12.0, -24.0), height=3.5, radius=14.0, log=lambda *a: None)


# ---- an untouched block CONVERGES: kept tris keep their source tangent (RUNG5.md "The gates measure the carve") --
#
# The world-river island's Terrain stores tangent.w = 0.0; the re-emit used to rebuild every kept tri's tangent
# as the kit's [idall, 0, 0, 1], so a forest rewrote (and took ledger ownership of) every block in its read
# window -- 6 of the [[river]] + [[forest]] recipe's 8 files differed from the river's bytes in tangent.w alone.

def _w0(bm):
    """``bm`` with every tangent.w = 0.0 -- the river island's carried Terrain bytes."""
    import dataclasses
    ca = dict(bm.chan_arrays)
    ca[CH_TAN] = [[t[0], t[1], t[2], 0.0] for t in bm.chan_arrays[CH_TAN]]
    return dataclasses.replace(bm, chan_arrays=ca)


def _forest_beside_a_w0_neighbour(tmp_path, mod):
    """Deploy two welded w=0 grass blocks, carve a forest in (0,0) only, deploy the carve. Returns
    ``(res, written, files, pre)``: the carve, the paths deploy_changed wrote, ``{blk: deployed path}``
    and ``{blk: its bytes before the deploy}``."""
    root = tmp_path / mod / "FF9_Data" / "WorldMap" / "Disc1" / "0_1" / "r0"
    root.mkdir(parents=True)
    files = {}
    for blk in ((0, 0), (1, 0)):
        files[blk] = M.write_ff9mesh(_w0(_grid_block(*blk)), root / f"Block[{blk[0]}][0] Terrain.ff9mesh")
    pre = {blk: p.read_bytes() for blk, p in files.items()}
    blocks = IN.read_deployed_blocks(mod, near=(26.0, -26.0), reach=40.0, game=tmp_path)
    res = IN.carve_forest(IN.soup_from_blocks(blocks), center=(26.0, -26.0), donor=(15, 15),
                          game=tmp_path, log=lambda *a: None)
    written = IN.deploy_changed(res["changed"], mod_folder=mod, game=tmp_path, skip_mirror=True,
                                log=lambda *a: None)
    return res, written, files, pre


def test_carve_forest_leaves_an_untouched_w0_block_unwritten(monkeypatch, tmp_path):
    """The carve re-emits its whole read window; the neighbour (1,0) it never touched re-emits
    byte-identical to its deployed w=0 file, so deploy_changed's byte-compare skips it. In the carved
    block the kept grass keeps w=0 too, and only the canopy + zip wear the kit's w=1."""
    _patch_donor(monkeypatch, _canopy_donor())
    res, written, files, pre = _forest_beside_a_w0_neighbour(tmp_path, "modx")
    assert set(res["changed"]) == {(0, 0), (1, 0)}                      # the neighbour IS re-emitted
    assert M.ff9mesh_bytes(res["changed"][(1, 0)]) == pre[(1, 0)]
    assert [p.name for p in written] == ["Block[0][0] Terrain.ff9mesh"]
    assert files[(1, 0)].read_bytes() == pre[(1, 0)]
    bm = res["changed"][(0, 0)]
    T = bm.chan_arrays[CH_TAN]
    kept = [t for t in bm.tris if all(T[i][3] == 0.0 for i in t)]
    new = [t for t in bm.tris if all(T[i][3] == 1.0 for i in t)]
    assert len(kept) + len(new) == len(bm.tris)                         # no tri mixes the two
    assert len(kept) == len(_grid_block(0, 0).tris) - res["report"]["dropped"]
    assert {T[t[0]][0] for t in new} == {GRASS, FOREST}                 # the zip + the canopy


def test_carve_forest_untouched_block_break_it_the_rebuilt_tangent_rewrites_it(monkeypatch, tmp_path):
    """BREAK-IT: put the old re-emit back (every tangent rebuilt as [idall, 0, 0, 1]) -- the untouched
    neighbour's bytes now differ in tangent.w alone, and the deploy writes it."""
    import dataclasses
    _patch_donor(monkeypatch, _canopy_donor())
    real = IN._assemble

    def rebuilt(soup, drop, new_by_block):
        out = real(soup, drop, new_by_block)
        for blk, bm in out.items():
            ca = dict(bm.chan_arrays)
            ca[CH_TAN] = [[t[0], 0.0, 0.0, 1.0] for t in bm.chan_arrays[CH_TAN]]
            out[blk] = dataclasses.replace(bm, chan_arrays=ca)
        return out
    monkeypatch.setattr(IN, "_assemble", rebuilt)
    res, written, files, pre = _forest_beside_a_w0_neighbour(tmp_path, "modx")
    assert M.ff9mesh_bytes(res["changed"][(1, 0)]) != pre[(1, 0)]
    assert sorted(p.name for p in written) == ["Block[0][0] Terrain.ff9mesh", "Block[1][0] Terrain.ff9mesh"]
    # what landed on the untouched neighbour is its own grid with w=1: tangent.w is the whole diff
    assert files[(1, 0)].read_bytes() == M.ff9mesh_bytes(_grid_block(1, 0)) != M.ff9mesh_bytes(_w0(_grid_block(1, 0)))


def test_carve_mountain_kept_tris_keep_their_source_tangent(monkeypatch, tmp_path):
    """carve_mountain's own re-emit: a kept grass tri carries its source tangent (w=0 here), the massif
    and the zip the kit's [idall, 0, 0, 1]."""
    _patch_donor(monkeypatch, _pyramid_donor())
    res = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _w0(_mountain_bench())}), near=(26.0, -26.0),
                            alcove=None, game=tmp_path, log=lambda *a: None)
    (blk, bm), = res["changed"].items()
    T = bm.chan_arrays[CH_TAN]
    kept = [t for t in bm.tris if all(T[i][3] == 0.0 for i in t)]
    new = [t for t in bm.tris if all(T[i][3] == 1.0 for i in t)]
    assert len(kept) + len(new) == len(bm.tris)
    assert len(kept) == len(_mountain_bench().tris) - res["report"]["dropped"]
    assert len(new) == 4 + res["report"]["zip_tris"]


# ---- the foot-course window (the spur-graft class, R4 take-5) --------------------------------


# a saddle whose high corners stand a real WALL over the lawn: since R4 take 11 a foot tri
# shallower than stock's p01 contact slope (25 deg) is ground, and the default saddle's rim
# sits at lawn height (its steepest foot ~28 deg, most far shallower)
WALL_SADDLE = (0.0, 2.0, 0.0, 1.8)


def _r10_saddle_donor(cx=24.0, cz=-24.0, half=2.5, apex=6.0, ax=1.5, az=1.5,
                      hs=(0.0, 0.6, 0.0, 0.5)):
    """The saddle-rim pyramid dressed in a REAL row-10 tile (col 6 of the rock chart):
    adjacent side faces pair into 4-vert quads whose uv extent is ~one full tile, so
    the foot-course exemplar harvest finds them; the saddle base ring keeps the apron
    field genuinely nonuniform (the flat-window exclusion is observable) while staying
    near-planar (a warped base ring trips the de-tilt rigidity gate). The rise for THE
    PROFILE LAW predicate comes from the APEX: at half=2.5 the apex sits within the
    predicate's 6u reach of the near zip tris (-> rock foot course there) and out of
    reach of the far ones (-> gentle grass) -- OFF-CENTER by (ax, az), because a
    centered apex is equidistant from every zip tri and the split is all-or-nothing;
    pass a low ``apex`` to test the gate."""
    puA, pvA = IN.ROCK_CHART_PHASE
    u0, u1 = puA + 6 * 0.0625, puA + 7 * 0.0625
    v0, v1 = pvA + 10 * 0.03125, pvA + 11 * 0.03125
    c00 = ((cx - half, hs[0], cz - half), u0)
    c10 = ((cx + half, hs[1], cz - half), u1)
    c11 = ((cx + half, hs[2], cz + half), u0)
    c01 = ((cx - half, hs[3], cz + half), u1)
    top = ((cx + ax, apex, cz + az), (u0 + u1) / 2)
    pos, nrm, uv, tan, flat, t_out = [], [], [], [], [], []
    for a, b in ((c10, c00), (c11, c10), (c01, c11), (c00, c01)):
        base = len(pos)
        for (p, pu), pv in ((a, v1), (b, v1), (top, v0 + 0.001)):
            pos.append(list(p))
            nrm.append([0.0, 1.0, 0.0])
            uv.append([pu, pv])
            tan.append([MASSIF_DONOR, 0.0, 0.0, 1.0])
            flat.append(len(pos) - 1)
        t_out.append([base, base + 1, base + 2])
    return BlockMesh(name="Block[0][0] Terrain", disc=1, x=0, y=0, lod="0_1",
                     vcount=len(pos), stride=48,
                     channels={CH_POS: (0, 3), CH_NRM: (12, 3), CH_UV: (24, 2), CH_TAN: (32, 4)},
                     chan_arrays={CH_POS: pos, CH_NRM: nrm, CH_UV: uv, CH_TAN: tan},
                     flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def test_carve_mountain_foot_course_window(monkeypatch, tmp_path):
    puA, pvA = IN.ROCK_CHART_PHASE
    u0, u1 = puA + 6 * 0.0625, puA + 7 * 0.0625
    v0, v1 = pvA + 10 * 0.03125, pvA + 11 * 0.03125
    # BASELINE (no window): the saddle rim lifts the apron grass above the bench plane
    _patch_donor(monkeypatch, _r10_saddle_donor(hs=WALL_SADDLE))
    soup0 = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res0 = IN.carve_mountain(soup0, center=(22.0, -24.0), alcove=None, game=tmp_path,
                             log=lambda *a: None)
    bm0 = res0["changed"][(0, 0)]
    g0 = [p[1] for p, t4 in zip(bm0.chan_arrays[CH_POS], bm0.chan_arrays[CH_TAN])
          if t4[0] == GRASS]
    assert max(g0) > 3.2 + 1e-6, "baseline sanity: the saddle rim must lift the apron"
    assert res0["report"]["foot_tris"] == 0

    # THE WINDOW covers the whole block: no lift anywhere, every zip tri emits as rock
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(22.0, -24.0), alcove=None, game=tmp_path,
                            foot_course_rects=[(0.0, -64.0, 64.0, 0.0)],
                            log=lambda *a: None)
    r = res["report"]
    # rock only near the risen corner (THE PROFILE LAW predicate); the no-rise arcs
    # of the same window stay grass
    assert 0 < r["foot_tris"] < r["zip_tris"]
    # THE PROFILE LAW tight hole: inside the window the drop test uses MTN_FC_CLEAR
    # instead of the standard clearance, so the contact hugs the rim footprint
    assert r["dropped"] < res0["report"]["dropped"]
    bm = res["changed"][(0, 0)]
    grass_y = [p[1] for p, t4 in zip(bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN])
               if t4[0] == GRASS]
    # no apron lift anywhere (the baseline lifted above 3.2): the only grass above the
    # bench plane is the zip riding a rim corner, so every such vert IS a carried position
    rock_at = {tuple(round(float(x), 4) for x in p) for p, t4 in
               zip(bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]) if t4[0] == MASSIF}
    lifted = [p for p, t4 in zip(bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN])
              if t4[0] == GRASS and p[1] > 3.2 + 1e-6
              and tuple(round(float(x), 4) for x in p) not in rock_at]
    assert max(grass_y) > 3.2 + 1e-6 and lifted == [], "window ground must stay flat (no apron lift)"
    # every topo-49 vert (carried faces AND the foot course) samples inside the tile
    rock = [(p, u2) for p, u2, t4 in zip(bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV],
                                         bm.chan_arrays[CH_TAN]) if t4[0] == MASSIF]
    assert len(rock) == (4 + r["foot_tris"]) * 3
    for p, u2 in rock:
        assert u0 - 1e-6 <= u2[0] <= u1 + 1e-6 and v0 - 1e-6 <= u2[1] <= v1 + 1e-6
    # fringe pinning: foot verts at the lawn line sample the exemplar's fringe edge (the
    # harvest's v_bot = the donor pair's two lowest verts = v1 exactly). At, not "at 3.2":
    # take 9 hands the saddle's below-lawn rim nodes back to the apron (the free-base
    # burial take 8 meant for them), which settles the hole a little under the plateau
    foot_ground = [u2 for p, u2 in rock if p[1] < 3.2 + 0.05]
    assert foot_ground and all(u2[1] == pytest.approx(v1, abs=1e-9) for u2 in foot_ground)

    # refusal: a window that catches no zip tri
    soup2 = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    with pytest.raises(ValueError, match="no rock foot course emitted"):
        IN.carve_mountain(soup2, center=(22.0, -24.0), alcove=None, game=tmp_path,
                          foot_course_rects=[(200.0, -260.0, 220.0, -240.0)],
                          log=lambda *a: None)


def _off_lawn_line(bm, corner, vs):
    """The donor with ``corner``'s v moved OFF the lawn line in each face meeting it -- Uaho's home t404/t405
    (one rim vertex at v 10.53 / 10.19 tiles, the painted fringe row at 11.0)."""
    U = [list(u) for u in bm.chan_arrays[CH_UV]]
    hits = [i for i, p in enumerate(bm.chan_arrays[CH_POS]) if tuple(p) == corner]
    assert len(hits) == len(vs)
    for i, v in zip(hits, vs):
        U[i][1] = v
    return BlockMesh(name=bm.name, disc=1, x=0, y=0, lod="0_1", vcount=bm.vcount, stride=48,
                     channels=dict(bm.channels), chan_arrays={**bm.chan_arrays, CH_UV: U},
                     flat_index=bm.flat_index, tris=bm.tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                     submeshes=[])


def test_carve_mountain_snaps_an_off_lawn_line_rim_vertex_onto_the_fringe_row(monkeypatch, tmp_path):
    """THE LAWN-LINE SNAP (UAHO-LAWN-LINE-BENCH.md): stock seats every fringe contact edge on the tile's
    painted lawn line (2,081 of 2,088 disc-1 ends). A donor rim vertex off it reads as bare rock hitting
    the lawn once the zip grass meets it (the owner's Uaho SE end: "no transition tile"). The carve snaps
    it onto the line in every carried corner there -- UV only, so the snapped carve equals the carve of
    the same donor already on the line, byte for byte."""
    pvA = IN.ROCK_CHART_PHASE[1]
    v1 = pvA + 11 * 0.03125
    good = _r10_saddle_donor()
    corner = (24.0 - 2.5, 0.0, -24.0 - 2.5)                  # the saddle's c00 (hs[0] = 0.0)
    bad = _off_lawn_line(good, corner, [v1 - 0.81 * 0.03125, v1 - 0.47 * 0.03125])

    def carve(donor):
        _patch_donor(monkeypatch, donor)
        logs = []
        res = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _mountain_bench()}), center=(22.0, -24.0),
                                alcove=None, game=tmp_path,
                                log=lambda *a: logs.append(" ".join(str(x) for x in a)))
        return res["changed"][(0, 0)], logs

    bm_good, logs_good = carve(good)
    bm_bad, logs_bad = carve(bad)
    assert any("lawn-line snap: 1 rim position, 2 carried corners" in line for line in logs_bad)
    assert not any("lawn-line snap:" in line for line in logs_good)    # already on the line: a no-op
    for ch in (CH_POS, CH_NRM, CH_TAN, CH_UV):
        assert bm_bad.chan_arrays[ch] == bm_good.chan_arrays[ch], ch


def test_lawn_line_snap_skips_a_position_an_interior_rock_tri_fans_at():
    """A snap only where EVERY carried rock corner at the position is a zip contact: an interior tri fanning
    there would take a v seam instead -- the position is left and named."""
    pvA = IN.ROCK_CHART_PHASE[1]
    u, v1, v0 = IN.ROCK_CHART_PHASE[0] + 6.5 * 0.0625, pvA + 11 * 0.03125, pvA + 10 * 0.03125
    off = v1 - 0.5 * 0.03125
    P, Q, R, T = (0.0, 0.0, 0.0), (4.0, 0.0, 0.0), (-4.0, 0.0, 0.0), (0.0, 3.0, -2.0)

    def c8(p, v):
        return (*p, u, v, 0.0, 1.0, 0.0)

    rock = float(encode_id(topograph=49))
    parents = [((c8(P, off), c8(Q, v1), c8(T, v0)), rock, "mountain"),
               ((c8(R, v1), c8(P, off), c8(T, v0)), rock, "mountain"),
               ((c8(Q, 9.0), c8(P, 9.0), c8((0.0, 0.0, 4.0), 9.0)), GRASS, "zip"),
               ((c8(P, 9.0), c8(R, 9.0), c8((0.0, 0.0, 4.0), 9.0)), GRASS, "zip")]
    out, st = IN._lawn_line_snap(parents, rock_topos={49}, log=lambda *a: None)
    assert st["positions"] == 1 and st["entries"] == 2 and st["left"] == 0
    assert all(c[4] == v1 for corners, _, fam in out if fam == "mountain" for c in corners if c[:3] == P)
    # an interior rock tri fanning at P (no zip edge through it): the snap leaves P alone
    fan = ((c8(P, off), c8(T, v0), c8((0.0, 2.0, -4.0), v0)), rock, "mountain")
    out2, st2 = IN._lawn_line_snap(parents + [fan], rock_topos={49}, log=lambda *a: None)
    assert st2["positions"] == 0 and st2["left"] == 2
    assert out2 == parents + [fan]


def test_carve_mountain_unifies_a_fringe_seam_at_a_contact_tri_corner(monkeypatch, tmp_path):
    """THE FRINGE-SEAM UNIFY (UAHO-SEAM-BENCH.md): stock carries 6 fringe v-seams > 0.25 tile in 2,536 shared
    fringe positions, every one on a contact tri. Where two donor charts meet at a contact tri's corner, the
    blades end at a different height either side of their shared edge (R5b's tooth). The carve moves every rock
    corner there onto the present value that moves the fewest -- here one face's apex of four -- so the carve
    equals the carve of the same donor without the seam, byte for byte."""
    pvA = IN.ROCK_CHART_PHASE[1]
    good = _r10_saddle_donor()
    apex = (24.0 + 1.5, 6.0, -24.0 + 1.5)
    hits = [i for i, p in enumerate(good.chan_arrays[CH_POS]) if tuple(p) == apex]
    assert len(hits) == 4
    U = [list(u) for u in good.chan_arrays[CH_UV]]
    U[hits[3]][1] = pvA + 9.4 * 0.03125                      # one face's chart maps the apex 0.63 tile higher
    bad = BlockMesh(name=good.name, disc=1, x=0, y=0, lod="0_1", vcount=good.vcount, stride=48,
                    channels=dict(good.channels), chan_arrays={**good.chan_arrays, CH_UV: U},
                    flat_index=good.flat_index, tris=good.tris, raw_vbuf=b"", raw_ibuf=b"", use32=True,
                    submeshes=[])

    def carve(donor):
        _patch_donor(monkeypatch, donor)
        logs = []
        res = IN.carve_mountain(IN.soup_from_blocks({(0, 0): _mountain_bench()}), center=(22.0, -24.0),
                                alcove=None, game=tmp_path,
                                log=lambda *a: logs.append(" ".join(str(x) for x in a)))
        return res["changed"][(0, 0)], logs

    bm_good, logs_good = carve(good)
    bm_bad, logs_bad = carve(bad)
    assert any("fringe-seam unify: 1 position, 1 carried corner" in line for line in logs_bad)
    assert not any("fringe-seam unify:" in line for line in logs_good)
    for ch in (CH_POS, CH_NRM, CH_TAN, CH_UV):
        assert bm_bad.chan_arrays[ch] == bm_good.chan_arrays[ch], ch


def test_fringe_seam_unify_never_flips_the_texture_and_leaves_a_plug_corner():
    """Candidates are the v values already present; one that would invert a tri (v rising with height) is
    invalid -- R5b's V0, where chart A's value would flip two chart-B tris. A position holding a non-carried rock
    corner (a plug) is left and named."""
    puA, pvA = IN.ROCK_CHART_PHASE
    u = puA + 6.5 * 0.0625

    def v(t):
        return pvA + t * 0.03125

    def c8(p, vt):
        return (*p, u, v(vt), 0.0, 1.0, 0.0)

    rock = float(encode_id(topograph=49))
    P, Q, LA, RB, M, Z = (0.0, 1.0, 0.0), (0.0, 5.0, 0.0), (-4.0, 1.0, 0.0), (4.0, 1.0, 0.0), \
        (3.0, 4.5, -2.0), (0.0, 1.0, 4.0)
    parents = [((c8(P, 11), c8(LA, 11), c8(Q, 10.0625)), rock, "mountain"),     # chart A
               ((c8(RB, 11), c8(P, 11), c8(Q, 9.375)), rock, "mountain"),       # chart B
               ((c8(Q, 9.375), c8(M, 9.9), c8(RB, 11)), rock, "mountain"),      # chart B, M below Q at 9.9
               ((c8(LA, 25), c8(P, 25), c8(Z, 25)), GRASS, "zip"),
               ((c8(P, 25), c8(RB, 25), c8(Z, 25)), GRASS, "zip")]
    out, st = IN._fringe_seam_unify(parents, rock_topos={49}, log=lambda *a: None)
    assert st == {"positions": 1, "entries": 1, "left": 0}
    assert [c[4] for corners, _, fam in out if fam == "mountain" for c in corners if c[:3] == Q] == [v(9.375)] * 3
    assert out[1:] == parents[1:]
    # a plug corner at Q: left alone
    plug = ((c8(Q, 9.375), c8((1.0, 4.0, 1.0), 9.9), c8(M, 9.9)), rock, "plug")
    out2, st2 = IN._fringe_seam_unify(parents + [plug], rock_topos={49}, log=lambda *a: None)
    assert st2 == {"positions": 0, "entries": 0, "left": 1} and out2 == parents + [plug]


def _foot_window_carve(monkeypatch, tmp_path, hs=WALL_SADDLE):
    _patch_donor(monkeypatch, _r10_saddle_donor(hs=hs))
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res = IN.carve_mountain(soup, center=(22.0, -24.0), alcove=None, game=tmp_path,
                            foot_course_rects=[(0.0, -64.0, 64.0, 0.0)], log=lambda *a: None)
    bm = res["changed"][(0, 0)]
    P, U, Tn = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_UV], bm.chan_arrays[CH_TAN]
    rock = [(i, i + 1, i + 2) for i in range(0, len(P), 3) if Tn[i][0] == MASSIF]
    return res, P, U, rock


def _foot_only(P, rock):
    # the saddle donor's 4 carried faces all share its APEX (the highest rock vert); every
    # other rock tri is the emitted foot course
    top = max(float(P[i][1]) for t in rock for i in t)
    return [t for t in rock if max(float(P[i][1]) for i in t) < top - 1e-6]


def test_carve_mountain_foot_course_no_rock_below_the_lawn(monkeypatch, tmp_path):
    # R4 take 9, the owner-filed NW sliver ("should be ground"): the saddle's low corners
    # sit under the plateau, 6u from the risen apex -- take 8's centroid predicate saw the
    # apex and minted fringe rock lying flat on the dip there (2 tris on this donor). Rock
    # only where the nearest rim stands above the lawn AND the tri itself rises over it.
    res, P, U, rock = _foot_window_carve(monkeypatch, tmp_path)
    assert res["report"]["foot_tris"] > 0
    lying = [t for t in rock if max(float(P[i][1]) for i in t) <= 3.2 + IN.MTN_FC_RIM_ABOVE]
    assert lying == []


def test_carve_mountain_foot_course_v_is_per_vertex(monkeypatch, tmp_path):
    # R4 take 9, the owner's "1 has a grass edge, 2 has a mountain edge, but they meet at
    # an edge": take 8 spread each tri's own full tile over its own span, so a shared rim
    # vert took a different v in every neighbour (0.33 tile apart on this donor; 0.97 on
    # the live SE corner). v is now a function of the VERTEX -- the donor's own cut tile
    # at a carried rim vert, the stock-density lawn deviation elsewhere -- so every tri
    # sharing a position samples the same texel row there (stock: 6 seams in 2536).
    _, P, U, rock = _foot_window_carve(monkeypatch, tmp_path)
    at = defaultdict(set)
    for t in rock:
        for i in t:
            at[tuple(round(float(x), 3) for x in P[i])].add(round(float(U[i][1]), 7))
    seams = {k: v for k, v in at.items() if max(v) - min(v) > 1e-6}
    assert seams == {}


def test_carve_mountain_foot_course_u_is_per_vertex(monkeypatch, tmp_path):
    # R4 take 11, the owner's SE-corner streaks: take 5-10 stretched each foot tri's own
    # s-extent over one full tile width, so u restarted at every tri (live window abs-u spread
    # p50 0.97 tile; stock p50 0.00). u is now one function of the vertex (arc length along
    # the course, mirror-repeated in the exemplar strip): foot tris sharing a position sample
    # the same texel column there.
    res, P, U, rock = _foot_window_carve(monkeypatch, tmp_path)
    foot = _foot_only(P, rock)
    assert foot
    at = defaultdict(set)
    for t in foot:
        for i in t:
            at[tuple(round(float(x), 3) for x in P[i])].add(round(float(U[i][0]), 7))
    assert {k: v for k, v in at.items() if max(v) - min(v) > 1e-6} == {}


def test_carve_mountain_foot_course_no_shallow_wall(monkeypatch, tmp_path):
    # R4 take 11, the owner's "3": a 21 deg rock skirt at the SE corner. Stock's rock-grass
    # contact tris are shallower than 25 deg in 1.1% of 1130 (p01) -- a foot tri that shallow
    # is ground, emitted as grass.
    res, P, U, rock = _foot_window_carve(monkeypatch, tmp_path)
    floor = math.cos(math.radians(IN.MTN_FC_SLOPE_MIN))
    shallow = []
    for t in _foot_only(P, rock):
        a, b, c = (np.asarray(P[i][:3], dtype=float) for i in t)
        n = np.cross(b - a, c - a)
        if abs(n[1]) / (np.linalg.norm(n) or 1.0) >= floor:
            shallow.append(t)
    assert res["report"]["foot_tris"] > 0 and shallow == []


def test_carve_mountain_foot_course_fin_is_ground(monkeypatch, tmp_path):
    # R4 take 12: a foot tri reaching down to a BURIED rim vert (the donor's rim under the
    # lawn -- its free-base burial) is ground. As rock it put two verts on the fringe edge row
    # and smeared (the SE corner's t631, takes 10-11); as plain rock (option A) it read as a
    # grey shard on the lawn. The saddle's low corners are buried, so it has such tris.
    res, P, U, rock = _foot_window_carve(monkeypatch, tmp_path)
    foot = _foot_only(P, rock)
    carried_at = {tuple(round(float(x), 3) for x in P[i]) for t in rock if t not in foot for i in t}
    buried = {k for k in carried_at if k[1] < 3.2 - IN.MTN_FC_RIM_ABOVE - 0.05}
    assert buried, "the fixture must bury part of its rim"
    assert res["report"]["foot_tris"] > 0
    assert [t for t in foot if any(tuple(round(float(x), 3) for x in P[i]) in buried
                                   for i in t)] == []


def test_carve_mountain_foot_course_relief_gate(monkeypatch, tmp_path):
    # THE PROFILE LAW relief gate: a rim parked at lawn height everywhere (the flat
    # saddle) does not rise, so the window refuses to paint rock on the flat lawn --
    # the owner-filed "stretches of rock on the ground" defect class
    _patch_donor(monkeypatch, _r10_saddle_donor(apex=1.2))
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    with pytest.raises(ValueError, match="no rock foot course emitted"):
        IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                          foot_course_rects=[(0.0, -64.0, 64.0, 0.0)],
                          log=lambda *a: None)


def test_carve_mountain_foot_course_needs_exemplars(monkeypatch, tmp_path):
    # a donor with no row-10 full-tile quads (the plain pyramid's flat _MAIN_U uvs)
    _patch_donor(monkeypatch, _pyramid_donor())
    soup = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    with pytest.raises(ValueError, match="no row-10 exemplar"):
        IN.carve_mountain(soup, near=(26.0, -26.0), alcove=None, game=tmp_path,
                          foot_course_rects=[(0.0, -64.0, 64.0, 0.0)],
                          log=lambda *a: None)


def test_carve_mountain_foot_course_steepen(monkeypatch, tmp_path):
    _patch_donor(monkeypatch, _r10_saddle_donor(hs=WALL_SADDLE))
    # the subject is the (retired, take 6) pull's own geometry. Since take 12 the saddle's
    # buried-rim fins are ground, and the pull steepens them into grass banks: 4 against the
    # zip's budget of 2, a refusal the gate is RIGHT to make for a real carve -- so this test
    # alone widens the budget, to keep measuring what the pull does to the base
    monkeypatch.setattr(IN, "MTN_ZIP_BANK_MAX", 4)

    def base_radius(res):
        cx2, cz2 = res["center"]
        bm = res["changed"][(0, 0)]
        pos, tan = bm.chan_arrays[CH_POS], bm.chan_arrays[CH_TAN]
        r = 0.0
        for tri in bm.tris:
            if tan[tri[0]][0] != MASSIF or not any(pos[i][1] > 6.0 for i in tri):
                continue                                   # only the carried pyramid faces
            for i in tri:
                if pos[i][1] < 5.0:
                    r = max(r, math.hypot(pos[i][0] - cx2, pos[i][2] - cz2))
        return r

    soup0 = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res0 = IN.carve_mountain(soup0, near=(26.0, -26.0), alcove=None, game=tmp_path,
                             foot_course_rects=[(0.0, -64.0, 64.0, 0.0)],
                             log=lambda *a: None)
    soup1 = IN.soup_from_blocks({(0, 0): _mountain_bench()})
    res1 = IN.carve_mountain(soup1, near=(26.0, -26.0), alcove=None, game=tmp_path,
                             foot_course_rects=[(0.0, -64.0, 64.0, 0.0, 2.0)],
                             log=lambda *a: None)
    assert res0["center"] == res1["center"]
    # the pull drags the base toward the centre (full at lawn height); the apex, near
    # TOP, barely moves -- the face steepens
    assert base_radius(res0) - base_radius(res1) > 1.2
    assert res1["report"]["peak_y"] == pytest.approx(res0["report"]["peak_y"], abs=1e-6)


@needs_game
def test_carve_mountain_clamps_comp9s_plug_into_its_collar_tile(tmp_path):
    """THE COLLAR-TILE CLAMP (snowmassif/NOTES.md, round 21): comp9's plug chart extrapolates to v 0.2038, past its
    collar (v <= 0.1973) and across the atlas's tile line at 0.200 -- the white sliver the owner saw. The carve
    clamps that overshoot (27 px against a 9 px fit residual) into the collar's uv box, and its plugs then sample
    no gutter texel. Uaho's plug overshoot sits inside its fit's noise and is kept: the identity nets above pin it.
    The raw overshoot is asserted too, so the clamp is shown to have had work to do."""
    from ff9mapkit.world.island import build_landmass
    for seed in (42.0, 7.0, 11.0):                     # mountaindonors/sweep.py's bench: r94 snow at (1380, -100)
        try:
            built = build_landmass(center=(1380.0, -100.0), base_radius=94.0, seed=seed, lobes=1, n_patches=0,
                                   ground="snow")
            break
        except Exception:                              # noqa: BLE001 -- a mint that trips its own shape gates
            continue
    blocks = {blk: M.blockmesh_from_ff9mesh(M.write_ff9mesh(bm, tmp_path / f"b_{blk[0]}_{blk[1]}.ff9mesh"), disc=1,
                                            x=blk[0], y=blk[1], part="terrain")
              for blk, bm in built["blocks"].items()}
    lines = []
    res = IN.carve_mountain(IN.soup_from_blocks(blocks), near=(1380.0, -100.0), donor=COMP9_BLOCKS, rot_deg=0,
                            ground="snow", alcove=COMP9_INLET, log=lines.append)
    plug_line = next(str(s) for s in lines if str(s).startswith("aperture plugs:"))
    m = re.search(r"raw plug uv u \S+ v ([\d.]+)\.\.([\d.]+) vs the collar box u \S+ v ([\d.]+)\.\.([\d.]+)",
                  plug_line)
    raw_hi, box_hi = float(m.group(2)), float(m.group(4))
    assert raw_hi > box_hi + 0.004, plug_line                            # the chart does overshoot (27 px)
    assert "clamped into the collar's uv box" in plug_line
    assert res["report"]["plugs"] == 2
    assert any("white-gutter tris = 0" in str(s) for s in lines) or any("atlas gate SKIPPED" in str(s) for s in lines)
