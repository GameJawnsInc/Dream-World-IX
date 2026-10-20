# `world-river`: carry a stock river onto a kit island -- the build plan

**Status:** signed off as written, with the five recommended answers (2026-10-19). **Rung 0 is DONE** (offline,
2026-10-20; see "Rung 0 result" below). **Rung 1 is DONE** (offline, 2026-10-20; "Rung 1 result"). **Rung 2 is DONE** (offline, 2026-10-20;
"Rung 2 result"): every gate green on cluster C. **Rung 3 is DONE** (offline, 2026-10-20; "Rung 3 result"): written to a
scratch folder, B1 green on the bytes, W1 green bar one cliff-corner band step, the render reads as the bay. **Rung 4 is
CLOSED** (in game, owner-passed, 2026-10-20). **The CLI verb is WIRED and LIVE, owner-passed** (2026-10-20; "The CLI
verb" below). The evidence
is in `RECON.md` (R0, R1 rounds 1-4); this file is the build.

## What the verb does

`world-river` carries the stock lowland river at cluster C onto a kit island. Cluster C is the river from the
escarpment foot to its mouth in a beached cove, at blocks (16,14)-(17,15). The verb is a COMPOSITION:
- **Verbatim:** the river, its banks, its bridge, the cove, both beaches and the island in the cove, carried as stock
  bytes.
- **Minted:** a kit island grown round them, with the existing island mint.
- **Joined** to that island at exactly three kinds of seam:
  - the lawn ring: the land zip, proven machinery;
  - two cliff join columns, where the kit's wall meets the stock lips;
  - a water seam across the cove's mouth: the knit, proven rim-retile machinery.

Every other surface is stock. Those three seams are the authored surface, and each gets a gate and an in-game check
(THE DEFECT FOLLOWS THE AUTHORSHIP).

```
py -m ff9mapkit world-river --mod-folder F --at DX,DZ|auto [--dry-run] [--no-apron] [--skip-mirror] [--area N] [--donor cluster-c]
```

`--at` places the fragment by translation only: rotation 0 in v1, the offset a multiple of 4u so every water tile
stays on the lattice (T0), and a whole 64u block (T1: the write splits per block). The whole composition must land on
open ocean. As wired, the apron is ON by default (`--no-apron` opts out): the in-game-proven build ran it.

## What is already proven (offline; RECON.md)

- **The unit is wider than the parts.** The river's lawful unit is:
  - Stream + RiverJoint;
  - the 188 topo-62 banks;
  - the Terrain water tri that closes the source (IDALL 4044);
  - the bridge (40 tris, a walkable topo-52 deck).

  Seated into a kit lawn it is clean on the land side: 0 cracks, 0 introduced misses, skip parity 0, zip chord 8.25u.
  The apron is not needed on a level bench.
- **THE BANK SKIP LAW is in the kit.** `_strip_dispatch` keeps the IDALLs the ground query skips, and
  `placement.skip_parity_gate` refuses a carry that flips one. On cluster C the old strip would flip 177 of 188 banks.
- **The cliffs match.** The bay's two rocky lips and the kit's minted wall are one language: slope 70.9-72.8 vs
  72.7 deg, the same V rows, the same U density. Join columns at the kit's 3.2 crest exist:
  - E: crest (1140.46, 3.11, -1028.0) over base (1141.11, 0, -1028.0), u 0.8242;
  - W: crest (1039.77, 3.29, -1084.39) over base (1040.0, 0, -1083.34), u 0.752.
- **The fragment can cut no component** (THE MINIMAL FRAGMENT). Forests, the tower and the escarpment are left home,
  not cut. One correction: the seaward boundary must route round the island, not cut straight across it (RECON R1,
  round 4).
- **The eye can see it.** `world-render --stock` draws water parts and free-riding donor parts, calibrated against
  in-game stills.

## The pipeline

Each step is a pure function returning its result plus a report; deploying is a separate final step. Refusals carry
the point or edge where they fail. Those are two of the overworld-editor habits (`../../overworld-editor/PLAN.md`),
built in from the start.

1. **`river.fragment(donor)` -> the fragment.** It promotes `ensemble.py` + `closure.py`.
   - **The unit:** the parts, plus every welded topo-62 bank, Terrain water tri and Object.
   - **The cove assembly:** water and beach behind the seaward boundary; lip, sand and beach closed along the coast; and
     every land component standing in the cove taken WHOLE, its shallow ring included.
   - **The seaward boundary** is computed, not drawn: the cheapest path across the cove's mouth from the W join base to
     the E join base through sea3/sea5/sea4 tiles only, staying seaward of every shallow (sea1/sea2) ring.
   - **Output:** the tris (part, positions, UVs, normals, IDALLs verbatim), the boundary classed (lawn / water / join /
     source), the join columns, the source contact.
   - **Refuses** any boundary edge that cuts a component: a forest, rock, Object or island partly inside.
2. **`river.outline(fragment, at, margin)` -> the island's outline.**
   - The kit arc runs from the E join base round the fragment's land side, at least `margin` from its land ring, to
     the W join base. It is closed through the water by the seaward boundary.
   - Segments are no longer than 8u (the mint's grain).
   - The arc's length is RESAMPLED so the U phase lands on both joins (step 4).
3. **The mint takes an outline.** `island.build_landmass` gains `outline=` (a custom ring) and `rim_at=` (fixed rim
   points at given indices: the two join crests).
   - Everything after the outline is the existing mint, unchanged.
   - `outline=None` must rebuild every frozen island identity net byte for byte.
4. **The join columns.**
   - The mint's outline passes through each stock join BASE, and its rim through each stock CREST: the crest snap, at
     the source, not after the fact.
   - The mint's shore arc length gains an origin so the kit wall's u at E equals 0.8242. The resampled arc puts u at W
     on 0.752 (mod the rock strip; at most 19.8u of arc slack).
   - The V rows are the language's: 0.8926 / 0.9229.
5. **The opening and the seat.**
   - Drop every mint tri inside the fragment's footprint plus `CLEAR` (2.5u). All must be the mint's own lawn or
     wall, never a join column.
   - Insert the fragment, translated.
   - Zip the hole's ARC to the fragment's land ring from E crest to W crest with a new open-chain DP
     (`interior._zip_dp_open`, the cyclic `_zip_dp` without the wrap), the grass side on exact floats (THE EXACT-WELD
     LAW).
   - `--apron` turns on the mountain's lift for a bench that is not level.
6. **The water.**
   - The fragment's sea parts are carried. Outside the seaward boundary is the island lane's cut Sea4 sheet.
   - Where the boundary's sea3/sea5 meets Sea4, the rim retile (`rimretile.rim_retile`) re-bands the crop seam. Sea3
     never touches sea4 (THE LATTICE ADJACENCY LAW).
   - The boundary never touches shallows, so the {sea1, sea5} ladder is not needed.
7. **Binding and deploy.**
   - **Every target cell diverts to (16,15).** It is the one stock prefab that hosts every part the composition emits:
     Terrain, Object, Beach1, Sea1-5, Stream, RiverJoint.
   - **Every part a cell does not carry is written as a hidden blank** (one zero-area tri: 0 indices crash
     `AddWalkMesh`), so (16,15)'s own stock parts never free-ride. This is the `deploy_mountain_parts` pattern.
     It is also what makes (16,15) a lawful host: THE PREFAB-PARTS GATE says an Object-bearing donor never hosts a
     foreign cell, because its Object would ghost-render there (THE GHOST SIDECAR). The blank Object override
     suppresses the ghost in every cell but the bridge's; B1 checks it.
   - **Split and write:** tris split at the 64u borders (`split_borders8`). The disc-4 mirror and the ledger run as for
     every writer.
8. **The source.** In v1 the source tip zips to lawn (the seat dry run passes there) and the verb WARNS: "every stock
   river rises in a mountain -- add one with `world-mountain` at (x, z)". A `--source-massif DONOR` that composes it
   is a later rung.

## The gates (all offline, all before the first write)

| gate | what must hold | proven by |
|---|---|---|
| F1 component closure | no boundary edge cuts a forest, rock, Object or island component | `closure.py` (corrected) |
| F2 shore scope | the seaward boundary touches no sea1/sea2/beach | THE STRICT SHORE LAW |
| G1 crack | no once-edge the parts did not already have, except the island's outer coast and the knit seam | the seat dry run |
| G2 grain | zip edges < 9u, mint edges <= 8u | mint + seat |
| G3 weld audit | 0 near-miss vertex pairs (< 0.05u) | `weld_audit` |
| G4 census | no INTRODUCED miss against the donor at the same relative points; MISS 0 elsewhere | THE NO-INTRODUCED-MISSES LAW |
| G5 skip parity | 0 flips (the 177 banks + the bridge's 24 sides keep their IDALLs) | `placement.skip_parity_gate` |
| G6 water visibility | the ground query hits stream/joint through the bank holes as at home | the seat dry run (673 hits) |
| J1-J4 joins | crest/base welds exact; \|du\| < 1e-4 at both columns; the V rows; the first kit column's slope within the stock 60-80 deg | new |
| W1 water adjacency | after the rim retile, 0 sea3/sea1/sea2-to-sea4 contacts on the knit seam; the Wang-carry and sea-plan gates | existing gates |
| B1 binding | every target cell's Donor.txt prefab hosts every emitted part; every free-rider blanked | the effective-prefab and prefab-parts gates |
| C1 budget | <= ~5k tris per walkable part per block (the cost law) | terrain study rank 10 |

## Tests

- **Hermetic** (synthetic, so they run in a fresh worktree). A small channel, banks, mouth, cove and an islet:
  - the fragment closure takes the islet whole and refuses a half-cut one;
  - the open-chain zip welds both ends exactly;
  - the crest snap and the U phase land on given values;
  - the custom outline mints a closed wall.

  **Break-its:**
  - the old dispatch strip fails G5 by name;
  - a forest cut fails F1;
  - a join 0.01u off fails J1;
  - a seaward boundary through sea1 fails F2.
- **Identity:** `build_landmass(outline=None)` rebuilds every existing island identity net byte for byte.
- **Install-gated:** cluster C's fragment counts, boundary classes and gate results are pinned. The test warns, then
  skips, when no install resolves, so a skip can never pass silently.

## Rungs (each useful alone; one change per in-game test)

| rung | what | accept | cost |
|---|---|---|---|
| 0 | `river.fragment` + its catalog row (`donors.toml` class `river`) + F1/F2; the seaward boundary computed round the island | cluster C's fragment holds the whole island; F1/F2 green; break-its red | half a day |
| 1 | `build_landmass(outline=, rim_at=)` + the U-phase origin | identity nets byte-identical; J1-J4 on a synthetic outline and on cluster C's | a day |
| 2 | the composition, offline end to end, no write: opening, open zip, joins, binding plan | every gate green, or each failure localized and understood | a day |
| 3 | deploy to a scratch folder outside the install + rim retile + `world-render --stock` | W1 and B1 on the written bytes; the render reads as the bay | half a day |
| 4 | in game, one launch, the lab in and out by `lab_install.py` | registered: the river and stream animate; a walk at a bank stops as at home; the bridge carries the player across; the Blue Narciss sails the cove to the beach; walking the cliff top across both joins never drops; the owner's eye passes the bay | one session |
| 5 | ~~`--source-massif`~~ and the `world-fuse [[river]]` row -- REPLANNED in `RUNG5.md` (no catalogued massif can stand at this source) | recipe = CLI bytes; the source's own foot as a recon | CLOSED: 5a + 5b done, 5c recon = NO (RUNG5.md); the lawn source is permanent |

## Rung 0 result (offline)

`ff9mapkit/world/river.py`: `fragment(donor)` reads the window and calls `build_fragment(tris, donor)`, a pure function
over tri dicts, which runs F1 and F2 and refuses with `RiverRefused(gate, where)`. The catalog row is `cluster-c`,
class `river`, status `candidate` until rung 4. `fragment_run.py` prints the report and draws `out/fragment_plan.png`.

| cluster C | |
|---|---|
| fragment | 1,535 tris: the unit 330, the cove 1,027, the coast 141, the island 85 |
| the island | WHOLE (round 4's chord carried half of it) |
| seaward boundary | 146.0u along 34 deep-water edges (the straight chord was 115.3u) |
| boundary | lawn 650.1u, water 146.0u, join 6.6u, source 5.7u, nothing open |
| F1 | green: 1 Object (the bridge), 3 beaches and 1 island, each whole |
| F2 | green |

What the build settled, beyond the plan:
- **THE ISLAND TETHER.** Each island standing in the bay is joined to the mouth by a water corridor the boundary may
  not touch, so the boundary must go round it on the sea side. Without it the cheapest path runs landward and
  leaves the island home: a lawful but smaller fragment, a quiet wrong answer rather than a refusal. A test proves
  the tether is what routes the boundary seaward.
- **The boundary's vertices touch deep water only** (both join bases excepted). So no island's shallow ring can
  straddle it, and F1 can never find an island cut by the seaward boundary.
- **A leak is any cove edge with nothing across.** Open-sea blocks have no prefab and so no tris, so checking only
  the window's frame would miss a leak into them.
- **The sand row is taken as whole 4u cells.** One row of lone tris is a sawtooth against the zip.
- **J0 checks a join's roles:** the base touches water and the crest does not. A wall cell's diagonal is a
  crest-to-base wall edge too, so it is lawful.

Tests (`tests/test_world_river.py`): a synthetic cove with an islet straddling the chord, and break-its for a cut
forest, a half-cut islet, a lip cut off the columns, a mouth barred by shallows, a boundary through sea1, a leaking
cove, the joins, and the tether. A mutation run took out F1, F2, the tether, the deep-vertex rule and the join stop
in turn, and each one turned at least one test red. The install-gated test pins cluster C's numbers.

## Rung 1 result (offline)

**The mint takes an outline.** `island.build_landmass` gains three arguments, all defaulting to the blob mint:
- `outline=`: a custom coast ring, either winding, its rim inset along each vertex's inward normal;
- `rim_at=`: crests pinned to exact stock points (fixed in the rim, the wall and the grass);
- `shore_origin=`: the wall band's arc-length origin.

The V row now goes by the corner's ROLE, not its height (THE WALL V CORNER-ROLE LAW): a crest pinned below 3.2 still
takes the top row. Every blob corner sits at 0 or 3.2, where role and height give the same float.

**The identity net.** `tests/test_world_mint_outline.py` freezes digests of nine blob mints, taken from the code
before the change: one lobe, three (island E), two, relief, desert, the big-mint refinement, the seam wrap, the Uaho
bench and (with an install) a beach mint. All nine are byte-identical. The install-gated Uaho and island-E nets in
`test_world_interior.py` pass too.

**`river.outline(fragment)` builds the ring.** The ring is the kit ARC plus the seaward boundary.
1. The island holds the fragment plus a one-sided band, `margin` 16u wide, on the land side of the fragment's land
   ring, tapered to 0 at the joins.
2. At each join it also holds a band on the land side of the HOME coast, so the arc leaves each join along the stock
   lip it replaces. The geometry forces this: the column parts the carried lip from the home one, and a kit wall
   arriving from any other side would lie over the carried lip. At W this makes a short lobe south of the join.
3. A morphological closing (radius 24u) fills the inlet the band would leave between the river and the cove (one
   lowland in stock). It keeps only what lies nearer the land ring than the seaward boundary, so the cove's mouth
   stays open.
4. The band's contour (numpy only: an exact separable distance transform, then marching squares) is smoothed and
   re-spaced to 6u.

**THE U PHASE.**
- `shore_origin` lands E's stock U (0.82422).
- An outward bump of the arc's middle, found by bisection, lands the arc's length so W's U is 0.75195 too.
- **THE WRAP GUARD:** each join's arc segment stays inside the rock strip. rock_uvs window-translates a tri that
  straddles the band's wrap, so W's last segment is 3.6u, inside its 4.24u margin. A test proves what happens
  without the guard.

**J1-J4** (`river.join_gates`, on the minted island):

| cluster C | E | W |
|---|---|---|
| J1: the column, bit for bit | 1 kit tri | 1 kit tri |
| J2: U off the stock | 2e-16 | 2e-15 |
| J3: V off the stock (the kit's 0.893 row vs the stock's 0.89258) | 0.00042 | 0.00042 |
| J4: slope | 78.2 deg | 72.0 deg |

The island:
- Mint: 12 blocks, 3,310 tris, 1.5s.
- Arc: 569.6u, 96 points, 3.3-7.1u segments, at least 9.5u from the land ring away from the joins.
- `verify_landmass`: 0 cracks, open edges, holes, down-facing tris or over-8u grass edges.
- **Two tris fail the walk filter: the seaward wall quads at the two columns.** The closing chain's wall meets the
  pinned crest there. Both lie inside the fragment's footprint, which rung 2's opening drops, and the test pins
  exactly those two.
- The shape-language gate is not judged here. The seaward chain is lattice-stepped and dropped, so the arc's own
  shape is judged in rung 2.

The plans are `out/outline_plan.png` and `out/outline_join_{E,W}.png`, from `outline_run.py`.

What the build settled, beyond the plan:
- **The crest must stand nearest its own base.** The wall's U comes from the nearest coast vertex
  (`island.shore_s`), so a crest standing nearer another vertex takes that vertex's arc length. J2 catches it (a
  test), and cluster C's crests stand 0.65u and 1.07u from their bases.
- **A lattice-aligned coast is a degenerate Delaunay.** A real donor never sits on the mint's 4u grid; the synthetic
  fixture is shifted off it.
- **A 4u lip cell is a ramp, not a cliff** (37-52 deg). J4 refuses it, which is one of the break-its.

Tests:
- `test_world_river.py`: the synthetic cove's outline (stubs along the home coasts, both phases exact, the whole
  fragment held), and a hand-built kit-like ring with J1-J4 green.
- Break-its: J1 0.01u off, J2 a wrong origin, J2 the wrap, J2 the nearest-vertex crest, J3 a V row, J4 a ramp, a
  missing UV, a band running one way, a join at the strip's edge.
- `test_world_mint_outline.py`: both windings mint a closed wall; the crest is welded by wall and grass; V goes by
  role; the origin moves U by the density.
- Install-gated: cluster C end to end.
- A mutation run (a non-zero default origin, height-based V, a fixed winding) turned tests red each time.

## Rung 2 result (offline)

`river.compose(fragment, offset=, window=)` runs the whole composition with nothing written:
1. the outline in the donor frame;
2. the translation (4u multiples; every float stays exact);
3. the mint;
4. the opening;
5. the apron;
6. the open zip;
7. the area stamp;
8. every gate and the binding plan.

**The target.** Open ocean is scarce. A 3 x 5-block footprint fits only across the world's seam (columns 23, 0, 1,
rows 13-17). `river.open_ocean_offsets` finds 8 such placements, all at block offset 8 or 9, and the dry run uses
the first, (8, 0). It touches no deployed override.

**The opening and the apron.**
- **The opening:** 1,673 of the mint's 3,310 tris drop: 1,605 lawn and the 68 walls of the seaward chain. The arc's
  walls, both join columns among them, all stay.
- **The apron:** the kit lawn moves toward the land ring's own heights, by up to -1.47u and +0.33u over 593
  positions. A stock lowland falls 2-3u to its beach behind the sand row, so the reach is 24u, twice the
  mountain's.

**THE OPEN ZIP.**
- **The strip.** The hole's rim and the fragment's land ring are two chains, crest E to crest W, welded at both
  columns. A minimal-chord strip joins them, on the kit's exact floats.
- **The DP.** It may FAN round a shared end: at the E column the two chains leave in opposite directions, and one
  tri cannot span 180 deg. It also routes round plan-flat slivers, where the 4u lattice and the block borders line
  both chains up.
- **The refinement.** Longest-edge bisection of the zip's interior edges (Rivara) brings every edge to 6.7u or
  less and every climb to 1.4u or less. It is margin, measured: unrefined, the longest chord is 8.95u, 0.05u under
  G2.
- **The result:** 442 tris; flattest ny 0.947.

**THE NOTCH CLOSURE (new in the fragment, rung 0's code).**
- **What it does:** it carries any stock grass or sand tri that the fragment holds on two sides.
- **Why:** such a notch has all three corners on the land ring, so no zip strip can fill it; the strip folds over
  the fragment.
- **Where it bit:** at the cove's NE corner, two squared sand cells meet at a point. The fold put 39 G4 samples on
  zip grass over the carried sand and beach.
- **Cost:** 12 tris on cluster C (the fragment is now 1,547). Carried, they are stock bytes, not authored ones.

**THE STAMP (decision 1).**
- Carried ground (Terrain, Beach1, the bridge) takes the island's area. That is `minted_area`, here 14
  (SAFE_ROAD_AREA at open sea), the same as the island lane's land.
- The 201 tris the ground query skips keep their IDALLs: the 177 banks and the bridge's 24 sides.
- Every event bit is stripped.
- **Read for the owner:** the water parts keep their stock areas. Stock sea is area 0, as the island lane's sea
  is, and the river's water is area 0 on 88 of 90 tris. "Every carried tri" is read as every carried ground tri,
  the tris the island lane stamps.

**The gates, on cluster C at offset (8, 0): all green.**

| gate | result |
|---|---|
| J1-J4 | as rung 1: columns exact, \|du\| <= 2e-15, \|dv\| 0.00042, 78.2 / 72.0 deg |
| zip | 442 tris, max edge 6.66u, max climb 1.39u (1.5u counting carried edges), ny >= 0.947 |
| G1 crack | 0. The once-edges are exactly the arc's coast (140) and the seaward seam (34) |
| G3 weld | 0 minted. Inherited: the mint's own border cuts (also on island E: 7) and the fragment's |
| G4 census | 10,124 samples in the footprint ground EXACTLY as home (mesh and topograph). Kit land: 3,342 samples, 0 MISS |
| G5 skip parity | 0 flips over 201 skipped tris |
| G6 water | no stream or river-joint sample moved |
| B1 binding | 12 cells, all open ocean, all divert to (16,15); the bridge's Object in one cell, blank in 11 |
| C1 budget | the largest part is 601 tris (budget 5,000) |

G4 now fails on ANY change inside the footprint, not only an introduced miss: a kit or zip tri over the fragment is
a stacked sheet. The earlier rule passed 39 of them.

**Break-its on the real composition** (`test_cluster_c_break_its`):
- notch closure off: G4 red;
- the old dispatch strip: G5 red (201 flips, the plan's named break-it);
- the donor's own cells: B1 red;
- a zip tri lost: G1 red.

A mutation run (skip kept, the G4 rule, the notch threshold, the fan) turned tests red each time.

**Without the apron** every gate is still green, but the zip's steepest edge climbs 2.24u, 4% under the engine's
2.34u step. With the mountain's 12u apron it climbs 1.77u; with the river's 24u, 1.39u.

**Tried and removed:** a fold penalty in the DP (refuse a zip tri over the fragment). The notch closure made it
unnecessary. Without the closure it made things worse, moving one bad sample to 39. It was authored surface with no
case left to answer.

Plans: `out/compose_plan.png`, `out/compose_{E,W,NE,mouth}.png`, from `compose_run.py`.

## Rung 3 result (offline)

`river.write_composition(comp, root, window=, donors=)` writes the whole thing to a folder OUTSIDE the install. It
refuses a root inside the game (B0). The steps:
1. **Part meshes.** The composition splits at the 64u borders, block-local. A carried tri keeps its tangent's y/z/w
   verbatim.
2. **The kit's Sea4 cut.** The island lane's deep sheet goes on every block, cut under the island AND the
   fragment's own water.
3. **THE KNIT.** The rim retile runs on the sea bands in memory, to its fixed point.
4. **The write.** Every prefab part is written, as a hidden blank where nothing is carried, with the `Donor.txt`
   divert.
5. **B1 read back from the bytes.**

`write_run.py` runs it on cluster C, then `world-render --stock` and four seam views.

**What the build had to settle.** Each of these was a gate failing, found and fixed at its cause.

| finding | what it changed |
|---|---|
| **THE CELL-ALIGNED SEAM** | 10 of the seaward boundary's 34 edges ran along cell diagonals. Each splits a 4u cell between carried sea3 and kit Sea4, a contact inside one cell that the cell-binned retile can neither see nor re-band. A diagonal now costs 100 more: 0 are left away from the joins. |
| **THE SHORE-CLEAR SEAM** | The retile re-bands a cell only away from shore (its shore scope). Hugging the island's shallow ring, the seam left 9 sea3/sea4 contacts. It now keeps 2 cells clear of the bay islands' shores, except within 12u of a join base. It counts only the shores the COMPOSED island has there: home's land beyond the cove is not carried, and the kit's deep sheet replaces it. |
| **THE COVERED-TRI TEST** | The island lane drops a plane tri when its three corners lie under land, which holds while the cover is convex across the cell. At the E join, the kit wall and the carried water cover every corner of a plane tri round a sliver of open sea, and the byte census caught the hole. The corners AND four interior points must now be under. |
| **TWO WANG DIALECTS** | Pooled over the window, the tile harvest is empty. Stock writes the same Wang tile two ways across blocks (a wrap corner at u 0.0 in one, 0.0317 in another), and the harvest drops any variant whose instances disagree. `knit_variants` harvests block by block, first wins, the cove's own blocks first, so each tile is verbatim from one stock block. |
| **THE RETILE NEEDS THE BANDS** | `rimretile.apply_rim` rebuilds only the sea bands a block already has, so a block without Sea5 lost its re-banded tris (the repartition gate refused). The knit seeds empty Sea3/Sea5 parts. |
| **THE SEAM-WRAP RENDER** | The renderer read only mod folders in the install and clamped columns to 0..23, so an island across the seam rendered torn. `world-render --mod-root DIR` reads any folder. Cells keep their unwrapped columns; files and prefabs come from the wrapped label. |

These moved rung 0-2's pinned numbers:
- the fragment is 1,546 tris;
- the seam is 170.4u along 43 edges;
- the ring has 138 points;
- G4: 10,098 samples, all exactly home.

**W1 on cluster C, after the knit.** 16 quads re-banded over two passes. Home's own baseline is from the same blocks
in stock.

| | composed | home |
|---|---|---|
| tiles facing deep without their transition | 0 | 1 |
| crop-made sea pairs at any tri edge (sea3/4, sea1/4, sea2/4, sea2/5) | 0 | 0 |
| contradicting edges | 2 | 2 |
| wang-carry frame | 0 incoherent | |
| unpaintable slivers | 0 | |

One of the two contradicting edges is home's own, at the E headland. The other is introduced, at the W join's
corner cell. This is **THE CLIFF-CORNER BAND STEP**: the carried cliff's sea3 meets the kit cliff's Sea4 across one
cell edge. It is the same step home ships at its E headland, and from the water it sits under the wall's foot. W1
stays strictly red on it, localized and understood, for the owner's eye.

The sea-plan gate: A green (no submerged land), C green (3.9% sea/land overlap, ceiling 19%). B warns: the island's
interior blocks carry almost no Sea4, the continent-scale class the island lane also warns on.

**B1 on the bytes: green.**
- 132 files over 12 cells, each diverting to (16,15) with a file for every part that prefab hosts.
- Every file round-trips.
- The engine's census over the WRITTEN stacks misses nowhere home grounds. 98 samples miss at home too: the skipped
  banks, THE BANK SKIP LAW.

**The render** (`out/river_render/`: overview, the standard views, `seam_top`, `join_W`, `join_E`, `mouth_in`):
- **It reads as the bay.** The river and its bridge wind through the kit lawn to the cove's beach. The island stands
  in the cove, and the shallows grade to deep.
- **Both joins read as one continuous rock face.**
- **Two things for the owner's eye.** First, the seam runs along a straight lattice row, so the knitted band edge is
  straighter than stock's wandering ones. Second, the W corner's band step.

Tests:
- `test_world_river.py`: the seam cell-aligned and shore-clear, with a break-it; part meshes block-local with
  tangents kept; the contact census; the covered-tri cut; knit variants first-wins; the write refusing the install;
  write and read back across the seam with two B1 break-its; the renderer reading a scratch root across the seam.
- Install-gated: cluster C written and audited.
- A mutation run turned tests red each time: no diagonal cost, corner-only cut, no wrap, pooled variants.

## Rung 4 result (in game) -- CLOSED, owner-passed

**Every registered check passed, the owner's eye on the bay included** ("the bay passes"). Cluster C's catalog row is
now `qualified`. What v1 still lacked at the close was the CLI verb (now wired: "The CLI verb" below). The lab
is
`river.write_composition` verbatim, written by `lab_build.py` with the mist off. `lab_prep.py` predicts every height
and stop from the engine's ground and movement rules over the lab files (the ray from y + 2.34375, the 8-angle slide,
masks WALK and BOAT). `lab_install.py` put the lab first in FolderNames and restored Memoria.ini byte-exact after
each launch.

**The placement moved.** Rung 2's offset (8, 0) is open ocean in the stock tree, but the live overworld folder already
holds 54 files on those cells. **B1 now reads the mod tree too** (`binding_plan(mod_folder=)`, through
`mesh.existing_overrides`): an occupied target cell is a B1 failure. The lab sits at (8, -2): cells (23,12-14),
(0,11-15) and (1,11-14), across the world's seam, which no live folder touches. Every rung 3 gate held there.

| check | game | simulation |
|---|---|---|
| R1 the kit lawn / the carried island / the bridge deck (Object topo 52) | y 3.199 / 2.863 / 4.090 | 3.200 / 2.865 / 4.093 |
| R2 the bank walk at the stream | blocked at 12.86u, min y 3.05 | 13.1u |
| R3 the bridge walk | across, 16.25u of 16.22, min y 3.09 | reached |
| R5 the E join's cliff top | blocked at 17.17u, min y 2.84 (never drops) | 16.98u, min y 2.85 |
| R5 the W join's cliff top | across, 18.80u, min y 3.23 | reached, 18.38u |
| R4 the Blue Narciss from the kit's open sea | across the knit seam into the cove, stopped at 82.23u on the beach | 82.21u |

**The water animates.** Pairs of stills 60 frames apart, mean pixel change by region; the grass is 0.00 in every view:
- the sea and the cove: 2.3-3.4;
- the stream: 12.6 under the bridge and 9.2 at the source end;
- the river mouth: 16.6.

**THE SUNKEN CHANNEL:** the stream's water sits at y 0.39, 2.8u under the lawn. From the lawn views, the low world
camera sees only the banks: the river view's stills show a dry-looking gully and no motion there. The carry is
verbatim (G4: every sample exactly home), so home looks the same. The channel views (`channel_deck`, `source`) put the
water in the near field.

**Three things put to the owner's eye, all passed with the bay** (stills in `.harness-runs/20261020-090223-world-river-foot/rung4-sheet.png` and
`.harness-runs/20261020-090931-world-river-channel/rung4-channel.png`):
1. **The bay** reads as stock: the beach, the shallows grading to deep, the island in the cove.
2. **The source end** is the stream's banks closing in open lawn (decision 3). Rung 5's massif replaces it.
3. **A streaked grass band on the kit cliff's lip.** Flat lip tris whose texture mapping collapses to one direction
   (v 0.77-0.82, the grass rows of the wall atlas). These are the kit mint's own: the kit islands already live in
   FF9CustomMap-world carry 23 such tris, the lab island 12.

The harness's own lesson, for the next overworld session: `world_face` measures the heading by WALKING about 30u. On
a narrow headland the probe slides along the cliff and reads as a camera that will not turn (round 1 lost the foot
stage that way). Face on the open lawn, then teleport to the start; the camera's yaw survives the teleport.

## The CLI verb (wired, 2026-10-20)

`world-river` runs rung 4's lab recipe as one command (`cli._cmd_world_river`; the helpers are `river.py`'s last
section). **How it writes into a live folder:** `write_composition` keeps refusing the install (B0), so the verb never
asks it to. It STAGES: the composition is written to a temp folder outside the install and audited there (W1 after the
knit, the sea plan, B1 on the bytes). `write_verdict` decides, accepting W1 red only on the donor's owner-passed
THE CLIFF-CORNER BAND STEP (`UNDERSTOOD_EDGES`, donor frame) and nothing else. Then `promote` moves exactly the staged
bytes through the kit's one write seam (`mesh.deploy_override` per part mesh, `mesh.deploy_donor_sidecar` per
divert: the ledger, the backups, the ownership refusal). Every staged mesh must round-trip through the seam's
serializer first, and every deployed file must equal its staged one after (P0). The disc-4 mirror runs last, as for
every world writer. `--dry-run` is the same pipeline minus the promotion, so it reports every gate the real run does.

