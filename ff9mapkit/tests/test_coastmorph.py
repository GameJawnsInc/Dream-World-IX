"""The coast-morph pillar (world/coastmorph.py) -- golden tests against the IN-GAME-PROVEN
build (2026-07-09, donor (7,17)'s NE cliff window, deployed cells (11,9) bump / (13,9)
headland vs the (9,9) verbatim reference; land approved round 1, water round 2).

These tests need the FF9 install (they decode the real donor bytes) and skip cleanly on a
public clone, like the other transplant proofs.
"""
import hashlib
import math

import pytest


def _game_ready() -> bool:
    from ff9mapkit import config
    try:
        return (config.find_game_path(None) / "StreamingAssets").is_dir()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _game_ready(), reason="needs the FF9 install + UnityPy")

DONOR = (7, 17)
# the proven window's base-outline endpoints (donor world frame, snapped from the mesh)
START = (492.0, -1102.8203125)
END = (508.0, -1113.6796875)
#: sha256 over the sorted rounded emissions (terrain positions; sea positions+uvs) of the
#: proven headland build -- geometry is deterministic; grass UV quadrant PICKS are
#: deterministic too (sorted Delaunay iteration) but excluded so an anti-tiling hash-tweak
#: never masks a geometry regression.
GOLDEN_HASH = "9ad139e61b888b14"


def _window():
    from ff9mapkit.world import coastmorph as CM
    return CM.CliffWindow(DONOR, START, END)


def test_window_decodes_the_proven_columns():
    win = _window()
    assert len(win.base) == 5
    assert [round(p[0]) for p in win.base] == [492, 496, 500, 504, 508]
    # the lip-row laws, byte-exact on this specimen (crease 0.893 / base 0.923)
    assert all(abs(p[1]) < 0.01 for p in win.base)          # free-base at the waterline
    assert len(win.quads) == 4 and all(len(q) == 2 for q in win.quads)
    assert win.nhat[1] > 0                                   # seaward = north-east here


def test_bump_builds_the_proven_counts_and_refuses_the_fold():
    from ff9mapkit.world import coastmorph as CM
    disp, sea = CM.cliff_bump(DONOR, START, END, 2.5)
    assert disp.part == "terrain" and disp.expected == 26   # the deployed proven counts
    assert sea.part == "sea4" and sea.expected == 9
    # the ~2.5u conforming envelope is GEOMETRIC: 3.0 folds the tile whose shore vert sits
    # between two fixed water verts (the in-game-refused case, made a build-time refusal)
    with pytest.raises(ValueError, match="folds a tile"):
        CM.cliff_bump(DONOR, START, END, 3.0)


def test_headland_golden_build():
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_headland(DONOR, START, END, 8.0)
    # the proven scope: 8 wall + 6 grass dropped / 19 sea dropped / zero surviving
    # moved-vert instances (the DROP-DON'T-DRAG law) / 16 wall + 18 grass + 17 sea emitted
    assert drop_t.expected == 14 and drop_s.expected == 19
    assert disp.expected == 0
    assert len(emit_t.tris) == 34 and len(emit_s.tris) == 17
    # every emitted tri is real geometry (the wall law: never test plan area)
    from ff9mapkit.world.transplant import _tri_area2_3d
    assert all(_tri_area2_3d(t3) > 1e-6 for t3 in emit_t.tris + emit_s.tris)
    # the golden emission hash (positions; sea incl. uvs) == the in-game-proven build
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = hashlib.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_HASH


#: the bay's proven-build hash (D=6 on the same window; deployed at (12,9) 2026-07-10)
GOLDEN_BAY_HASH = "232a4c1c4dd2b634"


def test_bay_golden_build():
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_bay(DONOR, START, END, 6.0)
    # 8 wall + 15 grass dropped (the crease-footprint extension) / 11 sea / zero survivors
    assert drop_t.expected == 23 and drop_s.expected == 11
    assert disp.expected == 0
    assert len(emit_t.tris) == 29 and len(emit_s.tris) == 15
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = hashlib.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_BAY_HASH


def test_bay_refuses_a_component_reach():
    from ff9mapkit.world import coastmorph as CM
    # at depth 8 the bay's inland outline reaches past the window's grass component --
    # the containment gate refuses (the component laws, made a build-time refusal)
    with pytest.raises(ValueError, match="escapes the drop sets"):
        CM.cliff_bay(DONOR, START, END, 8.0)


#: the composed morph's window (480..508, spanning the REFINED-crease fan gap at 480-484)
#: and its proven-build hash (deployed at (10,9) 2026-07-10)
LOBES_START = (480.0, -1110.99)
LOBES_END = (508.0, -1113.6796875)
GOLDEN_LOBES_HASH = "1c5dab560c183654"


def test_lobes_golden_build():
    """A bay between two headlands as ONE composed reshape -- exercises the refined-fan gap
    decode, the free equal-arc resample (the pinned scheme degenerates on multi-lobe
    profiles), the phase-table wall UVs, and the grass ring-extension ladder."""
    import hashlib as _h
    from ff9mapkit.world import coastmorph as CM
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_lobes(
        DONOR, LOBES_START, LOBES_END, (3.5, -5.0, 6.5))
    assert drop_t.expected == 39 and drop_s.expected == 23
    assert disp.expected == 0
    assert len(emit_t.tris) == 47 and len(emit_s.tris) == 23
    def sig(tris, uv=True):
        return sorted(tuple(round(c, 6) for v in t3 for c in
                            (list(v[0]) + (list(v[2]) if uv else []))) for t3 in tris)
    h = _h.sha256(repr(sig(emit_t.tris, uv=False) + sig(emit_s.tris)).encode()).hexdigest()
    assert h[:16] == GOLDEN_LOBES_HASH


def test_lobes_reach_gate_refuses_the_shallow_ladder():
    from ff9mapkit.world import coastmorph as CM
    # a window starting one column further west pushes its first headland lobe's footprint
    # into the sea5 band -- the REACH gate refuses (non-sea4 within the morph's reach)
    with pytest.raises(ValueError, match="reaches sea"):
        CM.cliff_lobes(DONOR, (476.0, -1108.9), LOBES_END, (3.5, -5.0, 6.5))


#: the (7,17) S-beach waterline run (deployed with the D=2.5 seaward bow at (11,8) 2026-07-10)
BEACH_START = (476.0, -1124.0)
BEACH_END = (504.0, -1132.0)


#: the (3,11) NOSE window (the map's one single-cell-carryable convex beach; the definitive
#: per-vert seam-direction census re-classed the "+45%" runs as pocket misreads -- true
#: noses are GENTLE, map max ~+19% of length, while pockets run to ~-46%)
NOSE_DONOR = (3, 11)
NOSE_START = (204.3789, -744.3672)
NOSE_END = (224.0, -761.4375)


def test_beach_bump_builds_and_gates():
    """The ASSEMBLY bow (rung 1, hug-law form): one displacement field -- waterline at
    factor 1, seaward water over the depth-scaled ladder taper (strain <=~16%, verbatim
    drag), and the landward side riding (flat across the swash, cos^2 over the berm) so
    the ribbon stays its near-constant within-beach width. THE SHAPE-CLASS GATE rules
    direction per donor: (7,17) is a pocket (landward-only), (3,11)'s nose grows seaward."""
    from ff9mapkit.world import coastmorph as CM
    # the pocket: seaward refuses (class), landward passes (the assembly slides)
    with pytest.raises(ValueError, match="SHAPE-CLASS GATE"):
        CM.beach_bump(DONOR, BEACH_START, BEACH_END, 2.5)
    (disp,) = CM.beach_bump(DONOR, BEACH_START, BEACH_END, -1.0)
    assert disp.part is None and disp.expected == 211
    # the nose: seaward passes to the window's hug ceiling (a bend vert breaks at 2.0)
    (disp,) = CM.beach_bump(NOSE_DONOR, NOSE_START, NOSE_END, 1.5)
    assert disp.expected == 173
    with pytest.raises(ValueError, match="RIBBON/HUG GATE"):
        CM.beach_bump(NOSE_DONOR, NOSE_START, NOSE_END, 2.0)
    with pytest.raises(ValueError, match="SHAPE-CLASS GATE"):
        CM.beach_bump(NOSE_DONOR, NOSE_START, NOSE_END, -1.5)
    # land drags => the land-drag envelope caps depth outright
    with pytest.raises(ValueError, match="land-drag envelope"):
        CM.beach_bump(DONOR, BEACH_START, BEACH_END, 3.5)


