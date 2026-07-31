# RIM GRAMMAR — how stock CONSTRUCTS the crest rim (questions registered BEFORE the instrument ran)

2026-07-31. The junction-aware round scored PARTIAL (JUNCTION-AWARE-PREDICTION.md): the
carried faces, the crease seams, and the foot weld all passed in-game silently; the one
junction that failed on form is THE CREST RIM — jagged silhouette, incoherent plateau
seam, jutting tris, through five sub-iterations of weld machinery. The owner's own call:
*"need to think harder about how a rim can be formed... should we stop and do more
studying?"* — yes. This fifth study on the shared wall instrument decodes the rim's
CONSTRUCTION, the thing J1 never measured (J1 was statistical: weld rate, fringe dy,
tile vocabulary — never the tri LAYOUT).

## The suspicion driving R1

Our minted plateau top is a **4u lattice CLIPPED against the crest polyline** — every
rim tri is an arbitrary clip sliver, so the edge flow is incoherent by construction no
matter how exactly it welds. The hypothesis: stock never clips — its plateau at the rim
is a **DEFORMED LATTICE COURSE** (the rim row of lattice verts displaced onto the crest
curve, topology kept regular), i.e. an inset ring of well-shaped tris running parallel
to the crest. If true, coherent edge flow is automatic and no clip-and-weld can imitate it.

## Questions — registered before running

**R1 — THE RIM RING'S TRI LAYOUT (the central question: deformed course vs lattice clip).**
Per wall component, discriminants:
- plan lattice residual (distance to the 4u grid) of CREST verts vs the ring-1 INNER
  boundary verts vs far plateau verts — the deform hypothesis predicts crest off-grid,
  inner ring back on-grid;
- ring-1 tri count per crest edge (a quad course reads ≈ 2);
- ring-1 tri SHAPE vs far plateau: plan area distribution (a full half-cell is 8u²),
  min plan angle, sliver fraction (area < 2u² or angle < 15°) — a clipped lattice shows
  a sliver tail, a deformed course shows the far-field's shape;
- inner-boundary edges vs the nearest crest segment: direction misalignment (a parallel
  course reads low) and offset distance (one course ≈ 4u, tight spread).

**R2 — CREST SILHOUETTE STATISTICS (the jaggedness numbers a mint must hit).**
Chain the crest edges into ordered polylines; measure segment length distribution, plan
TURN angle per interior vertex (binned), the sign-ALTERNATION rate of consecutive large
turns (zigzag = high alternation), and y-jitter (per-edge |dy| + detrended deviation).

**R3 — TOP-COURSE ANATOMY AS A COURSE (both sides of the weld).**
- Plateau side: ring-1 tile histogram split from ring-2 (J1 pooled two rings); the uv
  ORIENTATION of ring-1 tris relative to the crest — which tile edge (u/v extreme) sits
  ON the weld (the foot's row-10 band puts its painted fringe edge on the weld line —
  does the top do the same?).
