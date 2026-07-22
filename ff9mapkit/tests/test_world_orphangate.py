"""THE ORPHAN-DECAL GATE (``ff9mapkit.world.orphangate``) -- the comp[1] fringe-arc's proven rule set
(``studies/overworld-topography/comp1_orphan_redress.py`` --census3), productized as a carry-time
census+gate hooked into ``world-transplant``'s ``transplant()``/``transplant_region()``.

Hermetic: the classifier / lawfulness rules / redress math on synthetic (zero-SE-bytes) fixtures built
straight from ``grassland.py``'s own constants, plus the WARN/enforce/allow/redress gate composition and
the ``transplant()`` wiring (offline, ``world_tris`` stubbed). Game-gated: the deployed comp[1] region
(already hand-redressed across 3 study rounds, 2026-07-22) censuses clean (WITH the ring active, matching
``--census3`` tri-for-tri), and the PRE-redress backup bytes (``backups/comp1-redress.20260722-140044/``)
reproduce real historical orphans -- including the exact Round-3 Class-B topo/UV mismatch at cell
(305,-299).

RULE-FIDELITY re-pass (2026-07-22): the RING-CONTEXT fix (an injectable ``context_provider`` feeding a
1-block Moore ring of real deployed-or-stock terrain into BOTH the Class-A radius search and the Class-B
group statistics, matching ``--census3``'s own ``round3_generalized_census`` exactly) and the AMBIGUOUS
verdict (a cell Class A and Class B both claim -- ``--census3``'s own hard-refused/unmodelled shape --
ported as its own klass, WARNed loudly, failed under enforce, never auto-fixed by redress)."""
from __future__ import annotations

import copy

import pytest

from ff9mapkit.world import extract as X, grassland as GL, mesh as M, orphangate as OG, transplant as TR

NRM = (0.0, 1.0, 0.0)


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


def _v(x, y, z, uv=(0.5, 0.5), idall=12800.0, nrm=NRM):
    return ((float(x), float(y), float(z)), nrm, tuple(uv), (float(idall), 0.0, 0.0, 1.0))


def _quad(x0, x1, z0, z1, *, y=0.0, idall=12800.0, uv=(0.5, 0.5)):
    """Two UP-FACING tris covering [x0,x1] x [z0,z1] (world coords, z0 < z1 <= 0)."""
    a, b = _v(x0, y, z1, uv, idall), _v(x1, y, z1, uv, idall)
    c, d = _v(x1, y, z0, uv, idall), _v(x0, y, z0, uv, idall)
    return [[a, b, d], [b, c, d]]


def _fake_world(blocks):
    def fake(bx, by, part, **_k):
        return [list(t) for t in blocks.get((bx, by, part), [])]
    return fake


def _island_donor(land_x=(88.0, 104.0)):
    """Donor (1,1): a small terrain island + a full-cell sea4 (world frame x 64..128, z -128..-64).
    Every uv defaults to (0.5,0.5) -- nowhere near any STRIPS band, so it never trips the gate."""
    return {(1, 1, "terrain"): _quad(land_x[0], land_x[1], -104.0, -88.0),
            (1, 1, "sea4"): _quad(64.0, 128.0, -128.0, -64.0, idall=232.0)}


def _strip_tri(pair, row, ori, cell, *, topo, part_y=0.0):
    """ONE genuine STRIPS(pair,row,ori) decal tri at 4u ``cell`` -- 3 corners at the cell's own
    (0,0)/(1,0)/(0,1) fractional lattice points, UV computed via
    :func:`ff9mapkit.world.orphangate._strip_uv_for_pair` so it round-trips exactly through
    :func:`~ff9mapkit.world.orphangate.classify_strip_tri`. Zero Square-Enix bytes -- pure function
    of the repo's own byte-measured ``grassland.STRIPS``/``STRIP_U``/``STRIPS_V`` constants."""
    (i, j) = cell
    x0, z0 = 4.0 * i, 4.0 * j
    idall = float(X.encode_id(0, 0, topo, 0))
    corners = [(x0, z0), (x0 + 4.0, z0), (x0, z0 + 4.0)]
    return [_v(x, part_y, z, OG._strip_uv_for_pair(pair, x, z, cell, row, ori), idall)
            for (x, z) in corners]


def _mains_tri(cell, topo, *, uv=(0.05, 0.8), part_y=0.0):
    """A plain (non-STRIPS) ground tri at ``cell`` wearing ``topo`` -- context-only content: its UV
    never matters for classification (``fam`` is purely topo-keyed), only that it stays far from
    every STRIPS band (0.05,0.8 sits in grass's own MAINS rect, nowhere near a STRIP_U column)."""
    (i, j) = cell
    x0, z0 = 4.0 * i, 4.0 * j
    idall = float(X.encode_id(0, 0, topo, 0))
    return [_v(x0 + 0.5, part_y, z0 + 0.5, uv, idall), _v(x0 + 3.5, part_y, z0 + 0.5, uv, idall),
            _v(x0 + 0.5, part_y, z0 + 3.5, uv, idall)]


