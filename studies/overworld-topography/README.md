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
| dirthill | 38 | (0.45703, −0.20215) | (−0.27127, −0.02066) | wall = THE DESERT WALL VERBATIM (measured stock adjacency) |
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
flats41 = pale fine sand; 0% blank texels everywhere). **PRODUCTIZED same day**:
`grassland.GROUNDS` grew scrub/dirthill/snow/canyon/flats (walls: dirthill = its real
measured desert wall; scrub/flats BORROW the desert wall — an authoring choice, stock
never coasts them), `--ground` choices now track the registry on `world-island` +
`world-mountain`, constants pinned in `test_ground_families_registry`; both byte-identity
oracles pass unchanged (grass/desert entries untouched). **THE GROUND SAMPLER deployed
same day (playtest pending):** five r22 seed-11 islets in the row-19 open ocean, one per
family, one block each, all gates clean, disc-4 mirrored — scrub (480,−1248) block (7,19)
· dirthill (608,−1248) (9,19) · snow (864,−1248) (13,19) · canyon (992,−1248) (15,19) ·
flats (1120,−1248) (17,19). First visit needs a world re-entry (new blocks); disc 4 a
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
when filled — scrub is a TRANSITION vocabulary, not a fill · **dirthill = usable but
reads as forest-canopy top, rim dip doesn't line up** (user: likely the Black-Mage-
Village area brush; census slope med 30° — a SLOPE vocabulary, stock never shows it
flat-at-scale) · **flats = ground reads good, but an INTERIOR type — doesn't blend with
the coastline** (the borrowed desert rim lip; the ground fill itself ★ verbatim-checked
at (1242,−294) blk (19,4) — "checks out"). Encoded as `GROUNDS[..]["cls"]`
island/transition/slope/interior + a CLI mint note + `test_ground_families_registry`.
**ALL FIVE sampler islets are KEPT deployed** (user, 2026-07-15) — the row-19 reference
exhibits for every family.
The future consumption of the three non-island families = mixed-biome landmasses
(scrub as the grass↔dirt seam, dirthill on carved slopes, flats as interior plains).

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
on disc 1 (every raised complex is a peak or a block-frame-cut escarpment fragment with a
74–95% high rim; (6,15)'s true shelf is a RIVERBANK terrace against the river at 15.2).
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
