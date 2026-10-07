# Capacity lane: adversarial verification

This pass tried to break each finding in `NOTES.md` (CAP-1 to CAP-13). All of it was offline and
read-only on the install, the Memoria clone (`C:\gd\FFIX\Memoria`, base `6b8bb2d5` plus the working-tree
patch stack) and the memory store.

- Every cited engine and kit line was re-opened.
- All 11 lane scripts were re-run.
- Five `verify_*.py` scripts were added to hunt counterexamples.

**Result:** none of the 13 findings is refuted.

- **7 are confirmed:** CAP-1, CAP-2, CAP-6, CAP-8, CAP-9, CAP-11 and CAP-12.
- **6 are corrected:** CAP-3, CAP-4, CAP-5, CAP-7, CAP-10 and CAP-13. Three of these change a number or
  a conclusion a builder would rely on:
  - **CAP-4:** the far-plane figure comes from a code path the game never runs.
  - **CAP-7:** the "stock-like density" figure uses the wrong area unit and is off by about 2x.
  - **CAP-10:** NPC and camera ground queries skip the cheap triangle filters, and the camera queries
    were left out of the model.

## Verdict table

| ID | Verdict | Note |
|---|---|---|
| CAP-1 | **confirmed** | `unity_limits.py` re-run: the 65000 vertex-cap string is in both `x64/` and `x86/FF9.exe`. The calibration strings were found in both. The managed `UnityEngine.dll` has 0 `set_indexFormat` and 1 `get_vertices`. `WorldMeshOverride.cs:186`, `s34...patch:378`, `mesh.py:121-123` and `test_world_ledger.py:197` all say 65535, as cited. The contradiction is upheld. Vertex sharing is genuinely barred: with vcount < icount, `TriangleNormals` is short (`WMBlock.cs:65`) and `WMPhysics.cs:22` indexes it per tri. The failure mode in-game is still open (P1). |
| CAP-2 | **confirmed** | `universe.py` / `prefab_children.py` re-run: `0_2` terrain exists for exactly the 26 blocks, and `Terrain2`/`Object2` bind to the `0_2` meshes. `WMWorldPrefabMaker.cs:120-138` names the `0_2` children `Terrain2`/`Object2` and sets `isSwitchable`. **New:** the runtime scene's `WMBlock.IsSwitchable` set is exactly the 26 cells of `ff9.cs:9153-9208` (`verify_scene_blocks.py`). `form_diff.py` reproduces 12262/12547 = 0.977, with 13 identical blocks. `extract.py:11` and `cli.py:8960` are wrong. |
| CAP-3 | **corrected** | The substance is confirmed: the key at `WMWorld.cs:823-825` hardcodes `0_1` plus `transform.name`, Form-2 children are named `Terrain2`/`Object2`, and `ApplyForm`/`ActiveWalkMeshes` switch both render and walk. One cited range is off: Form-2 registration is `WMWorld.cs:597-600` (ObjectForm2 597-598, TerrainForm2 599-600), not 599-600. A flip takes effect at world construction (`w_worldSystemConstructor`, `ff9.cs:8832`, then LoadBlock and ApplyForm), so on the next world entry. Live exposure is still 0 on disc 1 and disc 4. Disc9 has an override at (14,12), a Cleyra switchable cell, but Path D runs in BLANK mode (`CloneStockWorld=false`, so IsSwitchable is false) and is safe. It is exposed only in the debug CLONE mode. |
| CAP-4 | **corrected** | The no-streaming law is confirmed. `ff9.cs:3703` is the only `LoadBlocks` caller. `OnUpdateLoading` runs only after LoadBlocks sets `LoadingTheRestOfBlocksInBackground` (`WMScriptDirector.cs:109-110`). The 254 log lines are contiguous (Memoria.log lines 41-294, nothing interleaved): one synchronous pass. **The far-plane sub-claim is wrong.** `CreateProjectionMatrix` is called only when `useCustomProjectionMatrix` is true (`WMScriptDirector.cs:348`). That flag is a private, non-serialized bool set only by an editor `[ContextMenu]`, so the PSX projection (and `ClipDistance`, forced to 300000 at `WMScriptDirector.cs:42`) never runs. The runtime far plane is WorldCamera's serialized `farClipPlane` = **1000 u** (near 0.3, read from `level7`/`level19` by `verify_world_camera.py`), not ~1173 u. This answers open question 4. |
| CAP-5 | **corrected** | The read model is confirmed. `predict_reads.py` reproduces 254 predicted, 254 logged, 254/254 agreement, 391 dead files, 68,816 B. The prediction is independent of the log, so the check could have failed. **The example is wrong:** (9,17) has **8** Form-1 slots, and the richest donor is **(16,15) with 10** on both discs (`verify_slots_form2.py`). Script caveat: the scripts treat a cell as "land" if its prefab has a Terrain child, but the engine branches on the scene's `IsSea`. The two disagree on 15 terrain-less open-water cells (for example (8,4), (8,18), (6,17)): those are `IsSea=false` (`verify_scene_blocks.py`). This is latent: no deployed file sits on those cells, and the stock totals are unaffected because each holds exactly 512 tris. HIDDEN_PARTS is `island.py:52`. |
| CAP-6 | **confirmed** | `census.py --rebuild` reproduces every number: 2178 meshes, all u16, 1 submesh, unindexed, max index 2315. Terrain disc1: median 314, p99 698, max 736 at (18,13). Disc4 max 772. Block max 826 at (16,11) (disc4: 852). Totals 268,565 / 269,709. Land verts 490,815. `live_budget.py`: 285,796 (+6.4%), (10,9) = 1388 (1.68x), largest part 626 tris at (1,17). |
| CAP-7 | **corrected** | Quantization is confirmed: 35.25% of verts on the 4 u lattice and 100% on the 1/256 grid. That 100% was checked against kit-authored terrain, which reads a **median of 0%** on the same test (`verify_density_quantum.py`), so the test can fail. Edge, area, degenerate and sub-2u stats reproduce. **Density unit error:** 0.077 tris/u² is tris per whole 4096 u² block, sea included. Per covered plan area the stock median is **0.17** tris/u² (p5-p95 0.13-0.27), and 1 / median tri XZ area is 0.14. A "stock-like 0.08" gate would be 2x too strict. Minor: other 1/256 conversions exist (`ff9.cs:2408`, `4217-4266`), but they are script-facing reads and none touch geometry. |
| CAP-8 | **confirmed** | `resolution.py` reproduces: bundle atlases are 1024², the engine resolves Moguri's loose PNGs at terrain 2048x4096 and objects 4096x4096. The HD rate is 32.84/28.08 px/u, vanilla 15.50/7.71, and a median edge covers 133.4 HD texels. `TILE_U`/`TILE_V` are at `critic_uv_rate.py:45`. Memory records the terrain dims but not the object dims. |
| CAP-9 | **confirmed** | Source order holds: the clone is made at `WMWorld.cs:835-846` [s34], then `SetupPreloadedMaterials` runs at `:808` and `:634`, then `WMBlock.cs:106-111` reassigns by GameObject name. `MaterialDatabase` gets an entry only when a loose texture is found (`WMBlock.cs:290-300`), and MoguriMain ships `res(1_24)_terrain`/`objects`, `11_0_192`, `11_64_192`, `quicksand` and `watershrine` (checked on disk). `WMRenderTextureBank` animates the shared sea materials, never per renderer, so per-cell sea clones survive. The in-game effect is still open (P3). |
| CAP-10 | **corrected** | The scan law and the simulation numbers reproduce: stock 83.7-90.0 tests per probe, then 7.0x, 44.5-46.6x and 233.8-251.9x. Three corrections: **(a)** NPC re-grounds (`ff9.cs:5191-5203`) and camera probes run with `IgnoreExceptions=true`, which skips both cheap filters (`WMPhysics.cs:16-29`). Every iterated tri on those paths is the expensive 3x TransformPoint + ray/tri test. **(b)** 1 or 4 camera-eye ground probes run per frame (`ff9.cs:2943-2988`, cached in `w_cameraHit`). These are an unmodelled consumer. Only the walker's RoundCheck runs cached *and* filtered (`verify_query_sites.py`). **(c)** `scan_cost`'s from-sky first hit is a **lower** bound on scan depth, not an upper bound. The real ray starts 2.34 u above the actor and rejects surfaces above it (`WMPhysics.cs:96`), so it can only scan deeper. |
| CAP-11 | **confirmed** | `RegisterBareObjectOverride` (`WMWorld.cs:868-884`) calls only `AddForm1Transform`. The gate is `:595` (`!ObjectForm1 && TerrainForm1`). A stock Object is registered first (`:588-589`), so its override is first in `Form1WalkMeshes` and every full scan starts on it. |
| CAP-12 | **confirmed** | The perf memory profiles kit tooling only. A memory grep of the overworld, path-d, sea, worldmesh and harness topics finds no in-game frame-time or memory budget. The only in-game timings on record are the owner-confirmed ~1 s reload loop (`project-ff9-overworld-3d-interface-review.md:13`) and the per-frame exception lag (`project-ff9-worldmesh-unindexed-contract.md:21`). |
| CAP-13 | **corrected** | 48 B per vertex of managed walk copies is confirmed (`WMBlock.cs:56-82`: verts 12 + tris 4 + normals 12 + tangents 16 + per-tri normal 4). The arithmetic reproduces: 805,695 verts, and ~1.66 GB with every land Terrain at the cap. **But** the 205 sea cells share one native Sea4f mesh (`sharedMesh`, never cloned), so the ~50 B/vert native cost applies to ~492k unique verts, not 806k. Two costs go the other way and are not modelled: readable meshes also keep a CPU-side copy, and the inactive Form-2 copies are resident (next section). Still a hypothesis until measured in-game. |

