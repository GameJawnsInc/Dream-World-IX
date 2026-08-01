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

---

# FINDINGS (2026-07-31 — 20 agents, 6 instruments, every law adversarially verified)

Ran as workflow `wf_784a4932-e07`: 3 history readers, 6 law instruments, 6 independent
skeptics, a 3-lens design panel, a synthesizer, a completeness critic. **5 of 6 laws
had their build implication REFUTED by their skeptic** — the verification pass was the
most valuable part of the study, and its refutations are recorded here as first-class
findings. Instruments and artifacts: `studies/overworld-topography/*.py` +
`out/*.json` (40 artifacts). Nothing was deployed; the live bench is untouched.

## THE HEADLINE — measured, and independently re-verified by the parent session

**The minted ring's ground mesh is shattered.** Deployed bytes vs the pristine backup
(`terrace-strip-prewall.20260731-220001`), same six blocks, parent-session check:

| | live | pristine | stock grass |
|---|---|---|---|
| grass tris | 4,181 | 858 | — |
| median tri area | **0.32u²** | 8.00u² | 8.0u² |
| under 1u² | 79% | 1% | ~0% |
| max tris per 4u cell | **82** | 5 | 4-5 (map-wide max) |
| grass steeper than 45° | **107** | 0 | 0 |
| short edges over the engine's 2.34375u climb ceiling | **15** (worst 3.44u) | 0 | 0 |

It is radially localized: lawful in the carried core (r 0-16u), collapsed through
r 16-56u — the ring the owner has been pointing at in every screenshot. Cause: a
**per-vertex** reconciliation of a flat island to a non-level donor weld line forces
partition, slicing, conformance splits, centroid fans and four stitch passes whose
tolerances fight each other (border stitch inserts at 0.12u = 2× the 0.06u micro-weld
radius, so its wedges can never be welded away; the residue stitch's 0.05u sits INSIDE
the weld radius, so everything it repairs is damage the later passes created).

## S0 — THE ANSWER, apportioned

**The recurrence is not eight bugs and not the wrong island. It is one loop:** each
round fixed the named defect by AUTHORING something new next to the mesa, and the eye
then judged the new thing. Measured: **12 of 13 playtest verdicts** and **32 of 37
individually named defects** landed on whatever that iteration had most recently
authored; none ever landed on carried stock geometry that was in its own context.
Two things kept the loop from closing:

1. **The tests could not fail. 0 of 13** — the gate suite has never once fired before
   the owner's eye. Every gate asks *"is this value inside stock's distribution for
   this element?"*, never *"does stock ever build this shape at all?"* So a wall end
   with 42 stock counterexamples and 0 instances, and a mound with 176 counterexamples
   and 0 instances, both passed every percentile. Round 6 shipped a 10.94u weld
   displacement inside a 12u cap and the owner named exactly that face: **a gate can be
   green and wrong in the same number.** Every gate in the suite was written *after* a
   verdict named its class — the suite is a regression harness, not an oracle.
2. **The repairs were the defect factory** (the table above).

Apportionment (weights are judgement; the discriminants are measurement): **~20%
independent bugs** — real convergence, all of it on the WALL BODY, six classes
permanently dead; **~55% structural**, but in NONE of the three forms the arc assumed
— the surviving form is **tessellation + height**, not uv, not family, not shading;
**~15% context** — and much weaker than S4 first claimed; **~10% process** (round 8's
six-change bundle made its own verdict unattributable, violating this project's
one-change-per-test rule).

## THREE BELIEFS THE ARC ACTED ON, ALL MEASURED OUT

- **UV DISCONTINUITY IS NOT THE SEAM.** The live bench is *more* uv-continuous than
  the real game: **83.9%** of shared ground edges uv-exact vs stock's **52.4%** (and
  only 23.5% of stock's own cross-cell shared positions match at all). A uv break at a
  cell border is stock-normal.