def _rec(cell, pair, row, ori, topo, *, block=(0, 0), tri_idx=None):
    """A hand-built orphan-decal RECORD (bypassing :func:`~ff9mapkit.world.orphangate.flatten_terrain_records`
    entirely -- for isolating :func:`row_lawfulness`/:func:`topo_consistency_defects` from the BlockMesh
    plumbing)."""
    x0, z0 = 4.0 * cell[0], 4.0 * cell[1]
    world_pts = [(x0, 0.0, z0), (x0 + 4.0, 0.0, z0), (x0, 0.0, z0 + 4.0)]
    uv = [OG._strip_uv_for_pair(pair, p[0], p[2], cell, row, ori) for p in world_pts]
    return dict(block=block, tri_idx=tri_idx or [0, 1, 2], topo=topo, fam=GL.TOPO_FAMILY.get(topo),
               world_pts=world_pts, uv=uv, cell=cell)


def _mains_rec(cell, topo, *, block=(0, 0), tri_idx=None, uv=(0.05, 0.8)):
    x0, z0 = 4.0 * cell[0], 4.0 * cell[1]
    world_pts = [(x0, 0.0, z0), (x0 + 4.0, 0.0, z0), (x0, 0.0, z0 + 4.0)]
    return dict(block=block, tri_idx=tri_idx or [900, 901, 902], topo=topo,
               fam=GL.TOPO_FAMILY.get(topo), world_pts=world_pts, uv=[uv, uv, uv], cell=cell)


def _cell_meshes(*tri_groups, block=(0, 0)):
    """Wrap tri lists into ONE 'Terrain' BlockMesh for ``block`` (block-local == world coords when
    ``block == (0, 0)`` -- ``block_world_origin(0, 0) == (0, 0)``)."""
    bm = TR._soup_block_mesh("Block[0][0] Terrain", block, list(tri_groups), disc=1, lod="0_1")
    return {block: [("Terrain", bm)]}, bm


def _orphan_fixture():
    """comp[1]'s exact shape in miniature: a desert-only region (zero grass anywhere) wearing one
    grass|desert row-2 fringe decal at cell (10,0) -- Round 10's proven defect class -- alongside its
    walkmesh partner tri (plain desert mains, same cell)."""
    pair = ("grass", "desert")
    orphan = _strip_tri(pair, 2, 0, (10, 0), topo=16)
    partner = _mains_tri((10, 0), 17)
    return _cell_meshes(orphan, partner)


# ================================================================================================ classify_strip_tri
def test_classify_strip_tri_round_trips_every_pair_row_orientation():
    for pair in GL.STRIPS:
        for row in range(GL.STRIPS[pair]["rows"]):
            for ori in GL.ORIS:
                tri = _strip_tri(pair, row, ori, (2, -3), topo=16)
                cls = OG.classify_strip_tri([v[0] for v in tri], [v[2] for v in tri], (2, -3))
                assert cls == (pair, row, ori)


def test_classify_strip_tri_none_for_plain_mains():
    tri = _mains_tri((0, 0), 0)
    assert OG.classify_strip_tri([v[0] for v in tri], [v[2] for v in tri], (0, 0)) is None


# ================================================================================================ row_lawfulness
def test_row_lawfulness_straddle_needs_genuine_same_cell_straddle():
    pair = ("grass", "desert")
    lawful, _ = OG.row_lawfulness((0, 0), pair, 1, "desert", {(0, 0): {"grass", "desert"}})
    assert lawful is True
    lawful2, detail2 = OG.row_lawfulness((0, 0), pair, 3, "desert", {(0, 0): {"desert"}})
    assert lawful2 is False and "no same-cell straddle" in detail2["missing_context"]
    # a partner family NEARBY (not in the SAME cell) never rescues a straddle row
    lawful3, _ = OG.row_lawfulness((0, 0), pair, 1, "desert", {(0, 0): {"desert"}, (1, 0): {"grass"}})
    assert lawful3 is False


def test_row_lawfulness_fringe_row_accept_radius_boundary():
    pair = ("grass", "desert")
    # partner at exactly the accept radius (2) -> lawful
    lawful, detail = OG.row_lawfulness((0, 0), pair, 2, "desert", {(2, 0): {"grass"}})
    assert lawful is True and detail["radius_needed"] == 2
    # partner at radius 3 -- DETECTED (within the 4-cell curvature bound) but beyond the accept
    # radius -> unlawful, and the detail says so (not "not found at all")
    lawful3, detail3 = OG.row_lawfulness((0, 0), pair, 2, "desert", {(3, 0): {"grass"}})
    assert lawful3 is False and detail3["radius_needed"] == 3
    assert "accept radius" in detail3["missing_context"]
    # no partner anywhere within the max band radius -> unlawful, radius_needed None
    lawful4, detail4 = OG.row_lawfulness((0, 0), pair, 0, "desert", {})
    assert lawful4 is False and detail4["radius_needed"] is None
    assert "not found within" in detail4["missing_context"]


