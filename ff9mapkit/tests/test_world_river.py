"""world-river rung 0: the FRAGMENT and its two topology gates (world/river.py;
studies/terrain-malleability/watercarry/PLAN.md).

The hermetic tests run on a synthetic cove drawn as an ASCII map (4u cells, two tris each), so they collect in a fresh
worktree: a river with banks rising at a rock, a forest beside it, a beached cove walled by lip, two join columns at
the cove's mouth and an islet straddling the straight chord between them. One install-gated test pins cluster C."""
from __future__ import annotations

import math
import warnings
from collections import Counter

import numpy as np
import pytest

from ff9mapkit import config
from ff9mapkit.world import extract as X, river as R

# rows run north to south (z = -4 * row), columns west to east (x = 4 * col)
COVE = [
    "GGGGGGGGGGXXXGGGGGGGGGGG",   # 0  the rock the river rises at
    "GGGGGGGGGGKRKFFGGGGGGGGG",   # 1  the river (R) between its banks (K); a forest (F) beside it
    "GGGGGGGGGGKRKFFGGGGGGGGG",   # 2
    "GGGSSSSSSSKRKSSSSSSSSGGG",   # 3  the sand row
    "GGGLBBBBBBBRBBBBBBBBLGGG",   # 4  the beach; the mouth
    "GGGL1111111111111111LGGG",   # 5
    "GGGL2222222222222222LGGG",   # 6
    "GGGL3333333333333333LGGG",   # 7
    "GGGL3333333333333333LGGG",   # 8
    "GGGL3333333333333333LGGG",   # 9
    "GGGL3333333333333333LGGG",   # 10
    "GGGL3333331111333333LGGG",   # 11 the islet's shallow ring
    "GGGL3333331GG1333333LGGG",   # 12 the islet; the join columns sit on the row 12 / 13 line
    "LLLL5555551GG1555555LLLL",   # 13 the headlands turn
    "44444444441GG14444444444",   # 14
    "444444444411114444444444",   # 15
    "444444444444444444444444",   # 16
    "444444444444444444444444",   # 17
    "444444444444444444444444",   # 18 open sea: room for the seam to keep two cells clear of the islet's shallows
    "444444444444444444444444",   # 19
    "444444444444444444444444",   # 20
    "444444444444444444444444",   # 21
]
TOPO = {"G": 0, "L": 58, "S": 31, "F": 36, "X": 49, "K": 62}
PART = {"R": "stream", "B": "beach1", "1": "sea1", "2": "sea2", "3": "sea3", "4": "sea4", "5": "sea5"}
WET = set("RB12345")
DONOR = R.RiverDonor(name="synthetic", blocks="0,0", window=((0, 1), (0, 1)), unit_blocks=((0, 0),),
                     joins=(("W", (12.0, 3.0, -52.0), (16.0, 0.0, -52.0)),
                            ("E", (84.0, 3.0, -52.0), (80.0, 0.0, -52.0))))
ISLET = {(12, 11), (12, 12), (13, 11), (13, 12), (14, 11), (14, 12)}
STOCK_V = {False: 0.92285, True: 0.89258}                   # base row, crest row (cluster C's columns)


