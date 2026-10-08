# Terrain malleability study: structure and editability of FF9 overworld terrain

Front page of a ten-lane, read-only study (2026-10-07) of how the overworld block mesh is built, what the engine
actually reads from it, and how far each axis of it can be edited. Written for whoever works on the kit's `world-*`
verbs next.

**Rules this page follows.**
- Only findings whose adversarial verdict is **confirmed** or **corrected** appear as fact. Corrections are applied
  in place, and the finding id is given so the lane `VERIFY.md` row can be checked.
- Hypotheses and unverifiable items are in section 8, kept apart. Refuted claims appear only in the short
  "Refuted during verification" list at the end, so nobody proposes them again.
- Where a lane `NOTES.md` and its `VERIFY.md` disagree, `VERIFY.md` wins.
- Engine cites are `file:line` under `C:\gd\FFIX\Memoria\Assembly-CSharp`, at the **patched working tree** unless
  marked "stock line". STOCK means unchanged against base `6b8bb2d5`; `sNN` means our `memoria-patches/` stack.
- Nothing was deployed, built or fixed by this study. No game file, mod folder or memory file was written.

---

## 1. What this study is, and how to regenerate it

### 1.1 Lanes

| lane (folder) | question | verifier |
|---|---|---|
| `consumption/` | which bytes of a block mesh the engine reads, part by part; which are free | `VERIFY.md` |
| `forms/` | the per-block Form 1 / Form 2 switch: mechanism, triggers, census, override interaction | `VERIFY.md` |
| `capacity/` | ceilings: vertices, tris, texel density, streaming, ground-query CPU cost | `VERIFY.md` |
| `vertical/` | how high and low terrain can go, and which engine systems set the limits | `VERIFY.md` |
| `uvclass/` | UV parameterization classes of disc-1 terrain and how far each stretches | `VERIFY.md` |
| `disc4/` | how Square's own disc-4 tree differs from disc 1 | `VERIFY.md` |
| `operators/` | inventory of all 37 `world-*` verbs; operator x axis matrix | **none** (support lane; F2/F3/F4/F14 verified by `gap_inplace_stitch_composition/`) |
| `gap_area_layer/` | tile AREA bits as an authored layer: consumers, geography, live audit, writer policy | `VERIFY.md` |
| `gap_inplace_stitch_composition/` | the stock stitch graph across parts and blocks; whether in-place edits compose | `VERIFY.md` |
| `gap_disc4_edit_reach/` | how far in-place edits of real land can lawfully reach disc 4 | `VERIFY.md` |

### 1.2 Preconditions

- The user's install (`p0data*.bin` bundles, `level7`/`level19`, `Memoria.log`) and the Memoria clone at
  `C:\gd\FFIX\Memoria`. Python with UnityPy and numpy.
- Decoded mesh caches are written **outside the repo** (OS temp or session scratchpad) to keep the provenance gate
  clear. `out/` folders hold derived counts, coordinates and renders only.
- Scripts that read live mod folders (`bind_oracle`, `live_overrides`, `live_budget`, `predict_reads`,
  `live_override_overlap`, `mirror_risk`, `live_audit`, `area_lint`) reflect the deployed state **at rerun time**.
  Their numbers drift as the owner deploys.

### 1.3 Rerun commands (in order, per lane)

**consumption** (from the repo root `C:\gd\Dream-World-IX`):
```
py studies/terrain-malleability/consumption/provenance.py
py studies/terrain-malleability/consumption/census.py
py studies/terrain-malleability/consumption/consumer_map.py
py studies/terrain-malleability/consumption/bind_oracle.py --log <Memoria.log snapshot>   # calibrated on the owner's 2026-10-06 23:55 log
py studies/terrain-malleability/consumption/landdonor_water.py
py studies/terrain-malleability/consumption/sea4f_vs_sea4.py
py studies/terrain-malleability/consumption/sea_event_quad.py
py studies/terrain-malleability/consumption/matrix.py
py studies/terrain-malleability/consumption/verify_sea_event_all_worlds.py
py studies/terrain-malleability/consumption/verify_dead_files.py
py studies/terrain-malleability/consumption/verify_tangent_natural_experiment.py
py studies/terrain-malleability/consumption/verify_fullvalue_scan.py
```

**forms** (from `studies/terrain-malleability/forms/`):
```
py probe_containers.py
py census_prefabs.py
py probe_scene_worlddisc.py
py probe_worlddisc_backup.py
py probe_prefab.py 3 9 1
py diff_forms.py
py mesh_channel_diff.py
py label_forms.py
py disc4_form2_provenance.py
py orphan_02.py
py live_override_overlap.py
py world_eb_form_writers.py
py rung_site.py
py render_form_map.py
py verify_world_reload_chain.py
py verify_world_eb_mapjumps.py
py verify_raycast_exceptions.py
py verify_noop_exact.py
```

**capacity** (from the repo root):
```
py studies/terrain-malleability/capacity/universe.py
py studies/terrain-malleability/capacity/prefab_children.py
py studies/terrain-malleability/capacity/census.py --rebuild
py studies/terrain-malleability/capacity/form_diff.py
py studies/terrain-malleability/capacity/resolution.py
py studies/terrain-malleability/capacity/unity_limits.py
py studies/terrain-malleability/capacity/live_overrides.py
py studies/terrain-malleability/capacity/predict_reads.py
py studies/terrain-malleability/capacity/live_budget.py 1
py studies/terrain-malleability/capacity/live_budget.py 4
py studies/terrain-malleability/capacity/scan_cost.py
py studies/terrain-malleability/capacity/walk_cost_sim.py
py studies/terrain-malleability/capacity/verify_world_camera.py
py studies/terrain-malleability/capacity/verify_scene_blocks.py
py studies/terrain-malleability/capacity/verify_density_quantum.py
py studies/terrain-malleability/capacity/verify_slots_form2.py
py studies/terrain-malleability/capacity/verify_query_sites.py
```

**vertical** (from the repo root):
```
py studies/terrain-malleability/vertical/engine_bounds.py
py studies/terrain-malleability/vertical/y_census.py            # --rebuild re-extracts
py studies/terrain-malleability/vertical/sea_layer_probe.py
py studies/terrain-malleability/vertical/below_zero_probe.py
py studies/terrain-malleability/vertical/canopy_sink_probe.py
py studies/terrain-malleability/vertical/camera_clip_census.py
py studies/terrain-malleability/vertical/render_bounds_probe.py
py studies/terrain-malleability/vertical/verify_camera_render_eye.py
py studies/terrain-malleability/vertical/verify_sea_rim_and_subzero.py
py studies/terrain-malleability/vertical/verify_form2.py
```

**uvclass** (from `studies/terrain-malleability/uvclass/`; cache at `%TEMP%\ff9_uvclass_cache`, override `$FF9_UVCLASS_CACHE`):
```
py uvc_features.py terrain
py uvc_features.py object
py uvc_census.py terrain
py uvc_census.py object
py uvc_calibrate.py
py uvc_deform.py
py uvc_reconcile.py
py uvc_probe_keying.py
py uvc_probe_flow.py
py uvc_probe_charts.py
py uvc_probe_light.py
py verify_rockwall.py
py verify_rockwall_b.py
py verify_keyspike.py
py verify_mclass_tiles.py
py verify_highland_tiles.py
py verify_cornerpin.py
py verify_cornerpin_stretch.py
py verify_baked_metric.py
py verify_calib.py
```

**disc4** (from `C:\gd\Dream-World-IX\ff9mapkit`; prefix every script with `py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/`):
```
inventory.py
census.py
calibrate.py
noise_check.py
prefab_census.py
anatomy.py
render_maps.py
crescent_probe.py
uv_coverage.py
ridge_art_owner.py
bark_usage.py
mirror_risk.py
weld_gap.py
grammar_summary.py
entrance_check.py
reorder_check.py
verify_prefix_collision.py
verify_lattice.py
verify_prefab_refs.py
verify_freeride.py
verify_weld_uncovered.py
verify_kept_exact.py
verify_virgin_art.py
verify_virgin_form2.py
verify_attr_nrm.py
```

**operators** (from the repo root):
```
py studies/terrain-malleability/operators/inventory_ast.py
py studies/terrain-malleability/operators/study_operator_census.py
py studies/terrain-malleability/operators/writer_gate_census.py
py studies/terrain-malleability/operators/operator_matrix.py
py studies/terrain-malleability/operators/disc_tree_inventory.py
py studies/terrain-malleability/operators/disc_tree_channels.py
py studies/terrain-malleability/operators/disc_mirror_eligible.py
py studies/terrain-malleability/operators/quick_counts.py
py studies/terrain-malleability/operators/donor_part_exposure.py
py studies/terrain-malleability/operators/probe_reshape_read_source.py
py studies/terrain-malleability/operators/probe_island_ground_refusal.py
py studies/terrain-malleability/operators/probe_inplace_excise.py        # exits 3 by design (calibration b unmet)
py studies/terrain-malleability/operators/defs_digest.py transplant coastmorph island interior --lines 10
```

**gap_area_layer** (from the repo root):
```
py studies/terrain-malleability/gap_area_layer/engine_consumers.py
py studies/terrain-malleability/gap_area_layer/eb_consumers.py
py studies/terrain-malleability/gap_area_layer/calibrate.py
py studies/terrain-malleability/gap_area_layer/stock_atlas.py
py studies/terrain-malleability/gap_area_layer/camera_place_effect.py
py studies/terrain-malleability/gap_area_layer/live_audit.py
py studies/terrain-malleability/gap_area_layer/lead_1918.py
py studies/terrain-malleability/gap_area_layer/writer_audit.py
py studies/terrain-malleability/gap_area_layer/area_table.py
py studies/terrain-malleability/gap_area_layer/area_lint.py
py studies/terrain-malleability/gap_area_layer/verify_place_seams.py
py studies/terrain-malleability/gap_area_layer/verify_choco_seams.py
py studies/terrain-malleability/gap_area_layer/verify_eb_area.py
py studies/terrain-malleability/gap_area_layer/verify_fog.py
py studies/terrain-malleability/gap_area_layer/verify_1918.py
```

**gap_inplace_stitch_composition** (from anywhere; prefix `py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/`; optional env `STITCH_SCRATCH`):
```
stitch_census.py
calibrate.py
border_closure.py
calibrate_walk.py
tear_sweep.py
tear_exposure.py
composition_probe.py      # writes only to scratch mod folders under the session scratchpad
gate_coverage.py
engine_cites.py
probe_detail.py
verify_tjunction_numpy.py
verify_claims.py
verify_object_walls.py
verify_baseline_artifact.py
```