def test_row_lawfulness_fringe_row_ambiguous_family_returns_none():
    lawful, detail = OG.row_lawfulness((0, 0), ("grass", "desert"), 0, "dunes", {})
    assert lawful is None and "ambiguous" in detail["missing_context"]


# ================================================================================================ topo_consistency_defects (Class B)
def test_topo_consistency_defects_flags_minority_topo_in_a_fringe_group():
    pair = ("grass", "desert")
    recs = [_rec((c, 0), pair, 0, 0, 16, tri_idx=[c]) for c in range(4)]
    recs.append(_rec((4, 0), pair, 0, 0, 17, tri_idx=[40]))       # the outlier: breaks the group's mode
    defects, stats = OG.topo_consistency_defects(recs)
    assert set(defects) == {(4, 0)}
    assert defects[(4, 0)][0]["topo"] == 17
    key = (pair, 0)
    assert stats[key]["mode_topo"] == 16 and stats[key]["mode_n"] == 4 and stats[key]["total_n"] == 5


def test_topo_consistency_defects_refuses_a_thin_group():
    pair = ("grass", "desert")
    recs = [_rec((c, 0), pair, 0, 0, 16, tri_idx=[c]) for c in range(3)]
    recs.append(_rec((5, 0), pair, 0, 0, 17, tri_idx=[50]))       # 4 total < FRINGE_MODE_MIN_GROUP (5)
    defects, _ = OG.topo_consistency_defects(recs)
    assert defects == {}


def test_topo_consistency_defects_skips_straddle_rows():
    pair = ("grass", "desert")
    recs = [_rec((c, 0), pair, 1, 0, 16, tri_idx=[c]) for c in range(4)]
    recs.append(_rec((4, 0), pair, 1, 0, 17, tri_idx=[40]))
    defects, _ = OG.topo_consistency_defects(recs)               # row 1 = straddle -- out of scope
    assert defects == {}


# ================================================================================================ orphan_decal_census (the reconciled A+B union)
def test_orphan_decal_census_flags_context_free_fringe_decal():
    pair = ("grass", "desert")
    recs = [_rec((10, 0), pair, 2, 0, 16), _mains_rec((10, 0), 17)]
    defects, stats = OG.orphan_decal_census(recs)
    assert set(defects) == {(10, 0)}
    hit = defects[(10, 0)][0]
    assert hit["klass"] == "A" and "partner family" in hit["missing_context"]
    assert stats["n_strip_tris"] == 1


def test_orphan_decal_census_lawful_with_partner_nearby():
    pair = ("grass", "desert")
    recs = [_rec((10, 0), pair, 2, 0, 16), _mains_rec((11, 0), 0)]   # grass 1 cell away
    defects, _ = OG.orphan_decal_census(recs)
    assert defects == {}


def test_orphan_decal_census_straddle_lawful_on_genuine_straddle_cell():
    pair = ("grass", "desert")
    recs = [_rec((10, 0), pair, 1, 0, 16), _mains_rec((10, 0), 0), _mains_rec((10, 0), 17)]
    defects, _ = OG.orphan_decal_census(recs)
    assert defects == {}


def test_orphan_decal_census_never_double_flags_a_tri_in_both_classes():
    """A tri that would trip BOTH Class A (bad context) and Class B (topo breaks its group's norm)
    is de-duplicated to exactly one hit, keyed on (block, tri_idx) -- and reads AMBIGUOUS (finding
    2's own repro shape), never silently folded into whichever class happened to be inserted first."""
    pair = ("grass", "desert")
    outlier = _rec((10, 0), pair, 0, 0, 17, tri_idx=[999])           # context-free AND off-mode
    norm = [_rec((c, 0), pair, 0, 0, 16, tri_idx=[c]) for c in range(4)]
    defects, stats = OG.orphan_decal_census(norm + [outlier])
    assert list(defects[(10, 0)]) == [d for d in defects[(10, 0)]]   # sanity: still a list
    assert len(defects[(10, 0)]) == 1                                 # not double-counted
    assert defects[(10, 0)][0]["klass"] == "AMBIGUOUS"
    assert "AMBIGUOUS" in defects[(10, 0)][0]["missing_context"]
    assert stats["n_ambiguous_cells"] == 1 and stats["ambiguous_cells"] == [[10, 0]]


# ================================================================================================ orphan_decal_census (the AMBIGUOUS verdict -- finding 2)
def test_orphan_decal_census_ambiguous_is_the_only_defect_when_context_isolates_it():
    """With the norm group given its own nearby grass partner (Class-A-lawful on its own), ONLY the
    outlier cell is a defect at all -- and it reads AMBIGUOUS (both classes independently claim it:
    Class A because grass sits > the 4-cell curvature bound away, Class B because its topo breaks
    the group's measured norm), never silently counted as plain Class A or Class B."""
    pair = ("grass", "desert")
    norm = [_rec((c, 0), pair, 0, 0, 16, tri_idx=[c]) for c in range(4)]
    grass_ctx = [_mains_rec((c, -1), 0, tri_idx=[900 + c]) for c in range(4)]   # radius-1 partner
    outlier = _rec((10, 0), pair, 0, 0, 17, tri_idx=[999])                     # nearest grass: 7 cells away
    defects, stats = OG.orphan_decal_census(norm + grass_ctx + [outlier])
    assert set(defects) == {(10, 0)}
    assert defects[(10, 0)][0]["klass"] == "AMBIGUOUS"
    assert stats["n_ambiguous_cells"] == 1 and stats["ambiguous_cells"] == [[10, 0]]


