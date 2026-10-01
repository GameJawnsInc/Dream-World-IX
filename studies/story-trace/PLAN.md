# The story-write trace (EB board #3)

**Status:** ★ **rung 0 in-game PROVEN 11/11** (`story-rung0`): s88 is live (sha `c55377f6c137d442…`, backups `20260924-172331`), and the trace on stock Lindblum 552 joined every script write to a store in the stock bytes. **Rung 1 ★ in-game 11/11** (`story-rung1`): the residue net and the epochs. **Rung 2 ★ in-game 8/8**
(`story-rung2`): THE NULL PAIR -- stock 552 x3 vs its verbatim fork x3, STOCK ONLY and FORK ONLY both empty.
**Rung 3 step 1 ★ in-game 7/7** (`story-rung3-s1d`): an unattended blind tour of stock Dali reached 450, the
trace named 450 as the only writer of the ping, and the story moved on by itself. **Rung 3 ★★ THE RETRODICTION,
in-game 17/18 + 1 VOID** (`story-rung3c`, predictions v2): against stock Dali x3, today's import-chain (F0, x3,
each replaying its stock partner's walk) and the round-4 seed (F4, x3), the trace -- no script reading -- named
450 as the ping's only writer, F0's seam into the real 450, F4's pre-empted latches and its byte-297 clobber, and
found F0 otherwise write-for-write stock (MIRROR: FORK ONLY and STOCK ONLY empty). The VOID is NULL-PRE's
stock-side evidence from 355 (a walker at its door). **The walker now meets stock's door facing gate ★★ in-game
8/8** (`story-facing-check`: the rung-3 miss measured, then the s90 closed loop turned him in place and crossed) and
a tour on it 7/7 with no facing miss. **Rung 4 ★ offline on session 3's real traces:** `fork-report <field> --trace`
shows the traced set difference cut to one field (351: the pre-empted latches and the byte-297 clobber; 450: no
member, every write reached only across the seam), and the per-field shares partition the whole comparison exactly.
**Session 4 ★★★ 18/18** (`story-rung3d`): every stock run entered 355 before 450, and R3-NULL-PRE's VOID is a PASS
(214 stock keys before 450, all written by the members). The ladder's rungs are all done. **F5 ★★ THE HUB LANE
UNDER THE TRACE, in-game 28/28** (`story-rung5`, predictions v3 sha `d3ae4121`): New Game -> the hub's journey pick
-> 12 pure verbatim members wrote what stock Dali writes, key for key, on paired walks. MIRROR was empty and 450 ran
as a member with no seam. The seed stamped exactly its three frozen rows, and the story advanced in member(354) on
stock's step. **F5b, the post-wake entry** (`story-rung5b`, predictions v1 sha `bab9e642`): **VERDICT: NOT PROVEN:
party -- proven: state, latches, walk.** The fixed seed entered past the wake landed on stock's hand-over state bit
for bit, the calibration control failed exactly as registered, and the walk matched stock. The party proof leg hit
a kit-template defect (below) and is VOID. **F5c ★★ THE RE-RUN ON THE AMBIENT-FIXED HUBS** (`story-rung5b2`,
predictions v2 sha `7cf2fe8c`): **VERDICT: PROVEN** (all four halves: state, latches, party, walk; 40 checks) and
**THE FIX: PROVEN** (the traced hub revisit sets the 9 and the restored tail clears it). The seed resolver's
post-advance phase is proven in the game at Dali 2600 -> 351/e6.

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

### Rung 3, the retrodiction -- session 4 (`story-rung3d`, predictions v2): ★★★ 18/18, the VOID now a PASS

Run on the fixed walker (door pin, the s90 closed-loop facing, the tick clock), same predictions v2 (sha d6dd541c,
P-FROZEN), 5730 s, nine runs and no re-run: S 3 of 3 (each moved the story to 2610 in 354 by itself, pass 2,
crossing 27), F0 3 of 3 (each replayed 24 of its partner's 24 steps, then 2610 in the real 354), F4 3 of 3 (passes
exhausted, the story never moved). **Every stock run entered 355 before 450** (the tour order 350 353 350 355 350
450), which is what session 3 lacked.
- **R3-NULL-PRE PASS:** 214 stock keys before 450 in every covered stock run, and all 214 written by the members
  in every covered F0 run: MISSING 0, PARTIAL 0. 95 of them were first written in the TOUR (want >= 60), by
  donor {350: 29, 351: 12, 352: 3, 353: 10, 354: 15, **355: 12**, 356: 14}. `fork-report 355` on these traces:
  12 of 12 matched, STOCK ONLY 0, FORK ONLY 0.
- Every other check PASSed as in session 3: R3-PING (writers {450: 3}), R3-SEAM (member(350) [30833] -> 450 in
  every F0 run), R3-MIRROR (0/0/0), R3-ADVANCE, R3-LATCH, R3-PREEMPT, R3-JOIN (0 failures), NC-THROW.
- **The render rate flipped WITHIN the launch:** 59.0 fps at the start, 31.4 during run 3, 59.7 from run 4, then
  31.8 during run 7. Each flip was measured by the driver's tick clock (`TickClock`, "was ..."), and the walk
  planned on the new rate: 304 crossings, 10 gated doors faced by the closed loop (all measured), no facing
  miss. So the rate is not fixed per launch. CPU load is not the cause: a probe with all 12 logical CPUs busy
  held a flat 60.0 fps (`studies/test-harness/render_rate_probe.py`). The open lead, unverified: both drops came
  a crossing or two after a failed bounce into 353, and the rate came back after the return to the title.

