"""world-island + the placement simulator + the grass language: the synth-landmass builder.

Hermetic -- the builder synthesizes everything (``flat`` mode needs no install data; meadow stamps are
install-derived and covered by the gated tests elsewhere; interiors are FLAT by default -- the ambient
relief field was RESURRECTED opt-in 2026-07-21 as a world-XZ value-noise field, world-keyed by
construction so the DEAD-RELIEF frame bug cannot recur; off by default => byte-identity). Coverage:
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
import warnings

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
    """Walking: origin y+2.34375, INFINITE reach down -- ground above the origin is unreachable
    (the climb ceiling); any DROP is legal (ff9.rayDistance is dead code in WMBlock.Raycast,
    source-verified 2026-07-12 -- how canopies/ledges are exitable). Sky finds it from any height."""
    bm = _bm([(_UP, GRASS)])                             # ground at 3.5
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=0.0, sky=False)[1] == "MISS"    # 3.5 > 0+2.34
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=2.0, sky=False)[0] == 3.5      # climb 1.5 <= 2.34
    assert P.place([("Terrain", bm)], 2.0, -2.0, y=8.0, sky=False)[0] == 3.5      # drop 4.5: LEGAL
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


# ---- the spatial index (audit rec 2: the accelerator that makes dense censuses affordable) --------------------------

def _nasty_meshlist():
    """Every semantics the index could plausibly break, in one meshlist: stacked same-plan tris
    (buffer order decides), a down-wound top, an engine-skipped idall, a tri crossing bucket
    borders, a second mesh shadowed by the first, and empty space."""
    lower = [(0.0, 1.0, 0.0), (8.0, 1.0, 0.0), (0.0, 1.0, -8.0)]
    upper = [(0.0, 5.0, 0.0), (8.0, 5.0, 0.0), (0.0, 5.0, -8.0)]
    spanner = [(5.0, 2.0, -5.0), (21.0, 2.0, -5.0), (5.0, 2.0, -21.0)]   # crosses the 8u/16u bucket lines
    skip = sorted(P.IDALL_SKIP)[0]
    surface = [(-8.0, 0.0, 8.0), (24.0, 0.0, 8.0), (-8.0, 0.0, -24.0)]
    terr = _bm([(lower, GRASS), (_DOWN, GRASS), (upper, skip), (upper, GRASS), (spanner, GRASS)])
    sea = _bm([(surface, SEA)])
    return [("Terrain", terr), ("Sea4", sea)]


def test_place_index_is_a_pure_accelerator():
    """Indexed and unindexed ``place`` agree at EVERY probe of a dense lattice that lands on tri
    edges, bucket borders (0, 8, 16), interior points, and off-mesh space -- ascending bucket order
    reproduces the file-order first hit, so the index can never change a verdict."""
    ml = _nasty_meshlist()
    idx = P.build_meshlist_index(ml)
    probes = [(-9.0 + i * 0.5, 9.0 - j * 0.5) for i in range(70) for j in range(70)]
    assert (0.0, 0.0) in probes and (8.0, -8.0) in probes and (16.0, -16.0) in probes
    for px, pz in probes:
        assert P.place(ml, px, pz, index=idx) == P.place(ml, px, pz), (px, pz)
    # the walk-ray window must thread through identically too
    for py, sky in ((0.0, False), (2.0, False), (800.0, True)):
        assert P.place(ml, 2.0, -2.0, y=py, sky=sky, index=idx) == \
            P.place(ml, 2.0, -2.0, y=py, sky=sky)


def test_census_indexed_matches_pointwise_unindexed_place():
    """``census`` now builds the index internally; its every reported point must equal the
    unindexed ``place`` verdict at that sample -- the accelerator is invisible in the output."""
    ml = _nasty_meshlist()
    cen = P.census(ml, span=(-9.0, 25.0, -25.0, 9.0), samples=24)
    for px, pz, gy, name, topo in cen["points"]:
        egy, ename, _, etopo = P.place(ml, px, pz, 0.0, sky=True)
        assert (gy, name, topo) == (egy, ename, etopo), (px, pz)


def test_coastnav_reuses_the_placement_index():
    """The promotion left ONE copy: coastnav's grid builder is placement's, same bucket size."""
    from ff9mapkit.world import coastnav as CN
    assert CN._build_grid is P.build_index and CN._GRID == P.INDEX_GRID


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


def _mock_landmass_deploy(monkeypatch):
    """Mock every write + the coast-nav stamp; returns (overrides, sidecars, stamps)."""
    from ff9mapkit.world import coastnav as CN
    overrides, sidecars, stamps = [], [], []
    monkeypatch.setattr(M, "deploy_override",
                        lambda bm, **k: overrides.append((bm.x, bm.y, k.get("part"))))
    monkeypatch.setattr(M, "deploy_donor_sidecar",
                        lambda dx, dy, **k: sidecars.append((dx, dy, k["x"], k["y"])))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})
    monkeypatch.setattr(CN, "stamp",
                        lambda mod_folder, **k: stamps.append((mod_folder, k)) or
                        {"policy": k.get("policy"), "totals": {56: 1}})
    return overrides, sidecars, stamps


def test_landmass_deploy_orchestration(monkeypatch):
    overrides, sidecars, stamps = _mock_landmass_deploy(monkeypatch)
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True)
    assert s["op"] == "landmass" and [b["block"] for b in s["blocks"]] == [[3, 1]]
    parts = sorted(p for (_, _, p) in overrides)
    assert parts == sorted(["Terrain", "Sea4", *I.HIDDEN_PARTS])
    assert all(o[0] == 3 and o[1] == 1 for o in overrides)
    assert sidecars == [(0, 0, 3, 1)]


# --- THE COAST-NAV EMITTER DEFAULT (Path D handoff step 5) ---------------------------------------


def test_landmass_stamps_coastnav_by_default(monkeypatch):
    """A fresh mint must not ship boat-permeable water: the emitter stamps its OWN cells, in the
    TARGET namespace, without per-file backups (the pre-stamp state is this call's own output)."""
    _, _, stamps = _mock_landmass_deploy(monkeypatch)
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, target_disc=9)
    assert len(stamps) == 1
    mod_folder, kw = stamps[0]
    assert mod_folder == "MOD"
    assert kw["cells"] == [(3, 1)], "the stamp must cover exactly the mint's own blocks"
    assert kw["disc"] == 9, "the stamp must run in the namespace the mint deployed into"
    assert kw["policy"] == "land-anywhere" and kw["deploy"] is True and kw["backup"] is False
    assert s["coastnav"]["totals"] == {56: 1}


