# Lane d9: the Disc9 (Path D world 9013) battle walk and the Disc9 bind receipts

This lane covers README section 7.1, rank 1(b) and 1(c). The work is designed and verified offline; nothing has been run in-game yet.

- **(b)** On world 9013, walk the Uaho carry, Disc9 cell (13,15) (area 63), until 3 random battles fire. Record each
  battle's scene id. The README predicts that every scene comes from zone 24's slice.
- **(c)** Archive `Memoria.log` and replay the bind oracle to get the first Disc9 receipts. The prediction comes from
  BLANK mode.

**Files.** All of these are in `studies/terrain-malleability/ingame/`. The two outputs in `out/` are gitignored.

| file | what it does |
|---|---|
| `d9_prep.py` | Offline, read-only. Builds homes, controls, encounter tables, the rate model and the bind prediction, and writes them to `out/d9_prep.json` and `out/d9_grid.npz`. |
| `d9_session.py` | The scenario. Its preflight refuses to load, before any launch, unless the deploy in §3 is live. |
| `d9_dryrun.py` | Runs the scenario against the harness FakeGame over the real Disc9 mesh. It also has negative controls and exercises `d9_post.py` from start to finish. |
| `d9_post.py` | Offline scoring after the run: exact heights, scene against the class of ground at the fire point, the rate model, recovery receipts, and the Disc9 bind receipts in both directions. |

Engine cites are `file:line` under `C:\gd\FFIX\Memoria\Assembly-CSharp`, at the patched working tree. s34, s60, s70,
s74, s75 and s83 are built and deployed (`memoria-patches/README.md`).

---

## 1. Blocker resolved: getting into 9013 needs one scratch deploy (bench 30950)

| question | answer | evidence |
|---|---|---|
| Is the Disc9 world content still deployed? | **Yes.** `FF9CustomMap-world` still registers `WorldScene 9013 WORLD13`. `EVT_WORLD_WORLD13.eb.bytes` is present in all 7 locales. `FF9_Data/WorldMap/Disc9/0_1` holds 541 files over 65 cells, all 65 of which bind (oracle, `d9_prep`). The carry (13,15) has `Donor.txt` = `0,0`, plus a 406-tri `Terrain.ff9mesh` and a 369-tri `Sea4.ff9mesh`. | live listing; `out/d9_prep.json` → `bind` |
| Does any live field act as a door to 9013? | **No.** I counted the bytes of all 1,085 live `.eb.bytes` files in the 6 FolderNames folders for `WorldMap(9013)` (`b6 00 35 23`): there are 0 hits. Literal WorldMap targets in the live `us` scripts are only 9000-9012. | byte scan (§6) |
| Can the harness reach 9013 without a door? | **No.** The agent's map verbs are `warp`, `worldwarp` and `teleport` (`HarnessAgent.cs:652-674`). The only way to choose a `wldMapNo` is `Ff9mkDebugMenu.ForceWorldState`/`ArmWorldReload` (`Ff9mkDebugMenu.cs:1552-1606`). That is an IMGUI button, and the harness cannot press IMGUI buttons. | source |
| Is bench 30950 still available? | **Yes, as an id.** No live folder registers FieldScene, WorldScene, BattleScene or MessageFile 30950. There is no stale `tools/scroll_out/revert_deploy_30950.py` in the main repo. | grep (§3.0) |
| Does the old bench still build with today's kit? | **Yes. Verified offline today** in the session scratchpad. `ff9mapkit lint` reports OK. `build` emits `FieldScene 30950 11 PATHDGATE PATHDGATE 30950` and `MessageFile 30950 MES_DWIX_30950`. `inject_worldjump.py` reports 7/7 OK as a dry run and 7/7 patched as a scratch write (`slot 4, 1236 -> 1380 B (+144)`; the template grew from August's 1192 B). A re-run is 7/7 SKIP, which is idempotent. `lint-eb` on the patched `us` file gives exactly the template baseline, `1 error(s), 0 warning(s)` (entry0/tag1). | §6 |

