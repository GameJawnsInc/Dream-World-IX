# RIM-AWARE STRIP CARRY — prediction registration (BEFORE building)

2026-07-31. The junction-aware round scored PARTIAL with the failure isolated to ONE
junction (JUNCTION-AWARE-PREDICTION.md), and the rim study then decoded that junction's
construction (RIM-GRAMMAR.md: THE DISPLACED-ROW LAW + complete numeric targets). The
owner chose this round: everything proven carries unchanged; the CREST RIM alone is
rebuilt to the law, and the foot band's declared shade fix rides along. Written before
the first builder edit; the bench is byte-verified pristine
(`backups/terrace-strip-prewall.20260731-003703`).

## The claim under test

The strip-carry claim, third and final presentation: **whole-mesh strips recomposed
read as FF9 when the joins follow stock's junction grammar — now including the rim's
displaced-row construction.**

- **CARRIED (in-game proven in the junction-aware round, unchanged):** the four donor
  strips (same pool, rigid pose), the crease seam welds (top-aligned matching +
  least-squares centering + taper + fold repair), the level foot weld at y = 3.2, the
  notch bridge + unwalkable-chute handling (bridge edges join the crest ring for the
  rasterization below), the pristine-bench guard, the game-eye culled-render review.
- **MINTED — the rim rebuilt to THE DISPLACED-ROW LAW:**
  1. **The plateau top is the INTACT 4u lattice.** Interior cells are whole cells.
     The lattice-clip against the crest polyline is DELETED — nothing on the top sheet
     is ever cut by a curve.
  2. **The crest ring is RASTERIZED onto the lattice graph**: a simple lattice cycle
     approximating the strips' top path is chosen, and each cycle vert is DISPLACED
     onto the strips' actual top boundary — **1:1, the strip's own top verts BECOME
     the rim row's verts** (shared verts, not proximity-matched). Cells with displaced
     corners remain whole (deformed) cells. The vert-correspondence solve (bijective,
     monotone along the ring) is declared mechanism freedom.
  3. **Crest y:** the rim row's y is the strip tops' y (stock wander rides along,
     rigid pose, no flattening pass); ring-2 inward is level at TOP_Y (J1: the plateau
     runs level from the weld).
  4. **The top-course texture is CARRIED INTO ITS SEAT:** the strips' top course
     already wears the cols 4-7 rows 3-4 grass-lip band with fv = 0.0 on their own
     crest edge (they are stock meshes); welding the lattice rim directly onto those
     verts lands the painted lip exactly ON the weld line, per the law. Minted top
     tris (lattice + notch patches) wear plain plateau grass — lawful, R3's plateau
     side has no rim vocabulary.
  5. **The foot band relever (the dark-shade fix):** row-10 retile becomes
     INTERMITTENT (target share 45-60%, station-run alternation, deterministic seed),
     one 3.7u course (was 4.6), v sampled at stock's phase [row 10.12 → 11.09] (was
     [10 → 11]). Orientation unchanged — it was correct. The intermittency PATTERN
     (run lengths) is unmeasured; declared freedom, and if a verdict names patchiness
     specifically, measuring stock's run-length distribution is the next single lever.

## Gates

All junction-aware gates carry (massing, census, reach, h_pairs at seams, the
per-carried-normal winding gate, watertight residue ≤ 24 once-edges / none > 5u / none
visible in the culled renders), plus NEW RIM GATES from the study's numbers:

1. **TOP-SHEET PURITY** — every top tri is an intact lattice half-cell, a rim-course
   half-cell with displaced corner(s), or a declared notch patch. ZERO clip-minted tris.
2. **DISPLACEMENT ENVELOPE** — rim vert displacement p50 ≤ 1.2u, p99 ≤ 2.5u
   (stock: med 0.80, p99 2.41; the lattice guarantees ≤ 2.83 exists).