**gap_disc4_edit_reach** (from `C:\gd\Dream-World-IX\ff9mapkit`; prefix `py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/`; optional env `GAP_DISC4_CACHE`):
```
s0_cache.py               # --rebuild re-decodes
s1_gate.py
s2_footprint.py
s3_tieground.py
s4_calibrate.py
s5_reach.py
s5b_crack_demo.py
s5c_border_welds.py
s5d_wallgate_preexisting.py
s6_semantic.py
s7_morph_replay.py        # ~10 min; has a 600 s wall-clock guard that could truncate on a slow host
s8_summarize.py
verify_area_pairing.py
verify_writer_atomicity.py
verify_dispatch_triggers.py
verify_w08_cases.py
verify_newpos_blind.py
verify_wallgate_population.py
```

---

## 2. The structure model

Each layer below is what the next layer is built from. Every row cites the code or census that establishes it.

| # | layer | what it is | key facts | evidence |
|---|---|---|---|---|
| 1 | **World grid** | 24 x 20 blocks of 64 u (480 cells), an x/z torus | `Wrap` shifts blocks in 64 u steps (`WMWorld.cs:1114-1146`, stock). Event dispatch uses a 32 u **event cell** (2 x 2 per block) packed into object-0 cell tags of the world `.eb` (`ff9.cs:2233`, `:5345-5352`). No stock mesh exists in column 23 or row 19, so no stock stitch crosses the wrap. | operators §1; stitch S15 |
| 2 | **WorldDisc skeleton** (scene `WMBlock`s) | 480 typetree-stripped `WMBlock` MonoBehaviours in `level7`/`level19` | Runtime truth for `IsSea` (exactly 205 cells) and `IsSwitchable` (exactly 26 cells). 15 terrain-less open-water cells (e.g. (8,4), (8,18), (6,17), (12,0)) are `IsSea=false`. Form lists serialize empty. Cannot be overridden from a mod folder. | capacity verifier `verify_scene_blocks.py`; forms F9 |
| 3 | **Block prefabs** | per-disc baked prefabs (480 + `Block[12][0]f`), each a set of named child slots | `SeaBlockPrefab = WorldDisc1 Block[12][0]f`, loaded from disc 1 even on disc 4 (`WMWorld.cs:1198-1200`, stock); its only child is `Sea4` (mesh `sea4f`). `LandDonorPrefab = Block[12][10]` of the current disc (`:1210-1211`, s34), which is an islet with Sea1/3/4/5, not plain land. 205 disc-4 ocean prefabs reference the **disc-1** (12,0) Sea4/Sea6 meshes. | consumption C6, C7; disc4 D4-03 |
| 4 | **Effective prefab** (which prefab a cell loads) | `IsSea=0` → own prefab. `IsSea=1` and a `Block[x][y] Terrain.ff9mesh` file exists → `Donor.txt` prefab, else `Block[12][10]`. Otherwise → `SeaBlockPrefab`. | Routing `WMWorld.cs:516-544`; donor `:549-569`; divert armed only by `File.Exists` (`WorldMeshOverride.cs:80-83`, s34). The Terrain stub's content is irrelevant when the donor has no TerrainForm1. Predicts the engine's ordered load list 81/81 blocks (254/254 lines) on disc 1. | consumption C6; capacity CAP-5 |
| 5 | **Parts** (child names) | Terrain, Object, Terrain2, Object2, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1-6, Sea3_2/4_2/5_2, VolcanoCrater1, VolcanoLava1, VolcanoLava2 | Registration order: Object, Terrain, bare-Object rule, Object2, Terrain2, block-219 early return, Volcano*, Beach1/2, Stream, River, RiverJoint, Falls, Sea1-6 (`WMWorld.cs:582-810`). The child **name** is the override namespace. The volcano child is `VolcanoCrater1`, not the mesh asset name. A stock child with no override registers its own stock mesh (free rider). | consumption C5 |
| 6 | **Forms** | Form 1 = `0_1` mesh set; Form 2 = `0_2` mesh set, used only by the 26 switchable cells | `0_2` is **not a far LOD** (`WMWorldPrefabMaker.cs:36,120-139`). Form 2 replaces Form 1 in the walk list (`WMBlock.cs:10-20`); water/beach/river/falls register in both. Decided once per world load from ScenarioCounter, `gEventGlobal[101]` and `Environment.txt` (`ff9.cs:8832` → `:9153-9208`). 38 orphan `0_2` water meshes per disc are never loaded. | forms F1-F3, F9, F12, F16; capacity CAP-2 |
| 7 | **Discs** | Disc 1 tree, disc 4 tree, Path D namespace (Disc9, s74/s75) | Disc 4 is a local re-cut of disc 1: 85/275 blocks identical, 10 reorder-only, 180 really edited (section 4.7). Path D runs in BLANK mode (every cell treated as sea, `CloneStockWorld=false`). | disc4 D4-01; consumption C5 |
| 8 | **Residency** | no LOD, no streaming | All 480 blocks load synchronously in one frame at world entry and are never discarded (`ff9.cs:3703` `LoadBlocks(false)`; `WorldState.cs:25` `DiscardBlockWhenStreaming=false`, stock). World camera: near 0.3, far 1000 u, FOV 45, scene-serialized (the PSX projection path is editor-only). | capacity CAP-4 + verifier; vertical V7 |
| 9 | **Mesh attributes** | position, normal, uv0, tangent; nothing else | All 2178 stock meshes: channel mask 139, 1 submesh, u16 indices, flat (vcount == icount), permuted index buffer. tangent.y/z/w = 0. tangent.x equal on all three corners. Vertices quantized to 1/256 u (100%); 35% on the 4 u lattice; median 3D edge 4.38 u. Max stock vcount 2316. | consumption C1; capacity CAP-6, CAP-7 |
| 10 | **IDALL** (corner-0 tangent.x) | per-triangle id | event `(id&0xC000)>>14`, area `(id&0x3F00)>>8` (6 bits, 64 values), topograph `(id&0xFC)>>2`, flags bits 0-1 (`ff9.cs:2335-2348`). Read from corner 0 only (`WMBlock.cs:210/231`). | consumption C3; gap_area GA15 |
| 11 | **Engine consumers** | renderer, walk/vehicle physics, IDALL consumers, camera, shadow | See the table below. | consumption C2-C4, C12; gap_area GA1-GA4 |
| 12 | **Override loader** (s34) | `TryLoad("WorldMap/Disc{tag}/0_1/r{y}/Block[x][y] " + child name)` (`WMWorld.cs:823-825`) | `0_1` is hard-coded, so Form-2 overrides are named `Terrain2`/`Object2` and still live under `0_1`. A file with no matching child is never opened and logs nothing; a bound malformed file logs `Log.Error` (`WorldMeshOverride.cs:52`). Bare-Object override (no stock Object) is render-only (`WMWorld.cs:868-884`). Per-cell PNG hook exists (`:835-846`) but is overwritten for Terrain/Terrain2/Object/Object2/Falls/Stream by `SetupPreloadedMaterials` (`:808` → `WMBlock.cs:106-111`) on this Moguri install. | consumption C5, C10; capacity CAP-9, CAP-11 |

**Engine consumers of block-mesh data** (all stock unless marked):

| consumer | reads | cite |
|---|---|---|
| Renderer, `WorldMap/Terrain` shader (Terrain, Terrain2, Object, Object2, Sea1-6, Sea*_2, Beach, River, RiverJoint, Volcano*) | position + uv0 only; uniform lighting (no normal) | consumption C2 |
| Renderer, `WorldMap/ScrollTexture` (Falls, Stream) | position + **normal** + uv0; N·L against the 3 world lights | consumption C2 |
| Back-face culling | winding (no world shader sets Cull, so Cull Back) | consumption C12 |
| Walk / vehicle ray | position, index order (first up-facing hit in buffer order), recomputed geometric normal, corner-0 tangent.x; 10-slot hit cache tested first (`WMPhysics.cs:6-47`, `WMBlock.cs:145-162`) | consumption C3; capacity CAP-10 |
| Full-value IDALL tests (flag bits matter only here) | 10 distinct values: 4078/4088/2040 skipped unless IgnoreExceptions; 0x31EE whole-mesh veto unless control type 1; 0x18EE/0x7EE/0x1BEE/0x2CEE (and 0xFEE=4078) make actor indices 1, 2, 11, 3-7 (party, mog, chocobos) keep their stored height (`ff9.cs:5209-5232`); 56/57 at `ff9.cs:3310` (never true on stock data) | consumption C3 corrected; vertical V14 corrected |
| Topograph | movement masks, sink, get-off, encounter record, sysvars 193/205, dust SPS, spray SE, chocobo, camera speed (49), encounter re-arm (52) | consumption §2 |
| Area (7 channels) | encounter zone (`ff9.cs:9237`; s60 adds the record hole), per-zone ENCRATE via sysvar 207, camera place (`ff9.cs:81` table read at `:3117`, every frame), area-12 camera lock below scenario 4990 (`:2771/:3199`), one-shot spawn weather for areas 9/12/13 (`:8508-8510`), labels (window title, main menu `MainMenuUI.cs:527`, save-slot Location `UIManager.cs:586-587` → `SharedDataBytesStorage.cs:482`), beach search (`EMinigame.cs:726` + WORLD08) | gap_area GA1-GA4 |
| Event | `WorldEvent` dispatch by cell tag (`ff9.cs:5345-5352`); UI: `DialogManager.cs:366/387`, `EIcon.cs:131`, `EventInput.cs:206` | consumption C9 verifier |
| Camera eye probes | sky cast under IgnoreExceptions, first-in-buffer hit, no cheap filters (`ff9.cs:2943-2988`) | capacity CAP-10 corrected |
| Shadow | ground height only (`ff9.cs:5146`) | consumption §2 |
| Minimap / navimap | no mesh data | consumption §2 |
| `Has*` flags on WMBlock | write-only (debug menu reads them) | consumption C11 |

---

## 3. The malleability matrix

Status: **in-game** = owner-played or harness-proven before this study; **offline** = proven from source and census
only; **open** = needs an in-game run. Kit operators come from the operators lane inventory (`operators/NOTES.md`
§3-4), a support lane without its own verifier; operator facts that were cross-verified cite the verifying lane.