**Cheapest route.** Deploy the owner-proven rung-6 bench verbatim into `FF9CustomMap-lab`, then walk onto its pad.
- The spliced tread region runs fade, then `arrive_writes(425,-479)`, then `D8:2 = 35`, then `WorldMap(9013)`
  (`inject_worldjump.range_body`).
- He lands on the V-shore lawn, Disc9 (6,7).
- The scenario teleports from there. Teleport works on 9013 because `WMScriptDirector.cs:43` sets `WrapWorld = true` on
  every world load, and `Ff9mkDebugMenu.cs:1813-1874` loads the destination block first.

Using `inject_worldjump.py --landing` to land directly on the carry was rejected. Its y seed would have to be re-measured,
and the proven landing is cheaper than re-proving a new one.

## 2. What the run measures, and why each number is the right one

**Route, per loop:**
1. `newgame`, then `warp(30950)`.
2. `calibrate_axes(hazards=[pad zone])`.
3. `walk_to(0,-1700, halt_on_transition)`, then `wait_world`. This lands him on world 9013.
4. Teleport to a home on the carry and repeat bursts. Each burst teleports home, holds "up" for about 2u, and settles.
   The hold is sized from the measured speed and capped at 3u.
5. When a battle starts, record `battle.scene`.
6. Recover to the title.

**Teleport adds no encounter distance.** Distance is the world actor's per-tick 3D delta × 256
(`EventEngine.ProcessEvents.cs:241-249`). It is counted only while `_moveKey = w_frameEncountEnable` (`:72-74`,
`:289-297`). That flag is set only while he moves on foot (`ff9.cs:5535-5538`).

**Why "teleport home before every burst".** The grass ring around the carry's rock is about 9u wide. The best disc of
clearance is 4.06u on topo 0 and 4.93u on topo 37. A burst can therefore never leave its (area, topograph) class. This is
the `world_probe(home=...)` idiom, and it is checked offline (§6).

**Homes** (`d9_prep`; off the 4u lattice; the clearance is to anything that is not that class, the cell edge included):

| home | world (x, z) | class | clearance | ground | expected `world_y` | event tiles | control: no divert |
|---|---|---|---|---|---|---|---|
| `topo0` | (883.112, −1000.343) | area 63, topo 0 | 4.06u | 2.8387 | 2.8387 | ≥ 11.9u | sea4f y 0.0, topo 57 |
| `topo37` | (873.842, −983.403) | area 63, topo 37 | 4.93u | 7.5453 | 6.3734 (canopy sink) | ≥ 8.9u | sea4f y 0.0, topo 57 |
| `landing` (control) | (428.362, −476.593) | area 0, topo 0, Disc9 (6,7) | 8.37u | 3.2000 | 3.2000 | none in cell | sea4f y 0.0, topo 57 |

**Encounter chain** (all numbers from the live bytes):
1. Area 63 maps to **zone 24** through `w_worldAreaZone` (`ff9.cs:9229-9232`). Zone 24's slice is records 250-253
   (`ff9.cs:9234-9256`).
2. Those rows are identical in the live `FF9CustomMap-world` disc-1 table, stock disc 1 and stock disc 4. So the open
   `w_frameDisc` question cannot change the answer. Here `w_frameDisc` is 1 anyway, because `GetDisc()` returns 1 below
   scenario 11090 (`ff9.cs:3653`, `WorldConfiguration.cs:246-252`).
3. Each zone-24 row repeats one scene in all 4 slots:

   | record | topograph | fog | scene | monster |
   |---|---|---|---|---|
   | 250 | 0 | 0 | 778 | Adamantoise |
   | 251 | 0 | 1 | 777 | Adamantoise |
   | 252 | 37 | 0 | 780 | Worm Hydra |
   | 253 | 37 | 1 | 779 | Worm Hydra |