- **THE TILE FAMILY I "FIXED" IN ROUND 8 IS NOT ON THE BENCH.** Deployed: 4,212
  grass.main + 10 grass.B + **zero grass.D**. Its only art-set boundary is 46u of
  grass.B|grass.main — a pair stock itself ships. (The unbridged-pair law is real and
  strong — grass.main|grass.D = 0 edges map-wide, confirmed on disc 4 — but it does not
  apply to this build.) Atlas luminance cannot even discriminate a family boundary from
  an ordinary tile butt (AUC 0.524).
- **GROUND NORMALS ARE RENDER-INERT.** `WorldMap/Terrain` binds only `vertex` +
  `texcoord`, has no light position, and `WMMesh.Normals` is read at **zero** non-debug
  sites (the walk query recomputes normals geometrically). **Round 8's entire
  "lighting half of the seam" pass could not change a single pixel** — and it put
  180.1u of >8° crease onto the donor's own weld line, the one surface the owner had
  praised. Add no normal gate; never spend another round on ground shading.

## THE DILEMMA WAS PARTLY MANUFACTURED

The **4.4u weld relief** the arc engineered against for five rounds (bury vs lift) is
a **tail statistic**: over the donor's 41 grass foot verts the honest p10-p90 spread is
**2.63u**, 65.9% of the line sits within 2u of its own minimum, and the max-min is set
by ~2 vertices. **34%** of the raw figure is a FOREST contact grass never has to reach
(grass-only span 3.03u), and **1.65u** of the remainder is a rigid **1.44° tilt** —
below stock's own median foot tilt of 2.23°. Residual after de-tilt: ~1u.

## THE ONE LAW THAT SURVIVED ITS SKEPTIC — S5, THE APPROACH-GROUND LAW