**THE STACK READ.** B1 in `compose` reads only the target folder's disc 1. The verb also reads every folder in
FolderNames, on disc 1 and on disc 4 unless `--skip-mirror` (lab_build's check). A cell two folders override
renders a mix of two deploys' parts, so the verb refuses. `--at auto` takes the nearest `open_ocean_offsets` shift
whose block rectangle the stack leaves free: on today's install it passes over (8,0), (8,-1), (8,1) and (9,0), all
held by FF9CustomMap-world, and lands on (8,-2), the proven placement.

**Measured, cluster C at `--at 512,128`:**
- `--dry-run`: every gate green, W1 understood on the band step at (24,14,3,14), the sea plan's B warning, 16.5s.
- A real run into an absolute scratch folder: the 132 Disc1 files are byte-identical to the rung 4 lab
  (`lab_build.py`'s `out/lab/FF9CustomMap-lab`, its mist file aside), plus the ledger. `discmirror.mirror` on that
  folder mirrored all 132 to Disc4, 0 free-ride pins, 0 cells skipped.
- `--no-apron`: every gate green offline too (zip max rise 2.24u of 2.34). Not played.

**THE REMOVAL (`--remove`, chosen over `--allow-overwrite`).** B1 refuses the verb's own earlier deploy on its cells,
and it still does. A redeploy is `world-river --remove --at DX,DZ` (the placement the deploy printed), then the
ordinary run, so the stack read runs again on clean cells. `river.remove_deploy` deletes a file only when the
folder's ledger says it is this deploy's: the last row for its (disc, cell, part) records its current bytes, and a
row with those bytes ran `world-river` at this placement. An explicit `--at` naming another shift is another
deploy's; `--at auto` does not say, and B1 never lets two deploys share a cell. It checks disc 1 and the disc-4
mirror. It is all or nothing: R1 names every foreign file before the first delete, and R0 refuses empty cells. Each
file is re-hashed, parked as `.bak-<ts>`, deleted, and ledgered (`op: remove`, `sha256: null`). Other stacked
folders are never touched. Why not `--allow-overwrite`: it cannot take a river out, it leaves the verb a waiver past
B1, and it would orphan any cell an earlier kit's composition covered and this one does not. Verified on the real
data into an absolute scratch folder: deploy, mirror, a foreign disc-4 byte refusing R1, remove (264 files), and a
byte-identical redeploy. A read-only ownership check of the live FF9CustomMap-world deploy at 512,128 (a CLI run,
ledgered) judged all 264 of its files the verb's own.

Not in v1: any coastnav stamp on the kit coast (the verb prints the coupling note).

**Live, owner-passed (2026-10-20).** `world-river --mod-folder FF9CustomMap-world --at 512,128`, run with FF9 closed:
- 264 files: 132 on Disc1, byte-identical to the rung 4 lab, and the Disc4 mirror with the same bytes.
- All 12 cells were empty before, so nothing was parked; 264 ledger rows were appended.
- The manifest (every path with its sha256, plus how to revert) and the pre-deploy ledger are in the MAIN repo's
  `backups/` (`world-river-deploy.20261020-103431.manifest.txt`).

The owner's playtest passed it. One observation: the two shallow-water triangles where the beach meets the river mouth
"look a little weird".

**CLOSED: they are home's own look.**
- **The bytes** (`mouth_compare.py`, 24u round the mouth): all 130 water, beach and river tris (Sea1-3, Stream,
  RiverJoint, Beach1) match home in position, UV, normal and tangent. The only difference is decision 1's area stamp
  on the beach and the carried ground (5 or 16 changed to 14), and those areas fall outside every range the engine
  reads for the camera, the weather or the area-12 lock.
- **The two triangles:** a Sea1 tri at the W corner and a Sea2 tri at the E corner, each with a vertex lifted to y
  0.535 where every other sea tri there lies flat at 0.
- **The eye** (`mouth_session.py`, one launch, 11/11): live and home stills from the same relative spots (the deck,
  the E beach, the W beach) show the same darker wedge at each corner. Only the water's animation phase differs.
  Stills: `.harness-runs/20261020-131150-world-river-mouth/mouth-zoom.png`.

## Decisions for the owner (answered: the recommendations, 2026-10-19)

1. **The AREA bits on carried tris.** Recommendation: stamp the island's own area (consistent camera, encounters and
   place name) on every carried tri, except those the ground query skips (THE BANK SKIP LAW), and strip every EVENT
   bit (no stray entrance). The alternative, keeping the donor's areas, gives the cove a different camera bucket from
   the island round it.
2. **What stays home.** The three forests beside the river and the tower stay home. The lawn between the river and the
   bay will read emptier than stock; `world-forest` can dress it afterwards with qualified canopies. The alternative,
   carrying them, drags the escarpment in (138u of rock) and is not lawful.
3. **The source in v1.** Recommendation: zip to lawn with a warning, and add the massif in rung 5. The alternative is
   to require a massif before v1 ships.
4. **Scope.** One donor (cluster C) in v1. Cluster D's falls (R2) needs a plateau and stays parked. Rotation stays at
   0 in v1: the cove's water ladder is dihedral-8, and free rotation is a later study.
5. **The name:** `world-river`.

## Risks

- **The join columns are new authored surface.** The crest snap at the source keeps them exact. J1-J4 gate them, and
  rung 4's cliff-top walk tests them in game.
- **The custom-outline mint near the joins.** The mint pulls its rim radially. `rim_at` fixes the join crests, but the
  wall tri beside each join may skew. J4 bounds its slope, and the render shows it.
- **The U phase is exact only at the joins.** Elsewhere the kit wall keeps its own per-tri window language, which is
  already in game on every kit island.
- **The water seam.** The rim retile is proven on transplant crop seams; the cove's mouth is a wider seam than any
  so far. W1 and the in-game boat run decide.
- **Speed.** The gates are pure Python, over ~1.4k fragment tris and a ~4k-tri mint. Expect minutes per dry run, and
  measure it in rung 2.

## Not in scope

- A minted, synthesized or painted river (THE FORM LESSON).
- Cutting the river out of a continent region (closed by THE FUSE LAW: 370-1112u of coast to mint).
- Lakes (no lake part exists; a separate recon).
- Rivers on the plateaus (R2).
