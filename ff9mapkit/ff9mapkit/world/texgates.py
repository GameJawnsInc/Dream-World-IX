"""THE TEXTURE + SEA GATES -- the Rung-F UV/relief arc's acceptance criteria, productized as
carry-time / mint-time gates so no kit mint path can ship the defect classes that cost that arc
eight in-game rounds.

PROVENANCE.  Every predicate here was proven on real bytes in
``studies/overworld-topography/`` and folded back through
``studies/overworld-topography/composite_gates.py`` (THE GENERATOR FOLD-BACK, 2026-07-25):

  :func:`zero_uv_area_gate`  <- ``uvf_gates.gate1_uv_validity``          (frac ceiling 0.0005)
  :func:`one_window_gate`    <- ``uvf_gates4.family_window_coherence_check`` (THE ONE-WINDOW-PER-TRI
                                LAW: a synthesized tri's three UVs come from ONE (cell,quad,ori)
                                window, resolved in its OWN family's ``grassland.ground_uv`` space)
  :func:`family_rect_gate`   <- ``uvf_gates4.family_rect_membership_check`` (REGION_EPS 0.006)
  :func:`sea_plan_gate`      <- ``uvf_gates.gate2_sea_plan_disjoint``    (the 3-predicate sea gate:
                                A calibrated submerged-TRI Y-order, B <=4x adjacent-block Sea4
                                uniformity, C real-sea/land plan-disjoint with the Sea4 deep
                                underlay AND 1-tri hidden placeholders excluded)

THE DEFECT CLASS these exist for (round 1 of that arc, in-game visible): a synthesizer that emits ONE
CONSTANT ``(uv, topo)`` for every vertex it mints -- the flat-sheet stain.  A constant UV collapses the
triangle's UV area to zero (gate 1 sees it), and any mis-scaled or mis-based window walks the UVs out
of the family's catalogued mains rect (gate 3 sees it).  Gate 2 is the positive form of the same law.

GATE SHAPE.  Every function here returns the SAME ``{"gate": ..., "ok": ..., "warn": ..., "enforced":
...}`` dict shape that :func:`~ff9mapkit.world.transplant.wang_carry_gate` and
:func:`~ff9mapkit.world.orphangate.orphan_decal_gate` already return, and follows their exact policy:
**WARN by default** (``ok`` stays ``True``, a ``warn`` flag surfaces the finding), ``enforce=True``
hard-fails, ``allow=True`` waives even when enforced.  Every gate here is PURELY READ-ONLY -- it never
mutates a byte of any BlockMesh it inspects, so wiring it into an existing carry/mint path changes
zero output bytes.

INPUT.  Pure functions over a BlockMesh set: ``cell_meshes`` = ``{(bx,by): [(part_name, BlockMesh),
...]}`` (exactly :func:`~ff9mapkit.world.transplant.transplant`'s / ``transplant_region``'s just-built,
pre-write tri set, and exactly ``orphangate``'s own parameter), ``region_cells`` = the set of
``(bx,by)`` blocks that are OURS to report.  No disk access, no install reads, no ring context.

THE CALIBRATION THAT SHAPED :func:`one_window_gate` (measured 2026-07-25 against READ-ONLY stock
disc-1 bytes; ``studies/overworld-topography/out/foldback/texgates_calibration_raw.json``).  A
blind lattice search -- "does SOME (cell,quad,ori) in the 4 candidate cells x 4 quads x 4 oris
reproduce this tri's three UVs?" -- reproduces only a small minority of REAL stock ground:

    stock Cleyra 13-15,11-12   : 4.2% / 5.3% / 10.7% / 6.1% / 7.9% / 4.2%   (n = 212/114/169/99/227/192)
    stock grass  (15,15)/(16,14): 18.5% / 11.9%                              (n = 286/268)
    stock dunes  (18,3)/(19,3) : 6.4% / 3.2%                                 (n = 233/217)

That is not a defect: :mod:`~ff9mapkit.world.grassland`'s own docstring records that real ground
SLIDES FREE FRACTIONAL WINDOWS over its painted-over internal gutter, so a stock tri's window is
usually off the locked 2x2 quadrant lattice this kit mints on.  A UV-SPAN form of the same test
("all three UVs inside one quadrant-rect-sized box") fares worse still on stock (0.3%-13.2%),
because a lawful stock ground tri routinely spans several 4u cells.  PER THE PROJECT LAW
*calibrate the instrument before you judge with it*, :func:`one_window_gate` therefore REFUSES to
judge blind: with no ``quad_ori`` field supplied it reports ``skipped`` and passes.  It gates only
when the CALLER (a generator -- :func:`~ff9mapkit.world.island.build_landmass`, a fill/retile
synthesizer) hands over the very ``{cell: (quad, ori)}`` field it minted with, which is the only
context in which the law is even defined.  Gates 1 and 3 need no such scoping: both measure
**1.000 clean** on all ten stock blocks above (0 zero-uv-area tris, 0 bit-identical-UV tris, and
2017/2017 mains-wearing ground tris inside their own family's mains rect).

SCOPE OF THE MAINS SELECTOR.  Gates 2 and 3 judge only MAINS-WEARING GROUND tris:
``grassland.TOPO_FAMILY`` maps the tri's topograph to a ground family with an entry in
``grassland.GROUNDS``, AND at least one of its three UVs already lies inside that family's own
:func:`~ff9mapkit.world.grassland.ground_main_region` rect.  That selector deliberately excludes the
rock/cliff band, the meadow (D) stamp set and the STRIPS transition vocabulary -- content that
lawfully lives in other atlas rects and is the ORPHAN-DECAL gate's business, not this module's.  On
stock it selects exactly the plain ground and finds it 100% lawful (above), so it never
false-positives on a verbatim carry.
"""
from __future__ import annotations

