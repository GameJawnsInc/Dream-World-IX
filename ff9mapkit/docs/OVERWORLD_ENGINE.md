# Overworld (WorldMap / "WM") engine mechanics — Memoria/FF9

Reverse-engineered while building the **F6 overworld debug tools** (2026-07-01). It is all C# in the Memoria
engine (built from FF9's own game bytes), so every mechanic here is ultimately traceable — including the teleport
reverter at the bottom, which turned out to be exactly that: plain C# (Memoria's frame smoother), **not** the
native driver we first suspected. Companion: the F6 menu lives in `Ff9mkDebugMenu.cs`; `ff9mapkit world-locate`
decodes the entrance dispatch.

## Update / tick architecture
- **Driver:** `WMScriptDirector` (a HonoBehavior). `HonoUpdate()` → `kPadPush.CollectInput()` →
  `HonoUpdate20FPS()` → `ff9.w_frameMainRoutine()` → `ff9.w_frameUpdate()`. There is also a plain Unity
  `Update()` → `OnUpdate20FPS()` loop (count = `FPSManager.MainLoopUpdateCount`). `HonoFixedUpdate()` →
  `WMWorld.OnUpdate()` which is **empty**. `HonoLateUpdate()` = projection matrix only.
- **`w_frameUpdate()` case 2** (the per-tick body), in order: `world.OnUpdate20FPS()` (wrap + pin SkyDome to the
  actor) → `w_movementUpdate()` (movement; free-move branch gated on `ff9.GetUserControl()`, else re-ground) →
  `w_frameUpdateEvent()` → `ServiceEvents()` → `ProcessEvents()` → **`eBin.ProcessCode()`** (the world `.eb`) →
  SPS → `w_cameraUpdate()` → `w_worldUpdate()`.
- **`w_frameService()`:** `w_movementService()` (shadows ONLY) → `w_worldService()`→`w_cellService()` (world
  effects) → `w_naviService()`.
- Logical tick ≈ 20 fps; render ≈ 60 fps (so a logical-tick change shows ~2–3 render frames after an OnGUI action).

## Actor / position model
- The player is a `WMActor` (`ff9.w_moveActorPtr`) — a MonoBehaviour on a GameObject `<name>WM`, **child of
  `TranslatingObjectsGroup`** (created in `WMWorld`; despite the name it stays FIXED at the origin — never
  translated). `originalActor` = the event `Actor`/`PosObj`, whose `.pos[]` are fixed-point coords.
- `WMActor.pos` getter = `transform.position` = **SCREEN** (wrapped) Unity units. `RealPosition` =
  `World.GetAbsolutePositionOf(transform)` = **ABSOLUTE** (un-wrapped) world units — the value the minimap +
  `ff9.w_frameGetParameter` (cases 201/202/203) use. Log both when debugging.
- Transform-writing setters: `.pos`, `.pos0/1/2` (each writes `transform.position` **and** `originalActor.pos[]`),
  and `SetPosition(x,y,z)` (fixed-point; writes transform + `SetAbsolutePositionOf` + `lastx/y/z`, but NOT
  `originalActor.pos`). Units: **fixed-point = worldUnits × 256**; `ff9.UnityUnit(f)` returns `f×256`.
- **Wrap:** 24×20 blocks of 64u. `OnUpdate20FPS` sets `BlockShift = 0` then `while(!Wrap()){}` to re-center;
  blocks carry `InitialX/Y` (content identity) vs `CurrentX/Y` (screen slot). `SetAbsolutePositionOf(t, absPos)`
  maps an absolute coord onto whichever loaded block currently holds that identity (`CurrentX*64 + local`).

## Player capabilities
- **Vehicle / control mode:** `gEventGlobal[190]` = `ff9.w_moveCHRControl_No`; `ff9.w_movementChange()` re-reads
  it (in the non-Bee scene) and applies the movement profile from `w_moveCHRControl[]` (ff9.cs:~1467). Modes:
  0 foot · 1–5 chocobo (terrain variants) · 6 gold-flying · 7 Blue Narciss (boat) · 8 Hilda Garde III · 9
  Invincible. Boarding is event-driven (swaps the controlled actor). The F6 **vehicle swap** does the null-safe
  *profile* swap (`[190]` + `w_movementChange`): terrain access / flight / speed / camera change, but Zidane keeps
  his model, and flying gives flying *collision* without ascent (no actor swap).
  `gEventGlobal[102]` = a separate `wmID` used by `WorldConfiguration`.
- **⚠ The profile swap is NOT safe in every world state (crash class).** `w_movementChange` is C#-null-safe, but
  each overworld state runs a different `EVT_WORLD_WORLDxx` event-script dispatcher. **Boarding a vehicle sets
  `[190]` AND the per-vehicle nav state (`Map.Byte[24/25/26]`) together; the F6 swap pokes only the byte.** So on
  any state whose **per-frame vehicle switch (entry-1/tag-1, `op_0B` on `Global.Byte[190]`)** has real nav arms
  (chocobo / air / boat), forcing a mode — *even one the game legitimately uses there* — drives that arm on
  uninitialised nav state → a `CalcStack` expression underflow (`[CalcStack.pop] topOfStackID == 0`, spammed
  per-frame) → crash. **In-game proven (2026-07-02): on WORLD00 both chocobo (1–5) AND airship (7–9) crash;
  only foot (0) is safe.** The underflow itself is soft (`CalcStack.pop` returns 0 and continues); the crash is a
  secondary fault off the corrupt branch. The real game never hits this because it always boards through the
  event sequence. **Fix (s22, F6 menu, commit 887ea62 + follow-up):** the vehicle buttons are gated per
  `wldMapNo` (`VehicleAllowByWorld` in `Ff9mkDebugMenu.cs`) + a belt-and-braces refuse in `SetVehicle`:

  | wldMapNo | dispatcher | switch shape | allowed modes |
  |---|---|---|---|
  | 9002, 9010, 9011 | WORLD02/10/11 | foot-only switch, **benign** idle default (no nav arm) | **0–9 (all)** — safe no-op, C# profile still swaps (WORLD11 ★in-game) |
  | 9000, 9003, 9005, 9007, 9008, 9009 | WORLD00/03/05/07/08/09 | vehicle-discriminating (real nav arms) | **0 (foot only)** — any non-foot mode crashes |
  | 9001, 9004, 9006, 9012 | WORLD01/04/06/12 | cutscene, no vehicle switch | **0 (foot only)** (conservative) |

  **Reaching a test entrance on a gated state (WORLD00 etc.):** use the vehicle-independent **World-tab
  Teleport** (absolute X/Z, re-grounds) — the swap can't fly you there. Making a vehicle actually work on a
  discriminating state would require replicating the boarding nav-state setup, or a *profile-decouple* (set the
  C# movement profile — `w_moveCHRControl_No`/`w_moveCHRControlPtr`, both `public static` — WITHOUT touching
  `[190]`, so the `.eb` stays on its safe foot arm). Both are unproven follow-ups.
- **Chocobo:** summonable on track topographs 3/18/21/22/28 (`w_frameChocoboCheck`) + Gysahl (event layer);
  `ff9.w_moveChocoboPtr` / `w_movePlanePtr`, availability via `originalActor.isEnableRenderer`.
- **Discs:** `WorldConfiguration.GetDisc()` = `ff9.w_frameScenePtr >= 11090 ? 4 : 1`; stored in `ff9.w_frameDisc`
  (== `gEventGlobal[0]`). Only **WorldDisc1** and **WorldDisc4** prefabs exist (discs 2–3 reuse disc-1 content).
  `WMWorld.SetDisc(1|4)` → `SceneDirector.Replace("WorldMapDebug", FadeOutToBlack_FadeIn)`. Switch via
  `ff9.w_frameSetParameter(501, 11090)` (→disc4) / `(502, 0)` (→disc1) — the stock `WMBeeMenu` pattern. It's a
  COARSE switch (doesn't advance ScenarioCounter/party), so a mismatched save can show wrong geometry.
- **Entrance dispatch** (fully byte-resolved 2026-07-01): walking an event tile fires `ff9.WorldEvent(cellX,cellZ,id)`
  which packs `num = 0x8000 | (cellZ<<8 & 0x3F00) | (cellX<<2 & 0xFC) | (id&3)` and `Request(objUID0, 1, num)`;
  `EventEngine.GetIP` matches `num` against object-0's **function TAGS** (not entry ids) — so **an entrance is a
  FUNCTION in object 0 whose tag == the cell `num`** (53 of them on disc-1 WORLD00). No matching func → silent no-op
  (that's why a bare tile-IDALL edit can't create an entrance). The func sets a place index `Map.Byte[39]` + hands off
  (`RunScriptAsync 6 1 11`) to the shared dispatcher (object 1, `tag-1`): vehicle switch → func-0xB does
  `Byte[24]=Byte[39]+100` → the dispatcher's conditional `Byte[24]-=100` → `Byte[29]=Byte[24]` → the base-2 AREA switch
  (60 cases) on `Byte[29]` → ScenarioCounter → `Field(dest)` (0x2B). **So the destination is the func's `Byte[39]`
  (== the switch case); the tile's IDALL area is only designer-correlated, NOT the dispatch key.** Interaction is the
  standard action-button `!` prompt, not a tread warp. `ff9mapkit world-locate` decodes area→field; journeys re-point
  via `worldmap_inject`/`field_remap`. **⚠ 13 DISPATCHERS:** the disc-1 overworld runs one of `EVT_WORLD_WORLD00..12`
  (p0data7) picked by the world MapNo (9000-9012 = entry/story state) — a new entrance must be added to the WORLDxx
  actually loaded (see below).
- **The game's own debug menu:** `WMBeeMenu` (the "Bee scene" = `WorldMapDebug`). Teleport buttons =
  `SetPosition(fixedPt) + w_movementChrInitSlice()`; disc = 501/502; change char = `WMScriptDirector.SetToNextChracter`.
  It is the ground-truth reference the F6 tools copy.

## The 13 world states (dispatchers) + the exit cascade (RE 2026-07-02)

The overworld is not one script — it is **13 event-script dispatchers `EVT_WORLD_WORLD00..12` = `EventDB[9000..9012]`**
(`FF9DBAll.Events.cs:1834-1846`). Exactly one is loaded as the world's per-frame brain, keyed by `ff.wldMapNo`.

**How the game picks one — the shared "exit cascade" (settled, byte-verified):** `WorldMap()` opcode `0xB6` →
`EventEngine.SetNextMap(arg)` → `ff9InitStateWorldMap(arg)` sets `ff.wldMapNo = arg` and loads `EventDB[arg]`
(`ff9.cs:9132-9150`) — **the opcode argument IS the wldMapNo.** But no field hardcodes a single target: all **79
world-exit fields carry a byte-IDENTICAL cascade** (verified identical in field 300 Ice Cavern e2/tag2 and field
2800 Dragon Gate e21/tag2) that emits **all 13** targets and selects by **`(ScenarioCounter band) × (Map.Byte[2]
region key)`** — a chain of `opDC(0)` SC gates, each with a `opD8(2)` switch on the per-visit region/coast key.
The SC band boundaries (5990 · [9615..9790] · 10400 · 11090) are identical across exit fields, and **11090 is
exactly `GetDisc()`'s disc-4 threshold**. `9009` is every band's **default arm** (the all-vehicle, all-field superset).

**Disc model:** ONE shared set of 13 for all four discs — no separate disc-4 family. SC<5990 → disc-1 {9000,9002,
9010,9011}+9001; 5990–10399 → disc-2/3 {9003,9005}+{9004,9006,9012}; 10400–11089 → late-disc-3 {9007}+9012;
≥11090 → disc-4 {9008}+9012; every band defaults to 9009. Disc 4 loads distinct **art** (`WorldMap/wmap/disc4/*`,
only `WorldDisc1`/`WorldDisc4` prefabs exist) but the **same `.eb` dispatcher family**.

| wldMapNo | role | disc / beat | vehicles boardable | notes |
|---|---|---|---|---|
| **9000** | free-roam | disc 1, most-open | foot + chocobo (0–6) | largest disc-1 entrance table (57 funcs); + Chocobo Forest/Hot&Cold |
| **9001** | **cutscene** | disc 1 (SC ~2910) | — | Cargo Ship → Field(503) |
| **9002** | free-roam, foot-only | disc 1, **earliest** | foot only | baseline Mist Continent (21 funcs, no chocobo) |
| **9003** | free-roam | disc 2–3 | foot + chocobo + fly + **boat (7)** | first boat state; + harbors {2173,2403} |
| **9004** | **cutscene** | disc 3 (~9400) | — | Hilda Garde 1 → Field(2261) |
| **9005** | free-roam | disc 3, Outer Continent | foot + chocobo (0–6) | cascade routes here on 9615≤SC≤9790 |
| **9006** | **cutscene** | disc 3 (~9400–9600) | — | Track Kuja → Field(2856) |
| **9007** | free-roam | late disc 3 | + **Hilda Garde III (8)** | own SC tier 10400–11089; + shrines {2550,2551} |
| **9008** | free-roam | **disc 4** | + **Invincible (9)** | sole state at SC≥11090; + {2752,2901 Memoria}; disc-4 art |
| **9009** | free-roam **superset** | all discs (default) | fullest (foot/chocobo/boat/Invincible) | every band's default arm; 63 fields |
| **9010** | free-roam, foot-only | disc 1, mid | foot only | baseline (same set as 9002/9011) |
| **9011** | free-roam, foot-only | disc 1, mid | foot only | baseline; the F6-proven safe vehicle-swap state |
| **9012** | **cutscene** | discs 2–4 (reused) | scripted (self-sets 190=6) | Chocobo Treasure → Field(1953) |

**Roles:** free-roam area-switch states (9000/02/03/05/07/08/09/10/11) each have the full entry-1/tag-1 dispatcher
(vehicle switch → base-2 AREA switch, ~59 cases → `Field()`) + a big entry-0 entrance-func table; the 4 cutscene
states (9001/04/06/12, named verbatim in `eventWorldMaps`, `ff9.cs:10344`) have no AREA switch and warp to a fixed
field. **A custom entrance must be added to the WORLDxx actually loaded at that beat** (`world-entrance` targets it).

**Region-key selection — RESOLVED 2026-07-02.** Within an SC band the state is picked by a **global region key
`opD8(2)`** (GLOB source, *not* `Map.Byte[2]` as first thought — a persistent `gEventGlobal` 16-bit value at index 2)
that **each exit field writes itself, SC-gated**, then the shared cascade's `op_0B`/`op_06` switch maps region-key →
`WorldMap(wldMapNo)`. Decoded from field 300's cascade (entry-2/tag-2, 19 `WorldMap` ops) and swept across all **61**
WorldMap-emitting fields — the region-key write is **per-field/heterogeneous** (field 300 writes {41,71}; field 262
{35,46,66,75}), confirming these are region-partitioned, not one shared value. Disc-1 partition (low SC band): region
key → **9000** {17,23,24,26,27,28,33,38,41,44,46,64,66,83}, **9002** {67–78}, **9010** {18,30,37}, **9011**
{35,36,42,43,45,50}, **9001** {52}; any **un-cased key → switch default = 9009** (no field writes 9009's own key 62).
So the four disc-1 free-roam states are distinguished by **which coast/area you exit into (× story)**, not a linear
sequence — all four are live. Disc-2/3 band → {9003 (bulk), 9005, 9004:key53, 9006:key55, 9012:key85}; late-disc-3 →
{9007 (bulk), 9012:85}; disc-4 → {9008 (bulk), 9012:85}; every band defaults to 9009. *(The exact real-world area
each small key names is a further nicety; the state map itself is settled.)*

**The "13" ARE the complete LIVE set — RESOLVED 2026-07-02.** EventDB also registers `9100=WORLDTS`, `9101=WORLDSV`,
`234=PAGE_1`, `286/598=WORLD_LND00/WM_LND00`, `287/599=WORLD_TRE00/WM_TRE00` (`FF9DBAll.Events.cs:1831-1850`) — but
`9100/9101` ship an `.eb` **only under `jp/`** (both 21760 B, full dispatchers, near-copies of a big WORLDxx) and are
**never invoked** by any field's exit cascade *or* any engine C# path (the only `9100/9101` refs are an unrelated SC
compare + animation ids) → **vestigial dev leftovers** (TS = title-screen, SV = save experiments). The LND/TRE/PAGE
ids have **no `.eb` asset at all** → dead name registrations. So custom overworld authoring targets exactly the 13
(9000–9012); nothing else is reachable.

## Minimap / place-names — FOUR distinct subsystems (RE 2026-07-02)

"Place name" conflates four independent layers. Keeping them apart is the point:

**1. Minimap MARKERS (the town/dungeon dots).** `ff9.w_naviLocationPos` = a **hardcoded C# `navipos[2,64]`**
(`struct { Int16 vx,vy; Int32 tx,ty; }`, `ff9.cs:10608`; built by literals `ff9.cs:421-1318`). Indexed
`[w_naviMapno, locationId]` — `w_naviMapno = (w_frameScenePtr>=5990) ? 1 : 0` (`ff9.cs:8678`; **dim0 = disc 1**
(`<5990`, the Mist Continent, 26 markers), **dim1 = disc 2+** (`>=5990`, the expanded/Outer/Forgotten world +
disc-4 — one shared coord layout, NOT a separate disc-4/Terra map as first labelled)). `vx/vy` = **baked minimap pixels**; `tx/ty` = **world coords** (fixed-point, used *only*
for airship autopilot). Render: `WorldHUD.cs:785-816` loops 0..63, spawns a `LocationPointer` at `vx/vy`
directly (markers do NOT use the live `w_naviGetPos` projection — that's the moving player/vehicle BLIP, a
separate pipeline, `ff9.cs:6939`). **Visibility gate = save flags:** `w_naviLocationAvailable` (`ff9.cs:6957`)
draws marker `n` iff `(vx|vy)!=0` AND unlock-bit `n` is set — the 64 bits are `gEventGlobal` bytes 92/94/96/98
(`keventNaviLocF0..F3`, `FF9Define.cs:183`) = **bits 736-799**. Disc-4 force-ORs `0x7C0`/`0xC000` into word 92
(`ff9.cs:6925`). Marker NAME = the world field's own text table 0: `FF9TextTool.GetTableText(0u)[locId+1]`
(`WorldHUD.cs:826`; special-case `63→49` Chocobo's Paradise).

**2. In-menu location NAME (the header on approach / in the menu).** `FF9TextTool.WorldLocationText(GetSysvar(192))`
(`UIManager.cs:544`, `MainMenuUI.cs:499`; also tile-area-keyed at `ff9.cs:3750`), from a `worldLocationText`
dict loaded from embedded `/ETC/worldloc.mes`. **`SetWorldLocationText` (`FF9TextTool.cs:791`) does NOT go
through `TextPatcher.PatchDatabaseString`** (unlike item/ability text) → **the kit's `TextPatch.txt >DATABASE`
cannot reach these**; the only no-DLL override is the legacy Memoria `[Import] Text=true` →
`StreamingAssets/Text/<LANG>/ETC/WorldLocations` (a single dir, NOT FolderNames-stacked).

**3. Continent-title BANNER (the big "Mist Continent" card).** `w_naviTitle` (set in `w_worldSystemConstructor`,
`ff9.cs:8682-8697`) = a **hardcoded scenePtr switch** — only `2400/5990/9605/9890 → 0/1/2/3`. Render =
a pre-rendered **language-keyed sprite** (`FF9UIDataTool.LoadWorldTitle`, `WorldHUD.cs:883`); rect/fade timing
tunable via `WorldConfiguration` `Title` tokens (FolderNames-stacked), but the TRIGGER is hardcoded.

**4. Player/vehicle BLIP.** live `w_naviGetPos(x,z)` world→normalized projection (`ff9.cs:6939`).

**⚠ don't confuse:** `w_worldLocX/Z/SENum` (`ff9.cs:1446`) is a **3-entry** proximity/SE table (Cleyra / Wind
Shrine / Earth Shrine), NOT the 64-marker table. And the field-entry place-name banner is the *separate*,
already-solved `FieldLocationName`/s33/`[field] location` seam.

**Authoring seams (no-DLL vs. rebuild):**
| Capability | Seam | DLL? | Diff |
|---|---|---|---|
| **Reveal/hide an existing marker via a flag** | `gEventGlobal` bits 736-799 (kit already names them, `flags.py:81`) | **no** | **low ★ cleanest win** |
| **Rename an existing marker's map label** | world field `.mes` table 0 (`GetTableText(0)[locId+1]`) | **no** | med |
| Rename the in-menu approach name | legacy `[Import] Text` → `ETC/WorldLocations` only (not the kit's TextPatch) | no* | high |
| Add / move a marker at custom coords | `w_naviLocationPos` is a compiled array — no data hook | **yes** | high |
| Fire the continent banner for a custom scenePtr | hardcoded `ff9.cs:8683` switch | **yes** | high |

**★ Built + IN-GAME PROVEN (2026-07-02) — `[startup] reveal_markers`.** Proof: revealed Lindblum (locId 24,
bit 760) — flag read 1 after entering the field, and the overworld marker changed from **"?" to "Lindblum."**
**In-game refinement:** an undiscovered marker with valid coords still SHOWS (as `"?"`); the discovery bit reveals
its NAME — so the bit gates the label, not the dot's existence (refines the `w_naviLocationAvailable` render-loop
reading in System 1). The reveal-via-flag win is now a declarative surface:
```toml
[startup]
reveal_markers = ["Alexandria", "Ice Cavern", 5, "all"]   # names (ALL matching slots), locIds 0-63, or "all"
```
on any field compiles to `set GLOB.bit[736+locId] = 1` presets prepended to that field's Main_Init — **byte-identical
to the game's own exit-cascade discovery write** (`opE4(736+locId)=1`), so entering the field reveals those markers
(persisted, save-backed). By-name resolves every slot a name owns (`"South Gate"` → 6-10; `"Qu's Marsh"` →
21/29/40/45). Registry + resolver: `ff9mapkit/world/navimap.py` (`MARKER_NAMES`, `resolve_markers`); it composes at
campaign/journey scope (the startup merge carries `reveal_markers`). Reveal-only (set to 1); to hide, use a raw
`flags = [{flag = <736+locId>, value = 0}]`. ⚠ a new marker still needs coords (a DLL) — this reveals the 64 existing
slots, and disc-4 force-unlocks a few regardless.

**Discovery-WRITE path — RESOLVED (probe 2026-07-02).** No engine write (only reads + the disc-4 force-OR):
each field's **exit cascade sets `GLOB bit (736+locId) = 1`** (the `.eb` token `opE4(lo,hi)` with `lo+hi*256 =
736+locId`, then `op7D(1,0) op2C`), revealing the markers **reachable from that exit**. Confirmed across **50 of
61** WorldMap fields: field 300 Ice Cavern → bit 739 (locId 3); field 262 Evil Forest → locId 1/2/3
(Alexandria/Evil Forest/Ice Cavern); the South-Gate fields → the locId 6-10 cluster; Alexandria Port (2403) →
locId 0. **So a mod reveals ANY marker with `set GLOB.bit[736+locId]=1` (no DLL) — this is the flag win, exactly.**
**Full `locationId → name` map — CAPTURED** (split world txid-0 by `\n`, index `locId+1`): 64 names — disc-1 (0-25)
= Alexandria Harbor · Alexandria · Evil Forest · Ice Cavern · Quan's Dwelling · Treno · South Gate ×5 · Ice Cavern ·
Observatory Mtn · Dali · North Gate ×2 · Gizamaluke's Grotto · Burmecia · Cleyra · Chocobo's Forest · Gizamaluke's ·
Qu's Marsh · Pinnacle Rocks · Lindblum Dragon's Gate · Lindblum · Lindblum Harbor; 26-63 (dim1) = Earth Shrine …
Oeilvert … Ipsen's Castle … Memoria (54) … Chocobo's Air Garden. **Slot counts: dim0 = 26 markers (0-25), 38 free
(26-63); dim1 ≈ 54 (0-48, 54-58), 10 free** — so the table has ample room, but a new marker's coords still need a DLL.
Kit's `worldmap_unlocks` band is 736-**823** (lumps in adjacent discovery bits e.g. `mognet_central` 815); the
**marker** bits are exactly 736-**799** (64).

## SOLVED — F6 overworld teleport (the `SmoothFrameUpdater_World` reverter) ★ IN-GAME PROVEN 2026-07-01
`SetActorPosition`/`SetPosition` moved the player; it held ~2 render frames, then snapped back to the **exact**
prior position on the first logical tick. **Root cause: `Memoria.SmoothFrameUpdater_World`** — Memoria's own
60fps world frame-interpolation smoother (active when render fps > the 20fps logical tick; `SmoothFrameUpdater_World.cs:45`),
which keeps its **own** committed position store per `WMActor` (`_smoothUpdatePosPrevious`/`_smoothUpdatePosActual`,
captured each tick in `RegisterState()`). Two of its methods write the actor transform **DIRECTLY**, bypassing every
`WMActor.pos`/`pos0`/`pos1`/`pos2`/`SetPosition` property:

- `ResetState()` (`SmoothFrameUpdater_World.cs:191`) — `wmActor.transform.position = wmActor._smoothUpdatePosActual;`,
  an **unconditional** snap to the cached pos, run at the **START of every logical tick BEFORE movement**
  (`HonoBehaviorSystem.cs:111`, inside the `MainLoopUpdateCount` loop). **This is the reverter.**
- `Apply()` (`cs:145`) — a per-render-frame `Vector3.Lerp(prev, actual, t)`, **guarded** by `frameMove.sqrMagnitude < 100f`
  (`cs:144`) so a *big* teleport delta is **skipped** → the player visibly holds ~2 render frames, then the next
  tick's `ResetState` snaps him back. Every symptom, explained.

Because both writes hit `transform.position` directly (not the `pos` property), the earlier stack-trace probes —
which were on the `WMActor.pos*` **property setters** — never fired for the player, and we wrongly concluded a
"non-C# native driver." It was plain Memoria C# the whole time. **Lead #1 (animation) is refuted**:
`UpdateAnimationViaScript` samples `originalActor.go`, which `addGameObjectToWMActor` (`WMWorld.cs:224`) parents
**under** the `_WM` transform — so animation only moves the model's *local* pose inside the parent; it cannot
re-assert the parent's world position.

**The fix (the game's OWN idiom):** after repositioning, set `SmoothFrameUpdater_World.Skip = N`. The `Skip` setter
clears every actor's `_smoothUpdateRegistered` flag, so `ResetState` (guarded `!_smoothUpdateRegistered`) and `Apply`
(guarded `_skipCount > 0`) pass the actor over until the next `RegisterState` re-seeds prev+actual from the **new**
transform. The engine does exactly this whenever it repositions the world control actor —
`EventEngine.DoEventCode.cs:1009` (the `CC`/`DefinePlayerCharacter` opcode) and `SceneDirector.cs:124` (scene change).
`Ff9mkDebugMenu.WorldTeleport` now does, in order: `EventEngine.SetActorPosition` (writes `po.pos[]` + `lastx/y/z` +
the wmActor transform) → `w_movementChrInitSlice` (re-ground Y) → `w_movementAutoPilotOFF` → **`SmoothFrameUpdater_World.Skip = 2`**
(the game uses 1; 2 gives margin because the F6 write lands from OnGUI at an arbitrary phase vs the tick). The movement
tick itself is NOT a reverter — `w_movementUpdate`/`w_movementControl` read the *current* transform (`lastx/y/z` are
re-derived from `pos0/1/2` each tick) and `w_movementSetheight` rewrites only Y, so the teleported XZ survives.
Engine patch: `memoria-patches/s22-debug-menu-f6.patch`.

## Authoring a NEW overworld entrance (★ in-game proven 2026-07-01)
First authored overworld connectivity: a plain road cell (35,25, east of Dali) → custom `!` prompt → Confirm →
entered the journey's forked Ice Cavern (**map 7000**, via the `s28 ForkSiblingField` redirect of the dispatcher's
`Field(300)`). Recipe:

1. **Pick the cell + destination.** `num = 0x8000|(cellZ<<8)|(cellX<<2)|event`. The F6 **World** tab shows the live
   cell (`w_worldPos2Cell` = `(int)(x/32), (int)(z/-32)`, identical to the readout) — use it as the targeting oracle.
   The destination is chosen by cloning a func whose `Byte[39]` routes there (each existing entrance func is `Byte[39]
   == its dispatch case`; e.g. `0x9895` → case 4 → Field 300 = Ice Cavern).
2. **Add the trigger func** to object-0 of the world `.eb`: `ff9mapkit.eb.edit.add_function(worldeb, 0, num, body)`
   where `body` is a VERBATIM clone of an ungated entrance func (`0x9895`: 29 B, no story-gate, no position check —
   `if Byte[24]==100 && on-foot { Byte[39]=4; RunScriptAsync 6 1 11 } return`). Round-trips byte-exact; the 56+ existing
   funcs + the dispatcher stay identical.
3. **⚠ Add it to the RIGHT dispatcher(s).** The disc-1 overworld runs one of `EVT_WORLD_WORLD00..12` by entry/story
   MapNo (9000-9012). Add the func to **every full dispatcher that has your clone source** (WORLD00/02/03/07/09/10/11
   all have `0x9895` + the area-4 case; WORLD01/04/06/12 are tiny cutscene states; WORLD05/08 have area-4 but not
   `0x9895`). Missing the loaded WORLDxx = silent no-op (the bug that made the first build fail — it was only in WORLD00).
4. **Set the tile event bits.** `ff9mapkit.world.mesh.retarget_tiles(bm, event=1, area=4, center=<cell centre>,
   radius<=16)` + `deploy_override(...)` — a loose `.ff9mesh` (needs the `s34` WorldMeshOverride engine patch). Keep the
   radius inside the 32-unit cell so it doesn't spill into a neighbour's entrance.
5. **Deploy + relaunch.** World `.eb` → `<mod>/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/
   world/<lang>/EVT_WORLD_WORLDxx.eb.bytes` for **all 7 langs** (loader uses `Localization.CurrentSymbol`). ⚠ **Patch each
   language's OWN dispatcher, don't clone US to all** — unlike field scripts, the world dispatchers are NOT fully
   language-identical: **JP** carries localized inline event dialogue in the dispatcher entries + a distinct layout (its
   `WORLD00` is 16 B shorter than US); uk/es/fr/gr/it are code-identical to US. Cloning US bytecode into `jp/` clobbers
   the Japanese overworld dialogue. Relaunch (or exit+re-enter the overworld) to reload. On foot, walk the cell and press
   **Confirm** on the `!`.

### `world-entrance` — the whole flow in one command (`world/entrance.py`)
The five steps above (+ the optional building below) are folded into one command, `ff9mapkit world-entrance`
(module `world/entrance.py`), so a whole entrance is a single call:

```
ff9mapkit world-entrance --cell 35 25 --field 300 --mod-folder FF9CustomMap \
    [--building castle.obj --flatten-pad 14] [--dry-run]
```

What it does, generalizing + hardening the manual recipe:
- **Destination.** `--field N` inverts `area_to_fields` to the dispatch case (prefers a `default` branch; errors with the
  reachable-field list if N isn't overworld-reachable); `--case C` sets `Byte[39]` directly. `--field 300` → case 4 (Ice
  Cavern), the proven default.
- **Trigger func.** Clones WORLD00's `0x9895` body and **patches its single `Byte[39]=<case>` literal** (`D5 27 7D <lo>
  <hi>`, unique in the 29 B body) to the chosen case — so ONE proven template routes to any reachable field. Re-disassembled
  to confirm `Byte[39]==case` + `RunScriptAsync(6,1,11)` before use.
- **Dispatcher coverage.** Deploys to **every dispatcher whose base-2 area switch carries that case** (not just those with
  `0x9895`): all 9 (`WORLD00/02/03/05/07/08/09/10/11`) carry case 4 — the manual spike missed `WORLD05/08`. All 7 langs.
- **Stacking + idempotency.** Reads the mod-folder `.eb`/`.ff9mesh` as the base when present (so a 2nd entrance ADDS to the
  1st, and terrain/building overrides compose via `mesh.blockmesh_from_ff9mesh`), backs up each pre-edit dispatcher, and
  **skips** a dispatcher that already has the cell's tag (never clobbers). `--dry-run` prints the full plan writing nothing.
- **Event tiles + building.** Sets the cell's terrain event bits (`event`/`area`, radius kept inside the 32u cell — warns if
  0 tiles match), and with `--building` places+seats the OBJ as the Object mesh (folds `world-mesh-build`: `--building-at`,
  `--no-seat`, `--replace-town`, `--topograph`).
- **⚠ SEAT, don't flatten.** `--flatten-pad R` reshapes WALKABLE ground; on bumpy terrain the former high bumps become
  local walls you get stuck against (the overworld only raycasts DOWN, so you can't climb back out). It's auto-capped to
  the building's INSCRIBED footprint (min centroid-to-edge, not the max corner — an asymmetric building would poke a
  circular pad past its narrow side into walkable ground) so any step stays under the impassable structure. **Seating
  alone is the right default** — the skirt hides a small float.
- **⚠ Stacking compounds geometry.** Re-reading the deployed override composes event tiles across entrances, but a
  flatten pad / a kept building COMPOUNDS on re-run (a 2nd castle stacks on the 1st). Use **`--fresh`** to re-read the
  block from pristine p0data for a clean re-iteration.
- **⚠ Building = RENDER-ONLY object + TERRAIN-block collision (never the object mesh as a collider).** Four layered
  fixes made a Blender building work at an entrance: (1) **render on ANY cell** — the s34 hook only overrode an
  EXISTING Object component, so a building on an open cell was INVISIBLE; `WMWorld.RegisterBareObjectOverride` now
  CREATES an Object component on a bare block (names it "Object" → object-atlas material). (2) **render-only** — do NOT
  feed the object mesh to `AddWalkMeshForm1`; a 3D building as a collider makes its back-face-culled walls + sub-ground
  base into INVISIBLE collision. (3) **collision = the TERRAIN under the building's convex HULL set to topo-59**
  (`retarget_tiles(topograph=59, only_polygon=<hull>)`) — conforms to the ground (a floating prop base buries/floats);
  topo has ZERO render effect (UV-only, byte-verified) so it's invisible. (4) **place by bbox-CENTRE, not vertex
  centroid** (`build_from_obj`/`_building_world_hull`) — an asymmetric model's centroid bulges it ~15u off-cell.
  `world-entrance` does all this by default; triggers use `exclude_polygon=<hull>`.
- **⚠⚠ Pick a genuinely OPEN cell — check the WHOLE BLOCK, not a 16u radius.** The repeated stuck + "dirt mounds"
  were (a) my footprint block, and (b) the block's OWN natural terrain (block[18][12] = 195 topo-49 dirt/river tiles;
  the cell centre was walkable so a 16u scan passed it, but the surroundings are river). Scan the block's blocked-
  fraction: block[15][15] is 0% blocked (clean grass). The solid footprint is also SPAWN-FRAGILE — teleporting/returning
  INTO it = stuck. For an entrance building, **`--hollow-building`** (render-only + no footprint block = zero blocked
  tiles = never stuck) is the safe default unless the arrival point is guaranteed outside the footprint. Diagnose a
  trap with a point-in-triangle walkability map (`scratchpad/walk_fine.py`): if the spot reads walkable it's not a
  topograph trap (look at the placement / a spawn inside the footprint).
- **⚠ Walkability / escape.** A live soft-lock escapes via **F6 → World → Teleport**. On-foot walkability is
  `w_movementCheckTopographID(limit, id)` (ff9.cs:5769) with on-foot `limit = {0x0010667F, 0xD8FF3CFF}` — **topo 10/36
  walkable, 49/59 blocked** (a building's topo-59 is the wall). `world-entrance` also LINTS the cell
  (`_cell_openness_note`) and warns on mostly-blocked (river/cliff) cells; an open, all-walkable cell is roomier but the
  solid base is what prevents the box.

**★ IN-GAME PROVEN 2026-07-01:** a Blender-modelled castle spawned assembled + grounded at the command's cell, the `!`
prompt fired, warped to the forked Ice Cavern. See memory `project-ff9-worldmap-feasibility`.

### The building layer (the town/dungeon model) — ★ s34-overridable, proven 2026-07-01
Each block loads TWO baked meshes (WMWorldPrefabMaker.cs:37,102): **"Terrain"** (ground + walkmesh + IDALL) and
**"Object"** (the buildings/towns/trees). `WMWorld.RegisterBlockComponent` (WMWorld.cs:728) runs the `s34` override
for BOTH, interpolating `transform.name` — so a `.ff9mesh` at `…Block[X][Y] Object.ff9mesh` overrides the building mesh
with **no engine change**. ~63 of ~260 blocks carry an Object mesh (`extract.list_object_blocks`). Kit:
`extract.read_block(part="object")`, `mesh.deploy_override(…, part="Object")`, `mesh.place_building(dst, src, translate)`
(append a copied structure — flat/unindexed mesh concat + index offset; UV/tangent carry over → the shared object atlas).
★ Copied Alexandria's castle onto the cell-(35,25) entrance → it rendered + warped. **Polish gotchas:** the Object mesh
is added to the WALKMESH (form-1), so a raw copy is 3D collision you snag on → give the building tiles an *impassable*
topograph (`w_movementCheckTopographID`, ff9.cs:5769, a bit outside the on-foot `limit` mask) so you're blocked at the
perimeter; and a flat-based building on sloped terrain buries/floats → seat it on a `flatten_region` pad. A block with
NO stock Object mesh needs a small `s34` tweak (fire the Object override when `prefab.ObjectForm1==null`).

**Blender mesh-surgery round-trip** (`world/blendio.py`, ★ round-trip byte/geometry-exact): `world-mesh-export
--block X Y [--block …] --part object --out m.obj` writes the block(s)' sub-mesh to a Wavefront OBJ in WORLD coords
(UVs + normals preserved; several blocks line up so you can splice a multi-block structure — Alexandria is `[19][10]`
fragment + `[20][10]` keep). Edit in Blender (default OBJ axes, Y-up). `world-mesh-build m.obj --into-block X Y --part
object --topograph 59 --mod-folder <mod>` rebuilds it into that block's local frame + loose `.ff9mesh`, unindexing the
flat mesh and STAMPING a uniform IDALL (topo 59 = impassable — the right model for a solid building), then deploys via
the s34 Object override. Buildings are clean because their IDALL is uniform; per-triangle TERRAIN IDALL (walkmesh) is
the follow-up (needs a spatial re-derive or a Blender face-attribute sidecar).