def grid_tris(rows, *, land_y=3.0, uv=False, shift=(0.0, 0.0)):
    """An ASCII map -> world tri dicts: each 4u cell two tris (the diagonal NW-SE); a vertex sits at y 0 when any
    cell round it is wet, else at ``land_y`` (a lip cell spans crest to base). ``uv`` gives every tri a wall-band UV
    -- U growing east and south (so the band runs W home -> W -> cove -> E -> E home, as cluster C's does), V the
    stock rows by corner role. ``shift`` moves the whole map off the 4u lattice (a real donor never sits on the
    mint's interior grid; a lattice-aligned coast is a degenerate Delaunay)."""
    H, W = len(rows), len(rows[0])
    assert all(len(r) == W for r in rows)

    def y(r, c):
        cells = [rows[rr][cc] for rr in (r - 1, r) for cc in (c - 1, c) if 0 <= rr < H and 0 <= cc < W]
        return 0.0 if any(ch in WET for ch in cells) else land_y
    out = []
    for r in range(H):
        for c in range(W):
            ch = rows[r][c]
            part = PART.get(ch, "terrain")
            topo = TOPO.get(ch, 0)
            idall = X.encode_id(topograph=topo)
            v = {(dr, dc): (4.0 * (c + dc) + shift[0], y(r + dr, c + dc), -4.0 * (r + dr) + shift[1])
                 for dr in (0, 1) for dc in (0, 1)}
            for tri in ((v[0, 0], v[0, 1], v[1, 1]), (v[0, 0], v[1, 1], v[1, 0])):
                P = np.array(tri, dtype=float)
                UV = (np.array([(0.77 + 0.002 * p[0] + 0.001 * p[2], STOCK_V[p[1] > 0]) for p in P]) if uv
                      else None)
                out.append({"blk": (int(4 * c // 64), int(4 * r // 64)), "part": part, "P": P, "uv": UV,
                            "nrm": None, "tan": None, "idall": idall, "topo": topo, "cell": (r, c)})
    return out


def _cells(f):
    return {t["cell"] for t in f.tris}


def _mesh_and_index(tris, f):
    M = R._Mesh(tris)
    inside = {id(t) for t in f.tris}
    frag = {i for i, t in enumerate(tris) if id(t) in inside}
    unit = R.river_unit(M, DONOR.unit_blocks)
    _comp, _main, islands = R.land_islands(M, unit)
    joins = {n: R.resolve_join(M, n, c, b) for n, c, b in DONOR.joins}
    return M, frag, islands, {R._ek(c, b) for c, b in joins.values()}


# ---- the fragment -------------------------------------------------------------------------------------------------

def test_fragment_takes_the_islet_whole_round_the_seaward_side():
    f = R.build_fragment(grid_tris(COVE), DONOR)
    cells = _cells(f)
    assert ISLET <= cells                                                  # the islet, whole
    assert {(r, c) for r in (11, 12, 13, 14, 15) for c in (10, 13)} <= cells   # ... with its shallow ring
    assert f.report["islands"] == [{"tris": 12, "at": [48.0, -54.0]}] and f.report["tethered"] == 1
    # the seaward boundary goes round the ring on the SEA side (below row 15), never across the chord landward
    zs = [p[2] for p in f.seaward]
    assert min(zs) <= -68.0 and max(zs) <= -52.0
    assert f.seaward[0] == (16.0, 0.0, -52.0) and f.seaward[-1] == (80.0, 0.0, -52.0)


def test_fragment_pieces_and_boundary_classes():
    f = R.build_fragment(grid_tris(COVE), DONOR)
    cells = _cells(f)
    assert {(r, 11) for r in range(1, 5)} <= cells                          # the river
    assert {(r, c) for r in range(1, 4) for c in (10, 12)} <= cells         # its banks
    assert {(r, 3) for r in range(4, 13)} | {(r, 20) for r in range(4, 13)} <= cells   # the cove's lip, to the joins
    assert not {(13, c) for c in (0, 1, 2, 3, 20, 21, 22, 23)} & cells      # the headland lip outside stays home
    assert {(3, c) for c in range(3, 10)} | {(3, c) for c in range(13, 21)} <= cells   # the sand row, whole cells
    assert not {(r, c) for r in (0, 1, 2) for c in (13, 14)} & cells       # the forest stays home
    assert not {(0, c) for c in range(10, 13)} & cells                      # the rock stays home
    bl = f.report["boundary_len"]
    assert bl["join"] == 10.0 and bl["source"] == 14.0 and "open" not in bl   # 3D: two 4x3 columns; 4 + 2 x 5
    assert bl["water"] == pytest.approx(f.report["seaward_len"], abs=0.1)
    assert f.report["F1"]["islands"] == 1 and f.report["F2"]["water_edges"] == len(f.seaward) - 1
    assert set(f.joins) == {"W", "E"} and f.joins["W"] == ((12.0, 3.0, -52.0), (16.0, 0.0, -52.0))


def test_fragment_carries_the_stock_tris_untouched():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    ids = {id(t) for t in tris}
    assert all(id(t) in ids for t in f.tris)                                # the very dicts, never copies


def test_the_tether_is_what_routes_the_boundary_seaward(monkeypatch):
    """Break-it: with no tether the cheapest path runs LANDWARD of the islet (12u shorter) and leaves it home -- the
    straight-chord trap RECON round 4 caught on cluster C, here as a quieter wrong answer."""
    monkeypatch.setattr(R, "_tether", lambda M, island, mouth: None)
    f = R.build_fragment(grid_tris(COVE), DONOR)
    assert not ISLET & _cells(f) and f.report["islands"] == []
    assert min(p[2] for p in f.seaward) >= -52.0


# ---- F1 component closure -----------------------------------------------------------------------------------------

def test_f1_refuses_a_cut_forest():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    M, frag, islands, join_edges = _mesh_and_index(tris, f)
    half = {i for i, t in enumerate(tris) if t["cell"] == (1, 13)}
    with pytest.raises(R.RiverRefused, match="F1: .*forest") as ei:
        R.gate_f1(M, frag | half, islands=islands, join_edges=join_edges)
    assert ei.value.gate == "F1" and ei.value.where == [(54.0, -6.0)]


def test_f1_refuses_a_half_cut_islet():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    M, frag, islands, join_edges = _mesh_and_index(tris, f)
    south = {i for i, t in enumerate(tris) if t["cell"] in {(14, 11), (14, 12)}}
    with pytest.raises(R.RiverRefused, match="F1: .*island"):
        R.gate_f1(M, frag - south, islands=islands, join_edges=join_edges)


def test_f1_refuses_a_lip_cut_off_the_columns():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    M, frag, islands, join_edges = _mesh_and_index(tris, f)
    gap = {i for i, t in enumerate(tris) if t["cell"] == (8, 3)}
    with pytest.raises(R.RiverRefused, match="F1: .*lip") as ei:
        R.gate_f1(M, frag - gap, islands=islands, join_edges=join_edges)
    assert (14.0, -32.0) in ei.value.where and (14.0, -36.0) in ei.value.where


def test_f1_passes_the_built_fragment():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    M, frag, islands, join_edges = _mesh_and_index(tris, f)
    assert R.gate_f1(M, frag, islands=islands, join_edges=join_edges)["islands"] == 1


# ---- F2 shore scope -----------------------------------------------------------------------------------------------

def test_f2_refuses_a_mouth_barred_by_shallows():
    barred = [row if i != 13 else "LLLL1111111111111111LLLL" for i, row in enumerate(COVE)]
    with pytest.raises(R.RiverRefused, match="F2: no deep-water route") as ei:
        R.build_fragment(grid_tris(barred), DONOR)
    assert ei.value.where[0] == (16.0, -52.0) and ei.value.where[-1] == (80.0, -52.0)


def test_f2_refuses_a_boundary_through_a_shallow():
    tris = grid_tris(COVE)
    f = R.build_fragment(tris, DONOR)
    M, frag, _islands, _je = _mesh_and_index(tris, f)
    path = [R.kk3(p) for p in f.seaward]
    w, e = path[0], path[-1]
    R.gate_f2(M, frag, seaward=path, bases=(w, e))                         # green as built
    ring = (40.0, 0.0, -44.0)                                               # a vertex of the islet's sea1 ring
    with pytest.raises(R.RiverRefused, match="F2: the seaward boundary touches a shallow") as ei:
        R.gate_f2(M, frag, seaward=path[:3] + [ring] + path[3:], bases=(w, e))
    assert (40.0, -44.0) in ei.value.where
    ring_tris = {i for i, t in enumerate(tris) if t["cell"] in {(15, 10), (15, 11)}}
    with pytest.raises(R.RiverRefused, match="F2"):                         # a sea1 tri across the fragment's edge
        R.gate_f2(M, frag - ring_tris, seaward=path, bases=(w, e))


def test_f2_refuses_a_cove_that_leaks():
    """A channel through the east headland joins the cove to the window's edge: the boundary closes nothing."""
    leaky = [row if i != 6 else row[:20] + "2222" for i, row in enumerate(COVE)]
    with pytest.raises(R.RiverRefused, match="F2: the cove leaks") as ei:
        R.build_fragment(grid_tris(leaky), DONOR)
    assert ei.value.where and ei.value.where[0][0] == 96.0


# ---- the unit, the mouth and the joins ----------------------------------------------------------------------------

def _with_w(crest, base):
    return R.RiverDonor(name="moved", blocks="0,0", window=DONOR.window, unit_blocks=DONOR.unit_blocks,
                        joins=(("W", crest, base), DONOR.joins[1]))


def test_join_must_be_a_stock_wall_column():
    with pytest.raises(R.RiverRefused, match="J0: join W is not a stock wall column"):     # the lip / grass edge
        R.build_fragment(grid_tris(COVE), _with_w((12.0, 3.0, -48.0), (12.0, 3.0, -52.0)))
    with pytest.raises(R.RiverRefused, match="J0: join W's base must touch water"):        # crest and base swapped
        R.build_fragment(grid_tris(COVE), _with_w((16.0, 0.0, -52.0), (12.0, 3.0, -52.0)))
    with pytest.raises(R.RiverRefused, match="J0: join W's base names 0 stock vertices"):  # 0.5u off any vertex
        R.build_fragment(grid_tris(COVE), _with_w((12.0, 3.0, -52.0), (16.5, 0.0, -52.0)))
    # a wall cell's diagonal is a crest-to-base wall edge too: lawful, and it moves the cut by half a cell
    f = R.build_fragment(grid_tris(COVE), _with_w((12.0, 3.0, -48.0), (16.0, 0.0, -52.0)))
    assert f.joins["W"] == ((12.0, 3.0, -48.0), (16.0, 0.0, -52.0))


def test_a_river_with_no_mouth_refuses():
    dammed = [row if i != 4 else "GGGLBBBBBBGGGBBBBBBBLGGG" for i, row in enumerate(COVE)]
    with pytest.raises(R.RiverRefused, match="U1: the river has no mouth"):
        R.build_fragment(grid_tris(dammed), DONOR)


def test_no_river_in_the_unit_blocks_refuses():
    elsewhere = R.RiverDonor(name="elsewhere", blocks="1,1", window=DONOR.window, unit_blocks=((1, 1),),
                             joins=DONOR.joins)
    with pytest.raises(R.RiverRefused, match="U0"):
        R.build_fragment(grid_tris(COVE), elsewhere)


# ---- rung 1: the outline and the join columns ---------------------------------------------------------------------

SHIFT = (0.375, 0.25)                                       # off the mint's 4u lattice, as a real donor is
#                                                             (binary fractions: float sums stay exact, as stock's do)
DONOR_UV = R.RiverDonor(name="synthetic-uv", blocks="0,0", window=DONOR.window, unit_blocks=DONOR.unit_blocks,
                        joins=tuple((n, (c[0] + SHIFT[0], c[1], c[2] + SHIFT[1]), (b[0] + SHIFT[0], b[1], b[2] + SHIFT[1]))
                                    for n, c, b in DONOR.joins))


def _cove_uv():
    return R.build_fragment(grid_tris(COVE, uv=True, shift=SHIFT), DONOR_UV)


def _u_at(s, ru0, strip_w, dens):
    return ru0 + (s * dens) % strip_w


def test_outline_on_the_synthetic_cove():
    """The kit arc from the first join round the land to the last: it leaves each join along the stock HOME coast,
    holds the whole fragment, keeps the mint's grain, never crosses itself, and lands the U phase on both joins."""
    f = _cove_uv()
    ol = R.outline(f)
    assert (ol.first, ol.last) == ("E", "W")                # the synthetic band runs W home -> W -> cove -> E -> E home
    (ce, be), (cw, bw) = f.joins["E"], f.joins["W"]
    assert ol.ring[0] == (be[0], be[2]) and ol.ring[ol.arc_end] == (bw[0], bw[2])   # the stock bases, exact
    assert ol.rim_at == {0: ce, ol.arc_end: cw}             # the stock crests, exact
    for n, i, j in (("E", 0, 1), ("W", ol.arc_end, ol.arc_end - 1)):   # each stub runs along its home coast
        b, h = np.array(ol.ring[i]), np.array(f.join_side[n]["home"])[[0, 2]]
        t, d = (h - b) / np.linalg.norm(h - b), (np.array(ol.ring[j]) - b) / np.linalg.norm(np.array(ol.ring[j]) - b)
        assert float(t @ d) > 0.999999, n
    ru0, strip_w, dens = R._wall_band()
    s_w = ol.shore_origin + R._poly_len(ol.ring[:ol.arc_end + 1])
    assert abs(_u_at(ol.shore_origin, ru0, strip_w, dens) - f.join_side["E"]["uv"]["base"][0]) < 1e-9
    assert abs(_u_at(s_w, ru0, strip_w, dens) - f.join_side["W"]["uv"]["base"][0]) < 1e-9
    rep = ol.report
    assert rep["seg_max"] <= 8.0 and rep["arc_to_land_min"] > 0.0 and 0.0 < rep["phase_added"] < strip_w / dens
    from ff9mapkit.world.island import _pip
    assert all(_pip(*t["P"].mean(axis=0)[[0, 2]], ol.ring) for t in f.tris)   # the ring holds the whole fragment


def test_outline_refuses_without_join_uvs():
    with pytest.raises(R.RiverRefused, match="J2: the fragment carries no UVs"):
        R.outline(R.build_fragment(grid_tris(COVE, shift=SHIFT), DONOR_UV))


def test_outline_refuses_a_band_running_one_way_out_of_both_joins():
    f = _cove_uv()
    js = f.join_side["W"]
    js["home_uv"] = (js["home_base_uv"][0] + 0.004, js["home_uv"][1])      # W's home coast now climbs like E's
    with pytest.raises(R.RiverRefused, match="J2: the stock band runs the same way out of both joins"):
        R.outline(f)


def test_outline_wrap_guard_refuses_a_join_at_the_band_edge():
    f = _cove_uv()
    f.join_side["W"]["uv"]["base"] = (0.7005, f.join_side["W"]["uv"]["base"][1])   # 0.12u of phase before the wrap
    with pytest.raises(R.RiverRefused, match="J2: a join's stock U sits within"):
        R.outline(f)


def hand_join(*, crest_in=1.0, last_seg=3.0, u=(0.82421875, 0.751953125), centre=(600.3, -500.2), radius=40.0):
    """A kit-like ring by hand: an arc from E (-30 deg) round the north to W (210 deg), spaced ~6u with a last
    segment of ``last_seg``, the U phase landed, closed by the straight chord. The 'stock' columns stand ``crest_in``
    inland of each base at the kit's 3.2 -- a 72.6 deg cliff, the kit's own language. -> (Outline, joins)."""
    c = np.array(centre)
    a_e, a_w = math.radians(-30.0), math.radians(210.0)
    a_l = a_w - 2.0 * math.asin(last_seg / (2.0 * radius))   # the second-last point: a chord of last_seg from W
    n = int(math.ceil(radius * (a_l - a_e) / 6.0))
    arc = [tuple(c + radius * np.array([math.cos(a), math.sin(a)])) for a in list(np.linspace(a_e, a_l, n + 1)) + [a_w]]
    ru0, strip_w, dens = R._wall_band()
    ph = {"E": u[0] - ru0, "W": u[1] - ru0}
    arc, _added, _bump = R.land_phase(arc, ph_first=ph["E"], ph_last=ph["W"], density=dens,
                                      period=strip_w / dens, outward=1.0)
    e, w = np.array(arc[0]), np.array(arc[-1])
    k = int(math.ceil(np.linalg.norm(e - w) / 6.0))
    chord = [tuple(w + (e - w) * q / k) for q in range(1, k)]
    joins = {}
    for name, b in (("E", e), ("W", w)):
        cr = b + crest_in * (c - b) / np.linalg.norm(c - b)
        joins[name] = ((float(cr[0]), 3.2, float(cr[1])), (float(b[0]), 0.0, float(b[1])))
    v = {"crest": 0.89258, "base": 0.92285}
    targets = {nm: {role: (uu, v[role]) for role in v} for nm, uu in (("E", u[0]), ("W", u[1]))}
    ol = R.Outline(ring=arc + chord, arc_end=len(arc) - 1, first="E", last="W",
                   rim_at={0: joins["E"][0], len(arc) - 1: joins["W"][0]}, shore_origin=ph["E"] / dens,
                   targets=targets)
    return ol, joins


def test_join_columns_land_exactly_on_a_hand_ring():
    """J1-J4 green: the kit's wall holds both stock columns bit for bit, U within 1e-12, V the language rows."""
    ol, joins = hand_join()
    rep = R.join_gates(R.mint(ol), ol, joins)
    for n in ("E", "W"):
        assert rep[n]["tris"] >= 1 and rep[n]["du"] < 1e-12 and rep[n]["dv"] < 5e-4, rep
        assert all(60.0 <= x <= 80.0 for x in rep[n]["slope"]), rep


def test_j1_refuses_a_join_a_hundredth_off():
    ol, joins = hand_join()
    built = R.mint(ol)
    (cx, cy, cz), base = joins["W"]
    with pytest.raises(R.RiverRefused, match="J1: no kit wall tri on the arc side holds join W"):
        R.join_gates(built, ol, {**joins, "W": ((cx + 0.01, cy, cz), base)})


def test_j2_refuses_a_wrong_u_origin():
    ol, joins = hand_join()
    ol.shore_origin += 0.5
    with pytest.raises(R.RiverRefused, match="J2: join E: the kit wall's U is 0.006250"):
        R.join_gates(R.mint(ol), ol, joins)


def test_j2_refuses_a_last_segment_across_the_band_wrap():
    """Why THE WRAP GUARD exists: W's stock U sits 4.24u of arc past the band's wrap; a 6u last segment straddles it
    and rock_uvs window-translates that tri, moving W's U to the strip's far edge. Judged on the pre-fix wall
    (``cell_lip=False``): THE CELL-CLIPPED LIP cuts a 6u segment at its lattice crossing, and here the cut happens to
    leave the column's own piece clear of the wrap -- so the defect needs the uncut segment to show, and J2 must
    still catch it."""
    ol, joins = hand_join(last_seg=6.0)
    with pytest.raises(R.RiverRefused, match="J2: join W"):
        R.join_gates(R.mint(ol, cell_lip=False), ol, joins)


def test_j3_refuses_a_v_row_off_the_stock():
    ol, joins = hand_join()
    ol.targets["W"]["crest"] = (ol.targets["W"]["crest"][0], 0.89058)
    with pytest.raises(R.RiverRefused, match="J3: join W"):
        R.join_gates(R.mint(ol), ol, joins)


def test_j4_refuses_a_column_that_is_a_ramp():
    """A stock 'lip' whose crest stands 2.5u inland is a 52 deg ramp, not a cliff: the kit wall meeting it leans off
    the stock 60-80 deg (the synthetic cove's own 4u lip cells are ramps like this)."""
    ol, joins = hand_join(crest_in=2.5)
    with pytest.raises(R.RiverRefused, match="J4: join E"):
        R.join_gates(R.mint(ol), ol, joins)


def test_j2_catches_a_crest_nearer_another_coast_vertex():
    """A crest 4u inland stands nearer the chord's first vertex than its own base, so the band's arc length at the
    crest is that vertex's: J2 sees the U jump (it is the wall's nearest-vertex rule, island.shore_s)."""
    ol, joins = hand_join(crest_in=4.0)
    with pytest.raises(R.RiverRefused, match="J2: join E"):
        R.join_gates(R.mint(ol), ol, joins)


# ---- rung 2: the composition's pieces ------------------------------------------------------------------------------

def _plan_area(tris):
    return sum(abs((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / 2 for a, b, c in tris)


def _shoelace(pts):
    return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][2] - pts[(i + 1) % len(pts)][0] * pts[i][2]
                   for i in range(len(pts)))) / 2


def test_open_zip_fans_round_a_crest_the_chains_leave_straight():
    """Two chains share both ends and leave the start in opposite directions (a 180 deg crest, like the E column's):
    one tri cannot span that, so the strip must fan -- no degenerate tri, and the tris tile the region exactly."""
    S, E = (0.0, 3.0, 0.0), (14.0, 3.0, 4.0)
    H = [S, (0.0, 3.0, 4.0), (4.0, 3.0, 8.0), (10.0, 3.0, 8.0), E]
    Rr = [S, (0.0, 2.0, -4.0), (6.0, 2.0, -6.0), (12.0, 2.0, -4.0), E]
    tris = R._zip_dp_open(H, Rr)
    assert all(min(math.dist(a, b), math.dist(b, c), math.dist(a, c)) > 0 for a, b, c in tris)
    assert all(_plan_area([t]) > 1e-6 for t in tris)
    assert _plan_area(tris) == pytest.approx(_shoelace(H + Rr[::-1][1:-1]), abs=1e-9)


def test_open_zip_routes_round_a_plan_flat_sliver():
    """A land point on the line of a hole edge (the lattice lines both arcs up) makes a plan-flat tri the shortest
    chord's choice; the steepness penalty routes round it."""
    S, E = (0.0, 3.0, 0.0), (12.0, 3.0, 0.0)
    H = [S, (4.0, 3.0, 0.0), (8.0, 3.0, 0.0), E]                      # the kit edge along z = 0
    Rr = [S, (4.0, 1.0, -0.0001), (6.0, 1.0, -3.0), (8.0, 1.0, -0.0001), E]
    nys = []
    for a, b, c in (R._up(t) for t in R._zip_dp_open(H, Rr)):
        n = np.cross(np.subtract(b, a), np.subtract(c, a))
        nys.append(abs(n[1]) / np.linalg.norm(n))
    assert min(nys) >= R.ZIP_NY_FLOOR, nys


def test_refine_zip_splits_only_interior_edges():
    """A zip across a wide gap (the E headland's case: the arcs ~12u apart, each spaced <= 8u like real arcs)."""
    S, E = (0.0, 3.0, 0.0), (20.0, 3.0, 0.0)
    H = [S, (4.0, 3.0, 6.0), (10.0, 3.0, 8.0), (16.0, 3.0, 6.0), E]
    Rr = [S, (4.0, 0.5, -6.0), (10.0, 0.5, -7.0), (16.0, 0.5, -6.0), E]
    tris, splits = R._refine_zip(R._zip_dp_open(H, Rr), max_edge=6.0)
    assert splits > 0
    own = Counter()
    for t in tris:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            own[R._ek(R.kk3(t[a]), R.kk3(t[b]))] += 1
    rim = ({R._ek(R.kk3(a), R.kk3(b)) for a, b in zip(H, H[1:])}
           | {R._ek(R.kk3(a), R.kk3(b)) for a, b in zip(Rr, Rr[1:])})
    assert {e for e, n in own.items() if n == 1} == rim                 # the arcs untouched: no T-junction
    inner = [e for e, n in own.items() if n == 2]
    assert max(math.hypot(a[0] - b[0], a[2] - b[2]) for a, b in inner) <= 6.0
    assert max(abs(a[1] - b[1]) for a, b in inner) <= R.ZIP_RISE
    assert _plan_area(tris) == pytest.approx(_plan_area(R._zip_dp_open(H, Rr)), abs=1e-9)


def test_notch_closure_carries_a_one_cell_gap():
    """A grass cell wedged between the sand row, a bank and the beach is held by the fragment on two sides: the
    notch closure carries it (both tris), so no zip strip has to fold over it."""
    gap = [row if i != 3 else row[:9] + "G" + row[10:] for i, row in enumerate(COVE)]
    f = R.build_fragment(grid_tris(gap), DONOR)
    assert f.report["notches"] == 2 and (3, 9) in _cells(f)
    assert R.build_fragment(grid_tris(COVE), DONOR).report["notches"] == 0


def test_stamp_follows_decision_1():
    from ff9mapkit.world.extract import decode_id, encode_id
    A = 14
    ground = {"part": "terrain", "idall": encode_id(event=3, area=5, topograph=31)}
    skip = {"part": "terrain", "idall": 4078}
    sea = {"part": "sea3", "idall": encode_id(event=2, area=0, topograph=55)}
    river = {"part": "stream", "idall": encode_id(area=16, topograph=51)}
    beach = {"part": "beach1", "idall": encode_id(area=19, topograph=30)}
    d = decode_id(R._stamp_carried(ground, A))
    assert (d["area"], d["event"], d["topograph"]) == (A, 0, 31)           # the island's area, the event stripped
    assert R._stamp_carried(skip, A) == 4078                                # THE BANK SKIP LAW
    d = decode_id(R._stamp_carried(sea, A))
    assert (d["area"], d["event"], d["topograph"]) == (0, 0, 55)           # water keeps its area, loses its event
    assert decode_id(R._stamp_carried(river, A))["area"] == 16
    assert decode_id(R._stamp_carried(beach, A))["area"] == A


def _blk_tri(bx, by, part):
    x, z = 64.0 * bx + 10.37, -64.0 * by - 10.21
    return {"part": part, "P": np.array([[x, 0.0, z], [x + 4, 0.0, z], [x, 0.0, z - 4]]), "uv": None, "nrm": None,
            "idall": 0}


def test_binding_plan_binds_open_ocean_to_the_prefab(monkeypatch):
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset(
        {"terrain", "object", "stream", "riverjoint", "beach1", "sea1", "sea2", "sea3", "sea4", "sea5"})})
    tris = [_blk_tri(2, 3, "terrain"), _blk_tri(2, 3, "stream"), _blk_tri(3, 3, "terrain"), _blk_tri(3, 3, "object")]
    plan = R.binding_plan(tris)
    assert plan["B1"]["ok"] and plan["C1"]["ok"] and plan["B1"]["cells"] == 2
    assert plan["cells"]["2,3"]["divert"] == list(R.DIVERT_PREFAB)
    assert "Object" in plan["cells"]["2,3"]["blanks"] and "Object" not in plan["cells"]["3,3"]["blanks"]
    assert "Stream" in plan["cells"]["3,3"]["blanks"] and "Sea4" not in plan["cells"]["2,3"]["blanks"]