import math

from . import grassland as GL
from .extract import block_world_origin, decode_id

CELL = 4.0

#: zero-UV-area: a tri whose three UVs span no atlas area at all (the constant-UV stamp's signature).
ZERO_UV_AREA_EPS = 1e-6
#: ``uvf_gates.GATE1_FRAC_CEILING`` (uvf_gates.py:70) -- world slivers legitimately collapse at this rate.
ZERO_UV_FRAC_CEILING = 0.0005
#: all three UVs bit-identical -- the pure constant stamp; stock measures ZERO, so the floor is 0.
BIT_IDENTICAL_EPS = 1e-6
#: ``uvf_gates4.py:72`` -- the same ceiling family as gate 1.
ONE_WINDOW_FRAC_CEILING = 0.0005
#: reconstruction tolerance, ``uvf_gates4.family_window_coherence_check``.
ONE_WINDOW_UV_TOL = 5e-6
#: ``transplant.GroundRetile._EPS`` / ``uvf_gates4.py:73`` -- the mains-rect membership slack.
REGION_EPS = 0.006
#: sea predicate B: adjacent touched blocks' Sea4 plan-area ratio (``uvf_gates.GATE2B_RATIO_CEILING``).
SEA_UNIFORMITY_CEILING = 4.0
#: sea predicate C: stock ``grass_coast`` sea/land plan-overlap headline (``uvf_gates.GATE2C_OVERLAP_CEILING``).
SEA_OVERLAP_CEILING = 0.1913
#: everything EXCEPT Sea4 (the deep-ocean underlay, which lawfully lies UNDER land).
SEA_REAL_PARTS = ("sea1", "sea2", "sea3", "sea5", "beach1", "beach2")
SEA_UNDERLAY_PART = "sea4"
#: a part with this many tris or fewer is a hidden convention placeholder, not real water.
PLACEHOLDER_MAX_TRIS = 1
#: matches :data:`ff9mapkit.world.orphangate.STUB_Y_FLOOR` -- blanking-stub tris are not content.
STUB_Y_FLOOR = -50.0


# ====================================================================================================
#  record extraction (pure, read-only)
# ====================================================================================================
def _part_tris(cell_meshes, region_cells, part_names):
    """``[(block, part_name, BlockMesh)]`` for every part of every REPORTED block whose lowercased
    name is in ``part_names``."""
    region = {tuple(c) for c in region_cells}
    out = []
    for block, parts in cell_meshes.items():
        blk = tuple(block)
        if blk not in region:
            continue
        for pn, bm in parts:
            if pn.lower() in part_names:
                out.append((blk, pn.lower(), bm))
    return out


