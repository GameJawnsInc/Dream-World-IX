# The story-write trace (EB board #3)

**Status:** ★ **rung 0 in-game PROVEN 11/11** (`story-rung0`): s88 is live (sha `c55377f6c137d442…`, backups `20260924-172331`), and the trace on stock Lindblum 552 joined every script write to a store in the stock bytes. **Rung 1 ★ in-game 11/11** (`story-rung1`): the residue net and the epochs. **Rung 2 ★ in-game 8/8**
(`story-rung2`): THE NULL PAIR -- stock 552 x3 vs its verbatim fork x3, STOCK ONLY and FORK ONLY both empty.
**Rung 3 step 1 ★ in-game 7/7** (`story-rung3-s1d`): an unattended blind tour of stock Dali reached 450, the
trace named 450 as the only writer of the ping, and the story moved on by itself. **Rung 3 ★★ THE RETRODICTION,
in-game 17/18 + 1 VOID** (`story-rung3c`, predictions v2): against stock Dali x3, today's import-chain (F0, x3,
each replaying its stock partner's walk) and the round-4 seed (F4, x3), the trace -- no script reading -- named
450 as the ping's only writer, F0's seam into the real 450, F4's pre-empted latches and its byte-297 clobber, and
found F0 otherwise write-for-write stock (MIRROR: FORK ONLY and STOCK ONLY empty). The VOID is NULL-PRE's
stock-side evidence from 355 (a walker at its door). Next: rung 4 (fork-report's story-writes axis).

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

## Rung 2 result -- the null pair

★ **In-game 8/8** (`story-rung2`, [`rung2_trace.py`](rung2_trace.py)). The fork: `ff9mapkit import 552 --verbatim
--id 30830 --name TRC552`, deployed with `tools/deploy_field.py --id 30830` (it wrote `ForkDonorPatch.txt` 30830 ->
552). Six runs in one launch, interleaved stock/fork, each New Game -> `storytrace 1` -> seed byte 236 = 0x0F ->
`warp <field> 3 3115` -> ~3 s -> `storytrace 0` -> soft reset.

- **STOCK ONLY: 0. FORK ONLY: 0. UNSTABLE: 0.** 11 story keys matched in all six runs (552's Main_Init, joined at
  the same function offsets on both sides); 0 join failures -- each side joined against the bytes it ran (the
  install's 552, the mod folder's 30830, the field-70 New Game override on both).
- **The donor mapping is live in the engine:** every one of the fork's 39 rows carries `don` 552, written by the
  engine from ForkDonorPatch, not assumed by the reader.
- **Six genuine runs:** distinct frame ranges (516-808 ... 3176-3572) and the tracer's pass counter monotonic
  across them (0 -> 927).
- **The falsifier bites** (checked offline first, on real rows): a fork run that never writes one of 552's
  Main_Init stores is named exactly in STOCK ONLY -- `WriteKey(donor=552, sid=0, tag=0, off=509,
  Global.Int16[239] = 552)`.
- The residue is the warp's own ~ menu writes, identical on both sides (bytes 0-2, 3/3 each), and so never a key.

## Rung 3, step 1 -- driving the stock Dali morning unattended (in progress)

The design (a read-only research pass + an adversarial check; notes in the session scratchpad): start where the
story does -- the village entrance 359 at SC 2540, which reads neither SC nor its entrance and sets the party
itself -- let the game play 359 -> 351 -> 352 on its own, then a BLIND tour crosses every exit of every field
reached (the kit's `eventscan.scan_gateways` order, bounded by the in-game location label "Dali/", never talking
to anyone) until SC leaves 2600. The story forces the route through 450 by itself: SC 2610 needs latch 2079, 2079
needs bit 2102, and only field 450 writes 2102 = 1. The research also found a THIRD round-4 defect nobody had
seen: the round-4 seed wrote byte 296 = 192 as a 16-bit word, zeroing the hub byte 297 in every member.

**Attempt 1 (`story-rung3-s1`): the tour ping-ponged 350 <-> 351 80 times.** The segment worked (control in 352 at
SC 2600). Then: the 350 arrival spot is 18u outside the 351 door zone, `walk_to` steers one axis at a time with no
knowledge of doors, a key held into the fade carried the player back through, and the tour marked an exit tried
when it chose it. Fixed by the harness's new walkmesh routing (`Session.route_to` / `route_cross`, commit
`fad76077`: A* over the stock walkmesh avoiding every other exit zone; the frame proven on recorded positions;
calibration that never presses toward a zone; an exit counts only when it lands; one-way doors last).

