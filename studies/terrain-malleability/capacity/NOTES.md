# Capacity and resolution ceilings of overworld terrain

Lane: **capacity**, part of the terrain-malleability study. The question: how much geometry and
detail can an overworld block hold, and what breaks first?

The lane is offline-only. It reads the user's install, the Memoria source clone and the memory
store, and modifies none of them. Every number below comes from a script in this directory. Every
engine line is tagged **[stock]** (unchanged against base `6b8bb2d5`, checked with
`git diff -U0 6b8bb2d5` on the clone) or **[sNN]** (added by our patch stack).

Rerun everything (about 1.5 min, all read-only):

```
py studies/terrain-malleability/capacity/universe.py
py studies/terrain-malleability/capacity/prefab_children.py
py studies/terrain-malleability/capacity/census.py --rebuild
py studies/terrain-malleability/capacity/form_diff.py
py studies/terrain-malleability/capacity/resolution.py
py studies/terrain-malleability/capacity/unity_limits.py
py studies/terrain-malleability/capacity/live_overrides.py
py studies/terrain-malleability/capacity/predict_reads.py
py studies/terrain-malleability/capacity/live_budget.py 1      (and 4)
py studies/terrain-malleability/capacity/scan_cost.py
py studies/terrain-malleability/capacity/walk_cost_sim.py
```

Outputs go to `out/` and hold derived numbers only (no asset bytes).

---

## THE CAPACITY ENVELOPE

| # | Limit | Value | Source | What breaks | Stock max / margin |
|---|---|---|---|---|---|
| E1 | Vertices per part mesh (native) | **65000** | Unity 5.2.3p2 player string in x64+x86 `FF9.exe` (`unity_limits.py`) | `mesh.vertices=` refused natively, so the part is empty or missing (predicted, see X1) | stock max 2316 verts (Terrain (18,13) disc4), **28x** headroom |
| E2 | Tris per part file under THE UNINDEXED CONTRACT | **21,666** (64,998 verts) | E1 + vcount==icount (`WMBlock.cs:65` [stock]) | same as E1 | stock Terrain max 772 tris, **28x**; deployed max 1549 tris (Disc9 Sea4), **14x** |
| E3 | 32-bit index buffer | **does not exist** | no `set_indexFormat` in the managed `UnityEngine.dll` (calibrated: `get_vertices` found); all 2178 stock meshes are u16 with 1 submesh (`universe.py`) | sharing verts to get past E2 is barred by the contract | none |
| E4 | Loader / kit accepted range | vcount 1..**65535** | `WorldMeshOverride.cs:186` [s34], `mesh.py:121`, pinned by `tests/test_world_ledger.py:197` | **65001..65535 is admitted but natively refused**, a 535-vert gap | latent only: deployed max is 4647 verts |
| E5 | Parts a cell can carry | the **host prefab's child slots only** (+ a bare Object if none) | `WMWorld.cs:582-806` [stock], `:868-884` [s34] | any other part file is never opened (predicted 254 reads of 645 files, matching the log 254/254) | 61% of deployed Disc1 files are dead (harmless stubs) |
| E6 | Distance LOD | **none exists** | no LODGroup in the 962 prefabs; `0_2` is **Form 2**, not a LOD | no LOD pop or stale far-mesh is possible | n/a |
| E7 | Form 2 (story state) | 26 switchable blocks read the key `"... Terrain2"`/`"Object2"` | `WMWorld.cs:823-825` [s34] + bundle child names | a `Terrain`/`Object` override **disappears when the block flips to Form 2** | live overrides on switchable blocks: **0** (latent) |
| E8 | Streaming radius | **none: all 480 blocks resident**, loaded synchronously in one frame | `ff9.cs:3703` `LoadBlocks(false)` [stock]; `WorldState.cs:25` Discard=false [stock] | every override is parsed at world entry. Memory and load time scale with the WHOLE map | deployed disc1 parse: 254 files, 9.24 MB, 177,567 verts, inside a 2-s log window |
| E9 | Ground-query CPU | O(N) linear scan of the block's walk tris, no spatial index | `WMPhysics.cs:13-46` [stock], `WMBlock.cs:137-200` [stock] | uniform refinement x4 tris → **7x** tests per probe; x16 → **45x**; x64 → **~240x** (`walk_cost_sim.py`) | stock about 84-90 tri tests per probe; deployed max block 1388 tris = 1.68x stock max |
| E10 | Texel density, terrain | HD **28-33 px/u** (1 texel ≈ 0.033 u); vanilla 7.7x15.5 px/u | measured UV-Jacobian (`census.py`) + atlas dims (`resolution.py`) | finer geometry adds silhouette and height, not texture detail. A median 4.38 u edge already spans ~133 HD texels | per-cell terrain PNGs are clobbered (X5) |
| E11 | Vertex quantum (stock) | **1/256 u** on 100% of stock verts, all parts, x/y/z | `resolution.py` | float32 `.ff9mesh` has no quantum; the only 1/256 truncation is the legacy actor mirror (`WMActor.cs:47,61`) | n/a |

