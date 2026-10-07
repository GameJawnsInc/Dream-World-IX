# Lane "consumption" — what the engine actually consumes from overworld block-mesh data

Study lane of `studies/terrain-malleability/`. Read-only on the install, the Memoria clone, the memory store and
every tracked file. Every number below comes from a script in this directory. Each script checks its own
calibration and exits non-zero if the check fails. Engine cites are `file:line` under
`C:\gd\FFIX\Memoria\Assembly-CSharp`, at the CURRENT patched tree. STOCK means upstream `6b8bb2d5` as pinned in
`memoria-patches/BASE_COMMIT`. PATCH means the line was added by our stack. `provenance.py` decides which, from
`git --no-optional-locks diff -U0 HEAD` (calibrated on 4 known lines).

## Instruments (rerun in this order, from the repo root)

| script | what it measures | calibration (all PASS on 2026-10-07) |
|---|---|---|
| `py studies/terrain-malleability/consumption/provenance.py` | STOCK/PATCH verdict + patch attribution for every cited line | 4/4 known lines classify correctly |
| `py studies/terrain-malleability/consumption/census.py` | 2178 meshes / 962 prefabs / 480 WMBlock flags / 56 materials / 19 shaders (both discs) → `out/consumption_census.json`; shader text dumped to `%TEMP%\ff9-consumption-shaders\` (outside the repo) | block (8,17) terrain = 339 verts, channels {pos,nrm,uv0,tan}; bundle `WorldMap/Terrain` Bind list == install `StreamingAssets/Shaders/WorldMap/Terrain.txt` |
| `py studies/terrain-malleability/consumption/consumer_map.py` | every engine read site of mesh data, with method + STOCK/PATCH → `out/consumer_map.json` | must find the WMPhysics `tangent.x` read, zero `.y/.z/.w` reads, the area decode in `w_worldGetBattleScenePtr` |
| `py studies/terrain-malleability/consumption/bind_oracle.py --log <Memoria.log snapshot>` | which loose override files the engine BINDS, cell by cell, over the live mod stack → `out/bind_oracle.json` | **81/81** blocks' logged `[WorldMeshOverride] loaded` sequences equal the predicted ordered bind list (1 block excluded, its files changed after the log); the (11,19) pre-fix replay = `[Sea4]` only |
| `py studies/terrain-malleability/consumption/landdonor_water.py` | what a sidecar-less reclaimed cell registers under its Terrain → `out/landdonor_water.json` | raster: (12,0) sea4f covers 100.000%; (12,0) sea4 misses exactly 16 u² |
| `py studies/terrain-malleability/consumption/sea4f_vs_sea4.py` | runtime open-ocean mesh vs the kit's sea-plane source → `out/sea4f_vs_sea4.json` | sea4f vs itself 512/512 |
| `py studies/terrain-malleability/consumption/sea_event_quad.py` | the event-1 tile in every open-ocean cell, and Sea6 vs world triggers → `out/sea_event_quad.json` | (12,0) quad → cell (25,1); dispatcher decode returns multi-cell cases |
| `py studies/terrain-malleability/consumption/matrix.py` | assembles the table below; re-finds every consumer cite by text and re-runs the provenance check | all input calibrations true |

The Memoria.log snapshot used is `Memoria.20261006-2355.log`, copied into the session scratchpad, because the
install's log is overwritten on every launch. It holds 254 `loaded` lines over 82 blocks from the owner's
2026-10-06 23:55 session.

## 1. What data exists (census.py; matrix.py prints it per part)

* **Every one of 2178 stock block meshes** has exactly the channels {position, normal, uv0, tangent}
  (`m_CurrentChannels`=139). None has vertex colour or uv1-3. Every mesh has 1 submesh and 16-bit indices
  (max vcount 2316). Every mesh is flat (vcount == icount). In every mesh the index buffer is a **permutation**
  of 0..n-1 (2178/2178). It is identity in only 33.
* **tangent.y, .z and .w are 0.0 in all 2178 meshes.** tangent.x is uniform across a triangle's 3 corners in
  100% of tris.
* The stored AABB equals the recomputed AABB in 2178/2178 meshes.
* **`0_2` is the FORM-2 mesh set, not a far LOD.** Prefab children `Terrain2`/`Object2`/`VolcanoLava2`/`Sea*_2`
  reference `0_2` meshes: 52 + 51 + 2 + 6. The other **76 `0_2` water meshes are referenced by no prefab**, so
  they are never loaded. `WMWorldPrefabMaker.cs:36,120-139` (STOCK, editor-only) agrees.
* **The prefab CHILD NAMES are the override namespace.** These are the names RegisterBlockComponent keys on:
  Terrain, Object, Terrain2, Object2, Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1-6, Sea3_2/4_2/5_2,
  VolcanoCrater1, VolcanoLava1, VolcanoLava2. The mesh asset is named "VolcanoCrater", but the child that binds
  is "VolcanoCrater1". No prefab has a VolcanoCrater2 child.
* Each disc has 205 IsSea cells. The per-block prefab IsSea flag agrees with the 480 WMBlocks of the bundled
  `WorldDisc-InCaseThatItNeedsToCreateAgain` prefab on both discs (480/480). That prefab is the proxy used for
  the live baked WorldDisc. **15 non-IsSea cells per disc have NO TerrainForm1**: water-only stock blocks such as
  (8,18), (8,4) and (12,0). Only 17 of the 260 disc-1 blocks that have a TerrainForm1 are Terrain-only (275 non-IsSea = 260 with Terrain + 15 water-only).
* **SeaBlockPrefab = `WorldDisc1/r0/Block[12][0]f`.** It is loaded from disc 1 even on disc 4
  (`WMWorld.cs:1198-1200` STOCK). It has exactly one child, `Sea4`, whose mesh is `sea4f` (512 tris).

## 2. The consumption matrix

**Renderer** (census shader binds + `WMBlock.cs:106-110` STOCK):

* Terrain, Terrain2, Object, Object2, Sea1-6, Sea*_2, Beach1/2, River, RiverJoint and Volcano* all use the
  shader `WorldMap/Terrain`. It binds **vertex + texcoord only**. Its lighting is uniform: ambient×2 + ½ΣLightColor.
* **Falls and Stream use `WorldMap/ScrollTexture`**. It binds **vertex + normal + texcoord** and computes
  N·L against the 3 world directional lights (`ff9.cs:4358-4363` STOCK).
* No block shader binds tangent, colour or uv1.

**Walk (on foot and vehicles)** (`WMBlock.cs:54-83,137-232`, `WMPhysics.cs:6-47`, STOCK; full decode =
`studies/path-d-new-world/WALK-QUERY-DECODE.md`):

* Position + index are read. The up-facing test is on the **geometric** normal (`WMBlock.cs:70`, `WMPhysics.cs:22`).
* tangent.x is read at **corner 0 only** (`WMPhysics.cs:15`, `WMBlock.cs:210/231`).
* Full-value skips (`WMPhysics.cs:16-20`): 4078/4088/2040. Veto (`WMBlock.cs:211`): 0x31EE.
* Topograph mask: `ff9.cs:5702`. Cache bypass on topograph 49/52: `ff9.cs:5692`.

**IDALL consumers** (consumer_map.py; all 30 topograph sites, 9 area sites, 4 event sites and 10 full-value sites are STOCK):

| IDALL field | consumers |
|---|---|
| event bits | `WorldEvent` dispatch keyed on the walked **cell** (`ff9.cs:5345-5352`); `EventCollision.cs:449` |
| **area bits** | encounter zone (`ff9.cs:9237`); script sysvar 192 and 207 (`ff9.cs:4202,4262`); **weather for areas 9/12/13** (`ff9.cs:8510-8519`); **forced upper camera + camera toggle disabled for area 12 on scenes < 4990** (`ff9.cs:2771,3199`); location name (`ff9.cs:3757-3758`) |
| topograph | movement masks, sink (`:5636`), get-off (`:5753-5831`), encounter record (`:9248`), sysvar 193/205, dust SPS (`:6184-6196`), vehicle spray and SE 38 (`:6398-6433`), chocobo (`:4330`, `EventCollision.cs:335-345`), camera speed for topograph 49 (`:2993`), encount re-arm for 52 (`:3730`) |
| flags bits | read **only through full-value equality** |
| full value | 4078/4088/2040 skip (`WMPhysics.cs:16-20`); 0x31EE veto; **0xFEE/0x18EE/0x7EE/0x1BEE/0x2CEE make an IgnoreExceptions actor (parked vehicle) keep its stored height** (`ff9.cs:5209-5232`) |

Stock counts (matrix.py): 4078 = 318 tris, 4088 = 286, 2040 = 282, 0x31EE = 56, 0x18EE = 416, 0x7EE = 588,
0x1BEE = 556, 0x2CEE = 484. Flags = 2 on 11019 tris; 2418 of those are special values. Flags 1 and 3 never occur.
Area 9/12/13 tiles = 4777/4082/1873. Area 12 sits in 7 disc-1 blocks around Cleyra/Burmecia (nearest-navipos
label only, not an identity).

**Other consumers:**

* **Camera:** sky-cast under IgnoreExceptions (`ff9.cs:2945-2988`). It reads the first-in-buffer hit, including
  skip-class and down-facing tris (prior art, placement-rules memory).
* **Shadow:** `ground_height` only (`ff9.cs:5146`). No normal is read and nothing is projected.
* **Minimap/navimap:** reads no mesh data. It uses a static PNG + `w_naviGetPos` (OVERWORLD_ENGINE.md).
* **Cell-tag/GetIP:** reads only the event bits + the actor POSITION → cell (`ff9.cs:5348`, `:9267-9271`).
* **Has\* flags** on WMBlock are write-only. Their only reader is our debug menu.

**Loader** (`WorldMeshOverride.cs`, PATCH s34):

* Reads pos + optional normal/uv/tangent + int32 indices. It enforces vcount ≤ 65535 (`:186`) and
  icount ≤ 3·vcount (`:188`). It builds ONE submesh (`:231`) and calls RecalculateBounds (`:232`).
* There is no colour or uv1 channel, so those are not authorable.

## 3. Free bytes vs load-bearing bytes

**FREE** (changing them has zero engine effect):

* tangent.y, .z and .w on every part. Evidence:
  * There are zero C# reads (consumer_map self-check), and no block shader binds tangent.
  * Natural experiment: in the live, play-tested stack, 1337 files carry w=1 and 48 carry y=1 (stock has 0
    everywhere).
  * They are usable as a provenance side-channel, and the s22 block dump records them (`world/readback.py`).
* tangent.x at corners 1 and 2. The engine reads corner 0 only.
* Stored normals on every part EXCEPT Falls/Stream:
  * Walk recomputes normals geometrically.
  * `WMMesh.Normals` is read only in `DrawWalkMeshes`/`TestWalkMeshes` (`WMWorld.cs:982/1040`), which have
    **no callers**.
* Vertex-array order, as long as the index buffer is remapped to match.
* Mesh name and bounds (derived).
* IDALL flags bits, unless the full value becomes or stops being one of the 9 special values.
* Geometry outside the block's 64×64 footprint is render-only (BLOCK LAW, prior art).
* Override files whose name is not a child of the effective prefab. There are 939 in the live stack, all
  intentional 1-tri blanks: 937 on donors without that child, plus 2 Terrain divert-arm stubs.
* The 76 orphan `0_2` water meshes.

**LOAD-BEARING:**

* **Position:** render, walk height and plan, camera ride-up, shadow Y.
* **Index buffer.** It must be flat (vcount == icount): a surplus vertex makes LoadBlocks throw, a deficit makes
  TriangleNormals short (UNINDEXED CONTRACT memory; loop at `WMBlock.cs:65`). The index buffer also determines:
  * winding → the walk filter and back-face culling;
  * order → first-tri-wins and the camera hit;
  * corner 0 → the IDALL source.
* **uv0:** the only appearance lever for WorldMap/Terrain parts.
* **Normals on Falls/Stream:** brightness. Whether pixels move depends on the light colours being nonzero
  (see Open questions).
* **tangent.x at corner 0:** every IDALL consumer in §2.
* **The tangent array (flag bit 4) on any walk-registered part.** Without it, `tangents[...]` indexes an empty
  array on the first ray over the block (`WMPhysics.cs:15`). The bind oracle audited 747 bound live files:
  0 violations.
* **Override file NAME** (must equal an effective-prefab child).
* **Existence of `Terrain.ff9mesh` on an IsSea cell.** It arms the divert. Its content is irrelevant when the
  donor has no TerrainForm1.
* **`Donor.txt` content.** It selects the prefab, and every child of that prefab rides along.

## 4. THE EFFECTIVE-PREFAB LAW and the (11,19) verdict

**Route** (`WMWorld.cs:516-544`; streaming mirror `:1287-1303`; async `:886-908` only when !IsSea):

* IsSea=0 → the cell's own prefab (STOCK).
* IsSea=1, and `HasLandOverride` is true (PATCH s34/s74; = `File.Exists` of `Block[x][y] Terrain.ff9mesh` in
  any folder, `WorldMeshOverride.cs:80-83`) → `ResolveReclaimDonor` (`:549-569`). That returns the Donor.txt
  prefab, or `LandDonorPrefab` = Block[12][10] of the current disc (`:1210-1211`).
* Otherwise → SeaBlockPrefab (STOCK).

**Binding.** `LoadBlock(prefab)` (`:582-810`) registers each slot the prefab has, in this order:

1. Object
2. Terrain
3. bare-Object rule (render-only, s34 `:595-596,868-884`)
4. Object2
5. Terrain2
6. block 219's early return (`:601-637`)
7. Volcano*
8. Beach1/2
9. Stream
10. River
11. RiverJoint
12. Falls
13. Sea1-6

Each `RegisterBlockComponent` looks up `TryLoad(".../0_1/r{y}/Block[x][y] " + child name)` (`:823-825`, s34/s74).
An override binds **iff the effective prefab has that child**. A stock child that has no override still
registers its own stock mesh: it free-rides, rendering and acting as walkmesh.

**Trace table** (`bind_oracle.py`, disc 1; every probe part was offered as an override):

| case | Terrain.ff9mesh | effective prefab | bound | dead |
|---|---|---|---|---|
| plain land (15,13) | either | own | Terrain if present (+ bare Object) | Donor.txt, all water parts |
| coastal (8,17) | either | own | Terrain?, Object (bare), Sea3/4/5 | Donor.txt, Sea1/2/6, Beach1 |
| water-only non-IsSea (8,18) | either | own | Sea3/4/5 | **Terrain (dead even when present)**, Donor.txt |
| sea (11,19) | absent | 12,0f | **Sea4 only** | everything else, including Donor.txt |
| sea (11,19) | present, no Donor.txt | 12,10 | Terrain, Object (bare), Sea1/3/4/5 | — |
| sea (11,19) | present + Donor 8,17 | 8,17 | Terrain, Object (bare), Sea3/4/5 | — |

**(11,19) verdict: RESOLVED.** The hypothesis is REFUTED as stated. The Terrain-presence intuition was right,
but at the wrong layer.

1. Registering Sea parts never depends on Terrain. `if (prefab.SeaN) RegisterBlockComponent(..., true, true)`
   (`WMWorld.cs:778-807`, STOCK). Stock already ships 15 water-only non-IsSea blocks per disc that walk and sail,
   among them (8,18), the very donor of this carry.
2. The real mechanism is prefab selection. (11,19) is IsSea=1, so without a Terrain override FILE the divert is
   un-armed. The cell then loads Block[12][0]f, whose only child is Sea4. Sea3 and Sea5 are never looked up, and
   Donor.txt is never read.
3. The carried Sea4 is a partial band. Its holes become ground-query misses, which produce an invisible vehicle
   wall and a void render.
4. Receipts:
   * The ADDENDUM-3 log (GROUND-FAMILY-DECODE §4) shows only `Block[11][19] Sea4` loaded.
   * The oracle replay of the pre-fix file set predicts exactly `[Sea4]`.
   * **The live 2026-10-06 log** (lines 253-255) shows `Block[11][19] Sea3, Sea4, Sea5` loaded and **no Terrain
     line**. That is exactly the divert-armed prediction: the stub Terrain is `File.Exists`'d, never `TryLoad`'d,
     because donor (8,18) has no TerrainForm1.

**Minimal tests that settle it.**

* Offline: `bind_oracle.py` replaying any file set. It is already calibrated against 81 live receipts.
* In-game (zero visual judgement): on a scratch IsSea cell, deploy Sea3+Sea4+Sea5 without Terrain → relaunch →
  the Memoria.log shows Sea4 only. Then add a 1-tri Terrain stub + Donor.txt pointing at a {Sea3,Sea4,Sea5}
  prefab → the log shows all three.

This was already played out across ADDENDUM 3-6 and owner-confirmed. The arc is CLOSED. The
`project-ff9-overworld-audit-roadmap` memory entry that still calls it OPEN is stale.

## 5. New findings beyond the brief (each with its script)

* **The land donor Block[12][10] is an open-ocean ISLET, not "plain inland land".**
  * Its prefab has Terrain (29 tris, 13u islet, y 0-3.77) + Sea1/Sea3/Sea4/Sea5.
  * Its water covers **97.30%** of the cell, and **93.27% is a boat-legal first hit**: topograph 57/54/53.
    The 2.70% hole is exactly the islet (`landdonor_water.py`).
  * The s34 comment `WMWorld.cs:1207-1209` says otherwise ("no beach/sea"), and so do two memories.
  * Consequence: a sidecar-less reclaimed cell — `terrain.reclaim`'s shipped deploy shape, which writes no
    Donor.txt — registers 12,10's Sea1/3/4/5 as Form1+Form2 walkmesh under the land. The 2026-07-02
    "height 0 z-fights with the sea surface" observation fits this, since nothing else can be coplanar inside
    the cell.
* **Sea6 fills Sea4's hole at (12,0).** The one missing quad in Block[12][0]'s Sea4 (16 u², local x60-64,
  z−44..−48) is exactly covered by its Sea6 (pixel-equal plan coverage). `sea4f` = Sea4 + those 2 tris
  (510 shared + 2), carrying Sea6's IDALL 16612 (= **event 1**, area 0, topograph 57).
  * So every IsSea cell ships an event-1 4×4 quad at cell (2bx+1, 2by+1).
  * 0 of 205 collide with a WORLD00 trigger, so it is inert in stock.
  * 3 of the 4 disc-1 Sea6 tiles DO sit on scripted ("None"-case) trigger cells (25,1), (17,30) and (39,15).
  * `sea_event_quad.py`.
* **The per-cell PNG texture hook (s34) is overwritten for Terrain, Terrain2, Object, Object2, Falls and Stream.**
  * `RegisterBlockComponent` assigns a cloned material (`WMWorld.cs:842-844`, PATCH). `LoadBlock` then ends with
    `SetupPreloadedMaterials` (`:808`, STOCK), which reassigns `MaterialDatabase[child name]`.
  * `MaterialDatabase` holds those names when their texture is found loose. On this install MoguriMain ships
    `res(1_24)_terrain/objects.png`, `11_0_192.png` and `11_64_192.png`.
  * Only Sea/Beach/River/RiverJoint/Volcano per-cell PNGs survive, and those become static (not animated).
* **Every bind failure is SILENT.** Unbound files produce no log line. Only binds log. A file existing on disk
  is not evidence that the engine reads it, so audit by effective prefab (`bind_oracle.py`).

## 6. Recorded claims this lane contradicts

* **`project-ff9-sea4-under-land-law.md:105`** ("a sidecar-less reclaimed cell resolves to [12][10] — no
  beach/sea … has **no water meshes whatsoever** … sealed") and **`project-ff9-overworld-terrain-authoring.md:63`**
  ("PLAIN inland donor (Block[12][10], no sea/beach sub-meshes)") are contradicted by the 12,10 prefab: it has
  Sea1/3/4/5, 97.30% coverage, 93.27% boat-legal. The "sealed" consequence therefore becomes a prediction of
  **boat-through-land**: the boat steps ≈0.94u (speed_move 240 vs foot 112). It is predicted for the flat
  profile with height > ~2.3 and for the cliff profile. It is not predicted for the island profile, whose 22u
  sand ramp blocks the boat, or for flat at height 0. This is a HYPOTHESIS until a boat test is run.
* **`project-ff9-world-locate-cell-tag-join.md` / the MEMORY.md index line** "IDALL area COSMETIC" and "Tile
  `--area` stamps are pure bookkeeping". Area drives:
  * the encounter zone (`ff9.cs:9237`), which the southern-ring memory already knows;
  * weather for areas 9/12/13 (`:8510`);
  * the forced camera for area 12 (`:2771,3199`);
  * sysvars 192/207 and the location name.

  It is non-dispatch, not cosmetic. `world/extract.py encode_id` calls it "the cosmetic regional tag".
* **`ff9mapkit/world/extract.py:11` and `cli.py:8960`** say "`0_2` is a far LOD". It is the Form-2 set (§1).
* **`project-ff9-overworld-placement-rules.md`** says the (12,0) Sea4 hole is "covered by something else at
  home". That something is Sea6, and the runtime open ocean is sea4f, not sea4 (§5).
* **`project-ff9-overworld-audit-roadmap.md`, "OPEN (11,19)"** is stale. The study closed it (§4).
* **Confirmed with a refined scope:** GROUND-JUNCTION-SYNTHESIS "WorldMap/Terrain binds NO normal" is TRUE (bundle
  and install copies agree, and `WMMesh.Normals` has zero live readers). "Ground normals are render-inert" holds
  for every part except Falls and Stream.

## Open questions

* Do the 3 world directional lights carry nonzero colour? The colours come from the weather table
  (`ff9.cs:4374-4387`). If yes, Falls/Stream normals change pixels. Probe: override one Falls mesh with flipped
  normals and take a `game_snap` A/B at a fixed camera.
* Does a sidecar-less reclaimed cell let the Blue Narciss sail under it? Prediction: yes for flat with height > 2.3
  and for cliff; no for island and flat-0. Cheapest decisive premise check: the s22 block dump
  (`~ → World → Dump`, parsed by `world/readback.py`) of a reclaimed scratch cell lists walk_form1 meshes for
  Sea1/3/4/5. Behaviour check (harness, `project-ff9-test-harness`): put the boat at the cell edge and drive into
  it, logging `ground_height` and topograph per tick.
* Does a WORLD00 trigger at (2bx+1, 2by+1, event 1) on an IsSea block fire when sailing or flying over the sea4f
  quad? This matters for Path D, where all cells are IsSea. Probe: a scratch trigger on a bench sea cell.
* Is the live baked WorldDisc equal to the bundled InCase prefab? Its IsSea flags agree 480/480 with the
  per-block prefabs, but the live one is in a scene bundle that was not read.
