# Verification of the "consumption" lane

An adversarial pass over `NOTES.md` and findings C1-C12 and H1. Everything was read-only: the install, the Memoria
clone at `C:\gd\FFIX\Memoria\Assembly-CSharp` (HEAD `6b8bb2d5` plus the working-tree patch stack), the memory store
and all tracked files. Nothing was deployed or built.

## Reproduction

All eight lane scripts were re-run on 2026-10-07 in the order NOTES.md gives. The bind oracle was fed the same
`Memoria.20261006-2355.log`, which is byte-identical to the install's current `Memoria.log`.

* Seven outputs are byte-identical to the lane's originals: `consumption_census`, `consumer_map`, `bind_oracle`,
  `landdonor_water`, `sea4f_vs_sea4`, `sea_event_quad` and `provenance`.
* `matrix.json` is semantically identical. Only its dict ordering differs.
* Every self-calibration passed, including the bind oracle's 81/81 receipts and the (11,19) replay.

New scripts, all read-only and all writing to `out/verify_*.json`:

| script | what it checks |
|---|---|
| `verify_sea_event_all_worlds.py` | The C9 event-1 sea quad against the object-0 cell tags of **all 13** world dispatchers (`evt_world_world00..12`), for both discs' 205 IsSea cells. Calibration: WORLD00 must reproduce the lane's 53 tags. |
| `verify_dead_files.py` | Opens all 939 "dead" `.ff9mesh` files and decodes their shape. It also re-derives bound vs dead with a second implementation of the effective-prefab rule, built from the census child names. |
| `verify_tangent_natural_experiment.py` | Splits the live files that have nonzero tangent.y/z/w into dead, bound, and bound with an engine log receipt. |
| `verify_fullvalue_scan.py` | A wider scan for full-IDALL equality tests than `consumer_map.py`. It accepts any literal and any IDALL-carrying left side, and counts a value written in two bases once. |

## Verdicts

