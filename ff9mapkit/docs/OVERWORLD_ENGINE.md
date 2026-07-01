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
  his model, and flying gives flying *collision* without ascent (no actor swap). Works in any disc/story state.
  `gEventGlobal[102]` = a separate `wmID` used by `WorldConfiguration`.
- **Chocobo:** summonable on track topographs 3/18/21/22/28 (`w_frameChocoboCheck`) + Gysahl (event layer);
  `ff9.w_moveChocoboPtr` / `w_movePlanePtr`, availability via `originalActor.isEnableRenderer`.
- **Discs:** `WorldConfiguration.GetDisc()` = `ff9.w_frameScenePtr >= 11090 ? 4 : 1`; stored in `ff9.w_frameDisc`
  (== `gEventGlobal[0]`). Only **WorldDisc1** and **WorldDisc4** prefabs exist (discs 2–3 reuse disc-1 content).
  `WMWorld.SetDisc(1|4)` → `SceneDirector.Replace("WorldMapDebug", FadeOutToBlack_FadeIn)`. Switch via
  `ff9.w_frameSetParameter(501, 11090)` (→disc4) / `(502, 0)` (→disc1) — the stock `WMBeeMenu` pattern. It's a
  COARSE switch (doesn't advance ScenarioCounter/party), so a mismatched save can show wrong geometry.
- **Entrance dispatch** (RE'd 2026-06-30): walking an event tile fires `ff9.WorldEvent(cellX,cellZ,id)` which
  packs `num = 0x8000 | (cellZ<<8 & 0x3F00) | (cellX<<2 & 0xFC) | (id&3)`; `EventEngine.GetIP` matches `num`
  against the world `.eb` entry-table ids; the matched entry runs a 2-level switch (vehicle `gEventGlobal[190]`
  → on-foot AREA switch keyed on the tile IDALL area → ScenarioCounter branch) → `Field(dest)` (MAPJUMP 0x2B).
  **An overworld entrance is a world-`.eb` ENTRY keyed to a cell** — a tile's event bits only TRIGGER the lookup;
  editing tile IDALL cannot create an entrance. `ff9mapkit world-locate` decodes place→blocks→field; journeys
  re-point exits via `worldmap_inject`/`field_remap` (the world is one shared entity, not per-journey).
- **The game's own debug menu:** `WMBeeMenu` (the "Bee scene" = `WorldMapDebug`). Teleport buttons =
  `SetPosition(fixedPt) + w_movementChrInitSlice()`; disc = 501/502; change char = `WMScriptDirector.SetToNextChracter`.
  It is the ground-truth reference the F6 tools copy.

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