def test_beach_bump_refuses_a_non_waterline_run():
    from ff9mapkit.world import coastmorph as CM
    # sand-seam endpoints (the landward boundary) are not a waterline run
    with pytest.raises(ValueError, match="waterline"):
        CM.beach_bump(DONOR, (480.0, -1120.0), (496.0, -1125.0), 2.0)


def _tweak_hash(tweaks):
    import hashlib as _h
    sig = []
    for t in tweaks:
        if hasattr(t, "keys"):
            sig.append((t.part, sorted(sorted(k) for k in t.keys)))
        elif hasattr(t, "tris"):
            sig.append((t.part, sorted(
                tuple(round(c, 6) for v in t3 for c in (list(v[0]) + list(v[2])))
                for t3 in t.tris)))
        else:
            sig.append(("displace", sorted(
                (k, tuple(round(x, 6) for x in v)) for k, v in t.moves.items())))
    return _h.sha256(repr(sig).encode()).hexdigest()[:16]


def test_beach_rebuild_golden():
    """Identity mode (rung 2 step 1, in-game proven ~indistinguishable 2026-07-10) -- the
    full tweak hash also pins the helper extraction as behavior-preserving."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.beach_rebuild(DONOR, BEACH_START, BEACH_END)
    assert [(t.part, getattr(t, "expected", None) or len(t.tris)) for t in tw] == [
        ("beach1", 14), ("sea2", 18), ("sea1", 26),
        ("beach1", 14), ("sea2", 18), ("sea1", 26)]
    assert _tweak_hash(tw) == "0ebffe558640a7d0"


def test_beach_reshape_golden_transport():
    """The SHAPE morph (rung 2 step 2) at the lawful depth where the band TRANSPORT
    fires. THE HUG LAW: the ASSEMBLY slides (sand seam + waterline together, the berm
    terrain drags) so the swash ribbon stays its near-constant within-beach width. THE
    SHAPE-CLASS LAW: (7,17) is a POCKET beach (concave to its chord), so the lawful
    direction is LANDWARD -- the pocket deepens, a column sheds a wash row, the vacated
    cells re-lay as sea1 (learned table), a sea1 cell returns to sea3 (learned
    quadrant/dihedral-8), and the edge-shade solver repairs exactly the Wang agreements
    the new map forces."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.beach_reshape(DONOR, BEACH_START, BEACH_END, -1.0)
    led = [(getattr(t, "part", None),
            ("drop", t.expected) if hasattr(t, "keys")
            else ("emit", len(t.tris)) if hasattr(t, "tris")
            else ("displace", t.expected)) for t in tw]
    assert led == [("beach1", ("drop", 14)), ("sea2", ("drop", 18)),
                   ("sea1", ("drop", 6)),
                   (None, ("displace", 20)),
                   ("beach1", ("emit", 16)), ("sea2", ("emit", 24)),
                   ("sea1", ("emit", 6)), ("sea3", ("emit", 2))]
    assert _tweak_hash(tw) == "2efc3ce72e461cc0"


def test_beach_reshape_identity_is_a_rebuild():
    """Depth 0 degenerates to a pure re-derivation: no band shifts, no sea1/sea3 changes,
    the same drop scope as identity mode."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.beach_reshape(DONOR, BEACH_START, BEACH_END, 0.0)
    assert [(t.part, hasattr(t, "keys")) for t in tw] == [
        ("beach1", True), ("sea2", True), ("beach1", False), ("sea2", False)]


def test_beach_reshape_shallow_landward_stays_conforming():
    """A shallow landward morph (no band shift) still slides the assembly + re-lays the
    foam/wash -- the degenerate no-transport case stays lawful."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.beach_reshape(DONOR, BEACH_START, BEACH_END, -0.5)
    parts = [(getattr(t, "part", None), hasattr(t, "keys")) for t in tw]
    assert ("sea3", True) not in parts and ("sea1", True) not in parts


def test_beach_reshape_refusals():
    from ff9mapkit.world import coastmorph as CM
    # THE SHAPE-CLASS GATE: (7,17) is a pocket beach -- EVERY seaward depth crosses its
    # chord toward the convex class (the in-game 'extruded ends' read, made a refusal)
    with pytest.raises(ValueError, match="SHAPE-CLASS GATE"):
        CM.beach_reshape(DONOR, BEACH_START, BEACH_END, 1.0)
    # the berm's own geometric fold limit (the sand-slide compresses the berm landward)
    with pytest.raises(ValueError, match="folds a berm tile"):
        CM.beach_reshape(DONOR, BEACH_START, BEACH_END, -1.5)
    # the sand-slide drags the berm -- the land-drag envelope caps depth outright
    with pytest.raises(ValueError, match="land-drag envelope"):
        CM.beach_reshape(DONOR, BEACH_START, BEACH_END, 3.5)
    # sand-seam endpoints are not a waterline run
    with pytest.raises(ValueError, match="matched waterline/sand columns|waterline"):
        CM.beach_reshape(DONOR, (480.0, -1120.0), (496.0, -1125.0), 1.0)