# ================================================================================================ flatten_terrain_records (the BlockMesh plumbing)
def test_flatten_terrain_records_skips_below_world_blanking_stub():
    stub = M.hidden_block_mesh(name="Block[0][0] Terrain", disc=1, x=0, y=0)
    assert OG.flatten_terrain_records({(0, 0): [("Terrain", stub)]}) == []


def test_flatten_terrain_records_reads_real_blockmesh_topo_and_cell():
    cell_meshes, _bm = _orphan_fixture()
    recs = OG.flatten_terrain_records(cell_meshes)
    assert len(recs) == 2
    topos = sorted(r["topo"] for r in recs)
    assert topos == [16, 17]
    assert all(r["cell"] == (10, 0) for r in recs)
    assert all(r["block"] == (0, 0) for r in recs)


# ================================================================================================ compute_orphan_redress (THE FIX-G SHAPE)
def test_compute_orphan_redress_retags_topo_when_it_still_carries_the_decal_topo():
    tri = _strip_tri(("grass", "desert"), 2, 0, (10, 0), topo=16)
    bm = TR._soup_block_mesh("Block[0][0] Terrain", (0, 0), [tri], disc=1, lod="0_1")
    res = OG.compute_orphan_redress(bm, 0.0, 0.0, (10, 0), [0, 1, 2], "desert")
    assert res["idall_changed"] is True
    lo_u, lo_v, hi_u, hi_v = GL.ground_main_region("desert")
    for uv in bm.uvs:
        assert lo_u - 1e-6 <= uv[0] <= hi_u + 1e-6 and lo_v - 1e-6 <= uv[1] <= hi_v + 1e-6
    for tan in bm.tangents:
        assert X.decode_id(int(round(tan[0])))["topograph"] == 17


def test_compute_orphan_redress_uv_only_when_topo_already_lawful():
    idall = float(X.encode_id(1, 5, 17, 2))                          # non-trivial event/area/flags
    tri = [_v(40.5, 0.0, 0.5, (0.05, 0.8), idall), _v(43.5, 0.0, 0.5, (0.05, 0.8), idall),
           _v(40.5, 0.0, 3.5, (0.05, 0.8), idall)]
    bm = TR._soup_block_mesh("Block[0][0] Terrain", (0, 0), [tri], disc=1, lod="0_1")
    before_tan = copy.deepcopy(bm.tangents)
    res = OG.compute_orphan_redress(bm, 0.0, 0.0, (10, 0), [0, 1, 2], "desert")
    assert res["idall_changed"] is False
    assert bm.tangents == before_tan                                  # event/area/flags AND topo untouched
    assert bm.uvs != [[0.05, 0.8]] * 3                                 # only the UV moved


def test_compute_orphan_redress_never_touches_geometry():
    tri = _strip_tri(("grass", "desert"), 2, 0, (10, 0), topo=16)
    bm = TR._soup_block_mesh("Block[0][0] Terrain", (0, 0), [tri], disc=1, lod="0_1")
    before_verts = copy.deepcopy(bm.verts)
    before_norms = copy.deepcopy(bm.normals)
    OG.compute_orphan_redress(bm, 0.0, 0.0, (10, 0), [0, 1, 2], "desert")
    assert bm.verts == before_verts and bm.normals == before_norms


# ================================================================================================ orphan_decal_gate (WARN/enforce/allow/redress, wang_carry_gate's exact shape)
def test_orphan_decal_gate_warn_default_flags_but_is_purely_read_only():
    cell_meshes, bm = _orphan_fixture()
    before_uv, before_tan = copy.deepcopy(bm.uvs), copy.deepcopy(bm.tangents)
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g["gate"] == "orphan-decals" and g["n_orphans"] == 1
    assert g["ok"] is True and g["warn"] is True and g["enforced"] is False        # WARN default
    assert bm.uvs == before_uv and bm.tangents == before_tan                       # zero mutation


def test_orphan_decal_gate_lawful_carry_is_clean_and_silent():
    pair = ("grass", "desert")
    cell_meshes, _bm = _cell_meshes(_strip_tri(pair, 2, 0, (10, 0), topo=16),
                                    _mains_tri((10, 0), 17), _mains_tri((11, 0), 0))
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g["n_orphans"] == 0 and g["ok"] is True and g["warn"] is False


