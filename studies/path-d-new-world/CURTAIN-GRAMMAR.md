# CURTAIN GRAMMAR — how stock SEALS a surface edge to lower ground (questions registered BEFORE the instrument ran)

2026-08-01. The walkability round closed with one open defect, owner-confirmed twice
(LAWN-CLIP-PREDICTION.md, "THE V-SHORE GAP, measured"): the carried wall HOVERS
1.5-3.2u over the descending shore at the two coast crossings — east (448.8,−507.8),
11 once-edges / 22u; west (382.4,−511.6). Mechanism known: `fits_bench` clips the
apron at the bench GRASS edge, so the carried skirt terminates mid-air exactly where
the bench shore descends below the lawn datum. The owner: *"i have a feeling it may
be complicated"* — and the site is where four systems meet (the carried wall, the
bench coast band, the sea sheets, the block-7 border).

Per the authorship law (GROUND-JUNCTION-SYNTHESIS.md: THE DEFECT FOLLOWS THE
AUTHORSHIP, 12/13) no fix is built before its grammar is measured. This seventh wall
study decodes the class no prior study asked about: **what stock ships where a
raised surface's edge sits over lower ground** — the sealing vocabulary — and then
classifies OUR two sites inside that vocabulary.

## What is already in hand (not re-derived here)

- **THE TAPER LAW** (ENDPOINT-GRAMMAR.md): 42/42 real wall crest endpoints taper to
  ground; a wall that "just stops" does not exist in stock. But that census measured
  walls ending ON GROUND — none of its endpoints was at a coast.
- **THE FREE-BASE LAW** (coast-mosaic, pillar D — measured on the COASTAL cliff
  class): ZERO face base edges map-wide land on walkable terrain; bases terminate
  FREE at/below the waterline. If wall-meets-coast resolves to this class, the fix
  is a descent, not a seal.
- **The blob curtain signature** (found during the underlay build, full_skirt.py
  ~1511): the carried forest blob's rim is closed by plan-degenerate vertical faces
  — every plan edge there has 3 owners, so the rim has NO once-edges. Donor bytes;
  the in-hand exemplar of a stock seal.
- **The 40° curtain regime** (GROUND-JUNCTION-SYNTHESIS, S1 surviving form): stock
  ground's uv vocabulary breaks at 40° — steeper faces leave the plan-budget rule.
- **THE BAND-CONTINUATION LAW** (the base-tile study): a wall's bottom band is the
  column's uv continuation, 100% seam-continuous — the candidate uv rule for a
  curtain.

## Questions — registered before running

**C1 — THE CURTAIN CENSUS (does a general sealing class exist?).** Across stock
disc-1 terrain blocks: every near-vertical face group (|geometric ny| ≤ ~0.2, i.e.
past the 40° break well into the curtain regime) OUTSIDE the two decoded wall
classes (topo-49 crest-seeded walls; the topo-58 coastal cliff strip). Per group:
what sits ABOVE its top edge and BELOW its bottom edge (surface class, topograph);
its drop height; its plan-owner signature (the blob's 3-owners-per-plan-edge — is
that the class invariant?); its texture family and topograph; its frequency by
context (forest rim / terrace edge / riverbank / plateau lip / shore). The census
must answer: **is "curtain" one class with one construction, or several?**

