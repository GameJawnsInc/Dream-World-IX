# The story-write trace (EB board #3)

**Status:** ★ **rung 0 in-game PROVEN 11/11** (`story-rung0`): s88 is live (sha `c55377f6c137d442…`, backups `20260924-172331`), and the trace on stock Lindblum 552 joined every script write to a store in the stock bytes. **Rung 1 ★ in-game 11/11** (`story-rung1`): the residue net and the epochs. Next: rung 2 (the null pair).

Board entry #3 of [`../eb-uses-board/BOARD.md`](../eb-uses-board/BOARD.md). It is the narrative-state arc's missing
instrument ([`../narrative-state/PLAN.md`](../narrative-state/PLAN.md)).

## Why

To boot a fork mid-story, the kit must know which story flags the real game has written by that beat, and which
scripts wrote them. The narrative-state arc tried to derive that statically. Rung 0 predicted dominance analysis
would lift coverage past ~55% of story write sites; measured, it reached 18.3% directly and 36.2% with E3
(narrative-state PLAN.md:139-146). About 90% of story sites sit outside Main_Init and a third are once-gated
interaction writes. Reading scripts cannot say when those fire. The trace watches the game write them.

The motivating case is on record: Dali bit 2102 is written only by field 450, which was missing from the chain,
and was found by hand-reading scripts (narrative-state PLAYTEST.md:166-180).

## The design (research pass: four readers, a designer and a checker against the code)

**What changed from the board entry.** The board proposed a per-frame memcmp of a shadow copy. That sees which byte
changed, never which function changed it, merges writes within a frame and misses a set-then-clear. The trace
instead hooks the engine's one store point and keeps the memcmp as a safety net for C# writers.

- **The hook.** Every script write to `gEventGlobal` (every width, every opcode, bit read-modify-writes included,
  in fields, battles and the world map) passes through `EBin.SetVariableValueInternal`. Hook it when the target
  buffer `ReferenceEquals` the live `gEventGlobal`. That also catches the one in-script bypass (the Oeilvert hotfix,
  `DoEventCode.cs:223`). At the store the static `s1` gives sid, uid and level; the opcode-start ip is latched where
  the opcode byte is read (`EBin.cs:194`), because at the store `ip` points mid-expression. The function tag comes
  from the entry's function table (`EventEngine.cs:1103-1124`, `GetIP` = 2 + offset). An addition buffer
  (`isAdditionCommand`: `movQData`, `neckTurnData`) is flagged, never given a tag.
- **`cs` writes.** `setVarManually` (`EBin.cs:480-493`) is the only non-script road into the store; it sets a flag so
  its rows are `src = "cs"` (GUIManager, EMinigame, the stock OnGUI debug jump, HonoluluFieldMain.cs:611/616).
- **The safety net.** About 20 C# writers bypass the store (the world map's `SC += 10` at ff9.cs:7168, ItemUI,
  VoicePlayer, the debug menu's SC setter, Scripts-DLL battle formulas through `BattleCalculator.cs:56`, whose writer
  set cannot be enumerated). A shadow copy compared at the top of every `ProcessEvents` catches them as `residue`.
- **Ordering.** Before a hooked store, the tracer compares live vs shadow for the bytes the store touches and emits
  `prestore` residue for any difference first; only then the write row; then it updates the shadow for those bytes.
  Otherwise an earlier bypass write to the same byte (or, for a bit write, a sibling bit) is silently absorbed.

## THE ROW CONTRACT (proto 1) -- the engine writes it, the kit reads it

Sink: `<game>/x64/ff9harness/story.jsonl`, one JSON object per line, buffered in memory and appended once per Unity
frame (and at `storytrace 0`). Numbers are JSON numbers, never strings.