def test_b1_refuses_a_cell_with_its_own_prefab_or_an_unhosted_part(monkeypatch):
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4"}),
                                                          (3, 3): frozenset({"terrain"})})
    plan = R.binding_plan([_blk_tri(2, 3, "terrain"), _blk_tri(2, 3, "stream"), _blk_tri(3, 3, "terrain")])
    assert not plan["B1"]["ok"]
    assert any("(3, 3) has its own stock prefab" in m for m in plan["B1"]["fails"])
    assert any("(2, 3) emits ['stream']" in m for m in plan["B1"]["fails"])


def test_b1_refuses_a_cell_another_deploy_already_holds(monkeypatch):
    """THE MOD-TREE OCCUPANCY READ: open ocean in the stock tree is not "free" -- a prior deploy in the target folder
    would be shadowed cell by cell. Without a folder the read is skipped (the offline composition has no target)."""
    from ff9mapkit.world import mesh as M
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4"})})
    seen = {}

    def held(cells, mod_folder, **kw):
        seen["cells"], seen["folder"] = list(cells), mod_folder
        return ["x/Block[3][3] Terrain.ff9mesh"] if (3, 3) in cells else []
    monkeypatch.setattr(M, "existing_overrides", held)
    tris = [_blk_tri(2, 3, "terrain"), _blk_tri(3, 3, "terrain")]
    assert R.binding_plan(tris)["B1"]["ok"] and not seen                    # no folder: no read
    plan = R.binding_plan(tris, mod_folder="FF9CustomMap-world")
    assert seen == {"cells": [(2, 3), (3, 3)], "folder": "FF9CustomMap-world"}
    assert not plan["B1"]["ok"] and plan["occupied"] == ["x/Block[3][3] Terrain.ff9mesh"]
    assert any("1 override file(s) already deployed" in m and "Block[3][3] Terrain.ff9mesh" in m
               for m in plan["B1"]["fails"])


def test_c1_refuses_a_part_over_budget(monkeypatch):
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4"})})
    monkeypatch.setattr(R, "PART_BUDGET", 1)
    plan = R.binding_plan([_blk_tri(2, 3, "terrain"), _blk_tri(2, 3, "terrain")])
    assert not plan["C1"]["ok"] and plan["C1"]["fails"] == ["(2, 3) Terrain: 2 tris"]


def test_translate_keeps_the_lattice_and_the_floats():
    f = R.build_fragment(grid_tris(COVE, shift=SHIFT), DONOR_UV)
    with pytest.raises(R.RiverRefused, match=r"T0: a translation of \(2, 0\) leaves the 4u water lattice"):
        R.translate(f, (2.0, 0.0))
    g = R.translate(f, (64.0, -128.0))
    assert g.joins["E"][1] == (f.joins["E"][1][0] + 64.0, 0.0, f.joins["E"][1][2] - 128.0)
    assert all(np.array_equal(a["P"] - b["P"], np.tile([64.0, 0.0, -128.0], (3, 1))) for a, b in zip(g.tris, f.tris))


