# Landmass prefabs — feasibility (2026-11-08)

**The question (owner):** using the laws we already have, can we do "synthed prefabs" yet? Making a new
landmass in the World tab still takes too many separate steps.

**Verdict: yes, if a prefab is a FROZEN COMPOSITION of what the kit already carries, placed in whole 64u
blocks.** A prefab is a relative `world-fuse` recipe: one plain `world-island` mint plus carried relief
(forest, mountain, hill) at offsets from an anchor block. Stamping it at a new site writes the SAME land,
shifted. So one in-game walk qualifies it for every site it can legally go. Three position leaks stand in
the way today; all three are small and measured (below).

A prefab is never synthesized surface. THE FORM LESSON and the dead-ends list rule that out, and
THE DEFECT FOLLOWS THE AUTHORSHIP is why it matters: a prefab mints no new surface after the walk that
qualified it. "Synth" can lawfully mean only a **search that proposes arrangements**: island seed/radius x
home-matched donor x relative offset, kept when every gate is green. Gates are not an oracle (0 of 13
verdicts predicted on the Path-D wall arc), so a searched arrangement is a CANDIDATE until it is walked,
exactly like `donors.toml`'s `candidate -> qualified`.

## What was measured (offline, scratch mod folders, nothing written to the install)

Sites: blocks (0-2, 13-15) vs (0-2, 15-17), two of the 30 stock open-ocean 3x3 windows, 128u apart in z.
Scripts: `prefab_xlate_probe.py` (the mint alone, no install), `prefab_folder_compare.py` (folder A vs B
block-shifted), `prefab_mesh_diff.py` (triangle multiset, vertex order ignored).

| Build | Shift | Result |
|---|---|---|
| `build_landmass` grass/desert/snow, 1-2 lobes, no decals | 4u, 32u | different land (the block/cell clip moves) |
| same | 64u, 128u, 192u | **identical** (position + UV, every triangle) |
| same with `relief_amp` 1.3, `relief_seed` pinned | any | different: the relief noise reads ABSOLUTE x,z |
| `world-island` grass r44 (meadow decals on) | 128u | 2 Terrain blocks differ: 136 tris wear other tiles |
| the same with the decal shuffle sorted first | 128u | same triangles; file bytes differ only in vertex order / normal noise < 1e-9 (neither is read by the engine) |
| `world-island --ground desert` r60 (no decals) | 128u | **byte-identical**, 81 files |
| + `world-forest` (blob 15,15) at the same relative point | 128u | **byte-identical**, all 9 Terrain files |
| + `world-mountain --donor 19,3 --rot 90` (desert peak) | 128u | positions exact; 59 apron tris in 1 block wear other UVs |

