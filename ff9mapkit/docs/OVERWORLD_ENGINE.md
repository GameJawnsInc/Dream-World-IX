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
  `--no-seat`, `--replace-town`, `--topograph`, `--flatten-pad` for sloped ground).

**⚠ still needs an in-game playtest** (I can't see the game): the command reproduces the proven cell-(35,25)→Ice-Cavern
result byte-for-byte in the states it already covered, and now also covers `WORLD05/08`. See memory
`project-ff9-worldmap-feasibility`.

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