def terrain_records(cell_meshes, region_cells) -> list:
    """One record per Terrain triangle of every REPORTED block: ``block``, ``cell`` (the 4u lattice
    cell of the CENTROID), ``tri_idx``, ``topo``, ``fam`` (``grassland.TOPO_FAMILY``, or ``None``),
    ``world_pts``, ``uv``.  Below-:data:`STUB_Y_FLOOR` blanking-stub tris are skipped.  Deliberately
    the same record shape :func:`~ff9mapkit.world.orphangate.flatten_terrain_records` emits, minus its
    ring-context merge (this module never reads disk)."""
    out = []
    for (blk, _pn, bm) in _part_tris(cell_meshes, region_cells, ("terrain",)):
        ox, oz = block_world_origin(*blk)
        verts, uvs, tans = bm.verts, bm.uvs, bm.tangents
        for tri in bm.tris:
            wpts = [(verts[j][0] + ox, verts[j][1], verts[j][2] + oz) for j in tri]
            if all(p[1] <= STUB_Y_FLOOR for p in wpts):
                continue
            topo = decode_id(int(round(tans[tri[0]][0])))["topograph"]
            cx = sum(p[0] for p in wpts) / 3.0
            cz = sum(p[2] for p in wpts) / 3.0
            out.append(dict(block=blk, tri_idx=list(tri), topo=topo, fam=GL.TOPO_FAMILY.get(topo),
                            world_pts=wpts, uv=[tuple(uvs[j]) for j in tri],
                            cell=(math.floor(cx / CELL), math.floor(cz / CELL))))
    return out


def mains_records(records) -> list:
    """THE MAINS SELECTOR (see the module docstring): the subset of ``records`` that is plain,
    mains-wearing GROUND -- a ``grassland.GROUNDS`` family by topograph, already claiming that
    family's own mains rect with at least one UV corner.  Excludes rock/cliff, the meadow (D) stamp
    set and the STRIPS transition vocabulary by construction.

    THE SELECTOR IS UV-BASED ON PURPOSE, AND THAT HAS A KNOWN BLIND SPOT.  A defect that walks a
    tri's UVs entirely OUT of its family's rect also walks it out of this selector, so gates 2 and 3
    stop seeing it -- :func:`zero_uv_area_gate` (topo-agnostic, every Terrain tri, 0 on stock) is the
    catch for that shape, and :func:`escaped_records` counts it as an advisory.  The alternative --
    selecting by topograph alone and demanding membership of SOME catalogued rect -- was measured and
    REJECTED: on ten stock blocks 184 of 2952 ground-topo tris (6.2%) wear a rect this kit has not
    catalogued at all (murals and uncatalogued decals; the Rung-F fold's own carried-uncatalogued
    census found the same class), so that form would refuse a verbatim stock carry outright."""
    out = []
    for r in records:
        fam = r["fam"]
        if fam is None or fam not in GL.GROUNDS:
            continue
        lo_u, lo_v, hi_u, hi_v = GL.ground_main_region(fam)
        if any(lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
               and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS for (u, v) in r["uv"]):
            out.append(r)
    return out


def escaped_records(records) -> list:
    """ADVISORY population: ground-topograph tris that claim NO family's mains rect at all.  On real
    stock this is 6.2% (184/2952 over ten blocks) -- murals and uncatalogued decals -- so it is
    REPORTED, never gated.  It exists so a caller can see the shape :func:`mains_records`' UV-based
    selector is blind to (a UV stamp that lands off every rect)."""
    out = []
    for r in records:
        fam = r["fam"]
        if fam is None or fam not in GL.GROUNDS:
            continue
        lo_u, lo_v, hi_u, hi_v = GL.ground_main_region(fam)
        if not any(lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
                   and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS for (u, v) in r["uv"]):
            out.append(r)
    return out


def uv_area(uv3) -> float:
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return abs((u1 - u0) * (v2 - v0) - (u2 - u0) * (v1 - v0)) / 2.0


