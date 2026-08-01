# APRON CARRY — prediction registration (BEFORE building)

2026-07-31. The base-tile grammar study decoded THE BAND-CONTINUATION LAW
(BASE-TILE-GRAMMAR.md): the transitional band is the column's own uv continuation —
100.0% u- and v-continuous with the course above, seam v = 10.16 both sides, zero
freedom. The owner's go-word followed. Written before the first builder edit.

## Why the texture-only lane is CLOSED (derived from the law, not retried)

The report after the study offered "copy seam uv verbatim" as the texture-only
re-mint, with a caveat. Working the caveat through the law's numbers closes the lane
outright: the bury seat's level cut sliced the donor mid-course, so each visible
bottom fragment's top seam carries the donor's own v — mid-face row boundaries,
column by column. The band may lawfully appear ONLY where the course above ends at
v ≈ 10.16 (there is not one discontinuous seam into row 10 in the 1,090-vert
census), and the fragments' seam v is donor-fixed elsewhere for most columns. Every
uv assignment on the cut fragments is therefore either lawful-but-bandless (the
mid-face continuation they already wear — playtest 1's missing transition) or
band-wearing-but-off-law (a fresh seam class stock never makes — playtest 2's
mismatched faces, now explained). No third option exists. The fix must be GEOMETRY:
put the donor's own band back above the ground plane.

## The claim under test

**Carrying BOTH sides of stock's own transition reads as FF9.** The mesa round
proved the carried wall body and top; this round completes the feature downward: the
mesa re-seated at its donor stature, its own near-solid row-10 foot band intact, and
its own GROUND APRON (the donor's sloping grass that rises to meet the weld line —
stock's answer to "both sides have a responsibility") carried with it. The
grass↔cliff transition becomes stock bytes end to end; the only minted junction
moves OUTWARD to the apron's edge, where it is grass-to-grass at near-bench level —
the most benign junction class this arc has.

- **CARRIED — everything from the mesa round UNCHANGED in plan** (same lattice
  translation, yaw 0): the 325-tri wall ring + ring-1 + enclosed plateau, all uvs /
  normals / tangents. **Seat dy changes only**: the donor ground-weld line sits
  ABOVE bench LOWLAND (3.2), restoring the donor's full stature (crest ~26.5 bench,
  ~3.7u taller than the buried build; declared here, not a defect class).
- **CARRIED — new this round:** the donor's foot band course (near-solid row 10, the
  census's own longest-chain exemplar) and the donor GROUND APRON — donor grass tris
  flooded outward from the weld line until they flatten to lowland, verbatim bytes.
  The donor's local lowland is ~3.0 vs the bench's 3.2 — near-level at the apron's
  outer rim by construction.
- **MINTED — ONLY the outer grass-to-grass weld:** the bench grass partition +
  shared-vertex rim weld machinery (in-game proven for three rounds) applied to the
  apron's outer boundary instead of a level-cut foot loop. The fringe machinery is
  DELETED — the study falsified stationing; the donor band replaces it.

## Declared mechanism freedoms (measured at build time, declared pre-deploy)

1. **Apron extent** — how many rings out the flood goes before the donor ground is
   flat-enough (target: outer-rim y within ~0.5u of bench 3.2, closing as a loop).
   If the donor apron does NOT close at near-bench level, the fallback within the
   round is a minted displacement skirt (bench grass reshaped to the donor's own
   measured approach slope) welded to the donor weld line directly.
2. **The west border** — the (14,14) continuation (4 wall tris) plus ITS apron must
   merge across the block border (kk-stitch). If the merged boundary cannot close,
   the west face resolution (trim + local mint) is declared in build notes.
3. **Outer-rim simplification** — whether the chord simplifier applies to the
   grass-to-grass rim or the verbatim donor polyline is kept.

## Gates

- Pristine-bench guard (restore `backups/terrace-strip-prewall.20260731-182852`
  first — the fringed mesa is live); watertight; winding per carried normals;
  massing / placement census / reach; culled game-eye renders.
- **CARRY PURITY, extended** — no wall uv modified ANYWHERE (byte-hash before/after)
  and no apron uv modified; the only minted vertex class is the outer grass weld.
- **THE BAND GATE (new, from the study)** — the foot-adjacent wall course's row-10
  share must read near the donor's own (≥ 0.8), vs ~0 in the buried build: proof the
  seat put the transition back above ground.

## REGISTERED PREDICTION

**PASS** — the base reads as FF9 and the top's standing pass holds. Basis: every
surface in the transition is stock's own, in stock's own arrangement; the one minted
seam is grass-to-grass at matched height.

## Falsification semantics — declared in advance

- **PASS** → the wall arc CLOSES at feature granularity with the full recipe:
  whole-feature carry INCLUDING the ground apron; `world-terrace` productization =
  a mesa-library carry.
- **FAIL naming the base/transition** → the apron-carry class itself is indicted on
  this bench → a context study (scale, surround); no further base rounds.
- **FAIL naming the outer grass weld** → one lever: soften/widen the outer blend;
  a single iteration, does not reopen the base.
- **Top/height named** → a seat/context call for the owner (the donor stature was
  the mesa registration's own preferred geometry), not a law failure.
- **PLUMBING failure** → fix or stop, no verdict (standard).

One round. Scored on the owner's verdict, whichever way it lands.

## BUILD NOTES (pre-deploy, 2026-07-31) — the declared freedoms, resolved by measurement

Builder `apron_carry.py` (the mesa_carry pipeline with the level cut and fringe
REMOVED); probe `probe_mesa_apron.py`; three offline iterations, gates GREEN.

- **Freedom 1 (apron extent), resolved:** collar = donor grass-class tris within
  **6u** of the weld, adjacency-flooded over the 5-block donor neighborhood, **and
  clipped to the bench's own grass coverage** (every vert over bench grass, ≥2u from
  the coast band). The donor's meadow continues past where the bench island has
  grass — on the west/southwest the bench coast comes in to ~40-46u and a 10u collar
  overlapped it (run-1's 262-edge residue). Where the bench runs out, the collar
  ends and bench grass welds directly to the donor weld line (the registered
  fallback, applied locally; 17 tris clipped). 168 apron tris carried.
- **Freedom 2 (west border), resolved:** the merged 5-block soup lets the crest
  component cross the border by shared verts — the 4-tri (14,14) continuation joins
  the carry with no special-casing, and its apron (24 tris in (14,14)) floods
  normally. No trim needed; 0 whisker edges.
- **Freedom 3 (rim simplification), resolved:** verbatim polyline, with plan-
  COLLINEAR runs merged into chords (zero-deviation merge — the on_chord machinery
  reasons per chord; unmerged collinear edges left bench fragments unsplit at shared
  rim verts). y interpolates per sub-edge (plan-straight, height-kinked chords).
- **The blend is conforming by construction:** the field is sampled ONLY at original
  bench verts (275 lifted, max 4.01u over the 12u falloff, coast-shared verts
  banned); every derived point — fragment corner, crossing, conformance split,
  sweep split — interpolates its parent's lifted verts. (Run 1 evaluated the field
  per point; every kept/cut boundary cracked.)
- **Gate dispositions, declared:** massing and reach are REPORT-ONLY this round —
  the massing gate's subject (a minted ground silhouette) does not exist (the
  visible rock-to-ground line is the donor's own weld line, med turn 19.3°, zero
  right angles; the grass-to-grass rim is a height-blended boundary with no
  silhouette), and the reach gate's fit is enforced structurally by the grass clip.
  A declared once-edge class exists for stock's own carried cracks (0 hits this
  build). Watertight residue: **19 once-edges of 5,168 (0.37%), none > 5u** (bound
  24; stock's own open rate 2.8-6.8%).
- **Numbers for the record:** seat dy −0.14 (donor stature; the bury's −4.35
  undone); crest ~26.2 bench, top 28.1 (~23-25u above ground — the tallest wall we
  have shipped, declared in the registration); band(10+11) share at the weld
  **100%**; weld line y 3.0..7.4; 8 forest-abutted weld edges (forest excluded as a
  feature class; the boundary closed with zero hole loops after the grass clip).

## PLAYTEST 1 (2026-07-31): THE CONNECTION PASSES; the apron-surface lever fires

Owner (from the west coast, on foot at the mesa's base): *"weird brown tiles and
some seams. the connection is nice though."*

- **The round's claim is confirmed** — the grass↔cliff transition ("the
  connection") reads right at donor stature with the donor's own band. Neither
  named defect is on the wall or the weld: both are on the APRON'S SURFACE.
- **Root cause, probed (`probe_apron_tiles.py`):** the apron carried the donor's
  HOME tiles — 20 tris of a different atlas family (col 5, rows 8-11: the donor
  meadow's dirt/talus band = the "weird brown tiles"), and its grass cells carry
  the donor's own tile phases, which cannot pattern-match the bench's positional
  L3 field at the rim (= the seams).
- **The registered outer-weld lever fires as the round's ONE change:** retile the
  apron's GROUND uv to the DESTINATION's L3 field (`G.ground_uv` over the bench's
  own seeded cell decode — the exact mapping the surrounding bench grass wears, so
  the pattern is continuous across the rim by construction). Lawful framing:
  grass tiling is POSITIONAL law in this engine (L3 assigns per destination cell);
  the apron's carried value is its GEOMETRY and the weld line, not its home tile
  phases. Wall uv untouched — carry purity of the band stands. Geometry, normals,
  and topograph tags stay donor.

## PLAYTEST 2 (2026-07-31): brown fixed; the surface lever's DECLARED ITERATION

Owner (three screenshots — west base (384,−511), SE base (444,−519), north base
(419,−490)): *"seam + stretched grass"* (west) — *"cliff base colliding with
raised-grass cliff, covering the base"* (SE) — *"seam + stretched grass on the
other side of that hill"* (north). Brown not re-named — the retile held. Every
defect is on the outer ground junction: the registered "soften/widen the outer
blend" lever, one iteration, applied as a bundle (one surface, one lever):

- **Stretched grass, root-caused by measurement** (`probe_apron_tiles.py`, the
  slope-uv addendum): stock grass uv tracks SURFACE distance (steep tris hold the
  flat per-surface rate 0.981 vs 0.982 while the per-plan rate inflates). The L3
  retile was plan-projected — up to ~20-40% stretch on the steep collar. The apron
  RESTORES its donor uv (surface-lawful, full carry purity back); only the donor
  meadow's DIRT band (col 5 rows 8-11 — playtest-1's brown) re-rows into the
  donor's own grass family, phases preserved (keep-u/swap-the-row on ground; the
  family self-tiles, so row parity folds 8-11 into 24-25 with every seam exact).
- **The seams, identified by elimination + the residue dump:** they survived BOTH
  uv schemes → not texture. Screenshot 1's west seam = the donor blocks' own
  cross-border hairline at posed x=384 (0.03u y-mismatch, stock's own, under the
  strict weld net); screenshot 3's north seam = a TRIANGULAR HOLE at (420,−490)
  (a donor step face whose class the apron flood excluded). Three targeted
  passes: a BORDER STITCH (64-grid border lines, 0.12u net), a HOLE CAPPER
  (once-edge 3-cycles = missing facets), and a RESIDUE STITCH (parallel
  once-edge chains, repair restricted to the residue so it cannot crawl). Plus
  one smooth ground-normal field over the whole touched surface (apron +
  fragments + lifted bench, area-weighted from final geometry) — the lighting
  half of the seam class.
- **The raised-grass cliff:** BLEND_R 12 → 24 (the minted ramp drops from
  ~25-35° to ≤ ~14°, stock-walkable grass) and the collar back at the registered
  APRON_D=10 with the bench-grass clip (more donor ground owns the approach).
  Step patches: donor pocket faces whose verts/edges are already carried join
  automatically.
- **Watertight: 5 residual once-edges of 7,404 (0.07%)** — down from the
  reviewed build's 19; the sweep's two-arm tolerance is measured-optimal (both
  loosening alternatives made it crawl: 128 and 40 residuals).

Per the registration this was the outer-weld lever's single iteration: if the
surface still fails, the lane rests pending a ground-approach study.