def test_landmass_coastnav_policy_passes_through(monkeypatch):
    _, _, stamps = _mock_landmass_deploy(monkeypatch)
    I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
               coastnav_policy="cliffs-refuse")
    assert stamps[0][1]["policy"] == "cliffs-refuse"


def test_landmass_coastnav_opt_out_and_dry_run_do_not_stamp(monkeypatch):
    _, _, stamps = _mock_landmass_deploy(monkeypatch)
    s1 = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, coastnav=False)
    s2 = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, dry_run=True)
    assert stamps == [] and "coastnav" not in s1 and "coastnav" not in s2


def _once_edge_violations(built):
    """Position-welded once-edges of the world soup with any vertex above the y=0 sea skirt
    (rounded-degenerate keys skipped -- border-clip hairline cut-vert pairs are not edges)."""
    import collections
    gpos, gtris = built["world"]["pos"], built["world"]["tris"]
    cnt = collections.Counter()
    for tri in gtris:
        pts = [tuple(round(gpos[v][k], 3) for k in range(3)) for v in tri]
        for q in range(3):
            if pts[q] != pts[(q + 1) % 3]:
                cnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    return [e for e, n in cnt.items() if n == 1 and not (e[0][1] <= 1e-3 and e[1][1] <= 1e-3)]


def test_build_landmass_seed42_concave_dent_is_watertight():
    """THE SEED-42 GRASS SLIVER (in-game confirmed 2026-07-13): at a concave corner dent the
    UNCONSTRAINED Delaunay may legally pick the OTHER diagonal of the quad spanning the notch (the rim
    ring edge is then not a triangulation edge at all); the centroid keep-filter drops both cover
    triangles, and the face between the wall top and the grass shipped MISSING from Block[2][19] -- a
    closed 3-cycle of once-edges at world (143-144, y 3.2, z -1262..-1265.4), far too small for the
    30x30 hole sampler. Ring-edge recovery must flip the notch quad back and the once-edge gate must
    hold on the exact shipping parameters."""
    built = I.build_landmass(center=(160.0, -1246.0), base_radius=31.0, seed=42.0, lobes=1, n_patches=0)
    assert built["ring_edge_flips"] >= 1                 # the notch quad WAS mis-diagonalized
    assert _once_edge_violations(built) == []
    rep = I.verify_landmass(built, sea_plane=_synth_plane())
    assert rep["open_edges"] == 0 and rep["missing_faces"] == 0 and rep["clean"], rep
    # the centroid of the face that shipped missing must now be covered by a grass triangle
    px, pz = 143.641, -1263.820
    gpos, gtris = built["world"]["pos"], built["world"]["tris"]
    covered = False
    for tri in gtris:
        a, b, c = (gpos[v] for v in tri)
        d = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[2]-c[2])*(px-c[0]) + (c[0]-b[0])*(pz-c[2])) / d
        w1 = ((c[2]-a[2])*(px-c[0]) + (a[0]-c[0])*(pz-c[2])) / d
        if w0 >= 0 and w1 >= 0 and 1 - w0 - w1 >= 0:
            covered = True
            break
    assert covered


