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