Stock's weld relief is not made at the foot; it is the regional ground field sampled
there (relief at 8/16/32u = 0.99/1.01/1.37× the weld line's own). **0 of 176
components are pedestals.** Outward the ground is a **short lip then a LEVEL TERRACE,
never a ramp** — feature-median slope 0.5/0.7/1.3/-0.1/0.5° across 0-4/4-8/8-16/
16-32/32-64u — sitting at a **sustained ~1.0-1.5u offset** over local lowland
(0.93/0.96/0.79/0.86/1.49u by distance band). Both arc moves are off-language: BURY
deletes stock's own transition; LIFT-with-falloff manufactures a monotone radial mound
resolving back to a plane, of which stock has **0 instances in 176 components**.
Corrections that matter: the required sustained offset is **~1.0-1.5u, not 4u**; the
bench's 4u-over-24u ramp is off-language in ARRANGEMENT but *in*-language in AMPLITUDE
(~stock p80 at that lag); and **a calm host is a real ~10% stock subpopulation** —
17/176 components sit on ground spanning ≤4.15u within 50.6u of the foot.

## THE OTHER LAWS, IN THEIR SURVIVING FORM

- **S1 ground-uv:** the per-4u-cell **budget** is plan-locked (cell uv extent p50 =
  1.000 tiles in every slope bin 0-40°; within-one-tile rate flat ~0.80), and the
  vocabulary break is at **40°** (curtain regime), not 35°. The plan-vs-surface debate
  that drove rounds 7-8 was **near-vacuous**: below 20° the two conventions are
  indistinguishable (discriminating power 0.005 at 12°), and above 20° stock ships a
  flat ~45/55 MIXTURE of both — desert trends the *other* way. The first pass's
  "contour axis plan-locked / down-slope surface-following" was SVD-magnitude ordering,
  not measured axes. **So the L3 retile was not the stretch, and neither is donor uv.**
- **S2 family boundary:** clause 1 solid (0 grass.main|grass.D map-wide, both discs);
  clause 2's "67.7% of boundaries are in open ground" corrected to **30.5%**; clause 3
  (luminance) is a **null result**. **S2's registered question was never answered** —
  the object was swapped from carried-sheet boundaries to art-set boundaries.
- **S3 normals:** decisive (above). Byte-fidelity clause corrected: the pre-snap
  construction is **angle**-weighted, not area-weighted, and the weld is by world
  position **across block borders** (4,600 shared positions, 5 disagreeing).
- **S4 context:** **the original verdict was REFUTED by measuring the actual bench
  instead of a modelled disc.** Live foot→coast is min 4.0 / med 17.9 / **MAX 25.9u**
  (not "~10u"), which is p33 among 33 stock components; two of the four approach annuli
  it declared empty are the 2nd and 3rd largest, and the mesa-class annulus floors are
  cleared 3-4×. **The bench is not the villain.** Only 32-64u = 0u² survives, and its
  stock floor is a 112u² sliver from one instance.
- **S6 region carry:** the "continent-scope" verdict was refuted by min-cut over a
  16,222-node land graph: a **1×1 carry of block (15,14) REDUCES the minted junction
  38-40%** (248-256u vs the live 416u) and is the optimum at 1-block scope; block
  (15,14) is terrain-part only, zero objects, zero landmarks, zero water to crop. But
  it does not restore the bench-side tessellation, so if the shattered sheet is the
  carrier, it relocates rather than removes.

## WHAT THE STUDY COULD NOT SETTLE — and it is the load-bearing gap

**Nobody has ever seen the defect.** Thirteen verbal verdicts, ~40 offline artifacts,
zero images. `tools/game_snap.ps1` was never run (attempted at write-up: the game was
not running), no in-game video was ever requested despite
`feedback-video-for-visual-bugs`, and the project's calibrated per-pixel eye was never
pointed at the bench. So the central causal link — *that the shattering is what the EYE
resolves as "meadowy tiles" and "seams"* — is **inference**, and the critic
half-falsified it: the fine triangles carry **stock-lawful uv rate** (96.89% inside
stock's p1-p99 band) and cross atlas gutters LESS than stock (7.8% vs 36-45%). What IS
measured is a tiny extreme-**anisotropy** tail localized to the 16-24u rim (p99
anisotropy 81,051, rate p99 91.2 px/u vs 2.0-2.2 and 33.9-50.4 outward) — the
collapsed repair-pass facets, on the order of tens of triangles and ~5u².

## SAFETY NOTE ON THE LIVE BENCH (new, nobody had checked)

The ring contains **107 grass triangles steeper than 45°**, **5 near-vertical**
(geometric ny ≤ 0.1 — `WMPhysics.Raycast` SKIPS these for the ground query while they
still render as grass), and **15 short grass edges above the engine's 2.34375u climb
ceiling** (worst 3.44u). The pristine bench has zero of all three. The cache path
`WMBlock.cs:155 → WMPhysics.cs:49` applies neither the up-facing nor the topograph
filter, so a cached bad triangle can ground the actor. This is the one defect class in
this project that can strand a save, it is not exercised by any gate, and it argues
against leaving the current build live for casual walking.

## VERDICT ON THE PANEL'S RECOMMENDATION — the parent session does NOT adopt it

The panel recommended a **cell-granular junction** (delete 21 invented mint sites;
every 4u cell wholly donor or wholly bench, never split; de-tilt 1.44°; ~1u as a
sustained island-wide offset). Its diagnosis is right and its deletions are the right
deletions. But the critic's objections stand and are not answerable by argument:
it would be **the ninth consecutive authored intervention at the same junction**,
predicting its own next verdict under the study's own top-ranked law; it **violates the
carry-purity law it convicts round 8 for violating, at 27× the magnitude** (1.65u of
motion on carried stock bytes); it is a **larger bundle** than the six-change lever it
indicts; and its causal bet is now the **last unfalsified hypothesis** rather than a
measured cause — and it is *half-falsified already* on the uv and gutter axes.

**Registered decision: no ninth build round. Resolve the visual question first**, by
the two cheap steps that need no deploy and no playtest:

1. **THE COARSENING A/B NULL TEST** (offline, ~1-2h): rebuild the deployed ring in
   memory as one quad per 4u cell carrying that cell's area-majority (quad,ori) window,
   render both A and B through the project's own pixel eye, and see whether the
   artifact the owner names survives coarsening. This decides the exact bet a build
   round would spend a playtest on. Instrument named by the critic:
   `critic_coarsen_ab.py`.
2. **THE LOCALISATION SNAP** (owner, ~2 minutes): three stills of the live bench —
   the NE rock line, ~30u out looking in, and looking down at his feet on the lifted
   ring. One frame distinguishes bench grass from carried apron from the rock line, and
   sub-cell patchwork from a large-area smear from a geometric step. This is the
   evidence class the arc has never once collected.

Bank regardless of what follows: **GATE T** (tessellation — triangle area band + tris
per 4u cell, scoped to the GRASS class: red on the live bytes, green on both pristine
and stock, the only gate in this arc with demonstrated discriminating power) and a
**walkability pass** (ground-query MISS, the 2.34375u climb ceiling, and no
render-only grass facet). Both are cheap, both are permanent, and both measure what
the eye and the engine judge rather than what the mesh reports about itself.

---

## THE COARSENING A/B — run same-day (`critic_coarsen_ab.py`, out/coarsen_ab/)

Both banked gates shipped first (`bench_audit.py`: 4 failures on the live bytes, 0 on
pristine — the arc's first gate that is red on a build the owner faulted and green on
ones he did not). Then the null test: A = deployed bytes, B = the ring coarsened to
one quad per 4u cell (pristine L3 decode, corner heights sampled from A's own
surface), C = pristine, rendered UNLIT (engine-faithful per S3) from nine vantages
including the owner's three screenshot positions.

**Eye calibration (binding precondition): partly met.** A reproduces offline: the SE
terraced grass bank covering the wall base (strong — the exact class of the owner's
screenshot 2), the west green spike, and faint dark mottling on the east shelf
(weak). A does NOT reproduce the thin bright seam lines at these camera/resolution
combinations — that class stays owner-eye-only offline.

**VERDICT — the null test SPLIT the causal claim, and the biggest class is NOT
tessellation:**

1. **"Raised-grass cliff covering the base" SURVIVES coarsening essentially
   unchanged** — B's bank is the same stepped terrace as A's, because the carrier is
   the MINTED HEIGHT FIELD (the Voronoi smoothstep mound), which corner-height
   sampling preserves at cell scale. This is S5's off-language ramp, seen in pixels.
   Consequence: **the panel's cell-granular junction, whose corner heights sample the
   current field, would have shipped this class straight into a tenth verdict** — the
   A/B just spent two hours instead of a playtest to find that out.
2. **"Meadowy corner tiles" WEAKLY supports the tessellation/window-mixing carrier** —
   A's east shelf mottling vanishes in B's uniform lawn (down_ring view) — but the
   offline reproduction is too faint to be decisive on its own.
3. **"Seams" UNDECIDED offline** — not reproduced in A at these vantages; geometry
   (the lift field's steps, the border-stitch hairlines, the open slits whose
   coordinates matched two of the owner's seam sightings at x=384 and (420,−490))
   remains the leading suspect by elimination, since uv, family, and shading are
   measured out.

**The load-bearing conclusion: THE LIFT FIELD IS THE PRIMARY CARRIER.** The strongest
named class is its shape; most residual geometry classes are its splinters; and the
one round whose lawn drew zero complaints (the buried mesa, playtest 1) is exactly
the round with no lift field. Any next build must DELETE the mound outright — S5's
lawful shapes are a level terrace at a sustained ~1-1.5u offset, or no stature
change at all — rather than re-tessellate under it. Coarsening alone is not a fix;
tessellation remains a real off-language axis (GATE T stands) but it is not what the
owner has been naming most loudly.

Still owed before any registration: the owner's three in-game stills (the seam class
has never been reproduced by any instrument, and it is now the only class without a
measured carrier).