---

## Findings

### X1. The real per-mesh vertex cap is 65000, not 65535 (contradicts a recorded bound)

**Kind:** law for the cap string; the failure mode is open. **Confidence:** high for the cap.

- Both shipped Unity players (`x64/FF9.exe`, `x86/FF9.exe`) contain the native error
  *"Mesh.vertices is too large. A mesh may not have more than 65000 vertices."* The scan is calibrated
  by finding the two `Failed setting triangles...` messages that every Unity 5 player carries
  (`unity_limits.py` → `out/unity_limits.json`).
- Our loader `WorldMeshOverride.cs:186` **[s34]** (`memoria-patches/s34-worldmap-mesh-override.patch:378`)
  and the kit seam `ff9mapkit/world/mesh.py:121-123` both admit up to 65535, citing "16-bit indices only".
  The drift test `ff9mapkit/tests/test_world_ledger.py:197` pins that literal.
- Under THE UNINDEXED CONTRACT (vcount == icount, `WMBlock.cs:65` [stock]), the true ceiling is
  **21,666 tris per part file**. No 32-bit index path exists: the managed `UnityEngine.dll` has no
  `set_indexFormat`, while `get_vertices` is found.
- Predicted failure for 65001-65535 (open): the native setter refuses, then `mesh.triangles = indices`
  fails with "indices referencing out of bounds". The result is an empty mesh, which means no render and
  no walk tris for that part.
- **Practical impact today: none.** The deployed max is 4647 verts, 14x below the cap. The fix is a
  one-line change of the seam bound to 65000 (and in s34, at the next DLL rebuild).

### X2. `0_2` is FORM 2 (the story-state alternate), not a far LOD (contradicts `extract.py:11` and `cli.py:8960`)

**Kind:** law. **Confidence:** high.

- `0_2` exists for exactly **26 blocks per disc** (`universe.py`). That is exactly the set that
  `ff9.cs:9153-9208` `w_worldChangeBlockSet` → `mw_worldSetFormBit` → `WMBlock.SetForm(2)` can flip
  [stock]. The flip conditions are `WorldConfiguration.cs:165-193` [stock]: South Gate, Alexandria,
  Fire Shrine, Lindblum, Cleyra, Black Mage Village, Water Shrine and Mognet Central/Chocobo Paradise.
  Only the last two (gEventGlobal 101 bits) also apply on disc 4.
- The bundle prefabs bind a child named **`Terrain2`** and one named **`Object2`** to the `0_2`
  meshes. Path_id equality holds for all 26 + 26 (`prefab_children.py`), and it matches
  `WMWorldPrefabMaker.cs:35-36,119-138` [stock, editor-only].
- Form 2 is not a decimation. **97.7%** of form-1 terrain tris (12,262/12,547) recur verbatim
  (geometry + IDALL) in form 2, and 13 of the 26 blocks have identical terrain in both forms
  (`form_diff.py`). There is no LODGroup in any of the 962 block prefabs.
- Rendering and walking switch by Form: `WMBlock.cs:10-19` (`ActiveWalkMeshes`) and `:119-135`
  (`ApplyForm`) [stock].

### X3. The Form-2 override trap: a latent malleability defect (open in-game)

**Kind:** law from source + bundle; the in-game effect is open. **Confidence:** high.

- The s34 key is `"WorldMap/Disc{d}/0_1/r{y}/Block[x][y] " + transform.name` (`WMWorld.cs:823-825`
  [s34; s74 namespace tag]). The `0_1` part is hardcoded.
- A Form-2 component is named `Terrain2`/`Object2`, so its override file must be
  **`0_1/.../Block[x][y] Terrain2.ff9mesh`**.
- An edit to a switchable block's `Terrain`/`Object` therefore **vanishes, both render and walkmesh,
  once the story flips the block**. `override_relpath(lod="0_2")` (`mesh.py:229-235`) builds a path the
  engine never reads.
- **Live check:** 0 of 1686 deployed overrides sit on the 26 switchable blocks, and no file is named
  Terrain2/Object2 (`live_overrides.py`). So the trap is latent, not live. The kit has no awareness of
  switchable blocks (grep: none).