Every row carries: `k` (kind), `f` (`Time.frameCount`), `p` (the tracer's count of ProcessEvents passes: monotonic
for the launch and never reset, but counted only while tracing -- it orders rows, fields and battles running several
logic passes per frame; it is not the engine's own pass number), `m` (gMode as `StartEvents` sets it: 1 field, 2
battle, 3 world, 4 system mode 8's battle; -1 before the tracer has seen an EventEngine), `fld` (`fldMapNo`), `don`
(`EffectiveFieldId(fld)`), `sc` (ScenarioCounter at the row). A `c` row is the exception: its `fld`/`don`/`m` are
its SITE's (where the counted stores ran), its `f`/`p`/`sc` the flush's.

| `k` | Meaning | Extra fields |
|---|---|---|
| `w` | a write through the store point | `src` (`eb` script opcode, `cs` setVarManually, `harness` the harness's own pokes), `sid`, `uid`, `lvl`, `ip` (opcode start, the engine's entry-relative ip; -1 when the latch belongs to another object), `tag` (-1 if unknown), `add` (1 = addition buffer, and then `tag` is -1), `byte` (first byte), `w` (width: the engine's own `EBin.VariableType` names, `SBit` `Bit` `SByte` `Byte` `Int16` `UInt16` `Int24` `UInt24` -- the kit disassembler's `VAR_TYPE` spelling), `bit` (the global bit index for a `SBit`/`Bit` write, else -1), `old`, `new` (as the engine READS that width, `GetVariableValueInternal`: UInt24's read sign-extends), `same` (1 when old == new). On `cs` and `harness` rows `sid` `uid` `lvl` `ip` `tag` are all -1 and `add` 0: at a C# store `s1` is whatever object ran last |
| `r` | residue: a byte changed with no hooked store | `byte`, `old`, `new`, `why` (`frame` or `prestore`) |
| `c` | counts for suppressed rows at one site | the site key (`src`, `sid`, `tag`, `ip`, `byte`, `w`, `bit`, plus the common `fld` and `m`), `n` (rows suppressed), `last` (the last `new`) |
| `e` | epoch: the whole array was replaced; the shadow now equals live | `why`: `arm`, `swap` (New Game / save load replace the array: a `ReferenceEquals` test; the OLD array's `frame` residue since the last pass is emitted first), `debug-restore`, `debug-clear`, `netsync` (co-op `NetSyncState.ApplyStory`; not `ApplyStoryTo`, which SelfTest drives against a scratch buffer), `off` |

**Suppression (bounded logs; the owner chose "record same-value stores, collapsed").** Per site key per epoch:
the first same-value store is emitted with `same: 1`, later ones are counted; the first 64 changing-value writes
are emitted, later ones are counted. Counts flush as `c` rows at each epoch and at `storytrace 0`. **The site key
is (`fld`, `m`, `src`, `sid`, `tag`, `ip`, `byte`, `w`, `bit`)**: a field change opens no epoch, and sibling fields
run byte-identical code at one (sid, tag, ip) -- Dali's `Bit[2102]` store at e2 tag 1 ip 479 runs in 350, 352, 354,
356, 358 and 450 -- so a key without the field counts the second field's store under the first field's row, and no
row ever names field 450.

**Masking.** The engine drops only residue on bytes 2032-2041 (the netsync cells, rewritten every frame under
co-op; `NetSyncState.cs:40-41`). Everything else is recorded raw and the kit masks at analysis time.

**Control.** Dormant unless the harness is armed and sends `storytrace 1`; when off, the hook costs one static bool
test. Arming the harness resets the tracer. `state.json` publishes `"storytrace": {"proto": 1, "on": ..., "rows":
..., "suppressed": ..., "error": ...}` so an older engine fails visibly. `error` is null while healthy, else why the
tracer turned itself off: a fault writes NO `off` row, so a reader must check `error` -- a file that simply stops is
not a complete run. The harness's own `gEventGlobal` pokes emit `src = "harness"` rows and update the shadow.

## From a row to a line of script

`allObjsEBData[sid]` is the kit's `Entry.abs_start`, so `abs_start + ip`-derived offsets join the static census
(`research/dominance_census.py`). Rows key on (donor, sid, tag, offset within the function): a fork's `[startup]`
prepend is a length-changing insert that shifts every later function in entry 0, and for entry 0's Main_Init the
reader aligns the fork's body to the donor's as a suffix. Trace the US build (the census is US bytes; JP differs in
71% of fields). Rows that match no census site (addition buffers, battle and world-map scripts, C#) are listed as
census gaps. (Computed-index 0xD3 writes never reach the trace at all: they go to `gScriptVector` /
`gScriptDictionary`, see Costs and risks.)

## The deliverable

A stock run and a fork run at the same beat: New Game, seed the beat's flags through the harness, `warp <field>
<entrance> <SC>` (never a bare `warp N -1 -1`, which drops both), a scripted play, soft reset, the other side.
Randomness is unseeded and logic ticks per frame vary, so the comparison is a SET of (donor, sid, tag, offset, byte,
value) over N = 3 runs per side: STOCK ONLY, FORK ONLY, UNSTABLE, RESIDUE, CENSUS GAPS.

**A run is one `arm` .. `off`.** The sink is append-only for a whole launch (a harness `reset` stops the trace but
never starts a new file), so the kit splits a story.jsonl into one run per `arm` (`storytrace.split_runs`;
`story-trace RUN#N` picks the N-th, a suite member's directory gets its own). A run with no `off` -- a fault, a
dead game, a restart, a file taken early -- is INCOMPLETE: every report banners it and `--strict` fails it, because
a key past its cut reads as absent. The driver's `storytrace(False)` refuses to return until the file holds exactly
the `rows` the engine counted, and raises on a published `error`.

## Owner decisions

1. **Ship it** in the engine bundle, at the next re-cut (s80 and s87 already wait for it).
2. **Record same-value stores, collapsed** (the suppression rule above).
3. **Beats:** Lindblum 552 @ SC 3115 for calibration, then Dali.
4. **N = 3 runs per side**, no RNG-seed engine command.
5. **The stock side may start from real saves** (needs a save-load lane; a later rung).
6. **Unify the kit's three story-noise masks and fix `named_word_at`'s byte/bit callers first.**

## Rung 0 result

★ **In-game 11/11** (`story-rung0`, [`rung0_trace.py`](rung0_trace.py)). New Game, the harness seeds byte 236 =
0x0F, `warp 552 3 3115`, stand ~2 s, `storytrace 0`.

- **The join is exact.** 13 script writes in 552, all 13 on a store instruction of the STOCK bytes at their (sid,
  tag, offset); every row attributed (sid 0, uid 0, a level, the opcode-start ip, tag 0).
- **Main_Init in script order, 10/10**, ATE branch included: `Bit[191]:=0`, `Bit[184]:=0`, `Int16[9]:=1582`,
  `Byte[13]`, `Int16[11]:=1587`, `Byte[14]`, `Int16[239]:=552`, `SByte[238]:=1`, `Int16[241]:=15`,
  `UInt16[251] |= 15`; ips ascending.
- **It saw what the static reading missed.** The design's checker listed `Byte[8]:=125` as entrance-99-101 only
  and never listed a second `Byte[13]`/`Byte[14]` write. The trace recorded `Byte[8]:=125` at ip 872 (a
  same-value store, `same: 1`) and `Byte[13]:=2` / `Byte[14]:=2` at ips 1591/1632 two frames later, from
  Main_Init's tail after its wait loop -- each joined to a real store.
- **The seed** arrived as a `harness` row; **the residue** was exactly the warp's own ~ menu writes (SC 3115 in
  bytes 0-1 = 43/12, the entrance 3 in byte 2), seen in field 70 before the load; `R0-OFF`: an armed, unstarted
  tracer wrote nothing; `ff9mapkit story-trace --strict` read the run back (and warned, correctly, that
  FF9CustomMap-world overrides field 70). No exceptions.
- The analysis was checked offline first against rows built from the real 552 bytes: the good run passed and five
  mutants (an ip one off, two rows swapped, no `off`, the seed as a script row, a wrong tag) each failed their own
  check.

## Rung 1 result

★ **In-game 11/11** (`story-rung1`, [`rung1_trace.py`](rung1_trace.py)), one traced run from the title: New
Game, harness pokes, `warp 552 3 3115`, ~5 s standing, `warp 552 5 3120`, soft reset, title -> Continue (the
sandbox autosave).

- **Epochs:** `arm`, New Game = ONE `swap`, the load = ONE `swap`, `off` -- no flood, and zero residue at the load.
- **The residue net is exact.** The calibration writer is the debug menu's own warp, a real C# bypass writing
  values the scenario chose: SC 3115 -> byte 0 = 43, byte 1 = 12, entrance 3 -> byte 2 = 3; then SC 3120 -> byte
  0 = 48, entrance 5 -> byte 2 = 5, and NO row for byte 1 (unchanged at 12). Those 5 rows are the run's only
  residue, and none of them sits within a frame of any of the run's 47 hooked writes to the same byte: the net and
  the hook never double-count.
- **The harness's own pokes** (`flag 12200`, `byte 236`, `byte 237`) arrived as `harness` rows, none as residue.
- **The quiet window** (~5 s standing in 552) held no rows at all -- no spontaneous residue, but also no script
  writes, so it is a weak check; the no-double-count result above is the strong one.
- **Not exercised in-game:** the debug menu's `debug-restore` / `debug-clear` epochs (no harness verb --
  `HarnessWarp` passes `resetFlags = false`), co-op's `netsync` epoch (two games), the `prestore` residue (needs a
  bypass write inside a pass), and the world map's `SC += 10` (a one-off continent-title beat). All are
  code-reviewed; verbs for the debug paths can ride the next s88 rebuild.

## Rungs

| Rung | What | Pass |
|---|---|---|
| **0** | Hook + sink on a STOCK field (Lindblum 552, entrance pinned) | Every `eb` row lands on a store instruction in the stock `.eb` at (sid, tag, offset); Main_Init's writes for that entrance appear in the script's order; an unarmed run writes no file |
| 1 | Residue and epochs | A harness poke, a debug-menu flag write and the world-map `SC += 10` appear as `harness` / `residue` rows; a script-only walk gives zero residue; New Game, load and clear each give exactly one epoch |
| 2 | **The null pair** (the real falsifier) | Stock 552 vs its own verbatim fork, N = 3: STOCK ONLY is empty |
| 3 | Retrodiction | The Dali chain vs stock Dali on the real story route: field 450 / bit 2102 comes out of the report with no script reading |
| 4 | fork-report's story-writes axis | `fork-report` shows the traced set difference |

The board's own falsifier ("refuted if it tightens no interval the save corpus gave") cannot fail as written: the
intervals were never built, and with seven SC points almost any write tightens one. Rung 2 replaces it.

## Costs and risks

- s88 is an engine patch: the build auto-deploys over the live install (`tools/build_memoria.py` enforces the 3x2
  backup; compile-check with `--no-deploy` first; relaunch after).
- The shared clone: audit with `memoria_stack_replay.py diag` before and after (clean at the start: 87 of 87 files
  byte-exact); capture with its `emit` mode. s86 is reserved but unbuilt and also touches `HarnessAgent.cs`.
- Not visible to the trace (all outside `gEventGlobal`): ATE seen-state (`AchievementState`), party state, and
  `gScriptVector` / `gScriptDictionary` -- the 0xD3 VECTOR / VECTOR_SIZE / DICTIONARY lane, where the kit keeps
  persistent tables, the fight ledger and roll streams. `SetVariableValue`'s `VariableSource.Null` branch writes
  them directly and never reaches the store point, so a fork whose kit content writes a table shows no FORK ONLY
  row; `debug-clear` empties them too, and its epoch is the only record. If that state matters to fork fidelity,
  it needs its own row kind in a later proto.
