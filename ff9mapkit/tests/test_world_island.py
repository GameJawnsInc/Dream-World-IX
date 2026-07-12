"""world-island + the placement simulator + the grass language: the synth-landmass builder.

Hermetic -- the builder synthesizes everything (``flat`` mode needs no install data; relief/stamps are
install-derived and covered by the gated tests elsewhere). Coverage:
  * the ENGINE PLACEMENT simulator's RE'd semantics (the rules that broke the original synth blob):
    winding filter, buffer-order-first (not nearest), mesh-order-first (Terrain shadows Sea), walk vs sky
    ray windows, the idall skip set, miss -> ground 0
  * fill_missing_grid_quads (the real (12,0) sea plane's hole = a void render + an invisible vehicle wall)
  * the grass mains language: the 4 measured orientation maps, the direction-aware bleed clamp, the
    avoid-same neighbour policy
  * build_landmass: gates clean in flat mode; MULTI-CELL splitting at 64u borders (per-block locality,
    watertight across the cut, rock UV wrap-safety, per-block placement census 0-MISS)
  * the deploy orchestration (7 parts + Donor.txt per touched block; dry-run writes nothing)
"""
from __future__ import annotations

import math

import pytest

from ff9mapkit.world import grassland as G, island as I, mesh as M, placement as P
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
                     flat_index=flat, tris=t_out, raw_vbuf=b"", raw_ibuf=b"", use32=True, submeshes=[])


GRASS = encode_id(topograph=0)
SEA = encode_id(topograph=57)
_UP = [(0.0, 3.5, 0.0), (8.0, 3.5, 0.0), (0.0, 3.5, -8.0)]          # CCW-from-above (engine up)
_DOWN = [(0.0, 3.5, 0.0), (0.0, 3.5, -8.0), (8.0, 3.5, 0.0)]        # reversed = down-wound


# ---- the placement simulator ----------------------------------------------------------------------------------------

def test_place_down_wound_top_is_invisible_and_misses_to_zero():
    """The original blob's fatal bug: a down-wound walkable top is filtered out -> ground 0."""
    bad = _bm([(_DOWN, GRASS)])
    gy, name, _, topo = P.place([("Terrain", bad)], 2.0, -2.0)
    assert (gy, name, topo) == (0.0, "MISS", None)
    good = _bm([(_UP, GRASS)])
    gy, name, _, topo = P.place([("Terrain", good)], 2.0, -2.0)
    assert (gy, name, topo) == (3.5, "Terrain", 0)


def test_place_first_buffer_triangle_wins_not_the_nearest():
    """Stacked up-facing layers resolve by BUFFER position: the lower tri, earlier in the buffer, wins."""
    lower = [(0.0, 1.0, 0.0), (8.0, 1.0, 0.0), (0.0, 1.0, -8.0)]
    upper = [(0.0, 5.0, 0.0), (8.0, 5.0, 0.0), (0.0, 5.0, -8.0)]
    gy, _, _, _ = P.place([("Terrain", _bm([(lower, GRASS), (upper, GRASS)]))], 2.0, -2.0)
    assert gy == 1.0                                     # NOT the closest hit from the sky (5.0)
    gy, _, _, _ = P.place([("Terrain", _bm([(upper, GRASS), (lower, GRASS)]))], 2.0, -2.0)
    assert gy == 5.0


def test_place_first_mesh_wins_terrain_shadows_sea_above():
    """Mesh REGISTRATION order: any Terrain hit beats a Sea surface above it (real blocks therefore keep
    water areas Terrain-free)."""
    submerged = [(0.0, -0.6, 0.0), (8.0, -0.6, 0.0), (0.0, -0.6, -8.0)]
    surface = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 0.0, -8.0)]
    gy, name, _, _ = P.place([("Terrain", _bm([(submerged, GRASS)])), ("Sea4", _bm([(surface, SEA)]))],
                             2.0, -2.0)
    assert (gy, name) == (-0.6, "Terrain")
    gy, name, _, topo = P.place([("Terrain", _bm([])), ("Sea4", _bm([(surface, SEA)]))], 2.0, -2.0)
    assert (gy, name, topo) == (0.0, "Sea4", 57)


def test_place_walk_ray_window_vs_sky():
    """Walking: origin y+2.34375, reach 2.8 -- ground above the origin or >2.8 below is unreachable
    (miss -> 0). Sky mode finds it from any height."""
    bm = _bm([(_UP, GRASS)])                             # ground at 3.5
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=0.0, sky=False)[1] == "MISS"    # 3.5 > 0+2.34
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=2.0, sky=False)[0] == 3.5      # within [y-0.46, y+2.34]
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=8.0, sky=False)[1] == "MISS"    # 4.5 below: > 2.8 drop
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=800.0, sky=True)[0] == 3.5