### X4. No streaming and no LOD: the whole map is resident, loaded in one synchronous frame

**Kind:** law. **Confidence:** high.

- `ff9.cs:3703` `ff9.world.LoadBlocks(false)` loads all 480 blocks at `w_frameCounter ==
  kframeEventStartLoop+1` (frame 5) [stock; line 3695 at base].
- `WorldState.cs:24-26` ends Awake with `DiscardBlockWhenStreaming = false` and
  `MaximumLoadAsynce = 2` [stock]. The only `IsReady = false` writer is the discard branch,
  `WMWorld.cs:1311-1327` [stock], so nothing ever unloads.
- `DetectUnseenBlocks` (`WMWorld.cs:1636-1668` [stock]) and its `maxDist` window only gate the
  `UpdateLoadBlocks` load path (`:1285`), which never fires once all blocks are ready. Memoria's
  `[Worldmap] MistViewDistance/NoMistViewDistance` (290/450 on this install) therefore only scale the
  sky/fog dome (`WMWorld.cs:140-146` [stock]).
- Visibility is Unity frustum culling + fog + the projection far plane. That plane is
  `(PsxGeomScreen+ClipDistance)/256`; the field defaults 220/300000 at `WMWorld.cs:2234-2236` give
  about 1173 u. These are public fields a scene may re-serialize, so the far plane itself is a
  hypothesis.
- Consequence: per-block caps are not the binding budget. **Whole-map totals are**: all override parsing
  happens at world entry, and all walk copies stay resident.
- Measured world entry (Memoria.log, 1-s resolution): the 254 disc-1 override loads span 2 timestamps
  (23:55:46-47). That is 9.24 MB / 177,567 verts (`predict_reads.py`).

### X5. Per-cell terrain textures cannot raise texel density while a loose atlas exists (open in-game)

**Kind:** law from source ordering; the in-game effect is open. **Confidence:** medium-high.

- s34's per-cell PNG clone (`WMWorld.cs:835-846` [s34]) runs inside `RegisterBlockComponent`.
  `LoadBlock` then calls `block.SetupPreloadedMaterials()` (`WMWorld.cs:808` [stock]). That call
  reassigns `renderer.material` for every renderer whose GameObject name is in `MaterialDatabase`
  (`WMBlock.cs:106-111` [stock]).
- The database is filled at `WMWorld.cs:63` → `WMBlock.cs:273-306` [stock], for each
  `ObjectNameToPaths` entry (`WMBlock.cs:310-326`) whose texture `SearchAssetOnDisc` finds loose. On
  this install, Moguri supplies Terrain/Terrain2/Object/Object2/Falls/Stream/Quicksand/WaterShrine.
- So a `Block[x][y] Terrain.png` is **overwritten** by the shared atlas material. Sea/Beach/River parts
  are not in the table, so their per-cell PNGs survive (the proven custom-ocean use).

### X6. Stock distribution: block and part ceilings (measurement)

Source: `census.py` → `out/census_cache.json`. Calibrated byte-equal against `read_block` on 3 blocks.

- 2178 meshes, both discs: all u16, all with 1 submesh, **all unindexed (v==i)**, max index value 2315.
- Terrain (disc1 0_1, n=260):
  - tris min 2 / **median 314** / p99 698 / **max 736** at (18,13). On disc 4: median 317 / max 772 at (18,13).
  - Object: n=63, median 37, max 239 at (5,3).
  - Sea4: max 515.
  - Sea4f: 512, the generic ocean fill used for all 205 sea cells.
- Per block, all Form-1 parts:
  - disc1 median 580 / p99 773 / **max 826** at (16,11). Densest: (16,11) 826, (14,17) 817,
    (0,0) 780, (20,10) 771, (17,14) 770.
  - disc4 max 852 at (16,11).
- **Whole-map resident Form-1 tris:** stock 268,565 (disc1) and 269,709 (disc4). This includes
  205 x 512 sea fill. Land verts are 490,815 (disc1).
- **Deployed now** (`live_budget.py`): 285,796 tris, **+6.4%**. The densest effective block is (10,9)
  at **1388 tris (1.68x stock max)**. The largest deployed disc-1 part is 626 tris.
