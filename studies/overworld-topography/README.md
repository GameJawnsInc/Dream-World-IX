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

Full statements + provenance: memory `project-ff9-overworld-interior-topography`.
Shore-side laws: memory `project-ff9-overworld-coast-mosaic` (the LAW INDEX).