| id | verdict | note |
|---|---|---|
| C1 | **confirmed** | Every aggregate reproduces: 2178/2178 meshes have mask 139 {pos, nrm, uv0, tan}, 1 submesh, 16-bit indices, flat layout, a permutation index buffer (identity in 33), tangent.yzw = 0, corner-uniform tangent.x, and stored AABB equal to the recomputed one. Max vcount is 2316 and the max terrain part is 772 tris at d4 (18,13). **Slip in the evidence:** "largest per block 826 at d1 (16,11)" is only the disc-1 maximum. Over both discs the maximum is **852 at d4 (16,11)**, followed by 850 at d4 (14,17). |
| C2 | **confirmed** | Every block child's material (Terrain, Sea1-6, Beach, River, RiverJoint, Volcano*, Object) uses `WorldMap/Terrain`, which binds vertex and texcoord. Falls and Stream use `WorldMap/ScrollTexture`. The install copy `ScrollTexture.txt` binds `normal` and does `dp3 v2, c7..c9` against `unity_LightPosition0-2`. The `*_mat` materials with their own WorldMap/Sea, Beach, River and Volcano shaders exist, but no block child uses them: they feed WMRenderTextureBank's RenderTexture draws, and they also bind vertex and texcoord only. `WMMesh.Normals` reads are at WMWorld.cs:1002 and :1060, inside the uncalled methods at :982 and :1040. The PATCH debug dump also reads normals (`Ff9mkDebugMenu.cs:1418/1436`); that has no gameplay effect. |
| C3 | **corrected** | (1) **"Nine special values" is really 8 distinct values.** `0xFEE` **is** 4078, the same value playing two roles: the walk-scan skip and the parked-actor hold. The tri counts were computed correctly on 8 values (2418 = 318+56+416+588+556+484). (2) **One STOCK full-value test was missed.** `ff9.cs:3310` (`w_cellHit`) contains `if ((control == 3 \|\| control == 2) && (id == 56 \|\| id == 57)) id = 54;`. `consumer_map.py`'s regex cannot see it because it needs a 3-5 digit literal. The true set is **10 distinct values**: {0xFEE, 0xFF8, 0x7F8, 0x31EE, 0x18EE, 0x7EE, 0x1BEE, 0x2CEE, 0x38, 0x39}. Value 57 has flags = 1. It occurs on 0 stock tris. The law that flag bits are read only through full-value equality still holds. |
| C4 | **confirmed** | Every cite is exact and STOCK, and every consumer is live: `w_weatherUpdate`, `w_cameraUpdate`, `w_cameraChangeTrigger` (R2) and `w_frameUpdateEvent`. Two nuances. (a) The weather case runs only when `w_frameCounterReady == 10`, so it reads the area under the player **once per world entry**, not continuously. (b) Area also reaches the main-menu location label (`MainMenuUI.cs:527`, through sysvar 192) and `UIManager.cs:587`. The memory "IDALL area COSMETIC" / "pure bookkeeping" and the `extract.py` "cosmetic regional tag" are **refuted**. |
| C5 | **corrected** | The child-name keying (WMWorld.cs:823-825) and the free-rider behaviour are confirmed. `verify_dead_files.py` agrees with the oracle's bound/dead split on all 939 dead files. Corrections: (1) 937 dead files are 1-tri blanks at y=-80 with area 0.005. The **2 Terrain divert stubs are at y=-100 with zero area.** (2) "Every failure to bind is silent" holds only for files with no matching child. A bound but malformed file **does** log `Log.Error` (WorldMeshOverride.cs:52; Donor.txt :121/:130). (3) **188** live cells use donor (0,0), not 187. In 187 of them Object2/Terrain2 both free-ride. The odd one is Disc9 (13,15), which also leaves (0,0)'s stock `Object` riding along. (4) All 254 receipts are **Disc1**, so the 81/81 match says nothing about the Disc4 mirror or the Disc9 predictions. Disc9 also assumes s75 BLANK mode (`CloneStockWorld` defaults to false and is session-only). |
| C6 | **confirmed** | Sea1-6 registration (WMWorld.cs:778-807, STOCK) is unconditional on Terrain. 15 water-only non-IsSea blocks exist per disc, including (8,18). The divert is armed only by `File.Exists` of Terrain.ff9mesh (WorldMeshOverride.cs:80-83). `Block[12][0]f` has the single child Sea4, which uses the sea4f mesh. Live log lines 253-255 show Sea3, Sea4 and Sea5 with no Terrain line. The live files are a 176 B Terrain stub plus Donor.txt "8,18". The roadmap memory's "OPEN (11,19)" entry is stale: GROUND-FAMILY-DECODE §4 ADDENDUM 3 (root cause) and ADDENDUM 6 ("THE (11,19) ARC IS CLOSED") already settled it. |
| C7 | **confirmed** | The census gives the 12,10 prefab slots {TerrainForm1, Sea1, Sea3, Sea4, Sea5} on both discs. The raster reproduces 97.30% coverage, 93.27% boat-legal, and a hole equal to the islet. The boat mask `0x2600000` decodes to topographs {53, 54, 57} (`ff9.cs:1658`, :5924-5939). `terrain.reclaim` writes **only** the Terrain override and no Donor.txt (`world/terrain.py`). The memory claims ("no water meshes whatsoever", "no sea/beach sub-meshes") and the s34 comment at :1207-1209 are **refuted** by the data. No live cell currently uses this route: all 229 route through Donor.txt. |
| H1 | **unverifiable** | The premises check out. Terrain registers before the Sea parts. A ray rejects surfaces above its origin (WMPhysics `num3 < 0`), and `rayDistance` is never passed to the raycast. The boat mask is {53, 54, 57}. The boat's full-stick step is 240·128/4/32/256 = **0.9375 u**. That comes from `w_movementShipOperation`'s alpha filter (:6235-6237), not from scaling the foot formula; the result is the same number by a different path. **The cliff case is weaker than stated.** A step wider than the band is necessary but not sufficient: a head-on step lands inside the ~0.73 u band about 78% of the time and is rejected. Getting through then depends on the ±11.25°…±78.75° slide search letting the boat creep up to the edge. The boat drive is needed. |
| C8 | **confirmed** | Children Terrain2 (52), Object2 (51), VolcanoLava2 (2) and Sea*_2 (6) reference 0_2 meshes. The other 76 0_2 meshes are referenced by no prefab, broken down as sea4 24, sea3 12, sea5 10, river 10, beach1 6, riverjoint 4, stream 4, falls 2, sea1 2, sea2 2. The only `0_2` string in the engine is in the editor-only `WMWorldPrefabMaker` (no runtime callers), and it sets `isSwitchable` when a 0_2 Terrain exists. 26 cells are switchable, and they agree 480/480 with the proxy on both discs. The "far LOD" comments at `extract.py:11` and `cli.py:8960` are **refuted**. |
| C9 | **confirmed** | sea4f is the 510 tris of sea4 plus 2 extra tris that carry Sea6's positions, winding and IDALL 16612 (event 1, area 0, topo 57), **re-UV'd into Sea4's atlas** with different UVs. **Strengthened:** `verify_sea_event_all_worlds.py` found **0 collisions in all 13 world dispatchers** across both discs. Those dispatchers hold 0-98 cell tags each; WORLD00 has 53. The 3/4 Sea6 tiles on scripted triggers reproduce. Event≠0 also has UI-side consumers outside script dispatch: `DialogManager.cs:366/387` and `EIcon.cs:131` / `EventInput.cs:206` through `IsWorldTrigger`. |
| C10 | **corrected** | The semantics are confirmed. `SearchAssetOnDisc` resolves names under `WorldMap/` through the WorldMaps ("data3") bundle branch to `MoguriMain/StreamingAssets/Assets/Resources/WorldMap/...`, where the terrain, objects, 11_0_192 and 11_64_192 PNGs exist. The volcano PNGs are absent, so the volcano parts are not in the DB on this install. Line fixes: LoadMaterialsFromDisc is **WMBlock.cs:273-306** and the name table is **:310-326**. This is still not receipt-proven; the lane's own PNG A/B experiment would settle it. |
| C11 | **corrected** | The law (no reads of tangent.yzw, corner-0-only tangent.x, inert normals except on Falls and Stream) is confirmed by code. **The natural experiment is inflated.** There are 1352 distinct files with nonzero tangent.y/z/w; "1385" counts 33 files twice. **939 of them are dead 1-tri blanks** the engine never opens. Only **413 are bound**, and only **163 have an engine log receipt** (158 with w≠0, 16 with y≠0). No live file varies tangent.x on corners 1 or 2, so that "free" byte rests on code alone. |
| C12 | **confirmed** | Every cite is exact. Unity's default `Cull Back` applies, because no world shader sets Cull, so winding matters for render too. The loader limits and RecalculateBounds are at WorldMeshOverride.cs:186-188 and :232. The contract audit is 747/747 clean. |

