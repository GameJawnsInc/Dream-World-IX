# Lane `disc4`: FF9's own terrain edits (WorldDisc1 vs WorldDisc4)

Read-only study. Every number below comes from a script in this directory that was actually run against the
user's own install. Derived outputs (JSON, renders) are in `out/`. No atlas pixels or mesh bytes are in the
repo: the atlas crops used for the by-eye checks went to the OS temp dir only.

**Run them** from `C:\gd\Dream-World-IX\ff9mapkit`, in this order (each takes 2-70 s; nothing writes outside
`out/` or the OS temp dir). Each one is invoked as `py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/<script>`:

| # | script | what it produces |
|---|---|---|
| 0 | `inventory.py` | the denominator: every worldmap container on both discs |
| 1 | `census.py` | per (LOD, block, part): IDENTICAL / REORDERED / ATTR / RESHAPE / RETOPO / ADDED / REMOVED, saved to `out/census.json` and `out/census_stdout.txt` |
| 1c | `calibrate.py` | 12 synthetic-edit checks (A0-A7) plus 7 known-case checks against memory (B). **All pass.** |
| 1n | `noise_check.py` | tolerance re-match, which rules out rounding-boundary float noise. It has its own self-test. |
| 2 | `prefab_census.py` | the 481 baked block prefabs: flags, slots, materials, transforms, and which mesh tree each slot reads |
| 3 | `anatomy.py` | engine-faithful ground deltas (`placement.place` sky-cast, 1u lattice), lattice reuse, welds, clusters |
| 4 | `render_maps.py` | `out/block_class_map.png`, `out/delta_map.png`, `out/delta_crop_*.png`, `out/rock_ribbons.json`. Includes the shape self-test. |
| 5 | `crescent_probe.py` | ridge cross-sections, UV-triplet novelty, Form-2 to Form-1 promotion |
| 6 | `uv_coverage.py` | atlas-coverage test (calibrated), and `out/uv_coverage.png` (a mask only) |
| 7 | `ridge_art_owner.py` | whose atlas art the crescents borrow, with a control |
| 8 | `bark_usage.py` | the bark/root tile's usage on each disc |
| 9 | `mirror_risk.py` | discmirror's own gate predicates run over all real cells, changed borders, and the live deployed state |
| 10 | `weld_gap.py` | the real seam gap behind every OPEN edge (calibrated: exact edges measure 0) |
| 11 | `grammar_summary.py` | grammar aggregates, entrance edits, and the per-site table |
| 12 | `entrance_check.py` | entrance-tile edits: CLOSED / GROWN / TRIMMED / NEW / reshaped |
| 13 | `reorder_check.py` | full-channel permutation proof, and whether buffer order alone moves the ground |

Shared instruments live in `d4lib.py`. Engine citations use `C:\gd\FFIX\Memoria\Assembly-CSharp` at the pinned
stock base commit `6b8bb2d5` (read via `git show`, read-only). "stock" means no `memoria-patches/*.patch` adds or
changes that line. I grepped the patches for `WMWorldPrefabMaker`/`WMWorld.cs`/`WorldConfiguration.cs` hunks:
`s75` touches `WorldConfiguration.UseMist` for Path D only, and no patch touches `GetDisc` or the prefab maker.

---

## 0. The asset model (law)

- Disc selection is stock. `WorldConfiguration.GetDisc()` returns `SC >= 11090 ? 4 : 1`
  (`Memoria/World/WorldConfiguration.cs:234-240` stock). The per-block prefab path is
  `WorldMap/Prefabs/WorldDisc{disc}/r{y}/Block[x][y]` (`Global/WM/WMWorld/WMWorld.cs:502`, async `:755`, both stock).
  The open-ocean fallback prefab is **always disc 1** `Block[12][0]f` (`WMWorld.cs:1060-1062` stock).
- Inventory (`inventory.py`): 481 prefabs per disc (480 + the `f` sea prefab), and the same set on both discs.
  - Tree `0_1`: 996 meshes on disc 1 and 995 on disc 4, over 275 blocks each (260 with Terrain).
  - Tree `0_2`: 94 and 93 meshes on 26 blocks.
  - Disc 4 has one fewer `riverjoint` (`0_1`) and one fewer `object` (`0_2`).
  - Both discs also ship `wmap/disc{1,4}/*` legacy blobs.
