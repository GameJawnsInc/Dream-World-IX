# Overworld (WorldMap / "WM") engine mechanics — Memoria/FF9

Reverse-engineered while building the **F6 overworld debug tools** (2026-07-01). It is all C# in the Memoria
engine (built from FF9's own game bytes), so every mechanic here is ultimately traceable — including the one
still-open problem at the bottom. Companion: the F6 menu lives in `Ff9mkDebugMenu.cs`; `ff9mapkit world-locate`
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

## OPEN PROBLEM — F6 overworld teleport reverts (UNSOLVED)
`SetActorPosition`/`SetPosition` moves the player; it holds ~2 render frames, then the player snaps back to the
**exact** prior position on the first logical tick and stays there. Exhaustively investigated 2026-07-01
(~16 engine builds with in-game stack-trace probes writing to `Memoria.log`):

- **Ruled out:** block-wrap (`BlockShift = 0` the whole time), autopilot (plane-only), navigation, renderer
  culling, camera event-aim (`ff9.GetEventAim()` == False), the `ProcessEvents` collision-revert (line ~79 —
  probe never fired), the world `.eb` `MoveToward` (it moves OTHER world actors — idx 18/20/21 — never the
  player), the `TranslatingObjectsGroup` parent (fixed at origin), and control state (reverts with control on OR off).
- **Definitive finding:** ungated stack-trace probes on ALL `WMActor` position setters (`pos`/`pos0`/`pos1`/`pos2`/
  `SetPosition`) fire for **every other actor but NEVER the player**, and there is no direct
  `transform.position`/`localPosition` write on the player anywhere in code. Yet the player's transform DOES move
  (parent fixed at origin ⇒ `localPosition` itself changes). So the writer leaves **zero C# footprint** → a
  Unity-native / animation binding re-asserts a *committed* position each frame. That committed store is NOT
  `originalActor.pos` / `lastx` / `transform` (all three get reverted **to** the prior value, not read from).
- **Next leads (for the resume):**
  1. Inspect the player's `WMActor` / `actor.go` GameObject for an `Animation`/`Animator` with **root motion**
     (Memoria's `WMActor.UpdateAnimationViaScript` samples `actor.go`'s `Animation`). If root motion drives the
     transform, that's the native writer — but it restoring an absolute *world* pos is odd, so verify.
  2. Find the hidden "committed position" the native driver reads each frame, and set it in the teleport (the
     thing to update is neither `pos[]`, `lastx`, nor the transform).
  3. Replicate the FULL board/place sequence including whatever `DefinePlayerCharacter` (event `CC`) /
     `w_movementChrConstructor` caches for the control actor.
- **Meanwhile:** the F6 **vehicle-swap → flying** mode reaches anywhere in any disc/state, which covers the
  original "reach an entrance under test" goal; the teleport button is kept as a WIP scaffold and marked as such.
