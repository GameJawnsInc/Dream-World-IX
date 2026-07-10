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


def test_structural_refuses_a_grassless_top():
    from ff9mapkit.world import coastmorph as CM
    # the (9,5) continent-island-A donor has ZERO grass (highland/mural top families) --
    # the baked-terrain law: no fill language, so structural morphs refuse cleanly and
    # only the conforming bow applies. Window = a clean run on block (10,6).
    with pytest.raises(ValueError, match="no grass mains"):
        CM.cliff_headland((10, 6), (695.6, -407.9), (680.0, -436.0), 6.0)


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