4. **Fog is 0 on Path D.** `UseMist()` returns false when `WorldDiscSpike.Engaged && SuppressMist`
   (`WorldConfiguration.cs:235`). `Engaged` is latched for ids 9013-9099 (`WorldDiscSpike.cs:40-41`, `:67-70`), and
   `SuppressMist` defaults to true (`:87`). Fog is part of the lookup key (`ff9.cs:9248`). So the scene alone shows
   whether s75's mist suppression engaged.
5. **Scene choice.** `SelectScene` (`EventEngine.cs:190-220`) picks a slot with `d[pattern&3]`
   (`EventEngine.Static.cs:120-126`). A repeat of the last scene re-rolls once (`EventEngine.ProcessEvents.cs:508-509`).
6. **Rate.** WORLD13's own sysvar-207 ladder, decoded from the deployed `us` `.eb`, sets ENCRATE **16** for zone 24 and
   12 for zone 0. Sysvar 207 is the zone under the actor (`ff9.cs:4260-4264`); ENCRATE is applied at
   `EventEngine.DoEventCode.cs:992-997`.
7. **Encounter check** (`EventEngine.ProcessEvents.cs:496-518`; `InitEncount`, `EventEngine.Initialize.cs:8-17`). The
   first check comes at 9.375u (initial −1440 fixed), then one every 3.75u (960 fixed). The base rises by 16 per check,
   and a battle fires when `random8() < base>>3`.
   - Median 54.4u, p90 95.6u, p99 129.4u.
   - **Certain by 485.6u**, at check 128.
   - On the landing lawn (zone 0): median 61.9u, certain by 646.9u.
8. **The Ragtime Mouse cannot interfere.** WORLD13 reads sysvar 205, which leads to `Battle 941/942`. That needs
   `w_frameEventBattleProb`, whose only writer is `RunWorldCode(26)` (`ff9.cs:3929-3930`). The deployed WORLD13 never
   calls it, so the value stays 0, `x % 1 == 0`, and the battle never fires (`ff9.cs:4254-4255`).
9. **The location title does not gate encounters at scenario 0.** `w_naviTitle` is −1 except at scenarios
   2400/5990/9605/9890 (`ff9.cs:8837-8852`).
10. **Scene instrument.** `battle.scene` = `battleMapIndex`, set from the world's `nextMapNo` when the battle starts
    (`ff9.cs:9332-9333`; published at `HarnessAgent.cs:1815`). It was already **calibrated in-game**: session 1's
    scene 174 matched zone 5, topo 41, fog 1, record 57 (`RESULTS.md` §1).

**The carry is the donor's terrain, verbatim.** Disc9 (13,15) `Terrain.ff9mesh` equals stock (0,0) Terrain in the same
local frame: 406/406 tris, 228/228 vertices, and the same IDALL multiset. So a height reading **cannot** tell "override
bound" from "donor Terrain free-riding". Part (c)'s log is the only receipt for that. The height **can** tell "the
divert armed" (land, y ≈ 2.84) from "no divert" (SeaBlockPrefab: sea at y 0, topo 57, not walkable).

**Recovery.** A level-1 party cannot survive Adamantoise or Worm Hydra.
- **Rung 1.** The game's own soft reset from BattleHUD.
  - The combo's held form is read through `GetKey` (`UIKeyTrigger.cs:55-61`), which admits BattleHUD (`:91-93`).
  - The handler has a battle branch (`:361-395`): `FF9BMenu_EnableMenu(false)`, `btl_seq = 1`, `Replace("Title")`.
  - It logs `[Soft Reset]` (`:361`).
- **Rung 2.** Let the party fall, then Confirm the Game Over screen (`GameOverUI.cs:67-90` → `Replace("Title")`).
- **Rung 3.** `restore_baseline()`.

## 3. The deploy (the orchestrator performs it; it touches nothing but `FF9CustomMap-lab`)

### 3.0 Read-only checks first. Abort on any surprise.

