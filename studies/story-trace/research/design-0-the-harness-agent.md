## 1. HARNESS AGENT

- **Channel dir:** `<game>/x64/ff9harness/`, resolved as `Application.dataPath/../ff9harness` (`HarnessAgent.cs:222-229`). It holds `req.txt` (commands in), `state.json`, `events.jsonl`, `shots/`, and `save/`, a save sandbox that is live while armed (`:364-400`).
- **Arming:** it is dormant by default and armed by a file, not an ini key. Being armed means an `ff9harness/arm` file exists. `PollArm` checks for it every 30 frames (`:287-294`), and `Active` is a plain static bool (`:44-47`). With no arm file, nothing is written.
  - A fault latches `_faulted` and the agent will not re-arm on its own (`:264-278`, `:300-301`).
  - Arming resets the per-run scratch and emits `armed` with `protocol` (`:303-327`).
  - Bootstrap is `UIKeyTrigger.cs:135` → `Ensure()`.
- **Cadence:**
  - `state.json` is rewritten every `_stateEvery` frames, default 2, tunable with the `stateevery` verb (`:180`, `:767`, `:1073-1076`). It is written in place with FileShare.Read, not as an atomic replace (`:1829-1867`).
  - `req.txt` is polled every 2 frames when idle and every 10 when busy (`:422-428`).
- **Command protocol ("pokes"):** line 1 is `seq <n>` (the request is ignored unless n is greater than the last one accepted), then one verb per line (`:422-470`).
  - Verbs that write story state: `flag <bit> [0|1]` (`:706-717`) and `byte <idx> <val>` (`:719-726`). Both poke `gEventGlobal` directly.
  - `watch <bits>` publishes the bits under `state.json` → `"flags"` (`:728-746`, `:1699-1723`).
- **Event row format** (`:1794-1808`): `{"frame":N,"kind":"...", k:v...}`. All extra values go through `Str()`, so numbers are emitted as quoted strings.
  - Each `Event()` call runs `File.AppendAllText` (`:1810-1821`).
  - The agent never truncates the file. The driver's `reset()` deletes it (`tools/harness/channel.py:641-647`) and `collect()` copies it out (`:885-892`).
- **What a story-write stream would look like on this publication:**
  - Additive only: protocol 5 (`:43`) does not need a bump. The unbuilt s86 plan sets this precedent, noting that the driver refuses a newer engine (`PLAYER-TRI-PATCH-PLAN.md:~95`).
  - Rows would be batched into `_pendingEvents` and flushed once per frame. Today a 2048-row resync would cost 2048 file opens in one frame.
  - A separate `story.jsonl` would also have to be added to `reset()`'s unlink list, or it would carry over from the previous run.
  - Gate: `if (!HarnessAgent.Active) return;`, the same zero-cost pattern the input hooks use.
- **Attribution caveat (important):** the agent's `Update` runs in unordered Unity Update order (`:31-35`). A memcmp there gives `(frame, byte)` and merges several writes in one frame, and it cannot name the writing function.
  - The single `.eb` choke point for global-variable writes is `EBin.SetVariableValue`, `case VariableSource.Global` (`EBin.cs:1894-1903`). The executing object is known there.
  - C# writers bypass it: the harness `flag`/`byte` verbs, `WriteCoopCells`, `ApplyStoryTo`, and the debug menu's `Array.Clear` (`Ff9mkDebugMenu.cs:2614`).
  - The array itself is reallocated by `NewGame` (`EventEngine.Initialize.cs:43`) and by save-load (`JsonParser.cs:522`). A shadow copy must therefore also track the reference, not just the bytes.

## 2. SnapshotStory

- **It is not a diff and not a shadow.** `NetSyncState.cs:45-60` allocates a `3+2048` frame (`[section 0][len u16]`), `Array.Copy`s the whole live array, then zeroes bytes **2032-2041** (`MaskLo`/`MaskHi`, `:40-41`, `:57-58`).
  - No memcmp loop exists to lift. The only compare loops are `SelfTest` scratch checks (`:242-247`, `:281-286`).
  - The trace needs a new shadow plus a compare. SnapshotStory contributes only the copy idiom and the mask constants.
  - Introduced by `s37-netsync-battle.patch:3497-3514`. `s85` adds `SectionTalk = 6` (`s85…patch:9`).