def uv_pairwise_maxdist(uv3) -> float:
    (u0, v0), (u1, v1), (u2, v2) = uv3
    return max(max(abs(u0 - u1), abs(v0 - v1)), max(abs(u0 - u2), abs(v0 - v2)),
               max(abs(u1 - u2), abs(v1 - v2)))


def plan_area_xz(w3) -> float:
    (x0, z0), (x1, z1), (x2, z2) = w3
    return abs((x1 - x0) * (z2 - z0) - (x2 - x0) * (z1 - z0)) / 2.0


def _gate(name, *, enforce, allow, dirty, detail, **extra):
    """The shared gate dict -- :func:`~ff9mapkit.world.transplant.wang_carry_gate`'s exact composition,
    verbatim: ``ok = allow or (not enforce) or not dirty``, and ``warn`` only in the default
    report-only mode (dirty, not enforced, not waived)."""
    d = {"gate": name}
    d.update(extra)
    d["enforced"] = bool(enforce)
    d["warn"] = bool(dirty) and not enforce and not allow
    d["detail"] = detail if detail else 0
    d["ok"] = bool(allow or (not enforce) or not dirty)
    # the honest headline key (audit rec 9): `ok` is the DEPLOY verdict (True under
    # WARN-default even when dirty); `status` is the REPORTING truth -- a CLI headline
    # derived from `ok` alone printed "gates CLEAN" in the same breath as a warn row.
    d["status"] = "fail" if not d["ok"] else ("warn" if d["warn"] else "pass")
    return d


# ====================================================================================================
#  GATE 1 -- ZERO-UV-AREA (uvf_gates.gate1_uv_validity)
# ====================================================================================================
def zero_uv_area_gate(cell_meshes, region_cells, *, enforce: bool = False, allow: bool = False,
                      records=None) -> dict:
    """THE CONSTANT-UV-STAMP GATE.  Over every Terrain tri of ``region_cells``: the fraction whose UV
    triangle has no area must stay <= :data:`ZERO_UV_FRAC_CEILING`, and NO tri may have all three UVs
    bit-identical (the pure constant stamp -- stock measures zero of those, so the floor is 0).

    Body: ``uvf_gates.gate1_uv_validity``, re-expressed over an in-memory BlockMesh set instead of a
    staged tree.  ``records`` may be passed to reuse an already-built :func:`terrain_records`."""
    recs = terrain_records(cell_meshes, region_cells) if records is None else records
    n = len(recs)
    zero = [r for r in recs if uv_area(r["uv"]) < ZERO_UV_AREA_EPS]
    bitid = [r for r in recs if uv_pairwise_maxdist(r["uv"]) < BIT_IDENTICAL_EPS]
    frac = (len(zero) / n) if n else 0.0
    dirty = (frac > ZERO_UV_FRAC_CEILING + 1e-12) or bool(bitid)
    worst = zero or bitid
    detail = "; ".join(f"{r['block']}@{r['cell']} topo{r['topo']}" for r in worst[:6])
    return _gate("tex-zero-uv", enforce=enforce, allow=allow, dirty=dirty, detail=detail,
                 checked=n, n_zero_uv_area=len(zero), zero_uv_area_frac=round(frac, 6),
                 n_bit_identical=len(bitid), ceiling=ZERO_UV_FRAC_CEILING)


