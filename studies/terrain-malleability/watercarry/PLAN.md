# `world-river`: carry a stock river onto a kit island -- the build plan

**Status:** plan for the owner's sign-off (2026-10-19). Nothing is built. The evidence is in `RECON.md` (R0, R1 rounds
1-4); this file is the build.

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
py -m ff9mapkit world-river --mod-folder F --at WX,WZ [--dry-run] [--apron] [--skip-mirror]
```

`--at` places the fragment by translation only: rotation 0 in v1, the offset a multiple of 4u so every water tile
stays on the lattice. The whole composition must land on open ocean.

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
| 5 | `--source-massif` and the `world-fuse [[river]]` row | the source meets a carried foot; recipe = CLI bytes | later |

## Decisions for the owner

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
