# Terrain malleability -- lane "forms": the per-block FORM SWITCH

Read-only study. Every number below comes from a script in this directory (rerun commands at the end). Engine
citations are `C:\gd\FFIX\Memoria\Assembly-CSharp\...` and are **stock Memoria** unless marked `[sNN]` (our
`memoria-patches/` stack; checked by grepping the patch hunks -- WMBlock.cs, WMBlockPrefab.cs, WMWorldPrefabMaker.cs,
WorldPlace.cs, NCalcUtility.cs, WMScriptDirector.cs are touched by NO patch; ff9.cs patches touch none of the
form-switch functions; WorldConfiguration.cs is touched only by s75's UseMist block).

Classes: **law** (source- or census-proven) / **measurement** (a number from a script here) / **hypothesis** /
**open** (needs an in-game test or a DLL experiment).

---

## 1. Mechanism

**F1 law -- one switch swaps walk, render and IDALL per block, atomically and exclusively.**
`WMBlock.ActiveWalkMeshes` returns `Form1WalkMeshes` when `Form==1`, `Form2WalkMeshes` when `Form==2`
(WMBlock.cs:10-20); every movement/height query goes through it (WMBlock.cs:155,164). The lists are exclusive: form 2
REPLACES form 1 in the raycast, never stacks. `LoadBlock` registers `ObjectForm1/TerrainForm1` to form 1 only,
`ObjectForm2/TerrainForm2` to form 2 only, `VolcanoCrater2/Lava2` to form 2 only, and every water/beach/river/falls
part to BOTH (WMWorld.cs:588-600, 638-656, 748-807; `RegisterBlockComponent` :812-858 feeds the SAME mesh to render
and walk). The per-triangle IDALL (event/area/topograph) comes from the active walk mesh's `tangent.x`
(WMBlock.cs:210), so the switch also swaps topograph (encounters/movement) and entrance tiles.
Block 219 (Water Shrine) has its own early-return branch: form 1 = Object/Terrain/Sea3/4/5, form 2 =
Object2/Terrain2/Sea3_2/4_2/5_2 + the WaterShrine effect prefab (render only) (WMWorld.cs:601-636).

**F2 law -- SetForm moves the walk mesh; only ApplyForm moves the render.** `SetForm` just stores `_form`, and is a
silent no-op unless `IsSwitchable` (WMBlock.cs:97-104). `ApplyForm` toggles `SetActive` on Form1/Form2Transforms
(:119-135). `mw_worldSetFormBit` calls `SetForm(2)` ONLY (ff9.cs:9210-9219). The render is applied when the block is
(re)loaded: `LoadBlock` ends in `ApplyForm` (WMWorld.cs:635, 809), and streamed-out blocks are rebuilt on re-entry
(:1312-1320).

**F3 law -- the form is decided once per world-scene load, BEFORE any block loads.** `WMScriptDirector.HonoAwake`
-> `w_frameSystemConstructor` (WMScriptDirector.cs:61) -> `w_worldSystemConstructor` (ff9.cs:3669) ->
`w_worldChangeBlockSet` (ff9.cs:8832). Blocks first load at `w_frameMainRoutine` frame `kframeEventStartLoop+1`
(ff9.cs:3700-3704), so the first `ApplyForm` already renders the decided form. Nothing about the form is saved: it is
a pure function of `ScenarioCounter` (= `gEventGlobal[0..1]`, ff9.cs:3652), `gEventGlobal[101]` and the mod's
`Environment.txt`, re-derived on every `WorldMap` scene load -- after a battle (BattleResultUI.cs:54), a field exit,
a world->world jump (WMScriptDirector.cs:225-228) and a save load. So it "persists" exactly as its inputs do.
Per-block, not global: 26 cells, each its own `_form` (default 1, WMBlock.cs:269). `ResetBlockForms`/`SetBlockForms`
are all-grid helpers (WMWorld.cs:1670-1694) used only by the debug paths below.

**F4 law -- there is no clean mid-visit switch in stock.** The only `.eb` route is `RunWorldCode(501, v)`
(0xC4, EventEngine.DoEventCode.cs:2529-2534 -> ff9.cs:4162-4190): `ResetBlockForms` (form 1 + ApplyForm on all),
`w_frameScenePtr = v`, `w_worldChangeBlockSet` (SetForm(2), no ApplyForm), then `SetDisc(1)`, which does nothing
when the disc is unchanged (WMWorld.cs:1702). Result: walk = form 2, render = form 1 on already-loaded blocks until
they stream out and back. Custom `Environment.txt` conditions are memoized for the visit (`_isEvaluated`,
WorldConfiguration.cs:634-653), so 501 would not even re-read a flag. **Measurement:** none of the 13 shipping world
dispatchers uses RunWorldCode 501/502 (`world_eb_form_writers.py`; calibrated: finds exactly the 18 known
RunWorldCode(26) writes and `Global.Bit[1608]`). The Keypad9 handler (WMScriptDirector.cs:365-371) has no caller;
`WMBeeMenu.SetBlockForms` (WMBeeMenu.cs:145,150) is the WorldMapDebug scene. **The clean refresh is a world reload:**
`WorldMap(<same id>)` (WMAPJUMP 0xB6, DoEventCode.cs:2458) -> mode 3 -> `Replace("WorldMap")`.

**F5 measurement -- the switch is NOT list-length-symmetric (answers walk-decode-claims.md:70/685).** Form 1 and form 2
walk lists differ in LENGTH at (13,12) and (14,12) on disc 1 (1 vs 2: form 1 has no Object), and the index-0 role
differs at (7,1), (8,1), (13,12), (14,12) (Terrain1 vs Object2; `label_forms.py`). The walk cache stores
(walkMeshIndex, triangleIndex) per block with no invalidation (WMBlock.cs:145-179) and
`WMPhysics.RaycastOnSpecifiedTriangle` indexes `triangles[triangleIndex*3]` unchecked (WMPhysics.cs:50-58); e.g. at
(13,12) a cached Terrain1 triangle (542 tris) reinterpreted against Object2 (36 tris) is out of range. Only a MID-VISIT
flip can reach it (F3: a load-time flip makes new WMBlock objects). **Hypothesis/open:** a 501 flip while standing on
one of those 4 cells throws every frame.

## 2. Triggers

**F6 law -- the trigger table is per PLACE, data-overridable with NO DLL.** `w_worldChangeBlockSet` (ff9.cs:9153-9208)
maps 9 `WorldPlace`s to 26 cells; each place's default condition is `UsePlaceAlternateForm`
(WorldConfiguration.cs:165-193): SouthGate_Gate disc1 & SC 2990..6989; Alexandria disc1 & SC>=8800; FireShrine and
WaterShrine disc1 & SC 10600..10699; Lindblum disc1 & SC>=5598; Cleyra disc1 & SC>=4990; BlackMageVillage disc1 &
SC>=6200; MognetCentral `gEventGlobal[101]&0x80`; ChocoboParadise `gEventGlobal[101]&0x40`. A mod-folder
`StreamingAssets/Data/World/Environment.txt` line `Place <WorldPlace> [Condition=<NCalc>]` REPLACES the default
(:168-169), parsed every world load (PatchAllWorldConfig, WMScriptDirector.cs:26 -> :93-121). NCalc can read
`GetEventGlobalByte(i)` (NCalcUtility.cs:125), `ScenarioCounter` (:272), `WorldDisc` (:307), `HasKeyItem` (:94) etc.;
`&` is UInt32 (Evaluant.Calculator/Domain/EvaluationVisitor.cs:179-181), so a kit flag F tests as
`(GetEventGlobalByte(F >> 3) & (1 << (F & 7))) != 0` (kit convention flags.py:501-503). Two effects follow the place
conditions for free: SandStorm = disc1 && !Cleyra (:208), WaterShrine splash = WaterShrine (:215-216).
**Check that can fail, passed:** the code's 26 cells == the IsSwitchable set in every disc-1 and disc-4 block prefab
== the IsSwitchable set of the 480 WMBlocks baked in the WorldMap scenes (level7 and level19), no cell driven by two
places (`label_forms.py`).

**F7 law -- the kit already emits this file** (`ff9mapkit world-environment`, world/environment.py:126-129
`[[place]]`) -- but two stacking traps: (a) conditions ACCUMULATE across mod folders (OR; parse order base -> lowest
-> highest priority, WorldConfiguration.cs:104-113, 412-421) and the kit never emits `Clear`; (b) Memoria's shipped
`StreamingAssets/Data/World/Environment.txt` header tells modders to write `Place Alexandria Clean`, but the parser only
accepts `Clear` (:400, :407) -- following the doc is a silent no-op. Also the kit validates any of the 64 place
names (environment.py:28-41), while only 9 have block forms. **Fixed after the study (defect 20):** the kit emits
`<key> Clear` before each keyed line (opt out: `stack = "combine"`), refuses a place without a form, and reports the
stacked lines for its keys plus any `Clean`.

**F8 measurement -- the world .eb writes the two flag-gated bits itself.** `Global.Bit[814]` (Chocobo's Paradise)
and `Global.Bit[815]` (Mognet Central) are B_LET-assigned 1 in entry 5 (tag 15/16) of 5 free-roam dispatchers
(world00/03/05/07/08) and read in entry 0 (`world_eb_form_writers.py`). Since forms are load-time (F3), the visible
change lands on the next world load. No world .eb touches the SC-keyed places.

## 3. Census

**F9 measurement -- 26 switchable cells, identical sets on both discs and both tiers.** Every one carries
TerrainForm2+ObjectForm2 (disc 4: 25 ObjectForm2), names exactly `Terrain2`/`Object2`/`VolcanoLava2`/`Sea3_2`..;
every form-2 slot resolves to a `worldmap/discN/0_2/...` mesh, every form-1 slot to `0_1` (0 mismatches,
`census_prefabs.py`). The runtime flags live on the SCENE WMBlocks, which are typetree-stripped; parsed with the
WMBlock typetree borrowed from p0data3's `worlddisc-incasethatitneedstocreateagain.prefab` under `check_read=True`,
480/480 rows, grid complete, Number row-major, 26 switchable, 205 sea, all Form lists serialized EMPTY (non-null --
why stock LoadBlock never news Form2Transforms) (`probe_scene_worlddisc.py`).

**F10 measurement -- what each switch actually does (disc 1; walk = 64x64 sky-cast samples per cell).**
Calibrated instrument (`diff_forms.py`: self-diff 0/4096; a synthetic +1.0 lift of x<16 caught with bbox x[0,16], dy 1.000).
Class from `mesh_channel_diff.py` (calibrated: self equal; a one-UV nudge flips uv/full but not geo).

| place (default) | cell | disc-1 class | walk chg /4096 | dy range | notes |
|---|---|---|---|---|---|
| SouthGate | (18,14) | RENDER-ONLY | 0 | - | Object UV swap (131 tris) |
| SouthGate | (17,12) | NO-OP | 0 | - | |
| Alexandria | (19,10) | GEO | 3 | 0 | 1 terrain tri + Object UV |
| Alexandria | (19,11) | GEO | 28 | -0.11..-0.05 | |
| Alexandria | (20,10) | GEO | 161 | -2.98..-0.19 | Object 232->180 tris (castle) |
| Alexandria | (20,11) | GEO | 9 | +1.95 | |
| FireShrine | (7,1) | GEO | 160 | 0 | Object2 ADDED (59), VolcanoCrater REMOVED, topo 59->49 x156 |
| FireShrine | (8,1) | GEO | 60 | +1.95 | Object2 ADDED (22), crater removed |
| FireShrine | (14,15) | RENDER-ONLY | 0 | - | Object UV; cell = Lindblum Dragon's Gate (29u) |
| Lindblum | (13,16) | RENDER-ONLY | 0 | - | |
| Lindblum | (13,17) | RENDER-ONLY | 178 | 0 | IDALL changes only (no topo, same event count) |
| Lindblum | (14,16) | GEO | 124 | -4.45..+1.95 | |
| Lindblum | (14,17) | GEO | 63 | -2.96..+3.24 | |
| Cleyra | (13,12) | GEO | 405 | -1.16..+5.07 | Object2 ADDED; ENTRANCE REMOVED (96 -> 0 event samples) |
| Cleyra | (14,12) | GEO | 599 | -0.29..+5.13 | Object2 ADDED; ENTRANCE REMOVED (95 -> 0) |
| BlackMageVillage | (14,6) (21,10) (22,14) | NO-OP x3 | 0 | - | the whole place is a no-op on disc 1 |
| WaterShrine | (3,9) | GEO | 1239 | -4.95..+1.66 | terrain 22->157, object 22->124, water sheets swapped, ENTRANCE ADDED (0 -> 257) |
| WaterShrine | (9,1) | NO-OP | 0 | - | |
| MognetCentral | (16,1) | GEO | 16 | -0.64..-0.09 | Object 2->44; entrance 12 -> 9 samples |
| MognetCentral | (13,4) (14,5) | NO-OP | 0 | - | |
| ChocoboParadise | (0,0) | GEO | 6 | -1.14..-0.07 | Object 5->17 |
| ChocoboParadise | (16,14) (9,17) | NO-OP | 0 | - | Chocobo's Forest (40u) / Lagoon (18u) cells |

Tally disc 1: 9 NO-OP, 4 RENDER-ONLY, 13 GEO (disc 4: 8/2/16). Place names are the stock comments plus the nearest
engine navipos landmark to the changed region (`ff9mapkit.world.locate.nearest_landmark`, distance shown in
form_table.json) -- confidence high for Water Shrine (7u), Mognet (1u), Cleyra (13u), Fire Shrine (28u), Alexandria,
Lindblum; medium for (0,0) (no landmark within 395u); the BMV and (9,1)/(13,4)/(14,5) assignments cannot be
checked visually because the switch changes nothing there. So the form switch is the stock mechanism that makes
Cleyra un-enterable and the Water Shrine enterable at the tile (IDALL event bits) level.

**F11 measurement -- disc 4's form 2 is mostly a STALE copy of disc 1's.** For the 7 disc-gated places, disc-4
TerrainForm2 is full-record identical to DISC 1's form 2 on 15/20 cells while disc-4 TerrainForm1 differs
(`disc4_form2_provenance.py`; cross-disc: TerrainForm1 differs on 23/26 cells). Forcing a disc-gated place on disc 4
would revert disc-4 terrain to disc-1-era geometry, e.g. (17,12) 1040/4096 and (14,16) 1395/4096 walk samples. The
two flag-gated places are consistent on disc 4.

**F12 measurement -- 38 orphan 0_2 meshes.** 94 (disc 1) / 93 (disc 4) meshes live under `0_2`; prefabs reference
56/55; the 38 orphans are all water/beach parts on switchable cells; 31 (disc 1) are identical to their 0_1 twin, 7
DIFFER, e.g. (19,11) river 69 vs 66 tris (42 shared; first recorded as 17 vs 66 through the D4-17 bug), falls, riverjoint, (0,0) sea4 (`orphan_02.py`). The only runtime-reachable
`0_2` reference is the dead baker (WMWorldPrefabMaker.cs:36); the Unity port draws form-1 water in both forms.

## 4. Override interaction

**F13 law -- s34 already addresses form-2 parts by name; zero new engine code needed for the 26 cells.** The override
key is `WorldMap/Disc{tag}/0_1/r{y}/Block[x][y] {transform.name}` (WMWorld.cs:823-825 [s34, tag from s74]) and
`copy.name = transform.name` (:815) is the baked child name, which F9 measured as `Terrain2`/`Object2`/
`VolcanoLava2`/`Sea3_2`/`Sea4_2`/`Sea5_2`. So `FF9_Data/WorldMap/Disc1/0_1/r{y}/Block[x][y] Terrain2.ff9mesh`
replaces the form-2 terrain (render + walk), and the kit's `override_relpath(..., part="Terrain2")` (world/mesh.py:229-235)
already spells it. **Hypothesis until played** (no in-game test has loaded a `*2.ff9mesh`).

**F14 law -- corollary trap: every kit `Terrain`/`Object` override on a switchable cell is FORM-1-ONLY.** When the
place condition flips, the stock form-2 mesh returns and the edit vanishes (render and walk). Today: 0 of 1291 live
disc-1/4 overrides sit on a switchable cell; 1 Path D (tag 9) override does, (14,12) Terrain (`live_override_overlap.py`):
safe in default BLANK mode (IsSwitchable=false, WorldDiscSpike.cs:194-198 [s71/s75]); in CLONE mode the cell copies
IsSwitchable=true (:187-193) and Cleyra's SC>=4990 condition would swap it to stock Terrain2 (hypothesis). No kit
lint knows the switchable set. **Fixed after the study (defect 19):** `world/forms.py` holds the set; every writer
warns, and `world-forms` checks a mod folder or the whole stack.

**F15 law -- a non-switchable cell cannot be made switchable from data.** `SetForm` checks the SCENE WMBlock's flag
(WMBlock.cs:99), and `LoadBlock` registers form-2 components only from `prefab.TerrainForm2/ObjectForm2` (WMWorld.cs:597-600).
Both are C# fields; WorldDiscSpike shows the runtime write is trivial (`b.IsSwitchable = src.IsSwitchable`,
WorldDiscSpike.cs:191 [s75]). **Minimal patch (one engine patch, about 50 lines, no rebake):**
1. WMWorld.Initialize, after `InitialBlocks` (:124): for each cell with a loose `Terrain2.ff9mesh`
   (`WorldMeshOverride.Exists`), set `IsSwitchable = true` -- it must happen before HonoAwake's `w_worldChangeBlockSet`.
2. LoadBlock: when `!prefab.TerrainForm2` and that override exists, call
   `RegisterBlockComponent(block, prefab.TerrainForm1, false, true)` under the name `Terrain2` (add an optional name
   parameter at :812/:815), and carry `ObjectForm1` (+ volcano parts) into form 2 too, otherwise the switch deletes the
   cell's stock object.
3. ff9.w_worldChangeBlockSet: after the stock places, for each cell with a `Block[x][y] Form.txt` NCalc sidecar that
   evaluates true, call `mw_worldSetFormBit(x, y)`.
Must NOT add serialized fields to WMBlock: its scene instances are typetree-stripped (F9), the same layout trap the
s34 note records for WMWorld (hypothesis, strong precedent).
**Built after the study (P1, engine patch s92):** steps 1-3 as sketched, with the sidecar named `Block[x][y] Form.txt`
(one NCalc line, evaluated like an Environment.txt condition); the arm runs at the end of `WMWorld.Initialize`, which
precedes `w_worldChangeBlockSet` and every block load; `RegisterBlockComponent` gained an optional child name. No
serialized field was added. Proven in game by round 6 (`ingame/RESULTS.md` section 21, 12/12).

**Story buildings (engine patch s93, `world-forms --building2`).** s92 read an `Object2` only where the cell has a
stock Object; s93 also registers a bare cell's `Object2` (form 2 only, render only) and makes a bare kit `Object`
form 1 only beside it. `object2_census.py` measured what removing a stock building leaves: on all 59 disc-1 cells with
one, nothing else answers under 90% of its footprint, so the kit fills the hole (closed holes only). Proven in game
by round 7 (`ingame/RESULTS.md` section 22, 15/15).

## 5. Verdict

Story-driven terrain change (bridge appears, forest burns, lake drains on a flag) is **viable, and mostly built
already**. The engine has an atomic per-block walk + render + IDALL swap, decided at world load from save state.
* **Tier 0 -- no DLL (stock Memoria):** retime or force the 9 stock places onto any kit flag with
  `world-environment [[place]] condition=...`. Stock art only: drain the Water Shrine lake, ruin Alexandria, close
  Cleyra, at fixed cells.
* **Tier 1 -- the shipped custom engine, no new patch:** custom form-2 geometry at the 26 cells via
  `Block[x][y] Terrain2/Object2.ff9mesh` (F13). Black Mage Village is a fully FREE 3-cell switch on disc 1 (all 3
  cells NO-OP): repoint its condition and stock play cannot tell (keep `WorldDisc == 1` in the condition -- F11).
* **Tier 2 -- one engine patch (F15):** any cell, any count, own per-cell condition.
* **Never needed:** a prefab rebake.
* **Mid-visit changes** need a world reload (`WorldMap(<same id>)`, or a field/battle round trip). A live in-place
  flip would need ApplyForm + walk-cache invalidation (F4/F5) -- not recommended.

**Smallest proof rungs (registered predictions):**
* **F0 (no DLL):** `Environment.txt` = `Place WaterShrine [Condition=WorldDisc == 1 && (GetEventGlobalByte(1089) & 1) != 0]`
  (flag 8712). Flag off -> debug-menu "Dump block" on (3,9) reports `Form=1`. Set the flag, reload the world -> `Form=2`,
  `Terrain2` active with 157 tris (form 1: 22), `Object2` 124 tris (22), walk list `[Object2, Terrain2, Sea3_2,
  Sea4_2, Sea5_2]`, terrain y min -5.07 (drained basin), entrance-tile IDALL present at world x 215-233,
  z -617..-599 (257/4096 samples, topograph 59), and the WaterShrine splash effect on. Falsifier: Form stays 1 ->
  the Environment.txt path is not read (folder/priority).
* **F1 (s34, the free BMV switch):** deploy `Block[22][14] Terrain2.ff9mesh` = stock (22,14) terrain with a seam-safe
  flattened plateau (radius <= 24u about the cell centre, world (1440,-928), stock y 22.69, topograph 49, 0 entrance
  tiles in the cell) + `Place BlackMageVillage [Condition=WorldDisc == 1 && <flag>]`. Predict: Memoria.log
  `[WorldMeshOverride] loaded 'WorldMap/Disc1/0_1/r14/Block[22][14] Terrain2'` in BOTH flag states (form-2 parts are
  built whatever the form, WMWorld.cs:599-600); harness `world_y` at the plateau = plateau height (+-0.15) with the
  flag on, the stock slope with it off. Log line but no height change -> the condition/IsSwitchable path; no log line
  -> the transform-name key hypothesis (F13) is false.

## Contradictions with recorded knowledge
* `ff9mapkit/ff9mapkit/world/extract.py:11` says "`0_2` is a far LOD". It is the FORM-2 (alternate) mesh set:
  WMWorldPrefabMaker.cs:35-36,119-138 loads `0_2` only into Terrain2/Object2/VolcanoCrater2/VolcanoLava2 (+ Sea3_2/4_2/5_2
  at (3,9)), sets IsSwitchable iff one exists, and F9 found 0 slot->directory mismatches over 960 prefabs. Same naming
  in `studies/overworld-topography/README.md:1222` and `mesh_parts_census.py:161` ("0_2 LOD") -- those two do
  identify the (3,9) water switch correctly.
* `studies/overworld-topography/README.md:1235` says s34 overrides on (3,9) "can reach **only** Terrain/Object/Sea3/4/5".
  They also reach Terrain2/Object2/Sea3_2/4_2/5_2 (registered through the same RegisterBlockComponent, WMWorld.cs:597-600,
  628-633). README.md:1223-1224 "registers only Object/Terrain (f1+f2)" -- form 1 and form 2 are DIFFERENT meshes
  (terrain 22 vs 157 tris), not one part in both lists.
* `studies/path-d-new-world/walk-decode-claims.md:685` frames `mw_worldSetFormBit` as firing "mid-session"; in stock it
  runs at world load before blocks exist (F3) -- mid-session only through the unused RunWorldCode 501. Its open
  "list-length parity" question is answered: unequal in shipping data (F5).
* memory `project-ff9-overworld-worlds.md:95` says `world-environment` needs a RELAUNCH; the file is re-parsed on
  every world load (WMScriptDirector.cs:26), so re-entering the overworld is enough (the kit's own docstring already says so).

## Rerun (from this directory, in order; all read-only on the install)
```
py census_prefabs.py          # -> out/prefab_census.json        (F9; ~1 min)
py probe_scene_worlddisc.py   # -> out/scene_worlddisc.json      (F9 scene tier)
py probe_worlddisc_backup.py  #    the WMBlock-tier backup prefab (typetree donor)
py probe_prefab.py 3 9 1      #    one prefab dump (calibration case)
py diff_forms.py              # -> out/form_diff.json            (F5, F10 walk; ~3 min)
py mesh_channel_diff.py       # -> out/mesh_channel_diff.json    (F10 classes, F11 cross-disc)
py label_forms.py             # -> out/form_table.json           (F6 check, F10 table, F5 parity)
py disc4_form2_provenance.py  # -> out/disc4_form2_provenance.json (F11)
py orphan_02.py               # -> out/orphan_02.json            (F12)
py live_override_overlap.py   # -> out/live_override_overlap.json (F14)
py world_eb_form_writers.py   #    (F4, F8)
py rung_site.py               #    (rung F0/F1 numbers)
py render_form_map.py         # -> out/form_map_disc{1,4}.png
```
