# The story-write trace: design walkthrough

**Bottom line:** the board's plan has the right outline: one dormant patch, driven by the harness, a stock run against a fork run, compared as a per-function set difference. But the mechanism it proposes can't produce that result. A per-frame memcmp sees which byte changed and in which frame. It never sees which function wrote it. This design captures writes at the one script store point instead, and keeps memcmp only as a check for C# writers the hook can't see.

## A. What question it answers
"At beat SC, which functions does the stock game run that write story state, and which of them does the fork never reach?"

The board's reason for building it is out of date. BOARD.md:34 still says dominance analysis lifts coverage "past ~55%". That prediction was proven wrong (PLAN.md:139-146). On the 2832 real story sites, static windows reached 18.3% directly and 36.2% with E3 added. The cause is that about 90% of story sites are outside Main_Init, and 32% are once-flag-gated writes that fire on interaction. Static analysis can't go further on those sites. A trace sees them as they are played.

Motivating case: Dali bit 2102 is written only by field 450, which was missing from the chain. It was found by hand-reading `.ebs` (PLAYTEST.md:166-180). The trace would replace these hand-asserted FORK_FIDELITY items: :197-200, :283-287 ("assert the beat"), and :60-65 (synth forks drop donor writes).

## B. Capture design
- **(1) Memcmp only (the board's plan).** It can't name the writer. It also:
  - merges several writes that land in the same frame
  - misses writes of the same value, and a set then clear within one tick
  - merges the battle loop's multiple `ServiceEvents` passes per Unity frame (HonoluluBattleMain.cs:578-584)
- **(2) Hook only.** `EBin.SetVariableValue`, `case VariableSource.Global` (EBin.cs:1902-1903) is the single store for every opcode and every width:
  - B_LET (:893-904), `*_LET` (:936-1065), `++`/`--` (:574-613), and the `_A`/`_E` variants through `putv` (:2067-2074)
  - bit writes are read-modify-write in the same switch (:1995-2003)
  - battle and world scripts reach it too (ProcessEvents.cs:116)
  - `s1` gives sid, uid, level and ip there (Obj.cs:79-137)

  But roughly 20 C# writers bypass it, including `ff9.cs:7168` (ScenarioCounter += 10 on the world map), ItemUI.cs:969, VoicePlayer.cs:334/343, and the harness's own pokes (HarnessAgent.cs:711-724).
- **(3) Recommended: both.** When the hook records a write, it also writes the new value into the shadow copy. A memcmp then finds only the writes that bypassed the hook, so whatever it turns up is exactly the C#-writer set.

What the patch touches:
- **`Global/EBin.cs`**
  - In the Global case, when armed: read the old value, emit a row, update the shadow.
  - Latch the opcode start at :194 (`a0 = s1.getByteIP()`). At the store itself, `ip` points into the middle of the expression.
  - Tag `setVarManually` (:480-493) as C#.
- **`EventEngine/ProcessEvents.cs`**
  - Set an `inScript` flag around `eBin.ProcessCode` (:116), so the no-encounter writes (:24-43, which run with a stale `s1`) are tagged `cs`.
  - Keep a pass counter.
  - At entry (:11), run the memcmp and the array-reference check. This also covers Main_Init through StartEvents (EventEngine.cs:760).
- **`HarnessAgent.cs`**: the trace verb, the sink, the reset on arming, and tags for its own pokes. Probably a new `StoryTrace.cs` as well, plus its csproj line.
- **Kit side**: `tools/harness/channel.py` and a session verb.

Recovering the function tag: find the largest `2+off ≤ op` in the entry's function table (EventEngine.cs:1103-1124). That is about 30 entries, scanned only when a store happens. Exception: when `isAdditionCommand` is set, `ip` indexes `movQData` rather than the script (Obj.cs:568-579). Flag those rows instead of deriving a tag.

## C. Row format and sink
One row (illustrative):
`{"f":8123,"pass":2,"mode":1,"fld":30823,"don":552,"sc":3115,"src":"eb","sid":0,"uid":0,"tag":0,"op":420,"caller":-1,"byte":18,"w":"i16","old":0,"new":1582}`

- **`src`** is one of four values:
  - `eb`: a script store
  - `cs`: C# code going through the choke point outside a script
  - `residue`: found by the memcmp; byte, old and new only
  - `harness`: the harness's own pokes
- **`caller`** comes from the `Call` stack via `getSender` (EventEngine.cs:359-385).
- **Sink: a separate `ff9harness/story.jsonl`**, not `events.jsonl`. `Event()` opens the file once per row and stringifies numbers (HarnessAgent.cs:1794-1821). Rows are buffered and flushed once per frame. The file must be added to `reset()`/`collect()` (channel.py:641-647, :885-892). The change is additive, so protocol 5 stands.
- **Arming:** the trace runs only when the harness is armed (`Active`, :44-47) and a `storytrace 1` verb has been sent. While dormant it costs one static bool check at the hook. The shadow resets when the harness arms (:303-327).
- **Epochs:** on each event below, emit one `{"k":"epoch","why":…}` row and resync the shadow silently. Never emit 2048 rows. Events:
  - arming
  - an array-reference swap: New Game (EventEngine.Initialize.cs:43) and save load (JsonParser.cs:522) both replace the array, so the test is `ReferenceEquals`, not a byte compare
  - the debug menu's RestoreSnapshot / ClearFlagState (Ff9mkDebugMenu.cs:2601-2614)
  - `ApplyStoryTo` (NetSyncState.cs:98-120, reached from HonoluluFieldMain.cs:148); this is co-op only, not a way to seed state
- **Masking:** the engine records raw rows, and the kit masks at analysis time using `BIT_REGIONS`, matched by region *name*.
  - Never mask by the `reserved` flag: worldmap_unlocks 736-823 is marked reserved but is real progression (flags.py:273-280).
  - Masked regions: the byte-23 scratch bytes, read-mail 8512-8711, the QTE and choice scratch, the netsync cells, and the behavior blackboard. Mognet gets its own channel.
  - One engine-side exception: drop residue rows for bytes 2032-2041. SnapshotStory is a full copy, not a memcmp (NetSyncState.cs:45-60), so its mask constants (:40-41) are the only part worth lifting.
  - Prerequisite: the kit has three masks that disagree today (dominance_census.py:215-217, forkreport.py:205-211, storyseed.py:30).

## D. From row to source
- **The join:** `allObjsEBData[sid]` is the kit's `Entry.abs_start` (EventEngine.cs:607-613; model.py:92,143). So `abs_start + op` is the census `off` key (dominance_census.py:177; cfg.py:797), and rows join directly onto the 12322-site census.
- **Readable output:**
  - source text from `cmdasm.disassemble_items` (cmdasm.py:283), joined the way ebsrc.py:418 does it
  - names from `logic_map` (:211-222)
  - static guards from `FieldFlow.guards_at` (cfg.py:917)

  The result reads like "552, entry 0 Main_Init, tag 0, `Int16[239] = 552`, unguarded".
- **Caveats:**
  - Fork rows are keyed to the donor through `EffectiveFieldId`, which needs the fork's ForkDonorPatch row.
  - The `[startup]` prepend shifts Main_Init offsets (build.py:5892). Subtract it.
  - The census is built from US-language bytes, and JP differs in 71% of fields. Trace in US.
  - Rows with no census match (0xD3 computed-index writes, addition buffers, C#) are listed as census gaps. That list is a finding in its own right.

## E. The deliverable
No existing scenario runs a donor and its fork at the same beat. The closest scaffold is `borrow_2507_ingame.py`. Recipe:
1. New Game.
2. Apply the seed with `g.flag`/`g.poke`, using `storyseed.resolve(...).set_bits` and `ate_word_values` (storyseed.py:107-114, :448).
3. `g.warp(stock, scenario, entrance)`, then run the scripted play.
4. Soft reset and repeat steps 1-3 against the fork.

Traps:
- Stock fields at a beat often open on a cutscene. Use a raw `warp N -1 -1` (cutscene_check.py:31-35).
- A member with its own baked `[startup]` overwrites the warp's SC (Ff9mkDebugMenu.cs:2131-2134).
- Stacked mod folders can override the "stock" field. Check `env.json`.

Randomness is unseeded (GetSysvar.cs:13-14) and logic ticks per frame vary (FPSManager.cs:94-99). So the comparison is a **set** keyed on (donor, entry, tag, op, byte, new), not an ordered diff, with N runs per side.

Illustrative report (invented values):
```
donor 552 @ SC 3115: stock x3 vs fork 30823 x3
STOCK ONLY (3/3 vs 0/3)
  552 e4 tag 3 (talk)  op 0x0142  bit 2345 := 1   guard bit[2340]
FORK ONLY
  552 e0 Main_Init     UInt16[0] := 3115          ([startup] stamp)
UNSTABLE 2 rows · RESIDUE byte 100 both sides · CENSUS GAPS 1 (0xD3)
```

## F. Calibration and falsifier
**Calibration: the Lindblum 552 known case.** A verbatim fork at SC 3115 with byte 236 = 0x0F (ATE_SYSTEM.md:340-345). The owner confirmed it on slot 30823 (PLAYTEST.md:85-92), but its current registration is unverified.

That proof was visual, and no write order was recorded. So the baseline has to be the static order from eb-src (entry 0, tag 0):
1. seed stamp
2. 191/184 (masked)
3. `Int16[9]=1582`
4. `Int16[239]=552`
5. `SByte[238]=1`
6. `Int16[241]=UInt16[236]`
7. `UInt16[251] |= UInt16[236]`

**The board's refutation can't run yet.** It says the trace is refuted if it "tightens no interval the save corpus already gave". But no intervals exist: rungs 4-5 were shelved, and storyseed only gives a one-sided `lo` (storyseed.py:100,116-126). What has to happen first:
- Build the corpus brackets: per bit, [last SC where it's clear, first SC where it's set], from the 19 saves (PLAN.md:70-82).
- Start the stock side from corpus saves. A run booted from a derived seed would be circular.
- Note that 3115 sits just above the corpus band (top 3110), while Dali 2600 is inside it.

## G. Rungs
- **Rung 0 (smallest in-game step):** hook plus sink on the 552 fork.
  - Pass: the static order above reproduces, each row attributed to (552, 0, 0) at offsets that match cmdasm.
  - Pass: an unarmed run writes no file.
- **Rung 1:** residue and epochs.
  - Pass: a harness poke, a debug-menu FlagWrite, and the world-map `SC += 10` all show up as residue or harness rows.
  - Pass: a walk that only runs scripts produces zero residue.
  - Pass: New Game, load and clear each produce exactly one epoch row.
- **Rung 2 (null pair):** stock 552 against its verbatim fork, N=3.
  - Pass: STOCK ONLY is empty.
- **Rung 3 (retrodiction):** Dali chain against stock at 2600.
  - Pass: field 450 / bit 2102 is named without reading any source.
- **Rung 4 (the board's test):**
  - Pass: at least one corpus bracket is tightened.
  - Fail: if none is, the trace is refuted as the board stated.
- **Rung 5:** feed fork-report's Story-writes axis (forkreport.py:214-226).

## H. Costs and risks
- **The build auto-deploys over the live install** with no backup of its own. Use `build_memoria.py` (it enforces the 3x2 backup), do a `--no-deploy` compile check first, and relaunch after. Restore from the MAIN repo.
- **Shared clone:** run `diag --files` first, because `EBin.cs` isn't in `DEFAULT_FILES`. Any build also ships other sessions' uncaptured edits.
- **Patch number:** this would be s88. The unbuilt, reserved s86 also touches `HarnessAgent.cs`, so s88 needs a `POSITION_AFTER` pin or a rebase.
- **Bundle:** the live DLL and the bundle drift apart. Shipping the trace means a re-cut from a proof worktree at `6b8bb2d5`, which is a separate release decision. s80 and s87 are already waiting for the next cut.
- **Log size:** today's `events.jsonl` is 22-39 KB per run, and `.harness-runs` already holds 290 MB across 51 runs. Collapse identical repeated rows into one row with a count.
- **Log lifetime:** the next run's `reset()` deletes the live file, and the run folder disappears with its worktree. The tool should copy the trace to `C:\gd\SCRATCH` itself.
- **Out of reach:** ATE seen-state (`AchievementState`) and party state are not in gEventGlobal, so the trace can't see them.
- **Side bug:** storyseed.py:175 and build.py:5919 pass a byte index to `named_word_at`, which takes a bit (flags.py:488-497). The refusal meant to be "non-negotiable" misfires as a result.

## I. Owner questions
1. Dev-only instrument, or part of the shipped bundle?
2. Build s86 first, or pin s88 after it?
3. Record same-value stores? They prove a function ran, but make bigger logs.
4. Re-verify 30823 for calibration, or use a fresh slot?
5. After calibration, is the primary beat Dali 2600 or Lindblum 3115?
6. Accept N runs per side, or add an RNG-seed verb (another engine change)?
7. Which real saves may seed the stock-side runs?
8. Unify the three masks and fix `named_word_at` before the trace, or separately?