def test_open_ocean_offsets_find_free_water(monkeypatch):
    taken = {(x, y): frozenset({"terrain"}) for x in range(24) for y in range(20) if not (x >= 20 and y >= 15)}
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: taken)
    blocks = [(0, 0), (1, 0), (1, 1)]
    offs = R.open_ocean_offsets(blocks)
    free = {(x, y) for x in range(20, 24) for y in range(15, 20)}
    assert offs and all({((x + dx) % 24, y + dy) for x, y in blocks} <= free for dx, dy in offs)   # columns wrap


# ---- rung 3: the written composition's pieces ---------------------------------------------------------------------

def test_seaward_boundary_is_cell_aligned_and_shore_clear():
    """THE CELL-ALIGNED SEAM: no seam edge splits a 4u cell (the cell-binned retile could not re-band the half).
    THE SHORE-CLEAR SEAM: away from the joins the seam keeps two cells clear of the islet's shallow ring, where the
    retile's shore scope would leave it un-knitted."""
    f = R.build_fragment(grid_tris(COVE), DONOR)
    S = f.seaward
    assert all(min(abs(a[0] - b[0]), abs(a[2] - b[2])) < 1e-9 for a, b in zip(S, S[1:]))
    ring = {(c, r) for r in (11, 12, 13, 14, 15) for c in (10, 11, 12, 13)}           # the islet + its sea1 ring
    for p in S:
        if min(math.hypot(p[0] - b[0], p[2] - b[2]) for b in (S[0], S[-1])) <= R.SEAM_JOIN_RELAX:
            continue
        ci, cj = math.floor(p[0] / 4.0 + 1e-9), math.floor(-p[2] / 4.0 + 1e-9)
        assert all(abs(ci - c) >= 2 or abs(cj - r) >= 2 for c, r in ring), p


def test_shore_clear_is_what_keeps_the_seam_off_the_ring(monkeypatch):
    monkeypatch.setattr(R, "SEAM_SHORE_CLEAR", 0)
    S = R.build_fragment(grid_tris(COVE), DONOR).seaward
    assert max(p[2] for p in S if p[0] > 30.0 and p[0] < 66.0) > -68.0      # it hugs the ring again


def _comp(tris):
    return R.Composition(offset=(0.0, 0.0), tris=tris, outline=None, plan={})


def _tri(part, pts, *, src="stock", tan=None, idall=0):
    return {"part": part, "P": np.asarray(pts, dtype=float), "uv": np.zeros((3, 2)), "nrm": np.tile([0.0, 1.0, 0.0],
            (3, 1)), "tan": tan, "idall": idall, "topo": 0, "src": src}


def test_part_meshes_are_block_local_and_keep_carried_tangents():
    stock = _tri("terrain", [[64 * 5 + 1.25, 2.0, -64 * 3 - 1.5], [64 * 5 + 5.25, 2.0, -64 * 3 - 1.5],
                             [64 * 5 + 1.25, 2.0, -64 * 3 - 5.5]], tan=np.array([[7.0, 0.0, 0.0, 0.0]] * 3), idall=7)
    kit = _tri("terrain", [[64 * 6 - 2.0, 3.0, -64 * 3 - 2.0], [64 * 6 + 2.0, 3.0, -64 * 3 - 2.0],
                           [64 * 6 - 2.0, 3.0, -64 * 3 - 6.0]], src="kit", idall=9)
    m = R.part_meshes(_comp([stock, kit]))
    assert sorted(m) == [(5, 3), (6, 3)]                                    # the kit tri splits at the border
    a = m[(5, 3)]["terrain"]
    assert a.chan_arrays[R.X.CH_POS][0] == [1.25, 2.0, -1.5]               # block-local, the floats exact
    assert a.chan_arrays[R.X.CH_TAN][0] == [7.0, 0.0, 0.0, 0.0]            # a carried tangent's y/z/w verbatim
    assert m[(6, 3)]["terrain"].chan_arrays[R.X.CH_TAN][0] == [9.0, 0.0, 0.0, 1.0]   # a kit tri: the lane's own


def test_sea_contacts_count_only_the_crop_pairs():
    sea3 = _blk_part((0, 0), "sea3", [[[0, 0, 0], [4, 0, 0], [0, 0, -4]]])
    sea4 = _blk_part((0, 0), "sea4", [[[4, 0, 0], [4, 0, -4], [0, 0, -4]]])
    sea5 = _blk_part((0, 0), "sea5", [[[0, 0, 0], [0, 0, -4], [-4, 0, 0]]])
    assert R.sea_contacts({(0, 0): {"sea3": sea3, "sea4": sea4, "sea5": sea5}}) == Counter({"sea3|sea4": 1})


def _blk_part(blk, part, tris_local):
    items = [(tuple((p[0] + 64.0 * blk[0], p[1], p[2] - 64.0 * blk[1], 0.0, 0.0, 0.0, 1.0, 0.0) for p in t), 0,
              (0.0, 0.0, 1.0)) for t in tris_local]
    return R._blockmesh(items, blk, part)


def _plane_cell():
    """One 4u sea cell, the NW-SE diagonal, block-local, as the (12,0) plane's cells are."""
    return _blk_part((0, 0), "sea4", [[[0, 0, 0], [4, 0, 0], [4, 0, -4]], [[0, 0, 0], [4, 0, -4], [0, 0, -4]]])


def test_kit_sea4_keeps_a_plane_tri_with_open_sea_inside_it():
    """The E join's case: the kit's wall and the carried water cover all three corners of a plane tri but not its
    middle -- the corner-only rule cut it and tore a hole in the sea; the covered-tri test keeps it."""
    L_cover = _blk_part((0, 0), "terrain", [[[-1, 3, 1], [1, 3, 1], [1, 3, -5]],              # a strip x -1..1:
                                            [[-1, 3, 1], [1, 3, -5], [-1, 3, -5]],            # (0, 0) and (0, -4)
                                            [[3, 3, -3], [5, 3, -3], [5, 3, -5]],             # a patch: (4, -4)
                                            [[3, 3, -5], [5, 3, -5], [3, 3, -3]]])
    meshes = {(0, 0): {"terrain": L_cover}}
    R.kit_sea4(meshes, plane=_plane_cell())
    # the SW tri (0,0)-(4,-4)-(0,-4) has every corner under cover and open sea at its centroid: kept, as is the NE
    # tri (its (4, 0) corner is open) -- the corner-only rule would have cut the SW one and torn a hole
    assert len(meshes[(0, 0)]["sea4"].tris) == 2
    full = _blk_part((0, 0), "terrain", [[[-1, 3, 1], [5, 3, 1], [5, 3, -5]], [[-1, 3, 1], [5, 3, -5], [-1, 3, -5]]])
    meshes = {(0, 0): {"terrain": full}}
    R.kit_sea4(meshes, plane=_plane_cell())
    assert len(meshes[(0, 0)]["sea4"].tris) == 0                            # all under land: cut


def test_knit_variants_take_each_tile_from_one_block_first_wins(monkeypatch):
    dialects = {(1, 1): {("t", "r0"): {"a": 1}}, (2, 2): {("t", "r0"): {"a": 2}, ("t", "r90"): {"a": 3}}}
    monkeypatch.setattr("ff9mapkit.world.rimretile.harvest_variants", lambda donors, **kw: dialects[donors[0]])
    v, src = R.knit_variants([(1, 1), (2, 2)])
    assert v == {("t", "r0"): {"a": 1}, ("t", "r90"): {"a": 3}} and src == {("t", "r0"): (1, 1), ("t", "r90"): (2, 2)}


def test_write_refuses_the_install(tmp_path, monkeypatch):
    monkeypatch.setattr("ff9mapkit.config.find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4"})})
    with pytest.raises(R.RiverRefused, match="B0: .* is inside the game install"):
        R.write({}, tmp_path / "FF9CustomMap-world")


def _full_cell_land(blk):
    return _blk_part(blk, "terrain", [[[0, 3, 0], [64, 3, 0], [64, 3, -64]], [[0, 3, 0], [64, 3, -64], [0, 3, -64]]])


def test_write_and_read_back_b1(tmp_path, monkeypatch):
    """A cell past the seam (unwrapped column 25) writes at its wrapped label 1: every prefab part (a blank where
    nothing is carried), the divert, and the bytes audit clean; then each B1 break-it is caught by name."""
    monkeypatch.setattr("ff9mapkit.config.find_game_path", lambda game=None: tmp_path / "game")
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4", "object"})})
    meshes = {(25, 3): {"terrain": _full_cell_land((25, 3))}}
    root = tmp_path / "scratch"
    written = R.write(meshes, root)
    names = sorted(p.name for p in written)
    assert names == ["Block[1][3] Donor.txt", "Block[1][3] Object.ff9mesh", "Block[1][3] Sea4.ff9mesh",
                     "Block[1][3] Terrain.ff9mesh"]
    au = R.audit_written(root, [(25, 3)], meshes=meshes)
    assert au["ok"] and au["census"]["1,3"]["miss"] == 0, au
    obj = root / "FF9_Data/WorldMap/Disc1/0_1/r3/Block[1][3] Object.ff9mesh"
    obj.unlink()                                                            # a free-rider: the prefab's own Object
    assert any("!= the prefab's parts" in m for m in R.audit_written(root, [(25, 3)])["fails"])
    R.write(meshes, root)
    (root / "FF9_Data/WorldMap/Disc1/0_1/r3/Block[1][3] Donor.txt").write_text("12,10")
    assert any("does not divert" in m for m in R.audit_written(root, [(25, 3)])["fails"])


def test_render_reads_a_scratch_root_across_the_seam(tmp_path):
    from ff9mapkit.world import render as RD
    site = RD.RenderSite(cells=RD.cells_around(1540.0, -200.0, radius=40.0), disc=1, game=tmp_path,
                         mod_root=tmp_path / "scratch")
    assert (24, 3) in site.cells and (23, 3) in site.cells                  # unwrapped columns kept
    p = RD.live_path(site, 24, 3, "Terrain")
    assert p == tmp_path / "scratch" / "FF9_Data/WorldMap/Disc1/0_1/r3/Block[0][3] Terrain.ff9mesh"


# ---- the verb: `world-river` --------------------------------------------------------------------------------------

def test_block_shift_takes_whole_blocks_on_the_lattice():
    assert R.block_shift((512.0, 128.0)) == (8, -2)                        # rung 4's in-game placement
    assert R.block_shift((-1024.0, 0.0)) == (-16, 0)
    with pytest.raises(R.RiverRefused, match=r"T0: a translation of \(513, 128\) leaves the 4u water lattice") as e:
        R.block_shift((513.0, 128.0))
    assert e.value.gate == "T0"
    with pytest.raises(R.RiverRefused, match="T1: the write moves whole 64u blocks only") as e:
        R.block_shift((516.0, 128.0))                                       # on the lattice, not a whole block
    assert e.value.gate == "T1"