3. **SLIVER GATE** — top-sheet sliver fraction (plan area < 2u² or min angle < 15°)
   ≤ 3% (stock's own rim course: 2.1%).
4. **RIM WATERTIGHT BY CONSTRUCTION** — the crest contributes ZERO once-edges and zero
   T-junctions (rim verts are shared strip verts, not welded matches); the aggregate
   residue budget is spent elsewhere or not at all.

## AMENDMENT (pre-build, 2026-07-31): the two mechanism freedoms are CLOSED by measurement

The owner asked for more study unless confident; both declared freedoms were doing
load-bearing work, and both are now measured. Declared before any builder edit.

1. **The correspondence is INHERITED, not solved — THE LATTICE-HOME POSE.** The
   registered "rasterize + bijective correspondence solve" freedom is replaced: the
   strips ARE stock walls, so their top verts are already displaced lattice verts in
   the donor frame. `probe_strip_lattice_homes.py` confirms it on all four real
   strips: crest lattice residual med 0.77-1.04u (stock: 0.80), p99 ≤ 2.40 (stock:
   2.41), on-grid 20-38% (stock: 28%), and **ZERO jump steps** (no consecutive top
   verts more than one lattice cell apart). Therefore the pose group snaps to the
   lattice symmetry — yaw in 90° steps, translation in 4u steps — which transports
   each strip-top vert's donor home onto the bench lattice: the rim row IS the
   strip-top verts seated at their transported homes; the interior fill is intact
   bench cells inside the rim cycle. No solve.
2. **SAME-home collisions are lawful course FANS, not defects.** 0-4 per strip: two
   adjacent top verts sharing a nearest lattice vert yield a course triangle fan —
   stock's own rim course mixes triangles into the quad row (0.95 tris/edge, area
   p25 6.0 vs the pure-quad 8.0). A JUMP at build time (none observed) is handled by
   the 4u translation freedom or one inserted undisplaced rim vert, and counts
   against the displacement-envelope gate.
3. **Costs of the snapped pose, declared:** (a) the seam-centering solve is now
   4u-quantized — the taper absorbs the residual, and the PROVEN seam gates (shear
   ratio ≤ 1.5, 12u cap) must still close offline, with cut-column freedom (±2) as
   the first lever; (b) the four strips' lattice paths must CLOSE around the ring
   within seam adjacency. Either failing offline is a PLUMBING STOP before any
   deploy, not a verdict.
4. **The foot intermittency pattern is now measured, replacing the declared freedom:**
   stock's row-10 runs are station-scale patches — run length med 7.8u (p25 4.0,
   p75 24.7, tail to ~80u) alternating with gaps med 6.3u (p75 10.3). The mint
   samples run/gap lengths from these ranges (deterministic seed); gated: share
   45-60%, run and gap medians within ±50% of stock's.

## REGISTERED PREDICTION

**PASS** — the owner reads it as FF9 interior rock wall. Basis: every complaint class
across both prior rounds now has a measured law behind it (faces/seams/foot passed
in-game already; the rim and the shade were the two open classes, and both are now
decoded, not guessed).

## BUILD NOTES (pre-playtest, declared with the deploy — 14 offline iterations)

The claim and gates are unchanged. Mechanism deltas found while building, all measured
against stock before adoption:

1. **The top construction converged to the DELAUNAY FORM of the displaced row.** The
   literal cell-based construction (classify lattice verts rim/proj/interior, emit
   whole cells, fill pockets) minted a thin-wedge class wherever a diagonal crest run
   passed just inside a lattice row, and a corridor class at a donor promontory —
   five successive mechanisms (greedy zip, offset-searched DP zip, 2-opt flips,
   index-fanned conformance, ear-fanned pockets) each fixed one site and exposed
   another. The closed form: **Delaunay over [crest verts + interior lattice verts
   ≥ 1.2u from the crest], clipped to the crest polygon** — the lattice interior
   reproduces intact half-cells on its own, corridors get max-min-angle ladders, and
   the boundary is the crest cycle edge-for-edge. Two small local passes complete it:
   a SLOT CAP (a concave wedge whose Delaunay tri centroid-clips away leaves a
   see-through slot — capped against its kept-boundary neighbor) and INTERIOR
   RELAXATION (a sliver tri's interior vert may move ≤ 1.2u — the far field's OWN
   measured off-grid envelope, R1: 35% off-grid, p90 1.22u).