```sh
G="C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX"
tasklist | grep -i FF9.exe                                                   # must print nothing
grep -hoE "^(FieldScene|WorldScene|BattleScene|MessageFile) 30950\b" "$G"/*/DictionaryPatch.txt   # must print NOTHING
grep -h "^WorldScene 9013" "$G/FF9CustomMap-world/DictionaryPatch.txt"     # must print: WorldScene 9013 WORLD13
ls "$G/FF9CustomMap-lab" "$G/FF9CustomMap-lab.ff9lock" 2>&1                 # must not exist (else another lab is live)
ls C:/gd/Dream-World-IX/tools/scroll_out/revert_deploy_30950.py 2>&1        # must not exist (deploy_field's prelude would run it)
git -C C:/gd/Dream-World-IX branch --show-current                           # the bench toml + splice script are on master
```

### 3.1 Memoria.ini

Use the same routine as sessions 4-7. Back up the file to
`C:\gd\Dream-World-IX\backups\Memoria.ini.pre-terrain-lab-d9.<stamp>` and record its sha256. Then put the lab folder
first:

```
FolderNames = "FF9CustomMap-lab", "FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo", "FF9CustomMap-schema", "FF9CustomMap-msgs"
```

### 3.2 Deploy the bench, then the splice

Run these from `C:\gd\Dream-World-IX`. The splice must follow every `deploy_field.py`.

```sh
py tools/deploy_field.py studies/path-d-new-world/rung6/fieldside/pathdgate.field.toml --id 30950 --name PATHDGATE --mod-folder FF9CustomMap-lab
py studies/path-d-new-world/rung6/fieldside/inject_worldjump.py --mod-folder "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-lab" --dry-run
py studies/path-d-new-world/rung6/fieldside/inject_worldjump.py --mod-folder "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-lab"
```

Expected results:

- **`deploy_field.py`**
  - `FF9CustomMap-lab/DictionaryPatch.txt` = `MessageFile 30950 MES_DWIX_30950` + `FieldScene 30950 11 PATHDGATE PATHDGATE 30950`.
  - It also writes `tools/scroll_out/revert_deploy_30950.py`, backups under `backups/`, and a `FF9CustomMap-lab.ff9lock`
    file beside `Memoria.ini`.
