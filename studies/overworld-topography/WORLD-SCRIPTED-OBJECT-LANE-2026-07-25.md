# The world SCRIPTED-OBJECT lane — decorative statics via `3DModel` + `.eb` (source trace, 2026-07-25)

> **Provenance:** offline source/byte trace (Memoria decompiled source at `C:\gd\FFIX\Memoria`, the live
> install, the kit, and the custom-vehicle study) produced during the Lantern Quay marker round.
> **★ IN-GAME PROVEN 2026-07-28** — scene-ladder rung 0 deployed a decorative static through this exact
> lane (stock model 313 + idle 5106, index 0, WORLD11 entry 16, the ferry ship moored off the Lantern
> Quay; owner-confirmed): both laws held on the first deploy, the world tick stayed alive, and a STOCK
> model needed no relaunch (only a minted `3DModel` id registers at launch). Build:
> `scene-ladder/rung0_quay_ship.py`.
> The quay marker itself chose the OTHER lane (baked per-block `Object.ff9mesh` carry; see
> `southern-ring/`): two files, no relaunch, no `.eb`. **This document is the reference for when a world
> object must be a real model/actor** — a visible ferry boat at a quay, an animated lantern flame, any
> set-dressing that the Object-mesh substrate can't express. The boat (rung 2, `studies/custom-vehicle/`)
> is the in-game-proven cousin, but it is a VEHICLE (index 8, needs s51); the decorative shape below is
> lighter and, unlike the vehicle, **stock-Memoria-clean if the two laws hold**.

## THE TWO LAWS (the whole verdict, up front)

1. **THE INDEX RULE (replaces s51):** never `SetObjectIndex(1..10)` on a decorative. Indices 3–7/8 enter
   the hardcoded `Find("…(Clone)")` NRE blocks (`ff9.cs:4445`, `:4504`); 1/2 and 9/10 hijack the engine's
   human/plane singletons (`ff9.cs:4537-4565`). **Index 0 is fully inert** — its `cache == 10` row skips
   all ground/shadow logic (`ff9.cs:5432`), so authored Y is kept verbatim and multiple decoratives can
   share index 0 harmlessly.