2. **CREST SILHOUETTE REPAIR:** the seam welds leave sub-2u crest edges and
   doubling-backs (turn > 150° on short legs) — debris stock's crest never shows
   (segments p25 = 4.0, turns p99 139). Repaired by merging the debris verts into
   the wall (position substitution ≤ 3.5u, the displacement envelope's own order);
   4 verts merged this build.
3. **The sliver gate, decomposed against stock:** the registered ≤ 3% compound gate
   held, but the honest baseline is now measured finer — stock ring-1's 2.1% =
   THIN (angle < 15°) 1.4% + SMALL (area-only) 0.7%. Final build: 1 sliver on 79 top
   tris (1.2% compound) — one 0.85u² tri deep in a 3u-wide donor promontory corridor,
   all-crest-vert (nothing may move), at stock's own thin rate.
4. **Final gate state (deployed build):** closure gap 0.35u; seam turns 68-86°; weld
   displacements ≤ 10.94u (cap 12); rim displacement med 0.92 / p99 2.39 / max 2.40
   (stock: 0.80 / 2.41); home jumps 0; watertight residue **1 once-edge** of 8483
   (0.012% — round 6 deployed with 4); foot fringe 54% share (stock 53%).
5. **The culled-render NE anomaly is explained and accepted:** a far-side donor
   promontory's outer faces, correctly wound (carried normals agree) and correctly
   culled, read as a floating tri under the offline renderer's PARALLEL rays at 17°
   elevation — an eye-at-infinity view. A ground perspective eye cannot reproduce it
   (the near wall's angular height occludes the far rim) and the elevated world
   camera looks down, which removes the sky-gap ray geometry. Forensics in the build
   log (6 connector tris, all donor-lawful). If the playtest shows a floater THERE,
   this note is falsified with it.

## Falsification semantics — declared in advance

- **PASS** → the wall rung closes SOLVED at strip granularity; `world-terrace`
  productization becomes eligible.
- **FAIL on rim form AGAIN** (jagged / incoherent / jutting at the crest despite the
  displaced-row build) → the law as read is insufficient at this scale; **the
  minted-plan wall lane CLOSES to whole-feature carry only. This is the last minted-rim
  presentation — no fourth round.**
- **Regression in a previously-passed class** (seams / foot geometry) → plumbing
  against a proven carry: one fix credit, then stop.
- **The foot SHADE alone still wrong** → a texture-lever failure recorded on its own
  axis (share/pattern/phase); it does not reopen or close the rim verdict.

One round. Scored on the owner's verdict, whichever way it lands.

## SCORED — FAIL on form; THE MINTED-PLAN LANE CLOSES (2026-07-31)

Playtest verdict, two sites, both named with coordinates:

1. **(428, −507), blk[6][7]** — *"the cliff is weirdly sliced, causing a stretched
   face along the cliff."* THE SEAM TAPER MADE VISIBLE: seam 0 carried this build's
   largest weld displacement (10.94u, inside the 12u gate) sheared across one station
   — the crease-weld's standing cost ("slightly stretched cliff" was already noted in
   the junction round's playtest 1 and carried as a scoring cost). The gate bounded
   it; the eye still reads it.
2. **(396, −504), blk[6][7]** — *"weird extra triangle part… an extra triangular
   grass piece."* THE WEST FINGER: a donor crest promontory sliced by the cut window
   into a 2-3u corridor the donor never shipped alone — its corridor top reads as a
   flat grass triangle and the slot cap as a rock flap lying on the ground. An
   ENDPOINT stock never has, minted by the cut.

No watertight class was named (no holes, gaps, or flicker — the audits' first fully
clean round in-game), and neither the dark foot band nor crest jaggedness recurred.
Both named defects are FORM defects of the COMPOSITION ITSELF: the seam weld's
displacement budget and the cut windows' artificial terminations.

**The registered closure clause fires.** This was the declared last minted-plan
presentation: strips cut mid-wall and recomposed — with every join now built to a
measured law — still do not read as FF9 at the joins' own scale. **The minted-plan
wall lane CLOSES to whole-feature carry.**

**The owner's diagnosis, recorded as the next decode's frame:** *"some parts don't
lift from base to rim cleanly. we may need more research on how to build connective
walls that have logical endpoints instead of trying to build the top to fit. both
sides have a responsibility."* Exactly: stock walls TERMINATE lawfully (their ends
are geometry, not cuts), and their plateau side is built WITH the wall, not fitted
to it afterward. Neither has ever been measured — every study so far measured wall
INTERIORS (tiles, instances, massing, junctions, rim) and every build cut strips
mid-wall, minting endpoints stock never ships.

**Banked from this round regardless:** the lattice-group pose + inherited homes
(probe-validated, in-game clean), the crest silhouette repair, the Delaunay
displaced-row top (watertight to 1 edge in 8483 — the machinery for any future
plateau mint), the measured foot pattern (no shade complaint), and the culled-render
NE-anomaly note (no floater was reported — the eye-at-infinity explanation held).