def test_ring_edge_recovery_is_a_noop_on_island_E():
    """Island E (seed 55, centre (344,-1152), r46, lobes 3) is the DEPLOYED byte-identity baseline for
    world-forest/world-hill: every rim ring edge there is already a Delaunay edge, so recovery reports
    ZERO flips -- and with zero flips build_landmass keeps the untouched Delaunay list, so the emitted
    bytes cannot move (verified against the pre-fix build, all 5 blocks hash-identical, 2026-07-13)."""
    built = I.build_landmass(center=(344.0, -1152.0), base_radius=46.0, seed=55.0, lobes=3, n_patches=2)
    assert built["ring_edge_flips"] == 0
    assert _once_edge_violations(built) == []


def test_verify_once_edge_gate_catches_a_single_missing_face():
    """The closed-surface gate sees what the sampled-hole gate cannot: knock ONE fully-interior grass
    triangle out of a clean build's world soup -> exactly 3 once-edge violations forming 1 closed
    3-cycle, and the report goes not-clean."""
    import collections
    built = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)
    gpos, gtris = built["world"]["pos"], built["world"]["tris"]
    cnt = collections.Counter()
    for tri in gtris:
        pts = [tuple(round(gpos[v][k], 3) for k in range(3)) for v in tri]
        for q in range(3):
            cnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] += 1
    victim = None
    for tidx, tri in enumerate(gtris):
        pts = [tuple(round(gpos[v][k], 3) for k in range(3)) for v in tri]
        if all(p[1] > 1.0 for p in pts) and all(
                cnt[tuple(sorted((pts[q], pts[(q + 1) % 3])))] == 2 for q in range(3)):
            victim = tidx
            break
    assert victim is not None
    del gtris[victim]
    del built["world"]["meta"][victim]
    rep = I.verify_landmass(built)
    assert rep["open_edges"] == 3 and rep["missing_faces"] == 1 and not rep["clean"]


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


def test_landmass_open_ocean_refusal_path_writes_nothing(monkeypatch):
    """THE REFUSAL PLUMBING ONLY -- deliberately NOT the law. ``_real_block_parts`` is stubbed here,
    so this test can only observe that a non-empty occupancy report raises, names the offending
    block, and does so BEFORE the first write. It CANNOT observe what the real oracle reads, and
    for six weeks it was the whole coverage of THE OPEN-OCEAN TARGET LAW while that oracle probed
    the stock tree and nothing else (the mod-overwrite hole, closed 2026-08-27). The law itself is
    pinned against real bytes by ``test_landmass_refuses_the_real_sea_only_incident_block`` below --
    keep BOTH: this one runs with no install, that one is the oracle."""
    called = []
    monkeypatch.setattr(M, "deploy_override", lambda *a, **k: called.append(a))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: called.append(a))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    monkeypatch.setattr(I, "_real_block_parts",
                        lambda blk, **k: {"sea3": 2, "sea5": 16} if blk == (3, 1) else {})
    with pytest.raises(ValueError, match=r"REAL world block\(s\).*\(3, 1\).*sea3"):
        I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True)
    assert not called                                    # refused BEFORE any file was written


# ---- THE OPEN-OCEAN TARGET LAW, driven against the REAL stock tree (install-gated) ------------------

#: The (6,17) canvas incident's OWN block -- SEA-ONLY in stock (it loads its own prefab, which has no
#: ``Terrain`` transform for a loose override to bind to, so an island fragment deployed there silently
#: never renders). Exactly the shape the law exists to refuse, and the shape the stub above imitates.
INCIDENT_BLOCK = (6, 17)
#: A block stock genuinely leaves as open ocean -- the CALIBRATION half. Without it a ``_real_block_parts``
#: that reported occupancy for everything would satisfy the refusal assertion and make the law useless.
FREE_BLOCK = (3, 1)


def _stock_tree_ready() -> str:
    """``""`` when the real disc tree is readable, else WHY it is not (the skip reason)."""
    from ff9mapkit import config
    try:
        if not (config.find_game_path(None) / "StreamingAssets").is_dir():
            return "no StreamingAssets under the resolved FF9 install"
    except Exception as e:                               # noqa: BLE001 -- any resolution failure is a skip
        return f"the FF9 install did not resolve ({type(e).__name__}: {e})"
    return ""


