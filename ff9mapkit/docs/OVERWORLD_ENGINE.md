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

**★ Built (2026-07-02) — `world-rename-markers` (rename a marker's label).** The other minimap no-DLL win.
`GetTableText(0u)[locId+1]` reads world text **block 68** (shared by all WORLD00..12) txid-0, newline-split after
its `[TBLE=…]` tag — and `ParseTextSplitTags` **ignores the TBLE offset numbers** (`DialogBoxSymbols.cs:35-38`), so
renaming is a pure splice of the `locId+1`-th line (no offset math). `ff9mapkit world-rename-markers <cfg.toml>
--mod-folder <mod>` rewrites txid-0 and shadows it per-language into `FF9_Data/embeddedasset/text/<lang>/field/68.mes`
(`navimap.deploy_marker_renames`):
```toml
[[marker_rename]]
name = "Lindblum"      # or locid = 24 (a name renames EVERY slot it owns; South Gate = 6-10)
to   = "Falcon City"
```
Splices only the target line (other 63 names + all other txids byte-identical); `--lang all` (default) writes every
language, `--lang us` just one. RELAUNCH to apply. **★ in-game proven 2026-07-02** (renamed Lindblum → "Falcon City").

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

## Overworld weather / environment — `Environment.txt` (★ built 2026-07-02, no DLL)

`WorldConfiguration.PatchWorldEnvironment` (`WorldConfiguration.cs:93`) reads a per-mod-folder
`StreamingAssets/Data/World/Environment.txt` (FolderNames-stacked) that overrides the overworld's **mist / rain /
weather-light / world-effects / place alternate-forms** (+ the continent-banner rect). Line grammar
`^(Place|Effect|Mist|Disc4|Rain|Light|Title)\s+(.*)$`; each `[Condition=<expr>]` is **NCalc** (`using NCalc`), so
`true`/`false` force on/off and a modifier is active if ANY of its conditions holds (conditions may reference world
state via `NCalcUtility.worldNCalcParameters`). **Kit: `ff9mapkit world-environment <cfg.toml> --mod-folder <mod>`**
emits the file (`ff9mapkit/world/environment.py`, `build_environment_txt`/`write_environment`):
```toml
[world_environment]
mist  = false                    # force the Mist-Continent mist OFF (true = on; omit a key = engine default)
disc4 = "w_frameDisc == 4"       # NCalc condition passthrough

[[world_environment.rain]]       # -> Rain Add [Position] [RadiusLarge] [RadiusSmall] [RainSpeed] [RainStrength]
position = [700, -800]           # WORLD units (engine ×256 via ff9.S); the numeric params are optional
radius_large = 400
strength = 220

[[world_environment.light]]      # -> Light Add [Position] [Radius] [Light]
position = [900, -600]
light = 2

[[world_environment.effect]]     # force a WorldEffect on/off (AlexandriaWaterfall, SandStorm, WindShrine, Windmill…)
name = "AlexandriaWaterfall"
on = false

[[world_environment.place]]      # force a WorldPlace alternate-form (Alexandria/Cleyra/Lindblum destroyed, …)
name = "Alexandria"
on = true
```
Valid enum names: `environment.WORLD_PLACES` / `WORLD_EFFECTS` (baked from `Memoria/World/WorldPlace.cs` +
`WorldEffect.cs`). RELAUNCH to apply (parsed at overworld init). The `Title` token (banner rect/timing) is not yet
exposed. **★ in-game proven 2026-07-02** (`mist = false` forced the disc-1 Mist-Continent mist off).

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
NO stock Object mesh needs a small `s34` tweak (fire the Object override when `prefab.ObjectForm1==null`). **★ GOTCHA
(in-game 2026-07-02): an Object `.ff9mesh` override REPLACES the whole block's Object mesh — so deploying just your
structure WIPES the block's stock objects (trees, bridges, a town).** Use `world-mesh-build --keep-block` (or
`place_building(stock, new)`) to APPEND onto the stock mesh; `build_from_obj` now reports `replaced_stock_tris` and the
CLI warns when a plain deploy would delete stock geometry.

**Blender mesh-surgery round-trip** (`world/blendio.py`, ★ round-trip byte/geometry-exact): `world-mesh-export
--block X Y [--block …] --part object --out m.obj` writes the block(s)' sub-mesh to a Wavefront OBJ in WORLD coords
(UVs + normals preserved; several blocks line up so you can splice a multi-block structure — Alexandria is `[19][10]`
fragment + `[20][10]` keep). Edit in Blender (default OBJ axes, Y-up). `world-mesh-build m.obj --into-block X Y --part
object --topograph 59 --mod-folder <mod>` rebuilds it into that block's local frame + loose `.ff9mesh`, unindexing the
flat mesh and STAMPING a uniform IDALL (topo 59 = impassable — the right model for a solid building), then deploys via
the s34 Object override. Buildings are clean because their IDALL is uniform; per-triangle TERRAIN IDALL (walkmesh) is
the follow-up (needs a spatial re-derive or a Blender face-attribute sidecar).

## Walkable new land — RESHAPE, don't overlay (`world-terrain`, ★ in-game proven 2026-07-02)