def test_orphan_decal_gate_enforce_fails_allow_waives():
    cell_meshes, _bm = _orphan_fixture()
    g_enf = OG.orphan_decal_gate(cell_meshes, {(0, 0)}, enforce=True)
    assert g_enf["ok"] is False and g_enf["warn"] is False
    cell_meshes2, _bm2 = _orphan_fixture()
    g_allow = OG.orphan_decal_gate(cell_meshes2, {(0, 0)}, enforce=True, allow=True)
    assert g_allow["ok"] is True and g_allow["warn"] is False


def test_orphan_decal_gate_redress_fixes_in_memory_and_makes_an_enforced_build_clean():
    cell_meshes, bm = _orphan_fixture()
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)}, enforce=True, redress=True)
    assert g["n_redressed"] == 1 and g["n_orphans"] == 0
    assert g["ok"] is True and g["warn"] is False                    # post-redress clean even enforced
    lo_u, lo_v, hi_u, hi_v = GL.ground_main_region("desert")
    orphan_uv = bm.uvs[0]                                             # the redressed tri's first corner
    assert lo_u - 1e-6 <= orphan_uv[0] <= hi_u + 1e-6


def test_orphan_decal_gate_redress_then_re_census_reads_clean_idempotent():
    cell_meshes, _bm = _orphan_fixture()
    OG.orphan_decal_gate(cell_meshes, {(0, 0)}, redress=True)
    g2 = OG.orphan_decal_gate(cell_meshes, {(0, 0)}, enforce=True)     # no redress this time
    assert g2["n_orphans"] == 0 and g2["n_redressed"] == 0 and g2["ok"] is True


def test_orphan_decal_gate_no_strips_content_checked_zero():
    cell_meshes, _bm = _cell_meshes(_mains_tri((0, 0), 0), _mains_tri((0, 0), 17))
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g["checked"] == 0 and g["n_orphans"] == 0 and g["ok"] is True and g["warn"] is False


# ================================================================================================ orphan_decal_gate (the AMBIGUOUS verdict -- finding 2)
def test_orphan_decal_gate_ambiguous_cell_warns_enforces_and_refuses_redress():
    """Finding 2's own repro at the gate level: a cell Class A and Class B BOTH claim reads
    AMBIGUOUS -- WARNs loudly (surfaced as n_ambiguous/ambiguous_cells, distinct from the plain
    A/B cells), FAILS under --enforce-orphan-decals even with --redress-orphans, and the redress
    NEVER touches it (an unmodelled overlap state is not auto-fixed blind)."""
    pair = ("grass", "desert")
    norm = [_strip_tri(pair, 0, 0, (c, 0), topo=16) for c in range(4)]
    grass_ctx = [_mains_tri((c, -1), 0) for c in range(4)]          # radius-1 grass partner, norm cells only
    outlier = _strip_tri(pair, 0, 0, (10, 0), topo=17)              # nearest grass: 7 cells away, AND off-mode
    cell_meshes, bm = _cell_meshes(*norm, *grass_ctx, outlier)
    before_uv, before_tan = copy.deepcopy(bm.uvs), copy.deepcopy(bm.tangents)

    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)}, enforce=True, redress=True)
    assert g["n_ambiguous"] == 1
    assert g["ambiguous_cells"] == [[10, 0]]
    assert g["ok"] is False                      # never auto-cleared by redress, even enforced
    assert g["n_redressed"] == 0                  # nothing was safe to fix
    assert [10, 0] in g["cells"]                  # stays flagged after the redress attempt
    assert bm.uvs == before_uv and bm.tangents == before_tan   # zero mutation -- refused, not attempted


def test_orphan_decal_gate_ambiguous_warn_default_ok_true_but_still_flagged():
    """Without --enforce-orphan-decals the ambiguous cell still WARNs (ok stays True, matching
    every other WARN-mode finding) rather than silently vanishing."""
    pair = ("grass", "desert")
    norm = [_strip_tri(pair, 0, 0, (c, 0), topo=16) for c in range(4)]
    grass_ctx = [_mains_tri((c, -1), 0) for c in range(4)]
    outlier = _strip_tri(pair, 0, 0, (10, 0), topo=17)
    cell_meshes, _bm = _cell_meshes(*norm, *grass_ctx, outlier)
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g["ok"] is True and g["warn"] is True
    assert g["n_ambiguous"] == 1 and g["ambiguous_cells"] == [[10, 0]]