def test_real_block_parts_reads_the_stock_tree_not_the_mod_folder():
    """THE ORACLE, CALIBRATED. ``_real_block_parts`` is the only thing THE OPEN-OCEAN TARGET LAW
    consults, and it reads ``transplant.world_tris`` against the STOCK disc tree -- never a mod
    folder. Pin BOTH directions on real bytes: the incident block reports its sea-only prefab, the
    free block reports nothing. A reader that answered the same for both would leave the law green
    and unarmed, which is precisely how the mod-overwrite hole survived six weeks of suites."""
    why = _stock_tree_ready()
    if why:
        warnings.warn(
            "THE OPEN-OCEAN TARGET LAW WENT UNVERIFIED in this run: " + why + ". This is the "
            "WORKTREE SKIP TRAP -- a green run here says nothing about the law. Re-run in the MAIN "
            "repo (C:/gd/Dream-World-IX/ff9mapkit), where the install resolves.", UserWarning)
        pytest.skip("stock disc tree unreadable -- " + why + " (see the warnings summary)")
    occ = I._real_block_parts(INCIDENT_BLOCK)
    assert occ, f"{INCIDENT_BLOCK} must read as an OCCUPIED real block; got {occ!r}"
    assert "terrain" not in occ, f"{INCIDENT_BLOCK} is the SEA-ONLY incident block; got {occ!r}"
    assert {"sea3", "sea4", "sea5"} <= set(occ), occ
    assert I._real_block_parts(FREE_BLOCK) == {}, "the calibration block must read as true open ocean"


def test_landmass_refuses_the_real_sea_only_incident_block(monkeypatch):
    """THE LAW ITSELF, no stub on the oracle: a radius-20 mint centred on the (6,17) incident block
    stays inside that one block, and ``landmass`` must refuse it from what the REAL stock tree says
    -- naming the block and its sea-only parts -- before a single file is written."""
    why = _stock_tree_ready()
    if why:
        warnings.warn(
            "THE OPEN-OCEAN TARGET LAW WENT UNVERIFIED in this run: " + why + ". This is the "
            "WORKTREE SKIP TRAP -- a green run here says nothing about the law. Re-run in the MAIN "
            "repo (C:/gd/Dream-World-IX/ff9mapkit), where the install resolves.", UserWarning)
        pytest.skip("stock disc tree unreadable -- " + why + " (see the warnings summary)")
    called = []
    monkeypatch.setattr(M, "deploy_override", lambda *a, **k: called.append(a))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: called.append(a))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    # the footprint must be the ONE block, or the assertion below stops naming what it thinks it names
    built = I.build_landmass(center=(I.BLOCK * INCIDENT_BLOCK[0] + I.BLOCK / 2,
                                     -I.BLOCK * INCIDENT_BLOCK[1] - I.BLOCK / 2),
                             base_radius=20.0, seed=5.0, stamps=None)
    assert sorted(built["blocks"]) == [INCIDENT_BLOCK]
    with pytest.raises(ValueError, match=r"REAL world block\(s\).*\(6, 17\).*sea4"):
        I.landmass("MOD", cell=INCIDENT_BLOCK, base_radius=20.0, seed=5.0, flat=True)
    assert not called                                    # refused BEFORE any file was written


# ---- OPT-IN rolling relief (the 2026-07-21 resurrection; world-XZ value noise) --------------------------------------

def test_relief_is_a_pure_function_of_world_xz():
    """THE FRAME FIX (the exact axis the DEAD field failed): relief is a pure function of WORLD (x, z).
    The SAME world point returns the SAME value regardless of how it was reached (a border vertex shared
    by two blocks -> one value on both sides), and it is NON-ZERO far from the world origin -- the old
    block-local field read 0.0 everywhere off block (0,0)."""
    # determinism / block-decomposition invariance: identical call == identical result
    for (x, z) in ((640.0, -608.0), (655.3, -611.7), (1200.0, -1200.0)):
        assert G.relief(x, z, seed=1234, amp=1.3) == G.relief(x, z, seed=1234, amp=1.3)
    # NON-ZERO away from the origin (the dead-relief bug produced identically 0.0 there)
    far = [abs(G.relief(x, z, seed=1234, amp=1.3))
           for (x, z) in ((672.0, -608.0), (160.0, -1120.0), (1400.0, -1250.0))]
    assert all(v > 0.05 for v in far), far
    # amp scales linearly; amp=0 is exactly flat
    assert G.relief(672.0, -608.0, seed=7, amp=0.0) == 0.0
    a = G.relief(672.0, -608.0, seed=7, amp=1.0)
    assert G.relief(672.0, -608.0, seed=7, amp=2.0) == pytest.approx(2.0 * a, abs=1e-12)


def test_relief_seed_decorrelates_the_field():
    """Different seeds give a genuinely different field (not a global offset): the value at a fixed
    world point moves, and the two fields are not equal across a sample of points."""
    pts = [(100.0 + 17 * i, -300.0 - 23 * i) for i in range(40)]
    a = [G.relief(x, z, seed=1, amp=1.3) for (x, z) in pts]
    b = [G.relief(x, z, seed=2, amp=1.3) for (x, z) in pts]
    assert a != b
    assert sum(1 for u, v in zip(a, b) if abs(u - v) > 0.05) >= 20   # broadly different, not a shift


