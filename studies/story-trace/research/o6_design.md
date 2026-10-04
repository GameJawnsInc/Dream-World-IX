# O6 -- Steiner's naming, the Knights of Pluto and his first door under the trace: the design

**Status: DESIGN, offline.** Nothing is imported, built, deployed, launched or frozen. The inputs are `o6_route.md` and
`o6_research.json` in this folder (the reconciled route, the walks, the start, the harness gaps, the fork gates) with the
critic's ten problems (`critique.problems`) overriding the map where they conflict, and the ten decisions the lead made
on top of both (0.1). This file folds them into code-level decisions in `o5_design.md`'s structure and keeps what O2-O5
learned. Every number below was read, read-only, from the stock US `.eb` files (through the kit at this branch's head,
c954f986 + the research commit), the research's scratch listings (`<scratchpad>/o6_research/reconcile/L{151,153,154}.txt`,
`stages151.out`, `stages153_328.out`, `mes_151.json`, `route153.out`, `goals153.out`), the live install (mod folders,
`Memoria.ini`), the archives of story-o1e, -o2, -o3, -o4 and -o5, and the live Memoria source (`C:\gd\FFIX\Memoria`, =
the deployed DLL, sha256 `ba976242...`); 0.2 says how. The offline check (section 6) re-derives every one of them.

**Rev. 2** folds in the second round's two critiques -- driver robustness (five) and claim integrity (ten). Each was
re-checked in the bytes, the stock walkmesh (the driver critic's FakeGame walk re-run here on stock 153), the engine
source or the harness; none was disproved and every one is adopted, one through the critic's second option (11.5 #4:
`after.old` is labelled as read, not re-derived from the archives). The big moves: the door walk is described as the
PRESSED path, two pad holds with the first into the corridor mouth's west corner (0.2 #7), and F15 is restated as the
stop's own firing condition; the walk-out is held a radius short of the floor's end (z ~2065) and the fade is 25 ticks,
not 26 (0.2 #6); a wrong landing after the door's evidence held is rule 2's verdict, the GAME's, never the walk's (S14
`left`); the page witness JUDGES the name -- a typed one is the driver's V13 and an instrument miss leaves the run
uncovered, never failing a check (S16, O6-NAMING); START-DEPENDENT classifies each deviation per run (FINDING /
EXPLAINED / START DRIFT); `end_run` accepts a naming screen BEFORE the ladder; the e15 float window and the evidence's
slack come from the bytes and the engine, never typed. 11.4 and 11.5 log every item; 11.2 (#2-#5, #10-#13) says where a
decision's letter is read by its intent.

**The segment** (decision 1): New Game, the trace armed, then in field 70 (after 70 e0 t0 ip130, before ip475) a raw
`warp 151 110 1190` (S) / `warp 31244 110 1190` (F). 151@110 (visit 1; EVT_ALEX1_AC_SEAT_R; Brahne the defined player,
no control): 17 pages, 5 KEYON pairs, the [TIME=20] windows 175/176, page 198, STEINER'S NAMING (`Menu(1,3)` e3 t1 ip603:
rule 4 + `accept_name`, the pre-filled default "Steiner" accepted, never typed), `Global.Byte[6] |= 8` (e3 t1 ip610),
`Field(153)` at 328 (e2 t1 ip932/ip940). 153@328 (visit 2; EVT_ALEX1_AC_H2F; the Knights of Pluto): 11 pages, the shared
script e15 (`Byte[8] := 125`, a Seq row), `Bit[3855]`/`Bit[3854]`, the party rebuild (`UInt16[21] := 8`, SetPartyReserve,
RemoveParty, PARTYADD(3)), `UInt16[19] |= 8`, STEINER'S FIRST CONTROL (e32 t1 ip2412) and ONE walk north on the ground to
the e23 door, which fires only at z > 1333 (`Int16[2] := 315` e23 t2 ip203, `Field(154)` ip211). It ENDS on arrival in
154 (EVT_ALEX1_AC_ENT_2F) -- real 154 on S, member(154) 31246 on F -- cut at 154's first row, e0 t0 ip26 (emitted: a new
site). SC 1190 throughout (no rung). No battle, FMV, choice or ATE.

