# Gap lane `gap_area_layer`: the tile AREA bits as an authored layer

This lane covers every consumer of the tile AREA bits, the stock area geography, a live audit, a per-writer audit,
and a proposed kit policy with a lint.

Everything here was read-only: the install, the Memoria clone, the memory store and all tracked files. Nothing was
deployed. Engine cites are `file:line` under `C:\gd\FFIX\Memoria\Assembly-CSharp`, at the current patched tree.
STOCK and PATCH come from the consumption lane's calibrated oracle (`consumption/provenance.py`, 4/4 calibration
cases). Every number below comes from a script in this directory. Each script checks its own calibration and exits
1 if the check fails.

## Instruments (rerun in this order, from the repo root)

| script | measures | calibration (all PASS 2026-10-07) |
|---|---|---|
| `py studies/terrain-malleability/gap_area_layer/engine_consumers.py` | every C# reader of area: direct, sysvar 192/207, LUTs, routes, 1-level callers. Also parses the area-keyed tables from source. Output `out/engine_consumers.json` | Re-finds all **9/9** consumption-lane area sites **and** `w_cameraArea2Place` (ff9.cs:3117). Parsed `w_worldAreaZone` equals the kit's `worldpack._AREA_ZONE`. Any consumer without an annotation fails the run. |
| `py studies/terrain-malleability/gap_area_layer/eb_consumers.py` | every GET of sysvar 192/207 in the 13 stock dispatchers plus the live overrides (US language), and the branch each read feeds. Output `out/eb_consumers.json` | Re-finds WORLD00's **25-arm sysvar-207 ENCRATE ladder** (agrees with `encounter.freq_writes`). Its own walk counts **18/18** `RunWorldCode(26)` writes (agrees with `encounter.rate_writes`). The single 192 switch's arm set equals `EMinigame.BeachData`. |
| `py studies/terrain-malleability/gap_area_layer/calibrate.py` | the area reader and the ground-query raster. Output `out/calibration.json` | **C1:** the (8,17) terrain area histogram is identical from p0data and from a `ff9mesh_bytes` copy in the scratchpad, and one flipped area bit is detected. **C2:** `arealib.raster` matches `placement.place(sky=True)` on **5376/5376** samples (Terrain 1151, Object 5, Sea/Beach 4219, MISS 1). |
| `py studies/terrain-malleability/gap_area_layer/stock_atlas.py` | stock area geography of both discs at 1u, with exact containers via `disc4/d4lib.mesh_objects`. Output `out/stock_atlas.{json,npz}`, `out/area_atlas.png` | uses the C2-calibrated raster |
| `py studies/terrain-malleability/gap_area_layer/camera_place_effect.py` | how far each camera place moves the camera at real stock heights, stock place seams, and MISS locations. Output `out/camera_place_effect.json` | — |
| `py studies/terrain-malleability/gap_area_layer/live_audit.py` | every live override cell on Disc1/4/9: bind (consumption `bind_oracle.Engine`), per-file area histograms, ground-query areas, record holes and consequences. Output `out/live_audit.json` | uses C2 and the bind oracle (81/81 disc-1 receipts) |
| `py studies/terrain-malleability/gap_area_layer/lead_1918.py` | the Block[19][18] lead. Output `out/lead_1918.json` | — |
| `py studies/terrain-malleability/gap_area_layer/writer_audit.py` | per-writer area class with re-located cites, every case world-entrance can stamp, and donor areas. Output `out/writer_audit.json` | every code needle must be found |
| `py studies/terrain-malleability/gap_area_layer/area_table.py` | all 64 areas against every consumer, plus safe-road candidates per camera place. Output `out/area_table.json` | — |
| `py studies/terrain-malleability/gap_area_layer/area_lint.py` | the prototype lint AL1-AL8 over all live cells. Output `out/area_lint.json` | **FIRES** on Block[19][18] (AL1+AL3+AL4). **FIRES** AL2 on a synthetic area-40 stamp (1973 u², 64 seam pairs). **SILENT** on the same cell unstamped. **SILENT** (no ERROR/WARN) on stock Uaho (0,0) fed in as authored. |

