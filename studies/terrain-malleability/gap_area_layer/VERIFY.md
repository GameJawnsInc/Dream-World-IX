# Adversarial verification: lane `gap_area_layer`

This pass was read-only on the install, the Memoria clone, the memory store and tracked files. New files are the
`verify_*.py` scripts in this directory and this file. Engine cites were re-opened at the patched tree
`C:\gd\FFIX\Memoria\Assembly-CSharp`. STOCK and PATCH were checked with `git diff HEAD` and `git show HEAD:` on each
cited file.

## Reruns

Every lane script was re-run. All ten outputs are **byte-identical** to the lane's originals (stdout and json):
`calibrate`, `engine_consumers`, `eb_consumers`, `stock_atlas`, `camera_place_effect`, `live_audit`, `lead_1918`,
`writer_audit`, `area_table` and `area_lint`.

* `calibrate.py` was also re-run with a **fresh** mesh cache: C1 and C2 PASS, 5376/5376.
* `stock_atlas.py` was rebuilt from a fresh cache. The npz is identical, so the results do not depend on the cached
  meshes.
* Every calibration block passes.

## Verdicts

| id | verdict | note |
|---|---|---|
| GA1 | **corrected** | The reader set is right. Every cite is exact. The STOCK/PATCH split is right: the label chain `UIManager.cs:586-587` → `FF9.mapNameStr` → `SharedDataBytesStorage.cs:482` → `SaveLoadUI.cs:360` is STOCK at HEAD. `SharedDataRawStorage.SaveSlotPreview` is a no-op, so the Bytes storage is the live one. An independent grep found no further reader: no NCalc world parameter exposes area, and `ff9.cs:2233/2246` are the cell-tag packer. **The history claim is overstated.** The camera-place reader was already recorded in `ff9mapkit/docs/OVERWORLD_ENGINE.md:821` and `world/interior.py:1381-1385`, so not "every earlier census" missed it. The save-slot write and the beach search were genuinely missed. |
| GA2 | **confirmed** | Table re-parsed independently: place 0 = 0-26 and 46-50; place 1 = 40-45; place 2 = 27-39 and 51-63. Element and posstat values were re-read, and the `:3141` blend is set only by `w_cameraChange` (`:5976/:5978/:5995`). Walkable↔walkable seams are 0 on both discs under 4 definitions: the lane's, any part with a walkable topograph, diagonals, and a 2-sample reach. A synthetic stamp fires (40 pairs). The law also holds for chocobos (see A2). Implication nit: 3.75° is the FOV change only at y ≤ −3.9 (0.1% of ground). See A4. |
| GA3 | **confirmed** | `:2771` sets the force flag. `:3123-3133` drives `upperCounter` down by 128 per frame to 0, then clears. `upper = rsin(counter/4)` blends toward the fly posstat 7 (15.6u distance, 29.3u height). Counter 4096 is the toggle-ON state (`WMScriptDirector.cs:139`, `ff9.cs:2622`). `:3199` refuses the toggle. All STOCK and reachable: `w_cameraUpdate` runs from the 20 FPS loop at `:3813`. Nits: the reset at `:2604` applies only on field→world entry when not loading a save. The ring runs at scenario 4100 < 4990, so the lock is live there. |
| GA4 | **corrected** | Raw-byte upper bound over all 13 dispatchers × 7 languages: sysvar 192 = 1 and sysvar 207 = 9 in every language, equal to the decoded reads. 0 exceptions were swallowed. GLOB 856-876 is written only in WORLD08: 21 writes, plus C# reads only. The gates at @6188-6262 are as stated. WORLD13's ladder is identical. **Error:** "the others 14 or 16" is wrong for zone 11, which is **12**. |
| GA5 | **corrected** | The geography numbers reproduce: 64/64 areas; 41/43 single landmasses; boundary statistics; 591 of 822 MISS in (16-17,14-15). **The disc-4 change is not all relabel.** Of the 7,987 u² area-0 land drop, about 7.1k is a true relabel on land present on both discs (0→7 6,133; 0→22 487; 0→14 469, in blocks (13-15,14-18) and (18-19,9-10)). 1,858 u² is disc-1 area-0 land that does not exist on disc 4 (blocks (6-7,4-5)). Nuance on "continental": 7,510 land↔land place contacts exist in stock, almost all area-0 topograph-58 rims against place-1/2 land. Those rims are not walkable, so the walkable statement stands. |
| GA6 | **confirmed** | Re-scored at the fog the ring actually runs with. The ring is scenario 4100, so `UseMist()` is true and the fog key is **1** (WorldConfiguration.cs:243). The lane scored fog 0, but the result is unchanged because every relevant zone's records are fog-symmetric (verify_fog). Area 14 = 147,102 u² walkable, 0 live. The quay clusters are IDALL 16384 (area 0, topograph 0), and zone 0 has topograph-0 records. Grimhorn is topograph 17, a hole. Sandreach Beach1 is an override with area 49 (27 tris, 108 u² ground, topograph 34). This depends on s60, which is DEPLOYED per the patch README. |
| GA7 | **confirmed** | **Can-fail control added (verify_1918):** the same 45 tris at their stock Cleyra cells (27-28, 23-24, e1) DO match object-0 tags in 6 stock dispatchers. The live cells (38-39, 36-37) match none, so "inert" is a real negative. IDALL 19620 exists only in disc-1 0_1 terrain of (13,11), (13,12), (14,11) and (14,12), across every container. The widest horseshoe rect (5-7,15-16) has 0 such tris. Its areas are {0, 48, 50, 45}, not only {48, 0}. Arithmetic nit: the 270 verts are 45 tris × 3 verts × 2 discs. |
| GA8 | **confirmed** | The Disc9 numbers reproduce. Areas {0,6,7,40,48,50,57,58,62,63} map to 7 zones and 3 places. The ENCRATE ladder in live WORLD13 is identical (zone 23 = 32). sqrt(32/12) = 1.633 matches the accumulating hazard (`_encountBase += encratio`) and memory `project-ff9-overworld-worlds`. Path D is mist-free under s75, so fog 0 is correct. The disc-1 and disc-4 record sets are identical, so the open `w_frameDisc` question cannot flip any hole/record verdict; it only changes which alternate scene band is used. |
| GA9 | **confirmed** | 0x0FEE decodes to event 0, area 15, topograph 59, flags 2. Disc1 Object "area 15" is 1620 tris and Disc9 Terrain "area 15" is 1064, and all of them are 4078. `WMPhysics.cs:16-20` skips 4078/4088/2040 unless `IgnoreExceptions` is set. Three sites set it, and none reads area: the camera eye raycast (`ff9.cs:2945`, which reads topograph 49 only), and two "is there ground here" probes (`:3966` in `w_frameSetParameter`, `:4800` in `w_movementChrFixBug`), which can treat a 4078 tri as present ground. |
| GA10 | **corrected** | The semantics are right: default `set_tile_area=True` (entrance.py:763, cli.py:5449), stamp at entrance.py:1027, and help texts at cli.py:9886-9888 and :9025. The counts reproduce: 151 cases; 3 lock; 9 weather; 12+50 place changes; 49 beach; 70 topograph-0 live; 89 wrap. **Cite:** `mesh.py:1417` is the area pass-through (`d["area"] if area is None else area`). The `& 0x3F` mask is at `world/extract.py:90`. The "62 change place" count assumes a place-0 host. |
| GA11 | **confirmed** | Every needle was re-located and read: interior.py:1381-1389 strip, :707/:711 canopy verbatim, transplant.py:402 retag keeps area, coastmorph.py:6056/6066 host area. Stock donor areas reproduce. |
| GA12 | **confirmed** | The candidate sets are identical against stock disc 1, live disc 1 (record sets equal) and disc 4. The stock fallback was confirmed at HEAD (`return w_frameBattleScenePtr[i + useAlternate - 1]`, the slice's last record). Scope caveat, which the claim states: candidacy holds only for the 7 safe-road topographs. Place-1/2 continents' native topographs (19/20/45/46, 7/27) have records in those zones. |
| GA13 | **confirmed** | Calibration and live counts reproduce exactly (1973 u², 64 pairs; Disc1/4 {AL1 1, AL3 8, AL4 1, AL5 8, AL8 2}; Disc9 {AL3 1, AL5 61, AL6 9, AL8 3}). Weaknesses to fix before promoting it: see A5. |
| GA14 | **corrected** | `w_cameraPosstatNow` is recomputed every frame with no blend (`:3157-3158`). FOV (`:2676`) and the eye **x/z** offset (`:2688-2689`, then `num18/num20` at `:2937-2939` → `:3067-3068`) therefore snap. The eye **height** does not snap. `num19 = pos.y + eyeOffset.y` (also floored by `cameraCorrect` + ground at `:3001`) is approached gradually by the `num8` vertical follow, which has a ±1u dead band and an `nsp`-scaled step (`:3007-3071`). So on foot, distance and FOV jump in one frame while height and the correct floor ease. |
| GA15 | **confirmed** | `w_worldAreaZone` and `w_cameraArea2Place` each have 64 entries, re-parsed independently. `_AREA_ZONE` has 64 entries and equals the engine table. The comments at worldpack.py:53, :43, :66 and :191 say 0..64. |

## Additional findings

**A1. The fog key is 1 on the Southern Ring.** `UseMist()` returns `scenario < 5990 || > 11090`, and the ring's
scenario is 4100. The lane's `encounter_live_u2`, AL5 and the writer_audit topograph-0 statuses are all keyed at
fog 0. Today this is harmless: every zone's record topographs are identical at fog 0 and fog 1 in both disc tables
(verify_fog). The kit lint should still key on the namespace's real fog:
* fog 1 for disc 1 below scenario 5990, and for disc 4;
* fog 0 for Path D under s75 `SuppressMist`.

**A2. Chocobos cannot cross a stock place seam either** (verify_choco_seams). Masks were parsed from `ff9.cs:1467+`.
* Under the raw limit masks, Light-Blue, Red, Deep-Blue and Gold-ground chocobos see 77-133 type_cam-1 place pairs.
  All of them are water (topographs 55/56) next to place-1 ground (topographs 19/20/46/49).
* Every one of those steps is refused by the `flg_gake=1` water↔ground rule (`ff9.cs:5702-5715`). That leaves 0.
* So GA2's law extends to every ground vehicle.
* Airships (type_cam 3) do cross places in stock, but posstats 4, 5 and 6 differ only in cameraCorrect (0.78u),
  which is eased.

**A3. Stock has 7,510 land↔land place contacts** (verify_place_seams, definition A). They are almost all area-0,
topograph-58 continental rims against place-1/2 ground. Any writer that retypes a topograph-58 rim to a walkable
topograph mints an AL2 seam. AL2 should therefore run after topograph-only writers too (coastnav, rimretile,
orphangate), not only after area writers.

**A4. Proposed experiment 2 predicts the wrong FOV.** At ground y ≈ 4 the height blend is t ≈ 0.45, so the
place-0→1 pers change is 30 × 0.55 = 16.5, which is **2.1°** at the default FieldOfView of 44. The live install has
`[Worldmap] FieldOfView = 58` (Memoria.ini:96), which scales that to about **2.7°**. The predicted 3.75° is wrong in
both cases. Distance (+4.3u) and height (+4.7u) are consistent with the model. The height delta will appear
gradually (GA14), so a single `game_snap` taken right after a seam crossing under-reads it.

**A5. Lint weaknesses.**
* The stock-Uaho negative control cannot trigger AL1, AL2 or AL4 by construction. It has no area 9/12/13, and the
  stock mosaic has no seams. A stronger negative control would be a stock entrance cell whose event tiles share the
  ground's area.
* AL3 and AL8 test tags against the union of all 14 live dispatchers. That is conservative for "inert", meaning it
  can under-report. For Disc9 only WORLD13's tags are reachable.

**A6. The lane's attribution of the (19,18) tiles stands.** The "horseshoe" in REVERT §13/§26 is the Daguerreo
horseshoe ensemble, donor (5-6,15-16). GROUND-FAMILY-DECODE records a separate Cleyra-region junction/dunes carry
("the donor junction IS the Cleyra region"). That carry is the likely source of the Cleyra tiles and of Grimhorn's
original area-12 ground. Not proven: which run did it remains open.

## Verification scripts (rerun from the repo root with `py`)

* `verify_place_seams.py`: GA2/GA5. An independent place-LUT parse, 4 seam definitions, a can-fail stamp, and the
  disc-4 relabel vs geometry split.
* `verify_choco_seams.py`: GA2/GA14. Chocobo limit masks parsed from source, with the `flg_gake` water↔ground
  refusal applied.
* `verify_eb_area.py`: GA4. The raw-byte sysvar bound across 7 languages, the swallowed-exception count, and every
  writer of GLOB 856-876.
* `verify_fog.py`: GA6/GA8/GA12/GA13. Encounter liveness re-scored at fog 0 and fog 1; zone record sets per disc.
* `verify_1918.py`: GA7. The stock-position control for the tag join, a global IDALL-19620 search, and the
  horseshoe 5-7 rect.