- **Netsync rewrites every frame:** `WriteCoopCells` (`NetSyncClient.cs:705-718`) writes byte 2032 (presence) and 2034-2037 (peer X/Z, Int16 LE). It is called in the per-frame paths at `:912`, `:939`, `:1079`, `:1114`, `:1121`, and on a config change at `:656`.
  - It runs "only while Enabled" (`:33-41`), so a vanilla or solo run with co-op disabled never touches those bytes.
  - The board's range 2032-2039 matches the cell block (bytes 2033 and 2038-2039 are reserved). The netsync mask extends to 2041 because byte 2040 is choice scratch.
- **Save-load/mirror hook:** `ApplyStoryBeforeEvents` runs at `HonoluluFieldMain.cs:148`, just before `StartEvents` (`NetSyncClient.cs:386-393`). It fits the board's epoch-marker point.

## 3. THE STACK

- **Numbering is capture order, not stack position.** `tools/memoria_stack_replay.py` sorts by the number (`:102-115`), with `TIE_ORDER` for the two s48s and the two s83s (`:83-86`), and `POSITION_AFTER` pinning s84 after s57 (`:87-90`).
  - The dead/removed skip set is at `:57-63` and is test-pinned to the README.
  - Base commit: `BASE_COMMIT`, i.e. `6b8bb2d5`.
- **s86 is missing because it is reserved and unbuilt.** `studies/test-harness/PLAYER-TRI-PATCH-PLAN.md:1-5` and `:62` define it as "`s86-harness-player-bgi-tri.patch` … SCOPED, NOT BUILT. Awaiting owner approval". s87 was captured after it.
  - The clone confirms it: `HarnessAgent.cs:1136` still reads `po.activeTri`.
  - **So a new trace patch would take s88.** It collides with s86 on `HarnessAgent.cs`, which s83 and s85 have also touched. Whichever of s86 and s88 is captured second needs a `POSITION_AFTER` pin or a rebase.
  - `EBin.cs` is already touched by s37, s44 and s65, and is not in the replay's `DEFAULT_FILES` (`:65-80`), so `diag` must be run with `--files`.
- **How patches are applied:** the stack lives uncommitted in the clone's working tree. A new patch is captured with `memoria_stack_replay.py emit`, then gated four ways (`snapshot --stop-after`, `git apply --check` + `patch -F0 --dry-run`, `git apply -R --check`, and `diag` all `==`) (`PLAYER-TRI…:113-121`; README STACK HEALTH `:131-143`).
- **Dormant diagnostics and how they gate:**
  - s63 is gated on game state, not a file: it runs only for `wldMapNo` in the cutscene worlds, as a burst in frames 0-20 then once every 60 (`s63…patch:21-27`).
  - s67 runs while an EYE/AIM rig is designated, plus a 90-frame tail (`s67…patch:14-53`).
  - Both logged via `Memoria.Prime.Log.Message` and were REMOVED after use (README `:108`, `:116`).
  - s68 is a fix, not a probe (README `:110`).
  - The only file-armed dormant subsystem is the s83 harness itself.

## 4. BUILD + DEPLOY

- **Build:** `py tools/build_memoria.py --label L` (SKILL `:20-35`). It:
  - refuses to start without the full 3×2 pre-build backup,
  - runs msbuild as a list-args subprocess with the trailing-backslash `SolutionDir`,
  - checks the sha of both arches after deploy,
  - reports the clone's in-flight edit count first.
  - `--no-deploy` is a compile-check only, using `DWIXNoDeploy`.
- **It auto-deploys.** The csproj `AfterBuild` step copies 3 DLLs into both x64 and x86 `Managed`, with no backup of its own (memory `:53-60`).
  - Restore with `py tools/restore_memoria_dll.py <ts>` from the MAIN repo. It is all-or-nothing and refuses if FF9 is running (SKILL `:66-76`).
  - A new DLL needs a relaunch.
- **Shared-clone trap** (memory `:158-185`): patches live uncommitted in the working tree, and s79 once silently vanished while the build still looked clean.
  - Audit first with `memoria_stack_replay.py diag --files <all +++ files> --out <private dir>`.
  - A build deploys every other session's uncaptured edits too.
  - The trace must not add serialized fields to baked MonoBehaviours (memory `:62-72`). HarnessAgent is created with `AddComponent`, so it is safe.
- **Bundle:** the live DLL and `dwix-custom-memoria-*.zip` are different artifacts and drift apart (memory `:192-196`).
  - Shipping the trace means cutting a bundle from a proof worktree applied at `6b8bb2d5`, never the live clone. After fingerprinting, `installer/dwix-engine.zip` and `INSTALL.txt` are refreshed in the same pass (`project-ff9-release-cutting.md:140-157`, `:199-207`).
  - That re-cut is a separate release decision. s80 and s87 are already waiting for the next cut.