- **`0_2` is the FORM-2 mesh tree, not a far LOD.**
  - Stock `WMWorldPrefabMaker.cs:36` builds the `.../0_2/r{y}/` path. Lines `:120-127` load `0_2 ... Terrain`
    into the slot `"Terrain2"` and `0_2 ... Object` into `"Object2"`. Lines `:198-208` bind those to
    TerrainForm2/ObjectForm2.
  - `WMWorld.cs:518-521` (stock) registers ObjectForm2/TerrainForm2 as Form-2 walkmeshes.
  - Shipped prefabs agree (`prefab_census.py`): `Terrain2 <- 0_2` ×26, `Object2 <- 0_2` ×26,
    `Sea3_2/4_2/5_2 <- 0_2` at (3,9), and `VolcanoLava2 <- 0_2` ×1. No prefab slot reads the other `0_2` sea,
    river or beach meshes, so those are unreferenced assets.
  - This contradicts `ff9mapkit/ff9mapkit/world/extract.py:11` and `cli.py:8960`, which say "0_2 = far LOD".
    The form switch belongs to another lane, so this is only noted here.

## 1. Census (Q1), Form 1 (`0_1`)

Across the 998 (block, part) keys:

| class | count |
|---|---|
| IDENTICAL | 672 |
| REORDERED (an exact full-channel permutation, 23/23 incl. `0_2`) | 20 |
| ATTR (same geometry; id, uv and/or normal changed) | 72 |
| RESHAPE (same footprints, new Y) | 3 |
| RETOPO (cut/re-triangulated) | 226 |
| REMOVED | 3 |
| ADDED | 2 |

**Per block:**
- 85 blocks are fully byte-identical.
- 10 differ only by triangle order.
- **180 of 275 carry a real change.** By most severe class: 151 RETOPO, 28 ATTR, 1 RESHAPE.

Map: `out/block_class_map.png`. The full per-block list is in `out/census_stdout.txt` and `out/census.json`.

**By part (real changes):**
- terrain 165
- object 37
- sea4 34
- sea3 26
- sea5 15
- sea1 11
- riverjoint 5
- beach1 5
- sea2 4
- river 2
- falls 1
- stream 1
- beach2, sea6, sea4f, volcanocrater and volcanolava: 0

**Terrain classes:** 81 IDENTICAL, 143 RETOPO, 14 REORDERED, 11 ATTR:uv, 3 ATTR:id+uv, 3 ATTR:id, 3 ATTR:nrm,
2 RESHAPE.

**Parts added or removed:**
- Object REMOVED at (13,4) (4 tris, in both forms) and at (18,11) (1 tri).
- Object ADDED at (13,12) and (14,12) (36 tris each).
- RiverJoint REMOVED at (19,10) (1 tri).
- Form 2 (`0_2`): 9 of 26 blocks changed (79 identical, 10 RETOPO, 3 REORDERED, 1 REMOVED, 1 ATTR).

**The prefab layer barely moved.** Only 6 of 481 prefab pairs differ in anything other than which mesh asset they
reference:
- (3,9): the Form-2 water materials are swapped to a single material.
- (13,4) and (18,11): Object slot removed (HasSpecialObject 1→0).
- (13,12) and (14,12): Object slot added (HasSpecialObject 0→1).
- (19,10): RiverJoint slot removed.

Transforms are identical everywhere. Disc-4 prefabs point at their own disc-4 mesh copies, even where those
copies are byte-identical. Square did its editing in the meshes.

**Calibration:**
- `calibrate.py` passes 12/12 synthetic checks: lift, retype, retile, re-light, shuffle (both index forms),
  delete plus XZ move, a ground +1 lift, and the local frame.
- It also re-finds 7/7 memory-recorded differing cells: the Daguerreo donors and (9,17).
- `noise_check.py`: of 239 RETOPO/RESHAPE keys, **0 vanish at a 0.002u tolerance**, so no rounding artifacts.
  22 keys are sub-0.1u micro-nudges (deltas such as 0.0039 = 1/256), mostly in sea and beach parts.
- About 208 keys move more than 0.5u.

## 2. Anatomy of the change sites (Q2)

Ground deltas use the engine-faithful sky-cast, with all Form-1 parts in registration order, on a 1u lattice
(`anatomy.py`, `render_maps.py`, `out/delta_map.png`).

Area changed (u²):

