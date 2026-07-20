"""THE NW-NOTCH HATCH FIX -- **SUPERSEDED 2026-07-20: FOLDED INTO THE SHIPPED CLASS.**

The degenerate-sand guard this module minted study-locally now ships INSIDE
``ff9mapkit.world.transplant.GroundRetile`` itself (the DEGENERATE-SAND GUARD branch of
``apply()``, counted + frozen by ``for_donor``'s prescan as ``sand_degenerate_recovered``), so the
bare CLI ``world-transplant --ground`` path carries the fix. This module remains as the diagnosis
record + a compatibility shim: :func:`build` delegates straight to ``GroundRetile.for_donor``
(byte-identical output to the deployed (11,18)+2x2 files -- re-verified at fold time), and
``DegenerateSandGuardRetile`` aliases the shipped class. The original diagnosis follows.

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

THE FIX (in-language, zero invented texture): detect a sand-mapped triangle whose final (u,v)
triple is degenerate (two or more vertices coincide) BEFORE emitting it, and instead of emitting
the broken sand uv, route it through the SAME PATH-STRIP RECOVER treatment GroundRetile already
uses for donor tris with no measured class (real desert mains texture, position-evaluated,
``grassland.assign_mains``) -- the exact same "no lawful class -> plain desert ground" policy the
shipped class's own docstring already documents, just also applied to a mapped-but-degenerate
SAND tri rather than only an entirely-unclassified one. Nothing invented; the tri keeps real
geometry, gets a real, elsewhere-proven-clean desert texture. Originally built here as a
study-local SUBCLASS (this session's hard rule: no shipped edits); folded into the shipped
``GroundRetile.apply()`` 2026-07-20 with the (8,17) 3-tri case as a shipped regression test.
The folded condition is REFINED over this module's original ("two+ mapped verts coincide"):
it fires only when the remap STRICTLY REDUCES the distinct-uv count -- the (10,17) island-B
donor's W-strip beach fragments are already degenerate at the SOURCE (zero-area clip
residues), render as nothing, and must stay verbatim sand or that deployed carry's bytes
would drift. The refinement also corrects this module's own census: of the 3 tris it
counted at (8,17), only ONE (donor (9,17) -- the exact tri under the reported hatch
pixels) is a real mapping-collapsed triangle; the other 2 are zero-area W-strip clip
residues at the x=504 clip plane, source-degenerate and census-only (never in written
output). A post-fold re-run is byte-identical to the deployed (11,18) files under either
condition -- the deployed bytes cannot tell them apart; the refined count is the honest one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world.transplant import GroundRetile   # noqa: E402

#: the guard ships in the base class now -- the subclass is history (see git log)
DegenerateSandGuardRetile = GroundRetile


def build(donor, dst, *, size=(1, 1), src=None, strips="auto", extra: float = 8.0, disc: int = 1,
          lod: str = "0_1", game=None) -> GroundRetile:
    """SUPERSEDED delegate -- ``GroundRetile.for_donor`` with the guard folded in (its prescan
    freezes ``sand_degenerate_recovered`` exactly as this module's donor re-walk used to)."""
    return GroundRetile.for_donor(donor, dst, size=size, src=src, strips=strips, extra=extra,
                                  disc=disc, lod=lod, game=game)
