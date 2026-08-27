# Overworld interior topography — the census study

The regenerable survey behind the **interior landmass** knowledge base (how FF9 builds
mountains, plateaus, forests, deserts, snowfields, and rivers — everything inland of the
shore vocabulary). It reads your own FF9 install; **no game bytes live in this repo** —
the `out/` artifacts regenerate in ~2 minutes:

```
py studies/overworld-topography/census.py        # artifacts -> studies/overworld-topography/out/
```

## Headline findings (disc 1, all 260 land blocks — 2026-07-12)

- **THE TERRACE LAW.** Walkable land lives in TWO altitude worlds: the lowlands (2–8u,
  peak 3–4u) and the plateaus (26–32u), with a near-empty gap at 18–26u — the gap is
  topo-49 rock. Mid heights (10–17u) are sparse terrace steps (the Forgotten Continent's
  canyon tiers, topo 45/46, and topo-13 shelves at ~17u).
- **LOOK FAMILIES ≪ TOPO IDS.** ~37 in-use topograph ids collapse into ~9 tile families:
  grass (0/1/2/3/10–13/42/59), dirt-desert (16–23/41), scrub (4/5/6), forest (36/37),
  canyon red-rock (45/46), snow (27/28), rock (49, 7, 62), shore sand (31/32/33), lip (58).
  Ids within a family are GAMEPLAY variants (encounter regions/events), not looks — e.g.
  plateau grass 10/11/12 renders with the same tiles as lowland grass 0.
- **FORESTS ARE GEOMETRY + TILES, fully lattice-native**: topo 36 (high, 20–32u) / 37
  (lowland), dark canopy tiles, the standard ~4.2u grid with ~1.9–2.3u per-tri height
  jitter (the "puffy" canopy), slopes to 90° yet FOOT-LEGAL — you walk into them.
- **RIVERS/FALLS/STREAMS ARE PARTS, like beaches**: tiny animated water-surface sub-meshes
  (`river`/`riverjoint` topo 48, `falls` topo 50, `stream` topo 51; 1–51 tris each) laid
  over a channel carved in the Terrain part. A falls sheet at block (5,15) spans y 15.2→26
  — it is the seam between the two altitude worlds. Also present: `volcanocrater`/
  `volcanolava` at (7,1)/(8,1) — Gulug.
- Dominant class map-wide: **topo 49 mountain rock** (27.8k tris, 164 of 260 blocks,
  median slope 51°, foot-illegal) — mountains are the walls that partition the walkable
  world. Top adjacencies: 0|49 (grass meets rock) and 10|49 (plateau meets rock).
- `topo_map_true.png` colors every 4u cell by its topograph's real mean atlas color —
  it reproduces the painted world map's reading at a glance (good sanity check that the
  census semantics are right).

## The forest arc (★ in-game proven 2026-07-12)

Two synthesis attempts were falsified in-game (per-tri tile picks, then dome+jitter+tiles —
"a sloppy triangular mess"); the UV studies (`forest_uv_language.py`, `forest_uv_components.py`)
showed canopy texture is hand-authored (28–35 non-affine UV patches, seams everywhere yet
invisible) ⇒ **THE CANOPY CARRY LAW: carry a real canopy blob whole, never synthesize it.**
`forest_blob_inventory.py` lists the carryable blobs ((15,15)'s 132-tri grass-bounded blob =
the clean donor); `forest_carry.py` is the proven build: lattice hole + chain-ordered rings +
greedy-bridge zip annulus + exact-float welds + **THE CANOPY STEP LAW** (wall faces are vertical
curtains; every rise gated ≤ 2.2u under the engine's 2.34375u step ceiling — stock forests
genuinely block at their own 2.4u+ segments). Proven on the reclaimed bench pad at cell (3,14)
(`world-reclaim --profile island --seg 16`).

## The canvas (★ IN-GAME PROVEN 2026-07-12 — "renders fully, the whole cliff loop is walkable, meadows look good")

The census exposed the blocker for every further interior rung: **no forest/hill-scale
grass exists anywhere we control** — the archipelago's grass pockets top out at ~16×8u,
lowland forest (topo 37) borders ONLY grass map-wide, and stock FF9 has no transplantable
big grass island. The fix is **island E, the from-scratch grassland canvas**: a
`world-island` mint (seed 55, ~112×114u, 3 lobes, two meadow stamps, rolling relief) at
world (344,−1152), blocks (4–5, 17–18) + (6,18) of `FF9CustomMap-world` — inside the
archipelago's bay, NE of island C. All offline gates clean (geometry, UV language,
placement census MISS=0, Moguri-atlas alpha, shape language); regeneration one-liner in
`ff9mapkit/examples/continent-v1/README.md`. Proven, it replaces the (3,14) bench as
the home for the forest-carry, hill, and terrace rungs.

Round-1 playtest (seed 20, blocks (4–6,17–18)): 5 of 6 blocks rendered walkable with the
cliffline; **block (6,17) never rendered** — it is a REAL sea-skirt block (sea3/4/5, the
real continent's offshore water W of (7,17)), so its own prefab loads and carries no
`Terrain` transform for the s34 loose override to bind to: the land fragment silently
vanishes. That is the transplant path's OPEN-OCEAN TARGET LAW biting a builder that never
had the gate — `world-island` now refuses any footprint block with real per-block assets
(hard refuse, no escape flag). (6,17)'s W+S frame edges are pure sea4, so the re-mint
lawfully keeps (5,17)/(6,18) beside it — only land had to move.

## The forest RE-HOME (★ IN-GAME PROVEN 2026-07-12 — "walked the whole rim aggressively, no more sticking anywhere")

`forest_rehome.py` carries the (15,15) canopy blob onto **island E's west lobe** (blob
centre world (312,−1140), 19u rim clearance — forest west, meadows east), retiring the
flat bench. It composes the proven carry recipe with the island's own machinery and
upgrades the two bench shortcuts: the carve runs on the island's deterministic world-soup
rebuild (byte-differential-proven == the deployed files), so the blob lawfully straddles
block borders via a generic-lerp border split; and the zip annulus gets faithful per-cell
mains UVs (each cell's quadrant/orientation DECODED from the kept tris' own UV bytes)
plus ring-owner normals instead of the bench's stretched-single-tile + hard-up fill.
Two law reruns caught real bugs offline: THE WALL LAW (the border split's plan-area
degeneracy filter silently dropped the vertical canopy curtains — 3D-area test required)
and the step gate (worst wall rise exactly 2.20 ≤ the 2.34375 ceiling; zip max rise
0.41u). 4 blocks changed, (6,18) untouched byte-identical.

Round 2 (the in-game stuck report at the rim): the per-face step gate is INSUFFICIENT —
the engine's climb is surface-to-surface across one foot step (~0.44u/frame), and vertical
walls are un-hittable (geometric ny ≤ 0.1), so the sampled climb = wall jump + one step of
dome slope; per-face 2.2 left 0.14u and the dome ate it. Also source-verified: descent is
ALWAYS legal (`ff9.rayDistance` is dead code in `WMBlock.Raycast`) — the kit's placement
simulator dropped its phantom 2.8 drop window. The comprehensive form now in the script:
per-STATION rim lift (launch pad within 2.10 of the exact canopy surface ≤0.75u inside,
sampled along every rim edge) + THE PERIMETER WALK-IN GATE (0.05u ground transects across
the whole rim; every ordered pair within one 0.65u step must climb ≤2.30). Worst climb
after the fix: 2.05 (was effectively 2.42+). ★ Round-3 playtest proved the whole rim
block-free. The (3,14) bench override is RETIRED (deleted; backup in `backups/`) — its
block is real map land, now restored to stock.

## The HILL at scale (★ IN-GAME PROVEN 2026-07-12 — "looks natural in-game, walkable from all sides")

The measured grass-hill language (disc-1 census, `hill_at_scale.py` header): lowland grass
slope envelope p50 6.5° / p90 15.7° / **p99 28.6°**; PURE-GRASS summits are real (no
mural-family handoff needed — e.g. (16,14) y 8.2/prom 4.2, (17,15) prom 5.1, (9,17) prom
5.2 over ~20u); profile = gentle cap, mid-flanks 20–24°, prominence 3.5–5.2 over 20–26u,
inside the lowland band (≤8u). The build: a raised-cosine dome **H=4.2 R=18** at island E's
south lobe (348,−1184) — pure-Y displacement of the DEPLOYED meshes (mains UVs are
XZ-linear ⇒ every tile stays lawful; the rolling relief rides on top), fams classified
straight from the deployed bytes (topo + UV family region), normals re-smoothed LOCALLY
(forest donor normals untouched). Gates: worst flank 21.9° ≤ p99, peak 7.40, cracks 0,
census MISS=0, single changed block (5,18).

## The PLATEAU-EDGE anatomy (studied 2026-07-12 — `plateau_edge.py`, offline)

The interior sibling of the coast cliff-lip laws, measured over 1037 plateau|49 crest
edges / 76 wall components / 48 blocks. The laws:

- **THE 27u RIM**: plateau crests band tightly at y 26.1–27.2 (med 26.6).
- **THE SOFT CREST**: the grass|rock dihedral is med 50° (p10 33 / p90 64) — softer than
  the coastal 66° crease; grass rolls in at ~7° (coastal ~9°).
- **NO LIP ROW inland**: plateau grass runs ORDINARY mains texture (V 0.769–0.830) right
  to the crest — the coastal 0.893 lip-row vocabulary is coastal-only.
- **THE INTERIOR WALL ≠ THE COASTAL STRIP**: 0 of 76 wall components touch the coastal
  rock strip. Interior walls sample a LARGE mountain-rock atlas region (u 0.004–0.642 ×
  v 0.109–0.363) in QUANTIZED 128×128px rects with lattice-snapped corners — a TILE
  LANGUAGE, not a mural — with FREE orientation (u tracks height stronger than v on the
  (14,13) reference wall). Mintability verdict: synthesis is ON, but a from-scratch wall
  first needs the tile-neighbor decode (a Wang-style study) of this rock set.
- **STACKED WALLS**: faces stack 4–10u (max rise med 6.0 / p90 9.6) for total drops med
  24.4 / max 40.3, landing dominantly on lowland grass.
- **THE MID-SHELF + NO-FOOT-PASS FINDING**: topo-13 = flat GRASS-textured shelves pinned
  at y 15.7–18.3 (slope 6–8°), ringed by 49. No ramp class exists anywhere: with the
  2.34375u step ceiling, the two altitude worlds are NOT connected by overworld walking —
  the game connects them via fields/vehicles. A faithful terrace build = shelf + stacked
  walls; no ramp is required (adding one would be off-language).

## The interior ROCK-WALL TILE LANGUAGE (decoded 2026-07-12 — `rock_wall_language.py`, offline)

The tile-neighbor decode over 8945 tile groups / 13929 neighbor pairs / 48 blocks — the
synthesis recipe for the terrace-wall rung:

- **THE WALL BANDS**: 86 tiles organize into 4-column bands with vertical ROLE structure —
  the **crest band** (atlas rows 3–4 × cols 4–7; 950/1006 crest-touching groups), the
  **upper-body band** (rows 6–9 × cols 0–3), the **lower-body/base band** (rows 7–10 ×
  cols 6–9; the true foot course row 10 exists ONLY here; 564/585 base-touching groups).
  A wall descends crest → upper body → base through the bands. (Minor accessory tiles at
  rows 18/20/21/25 — low-count features.)
- **THE COURSE QUANTIZATION**: one 128×128px tile per wall QUAD (med 2 tris) covering
  ~4.7u of height (p90 5.4) — the interior analog of the coastal column quantization,
  matching the stacked-wall 4–10u faces.
- **WINDOWED CONTINUATION, not Wang, not free**: 46% of geometric neighbors are
  ATLAS-ADJACENT (±1 col/row) + 11% same-tile repeats; ±3-col jumps are the 4-col band
  wraps (the coastal sawtooth generalized to 2D). Synthesis = advance u along the wall
  wrapping the band (window-translate at wraps — the coastal smear lesson), descend v
  through the role rows per course.
- Lattice phase learned from data (u: dual phase families ≈ staggered courses; v: 64/80px
  phases); groups are lattice-snapped ≤128px rects (the grouping guard held).

**⇒ THE TERRACE-WALL RUNG IS UNBLOCKED: full synthesis recipe in hand** (courses of ~4.7u
quads; crest/body/base band rows; u-continuation with band wrap).

## The INSTANCE anatomy (decoded 2026-07-30 — `rock_wall_instances.py`, after T1's failure)

The first decode never asked per-INSTANCE questions; terrace-wall T1 failed in game on
exactly those (flipped tiles, stamped-together sides — `studies/path-d-new-world/
TERRACE-WALL-PREDICTION.md`). Same grouping verbatim (8945 instances — the count is the
calibration), three laws:

- **LAW 1 — V-ORIENTATION IS FIXED PER TILE**: 54/62 well-sampled tiles are ≥90%
  orientation-consistent (the 8 mixed are low-count accessory tiles). Take orientation
  from the per-tile MAJORITY, never from one exemplar.
- **LAW 2 — MIRRORING IS RARE, NOT ABSENT**: 12.5% of horizontally-adjacent pairs invert
  their u-sense (same-tile pairs 15.6%). A mirror-free wall and a coin-flip wall are both
  off-language.
- **LAW 3 — A WALL COLUMN IS A CONTIGUOUS VERTICAL ATLAS STRIP**: the dominant vertical
  transitions are same-column row-descent, `(c,9)→(c,8)→(c,7)` (~130+ instances each),
  capped body→crest by specific pairs (`(7,7)→(5,4)` ×111, `(8,7)→(6,4)` ×106, and the
  `(0-1,7)→(0-1,6)` family). Courses are NOT independently-tiled bands — v continues down
  one atlas column per wall column, then the crest caps via the measured transition table
  (`out/rock_tile_instances.json` holds the full table + per-instance orientations).

## THE MASSING DECODE (2026-07-30 — `rock_wall_massing.py`, after the discriminant refutation)

The refutation said the silhouette is the look's carrier; this measures it, same wall
components as the two tile decodes. Numbers over 8,945 instances / 3,908 welded pairs /
2,616 foot edges (`out/rock_wall_massing.json`, profile renders in `out/massing/`):

- **THE 50° LAW.** Interior plateau walls batter at med **50.1°** (p25 43 / p75 57), uniform
  bottom-to-top. **NOT the coastal 73°** — T1 put a coastal cliff profile on an interior
  wall; the slope itself was off-language before any tile landed.
- **Courses weld COPLANAR**: dihedral med 6.8°, 71% under 10°, only 3% jogged ≥25°; the
  face retreats ~2.9u per course. The wall is a smooth battered sheet, not stacked ledges.
- **Ledges are DISCRETE features**: sparse (~1 per 44 quads) and deep (med 5.6u, p90 8u) —
  event-like shelves, not per-course trim.
- **THE FOOT IS SMOOTH**: turn med 17.4°, right angles **1%**, med edge 4.0u, 67% of verts
  lattice-touching. T1's right-angle lattice jag ("sharp edges at the bottom") is
  quantitatively off-language — feet touch the lattice but never zigzag it.
- **The crest is level but plan-wiggly**: height jitter med 0.4u, turn med 28.6°.
- **Profiles** (per-column silhouettes, normalized): one consistent mean batter per
  component with ORGANIC per-column wobble — irregular in-out jogs and ledge placements
  unique to each column. T1's columns were geometrically identical.

**THE VERDICT the study exists for:** the MEAN massing is lawfully compressible (batter,
course heights, retreat, foot smoothness, crest jitter — a small parameter set), but the
per-column wobble is the look's carrier and is organic — the precise class THE FORM LESSON
says statistics cannot fake. If the wall rung ever reopens, the grounded next idea is
**PROFILE-CARRY** — Rung F applied to walls: carry REAL columns' profiles (or whole wall
strips) verbatim onto a minted plan, and only then dress with the instance-law tiles. Not a
wobble generator, and it needs its own prediction registration.

## The TERRACE arc — round 4: THE TWO-LEVEL ISLAND (deployed, awaits playtest)

`two_level_f.py` **DEPLOYED 2026-07-12** (762 tris, block (3,17)): island F as
lowland-south / plateau-north (shelf y=17, topo 13) joined by a 3-course escarpment chord;
the sea side is a tall coast wall with FREE bases below the waterline. Teleports:
**(224,−1138)** = the lowland, **(224,−1108)** = the plateau top. All gates pass
(census MISS=0, zip winding, both ground probes); the offline render shows a coherent
escarpment, a clean corridor, closed ends. Five moves minted in the fix round (full
statements in the memory file):

