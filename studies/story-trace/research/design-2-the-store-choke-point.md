## 1. Script writes: every .eb store to gEventGlobal goes through one function

- **Choke point: `EBin.SetVariableValue`** (`Global/EBin.cs:1894-1989`). Its `case VariableSource.Global` (`:1902-1904`) calls `SetVariableValueInternal(gEventGlobal, t0&0xFFFF, varType, value)`. That same function also stores Map vars (`:1906`, `GetMapVar()`) and Instance vars (`:1909`), so the trace must filter on `cls == Global`.
- **One store function for all widths** (`EBin.cs:1991-2035`), one switch:
  - Bit/SBit: read-modify-write of the containing byte, `|=` or `&=~` (`:1995-2003`).
  - Int24: 3 bytes (`:2006-2022`, includes the jump-rope reward hack).
  - Byte: 1 byte (`:2024-2027`).
  - Int16: 2 bytes (`:2028-2032`).

  Bit writes and byte writes are not separate paths.
- **Every opcode reaches it.** Opcode 5 `set` → `expr()` (`EBin.cs:1477-1480`). The expression operators that call it:
  - `B_LET` → `SetVariableValue` (`:893-904`).
  - `*_LET` (`:936-1065`) and pre/post `++`/`--` (`:574-613`).
  - The `_A` "all party members" variants → `OperatorAll` → `putv` (`EventEngine.OperatorAll.cs:76,113-128`).
  - The `_E` let-ops → `putv` (`OperatorExtract.cs:200`).
  - `putv` itself is at `EBin.cs:2067-2074`.
  - Opcode arguments evaluate through `getv1` → `CalcExpr` → `expr` (`EventEngine.cs:1332-1338`).
- **C# code can also enter the choke point** through `setVarManually` (`EBin.cs:480-493`). Those rows need to be tagged as non-script (see §3).

## 2. Who wrote it: what is readable at the store

At `SetVariableValue`:
- **Executing object:** the static `EBin.s1` (`EBin.cs:32`). `gExec = s1` (`:158`). `gCur` is the same object, or its parent when `s1.cid == 1` (a shared script started with STARTSEQ): see `EBin.cs:162-165,181`, `EventEngine.cs:38,57`.
- **Obj header fields**, all plain byte reads from `Obj.buffer` (`Objects/Obj.cs:79-137`):
  - `sid` = the .eb entry index; its code is `allObjsEBData[sid]` (`Obj.cs:50`).
  - `uid`.
  - `ip` = an offset into that entry's bytes. At the store it points into the middle of the expression, not at the opcode start. The opcode start is only visible at `EBin.cs:194` (`a0 = s1.getByteIP()`, before `ip++`), so that site would need to latch it.
  - `level` = the running priority level.
- **Function tag: not stored anywhere.** It can be derived cheaply from `ip`. The entry's function table is `[?][count][(u16 tag, u16 off)×count]`, and a function starts at `2+off` (`EventEngine.GetIP`, `EventEngine.cs:1103-1124`). The tag is the one with the largest `2+off ≤ ip`: a scan of about 30 entries, needed only when a byte actually changes.
  - Caveat: when `isAdditionCommand` is set, `ip` indexes `movQData`/`neckTurnData` instead of `ebData` (`Obj.cs:568-579`).
- **Caller:** `Call` pushes the return ip plus the requester's `level`/`uid` onto the object's own stack (`EventEngine.cs:359-374`), and `getSender` reads the uid back (`:381-385`). So "who Requested this function" is recoverable too.
- **Map context:**
  - `FF9StateSystem.Common.FF9.fldMapNo` and `wldMapNo` (`ff9/State/FF9StateGlobal.cs:905,916`).
  - `Memoria.DataPatchers.EffectiveFieldId(...)` gives the fork's donor id (used at e.g. `EBin.cs:323`).
  - `FF9StateSystem.Battle.battleMapIndex` (`BattleStateSystem.cs:74`).
  - `EventEngine.gMode`: 1 field, 2 battle, 3 world, 4 = system mode 8 (`EventEngine.cs:580-595`).

  All are cheap static reads.
- **Battle and world scripts use the same path.** Battle calls `ServiceEvents` at `battle.cs:74,179` and `HonoluluBattleMain.cs:582,744`. World calls it at `WMScriptDirector.cs:60` and `ff9.cs:3744` (`w_frameUpdateEvent`). All of these → `ProcessEvents` → `eBin.ProcessCode` (`ProcessEvents.cs:116`) → the same `SetVariableValue`.

## 3. C# code that writes gEventGlobal outside the expression layer