| axis | lawful range (measured) | binding constraint | kit operator | status | gap |
|---|---|---|---|---|---|
| **Vertical reshape, real land** | continuous slope walkable to ~79.4° on lawn (2.34375 rise per 0.4375 u tick); a seam step above 2.34375 u, or above 1.171875 u when starting on topo 36/37/38, is a wall | `ff9.cs:1328`, `:5509`, `:5666`, `:5700` (stitch S16, vertical V3) | `world-terrain`, `world-deploy` (pure Y, Terrain part only) | in-game (interior hills) | moves Terrain only and tears cross-part welds (S5); last writer wins (S3); no entrance guard (S9); not edit-atomic (gap_disc4 A1) |
| **Vertical reshape, kit land** | same walk law | same | `world-hill` (raised cosine), `world-mountain` (rigid rock carry + pure-Y apron) | in-game | `world-mountain` keeps rock rigid (`MTN_ROCK_RIGID` 0.035); relaxing it needs experiment X1 first (UV-07) |
| **Absolute height** | stock: terrain −5.82..42.68, walkable to 34.07 (topo 36), plateau grass 25.6-28.8, sub-zero walkable only in the (2-3,7) basin to −5.77 | flight clamp 42.1875 applied after the floor raise, so an airship sits inside taller rock (`ff9.cs:5513-5520`); terrain taller than ~51 u under the camera can contain the rendered on-foot eye (~41.2 u for low actors in areas 40-45; ~52-52.8 u for airships); rendered eye cap 73.99 u; in the R2 high camera the cap binds for walkers above ~42.5 u; framing adapts only for actor y −3.9..13.67; mist height-fog plane at 29; sky casts see nothing above actor y + 400 | any Y writer | offline | no kit lint for the camera and flight bands |
| **Horizontal reshape / outline** | L.rule ground: per-vertex XZ moves with carried corner UVs are stock-normal to p90 1.12 u in the interior (1.51 u overall, mostly at class seams); plan scale ±10% (x1.1: 92.7% inside the stock envelope; x1.25: 26%); rotation about Y causes no facet-level baked-light error (painted light inside a ground tile under a free angle is untested); 90° steps keep the lattice | uvclass UV-04, UV-05, UV-08 (corrected) | `world-transplant` (rotation 0/90/180/270, shift 0 mod 4, row inserts, coast morphs), `world-island`, `--in-place` morphs | in-game per flag | free-angle carry untested (X5); `morph_in_place` co-moves only `transplant.PARTS`, so 952 Terrain positions welded to Object/River/Beach2/Sea6 tear unseen (S11) |
| **Retexture a region (UV)** | any UV: render-only, zero gameplay effect | `WorldMap/Terrain` binds uv0 (C2); UV read nowhere else (UV-01) | `GroundRetile`, `TileRetexture` (carries only), `world-rim-retile` (water only) | in-game for carries | per-cell Terrain/Object PNG is overwritten by `SetupPreloadedMaterials` (CAP-9, C10), so per-block re-baking needs an engine change |
| **Retexture globally** | one shared atlas: terrain 2048x4096, objects 4096x4096 (Moguri HD); 28-33 HD px/u | `WMBlock.cs:273-326` (CAP-8) | `world-atlas-reskin`, `world-atlas-add-tile` | offline | finer geometry adds silhouette, not texture (a median edge spans ~133 texels) |
| **Re-topograph** | any topograph per triangle, as long as the full IDALL avoids the 10 special values | corner-0 tangent.x (C3); movement mask `ff9.cs:5924-5939` | `world-retarget` (circle), `world-coastnav` (water), transplant ground retile | in-game | 14 flight-blocked topographs {8,9,14,15,24,25,26,29,39,40,43,44,47,63} are unused anywhere in stock (V12); as no-fly walls they are unplayed |
| **Area re-stamp** | 64 areas, all used by stock. Walkable ground must not change camera place across a walkable edge (stock: 0 such seams on both discs, also for chocobos). Area 12 locks the camera below scenario 4990. Areas 9/12/13 set spawn weather. | the 7 area channels (section 2, GA1-GA4) | `world-retarget --area` (user flag); `world-entrance` stamps area := case by default; island/reclaim/mesh emitters stamp 0; `world-mountain` strips to 0; `world-forest`, transplant and Path D carries keep the donor's area | offline; area-14 safe road in-game | no area policy in the kit; policy R1-R10 and lint AL1-AL8 proposed (`gap_area_layer/NOTES.md` §E) |
| **Event / entrance tiles** | event bits 14-15; the destination is the world `.eb` object-0 cell tag, not area | `ff9.cs:5345-5352` | `world-entrance` (reads stacked; tiles + building + `.eb` trigger) | in-game | a later `world-terrain`/`world-retarget` erases the 312 event corners and leaves a dangling `.eb` trigger (S3) |
| **Add land** | whole 64 u ocean cells | the divert (layer 4); 15 `IsSea=false` water-only cells cannot take land at all | `world-island`, `world-reclaim`, `world-transplant`, `world-coast`, `world-fuse`, `world-water` | in-game | a sidecar-less reclaim loads `Block[12][10]`, whose Sea1/3/4/5 (97.3% of the cell) free-ride under the new land (C7) |
| **Remove land** | stock does it by re-cut (disc-4 Shimmering Island: 1,856 samples Terrain → Sea4, event 1 → 2) | water must be a part of the cell's effective prefab | no primary operator (operators F11, unverified) | open | no land → sea operator for real land |
| **Density / detail** | ≤ 21,845 tris (65,535 verts) per part file, **in-game proven** (`ingame/RESULTS.md` §8; CAP-1's 65000 refuted); stock terrain max 772 tris/part, block max 852 | the s34 loader's 65535 bound (16-bit indices) with the unindexed contract; no 32-bit index | any emitter | in-game | ground query is a linear scan: x4 tris → 7x tests per probe, x16 → 45x, x64 → ~240x; NPC and camera probes skip the cheap filters (CAP-10). A bare-Object override is the only zero-query-cost detail (CAP-11). No in-game frame budget exists (CAP-12). |
| **Story / runtime form switch** | 26 switchable cells in 9 places; a mod-folder `Environment.txt` `Place <name> [Condition=<NCalc>]` replaces a place's condition with no DLL and can test any `gEventGlobal` byte | `ff9.cs:9153-9208`; `WorldConfiguration.cs:165-193`; `SetForm` is a no-op unless `IsSwitchable` (`WMBlock.cs:97-104`) | `world-environment` (`[[place]]`); `override_relpath(part="Terrain2")` exists, no form-2 writer | offline (rungs F0/F1 designed) | no clean mid-visit switch and no world-script world reload (F4 + forms A1); kit Terrain/Object edits on switchable cells are Form-1 only (F14); any other cell needs one ~50-line engine patch (F15); kit never emits `Clear` (F7) |
| **Water parts** | Sea1-6, Beach1/2, River, RiverJoint, Falls, Stream, in both forms. Open sea at y = 0; Form-1 shallow rims ramp to +0.8 at the shore; Form-2 (3,9) sea4 reaches +1.527. | registration `WMWorld.cs:748-807`; Falls/Stream normals are lit (C2) | `world-water`, `world-coastnav`, `world-rim-retile`, transplant `PARTS` | in-game | a Terrain-only Y edit leaves welded Sea/Beach vertices behind (S5); one-way walls at ±3 u in 149-154 of 154 beach edits (S6) |
| **Objects** | an Object override renders and walks when the host has a stock Object; with no stock Object it is render-only | `WMWorld.cs:588-596`, `:868-884` | `world-entrance` (building), `world-mesh-build` (OBJ) | in-game | Terrain Y edits near objects move entrance tiles in 54-74% of object-centred edits (S6) |
| **Free bytes** | tangent.y/z/w; tangent.x on corners 1-2; normals except Falls/Stream; vertex order (indices remapped); mesh name; bounds; flag bits away from the special values; unbindable override files | C11 | none | offline (163 receipted live files carry nonzero y/z/w) | a provenance side channel is possible but unplayed |
| **Disc-4 coexistence** | byte gate passes 84 of 275 real cells (71 of 260 land); order-invariant compare adds 10; per-part compare adds 14 more; parametric replay on disc-4 stock is lawful for 99.8% of synthetic edits, hazard-free for 63.7% | `discmirror.py:273-289` (D4-16, G1, G4) | `auto_mirror` in each writer; `world-mirror`; per-verb `--disc 4` | offline | per-cell skip cracks multi-cell edits (7.5%; 4.0 u step shown, G3); the writer itself is not atomic (A1); no replay hook |
| **Path D (Disc9)** | BLANK mode: every cell routes through `Donor.txt`; carried cells keep donor areas (10 areas, 7 zones, 3 camera places, 0 place seams) | s74/s75 | 11 verbs take `--target-disc` (operators F10, unverified) | in-game (9013 round trip) | bind oracle uncalibrated for Disc9 (C5) |
| **Multi-block / multi-part stitch** | stock is one conforming mesh: 0 T-junctions; moving every coincident instance in all parts by the same f(x,z) keeps every weld | stitch S1 | `world-terrain` moves Terrain-Terrain borders identically; transplant runs `weld_audit` (0 near-miss pairs) | offline | `weld_audit` cannot see a tear larger than 0.05 u (S10); no stitch gate anywhere |
| **Repeated edits on one real block** | entrance and interior verbs stack; the four pristine writers replace | stitch S3 | — | offline (scratch probes) | stacking read missing in `terrain.reshape`, `world-deploy`, `world-retarget`, `morph_in_place` |

---

## 4. New laws discovered (verified)

Each line: the law, its source, and the script that shows it.

### 4.1 What the engine reads

| law | cite | script |
|---|---|---|
| Every stock block mesh carries exactly position, normal, uv0, tangent; flat, u16, 1 submesh, permuted indices; tangent.y/z/w = 0; tangent.x corner-uniform. | consumption C1 | `consumption/census.py` |
| `WorldMap/Terrain` parts render from position + uv0 only; only Falls and Stream (`ScrollTexture`) read the stored normal. | C2 | `consumption/census.py`, `matrix.py` |
| Walk reads corner-0 tangent.x only; flag bits are read only through full-value equality, against 10 distinct values. | C3 corrected | `consumption/consumer_map.py`, `verify_fullvalue_scan.py` |
| Tile area has 7 consumer channels (encounter zone, ENCRATE, camera place, area-12 lock, spawn weather, three labels, beach search); 12 reader rows, 10 stock and 2 patch. | GA1 corrected, C4 | `gap_area_layer/engine_consumers.py` |
| Camera place by area: 0-26 and 46-50 → place 0; 40-45 → place 1; 27-39 and 51-63 → place 2. Stock has 0 walkable-to-walkable place seams on both discs, for walkers and ground chocobos. | GA2 | `gap_area_layer/camera_place_effect.py`, `verify_place_seams.py`, `verify_choco_seams.py` |
| Crossing a place seam on foot snaps camera distance and FOV in one frame; eye height eases (±1 u dead band). Source-derived, not yet observed in-game. | GA14 corrected | source read, `ff9.cs:3157-3158`, `:3007-3071` |
| Area 12 (scenario < 4990) forces the perspective counter **down** to the default near view and refuses the toggle to the high view. | GA3 | source read, `ff9.cs:2771`, `:3123-3133`, `:3199` |
| The world `.eb` reads sysvar 192 exactly once in the corpus (WORLD08 beach-search switch, 21 arms = `EMinigame.BeachData`) and sysvar 207 only for the 25-arm ENCRATE ladder of each free-roam dispatcher. | GA4 corrected | `gap_area_layer/eb_consumers.py`, `verify_eb_area.py` |
| All 64 area values are used in stock; area boundaries follow terrain, not block borders; camera place is constant per continent. | GA5 corrected | `gap_area_layer/stock_atlas.py` |
| "Area 15" on override Objects and Disc9 terrain is the walk-skip IDALL 4078 (0x0FEE) decoded, not an area. | GA9 | `gap_area_layer/live_audit.py` |
| Area is 6 bits: both engine tables have 64 entries. | GA15 | `gap_area_layer/engine_consumers.py` |

### 4.2 Which prefab and which files bind

| law | cite | script |
|---|---|---|
| The override namespace is the effective prefab's child names; a file with no matching child is never opened. | C5 corrected | `consumption/bind_oracle.py`, `verify_dead_files.py` |
| The effective prefab decides everything: the Terrain **file's existence** arms the sea-cell divert; Sea registration never depends on Terrain. This resolved the (11,19) defect. | C6 | `consumption/bind_oracle.py` (81/81 receipts) |
| `Block[12][10]`, the fallback land donor, is an islet: water covers 97.30% of the cell, 93.27% boat-legal. | C7 | `consumption/landdonor_water.py` |
| The runtime open-ocean mesh `sea4f` is `(12,0)` Sea4 plus the Sea6 quad (IDALL 16612, event 1), so every IsSea cell carries an event-1 tile at event cell (2bx+1, 2by+1); it collides with no trigger in any of the 13 dispatchers. | C9 | `consumption/sea4f_vs_sea4.py`, `sea_event_quad.py`, `verify_sea_event_all_worlds.py` |
| The read model predicts the engine's reads exactly (254/254 disc-1 log lines); 391 of 645 deployed disc-1 files are intentional dead stubs. | CAP-5 corrected | `capacity/predict_reads.py` |
| A bare-block Object override is render-only, so it is the only way to add triangles at zero ground-query cost. | CAP-11 | source read |

### 4.3 Forms

| law | cite | script |
|---|---|---|
| `0_2` is the Form-2 mesh set, not a far LOD; the overworld has no distance LOD at all. | F16, CAP-2, C8, D4-02 | `forms/census_prefabs.py`, `capacity/universe.py` |
| A form switch swaps walk, render and IDALL of a block together; Form 2 replaces Form 1 in the raycast. | F1 | `forms/label_forms.py` |
| The form is decided once per world load, before any block loads, and never saved; stock reloads are battle return, field → world entry and save load. | F3 corrected | `forms/verify_world_reload_chain.py` |
| No stock path changes form mid-visit cleanly: `RunWorldCode(501)` switches walk only, no dispatcher uses it, and a world-originated `WorldMap()` does nothing (WMAPJUMP returns 5; the world tick handles 3 and 4). | F4 corrected, forms A1 | `forms/verify_world_reload_chain.py`, `verify_world_eb_mapjumps.py` |
| Place conditions are data: `Environment.txt` replaces a place's default condition, re-parsed on every world load; conditions from several mod folders are OR'd; the parser accepts `Clear`, while Memoria's shipped doc says `Clean`. | F6, F7 corrected | `forms/label_forms.py` |
| Disc 1: of the 26 switches, 9 change nothing (Black Mage Village's 3 cells identical as ordered arrays), 4 change render/IDALL only, 13 change geometry; stock uses the switch to remove Cleyra's entrance tiles and add the Water Shrine's. | F10 | `forms/diff_forms.py`, `verify_noop_exact.py` |
| Disc 4's Form-2 meshes are mostly stale disc-1 copies (Terrain2 on 15/20 disc-gated cells). | F11 | `forms/disc4_form2_provenance.py` |
| Any kit Terrain/Object override on a switchable cell is Form-1 only and vanishes when the place flips. | F14, CAP-3 corrected | `forms/live_override_overlap.py` |
| A non-switchable cell cannot be made switchable from data (`SetForm` gates on the scene `WMBlock`). | F15 | source read |
| The world `.eb` itself writes the Chocobo's Paradise / Mognet bits 814/815 from 6 free-roam dispatchers. | F8 corrected | `forms/world_eb_form_writers.py` |

### 4.4 Capacity

| law | cite | script |
|---|---|---|
| ~~The per-part ceiling is 65000 native vertices (21,666 tris).~~ **REFUTED in-game** (`ingame/RESULTS.md` §8): 65,001- and 65,535-vertex parts render and walk; the ceiling is s34's 65535 (21,845 tris). No 32-bit index path exists. | CAP-1 | `capacity/unity_limits.py`, `ingame/vcap_build.py` |
| No streaming: all 480 blocks load synchronously at world entry and stay resident; far plane is the scene-serialized 1000 u. | CAP-4 corrected | `capacity/verify_world_camera.py` |
| Stock terrain is an irregular mesh on a 1/256 u grid; stock density per covered plan area is a median 0.17 tris/u² (p5-p95 0.13-0.27). | CAP-7 corrected | `capacity/resolution.py`, `verify_density_quantum.py` |
| Ground-query cost is a linear scan; uniform refinement costs ~k³ then ~k² per probe; NPC re-ground and camera probes skip the cheap filters. | CAP-10 corrected | `capacity/walk_cost_sim.py`, `verify_query_sites.py` |
| Inactive Form-2 copies of a switchable donor stay resident on every cell hosted on it (78 Uaho cells on (0,0): ~33k tris). | capacity verifier finding 3 | `capacity/verify_slots_form2.py` |

### 4.5 Vertical

| law | cite | script |
|---|---|---|
| All 64 vertical-bound engine constants are stock Memoria. | V1 corrected | `vertical/engine_bounds.py` |
| Canopy sink: on topo 36/37/38 the on-foot party and chocobos sit 1.171875 u below ground, so the climb ceiling from there is 1.171875 u (steepest head-on slope 69.53° on foot, 56.31° on a chocobo). | V3 | `vertical/canopy_sink_probe.py` |
| The controlled walker has no Y ceiling or floor; a ground-query miss refuses the step (a hole is a wall). | V1, V14 corrected | `vertical/engine_bounds.py` |
| Flight ceiling 42.1875 is applied after the floor raise, so over taller rock the airship sits inside it; stock summits exceed it by ≤ 0.49 u on 3 u². | V4 | `vertical/y_census.py` |
| The camera that renders is the internal eye plus a FixTypeCam offset: +2.18 u on foot, +5.54 u airship, +1.25 u Narciss. | V5 corrected | `vertical/verify_camera_render_eye.py` |
| No WorldMap shader bends geometry: every bound world shader except Unity's Standard passes a strict pure-MVP check with negative controls; the view is limited by fog and the 1000 u far plane, not by streaming. | V7 corrected | `vertical/render_bounds_probe.py` |
| The mist height-fog plane is y = 29. | V8 | source read `ff9.cs:8553-8554` |
| Sea sheets: open water at 0; Form-1 shallow rims ramp to +0.8 under land; Form-2 (3,9) sea4 rises to +1.527. | V9 corrected | `vertical/sea_layer_probe.py`, `verify_form2.py` |
| Walkable sub-zero ground exists only in the (2,7)/(3,7) basin (to −5.774); no water sheet ever covers sub-zero land. | V10 | `vertical/below_zero_probe.py` |
| Airship landing: up to 16 headings, each 8 collinear probes reaching 1.6x radius (4.0 u Hilda Garde, 4.5 u Invincible); all must be foot-legal, only the last height is compared (≤ 1.367 u). | V13 corrected | source read `ff9.cs:5839-5889` |

### 4.6 UV and texture

| law | cite | script |
|---|---|---|
| UV is consumed only by rendering; every texture law is a look law. | UV-01 | source read |
| The UV class follows the topograph family: walkable ground is 74.6-98.5% tile-scale charts of shared art (class L); wall families are 2.2-5.4% L (lip 58: 2.2, bank 62: 3.5, rock 49: 5.4). | UV-03 corrected | `uvclass/uvc_census.py` |
| About 16% of all disc-1 terrain area (40% of the M class) is exact 128 px tile-window rect-halves; the rock tile lattice phase is u 8 / v 64 px; 73.5% of (14,13) wall quads are exactly one tile. | uvclass verifier | `uvclass/verify_mclass_tiles.py`, `verify_rockwall.py`, `verify_keyspike.py` |
| Rock art is shared map-wide (far-reuse p50 31 blocks); the kit's `_cell_rect` "baked-unique" flag measures lattice/slope geometry, not art. | UV-10 corrected | `uvclass/verify_baked_metric.py` |
| Main grass (L.rule) density is tight (28.1/31.4/36.9 px/u); it tolerates ±10% plan scale and pure Y up to the plan-law slope envelope (p99 35°). | UV-05 | `uvclass/uvc_deform.py` |
| Coastal lip and rock courses key one 128 px tile per column and pin v at base/top whatever the width or height. | UV-06 corrected | `uvclass/uvc_deform.py` |
| Painted shading has no facing dependence. | UV-08 | `uvclass/uvc_probe_light.py` |
| Forest canopy charts are tile-scale (≤ 2x2 tiles) of shared art but not affine at 8 px. | UV-09 corrected | `uvclass/uvc_reconcile.py` |

### 4.7 Disc 4

| law | cite | script |
|---|---|---|
| Disc 4 is a local re-cut of disc 1: 81.4% of terrain triangles kept all-channel exact, median 9.3% of a block touched, block-border welds kept (0 of 67 changed edges worse). | D4-01, D4-04, D4-06 corrected | `disc4/census.py`, `verify_kept_exact.py` |
| New disc-4 interior geometry is free-form: 11.7% of interior new corners on the 4 u lattice vs 35.4% in stock. | from D4-05 refutation | `disc4/verify_lattice.py` |
| Only 6 of 481 prefabs changed; edits live in the meshes. | D4-03 | `disc4/prefab_census.py` |
| Reorder-only cells are exact full-channel permutations; buffer order changes ground only on shared-edge ties (measure zero). | D4-18, G2 | `disc4/reorder_check.py`, `gap_disc4_edit_reach/s3_tieground.py` |
| The Mist is a fog toggle (`UseMist`: scenario < 5990 or > 11090), not geometry. | D4-15 | source read |
| Disc 4 promotes after-event Form-2 objects into the Form-1 slot at (20,10) and (14,17). | D4-13 | `disc4/crescent_probe.py` |
| Site edits: Shimmering Island sunk; Iifa footprint raised ~1.1 u with entrance area 489 → 1,662 samples; Cleyra closed (3 of 4 blocks lose all entrance tiles; (14,11) keeps 19/36); 53 bark-tile topo-49 ridges laid over walkable ground; 16 blocks lose every in-block entrance tile. | D4-08, D4-10-D4-14 | `disc4/anatomy.py`, `entrance_check.py` |
| Disc 4 re-zones area on 44 blocks (1,191 tris) of unchanged geometry, mostly 0 → 7. | G9 | `gap_disc4_edit_reach/s6_semantic.py`, `verify_area_pairing.py` |
| Dispatcher 9008 (disc-4 free roam) has no trigger for any of the 24 entrance cells disc 4 closed; 9009 (the `~` disc-switch target) still has 22. | G8 corrected | `gap_disc4_edit_reach/s6_semantic.py`, `verify_w08_cases.py` |

### 4.8 Stitch and composition

| law | cite | script |
|---|---|---|
| The stock overworld is one conforming mesh across all parts and blocks: every stitch is an exact shared vertex, 0 T-junctions. | S1 | `gap_inplace_stitch_composition/stitch_census.py`, `verify_tjunction_numpy.py` |
| 11.4% of Terrain positions are welded to a non-Terrain part (5,648 of 49,419 on disc 1). | S2 | `stitch_census.py` |
| Stock borders: 436 of 443 land pairs closed; 7 open pairs (17.24 u total, max 3.07 u). | S13 corrected | `border_closure.py` |
| THE BERM LAW's 664/702 is grass-sand (topo 31) corner incidences with foam-welded ends kept. | S14 | `calibrate.py` |
| `world-terrain`, `world-deploy`, `world-retarget` and `morph_in_place` read pristine stock, so the last writer wins (8/8 pairs). | S3 | `composition_probe.py` |
| On a real disc, `world-terrain` cannot touch a kit island: an ocean cell with a deployed Terrain override is skipped as sea. | S4 | `composition_probe.py` |
| The torn-weld gap of a Terrain-only edit is exactly abs(f) at each welded position. | S5 | `composition_probe.py` |
| A replayed reshape (a pure function of world XZ) keeps disc-4 border welds; disc 4 adds no border T-junctions. | G5 | `gap_disc4_edit_reach/s5c_border_welds.py` |
| A disc-1 → disc-4 byte delta must be tested on an XZ footprint: 26-63% of disc-4-only triangles are invisible to a vertex-keyed test. | G7 corrected | `gap_disc4_edit_reach/s2_footprint.py`, `verify_newpos_blind.py` |

---

## 5. Contradictions with recorded knowledge (action items)

The memory store is shared and not under version control: make surgical edits.

### 5.1 Memory store (`~/.claude/projects/C--gd-Dream-World-IX/memory/`)

| recorded claim | where | correct statement | evidence |
|---|---|---|---|
| "IDALL area COSMETIC" / "Tile `--area` stamps are pure bookkeeping" | `MEMORY.md` index line and body of `project-ff9-world-locate-cell-tag-join` | area has 7 consumer channels; it is only not the entrance-dispatch key | C4, GA1 |
| `Block[12][10]` has "no water meshes whatsoever", reclaimed cells "sealed" | `project-ff9-sea4-under-land-law.md:105` | 12,10 has Sea1/3/4/5 covering 97.3% of the cell | C7 |
| "the PLAIN inland donor (Block[12][10], no sea/beach sub-meshes)" | `project-ff9-overworld-terrain-authoring.md:63` | same | C7 |
| (11,19) listed as OPEN with the Terrain-registration hypothesis | `project-ff9-overworld-audit-roadmap.md` (the "OPEN (2026-07-20)" entry) | closed by GROUND-FAMILY-DECODE §4 ADDENDUM 3-6; mechanism is prefab selection | C6 |
| THE SEA-LAYER LAW: "every sea sub-layer sits at EXACTLY Y=0 map-wide" | `project-ff9-overworld-audit-roadmap.md:104` | open water at 0; shallow rims to +0.8; Form-2 sea4 to +1.527 | V9 |
| disc 4 "mostly byte-identical to disc1" | `project-ff9-overworld-worlds.md:23` | 85 of 275 blocks identical; 180 really edited | D4-01 |
| "river" differs at Daguerreo | `project-ff9-overworld-worlds.md:24` | river is identical; the reading came from the `read_block` prefix bug | D4-20 |
| (9,17) as the exceptional mirror skip | `project-ff9-overworld-worlds.md:23-31` | skipping is the majority case: 73% of land cells | D4-16 |
| `world-environment` needs a RELAUNCH | `project-ff9-overworld-worlds.md:95` | re-parsed on every world load; a relaunch only for a new folder in `FolderNames` | F6 |
| THE CANOPY STEP LAW: step-up ceiling 2.34375 | `project-ff9-overworld-interior-topography.md:94-103` | holds for lawn → canopy; from topo 36/37/38 the ceiling is 1.171875 | V3 |
| topo 49 reaches "h to 37u" | `project-ff9-overworld-interior-topography.md` | 37.1 is the centroid p98; the vertex maximum is 42.68 | V2 |
| canopy UVs are "28-35 multi-tri continuity patches ... hand-authored organic texture with NO tile language" | `project-ff9-overworld-interior-topography.md` FOREST CHAPTER (~78-82) | counts are a vertex-union artifact; edge patches are tile-scale charts of shared art (still not affine at 8 px) | UV-09 |
| THE BAKED-TERRAIN LAW: topo 17/38/49 highland = hand-painted murals, 92-100% UV-unique, no tile language | `project-ff9-overworld-coast-mosaic.md` LAW INDEX line 92 | the uniqueness metric fails its negative control; rock art is shared; ~29% of rock M.flow area is exact 128 px tiles; topo 17 is 95.7% L | UV-10, uvclass verifier |
| (12,0) Sea4 is "missing one 4u quad ... (at home something else covers it)"; the only full-cell deep Sea4 plane | `project-ff9-overworld-placement-rules.md` | the cover is `(12,0)` Sea6; the runtime full plane is `sea4f` | C9 |
| "there is NO slope/step gate ... a raised slope stays walkable at any grade" | `project-ff9-worldmap-feasibility.md:349-351` | a step gate exists (2.34375 u; 1.171875 u from canopy); continuous slopes walk to ~79.4° | S16 |
| "there is NO native world → world path" | `project-ff9-f6-overworld-debug.md:142` | **right**; the forms lane's proposed `WorldMap(same id)` refresh was wrong | forms A1 |
| THE BERM LAW 664/702 | `project-ff9-overworld-coast-mosaic.md:146` | **right**; add the unit definition (S14) | S14 |

### 5.2 Study documents

| recorded claim | where | correct statement | evidence |
|---|---|---|---|
| `mw_worldSetFormBit` "fires mid-session"; list-length parity unverified | `studies/path-d-new-world/walk-decode-claims.md:685`, `:70` | runs at world load; lists are unequal at (13,12), (14,12) | F3, F5 |
| slice_height is 0 on land classes (ML-8) | `studies/path-d-new-world/walk-decode-claims.md:87, :147, :189` | topo 36/37/38 sink 1.171875 immediately. (`WALK-QUERY-DECODE.md:137` is **right**: rate-limiting applies only to water.) | V3 |
| normals are render-inert | `studies/path-d-new-world/GROUND-JUNCTION-SYNTHESIS.md:206-211` | right except Falls and Stream | C2 |
| s34 overrides on (3,9) "can reach only Terrain/Object/Sea3/4/5"; "0_2 LOD" wording | `studies/overworld-topography/README.md:1235`, `:1222-1224` | they also reach Terrain2/Object2/Sea*_2; `0_2` is Form 2 | F13, F16 |
| (16,5) "Real cell → disc 1 only (no mirror)" | `studies/overworld-topography/README.md:768-769` | pre-dates `auto_mirror`; (16,5) is gate-eligible | G14 |
| (9,17) Object geometry differs across discs | `studies/overworld-topography/GROUND-FAMILY-DECODE-2026-07-19.md:741` | exact permutation; the FREE-RIDE PIN is redundant but harmless | D4-18 |
| "Area choice is cosmetically free"; the (19,18) event tiles are "the horseshoe carry's 270 stock event verts" | `studies/overworld-topography/southern-ring/REVERT.md` §26.2; commit `e192f17c` | area drives labels and camera place; the tiles are stock Cleyra's entrance set (translated +348, −404) | GA1, GA7 |
| THE SEA-LAYER LAW | `studies/overworld-topography/AUDIT-AND-ROADMAP-2026-07-18.md:332` | as in 5.1 | V9 |

### 5.3 Kit code, CLI help and engine patch comments

| recorded claim | where | correct statement | evidence |
|---|---|---|---|
| "`0_2` is a far LOD" | `ff9mapkit/ff9mapkit/world/extract.py:11`; `cli.py:8960` (`world-extract --lod` help) | Form-2 mesh set | F16 |
| area is "a coarse REGIONAL tag" / "the cosmetic regional tag" | `world/extract.py:68-89` (`decode_id`, `encode_id`) | 7 channels | GA1 |
| "a cosmetic `area=<case>` stamp"; retarget "only the trigger flag + cosmetic" | `world/entrance.py:18`; `world/mesh.py:1393-1398` | same | GA1, GA10 |
| `--area` "a COSMETIC regional tag"; `--no-tile-area` "the stamp is pure bookkeeping" | `cli.py:9025`; `cli.py:9886-9888` | same | GA10 |
| ~~vcount ≤ 65535 ("16-bit mesh indices only")~~ **withdrawn: the claim is right** | `world/mesh.py` `MAX_MESH_VERTS`; `WorldMeshOverride.cs:186` (s34); pin `test_world_ledger.py::test_engine_patch_literals_are_pinned` | ~~native cap 65000~~ 65535 is the binding ceiling, in-game proven (`ingame/RESULTS.md` §8) | CAP-1 (refuted) |
| `terrain.reshape` and `morph_in_place` "READ the deployed override and write it back" | `world/mesh.py:347-351` (`mod_overwrite_gate` docstring) | both read pristine stock on real discs; true only for reshape's Path-D `target_disc` branch | S3 |
| entrance reads the deployed override "exactly as for terrain.reshape" | `world/entrance.py:741-743` | reshape does not; entrance does | S4 |
| "shared block-edge verts move identically → seamless"; "so nothing tears" | `world/terrain.py:9-10`; `cli.py:4091-4093` | true for Terrain-Terrain only; every cross-part weld tears | S5 |
| VertexDisplace keeps "every instance ... in EVERY part" coincident | `world/transplant.py:817-834` | only within the parts the caller loads (`transplant.PARTS`) | S11 |
| "The verbatim donor blocks have ZERO such pairs" | `world/mesh.py:1557-1559` (`weld_audit`) | false for disc-4 (18,4) Terrain (3 stock near-miss pairs) | S17 |
| lip UV density is "CONSTANT, so U is arc-length-driven" | `world/terrain.py:236-241` (`_apply_cliff_rock_uvs`) | stock lip is column-keyed (density ∝ 1/width); the kit's arc rule is a separate, in-game-accepted dialect | UV-06 |
| highland rock is "hand-PAINTED murals" | `world/transplant.py:1941-1949` | shared art, hand-placed; much is keyed tiles | UV-10 |
| "65 overworld areas (0..64)" | `world/worldpack.py:53` (also `:43`, `:66`, `:191`) | 64 (0-63) | GA15 |
| first-match lookup is unambiguous | `world/extract.py:334` comment, `_mesh_index` note | substring match collides `sea4`/`sea4f` and `river`/`riverjoint` | D4-17 |
| per-cell skip is the safe behaviour | `world/discmirror.py:12-16` docstring | per-cell skip of a multi-cell write cracks disc 4 | G3 |
| `Block[12][10]` is "a Terrain child, no town Object, no beach/sea" | s34 comment `WMWorld.cs:1203-1209` (our patch stack) | it carries Sea1/3/4/5 | C7 |
| `placement.WALK_SPEED` 79.4° | `world/placement.py` docstring | lawn only; 69.5° from topo 36/37/38 | V3 |

### 5.4 Superseded inside this study

| claim | where | correct statement |
|---|---|---|
| "stock disc 1 has 17 real border gaps" | `disc4/NOTES.md:191` | 7 open pairs, 17.24 u (S13) |
| "11 covered T-junctions" | `disc4/VERIFY.md` D4-06 | 0 T-junctions (S1) |
| per-part ceiling 21,845 tris; stock max 736 | `operators/NOTES.md` F1 | 21,845 stands (CAP-1's 21,666 refuted in-game, `ingame/RESULTS.md` §8); stock max 772 on disc 4 |
| Disc4 IDALL differs in area 44 / topograph 51 / event 11 blocks | `operators/NOTES.md` F18 | index-aligned artifact; order-invariant area 44 (17 shared), topograph 11, event 7 (G13) |
| area 12 "forced upper camera" | `consumption/NOTES.md` §2 | inverted (GA3) |
| SEA-LAYER as a proven law | `operators/NOTES.md` §6 sea repair row | see V9 |

---

## 6. Latent defects found (evidence only; nothing was fixed)

| # | defect | where | evidence | exposure today |
|---|---|---|---|---|
| 1 | `extract.read_block` resolves parts by substring: disc-4 (12,0) `sea4` → Sea4f; disc-1 (19,11) and disc-4 (5,16) `river` → RiverJoint | `world/extract.py:332-336`; reaches `water.py:463/504`, `transplant.py:127`, `discmirror.py:323`, `palette.py:51` | D4-17; `disc4/verify_prefix_collision.py` | the pin path pins RiverJoint twice and never River for a `(19,11)` donor (G10); false mirror SKIP at (12,0). **FIXED** after this study: exact match, `tests/test_world_block_part_lookup.py`; the fix's census also found (16,15) `river` → RiverJoint on both discs, a block with no River; no deployed write read any of the five |
| 2 | ~~vertex bound 65535 admits 65001-65535, which Unity refuses natively~~ **NOT A DEFECT, refuted in-game** (65,001 and 65,535 verts render and walk); the 65000 kit change it prompted (`b68e1c6b`) was over-strict and is reverted | `mesh.py:121-123`, s34 `WorldMeshOverride.cs:186`, test pin `test_world_ledger.py:197` | CAP-1 | none: the kit is back to 65535 (`mesh.MAX_MESH_VERTS`, equal to s34's bound), and s34 needs no change |
| 3 | four in-place writers read pristine stock, so a second edit erases the first; a later reshape/retarget silently kills a `world-entrance` (event tiles erased, `.eb` trigger left) | `terrain.py:139-143`, `cli.py:4149`, `cli.py:4275`, `transplant.py:3305` | S3 (8/8) | any repeat edit of one real block |
| 4 | the ownership ledger allows kit-on-kit erasure; no overwrite gate on those four writers | `mesh.py:491` | S3, S10 | same |
| 5 | Terrain-only Y edits tear cross-part welds: one-way walls at ±3 u in 149-154 of 154 beach-centred edits; a random r16 edit tears a stitch ~45% of the time, r96 (the `world-deploy` default) 99% | `terrain.py:159` | S5, S6, S8 | every coastal or object-bearing real-block edit |
| 6 | no entrance guard in `terrain.reshape` or `morph_in_place` (only `world-deploy` has one, `cli.py:4154-4165`) | `terrain.py`, `transplant.py:3286` | S9 | entrance blocks |
| 7 | `terrain.reshape` is not edit-atomic: a later block's wall-gate refusal leaves earlier blocks written (25.4% of disc-1-refused reshapes; a 0.62 u disc-1 step shown) | `terrain.py:126-167` | gap_disc4 A1, `verify_writer_atomicity.py` | multi-block reshapes |
| 8 | `discmirror` gates per cell, so a multi-cell edit spanning eligible and refused cells cracks disc 4 (7.5% of synthetic edits; 4.0 u step shown) | `discmirror.py:202-232`, `:273-289` | G3, `s5b_crack_demo.py` | multi-cell real-land edits |
| 9 | the mirror gate compares ordered arrays, refusing 10 pure-permutation cells | `discmirror.py:83-87` | D4-16, G1 | over-conservative only |
| 10 | `mesh.weld_audit` is blind to any tear larger than its 0.05 u tolerance | `mesh.py` `weld_audit` | S10 (0.06 u tear → 0 pairs) | every gate built on it |
| 11 | `VertexDisplace` co-moves only `transplant.PARTS`; a 1 u Object tear passes every `morph_in_place` gate | `transplant.py:46`, `:817-834` | S11 | in-place morphs near Object/River/Beach2/Sea6 |
| 12 | `.bak` parks collide within one wall-clock second and lose the earlier bytes (5/5 trials) | `mesh.py:501`, `:284` | S12 | rapid successive writes |
| 13 | disc-4 (18,4) Terrain has 3 stock near-miss pairs, so a disc-4 carry of it fails transplant's 0-pair weld gate on unmodified bytes | `mesh.py:1557-1559` | S17 | disc-4 carries of (18,4) |
| 14 | `world-entrance` stamps area := case by default: of 151 stampable cases, 3 lock the camera, 9 set weather, 62 change camera place, 49 arm the beach search, 70 make topograph-0 trigger tiles encounter-live, 89 wrap (case ≥ 64) | `entrance.py:763`, `:1027`; mask `extract.py:90` | GA10 | every new entrance |
| 15 | live Disc1/Disc4 `Block[19][18]` Terrain carries stock Cleyra's 45 entrance tris with area 12: camera lock, spawn weather, zone-5 battles, "Vube Desert" labels; inert as an entrance | live `FF9CustomMap-world` | GA7, `verify_1918.py`; in-game RESULTS section 1 | none. **FIXED 2026-10-08** with 16-17 by the host-area stamp (southern-ring `REVERT.md` section 32): area -> the block's host 14, area bits only; in game 11/11 (`ingame/RESULTS.md` section 15) |
| 16 | five Southern Ring quay trigger clusters keep area 0 / topograph 0, so they can roll zone-0 battles inside the area-14 safe road: (0,18), (1,6), (6,19), (10,9) 48 u² each; (22,18) 58 u² | live overrides | GA6 | none. **FIXED 2026-10-08** (REVERT section 32): all six quay triggers, Grimhorn's too, now area 14; Confirm still enters the Lantern Hall in game |
| 17 | Sandreach Beach1 at (12,18)/(12,19) kept donor area 49 (a beach-search arm); the R4b restamp covered Terrain only | live overrides | GA6 | none. **FIXED 2026-10-08** (REVERT section 32): area 14; the title reads Lindblum Plateau in game |
| 18 | a sidecar-less `world-reclaim` cell free-rides `Block[12][10]`'s water under the new land | `terrain.reclaim` writes no `Donor.txt` | C7; in-game H1 (`ingame/RESULTS.md` §9) | no live cell uses this route (all 229 use `Donor.txt`). **FIXED** after round 2: reclaim writes a hidden stub for each of 12,10's Sea1/3/4/5 (`terrain.LAND_DONOR_WATER`, pinned to the install in `tests/test_world_reclaim.py`); the bind oracle shows 0 free-riders on discs 1/4 and Path D, and the round-2 boat simulator predicts a cell-edge stall for every profile. **In-game PROVEN** (`ingame/RESULTS.md` §14): flat6 and cliff, 6/6 each, the boat stops at the cell edge. Side effect: a raised `flat` slab shows open sky under its edge |
| 19 | Form-1-only trap: kit Terrain/Object edits on the 26 switchable cells vanish when the place flips | override key `WMWorld.cs:823-825` | F14, CAP-3 | 0 live on disc 1/4; Path D (14,12) only in CLONE mode |
| 20 | `world-environment` never emits `Clear`, so conditions OR across mod folders; Memoria's shipped doc says `Clean`, which the parser ignores; the kit validates 65 place names, only 9 have forms | `world/environment.py:126-129` | F7 | any stacked `Environment.txt` |
| 21 | ~~the Path D cell Disc9 (13,15) uses donor (0,0) without an Object blank, so (0,0)'s stock Object (5 tris, topo 59) free-rides~~ **NOT A DEFECT (checked 2026-10-08):** (13,15) carries (0,0)'s OWN Terrain verbatim (1218/1218 verts, unmoved), which has a hole at the cell centre, and the free-riding Object is exactly its plug (607/607 hole samples covered, 0 over ground). It sits at its natural pose: THE OBJECT POSE LAW. The other donor-(0,0) cells blank it because they carry other terrain. Blanking it here would open a ~10 u² hole | live Disc9 files | consumption verifier finding 3 | none |
| 22 | stock engine: the Light Blue / Red Chocobo deep-water remap compares the full IDALL to 56/57, so it never fires | `ff9.cs:3310` (stock) | C3 corrected | stock behaviour; makes flag bit 0 load-bearing at those two values |
| 23 | `world-terrain`'s one-way-wall gate refuses mostly pre-existing slopes: the worst edge was already over the ceiling in 98.9% of refusals; a gate refusing only steepened edges would pass 62.6% | `terrain.py:34-85` | G12 corrected | `world-terrain` usability |

**Instrument caveats for anyone reusing these scripts:** `forms/diff_forms.py` omits the 4078/4088/2040 skips and
the 0x31EE veto; `capacity/predict_reads.py` and `live_budget.py` treat "prefab has Terrain" as land, which is wrong
for 15 `IsSea=false` water-only cells; `disc4/weld_gap.py` silently skips uncovered stretches; `disc4/uv_coverage.py`
prints only topographs with ≥ 50 new tris; `disc4/prefab_census.py` normalises the disc segment and hides cross-disc
refs; uvclass's per-patch κ misfiles keyed tiles with partial fringes as M; uvclass tile counts use a phase-0 grid;
`vertical/engine_bounds.py`'s stock tagger cannot fail as written; `vertical` camera numbers model the internal eye
(add the FixTypeCam offset); `capacity/scan_cost.py`'s from-sky depth is a lower bound;
`gap_inplace_stitch_composition/tear_sweep.py` probes vertical tris on their base line; `consumption/consumer_map.py`
misses indirect readers through `w_frameGetParameter(192/207)` and literals under 3 digits; `area_lint.py` keys
encounters at fog 0 (the Southern Ring runs at fog 1) and checks tags against the union of all dispatchers;
`s7_morph_replay.py` has a 600 s wall-clock cut-off.

---

## 7. Ranked next experiments

**In-game results → [`ingame/RESULTS.md`](ingame/RESULTS.md)** (harness sessions 1-7 plus round 2; every deploy went only to a scratch mod folder, since removed). **Confirmed:** ranks 1 (incl. the Disc9 walk, RESULTS §12), 2 (stock and the data-driven Environment.txt + Terrain2 switch: story terrain with no DLL), 3, 4 (crack + replay), 5 (canopy sink to 0.0015u, the −5.76 basin, and the airship ceiling 0.45u inside the 42.64 summit), 6 (the Terrain PNG clobber; Sea4 PNGs render), 7 (H1: a boat sails under a sidecar-less reclaim -- defect 18, since FIXED), 11 (R1/R2 only), and the rank-12 no-fly ring. **Refuted:** CAP-1 (65,535-vertex parts work). **Corrected:** the "descent stall" at a +3 beach tear was a harness artifact; the tear is a one-way wall (RESULTS §6). **Partial:** rank 10 (the pre-registered rule was inconclusive; the post-hoc brackets put the budget near 5k tris per walkable part); rank 11's "walkable alongside" (R3) proved nothing, and the ridge look awaits the owner. **Not run:** rank 9 (needs the owner's eye), rank 12's Falls normal A/B and tangent-stamp round trip, the boat "none" phase.

Cost classes: **no-DLL, no deploy** / **no-DLL, deploy** (mod files only) / **patch** (a new `memoria-patches` entry) /
**rebake** (none is ever needed: forms F17). Harness: memory `project-ff9-test-harness`; capture: `tools/game_snap.ps1`.

### 7.1 In-game

| rank | experiment | registered prediction | cost | why here |
|---|---|---|---|---|
| 1 | **Area session** (one harness run). (a) Disc1 save, scenario < 4990: teleport to (1244, −1181) on the `(19,18)` Cleyra tiles (area 12, topo 41); press the perspective toggle; read window title, main-menu label and a sandboxed save slot's Location; step to (1210, −1181) (area 14) and repeat. (b) Disc9: walk the Uaho carry (13,15), area 63, until 3 random battles. (c) Archive `Memoria.log` and replay `bind_oracle.py` for Disc9 receipts. | (a) toggle refused, camera stays default; all three labels read "Vube Desert"; on area 14 the toggle works and labels read "Lindblum Plateau". (b) every battle scene comes from zone 24's slice (`worldpack.zone_slice(24)`). (c) Disc9 loaded lines equal the BLANK-mode bind prediction. | no-DLL, no deploy | zero cost; validates live defects 15-17, the inverted area-12 record, the save-slot label channel, and gives the bind oracle its first non-disc-1 receipts. Decides whether to build the area policy and lint. |
| 2 | **Form switch, rung F0 then F1.** F0: `Environment.txt` `Place WaterShrine [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]` (flag 8712). F1: `Block[22][14] Terrain2.ff9mesh` (stock (22,14) with a flattened plateau, radius ≤ 24 u about (1440, −928)) + `Place BlackMageVillage [Condition=WorldDisc == 1 && <flag>]`. Refresh by a `Field()` round trip, a battle, or the `~` menu's world reload, **not** `WorldMap(same id)`. Do not step on the Water Shrine entrance tiles. | F0: flag off → `Dump block` (3,9) `Form=1`; flag on → `Form=2`, Terrain2 157 tris, Object2 124, terrain y min −5.07, entrance IDALL at x 215-233, z −617..−599. F1: log `[WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2'` in both flag states; `world_y` = plateau height ±0.15 with the flag on, stock slope (~22.69 at the centre) with it off. | no-DLL, deploy (text + 1 mesh) | the largest new capability (story-driven terrain) with no engine work; F1 also settles the Terrain2 key hypothesis and the Form-1-only trap. |
| 3 | **Beach seam tear.** `world-terrain --at 480 -1120 --radius 16 --raise 3` on (7,17) into a scratch folder stacked on top; `~` → World → Reload overworld; snap; harness walk from foam (476.28, −1120.28) north-west onto terrain and back. Control: `--raise 1`. | +3: a ~2.5-3 u slit along the Terrain/Beach1 and shallow-rim seams; all 24 beach → terrain crossings refused, terrain → beach legal. +1: slit visible, 0 walls. | no-DLL, deploy | in-game proof behind kit changes 1-5 of the stitch lane (stacking reads, overwrite gate, entrance guard, stitch gate, co-displacement) on the most-used verb. |
| 4 | **Disc-4 crack, then replay** (bench folder). `world-terrain --at 256 -872 --radius 16 --raise 4`; log must show `SKIP (4,13) ['sea1']` and mirror (3,13); `~` → World → disc 4 (loads 9009; fine for geometry); readouts at (254, −872) and (258, −872). Then `world-terrain ... --disc 4` and repeat. | first: a ~3.8 u wall along x = 256 for z ≈ −856..−888. After replay: smooth +4 u hill; readouts agree to < 1e-3. | no-DLL, deploy (2) | proves defect 8 and that replay heals it; gates the discmirror redesign (atomic writer + mirror + replay hook). |
| 5 | **Zero-edit vertical session.** Canopy: stand on forest (15,15) and on nearby lawn, read y vs offline ground. Basin: walk to (223.75, −464.25) and out. Flight: Hilda Garde over (1225.5, −926.5) at full altitude. | forest y = ground − 1.171875, lawn y = ground; basin y = −5.774 with no water; airship y holds 42.1875 over the 42.67 summit. | no-DLL, no deploy (needs a Hilda Garde save) | settles the canopy ceiling the walk gate and `WALK_SPEED` should use (V3 is source-confirmed but not distinguishable offline). |
| 6 | **Per-cell PNG overwrite check.** On a cell with Terrain and Sea4 overrides, add a vivid `Block[x][y] Terrain.png` and the same as `Sea4.png`; relaunch; snap. | Terrain shows no change (Moguri atlas); Sea4 shows the PNG, static. | no-DLL, deploy + relaunch | closes the per-block texture lever; only if it confirms and per-block textures are wanted does a patch follow. |
| 7 | **(12,10) free-ride and boat drive.** `world-reclaim` flat height 6, no `Donor.txt`, on a scratch ocean cell; `~` World Dump the block and parse with `world/readback.py`; then the harness boat drive into the cell (flat 6, then cliff 3.2; island profile as control). | dump lists Terrain + Sea1/3/4/5 of stock 12,10; outcome of the boat drive is the open hypothesis H1. | no-DLL, deploy + relaunch | decides whether `terrain.reclaim` must write a `Donor.txt` or blank the water parts. |
| 8 | **Vertex-cap window.** Two reclaimed scratch cells: Terrain at 64,998 verts and at 65,001 verts; sky-probe each centre; read `Player.log`. | 64,998 renders and walks; 65,001 logs "Mesh.vertices is too large" and has no ground. | no-DLL, deploy | the 65000 fix is warranted from the binary string alone; this only fixes the failure mode for the error message. **Run (session 7): refuted.** 65,001 and 65,535 verts render and walk (`ingame/RESULTS.md` §8). The binary string is not the binding gate. |
| 9 | **Rock stretch tolerance (X1).** On the Uaho bench, pure-Y scale the carried rock x1.25, x1.5, x2.0 about its rim; stills; owner judges. | x1.25 reads like the rigid carry; x1.5 borderline; x2.0 visibly stretched. | no-DLL, deploy (3) | required before relaxing `MTN_ROCK_RIGID`; the offline envelope is an uncalibrated proxy and blend-conform once smeared rock in-game. |
| 10 | **In-game cost budget.** Ground-query curve: one bench cell at refinement x1/x4/x16, 600-tick walks alone and with 3 parked actors, `tickrate.py`. World-entry parse time at 1x/2x/4x override volume. | no measurable change at x4; first cost, if any, at x16, dominated by parked-actor full scans; load time roughly linear in deployed vertices (~1 s now). | no-DLL, deploy | supplies the missing frame budget (CAP-12) before any dense-terrain feature. |
| 11 | **Disc-4 ridge look.** `~` disc 4, teleport to (1144, −395) or (846, −278), snap, walk across. | a bark/root ribbon 1-3 u tall; crest blocked; walkable alongside. Owner names it. | no-DLL, no deploy | resolves D4-09 (the replay hazard H1 depends on what the ridges are). |
| 12 | **Low priority.** Falls normal A/B at (19,11) (brightness changes only if world light colours are nonzero); tangent provenance stamp round trip (walk/render identical, stamp visible in the dump); no-fly topo-15 patch (airship stops at every altitude). | as stated | no-DLL, deploy | each settles one narrow open item. |

### 7.2 Offline and patch work

| rank | work | registered prediction | cost | why here |
|---|---|---|---|---|
| O1 | Prototype `mesh.stitch_gate(pre, post)` from the stitch census (block + 4 neighbours); run it over the 5,292-edit tear sweep and over accepted transplant carries (dry runs into scratch). | fires on 100% of sweep edits and on 0 accepted carries; any carry that fires names a partner outside `PARTS`. | offline, ~1 h | the replacement for the blind `weld_audit`; needed by stitch-lane changes 4-6. |
| O2 | discmirror redesign bench: atomic writer **and** atomic mirror, order-invariant per-part gate, replay hook, hazard check; replay the s5 population into scratch trees. | crack rate 7.5-12.5% → 0; reach = replay-clean plus warned hazards. | offline, ~half a day | includes defect 7 (writer atomicity), which the lane's original design missed. |
| O3 | Disc-4 dispatcher arrival census: decode the shared exit cascade of the 79 world-exit fields for scenario ≥ 11090; list region keys that fall to 9009. | most disc-4 exits land on 9008; a minority on 9009. | offline, ~2 h | bounds how live the 9009 re-arm trap (G8) is in normal play. |
| O4 | Promote `area_lint.py`: per-namespace fog key, per-dispatcher tag sets, a stock-entrance negative control, AL2 after topograph-only writers. | same live counts at fog 1; AL2 still 0. | offline | prerequisite for the area policy R1-R10. |
| O5 | Switchable-cell lint dry run over the live `FF9CustomMap-world` listing; must fire on a synthetic edit at (20,10). | 0 disc-1/4 hits; 1 Path D hit at (14,12). | offline, ~1 h | cheap guard for defect 19. |
| O6 | Interior T-junction census of disc-4 re-cut seams. | re-cut boundaries add interior T-junctions with small gaps (< 0.3 u for amount 4, r ≥ 16). | offline, ~1 h | completes the replay safety case (G5 covered borders only). |
| P1 | Tier-2 form patch spike (F15): set `IsSwitchable` at runtime for cells with a loose `Terrain2.ff9mesh`, register a renamed TerrainForm1 copy as form 2, add a per-cell NCalc sidecar. | arbitrary cells switch with their own condition; no rebake. | patch | only after rung F1 proves the Terrain2 key. |
| P2 | Lift the per-cell texture clobber (skip `SetupPreloadedMaterials` for override-textured renderers). | per-block Terrain textures render. | patch | only if in-game rank 6 confirms the clobber and per-block texture is wanted. |

---

## 8. Open / unproven

### 8.1 Hypotheses and unverifiable items

| id | item | state |
|---|---|---|
| H1 | The Blue Narciss can sail under a sidecar-less reclaimed cell (flat above ~2.3 u; cliff case depends on the slide search) | premises verified; needs the boat drive (rank 7) |
| F13 | A `Block[x][y] Terrain2.ff9mesh` / `Object2.ff9mesh` binds and switches with the form | source gives no way to break it; never loaded in-game (rank 2) |
| F15 | The ~50-line Tier-2 patch sketch | sound as a sketch; unbuilt |
| V3 | Canopy sink in-game | source chain exact; stock data cannot distinguish (rank 5) |
| V8 | GlobalFog (the 29 u plane) is enabled at runtime | code checks `globalFog.enabled`; unread |
| V11 | The 37.1 camera ride clamp was tuned to the topo-49 p98 | coincidence depends on the percentile; unverifiable |
| V12 | Side effects of authoring a flight-blocked topograph (encounters, footsteps) | unused in stock; untested |
| D4-09 | The disc-4 bark ridges are the Iifa roots | owner or in-game look (rank 11); the tile also textures disc-1 place footprints |
| CAP-13 | Memory model (~48 B/vertex managed walk copies resident; ~1.66 GB at the cap everywhere) | arithmetic checked; not measured |
| C10/CAP-9 | Per-cell Terrain PNG overwritten in-game | source order proven; no receipt (rank 6) |
| — | Falls/Stream normals change pixels | depends on the world light colours being nonzero |
| — | Bind oracle predictions for Disc4 and Disc9 | calibrated on disc 1 only; Disc9 assumes BLANK mode |
| — | A mid-visit `RunWorldCode(501)` flip on (7,1), (8,1), (13,12), (14,12) throws (cached walk index out of range) | reachable only from the Bee debug scene |
| — | The 7 orphan `0_2` water variants that differ from `0_1` (e.g. (19,11) river 69 vs 66 tris, 42 shared) are PSX Form-2 water the port dropped | unknown |
| — | Which run carried stock Cleyra's tiles onto (19,18) | the Cleyra-region junction/dunes carry is the likely source; unproven |
| — | Whether `w_frameDisc` is 1 on the Path D namespace (which encounter table) | cannot flip a hole/record verdict (tables equal); open |
| — | Whether the Southern Ring quay tiles roll a battle before the WorldEvent dispatch on the same step | open |
| — | Seam slits at gameplay camera distance; stock open border edges and disc-4 (18,4) near-misses as visible pinholes | open (rank 3 control) |
| — | Render effect of buffer order (z-fighting) on permuted cells | ground cost is measure zero; render unmeasured |
| — | `world-deploy`'s refusal rationale (actor embeds at stale Y) vs sky-cast spawn | needs one harness field exit onto a raised entrance tile |

### 8.2 Support-lane claims not adversarially verified (operators lane)

Treat as leads, not facts: F7 (beach2, sea6, stream, volcano parts, sea4f have no kit writer); F8 (seam handling
differs per operator; only `world-island` wraps the x seam); F9 (`world-island --ground` mints only grass, desert,
snow; `cli.py:9608-9612` help is stale); F10 (11 verbs take `--target-disc`; `world-water`, `world-entrance`,
`world-mesh-build`, `world-retarget`, `world-deploy` cannot target Path D); F11 (no remove-land operator; `--excise`
yields an empty plan on 0 of 260 real cells); F12 (no in-place retexture of real land; no polygon-granularity IDALL
from the CLI); F13 (`world-hill`/`world-forest` refuse non-grass ground); F15 (matrix column totals); F16 (66
write-capable study scripts, 50 unreferenced by the kit; curated list of study-only operators with proven laws);
F17 (closed lanes, sourced from CLAUDE.md §8 and the coast-mosaic LAW INDEX).

### 8.3 Refuted during verification (do not re-propose)

| claim | why it fails |
|---|---|
| New disc-4 vertices follow the stock vertex lattice (D4-05) | the pool mixed in re-heighted and cut-boundary corners; interior new corners are 11.7% on the 4 u lattice vs 35.4% stock |
| Disc 4 painted no new terrain art; every new topograph is 0% virgin except 59 (D4-07) | a print filter hid topographs 30, 48, 53-57, which are 100% virgin; 10,372-19,265 texels are used only by disc-4 terrain |
| The (14,13) rock wall is a continuous band sweep, not a tile language (UV-11) | counted on a phase-0 grid; at the true phase (u 8 / v 64 px) 73.5% of quads are exactly one 128 px tile; the recorded "one tile per wall quad" stands |
| Only 10 highland blocks wear keyed rock (UV-12) | the W/M split misfiles keyed tiles; 50 of 144 blocks are ≥ 50% exact-tile rock |
| The s34 per-cell PNG can re-bake deformed Terrain (UV-15) | `SetupPreloadedMaterials` overwrites it on any install with a loose atlas, including this one |
| An "origin-shift wall class" at small raises near Objects, e.g. Treno's gate (S7) | every instance is a zero-width line on the base of a vertical Object tri; no walkable area changes. Probe P2 withdrawn. |
| `WorldMap(<same id>)` from the world `.eb` refreshes forms mid-visit (forms F4 sub-claim) | WMAPJUMP returns 5 in the world and the world tick handles only 3 and 4; no stock dispatcher uses 0xB6 |
| Streamed-out blocks rebuild on re-entry; a 2-8 block streaming horizon (forms F2, vertical V7) | streaming is dead: all 480 blocks load once and are never discarded |
| Far plane ~1173 u from `ClipDistance` (CAP-4) | that projection path is editor-only; runtime far plane is 1000 u |
| Unity 5.2.3p2 refuses a Mesh over 65000 vertices, so 21,666 tris per part (CAP-1) | refuted IN-GAME: 65,001 and 65,535-vertex parts render and walk; the ceiling is s34's 65535 (`ingame/RESULTS.md` §8) |
| Airship landing uses a "probe ring" (V13) | 8 collinear probes per heading, only the last height compared |
| Area 12 "forces the upper camera" | it forces the default view and refuses the high toggle (GA3) |
| `extract.read_block`'s only collision is `sea4f` (disc4 P4 prediction) | `river`/`riverjoint` also collides, on disc 1 at (19,11) |
| Deep sea4/5/6 stay at y = 0 (vertical V9 restatement) | Form-2 (3,9) sea4 reaches +1.527, sea5 +0.391 |
| `world-terrain`'s wall gate refuses ~99% pre-existing slopes, so nearly all would unlock (G12 headline) | on the real population a steepened-only gate passes 62.6% |
| A camera-place change widens FOV by ~3.75° at y ≈ 4 (gap_area experiment 2) | ~2.1° at FOV 44, ~2.7° on this install (FieldOfView 58) |