def _game(tmp_path, monkeypatch, folders=()):
    """A bare install root: Memoria.ini stacking ``folders``, nothing else; no deploy pin, no env folder."""
    monkeypatch.setattr(config, "find_game_path", lambda game=None: tmp_path)
    monkeypatch.setattr(config, "_read_deploy_config", lambda start=None: {})
    monkeypatch.delenv("FF9_MOD_FOLDER", raising=False)
    tmp_path.mkdir(parents=True, exist_ok=True)
    if folders:
        (tmp_path / "Memoria.ini").write_text("[Mod]\nFolderNames = " + ", ".join(f'"{f}"' for f in folders) + "\n",
                                              encoding="utf-8")
    return tmp_path


def _override(game, folder, disc, x, y, part="Terrain"):
    p = game / folder / f"FF9_Data/WorldMap/Disc{disc}/0_1/r{y}/Block[{x}][{y}] {part}.ff9mesh"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"F9WM")
    return p


def test_stack_occupancy_reads_the_target_and_every_stacked_folder(tmp_path, monkeypatch):
    game = _game(tmp_path, monkeypatch, folders=("HIGH", "LOW"))
    _override(game, "HIGH", 1, 23, 12)
    _override(game, "LOW", 4, 0, 11, part="Sea4")
    _override(game, "LOW", 1, 5, 5)                                          # not a target cell
    _override(game, "MINE", 1, 0, 11, part="Donor").rename(game / "MINE/FF9_Data/WorldMap/Disc1/0_1/r11/Block[0][11] Donor.txt")
    occ = R.stack_occupancy([(23, 12), (0, 11)], "MINE")
    assert sorted(occ) == [("HIGH", 1), ("LOW", 4), ("MINE", 1)]          # the target is read though not stacked
    assert sorted(R.stack_occupancy([(23, 12), (0, 11)], "MINE", discs=(1,))) == [("HIGH", 1), ("MINE", 1)]
    assert R.stack_occupancy([(9, 9)], "MINE") == {}


def test_auto_offset_takes_the_nearest_free_open_ocean(tmp_path, monkeypatch):
    game = _game(tmp_path, monkeypatch, folders=("FF9CustomMap-world",))
    monkeypatch.setattr(R, "mint", lambda ol: {"blocks": [(16, 14), (17, 15)]})
    monkeypatch.setattr(R, "open_ocean_offsets", lambda blocks, **kw: [(8, 0), (8, -2)])
    _override(game, "FF9CustomMap-world", 4, 1, 14)                         # (17, 14) shifted (8, 0), wrapped: the
    assert R.auto_offset(None, "FF9CustomMap-world") == ((512.0, 128.0), [((8, 0), 1)])  # rectangle, not just blocks
    assert R.auto_offset(None, "FF9CustomMap-world", discs=(1,)) == ((512.0, 0.0), [])   # disc 4 not required
    _override(game, "FF9CustomMap-world", 1, 0, 12)
    with pytest.raises(R.RiverRefused, match="B1: none of the 2 nearest open-ocean placements is free"):
        R.auto_offset(None, "FF9CustomMap-world")


def _w1(where=((24, 14, 3, 14),), **kw):
    rep = {"ok": not where, "quads": 16, "after": {"seam": {"under": 0}, "contacts": {}},
           "edges_introduced": len(where), "edges_introduced_where": list(where), "unpaintable": [],
           "wang": {"incoherent": 0}}
    rep.update(kw)
    return rep


def _staged(**kw):
    rep = {"files": 132, "W1": _w1(), "B1": {"ok": True, "cells": 12, "fails": []},
           "sea_plan": {"A_ok": True, "A_submerged_tris": 0, "B_ok": False, "C_ok": True, "C_overlap_frac": 0.0389,
                        "status": "warn"}}
    rep.update(kw)
    return rep


def test_write_verdict_accepts_the_cliff_corner_step_and_nothing_else():
    from types import SimpleNamespace
    comp = SimpleNamespace(offset=(512.0, 128.0))
    assert R.write_verdict(_staged(), comp, R.CLUSTER_C) == []               # W1 red on the step only; B warns
    assert R.write_verdict(_staged(), SimpleNamespace(offset=(512.0, 0.0)), R.CLUSTER_C)[0][0] == "W1"  # moved
    assert R.write_verdict(_staged(W1=_w1(where=())), comp, R.CLUSTER_C) == []
    stray = R.write_verdict(_staged(W1=_w1(where=((24, 14, 3, 14), (24, 15, 0, 0)))), comp, R.CLUSTER_C)
    assert [g for g, _ in stray] == ["W1"] and "(24, 15, 0, 0)" in stray[0][1]
    unlisted = _w1()
    unlisted["edges_introduced"] = 9                                        # more than the report lists
    assert [g for g, _ in R.write_verdict(_staged(W1=unlisted), comp, R.CLUSTER_C)] == ["W1"]
    other = R.RiverDonor(name="other", blocks="0,0", window=((0, 0), (0, 0)), unit_blocks=(), joins=())
    assert [g for g, _ in R.write_verdict(_staged(), comp, other)] == ["W1"]   # a step is understood per donor
    under = _w1()
    under["after"] = {"seam": {"under": 2}, "contacts": {"sea3|sea4": 1}}
    assert [g for g, _ in R.write_verdict(_staged(W1=under), comp, R.CLUSTER_C)] == ["W1", "W1"]
    sea = dict(_staged()["sea_plan"], A_ok=False, A_submerged_tris=3, C_ok=False, C_overlap_frac=0.4)
    assert [g for g, _ in R.write_verdict(_staged(sea_plan=sea), comp, R.CLUSTER_C)] == ["sea_plan", "sea_plan"]
    b1 = {"ok": False, "cells": 12, "fails": ["(0,11) Donor.txt does not divert to (16, 15)"]}
    assert R.write_verdict(_staged(B1=b1), comp, R.CLUSTER_C)[0] == (
        "B1", "the written bytes do not bind: (0,11) Donor.txt does not divert to (16, 15)")


def test_promote_moves_exactly_the_staged_bytes_through_the_seam(tmp_path, monkeypatch):
    """The stage (outside the install) lands in the mod folder through deploy_override / deploy_donor_sidecar:
    every file byte for byte, one ledger row each; a file the writer does not write refuses P0 before any write."""
    import json
    game = _game(tmp_path / "game", monkeypatch)
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4", "object"})})
    stage = tmp_path / "stage"
    staged = R.write({(25, 3): {"terrain": _full_cell_land((25, 3))}}, stage)
    written = R.promote(stage, "FF9CustomMap-world")
    assert len(written) == len(staged) == 4
    for src in staged:
        dst = game / "FF9CustomMap-world" / src.relative_to(stage)
        assert dst.read_bytes() == src.read_bytes(), dst.name
    ledger = [json.loads(s) for s in (game / "FF9CustomMap-world/.ff9world.jsonl").read_text("utf-8").splitlines()]
    assert sorted(e["part"] for e in ledger) == ["Donor", "Object", "Sea4", "Terrain"]
    assert {tuple(e["cell"]) for e in ledger} == {(1, 3)}                    # the wrapped label
    scratch = tmp_path / "scratch" / "FF9CustomMap-river"                    # an absolute folder: outside any install
    assert len(R.promote(stage, str(scratch))) == 4 and (scratch / ".ff9world.jsonl").is_file()
    (stage / "notes.txt").write_text("x")
    with pytest.raises(R.RiverRefused, match="P0: the stage holds a file the writer does not write"):
        R.promote(stage, "Fresh")
    assert not (game / "Fresh").exists()


def _river_cli(tmp_path, monkeypatch, *, folders=("FF9CustomMap-world",), cells=((23, 12), (0, 11), (1, 11)),
               gates=None, staged=None):
    """The CLI with the river calls that read the install replaced by recorded-shape fakes (cluster C's numbers at
    (8,-2)); the shift, the stack read, the verdict and the report stay real. Returns the call log."""
    from types import SimpleNamespace
    _game(tmp_path, monkeypatch, folders=folders)
    calls = []
    frag = SimpleNamespace(donor=R.CLUSTER_C, tris=[], report={"tris": 1546, "unit": 330, "cove": 1026, "coast": 141},
                           boundary={"source": [((1128.5, 2.7, -914.9), (1128.9, 3.2, -917.9))], "lawn": []})
    ol = SimpleNamespace(ring=[(0.0, 0.0)] * 138)
    g = {"J": {"E": {"du": 2e-16, "dv": 4e-4, "slope": [78.21]}, "W": {"du": 2e-15, "dv": 4e-4, "slope": [72.04]}},
         "zip": {"tris": 442, "max_edge": 6.66, "max_rise": 1.39, "fails": 0, "ok": True},
         "G1": {"cracks": 0, "where": [], "ok": True}, "G3": {"near_miss": 0, "ok": True},
         "G4": {"points": 10098, "by": {"same": 10098}, "ok": True}, "G4_kit": {"points": 3341, "miss": 0, "ok": True},
         "G5": {"flipped": 0, "skipped_carried": 201, "ok": True}, "G6": {"river_points_moved": {}, "ok": True},
         "B1": {"ok": True, "cells": len(cells), "fails": []}, "C1": {"ok": True, "max": 601, "fails": []}}
    g.update(gates or {})

    def compose(f, **kw):
        calls.append(("compose", kw))
        return R.Composition(offset=tuple(float(v) for v in kw["offset"]), tris=[], outline=ol,
                             plan={"cells": {f"{x},{y}": {"divert": [16, 15]} for x, y in cells}},
                             report={"gates": g, "area": {"area": 14, "source": "open-sea"}})

    def write_composition(comp, root, **kw):
        calls.append(("stage", root))
        assert root.parent.is_dir()                                         # staged in a live temp folder
        return staged or _staged()
    monkeypatch.setattr(R, "read_window", lambda donor, game=None: calls.append(("read",)) or [])
    monkeypatch.setattr(R, "build_fragment", lambda win, donor: frag)
    monkeypatch.setattr(R, "outline", lambda f: ol)
    monkeypatch.setattr(R, "compose", compose)
    monkeypatch.setattr(R, "write_composition", write_composition)
    monkeypatch.setattr(R, "promote", lambda stage, folder, **kw: calls.append(("promote", folder)) or [])
    return calls


def test_world_river_parses():
    from ff9mapkit import cli
    ns = cli.build_parser().parse_args(["world-river", "--at", "512,128"])
    assert ns.func is cli._cmd_world_river
    assert (ns.at, ns.donor, ns.mod_folder, ns.area, ns.apron, ns.dry_run, ns.skip_mirror) == (
        "512,128", "cluster-c", None, None, True, False, False)              # the apron is the proven build's
    ns = cli.build_parser().parse_args(["world-river", "--mod-folder", "W", "--at", "auto", "--no-apron",
                                        "--dry-run", "--skip-mirror", "--area", "3", "--donor", "cluster-c"])
    assert (ns.mod_folder, ns.at, ns.apron, ns.dry_run, ns.skip_mirror, ns.area) == ("W", "auto", False, True, True, 3)
    assert cli.build_parser().parse_args(["world-river", "--at=-1024,0"]).at == "-1024,0"
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["world-river", "--mod-folder", "W"])  # --at is required
    assert cli._parse_river_at("auto") is None and cli._parse_river_at(" AUTO ") is None
    assert cli._parse_river_at("512,128") == (512.0, 128.0)
    with pytest.raises(ValueError, match="--at wants DX,DZ"):
        cli._parse_river_at("8,-2,0")