Refusals seen on the way (the verbs' own gates, useful for sizing a catalog): Uaho refused on grass r44
and r60 ("best raw clearance 2.5-3.1u vs the 6.5u band"). The forest refused on r44 (no plain-grass
pocket) and placed on r60. The desert peak placed on desert r60 with clearance 29u, all gates clean.

## The three position leaks (all deterministic; the cure is relative-to-anchor)

1. **Meadow decals** — `grassland.place_stamps` (line ~527) shuffles `cells_set` itself, so the shuffle's
   input order follows the absolute cells' hash order. Measured fix: `sorted(sorted(cells_set), ...)`.
2. **Rolling relief** — `island.build_landmass` evaluates `G.relief(x, z)` at absolute coordinates
   (line ~658), and the default `r_seed` comes from the centre (line ~638). A prefab needs the noise read in
   anchor-local coordinates.
3. **Mountain apron fallback** — `interior.py:3232`: a cell the carve cannot decode takes a tile from a
   hash of its ABSOLUTE cell id (seed 0xF95). Hash the anchor-relative cell instead.

**All three must be OPT-IN (a prefab frame flag), never a silent change.** Every recipe already on disk
replays its `[[island]]` / `[[mountain]]` rows and must keep writing the bytes it deployed: the editor's
said-back and replay checks and the C-rung identity gates depend on that. Python's int-tuple hashing is
stable across runs, so today's behaviour IS reproducible at a fixed site. It just doesn't survive a move.

## The laws that bound a prefab catalog

- **Placement snaps to whole 64u blocks** (measured above). Turning a prefab is unmeasured: the mint has
  no rotation, so a turned prefab would be a re-run, not a stamp, and would need its own walk.
- **THE OPEN-OCEAN TARGET LAW** (every footprint block is true open ocean) keeps a prefab off other land,
  so its own sea ring is the only context it ever meets. That is what lets one walk stand for every site.
  The stock map has 30 open 3x3 windows; the live folder is near full for multi-block carries (C20).
- **Home ground** per massif (`world-donors --class massif`): desert peak / crag / scrub on desert, the
  snow ridge on snow, Uaho / horseshoe / comp20 on grass. A prefab bakes the match in.
- **Size**: Uaho needs more than a 60u grass mint. A mountain's `--spread S` grows its footprint by S².
  Dunes have a size class (about 130 cells or more), so there is no small dunes prefab.
- **THE ONE-SITE WORLD LAW**: the two-ground landmass (`junction_compose`) is one per map. A prefab of
  that class carries `max_per_world = 1`.
- **Canopy vs rock**: a forest must be ringed by walkable ground (19u rim clearance on the re-home), and
  the rock's foot meets the canopy only on the 5-of-28 massifs measured. Screen offsets by home contact.

## Proposed ladder (one rung per in-game check)

- **P0 — the prefab frame: BUILT (2026-11-08), offline-proven; nothing deployed, no in-game step needed.**
  `--prefab-frame` on `world-island` + `world-mountain` (a `[[mountain]]` handle, cli + row), and
  `prefab_frame = true` on the `[[island]]` / `[[mountain]]` fuse rows, carried by `recipe.row_for`. The frame
  origin is the corner of the block holding the centre, so it moves with the land in whole blocks:
  - decals: `place_stamps(ordered=True)` shuffles the cells in sorted order;
  - relief: read at `(x, z) - frame`, seeded from `seed` (x1000, salted `PREFAB_RELIEF_SALT`) unless
    `--relief-seed` is given. The frame refuses a missing `--seed` (its default is centre-derived) and `--beach`;
  - mountain: the undecodable-cell tile hashes `cell - 16 * floor(centre / 64)`.

  `world-hill` and `world-forest` need no flag: measured byte-identical under a shift without one.
  **Measured:**
  - Default unchanged: 14 mint configs (decals, relief, desert, snow, no-seed; two sites) hash-identical before
    vs after, and the CLI desert isle + desert peak re-run is byte-identical to the pre-change run over 81 files.
  - Framed, through the CLI, sites 128u apart: the desert-peak isle is byte-identical, mountain block
    included (it differed in 59 tris unframed). So is the meadow grass isle (r60) + forest + hill (r14),
    all 81 world files.
  - The relief mint is identical at every whole-block shift, and still differs at 32u (the control).

  Fence: `tests/test_world_prefab_frame.py` (10 tests; the decal and carry ones install-gated). Each of five
  mutations (unsorted shuffle, absolute relief, absolute hash, the fuse row dropping the key, the recipe row
  dropping it) turns it red. `test_world_handles` covers the new handle. The overworld domain is green: 653 tests.
  Comparator law: compare at **float32** (what the `.ff9mesh` stores). In float64 the wall UVs carry 1e-15
  noise from absolute positions, which reads as "different land" that is not there.
- **P1 — `world-prefab NAME --cell BX,BY --mod-folder F`: BUILT (2026-11-08), offline-proven.**
  `world/prefab.py` + `world/data/prefabs.toml`. Rows relative to the anchor block's frame origin
  `(64*bx, -64*(by+1))`. Placement: rows on the map, then the CLEAR WINDOW (the target holds nothing in the
  footprint or any relief row's read window; no other FolderNames folder holds anything in the footprint),
  then a STAGING compose whose fingerprint must equal the catalog's, and only then the compose into the target
  (the verbs' own gates; never a copy of staged files) and a fingerprint of what it wrote.
  **THE FINGERPRINT HASHES TRIANGLES, NOT FILES** (measured): the framed mint alone writes the same triangles
  at every site but not in the same vertex order. Each triangle is taken at float32 with its normal rounded to
  1e-6 and rotated to its smallest corner, so the winding is kept.
  Measured: both prefabs fingerprint identically at (1,14) and (1,16); placed for real on (21,1) and (2,17),
  the written land is the catalog's; a second placement on the same block refuses.
  **ROOM, MEASURED: no stock open-ocean 3x3 window is free in the live FolderNames stack today.**
  `FF9CustomMap-world` holds 128 disc-1 override blocks, 4-9 of them in each of the 30 windows. A prefab on the
  live disc-1 map needs room made first (a sink or a move), a smaller footprint, or another world (Path D:
  the frame under `--target-disc` is unmeasured). Fence: `tests/test_world_prefab.py` (24 tests; the two
  real-bytes ones are install-gated); 10 mutations of `prefab.py` each turn it red.
- **P2 — seed the catalog from compositions already built here:** desert-peak isle and the meadow isle
  (forest + hill) are in as candidates (P1). Still to add: the snow-ridge isle (comp9:
  `--ground snow --radius 88 --lobes 2`) and the desert-scrub isle (comp26). Each one is walked once, then
  `qualified`.
- **P3 — the World tab "Add a prefab" card**: ghost the whole footprint, snap to blocks, one Check, and an
  Accept that lands as ONE undo step (a grouped step in `draft.py`'s history).
- **P4 — the arrangement search ("synth")**: enumerate seed/radius x home-matched donors x offsets, keep
  the all-green ones, and render them for the owner. Only the walked ones become prefabs.

## Open

- Which part of the editor feels janky to the owner (steps per landmass, Check waits, the island card
  offering only the plain mint, finding room) decides whether P3 comes before P1.
- The hill and forest ARE measured now (P0: byte-identical, no flag). The multi-block carries (`world-transplant`
  units) are not measured under a shift. C14 already
  showed a carry relabelled across the x seam is byte-identical 6/6, which is encouraging but not this test.