- **`inject_worldjump.py`**
  - 7 × `OK slot 4, 1236 -> 1380 B (+144), Range body 107 B, all funcs decode clean`.
  - Backups go to `C:\gd\Dream-World-IX\backups\rung6-pathdgate\<UTC stamp>\`.

`--name PATHDGATE` is mandatory. Without it the deploy writes `EVT_TEST30950`, and the splice then reports MISSING.

### 3.3 Verify, still offline

```sh
py studies/terrain-malleability/ingame/d9_session.py --preflight      # exit 0, "problems": []
cd ff9mapkit && py -m ff9mapkit lint-eb "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-lab/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/us/EVT_PATHDGATE.eb.bytes"
#   -> exactly "1 error(s), 0 warning(s)" (entry0/tag1 empty function body = the blank template's own quirk)
```

The preflight checks four things:
- the lab is in FolderNames;
- `FieldScene 30950` is served only by the lab, as PATHDGATE;
- no WorldScene/BattleScene 30950 exists, and MessageFile 30950 appears only in the lab;
- `WorldScene 9013` is registered, and all 7 locales carry `WorldMap(9013)`.

The scenario runs the same preflight at import, before `play.py` launches anything.

### 3.4 Teardown, after the run and after `d9_post.py`

```sh
py tools/scroll_out/revert_deploy_30950.py            # un-registers + removes the bench from the lab
del C:\gd\Dream-World-IX\tools\scroll_out\revert_deploy_30950.py   # else the NEXT 30950 deploy's prelude runs a revert against a deleted folder
# restore Memoria.ini byte-exact from the 3.1 backup (sha256 must match), then:
rmdir /s /q "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-lab"
del "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-lab.ff9lock"
```

## 4. Run commands

```sh
py studies/terrain-malleability/ingame/d9_prep.py                       # re-read the live Disc9 right before (it is a shared canvas)
py studies/terrain-malleability/ingame/d9_dryrun.py                     # optional, ~2 min, must print DRY RUN CLEAN
py tools/play.py studies/terrain-malleability/ingame/d9_session.py --label terrain-d9
py studies/terrain-malleability/ingame/d9_post.py .harness-runs/<stamp>-terrain-d9
py studies/terrain-malleability/consumption/bind_oracle.py --log .harness-runs/<stamp>-terrain-d9/Memoria.log   # optional cross-check (rewrites the gitignored consumption/out/bind_oracle.json)
```

**Loops.**
- The defaults are `topo0`, `topo0`, `topo37`, followed by the `landing` control.
- `D9_LOOPS=...` replaces the carry loops. `D9_CONTROL=0` drops the control.
- Each loop is one launch-free cycle of newgame → bench → 9013 → walk → battle → title, about 1.5-2.5 min. The whole run
  is about 6-10 min in one launch.
- Each loop is capped at 505.6u of walking (certain-by plus 20u) and 600 s of wall clock.

## 5. Registered predictions

These were written before any run. The numbers come from `out/d9_prep.json`.

| id | prediction | judged by | control / calibration |
|---|---|---|---|
| R0 | The pad lands him on world **9013**, within 3u of **(425, −479)**. | `state.world.id` (= `wldMapNo`), position | Owner-proven route (rung 6). |
| H | After every burst, `world_y` equals the live mesh's ground within ±0.15: **2.84** at the topo-0 home, **7.545 − 1.171875 = 6.373** at the topo-37 home, **3.20** on the landing lawn. This is land on a BLANK Path D cell, so the s34/s74 divert armed. | Exact sky query in `d9_post`. The in-run check allows nearest-sample slack (≤ 0.13u at these homes). | **No-divert control:** the same x/z would be sea4f at y 0, topo 57. The canopy sink is proven in-game to 0.0015u (`RESULTS.md` §2). |
| B1 | README 1(b): every carry battle scene is in zone 24's slice **{777, 778, 779, 780}**. | `battle.scene` at battle start | Instrument calibrated in session 1 (scene 174). |
| B2 | A battle that fires on **topo 0 is scene 778** (Adamantoise) and one on **topo 37 is 780** (Worm Hydra): the fog-0 rows. **777/779 would falsify s75's mist suppression** on Path D. | the fire point's exact class (the state ring's last on-map sample) | `--fog 1` negative control turns B2 red (§6). |
| RATE | Each battle fires within **485.6u** of on-foot travel. Expected median about 54u, p90 about 96u. Walking past the cap with no battle falsifies the encounter path, because a chord sum is a lower bound of the engine's 3D path. | the walked chord sum | Model from WORLD13's live ladder (ENCRATE 16). |
| C | Control loop, landing lawn, area 0 → zone 0, topo 0, fog 0: the scene is in **{5, 165, 206, 230}** (each 25%) and never 777-780. This separates "the area under him picks the zone" from "Path D has one fixed table". | `battle.scene` | `--zone0` negative control turns B1/B2 red. |
| REC | Each recovery reaches the title by **rung 1**, the soft reset from BattleHUD. `Memoria.log` carries one `[Soft Reset]` line per such recovery. | the session's recovery record plus a log count | Rung 2 (Game Over → Confirm) is the fallback. |
| (c) | The run's `Memoria.log` matches the bind prediction in both directions and has no other errors (details below). | `d9_post.bind_receipts` | Calibrated today on the live 13:50 disc-1 log (details below). |

**(c) in detail.** The run's `Memoria.log` should show:
- per 9013 load, exactly the oracle's ordered Disc9 bind lists: **238 lines over 65 cells**;
- **(13,15) = [Terrain, Sea4]** and (6,7) = [Object, Terrain, Sea4];
- a modal repetition count equal to the number of world loads (4 with the control loop);
- **0 Disc1/Disc4** override lines, because no disc-1/4 world loads in this run and s74 keeps Path D in its own namespace;
- **0** `failed` or `bad Donor.txt` lines.

**(c) calibration.** On the live 13:50 disc-1 log, 82/82 predicted cells matched with 1 repetition, 254/254 lines. The
one mismatch is (21,1), served by the since-removed lab: that is the positive control for the logged→predicted
direction. Dropping (0,16)'s lines from a copy flags it: the negative control for the predicted→logged direction.

**What each outcome means.**
- **B1+B2 pass:** a verbatim carry imports its donor's encounter area on the s74 namespace. The disc-1 table and fog 0
  are what Path D runs.
- **B1 pass, B2 fail with 777/779:** the encounter area carries, but s75's `SuppressMist` did not reach `w_frameFog`.
- **B1 fail with a zone-0 scene:** the area under him is not 63. Suspect the free-riding (0,0) Object, or a live edit
  since the prep. Re-run `d9_prep` and `d9_post`.
- **No battle past the cap on both carry and control:** the encounter path is off. Suspect the F4 NoRandomEncounter
  booster or a co-op `SuppressEncounters` first. The state does not publish either.

## 6. Offline verification already done (no game, no install writes)

- **Bench build and splice.** `ff9mapkit build` of `pathdgate.field.toml` into the session scratchpad, then
  `inject_worldjump.py` against that copy: dry run 7/7 OK, write 7/7 patched, re-run 7/7 SKIP. `lint-eb` on the patched
  `us` file: 1 error, which equals the template baseline. The toml lints OK.
- **Door census.** None of the 1,085 live scripts contains `b6 00 35 23`. Literal WorldMap targets in the live `us`
  scripts are only 9000-9012.
- **Dry run** (`d9_dryrun.py`, FakeGame with the real Disc9 raster as ground and the engine's encounter rule):
  - Seeds 9013, 77 and 5: all 4 loops clean. Battles came at 24.9-94.2u.
  - 0 bursts left their home class. Maximum burst 2.10u (≤ 3.0).
  - The preflight refuses a deploy without the splice and passes the staged one.
  - The soft reset from BattleHUD reaches the title.
  - `d9_post` was run end to end on a synthetic log: 952 = 238 × 4 lines, `(c)` passed.
- **Negative controls, all red where they should be:**
  - `--fog 1`: B2 fails, B1 still passes.
  - `--no-sink`: H fails on topo 37, with deviation 1.1719 against slack ≤ 0.13.
  - `--zone0`: B1 and B2 fail.
- **Bind-receipt instrument calibration.** See the (c) calibration paragraph in §5.

## 7. Risks

- **Shared canvas.** Disc9 holds other sessions' clusters. Re-run `d9_prep.py` right before the run. Its asserts refuse
  if the carry's class or clearance has changed.
- **Event tiles.** The carry has 18 u² of event tiles (IDALL 32512, event 1, between the rock and the forest). AL8 found
  their cell tags inert against every live dispatcher. The homes are 8.9-11.9u away and bursts are 3u at most, so they
  are never stepped on. The rung-6 exit tiles at Disc9 (6,8) are 74u south of the landing. If he did step on them, they
  would now warp to the lab's 30950, not black-screen.
- **Soft reset from BattleHUD is unproven in-game.** It is source-read, and FakeGame models it from research H9. The
  fallback is the Game Over → Confirm path (the party is level 1, and the ATB runs at the top-level menu). Rung 3 is
  `restore_baseline`.
- **No booster flag is published.** If F4 NoRandomEncounter or co-op `SuppressEncounters` is on, no battle can fire. The
  RATE check then reports the falsifier, and the control loop tells "carry" apart from "everywhere".
- **Nearest-sample height in-run.** The registered ±0.15 is scored exactly by `d9_post`. The in-run check adds the local
  step slack (≤ 0.13u at these homes).
- **Teleport during a battle transition.** A teleport could land in the frames between the encounter roll and
  `ui_state` leaving WorldHUD. It is harmless: the scene is chosen at the roll, and a home and its bursts share one class
  by construction. The scenario also waits out `fading`.
- **The lab leaves debris unless it is torn down.** The revert script in `tools/scroll_out` must be deleted with the
  folder (§3.4), or the next 30950 deploy runs a stale revert against a deleted folder.