def test_beach_slide_golden():
    """THE FULL-ASSEMBLY SLIDE (Path B resolved 2026-07-10) at the target depth -4.0 --
    past both old caps (drag fold -1.5 / hard 2.6). THE FULL-ASSEMBLY LAW (the sand
    census): the run band's one v-rect stretches over 1.8-6.6u only, row B is strictly
    terminal, run-seam v pins to 0.5947/0.5957 with zero exceptions -- a widened band has
    no lawful fill, so the WHOLE ladder moves: the band translates verbatim, the berm
    strip clips at the translated chain (18 mural tris -> 26 pieces), and the vacated
    shore re-lays ALL the way down the graded ladder (wash + sea1 ring + sea3 + sea5 by
    the learned table + a sea4 row -- sea4 grows landward, reconciling at the block
    frame where prefab ocean knits). THE T-VERTEX LAW (the playtest seam, in-game
    2026-07-10): kept berm regions re-triangulate from MERGED loops (no fragment-
    interface verts on shared edges), every emitted vert snaps to the canonical
    pos+delta floats, and the band's land edge subdivides at the genuine cut crossings
    (7 band tris re-emitted here) so both sides of the new chain carry identical verts;
    the T-VERTEX GATE then certifies the touched neighbourhood pinhole-free."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world.extract import decode_id
    tw = CM.beach_slide(DONOR, BEACH_START, BEACH_END, -4.0)
    led = [(getattr(t, "part", None),
            ("drop", t.expected) if hasattr(t, "keys")
            else ("emit", len(t.tris)) if hasattr(t, "tris")
            else ("displace", t.expected)) for t in tw]
    assert led == [("beach1", ("drop", 14)), ("sea2", ("drop", 18)),
                   ("sea1", ("drop", 22)), ("sea3", ("drop", 2)),
                   ("sea5", ("drop", 10)), ("terrain", ("drop", 25)),
                   (None, ("displace", 23)),
                   ("beach1", ("emit", 16)), ("sea2", ("emit", 24)),
                   ("sea1", ("emit", 22)), ("sea3", ("emit", 4)),
                   ("sea5", ("emit", 10)), ("sea4", ("emit", 4)),
                   ("terrain", ("emit", 43))]
    assert _tweak_hash(tw) == "f66e2b6520b562b0"
    # BAND RIGIDITY: every moved vert in one column (seam + land + interior) shares one
    # dz -- the band translates, never strains (widths/density/pins by construction)
    disp = next(t for t in tw if hasattr(t, "moves"))
    byx = {}
    for (x, y, z), d in disp.moves.items():
        byx.setdefault(round(x, 1), set()).add(round(d[2], 6))
    assert all(len(s) == 1 for s in byx.values())
    # seam verts ride flat (dy=0); land verts re-conform UP the berm (landward is higher)
    dys = sorted(round(d[1], 3) for d in disp.moves.values())
    assert dys[0] == 0.0 and dys[-1] > 0.3
    # the berm clip drops 18 mural tris; the ONLY dropped sand tris are the 7 cut-line
    # hosts, re-emitted subdivided at the mural pieces' crossing verts (verbatim texture)
    ter_drop = next(t for t in tw if hasattr(t, "keys") and t.part == "terrain")
    from ff9mapkit.world import transplant as TR
    sand_keys = {frozenset(CM._pk(v[0]) for v in t3)
                 for t3 in TR.world_tris(*DONOR, "terrain")
                 if decode_id(int(round(t3[0][3][0])))["topograph"] == 31}
    assert len(ter_drop.keys & sand_keys) == 7


def test_beach_slide_refusals():
    from ff9mapkit.world import coastmorph as CM
    # SEAWARD on the pocket: the shape-class law refuses (a pocket may not bow toward
    # the convex class) -- the free-form seaward path carries the same gate
    with pytest.raises(ValueError, match="SHAPE-CLASS GATE"):
        CM.beach_slide(DONOR, BEACH_START, BEACH_END, 0.5)
    with pytest.raises(ValueError, match="LANDWARD only"):
        CM.beach_slide(DONOR, BEACH_START, BEACH_END, -6.5)
    # the -2.0..-2.5 valley: the wash width-envelope (BAND GATE) refuses fractional-row
    # slides on the 6.7u/4.0u jump column; full-row depths (-3.0+) re-band cleanly
    with pytest.raises(ValueError, match="BAND GATE"):
        CM.beach_slide(DONOR, BEACH_START, BEACH_END, -2.0)


def test_beach_slide_seaward_golden():
    """The SEAWARD slide (the grass-berm nose rung, free-form) on the proven (18,15)
    nose at its probed ceiling +2.5: the band's 15 sand tris DROP and re-emit
    TRANSLATED VERBATIM (drop-don't-drag -- grass never moves, the GRASS-PIN law), the
    water rides the bump's proven ladder-taper field (269 displaced instances), and
    the vacated strip re-fills with 12 NATIVE GRASS tris (_grass_fill_region, the
    headland vocabulary; crack + grain gated). The island gains real grass area --
    TRUE seaward land growth. Deeper rungs refuse on WATER STRAIN at the block frame
    (the binding law of this window, not the berm the slide freed)."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world.extract import decode_id
    tw = CM.beach_slide(NOSE_SLIDE_DONOR, NOSE_SLIDE_START, NOSE_SLIDE_END, 2.5)
    led = [(getattr(t, "part", None),
            ("drop", t.expected) if hasattr(t, "keys")
            else ("emit", len(t.tris)) if hasattr(t, "tris")
            else ("displace", t.expected)) for t in tw]
    assert led == [("terrain", ("drop", 15)), (None, ("displace", 269)),
                   ("terrain", ("emit", 27))]
    assert _tweak_hash(tw) == "0513432ef7d69bc2"
    emit = next(t for t in tw if hasattr(t, "tris"))
    n_sand = sum(1 for t3 in emit.tris
                 if decode_id(int(round(t3[0][3][0])))["topograph"] == 31)
    assert (n_sand, len(emit.tris) - n_sand) == (15, 12)
    # water strain at the frame binds the deeper rung
    with pytest.raises(ValueError, match="STRAIN GATE"):
        CM.beach_slide(NOSE_SLIDE_DONOR, NOSE_SLIDE_START, NOSE_SLIDE_END, 3.0)


NOSE_SLIDE_DONOR = (18, 15)
NOSE_SLIDE_START = (1198.0273, -997.3633)
NOSE_SLIDE_END = (1173.1484, -1013.8867)


#: the comma's (9,6) window (desert topo-17 top, 93% uv-rect reuse) and the isthmus's
#: (7,6) window (topo-19 tiled + topo-49 at 0% local reuse -- the REAL mural class)
COMMA_START, COMMA_END = (640.0, -416.0), (620.09765625, -448.0)
ISTH_START, ISTH_END = (462.83203125, -448.0), (448.0, -405.85546875)


def test_structural_refuses_a_uv_unique_top():
    from ff9mapkit.world import coastmorph as CM
    # THE MEASURED MURAL GATE (capability 1): topo NUMBER never decides -- the isthmus's
    # topo-49 is uv-unique HERE (0% local reuse) while the crescent's topo-49 is 90%
    # tiled. The refusal names the offending topo and its measured reuse.
    with pytest.raises(ValueError, match=r"topo-49.*painted-mural"):
        CM.cliff_headland((7, 6), ISTH_START, ISTH_END, 6.0)


def test_tiled_headland_builds_on_the_comma():
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world.extract import decode_id
    from ff9mapkit.world.transplant import _tri_area2_3d
    # the morph-envelope flip: a desert top (93% uv-rect reuse) is a TILE VOCABULARY,
    # not a mural -- the tiled lane repeats the window's own dropped tiles
    drop_t, drop_s, disp, emit_t, emit_s = CM.cliff_headland((9, 6), COMMA_START,
                                                             COMMA_END, 6.0)
    assert disp.expected == 0                       # the DROP-DON'T-DRAG law holds
    assert len(emit_t.tris) > 0 and len(emit_s.tris) > 0
    assert all(_tri_area2_3d(t3) > 1e-6 for t3 in emit_t.tris + emit_s.tris)
    # D-4 CARRIED VOCABULARY: every emitted terrain idall already exists in the window's
    # own terrain (wall 58 + the dropped tiles' families travel with the clones; nothing
    # is minted), and the desert family itself is present in the fill
    win = CM.CliffWindow((9, 6), COMMA_START, COMMA_END)
    real_idalls = {tuple(t3[0][3]) for t3 in win.terr}
    emitted = {tuple(t3[0][3]) for t3 in emit_t.tris}
    assert emitted <= real_idalls
    topos = {decode_id(int(round(i[0])))["topograph"] for i in emitted}
    assert 17 in topos and 58 in topos
    # ...and the clone is a TRANSLATE-clone: every non-wall fill uv sits inside some
    # dropped tile's uv-rect expanded by its own span (a raw extrapolation walks whole
    # rect-widths out of the atlas; the translate offset keeps the eval point in the
    # source tile's own cell)
    wall_idall = {tuple(t3[0][3]) for t3 in win.cliff}
    dropped_srcs = [t3 for t3 in win.mains if drop_t._key_set(t3) in drop_t.keys]
    assert dropped_srcs, "no dropped mains reconstructed from the window"
    rects = []
    for t3 in dropped_srcs:
        us = [v[2][0] for v in t3]
        vs = [v[2][1] for v in t3]
        du, dv = max(us) - min(us), max(vs) - min(vs)
        rects.append((min(us) - du, max(us) + du, min(vs) - dv, max(vs) + dv))
    for t3 in emit_t.tris:
        if tuple(t3[0][3]) in wall_idall:
            continue
        for v in t3:
            u, vv = v[2]
            assert any(r[0] <= u <= r[1] and r[2] <= vv <= r[3] for r in rects), \
                f"fill uv ({u:.3f},{vv:.3f}) escapes every expanded source rect"


def test_mural_gate_reads_the_measured_threshold(monkeypatch):
    from ff9mapkit.world import coastmorph as CM
    # threshold at 1.01: even the 93%-tiled comma reads as mural (the gate is live)
    monkeypatch.setattr(CM, "MURAL_REUSE_MIN", 1.01)
    with pytest.raises(ValueError, match="painted-mural"):
        CM.cliff_headland((9, 6), COMMA_START, COMMA_END, 6.0)
    # threshold at 0.0: the isthmus's uv-unique topo-49 passes the gate and the window
    # fails LATER for a different reason -- the gate reads the constant both ways
    monkeypatch.setattr(CM, "MURAL_REUSE_MIN", 0.0)
    with pytest.raises(ValueError) as ei:
        CM.cliff_headland((7, 6), ISTH_START, ISTH_END, 6.0)
    assert "painted-mural" not in str(ei.value)


def test_harvest_folds_the_wrap_seam():
    from types import SimpleNamespace
    from ff9mapkit.world import coastmorph as CM
    # SYNTHETIC seam specimen (no palette wall witnesses the fold, so this pins it):
    # 5 clean gaps whose left-column U runs 0.30/0.40/0.50/0.60 and one wrap gap whose
    # left corners carry the SEAM form 0.55 (= 0.30 + 0.25). The fold must merge it onto
    # 0.30 so the canonical set is the true 4-cycle -- without the fold the seam cluster
    # displaces a canonical from the top-4.
    left_us = [0.30, 0.40, 0.50, 0.60, 0.55]
    base = [(4.0 * i, 0.0, 0.0) for i in range(len(left_us) + 1)]
    crease = [(4.0 * i, 2.0, -2.0) for i in range(len(left_us) + 1)]
    quads = []
    for i, u in enumerate(left_us):
        bl, cl, br, cr = base[i], crease[i], base[i + 1], crease[i + 1]
        t1 = [(bl, (0, 1, 0), (u, 0.1), (0,)), (cl, (0, 1, 0), (u, 0.2), (0,)),
              (br, (0, 1, 0), (u + 0.06, 0.1), (0,))]
        t2 = [(cl, (0, 1, 0), (u, 0.2), (0,)), (cr, (0, 1, 0), (u + 0.06, 0.2), (0,)),
              (br, (0, 1, 0), (u + 0.06, 0.1), (0,))]
        quads.append([t1, t2])
    win = SimpleNamespace(quads=quads)
    bk = [CM._pk(p) for p in base]
    ck = [CM._pk(p) for p in crease]
    cycles = CM._harvest_wall_cycles(win, bk, ck, len(left_us))
    assert cycles, "no candidate cycles harvested"
    assert sorted(cycles[0]) == [0.3, 0.4, 0.5, 0.6], sorted(cycles[0])


def test_one_lane_law_refuses_a_mixed_top(monkeypatch):
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import extract as EX
    # the crescent's (16,1) window consumes topo-17 AND topo-49 tiles; remapping the
    # 49-family idalls to grass makes the drop MIX grass with a tiled family -- no
    # single fill language spans it, so the one-lane law must refuse
    real = EX.decode_id

    def fake(i):
        d = dict(real(i))
        if d["topograph"] == 49:
            d["topograph"] = 0
        return d
    monkeypatch.setattr(CM, "decode_id", fake)
    with pytest.raises(ValueError, match="mixes grass"):
        CM.cliff_headland((16, 1), (1088.0, -84.0), (1024.0, -71.421875), 6.0)


def test_wall_cycle_harvests_on_a_non_grass_wall():
    from ff9mapkit.world import coastmorph as CM
    # D-5: the desert wall carries its OWN 4-phase U ramp (the grass CYC constants match
    # almost none of its gaps) -- the harvest reads it from the window's clean gaps
    win = CM.CliffWindow((9, 6), COMMA_START, COMMA_END)
    bk = [CM._pk(p) for p in win.base]
    ck = [CM._pk(p) for p in win.crease]
    cycles = CM._harvest_wall_cycles(win, bk, ck, len(win.base) - 1)
    assert cycles, "no candidate cycles harvested"
    got = sorted(cycles[0])
    want = (0.4277, 0.4902, 0.5527, 0.6152)
    assert all(abs(g - w) < 0.003 for g, w in zip(got, want)), got


def test_headland_refuses_an_illegal_gap_count():
    from ff9mapkit.world import coastmorph as CM
    # a 3-gap sub-window (492..504) cannot satisfy the deterministic U-ramp: its clean
    # gaps cover only 3 of the 4 texture phases (the free resample lifts the old strict
    # mod-4 window rule, but a pattern for every phase must exist in-window)
    with pytest.raises(ValueError, match="texture phases"):
        CM.cliff_headland(DONOR, START, (504.0, -1110.765625), 6.0)


def test_strips_rebuild_golden():
    """SEA5 EMISSION -- the strip-band identity rebuild: every decodable sea1 + sea5 cell
    of (7,17) re-derived from the learned table (the emission self-check re-decodes every
    emitted cell in-function). Positions identity, UVs re-derived -- the deployed-bytes
    differential vs a verbatim clone shows UV-only changes on decoded cells."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.strips_rebuild(DONOR)
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("sea1", 26), ("sea1", 26), ("sea5", 61), ("sea5", 61)]
    assert _tweak_hash(tw) == _tweak_hash(CM.strips_rebuild(DONOR))  # deterministic
    # positions are identity: every emitted tri's vertex set exists in the stock mesh
    emit1 = next(t for t in tw if not hasattr(t, "keys") and t.part == "sea1")
    from ff9mapkit.world import transplant as TR
    stock = {frozenset(CM._pk(v[0]) for v in t3) for t3 in TR.world_tris(*DONOR, "sea1")}
    assert all(frozenset(CM._pk(v[0]) for v in t3) in stock for t3 in emit1.tris)


def test_sand_rebuild_golden():
    """SAND EMISSION (Path A, byte-learned 2026-07-10) -- the sand-band identity rebuild
    on the proven beach: (7,17)'s closed run columns re-derive from the learned two-rect
    strip (the P quad + the real Q+=Q- mirror-fold group, 6 tris), while the caps (row B,
    the end-cap-assembly rung), the bend-fan halves and the frame splits stay verbatim
    (the closure freeze). UV-x-only: positions identity, v ribbon pins byte-unchanged."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.sand_rebuild(DONOR)
    drop, emit = tw
    assert (drop.part, drop.expected) == ("terrain", 6)
    assert len(emit.tris) == 6
    assert _tweak_hash(tw) == _tweak_hash(CM.sand_rebuild(DONOR))  # deterministic
    stock = {frozenset(CM._pk(v[0]) for v in t3): t3
             for t3 in TR.world_tris(*DONOR, "terrain")}
    assert all(frozenset(CM._pk(v[0]) for v in t3) in stock for t3 in emit.tris)
    # the ribbon pins survive byte-exact; every emitted column re-decodes as a run tile
    assert {round(v[2][1], 4) for t3 in emit.tris for v in t3} == {0.5664, 0.5947}
    assert all((CM._sand_tri_decode(t3) or ("", 0))[0] == "run" for t3 in emit.tris)
    # the FLIP is a real re-derivation on every tri (never a silent donor coincidence):
    # (7,17)'s P quad re-derives on Q and its Q+=Q- fold group on P
    for t3 in emit.tris:
        ref = stock[frozenset(CM._pk(v[0]) for v in t3)]
        s = sorted(range(3), key=lambda i: CM._pk(t3[i][0]))
        r = sorted(range(3), key=lambda i: CM._pk(ref[i][0]))
        assert max(abs(t3[s[i]][2][0] - ref[r[i]][2][0]) for i in range(3)) > 0.01
        assert all(abs(t3[s[i]][2][1] - ref[r[i]][2][1]) < 1e-7 for i in range(3))


def test_sand_rebuild_freezes_a_frame_fragment():
    """(13,10) carries only the frame-straddling tail of the (12,11)/(13,11) band: every
    column fails the closure freeze (a non-port, non-chain boundary edge on the block
    frame), so the rebuild refuses rather than half-emit a split column."""
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="no closed decodable sand columns"):
        CM.sand_rebuild((13, 10))