def test_world_river_dry_run_reports_every_gate(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch)
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "placement --at 512,128: block shift (8,-2), rotation 0, 3 cells (0,11) (1,11) (23,12)" in out
    for row in ("J1-J4 joins", "zip", "G1 crack", "G3 weld audit", "G4 census", "G4 kit ground", "G5 skip parity",
                "G6 water", "B1 binding", "B1 stack", "C1 budget", "B1 bytes"):
        assert any(ln.startswith(f"    {row} ") and " green " in ln for ln in out.splitlines()), row
    assert "W1 knit         understood" in out and "THE CLIFF-CORNER BAND STEP at [(24, 14, 3, 14)]" in out
    assert "sea plan        warn" in out
    assert "!! WARNING (decision 3): the river's SOURCE zips to lawn" in out and "`world-mountain` at (105, -788)" in out
    assert "would deploy 132 files into FF9CustomMap-world (+ the disc-4 mirror). Nothing written." in out
    assert [c[0] for c in calls] == ["read", "compose", "stage"]            # staged and audited, never promoted
    kw = calls[1][1]
    assert (kw["offset"], kw["apron"], kw["area"], kw["mod_folder"]) == ((512.0, 128.0), True, None,
                                                                         "FF9CustomMap-world")
    assert not calls[2][1].parent.exists()                                   # the stage is gone
    assert not calls[2][1].is_relative_to(tmp_path)                          # and it never sat in the install


def test_world_river_deploys_through_the_promotion(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch)
    monkeypatch.setenv("FF9_MOD_FOLDER", "FF9CustomMap-world")               # the env folder resolves
    assert cli.main(["world-river", "--at", "512,128", "--no-apron"]) == 0
    assert [c[0] for c in calls] == ["read", "compose", "stage", "promote"]
    assert calls[1][1]["apron"] is False and calls[3][1] == "FF9CustomMap-world"
    out = capsys.readouterr().out
    assert "deployed 0 files into FF9CustomMap-world" in out and "COUPLED, not rebuilt" in out


def test_world_river_refuses_off_the_lattice_before_reading(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch)
    for at, gate in (("513,128", "T0"), ("516,128", "T1")):
        assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", at, "--dry-run"]) == 2
        assert capsys.readouterr().err.startswith(f"world-river refused -- {gate}: ")
    assert calls == []


def test_world_river_refuses_an_occupied_cell(tmp_path, monkeypatch, capsys):
    """THE STACK READ through the CLI: a lower folder's disc-4 override on a target cell refuses B1 before the stage
    is written -- the composition's own B1 reads only the target folder's disc 1. --skip-mirror drops disc 4."""
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch, folders=("FF9CustomMap-world", "OTHER"))
    _override(tmp_path, "OTHER", 4, 0, 11, part="Sea4")
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128"]) == 2
    cap = capsys.readouterr()
    assert "world-river refused -- B1: the stack already overrides these cells" in cap.err
    assert "OTHER disc 4 (1 file(s))" in cap.err and "    B1 stack        RED" in cap.out
    assert "--remove" not in cap.err                                        # not this verb's: no way out to offer
    assert [c[0] for c in calls] == ["read", "compose"]                     # nothing staged, nothing promoted
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--dry-run",
                     "--skip-mirror"]) == 0
    _override(tmp_path, "FF9CustomMap-world", 1, 23, 12)                     # the target itself, disc 1
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--skip-mirror"]) == 2
    assert "FF9CustomMap-world disc 1: 1 file(s)" in capsys.readouterr().out


def test_world_river_refuses_a_red_gate_by_name(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch, gates={"G5": {"flipped": 177, "skipped_carried": 24, "ok": False,
                                                           "where": [(1100.0, -950.0)]}})
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128"]) == 2
    cap = capsys.readouterr()
    assert "world-river refused -- G5: red at [(1100.0, -950.0)]" in cap.err and "G5 skip parity  RED" in cap.out
    assert "stage" not in [c[0] for c in calls]
    calls[:] = []
    _river_cli(tmp_path, monkeypatch, staged=_staged(W1=_w1(where=((24, 14, 3, 15),))))
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128"]) == 2
    cap = capsys.readouterr()
    assert "world-river refused -- W1: 1 contradicting band edge(s) home lacks" in cap.err
    assert "W1 knit         RED" in cap.out


def test_world_river_needs_a_folder_and_a_river_donor(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path, monkeypatch)
    assert cli.main(["world-river", "--at", "512,128", "--dry-run"]) == 2   # no flag, env or pin: no shared default
    assert "It never falls back to the shared FF9CustomMap" in capsys.readouterr().err
    monkeypatch.setattr(config, "_read_deploy_config", lambda start=None: {"mod_folder": "PINNED"})
    assert cli.main(["world-river", "--at", "512,128", "--dry-run"]) == 0
    assert calls[1][1]["mod_folder"] == "PINNED"
    capsys.readouterr()
    assert cli.main(["world-river", "--mod-folder", "W", "--donor", "cluster-d", "--at", "512,128"]) == 2
    assert "'cluster-d' is not a river donor" in capsys.readouterr().err


# ---- `world-river --remove`: the verb's own deploy taken back out -------------------------------------------------

RIVER_CELLS = ((23, 12), (0, 11), (1, 11))                                   # _river_cli's three cells, wrapped
_PROMOTE = R.promote                                                          # _river_cli stubs it; a deploy needs the seam


def test_ledger_verb_skips_the_top_level_options():
    """A recorded argv may lead with the top-level `--game PATH` / `--mod-folder NAME`; the pinned option list is the
    parser's own (a new top-level value option would make every row's verb its value)."""
    import argparse
    from ff9mapkit import cli
    from ff9mapkit.world import mesh as M
    assert M.ledger_verb(["world-river", "--at", "512,128"]) == "world-river"
    assert M.ledger_verb(["--game", "D:/ff9", "--mod-folder", "world-island", "world-river"]) == "world-river"
    assert M.ledger_verb(["--game=D:/ff9", "world-mirror"]) == "world-mirror"
    assert M.ledger_verb(None) is None and M.ledger_verb(["--version"]) is None
    top = {s for a in cli.build_parser()._actions if type(a) is argparse._StoreAction for s in a.option_strings}
    assert top == set(M._TOP_VALUE_OPTS)


def test_ledger_shift_reads_the_placement():
    assert R.ledger_shift(["world-river", "--at", "512,128"]) == (8, -2)
    assert R.ledger_shift(["world-river", "--at=-1024,0"]) == (-16, 0)
    assert R.ledger_shift(["world-river", "--at", "1,1", "--at", "512,128"]) == (8, -2)   # the last wins, as argparse
    for argv in (["world-river", "--at", "auto"], ["world-river", "--at", "513,128"], ["world-river"], None):
        assert R.ledger_shift(argv) is None
    assert R._same_shift((8, -2), (-16, -2)) and not R._same_shift((8, -2), (8, -1))   # 24 columns is no shift
    row = {"argv": ["world-river", "--mod-folder", "C:/scratch/" + "x" * 120, "--at", "512,128"], "utc": "T"}
    assert R._row_who(row).endswith("--at 512,128` at T") and " ... " in R._row_who(row)  # a long folder hides nothing


def _deploy_river(tmp_path, monkeypatch, folder="FF9CustomMap-world", *, at="512,128", cells=RIVER_CELLS,
                  verb="world-river", mirror=True):
    """A real deploy of three cells into ``<game>/<folder>``: the writer's files staged outside the install, promoted
    through the ledgered seam, then mirrored to disc 4 by the real mirror (no stock parts there: open ocean). The
    ledger rows carry ``verb ... --at at``. Returns ``{disc-relative path: bytes}`` of everything deployed."""
    from ff9mapkit.world import discmirror as DM, mesh as M
    game = config.find_game_path(None)
    monkeypatch.setattr(R.X, "block_parts", lambda **kw: {R.DIVERT_PREFAB: frozenset({"terrain", "sea4", "object"})})
    monkeypatch.setattr(DM, "_real_parts", lambda disc, lod="0_1", game=None: {})
    monkeypatch.setattr(M, "_DEPLOY_ARGV", [verb, "--mod-folder", folder, "--at", at])
    stage = tmp_path / f"stage-{verb}-{at}"
    R.write({c: {"terrain": _full_cell_land(c)} for c in cells}, stage)
    _PROMOTE(stage, folder)
    if mirror:
        DM.mirror(folder, cells=set(cells), atomic=True, log=lambda *a: None)
    root = game / folder / "FF9_Data/WorldMap"
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("Block*") if ".bak-" not in p.name}


def _deployed(game, folder="FF9CustomMap-world"):
    root = game / folder / "FF9_Data/WorldMap"
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("Block*") if ".bak-" not in p.name) \
        if root.is_dir() else []


def _ledger(game, folder="FF9CustomMap-world"):
    from ff9mapkit.world import mesh as M
    return M.read_ledger(game / folder)


def test_world_river_remove_takes_its_own_deploy_out_and_the_verb_redeploys(tmp_path, monkeypatch, capsys):
    """The gap this closes: B1 refused the verb's own earlier deploy, so nothing could re-run it. --remove deletes
    exactly the ledger-owned files (disc 1 and the disc-4 mirror), parks each first, ledgers each; then the ordinary
    run passes the stack read on the same cells, and a second deploy + remove round-trips."""
    from ff9mapkit import cli
    calls = _river_cli(tmp_path / "game", monkeypatch)
    game = tmp_path / "game"
    before = _deploy_river(tmp_path, monkeypatch)
    assert len(before) == 24 and sum(k.startswith("Disc4/") for k in before) == 12   # 4 files x 3 cells x 2 discs
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--dry-run"]) == 2
    assert "`world-river --remove --at 512,128`" in capsys.readouterr().err  # B1 names the way out

    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove",
                     "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "3 cells (0,11) (1,11) (23,12) in FF9CustomMap-world, disc(s) 1, 4" in out
    assert "would remove 24 files (disc 1: 12, disc 4: 12), every one this verb's by the ledger. Nothing removed." in out
    assert len(_deployed(game)) == 24
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove"]) == 0
    out = capsys.readouterr().out
    assert "removed 24 files from FF9CustomMap-world (disc 1: 12, disc 4: 12)" in out
    assert "To redeploy here: world-river --mod-folder FF9CustomMap-world --at 512,128" in out
    assert _deployed(game) == [] and R.stack_occupancy(list(RIVER_CELLS), "FF9CustomMap-world") == {}
    baks = sorted((game / "FF9CustomMap-world/FF9_Data/WorldMap").rglob("*.bak-*"))
    assert len(baks) == 24                                                   # every byte parked, beside itself
    for b in baks:
        rel = b.relative_to(game / "FF9CustomMap-world/FF9_Data/WorldMap").as_posix().split(".bak-")[0]
        assert b.read_bytes() == before[rel], rel
    gone = [e for e in _ledger(game) if e.get("op") == "remove"]
    assert len(gone) == 24 and all(e["sha256"] is None and e["argv"][-1] == "--remove" for e in gone)
    assert {(e["write_disc"], e["part"]) for e in gone} == {(d, p) for d in (1, 4)
                                                             for p in ("Terrain", "Sea4", "Object", "Donor")}
    monkeypatch.setattr(cli, "find_game_path", lambda g=None: game)         # bound at import: pin it too
    assert cli.main(["world-ledger", "--mod-folder", "FF9CustomMap-world"]) == 0
    assert "kit " in (out := capsys.readouterr().out) and "REMOVED" in out   # the reader names the row for what it is

    calls[:] = []                                                            # the ordinary run, same cells: free now
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--dry-run"]) == 0
    assert [c[0] for c in calls] == ["read", "compose", "stage"]
    assert _deploy_river(tmp_path, monkeypatch) == before                    # the seam takes it back: no refusal
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove"]) == 0
    assert _deployed(game) == []