2. **THE ANIMATION RULE (replaces s49):** the object must be *running* a real, registered, loadable clip —
   `SetStandAnimation(<donor idle>)` in tag 0 **and** a per-frame `RunAnimation(<same>)` tag-1 loop
   (stock WORLD11 entry 11's exact shape). A truly animation-free static NREs **every frame** in
   `SmoothFrameUpdater_World` on any install with `WorldFPS < 0` or `WorldTPS < WorldFPS` (this install:
   `Memoria.ini` `WorldFPS = -1` → the hazard is LIVE), and that NRE **silently kills the whole world
   script tick**. s49 stays recommended as the belt-and-braces (a clip that fails to LOAD lands in the
   same NRE, and nothing offline can prove the load).

---

The full trace follows, verbatim from the research agent.

## 1. The `3DModel` DictionaryPatch directive

**Engine parser** — `C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Configuration\DataPatchers.cs:591-614`:

```
else if (String.Equals(entry[0], "3DModel"))          // :591
    if (FF9BattleDB.GEO == null) continue;            // :602
    ... parse every token 1..n-2 as an int ...         // :604-611
    FF9BattleDB.GEO[ID[idindex]] = entry[entry.Length - 1];   // :613
```

* What it registers: **one or more integer GEO ids → one GEO NAME string**, injected into
  `FF9BattleDB.GEO`, which is a **two-way** id↔name dict. It is *not* a path alias — the path is derived
  from the name later. Sibling directive `3DModelAnimation` (`DataPatchers.cs:615-638`) does the same for
  `FF9DBAll.AnimationDB` + `FF9BattleDB.Animation`.
* **RELAUNCH required.** `DataPatchers.Initialize()` (`DataPatchers.cs:107-129`) is called exactly once
  from `AssetManager.DelayedInitialization()` (`Global\Asset\AssetManager.cs:116`), guarded by
  `_isInitialized` (`:109-110`). It walks `AssetManager.FolderLowToHigh` and `File.ReadAllLines` each
  folder's `DictionaryPatch.txt` (`:114-119`) — low→high, so a higher-priority mod folder's line wins.
  The `~` hot-reload does **not** re-run it.
* Name → path → assets. `ModelFactory.GetRenameModelPath` (`Global\Model\ModelFactory.cs:26-34`) turns the
  name into `Models/{typeInt}/{geoId}/{geoId}`, where `typeInt` comes from the name's GROUP token
  (`GetModelType`, `ModelFactory.cs:403`); `GEO_WEP*` goes to `BattleMap/BattleModel/...` instead
  (`:26-30`). `CreateModel` (`:50-67`) probes the **mod folder on disc FIRST**
  (`AssetManager.SearchAssetOnDisc(renameModelPath + ".fbx")` → `ModelImporter.CreateCustomModelFromFbx`),
  falling back to the bundled asset (`:71-74`).
* So the assets that must sit alongside the line: `…/Models/<typeInt>/<id>/<id>.fbx` plus the PNG textures
  in the same folder. Two name-derived behaviours matter for a WORLD model:
  * `ModelFactory.cs:171` — `AnimationFactory.AddAnimToGameObject(model, modelNameId, (isBattle && !…_B1_)
    || modelNameId.Contains("_W0_"))`. The `_W0_` token in the NAME switches on the auto-anim folder
    sweep. Keep `_W0_` in a world mint's name.
  * `ModelFactory.cs:118-119` assigns the `WorldMap/Actor` shader by
    `modelNameId.Contains("GEO_SUB_W0")` — but that block is inside the **bundled-asset else-branch**. For
    a loose FBX the shader comes from `ModelImporter.GetShaderPathFromType(…, gMode)`
    (`Memoria\Assets\3DModel\ModelImporter.cs:403-419`), which returns `"WorldMap/Actor"` when
    `mode == 3`. Equivalent result, different code path — worth knowing if a mint ever renders wrong.

**Kit side (who emits the line)**

| emitter | file:line |
|---|---|
| canonical directive string | `ff9mapkit\ff9mapkit\models\mint.py:83` (`"directive": f"3DModel {new_id} {name}"`), also `:140` for the `fbx=` form |
| one-shot deploy + append to `DictionaryPatch.txt` | `ff9mapkit\ff9mapkit\models\mint.py:170-183` |
| build path (`[[mint]]` blocks → `mint_lines`) | `ff9mapkit\ff9mapkit\build.py:6883-6920` (esp. `:6920 mint_lines.append(man["directive"])`), returned as `"mint_lines"` at `build.py:8222-8226` |
| deploy/revert ownership (drops a live `3DModel` line only on exact-id match) | `ff9mapkit\ff9mapkit\dictpatch.py:24-33` (`mint_model_ids`), `:47-105`, `:107-140` |
| foreign-line-loss guard text | `ff9mapkit\ff9mapkit\deploy.py:63-71` |
| docs | `ff9mapkit\docs\CUSTOM_MODELS.md:100-110`; relaunch table `ff9mapkit\docs\SUMMONS.md:147` |

## 2. The mint / deploy path (the crimson boat, rung 2)

**Script:** `studies\custom-vehicle\mint_boat.py`
* `:21-23` — `MINT_ID = 6321`, `MINT_NAME = "GEO_SUB_W0_DWX"`, `SOURCE = "GEO_SUB_W0_008"` (Blue Narciss,
  real id 321).
* `:25-29` — `mod = <game>/FF9CustomMap-world`; `deploy_mint(SOURCE, MINT_ID, mod, MINT_NAME)`.
* `:31-63` — post-pass: hue-rotates every PNG in the deployed mint folder toward crimson (in-place, so the
  folder holds recoloured donor textures).
* `:7-8` docstring states the write target and **"RELAUNCH required once (3DModel registers at launch)"**.

**Kit function:** `ff9mapkit\ff9mapkit\models\mint.py:170-183 deploy_mint()`
* `:175` destination = `Path(mod_folder) / *export._RES / *export.model_dir_parts(type_int, id)`.
  * `_RES = ("StreamingAssets", "Assets", "Resources")` — `ff9mapkit\ff9mapkit\models\export.py:16`.
  * `model_dir_parts` — `export.py:19-25`: `("Models", str(type_int), str(geo_id))` (weapons →
    `BattleMap/BattleModel/...`).
* `:176` `export_mint(...)` writes `<id>.fbx` (ASCII FBX, `mint.py:100`) + every donor texture as
  `<stem>.png` (`mint.py:101-105`).
* `:177-181` appends the `3DModel` line to `<mod>/DictionaryPatch.txt`, **idempotent** (`if
  man["directive"] not in lines`), atomic write.

**Actual on-disk write-set (verified in the live install):**
```
FF9CustomMap-world/StreamingAssets/assets/resources/Models/5/6321/6321.fbx
FF9CustomMap-world/StreamingAssets/assets/resources/Models/5/6321/321_0.png .. 321_3.png
FF9CustomMap-world/DictionaryPatch.txt   ->  "3DModel 6321 GEO_SUB_W0_DWX"
```

**Id band.** `MINT_BAND_START = 6000` — `mint.py:31` ("first id clear of every real GEO id (real max =
5511)"); enforced at `mint.py:70-72` and `:131-132`; `SetModel` takes a 2-byte id so the ceiling is 65535
(`mint.py:20-21`). 6321 = 6000 + the donor's id 321 (mnemonic, not required).

**Class = WORLD.** `type_int` derives from the GROUP token: `mint.py:35-43` → `extract._TYPE_INT =
{'acc':1,'main':2,'mon':3,'npc':4,'sub':5,'wep':6}` (`ff9mapkit\ff9mapkit\models\extract.py:33`).
`GEO_SUB_W0_DWX` → group `sub` → **type 5**, i.e. `Models/5/`, the same folder family as every stock
`GEO_SUB_W0_*` overworld actor (310 = `GEO_SUB_W0_001`, 321 = `GEO_SUB_W0_008`, …). It is a
**world-class** model, not field/battle. Its FORM token `W0` also drives the `_W0_` auto-anim/shader
behaviour (§1).

**Animations are NOT part of the mint.** `mint.py:9-16` and `:75-80`: clips resolve from the **ANIM
NAME's** tokens (`AnimationFactory.AddAnimWithAnimatioName`, `Global\AnimationFactory.cs:54-66` →
`Animations/GEO_{tok1}_{tok2}_{tok3}/{animName}` → `GetRenameAnimationPath`), *independent of the model's
own id*. So `SetStandAnimation(5145)` / `SetWalkAnimation(5143)` on a 6321 model still load out of folder
321. `build_boat_world11.py:2-4` names this the "animation-redirect law".