`ff9mapkit world-terrain --mod-folder <mod> --radius R (--at X,Z | --ridge X0,Z0,X1,Z1) (--raise H | --lower H |
--flatten)` authors walkable terrain — a hill/crater/plateau or a ridge/valley (`world/terrain.py` → `deform_radial` /
`deform_ridge` / `flatten_region`). **The load-bearing lesson: RESHAPE the stock terrain verts; do NOT overlay a new
mesh.** Why (ground-follow RE): the player's Y is a **down-raycast from `player.y + rayStartOffsetY` (2.34375)** for
`rayDistance` (2.8) (`ff9.cs:7141` `w_nwpHit`), and the walkmesh only accepts **up-facing** triangles (`Dot(up, normal)
> 0.1`, `WMPhysics.cs:22`), and a per-frame **triangle cache** re-hits the player's current tri first (`WMBlock.cs:145`).
Net effect: a mesh *overlaid on top of* intact ground is **non-walkable** — the stock surface underneath keeps winning
the raycast (so an overlay is decoration/props, not ground you climb). Displacing the existing verts leaves a **single
walkmesh surface** → walkable. Three more facts baked into `world-terrain` (each a real bug hit + fixed): build in the
block's **LOCAL frame** (verts are local; a world-coord mesh lands off-block and is culled); **winding** must be
up-facing to match stock (`geom-normal Y ≥ 0`, else back-face-culled + walkmesh-rejected — seen through); the index
buffer (`flat_index`) IS the triangle list, so emit **fresh verts per triangle** (shared verts desync it → garbage
faces). And **multi-block**: a deform wider than one 64u block is applied to EVERY touched block with the SAME
**world-space** center/radius/amount, so shared block-edge verts move identically → **seamless** (else the hill is cut
at the grid boundary). Reshape keeps the stock texture + walkability topograph. ★ Proven: a seamless walkable grassy
hill across blocks (16,14)+(16,15).

## New continent — RECLAIM ocean cells as walkable land (`world-reclaim`, Path D · s34 extension · ★ in-game proven 2026-07-02)

