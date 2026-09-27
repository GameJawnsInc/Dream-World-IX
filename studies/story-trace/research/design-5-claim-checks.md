## Claim checks

1. **CLAIM:** `SetVariableValue` Global case is the single script store for all widths.
   **VERDICT:** confirmed.
   **EVIDENCE:** `EBin.cs:1902-1903`. One switch at `:1991-2035`; bit RMW at `:1995-2003`. Writers: `B_LET` `:893-904`, `*_LET` `:936-1065`, `++`/`--` `:574-613`, `putv` `:2067-2074`, called from `OperatorAll.cs:76,113-128` and `OperatorExtract.cs:200`. All modes run `ProcessEvents.cs:116`.
   **CORRECTION:** there is one in-script bypass. `DoEventCode.cs:223` (the Oeilvert hotfix) calls `SetVariableValueInternal` directly. Hook `SetVariableValueInternal` with `ReferenceEquals(buffer, gEventGlobal)` instead, which also catches it with a valid `s1`.

2. **CLAIM:** the no-encounter writes at `ProcessEvents.cs:24-43` are gEventGlobal writes, so `inScript` is needed.
   **VERDICT:** wrong.
   **EVIDENCE:** `0xC5 & 3 = 1` gives `VariableSource.Map` (`EBin.cs:482,2559-2563`). In HW naming "Glob" means Map and "Gen" means gEventGlobal (`DoEventCode.cs:215` "VARL_GenBool", `EventEngineUtils.cs:2221`). `WorldHUD.cs:446/454` and `UIKeyTrigger.cs:375` (9173) are Map too.
   **CORRECTION:** drop `inScript`. Tagging `setVarManually` already covers every non-script entry into the choke point: `GUIManager.cs:57-58`, `EMinigame.cs:408,426-427,452-453,490-492`, and `HonoluluFieldMain.cs:611/616` (a stock OnGUI debug jump the draft missed). `EMinigame` also fires mid-opcode (`EBin.cs:208`, `ETb.cs:159`), so `inScript` would mislabel it anyway.

3. **CLAIM:** the attribution fields and the opcode latch work as described.
   **VERDICT:** confirmed.
   **EVIDENCE:** `s1` is static (`EBin.cs:32`). `ip`/`level`/`sid`/`uid` are at `Obj.cs:79/91/115/127`. At `:194` the opcode byte is read before `ip++` (`:204`). `GetIP` returns `2+offset` (`EventEngine.cs:1103-1123`). Addition buffers are `movQData` (`DoEventCode.cs:865`) and `neckTurnData` (`ProcessNeck.cs:237`).

4. **CLAIM:** `caller` via `getSender`.
   **VERDICT:** overstated.
   **EVIDENCE:** `getSender` is private and reads slot `sx-1` (`EventEngine.cs:381-385`). `Call` stores `gExec.uid` (`:363`).
   **CORRECTION:** it reads garbage when `sx==0` (a function not entered by `Call`). For engine-initiated calls (talk, regions) `gExec` is stale. Treat it as valid only for script `Request`s.

5. **CLAIM:** the C# writer list.
   **VERDICT:** confirmed (checked `ff9.cs:7139/7167-7168`, `ItemUI:969`, `VoicePlayer:334/343`, `HarnessAgent:711-724`, `SFX:880`, `BattleActionCode:703`, `WMBeeMenu:117`, `ff9.cs:2271/3098/7084/7089`).
   **CORRECTION:** add debug-menu `:2184` (an SC setter). `BattleCalculator.cs:56` hands the live array to external Scripts-DLLs, so that writer set cannot be enumerated. Only residue can see it.

6. **CLAIM:** hook writes the new value into the shadow, so residue is exactly the C#-writer set.
   **VERDICT:** wrong as specified.
   **CORRECTION:** if the hook takes "old" from the live array and copies it into the shadow, it absorbs any earlier bypass write to the same byte. For bit RMW that includes other bits of the byte. Before storing, compare live vs shadow for the touched bytes and emit residue first.

7. **CLAIM:** epochs are detectable.
   **VERDICT:** partly wrong.
   **EVIDENCE:** New Game (`Initialize.cs:43`) and load (`JsonParser.cs:522`) swap the reference: confirmed. `RestoreSnapshot`/`ClearFlagState` (`Ff9mkDebugMenu.cs:2601-2602`, `:2614`) and `ApplyStoryTo` (`NetSyncState.cs:97-120`) write in place.
   **CORRECTION:** the patch must also touch `Ff9mkDebugMenu.cs` and `NetSyncState.cs`; they are missing from the file list. `ClearFlagState` also fires on a debug warp with reset (`:2123-2124`). `HarnessWarp` passes `false` (`:474`), so seeds survive.

8. **CLAIM:** SnapshotStory is a full copy with the mask at 2032-2041.
   **VERDICT:** confirmed (`NetSyncState.cs:40-41,45-60`).