- **THE ASYMMETRIC STRIP** — clear 2.5u on the plateau side but the wall's whole footprint
  (3·run + 1.5 ≈ 10.1u) on the lowland side; courses never hover over kept grass, the zip
  is a real apron.
- **THE DISTANCE-TRUE OFFSET** (`offset_ring`) — dense resample → outward-normal push →
  the FOLD FILTER (offset points closer than D to the source = fold loops → dropped). One
  rule for chord/coast/corners; the notch can't fold rings.
- **THE ARC-PROJECTED CREST COURSE** — ring-1 stations project onto the crest's arc
  (`crest_param`); monotone merge by arc; native crest verts keep the identity weld and
  take lerped u along their tile's top edge. The coast-arc fan compression is gone.
- **THE CELL CLIP** — zip tris clip to the 4u cell grid BEFORE the per-cell mains decode
  (spanning tris hit mains_uv's bleed clamp → the corridor's dashed smears).
- **THE TANGENT-EXIT TRAP** — a partition line exiting through a coastal extreme grazes
  the coast tangentially and degenerates every offset/fan (the chord exits island F at its
  EAST TIP). The wide out-strip + a largest-component sliver prune absorb it; wall ends
  close with rock END FANS through the foot ring's sea verts (never a stretched grass cap).

Known cosmetic remainder (deferred): a small stripy corner-fan patch (~4×3u) on the wall's
outer skirt over open sea at the east corner, visible only from the sea side.

**Playtest round 3: STILL stuck (inside the mountain, the west mouth) + still-stretched
tops → the user called the meta-law: "study the actual mountains before synthing too much
of our own". Island F RESTORED PRISTINE (the trap is gone).** The round-3 trap: the moat
trim raised the floor, but the corridor still dead-ended AT the island edge inside the
Sea4 lap zone — pressing west queries open sea (cacheable) while sea laps under the slot
floor (THE MOAT LAW v2: walkable synth ground ends ≥~4u inland of the outline).

## THE v3 VERDICT + THE v4 PLAN (the state to resume from)

Three v3 rounds (facing flip → top snap + foot strip) all ended REJECTED: "tons of jank —
very spiky, faces stacked over each other, no form to it." Island F is RESTORED PRISTINE.
**THE FORM LESSON:** the bend-carry moved real CONTENT through a synthetic FRAME — ribbon
(s,d,h) + per-vert corrections destroyed the donor's coherent 3D massing; that is still
synthesis (the meta-law's fourth firing). `two_level_v3.py` stays as the falsification
record; its GATES (rule-f oracle, moat/verge, facing check) are the keepers.

**v4 = TRANSPLANT A WHOLE REAL TWO-LEVEL COASTAL FEATURE** (decided, not started): census
disc 1 for a real coastal window (1-2 blocks) where a highland shelf + escarpment meets
lowland grass and the sea; carry it VERBATIM with the proven `world-transplant`/`world-fuse`
machinery (the continent pillar's zero-guess path). Fallbacks: in-place morph of a real
escarpment coast, or a 3D-massing anatomy study. Do NOT resume ribbon-bending.

## THE v4 TRANSPLANT CENSUS (★ DONE 2026-07-12 — the donor is found)

Three scripts (`v4_transplant_census.py` → `v4_rect_scan.py` → `v4_window_probe.py` +
`v4_donor_detail.py`/`v4_donor_render.py`; artifacts in `out/`):

- **THE ISLAND COROLLARY of the no-free-mesa law:** map-wide landmass components (blocks
  connected by LAND crossing shared frames, wrap-aware) show NO small sea-ringed landmass
  has walkable highland. All real high country (walkable y>18: 31.6ku²) lives on the ONE
  97-block continent (esc 211ku²). The only compact sea-ringed "mountain" landmasses are
  Uaho (0,0) and the (9-10,5-7) 2×3 crag island — both crag-only, no second walkable level.
  A pure full-containment two-level island donor DOES NOT EXIST; FF9 never built one.
- **THE LOWLAND-CUT RECT SCAN:** the lawful cut crosses only lowland (the cut-line law —
  high relief is a component, cut around never through). Scanning every rect ≤4×3 for
  windows whose EVERY external land crossing is ≤6.5u found essentially ONE raised-walkable
  feature: **the (5-6,15-16) river-terrace highland** (mid 820u², ALL topo-13; esc 5.2ku²;
  cover 0.50) — the same falls the original census flagged as "the seam between the two
  altitude worlds."
- **THE DONOR: window (5-7,15-16) 3×2** (192×128u). A rocky horseshoe massif (walls to
  ~31u) rising from a lowland grass coastal ring, enclosing a hanging grass bowl at
  y 15.2 (topo-13) with a real river + TWO waterfall sheets + a small stone object mesh;
  a NE peninsula, a SE FOREST islet (topo 37), real sea1-free all-cliff coast (no beach
  anywhere in-window). **Quest-clean by construction: zero event bits on every tri** (the
  dispatch areas are 48 = "Esto Gaza/Terrace", 50, and 45 on 12 dirt tris). The whole
  feature closes inside the window except TWO 8u-wide lowland necks on the N frame
  (donor x≈388-396 grass tongue, ymax 3.6; x≈467-476 the (7,15) dirt-islet tip, ymax 3.2
  — and (7,15)'s sea parts are FULL-CELL under its land, so dropping that islet leaves
  clean real sea).
- **THE TARGET: rect (1,16) 3×2 rot 0** — cells (1-3,16-17), all true prefab ocean
  (island B's empty east column + free water), REPLACING island F's cell (3,17). v4's W/E/S
  frame edges are pure open water (fuse-legal toward B, E, and C).
- **THE FREE-RIDE DISCOVERY (what killed the "carry-set extension" work item):** the s34
  sidecar loads the DONOR BLOCK'S WHOLE PREFAB for a reclaimed cell and overrides only the
  parts with deployed files — identity for the rest. At rot 0 / shift 0,0 block-local
  coords are position-independent, so the falls/river/riverjoint/object sub-meshes ride
  along VERBATIM FOR FREE. Stripping (if ever wanted) = empty-stub overrides — already a
  proven mechanism (island F's mint deployed 176-byte stubs for its unused parts).

**THE v4 BUILD (round 1 ★ IN-GAME PROVEN 2026-07-13: the falls/river/bridge ensemble renders
— THE FREE-RIDE MECHANISM PROVEN; the neck cuts "look the same as verbatim" — no further
treatment; minimap shape check pending, cosmetic).** `world-transplant
--mod-folder FF9CustomMap-world --cell 1,16 --donor 5,15 --size 3x2 --shift 0,0
--land-margin 0` — first dry-run CLEAN, zero hand edits; the machinery auto-armed its
proven N tongue strips for the two necks. Deployed 30 files (6 cells × Terrain/Sea3/5/4 +
Donor.txt). Removed first (backed up to `backups/v4-predeploy.20260713/`): island F's 8
files at (3,17) + the sanctioned-deletable (2,16) reference islet (5 files, the island-B
cliff-lip leftover). Post-deploy: engine-true probes on the DEPLOYED bytes ground 462
lowland + 84 bowl points (topo-13 at y≈16.4 over the 15.2 river plane); 16 no-hits, all
inherited from the real map. Minimap re-composited (21 blocks). **Teleports: lowland
(75.5, −1074.5) · terrace bowl (130.5, −1077.5)**. After four falsified synthesis rounds,
the transplant path delivered the two-level island — lowland ring + hanging terrace +
real falls — on its FIRST deploy, with zero new machinery.

## THE PRODUCTIZATION (★ 2026-07-13): `world-forest` + `world-hill` are kit verbs

`forest_rehome.py` + `hill_at_scale.py` are extracted into `ff9mapkit/world/interior.py`
+ two CLI verbs (`--near` scan / `--center` exact; deployed-bytes only, byte-derived
fams, all study gates incl. the perimeter walk-in simulation). **Proven by IDENTITY**
(`interior_productize_check.py`): clean seed-55 mint → module forest carve → module hill
reproduces the deployed, in-game-proven island E **byte-for-byte on all 5 blocks** — and
the CLI verbs' own `--near` scans, run end-to-end on a scratch mod folder, converged on
the studies' exact placements ((312,−1140) forest / (348,−1184) hill) and reproduced the
same bytes. One new law minted: **the hill scan's ROLLING-RELIEF ENVELOPE** (footprint
y-span ≤ 2.4u — an existing hill's footprint is still pure mains, and the naive scan
self-selected it and tried to stack; the slope gate refused, and the envelope now keeps
the scan honest). Hermetic tests: `ff9mapkit/tests/test_world_interior.py`.

## THE PRODUCTIZATION (★ 2026-07-15): `world-mountain` is a kit verb

`massif_carry.py` (the in-game-approved Uaho carry) is extracted into
`interior.carve_mountain` + a CLI verb (`--near` scan with exact-90° rotation fallbacks /
`--center` exact; `--donor` default `0,0` = Uaho, the only donor with an anatomy study —
the alcove floor is donor-conditional and the aperture-plug chart phase is inlined from
`daguerreo_massif_anatomy.py`). All study gates carried: ROCK-RIGID, the weld-safe
per-POSITION apron lift, the DP zip envelope, baseline-subtracted once-edges, the
rock/grass placement probes, the Moguri-atlas alpha gate, the census. **Proven by
IDENTITY** (`mountain_productize_check.py`): the pristine bench mint (preserved game-side
as the deployed file's `.pristine-r31s42` sibling) → module carve reproduces the
deployed, in-game-approved bench **byte-for-byte** — the module's own scan converges on
the study's exact placement ((162,−1246) rot 0) and its mint-hole patch replays the
study's one patched hole; the go-forward fresh-mint path differs only by the mint's own
concave-dent fix (24 tris at the two dents, far outside the carve; block (2,18)
byte-identical). One robustness guard minted during extraction: the mint-hole detector
now distinguishes a REAL hole from a legally-detached tri whose own edges chain into a
3-cycle. Hermetic tests (incl. a synthetic pyramid-donor end-to-end carve with a
monkeypatched donor read): `ff9mapkit/tests/test_world_interior.py`.

## THE HORSESHOE DONOR CHECK (★ 2026-07-15): DISQUALIFIED — THE ENSEMBLE-APERTURE FINDING

`horseshoe_donor_check.py` → `out/horseshoe_donor.json` — the qualification pass for the
Daguerreo horseshoe (blocks (5-6,15-16), the v4 transplant's centerpiece), run through
the SHIPPED `_mountain_blob`/`carve_mountain`. The massif is structurally beautiful
donor material — 562 rock tris + the flooded hanging bowl (121 topo-13 + 30 interior
topo-58) = a 713-tri blob, ONE clean 62-pt foot rim at y[2.4,6.4], radius **54.3u**,
one interior ring — but the qualification DISQUALIFIES it on three independent axes:

1. **THE ENSEMBLE-APERTURE FINDING** (the headline law): the interior ring (43 pts,
   y[15.2,29.4] = the river/falls MOUTH through the massif) is 100% owned by the UNION
   of the donor's auxiliary parts (object 22 / falls 12 / river 15 / riverjoint 4,
   overlapping) — **Uaho's object-only aperture law is the small-mountain special
   case**. The shipped aperture gate refuses, correctly.
2. Even with a union-validated gate, the Uaho-style plug would seal a **14u-tall river
   mouth with collar rock** and carry the bowl as a dry dead pond — a form alteration of
   exactly the class THE FORM LESSON kills. The faithful path is **THE ENSEMBLE CARRY**
   (a future rung): transform falls/river/riverjoint/object parts under the same rigid
   map and deploy them as part overrides — real new machinery (part deployment, the
   animated water materials, object SUBSETTING: the object part also holds Daguerreo's
   entrance scenery).
3. **Bench feasibility**: horseshoe scale needs ~r69 mints, and `world-island` r69 is
   not robustly clean (seeds 7/11/23/42 trip `grass_over_8u` by 2-3 interior slivers;
   seed 55 trips the shape gate) — a mint-robustness rung of its own. Free 3×3 ocean
   windows are NOT the constraint (19 exist map-wide).

Today's tool for placing the horseshoe remains the proven **v4 rect transplant** (the
water system free-rides). `--donor` stays Uaho + the crag.

**→ THE ENSEMBLE CARRY (★ built same day, 2026-07-15, user green-lit).** The
disqualification became the spec: `ensemble_inventory.py` measured the aux parts (ALL
components 100% inside the rim — no town scenery in the donor rect; 122 tris total;
stride-48 with REAL tangents; parts ship per-block) and `carve_mountain` now carries
them: rings not object-backed validate against the PART UNION (`ENSEMBLE_PARTS`) and
classify as **ensemble apertures** (no plugs — the parts cover the hole exactly as
stock); each aux component in the rim footprint rides the same rigid map (positions
de-tilt+rot+DY, normals inverse-transpose, tangents as sheared directions, UVs verbatim)
into per-block part overrides; `deploy_mountain_parts` writes content + BLANKS for every
ensemble part on every span block (the free-ride trap) + the **Donor.txt divert** to a
part-carrying donor block ((5,15) has all five transforms). Gates evolved en route, each
Uaho-frozen: the crack gate exempts open ensemble rings by SEGMENT proximity
(border-split halves), the edge gate covers synthetic zip only (verbatim stock rock is
donor-given), the zip envelope gains a bank allowance (≤2 tris in [0.5, 0.83) — the
horseshoe's falls-outlet bank, min ny 0.59), the peak probe replaces the bbox-centre
probe (a horseshoe's centre is its open mouth), and the span widens with PRESENT
apron-rect blocks under a per-position taper (border starvation fix). Plus the bench
enablers: adaptive outline density past r60 + the conditional >8u fill refinement in
`world-island` (both no-ops on every frozen baseline). **DEPLOYED**: r72 seed-42 bench
at (1280,−1184) blocks (18-21,17-19), the horseshoe at (1288,−1190) rot 0 — 713 terrain
tris + 122 aux tris (Falls/River/RiverJoint/Object) across a 10-block span, census
MISS=0, both byte-identity acceptances + 3515 tests green; teleport **(1227.5,
−1189.5)** face east.

**★ IN-GAME PROVEN + CLOSED over 3 rounds (2026-07-15).** Round 1: *"the falls animate,
the bowl is walkable"* — the mechanism (part overrides + the Donor.txt divert binding
ANIMATED materials) is proven — but a seam/see-through quad + a walk trap → **THE
FOOTPRINT SWEEP**: 8 donor terrain tris sat plan-inside the rim uncarried (the mouth
tunnel's topo-58 lining = the trap; a weld-isolated 2-tri rock SHINGLE = the
see-through quad; a canopy bit). They cannot join the blob's manifold ring math (a free
shingle touches the sheet at ONE vertex — THE WALL LAW's shingled reality), so every
centroid-inside-rim tri now rides VERBATIM outside the ring accounting, its open edges
exempt at the crack gate by segment proximity. Measured EMPTY on Uaho + the crag.
Round 2: three walk defects (climb the falls, walk off the bridge into the water, still
trappable) → **THE WALK-LEGALITY LAW**, read from the engine: the ground query reads
the hit tri's `tangent.x` as the IDALL for MOVEMENT LEGALITY (`(id & 0xFC) >> 2` vs the
per-vehicle 64-topo limit mask — `ff9.cs w_movementCheckTopographID`; the foot mask
`{0x0010667F, 0xD8FF3CFF}` blocks 49/58, walks 0/13/17/37), and stock aux parts carry
leftover REAL tangents whose x garbage-decodes to **topo 0 = walkable** (stock never
noticed — its mouth interior is unreachable on foot) → **THE SCENERY SEAL**: worldmap
shaders never consume tangents (Terrain stores IDALL floats in that channel and shades
fine), so carried aux parts store a blocked-topo IDALL (49) — the bridge/falls/river
ensemble becomes look-but-don't-touch scenery, exactly stock's semantics; ONE change
sealed all three defects. Round 3: *"that worked, it's sealed now"*. The bowl stays
scenery-only by choice (stock semantics; a walkable bowl would be a designed terrain
path, not a carry fix). **`--donor` qualified: Uaho (0,0) · crag (10,5-6) · horseshoe
(5-6,15-16)** — the mountain arc's claim is now *any studied massif, any size, water
and all*.

## THE CRAG DONOR ANATOMY (★ 2026-07-15): measured, and DISQUALIFIED for single-block v1

`crag_anatomy.py` → `out/crag_anatomy.json` + `out/crag_map.png` — the donor-qualification
pass the backlog required before extending `world-mountain --donor` beyond Uaho. Findings:

* **ONE cross-block massif.** The crag's rock is a single 294-tri component (pure topo 49,
  no 7/62) straddling blocks **(10,5)+(10,6)** — 33×63u, peak y 26.5. Block (9,5) has no
  terrain mesh at all; (9,6)/(9,7)/(10,7) hold no massif rock.
* **Region-level, it is beautiful donor material**: the merged rim CHAINS cross-block into
  ONE clean 42-pt foot ring at y[6.0,8.0] (max 2u oscillation!), radius **33.7u**, de-tilt
  0.8°, residual ±1u; lattice-sheet class (v-weld 0.73, same class as Uaho/the horseshoe);
  no apertures, no pockets, no object ensemble.
* **Per block it is NOT a mountain**: each in-block fragment's "rim" includes the block-
  border cut and mid-shoulder heights (rim y up to 17.6, de-tilt 22.7°/residual ±6 on
  (10,5)) — and the real `carve_mountain` dry-carve REFUSES both, for the right reasons
  ((10,5): zip rise 4.66 > 2.34; (10,6): radius 28.1 doesn't fit any in-block placement —
  the hard ceiling is ~23.5u, the r31 bench pocket ~20u).
* **Its own tile band**: sharply tiled (corner peakiness 9–12×) but a DIFFERENT chart —
  phase (0.011719, 0.015625), exactly 1/256 off `ROCK_CHART_PHASE` in both axes, rows 2–6
  + 13–14 vs the Uaho/Daguerreo band's 6–12. The plug-chart constants are BAND-SPECIFIC;
  a donor from another rock look-family needs its own phase (moot here — no apertures).
* **Feet on topo 17, not grass**: the crag's painted foot fringe meets wasteland ground,
  not mains grass — a look-risk if ever seated on a grass island (offline-untestable).
* **Dispatch**: all rock baked (event 0, area 62) — the DONOR-DISPATCH STRIP handles it.

**THE DESERT GROUND LANGUAGE (★ 2026-07-15)** — `desert_ground_anatomy.py` →
`out/desert_ground.json`; the sidebar the crag's foot fringe demanded (painted against
topo-17 ground, unjudgeable on grass). Findings: 81 disc-1 blocks carry topo-17; the
ground obeys the SAME laws as grass (exact linear-in-XZ per 4u cell, one ~128px tile per
cell, 4 rotations, grass handedness 224:6, avoid-repeat neighbours 7%) with a busier
vocabulary (39 half-tile origins; the dominant 2×2 mains set covers 32%; a 4-row strip
column at u 0.844 = the B-strip analogue) and rougher relief (y std 2.44 vs grass
0.66–1.25). Real desert cells use FREE fractional windows across the painted-over
internal gutter (THE COL-FREEDOM LAW at ground scale — the naive 16-hypothesis gate
passes only 48%), but the locked grass-form window is a common real form and stays
inside painted art. **THE DESERT TRANSLATION LAW:** the desert mains region is the grass
mains structure translated by exactly **(+0.65332, −0.09863)** in the atlas — same
quadrant rects, widths, and gutters, byte-exact at 5dp — so the lawful mint form is
literally `G.mains_uv(...) + (DU, DV)` with topograph 17. `desert_bench.py` applied it:
the crag bench's 746 plain-grass tris retiled IN PLACE to desert mains (fresh per-cell
assignment, zero geometry change, atlas gate 0 blanks, census MISS=0), DEPLOYED +
mirrored — the crag now stands on its native ground; foot-fringe verdict pending.
Known cosmetic remnant: the coastal cliff-top LIP ring still wears its grass-family
tiles (the lip is its own vocabulary — a desert-island mint would need a desert lip).
**→ closed same day by THE WALL TRANSLATION LAW** (`desert_shore.py`): the "lip" is
painted INTO the mint's cliff-wall band texture, and the crag island's own coast
measures the same 4-tile-wide one-row band at (−0.27127, −0.02066) from `ROCK_U/V` —
the bench's topo-58 wall corners translated in place (zero geometry change), DEPLOYED
+ mirrored: the bench is now FULLY desert. **→ PRODUCTIZED same day as
`--ground grass|desert`** on `world-island` + `world-mountain` (`grassland.GROUNDS`,
`ground_uv`; stamps disable off-grass): grass is the bit-frozen identity (BOTH
byte-identity acceptances pass unchanged), and the full desert path runs green offline
(module desert mint → verify clean → the crag carve, all gates). **The full desert
bench is ★ IN-GAME PROVEN 2026-07-15 ("looks good": ground + shore + the native-ground
crag).** EARMARKED for the future — **THE DESERT TILE FIDELITY CHECK**: the mint uses
locked grass-form windows (stock desert slides FREE fractional windows, 48% locked) and
reuses the grass relief field (stock desert: y std 2.44 vs grass 0.66–1.25); both fine
at bench scale — revisit if a large desert landmass reads too regular/smooth.