def test_cap_rebuild_golden():
    """THE END-CAP LAWS (byte-learned 2026-07-11) -- the identity round-trip on the
    proven beach: both of (7,17)'s BL foam caps and both sand row-B caps re-derive
    from the laws + canonical snap floats BYTE-EXACTLY (the internal gates raise on
    any incompleteness). THE SLOT LAW: slots transport -- the slot-flip experiment was
    falsified in-game at (9,8) ("non-capped straight lines"): the beach texture is one
    curling-swash composition and only the BL window fades (THE TAPER ASYMMETRY)."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.cap_rebuild(DONOR)
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("beach1", 4), ("beach1", 4), ("terrain", 4), ("terrain", 4)]
    assert _tweak_hash(tw) == _tweak_hash(CM.cap_rebuild(DONOR))  # deterministic
    # BOTH parts are byte-identity: every emitted (pos, uv) tri exists verbatim
    for part in ("beach1", "terrain"):
        emit = next(t for t in tw if hasattr(t, "tris") and t.part == part)
        stock = {frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                           for v in t3) for t3 in TR.world_tris(*DONOR, part)}
        assert all(frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                             for v in t3) in stock for t3 in emit.tris)
    emitf = next(t for t in tw if hasattr(t, "tris") and t.part == "beach1")
    assert {round(v[2][1], 4) for t3 in emitf.tris for v in t3} == {0.5312, 0.9375}


def test_cap_rebuild_tr_round_trip():
    """(16,5) uses the TR curl-out caps: the rebuild reproduces them byte-exactly
    through the same emitter (slot transported, snaps canonical)."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.cap_rebuild((16, 5))
    emitf = next(t for t in tw if hasattr(t, "tris"))
    assert {round(v[2][1], 4) for t3 in emitf.tris for v in t3} == {0.0, 0.4844}
    assert {round(v[2][0], 4) for t3 in emitf.tris for v in t3} == {0.5, 0.9844}
    stock = {frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                       for v in t3) for t3 in TR.world_tris(16, 5, "beach1")}
    assert all(frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                         for v in t3) in stock for t3 in emitf.tris)