Stock meshes are cached as numpy in the session scratchpad (`arealib.SCRATCH`), outside the repo. `out/` holds only
derived label rasters, statistics and renders. World location names are resolved at runtime and only printed: the
`*_stdout.txt` files carry the dozen names relevant here and are not a table dump.

## A. The complete consumer table

### A1. Engine (C#)

`engine_consumers.py` finds 28 rows: 26 STOCK, 2 PATCH.

| # | consumer | cite | prov | cadence | what area changes |
|---|---|---|---|---|---|
| 1 | **encounter scene** `w_worldGetBattleScenePtr` | ff9.cs:9237 (via `w_worldArea2Zone` :9229-9231, LUT :1348) | STOCK (+ **s60** miss → null :9264, `SelectScene` EventEngine.cs:194) | each encounter that fires | zone → record slice → (topograph, fog) row. Under s60 a hole means no battle. Stock falls back to the slice's last record. |
| 2 | **camera place** `w_cameraChangeUpdate` | ff9.cs:3117 (table :81, elements :231-322, posstats :148) | STOCK | **every camera frame**, no easing (the change-counter blend is only for vehicle swaps, :3141; `w_cameraChange` callers :5976/:5978/:5995 only) | **place 0** = areas 0-26 and 46-50; **place 1** = areas 40-45; **place 2** = areas 27-39 and 51-63. On foot the place selects the 'down' posstat (0/3/1). It is blended to 'up' by actor height and matters only below y = 13.67 (:3181). |
| 3 | **area-12 lock** `w_cameraUpdate` | ff9.cs:2771 | STOCK | every camera frame while ScenarioCounter < 4990 (`w_frameScenePtr` = gEventGlobal u16[0], :3652) | sets `upperCounterForce`, which drives the perspective counter to **0, the DEFAULT view** (:3124-3133) |
| 4 | **area-12 toggle refusal** `w_cameraChangeTrigger` | ff9.cs:3199 | STOCK | each press of the perspective toggle | the toggle to the high view is refused: counter 4096 = posstat 7, eye 29.3u (`SetPerspectiveToggle`, WMScriptDirector.cs:139) |
| 5 | **spawn weather** `w_weatherDeside` | ff9.cs:8510 | STOCK | **one-shot**, when `w_frameCounterReady == 10` and the script number is 0, so it reads the area under the spawn | areas 9/12/13: Color[3] g/toffsetup = 32600, weather re-dest, `w_frameCloud = false` (clouds off) |
| 6 | **window title** `w_worldLocationName` ← `w_frameUpdateEvent` | ff9.cs:3757-3758, :3745 | STOCK | every world frame | `WorldLocationText(area)` in the PC window title, shown when area ≠ 0 or topograph is 0 or 37 |
| 7 | sysvar 192 / 207 | ff9.cs:4202 / :4262-4263 (`w_frameGetParameter`) | STOCK | on demand | area / `w_worldArea2Zone(area)`. Script route: `B_SYSVAR` → EBin.cs:1246 → EventEngine.GetSysvar.cs:105 |
| 8 | **main-menu location label** `DisplayGeneralInfo` | MainMenuUI.cs:527 | STOCK | each menu draw | `WorldLocationText(sysvar192)` |
| 9 | **save-slot Location** `MenuOpenEvent` | UIManager.cs:586-587 → `FF9.mapNameStr` → SharedDataBytesStorage.cs:482 | STOCK | each world menu open | the area's name is **written into the save preview slot's Location** (persistent) |
| 10 | **beach search** `CheckBeachMinigame` | EMinigame.cs:726 (BeachData :768, 21 areas) | STOCK | polled every frame by EIcon.cs:131, EventCollision.cs:328, EventInput.cs:206 | When `GLOB.Bit[1042]` is set, the player is on foot (ControlNo 0) and the area is in BeachData, the Beach bubble shows, Confirm is stripped from a world trigger (SQEX #2893), and the visit bit is GLOB 856+i (AllSandyBeach achievement, :480). Areas: {4,5,13,16,17,18,19,25,29,30,31,33,37,38,46,47,49,50,51,52,58}. |
| 11 | Journal counter `ReadCounter` | JournalUI.cs:365 | **PATCH** s82 | on draw | reads any configured sysvar. It consumes area only if an entry is authored with 192/207. |
| 12 | debug readout `WorldReadout` | Ff9mkDebugMenu.cs:1750 | **PATCH** s22 | while the ~ World tab is open | display only |

**Missed by every earlier census:** row 2 (camera place), row 9 (the save-slot chain) and row 10 (the beach search,
four sites). The consumption C4 list has 5 entries. VERIFY.md added rows 8 and 9's first hop, but not the
SharedDataBytesStorage write.

**Prior art the lanes missed:** `world/interior.py:1381-1384` already names `w_cameraArea2Place`: "Uaho's baked
area=63 is bucket 2 = cameraDistance 6000". That is consistent: place 2's foot 'down' is posstat 1, distance
6000/256 = 23.44u.

**Camera place magnitude** (`camera_place_effect.py`, all walkable stock land, disc 1):
* 87.3% of samples sit below y = 13.67 (median y 3.85), so the place matters almost everywhere.
* Posstats in units:

  | posstat | role | distance | height | correct | pers |
  |---|---|---|---|---|---|
  | 0 | place-0 foot down | 19.53 | 8.59 | 11.72 | 320 |
  | 3 | place-1 foot down | 27.34 | 17.19 | 1.95 | 350 |
  | 1 | place-2 foot down, chocobo | 23.44 | 12.50 | 11.72 | 350 |

* Restamping place-0 ground to place 1 moves the on-foot camera by a median **+4.41u distance, +4.85u height,
  −5.51 cameraCorrect, +16.9 pers** (pers drives the FOV through `cameraPers/8`, ff9.cs:2676). Maxima are
  6.07 / 6.68 / 7.59.
* Restamping place 0 to place 2 moves it by a median +2.21 / +2.21 / 0 / +16.9.
* Chocobo (type_cam 1) treats place 0 and place 2 identically; only place 1 differs.
* Airships (type_cam 3) differ only at place 1 (cameraCorrect 13.28 vs 14.06).
* Blue Narciss (type_cam 2) and control 6 (type_cam 4) ignore the place.
* **Stock has ZERO walkable↔walkable camera-place seams on either disc**: 0 pairs. All 8257 place-change pairs touch
  water or unwalkable ground. In stock, camera place is a continent constant (atlas).

### A2. WORLD .eb (all 13 stock dispatchers, plus the live ones and WORLD13)

`eb_consumers.py` finds exactly two kinds of read:

* **sysvar 207** is read exactly once per free-roam dispatcher: WORLD00/02/03/05/07/08/09/10/11, plus live WORLD13.
  The read is always the 25-arm ENCRATE ladder in an entry's **tag-1 loop**, so it runs per frame. The ladder vector
  per zone is {0:12, 1:16, 2:11, 3:14, 4:16, 5:14, 6:16, 7:14, 8:16, 9:16, 10:24, 11:12, 12-22:16 (except
  15:11, 19:14), 23:32, 24:16}.
* **sysvar 192** is read exactly once in the whole corpus: WORLD08 entry 3 tag 1 @6265, a 21-arm switch.
  * Its arm set is exactly `BeachData`, and each arm sets `GLOB.Bit[856..876]`.
  * The read is gated by sysvar 209, `Map.Byte[35]`, usercontrol, a KEYON, `Global.Byte[190]` and `GLOB.Bit[1042]`.
  * So **the beach visit is recordable only in world state 9008**, while the C# icon (row 10) runs in every state.
* No dispatcher reads area for music, SPS, chocobo, Mognet or vehicles.
* The entrance "AREA switch" (entry-1/tag-1, base 2) is keyed on `Byte[39]`, not on sysvar 192. That confirms the
  cell-tag law.

## B. Stock area geography (`stock_atlas.py`, `out/area_atlas.png`)

* **All 64 area values occur on both discs** (64/64). **There is no unused or virgin area.** Every stamp aliases a
  stock region's zone, label, camera place and beach arm.
* **Camera place is continental.**
  * Place 0 covers the Mist Continent plus the southern and western islands (areas 0-26, 46-50).
  * Place 1 covers the western continent (areas 40-45; area 41 alone is 51,460 u²).
  * Place 2 covers the northern continents (areas 27-39, 51-63).
* Area 0 is also the whole ocean: 1,422,235 water u² on disc 1. Only 6,416 water u² carry a non-zero area
  (Beach/Sea rims). Area 0 land is 94,098 u² in 1,337 land components; the largest is 75,018 u², centred on block
  (18.0, 12.6).
* 41 of 64 areas are a single landmass on disc 1 (43 on disc 4).
* **Area boundaries are terrain-shaped, not block-aligned.**
  * Only 2.5% of area-boundary sample pairs lie on a 64u block border (disc 4: 2.3%). The null rate for random
    pairs is 1.56%.
  * 64.2% of area boundaries are also topograph changes (66.4% on disc 4).
  * Only 18.5% of topograph boundaries are area boundaries (18.1% on disc 4).
  * Land-bearing blocks carry 1-5 areas each: {1:54, 2:90, 3:83, 4:27, 5:6} on disc 1.
* **Disc 4 relabels part of the Mist Continent.** Area 0 land falls from 94,098 to 86,111 u²; area 7 rises from
  30,293 to 36,412; area 6 falls from 4,193 to 3,525; areas 14 and 22 gain about 450 u² each. A disc-1 → disc-4
  byte mirror therefore carries disc-1 labels into disc-4 ground.
* Area 12 (lock, weather) is two components (9,331 u²) in the west of the Mist Continent, the Cleyra desert region.
* The atlas has 822 MISS samples per disc, 591 of them in blocks (16-17,14-15). They do not affect area statistics.

## C. Live audit (`live_audit.py`; Disc1 82 cells, Disc4 82, Disc9 65)

Walkable u² by area, from the engine ground query over every live cell, at the live record table:
* Disc1 and Disc4 use `FF9CustomMap-world/.../disc1/discmr.img.bytes` (disc 1) and stock p0data (disc 4).
* Disc9 uses the live disc-1 table and is assumed to run with `w_frameDisc` 1.

**Disc1 (Disc4 is identical; it is the mirror):**
* **area 14** (Lindblum Plateau): zone 6, place 0. 147,102 u² walkable, of which **0** u² can encounter: every
  ground topograph {0,3,16,17,31,32,41} is a hole. This is the R4b safe road, and it needs s60.
* **area 0**: zone 0. 958 u² walkable, of which 910 can encounter:
  * the canopy at (1,2)/(2,2), 440 + 220 u², as designed;
  * the **quay trigger tiles**: 48 u² at each of (0,18), (1,6), (6,19) and (10,9), and 58 u² at (22,18). These are
    IDALL 16384, area 0, topograph 0, zone 0, so they can encounter while the area-14 ground around them cannot.
  * Grimhorn (18,18) is IDALL 16452, topograph 17, which is a hole.
* **area 12** (Vube Desert): zone 5. 228 u² at **(19,18)**, all able to encounter, with the camera **lock** and
  spawn weather.
* **area 49** (Palmnell Island): zone 18. 108 u² on Beach1 at (12,18)/(12,19), a hole. This is a **beach arm**: the
  R4b stamp only rewrote Terrain, so the Sandreach Beach1 kept its donor area 49.
* Mosaic: **0** walkable place seams; 438 walkable zone-change pairs (the designed canopy/quay/road mix).

**Disc9 (Path D)** keeps its donors' areas:
* Walkable u² by area: 0 (56,518), 7 (1,566), 6 (100), 40 (2,520), 48 (4,683), 50 (1,024), 57 (9,086), 58 (3,406),
  62 (2,945), 63 (754).
* Almost all of it can encounter (AL5 fires on 61/65 cells). There are 7 zones {0,2,15,18,21,23,24} and 3 camera
  places:
  * the area-40 island (14-15,12-13) is place 1;
  * the 57/58, 62 and 63 islands are place 2.
* The Uaho carry at (13,15) is area 63, **zone 24**: 754 u² can encounter, using the zone REVERT §26.1 lists as
  Adamantoise / Worm Hydra.
* The area-62 carry at (10-11,12-14) is zone 23, whose **ENCRATE is 32**, about 1.63× the battle frequency of
  zone 0.
* Mosaic: **0** walkable place seams. Every island is internally single-place, so the camera changes per island, not
  per tile. There are 412 walkable zone-change pairs.

**Leads:**
* **Disc1/Disc4 Block[19][18]** (`lead_1918.py`):
  * The 45 tris are IDALL 19620 (event 1, area 12, topograph 41). After a (+348, −404) translation, lifted 0.47u,
    they are an **XZ-exact verbatim copy of stock Cleyra's entrance tile set**.
  * IDALL 19620 occurs in stock only in disc-1 blocks (13,11)×6, (13,12)×15, (14,11)×6 and (14,12)×18, which is
    45 tris. The nearest landmark is Cleyra, 1.95u away.
  * Their packed cell tags (38-39, 36-37, e1) match **no object-0 tag in any of the 14 live dispatchers**, so they
    are inert as an entrance. They are fully live as an area consumer:
    * zone-5 battles on 228 u²;
    * the camera lock and refused toggle below scenario 4990;
    * spawn weather;
    * the "Vube Desert" label in the title, the menu and the save slot.
  * The file's mtime is 2026-07-26 16:01, the R4b area-14 stamp. That stamp deliberately skipped event tiles
    (REVERT §26.2).
  * REVERT §26.2 and commit e192f17c attribute these verts to "the horseshoe carry". The horseshoe donor (5-6,15-16)
    carries areas {48:~60%, 0} and **0** tris of IDALL 19620. The tiles are a **Cleyra-region carry**, the same
    region as Grimhorn's original area-12 ground. Which verb ran the carry is not established.
  * The Grimhorn arrive point (1214, −1192) is 17u west of their bounding box, so a ferry arrival does not trigger
    the weather.
* **Disc1 Object "area 15" (1620 tris, 6 cells)** is the walk-skip IDALL **4078 = 0x0FEE**, whose bits decode as
  area 15, topograph 59, flags 2. That is 6 × 270 quay beacons. They are never a ground hit, so they are **not an
  area consumer**. The Disc9 "area 15" (1064 Terrain tris) is the same 4078 artifact.
* **Disc9 donor areas {0,6,7,40,48,50,57,58,62,63}** are carried by Donor.txt prefabs and Terrain carries:
  * area 7 from the forest donor (15,15) canopy;
  * areas 48/50 from donors (6-7,16);
  * 57/58 from (14-17,1-2);
  * 62 from (9-10,5-7);
  * 63 from (0,0), Uaho.
  * Three carried event clusters are inert (AL8): (2,4) and (20,17) area 57; (13,15) area 63.

## D. Per-writer audit (`writer_audit.py`)

| writer | class | cite (ff9mapkit/ff9mapkit/…) |
|---|---|---|
| world-island / islandbeach | STAMP-CONST 0 | world/island.py:462-463, world/islandbeach.py:141 |
| world-reclaim + synthetic emitters | STAMP-CONST 0 | world/mesh.py:555, :641, :716 |
| building (blendio) | STAMP-CONST 0, or the caller's idall (4078 recommended) | world/blendio.py:231 |
| **world-entrance** | **STAMP-CASE**: area := case & 0x3F, by default | world/entrance.py:1027; `--no-tile-area` cli.py:9886 |
| world-retarget | USER (default keep) | world/mesh.py:1417; help cli.py:9025 |
| world-mountain | STRIP → 0 (event and area dropped) | world/interior.py:1386 (rationale :1381-1385) |
| world-forest | PRESERVE donor canopy; the grass zip is 0 | world/interior.py:711 / :707 |
| world-hill | PRESERVE host | world/interior.py:896 |
| world-transplant (rect carry, ground retile) | PRESERVE (donor bytes; retile changes topograph only) | world/transplant.py:402 |
| coast morph | STAMP-HOST (local block's area) | world/coastmorph.py:6056, :6066 |
| coast nav / rim retile / orphan gate | PRESERVE (topograph-only) | world/coastnav.py:16, world/orphangate.py:620 |
| disc mirror | PRESERVE (byte copy) | world/discmirror.py:87 |
| Path D Donor.txt cells | PRESERVE donor prefab (engine route) | measured in C |
| R4b safe-road stamp (study script) | STAMP-CONST 14 for event == 0 and topograph not in 36-38 | REVERT.md §26.2 |

Measured consequences of the data-dependent writers:

* **world-entrance's default stamp**, over all 151 cases it can stamp (2-60, 53, and 61-155 minus 91-93):
  * **3 cases lock the camera**: 12, 76 and 140, because case & 0x3F wraps.
  * **9 cases set spawn weather.**
  * **62 cases change the camera place**: 12 to place 1 and 50 to place 2. Each one creates a walkable place seam on
    the trigger tiles.
  * **49 cases arm the beach.**
  * **70 cases make topograph-0 trigger tiles able to encounter.**
  * **89 cases wrap** (case ≥ 64).
* **Donor areas:**
  * the forest donor (15,15) canopy is **area 7** (zone 2);
  * the mountain donor (0,0) is 63/0;
  * crag (10,5-6) is 62/0;
  * the horseshoe (5-6,15-16) is 48/0;
  * comp20 (12,16-17) is 7/0;
  * the Cleyra junction (13-14,11-12) is 12/13/9/0.

## E. Proposed kit AREA POLICY and lint

**The principle.** Area is an authored layer with **seven channels**:

1. the encounter zone (`ff9.cs:9237`);
2. the per-zone ENCRATE frequency (every ladder);
3. the camera place (`ff9.cs:3117`);
4. the area-12 lock (`ff9.cs:2771/3199`);
5. spawn weather (`ff9.cs:8510`);
6. labels (title, menu, save slot);
7. the beach search (EMinigame and WORLD08).

Every writer **declares** a target area. The **site policy area** is chosen in two steps:

1. Pick the camera **place** of the stock walkable ground the new land is walk-connected to. Open-sea sites default
   to place 0.
2. Within that place, pick by **encounter intent**.
   * For a safe road, use a candidate from `area_table.py`. Each candidate is a hole for every safe-road
     topograph {0,3,16,17,31,32,41} and carries no lock or weather:
     * **place 0:** {14 (proven), 22, 26, 2, 3, 10, 11};
     * **place 1:** {40-45};
     * **place 2, without a beach arm:** {53-56}.
   * For encounter ground, use an area whose zone has records for the ground's topographs.
3. Safe roads need **s60**. On stock Memoria a hole falls back to the zone's last record.

| # | writer | rule | measured consequence it prevents |
|---|---|---|---|
| R1 | world-island, world-reclaim, mesh emitters | stamp the **site policy area**, not 0 | Area 0 is zone 0, which has records at topographs {0,13,37}, so minted grass rolls Python/Goblin/Mu. The ring needed a post-hoc 85,236-vert / 112-file restamp (REVERT §26). |
| R2 | world-entrance | default `--no-tile-area`: event tiles **inherit the host ground's area** (the dominant area of the authored ground in the cell). Never area := case. | 3/151 cases lock, 62/151 change the place, 70/151 make the trigger encounter-live, 89 wrap. Live: 5 armed quay clusters are zone-0 islands inside safe area-14 ground (AL3/AL5). |
| R3 | world-retarget `--area` | keep as a user flag, but print the area's consequence row, refuse area 12 and any place change against neighbouring ground unless `--force`, and fix the help text | AL1/AL2 |
| R4 | world-mountain | keep the strip, but strip to the **site policy area** instead of 0 | a carried Uaho at 63 would be place 2 and zone 24 (Path D measured: 754 u² encounter-live) |
| R5 | world-forest | stamp the canopy to a declared **canopy area** (the ring uses 0); default to the site policy area; carrying 7 must be deliberate | Path D area-7 canopy: 1,566 u² of zone-2 encounters |
| R6 | world-transplant, Path D Donor.txt carries | restamp walkable carried ground to the site policy area unless `--keep-donor-area`. Carried EVENT tiles become event 0 with the host area unless `--keep-entrances` is set **and** a dispatcher tag exists. | Disc9: 10 areas, 7 zones, 3 places. Area 62 runs at ENCRATE 32. 3 inert carried event clusters. The Cleyra tiles at (19,18) lock the camera. |
| R7 | coast morph (STAMP-HOST), topograph-only writers, world-hill | keep as is | 0 walkable place seams in every live mosaic |
| R8 | disc mirror | after mirroring, lint disc 4 against **disc 4's own** stock layer | disc 4 relabels about 8k u² of area 0 |
| R9 | Object/building overrides | use idall 4078 (walk-skip) on donor-backed cells; the lint explains the "area 15" decode | 1620 + 1064 artifact tris |
| R10 | the R4b stamp | make it the emitter default (R1) **and** extend it to non-Terrain walk parts (Beach1 area 49 survived) and to event tiles (R2) | Sandreach Beach1 area 49 is a beach arm; 45 Cleyra tiles; 5 quay clusters |

**Lint spec**, prototyped in `area_lint.py`. It judges only authored ground: override-sourced samples whose IDALL
differs from stock at that position. Path D samples are all authored.

| rule | level | fires when | tied to |
|---|---|---|---|
| AL1 LOCK | ERROR | authored walkable area 12 | ff9.cs:2771/3199/8510 |
| AL2 PLACE-SEAM | ERROR | a walkable↔walkable 4-neighbour pair, either side authored, whose camera place differs | ff9.cs:81/3117 (no easing); stock has 0 |
| AL3 EVENT-AREA | WARN | an authored event tile's area differs from its cell's dominant authored ground area (reports armed or INERT) | R2 |
| AL4 WEATHER | WARN | authored walkable area 9/12/13 | ff9.cs:8510 |
| AL5 ENCOUNTER | INFO (WARN if the cell is declared safe) | authored walkable (zone, topograph, fog 0) has a record | ff9.cs:9237 + s60 |
| AL6 BEACH | INFO | an authored walkable area is in BeachData | EMinigame.cs:726, WORLD08 |
| AL7 SKIP-DECODE | INFO | override tris carry 4078/4088/2040 (area bits are a decode artifact) | WMPhysics skip |
| AL8 INERT-EVENT | INFO | an authored event tile's cell tag matches no live dispatcher tag | WorldEvent / GetIP |

**Live result.**
* **Disc1 and Disc4 (identical):**
  * AL1 ×1 and AL4 ×1 at (19,18).
  * AL3 ×8: 5 armed quays, Grimhorn, the inert Cleyra set, and (12,18). At (12,18) the donor (9,17) Object's
    3 event tris are inert. On Disc1 they are a stock free rider; on Disc4 they come from an override.
  * AL5 ×8 and AL8 ×2.
* **Disc9:** AL3 ×1 at (6,8) (area-0 entrance tiles in area-7 ground); AL5 ×61; AL6 ×9; AL8 ×3.
* **AL2 is 0 everywhere.**
* "Authored" means the IDALL differs from the cell's background: the stock cell, or BLANK sea4f on Disc9. So
  Donor.txt free riders that were moved to a new position count as authored.

## Recorded claims this contradicts

1. **`ff9mapkit/ff9mapkit/world/extract.py:68-89`.** The `decode_id` docstring says area is "a coarse REGIONAL
   tag"; `encode_id` says "the cosmetic regional tag". Area has seven engine/script channels (A1/A2). Also
   contradicted:
   * `world/entrance.py:18` ("cosmetic `area=<case>`");
   * the `retarget_tiles` docstring, `world/mesh.py:1393-1398` ("only the trigger flag + cosmetic").
2. **`ff9mapkit/ff9mapkit/cli.py:9025`.** The world-retarget `--area` help says "a COSMETIC regional tag". The
   world-entrance `--no-tile-area` help at cli.py:9886-9888 says "the stamp is pure bookkeeping". Both are
   contradicted.
3. **Memory `project-ff9-world-locate-cell-tag-join`**: "cosmetic regional tag … Tile `--area` stamps are pure
   bookkeeping". Area is still not the dispatch key; that part stands.
4. **Consumption C4 "five places" and its wording "forced upper camera".**
   * The set is incomplete: it misses the camera place (ff9.cs:3117), the beach search (EMinigame.cs:726 and three
     callers, plus WORLD08) and the save-slot Location (UIManager.cs:587 → SharedDataBytesStorage.cs:482).
   * The direction is inverted: area 12 forces the perspective counter **down to 0, the default view**, and refuses
     the toggle **to** the high view. The counter value 4096 is the toggle-on state (WMScriptDirector.cs:139).
5. **`studies/overworld-topography/southern-ring/REVERT.md` §26.2.**
   * It says "Area choice is cosmetically free: WorldLocationText(area)'s only gameplay caller is the … debug
     PlayerWindow title". Main-menu and save-slot labels (MainMenuUI.cs:527, UIManager.cs:587) and the camera place
     contradict this. Area 14 happens to be place 0, so the ring's choice was camera-neutral.
   * Its "the horseshoe carry's 270 STOCK event verts" (also in commit e192f17c) is contradicted. The tiles are
     Cleyra's (C, lead 1).
6. **`world/worldpack.py:53`** comment: "65 overworld areas (0..64)". The engine table and `_AREA_ZONE` have 64
   entries (6-bit area, 0-63). `worldloc.mes` has 65 strings, the last one empty.
7. **The task brief's lead**: "camera place and encounter zone change from tile to tile" on Disc9. The zone does
   change (412 walkable zone-change pairs), but there are **0 place seams**: the place is constant per island. The
   "area 15" in the brief is the 4078 skip artifact.

## Proposed in-game probes (NOT run; harness memory `project-ff9-test-harness`)

1. **The area-12 lock and labels at (19,18).**
   * Setup: a Disc1 save with ScenarioCounter < 4990. Teleport (~ World tab) to about (1244, −1181), inside the
     bounding box x 1231-1256, z −1194..−1170. The readout should show area 12, topograph 41.
   * Press the perspective toggle and take a `game_snap`. Prediction: the toggle is refused and the HUD perspective
     stays off. Read the window title and the main-menu label; both should say "Vube Desert".
   * Step to (1210, −1181), area 14. The toggle should work and the label should change.
   * Cost: one short session, no deploy.
2. **The camera-place framing delta.**
   * On Disc9, stand on the area-40 island (cell (14,13), place 1) and on an area-0 island at a similar ground y.
     `game_snap` each with the same camera rotation.
   * Prediction: at y ≈ 4 the place-1 eye is about 4u farther and about 4.5u higher, the FOV is about 3.75° wider,
     and cameraCorrect is lower.
   * A true seam test (an on-foot snap with no easing) needs a bench with a deliberate area-40 stamp on part of an
     island. That is the AL2 calibration case, at a scratch id. This is the only probe that needs a deploy.
3. **A carried zone on Path D.**
   * Walk the Uaho carry, Disc9 (13,15), area 63, until 3 random battles fire. Log `nextMapNo`.
   * Prediction: every scene comes from zone 24's record slice (`worldpack.zone_slice(24)`), and none fires on
     surrounding area-0 sea.
   * This confirms "a verbatim carry imports the donor's encounter area" on the s74 namespace and the disc-1-table
     assumption.

## Open questions
* Whether area 12's forced default view visibly snaps or eases. The code has no easing on the place channel, but
  the upperCounter ramps at speed −128 per frame.
* Which kit verb ran the Cleyra carry onto (19,18).
* Whether `w_frameDisc` is 1 on the s74 namespace. That decides which encounter table Disc9 uses.
* What gates the beach search beyond bit 1042 (`Global.Byte[190]` case 25, `Map.Byte[35]`, a KEYON). Whether it is
  reachable at all off WORLD08.