**THE DESERT TILE FIDELITY CHECK — round 1 (2026-07-15, playtest pending).** The check's
vehicle: a pure-plain r52 seed-11 desert island at **(768,−1216)**, blocks (11–12,18–19)
(the last free 2×2 ocean window in rows 14–19), deployed to FF9CustomMap-world + disc-4
mirrored, all gates clean. `desert_fidelity_eye.py` = the offline eye (plan-view
Moguri renders: TEXTURE / HILLSHADE / COMBINED; mint interior vs stock desert blocks
(12,4) + (12,5)) → `out/desert_fidelity_eye.png`. Offline verdicts:
1. **THE DEAD-RELIEF DISCOVERY (a real kit bug, worse than the earmark):** the mint
   applies NO relief anywhere in practice — `grassland.relief_field` keys its lattice on
   the donor block's LOCAL 4u nodes (i∈[0,16], j∈[−16,0], gap-filled to ±16 around the
   world ORIGIN) while `island.fill_y` samples `relief_at` with WORLD coords, so every
   island away from block (0,0) gets `field.get(...) → 0.0`. Verified: a fresh island-E
   re-mint is byte-flat at 3.20 (its deployed roll is entirely the forest rim-lift +
   hill builds), and the fidelity island's deployed bytes are y∈{0, 3.2} exactly. The
   grass/mountain byte-identity acceptances stayed green through this because BOTH sides
   of the comparison were flat — identity proves consistency, not relief. The never-flat
   law is silently unmet by every mint to date (they read OK in-game at bench scale, so
   this was invisible until now).
2. **The texture gap reads as VOCABULARY, not window phase:** at 64×64u the mint's
   locked-window repetition is subtle (desert mains are low-contrast), but stock desert
   is only ~32% mains — its look at scale comes from the OTHER origins (shrub-rosette
   clusters, vegetation clumps, grass inclusions, the u-0.844 strip column) scattered as
   loose patches. The mint is a uniform mains carpet; the free-window sampler alone
   would NOT close this — the busier tile vocabulary is the visible axis.
In-game round 1 = judge the deployed island as-is (both axes in one walk). If it reads
wrong, the extension order suggested by the eye: (a) a desert RELIEF field scaled from
the measured stats (also fixes the dead-relief bug — decide whether grass mints adopt
it too, which breaks the frozen flat-mint identity oracles), then (b) the vocabulary
sampler (mains + measured shares of the non-mains origins per the census), then
(c) free fractional windows last (least visible offline).

