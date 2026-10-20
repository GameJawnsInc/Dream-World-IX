"""world-river rung 0: the FRAGMENT and its two topology gates (world/river.py;
studies/terrain-malleability/watercarry/PLAN.md).

The hermetic tests run on a synthetic cove drawn as an ASCII map (4u cells, two tris each), so they collect in a fresh
worktree: a river with banks rising at a rock, a forest beside it, a beached cove walled by lip, two join columns at
the cove's mouth and an islet straddling the straight chord between them. One install-gated test pins cluster C."""
from __future__ import annotations

import math
import warnings

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

SHIFT = (0.37, 0.21)                                        # off the mint's 4u lattice, as a real donor is
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
    and rock_uvs window-translates that tri, moving W's U to the strip's far edge."""
    ol, joins = hand_join(last_seg=6.0)
    with pytest.raises(R.RiverRefused, match="J2: join W"):
        R.join_gates(R.mint(ol), ol, joins)


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
    in half), F1 + F2 green, the boundary classed."""
    _need_install()
    f = R.fragment(R.CLUSTER_C)
    rep = f.report
    assert rep["islands"] == [{"tris": 85, "at": [1087.5, -1054.8]}] and rep["tethered"] == 1
    assert (rep["tris"], rep["unit"], rep["cove"], rep["coast"]) == (1535, 330, 1027, 141)
    assert rep["boundary_len"] == {"lawn": 650.1, "water": 146.0, "join": 6.6, "source": 5.7}
    assert rep["F1"] == {"forest": 0, "rock": 0, "object": 1, "building": 0, "beach": 3, "islands": 1}
    assert rep["F2"] == {"water_edges": 34} and rep["seaward_len"] == 146.03
    assert f.joins["W"][1] == (1040.0, 0.0, f.joins["W"][1][2]) and abs(f.joins["W"][1][2] + 1083.34) < 0.01
    assert rep["parts"]["object"] == 40 and rep["parts"]["stream"] == 90 and rep["parts"]["riverjoint"] == 11


def test_cluster_c_outline_mints_with_both_joins_exact():
    """Rung 1's acceptance on real data (PLAN.md): cluster C's kit arc leaves E north along its home coast and
    arrives at W from the ESE; the custom-outline mint holds both stock columns bit for bit with the U landed, and
    every geometry gate is clean bar the two seaward wall quads at the columns -- inside the fragment's footprint,
    which rung 2's opening drops."""
    _need_install()
    from ff9mapkit.world import island as I
    f = R.fragment(R.CLUSTER_C)
    ol = R.outline(f)
    rep = ol.report
    assert (rep["first"], rep["last"], rep["arc_points"], rep["ring_points"]) == ("E", "W", 96, 129)
    assert rep["seg_max"] <= 8.0 and rep["arc_to_land_min"] > 8.0 and rep["stub"] == {"E": 6.0, "W": 3.601}
    built = R.mint(ol)
    j = R.join_gates(built, ol, f.joins)
    assert j["E"]["du"] < 1e-12 and j["W"]["du"] < 1e-12 and max(j["E"]["dv"], j["W"]["dv"]) < 5e-4
    assert (j["E"]["slope"], j["W"]["slope"]) == ([78.21], [72.04])
    v = I.verify_landmass(built)
    assert (v["cracks"], v["open_edges"], v["holes"], v["down_facing"], v["grass_over_8u"]) == (0, 0, 0, 0, 0)
    gpos, gtris = built["world"]["pos"], built["world"]["tris"]
    steep = []
    for tri in gtris:
        a, b, c = (np.asarray(gpos[k]) for k in tri)
        n = np.cross(b - a, c - a)
        if n[1] / np.linalg.norm(n) <= 0.1:
            steep.append({tuple(map(float, gpos[k])) for k in tri})
    assert len(steep) == v["walk_filter_fails"] == 2
    for name in ("E", "W"):                                    # each holds its join column: the seaward quad's tri
        crest, base = (tuple(map(float, p)) for p in f.joins[name])
        assert sum(1 for s in steep if {crest, base} <= s) == 1, name