def test_relief_fade_pins_the_shore_and_ramps_inland():
    """THE WELD-PRESERVATION fade: 0 within fade_lo of the edge (the wall-top rim never moves),
    smoothstep-ramping to exactly 1 by fade_hi."""
    assert G.relief_fade(0.0) == 0.0
    assert G.relief_fade(2.0) == 0.0                                 # at fade_lo
    assert G.relief_fade(12.0) == 1.0                                # at fade_hi
    assert G.relief_fade(50.0) == 1.0
    mid = G.relief_fade(7.0)                                         # halfway -> smoothstep(0.5)=0.5
    assert mid == pytest.approx(0.5, abs=1e-9)
    # monotonic non-decreasing
    xs = [i * 0.5 for i in range(40)]
    ws = [G.relief_fade(x) for x in xs]
    assert all(ws[i + 1] >= ws[i] - 1e-12 for i in range(len(ws) - 1))


def test_relief_off_is_byte_identical_to_flat():
    """The byte-identity PRIME GUARD: with relief_amp=0 (the default) every interior vertex sits at
    exactly land_height -- the emitted geometry is the flat mint, float-for-float (the same class of
    no-op the 2026-07-15 retire proved). Distinct Y == {0 sea-skirt, land_height}."""
    flat = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0)                 # default amp=0
    explicit = I.build_landmass(center=(224.0, -96.0), base_radius=20.0, seed=5.0, relief_amp=0.0)
    yf = sorted({round(p[1], 6) for p in flat["world"]["pos"]})
    ye = sorted({round(p[1], 6) for p in explicit["world"]["pos"]})
    assert yf == ye == [0.0, 3.2]
    # and every emitted vertex position matches float-for-float
    assert [tuple(p) for p in flat["world"]["pos"]] == [tuple(p) for p in explicit["world"]["pos"]]


def test_relief_on_stays_in_the_slope_envelope_and_gates_clean():
    """RELIEF ON at the demo site: the walkable-ground slope p99 stays under MAX_FLANK (28.6 deg, the
    measured lowland ceiling), every geometry gate is clean, and the interior actually ROLLS (Y varies)
    while the shore stays welded."""
    built = I.build_landmass(center=(672.0, -608.0), base_radius=44.0, seed=None, lobes=1, relief_amp=1.3)
    rep = I.verify_landmass(built)
    assert rep["clean"], {k: v for k, v in rep.items() if k != "placement"}
    assert rep["cracks"] == 0 and rep["down_facing"] == 0 and rep["walk_filter_fails"] == 0
    assert rep["grass_over_8u"] == 0 and rep["open_edges"] == 0 and rep["holes"] == 0
    assert 0.0 < rep["main_slope_p99"] <= I.MAX_FLANK                # rolls, but inside the envelope
    # ground actually undulates (not flat), and the rim ring is welded at exactly land_height
    from ff9mapkit.world.extract import decode_id
    gpos, gtris, gmeta = built["world"]["pos"], built["world"]["tris"], built["world"]["meta"]
    gy = [gpos[v][1] for ti, tri in enumerate(gtris) for v in tri
          if decode_id(int(round(gmeta[ti][1])))["topograph"] == 0]
    assert max(gy) - min(gy) > 1.0                                   # a real roll
    rim_xz = {(round(x, 3), round(z, 3)) for (x, z) in built["rim"]}
    for ti, tri in enumerate(gtris):
        if decode_id(int(round(gmeta[ti][1])))["topograph"] != 0:
            continue
        for v in tri:
            if (round(gpos[v][0], 3), round(gpos[v][2], 3)) in rim_xz:
                assert gpos[v][1] == 3.2                             # THE RIM WELD short-circuit


def test_relief_envelope_refuses_an_over_amplitude_mint():
    """The slope-envelope gate BITES: a wildly over-amplitude relief (amp far off the calibrated band)
    pushes the ground slope p99 past MAX_FLANK and verify_landmass goes not-clean -- the gate is real,
    not vacuous."""
    built = I.build_landmass(center=(672.0, -608.0), base_radius=44.0, seed=None, lobes=1, relief_amp=12.0)
    rep = I.verify_landmass(built)
    assert rep["main_slope_p99"] > I.MAX_FLANK
    assert not rep["clean"]


def test_relief_welds_across_a_block_border():
    """A relief mint straddling a 64u block border stays watertight: because relief is keyed on WORLD
    XZ, the two halves of a border-crossing triangle get the identical Y at the shared cut vertices
    (a block-local field would crack here) -> cracks == 0 across the multi-block split."""
    built = I.build_landmass(center=(256.0, -96.0), base_radius=26.0, seed=5.0, relief_amp=1.3)  # ON the x=256 border
    assert len(built["blocks"]) >= 2
    rep = I.verify_landmass(built)
    assert rep["cracks"] == 0 and rep["open_edges"] == 0 and rep["clean"], \
        {k: v for k, v in rep.items() if k != "placement"}