def test_beach_mint_golden():
    """BEACH-MINT rung 1 -- (7,17)'s beach re-minted from chain specs: 16 donor sand
    tris (incl. the 4-tri bend fan, NOT transported) become 14 clean column tris; the
    UV sets are exactly the two languages; every interface vert is preserved; the
    synthetic seam chain's interior verts are NEW positions at the requested width."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.beach_mint(DONOR, width=2.5)
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("terrain", 16), ("terrain", 14), ("beach1", 14), ("beach1", 14)]
    assert _tweak_hash(tw) == _tweak_hash(CM.beach_mint(DONOR, width=2.5))
    emits = next(t for t in tw if hasattr(t, "tris") and t.part == "terrain")
    emitf = next(t for t in tw if hasattr(t, "tris") and t.part == "beach1")
    assert {round(v[2][1], 4) for t3 in emits.tris for v in t3} \
        == {0.5664, 0.5947, 0.6006, 0.625}
    assert {round(v[2][0], 4) for t3 in emitf.tris for v in t3} == {0.0156, 0.5}
    assert {round(v[2][1], 4) for t3 in emitf.tris for v in t3} \
        == {0.0156, 0.4531, 0.5312, 0.9375}
    # the seam moved: some minted verts must NOT exist in the stock mesh (synthesis),
    # while every boundary edge vert must (the pinned interfaces)
    stock = {CM._pk(v[0]) for t3 in TR.world_tris(*DONOR, "terrain") for v in t3} \
        | {CM._pk(v[0]) for t3 in TR.world_tris(*DONOR, "beach1") for v in t3}
    new = {CM._pk(v[0]) for t3 in emits.tris + emitf.tris for v in t3}
    assert len(new - stock) == 6            # the 6 interior seam verts are SYNTHETIC


def test_deformed_rect_law_decodes_the_strip_tiers():
    """THE DEFORMED-TILE RECT LAW (byte-learned 2026-07-11, the rung-3 convergence
    study): a strip tile's uv map is a <=2u x <=2v snap-rect ASSIGNED TO ITS CORNERS
    independent of geometric deformation (position-evaluated fits fail BECAUSE the
    map deforms with the tile); inserted verts are positional edge-lerps. On the
    proven coastal donors the law explains EVERY lattice group and every conforming
    group of both strip bands."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    for donor in (DONOR, (3, 13), (9, 17)):
        for part in ("sea1", "sea5"):
            tris = TR.world_tris(*donor, part)
            if not tris:
                continue
            kinds = [k for _g, k, _d in CM._deformed_strip_groups(tris)]
            assert kinds and all(k == "rect" for k in kinds), (donor, part)
    # (18,15) carries exactly two real residual sea1 groups (the map-wide ~5% class:
    # rotated / cross-group-anchored) -- the law names its residual honestly
    kinds = [k for _g, k, _d in CM._deformed_strip_groups(
        TR.world_tris(18, 15, "sea1"))]
    assert kinds.count("residual") == 2 and kinds.count("rect") >= 10


def test_conforming_rebuild_golden():
    """The rect law's completeness proof on (7,17): every conforming strip group
    re-derives through corner assignment + positional lerps under the equality
    gate; the emitted tris re-decode under the law; every emitted (pos, uv) is
    identity to the donor at 4dp (these donors' groups are all-corner -- transport
    verified structurally; the lerp tier is the rare map-wide residual)."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.conforming_rebuild(DONOR)
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("sea1", 10), ("sea1", 10), ("sea5", 8), ("sea5", 8)]
    assert _tweak_hash(tw) == _tweak_hash(CM.conforming_rebuild(DONOR))
    for part in ("sea1", "sea5"):
        emit = next(t for t in tw if hasattr(t, "tris") and t.part == part)
        stock = {frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                           for v in t3) for t3 in TR.world_tris(*DONOR, part)}
        assert all(frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                             for v in t3) in stock for t3 in emit.tris)
        kinds = [k for _g, k, _d in CM._deformed_strip_groups(emit.tris)]
        assert all(k == "rect" for k in kinds)


def test_beach_mint_land_golden():
    """RUNG 2a -- the FREE-FOOTPRINT mint, landward: the interior LAND CHAIN is
    synthetic too (sin^2 eased, cap ends pinned, berm-surface conformed) and the berm
    is CLIPPED at the new chain (the beach_slide machinery). At land=2.4 on (7,17):
    16 sand + 18 berm tris drop, 24 band + 26 clipped-piece tris emit, the area
    ledger is exact (band growth == consumed berm), every band land-edge vert is
    bit-exact in a clipped piece, and the foam is byte-identical to the land=None
    mint (land only touches terrain)."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.beach_mint(DONOR, land=2.4)
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("terrain", 34), ("terrain", 50), ("beach1", 14), ("beach1", 14)]
    assert _tweak_hash(tw) == "7049a91ba729b787"
    assert _tweak_hash(tw) == _tweak_hash(CM.beach_mint(DONOR, land=2.4))
    # the exact area ledger: band growth over the land=None mint == consumed berm
    from ff9mapkit.world import transplant as TR
    from ff9mapkit.world.extract import decode_id
    topo31 = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"] == 31

    def area(tris):
        s = 0.0
        for t3 in tris:
            (ax, _, az), (bx, _, bz), (cx, _, cz) = (v[0] for v in t3)
            s += abs((bx - ax) * (cz - az) - (cx - ax) * (bz - az)) / 2.0
        return s
    terr = TR.world_tris(*DONOR, "terrain")
    grown = area([t for t in tw[1].tris if topo31(t)]) \
        - area(CM.beach_mint(DONOR)[1].tris)
    consumed = area([t for t in terr if CM._key_set(t) in tw[0].keys
                     and not topo31(t)]) \
        - area([t for t in tw[1].tris if not topo31(t)])
    assert abs(grown - consumed) < 0.05
    # every band land-edge vert welds a clipped piece BIT-exactly (the T-vertex law)
    land_vs = {0.5664, 0.5674, 0.5977, 0.5986, 0.5996, 0.6006, 0.6045, 0.6123}
    pieces = {tuple(v[0]) for t3 in tw[1].tris if not topo31(t3) for v in t3}
    edge = {tuple(v[0]) for t3 in tw[1].tris if topo31(t3) for v in t3
            if round(v[2][1], 4) in land_vs}
    assert edge <= pieces
    # foam untouched by land=
    assert repr(tw[3].tris) == repr(CM.beach_mint(DONOR)[3].tris)


def test_beach_mint_land_probes_the_ribbon_ceiling():
    """The land knob's lawful ceiling on (7,17) is the RIBBON envelope (band width
    tops out at 6.6): 2.6 builds, 3.0 refuses; composition with width= works."""
    from ff9mapkit.world import coastmorph as CM
    CM.beach_mint(DONOR, land=2.6)
    CM.beach_mint(DONOR, width=3.0, land=2.0)
    with pytest.raises(ValueError, match="ribbon"):
        CM.beach_mint(DONOR, land=3.0)


def test_beach_mint_probes_the_swash_ceiling():
    """The width knob's lawful ceiling on (7,17) is set by the SWASH envelope (band +
    swash share the pinned L->W corridor): 4.6 builds, 5.0 refuses."""
    from ff9mapkit.world import coastmorph as CM
    CM.beach_mint(DONOR, width=4.6)
    with pytest.raises(ValueError, match="swash width"):
        CM.beach_mint(DONOR, width=5.0)
    with pytest.raises(ValueError, match="ribbon"):
        CM.beach_mint(DONOR, width=1.0)