# ====================================================================================================
#  GATE 2 -- ONE-WINDOW COHERENCE, FAMILY-AWARE (uvf_gates4.family_window_coherence_check)
# ====================================================================================================
def one_window_gate(cell_meshes, region_cells, *, quad_ori=None, enforce: bool = False,
                    allow: bool = False, records=None) -> dict:
    """THE ONE-WINDOW-PER-TRI LAW.  A synthesized ground tri's three UVs must all come from ONE
    ``(cell, quad, ori)`` window, resolved through its OWN family's
    :func:`~ff9mapkit.world.grassland.ground_uv` space -- the tri's CENTROID cell first, then each
    vertex's own cell as a fallback (``uvf_gates4.family_window_coherence_check``'s candidate order).

    ``quad_ori`` = ``{(i,j): (quad, ori)}``, the very per-cell field the caller MINTED with
    (:func:`~ff9mapkit.world.grassland.assign_mains`'s two dicts zipped, or a decoded field).
    **Without it this gate does not judge**: it returns ``skipped=True`` and passes.  See the module
    docstring's calibration -- a blind lattice search reproduces only 3.2%-18.5% of REAL stock
    ground, because lawful stock ground slides free fractional windows, so blind judging would refuse
    every verbatim carry.  Only tris whose centroid cell is IN the supplied field are judged; the rest
    are reported as ``out_of_field`` and never gated."""
    recs = terrain_records(cell_meshes, region_cells) if records is None else records
    mains = mains_records(recs)
    if quad_ori is None:
        return _gate("tex-one-window", enforce=enforce, allow=allow, dirty=False,
                     detail="no (quad,ori) field supplied -- see texgates docstring calibration",
                     skipped=True, checked=0, mains_tris=len(mains), n_multi_window=0,
                     multi_window_frac=None, ceiling=ONE_WINDOW_FRAC_CEILING)
    field = {tuple(k): v for k, v in quad_ori.items()}
    judged = 0
    bad = []
    out_of_field = 0
    for r in mains:
        if r["cell"] not in field:
            out_of_field += 1
            continue
        judged += 1
        fam, uv3, wpts = r["fam"], r["uv"], r["world_pts"]
        cands = [r["cell"]] + [(math.floor(p[0] / CELL), math.floor(p[2] / CELL)) for p in wpts]
        ok = False
        for cell in cands:
            qo = field.get(cell)
            if qo is None:
                continue
            quad, ori = qo
            pred = [GL.ground_uv(p[0], p[2], cell, quad, ori, fam) for p in wpts]
            if all(abs(pred[k][0] - uv3[k][0]) < ONE_WINDOW_UV_TOL
                   and abs(pred[k][1] - uv3[k][1]) < ONE_WINDOW_UV_TOL for k in range(3)):
                ok = True
                break
        if not ok:
            bad.append(r)
    frac = (len(bad) / judged) if judged else 0.0
    dirty = bool(judged) and frac > ONE_WINDOW_FRAC_CEILING + 1e-12
    detail = "; ".join(f"{r['block']}@{r['cell']} {r['fam']}" for r in bad[:6])
    return _gate("tex-one-window", enforce=enforce, allow=allow, dirty=dirty, detail=detail,
                 skipped=False, checked=judged, mains_tris=len(mains), out_of_field=out_of_field,
                 n_multi_window=len(bad), multi_window_frac=round(frac, 6),
                 ceiling=ONE_WINDOW_FRAC_CEILING)


# ====================================================================================================
#  GATE 3 -- FAMILY MAINS-RECT MEMBERSHIP (uvf_gates4.family_rect_membership_check)
# ====================================================================================================
def family_rect_gate(cell_meshes, region_cells, *, enforce: bool = False, allow: bool = False,
                     records=None) -> dict:
    """Every mains-wearing ground tri's three UVs must sit inside ITS OWN family's catalogued mains
    rect (:func:`~ff9mapkit.world.grassland.ground_main_region`, +/- :data:`REGION_EPS`), and none may
    have zero UV area.  A corner outside the family region samples a transparent atlas gutter -- white
    in game.  Body: ``uvf_gates4.family_rect_membership_check``.  Measured 1.000 clean on ten stock
    blocks (2017/2017 tris), so it never false-positives on a verbatim carry."""
    recs = terrain_records(cell_meshes, region_cells) if records is None else records
    mains = mains_records(recs)
    out_of_region, zero_area = {}, {}
    offenders = []
    checked = {}
    for r in mains:
        fam = r["fam"]
        checked[fam] = checked.get(fam, 0) + 1
        lo_u, lo_v, hi_u, hi_v = GL.ground_main_region(fam)
        n_out = sum(1 for (u, v) in r["uv"]
                    if not (lo_u - REGION_EPS <= u <= hi_u + REGION_EPS
                            and lo_v - REGION_EPS <= v <= hi_v + REGION_EPS))
        if n_out:
            out_of_region[fam] = out_of_region.get(fam, 0) + n_out
            offenders.append((r, "out-of-region"))
        if uv_area(r["uv"]) < ZERO_UV_AREA_EPS:
            zero_area[fam] = zero_area.get(fam, 0) + 1
            offenders.append((r, "zero-area"))
    dirty = bool(out_of_region) or bool(zero_area)
    detail = "; ".join(f"{r['block']}@{r['cell']} {r['fam']} {why}" for (r, why) in offenders[:6])
    return _gate("tex-family-rect", enforce=enforce, allow=allow, dirty=dirty, detail=detail,
                 checked_by_family=checked, out_of_region_by_family=out_of_region,
                 zero_area_by_family=zero_area, region_eps=REGION_EPS,
                 escaped_every_mains_rect_ADVISORY=len(escaped_records(recs)))