**Wholesale (these replace or rewrite the whole array):**
- `EventEngine.Initialize.cs:43`: `NewGame()` assigns a fresh `new Byte[2048]` (a new array reference).
- `JsonParser.cs:522`: `ParseEventJsonToData` (save load) assigns `Convert.FromBase64String` (a new array reference).
- `NetSyncState.cs:98-120`: `ApplyStoryTo` copies bytes one by one, skipping the mask 2032-2041 (`:40-41`). Reached via `ApplyStory` `:84-93` ← `NetSyncClient.cs:426` ← `ApplyStoryBeforeEvents` (`HonoluluFieldMain.cs:148`).
- `Ff9mkDebugMenu.cs:2601-2602` `RestoreSnapshot` (`Array.Copy`) and `:2614` `ClearFlagState` (`Array.Clear`).

**Direct single-byte or bit writes (these skip the choke point):**
- `EventEngine.DoEventCode.cs:223`: Oeilvert hotfix, clears bits 3536-3542 (field 2209) through `SetVariableValueInternal`.
- `ff9.cs:2271`: byte 100, navi mode (`updateNaviMode`; callers `ff9.cs:7069`, `WorldHUD.cs:279,532`).
- `ff9.cs:3098`: byte 101 bit 0 (`w_cameraSetEyeAim`).
- `ff9.cs:7084,7089`: UInt16 at byte 92 (known locations).
- **`ff9.cs:7168`**: `w_naviTitleElement` writes **ScenarioCounter += 10** on the world map. This is a story-counter writer that is not a script.
- `ItemUI.cs:969`: byte 181, Gysahl Greens (chocobo); `WMBeeMenu.cs:117`: same byte.
- `EMinigame.cs:454,493`: byte 191 = 5.
- `SFX.cs:880`: `BattleCallback` sets byte 199 `|= 16`; `BattleActionCode.cs:703`: SFX `SetVariable`.
- `VoicePlayer.cs:334,343`: `++` on bytes 510-525.
- `NetSyncClient.cs:705-723`: `WriteCoopCells`, bytes 2032-2037, per frame (callers `:656,912,939,1079,1114,1121`).
- `HarnessAgent.cs:711-715` (bit) and `:724` (byte).
- Debug menu: `SetVehicle` `:1679`, `FlagWrite` `:2364`, `ByteWrite` `:2412`, `ApplyFlagBatch` `:2515-2522`, and `ScenarioCounter`/`FieldEntrance` setters at `:1912-1914,2017-2035,2130-2135`.

**Through the choke point, but not a script (the `s1` attribution is wrong for these):**
- `ProcessEvents.cs:24-43`: No-Encounter bools, every frame, run before `ProcessCode`, so `s1` is left over from the last object of the previous frame.
- `GUIManager.cs:57`: `SetFieldMap`, SC/map index.
- `EMinigame.cs:408` (via `ETb.cs:162`), `:426-427`, `:452-453`, `:490-492`.

**Not found:** any C# writer for mail/Mognet.

## 4. Frame hook

- **The single common bracket is `EventEngine.ProcessEvents`** (`ProcessEvents.cs:11`). `ServiceEvents` calls it (`EventEngine.cs:114-126`), and so does `StartEvents` directly (`EventEngine.cs:760`). That second call is Main_Init running synchronously inside `HonoluluFieldMain.cs:149`, just after the netsync apply at `:148`.
- **The field per-frame call** is `HonoluluFieldMain.cs:240` in `FF9FieldMapMain`.
- **In battle, `ServiceEvents` can run several times per Unity frame** (a do/while loop at `HonoluluBattleMain.cs:578-584`). A Unity-`Update` memcmp would merge those passes into one row.
- **A catch-all per-Unity-frame tick already exists** in all modes: `HarnessAgent.Update` (`HarnessAgent.cs:240`), a DontDestroyOnLoad component bootstrapped from `UIKeyTrigger.cs:135`.
- **Any shadow copy must re-read `FF9StateSystem.EventState.gEventGlobal` each time**, because New Game and save load swap the array reference (§3).

## 5. ScenarioCounter

- It is bytes 0-1 of gEventGlobal, little-endian: `EventState.cs:16-24` (getter `:18`, setter `:21-22`). `FieldEntrance` is bytes 2-3 (`:26-33`).
- The script view is `EBin.SC_COUNTER_SVR = 0xDC` = Global UInt16 at index 0 (`EBin.cs:34`), so script writes to it go through §1.
- The world map also reads it from C#: `ff9.cs:3652`, `WMWorld.cs:154`.