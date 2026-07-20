"""THE NW-NOTCH HATCH FIX -- a study-local, SUBCLASSED extension of
``ff9mapkit.world.transplant.GroundRetile``.

THE DIAGNOSIS (full record: artifact_diagnose.py -> artifact_bucket_render.py [a false lead,
retracted below] -> hatch_tight_zoom.py -> the final isolation below). The visible hatch is NOT
the donor's B-strip/"worn path" band (topo-in-GRASS_TOPOS tris whose uv sits in
``grassland.FAM_REGION["B"]`` -- 54 tris over 28 cells at (8,17)). That band goes through
GroundRetile's existing PATH-STRIP RECOVER (``assign_mains``) fallback and renders CLEANLY --
proven by rendering the recover bucket in total isolation (``out/recovered_ALL_solo.png``, zero
artifacts) AND by rendering the exact same window the FULL scene sees (the "cross" shaped
recover footprint is smooth desert sand throughout; only a THIN separate sliver is broken). A
first hypothesis (the STRIPS-band grass|desert seam law is the fix) was tested and REJECTED: that
translation still samples a green/grass-look texel column (a real strip is two-toned by design --
it is a coastline SEAM decal, not a general ground fill), so applying it here just repaints the
donor's real "worn path" as visible green blotches -- a worse defect, reverted.

THE REAL ROOT CAUSE, isolated to 3 donor terrain triangles (of 23 total SAND-band tris the (8,17)
carry touches, one of them being the exact tri under the reported hatch pixels): the desert SAND
band (``coastmorph.SAND_BANDS["desert"]``) has only ONE discrete v-row per tier (land/seam/
cap_land/cap_seam), while the grass SOURCE band legitimately wears SEVERAL sub-variant v-pins per
tier (``coastmorph.SAND_V_CAP_LAND`` alone lists 6). A triangle whose 3 vertices straddle two
DIFFERENT grass cap_land sub-variants is a perfectly normal, non-degenerate donor triangle -- but
once each vertex snaps independently to ITS nearest grass-side anchor and then that anchor's
desert-side target, two (or all three) vertices can collapse onto the IDENTICAL desert (u,v)
point. The triangle stays real (nonzero) in world space but its final UV area goes to ~0 -- the
renderer then stretches one texel-row of the atlas across the tri's whole world-space extent,
and whatever fine grain that atlas row carries reads as bold, regularly-spaced diagonal bands
(``out/hatch_tight_zoom.png``). This is a genuine granularity mismatch the measured law cannot
resolve for these specific tris -- NOT a mapping to fix, but an unmeasurable-for-this-triangle
case (the same class of situation ``GroundRetile``'s own PATH-STRIP RECOVER budget exists for).

THE FIX (in-language, zero invented texture, zero edits to shipped ff9mapkit/ code): detect a
sand-mapped triangle whose final (u,v) triple is degenerate (two or more vertices coincide) BEFORE
emitting it, and instead of emitting the broken sand uv, route it through the SAME PATH-STRIP
RECOVER treatment GroundRetile already uses for donor tris with no measured class (real desert
mains texture, position-evaluated, ``grassland.assign_mains``) -- the exact same "no lawful class
-> plain desert ground" policy the shipped class's own docstring already documents, just also
applied to a mapped-but-degenerate SAND tri rather than only an entirely-unclassified one. Nothing
invented; the tri keeps real geometry, gets a real, elsewhere-proven-clean desert texture.

Composition only: :class:`DegenerateSandGuardRetile` subclasses the shipped ``GroundRetile`` and
overrides only the ``apply()`` sand branch (calling ``super().apply()`` unchanged for everything
else, including the B-strip/PATH-STRIP RECOVER path, which needed no fix). No shipped file edited.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world.transplant import GroundRetile, decode_id   # noqa: E402
from ff9mapkit.world import grassland as G                        # noqa: E402


class DegenerateSandGuardRetile(GroundRetile):
    """``GroundRetile`` + a guard on the SAND branch: a tri whose sand-remapped (u,v) triple
    degenerates (two+ vertices coincide -- a real granularity mismatch between the grass source's
    multi-variant tier pins and desert's single-row pins, see module docstring) is diverted to the
    SAME PATH-STRIP RECOVER treatment already used for unmeasured-class donor tris, instead of
    being emitted with a near-zero-area UV (the hatched-stripe artifact)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.n["sand_degenerate_recovered"] = 0
        self._degenerate_cache: dict = {}

    def apply(self, part, poly):
        if part == "terrain" and self.sand_src is not None and self.sand_anchors \
                and self.sand_du is not None:
            topo = decode_id(int(round(poly[0][3][0])))["topograph"]
            if topo == self.sand_src["topo"]:
                pts = [(round(uvv[0] + self.sand_du, 6), round(self._sand_v(uvv[1]), 6))
                       for (_, _, uvv, _) in poly]
                if len(set(pts)) < len(pts):
                    # degenerate -- recover via the SAME assign_mains policy PATH-STRIP RECOVER
                    # uses, keyed per-4u-cell so neighbouring degenerate tris share one assignment.
                    cx = sum(v[0][0] for v in poly) / len(poly)
                    cz = sum(v[0][2] for v in poly) / len(poly)
                    cell = (math.floor(cx / 4.0), math.floor(cz / 4.0))
                    qo = self.recover_cells.get(cell) or self._degenerate_cache.get(cell)
                    if qo is None:
                        cq, co = G.assign_mains({cell}, seed=0xF93)
                        qo = (cq[cell], co[cell])
                        self._degenerate_cache[cell] = qo
                    quad, ori = qo
                    self.n["sand_degenerate_recovered"] += 1
                    return [(p, nr, tuple(G.ground_uv(p[0], p[2], cell, quad, ori, self.dst)),
                             self._retag(tan, self.dst_topo))
                            for (p, nr, uvv, tan) in poly]
        return super().apply(part, poly)

    def gate(self) -> dict:
        g = super().gate()
        g["sand_degenerate_recovered"] = self.n["sand_degenerate_recovered"]
        return g


def build(donor, dst, *, size=(1, 1), src=None, strips="auto", extra: float = 8.0, disc: int = 1,
         lod: str = "0_1", game=None) -> DegenerateSandGuardRetile:
    """Drop-in replacement for ``GroundRetile.for_donor`` -- same prescan (sand anchors, wall-
    context law, recover budget for genuinely unmeasured classes), returned as the
    degenerate-sand-guarded subclass instead of the plain class. Re-walks the SAME donor+strip
    gather ``for_donor`` already did, purely to count how many of its ``sand`` tris are the
    degenerate case (see module docstring), so the retile's ``expected`` census stays exact
    (``sand`` count reduced by exactly the diverted tris; ``sand_degenerate_recovered`` added)."""
    from ff9mapkit.world.transplant import world_tris, clip_poly
    from ff9mapkit.world.terrain import GRID_X, GRID_Y

    base = GroundRetile.for_donor(donor, dst, size=size, src=src, strips=strips, extra=extra,
                                  disc=disc, lod=lod, game=game)

    (dbx, dby) = donor
    (nx, ny) = (int(size[0]), int(size[1]))
    terrain = []
    for j in range(ny):
        for i in range(nx):
            terrain += [list(t) for t in world_tris(dbx + i, dby + j, "terrain", disc=disc,
                                                     lod=lod, game=game)]
    all_specs = {
        "E": [((dbx + nx, dby + j), 0, 64.0 * (dbx + nx) + extra, True) for j in range(ny)],
        "W": [((dbx - 1, dby + j), 0, 64.0 * dbx - extra, False) for j in range(ny)],
        "N": [((dbx + i, dby - 1), 2, -64.0 * dby + extra, True) for i in range(nx)],
        "S": [((dbx + i, dby + ny), 2, -64.0 * (dby + ny) - extra, False) for i in range(nx)]}
    if strips in ("auto", "all"):
        gathered = set(all_specs)
    elif strips in ("none", None):
        gathered = set()
    else:
        gathered = {str(d).upper() for d in strips}
    strip_specs = [spec for d in sorted(gathered) for spec in all_specs[d]]
    for ((nx2, ny2), axis, plane, below) in strip_specs:
        if not (0 <= nx2 < GRID_X and 0 <= ny2 < GRID_Y):
            continue
        for tri in world_tris(nx2, ny2, "terrain", disc=disc, lod=lod, game=game):
            cp = clip_poly(list(tri), axis, plane, below)
            if len(cp) >= 3:
                terrain.append(cp)

    n_degenerate = 0
    if base.sand_src is not None and base.sand_anchors and base.sand_du is not None:
        for tri in terrain:
            if decode_id(int(round(tri[0][3][0])))["topograph"] != base.sand_src["topo"]:
                continue
            pts = [(round(uvv[0] + base.sand_du, 6), round(base._sand_v(uvv[1]), 6))
                   for (_, _, uvv, _) in tri]
            if len(set(pts)) < len(pts):
                n_degenerate += 1

    expected = dict(base.expected)
    expected["sand"] = expected.get("sand", 0) - n_degenerate
    expected["sand_degenerate_recovered"] = n_degenerate
    return DegenerateSandGuardRetile(
        dst=base.dst, src=base.src, sand_anchors=base.sand_anchors,
        recover_cells=dict(base.recover_cells), recover_budget=base.recover_budget,
        expected=expected)