**Relaunch:** yes, once per new id. Cited in `mint.py:172`, `mint_boat.py:8`,
`build_boat_world11.py:54-56`.

## 3. How a world `.eb` places a model at a coordinate

### 3a. What the boat script does

`studies\custom-vehicle\build_boat_world11.py`

| piece | lines |
|---|---|
| entry/uid constants (`BOAT_UID = 15`, `ANCHOR_UID = 14`, `SNAP_TAG = 60`) | `:51-53` |
| `MODEL_ID = 6321` + the s51 warning | `:57-63` |
| fixed-point helper `fp(v) = (v*256) & 0xFFFFFFFF` | `:90-92` |
| **tag-0 Init body** (`BOAT_INIT`) | `:95-124` |
| tag-1 per-frame board/dismount loop | `:128-160` |
| anchor's shore-snap func (tag 60) | `:162-167` |
| entry blob builder `[etype, fc] + (tag,fpos)* + code`, 4-byte pad | `:170-182` |
| assemble + round-trip assert | `:185-189` |
| entry append / in-place replace | `:198-216` (`E.append_entry(out, BOAT_UID, build_entry(etype, [(0, boat_init), (1, boat_loop)]))` at `:206`) |
| `Main_Init` gains `InitObject(15, 0)` before the final `RET()` | `:218-230` |
| etype byte read from the real WORLD03 boat entry 6 (= **2**) | `:240-249` |
| all-7-language patch-in-memory-then-write, with backups | `:256-281` |

The Init sequence as authored (`:96-123`):
```
SetObjectIndex(8)                      # binds the actor to the Blue Narciss vehicle index
SetModel(6321, 100)                    # arg2 = eye/head height
SetObjectFlags(5)                      # 1 show model | 4 collision-with-NPC
SetObjectLogicalSize(0, 80, 90)
op_DF(100)                             # 0xDF SetObjectOvalRatio (world-only collision stretch)
SetObjectSize(15, 106, 106, 106)
SetStandAnimation(5145) / SetWalkAnimation(5143) / op_35(5143)   # op_35 = 0x35 ARUN = SetRunAnimation
…mode-7 load arm (AttachObject/DefinePlayerCharacter)…
MoveInstantXZY(const4(fp(x)), const(Y), const4(fp(z)))
TurnInstant(const(face))
RET()
```

### 3b. Engine semantics of each op (cited)

| op | Memoria | notes |
|---|---|---|
| `InitObject` 0x09 | `EventEngine.DoEventCode.cs:120-140` | `new Actor(sid, uid, sizeOfActor)`; **uid defaults to the slot index when arg2 == 0** (`Global\Objects\Obj.cs:19-21`); in `gMode == 3` it immediately calls `WMWorld.addWMActorOnly(actor)` (`:134-135`) |
| `SetModel` 0x2F | `DoEventCode.cs:1084-1132` | world branch `:1127-1131`: `CreateModel(GEO.GetValue(po.model), …, WorldSmoothTexture)` then `addGameObjectToWMActor` |
| (deferred model creation) | `EventEngine.updateModelsToBeAdded.cs:19-45`, `:70-76` | same thing for objects inited before the scene was ready; `addWMActorOnly` + `addGameObjectToWMActor` + `wmActor.SetPosition(pos[0..2])` |
| `SetObjectIndex` 0x3B | `DoEventCode.cs:1286-1290` | `this.gExec.index = (Byte)getv1()` — **this is the index into every world per-actor table** (see §4/§5) |
| `SetObjectFlags` 0x93 | `DoEventCode.cs:2071-2084`, bit doc at **`:2073`** | `1 show model · 2 collide-with-player · 4 collide-with-NPC · 8 disable talk · 16 can't walk through · 32 don't hide all` |
| `MoveInstantXZY` 0xA1 | `DoEventCode.cs:2179-2186`, applied `:2242`, `SetActorPosition` `:3483-3507` | reader: `destX=getv2(); destZ=-getv2(); destY=getv2();` then `SetActorPosition(po, destX, destZ, destY)` where the signature is `(po, x, y, z)`. **Net mapping: arg1→pos[0] (X), arg2→pos[1] (Y, SIGN-FLIPPED by the reader), arg3→pos[2] (Z).** World branch `:3492-3506`: `wmActor.SetPosition(...)`, and the `w_movementChrVerifyValidCastPosition` clamp only runs for `index 3..7` (`:3497`) — a non-chocobo index is placed **verbatim, unclamped**. |
| `TurnInstant` 0x36 | `DoEventCode.cs:1191-1220`, world branch `:1214-1219` | writes `wmActor.rot.y`; byte units 0=south, 64=west, 128=north, 192=east (`:1196`) |
| `Wait` 0x22 (`op_22`) | `DoEventCode.cs:655` | "wait N frames" — the per-frame yield in every loop |
| `SetObjectOvalRatio` 0xDF (`op_DF`) | `DoEventCode.cs:2966` | *"stretching factor for the object's collisions (seems to only work on world maps)"* — consumed at `EventCollision.cs:206-209` |