def test_cap_rebuild_refuses_the_spit():
    """(3,11) is the double-sided SPIT: its caps are the BR/subdivided tip vocabulary
    (out of the quad-cap laws' scope) and its sand caps ride the fold -- nothing
    lawful to rebuild, so the tool refuses rather than half-emit."""
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="no lawful end caps"):
        CM.cap_rebuild((3, 11))


def test_cliff_clearance_gate():
    """THE CLEARANCE GATE -- the cliff shape law: cliffs are class-free (a headland on a
    bay rim read clean in-game, (16,9)) and push shear is harmless (the wall REBUILDS --
    81-degree crest shear proven), so the real hazard is the pushed outline PINCHING.
    (21,10)'s first headland window at D=8 pushes to ~1.2u of itself (was the riskiest
    line in the pre-gate catalog); the proven wild rim (16,9) D=8 (5.6u clear) passes."""
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="CLEARANCE GATE"):
        CM.cliff_headland((21, 10), (1344.9609, -651.6719), (1344.0, -662.543), 8.0)
    tw = CM.cliff_headland((16, 9), (1064.0, -640.0), (1024.0, -588.0), 8.0)
    assert len(tw) == 5


def test_coast_scanner_finds_the_proven_windows():
    """The coast window scanner on (7,17): re-discovers the proven morph windows with
    the proven ceilings, probing the REAL builders (the gates are the oracle) and
    certifying each ceiling through a morph_in_place dry-run. The cliff search is
    refusal-steered: 'window gap K' and 'touches seaX first at (X,Z)' refusals name the
    cut points, so the maximal island base run converges to the lawful NE window."""
    from ff9mapkit.world import coastscan as CS
    ws = CS.scan_block(*DONOR)
    beach = next(w for w in ws if w["kind"] == "beach")
    assert beach["class"] == "pocket"
    bump = beach["probes"]["beach-bump"]
    assert bump["seaward"] is None                   # the shape-class law
    assert "SHAPE-CLASS" in bump["seaward_binding"]
    assert bump["landward"] == -2.5
    assert beach["probes"]["beach-reshape"]["landward"] == -1.0
    # the full-assembly slide: landward-only v1, and its ceiling on this window is the
    # verb's own hard cap (-6) -- every gate (class/slope/strip-census/graded-ladder
    # water re-lay/T-vertex) clears; deepest-first probing matters (the -2..-2.5
    # band-gate valley must not settle the ladder)
    slide = beach["probes"]["beach-slide"]
    assert slide["seaward"] is None                  # a pocket: class/hug refuse seaward
    assert slide["landward"] == -6.0
    cliff = next(w for w in ws if w["kind"] == "cliff")
    assert cliff["probes"]["cliff-headland"]["depth"] == 8.0
    assert cliff["probes"]["cliff-bay"]["depth"] == 6.0
    assert cliff["probes"]["cliff-bump"]["depth"] == 2.0
    # every discovered cliff window shares the proven NE run
    assert cliff["probes"]["cliff-headland"]["window"][0][0] == 480.0


def test_coast_scanner_nose_block():
    """(18,15): the scanner reports the in-game-proven nose ceiling (+2.5 seaward, the
    deployed in-place morph), the reshape's structural refusal on a free-form shore,
    and the SEAWARD SLIDE's probed ceiling (+2.5, water-strain-bound at the frame --
    the grass-berm nose rung: verbatim band + native grass growth at bump depth)."""
    from ff9mapkit.world import coastscan as CS
    ws = CS.scan_block(18, 15, verbs=("beach-bump", "beach-reshape", "beach-slide"))
    beach = next(w for w in ws if w["kind"] == "beach")
    assert beach["class"] == "nose"
    assert beach["probes"]["beach-bump"]["seaward"] == 2.5
    assert "lattice columns" in beach["probes"]["beach-reshape"]["seaward_binding"]
    slide = beach["probes"]["beach-slide"]
    assert slide["seaward"] == 2.5
    # landward on a nose: the class law refuses every rung (the mirror of the pocket)
    assert slide["landward"] is None


def test_headland_grain_and_widths_stay_lawful():
    from ff9mapkit.world import coastmorph as CM
    _, _, _, emit_t, _ = CM.cliff_headland(DONOR, START, END, 8.0)
    longest = max(max(math.dist(t3[i][0], t3[(i + 1) % 3][0]) for i in range(3))
                  for t3 in emit_t.tris[16:])                # the grass fill
    assert longest <= CM.MAX_GRAIN


#: the band-conversion probe's build hash ((116,-281) sea3 -> sea1 on (7,17))
GOLDEN_BAND_CONVERT_HASH = "7200da988a77d486"