# ---- the stacked-sheet census + the VETO + the order-exception refusals (audit rec 3) -------------------------------

def test_census_flags_a_walkable_sheet_under_a_walkable_sheet():
    """THE LAWN-UNDER-HILL CLASS (BENCH-WALK-SIM's playtest pin): place() is first-hit-or-
    MISS, so a walkable sheet under a walkable sheet is invisible to it -- the engine
    grounds on the buffer-EARLIER lower sheet, and the player walks UNDER the surface.
    census() must flag it: stacked non-empty, and shadowed (an inversion) because the
    engine's pick sits below the top sheet."""
    lower = [(0.0, 1.0, 0.0), (8.0, 1.0, 0.0), (0.0, 1.0, -8.0)]
    upper = [(0.0, 5.0, 0.0), (8.0, 5.0, 0.0), (0.0, 5.0, -8.0)]
    cen = P.census([("Terrain", _bm([(lower, GRASS), (upper, GRASS)]))],
                   span=(1.0, 7.0, -7.0, -1.0), samples=4)
    assert cen["stacked"] and cen["inversions"]
    rec = cen["inversions"][0]
    assert rec["shadowed"] and rec["gap"] == 4.0
    # a single sheet is clean, and a walkable sheet over NON-walkable sea is NOT a stack
    cen1 = P.census([("Terrain", _bm([(upper, GRASS)]))], span=(1.0, 7.0, -7.0, -1.0), samples=4)
    assert cen1["stacked"] == [] and cen1["inversions"] == []
    sea_below = [(0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.0, 0.0, -8.0)]
    cen2 = P.census([("Terrain", _bm([(upper, GRASS)])), ("Sea4", _bm([(sea_below, SEA)]))],
                    span=(1.0, 7.0, -7.0, -1.0), samples=4)
    assert cen2["stacked"] == []
    # sheets 0.1u apart are a relief-seam micro-overlap, not a stack (STACK_GAP_MIN,
    # calibrated against the owner-accepted bench -- without it the gate judges the
    # ACCEPTED island defective)
    near = [(0.0, 5.1, 0.0), (8.0, 5.1, 0.0), (0.0, 5.1, -8.0)]
    cen3 = P.census([("Terrain", _bm([(upper, GRASS), (near, GRASS)]))],
                    span=(1.0, 7.0, -7.0, -1.0), samples=4)
    assert cen3["stacked"] == []


def test_all_sheets_scan_order_dedup_and_strict_boundary():
    """all_sheets: every passing intersection in SCAN order (mesh order, buffer order),
    deduped by y at 0.02; strict=True rejects a hit ON a triangle edge (a shared boundary
    LINE is not a stack)."""
    lower = [(0.0, 1.0, 0.0), (8.0, 1.0, 0.0), (0.0, 1.0, -8.0)]
    lower_dup = [(0.0, 1.01, 0.0), (8.0, 1.01, 0.0), (0.0, 1.01, -8.0)]
    upper = [(0.0, 5.0, 0.0), (8.0, 5.0, 0.0), (0.0, 5.0, -8.0)]
    ml = [("Terrain", _bm([(lower, GRASS), (lower_dup, GRASS), (upper, GRASS)]))]
    sheets = P.all_sheets(ml, 2.0, -2.0)
    assert [round(s[0], 2) for s in sheets] == [1.0, 5.0]        # dup deduped, scan order kept
    assert all(s[3] == 0 for s in sheets)
    # the probe on the hypotenuse x+z=8 of `upper`: strict rejects, lenient accepts
    on_edge = P.all_sheets([("Terrain", _bm([(upper, GRASS)]))], 4.0, -4.0)
    off_edge = P.all_sheets([("Terrain", _bm([(upper, GRASS)]))], 4.0, -4.0, strict=False)
    assert on_edge == [] and len(off_edge) == 1
    # index parity: indexed all_sheets returns the identical list
    idx = P.build_meshlist_index(ml)
    assert P.all_sheets(ml, 2.0, -2.0, index=idx) == sheets


def test_place_veto_abandons_the_whole_mesh():
    """A passing hit with idall 0x31EE (flight-only) makes the engine abandon the WHOLE
    mesh -- the query falls through to the NEXT mesh, not the next triangle."""
    veto_top = [(0.0, 5.0, 0.0), (8.0, 5.0, 0.0), (0.0, 5.0, -8.0)]
    walk_below = [(0.0, 1.0, 0.0), (8.0, 1.0, 0.0), (0.0, 1.0, -8.0)]
    ml = [("Terrain", _bm([(veto_top, P.VETO), (walk_below, GRASS)])),
          ("Sea4", _bm([(walk_below, SEA)]))]
    gy, name, idall, topo = P.place(ml, 2.0, -2.0)
    assert (gy, name, topo) == (1.0, "Sea4", 57)         # fell through to the NEXT mesh
    # and the veto tri is invisible to all_sheets
    assert all(s[2] != P.VETO for s in P.all_sheets(ml, 2.0, -2.0))