- Terrain resolution (disc1):

  | Quantity | p1 | p5 | p50 | p95 | p99 | max |
  |---|---|---|---|---|---|---|
  | 3D edge (u) | 1.32 | 2.35 | **4.38** | 7.19 | 9.01 | 15.6 |
  | XZ edge (u) | | | 4.05 | | | |
  | 3D area (u²) | 1.08 | | 8.05 | | 20.8 | 41.2 |

  - Min non-degenerate edge 0.30 u, min area 0.153 u². There are 2 degenerate tris, both in (13,18).
  - Density: median 0.077 tris/u², max 0.18.
  - Sub-lattice detail is rare: 566 tris (0.67%) in 66 blocks have every edge < 2 u.
  - Non-up-facing (ny ≤ 0.1) tri share: median 0.93%.
  - **Only 35.3% of terrain verts lie on the 4 u lattice. 100% of all stock verts (every part, x/y/z)
    lie on the 1/256 u PSX grid.** Calibration: Sea4f reads 100%/100%. Terrain is an irregular TIN,
    1/256-quantized, with a ~4 u median edge. It is not a 4 u heightfield; the 4 u lattice is the
    texture/retile frame (`frames.py`).

### X7. Texel density (measurement + law)

- Atlases:
  - Vanilla `res(1_24)_terrain` and `_objects` are 1024x1024 (bundle Texture2D header).
  - The engine resolves Moguri loose files: terrain **2048x4096**, objects **4096x4096** (PNG IHDR;
    `resolution.py`). The 4096² object atlas is new information; memory had no dims for it.
- Terrain UV rate, per-tri isometric Jacobian singular values (median max/min):
  - vanilla **15.5 / 7.7 px/u** (anisotropy 2.0)
  - HD **32.8 / 28.1 px/u** (anisotropy 1.17)
- This is consistent with one atlas tile (`TILE_U,TILE_V = 1/16, 1/32`, `critic_uv_rate.py:45`) per
  4 u cell: 64x32 px vanilla, 128x128 px HD. Two independent routes agree.
- Objects are finer: median edge 1.80 u, HD rate 50.3/37.6 px/u on the 4096² object atlas.
- Implication: texture detail is ~130 HD texels per terrain edge, so finer geometry buys shape, not
  texture. The texture ceiling is the shared atlas (global; per-cell is blocked by X5). The geometric
  floor any stock content uses is 1/256 u.

### X8. The ground-query CPU cost model (law from source + measurement from simulation)

- **Law [stock]:**
  - The full scan iterates the block's Form-1 walk meshes in registration order:
    `WMWorld.cs:588-806`, `WMBlock.cs:185-200`.
  - **Object is first, and it IS a walk mesh** (`RegisterBlockComponent(..., ObjectForm1, true,
    false)` → `AddWalkMeshForm1`, `:848-852`).
  - Each tri pays a cheap mapid/up-facing filter, then **3x `Transform.TransformPoint` + a
    ray/triangle test** (`WMPhysics.cs:13-46`).
  - There is no spatial index. Exactly one block answers (THE BLOCK LAW).
  - The 10-slot cache (`ff9.cs:10749-10760`, `WMBlock.cs:145-179`) saves scans only while the walker
    stays on recently-hit tris.
  - Non-controlled actors run with cache = null, so **a full scan every frame**
    (walk-decode-claims.md step 14).
- **Measurement:**
  - Stock full-scan depth (`scan_cost.py`, 260 blocks x 256 plan points, from-sky upper bound):
    median of block means 300 tris iterated / 289 expensive. That is ~50% of the block's walk tris;
    a miss = all of them, at most 826. Plan miss rate 0 (stock regime calibration holds).
  - Walker simulation (`walk_cost_sim.py`, 3 blocks, 60 walks each, 0.4375 u/tick, 10-ring):

    | Refinement | Tris (block 15,14) | Full scans per probe | Tri tests per probe | Cost vs stock |
    |---|---|---|---|---|
    | stock | 647 | 0.25 | ~88 | 1x |
    | x4 tris | | 0.46 | | **7x** |
    | x16 tris | ~10k, under the 21,666 part cap | 0.74 | | **45x** |
    | x64 tris | ~41k, over the cap, model only | 0.97 | | **~240x** |

  - The law it follows: **cost ∝ N_tris x min(1, step/edge)**. That is ~k³ for edge/k refinement,
    then ~k² once every probe misses the cache. NPCs (no cache) scale as k².
- **Design lever (law):** a **bare Object** override (`WMWorld.cs:868-884` [s34]) is render-only,
  with no `AddWalkMesh`. It is the only way to add visual tris at **zero query cost**, but only on
  blocks with no stock Object. A stock-Object override adds its tris to the FRONT of every full scan.
- Absolute ms cost is **open**. Python timing says nothing about Mono icalls.

### X9. Which override files the engine reads: the effective-prefab model, calibrated in-game (law)

- `predict_reads.py` encodes the source model:
  - land cell → its own prefab
  - reclaimed sea cell → Donor.txt prefab (else (12,10))
  - else → SeaBlockPrefab
  - a part is read iff the host has that child name, or it is the bare-Object case
