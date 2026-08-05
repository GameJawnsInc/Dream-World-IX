# THE RING DROP — registered before building, 2026-08-02

## What the playtests established

| island | shallow ring carried | water artifact |
|---|---|---|
| the comma `(9,5)` | none | none |
| **the corner isle `(0,0)`** | **none** | **none — owner-confirmed** |
| **the isthmus `(6,6)`** | **sea3 492 + sea5 152, CROPPED at the rect frame** | **yes** |

The corner isle was deployed as a test of the ring-cut diagnosis and **confirmed it**: a
deep-water island with no ring has no artifact, while the one island carrying a cropped ring
has one. Stock's ring continues 294 tris north past the donor rect frame; a 2x2 rect cannot
contain it, and a bigger rect destroys the carry (THE RING-CUT TRAP).

## The fix, and why it is a CONVERSION rather than a drop-and-fill

Removing the ring leaves an ANNULUS — bounded inside by the island's waterline and outside
by sea4's inner edge. `flat_patch` fills a simple ring, not an annulus, so drop-and-fill
would need new triangulation across a hole and would author every triangle it emits.

But nothing about the ring's GEOMETRY is wrong. Measured: sea3/sea5 are flat at y=0, carry
the same shared normal byte constant as sea4, and wind negative exactly as sea4 does. Only
their SHADE is wrong for a cropped context. So the lawful edit is to **retag them as deep
water in place** — positions, normals and winding verbatim, only uv and IDALL change.

That is the same vocabulary the excise fill already uses (`SEA4_QUADS`, `SEA4_IDALL`) and
the same positional rule (`fu = x/4 % 1`, `fv = -z/4 % 1` inside the chosen quadrant), so
the converted ring and any neighbouring fill agree by construction. Sea4's quadrant choice
is free (measured uniform across world-cell parities), so no tone gate is needed.

**Zero triangles are authored. The tri count cannot change.**

## Predictions

* **R-1** Converted tri count == the dropped sea3+sea5 count exactly (644 for the isthmus);
  terrain is untouched at 578.
* **R-2** Gates stay clean, and the 18 cropped-Wang advisory **disappears** — it fires on
  deep-vs-shallow frame adjacency, and after conversion there is no shallow band to abut.
* **R-3** The census stays at `introduced=0`. Winding is preserved, so no tri flips
  back-facing (the failure that scored 73 introduced misses on a wound-wrong fill).
* **R-4** In game: the hard sea3->sea4 edge in open water is GONE, and the island sits in
  uniform deep ocean like the comma and the corner isle.

**R-4 is the only one a playtest can settle. If the edge survives, the ring was never the
cause and the diagnosis is wrong despite the corner-isle confirmation.**

## Stop rule

Offline-only until the gates are clean and R-1..R-3 are scored. One deploy, one playtest.

---

## FINDINGS — R-1..R-3 CONFIRMED, R-4 awaiting the playtest

**R-1 CONFIRMED.** `dropped={'sea3': 492, 'sea5': 152}` -> `converted=644`,
`conserved=True`. Terrain untouched at 578. The carried line reads `sea3:0 sea5:0
sea4:1686`, and 1042 + 644 = 1686 exactly.

**R-2 CONFIRMED.** `wang-carry incoherent=0` -- the 18 cropped-Wang seams are gone, and the
whole deploy now ships with **zero advisories** where it previously had one. The advisory
fired on deep-vs-shallow frame adjacency; with no shallow band there is nothing to abut.

**R-3 CONFIRMED.** `census miss=0 inherited=0 introduced=0`, `weld-audit pairs=0`.

**R-4 open** -- only the game can settle whether the hard edge in open water is gone.

### The deploy needed checking, and it checked out

A re-shade means the carry writes NO Sea3/Sea5, so the previous deploy's shallow overrides
could have been left on disk and rendered anyway. Verified rather than assumed: the kit
rewrote them as **3-vertex stubs** (its blank-a-part idiom, which suppresses the prefab's
own sheet) and moved the geometry into Sea4, which grew from ~534 to ~1275 verts per cell.
Nothing stale survived.

### Coverage

Four mutations, four caught: positions no longer preserved, the winding guard never firing,
uv abandoning the positional rule, and the plan converting fewer tris than it drops.


---

## THE RING DROP WAS THE WRONG FIX ENTIRELY — playtest 2, 2026-08-04

**R-4 is moot: I solved a problem the owner did not have.**

The ask was that the ring's cut edge be **re-tiled with proper Wang transitions** so the
shallow band terminates lawfully into deep water. I removed the ring instead. Owner:
*"now it's just all deep sea water instead of what I was asking for (the edge to be
auto-Wanged)"*. Deleting a feature is not fixing its edge.