# ================================================================================================ orphan_decal_gate (RING CONTEXT -- findings 1 + 3)
def test_orphan_decal_gate_class_b_ring_extends_a_thin_local_group_to_flag_its_outlier():
    """Finding 1's own repro (verbatim shape): a synthetic desert|dunes row-0 group of 4 tris in the
    just-carried region (3 lawful topo=16, 1 defective topo=17 -- the exact shape of the real
    in-game-proven (305,-299) Class-B defect), each cell's OWN Class-A context independently
    satisfied by a dunes tile one cell away (so ONLY Class B could ever catch the topo=17 outlier).
    Scoped to cell_meshes ALONE the group is 4 members (< FRINGE_MODE_MIN_GROUP=5) -- too thin to
    judge, so the un-ringed port MISSES it. A ring supplying 2 more real topo=16 members of the SAME
    (pair,row) group grows the sample to 6 (mode 5/6 = 0.833 >= 0.8) and the outlier is caught."""
    pair = ("desert", "dunes")
    fringe = [_strip_tri(pair, 0, 0, (10 + k, 0), topo=(17 if k == 3 else 16)) for k in range(4)]
    dunes_ctx = [_mains_tri((10 + k, -1), 41) for k in range(4)]     # radius-1 dunes partner, every cell
    cell_meshes, _bm = _cell_meshes(*fringe, *dunes_ctx)
    g_no_ring = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g_no_ring["n_orphans"] == 0                # MISSED without the ring: group too thin (4 < 5)

    ring_extra = [_strip_tri(pair, 0, 0, (0, 0), topo=16), _strip_tri(pair, 0, 0, (1, 0), topo=16)]
    ring_bm = TR._soup_block_mesh("Block[9][9] Terrain", (9, 9), ring_extra, disc=1, lod="0_1")
    ring_meshes = {(9, 9): [("Terrain", ring_bm)]}
    cell_meshes2, _bm2 = _cell_meshes(*fringe, *dunes_ctx)
    g_with_ring = OG.orphan_decal_gate(cell_meshes2, {(0, 0)},
                                       context_provider=lambda region: ring_meshes)
    assert g_with_ring["n_orphans"] == 1
    assert g_with_ring["cells"] == [[13, 0]]
    assert g_with_ring["ambiguous_cells"] == []       # a clean Class-B catch, not an overlap
    assert g_with_ring["ring_blocks"] == [[9, 9]]


def test_orphan_decal_gate_ring_context_rescues_a_lawful_fringe_decal_at_the_rect_edge():
    """Finding 3's own repro: a legitimately-dressed fringe decal near the carried rect's edge whose
    partner family exists 1-2 cells away in ALREADY-DEPLOYED/STOCK terrain OUTSIDE the carry --
    --census3 reads a ring (mod override where present, else stock); the gate must too, via the
    injectable context_provider (no SE bytes needed to prove it)."""
    pair = ("grass", "desert")
    fringe = _strip_tri(pair, 2, 0, (15, 0), topo=16)      # near block (0,0)'s east edge
    cell_meshes, _bm = _cell_meshes(fringe)
    g_no_ring = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g_no_ring["n_orphans"] == 1                     # no grass anywhere in the carried region alone

    # a genuine grass tile one cell east of the fringe decal, stored in the NEIGHBOUR block (1,0) --
    # "already-deployed/stock terrain OUTSIDE the carry" (block (0,0) alone).
    ring_grass = _mains_tri((0, 0), 0)                     # block(1,0)-local cell (0,0) -> world cell (16,0)
    ring_bm = TR._soup_block_mesh("Block[1][0] Terrain", (1, 0), [ring_grass], disc=1, lod="0_1")
    ring_meshes = {(1, 0): [("Terrain", ring_bm)]}
    cell_meshes2, _bm2 = _cell_meshes(fringe)
    g_with_ring = OG.orphan_decal_gate(cell_meshes2, {(0, 0)},
                                       context_provider=lambda region: ring_meshes)
    assert g_with_ring["n_orphans"] == 0
    assert g_with_ring["ok"] is True and g_with_ring["warn"] is False
    assert g_with_ring["ring_blocks"] == [[1, 0]]


def test_orphan_decal_gate_ring_is_read_only_and_never_mutates_ring_meshes():
    """The injected ring's own BlockMesh is never touched, even under --redress-orphans -- only
    cell_meshes (the just-carried region) is ever a redress target."""
    pair = ("grass", "desert")
    fringe = _strip_tri(pair, 2, 0, (10, 0), topo=16)
    partner = _mains_tri((10, 0), 17)
    cell_meshes, _bm = _cell_meshes(fringe, partner)        # a plain orphan, context-free
    ring_bm = TR._soup_block_mesh("Block[5][5] Terrain", (5, 5), [_mains_tri((0, 0), 0)],
                                  disc=1, lod="0_1")
    before_ring_uv = copy.deepcopy(ring_bm.uvs)
    ring_meshes = {(5, 5): [("Terrain", ring_bm)]}
    OG.orphan_decal_gate(cell_meshes, {(0, 0)}, redress=True,
                         context_provider=lambda region: ring_meshes)
    assert ring_bm.uvs == before_ring_uv                    # the ring mesh is read-only, never mutated


def test_orphan_decal_gate_default_no_mod_folder_skips_ring_entirely():
    """Backward compatibility: with no mod_folder AND no context_provider (every pre-fix call site
    / test), the ring is empty and behaviour matches the pre-ring port exactly -- zero disk access."""
    cell_meshes, _bm = _orphan_fixture()
    g = OG.orphan_decal_gate(cell_meshes, {(0, 0)})
    assert g["ring_blocks"] == []
    assert g["n_orphans"] == 1                               # unchanged from the pre-ring behaviour