def test_band_convert_golden():
    """RUNG 3, step 1 -- THE ONE-CELL BAND-CONVERSION on (7,17)'s beach-west ring
    ((116,-281) sea3 -> sea1, the virgin mint's ring re-band in miniature): C emits
    as a fresh lattice strip tile for its depth-fact edge-set {S,W}, and the two
    CONFORMING sea1 neighbours re-emit under their new shade fields via the
    deformed-tile rect law -- (117,-281) {S,W} -> {S} (row 3 -> row 0) and
    (116,-280) {N,S,W} -> {N,W}: the first genuinely FRESH deformed-tile emissions
    (rects chosen, not transported). Geometry/normals/IDALL verbatim."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    tw = CM.band_convert(DONOR, (116, -281), "sea1")
    led = [(t.part, t.expected if hasattr(t, "keys") else len(t.tris)) for t in tw]
    assert led == [("sea3", 2), ("sea1", 2), ("sea1", 4), ("sea1", 4)]
    assert _tweak_hash(tw) == GOLDEN_BAND_CONVERT_HASH
    assert _tweak_hash(tw) == _tweak_hash(CM.band_convert(DONOR, (116, -281), "sea1"))
    # geometry, normals and IDALL transport VERBATIM -- only uvs (and C's part)
    # change: every emitted tri's (pos, normal, tangent) signature exists in stock
    stock = {p: TR.world_tris(*DONOR, p) for p in ("sea1", "sea3")}

    def sig(t3):
        return tuple(sorted((CM._pk(v[0]), tuple(v[1]), tuple(v[3])) for v in t3))
    old_sigs = {sig(t3) for p in stock for t3 in stock[p]}
    assert all(sig(t3) in old_sigs for t in (tw[1], tw[3]) for t3 in t.tris)
    # C's tile: a lattice quad on the block's own exact floats, decoding to {S, W}
    cuv = {(round(v[2][0] * 1024, 1), round(v[2][1] * 1024, 1))
           for t3 in tw[1].tris for v in t3}
    assert cuv == {(0.0, 766.0), (0.0, 1024.0), (1007.7, 766.0), (1007.7, 1024.0)}
    assert all(TR.strip_edge_set(t3) == frozenset("SW") for t3 in tw[1].tris)
    # the re-emissions are FRESH: every re-emitted tile's uv rect differs from the
    # donor's original at that tile (the row change is the visible law choice)
    old_uv = {frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                        for v in t3) for t3 in stock["sea1"]}
    assert all(frozenset((CM._pk(v[0]), round(v[2][0], 4), round(v[2][1], 4))
                         for v in t3) not in old_uv for t3 in tw[3].tris)
    # ... and re-decode as one rect group each under the deformed-tile law
    kinds = [k for _g, k, _d in CM._deformed_strip_groups(tw[3].tris)]
    assert kinds and all(k == "rect" for k in kinds)


def test_band_convert_refusals():
    """The v1 scope refusals, each an actionable law: a 4-deep open-ocean cell has
    no lawful strip; the sea4->sea5 site beside the one-deep ring tile CASCADES
    (the neighbour's edge-set would empty); a strip-band source needs its own
    re-band; a frame-ring cell's shade field crosses blocks; a mixed-dialect block
    refuses at the vocabulary."""
    import pytest
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="no learned strip"):
        CM.band_convert(DONOR, (114, -283), "sea5")      # open sea4: edge-set {E,N,S,W}
    with pytest.raises(ValueError, match="cascades"):
        CM.band_convert(DONOR, (116, -283), "sea5")      # (117,-283) {W} would empty
    with pytest.raises(ValueError, match="non-strip band"):
        CM.band_convert(DONOR, (115, -281), "sea1")      # sea5 source: out of v1 scope
    with pytest.raises(ValueError, match="frame ring"):
        CM.band_convert(DONOR, (112, -281), "sea1")
    with pytest.raises(ValueError, match="mixed strip v-dialect"):
        CM.band_convert((18, 15), (300, -245), "sea1")


def test_virgin_mint_golden():
    """BEACH-MINT rung 3 -- THE VIRGIN-SHORE MINT at the census winner (9,17), run
    (153..155,-282): a new beach synthesized on the bare south face of the grass
    peninsula, no donor beach to pin to. The ledger pins the full composition: the
    berm clip (12 terrain dropped -> berm fragments + the minted sand band), the
    foam assembly, the wash zip (sea2 fragments with continued uvs), the (155,-283)
    sea1 drop under the swash, and THE RING RE-BAND -- the (156,-283) conforming
    sea3 quad flips to sea1 by corner-role assignment (the deformed-tile rect law)
    with the (156,-284) neighbour re-emitted under its new deep-edge-set {E,S}."""
    from ff9mapkit.world import coastmorph as CM
    tw = CM.virgin_mint((9, 17), (619.2, -1128.2), (623.8, -1127.6))
    led = [(t.part, ("drop", t.expected) if hasattr(t, "keys")
            else ("emit", len(t.tris))) for t in tw]
    assert led == [("terrain", ("drop", 12)), ("terrain", ("emit", 34)),
                   ("beach1", ("emit", 8)),
                   ("sea2", ("drop", 2)), ("sea2", ("emit", 7)),
                   ("sea1", ("drop", 4)), ("sea1", ("emit", 5)),
                   ("sea3", ("drop", 2))]
    assert _tweak_hash(tw) == "56a73347d9bbe571"
    # the ring re-band is present and generative: among the sea1 emissions, the
    # re-banded (156,-283) CONFORMING quad carries the block's strip dialect
    # (corner-role assignment -- a lattice decode cannot read a deformed tile;
    # the builder's own re-decode gate pins the exact placement)
    sea1_emit = next(t.tris for t in tw
                     if getattr(t, "part", None) == "sea1" and hasattr(t, "tris"))
    ring = [t3 for t3 in sea1_emit if CM._cell_of_tri(t3) == (156, -283)]
    assert len(ring) == 2
    us = {round(v[2][0], 6) for t3 in ring for v in t3}
    assert us <= {0.0, 0.984127}                      # the block's strip u dialect
    groups = list(CM._deformed_strip_groups(ring))
    assert len(groups) == 1 and groups[0][1] == "rect"


def test_virgin_mint_refusals():
    """The refusal-steered envelope: anchors hugging the existing beach fail THE
    GRASS-TONGUE LAW; a stub arc fails the along-shore column envelope; an
    off-coast anchor refuses outright."""
    import pytest
    from ff9mapkit.world import coastmorph as CM
    with pytest.raises(ValueError, match="[Gg]rass-tongue"):
        CM.virgin_mint((9, 17), (617.0, -1128.6), (623.8, -1127.6))
    with pytest.raises(ValueError, match="along-shore envelope"):
        CM.virgin_mint((9, 17), (622.5, -1127.7), (623.8, -1127.6))
    with pytest.raises(ValueError, match="off the shoreline"):
        CM.virgin_mint((9, 17), (600.0, -1100.0), (623.8, -1127.6))


def test_virgin_mint_deep_shore_golden():
    """THE REAL-SCALE CONTINENT MINT (v2): bank_lower + virgin_mint with pre= /
    pins_from= / the deep-shore LADDER SYNTHESIS on (10,18)'s islet (continent
    island B -- zero beaches, a ~4u mesa bank, sea3/sea5/sea4 all around). The
    bank sinks to a cay profile (shore verts pinned); the mint computes on the
    post-reshape geometry; cut deep tiles re-band to WASH (mains, position-
    evaluated); and the plan-then-emit LADDER REPAIR steps every introduced
    unlawful pair one band down ({wash|4} -> 4->5 -> 5->1) until the whole
    synthesized ladder is lawful -- including 34 sea4 tiles."""
    from ff9mapkit.world.coastmorph import bank_lower, virgin_mint
    # the corridor bank (playtest-steered): the sink hugs the cove chord so the
    # islet's crown + far walls keep ~92% of their natural height (a radial
    # reach flattened the whole rim -- "shrunken cliffs confirmed")
    pre = bank_lower((10, 18), (674.0, -1168.4), radius=7.0, shore_slope=0.75,
                     cap=3.6, along=((666.9, -1168.6), (681.1, -1168.2)))
    tw = virgin_mint((10, 18), (666.9, -1168.6), (681.1, -1168.2),
                     width=3.6, swash=4.4, pre=pre, pins_from=(7, 17))
    led = [(getattr(t, "part", None),
            ("drop", t.expected) if hasattr(t, "keys")
            else ("emit", len(t.tris)) if hasattr(t, "tris")
            else ("displace", t.expected)) for t in pre + tw]
    # the pre = [wall drops, the sink, the re-pinned walls] (CLIFF V NEVER
    # DRAGS + THE LIP ANCHOR, per column -- the 14th face is the seam closure:
    # a tri holding a cropped base vert but no moved vert); the mint's terrain
    # drop reconciled down to 4 (walls it consumes cancel against the pre's
    # emissions -- they are simply never re-emitted)
    assert led == [("terrain", ("drop", 14)), (None, ("displace", 25)),
                   ("terrain", ("emit", 8)),
                   ("terrain", ("drop", 4)), ("terrain", ("emit", 19)),
                   ("beach1", ("emit", 18)),
                   ("sea2", ("emit", 29)), ("sea1", ("emit", 22)),
                   ("sea3", ("drop", 14)),
                   ("sea5", ("drop", 16)), ("sea5", ("emit", 22)),
                   ("sea4", ("drop", 34))]
    assert _tweak_hash(pre + tw) == "6c3d0ba4365adef5"
    # real-scale check: 4 columns over the ~14.8u arc (the whole point)
    foam = next(t.tris for t in tw
                if getattr(t, "part", None) == "beach1" and hasattr(t, "tris"))
    assert len(foam) == 18


def test_shore_spec_parsers():
    """The CLI spec grammar for the productized island-B pattern: positional
    tails + named segments, round-tripping into the build_shore_tweaks dicts."""
    from ff9mapkit.world.coastmorph import (parse_bank_lower_spec,
                                            parse_virgin_mint_spec)
    b = parse_bank_lower_spec("674.0,-1168.4:7.0:0.75:3.6:"
                              "along=666.9,-1168.6/681.1,-1168.2")
    assert b == {"center": [674.0, -1168.4], "radius": 7.0, "shore_slope": 0.75,
                 "cap": 3.6, "along": [[666.9, -1168.6], [681.1, -1168.2]]}
    assert parse_bank_lower_spec("10,-20:5") == {"center": [10.0, -20.0],
                                                 "radius": 5.0}
    m = parse_virgin_mint_spec("666.9,-1168.6:681.1,-1168.2:3.6:4.4:pins=7,17")
    assert m == {"start": [666.9, -1168.6], "end": [681.1, -1168.2],
                 "width": 3.6, "swash": 4.4, "pins_from": [7, 17]}
    assert parse_virgin_mint_spec("1,2:3,4") == {"start": [1.0, 2.0],
                                                 "end": [3.0, 4.0]}
    # named segments are order-free relative to the positional tail
    m2 = parse_virgin_mint_spec("1,2:3,4:pins=7,17:3.6")
    assert m2["pins_from"] == [7, 17] and m2["width"] == 3.6
    for bad, fn in (("674,-1168", parse_bank_lower_spec),
                    ("1,2:3,4:5:6:7", parse_virgin_mint_spec),
                    ("1,2:3:oops=1", parse_bank_lower_spec)):
        with pytest.raises(ValueError):
            fn(bad)


def test_build_shore_tweaks_matches_the_proven_island_b_build():
    """THE PRODUCTIZATION PROOF: the declarative dicts (the fuse layout's
    [placement.bank_lower]/[placement.virgin_mint] tables = the parsed CLI
    specs) build a tweak list BYTE-IDENTICAL to the proven hand-scripted
    island-B deploy -- same golden hash as test_virgin_mint_deep_shore_golden.
    Each verb's block derives from its own spec coords ((10,18) here, inside
    the (10,17)+2x2 region); foreign coords refuse actionably."""
    from ff9mapkit.world.coastmorph import build_shore_tweaks
    bank = {"center": [674.0, -1168.4], "radius": 7.0, "shore_slope": 0.75,
            "cap": 3.6, "along": [[666.9, -1168.6], [681.1, -1168.2]]}
    mint = {"start": [666.9, -1168.6], "end": [681.1, -1168.2],
            "width": 3.6, "swash": 4.4, "pins_from": [7, 17]}
    tweaks, notes = build_shore_tweaks((10, 17), (2, 2), bank=bank, mint=mint)
    assert _tweak_hash(tweaks) == "6c3d0ba4365adef5"
    assert notes == ["bank_lower @ block (10, 18) (corridor)",
                     "virgin_mint @ block (10, 18) (pins from (7, 17))"]
    # the region gate: coords outside the placement region refuse
    with pytest.raises(ValueError, match="outside the placement region"):
        build_shore_tweaks((10, 17), (1, 1), bank=bank)   # (10,18) not in 1x1
    with pytest.raises(ValueError, match="outside the placement region"):
        build_shore_tweaks((9, 5), (2, 3), mint=mint)


def test_fuse_layout_stateful_tweaks_guard():
    """A layout REAL deploy refuses plain 'tweaks' actionably: tweak objects are
    STATEFUL and fuse_layout applies each placement twice (the gate pass + the
    deploy pass) -- tweaked placements pass 'tweaks_factory' instead, rebuilt
    fresh per pass."""
    from ff9mapkit.world import fuse as FU
    with pytest.raises(ValueError, match="tweaks_factory"):
        FU.fuse_layout("UNUSED-guard-test",
                       [{"cell": (2, 16), "donor": (10, 18), "size": (1, 1),
                         "tweaks": [object()]}], dry_run=False)


def test_bank_lower_wall_lip_anchor():
    """THE LIP ANCHOR, per COLUMN (the round-4 gash fix). The rock strip's V is
    a CORNER ASSIGNMENT (byte-checked map-wide: crest 0.8926 / base 0.9229 on
    every face 0.9..5.5u tall; the strip never wraps), so a sink must keep every
    crest v VERBATIM (the lip survives -- no hard/bevel alternation) and crop
    each base v along its own column at the column's original density. A
    per-FACE affine cannot do this: it seams at shared columns and pushes v
    outside the strip (playtest round 4: white gashes + grass bleeding)."""
    from collections import defaultdict

    from ff9mapkit.world import transplant as TR
    from ff9mapkit.world.coastmorph import bank_lower
    from ff9mapkit.world.extract import decode_id

    pre = bank_lower((10, 18), (674.0, -1168.4), radius=7.0, shore_slope=0.75,
                     cap=3.6, along=((666.9, -1168.6), (681.1, -1168.2)))
    drops = next(t for t in pre if hasattr(t, "keys"))
    emits = next(t for t in pre if hasattr(t, "tris"))
    terr = TR.world_tris(10, 18, "terrain")
    topo = lambda t3: decode_id(int(round(t3[0][3][0])))["topograph"]
    band = [t3 for t3 in terr if topo(t3) == 58]
    v_lo = min(v[2][1] for t3 in band for v in t3)
    v_hi = max(v[2][1] for t3 in band for v in t3)
    assert (round(v_lo, 4), round(v_hi, 4)) == (0.8926, 0.9229)
    # original uv pairs per plan position (y sinks; x/z never move)
    band_by_plan = defaultdict(set)
    for t3 in band:
        for v in t3:
            band_by_plan[(round(v[0][0], 4), round(v[0][2], 4))].add(
                (v[2][0], v[2][1]))
    for t3 in emits.tris:
        # the LIP survives on every emitted face: its minimum v IS the lip row
        assert min(v[2][1] for v in t3) == v_lo
        for (pos, nrm, uv, tan) in t3:
            # THE V-IN-BAND GATE's invariant: inside the byte-derived strip band
            assert v_lo - 1e-4 <= uv[1] <= v_hi + 1e-4
            pairs = band_by_plan[(round(pos[0], 4), round(pos[2], 4))]
            # u is untouched, and a crop only ever SHEDS deep rows (v never
            # rises above the vert's own original row)
            assert any(u == uv[0] and uv[1] <= v_ + 1e-9 for (u, v_) in pairs)
    # seam closure: a surviving wall tri never disagrees with an emission at a
    # shared vert (every changed-v vert lives only in dropped+re-emitted faces)
    emit_by_plan = {}
    for t3 in emits.tris:
        for v in t3:
            emit_by_plan[(round(v[0][0], 4), round(v[0][2], 4), v[2][0])] = v[2][1]
    for t3 in band:
        if drops._key_set(t3) in drops.keys:
            continue
        for v in t3:
            got = emit_by_plan.get((round(v[0][0], 4), round(v[0][2], 4), v[2][0]))
            assert got is None or got == v[2][1], \
                "a surviving wall tri disagrees with an emission at a shared vert"


# --- THE SAND-BAND FAMILIES (the beach translation law, 2026-07-15) ---------------------

def test_sand_band_families_registry():
    """The desert band's measured constants (the desert-beach study): u-strip exactly
    +335/1024 texels from grass, single-valued v pins run 548->579 / cap 580->611,
    an eps under half the 1-texel run-seam/cap-land gap."""
    from ff9mapkit.world import coastmorph as CM
    assert set(CM.SAND_BANDS) == {"grass", "desert"}
    g, d = CM.SAND_BANDS["grass"], CM.SAND_BANDS["desert"]
    assert (g["topo"], g["du"]) == (31, 0.0)
    assert (d["topo"], d["du"]) == (32, 335.0 / 1024)
    assert d["v_land"] == (0.53516,) and d["v_seam"] == (0.56543,)
    assert d["v_cap_land"] == (0.56641,) and d["v_cap_seam"] == (0.59668,)
    assert d["eps_v"] < (0.56641 - 0.56543) / 2.0
    # grass wiring unchanged (the 44 golden tests above are the byte proof)
    assert g["v_land"] is CM.SAND_V_LAND and g["v_seam"] is CM.SAND_V_SEAM


def test_desert_band_decodes_and_rebuilds():
    """The family auto-detection + decoder on a REAL desert beach block ((20,5): run 39
    cap 2), and sand_rebuild's emission self-check runs green under the desert rects."""
    from ff9mapkit.world import coastmorph as CM
    from ff9mapkit.world import transplant as TR
    terr = TR.world_tris(20, 5, "terrain", disc=1)
    fam = CM._sand_band_family(terr, what="(20,5)")
    assert fam is not None and fam["name"] == "desert" and fam["topo"] == 32
    from ff9mapkit.world.extract import decode_id
    sand = [t3 for t3 in terr
            if decode_id(int(round(t3[0][3][0])))["topograph"] == 32]
    dec = [CM._sand_tri_decode(t3, fam) for t3 in sand]
    n_run = sum(1 for x in dec if x and x[0] == "run")
    n_cap = sum(1 for x in dec if x and x[0] == "cap")
    assert n_run >= 30 and n_cap >= 1
    # the identity rebuild re-derives desert columns (rect flip + re-decode gate)
    tw = CM.sand_rebuild((20, 5), disc=1)
    assert sum(len(t.tris) for t in tw if type(t).__name__ == "EmitTris") >= 20


def test_morph_in_place_refuses_absent_part_emission():
    """THE (18,3) INCIDENT: an in-place morph must REFUSE a tweak that emits into a
    part the real cell does not carry (its prefab has no transform to bind an
    override to) -- never silently drop the emission while gates read clean."""
    from ff9mapkit.world import transplant as TR

    class _FakeEmit:
        part = "beach1"

        def apply(self, part, poly):
            return poly

        def emit(self):
            v = ((1.0, 0.0, -1.0), (0.0, 1.0, 0.0), (0.0, 0.0), (0.0, 0.0, 0.0, 0.0))
            return [(v, v, v)]

        def gate(self):
            return {"gate": "emit[beach1]", "ok": True}

    with pytest.raises(ValueError, match="carries no 'beach1'|could never render"):
        TR.morph_in_place("FF9CustomMap-ptest", cell=(18, 3),
                          tweaks=[_FakeEmit()], dry_run=True)
