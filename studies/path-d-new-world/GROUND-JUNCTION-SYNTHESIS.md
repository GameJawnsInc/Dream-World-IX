# THE GROUND-JUNCTION SYNTHESIS — why every round relocates the defect instead of removing it

2026-07-31. Registered BEFORE any instrument runs. The owner's call after the
apron-carry lever's declared iteration: *"now we're back to weird meadowy corner
tiles and we've got more seams, and the hill still isn't fixed (plus it's seaming).
back to studies... see if we can orchestrate/synthesize our knowledge, mixed with
more studies, into truly understanding what's happening here and why we keep getting
problems iteration after iteration."*

This study is not another grammar decode of one feature. It is the **synthesis**
study: it takes the arc's own eight-round record as DATA, measures the stock laws
that record implies we are still missing, and must produce a causal model plus a
decision — not another patch.

## S0 — THE META-QUESTION (the owner's own, made falsifiable)

Eight rounds, and the visible defect has MOVED every time without ever going away:
strip seams → crest rim → sliced/stretched faces → missing base band → mismatched
base faces → brown tiles + rim seams → stretched grass + raised-grass cliff →
meadowy tiles + more seams + the hill. **The defect always sits on whatever we most
recently minted.**

Three competing explanations, with discriminants registered in advance:

- **(a) INDEPENDENT BUGS** — each round had its own unrelated defect; the arc is
  simply converging slowly. *Discriminant:* defect classes would be uncorrelated
  with what changed, and residual counts would fall monotonically. (Round 8's
  watertight residue DID fall 19 → 5 while the owner's complaint count ROSE 3 → 3+;
  early evidence against.)
- **(b) STRUCTURAL — THE TWO-FIELDS CAUSE** — a carried donor sheet and the bench
  sheet are two independently authored positional fields (uv phase, tile family,
  normal convention, height datum). ANY line where they meet is a discontinuity, so
  every mint relocates the seam rather than removing it, and no per-vertex fix can
  win. *Discriminant:* the defect follows the mint (it does, 8/8), AND stock never
  places such a boundary in open ground (S2 tests this).
- **(c) OFF-LANGUAGE CONTEXT** — a ~60u mesa on a ~50u synthetic island with 6-10u
  of ground before the sea is a configuration stock never authors, so every junction
  is compressed into a distance the grammar has no vocabulary for. *Discriminant:*
  the stock census finds no instance of our configuration (S4), and the donor's own
  base needs a ground slope our island cannot host (S5).

(b) and (c) are not exclusive; the study must apportion them.

## The structural fact that provokes S5 (already in hand, unexplained)

The donor mesa's ground-weld line is **NOT level: y 3.0 → 7.4** (4.4u of relief).
Attaching it to a flat bench at LOWLAND 3.2 therefore admits only two moves, and the
arc has now tried BOTH and failed BOTH:
- **BURY** (rounds 4-5): seat it low so the weld line falls below the cut → the
  donor's own transitional band is cut away → "mismatched faces" at the base.
- **LIFT** (rounds 6-8): raise bench ground to meet the weld line → a 4u grass mound
  → "raised-grass cliff", "the hill still isn't fixed".
The unexamined third move is to make the DESTINATION GROUND ALREADY HAVE THE DONOR'S
SHAPE over a large enough area — which is a context/region question, not a weld one.

## Registered questions

**S1 — THE GROUND-UV LAW (definitive; the current answer is weak evidence).**
The playtest-2 probe compared per-plan vs per-surface uv rate on the donor apron and
found surface flatter (0.981 vs 0.982) than plan (1.000 vs 0.986) — but both are ≈1.0
and the sampled slopes were shallow, so the effect size does not carry a build.
Measure across ALL stock ground classes with real slope bins (0-10 / 10-25 / 25-40 /
40°+): duv per plan-unit vs per-surface-unit; whether a 4u CELL maps to exactly one
tile (the L3 per-cell model) even when the cell spans a slope; and what happens to uv
where stock ground crosses a break in slope. **The build decision this settles:** may
a destination-field retile (`G.ground_uv`, plan-projected) ever be applied to sloped
carried ground, or is that projection itself the "stretched grass"?

**S2 — THE FAMILY-BOUNDARY LAW (the seam class's root).**
Our seams survived BOTH uv schemes, so they are not a tiling bug — they are the
boundary itself. In stock: does a ground TILE-FAMILY boundary ever lie in open, flat,
walkable ground? Or is every family boundary co-located with a feature (a wall foot,
a water edge, a forest blob, a block border, a coast)? Measure boundary length by
co-location class, plus what stock puts ON the boundary (a transition tile
vocabulary?). Prior art to build on, not re-derive: `biome_seam_anatomy.py`,
`biome_adjacency_census.py`, and the ecotone/RIBBON FALLACY finding. **Settles:**
whether a carried-sheet boundary can EVER be made invisible in open ground, or must
be hidden behind a feature / eliminated.

**S3 — THE GROUND-NORMAL LAW (the shading half of "seam").**
What normals does stock ship on ground? Uniform up, face-derived, or smoothed across
faces — and does the convention change with slope or class? Measure the angle between
each ground vert's shipped normal and (i) world up, (ii) its own faces' area-weighted
average. **Settles:** whether round 8's harmonized smooth field is stock-lawful or
itself a novel convention that reads as a seam against unsmoothed bench grass.

**S4 — THE CONTEXT CENSUS (is our bench in-language at all?).**
For every stock rock/wall component: the plan distance from its foot to the nearest
sea/coast, the area and extent of contiguous walkable ground around it, and the
smallest landmass that hosts a wall of each size class. Then place OUR configuration
(mesa ~61×57u, bench island grass reach ~50.6u, foot-to-coast 6-10u) in that
distribution. **Settles:** whether the bench is a legitimate host or the whole
context is off-language — the mesa registration's own declared FAIL clause.

**S5 — THE APPROACH-GROUND LAW (what stock's ground DOES at a wall foot).**
Profile stock ground outward from wall feet: slope vs distance, the relief of the
weld line itself, how far out the ground takes to return to its local lowland, and
whether the approach ever reads as a discrete mound (our "hill") or always as
regional slope. Include the donor (15,14) as a labeled case. **Settles:** the
BURY-vs-LIFT dilemma — what radius of destination ground must already carry the
donor's shape for the base to read right, and therefore whether a 50u island can
ever host this donor.

**S6 — THE REGION-CARRY FEASIBILITY (the candidate that deletes the junction class).**
Every failure has been at a minted junction between carried and bench sheets. The
untried move that removes the class rather than relocating it: carry the donor's
WHOLE NEIGHBORHOOD (the mesa's block plus its ground, out to the sea) as the island
itself, minting only the SEA boundary — a junction class we have proven machinery and
laws for (coast-mosaic / `world-transplant --ground` / the SEA4-UNDER-LAND LAW).
Assess mechanically: what would be carried, what minted, which existing gates apply,
what the block-border and coast-nav requirements are, and what the known blockers
are. **Settles:** whether the next registrable round is a region carry, and at what
scope.

## Method

Multi-agent orchestration (the owner's ask): parallel readers over the arc's own
record; six independent instruments for S1-S6, each ADVERSARIALLY VERIFIED by a
skeptic that re-measures by a different method before any finding is believed; then a
judge panel of independent approach designs, synthesized into one causal model + one
ranked decision. Read-only against stock disc-1; nothing deploys; the live bench
stays as the owner last saw it. Instruments land in
`studies/overworld-topography/`, artifacts in its `out/`.

## Success criterion

The study succeeds if it produces (1) an apportioned answer to S0 — named cause(s),
with the discriminants actually measured, (2) at least one law per S1-S5 stated with
numbers and its instrument's limits declared, and (3) a RANKED decision on the next
round with a predicted outcome for each candidate, including an explicit
"stop/rest the lane" option. It FAILS if it can only restate the defect list — in
which case the wall arc rests and the owner decides scope.