# ================================================================================================ default_context_provider / _ring_blocks (the ring reader itself)
def test_ring_blocks_excludes_the_region_and_clips_to_the_grid():
    ring = OG._ring_blocks({(0, 0)})
    assert (0, 0) not in ring                                # the region is never its own ring
    assert all(bx >= 0 and by >= 0 for (bx, by) in ring)      # off-grid neighbours (block (-1,*) etc) clipped
    assert set(ring) == {(0, 1), (1, 0), (1, 1)}


def test_default_context_provider_reads_a_deployed_override_over_stock(monkeypatch, tmp_path):
    """READ-ONLY, hermetic: config.find_game_path is patched to an EMPTY temp dir (never the real
    install -- the hard safety rule) and ONE synthetic ring block override is hand-written; the
    reader must pick it up without needing (or touching) any real game bytes."""
    from ff9mapkit import config
    monkeypatch.setattr(config, "find_game_path", lambda explicit=None: tmp_path)
    ring_bm = TR._soup_block_mesh("Block[1][0] Terrain", (1, 0), [_mains_tri((0, 0), 0)],
                                  disc=1, lod="0_1")
    rel = M.override_relpath(1, 1, 0, "0_1", "Terrain")
    M.write_ff9mesh(ring_bm, tmp_path / "MOD" / rel)
    out = OG.default_context_provider({(0, 0)}, mod_folder="MOD")
    assert set(out) == {(1, 0)}                              # every OTHER ring block: no override, no
                                                              # stock reachable from an empty temp dir --
                                                              # silently skipped, never fatal
    assert out[(1, 0)][0][0] == "Terrain"


def test_default_context_provider_no_install_degrades_to_empty_ring(monkeypatch):
    """No resolvable FF9 install (a bare CI checkout) degrades to "no ring" rather than raising --
    the ring is an accuracy improvement to a WARN-by-default gate, never a hard requirement."""
    from ff9mapkit import config

    def _raise(explicit=None):
        raise config.ConfigError("no install for this test")
    monkeypatch.setattr(config, "find_game_path", _raise)
    assert OG.default_context_provider({(0, 0)}, mod_folder="MOD") == {}


# ================================================================================================ transplant() wiring (offline)
def test_transplant_wiring_reports_orphan_decal_gate_and_stays_clean_on_plain_content(monkeypatch):
    """A plain island carry (no STRIPS content anywhere -- _v's default uv (0.5,0.5) is nowhere near
    any decal band) is unaffected: the new gate reports present + clean, and the existing clean
    build stays clean -- the byte-identity contract in WARN mode."""
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8)
    og = next(g for g in s["gates"] if g["gate"] == "orphan-decals")
    assert og["n_orphans"] == 0 and og["ok"] is True and og["warn"] is False
    assert s["clean"] is True


def test_transplant_kwargs_thread_to_orphan_decal_gate(monkeypatch):
    monkeypatch.setattr(TR, "world_tris", _fake_world(_island_donor()))
    s = TR.transplant("MOD", cell=(4, 2), donor=(1, 1), dry_run=True, census_samples=8,
                      enforce_orphan_decals=True)
    og = next(g for g in s["gates"] if g["gate"] == "orphan-decals")
    assert og["enforced"] is True                     # the flag reached the gate call


# ================================================================================================ CLI flag threading
def test_cli_orphan_decal_flags_thread_to_transplant(monkeypatch):
    """--enforce-orphan-decals / --allow-orphan-decals / --redress-orphans parse and reach
    TR.transplant with the right kwargs -- mirrors how --enforce-wang-carry threads through the
    same shared `kw` dict in _cmd_world_transplant."""
    from ff9mapkit import cli
    from ff9mapkit.world import transplant as TRmod
    captured = {}

    def fake_transplant(mod_folder, **kw):
        captured.update(kw)
        return dict(op="transplant", donor=[7, 17], cell=[4, 19], rot=0, shift=[0.0, 0.0],
                   window={"x": [0.0, 0.0], "z": [0.0, 0.0]}, strips=[], coverage_strips=[],
                   carried={}, clipped_out={}, blanked=[], gates=[], clean=True, dry_run=True,
                   deployed=[])

    monkeypatch.setattr(TRmod, "transplant", fake_transplant)
    rc = cli.main(["world-transplant", "--mod-folder", "MOD", "--cell", "4,19", "--donor", "7,17",
                  "--enforce-orphan-decals", "--allow-orphan-decals", "--redress-orphans",
                  "--dry-run"])
    assert rc == 0
    assert captured["enforce_orphan_decals"] is True
    assert captured["allow_orphan_decals"] is True
    assert captured["redress_orphans"] is True