def test_place_skips_the_engine_idall_exceptions():
    for skip_id in sorted(P.IDALL_SKIP):
        bm = _bm([(_UP, skip_id), (_UP, GRASS)])
        gy, _, idall, _ = P.place([("Terrain", bm)], 2.0, -2.0)
        assert idall == GRASS                            # the skipped tri is invisible to the query


def test_census_reports_misses():
    bm = _bm([(_UP, GRASS)])
    cen = P.census([("Terrain", bm)], span=(1.0, 63.0, -63.0, -1.0), samples=8)
    assert len(cen["miss"]) > 0 and ("Terrain", 0) in cen["counts"]


# ---- fill_missing_grid_quads ----------------------------------------------------------------------------------------

def _grid_plane(missing=()):
    tris = []
    for i in range(16):
        for j in range(-16, 0):
            if (i, j) in missing:
                continue
            x0, z0 = 4.0 * i, 4.0 * j
            tris.append(([(x0, 0.0, z0), (x0, 0.0, z0 + 4), (x0 + 4, 0.0, z0)], SEA))
            tris.append(([(x0 + 4, 0.0, z0), (x0, 0.0, z0 + 4), (x0 + 4, 0.0, z0 + 4)], SEA))
    return _bm(tris, name="Block[12][0] Sea4", x=12, y=0)


def test_fill_missing_grid_quads_fills_the_hole():
    holed = _grid_plane(missing={(15, -12), (3, -5)})
    fixed = M.fill_missing_grid_quads(holed)
    assert len(fixed.tris) == len(holed.tris) + 4        # 2 tris per filled quad
    # the census over the fixed plane has no miss at the former holes
    gy, name, _, topo = P.place([("Sea4", fixed)], 62.0, -46.0)
    assert (name, topo, gy) == ("Sea4", 57, 0.0)


def test_fill_missing_grid_quads_complete_plane_is_returned_unchanged():
    full = _grid_plane()
    assert M.fill_missing_grid_quads(full) is full


# ---- the grass mains language ---------------------------------------------------------------------------------------

def test_mains_uv_orientation_maps_match_the_measured_derivatives():
    """ori0 u=+x v=-z; ori90 u=+z v=+x; ori180 u=-x v=+z; ori270 u=-z v=-x (one handedness, real 100%)."""
    cell, quad = (0, 0), (0, 0)
    for ori, (du_dx, du_dz, dv_dx, dv_dz) in {0: (1, 0, 0, -1), 90: (0, 1, 1, 0),
                                              180: (-1, 0, 0, 1), 270: (0, -1, -1, 0)}.items():
        u0, v0 = G.mains_uv(1.0, 1.0, cell, quad, ori)
        ux, vx = G.mains_uv(1.5, 1.0, cell, quad, ori)
        uz, vz = G.mains_uv(1.0, 1.5, cell, quad, ori)
        assert math.copysign(1, ux - u0) == du_dx if du_dx else abs(ux - u0) < 1e-9
        assert math.copysign(1, uz - u0) == du_dz if du_dz else abs(uz - u0) < 1e-9
        assert math.copysign(1, vx - v0) == dv_dx if dv_dx else abs(vx - v0) < 1e-9
        assert math.copysign(1, vz - v0) == dv_dz if dv_dz else abs(vz - v0) < 1e-9


def test_mains_uv_bleed_never_leaves_the_region():
    """Straddler corners bleed INWARD only (outside the 2x2 region = Moguri's transparent gutters)."""
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    for quad in ((0, 0), (0, 1), (1, 0), (1, 1)):
        for ori in G.ORIS:
            for (x, z) in ((-6.0, 2.0), (10.0, -10.0), (2.0, 6.0), (-6.0, -10.0)):   # far outside cell (0,0)
                u, v = G.mains_uv(x, z, (0, 0), quad, ori)
                assert lo_u - 1e-9 <= u <= hi_u + 1e-9 and lo_v - 1e-9 <= v <= hi_v + 1e-9


def test_assign_mains_avoid_same_policy():
    """The policy dodges ONE randomly-picked assigned neighbour (real same-quadrant rate is 12%, not 0):
    a cell always differs from at least one W/S neighbour, and the overall same-rate stays low."""
    cells = [(i, j) for i in range(12) for j in range(12)]
    cq, _ = G.assign_mains(cells, seed=7)
    same = tot = 0
    for (i, j) in cells:
        nbs = [nb for nb in ((i - 1, j), (i, j - 1)) if nb in cq]
        if nbs:
            assert any(cq[nb] != cq[(i, j)] for nb in nbs)
        for nb in nbs:
            tot += 1
            same += cq[nb] == cq[(i, j)]
    assert same / tot < 0.2                              # real: ~12%; uniform-random would be 25%


# ---- the landmass builder -------------------------------------------------------------------------------------------

def _synth_plane():
    return _grid_plane()