# ====================================================================================================
#  GATE 4 -- THE 3-PREDICATE SEA GATE (uvf_gates.gate2_sea_plan_disjoint)
# ====================================================================================================
def sea_plan_gate(cell_meshes, region_cells, *, enforce: bool = False, allow: bool = False,
                  records=None) -> dict:
    """The 3-predicate sea gate, ``uvf_gates.gate2_sea_plan_disjoint`` over an in-memory BlockMesh set.

    * **A -- Y-ORDER.** No land Terrain tri may be fully SUBMERGED (all three vertices at or below the
      y=0 sea plane).  The literal per-vertex reading is a CALIBRATION TRAP -- real shoreline vertices
      lawfully taper to exactly 0.0 on every stock coastal stratum -- so the per-vertex count is a
      DIAGNOSTIC only and the gating predicate is the calibrated per-tri one (stock: 0 everywhere).
    * **B -- UNIFORMITY.** Adjacent reported blocks' Sea4 plan areas may differ by at most
      :data:`SEA_UNIFORMITY_CEILING` (4x).  This is what refuses the degenerate one-blob Sea4 stub:
      a full plane next to a stub reads as an infinite ratio.
    * **C -- REAL-SEA DISJOINT.** The 4u cells covered by REAL water parts (:data:`SEA_REAL_PARTS` --
      Sea4, the deep underlay, is excluded because it lawfully lies UNDER land, and <=
      :data:`PLACEHOLDER_MAX_TRIS`-tri hidden convention placeholders are excluded because they are
      not water) must overlap land cells by at most :data:`SEA_OVERLAP_CEILING` (stock grass_coast's
      own headline)."""
    recs = terrain_records(cell_meshes, region_cells) if records is None else records
    region = {tuple(c) for c in region_cells}

    # (A) Y-ORDER -- calibrated per-tri predicate; per-vertex reading is diagnostic only.
    n_verts = n_tris = per_vertex = submerged = 0
    y_min = None
    for r in recs:
        n_tris += 1
        ys = [p[1] for p in r["world_pts"]]
        for y in ys:
            n_verts += 1
            y_min = y if y_min is None else min(y_min, y)
            if not (y > 0.0):
                per_vertex += 1
        if all(y <= 0.0 for y in ys):
            submerged += 1
    passA = submerged == 0

    # (B) UNIFORMITY -- adjacent reported blocks' Sea4 plan area.
    areas = {}
    for (blk, _pn, bm) in _part_tris(cell_meshes, region, (SEA_UNDERLAY_PART,)):
        ox, oz = block_world_origin(*blk)
        a = 0.0
        for tri in bm.tris:
            a += plan_area_xz([(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri])
        areas[blk] = areas.get(blk, 0.0) + a
    pairs = 0
    max_ratio = 0.0
    ratio_viol = []
    for blk in sorted(areas):
        for (dx, dy) in ((1, 0), (0, 1)):
            nb = (blk[0] + dx, blk[1] + dy)
            if nb not in region or nb not in areas:
                continue
            pairs += 1
            lo, hi = min(areas[blk], areas[nb]), max(areas[blk], areas[nb])
            ratio = (1.0 if hi < 1e-9 else float("inf")) if lo < 1e-9 else hi / lo
            if ratio != float("inf"):
                max_ratio = max(max_ratio, ratio)
            if ratio > SEA_UNIFORMITY_CEILING + 1e-9:
                ratio_viol.append((list(blk), list(nb), round(areas[blk], 3), round(areas[nb], 3)))
    passB = not ratio_viol

    # (C) REAL-SEA DISJOINT.
    land_cells = {r["cell"] for r in recs}
    sea_cells = set()
    n_placeholder = n_real = 0
    for (blk, _pn, bm) in _part_tris(cell_meshes, region, SEA_REAL_PARTS):
        if len(bm.tris) <= PLACEHOLDER_MAX_TRIS:
            n_placeholder += 1
            continue
        n_real += 1
        ox, oz = block_world_origin(*blk)
        for tri in bm.tris:
            w = [(bm.verts[j][0] + ox, bm.verts[j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0
            cz = sum(p[1] for p in w) / 3.0
            sea_cells.add((math.floor(cx / CELL), math.floor(cz / CELL)))
    overlap = land_cells & sea_cells
    overlap_frac = (len(overlap) / len(land_cells)) if land_cells else 0.0
    passC = overlap_frac <= SEA_OVERLAP_CEILING + 1e-9

    dirty = not (passA and passB and passC)
    bits = []
    if not passA:
        bits.append(f"{submerged} fully-submerged land tri(s)")
    if not passB:
        bits.append(f"Sea4 uniformity {ratio_viol[:3]}")
    if not passC:
        bits.append(f"sea/land plan overlap {round(overlap_frac, 4)} > {SEA_OVERLAP_CEILING}")
    return _gate("sea-plan", enforce=enforce, allow=allow, dirty=dirty,
                 detail="; ".join(bits),
                 A_submerged_tris=submerged, A_per_vertex_at_or_below_0_DIAGNOSTIC=per_vertex,
                 A_tris_checked=n_tris, A_verts_checked=n_verts,
                 A_min_y=(None if y_min is None else round(y_min, 4)), A_ok=passA,
                 B_pairs=pairs, B_max_ratio=("inf" if ratio_viol and max_ratio == 0.0
                                             else round(max_ratio, 3)),
                 B_violations=len(ratio_viol), B_ceiling=SEA_UNIFORMITY_CEILING, B_ok=passB,
                 C_land_cells=len(land_cells), C_real_sea_cells=len(sea_cells),
                 C_overlap_cells=len(overlap), C_overlap_frac=round(overlap_frac, 6),
                 C_placeholders_excluded=n_placeholder, C_real_sea_parts=n_real,
                 C_ceiling=SEA_OVERLAP_CEILING, C_ok=passC)


# ====================================================================================================
#  the battery
# ====================================================================================================
def texture_sea_gates(cell_meshes, region_cells, *, quad_ori=None, enforce: bool = False,
                      allow: bool = False, sea: bool = True) -> list:
    """All four gates over one BlockMesh set, sharing ONE :func:`terrain_records` pass.  Returns a
    list of gate dicts in the caller's existing ``gates`` shape.  ``sea=False`` drops
    :func:`sea_plan_gate` (a caller with no water parts in hand -- its predicates B/C would be
    vacuous rather than wrong, but reporting a vacuous gate is noise)."""
    recs = terrain_records(cell_meshes, region_cells)
    # AUDIT REC 9's "promote the calibrated two to enforce-by-default" was tried here on
    # 2026-08-04 and REFUTED by this kit's own corpus (recorded so it is not re-proposed):
    # family-rect fails REAL desert-family region carries ("desert out-of-region" -- the
    # 1.000/2017-tris calibration covered grass mains only), and zero-uv-area, clean on the
    # whole real carry corpus, still flips 20+ hermetic fixtures whose synthetic meshes carry
    # dummy UVs. An enforce-default belongs at a VERBATIM-carry call site if anywhere, never
    # in this composite. All four gates keep the blanket `enforce`; `allow` waives.
    out = [zero_uv_area_gate(cell_meshes, region_cells, enforce=enforce, allow=allow, records=recs),
           one_window_gate(cell_meshes, region_cells, quad_ori=quad_ori, enforce=enforce,
                           allow=allow, records=recs),
           family_rect_gate(cell_meshes, region_cells, enforce=enforce, allow=allow, records=recs)]
    if sea:
        out.append(sea_plan_gate(cell_meshes, region_cells, enforce=enforce, allow=allow, records=recs))
    return out