The overworld is a **fixed 24×20 = 480-block grid where every ocean cell already exists as a real `WMBlock`** — it
just short-circuits to one shared `SeaBlockPrefab` (`WMWorld.cs:495` initial load + `:1180` streaming reload). So "new
continent" is **make designated ocean cells load land**, not mint a new world. `ff9mapkit world-reclaim --mod-folder
<mod> --cells "x,y;x,y"` (or a range `x0-x1,y0-y1`) synthesizes a fresh flat, textured, **walkable** terrain override
per sea cell (`world/terrain.py` `reclaim` → `mesh.flat_block_mesh` + `palette.apply_palette_uvs` → a loose
`Block[x][y] Terrain.ff9mesh`, deployed like any Terrain override).

**Why it needs an engine change (the make-or-break, RE'd over the WM source):** `block.IsSea` is read in EXACTLY two
places, both pure prefab-routing to `SeaBlockPrefab` — there is **NO** downstream movement / collision / encounter /
camera gate on it (walkability is 100% the mesh's `tangent.x` topograph, `WMBlock.Raycast@210`; `w_worldSeaBlockPtr` /
`HasSea` are dead code). But a sea cell short-circuits to `SeaBlockPrefab` — which carries only **Sea** forms, **no
`TerrainForm1`** (verified offline: block `[12][0]` has only `sea4`/`sea6` meshes) — *before* the s34 override hook can
fire. So on stock/current Memoria, dropping a Terrain override on an ocean cell is a **no-op**.

**The s34 extension (data-driven divert; `memoria-patches/s34-worldmap-mesh-override.patch`):** at BOTH sea call sites,
if `WorldMeshOverride.HasLandOverride(disc, x, y)` (a `File.Exists` check for the cell's loose `Block[x][y]
Terrain.ff9mesh`), route the cell onto a cached **plain land DONOR prefab** (`Block[12][10]` — has a `Terrain` child,
no town `Object`; null-guarded) instead of `SeaBlockPrefab`. `RegisterBlockComponent` then swaps our per-cell override
(keyed on the TARGET block's `InitialX/InitialY`, not the donor's) in as the cell's Terrain **render + walkmesh +
topograph**. `IsSea` is left untouched (harmless — the divert no longer consults `SeaBlockPrefab` for that cell) and
grid placement is `InitialX/InitialY`-driven, so the donor's own coords are irrelevant. BOTH sites must stay identical
or a reclaimed cell renders on first load then reverts to ocean after streaming out/back.

**Authoring facts (reuse the reshape stack):** the flat plane is built in **LOCAL** block space (x[0,64] z[-64,0],
Y=`height` default 0 = sea/coast level — real land bottoms out at Y=0), **fresh verts per triangle** (flat/unindexed),
**up-wound** so the *geometric* normal `Cross(v1-v0, v2-v0)` is +Y (the walkmesh up-facing filter uses that, NOT the
stored vertex normal — `WMBlock.cs:70` / `WMPhysics.cs:22`), `tangent.x = encode_id(topograph)` with **topograph 0 =
walkable plains** (the on-foot mask `0x0010667F/0xD8FF3CFF` admits 0/10/17/36…; **49/58/59 are BLOCKED** — 59 is the
building-footprint wall, NOT walkable, so do not use it for ground), and palette-stamped terrain-atlas UVs so it
textures like stock land. **Reachability:** a lone reclaimed cell is an ISLAND (the surrounding stock sea stays
non-walkable on foot) — prove render+collide with **F6 → World → Teleport** onto the cell's world center
(`x*64+32, -(y*64+32)`); ship on-foot reachability as a **contiguous bridge of reclaimed cells from the coast** (each
cell just needs its own override — the divert is per-cell/data-driven). This is the FOUNDATION of a true new landmass;
the remaining Path-D frontier is scale + a coastline/height pass + true new-continent geography.

★ **PROVEN 2026-07-02** (screenshot): a 2-cell strip (2,12)+(2,13) rendered as walkable grassy land, player stood +
walked on it, and was blocked at every sea seam (island behavior, as designed). **TWO lessons from the first run:**
(1) ⚠ **do NOT add a serialized field to `WMWorld`** — the donor cache field must be `[NonSerialized]`; a public field
broke the baked-prefab deserialization → NRE flood → overworld blackscreen (Unity's `output_log.txt`, not Memoria.log
— see `project-ff9-memoria-build`). (2) **`--height 0` z-fights with the sea surface** (the flat plane is coplanar with
the water → interlaced green/blue strips; functional but ugly). Deploy an open-ocean island at **`--height` a few units
above 0** to clear the wave plane. ⚠ Raising height under a STANDING player embeds them (down-ray from `player.y+2.34`
misses the higher surface) — teleport away + back (F6 re-grounds) after a height change, or set height before first
arrival. A coast-flush BRIDGE wants `--height 0` at the shore (matches the coast, which bottoms at Y=0).

### FAITHFUL coast — `world-coast` (place a REAL FF9 coastline, ★ in-game proven 2026-07-02, per-cell donor + F6 fix)

The synthetic `island` profile is a STYLIZED grass/sand slab; a real FF9 coast is layered **animated sub-meshes**
(`terrain` land + `sea3/4/5` water + a dedicated `beach1` sand/foam mesh driven by `WMRenderTextureBank` — NOT the
terrain atlas, which is why no terrain tile can reproduce the white foam). To author a *genuine* coast, CARRY a real
coastal block: `ff9mapkit world-coast --cells X,Y --donor dx,dy` copies the real donor block's terrain (real shape +
shore rim + UVs + walkable topographs) to the cell's Terrain override **and** writes a `Block[x][y] Donor.txt` sidecar
= `"dx,dy"`. **Engine (s34 per-cell donor):** the sea-cell divert calls `ResolveReclaimDonor` → `WorldMeshOverride.
TryReadDonorPath` reads the sidecar → loads THAT real coastal block prefab as the donor (cached in a `[NonSerialized]
Dictionary`; `LoadBlock` renders its `Beach1/Sea/foam` gated on `prefab.<field>`, not `block.Number`, so they carry
onto the cell), falling back to the plain inland donor (Block[12][10]) when no sidecar. ★ IN-GAME PROVEN 2026-07-02: a real beach +
foam rendered on cell (2,17) via a `Donor.txt`=`"18,15"` sidecar (per-cell, not a hardcode), faithfully walkable.
`ff9mapkit world-coast --list` browses the 44 real beach donors. ⚠ do NOT donor block 219 (Water Shrine — its form-2
sea is target-`Number`-gated). Trade-off: faithful land is a MOSAIC of real coast pieces (assembled from FF9's actual
coastline blocks), not an arbitrary outline — the next frontier is authoring coastlines from scratch.

**F6 teleport fix (bundled):** warping onto varied coastal terrain stranded the player under it — NOT a short re-ground
ray (`w_movementChrInitSlice` already sky-casts infinitely from +400u), but `w_nwpHit` early-returning `defaultHeight=0`
on a destination block not yet `IsReady` at warp time. Fix: `WMWorld.ForceLoadBlockReadyAt(pos)` force-loads the target
block (synchronous `LoadBlock` sets `IsReady`) before grounding. Observable only on a FAR/unstreamed warp.

### Custom graded OCEAN water — `world-water` (synthesize open water from scratch, validated 17/17 tile-shape, ★ in-game "looks good" 2026-07-05)

Where `world-coast` MOSAICS real coastline pieces, `world-water` **synthesizes** faithful open-ocean water from a depth
field — the "author water from scratch" frontier the coast section flagged. `ff9mapkit world-water --cells X,Y
[--deep S] [--donor 15,4]` deploys, per cell: a flat `Terrain` override at `Y≈0` (the s34 land-override GATE **and** the
cell's WALKMESH — see below), the three `Sea3`/`Sea5`/`Sea4` water sub-meshes at `Y=0`, blanked `Sea1`/`Sea2`, and a
`Donor.txt` naming a real deep-ocean block (same per-cell donor mechanism as `world-coast`). Code: `world/water.py`
(algorithm + orchestration) + `mesh.tri_soup_block_mesh`/`hidden_block_mesh` (the render-sub-mesh + blanking primitives).
**Requires the custom engine (s34); RELAUNCH.**

**Walkmesh / boat traversal (RE 2026-07-06, source-confirmed).** On a reclaimed cell the `Terrain` override is registered
BEFORE the Sea meshes (`WMWorld.LoadBlock` order) so it WINS the walkmesh raycast (`WMBlock.Raycast` iterates
`ActiveWalkMeshes` and returns the first mesh hit). So the `Terrain` override IS the cell's walkmesh, and its Y +
topograph are the levers. Real ocean has NO terrain — its Sea meshes at `Y=0` carry a SEA topograph (sea3=54 shallow,
sea4=57 deep, IDALL `tangent.x` bits 2-7) and ARE the walkmesh; a BOAT (movement mode 7) is a surface follower whose
`Y` = the raycast hit (`w_nwpHit`→`w_cellHit`, no default-height fallback on a ready cell), and its traversal mask
`{0x02600000,…}` admits topographs 53/54/57 while ON-FOOT (mode 0) + chocobos are BLOCKED on water (mask
`{0x0010667F, 0xD8FF3CFF}`). So `world-water` sets the `Terrain` walkmesh to `Y=-0.1` (`WATER_Y` — just below the `Y=0`
water render, so a boat floats ~at the surface with the model visible; hidden under the opaque water → no z-fight; `0`
z-fights, a bigger negative sinks the vehicle — tune with `--height`) carrying `topograph 57` (`WATER_TOPOGRAPH`,
`tangent.x=228`). Result: a boat sails on top / on-foot is blocked — real ocean. (Before this: `Y=-3`/topo-0 = a land
floor UNDER the opaque water, so travel happened submerged with the character hidden.) **Test with a boat** (F6 → World
→ vehicle swap to Blue Narciss if you don't have one) from a NON-parked-on-the-cell save — changing the topograph under
a parked on-foot actor risks the "no controlled actor" brick → [[project-ff9-overworld-actor-brick]].

**The byte-derived recipe** (surveyed across all 15 disc-1 open-ocean blocks; tile-for-tile 17/17 shape-match vs the
real game; the only per-cell difference is a corner seam-variant the game itself coin-flips 50/50):

- **Alphabet = 3 shades.** Open ocean uses ONLY `Sea3` (light/shallow) / `Sea5` (transition) / `Sea4` (dark/deep).
  `Sea1`/`Sea2` are COAST-only (0 of 3583 surveyed open-ocean tiles) → blanked (a buried degenerate tri), else they
  read as misplaced river tiles.
- **Placement = a MARCHING BAND.** Sample the depth field at each 4u sub-tile's four EDGE MIDPOINTS **in WORLD
  coordinates**; an edge is "deep" if `depth > threshold`. 0 deep → `Sea3`; 4 → `Sea4`; 1–3 → a `Sea5` transition.
  Because the samples are the SHARED cell-edge midpoints, neighbours agree by construction → `Sea3` can never touch
  `Sea4`, seams line up, **and this holds ACROSS block boundaries** (adjacent cells sample the same world edges) → a
  contiguous multi-cell region is seamless. This world-space sampling is the one real generalization over the single-
  block scratch prototype.
- **Transition UV = a Wang tile** keyed by which edges face deep (`DEEPSET2TILE`): 1 deep → a "tip" v-strip rotated to
  point at the deep side; 3 deep → a strip pointing at the lone shallow; 2-adjacent (a corner) → one of two seam-
  variants; 2-opposite (a channel, no Wang tile) → degrade to the deepest single edge.
- **Mains UV = quadrant + 4-rotation anti-tiling.** `Sea3`/`Sea4` pick one of the texture's 2×2 quadrants (parity flip
  ~68% between neighbours) and one of **4** rotations (prefer-same ~45%) — the real caustic shuffle. **Depth is carried
  by WHICH SHADE, never by orientation.**

Byte-exact constants (reconstructed from real block (8,4), in `world/water.py`): `URECT`/`VRECT` (mains quadrant),
`UFULL`/`VSTRIP` (transition full-width-u × quarter-strips-v), `NORMAL = (-0.12, 0.98, 0.17)`. The mesh is **position +
UV only** (the `WorldMap/Terrain` shader binds only vertex + texcoord — normals/tangents are irrelevant to water
rendering, so a single byte-proven normal is stamped everywhere). Depth is caller-controlled with two built-in fields
(or pass your own `depth(world_x, world_z)` callable — a hand-authored map / real contour): the DEFAULT (no `--deep`)
is **faithful open ocean** (`open_ocean_depth_field` — mostly deep, ~94% Sea4 like real FF9 open water, with a
`--shallows`-fraction scatter of coherent shallow patches, each ringed by transition; `--shallows 0` = uniform deep
Sea4); a direction `--deep N/S/E/W` opts into a **graded shallow→deep RAMP** (`default_depth_field`, for a coast/bay;
`--threshold`/`--span`/`--noise`). Anti-tiling is seeded per cell from `(--seed, x, y)` so a region doesn't macro-repeat;
the shade PLACEMENT is seed-independent (set by depth).

**Hard-won lessons (do NOT relitigate — offline rendering + marginal statistics CANNOT judge water quality; both of
these were invisible to them and found only by UV byte-analysis + the human's in-game read):** (1) real ocean uses all
**4** rotations of each quadrant, not just 0/180 (a generator doing only 0/180 is wrong on ~46% of tiles, invisible to
stats); (2) the transition tile identity is the deep-edge-SET, not a shallow/deep depth bias (that heuristic regressed).
Validate everything against a verbatim real block; don't declare victory before the human confirms in-game. **Two A/B
references are built in** (both keep the identical deploy shape — flat Terrain gate + Sea3/Sea4/Sea5 + blanked
Sea1/Sea2 + donor sidecar — so only the water differs):
  * `world-water --cells X,Y --verbatim [BX,BY]` deploys a REAL open-ocean block (default `8,4`, the byte-proven block
    the synth was validated 17/17 against) VERBATIM — the north-star, isolating SYNTHESIS from the deploy pipeline
    (`water.deploy_verbatim`).
  * `world-water --cells X,Y --reproduce [BX,BY]` reads that block's shallow/deep LAYOUT and regenerates it through the
    synth mesh pipeline (`water.reproduce` → `arrangement_from_block`: same shade grid + fresh mains anti-tiling). Each
    Sea5 transition tile is read from the block's ACTUAL UVs — the exact `(strip, rotation)` **and** its real v-band
    rect (`read_sea5_tiles`/`_fit_tile`, the fit that scored 17/17) — so a thin peninsula comes out right, not
    guessed from neighbour shades (that shade heuristic, `_repro_deepset`, is only the fallback for the rare
    transpose tile a pure rotation can't represent). Deploy it beside `--verbatim` of the same block — they should look
    alike. This holds the LAYOUT fixed (a real block's) so the only variable is tile quality — the in-game form of the
    offline 17/17.
**In-game loop:** relaunch → F6 → World → Teleport to the cell centre (`x*64+32, -(y*64+32)`; the proven demo cell
(3,17) → `224, -1120`). Remaining frontier: seam-match the corner variant via the connective-adjacency rules instead of
the 50/50 coin-flip (cosmetic — the game itself coin-flips it).

## Overworld texturing — the model + the learned UV palette (RE 2026-07-02)

**The atlas is global + shared, not per-block.** The overworld's terrain uses ONE **1024×1024** atlas
(`WMConstants.cs:83-85`) bound to the single static `WMWorldPrefabMaker.TerrainMaterial`; `LoadMesh` gives *every*
block's Terrain mesh that same material (`WMWorldPrefabMaker.cs:193`). Buildings/props use a paired global **Object**
atlas (`ObjectMaterial`). A block's mesh selects *which tile* it draws purely by its **per-vertex UVs** (normalized
0–1; `pixel = uv × 1024`). Beyond those two there are ~9 special materials (Beach/River/Stream/Falls/Sea1-6/Volcano),
some **animated** by `WMRenderTextureBank` (frame-swap or `_Offset` scroll) — those are hardcoded per-material in C#.
The static atlas textures load through `WMBlock.LoadMaterialsFromDisc` → `AssetManager.SearchAssetOnDisc`, which checks
**mod paths first** (`WMBlock.cs:290-297`) — so an atlas PNG in the mod folder wins (Moguri's HD-reskin hook).

**Topograph does not select the texture — but it *correlates* with it.** Texture is chosen only by UV; the
per-triangle `topograph` (`tangent.x` IDALL) drives walkability/encounters. Empirically, though, real faces of the
same topograph reuse a small, stable set of atlas tiles (probed across blocks; the *same* tile UVs recur block after
block), so topograph is a usable **key for a learned UV palette** — with the caveat that some topographs are broad
buckets (topo 49 spans many tiles), so the robust unit is "a real donor face's UV triplet," modal tile as default.

**No-DLL feasibility — three tiers:**
- **T1 — reuse existing atlas tiles via UVs (★ IN-GAME PROVEN 2026-07-02, no DLL).** Learn `topograph → real donor UV
  triplets` from shipping blocks; stamp them onto new/UV-less faces (which otherwise carry `[0,0]` = the atlas corner,
  which is a **blank white** tile). ★ Proven: a small test box stamped with a real Alexandria wall tile (UV ≈0.58,0.45)
  rendered the masonry wall in-game, side-by-side with a plain `[0,0]` box that rendered solid white. `world/palette.py`:
  `build_palette` (cached per disc/part) · `pick_uvs` · `apply_palette_uvs` (per-triangle, only zero-UV faces).
  `world-mesh-build --texture` applies it (covers a UV-less Blender model + the `add_solid_base` hull);
  `world-texture-palette` inspects it. **Tiling caveat:** a real tri's UV rect is ~5-6% of the atlas, so a donor
  triplet is stamped PER TRIANGLE — don't stretch one tile across a big face. **The modal is always a REAL tile**
  (probed: 0/2604 terrain and 0/1219 object palette tiles are transparent — real faces carry real UVs; the white
  box in testing was the *no-palette* `[0,0]` default, which is a transparent atlas corner, not a palette pick). So
  the picker below is for choosing *which* real tile (a wall vs a road vs bark), not for avoiding white.
- **The atlas + tile PICKER (★ built).** `world/atlas.py` extracts the two shared **1024×1024 RGBA** atlases
  (`res(1_24)_terrain`/`_objects`, p0data3; `WMBlock.cs:312-315`) — resolving the object-atlas dimension (also 1024²).
  `world-atlas-extract` dumps the PNG; `world-atlas-catalog` renders a contact sheet (each topograph's real donor
  tiles as labeled `TOPO:VARIANT` thumbnails); `world-mesh-build --tile TOPO:VARIANT` forces the picked tile on all
  new faces (e.g. `--tile 52:0` = a castle wall). Blank tiles (should any exist) are detected by **alpha** (the
  transparent-white `[0,0]` corner) via `atlas.tile_is_blank`/`filter_blank` (opt-in `build_palette(skip_blank=True)`).
  UV→pixel is `(u·1024, (1-v)·1024)` (Unity V is bottom-up).
- **T2 — HD atlas reskin (★ deploy built, no DLL; repaint is the art task).** `world-atlas-extract` → repaint the PNG
  (same UV layout) → `world-atlas-reskin` deploys it to `<mod>/StreamingAssets/assets/resources/worldmap/textures/
  res(1_24)_<terrain|objects>.png` (the `SearchAssetOnDisc` mod path, `AssetManager.cs:804`, checked before the
  embedded asset). Replace the *pixels*, keep the *tile positions*, and all existing geometry reskins for free.
- **T3 — genuinely new atlas content (★ pipeline built 2026-07-02, no DLL).** FF9's atlases have ample UNUSED
  (fully-transparent) space — **124 free 32px cells in terrain, 373 in object** — so a *new* appearance goes into a
  free region of the EXISTING atlas (no new material needed). `world-atlas-add-tile <tile.png>` finds a free gap
  (`atlas.find_free_region`), composites the tile with a **1px UV inset** (dodges the configurable bilinear bleed,
  `WMBlock.SetTextureFilterMode`→`WorldSmoothTexture`), deploys the reskin, and prints the UV rect; then
  `world-mesh-build --tile-uv Umin,Vmin,Umax,Vmax` stamps that region on custom geometry (`palette.stamp_uv_rect`).
  ★ Proven the pipeline end-to-end offline with a magenta test tile (rendered on a box, forest/bridge kept via
  `--keep-block`); the *art* (a nice tile) is the human's, the plumbing is done. (A genuinely SEPARATE atlas — vs a
  free-region add — would need a new material entry in the code-hardcoded `ObjectNameToPaths`, `WMBlock.cs:310`; the
  free-region route avoids that entirely.)

Open: the atlas tile-grid pitch is inferred (~5-6%/tri), not read from a constant; the palette is disc-1-derived
(per-disc rebuild if the mapping differs). (Resolved: object atlas = 1024² like terrain; atlas lives in p0data3 as
`res(1_24)_*`; the extract/catalog/reskin tools are built.)

## Overworld encounters + the world-pack binary (RE 2026-07-02)

The last un-RE'd overworld data system. Fully traced through the Memoria C# (5-finder workflow + a direct
cross-check of every load-bearing line). Two halves: a **baked binary table** (which monsters, keyed by
terrain) and a **live per-frame trigger** whose *rate* the world `.eb` itself pokes.

### The world-pack container (`discmr.img`)

All native overworld tables live inside one asset per disc — `w_fileImagename[0]` =
**`WorldMap/wmap/disc1/discmr.img`** (disc-4 twin `…/disc4/discmr.img`, `ff9.cs:353-367`). It is a **two-layer
container**:

1. **Sector TOC** — the first 2048-byte sector is a table of `w_fileImageSectorInfo[]` `{start, length}` records
   (each in 2048-byte disc sectors), read at `ff9.cs:3626`.
2. **The pack** — section **index 1** (`w_fileImageSectorInfo[1]`) is read into the fixed **92160-byte**
   `w_memorySPSData` buffer (`ff9.cs:8676`). This buffer is itself a **pointer-table pack**: `w_framePackExtractPosition(data, no)`
   (`ff9.cs:4267`) reads `count = ReadInt32(@0)`, then returns `ReadInt32(@ 4 + no*4)` = the absolute byte offset of
   sub-table `no`. `w_framePackGetPtr_*(data, no)` seeks there and deserializes.

Sub-table indices (`kWorldPack*`, `ff9.cs:9591+`): **3 = EncountTable**, **4 = EncountSpecial**, 0 EffectAreaBin,
1 ChocoboPal, 2 PaletVolcano, 5 ColorTable(weather), 6 AnimationTable(texture scroll), 7 SpsData, 41 EffectBin,
53-65 the named world SPS effects, **66 = ModelSea** (the `sNWBBlockHeader` sea geometry).

**Load path is mod-overridable.** `FF9Pc_SeekReadB` reads via **`AssetManager.LoadBytes(fileName)`** (`ff9.cs:2476`)
— the same FolderNames-stacked path every other mod asset uses. So a mod folder that ships a replacement
`WorldMap/wmap/disc1/discmr.img` is honored. (Caveat: it's whole-file replacement of a two-layer binary, so it
needs a kit codec — see feasibility.)

### The 355-record encounter table (`EncountData`)

`w_frameBattleScenePtr` = pack sub-table 3, an array of **355** `EncountData` (`ff9.cs:8698`;
`WMBinarayReaderExtension.cs:82-94`). **Packed record = 10 bytes** — the reader is sequential, no alignment padding:

```
UInt16 scene[4];   // 8 B — battle-scene ids (scene[3] = the special/friendly variant, see below)
Byte   pattern;    // 1 B — topographId = (pattern >> 2); low 2 bits = scene-slot select
Byte   pad;        // 1 B — hasFog = (pad & 1); (pad >> 1) = reserved
```

(355 × 10 = 3550 B. Two workflow readers reported 6 and 12 — both wrong: 6 was a miscount, 12 is the C# managed
`sizeof` with struct alignment. The **binary stride is 10**.)

**Record selection — `w_worldGetBattleScenePtr()` (`ff9.cs:9079`):** it is keyed by **zone × topograph × fog**, not
a flat area lookup:
1. `zoneId = w_worldArea2Zone(area)` (`w_worldAreaZone[]` LUT); the table is sliced per zone by the CSR array
   `w_worldZoneInfo[zoneId .. zoneId+1]` (a `Byte[26]`, built at load from `w_worldZoneFigure[zone]*2`, `ff9.cs:8666-8675`).
2. Within the slice, pick the record whose **`(pattern>>2) == m_GetIDTopograph(actor)` AND `(pad&1) == w_frameFog`**
   (`ff9.cs:9093`). So the *same* terrain gives a different monster set with mist up vs down.
3. **Disc-4 alternate band:** if `w_frameDisc==4 && i<100`, it returns `w_frameBattleScenePtr[i + 254]` instead
   (`ff9.cs:9095-9100`) — the disc-4 monster re-table lives +254 records up in the same array.

### The per-frame trigger — `.eb`-driven

> ⚠ **Correction (in-game 2026-07-02):** `case 205` below is a world-`.eb` sysvar and its `w_frameEventBattleProb`
> denominator IS the proven *rate* lever — but its `topograph∈[36,38]` clause is **not** "the only tiles that fire."
> Battles were observed on other topographs; the operative trigger is the EventEngine step-accumulator
> `ProcessEncount` (`EventEngine.ProcessEvents.cs:462`). Read the clause below as *one* gate, not the whole story.

The trigger is **polled by the world `.eb`** as GET-sysvar **case 205** (`ff9.cs:4235`), i.e. it lives in the 13
world dispatchers, not a hidden native loop. Fires (returns 1) only when **all** hold:

- `w_frameEncountEnable` (armed from `w_frameEncountMask` when the vehicle's `encount` flag is set, the player is
  moving, topograph≠52, and no title banner — `ff9.cs:5380`),
- `w_moveCHRControl_Move` (position changed this frame),
- **topograph ∈ [36,38]** (the encounter-eligible land band),
- `w_frameCounter > 400` (post-load settle), and the HUD is not FullMap,
- the RNG roll hits: `((random8()<<8 | random8()) % (w_frameEventBattleProb+1)) == 1` → **per-frame p = 1 / (w_frameEventBattleProb+1)**.
- Short-circuit above all of it: `FF9StateSystem.Settings.IsNoEncounter` → always 0.

**The rate is authorable with NO DLL and NO codec:** `w_frameEventBattleProb` is a `UInt16` (`ff9.cs:10088`) set
by the world `.eb` via **SET-sysvar case 26** (`ff9.cs:3920`). Each dispatcher pokes it as you cross regions — so
editing the world `.eb`'s case-26 writes (the same surface we already author for `world-entrance`) re-tunes the
overworld encounter rate per zone. Danger-level = *just this denominator*.

### Special / friendly encounters (`sworldEncountSpecial`)

Pack sub-table 4 = **9** records of `{ UInt16 area[12] }` (24 B each, 216 B; `ff9.cs:11321`,
`WMBinarayReaderExtension.cs:144`). A non-zero `area[j] = N` is a **1-based index** into the 355-table
(`w_frameBattleScenePtr[N-1]`); `0` = empty slot. At world init a bitmask from **event-globals 194 & 198** selects
which of the 9 records are active (`ff9.cs:8892`); each active record's target rows get `scene[3]` overwritten with
their own `scene[2]` (`ff9.cs:8900`), and every active `scene[3]` is added to `w_friendlyBattles` (`ff9.cs:8706`).
When `SettingsState.IsFriendlyBattleOnly`, `SelectScene()` filters encounters to that set. **The 9 records are the
9 FRIENDLY-MONSTER sidequest creatures** (user-confirmed, 2026-07-02): `0` Mu · `1` Ghost · `2` Ladybug · `3` Yeti
· `4` Nymph · `5` Jabberwock · `6` Feather Circle · `7` Garuda · `8` Yan — each record's `area[12]` = the overworld
areas that creature roams, and event-globals 194/198 are the quest-progress bitmask of which are currently
placeable. The `scene[2]→scene[3]` swap makes the friendly creature the encounter's overriding scene where its
areas match. (Still open: exactly when 194/198 flip along the quest.)

### Battle handoff

Trigger → `ff9worldInternalBattleEncountStart()` (`WMScriptDirector.cs:154`, sets the state attrs) →
`SelectScene()` picks a `scene[]` slot → the id lands in `FF9StateWorldMap.nextMapNo` (an `Int16` that here holds
a **battle-scene id**, not a map no) → BGM via `FF9SndMetaData.GetMusicForBattle(BtlBgmMapperForWorldMap, wldMapNo,
nextMapNo)` (`WMScriptDirector.cs:208`; the mapper is a `(worldMapNo → (battleSceneId → songId))` dict loaded from
`EmbeddedAsset/Manifest/Sounds/WldBtlEncountBgmMetaData.txt`) → `SceneDirector.Replace("BattleMap", SwirlInBlack)`
(`WMScriptDirector.cs:222`).

### No-DLL feasibility (what this unlocks)

| Lever | Cost | Notes |
|---|---|---|
| **Encounter *rate*** | ★ **BUILT** (`world-encounter-rate`) — free, no DLL/codec | rewrites the world `.eb` SET-sysvar case-26 writes (`w_frameEventBattleProb`) — same surface as `world-entrance`. See below. |
| **Per-vehicle encounter on/off** | free | `TransportControls.csv` col 12 (`CsvParser.Boolean`), already patched by `WorldConfiguration.PatchWorldCHRControl`. ⚠ the two airships hold **22/23** in that Boolean column — unexplained (open q). |
| **Re-table which monsters spawn where** | ★ **BUILT** (`world-encounters`) — no DLL | edits `EncountData.scene[]`/`pattern`/`pad` in place + deploys a whole-file `discmr.img` mod override (`AssetManager.LoadBytes` honors it). See below. |
| **Clean CSV authoring seam** | small DLL patch | a `Data/World/WorldEncounters.csv` + `PatchWorldEncounter()` mirroring the existing 3 world patchers (`DataResources.cs` exposes only TransportControls/WeatherColors/Environment today; no encounter hook). s23–s33-class change. |
| **Friendly/special-zone authoring** | research | via event-globals 194/198 + the 9 special records; blocked on the open questions. |

**Correction vs the first-pass verdict:** re-tabling monsters is *not* impossible without a DLL — the `.img` loads
through the mod-override path, so a whole-file repack works; only a *targeted patch* needs the engine seam. And the
encounter *rate* is already free via the world `.eb`.

### `world-encounter-rate` — retune the rate (★ in-game proven 2026-07-02, no DLL)

`ff9mapkit world-encounter-rate --mod-folder <mod> [--multiplier F | --set PROB | --peaceful]` (`world/encounter.py`).
It rewrites every immediate `RunWorldCode(26, value)` write in the world dispatchers' `.eb` — probed empirically as
**exactly 18 writes**: the 9 free-roam states (9000/02/03/05/07/08/09/10/11) each carry 2 (entry-0 tag-0 `Main_Init` +
entry-0 tag-10 `Main_Reinit`); the 4 cutscene states carry none. The game ships only two danger values, `prob 231`
(p=1/232, standard) and `prob 365` (p=1/366, the gentler disc-1 `Main_Init` rate that normalizes to 232 after the first
battle). `--multiplier` is an encounter-**frequency** scale (2.0 = twice as many; it divides the period `prob+1`,
preserving the game's relative danger and staying idempotent by always deriving from the pristine dispatcher);
`--set` forces an absolute `w_frameEventBattleProb`; `--peaceful` sets `0xFFFF` (≈no encounters). Deploy is a
per-language `.eb` shadow (the writes are language-identical in count, JP at different offsets) that STACKS on any
`world-entrance` edit (reads the mod-folder override if present). RELAUNCH / re-enter the overworld to apply.

### `world-encounters` — re-table the monsters (★ IN-GAME PROVEN 2026-07-02, no DLL)

**★ Confirmed in-game 2026-07-02:** setting **all 355 records** to one scene (`[[set]] all = true`) made every
overworld battle the identical fight (scene 359 = Mist-Continent Pythons/Goblins on the forest BG), everywhere on
the map — so the `discmr.img` override *loads* and the codec is byte-correct. **Targeting lesson (the thing that
first fooled the test):** record SELECTION is **zone-slice-primary** — `w_worldGetBattleScenePtr` (`ff9.cs:9079`)
scans only the current *area*'s slice of the table (`w_worldZoneInfo[zone..zone+1]`), matches `topograph` + `fog`
within it, and **falls back to the slice's last record** when nothing matches. So a `topograph=`-only edit can miss
the record that actually fires (its zone had no topograph match → the fallback record, a different topograph, fired).
Use `all = true` for a uniform overworld, target a specific record `index`, or — the proper surgical lever — scope
by **`area`/`zone`** (below). Also note the operative encounter TRIGGER is the
EventEngine step-accumulator `ProcessEncount` (`EventEngine.ProcessEvents.cs:462`: `_encountBase += encratio` →
`random8() < _encountBase>>3` → `SelectScene`→`w_worldGetBattleScenePtr`), **not** the `case 205` topograph-36–38
gate I first fixated on (that gate is a separate world-`.eb` sysvar path; empirically battles fire on other
topographs too). The *rate* lever (`w_frameEventBattleProb`) is still real + proven — just don't read the
`case 205` topograph clause as "the only tiles that fire."

`ff9mapkit world-encounters --list [--all] [--disc 1|4]` inspects the table; `--config <toml> --mod-folder <mod>
[--disc N] [--dry-run]` edits + deploys (`world/worldpack.py`). The `Discmr` codec parses the two-layer container
(sector-TOC → pointer pack) and edits the 355 `EncountData` **in place** — re-tabling only changes record *values*,
never counts, so it rewrites the 3550 encount bytes at their absolute offset and leaves the 2 pad bytes + every
other pack section verbatim (`Discmr(x).to_bytes() == x` for an unedited image, proven on both discs). The edit
config: `[[set]]` matches by `index` or `topograph` (+ optional `fog`) and sets `scene` (a 4-list or per-slot
`scene0..3`) / `pattern` / `pad`; `[remap]` swaps a battle-scene id for another across every slot (e.g. "replace
formation 358 with 999 everywhere"). Deploy writes a **whole-file** `discmr.img` override at
`<mod>/StreamingAssets/assets/resources/worldmap/wmap/disc{N}/discmr.img.bytes` (the `AssetManager` bundle-branch
path, `AssetManager.cs:593` → `Assets/Resources/…​.bytes`, case-insensitive; the same convention the `.eb` overrides
use). Disc 1 and disc 4 have separate tables (disc 4 also backs the `i+254` alternate band); edit both to fully
re-table. RELAUNCH to apply (it's a bundled asset, not F6-reloadable).

**The zone/area layout (the selection key — ★ IN-GAME PROVEN 2026-07-02).** A zone-0-only edit (`[[set]] area = 0`)
changed *only* the Alexandria/Mist start (F6 `area` 0/1 → uniform scene 359) while every other region kept its normal
encounters — confirming area → zone → table-slice end-to-end. The 355 records are laid
out **zone-by-zone**. Two hardcoded engine LUTs (baked into `world/worldpack.py`): `w_worldAreaZone` (`ff9.cs:1348`)
maps each overworld **area** (0–63, the 6-bit `m_GetIDArea` tile field the F6 World tab prints) → one of **25 zones**;
`w_worldZoneFigure` (`ff9.cs:1415`) gives each zone its count of topograph entries (×2 fog twins = its record count).
The CSR `zone_info[z] = 2·Σ figure[0..z-1]` places zone `z` at records `[zone_info[z], zone_info[z+1])`. The disc-1
zones sum to exactly **254 records (0–253)** — which is precisely why the disc-4 alternate offset is `+254`
(`ff9.cs:9095`): records 254–354 are the disc-4 band. So the authoring flow is: stand where you want to change
encounters → read `area` off F6 → `[[set]] area = N` (or `zone = Z`), optionally `+ topograph/fog` to narrow within
the slice. `world-encounters --zones` prints the whole `zone → areas → record-slice → topographs` map. Example: zone 0
(areas 0,1 = the Alexandria/Mist start) = records 0–5, topographs {0,13,37} — record 4 (topo 37) is scene 359, the
grass encounter proven above.

### Open questions (confirm before building an authoring feature)

- ~~Confirm the 10-byte stride against real bytes~~ → **confirmed** (`world/worldpack.py` parses both discs, span
  off[3]→off[4] = 3552 = 355×10 + 2 pad; round-trip identity holds).
- ~~Whether the kit needs an `.img` codec~~ → **built** (`world/worldpack.py`).
- The exact `m_GetIDArea` mask (reported `(IDALL & 0x3F00)>>8`).
- The 9 special records are the **Friendly-Monster** creatures (resolved above). Still: when **event-globals
  194 & 198** flip along the sidequest.
- The airship **encount = 22/23** in a Boolean-parsed CSV column — rate? mask?
- **In-game**: confirm the `discmr.img` mod-override path takes (the codec is byte-proven offline; the override
  path is derived from `AssetManager` source, not yet in-game verified) — and that disc 1 vs disc 4 both need editing.
