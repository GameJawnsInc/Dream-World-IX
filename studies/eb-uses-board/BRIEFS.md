# Background briefs

The four briefs every idea agent was given, verbatim. Written by agents reading this repo on 2026-09-19 (before the 54-commit master catch-up), so line numbers may have drifted. [← index](DOSSIER.md)


---

# Brief: Opcode + expression surface

# FF9 `.eb` OPCODE + EXPRESSION SURFACE — COMPLETE INVENTORY

Sources read: `ff9mapkit/ff9mapkit/eb/_optables.py` (tables baked from Memoria `EventEngineUtils.opArgCount/opArgSize` + `EventEngine.DoEventCode.cs` names), `eb/opcodes.py` (encoder + verified docstrings), `eb/disasm.py` (byte reader), `eb/_exprtable.py`, `eb/_membertable.py`, `eb/exprsem.py`, `eb/exprasm.py`, `eb/_regen_optables.py`. Cross-checks: `studies/minigame-ui/SURVEY.md`, `studies/movement/SURVEY.md`, `studies/messages/SURVEY.md`, `ff9mapkit/ff9mapkit/journal.py` (sysvar/memoria-var bounds), `world/encounter.py`, `content/region.py`.

Notation per row: `op  Mnemonic(argwidths)` — widths are bytes per operand from `OP_ARG_SIZE`; `var` = operand count read from the stream; `*` = **flow terminator** (path ends, `adFin()`); `‡` = **exotic / rare** (detailed in §14). Rows marked `[unnamed]` have table entries but no name in Memoria's `DoEventCode` case comments — decoded surface nobody in this repo has spent.

---

## 0. WIRE FORMAT (what every line costs)

```
[0xFF] op                       ; 0xFF selects the extended page (op |= 0x100)
[argFlag:u8]                    ; ONLY if op >= 0x10 AND argc != 0
operand0 .. operandN            ; LE immediate of width OP_ARG_SIZE[op][i]
                                ;   OR, if argFlag bit i is set, an RPN token blob ending 0x7F
```
- **argFlag bit index == OPERAND index**, consumed left to right (`EventEngine.cs:1331-1362`). Any operand of any opcode can be an expression. This is the single most under-used fact in the whole ISA: ~every opcode in this document is secretly *computed-argument capable*.
- `op == 0x05` is forced `argFlag = 1` by the reader — it is the bare "evaluate an expression" statement (the SET/selector-push).
- Variable-count ops: `0x06` (`1 + 2n` operands), `0x0B` (`2 + n`), `0x0D` (`2 + n`, 2-byte count), `0x29` (`n` × 4-byte).
- `argsize` overrides: `0x29 → 4` per operand; `0x06/0x0B/0x0D → 2`.
- Immediates are **width, not signedness** — both readings are legitimate per opcode (`opcodes._imm` accepts the union window and refuses anything outside it rather than masking).

---

## 1. FLOW / SCRIPT CONTROL

| op | mnemonic | notes |
|---|---|---|
| 0x00 | `NOTHING()` | NOP |
| 0x01 | `JMP(rel:2)` | unconditional; **signed** int16 relative to `instr.end` |
| 0x02 | `JMP_IFNOT(rel:2)` | tests the value pushed by the preceding `0x05`; skip read **UNSIGNED** (a backward JMP_IFNOT becomes a huge forward target) |
| 0x03 | `JMP_IF(rel:2)` | signed int16 |
| 0x04 | `RET()` * | level-0 return drives `ExitBattleEnd` |
| 0x05 | `SET(expr)` | pushes/evaluates one expression; the selector-push before a switch, and the assignment statement (`B_LET` inside) |
| 0x06 | `SWITCHEX(var×2)` | explicit (value, reloffset) pairs + default; anchor `off+4` |
| 0x0B | `SWITCH(var×2)` | contiguous range: `base = sx_hi(a[0])`, default `a[1]`, then n case reloffsets; anchor `off+1` |
| 0x0D | `SWITCH2(var×2)` | 0x0B with a 2-byte case count; anchor `off+2`. **Zero ship** — by-construction only |
| 0x0A, 0x0C, 0x0E, 0x0F | `[unnamed]` 0-arg | four free zero-operand slots in the flow band |
| 0x1C | `TerminateEntry(1)` * | 255 = "This". Deactivates an entry / switch zone |
| 0x22 | `Wait(1)` | frame wait |
| 0x4F | `[unnamed]` `STOP(1)` * | terminator per `TERMINATOR_OPS`, name never parsed |
| 0x97 | `ReturnEntryFunctions(1)` | |
| 0xF5 | `GameOver()` * | |

All 5,563 switches across the 676 shipping fields decode 100% boundary-aligned with this model.

## 2. ENTRY / DISPATCH / OBJECT LIFECYCLE

`0x07 InitCode(1,1)` · `0x08 InitRegion(1,1)` · `0x09 InitObject(1,1)` — arm an entry as code / region / positional object.
`0x10 RunScriptAsync(1,1,1)` (REQ, fire-and-forget) · `0x12 RunScript(1,1,1)` (REQSW, concurrent) · `0x14 RunScriptSync(1,1,1)` (REQEW, blocks) — all `(level, uid, tag)`, target **by UID** (250 = control character).
`0x16/0x18/0x1A RunScriptObject{Async,,Sync}(1,1)` — the object-indexed twins; **not modeled by cfg.py**, unexplored.
`0x43 RunSharedScript(1)` · `0x44 WaitSharedScript()` · `0x45 StopSharedScript()` — one shared coroutine per object, uid = `gExec.uid + cSeqOfs`.
`0x1D CreateObject(2,2)` · `0x3B SetObjectIndex(1)` · `0x93 SetObjectFlags(1)` · `0xE9 UpdatePartyUID()`.
`0x11/0x13/0x15/0x17/0x19` `[unnamed]` 0-arg — the odd slots interleaved with the RunScript family (padding, or five unnamed dispatch variants).

## 3. ACTOR MOVEMENT / PATHING

`0x23 Walk(2,2)` (blocks) · `0x24 WalkTowardObject(1)` · `0x25 InitWalk()` · `0x26 SetWalkSpeed(1)` · `0x55 SetWalkTurnSpeed(1)` (crank to 255 to kill the walk-arc orbit) · `0xA2 WalkXZY(2,2,2)` · `0xE8 SideWalkXZY(2,2,2)` · `0xA0 WalkToExit()` · `0xA4 CalculateExitPosition()` · `0xA5 Slide(2,2)` · `0xA6 SetRunSpeedLimit(1)` · `0x6A DisableRun()` / `0xF0 EnableRun()`.
Teleports: `0xA1 MoveInstantXZY(2,2,2)` — args are **(worldX, −worldY, worldZ)**, disables pathing · `0xAD MoveInstantXZYEx(1,2,2,2)` · `0xBF MoveInstantEx(1,2,2)` (by uid, re-grounds).
Turn: `0x36 TurnInstant(1)` (0=S 64=W 128=N 192=E) · `0x87 TurnInstantEx(1,1)` · `0x56 TimedTurn(1,1)` · `0xBB TimedTurnEx(1,1,1)` · `0x51 TurnTowardObject(1,1)` · `0x9B TurnTowardPosition(2,2)` · `0xA7 Turn(1)` · `0x50 WaitTurn()` / `0xBC WaitTurnEx(1)` · `0x99 SetTurnSpeed(1)` · `0x37 SetPitchAngle(1,1)`.
Jump: `0xE2 SetupJump(2,2,2,1)` (x, −y, z, frames) · `0xDC Jump()` · `0x94 SetJumpAnimation(2,1,1)` · `0x9C RunJumpAnimation()` · `0x9D RunLandAnimation()`.
Collision: `0xA8 SetPathing(1)` · `0xCB EnablePath(1,1)` · `0x9A EnablePathTriangle(2,1)` · `0x27 SetTriangleFlagMask(1)` (127 = ignore restricted triangles; engine resets to 255 every field load).
Control: `0x2D DisableMove()` / `0x2E EnableMove()` · `0x2C DefinePlayerCharacter()` · `0x67 SetControlDirection(1,1)` ‡ · `0xB9 AddControllerMask(1,2)` ‡ / `0xBA RemoveControllerMask(1,2)` ‡.
`0xA3 [unnamed](1,1,1,1)` — a 4×u8 actor-band op, unexplored.

## 4. ACTOR ANIMATION

`0x33 SetStandAnimation(2)` · `0x34 SetWalkAnimation(2)` · `0x52 SetInactiveAnimation(2)` · `0x7A SetLeftAnimation(2)` · `0x7B SetRightAnimation(2)` · `0x40 RunAnimation(2)` / `0xBD RunAnimationEx(1,2)` · `0x41 WaitAnimation()` / `0xBE WaitAnimationEx(1)` (both hang on a player-cloned actor) · `0x42 StopAnimation()` (clears afExec/afLower/afFreeze — required before a Walk) · `0x3D SetAnimationInOut(1,1)` · `0x3E SetAnimationSpeed(1)` · `0x3F SetAnimationFlags(1,1)` · `0x86 SetAnimationStandSpeed(1,1,1,1)` · `0x98 MakeAnimationLoop(1)` · `0x90 DisableInactiveAnimation()` / `0xEE EnableInactiveAnimation()` · `0x47 EnableHeadFocus(1)` · `0x8B SetHeadFocusMask(1,1)` · `0x91 FollowFocus(1)` ‡ · `0x38 Attack(1)` · `0xE5 AttackSpecial(1)` · `0xDB EnableVictoryPose(1,1)` ‡ · `0x35 [unnamed](2)` (an anim-id-shaped slot in the middle of the anim setters).

## 5. MODEL / APPEARANCE / SHADOW / ATTACH

`0x2F SetModel(2,1)` · `0x39 ShowObject(1,1)` / `0x3A HideObject(1,1)` · `0xD5 HideAllObjects()` / `0xD6 ShowAllObjects()` · `0x8F SetModelColor(1,1,1,1)` · `0x9F SetObjectSize(1,1,1,1)` · `0x4B SetObjectLogicalSize(1,1,1)` · `0x62 SetRow(1,1)` · `0x4C AttachObject(1,1,1)` / `0x4D DetachObject(1)` / `0xD4 AttachObjectOffset(2,2,2)` · `0x88 RunModelCode(1,2,2,2)` ‡.
Shadow: `0x7F EnableShadow()` · `0x80 DisableShadow()` · `0x81 SetShadowSize(1,1)` · `0x82 SetShadowOffset(2,2)` · `0x83 LockShadowRotation(1)` · `0x84 UnlockShadowRotation()` · `0x85 SetShadowAmplifier(1)`.
Texture: `0xC0 EnableTextureAnimation(1,1)` · `0xC1 RunTextureAnimation(1,1)` · `0xC2 StopTextureAnimation(1,1)`.
`0x30/0x31 [unnamed]` 0-arg, `0x32 [unnamed](1,1)`, `0x46 [unnamed]` 0-arg, `0x4E [unnamed]` 0-arg.

## 6. CAMERA

`0x1E SetCameraBounds(1,2,2,2,2)` · `0x6F MoveCamera(2,2,1,1)` · `0x70 ReleaseCamera(1,1)` · `0x71 EnableCameraServices(1,1,1)` · `0x72 SetCameraFollowHeight(2)` · `0x73 EnableCameraFollow()` / `0x74 DisableCameraFollow()` · `0x7E SetFieldCamera(1)` (multi-camera switch) · `0xC3 SetTileCamera(1,1)` · `0x28 Cinematic(1,1,1,1)` · `0xA9 CalculateScreenPosition(1)` ‡ · `0xEA CalculateScreenOrigin()` ‡ · `0x6B SetBackgroundColor(1,1,1)`.

## 7. TILE / BG OVERLAY (the 2D sprite engine)

`0x59 SetTileColor(1,1,1,1)` · `0x5A SetTilePositionEx(1,2,2,2)` · `0x5B ShowTile(1,1)` · `0x5C MoveTileLoop(1,1,2,2)` · `0x5D MoveTile(1,1,2,2)` · `0x5E SetTilePosition(1,2,2)` · `0x5F RunTileAnimation(1,1)` · `0x60 ActivateTileAnimation(1,1)` · `0x61 SetTileAnimationSpeed(1,2)` · `0x63 SetTileAnimationPause(1,1,1)` · `0x64 SetTileAnimationFlags(1,1)` · `0x65 RunTileAnimationEx(1,1,1)` · `0xCA ResetTileAnimation(1,1)` · `0xE4 MoveTileLoopWithOffset(1,1,2,2,1)` · `0xE6 SetTileLoopType(1,1)` · `0xE7 SetTileAnimationFrame(1,1)` · `0xED SetTileLoopAlpha(1,2,2)` · `0x92 AttachTile(1,2,1,1,1,1,1)` ‡ · `0xC9 SetupTileLoopingWindow(1,2,2,2,2)` ‡ · `0x76 DrawRegionStart(2,2)` ‡ / `0x77 DrawRegionSetLast(2,2)` ‡ / `0x78 DrawRegionPushNew()` ‡ · `0x58 [unnamed](2,2,2)` (a 3×i16 slot immediately before the tile band — plausibly a tile/scroll primitive, unexplored) · `0x11C SetTilePositionTimed` (Memoria, §16).

~25K combined uses in stock. `[[gauge]]` proved the whole band drives a custom HUD with **one `SetTileAnimationFrame` per tick**.

## 8. WINDOW / TEXT