## Additional findings

1. **The world far plane is 1000 u, scene-serialized.** The PSX projection path is editor-only (see CAP-4).
   This answers open question 4.
2. **The runtime scene flags were read directly.** The 480 `WMBlock` MonoBehaviours in `level7`/`level19`
   were decoded by layout, with the calibration Number = y*24 + x asserted for all 480.
   - `IsSea` = exactly 205 cells.
   - `IsSwitchable` = exactly the 26-cell set.
   - The 15 terrain-less own-prefab open-water cells are `IsSea=false`. A `Terrain` or bare-`Object` file
     on them never binds, and the reclaim divert never fires. This agrees with the recorded law at
     `project-ff9-overworld-interior-topography.md:957`, the (6,17) case.
   - The lane's read and budget scripts would mis-host these cells. This is latent: there are no deployed
     files on them.
3. **Inactive Form-2 copies stay in memory.** Each of the 78 Uaho cells hosted on the switchable donor
   (0,0) registers that donor's stock Terrain2 + Object2 (423 tris) as inactive Form-2 copies:
   - about 33k tris in total;
   - about 99k verts held in walk arrays, plus GameObjects.

   `live_budget.py` counts Form 1 only. One more cell is hosted on (9,17).
4. **Ground-query consumers by type** (`verify_query_sites.py`):
   - **Cached and filtered:** only the walker's `w_movementRoundCheck`.
   - **Cached but unfiltered:** the camera eye probes.
   - **Null cache and unfiltered:** the NPC re-ground, init, fix-bug, verify-cast and the `w_frameSetParameter` placement calls.

   For P4, the per-frame NPC cost per tri is the expensive test on every tri it iterates.