def test_cli_orphan_decal_flags_default_off(monkeypatch):
    from ff9mapkit import cli
    from ff9mapkit.world import transplant as TRmod
    captured = {}

    def fake_transplant(mod_folder, **kw):
        captured.update(kw)
        return dict(op="transplant", donor=[7, 17], cell=[4, 19], rot=0, shift=[0.0, 0.0],
                   window={"x": [0.0, 0.0], "z": [0.0, 0.0]}, strips=[], coverage_strips=[],
                   carried={}, clipped_out={}, blanked=[], gates=[], clean=True, dry_run=True,
                   deployed=[])

    monkeypatch.setattr(TRmod, "transplant", fake_transplant)
    rc = cli.main(["world-transplant", "--mod-folder", "MOD", "--cell", "4,19", "--donor", "7,17",
                  "--dry-run"])
    assert rc == 0
    assert captured["enforce_orphan_decals"] is False
    assert captured["allow_orphan_decals"] is False
    assert captured["redress_orphans"] is False


# ================================================================================================ game-gated acceptance
#: the comp[1] 9-block core (== studies/overworld-topography/comp1_orphan_redress.py MINT_BLOCKS)
_COMP1_BLOCKS = [(bx, by) for bx in range(18, 21) for by in range(17, 20)]


def _comp1_deployed() -> bool:
    if not _game_ready():
        return False
    from ff9mapkit import config
    try:
        root = config.find_game_path(None) / "FF9CustomMap-world"
    except Exception:
        return False
    return (root / "FF9_Data/WorldMap/Disc1/0_1/r18/Block[19][18] Terrain.ff9mesh").is_file()


@pytest.mark.skipif(not _comp1_deployed(), reason="live FF9CustomMap-world doesn't carry the deployed "
                    "comp[1] mint (fresh/wiped install)")
def test_orphan_decal_gate_deployed_comp1_region_censuses_clean():
    """ACCEPTANCE: the deployed comp[1] region -- already hand-redressed across 3 study rounds,
    2026-07-22 ('no green, no mistiling') -- censuses ZERO orphans under the productized gate: the
    same rule set, now shipped. Runs WITH the RING active (``mod_folder`` passed -- the real
    deployed-or-stock reader) so this is the FULL fix exercised on real bytes, matching --census3's
    own ring semantics, not just the pre-ring (region-only) behaviour."""
    from ff9mapkit import config
    root = config.find_game_path(None) / "FF9CustomMap-world"
    cell_meshes = {}
    for (bx, by) in _COMP1_BLOCKS:
        p = root / f"FF9_Data/WorldMap/Disc1/0_1/r{by}/Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            cell_meshes[(bx, by)] = [("Terrain", M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by,
                                                                          part="terrain"))]
    assert len(cell_meshes) == 9
    g = OG.orphan_decal_gate(cell_meshes, set(cell_meshes), enforce=True,
                             mod_folder="FF9CustomMap-world")
    assert g["n_orphans"] == 0, g["cells"]
    assert g["n_ambiguous"] == 0, g["ambiguous_cells"]
    assert g["ok"] is True and g["warn"] is False
    assert g["ring_blocks"], "expected the real Moore ring around comp[1] to read SOME context"


def _comp1_round1_backup_present() -> bool:
    if not _game_ready():
        return False
    from pathlib import Path
    bk = (Path(__file__).resolve().parents[2] / "backups" / "comp1-redress.20260722-140044"
         / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1")
    return (bk / "r18" / "Block[19][18] Terrain.ff9mesh").is_file()


@pytest.mark.skipif(not _comp1_round1_backup_present(),
                    reason="the comp1-redress.20260722-140044 PRE-fix backup fixture is absent")
def test_orphan_decal_gate_pre_redress_backup_reproduces_real_historical_orphans():
    """The GATE WOULD HAVE CAUGHT IT: over the PRE-round-1-fix backup bytes (the real orphan-decal
    defect this whole gate productizes), the census finds real orphans -- including cell (305,-299),
    Round 3's exact Class-B topo/UV mismatch ('topo 17 breaks its own desert|dunes row-0 decal
    group's measured norm', word-for-word the study's own finding) -- and `--redress-orphans` fixes
    every one of them in memory, re-censusing clean."""
    from pathlib import Path
    bk = (Path(__file__).resolve().parents[2] / "backups" / "comp1-redress.20260722-140044"
         / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1")
    cell_meshes = {}
    for (bx, by) in ((19, 18), (20, 18), (19, 19)):
        p = bk / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        cell_meshes[(bx, by)] = [("Terrain", M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by,
                                                                       part="terrain"))]
    g = OG.orphan_decal_gate(cell_meshes, set(cell_meshes), enforce=True)
    assert g["n_orphans"] >= 1 and g["ok"] is False and g["warn"] is False
    assert [305, -299] in g["cells"]
    assert "topo 17 breaks its own" in g["detail"] or any(
        "topo 17 breaks its own" in str(v) for v in g["cells"])

    # --redress-orphans fixes every finding IN MEMORY and the re-census reads clean
    cell_meshes2 = {}
    for (bx, by) in ((19, 18), (20, 18), (19, 19)):
        p = bk / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        cell_meshes2[(bx, by)] = [("Terrain", M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by,
                                                                        part="terrain"))]
    g2 = OG.orphan_decal_gate(cell_meshes2, set(cell_meshes2), enforce=True, redress=True)
    assert g2["n_redressed"] >= 1 and g2["n_orphans"] == 0 and g2["ok"] is True