`0x1F WindowSync(1,1,2)` · `0x20 WindowAsync(1,1,2)` · `0x95 WindowSyncEx(1,1,1,2)` / `0x96 WindowAsyncEx(1,1,1,2)` (per-actor attribution; needs the bubble bit `flags & 128`) · `0x21 CloseWindow(1)` (turns the PAGE on a `[PAGE]` entry; can BLOCK on a voice clip) · `0xEB CloseAllWindows()` ‡ · `0x54 WaitWindow(1)` · `0x53 PreventWindowInit()` ‡ · `0x8E RaiseWindows()` (clamped at depth 90 — raise once per open, never re-raise) · `0x66 SetTextVariable(1,2)` ‡ · `0x7C EnableDialogChoices(2,1)` ‡ · `0xE3 SetDialogProgression(1)` (writes `gMesSignal`, read back as sysvar 8) · `0x68 Bubble(1)` ‡ · `0xEF ShowHereIcon(1)` ‡ · `0xD7 ATE(1)` (3-bit flag word: 1 = blue/optional, 6 = grey forced, 0 = clear; avoid 5) · `0xB0 SetFieldName(2)` ‡ / `0xB1 ResetFieldName()` · `0xD0 BattleDialog(2)` ‡ · `0x75 Menu(1,1)` ‡ · `0x7D RunTimer(1)` ‡ / `0x8D ShowTimer(1)` ‡ / `0x69 ChangeTimerTime(2)` ‡ · `0xEC FadeFilter(1×6)` ‡ · `0x79 [unnamed]` 0-arg (sits inside the DrawRegion trio — the likely `DrawRegionEnd`/commit, unexplored) · `0x6C/0x6D/0x6E [unnamed]` 0-arg (three free slots between the timer and camera bands).

Window ids 0..7; **255 is the engine's no-window sentinel, never emit it**. Depth = 68 − 2×id.

## 9. SOUND / VIBRATION

`0xC5 RunSoundCode(2,2)` · `0xC6 RunSoundCode1(2,2,3)` · `0xC7 RunSoundCode2(2,2,3,1)` · `0xC8 RunSoundCode3(2,2,3,1,1)` — one opcode family, four arities; the 3-byte operand is the pan/volume/pitch payload.
`0x89 SetSoundPosition(2,2,2,1)` · `0x8A SetSoundObjectPosition(1,1)` — **positional audio**, barely touched by the kit.
`0x1B ContinueBattleMusic(1)`.
Vibration (a whole dead subsystem on Steam): `0xF6 VibrateController(1)` ‡ · `0xF7 ActivateVibration(1)` · `0xF8 RunVibrationTrack(1,1,1)` ‡ · `0xF9 ActivateVibrationTrack(1,1,1)` · `0xFA SetVibrationSpeed(2)` · `0xFB SetVibrationFlags(1)` · `0xFC SetVibrationRange(1,1)`.

## 10. BATTLE