def test_census_refuses_the_registration_order_exception_blocks():
    """The two engine exceptions the simulator does not model must REFUSE, not silently
    mis-order: Water Shrine (Number 219 = block (3,9)) and prefab-driven Volcano parts."""
    shrine = _bm([(_UP, GRASS)], name="Block[3][9] Terrain", x=3, y=9)
    with pytest.raises(ValueError, match="Water Shrine"):
        P.census([("Terrain", shrine)])
    with pytest.raises(ValueError, match="[Vv]olcano"):
        P.census([("VolcanoCrater1", _bm([(_UP, GRASS)]))])


# ---- THE MOD-OVERWRITE GATE (back-ported from world-transplant, 2026-07-15) -------------------------

def _mod_tree(tmp_path, *, cell=(3, 1), disc=1, names=("Terrain.ff9mesh", "Sea4.ff9mesh", "Donor.txt")):
    """A tmp game root whose mod folder already holds deployed overrides at ``cell``."""
    bx, by = cell
    d = tmp_path / "MOD" / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    d.mkdir(parents=True, exist_ok=True)
    for n in names:
        (d / f"Block[{bx}][{by}] {n}").write_bytes(b"PRIOR-DEPLOY")
    return d


def _stub_writes(monkeypatch, called):
    monkeypatch.setattr(M, "deploy_override", lambda *a, **k: called.append(a))
    monkeypatch.setattr(M, "deploy_donor_sidecar", lambda *a, **k: called.append(a))
    monkeypatch.setattr(I, "_sea_plane", lambda disc=1, game=None: _synth_plane())
    # stock says the footprint is FREE -- which is precisely the blind spot: _real_block_parts
    # reads the REAL game tree (transplant.world_tris), never the mod folder.
    monkeypatch.setattr(I, "_real_block_parts", lambda blk, **k: {})


def test_landmass_refuses_a_footprint_another_deploy_already_owns(tmp_path, monkeypatch):
    """THE DEFECT THIS CLOSES. The OPEN-OCEAN TARGET LAW above passes here -- stock genuinely has
    nothing at (3,1) -- and the mint would still have overwritten another deploy's files. That is
    the 2026-07-15 dunes-islet incident, fixed then in ``transplant._mod_overwrite_gate`` and never
    propagated to this lane, which had copied the pre-fix shape on 2026-07-12. Live cost measured
    2026-08-27: the recorded Aldermarch mint's 19 blocks all read 'free' while six held the
    owner-confirmed R4 bench on both discs."""
    import pytest
    called = []
    _stub_writes(monkeypatch, called)
    _mod_tree(tmp_path)
    with pytest.raises(ValueError, match="already holds 3 deployed override file"):
        I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True, game=tmp_path)
    assert not called                                    # refused BEFORE any file was written


def test_landmass_allow_overwrite_waives_the_mod_gate(tmp_path, monkeypatch):
    """The hatch is deliberate and must still work -- a guard rail, not a wall."""
    called = []
    _stub_writes(monkeypatch, called)
    _mod_tree(tmp_path)
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
                   game=tmp_path, dry_run=True, allow_overwrite=True)
    assert s["report"]["clean"]


def test_mod_overwrite_gate_ignores_parked_bak_files(tmp_path, monkeypatch):
    """REGRESSION PIN. ``deploy_override`` parks ``<name>.bak-<ts>`` beside a file it overwrites, so an
    occupancy read using a bare ``startswith`` would count backups as deployed content and refuse
    forever after the first legitimate re-deploy. ``mesh.existing_overrides`` carries the extension
    filter (audit rec 6); ``transplant._mod_overwrite_gate``'s own copy did not, which is why THAT
    reader was not the one promoted -- and why the gate itself was promoted onto this one on
    2026-08-27 (pinned by ``test_transplant_mod_overwrite_gate_ignores_parked_bak_files``)."""
    called = []
    _stub_writes(monkeypatch, called)
    _mod_tree(tmp_path, names=("Terrain.ff9mesh.bak-20260101-000000",))
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
                   game=tmp_path, dry_run=True)
    assert s["report"]["clean"]                          # backups alone must NOT trip the gate


def test_mod_overwrite_gate_reads_the_WRITE_disc_not_the_read_disc(tmp_path, monkeypatch):
    """``target_disc`` (Path D's sentinel namespace) is where the bytes LAND, so that is the tree the
    gate must scan. Occupancy on the read disc is irrelevant and must not refuse."""
    import pytest
    called = []
    _stub_writes(monkeypatch, called)
    _mod_tree(tmp_path, disc=1)                          # occupied on the READ disc only
    s = I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
                   game=tmp_path, dry_run=True, target_disc=9)
    assert s["report"]["clean"]

    _mod_tree(tmp_path, disc=9)                          # now occupy the WRITE disc
    with pytest.raises(ValueError, match="on disc 9"):
        I.landmass("MOD", cell=(3, 1), base_radius=20.0, seed=5.0, flat=True,
                   game=tmp_path, target_disc=9)