def test_build_landmass_single_cell_gates_clean():
    built = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)
    assert set(built["blocks"]) == {(3, 1)}
    rep = I.verify_landmass(built, sea_plane=_synth_plane())
    assert rep["clean"], rep
    entry = rep["placement"][(3, 1)]
    assert entry["miss"] == 0 and entry["centre_ok"]


def test_build_landmass_multi_cell_splits_per_block_and_stays_watertight():
    built = I.build_landmass(center=(256.0, -96.0), base_radius=26.0, seed=5.0)   # centred ON the x=256 border
    assert len(built["blocks"]) >= 2 and (3, 1) in built["blocks"] and (4, 1) in built["blocks"]
    # per-block locality: every vert inside its block's local bounds (the engine raycasts only that block)
    for blk, bm in built["blocks"].items():
        for v in bm.verts:
            assert -1e-6 <= v[0] <= I.BLOCK + 1e-6 and -I.BLOCK - 1e-6 <= v[2] <= 1e-6, (blk, v)
    rep = I.verify_landmass(built, sea_plane=_synth_plane())
    assert rep["clean"], rep                            # cracks==0 = watertight across the border cut
    for blk, entry in rep["placement"].items():
        assert entry["miss"] == 0, (blk, entry)


def test_build_landmass_rock_uvs_are_wrap_safe():
    """Every rock tri's U window fits inside the strip (the mid-tri sawtooth wrap was the in-game smear)."""
    built = I.build_landmass(center=(224.0, -96.0), base_radius=22.0, seed=11.0)
    strip_w = I.ROCK_U[1] - I.ROCK_U[0]
    from ff9mapkit.world.extract import decode_id
    n_rock = 0
    for _, idall, fam, uvv in built["world"]["meta"]:
        if fam != "rock":
            continue
        n_rock += 1
        us = [u for (u, _) in uvv]
        assert I.ROCK_U[0] - 1e-6 <= min(us) and max(us) <= I.ROCK_U[1] + 1e-6
        assert max(us) - min(us) <= strip_w + 1e-6
    assert n_rock > 50


def test_landmass_deploy_orchestration(monkeypatch):
    overrides, sidecars = [], []
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: overrides.append((bm.x, bm.y, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: sidecars.append((dx, dy, k["x"], k["y"])))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True)
    assert s["op"] == "landmass" and [b["block"] for b in s["blocks"]] == [[3, 1]]
    parts = sorted(p for (_, _, p) in overrides)
    assert parts == sorted(["Terrain", "Sea4", *I.HIDDEN_PARTS])
    assert all(o[0] == 3 and o[1] == 1 for o in overrides)
    assert sidecars == [(0, 0, 3, 1)]


def test_multi_blob_outline_deterministic_and_in_language():
    """The asymmetric multi-lobe coastline stays inside FF9's measured shape language (real: med turn
    22 deg/8u, corner 15%, acute 7%) and is reproducible per seed."""
    a1, r1 = M.multi_blob_outline(96.0, -192.0, lobes=3, base_radius=40.0, seed=86.0)
    a2, r2 = M.multi_blob_outline(96.0, -192.0, lobes=3, base_radius=40.0, seed=86.0)
    assert a1 == a2 and r1 == r2 and min(r1) > 0
    st = M.outline_shape_stats(a1)
    assert 8.0 <= st["med_turn"] <= 35.0 and st["acute"] <= 0.12 and st["max_turn"] < 150.0
    st_other = M.outline_shape_stats(M.multi_blob_outline(96.0, -192.0, lobes=3, base_radius=40.0, seed=87.0)[0])
    assert st_other != st                                # a different seed is a different island


def test_build_landmass_lobes_shape_gate():
    built = I.build_landmass(center=(96.0, -192.0), base_radius=40.0, seed=86.0, lobes=3)
    rep = I.verify_landmass(built, sea_plane=_synth_plane())
    assert rep["shape"]["ok"] and rep["clean"], rep
    assert len(built["blocks"]) >= 4                     # a radius-40 landmass genuinely spans blocks


def test_landmass_dry_run_writes_nothing(monkeypatch):
    called = []
    monkeypatch.setattr(M, "deploy_override", lambda *a, **k: called.append(a))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: called.append(a))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, dry_run=True)
    assert not called and s["report"]["clean"]


def test_landmass_refuses_real_world_blocks(monkeypatch):
    """THE OPEN-OCEAN TARGET LAW: a footprint block with real per-block mesh assets refuses the
    whole deploy -- on a sea-only real block the Terrain override has no transform to bind to,
    so the fragment silently never renders in-game (the (6,17) canvas incident, 2026-07-12)."""
    import pytest
    called = []
    monkeypatch.setattr(M, "deploy_override", lambda *a, **k: called.append(a))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: called.append(a))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts",
                        lambda blk, **k: {"sea3": 2, "sea5": 16} if blk == (3, 1) else {})
    with pytest.raises(ValueError, match=r"REAL world block.*(3, 1)"):
        I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True)
    assert not called                                    # refused BEFORE any file was written