Coordinate scale: world literals are fixed-point ×256 (`build_boat_world11.py:90-92`; corroborated by
`ff9mapkit\ff9mapkit\save.py:311-314` — world player X at `gEventGlobal` 64, Z at 69, `WORLD_POS_FP =
256`, 3-byte coords).

### 3c. The stock precedent for a purely decorative static — **WORLD11 entry 11**

`studies\custom-vehicle\recon_world11.txt:1897-1920` (disasm of stock `EVT_WORLD_WORLD11` entry 11, model
313 = `GEO_SUB_W0_021`):

```
----- ENTRY 11 tag=0 -----                     ----- ENTRY 11 tag=1 -----
SetObjectIndex(15)                             L0:
SetModel(313, 100)                             SetAnimationFlags(1, 1)
SetObjectFlags(5)                              SetAnimationInOut(0, 0)
SetObjectLogicalSize(0, 60, 80)                RunAnimation(5106)
op_DF(100)                                     op_22(1)
SetObjectSize(11, 100, 100, 100)               JMP(L0)
SetStandAnimation(5106)
SetWalkAnimation(5106)
op_35(5106)
MoveInstantXZY({const4(282324)}, 58765, {const4(4294761467)})
TurnInstant(184)
RET()
```
Armed from `Main_Init` under a ScenarioCounter gate (`recon_world11.txt:130-156`: `InitObject(11,0)`
inside the `2800 <= UInt16[0] < 2900` branch; the unconditional ones are 8,9,10,5,14,6).

### 3d. MINIMAL sequence for a decorative, non-interactive, non-controlled static

**Entry:** `etype = 2`, exactly two funcs: tag 0 and tag 1. (The slot-table census in §6 shows every stock
world *object* entry is etype 2, code entries etype 0.)

tag 0 (Init):
```
SetObjectIndex(<free, inert index — see §4/§5; 0 is the most inert>)
SetModel(<geoId>, <eyeHeight>)
SetObjectFlags(1)                # show model ONLY — no collide-with-player/NPC bits
SetObjectSize(<uid>, s, s, s)    # optional; 100 = 1:1
SetStandAnimation(<donor idle id>)   # REQUIRED for stock safety, see §4b
MoveInstantXZY({const4(x*256)}, {const(y)}, {const4(z*256)})
TurnInstant({const(face)})
RET()
```
tag 1 (loop) — **required in practice, not optional**:
```
L0:
SetAnimationFlags(1, 1)
SetAnimationInOut(0, 0)
RunAnimation(<same donor idle id>)
op_22(1)
JMP(L0)
```
Why the loop is not optional: `RunAnimation` → `ExecAnim` (`EventEngine.cs:1397-1407`) is the **only**
thing that ever assigns `actor.anim` (`EventEngine.cs:1401`, `EventEngine.ProcessAnime.cs:197`; the
`ProcessAnime` idle/walk/run assignments at `:55/:63/:71` are gated on `animFlag & afExec`, which only
`ExecAnim` sets). Leave `anim == 0` and you land in the s49 NRE (§4b). A single `RunAnimation` in tag 0
would also seed `anim`, but the stock shape re-issues it each frame and is the proven pattern.
`SetObjectFlags`/`SetModel`/`MoveInstantXZY`/`TurnInstant` must be in **tag 0** — tag 0 runs once at
`InitObject`, tag 1 is the per-frame body.

Also arm it: add `InitObject(<slot>, 0)` to `Main_Init` (entry 0, tag 0) — the pattern
`build_boat_world11.py:218-230` implements with a text round-trip assertion.

**Kit API for world `.eb` authoring:** there is **no** world object-placement helper.
`ff9mapkit\ff9mapkit\world\entrance.py` only ever uses `add_function` / `replace_function_body` / switch
repointing on entries 0 and 1 (`entrance.py:721-723`, `:416-422`); the loader/paths it does own are
`load_all_dispatchers` / `load_world_dispatchers` (`entrance.py:86`, `:122`) and `_WORLD_EB_SUBDIR =
"StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world"` (`entrance.py:39`). The
generic entry primitives are in `ff9mapkit\ff9mapkit\eb\edit.py` — `append_entry` `:96-130`,
`grow_entry_table` `:70-93`, `insert_entry_at` `:133-168`, `add_function` `:171-205`,
`replace_function_body` `:208-241`. Assembler: `ff9mapkit\ff9mapkit\eb\cmdasm.py`
(`assemble_block`/`disassemble_block`). Deploy law (all 7 languages, **never clone US into `jp/`**):
`ff9mapkit\docs\OVERWORLD_ENGINE.md:344-350`.

## 4. Risks — grounded

### 4a. s51 / the world CLONE-NAME law — **does NOT apply to a non-vehicle decorative object**

Patch: `memoria-patches\s51-world-constructor-name-guards.patch` (whole file, 80 lines). Rationale entry:
`memoria-patches\README.md:69`.