def test_world_river_remove_scratch_folder_and_skip_mirror(tmp_path, monkeypatch, capsys):
    """An absolute scratch folder works as the deploy does; --skip-mirror leaves disc 4 exactly as it is."""
    from ff9mapkit import cli
    _river_cli(tmp_path / "game", monkeypatch)
    scratch = str(tmp_path / "scratch" / "FF9CustomMap-river")
    _deploy_river(tmp_path, monkeypatch, scratch)
    assert cli.main(["world-river", "--mod-folder", scratch, "--at", "512,128", "--remove", "--skip-mirror"]) == 0
    out = capsys.readouterr().out
    assert "removed 12 files" in out and "disc 4 left as it is (--skip-mirror)" in out
    assert _deployed(tmp_path / "game", scratch) == sorted(f"Disc4/0_1/r{y}/Block[{x}][{y}] {p}"
                                                           for x, y in RIVER_CELLS for p in ("Donor.txt",
                                                           "Object.ff9mesh", "Sea4.ff9mesh", "Terrain.ff9mesh"))
    assert cli.main(["world-river", "--mod-folder", scratch, "--at", "512,128", "--remove"]) == 0  # the rest
    assert _deployed(tmp_path / "game", scratch) == []


def _remove_refused(cli, capsys, folder="FF9CustomMap-world", *extra, at="512,128"):
    assert cli.main(["world-river", "--mod-folder", folder, f"--at={at}", "--remove", *extra]) == 2
    return capsys.readouterr().err


def test_world_river_remove_refuses_foreign_bytes_and_removes_nothing(tmp_path, monkeypatch, capsys):
    """Break-it per ownership refusal (R1): a hand edit, a file no row covers, another verb's last write, another
    placement's deploy, bytes put back after a removal -- each refuses the WHOLE removal, every file stays."""
    from ff9mapkit import cli
    from ff9mapkit.world import mesh as M
    _river_cli(tmp_path / "game", monkeypatch)
    game = tmp_path / "game"
    disc1 = game / "FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1"
    before = _deploy_river(tmp_path, monkeypatch)

    def unchanged():
        assert len(_deployed(game)) == 24 and not [e for e in _ledger(game) if e.get("op") == "remove"]
        assert not list((game / "FF9CustomMap-world").rglob("*.bak-*"))

    sea4 = disc1 / "r11/Block[0][11] Sea4.ff9mesh"                           # 1. a hand edit on disc 1
    sea4.write_bytes(before["Disc1/0_1/r11/Block[0][11] Sea4.ff9mesh"] + b"\0")
    err = _remove_refused(cli, capsys)
    assert err.startswith("world-river refused -- R1: 1 file(s) on the target cells are not this verb's deploy")
    assert "Disc1 Block[0][11] Sea4.ff9mesh: its bytes are not the last ledgered write" in err
    sea4.write_bytes(before["Disc1/0_1/r11/Block[0][11] Sea4.ff9mesh"])
    unchanged()

    d4 = game / "FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r12/Block[23][12] Terrain.ff9mesh"
    d4.write_bytes(b"F9WM")                                                  # 2. a hand edit on the mirror only
    assert "Disc4 Block[23][12] Terrain.ff9mesh: its bytes are not the last" in _remove_refused(cli, capsys)
    d4.write_bytes(before["Disc4/0_1/r12/Block[23][12] Terrain.ff9mesh"])
    unchanged()

    extra = disc1 / "r11/Block[1][11] Stream.ff9mesh"                        # 3. a file no ledger row covers
    extra.write_bytes(b"F9WM")
    assert "Disc1 Block[1][11] Stream.ff9mesh: no ledger row" in _remove_refused(cli, capsys)
    extra.unlink()
    unchanged()

    obj = disc1 / "r12/Block[23][12] Object.ff9mesh"                         # 4. another verb's ledgered write
    monkeypatch.setattr(M, "_DEPLOY_ARGV", ["world-island", "--mod-folder", "FF9CustomMap-world"])
    obj.write_bytes(before["Disc1/0_1/r12/Block[23][12] Object.ff9mesh"] + b"x")
    M.record_ledger_write(obj, cell=(23, 12), part="Object", write_disc=1)
    err = _remove_refused(cli, capsys)
    assert "R1: 1 file(s)" in err
    assert "Disc1 Block[23][12] Object.ff9mesh: another deploy's: last written by `world-island --mod-folder" in err
    unchanged()


def test_world_river_remove_refuses_another_placement_and_returned_bytes(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    _river_cli(tmp_path / "game", monkeypatch)
    game = tmp_path / "game"
    _deploy_river(tmp_path, monkeypatch, at="1024,128")                     # 5. world-river's, another placement
    err = _remove_refused(cli, capsys)
    assert "R1: 24 file(s)" in err and "another deploy's: last written by `world-river --mod-folder " \
                                       "FF9CustomMap-world --at 1024,128`" in err
    assert len(_deployed(game)) == 24
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "1024,128", "--remove"]) == 0
    capsys.readouterr()

    before = _deploy_river(tmp_path, monkeypatch, at="auto")                 # auto does not say: B1 is the guard
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove"]) == 0
    capsys.readouterr()
    bak = next((game / "FF9CustomMap-world/FF9_Data/WorldMap/Disc1/0_1/r11").glob("Block[[]0][[]11] Sea4*.bak-*"))
    back = bak.with_name(bak.name.split(".bak-")[0])                         # 6. a parked copy put back by hand
    back.write_bytes(bak.read_bytes())
    assert back.read_bytes() == before["Disc1/0_1/r11/Block[0][11] Sea4.ff9mesh"]
    err = _remove_refused(cli, capsys)
    assert "R1: 1 file(s)" in err and "the ledger last REMOVED it; these bytes came back without a row" in err
    assert back.is_file()


def test_world_river_remove_refuses_nothing_auto_and_off_lattice(tmp_path, monkeypatch, capsys):
    from ff9mapkit import cli
    calls = _river_cli(tmp_path / "game", monkeypatch)
    err = _remove_refused(cli, capsys)                                        # 7. nothing deployed there
    assert err.startswith("world-river refused -- R0: nothing to remove: FF9CustomMap-world holds no override")
    calls[:] = []
    assert "needs the placement the deploy printed (--at DX,DZ), not auto" in _remove_refused(cli, capsys, at="auto")
    assert _remove_refused(cli, capsys, at="513,128").startswith("world-river refused -- T0: ")
    assert calls == []                                                      # 8./9. refused before the first read


def test_world_river_remove_stops_when_a_file_changes_under_it(tmp_path, monkeypatch, capsys):
    """10. A concurrent write between the ownership read and a delete stops the removal, naming how far it got; the
    rest stay ours by the ledger, so a re-run finishes the job."""
    from ff9mapkit import cli
    from ff9mapkit.world import mesh as M
    _river_cli(tmp_path / "game", monkeypatch)
    game = tmp_path / "game"
    _deploy_river(tmp_path, monkeypatch)
    victim = game / "FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r12/Block[23][12] Terrain.ff9mesh"
    ours, real_park = victim.read_bytes(), M.park_backup                     # the victim is the last file reached

    def park(dest):
        victim.write_bytes(b"F9WM")                                          # another session, mid-removal
        return real_park(dest)
    monkeypatch.setattr(M, "park_backup", park)
    assert "R1: Disc4 Block[23][12] Terrain.ff9mesh changed after the ownership read (another session?): stopped " \
           "after removing 23 of 24 file(s)" in _remove_refused(cli, capsys)
    assert _deployed(game) == ["Disc4/0_1/r12/Block[23][12] Terrain.ff9mesh"]
    monkeypatch.setattr(M, "park_backup", real_park)
    assert "Disc4 Block[23][12] Terrain.ff9mesh: its bytes are not the last ledgered write" in _remove_refused(
        cli, capsys)                                                         # the other session's bytes: not ours
    victim.write_bytes(ours)                                                 # it put them back: the re-run finishes
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove"]) == 0
    assert "removed 1 file from" in capsys.readouterr().out and _deployed(game) == []


def test_world_river_remove_leaves_other_stacked_folders_and_the_redeploy_still_refuses_them(tmp_path, monkeypatch,
                                                                                               capsys):
    """Only the target folder is touched: a lower folder's override on a target cell stays (named), and the next
    deploy's stack read refuses it exactly as before. A later `world-mirror` re-copy of our bytes stays ours."""
    from ff9mapkit import cli
    from ff9mapkit.world import mesh as M
    calls = _river_cli(tmp_path / "game", monkeypatch, folders=("FF9CustomMap-world", "OTHER"))
    game = tmp_path / "game"
    _deploy_river(tmp_path, monkeypatch)
    theirs = _override(game, "OTHER", 4, 0, 11, part="Sea4")
    d4 = game / "FF9CustomMap-world/FF9_Data/WorldMap/Disc4/0_1/r11/Block[1][11] Terrain.ff9mesh"
    monkeypatch.setattr(M, "_DEPLOY_ARGV", ["world-mirror", "--mod-folder", "FF9CustomMap-world"])
    M.record_ledger_write(d4, cell=(1, 11), part="Terrain", write_disc=4, read_disc=1)   # a world-mirror re-copy
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128", "--remove"]) == 0
    out = capsys.readouterr().out
    assert "removed 24 files" in out
    assert "NOTE: OTHER disc 4 also overrides these cells (1 file(s)) -- untouched; a redeploy here still refuses " \
           "B1 on it" in out
    assert theirs.read_bytes() == b"F9WM" and _deployed(game) == []
    calls[:] = []
    assert cli.main(["world-river", "--mod-folder", "FF9CustomMap-world", "--at", "512,128"]) == 2
    err = capsys.readouterr().err
    assert "world-river refused -- B1: the stack already overrides these cells" in err and "OTHER disc 4 (1 file(s))" \
        in err
    assert [c[0] for c in calls] == ["read", "compose"]