**C2 — THE CURTAIN UV RULE (what a mint would have to emit).** On the donor
exemplar (the (15,14) forest blob rim) and every C1 family: is the curtain's uv the
band-continuation of the surface above (THE BAND-CONTINUATION LAW's prediction), a
dedicated atlas strip (the coastal cliff's V-corner-role pattern), or the surface
BELOW's continuation? Plus the v-orientation (grows downward?), the tile rows used,
and whether the top edge pins to a painted lip row (the cliff-lip texel-row law's
analogue).

**C3 — WALL-MEETS-COAST (the site class our V-notch claims to be).** Census every
stock site where an interior rock mass (topo 49/50, the wall body class) comes
within ~8u plan of a sea/beach sheet. At each: does the rock BODY descend below the
waterline (THE FREE-BASE LAW generalizing to interior walls), does GROUND always
wrap the foot (the apron never ends before the rock does), or does a curtain seal
the junction? The frequency of each resolution, with drop heights and the ground
class present at the junction. **This is the discriminant question**: it decides
whether our sites are curtain sites at all, or apron-extension sites, or
descend-into-the-sea sites.

**C4 — OUR TWO SITES, MEASURED (the patient's anatomy before the prescription).**
On the deployed bench bytes: at each hover cluster, the exact carried boundary
chain (its verts, heights, and owner tris), the bench surface below (class,
topograph, descent profile from the lawn datum to the waterline), the plan gap
between the carried edge and the nearest bench once-edge, and the block-7 border's
position relative to the cluster. Output: a per-site section view + plan render.
Then the classification: for each site, which C3 resolution the analogous stock
configuration uses.

## Alternatives held on the table (the round chooses AFTER the study)

1. **THE CURTAIN MINT** — emit the donor's own sealing idiom along the clipped
   boundary (only registrable if C1/C2 name one construction and C3 says stock
   seals here).
2. **THE APRON EXTENSION** — relax `fits_bench` past the grass edge so the donor's
   own ground carries onto the coast band (only if C3 says ground always wraps; note
   it RELOCATES the junction to the waterline rather than removing it unless the
   carried apron conforms to the descending shore).
3. **THE COAST-NAV CLIFF** — the bench's own shore idiom stamped at the crossings
   (the coast-mosaic machinery; only if C3 resolves wall-meets-coast to the coastal
   cliff class).
4. **THE FREE DESCENT** — carry/extend the wall body down below the waterline per
   THE FREE-BASE LAW (only if C3 finds interior rock doing exactly that at coasts).

## Method

Read-only vs stock disc-1 (`ff9mapkit.world.extract`: `list_blocks` / `read_block`
/ `decode_id`, terrain part) + the deployed bench bytes for C4 (`walk_sim.load_world`).
Multi-agent: parallel instruments for C1-C4, each load-bearing finding adversarially
re-measured by a different method before it is believed (the synthesis study's
discipline — 5 of 6 laws there died under their skeptic). Instruments →
`studies/overworld-topography/curtain_*.py` + the C4 probe beside this file;
artifacts → `out/`. Nothing deploys; the live bench stays as the owner last saw it.

## Success criterion

C1/C2 name the sealing construction(s) with numbers, C3 resolves wall-meets-coast
to a dominant idiom, and C4 classifies both hover sites → the V-shore round becomes
registrable with ONE named fix class and a falsifiable prediction. It FAILS if the
census finds no consistent sealing grammar — in which case the round's default
falls to the smallest-authorship alternative (the apron extension, which mints no
new surface class) and says so honestly.

---

# FINDINGS (2026-08-01 — 8 agents: 4 instruments + 4 independent skeptics, wf_b0a8c603)

Instruments: `overworld-topography/curtain_census.py` (+ skeptic `curtain_skeptic_recheck*.py`),
`curtain_uv.py` (+ `curtain_skeptic.py`), `curtain_coast_sites.py` (+ `curtain_c3_recheck.py`,
`curtain_c3_spotread.py`), `path-d-new-world/probe_vshore_anatomy.py` (+ `skeptic_vshore_c4.py`).
Skeptic score: 13 CONFIRMED / 9 CORRECTED / 1 REFUTED across 23 claims — corrections
recorded below as first-class. Read-only; the live bench is byte-unchanged (the
registered probe re-ran byte-identical during C4).

## C1 — THE CURTAIN IS ONE CONSTRUCTION, and it is general

Of 5,703 near-vertical stock terrain tris (260 blocks), outside the two decoded wall
classes sit **159 curtain components (2,703 tris): fully plan-degenerate, 97%
zero-once-edged, topograph CONTINUING the surface above (94%), drop med 2.44u p90
3.62 max 6.58**. The registered "3 owners per plan edge" was the special case — the
class invariant is **NEVER-ONCE** (owner mode is 4: surface + both quad tris +
ground). Contexts: raised-blob rims (topo-38, forest 36/37) sealed onto plains,
plateau tops, and the shore (12 comps touch topo-58 by shared verts). Sloped
near-vertical faces are NOT curtains — they are scarp-sheet self-steepenings (topo
59/62) and gorge walls. Corrected: rock-49-above curtains are 3-4 comps, not 10.

## C2 — THE CURTAIN UV RULE: a dedicated PINNED strip; band-continuation REFUTED

**THE BAND-CONTINUATION LAW does not govern curtains.** The curtain's uv is
discontinuous with BOTH neighbors at ~0/1490 shared verts. Per surface family, a
dedicated atlas strip with **PINNED v (stretch over the drop — no dv/drop rate
exists)**:
- **forest 37 + forest-on-plateau 36**: u 115-241 texels, v_top **930** / v_bot
  **961** pinned (719/725 + 424/429 tris exact); u advances ~15 texels/u, station
  anchors {115,179,241}, one ~64-texel tile per ~4.1u run; TRUE inter-quad seams
  are only 53% u-continuous (the 77% figure counted quad diagonals) — statistical,
  not a deterministic unwrap;
- **topo-38 (desert veg)**: own two-row strip u 738-869, v rows 548/580/611, drops
  to 3.42u;
- topo-59 is the one impure family (forest strip + rock rows mixed).
Construction: vertical outward-wound quads (723/725), topograph/raw-id = the
surface family's own (forest curtains carry the surface's raw id 1940), top edge
welded to the rim verts, **bottom verts at the same plan positions welded INTO the
ground sheet (16/16 on the donor, including border-adjacent)**. Stock ships **ZERO
open forest rims** (371 curtain-sealed / 135 direct-weld / 137 border / 0 once).
⚠ Domain honesty (skeptic): the forest strip's shipped drop domain is
**1.668-2.863u** — our site drops (0.5-3.25u) overhang it at BOTH ends; the
38-family two-row strip is the tall-drop precedent.

## C3 — WALL-MEETS-COAST: the seal is the resolution; our defect class has NO stock instance

The load-bearing result, threshold-free and positive-control-calibrated:
**hover-over-ground = ZERO in stock** (0/2,928 free edges across all 122 coastal
blocks; a synthetic floating slab control IS detected). Stock's coast vocabulary:
ramp, seal, waterline free-base, object-part seam — no hovering member. At the
~80 physical wall-meets-coast junctions:
- a **seal is present at 90% of sites** (the skeptic refuted the instrument's
  55/38/7/1 partition — wrap-vs-seal is a continuum and wrap-WITHOUT-seal is 2%);
- the seal is **the coastal-cliff construction**: majority **topo-58** near-vertical
  faces sealing a foot-legal WALKABLE lip (90%), **seal bottom at the waterline
  (median 0.00)**, sealed drop med ~3.0u;
- **rock never dives below the water: 0/311 sites** — the rock hem stops med 3.56u
  up and the 58-class curtain carries the last stretch down. FREE DESCENT has zero
  stock precedent.
- Free hems AT/below the waterline are lawful (2,499 of 2,928 free edges); one
  genuine elevated hover-over-open-SEA location exists map-wide (block (13,17),
  5.8u), where the terrain sheet ends entirely; stock also ships 31 void-bounding
  topo-58 hems — but never over ground.

## C4 — THE PATIENT: three sites, not two; every hover edge is carried authorship

18 of the 19 registered east "hover edges" were **block-border seam phantoms**
(probe_vshore_gap counts per block; a border edge has an owner in EACH block). The
true open boundary, verified at 2dp AND 4dp rounding:
- **EAST (448,−506)**: ONE 4.0u edge in the x=448 plane at y=3.149, dropping
  **3.149u to open Sea4 (y=0)** — and it is the BOTTOM of an existing 0.051u
  plan-degenerate mini-curtain (ny=0.000, mapid 1940, topo 37 — the blob idiom,
  clipped). The fix here EXTENDS an existing curtain downward.
- **WEST (382,−512)**: ONE connected **~14.6u** carried rim (W1+E_a+E_b+W3, ny
  0.58-1.0, no curtain exists) hanging 0.65-2.32u over the build's OWN lawn/4078
  underlay, straddling BOTH border planes (x=384, z=−512), **plus W2** — 3.27u of
  carried-lawn rim hanging a full **3.2u over Sea4** at a 4.5u sea inlet. ~17.8u
  total. (The instrument's single-block scan-vocabulary hover test under-detected;
  the skeptic's union-of-blocks render-vocabulary test is the honest one.)
- **SOUTH (448,−538)** — the registration MISSED it: 5 edges/16.93u on the same
  x=448 plane — a 4.0u chain 2.79-3.25u over Sea4 (one owner is the 4078
  underlay's OWN rim) + a 12.93u hem chain 0.51-0.75u over own lawn/underlay.
- Residual outside the sites: **14 sub-1u hem edges** (gaps 0.57-0.95, x 412-438,
  z −544..−556) + a rounding-unstable 1.56u skirt edge + **one 3.46u border-rim
  edge on x=384 with a 2.32u drop** (same class as the west rim, contiguous).
- **Authorship: 27/27 hover edges are carried; the pristine bench has ZERO** — its
  100 non-rim once-edges have NOTHING below and midpoint y exactly 0.0: the bench's
  own free edges terminate AT the water (the free-base idiom, matching C3).
- Shore mechanism at east: the bench coast is **Sea4-under-land** (topo-58 strip
  descends then the sheet ends FREE over sea with no waterline crossing) — which is
  why the slits open onto water.
- ⚠ Engineering note (skeptic): near-duplicate verts in the carried skirt make edge
  identity rounding-unstable NW of west — **seal code must key on geometry, not
  rounded vert equality**.

## VERDICT — the success criterion is MET; the fix class is chosen by the grammar

The construction is nameable (C1+C2), the discriminant resolved (C3: stock SEALS —
never hovers, never wraps-instead, never dives), and the sites are classified (C4).
**The alternatives fall away by measurement**: APRON EXTENSION dies on C3
(wrap-without-seal is a 2% minority and the bench shore is Sea4-under-land — there
is no shore surface to conform more ground onto); FREE DESCENT dies on C3 (zero
precedent); the bench-side COAST-NAV CLIFF stamp is subsumed — stock's own seal at
this junction IS the cliff-class curtain construction.

**The registrable round: THE CURTAIN SEAL** — close every true open rim with the
stock curtain construction, per-site bottom target:
1. over-water rims (east, W2, south-sea): curtain from the rim down to the
   waterline y=0, bottom terminating FREE at the water (C3's median-0.00 idiom =
   the pristine bench's own free-edge envelope);
2. over-own-ground rims (west rim, south hem, the x=384 border edge, the sub-1u
   hems): curtain from the rim down, bottom verts welded INTO the sheet below at
   the same plan positions (C2's 16/16 donor rule);
with topograph/raw-id continuing the surface above, outward winding, pinned-strip
uv per the surface family (drops ≥~1.7u: the family strip; drops beyond 2.86u and
sub-1u hems overhang shipped forest-strip domain — the round's registration must
declare which strip serves each drop and score it as a falsifiable prediction).
Walk safety: a vertical curtain has geometric ny=0 → the engine's ny>0.1 full-scan
filter already skips it (WALK-QUERY-DECODE), and the camera sky-cast hits the
surface above first in carried-first buffer order — but BOTH must be gated, not
assumed.
