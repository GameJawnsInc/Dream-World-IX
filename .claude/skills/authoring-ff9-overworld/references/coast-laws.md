# Coast laws — NAME INDEX ONLY (full statements live in memory)

> **This file is a THIN INDEX, not the laws.** The full statements + provenance live in memory
> **`project-ff9-overworld-coast-mosaic`** — read its `## LAW INDEX (read this first — full statements
> below in this file)` section FIRST, then search the quoted `→ "…"` phrase to jump to the named section.
> The memory file is canonical; if this index and the memory disagree, the memory wins. Every entry below
> quotes the law's NAME verbatim + the index's one-line gist (snapshot of the LAW INDEX as of 2026-07-11,
> 115 laws in 7 theme groups). Do not act on a gist — read the full statement.

## Contents

- [A. Component & mosaic foundations](#a-component--mosaic-foundations)
- [B. Verbatim transplant & component-edit laws](#b-verbatim-transplant--component-edit-laws)
- [C. Growth (RowInsert / cut_census / slides / fuse)](#c-growth-rowinsert--cut_census--slides--fuse)
- [D. Cliff-morph pillar](#d-cliff-morph-pillar)
- [E. Beach-morph & beach-mint](#e-beach-morph--beach-mint)
- [F. Strips / Wang / deformed-tile languages](#f-strips--wang--deformed-tile-languages)
- [G. Map-wide census verdicts & ceilings](#g-map-wide-census-verdicts--ceilings)

## A. Component & mosaic foundations

- **THE LAW (why continuous coastline is hard)** — a per-cell tiler/WFC over arbitrary tiles CANNOT make continuous LAND: independently-authored 3D cliffs never meet cleanly; only WATER seams blend freely → "★ RESUME — START FRESH ON COASTLINES".
- **SHALLOWS ARE SHORE-BOUND, COPY-ONLY (the water-ladder law)** — true shallow (sea2/sea1) is inseparable from a shore, never a gradient in open water; deep+mid open water is synthesizable → "WATER-LADDER COMPONENT STUDY".
- **THE RING LADDER** — bands ring an island in exact order Sea4→Sea5→Sea3→Sea1→Sea2→beach1→land; ring width tracks bathymetry, not a uniform offset → "COASTLINE COMPONENT SPEC".
- **CLIFF TEXTURE MAPPING RULE** — cliff rock = a specific atlas strip, V ∝ height, U ∝ shore position; land texture is baked per-mesh UVs → "COASTLINE COMPONENT SPEC".
- **TILE-SELECTION RULE** — cliff U = along-shore arc-length sawtooth wrapping the rock strip → "COASTLINE COMPONENT SPEC".
- **THE VERIFY-BEFORE-DEPLOY GATE** — build in memory; gate offline on cracks=0 / down-facing=0 / holes=0 / on-grain before any deploy → "NATIVE-GRASS ISLAND SYNTHESIS".
- **THE STAMP-BORDER RULE** — a meadow stamp's border may carry only plain-main or strip0 → "NATIVE-GRASS ISLAND SYNTHESIS" (v6).
- **THE BEACH RIBBON RULE** — beach1 = a one-quad foam ribbon (~4.35u); beach1 is the animated SWASH, not sand → "THE BEACH LANGUAGE".
- **BEACHES ARE BAY ARCS, NEVER RINGS (census)** — beaches live in sheltered water; the rocky lip is the default coast and terminates them → "THE REAL BEACH GRAMMAR".
- **THE ENGINE FOOT-WALK TABLE** — the foot-legal topograph set (full table in the memory) → "THE REAL BEACH GRAMMAR" (research round 2).
- **THE NO-WALLS LAW (superseded)** — v8 re-diagnosed the tears as MISSING closure, not wall culling → "v4 = THE RIBBON-WARP" (research round 4 / v8).
- **THE MOVEMENT-CACHE SHADOW** — sea tiles under walkable land shadow-block; waterline tiles must CONFORM to the coast → "v4 = THE RIBBON-WARP" (v5), full rule in memory `project-ff9-overworld-placement-rules`.
- **CURVE-VS-GRID WATER: STAIRCASE ON THE 4u LATTICE** — a smooth offset edge vs grid tiles ALWAYS overlaps or gaps; snap the collar's outer edge to lattice corners → "v4 = THE RIBBON-WARP" (v6).
- **KEY DONOR VERTS BY ORIGINAL INDEX, never by position** — position-merging scrambles every carried tile → "v4 = THE RIBBON-WARP".
- **ONE GLOBAL WINDING FLIP for carried geometry** — per-tri flipping is NEVER right for carried tris → "v4 = THE RIBBON-WARP" (v6).

## B. Verbatim transplant & component-edit laws

- **COMPONENTS ARE GEOMETRY+TEXTURE+TOPO UNITS** — texture substitution across component classes FAILS → "TWEAK 2 v6 FALSIFIED".
- **A BEACH SHRINK = THE WATERLINE MOVING, NOT THE APRON AMPUTATED** — the waterline sweeps inland to the cliff foot → "v9/v10" (tweak 2).
- **THE SLIDE-THE-ASSEMBLY LAW** — slide connector assemblies whole, never re-draw their boundaries → "v12" (tweak 2).
- **EVERY BEACH-END BOUNDARY IS A LOAD-BEARING WELD / WHERE-THE-CURL-BEGINS** — visible beach length is a TEXTURE phenomenon (the cap curl) → "v13/v14 endpoint iterations" (tweak 2).
- **NEVER HAND-TYPE GEOMETRY + THE WELD AUDIT** — real verts are off-lattice floats; the near-miss vertex census (`weld_audit`) is a permanent deploy gate → "v15/v16" (tweak 2).
- **THE ISLAND-TONGUE RULE (strips="auto")** — carry a neighbour strip only where the donor's OWN land reaches that border → "★ PRODUCTIZED INTO THE KIT" (world-transplant).
- **THE OPEN-OCEAN TARGET LAW (kit gate)** — a transplant target must be OPEN OCEAN; real targets refuse without allow_real_target → "✗✗ THE (5,2)/(6,2) INCIDENT".
- **THE NO-INTRODUCED-MISSES CENSUS LAW** — the census gate is "no INTRODUCED misses", not miss==0 → "INCREMENT 3" (slice-donor generalization).
- **NEW ENVELOPE LAW (fold bisect)** — on a concave shore the legal bow peak = the smallest sea2 conforming tri wedged between converging moved columns → "INCREMENT 3".
- **ZERO-END-SLOPE DISPLACEMENT LAW** — taper with sin²/smoothstep, keep displacement directions LOCAL, gate on turn-language → "BOW v2".
- **THE ARC-CLOSING SALIENCE LAW** — WIDTH CONTRAST is the visibility cue; within-band vertex moves (~±2.5u) are a FINE-ADJUSTMENT tool → "★ v3 IN-GAME VERDICT" (increment 4).
- **THE A/B TWEAK-SET LAW** — a grown build must carry the reference's EXACT tweak set plus the growth op → "A/B HYGIENE CATCH".
- **DIFFERENTIAL-VS-REFERENCE VERIFICATION** — proven by an offline BYTE DIFFERENTIAL against a reference deploy, not by eyeballing → "★ SPILL-CLIP PROVEN".
- **THE WALL LAW** — the degenerate-sliver filter must test TRUE 3D area, never plan area → "MULTI-CELL CARRY".
- **THE PREFAB-PARTS GATE** — a target cell's sidecar prefab must host a SUPERSET of the carried sub-mesh transforms → "MULTI-CELL CARRY".
- **IN-PLACE-FRAME + BOUNDS GATES** — an in-place morph's block-frame vert set must be byte-unchanged and nothing may leave the cell → "★ IN-PLACE CLIFF MORPHS" / "THE CARRY REALITY + `morph_in_place`".
- **THE CARRY REALITY** — (7,17) is FF9's ONLY fully-in-block beach → morph real cells IN PLACE (`--in-place`) → "★ THE SEAWARD NOSE MORPH".

## C. Growth (RowInsert / cut_census / slides / fuse)

- **THE OBJECT-ANCHOR LAW** — a donor's Object renders from the PREFAB at its original pose; its ground must net-zero displacement → "INCREMENT 6 v1".
- **THE FAMILY LAW** — topo-0 ground has MORE mains families than grass+meadow → "INCREMENT 6 v1".
- **THE PAINTED-WASH COMPONENT LAW** — a painted wash is a COMPONENT; NO per-cell fill can continue paint; census risk `crosses-wash` → "v6 in-game" (increment 6).
- **THE FILL LAW (+ the STRETCH LAW / SIDE RULE steps)** — inside a painted-wash family, CONTINUE the local material → "v3–v6" (increment 6).
- **MIRROR-AFFINE UV LAW** — mirror-affine fill inheritance is valid only where the real mapping IS plan-affine → "★★ v1 IN-GAME" (increment 5).
- **THE WATER-FILL LAW** — Wang strips translate-CLONE (directional); pure quadrant bands + the sand apron keep the mirror → "★★★ 3-CUT GROWTH".
- **THE STRICT SHORE LAW** — a cut may not cross/touch sea1/sea2 (census `touches-shallows`) → "✗→law THE 3-CUT BUILD'S SEA".
- **THE SLACK LAW** — growth needs water slack on the shifted frame side → "THE FIRST IN-GAME MULTI-CUT".
- **THE STRIP-ACROSS-LINE law** — a strip with an E/W deep edge = a transition band PARALLEL to the cut; the clone duplicates it → "★ THE STRIP-ACROSS-LINE law".
- **EMPTY-CELL LAWS: `gap-vacation` / `spills-into-empty` (+ the Composition law)** — a region cut's shift is global but the fill is at-the-line only; a boundary is fillable IFF pure open water → "REGION GROWTH CUTS" / "MULTI-BOUNDARY SEAM EXTRUSION" / "★ THE SPILL-CLIP LAW".
- **THE SPILL-CLIP LAW** — spilled columns CLIP at the cell's fixed border under a census-certified water-column BUDGET → "★ THE SPILL-CLIP LAW".
- **THE RELIEF LAW** — a cut's fill is a seam-profile extrusion; `MAX_CUT_RELIEF=6.0`; high relief is a COMPONENT — cut around, never through → "REGION-GROWTH ROUND VERDICT".
- **THE INTERIOR BORDER-T WELD LAW (+ THE CORNER-SLIVER WELD CLUSTER)** — border weld pairs judge as union-find CLUSTERS → "MULTI-BOUNDARY SEAM EXTRUSION" + "Z-AXIS RowInsert".
- **THE EXACT-ROTATION ADAPTER** — never transpose the fill vocabulary by hand; z-cuts delegate to the proven x-RowInsert → "Z-AXIS RowInsert".
- **THE HAIRLINE LAW** — drop only true collinear clip degenerates; gates: the clip-drop LEDGER + the border MICRO-CENSUS → "Z-AXIS RowInsert" (the −352 z-slide playtest).
- **THE LATTICE-SEAM LAW** — an off-lattice on-line vert in an open-water part disqualifies a cut (census `conforming-on-line`) → "Z-AXIS RowInsert" (the −352 z-slide playtest).
- **THE BAKED-TERRAIN LAW** — topo 17/38/49 highland = hand-painted MURALS, NO tile language; census risk `crosses-baked-terrain` → "THE BAKED-TERRAIN LAW".
- **THE FUSE LAW** — LAND never knits (coastlines are components); the WATER knits; every shared layout border certifies row-by-row from `frame_profile` → "★ THE FUSE LAW".
- **THE `cut_census` RISK SET (the component laws as gates)** — straddlers · `crosses-beach` · `beach-end-on-line` · `crosses-wash` · `displaces-object-ground` · `touches-shallows` · `crosses-relief` · `conforming-on-line` · `crosses-baked-terrain` · `gap-vacation`/spill budgets/`boundary_fills` → "v6 in-game" (increment 6) + the per-law entries above.

## D. Cliff-morph pillar

- **THE COLUMN QUANTIZATION LAW** — exactly one 64px rock tile per wall column, the strip = exactly 4 tiles; the U-ramp is DETERMINISTIC → "THE COAST-MORPH PILLAR OPENED" (study facts).
- **THE ±2.5u CONFORMING-BOW CEILING** — the envelope is a GEOMETRIC ceiling, rediscovered by the fold gate → "RUNG 1" (the 2.5u conforming bump).
- **DROP-DON'T-DRAG** — every tri touching a moved vert drops + re-fills natively → "RUNG 2" (the structural headland).
- **WATER UVs NEVER DRAG (and never clamp)** — moved water re-evaluates through its own tile map; ring fills are ZIP strips, UNCLAMPED → "PLAYTEST ROUND 1" (coast-morph).
- **THE WATER DENSITY GATE (permanent)** — emitted water uv-from-world singular values must sit inside the real dropped tiles' envelope → "PLAYTEST ROUND 1" (coast-morph).
- **THE CRACK GATE + THE GRAIN GATE** — a fill's once-edges must equal the region polygon's segments exactly; max fill edge ≤6.6u → "RUNG 2" (the structural headland).
- **THE BAY ASYMMETRY LAWS** — the bay wedge consumes GRASS; a land component within reach = offline refusal; the sea ledger is SIGNED → "★ THE BAY MORPH".
- **THE REFINED-CREASE VOCABULARY** — real walls carry half-step-U crease fan verts; column quantization holds through the fan → "★ COMPOSED MORPHS" (cliff_lobes).
- **THE REACH GATE** — a lobe's footprint may touch ONLY sea4 → "★ COMPOSED MORPHS".
- **FREE EQUAL-ARC RESAMPLE** — interior wall columns place freely at equal new-arc; total ≡ ncols (mod 4) → "★ COMPOSED MORPHS".
- **THE RING-EXTENSION LADDER** — a sub-grain bay-rim corridor is unlawful; consume one more grass ring and rebuild → "★ COMPOSED MORPHS".
- **THE BAKED-TERRAIN REFUSAL (structural morphs)** — mural-topped donors have NO fill language: bow-only → "★ MORPHS ON THE LIVE CONTINENT".
- **THE CENSUS DISPLACEMENT INVERSE** — a pre-existing donor hole translates with a morphed shore; `VertexDisplace.census_inverse` → "★ MORPHS ON THE LIVE CONTINENT".
- **THE LOCAL ENVELOPE / WINDOW SLIDER** — the fold precheck IS the envelope measure → "★ MORPHS ON THE LIVE CONTINENT".
- **THE LIP-ROW VOCABULARY** — a face's top edge pins to a painted texel row KEYED BY THE TOP FAMILY → "★ THE CLIFF-FACE TRANSITION LAWS".
- **THE CONFORMING-CREASE LAW** — 99% of lip grass is crease-conforming deformed geometry; NO edge-tile class, NO blend family, NO bevel → "★ THE CLIFF-FACE TRANSITION LAWS".
- **THE FREE-BASE LAW** — ZERO face base edges map-wide land on walkable terrain; bases terminate FREE at/below the waterline → "★ THE CLIFF-FACE TRANSITION LAWS".
- **THE CLEARANCE GATE (the cliff shape law is PINCH, not class)** — cliffs are CLASS-FREE; the real hazard = the pushed outline pinching (≥4u gate) → "★ THE CLEARANCE GATE".
- **THE BUILDERS ARE THE ORACLE (+ REFUSAL-STEERED search)** — the scanner probes the real morph fns and certifies via a `morph_in_place` dry-run; zero law re-implementation → "★ THE COAST WINDOW SCANNER".

## E. Beach-morph & beach-mint

- **THE RIBBON GATE** — post-move swash width must stay in the real envelope → "▶ THE BEACH FRONTIER OPENS".
- **THE LADDER-TAPER LAW + THE BAND GATE** — a shore morph moves ALL bands in proportion; no band below 60% of its verbatim width → "PLAYTEST ROUND 2" (beach bow).
- **WATER NEVER DRAGS IS UNIVERSAL** — foam drags (edge-anchored), wash re-evaluates → "PLAYTEST ROUND 1" (beach bow) / "LAW SUPERSEDED".
- **THE REFINED WATER-MECHANISM LAW + THE STRAIN GATE** — water tolerates SMALL strain, never SHARP strain, never EXTRAPOLATED re-evaluation → "PLAYTEST ROUND 3" (beach bow).
- **THE HUG LAW** — within ONE beach the swash ribbon is near-constant; the assembly slides as a unit → "THE THREE AESTHETIC LAWS".
- **THE SHAPE-CLASS LAW** — a beach's convexity class is INHERITED from the coast it aprons; NEVER cross the chord toward the opposite class → "THE THREE AESTHETIC LAWS".
- **THE CAP-TAPER LAW** — the two TERMINAL foam columns carry the separate end-cap taper band, not run tiles → "THE THREE AESTHETIC LAWS".
- **THE ABSOLUTE WASH ENVELOPE** — the wash re-lays width-driven within the ABSOLUTE 2.4–8.4u envelope; ratio-to-old is a FALSE law → "STRUCTURAL BEACH, STEP 2".
- **THE EDGE-SHADE FIELD** — strip edge states are Wang SHADES that must AGREE across tiles; the field is SHAPE DATA read from the donor → "STRUCTURAL BEACH, STEP 1" / "STEP 2".
- **SEA2 CONFORMING = AFFINE CONTINUATION** — waterline-conforming wash tiles are the cell's quadrant map evaluated at the conforming verts → "STRUCTURAL BEACH, STEP 1".
- **THE DEFINITIVE SEAWARD RULE** — seaward = minus the mean per-vert wl→nearest-seam direction → "★ THE SEAWARD NOSE MORPH".
- **THE ASYMMETRIC CLASS ENVELOPE** — pockets run to −46% of chord length, TRUE noses ≤ +19% → "★ THE SEAWARD NOSE MORPH".
- **THE SAND-RIBBON LAW (Path B falsified)** — the sand band is a single-row chain-pinned RIBBON; NO lawful widened-band fill exists ⇒ the growth verb is the FULL-ASSEMBLY SLIDE → "PATH B — RESOLVED BY FALSIFICATION".
- **THE GRADED-LADDER RE-LAY (+ the SLOPE GATE)** — a full-row slide re-lays the whole ladder; block-frame reconcile is a lawful break → "THE FULL-ASSEMBLY SLIDE".
- **THE BAND-GATE VALLEY** — fractional-row shifts can't re-band (a real hole, not a bug); hard cap −6 → "THE FULL-ASSEMBLY SLIDE".
- **THE T-VERTEX LAW + THE T-VERTEX GATE** — translated chains mint rasterization pinholes; the float32-scale scan is the honest oracle → "THE FULL-ASSEMBLY SLIDE".
- **THE GRASS-PIN LAW (seaward slide)** — grass never moves; the band translates verbatim; the vacated strip re-fills with NATIVE grass → "THE SEAWARD SLIDE".
- **THE U-STRIP + per-band v pins (sand)** — the sand band lives at fixed atlas u-rects P/Q with PER-BAND v-pin constants → "PATH A — THE SAND-BAND EDGE TABLE".
- **THE ONE-SHADE LAW** — sand's 3 lattice edges are ONE mutual shade class; caps pin outward BECAUSE the cap band is a gradient → "PATH A — THE SAND-BAND EDGE TABLE".
- **THE CLOSURE FREEZE + the RECT FLIP** — every non-internal sand edge must be a port or chain edge; the identity rebuild re-derives by deterministic P↔Q flip → "PATH A — THE SAND-BAND EDGE TABLE".
- **THE TAPER ASYMMETRY + THE SLOT LAW (end caps)** — only the BL cap window FADES; slots TRANSPORT, mint defaults to BL; the cap round-trip IS the completeness proof → "THE END-CAP LAWS".
- **THE ASSEMBLY BOUNDARY GATE (mint)** — every emitted once-edge must sit on pinned verts; the donor's pinned-vert boundary preserved exactly → "BEACH-MINT RUNG 1".
- **THE UNION CRACK GATE (rung 2a)** — once-edges of the dropped union == the emitted union when the land chain synthesizes; berm CLIPPING is lawful on ANY painted berm → "BEACH-MINT RUNG 2a".
- **THE BERM LAW** — beach berms are topo-0 ONLY → "THE RUNG-2 WINDOW STUDY".
- **THE LATTICE ADJACENCY LAW** — lawful band pairs only (full table in the memory): sea3 NEVER touches sea4 anywhere; {1,5} is real → "THE RUNG-2 WINDOW STUDY".
- **BEACHES NEVER SHARE VERTS** — min separation 4.06u (the grass-tongue separator) → "THE RUNG-2 WINDOW STUDY".
- **THE EXACT FOOTPRINT-CUT (rung 3)** — the assembly is ONE simple polygon; kept = the exact tri-minus-polygon arrangement (BSP leaves T-points at in-tri footprint corners) → "BEACH-MINT RUNG 3".
- **THE REFLEX CAP DIAGONAL** — a pinned real crease-base pair makes a cap quad reflex; only the reflex-vertex diagonal is interior, the emitter's split must match → "BEACH-MINT RUNG 3".
- **THE EDGE-LEVEL RING TRIGGER** — the ring re-band fires on a sea3 tile sharing a geometric EDGE with minted foam; introduced-only → "BEACH-MINT RUNG 3".
- **THE FOAM-COLUMN ENVELOPE + THE COLUMN-SCALE READ** — real foam run columns span 0.92–6.27u along-shore (map-wide census); short columns are real grammar, but an ALL-minimum-column beach reads dense/squished (in-game) — pick windows allowing ~3-4u columns → "BEACH-MINT RUNG 3".
- **CAP-END GEOMETRY IS TRANSPORTED LAW** — real crease-base cap pins bypass the synth band/slope envelopes → "BEACH-MINT RUNG 3".

## F. Strips / Wang / deformed-tile languages

- **THE LEARNED WANG TABLE** — a real strip tile is a PURE function of which neighbours sit deeper; NEVER derive the table through synthesis conventions → "★ BAND-CROSSING RE-WANG, STEP 1".
- **SEA3'S LANGUAGE** — quadrant mains with its OWN v-split, placed over DIHEDRAL-8 (a rotation-4 fit misses half) → "STRUCTURAL BEACH, STEP 2" ("SEA3'S LANGUAGE LEARNED").
- **COASTAL SEA4 IS DIHEDRAL-8** — near-shore sea4 mains use mirrored placements → "THE FULL-ASSEMBLY SLIDE".
- **{sea1,sea5} ADJACENCY IS REAL** — a sea1 deep edge lawfully fronts sea5 directly → "THE FULL-ASSEMBLY SLIDE" / "THE ONE-CELL BAND-CONVERSION".
- **THE STRIP-FAMILY CLOSURE (census)** — `strips_rebuild` re-derives every decodable sea1+sea5 cell (~7% inset-rect residual stays verbatim) → "★ SEA5 EMISSION".
- **THE FOAM LANGUAGE** — run tile repeating per 4u along-shore column; the end-cap band is a SEPARATE texture band → "STRUCTURAL BEACH, STEP 1" + THE CAP-TAPER LAW.
- **THE DEFORMED-TILE RECT LAW** — a strip tile's uv map = a snap-rect ASSIGNED TO ITS CORNER VERTS independent of geometric deformation, + positional edge-lerps on inserted verts → "THE DEFORMED-TILE RECT LAW".
- **THE ROW-BOUNDARY GROUPING GUARD** — uv-equal-edge union-find must refuse merges exceeding one ≤2×≤2 rect → "THE DEFORMED-TILE RECT LAW".
- **THE DISCRETE ROLE-DECODE** — every strip group decodes to EXACTLY ONE (v-row, dihedral-8 orientation) via nearest-cell-corner roles → "THE ONE-CELL BAND-CONVERSION".
- **THE PER-BLOCK FLOAT DIALECT** — emission floats are byte-read from the block's own decoded groups, never typed; MIXED-dialect blocks refuse → "THE ONE-CELL BAND-CONVERSION".
- **THE SHADE-AGREEMENT LAW** — a strip tile's deep-claim is TWO-SIDED within a band and EQUALS the depth fact against a different band → "THE ONE-CELL BAND-CONVERSION".
- **THE CASCADE REFUSAL** — a conversion that would EMPTY a neighbour's edge-set refuses; also refused: open ocean, strip-band sources, frame-ring cells → "THE ONE-CELL BAND-CONVERSION".

## G. Map-wide census verdicts & ceilings

- **Growth-line censuses** — (9,17): ZERO usable growth lines; (7,17): exactly ONE clean line; world sweep: 56 donors with ≥2 clean x-lines → "v6 in-game" (the `cut_census` productization).
- **THE GROWTH CEILING** — single-donor single-axis = 2 cuts / +8u under the strict shore law; the ceiling is set by the COMPONENT laws → "✗→law THE 3-CUT BUILD'S SEA" / "STEP-2 PAYOFF SCAN".
- **The multi-block landmass screen** — NO verbatim-clean 2-block landmass exists in FF9 except (9,5)+2×3; its land is un-growable on either axis → "MULTI-CELL CARRY" (SCREENING FINDING) / "Z-AXIS RowInsert" (z-census).
- **The second-donor screen** — (9,5)'s clean-small-island property does NOT generalize; best alternative (10,17)+2×2 → "SECOND-DONOR SCREEN" / "★ THE SPILL-CLIP LAW".
- **The morph catalog** — 324 windows map-wide; beach-reshape = exactly 1 lawful window map-wide, (7,17) → "★ THE SCANNER'S CLAIMS PROVEN IN-GAME".
- **Slide ceilings** — landward column slide: exactly ONE lawful window map-wide ((7,17)); seaward free-form ceilings per donor → "THE FULL-ASSEMBLY SLIDE" (SCANNER-WIRED) / "THE SEAWARD SLIDE".
- **Virgin-window censuses** — the post-band-convert WIDENED census: the whole map holds 3 windows, winner (9,17) run (153..155,−282) — don't re-sweep; tri-level: the separation law halves (9,17)/(7,17)'s arcs, (3,13) NE refuses on the slope law (tall bank) — THE MAP IS FULL for real-scale virgin beaches; mint on kit-built shores → "THE RUNG-2 WINDOW STUDY" / "THE WIDENED VIRGIN-WINDOW CENSUS" / "BEACH-MINT RUNG 3".