## Reproduction log

| Script | Re-run result vs claim |
|---|---|
| `universe.py` | 5.2.3p2; disc1 1090 + disc4 1088 = 2178, all u16, all 1 submesh; `0_2` terrain on 26 blocks per disc: **match** |
| `prefab_children.py` | Only Transform/MonoBehaviour/MeshFilter/MeshRenderer; (Terrain2, `0_2`) 26 and (Object2, `0_2`) 26, no UNMATCHED: **match**. Caveat: the binding map is keyed by root name, so disc 1 and disc 4 collide; the mesh-name tail check covers both. |
| `census.py --rebuild` | Calibration OK on 3 blocks; every CAP-6 / CAP-7 number: **match** |
| `form_diff.py` | 12262/12547 = 0.977; 13 identical blocks; (3,9) 22 vs 157: **match** |
| `resolution.py` | Terrain on 4 u lattice 0.3525; 1/256 grid 1.0; atlas dims; rates: **match** |
| `unity_limits.py` | 65000 in both exes; calibration strings 1/1; `set_indexFormat` 0: **match** |
| `live_overrides.py` | 1686 files; max 4647 verts at Disc9 (6,8) Sea4; 0 contract violations; 0 on switchable cells (disc 1/4 only): **match** |
| `predict_reads.py` | 254 / 254 / 254, 391 dead, 9,238,564 B, 177,567 verts: **match** |
| `live_budget.py 1` / `4` | 285,796 / 286,940 tris; (10,9) 1388: **match** |
| `scan_cost.py` | Iterated median 300.4, expensive median 289.3, fraction 0.506, miss rate 0: **match** |
| `walk_cost_sim.py` | 7.0 / 6.9 / 7.1x; 45.5 / 44.5 / 46.6x; 237.8 / 233.8 / 251.9x: **match** |

## Verifier scripts (read-only)

Outputs go to `out/verify_*.json`.

- `verify_world_camera.py`: WorldCamera serialized near/far/FOV from the scene files.
- `verify_scene_blocks.py`: runtime `WMBlock` `IsSea`/`IsSwitchable`, layout-calibrated.
- `verify_density_quantum.py`: negative calibration of the 1/256-grid test; density per covered area vs per block.
- `verify_slots_form2.py`: Form-1 slot ranking, terrain-less own-prefab cells, Form-2 copies on switchable donors.
- `verify_query_sites.py`: every ground-query call site in `ff9.cs`, with its cache argument and `IgnoreExceptions` state.