- Wall side: the crest-touching wall course — its height below the crest, its tile rows
  vs mid-face (is there a dedicated TOP atlas band, the twin of the foot's row 10?), and
  which tile edge kisses the crest.

**R4 — OVERHANG BOUNDS (the "jutting triangle" budget).**
For near-crest wall verts (within 1.5u of crest y): signed plan excursion OUTWARD beyond
the crest polyline — med/p90/p99/max. Plus the setback profile: median outward distance
at fixed drops below the crest (0.5-1.5u, 1.5-2.5u, 3-5u).

**R5 — THE FOOT-COURSE SHADE (the dark-band bug from playtest 2).**
Our row-10 fringe read DARKER than the carried mid-face. From stock's bottom course plus
the vanilla atlas PIXELS (`ff9mapkit.world.atlas.load_atlas(source="bundle")`):
- what fraction of stock bottom-course tris wear the row-10 band at all vs plain
  mid-face rows — maybe stock retiles only a thin sliver, not our full 4.6u course;
- the v-SUBRANGE within row 10 stock actually samples, and the band's real height above
  the foot weld;
- mean luminance of row-10 cols 6-9 (whole tile AND stock's sampled subrange) vs the
  mid-face rows' tiles — is row 10 inherently darker, or darker only outside the
  subrange stock uses?

## Method

Same crest-seeded topo-49/PLATEAU extraction as the four prior wall studies (language /
instances / massing / junctions); read-only vs stock disc-1; instrument
`studies/overworld-topography/rock_wall_rim.py`; artifacts →
`out/rock_wall_rim.json` + a plan render of the largest components' rim courses
(crest polyline + ring-1 tris — the eyeball check on coherent-course vs slivers).

## Success criterion

R1 resolves to a NAMEABLE construction law + R2 yields numeric silhouette targets →
a rim-aware build round becomes registrable. If no law emerges (stock's rim turns out
as arbitrary as a clip), the minted-plan wall lane rests at whole-feature carry.

---

## FINDINGS (measured 2026-07-31 — 48 blocks / 62 components / 951 crest edges)

One instrument iteration was needed and is declared: the first R4 pass assigned distant
along-wall verts to far-away crest edges (a fake 19u "setback"); the rerun caps the
plan distance at 8u. R5 gained the unwrapped v-span/orientation measures and the atlas
crops after the first pass showed raw fv statistics were phase-ambiguous.

**R1 — THE DISPLACED-ROW LAW. Stock never clips.** The plateau is the intact 4u
lattice everywhere; the crest is formed by DISPLACING the outermost lattice row's
verts onto the wall's top boundary:
- crest verts sit OFF-grid — plan residual med 0.80u, only 28% on-grid, p99 2.4u —
  while the ring-1 inner boundary sits back ON-grid (61.5% ≈ the far field's 64.5%,
  med 0.0u): the displacement is one row deep;
- ring-1 tris stay full half-cells — area med 7.5u² vs far 8.0, min-angle med 41.6°
  vs 45.0°, sliver rate 2.1% vs the 0.9% far-field baseline. NO clip tail;
- 0.95 ring-1 tris per crest edge — a single-quad-deep course;
- the inner boundary is the lattice's own hypotenuse SAWTOOTH (align med 50° at
  lattice scale, offset med 1.66u), not a smooth inset curve: the coherence lives in
  the TRI LAYOUT, not in a literal parallel ring.
The render (`out/rim_courses.png`) shows it plainly: one coherent course of uniform
tris along a smooth crest, in all three largest components.

**R2 — the silhouette targets a mint must hit:**
- segment length med 4.14u, **p25 = 4.00u — never shorter than a cell** (the
  no-sliver signature), p90 5.51, p99 6.52;
- plan turn med 14.9°: 50% < 15°, 82% < 30°, only 4.9% ≥ 90°; sign alternation of
  large turns 46.5% = coin-flip (no systematic zigzag);
- the crest is NOT level: per-edge |dy| med 0.25u p90 0.73, detrended |y| dev med
  0.21u p90 0.68 — a gentle ±0.7u wander. (Our dead-flat TOP_Y is itself un-stock.)

**R3 — the crest vocabulary lives on the WALL side (the twin of the foot's row 10).**
The plateau side is plain grass to the weld (ring-1 tiles = ring-2 = far field, cols
0-1 rows 24-25; |dv| med 0.02 — no orientation preference; J1's "no rim vocabulary"
holds for the plateau). The WALL's crest course wears a dedicated band — **cols 4-7,
rows 3-4** — whose art is rock with a painted GRASS LIP (`out/rim_atlas_bands.png`),
and the course pins **fv = 0.0 at the crest** (p25 = p75 = 0.0), v growing DOWNWARD,
one full row per course (span med 1.00): the grass lip lands exactly on the weld line.
Course height med 4.44u p90 5.53. This explains playtest "pokey grass"/seam sparkle:
carried strips carry this painted lip in their top course; any weld that doesn't put
that fv=0 edge on the crest smears the lip mid-face.

**R4 — the jut budget + course quantization:** near-crest (drop ≤ 1.5u) outward
excursion beyond the crest line: med 0.73u, p90 5.68, p99 7.34, **max 7.81u** —
station-scale CONNECTED ledges are lawful; nothing floats. The drop band 1.5-2.5u is
EMPTY (zero verts within 8u plan of the crest): verts live ON course rows (the crest
row, then the next at ~4.4u) — vertical pitch is quantized.

**R5 — the dark-band bug, root-caused (flip-validated by the atlas crops):** row 10
IS inherently dark — mean luminance 67-73 vs mid-face 112-165; the art is deep-shadow
rock with the grass fringe at its high-v edge. Stock keeps it from reading as a dark
stripe three ways, all of which our mint violated:
1. **INTERMITTENT** — only 53% of stock's bottom-course tris wear row 10; the rest
   wear ordinary rows (3/9/5/6...). Ours retiled 100% — a solid dark ring.
2. **SHORTER** — stock's row-10 course is 3.71u med; ours minted 4.6u.
3. **PHASE** — stock samples v ∈ [row 10.12 → 11.09] (span 0.97, v grows downward,
   0.0% grow-with-height): shifted +0.12 rows past our [10 → 11], cropping the tile's
   dark top strip and grabbing the bright grass strip past the row boundary
   (lum ~80-90) at the weld. Our fringe ORIENTATION (high-v on the weld) was correct.

## VERDICT — the success criterion is met

R1 names the law and R2-R5 complete the numbers: **a rim-aware round is REGISTRABLE.**
The build shape it implies (for the next registration, not built here): mint the
plateau as the INTACT lattice and rasterize the crest ring onto the lattice graph —
then the strips' own top verts BECOME that rim row (1:1 vertex identification inside
the measured envelope: displacement ≤ ~2.4u plan, segments 4-6.5u, turns mostly <30°,
y wander ±0.7u) — never clip lattice tris against a curve. Keep the carried top course
welded with its fv=0 grass-lip edge on the crest; retile the foot at ~53% share /
3.7u / +0.12 v-phase. Everything upstream (strips, crease seams, level foot weld)
is already in-game proven and carries unchanged.