Hazard site, live (patched) source `C:\gd\FFIX\Memoria\Assembly-CSharp\Global\ff9\ff9.cs:4436-4535`:
* chocobo block, gated **`posObj.index >= 3 && posObj.index <= 7`** — `ff9.cs:4445`, the
  `Find("GEO_SUB_W0_003(Clone)/mesh0")` / `"308(Clone)/mesh0"` chain at `:4476-4490`, unguarded
  `component.material` derefs at `:4493-4501` (stock).
* Blue-Narciss block, gated **`posObj.index == 8`** — `ff9.cs:4504`, `Find("GEO_SUB_W0_008(Clone)")` at
  `:4516`, `"321(Clone)"` fallback `:4519`, and the stock unguarded `transform4.localPosition` deref
  (patch lines `74-76` of s51 show the removed stock code).

These are the **only two** hardcoded `transform.Find("<name>(Clone)")` sites in the entire world/event
code — verified by sweeping `Global\ff9\ff9.cs`, `Global\WM\`, `Global\Event\`: hits are
`ff9.cs:4476,4479,4481,4484,4486,4489,4516,4519` plus two harmless `block.transform.Find("Object")` in
`WMWorld.cs:631,671`.

**Verdict:** the NRE is reachable **only** when the actor's `index` is 3–7 or 8. A decorative object that
never calls `SetObjectIndex(3..8)` never enters either block. → **s51 is NOT required for this lane.**
(The boat needed it purely because `build_boat_world11.py:96` sets `SetObjectIndex(8)`.)

Two adjacent index rules you must respect anyway (stock, unpatched):
* `ff9.w_movementChrConstructor` (`ff9.cs:4537-4565`) assigns global pointers by index: 1/2 →
  `w_moveHumanPtr`, 3-7 → `w_moveChocoboPtr`, 8 → `w_movePlanePtr`, 9/10 → `w_movePlanePtr`. Using those
  hijacks the engine's vehicle/human singletons.
* `w_moveCHRStatus` is a **22-slot array of a CLASS** (`ff9.cs:1769` `new ff9.s_moveCHRStatus[22]`;
  `ff9.cs:10666 public class s_moveCHRStatus`) — index must be `0..21` and two actors sharing an index
  share mutable ground/slice state.

Free-index census (disassembling `SetObjectIndex` across all 13 stock dispatchers):

| dispatcher | indices used | free |
|---|---|---|
| WORLD00 | 1,3,4,5,6,7,11,12,13 | 0,2,8,9,10,14-21 |
| WORLD03 | 1,3,4,5,6,7,8,11,12,13,14 | 0,2,9,10,15-21 |
| **WORLD11** | **1,11,13,15,18,20,21** | **0,2,3,4,5,6,7,8,9,10,12,14,16,17,19** |
| WORLD12 | 1,6,7 | 0,2,3,4,5,8-21 |

For WORLD11, the safe decorative picks (free **and** outside 1-10) are **{0, 12, 14, 16, 17, 19}**; **0 is
the most inert** (see §5).

### 4b. s49 / the world-smoother NRE — **APPLIES, and it is the one real gate**

Patch: `memoria-patches\s49-world-smoother-anim-guard.patch`. Rationale entry (incl. the 1,868-NRE log and
the "world script tick silently dead" symptom): `memoria-patches\README.md:70`. Kit narrative on the same
class: `ff9mapkit\docs\OVERWORLD_ENGINE.md:290-322`.

Stock code (the `-` lines of the patch, hunk at `SmoothFrameUpdater_World.cs` ~line 53):
```
String curAnim = FF9DBAll.AnimationDB.GetValue(actor.originalActor.anim);
Animation anim = actor.Animation;
AnimationState animState = anim[curAnim];
… animState.time reads …          # live file: SmoothFrameUpdater_World.cs:107 and :113
```
Loop head, live file
`C:\gd\FFIX\Memoria\Assembly-CSharp\Memoria\Application\SmoothFrameUpdater_World.cs:67-70`: it iterates
**every** active `cid == 4` object and only skips when `actor == null || cid != 4 || actor.Animation ==
null`. **Note there is no visibility check** — hiding the object does not exempt it.

What makes an actor trip it (two independent doors):
1. `actor.originalActor.anim` not a key in `AnimationDB` → stock `GetValue` is `_fwdDictionary[key]`
   (`C:\gd\FFIX\Memoria\Memoria.Prime\Collections\TwoWayDictionary.cs:83-86`) → **KeyNotFoundException**.
2. The name resolves but the object's `Animation` component holds **no clip of that name** →
   `anim[curAnim] == null` → **NRE on `animState.time`**.

Door 2 is exactly what a no-animation static hits, and this is the subtle part:
* `Animation` component is always present — `ModelImporter` adds one for loose FBX at
  `Memoria\Assets\3DModel\ModelImporter.cs:132` and `:334`; bundled prefabs ship one. So the
  `actor.Animation == null` escape never fires.
* A minted world model gets **zero clips at creation**: `ModelFactory.cs:171` →
  `AnimationFactory.AddAnimToGameObject` (`Global\AnimationFactory.cs:68-99`) — the name is not in
  `animationMapping`, and the `_W0_` auto-anim branch loads `Animations/GEO_SUB_W0_DWX` which does not
  exist → early `return` at `:88-89`. Clips only arrive via `SetStandAnimation`/`SetWalkAnimation`/`ARUN`,
  which call `AddAnimWithAnimatioName` (`DoEventCode.cs:1142`, `:1179-1190`; `AnimationFactory.cs:54-66`).
* `actor.anim` defaults to **0**, and `AnimationDB[0]` **does** exist:
  `Global\ff9\FF9DBAll.Animation.cs:5745` → `{0, "ANH_MAIN_F0_STN_B"}`. That is a *Zidane field* clip —
  never on a `GEO_SUB_W0_*` object. So door 1 is dodged and **door 2 fires**: `animState == null` → NRE
  **every frame**.

Is the smoother even on? `Enabled => Configuration.Graphics.WorldFPS < 0 || WorldTPS < WorldFPS`
(`SmoothFrameUpdater_World.cs:62`). Defaults are `WorldFPS = 20`, `WorldTPS = 20`
(`Memoria\Configuration\Structure\GraphicsSection.cs:40-41`) → disabled. **But this install's
`Memoria.ini` sets `WorldFPS = -1` (line 54) and `WorldTPS = 28` (line 55)** → `Enabled == true`. So on
this machine the hazard is live.

Contrast, and the reason the stock game never trips: the *other* per-frame anim path is guarded.
`WMActor.UpdateAnimationViaScript` (`Global\WM\WMActor\WMActor.cs:182-199`), called for every world actor
every frame from `WMScriptDirector.cs:232-244`, does `if (anim.GetClip(animName) == null) return;` at
`:191-192`. Only the Memoria-added smoother is unguarded.

**Verdict:** a static object **with no animation trips the s49 NRE on stock Memoria** (whenever `WorldFPS
< 0` or `WorldTPS < WorldFPS`). It does **not** trip it if it sets a donor-borrowed idle **and** actually
runs it (`RunAnimation` → `ExecAnim` sets `anim`, and the clip was added by `AddAnimWithAnimatioName`) —
i.e. exactly the stock WORLD11-entry-11 shape in §3c/§3d. s49 remains the belt-and-braces: it also covers
the case where the borrowed clip fails to LOAD (`AssetManager.Load` returns null → `AddClip` never
happens → `animState == null` again), which no `.eb` discipline can guarantee offline.

## 5. Does a placed world object cost anything in the ground query / walkmesh?

**Walkmesh geometry: no.** The world ground query raycasts **only the terrain `WMMesh` triangle arrays** —
`WMPhysics.Raycast(ray, WMMesh, out hit)` (`Global\WM\WMPhysics.cs:6-48`) and `WMBlock.Raycast(ray,
List<WMMesh>, …)` (`Global\WM\WMBlock\WMBlock.cs:185-215`, walkability decided from `tangents[...].x` =
the topo/`mapid` word at `:210`). No Unity colliders, no actor meshes. An `.eb` actor adds **zero**
walkmesh surface and cannot be stood on or block a step.

**Per-frame cost: yes — one ground raycast per visible object per tick.** `ff9.w_movementUpdate`
(`ff9.cs:5102-5194`) walks every active `cid == 4` object; for each visible non-controlled one (`:5122
objIsVisible`, `:5136-5141`) it runs the else-branch at `:5142-5189`: `w_cellHit(ref pos, ref status.id,
out num, null, out ground_height)` (with a second sky-cast retry on a miss, `:5151-5155`), writes
`status.ground_height`, writes back `wmActor.pos`, then `w_movementSetheight(posObj)` (`:5191`).
`w_movementChrInitSlice` (`ff9.cs:4588-4604`) does the same sweep on load. Visibility gate = `flags & 1`
(`EventEngine.cs:1170-1175`, wrapper `ff9.cs:2209-2212`) — the *show model* bit.

**Whether the Y you authored survives is index-dependent.** `w_movementSetheight` (`ff9.cs:5427-5482`)
does all of its ground/slice work under **`if (s_moveCHRStatus.cache != 10)`** (`:5432`) and otherwise
only calls `wmActor.SetFogByHeight()` (`:5480`). Extracting the 22-row table from `ff9.cs:1769+`:

| index | slice_type | shadow_size | flg_fly | control | cache | effect |
|---|---|---|---|---|---|---|
| **0** | 0 | **0** | 0 | 11 | **10** | height logic SKIPPED, shadow never scaled/positioned → authored Y kept verbatim |
| 1,2 | 1 | 6 | 0 | 0 | 0 | human (hijacks `w_moveHumanPtr`) |
| 3-7 | 1 | 10 | 0 | 1-5 | 1 | chocobo (**s51 block + `VerifyValidCastPosition` clamp**) |
| 8 | 2 | 16 | 0 | 7 | 2 | Blue Narciss (**s51 block**; `ground_height` forced to 0 at `ff9.cs:5156-5159`) |
| 9,10 | 0 | 16 | 1 | 8,9 | 2 | airship (hijacks `w_movePlanePtr`) |
| 12 | 0 | 6 | 2 | 11 | 9 | height applied |
| 13 | 1 | 0 | 2 | 11 | 10 | height skipped, no shadow |
| 14 | 0 | **30** | 0 | 11 | 10 | height skipped, but `w_FF9DisplayShadow` special-cases `index != 14` (`ff9.cs:5052`) |
| 15-21 | 0 | 12-16 | 1 | 11 | 4-8 | flying classes (15 is what stock WORLD11 e11 uses) |

So **index 0 is the ideal decorative index**: no ground snap, no shadow scaling, no vehicle-pointer
hijack, no s51 block, and because `cache == 10` short-circuits everything, **multiple decoratives can
share index 0 harmlessly** despite `s_moveCHRStatus` being a shared class instance. One thing to verify
in-game: `w_movementService` → `w_FF9DisplayShadow` (`ff9.cs:4984-5010`, `:5012-5061`) still `AddShadow`s
a generic 1.0-scale shadow object for an unrecognised index (`:5033-5037`) and `SetActive(true)`s it when
`display` is true (`:5039-5044`), while the positioning block is skipped for `shadow_size == 0` (`:5061`)
— i.e. a potentially unpositioned shadow quad. Cosmetic, not a crash.

**Interaction / "collision": no, unless you give it a handler.** In world mode there is no physical push.
`EventCollision.Collision` (`Global\Event\EventCollision.cs:167-242`, `gMode == 3` branch `:176-234`) is a
radius **proximity/trigger** query using `collRad`/`talkRad` and the `ovalRatio` stretch (`:206-209`); a
candidate must clear `flag4 = eventEngine.GetIP(obj.sid, (talk?3:2), obj.ebData) != nil` (`:199`) — i.e.
**the object must own a function tag 2 (or 3)**. Called every frame on the controlled object from
`EventEngine.ProcessEvents.cs:65-69` via `CollisionRequest` (`EventCollision.cs:253-296`). A decorative
entry with only tags 0 and 1 and `SetObjectFlags(1)` is therefore never selected: no talk prompt, no push,
no `!` icon.

**Encounters, camera, minimap:** unaffected — the object never becomes `w_moveActorPtr`/control char
(`ff9.cs:5136`), so the free-move/encounter branch (`w_movementControl`, `ff9.cs:5484+`) never runs for it.

## 6. Object/UID budget in `EVT_WORLD_WORLD11.eb`

Header layout: byte 3 = entry count, table at 0x80, 8-byte slots `off:u16 sz:u16 loc:u8 flags:u8 pad:u16` —
`ff9mapkit\ff9mapkit\eb\model.py:12-29`, `:40-44`. Engine side: `sSourceObjN = br.ReadByte()` at offset 3
and `sObjTable[i].ReadData` per slot — `EventEngine.cs:510-521`; slot layout
`Global\Objects\ObjTable.cs:6-14` (so the kit's `loc` byte **is** `varn`, the entry's local-Instance-var
byte count, consumed at `Global\Objects\Obj.cs:28`).

**STOCK `EVT_WORLD_WORLD11` (probed from the game archive):** 9348 B, **entry_count = 23**, slots **0-14
populated, 15-22 EMPTY**.

| slot | size | varn(`loc`) | etype | funcs | what (from `recon_world11.txt`) |
|---|---|---|---|---|---|
| 0 | 1480 | 0 | 0 | 45 | `Main_Init` + the entrance-func table (tags 38xxx-41xxx) |
| 1 | 1532 | 0 | 0 | 3 | the dispatcher (vehicle switch → AREA switch) |
| 2 | 76 | 0 | 0 | 2 | code entry |
| 3 | 1068 | 3 | 0 | 2 | code entry |
| 4 | 316 | 6 | 0 | 7 | code entry (tags 12,15-18) |
| 5 | 1172 | 26 | 2 | 6 | object, `SetObjectIndex(11)` `SetModel(307)` — Mog/moogle class |
| 6 | 536 | 0 | 2 | 4 | object, index 13, model 311 |
| 7 | 332 | 1 | 2 | 4 | object (walk-path actor, tags 24/25) |
| 8 | 500 | 1 | 2 | 4 | object, index 18, model 319 |
| 9 | 468 | 1 | 2 | 4 | object, index 20, model 315 |
| 10 | 672 | 1 | 2 | 4 | object, index 21, model 314 |
| 11 | 88 | 0 | 2 | 2 | **the decorative static** — index 15, model 313, fixed `MoveInstantXZY`+`TurnInstant` |
| 12 | 360 | 1 | 0 | 2 | code entry |
| 13 | 44 | 9 | 0 | 2 | code entry |
| 14 | 392 | 9 | 2 | 5 | **the world player anchor** — index 1, model 310 |
| 15-22 | 0 | — | — | — | **free** |

**DEPLOYED `FF9CustomMap-world` copy (all 7 languages present; us/uk/es/fr/gr/it = 9718 B, jp = 9706 B;
entry_count still 23):** slot 0 grew to 1516 B / 46 funcs (the added `InitObject(15,0)`), slot 14 grew to
424 B / 6 funcs (the added tag-60 shore-snap), and **slot 15 = the boat, 287 B, etype 2, 2 funcs**. **Free
entry slots remaining: 7 (16-22).**

**UIDs taken.** Because `InitObject(slot, 0)` defaults `uid = sid` (`Obj.cs:19-21`) and the stock
`Main_Init` arms slots by raw index (`recon_world11.txt:133-149`: `InitCode 13,12,1,2,3,4` / `InitObject
11(gated),8,9,10,5,14`), **uid == slot index throughout**: **0-15 taken, 16-22 free**. Engine-reserved
uids on top of that: 250 = player alias, 251-254 = party, 255 = self
(`ff9mapkit\ff9mapkit\content\object.py:187` `_SPECIAL_UIDS`; used as `obj(uid=250)`/`obj(uid=255)` in the
disasm at `recon_world11.txt:132` / `:2064-2067`).

**Is an entry-add a supported kit operation?** The primitive is first-class and heavily exercised —
`eb.edit.append_entry` (`edit.py:96-130`) is used by ~14 field content injectors (`content\gateway.py:101`,
`content\object.py:261/316/329`, `content\ladder.py:481/492/560/638`, `content\platform.py:309/334/418`,
`content\cutscene.py:364`, `content\encounter.py:38`, `content\music.py:81`, `content\camera.py:96`,
`content\ate.py:117`, `content\onentry.py:132`, `battle\aiauthor.py:57`). It refuses a non-empty slot
(`edit.py:110-111`), enforces the u16 table-offset budget ≈64 KB (`edit.py:115-122`) and the 255-slot
ceiling (`edit.py:67`, `:84-85`, cross-referenced `ff9mapkit\docs\BEHAVIOR.md:445`).

Caveats that are real, and none of them is "corruption":
* **`append_entry` writes `loc/varn = 0`** (`edit.py:126-129`). An appended entry therefore has **no
  Instance var space** — `Instance.Byte[n]` in its body is out of its allocation (`Obj.cs:28`). Compare
  stock slots 5 (varn 26) / 3 (3) / 4 (6). The boat body uses none; a decorative body must use none either
  (or the slot record's byte 4 must be set by hand).
* **Do not renumber.** `insert_entry_at` (`edit.py:133-168`) renumbers later slots and is only safe behind
  the field-specific remapper `content\object.py:228-246 insert_entry_before_band` + `shift_slot_refs`
  (`:190-225`). There is **no world equivalent** — use `append_entry` into a free slot.
* **Growing byte 3 is lower-risk on the world than on a field**, because the `sSourceObjN - 9` party band
  is battle-only (`EventEngine.cs:643-653`, gated `gMode == 2`) and `GetNumberNPC` is a field consumer
  (`EventEngine.cs:919` → `Honolulu\HonoluluFieldMain.cs:140`). Moot for WORLD11 anyway: 7 pre-declared
  empty slots.
* **7 languages, each its own base.** `OVERWORLD_ENGINE.md:344-350` and `build_boat_world11.py:256-267`
  (patch every language *from its own bytes*; JP has a distinct layout — confirmed by the 12-byte size
  difference above). The kit doc's general warning about hand-rolling entry tables is
  `ff9mapkit\docs\TROUBLESHOOTING.md:182` / `docs\TECHNICAL.md:103-104`.

## VERDICT — is the scripted decorative-object lane stock-Memoria-clean?

| hazard | applies to a decorative non-vehicle static? | custom-engine patch required? |
|---|---|---|
| **s51** world-constructor clone-name NRE (`ff9.cs:4436-4535`, gates at `:4445` and `:4504`) | **No** — unreachable unless `SetObjectIndex` is 3-7 or 8 | **NOT required.** Stock-clean by construction: pick an index outside 3-10 (index **0** best; WORLD11 free-and-safe = {0,12,14,16,17,19}) |
| **s49** `SmoothFrameUpdater_World.RegisterState` NRE (`SmoothFrameUpdater_World.cs:67-91`, stock `.time` derefs at `:107`/`:113`; enabled here by `Memoria.ini` `WorldFPS = -1`) | **Yes, if the object has no running animation** — `anim` stays 0, `AnimationDB[0]="ANH_MAIN_F0_STN_B"` (`FF9DBAll.Animation.cs:5745`) is not a clip on a `GEO_SUB_W0_*` object → per-frame NRE that kills the whole world script tick | **Avoidable without the patch** by copying stock WORLD11 entry 11 exactly: `SetStandAnimation(<donor idle>)` in tag 0 **and** `RunAnimation(<same>)` in the tag-1 loop. **s49 is still recommended as the safety net** (a clip that fails to load lands in the same NRE, and nothing offline can prove the load). |

**Bottom line:** the scripted-object lane is **stock-Memoria-clean** — unlike the vehicle lane, which
hard-requires s51 — *provided* the two laws at the top of this document hold. Everything else on the lane
is stock: the `3DModel` registration (`DataPatchers.cs:591-613`, one relaunch), the loose-FBX mint under
`Models/5/<id>/` (no DLL), and the `.eb` entry-add via `eb.edit.append_entry` into one of WORLD11's 7
remaining free slots (16-22), armed with `InitObject(<slot>, 0)` in `Main_Init`, written per-language into
`<mod>/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/<lang>/`.