- It predicts **254** reads of the 645 deployed Disc1 files. The last disc-1 world entry in
  Memoria.log shows exactly those **254 / 254**, with 0 disagreements either way.
- The 391 dead files (68 KB) are `world-island` HIDDEN_PARTS stubs (`island.py:52-53`) for
  Sea1/2/3/5/Beach1 on 78 cells hosted by donor (0,0), which has none of those slots. They are harmless
  no-ops. The one dead Terrain is the documented (11,19) divert-arming stub (`AUDIT-AND-ROADMAP...md:332`).
- The capacity consequence: **a cell's part schema is its host prefab's.** Adding a part type means
  choosing a donor that has the slot.

### X10. Memory model (hypothesis)

- `AddWalkMesh` (`WMBlock.cs:56-82` [stock]) keeps managed copies of vertices, triangles, normals,
  tangents and per-tri normals. That is ≈ **48 B/vertex** resident, plus the native render mesh
  (≈ 50 B/vertex) and parse garbage from `ReadMesh` (`WorldMeshOverride.cs:192-223`).
- Stock disc1 resident ≈ 806k verts → ~80 MB.
- Every land Terrain at the E2 cap (260 x 64,998 verts) → ~1.6 GB, which is fatal for an x86 build.
  The binding budget is whole-map, not per-block.

### X11. The perf memory measures OFFLINE TOOLING, not the game (summary + gap)

- `project-ff9-overworld-perf-assessment.md` profiles the Python kit:
  - `read_block` index + memo took `world-morphs --all` from 211 to 105 s
  - `warm_run` brought crag_anatomy from 3.8 to 0.76 s
  - only pip/near_poly/place are kernel candidates
- **There is no recorded in-game frame-time budget for overworld geometry.** The only in-game perf
  facts on record are the "~1 s overworld reload loop" (owner-confirmed) and the "per-frame exception
  lag" from an unindexed-contract breach.

---

## Contradictions flagged

1. **E4/X1:**
   - Recorded: `mesh.py:121-123` "Unity 5.2.3 has 16-bit mesh indices only; 1..65535", the same bound
     in `WorldMeshOverride.cs:186` [s34], pinned by `test_world_ledger.py:197`.
   - Evidence: the native player caps at **65000**, so the window 65001-65535 is admitted but rejected.
2. **X2:**
   - Recorded: `extract.py:11` "(`0_2` is a far LOD)" and `cli.py:8960` "0_2 = far LOD". The
     overworld README :1222 already calls it a "water-LEVEL form-switch stored in the 0_2 LOD".
   - Evidence: `0_2` = Form 2 (26 switchable blocks, `Terrain2`/`Object2` children, 97.7% verbatim
     terrain). No distance LOD exists.

## Proposed in-game probes (describe only, never run here)

Use the test harness (memory `project-ff9-test-harness.md`) on a scratch cell in a sandboxed namespace.

- **P1 vertex-cap window** (cheapest):
  - Deploy one Terrain override at 64,998 verts (21,666 flat tris, legal) and one at 65,001 (21,667
    tris) on two reclaimed scratch cells.
  - Predict: the first renders and walks; the second shows the native "Mesh.vertices is too large"
    error in Player.log, plus no ground (walker stalls, `game_snap` shows a hole).
- **P2 Form-2 trap:**
  - On disc 4, deploy a visible Terrain edit on (13,4) (Mognet Central, gEventGlobal 101 & 0x80).
  - Toggle the bit with the ~ menu Flags and re-enter the world.
  - Predict: the edit is visible in form 1 and gone in form 2.
  - Then add the same mesh as `Block[13][4] Terrain2.ff9mesh` and predict it is back in form 2.
- **P3 per-cell texture clobber:**
  - Next to an existing Terrain override, add a garish `Block[x][y] Terrain.png`; add the same PNG to
    a Sea4 override as the control.
  - Predict: the Terrain PNG is invisible (X5) and the Sea4 PNG is visible.
- **P4 query-cost curve:**
  - On one bench cell, deploy terrain refined x1/x4/x16 (≤ 21,666 tris), walk a fixed harness path,
    and park 3 NPC actors on the cell.
  - Record ticks per wall-second with `tickrate.py`.
  - Predict: flat at x1 and x4. If anything shows, it shows at x16 (45x the stock tests per probe).
- **P5 world-entry hitch:** time world entry with Memoria.log at sub-second resolution (or harness
  timestamps) for the current 9.2 MB and for 2x/4x the deployed volume. Predict a roughly linear cost.