**And the execution was independently bad.** Owner: *"look at the stretched, hard-edged deep
sea tiles near the coast"*. That is the tile-anchored UV I introduced while fixing the
checkerboard: it clamps each vertex into its triangle's centroid tile, which is right for
lattice-aligned tiles and wrong for the coast-cut triangles, whose vertices fall outside
that tile and get flattened onto its edge. **My fix for bug 2 created bug 3.**

### The remedy was named in the advisory I dismissed as noise

The wang-carry warning says, verbatim: *"re-tile the rim (`wang_rim_retile` for sea3/sea5,
the {sea1,sea5} ladder for sea1/sea2)"*. I read that advisory, decided it was noise because
the owner said the LAND edge looked fine, and never checked that it named a remedy. It did.

Two caveats, both worth knowing:
* **`wang_rim_retile` is not a shipped verb.** It exists only as
  `studies/overworld-topography/wang_rim_retile.py`, hardcoded to the `(8,17)` desert-beach
  island. The advisory points at something a user cannot run.
* But the approach is **precedented and correct**, and its design note states the principle
  I violated: the replacement sea5 UVs are *"HARVESTED byte-exact from the donor island's
  OWN real sea5 termination tiles ... NOT synthesized"*, with geometry, normals and topo
  identical — a pure repartition between the Sea3/Sea4/Sea5 files.

### What the right fix looks like

For each of the 18 flagged rim quads on the isthmus: terminate the cropped shallow into the
deep ring with a real sea5 transition tile whose deep-set points outward, harvested from
donor `(6,6)+2x2`'s own termination tiles. Verts, normals and topo unchanged; only the uv
rect and the containing Sea file change. Non-regression is airtight by construction because
the triangle multiset is preserved.

Adapting the script means generalising its hardcoded `ISLAND`/`DONORS` disc-1 case to a
disc-9 target.

### THE STANDING LESSON, now paid for three times in one feature

Every failure here came from AUTHORING texture instead of CARRYING it. The owner named it
before the second playtest — *"i thought we solved the whole Wang-patching transplant
thing"* — and it is solved, for carrying. `--deepen-shallow` should be treated as a dead
end, not a tool: it deletes a feature to avoid re-tiling it, and there is no case where
that is the right trade.


---

## ★ THE RIM RE-TILE PASSED — playtest 3, 2026-08-04

Owner: *"that's a pass, the hard edge became a series of Wang tiles"*.

The cropped shallow ring now terminates into deep water through real transition tiles
instead of stopping at a straight block-frame line. **Measured before the playtest, and the
number that predicted it:** tiles whose uv UNDER-covers the deep they face — the hard-seam
class — went **3 → 0**.

### What worked, stated so it is not re-learned

**Carrying, not authoring.** The replacement uvs were harvested byte-exact from donor
`(6,6)`'s own sea5 termination tiles; all six deep-sets the plan needed were covered
verbatim, so nothing was synthesized. Geometry was a pure repartition — the (verts+topo)
multiset identical per cell, gated — so the edit *could not* move a vertex or flip a face.

Contrast the two failures, both of which authored uv:
* per-triangle quadrant → a checkerboard across the whole sheet;
* tile-anchored uv → stretched, hard-edged tiles on the coast-cut triangles.

### The three things I got wrong, in order

1. **Wrong problem.** The ask was to re-tile the rim; I deleted the ring
   (`--deepen-shallow`). Now removed from the CLI — it deletes a feature to avoid
   re-tiling it, and there is no case where that is the right trade. The function is kept,
   marked as a superseded dead end, because its measurement is still true.
2. **Dismissed the advisory that named the remedy.** The wang-carry warning says
   *"re-tile the rim (wang_rim_retile ...)"*. I read it, decided it was noise because the
   owner said the LAND edge looked fine, and never checked that it named a fix.
3. **Two gate mis-calibrations**, both nearly shipping: a guessed threshold band that
   passed the broken sheet by 0.015, and a lattice check too narrow to see the lattice it
   was written for.

### One real subtlety worth keeping

**A single pass does not converge.** The deep-set derivation reads the shade map, and
converting sea3→sea5 changes that map, so neighbours' deep-sets shift underneath the first
pass. Re-running reaches a fixed point at pass 2 (27 quads, all sea5→sea5, stable through
pass 4). Any future rim retile must iterate.

### Residual, honestly

20 of 82 rim tiles still OVER-cover — a transition facing shallow, a gradient where none is
needed. Owner-accepted as-is. It is a different and much subtler class than the hard seam,
and not worth authoring surface to chase.

### Next, if this is ever productized

`wang_rim_retile` is still not a shipped verb — the advisory points users at a study script.
`isthmus_rim_retile.py` is the second instance of the same pattern, which is usually the
point at which it should become one.