What O6 newly puts under the trace: a NAMING whose result the trace cannot see (`PLAYER.Name` is save data, not
gEventGlobal) -- witnessed instead on the page that renders it (0.2 #8); the first SHARED-SCRIPT row since O1e (153 e15 t0
ip32, a Seq that entry 32 starts); the first START-DEPENDENT VALUES since O2 (8 here; 11 and 1807 after the O1-O5 routes
as driven); and the first walk whose evidence is a DOOR that hands the run to the next field -- a landing the driver must
accept whether `route_to` sees it before or after it returns (critique #1, decision 3), and a landing ELSEWHERE that is
rule 2's verdict, the game's: the evidence proves the door was e23's, whose only live `Field()` is ip211 (11.5 #1).

---

## 0. What this design decides, and what it found

### 0.1 Decided upstream (not relitigated)
1. **The segment** (the research's candidate 3): the run above; `visits` [151, 153]; the end on arrival in 154 with
   `side_ends` {S: [154], F: [31246]}; the cut at 154 e0 t0 ip26 (its first emitted row: verified, 0.2 #13); SC 1190
   throughout, O3's NO-SC shape. No rung, no battle, FMV, choice or ATE.
2. **The fork side:** O4's deployed members 31244 (151), 31245 (153), 31246 (154); nothing imported, built or deployed.
   `o6_forks.json` references O4's chain as `o5_forks.json` does (6.4).
3. **The walk's verdict** (critique #1, option (a)): an OPT-IN `to` on trigger steps -- `x_trigger` returns done when the
   loss sample satisfies `until` AND the landing is None or a field whose place is `to` (`rec.landed`, or the switch
   waited out); every other path unchanged (O1-O5 byte-identical). ExitField's walk-out is modelled in the FakeGame (he
   keeps moving until the flip; the flip may land before or after `route_to`'s settle returns) and BOTH landing paths and
   a wrong landing are tested. Built as S14 (1.2) with H16 (3.1).
4. **The naming:** rule 4 + `accept_name`; P-SETTINGS pins `DisableNameChoice` 0 (O4's settings already do: 4.15); an
   O6-NAMING check -- exactly one `named` row per run in 151 (after page 198, before the ip610 row) AND the first [STNR]
   page after it reads "Steiner" on both sides; `end_run`'s naming recovery (accept the screen, then RETRY the warp to
   the recovery field, logged `recover-warp-after-naming`; if `accept_name` itself fails, stop the session cleanly) with
   FakeGame tests that fail without it; an R-NAMING-VOID rehearsal. Built as S15 (1.2), S16 (1.2: the page witness,
   which JUDGES the name -- the driver enforces, O6-NAMING re-checks: 11.5 #2) and H16b/H17 (3.2, 3.3).
5. **Start-dependent:** TWO keys, the same on S and F -- 151 e3 t1 ip610 `Byte[6] |= 8` (8 here, 11 after a true O1-O5
   run) and 153 e32 t1 ip2206 `UInt16[19] |= 8` (8 here, 1807 after a true run; "a true run" read as the O1-O5 routes as
   driven, 11.2 #13) -- in O2's 4.5 shape, O2's `start_dependent` check and report PORTED into `o6_steiner.py` with an
   `after` key and wording scoped to O1-O5 (never O2's hard-coded "after O1": the span rendered from the predictions
   and checked against the class's `AFTER_RUN`, 11.5 #4); the old/same-only differences and the emitted pattern stated
   in the scope line (4.5, 5.3 O6-START-DEPENDENT -- each deviation classified per run, 11.5 #3 -- 5.4).
6. **The checks layer** (critique #2-#5, #7): a NEW O6-GOALS ((c') the planned route's first sample past z 1333 in e23 on
   an OPEN ground tri; (d') every other registered exit at 328 wholly outside the evidence, no open tri at z > 1200
   reachable off the ground; the dry-run mutants until z_gt 900, e25 dropped from avoid, a start on the upper corridor);
   O6-CENSUS with e15 LIVE at 328 (its only caller e32 t1 ip866) and the shared-entry proof kept for the others; PATTERN
   with the e15 row's position among e32 t1's rows UNORDERED (frozen from R-DOOR's measured gap; rev. 2: the window
   bounded by the bytes -- after e32 t0 ip727, before e32 t1 ip1656 -- the measured position report-only and refused
   outside it, 11.5 #6, 11.2 #10); R-WALK-VOID's stop as a z variant (`walk_stop_z` ~500) with R-DOOR confirming at
   least two holds before z 924 (read by its intent: in every R-DOOR run a walk hold is sent at published z in
   [`walk_stop_z`, 1333) -- F15, 11.2 #4); the per-language build claim from O5's C0 diff + P-EB's pins, re-run per
   language by O6-BUILD itself (6.1).
7. **O5's full preflight set** (6.2), all green before any rehearsal (it is today: 0.2 #15).
8. **Rehearsals** (the lead): R-DOOR x2 (stock, the WHOLE segment 151 -> 154: the only stage that defines predictions),
   R-NAMING-VOID, R-WALK-VOID (z stop), F-SMOKE (untraced: 31244@110, 31245@328, 31246@315 load as their twins), F-PASS
   (UNTRACED, before the freeze: one fork run through the whole route) (7.1).
9. **Built ON the shared machinery:** `O6Segment` in `o6_steiner.py`; every shared change keeps O1-O5 analysing
   byte-identically -- the gate extended to O5, its baseline captured FIRST (1.4); G21's pins extended by its own rules.
   Predictions frozen by the lead after the rehearsals (a draft function + `--freeze` refusing to overwrite). PLAN.md's
   O6 section carries the O7 HANDOFF (9 C4).
10. A parallel session may merge harness fixes into master meanwhile; the lead merges master before the merge (11.2 #7).

### 0.2 Found while designing (each verified offline, read-only)
1. **The start residue is THREE rows.** SC 1190 = 0x04A6 writes bytes 0 (0 -> 166) and 1 (0 -> 4); FieldEntrance 110 =
   0x006E writes byte 2 (0 -> 110) and leaves byte 3 at 0 (StoryTrace's Diff emits a byte that changed, :514-527): `[[0,
   0, 166], [1, 0, 4], [2, 0, 110]]` -- O2-O4's count, not O5's four. The warp window is O2-O5's (after 70 e0 t0 ip130
   `Byte[13] := 1`, before ip475 `:= 2`): 151's prologue takes ip119 (`Byte[13]` 1 -> 0), never ip97 or window 56.
2. **151's entrance dispatch is a COMPARE, not a switch.** 151 e0 t0 ip232 `SET({Global.Int16[2] const(110) B_EQ
   B_EXPR_END})`, ip240 `JMP_IFNOT(L340)`: at 110 it falls through (ip243 `Map.Byte[24] := 1`, InitObject 3, 4, 5, 17,
   12, `ip343 JMP(L432)`); every other entrance jumps to L340 (InitObject 3, 12, 6, 7, InitRegion(8), ip410 `Byte[8] :=
   125`). `o4_castle.instanced_at` reads only a SWITCH / SWITCHEX on `Int16[2]` and RAISES on 151 ("Main_Init holds no
   SWITCH / SWITCHEX on Global.Int16[2]"): O5's census and region readers could not prove anything about 151. O6 adds
   its own `instanced_at6` (1.3: O4's walker plus the compare form, `Int16[2] const(N) B_EQ` + `JMP_IFNOT`/`JMP_IF`, the
   entrance deciding the branch) -- O4's and O5's functions are not edited. Read: 151 at 110 instances {object 3, 4, 5,
   12, 17; code 1, 2}; at any other entrance {object 3, 6, 7, 12; region 8; code 1, 2}. 153 at 328 (O4's walker, the
   SWITCHEX): {object 13, 14, 16, 17, 32; region 23, 24, 25; code 1, 2, 21}; 154 at 315: {object 5, 6, 7, 15; region 8,
   9, 10; code 1, 11}.
3. **The store census at the route's entrances** (`o3_prima_vista.store_sites`, 0 undecoded): stock 151 holds 21 global
   store sites, 153 holds 51, 154 holds 22. At 110 / 328 every one classifies (4.4-4.6): 151 -- writes 7, chain 1, masked
   2 (ip22 is `start_first`), error path 4, dead 5 (ip41, ip130, ip211, ip410 -- the default entrance's branch -- and
   **e3 t3 ip909** `Bit[3793] := 1`: Brahne's talk handler; e3 IS instanced at 110 -- she is the defined player, e3 t0
   ip171 `DefinePlayerCharacter()` -- so the function is not inert, but no control exists at 110 and a player cannot
   talk to herself), inert 2 (e8 t2 ip38/ip237: region 8, instanced only at L340); 153 -- writes 21, chain 1, masked 2,
   error path 4, forbidden 4 (e24 t2 ip183; e25 t2 ip195, ip222, ip421: what a walk into e24/e25 writes), dead 10 (e0 t0
   ip41, 130, 211, 243, 1188, 1260; e32 t1 ip1797, 1819, 1841 behind `const(0)` tests; ip2161 behind `PARTYCHK(5)`,
   false after the rebuild), inert 9 (e3 t1 ip1741, 2953, 3150, 3168, 3288; e18 t1 ip890, 1077; e28 t2 ip38, 227 -- e3,
   e18 and e28 are not instanced at 328). **e15 is LIVE:** its one store (ip32) is run by `RunSharedScript(15)` at e32
   t1 ip866, and e32 IS instanced at 328 (critique #3) -- the store is a `writes` key. Every other `RunSharedScript`
   site of 153 -- e3 t1 ip1021 (5), ip2481 (4), ip2939 (6), e7 t1 ip1101 (8), e9 t1 ip325 (10), e11 t1 ip282 (12), e18 t1
   ip887 (19) -- lies in an entry not instanced at 328, and none of entries 4, 5, 6, 8, 10, 12, 19 holds a store.
4. **The emitted pattern: 34 rows, no count.** Over this start (field 70's prologue values: Int16[9] 643, Byte[13] 1,
   Int16[11] -1, Byte[14] 0, Byte[8] 125, Bit[191] 0, Bit[184] 0; every other target New Game's 0), no site is stored
   twice before the cut, so the sink (StoryTrace.cs:374-401) emits every store and no `c` row arises: visit 1 (151) 10
   rows -- ip22 (same), ip49 (same), ip57 (643 -> -1), ip119 (1 -> 0), ip138 (same), ip200 (same), ip315 (125 -> 125,
   same), e3 t1 ip610 (0 -> 8), e2 t1 ip735 (125 -> 0), ip932 (110 -> 328); visit 2 (153) 24 rows -- the six prologue
   rows (all same-value, all EMITTED: new sites in fld 153 / 31245), e32 t0 ip718 and ip727 (0 -> 1), e15 t0 ip32 (0 ->
   125), e32 t1 ip971 (same), ip1006 (0 -> 1), ip1041 (1 -> 0), ip1076 (0 -> 1), ip1597 (1 -> 0), ip1632 (0 -> 1), ip1656
   (0 -> 8), ip1741 (same), ip1775 (0 -> 1), ip2172 (same), ip2206 (0 -> 8), ip2232 (same), ip2240 (same), ip2248 (0 ->
   1), e23 t2 ip203 (328 -> 315). 4 masked rows (151's and 153's ip22/ip49), 28 writes + 2 chain = **30 keys** a run.
   Then 154 e0 t0 ip26, the cut. The research's count (34) holds.
5. **Every key's function offset**, joined on the stock US bytes (`ScriptIndex.function_at`; the `off` column of 4.3-4.6):
   151 e0 t0 ip22/49/57/119/138/200/315 -> 16/43/51/113/132/194/309; e3 t1 ip610 -> 426; e2 t1 ip735/932 -> 724/921;
   153 e0 t0 the same six -> the same six; e32 t0 ip718/727 -> 700/709; **e15 t0 ip32 -> 26** (entry 15's tag 0); e32 t1
   ip971/1006/1041/1076/1597/1632/1656/1741/1775/2172/2206/2232/2240/2248 -> 234/269/304/339/860/895/919/1004/1038/1435/
   1469/1495/1503/1511; e23 t2 ip203 -> 173; 154 e0 t0 ip26 -> 16.
6. **ExitField's walk-out is long, the floor ends before it does, and pathing holds him a radius short of it**
   (critique #1, measured; rev. 2: the driver critic's #2 and the claim critic's #7, each re-read in the source and the
   bytes). e23 t2: ip58 `CalculateExitPosition()` (MJPOS, DoEventCode.cs:2247-2275) projects his position onto the
   region's FIRST edge, q[0] -> q[1] = (-227, 3000) -> (200, 3000), clamped to it: the exit point is (his x at the loss,
   3000), ~1665 u north. ip59 `ExitField()` (MOVQ, DoEventCode.cs:860-869) calls `Obj.movQData` on the player --
   CLRDIST, MOVJ (walk to the exit point), return (Obj.cs:60-67) -- and sets `usercontrol` 0; MOVJ moves him
   `actor.speed` a tick (`curPos += moveVec`, EventEngine.MoveToward.cs:15-30, :166), re-run each tick (`stay()`) until
   it arrives or -- with `actMove` set -- its distance stops shrinking (:222-235); held at the floor's end he stands
   still either way. **His speed is the gait of his LAST CONTROLLED FRAME**: HonoUpdate rewrites
   `originalActor.speed = isRunning ? 60 : 30` on every frame he has control (FieldMapActorController.cs:210-211), so
   it is 60 because the walk RUNS -- not e32 t1 ip1160's `SetWalkSpeed(60)`, which the first controlled frame
   overwrote (the first design's "never reset" was wrong; the number survives, the reason does not). **Pathing is on**
   (e32 t0 ip548 `SetPathing(1)`: `charFlags & 1`, DoEventCode.cs:2618-2628), so every tick ServiceChar's walkmesh
   traversal and radius forces (FieldMapActorController.cs:360-361, :950-1027; RadiusValid :1060, ServiceForces
   :1161) keep his centre a radius -- 120 (0.2 #19) -- inside the open floor. On his line the open ground ends between
   z 2150 and 2200 (stock 153, the 33 closed: open ground x [-910, 895] at z 2150, none at z 2200), so he stops at
   **z ~2065, ~12 ticks after a fire near z 1340**, and stands there for the rest of the **25 ticks** to `Field(154)`:
   ip95 `op_22(1)` is SKIPPED -- ip68 tests `Map.Bit[159] == 1`, which Main_Init's tail sets unconditionally (153 e0
   t0 ip2356), and ip80 tests `Map.Bit[144] == 0`, which 153 never writes (all 26 of its references are `B_EQ` tests),
   so the path runs ip79 `DisableMove()`, ip91 `DisableMenu()`, ip92 `JMP(L68)` to ip98 -- and only ip153's
   `op_22(25)` waits before ip203 `Int16[2] := 315` and ip211 `Field(154)` (one tick, no wait between; e24 and e25 are
   the same shape: 25 ticks too). `route_to`'s smooth walk `settle()`s after every hold until two samples within 0.5 u
   span two ticks (session.py:1785-1849): with him held still ~13 ticks before the switch, it most likely returns
   BEFORE it (`landed` None: PATH A); if the radius forces leave him jittering, or the reads straddle the switch, it
   returns after it (`landed` the next field, `changed_to` set: PATH B). TODAY's `x_trigger` is done only on `landed in
   (None, fid)` (segment_drive.py:2485) and reads path B as the driver's V11 (`left_for` -> `strayed`, :2486-2488).
   The critic's 12-in-36 on O2's doors does not transfer: here the exit edge lies beyond the floor, and which path a run
   takes is the engine's. S14 accepts both paths; rule 1 records the walk-out and the flip in both (S14b: in path A
   `route_to` has returned ~12 ticks before the switch, so neither its record nor O5's walk tap holds the flip); R-DOOR
   records which path each run took (F2). The FakeGame's door today stops him dead (`_enter_regions` sets `_coast` None,
   fakegame.py:1663-1690): H16/H18 model the walk-out (H18's builder default `stop_z` 2065, an ESTIMATE R-DOOR
   measures).
7. **The pressed path is not the planned line: TWO walk holds, likely, the first into the corridor mouth's west
   corner** (critique #4; rev. 2: the driver critic's #1, re-run here -- the first design's "one straight leg, one
   hold, R-WALK-VOID's z stop may never fire" described the PLANNER's line and was wrong). The smooth walk presses PADS:
   `_plan_hold` (session.py:3073-3179) takes one of the two pad directions either side of the bearing (`_eight_way`,
   :8534) and the longest press whose end stays within the leg's DRIFT -- `_leg_chunk / 2`, half the remaining leg's
   clearance from the AVOID REGIONS AND BLOCKERS ONLY, never the walls (:2932-2944, :3142-3143), capped at
   `ROUTE_CHUNK_MAX` / 2 = 180 u -- less the heading spread (and `ROUTE_HOLD_TICKS` 22.5 ticks, :2672, which binds
   later). 153's one basis (248, 0) gives `key_move_basis(0)` up = (0.0245, 0.9997), 1.4 degrees east of +z; the leg
   bears 9.5 degrees east of +z, 8 east of up, so hold 1 is "up" (the nearer pad, the drift capping it at ~800-900 u
   where its end strays 180 u off the leg, less the heading spread), from the grant straight into the WEST CORNER of
   the corridor mouth: pressing up from (-245, 42) his clearance first falls under his radius 120 at (-224, 917), and
   the corridor's open ground is x [-175, 210] from z 1150 to 1800 -- his centre band [-55, 90]. Re-run here (the real
   Session against the FakeGame on
   stock 153's player walkmesh, the 33 closed, e23 as a region past z 1333, avoid e24/e25; the driver critic's
   `o6_critic_sim.py`): at clearance 120 (Steiner) the calibration's four probes (none past z ~192), then `hold up 32`
   from (-245, 42) ended at (-179, 941) -- the fake's clearance pushed him 44 u east of his pressed line -- then `hold up
   16` from (-179, 941), the loss at (-50.4, 1339.8); at the fake's usual 80, three holds, the second sent at (-192,
   989), the third at (-92, 1288), the loss at (-90.8, 1348.4); from (-220, 67) at 120, hold 2 sent at (-113, 1019), the
   loss at (-49.7, 1360.2). So: (a) every run meets that corner, on hold 1 or 2: in the engine RadiusValid /
   ServiceForces (FieldMapActorController.cs:1060-1245) slide or stop him there, which nothing has measured -- a stop
   leaves him off the leg and the drift rule sends hold 2 up+right, so there is no stall loop -- and R-DOOR records it
   as a go/no-go (F1, F12); (b) hold 2 is sent at published z ~940-1020, INSIDE e23's quad (its south edge z 924-935)
   in its NON-firing band, control held: R-WALK-VOID's z stop (`walk_stop_z` 500) FIRES there, mid-walk, as decision 6
   intends -- the first design's F15 ("two walk holds before the first sample at z >= 924") would have counted ONE and
   chosen the fallback for a stop that does fire, so F15 is restated as the stop's own firing condition and
   `walk_stop_z` is taken from R-DOOR's measured hold-2 starts (11.2 #4); the FALLBACK overlay `walk_stop_hold` (the
   first walk hold after the calibration -- the field's basis cached in `g._axes` -- raises before it is sent) stays
   for a launch where no walk hold is sent in [`walk_stop_z`, 1333); (c) the loss lands where the corner left him (x -50
   to -90 in the fake), not on the planned line's (-29, 1333): inside e23 either way, which is all the evidence needs
   (O6-GOALS (d'): no open floor past z 1200 lies off the ground).
8. **The name on the page.** `[STNR]` is a constant text replace tag (FFIXTextTag.cs:390) resolved to
   `FF9StateSystem.Common.FF9.GetPlayer(CharacterId.Steiner).Name` (DialogBoxSymbols.cs:67-68) when the window's parser
   first runs (TextParser.cs:62-70); the agent publishes `ParsedText` (HarnessAgent.cs:1708-1721: "what is actually
   drawn"), the WHOLE text -- the type-out is a per-vertex alpha (TextParser's `AppearProgress`), not a shorter string.
   (Rev. 2, the claim critic's #2 (ii), re-read:) `ParsedText` starts as the RAW text, tags included -- the TextParser
   constructor sets `ParsedText = InitialText` (TextParser.cs:54-60) until `Parse` runs -- and the agent falls back to
   `Phrase` only for an empty one, so an UNPARSED window would publish its tag. In practice none is published: the
   driver critic (checked and sound) and the source agree that `DialogManager.AttachDialog` calls `Dialog.Show` at once
   (DialogManager.cs:99-153) and `Show`'s `AutomaticSize` parses the constant replace tags before the window is first
   drawn (Dialog.cs:597-603, :1560-1575: `Parse(ConstantReplaceTags)`, or each page's `ProcessText`); the witness keeps
   only parsed windows all the same (S16: an unparsed sibling is never listed, never judged), and R-DOOR counts any
   unparsed sample (F3). So the first PARSED sample of a [STNR] window shows the name `PLAYER.Name` holds. Block 3
   (US): mes 199 `[WDTH=0,65,19,-1]Queen Brahne\n“Captain [STNR]!”[INCS][TIME=-1]` (e3 ip693, slot 0) and mes 200
   `[STNR]\n“Yes, Your Majesty!”[INCS][TIME=-1]` (e12 ip803, slot 4) open in stage 21 ONE AFTER THE OTHER (rev. 2, the
   claim critic's #2 (iv)): e3 t1's stage-21 block (ip679) opens 199 at ip693 after `op_22(1)`, e12 t1's (ip796) opens
   200 at ip803 after `op_22(7)` and `RunAnimation(1984)` -- ~6 ticks later (stages151.out) -- so the first parsed
   sample normally lists 199 ALONE. They are the first [STNR] windows after the naming (198, 177-197 hold none); 203,
   211-214, 217-219, 221 and 222 follow (153's pages); mes 124 (a soldier's talk at 328) is never opened by the route.
   The witness (S16) takes the first sample listing a parsed window a frozen entry names, JUDGES its lines against the
   frozen ones (a mismatch is the driver's V13: input at the naming screen) and logs the row; O6-NAMING (b) re-checks it
   (4.11).
9. **The values after the O1-O5 routes, re-derived from the archives** (not only the research's composition; rev. 2:
   the first design's "true-run values" overstated what the archives hold). story-o1e, all six runs,
   both sides: 50 e17 t1 ip3240 `Byte[6]` 0 -> 1; 50 e17 t1 ip1629/1667 and 50 e13 t1 ip1149/1187/1225 `UInt16[19]` 0 ->
   1 -> 5 -> 261 -> 773 -> 1797. story-o2 (a raw start): 116 e2 t1 ip765 `Byte[6]` 0 -> 2, 100 e19 t1 ip1531 `UInt16[19]`
   0 -> 2 -- after O1 they write 1 | 2 = 3 and 1797 | 2 = 1799. story-o3, -o4, -o5: no row on bytes 6, 19 or 20 in any
   trace (the claim critic re-read all five and agrees). So after the O1-O5 routes AS DRIVEN -- O2-O5 each from a raw
   start, composed with the bytes' `|=`: these are the routes' values, not a measured chained play (rev. 2, 11.5 #4) --
   151 ip610 writes 3 | 8 = **11** and 153 ip2206 writes 1799 | 8 = **1807**; 1799 is bits 0, 1, 2, 8, 9, 10 -- bit 3
   clear, so ip2180's guard `(UInt16[19] >> 3) & 1 == 0` takes the same branch. `after.old` (3, 1799) is READ here at
   design time and labelled so (`after.source`, 4.5); only `after.value` is computed.
10. **Old/same-only start differences** (value equal, `old` or `same` not): 151 ip57 (Int16[9] 643 -> -1 here; -1 -> -1
    after the O1-O5 routes), ip119 (Byte[13] 1 -> 0; 0 -> 0), ip315 (Byte[8] 125 -> 125, same, here; 0 -> 125, a change,
    after them: O5's last write is 153 e18 t1 ip890 `:= 0`); 153 e32 t1 ip1656 (UInt16[21] 0 -> 8; 1 -> 8: O4 wrote 1),
    ip1741 (Byte[303] 0 -> 0 same; 1 -> 0 a change: O4 left 1), ip2248 (Byte[18] 0 -> 1; 1 -> 1 same: O3 left 1). And the
    PATTERN: in a single-epoch chained O1-O6 run, 151's ip22 (O5's cut row), 153@328's prologue sites
    (O4/O5 emitted them) and 154's ip26 (O5 emitted it) would be suppressed `c` counts -- O6's start row, its visit-2
    prologue and its END ROW exist only because each run is a fresh epoch. Every frozen sequence, count and the cut are
    this start's (5.4).
11. **The e15 row and its race** (critique #5, measured on the bytes). e32 t1 stage 40: ip815 opens 212, ip866
    `RunSharedScript(15)`, ip870 `WaitWindow(4)`; the Seq (STARTSEQ, DoEventCode.cs:1414-1421; Obj.cs:47-58) runs entry
    15: ip6 `op_22(45)`, ip9 `RunSoundCode(0, 137)`, a `SYSVAR[3]` wait (ip15-29), **ip32 `Byte[8] := 125`**. e32 t1
    meanwhile: 212's Confirm, ip887-898 `op_22` 15 + 10 + 15, 213, 214, stage 41 (e16's Walk + 215), stage 42 (216),
    stage 43's ip960 (217 opens) and ip971: at least 40 ticks of scripted waits and five pages, against e15's 45 ticks and
    a sound sync. In order unless the sync stalls ~1.3 s -- floated in PATTERN (4.18). THE FLOAT'S WINDOW IS THE BYTES'
    (rev. 2, the claim critic's #6): the row cannot precede ip866, which e32 t1 reaches only after e32 t0 (Init) has run
    ip718/ip727; and between ip971 and ip1656 (the rebuild's first store) e32 t1 holds 24 `op_22` instructions summing
    351 ticks (each counted once: a lower bound), the stage-44/45 walks (~2900 u at 60 u a tick) and four more pages
    (218, 219, 221, 222) -- a sync stall long enough to carry the store past ip1656 is ~12 s or more. So PATTERN floats
    the row between e32 t0 ip727 and e32 t1 ip1656 (never anywhere up to ip203, as the first design had it), R-DOOR's
    measured position is report-only, and the freeze refuses one outside the window. The row reads sid 15, uid 96 (32 +
    cSeqOfs 64), tag 0, ip 32, add 0 (StoryTrace.cs:354-371); `uid` is compared nowhere (storytrace.py:227 checks a row's
    attribution only off an `eb` row; JOIN and WriteKey key sid/tag/ip/off): R-DOOR records it. The FakeGame writes uid
    = sid (fakegame.py `_story_store`): harmless for the same reason.
12. **The walk on the stock walkmesh** (`PlayerWalkmesh(stock 153, closed = O5's 33)`, the harness's own
    `route_avoiding(..., leave_wall=True)`): the grant (-245, 42) stands on ground tri 114 (PSX y -1) under upper tri 42
    (-1499, closed); the start's open component holds 118 tris (PSX y -1492..-1: the west stair's open tris included);
    the route is ONE leg to (19, 1620), 1600 u, the goal on tri 151, 195 u from a wall; sampled every 5 u, its first
    sample past z 1333 is (-29.0, 1333.1) on open ground tri 79 (PSX y -1), inside e23 (`doorface.region_contains`); at
    clearance 120 the planner gives (-53, 1130) -> (19, 1620), its first sample past z 1333 (-22.5, 1337.9), tri 54.
    The 14 open tris of the component with a vertex at z > 1200 are all ground (PSX y -1), and NO open tri anywhere on
    the mesh has a vertex at z > 1200 and one at PSX y <= -100. e24's quad lies at z -74..406 and e25's at z -2348..-900
    (the route passes 1897 u and 942 u off them). (-226, 1086) -- soldier e14's spot on the upper corridor -- has no open
    tri at all (only upper tri 24); (-24, -2078), Steiner's spawn on the corridor, has open GROUND tri 83 under it, so
    "a start on the upper corridor" is mutated with the former (8 GOALS). This is the PLANNER's line, what O6-GOALS (c')
    judges; the PRESSED path differs (0.2 #7, rev. 2): two pad holds, the first into the corridor mouth's west corner
    (the planned leg itself dips to 113 u off the walls at (-72..-59, 1078..1157)), the loss at x ~-50 to -90.
13. **The end row and the end state.** 154's first store at 315 is e0 t0 ip26 `Bit[191] := 0` (0 -> 0, same): a new site
    in the epoch, EMITTED -- the cut row on both sides (31246 on F: the member's own `fldMapNo`). The row before it is
    153 e23 t2 ip203. 154@315 takes ip234 `SWITCH(304, L392, L232)`'s default L392 and stores no `Byte[8]` there (ip279
    is the 304 branch's) nor anything but its same-value prologue: nothing races the live end-state read, so `Byte[8]`
    (125) is read live (4.10), unlike O5's.
14. **The route pins** (4.16): 65 instruction texts, each read off the stock US listing while designing and quoted
    exactly; `route_mes` (block 3, US) as quoted in #8 and 4.16; mes 56 `[IMME][D06050][HSHD]Error [C8B040][HSHD]Env
    Play()\n...` holds the stop page's "Env Play()".
15. **The premises hold at the branch head.** `o5_hallway.py --offline-check` (frozen v1): 6 PASS -- O5-BUILD "140
    files ... the route members' pins hold in 21 member files (3 route members x 7 languages): the only byte diffs are
    their 16 in-chain Field() operands" (O4's build is readable), O5-KEYS, O5-TEXT 7 of 7, O5-CENSUS, O5-REGIONS,
    O5-GOALS. `o5_hallway.py --preflight` on the live install: 12 of 12 PASS today (P-MANIFEST, P-DEPLOY, P-EB, P-FLOOR,
    P-STOCK, P-TEXT block 3 strict, P-RECOVERY 4600 in FF9CustomMap-world, P-DONOR 151 -> 31244 / 153 -> 31245 / 154 ->
    31246, P-SETTINGS incl. `DisableNameChoice` 0, P-PAD, P-OVERRIDE `2ce8887e`, P-ENGINE `ba976242`). The live
    Memoria.ini line 256 reads `DisableNameChoice = 0`. The story-noise mask covers only Bit[191] (boot_scratch) and
    Bit[184] (field_menu_guard) of O6's 18 targets.
16. **No fork gate on the route** (research `fork_gates`): the members differ from their donors only in `Field()`
    operands (O5's C0, per language, and O6-BUILD re-reads it: 6.1); `Menu(1,3)` and the party ops carry no field key;
    SETCAM #493 is wrapped and camera-only; s62's VIB ops are 325-only. PSXCameraAspect's raw RestrictedCams letterbox
    (153/154 camera 0) differs between S and F visually: never compare those screenshots.
17. **end_run on the naming screen, today** (segment_trace.py:537-587, critique #9; rev. 2: the driver critic's #4,
    re-timed in session.py): the warp is refused outside FieldHUD (`recover-warp-failed`); `restore_baseline`
    (session.py:8138-8176) runs `close_ui` -- six Cancels 12 frames apart, each only refocusing the name box (each
    starts NameSettingUI's 0.5-s `DelayFocusTextField`, NameSettingUI.cs:122-133), then a 20-s wait for FieldHUD that
    fails (:8075-8100) -- and the soft reset, swallowed outside FieldHUD/WorldHUD/BattleHUD (UIKeyTrigger.cs:94), which
    waits 45 s before it raises (:8034-8073): **~67 s** (not the first design's 25-30) before today's code reaches
    `accept_name` (`end-naming`) and `restore_baseline` again, now through 151's running scene with no warp (O1d: a soft
    reset through a running opening scene did not reach the title). Only that long gap keeps the last Cancel's delayed
    refocus from undoing `accept_name`'s first Confirm. If `accept_name` raises, `restore_baseline` raises "the title
    could not be restored", and every later run's `end_run` (segment_trace.py:654-657, at the start of `one()`) meets the
    same stuck game: the session is lost one run at a time. S15 accepts the screen FIRST -- on the refused warp, before
    any Cancel -- then retries the warp, then climbs the ladder, and stops the session cleanly when `accept_name` fails.
18. **The probe carries the field.** `route_to`'s loss probe keeps `{"frame", "field", "x", "z", "control"}` of the
    FIRST read with control gone (session.py:340-343, :816-818). A loss read only in the NEXT field (a read gap across
    the 25-tick fade) has `field` != the walk's: its x, z are the new field's, and judging `until` on them is meaningless
    -- under `to` it is the instrument's V13 (S14), never a V11 and never "interrupted" (which would leave a covered-looking
    run with no done step).
19. **Steiner at 328** (153 e32 t0 case 328, ip22 `SWITCH(324, ...)` -> L24): CreateObject(-24, -2078) on the upper
    corridor (PSX -1499), `SetObjectLogicalSize(30, 35, 50)` ip520 (controller radius 120 = 4 x 30, collRad 35), ip548
    `SetPathing(1)` (the walk-out's hold at the floor's end, 0.2 #6), ip717 `DefinePlayerCharacter()`, ip718 / ip727
    `Bit[3855]` / `Bit[3854] := 1` (every time e32 t0 runs: once in O6). Stage 40
    walks him to (-24, -74), stage 44 down the west stair, stage 45 to (-575, 807) then (-245, 42) (ip1360/ip1367); the
    knights' rendezvous does not move him (their flags carry bit 2: walk-through, WalkMesh.cs:915-917). Stage 48: 222, the
    rebuild, ip2382 `Map.Bit[158] := 1`, the gates ip2390 / ip2401, **ip2412 `EnableMove()`**. Nothing stores between
    ip2412 and the loss (e32 t1 idles after ip2428; the knights, soldiers and e21 store nothing): THE PAIRED-WALK LAW
    holds by construction.
20. **151 grants no control.** Brahne e3 is the defined player at 110 (e3 t0 ip171) and nothing sets `Map.Bit[158]` there
    (Main_Init's tail ip1010 tests it; e12 t0 ip149 `SWITCH(110, L159, L147)` skips Steiner's own grant): a control sample
    in 151 is V4 (game).
21. **The time a run takes** (an estimate, on O5's MEASURED rate: R-FULL 99-112 s for ~36 pages, 7 KEYON pairs, a choice,
    one walk and 474 ticks of scripted waits): O6 holds 28 pages, 5 KEYON pairs, 2 timed windows, the naming, one walk
    and 511 ticks of waits (151: 319; 153@328: 192) -- ~100-130 s. The draft's budget is generous; R-DOOR freezes it (F6).

---

## 1. Module layout

### 1.1 Files

| File (in `studies/story-trace/` unless a path is given) | | What it holds |
|---|---|---|
| `segment_regress.py` | edit, FIRST (A0) | The gate extended to O5: G0'''' (`--capture-o5`), G28-G31 (1.4); G21 over the UNION of the O3, O4 and O5 baselines' `sources`, `--rebaseline-source` over all three; `FAKE_PINS_O5`; `REQUIRED_TESTS_O6` empty; G32 joins at B3, G33 at C2. |
| `research/o5_regress_baseline.json` | new, FIRST (A0) | The captured O5 baseline (LF, `-text`), its `sources` included. |
| `segment_drive.py` | edit (A1, B3) | S14 (the landing-aware trigger: `step_of`'s `to`, `trigger_to_verdict`, `_Drive.x_trigger_to`, `run_step`'s `left` outcome and opt-in `misroute` key; `x_trigger`'s body untouched but for its first line's dispatch), S14b (rule 1 records a done `to` step's walk-out and flip) and S16 (the name on the page: `naming_of`, rule 4's `before`, `_Drive.page_witness`, which JUDGES the lines: V13 on a typed name). Each opt-in. |
| `segment_trace.py` | edit (A2) | S15: `end_run` accepts a naming screen on the refused warp, BEFORE the ladder, then retries the warp (`end_naming`; the session-stop marker when `accept_name` fails), and `run()`'s clean stop. Neutral for O3-O5 (no naming screen on their routes); an INTENDED change for O1 and O2, whose routes hold one (1.2 S15; recorded in 11.6). |
| `tools/harness/fakegame.py` | edit (A1, A2, B1) | H16 (a region's opt-in `walkout`; the test-held `exit_gate`), H16b (`reset_blocked_fields`), H17 (the visit's `naming` step, the [STNR] rendering, its faults; `unparsed_frames` per mes), H18 (the visit's `door` step, ExitField's walk-out, `exit_gate`), H19 (O6's faults). H16/H16b touch unpinned functions; H17/H18 edit `_visit_steps` and `_VisitBeat` methods (O5 pins: re-baselined by name with their reasons, G21, and proven unchanged in behaviour by the O5 replay, B0). |
| `ff9mapkit/tests/test_harness.py` | edit | The tests of 1.2, 3 and 9; the O6 route builder `_o6_route` (test-side, 3.6); the O5 replay `test_fake_door_keeps_the_hallway_route_identical` (A0b). No existing test body changes (G21). |
| `research/o5_fake_replay.json` | new (A0b) | The O5 replay's golden: the hand-stepped O5 route (S and F) on the UNEDITED fake (before H16 and every later fake edit) -- every change of its published sample and every trace row (LF, `-text`), captured twice and refused when the readings differ. |
| `o6_steiner.py` | new (C1) | `O6Segment(o5_hallway.O5Segment)` and its module functions (1.3). |
| `o6_forks.json` | new (C1) | The chain manifest: O4's, reused (6.4). |
| `o6_dryrun.py` | new (C2) | Synthetic sessions, units and offline mutants (section 8); `as_if_frozen(pred)` and `--as-if-frozen` (G33). |
| `o6_rehearse.py` | new (C3) | R-DOOR, R-NAMING-VOID, R-WALK-VOID, F-SMOKE, F-PASS for `tools/play.py` (section 7). |
| `.gitattributes` | edit | `studies/story-trace/research/o5_regress_baseline.json -text` (A0); `studies/story-trace/research/o5_fake_replay.json -text` (A0b); `studies/story-trace/o6_predictions*.json -text` (C1, before any freeze). |
| `PLAN.md` | edit (C4) | The O6 section: "draft: rehearsals pending, freeze pending", with the O7 handoff. |

NOT edited: `o1_*`, `o2_*`, `o3_*`, `o4_*`, `o5_hallway.py`, `o5_dryrun.py`, `o5_rehearse.py`, `tools/harness/session.py`,
`tools/harness/channel.py`, every frozen predictions file. `o5_hallway` (and through it `o4_castle`, `o3_prima_vista`,
`o2_alexandria`) is imported as shared code; its outputs are the gate (G22-G25 for O4's, G28-G31 for O5's). O6's census,
instancing, region and goal logic are its own functions in `o6_steiner.py` (0.2 #2), never edits to O4's or O5's.
`session.py` needs no change: `accept_name`, `route_to`'s handoff and the loss probe are used as they are.

### 1.2 The shared changes (each opt-in or behaviour-neutral for O1-O5 -- but S15, an INTENDED change for O1 and O2)

**S14 -- THE LANDING-AWARE TRIGGER** (`to` on a trigger step; decision 3; critique #1; built in A1). New code beside
O2's executor, never a refactor of it: `x_trigger`'s body is byte-identical but for one dispatch line at its head.

```python
def step_of(pred, raw):        # one refusal added, after the trigger's target/until rule
    ...
    if kind == "trigger" and out.get("to") is not None and not _is_int(out["to"]):
        raise ValueError(f"step {raw!r}: a trigger's to is a place, an int (a bool is no int)")

def trigger_to_verdict(lost, fid: int, ok: bool, landed, to_place, to: int) -> tuple:
    """S14's verdict, pure (research/o6_design.md 1.2): ``lost`` the walk's loss sample (route_to's probe, or the
    trigger wait's read) with its ``field``; ``fid`` the field the walk ran in; ``ok`` whether ``lost`` satisfies the
    step's evidence (``until``, or standing in its ``target``); ``landed`` the landing -- route_to's own record, or the
    switch waited out once the published id left -- None while he is still in ``fid``; ``to_place`` its frozen place.
    Returns ("done", landed) -- the evidence held where control went IN THIS FIELD, and the run either has not left yet
    or left for ``to`` (path A: None; path B: the next field); ("left", landed) -- the evidence held but the landing
    is ANOTHER place: by the step's soundness proof (O6-GOALS (d') and (e)) the loss was the door's own, whose only
    live ``Field()`` leads to ``to``, so the landing is its script's, the fork's or the engine's, never the walk's --
    rule 2's verdict for that field, the GAME's (rev. 2, 11.5 #1); ("v13", why) -- the loss was never read in this
    field (``lost`` None with a landing, or ``lost["field"]`` another field: a read gap across the door's fade -- the
    instrument's, the evidence unjudgeable); ("v11", why) -- the walk left the field from an in-field loss WITHOUT the
    evidence (today's ``strayed``): the driver's, the ONLY driver V11 under ``to``; ("judge", None) -- an in-field
    loss without the evidence and no landing: today's last lines decide (door_loss, interrupted)."""
```
`_Drive.x_trigger` gains one first line -- `if step.get("to") is not None: return self.x_trigger_to(step)` -- and is
otherwise unchanged. `x_trigger_to(step)`:
1. the walk, as today: `rec = g.route_to(*goal, zone=pts, avoid=..., tolerance=..., **self.walk_kw(step))` (`handoff`
   True, `smooth` True: unchanged); `out = {"route": trim_route(rec), "lost": rec["lost"], "landed": None}`;
2. no loss in the record, still here (`rec.landed in (None, fid)`, the published id `fid`) and control held: today's
   wait (`TRIGGER_WAIT_S` for control to go or the field to change; nothing within it -> "failed", as today); a read with
   control gone IN THIS FIELD becomes `lost` (`sample(st)` plus its `field`);
3. the landing: `landed = self.left_for(rec, out, "the trigger's door", wait)` -- `rec.landed`, else the switch waited out
   (`exit_wait_s`) when the published id has left `fid`, else None; `to_place = place(landed, self.members)`;
4. `trigger_to_verdict(...)`: "done" -> `out["landed"] = landed`, and on a landing from `rec.landed` the FLIP FRAME read
   off the ring (the first sample after `lost.frame` whose field is not `fid`: `out["flip_frame"]`; the switch path sets
   it itself, :2343); **"left"** -> `out["misroute"] = {"fld": landed, "place": to_place}`, `out["why"]` ("the door's
   evidence held at (x, z) in <fid> and the run landed in <fld> (place <p>), not <to>: rule 2's"), `landed` LEFT None
   and no `v`, returned as the outcome "left"; "v13" -> `out.update(v="V13", by="driver", why=...)`, "void"; "v11" ->
   `self.strayed(step, out, landed, ...)` (V11, driver, `door` the registered exit his loss stood in); "judge" (an
   in-field loss WITHOUT the evidence) -> today's last lines (:2507-2515: `door_loss` -- a registered exit within
   `exit_slack` of the loss: its switch waited out, V11 on a landing, else "interrupted" -- or "interrupted" outright).
`run_step` gains three lines, all inert for O1-O5 (no executor of theirs returns "left", sets `misroute` or runs a step
carrying `to`): an `elif verdict == "left": pass` beside done/failed/interrupted -- no beat, no raise, `walked` None (the
verdict is no unfinished walk); `if rec.get("misroute") is not None: row["misroute"] = rec["misroute"]` (the row keeps
today's keys otherwise); and, on "done" for a step carrying `to`, `self.to_row = row` (S14b's handle). The loop's NEXT
POLL meets the landing in rule 2 and gives exactly rule 2's verdict for that field:
**V19 (game)** on F for a real field a member forks, else `stray()` with no unfinished walk -- **V11 (game)** at rule 2's
cell `[place(landing), sc, the visit just left]` (segment_drive.py:2183-2185, :3036-3040). The landing sits under
`misroute`, a key the `walk` backing never reads (it backs only a step row with `v` "V11" and `landed` the hit's `fld`,
:804-807, never checking `by`), so the landing's rows stay UNBACKED: FORBIDDEN reads them as the fork's. On path A
(`route_to` returned before the switch) the same landing reaches rule 2 after a "done" step -- `walked` None (:2683) --
and gets the same verdict: the class no longer flips with the engine's timing (the claim critic's (c)). The first
design's V11-by-the-driver here is withdrawn: it backed the fork's post-landing rows (A-FORBIDDEN), let a one-sided
misroute be re-run away under VOID-ASYM (b), and demoted a stop_on V19 (a landing in a real 150 on F) to a re-runnable
VOID.
The step row (`run_step`) carries `lost` (with its field), `landed`, `flip_frame`, `misroute` when set and the trimmed
`route` (`landed`, `changed_to`, `handoff`): which path a run took is read off them (R-DOOR F2, the report).

**S14b -- THE WALK-OUT ON RECORD** (rev. 2, the driver critic's #5; built in A1 with S14). In path A `route_to` returns
~12 ticks before the map switch: the step row's `flip_frame` is None and O5's walk tap stops sampling when `route_to`
returns, so neither holds the flip F2 asks for. `run_step` keeps the last DONE step row whose step carries `to` as
`self.to_row`; rule 1 (the end), on its first poll in the end field, reads `ring_since(g, lost.frame)` and updates that
row IN PLACE (as `stray()` updates a walked row): `walkout` -- `[frame, x, z, control]` of every ring sample after
`lost.frame` still in the step's field -- `flip_frame` when None (the first ring sample after `lost.frame` whose field is
not the step's: `flip_late` True), and `landed_frame` (the first ring sample in the end field). Both paths then carry
the loss -> flip -> landing frames and the walk-out's samples (where he stopped: the estimate z ~2065, 0.2 #6); the
ring holds 300 samples against the fade's 25 ticks and rule 1's latency. Opt-in: no O1-O5 step carries `to`.

Why a verdict and not a sub-region (the critic's option (b)): decision 3. And why both paths must be DONE: in O6 the
walk-out runs ~12 ticks to a radius short of the floor's end and the map switches at 25 (0.2 #6) -- whether `settle()`
sees him still before the switch is the engine's timing, not the fork's; reading one path as V11 would turn a timing
race into a driver VOID that VOID-ASYM (b) can read as structural (critique #1's knock-on).

Tests (A1; each into `REQUIRED_TESTS`, G7's selection; H16's region walk-out, 3.1). Path A is reproduced
DETERMINISTICALLY (rev. 2, the driver critic's #3): the fake's switch is held by the test-side `fake.exit_gate` (H16)
until a log hook releases it when the door step's row is appended, so a starved harness thread can never read the
switch before `settle()` sees him still and flip the assertion; path B (`stop_z` None) needs no gate.
`test_segment_step_of_trigger_to_is_strict` (pure: an int accepted; a bool, a str, a float refused; a cross's `to`
unchanged);
`test_segment_trigger_to_verdict_classes` (pure: path A, path B, a wrong place -> left, a loss in another field, no loss
with a landing, an in-field loss without the evidence and a landing -> v11, the same with no landing -> judge; break:
drop the in-field rule -- the loss in another field reads its x, z);
`test_segment_trigger_to_lands_after_the_walk_returns_on_the_fake` (H16: a short walk-out -- `stop_z` just past the
firing line -- and the switch GATED until the step row is logged: `landed` None, done, the step row's `route.landed`
None; then rule 1 fills `walkout`, `flip_frame` (`flip_late` True) and `landed_frame` on that row (S14b); break: no
S14b -- `flip_frame` stays None);
`test_segment_trigger_to_lands_before_the_walk_returns_on_the_fake` (H16: the walk-out runs until the switch: the
record's `landed` is the next field, done, `flip_frame` set from the ring, `walkout` filled at rule 1; break: the same
table WITHOUT `to` -- today's `x_trigger` -- reads V11 "the trigger's walk left ...": the test that fails on today's
code);
`test_segment_trigger_to_wrong_landing_is_rule_2s_on_the_fake` (the region's own `to` is another place: the step row's
outcome "left", `misroute` the wrong field, `landed` None, no beat; the run VOID V11 (GAME) at rule 2's cell, its rows
in the wrong field UNBACKED (`_backing` None); on F with the region's `to` a REAL field a member forks: V19 (game);
break: the first design's `strayed` -- V11 driver, `landed` set, the rows backed);
`test_segment_trigger_to_unseen_loss_is_v13_on_the_fake` (the fake's publication stalled from the fire to the switch --
`fake.stall_publish` -- so the first read without control is in the next field: V13 driver, never done, never V11;
break: judge `until` on that read);
`test_segment_trigger_without_to_keeps_todays_paths_on_the_fake` (path B without `to`: V11 driver, exactly today's
row and reason, no `misroute` key, no `walkout` -- O1-O5's executor pinned by behaviour).

**S15 -- END_RUN'S NAMING RECOVERY AND THE SESSION STOP** (decision 4; critique #9; rev. 2: the driver critic's #4 --
the screen accepted FIRST; built in A2). `Segment.end_run` (segment_trace.py:537-587) gains a method and two call
sites; its battle branches and the plain path are untouched:
```python
                try:
                    g.warp(recovery)
                    log.append({"k": "recover-warp", "field": recovery})
                except HarnessError as err:
                    log.append({"k": "recover-warp-failed", "why": str(err)[:200]})
                    if g.state.ui_state == "NameSetting":   # S15: the screen FIRST -- before any Cancel, before the ladder
                        self.end_naming(g, log, recovery)
        ok, why = g.restore_baseline()
        if not ok and g.state.ui_state == "NameSetting":    # a screen that opened after the warp's read: today's place
            self.end_naming(g, log, recovery)
            ok, why = g.restore_baseline()
        if not ok:
            raise HarnessError(f"the title could not be restored: {why}")

    def end_naming(self, g, log: list, recovery: int) -> None:
        """S15: accept the naming screen (its default), then the warp a running scene cannot refuse from FieldHUD."""
        try:
            g.accept_name()
        except HarnessError as err:                         # the screen will not leave: nothing can reach the title
            log.append({"k": "end-naming-failed", "why": str(err)[:200]})
            stop = HarnessError(f"the naming screen stayed up through accept_name ({str(err)[:160]}): the title "
                                f"cannot be reached -- the session stops")
            stop.session_stop = True                        # S15's marker: run() stops the session cleanly
            raise stop from err
        log.append({"k": "end-naming"})
        try:
            g.warp(recovery)
            log.append({"k": "recover-warp-after-naming", "field": recovery})
        except HarnessError as err:
            log.append({"k": "recover-warp-after-naming-failed", "why": str(err)[:200]})
```
**The order** (the driver critic's #4, re-timed in session.py): today's order climbs the ladder first -- `close_ui`'s six
Cancels and 20-s wait, then the soft reset's 45-s wait, ~67 s (0.2 #17) -- and only that gap keeps the last Cancel's
0.5-s refocus (NameSettingUI.cs:122-133) from undoing `accept_name`'s first Confirm. S15 accepts the screen on the
refused warp, when nothing has pressed Cancel: Confirm 1 takes the focus off the box, Confirm 2 is OK, the retried warp
leaves 151's running scene from FieldHUD, and the ladder climbs from 4600 -- seconds, not ~67 s (F6 records
R-NAMING-VOID's measured time). `end_naming` is NEVER called within 0.5 s of a Cancel: at its first call site nothing
has pressed one; at its second the ladder's 45-s soft-reset wait separates them.
The marker is an ATTRIBUTE on a HarnessError, never a new class: every handler that catches HarnessError today (the
session end's `ended` record, a rehearsal's `one()`) keeps catching it. `Segment.run`'s `one()` reads it:
`except HarnessError as err:` -> when `getattr(err, "session_stop", False)`: the run's record gets `stopped` (its why)
and `skipped` "the session stopped: <why>" when its drive never began (the marker came from the `end_run` at the run's
head), else `outcome` "STOPPED: the session stopped: <why>"; the shared flag `halt` is set. The run loop breaks on
`halt` before the next run and the re-run loop does not start; `session["stopped"]` records the why. The session's end
(`end_session_warps`) still calls `end_run` (its HarnessError, marker or not, goes into `session["ended"]`) and the
analysis runs on what was recorded: a stopped session is judged on the runs it COVERED -- VOID by O6-COVER when a
side is under `min_covered` (naming-stuck-session), else those runs' verdict (naming-stuck-after-four: PROVEN on 2 + 2)
-- never NOT PROVEN by a run it never drove (rev. 2: the first design's "a short session reads VOID" held only for the
first case, the claim critic's #5).
**NOT neutral for O1 and O2 -- an INTENDED change** (rev. 2, the claim critic's #5; recorded in 11.6 before building).
`O1Segment` and `O2Segment` inherit `Segment.end_run` and `run` (o1_opening.py:246, :359; segment_trace.py:537-587,
:633-690), and both routes hold a naming screen (O1's 50 `Menu(1, 0)`, o1_opening.py:164; O2's frozen registration
(116, 1155, `named`) in `o2_predictions_v1.json`). An O1 or O2 run stopped with its screen up now gets the screen
accepted at once and the retried warp (today: ~67 s, then the ladder through the running scene, which O1d saw fail),
and a screen `accept_name` cannot close now stops the session (today: every later run's `end_run` meets it, one run
at a time). The first design's "O1-O5 never raise the marker" was wrong. Neutral for O3-O5 (their routes hold no
naming screen: `naming` [] in their predictions). The regression gate replays RECORDED sessions (G1-G31) and cannot
see a driver or session change at all: the fake tests below pin the new behaviour, O1's and O2's included.

Tests (A2; into `REQUIRED_TESTS`):
`test_segment_end_run_warps_after_the_naming_screen_on_the_fake` (in 30820, a visit beat's pages, then a scene-level
`{"naming": 3}` beat, then another visit beat whose script runs on after the screen; the run stopped with the screen up;
H16b's `reset_blocked_fields` {30820}, the fake's `warp_field_only` on, `soft_reset_ui` the engine's; `close_ui` and
`soft_reset` wrapped to RECORD their calls: the log reads `recover-warp-failed`, `end-naming`,
`recover-warp-after-naming` (30821, the session tests' stand-in for 4600), then the title, and neither wrapper was
called before `accept_name`'s first Confirm; breaks: no retried warp -> "the title could not be restored"; the first
design's order (the ladder first) -> `close_ui` called before the screen was accepted);
`test_segment_end_run_stops_the_session_when_accept_name_fails` (`g.accept_name` wrapped to raise: `end-naming-failed`,
a HarnessError with `session_stop` True; break: raise a plain HarnessError);
`test_segment_session_stops_cleanly_on_a_stuck_naming_screen_on_the_fake` (`Segment.run` on the fake with a stub segment
whose run 1 leaves the naming screen up and whose `accept_name` always fails: run 2 recorded `stopped` and `skipped`, no
run 3, no re-run, `session["stopped"]` set, `session["ended"]` ok False, the analysis read; break: catch the marker as a
plain HarnessError -- runs 2 and 3 each VOID "STOPPED", the session lost one run at a time);
`test_segment_reset_blocked_fields_swallow_the_combo_on_the_fake` (H16b's own test, 3.2);
`test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake` (rev. 2, the claim critic's #5: the
INHERITED, unedited `O1Segment().end_run` and `O2Segment().end_run`, each with its own route's screen up on the fake --
`{"naming": 0}` / `{"naming": 1}` -- read S15's rows (`recover-warp-failed`, `end-naming`, `recover-warp-after-naming`)
and reach the title; with `accept_name` wrapped to fail, `end-naming-failed` and the marker; the intended change pinned
by behaviour).

**S16 -- THE NAME ON THE PAGE** (an opt-in `on_page` on a naming registration; decision 4's witness; built in B3 with its
fake, 11.2 #2). The trace cannot see `PLAYER.Name`; the page that renders it can (0.2 #8). **The driver ENFORCES, the
analysis re-checks** (rev. 2, the claim critic's #2 -- O5's CHOICE shape: there the other branch's page is the driver's
V13 and CHOICE only re-checks). The first design had the driver record and O6-NAMING judge: an instrument miss (no
parsed sample, a missed 198) then FAILED a core check -- against THE PAIRED-WALK LAW's coverage rule, "a walker failure
is VOID, never a falsification" -- and a name typed during `accept_name`'s blocking call (which the run-wide witness
polls around, never through: o4_castle.py:790-830) left a COVERED run that failed (b). The name has no field key --
`Menu(1, 3)` goes to `EventService.StartMenu` (DoEventCode.cs:2317-2340), the default comes from
`CharacterDefaultName` (NameSettingUI's `SetData`), P-TEXT3 is strict -- so a non-default name is input or the engine,
never the fork: the driver's V13, re-run, as O5's other-branch page is.
```python
NAMING_KEYS = ("donor", "sc", "beat", "on_page", "why")
ON_PAGE_KEYS = ("tag", "beat", "windows", "why")
WINDOW_KEYS = ("mes", "raw_holds", "line", "text")
def naming_of(pred) -> list:
    """pred["naming"] checked STRICT before anything is driven (S16): a list of registrations, each exactly keys of
    NAMING_KEYS -- ``donor`` and ``sc`` ints (a bool is no int), ``beat`` a non-empty str or None, ``why`` a str -- and,
    opt-in, ``on_page`` exactly keys of ON_PAGE_KEYS (``why`` optional): ``tag`` a non-empty text tag (``"[STNR]"``),
    ``beat`` a non-empty str, ``windows`` a non-empty list, each exactly WINDOW_KEYS -- ``mes`` an int, ``raw_holds`` a
    non-empty str holding ``tag``, ``line`` an int >= 0, ``text`` a non-empty str holding no ``tag`` and no ``[``.
    ValueError naming the first fault. O2's ``{"donor", "sc", "beat"}`` passes unchanged."""
```
In `_Drive`: `self.naming = naming_of(pred)` at the start; rule 4 reads it (as today: the first registration of the
place and the published SC). Under a registration WITH `on_page` only:
- BEFORE `accept_name`, `before = self.last_listed(st.frame)`: the ring's latest sample before the naming screen's first
  sample that listed a window -- `{"frame", "raws"}` (`dialog_rows(raw)`'s phrase_raw column) -- or None; the `named`
  row gains `"before": before`. (Read before the Confirms: the ring holds 300 samples, the screen a few seconds.) The
  driver records it; the analysis reads it (A-NAMING, 5.1: a `before` without 198's marker leaves the run UNCOVERED).
- AFTER it: the page witness is armed -- `self.pw = {"tag", "beat", "windows", "frame": st.frame, "field": self.fid,
  "visit": self.visit, "scanned": st.frame}`.
- EVERY POLL (after rule 3, before rule 4; armed only): a new visit disarms it -- no row, its beat stays False: the run
  UNCOVERED (the ring held no parsed frozen window while 151 lasted: the instrument's miss, never a failed check); else
  `page_witness(st)` scans `ring_since(g, scanned)` for the first sample in the armed field listing a PARSED window that
  a frozen window names (its raw holds that window's `raw_holds`, its text holds no tag). On it, ONE row `{"k":
  "name_on_page", "field", "donor", "visit", "frame", "tag", "windows": [{"mes", "raw", "text", "line", "want", "ok"},
  ...], "verdict"}` -- EXACTLY those windows (an unparsed window, or one no frozen entry names, is never listed: with
  the bytes' ~6-tick lag the first such sample normally lists 199 alone, 0.2 #8) -- each window's line `line` compared
  with its frozen `text`, disarmed. All equal: `verdict` "ok", the registration's `on_page.beat` True. Any differs:
  `verdict` "V13" and RouteVoid V13 (driver), cell `[place, sc, visit]`, "the name on the page is not the default: mes
  <m> renders <line>, registered <text> -- input at the naming screen (accept_name's blocking call, which the
  run-wide witness does not see)".
Without `on_page` (O2's registration) rule 4 is today's exactly: no `before`, no arming, no row.

Tests (B3; into `REQUIRED_TESTS`): `test_segment_naming_of_is_strict` (pure; each refusal once, the `windows` keys
included; O2's registration passes); `test_segment_naming_on_page_rows_on_the_fake` (H17: a page holding "And,
Captain", the naming step, a KEYON pair of two [STNR] windows, the second opening 6 ticks after the first (the bytes'
lag): the `named` row's `before` holds the page's raw, ONE `name_on_page` row listing the FIRST window alone, "Steiner"
rendered, `verdict` "ok", the beat True; with H17's `unparsed_frames` {first: 2} the row's frame is the first PARSED
sample's; the pair opened together with `unparsed_frames` {second: 3}: the row lists the first window only;
`name_typed` "Rusty": the row's `verdict` "V13" and the run VOID V13 (driver); an O2-shaped registration on the same
fake: the `named` row has exactly today's keys and no `name_on_page` row; breaks: take the first sample listing the tag
whatever its text; list every window of the sample holding the tag; record without judging (the first design: a typed
name covered); read `before` after the Confirms); `test_segment_naming_of_reads_every_frozen_predictions` (rev. 2, the
claim critic's #5: pure -- every `studies/story-trace/*predictions*.json` that exists, its `naming` or none, passes
`naming_of`: O2's `{"donor", "sc", "beat"}`, O3-O5's `[]`, O1's and rung 3/5's none; the file list is globbed at run
time, never pinned, so the lead's freeze adds a file the test reads, never one it expects);
`test_segment_alexandria_naming_keeps_its_rows_on_the_fake` (rev. 2, the claim critic's #5: O2's FROZEN registration,
read from `o2_predictions_v1.json`, through `naming_of` and rule 4 on the fake's `{"naming": 1}` scene: the `named`
row's keys exactly `k`, `field`, `donor`, `sc`, `frame` -- today's -- no `before`, no `name_on_page` row, no page witness,
the beat `named` True; break: write `before` whatever the registration).

### 1.3 `o6_steiner.py`

`O6Segment(o5_hallway.O5Segment)`:
- `tag = "O6"`, `predictions = HERE / "o6_predictions_v1.json"`, `manifest = HERE / "o6_forks.json"`, `session_file =
  "o6_session.json"`, `report_file = "o6_report.txt"`, `chain_dir`/`build_dir` O4's, `accept_us_build = False`,
  `recovery = 4600`, `end_session_warps = True`.
- `core_ids = ("START", "NO-SC", "CHAIN", "RESIDUE", "WRITES", "NULL", "STABLE", "LANDING", "NAMING", "WALK",
  "PATTERN", "START-DEPENDENT", "MASKED", "STATE", "JOIN")`; `titles` every check's O6 text (O5's shape, section 5).

**Inherited unchanged** (O5's, O4's, O3's or O2's): `read_session` (keeps the stock source), `forbidden_check`,
`void_asym_check` (O4's (a)-(d) over S13's `[place, sc, visit]` cells), `start_check` (O3's, data-driven: three residue
rows), `no_sc_check`, `span_check` (CHAIN), `residue_check`, `writes_check` (O4's EXACT over writes + chain + ladder
`[]`), `null_check`/`stable_check`/`join_check`, `masked_check`, `history`/`suppressed`/`state_check`, `text_check` (O4's,
over `text_blocks` [3]), `fingerprint_extra`, `drive` (O4's: `SD.drive(..., witness=input_witness(g))`), `build_check`
and `build_pins` (O5's: the route members' per-language pins from `route_build`, which is O5's -- the same three
members), `preflight_extra` (O5's: P-TEXT3 strict, P-RECOVERY, P-DONOR over `route` + `end_fields` = 151, 153, 154,
P-SETTINGS, P-PAD, P-OVERRIDE, P-ENGINE), `capabilities` (O5's: P-CAP, P-OBJECTS, P-LANG, P-DONOR-LOG and P-LAUNCH over
`ROUTE_DONORS`, which O6 rebinds to (151, 153, 154) -- the same set -- and P-PAD).

**Overridden:** `draft()` (section 4; members and names from O4's `campaign.toml`, `route_members` over 151, 153, 154);
`freeze()` (7.3's refusals, then the base's); `offline_extra` (O6-TEXT, O6-CENSUS, O6-REGIONS, O6-GOALS); `keys_check`
(O2's machinery on the chain, the writes, the start-dependent keys, `forbidden_sites` + `error_path` + `dead`,
`start_first`; then `start_music` one writes key, every `after.value` computed and `after.run` the class's `AFTER_RUN`,
and the route pins + `route_mes`, 6.1); `route_pins_check` (O6's `route_mes`); `census_check`, `regions_check`,
`goals_check` (O6's readers, 6.1); `core_checks`; `landing_check`, `naming_check`, `walk_check`, `pattern_check`,
`start_dependent_check` (5.3); `why_void` (O5's A-START scoped to visit 1 -- 151 is visited once, so an error-path row
of 151 is always A-START; 153's error path is V5 by the game at `[153, 1190, 2]` -- plus rev. 2's A-NAMING, 5.1);
`report_extra` (5.4); `add_arguments`/`handle` (`--draft`, `--rehearsal-report`).

**Class attributes and constants** (rev. 2): `AFTER_RUN = "O1-O5"` -- the span O6-KEYS requires of every
start-dependent key's `after.run` and the report renders from the predictions, never a literal (O7's subclass
overrides it: the claim critic's #4); `RUN_U_PER_TICK = 60` (his run under control: HonoUpdate's speed,
FieldMapActorController.cs:210-211) and `STALE_TICKS = 3` -- the evidence's slack DERIVED from them (4.12, O6-GOALS
(c'')), never typed (the claim critic's #8).

**Module functions** (pure unless named a reader): `ROUTE = (151, 153)`, `VISITS = (151, 153)`, `END_FIELD = 154`,
`ROUTE_DONORS = (151, 153, 154)`; `route_members(members)` / `route_members_line` (O5's shape over 151, 153, 154);
`instanced_at6(idx, entrance, *, items=None)` (0.2 #2: O4's walker, the dispatch a SWITCH / SWITCHEX on `Int16[2]` OR
every `SET({Global.Int16[2] const(N) B_EQ B_EXPR_END})` followed by `JMP_IFNOT(L)` / `JMP_IF(L)`, the entrance deciding
the branch -- on a field with neither, ValueError as O4's); `store_census6(fields, stock, pred, *, sites=None,
classify=None, instanced=instanced_at6)` (O5's census with the instancing seam, the LIVE shared proof, 6.1);
`regions_problems6(pred, stock, *, instanced=instanced_at6)` (O5's, with the seam); `goals_extra6(pred, walkmesh=None)`
(c'), (c''), (d'), (e) (6.1); `door_test(text)` (e23's tag-2 test read off its pinned text: `(ground_y, threshold_z)` =
(-100, 1333) from `f[1] const(65436) B_GT` / `f[2] const(1333) B_GT`, 2-byte constants signed; None for a test with no z
term); `pattern_of6` (O5's `pattern_of`, reused) and `pattern_diff6(got, pat)` (the floating rows, 5.3);
`naming_rows(log, pred)`, `on_page_lines(row, pred)`, `start_dependent_rows(rows, pred, members)`; `trace_summary(rows,
pred, ...)` (O5's shape, O6's crossings: 151 ip932 -> the next row, 153 ip203 -> the cut; the e15 row's frame, index and
gap to ip971; the two start-dependent rows); `rehearsal_report(run_dir)`; `run(g)`; `main(argv)`.

### 1.4 The regression gate extended to O5 (`segment_regress.py`)

The implementer extends the gate and captures its O5 baseline FIRST (A0), before any shared-code change. The O5 items
import only O5's modules (`o5_hallway`, `o5_dryrun`) inside their functions.

`O5S = C:\gd\Dream-World-IX\.harness-runs\20261003-091627-story-o5`, `V1_O5 = HERE / "o5_predictions_v1.json"` (sha256
`0c991f43...`).

| Item | Check |
|---|---|
| G0'''' | `py studies/story-trace/segment_regress.py --capture-o5` writes `research/o5_regress_baseline.json` (LF, `-text`): the full `(checks, report)` of O5S with V1_O5; every `o5_dryrun` session case's `(checks, report)` and "predictions-changed"'s; every unit's `(name, ok, detail)` (`units(...)` then `listed_units(...)`, in `run_cases`'s order); `O5.offline_check(V1_O5)`; the tests G26 collects; the HEAD and V1_O5's sha; and `sources`: the AST sha of every test G26 collects and of every function in `FAKE_PINS_O5` (below) -- only names neither the O3 nor the O4 baseline already pins (`o5_pin_names` refuses one pinned in either). It refuses an existing file, refuses unless G26, G27 and G28-G31's baseline-free halves pass, and takes TWO readings first, refusing when they differ after every temporary root reads `<tmp>` (G0'''s rule). |
| G28 | `O5.analyse(O5S, pred_path=V1_O5)`: the report equals `(O5S/"o5_report.txt").read_text(encoding="utf-8")` exactly and the baseline's; the checks the baseline's; PROVEN with 18 checks, all True. |
| G29 | `py studies/story-trace/o5_hallway.py --analyse O5S --predictions V1_O5` exits 0 and prints that report (plus print's newline), run as G23 runs O4's CLI (`PYTHONIOENCODING=utf-8` in its environment: O5's pages quote U+2500, which `segment_trace.say` would escape on a cp1252 console). |
| G30 | Every `o5_dryrun` session case's `(checks, report)` and unit's `(name, ok, detail)` byte-equal to the baseline's (each temporary root `<tmp>`), and `o5_dryrun.run_cases(V1_O5)` returns 0 printing "144/144 cases as registered" (N from the replica). The replica follows `run_cases` step for step, as G24 does O4's. G30 IS O5's VOID-PATH BASELINE: story-o5 holds six covered runs. |
| G31 | `O5.offline_check(V1_O5)` equals the baseline's `[(ok, what, detail)]`: 6 checks, all PASS (reads O4's build and the install, read-only). |
| G21 (extended) | THE SOURCE PINS over the UNION of the O3, O4 and O5 baselines' `sources` (`union_sources(*sources)`: a name in two refused), against one `research/source_pins.json` (append-only; `--rebaseline-source NAME` looks NAME up in any of the three; the CLI passes `--baseline-o5`, and a call naming none reads the O3 baseline alone -- O5's 11.5 PART A #1 lesson: a test's temporary baseline never meets a committed one). |
| G32 (from B3) | `pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o6_ or fake_naming or fake_door"` from `ff9mapkit/`: all passed, 0 failed, 0 skipped, 0 errors; every name in `REQUIRED_TESTS_O6` among them. No baseline: the list is the floor. |
| G33 (from C2) | `o6_dryrun.run_cases` on the frozen O6 predictions once they exist, else the draft, AND on `o6_dryrun.as_if_frozen(draft)` -- the draft with every freeze-time value changed as the lead's freeze changes it: `pattern.floating[0].measured` set inside its window, every budget scaled (x1.5, rounded), `rehearsals` non-empty (rev. 2, the claim critic's #9: the freeze rewrites exactly the values that cost O2, O4 and O5 a pre-merge run, so the cases must be shown to read them from the predictions, never a literal): each returns 0 printing "N/N cases as registered", N at least `O6_DRYRUN_FLOOR` (the count C2 prints). |

`FAKE_PINS_O5` (the fake O5's tests run on, beyond the O3 and O4 pins, by qualified name): `FakeGame._story_site`,
`FakeGame._story_counts`, `_visit_steps`, and every method of `_VisitBeat` (`FAKE_PIN_CLASSES_O5 = ("_VisitBeat",)`;
`fake_pins_o5()` reads them as `fake_pins_o4()` does). `_missing()` gains O5S's session and report, V1_O5, the O5
baseline (`o5s`), and from C2 the frozen O6 predictions or O4's `campaign.toml` (`o6`). Tests O6 adds named `test_segment_*`
join `REQUIRED_TESTS` (G7); every `test_o6_*`, `test_fake_naming_*` and `test_fake_door_*` joins `REQUIRED_TESTS_O6`.
O6's rehearsal tests are named `test_o6_rehearsal_*` (never "rehearse": G12's selection); no O6 name holds "o5_",
"o4_", "o3_drive", "o2_", "o1_" or "fake_visit" (G26's selection). Test: `test_segment_regress_o5_pins_join_the_union`
(A0, pure: G21's checker over three baselines on temporary copies -- an edited pinned O5 test FAILS naming it; a
re-baseline row for an O5-baseline name passes; a name pinned in two baselines is refused at capture and by the union;
into `REQUIRED_TESTS`).

---

## 2. The drive

### 2.1 The model (keys the driver reads; the rest of the predictions is the analysis's)
- **`table`**: ONE cell, `{"donor": 153, "sc": 1190, "visit": 2, "steps": [the north door]}` (2.5; S13: every VOID and
  `observed` cell is `[place, sc, visit]`). Control anywhere else -- 151@110, 153 before the grant or after the step,
  154 before rule 1 -- is V4 (game).
- **`naming`**: `[{"donor": 151, "sc": 1190, "beat": "named", "on_page": {"tag": "[STNR]", "beat": "name_on_page",
  "windows": [{"mes": 199, ...}, {"mes": 200, ...}]}}]` (4.11: the frozen windows and their computed lines live HERE,
  the one source the driver judges with and the analysis re-reads) (rule 4 + `accept_name`; S16's page witness, which
  judges the lines). A naming screen anywhere else is V10 (game).
- **`battles: []`** (any battle V10); no `movies`; no `guard`, no `chanbara`.
- **`stop_pages`**: `[{"match": "Env Play()", "why": "151's and 153's ambient error window 56 ('Error Env Play()
  Slot=n': 151 e0 t0 ip950/984, 153 e0 t0 ip2304/2338): Byte[13]/[14] arrived as 2 or 9"}]`.
- **`choices`**: O1's skip net only, `{"donor": null, "sc": null, "match": "want to skip", "pick": "default", "once":
  false, "beat": null}` -- no choice is on the route; any other is V1 (game).
- **`witness`** (S12, run-wide): `{"input_every_s": 0.05, "why": ...}` (4.13).
- **`route: [151, 153]`, `visits: [151, 153]`, `end_fields: [154]`, `side_ends: {"S": [154], "F": [31246]}`** (S6).
  **`regions`** (4.17): the landing judge reads role `exit` (153.e23, e24, e25) and the step's `avoid`.
- **`budget`** with `end_row_s` (rule 1 waits for 154's first row) and `settle_s` (rule 8's settle).

### 2.2 The driver loop for O6 (O5's rules in O5's order; O6's additions marked)
Every poll reads `st`, `sc` and `donor = place(fid, members)`. (S12) the witness first.
1. **End** (`fid in self.ends`: real 154 on S, member(154) 31246 on F): the end state (4.10), the last scan, (S14b) the
   done door step's walk-out and flip filled in from the ring, the end row (154's first trace row, up to `end_row_s`),
   `reached`. Then the stall watchdog.
2. **Route**: on F a REAL field a member forks is **V19** (game, a finding: `rerun.stop_on`) -- 151/153/154, or after the
   door's evidence held (S14's `left`) a real 150 or 64; anything else off the route V11 (`stray()`: the game's, unless
   the last thing the run did was an unfinished walk).
3. **Visit**: the order 151 -> 153; (S16) a new visit disarms an armed page witness (the beat stays False: uncovered).
3b. (S16) **The page witness**, armed only after a registered naming with `on_page`: the ring scanned for the first
   sample listing a PARSED window a frozen entry names; on it the `name_on_page` row, JUDGED -- the lines equal: its
   beat; else V13 (driver: input at the naming screen).
4. **Naming** (registered: 151 at SC 1190): (S16) `before` read off the ring; `accept_name()`; the `named` row (with
   `before`); the page witness armed. Anywhere else: V10.
5. A tutorial or a battle: V10.
6. A choice: O1's readiness hold, then the rules (only the skip net exists: anything else V1).
7. **A page** (control off): the stop page (V5, nothing pressed); else O1's rule 7 -- Confirm, then
   `CUTSCENE_PAGE_TICKS` -- for every page, KEYON pair window and timed window alike (no guard, no page-once).
8. **Control held** (settled `settle_s`): (S13) the cell (153, 1190) at visit 2 runs the north door (2.5); anywhere else
   V4 (game), its cell `[place, 1190, visit]`.
9. Otherwise wait (the scripted walks, the fades, the knights, the load).

### 2.3 Every research beat, and what handles it
The research's `reconciled.route.beats` 1-24, with the critic's corrections.

| # | Field | Beat | Handled by |
|---|---|---|---|
| 1 | 70 -> 151 | the raw warp; residue SC bytes 0 (0 -> 166), 1 (0 -> 4), FieldEntrance byte 2 (0 -> 110) | `start_run` (O2's); O6-START (a) expects THREE rows |
| 2 | 151 | Main_Init at 110: the prologue (ip22-ip200, ip119 from old 1), InitObject 3/4/5/17/12, the BGM wait, ip315 `Byte[8] := 125` (same); Brahne e3 the defined player, no `Map.Bit[158]`: no control | nothing (WRITES, START); control here V4 |
| 3 | 151 | stage 1: 175 (e4, slot 2) and 176 (e5, slot 3) `[TIME=20]` -- NOT `[NFOC]`: a Confirm may close them early, a timing-only effect (no script waits on them, no store) -- then 177 (e12, slot 4, WindowAsync + WaitWindow ip477) | rule 7 (each sample pressed; F8 records whether 175/176 react) |
| 4 | 151 | stages 2-5: 178 (e17 Sync, slot 1), 179 (e5 Sync, 3), 180 (e4 Sync, 2), 181 (e17 Async + Wait, 1) | rule 7 |
| 5 | 151 | stage 6: KEYON pair 182 (e4, slot 2, [INCS][TIME=-1]) + 183 (e5, slot 3); the gate (`SYSVAR[8] < 2` and `Map.Byte[29]`'s 250-tick countdown), then e4 t1 ip516 KEYON (Confirm or Special, the EDGE) | rule 7 (Confirm every ~4 ticks until both close; an edge before the gate is lost) |
| 6 | 151 | stages 7-10: 184 (e12 Sync, 4), 185 (e17 Sync, 1), 186 (e4 Sync, 2), 187 (e5 Sync, 3) | rule 7 |
| 7 | 151 | stage 11: KEYON pair 188 (e4, 2) + 189 (e5 WindowSync, 3); e4 t1 ip693 | rule 7 |
| 8 | 151 | stage 12: 190 (e17 Async + Wait, 1); stage 13: waits only (e3 `op_22(90)`, Beatrix's 8-leg walk); stages 14-18: 191 (e3, 0), 192 (e17 Sync, 1), 193 (e3, 0; [SPED=2]), 194 (e17 Sync, 1), 195 (e3, 0; [SPED=2]) | rule 7; nothing in stage 13 |
| 9 | 151 | stage 19: KEYON pair 196 (e3, 0) + 197 (e17 WindowSync, 1); e3 t1 ip475 | rule 7 |
| 10 | 151 | stage 20: 198 (e3 ip576 WindowAsync, `op_22(10)`, TimedTurn, ip590 `WaitWindow(0)`; [SPED=2] type-outs) | rule 7 (a Confirm may only finish its type-out: pressed again on its next sample) |
| 11 | 151 | ip593 `SetCharacterData(3, 0, 3, 5, 3)`, `op_22(5)`, **ip603 `Menu(1, 3)`: NameSettingUI for CharacterId 3, the default pre-filled, the box focused**; `op_22(10)`, **ip610 `Byte[6] \|= 8`** (0 -> 8), `op_22(10)` | rule 4: `before`, `accept_name()` (Confirm 1 takes focus off the box, Confirm 2 is OK), the `named` row, the page witness armed (S16) |
| 12 | 151 | stage 21: KEYON pair **199** (e3 ip693 after `op_22(1)`, slot 0, "Captain [STNR]!") + **200** (e12 ip803 WindowSync after `op_22(7)` and RunAnimation -- ~6 ticks after 199 -- slot 4, "[STNR]" the speaker line); e3 t1 ip742; then 201 (e3 Sync, 0) | rule 7; the page witness's first sample listing a parsed frozen window (199 alone, normally): the `name_on_page` row, judged (S16) |
| 13 | 151 | stage 22: KEYON pair 203 (e12, slot 4, [STNR]) + 202 (e17 WindowSync, 1); e12 t1 ip935 | rule 7 |
| 14 | 151 | stage 23: ip735 `Byte[8] := 0`, DisableMove, PreloadField(5, 153), `op_22(65)`, ip932 `Int16[2] := 328`, ip940 `Field(153)` (F: 31245) | rule 3 (the visit) |
| 15 | 153 | Main_Init at 328 (ip255 SWITCHEX -> L603; ip802 JMP(L1288) skips L1098): the prologue (all same-value, all EMITTED: new sites), InitObject 32/16/17/13/14, InitRegion 23/24/25, InitCode 21; e32 t0 (case 328): CreateObject(-24, -2078) upstairs, size (30, 35, 50), `DefinePlayerCharacter`, ip718 `Bit[3855] := 1`, ip727 `Bit[3854] := 1` | nothing (WRITES, PATTERN) |
| 16 | 153 | stage 40: Walk(-24, -74); pages 211, 212 (e32 Async + Wait, slot 4); **ip866 `RunSharedScript(15)` -> e15 t0 ip32 `Byte[8] := 125`** (the Seq row, sid 15 uid 96, ~45 ticks + a sound sync later); 213, 214 | rule 7; the e15 row floats (PATTERN) |
| 17 | 153 | stage 41: 215 (e16 WindowSync, slot 5); stage 42: 216 (e17 WindowSync, 6); the knights `SetObjectFlags(7)` (walk-through) | rule 7 |
| 18 | 153 | stage 43: 217 (slot 4) with the loop ip971 `Byte[208] := 0` (same) / ip1006 `++`; 218 with ip1041 `:= 0` / ip1076 `++` -- the stores run while each page is up | rule 7 |
| 19 | 153 | stage 44: SetWalkSpeed(60) ip1160, four walks down the west stair; stage 45: Walk(-575, 807) ip1360, **Walk(-245, 42) ip1367**, the knights' rendezvous (they walk, he stays) | rule 9 (wait) |
| 20 | 153 | stage 46: 219; stage 47: 221 (220 is never shown) | rule 7 |
| 21 | 153 | stage 48: 222 (slot 4) with ip1597 `Byte[208] := 0` / ip1632 `++` | rule 7 |
| 22 | 153 | THE REBUILD (no input): ip1656 `UInt16[21] := 8`, SetPartyReserve, RemoveParty x12, PARTYADD(3); ip1741 `Byte[303] := 0`, ip1775 `++`; PARTYCHK(5) false -> ip2172 `Byte[4] := 0`; ip2180's bit-3 test true -> **ip2206 `UInt16[19] \|= 8`**; ip2232, ip2240, ip2248; ip2382 `Map.Bit[158] := 1`; **ip2412 `EnableMove()`: STEINER'S FIRST CONTROL** at (-245, 42) | rule 8: settle, then the cell's step |
| 23 | 153 | THE NORTH DOOR: e23 t2 ip38 (`SYSVAR[2]`, on the ground, z > 1333) -> ip59 ExitField (control goes; the walk-out north, held a radius short of the floor's end, z ~2065) -> 25 ticks (ip153 `op_22(25)`; ip95's `op_22(1)` skipped) -> ip203 `Int16[2] := 315`, ip211 `Field(154)` (F: 31246) | the trigger step with `to` (2.5; S14); its walk-out on record (S14b) |
| 24 | 154 | THE END: 154 e0 t0 ip26 (31246 on F) -- the cut row; 154's Main_Init at 315 (L392) writes only same-value prologue stores | rule 1 (per side) and its end row |

### 2.4 151@110: the royal seat box and Steiner's naming
- **No control.** Brahne (e3) is the defined player (e3 t0 ip171) and nothing sets `Map.Bit[158]` at 110 (0.2 #20):
  the whole visit is rule 7's pages and pairs, rule 4's naming and rule 9's waits. A control sample here is V4 (game)
  at `[151, 1190, 1]`.
- **Pages, pairs, timed windows.** O1's rule 7, unchanged: 17 pages, five KEYON pairs (Confirm every ~4 ticks until both
  windows close: each gate is at most 250 ticks, 8.3 s -- `no_progress_s` >= 60 covers it), and 175/176. 175/176 carry
  `[TIME=20]` WITHOUT `[NFOC]` (unlike O5's 137/140): a Confirm decided on a sample listing only them may close one
  early -- e4/e5 never wait on them (WindowAsync, no WaitWindow) and no store follows them, so the effect is timing
  only; F8 records it.
- **198 and the naming.** 198 types out ([SPED=2]): rule 7's first Confirm may only finish it; its next sample is
  pressed again. ip590 `WaitWindow(0)` returns when 198 is gone; `op_22(5)`; ip603 `Menu(1, 3)` opens NameSettingUI
  (DoEventCode.cs:2317-2341: skipped only under `DisableNameChoice`, pinned 0 by P-SETTINGS), pre-filled with
  `CharacterDefaultName` (NameSettingUI.cs:137-151, id 3 < 12), the box focused. The agent publishes `ui_state`
  "NameSetting", no dialog. Rule 4: the registration (151, 1190) matches; S16 reads `before` (198's last listed sample,
  0.2 #8); `g.accept_name()` (session.py:7134-7156): up to 4 Confirms, each waiting <= 2 s for the screen to close --
  Confirm 1 takes the focus off the box, Confirm 2 is OK: `SetCharacterName` -> `PLAYER.Name = "Steiner"` -> FieldHUD
  (NameSettingUI.cs:173-177). Never Cancel (refocuses), never Menu (resets the name). The `named` row is written, the
  page witness armed.
- **A stray Confirm.** (Rev. 2: the driver critic checked this and found it cannot happen; the first design's hedge is
  kept only as the worst case.) Rule 7 presses only while a window is listed, 198 leaves the list only after its close
  animation, `op_22(5)` separates its close from `Menu(1, 3)`, and a Confirm during NameSettingUI's Show fade is
  dropped (`UIScene.OnKeyConfirm` returns false while `isLoading`, UIScene.cs:108-111) -- so no rule-7 Confirm reaches
  the box. Were one to go down on the open screen, it would do Confirm 1's job (the focus off the box) and
  `accept_name`'s first Confirm would be OK -- the same default name; TWO would close the screen before rule 4 sees it:
  no `named` row, the beat False, the run uncovered (A-BEATS) and re-run, never a wrong claim. `accept_name`'s own first
  Confirm may meet the fade and be dropped: its 2-s wait and the next Confirm absorb it (4 Confirms in all). F3 records
  every Confirm's down frame against the screen's first sample.
- **The witness.** ip610 `Byte[6] |= 8` runs after the screen closes (`op_22(10)`): its row follows the `named` row
  (O6-NAMING (a)). Stage 21 opens 199, then 200 ~6 ticks later -- the first [STNR] windows after the naming -- and S16
  takes the first sample listing a PARSED window a frozen entry names (199 alone, normally) and JUDGES it against the
  frozen lines: "“Captain Steiner!”" as 199's second line, "Steiner" as 200's first when listed. Equal: the
  `name_on_page` row (`verdict` "ok") and its beat; different: the row (`verdict` "V13") and the driver's V13 -- input at
  the naming screen, re-run (O6-NAMING (b) re-checks a covered run's row). The ring holding no parsed frozen window
  before 151's visit ends leaves the beat False: the run uncovered, never failed.
- **The exit.** Stage 23: ip735 `Byte[8] := 0`, `op_22(65)`, ip932 `Int16[2] := 328`, ip940 `Field(153)` (31245 on F:
  member(151)'s operand, P-EB). Rule 3 counts visit 2.

### 2.5 153@328: the assembly and the north door (cell (153, 1190), visit 2)
**The assembly** (no control): 11 pages by rule 7 (211-219, 221, 222); the stage-44/45 walks by rule 9; the rebuild, no
input. The e15 Seq row lands during 212-214 (0.2 #11). The knights walk in at stage 45 and out east at 48 (walk-through:
flags 7, then 14) and are gone (`op_1C(255)`) soon after the grant; the soldiers e13/e14 stand on the upper corridor
(PSX -1499) all visit.

**The step** (the research's walk plan with the critic's corrections and decision 3; O5's `steps_default` under it):
```json
{"kind": "trigger", "name": "the north door", "goal": [19, 1620], "until": {"z_gt": 1200}, "to": 154,
 "avoid": ["153.e24", "153.e25"],
 "closed_tris": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 28, 32, 33, 34, 35, 38, 39,
                 41, 42, 43, 45, 46],
 "npcs": false, "beat": "steiner_door", "start": [-245, 42]}
```
Why each key:
- **trigger, not cross** (the research's dispute 3): a `cross` passes e23's quad as the zone, and `route_to`'s smooth
  leg returns "arrived" on the first sample inside it (session.py:3368-3369) -- z ~930, where e23 cannot fire -- and the
  step ends "failed" with control held. A trigger with an `until` and no `target` walks to the goal with no zone
  (segment_drive.py:2476-2478) and is judged on the loss.
- **`to`: 154** (S14): the step is done on the loss sample's evidence AND a landing that is None or in place 154 -- path
  A (`route_to` returned before the switch) and path B (after it) alike (0.2 #6). On F, place(31246) = 154. A landing in
  another place after the evidence held is S14's `left`: rule 2's verdict for that field -- V11 (game), or V19 on F for
  a real field a member forks -- never the walk's (11.5 #1). A landing in REAL 154 on F passes the step (place 154) and
  is V19 by rule 2 on the next poll -- the step judges the walk, rule 2 the chain.
- **`until` {z_gt: 1200}**: e23 t2 ip38 fires only on the ground with z > 1333 (`f[2] const(1333) B_GT`); his loss
  sample is the first read with control gone, at or north of the firing line (the walk-out carries him north), so a
  real fire always satisfies z > 1200; the 133-u margin admits a sample whose published position trails the engine's by
  a tick or two (O6-GOALS (c''): at most the DERIVED slack -- `STALE_TICKS` 3 x his run's 60 u a tick = 180 u, 4.12 --
  of e23's non-firing band; the first design's typed 160 is withdrawn). No other control-taker at 328 reaches z 1200:
  e24's quad lies at z <= 406, e25's at z <= -900 (O6-GOALS (d')).
- **`avoid` e24, e25**: the two other live exits at 328 (e24 -> 150@315, unconditional; e25 -> 64@315 on the ground,
  151@315 upstairs with z < -1400). `route_to` calibrates clear of them and plans round them (>= 942 u off).
- **`closed_tris`** (O5's 33): the upper corridor's floor-0 tris over the hall, which `point_on_walkmesh` would answer
  first (no route on the plain mesh: `route153.out`); floor 1 (0xa001) is closed at mask 255 already.
- **`npcs` false**: the harness's level filter keeps an actor standing on ANY floor under it (session.py:4981-5008), so
  e13 (158, 1102) and e14 (-226, 1086) on the corridor (PSX -1499) would become 220-u discs over the ground approach,
  though the engine never pairs them (|dy| >= 400, WalkMesh.cs:922); the knights carry bit 2 (no pairing,
  WalkMesh.cs:915-917); no actor at 328 has a Range; talk needs a Confirm the driver never presses with control held.
- **`start` [-245, 42]**: stage 45's last Walk (ip1367), the grant's position by the bytes; R-DOOR measures it (F1).

**The floor:** `floor_for(153, closed)` = `PlayerWalkmesh(stock 153, closed=the 33)`; the same floor on S and F (P-FLOOR
pins member(153)'s deployed walkmesh to 153's).

**The planned route** (0.2 #12): (-245, 42) -> (19, 1620), one leg, 1600 u, >= 113 u off every wall at the planner's 80
(Steiner's radius is 120: at 120 the planner's route bends through (-53, 1130), >= 123 u off; no clearance key, as the
research found), the firing line first crossed at (-29.0, 1333.1) on ground tri 79, inside e23. This is what O6-GOALS
(c') judges -- the line the planner can draw -- NOT the path he walks.

**The pressed path** (0.2 #7, rev. 2: the driver critic's #1, re-run on stock 153). The smooth walk presses pads, each
hold the longest whose end stays within 180 u of the leg's remaining line (walls never count), so: hold 1 "up" (the
basis's v, 8 degrees west of the leg), ~800-900 u from the grant straight into the WEST CORNER of the corridor mouth --
his clearance falls under his radius at (-224, 917), the corridor's open ground is x [-175, 210] from z 1150, his centre
band [-55, 90]; the engine slides or stops him there (unmeasured: RadiusValid / ServiceForces, FieldMapActorController.cs
:1060-1245), the fake pushes him east (to (-179, 941) at clearance 120). Hold 2 is sent at published z ~940-1020,
inside e23's quad in its non-firing band, control held -- "up" again, or "up+right" when a stop left him off the leg
(the drift rule turns him back: no stall loop) -- and carries him through the mouth past z 1333 on its east-pushed line:
the fake's loss at (-50.4, 1339.8) (clearance 120), (-90.8, 1348.4) (80, three holds). ~22 ticks of running to the
fire (~1310 u in the fake), the calibration's probes before it.
R-DOOR records hold 1's end point and every slide, stall, push or blocker at the corner (F1, F12: a go/no-go), and the
hold-2 starts F15 takes `walk_stop_z` from. The planned line's soundness is unaffected: every open tri past z 1200 is
ground, and only e23 reaches past it (O6-GOALS (d'), (e)) -- wherever the corner sends him, a loss past the evidence is
e23's.

**Calibration:** `route_to` calibrates clear of `avoid` with `key_prior(153)` (every `SetControlDirection` in 153 is (248,
0): one basis for the field, the camera code e21 visual only); F calibrates `prior_for(153)` (the place). The probes
(<= ~240 u; the fake's up probe reached z ~192) reach no region from (-245, 42) (e25 942 u south, e23's south edge 882 u
north) and stay below `walk_stop_z` 500.

**The walk-out and the two landing paths** (0.2 #6): at the fire, ExitField takes control (the probe's `lost`, read in
153) and MOVJ walks him north toward (his x, 3000) at 60 u a tick -- the run's speed, kept from his last controlled
frame -- until pathing holds his centre a radius short of the open floor's end, z ~2065, ~12 ticks after the fire; 25
ticks after the fire ip203 and `Field(154)`. `route_to` (handoff) returns when its hold ends and `settle()` sees him
still -- most likely before the switch, held ~13 ticks at the floor's end (path A: `landed` None; x_trigger_to's
`left_for` then reads 153 still, or waits out the switch if the id already left: `landed` 154, `flip_frame` from the
switch), after it otherwise (path B: `rec.landed` 154 or 31246, `changed_to` set, `flip_frame` from the ring). Both are
done. Rule 1 then puts the walk-out's samples, the flip and the landing frame on the step row in both paths (S14b);
R-DOOR records each run's path, `lost.frame`, `flip_frame`, `landed_frame` and where the walk-out stopped (F2).

**Hazards:** e25 (942 u south) and e24 (1897 u east) -- in `avoid`, registered `exit`: a loss in one is the landing
judge's (`door_loss` -> its switch -> V11 driver, `door` named). e26/e27/e28 are not instanced at 328 (registered
`dormant`). The knights pass >= 480 u south and east of the leg, walk-through. SETCAM #493 is effMapNo-wrapped and
camera-only; PSXCameraAspect's raw letterbox differs S/F (visual: never compare 153 camera-0 screenshots).

**Timeouts:** `timeout_s` 20 (the walk ~1 s); `TRIGGER_WAIT_S` 2 after a walk that ended with control held, then
`failed` (a first `failed` is re-run -- `attempts` 2 -- and O6-WALK (a) admits it; a second is V7, driver);
`interrupts` 1 (none is expected: no scene region is instanced at 328; one interruption leaves control off with no
re-grant, and the stall watchdog then reads it -- V14, the game's, which VOID-ASYM (a) reads).

**THE PAIRED-WALK LAW** holds by construction (0.2 #19): nothing stores between ip2412 and the loss; the next row is
the exit's own chain row ip203, after the loss. O6-WALK (b) checks the walk window on the rows (5.3).

### 2.6 The arrival in 154 (the end per side)
Rule 1 fires on its first poll in 154 (31246 on F): the end state read live (4.10: 154@315 stores nothing but same-value
prologue keys, so nothing races the read -- `Byte[8]` included, 0.2 #13), the last forbidden scan, the door step's
walk-out, flip and landing frame read off the ring onto its row (S14b), the end row (154's first trace row, e0 t0 ip26,
waited up to `end_row_s`). Nothing is pressed after rule 1; Steiner's control in 154
(Main_Init's tail ip588) comes later and is never read. `end_run` then warps to 4600 from 154's FieldHUD.

### 2.7 VOID conditions (each a RouteVoid with its class, cell and attribution; the run is not covered)
| | Condition in O6 | by |
|---|---|---|
| V1 | A choice no rule matches (none is on the route). | game |
| V4 | Control held anywhere but the cell (153, 1190) at visit 2 -- 151 at any point, 153 before the grant -- or control after its step is done. | game |
| V5 | The stop page ("Env Play()"), nothing pressed. | driver in visit 1 (151: the warp's start state); game after (153) |
| V7 | The north door out of attempts (2) or interruptions (1). | driver |
| V10 | A naming screen anywhere but (151, 1190); a tutorial; a battle. | game |
| V11 | Off the route or its order (rule 2's `stray()`/rule 3) -- including the north door's landing in a place other than 154 after its evidence held (S14's `left`, judged by rule 2: the game's, its rows UNBACKED); a walk into e24/e25 or another loss WITHOUT the evidence that lands (the landing judge: `door` named, the driver's). | game; driver after an unfinished walk or a loss without the evidence |
| V12 | A forbidden write the driver's own log backs. | driver |
| V13 | The budget; an instrument stop; outside input anywhere (S12); the name on the page not the default (S16: input at the naming screen, during `accept_name`'s blocking call); the north door's loss never read in 153 (S14: a read gap across the fade). | driver |
| V14 | The watchdog alone. | game |
| V19 | On F, a REAL field a member forks: 151, 153 or 154 (a route `Field()` the chain did not retarget), or -- after the north door's evidence held (S14's `left`) -- another, a real 150 or 64. A FINDING (`rerun.stop_on`). | game |

Every cell is `[place, sc, visit]` (S13): V4 in 151 is `[151, 1190, 1]`; V13 of the page witness `[151, 1190, 1]`; V4 /
V7 / V11 / V13 at the door `[153, 1190, 2]`; V19 on an arrival in a real 154 `[154, 1190, 2]`, and rule 2's V11 / V19
after S14's `left` `[place(landing), 1190, 2]` (rule 2 runs before the visit counts: the visit just left). V2,
V3, V6, V8, V9, V15-V18 cannot arise (no guarded or default-take choice, no watched cell, no wait_sc or climb, no
battle, no fight, no guard). A run whose drive raises a plain HarnessError (`accept_name` failing in rule 4: "the naming
screen stayed up through 4 Confirms") is "STOPPED" (unclassed) and the next `end_run` meets the screen: S15.

### 2.8 Recovery
- **From 154** (every covered run) and **from 153 mid-walk or mid-assembly**: `end_run` warps to 4600 (FieldHUD), then
  the ladder -- O5's path; R-WALK-VOID proves it from the walk (F7).
- **From 151 with the naming screen up** (a run stopped there): the warp is refused (`recover-warp-failed`); S15 accepts
  the screen AT ONCE, before any Cancel (`end-naming`), retries the warp to 4600 (`recover-warp-after-naming`) and climbs
  the ladder from there -- seconds; the first design's order (the ladder first) spent ~67 s in `close_ui` and the
  swallowed reset before it (0.2 #17). R-NAMING-VOID proves it and F6 records its time (F7).
- **The screen will not leave** (`accept_name` fails in `end_run`): `end-naming-failed`, the session stops cleanly
  (S15): no later run is driven against a stuck game; the analysis reads what was recorded -- VOID when a side is short
  of `min_covered`, else the covered runs' verdict.
- **The session's end** goes through `end_run` (`end_session_warps`), recorded in `session["ended"]`.

---

## 3. Harness additions (FakeGame only; each opt-in, modelled on the bytes, tested)

No change to `session.py`, `channel.py` or the agent. What is missing is a fake that (a) keeps the player moving after a
door takes control -- ExitField's walk-out -- so that `route_to` can return before OR after the switch (critique #1:
today's fake stops him dead, a check that cannot fail); (b) plays a naming screen INSIDE a scripted visit, and renders
the name on later pages; (c) can make the soft reset fail where O1d saw it fail; and (d) plays O6's route. Each choice
cites the byte or engine line it stands for; each knob's default is the engine's, or where unmeasured the design's named
estimate.

### 3.1 H16 -- a region's walk-out (`"walkout"` on a `regions` entry; PART A, A1)
A `fake.regions` entry gains an opt-in key `"walkout": {"to": [x, z], "speed": u, "stop_z": z | None}`. When the region
fires (`_enter_regions`, today: control off, `_coast` None, the exit scheduled `exit_frames` later), the walk-out is
armed: `self._walkout = {"to", "speed", "stop_z"}`; `_step_world` steps it each field tick of a frame while
`self._exit` is pending (before the control test that skips `_step_player`): he moves toward `to` at `speed` units a
tick (ExitField = `Call(po, movQData)`, DoEventCode.cs:860-869; movQData = CLRDIST, MOVJ, return, Obj.cs:60-67; MOVJ
moves him `actor.speed` a tick toward `sMapJumpX/Z`, EventEngine.MoveToward.cs:15-30, :166 -- the speed of his last
controlled frame, HonoUpdate's 60 for a run, FieldMapActorController.cs:210-211) and stops at `to`, or -- `stop_z`
given -- once his z passes it (a radius short of the floor's end, where pathing's ServiceChar holds him: 0.2 #6, an
ESTIMATE R-DOOR measures). `_step_exit_now` clears it (the field changes). Without the key: today's behaviour exactly
(stopped dead).
**The gate** (rev. 2, the driver critic's #3): `fake.exit_gate` -- a `threading.Event` the TEST holds, default None.
With it, a fired region's switch (`_step_exit_now`, H16) and a door's stores and `Field` (H18) wait, once their
`exit_frames` / `ticks` have run, until the event is set; he stands where the walk-out left him meanwhile. The path-A
tests release it from a log hook (a `list` subclass whose `append` sets the event when the door step's row is
appended): `route_to` has then returned, `left_for` has read the field still his, and the step is "done" with
`landed` None -- reproduced deterministically, never by real starvation (section 9's rule): without the gate a starved
harness thread could read the switch before `settle()` saw him still, take path B, still be "done" -- so nothing
re-runs -- and flip the test's `route.landed` assertion. Path B needs no gate (`stop_z` None: he never stands still
before the switch).
`_enter_regions`, `_step_world` and `_step_exit_now` are no G21 pins (FAKE_PINS / FAKE_PINS_O4 / FAKE_PINS_O5 name none
of them); every O1-O5 test that fires a region runs without the key and without the gate. Test (A1;
`REQUIRED_TESTS`): `test_segment_region_walkout_keeps_him_moving_until_the_flip_on_the_fake` (with the key he moves
`speed` a tick toward `to` from the fire to the switch, stops at `stop_z` when given, and the published `control` stays
False; with `exit_gate` held the switch waits, him standing at `stop_z`, until the event is set, then lands in one
frame; without the key, his position is frozen from the fire; breaks: no walk-out; ignore the gate). S14's fake tests
(1.2) use it: path A with `stop_z` a little past the firing line and the gate (he is still long before the switch, and
the switch cannot come before the step row), path B with `stop_z` None and `exit_frames` shorter than the walk (he is
moving when the field changes).

### 3.2 H16b -- fields that swallow the soft reset (`fake.reset_blocked_fields`, default empty; PART A, A2)
`_check_soft_reset` returns without resetting while `self.field_id in self.reset_blocked_fields` -- O1d's measurement (a
soft reset through Alexandria's running opening scene did not reach the title: PLAN.md O1, session story-o1d), the
stand-in for "a running scene there swallows it", whatever the engine's reason. Unpinned (`_check_soft_reset` is no
pin). Test (A2; `REQUIRED_TESTS`): `test_segment_reset_blocked_fields_swallow_the_combo_on_the_fake` (in a listed field
the combo does nothing; a warp out of it, then the combo: the title; break: ignore the set).

### 3.3 H17 -- the naming step and the name on the page (PART B, B1)
A visit step `{"naming": 3, "name": "Steiner"}` (`VISIT_STEP_KEYS["naming"] = ("name",)`): MENU (DoEventCode.cs:2317-2341)
-> `EventService.StartMenu(1, 3)` -> NameSettingUI, the box pre-filled with `name` (`CharacterDefaultName`,
NameSettingUI.cs:137-151) and focused. The script step sets `fake.ui_state = "NameSetting"` and lists no window; the
visit's script then stands still -- `_Machine.frame` runs `on_tick` only on FieldHUD (fakegame.py:3271: "a menu up holds
the field"), the engine's Menu blocking the script -- while `_VisitBeat.ui` (every frame) takes the screen's keys, the
fake's scene-beat naming rule (fakegame.py:2912-2922, NameSettingUI.cs:72-83, :107, :173): a Confirm going down while the
box is focused takes the focus off; the next is OK -- `fake.named.append(3)`, `fake.names[3] =` the name saved,
`fake.ui_state = "FieldHUD"`; a Cancel puts the focus back. The script resumes the tick the screen closes.
**The name on the page:** every window `_VisitBeat.open` lists has `[STNR]` in its TEXT replaced by `fake.names.get(3,
"Steiner")` (DialogBoxSymbols.cs:67-68; its raw keeps the tag, as `phrase_raw` does) -- the fake keeps `fake.names`
(new, empty: the default rendered) beside `fake.named`. Knobs (`VISIT_DEFAULTS`, strict): `name_typed` (str or None: the
name the OK saves -- a typed name's stand-in, outside input in the box: the page witness's V13), `naming_deaf` (int: the
screen drops its first k Confirms -- with k >= 4 `accept_name` raises, the stuck screen), `unparsed_frames` (rev. 2: a
dict `{mes: k}` -- that window publishes its RAW text, tags included, for its first k frames: the TextParser constructor's
`ParsedText = InitialText` before `Parse`, TextParser.cs:54-60, HarnessAgent.cs:1714-1720). The engine is expected
NEVER to publish that state -- `Dialog.Show` parses the constant tags at attach (0.2 #8; the driver critic, checked and
sound) -- so the knob tests the page witness's GUARD (only parsed windows are listed and judged), not a measured state;
R-DOOR counts any unparsed sample (F3). The pair's own lag is the builder's (3.6: 200 ~6 ticks after 199). Tests (B1;
`REQUIRED_TESTS_O6`):
`test_fake_naming_screen_takes_two_confirms` (NameSetting published with no window; Confirm 1 the focus, Confirm 2 OK;
the script resumes after it; `named` [3]; a Cancel between re-focuses; break: close on the first Confirm);
`test_fake_naming_holds_the_script` (a store step after the naming runs only after OK; break: tick the script while the
screen is up); `test_fake_naming_renders_the_name_on_later_pages` (a [STNR] page after it renders "Steiner", its raw the
tag; `name_typed` "Rusty": "Rusty"; `unparsed_frames` {that mes: 2}: the raw text for two frames, then the name, and a
sibling window without an entry parsed from its first frame; break: substitute in the raw too);
`test_fake_naming_deaf_screen_defeats_accept_name` (`naming_deaf` 9: `accept_name` raises after its 4 Confirms; break:
count a dropped Confirm).

### 3.4 H18 -- the door step: e23/e24/e25's tag 2, ExitField's walk-out, the stores, the Field (PART B, B1)
A visit step `{"door": knobs}` (`VISIT_STEP_KEYS["door"] = ()`; `DOOR_DEFAULTS = {"doors": (), "speed": 60.0}`), run per
field tick while he has control: the regions' tag 2 in ENTRY order (the engine runs region objects by entry: e23, e24,
e25), each door `{"name", "points", "z_gt"?, "stores", "ticks", "to", "walkout"?}` tested on his centre
(`doorface.region_contains(x, z, points)`, IsInQuad) and -- with `z_gt` -- z > `z_gt` (e23 t2 ip38's `f[2] > 1333`; its
`f[1] > -100` ground half is the floor-blind fake's ground, as O5's e26 model reads it). The first hit FIRES: control off
(ExitField ip59), `_coast` None, a `visit_log` row "door" (name, x, z); then for `ticks` ticks (e23: **25** = ip153
`op_22(25)`; ip95's `op_22(1)` is skipped -- ip68's `Map.Bit[159] == 1`, set by Main_Init ip2356, and ip80's
`Map.Bit[144] == 0`, never written in 153, take ip91 `DisableMenu()` and ip92 `JMP(L68)`: rev. 2, the claim critic's
#7; e24 and e25 are the same shape, 25 too) the walk-out -- with `walkout` `{"to": [x, z], "stop_z": z | None}`,
toward `to` at `speed` a tick (his run's 60, kept from his last controlled frame: HonoUpdate, FieldMapActorController.cs
:210-211; MOVJ at `actor.speed`), stopping at `to` or past `stop_z` -- then, the gate (`fake.exit_gate`, H16) set or
absent, the door's `stores` (e23: `[23, 2, 203, 2, "Int16", 315, -1]`) and `_field(to)` in the same tick (ip203 then
ip211, no wait between). Without `walkout` he stands still from the fire. `land_real` applies to the door's Field (it
reads `_field`'s map). The builder's e23: `walkout` {"to": [-31, 3000] (MJPOS's projection onto e23's first edge,
DoEventCode.cs:2247-2275, for the planned crossing; the pressed path's crossing at x -50 to -90 projects within 60 u of
it, immaterial to a fake that judges only z), "stop_z": **2065** (rev. 2, the driver critic's #2: the open floor's end
on his line, z 2150-2200, less his radius 120 -- pathing's ServiceChar holds his centre there, 0.2 #6; the first
design's 2185 was the floor's end itself, an ESTIMATE either way)} -- ~12 ticks of walk-out, then still ~13: path A at
the default; tests take `stop_z` None for path B. e24 and e25 carry their stores (`[24, 2, 183, 2, "Int16", 315, -1]`;
`[25, 2, 195, 2, "Int16", 315, -1]`), `ticks` 25, and land in "150" / "64" (a wrong door's stand-ins). Tests (B1;
`REQUIRED_TESTS_O6`):
`test_fake_door_fires_only_past_its_line` (inside e23's quad at z 1000: nothing; past z 1333: the fire, control off;
break: drop `z_gt`); `test_fake_door_walkout_then_stores_then_field` (the walk-out's samples move north `speed` a tick to
`stop_z`, then still; the store the tick of the switch, the field `to` after `ticks` (25); with `exit_gate` held, the
store and the field wait for it; break: store at the fire);
`test_fake_door_walks_out_until_the_flip_without_stop` (`stop_z` None: moving every tick until the switch);
`test_fake_door_entry_order_and_misroute` (in two quads at once the lower entry fires; H19's `door_misroute` sends e23's
Field to "150").

### 3.5 H19 -- O6's faults (each absent by default)
`name_typed`, `naming_deaf`, `unparsed_frames` (H17); `door_misroute` (`{door name: field_to key}`: the door's Field
lands elsewhere -- the stand-in for a misrouted fork operand or engine: S14's `left`, rule 2's V11 (game), or V19 with
`land_real`). Reused from H15 unchanged: `land_real` (`{to: id}`: a Field
landing in the REAL id, V19), `grant_at` (`{visit index: [x, z]}`: control in 151, V4), `error_window` (`{visit index:
value}`: Byte[13] arrived 2 -- the leading stores take `VISIT_ERROR_STORE` (ip97: 151's and 153's error store sit at the
same ip) and window 56 waits: V5), `store_override` (`{ip: value}`: a fork storing another value -- ip610 9, a
start-dependent value changed on one side). Test-side, not knobs: a stalled publication (`fake.stall_publish`) across the
door's fade (S14's V13), the held `fake.exit_gate` (path A, H16), a stub witness, a wrapped `g.accept_name`
(R-NAMING-VOID's stop; S15's failure), a wrapped `g.send` (R-WALK-VOID's stop).

### 3.6 The O6 route builder (test-side `_o6_route(side, *, e15_late=False, walkout_stop=2065, short=False, wait_scale=0.25, **faults)`)
Three visit beats from the bytes (`stages151.out`, `stages153_328.out`; slots as the scripts open them). Window TEXTS
are placeholders (`"151 mes 177"`, raw `"[STRT=0,0]151 mes 177"`), each distinct, except where the driver or a check
matches: 198 holds "And, Captain" (raw `[STRT=0,0]Queen Brahne\n“And, Captain[SPED=2]...[SPED=-1]uh[SPED=2]...[SPED=-1]”`);
199 / 200 / 203 / 211-214 / 217-219 / 221 / 222 carry block 3's [STNR] sources as raws and the same with `[STNR]` as
texts (H17 renders them); window 56 holds "Env Play()". Fixture fields `_O6_FIELDS`: S {"151": 30810, "153": 30820,
"154": 30821, "150": 30830, "64": 30831}, F {"151": 31244, "153": 31245, "154": 31246, "150": 31243, "64": 31240}; a
test-side `_o6_register(game)` (`_o5_register`'s shape) registers 30830, 30831 and the five F ids under `_O6_NAMES`
({"31240": "O6_AST", "31243": "O6_HALL", "31244": "O6_SEAT", "31245": "O6_H2F", "31246": "O6_ENT"}); members {31244:
30810, 31245: 30820, 31246: 30821, 31243: 30830, 31240: 30831}. Floor: O5's box `(-2400, -2400, 3000, 3200)` (it covers
the walk). Field 70's prologue values poked before the trace is armed (`_o5_field70`, reused: Int16[9] 643, Byte[13] 1,
Int16[11] -1, Byte[14] 0, Byte[8] 125).
- **151@110:** stores e0 t0 ip22, 49, 57, 119, 138, 200 (`_o5_prologue`); wait 10 (the BGM wait ip274-294); store ip315
  `Byte[8] := 125`; timed 175 (slot 2, 20), wait 15, timed 176 (3, 20), wait 50, page 177 (4); pages 178 (1), 179 (3),
  180 (2), 181 (1); pair [[182, 2], [183, 3]] lag 2 gate 40; pages 184 (4), 185 (1), 186 (2), 187 (3); pair [[188, 2],
  [189, 3]]; page 190 (1); wait 90 (stage 13); pages 191 (0), 192 (1), 193 (0, typing 0.3), 194 (1), 195 (0, typing
  0.3); pair [[196, 0], [197, 1]]; page 198 (0, typing 0.5); wait 5; `{"naming": 3, "name": "Steiner"}`; wait 10; store
  e3 t1 ip610 `Byte[6] := 8`; wait 10; pair [[199, 0], [200, 4]] lag 6 (rev. 2: e3's `op_22(1)` before 199, e12's
  `op_22(7)` and RunAnimation before 200 -- the claim critic's #2 (iv); texts and raws as above); page 201 (0); pair
  [[203, 4], [202, 1]]; store e2 t1 ip735 `Byte[8] := 0`; wait 65; store e2 t1 ip932 `Int16[2] := 328`; field "153".
- **153@328:** stores e0 t0 ip22, 49, 57, 119, 138, 200; wait 10; store e32 t0 ip718 `Bit[3855] := 1`, ip727 `Bit[3854]
  := 1`; place (-24, -2078); wait 20; page 211 (4); wait 20; page 212 (4); wait 15; store e15 t0 ip32 `Byte[8] := 125`
  (the Seq row: ~45 ticks after ip866; `e15_late` moves it after ip1006, "the order flipped"); wait 25; pages 213 (4),
  214 (4), 215 (5), 216 (6); store ip971 `Byte[208] := 0`, ip1006 `:= 1`, page 217 (4); store ip1041 `:= 0`, ip1076 `:= 1`,
  page 218 (4); places (-150, -550), (-1235, -558), (-1595, -195), (-1370, 804), (-575, 807), (-245, 42) each after a wait
  of 10; wait 70 (stage 45's waits); pages 219 (4), 221 (4); store ip1597 `:= 0`, ip1632 `:= 1`, page 222 (4); stores
  ip1656 `UInt16[21] := 8`, ip1741 `Byte[303] := 0`, ip1775 `:= 1`, ip2172 `Byte[4] := 0`, ip2206 `UInt16[19] := 8`,
  ip2232 `Byte[4] := 0`, ip2240 `Byte[17] := 0`, ip2248 `Byte[18] := 1`; grant (-245, 42); door {e23 (its quad, z_gt
  1333, its store, ticks 25, to "154", walkout {to (-31, 3000), stop_z `walkout_stop`}), e24 (its quad, its store, ticks
  25, to "150"), e25 (its quad, its store, ticks 25, to "64")}.
- **154@315:** stores e0 t0 ip26, 53, 61, 123, 142, 204; wait 100000 (the end: rule 1 reads its first poll).
- `short`: 153@328 alone from the grant (its prologue, the grant, the door) -- the walk's tests that need no 151.
The stores are the predictions' sites (C1's `test_o6_steiner_route_builder_matches_the_keys` compares the builder's store
list with the draft's writes, chain, masked and start rows, and the builder's trace under `story_suppress` with the
draft's `pattern`: one source of truth).

---

## 4. Predictions (draft v1: `O6Segment.draft()`)

### 4.1 Top level
```json
{"version": 1,
 "what": "O6: 151@1190 (warp, entrance 110; EVT_ALEX1_AC_SEAT_R) -> Steiner's naming -> 153@328 (EVT_ALEX1_AC_H2F; the Knights of Pluto) -> Steiner's first control, the walk to the north door -> Field(154) at 315 (EVT_ALEX1_AC_ENT_2F), SC 1190; stock vs the alxc disc-1 chain as O4 deployed it (route members 31244-31246; PLAN.md, O6) -- a US session",
 "rehearsals": [],
 "order": ["S", "F", "S", "F", "S", "F"], "min_covered": 2, "rerun": {"max": 2, "stop_on": ["V19"]},
 "budget": {"run_s": 600, "run_min_s": 300, "session_s": 3600, "settle_s": 1.0, "no_progress_s": 60, "end_row_s": 10.0},
 "start": {"S": 151, "F": 31244}, "entrance": 110, "scenario": 1190, "lang": "us",
 "end_field": 154, "end_fields": [154], "side_ends": {"S": [154], "F": [31246]},
 "route": [151, 153], "visits": [151, 153], "stock_fields": [151, 153, 154],
 "members": {"31240": 64, "...": "...", "31259": 167}, "names": {"31240": "O4_AC_AST", "...": "..."},
 "text_block": 3, "text_blocks": [3], "recovery": 4600, "cut_start": true,
 "start_first": "4.7", "start_music": "4.7", "start_residue": [[0, 0, 166], [1, 0, 4], [2, 0, 110]],
 "residue_after_start": [], "sc_bytes": [0, 1], "ladder": [], "entrance_bytes": [2, 3], "chain": "4.3",
 "writes": "4.4", "start_dependent": "4.5", "error_path": "4.6", "forbidden_sites": "4.6", "dead": "4.6",
 "inert": "4.6", "live_shared": "4.6", "noise": [], "forbidden": "4.9", "landing": "5.3",
 "end_state": "4.10", "naming": "4.11", "name": "4.11", "walk": "4.12", "beats": ["named", "name_on_page", "steiner_door"],
 "battles": [], "stop_pages": ["2.1"], "regions": "4.17", "hotspots": {}, "table": ["2.5"], "steps_default": "4.17",
 "choices": ["2.1"], "witness": "4.13", "route_pins": "4.16", "route_mes": "4.16", "route_build": "6.1",
 "pattern": "4.18", "settings": "4.15", "override70": "4.15", "derived": "4.15", "engine": "4.15"}
```
- `members`/`names` are O4's twenty (`chain_from_campaign` on O4's `campaign.toml`); `route_members` over 151, 153, 154
  derives 31244, 31245, 31246 (printed by `--offline-check`, never assumed). P-DEPLOY, P-EB, P-FLOOR and the fingerprint
  read all twenty.
- `start_residue` THREE rows (0.2 #1); `ladder` [] with `sc_bytes`: O6-NO-SC is O3's `no_sc_check`.
- `route_build` is O5's exactly (the same three members, their 16 in-chain Field() operand sites: 6.1).

### 4.2 No SC rung
No store to SC's bytes in any width in 151, 153 or 154 (the census, 6.1); the reads -- 151 e0 t0 ip461 (`SC < 12000`:
true, camera 0 and SPS) and 153 e0 t0 ip232 (`SC > 1900`: false) -- take the same branch from the raw warp and from O5's
end (both 1190).

### 4.3 The FieldEntrance chain (`Global.Int16[2]`; O6-CHAIN; the first `old` is 110, the warp's entrance)
| # | donor | sid | tag | ip | off | value | what |
|---|---|---|---|---|---|---|---|
| 1 | 151 | 2 | 1 | 932 | 921 | 328 | stage 23, then `Field(153)` ip940 |
| 2 | 153 | 23 | 2 | 203 | 173 | 315 | the north door (e23 t2), then `Field(154)` ip211 |

### 4.4 Registered writes (O6-WRITES: every covered run's keys are EXACTLY these and the chain)
| donor | sid | tag | ip | off | target | value | op | what |
|---|---|---|---|---|---|---|---|---|
| 151 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient (from 643) |
| 151 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (from 1: `start_music`) |
| 151 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | ambient (same) |
| 151 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | ambient (same) |
| 151 | 0 | 0 | 315 | 309 | Byte[8] | 125 | := | after the BGM wait (same: field 70 left 125) |
| 151 | 3 | 1 | 610 | 426 | Byte[6] | 8 | \|= (prior newgame0) | after `Menu(1, 3)`: **START-DEPENDENT** (4.5) |
| 151 | 2 | 1 | 735 | 724 | Byte[8] | 0 | := | stage 23 |
| 153 | 0 | 0 | 57 | 51 | Int16[9] | -1 | := | ambient (same, EMITTED: a new site) |
| 153 | 0 | 0 | 119 | 113 | Byte[13] | 0 | := | ambient (same) |
| 153 | 0 | 0 | 138 | 132 | Int16[11] | -1 | := | ambient (same) |
| 153 | 0 | 0 | 200 | 194 | Byte[14] | 0 | := | ambient (same) |
| 153 | 32 | 0 | 718 | 700 | Bit[3855] | 1 | := | Steiner's t0 at 328 |
| 153 | 32 | 0 | 727 | 709 | Bit[3854] | 1 | := | Steiner's t0 at 328 |
| 153 | 15 | 0 | 32 | 26 | Byte[8] | 125 | := | **the shared script** (Seq, run by e32 t1 ip866) |
| 153 | 32 | 1 | 971 | 234 | Byte[208] | 0 | := | stage 43, 217's loop (same) |
| 153 | 32 | 1 | 1006 | 269 | Byte[208] | 1 | ++ (prior 153/32/1/971) | stage 43 |
| 153 | 32 | 1 | 1041 | 304 | Byte[208] | 0 | := | 218's loop |
| 153 | 32 | 1 | 1076 | 339 | Byte[208] | 1 | ++ (prior 153/32/1/1041) | |
| 153 | 32 | 1 | 1597 | 860 | Byte[208] | 0 | := | stage 48, 222's loop |
| 153 | 32 | 1 | 1632 | 895 | Byte[208] | 1 | ++ (prior 153/32/1/1597) | |
| 153 | 32 | 1 | 1656 | 919 | UInt16[21] | 8 | := | the rebuild: the party mask (Steiner) |
| 153 | 32 | 1 | 1741 | 1004 | Byte[303] | 0 | := | (same) |
| 153 | 32 | 1 | 1775 | 1038 | Byte[303] | 1 | ++ (prior 153/32/1/1741) | |
| 153 | 32 | 1 | 2172 | 1435 | Byte[4] | 0 | := | PARTYCHK(5) false (same) |
| 153 | 32 | 1 | 2206 | 1469 | UInt16[19] | 8 | \|= (prior newgame0) | ip2180's bit-3 guard true: **START-DEPENDENT** (4.5) |
| 153 | 32 | 1 | 2232 | 1495 | Byte[4] | 0 | := | (same) |
| 153 | 32 | 1 | 2240 | 1503 | Byte[17] | 0 | := | (same) |
| 153 | 32 | 1 | 2248 | 1511 | Byte[18] | 1 | := | 0 -> 1 |

28 writes + 2 chain = **30 keys a run**, beside the masked prologue rows (Bit[191] and Bit[184] at 151 and 153: ip22,
ip49; `boot_scratch`, `field_menu_guard`). Every key's `m` 1, `src` "eb". EXACT for O5's reason: the key set is small and
fully enumerated by the bytes (O6-CENSUS classifies every store site of 151 and 153; O6-KEYS proves every listed site);
R-DOOR must show the exact set before the freeze (F4).

### 4.5 Start-dependent keys (O2's 4.5 shape; decision 5)
These are compared stock against fork like any key; both sides start alike. They are declared so that no reader takes
O6's value for the value an O1-O6 play writes:
```json
[{"donor": 151, "m": 1, "src": "eb", "sid": 3, "tag": 1, "ip": 610, "off": 426, "target": "Global.Byte[6]", "value": 8,
  "op": "|=", "prior": "newgame0",
  "after": {"run": "O1-O5", "old": 3, "value": 11,
            "source": "old READ at design time from the story-o1e (all six runs) and story-o2 S traces, the routes as driven (o6_design.md 0.2 #9); story-o3/-o4/-o5 hold no row on byte 6",
            "why": "Byte[6] |= 1 at 50 e17 t1 ip3240 (O1, Zidane's naming) and |= 2 at 116 e2 t1 ip765 (O2, Vivi's); O3-O5 write it nowhere (their traces hold no row on byte 6)"},
  "what": "151 Byte[6] |= 8 after Menu(1,3) (Steiner's naming): 0 -> 8 on New Game's 0"},
 {"donor": 153, "m": 1, "src": "eb", "sid": 32, "tag": 1, "ip": 2206, "off": 1469, "target": "Global.UInt16[19]",
  "value": 8, "op": "|=", "prior": "newgame0",
  "after": {"run": "O1-O5", "old": 1799, "value": 1807,
            "source": "old READ at design time from the story-o1e (all six runs) and story-o2 S traces, the routes as driven (o6_design.md 0.2 #9); story-o3/-o4/-o5 hold no row on bytes 19-20",
            "why": "O1 leaves 1797 (50 e17 t1 ip1629/1667, e13 t1 ip1149/1187/1225: 0 -> 1 -> 5 -> 261 -> 773 -> 1797), O2 |= 2 at 100 e19 t1 ip1531 -> 1799; O3-O5 write it nowhere; bit 3 is clear in both, so ip2180's guard takes the same branch"},
  "what": "153 UInt16[19] |= 8 in Steiner's rebuild: 0 -> 8 on New Game's 0"}]
```
Both are also rows of 4.4 at these values, so O6-WRITES and O6-NULL judge them. O6-KEYS computes `value` from `prior` and
the statement's constant, and `after.value` from `after.old` the same way (3 | 8 = 11, 1799 | 8 = 1807); `after.old`
itself is NOT computed (rev. 2, the claim critic's #4: the first design's "a typed number is never trusted" overstated
it) -- it is READ, from the story-o1e and story-o2 S traces at design time, and `after.source` says so: the routes AS
DRIVEN (O2-O5 each from a raw start) composed with the bytes' `|=`, never a measured chained play. O6-KEYS requires
`after.run` to equal the class's `AFTER_RUN` ("O1-O5"; O7's subclass overrides it) and `after.source` to be present.
O6-START-DEPENDENT (5.3) classifies each one's `old` and `new` per run; the report prints them with `after` under 5.4's
scope line, its span RENDERED from `after.run` -- "after the O1-O5 routes as driven it would write 11 (from 3)" --
never a literal, never O2's "after O1".

### 4.6 The error path, the forbidden sites, the dead sites, the inert functions, the live shared entry (registered; never expected)
- `error_path` (an incoming Byte[13]/[14] of 2 or 9; each `:=`): 151 e0 t0 ip97/91 `Byte[13] := 9`, ip178/172 `Byte[14]
  := 9`, ip960/954 `Byte[13] := 0`, ip994/988 `Byte[14] := 0` (window 56's resets); 153 e0 t0 ip97/91, ip178/172,
  ip2314/2308, ip2348/2342 (the same four). A 151 row is the start's fault (A-START, V5 driver); a 153 row the game's.
- `forbidden_sites` (what a walk into another door at 328 writes, before that door's Field): 153 e24 t2 ip183/153
  `Int16[2] := 315` (-> 150); e25 t2 ip195/165 `Int16[2] := 315` (-> 64), ip222/192 `Byte[8] := 0` and ip421/391
  `Int16[2] := 315` (upstairs with z < -1400 -> 151).
- `dead` (each with why false on the route): 151 e0 t0 ip41/35 `Int16[2] := 10000` (behind `Bit[184] == 1`), ip130/124
  `Byte[13] := 1` and ip211/205 `Byte[14] := 1` (the else of `Int16[9] < 0` / `Int16[11] < 0`, just set -1), ip410/404
  `Byte[8] := 125` (the default entrance's branch L340), e3 t3 ip909/61 `Bit[3793] := 1` (Brahne's talk handler: she is
  the defined player at 110 and no control exists there, 0.2 #3); 153 e0 t0 ip41/35, ip130/124, ip211/205 (the same three
  shapes), ip243/237 `Int16[2] := 3` (behind ip232 `SC > 1900`), ip1188/1182 and ip1260/1254 `Byte[8] := 125` (L1098,
  skipped by ip802 `JMP(L1288)` at 328), e32 t1 ip1797/1060, ip1819/1082, ip1841/1104 `Byte[303] ++` (behind `const(0)`
  tests; values 2, 3, 4 from their priors 1775, 1797, 1819), ip2161/1424 `Byte[4] := 1` (behind `PARTYCHK(5)`: false,
  the party [Steiner] after the rebuild).
- `inert` (FUNCTION-level, proven by `instanced_at6` at the field's route entrance, 6.1): `{"donor": 151, "sid": 8,
  "tags": "*"}` (region 8: InitRegion(8) only on L340); `{"donor": 153, "sid": s, "tags": "*"}` for s in 3 (325 and the
  default), 18 (316), 28 (325).
- `live_shared` (NEW, the critic's #3): `[{"donor": 153, "sid": 15, "callers": [[32, 1, 866]], "why": "entry 15 is a
  shared script with no instance of its own: e32 t1 ip866 RunSharedScript(15) runs it (STARTSEQ, DoEventCode.cs:1414-1421),
  and e32 IS instanced at 328 -- so its ip32 Byte[8] := 125 is a writes key, its row sid 15, uid 96, tag 0, ip 32, add 0"}]`.
  O5 registered the same entry `inert`, `shared_by` [32] -- correct at 325 and 316, wrong at 328.

### 4.7 The start (O6-START)
```json
"start_first": {"donor": 151, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 22, "off": 16, "target": "Global.Bit[191]",
                "value": 0, "op": ":=", "what": "151's Main_Init: its first store (emitted same: a new site)"},
"start_music": {"donor": 151, "m": 1, "src": "eb", "sid": 0, "tag": 0, "ip": 119, "off": 113, "target": "Global.Byte[13]",
                "value": 0, "op": ":=", "old": 1,
                "what": "151's ambient branch from the warp's Byte[13] 1 (field 70's prologue :=1 at ip130; the warp leaves 70 before ip475's :=2)"}
```
The warp window and `old: 1` are O2-O5's (twenty-one runs measured the same start), under the override P-OVERRIDE pins. A
2 would take ip97 and window 56: A-START (V5, driver).

### 4.8 Noise: none
No `SYSVAR[0]` read in 151, 153 or 154; no battle, no ATE, no choice; the walk's path writes nothing (2.5); the e15 row's
POSITION races, its key does not (4.18). `noise: []`: NULL and STABLE set nothing aside.

### 4.9 Forbidden
```json
[{"off_route": true, "cause": "walk",
  "why": "a write off the route: S, a place outside [151, 153] + [154]; F, a field that is neither a member whose donor is on the route nor F's own end field (real 151/153/154 on F: an un-retargeted Field() or an engine id leak; 150/31243 or 64/31240 after a walk into e24/e25, backed by its V11 step row)"}]
```
No door pattern (O5's 0.2 #13: e24's and e25's tag 2 run their `Field()` right after their stores, so a run that wrote
them lands off the route, where `off_route` hits; a driver walk is backed by its V11 step row, a fork's would not be; a
covered run cannot hold them: WRITES exact). No `choice` pattern (no choice).

### 4.10 End state (read live on arrival in 154 / member(154); O6-STATE (b))
```json
{"Global.UInt16[0]": 1190, "Global.Int16[2]": 315, "Global.Byte[6]": 8, "Global.Byte[8]": 125,
 "Global.Bit[3855]": 1, "Global.Bit[3854]": 1, "Global.Byte[208]": 1, "Global.UInt16[21]": 8, "Global.Byte[303]": 1,
 "Global.Byte[4]": 0, "Global.UInt16[19]": 8, "Global.Byte[17]": 0, "Global.Byte[18]": 1,
 "Global.Byte[13]": 0, "Global.Byte[14]": 0, "Global.Int16[9]": -1, "Global.Int16[11]": -1,
 "Global.Bit[191]": 0, "Global.Bit[184]": 0,
 "Global.Bit[3795]": 0, "Global.Bit[3793]": 0, "Global.Byte[475]": 0, "Global.Bit[3815]": 0, "Global.Bit[3717]": 0,
 "Global.Bit[3718]": 0, "Global.Int16[469]": 0, "Global.Byte[472]": 0, "Global.Byte[206]": 0, "Global.Bit[3796]": 0,
 "Global.Bit[3811]": 0, "Global.Bit[3852]": 0}
```
Nineteen the route leaves, twelve untouched since New Game (O5's choice bit and O7's: 159's Bit[3796], 164's Bit[3811],
154's Dojebon talk Bit[3852]). `Byte[8]` IS here (unlike O5): 154@315 stores no `Byte[8]` (0.2 #13), so the live read
cannot race; its whole history is also frozen by O6-PATTERN (b) (151 ip315 125, ip735 0, 153 e15 ip32 125).

### 4.11 The naming (the driver's registration and the analysis's claim)
```json
"naming": [{"donor": 151, "sc": 1190, "beat": "named",
            "on_page": {"tag": "[STNR]", "beat": "name_on_page",
                        "windows": [{"mes": 199, "raw_holds": "“Captain [STNR]!”", "line": 1, "text": "“Captain Steiner!”"},
                                    {"mes": 200, "raw_holds": "[STNR]\n“Yes, Your Majesty!”", "line": 0, "text": "Steiner"}],
                        "why": "PLAYER.Name is no gEventGlobal store: the first parsed page rendering [STNR] after the screen is the name's only witness (0.2 #8); the driver judges it (V13 on another name), O6-NAMING (b) re-checks it"}}],
"name": {"place": 151, "char": 3, "default": "Steiner",
         "before": {"mes": 198, "marker": "And, Captain"},
         "store": {"place": 151, "sid": 3, "tag": 1, "ip": 610, "target": "Global.Byte[6]"},
         "why": "151 e3 t1: 198 (WaitWindow ip590), ip603 Menu(1,3), ip610 Byte[6] |= 8; stage 21 opens 199, then 200 ~6 ticks later"}
```
The frozen windows live ONCE, in the driver's registration (rev. 2, the claim critic's #2: the driver judges with them,
O6-NAMING re-reads the same entries; the first design kept them in `name.on_page`, where only the analysis could use
them). Each window's `text` is COMPUTED, never typed: the mes line `line` of block 3's source with `[STNR]` replaced by
`name.default` and every `[...]` tag removed (O6-KEYS checks the frozen text equals it, and that the source holds
`raw_holds`); R-DOOR measures the rendered lines before the freeze (F3) -- a difference stops the freeze for an
engine-level explanation, never a loosened compare. `name.before.marker` stays the analysis's: A-NAMING (5.1) reads the
`named` row's `before` against it.

### 4.12 The walk
```json
"walk": {"name": "the north door", "donor": 153, "visit": 2, "door": "153.e23",
         "why": "153 e23 t2 ip38: on the ground (f[1] > -100) and past z 1333 takes control (ExitField ip59); the loss sample is read at or north of the line (the walk-out walks north); THE PAIRED-WALK LAW: nothing stores between ip2412 and the loss"}
```
The door's test is READ from its pinned text (`door_test`: ground -100, threshold 1333), never typed here (O6-GOALS
(c'')). **The slack the `until` may admit is DERIVED, never typed** (rev. 2, the claim critic's #8: the first design's
`stale_slack` 160 was justified only in prose -- and its own "two ticks of his run plus a tick's publication lag" made
180, not 160 -- and (c'') would have admitted any threshold down to 1333 - `stale_slack`, so a frozen 500 let the
"until z_gt 900" mutant pass): `STALE_TICKS` 3 x `RUN_U_PER_TICK` 60 = **180 u** -- his run's speed under control
(HonoUpdate, FieldMapActorController.cs:210-211), times two ticks the published position may trail the engine's (the
agent's Update can run before the actors' in a frame, settle's own note, session.py:1814-1817, and a slow or hitched
frame holds two ticks) plus the tick in which the fire takes control. Both are o6_steiner constants (1.3); a `walk`
carrying a typed `stale_slack` is REFUSED by O6-GOALS (c'') and by `freeze`. F1 cross-checks the derivation on R-DOOR's
loss samples: every loss at published z >= 1333 - 180 = 1153, else the freeze stops.

### 4.13 Coverage beats, the input witness
Beats `named` (rule 4's registration), `name_on_page` (S16's row, `verdict` "ok"), `steiner_door` (the door step's
`done`); plus `end == "reached"`. O6-NAMING and O6-WALK re-read them from the rows. `witness` (S12): `{"input_every_s":
0.05, "why": "the naming screen keeps what a keyboard types and PLAYER.Name is no gEventGlobal store: outside input
would save another name while the driver accepts the default -- the run-wide witness VOIDs a run that sees input
between blocking calls (V13), and S16's page witness VOIDs one whose page renders another name (V13): a key typed during
accept_name's blocking call"}`.

### 4.14 Budget and recovery
Estimated ~100-130 s a run (0.2 #21). Drafts: `run_s` 600, `run_min_s` 300, `session_s` 3600, `settle_s` 1.0,
`no_progress_s` 60 (a KEYON gate is <= 8.3 s; the naming's Confirms <= 8 s inside one blocking call), `end_row_s` 10.
F6 replaces every one from R-DOOR. Recovery is `end_run` with S15 (2.8); the session ENDS through it
(`end_session_warps`).

### 4.15 Settings, the New-Game override, the engine, the derived facts
O4's frozen values, unchanged (as O5's): `settings` (28 keys: [Battle], [Cheats], [Hacks] incl. `DisableNameChoice` 0 --
decision 4's pin -- [Control] incl. `AlwaysCaptureGamepad` 1 and `SwapConfirmCancel` 0, [Graphics] `FieldTPS` 30),
`override70` {FF9CustomMap-world: 2ce8887e...}, `engine` {x64, x86: ba976242...}, `derived` (cfg.control 0, 30 ticks a
second). `freeze` refuses an engine that is not the live DLLs'.

### 4.16 The route pins (O6-KEYS (b): the bytes the driver, the naming, the walk and the FakeGame rest on)
`route_pins`, each `[donor, sid, tag, ip, eb-src text]`, compared EXACTLY with the stock US script's instruction text (74
pins -- the first design's 65 plus rev. 2's nine: e23 t2's ip68-ip92 path that skips ip95, Main_Init's ip2356 and e32
t0's ip548 -- each verified against the stock US listing while designing):
| what | site | text |
|---|---|---|
| 151's dispatch (0.2 #2) | 151 e0 t0 ip232, 240 | `SET({Global.Int16[2] const(110) B_EQ B_EXPR_END})`, `JMP_IFNOT(L340)` |
| 151's SC read | 151 e0 t0 ip461 | `SET({Global.UInt16[0] const(12000) B_LT B_EXPR_END})` |
| 151 grants no control | 151 e0 t0 ip1010; e3 t0 ip171; e12 t0 ip149 | `SET({Map.Bit[158] const(1) B_EQ B_EXPR_END})`, `DefinePlayerCharacter()`, `SWITCH(110, L159, L147)` |
| the pairs | 151 e4 t1 ip516, 693; e3 t1 ip475, 742; e12 t1 ip935 | `SET({const4(131072) B_KEYON B_NOT const4(524288) B_KEYON B_NOT B_ANDAND B_EXPR_END})` (O4's `PAIR_TEXT`) |
| 198 | 151 e3 t1 ip576, 590 | `WindowAsync(0, 128, 198)`, `WaitWindow(0)` |
| the naming | 151 e3 t1 ip593, 603 | `SetCharacterData(3, 0, 3, 5, 3)`, `Menu(1, 3)` |
| the first start-dependent store | 151 e3 t1 ip610 | `SET({Global.Byte[6] const(8) B_OR_LET B_EXPR_END})` |
| the page witness's windows | 151 e3 t1 ip693; e12 t1 ip803 | `WindowAsync(0, 128, 199)`, `WindowSync(4, 128, 200)` |
| 151's exit | 151 e2 t1 ip932, 940 | `SET({Global.Int16[2] const(328) B_LET B_EXPR_END})`, `Field(153)` |
| 153's SC read, dispatch | 153 e0 t0 ip232, 255 | `SET({Global.UInt16[0] const(1900) B_GT B_EXPR_END})`, `SWITCHEX(L1098, 325, L273, 5, L438, 328, L603, 316, L799, 3, L951)` |
| the regions at 328 | 153 e0 t0 ip626, 629, 632 | `InitRegion(23, 0)`, `InitRegion(24, 0)`, `InitRegion(25, 0)` |
| L1098 skipped | 153 e0 t0 ip802 | `JMP(L1288)` |
| Steiner at 328 | 153 e32 t0 ip22, 520, 717 | `SWITCH(324, L383, L140, L383, L383, L59, L24, L221, L302)`, `SetObjectLogicalSize(30, 35, 50)`, `DefinePlayerCharacter()` |
| his pathing: the walk-out held a radius short of the floor's end (rev. 2, 0.2 #6) | 153 e32 t0 ip548 | `SetPathing(1)` |
| the shared script | 153 e32 t1 ip866; e15 t0 ip6, 32 | `RunSharedScript(15)`, `op_22(45)`, `SET({Global.Byte[8] const(125) B_LET B_EXPR_END})` |
| the stair walk's speed (stage 44; NOT the walk-out's: HonoUpdate rewrites his speed on every controlled frame -- rev. 2, 0.2 #6) | 153 e32 t1 ip1160 | `SetWalkSpeed(60)` |
| the grant's place | 153 e32 t1 ip1360, 1367 | `Walk(64961, 807)`, `Walk(65291, 42)` |
| the rebuild's guards | 153 e32 t1 ip2152, 2180 | `SET({const(5) B_PARTYCHK B_EXPR_END})`, `SET({Global.UInt16[19] const(3) B_SHIFT_RIGHT const(1) B_AND const(0) B_EQ B_EXPR_END})` |
| the second start-dependent store | 153 e32 t1 ip2206 | `SET({Global.UInt16[19] const(8) B_OR_LET B_EXPR_END})` |
| the grant | 153 e32 t1 ip2382, 2390, 2401, 2412 | `SET({Map.Bit[158] const(1) B_LET B_EXPR_END})`, `SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})`, `SET({Map.Bit[156] const(0) B_EQ B_EXPR_END})`, `EnableMove()` |
| e23 (the door) | 153 e23 t2 ip30, 38, 58, 59, 95, 153, 203, 211 | `SET({B_SYSVAR[2] B_EXPR_END})`, `SET({obj(uid=250).f[1] const(65436) B_GT obj(uid=250).f[2] const(1333) B_GT B_ANDAND B_EXPR_END})`, `CalculateExitPosition()`, `ExitField()`, `op_22(1)` (SKIPPED on the route: the next row's tests), `op_22(25)` (the fade's 25 ticks), `SET({Global.Int16[2] const(315) B_LET B_EXPR_END})`, `Field(154)` |
| why ip95 is skipped: the fade is 25 ticks, not 26 (rev. 2, the claim critic's #7) | 153 e23 t2 ip68, 76, 79, 80, 88, 91, 92; 153 e0 t0 ip2356 | `SET({Map.Bit[159] const(1) B_EQ B_EXPR_END})`, `JMP_IFNOT(L68)`, `DisableMove()`, `SET({Map.Bit[144] const(0) B_EQ B_EXPR_END})`, `JMP_IFNOT(L65)`, `DisableMenu()`, `JMP(L68)`; Main_Init's tail `SET({Map.Bit[159] const(1) B_LET B_EXPR_END})` -- and O6-KEYS scans 153's whole script: NO store to `Map.Bit[144]` (its 26 references all `B_EQ` tests), so ip80's test holds |
| e24 | 153 e24 t2 ip30, 183, 191 | `SET({B_SYSVAR[2] B_EXPR_END})`, `SET({Global.Int16[2] const(315) B_LET B_EXPR_END})`, `Field(150)` |
| e25 | 153 e25 t2 ip30, 38, 195, 203, 210, 222, 421, 429 | `SET({B_SYSVAR[2] B_EXPR_END})`, `SET({obj(uid=250).f[1] const(65436) B_GT B_EXPR_END})`, `SET({Global.Int16[2] const(315) B_LET B_EXPR_END})`, `Field(64)`, `SET({obj(uid=250).f[2] const(64136) B_LT B_EXPR_END})`, `SET({Global.Byte[8] const(0) B_LET B_EXPR_END})`, `SET({Global.Int16[2] const(315) B_LET B_EXPR_END})`, `Field(151)` |
| 153's other Field(154) | 153 e3 t1 ip3158 | `Field(154)` (in e3: not instanced at 328 -- O6-GOALS (e)) |
| 154's dispatch, the end row, its later grant | 154 e0 t0 ip234, 26, 588 | `SWITCH(304, L392, L232)`, `SET({Global.Bit[191] const(0) B_LET B_EXPR_END})`, `EnableMove()` |

Plus `route_mes` (block 3, US, the asset the engine reads):
```json
"route_mes": {"block": 3, "before": {"mes": 198, "holds": "And, Captain"},
              "on_page": [{"mes": 199, "holds": "“Captain [STNR]!”"}, {"mes": 200, "holds": "[STNR]\n“Yes, Your Majesty!”"}],
              "stop_page": {"mes": 56, "holds": "Env Play()"}}
```
O6-KEYS reads it: mes 198 holds the marker and no `[STNR]`; 199 and 200 hold their sources; no mes the script opens in 151
before 199 holds `[STNR]` (175-198: every window 151's route lists before the naming); every `naming[0].on_page.windows`
text is the computed line and every `raw_holds` the source's (4.11); mes 56 holds the stop page. The naming check, the
page witness, the stop page and the FakeGame's texts can then never drift from what the game shows.

### 4.17 The regions, the table's defaults
```json
"regions": {
 "153.e23": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "exit", "to": 154, "entrance": 315, "face_gate": null,
             "why": "the north door: tag 2 needs SYSVAR[2], the ground (f[1] > -100) and z > 1333 (ip38); ExitField ip59, ip203 Int16[2] := 315, ip211 Field(154)"},
 "153.e24": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "exit", "to": 150, "entrance": 315, "face_gate": null,
             "why": "tag 2 needs SYSVAR[2] alone: ip183 Int16[2] := 315, ip191 Field(150)"},
 "153.e25": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "exit", "to": 64, "entrance": 315, "face_gate": null,
             "why": "on the ground ip195/ip203 -> 64; upstairs with z < -1400 ip222 Byte[8] := 0, ip421/ip429 -> 151 (unreachable after the grant)"},
 "153.e26": {"points": [[-227, 3000], [200, 3000], [212, 935], [-264, 924]], "role": "dormant", "entrances": [328], "why": "side scene A (325)"},
 "153.e27": {"points": [[-777, -2348], [777, -2348], [777, -900], [-777, -900]], "role": "dormant", "entrances": [328], "why": "side scene B (325)"},
 "153.e28": {"points": [[2850, 347], [2850, -13], [1739, -74], [1739, 406]], "role": "dormant", "entrances": [328], "why": "the back door (325)"},
 "151.e8": {"points": [[-187, -7057], [173, -7000], [173, -8914], [-187, -8914]], "role": "dormant", "entrances": [110], "why": "InitRegion(8) only on the default branch L340: -> 153 @327"}}
```
154 is the END place: its regions (e8/e9/e10, instanced at 315) and its census are O7's; the run ends before any control
there. `steps_default` is O5's exactly (`attempts` 2, `interrupts` 1, `timeout_s` 20, `tolerance` 45, `exit_slack` 40,
`exit_wait_s` 5.0, `npcs` true -- the step overrides it false -- `overlay_ok` false, `immediate` false, `settle` null,
`lunge_ticks` 0, `min_depth` 40, `confirm_s` 4.0, `climb` O2's).

### 4.18 The emitted row pattern (the sink's prediction, the floating e15 row; R-DOOR measures it; O6-PATTERN judges it)
`pattern` = `{"visits": [[[place, sid, tag, off, target, new, same], ...] per visit, the floating rows OUT], "floating":
[...], "counts": [], "why"}`:
- `visits[0]` (151@110): (151, 0, 0, 16, Bit[191], 0, 1), (151, 0, 0, 43, Bit[184], 0, 1), (151, 0, 0, 51, Int16[9], -1,
  0), (151, 0, 0, 113, Byte[13], 0, 0), (151, 0, 0, 132, Int16[11], -1, 1), (151, 0, 0, 194, Byte[14], 0, 1), (151, 0, 0,
  309, Byte[8], 125, 1), (151, 3, 1, 426, Byte[6], 8, 0), (151, 2, 1, 724, Byte[8], 0, 0), (151, 2, 1, 921, Int16[2],
  328, 0);
- `visits[1]` (153@328, 23 rows): (153, 0, 0, 16, Bit[191], 0, 1), (153, 0, 0, 43, Bit[184], 0, 1), (153, 0, 0, 51,
  Int16[9], -1, 1), (153, 0, 0, 113, Byte[13], 0, 1), (153, 0, 0, 132, Int16[11], -1, 1), (153, 0, 0, 194, Byte[14], 0,
  1), (153, 32, 0, 700, Bit[3855], 1, 0), (153, 32, 0, 709, Bit[3854], 1, 0), (153, 32, 1, 234, Byte[208], 0, 1), (153,
  32, 1, 269, Byte[208], 1, 0), (153, 32, 1, 304, Byte[208], 0, 0), (153, 32, 1, 339, Byte[208], 1, 0), (153, 32, 1, 860,
  Byte[208], 0, 0), (153, 32, 1, 895, Byte[208], 1, 0), (153, 32, 1, 919, UInt16[21], 8, 0), (153, 32, 1, 1004,
  Byte[303], 0, 1), (153, 32, 1, 1038, Byte[303], 1, 0), (153, 32, 1, 1435, Byte[4], 0, 1), (153, 32, 1, 1469,
  UInt16[19], 8, 0), (153, 32, 1, 1495, Byte[4], 0, 1), (153, 32, 1, 1503, Byte[17], 0, 1), (153, 32, 1, 1511, Byte[18],
  1, 0), (153, 23, 2, 173, Int16[2], 315, 0);
- `floating`: `[{"visit": 2, "tuple": [153, 15, 0, 26, "Global.Byte[8]", 125, 0], "after": [153, 32, 0, 709,
  "Global.Bit[3854]", 1, 0], "before": [153, 32, 1, 919, "Global.UInt16[21]", 8, 0], "measured": null, "why": "153 e15
  t0 ip32, the Seq e32 t1 ip866 starts: op_22(45) and a sound sync before it, against at least 40 ticks of waits and five
  pages before ip971 -- in order unless the sync stalls (0.2 #11); the window is the bytes': it cannot precede ip866,
  which follows e32 t0's ip727, and ip1656 (the rebuild) comes >= 351 ticks of op_22, the stair walks and four pages after
  ip971; its place among the e32 t1 rows between is not compared"}]` -- rev. 2 (the claim critic's #6): the window's
  `before` is e32 t1 ip1656's tuple, NOT e23's ip203 (the first design's, which admitted the rebuild and the grant
  too); the freeze writes R-DOOR's measured position -- the row's index among visit 2's emitted rows and its frames to
  ip971's -- into `measured` (F4), refuses it null, and REFUSES one outside the window; `measured` is REPORT-ONLY (O6-PATTERN
  judges the bytes' window, never the measured gap: 11.2 #10);
- `counts`: [] -- no site is stored twice before the cut (0.2 #4): any `c` row of 151 or 153 fails (a).
Totals before the cut: 34 `w` rows (30 unmasked), no `c` row. The tuples carry `same`, not `old` (O5's rule: the
suppression pattern turns on whether a store changed its byte; `old` is CHAIN's, START's and START-DEPENDENT's).

---

## 5. Checks (O6's analysis)

### 5.1 Reading a run: the COVERED rule
O5's rule (skipped, install changed, the drive did not reach the end, a beat not done -- `named`, `name_on_page`,
`steiner_door` -- no or an incomplete trace, A-NOSTART, a BACKED forbidden hit, A-MISMATCH, A-START on 151's error path,
A-NOEND), A-START as O5 scopes it (151 is visited once: its error-path row is always the start's), and rev. 2's
**A-NAMING** (the claim critic's #2): the `named` row's `before` holds no raw with `name.before.marker` ("And,
Captain") -- the ring held no sample of 198 before the screen, or a screen came before 198 -- class V13, by the driver,
cell `[151, 1190, 1]`: the run UNCOVERED, re-run, never a failed check (a miss on every run of one side is VOID-ASYM
(b)'s). Likewise a page witness that found no parsed frozen window before 151's visit ended leaves the beat
`name_on_page` False: uncovered, never failed. A drive VOID carries its V-class and its `[place, sc, visit]` cell (2.7).
A run the session never drove (S15: `skipped` "the session stopped") is listed with its reason and is no VOID class. The
report lists every uncovered run's reasons per side.

### 5.2 The cuts (per side, frozen places)
`cut_at_start` from 151's first `w` row (place 151: real 151 on S, member(151) 31244 on F; the THREE residue rows in 70
go to `pre`); `cut_at_end` at the first `w`/`r` row in an end PLACE -- `end_places(pred, side)`, [154] on both sides (S6).
Kept after the cut: the epoch rows and any `c` rows of places 151 and 153 (none expected: 0.2 #4). On F the end place
154 is member(154)'s; LANDING (d) reads the cut row's `fld` (31246 on F, 154 on S); a run that entered real 154 on F is
VOID by rule 2 first (V19).

### 5.3 The checks, in order, each with the mutant that makes it fail (section 8 registers every one)
**All-run checks** (every run with a readable trace, judged even when COVER is short):
- **O6-FORBIDDEN** (O2's). Mutants: wrong-door-unbacked-F; misroute-one-F (rev. 2: S14's `left` -- the landing's rows
  under no V11 step row, so UNBACKED, the fork's; with VOID-ASYM (a)).
- **O6-VOID-ASYM** (O4's (a)-(d) over S13's `[place, sc, visit]` cells; `stop_on` [V19]). Mutants: v19-one-F (a, c),
  v4-control-151-F (a), v10-naming-153-F (a), v5-error-153-F (a: V5 game at `[153, 1190, 2]`, no A-START), v14-one-S
  (a), misroute-one-F (a: one F run V11 GAME at rule 2's cell `[150, 1190, 2]` after S14's `left`, with FORBIDDEN --
  the first design's V11-by-the-driver let it be re-run away), v7-door-all-F (b), v11-door-all-F (b: every F run V11
  driver at `[153, 1190, 2]` -- a loss without the evidence that lands, every run; VOID-ASYM still reads one side VOID in
  one class in every run), name-typed-F (b: every F run V13 driver at `[151, 1190, 1]`, the page witness's -- a typed
  name on every fork run is structural, never re-run away); and the PASS cases v13-input-one-F, v13-loss-unseen-one-F,
  name-typed-one-F (one F run V13 at the page: re-run), v11-wrong-door-S (backed), control-151-each-side.

**Then:** **O6-FROZEN**, **O6-COVER**. Mutants: predictions-changed; named-beat-missing, on-page-beat-missing (the ring
held no parsed frozen window: uncovered), door-beat-missing, naming-before-missing-both (A-NAMING on every run),
name-typed-both (V13 at the page on every run of both sides; VOID-ASYM P: no side covered); naming-stuck-session (S15:
the session stopped after run 4, S 1 and F 1 covered: VOID); and the PASS case naming-stuck-after-four (S15: the
session stopped at run 5 with S 2 and F 2 covered -- judged on them, PROVEN, `stopped` reported: rev. 2, the claim
critic's #5).

**Core checks** (over the covered runs):
- **O6-START** (O3's): (a) `pre` is exactly the THREE residue rows; (b) the first `w` row in place 151 is `start_first`,
  raw; (c) the first Byte[13] row in place 151 is ip119 `:= 0` from old 1. Mutants: start-residue-four (S: a byte-3 row
  0 -> 1 -- O5's four-row contract would pass it), start-residue-two (S: byte 2's row missing), start-residue-wrong (S:
  byte 2 0 -> 109), start-first-missing, start-music-old-wrong, front-cut-write.
- **O6-NO-SC** (O3's `no_sc_check`): no kept row over bytes 0-1 after the start. Mutants: sc-write-fork (a `cs`
  UInt16[0] row in 153 on F), sc-harness-poke-both (NO-SC alone).
- **O6-CHAIN** (O2's `span_check` over bytes 2-3 from 110): exactly 4.3, in order, each from the last. Mutants:
  chain-dropped-fork, chain-first-old-wrong (both: ip932's old 111: CHAIN alone).
- **O6-RESIDUE**: none after the start. Mutant: residue-after-start.
- **O6-WRITES (exact)**: every covered run's keys outside the noise ARE the 30 (O4's `writes_check`). Mutants:
  fork-drops-a-write (no 153 ip2248 on F), writes-extra-symmetric (both: 153 e32 t1 ip2161's dead store), inert-row-both
  (both: 153 e3 t1 ip2953, inert at 328) -- each with PATTERN (b).
- **O6-NULL**, **O6-STABLE** (O1's, no noise). Mutants: NULL -- fork-drops-a-write, e15-missing-F; STABLE --
  extra-key-one-F (one F run of three holds 151 e3 t3 ip909's store: STABLE F, WRITES F, STATE F, PATTERN F (b); NULL P).
- **O6-LANDING** (O5's shape over O6's crossings; every covered run, each clause named):
  - (a) every field-mode `w`/`c` row ran in its place's own field (member(place) on F) and stands in a route place [151,
    153];
  - (b) the crossing, on field-mode `w` rows at their places' own fields: the run holds `landing.exit151` (151 e2 t1 ip932
    `Int16[2] := 328`) and the next row after it is `landing.enter153` (153 e0 t0 ip22 `Bit[191] := 0`, emitted: a new
    site -- 153 loaded by 151's Field(153)); no row of place 151 after `enter153`;
  - (c) the last field-mode `w` row before the end cut is `landing.exit153` (153 e23 t2 ip203 `Int16[2] := 315`, by
    PLACE), and the run's `end` log row names the side's end field (154 on S, 31246 on F);
  - (d) THE END PER SIDE: the end cut (`cut_row`) is a raw `w` row that is `landing.end_row` (154 e0 t0 ip26 `Bit[191] :=
    0`) at `fld` the side's end field;
  - (e) every F digest records no seam and no seam key (the chain is closed from member(151) to member(154)).
  Mutants: lands-real-153-covered ((a)(b)(e), FORBIDDEN, WRITES; NULL P), harness-after-exit151-both ((b) alone: a
  harness row of place 151 between ip932 and 153's ip22), last-place-harness-both ((c) alone: a harness row in 153 after
  ip203), end-log-row-real-154-F ((c) alone), end-real-154-F ((d) alone: every F run's cut row at fld 154, `off` in
  31246), end-boundary-residue-both ((d) alone), seam-key-F (rev. 2, the claim critic's #10: every F run holds one
  script row in REAL 64 -- e0 t0 ip22 `Bit[191] := 0` -- between 153's ip2248 and ip203: one seam crossing and one seam
  key -> (e), with (a) and FORBIDDEN; any further co-failure the render gives re-registered with its reason). (e) is not
  registered ALONE on rows: a seam needs a row placed in a real non-member field after a member
  (storytrace.py:838-870), and a field-mode `w`/`c` row there is (a)'s, an `r` row RESIDUE's -- if C2 finds a row kind
  that reaches (e) alone, it registers that case too; the unit **landing-e** drives (e) alone on a covered F run whose
  digest carries one seam and nothing else.
- **O6-NAMING** (new; decision 4; rev. 2: the claim critic's #2 -- the driver ENFORCES, this RE-CHECKS, O5's CHOICE
  shape), every covered run of both sides:
  - (a) exactly ONE `named` row; its `donor` 151 and `field` the side's 151 field (151 on S, 31244 on F); its `frame`
    before the frame `f` of the run's ip610 row (`name.store`: the raw `w` row at place 151, e3 t1 ip610,
    Global.Byte[6]) -- the screen came before the store its closing releases; a run with no ip610 row fails (a): its
    anchor is missing. (The `before` marker is no longer (a)'s: a `before` without it is A-NAMING, 5.1 -- the
    instrument's miss leaves the run uncovered, never failing a core check.)
  - (b) exactly ONE `name_on_page` row, after the `named` row (its frame greater), in the same field, with `verdict`
    "ok"; at least one window, and EVERY listed window one a frozen entry names (`raw_holds` in its raw), PARSED (no
    tag in its text) and with its line `line` equal to the frozen `text` exactly -- "“Captain Steiner!”" for 199,
    "Steiner" for 200 when listed: the default name, on both sides. The driver wrote the row only after that very
    judgment, so a covered run fails (b) only through a bypassed driver rule.
  Mutants (each NAMING alone unless named): naming-two-rows-both ((a)), naming-none-both ((a): the beat set, no row -- a
  bypassed rule), naming-after-610-both ((a): the `named` frame after ip610's row), naming-real-151-F ((a): the `named`
  row's field 151 on F), start-dependent-missing-both ((a) with START-DEPENDENT, WRITES, PATTERN (b): its anchor
  gone), name-on-page-twice-both ((b): "exactly ONE"), name-on-page-other-field-both ((b): the row in 153 -- "in the
  same field"; the driver disarms at a new visit, so only a bypass writes it), name-on-page-before-named-both ((b)),
  name-on-page-other-window-covered-both ((b): the row lists only window 203, `verdict` "ok", the beat True -- a
  bypassed rule), name-wrong-covered-F ((b): every F run COVERED with 199 rendering "“Captain Rusty!”" and `verdict` "ok"
  -- a bypassed V13); and the PASS case name-on-page-both-windows-both (the row lists 199 and 200, both lines right).
  The first design's naming-before-missing-both, name-typed-F and name-on-page-other-window-both registered instrument
  events as NOT PROVEN; they are now VOID cases (COVER, VOID-ASYM above), and a typed name is the driver's V13.
- **O6-WALK** (O5's (a)-(b), S14's landing; THE PAIRED-WALK LAW), every covered run:
  - (a) exactly one `step` row of the door step (`walk.name`, `walk.donor` 153, `walk.visit` 2) with `outcome` "done",
    its `lost` sample satisfying the step's `until` (re-checked: `until_ok`) AND read in the side's 153 field
    (`lost.field`: 153 on S, 31245 on F), its `landed` None or the side's end field (154 / 31246: path A or B); before it
    at most `interrupts` (1) `interrupted` rows, each with no `door`, and at most `attempts` - 1 (1) `failed` rows, each
    with `landed` None and no `door`; nothing after it;
  - (b) no `w` row (any target, masked or not) whose frame lies inside a walk window (O5's `walk_windows`: each attempt's
    `[frame0, its end]`, the end `lost.frame` for "done" and "interrupted", the row's `frame` for "failed", and the gaps
    between attempts).
  Mutants (each alone): walk-no-step-both, walk-lost-south-both (the done row's `lost` z 1100: the walk failing its
  evidence), walk-lost-other-field-both (the done row's `lost.field` the end field: a bypassed V13), walk-landed-wrong-
  both (the done row's `landed` 30830 / 31243: a bypassed `left` -- rule 2's verdict), walk-two-interrupts-both,
  walk-interrupt-in-door-both
  (`door` 153.e25), walk-two-failed-both, walk-failed-in-door-both, walk-window-late-row-both (153 ip2248's row stamped
  inside the walk window, its order kept: WRITES, MASKED and PATTERN cannot see it); and the PASS cases
  walk-path-b-both (every done row `landed` 154 / 31246, `route.landed` set: S14's path B), walk-interrupted-once-both,
  walk-failed-once-both.
- **O6-PATTERN** (O5's, with the floating rows; critique #5): over the SCRIPT's rows (`src` "eb") of the route places
  [151, 153] before the cut that join, masked rows in (O5's `pattern_of`, reused):
  - (a) the `c` rows, as a multiset, are `pattern.counts` -- here none: any `c` row of 151 or 153 fails;
  - (b) the field-mode `w` rows, split into visits (maximal runs of one place), are `pattern.visits` with the floating
    rows taken out: each floating tuple present EXACTLY ONCE in its visit, after its `after` tuple and before its
    `before` tuple -- for the e15 row, after e32 t0 ip727 and before e32 t1 ip1656: the bytes' window (rev. 2, the claim
    critic's #6; its place among the rows between is not compared, and `measured` is never read here) -- and the
    remaining sequence equal to the frozen one in order -- a visit more or fewer failing.
  Mutants: c-row-151-F ((a) alone: every F run's 151 ip57 counted -- the prologue ran twice), byte8-repeat-both ((b)
  alone: a second 151 ip735 `Byte[8] := 0` -> 0, emitted `same` 1), e15-twice-both ((b) alone: a second e15 row 125 ->
  125), e15-before-window-both ((b) alone: the e15 row before e32 t0 ip727's -- the window's lower bound),
  e15-after-rebuild-both ((b) alone: the e15 row after ip1656's, before ip203 -- its upper bound, which the first
  design's window admitted), e15-outside-window-both ((b), with LANDING (c): the e15 row after ip203), rebuild-swap-F ((b)
  alone: ip1656 and ip1741 swapped -- two targets, so STATE (a) cannot see it); and the PASS case e15-after-971-both
  (the e15 row after ip971 and ip1006 in every run: "the e15/e32 order flipped" -- decision 6).
- **O6-START-DEPENDENT** (new: O2's 4.5 report, ported, and a check; decision 5; rev. 2: the claim critic's #3 -- every
  deviation CLASSIFIED PER RUN on the fields, never by which side holds it), every covered run of both sides, for each
  `start_dependent` key: exactly ONE raw `w` row at its site (place, sid, tag, ip, target), its `old` the `prior`'s value
  (newgame0: 0) and its `new` the key's `value` (8) -- computed by O6-KEYS from the prior and the statement, never typed.
  Any other row FAILS the check, the detail naming each run's class:
  - `old` = the prior, `new` != the value: **FINDING** -- the store itself wrote another value (it fails NULL / WRITES
    too);
  - `old` != the prior, and an EARLIER row of the run (any `w` or `r` row after the arm) touches the target's bytes:
    **EXPLAINED** by that row, named -- it is WRITES' extra key (or RESIDUE's row);
  - `old` != the prior and nothing earlier explains it: **START DRIFT on that side** -- the instrument's start (the state
    before the arm: New Game, field 70 or the warp), never the fork's: in a fresh epoch with WRITES exact, every hooked
    store emits its site's first row (StoryTrace.cs `AfterStore`), a bypass write surfaces as a residue row
    (StoryTrace.cs `Diff`), and P-EB pins the members to their donors but for `Field()` operands; the label adds "the
    `<after.run>` continuation" only when (`old`, `new`) = (`after.old`, `after.value`) exactly;
  - not exactly one row: the count, named.
  The first design keyed the label on SIDES ("one side: a FORK FINDING; both: START DRIFT") and so called a one-sided
  start difference a fork finding. A drift still FAILS the check (and WRITES / STATE with it): the run's start is the
  predictions' premise, and the label tells the lead it is the instrument's start, never the fork. Mutants: start-drift-F
  (renamed from start-dependent-differs-F: every F run ip610 old 1, new 9, no earlier row on byte 6 -- START DRIFT on F:
  S-D F, WRITES F, NULL F, STATE F, PATTERN F (b)), start-dependent-new-differs-F (every F run ip610 old 0, new 9 --
  `store_override`'s shape: a FINDING: S-D F, WRITES F, NULL F, STATE F, PATTERN F (b)), start-drift-both (both sides:
  ip610 3 -> 11 and ip2206 1799 -> 1807, the end state 11 / 1807 -- START DRIFT on both, the O1-O5 continuation: S-D F,
  WRITES F, STATE F (b), PATTERN F (b); NULL P), start-dependent-twice-both (a second ip2206 row 8 -> 8: S-D F,
  PATTERN F (b)), start-dependent-missing-both (no ip610 row on either side: S-D F (the count), WRITES F, PATTERN F (b),
  NAMING F (a): its anchor; NULL P).
- **O6-MASKED** (O2's). Mutant: masked-differs (with PATTERN (b): the masked rows are frozen tuples).
- **O6-STATE** (O2's): (a) each unmasked target's emitted history identical across every covered run, in order (the e15
  row's float does not reorder `Byte[8]`'s own history: 151 ip315, ip735, then e15 ip32); (b) every covered run's
  `end_state` == 4.10. Mutants: end-state-differs ((b) alone: one covered F run's `Bit[3855]` 0 live), fork-drops-a-write
  (a).
- **O6-JOIN** (O1's): every script row joins, the e15 row included (sid 15, tag 0, ip 32 in 153's and member(153)'s
  bytes). Mutant: join-failure (both: an extra row at 153 e32 t1 ip2207: JOIN alone -- PATTERN reads only rows that
  join).
- **O6-THROW** (in `run`): nothing thrown through EventEngine, EBin, StoryTrace or HarnessAgent.

**VERDICT**: O1's `verdict()`. A failed check outranks a void one: a V19 reads "NOT PROVEN: O6-VOID-ASYM", never VOID.

### 5.4 Report-only (`report_extra`)
- **Scope**, five lines:
  - *start dependence* -- (its span rendered from the keys' `after.run`, never a literal: rev. 2, the claim critic's
    #4) "values: two keys' VALUES depend on this start (a raw warp into 151@110 at SC 1190 from New Game), the same on
    both sides: 151 e3 t1 ip610 Byte[6] |= 8 writes 8 here and 11 after the <after.run> routes as driven (from 3: O1's
    |= 1, O2's |= 2 -- read from the archives at design time), 153 e32 t1 ip2206 UInt16[19] |= 8 writes 8 here and 1807
    after them (from 1799; its guard ip2180 reads bit 3, clear in both, so the branch is the same). OLD/SAME only (the
    value equal): 151 ip57 (Int16[9] 643 here, -1 after), ip119 (Byte[13] 1 vs 0), ip315 (Byte[8] same-value 125 here,
    a change 0 -> 125 after), 153 e32 t1 ip1656 (UInt16[21] old 0 vs 1), ip1741 (Byte[303] same-value here, a change
    1 -> 0 after), ip2248 (Byte[18] a change here, same-value after). The EMITTED ROW PATTERN: each run is a fresh epoch,
    so 151's start row ip22, 153@328's six prologue rows and 154's end row ip26 are emitted here, but would be
    suppressed `c` counts in a single-epoch chained O1-O6 run (O4 and O5 emitted those sites first): O6-PATTERN's frozen
    sequences, LANDING (b)'s re-entry row, the end cut and every row count are this start's -- never reuse them against
    a chained trace. Not covered: party data (the rebuild's SetPartyReserve / RemoveParty / PARTYADD), gil, Map
    variables, the camera, field 70's override state, and the untouched targets' values after the <after.run> routes";
  - *the name* -- (rev. 2, the claim critic's #2) "Steiner's name is PLAYER.Name, no gEventGlobal store: the trace
    cannot see it. The DRIVER judged the name the GAME renders on the first parsed [STNR] page after the screen (199's
    'Captain Steiner!', 200's speaker line when listed) against the default, on both sides, and VOIDed any run whose page
    showed another (V13: input at the naming screen, which accept_name's blocking call keeps from the run-wide
    witness); O6-NAMING (b) re-checks every covered run's row. The screen itself has no field key (Menu(1,3),
    EventService.StartMenu; the default is CharacterDefaultName), so S and F open the same one: a non-default name is
    input or the engine, never the fork. What remains: a name typed on either side makes that run VOID (re-run); typed
    on every run of a side it is VOID-ASYM (b), on every run of both sides the session reads VOID -- never PROVEN, and
    never a fork finding. A page the instrument never caught parsed leaves its run uncovered";
  - *the end state* -- "read live on arrival in 154: 154@315 stores only same-value prologue keys (ip279 is the 304
    branch's), so Byte[8] is read live too";
  - *settings and engine* -- the recorded `settings` (incl. `DisableNameChoice` 0), `derived`, `engine` (O4's lines);
  - *language* -- derived from the session's recorded P-TEXT3 line (O4's `scope_lang` shape, block 3).
- **Start dependence** (O2's 4.5 report, ported): per key "`<target> <op>` at `<donor> e<sid> t<tag> ip<ip>`: S
  `[values]`, F `[values]` (registered `<value>`, old `[olds]`); after the `<after.run>` routes as driven it would write
  `<after.value>` (from `<after.old>`, `<after.source>`) -- `<after.why>`" -- every span and number from the predictions
  (the unit **start-dependent-check** renders an `after.run` "O1-O6" as "O1-O6"); then per run any deviation with its
  class (FINDING / EXPLAINED by <row> / START DRIFT on <side>, with "the <after.run> continuation" when it is one).
- **The naming, per run:** the `named` row (frame, field), its `before` raws (A-NAMING's evidence), the `name_on_page`
  row (frame, every listed window's mes, raw, text, line, want, ok, the `verdict`), the frames from the screen's first
  sample to ip610's row, and from 199's first sample to 200's when the ring holds both.
- **The walk, per run:** the grant's sample (frame, x, z), the route record (legs, length, replans, pushes, waits), the
  loss sample (frame, field, x, z) and the last control sample before it, ticks grant -> loss, THE LANDING PATH (A:
  `route.landed` None; B: set, with `changed_to`), `flip_frame` (and `flip_late`), `landed_frame`, the frames loss ->
  flip -> landing, the walk-out's samples and where they stopped (S14b), a `misroute` when one was read, interruptions
  and failed attempts, the calibration's probes.
- **The e15 row, per run:** its frame, its index among visit 2's emitted rows, the frames from it to ip971's row (the
  float's measured gap: report-only, the window the bytes'), its sid/uid/tag/ip/add as written.
- **The pattern, per run:** the emitted rows per visit, any `c` rows, O6-PATTERN's first difference when it fails.
- The session's end (S5) and `stopped` (S15), O5's sections copied (VOID reasons per side, masked counts, forbidden hits,
  the P-TEXT3 line, the folded transcripts), and the re-runs held.

---

## 6. Offline check and preflight

### 6.1 `--offline-check` (the install and O4's build, read-only; reads `--predictions`, else the frozen file, else the DRAFT, and prints which)
- **O6-BUILD**: O5's `build_check` -- the base rule (every member's `.eb`, 7 languages, its own donor's with only
  in-chain `Field()` literals remapped: "140 files") -- and O5's `build_pins` over `route_build` (O5's, unchanged: the
  same three route members), PER LANGUAGE (each language's script decoded on its own; every byte in which member(151),
  member(153) or member(154) differs from its donor lies in the operand of one of its in-chain `Field()` instructions --
  member(151): e2 t1 ip940 (153), e8 t2 ip245 (153); member(153): e3 t1 ip3158 (154), e18 t1 ip1085 (151), e23 t2 ip211
  (154), e24 t2 ip191 (150), e25 t2 ip203 (64) and ip429 (151), e28 t2 ip235 (150); member(154): e2 t1 ip1528 and the six
  of e8/e9/e10 t2 -- and every such operand differs). This IS the per-language instruction-level claim the critic (#7)
  found the research had only for US: O5's C0 measured it on O4's build in all seven languages (`o5_forks.json`
  `built.measured`), O6-BUILD re-runs it at every `--offline-check`, and P-EB pins the live files to that build.
  Expected: "140 files, every language its own donor's; the route members' pins hold in 21 member files (3 route members
  x 7 languages): the only byte diffs are their 16 in-chain Field() operands; member(151) 31244, member(153) 31245,
  member(154) 31246" (0.2 #15's reading, O5's line).
- **O6-KEYS**: O2's `keys_check` machinery on (the chain, the writes, the start-dependent keys, `forbidden_sites` +
  `error_path` + `dead`, `start_first`) -- every key a store of its variable at `(sid, tag, ip)` with its function offset
  `off`, its MANDATORY `op` the statement's (`B_LET`, `B_OR_LET`, `B_POST_PLUS`), a compound value COMPUTED from its
  `prior` (newgame0 or a registered key) and the constant -- then: `start_music` exactly one writes key; every
  start-dependent key's `after.value` computed from `after.old` and the statement (3 |= 8 = 11, 1799 |= 8 = 1807), its
  `after.run` equal to the class's `AFTER_RUN` ("O1-O5": never a literal in the check, 11.5 #4) and its `after.source`
  present (`after.old` is read, not computed: 4.5); the `live_shared` entry's key (153 e15 t0 ip32) among the writes;
  then THE ROUTE PINS (4.16) exactly, 153's script holding NO store to `Map.Bit[144]` (ip80's test, the 25-tick fade),
  and `route_mes` as 4.16 states it, every `naming[0].on_page.windows` text the computed line (4.11). Expected: "60 keys
  over 58 distinct sites (the two start-dependent keys repeat two writes), every op in its statement, 11 compound values
  computed from their priors (the writes' two |= and four ++, the two start-dependent repeats, the three dead ++ stores),
  none masked but start_first (boot_scratch: O6-START reads it raw); start_music one writes key; the after values 11
  and 1807 computed, after.run O1-O5 (AFTER_RUN), their olds read (after.source); 74 route pins equal; 153 never writes
  Map.Bit[144] (26 references, all tests); mes 198 holds the marker, 199 and 200 their sources, no earlier 151 window
  [STNR], the on-page lines computed, mes 56 the stop page".
- **O6-TEXT**: O4's `text_check` on block 3, STRICT: "block 3: 7 byte-equal of 7; KNOWN-KIT-DEFECT 0, FAIL 0".
- **O6-CENSUS** (`store_census6`): every gEventGlobal store site of stock 151 and 153 is in `writes`, `chain`, the noise
  mask, `start_first`, `error_path`, `forbidden_sites`, `dead` or an `inert` function (O4's class precedence); every
  function decodes; no unresolved store. THE INERT PROOF at the route's entrance of each field (`visit_entrances`: 151 at
  110, 153 at 328), by `instanced_at6` (0.2 #2): every instancing op of the field sits in e0 t0, and the entrance instances
  no inert entry. THE LIVE SHARED PROOF (critique #3): for each `live_shared` entry, its `RunSharedScript(n)` sites are
  exactly `callers` and every caller's entry IS instanced at the entrance -- and an entry registered `inert` with a caller
  instanced there FAILS by name (O5's registration of e15 replayed at 328: "153 e15: registered inert, run by
  RunSharedScript(15) at e32 t1 ip866 -- e32 instanced at 328"). And every OTHER `RunSharedScript` site of the field lies
  in an entry not instanced at the entrance, or its shared entry holds no store (0.2 #3) -- the shared-entry proof kept
  for the others. 154 is the end place: its first store at 315 is the cut (O6-LANDING (d)); its census is O7's. Expected:
  "151: 21, 153: 51 store sites -- all classified (writes 7/21, chain 1/1, masked 2/2 (151's ip22 is start_first),
  error_path 4/4, forbidden 0/4, dead 5/10, inert 2/9); 0 unresolved; inert 151 e8 not instanced at 110, 153 e3, e18, e28
  not instanced at 328; LIVE shared 153 e15 (run by e32 t1 ip866, e32 instanced at 328); 153's other shared entries 4,
  5, 6, 8, 10, 12, 19 hold no store, their callers in e3/e7/e9/e11/e18 (not instanced at 328)".
- **O6-REGIONS** (`regions_problems6`): every frozen region's points are the first SetRegion of its (donor, entry);
  `exit`: `scan_gateways` has its (to, entrance, face_gate) AND `instanced_at6` instances it at the place's route
  entrance; `dormant`: instanced at none of its `entrances`, which must be exactly the place's route entrances; every
  gateway of 151 and 153 and every region a route entrance instances is registered; no hot-spot. Expected: "7 regions (3
  exit, 4 dormant), 0 hot-spots, 5 gateway entries all registered".
- **O6-GOALS**: O2's `goals_check` on the table (the step runnable; `visits` a walk on the route from the start place; the
  goal on the floor >= 80 from a wall with the 33 closed -- (19, 1620), 195 u; the `until` true at the goal; a route from
  `start` round the `avoid`) -- then `goals_extra6` (critique #2; decision 6), for the walk step:
  - **(c') THE FIRING LINE ON THE ROUTE:** the `start` stands on an OPEN tri of the step's floor (the 33 closed) at
    ground height (PSX y > the door's ground bound, -100); the planner's route (`route_avoiding`, the step's floor, round
    its `avoid`; at the step's `clearance` when it carries one), sampled every 5 u on the real mesh (the open tri under
    each point, its interpolated height), first passes the door's threshold (z > 1333) at a point INSIDE the door's quad
    (`doorface.region_contains`) on an open tri at ground height. Measured: (-29, 1333), tri 79, PSX y -1, inside 153.e23.
  - **(c'') THE EVIDENCE'S THRESHOLD:** the door's own test, read from its pinned text (`door_test`: `f[1] const(65436)
    B_GT` -> ground y -100, `f[2] const(1333) B_GT` -> threshold 1333; a door whose test holds no z term FAILS), and the
    step's `until` exactly one `z_gt` t with threshold - slack <= t <= threshold, the slack DERIVED -- `STALE_TICKS` 3 x
    `RUN_U_PER_TICK` 60 = 180 u (4.12; rev. 2, the claim critic's #8) -- never read from the predictions: a `walk`
    carrying a typed `stale_slack` FAILS by name. Never stricter than the engine (a real fire's loss sample always
    satisfies it: read at or north of the line, the walk-out walking north) and admitting at most the slack of the door's
    non-firing band. Measured: t 1200, 133 u admitted.
  - **(d') THE EVIDENCE'S SOUNDNESS:** every OTHER registered `exit` of the place (153.e24, 153.e25) lies wholly outside
    the `until` (no vertex of its quad satisfies it: e24 z <= 406, e25 z <= -900) AND is in the step's `avoid`; on the
    start's open component, every tri with a vertex past the `until` (z > 1200) is ground everywhere (every vertex at PSX
    y > -100) -- so no open floor past the evidence lies off the ground, where e23 could not fire. Measured: 14 tris,
    every one PSX y -1; no open tri on the whole mesh with a vertex at z > 1200 and one at PSX y <= -100.
  - **(e) THE LANDING'S DOOR:** the step's `to` is where the route's order goes next from its place (here the end field
    154: the last visit's next is an end field), and the place's only `Field(<to>)` site in an entry instanced at its
    route entrance is the door's (153: e23 t2 ip211; e3 t1 ip3158 lies in e3, not instanced at 328) -- so a landing in
    `to` from this walk is the door's own, which S14 relies on; and with (d') a loss past the evidence can only be
    e23's, whose only live `Field()` leads to `to` -- so a landing ELSEWHERE after the evidence held is the door's
    script's, the fork's or the engine's, never the walk's: S14's `left`, rule 2's verdict (rev. 2, 11.5 #1).
  The first design's inheritance of O5's (c)/(d) is withdrawn: O5's (d) refuses any exit with a vertex inside `until`,
  and 153.e23 lies inside z > 1200 by design; O5's (c)/(d) test a PSX y contour this flat walk never reaches (critique #2).
  Expected: "1 steps: (153, 1190) #1 wall 195 route 1 legs 1600u; (c') the start (-245, 42) on open ground tri 114; the
  route first past z 1333 at (-29, 1333), tri 79 (PSX y -1), inside 153.e23; (c'') the door's test (ground > -100, z >
  1333) and until z_gt 1200: 133 u of its non-firing band admitted (<= 180: 3 ticks x 60 u, derived); (d') 153.e24, 153.e25 wholly outside the
  until and avoided; the start's open component (118 tris): its 14 tris past z 1200 all ground; (e) to 154: 153's live
  Field(154) at 328 is e23 t2 ip211 alone".
- No SEAM check (the chain is closed: LANDING (e)).

### 6.2 `--preflight` (the live install, read-only; ALL GREEN today -- nothing needs deploying; decision 7)
O5's set, unchanged but for O6's titles: **P-MANIFEST** (`o6_forks.json` members = the frozen members, `deployed` true),
**P-DEPLOY** (twenty, each once under its name, mapped once), **P-EB** (20 x 7 live `.eb` = O4's build), **P-FLOOR**
(twenty deployed walkmeshes = their donors'; member(153)'s is the north door walk's floor), **P-STOCK** (no mod folder
overrides 151, 153 or 154), **P-TEXT3** (block 3, STRICT), **P-RECOVERY** (4600 registered: FF9CustomMap-world),
**P-DONOR** (151, 153 and 154 each forked by exactly one ForkDonorPatch row across the stack, its member's: 31244,
31245, 31246 in FF9CustomMap), **P-SETTINGS** (4.15's 28 keys, `DisableNameChoice` 0 among them), **P-PAD**,
**P-OVERRIDE** (field 70's override, one folder, the pinned sha: the warp window and Byte[13] 1 come from it),
**P-ENGINE** (the live DLLs the pinned sha). Today: 12 of 12 PASS (0.2 #15, read with O5's frozen predictions; the same
readers, the same facts).
**In game** (`capabilities`, O5's): P-CAP, **P-OBJECTS** ("the engine publishes the field's objects (s89): the walk plans
with `npcs` off -- the corridor soldiers e13/e14 and the knights e16/e17 publish, none is planned round"), P-LANG
(English(US)), P-DONOR-LOG (this launch's Memoria.log: the patchers ran, no ForkDonorPatch collision for 151, 153 or 154),
P-LAUNCH (every stacked patch file, Memoria.ini and the engine DLLs older than the launch; the DLLs the pinned engine),
P-PAD (re-sampled).
`--preflight` must read all green before any rehearsal; if it does not, the lead says exactly which line failed and stops.

### 6.3 The fingerprint (per run, before and after)
O5's, unchanged: another session's deploy, a re-wired New Game or an engine rebuild mid-session makes runs VOID
(A-INSTALL), never skews them.

### 6.4 `o6_forks.json` (the implementer writes it; nothing to flip: the chain is live)
```json
{"what": "O6's fork chain: O4's alxc disc-1 chain as deployed (31240-31259, FF9CustomMap). O6 starts in member(151) 31244 (at 110), runs member(153) 31245 (at 328) and ENDS on arrival in member(154) 31246 (at 315): every route Field() is retargeted, so the chain is closed (no seam). Nothing is imported, built or deployed for O6.",
 "reuses": "studies/story-trace/o4_forks.json",
 "import": "O4's (o4_forks.json import)", "build": "O4's: C:/gd/_ns_playtest/o4/build", "deploy": "O4's, 2026-10-02 09:04 local",
 "mod_folder": "FF9CustomMap", "members": {"<20 fork ids>": "<donor>"}, "names": {"<20 fork ids>": "<name>"},
 "route_members": {"31244": 151, "31245": 153, "31246": 154},
 "text_blocks": {"3": [31243, "...", 31259]},
 "deployed": true, "relaunch_needed": false,
 "relaunch_why": "nothing is deployed for O6; P-LAUNCH proves the launch read the live patch files, P-DONOR-LOG that it logged no collision for 151, 153 or 154",
 "global_side_effects": "O4's (o4_forks.json global_side_effects): O6 adds none",
 "known_defects": [], "revert": "O4's (o4_forks.json revert)",
 "built": {"where": "C:/gd/_ns_playtest/o4/build (O4's build, read-only)",
           "measured": "<C0: the route members' Field() operand sites per language, re-read from O4's build; O5's C0 (o5_forks.json built.measured) found the same>"},
 "verified": null}
```

---

## 7. Rehearsal plan (the lead runs these in game)

### 7.1 The stages (`o6_rehearse.py`: `run(g, field=None)`; `O6_STAGE=<name>` picks one by name, `--field 151` R-DOOR)
Each traced stage: New Game; `wait_frames(30)`; `storytrace(True)`; the raw warp; `segment_drive.drive(g, stage_pred,
side, log, end_fields=..., observe=recorder, forbid_live=True, witness=input_witness(g))`; the trace to
`rh_<stage>_<n>.jsonl`; the record into `o6_rehearsal.json`; `end_run` (S15's), its rows recorded. Only R-DOOR's traces
may define or change the keys, the start, the end state, the naming's lines or the row pattern; the staged runs prove
mechanics. F-SMOKE and F-PASS send NO `storytrace` verb.

| Stage | When | Warp | Ends in | Runs | What it settles |
|---|---|---|---|---|---|
| **R-DOOR** (the go/no-go and the predictions) | stock | `warp 151 110 1190` | 154 | 2 | F1-F6, F8, F10-F12, F15: 151's pages, pairs and timed windows under rule 7 (175/176's reaction); the naming (NameSetting's first sample, every Confirm's down frame, the screen's close, the `named` row, `before`); the `name_on_page` row (its windows' rendered lines, its `verdict`; 199's first sample to 200's); the ip610 row; 153's pages; the e15 row (sid, uid, tag, ip, add, its frame, its index and gap to ip971); the grant (position, frame, objects); the calibration; the walk (route, every hold's start and end position and pressed direction, slides/stalls/pushes/blockers -- hold 1's end and the corridor mouth's corner the go/no-go, the hold-2 starts `walk_stop_z` is taken from); the loss sample (frame, field, x, z, published y); THE LANDING PATH (`route.landed`, `changed_to`, `handoff`, and S14b's `flip_frame`, `landed_frame`, `walkout` -- the frames loss -> flip -> landing and where the walk-out stopped); the end cut 154 e0 t0 ip26; the keys, the masked rows, the pattern; the end state; the run time; the longest no-progress stretch |
| **R-NAMING-VOID** (by name; LAST but one) | stock | `warp 151 110 1190`, the stage key `naming_stop` | -- | 1 | F7: the run stopped WITH THE SCREEN UP -- o6_rehearse wraps `g.accept_name` to raise "the rehearsal's stop at the naming screen" on its FIRST call (rule 4's), before any Confirm, the session's own restored at once -- then `end_run`: `recover-warp-failed`, `end-naming` (S15: the screen accepted at once, no `close_ui` before it), `recover-warp-after-naming` (4600), the title; its time from the stop to the title recorded (F6) |
| **R-WALK-VOID** (by name; LAST) | stock | `warp 153 328 1190` (the assembly from its start: 151 is not needed), the stage overlay `walk_stop_z` -- 500, or the value F15 takes from R-DOOR's hold-2 starts -- or, F15's fallback, `walk_stop_hold` | V13 | 1 | F7: the walk stopped -- a wrapped `g.send` raises "the rehearsal's stop mid-walk" before the first `hold` sent while the published z is >= `walk_stop_z` in 153 (hold 2, sent inside e23's quad in its non-firing band, control held: 0.2 #7; `walk_stop_hold`: before the first `hold` sent once 153's basis is cached in `g._axes`, the calibration done), on the driver's own thread, the session's send restored at once; no `hold` step in steps.jsonl after the raise; `end_run` (the warp to 4600 from 153's FieldHUD, the ladder) reaches the title |
| **F-SMOKE** (by name; NO trace) | any time (deployed) | `warp 31244 110 1190`, `warp 31245 328 1190`, `warp 31246 315 1190` -- each `member(<donor>)` resolved from the chain -- and their stock twins | -- | 6 warps | F13: each member loads at its entrance and SC (field, FieldHUD), its published object sids EQUAL to its stock twin's measured set after `smoke_s` (the bytes predict 151@110 {4, 5, 12, 17}, 153@328 {13, 14, 16, 17}, 154@315 {5, 6, 7} -- the player never published -- but only the twin's reading is compared), 0 exceptions, `end_run` ok |
| **F-PASS** (by name; NO trace; before the freeze) | after F-SMOKE | `warp 31244 110 1190` | 31246 | 1 | F14: one F run through the whole route on the DRAFT (`forbid_live` False, `end_row_s` None): reached member(154), beats `named`/`name_on_page`/`steiner_door`, no V-class, no exception through EventEngine/EBin/HarnessAgent since the warp. It may only STOP the session (F14); its record is never evidence for any key and never shapes a frozen value |

Default order without `O6_STAGE`: R-DOOR, R-NAMING-VOID, R-WALK-VOID (the void stages last: a recovery that fails ends
the launch, and that failure is the finding). F-SMOKE and F-PASS by name only. Estimates a run: R-DOOR ~2 min,
R-NAMING-VOID ~1 min (S15 accepts the screen at once: no `close_ui` wait, no swallowed reset), R-WALK-VOID ~1 min,
F-SMOKE ~3 min in all, F-PASS ~2 min. `o6_rehearse.py` reuses O5's shapes (`select`, `stage_sides`, `stage_pred` -- the overlay keys `walk_stop_z` and
`walk_stop_hold` laid on the copy's WALK step, the stage key `naming_stop` read by `one()`; `O4R.stage_ids` resolving
`member(N)`; `O5R.Recorder` (grants with their objects, pages with `gone_frame`, the KEYON pairs, timed windows);
`O5R.WalkTap`; O5's `WalkStop` generalized to `x_stop` / `z_stop` / `hold_stop`; `fpass`; `O4R.smoke`), adds
`NamingStop` and the naming record (7.2), and cuts every summary at the stage's end PLACES (`o6_steiner.trace_summary`).
The command: `py tools/play.py studies/story-trace/o6_rehearse.py --label o6-rh --timeout 240`.

### 7.2 What every stage records
O5's record (grants, pages with `timed`, the press evidence, the longest no-progress stretch, the end state, `end_run`'s
rows, the walk tap's holds and samples, the calibration record, the published objects at the grant, the dialog-section
catch rate) plus:
- **the naming**: the first sample with `ui_state` "NameSetting" (frame) and the last 198 sample before it; every
  Confirm's request and down frame from steps.jsonl/events.jsonl between them and the screen's close (which press did
  Confirm 1's job: rule 7's stray or `accept_name`'s); the close frame; the `named` row and its `before`; the
  `name_on_page` row and its `verdict`; every [STNR] window's rendered lines on every sample the recorder read while it
  was listed (an unparsed sample counted: expected none, 0.2 #8); the frames from 199's first sample to 200's (the
  bytes' ~6 ticks); the ip610 row's frame;
- **the e15 row**: from the trace -- the row whole (sid, uid, tag, ip, add, frame), ip971's row frame, the gap in frames
  and ticks (at the launch's measured rate), its index among visit 2's emitted rows, and whether it lies inside the
  bytes' window (after e32 t0 ip727, before e32 t1 ip1656);
- **the walk**: the grant sample and the frames from 222's going to it; every hold (its start and end position,
  pressed direction, measured travel, slide/stall/push/blocker -- O5's judgments); HOLD 1's end point and the corridor
  mouth's corner (rev. 2, 0.2 #7: did the west wall slide him east, stop him, cost a push, a blocker or a replan?); every
  WALK hold (after the calibration) sent while the published z lay in [`walk_stop_z`, 1333) and every hold-2 start
  (F15); the loss sample and its `field`; the first sample in the next field; THE LANDING PATH (A or B) with
  `route.landed`, `changed_to`, `handoff`; S14b's `flip_frame` (`flip_late`), `landed_frame` and `walkout` off the
  step row -- in path A the walk tap stopped when `route_to` returned, so the step row is the record -- the frames loss
  -> flip -> landing, and where the walk-out stopped (the estimate z ~2065: a radius short of the floor's end);
- **the trace** through `trace_summary`: the start rows, the chain rows, each registered key present or absent, every
  unregistered key, the crossings (151 ip932 -> the next row, 153 ip203 -> the cut), the emitted rows per visit, any `c`
  row, the start-dependent rows (old, new), the end cut's row, the residue, the masked counts, the join failures;
- the launch's settings and engine, P-LAUNCH, P-DONOR-LOG, P-PAD, P-OVERRIDE and P-ENGINE readings;
- F-SMOKE: per warp the field and UI reached and when, the object sids against the twin's, exceptions, `end_run`'s
  result; F-PASS: the drive's outcome and rows, the exceptions since the warp.
`py studies/story-trace/o6_steiner.py --rehearsal-report <run dir>` prints all of it, stage by stage, run by run.

### 7.3 The freeze checklist (each item needs its evidence; the run dirs go into `rehearsals`)
- **F1 (the grant and the walk; go/no-go).** In every R-DOOR run: control granted once in 153 near (-245, 42) (within 64
  u; else the step's `start` takes the measured point and O6-GOALS runs again before the freeze), the door step `done`
  on its first attempt, its loss sample in 153's own field at z > 1200 (expect z 1333-1450 and x inside e23's quad on
  the corridor's open ground, the centre band ~[-55, 90] at his radius -- the fake lost him at x -50 to -90, NOT on the
  planned line's -29; published y ~1), no V-class. THE DERIVED SLACK CROSS-CHECKED (rev. 2, the claim critic's #8):
  every loss at published z >= 1333 - 180 = 1153, else STOP -- `STALE_TICKS` is wrong. THE CORNER (rev. 2, the driver
  critic's #1): hold 1's end point and the corridor mouth's effect on him recorded per run (with F12); GO when the walk
  is done on its first attempt and the corner cost at most a slide or a stop that the next hold cleared; a corner that
  cost a replan, a blocker, a push or more than one extra hold, or a run not done on its first attempt, is NO-GO: STOP
  the freeze for a re-derived walk (the goal or a start nudge, re-checked by O6-GOALS) and repeat R-DOOR. A walk that
  fails its evidence: STOP and re-derive the threshold and the evidence from the measured loss samples.
- **F2 (the landing path).** Each run's path (A or B), its frames loss -> flip -> landing and the walk-out's samples
  (S14b: on the step row in both paths), and where the walk-out stopped (expect z ~2065), recorded. Both paths are DONE
  by S14; no freeze value depends on which. A run in neither (a V13 "loss unseen", a V11, or S14's `left`) STOPS the
  freeze for an explanation.
- **F3 (the naming).** NameSetting published with no window; the screen closed within `accept_name`'s 4 Confirms (O1/O2
  measured 2); the `named` row after 198's last sample (`before` holding "And, Captain") and before ip610's row; the
  `name_on_page` row on stage 21's first sample listing a parsed frozen window (199 alone expected, 200 ~6 ticks
  later), `verdict` "ok", its rendered lines EQUAL to 4.11's computed texts ("“Captain Steiner!”", and "Steiner"
  wherever 200 is read) -- a difference (a space, a tag left, a line break) STOPS the freeze for an engine-level
  explanation, never a loosened compare (in the session it would be every run's V13); no unparsed [STNR] sample on any
  read (the engine parses at attach: 0.2 #8 -- one seen is recorded and explained); any stray rule-7 Confirm on the
  screen named.
- **F4 (keys, the pattern, the float).** The R-DOOR traces define the predictions: per run exactly the 30 keys and the 4
  masked rows; no error-path, dead, forbidden or inert row; exactly the three start residue rows and none after; 151's
  first `w` row ip22 and its first Byte[13] row ip119 from old 1; every visit's emitted sequence exactly 4.18's tuples
  with the e15 row inside the bytes' window (after e32 t0 ip727, before e32 t1 ip1656), no `c` row; the e15 row's
  attribution (sid 15, tag 0, ip 32, add 0; its uid recorded, expected 96) and its MEASURED position (its index among
  visit 2's emitted rows, its frames to ip971) written into `pattern.floating[0].measured` -- report-only; the freeze
  refuses one outside the window; the end cut 154 e0 t0 ip26; the two runs key for key and tuple for tuple identical
  (the float aside); any difference explained at the byte level before the freeze (a new site only with O6-CENSUS's
  lists updated).
- **F5 (end state).** Every R-DOOR `end_state` equals 4.10 (Byte[8] 125 read live).
- **F6 (budgets).** `run_s` = 2 x the slowest R-DOOR; `run_min_s` = 1.25 x the median PLUS the longest measured
  recovery (rev. 2, the driver critic's #4: the next run's `end_run` spends it before its drive; R-NAMING-VOID's from
  the stop to the title -- S15: seconds, not ~67 -- R-WALK-VOID's, R-DOOR's from 154, all recorded); `session_s` = 8 x
  the median + 1800; `no_progress_s` = max(60, 3 x the longest no-progress stretch of any traced stage); `settle_s` 1.0,
  O1's.
- **F7 (recovery).** R-NAMING-VOID: end_run's rows `recover-warp-failed`, `end-naming`, `recover-warp-after-naming`
  (4600), then the title, with no `close_ui` before `end-naming`; R-WALK-VOID: the stop with no `hold` step in
  steps.jsonl after the raise, `recover-warp` (4600) and the title; R-DOOR's `end_run` from 154 reaches the title.
- **F8 (pairs and timed windows).** Every KEYON pair closed within 8.3 s of its second window; whether 175/176 closed
  early under a Confirm recorded (timing only: no store follows them).
- **F9 (pages' openings).** The dropped first presses and the [SPED] type-outs counted (198's included): recorded only
  (no page-once, no guard in O6).
- **F10 (settings and launch).** P-SETTINGS (incl. `DisableNameChoice` 0), P-PAD, P-OVERRIDE, P-ENGINE, P-LAUNCH and
  P-DONOR-LOG pass on the rehearsal launch; its fingerprinted `settings` and `engine` equal 4.15's.
- **F11 (the input witness).** No `input` row in any run.
- **F12 (objects and the corner).** At the grant: the published objects recorded (e13/e14 on the corridor, the knights
  walking east, walk-through); `npcs` false: none planned round. Recorded only. And the corridor mouth's west corner
  (rev. 2, 0.2 #7): hold 1's end point, and any slide, stall, push or blocker there, per run -- F1's go/no-go reads it.
- **F13 (F-SMOKE).** The three members load as their twins, their object sids each EQUAL to the twin's measured set.
- **F14 (F-PASS: may only STOP the session).** Reached member(154) with no throw and no V-class. Any V-class or throw it
  shows is a FINDING written into PLAN.md before anything else; an engine or build change in response re-pins P-ENGINE and
  P-EB and repeats F-PASS; nothing it records shapes a frozen value.
- **F15 (the stop's own firing condition; rev. 2, the driver critic's #1, 11.2 #4).** The z stop fires on the first
  `hold` sent at published z >= `walk_stop_z`, so it lands mid-walk exactly when, in EVERY R-DOOR run, some WALK hold is
  sent while the published z lies in [`walk_stop_z`, 1333) -- before the door can fire, control held. `walk_stop_z` is
  taken from R-DOOR's measured hold-2 starts: the draft's 500 stays when every run's hold 2 starts at z >= 500 (expected
  ~940-1020: 0.2 #7) and every calibration probe ends below it (expected <= ~192); else the lowest hold-2 start less 50,
  when that still clears the probes. Met -> R-WALK-VOID runs with that `walk_stop_z` (the stop lands mid-walk -- inside
  e23's quad in its non-firing band, as hold 2 is sent); not met -> R-WALK-VOID runs with the fallback `walk_stop_hold`
  (the run stopped inside the step, control held, before his first walk hold), and the record says which. The first
  design's rule ("two walk holds before the first sample at z >= 924") counted ONE hold on the critic's runs and would
  have chosen the fallback for a stop that fires.
Then `--freeze` (v1). `freeze` refuses: no `witness`; a `naming` registration without `on_page` or without its
`windows`; a table step carrying a rehearsal overlay (`walk_stop_z`, `walk_stop_hold`, `walk_stop_x`); a `walk` carrying a
typed `stale_slack`; `side_ends` failing `side_ends_of`; a non-empty `battles`; a `start_dependent` key without `after`
or without `after.source`; `pattern.floating` with `measured` null, or with a measured position outside its window (after
e32 t0 ip727, before e32 t1 ip1656); an empty `rehearsals`; an `engine` that is not the live DLLs'; an existing file.

### 7.4 After the freeze: the session (the lead)
- **G1.** `--preflight` all green on the session's launch (P-LAUNCH, P-ENGINE, P-DONOR-LOG in game).
- **G2.** The session, unattended and hands off (no key while the game has focus, no pad -- the witness VOIDs a run that
  sees one, V13; a key typed at the naming screen is the page witness's V13 -- every run it touches is VOID, re-run):
  `py tools/play.py studies/story-trace/o6_steiner.py --label story-o6 --timeout 240`.

---

## 8. The dry run (`o6_dryrun.py`: synthetic sessions through `O6.analyse`)

Built like `o5_dryrun.py`: its own `render` (O5's, with O6's start values -- SC 1190, FieldEntrance 110, Byte[13] 1,
Int16[9] 643, Int16[11] -1, Byte[8] 125, every other target 0 -- and the sink's per-site rule: with O6's distinct sites
nothing is suppressed unless a case stores a site twice), O3's event helpers, O5's `at(frame)` anchors and the store
options (`f`, `emit`, `fld`/`don`, `old`), and O3's EXACT `case()` (every check a case does not name must read PASS; a
COVER-VOID case expects every core check VOID; LANDING, NAMING, WALK, PATTERN, START-DEPENDENT and VOID-ASYM cases
register the clause the detail must name). Every case reads its freeze-time values -- the budgets, `measured`,
`rehearsals` -- FROM THE PREDICTIONS it is given, never a literal (rev. 2, the claim critic's #9): C2 and G33 run every
case both on the draft (or the frozen file) and on `as_if_frozen(draft)` (1.4: `measured` set inside its window, every
budget x1.5, `rehearsals` non-empty), N/N each.
- **Real store sites** (every field row joins): 4.3-4.6's, the error-path, forbidden, dead and inert sites, 154 e0 t0
  ip26 (the end row) and 154's post-cut prologue.
- **A base run**: `arm` (fld 70); the three residue rows (fld 70); visit 1's ten rows (4.18) -- ip610's row at
  `F_610` 3100, after the naming; ip735, ip932; visit 2's 24 rows -- the e15 row at `F_E15` 4300, before ip971 at 4600;
  the rebuild's rows; nothing in the walk window [`F_WALK0` 6000, `F_LOST` 6050]; ip203 at 6100; 154's ip26 at 6200 (the
  cut), then its post-cut rows; `off` (fld 154 / 31246). On F: 151 -> 31244, 153 -> 31245, 154 -> 31246.
- **A log**: the visit rows; the page presses; the `named` row (frame `F_NAMED` 3000, field 151 / 31244, `before`
  {frame 2990, raws [198's source]}); the `name_on_page` row (frame `F_PAGE` 3200, `verdict` "ok", windows [199 alone --
  the bytes' lag puts 200 ~6 ticks later: mes 199, its raw, text "Queen Brahne\n“Captain Steiner!”", line 1, want
  "“Captain Steiner!”", ok true]); the door step row (`done`, `frame0` 6000, `lost` {frame 6050, field 153 / 31245, x
  -50, z 1340}, `landed` None, `route` {landed None, changed_to None, handoff True}, S14b's `flip_frame` 6100 with
  `flip_late`, `landed_frame` 6150 and its `walkout` samples); the end row (154 / 31246); `end_state` (4.10); beats
  `{"named": true, "name_on_page": true, "steiner_door": true}`. Every VOID a case adds carries a `[place, sc, visit]`
  cell.

| Case | Want |
|---|---|
| null-pair | PROVEN |
| fork-drops-a-write (no 153 ip2248 on F) | NOT PROVEN (WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-dropped-fork (no 153 ip203 on F) | NOT PROVEN (CHAIN F, LANDING F (c), WRITES F, NULL F, STATE F, PATTERN F (b)) |
| chain-first-old-wrong (both: ip932's old 111) | NOT PROVEN (CHAIN F alone: PATTERN's tuples carry `same`, not `old`) |
| start-residue-four (S: a byte-3 row 0 -> 1) | NOT PROVEN (START F) -- O5's four-row contract would pass it |
| start-residue-two (S: byte 2's row missing) | NOT PROVEN (START F) |
| start-residue-wrong (S: byte 2 0 -> 109) | NOT PROVEN (START F) |
| start-first-missing (both: 151's ip22 dropped) | NOT PROVEN (START F, PATTERN F (b); MASKED P: 153's ip22 still writes boot_scratch on both sides -- re-registered with its byte-level reason if the render shows more) |
| start-music-old-wrong (both: ip119's old 2) | NOT PROVEN (START F) |
| front-cut-write (F: a `w` row in fld 70 before the start) | NOT PROVEN (START F) |
| error-path-start-S (one S run: 151 ip97, stopped at window 56; V5 driver [151, 1190, 1]) | PROVEN (S 2 of 3); the run's classes include V5 and A-START |
| v5-error-153-F (one F run: 153 ip97, window 56; V5 game [153, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)); no A-START |
| residue-after-start (F: an `r` row on byte 300) | NOT PROVEN (RESIDUE F) |
| writes-extra-symmetric (both: 153 e32 t1 ip2161 `Byte[4] := 1`) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| inert-row-both (both: 153 e3 t1 ip2953) | NOT PROVEN (WRITES F, PATTERN F (b); NULL P) |
| extra-key-one-F (one F run of three holds 151 e3 t3 ip909 `Bit[3793] := 1`) | NOT PROVEN (STABLE F, WRITES F, STATE F, PATTERN F (b); NULL P) |
| sc-write-fork (F: a `cs` UInt16[0] := 1190 row in 153) | NOT PROVEN (NO-SC F, WRITES F, NULL F, STATE F) |
| sc-harness-poke-both | NOT PROVEN (NO-SC F alone) |
| e15-missing-F (every F run without the e15 row) | NOT PROVEN (WRITES F, NULL F, STATE F, PATTERN F (b)) |
| e15-after-971-both (the e15 row after ip971 and ip1006: "the order flipped") | PROVEN (decision 6: unordered) |
| e15-twice-both (a second e15 row 125 -> 125, emitted `same` 1) | NOT PROVEN (PATTERN F (b) alone) |
| e15-before-window-both (the e15 row before e32 t0 ip727's: the window's lower bound -- rev. 2) | NOT PROVEN (PATTERN F (b) alone) |
| e15-after-rebuild-both (the e15 row after ip1656's, before ip203: the bytes' upper bound, which the first design's window admitted -- rev. 2) | NOT PROVEN (PATTERN F (b) alone) |
| e15-outside-window-both (the e15 row after ip203) | NOT PROVEN (PATTERN F (b), LANDING F (c)) |
| byte8-repeat-both (a second 151 ip735 `Byte[8] := 0` -> 0, emitted) | NOT PROVEN (PATTERN F (b) alone) |
| c-row-151-F (every F run: a `c` row of 151 ip57, n 1) | NOT PROVEN (PATTERN F (a) alone) |
| rebuild-swap-F (every F run: ip1656 and ip1741 swapped) | NOT PROVEN (PATTERN F (b) alone) |
| start-drift-F (renamed from start-dependent-differs-F -- rev. 2: every F run ip610 old 1, new 9, no earlier row on byte 6) | NOT PROVEN (START-DEPENDENT F, WRITES F, NULL F, STATE F, PATTERN F (b)) -- the detail names START DRIFT on F (the instrument's start), never a fork finding |
| start-dependent-new-differs-F (rev. 2: every F run ip610 old 0, new 9 -- `store_override`'s shape) | NOT PROVEN (START-DEPENDENT F, WRITES F, NULL F, STATE F, PATTERN F (b)) -- the detail names a FINDING: the store wrote another value |
| start-drift-both (both: ip610 3 -> 11, ip2206 1799 -> 1807, end state 11 / 1807) | NOT PROVEN (START-DEPENDENT F, WRITES F, STATE F (b), PATTERN F (b); NULL P) -- START DRIFT on both sides, "the O1-O5 continuation" ((old, new) = after's) |
| start-dependent-twice-both (a second ip2206 row 8 -> 8) | NOT PROVEN (START-DEPENDENT F, PATTERN F (b)) |
| start-dependent-missing-both (rev. 2: no ip610 row on either side; the end state 4.10's) | NOT PROVEN (START-DEPENDENT F -- the count -- WRITES F, PATTERN F (b), NAMING F (a): its anchor; NULL P) |
| naming-two-rows-both | NOT PROVEN (NAMING F (a) alone) |
| naming-none-both (beats `named` True, no `named` row) | NOT PROVEN (NAMING F (a) alone) |
| naming-after-610-both (the `named` frame after ip610's row) | NOT PROVEN (NAMING F (a) alone) |
| naming-before-missing-both (`before`'s raws without "And, Captain": the ring missed 198 -- rev. 2, A-NAMING) | VOID (COVER V: every run A-NAMING, V13 driver; VOID-ASYM P) |
| naming-real-151-F (every F run's `named` row at field 151) | NOT PROVEN (NAMING F (a) alone) |
| name-typed-one-F (rev. 2: one F run VOID V13 driver at [151, 1190, 1]: "the name on the page is not the default", its row `verdict` V13, 199 "“Captain Rusty!”") | PROVEN (F 2 of 3: re-run) |
| name-typed-F (rev. 2: every F run VOID V13 driver at [151, 1190, 1], the page witness's) | NOT PROVEN (VOID-ASYM F (b); COVER V) -- a typed name on every fork run is structural, never re-run away |
| name-typed-both (rev. 2: every run of both sides VOID V13 driver at [151, 1190, 1]) | VOID (COVER V; VOID-ASYM P: no side has a covered run) |
| name-wrong-covered-F (rev. 2: every F run COVERED, its row's 199 line "“Captain Rusty!”" with `verdict` "ok" -- a bypassed V13) | NOT PROVEN (NAMING F (b) alone) |
| name-on-page-twice-both (rev. 2: two `name_on_page` rows) | NOT PROVEN (NAMING F (b) alone) |
| name-on-page-other-field-both (rev. 2: the row's field 153 / 31245 -- a bypassed disarm) | NOT PROVEN (NAMING F (b) alone) |
| name-on-page-before-named-both | NOT PROVEN (NAMING F (b) alone) |
| name-on-page-other-window-covered-both (the row lists only window 203, `verdict` "ok", the beat True -- a bypassed rule; rev. 2 renamed) | NOT PROVEN (NAMING F (b) alone) |
| name-on-page-both-windows-both (rev. 2: the row lists 199 and 200, both lines right) | PROVEN |
| naming-stuck-session (S: run 3 STOPPED "the naming screen stayed up", run 4 `skipped` "the session stopped", no 5-6; `session["stopped"]`) | VOID (COVER V: S 1 of 3, F 1 of 3; VOID-ASYM P) |
| naming-stuck-after-four (rev. 2, the claim critic's #5: runs 1-4 covered, run 5 (S) STOPPED "the naming screen stayed up", run 6 `skipped`; `session["stopped"]`) | PROVEN (S 2 of 3, F 2 of 3: a stopped session judged on the runs it covered; `stopped` in the report) |
| lands-real-153-covered (every F run: 153's rows at fld 153, the drive reached) | NOT PROVEN (LANDING F (a)(b)(e), FORBIDDEN F, WRITES F; NULL P) |
| harness-after-exit151-both (a harness row of place 151 between ip932 and 153's ip22) | NOT PROVEN (LANDING F (b) alone) |
| last-place-harness-both (a harness row in 153 after ip203) | NOT PROVEN (LANDING F (c) alone) |
| end-log-row-real-154-F (every F run's synthetic `end` row names 154) | NOT PROVEN (LANDING F (c) alone) |
| end-real-154-F (every F run's cut row at fld 154; `off` in 31246) | NOT PROVEN (LANDING F (d) alone) |
| end-boundary-residue-both (an `r` row in place 154 before its ip26) | NOT PROVEN (LANDING F (d) alone) |
| seam-key-F (rev. 2, the claim critic's #10: every F run holds one script row in REAL 64, e0 t0 ip22 `Bit[191] := 0`, between 153's ip2248 and ip203 -- a seam crossing and a seam key) | NOT PROVEN (LANDING F (a)(e), FORBIDDEN F; any further co-failure the render gives re-registered with its reason -- (e) alone is the unit landing-e's) |
| end-row-missing-one-S (one S run: no row in 154, `off` in 154) | PROVEN (S 2 of 3); that run A-NOEND |
| v19-one-F (one F run VOID V19 game at [154, 1190, 2]: landed in real 154) | NOT PROVEN (VOID-ASYM F (a)(c)) |
| leak-real-153-F (one F run VOID V19 at [153, 1190, 1]; its rows at fld 153) | NOT PROVEN (FORBIDDEN F, VOID-ASYM F) |
| v4-control-151-F (one F run VOID V4 game at [151, 1190, 1]: "control in 151") | NOT PROVEN (VOID-ASYM F (a)) |
| control-151-each-side (one run each side V4 game at [151, 1190, 1]) | PROVEN (S 2 of 3, F 2 of 3) |
| v10-naming-153-F (one F run VOID V10 game at [153, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| v14-one-S (one S run VOID V14 game at [153, 1190, 2]) | NOT PROVEN (VOID-ASYM F (a)) |
| v7-door-all-F (every F run VOID V7 driver at [153, 1190, 2]) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v11-door-all-F (every F run VOID V11 driver at [153, 1190, 2]) | NOT PROVEN (VOID-ASYM F (b); COVER V) |
| v13-input-one-F (one F run VOID V13 driver: outside input) | PROVEN (F 2 of 3) |
| v13-loss-unseen-one-F (one F run VOID V13 driver: "the loss went unseen in 31245") | PROVEN (F 2 of 3) |
| v11-wrong-door-S (one S run VOID V11 driver: e25's ip195 row, a step row `door` 153.e25 `landed` 64, rows in 64) | PROVEN (S 2 of 3; the 64 hits backed: A-FORBIDDEN) |
| wrong-door-unbacked-F (one F run: e25's ip195 row and rows in 31240, no step row explains them) | NOT PROVEN (FORBIDDEN F, and the co-failures the rows give -- registered with their reason) |
| misroute-one-F (rev. 2, the claim critic's #1: one F run -- the door's evidence held, its loss at (-50, 1340) in 31245; the step row `left`, `misroute` {fld 31243, place 150}, `landed` None; VOID V11 GAME at rule 2's cell [150, 1190, 2]; e23's ip203 row, then rows in 31243) | NOT PROVEN (VOID-ASYM F (a), FORBIDDEN F: the 31243 rows UNBACKED -- no V11 step row with `landed` 31243; any further co-failure the rows give re-registered with its reason) |
| walk-path-b-both (every done row `landed` 154 / 31246, `route.landed` set, `flip_frame` set) | PROVEN (S14's path B) |
| walk-interrupted-once-both | PROVEN |
| walk-failed-once-both | PROVEN |
| walk-no-step-both | NOT PROVEN (WALK F (a) alone) |
| walk-lost-south-both (the done row's `lost` z 1100: "the walk failing its evidence") | NOT PROVEN (WALK F (a) alone) |
| walk-lost-other-field-both (the done row's `lost.field` 154 / 31246) | NOT PROVEN (WALK F (a) alone) |
| walk-landed-wrong-both (the done row's `landed` 30830 / 31243: a bypassed `left`) | NOT PROVEN (WALK F (a) alone) |
| walk-two-interrupts-both | NOT PROVEN (WALK F (a) alone) |
| walk-interrupt-in-door-both (`door` 153.e25) | NOT PROVEN (WALK F (a) alone) |
| walk-two-failed-both | NOT PROVEN (WALK F (a) alone) |
| walk-failed-in-door-both | NOT PROVEN (WALK F (a) alone) |
| walk-window-late-row-both (153 ip2248's row stamped inside the walk window, its order kept) | NOT PROVEN (WALK F (b) alone) |
| named-beat-missing (two S runs: `{"named": false}`) | VOID (COVER V; VOID-ASYM P) |
| on-page-beat-missing (two S runs: no `name_on_page` row, `{"name_on_page": false}` -- the ring held no parsed frozen window before 151's visit ended: the instrument's miss) | VOID (COVER V; VOID-ASYM P) |
| door-beat-missing (two S runs: `{"steiner_door": false}`) | VOID (COVER V; VOID-ASYM P) |
| end-cut (S: rows in 154 past the end) | PROVEN |
| end-state-differs (one covered F run: `Bit[3855]` 0 live) | NOT PROVEN (STATE F (b)) |
| masked-differs (every F run without its Bit[184] rows) | NOT PROVEN (MASKED F, PATTERN F (b)) |
| mismatched (one F run's member rows name another donor) | PROVEN; that run A-MISMATCH |
| no-start-row (one S run never reaches 151) | PROVEN; that run A-NOSTART |
| join-failure (both: an extra row at 153 e32 t1 ip2207) | NOT PROVEN (JOIN F alone) |
| trace-without-off | VOID |
| install-changed | VOID |
| predictions-changed | NOT PROVEN (FROZEN F) |

A case's want that the code cannot hold (a co-failure the table did not foresee) is explained at the byte level and
re-registered, never loosened silently (O3 11.6, O4 11.4 C #10, O5 11.5 PART C #12 did this). The inert-row case
places its `Byte[8]` row before the e15 row and the writes-extra case its `Byte[4]` row before ip2172 (where the script
would run it), so both end values stay 4.10's and STATE (b) passes: the cases isolate WRITES and PATTERN.

Units (no session): **step-of-to** (S14's refusals); **trigger-to-verdict** (the pure verdict: path A, path B, a wrong
place after the evidence -> left (rev. 2), a loss in another field, no loss with a landing, an in-field loss without the
evidence -> v11 with a landing, judge without); **naming-of** (S16's refusals, the `windows` keys included; O2's
registration passes; every frozen predictions file passes); **instanced-at6** (151 at 110 -> {object 3, 4, 5, 12, 17;
code 1, 2}, at 327 -> {object 3, 6, 7, 12; region 8; code 1, 2}; 153 at 328 equal to O4's walker's; O4's raises on 151 --
the reason O6 has its own); **render** (the base run: 34 `w` rows before the cut, no `c` row; the same event list through
the FakeGame's H13 knob gives the same `(k, fld, sid, tag, ip, new, same)` sequence); **pattern** (`pattern_diff6` on the
base: none; the e15 row anywhere in its window -- after e32 t0 ip727, before e32 t1 ip1656 -- none; before ip727, after
ip1656, twice, or missing: (b); a `measured` value never changes the result); **trace-summary** (a base S run: the chain
2/2, writes 28/28, the cut row 154 ip26; an F stage ending in 31246 cut at place 154; the same summary given end FIELDS
on F is not cut -- the unit's mutant); **state-history** (Byte[8] `[(151, 125), (151, 0), (153, 125)]`, Byte[208] six
entries, Byte[6] `[(151, 8)]`); **naming-check** (pure, over synthetic runs: its PASS and every clause's FAIL -- (b)'s
`verdict`, an unparsed window listed, a window no entry names, a line that differs, two rows, another field each);
**start-dependent-check** (pure: its PASS and every class -- FINDING (old 0, new 9), EXPLAINED (an earlier `w` row on
byte 6 named), START DRIFT on one side and on both, "the <after.run> continuation" only at (`after.old`,
`after.value`), the zero-row and two-row counts -- and the report line rendered from the predictions: an `after.run`
"O1-O6" renders "after the O1-O6 routes as driven", and O6-KEYS FAILS it unless the class's `AFTER_RUN` is "O1-O6"
(a subclass's); never "after O1"); **landing-e** (rev. 2: a covered F run whose digest carries one seam and nothing
else: LANDING F, the detail naming (e) alone); **why-void** (A-START on 151's ip97, none on 153's; A-NAMING on a
`before` without "And, Captain", none with it); **as-if-frozen** (rev. 2: `as_if_frozen(draft)` changes `measured`, every
budget and `rehearsals` and nothing else; `freeze` would accept its freeze-time keys); **door-test** (`door_test` reads (-100, 1333)
off e23's pinned text, None off e24's); **store-census** (PASS with 6.1's line; mutants each FAIL by name: e15 registered
`inert` `shared_by` [32] (its caller e32 instanced at 328); e15's key removed from the writes ("in no list"); 151 e3
registered `inert` (instanced at 110); 151 e3 t3 ip909 removed from `dead`; 151 e8 removed from `inert`; 153 e23
registered `inert` (instanced at 328, and its ip203 a chain key); `live_shared` callers naming e3); **regions** (PASS;
mutants: 153.e23 dormant (instanced at 328), 153.e26 exit (instanced at no route entrance), 151.e8 exit (not instanced at
110), 153.e25 missing (a gateway not registered), 153.e24's points shifted, a dormant region whose `entrances` omit 328);
**goals** (PASS with 6.1's lines; mutants: `until` z_gt 900 ((c''): 433 u of the non-firing band, over the derived
180), a typed `walk.stale_slack` 500 ((c''): refused by name -- rev. 2, the claim critic's #8: under the first design it
let the 900 mutant pass), e25 dropped from `avoid` ((d')), `start` (-226, 1086) on the upper corridor ((c'): no open
tri under it), `walk.door` 153.e24 ((c''): no z term), `to` 150 ((e)), `closed_tris` empty (O2's: no route), the goal at
(19, 2500) (O2's: off the floor)); **route-pins** (PASS; mutants: a pin's text changed -- e23 t2 ip80's included --, a
`Map.Bit[144] := 1` store added to 153's script (ip80's test no longer holds), mes 198 without "And, Captain", mes 199
without its source, mes 200 without its source, a `naming[0].on_page.windows` text not the computed line, mes 56 without
"Env Play()"); **build-pins** (O5's unit on O6's
predictions: an extra byte changed in member(153)'s e32 t1, a `PreloadField` operand remapped, an in-chain `Field()` left
unremapped: FAIL each); **keys offline mutants** (a write's value -- ip2248 := 0; a chain `off` + 1; `start_first`'s
target; a dead site's value; `start_music` at ip138; a start-dependent `after.value` 12; an `after.run` "O1-O4" (not
`AFTER_RUN`); an `after.source` removed; the e15 key at sid 32 (the join fails); the ip1006 `++` key's `prior` removed);
**p-donor-log**, **p-launch** (O5's units with 151/153/154);
**p-settings** (O5's, plus `DisableNameChoice` 1 FAILS), **p-pad**, **p-override**, **p-engine**, **text-strict**,
**input-witness** (O4's units on O6's pinned values).

It prints the summary columns (FROZEN COVER FORBIDDEN VOID-ASYM START NO-SC CHAIN RESIDUE WRITES NULL STABLE LANDING NAMING
WALK PATTERN START-DEPENDENT MASKED STATE JOIN) and "N/N cases as registered", exiting 1 on any miss.

---

## 9. Build order (three parts; no deploy, no game, no `tools/play.py`, no full suite)

Run pytest from `ff9mapkit/`, the study scripts from the worktree root. The harness tests run in REAL TIME (the FakeGame
loops on a thread): run the named `-k` selections, never many at once, and the whole file only where a PART says so,
alone (serially: O5's B0 measured 26 timing flakes at `-n 6`, every one passing alone). A SKIPPED test is not a pass:
every required pytest run reports 0 failed and its skips/xfails exactly the PART's baseline's (taken before the PART's
first change); a skip for missing templates is fixed with `py -m ff9mapkit extract-templates` and the run repeated.
**Load-robust tests** (O4 and O5 lost runs to load flakes; the nightly runs the whole file at `-n 6`): a test that
drives a route on the fake re-runs its run (at most 2 more) when, and only when, it ends in a DRIVER class a starved
harness can cause (V13 budget; V13 "the loss went unseen" -- S14; V7 by a timed-out walk), asserting the class on each
discarded attempt -- a GAME class (V4, V5 by the game, V10, V14, V19), a V11, a V13 of the page witness (a typed
name), or a wrong verdict is never re-run; every race is reproduced by a deterministic stall (a wrapped call,
`fake.stall_publish`, the test-held `fake.exit_gate` for path A -- rev. 2, the driver critic's #3: a test whose
assertion depends on which landing path a run took must GATE the switch, because a starved run takes the other path
and is still "done", so no re-run rule catches it), never by real starvation; the fake's loop runs at most 4x its
`render_fps`. A test asserts nothing a lead's in-game step changes (no deployed flag, gate
witness or the draft's `rehearsals` list pinned -- O2, O4 and O5 each lost a pre-merge run to that): the draft test
reads the rehearsals from the draft, never a literal. A failure that passes on an immediate re-run of that test alone is
a timing flake: named in the commit message, never ignored. Commit on the branch when a step is green, one step per
commit, each message ending with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Write non-ASCII files with
Python (utf-8) or the Edit/Write tools; frozen JSON and baselines are LF (`-text`); a Windows path inside a Python string
is raw or escaped.

### PART A -- the regression gate extended to O5 (baseline FIRST), then the shared opt-in changes
0. **Before anything:** `git log --oneline master..HEAD`, `git status`; the branch-point counts of the whole
   `tests/test_harness.py` (master's own record, as O5's PART A read it) into A0's commit message.
1. **A0: the O5 gate and its baseline, FIRST.** Extend `segment_regress.py` (1.4: G0'''' `--capture-o5` with its
   two-readings rule and refusals; G28-G31; `union_sources(*sources)` and `union_base` over three baselines; G21's
   message; `--rebaseline-source` over three (`baseline_o5` None by default, `--baseline-o5` on the CLI);
   `FAKE_PINS_O5`, `FAKE_PIN_CLASSES_O5`, `fake_pins_o5()`, `o5_pin_names`; `REQUIRED_TESTS_O6` empty; `_missing()`'s
   `o5s`/`o6`; the module docstring gains G0'''' and G28-G33 and says G30 is O5's VOID-path baseline) with
   `test_segment_regress_o5_pins_join_the_union` (into `REQUIRED_TESTS`). Run `py studies/story-trace/segment_regress.py`
   (G1-G27 green at the head first: a red gate is triaged before any capture), then `--capture-o5`, and commit
   `research/o5_regress_baseline.json` with its `.gitattributes` line before any other code change. Then the gate reads
   G1-G31 (G21 over three).
   **A0b: THE O5 REPLAY, BEFORE ANY FAKE EDIT** (rev. 2, the claim critic's #5: G1-G31 replay RECORDED sessions and
   cannot see a fake change, and once B1 re-baselines O5's pinned `_VisitBeat` methods, G26 passing proves O5's tests
   pass, not that the fake is unchanged). `test_fake_door_keeps_the_hallway_route_identical`: O5's route builder
   (`_o5_route`, S and F) played BY HAND -- `_fv_play`'s scripted player, the fake stepped frame by frame
   (`_frame_once`), no thread, no wall clock -- to its end; the document it builds: every frame whose compact sample
   changed (frame, field, ui_state, control, player x/z, the listed windows' slot/raw/text, the choice) and every trace
   row, LF JSON. With `O6_CAPTURE_REPLAY=1` it WRITES `research/o5_fake_replay.json` -- refusing an existing file and
   refusing unless two captures in one process are equal -- on the fake as master left it; without it, it COMPARES and
   fails naming the first differing frame (a missing golden FAILS, never skips). Captured and committed, with its
   `.gitattributes` line, right after A0's baseline and before A1 -- so it proves H16/H16b (A1, A2) and H17/H18 (B1)
   neutral for O5's route alike. The name holds no "o5_" or "fake_visit" (G26's selection stays O5's own); it joins
   `REQUIRED_TESTS_O6` with B3's names.
2. **A1: S14, S14b and H16** (`step_of`'s `to`, `trigger_to_verdict` with its `left`, `x_trigger_to` and `x_trigger`'s
   one dispatch line; `run_step`'s `left` branch and opt-in `misroute` key and its `to_row`; rule 1's walk-out record;
   the region's `walkout` in `_enter_regions` / `_step_world` / `_step_exit_now`, and `fake.exit_gate`) with their eight
   tests (1.2, 3.1). Breaks: S14 -- drop `to` (path B reads V11), accept any landing, the first design's `strayed` for a
   wrong landing after the evidence (V11 driver, the rows backed), judge a loss read in another field; S14b -- no
   walk-out record (path A's `flip_frame` None); H16 -- no walk-out, ignore the gate.
3. **A2: S15 and H16b** (`end_run`'s `end_naming` on the refused warp -- the screen accepted FIRST -- its retried warp
   and the session-stop marker; `run()`'s clean stop; `reset_blocked_fields`) with their five tests (1.2, 3.2). Breaks:
   no retried warp; the first design's order (the ladder before the screen); a plain HarnessError; the marker caught as
   a plain HarnessError in `one()`. The commit message names the INTENDED O1/O2 change (1.2 S15, 11.6).

**PART A REQUIRED-GREEN** (after A0, and again after A1 and A2):

| Command | Expected |
|---|---|
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G31 each PASS (G21 over three baselines: no re-baseline row expected in PART A -- H16/H16b touch no pinned function) |
| `py studies/story-trace/o1_dryrun.py` | exit 0; "16/16 cases as registered" |
| `py studies/story-trace/o2_dryrun.py --predictions studies/story-trace/o2_predictions_v1.json` | exit 0; "86/86 cases as registered" |
| `py studies/story-trace/o3_dryrun.py --predictions studies/story-trace/o3_predictions_v1.json` | exit 0; "102/102 cases as registered" |
| `py studies/story-trace/o4_dryrun.py --predictions studies/story-trace/o4_predictions_v1.json` | exit 0; "103/103 cases as registered" |
| `py studies/story-trace/o5_dryrun.py --predictions studies/story-trace/o5_predictions_v1.json` | exit 0; "144/144 cases as registered" |
| `py studies/story-trace/o5_hallway.py --analyse C:\gd\Dream-World-IX\.harness-runs\20261003-091627-story-o5 --predictions studies/story-trace/o5_predictions_v1.json` | exit 0; `VERDICT: PROVEN`; the archived `o5_report.txt` byte for byte (`PYTHONIOENCODING=utf-8`) |
| `py studies/story-trace/o5_hallway.py --offline-check --predictions studies/story-trace/o5_predictions_v1.json` | exit 0; 6 PASS (0.2 #15) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "segment"` | all passed, 0 failed, 0 skipped (A0's one; A1's eight after A1; A2's five after A2) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o5_ or fake_visit or fake_story_suppress"` (after A1, A2) | all passed, 0 failed, 0 skipped: O5's tests untouched by S14, S14b, S15, H16, H16b |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o2_ or o3_drive"` (after A1) | all passed: the O2/O3 walks (their trigger steps carry no `to`) unchanged |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o1_ or o2_"` (after A2) | all passed, 0 failed, 0 skipped: O1's and O2's own tests untouched by S15's reorder (no existing test stops a run on a naming screen; the INTENDED change is pinned by A2's `test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake`) |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "fake_door_keeps_the_hallway"` (after A0b's capture, without `O6_CAPTURE_REPLAY`; again after A1 and A2) | 1 passed, 0 failed, 0 skipped: O5's hand-stepped route IDENTICAL on the fake -- H16, `exit_gate` and H16b neutral for it |

### PART B -- the FakeGame for O6's route, S16, then the driver's O6 tests
1. **B0:** the PART's baseline of the whole `tests/test_harness.py` (passed / xfailed / skipped), run ALONE and serially,
   from this worktree with the templates extracted. Expected: A0's recorded branch-point count plus PART A's 15 new tests
   (A0's one, A0b's replay, A1's eight, A2's five); any other difference explained before B1.
2. **B1: H17, H18, H19** (`fakegame.py`): the `naming` and `door` visit steps (`VISIT_STEP_KEYS`, `DOOR_DEFAULTS`),
   `_visit_steps`' checks for them, `_VisitBeat.__init__`'s new knobs (`unparsed_frames` a `{mes: k}` dict),
   `_VisitBeat.ui`'s naming keys, `_VisitBeat.open`'s [STNR] rendering, `_VisitBeat._run`'s dispatch and the new
   `_naming` / `_door` methods (the door's 25 ticks, its walk-out, `exit_gate`); `fake.names`; and the eight fake tests
   of 3.3-3.4, each with its break. The O5 pins this edits (`_visit_steps`, `_VisitBeat.__init__`, `_VisitBeat.ui`,
   `_VisitBeat.open`, `_VisitBeat._run`) are re-baselined by name with their reasons IN THIS COMMIT (`--rebaseline-source
   NAME --reason TEXT`); no O5 test body changes; every O5 test still passes (G26), AND A0b's replay still reads
   identical -- the behavioural proof the re-baseline needs.
3. **B2: the O6 route builder** (`_o6_route`, `_o6_register`, test-side, 3.6) and
   `test_fake_door_route_plays_to_154_unattended` (a SCRIPTED PLAYER, not the driver: every page, pair and timed window
   Confirmed, the naming's two Confirms, Up held from the grant until control goes; `fake.named` [3]; the [STNR] pages
   render "Steiner"; the trace with `story_suppress`: 4.18's tuples by ip -- 10 + 24 rows, the e15 row in its window --
   and no `c` row; the cut row 154 ip26; break: a builder whose e23 fires on its whole quad).
4. **B3: S16 and the driver on the fake.** S16 in `segment_drive.py` (`naming_of` with the `windows`, rule 4's `before`,
   the page witness that JUDGES) with its four tests (1.2: `test_segment_naming_of_is_strict`,
   `test_segment_naming_on_page_rows_on_the_fake`, `test_segment_naming_of_reads_every_frozen_predictions`,
   `test_segment_alexandria_naming_keeps_its_rows_on_the_fake`; into `REQUIRED_TESTS`); then O6's predictions on the
   fixture's fields (`_o6_pred`: the cell (30820, 1190, visit 2), the naming registration with `on_page` and its
   windows, the witness stub, `side_ends` {S: [30821], F: [31246]}, the members). Tests (S at 60 fps mean ticks, F
   through the members at 31 fps quantized where named; `wait_scale` 0.25; `story_suppress` on, as O5's):
   - `test_o6_drive_names_steiner_and_walks_to_the_north_door_on_the_fake` -- S and F: beats `named`, `name_on_page`,
     `steiner_door`; the `named` row with `before` (198's raw), the `name_on_page` row (199 alone, rendered "Steiner",
     `verdict` "ok" -- 200 opens 6 ticks later in the builder); the door row `done`, `lost` z > 1200 in 30820 / 31245,
     its `walkout` filled at rule 1 (S14b); the pattern by ip (4.18); the end row 154's ip26 (31246 on F); no
     A-MISMATCH; `end_state`; `forbid_live` True: no forbidden row. Break: drop S16 (the run uncovered: `name_on_page`
     False). (The builder's default `walkout_stop` 2065 leaves him still ~13 ticks before the switch, so `settle()`'s
     two-tick rule usually returns first -- path A, which today's `x_trigger` also passes; this test asserts NO path,
     and S14's break is the next test's, on path B.)
   - `test_o6_drive_takes_the_landing_before_the_walk_returns` -- `walkout_stop` None: path B, covered; the row's
     `route.landed` set, `flip_frame` set. Break: today's `x_trigger`.
   - `test_o6_drive_takes_the_landing_after_the_walk_returns` -- `walkout_stop` 1400 and `fake.exit_gate` released by the
     log hook when the door's step row is appended (rev. 2, the driver critic's #3: path A DETERMINISTIC -- the switch
     cannot come before the step row, whatever the harness thread's load): path A, covered, `route.landed` None, and
     S14b's `flip_frame` (`flip_late`), `landed_frame` and `walkout` on the row. Break: no S14b.
   - `test_o6_drive_wrong_door_is_the_drivers_v11` -- a mutant table walking south into e25 (a loss WITHOUT the
     evidence): V11 driver, the step row's `door` 153.e25 and `landed` "64"; its post-landing rows backed. Break: e25
     registered `dormant`.
   - `test_o6_drive_misrouted_door_is_rule_2s` (rev. 2, the claim critic's #1; renamed from `..._is_the_drivers_v11`) --
     S, `door_misroute` {"e23": "150"}: the evidence held, the step row `left` with `misroute` 30830 and `landed` None,
     the run VOID V11 (GAME) at rule 2's cell [30830, 1190, 2], the 30830 rows UNBACKED (`_backing` None). Break: the
     first design's `strayed` (V11 driver, `landed` set, the rows backed).
   - `test_o6_drive_misrouted_door_to_a_real_field_is_v19` (rev. 2, the claim critic's #1) -- F, `door_misroute` {"e23":
     "150"} with `land_real` {"150": 30830}: V19 (game) at [30830, 1190, 2] -- a stop_on finding, never a re-runnable
     VOID. Break: the first design's V11 driver.
   - `test_o6_drive_loss_unseen_is_v13` -- `fake.stall_publish` across the fade: V13 driver; re-run-safe by its class.
   - `test_o6_drive_fork_landing_in_real_154_is_v19` -- F with `land_real` {"154": 30821}: V19 game at [154, 1190, 2].
   - `test_o6_drive_typed_name_is_the_drivers_v13` (rev. 2, the claim critic's #2; renamed from
     `..._typed_name_reads_on_the_page`) -- `name_typed` "Rusty": the `name_on_page` row's `verdict` V13, its 199 line
     "“Captain Rusty!”", the run VOID V13 (driver) at [30810, 1190, 1] "input at the naming screen"; never re-run by the
     load-robust rule. Break: the first design's S16 (record, never judge) -- the run covered.
   - `test_o6_drive_unparsed_page_is_skipped` -- `unparsed_frames` {199: 2}: the page row's frame is the first PARSED
     sample's; and with the pair opened together (lag 0) and `unparsed_frames` {200: 3}: the row lists 199 only,
     `verdict` "ok". Break: list every window holding the tag (the unparsed sibling then fails the judgment).
   - `test_o6_drive_stuck_naming_screen_stops_the_run` -- `naming_deaf` 9: rule 4's `accept_name` raises, the run
     STOPPED with the screen up; then `end_run`: `end-naming-failed` and the session-stop marker (S15).
   - `test_o6_drive_naming_recovery_reaches_the_title_on_the_fake` -- the run stopped with the screen up (a wrapped
     `accept_name` raising once), `reset_blocked_fields` {30810}: `end_run`'s rows `recover-warp-failed`, `end-naming`,
     `recover-warp-after-naming`, the title, and no `close_ui` call before `end-naming` (the screen accepted FIRST).
     Breaks: drop S15's retried warp; the first design's order.
   - `test_o6_drive_control_in_151_is_v4` -- `grant_at` {1: [...]}: V4 game at [151, 1190, 1]. Break: key the VOID
     `[donor, sc]`.
   - `test_o6_drive_stop_page_in_the_start_is_v5_driver` -- `error_window` {1: 2}: V5 driver at [151, 1190, 1]; {2: 2}:
     V5 game at [153, 1190, 2].
   - `test_o6_drive_unregistered_naming_is_v10` -- a naming step in 153's visit: V10 game at [153, 1190, 2].
   - `test_o6_drive_e15_late_is_covered` -- `e15_late`: covered (the driver never reads the order; C1's PATTERN test
     judges it).
   - `test_o6_drive_walks_the_real_hall_on_the_fake` (rev. 2, the driver critic's #1) -- the fake's floor
     `PlayerWalkmesh(stock 153, closed=the 33)` and the driver's `floor_for` the same, `fake.clearance` 120 (Steiner's
     radius: `SetObjectLogicalSize(30, ...)` x 4, 0.2 #19): from (-245, 42) the step is `done`, its loss at z > 1333
     INSIDE e23's quad, and THE CORNER RECORDED -- a wrapped `g.send` logs each walk hold's start, and some walk hold
     ends >= 20 u east of where its pressed line put it (the fake's push off the corridor mouth's west wall; the
     critic's run: hold 1 (-245, 42) "up" -> (-179, 941), 44 u east). NO x band: hold sizes follow the fake's measured
     rate, and the first design's "x in [-60, 20]" failed at clearance 80 (x -91) and passed at 120 by 10 u -- a flake at
     `-n 6`. Reads the install (a skip-with-warning without it: a skip fails G32).
   In this commit every `test_o6_*`, `test_fake_naming_*` and `test_fake_door_*` name goes into `REQUIRED_TESTS_O6` and
   G32 joins the gate.
5. **B4:** the whole `tests/test_harness.py` ALONE, serially: B0's counts + every new test passed, B0's xfails, 0
   skipped, 0 failed.

**PART B REQUIRED-GREEN:**

| When | Command | Expected |
|---|---|---|
| B0, and B4 | `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore` (alone, serially) | B4: B0's counts + every new test passed, B0's xfails, 0 skipped, 0 failed |
| after B1 | `... -k "fake_naming or fake_door"` | 9 passed (the replay + the eight; B2: 10), 0 failed, 0 skipped -- the replay IDENTICAL on the edited fake |
| after B1 | `... -k "o5_ or fake_visit or fake_story_suppress"` | all passed: O5's fake and driver tests on the edited `_VisitBeat` |
| after B1-B3 | `... -k "o1_ or o2_ or o3_ or o4_ or o5_ or segment or fake_"` | all passed, 0 failed, 0 skipped |
| after B3 | `... -k "segment_naming or segment_alexandria"` | 4 passed, 0 failed, 0 skipped (S16's tests) |
| after B3 | `... -k "o6_"` | 17 passed, 0 failed, 0 skipped |
| after every B step | `py studies/story-trace/segment_regress.py` | exit 0; G1-G31 PASS (G21: each re-baseline row named in B1's commit), G32 from B3 |

### PART C -- O6 itself
1. **C0: measure, read-only.** From the worktree, on O4's build (`C:\gd\_ns_playtest\o4\build`, never written): the
   route members' byte diffs against their donors, per language (O6-BUILD's pins: O5's `route_build`, expected
   unchanged), and the chain's `campaign.toml` (route members 31244 / 31245 / 31246 -- anything else STOPS PART C until the
   predictions are re-derived). No commit (the numbers go into C1's `o6_forks.json` `built.measured`).
2. **C1: `o6_steiner.py`** (1.3, sections 4-6: the draft, the checks LANDING, NAMING, WALK, PATTERN with its floating
   rows, START-DEPENDENT -- O2's check and report PORTED with `after` and the O1-O5 wording -- the offline checks with
   `instanced_at6`, `store_census6` and its LIVE shared proof, `regions_problems6`, `goals_extra6` and `door_test`, the
   route pins and `route_mes`, `trace_summary`, the CLI), `o6_forks.json` (6.4), the `.gitattributes` line for
   `o6_predictions*.json`. Tests (into `REQUIRED_TESTS_O6`): `test_o6_steiner_draft_reads_the_chain_from_campaign` (the
   rehearsals read from the draft, never a literal);
   `test_o6_steiner_freeze_refuses` (each refusal of 7.3 -- rev. 2's included: a typed `stale_slack`, a registration
   without `windows`, an `after` without `source`, a measured e15 position outside the window);
   `test_o6_steiner_route_builder_matches_the_keys` (the builder's stores == the draft's writes, chain, masked and start
   rows; its H13 trace's `pattern_of6` == the draft's `pattern`, the floating row inside its window; its window texts
   == the registration's computed lines); `test_o6_steiner_instanced_at_reads_the_compare_dispatch` (151 at 110 and at
   327; O4's raises; 153 at 328 equal to O4's); `test_o6_steiner_census_proves_live_and_inert` (the real bytes: PASS; e15
   registered inert -> FAIL by name; 151 e3 registered inert -> FAIL); `test_o6_steiner_regions_roles`;
   `test_o6_steiner_goals_door` ((c') on a synthetic mesh with the start off the floor; (c'') with until z_gt 900 and
   with a typed `stale_slack` 500 (refused); (d') with e25 out of `avoid` and with an upstairs tri past z 1200; (e) with
   `to` 150); `test_o6_steiner_pattern_floats_the_e15_row` (inside the bytes' window PASS; before ip727 and after ip1656
   FAIL; a changed `measured` never changes the result); `test_o6_steiner_naming_check` (each clause's FAIL, its PASS);
   `test_o6_steiner_start_dependent_check` (equal: PASS, the report line rendered from `after.run` -- "after the O1-O5
   routes as driven it would write 11 (from 3)", and "O1-O6" renders "O1-O6"; old 0 / new 9: FINDING; an earlier row on
   byte 6: EXPLAINED, named; old 1 / new 9 on one side: START DRIFT on that side, never a finding; 3 -> 11 on both:
   START DRIFT, "the O1-O5 continuation"; never "after O1"); `test_o6_steiner_why_void_reads_151s_error_path_as_the_start`
   (and A-NAMING on a `before` without the marker); `test_o6_steiner_preflight_verdicts` (P-DONOR over 151/153/154,
   P-TEXT3 strict, `DisableNameChoice` 1 FAILS P-SETTINGS).
3. **C2: `o6_dryrun.py`** -- every case and unit of section 8 as registered, O3's EXACT `case()`, run on the draft AND on
   `as_if_frozen(draft)` (`--as-if-frozen`), N/N each (rev. 2, the claim critic's #9). G33 joins the gate with
   `O6_DRYRUN_FLOOR` = the count C2 prints; `test_o6_steiner_trace_summary_cuts_at_end_places` lands here (it reads the
   dry run's renderer, O4's C2 #11).
4. **C3: `o6_rehearse.py`** + `--rehearsal-report`. Tests (every one with `warp_arrive_control` False and the engine's
   `soft_reset_ui`): `test_o6_rehearsal_stage_ids_follow_the_chain`; `test_o6_rehearsal_plumbing_on_the_fake` (R-DOOR: the
   record holds every 7.2 section -- the naming, the page row and its verdict, the e15 gap and window, the grant, the walk
   tap, hold 1's end and the corner, the walk holds in [`walk_stop_z`, 1333) and the hold-2 starts, the landing path with
   S14b's walk-out, the trace summary, `end_run`'s rows); `test_o6_rehearsal_naming_void_stops_at_the_screen_on_the_fake`
   (R-NAMING-VOID: `NamingStop` raises at rule 4's first `accept_name`, the session's own restored; end_run's three rows,
   no `close_ui` before `end-naming`; the title; break: no restore -- end_run's own `accept_name` then raises too);
   `test_o6_rehearsal_walk_void_stops_mid_walk_on_the_fake` (R-WALK-VOID's z variant on the real hall's floor at
   clearance 120 -- the walk there needs two holds, hold 2 sent at z ~940 (0.2 #7): the raise before the hold sent at
   z >= the stop, no `hold` after it, `recover-warp`, the title; break: a timer around `route_to`);
   `test_o6_rehearsal_walk_void_falls_back_to_the_first_walk_hold` (`walk_stop_hold`: the raise before the first hold
   after the basis is cached -- never a calibration probe); `test_o6_rehearsal_smoke_sends_no_storytrace_on_the_fake`;
   `test_o6_rehearsal_fpass_runs_untraced_to_the_member_on_the_fake`.
5. **C4: the O6 section in `PLAN.md`** -- the question, the segment, the sides and their ends, the naming and the name
   on the page, the start-dependent keys and their scope, the e15 row and its float, the door walk and S14, the checks,
   "draft: rehearsals pending, freeze pending", "a US session" in its heading, and THE O7 HANDOFF (verbatim, 9.1). The
   brief's milestone line (CLAUDE.md section 10) is left as it is.

**PART C REQUIRED-GREEN** (after each of C1-C4, as far as it exists):

| Command | Expected |
|---|---|
| `py studies/story-trace/o6_steiner.py --offline-check` | exit 0; "predictions: the draft"; "chain: member(151) 31244, member(153) 31245, member(154) 31246"; 6 PASS -- O6-BUILD, O6-KEYS, O6-TEXT, O6-CENSUS, O6-REGIONS, O6-GOALS, each detail 6.1's expected line |
| `py studies/story-trace/o6_steiner.py --preflight` | exit 0, ALL GREEN (12) -- or the exact failing line reported to the lead |
| `py studies/story-trace/o6_steiner.py --draft` | exit 0; the draft JSON: `side_ends` {"S": [154], "F": [31246]}, `visits` [151, 153], the naming with `on_page` and its two `windows`, the witness, the `walk` with no `stale_slack`, every `after` with `run` and `source`, `engine` the pinned sha, `rehearsals` [] |
| `py studies/story-trace/o6_dryrun.py` | exit 0; "N/N cases as registered" (from C2) |
| `py studies/story-trace/o6_dryrun.py --as-if-frozen` | exit 0; "N/N cases as registered" -- the same N: no case reads a freeze-time literal |
| `py studies/story-trace/segment_regress.py` | exit 0; G1-G32, and G33 from C2 |
| `py -m pytest tests/test_harness.py -q -p no:cacheprovider -W ignore -k "o6_ or fake_naming or fake_door"` | all passed, 0 failed, 0 skipped, every `REQUIRED_TESTS_O6` name among them |

Then the lead's sequence (7.1-7.4): `--preflight`, the rehearsals, the freeze checklist, `--freeze` (v1), the session.

### 9.1 THE O7 HANDOFF (C4 copies it into PLAN.md's O6 section; the critic's #10)
"**Next, O7:** 154@315 -> 158 -> 159 -> 160 -> 162 -> 163 -> 164 -> 165 -> 166 -> FMV004 -> `Field(55)`, started by a
raw `warp 31246 315 1190` (S: `warp 154 315 1190`), Steiner's control on arrival (154 e0 t0 ip588, Main_Init's tail).
That start is NOT clean. A raw warp lacks what O6 leaves behind -- the party rebuild ([Steiner]: SetPartyReserve(8),
RemoveParty 0-11, PARTYADD(3); a raw New Game party is [Zidane]), `Bit[3855]`/`Bit[3854]` 1, `UInt16[21]` 8, `UInt16[19]
|= 8` and `Byte[6] |= 8` (bit 3), `Byte[208]` 1, `Byte[303]` 1, `Byte[18]` 1, `Byte[8]` 125 -- and these are READ past
O6's end: `Bit[3855]`/`[3854]` by 164 e1 t3 (the knights' count, ip326), the party and `UInt16[19]` by 55 e8 t1 (ip633
SetPartyReserve, the PARTYCHK loop at ip666, and the start-dependent BRANCH at ip1354: on a raw start ip1380 writes
`UInt16[19] |= 1`, a true run skips it). O7's start analysis begins from these (pokes, an O6 prefix, or a claim scoped to
the branch), never from 'clean'. O7 also needs, each opt-in and FakeGame-tested, O1-O6 kept byte-identical: a WAYPOINT
step kind (154's balcony -> the west flight -> the ground: two legs with complementary closures, the engine's
neighbour links -- `wm154.out`; 164/165's self-overlapping spirals); a per-step CLEARANCE threaded into `route_to`
(164's narrow turn plans only at <= 64; `route_to` takes none: session.py:4139-4143); a HEIGHT evidence (164 e2 fires at
`f[1] < -12000`, 165 e2 at `f[1] < -15000`: S14's `to` judges their landings, but `until` reads only x and z -- it needs a
y axis); the 164 KNIGHT HOLD (e1 t1 ip230 `Bit[3811] := 1` races the exit after four walks at speed 15 and an animation: a
hold at a waypoint and an order check); a MOVIE decision (FMV004, `MBG_DEF("FMV004", 1, 0)`: type 0, skippable, 45.41 s
live, no page after it -- a skip policy needs a defined span, else rule 9 plays it out); and the 55 SEAM decision
(member(166) 31258 keeps a raw `Field(55)`: F lands in REAL 55 unless 31258 is rebuilt with 55 -> 31205, owner-gated).
Settled for O7 by the O6 research: every walked field's grant is its Main_Init tail (154 ip588, 158 ip379, 159 ip665,
160 ip399, 162 ip866, 163 ip618, 164 ip698, 165 ip778); the live door stores `Byte[13] := 3` are 158 e2 ip194 and 165 e2
ip205 only; 159's forced monologue (e16 t1 ip390, pages 296-300, `Bit[3796] := 1` ip672) re-grants in place
(`interrupts` 1)."

---

## 10. Open risks (what only the game can settle)
1. **The landing path and the walk-out** (F2): whether pathing holds him exactly still a radius short of the floor's
   end (z ~2065, an estimate: rev. 2) or the radius forces leave him jittering, and so whether `route_to` returns before
   or after the switch, is the engine's to show. S14 makes both DONE and S14b records both; what remains is a loss never
   read in 153 (a read gap across the 25-tick fade: V13, the instrument's, re-run) and a walk-out that leaves him
   somewhere `settle()` never calls still (its 3-s timeout returns the last state: path B).
2. **151's scene under the driver** (F8, F9): 151 has never been driven (O5 cut at its first row): 17 pages, five KEYON
   pairs, 175/176 without `[NFOC]` (a Confirm may close them early: timing only), the [SPED=2] type-outs of 193, 195 and
   198. Rule 7 is O1's and drove O3-O5's scenes; a stall shows as V14 or the budget.
3. **The naming** (F3): Steiner's `ui_state` NameSetting publication (proven for Zidane in O1 and Vivi in O2, not for
   CharacterId 3); a stray rule-7 Confirm on the opening screen (harmless) or two (the run uncovered, re-run); the
   rendered [STNR] lines (the frozen texts are computed from the source; R-DOOR measures them -- a difference stops the
   freeze, and in a session would be every run's V13: VOID, never NOT PROVEN); an unparsed window (not expected: the
   engine parses at attach; the witness skips one anyway).
4. **The e15 row** (F4): its attribution in game (sid 15, tag 0, ip 32, add 0 by the source; uid 96 recorded, never
   compared) and its race with ip971 (floated inside the bytes' window, after ip727 and before ip1656; the measured
   position recorded, report-only). A sound sync that held the store past ip1656 (~12 s or more) would fail PATTERN on
   that run; one that never returns would leave e15 unrun: the run then fails WRITES/NULL symmetrically or one-sidedly --
   a game stall, not the fork's (the row is e32's Seq on both sides).
5. **The grant and the walk** (F1, F12, F15): the grant position is the bytes' (stage 45's Walk(-245, 42)); THE CORNER
   (rev. 2): hold 1 presses "up" into the corridor mouth's west corner, and whether the engine slides him east or stops
   him there is unmeasured (RadiusValid / ServiceForces) -- F1's go/no-go; the loss sample's z (expect 1333-1450) and x
   (inside e23, likely x -50 to -90, off the planned line); the walk holds sent in [`walk_stop_z`, 1333) (expect hold 2
   at z ~940-1020: R-WALK-VOID's z stop fires; the fallback only if not).
6. **The end state** (F5): no store at 315 races the read (the bytes); R-DOOR confirms it, Byte[8] included.
7. **Recovery from the naming screen** (F7): S15 accepts the screen on the refused warp, before any Cancel, then retries
   the warp -- seconds, unmeasured until R-NAMING-VOID (F6 records it). A screen `accept_name` cannot close stops the
   session (S15): judged on the runs it covered, never a wrong verdict.
8. **The budgets** (F6): estimated (0.2 #21) on O5's measured rate; R-DOOR freezes them. TickClock handles 31/60 fps
   flips (proven in earlier sessions).
9. **A pad or a hand at the machine** (F11): the witness polls the whole run between blocking calls; `accept_name` is one
   blocking call, and a key typed during it is unseen by the witness -- S16's page witness reads its result on the page
   instead and VOIDs that run (V13, the driver's: re-run; on every run of a side VOID-ASYM (b)).
10. **The shared install**: another session's deploy, a re-wired New Game or an engine rebuild mid-session is A-INSTALL
    (6.3); the lead re-runs `--preflight` on the session's own launch (G1).

Closed by the bytes or the source (no longer open): the three residue rows (0.2 #1); 151's compare dispatch and its
instancing (0.2 #2); the census with e15 live (0.2 #3); the pattern's 34 rows and no count (0.2 #4); the walk-out's
target, its speed (HonoUpdate's run), its hold a radius short of the floor's end (pathing) and the 25 ticks (0.2 #6);
the pressed path's two holds and the corner (0.2 #7, on the fake over the real mesh -- the corner's ENGINE effect stays
open: #5); the [STNR] rendering in `ParsedText`, parsed at attach, and 199 before 200 (0.2 #8); the values after the
O1-O5 routes as driven (0.2 #9, from the archives); the e15 window's bounds (0.2 #11); the route's geometry and the
evidence's soundness (0.2 #12, O6-GOALS); the end row's emission and the end state's stability (0.2 #13); end_run's
~67-s ladder on a naming screen (0.2 #17); no control in 151 (0.2 #20); no SC rung, battle, FMV, ATE or choice; every
route `Field()` retargeted in every language (O6-BUILD).

---

## 11. Critique log

### 11.1 The research critic's ten
Each re-checked in the bytes, the engine source, the harness or an archive; none disproved. (The task names nine; the
critique holds ten: #1 a blocker, #2 major, #3-#10 minor. All ten are logged.)

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (blocker) | The 153@328 walk as a plain `trigger` cannot accept a field change: a run whose `route_to` record already holds the next field reads V11 (driver) though the right door fired; the fake stops him dead, so no dry run can show it. | segment_drive.py:2485-2488 (`landed in (None, fid)`, then `strayed`); session.py:1780-1849 (`settle`), :2896-2907 (`_landed` under handoff), :3438-3441; DoEventCode.cs:860-869 (MOVQ), :2247-2275 (MJPOS); Obj.cs:60-67; e23 t2 ip58-ip211; fakegame.py:1663-1690 | ADOPTED as decision 3's option (a): S14 (`to`, `trigger_to_verdict`, `x_trigger_to`; `x_trigger`'s body unchanged), H16 (the region walk-out) and H18 (the visit door's walk-out); tests for path A, path B (failing on today's code), a wrong landing and an unseen loss; R-DOOR records the path (F2). SHARPENED (0.2 #6): e23's exit point lies 1665 u north, beyond the floor, so in O6 the race is not the critic's 1-in-3 but the engine's to decide each run; and a loss read only in the next field is the instrument's V13 under `to`, never a judged `until`. (Rev. 2: a wrong landing after the evidence is S14's `left`, rule 2's verdict, not the driver's V11 -- 11.5 #1; the walk-out held at z ~2065 and the fade 25 ticks -- 11.4 #2, 11.5 #7; path A gated in the fake and its flip recorded -- 11.4 #3, #5.) |
| 2 (major) | O5's GOALS (c)/(d) cannot be inherited: (d) refuses an exit inside `until` (e23 lies in z > 1200 by design), (c)/(d) test a PSX y contour this flat walk never reaches. | o5_hallway.py:759-834; the stock walkmesh with the 33 closed (0.2 #12) | ADOPTED: O6-GOALS (c') the first sample past z 1333 in e23 on open ground; (c'') the `until`'s threshold within `stale_slack` of the door's own (read from its pinned test); (d') every OTHER exit wholly outside the evidence and avoided, every open tri past z 1200 ground; (e) the landing's door (the only live Field(154) at 328). Mutants: until z_gt 900, e25 out of avoid, a start on the upper corridor ((-226, 1086): no open tri), `walk.door` e24, `to` 150. The critic's "evidence = the landing" note became (e) and S14's `to`, not a replacement for `until`. (Rev. 2: (c'')'s slack DERIVED, 180 u, a typed one refused -- 11.5 #8; (c') judges the planner's line, the pressed path differs -- 11.4 #1.) |
| 3 (minor) | O6-CENSUS must flip e15: at 328 e32 is instanced, so e15's ip32 is a live key. | o5_hallway.py:496-588 (`shared_by`); 153 e0 t0 ip617 InitObject(32); `shared_sites(153)` (0.2 #3) | ADOPTED: `live_shared` (4.6) with its caller proof; the other shared entries' callers proven not instanced at 328 and their entries storeless; the census mutant "e15 registered inert" FAILS by name. |
| 4 (minor) | R-WALK-VOID's x stop cannot fire on a northward walk; a hold can last 22.5 ticks, so a stop may have no between-holds moment before z 924. | o5_rehearse.py:309-333 (WalkStop); session.py:2672 | ADOPTED: the z variant (`walk_stop_z` 500); F15 reads R-DOOR's holds. SHARPENED (0.2 #7): one 1600-u leg and a 1350-u hold cap make ONE walk hold likely, so the design adds the fallback `walk_stop_hold` (stop before the first walk hold after the calibration), chosen by F15, and says which ran (11.2 #4). (Rev. 2: that sharpening was WRONG -- the pressed path is two holds, hold 2 sent at z ~940-1020, so the z stop fires; F15 restated as the stop's own firing condition, the fallback kept for a launch where it fails: 11.4 #1.) |
| 5 (minor) | Visit 2's row order is a timing race; PATTERN judges rows in order. | 153 e15 t0 ip6-ip32; e32 t1 ip866-ip971 (0.2 #11); o5_hallway.py:886-909 | ADOPTED: `pattern.floating` -- the e15 tuple once, between e32 t0's ip727 and e23's ip203, unordered among e32 t1's rows; `measured` filled from R-DOOR (F4) and required by `freeze`; the PASS case e15-after-971-both and the FAIL cases e15-twice / e15-outside-window. STATE's per-target histories are unaffected (Byte[8]'s own order is fixed). (Rev. 2: the window bounded by the bytes -- before e32 t1 ip1656, not e23's ip203 -- `measured` report-only, refused outside it: 11.5 #6.) |
| 6 (minor) | The naming has an on-screen witness: the [STNR] pages render PLAYER.Name. | mes 199/200 (block 3, US); DialogBoxSymbols.cs:67-68, FFIXTextTag.cs:390, TextParser.cs:54-70, HarnessAgent.cs:1708-1721 (0.2 #8) | ADOPTED: S16 records the first parsed [STNR] page after the screen; O6-NAMING (b) compares its lines with the frozen ones (computed from the source, measured by R-DOOR); the mutants name-typed-F, name-on-page-before-named, name-on-page-other-window. (Rev. 2: S16 now JUDGES -- a typed name the driver's V13, a miss uncovered -- and O6-NAMING re-checks: 11.5 #2.) |
| 7 (minor) | "Re-diffed in all 7 languages" overstates: the instruction diff was US only. | reconcile/forkdiff.py (`lang = "us"`); O5's C0 (`o5_forks.json` `built.measured`); `O5Segment.build_pins` | ADOPTED: O6-BUILD is O5's `build_pins` -- each language's script decoded on its own, every differing byte an in-chain `Field()` operand -- re-run at every `--offline-check` (0.2 #15 read it 21 of 21 today), with O5's C0 cited and P-EB pinning the live files. |
| 8 (minor) | The start-dependent machinery is O2's; O5 carries `start_dependent: []`; O2's report hard-codes "after O1". | o5_hallway.py:391; o2_alexandria.py:305-308, :1506-1512 | ADOPTED: O2's 4.5 shape with `after` {run "O1-O5", old, value, why} (4.5), O6-KEYS computing `after.value`, O6-START-DEPENDENT (a check: old and new per side, FINDING vs START DRIFT named) and the report line "after a true O1-O5 run it would write ..."; the values re-derived from the archives (0.2 #9). (Rev. 2: classified per run, never by side; the span rendered from `after.run` and checked against `AFTER_RUN`; "the routes as driven"; `after.old` labelled as read: 11.5 #3, #4.) |
| 9 (minor) | The end_run naming fix is incomplete: if `accept_name` itself fails, every later run's `end_run` meets the same stuck game. | segment_trace.py:581-587, :654-657 (0.2 #17) | ADOPTED: S15 -- the retried warp, and `end-naming-failed` raising a HarnessError with the `session_stop` marker that `run()` turns into a clean stop (later runs not driven, `session["stopped"]`, the analysis read); its FakeGame tests fail without it; R-NAMING-VOID. (Rev. 2: the screen accepted FIRST, before the ladder -- 11.4 #4; an intended O1/O2 change, pinned by A2's test -- 11.5 #5.) |
| 10 (minor) | The O7 handoff understates start dependence. | bytes_route/L164.txt:190 (164 e1 t3 ip326); bytes_route/L55.txt:678-698 (55 e8 t1 ip633, ip666) | ADOPTED: 9.1 (copied into PLAN.md by C4) lists what a raw `warp 31246 315 1190` lacks and who reads it past O6's end. |

### 11.2 Where this design reads a decision's letter differently (each said, none relitigated)
1. **Decision 3's "the landing is ... rec.landed, or the switch waited out":** read as `left_for`'s rule (the record's
   landing, else the switch waited out once the published id has left, else None) evaluated AFTER the walk. And "the loss
   sample" is read as the loss sample IN THE WALK'S FIELD: a sample first read in the next field carries that field's
   coordinates, so judging `until` on it would be meaningless -- under `to` it is V13 (driver), the instrument's (0.2
   #18). Without `to`, today's paths exactly.
2. **Decision 4's "the first [STNR] page after it reads 'Steiner'":** the driver's part is a third shared opt-in change
   the decisions do not name -- S16, `on_page` on a naming registration -- because the trace holds no page text and O1's
   rule-7 press rows carry none. Rev. 2 (the claim critic's #2): the DRIVER judges it -- the first sample listing a
   PARSED window a frozen entry names, each listed line against the registration's computed text: equal, the row and
   the beat; different, the driver's V13 (input at the naming screen) -- and O6-NAMING (b) re-checks a covered run's
   row; a page never caught parsed leaves the run uncovered. "The first [STNR] page" is read as that first sample's
   frozen windows: 199 alone, normally (200 opens ~6 ticks later), "“Captain Steiner!”" its line 1; 200's speaker line
   "Steiner" when listed (an exact line, where a substring would pass a typed "Steinerx"). Built in PART B (B3) beside
   the fake step it needs (H17), not in PART A: decision 9's PART A names the trigger `to` and the naming recovery only.
3. **Decision 4's "after page 198":** proven by the `named` row's `before` (S16: the last listed sample before the screen
   holds 198's source marker "And, Captain"), read off the ring before the Confirms -- the only record of the page order
   the trace and O1's press rows lack. Rev. 2 (the claim critic's #2): decision 4 lists "after page 198" inside the
   O6-NAMING check; this design reads it as a COVERAGE condition instead -- A-NAMING (5.1): a `before` without the marker
   leaves the run uncovered, re-run, VOID-ASYM (b) if every run of a side lacks it -- because a `before` without 198 is
   first the ring's miss, an instrument event, and THE PAIRED-WALK LAW's coverage rule makes an instrument event VOID,
   never a falsification. "Exactly one `named` row ... before the ip610 row" stays in the check.
4. **Decision 6's R-WALK-VOID "z variant (walk_stop_z ~500) with R-DOOR confirming at least two holds before z 924":**
   READ BY ITS INTENT (rev. 2, the driver critic's #1). The intent: the stop must fire MID-WALK -- a walk hold sent with
   control held, before the door can fire -- so the recovery is proven from inside the walk. The letter ("two holds
   before z 924") counts holds sent before the first sample past e23's south edge, and the critic's re-run on stock
   153's mesh shows hold 2 sent at z ~940-1020: past 924, inside e23's quad but in its NON-firing band (z < 1333), with
   control held -- the letter counts ONE and would choose the fallback for a stop that does fire there. F15 therefore
   states the stop's own firing condition: in every R-DOOR run a walk hold is sent at published z in [`walk_stop_z`,
   1333), with `walk_stop_z` taken from R-DOOR's measured hold-2 starts (the draft's 500 when they all start at or above
   it and every calibration probe ends below it). Standing inside e23's quad below 1333 is no hazard for the stop: e23's
   tag 2 tests `f[2] > 1333` every tick and fails. The fallback the first design added (`walk_stop_hold`, the first walk
   hold after the calibration) stays for a launch where the condition fails -- the same recovery situation (FieldHUD
   in 153@328, control held, the step underway), the record saying which ran (F15).
5. **Decision 6's O6-GOALS (c')/(d'):** stated as written, plus (c'') -- the `until`'s threshold within the DERIVED slack
   (rev. 2: `STALE_TICKS` 3 x 60 u = 180 u, never typed) of the door's own, read from its pinned test -- which is what
   makes the "until z_gt 900" mutant fail (900 is far inside e23's non-firing band, 433 u > 180), and (e), the critic's
   landing-evidence note, which S14 relies on -- for `to` AND, with (d'), for `left` (a landing elsewhere after the
   evidence is not the walk's).
6. **Decision 8's rehearsal list:** the research's R-THRONE (151 -> 153 alone) is not run (decision 8 names R-DOOR as the
   whole segment); R-WALK-VOID warps straight into 153 at 328 (the assembly from its start: no naming needed to stop a
   walk), its draft overlay setting the stage's start, the table's visit-2 cell still matching (`self.at` from the start
   place's index).
7. **Decision 10 (master moving):** the lead's merge may meet `source_pins.json` (both sides append rows: keep all, per
   name in head order), `REQUIRED_TESTS*` additions (keep both) and `segment_regress.py`'s neighbouring lines; then the
   whole gate and `tests/test_harness.py` run on the merged head.
8. **Decision 7's preflight "P-DONOR 151/153/154":** read as O5's P-DONOR over `route` + `end_fields` -- [151, 153] +
   [154]: the same three donors O5 read, in another order.
9. **Decision 1's end state:** O5 kept `Byte[8]` out of the live end state (151's ip315 raced the read); at 154@315 no
   store races it (0.2 #13), so `Byte[8]` is IN 4.10 -- and its history is frozen by PATTERN (b) as well.
10. **Decision 6's "PATTERN with the e15 row's position relative to e32 t1's rows UNORDERED (frozen from R-DOOR's
    measured gap)":** (rev. 2, the claim critic's #6) the WINDOW is frozen from the BYTES -- after e32 t0 ip727, before
    e32 t1 ip1656 -- and R-DOOR's measured position is frozen into `measured`, which the freeze refuses outside the
    window and the check never reads (report-only). The alternative the letter might suggest -- a window cut to the
    measured gap -- would be a check tuned to two samples of a race, failing the first session whose sound sync runs a
    little slower; the bytes' window holds every order the script allows and still fails a row the script cannot
    produce (before ip727, after the rebuild).
11. **Decision 3's "x_trigger returns done when the loss sample satisfies until AND the landing is None or a field whose
    place is `to` ... every other path unchanged (O1-O5 byte-identical)":** (rev. 2, the claim critic's #1) "every other
    path unchanged" is read as O1-O5's paths -- steps without `to` -- which are byte-identical. A step WITH `to` whose
    evidence held but whose landing is another place is not "done"; the first design made it the driver's V11, rev. 2
    makes it `left`, judged by rule 2 (the game's V11, or V19 on F for a real forked field), because O6-GOALS (d') and (e)
    prove the loss was e23's and e23's only live `Field()` leads to `to`: the walk cannot cause that landing.
12. **Decision 4's "end_run's naming recovery (accept the screen, then RETRY the warp ...)":** (rev. 2, the driver
    critic's #4) the first design accepted the screen only after the ladder had failed (~67 s of `close_ui` and the
    swallowed soft reset); rev. 2 follows the decision's order literally -- the screen accepted on the refused warp,
    then the retried warp, then the ladder -- and records the INTENDED effect on O1's and O2's inherited `end_run`
    (1.2 S15, 11.6).
13. **Decision 5's "O2's start_dependent check and report PORTED ... wording scoped to O1-O5 (never O2's hard-coded
    'after O1')":** (rev. 2, the claim critic's #3, #4) the scope is carried by the PREDICTIONS (`after.run` "O1-O5",
    checked against the class's `AFTER_RUN`), never by a literal in code -- O7's subclass changes one attribute; the
    wording says "the O1-O5 routes as driven", since `after.old` composes O2-O5's raw-start routes and is labelled as
    read; and the check classifies each deviation per run (FINDING / EXPLAINED / START DRIFT), where "one side vs both"
    had stood in for the classification.

### 11.3 The second round (rev. 2): how it was checked, and what it moved
Two critics read the first design: one for the DRIVER's robustness (five items, one major), one for the CLAIM's
integrity (ten, three major). Every disputed fact was re-read at the source, read-only: the harness (`session.py`'s
`_plan_hold`, `_leg_chunk`, `settle`, `close_ui`, `soft_reset`, `restore_baseline`, `accept_name`), the driver
(`segment_drive.py`'s backing, `stray`, rule 2, `run_step`), the Memoria source at the deployed DLL
(`FieldMapActorController.cs` HonoUpdate / ServiceChar, `EventEngine.MoveToward.cs`, `DoEventCode.cs` MOVQ / MJPOS /
SetPathing, `NameSettingUI.cs`, `TextParser.cs`, `Dialog.cs`, `DialogManager.cs`), the stock bytes (L151's stage 21,
L153's e23/e24/e25 t2, Main_Init's tail, e32 t0 ip548, e15 t0, e32 t1 ip866-ip1656), the stock 153 walkmesh, and the
O1/O2 archives (no `end-naming` row in any). The driver critic's two scratch scripts were re-run against this worktree
and reproduced every number they quoted. Nothing was disproved; every item is adopted (11.4, 11.5), one through the
critic's second option. Sections moved: 0.2 #6-#9, #11, #12, #17, #18; 1.1-1.3 (S14 `left`, S14b, S15's order, S16's
judgment, `AFTER_RUN`, the slack constants); 2.1-2.8; 3.1, 3.3-3.6 (`exit_gate`, 25 ticks, `stop_z` 2065, the pair's
lag, per-mes `unparsed_frames`); 4.5, 4.11, 4.12, 4.16 (74 pins), 4.18; 5.1-5.4; 6.1; 7.1-7.4 (F1-F4, F6, F7, F12, F15,
the refusals); 8 (cases and units); 9 (A0b, A1, A2, B0, B1, B3, C1-C3 and every REQUIRED-GREEN count); 10.

### 11.4 The driver-robustness critique (five)
Each re-checked in the harness, the engine source, the bytes or the stock walkmesh -- the critic's FakeGame walk re-run
here (`o6_critic_wm.py`, `o6_critic_sim.py` in the session scratchpad: every number reproduced) -- none disproved, each
adopted.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (major) | The door walk is not the straight, wall-clear 1600-u leg the design models: `_plan_hold` presses only the 8 pad directions and caps each hold's end at `_leg_chunk / 2` (180 u) off the leg, measured against avoid regions and blockers only; hold 1 "up" runs ~900 u into the corridor mouth's west corner; F15 counts one hold before z 924 and picks the fallback, though `walk_stop_z` 500 fires on hold 2 (sent at z 941-1019, inside e23's non-firing band); the B3 test's x band fails at clearance 80 and passes at 120 by 10 u. | session.py:2932-2944 (`_leg_chunk`: hazards and blockers, never walls), :3073-3179 (`_plan_hold`), :3142-3143, :8534 (`_eight_way`); `key_move_basis(0)` up = (0.0245, 0.9997), the leg 9.5 degrees east of +z; the critic's probe re-run: the up ray's clearance first < 120 at (-224, 917), open ground x [-175, 210] for z 1150-1800, the planned leg itself 113 u off at (-72..-59, 1078..1157); the sim re-run at clearance 120 ((-245, 42) `hold up 32` -> (-179, 941), `hold up 16`, loss (-50.4, 1339.8)), at 80 (holds sent at z 42, 989, 1288; loss (-90.8, 1348.4)), from (-220, 67) (hold 2 at (-113, 1019); loss (-49.7, 1360.2)); o5_rehearse.py:309-333 (WalkStop fires on ANY hold, calibration included: the probes stay below z ~192) | ADOPTED: 0.2 #7, #12 and 2.5 describe the PRESSED path (two holds, the corner, the loss off the planned line); F1/F12 gain the corner's go/no-go (hold 1's end; a slide or a stop the next hold clears is GO, a replan, blocker, push or extra hold NO-GO); F15 restated as the stop's own firing condition, `walk_stop_z` from R-DOOR's hold-2 starts (11.2 #4); the B3 test at `fake.clearance` 120 asserts done, a loss past z 1333 inside e23 and the corner recorded, no x band; C3's walk-void test runs on the real hall's floor. The planned line's soundness is untouched (O6-GOALS (d'): any loss past z 1200 is e23's). |
| 2 (minor) | The walk-out model is wrong twice: HonoUpdate rewrites his speed on every controlled frame (MOVJ uses the gait of his last one), and pathing stops him a radius short of the floor's end, z ~2065, ~12 ticks after a fire near 1340 -- not at 2185. | FieldMapActorController.cs:210-211 (`originalActor.speed = isRunning ? 60 : 30` while `GetUserControl()`), :360-361 (ServiceChar when `charFlags & 1`), :950-1027, :1060 (RadiusValid), :1161 (ServiceForces); EventEngine.MoveToward.cs:166 (`curPos += moveVec`), DoEventCode.cs MOVJ (`stay()` until arrival); DoEventCode.cs:2618-2628 (SetPathing -> `BGI_charSetActive`); L153 e32 t0 ip548 `SetPathing(1)`; the corridor profile (open ground at z 2150, none at 2200) | ADOPTED: 0.2 #6 rewritten (the number 60 survives, its reason changed; the hold at z ~2065); H18's builder default `stop_z` 2065 (`_o6_route`'s `walkout_stop`); F2 expects z ~2065; ip1160's pin re-labelled the stair walk's speed, e32 t0 ip548 pinned (4.16). No verdict depended on it: S14 marks both paths done. |
| 3 (minor) | The path-A fake tests depend on a wall-clock race: if the harness thread is starved it reads the switch first, takes path B -- still "done", so nothing re-runs -- and the `route.landed` None assertion flips. | session.py:1785-1849 (`settle`: two still samples spanning two ticks); segment_drive.py run_step (a "done" step is never re-run); section 9's load-robust rule | ADOPTED: `fake.exit_gate` (H16, H18), a test-held event released by a log hook when the door's step row is appended -- the switch can never precede the step row; both path-A tests use it; section 9's rule names it; path B (`stop_z` None) needs none. |
| 4 (minor) | Naming recovery waits ~67 s before it accepts the screen (six Cancels, `close_ui`'s 20 s, `soft_reset`'s 45 s), and only that gap keeps the Cancels' 0.5-s refocus from undoing `accept_name`'s first Confirm. | session.py:8034-8073 (`soft_reset`: 45-s wait, then raises), :8075-8100 (`close_ui`: six Cancels 12 frames apart, then 20 s), :8138-8176 (the rungs); NameSettingUI.cs:122-133 (`DelayFocusTextField`: 0.5 s), :72-83 (Confirm: focus off, then OK) | ADOPTED: S15's `end_naming` runs on the refused warp when `ui_state` is NameSetting -- accept, then the retried warp, then the ladder -- with no Cancel before it; its second call site (after the ladder) is >= 45 s from any Cancel; F6 records R-NAMING-VOID's measured recovery time; 0.2 #17, 2.8 and 7.1 re-timed; A2's test records `close_ui` / `soft_reset` calls and breaks on the first design's order. |
| 5 (minor) | In path A the flip is never recorded: `route_to` returns ~12 ticks before the switch, the step row's `flip_frame` is None, and O5's walk tap stops when `route_to` returns -- F2's "loss -> flip" and the walk-out's samples are unobtainable. | segment_drive.py run_step (`flip_frame` only from the executor), :2328-2353 (`switch` sets it only when it waits); o5_rehearse.py's WalkTap | ADOPTED as S14b: rule 1, on its first poll in the end field, reads `ring_since(lost.frame)` onto the done `to` step row in place -- `walkout`, `flip_frame` (`flip_late` when filled there), `landed_frame` -- in both paths; the rehearsal record and the report read them off the row (7.2, 5.4); A1's and B3's path-A tests break without it. |

The critic's "checked and sound" items hold as stated (the stray Confirms, the name on its first sample -- 0.2 #8 now
cites the attach-time parse -- S14 reading the real door either way, e24/e25 and the corridor soldiers); the
`unparsed_frames` knob is kept as a guard test, labelled a state the engine is not expected to publish (3.3).

### 11.5 The claim-integrity critique (ten)
Each re-checked in the driver, the analysis, the bytes, the engine source or the archives; none disproved; nine adopted
as asked, one (#4) through the critic's second option, with the first option's rejection reasoned here.

| # | Problem | Re-checked | Disposition |
|---|---|---|---|
| 1 (MAJOR) | S14 blames the driver for a wrong landing that can only come from e23's own `Field()`: V11 driver backs the fork's post-landing rows (A-FORBIDDEN), lets a one-sided misroute be re-run away under VOID-ASYM (b), flips class with the landing path (path A reaches rule 2 after a "done": V11 game), and demotes a real-150 V19 on F to a re-runnable VOID. | segment_drive.py:804-807 (the `walk` backing: `v` "V11" and `landed` == the hit's `fld`, never `by`), :2183-2185 (`stray()`: the game's with no unfinished walk), :2683 (`walked` None after a done step), :3036-3040 (rule 2's V19 for a real field a member forks); o4_castle.py:1729-1768 (VOID-ASYM (a), (b)); O6-GOALS (d'), (e) | ADOPTED: under `to`, the evidence held and a landing in another place is S14's `left` -- logged with `misroute` (`landed` None, no `v`), no raise -- and the next poll's rule 2 gives exactly its verdict (V19 game on F for a real forked field, else V11 game at rule 2's cell); the rows stay UNBACKED; V11 driver only for a loss without the evidence; `test_..._wrong_landing_is_rule_2s_on_the_fake`, `test_o6_drive_misrouted_door_is_rule_2s`, `test_o6_drive_misrouted_door_to_a_real_field_is_v19`; dry-run misroute-one-F (NOT PROVEN: VOID-ASYM F (a), FORBIDDEN F); 2.7, 11.2 #11. |
| 2 (MAJOR) | O6-NAMING turns instrument events into falsifications and a typed name counts as covered: (i) a name typed during `accept_name`'s blocking call is unseen by the witness and the run covered; (ii) an unparsed sibling lists its tag and fails (b); (iii) missed samples are NOT PROVEN; (iv) 199 opens ~6 ticks before 200, so the two-window equality is rarely exercised. | o4_castle.py:790-830 (the witness polled between blocking calls); DoEventCode.cs:2317-2340 and NameSettingUI `SetData` (the name has no field key); TextParser.cs:54-60 (`ParsedText = InitialText` until `Parse`), HarnessAgent.cs:1708-1721; DialogManager.cs:99-153, Dialog.cs:597-603, :1560-1575 (parsed at attach: (ii) guarded against, not expected); L151 stage 21 (e3 t1 ip679 `op_22(1)` ip693 199; e12 t1 ip796 `op_22(7)`, ip799 RunAnimation, ip803 200); segment_drive.py:3690-3808 (O5's guard: the other branch V13 by the driver, CHOICE re-checks) | ADOPTED in O5's CHOICE shape: S16's witness lists only PARSED windows a frozen entry names, judges each line against the registration's computed text (the windows now live once, there), writes `verdict`, and VOIDs V13 (driver) on a mismatch; no parsed frozen window before the visit ends -> the beat False (uncovered); a `before` without 198's marker -> A-NAMING (uncovered); O6-NAMING (b) re-checks (bypass mutants); name-typed-F now VOID-ASYM (b), name-typed-one-F PROVEN, name-typed-both VOID; the builder lags 200 by 6 ticks; a fake test with the pair opened together and 200 unparsed lists 199 alone; 0.2 #8, 1.2 S16, 4.11, 5.1, 5.3, 5.4, 11.2 #2-#3. |
| 3 (MAJOR) | O6-START-DEPENDENT labels a start difference as a fork finding: the rule keyed on sides, not on which field deviates; an unexplained `old` can only be the instrument's start. | StoryTrace.cs `AfterStore` (every hooked store emits its site's first row) and `Diff` (bypass writes surface as residue rows); P-EB's pins; the registered mutant start-dependent-differs-F (old 1, nothing explaining it) | ADOPTED: each deviation classified per run on the fields -- FINDING (old = prior, new differs), EXPLAINED (an earlier row on the target, named), START DRIFT on that side (nothing explains it), "the <after.run> continuation" only at (`after.old`, `after.value`); the mutant renamed start-drift-F, start-dependent-new-differs-F added as the real finding. A drift still FAILS the check, with WRITES and STATE: the predictions' start is the claim's premise, and the label tells the lead the start drifted, never the fork. Making a drift UNCOVERED (an A-DRIFT reason) was weighed and not taken: the critic asked for the label, and a VOID would let a re-run quietly absorb a start that drifts on one side only. |
| 4 (minor) | The port keeps literals ("after a true O1-O5 run"; KEYS checking "O1-O5") -- O2's "after O1" mistake one segment later, with O7 subclassing `O6Segment` -- and `after.old` is typed though 4.5 says a typed number is never trusted. | o2_alexandria.py:1500-1512 (O2's report line); the five archives (story-o1e: 50 e17 t1 ip3240 Byte[6] 0 -> 1, UInt16[19] 0 -> ... -> 1797; story-o2: 116 e2 t1 ip765 Byte[6] 0 -> 2, 100 e19 t1 ip1531 UInt16[19] 0 -> 2; story-o3/-o4/-o5: no row on bytes 6, 19, 20 -- the critic re-read them and agrees with 0.2 #9) | ADOPTED: the report renders `after.run` from the predictions; O6-KEYS compares it with the class attribute `AFTER_RUN` (O7 overrides); the wording says "the O1-O5 routes as driven"; a unit renders "O1-O6" as "O1-O6". For `after.old`, the critic's SECOND option -- labelled (`after.source`: read from story-o1e and story-o2 at design time) and the 4.5 claim corrected. The FIRST option (re-derive it from the five archives' S traces at every offline check) is NOT taken: the number is a COMPOSITION of separate fresh-epoch routes, O2-O5 each from a raw start, folded with the bytes' `\|=`; re-reading the archives would only re-perform that composition, at the price of making O6-KEYS depend on five local archives, and would measure nothing the label does not already state. |
| 5 (minor) | "Behaviour-neutral for O1-O5" is false for S15 and S16, and the gate cannot see it: O1 and O2 inherit `end_run` and `run` and hold naming screens; `naming_of` runs on O2's frozen registration; G1-G31 replay recorded sessions; after B1's re-baseline G26 proves the tests pass, not the fake unchanged; "a short session reads VOID" holds only under `min_covered`. | o1_opening.py:164, :246, :359; segment_trace.py:537-587, :633-690; o2_predictions_v1.json `naming` (`{"beat": "named", "donor": 116, "sc": 1155}`); O3-O5's `naming` []; segment_regress G1-G31; fakegame.py `_frame_once` (a hand-stepped, deterministic fake) | ADOPTED: 1.2 S15 states the INTENDED O1/O2 change and 11.6 records it before building; A2's `test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake`; B3's `test_segment_alexandria_naming_keeps_its_rows_on_the_fake` and `test_segment_naming_of_reads_every_frozen_predictions`; A0b's hand-stepped O5 replay golden (`research/o5_fake_replay.json`), captured before any fake edit and identical after H16/H16b (A1, A2) and H17/H18 (B1); dry-run naming-stuck-after-four (PROVEN on 2 + 2 covered); the "short session" claim corrected. |
| 6 (minor) | The e15 float window (e32 t0 ip727 to e23 ip203) is far wider than the race, spanning the rebuild and the grant; `measured` is read only by `freeze`, and only to refuse null. | L153 e15 t0 ip6-ip32; e32 t1 ip866-ip971 and ip971-ip1656 (24 `op_22` summing 351 ticks, the stage-44/45 walks, four pages) | ADOPTED (the bytes' bound): after e32 t0 ip727, before e32 t1 ip1656 (4.18); the freeze refuses a measured position outside it; `measured` stated report-only (11.2 #10); e15-before-window-both and e15-after-rebuild-both registered. |
| 7 (minor) | The walk-out waits 25 ticks, not 26: ip95's `op_22(1)` is skipped. | L153 e23 t2 ip68 (`Map.Bit[159] == 1`; Main_Init ip2356 sets it), ip80 (`Map.Bit[144] == 0`; 153 never writes it: 26 references, all `B_EQ` tests), ip91 `DisableMenu()`, ip92 `JMP(L68)` -> ip98, ip153 `op_22(25)`; e24/e25 the same shape | ADOPTED: 25 everywhere (0.2 #6, #18, 2.3, 2.5, 3.4, 3.6, 10); e23 t2 ip68-ip92 and Main_Init ip2356 pinned (4.16: 74 pins); O6-KEYS scans 153 for no `Map.Bit[144]` store; a route-pins mutant adds one. |
| 8 (minor) | (c'') trusts a typed `stale_slack`: a frozen 500 would let the "until z_gt 900" mutant pass. | 4.12's own why ("two ticks of his run plus a tick's publication lag" makes 180, not the typed 160); FieldMapActorController.cs:210-211 (the run's 60 u a tick); session.py:1814-1817 (the published position's lag) | ADOPTED (derive): `STALE_TICKS` 3 x `RUN_U_PER_TICK` 60 = 180 u, o6_steiner constants; a typed `stale_slack` refused by (c'') and by the freeze; goals mutant `stale_slack` 500; F1 cross-checks it on R-DOOR's loss samples (each >= 1153). The `until`'s 1200 (133 u) stays inside it. |
| 9 (minor) | G33's input changes when the lead freezes (`measured`, the budgets, `rehearsals`): the class of change that cost O2, O4 and O5 a pre-merge run. | 1.4 G33; 7.3 | ADOPTED: `o6_dryrun.as_if_frozen(draft)`; C2 and G33 require N/N on it as well as on the draft or frozen file; every case reads freeze-time values from its predictions; `--as-if-frozen` in PART C's REQUIRED-GREEN; the unit as-if-frozen. |
| 10 (minor) | Some clauses have no failing case: NAMING (b)'s "exactly ONE" and "in the same field", START-DEPENDENT's zero-row case, the float's lower bound, LANDING (e) alone, and the scope line's "a name typed on both sides alike would fail (b) on both". | section 8's table against 5.3's clauses | ADOPTED: name-on-page-twice-both, name-on-page-other-field-both, start-dependent-missing-both, e15-before-window-both and name-typed-both registered with their co-failures; the scope line rewritten (a typed name is the driver's V13: VOID, never "fails (b)"). "seam-key-alone-F" is registered as seam-key-F with (a)'s and FORBIDDEN's co-failures: (e) is not expected to fail ALONE on any row the render gives -- a seam needs a row placed in a real non-member field after a member (storytrace.py:838-870), which (a) (a field-mode `w`/`c` row) or RESIDUE (an `r` row) also reads -- so the unit landing-e drives (e) alone, and C2 registers a lone-(e) case if it finds a row kind that reaches it. |

### 11.6 As built (the implementer appends, PART by PART)
Where the design was silent or wrong, each the smallest correct thing, in O5's 11.5 form; and the review's findings, in
O5's 11.6 form.

**Known before building (rev. 2, the claim critic's #5):** S15 changes O1's and O2's INHERITED `end_run` on purpose. An
O1 run (50's `Menu(1, 0)`) or an O2 run (116's `Menu(1, 1)`) stopped with its naming screen up now has the screen
accepted on the refused warp, then the retried warp to its recovery field, then the ladder -- where it used to spend
~67 s in `close_ui` and the swallowed soft reset before accepting it and climbing the ladder through the running
scene; and an O1 or O2 session whose screen `accept_name` cannot close now stops cleanly instead of losing every later
run. No archived run log in `.harness-runs` holds an `end-naming` row (story-o1 to -o1e, story-o2: grep, read-only),
and the gates replay records without re-running `end_run` (G1-G31), so the change is invisible to them; A2's
`test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake` pins the new behaviour. The implementer
confirms it here in A2's entry.

#### PART A, as built: where the design was silent or wrong (each the smallest correct thing)
A0 first: the gate at the branch head (2f7247ce: c954f986 plus the O6 research and design commits, research files
only) read 27/27 PASS (34 min) -- nothing to triage. The branch point's whole-file count: master's own record is the
nightly at 2575495e (before the O5 merge), `tests/test_harness.py` 771 collected, 770 passed + 1 xfailed
(`_CREEP_BAND`); c954f986 collects 850. The gate extended (6e74884b), the O5 baseline was captured there -- two
readings identical, G26 (54 passed), G27 (144/144), G28-G31 PASS, 7 m 48 s, 82 sources (G26's 54 tests, FAKE_PINS_O5's
3 and `_VisitBeat`'s 25 methods), 2102602 bytes -- and committed (00e499ef) before any other code change. A0b's golden
(d6d31ea9) was captured on the unedited fake: 42248 bytes; per side 188 sample changes over 1054 frames (the stair
walk's 42 control frames, choice 128, the four visits) and 38 trace rows. The gate then read 31/31 (G21 over three
baselines: 296 sources, 8 re-baseline rows) after A0 (37 min) and again after A1 (8541f1f3; G7 59 passed; 41 min).
After A2 (78f04f02) it read 30/31 (48 min): G26 failed ONE test, `test_o5_drive_climbs_the_real_stair_on_the_fake` --
the step "done" and its evidence (`x_le` -1100) held, but the loss sample read at x -1243.5 against the test's own
bound of -1284. On 153's mesh the y -450 contour runs diagonally (its first crossing walking -x, by the test's own
height function: x -1242 at z -300, -1315 at z -250, -1360 at z -200), so x <= -1284 holds only where the walk meets it
at z >= about -271, and this run met it near z -299: the starved walk's LINE bent, not the loss rule. A TIMING FLAKE by
9's rule, named in the as-built commit: alone it passed three times running (12-14 s each), and G26's whole selection
passed on its re-run (54 passed, 0 failed, 0 skipped; 5 min 53 s). PART A's lines on its path are inert there (it
drives `SD.drive` through `_o5_run`: no trigger step carries `to`, no region a walk-out, no test a gate, and never
`end_run` or `run`; A2's one fake line it meets is the unread `reset_blocked_fields`). The test is O5's and pinned, so
PART A leaves it as it is. The REQUIRED-GREEN `-k "segment"` run at 78f04f02 read one more while another project's batch
job loaded the machine: `test_segment_drive_ends_per_side_on_the_fake` (O4's S6) found no trace row in its end field --
the store is its test-side director's, 240 frames after the arrival, and the director stops when the drive returns --
alone 3 of 3 (10 s each), and the selection's re-run 59 passed; O4's, its PART A lines inert as above. The gate's
re-run at 78f04f02 then read 31/31 (38 min; G7 64 passed, G26 54, G30 87 sessions and 57 units, G21 296 sources). No
G21 re-baseline row in PART A: H16, `exit_gate` and H16b touch no pinned function, and A0b's replay reads identical
after each step. PART A adds 15 tests (A0's one, A0b's replay, A1's eight, A2's five): 865 collected.
The confirmation the design asks for (11.6, "Known before building"): S15 changes O1's and O2's inherited `end_run` and
`run` exactly as stated there -- A2's commit message names it -- and
`test_segment_end_run_naming_paths_for_the_opening_and_alexandria_on_the_fake` pins it on the unedited classes (its
mutant, today's `end_run`, fails it: no `recover-warp-after-naming` row).

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | A0, `union_sources` | "`union_sources(*sources)`: a name in two refused". | Over the O3, O4 and O5 baselines, in that order; for two the refusal keeps O5's words byte for byte ("pinned in both the O3 and the O4 baselines"), so O4's pinned test reads as before; with three each pair that shares a name is named. |
| 2 | A0, `_missing()`'s `o6` | "from C2 the frozen O6 predictions or O4's `campaign.toml` (`o6`)". | The flag exists from A0 (A0's list names it) and no mode passes it until G33 joins at C2; it reads `o6_predictions_v1.json`, else O4's chain `campaign.toml`, by path -- never importing `o6_steiner`, which C1 writes. |
| 3 | A0, the O5 pins | "the tests G26 collects". | `test_segment_regress_o5_pins_join_the_union` holds "o5_", so G26 collects it and the O5 baseline pins it with O5's tests (as the O4 baseline pinned O5's A0 test): an edit to it now needs its re-baseline row. |
| 4 | A1, S14b's handle | "on "done" for a step carrying `to`, `self.to_row = row`". | A TRIGGER step carrying `to`: a cross's `to` is required (STEP_NEEDS) and every O2-O5 cross carries one, so the letter would have written a walk-out record onto their rows at rule 1 -- O1-O5 no longer unchanged in behaviour. |
| 5 | A1, `trigger_to_verdict` | "("v13", why) -- the loss was never read in this field (``lost`` None with a landing, ...)". | ``lost`` None is V13 with or without a landing: the executor settles "still here, control held" (the wait; ``failed``) before the verdict, so ``lost`` None with no landing arises only when the published id left and came back (the switch saw no landing) -- the instrument's, never a judgement on a missing sample. |
| 6 | A1, the flip frame | "on a landing from `rec.landed` the FLIP FRAME read off the ring". | Only for a loss read in this field: a loss first read in the next field (V13) leaves no in-field sample to read the flip after. |
| 7 | A1, S14b's `flip_late` | "`flip_frame` when None (... `flip_late` True)". | Written in both paths: True when rule 1 filled the flip (path A), False when the executor had one (path B, or the switch waited out) -- a row always says which. |
| 8 | A1, the V13 test's stall | "the fake's publication stalled from the fire to the switch -- `fake.stall_publish`". | A test-side hold of the fake's publish while its exit is pending: `stall_publish` blocks the frame LOOP for its stall (the game hung inside the write), so no switch can come inside it and the read after it is the fire's own sample (control gone in the walk's field) -- it cannot make the first read without control land in the next field. |
| 9 | A1, the wrong-landing test | "the region's own `to` is another place: the step row's outcome "left"". | Run on path B (no `stop_z`). On path A the step is "done" before the landing exists and rule 2 judges the landing after it -- the same V11 (game), but no `misroute` row to assert. |
| 10 | A1, the load-robust rule | "re-runs its run (at most 2 more) when ... a DRIVER class a starved harness can cause". | Also, in the path-B and the no-`to` tests, a run the load bent onto the other path (route_to's 3-s settle out before the switch; a loss first read in the next field), each discarded attempt's class asserted: those runs end "done" or in the asserted V11, so no class rule could catch them. Path A is gated, as designed. |
| 11 | A1, H16's knob and gate | `"walkout": {"to", "speed", "stop_z"}`; "`fake.exit_gate`". | `to` required, `speed` default 60 (HonoUpdate's run), `stop_z` default None; any other key refused when the region fires (strict, as every fake knob). The gate holds every exit that comes due in `_step_world` (a region's or a contact trigger's scheduled one) and a region's immediate one (`exit_frames` 0); a contact trigger's immediate switch is not gated -- no O6 test holds one there. Without a gate, today's fake. |
| 12 | A2, S15's skipped run | "`skipped` "the session stopped: <why>" when its drive never began". | The run's outcome stays the loop's "not driven"; `read_session` (shared, unedited) reads the record as today's skipped run -- A-SKIPPED and the drive's end not reached, both the driver's. O6's "no VOID class" reading (5.1) is its own analysis's (PART C). |
| 13 | A2, the O1/O2 test | "each with its own route's screen up on the fake". | `recovery=30821` passed to the inherited `end_run` (4600 is no fixture field), and the ladder's waiting rungs on 3-s clocks (`_o3_quick_ladder`), so today's-order mutant reads in seconds; the correct path never waits in them. |

#### PART B, as built: where the design was silent or wrong (each the smallest correct thing)
B0, at 181dba23 before any PART B change: the whole `tests/test_harness.py` alone, serially -- 864 passed, 1 xfailed
(`_CREEP_BAND`'s 60.0-210), 0 skipped, 0 failed: 865 collected, A0's branch-point 850 plus PART A's 15 (62 min). Nothing
to explain. B1 (e6b2a1e4): the gate 31/31 (36 min) with eight re-baseline rows (16 in all). B2 (d3ecd444): the gate's
first run read 30/31 -- G19 failed ONE test, O4's `test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor`
(one of its three paced fights ended in an exception its `_o4_run_informative` does not re-run), on a path no PART B
code touches (the Chanbara machine beat, `segment_drive` and `segment_trace` untouched by B1 and B2; B2 test-side only),
green in B0 and in B1's gate an hour before; alone 3 of 3 (73 s each) -- a TIMING FLAKE by 9's rule, named in B2's
commit; the gate's re-run on that state read 31/31. B3 (5551bf0e): the gate 32/32 (39 min 53 s; G7 68 passed, S16's
four among them; G32 27 passed, every `REQUIRED_TESTS_O6` name; G21 296 sources, 16 rows: B3 touches no pinned source).
After B1-B3, `-k "o1_ or o2_ or o3_ or o4_ or o5_ or segment or fake_"`: 294 passed, 0 failed, 0 skipped (32 min). B4's
first run (at 5551bf0e, alone, serially, 73 min) read 892 passed, 1 xfailed, 0 skipped, 2 FAILED -- O4's
`test_o4_drive_scores_100_on_the_fake` and
`test_o4_drive_paced_tracks_the_closing_prompt_beside_its_successor`, each VOID in all three of its
`_o4_run_informative` attempts by the instrument's own load class, "a read gap of 0.11-0.18 s straddles instance N's
mark" (the harness not reading for over a tenth of a second mid-fight, at about 02:07); no PART B code on their path
(their predictions register no naming, so S16 never arms; the Chanbara beat and executor untouched); each passed alone 3
of 3 (49-50 s and 72-82 s) -- TIMING FLAKES by 9's rule, named here; everything else as B0 (no test lost, B0's xfail,
all 30 new tests passed). B4: the whole file re-run alone, serially, at 5551bf0e (67 min) -- 894 passed, 1 xfailed
(B0's), 0 skipped, 0 failed: B0's 864 and PART B's 30, no test lost, no status changed. PART B adds 30 tests (B1's
eight, B2's one, B3's four S16 and seventeen O6 drive tests): 895 collected. A suggestion for the lead: O4's two
paced/scoring drive tests meet the harness's read-gap VOID whenever the machine stalls the driver's reads mid-fight; the
nightly's -n 6 may meet them.

| # | Where | The design | As built, and why |
|---|---|---|---|
| 1 | B1, the re-baselined pins | "The O5 pins this edits (`_visit_steps`, `_VisitBeat.__init__`, `_VisitBeat.ui`, `_VisitBeat.open`, `_VisitBeat._run`)". | Eight, not five: also `_VisitBeat.shown` (an unparsed window publishes its raw, and the publish reads `shown`), `_VisitBeat._open_mes` and `_VisitBeat._pair` (they pass the step's mes to `open`, which keys `unparsed_frames` by it -- `open` alone never knows it). Each re-baselined by name with its reason in B1's commit; A0b's replay identical and G26's 54 passing on the edited fake. |
| 2 | B1, the door's fire row | "a `visit_log` row "door" (name, x, z)". | Kind `fire`: `_run` already logs every step's start, the door step's as kind `door`, so a fire of the same kind would make two `door` rows of one fire. |
| 3 | B1, a naming step without `name` | (silent) | The OK saves no name (`fake.names` unchanged, `fake.named` gets the character): a [STNR] page then renders the pre-filled default, "Steiner". |
| 4 | B1, the door's walk-out | "for `ticks` ticks ... the walk-out". | The visit beat's own: a step per WHOLE field tick of its script (MOVJ runs in ProcessEvents beside the door's own script), held through the exit gate ("he stands where the walk-out left him meanwhile"); H16's region walk-out stays the world's (a frame's share of a tick, while a FakeGame exit is pending), untouched. |
| 5 | B2, the [STNR] pages | "199 / 200 / 203 / 211-214 / 217-219 / 221 / 222 carry block 3's [STNR] sources as raws". | 198, 199 and 200 (and window 56) carry block 3's sources -- what a driver rule or a check matches; the other [STNR] pages are placeholders under the tag (`[STNR]` + a distinct line): no rule or check reads their words and the fake renders the tag the same. The same coverage with less game text in the repo. |
| 6 | B2, the scripted player | "a SCRIPTED PLAYER ... the naming's two Confirms". | `_o6_play`, O6's own: O5's `_fv_play` presses nothing on a naming screen (no window is listed there); O5's helper untouched. |
| 7 | B2, the builder's knobs | `_o6_route(side, *, e15_late, walkout_stop, short, wait_scale, **faults)`. | Plus `lag199` (default 6, the bytes'): the unparsed-window tests need the pair opened together, or 60 ticks apart (#11). |
| 8 | B3, `naming_of` | "each exactly keys of NAMING_KEYS -- `donor` and `sc` ints ..., `beat` a non-empty str or None, `why` a str". | `donor` and `sc` required; `beat`, `why` and `on_page` optional -- O2's frozen registration carries no `why`. |
| 9 | B3, `before` | "the ring's latest sample before the naming screen's first sample that listed a window". | The screen's first sample read as the start of the run of `NameSetting` samples ending at rule 4's poll; `before` the latest sample before it that lists any window. |
| 10 | B3, the witness at a new visit | "a new visit disarms it -- no row, its beat stays False ... (the ring held no parsed frozen window while 151 lasted)". | Rule 3 first takes a LAST scan of the field the run leaves -- a poll gap across the visit's end must not lose a 199 the ring did hold -- then disarms; a row found there is judged as any other. |
| 11 | B3, `unparsed_frames` in the tests | "`unparsed_frames` {first: 2}" / "{second: 3}" / "{199: 2}" / "{200: 3}". | 90 frames, 200 opening 60 ticks after 199 (or with it): two frames are ~8 ms at the fake's 4x loop, under the driver's 30-50 ms reads, so the knob would test nothing (and with 199 unparsed past 200's opening the first parsed frozen window is 200's). A run whose ring read no unparsed sample tests nothing and is re-run (the drive test's `spoiled`); the segment test runs its scene at the render rate, 1.5 s unparsed. |
| 12 | B3, "199 alone" | "the `name_on_page` row (199 alone, ...)". | Asserted exactly per sample: the row stands on the ring's first sample listing a parsed frozen window and lists exactly that sample's parsed frozen windows -- 199 alone whenever 200 is unopened or unparsed there. Never a timing claim: a starved read lands after 200 opens and lists both, both right. |
| 13 | B3, `short` | "`short`: 153@328 alone from the grant". | The short run starts in 153 at 328 and keeps the cell at visit 2 (the start place's index in `visits`, as R-WALK-VOID's stage does), so every VOID cell reads `[..., 2]` as on the full route. |
| 14 | B3, the misroute tests | (the path unstated) | Path B (`walkout_stop` None), as A1's wrong-landing test (PART A #9): on path A the step is done before the landing exists and has no `misroute`; a run the load bent onto path A is re-run, its class asserted (the game's). |
| 15 | B3, `test_o6_drive_e15_late_is_covered` | no break named. | Break: the builder's `e15_late` ignored (the row then precedes ip971) -- no driver code reads the order, which is the claim. |
| 16 | B3, the wrong-door test | "V11 driver, the step row's `door` 153.e25 and `landed` "64"". | Also accepted: the step "interrupted" with rule 2's late V11 on the same row -- a fake starved past `exit_wait_s` (5 s) -- the driver's V11 for the same walk, its `door` and `landed` the same. |
| 17 | B3, the main drive test | "its `walkout` filled at rule 1 (S14b)". | Its `flip_frame` and `landed_frame` asserted in either path; the walk-out's samples are the gated path-A test's, where `settle()`'s reads guarantee them (on path B a fully starved harness may read nothing between the loss and the flip). |
| 18 | B3, the naming recovery test | "`end_run`'s rows ... the title". | A director gives control in 30821 on arrival (4600's grant; the O6 runs keep `warp_arrive_control` False): without it `end_run`'s retried warp waits 60 s for control and logs `recover-warp-after-naming-failed`. |