**Attempt 2 (`story-rung3-s1b`, 5/7): no ping-pong -- 40 crossings, 26 landed, fields 350/351/352/354/356 -- but
never 450.** What stopped it was the live village, not the story:
- 353 (the Mayor's house): the gateway works; Mayor Kapu's arrival scene puts the player back in 350 (the story
  bars the house at this beat).
- 350 -> 450 and 350 -> 355 (and 350 -> 356 twice): planned, then stuck with control held, travelled 0. Every
  frame shows Zidane pressed into a villager or a Dali child standing in the path. (A first reading blamed the
  "ACTIVE TIME EVENT" card; that is the optional-ATE corner indicator, up through walks of 2446u and 3665u too,
  and it gates no movement.) The router avoids walls and exit zones but not NPCs -- the harness publishes no
  object positions -- and none of those NPCs is solid: stock 350 never sets object flag 16, so the engine lets
  the player through by insisting (FieldMapActorController.CheckCollFallback: 26 MovePC calls unbroken), which the
  routed walk's short bursts never did.
- 356 -> 358: stalled four times exactly the controller radius off triangle 50, a door strip whose triFlags
  0xA001 bar the controlled player (356's own door walk lowers the mask to 127). Not a body: a wall the router's
  raw walkmesh did not have.
- The trace: 0 join failures, no exceptions; no `Bit[2102] := 1` (450 was never entered).

Driver-side fix, built and fake-tested, not yet run in-game: `route_cross(unstick=True)` waits a stall out, then
pushes through in one unbroken hold, and only then routes round an unseen blocker; the tour routes on
`pathfind.PlayerWalkmesh` (closed triangles are walls: 356 -> 358 becomes a clean NO ROUTE) and scores
"stood inside the zone, nothing fired" by zone membership (`rung3_step1.py` docstring has the strike rule).

**Attempt 3 (`story-rung3-s1c`) -- THE PREMISE HOLDS: the blind tour reached 450 and the stock game wrote the
ping there.** With `route_cross(unstick=True)` the tour made 25 crossings (16 landed) through 350, 351, 352, 354,
355, 356 and 450 -- the 350 -> 355 and 350 -> 450 crossings that failed before now landed after waits and a push
through a villager (the owner, watching: the walker works, movement is choppy, roaming NPCs block it at times). The
controller's latch then flipped, Garnet spawned in the weapon shop, and the run stopped on her dialogue CHOICE
("You changed the way you talk!"): the cutscene waiter presses Confirm through boxes but never picks a choice, and
timed out after 240 s. So the formal checks read an empty trace; the raw trace was saved, and read offline it shows
the story's own route, found by a blind tour, writing exactly what the design predicted:

| Write | Where (field entry func +offset) | Frame |
|---|---|---|
| SC 2540 -> 2600 | 352 e17 f1 +5340 (the wake) | 9375 |
| 2078 := 1, 2086 := 1 | 352 e17 f1 (the wake) | 9375 |
| 2064 := 1, 2078 := 0 | 351 e16 f2 (the lobby exit) | 10628 |
| 2086 := 0 | 450 e0 Main_Init | 18172 |
| **2102 := 1**, 2085 := 1 | **450 e19 f2 +89 -- "Walk-in trigger (tag 2)"** | **18388** |
| 2102 := 0, **2079 := 1**, 2075 := 1 | 356 e2 f1 (the controller's latch flip, in the windmill) | 20861 |

The only writer of `Bit[2102] := 1` is field 450. All 381 script rows join a store in the bytes the game ran
(0 failures). Next: take a scene's default choice (the cursor's option) so the run finishes on its own and the
formal checks run; smoother movement; NPC positions from the agent (an engine change, owner's call).

**Attempt 4 (`story-rung3-s1d`) -- ★ STEP 1 PASSED IN-GAME 7/7, unattended.** The walker now plans around the
field's published objects (engine patch s89, live: every actor's position, collision radius, `solid`, and the
contact/talk trigger radii) with `route_cross(npcs=True, smooth=True)`, and scenes answer a choice with the game's
own default (`watch_cutscene(choices="default")`). 27 crossings, 17 landed, through 350/351/352/354/355/356/450;
mostly clean plans round NPCs, one push-through, no bump loops.
- **S1-PING:** `Bit[2102] := 1` written once, by field 450 alone -- entry 19, tag 2, offset 89, its walk-in trigger.
- **S1-ADVANCE:** the latch flipped, Garnet spawned in the weapon shop, the walker answered her two choices with
  the defaults ("You're doing great!", "You were Ruby!"), and the story moved to SC 2610 -- the tour stopped by its
  own rule (pass 2, crossing 27).
- **S1-JOIN:** every script row joined its store in the bytes the game ran; NC-THROW clean.
- One open oddity: 350 -> 351 in pass 2 came back `blocked` both in this run and the last (NPCs gather near the
  inn door by then); it did not stop the tour.

Next: the fork sides (F0 = the current import-chain output, which omits 450; F4 = the round-4 seed, with the
297-clobber the research found) against this stock run -- the retrodiction itself.

### Rung 3, the retrodiction -- session 1 (`story-rung3`, VOID by its own rule)

The fork sides are deployed (F0 = today's import-chain, 30831-30841, 450 a seam from member(350); F4 = round 4
exactly, 30842-30852 -- `rung3_forks.json`) and the nine-run session ran against the frozen predictions
(`rung3_predictions.json`, sha 220532a8, recorded before run 1). Pre-flight passed on the live install (manifest,
registrations, ForkDonorPatch, member floors = donor floors, exits, no stock overrides).

**Round 1 was covered on every side (S#1, F0#2, F4#3); every later run was VOID** -- the scripted wake left
Zidane at (-133, 847) in the inn room, 59u off the walkmesh edge, and the planner's fixed 80u wall clearance
found no route out (the real player radius there is smaller). The VOID rule did its job: every retrodiction
check reported VOID (1 of 3 covered runs a side), never a verdict it had not earned; R3-DONOR, R3-JOIN (0 join
failures over all 13 runs) and NC-THROW passed.

**An exploratory N=1 look at round 1 (NOT the registered verdict -- the analysis re-run with min_covered = 1):**
- R3-PING: `Bit[2102] := 1` written by 450 alone.
- R3-SEAM: F0's first seam `member(350) [30833] -> 450`; the ping reached only across it; no F0 donor writes it.
- R3-ADVANCE: F0 reached 2610 in the REAL 354 (after the seam the morning plays in the real game); F4 never did.
- R3-LATCH: for F4 every hub-gated write is STOCK ONLY (351's lobby 2064/2078, 450's 2086 := 0, 450 e19's
  ping/296/2085, the controller's 2079/2075), and the CLOBBER report names byte 297.
- R3-PREEMPT: 2064, 2079, 2075 stamped in every F4 member, beside the stock writers that set them later
  (351 e16 +112; the 356 controller +222/+315).
- R3-NULL-PRE / MIRROR: two STOCK ONLY keys, `359 e5 t17 +49 Byte[299] = 6 / 7` -- a villager's dialogue
  timer that counts frames until Confirm (`while Byte[299] < 30 && !KEYON(Confirm): Byte[299]++`), i.e. input
  timing, not a fork difference. N = 3 exists to turn exactly this into UNSTABLE rather than STOCK ONLY.

Next: the start-clearance fix (plan out of a spot tighter than the planning clearance, never deeper), then the
session again for three covered runs a side.

### Rung 3, the retrodiction -- session 2 (`story-rung3b`): 16/18; both misses are the walk's order, not the fork

Ten runs, 7005s, against the same frozen predictions (sha 220532a8). Coverage: S 3 of 3, F0 3 of 4 (run 2 VOID:
boxed among the walking Dali children after Vivi's scene, the story never moved; re-run 10 replaced it), F4 3 of 3.
- **PASS:** the six pre-flight checks, P-FROZEN, R3-RUNS, R3-DONOR, R3-JOIN (0 failures), NC-THROW, and every
  retrodiction claim at N = 3 -- R3-PING (`Bit[2102] := 1`, writers {450: 3}), R3-SEAM (every F0 run's first seam
  `member(350) [30833] -> 450`, the ping reached only across it, no F0 donor writes it), R3-ADVANCE (F0 reached 2610
  in the REAL 354 every run, F4 never), R3-LATCH (every hub-gated write STOCK ONLY for F4; the CLOBBER report
  names byte 297), R3-PREEMPT (2064/2079/2075 stamped in every F4 member beside their stock writers).
- **FAIL R3-NULL-PRE:** its claim held -- MISSING 0: all 171 keys stock writes before 450 in every run were
  written by the members in every F0 run -- but its non-vacuity clause did not: 40 tour keys (want >= 60), none
  from 355 or 356.
- **FAIL R3-MIRROR:** FORK ONLY `355 e3 t0 +12 SByte[296] = -64`, `355 e18 t0 +383 Int16[241] = 12`; STOCK ONLY
  `350 e2 t1 +12 / +49 SByte[296] = 1 / 2`, `356 e2 t1 +12 SByte[296] = 1`, `355 e18 t0 +383 Int16[241] = 8`.

**The diagnosis (the traces, run by run): one cause -- the sides walked Dali in different orders.**
- S#7 and F0#5/#8 crossed identically until 350 exit 4 (to 355). There all three stock runs came back `boxed`
  (the children, the defect below) and went on to 450 first, seeing 355 only after it; all three F0 runs crossed
  first time and saw 355 before the seam. (S#1 also missed 356 before 450.)
- `SByte[296]` is a countdown the morning runs after the ping: 450 e19 sets it to 3, each room's controller
  (tag 1, +12) steps it down on entry (350's re-arms it, +49), and the room that takes it to 0 does the flip
  (`Int16[241]` 8 -> 32, 296 := -64). Which room writes which value IS the visit order after 450. `Int16[241]`
  is order-carried the same way (450's Main_Init sets 12 -> 8; 355's +383 stores what it finds), and 355 e3's
  same-value `-64` store runs only while the countdown is idle -- only when 355 comes before 450.
- NULL-PRE's "before 450 in every stock run" lost 355 (after 450 in every stock run) and 356 (after it in S#1).
- None of the six keys is a fork difference: each is a (state, order) pair both sides write under the same walk.
  The registered verdict stays 16/18. What failed is the design's untested premise that both sides walk the same
  route -- `dali_tour.py` said so in a docstring and nothing checked it. The within-side walks are not fixed
  either (every stock run's room sequence differs), so noise was never the risk; a SYSTEMATIC side difference
  (3 of 3 boxed vs 0 of 3) was, and pattern-level STOCK/FORK ONLY cannot tell that from a fork difference.

Next: (1) a box whose rule-breakers are walking waits for them before it scores a strike; (2) take the order out
of the comparison by construction -- each fork run REPLAYS its stock partner's landed crossings (same exits, same
order, each retried until it lands, VOID if it cannot), then tours blind past the partner's advance -- registered as
predictions v2 before session 3, the claims unchanged; (3) session 3.

### Rung 3, the retrodiction -- session 3 (`story-rung3c`, predictions v2): ★★ 17/18, the one non-PASS a VOID

Nine runs, 5481s, no re-run needed: S 3 of 3, F0 3 of 3 (each replayed every step of its partner's walk -- 21, 23,
23 -- and its story moved on at its partner's advancing step, in the real 354), F4 3 of 3. Predictions v2 (sha d6dd541c),
frozen before run 1.
- **PASS** -- the six pre-flight checks, P-FROZEN, R3-RUNS (0 VOID runs), R3-DONOR, R3-JOIN (0 failures), NC-THROW;
  and the retrodiction: R3-PING (`Bit[2102] := 1`, writers {450: 3}), R3-SEAM (every F0 run's first seam
  `member(350) [30833] -> 450`, the ping reached only across it, no F0 donor writes it), **R3-MIRROR (0 FORK ONLY,
  0 STOCK ONLY, 0 clobbers -- with the walks paired, today's import-chain writes exactly what stock writes, less
  what lives across its seam)**, R3-ADVANCE (F0 at 2610 in the real 354 every run; F4 never), R3-LATCH (every
  hub-gated write STOCK ONLY for F4; CLOBBER names byte 297, 1 -> 0 by the seed's `UInt16[296] = 192`),
  R3-PREEMPT (2064/2079/2075 stamped in every F4 member, beside their stock writers).
- **VOID R3-NULL-PRE** -- the claim held: 205 keys stock writes before 450 in every run, MISSING 0; 80 of them first
  written in the tour, from 350/351/352/353/354/356 -- but no stock run gave 355 before 450 (S#1 never entered it:
  a Dali child pinned Zidane short of its door twice; S#7 took it after 450 after a LIVE miss there), so v2 names
  the stock side's evidence short: too little to say, not a falsification. Its six PARTIAL keys are one site,
  `359 e5 t17 +49 Byte[299] = 1..6`: the villager's count of frames until Confirm, in the scripted segment (F0#5's
  Confirm landed before the loop's first tick) -- input timing, not the fork.

**What rung 3 proves.** The instrument does the job the arc built it for: pointed at a stock zone and two forks of
it, with no script reading, the set difference names the missing field and its store (450 e19 +59, the ping), the
fork's seam into the real game, the seed's pre-empted latches beside the stock writers they pre-empt, and the
16-bit write that clobbers its neighbour byte -- and says nothing else. What it cost to get a clean comparison is a
law of its own: **a fork-vs-stock diff is only as good as the walk is paired** -- a story byte like the
`SByte[296]` countdown carries the visit order, and a blind walker that behaves systematically differently on two
sides (3 of 3 boxed vs 0 of 3) fabricates STOCK/FORK ONLY keys the pattern-level compare cannot tell from a fork
difference. Replay the stock walk on the fork side; judge coverage, not outcome.

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