def test_one_occupancy_reader_in_the_kit(tmp_path, monkeypatch):
    """``fuse``, ``island`` and ``transplant`` must not drift apart again -- the whole defect was
    THREE copies of one idea, only one of which got fixed. ``fuse`` and ``island`` call the shared
    reader by name; ``transplant``'s gate wraps it (it owns a ``Donor.txt`` re-deploy waiver the
    others have no use for), so pin the wrapper by making the shared reader observable and proving
    the gate goes through it -- a private ``iterdir`` copy would never touch this sentinel."""
    from ff9mapkit.world import fuse as F, transplant as TR
    assert F._existing_overrides is M.existing_overrides
    _mod_tree(tmp_path)
    hits = M.existing_overrides([(3, 1)], "MOD", disc=1, lod="0_1", game=tmp_path)
    assert len(hits) == 3 and all("Block[3][1] " in h for h in hits)
    asked = []
    monkeypatch.setattr(M, "existing_overrides",
                        lambda cells, mod, **kw: asked.append((sorted(cells), mod, kw)) or [])
    g = TR._mod_overwrite_gate("MOD", {(3, 1): (7, 17)}, disc=1, game=tmp_path)
    assert asked == [([(3, 1)], "MOD", {"disc": 1, "lod": "0_1", "game": tmp_path})]
    assert g["ok"] is True and g["existing"] == 0    # the sentinel said "free", so the gate must too


# ---- THE INTERIOR-BLOCK SEA (the first continent-scale mint's crash, 2026-08-28) ---------------

def _full_cover_land(x=3, y=1):
    """A Terrain mesh whose block-LOCAL XZ footprint covers the WHOLE 64u cell (two triangles with
    1u overhang) -- the fully-interior case every mint below ~r91 structurally cannot produce
    (64*sqrt(2)/2 = 45.3u half-diagonal; the r144 continent at (1520,-464) was the first to hit
    it, and it crashed the deploy loop mid-write)."""
    A, B = -1.0, 65.0
    return _bm([(((A, 3.2, B), (B, 3.2, B), (B, 3.2, A - 66.0)), 0),
                (((A, 3.2, B), (B, 3.2, A - 66.0), (A, 3.2, A - 66.0)), 0)],
               name="Block[3][1] Terrain", x=x, y=y)


def test_sea4_override_emits_hidden_stub_when_land_consumes_the_plane():
    """The empty cut must become a BLANKING STUB -- not a 0-vert mesh (write_ff9mesh's loader-range
    contract refuses vcount 0 MID-DEPLOY, stranding a partial write: the r144 mint's actual
    failure, 55 debris files) and not an omitted file (the cell's Donor.txt diverts to the donor
    prefab, and an un-overridden part FREE-RIDES the donor's own sea verbatim under our land)."""
    sea = I._sea4_override(_synth_plane(), 3, 1, frozenset(), _full_cover_land(), 3)
    assert sea.vcount == 3 and len(sea.tris) == 1          # the hidden stub's shape
    assert sea.name == "Block[3][1] Sea4"
    assert all(v[1] <= -79.0 for v in sea.chan_arrays[CH_POS])   # far below the world: renders nothing


def test_sea4_override_keeps_the_cut_plane_when_sea_remains():
    """A coastal block (land covers only part of the cell) keeps the genuine cut plane -- the stub
    replaces a FULLY consumed one only."""
    plane = _synth_plane()
    small = _bm([(((0.0, 3.2, 0.0), (8.0, 3.2, 0.0), (0.0, 3.2, -8.0)), 0)],
                name="Block[3][1] Terrain", x=3, y=1)
    sea = I._sea4_override(plane, 3, 1, frozenset(), small, 3)
    full = I._cut_plane(plane, 3, 1, frozenset(), None, label_x=3)
    assert len(sea.tris) > 1                                # genuinely the plane, not a stub
    assert len(sea.tris) >= len(full.tris) - 4              # only the land corner's tris dropped
    assert any(v[1] > -1.0 for v in sea.chan_arrays[CH_POS])


def test_sea4_override_stub_carries_the_wrapped_label():
    """On a seam-side block the stub must carry the WRAPPED label (the engine probes it), exactly
    like every other deployed part -- unwrapped col 24 deploys as Block[0]."""
    sea = I._sea4_override(_synth_plane(), 24, 1, frozenset(), _full_cover_land(x=24), 0)
    assert sea.name == "Block[0][1] Sea4" and sea.x == 0