| change | area |
|---|---|
| height-only | 16,677 |
| other topograph/walkability | 3,812 |
| raised new rock (walkable → topo 49, rise >0.5) | 2,422 |
| entrance tiles changed | 2,384 |
| land → sea | 1,401 |
| sea → land | 298 |

Walkability flips: about 4,689 samples went walk → blocked; about 305 went blocked → walk.

Six 8-connected clusters: the Mist Continent (78 blocks), Iifa/Outer (27), Shimmering/Lost (15),
Forgotten (35), (9,17) and (9,7).

| site | what changed (measured) | story reading (confidence) |
|---|---|---|
| **Iifa Tree** (11,4) (12,4) (11,5) (12,5) | Terrain and Object retopo'd. 56-97% of each block's area was re-heighted, and **up** at every changed sample: mean +1.08 to +1.28u, max 2.9u. The tree Object rose 1-3u. Topo 59→60 on 98 samples per block. Entrance footprint (event 1) **grew 489 → 1,662 samples**. | The disc-4 Iifa as the gateway to Memoria. The stock world effect `Memoria` is on only when `w_frameDisc == 4` (`WorldConfiguration.cs:211-212` stock). (medium) |
| **Shimmering Island** (6,4) (7,4) (6,5) (7,5) | **Sunk.** 1,856 samples Terrain→Sea4. Terrain tris 287→80 at (7,4) and 187→58 at (7,5), while Sea4 grew in all four blocks (+25 to +83 tris). dy mean −4u, max −11u. Topo 59→57. Entrance tiles re-id'd **event 1→2** and extended onto the new sea. (6,4) and (6,5) gained event-2 tiles. | The Terra gateway disappears after disc 3. (high for "island removed", medium for the event-id meaning) |
| **Cleyra** (13,11) (14,11) (13,12) (14,12) | **All in-block entrance tiles removed** (96+95+18, and 17 of 36). Town ground topo 59→41 (dunes), with 212 samples going blocked→walk. A 36-tri Object was ADDED at (13,12) and (14,12), and it is not disc 1's Form-2 object (15/36 shared). | Cleyra destroyed. The disc-1 tree handles discs 2-3 through the alternate form: `SandStorm` is `w_frameDisc==1 && !UsePlaceAlternateForm(Cleyra)` (`WorldConfiguration.cs:207-208` stock). Disc 4 bakes the after-state into Form 1. (medium-high) |
| **Alexandria / Lindblum objects** | Disc 4's **Form-1 object equals disc 1's Form-2 object.** At (20,10), 180/180 tris match, versus 116/232 against disc-1 Form 1. At (14,17), 121/121, versus 65/113. Alexandria Harbour (21,10) loses all 35 entrance samples, now sea topo 57. (`crescent_probe.py` (c)) | Post-event (destroyed or damaged) states promoted to the default form. (medium) |
| **~53 crescent ridges map-wide**, on all continents | Narrow raised ridges of topo 49 (blocked) laid on **unchanged** walkable ground (topos 0/5/17/27/41). Rise 1.2-3.0u, 1.5-4u wide at half height, 10-22u long, elongation median 6.4. Ground beyond ±6u is untouched (max \|dy\| 0-0.25u). They sample one atlas tile set: 64% of their 14,456 texels fall in 12 of 43 32px cells. By eye, that tile is a fibrous, diagonally grained **bark/root** texture with moss flecks. **The tile is already used on disc 1** (502 tris on 34 blocks, all topo 49), and disc 4 spreads it to **2,095 tris on 116 blocks** (+82 blocks, none dropped). They close or trim entrance footprints: ridge rock covers the lost tiles at Conde Petie Mtn Path (13,3)/(13,4), Esto Gaza (5,3), Oeilvert (6,12), Desert Palace (18,4), Evil Forest (19,11), Ice Cavern (18,12), South Gate (18,14) and Pinnacle Rocks (14,17). | The Iifa roots spreading over the world in disc 4. (medium: the form and texture fit, but it needs an owner or in-game look) |
| Mist | Nothing. Mist is not geometry: `UseMist()` is `SC<5990 \|\| SC>11090` (`WorldConfiguration.cs:223-232` stock), a fog toggle that is also part of the encounter key (see the s75 patch comment). | n/a (law) |
| Water parts | Sea1-5 and beach1 change only where the coast changed (Shimmering, (13-20,15-16)), plus 22 sub-0.1u nudges. Daguerreo: falls and **riverjoint** changed, **river did not** (minor correction to memory's "falls/object/river/terrain/sea"). | — |

Entrance verdicts (`entrance_check.py`, in-block event-bit tiles):
- 16 blocks CLOSED.
- 6 GROWN (Iifa ×4 and Treno ×2, +9 each).
- 2 NEW (Shimmering, on the sea).
- 9 reshaped.
- 1 TRIMMED by raised rock.

"CLOSED" means only that no event-bit tile remains inside that block. Whether the place still dispatches needs the
disc-4 dispatcher decode (open).

## 3. The editing grammar (Q3)

**Square edited by LOCAL RE-CUT.** Over the 165 really-changed terrain blocks (`grammar_summary.py`):
- 68,168 → 69,204 tris (+1,036 net).
- **88.3% of triangles kept byte-exact.**
- 3.8% re-heighted in place: same XZ footprint, new Y.
- 7.9% cut and replaced by 6,455 new tris.
- By XZ area, 8.4% cut and 4.2% re-heighted.
- Per-block touched area: median **9.3%**, p75 17%, p90 35%.
- Only 8 blocks are more than 50% touched: the four Iifa blocks, three Shimmering blocks, and (10,0).

Other features of the grammar:

- **Pure in-place reshape exists, but almost never as a standalone edit.** Only 2 terrain blocks and 1 river are
  RESHAPE-only. Re-heighting mostly happens inside a re-cut; Iifa (12,4) re-heights 343 of 456 tris.
- **Attribute-only edits are a real tool:** id-only retype (3 terrain blocks), uv-only retile (11), normal-only
  re-light (3), and many id/uv edits on sea parts.
- **Land↔sea conversion stays inside the block.** Terrain is cut back and Sea4 is grown in the same cell, with no
  prefab flag change (IsSea stays as baked).
- **New vertices sit on the old lattice.**
  - Disc-4-only corners land on disc 1's existing vertex XZ positions 40-68% of the time, depending on the
    cluster (60% Mist, 68% Iifa, 45% Shimmering, 40% Forgotten).
  - Their 4u-lattice rate is 22-39%, against a stock baseline of 38.4% (12,847 of 33,447 disc-1 verts).
  - So the new geometry follows the stock vertex grammar; it is not a free-form mesh.
- **Welds are kept.**
  - Calibration: all 774 exact edges measure gap 0.
  - Of the 67 block-border edges whose profile changed, 63 are gap-free on disc 4 and **none is worse than
    disc 1** (`weld_gap.py`).
  - The 5 edges that went from "exact" to "open" are T-junctions (gap 0).
  - Stock disc 1 itself has 17 real border gaps (15 of them ≥1u, at cliffs), so "exact weld" is a goal, not a
    stock invariant.
- **No new art.** The two discs share one terrain material (identical PathIDs). New topo-49 tris use **0.18%**
  never-used-on-disc-1 texels (346 of 194,946). The crescents re-use an existing bark tile. Calibration:
  identical blocks show 0 of 2,763,388 virgin texels.
- **Form promotion.** At Alexandria and Lindblum, disc 4 copies Form-2 objects into the Form-1 slot. The Form-2
  slots still exist in the disc-4 prefabs.

**What this says the engine tolerates** (it ships all of the following):
- Arbitrary per-block vertex and triangle counts. For example (7,4) goes 287→80, (18,12) 599→667, and
  Sea4 (7,4) 237→320.
- Retyped IDALLs, grown, removed and re-id'd entrance tiles, and land↔sea swaps inside a cell.
- Part slots added or removed (object, riverjoint).
- None of it needs a prefab/flag or DLL change.

## 4. Tooling interaction: `world/discmirror.py` (Q4, evidence only, no fix)

`mirror_risk.py` runs the module's own `_real_parts` and `_parts_identical` predicates.

- **The gate refuses most of the real map.**
  - `mirror()` (`discmirror.py:276-289`) skips any destination cell whose real parts differ across discs:
    **191 of 275 real cells** (186 by content, 5 by part sets), which is **189 of 260 land cells (73%)**.
    The census predicts the gate on 274/275 cells.
  - An in-place edit of real land therefore reaches disc 4 only about 27% of the time. On the other cells it is
    logged as SKIP and disc 4 shows the stock disc-4 cell.
  - Memory treats (9,17) as the example of a skipped cell. It is actually the majority case.
- **The gate is order-sensitive.** `_parts_identical` (`discmirror.py:83-87`) compares raw vertex lists, so the
  10 reorder-only cells (for example (3,8), (7,3), (12,16), (21,13)) are refused although they are exact
  permutations. That makes it over-conservative, which is harmless.
- **A false SKIP comes from a real `read_block` bug.**
  - `X.read_block(12, 0, disc=4, part="sea4")` returns the **Sea4f** mesh (1,536 verts instead of 1,530).
  - Cause: `extract.py:332-336` matches with `target in c`, and disc 4's `... sea4f.asset` container precedes
    `... sea4.asset` in bundle order. Disc 1 is correct only by ordering luck.
  - So the gate compares disc-1 Sea4 against disc-4 Sea4f and refuses (12,0).
  - Every kit read of disc-4 (12,0) Sea4 gets the wrong mesh.
- **No clobber in the live state.**
  - `FF9CustomMap-world` holds 93 cells (728 files). Every Disc1/Disc4 pair is byte-identical.
  - None of these cells overrides a real part that differs across discs, and none touches a changed border.
  - The only asymmetry is the documented FREE-RIDE PIN `Disc4/.../Block[12][18] Object.ff9mesh`, which pins donor
    (9,17)'s Object.
  - That object is an **exact permutation** across discs (`reorder_check.py` (a)). The pin is therefore
    geometrically redundant, though harmless. This corrects `GROUND-FAMILY-DECODE-2026-07-19.md:741`, which says
    "geometry ... != the disc4 donor Object".
- **Neighbours.** The gate never checks neighbour borders. Measured, though, all 128 block sides whose profile
  changed across discs are land|land, and none faces an open-ocean cell. So the main use case (reclaimed ocean
  cells) cannot crack against a disc-4-changed border today. The risk applies only to future in-place edits on land.
- **The reclaim fallback is safe.** The fallback donor (12,10) is byte-identical across discs, so sidecar-less
  reclaims render the same on both.
- **Buffer order alone can change the ground readout,** at a negligible level. Within a mesh the first passing
  triangle in buffer order wins. In 4 of 10 reorder-only blocks, 8-24 of 16,384 samples report a different
  topograph with dy = 0, consistent with shared-edge ties.

## Contradictions with recorded knowledge

1. **Memory `project-ff9-overworld-worlds.md:23`** says disc 4 is "275 blocks, mostly byte-identical to disc1".
   Measured: only **85 of 275** blocks are byte-identical, 10 are reorder-only, and **180 carry real geometry,
   attribute or part edits**. By (block, part) key, 672 of 998 are identical. This is consistent with the unsourced
   print `verify_s2_family_boundary.py:505` ("260 blocks; 178 differ"): 179 terrain meshes are non-identical.
2. **`ff9mapkit/ff9mapkit/world/extract.py:11` and `cli.py:8960`** say "`0_2` = far LOD". Stock
   `WMWorldPrefabMaker.cs:36,120-127,198-208` and the shipped prefab slots show it is the **Form-2** tree.
3. **`studies/overworld-topography/GROUND-FAMILY-DECODE-2026-07-19.md:741`** says (9,17)'s Object geometry differs
   across discs. Measured: it is an exact full-channel permutation, with a byte difference only.
4. **Memory `project-ff9-overworld-worlds.md:24`** lists "river" among the Daguerreo differing parts. Measured: the
   river parts are identical there; falls and riverjoint differ.

## Open questions and proposed in-game probes

All of these are designed here, none has been run. Harness: memory `project-ff9-test-harness.md`.
Capture: `tools/game_snap.ps1`.

- **Are the crescents Iifa roots?** Cheapest probe:
  1. ~ menu → World → disc switch to 4.
  2. Teleport to (1144,-395) near the Earth Shrine, or (846,-278) on the Conde Petie Mountain Path.
  3. Take a `game_snap`, and try to walk across the ridge. Expect it to be blocked (topo 49).
  4. The owner names the feature.
- **What the Shimmering Island event-2 tiles and the 16 CLOSED blocks dispatch to on disc 4.** Offline: decode
  WORLD08 (9008) with `world/entrance.py` dispatcher loading and the `locate.py` cell-tag join, then check whether
  object-0 tags still cover those cells. In-game: walk onto the old Esto Gaza or Ice Cavern cells on disc 4.
- **Does the edge-tie reading explain the reorder ground deltas?** Offline: recompute those samples with their
  barycentric margins.