`0x2A Battle(1,2)` * — **NOT a warp**; encoding a field warp here starts a battle with the field id as scene id (crash). `0x8C BattleEx(1,1,2)` * (per TERMINATOR set it is `0x2A`'s extended twin) · `0x4A RunBattleCode(1,2)` · `0x3C SetRandomBattles(1,2,2,2,2)` · `0x57 SetRandomBattleFrequency(1)` (the real overworld lever; `world-encounter-frequency`) · `0xE1 TerminateBattle()` · `0xD0 BattleDialog(2)` ‡ · `0x11D AddBattleStatus` / `0x11E RemoveBattleStatus` (§16).

## 11. PARTY / INVENTORY / CHARACTER STATE

`0x48 AddItem(2,1)` / `0x49 RemoveItem(2,1)` · `0xCE AddGi(3)` ‡ / `0xCF RemoveGi(3)` ‡ (gil, 24-bit unsigned; negative wraps) · `0xB2 Party(1,2)` (PARTYMENU: minSize, lockedMask) · `0xDD RemoveParty(1)` · `0xB4 SetPartyReserve(2)` · `0xDE SetName(1,2)` · `0xFE SetCharacterData(1,1,1,1,1)` ‡ · `0xF1 SetHP(1,2)` ‡ / `0xF2 SetMP(1,2)` ‡ · `0xF4 LearnAbility(1,1)` ‡ / `0xF3 UnlearnAbility(1,1)` ‡ · `0xD9 CureStatus(1,1)` · `0xCC AddCharacterAttribute(2)` / `0xCD RemoveCharacterAttribute(2)` (bit 4 = LADDER) · `0xAA EnableMenu()` / `0xAB DisableMenu()` · `0x112-0x116` (§16).

## 12. WORLD / VEHICLE / FIELD TRANSITION

`0x2B Field(2)` * · `0xB6 WorldMap(2)` * ‡ · `0xFD PreloadField(1,2)` (no-op outside PSX) · `0x9E ExitField()` · `0xC4 RunWorldCode(1,2)` ‡ · `0x29 SetRegion(var × 4)` · `0xB5 PretendToBe(1)` ‡ · `0xD8 SetWeather(1,1)` ‡ · `0xAC ChangeDisc(2)` ‡.

## 13. MINIGAME / EXOTIC TOP BAND

`0xAE TetraMaster(2)` * ‡ · `0xAF DeleteAllCards()` ‡ · `0xE0 AddFrog()` ‡ · `0xB3 RunSPSCode(1,1,2,2,2)` ‡ / `0xDA RunSPSCodeSimple(1,1,1,2,2)` ‡ · `0xB7/0xB8 [unnamed]` 0-arg · `0xD1/0xD2/0xD3 [unnamed]` 0-arg · `0xDF [unnamed](1)` · `0xFF` — **reserved: the extended-page prefix**, never an opcode.

⚠ **`0xD3` at opcode level is an unnamed 0-arg statement. `0xD3` inside an EXPRESSION stream is `flexible_varfunc`** (§18.6). Two different namespaces, same byte.

---

## 14. THE EXOTICS — what it plausibly does, what you could build

Confidence tags: **[V]** verified in-game or byte-decoded in this repo · **[E]** read off engine source · **[I]** inferred from the table/name, unproven.

| op | mnemonic | what it does | what a creative author builds |
|---|---|---|---|
| 0xAE | `TetraMaster(deck:2)` **[V]** | launches QuadMist from any field; **flow terminator** (`return 7`), so it must be the last statement in its function. Gate on `B_SYSVAR[19] ≥ 5` cards | any wager/duel gate — a toll bridge you card your way past, a "prove yourself" rank ladder, a boss that plays you instead of fighting. The uid-keyed `EMinigame.Set*Id` helpers are inert on custom fields, so the *opponent* must be chosen by deck arg + story flag |
| 0xAF | `DeleteAllCards()` **[E]** | wipes the card collection | a "the deck was stolen" story beat; a roguelike run reset; a New Game+ that keeps gil and drops cards |
| 0xB5 | `PretendToBe(char:1)` **[I/E]** | makes the current actor impersonate another character's identity for party/dialogue purposes | **disguise quests** — infiltration where the leader reads as a guard; a doppelgänger scene; body-swap arcs. The only opcode that lies about who you are without a model swap |
| 0xCE/0xCF | `AddGi / RemoveGi(24-bit)` **[V]** | party gil ±, caps 9,999,999 / floors 0 | tolls, bribes, upkeep. Combined with a per-tick daemon: **a gil DRAIN as a clock** — rent, fuel, mercenary wages. The one currency the engine tracks for free and the menu renders for free |
| 0xAC | `ChangeDisc(disc:2)` **[I/E]** | the PSX disc-swap prompt; inert or cosmetic on Steam | a diegetic **chapter/act break** if it still renders; otherwise a free no-op marker byte for a disc-aware save layout |
| 0xD8 | `SetWeather(a:1,b:1)` **[I]** | field weather state (rain/snow/clear + intensity, by inference from arg shape) | day/night and storm cycles driven by a story flag; a weather-gated puzzle (rain fills a channel); mood control per revisit. Tabled in `studies/cutscene-authoring/REVIEW.md` — never benched |
| 0xE0 | `AddFrog()` **[V]** | increments **the** frog counter — the game's ONE engine-backed, field-agnostic counter opcode, readable as `B_SYSVAR[16]` | a **free save-persisted global integer** with no flag budget: collection counters, kill counts, reputation, a stamp card. Abuse it as generic score and the menu even displays it |
| 0xF6 | `VibrateController(n:1)` + 0xF7-0xFC | the full rumble-track subsystem: activate, run track, per-track activate, speed, flags, range | on modern controllers this is live haptics. **Haptic-only information channel**: a Geiger-counter hunt (rumble strength = proximity to a buried item), rhythm-game beats, a heartbeat that rises with danger. Six opcodes of expressive bandwidth nobody in FF9 modding uses |
| 0x75 | `Menu(id:1, sub:1)` **[V]** | 0=main, 1=name entry (renames a REAL character), 2=shop (`shopId`), 4+0=save, 5=chocograph; 3/6/7/8 dead | `Menu(2,id)` = a shop anywhere → **armoury/black-market/hire-hall** phases (proven, bench 30418). `Menu(1,char)` = the only text-input primitive in the game — a naming ceremony, a password gate spelled into a character name. `Menu(4,0)` = a save point that is just a script |
| 0x66 | `SetTextVariable(slot:1, val:2)` **[V]** | writes `ETb.gMesValue[slot]`; `[VAR=n]`/`[ITEM=n]`/`[TBLE=n]` render it. **Expression form** (`arg_flags=0b10`) escapes the ±32767 immediate cap | the whole-wire protocol for a live HUD. `[TBLE=bank]` = a value-indexed string swap → one `.mes` entry holding N states = **a text-mode progress bar, a state machine readout, ASCII art frames** with no art pipeline at all |
| 0x68 | `Bubble(state:1)` **[V]** | the "!" / "?" float over the player | free 1-bit sprite. Stealth detection meter, a hot/cold finder, a "someone is watching" tell |
| 0xEF | `ShowHereIcon(mode:1)` **[V]** | the location marker; mode 3 = unconditional | a second free 1-bit sprite, independently addressable from Bubble — two bits of always-on HUD with zero art |
| 0x7D/0x8D/0x69 | `RunTimer / ShowTimer / ChangeTimerTime` **[V]** | the Hunt-Festival clock. `ChangeTimerTime(GetTimerTime + N)` is stock's **additive** time-bonus idiom; readable as `B_SYSVAR[17]` | any timed run. But also: the timer keeps ticking through a shop pause → **a shop with a clock on it**. And field 1853 carries a cut minigame where *score extends the clock* — the full survival-loop shape, already wired in stock bytes |
| 0xEC | `FadeFilter(6×1)` **[V]** | `WIPERGB` — full-screen colour fade/flash with 6 parameters | not just transitions: **a damage flash, a lightning strike, a memory/flashback tint, a vision-impairment mechanic** (fog, blindness). Needs `RaiseWindows` to put text above it |
| 0x76/0x77/0x78 | `DrawRegionStart(2,2) / SetLast(2,2) / PushNew()` **[I]** | a scissor/draw-region stack: begin a region, set its extent, push a nested one | **arbitrary screen masking** — letterbox bars, a spotlight/keyhole view, a split-screen, a picture-in-picture, a torch-radius reveal. The `PushNew` implies nesting, which implies a compositor nobody has driven |
| 0x92 | `AttachTile(1,2,1,1,1,1,1)` **[V-cited]** | binds a BG overlay to an actor — 7 operands, the widest tile op | a **health bar over an NPC's head**, a name tag, a status icon, a targeting reticle that tracks a moving actor. Turns the 2D overlay layer into a world-space UI layer |
| 0xC9 | `SetupTileLoopingWindow(1,2,2,2,2)` **[I]** | defines a scrolling/looping window rect for a tile | infinite scroll: a **waterfall, conveyor, starfield, credits crawl, a moving-train parallax** — and, with the rect as a viewport, a scrolling *map* or minimap inside a field |
| 0xB3/0xDA | `RunSPSCode(1,1,2,2,2)` / `RunSPSCodeSimple(1,1,1,2,2)` **[E]** | drives an SPS particle effect by code + params | a magic-cast tell, a portal, environmental smoke, **a particle as a game object** (a wisp that leads you). Readable back via `B_SPS` in expressions |
| 0xC4 | `RunWorldCode(code:1, val:2)` **[V]** | the overworld's whole parameter surface: `(0,n)` weather auto-cycle, `(1,mode)` vehicle mode, `(2,x)` minimap visibility, `(4,x)` naviMode, `(26,n)` Ragtime-Mouse probability, `(28,0)` dismount, `(32/41,…)` PSX music no-ops | the custom-vehicle lever (proven: boat, ferry). Unexplored codes are a **map of every world tunable** — `w_frameSetParameter`'s switch runs `ff9.cs:3842-3931` |
| 0xB6 | `WorldMap(entry:2)` * **[V]** | field → world map at an entry | branch the entry by story flag and one door becomes many destinations |
| 0xB0/0xB1 | `SetFieldName(id:2) / ResetFieldName()` **[V]** | sets the location label the **menu and save slot** show (there is no on-field title popup) | 3 fields only in stock ("You don't know where you are"). Use it for **amnesia, disguise, a shifting dungeon**, or to label the save slot with *quest state* rather than a place |
| 0x11A/0x11B | `ClearMemoriaVector(id) / ClearMemoriaDictionary(id)` **[V-adjacent]** | reset a `gScriptVector`/`gScriptDictionary` slot | the save-persisted collections (§18.6). Clear = **New Game+ reset, round reset, inventory-of-your-own-design wipe** |
| 0x115/0x116 | `AddShopItem / AddShopSynthesis` **[V]** | mutate `ff9buy.ShopItems` — a **static process table**: changes survive New Game AND ~Reload, reset only at relaunch | stock that grows with the story, a black market unlocked by a flag, **THE HIDDEN-RECIPE IDIOM** (declare a locked recipe on a parked shop, graft the real shop at runtime). ⚠ the persistence is a footgun as much as a feature |
| 0xFE | `SetCharacterData(1,1,1,1,1)` **[I]** | 5-operand write into a character record (char, selector, + 3 payload bytes) | direct stat surgery outside the menu: a **curse that drops STR**, a training montage, a temporary buff with no status effect |
| 0x112-0x114 | `SetCharacterEquipment / Level / Exp` **[E]** | equip a slot, set level, set exp — all 3-byte operands, all expression-capable | scripted loadouts per scene, a **level-scaled encounter**, a flashback where you're level 1, an arena that normalizes the party |
| 0xF1/0xF2 | `SetHP / SetMP(char:1, val:2)` **[E]** | direct HP/MP write | field-side damage: a trap corridor, a poison swamp, an endurance gauntlet, an HP-as-resource puzzle. No battle required |
| 0xF3/0xF4 | `UnlearnAbility / LearnAbility(char:1, ab:1)` **[E]** | grant/revoke an ability outright | a trainer NPC, a **skill tree in field script**, a curse that seals a spell, a story-beat power unlock |
| 0x11D/0x11E | `AddBattleStatus(6×3) / RemoveBattleStatus(3×3)` **[E]** | apply/clear a status (target, status, permanent?, +3 params) | field-applied status: petrification puzzles, a Float you need to cross lava, Mini to fit a gap, a permanent story-curse |
| 0xA9/0xEA | `CalculateScreenPosition(uid:1) / CalculateScreenOrigin()` **[I]** | projects an actor (or the origin) into screen space, presumably into readable vars | **the missing link between 3D actors and the 2D tile layer** — place an overlay exactly over a moving NPC, build a targeting cursor, a "look here" arrow, or a comic-panel speech tail that tracks. Likely feeds `AttachTile`'s use cases with computed coordinates |
| 0x67 | `SetControlDirection(x:1, y:1)` **[V]** | remaps the control axes (`TWIST`); `(-1,-1)` verified as an encoded pair | **camera-relative-to-fixed remap** per camera angle. Creative: a drunk/confusion state, a mirror-world where left is right, a rotating-room puzzle |
| 0xB9/0xBA | `AddControllerMask(1,2) / RemoveControllerMask(1,2)` **[V]** | masks pad bits (`EventInput.PSXCntlPadMask`). ⚠ **a direction mask also kills the menu** (`EnableMove` re-grants as `IsMenuON && IsMovementControl`) and **does not undo itself** | one-button tutorials (stock's only use, field 652). Creative: **a control-degradation mechanic** — paralysis that removes one direction, a QTE that only accepts one button, a stealth mode where running is masked out. Whatever removes the mask must be reachable *without moving* |
| 0x88 | `RunModelCode(1,2,2,2)` **[I]** | a per-model command channel with 3 wide params | the model-side twin of RunSoundCode/RunWorldCode — likely bone/part/material control. Worth a decode: it is the only unexplored *parameterized* channel into a live model |
| 0x91 | `FollowFocus(uid:1)` **[I]** | makes an actor's gaze/facing track a target continuously | crowd reaction — **a room full of NPCs that all turn to watch you**; a portrait whose eyes follow; a sentry that tracks before it detects |
| 0xD0 | `BattleDialog(textId:2)` **[E]** | pushes a message into the BATTLE text channel (`MESB`) | a boss that taunts by name mid-fight, a tutorial voice during combat, **narrative delivered inside battle** without a cutscene |
| 0x7C | `EnableDialogChoices(mask:2, default:1)` **[V]** | availability bitmask + initial cursor row; only applies if the text carries `[PCHM]`. 833 stock uses; mask can be an expression | **greyed-out** options (visible but locked) vs the kit's vanishing rows — the difference between "you can't yet" and "there is nothing". Dialogue that shows you what you're missing |
| 0xEB / 0x53 | `CloseAllWindows()` / `PreventWindowInit()` **[E]** | both exist in the engine, **used by ZERO shipping fields** | free real estate. `PreventWindowInit` implies a window that persists across a transition — a **persistent HUD panel** surviving a scene change. Verbatim-first: bench before trusting |
| 0xDB | `EnableVictoryPose(1,1)` **[I]** | arms the post-battle pose on the field | a scripted "we won" beat without a battle; a celebration on demand |
| 0x62 | `SetRow(1,1)` **[I]** | front/back row from field script | a formation puzzle; a stance system set by where you stand in the room |

---

## 15. THE UNNAMED EXTENDED BLOCK — 0x100-0x111

Eighteen extended-page opcodes with **arg shapes but no names** (Memoria's `DoEventCode` case comments carry none; `_regen_optables` leaves the hex placeholder). This is the historical **BS\*/BA\*** block.

```
0x100(1,1) 0x101(1,1) 0x102(1,1) 0x103(1,1) 0x104(1,1) 0x105(1,2) 0x106(1,1)
0x107(1,2,2) 0x108(1,1) 0x109(1,1) 0x10A(1,1) 0x10B(1,1) 0x10C(1,1) 0x10D(1,2)
0x10E(1,1) 0x10F(1,1,1) 0x110(1,1,1) 0x111(1,1)
```
Every one takes an object/target as operand 0. **This is the single largest undocumented block in the ISA** and the cheapest brainstorm win: eighteen opcodes, a `read_code` that already decodes them, and a 676-field corpus to census for usage. If zero fields use them they are free slots; if some do, the disassembly of those sites names them.

## 16. MEMORIA'S OWN EXTENDED PAGE — 0x112-0x11E

Declared in `_regen_optables.CUSTOM_EXTENDED`, dispatched ad hoc, **every operand read with `getv3()` — 3-byte immediates, expression-flagged like any arg**. These do not appear in the static tables; the kit declares them.

`0x112 SetCharacterEquipment(char, slot, item)` · `0x113 SetCharacterLevel(char, level)` · `0x114 SetCharacterExp(char, exp)` · `0x115 AddShopItem(shopId, item, add?)` · `0x116 AddShopSynthesis(shopId, synthId, add?)` · `0x117 WalkEx(obj, speed, x, y, z, flags)` — **the only walk with a speed and a Y in one call** · `0x118 TurnTowardObjectEx(turner, target, speed)` · `0x119 SetLogicalAnimationEx(obj, kind, anim)` · `0x11A ClearMemoriaVector(id)` · `0x11B ClearMemoriaDictionary(id)` · `0x11C SetTilePositionTimed(overlay, dx, dy, dz, frames)` — **tweened overlay motion, no per-frame daemon** · `0x11D AddBattleStatus(target, status, perm?, a1, a2, a3)` · `0x11E RemoveBattleStatus(target, status, perm?)`.

Verified against Memoria base `6b8bb2d5`. The static tables end exactly at 0x112 (asserted by the regen script) — anything past 0x11E is unallocated space **we control**, since this page is ours to extend in `memoria-patches/`.

---

## 17. FLOW FACTS THE AUTHORING LAYER ENFORCES

- `TERMINATOR_OPS = {0x04 RET, 0x1C TerminateEntry, 0x2A Battle, 0x2B Field, 0x4F STOP, 0xAE TetraMaster, 0xB6 WorldMap, 0xF5 GameOver}` — a path reaching one ends; the IP never advances into adjacent bytecode.
- `JUMP_OPS = {0x01, 0x02, 0x03}`; a conditional tests the value the immediately preceding `0x05` pushed.
- `RUNSCRIPT_OPS = (0x10, 0x12, 0x14)` — uid = `imm(1)`, tag = `imm(2)`. `0x16/0x18/0x1A` are **not modeled** by `cfg.py` (`cfg.py:871`).

---

## 18. THE EXPRESSION / RPN LAYER

### 18.1 The machine
Not a textbook postfix VM. An operand token **pushes** (`_s7.push`); an operator **pops lazily** through `EvaluateValueExpression` then pushes exactly one result through `expr_Push_v0_Int24`. Net per token = `−arity + 1` for every operator except `B_EXPR_END` (0x7F), which pushes nothing and **must be the last token**. A stream must leave **exactly one** value.

- **No depth ceiling.** `CalcStack.push` grows its backing list on demand. Deepening an expression is free.
- **Underflow is not a crash**: `CalcStack.pop` on empty logs `[CalcStack.pop] topOfStackID == 0` and yields 0 — one log line per evaluation plus a silently wrong number. `exprsem.analyze()` refuses it statically.
- **THE 26-BIT VALUE ENVELOPE.** Every *computed* intermediate is 26-bit signed (`EXPR_VALUE_MIN/MAX = ∓2^25`). The push ORs the Int26 class tag into bits 26-28 with **no mask**, and the read-back is `(t0 << 6) >> 6`. Overflow does not truncate — **the high bits collide with the VariableSource field and the entry is re-read as a different variable class.** Only a *bare terminal var token* bypasses the push and returns a full Int32 via `getv()`. (This is the same number `content/behavior.py` carries as `TABLE_VALUE_MIN/MAX`, and it is what killed the Path-B region test: cross products overflowed on 36% of fields.)

### 18.2 Operator table (op_binary 0-127, all named in `_exprtable.EXPR_OP_NAMES`)

- **Arithmetic/bitwise/compare (arity 2):** `B_MULT B_DIV B_REM B_PLUS B_MINUS B_SHIFT_LEFT B_SHIFT_RIGHT B_LT B_GT B_LE B_GE B_EQ B_NE B_AND B_XOR B_OR B_ANDAND B_OROR`
- **Unary:** `B_SINGLE_MINUS B_NOT B_COMP` (arity 1). ⚠ **`B_SINGLE_PLUS` is arity 0 in the shipping engine** — a bare re-push of stale `_v0` that strands its operand.
- **Inc/dec through an lvalue (WRITE, arity 1):** `B_POST_PLUS B_POST_MINUS B_PRE_PLUS B_PRE_MINUS`
- **Assignment (WRITE, arity 2):** `B_LET` + `B_{MULT,DIV,REM,PLUS,MINUS,SHIFT_LEFT,SHIFT_RIGHT,AND,XOR,OR}_LET`
- **Member-list lane (the battle-AI "for all members" operators):** `_A` suffix = arity 3 WRITE (`B_LET_A` etc., operands `[member-list, member-field, rhs]`); `_E` suffix = arity 3 READ compare/bitwise over a list (`B_LT_E … B_OR_E`), plus `B_LET_E B_AND_LET_E B_XOR_LET_E B_OR_LET_E` (arity 3 WRITE); `B_NOT_E B_LMAX B_LMIN` arity 2. ⚠ **`B_LMAX`/`B_LMIN` are party-member ARGMAX/ARGMIN returning a member BITMASK, not numeric clamps** — a documented trap.
- **List primitives:** `B_MEMBER(i)` (inline byte, pushes a member ref, arity 0) · `B_COUNT` (popcount of a list) · `B_PICK` (arity 2) · **`B_SELECT` (arity 1, IMPURE — draws `Comn.random8()`, advances the shared RNG)**
- **Input:** `B_KEY B_KEYOFF B_KEY2 B_KEYON2 B_KEYOFF2` (pure ETb reads) · **`B_KEYON` is IMPURE — it SETS `VoicePlayer.scriptRequestedButtonPress`**, read by the dialogue-close path and the voice player
- **Trig/geometry:** `B_SIN B_COS B_SIN2 B_COS2` (arity 1) · `B_ANGLE B_DISTANCE B_ANGLE2` (arity 2) · `B_ANGLEA B_DISTANCEA` (arity 1) · `B_PTR(i)` (inline byte)
- **Party/field reads (arity 1):** `B_CURHP B_MAXHP B_CURMP B_MAXMP` (read a **party slot** via GetPlayer — NOT the acting unit) · `B_HAVE_ITEM` (= `GetItemCount(id)`) · `B_BAFRAME B_FRAME` · `B_BGIID B_BGIFLOOR` (**which walkmesh triangle / floor the actor is on — the only spatial classifier that actually works**) · `B_PARTYCHK` · `B_SPS` (arity 2, returns 0)
- ⚠ **`B_PARTYADD` (arity 1) is a WRITE — it RECRUITS a party member.** No `_LET` in the name; the reason `exprsem` classifies exhaustively instead of by name pattern.
- **Pushes:** `B_CONST` → `const(N)` (2-byte) · `B_CONST4` → `const4(N)` (4-byte) · `B_OBJSPECA` → `obj(uid=U).f[F]` · `B_SYSLIST[i]` · `B_SYSVAR[i]` · the `0xC0` variable tokens
- **Dead (arity 0, return 0 — no `case` in `DoCalcOperationExt`):** `B_PAD0-3`, `B_CAST8 B_CAST8U B_CAST16 B_CAST16U B_CAST_LIST`, `B_OBJSPEC`, `pad67 pad68 pad69`, `B_pad7b B_PAD4`. **There is no cast operator in the shipping engine** — width comes from the variable token, not from a cast.

`UNSAFE_TO_REPEAT = WRITE_OPS | IMPURE_OPS` — the set a per-frame HUD value may never contain.

### 18.3 Variable addressing — the `0xC0` token

```
bit7,6 = 1 (0xC0 base) · bit5 = long index (2-byte, else 1) · bits 4-2 = VariableType · bits 1-0 = VariableSource
```
- **Source (0-3 only in this token):** `0 Global` (= `gEventGlobal`, save-persistent) · `1 Map` (per-field transient) · `2 Instance` (entry locals) · `3 Null` (→ **Memoria custom variables**, §18.5)
- Sources `4 Object`, `5 System`, `6 Member`, `7 Int26` are reached through their own tokens (`obj(...)`, `B_SYSLIST`, `B_MEMBER`).
- **Type:** `0 SBit · 1 Bit · 2 Int24 · 3 UInt24 · 4 SByte · 5 Byte · 6 Int16 · 7 UInt16`. Ranges: Bit (0,1) · SByte (−128,127) · Byte (0,255) · Int16 (∓32768/32767) · UInt16 (0,65535) · **Int24 AND UInt24 share one case label and both sign-extend the third byte → (−8388608, 8388607)**.
- `0xC4` = `Global.Bit` = a story flag (the kit's GLOB_BOOL); `0xC5` = `Map.Bit` (MAP_BOOL twin). **Safe story-flag band is ≥ 8712.**
- Assembler form is the exact inverse of the disassembler: `Source.Type[index]`, minimal encoding (short index when ≤ 0xFF). `assemble()` **self-verifies the round trip** at the library boundary.

**The under-used part:** the same `gEventGlobal` byte array is addressable at *any* of 8 widths. `Global.Int24[187]` and `Global.Byte[561]` overlap. That is aliasing you can exploit (pack 3 counters in a word, read them as one) — or corrupt yourself with.

### 18.4 `B_SYSVAR[code]` — 32 engine reads (`GetSysvar.cs:9-107`)

Known codes: `0` = `Comn.random8()` **IMPURE, advances the shared RNG** · `2` = usercontrol (**read-only from script** — no Set case; `UCOFF`/`UCON` are the writers) · `6` = party gil · `7` = step count (**DEAD — one assignment repo-wide, `gStepCount = 0`**) · `8` = `gMesSignal` (the text→script handshake; written by `SetDialogProgression` and by in-text `[SIGL=n]`/`[INCS]` tags when their position *appears on screen*) · `9` = `GetChoose()` — **IMPURE, it WRITES `ETb.sChoose`; re-reading clobbers a pending choice** (hence `switch_on_choice`: push the selector ONCE) · `10-13` = map-jump / sys x,y · `16` = Frogs.Number · `17` = `TimerUI.Time` · `19` = card count (**clamped to 95 / MaxCardCount-remapped — not the raw count**) · `20` = play time in seconds (engine-clamped to 8,388,607) · `193` = topograph (world) · `200` = "transition busy" (world entrance ready-poll) · `205` = the Ragtime-Mouse probability roll (**NOT the encounter check**) · `207` = `w_worldArea2Zone(...)`, the world encounter-rate ladder selector.

**~15 of 32 codes are unaccounted for in this repo.** Each is a free read of live engine state.

### 18.5 `Null.<Type>[n]` — Memoria custom variables (11 codes, `EBin.cs:2416-2431`)

`0` TETRA_MASTER_WIN · `3` TETRA_MASTER_POINTS · `4` TETRA_MASTER_RANK (collector level) · `5` TREASURE_HUNTER_POINTS (a weighted popcount over flag ranges). Owner-confirmed in-game on bench 30800. The other codes are undocumented here. **This is the extension point**: a Memoria patch adding `memoria_variable` codes makes *any* engine state script-readable with no new opcode.

### 18.6 **0xD3 — `flexible_varfunc`, the computed-index escape hatch**

```
D3  <id:u16>  <argc:u8>        ; carved OUT of the variable-token space — EBin.expr checks it FIRST
```
`argc` **rides the wire**; the engine pops exactly that many CalcStack operands (pushed *before* the token, ordinary RPN) and pushes exactly one result. No per-function arity table is needed or trusted. An **undefined id falls through to 0 and still pushes one** — so the surface is safe to probe.

Sugar names at canonical arity (`FLEX_FN_SUGAR`):

| token | id, argc | meaning |
|---|---|---|
| `B_VECTOR` | (20, 2) | `gScriptVector[vecId][index]` |
| `B_VECTOR_SIZE` | (21, 1) | length of vector `vecId` |
| `B_DICTIONARY` | (22, 2) | `gScriptDictionary[dictId][key]` |

Everything else round-trips as the explicit `flex(id,argc)` form.

**Why this is the most important token in the ISA:**
1. **`B_VECTOR` pushes a resolvable LVALUE** — readable anywhere an operand is, and **assignable via `B_LET`**. Writing at `index == size` **APPENDS**; a missing id at index 0 **CREATES** the vector.
2. **Both stores are SAVE-SERIALIZED** (`JsonParser.cs:521-545`).
3. **The index is a computed expression.** Stock `.eb` has no arrays — every table in shipping FF9 is an unrolled switch ladder. This gives you `table[f(x)]`: state machines, lookup tables, per-actor records, queues, ring buffers, inventories of your own design, save-persisted leaderboards — **all in stock Memoria, no DLL**.
4. Paired with `0x11A ClearMemoriaVector` / `0x11B ClearMemoriaDictionary` for reset.

This is the surviving dividend of the falsified Path-B arc, and it is still mostly unspent: the behavior compiler seeds `size←0/size←n` (which is what keeps stale saves inert — keep it law), and essentially nothing else in the kit uses computed indexing.

### 18.7 `B_MEMBER(N)` — battle-unit fields (`btl_scrp.GetCharacterData`)

`N` is a **switch-case selector, not a byte offset**, and `B_MEMBER(N) <expr> B_LET_A` **writes** it. `B_SYSLIST[1]` = acting unit (SELF), `B_SYSLIST[0]` = target.

`35 max.hp · 36 cur.hp · 37 max.mp · 38 cur.mp · 39 max.at · 40 cur.at · 41 level · 42-47 status.{invalid,permanent,cur}.{hi,lo} · 48-51 elem.{invalid,absorb,half,weak} · 52 target · 53 disappear · 57 geo_id · 58 mesh · 64 row · 65 line_no · 72 str · 73 mgc · 74 phys_def · 75 phys_evade · 76 mag_def · 77 mag_evade · 112 motion · 114 cur_attack · 140 pos.x · 141 pos.ny · 142 pos.z · 146 exp · 147 gil · 148 trance · 149 t_gauge`

Selectors **55/56 (model scale) are write-only** and deliberately omitted from the read table. `geo_id`/`mesh`/`motion` are writable → **mid-battle model and animation swaps from AI script**. `pos.x/ny/z` are writable → **scripted positional choreography inside battle**.

---

## 19. ENCODING TRAPS (each cost something)

1. `0x2A` is **Battle**, not PreloadField. Encoding a warp as `0x2A` starts a battle with the field id as scene id → null-ref crash.
2. `0xFD PreloadField` is a no-op outside PSX. `Field()` alone warps. The kit deliberately ships **no** `preload_field()` helper.
3. `MoveInstantXZY`/`SetupJump` take **(x, −y, z)** despite the name.
4. Window id **255 is the no-window sentinel** — never emit.
5. `CloseWindow` on a `[PAGE]` entry **turns the page**; one close per remaining page. It can also **block** on a voice clip.
6. `RaiseWindows` is clamped at depth 90 → a third raise **inverts** window z-order. One raise per open.
7. A direction controller-mask **also kills the menu**, and **does not undo itself**.
8. `SetTextVariable`'s immediate value is a sign-extended Int16 (±32767); the expression form (`arg_flags=0b10`) is the only way past it — but lands in the 26-bit envelope.
9. `B_SYSVAR[9]` (choice) and `B_SYSVAR[0]` (random) are **impure reads**. Never in a per-frame value.
10. `0xD3` decoded as a short-index variable **desyncs the stream by 2 bytes** — the engine checks it first, so must any decoder.
11. An expression blob **must** end `0x7F` or `CalcExpr` walks into the next instruction's bytes.

---

## 20. BRAINSTORM SEEDS — the surface that is decoded but unspent

1. **`0x100-0x111`** — 18 named-nothing extended opcodes with known arg shapes, all object-targeted. Census the 676-field corpus; either they're free slots or the sites name them.
2. **The 8 unnamed low slots** (`0x0A 0x0C 0x0E 0x0F 0x11 0x13 0x15 0x17 0x19 0x30 0x31 0x32 0x35 0x46 0x4E 0x58 0x6C 0x6D 0x6E 0x79 0xA3 0xB7 0xB8 0xD1 0xD2 0xD3 0xDF`) — ~27 total. `0x79` sitting inside the DrawRegion trio and `0x58` sitting before the tile band are the two highest-value guesses.
3. **The `DrawRegion` trio** — a nesting scissor stack nobody has driven. Spotlight, keyhole, split-screen, torch radius.
4. **`CalculateScreenPosition` + `AttachTile`** — 3D→2D projection feeding world-space 2D UI. Health bars over enemies, tracking reticles, comic speech tails.
5. **The vibration family (7 opcodes)** — a whole untouched output channel that is live on modern pads.
6. **`0xD3` computed indexing** — save-persisted arrays and dictionaries in stock Memoria. The single biggest capability gap between "FF9 scripts" and "a programming language", already open.
7. **Positional audio** (`SetSoundPosition` / `SetSoundObjectPosition`) — sound as a *findable* object.
8. **`RunWorldCode`'s unenumerated cases** (`ff9.cs:3842-3931`) — the complete overworld tunable map.
9. **`RunModelCode`** — the only unexplored parameterized channel into a live model.
10. **`PreventWindowInit` + `CloseAllWindows`** — zero stock uses; `PreventWindowInit` implies a window surviving a transition, i.e. a persistent HUD.
11. **`[TBLE=bank]` + `SetTextVariable`** — a value-indexed string bank = arbitrary text-mode graphics with no art pipeline.
12. **Expression-valued operands on opcodes nobody has flagged** — every operand of every opcode above can be computed at runtime. `Field(<expr>)`, `Battle(<expr>)`, `Menu(2, <expr>)`, `AddItem(<expr>, <expr>)` are all legal encodings. A computed-destination door, a computed shop, a computed encounter are each one `arg_flags` bit away.

---

# Brief: Already shipped / in flight / dead ends

# `.eb`-LEVEL CAPABILITY INVENTORY — what already exists

Legend: **SHIPPED** = in the kit, buildable today · **IN-FLIGHT** = code landed, playtest/ratification pending · **STUDY-ONLY** = designed/researched, not built.

---

## A. Core field-logic vocabulary (all compile to pure `.eb`, all SHIPPED)

Every one of these is a declarative `field.toml` block backed by a module in `ff9mapkit/ff9mapkit/content/`.

| Name | What it does | Status |
|---|---|---|
| `[[gateway]]` | Region-triggered field→field warp (`Field` 0x2B), fade-before-warp, per-door arrival, on-exit story advance | SHIPPED |
| `[[gateway]] to = "worldmap"` | Field→overworld exit; carries stock's byte-identical 13-target exit cascade (`worldexit.py`) | SHIPPED |
| `[[chest]]` | Treasure chest: open anim, `give_item` by name, gil add/subtract, `remove_item`, GLOB once-flag | SHIPPED |
| `[[event]]` | Generic press/tread region running an authored body; flags, branching, `cooldown`, `received` item-get box | SHIPPED |
| `[[npc]]` | NPC object w/ model, `face`, talk handler, dialogue tail, speaker tags, `opens_shop` | SHIPPED |
| `[[prop]]` | Static/posed prop objects, `pose` resolves the model's own form | SHIPPED |
| `[[ladder]]` | Navigable vertical/slant/bent ladders — bidirectional from-scratch, faithful (imported), emulated one-way; floor/gateway/worldmap tops | SHIPPED |
| `[[jump]]` | Ledge jumps, action or tread trigger, multi-hop `via`, per-hop `steps`; from-scratch `to =` (not copy-only) | SHIPPED |
| `[[platform]]` | Moving platforms/elevators incl. the **visible model** (`model`, `model_offset`, `warp_to` for inter-floor rides) | SHIPPED |
| `[[savepoint]]` | Synthesized `Menu(4,0)` savepoint + Moogle: bubble, dialogue, Yes/No, GLOB(184) latch, save choreography, barrel-pop reveal | SHIPPED |
| `[savepoint.mognet]` | Join FF9's real Mognet letter network as a NEW moogle | SHIPPED |
| Mognet DONOR-FORK lane | Patch a real moogle field in place to join the network | SHIPPED (in-game proven) |
| `[[choice]]` | Dialogue choice menus: NPC-triggered or zone/lever, flag-gated rows, `warp` action, `recall` | SHIPPED |
| Dialogue engine | Speaker names, auto-wrap, pages, window styling (style/window/actor/instant/speed/duration/window_pos/box/no_turbo/no_focus/**polled**) | SHIPPED |
| Multi-window + beats | `open`/`close`/`wait_window`/`raise` (several windows at once), `signal`/`hold`/`wait_signal`/`set_signal` text-synchronized beats, coloured text `{item}…{/}` | SHIPPED |
| `[[text_table]]` | A field's own string banks; runtime `[ITEM=]`-style resolution of live values into text | SHIPPED |
| Control locking | `lock` / `lock_menu` on dialogue + the whole movement-gate model (usercontrol, pad mask, controller deactivation) | SHIPPED |
| `[player] locked_entrances` | Arrive with control withheld at named entrances — stock's race-free `General_FieldEntrance`-gated grant (`entrylock.py`) | SHIPPED |
| `[player] twist` / movement | TWIST control-direction rotation so W = up-screen on a yawed camera (`movement.py`) | SHIPPED |
| `[encounter]` | Random encounter regions, rate, scene binding; `[[battle_bgm]]`; `RunSoundCode` field BGM; the song-0 fork battle-BGM fix | SHIPPED |
| `Main_Reinit` (tag 10) | After-battle resume entry — fixes the cutscene-field-clone softlock | SHIPPED |
| `[[on_entry]]` | Gated, once field-load narration/beat (incl. message-in-verbatim) | SHIPPED |
| `[startup]` | Assert the story beat / preset flag state at field entry | SHIPPED |
| `[party]` | Add/remove party members at field entry | SHIPPED |
| Story flags | GLOB vs MAP scoping, safe band ≥8712, partitioned campaign vs kit-standing lanes, long-index encoding, auto-allocation | SHIPPED |
| `[cutscene]` / `[[cutscene]]` | Full choreography: cast scenes, `walk`/`teleport`/`turn` (animated)/`anim`/`say`, paths, once-flags, story-event director (beat-gated, story-advancing) | SHIPPED |
| Conductor | Multi-actor central-director idiom (`*Ex` opcode family by UID, `with_prev` parallel beats + async fork/join) | SHIPPED |
| `pathfind.py` | Auto-routes a blocked cutscene walk around walls + other actors into clear straight legs (A* + string-pull) | SHIPPED |
| ATE system | Both flavors — optional blue-menu ATE and grey unskippable | SHIPPED |
| `[[shop]]` / `[[synthesis]]` / `[[synthesis_edit]]` | Custom shop + synth shops, NPC or standalone press-region opener; runtime `add_shop_item`/`remove_shop_item` (0x115) and `add_shop_synth`/`remove_shop_synth` (0x116) | SHIPPED |
| `[[sps]]` | SPS particle triggers from field logic | SHIPPED |
| `[music]` | Field BGM | SHIPPED |
| `areatitle.py` | Suppress a BG-borrowed field's inherited area-title overlays | SHIPPED |
| `entry_settle = "auto"` | Computed entry black-hold on arrival | SHIPPED |
| `[deathrules] on_defeat` | Warp instead of game over; OUTPOST "last camp visited"; instant/quiet exit; covers verbatim forks | SHIPPED |
| `[[coop]]` | Two-plate co-op gates — peer presence/position read out of reserved `gEventGlobal` cells as plain GLOB vars; fail-safe on stock engine | SHIPPED |
| `[[folklore]]` | Folklore codex entries minted as key items (band 80-254), grants ride `AddItem` with pool-encoded ids | SHIPPED (in-game proven) |
| `[chocobo]` | Chocobo Hot & Cold: dig prize pool + timer resolved into `[[logic_edit]] expr_literal` edits on a verbatim forest fork | SHIPPED |

## B. Actor AI — the behavior-tree compiler (`[behavior]`, target IS `.eb`)

| Name | What | Status |
|---|---|---|
| `[behavior]` trees | Priority branches, `when`/`do`, patrol/march/chase/wander/flee/hold_ground, mutual combat w/ HP + deaths, alarms, shift clocks | SHIPPED |
| Behavior CLASSES | `npcs = [...]` — one brain shared across same-tree units | SHIPPED |
| Pooled units | Runtime activation, spawn-at-your-feet, `hold_post`, per-pool spawn-request flag | SHIPPED (proven) |
| Pool ECONOMY | `price` + gil gate + RemoveGil, `button = true` SELECT-poller buy-anywhere hire | SHIPPED (proven) |
| Waves + win/loss | Countdown clock, `timer=`, REAL battles, THE CLOCK-COUPLED BATTLE LAW | SHIPPED |
| Data tables / counters / schedules | `gScriptVector` arrays on the `0xD3` computed-index dividend, schedule clock | SHIPPED, playtest-PENDING |
| `[[behavior.scan]]` / `[[behavior.group]]` / `engage` | Vector loop, group loop, `nearest`, `alive_only` | SHIPPED |
| `[[behavior.hud]]` | On-screen HUD strips w/ value sources (`gil`/`timer`/`hp:<unit>`), per-slot `digits` | SHIPPED |
| Theater verbs | `sfx`, `flash`, `announce` (delay/sustain), strike clips, hit cues, death beat, wave herald, staged win/lose text | SHIPPED |
| `award` / `hireable` | Economy payout + published per-pool flag | SHIPPED |
| `adjust` + `[[behavior.drift]]` | The vocabulary's first numeric write (the Sims lane's rung 0) | SHIPPED (offline) |
| Archetypes | Stamp a whole proven tree; ambient-life family, branch archetypes, the stamp WIZARD | SHIPPED |
| `behavior compile`/`lint`/`view` | Dry-compile + report, static checks + walkability sweep of routes AND dynamic pursuit lines, disassemble every body | SHIPPED |
| Workspace Behavior tab | Read-only ladder → editable ladder → authors on the stage → ▶ Simulate offline tick-stepper | SHIPPED |
| `[siege]` | Fort-Condor tower-defense as ONE declarative block + `examples/siege/` | SHIPPED |
| Route auto-feed | `route = "auto"` on `patrol`/`march` | SHIPPED |

## C. Minigame / UI substrate built on `.eb`

| Name | What | Status |
|---|---|---|
| `[[numeric_input]]` | The Treno-auction numeric stepper + choice `recall` to re-render a saved value | SHIPPED (fully in-game proven, bench 30417) |
| `[[qte]]` | The Blank-duel reaction game as kit vocabulary | SHIPPED |
| `[[gauge]]` | DLL-free tiles-as-sprites value bar | SHIPPED |
| Live-counter HUD daemon | Festival-of-the-Hunt shape, timer triplet 0x69/0x8D/0x7D | SHIPPED (as `[[behavior.hud]]`) |
| Fort Condor (full minigame) | Lane defense — unit AI migrated onto the behavior compiler; data-table substrate on bench 30415 | IN-FLIGHT (awaiting owner ratification) |
| Tetra Master | Feasibility done, near-fully data-moddable; `[scene] win_card` + `win_card_rate` shipped on the battle side | STUDY-ONLY (study dir on an unmerged branch) |
| The Manor / Sims | Needs/drift simulation on the behavior compiler | IN-FLIGHT (rung 0 shipped, rest study) |

## D. `.eb` tooling, round-trip, fork editing

| Name | What | Status |
|---|---|---|
| `eb-src` / `eb-asm` | Byte-exact `.ebs` source round-trip for any field event script; annotated (entry/routine/instruction comments), `--against` splice edits, 9753-binary standing gate | SHIPPED (rungs 1-4, 6-7; playtest-confirmed at slot 30810) |
| `logic-map` | Decode/read an entangled real `.eb`, name its entries/functions | SHIPPED |
| `logic-add` / `logic-edit` | Edit + add entries in place on a verbatim fork; `[[logic_edit]]` kinds incl. `expr_literal` | SHIPPED (whole EDIT tier in-game proven) |
| `lint-eb` | Static `.eb` validation | SHIPPED |
| `disasm` | Full opcode disassembler (`eb/disasm.py`, `_optables.py` authoritative) | SHIPPED |
| `exprasm` / `exprsem` | RPN expression assembler + semantics (also reused for enemy AI) | SHIPPED |
| `labelasm` | Label assembler w/ LONG-JUMP RELAXATION (the ~32KB body ceiling, removed) | SHIPPED |
| `cmdasm`, `cfg.py`, `model.py` | Command assembler, CFG + dominator pass, the `.eb` object model | SHIPPED |
| `.eb` file budget | `EB_FILE_BUDGET` / `eb_budget_used()` (offset-based, not `len()`), `append_entry` pre-checks, `CompiledBehavior.size_report()` byte histogram | SHIPPED |
| The BUDGET METER + escalation | A CLI/GUI byte meter approaching the ceiling, and `engine = "stock"/"dwix"` DECLARED escalation to an extended opcode path | **STUDY-ONLY** (and S1 blocker still live: `binutils.py:39-41` `pu16` still masks `& 0xFFFF` unchecked) |
| Computed array indexing (`0xD3`) | `flexible_varfunc` lane — stock Memoria already gives `.eb` computed indices; the Path-B dividend | SHIPPED |
| `eb.edit.nop_cinematics` | Seamless New-Game entry by nopping opening cinematics | SHIPPED |
| Region arming | >2-region silent-arming bug fixed; region tags 2/3/10, `IsInQuad` fan/doubled-vertex rule | SHIPPED |
| `fork-report --explain` | Decode a field's NPC interactions into readable English; Dialogue/Party/Items/Camera/Player axes; ROSTER-BY-BEAT | SHIPPED |
| Assembler + entry-table hardening | Stress pass; `set_u16` no longer masks | SHIPPED |

## E. Story / narrative-state

| Name | What | Status |
|---|---|---|
| Narrative-state ENGINE | Rungs 0-2 + chain/HUB lane proven: New Game → hub pick → derived mid-story boot played the Dali morning and handed off to the real game | IN-FLIGHT (rungs 0-2 ★; higher rungs open) |
| `story-seed <field> --beat` | Demand-driven `[startup]` emission for only the bits the field READS, per-bit provenance | SHIPPED (CLI verb live) |
| Dominance instrument | CFG+dominator over decompiled corpus → per-bit-write-site SC/flag windows | SHIPPED (rung 0) |
| Completion Journal | `[[section]]`/`[[section.beat]]` catalog → live `.eb` checklist marks, next-objective ladder, rank expressions, missable verdicts; in-game 3-tab Journal menu (M0-M5) | IN-FLIGHT (M0-M3 owner-confirmed, M4/M5 playtest-pending) |
| `[[on_entry]]` / `[startup]` / flag registry | Worldmap Navi known-location words, flags/flags-diff/flags-inspect | SHIPPED |
| New Game entry | Stock field-70 `Field(<id>)` override + auto re-wire on campaign deploy | SHIPPED |

## F. Co-op (field + battle)

| Name | What | Status |
|---|---|---|
| F1 field lockstep | Solo benches proven unattended (s84) | IN-FLIGHT (two-machine pending) |
| F3.1 talk relay | Solo-proven (s85, v13) | IN-FLIGHT |
| F2 headline boxes | Proven 2026-07-23 | SHIPPED-UNPROVEN→proven |
| `[[coop]]` plates | See §A | SHIPPED |
| Battle co-op / visitor mode | State-mirror lane; CLI + Workspace Co-op tab | IN-FLIGHT (solo proven, two-machine pending) |
| Co-op gateways / camera / platforms-teleport / inventory-authority | Research passes only | STUDY-ONLY |

## G. Overworld / vehicle lanes that bottom out in `.eb`

| Name | What | Status |
|---|---|---|
| `world-entrance --action-prompt` | The faithful "!" confirm-to-enter overworld entrance | SHIPPED |
| `world-entrance --nameplate-name` | Custom-named native entrance via AREA-SWITCH SURGERY | SHIPPED |
| `world-entrance --field-direct` | Real zone-in (fade + arrival sentinel) | SHIPPED |
| Custom vehicle (crimson Blue Narciss) | Boarding plate, engine-legality dismount, moor-home, wake/land-anywhere/seal/standoff | SHIPPED (owner-confirmed, Southern Ring R5) |
| `[[ferry]]` + `depart_code` | Ferry departure arms, symmetric origin-port departures, s69 minimap bracket | SHIPPED |
| `world-encounter-frequency` | The REAL per-zone overworld encounter-rate lever (ENCRATE ladder) | SHIPPED |
| Path D 3rd overworld | Rungs 0-6 done, 9013 round trip owner-confirmed, bench 30950 entry + "!"-Confirm exit | IN-FLIGHT (§8 polish at owner's call) |

## H. Other in-flight / study-only `.eb`-adjacent surfaces

- **Click authoring** — click-on-the-art placement of NPCs/props/**trigger regions**; rungs 0-4 + 6a-6d owner-confirmed, 7e/7f built, Trace rig. IN-FLIGHT.
- **In-game test harness** — agent-driven input injection against a live FF9 (navigation axes, character walks). IN-FLIGHT (proven 2026-08-27).
- **Cutscene DOC TAB** — scene rail, step ladder, stage, beat storyboard. SHIPPED offline, playtest pending.
- **Floorplan** — hand-drawn multi-room plan → wired dungeon (gateways generated). SHIPPED.
- **Interactive docs (docsite/)** — live at jawnston.com/ff9docs. IN-FLIGHT (S1-S7 playtest pending).
- **Messages survey** — complete opcode/flags-byte map; `[WDTH]` dummied; only 64 field text blocks for 831 fields. Research consumed into the shipped window/beat/colour vocabulary. STUDY (survey) + SHIPPED (product).
- **Movement survey** — the four engine gates + pause umbrella, THE CONTROLLER-DEACTIVATION LAW, the pad-mask-kills-the-menu trap. STUDY + SHIPPED (`entrylock`, `lock`/`lock_menu`, twist).
- **Folklore SUBMENU** (own main-menu row, two-pane NGUI) — DESIGN COMPLETE, NOTHING BUILT. STUDY-ONLY.
- **Deploy isolation (per-checkout leases)** — DEFERRED, first draft falsified. STUDY-ONLY.

---

## I. DEAD ENDS that touch `.eb` — do NOT re-propose

From CLAUDE.md §8 (each cost real rounds; all falsified):

1. **Hades Workshop "Export as Custom Field"** — systemic atlas-clone UV bug (A/B tested).
2. **HW adding a new `.eb` entry** — corrupts the file, overwrites the player object. Python only, always.
3. **Encoding a field warp as opcode `0x2A`** — that's `Battle`, not PreloadField → crash/black screen. (`Field` = 0x2B; real `PreloadField` 0xFD is a no-op hint on Steam.)
4. **Grafting a render-only NPC's talk handler into a NON-verbatim fork (#14)** — 0-tractable across a 675-field census; an NPC's interactive tag-3 IS the field's quest logic, inseparable. Use `--verbatim`. (Adding NEW *self-contained* kit content onto a verbatim fork IS supported.)
5. **Path B — a compiled dynamic Chase/Wander region test in `.eb`** — no sound `(x,z)`→region test exists: cross products overflow the 26-bit CalcStack on 36% of fields, the AABB fallback misclassifies 20.8%, and `PathTo` sums with scripted Walk in the same frame. (Dividend kept: computed array indexing `0xD3`.)
6. **THE TOPOGRAPH 36-38 ENCOUNTER LAW** — falsified in-game twice. `case 205`/`w_frameEventBattleProb` is the RAGTIME MOUSE; ordinary encounters are `ProcessEncount` + a per-ZONE `ENCRATE` ladder, safety is an AREA-table hole. `world-encounter-rate` is a misnomer.
7. **The self-summon `--action-prompt`/`--nameplate` overworld entrance** — too timing-fragile; superseded by AREA-SWITCH SURGERY.
8. **A uniform `orgPos/2` walkmesh slide / an `f0`-vs-`+org` frame auto-detector** — the import frame is always `vert + orgPos + floor.org`. No heuristic.
9. **A no-art camera REFRAME on import** — floor-aim flips sign on up-pitched cameras. Removed.
10. **The FieldCreator 5-point camera anchor on a flat floor** — mathematically degenerate.
11. **Per-pitch `sx/sy` canvas scale** — the map is exact scale-1; the apparent drift was the character collision radius.

Non-§8 but equally settled, worth not re-proposing:
- **A text_block offset band (`40000+id`)** — Int16 wrap, loads zero text. And "pick a real id no higher folder defines" is the ANTI-pattern (flat global mesID namespace shared with the base game).
- **Story flags in the 8512+ band** — live save-corrupter; 8512-8711 is stock read-mail payload, 8376-8511 is the Mognet lock band. `FIRST_SAFE_FLAG` = 8712.
- **An object Init that returns before `SetModel`** — THE OBJECT-INIT GATE LAW; story-gate the `InitObject` CALL SITE instead.
- **A hand-rolled looping NPC-AI referee in raw `.eb`** — the ~500-line fort-condor referee was DELETED; the behavior compiler subsumes it.
- **JSON anywhere in engine-side code** — THE NEWTONSOFT LAW (Unity-5.2 Mono TypeLoadException). TSV records only.
- **Silent compiler escalation past the `.eb` budget** — THE ESCALATION LAW: an unknown opcode on stock Memoria is a silent no-op, not a crash; escalation must be declared, never inferred.

---

# Brief: Constraints

Writing the brief now.

# CONSTRAINTS BRIEF — what bounds any new `.eb` idea

Judge every proposed mechanic against these. Each is engine-fixed or law-fixed; none is removable by a compiler pass. Citations are `path:line` in `<repo>`.

---

## 1. The ~64KB whole-file budget (the hardest ceiling)

- **The number: `EB_FILE_BUDGET = 0xFFFF`** — `ff9mapkit/ff9mapkit/binutils.py:39`. It is an **OFFSET** budget, not a file-length budget: `eb_budget_used(b) == len(b) - ENTRY_TABLE_OFF` (`binutils.py:56-62`, `ENTRY_TABLE_OFF = 0x80 = 128`, `eb/model.py:40`). A meter reporting raw `len(eb)` disagrees with enforcement by 128 bytes.
- **Enforced at exactly two write sites**, both strict-raise: `binutils.py:101-111` (`set_u16`) and `eb/edit.py:116-123` (`append_entry`). `pu16` (`binutils.py:74-82`) was the sibling masking-bug; it is now strict too. **Nothing else spends the constant** — `build.py`'s `FieldResult` still has no `eb_size` field, `lint` has no `budget` bucket, `tools/deploy_field.py` has no validation step. So **an idea that claims "we'll see the meter warn us" is claiming a thing that does not exist yet** (studies/eb-budget/PLAN.md §3.3 names all four unfinished call sites; only `journalfield.py:1364-1369` measures at all).
- **Everything in one field shares it**: behavior ticker + dispatch + duty bodies + dialogue + gateways + cutscenes + chests. Measured receipts (studies/eb-budget/PLAN.md §1):
  - fort-condor donor, behavior bodies alone: **≈50-55 KB**
  - bench ISLES 30416 ticker alone (14-unit brawl): **33,820 B**, in-game proven
  - 20-ally × 6-raider counter cross-product: **exceeds the whole file**
  - field 559 naive per-pair region test: **48 KB**, would not assemble (interval compression → 8,140 B, 0.17×)
- **What over-budget costs:** a build ERROR today (good). Historically it masked to garbage function tags with no error at the write site → black screen at playtest. Any idea that pushes a field over is not "slow", it is **unbuildable**.
- **Two adjacent u16 limits, distinct:** `EB_ENTRY_SIZE_MAX = 0xFFFF` is the slot record's own `size` field (`binutils.py:48-53`) — one entry body cannot exceed 64KB either.
- **Structural ceilings around it:** entry table = **255 slots max** (`entry_count` is header byte 3 — `eb/edit.py:67`, `ENTRY_TABLE_MAX = 255`), **255 functions per entry** (func-count is one byte, `eb/edit.py:194` reads `fc = b[es+1]`), **≤255 bytes of per-instance locals** (`loc`/`varn` is u8, `eb/edit.py:133-136`). Object uids: `Obj.uid` is a Byte, 250-255 reserved (250=controlled, 251-254=party, 255=gCur) → **~0-249 addressable**, and a uid collision *silently disposes* the previous holder (studies/fort-condor/RUNG0.md §5).
- **Measure the FINAL assembled bytes.** `labelasm` island insertion adds 6 B per island after the fact (`eb/labelasm.py:170`), so any pre-relaxation estimate under-reports.
- **The cheap relief levers, before proposing engine work:** table-ize cross-products onto `0xD3` VECTOR indexing (§3 below), find the structure before unrolling (the 559 0.17× result), and push pure tuning data to CSV where the engine already reads it generically.

---

## 2. The 26-bit CalcStack value envelope

- **`EXPR_VALUE_MIN/MAX = ±(1<<25)`, i.e. −33,554,432 … 33,554,431** — `ff9mapkit/ff9mapkit/eb/opcodes.py:543-552`. Grounded in `EBin.expr_Push_v0_Int24` (EBin.cs:1270-1274), read back as `(t0 << 6) >> 6` (EBin.cs:1682-1684).
- **Overflow does not truncate — it changes the variable's CLASS.** The push ORs the Int26 class tag into bits 26-28 with **no mask on `_v0`**, so a too-large intermediate's high bits collide with the VariableSource field and the entry is re-read as a *different variable class* (`opcodes.py:545-550`; studies/sims/PLAN.md:62 records the same: "26-bit overflow RE-READS as a different variable class — not truncation"). This is a silent-wrong-answer failure, not an exception.
- **Only a BARE TERMINAL var token bypasses the push** and returns full Int32 via `getv()` (`opcodes.py:551-552`). Any *computed* intermediate is capped.
- **There is NO stack-DEPTH ceiling** — `CalcStack.push` grows its `List<Int32>` on demand (CalcStack.cs:9-15,76); deepening an expression is free (`eb/exprsem.py:30-32`). Depth is not the constraint; **value magnitude is**.
- **Underflow is soft and therefore worse than a crash**: `CalcStack.pop` on an empty stack logs `[CalcStack.pop] topOfStackID == 0` and **yields 0** (CalcStack.cs:17-27, `eb/exprsem.py:26-29`). In a per-tick HUD value that is one log line per frame plus a silently wrong number; downstream it has produced secondary crashes (the overworld vehicle-profile case: "underflow itself is soft… the crash is a secondary fault off the corrupt branch", `docs/OVERWORLD_ENGINE.md` Player-capabilities §).
- **The falsified precedent to not re-litigate:** exact point-in-region = cross products, which **overflow on 244/674 real fields (36%)**; the overflow-safe AABB fallback **misclassifies 20.8%** of occupiable points on field 559 (studies/behavior-trees/PLAN.md:395-420). Any idea needing exact 2D geometry in `.eb` is already dead.
- Offline guard that exists: `eb/exprsem.py` `analyze()` walks the RPN stream with each operator's true arity and refuses an underflow / a stream not ending at exactly one value. Use it; `exprasm.assemble()` alone does **no** arity or balance checking (`exprsem.py:1-8`).

---

## 3. Jump range, island relaxation, and what it costs

- **All three jumps carry a 16-bit offset from the instruction's END** (`eb/labelasm.py:14-19`, engine `EBin.jumpToCommand`):
  - `0x01` JMP — **signed**, ±32,767
  - `0x03` JMP_IF — **signed**, ±32,767
  - `0x02` JMP_IFNOT — **unsigned**, forward-only, reach 65,535. A backward JMP_IFNOT is a **hard error at emit** (`labelasm.py:203-204`); no island can rescue it, because no island can make a backward hop unsigned (`labelasm.py:73-79`).
- **Relaxation exists and works**: an out-of-range jump is re-routed through an inserted **6-byte island** (`JMP skip; island: JMP target; skip:`), iterated to a fixpoint since each insertion shifts later offsets; chains form naturally; same-target long jumps **reuse** an in-reach island (`labelasm.py:21-34, 93-132, 135-171`). Placement aims at `_SIGNED_REACH = 30000` / `_UNSIGNED_REACH = 63000` while detection uses the true `_SIGNED_MAX = 32767` / `_UNSIGNED_MAX = 65535` (`labelasm.py:42-50`).
- **Two invariants relaxation must not break**: a body with no long jump assembles **byte-identical** to the pre-relaxation encoder (golden stability), and **an island is never inserted between an expression statement and the conditional that consumes it** (`labelasm.py:30-34, 149-153`) — the CalcStack desync law.
- **The cost:** islands add bytes to the §1 budget, and convergence is capped at `max(400, 2*njumps + 64)` rounds (`labelasm.py:182`); non-convergence raises. So "just make the ticker bigger" trades §1 headroom for §3 headroom, not for free.
- Consequence for ideas: **the ±32K body wall is gone, the 64KB FILE wall is not.** A proposal whose selling point is "one giant body" is fine on jumps and fatal on budget.

---

## 4. The stock-Memoria vs DWIX-engine escalation law

- **The split (CLAUDE.md §5):** a **novel** field runs on **stock** Memoria; a **forked** field REQUIRES the s23-s33 fork-gate suite. Engine-independence is a live, user-facing property of the kit — an idea that quietly revokes it is a regression, not a feature.
- **Why unknown opcodes are worse than a crash:** on a stock install an unrecognized opcode falls through `EventEngine.DoEventCode()`'s `default: return 1` — **a silent no-op with no log** (studies/eb-budget/PLAN.md §2). Wrong behavior with no evidence is the exact black-screen-at-playtest class this project keeps paying for.
- **THE ESCALATION LAW:** an `.eb` never leaves stock-compatible without the author being told in the same breath. `engine = "stock"` is the default and over-budget is a build ERROR; `"dwix"` stamps an engine requirement into the built mod that deploy honors; `"auto"` may escalate but **loudly** — logged plus a lint finding naming the exact byte count that forced it. The extended path's first runtime act must be a **capability probe** so a mis-shipped mod says so instead of no-op'ing.
- **There is no zero-rebuild hook for `.eb` execution.** `DoEventCode()` is a ~3,509-line hand-written `switch` over ~262 opcodes ending in `default: return 1` — **no reflection, no `ScriptsLoader`, no unused slot, no callback list**. `Memoria/Field/SFieldCalculator.cs:24-46`'s `[FieldAbilityScript]` *is* a real zero-rebuild reflection hook but fires **only on a field-usable ability/item cast from the menu** — useless for always-running actor AI (studies/eb-budget/PLAN.md §5). Anything general is a genuine base-engine patch → DWIX-only → forks-only shipping.
- **Never open a PR to upstream `Albeoris/Memoria`** (CLAUDE.md §2). Engine work stays local on the `memoria-patches/` stack.

---

## 5. Story flags: the safe band and GLOB vs MAP

- **`FIRST_SAFE_FLAG = 8712`** — `ff9mapkit/ff9mapkit/flags.py:53`. The usable custom window is **[8712, 16320)** (`CHOICE_SCRATCH_FLOOR = 16320`, `flags.py:69`); `is_safe_bit` enforces it (`flags.py:501-503`) and authoring validation refuses outside it (`flags.py:563-576`).
- **Reserved, do not allocate** (`flags.py:31-52`):
  - 8192-8367 stock **Mognet mailbox** (Byte[1024-1045]), written by ~48 real moogle fields in ordinary play
  - 8376-8511 **Mognet one-shot lock band** (give 8376-8439 / read 8440-8503) — long mislabelled "the chest bitfield"
  - **8512-8711 stock READ-MAIL payload** — whole-byte-written on every Mognet open. **The old "8512 is safe" claim came from a bool-only census and is a live save-corrupter.**
  - 16144-16255 `[[qte]]` modal scratch; 16256-16319 netsync co-op cells, **rewritten by the engine every frame** while co-op runs
- Auto-allocation bases already carved out of the band: `AUTO_CUTSCENE_BASE = 14704` (`flags.py:107`), plus campaign/journey lanes partitioned from `FIRST_SAFE_FLAG` (`flags.py:72-99`). A new mechanic that wants a block of flags must claim a *named* band, not squat.
- **GLOB vs MAP is a persistence decision with a crash edge:**
  - **GLOB** = source 0, token `0xC4` = save-backed `gEventGlobal`, **2048 bytes total** (`flags.py:1-6`), persists across field reloads and saves.
  - **MAP** = source 1, token `0xC5` = per-field, **WIPED on every field load**.
  - **`EventContext.mapvar` is only 80 bytes** — a high MAP index is out of bounds and is a **hard crash** (`content/choice.py:34-36`; skill `authoring-ff9-field-scripts/SKILL.md`, Flag-persistence §). HW's naming of the two is **inverted** — do not trust an HW-derived note.
  - Addressing: a **Bit** index N → byte `N>>3`, bit `N&7`; a **Byte/Int16/UInt16** index is a **raw byte offset** (`flags.py:17-21`). "Bit 184" and "byte 184" are different locations.
  - Indices > 0xFF need the long-index token encoding.
- **`gScriptVector` also rides saves** (JsonParser) — a vector-backed idea inherits stale state across sessions; the `size←0 / size←n` seed idiom is law (studies/behavior-trees/PLAN.md:~608).

---

## 6. Text blocks: one flat GLOBAL mesID namespace, shared with the base game

- `FF9TextTool` merges per-txid **cumulatively**, so custom text written on a REAL block **overwrites that location's shipping dialogue**. Known collisions: **1073 = Black Mage Village, 8 = Ice Cavern, 22 = Lindblum**. **There is no free real block** — "pick a real id no higher folder defines" is the anti-pattern (CLAUDE.md §5).
- `text_block` **defaults to 1073** (`docs/FORMAT.md:93`), which is only safe because each custom field ships its own `.mes` at that block *in its own mod folder*; **two members sharing a block in one folder overwrite each other** (`docs/CAMPAIGN_IMPORT.md:323`). The kit's newer guidance is a **minted** block per field with `register_text_block = true` (`docs/FORMAT.md:1076-1077`).
- **Never use an offset band.** Consumption is Int16, so `40000 + id` wraps and loads **zero text**.
- **A fork keeps its donor's block** — voice acting and dual-language key off it.
- **Registration changes need a RELAUNCH; content edits hot-reload.** An idea whose iteration loop depends on minting new blocks pays a relaunch per iteration.
- TXID layout inside a block: authored dialogue is allocated `start_txid + i` from `DEFAULT_BASE_TXID` (`content/text.py:856-888`); explicit-txid entries are **only legal in a field's OWN minted block** (`content/text.py:893-901`).
- Live registrations are only readable from the deployed file: `grep -oE "FieldScene [0-9]+" <game>/FF9CustomMap/DictionaryPatch.txt`. EventDB/SceneData ids are **global across stacked mod folders**; a collision is the classic null-`.eb` black screen. Bands: 10-3100 real (locked) · 4000-9899 shipped custom · **9000-9012 is a RESERVED HOLE** (engine world-map location ids) · 30000-32767 dev scratch (`fldMapNo` is Int16, max 32767).

---

## 7. The per-frame execution model

**`.eb` is cooperative, per-object, and non-preemptive. There is no instruction quota — a tight loop with no yielding opcode hangs the field.**

- **Tick driver:** logical tick ≈ **20 fps**, render ≈ 60 fps (`docs/OVERWORLD_ENGINE.md`, Update/tick architecture). Per tick the chain is `w_frameUpdateEvent()` → `ServiceEvents()` → `ProcessEvents()` → **`eBin.ProcessCode()`** (`docs/OVERWORLD_ENGINE.md:18`). A logical-tick change shows ~2-3 render frames later.
- **Each object entry has its own script thread with its own `wait` byte.** `EBin.ProcessCode` (EBin.cs:136-157) runs, per object, per tick:
  ```
  if (s1.wait != 0) {
      if (s1.wait == 254) { if (s1.winnum == 255) s1.wait = 0;
                            else if (!ETb.MesWinActive(s1.winnum)) { s1.winnum = 255; s1.wait = 0; } }
      else if (s1.wait != 255) s1.wait--;
      next0(); continue;               // this object is skipped this tick
  }
  ```
  (quoted at studies/field-coop/interactions-census.md:88-103 and studies/field-coop/dialogue-sync.md:21-30).
- **Yielding is opcode-driven, and `gCur` is the CALLING OBJECT only** — not the engine as a whole. `Wait(n)` = `0x22`, encoded `22 00 nn` with a **1-byte** count (`eb/edit.py:475`, `eb/opcodes.py:188`). Window ops `MES`/`WindowSync` `0x1F`, `MESA`/`WindowSyncEx` `0x95`, `WAITMES` `0x54` all end `this.gCur.wait = 254; return 1;` — **only that object's thread stalls** (dialogue-sync.md:11-19).
- **A blocked object is not polling.** While `wait == 254` the interpreter skips the object entirely; `B_KEYON` is not read. The window is closed by a wholly separate consumer of Confirm — `UIKeyTrigger.HandleDialogControlKeyPressCustomInput` (UIKeyTrigger.cs:798-825) reading `HonoInputManager.IsInputDown` directly, **not** through `ETb.KeyOn()`/`B_KEYON` (interactions-census.md:88-112). Script-side and UI-side Confirm are two independent lanes; a guard in one cannot touch the other.
- **Dispatch terminators end the pass** via the engine's `adFin()`: `RET 0x04`, `TerminateEntry 0x1C`, `Battle 0x2A`, `Field 0x2B`, `STOP 0x4F`, `TetraMaster 0xAE`, `WorldMap 0xB6`, `GameOver 0xF5` (`eb/disasm.py:148-155`, `TERMINATOR_OPS`). A path that falls off a function end with no terminator runs the IP into adjacent bytecode — `eblint.py` flags it as an ERROR.
- **Other blocking ops** (each blocks the calling object only): `WaitSharedScript 0x44` joins only the object's OWN shared script, not a global barrier (`eb/opcodes.py:107-110`); `WaitTurnEx 0xBC` / `WaitAnimationEx 0xBE` **hang on a player clone** (`eb/opcodes.py:141-153`); `WAITANIM 0x41` blocks until the clip finishes (`content/behavior.py:459`).
- **Dispatch gating:** `ProcessEvents.cs:180-181` gates **new CollisionRequests** on `usercontrol`, **not** the stepping of an already-running body (`eblint.py:57-62`). 518 stock tag-2 bodies block under their own lock and work fine — so "it blocks under a lock" is not itself a defect signature.
- **The real perf wall is not instruction count — it is movers.** `WalkMesh.Collision` linearly scans **every** active object (WalkMesh.cs:912-962) and is called **per moving actor per frame** (FieldMapActorController.cs:762) → O(n²). Many objects is cheap; many simultaneous **movers** is the wall (studies/fort-condor/RUNG0.md §5). Stock never ships more than **23 model actors** on one field; census p50/p90/p99 of model-bearing actors is 5/11/18 (RUNG0.md §6).
- **Per-iteration cost of vector-indexed expressions is the measured frame budget**: ~**200 iterations/tick** (studies/behavior-trees/PLAN.md:~608). A bounded in-tick loop is fine; an unbounded one is not.
- **There is NO dialog lock in the engine** — control is a *script convention* (`eblint.py:33-42`). The only defense against a shipped softlock is static lint. Budget for that in any idea that locks movement.

---

## 8. Region tags 2 / 3 / 10

- **tag 2 = tread**: fires **every frame** the player is inside the quad (level-triggered — `content/event.py:375`). Used for "!" bubble arming and auto-fire on walk-in.
- **tag 3 = press-to-interact** (the action/Confirm receiver; also the NPC talk handler — `dialogue.py:72`). **The func MUST be ≥ 9 bytes** or you get per-frame `IndexOutOfRangeException` log-spam: `IsActuallyTalkable` polls `tag3[ip+7]` / `[ip+8]` every frame the player is near it, so a shorter func indexes past the entry buffer (`.claude/skills/authoring-ff9-field-scripts/references/eb-opcodes.md:54-56`).
- **tag 10 = `Main_Reinit`**, entry-0 — the **after-battle re-entry** (`eb/cfg.py:750`, `MAIN_REINIT_TAG = 10`). A field cloned from a cutscene field **without** it **softlocks after battle**: `EnterBattleEnd` suspends objects and nothing resumes them.
- **Other tag facts that bound ideas:** tag 0 = Init, tag 1 = Loop. **Actor choreography must run in the LOOP (tag 1), never Init (tag 0)** — Init runs at `state == 2` where `ProcessAnime` never advances `animFrame` (transform moves, skeleton freezes). **An object's Init must NEVER return before `SetModel`** — a passing gate loads the object permanently HIDDEN (interactable, unrendered); 18,688 stock inits, **zero** early returns. Story-gate the `InitObject` CALL SITE in `Main_Init` instead.
- **A func tag is NOT unique inside an entry** — 15 of the 818 shipping EVTs repeat one (`evt_dali_v_dl_wms0` entry 18 lists tags 13 and 14 twice), so any tool addressing functions must go **positionally** or it silently edits the first namesake (`eb/edit.py:215-229`).
- **Trigger firing is gated on `usercontrol == 1`.** Polygon point ORDER sets the exit walk-out direction. `IsInQuad` tests a fan of consecutive vertex triplets — **collinear points are a dead zone**; use a convex quad with the last vertex DOUBLED. There is a known **>2-region silent-arming bug** (see `references/regions-encounters.md`).
- **Contact is player-centric.** tag-2/Range fires from the PLAYER's collision request (`EventCollision → CheckNPCInput` is controlled-char-driven) — **unit-vs-unit engagement must be distance-polling**, not contact (studies/fort-condor/RUNG0.md §4).
- **Never stack two Confirm receivers.** A talky NPC parked inside an action zone EATS the press inside its arc (the fort-condor "one-Confirm-receiver" lesson, studies/behavior-trees/PLAN.md:~262). Bind the menu to the TALK.

---

## 9. The `0x2A` Battle vs `0x2B` Field trap

- **`Field = 0x2B` (MAPJUMP) is the real field warp** — `eb/opcodes.py:508`, `eb/edit.py:500`, `eb/ebsrc.py:95`, `_optables.py:345`.
- **`Battle = 0x2A`** — `_optables.py:344`, `eb/ebsrc.py:96` (`scene = btlId & 0x7FFF`, arg 1). Encoding a warp as `0x2A` **literally starts a battle using the field id as the scene id** → crash / black screen. Explicitly warned at `eb/opcodes.py:505-507` and burned in at `content/ladder.py:413` ("emitting 0x2A here literally fired a battle using the field id as the scene"). It is in §8 of CLAUDE.md as a proven dead end.
- **Real `PreloadField = 0xFD` is a no-op HINT on Steam** — it does not warp; do not build a mechanic on it.
- **`0x01` is an undocumented unconditional JMP.** Do not overwrite a `Wait` that sits right after one — the activation gets skipped (`.claude/skills/authoring-ff9-field-scripts/SKILL.md`, opcode-traps §). This matters because the kit's shift-free edit idiom is "overwrite a 3-byte `Wait(n)` filler with an equal-length op" (`eb/edit.py:13-17, 475, 529`).
- **A field→field warp MUST fade to black BEFORE `Field()`.** Both `0x2A` and `0x2B` are `adFin()` terminators (`eb/disasm.py:148-155`) — nothing after them in the body runs.
- **A computed warp exists**: `Field(<VAR>)` = `0x2B` with its argFlag bit set (`content/region.py:286`), so destination-by-expression is available without an engine patch.

---

## 10. What `.eb` genuinely CANNOT do (these need a DLL patch)

If an idea lands in this list, it is DWIX-engine-only — i.e. it ships only with forks, breaks the novel-field stock guarantee, and needs the §4 declaration/stamp/probe.

1. **Any new opcode or extension point at all.** `DoEventCode()` has no reflection, no loader, no free slot, no callback list (§4). `[FieldAbilityScript]` only fires on a menu-cast field ability — not a general hook.
2. **Exact point-in-region / point-in-triangle geometry.** Falsified by the 26-bit envelope (36% of fields overflow) and the 20.8%-misclassifying AABB fallback. Portal-crossing dead reckoning is expressible but desyncs on any teleport (including `MoveInstantEx`, which the pooled-unit vocabulary fires on *every spawn*) with no sound recovery test (studies/behavior-trees/PLAN.md:395-425).
3. **Engine-driven pathfinding (`PathTo`).** `MoveNPC()` drains `movePaths` into `moveTarget`, but the scripted walk (`MoveToward_mixed_ex`) writes `curPos` **directly** and never touches `hasTarget`/`moveTarget`/`movePaths` — **both lanes move `curPos` in the same frame, so they SUM.** Adopting it costs the proven blocking-`Walk` core, per-action `speed=` (hardcoded `30f`, FieldMapActorController.cs:107, refreshed only for the player at :211) and the walk animation (the walk/idle auto-switch is inside `if (FF9StateSystem.Field.isDebug)`, :367) (studies/behavior-trees/PLAN.md:~430-455).
4. **Per-field engine gates a fork does not inherit** — the whole s23-s33 class: narrow-map width, off-mesh exemptions, the fake-battle return field, `DoEventCode`'s ~150 `mapNo == N` local-alias gates, the NAME-keyed `FieldMapExtraOffset` overlay z-offsets, SPS offsets, the menu LOCATION name lookup, the field→battle BGM fallback, mesh-combine, smooth-cam. See `memoria-patches/README.md` — its per-patch table is authoritative over any range quoted elsewhere.
5. **Loose world-map mesh/texture overrides** (s34 `WorldMeshOverride`, hooked in `WMWorld.RegisterBlockComponent`) — FF9 is Unity 5.2.3, `AssetManager.LoadFromDisc<Mesh>` is unsupported, so there is *no* loose-mesh path without the patch.
6. **The overworld no-controlled-actor self-heal** (s39) — a black screen baked into the save, unrecoverable from script.
7. **Anything the engine simply never reads.** From the Path-D arc: WorldMap/Terrain binds **NO normal**, so a ground/uv/normal fix in script is a fix for a mechanism nothing consumes (CLAUDE.md §7).

**What `.eb` CAN own end to end** (do not propose an engine patch for these): the whole event script, camera + walkmesh math, gateways/triggers/flags, dialogue/text, encounters + BGM + battle-bg metadata, behavior trees (patrols/chases/waves/pools/timers), chests, savepoints, ATEs, ladders, jumps, moving platforms, shops, custom playable characters, custom models and animations, items/equipment — all zero-DLL, stock Memoria.

**The one free dividend worth designing toward:** stock Memoria **already** gives `.eb` **computed array indexing** — expression token **`0xD3` flexible_varfunc** (u16 command + u8 argc, args popped off the CalcStack; EBin.cs:331/351) exposing **`VECTOR` (cmd 20) / `VECTOR_SIZE` (21) / `DICTIONARY` (22)**, backed by `FF9StateSystem.EventState.gScriptVector` (`List<Int32>`, stack-supplied index, save-persisted through JsonParser). Added upstream in `91e94a66` (2023-09-23), verified an ancestor of our pinned base `6b8bb2d5` ⇒ **available on stock at zero engine cost** (studies/behavior-trees/PLAN.md §8). `0xD3` is already carved out of the var-token space in all four expression walkers (`eb/disasm.py:172-175`; eb-roundtrip PLAN §1). Caveat: a `0xD3` statement writes engine state, so the CFG analyzer treats it as killing every guard (`eb/cfg.py` `stmt_write_effect`, `lead == 0xD3 → "ALL"`), and `exprasm` could not emit it as of the behavior-trees writeup — check current status before assuming emission.

---

## 11. Process constraints on any proposal

- **A green gate suite is a regression harness, not an oracle.** Measured over the Path-D wall arc: **0 of 13** playtest verdicts were predicted by a gate. Offline ≠ in-game proof.
- **THE DEFECT FOLLOWS THE AUTHORSHIP.** 12 of 13 verdicts / 32 of 37 named defects in that arc landed on whatever the round had most recently authored. **The cheapest way to stop minting defects is to stop minting surface** — weight an idea's new-surface count as a cost, not a feature.
- **Fork or learn from a real field's bytes BEFORE authoring a new mechanic.** Every mechanic in the kit was grounded byte-for-byte against shipping FF9 data. A bytecode SHAPE grounded nowhere in stock (e.g. the bounded in-tick loop) needs the verbatim-first treatment and its own bench.
- **One change per in-game test**; a build that succeeds proves nothing about behavior.
- **Round-trip is the review surface.** `eb-src` / `eb-asm` round-trip **9753/9753** event binaries byte-exact, with `eb-asm --against <donor.eb>` splicing only changed functions (a one-operand chest edit moves **1 byte of 9268**) — so an idea that produces reviewable `.ebs` diffs is cheaper to land than one that only produces bytes (studies/eb-roundtrip/PLAN.md status block, Rungs 6-7).
- **A law in a docstring is a wish.** A constraint not enforced at the call site is not enforced — the §1 meter is the standing example of a correct mechanism with no call sites.

---

# Brief: Engine services reachable from .eb

**Evidence base:** `memoria-patches/README.md` (376 lines, 34 live patches), `ff9mapkit/ff9mapkit/eb/` (5,647 lines), opcode census run over the whole package.

---

## 1. The headline number

`eb/_optables.py` names **230 opcodes**. A census of every `.py` in the package (excluding the tables, disassembler, and tests) shows **91 named opcodes the kit never emits or references anywhere**. The engine's `.eb` surface is roughly **60% exploited, 40% dark** — and almost all of the dark part is *stock* Memoria, so it costs **zero engine change and keeps novel-field stock compatibility** (the §5 engine-independence split). That is the cheapest lane on the board by a wide margin.

Full unused list, grouped by service:

| Service | Unused opcodes | What it buys |
|---|---|---|
| **Tile / texture animation** | `0x5A 5E 5F 60 61 63 64 65 C0 C1 C2 C3 C9 CA E4 E6 ED 11C` (18) | The kit touches only 6 tile ops (`content/gauge.py`'s HUD). The rest is the BG-layer animation engine: `RunTileAnimation(Ex)`, `SetTileAnimationSpeed/Pause/Flags`, `SetTileLoopAlpha`, `SetTileCamera`, `SetupTileLoopingWindow`, `EnableTextureAnimation`/`RunTextureAnimation` (UV scroll). Animated water/fog/rain curtains, parallax, a lit-window night pass — **on art that already exists in any fork**. `SetTilePositionTimed` (0x11C) tweens with no per-frame script. |
| **Weather / color** | `0xD8 SetWeather`, `0x8F SetModelColor` | `SetWeather` is emitted by nothing in the kit. Paired with the already-used `FadeFilter`/`SetBackgroundColor`, this is a one-command "night mode / storm mode" pass over **any forked field**. |
| **DrawRegion (scissor)** | `0x76 77 78` | An untouched *rendering* service: letterbox, split panes, picture-in-picture, a vision-cone/flashlight mask, a spyglass. Nothing in the repo has ever decoded it. |
| **Camera** | `0x1E SetCameraBounds`, `0x72/73/74` follow-height + follow on/off | The kit drives `MoveCamera`/`ReleaseCamera` only. Follow-cams and camera bounds are the missing half of the scene-ladder's rig work. |
| **Positional sound** | `0x89 SetSoundPosition`, `0x8A SetSoundObjectPosition`, `0xC6/0xC7 RunSoundCode1/2` | Audio attached to a moving actor. Stealth cues, a fountain you hear before you see, doppler on the ferry. |
| **Vibration** | `0xF6–0xFC` (7 ops) | Entirely unused, and `s62` already fixed the fork name-key path for `vib.LoadVibData`, so the data lane is live. Rumble choreography + a haptic accessibility lane. |
| **Shadows** | `0x81–0x85` size/offset/rotation-lock/amplifier | Levitation, a moving light source, a giant's shadow — effects with no art cost. |
| **Character DB (Memoria ext)** | `0x112 SetCharacterEquipment`, `0x113 SetCharacterLevel`, `0x114 SetCharacterExp` | **Directly unblocks the narrative-state arc.** A derived mid-story boot currently cannot set levels or gear from `.eb`; these three ops do exactly that, with expression-valued operands. |
| **Battle-adjacent** | `0x11D/0x11E Add/RemoveBattleStatus`, `0x1B ContinueBattleMusic`, `0xDB EnableVictoryPose`, `0xE1 TerminateBattle`, `0xE0 AddFrog`, `0xE5 AttackSpecial` | Field-side status (poison swamp, petrify puzzle, a curse that follows you into battle), seamless boss-chain music, scripted flee/ambush resolution. |
| **Identity / presentation** | `0xB5 PretendToBe`, `0xDE SetName`, `0xB0/0xB1 SetFieldName/Reset`, `0xEF ShowHereIcon` | Runtime location banner ("Alexandria — nine years later"), runtime rename (the caveat `creating-ff9-characters` lists as a known limit), disguise/impostor mechanics that pair with `--swap-player`. |
| **Object rig** | `0xD4 AttachObjectOffset`, `0x39 ShowObject`, `0xD6 ShowAllObjects`, `0x3B SetObjectIndex`, `0x4D DetachObject` | The kit uses `AttachObject` but not the **offset** variant: riding, carrying, mounted actors, held props. |
| **Misc worth decoding** | `0x97 ReturnEntryFunctions`, `0x53 PreventWindowInit`, `0xDA RunSPSCodeSimple`, `0xAC ChangeDisc`, `0x62 SetRow`, `0xA6 SetRunSpeedLimit` | `ReturnEntryFunctions` is dispatch control nobody has looked at. |

---

## 2. The expression side is darker than the opcode side

Unused expression tokens (`eb/_exprtable.py`), each a **read with no engine change**:

- **`B_BGIID` (112) / `B_BGIFLOOR` (113)** — the walkmesh triangle id and floor index **under an actor, readable every frame**. This is a free "what am I standing on" channel: surface-dependent footsteps, damage/ice/slip floors, stealth by floor tag, room-aware music crossfade, a floor-triggered trap — **with no regions, no triggers, no new flags**. Highest ratio of capability to cost on this list.
- **`B_FRAME` (106) / `B_BAFRAME` (101)** — free global frame clocks for deterministic choreography and poll throttling.
- **`B_SPS` (108)** — read particle state; gate logic on *an effect finishing* instead of `Wait(N)`.
- **`B_ANGLEA` (96) / `B_DISTANCEA` (97)** — the object-referencing perception that `content/behavior.py`'s **player-ref eval law** forbids in user conditions (`_FORBIDDEN_COND`). A safe engine-side accessor would lift that law.
- **Sysvars**: `GetSysvar` has ~32 cases; the kit uses only **0, 2, 6, 8, 9, 16, 17, 19, 20** (+ world 193/205/207). Per `studies/field-coop/dialogue-census/census.py:73`, **10–13 are map-jump / system x,y** and nobody has touched them. ~20 cases unmapped.
- **`Null.SBit[n]` (`memoria_variable`, `EBin.cs:2416-2431`)** — a whole read namespace with **zero shipping precedent anywhere in FF9**. Known members: TH points (5), card record (0), collector points (3)/level (4).

### The single biggest under-exploited thing: `0xD3` `flexible_varfunc`

The kit sugars exactly **three** ids — `(20,2) B_VECTOR`, `(21,1) B_VECTOR_SIZE`, `(22,2) B_DICTIONARY` — and everything else round-trips as the generic `flex(id,argc)` **with no emitter**. The registry is at `Global/EBin.cs:2388-2431`. The completion-journal bench already proved the lane works in-game (`studies/completion-journal/PLAN.md:1103`): `flex(13,1)` player level returned 16/22 correctly, `flex(6,1)` actor→id conversion works, `flex(10,1)` party slot works; `flex(16,3)` `PLAYER_ABILITY_LEARNT` came back inconclusive with a **silent-zero path**.

Two consequences:
1. **A systematic `flex` census is cheap, offline-startable, and high-yield** — one bench field, one window, a sweep of ids 0-40 × arities 1-3. Nobody has done it.
2. `B_VECTOR` is a **resolvable LVALUE** that is **save-serialized**: index==size appends, missing id at index 0 creates. That is a real database inside the save file, reachable from stock `.eb`. Unbuilt ideas it makes trivial: the **per-chest registry the journal study says "nowhere — no registry exists"**, a quest log, NG+ carryover, bestiary/kill counters mirrored script-side (the `AchievementState` bucket the journal declared unreachable), the Fort Condor unit roster, co-op session state. `ClearMemoriaVector`/`ClearMemoriaDictionary` (0x11A/0x11B) are the matching teardown ops — round-tripped in `tests/test_ext_opcodes.py`, emitted by nothing.

---

## 3. What this project has already added — and what it implies

**Finding: across 34 live patches, the project has added ZERO `.eb`-facing surface.** 33 patches touch `EventEngine`-adjacent files; not one adds a `DoEventCode` case, a `GetSysvar` case, or a `flexible_varfunc`. Every patch is a *gate wrap* (s23-s33, s62, s65 — `EffectiveFieldId`/`EffectiveFieldName`), a *runtime service in C# that scripts cannot see* (netsync s36-s57/s84/s85, SFX s47-s58, worlddisc s71-s75, journal/folklore menus s45/s46/s81-s83), a *guard* (s39/s49/s51/s60/s61/s64/s66/s79), or *dev tooling* (s22/s43/s70/s78/s80/s83).

What that implies is cheap next:

- **A new extended opcode is additive and low-risk.** Engine side: one `DoEventCode` switch case on the `0xFF` page (0x11F+). Kit side: one entry in the `CUSTOM_EXTENDED` block of `eb/_regen_optables.py` (which already asserts the static tables end at `0x112`), and `tests/test_ext_opcodes.py` is a ready-made template. Every extended operand is read with `getv3` and is **expression-flagged**, so *any new opcode gets computed arguments for free* (proven by `test_extended_expression_arg`). No prefab-layout hazard like s74's serialized-field trap.
- **A new sysvar case is cheaper still** — read-only, 1-byte code, and `eb/exprasm.py` already assembles `B_SYSVAR[i]` for *any* i, so the kit needs no change at all. The obvious first batch is the completion-journal's blocked half: `AchievementState` ATE checks, `modelKillCount`/`categoryKillCount`, bestiary, synthesis/auction counters — each one switch case, each unblocking a journal row that is otherwise unreachable.
- **A new `flexible_varfunc` is the cheapest LVALUE** (assignable + save-serialized, like the vector trio).
- **The `s72` pattern generalizes**: `WorldScene <id> <NAME> [mesID]` in `DataPatchers.cs` shows that a new **DictionaryPatch directive** is a ~50-line, data-driven registration lane. Same pattern would serve `ScriptHook`, `SoundScene`, or a table-driven trigger registry.
- **The `s83` harness proves the "static polled every frame" pattern**: `HarnessAgent` is read by `HonoInputManager` on *every key query of every frame* and bootstrapped from `UIKeyTrigger.Update`. **A symmetric "script bus" — one static array written by any C# subsystem, exposed as ONE new sysvar — would give `.eb` a read channel into netsync, the journal, the harness, the SFX rig, and everything future, for the price of a single switch case.** That is the highest-leverage single patch on this list.

⚠ Cost note for the team: any new opcode/sysvar moves content onto the custom bundle. Novel fields currently run on **stock**. So rank the 91 unused stock opcodes and the dark `flex`/sysvar reads *above* new engine surface wherever they can do the job.

---

## 4. What the engine polls every frame (piggyback points)

1. **Blocked-walk operands are re-read per frame.** `EventEngine.MoveToward.cs` re-reads `actor.speed` on *every frame* of a blocked walk — `content/behavior.py` exploits this for mid-walk speed changes. **The general law is unexplored: any opcode operand that is an expression and sits inside a blocking op is a live per-frame channel.** Worth a systematic sweep of which blocking ops re-evaluate.
2. **The central ticker** (`content/behavior.py`): one seated entry looping `Wait(tick=1)`, ticking every unit per frame, GLOB-fed. Used only by behavior trees today. A field-wide *director* on the same architecture could poll input, timer, floor id, HP, and party state — nothing about it is AI-specific.
3. **Region occupancy** (tags 2/3/10) is evaluated per frame; tag-10 is the `Main_Reinit` after-battle re-entry.
4. **`B_KEY`/`B_KEYON`/`B_KEYOFF`/`B_KEY2`** read live pad state *inside an expression* — real-time input from a script loop (proven by `content/qte.py`). Combine with the **already-used** `AddControllerMask`/`RemoveControllerMask` (`0xB9`/`0xBA` — the one script lock independent of sysvar 2, per `studies/movement/SURVEY.md`) for **partial control**: a field where only one button works. Ritual sequences, rhythm, hold-your-breath, a one-handed section. No engine change.
5. **`B_SYSVAR[17]` = `TimerUI.Time`** — `RunTimer`/`ShowTimer` gives a per-frame decrementing clock readable from any expression (`battle/battleai.py:144`). A free real-time budget for any mechanic.
6. **The netsync lane already writes `gEventGlobal` cells every frame under co-op** (noted in `behavior.py`'s blackboard comment) — an engine→script per-frame channel *that already exists and works*; nothing outside netsync reads it.
7. **`w_frameUpdate` case 0** — the world loop's per-frame hook the project already injects into (s39 self-heal, s64 gate).
8. **`ProcessEncount`** runs per step with the per-zone `ENCRATE` ladder (s60 patched its null path) — the encounter poll is a script-visible cadence.
9. **`GetSysvar(0)` = `Comn.random8()`** advances the shared RNG stream on every read (flagged IMPURE in `eb/exprsem.py:183`) — a per-call entropy source, already used for Wander.

---

## 5. Ranked seeds for the room

1. **`B_BGIID`/`B_BGIFLOOR` floor-awareness pack** — surface footsteps, damage/ice floors, stealth, room-aware audio. Stock, zero engine, reads a value the engine computes every frame anyway.
2. **The `flex(id,argc)` census** — one bench field, offline-authorable, maps a whole unmapped engine API. Probe harness already exists at `studies/completion-journal/bench/`.
3. **`B_VECTOR` as a save-serialized database** — the per-chest registry, quest log, NG+ carryover, bestiary. Closes the journal study's largest "nowhere" cell without a DLL.
4. **`0x112/0x113/0x114` character-DB ops** — the narrative-state engine's missing lever: a derived mid-story boot that sets levels and equipment from `.eb`.
5. **The tile/texture animation pack (18 ops)** — animated backgrounds on art the project already has; the largest untouched *visual* surface, and it sidesteps the "I cannot paint backgrounds" constraint.
6. **One new sysvar = a universal C#→script bus** — the cheapest engine patch with the widest downstream reach.
7. **`SetWeather` + `SetModelColor` + `FadeFilter`** — a one-command night/storm pass over any forked field.
8. **DrawRegion (`0x76-0x78`)** — a genuinely undecoded rendering service; worth one decode round to see what it can frame.