Archived at `C:\gd\Dream-World-IX\.harness-runs\20260928-011959-story-rung3d\` (traces, per-run logs, session record,
the live log `rung3d_session.log`). **Rung 3 is closed: 18/18 on the registered predictions.**

### After rung 3: the walker meets stock's door facing gate (★★ in-game 8/8, and a tour on it 7/7)

The 116-miss diagnosis (research `rung3-5`) left one class open: **23 misses were stock's door facing gate** -- he
stood in the door's region facing wherever the walk left him, nothing fired, and the tour struck the door. Grounded
in the engine and the stock bytes (research `rung3-6`): 122 of 1393 walk-in gateways (98 fields; 6 of 350's doors,
and 351/353/356 have one each) run the warp only while his facing byte is within 47/256 of a turn of the bearing to
his projection onto the region's FIRST edge -- strict (48 fails), re-tested every tick he stands in it; the facing
lerps 40% per MovePC CALL (a walked tick is one), a press into a wall still turns him, and `player.dir` is 0 on
every field. Built: `content.doorface` (the rule, engine-exact, no game table), `scan_gateways`' `face_gate` /
`region` (the detector matches the stock census 100/100), a fake game that models the gate (so a test can fail),
and a walker that faces a GATED door when it stands in it with nothing fired. **Engine patch s90** (deployed by the
owner) publishes the real facing (`player.face`, the byte the gate compares, from EBin's own read) and a `turn`
verb that turns him in place, so on this engine the step is a closed loop: turn with zero travel, judge the door by
the MEASURED byte. The walked press, sized by a prediction and kept inside the region, is the fallback on an engine
without s90. The tour's verdicts: a gated door the walker never faced is LIVE (no strike; a replay steps back first),
a door faced and still shut is the door's MISS, and the 353 "never became playable" crossing is a bounce. Four
workflows, each reviewed from several lenses with every finding verified (31 + 16, all real, all fixed or pinned),
mutation-tested.

**In the game, 2026-09-27 (owner's go): ★★ `story-facing-check` 8/8** (`facing_check.py`, 189 s; run 1 stopped at a
calibration a wall slide deflected -- the scenario now seeds 350's TWIST prediction and checks it). At 350's door to
351, from the tour's own story state (the segment to 352 at SC 2600, then 350 by entrance 2 at (258, -58), byte 50):
s90 publishes the facing and it is the kit's byte of the yaw (FC-CAP, FC-BYTE); three in-place turns moved him 0.0u
and each reported the byte state.json shows (FC-INPLACE); both pads converged to the TWIST's predicted heading to
0.001 deg (FC-BASIS, right -88.594 / left 91.406); a 3-frame turn left 180 x 0.6^6.00002 of the angle -- whole
MovePC calls, 40% each (FC-LERP); **standing in the door's region 113/256 off the door, it stayed shut for 90 frames
(FC-SHUT: the rung-3 miss, measured)**; and **from that spot the walker's closed loop turned him in place on `right`,
travelled 0.0, and crossed to 351 (FC-FACE: faced, face_measured, during "face")**. Then **`story-facing-tour` 7/7**
(`rung3_step1.py` on the fixed walker, 723 s): 28 crossings, 19 landed, SC 2600 -> 2610 by itself, 450 again the
ping's only writer; every gated door it walked to opened -- 350 -> 351 twice (the door session 2 missed 10/10), 351
-> 352, 350 -> 354, 350 -> 356 twice, 350 -> 355 -- with no facing miss (23 in sessions 1-3). Honest limits: those
all opened DURING the walk (the facing step was not needed on this tour; FC-FACE is its proof), 355 was again entered
only after 450 (R3-NULL-PRE still wants a 355-before-450 run), 356 -> 358 found no route twice (planner geometry,
not facing), and **the game rendered at 28-53 fps under the harness across runs (31, 53, 28, 32), never the 60 the
harness's per-frame WALK_SPEED/RUN_SPEED assume** -- the closed loop measures, but the open-loop fallback and every
press sized in frames inherit that error. (Measured since over 79 archived launches: the STEADY rate is ~31 or ~60 fps
for a whole launch, the quoted figures ring averages over field loads; the driver now plans in 30 Hz ticks by a rate
it measures -- `tools/harness/tickrate.py` -- and the per-frame constants are gone.)

## Rung 4 result -- fork-report shows the traced set difference (★ offline, on session 3's real traces)

`fork-report <field> --trace <stock runs> [--fork-trace <fork runs> --member ...]` puts the trace under the report,
cut to the one field (`storytrace.FieldShare`: every key names its donor, so a field's share is the keys whose
donor is the field, over the same runs). Alone, it lists the stock walk's writes in the field and splits the
static Story-writes candidates into three groups: written by the field's own script (value and run count), never
run (no evidence), and traced writes no candidate lists. With a fork side, it prints the set difference cut to
the field, and then the whole comparison's totals: a clean field in a broken chain never reads clean.
`docs/FORK_REPORT.md` has the reference.

**The pass, on session 3 (`story-rung3c`), no script reading:**
- **`fork-report 351` against F4:** STOCK ONLY holds the lobby exit's `Bit[2078] := 0` / `Bit[2064] := 1`
  (e16 +71/+112) and 351's hub-gated Main_Init stores. PRE-EMPTED names 2064/2075/2079 and SC 2600 beside their
  stock writers. The seed word `UInt16[296] = 192` is the NEIGHBOUR-BYTE CLOBBER of hub byte 297 (1 -> 0, 3/3).
- **`fork-report 450` against F0:** 450 is NO member; all 20 of its stock keys, the ping `Bit[2102] := 1` at e19
  +59 among them, are REACHED ONLY ACROSS A SEAM from member(350).
- **`fork-report 350` against F0:** clean (STOCK ONLY 0, FORK ONLY 0) and it names the seam.

These are rung 3's R3-LATCH, R3-PREEMPT, R3-SEAM and R3-PING, one field at a time. Across every donor field on
both chains, the shares partition the whole comparison exactly: each key is in exactly one field's share, and the
shares' union equals the whole comparison. That invariant is now a test on the real Dali rows. Session 3's frozen
analysis re-reads the same after the change (17/18 + the VOID).

**Review (`wf_f8ed20fb-b09`):** three read-only lenses, a 108-mutant test-strength pass and a skeptic per group
found 16 distinct confirmed defects, all fixed (`356ac508`); every new test fails on the code before it. Three
were in the reader under every report:
- **Alignment:** the skeleton fallback in `align_function` paired two different expression statements. An
  inserted same-shape `SET` filed the fork's real store as its prepend, and then PRE-EMPTED it.
- **Seams:** `Comparison.seams` counted a run twice when it crossed twice. It also kept only the first run's
  fields: on session 3, F0's seam now also names the real 355 that run 8 walked, the only change in the whole
  reports.
- **Repeated flags:** argparse kept only the last of a repeated `--fork`.

## F5 -- the hub lane under the trace (★★ in-game 28/28, `story-rung5`)

### The session (2026-09-28, `story-rung5`): 28/28, no re-runs

- **Deploy.** 13 ids went additively into FF9CustomMap, and all 7 static pre-flight checks passed on the live install.
  The session's launch was the one relaunch. It took 3541 s at a steady ~60 fps. The install was left clean: no
  arm file, and `Memoria.ini` untouched.
- **P-HUBLEG, the hub leg's first in-game test, PASSED.** It measured Stiltzkin's r = 152, talk_r = 338 and the
  approach (304, 127, 176), which is the geometry read offline from the hub's bytes. Up and down were blocked from
  the spawn, as the collision model predicted, so the up axis was derived from the hub's twist prior. The design's
  blind calibration would have refused there and cost the launch. The talk opened on the first try, and the stay
  row stayed.
- **The frozen six** (S F5 S F5 S F5) were **all covered**:
  - every F5 run's pick landed in 31111 (a hub leg of about 6 s, 1 try, 1 press);
  - its segment woke in member(352) at 2600;
  - it replayed its partner's whole entered walk (22, 22 and 24 steps);
  - SC advanced to 2610 in member(354) on the partner's step.
- **Every check PASSED:**
  - R5-STAMP: exactly the three frozen stamps, joined against the hub's bytes;
  - R5-MIRROR: 0 FORK ONLY and 0 STOCK ONLY against a stock guard of 283 keys;
  - R5-NOSEAM and R5-PING: 450 wrote the ping as member 31112, with no seam anywhere;
  - R5-STATE: the wake-instant state is equal in all three pairs, bit for bit (byte 299 aside);
  - R5-SEGMENT: 117 segment keys, equal in every pair;
  - R5-PARTIAL: 5 walk-order keys differ between pairs and agree within each;
  - R5-JOIN 0 failures, R5-PREEMPT empty, NC-THROW nothing thrown.
- **The offline `--analyse`** of the archived run reproduces both reports byte for byte.
- **A second instrument agrees.** rung 4's `fork-report <field> --trace` on the same traces, cut per field, gives
  0 STOCK ONLY and 0 FORK ONLY in every field these walks entered. Matched keys: 359 49/50, 351 23/25, 352 63/63,
  350 40/43, 353 12/12, 354 23/23, 355 12/12, 356 28/28, 358 13/13, 450 20/20.
  - Each field's remainder is UNSTABLE in equal counts on both sides: the timing byte 299 and the walk-order keys.
  - The 7 whole-comparison FORK ONLY keys are the hub's own rows, filed under 31100 (no real donor).
  - 312 and 357 were never entered by any walk.

**What it does and does not prove.** At this entry, the hub lane as shipped plays the Dali morning write-for-write
like stock, from the pick to the story's advance, and 450 is a member. It does NOT test the seed's beat-instant
values, as predicted: 359's own start-up and the night segment re-create them (the KNOWN-GAP; R5-STATE PASSes on the
state the segment produces). The offline-predicted seed defects for an entry past the wake are still open and
untested in the game: the ATE latches 2078/2086 left 0 where stock has 1, and all four party members where stock
has Zidane alone. F5b would test them. The trace cannot see party state.

**Archive:** `C:\gd\Dream-World-IX\.harness-runs\20260928-153015-story-rung5\` (traces, logs, reports, the scripts
snapshot, `rung5_session.console.log`).

### The build (offline)

**What it tests.** Today's hub lane, New Game -> hub pick -> a chain of pure verbatim forks, as a third fork side
next to stock Dali, under THE PAIRED-WALK LAW and rung 3's machinery. The owner chose the lane as shipped: entry at
member(359), no F5b.
- **The build** (fresh ids, the durable tree `C:\gd\_ns_playtest\f5`): the hub T5_HUB 31100 (gen-hub's BG-borrow of
  950's room, no ForkDonorPatch row) and 12 pure verbatim Dali members 31101-31112, 450 among them as 31112.
- **The hub's journey row** stamps SC 2600, words 208=0 and 297=1, and a party of four, with no flags. It then warps
  to member(359) = 31111.
- **The pairing.** The hub's rows are the SEED, judged only by R5-STAMP, R5-SAME and R5-STATE. Both sides are
  compared from their first row in their own 359.
- **The known gap.** At this entry, 359's own Main_Init re-stamps the zone, so the segment masks the seed's
  beat-instant values; R5-STATE records this.
- **The seed itself is predicted wrong offline for any entry past the wake.** The resolver leaves the ATE latches
  2078/2086 at 0 where stock has 1, and adds all four party members where stock has Zidane alone.

**The code** is `rung5_hub.py`: the session, the analysis, and the CLI (`--offline-check`, `--preflight`,
`--analyse`). The one shared change is `dali_tour.segment(enter=)`; rung 3 passes no `enter` and is unchanged.
- **`rung5_dryrun.py` is 55/55:** the base, 46 mutants and guards, 2 must-PASS cases and 5 offline pre-flight cases.
  It builds the 13 fields itself and checks each `.eb` against its frozen sha.
- **Tests:** 23 FakeGame tests of the segment and the hub leg in `test_harness.py`.
- **Frozen:** `rung5_predictions_v3.json` (sha `d3ae4121`, LF, `-text`) and `rung5_forks.json` (deployed_at null).

**Where the design was wrong against the bytes** (each is declared in the predictions' implementation list):
- **The spawn is inside Stiltzkin.** The hub spawn stands 76u inside his collision radius (r 152, push-out 136 < r),
  so every probe that faces him is undone and a blind `calibrate_axes` cannot work there. The leg calibrates on the
  hub's own SetControlDirection twist `[255, 255]`, and P-HUB checks that twist in the bytes.
- **The walk goes the other way.** The approach walk goes WEST, away from him, so he is turned in place before every
  Confirm.
- **Two clocks.** `hub_s` covers the leg up to the pick's Confirm. The new `entry_s` (60 s) covers the press to the
  landing in 31111. So no budget stop can follow a stamp.
- **Stop classes.** The review corrected these: a budget stop is DRIVE, and a stall at member entry after the stamps
  is FORK-STOP `segment@359`. A replay point now carries its step name (`replay@15(350.6 -> 450)`), so two different
  crossings no longer count as one reproduction.

**The hub leg was unverified in the game at the freeze.** P-HUBLEG measured it before run 1 and passed (above).

**A pre-existing red, not F5's:** `rung3_dryrun.py` is 79/80, and session 3's S_vs_F0 report gains `, 355` on its
"real fields seen across it" line. Both come from rung 4's seam listing (`356ac508`). HEAD's committed code produces
the identical output. Re-baselining rung 3's archived reports is the owner's call.

## F5b -- the seed resolver's post-advance phase, entered past the wake (in-game: NOT PROVEN: party)

**What it tests.** The kit's fix (`storyseed.py`'s post-advance phase, `4a331cbb`): a hub journey row stamps THE
HAND-OVER STATE OF ITS ENTRY. Entered past the wake at member(351) = 31101 through entrance 6 (stock's own first
step after the wake), the row carries the wake's latches 2078/2086 = 1, a party of Zidane alone (the wake's three
presence-guarded removes) and the entrance. F5's pre-wake row is byte-identical. The design, its three critics and
the 12-agent build are archived at `C:\gd\Dream-World-IX\.harness-runs\story-trace-archive\f5b\`.
- **Sides:** [S, F5B, CTL] x 3, on F5's 12 deployed members. T5B_HUB 31113 carries the fixed row; T5B_CTL 31114
  carries today's pre-phase row at the same entry, as a calibration control predicted to fail exactly as registered.
  Each fork run replays its stock partner's walk from step 2 (CTL: step 2 only).
- **Frozen verdict rule:** PROVEN / NOT PROVEN: <half> / FAILED: <check>, over four halves (state, latches, party,
  walk). Never a PASS count.

### The session (2026-09-29, `story-rung5b`): VERDICT: NOT PROVEN: party -- proven: state, latches, walk

- 3440 s, one launch, no re-runs. All nine runs covered: S 3, F5B 3, CTL 3. The install was left clean.
- **P-HUBLEG passed for both hubs.** The hub-arrival autosave, the party instrument, read fresh and New Game's
  [0,255,255,255] both times.
- **State (proven).**
  - R5B-LAND: at the landing, F5B equals stock outside the registered 53-bit landing set, which differs exactly as
    registered, in all 3 pairs.
  - R5B-STATE: after 351's own arrival, F5B equals stock bit for bit outside the registered 34-bit residual R.
  - R5B-CONTROL: all 5 clauses PASS over 3 covered CTL runs. Today's row at the same entry fails exactly as
    registered, so the instrument is shown able to fail in the game.
- **Latches (proven).**
  - R5B-ECHO: the latch consumers fire as in stock (351 e16 t2 ip105 clears 2078; 450 clears 2086).
  - R5B-ARRIVAL: the entry's arrival is stock's step-1 arrival, exactly the 11 keys.
  - R5-LATCH: all 8 hub-gated writes on both sides.
- **Walk (proven).**
  - R5-MIRROR: 0 STOCK ONLY, and 8 FORK ONLY, all SUPP-admitted (the 5 registered blind-spot keys among them).
  - R5-PARTIAL: equal in every pair.
  - R5-REACH, R5-PING and R5-NOSEAM: 450 wrote the ping as a member.
  - R5-ADVANCE: 2610 in member(354) on the partner's step minus one.
  - R5-JOIN 0 failures; NC-THROW nothing thrown.
- **Party (NOT PROVEN): P-PARTYREMOVE is VOID.**
  - Its known-positive reads came out as registered: r1 [0,2,3,1] after the CTL pick, and r2 [0,2,3,1] after the
    warp into T5B_HUB from 31101.
  - The F5B pick then landed in 31101 on stock's leftover developer window "Error Env Play() / Slot=0" (351
    Main_Init, WindowAsync 51), which the harness could not close. That happened twice, so R5B-PARTY is VOID.
- **The raw party reads, recorded and not judged:** F5B landed [0,255,255,255] and ended [0,255,255,255] in all 3
  runs, which is stock's post-wake party. CTL landed [0,2,3,1]: the old row's party defect, in the game. F5B's match
  is not proof the removes act, because New Game already gives [0,255,255,255]. P-PARTYREMOVE existed to settle
  exactly that.

**The cause is the kit's blank template, not the seed and not gen-hub (corrected by F5c).** Every synthesized
Main_Init starts from the kit's blank field: stock field 1357 (EVT_LIND2_CS_LB_HNG_0) patched by
`data/provenance/blank.<lang>.patch`, whose ops `[c 435 29][c 532 105]` skip 1357 src[464:532] -- both of its
report/clear blocks. So the blank keeps stock's ambient-sound prologue (Int16[9] := -1, then Byte[13] := 9 when the
field is entered with Byte[13] == 2, i.e. from a field whose ambient sound was still playing) and lost the tail that
clears the 9 (stock's rule: 813 of 818 Main_Inits close the prologue with it, right before `set MAP159 = 1`;
359.ebs:105-111 is one of them). That reaches EVERY synthesized build -- `new`, BG-borrow, `--editable` and
non-verbatim `--native` imports, campaign and journey synth members, gen-hub hubs, the bundled examples -- not gen-hub
alone; verbatim forks carry their donor's own tail. P-PARTYREMOVE is the only path that enters a hub from a Dali field
(31101 -> 31113, the harness's debug warp, which skips stock's exit idiom `Byte[13] := 3`). Every Dali field keeps an
arriving 9 and reports it with that window (351.ebs:16-30 and 326-340). The runs themselves enter the hubs from New
Game and never saw it. This is by the scripts' code and consistent with the observed window; the trace did not cover
that untraced leg (F5c's P-AMBIENT traces exactly it). A player meets it when a field entry skips the exit idiom: a
kit warp, or the New-Game override (F-WARP, F-NG below).

**Archive:** `C:\gd\Dream-World-IX\.harness-runs\20260929-001746-story-rung5b\`. The offline `--analyse` reproduces
both reports byte for byte.

### F5c: the ambient clear, and the v2 re-test (★★ in-game: VERDICT PROVEN, THE FIX PROVEN)

**The session (2026-09-29, `story-rung5b2`): 63/63; VERDICT: PROVEN: every check PASS (40 checks), 3 covered F5B
pairs, 3 covered CTL runs. THE FIX (in game, slot 0, hub revisit from 351): PROVEN.**
- 3100 s, one launch, no re-runs; S 3, F5B 3, CTL 3 covered. The fixed hubs 31113/31114 were redeployed in place
  from `cadc862a` (O13's deploy gate held; recorded in `rung5b_forks_v2.json`). The install was left clean.
- **P-PARTYREMOVE PASSED on its first attempt:** r1 [0,2,3,1] after the CTL pick, r2 [0,2,3,1] after the warp into
  T5B_HUB from 31101, r3 [0,255,255,255] after the F5B pick. The fix's party removes act on a real roster.
- **P-AMBIENT PROVEN (attempt 1 of 1):** (a) 31113 e0 t0 ip109 Global.Byte[13] 2 -> 9 (the prologue still sets the
  9 on a revisit from 351), (b) ip275 9 -> 0 (the restored tail clears it), (c) 31101 e0 t0 ip134 0 -> 1 (351 arrives
  clean), and control came back in 31101. The window that VOIDed session 1's leg never appeared.
- **Every check PASSED**, among them HUB-ROWS-SAME (the fixed hubs' New-Game-path rows are session 1's exactly),
  R5B-LAND / R5B-STATE / R5B-CONTROL (state), R5B-ECHO / R5B-ARRIVAL / R5-LATCH (latches), R5B-PARTY (party, the
  removes now proven load-bearing), R5-MIRROR / R5-PARTIAL / R5-REACH / R5-PING / R5-NOSEAM / R5-ADVANCE (walk),
  and NC-THROW.
- The offline `--analyse` of the archived run reproduces both reports, the VERDICT line and THE FIX line byte for
  byte. Archive: `C:\gd\Dream-World-IX\.harness-runs\20260929-163016-story-rung5b2\` (incl. `ambient_trace_1.jsonl`).
- **Consequences (as registered in v2's fix_line):** THE FIX: PROVEN with the full suite green licenses the master
  merge of `claude/ambient-clear`; F-REDEPLOY may now proceed, one owner-gated change at a time. The claim covers
  ambient slot 0 on the revisit path from 351 only; slot 1, the full-opening New Game and audio remain untested.

- **The fix (kit, `claude/ambient-clear` e1317a42).** `content/ambient.py`: `build_script` restores stock's tail
  FIRST, silently -- `if Byte[13] == 9 { Byte[13] := 0 }` and the same for Byte[14], 38 bytes, each statement 1357's
  own encoding, no report window -- right before `set MAP159 = 1`. The blank, its patches and `blank.sha256` are
  unchanged. `tests/test_ambient.py` (25) pins it on 9 builds.
- **The merge gate.** `claude/ambient-clear` reaches master only after the in-game THE FIX line reads PROVEN.
  `claude/story-trace-f5b` carries the fix through TWO merges of that branch -- 10159945 (the fix, e1317a42) and
  e2d7757e (the review's tests and CHANGELOG wording, b90eae4a; the fix's code unchanged) -- and does not merge to
  master while it does. To merge the resolver first, or on FAILED, revert both, NEWEST FIRST: `git revert -m 1
  e2d7757e`, then `git revert -m 1 10159945` (the older one alone conflicts on the files the newer one edited).
  The predictions record both (`hub_fix.merge`, `hub_fix.remerges`).
- **v2** (`rung5b_predictions_v2.json`, frozen by F5c's freeze): session 1's whole shape re-run on the fixed hubs
  under v1's frozen rule plus HUB-ROWS-SAME (the hubs' New-Game-path e0 t0 rows exactly session 1's; load-bearing,
  state half). P-HUBDIFF (static): each hub is its preserved v1 build plus exactly the tail, 7 languages. P-AMBIENT
  (in game, traced, after P-PARTYREMOVE): P-PARTYREMOVE's leg with the story trace armed -- (a) 31113 ip109 2 -> 9,
  (b) the tail's ip275 9 -> 0, (c) 31101 ip134 0 -> 1 -- judged by a registered decision table and reported on THE
  FIX line after the VERDICT, never an input to it. Session 1 re-analyses on v1, unchanged. Frozen sha
  7cf2fe8cc2d63ad96b7d531ef885179e9c8e11aa8994955e8621a23717295688 (the review's re-freeze, before any v2 session
  or deploy; the first freeze, f50ce056, never ran), with `rung5b_forks_v2.json` 7aa6ad4b (deployed false).
- **The frozen dry-runs after the fix** (their tomls now build the fixed bytes): `rung5_dryrun.py --build
  C:\gd\_ns_playtest\f5\keep_v3\build` (or `--pre-ambient`); `rung5b_dryrun.py --predictions
  studies/story-trace/rung5b_predictions_v1.json --build C:\gd\_ns_playtest\f5b\keep_v1\hubs --members
  C:\gd\_ns_playtest\f5b\keep_v1\members` (or `--pre-ambient`). `--predictions` is now required. The preserved builds
  carry SHA256SUMS.
- **The review, fixed before any session.** Kit (b90eae4a, tests and CHANGELOG only, re-merged): T-AMB-2 pins the
  pass as build_script's FIRST step (no settle hold before the TAIL), T-AMB-1 iterates the literal (13, 14),
  T-AMB-4 pins classify's stricter all(); BREAK-IT's 8 and the review's 3 mutations all red; the full suite re-run.
  Study: the control marker's False is a LIVE measurement only -- a game that exited or a frozen channel leaves
  `hub_control` None (`hub_unmeasured`), so a crash after (a) is VOID cut-after-precondition, never a FAILED that
  would revert the fix; a cut trace (a collect error) never FAILs row 6 or 11 by what it lacks; the leg reports what it
  threw (its own log mark after the arm) on THE FIX line, report-only; P-AMBIENT never raises; a tracer fault during
  P-AMBIENT ends the session before its runs, named (the fault latches until a relaunch). The dry-run gained 11
  registered cases (7 P-AMBIENT -- among them amb-record-disagrees: THE FIX re-derives every attempt from its file,
  never the recorded verdict -- 2 HUB-ROWS-SAME, 2 P-HUBDIFF), and test_harness.py 5 FakeGame / unit tests plus the
  collect-before-restore order in test (7). Declared: **CARRY-CONSISTENCY's numbers half is regression-only for a
  change confined to the hub's Main_Init tail** -- the registered tail-first mutant re-derives all 25 carried numbers
  (the review deleted the seating clause and the case read PASS); its registered FAIL, and so its can-fail, rests on
  the SEATING clause (every base fork run's hub e0 t0 rows = `ng_rows`), which the frozen check text (F5c
  checks.json, verbatim) does not name.

**F-REDEPLOY: ★ DONE, all 47 proven in game.** The method was a splice, not a rebuild (`tools/ambient_splice.py`:
the live `.eb` plus exactly the TAIL). 4600 was proven on the New-Game route, and 6601-6603 each by the two-slot
clear. 31113/31114 were F5c's. The other 41 were spliced one id at a time and proven by the two-slot clear in one
run, `f_redeploy_rest.py`: 33 passed at once. The other 8 had all four rows at the predicted ips and failed only on a
stale bits sample; the trace's next write to [13]/[14] read old 0, and a re-run of the 8 with a fresh-sample read
passed 11/11. Every field's clear landed at the ips predicted from its own bytes. The original registration follows.

A deployed synthesized field keeps the defect until it is rebuilt and redeployed. The 47 live ids, by folder:
- `FF9CustomMap`: 4010-4013, 6500, 30416, 30801, 30860-30863, 30870, 30880, 30883, 30890, 30900, 30910-30912,
  30920-30922, 30925, 30930, 30935-30937, 30945-30949, 30955, 30956, 30960, 31100, 31113, 31114;
- `FF9CustomMap-world`: 4600, 6601-6603;
- `FF9CustomMap-schema`: 30820-30821;
- `FF9CustomMap-msgs`: 30601-30603.

The last two folders ARE in the live `Memoria.ini` FolderNames, at lowest priority (read while the fix was built;
the design had them UNVERIFIED), so their ids are live defects too. Priority: 4600 and 6601-6603 first, through the
world pack's own deploy path, then the New-Game re-wire. Each is its own owner-gated change with its own in-game
check, and none started before THE FIX: PROVEN (only 31113/31114 were redeployed by F5c; THE FIX read PROVEN in
`story-rung5b2`, so they may now proceed). Read-only verifier:
`ambient.classify` over every `<GAME>/FF9CustomMap*/StreamingAssets/**/field/us/*.eb.bytes`, catching `ValueError`.
The 47 ids read `missing` before a redeploy and `restored` after (measured read-only, by folder: FF9CustomMap 38
missing and 35 `stock-tail`, -world 4 missing, -schema 2, -msgs 3). Two readings are EXPECTED, never failures: every
verbatim fork reads `stock-tail` (its donor's own tail), and the New-Game override, FF9CustomMap-world's
`evt_alex1_ts_opening.eb.bytes` (stock field 70, one of stock's five fields with no tail -- 70 owns 643), raises
`ValueError` ("no `set MAP159 = 1` after its `Byte[14] := 1`"); the loop lists it as a stock exception and goes on.
The other follow-ups live in the kit CHANGELOG's Known issues: F-NG (the New-Game
override hands off with 643 playing), F-WARP (kit warps skip the exit idiom), F-IMPORT (imports lose the donor's
ambient; FORK_FIDELITY.md row 15); F-PROBE (a traced full-opening New Game) settles F-NG's path in game.

## O1 -- the opening under the trace: New Game to Alexandria (design)

**The question.** Over the game's first segment, does a verbatim whole-zone fork of Prima Vista write the real
game's story state key for key? And what does the real opening write? That second answer is the recorded ground
truth any later seed of the opening needs. O1 is the first segment of a walk through the faithful disc-1 opening
([[project-ff9-faithful-opening]]). Each segment is a paired stock/fork session under THE PAIRED-WALK LAW, and each
later one adds its zone to the chain.

**The segment** (two read-only readers, notes in the session scratchpad `opening_research/`): New Game -> 70 -> 50
(Cargo Room) -> 52 (Meeting Room) -> `Field(100)`. None of the three warps is gated by SC or by a flag. 50 runs on a
map-local stage counter, and 52 leaves on its choice.
- 50: two lines, then SC 0 -> 1000 (the segment's only SC write) before control. The player then walks to the candle
  (a region diamond round (0, 350)), confirms, and picks "Light the candle". Cinna's line follows, then the naming
  screen for Zidane (`Menu(1,0)`), then `Byte[6] |= 1`. After four lines comes the Masked Man battle (scene 336):
  the party is set to 9999 HP, and the AI ends it with a victory once he has taken 188 damage. Then eight lines,
  and `Int16[2] := 100`, `Field(52)`.
- 52: a scene with no control. Its one question defaults to "kidnap Queen Brahne", which loops back to the question;
  "Princess Garnet" moves on. Then FMV002, `Int16[2] := 102`, `Field(100)`.

**The sides.** S = stock. F = `import-chain 50 --verbatim --whole-zone --fresh-ids --id-base 31200 --name-prefix O1`:
the tshp zone's 20 fields (50-63, 65-67 and the disc-4 endings 3008-3010), deployed one member at a time to
`FF9CustomMap` 31200-31219 with one relaunch. Field 100 (alxt) is not a member, so member(52)'s `Field(100)` stays
real. That is the seam, and the segment ends there.

**The entry.** Each run: New Game, trace on, then in field 70 a raw `warp` to 50 or member(50) at entrance 0. This
is rung 3's own start. The New Game override stays the Southern Ring's (-> 4600), untouched. It skips FMV001 and
70's two post-FMV writes (`Byte[13]` 1 -> 2, `Int16[2] := 0`, already 0), identically on both sides. F-PROBE's trace
shows those are 70's only writes after its prologue.

**The route: one driver, both sides.** It acts only on what the game shows, in this order:
1. Field 100: stop.
2. The naming screen: `accept_name()`, a new harness verb (Confirm twice, back to FieldHUD, keeping the default name).
3. In battle: the tutorial screen gets Confirm; a command prompt gets Attack on the first enemy standing; a result
   gets `leave_battle()`.
4. A choice, by the segment's rule table on its text:
   - "Light the candle": that option.
   - 52's question: the option naming Garnet.
   - "Skip movie?" (a stray Confirm during FMV002): the game's default, don't skip.
   - Anything else: the run stops, VOID.
5. A dialogue page: Confirm.
6. Control in 50 before the candle: route to (0, 350) and interact. Control anywhere else: VOID.

Optional pickups are never taken. Each run has a 12-minute budget.

**The session.** One launch, S F S F S F. After each run it goes back to the title (rung 3's recovery ladder), saves
the trace (`run<i>_<side>.jsonl`) and rewrites the session record. A side short of 2 covered runs re-runs, up to 2
more each.

**Coverage.** A run is covered when its trace closed whole and it reached 100 by the route with every beat done:
candle, name, battle won, Garnet. The analysis reads covered runs only and needs at least 2 per side.

**The analysis and its checks** (frozen in `o1_predictions_v1.json` before any run). Each covered run is cut at its
first row in field 100, then goes through `storytrace.digest` (the fork side with its members) and `compare`.
- O1-FROZEN: the predictions' sha.
- O1-PREFLIGHT:
  - every member is registered once, with its ForkDonorPatch row;
  - each member's live `.eb` is the build's, and differs from its donor only in `Field()` operands remapped
    member to member;
  - no mod folder overrides stock 50, 52 or 100.
- O1-COVER: at least 2 covered runs a side.
- O1-LADDER, every covered run of both sides: SC 0 -> 1000 once, `Int16[2] := 100` in 50, `:= 102` in 52, and
  `Byte[6] |= 1` in 50. Each is checked at the ip predicted from the bytes.
- O1-NULL: STOCK ONLY and FORK ONLY are empty, and UNSTABLE holds only the registered battle noise (scene 336's AI:
  `Byte[206] :=` a random value, and `Byte[199] |= 2`).
- O1-JOIN: 0 join failures.
- O1-THROW: no exception through EventEngine/EBin/StoryTrace/HarnessAgent.
- Report-only: each fork run's dialogue transcript equals its stock partner's, page for page.

The verdict is PROVEN, NOT PROVEN: <the keys>, or VOID.

**Expected: a null.** The members are verbatim. Every `fldMapNo` gate that FORK_IDGATE_MAP lists for 50-52 is
already wrapped, and scene 336 has no next-field op for s24 to redirect. The null is the baseline each later segment
is read against: Alexandria, the castle, the play, the kidnapping, the crash. The stock runs are the opening's first
recorded story-state ground truth.

**Owner-gated:** the 20-member deploy with its ForkDonorPatch rows and the relaunch, and the session.

**Session `story-o1` (predictions v1 `49fd880f`): stopped after run 1, VOID at the candle.** The chain was deployed
(31200-31219, live preflight 5/5) and the instrument read true: run 1's trace wrote SC 0 -> 1000 at 50 e17 t1 ip1804,
the frozen key. The driver then failed the route twice at the candle, as the owner saw while watching:
- v1's candle point was the region's centre (0, 350), which is where the table stands. He stood in the region with the
  "?" up, pressed against the table.
- `interact()` refuses to press while a window is open. The region's own async hint ("Press the X button when the ?
  appears.") is up exactly while he stands where the Confirm works.

The fix was built and re-tested offline:
- v2 (`681398ac`) walks to (180, 290), the spot run 1 stood on with the "?" up.
- The driver pages no window that is up while he holds control; such a window is an overlay.
- At the candle it presses a plain Confirm and waits for the choice.
- `route_to(overlay_ok=True)` starts a walk under such a hint (the timed "Light the candle..." after 300 frames).

**Sessions `story-o1b` to `story-o1d`: each stopped at run 1 or 2 on a new driver fault, each fixed before the next.**
- o1b (v2 `681398ac`): the candle choice opened. It publishes as `['', 'ight the candle', 'Cancel']`, because the
  line after `[CHOO][MOVE=18,0]` loses its first character, and v2's rule missed it. v3 (`05fb803e`) matches
  "the candle".
- o1c (v3): run 1 (stock) reached 100 with every beat, but the Masked Man's scripted end reports result 2,
  victory-no-pose, and v3 counted only 1 as won. v4 (`1ac32b3a`) registers `battle_won` [1, 2]. The run read the
  checks true on real data: the four ladder keys, 0 join failures, and the only battle rows the registered
  `Byte[206]` noise.
- o1d (v4): run 1 reached 100. Run 2 could not get back to the title: the soft reset does not reach it through
  Alexandria's opening. `end_run` now warps to 4600 first, then resets.

**★★ Session `story-o1e` (predictions v4 `1ac32b3a`): VERDICT: PROVEN, 7/7.** Over New Game -> 50 -> 52 ->
`Field(100)`, the verbatim fork of Prima Vista writes the real game's story state, key for key.
- O1-COVER: stock 2 of 3 covered, fork 3 of 3. S#1 was VOID: a `fight()` step landed after the scripted end had
  turned the HUD off. That race is fixed since: `fight()` reads the state again on that refusal.
- O1-LADDER: 5 runs x 4 keys. SC 0 -> 1000 once at 50 e17 t1 ip1804; `Byte[6] |= 1`; FieldEntrance 100, then 102.
- O1-NULL: 47 keys matched in every run of both sides. The only differences were `Byte[206]` values, the AI's random
  wait.
- O1-STABLE: 178 unstable keys, all registered noise.
- O1-JOIN: 596 rows, 0 failures.
- O1-THROW: none.

Each run took about 3.5 minutes.

The report-only dialogue line reads the fork runs as != the stock run, at 27-29 pages against 28. The two stock runs
differ from each other in the same place: 50's four self-closing "Whew..." windows stack, and the driver samples
them at varying moments. Every other page matches across the five runs. So the comparison needs self-closing windows
folded before it can read a fork difference.

The chain stays deployed (31200-31219) for the next segments.

**Next, O2:** Alexandria, where Vivi's segment starts in field 100. That means the alxt zone joins the chain, and the
driver gains that segment's naming screen, its walks and its talks.

## O2 -- Alexandria under the trace: Vivi's segment (PROVEN: story-o2, v1 081d774e)

**The question.** Over Alexandria's first story segment, does a verbatim fork of the alxt zone write the real game's
story state key for key? The stock runs are also this segment's recorded ground truth. The design, with both of its
critiques folded in, is [`research/o2_design.md`](research/o2_design.md); the route it rests on is
[`research/o2_route.md`](research/o2_route.md) (two readers reconciled, a completeness critic's corrections applied).

**The segment.** A raw warp into 100 (Main Street) at entrance 102 with the scenario at 1000, then 100 -> 101 -> 102
-> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 -> `Field(61)` (116 e2 t1 ip1702). SC climbs 1000 -> 1150 -> 1151 ->
1152 -> 1153 -> 1154 -> 1155. The segment ends on arrival in real field 61, on both sides.

**The sides.** S = stock. F = `import-chain 100 --verbatim --ids 100-117 --fresh-ids --id-base 31220 --name-prefix
O2`: 18 members, 31220-31237, sharing text block 33 ([`o2_forks.json`](o2_forks.json)). Built offline at
`C:\gd\_ns_playtest\o2\build`, NOT deployed. Field 61 is no member, so member(116)'s `Field(61)` stays real: the
seam, judged in donor terms.

**The entry.** Each run: New Game, the trace armed, then `warp 100 102 1000` (stock) or `warp 31220 102 1000` (fork).
It is not a replay of O1. The warp writes FieldEntrance and the scenario before the map changes: exactly three
residue rows in field 70 (bytes 0-2), which the front cut sets aside and O2-START requires. Only two gEventGlobal
values depend on that start: `UInt16[19] |= 2` and `Byte[6] |= 2` write 2 and 2 here, and would write 1799 and 3 after
O1. The report prints both under the claim's scope: gEventGlobal values only, not party data, cards or field 70's
override state.

**The driver** (`segment_drive.drive`, research/o2_design.md 2). A beat table of cells keyed by (donor place,
published SC). Each cell is a list of steps (cross, trigger, confirm, wait_sc, leave_now), counted per field visit
and done only on its own evidence. Six choices, every one taken at the game's own default cursor (option 0), and the
naming screen. The climb holds Up in bursts. At the 105 lookout the exit is taken at once (a lunge, then the
crossing), because Alleyway Jack's contact comes about 1.5-2.0 s after control. Anything the table cannot answer is
a VOID with its class (V1-V14), attributed to the driver or the game. The driver keeps `press`, `watch`, `step` and
`visit` rows. A forbidden write (Jack's contact, the Confirm hot-spots, Kupo, 104's info options, a write off the
route) VOIDs the run only when that evidence backs it; otherwise it is a finding.

**The checks** ([`o2_alexandria.py`](o2_alexandria.py); research/o2_design.md 5 and 6):
- offline: O2-BUILD, O2-TEXT, O2-KEYS, O2-REGIONS, O2-GOALS;
- preflight: P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT, P-RECOVERY; in game P-CAP, P-OBJECTS, P-LANG;
- the session: O2-FROZEN, O2-COVER; O2-FORBIDDEN and O2-VOID-ASYM over every run, covered or not; then START,
  LADDER, CHAIN, RESIDUE, WRITES, NULL, STABLE, SEAM, MASKED, STATE and JOIN over the covered runs; THROW.

**The uk text: a KNOWN-KIT-DEFECT, now cleared by a rebuild.** The first build shipped `uk/field/33.mes` as the stock
US text: `dialogue._lang_score` gives us and uk one English stopword set (dialogue.py:374 on this branch), so the kit's
text carry handed uk the us pick. O2-TEXT and P-TEXT compare each language with the asset the engine itself reads (its
ResourceManager path, `embeddedasset/text/<lang>/field/33.mes`), never with `extract_field_mes`. A mismatch in the
session language (us) is a hard FAIL. A copy of another language's stock asset is a named, counted KNOWN-KIT-DEFECT
line, and anything else is a FAIL. On the first build: 6 languages byte-equal, KNOWN-KIT-DEFECT 1 (uk shipped stock us
`4751874951`; stock uk is `8c94536b6c`), FAIL 0. The kit fix (each language picked by its resource path) is on master
since `aa627d52`, and the O2 fork's text sidecars were repaired with `tools/refresh_verbatim_text.py` (`ac9a3d69`;
each keeps a `.pre-refresh-20260930-104516` copy). This branch carries neither: only the sidecars matter to a build.
The chain was then rebuilt from the repaired sidecars (`build-all` from master `ac9a3d69`; the old build is kept at
`C:\gd\_ns_playtest\o2\build.pre-ukfix-20260930`), and O2-TEXT reads 7 byte-equal of 7, KNOWN-KIT-DEFECT 0, with no
code change here -- the rule's promised outcome. The uk text is no longer a precondition of the deploy.

**Status: ★★ PROVEN (session `story-o2`, v1 `081d774e`).** Alexandria's segment under the trace: the warp into 100 at
SC 1000 -> 101 -> 102 -> 103 -> 104 -> 103 -> 105 -> 106 -> 115 -> 116 -> Field(61), and the verbatim fork chain
(31220-31237, deployed into FF9CustomMap) writes the real game's story state key for key. S F S F S F, 6/6 covered
(S 3 of 3, F 3 of 3), unattended, 2100 s; every check PASS: FROZEN, COVER, FORBIDDEN (0 hits), VOID-ASYM (none),
START, LADDER (6 runs x 6), CHAIN (6 x 12), RESIDUE, WRITES (6 x 26), NULL (94 keys matched, 0 stock-only, 0
fork-only, noise set aside 0), STABLE (0 unstable), SEAM (every fork run leaves only at member(116) -> 61), MASKED,
STATE (19 targets' write histories identical in order, the end state as frozen), JOIN (738 rows, 0 failures), and
THROW (none). Every run took all eight beats. Hippaul's registered noise never fired, so the noise set aside is
empty: the verdict needs no exemption. One CENSUS GAP, the same on both sides (100 e19 +417 `Byte[303]` B_POST_PLUS,
a store the census does not count), reported, not judged. Archive:
`C:\gd\Dream-World-IX\.harness-runs\20260930-192740-story-o2` (o2_report.txt).

The stock rehearsals that set up the freeze ran unattended through the harness, one launch a stage, 16 runs, every run
reaching its stage's end field (archived under `C:\gd\Dream-World-IX\.harness-runs\20260930-18*-o2-rh-*`):

| Stage | Runs | What it showed |
|---|---|---|
| R-115 | 3/3 | F1: `hold up` climbs -- the published y RISES 0 -> 2691 in 9 bursts, then holds 3 at the top before 116 |
| R-106 | 2/2 | F3: SC 1153 arrives at the wait point (560,1991); e14 lost -> id flip 54 frames |
| R-105 | 5/5 | F2: Jack never within his range_r 299 (min 2086); first move 4-6 frames after the grant; 305/310/314 matched |
| R-116 | 2/2 | three triggers; naming (Byte[6]=2); Puck min 185; F8: end_run from 61 reaches the title |
| R-115a | 2/2 | the 115 scene, choice 367, the real stage-10 grant (50,-968); run 2 held 4 bursts at the ladder's top |
| R-FULL | 2/2 | 337 s / 358 s. Ladder 6/6, chain 12/12, writes 26/26, start-dependent 2/2, 0 forbidden, 0 join failures; the two runs key for key identical (50 unregistered keys each); F9 start residue exact; F11 end state = the draft's; Hippaul's ip254 absent both times |

What the rehearsals corrected (commits `9df45bda` and the freeze commit): the FakeGame's ladder ran the wrong way
("smaller is higher"; the climb verb is sign-blind, so its tests passed on a ladder the game does not have) and the
draft's climb `top: -2431` could never fire -- both fixed; `stall_bursts` 3 -> 8 (R-115a run 2 held 4 bursts at the
top: 3 would have VOIDED it); the (105, 1152) start is the measured grant (-598, 1608), not the lookout; 116's third
step starts at (-716, 2307), where the trigger above it ends; F7 budgets from R-FULL (`run_s` 716, `run_min_s` 434,
`session_s` 4580, `no_progress_s` 120, `exit_wait_s` 5). One surprise kept as designed: in 100, control drops once at
(65, 3489) every run (the Rat Kid scene; the design had placed the bump near z 6200) and the step's one `interrupts`
absorbs it.

- `o2_alexandria.py --offline-check`: 5 PASS on the frozen v1 (126 files own-language; 48 key sites; 26 regions, 17
  hot-spots and all 21 gateways of the route fields registered; 14 goals, every step runnable and every crossing where
  the route's order goes next); O2-TEXT 7 byte-equal of 7 on the rebuilt chain (the uk KNOWN-KIT-DEFECT line it
  printed on the first build is gone).
- `--preflight`: red, as expected: P-MANIFEST, P-DEPLOY, P-EB and P-FLOOR fail (nothing deployed); P-STOCK, P-TEXT
  ("no mod folder ships block 33") and P-RECOVERY pass.
- [`o2_dryrun.py`](o2_dryrun.py): 86/86 as registered -- the design's section 8 (44 session cases, 4 unit cases),
  plus 4 cases and 2 unit cases added where mutating a check's clause showed no case that isolated it, plus the
  review's: 27 one-change mutants of the draft that O2-KEYS, O2-REGIONS and O2-GOALS must each FAIL by the clause they
  break, O2-TEXT's missing language, P-RECOVERY, and O2-STATE's history and suppressed stores.
- The O1 regression gate (`segment_regress.py`): 7/7.
- A review of PARTS A-C found eight defects; each is fixed with a test that fails on the code before it
  (research/o2_design.md 11.6). The weightiest: a walk into the WRONG door is now the driver's V11 -- one landing
  judge every executor shares, and rule 2 holds each new visit to the route's order (`visits`) -- where it had read as
  the game's (a finding, not a VOID); and a wait begun short of its point is the driver's V7, never the game's V8.

**Done, in order:** the stock rehearsals (above), the fold-in, `--freeze` (v1), the chain rebuilt with the uk kit fix,
the owner-approved deploy of the 18 members (main checkout, master `ac9a3d69`; [`o2_forks.json`](o2_forks.json)),
`--preflight` 7/7, and the session (`py tools/play.py studies/story-trace/o2_alexandria.py --label story-o2
--timeout 240`): PROVEN. The chain stays deployed; its reverts run newest first (`o2_forks.json` revert).

What only the game can settle is the design's section 10: the climb, Jack's timing, the exits' map-switch latency,
mbg101's frame-rate change, Kupo near the ladder, 116's narrow walks, the facing for the two tag-3 Confirms, and 61's
FMV under end_run's warp.

## O3 -- the play under the trace, a US session: 61 -> 62 -> battle 338 -> 63 -> real 64 (PROVEN: story-o3, v1 1bcf11a9)

**The question.** Over the play's Act I -- the narrator and the curtain, the fight with King Leo, and the battle's own
return to the stage -- does the verbatim tshp chain O1 deployed write the real game's story state key for key, through
a battle that hands the run to ANOTHER field? That hand-over is the s24 battle-return redirect, in-game proven once
(June) and never under the trace. The stock runs are also this segment's recorded ground truth. The design, with its
two critique rounds folded in, is [`research/o3_design.md`](research/o3_design.md); the route it rests on is
[`research/o3_route.md`](research/o3_route.md) and [`research/o3_research.json`](research/o3_research.json).

**The segment.** A raw warp into 61 (entrance 0, SC 1155), then:
- 61: FMV003, the narrator's pages 72-78, the curtain, `Field(62)`;
- 62: Act I, the play's party rebuilt, `Int16[2] := 0`, then `Battle(0,338)`;
- battle 338 (King Leo, `BSC_TH_E002`): it ends by script once he has taken 186 damage (result 2: WinPose off), and
  its own `RunBattleCode(37,63)` loads 63 FRESH -- 62 is never resumed;
- 63: the scene on the stage, then `Field(64)` (63 e4 t1 ip828).

It ends on arrival in REAL 64 on both sides, cut at 64's first row (e0 t0 ip22). SC holds 1155 throughout: there is no
ladder, and O3-NO-SC requires that no row touch its bytes.

**The sides.** S = stock. F = O1's whole-zone tshp chain as deployed (31200-31219, FF9CustomMap;
[`o3_forks.json`](o3_forks.json)): 31211 (61) -> 31212 (62) -> battle -> 31213 (63), three members never run before.
31213's `Field(64)` is not retargeted: the seam. Nothing is imported, built or deployed for O3. Battle 338 bakes real
63; on F the engine's redirect (`ForkSiblingField(63)` = 31213) must land the run in member(63). Real 63 there is V16,
a finding the analysis reads as NOT PROVEN (VOID-ASYM, FORBIDDEN; LANDING (a) too if such a run were ever covered),
never as a VOID: a V16 run is uncovered, and LANDING reads only covered runs.

**A US session -- two scoped facts, never silent.** O1's chain is a legacy build:
- every member's jp/fr/gr/it/es `.eb` is US bytecode (O3-BUILD accepts the us build, as O1-BUILD did, and says "a US
  session's build" in its title);
- text block 2's uk copy is the US text: the KNOWN-KIT-DEFECT line "uk: ships stock us (3a6f3246c2; stock uk
  7ac9f17435)", which O3-TEXT, P-TEXT and the session report print, never a pass. Block 2 is global, so a UK game shows
  US text in stock 61-69 too; O4's alxc deploy rewrites it.

The claim is a US session's (P-LANG pins the session language). A PROVEN O3's milestone line will say so too.

**The entry.** Each run: New Game, the trace armed, then `warp 61 0 1155` (stock) or `warp 31211 0 1155` (fork), O2's
form. The warp writes the scenario's two bytes in field 70 (0 -> 131, 0 -> 4). The front cut sets them aside and
O3-START requires them. 61 must then take its ambient branch from the warp's `Byte[13]` 1 (ip119), never the error
path (ip97: the "Error Env Play()" window).

**The driver** (`segment_drive.drive`, research/o3_design.md 2): no beat table, since 61-63 never grant control and
control anywhere is V4. The battle beat (S4) is one registry row: 62, SC 1155, scene 338, won [1, 2], lands 63. Rule 1b
answers it on a new battle epoch, matched on the published scene and the visit's place, and the executor:
- fights it with `fight()` within the row's bounds (no result is V15, the driver's);
- leaves with `leave_battle(stop_on_field)`, each press a `press` row;
- waits for the landing in two tiers (late is recorded, never voided; V14 past the cap);
- judges it: 63 on S, member(63) on F, V16 for real 63 on F, V11 anywhere else.

61-63's error window is a stop page (V5, nothing pressed). A V16 holds its side's re-runs (S2), and the session ends
through `end_run` (S5): a run stopped in 61 mid-FMV003, where the soft reset is dead, warps out first.

**The checks** ([`o3_prima_vista.py`](o3_prima_vista.py); research/o3_design.md 5 and 6):
- offline: O3-BUILD, O3-TEXT, O3-KEYS, O3-REGIONS, O3-SCENE (battle 338's own scene: won by its WinPose flag, its
  next field, its one store, every unresolved store classified) and O3-CENSUS (every gEventGlobal store site of 61-63
  classified: writes, chain, masked, start_first, error path, forbidden, dead);
- preflight: P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR, P-STOCK, P-TEXT, P-RECOVERY, P-DONOR, P-SETTINGS, P-STOCK-BATTLE;
  in game P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG and P-LAUNCH (this launch read the files the preflight reads);
- the session: O3-FROZEN, O3-COVER; O3-FORBIDDEN and O3-VOID-ASYM over every run, covered or not; then START, NO-SC,
  CHAIN, RESIDUE, WRITES (EXACT: the 24 writes and the 3-key chain, the battle's `Byte[206]` noise aside), NULL,
  STABLE, SEAM, LANDING (a)-(e), BATTLE (a)-(d), MASKED, STATE and JOIN over the covered runs; THROW.

**Status: ★★ PROVEN (session `story-o3`, v1 `1bcf11a9`), a US session.** The play's first act under the trace: the warp
into 61 at SC 1155, FMV003, 62, battle 338, the battle's own `RunBattleCode(37, 63)` into a FRESH 63, `Field(64)`; O1's
deployed tshp members 31211-31213 write the real game's story state key for key. S F S F S F, 6/6 covered (S 3 of 3,
F 3 of 3), unattended, 1432 s, nothing deployed for it; every check PASS: FROZEN, COVER, FORBIDDEN, VOID-ASYM (none),
START, NO-SC (SC 1155 throughout), CHAIN (6 x 3), RESIDUE, WRITES (exactly 27 keys a run), NULL (27 keys matched; the
only stock-only/fork-only keys are battle 338's random `Byte[206]` values, the registered noise), STABLE, SEAM,
LANDING (a)-(e) -- every fork run's battle landed in 31213, never real 63: the s24 battle-return redirect, measured
under the trace for the first time --, BATTLE (scene 338, result 2 in all 6), MASKED, STATE (the end state as frozen,
20 variables), JOIN (601 rows, 0 failures), THROW (none). Archive:
`C:\gd\Dream-World-IX\.harness-runs\20261001-095552-story-o3` (o3_report.txt).

The stock rehearsals before the freeze (archived `20261001-09*-o3-rh-*`; F1-F12 all met, the optional R-SKIP not run):
R-START 2/2 (FMV003 plays after the warp, ~90 s to page 72), F-SMOKE (31211-31213 load, objects = their stock twins),
R-62 2/2 (the battle beat; 63 fresh after 62 ip1285), R-FULL 2/2 (27 keys, the two runs identical, the end state as
drafted), R-BATTLE-VOID (a soft reset from BattleHUD reaches the title). F9 sized the battle row (timeout_s 124,
max_turns 30, land_s 10) and the budget (run_s 500, no_progress_s 271 for FMV003's 90 s).

The offline build, as it stood before the rehearsals (branch `claude/story-trace-o3`, PARTs A-C of the design's
section 9):
- `o3_prima_vista.py --offline-check`: 6 PASS on the draft. O3-BUILD 140 files (15 own-language, 105 us-build);
  O3-TEXT KNOWN-KIT-DEFECT 1, FAIL 0, 6 byte-equal of 7, the uk line printed; O3-KEYS 53 sites; O3-REGIONS 0
  regions, 0 hot-spots, 0 gateways; O3-SCENE 338 as designed (flags 0x1839, won exactly [1, 2], RunBattleCode(37, 63),
  one store at e1 t1 ip267, 24 unresolved stores all `B_SYSLIST[0]`, >= 186 damage); O3-CENSUS 61: 15, 62: 28,
  63: 15 store sites, all classified.
- `--preflight` on the live install: 10/10 PASS (O1's chain deployed; P-DONOR 61 -> 31211, 62 -> 31212, 63 -> 31213;
  P-SETTINGS 23 keys as frozen; P-STOCK-BATTLE: the stack overrides only the LEDGER scenes, no selector names 338, and
  its four DictionaryPatch BattleScene lines are the LEDGER scenes', none on 338 or TH_E002).
- [`o3_dryrun.py`](o3_dryrun.py): 92/92 as registered -- section 8's cases and units with an EXACT `case()` (every
  check a case does not name must PASS), two cases added where the design's table could not hold (research/o3_design.md
  11.6) and three by the review (11.7: BATTLE (c) on each side, A-NOEND).
- [`o3_rehearse.py`](o3_rehearse.py): R-START, F-SMOKE (untraced), R-62, R-FULL, R-SKIP and R-BATTLE-VOID, chosen by
  `O3_STAGE`; its plumbing is proven on the fake.
- The regression gate (`segment_regress.py`): G1-G14, O1's and O2's outputs byte-identical, O3's driver tests (G13)
  and O3's dry run (G14) green.
- A code review's twelve findings (research/o3_design.md 11.7), each fixed with a test that fails without it: a
  reached run with no row in 64 is A-NOEND (driver), and rule 1 waits for that row (`budget.end_row_s`); P-STOCK-BATTLE
  reads DictionaryPatch's `BattleScene` lines; `fight()` tells a vanished battle ("gone") from a timeout;
  `leave_battle` honours its timeout; `end_run` waits out a battle exit's load; the rehearsal records each run's own
  fight; the ini reader's `;;` is the engine's.

**Done, in order:** the rehearsals in 7.1's order, the freeze checklist F1-F12, `--freeze` (v1), `--preflight` 10/10
with P-LAUNCH and P-DONOR-LOG on the session's own launch, and the session: PROVEN.

**Next, O4:** from the arrival in real 64 (A. Castle/Public Seats, alxc) by a raw warp into member(64) at entrance 100
with SC 1155, so O1's 31213 never needs re-linking; the alxc disc-1 cluster forked in a fresh band; the first end at
150 -> `Field(153)`, SC 1190 (research/o3_route.md, candidates 2-3). It carries the Chanbara minigame (random prompts)
and the encore choice 124.

What only the game can settle is the design's section 10: FMV003 right after the warp cut FMV001, the s24 redirect
under the trace, King Leo's latch, the soft reset from inside a battle, the published scene and result, the leave after
a scripted end, the F side's landing time, the watchdog against FMV003, and the members' first load.

## Rungs

| Rung | What | Pass |
|---|---|---|
| **0** | Hook + sink on a STOCK field (Lindblum 552, entrance pinned) | Every `eb` row lands on a store instruction in the stock `.eb` at (sid, tag, offset); Main_Init's writes for that entrance appear in the script's order; an unarmed run writes no file |
| 1 | Residue and epochs | A harness poke, a debug-menu flag write and the world-map `SC += 10` appear as `harness` / `residue` rows; a script-only walk gives zero residue; New Game, load and clear each give exactly one epoch |
| 2 | **The null pair** (the real falsifier) | Stock 552 vs its own verbatim fork, N = 3: STOCK ONLY is empty |
| 3 | Retrodiction | The Dali chain vs stock Dali on the real story route: field 450 / bit 2102 comes out of the report with no script reading |
| **4** | fork-report's story-writes axis | `fork-report` shows the traced set difference -- ★ DONE (offline, session 3) |

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