9. **CLAIM:** HarnessAgent arming and sink.
   **VERDICT:** confirmed.
   **EVIDENCE:** `Active` at `:47`; `PollArm` and the reset at `:287-327`; `Event()` does `AppendAllText` per call with numbers passed through `Str` (`:1794-1821`). An unknown op produces an `error` event, not a fault (`:489-494,:877`).
   **CORRECTION:** an old engine can't advertise support, so publish a `storytrace` capability in `state.json`.

10. **CLAIM:** the `BIT_REGIONS` contents.
    **VERDICT:** partly wrong.
    **EVIDENCE:** `flags.py:236-320`.
    **CORRECTION:**
    - The read-mail region is named `mognet_readmail_payload`, not `readmail_payload`.
    - Byte 23 has only bits 184 and 191 named (`:269-272`). Bits 185-190 are in no region, while all three kit masks cover 184-191, so matching by name leaves them unmasked.
    - `mognet_lock_margin` 8504-8511 holds real stock bools (8510-8511) and the kit's deathrules marker (8508).
    - `kit_world_flags` 14976-15007 (ferry) and `nameplate_explored_words` are live progression. Keep them.

11. **CLAIM:** the three masks disagree, and `named_word_at` is called with a byte.
    **VERDICT:** both confirmed.
    **EVIDENCE:** the census is at `research/dominance_census.py` at the repo root, not in the package (184-191 plus 8192-8711). `forkreport.py:205-211`; `storyseed.py:30`. `flags.py:488-497` does `>>3`; `storyseed.py:175` and `build.py:5919` pass `bit//8`.

12. **CLAIM:** the new patch is s88.
    **VERDICT:** confirmed.
    **EVIDENCE:** s87 is the highest file. s86 is reserved only in `PLAYER-TRI-PATCH-PLAN.md:62`. No s88+ exists in any of 39 worktrees. `DEFAULT_FILES` (`memoria_stack_replay.py:60-80`) lacks both `EBin.cs` and `EventEngine.ProcessEvents.cs`.

13. **CLAIM:** the build auto-deploys.
    **VERDICT:** confirmed (csproj `:1503` `AfterBuild`; `build_memoria.py:27-31,86-95`).

14. **CLAIM:** the same-beat recipe works.
    **VERDICT:** partly wrong.
    **EVIDENCE:** `newgame` `session.py:1454`, `warp` `:1546`, `soft_reset` `:2902`.
    **CORRECTION:**
    - The literal raw `warp N -1 -1` (`cutscene_check.py:33`) drops both entrance and SC. Use `g.send(f"warp {N} {E} {SC}")`.
    - There is no save-load verb. The only route is title → Continue into the sandbox autosave with a relaunch (`rung0_persist.py:126-141`), so "start the stock side from corpus saves" needs a new lane.

15. **CLAIM:** calibration slot 30823.
    **VERDICT:** now verified as absent.
    **EVIDENCE:** it is not in any of the 6 folders' `DictionaryPatch` (`Memoria.ini:6` now stacks 6, not 4). No `ForkDonorPatch.txt` exists in any folder, only a `.lock`.
    **CORRECTION:** redeploy and relaunch first. `EffectiveFieldId` currently maps nothing.

16. **CLAIM:** the 552 static write order.
    **VERDICT:** wrong (incomplete).
    **EVIDENCE:** `f552.ebs:9-47,120-150`.
    **CORRECTION:**
    - Also written: `Int16[2]=10000` (FieldEntrance, only when bit 184 is set), `Byte[13]` ∈{0,1,9}, `Int16[11]=1587`, `Byte[14]` ∈{0,1,9}.
    - `Int16[239]=552` is written only when FieldEntrance ∉{1,2}; otherwise the script writes 238=0 and 241=0.
    - The whole ATE block is gated on `UInt16[236]!=0`.
    - `Byte[8]=125` is written on entrances 99-101.
    - Pin the entrance. Rung 0's pass criterion fails as written.

17. **CLAIM:** tick drift comes from the battle loop.
    **VERDICT:** confirmed but broader: fields also run several logic ticks per frame (`FPSManager.cs:94-99`), so `pass` is needed everywhere.

## Missed

- The `[startup]` prepend is a length-changing insert (`build.py:5877-5895`). It shifts every later function in entry 0, not just Main_Init. Key on (entry, tag, offset within the function).
- `guards_at` takes a function index, not a tag (`cfg.py:917`).
- Rung 4 can't fail. With 7 distinct SC points (`PLAN.md:70-76`), almost any traced write tightens a bracket.
- Rung 3 is circular. The stock run must physically visit field 450, and choosing that route assumes the answer.
- New Game currently lands through the field-70 override (`FF9CustomMap-world/.../evt_alex1_ts_opening`). No stock 552 override is present.