# ---- cluster C, on the user's install -----------------------------------------------------------------------------

def _need_install() -> None:
    try:
        import UnityPy  # noqa: F401
        ok = (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        ok = False
    if not ok:
        warnings.warn("cluster C's world-river fragment went unchecked on real data in this run: no FF9 install + "
                      "UnityPy. Re-run in the MAIN repo (C:/gd/Dream-World-IX/ff9mapkit).", UserWarning)
        pytest.skip("needs the FF9 install + UnityPy (see the warnings summary)")


def test_cluster_c_fragment_holds_the_whole_island():
    """Rung 0's acceptance (PLAN.md): the island in cluster C's cove whole (85 tris, where the round-4 chord cut it
    in half), F1 + F2 green, the boundary classed; rung 2's notch closure carries 12 stock tris more."""
    _need_install()
    f = R.fragment(R.CLUSTER_C)
    rep = f.report
    assert rep["islands"] == [{"tris": 85, "at": [1087.5, -1054.8]}] and rep["tethered"] == 1
    assert (rep["tris"], rep["unit"], rep["cove"], rep["coast"], rep["notches"]) == (1546, 330, 1026, 141, 12)
    assert rep["boundary_len"] == {"lawn": 607.4, "water": 170.4, "join": 6.6, "source": 5.7}
    assert rep["F1"] == {"forest": 0, "rock": 0, "object": 1, "building": 0, "beach": 3, "islands": 1}
    assert rep["F2"] == {"water_edges": 43} and rep["seaward_len"] == 170.38
    assert f.joins["W"][1] == (1040.0, 0.0, f.joins["W"][1][2]) and abs(f.joins["W"][1][2] + 1083.34) < 0.01
    assert rep["parts"]["object"] == 40 and rep["parts"]["stream"] == 90 and rep["parts"]["riverjoint"] == 11


def test_cluster_c_outline_mints_with_both_joins_exact():
    """Rung 1's acceptance on real data (PLAN.md): cluster C's kit arc leaves E north along its home coast and
    arrives at W from the ESE; the custom-outline mint holds both stock columns bit for bit with the U landed, and
    every geometry gate is clean bar the two seaward wall quads at the columns -- inside the fragment's footprint,
    which rung 2's opening drops. And no lip streak: the pre-fix mint's 12 streaked lip tris (17.53 u^2, the
    2026-10-20 rung-4 stills) are gone under THE CELL-CLIPPED LIP.

    Re-pinned with the cell-clipped lip: W's column tri leans 72.13 (was 72.04) -- its join segment now carries a
    lattice cut, dented JOIN_CUT_DENT landward, and the column tri is that segment's last fan piece; and the walk
    filter drops 3 tris (was 2) -- E's seaward quad carries a cut too, so its steep tri is two coplanar pieces. Every
    one still sits on a join base, in a seaward quad."""
    _need_install()
    from ff9mapkit.world import island as I
    f = R.fragment(R.CLUSTER_C)
    ol = R.outline(f)
    rep = ol.report
    assert (rep["first"], rep["last"], rep["arc_points"], rep["ring_points"]) == ("E", "W", 96, 138)
    assert rep["seg_max"] <= 8.0 and rep["arc_to_land_min"] > 8.0 and rep["stub"] == {"E": 6.0, "W": 3.601}
    built = R.mint(ol)
    j = R.join_gates(built, ol, f.joins)
    assert j["E"]["du"] < 1e-12 and j["W"]["du"] < 1e-12 and max(j["E"]["dv"], j["W"]["dv"]) < 5e-4
    assert (j["E"]["slope"], j["W"]["slope"]) == ([78.21], [72.13])
    v = I.verify_landmass(built)
    assert (v["cracks"], v["open_edges"], v["holes"], v["down_facing"], v["grass_over_8u"]) == (0, 0, 0, 0, 0)
    assert v["lip_streaks"] == 0 and I.lip_streak_tris(built) == []
    old = I.lip_streak_tris(R.mint(ol, cell_lip=False))
    assert (len(old), round(sum(a for _r, a, _c, _f in old), 2)) == (12, 17.53)
    gpos, gtris = built["world"]["pos"], built["world"]["tris"]
    steep = []
    for tri in gtris:
        a, b, c = (np.asarray(gpos[k]) for k in tri)
        n = np.cross(b - a, c - a)
        if n[1] / np.linalg.norm(n) <= 0.1:
            steep.append({tuple(map(float, gpos[k])) for k in tri})
    assert len(steep) == v["walk_filter_fails"] == 3
    bases = {tuple(map(float, b)) for _c, b in f.joins.values()}
    assert all(s & bases for s in steep)                       # all in the two seaward quads
    for name in ("E", "W"):                                    # each holds its join column: the seaward quad's tri
        crest, base = (tuple(map(float, p)) for p in f.joins[name])
        assert sum(1 for s in steep if {crest, base} <= s) == 1, name



@pytest.fixture(scope="module")
def cluster_c():
    _need_install()
    win = R.read_window(R.CLUSTER_C)
    f = R.build_fragment(win, R.CLUSTER_C)
    return win, f, R.outline(f)


def _red(comp):
    return sorted(k for k, g in comp.report["gates"].items() if isinstance(g, dict) and g.get("ok") is False)


def test_cluster_c_composes_green_on_open_ocean(cluster_c):
    """Rung 2's acceptance (PLAN.md): cluster C composed onto the open ocean across the world's seam (the only
    open water a 3 x 5-block footprint fits), every gate green: J1-J4, the zip envelope, G1-G6, B1, C1. Inside the
    footprint the island grounds EXACTLY as home does at every sample.

    Re-pinned with the cell-clipped lip (THE LIP-STREAK FIX): the kit's lip is cut at the lattice lines, so it
    carries more, smaller tris -- 3785 (was 3329), the opening drops 1722 (was 1690: 1621 lawn + 101 wall) and keeps
    2063 (was 1639) -- and the zip over the finer hole arc lays 440 tris (was 442), max rise 1.40 (was 1.39). Every
    gate, the G4 census at home included, is exactly as it was."""
    win, f, ol = cluster_c
    assert R.open_ocean_offsets(sorted(R.mint(ol)["blocks"]))[0] == (8, 0)
    comp = R.compose(f, offset=(512.0, 0.0), window=win, ol=ol)
    rep, g = comp.report, comp.report["gates"]
    assert rep["green"] and _red(comp) == []
    assert rep["opening"] == {"kit_tris": 3785, "dropped": 1722, "dropped_fams": {"main": 1621, "rock": 101},
                              "kept": 2063}
    assert (g["zip"]["tris"], g["zip"]["max_edge"], g["zip"]["max_rise"]) == (440, 6.66, 1.4)
    assert g["G4"]["by"] == {"same": 10098} and (g["G4_kit"]["points"], g["G4_kit"]["miss"]) == (3341, 0)
    assert (g["G1"]["cracks"], g["G3"]["near_miss"], g["G5"]["flipped"]) == (0, 0, 0)
    assert g["G5"]["skipped_carried"] == 201 and g["B1"]["cells"] == 12
    cells = comp.plan["cells"]
    assert cells["0,14"]["tris"]["Object"] == 40                         # the bridge, in its one cell
    assert all("Object" in c["blanks"] for k, c in cells.items() if k != "0,14")
    assert all(c["divert"] == [16, 15] for c in cells.values())


def test_cluster_c_break_its(cluster_c, monkeypatch):
    """Each defence, removed, turns its gate red on the real composition."""
    win, f, ol = cluster_c
    from ff9mapkit.world import extract as X
    with monkeypatch.context() as mp:                                       # the notch closure -> G4 (a fold)
        mp.setattr(R, "notch_closure", lambda M, frag: set())
        f0 = R.build_fragment(win, R.CLUSTER_C)
    assert _red(R.compose(f0, offset=(512.0, 0.0), window=win)) == ["G4"]

    def old_strip(t, area):                                                 # the old dispatch strip -> G5
        d = X.decode_id(int(t["idall"]))
        return int(X.encode_id(0, area if t["part"] in R.GROUND_PARTS else d["area"], d["topograph"], d["flags"]))
    with monkeypatch.context() as mp:
        mp.setattr(R, "_stamp_carried", old_strip)
        comp = R.compose(f, offset=(512.0, 0.0), window=win, ol=ol)
    assert _red(comp) == ["G5"] and comp.report["gates"]["G5"]["flipped"] == 201
    comp = R.compose(f, offset=(0.0, 0.0), window=win, ol=ol)              # the donor's own cells -> B1
    assert _red(comp) == ["B1"] and "has its own stock prefab" in comp.report["gates"]["B1"]["fails"][0]
    with monkeypatch.context() as mp:                                       # a zip tri lost -> G1 cracks
        mp.setattr(R, "_refine_zip", lambda tris, max_edge, rise=R.ZIP_RISE: (list(tris)[1:], 0))
        comp = R.compose(f, offset=(512.0, 0.0), window=win, ol=ol)
    assert "G1" in _red(comp) and comp.report["gates"]["G1"]["cracks"] >= 2



def test_cluster_c_writes_and_reads_back(cluster_c, tmp_path):
    """Rung 3's acceptance (PLAN.md): cluster C written to a scratch folder outside the install. B1 on the bytes:
    every cell diverts to (16,15) with every prefab part, the files round-trip, and the engine's census over the
    WRITTEN stacks misses nowhere home grounds (98 samples miss at home too: the skipped banks). W1 after THE KNIT:
    no tile facing deep without its transition, no crop-made sea pair at any tri edge, the frame coherent, nothing
    unpaintable -- and one contradicting edge home lacks, at the W join's corner (THE CLIFF-CORNER BAND STEP: the
    carried cliff's sea3 against the kit cliff's sea4, the step home itself ships at cluster C's E headland)."""
    win, f, ol = cluster_c
    comp = R.compose(f, offset=(512.0, 0.0), window=win, ol=ol)
    own = Counter(t["blk"] for t in f.tris if t["part"] == "sea5")
    (bx0, bx1), (by0, by1) = R.CLUSTER_C.window
    donors = [b for b, _ in own.most_common()] + [(x, y) for x in range(bx0, bx1 + 1) for y in range(by0, by1 + 1)]
    rep = R.write_composition(comp, tmp_path / "river_mod", window=win, donors=donors)
    b1, w1 = rep["B1"], rep["W1"]
    assert rep["files"] == 132 and b1["ok"] and b1["cells"] == 12
    assert sum(c["home_miss"] for c in b1["census"].values()) == 98
    assert w1["after"]["seam"]["under"] == 0 and w1["after"]["contacts"] == {} and w1["wang"]["incoherent"] == 0
    assert w1["unpaintable"] == [] and w1["home"]["edges"] == 2
    assert w1["edges_introduced"] == 1 and w1["edges_introduced_where"] == [(24, 16, 3, 14)]
    sp = rep["sea_plan"]
    assert sp["A_ok"] and sp["C_ok"] and sp["status"] == "warn"            # B: the island's interior blocks