**★ VERDICT — THE CHECK IS CLOSED (playtest 2026-07-15): "no and no — this looks like
a fine desert."** Neither gap reads in-game at r52 scale: the locked-window mains
carpet passes, and dead-flat ground passes (the player-height oblique camera + the
low-contrast desert texture hide both axes the plan-view eye could see). The desert
ground spec STANDS as shipped — no free-window sampler, no vocabulary sampler, no
relief field needed for `--ground desert`. The check island is KEPT deployed (the
first pure-plain `--ground desert` island proven at scale; remove = delete the
28 files across blocks (11-12,18-19) + re-run `world-mirror`). THE DEAD-RELIEF
DISCOVERY was resolved same day — **the user chose RETIRE over fix** ("B, with C as
fallback"): `grassland.relief_field`/`relief_at` and `build_landmass(relief=...)` are
REMOVED, `--flat` now means only "skip the meadow stamps", and every doc states the
interior is flat at `--height` by design (explicit height = the studied verbs).
**Proven a byte-no-op:** a post-retirement re-mint of this island reproduces all 32
deployed files byte-for-byte (removing `+0.0` changes no floats), so the frozen
identity oracles stand untouched. **THE RESURRECTION PATH (the user flags relief as
"useful for big continents for sure"):** if a continent-scale plain ever reads too
flat, rebuild relief as a measured per-ground rung — grass y std 0.66–1.25 /
|dY| med ~0.2 / p90 ~0.5–0.7, desert y std 2.44 / med 0.33 / p90 1.04 (this study +
`census.py` regenerate the stats) — with a position-independent frame (island-local
or lattice-wrapped anchoring; the original bug was block-local field keys sampled
with world coords), rim-fade preserved (welds keep exact Y), applied per ground
family, and proven through the offline eye + one playtest like every other rung.

**THE ROLLING-RELIEF RESURRECTION (★ BUILT + DEPLOYED 2026-07-21, playtest pending).** The
resurrection path above was taken — but NOT as prescribed (a re-key of the old snapshot). The
archaeology found the old `relief_field` had TWO defects, not one: (a) the fatal frame bug (block-local
lattice keys sampled with world coords → 0.0 off block (0,0)), and (b) a latent one — it was a
single-block VERBATIM SNAPSHOT (a 16×16 = 64u patch), non-tileable, reading 0 past one block even if
re-framed. A faithful resurrection needs a field defined over ALL world XZ. So the rebuild is a
**deterministic WORLD-XZ VALUE-NOISE field** (`grassland.relief(x, z, seed, amp)` + `relief_fade`):
2 octaves (base period 20u w1.0 + detail 10u w0.45), default amp 1.3, `GROUNDS[..]["relief_scale"]`
per family (grass 1.0, desert 1.6). Because it is a PURE function of world (x, z): the frame bug cannot
recur (same world point → same height, always), and cross-block seam welds hold BY CONSTRUCTION (one
world (x,z) → one value on both sides of a border — a block-local field would crack seams). It is
**opt-in** (`build_landmass(relief_amp=0)` default → flat → byte-identity); the retire also silently
dropped the rim-weld short-circuit, which is **restored** (rim vertices → exactly `land_height`) plus a
smoothstep FADE (fade 2→12u ≈ one wavelength) so the wall-top ring never moves.

*Calibration (calib_relief.py; the design's ground truth):* stock grass topo-0, plane-DETRENDED, is
std 0.46-1.07 (calm interior plains 0.46-0.49), 4u-neighbour |dY| med ~0.2 p90 ~0.5-0.7, per-tri slope
p90 ~9-25 / p99 ~15-33 / max ~40 deg (independently re-confirms HILL-AT-SCALE p99 28.6), autocorrelation
decorr ~9-12u (wavelength ~18-22u); desert topo-17 is ~1.5-2× rougher. Stock relief does NOT taper at
the coast (the land edge is where the cliff rises) — the shore fade is a WELD-PRESERVATION requirement,
not stock mimicry. The prototype field at amp 1.3 measures **std 0.58, slope p90 8 / p99 11 / max 15
deg (>2.4× margin under MAX_FLANK 28.6), decorr 15u** — squarely in the calm-grass band,
position-independent across seeds/offsets, block-decomposition-invariant.

*Proof:* byte-identity of ALL 17 world-island oracle blocks HEAD-vs-worktree with relief OFF (relief
returns land_height unchanged — the same no-op the 2026-07-15 retire proved); the full offline gate
suite CLEAN with relief ON (cracks/down/steep/big/oob/holes/open all 0) + a NEW `verify_landmass`
slope-envelope gate `main_slope_p99 ≤ 28.6` (bites a 12.0-amp mint, vacuous for flat); the offline eye
`relief_eye.py` (top-down hillshade + grazing, CALIBRATED vs stock grass (15,15)/(18,12) through the
same pipeline — the mint's local |dY| med 0.16 / p90 0.40 matches stock 0.17-0.20 / 0.55-0.57;
`out/relief_eye_*.png`). Relief is MUTUALLY EXCLUSIVE with hill/forest/mountain per island (the 2.4u
ROLLING-RELIEF ENVELOPE gate in `interior.py` is the backstop). DEMO island deployed at **`--cell 10,9`
world (672,−608) r44** (the inter-continental strait, the most-flown-over open ocean; 6 blocks, both
discs mirrored, `backups/relief-demo.20260721/` + `revert_relief_demo.py`). The one open risk is purely
aesthetic (does the roll READ at the player camera) — the top-down eye shows it clearly, the grazing
view shows a gentle wall-free dome, and only the playtest closes it. Full API: `world-island --relief
[--relief-amp N] [--relief-seed N]`.

**THE GROUND FAMILIES (★ offline 2026-07-15, playtest pending)** —
`ground_families_anatomy.py` → `out/ground_families.json` + `.log`;
`ground_families_eye.py` → `out/ground_families_eye.png` (the atlas contact sheet).
The desert method (census → per-4u-cell exact-affine decode → mural screen → AUTO 2×2
detection → 5dp rect recovery → translation fit → wall probe) run over every remaining
walkable family + controls. **THE TRANSLATION LAW IS UNIVERSAL**: every family with
tiled data is the grass mains 2×2 translated, outer-bound exact at 5dp —

| family | topos | mains (du, dv) | wall (du, dv) | notes |
|---|---|---|---|---|
| grass (control) | 0 | (0, 0) zero spread | (+0.00022, −0.00015) ≈ 0 | machinery validated both ends |
| grass variants (control) | 1,2,3,10-13,42 | (0, 0) | — | family model BYTE-proven |
| scrub | 4,5,6 | (0.25977, −0.06738) | none in stock | the grass↔dirt ECOTONE tile set |
| brush | 38 | (0.45703, −0.20215) | (−0.27127, −0.02066) | wall = THE DESERT WALL VERBATIM (measured stock adjacency) |
| snow | 27,28 | (0.0, −0.33691) | (−0.44021, +0.05161) | same u-COLUMN as grass, v-shift only; icy band rows 0.94434/0.97461 (the memory's lip-row 0.944 ✓) |
| canyon | 45,46 | (0.7793, −0.31641) | (−0.69509, −0.49722) | red band shows a 3rd v-level (possible 2-row course wall) |
| dirt 19 / 20 | 19, 20 | = DESERT exactly | desert | family model BYTE-proven |
| dirt 41 | 41 | (0.38964, −0.13477) | none in stock | **family-model EXCEPTION** — its own pale-sand set, NOT desert's |
| dirt 16 | 16 | — | — | thin (6 blocks); COLUMN origin structure, no clean 2×2 (dry lakebed) |

Method fix en route: the naive 8-edge translation fit fails on EVERYTHING including the
grass control (identical 0.00196/0.00097 "spread" everywhere) because the mode-voted
INTERNAL hi/lo edges are contaminated by the gutter-crossing free-window form — the fit
must use the 2×2 OUTER BOUNDS (bleed-immune; the desert law itself came from lo edges).
The locked-form (mint-form) share is a minority REAL form even on grass (22% of mains
cells) — the gate is a diagnostic, not an acceptance; the locked mint is in-game proven.
The eye sheet confirms every translated region paints coherent art (scrub = green/dirt
ecotone, snow = white field + pale-blue ice wall, canyon = red tiers + dark red wall,
dunes41 = pale fine sand; 0% blank texels everywhere). **PRODUCTIZED same day**:
`grassland.GROUNDS` grew scrub/brush/snow/canyon/dunes (walls: brush = its real
measured desert wall; scrub/dunes BORROW the desert wall — an authoring choice, stock
never coasts them), `--ground` choices now track the registry on `world-island` +
`world-mountain`, constants pinned in `test_ground_families_registry`; both byte-identity
oracles pass unchanged (grass/desert entries untouched). **THE GROUND SAMPLER deployed
same day (playtest pending):** five r22 seed-11 islets in the row-19 open ocean, one per
family, one block each, all gates clean, disc-4 mirrored — scrub (480,−1248) block (7,19)
· brush (608,−1248) (9,19) · snow (864,−1248) (13,19) · canyon (992,−1248) (15,19) ·
dunes (1120,−1248) (17,19). First visit needs a world re-entry (new blocks); disc 4 a
relaunch.

**★ SAMPLER ROUND 1 (playtest 2026-07-15) — the translation makes tiles paint right;
whether a family is an ISLAND FILL is a second, independent axis.** Verdicts: **snow
"looks good" ★** · **canyon ★ "looks alright against verbatim"** (compared at the stock
flat-canyon window (486,−678) block (7,10); noted nuance — verbatim mixes MORE lighter
browns into the dark: the vocabulary-share axis again (stock grounds are only partly
mains; cf. desert's ~32%) — earmark-only, the desert fidelity precedent says it may
never read at scale) · **scrub =
"tiling/wang mismatch"** — and the follow-up parity probe FALSIFIED the macro-tile
hypothesis (stock places scrub grass-style free, parity-lock 31% ≈ the 25% chance floor,
all 4 oris uniform): stock only ever lays scrub as narrow SEAM strips between solid
grass/dirt fields, so the ecotone tiles read as "patchy edge" there and as raw mismatch
when filled — scrub is a TRANSITION vocabulary, not a fill · **brush = usable but
reads as forest-canopy top, rim dip doesn't line up** (user: likely the Black-Mage-
Village area brush; census slope med 30° — a SLOPE vocabulary, stock never shows it
flat-at-scale) · **dunes = ground reads good, but an INTERIOR type — doesn't blend with
the coastline** (the borrowed desert rim lip; the ground fill itself ★ verbatim-checked
at (1242,−294) blk (19,4) — "checks out"). Encoded as `GROUNDS[..]["cls"]`
island/transition/slope/interior + a CLI mint note + `test_ground_families_registry`.
**ALL FIVE sampler islets are KEPT deployed** (user, 2026-07-15) — the row-19 reference
exhibits for every family. **Later the same day: the CANYON islet (15,19) was REMOVED**
(THE WALL-CONTEXT LAW — minted red sea cliffs are off-language; user: "remove both";
backup `backups/canyon-removals.20260715/`). **⚠ And a deploy OVERSIGHT surfaced during
the removal hunt: the DUNES islet at (17,19) had been OVERWRITTEN by the snow island B's
south data cell** (the snow target scan misread the occupancy notes; the transplant's
real-target gate checks STOCK, not the mod folder — so nothing refused). The stale dunes
`Object.ff9mesh` remained at (17,19) but silently didn't render (Donor.txt named
(10,18), whose prefab lacks Object — the prefab-parts law). **RESOLVED same day (user:
option 1)**: the dunes islet RE-MINTED at block (10,19), centre **(672,−1248)** (same
r22 seed-11 spec; the exhibit row is whole again), the stale (17,19) dunes leftovers
(Object/Sea1/Sea2, both discs) swept to `backups/dunes-stale-1719.20260715/`, disc-4
re-mirrored. **And the incident is productized as THE MOD-OVERWRITE GATE**
(`transplant._mod_overwrite_gate`, on both transplant pipelines + `--allow-mod-overwrite`):
a target DATA cell already holding mod overrides now REFUSES unless its Donor.txt names
this deploy's own sidecar donor (a re-deploy of the same transplant — the proven
iteration loop stays free); the live-folder test proves the exact dunes configuration
now refuses on this gate alone. (The re-minted islet's coast wears the borrowed desert
wall — dunes touches topo-58 ZERO times in stock; the user re-affirmed 2026-07-15:
**kept as-is as a REFERENCE EXHIBIT, not a verbatim claim** — same status as the scrub
and brush islets.)

**THE MIXED-BIOME LANDMASS (rung 1 ★ BUILT + DEPLOYED 2026-07-15, playtest pending)**
— user-called. The composition grammar first (`biome_adjacency_census.py` +
`biome_seam_anatomy.py`): **the adjacency graph is SPARSE and DESERT-HUBBED** —
grass|desert 193 edges (flat direct welds), scrub|desert 958 (the dominant seam;
scrub barely touches grass, 58), desert|brush 532, desert|dunes 190 (patches 8–53u,
EXCLUSIVELY inside desert); snow and canyon touch NO walkable family. Boundary
anatomy: grass|desert and desert|dunes are NEVER plain-mains on both sides — each
pair has a dedicated one-tile ECOTONE STRIP COLUMN (width 0.0605, ~4 v-rows), and
**THE ECOTONE-STRIP TRANSLATION FINDING**: the columns are the grass B-strips
(STRIP_U/STRIPS_V) translated — dunes ecotone ≈ B + (−0.13478, −0.06738), the
grass|desert column at u[0.918,0.9785] ≈ B + (+0.5244, −0.047) (5dp fits = an
earmarked decode; desert|scrub needs NO strip — scrub mains ARE the transition,
355/958 plain|plain attested, and scrub-mains overlap onto the desert-topo side
122/199). **Rung 1 = the verbatim BIOME-PATCH WINDOW CARRY**
(`dunes_patch_carry.py`): a lattice CELL-SET window (straddle fixpoint over the
surface layer — topo-59 base and 62 are neither carried nor foreign — + THE
DESERT-RING CLOSURE absorbing pockets until the ring closes in desert + THE
DONOR-CONTEXT RING GATE: every ring edge's donor OUTSIDE must be desert-family, so
the deployed outside (mint desert mains) reproduces the donor context modulo the
free within-family texel swap). Built for DUNES first and **FALSIFIED BY CENSUS:
THE NO-ENCLOSED-DUNES LAW — no dunes ensemble in stock closes in desert alone**
(cliff-free or cliffs-carried, cap 2000 cells: every closure chains into
brush/grass first) — a dunes patch has NO verbatim window; it waits on the ecotone
vocabulary decode (or rides a future mixed-donor mountain-class carry). **SCRUB
CONVERGES: 16 desert-ringed windows** (9–15 cells, the Outer-Continent belt near
(988,−312)). DEPLOYED: a fresh desert islet at block (8,19) centre **(544,−1248)**
(r26 seed 2, the exhibit row) with a 19-cell verbatim scrub ensemble carried into
its flat interior (38 tris: 24 scrub + 14 desert ring, real relief y 3.04–3.85
conformed to H=3.2 by ring plane-fit + ring-exact IDW; area/event id bits rewritten
to the islet's, topo+texels donor-verbatim; gates: boundary-invariance ok, weld 0,
full census 0 MISS). The REAL ensemble for A/B: block (13,3) centre (1210,−386).
Disc-4 mirrored. **⚠→✔ THE FRAME BUG (found 2026-07-17, "the coordinates put me in
the ocean")**: the original deploy shipped in the WRONG FRAME — the carry built its
soup in WORLD coords (the block offset added on read-back) but handed it to
`_soup_block_mesh`, which stores its input verbatim as the block LOCAL frame, so the
override deployed at local (518,−1248) and the engine drew the island 512E/1216-off in
open ocean (never renderable — which is why the rung was never confirmed in-game).
The offline gates all PASSED because they were self-consistent in the wrong frame and
the differential census was masked by the real Sea4 mesh covering the samples. Fixed:
a `to_local` un-offset before `_soup_block_mesh` on both soups + a permanent
FRAME-BOUNDS GATE (a block override's local verts must sit in [0,64]×[−64,0], like
every real block). Re-deployed at local x[6.3,57.7] z[−59.2,−7.0] — the island now
renders at (544,−1248); disc-4 re-mirrored. **THE LESSON: a differential/self-consistent
gate cannot catch a frame error — assert the ABSOLUTE block frame.**
**⚠→✔ THE HARD-EDGE CLIP (round 2, 2026-07-17, "hard edges on the scrub")**: the first
window scan (seed-grow + desert-ring closure + a donor-context ring gate requiring
every boundary edge's outside to be PURE desert) selected a compact clean CORE of the
(13,3) patch — 12 pure-scrub + 7 pure-desert cells, **zero MIXED cells** — clipping the
donor's own dithered fringe (a MIXED cell = one 4u cell holding both a scrub tri and a
desert tri, the diagonal sub-cell blend; the donor region has 7). Rewrote the scan
around CONNECTED COMPONENTS: the whole scrub-cell component + a pure-desert 8-neighbour
ring, carried verbatim (mixed cells included), refusing any component not fully
desert-ringed (the full (13,3) patch abuts cliffs on its east — census-true, refused:
would need the cliff carried too). Only 2 fully-ringed scrub patches exist in the belt;
the winner carries **3 dither cells over 6 scrub cells** — the softest verbatim scrub
in FF9 (the map-wide census is mostly hard per-tile edges, 355/958 plain|plain, so a few
diagonal-blend tiles is as soft as stock scrub gets). Deployed at (544,−1248), A/B the
real patch at (1158,−388). **⚠ ROUND 3 (2026-07-17, the user's side-by-side): the carried
patch's ends are AMPUTATION STUMPS — "the 2 ends of ours are part of greater shrub on
the verbatim."** The bug: the isolation claim checked the ring for cliffs/foreign but
NEVER for MORE SCRUB — the 4-adjacency component was diagonally connected to the greater
shrub system (byte-confirmed: the carried comp touches 2 more scrub cells diagonally).
The corrected census (8-ring scrub-free = TRUE isolation): 12 components in the belt →
**5 truly isolated — and EVERY one leans on rock or brush** (best: 10 cells @ (986,−314)
with 1 wall cell). The scrub∪brush union test: the brush-only candidate at (1106,−134)
unions into a 121-cell system with 56 rock cells — brush is the SLOPE family, it chains
into cliffs by nature. **THE ENSEMBLE LAW (the mixed-biome composition verdict, 3
censuses deep): FF9's interior families NEVER sit as clean patches in open ground —
dunes never close in desert (the no-enclosed-dunes law), scrub is either a diagonal
fragment of a greater system or leans on rock/brush, brush IS the hillside. The faithful
unit is the whole interlocked ensemble (ground + shrub + slope + rock) — the
mountain-carry class on a bigger bench, not a flat-islet patch.** Disposition of the
islet's amputated fragment + the ensemble-carry rung = the user's call.
The future consumption of the three non-island families = mixed-biome landmasses
(scrub as the grass↔dirt seam, brush on carved slopes, dunes as interior plains).

**THE DESERT BEACH (★ offline 2026-07-15, the in-game rung PARKED at the transplant
fork)** — `desert_beach_anatomy.py` / `desert_beach_decode.py` / the pin census →
**THE BEACH TRANSLATION LAW**: stock desert beaches exist in force (14 Outer-Continent
blocks, 112 sand↔topo-17 back welds) and their topo-32 sand band is the grass band's
STRUCTURE at its own atlas spot — u-strip EXACTLY +335/1024 texels (P/Q preserved),
own single-valued v pins (run 548→579, cap 580→611: land edges −32, seam edges −30,
the ribbon 2 texels taller), foam universal, sand topo family-keyed 1:1 with the
backing ground (zero mixed blocks; topo 33 = the Lost Continent's foam-less FROZEN
SHORE at +330, measured only). **Productized as `coastmorph.SAND_BANDS`** + per-donor
auto-detection through every sand-band verb; grass byte-frozen (44 golden tests),
desert proven on all 15 real blocks (`desert_beach_acceptance.py`: decode 82% vs
grass 73%, sand_rebuild 12/15, cap_rebuild byte-identity 11/15; refusals = the same
residual classes as grass). En route: **THE ABSENT-PART LAW** — an in-place morph
CANNOT emit into a part the real cell's prefab doesn't carry (no transform to bind
the override; the (18,3) incident shipped a foam-less beach while gates read clean —
morph_in_place now refuses actionably; the bad deploy was reverted). The window scan
(`desert_beach_window_scan.py`, builders-as-the-oracle) first seemed to close the
in-place path: bare desert coasts lack the parts, beach-block coasts are the
cliff-lip by grammar (bay arcs!), and the two lawful (16,5) windows failed the
IN-PLACE-FRAME gate. **The transplant path (island-B) IS closed** — the census
truth: no self-contained desert landmass exists in stock (`desert_beach_transplant
_scan.py`: every desert beach block is continent coast; land-fit fails everywhere;
the only clean multi-block landmasses in FF9 are grass — (9,5)+2×3 and island B's
own (10,17)+2×2). But the frame-failure DIAGNOSIS re-opened in-place: the failing
verts were pure PART RE-LABELING (the wash re-band flipping sea3→sea2 at the frame,
water-union byte-identical) — and lawfully refused, since the NEIGHBOR's band at
those verts is sea3 ({2,3} off-language across the border, where a single-cell
morph can't re-band). The lever: **the wash reached the frame only at the default
swash 4.6 — at swash 3.8 (inside the ribbon envelope) the whole re-band stays
in-cell and the 14.6u window runs CLEAN through every gate.** ★ DEPLOYED
2026-07-15 (playtest pending): the first MINTED DESERT BEACH, block (16,5), the
Outer Continent's east coast — `world-transplant --in-place --cell 16,5 --donor
16,5 --bank-lower "1075.22,-333.89:18" --virgin-mint "1071.19,-328.14:1079.26,
-339.64:2.4:3.8:pins=20,5"`; minted foam/sand/wash at (1071–1079, −328..−340),
teleport ≈ (1074, −336); THE BUILT-IN A/B: the block's own REAL desert beach runs
the west shore, centroid (1061, −358), ~15u around the corner. Real cell → disc 1
only (no mirror; a world re-entry loads it); revert = delete the five deployed
overrides. **Round 2 (playtest 2026-07-15): the beach itself "looks good"; the END
CONNECTIONS read as tiny cliffs** — the radial r18 bank had sunk the flanking coast
beyond the caps (real beach ends die against the TALL lip — the bay-arc grammar);
re-deployed with the CORRIDOR bank (`:8:along=chord` — the sink hugs the beach line,
the flanks keep stock height). **The user's second tell — a SQUARED SEA TILE against
the foam — diagnosed structurally (THE WASH-APRON PROPORTION):** at the real beach
everything within ~13u of the foam is PURE sea2 wash; at the mint, ring-re-banded
sea1 sits at ~4u (a deeper band's animated texture butting the wash = the visible
square). The mint's `wash_reach` lever (now CLI-exposed as `:wash=R`) only applies
on DEEP shores (`deep_shore = no sea2 dropped`) — this window drops 3 sea2 tris (the
real beach's ladder wraps into the corner), so the outer bands stay where stock had
them. The truth underneath: this corner's bathymetry is a NARROW SHELF (deep water
close-in = why no beach grew here naturally); a stock-proportioned apron needs the
mint to RE-PROPORTION the ladder on shelf shores (convert near sea1/sea3 to wash +
push the re-band ring outward — the LADDER-TAPER LAW's mint analogue), **→ THE SHELF
RE-PROPORTION RUNG built same day** (user: "the ends look good now, build the ladder
re-proportion rung"): explicit `wash=R` on a shelf shore now SEEDS whole sea1/sea3/sea5
tiles within reach as planned wash conversions riding THE LADDER-REPAIR FIXPOINT
(plan-then-emit, strip re-emission, every gate) — plus three new fixpoint rules minted
through the (16,5) traces: **THE ROLLBACK RULE** (a pair needing a FRAME-ROW cell — the
repair is border-blind; an in-place re-label breaks border welds — or a FALLEN cell
(proven unlearnable) or a PARTIAL (part,cell) (cut fragments) reverts the shallow-side
conversion instead, monotone, fall-through-to-legacy when nothing is revertible = every
proven build byte-compatible, 47 goldens frozen); **THE COMPRESSED LADDER** (a
rolled-back cell stays convertible DOWN-ladder: wash→sea1→frame-sea3 in adjacent
columns is lawful and real — the east flank's form); **THE ENGULFED-TILE RULE** (a
surviving sea1 whose new edge-set is [] has NO strip form — no such tile exists — and
re-bands to wash, always lawful since es=[] means every neighbour is wash/sea1).
Deployed at wash=13: the square's body IS wash now (rows −87..−89 converted, the sea1
ring pushed to the frame column as the compressed ladder; the NW pocket rolled back
untouched); the residue at the foam line = cut-fragment slivers (lawfully immovable).
Playtest pending. **→ THE LADDER MINT ★ BUILT + DEPLOYED same day** (the user reverted
(16,5) and called the rung): `world-island --beach B0,B1[:W[:S]] --beach-pins BX,BY`
(`islandbeach.py`) replaces the cliff wall along an outline arc with the measured beach
profile (berm → sand band L→S → foam ribbon S→W, chains pinching at the arc's interior
ends against the full-height flanks) and mints the water ladder: the wash collar (a
greedy zip from W to the sea1 ring's lattice staircase, sea2 mains uvs
position-evaluated), sea1 + sea5 rings (1-cell dilation = adjacency lawful BY
CONSTRUCTION; tiles via the learned Wang table + `_strip_emit` with the PINS block's
float dialect — (20,5) is dialect-MIXED, (15,1) clean, so desert pins default needs
care), and THE COVERAGE CUT (the sea4 plane loses only cells the ladder FULLY owns —
16-sample coverage fixpoint; wash tris straying into kept-plane cells drop = the
z-fight law; the pinch tapers keep deep water under them like the flanking coast).
En-route fixes: the pinch anchors moved to the arc's interior ends (the rim-ring
sliver), and beach TRANSITION wall quads pick their diagonal by best worst-lean (the
two ends MIRROR). Deployed: the first BEACH-BEARING minted island — desert, r18 seed
11 @ (288,−1243) block (4,19), beach on the south face (bearings 235–305), pins
(15,1), 396 terrain tris + foam 34/wash/sea1/sea5, all gates clean incl. census 0
MISS; teleport (288,−1243), disc-4 mirrored. Grass identity: BOTH byte-identity
oracles pass (beach=None mints untouched). **Round 1 (playtest): the ladder reads, but
"hard edges around the beach sides" (the coverage fixpoint DROPPED taper wash tris =
straight cuts in the light band) + "the escalating desert section looks stretched"
(single 4.6u berm quads overrun their one cell's mains map and smear at the bleed
clamp). Round 2 fixed both (RAISE-DON'T-DROP: taper wash lifted 0.02u over the kept
plane; THE LATTICE-SCALE BERM: ~2.2u rows, one global row count, pinch-fan end columns
-- the closed-surface gate caught both weld classes). Round 3 verdict: STILL z-fighting
near the edges (the 0.02 lift is too thin; and the taper FOAM's W edge approaches y=0
asymptotically over the kept sea4 = a near-coplanar sliver strip) and "oddly shaped in
general -- doesn't fit the verbatim feel; THE HEIGHT OF THE ISLAND mixed with the slope
of the beach is causing problems" (the user's diagnosis, ringing true: real beach
coasts are LOW -- (20,5)'s backing terrain sits at y 1.56-2.73, and island B's recipe
SANK the mesa rim to a cay before minting; a 3.2 plateau with a carved ramp reads as a
funnel in a drum, not a beach).** NEXT ROUND (the cheap experiment first): mint the
beach islet at `--height 1.6` -- a LOW island = the island-B cay shape with the wall
short everywhere and the berm run gentle; if that restores the verbatim feel, the
productized form is likely "beach arcs want low islands" (a lint/warning) or a local
interior sink behind the arc (the island-B bank_lower INSIDE the mint). For the
z-fight: raise the taper lift to ~0.1 + lift the taper foam's W-edge verts, or clip
the taper tris at the cut boundary (honest but more work). **Round 4 (the stock-true
cay --height 2.7344 + the 0.1/0.05 lifts): WORSE — "still z-fighting, now there's
seams. you're doing the aggressive synthing again"** (the lifted taper tris read as
lit ledges = the lift traded z-fight for seams; the berm band still stretched-noise;
the west transition wall a hard crease). **THE LADDER MINT IS CLOSED AS FALSIFIED
after 4 rounds** — THE FORM LESSON's beach instance, the exact massif_synth
trajectory (each round fixes the named defect and mints a new one, because the mint
reproduces a beach's measured properties, never its look). `islandbeach.py` stays as
the record; the ring/zip/coverage-cut water mechanics remain sound vocabulary.

**→ THE (7,17)→DESERT RETILE (the pivot — carry, don't synth; ★ BUILT + DEPLOYED
2026-07-15, playtest pending)** — user-picked option 1: transplant FF9's only
fully-in-block beach island **(7,17)** (`world-transplant`, the byte-proven vehicle
whose own help text names it) and RE-FAMILY the carried bytes desert via the
translation laws. `island717_retile_census.py` = the feasibility answer, and it is
TOTAL: **(7,17) carries NO painted berm** — its 62/62 ground tris are pure grass
MAINS (the sand back-welds straight onto mains 8/8, and desert beaches mirror that:
their sand welds onto desert mains 86/111), 35/35 wall tris in the rock band, 16
sand tris on the pins, 14 foam tris = topo-relabel-only (30→34, texture universal),
water untouched. The ONLY residual: a 4-tri 2-cell dirt PATH strip stepping down to
the beach (its own u-column [0.8555,0.916], v per-cell) — stock desert has NO path
analogue (sand→mains direct weld), so those 2 cells re-uv as position-evaluated
desert mains (the one non-verbatim decision, 12 uv rewrites, budgeted). Productized
as **`transplant.GroundRetile`** + **`world-transplant --ground desert`**: per-class
uv translation (GROUNDS mains/wall deltas + the SAND_BANDS re-pin over
donor-byte-read anchor pairs — monotone, EXACT on classified pins, per-tier lerp on
conforming verts), event/area/flags bits preserved on every relabel, geometry/
normals/water byte-verbatim, and a STRICT gate: prescan-frozen per-class expected
counts, a recover budget, and ZERO unclassified content (an unmeasured donor class
refuses actionably — study it, don't guess it). Acceptance
`island717_retile_acceptance.py`: 7563 checks, 0 failures; full pipeline dry-run
green (weld 0, census miss 0). DEPLOYED: the ladder-mint bench REVERTED
(`backups/ladder-mint-bench.20260715/`), the desert island at cell **(4,19)**
(shift −8: island ≈ (292,−1245)) + the UNTOUCHED grass control at **(6,19)**
(≈ (420,−1245)) for same-session A/B, disc-4 mirrored. The N-strip nicety: the
(7,16) continent band contributes 12 recover tris that clip away at zero z-shift —
recovered harmlessly, counted honestly. **★ IN-GAME PROVEN 2026-07-15, round 1:
"the desert island looks verbatim, keep both"** — both islands stay deployed; the
beach-on-our-islands prize is CLOSED by the carry (first-deploy pass, zero fix
rounds — against the ladder mint's 4). Open follow-ons (earmarks, not scheduled):
non-beach donors to the other island-class families (snow/canyon need no sand
family). **→ MULTI-BLOCK `--ground` ★ BUILT + DEPLOYED same day** (user-called):
`for_donor` grew `size=` — the prescan mirrors the REGION gather exactly (rect
cells whole + outer-border strips at the region clip planes) and `--ground`
composes with `--size`. The (10,17)+2×2 island-B donor census: a 1×2-data
CLIFF-COAST island (topo 58+0 only — NO sand/beach1/object of its own; the
continent-v1 island B's beach was the MINT's, not stock), so the retile is
mains+wall — the W coverage strip contributes the (9,17) beach's border
fragments (2 sand + 4 foam, cap-tier anchors only), retiled desert exactly as
verbatim would carry them grass. First dry-run CLEAN through every region gate
(prefab-parts, border-census incl.). DEPLOYED desert at target rect (22,18)+2×2 —
data cells (22,18)+(22,19), the empty east column stays true prefab ocean — just
east of the horseshoe massif bench (an offshore desert isle); island ≈
(1442,−1214); disc-4 mirrored. (The near-bench rect (8,18) refused correctly:
(9,18) is a REAL stock block — the target gate checks the whole rect.)
**★ IN-GAME PROVEN 2026-07-15 round 1: "the desert island B looks verbatim,
keep it"** — kept deployed; two donors, two first-deploy passes, zero fix
rounds. The retile arc is CLOSED as a proven verb (single + multi-block).
**→ THE SNOW ISLAND B ★ BUILT + DEPLOYED same day** (user-called): same
(10,17)+2×2 donor, `--ground snow` (topo 0→27, mains dv −0.33691, walls →
the measured ICY band — the first REAL wall set through the icy delta).
The build minted the STRIPS-PARITY rung: with auto strips the W coverage
band drags in (9,17)'s beach fragments and snow lawfully REFUSES (no
measured sand family) — but the desert build's carried counts prove strip
content ALL clips at the frame (shipped bytes = the donor's own tris
exactly), so `--strips none` is byte-equivalent and lawful; `for_donor`
grew `strips=` (the prescan must MATCH the transplant call — expected
counts are exact). Deployed at (17,18)+2×2 — data (17,18)+(17,19), island
≈ (1122,−1214), just west of the horseshoe bench; every gate green incl.
census/border with no strips; disc-4 mirrored. (Target hunt: (10,18)
refused = the donor's own cell; row-18 cols 14-16 are real stock coast —
the gates did the map-reading.) **★ IN-GAME PROVEN 2026-07-15 round 1
("good")** — kept; the icy wall band is real-wall proven; three families
(grass verbatim / desert / snow) on the same donor, three first-deploy
passes. **→ THE CANYON ISLAND B ★ DEPLOYED same day** (the last island-class
family): same donor, `--ground canyon --strips none` + **ROT 180** — the
retile is rotation-invariant (donor-frame apply), and the flip solved the
target hunt: rect (22,17)+2×2 is all stock-ocean but its west column holds
the desert island B — rot 180 lands the data in the EAST column
(23,17)+(23,18), zero writes west, and the flipped silhouette won't read
as a copy of its desert twin diagonally below. Island ≈ (1502,−1154), NE
of desert island B; first REAL walls through the red-rock band
(du −0.69509, dv −0.49722); every gate green; disc-4 mirrored. (Rows 16-17
mid-map probed all real stock — the south ocean band is the bench row for
a reason.) **Playtest round 1: "I don't recall any real canyon tiles with
cliffs this high" → THE WALL-CONTEXT LAW (`family_wall_envelope.py`)**:
a family's wall band is context-keyed, not just atlas-keyed. Map-wide:
canyon's red band = 655 wall tris in 48 faces; exactly 1 borderline face
(3 tris, block (3,7), y −4.8..−3.2) sits BELOW datum — an INTERIOR gorge
wall, not open sea. Zero open-sea coastal canyon walls anywhere on the
map; where Forgotten canyon ground meets the sea the cliffs are topo-49
MURALS (unmintable, the baked-terrain law); grey-band walls under canyon
ground: zero instances. Literal height is in-envelope (real red faces
reach 4.48u vs the donor's 3.91) — the violation is a red wall rising
from open water, which stock never shows. **Canyon therefore has NO
lawful coastal wall dress → a canyon ISLAND is off-language** (canyon
stays lawful as interior/highland ground behind another coast; the
sampler canyon islet shares the violation). *(2026-07-18 map-wide
re-census, `family_wall_envelope.py`: 655 tris/48 faces, 1 below-datum
gorge face — the earlier "748 tris, 0 coastal" reading was a top-8-
specimen-slice artifact, never a map-wide tally; that same slice today
reads 231 tris/27 faces, still 0 coastal.)* **Snow re-verified the
opposite way: 1019 icy-band wall tris across 10 faces map-wide, EVERY
face COASTAL, faces to 6.35u (an 8-face specimen slice reads 272 tris,
all coastal, max 5.73u) — the snow island B is squarely in-language.**
*(2026-07-18 correction: the old "733/733" figure matches neither the
map-wide nor specimen count and is retired.)* **Disposition (user:
"remove both and add the guard"): the canyon island B ((23,17)+(23,18))
and the sampler canyon islet ((15,19)) are REMOVED from both disc trees
(backup `backups/canyon-removals.20260715/`), and THE GUARD is shipped at
BOTH chokepoints** — `build_landmass` refuses `--ground canyon` outright
(a mint's rim is a sea cliff by construction), and `GroundRetile.for_donor`
refuses any coastal-wall donor whose target family's band isn't MEASURED
coastal (`wall_coastal` flags in GROUNDS: grass/desert/snow True (measured),
canyon False, borrows unmeasured). Canyon remains lawful as interior
ground behind a lawful coast.

**Verdict (round 1): the crag cannot be a single-block `world-mountain --donor`** —
donor-side the blob build generalizes cleanly per A2; target-side needed a multi-block
placement scan + split-border emission.

**→ THE MULTI-BLOCK EXTENSION (★ built same day, 2026-07-15).** `carve_mountain` now takes
a donor block LIST/rect (the blob merges in the world frame) and auto-sizes the target: a
blob that fits one block runs the frozen single-block pipeline (the Uaho identity
acceptance passes bit-for-bit through the generalization — the refactor oracle), a bigger
one works over the minimal SPAN of deployed blocks (new tris split at 64u borders via
`split_borders8` — identity welds, exactly how the stock crag itself ships; the apron
welds internal borders per POSITION and tapers only at the span's outer rect; crack gate
+ probes + census span-wide). The crag carry runs GREEN offline (294 tris over a 2×2
span, zip rise 1.05 / ny 0.96 / rigidity 0.7% / apron 4.1° — far inside every envelope)
and is DEPLOYED on a fresh r50 bench island at **(64,−1216)** (`world-island` seed 11 +
`world-mountain --near 64,-1216 --donor 10,5-6`, placed (70,−1218) rot 0; teleport
**(30.5, −1217.5)** face east) — **★ MECHANISM IN-GAME PROVEN 2026-07-15** ("looks
verbatim" + "rim walk is good": the border seams are invisible, the rim walks clean).
The LOOK verdict is deliberately deferred: the crag's foot fringe is painted against
topo-17 DESERT ground and reads foreign on mains grass — the DESERT GROUND-LANGUAGE
study (census → tile decode → a desert island ground → re-seat the crag) is the next
rung; only on native ground can "reads native" be judged.

## Round 4: THE v3 BEND-CARRY (deployed, then rejected -- see the verdict above)

`two_level_v3.py` **DEPLOYED** (1431 tris): the escarpment is now a CARRIED real wall —
donor (17,12)'s ribbon (23.6u tall, 81u run, corr −0.96), every vert/UV/normal real bytes,
(s,d,h)-bent along our crest in 3 shingle-overlapped laps. The offline render shows one
coherent crag wall; all gates clean (census 0 MISS, rule-f 0, moat/verge, probes). The
build minted the v3 carry laws (full statements in the memory): THE MID-DEPTH ANCHOR
(+ THE HULL CLOSURE for bays — an anchor bridges concavities < D_MID), THE WANDER
CORRECTION (d referenced to TRUE crests both sides), THE INTERIOR WINDOW (+ keep
straddlers), PER-KEY SHIFTS never per-tri nudges, THE GHOST REMEDY (idall 4078 = the
engine's own ray-skip list), THE FULL-CELL SEA REVELATION → THE VERGE RULE final form
(outline proximity, signed distances), and RULE-(f) AS A FIX ORACLE. Teleports:
**(226.5,−1137.5)** lowland / **(222.5,−1106.5)** plateau.

**THE WALL MESH ORGANIZATION STUDY (`wall_anatomy.py` → out/wall_anatomy.json)** — the 8
largest interior escarpments answer how real walls are BUILT (full laws in the memory):
courses are SHINGLED FREE STRIPS (zero vertex sharing between courses); TOPS FLOAT under
the grass bevel (zero identity welds at every crest) while FEET WELD identity-exact to the
ground; vertex normals are smoothed UP-LEANING terrain normals (ny med 0.67, p10 0.49,
p90 0.95 — not face normals, not constant); UVs are FRACTIONAL (only 7-29% corner-pure);
70-82% clean ~4×4u quads + 20-30% lone filler tris; and real crest chains are JAGGED
(turn p90 > 90°) — the shave toward fair curves was off-language. ⇒ v3 = BEND-CARRY a
real escarpment strip along our crest: no course/crest welds needed (the shingle laws),
only the foot conforms.

**Playtest round 2: "top looks pretty good" + three findings** (laws in the memory files):
the stuck spot at ~(200,−1125) was THE MOAT LAW (a rule-(f) corollary — the zip welded to
the south chain's band-descending end verts, building a walkable ramp to the waterline;
the mint's Sea4 under-lap became cacheable → the movement-cache-shadow trap; fixed by
trimming chain ends to rim height + the MOAT GATE: every zip vert ≥2.4, verified 0
walkable-below-2.4 points across the corridor band post-deploy). The 2 stretched cliff
tris at (206,−1111) were THE LONG-EDGE TILE SPAN (a 5-8u native crest edge spans several
tile windows but gets one tile; fixed by densifying the crest ring to ≤3u colinear
segments). The "mountain meets the sea" question: free-base termination is measured-real,
but stock tall sea-cliffs wear the coastal band language + a foam outline — our interior-
language-into-water arc is a hybrid; re-clothing it is a candidate follow-up rung.

**Playtest round 1: "looks pretty good" + two issues, fixed and redeployed** (laws in the
memory file): the exact-coordinate teleport (224,−1138) grounded the player UNDER the
terrain — THE LATTICE-EDGE TELEPORT TRAP (a sky-cast at an exactly-lattice x/z can
float-miss both shared-edge triangles → Y=0; teleports are now handed out MID-CELL:
**(226.5,−1137.5)** lowland / **(222.5,−1106.5)** plateau); the east side's crest smears +
hard right angle — THE CONVEX-ONLY CORNER SHAVE (smoothed ±5u turn metric, convex corners
only; raw per-vertex turns cascade down the lattice staircase forever, and shaving a
CONCAVE corner deepens it) + THE FAN FALLBACK (collapsed tile windows at macro corners get
full-width corner assignment instead of arc-lerped u). A `DEBUG_CLASS=1` env renders the
build class-colored (raised/kept/wall/zip) — how the false alarm about the structure was
cleared in minutes.

### The round-3 carry verdict (what forced the two-level shape)

Round-3 playtest verdict on the (17,15) carry: the donor is a **PEAK in situ** — a sharp
crag with one steep walkable topo-13 face, not a flat shelf (user: ugly; the PLATEAU idea
is the keeper). The crag was removed and island F restored pristine. The carry MECHANISM
worked (it rendered as real FF9 rock, being real bytes); the object was wrong — and the
follow-up census minted **THE NO-FREE-MESA LAW**: no free-standing flat-topped mesa exists
on disc 1 (every raised complex is a peak or a block-frame-cut escarpment fragment, rock-
ringed on the order of ~96% by rim per the in-game (17,15) crag verdict; (6,15)'s true shelf
is a RIVERBANK terrace against the river at 15.2). *(2026-07-18 correction: the "74–95% high
rim" figure once cited here has no committed measurement script — `crag_anatomy.py`'s ~74%
measures course-weld, a different quantity; the qualitative law stands, the stat is softened
to the ~96% in-game-verdict reading pending a dedicated rim-fraction script.)*
Flat terraces exist only as EDGES of larger highland ⇒ the two-level build above — the
shape FF9 actually uses.

## Round 2: THE MESA CARRY (superseded by the verdict above — `mesa_carry.py` kept)

**Round-2 verdict on synthesis: three wall-texture conventions failed visually** (mixed
bands → a bright mid-stripe, caught in-game round 1; fractional bottom-edge lerps →
streaks; corner-snapped bridge fans → shag — both caught by the offline render). The
meta-law fired (stop iterating conventions; study or carry) and the mesa SEARCH found the
answer: **REAL carryable mesas exist** — topo-49 wall components that enclose a raised
topo-13 shelf AND land on lowland grass all around, i.e. naturally-bounded blobs. Six
candidates on disc 1; `mesa_carry.py` carries the **(17,15) mini-mesa** (16×16u, wall +
shelf, verbatim geometry+UV+topo) onto island F's centre with the proven carve machinery —
**the CARRY LAW's 5th instance** (beach1 → shore components → canopy → carried streams
pending → the mesa). The bigger (6,15) mesa (36×23, shelf 16.2) needs a larger islet — a
follow-up. Also minted this round: per-ring equal-arc stations + THE CONE-PERIMETER TRAP
(a closed small terrace ring grows +2π·run per course — shared station counts stretch
foot tiles 2×; real plateau edges are long escarpments, not cones).

## The synthesized TERRACE (round 1, superseded — `terrace_build.py` kept as the record)

The composition test for both interior studies, on **island F, the terrace islet** (a new
`world-island` mint at block (3,17), center (224,−1120), r26 seed 15, patchless — island E's
free mains were exhausted by forest+meadows+hill). The terrace: a **mid-shelf** (topo 13,
grass mains, y≈17, r≈6.5 — real shelves are this small) ringed by **three stacked wall
courses** at the real 58° slope (topo 49 — foot-illegal blocks by TOPO, the faithful
mechanism; no ramp per the NO-FOOT-PASS law), textured by the decoded band recipe: crest
row 4 (cols 4–7) → body row 7 (cols 0–3) → base row 10 (cols 6–9), ONE 128px tile per
~4.4u quad, u advancing with the 4-col band wrap. Tile rects are BYTE-READ modal (u0,v0,
du,dv) per id from the decode (typing them from the lattice phase sampled Moguri's
transparent gutters — the PER-BLOCK FLOAT DIALECT law biting again). Foot welds to the
island by the proven carve machinery; the hole ring derives from DROPPED-ADJACENCY (exact —
a geometric band filter caught the compact islet's own coast once-edges). Gates: rect
membership, cracks 0, census MISS=0, shelf centre grounds topo 13 @ 16.74, atlas 0.

## THE DAGUERREO MASSIF ANATOMY — the turning-wall study (`daguerreo_massif_anatomy.py`)

The v4 transplant put a real HORSESHOE massif in our own fork — the first turning/branching
mountain we fully own; every prior wall study sampled straight escarpment runs in aggregate.
Read on the REAL donor bytes (5-6,15-16) (identical to the deployed island at rot0/shift0);
artifacts `out/daguerreo_massif.json` + `out/massif_cols.png` / `out/massif_rows.png`.

**THE SHEET-MASSIF DISCOVERY (the headline): this mountain is NOT the wall class.** The
whole massif (562 topo-49 tris across 4 blocks, y 2.4–31.4) is ONE edge-welded component;
74% of its quads weld vertically to the course below (the 8 big escarpments measured 0% —
shingled free strips); 97% of tris are up-facing (ny>0.3 — no vertical curtains); quad
courses are ~4.3u tall × ~4u wide with plan spacing COMPRESSED on steep faces (NN med
2.62u). ⇒ FF9 mountains come in (at least) TWO construction classes: **ESCARPMENT WALLS**
(shingled free strips on long straight plateau edges — the wall_anatomy class) and
**LATTICE-SHEET MASSIFS** (one continuous welded quad sheet draped over the whole relief,
over the top included — no ridge construction exists; only 34u of knife-edges on the whole
horseshoe). The v3 bend-carry bent a strip-class donor around a closed form FF9 builds as
a draped sheet — the FORM LESSON's mechanical explanation.

**The tile language on a sheet (turn behavior):** it IS the 128px tile language (phase
peakiness 7-9×, uv bbox exactly the known interior wall region — not a mural). Rows =
~4.5u HEIGHT COURSES, turn-invariant around the whole loop (row 10 foot at y 3.6-7.5 →
row 9 → 8 → 7 ascending — the G5 staircase), RE-BASED per façade — against the hanging
bowl's topo-13 rim the wall runs rows 6/5, not the foot course. Cols = the contour
sawtooth, cycling continuously around the closed loop; at SHARP bends (facing delta >35°)
windowed continuation collapses (atlas-adjacent 50%→21%, "other" 31%→56%) into FREE
fractional window placement, with narrower quads (3.0u vs 4.0u med). Straight-run "other"
offsets are NOT noise: repeated systematic deltas ((2.16,3.16)×20 …) = boundaries between
window SYSTEMS (the low ring vs the tall west face). Strips do NOT preferentially break at
bends; filler tris do NOT concentrate at bends (both med ≈ overall).

**Water anatomy:** THE FALLS APERTURE — the terrain wall has a LITERAL 19-edge hole behind
the falls sheets (the falls mesh IS the surface there; 2 further edges were block-frame key
artifacts); the river channel bed is topo-58 (the coastal-lip class reused inland, blocked)
with the water plane inset ~0.5u below the banks and the wall CONTINUOUS behind it. Feet
weld 100% everywhere (grass, bowl rim, forest), dihedral 46-53° (the soft interior crest).

**Stage 2 — THE TILE-TOLERANCE PROBES (`massif_tweak1.py` + `massif_face_render.py`,
in-game + offline 2026-07-13, probes reverted):** two one-quad UV-only swaps on the live
island's west face, both to tiles from the massif's own inventory (only ORGANIZATION broke).
Probe A (same row, col ±2 window break) = INVISIBLE offline close-up and at gameplay
distance ⇒ **THE COL-FREEDOM LAW** — within the right row band the col/window choice is
cosmetically free (the sawtooth is how the painter worked, not a visual constraint; kills
the v3-era organization problem). Probe B (same col, row 9→7 course break) = clearly
visible up close (a pale off-course square) ⇒ rows stay the load-bearing axis.
`massif_face_render.py` = **THE OFFLINE EYE**: a Moguri-textured orthographic elevation
render of a wall face (before/after/marked) — synthesis candidates iterate against it
offline; only finals go to playtest.

**Stage 3 — THE SPUR ★ IN-GAME PROVEN 2026-07-13 ("looks good, i compared to verbatim" —
`massif_spur.py`; kept deployed, disc-4 re-mirrored): the FIRST in-game-proven synthetic
mountain material.** One course of fully synthetic rock bulges the real massif foot outward
3.5u over a 14.9u SW-face window (cell (1,17)); side-by-side against the verbatim wall it
reads as normal rock. The graft recipe: drop footprint grass + the window's bottom-course
quads → the ring = exactly the kept|dropped edges → zip grass-outline→exposed-sheet-edge,
every new vert a ring FLOAT; row-10 tiles (the y-band match), cols free per the col-freedom
law, fractional UVs inside real exemplar-QUAD rects; gates ring-consumed / no new
once-edges / census MISS=0 / the offline eye. Two offline catches en route (no playtest
wasted): single-TRI exemplars smear (use full-tile QUADS) + **THE CLEAN-BOUNDARY GATE** (a
graft window needs ≥1.5u separation between the exposed sheet edge and the grass outline —
the sheet class has no universal clean course line, SELECT for one). ⇒ the `world-mountain`
rung is UNBLOCKED (hill-at-scale geometry + this retile/weld recipe; not yet built).

Full statements + provenance: memory `project-ff9-overworld-interior-topography`.
Shore-side laws: memory `project-ff9-overworld-coast-mosaic` (the LAW INDEX).

## THE STANDALONE WATER-FEATURE CENSUS (★ CLOSED BY CENSUS 2026-07-22 — `standalone_water_census.py`)

Roadmap 5.5: can a SMALL self-contained water feature (a stream / pond / short falls) be
carried onto a minted island **without dragging a mountain along**? The horseshoe proved
falls/river/riverjoint aux parts carry as part of a BIG massif ensemble; the open question
was whether stock holds a water feature whose complete ensemble (channel + aux parts +
banks) closes naturally on ALL sides — no amputation stumps, sources/sinks judged honestly.

**The whole water universe (disc 1):** the water features are named sub-mesh parts —
`river` (10 blocks), `stream` (7), `riverjoint` (6), `falls` (3) — plus the channel-bank
terrain family **topo 62** (480 tris on 10 blocks, **10/10 within one block of a water
part** ⇒ topo 62 IS the carved channel, part of every feature's ensemble). Only **2**
water-topo tris are baked into terrain (single channel markers on (17,14)/(18,13)); there
is **no** pond hidden in terrain — every real feature is a part. (`sea6`/`sea4f` are sea
layers, not features; `volcanocrater`/`volcanolava` = Gulug.)

**THE TERMINATION CENSUS is decisive: 6 water components map-wide, ZERO OPEN tips.** Welding
all water parts into components and classifying each component's two flow-axis tips as
SEA-anchored / MASSIF-anchored / OPEN (far from both), **every single tip is SEA or MASSIF**:

| comp | parts | y-range | tip A / tip B | blocks | reading |
|---|---|---|---|---|---|
| 0 | river+joint+stream | 0.4–2.9 | MASSIF / MASSIF | (18,13)(19,11-13) | valley stream, both ends rock |
| 1 | joint+stream | −0.2–1.0 | **SEA** / **MASSIF** | (16,14)(16,15)(17,14) | lowland river-to-sea — source at massif foot |
| 2 | falls+river+joint | 2.5–26.4 | MASSIF / MASSIF | (19,10-11)(20,10-11) | plateau river + falls |
| 3 | river | 26.1–27.8 | MASSIF / MASSIF | (14,17)(15,17) | highland plateau river |
| 4,5 | falls+river+joint | 15.2–26.0 | MASSIF | (5-6,15-16) | Daguerreo (already carried) |

**Every stock river rises in a mountain** (geographically correct) or runs massif-to-massif.
The closest thing to a standalone lowland feature is **cluster C** (16,14)/(16,15)/(17,14):
a genuine lowland river (y ~0–1, rock ≤16%) with a natural **sea mouth** (riverjoint+beach1
at (16,15), tip 0u from sea) — but its **source is the massif foot** (tip 3.2u from rock, 23
rock tris within 12u; the top-down eye `out/streamC_topdown.png` shows the ribbon ending in
grass at the base of the reddish rock). Excluding the mountain leaves an upstream stump
(water from nowhere); including it drags a mountain — either way it violates the constraint.
It also carries three place-entrances (areas 11/15) and empties into the sea, so a faithful
carry would be a **coastal-river ensemble** (terrain+stream+joint+beach1+sea aligned to an
island coast), NOT the "small self-contained inland feature" 5.5 asked for.

**⇒ CLOSED BY CENSUS — the ENSEMBLE LAW's stream instance, with numbers.** No stock water
feature has a self-contained open-lowland terminus, so there is no standalone stream/pond to
carry. The lawful carriable unit for ANY water feature is the whole **massif ensemble**
(Daguerreo-style, already proven; cluster D at (18-20,10-13) is the next such ensemble if a
mountain-with-falls-to-sea is ever wanted — but that is an ensemble carry, not a standalone
water feature). Do not force a build.

## THE LAST-UNSTUDIED-MESH-PARTS CENSUS (★ DONE 2026-07-22 — `mesh_parts_census.py`)

Roadmap 5.25. The coast/interior arc decoded Beach1 (the foam swash ribbon) and the Sea1–5
shade ladder; four worldmap sub-mesh forms had never been measured. All four decoded offline
with numbers, each with its kit-impact verdict. The census reproduces to the byte, `deployed=false`.

**Engine map (C:/gd/FFIX/Memoria):** the prefab exposes fixed slots `Beach1/Beach2`,
`Sea1..Sea6`, `Sea3_2/4_2/5_2` (`WMBlockPrefab.cs:14-36`); `WMWorldPrefabMaker.cs:38-167` binds
each named sub-mesh to a slot; `WMRenderTextureBank.cs:34-63` gives the animated atlas bands.

**Beach2 — a DISTINCT regional shore, not a second beach.** 4 blocks, identical disc1/disc4:
**(6,3), (7,3), (8,2), (8,3)** — a contiguous far-north cluster. Own material `Beach2Material`,
own animated atlas **`11_128_128`** (4 frames), UV band **u[0,0.5] v[0,0.97]** — DISTINCT from
Beach1's `11_0_128` / v[0.02,0.47] (`WMWorldPrefabMaker.cs:72-81`, `WMRenderTextureBank.cs:37-39`).
Registered form1+form2 right after Beach1 (`WMWorld.cs:711-720`, sets `HasBeach2`). Geometry is
small (3–24 tri per block, y 0–0.78, same swash height as Beach1). **The tell: 4/4 Beach2 blocks
carry NO Beach1** — Beach2 is an *alternative* coast art used in that one region, not a second
beach layered on a block. Terrain under it is the grass/dirt-ecotone family (topos 7/27/49/58).

**Sea6 — an orthogonal special open-ocean tile, not a ladder rung.** 4 blocks: **(8,15), (12,0),
(19,7), (22,13)**. Every instance is a **single ~4×4u quad (2 tri, 6 verts)**, always interior
open ocean, y=0. Own material `Sea6Material`, atlas **`11_192_64`** (only **4** frames vs the
ladder's 6) (`WMRenderTextureBank.cs:61-63`). (⚠ the earlier u-max-scale argument is RETRACTED — u-max is per-MESH, not per-material: sea1 also reads 0.9841 while sea3/4 read 0.9921.) Registered LAST after Sea5 (`WMWorld.cs:766-770`). So Sea6 is not a depth
rung of the shallow↔deep ladder (land < beach1 < sea2 < sea1 < sea3 < sea5 < sea4) — it is a rare
decorative deep-ocean fleck the artists sprinkled in four spots.

**Sea4f — the seamless generic-ocean FILL mesh.** Exactly one exists: **`block[12][0] sea4f`**,
**512 tri = 256 quads = a perfect 16×16 full-cell grid**, y=0. The runtime `SeaBlockPrefab` = the
baked prefab **`Block[12][0]f`** (`WMWorld.cs:1161-1163`) — the tile the engine renders for EVERY
open-ocean cell. There is exactly one generic ocean prefab, so exactly one `sea4f`; (12,0) is its
arbitrary plain-open-ocean home (it also donates its Terrain+Sea4+Sea6 to the empty-block
fallback, `WMWorldPrefabMaker.cs:152-156`). The real `block[12][0] sea4` (510 tri, −2) is the
actual map cell; `sea4f` is its full-grid seamless twin.

**Block 219 = grid (3,9), the Water Shrine.** `Number = row·24 + col`, so 219 = 9·24+3 → **(3,9)**
(matches the `j==3 && i==9` form-2 special-case, `WMWorldPrefabMaker.cs:159`). It is the **ONLY**
block with the `Sea3_2/4_2/5_2` **water-LEVEL form-switch** (stored in the 0_2 LOD; the two forms
are the shrine's raised/lowered water). A small landmass (terrain 22 tri, y→4.5) with the shrine
`object`, ringed by Sea3/Sea4/Sea5. The **early return** (`WMWorld.cs:569-604`) registers only
Object/Terrain (f1+f2) + the WaterShrine effect + Sea3/4/5 (f1) + Sea3_2/4_2/5_2 (f2) then
`return`s — **skipping** Beach1/2, Sea1/2/6, Stream/River/Falls, Volcano entirely.

### Kit-impact verdicts

| Form | Verdict | Evidence |
|---|---|---|
| **Beach2** | **REAL latent gap (low reach)** | `transplant.PARTS` (transplant.py:40) and `GroundRetile.for_donor` (transplant.py:445-462, gathers only terrain+beach1) OMIT beach2. The deploy loop (transplant.py:2656-2664) iterates ONLY `PARTS`, so a part outside it is neither re-emitted nor **blanked** → under a **rotated/shifted** `world-transplant` of (6,3)/(7,3)/(8,2)/(8,3) the donor prefab's original beach2 **free-rides UNROTATED** (a floating shore). Reach is narrow — ⚠ CORRECTED per the adversarial re-verify: `list_coastal_donors(beach_only=True)` INCLUDES the beach2 blocks ('beach2'.startswith('beach'), extract.py:258/267 — the original 'excluded' claim was FALSE); reach stays low because that scan serves the UNROTATED reclaim path (where a free-riding beach2 is harmless/intended) and none of the 4 are qualified `--donor` blocks (transplant donors are user-specified, no auto-scan). **Fix (later):** add `"beach2"` to `PARTS` + `for_donor`'s gather (+ a `Beach2Material` foam-relabel branch). |
| **Sea6** | real but **negligible** | Same `PARTS` omission drops it, but sea6 is one 4×4 2-tri fleck — cosmetically invisible. `SEA_ADJ_LAWFUL`/`OPEN_WATER_PARTS`/the wang gate never reason about it, and the kit never *emits* sea6, so no gate mis-fires. Adding `"sea6"` to `PARTS` would make a verbatim carry byte-complete. |
| **Sea4f** | **decode-only** | The generic full-cell ocean fill; the reclaim divert (Path D) *replaces* the `SeaBlockPrefab` for a reclaimed cell, so no kit path ever reads or targets `sea4f`. |
| **Block 219 / (3,9)** | **decode-only** | s34 Path-C overrides on (3,9) can reach **only** Terrain/Object/Sea3/4/5 (registered before the early return); Beach/Sea1/Sea2/Sea6/Stream/River/Falls overrides are silently dropped. Path D (reclaim) never applies — (3,9) is not `IsSea`. The WaterShrine effect + form-switch are hardcoded to `Number==219`, so the shrine is **uncarriable** (a copy at any other cell gets neither). No kit path targets (3,9). |

The **disc-4 mirror** (`discmirror.py`) is part-agnostic (regex `[a-z0-9]+`, whole-donor
free-ride pin) → it would carry beach2/sea6 faithfully; the mirror is **not** a gap.

## THE COMPOSED-WORLD DESIGN PROBES (★ CLOSED 2026-08-27 — the two stragglers, finished)

Commit `87711d26` shipped the composed-world design round's pipeline (`canvas_census.py`,
`continent_{site_scan,rank,verify,layout,render}.py`, `design_dock_scan.py`) but left **two
probes untracked** — the only two untracked `.py` in this directory, never committed on any
branch. Both are now finished and tracked, and both were verified against the archived
2026-07-25 output before landing.

**`design_band_sweep.py`** — free-radius sweep of the SOUTHERN ARCHIPELAGO BAND, reporting per
named gap (G1 strait / G2 shoal / G3 open reach / G4 east flank / G5 north shelf) the best
mintable centre + `r_max`. It reads `out/world-design/_forbidden_blocks.json`, exactly as its
tracked siblings `continent_site_scan.py:30`, `canvas_render.py:31`, and `continent_render.py:57`
do — so it is not runnable until `canvas_census.py` (which writes that sidecar, line 427) has run
in the same tree. That is stage ordering, not a defect. **Identity acceptance:** re-run against
the archived forbidden set, it reproduces the archived `design_band_sweep.json` byte-for-byte.
As archived it reports the band's only large free pocket as **G4 east flank, r_max 96 at
(1440,−1184) = block (22,18)**, every other gap topping out at r_max 32–40.

⚠ **Those numbers are STALE, and the probe is only as fresh as its input.** `_forbidden_blocks.json`
is not a stock fact — `canvas_census.py:263-264` folds in a LIVE scan of the shared install, so the
archived sidecar is a 2026-07-25 snapshot of a tree that 18+ worktrees write to. Since then the ring
deployed **Lamplight into block (22,18)** — the very block G4's r_max 96 was measured at. Verified
live 2026-08-27: (22,18) now carries a full `Beach1 Object Sea1 Sea2 Sea3 Sea4 Sea5 Terrain`
override set. **Re-run `canvas_census.py` first; never reuse an archived sweep as a siting fact.**

**`design_sandreach_probe.py`** — diagnosed why `design_dock_scan.py` reported Sandreach (blocks
(11,18),(11,19),(12,18),(12,19)) as 116 land samples but **zero** dock aprons. **★ ANSWERED, and
the zero was correct:** land topo is `{17: 88, 58: 17, 34: 7, 32: 4}` over a bbox of only
124u × 56u with y 0.25–6.49 — a steep crag, not a landable shore. Only **2** full 8u pads exist
and both carry ~5u of relief. Three independent blockers: topo 17 is highland, which **THE
BAKED-TERRAIN LAW** makes a hand-painted mural with no tile language (so **THE BAKED-TERRAIN
REFUSAL** means a dock apron cannot be morphed in either); topo 58 is the cliff lip, which **THE
ENGINE FOOT-WALK TABLE** lists as foot-ILLEGAL; and no pad meets the low-relief admission.
Given a `--src` source seam (snapshot dir vs the live install) so the answer survives install
drift — verified both ways: the seam reproduces the live numbers exactly, and an empty snapshot
dir yields 1089 MISS rather than silently falling back.

**En route — the judgment's horseshoe open question, ANSWERED.** `design_judgment.json` flagged
that the horseshoe/crag bench at (18-20,17-19) had no Falls/River/RiverJoint files and every
`Donor.txt` reading `0,0`. Re-checked live 2026-08-27: **still true**, across all 11 deployed
blocks (18-21,17-19), which carry only `Beach1 Object Sea1 Sea2 Sea3 Sea4 Sea5 Terrain`. So the
live bench is **NOT** the 2026-07-15 ENSEMBLE CARRY described above — that one deploys the aux
water parts *and* a `Donor.txt` divert to a part-carrying donor ((5,15) has all five transforms).
With `Donor.txt` = `0,0` the divert points at a block that has no such transforms, so per **THE
EFFECTIVE-PREFAB ORACLE LAW** those aux overrides would not bind even if the files were restored.
The bench was evidently re-deployed by a later plain island/transplant pass. Not a mystery, and
not a data-loss finding — but the ensemble carry must be **re-run** if the horseshoe's river/falls
system is wanted at that site.

## THE ALDERMARCH MINT COMMAND IS UNSAFE TO RUN AS RECORDED (★ 2026-08-27)

`continent_layout.json` records an un-run mint for Design B's Aldermarch continent:

    world-island --center 176,-176 --radius 96 --lobes 3 --seed 31 --ground grass --height 3.2 --patches 3

**Do not run it at that centre.** Re-validated 2026-08-27:

* **The lane is fine.** All 7 flags still exist unrenamed (`cli.py:9027` parser, `_cmd_world_island`
  at `:4661`), and a from-scratch multi-lobe GRASS `world-island` is *not* a falsified lane —
  `SYNTHESIS-RECONSIDERED.md` (2026-07-29) puts this verb in its PASSES column by name, and it was
  playtest-confirmed twice AFTER the design round (R3 Lamplight r44; the R4 bench, a 3-lobe mint).
  None of the §8 falsifications reach it: **THE LADDER MINT** binds `--beach` only (not passed, and
  the CLI now banners it at `cli.py:4676-4683`); the **dunes size class** binds the dunes family and
  is a floor this 19-block mint is far above; **from-scratch massif SYNTHESIS** is answered by the
  layout's own `world-mountain --donor` carries, which are the prescribed replacement.
* **The SITE is dead.** 6 of the mint's 19 footprint blocks — **(1,1) (1,2) (1,3) (2,1) (2,2)
  (2,3)** — are already occupied on **both** Disc1 and Disc4 by the owner-confirmed **R4 bench
  island** (`REVERT.md` §25.3, built 2026-07-26, one day after the design round). Verified live: 8
  override files per block per disc.
* **⚠ And the siting gate cannot see it.** THE OPEN-OCEAN TARGET LAW (`island.py:979-1000`) tests
  `_real_block_parts` (`island.py:930-942`), whose docstring is explicit that it reads *"The REAL
  game's per-block mesh assets"* — via `transplant.world_tris` against the **stock** disc tree. It
  never looks at the mod folder. All 19 blocks are stock-open-ocean, so the gate passes, and
  `island.py:1013-1046` writes Terrain + a Sea4 cut + blanking stubs + `Donor.txt` per footprint
  block, auto-mirrored to Disc4 — over the R4 bench's carved canopy, hill displacement, Sea4 cut
  and coast-nav classes. That is a breach of **THE ACCEPTED-CONTENT ADDITIVE CONTRACT**, the
  round's one checkable respect-mechanism. (`canvas_census.py:50-66 NAMED_BENCHES` has also
  drifted — it does not list the R4 bench blocks; a re-run catches them only via its live scan.)
* **The SECOND gate would not stop it either — but not for the reason the first one fails.**
  `mesh.deploy_override` (`mesh.py:328-380`) does carry a real safety net: THE DEPLOY LEDGER + THE
  OWNERSHIP REFUSAL, and `backup=True` is the default, so differing bytes ARE parked as
  `<name>.bak-<ts>` before any overwrite. **The overwrite is therefore recoverable, not silent** —
  an earlier revision of this section said "unconditionally, no backup", which was wrong.
  The refusal itself is disarmed here by its own bootstrap clause — see the next section.

**Status: SUPERSEDED, not merely stale.** The judge shelved Aldermarch the same day it was drawn,
conditional on two unblocks that are both **still unmet** — THE SEAM-WRAP GAP (`island.py:186-214`
`_split_at_borders` still computes `bx0` with no modulo and no wrap branch) and a coast-smoothness
recalibration that does not exist anywhere in the repo. The owner question that would ratify it
(`open_questions_for_the_owner[3]`) was never answered, and `aldermarch` / `(48,-240)` return zero
hits repo-wide. Reviving it means: re-run `canvas_census.py` against today's install, RE-SITE, add
the required `--mod-folder` (the recorded string is design notation, never a copy-paste line), and
get owner ratification first.

## THE DOCK SCAN COUNTED ITS OWN BLIND SPOTS AS SEA (★ FIXED 2026-08-27)

`design_dock_scan.py` sites dock aprons by asking "is there open water within 24u?". Its
classifier defined water as the **complement of land**:

    land  = {k: v for k, v in grid.items() if v[1] in LAND_MESH and v[0] > 0.25}
    water = {k for k, v in grid.items() if k not in land}

so every **MISS** — a sample where the ground query found no mesh at all — was counted as
water. `miss` was computed on the next line but only ever reported as a count. A candidate
could therefore be admitted because a hole in the *measurement* sat within 24u, not because
real sea did. In the archived 2026-07-25 run the counts are material: Tidefall `n_miss=256`
against `n_land=561`, Larkspur `n_miss=768` against `n_land=366` (~24% of that island's grid).

**What the MISSes actually were — not holes in deployed geometry.** `ISLANDS` lists an
island's blocks, but `scan` sweeps their bounding **rectangle**, and these block lists are not
rectangles. Tidefall's bbox holds 6 blocks against a 5-block list; the odd one out, **(8,18)**,
has no override in the mod folder, so nothing loads and all 16×16 = **256** of its samples MISS.
Larkspur: **(9,8), (9,10), (11,10)** — 3 × 256 = **768**. The arithmetic reproduces both archived
counts exactly. So a MISS here was never a hole in deployed geometry — it was ground the probe
declined to *measure*, because it read only the mod folder's overrides and an unmodded block has
none. (Part 3 below goes and measures it. It is all ocean — but that is a finding, not the
assumption the old code was making.)

**The fix is in three parts, and the last removes the blind spot entirely.**

1. **The sweep is scoped to the island's own blocks.** The lattice is still laid over the
   bounding box, but only points inside the **closed** span of a block that loaded are queried —
   closed, because a block's mesh reaches its own edge verts, so the coastal rim is measured by
   the block behind it. The probe no longer asks a question it cannot answer, and **MISS recovers
   its census meaning**: a MISS is a *real* hole, and `n_miss` is a hard-zero gate that prints a
   `GATE FAIL` line if one ever appears.
2. **MISS is excluded from `water`**, and a MISS within the 24u admission envelope
   **disqualifies** the candidate — a dock is exactly where the boat hull and the landing apron
   meet.
3. **The stock map is composed underneath** (`load_world_meshlist`, default on; `--no-stock`
   opts out). The mod folder holds only *overrides*, so reading it alone left every un-overridden
   block blank. Layered the way the engine layers a cell — the loose override if present, else
   **the game's own asset for that block**, else the shared **`SeaBlockPrefab`** for a cell with
   no assets at all (stood up with the game's one full-cell deep Sea4 plane, hole-filled, exactly
   as `island._sea_plane` does) — there is nothing left for the probe to be blind to.
   **`n_unmeasured` is 0 on all five islands.**

The `unmeasured` class survives for `--no-stock` runs: never queried, never water, never
disqualifying — the probe's own blindness is not evidence of a defect on the ground. The JSON
records `miss_xz`, `unmeasured_xz`, the per-block provenance (`blocks_mod` / `blocks_stock` /
`blocks_open_ocean`) and `blocks_no_mod_override` (a declared island block whose own override is
missing — a data defect), not just counts; the archived run could not be audited after the fact
because only the count was kept.

**What proves the layering is the right way up**, two ways. Composing stock underneath leaves
`n_land` byte-identical on all five islands (3064 / 561 / 116 / 589 / 366) — if a stock sea part
were winning over a mod `Terrain` override anywhere, the land count would collapse. And run
against an **empty** mod folder with only the stock layer, all five footprints read **0 land /
100% water / 0 candidates**: every one of these islands is deployed onto true open ocean, so
every square of island land in a real run comes from the override layer and stock never wins over
it. Parts 1–2 are silent on real data (`n_miss` is 0 everywhere), so `--selftest` exercises them
on synthetic input; part 3 fires on real data and is pinned by those two measurements.

**Re-derivation — A/B against one pinned snapshot** (`--src`, the seam added to
`design_sandreach_probe.py` in `35388a8d`; snapshot + all runs archived under
`backups/world-design.dockscan-refix.20260827/`). `--legacy-water` restores the *whole* pre-fix
probe — bbox sweep, MISS-as-water, no disqualify test — and reproduces the archive on every count
(Tidefall 561/1056/**256**/136 · Larkspur 366/2035/**768**/141 · Grimhorn 589/1812/0/210 ·
Sandreach 116/973/0/0) and on every candidate's identity, order, `water_dist`, `relief` and `y`.

⚠ **One real drift, fully explained.** Four samples read `topo` **59** where the archive read
0/17: (48,−1160) Ashvale · (420,−1224) Tidefall · (1204,−1184) Grimhorn · (700,−608) Larkspur.
Those are exactly the four **R2 quay beacon anchors** (`southern-ring/REVERT.md:1211,1307,1373`),
deployed 2026-07-26 — the day *after* the archive — and topo 59 is their terrain-hull collision
class. None is one of the four grafted dock coords. This is precisely the drift `--src` exists to
pin, and it is the reason a raw re-run against the live install is not a comparison.

**THE DEFECT WAS REAL BUT INERT ON THIS DATA.** Water falls by exactly the miss count (Tidefall
1056 → 800, Larkspur 2035 → 1267) and **not one candidate moves** — 0 added, 0 dropped, 0
`water_dist` changed, on all five islands, under the classifier fix *and* under the re-scoped
sweep. Falsified directly rather than inferred: re-running the admission test against the
unmeasured samples **alone** admits **0** candidates on Tidefall and **0** on Larkspur. A handful
(5 Tidefall, 8 Larkspur) do sit within 24u of unmeasured ground, but each also has real sea
within 12u.

**The re-scope and the stock layer are payoffs in gates, not in verdicts.** Scoping the sweep
left the candidate list on all five islands **identical**; composing stock underneath left it
identical **again**, and restored the full bbox as measured ground. Both fix how the measurement
is *constructed*, not what it concludes. What they buy is two gates that now mean something:
**`n_miss` is 0** on all five islands (and means what the placement census means by it), and
**`n_unmeasured` is 0** — there is no longer any ground the probe declines to look at.

**And the measured answer to what the holes were: all 1024 of them ARE ocean.** (8,18) has real
stock ocean geometry — Sea3 (6 tris) + Sea4 (474) + Sea5 (32), tiling the cell exactly; (9,8),
(9,10) and (11,10) have *no* stock assets at all and are true open ocean off the shared
`SeaBlockPrefab`. With that layer composed, Tidefall's water returns to exactly **1056** and
Larkspur's to exactly **2035** — the archive's own numbers. ⚠ **So the pre-fix probe's assumption
was factually right, and that is the least reassuring possible outcome:** it was still an
assumption, it could just as easily have sat over stock *land*, and in that case every dock
candidate it admitted on their strength would have been fiction. The numbers are unchanged; what
changed is that they are now measured, and the probe can no longer be right by luck.

**All four grafted dock coordinates SURVIVE**, each on real sea at 12u: **(272,−1168)** Ashvale ·
**(412,−1224)** Tidefall · **(1204,−1192)** Grimhorn · **(700,−616)** Larkspur (`unmeasured_dist`
29.12u). Independently of this probe, (412,−1224) was already found unbuildable in play — the
ring's R2 moved that trigger to **(420,−1232)** because the beacon hull crossed the (6,19)/(6,18)
seam (`southern-ring/DESIGN.md:44-45`); that verdict stands and is unaffected.

**Seam verified, as `design_sandreach_probe.py`'s was.** A default (live install) run is
byte-identical to the snapshot run apart from the recorded `_source`, and an **empty** `--src` dir
does not silently fall back to the live install — with `--no-stock` it reports every sample
unmeasured, and with the stock layer on it reports the base game (all ocean, per above). Note the
seam pins the **mod** bytes only; the stock layer comes from the game's own assets, which no kit
path writes, so it does not drift.

⚠ **What remains.** (1) **One layering case is not modelled**, because it does not arise on this
island set: a cell carrying a `Donor.txt` divert takes its un-overridden parts from the **donor's**
prefab, not its own. Measured here, every stock part under every mod-overridden block *is*
overridden, so nothing free-rides and the question never comes up — but it would on an island that
leaves parts un-overridden, and `load_world_meshlist` says so at the call site. (2) `candidates`
is still capped at 400; `n_candidates` carries the true total (Ashvale: **562** real, 400 listed),
which the archived run did not record at all.
## THE LEDGER COVERAGE HOLE (★ 2026-08-27 — `ledger_coverage_audit.py`)

Chasing "what would have stopped the Aldermarch overwrite" turned up a better answer than a new
gate: **the mechanism already exists, and it is 98% unarmed.**

`mesh.deploy_override` (`ff9mapkit/ff9mapkit/world/mesh.py:328-380`) carries THE DEPLOY LEDGER +
THE OWNERSHIP REFUSAL (audit rec 6) — every write appends a line to `<mod>/.ff9world.jsonl`, and
before overwriting DIFFERING bytes it refuses when the on-disk sha256 matches no ledger entry for
that cell+part+write_disc. It is well built, `backup=True` parks `.bak-<ts>` first, and it has
fired for real (the rec-16 compose smoke — island mint → coastnav stamp → re-mint refused *our own*
bytes as foreign, which is why `record_ledger_write` exists).

**The hole is its bootstrap clause**, `mesh.py:368`:

    if shas and cur_sha not in shas and not force_overwrite ...

`if shas` makes a cell+part with **no** ledger entry permissive — and the ledger is write-side
only. There is no adopt/backfill path anywhere in the kit (`grep adopt|backfill` over `world/` +
`cli.py` returns nothing), so it can never learn about content it did not itself write. Anything
deployed before the ledger shipped, or by any writer that bypasses `deploy_override`, is invisible
to it **permanently**. That is not a bootstrap window; it is a standing hole the size of the
pre-existing install.

Measured live 2026-08-27 on `FF9CustomMap-world`:

| write-disc | overrides | PROTECTED | DIVERGED | UNPROTECTED |
|---|---|---|---|---|
| Disc1 | 437 | 0 | 0 | **437** |
| Disc4 | 438 | 0 | 0 | **438** |
| Disc9 | 395 | 25 | 1 | 369 |
| **total** | **1270** | **25 (2.0%)** | 1 | **1244 (98.0%)** |

The ledger holds 113 lines / 26 keys, **all `write_disc: 9`**, all kit 1.0.0b17. So the refusal
protects 25 files on the Path D sentinel disc and **nothing at all on the real discs** — every
owner-confirmed playtested island included. Plus **177 `Block[X][Y] Donor.txt` sidecars are
outside the ledger's scope entirely** (`deploy_donor_sidecar` never ledgers), and those are
load-bearing: Donor.txt picks which real coastal prefab the s34 divert renders.

One row is **DIVERGED** right now — Disc9 (2,17) Terrain, 1 ledger entry, sha matching none. The
refusal would fire there today. That is the non-ledgered-in-place-writer class the
`record_ledger_write` helper was added to close, so it is worth finding which writer did it.

**Calibration (the instrument can fail).** Three controls, all passing: (A) a verbatim snapshot
through the `--src` seam reproduces the live disc-9 numbers exactly; (B) appending **one byte** to
a PROTECTED file flips it 25/1 → 24/2 PROTECTED/DIVERGED; (C) removing the ledger flips all 395
to UNPROTECTED. The classifier genuinely depends on both the bytes and the ledger.

**⚠ CORRECTION (same day, after an adversarial pass): a backfill is NOT the fix, and would make
this hazard WORSE.** The obvious move — one pass stamping an `"via": "adopt"` row per unledgered
file — was refuted. Adopting converts *"unknown provenance, so an overwrite is at least
unexamined"* into *"kit-owned, therefore an overwrite is legitimate"*: the refusal fires only on
bytes matching **no** row, so giving every file a row makes every subsequent overwrite pass the
gate silently. It is strictly more surface than the real fix and catches strictly less. If an adopt
pass is ever wanted for provenance reasons, its rows must be tagged `"via": "adopt"` **and the
refusal must treat an adopt row as REFUSE-not-permit** — a semantics change, not a backfill.

**The ledger is good for ATTRIBUTION, not occupancy.** The occupancy hazard belongs to a different
mechanism entirely — THE MOD-OVERWRITE GATE, next section. Two real fixes came out of this: the
disc mirror now ledgers (`66436348`, which buys attribution — the mirror still writes without a
backup), and the mint lane now has a genuine occupancy gate.

## THE MOD-OVERWRITE GATE, BACK-PORTED (★ 2026-08-27) — a fix that existed here for six weeks

The Aldermarch finding has a root cause sharper than "the gate reads the stock tree", and the repo
had already written it down. `transplant.py`'s `_mod_overwrite_gate` docstring:

> **THE MOD-OVERWRITE GATE (2026-07-15, the dunes-islet incident): the real-target gate reads STOCK
> data only, so a target cell already holding a PRIOR MOD DEPLOY (a minted islet, an older
> transplant) sailed straight through and was silently overwritten.**

And `island.py`'s own comment above THE OPEN-OCEAN TARGET LAW says it is *"the world-transplant
gate, **ported here 2026-07-12**"*. So the mint lane copied the gate **three days before the fix**,
and the fix was never propagated back. Same class, same file family, unfixed for six weeks — which
is exactly why `world-island` at the recorded Aldermarch centre reads all 19 footprint blocks as
"free" while six of them hold the owner-confirmed R4 bench on both discs.

**What was NOT done, and why.** The obvious move — port `_mod_overwrite_gate` itself — was killed
on measurement. It has a donor hatch: a cell whose `Donor.txt` names this deploy's own donor counts
as a re-deploy and passes. `island.py`'s `DEFAULT_DONOR = (0,0)` and all six Aldermarch collision
blocks carry `Donor.txt = 0,0`, so the gate would have returned **ok** on the very case it was
meant to catch — donor identity is not deploy identity. Its file scan also lacks the extension
filter, so it counts parked `.bak-<ts>` files as occupancy.

**What was done.** `fuse.py`'s `_existing_overrides` was the better reader (it carries the
extension filter, audit rec 6) but was wired at exactly one call site. It is now
`mesh.existing_overrides`, living beside the write seam so there is **one** occupancy reader in the
kit rather than one per verb, and `island.landmass` gates on it before any write, with
`allow_overwrite` / `--allow-overwrite` as the deliberate hatch. `fuse`'s `[[island]]` runner now
threads that flag through too — it was calling `I.landmass` directly and bypassing compose's own
occupancy check entirely.

**Verified statically, no game launch.** Five new tests in `test_world_island.py`, all hermetic
(tmp game root, no install, no templates — occupancy is a filesystem question): the refusal with
stock stubbed to *free*, which is the blind spot the law cannot see; the `allow_overwrite` waiver;
a regression pin that parked `.bak-*` files do **not** trip the gate; that the gate reads the
**write** disc, not the read disc (a row on the wrong disc would look populated and protect
nothing); and that `fuse` and `island` share one reader object so they cannot drift apart again.
Non-vacuity proven the house way — disabling the gate turns exactly the two refusal tests red.
Also fixed `match=r"REAL world block.*(3, 1)"` in the pre-existing test: unescaped parens are a
regex **group**, so a message that lost its parens passed.

**Still open — the test that owns the law is mocked.** `test_landmass_refuses_real_world_blocks`
monkeypatches `_real_block_parts` with a stub, so it proves the plumbing and can never observe what
that function actually reads. That is why the stock-blindness survived six weeks of green suites.
The new tests cover the occupancy half; an install-gated test driving the real `_real_block_parts`
against a known stock-occupied block is the remaining piece.

## THE GATE, EXTENDED TO THE WHOLE LANE (★ 2026-08-27) — and the half that must NOT be a refusal

The back-port above fixed one lane. An audit of all **14 write-capable entry points in `world/`**
found only three gating on the mod tree at all (`transplant.transplant_region`,
`fuse.compose_layout`, and now `island.landmass`). Extending the gate to the rest turned up a
distinction the original framing did not have, and it is the load-bearing result of this pass.

**THE READS-THE-MOD-TREE TEST.** A writer that **SYNTHESIZES or CARRIES** its bytes consults the mod
tree nowhere, so a target another deploy owns is replaced without a word — that is the dunes-islet /
Aldermarch defect, and it wants a **refusal**. A writer that **READS the deployed override and writes
it back** overwrites an already-deployed cell *by design, on every legitimate run* — there a refusal
is a wall, not a guard rail. The audit note that opened this task read *"each reads only the stock
tree or nothing"*; that is true of four of the eight named writers and false of the other four, and
the four it is false about are exactly the four that must not refuse.

| writer | reads the mod tree? | verdict |
|---|---|---|
| `terrain.reclaim` | no — synthesizes | **REFUSE** + `--allow-overwrite` |
| `terrain.coast` | no — carries donor bytes | **REFUSE** + `--allow-overwrite` |
| `water.water` / `deploy_verbatim` / `reproduce` | no | **REFUSE** + `--allow-overwrite` |
| `water.deploy_island_sea` | no | **REFUSE**, scoped to the SEA parts |
| `interior.deploy_mountain_parts` | yes (`read_deployed_blocks`) | **WARN ROW** |
| `interior.deploy_changed` | yes (`read_deployed_blocks`) | **nothing** — a warn would be vacuous |
| `entrance.author_entrance` | yes (`read_block_stacked`) | **WARN ROW** on `--fresh` |
| `entrance.extend_nameplate_band` | yes, and writes `.eb`, not block overrides | **out of scope** |

Three of those rows are worth their own sentence.

- **`deploy_island_sea` is the one place whole-cell scope is wrong.** It lays sea *around* an island
  whose LAND `Terrain` the caller itself just wrote on those very cells, so an unscoped read refuses
  on the deploy's own co-tenant. `mesh.existing_overrides` therefore gained an optional `parts=`
  scope — narrowing THE one reader rather than minting a second one at the call site that needs it.
- **The interior warn is not the obvious one.** "You are editing a deployed cell" would fire on 100%
  of runs. The real hazard is narrower: `deploy_mountain_parts` writes carried content **or a hidden
  blank** for every `ENSEMBLE_PART` and never reads those parts back, so a prior deploy's `Object` —
  a `world-entrance` building on a span block — is erased in silence. That is what the warn names.
- **`extend_nameplate_band` has no cells.** It splices func-0xB in the dispatcher `.eb.bytes`, and it
  already carries a *better-fitted* guard than occupancy: idempotent skip, backup, and an outright
  refusal of any arm section matching neither the stock nor the extended template. Nothing to add.

**One gate now, not one per verb.** The refusal moved into `mesh.mod_overwrite_gate`, beside
`existing_overrides` and the write seam; `island.landmass`'s inline copy calls it. Seven call sites,
one implementation — the hole survived six weeks precisely because each lane owned its own copy.

**Two mechanical rules the gate has to obey, both pinned by tests.** It runs over the WHOLE cell list
at the public entry, never per-cell inside the deploy loop (`water._deploy_ocean_cell` deploys one
cell at a time; refusing at cell 3 of 5 leaves a half-deploy). And it reads the **write** disc —
`target_disc`, engine patch s74 — because a gate on the read disc looks populated and protects
nothing.

**Verified statically, no game launch.** 23 hermetic tests in
`ff9mapkit/tests/test_world_mod_overwrite_gate.py` (tmp game root; no install, no templates), plus an
install-gated pin that `author_entrance` actually *calls* its note — the c39ea162 lesson was that a
helper proven alone and never proven CALLED is the same shape of nothing. Non-vacuity the house way:
each gate disabled in turn turns exactly its own tests red, nine for nine, and both `parts=` scopes
likewise. Domain green: 886 passed / 6 skipped across `tests/test_world*.py` + `test_discmirror*.py`
+ `test_navimap_worldmap.py` + `test_cli*.py`.

**One pre-existing test was re-scoped, not loosened.**
`test_discmirror_auto.test_hermeticity_mocked_deploy_calls_never_touch_a_real_install` asserted that
a writes-mocked `water()` never resolves `config.find_game_path` — a proxy for "no mirror pass ran".
The occupancy gate is a legitimate new READ of that root, so the bar is now stated in two halves:
with the gate stubbed the original ZERO-resolutions law holds verbatim, and with it live there is
EXACTLY ONE and still no mutation. (An audit's scope is part of its calibration: a gate that predates
a new degree of freedom scores it against assumptions it never made.)

**Still open.** `terrain.reshape` and `transplant.morph_in_place` remain deliberately ungated and
un-warned. They are in the same in-place class as the interior verbs, but neither blanks a part it
did not read, so there is no analogue of the `ENSEMBLE_PART` hazard to name — if one is ever found,
the warn belongs there too, never a refusal.