## Additional findings

1. **A latent STOCK bug: the chocobo deep-water remap is dead.** `ff9.cs:3310` compares the **full** IDALL to 56 and
   57 to remap them to 54 for Light Blue and Red Chocobo (controls 2 and 3). The intent was almost certainly
   topographs 56/57. No stock tri carries IDALL 56 or 57: real topograph 56/57 tiles carry full values ≥ 224. So the
   remap never fires. A tile stamped with full value 56 or 57 (topograph 14, area 0) would trigger it, and that
   makes flags bit 0 load-bearing at that one value.
2. **The bind oracle's receipt calibration covers disc 1 only.** All 254 receipts are Disc1. The Disc4 and Disc9
   predictions, including the BLANK-mode `is_sea=True` assumption for Disc9, are uncalibrated. In s75 CLONE mode, 23
   of the 65 Disc9 cells would route to their own stock prefabs instead of their Donor.txt.
3. **One Path-D cell carries an un-blanked stock object.** Disc9 (13,15) uses donor (0,0) without an Object blank, so
   (0,0)'s stock `Object` (5 tris, all topograph 59) free-rides as render and walkmesh. Every other donor-(0,0) cell
   blanks it. This is an oracle prediction in BLANK mode with no receipt.
4. **The weather consumer of area bits is one-shot per world entry.** It runs only when `w_frameCounterReady == 10`,
   so for weather what matters is the area under the spawn point. Encounters, sysvars, the camera and the title
   still read area continuously.

## Memory and recorded laws: who is right

* `project-ff9-sea4-under-land-law.md:105` and `project-ff9-overworld-terrain-authoring.md:63`, which say 12,10 has
  "no water", are **wrong**. The lane is right: the prefab census and the raster show it.
* `project-ff9-world-locate-cell-tag-join.md`, which says area is "cosmetic" and "pure bookkeeping", is **wrong** as a
  general statement. It is right only that area is not the entrance-dispatch key.
* `project-ff9-overworld-audit-roadmap.md`, "OPEN (11,19)", is **stale**. The study closed it, and the lane re-derives
  the same mechanism.
* `project-ff9-overworld-placement-rules.md`, "the only full-cell deep plane", is **imprecise**. The runtime plane is
  sea4f, the "something else" that covers the hole is Sea6, and the kit's cloned fill differs from sea4f in exactly
  those 2 tris.
* GROUND-JUNCTION-SYNTHESIS, "ground normals are render-inert", is **right for every part except Falls and Stream**.
